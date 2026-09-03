import React from 'react';

const SUGGESTED_QUESTIONS = [
  'What constitutes theft under Bharatiya Nyaya Sanhita?',
  'What are consumer rights in India?',
  'What does the Constitution say about fundamental rights?',
  'How are electronic records admitted under Bharatiya Sakshya Adhiniyam?',
];

export default function ChatEmptyState({ onSelectSuggestion }) {
  return (
    <div style={styles.container}>
      <img
        src="/nyayasetu-mark.png"
        alt="NyayaSetu"
        style={styles.heroLogoMark}
      />

      <h3 style={styles.title}>NyayaSetu Legal Intelligence</h3>
      <p style={styles.subtitle}>
        Your AI-powered gateway to Indian legal knowledge, grounded directly in verified statutory enactments.
      </p>

      <div style={styles.suggestionsContainer}>
        <div style={styles.suggestionsHeader}>SUGGESTED INQUIRIES</div>
        <div style={styles.chipsGrid}>
          {SUGGESTED_QUESTIONS.map((q, idx) => (
            <button
              key={idx}
              type="button"
              onClick={() => onSelectSuggestion(q)}
              style={styles.chipButton}
              title={`Ask: "${q}"`}
            >
              <span style={styles.chipBullet}>•</span>
              <span style={styles.chipText}>{q}</span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

const styles = {
  container: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    padding: '2.5rem 1.5rem',
    textAlign: 'center',
    margin: 'auto',
    maxWidth: '580px',
  },
  heroLogoMark: {
    height: '68px',
    width: 'auto',
    maxHeight: '72px',
    objectFit: 'contain',
    display: 'block',
    margin: '0 auto 1.25rem auto',
    background: 'transparent',
    border: 'none',
    boxShadow: 'none',
  },
  title: {
    fontSize: '1.25rem',
    fontWeight: '700',
    color: '#0f172a',
    marginBottom: '0.45rem',
    letterSpacing: '-0.015em',
  },
  subtitle: {
    fontSize: '0.875rem',
    color: '#64748b',
    lineHeight: '1.55',
    marginBottom: '1.75rem',
    maxWidth: '460px',
  },
  suggestionsContainer: {
    width: '100%',
    textAlign: 'left',
  },
  suggestionsHeader: {
    fontSize: '0.6875rem',
    fontWeight: '700',
    color: '#94a3b8',
    letterSpacing: '0.08em',
    marginBottom: '0.65rem',
    textTransform: 'uppercase',
  },
  chipsGrid: {
    display: 'flex',
    flexDirection: 'column',
    gap: '0.5rem',
  },
  chipButton: {
    display: 'flex',
    alignItems: 'center',
    gap: '0.65rem',
    padding: '0.7rem 0.95rem',
    backgroundColor: '#ffffff',
    border: '1px solid #e2e8f0',
    borderRadius: '8px',
    color: '#1e293b',
    fontSize: '0.84375rem', /* 13.5px */
    fontWeight: '500',
    cursor: 'pointer',
    textAlign: 'left',
    transition: 'all 0.15s ease',
    boxShadow: '0 1px 2px rgba(0, 0, 0, 0.03)',
  },
  chipBullet: {
    color: '#0d9488',
    fontSize: '1.1rem',
    lineHeight: 1,
  },
  chipText: {
    flex: 1,
    lineHeight: '1.4',
  },
};
