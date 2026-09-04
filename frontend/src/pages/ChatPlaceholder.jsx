import React, { useState, useRef, useEffect, useCallback } from 'react';

export default function ChatPlaceholder({ onBackHome }) {
  const [messages, setMessages] = useState([
    {
      id: 'welcome',
      role: 'assistant',
      content:
        'Hello! I\'m NyayaSetu, your AI-powered legal information assistant.\n\nHow can I help you explore Indian legal information today?',
      sources: [],
    },
  ]);
  const [inputQuery, setInputQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [sessionId, setSessionId] = useState(null);
  const [errorMsg, setErrorMsg] = useState(null);
  const messagesEndRef = useRef(null);

  const sampleQueries = [
    'What is the punishment for theft under Bharatiya Nyaya Sanhita?',
    'What fundamental rights are guaranteed by the Constitution of India?',
    'What constitutes electronic evidence under Bharatiya Sakshya Adhiniyam?',
    'What are the consumer redressal commission pecuniary limits under CPA 2019?',
  ];

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  const handleSend = useCallback(async (queryToSend) => {
    const text = (queryToSend || inputQuery).trim();
    if (!text || loading) return;

    setErrorMsg(null);
    setInputQuery('');

    // Append user query immediately
    const userMsg = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: text,
      sources: [],
    };
    setMessages((prev) => [...prev, userMsg]);
    setLoading(true);

    try {
      let currentSessionId = sessionId;

      // 1. Create session if not already existing
      if (!currentSessionId) {
        const createRes = await fetch('http://localhost:3000/api/chats', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ title: text.slice(0, 60) }),
        });

        if (createRes.ok) {
          const createData = await createRes.json();
          currentSessionId = createData.data?.sessionId;
          setSessionId(currentSessionId);
        }
      }

      // 2. Post query to backend API
      if (currentSessionId) {
        const msgRes = await fetch(`http://localhost:3000/api/chats/${currentSessionId}/messages`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ query: text }),
        });

        if (msgRes.ok) {
          const data = await msgRes.json();
          const assistantPayload = data.data?.message;
          setMessages((prev) => [
            ...prev,
            {
              id: assistantPayload?._id || `asst-${Date.now()}`,
              role: 'assistant',
              content: assistantPayload?.content || 'No response content returned.',
              sources: assistantPayload?.sources || [],
            },
          ]);
          setLoading(false);
          return;
        }
      }

      // Fallback: If backend is not currently running locally, show informative research card
      setMessages((prev) => [
        ...prev,
        {
          id: `asst-${Date.now()}`,
          role: 'assistant',
          content:
            'NyayaSetu Backend connection notice: The Node.js application gateway (http://localhost:3000) or Python RAG service is currently not reachable in this local browser session. Start the backend with `npm start` in the backend directory to interact with live indexed statutes.',
          sources: [],
        },
      ]);
    } catch {
      setErrorMsg('Unable to reach Node.js gateway at http://localhost:3000. Start the backend to execute live queries.');
    } finally {
      setLoading(false);
    }
  }, [inputQuery, loading, sessionId]);

  const handleClear = () => {
    setMessages([
      {
        id: 'welcome',
        role: 'assistant',
        content:
          'Conversation cleared. You can ask a new legal question regarding Indian statutory enactments.',
        sources: [],
      },
    ]);
    setSessionId(null);
    setErrorMsg(null);
  };

  const formatTime = () => {
    const now = new Date();
    return now.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: true });
  };

  return (
    <div style={styles.chatPage} className="chat-page-root">
      <div style={styles.chatShell} className="chat-shell-root">
        {/* ── Chat Header ── */}
        <div style={styles.chatHeader}>
          <div style={styles.headerLeft}>
            <div style={styles.aiAvatar}>
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M12 3v18" />
                <path d="M5 6l14 0" />
                <path d="M5 6l-3 7a4 4 0 0 0 6 0l-3 -7" />
                <path d="M19 6l-3 7a4 4 0 0 0 6 0l-3 -7" />
                <path d="M9 21h6" />
              </svg>
            </div>
            <div style={styles.headerIdentity}>
              <span style={styles.headerName}>NyayaSetu AI Assistant</span>
              <div style={styles.statusRow}>
                <span style={styles.statusDot}></span>
                <span style={styles.statusText}>Online · Ready to assist</span>
              </div>
            </div>
          </div>

          <div style={styles.headerRight}>
            <button
              onClick={handleClear}
              style={styles.headerAction}
              title="Clear current legal conversation"
              aria-label="Clear conversation"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M3 6h18" />
                <path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
                <path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6" />
                <line x1="10" y1="11" x2="10" y2="17" />
                <line x1="14" y1="11" x2="14" y2="17" />
              </svg>
            </button>
            <button
              onClick={onBackHome}
              style={styles.headerAction}
              title="Back to homepage"
              aria-label="Close chat and return to homepage"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <line x1="18" y1="6" x2="6" y2="18" />
                <line x1="6" y1="6" x2="18" y2="18" />
              </svg>
            </button>
          </div>
        </div>

        {/* ── Error Banner ── */}
        {errorMsg && (
          <div style={styles.errorBanner}>
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="10" />
              <line x1="12" y1="8" x2="12" y2="12" />
              <line x1="12" y1="16" x2="12.01" y2="16" />
            </svg>
            <span>{errorMsg}</span>
          </div>
        )}

        {/* ── Message Conversation Area ── */}
        <div style={styles.conversationArea} className="chat-scroll-area">
          {messages.map((m) => (
            <div
              key={m.id}
              style={{
                ...styles.messageRow,
                justifyContent: m.role === 'user' ? 'flex-end' : 'flex-start',
              }}
            >
              {m.role === 'assistant' && (
                <div style={styles.msgAvatarSmall}>
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M12 3v18" />
                    <path d="M5 6l14 0" />
                    <path d="M5 6l-3 7a4 4 0 0 0 6 0l-3 -7" />
                    <path d="M19 6l-3 7a4 4 0 0 0 6 0l-3 -7" />
                    <path d="M9 21h6" />
                  </svg>
                </div>
              )}

              <div
                style={{
                  ...styles.messageBubble,
                  ...(m.role === 'user' ? styles.userBubble : styles.assistantBubble),
                }}
              >
                <div style={styles.bubbleContent}>{m.content}</div>

                {/* Sources / Citations */}
                {m.sources && m.sources.length > 0 && (
                  <div style={styles.sourceSection}>
                    <div style={styles.sourceHeader}>
                      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                        <polyline points="14 2 14 8 20 8" />
                        <line x1="16" y1="13" x2="8" y2="13" />
                        <line x1="16" y1="17" x2="8" y2="17" />
                      </svg>
                      <span>VERIFIED SOURCES ({m.sources.length})</span>
                    </div>
                    {m.sources.map((s, idx) => (
                      <div key={idx} style={styles.sourceCard}>
                        <div style={styles.sourceTitle}>
                          {s.sourceLabel} · {s.documentName}
                          {s.pageNumbers && s.pageNumbers.length > 0 && ` (Page ${s.pageNumbers.join(', ')})`}
                        </div>
                        {s.snippet && <div style={styles.sourceSnippet}>"{s.snippet}"</div>}
                      </div>
                    ))}
                  </div>
                )}

                <div style={styles.timestamp}>{formatTime()}</div>
              </div>
            </div>
          ))}

          {/* Loading Indicator */}
          {loading && (
            <div style={styles.messageRow}>
              <div style={styles.msgAvatarSmall}>
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M12 3v18" />
                  <path d="M5 6l14 0" />
                  <path d="M5 6l-3 7a4 4 0 0 0 6 0l-3 -7" />
                  <path d="M19 6l-3 7a4 4 0 0 0 6 0l-3 -7" />
                  <path d="M9 21h6" />
                </svg>
              </div>
              <div style={styles.loadingBubble}>
                <div style={styles.loadingDots}>
                  <span className="chat-dot chat-dot-1" style={styles.dot}></span>
                  <span className="chat-dot chat-dot-2" style={{ ...styles.dot, animationDelay: '0.15s' }}></span>
                  <span className="chat-dot chat-dot-3" style={{ ...styles.dot, animationDelay: '0.3s' }}></span>
                </div>
                <span style={styles.loadingText}>Searching statutory database & reranking passages...</span>
              </div>
            </div>
          )}

          {/* Suggested Queries (shown on initial state) */}
          {messages.length <= 2 && !loading && (
            <div style={styles.suggestionsContainer}>
              <div style={styles.suggestionsLabel}>Suggested legal research topics</div>
              <div style={styles.suggestionsGrid}>
                {sampleQueries.map((q, i) => (
                  <button
                    key={i}
                    onClick={() => handleSend(q)}
                    style={styles.suggestionChip}
                    className="chat-suggestion-chip"
                  >
                    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ flexShrink: 0, opacity: 0.5 }}>
                      <circle cx="11" cy="11" r="8" />
                      <line x1="21" y1="21" x2="16.65" y2="16.65" />
                    </svg>
                    <span>{q}</span>
                  </button>
                ))}
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* ── Input Area ── */}
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSend();
          }}
          style={styles.inputArea}
        >
          <div style={styles.inputWrapper}>
            <input
              type="text"
              placeholder="Ask anything about Indian legal information..."
              value={inputQuery}
              onChange={(e) => setInputQuery(e.target.value)}
              disabled={loading}
              style={styles.inputField}
              className="chat-input-field"
              autoComplete="off"
            />
            <button
              type="submit"
              disabled={!inputQuery.trim() || loading}
              style={{
                ...styles.sendBtn,
                opacity: !inputQuery.trim() || loading ? 0.4 : 1,
                cursor: !inputQuery.trim() || loading ? 'not-allowed' : 'pointer',
              }}
              aria-label="Send message"
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                <line x1="22" y1="2" x2="11" y2="13" />
                <polygon points="22 2 15 22 11 13 2 9 22 2" />
              </svg>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

