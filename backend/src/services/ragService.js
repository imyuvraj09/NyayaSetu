/**
 * Dedicated RAG Client Service for NyayaSetu.
 * Handles microservice HTTP communication with the Python FastAPI RAG Service.
 * Implements strict timeout management, typed error translation, and response normalization.
 */

const { RAG_SERVICE_URL, RAG_SERVICE_TIMEOUT_MS } = require('../config/env');
const {
  RAGServiceUnavailableError,
  RAGServiceTimeoutError,
  RAGResponseError,
} = require('../utils/errors');

class RAGService {
  constructor(baseUrl = RAG_SERVICE_URL, timeoutMs = RAG_SERVICE_TIMEOUT_MS) {
    this.baseUrl = baseUrl.replace(/\/+$/, '');
    this.timeoutMs = timeoutMs;
  }

  /**
   * Check whether the FastAPI RAG service is reachable and healthy.
   * @returns {Promise<{ available: boolean, details: any }>}
   */
  async checkHealth() {
    const healthUrl = `${this.baseUrl}/api/v1/health`;
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 5000);

    try {
      const response = await fetch(healthUrl, {
        method: 'GET',
        headers: { Accept: 'application/json' },
        signal: controller.signal,
      });
      clearTimeout(timeout);

      if (!response.ok) {
        return { available: false, details: { status: response.status } };
      }

      const data = await response.json();
      return { available: true, details: data };
    } catch (err) {
      clearTimeout(timeout);
      return { available: false, details: { error: err.message } };
    }
  }

  /**
   * Submit a legal inquiry to the Python FastAPI RAG service.
   *
   * @param {string} query - Cleaned user question
   * @param {string} [sessionId] - Optional session ID for tracing
   * @returns {Promise<{ content: string, sources: Array, ragMetadata: Object }>}
   */
  async queryLegalRAG(query, sessionId = null) {
    const endpointUrl = `${this.baseUrl}/api/v1/query`;
    const startTime = Date.now();

    const controller = new AbortController();
    const timer = setTimeout(() => {
      controller.abort();
    }, this.timeoutMs);

    try {
      console.log(`[RAG Client] Calling RAG service at ${endpointUrl} (timeout: ${this.timeoutMs}ms)`);

      const response = await fetch(endpointUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Accept: 'application/json',
        },
        body: JSON.stringify({
          query,
          session_id: sessionId,
        }),
        signal: controller.signal,
      });

      clearTimeout(timer);
      const durationMs = Date.now() - startTime;

      if (!response.ok) {
        let errorBody = '';
        try {
          errorBody = await response.text();
        } catch (_e) {
          // ignore
        }

        console.error(`[RAG Client] HTTP ${response.status} from RAG service: ${errorBody}`);

        if (response.status === 503) {
          throw new RAGServiceUnavailableError();
        }
        if (response.status === 504 || response.status === 408) {
          throw new RAGServiceTimeoutError();
        }
        throw new RAGResponseError(`RAG service returned HTTP error: ${response.status}`);
      }

      const data = await response.json();

      // Validate required response fields
      if (!data || typeof data !== 'object' || typeof data.answer !== 'string') {
        throw new RAGResponseError('Malformed response payload from AI legal service.');
      }

      // Normalize sources
      const rawSources = Array.isArray(data.sources) ? data.sources : [];
      const normalizedSources = rawSources.map((s, idx) => ({
        sourceNumber: idx + 1,
        sourceLabel: s.source_label || `[SOURCE ${idx + 1}]`,
        documentName: s.document_name || 'Indian Statutory Law',
        chunkId: s.chunk_id || '',
        pageNumbers: Array.isArray(s.page_numbers) ? s.page_numbers : [],
        relevanceScore: typeof s.reranker_score === 'number'
          ? s.reranker_score
          : typeof s.similarity_score === 'number'
          ? s.similarity_score
          : null,
        snippet: s.text_snippet || s.content_snippet || '',
        evidenceType: s.evidence_type || 'STATUTE',
        caseName: s.case_name || null,
        court: s.court || null,
        citation: s.citation || null,
        paragraphNumber: s.paragraph_number || null,
        isHoldingOrRatio: Boolean(s.is_holding_or_ratio),
      }));

      // Normalize metadata
      const normalizedMetadata = {
        model: data.model_metadata?.model || null,
        provider: data.model_metadata?.provider || null,
        retrievalDuration: null,
        totalDuration: durationMs,
        warnings: Array.isArray(data.warnings) ? data.warnings : [],
        status: data.status || 'success',
        requestedFacets: Array.isArray(data.requested_facets) ? data.requested_facets : [],
        facetCoverage: data.facet_coverage || {},
        facetValidation: data.facet_validation || {},
        claimValidation: data.claim_validation || {},
        qualityStatus: data.quality_status || 'COMPLETE',
        caseLawStatus: data.case_law_status || null,
        evidenceGraph: data.evidence_graph || null,
        generationStatus: data.generation_status || (data.status === 'retrieval_only' ? 'RETRIEVAL_ONLY' : 'SUCCESS'),
        retrievalStatus: data.retrieval_status || 'SUCCESS',
        validationStatus: data.validation_status || 'PASSED',
      };

      console.log(
        `[RAG Client] RAG response received in ${durationMs}ms with ${normalizedSources.length} sources (status: ${normalizedMetadata.status})`
      );

      return {
        content: data.answer,
        sources: normalizedSources,
        ragMetadata: normalizedMetadata,
      };
    } catch (err) {
      clearTimeout(timer);

      if (err.name === 'AbortError') {
        console.error(`[RAG Client] Request timed out after ${this.timeoutMs}ms`);
        throw new RAGServiceTimeoutError();
      }

      // Check for connection refusal or DNS resolution failure
      if (
        err.code === 'ECONNREFUSED' ||
        err.code === 'ENOTFOUND' ||
        err.message?.includes('fetch failed') ||
        err.message?.includes('connect ECONNREFUSED')
      ) {
        console.error(`[RAG Client] Connection refused to RAG service at ${this.baseUrl}: ${err.message}`);
        throw new RAGServiceUnavailableError();
      }

      // Re-throw our typed errors directly
      if (
        err instanceof RAGServiceUnavailableError ||
        err instanceof RAGServiceTimeoutError ||
        err instanceof RAGResponseError
      ) {
        throw err;
      }

      console.error('[RAG Client] Unexpected error communicating with RAG service:', err.message);
      throw new RAGResponseError('Unable to process AI legal response.');
    }
  }
}

// Singleton instance
const ragService = new RAGService();

module.exports = {
  RAGService,
  ragService,
};
