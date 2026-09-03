import React, { useRef, useEffect } from 'react';

export default function ChatInput({
  value,
  onChange,
  onSubmit,
  disabled,
  placeholder = 'Ask a question about Indian law...',
}) {
  const textareaRef = useRef(null);

  // Auto-resize textarea height up to 140px
  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = 'auto';
    const newHeight = Math.min(el.scrollHeight, 140);
    el.style.height = `${Math.max(newHeight, 38)}px`;
  }, [value]);

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (value.trim() && !disabled) {
        onSubmit();
      }
    }
  };

  return (
    <div style={styles.container}>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          if (value.trim() && !disabled) onSubmit();
        }}
        style={styles.form}
      >
        <div style={styles.inputWrapper}>
          <textarea
            ref={textareaRef}
            rows={1}
            value={value}
            onChange={(e) => onChange(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={placeholder}
            disabled={disabled}
            style={styles.textarea}
          />

          <button
            type="submit"
            disabled={!value.trim() || disabled}
            style={{
              ...styles.sendButton,
              ...(value.trim() && !disabled ? styles.sendButtonActive : styles.sendButtonDisabled),
            }}
            aria-label="Send legal query"
            title="Send (Enter)"
          >
            <svg
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.4"
              strokeLinecap="round"
              strokeLinejoin="round"
              style={{ transform: 'translateX(-1px) translateY(1px)' }}
            >
              <line x1="22" y1="2" x2="11" y2="13" />
              <polygon points="22 2 15 22 11 13 2 9 22 2" />
            </svg>
          </button>
        </div>
      </form>

      <div style={styles.disclaimerText}>
        NyayaSetu provides legal information based on available statutory sources and is not a substitute for professional legal advice.
      </div>
    </div>
  );
}

const styles = {
  container: {
    display: 'flex',
    flexDirection: 'column',
    gap: '0.4rem',
    width: '100%',
  },
  form: {
    width: '100%',
  },
  inputWrapper: {
    display: 'flex',
    alignItems: 'flex-end',
    backgroundColor: '#ffffff',
    border: '1px solid #cbd5e1',
    borderRadius: '12px',
    padding: '0.45rem 0.5rem 0.45rem 0.95rem',
    boxShadow: '0 1px 3px rgba(15, 23, 42, 0.05)',
    transition: 'border-color 0.15s ease, box-shadow 0.15s ease',
  },
  textarea: {
    flex: 1,
    border: 'none',
    outline: 'none',
    backgroundColor: 'transparent',
    resize: 'none',
    fontFamily: 'inherit',
    fontSize: '0.90625rem', /* 14.5px */
    color: '#0f172a',
    lineHeight: '1.45',
    maxHeight: '140px',
    padding: '0.35rem 0.5rem 0.35rem 0',
  },
  sendButton: {
    width: '36px',
    height: '36px',
    borderRadius: '8px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    border: 'none',
    cursor: 'pointer',
    transition: 'all 0.18s ease',
    flexShrink: 0,
    marginBottom: '0.1rem',
  },
  sendButtonActive: {
    backgroundColor: '#0f3a68',
    color: '#ffffff',
    boxShadow: '0 2px 6px rgba(15, 58, 104, 0.28)',
  },
  sendButtonDisabled: {
    backgroundColor: '#f1f5f9',
    color: '#94a3b8',
    cursor: 'not-allowed',
  },
  disclaimerText: {
    fontSize: '0.6875rem', /* 11px */
    color: '#94a3b8',
    textAlign: 'center',
    lineHeight: '1.4',
    padding: '0 0.5rem',
  },
};
