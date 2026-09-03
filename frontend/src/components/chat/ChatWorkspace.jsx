import React, { useState } from 'react';
import ConversationSidebar from './ConversationSidebar';
import ChatMessages from './ChatMessages';
import ChatInput from './ChatInput';
import { useChatSessions } from '../../hooks/useChatSessions';

export default function ChatWorkspace({ onClose, isExpanded, onToggleExpand }) {
  const {
    sessions,
    activeSessionId,
    messages,
    loadingSessions,
    sending,
    loadingStage,
    error,
    selectSession,
    startNewConversation,
    sendMessage,
    retryLastMessage,
    deleteSession,
  } = useChatSessions();

  const [inputVal, setInputVal] = useState('');
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);

  const handleSend = () => {
    const text = inputVal.trim();
    if (!text || sending) return;
    setInputVal('');
    sendMessage(text);
  };

  const handleSelectSuggestion = (suggestionText) => {
    sendMessage(suggestionText);
  };

  return (
    <div style={styles.workspace} className="nyayasetu-workspace-root">
      {/* ── Desktop & Tablet Persistent Sidebar ── */}
      <div style={styles.desktopSidebarWrapper} className="desktop-sidebar-pane">
        <ConversationSidebar
          sessions={sessions}
          activeSessionId={activeSessionId}
          loadingSessions={loadingSessions}
          onSelectSession={selectSession}
          onNewConversation={startNewConversation}
          onDeleteSession={deleteSession}
        />
      </div>

      {/* ── Mobile Collapsible Sidebar Drawer ── */}
      {mobileSidebarOpen && (
        <div
          style={styles.mobileDrawerBackdrop}
          onClick={() => setMobileSidebarOpen(false)}
        >
          <div
            style={styles.mobileDrawerPane}
            onClick={(e) => e.stopPropagation()}
          >
            <ConversationSidebar
              sessions={sessions}
              activeSessionId={activeSessionId}
              loadingSessions={loadingSessions}
              onSelectSession={selectSession}
              onNewConversation={startNewConversation}
              onDeleteSession={deleteSession}
              onCloseMobile={() => setMobileSidebarOpen(false)}
            />
          </div>
        </div>
      )}

      {/* ── Main Chat Area (Right Side) ── */}
      <main style={styles.mainArea} className="nyayasetu-chat-main">
        {/* Header */}
        <header style={styles.header}>
          <div style={styles.headerLeft}>
            {/* Mobile Sidebar Toggle Button */}
            <button
              type="button"
              onClick={() => setMobileSidebarOpen(true)}
              style={styles.mobileMenuButton}
              className="mobile-sidebar-toggle"
              aria-label="Open conversation history"
              title="Conversations"
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                <line x1="3" y1="12" x2="21" y2="12" />
                <line x1="3" y1="6" x2="21" y2="6" />
                <line x1="3" y1="18" x2="21" y2="18" />
              </svg>
            </button>

            {/* NyayaSetu Logo Mark & Assistant Title */}
            <img
              src="/nyayasetu-mark.png"
              alt="NyayaSetu AI Assistant"
              style={styles.headerLogoMark}
            />

            <div style={styles.headerTitleColumn}>
              <h2 style={styles.headerTitle}>NyayaSetu AI Assistant</h2>
              <span style={styles.headerSubtext}>Indian Statutory Intelligence</span>
            </div>
          </div>

          <div style={styles.headerRight}>
            {/* Online Status Pill */}
            <div style={styles.statusPill}>
              <span style={styles.statusDot}></span>
              <span style={styles.statusText}>Online · Ready to help</span>
            </div>

            {/* Expand / Fullscreen Toggle */}
            {onToggleExpand && (
              <button
                type="button"
                onClick={onToggleExpand}
                style={styles.iconButton}
                title={isExpanded ? 'Restore window size' : 'Expand workspace'}
                aria-label={isExpanded ? 'Restore window size' : 'Expand workspace'}
              >
                {isExpanded ? (
                  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M4 14h6v6" />
                    <path d="M20 10h-6V4" />
                    <path d="M14 10l7-7" />
                    <path d="M3 21l7-7" />
                  </svg>
                ) : (
                  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M15 3h6v6" />
                    <path d="M9 21H3v-6" />
                    <path d="M21 3l-7 7" />
                    <path d="M3 21l7-7" />
                  </svg>
                )}
              </button>
            )}

            {/* Close Button */}
            {onClose && (
              <button
                type="button"
                onClick={onClose}
                style={styles.iconButton}
                title="Close chat workspace"
                aria-label="Close chat workspace"
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                  <line x1="18" y1="6" x2="6" y2="18" />
                  <line x1="6" y1="6" x2="18" y2="18" />
                </svg>
              </button>
            )}
          </div>
        </header>

        {/* Scrollable Chat Area */}
        <ChatMessages
          messages={messages}
          loading={sending}
          loadingStage={loadingStage}
          error={error}
          onRetry={retryLastMessage}
          onSelectSuggestion={handleSelectSuggestion}
        />

        {/* Fixed Sticky Input Area at Bottom */}
        <footer style={styles.footerInputArea}>
          <ChatInput
            value={inputVal}
            onChange={setInputVal}
            onSubmit={handleSend}
            disabled={sending}
          />
        </footer>
      </main>
    </div>
  );
}