const styles = {
  /* ── Page Wrapper ── */
  chatPage: {
    backgroundColor: '#0f1729',
    minHeight: 'calc(100vh - var(--header-height, 58px))',
    display: 'flex',
    alignItems: 'flex-start',
    justifyContent: 'center',
    padding: '2rem 1.5rem',
  },

  /* ── Chat Shell ── */
  chatShell: {
    width: '100%',
    maxWidth: '820px',
    backgroundColor: '#1a2332',
    borderRadius: '8px',
    border: '1px solid #253040',
    display: 'flex',
    flexDirection: 'column',
    height: 'calc(100vh - var(--header-height, 58px) - 4rem)',
    minHeight: '480px',
    overflow: 'hidden',
  },

  /* ── Header ── */
  chatHeader: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '0.875rem 1.25rem',
    borderBottom: '1px solid #253040',
    backgroundColor: '#1e2d3d',
    flexShrink: 0,
  },
  headerLeft: {
    display: 'flex',
    alignItems: 'center',
    gap: '0.75rem',
  },
  aiAvatar: {
    width: '36px',
    height: '36px',
    borderRadius: '8px',
    backgroundColor: '#0d9488',
    color: '#ffffff',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    flexShrink: 0,
  },
  headerIdentity: {
    display: 'flex',
    flexDirection: 'column',
    gap: '0.15rem',
  },
  headerName: {
    fontSize: '0.9375rem',
    fontWeight: '600',
    color: '#e2e8f0',
    letterSpacing: '-0.01em',
  },
  statusRow: {
    display: 'flex',
    alignItems: 'center',
    gap: '0.375rem',
  },
  statusDot: {
    width: '7px',
    height: '7px',
    borderRadius: '50%',
    backgroundColor: '#22c55e',
    display: 'inline-block',
    flexShrink: 0,
  },
  statusText: {
    fontSize: '0.6875rem',
    color: '#64748b',
    fontWeight: '500',
  },
  headerRight: {
    display: 'flex',
    alignItems: 'center',
    gap: '0.35rem',
  },
  headerAction: {
    width: '32px',
    height: '32px',
    borderRadius: '6px',
    color: '#64748b',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    transition: 'all 0.15s ease',
    backgroundColor: 'transparent',
    border: 'none',
    cursor: 'pointer',
  },

  /* ── Error Banner ── */
  errorBanner: {
    display: 'flex',
    alignItems: 'center',
    gap: '0.5rem',
    padding: '0.625rem 1.25rem',
    backgroundColor: '#2d1a1a',
    borderBottom: '1px solid #3d2020',
    color: '#fca5a5',
    fontSize: '0.8125rem',
    flexShrink: 0,
  },

  /* ── Conversation Area ── */
  conversationArea: {
    flex: 1,
    overflowY: 'auto',
    padding: '1.25rem',
    display: 'flex',
    flexDirection: 'column',
    gap: '1rem',
  },

  /* ── Messages ── */
  messageRow: {
    display: 'flex',
    alignItems: 'flex-start',
    gap: '0.625rem',
    width: '100%',
  },
  msgAvatarSmall: {
    width: '28px',
    height: '28px',
    borderRadius: '6px',
    backgroundColor: '#253040',
    color: '#0d9488',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    flexShrink: 0,
    marginTop: '2px',
  },
  messageBubble: {
    maxWidth: '78%',
    padding: '0.875rem 1.125rem',
    borderRadius: '6px',
    lineHeight: '1.6',
    fontSize: '0.875rem',
  },
  userBubble: {
    backgroundColor: '#0d9488',
    color: '#ffffff',
    borderRadius: '6px 6px 2px 6px',
  },
  assistantBubble: {
    backgroundColor: '#1e2d3d',
    color: '#cbd5e1',
    border: '1px solid #253040',
    borderRadius: '6px 6px 6px 2px',
    whiteSpace: 'pre-wrap',
  },
  bubbleContent: {
    lineHeight: '1.6',
    wordBreak: 'break-word',
  },
  timestamp: {
    fontSize: '0.625rem',
    color: '#475569',
    marginTop: '0.5rem',
    textAlign: 'right',
  },

  /* ── Sources ── */
  sourceSection: {
    marginTop: '0.875rem',
    paddingTop: '0.75rem',
    borderTop: '1px solid #253040',
  },
  sourceHeader: {
    display: 'flex',
    alignItems: 'center',
    gap: '0.375rem',
    fontSize: '0.625rem',
    fontWeight: '700',
    letterSpacing: '0.08em',
    color: '#0d9488',
    marginBottom: '0.5rem',
    textTransform: 'uppercase',
  },
  sourceCard: {
    backgroundColor: '#162030',
    border: '1px solid #253040',
    borderRadius: '4px',
    padding: '0.5rem 0.75rem',
    fontSize: '0.75rem',
    marginBottom: '0.3rem',
  },
  sourceTitle: {
    fontWeight: '600',
    color: '#94a3b8',
  },
  sourceSnippet: {
    fontSize: '0.6875rem',
    color: '#64748b',
    marginTop: '0.2rem',
    fontStyle: 'italic',
  },

  /* ── Loading ── */
  loadingBubble: {
    display: 'flex',
    alignItems: 'center',
    gap: '0.75rem',
    padding: '0.875rem 1.125rem',
    backgroundColor: '#1e2d3d',
    border: '1px solid #253040',
    borderRadius: '6px 6px 6px 2px',
  },
  loadingDots: {
    display: 'flex',
    alignItems: 'center',
    gap: '4px',
  },
  dot: {
    width: '6px',
    height: '6px',
    borderRadius: '50%',
    backgroundColor: '#0d9488',
    display: 'inline-block',
    animation: 'chatDotPulse 1.2s ease-in-out infinite',
  },
  loadingText: {
    fontSize: '0.8125rem',
    color: '#64748b',
  },

  /* ── Suggestions ── */
  suggestionsContainer: {
    marginTop: '0.5rem',
    padding: '1rem',
    backgroundColor: '#162030',
    borderRadius: '6px',
    border: '1px solid #253040',
  },
  suggestionsLabel: {
    fontSize: '0.6875rem',
    fontWeight: '700',
    letterSpacing: '0.06em',
    color: '#64748b',
    marginBottom: '0.75rem',
    textTransform: 'uppercase',
  },
  suggestionsGrid: {
    display: 'flex',
    flexDirection: 'column',
    gap: '0.375rem',
  },
  suggestionChip: {
    display: 'flex',
    alignItems: 'center',
    gap: '0.5rem',
    textAlign: 'left',
    padding: '0.625rem 0.875rem',
    backgroundColor: '#1a2332',
    border: '1px solid #253040',
    borderRadius: '4px',
    fontSize: '0.8125rem',
    color: '#94a3b8',
    cursor: 'pointer',
    transition: 'all 0.15s ease',
  },

  /* ── Input Area ── */
  inputArea: {
    padding: '0.875rem 1.25rem',
    borderTop: '1px solid #253040',
    backgroundColor: '#1e2d3d',
    flexShrink: 0,
  },
  inputWrapper: {
    display: 'flex',
    alignItems: 'center',
    gap: '0.625rem',
    backgroundColor: '#0f1729',
    borderRadius: '6px',
    border: '1px solid #253040',
    padding: '0.25rem 0.25rem 0.25rem 1rem',
  },
  inputField: {
    flex: 1,
    backgroundColor: 'transparent',
    border: 'none',
    outline: 'none',
    color: '#e2e8f0',
    fontSize: '0.875rem',
    padding: '0.625rem 0',
    fontFamily: 'inherit',
  },
  sendBtn: {
    width: '38px',
    height: '38px',
    borderRadius: '6px',
    backgroundColor: '#0d9488',
    color: '#ffffff',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    border: 'none',
    flexShrink: 0,
    transition: 'opacity 0.15s ease, background-color 0.15s ease',
  },
};
