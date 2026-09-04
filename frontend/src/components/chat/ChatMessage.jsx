import React from 'react';
import LegalMarkdown from './LegalMarkdown';
import SourceCitation from './SourceCitation';
import AssistantLegalResponse, { parseStructuredResponse } from './AssistantLegalResponse';

export default function ChatMessage({ message }) {
  const isUser = message.role === 'user';
  const sources = message.sources || [];

  // Safely coerce content to string for error resilience
  const rawContent = message.content;
  const safeContent =
    typeof rawContent === 'string'
      ? rawContent
      : rawContent && typeof rawContent === 'object'
        ? rawContent.message || rawContent.error || JSON.stringify(rawContent)
        : String(rawContent || '');

  // Attempt to parse structured JSON format for assistant messages
  const structured = !isUser ? parseStructuredResponse(safeContent) : null;

  return (
    <div
      style={{
        ...styles.row,
        justifyContent: isUser ? 'flex-end' : 'flex-start',
      }}
    >
      {isUser ? (
        /* ── User Message Bubble ── */
        <div style={{ ...styles.bubble, ...styles.userBubble }}>
          <div style={styles.userText}>{safeContent}</div>
          {message.timestamp && (
            <div style={{ ...styles.timestamp, textAlign: 'right', color: 'rgba(255,255,255,0.75)' }}>
              {message.timestamp}
            </div>
          )}
        </div>
      ) : structured ? (
        /* ── Structured Legal Response Card ── */
        <div style={styles.assistantCardWrapper}>
          <AssistantLegalResponse
            structured={structured}
            sources={sources}
            ragMetadata={message.ragMetadata || message.metadata || {}}
          />
          {message.timestamp && (
            <div style={{ ...styles.timestamp, textAlign: 'left', color: '#94a3b8' }}>
              {message.timestamp}
            </div>
          )}
        </div>
      ) : (
        /* ── Legacy / Fallback Plain-text Assistant Bubble ── */
        <div style={{ ...styles.bubble, ...styles.assistantBubble }}>
          <div style={styles.assistantContent}>
            {((message.ragMetadata?.generationStatus === 'RETRIEVAL_ONLY') || (message.metadata?.generationStatus === 'RETRIEVAL_ONLY')) && (
              <div style={styles.fallbackStatusNotice}>
                AI synthesis temporarily unavailable; answer limited to retrieved legal evidence.
              </div>
            )}
            {((message.ragMetadata?.generationStatus === 'RATE_LIMITED') || (message.metadata?.generationStatus === 'RATE_LIMITED')) && (
              <div style={{ ...styles.fallbackStatusNotice, ...styles.fallbackStatusNoticeAmber }}>
                AI synthesis is temporarily unavailable. The retrieved legal evidence is shown below.
              </div>
            )}
            <LegalMarkdown content={safeContent} />

            {/* Statutory Citations Section for legacy messages */}
            {sources.length > 0 && (
              <div style={styles.sourcesWrapper}>
                <div style={styles.sourcesHeader}>
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4">
                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                    <polyline points="14 2 14 8 20 8" />
                  </svg>
                  <span>VERIFIED STATUTORY CITATIONS ({sources.length})</span>
                </div>

                <div style={styles.sourcesList}>
                  {sources.map((src, idx) => (
                    <SourceCitation key={idx} source={src} index={idx} />
                  ))}
                </div>
              </div>
            )}
          </div>

          {message.timestamp && (
            <div style={{ ...styles.timestamp, textAlign: 'left', color: '#94a3b8' }}>
              {message.timestamp}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

const styles = {
  row: {
    display: 'flex',
    width: '100%',
    marginBottom: '0.9rem',
  },
  bubble: {
    maxWidth: '82%',
    padding: '1.15rem 1.35rem',
    wordBreak: 'break-word',
    transition: 'all 0.15s ease',
  },
  userBubble: {
    backgroundColor: '#0f3a68',
    color: '#ffffff',
    borderRadius: '16px 16px 4px 16px',
    boxShadow: '0 2px 10px rgba(15, 58, 104, 0.18)',
    maxWidth: '75%',
  },
  userText: {
    fontSize: '0.9375rem',
    lineHeight: '1.55',
    whiteSpace: 'pre-wrap',
  },
  assistantBubble: {
    backgroundColor: '#ffffff',
    color: '#1e293b',
    borderRadius: '16px 16px 16px 4px',
    border: '1px solid #e2e8f0',
    boxShadow: '0 2px 8px rgba(15, 23, 42, 0.04)',
    maxWidth: '85%',
  },
  assistantCardWrapper: {
    maxWidth: '88%',
    display: 'flex',
    flexDirection: 'column',
    gap: '0.35rem',
    transition: 'all 0.15s ease',
  },
  assistantContent: {
    display: 'flex',
    flexDirection: 'column',
  },
  timestamp: {
    fontSize: '0.6875rem',
    marginTop: '0.55rem',
    fontWeight: '500',
    letterSpacing: '0.01em',
  },
  sourcesWrapper: {
    marginTop: '1rem',
    paddingTop: '0.85rem',
    borderTop: '1px solid #f1f5f9',
  },
  sourcesHeader: {
    display: 'flex',
    alignItems: 'center',
    gap: '0.4rem',
    fontSize: '0.6875rem',
    fontWeight: '700',
    color: '#0d9488',
    letterSpacing: '0.06em',
    marginBottom: '0.6rem',
    textTransform: 'uppercase',
  },
  sourcesList: {
    display: 'flex',
    flexDirection: 'column',
  },
  fallbackStatusNotice: {
    padding: '0.55rem 0.85rem',
    marginBottom: '0.75rem',
    backgroundColor: '#f0fdfa',
    border: '1px solid #ccfbf1',
    borderRadius: '6px',
    color: '#0f766e',
    fontSize: '0.8125rem',
    fontWeight: '500',
    lineHeight: '1.4',
  },
  fallbackStatusNoticeAmber: {
    backgroundColor: '#fffbeb',
    border: '1px solid #fef3c7',
    color: '#b45309',
  },
};
