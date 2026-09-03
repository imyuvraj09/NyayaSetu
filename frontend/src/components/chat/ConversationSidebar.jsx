import React, { useState } from 'react';
import ConversationItem from './ConversationItem';
import DeleteConfirmModal from './DeleteConfirmModal';

export default function ConversationSidebar({
  sessions,
  activeSessionId,
  loadingSessions,
  onSelectSession,
  onNewConversation,
  onDeleteSession,
  onCloseMobile,
}) {
  const [sessionToDelete, setSessionToDelete] = useState(null);
  const [deleting, setDeleting] = useState(false);

  const handleDeleteConfirm = async () => {
    if (!sessionToDelete) return;
    setDeleting(true);
    await onDeleteSession(sessionToDelete.sessionId);
    setDeleting(false);
    setSessionToDelete(null);
  };

  return (
    <aside style={styles.sidebar} className="nyayasetu-chat-sidebar">
      {/* ── Sidebar Top / Header ── */}
      <div style={styles.topSection}>
        <div style={styles.brandRow}>
          <div style={styles.brand}>
            <img
              src="/nyayasetu-mark.png"
              alt="NyayaSetu"
              style={styles.logoMark}
            />
            <span style={styles.brandText}>NyayaSetu</span>
          </div>

          {/* Close drawer button for mobile view */}
          {onCloseMobile && (
            <button
              type="button"
              onClick={onCloseMobile}
              style={styles.closeMobileBtn}
              aria-label="Close sidebar"
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2">
                <line x1="18" y1="6" x2="6" y2="18" />
                <line x1="6" y1="6" x2="18" y2="18" />
              </svg>
            </button>
          )}
        </div>

        {/* New Conversation Button */}
        <button
          type="button"
          onClick={() => {
            onNewConversation();
            if (onCloseMobile) onCloseMobile();
          }}
          style={styles.newChatButton}
        >
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round">
            <line x1="12" y1="5" x2="12" y2="19" />
            <line x1="5" y1="12" x2="19" y2="12" />
          </svg>
          <span>New Conversation</span>
        </button>
      </div>

      {/* ── Sessions List / Recent Conversations ── */}
      <div style={styles.listContainer} className="sidebar-sessions-scroll">
        <div style={styles.sectionHeading}>RECENT CONVERSATIONS</div>

        {loadingSessions && sessions.length === 0 ? (
          <div style={styles.loadingState}>Loading conversations...</div>
        ) : sessions.length === 0 ? (
          <div style={styles.emptyState}>
            <div style={styles.emptyTitle}>No conversations yet</div>
            <div style={styles.emptyDesc}>
              Start a legal conversation to explore Indian statutory knowledge.
            </div>
          </div>
        ) : (
          <div style={styles.itemsList}>
            {sessions.map((s) => (
              <ConversationItem
                key={s.sessionId}
                session={s}
                isActive={s.sessionId === activeSessionId}
                onSelect={(id) => {
                  onSelectSession(id);
                  if (onCloseMobile) onCloseMobile();
                }}
                onDeleteRequest={(session) => setSessionToDelete(session)}
              />
            ))}
          </div>
        )}
      </div>

      {/* ── Delete Confirmation Dialog ── */}
      <DeleteConfirmModal
        isOpen={!!sessionToDelete}
        title={sessionToDelete?.title}
        onConfirm={handleDeleteConfirm}
        onCancel={() => setSessionToDelete(null)}
        deleting={deleting}
      />
    </aside>
  );
}

const styles = {
  sidebar: {
    width: '260px',
    height: '100%',
    backgroundColor: '#f8fafc',
    borderRight: '1px solid #e2e8f0',
    display: 'flex',
    flexDirection: 'column',
    flexShrink: 0,
    userSelect: 'none',
  },
  topSection: {
    padding: '1.1rem 1rem 0.85rem 1rem',
    borderBottom: '1px solid #edf2f7',
    display: 'flex',
    flexDirection: 'column',
    gap: '0.85rem',
  },
  brandRow: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  brand: {
    display: 'flex',
    alignItems: 'center',
    gap: '0.45rem',
  },
  logoMark: {
    height: '26px',
    width: 'auto',
    maxHeight: '28px',
    objectFit: 'contain',
    display: 'block',
    background: 'transparent',
    border: 'none',
  },
  brandText: {
    fontSize: '1rem',
    fontWeight: '800',
    color: '#0f172a',
    letterSpacing: '-0.02em',
  },
  closeMobileBtn: {
    width: '32px',
    height: '32px',
    borderRadius: '6px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: 'transparent',
    border: 'none',
    color: '#64748b',
    cursor: 'pointer',
  },
  newChatButton: {
    width: '100%',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: '0.5rem',
    padding: '0.6rem 0.85rem',
    backgroundColor: '#ffffff',
    border: '1px solid #cbd5e1',
    borderRadius: '8px',
    color: '#0f3a68',
    fontSize: '0.84375rem',
    fontWeight: '600',
    cursor: 'pointer',
    boxShadow: '0 1px 3px rgba(15, 23, 42, 0.04)',
    transition: 'all 0.15s ease',
  },
  listContainer: {
    flex: 1,
    overflowY: 'auto',
    padding: '0.9rem 0.65rem',
  },
  sectionHeading: {
    fontSize: '0.6875rem',
    fontWeight: '700',
    color: '#94a3b8',
    letterSpacing: '0.07em',
    padding: '0 0.45rem 0.65rem 0.45rem',
  },
  itemsList: {
    display: 'flex',
    flexDirection: 'column',
  },
  loadingState: {
    padding: '1.25rem 0.5rem',
    fontSize: '0.78125rem',
    color: '#94a3b8',
    textAlign: 'center',
  },
  emptyState: {
    padding: '1.5rem 0.5rem',
    textAlign: 'center',
  },
  emptyTitle: {
    fontSize: '0.8125rem',
    fontWeight: '600',
    color: '#64748b',
    marginBottom: '0.25rem',
  },
  emptyDesc: {
    fontSize: '0.71875rem',
    color: '#94a3b8',
    lineHeight: '1.45',
  },
};