const styles = {
  workspace: {
    display: 'flex',
    width: '100%',
    height: '100%',
    backgroundColor: '#ffffff',
    overflow: 'hidden',
  },
  desktopSidebarWrapper: {
    height: '100%',
    display: 'flex',
    flexShrink: 0,
  },
  mobileDrawerBackdrop: {
    position: 'fixed',
    inset: 0,
    zIndex: 1000,
    backgroundColor: 'rgba(15, 23, 42, 0.45)',
    display: 'flex',
  },
  mobileDrawerPane: {
    width: '280px',
    height: '100%',
    backgroundColor: '#ffffff',
    boxShadow: '4px 0 20px rgba(0, 0, 0, 0.15)',
    display: 'flex',
  },
  mainArea: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    height: '100%',
    minWidth: 0,
    backgroundColor: '#fafbfc',
  },
  header: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '0.85rem 1.4rem',
    backgroundColor: '#ffffff',
    borderBottom: '1px solid #e2e8f0',
    flexShrink: 0,
  },
  headerLeft: {
    display: 'flex',
    alignItems: 'center',
    gap: '0.85rem',
  },
  mobileMenuButton: {
    display: 'none', /* Shown via CSS on mobile */
    alignItems: 'center',
    justifyContent: 'center',
    width: '36px',
    height: '36px',
    borderRadius: '6px',
    border: '1px solid #e2e8f0',
    backgroundColor: '#f8fafc',
    color: '#334155',
    cursor: 'pointer',
  },
  headerLogoMark: {
    height: '38px',
    width: 'auto',
    maxHeight: '40px',
    objectFit: 'contain',
    display: 'block',
    background: 'transparent',
    border: 'none',
    boxShadow: 'none',
    flexShrink: 0,
  },
  headerTitleColumn: {
    display: 'flex',
    flexDirection: 'column',
  },
  headerTitle: {
    fontSize: '1rem',
    fontWeight: '700',
    color: '#0f172a',
    margin: 0,
    lineHeight: '1.25',
    letterSpacing: '-0.01em',
  },
  headerSubtext: {
    fontSize: '0.6875rem',
    color: '#64748b',
    fontWeight: '500',
  },
  headerRight: {
    display: 'flex',
    alignItems: 'center',
    gap: '0.65rem',
  },
  statusPill: {
    display: 'flex',
    alignItems: 'center',
    gap: '0.45rem',
    backgroundColor: '#f8fafc',
    borderRadius: '9999px',
    padding: '0.3rem 0.75rem',
    border: '1px solid #e2e8f0',
  },
  statusDot: {
    width: '7px',
    height: '7px',
    borderRadius: '50%',
    backgroundColor: '#22c55e',
    boxShadow: '0 0 5px rgba(34, 197, 94, 0.6)',
  },
  statusText: {
    fontSize: '0.71875rem',
    color: '#475569',
    fontWeight: '500',
    whiteSpace: 'nowrap',
  },
  iconButton: {
    width: '34px',
    height: '34px',
    borderRadius: '6px',
    backgroundColor: '#f8fafc',
    border: '1px solid #e2e8f0',
    color: '#475569',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    cursor: 'pointer',
    transition: 'all 0.15s ease',
  },
  footerInputArea: {
    padding: '0.85rem 1.4rem 1.1rem 1.4rem',
    backgroundColor: '#ffffff',
    borderTop: '1px solid #e2e8f0',
    flexShrink: 0,
  },
};
