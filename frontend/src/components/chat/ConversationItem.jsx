import React, { useState } from 'react';

export default function ConversationItem({
  session,
  isActive,
  onSelect,
  onDeleteRequest,
}) {
  const [isHovered, setIsHovered] = useState(false);

  const title = session.title || 'Legal Inquiry';
  const dateStr = session.updatedAt || session.createdAt;

  const formatRelativeTime = (timestamp) => {
    if (!timestamp) return '';
    try {
      const d = new Date(timestamp);
      const now = new Date();
      const diffMs = now - d;
      const diffMins = Math.floor(diffMs / (1000 * 60));
      const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
      const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

      if (diffMins < 2) return 'Just now';
      if (diffMins < 60) return `${diffMins}m ago`;
      if (diffHours < 24) return `${diffHours}h ago`;
      if (diffDays === 1) return 'Yesterday';
      if (diffDays < 7) return `${diffDays}d ago`;
      return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    } catch {
      return '';
    }
  };

  const relativeTime = formatRelativeTime(dateStr);

  return (
    <div
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      style={{
        ...styles.itemContainer,
        ...(isActive ? styles.itemActive : isHovered ? styles.itemHovered : {}),
      }}
    >
      <button
        type="button"
        onClick={() => onSelect(session.sessionId)}
        style={styles.selectButton}
        title={title}
      >
        <div style={styles.titleRow}>
          <svg
            width="14"
            height="14"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2.2"
            strokeLinecap="round"
            strokeLinejoin="round"
            style={{
              ...styles.chatIcon,
              color: isActive ? '#0f3a68' : '#64748b',
            }}
          >
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
          </svg>
          <span
            style={{
              ...styles.titleText,
              color: isActive ? '#0f3a68' : '#1e293b',
              fontWeight: isActive ? '600' : '500',
            }}
          >
            {title}
          </span>
        </div>

        {relativeTime && (
          <span style={styles.timeText}>{relativeTime}</span>
        )}
      </button>

      {/* Delete Trigger Button */}
      <button
        type="button"
        onClick={(e) => {
          e.stopPropagation();
          onDeleteRequest(session);
        }}
        style={{
          ...styles.deleteButton,
          opacity: isHovered || isActive ? 1 : 0,
        }}
        aria-label={`Delete conversation ${title}`}
        title="Delete conversation"
      >
        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
          <polyline points="3 6 5 6 21 6" />
          <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
        </svg>
      </button>
    </div>
  );
}

const styles = {
  itemContainer: {
    position: 'relative',
    display: 'flex',
    alignItems: 'center',
    borderRadius: '6px',
    border: '1px solid transparent',
    backgroundColor: 'transparent',
    marginBottom: '0.25rem',
    transition: 'all 0.15s ease',
  },
  itemHovered: {
    backgroundColor: '#f1f5f9',
  },
  itemActive: {
    backgroundColor: '#e6f0fa',
    borderColor: '#bfdbfe',
    boxShadow: 'inset 3px 0 0 #0f3a68',
  },
  selectButton: {
    flex: 1,
    minWidth: 0,
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'flex-start',
    gap: '0.2rem',
    padding: '0.6rem 0.65rem 0.6rem 0.75rem',
    backgroundColor: 'transparent',
    border: 'none',
    cursor: 'pointer',
    textAlign: 'left',
  },
  titleRow: {
    display: 'flex',
    alignItems: 'center',
    gap: '0.55rem',
    width: '100%',
    minWidth: 0,
  },
  chatIcon: {
    flexShrink: 0,
  },
  titleText: {
    fontSize: '0.8125rem', /* 13px */
    whiteSpace: 'nowrap',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    lineHeight: '1.3',
    flex: 1,
  },
  timeText: {
    fontSize: '0.6875rem', /* 11px */
    color: '#94a3b8',
    paddingLeft: '1.45rem',
  },
  deleteButton: {
    width: '28px',
    height: '28px',
    borderRadius: '4px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: 'transparent',
    border: 'none',
    color: '#94a3b8',
    cursor: 'pointer',
    marginRight: '0.35rem',
    transition: 'color 0.15s ease, background-color 0.15s ease, opacity 0.15s ease',
    flexShrink: 0,
  },
};
