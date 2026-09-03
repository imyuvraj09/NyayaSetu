import React from 'react';
import SourceCitation from './SourceCitation';

/**
 * Attempts to parse a structured legal response JSON from the assistant's content string.
 * Returns the parsed object if valid, or null if the content is plain text / old format.
 */
export function parseStructuredResponse(content) {
  if (!content || typeof content !== 'string') return null;

  const trimmed = content.trim();

  // Quick heuristic: must look like a JSON object
  if (!trimmed.startsWith('{')) return null;

  try {
    // Handle possible markdown code fences wrapping JSON
    let jsonStr = trimmed;
    if (jsonStr.startsWith('```')) {
      jsonStr = jsonStr.replace(/^```(?:json)?\s*\n?/, '').replace(/\n?```\s*$/, '');
    }

    const parsed = JSON.parse(jsonStr);

    // Validate required fields
    if (
      parsed &&
      typeof parsed === 'object' &&
      typeof parsed.mainAnswer === 'string' &&
      parsed.mainAnswer.trim().length > 0
    ) {
      return {
        legalDomain: parsed.legalDomain || null,
        mainAnswer: parsed.mainAnswer,
        legalBasis: parsed.legalBasis || null,
        recommendedNextSteps: Array.isArray(parsed.recommendedNextSteps)
          ? parsed.recommendedNextSteps.filter((s) => typeof s === 'string' && s.trim())
          : [],
      };
    }
  } catch {
    // Not valid JSON — fall through to null
  }

  return null;
}

/**
 * Renders a structured legal response card with sections:
 * Legal Domain → Main Answer → Legal Basis → Recommended Next Steps → Sources
 */
