import React from 'react';

export default function WhyNyayaSetuSection() {
  const pillars = [
    {
      label: 'SOURCE-BACKED',
      title: 'Statutory Grounding',
      desc: 'Answers are synthesized directly from retrieved statutory passages rather than generated from ungrounded parametric memory, preventing legal hallucination.',
      icon: (
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
          <polyline points="14 2 14 8 20 8" />
          <line x1="16" y1="13" x2="8" y2="13" />
          <line x1="16" y1="17" x2="8" y2="17" />
          <polyline points="10 9 9 9 8 9" />
        </svg>
      ),
    },
    {
      label: 'EXPLAINABLE',
      title: 'Transparent Citations',
      desc: 'Every substantive answer references verified source passages with exact enactment titles, page numbers, and chunk IDs for full provenance and auditability.',
      icon: (
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <circle cx="11" cy="11" r="8" />
          <line x1="21" y1="21" x2="16.65" y2="16.65" />
          <line x1="11" y1="8" x2="11" y2="14" />
          <line x1="8" y1="11" x2="14" y2="11" />
        </svg>
      ),
    },
    {
      label: 'RETRIEVAL-DRIVEN',
      title: 'Two-Stage Precision',
      desc: 'Combines dense vector retrieval (BAAI/bge-small-en-v1.5) with cross-encoder neural reranking (BAAI/bge-reranker-base) for statutory accuracy.',
      icon: (
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <polygon points="12 2 2 7 12 12 22 7 12 2" />
          <polyline points="2 17 12 22 22 17" />
          <polyline points="2 12 12 17 22 12" />
        </svg>
      ),
    },
  ];

  return (
    <section id="why-nyayasetu" className="section-spacer" style={styles.section}>
      <div className="container">
        <div className="section-header">
          <h2 className="section-title">Designed for Accessible Legal Knowledge</h2>
          <p className="section-desc">
            Engineered with strict safety guardrails, factual retrieval, and explainability for Indian legal questions.
          </p>
        </div>

        <div style={styles.pillarGrid}>
          {pillars.map((item, idx) => (
            <div key={idx} style={styles.pillarCard}>
              <div style={styles.iconContainer}>{item.icon}</div>
              <span style={styles.pillarLabel}>{item.label}</span>
              <h3 style={styles.pillarTitle}>{item.title}</h3>
              <p style={styles.pillarDesc}>{item.desc}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

const styles = {
  section: {
    backgroundColor: '#fafbfc',
  },
  pillarGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))',
    gap: '1.5rem',
  },
  pillarCard: {
    backgroundColor: '#ffffff',
    border: '1px solid #e2e8f0',
    borderRadius: 'var(--radius-sm, 4px)',
    padding: '1.5rem 1.35rem',
    display: 'flex',
    flexDirection: 'column',
  },
  iconContainer: {
    width: '36px',
    height: '36px',
    borderRadius: 'var(--radius-sm, 4px)',
    backgroundColor: '#e6f4f1',
    color: '#0d9488',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: '1rem',
  },
  pillarLabel: {
    fontSize: '0.6875rem', /* 11px */
    fontWeight: '700',
    letterSpacing: '0.08em',
    color: '#0d9488',
    marginBottom: '0.4rem',
  },
  pillarTitle: {
    fontSize: '1.125rem', /* 18px */
    fontWeight: '700',
    color: '#0f172a',
    marginBottom: '0.45rem',
  },
  pillarDesc: {
    fontSize: '0.875rem', /* 14px */
    lineHeight: '1.55',
    color: '#475569',
  },
};
