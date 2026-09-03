import React from 'react';

export default function DeleteConfirmModal({ isOpen, title, onConfirm, onCancel, deleting }) {
  if (!isOpen) return null;

  return (
    <div style={styles.backdrop} onClick={onCancel} role="dialog" aria-modal="true">
      <div style={styles.modal} onClick={(e) => e.stopPropagation()}>
        <div style={styles.iconCircle}>
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#ef4444" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="3 6 5 6 21 6" />
            <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
            <line x1="10" y1="11" x2="10" y2="17" />
            <line x1="14" y1="11" x2="14" y2="17" />
          </svg>
        </div>

        <h3 style={styles.title}>Delete Conversation?</h3>
        <p style={styles.message}>
          This action will permanently remove {title ? `"${title}"` : 'this conversation'} and its stored legal messages from your history.
        </p>

        <div style={styles.actions}>
          <button
            type="button"
            onClick={onCancel}
            disabled={deleting}
            style={styles.cancelBtn}
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={onConfirm}
            disabled={deleting}
            style={styles.deleteBtn}
          >
            {deleting ? 'Deleting...' : 'Delete'}
          </button>
        </div>
      </div>
    </div>
  );
}

const styles = {
  backdrop: {
    position: 'fixed',
    inset: 0,
    zIndex: 100000,
    backgroundColor: 'rgba(15, 23, 42, 0.55)',
    backdropFilter: 'blur(4px)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    padding: '1rem',
  },
  modal: {
    width: 'min(420px, 92vw)',
    backgroundColor: '#ffffff',
    borderRadius: '12px',
    border: '1px solid #e2e8f0',
    boxShadow: '0 20px 40px -8px rgba(15, 23, 42, 0.25)',
    padding: '1.5rem',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    textAlign: 'center',
  },
  iconCircle: {
    width: '44px',
    height: '44px',
    borderRadius: '50%',
    backgroundColor: '#fee2e2',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: '0.85rem',
  },
  title: {
    fontSize: '1.125rem',
    fontWeight: '700',
    color: '#0f172a',
    margin: '0 0 0.35rem 0',
  },
  message: {
    fontSize: '0.84375rem',
    color: '#64748b',
    lineHeight: '1.5',
    margin: '0 0 1.35rem 0',
  },
  actions: {
    display: 'flex',
    gap: '0.75rem',
    width: '100%',
  },
  cancelBtn: {
    flex: 1,
    padding: '0.65rem 1rem',
    borderRadius: '6px',
    border: '1px solid #cbd5e1',
    backgroundColor: '#ffffff',
    color: '#334155',
    fontSize: '0.875rem',
    fontWeight: '600',
    cursor: 'pointer',
  },
  deleteBtn: {
    flex: 1,
    padding: '0.65rem 1rem',
    borderRadius: '6px',
    border: 'none',
    backgroundColor: '#ef4444',
    color: '#ffffff',
    fontSize: '0.875rem',
    fontWeight: '600',
    cursor: 'pointer',
    boxShadow: '0 2px 6px rgba(239, 68, 68, 0.25)',
  },
};