export default function AssistantLegalResponse({ structured, sources }) {
  const { legalDomain, mainAnswer, legalBasis, recommendedNextSteps } = structured;
  const hasSteps = recommendedNextSteps && recommendedNextSteps.length > 0;
  const hasBasis = legalBasis && legalBasis.trim().length > 0;
  const hasSources = sources && sources.length > 0;

  return (
    <div style={styles.responseCard}>
      {/* ── Legal Domain Badge ── */}
      {legalDomain && (
        <div style={styles.domainSection}>
          <span style={styles.domainLabel}>Legal Domain:</span>{' '}
          <span style={styles.domainValue}>{legalDomain}</span>
        </div>
      )}

      {/* ── Main Answer ── */}
      <div style={styles.mainAnswerSection}>
        {mainAnswer.split('\n').filter(Boolean).map((para, idx) => (
          <p key={idx} style={styles.answerParagraph}>
            {renderInlineFormatting(para)}
          </p>
        ))}
      </div>

      {/* ── Legal Basis ── */}
      {hasBasis && (
        <>
          <div style={styles.divider} />
          <div style={styles.sectionContainer}>
            <h4 style={styles.sectionHeading}>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" style={{ marginRight: '0.4rem', flexShrink: 0 }}>
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                <polyline points="14 2 14 8 20 8" />
                <line x1="16" y1="13" x2="8" y2="13" />
                <line x1="16" y1="17" x2="8" y2="17" />
              </svg>
              Legal Basis
            </h4>
            <div style={styles.sectionBody}>
              {legalBasis.split('\n').filter(Boolean).map((para, idx) => (
                <p key={idx} style={styles.basisParagraph}>
                  {renderInlineFormatting(para)}
                </p>
              ))}
            </div>
          </div>
        </>
      )}

      {/* ── Recommended Next Steps ── */}
      {hasSteps && (
        <>
          <div style={styles.divider} />
          <div style={styles.sectionContainer}>
            <h4 style={styles.sectionHeading}>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" style={{ marginRight: '0.4rem', flexShrink: 0 }}>
                <polyline points="9 11 12 14 22 4" />
                <path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11" />
              </svg>
              Recommended Next Steps
            </h4>
            <ul style={styles.stepsList}>
              {recommendedNextSteps.map((step, idx) => (
                <li key={idx} style={styles.stepItem}>
                  {renderInlineFormatting(step)}
                </li>
              ))}
            </ul>
          </div>
        </>
      )}

      {/* ── Sources ── */}
      {hasSources && (
        <>
          <div style={styles.divider} />
          <div style={styles.sectionContainer}>
            <h4 style={styles.sourcesHeading}>
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" style={{ marginRight: '0.35rem', flexShrink: 0 }}>
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                <polyline points="14 2 14 8 20 8" />
              </svg>
              Verified Statutory Citations ({sources.length})
            </h4>
            <div style={styles.sourcesList}>
              {sources.map((src, idx) => (
                <SourceCitation key={idx} source={src} index={idx} />
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  );
}

/**
 * Light inline text formatter: handles [Source N] references and **bold** markers
 * without rendering raw markdown syntax to the user.
 */
function renderInlineFormatting(text) {
  if (!text) return text;

  // Split by **bold** and [Source N] patterns
  const parts = text.split(/(\*\*.*?\*\*|\[Source \d+\])/g);

  return parts.map((part, index) => {
    if (part.startsWith('**') && part.endsWith('**')) {
      return (
        <strong key={index} style={{ fontWeight: '600', color: '#0f172a' }}>
          {part.slice(2, -2)}
        </strong>
      );
    }
    if (/^\[Source \d+\]$/.test(part)) {
      return (
        <span key={index} style={styles.sourceRef}>
          {part}
        </span>
      );
    }
    return part;
  });
}

const styles = {
  responseCard: {
    backgroundColor: '#ffffff',
    border: '1px solid #e2e8f0',
    borderRadius: '10px',
    padding: '1.35rem 1.5rem',
    boxShadow: '0 1px 4px rgba(15, 23, 42, 0.04)',
    display: 'flex',
    flexDirection: 'column',
    gap: 0,
    transition: 'box-shadow 0.15s ease',
    maxWidth: '100%',
  },
  domainSection: {
    marginBottom: '1rem',
  },
  domainLabel: {
    fontSize: '0.8125rem',
    fontWeight: '600',
    color: '#64748b',
    letterSpacing: '0.01em',
  },
  domainValue: {
    fontSize: '0.875rem',
    fontWeight: '700',
    color: '#0d9488',
    letterSpacing: '-0.005em',
  },
  mainAnswerSection: {
    marginBottom: '0.25rem',
  },
  answerParagraph: {
    fontSize: '0.9375rem',
    lineHeight: '1.68',
    color: '#1e293b',
    margin: '0 0 0.7rem 0',
  },
  divider: {
    height: '1px',
    backgroundColor: '#e2e8f0',
    margin: '0.85rem 0',
    width: '100%',
  },
  sectionContainer: {
    marginBottom: '0.15rem',
  },
  sectionHeading: {
    fontSize: '0.875rem',
    fontWeight: '700',
    color: '#0f3a68',
    margin: '0 0 0.65rem 0',
    display: 'flex',
    alignItems: 'center',
    letterSpacing: '-0.005em',
  },
  sectionBody: {},
  basisParagraph: {
    fontSize: '0.875rem',
    lineHeight: '1.62',
    color: '#334155',
    margin: '0 0 0.6rem 0',
  },
  stepsList: {
    margin: '0 0 0 1.15rem',
    padding: 0,
    listStyleType: 'disc',
  },
  stepItem: {
    fontSize: '0.875rem',
    lineHeight: '1.55',
    color: '#334155',
    marginBottom: '0.4rem',
    paddingLeft: '0.15rem',
  },
  sourcesHeading: {
    fontSize: '0.75rem',
    fontWeight: '700',
    color: '#0d9488',
    letterSpacing: '0.04em',
    textTransform: 'uppercase',
    margin: '0 0 0.6rem 0',
    display: 'flex',
    alignItems: 'center',
  },
  sourcesList: {
    display: 'flex',
    flexDirection: 'column',
  },
  sourceRef: {
    fontSize: '0.8125rem',
    fontWeight: '600',
    color: '#0d9488',
    backgroundColor: '#f0fdfa',
    borderRadius: '3px',
    padding: '0.05rem 0.3rem',
    margin: '0 0.1rem',
  },
};
