import React, { useRef, useEffect } from 'react';
import ChatMessage from './ChatMessage';
import ChatEmptyState from './ChatEmptyState';

export default function ChatMessages({
  messages,
  loading,
  loadingStage,
  error,
  onRetry,
  onSelectSuggestion,
}) {
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading, error]);

  if (messages.length === 0 && !loading) {
    return (
      <div style={styles.scrollArea}>
        <ChatEmptyState onSelectSuggestion={onSelectSuggestion} />
      </div>
    );
  }

  return (
    <div style={styles.scrollArea} className="modal-chat-scroll">
      {messages.map((m) => (
        <ChatMessage key={m.id} message={m} />
      ))}

      {/* Two-stage loading state */}
      {loading && (
        <div style={styles.loadingContainer}>
          <div style={styles.loadingBubble}>
            <div style={styles.loadingDots}>
              <span style={styles.dot1}></span>
              <span style={styles.dot2}></span>
              <span style={styles.dot3}></span>
            </div>
            <span style={styles.loadingText}>
              {loadingStage || 'Searching legal sources...'}
            </span>
          </div>
        </div>
      )}

      {/* Inline Error Card with Retry Button */}
      {error && (
        <div style={styles.errorCard}>
          <div style={styles.errorIcon}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#ef4444" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="10" />
              <line x1="12" y1="8" x2="12" y2="12" />
              <line x1="12" y1="16" x2="12.01" y2="16" />
            </svg>
          </div>
          <div style={styles.errorContent}>
            <div style={styles.errorTitle}>Unable to generate a response</div>
            <div style={styles.errorMessage}>
              {typeof error === 'string' ? error : error?.message || 'An unexpected error occurred.'}
            </div>
            {onRetry && (
              <button type="button" onClick={onRetry} style={styles.retryButton}>
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round">
                  <polyline points="23 4 23 10 17 10" />
                  <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10" />
                </svg>
                <span>Retry</span>
              </button>
            )}
          </div>
        </div>
      )}

      {/* Unanswered User Inquiry Card with Generate Button */}
      {!loading && !error && messages.length > 0 && messages[messages.length - 1].role === 'user' && (
        <div style={styles.unansweredCard}>
          <div style={styles.unansweredIcon}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#0f3a68" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="10" />
              <polyline points="12 6 12 12 16 14" />
            </svg>
          </div>
          <div style={styles.unansweredContent}>
            <div style={styles.unansweredTitle}>Pending Legal Analysis</div>
            <div style={styles.unansweredText}>
              No legal response was generated for this inquiry (the previous request may have timed out or interrupted).
            </div>
            {onRetry && (
              <button type="button" onClick={onRetry} style={styles.generateButton}>
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round">
                  <polyline points="23 4 23 10 17 10" />
                  <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10" />
                </svg>
                <span>Generate Legal Response</span>
              </button>
            )}
          </div>
        </div>
      )}

      <div ref={bottomRef} style={{ height: '1px' }} />
    </div>
  );
}

const styles = {
  scrollArea: {
    flex: 1,
    overflowY: 'auto',
    padding: '1.25rem 1.6rem',
    display: 'flex',
    flexDirection: 'column',
    backgroundColor: '#fafbfc',
  },
  loadingContainer: {
    display: 'flex',
    width: '100%',
    marginBottom: '0.85rem',
  },
  loadingBubble: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '0.65rem',
    padding: '0.8rem 1.25rem',
    backgroundColor: '#ffffff',
    borderRadius: '12px',
    border: '1px solid #e2e8f0',
    boxShadow: '0 2px 8px rgba(15, 23, 42, 0.04)',
  },
  loadingDots: {
    display: 'flex',
    alignItems: 'center',
    gap: '4px',
  },
  dot1: {
    width: '6px',
    height: '6px',
    borderRadius: '50%',
    backgroundColor: '#0d9488',
    animation: 'chatDotPulse 1.2s ease-in-out infinite',
  },
  dot2: {
    width: '6px',
    height: '6px',
    borderRadius: '50%',
    backgroundColor: '#0d9488',
    animation: 'chatDotPulse 1.2s ease-in-out 0.2s infinite',
  },
  dot3: {
    width: '6px',
    height: '6px',
    borderRadius: '50%',
    backgroundColor: '#0d9488',
    animation: 'chatDotPulse 1.2s ease-in-out 0.4s infinite',
  },
  loadingText: {
    fontSize: '0.8125rem',
    color: '#475569',
    fontWeight: '500',
  },
  errorCard: {
    display: 'flex',
    alignItems: 'flex-start',
    gap: '0.75rem',
    padding: '0.95rem 1.2rem',
    backgroundColor: '#fef2f2',
    border: '1px solid #fecaca',
    borderRadius: '10px',
    marginBottom: '1rem',
  },
  errorIcon: {
    flexShrink: 0,
    marginTop: '0.1rem',
  },
  errorContent: {
    display: 'flex',
    flexDirection: 'column',
    gap: '0.3rem',
    flex: 1,
  },
  errorTitle: {
    fontSize: '0.84375rem',
    fontWeight: '700',
    color: '#991b1b',
  },
  errorMessage: {
    fontSize: '0.78125rem',
    color: '#b91c1c',
    lineHeight: '1.45',
  },
  retryButton: {
    alignSelf: 'flex-start',
    display: 'inline-flex',
    alignItems: 'center',
    gap: '0.4rem',
    marginTop: '0.35rem',
    padding: '0.35rem 0.75rem',
    backgroundColor: '#ffffff',
    border: '1px solid #fca5a5',
    borderRadius: '6px',
    color: '#b91c1c',
    fontSize: '0.75rem',
    fontWeight: '600',
    cursor: 'pointer',
    boxShadow: '0 1px 2px rgba(0, 0, 0, 0.05)',
  },
  unansweredCard: {
    display: 'flex',
    alignItems: 'flex-start',
    gap: '0.75rem',
    padding: '0.95rem 1.2rem',
    backgroundColor: '#f0f9ff',
    border: '1px solid #bae6fd',
    borderRadius: '10px',
    marginBottom: '1rem',
  },
  unansweredIcon: {
    flexShrink: 0,
    marginTop: '0.1rem',
  },
  unansweredContent: {
    display: 'flex',
    flexDirection: 'column',
    gap: '0.3rem',
    flex: 1,
  },
  unansweredTitle: {
    fontSize: '0.84375rem',
    fontWeight: '700',
    color: '#0369a1',
  },
  unansweredText: {
    fontSize: '0.78125rem',
    color: '#0284c7',
    lineHeight: '1.45',
  },
  generateButton: {
    alignSelf: 'flex-start',
    display: 'inline-flex',
    alignItems: 'center',
    gap: '0.4rem',
    marginTop: '0.45rem',
    padding: '0.4rem 0.85rem',
    backgroundColor: '#0f3a68',
    border: 'none',
    borderRadius: '6px',
    color: '#ffffff',
    fontSize: '0.78125rem',
    fontWeight: '600',
    cursor: 'pointer',
    boxShadow: '0 1px 4px rgba(15, 58, 104, 0.2)',
  },
};
