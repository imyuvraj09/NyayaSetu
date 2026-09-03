import React from 'react';

export default function WorkflowSection() {
  const stages = [
    {
      num: '01',
      title: 'Ask a Question',
      desc: 'Users ask legal questions in natural language regarding Indian statutes, procedures, or civil protections.',
    },
    {
      num: '02',
      title: 'Understand the Query',
      desc: 'The system normalizes and processes the inquiry to formulate an optimized semantic representation for retrieval.',
    },
    {
      num: '03',
      title: 'Retrieve Legal Sources',
      desc: 'Relevant statutory passages are retrieved from the dense vector index across 4,184 verified legal chunks.',
    },
    {
      num: '04',
      title: 'Advanced Reranking',
      desc: 'A cross-encoder deep neural model scores candidate passages with joint query-document cross-attention.',
    },
    {
      num: '05',
      title: 'Generate an Answer',
      desc: 'The language model synthesizes an explainable answer grounded strictly on the retrieved legal context.',
    },
    {
      num: '06',
      title: 'Verify Sources',
      desc: 'Deterministic validators ensure all citations link directly to verified Indian statutory sources without hallucinations.',
    },
  ];

  return (
    <section id="how-it-works" className="section-spacer" style={styles.section}>
      <div className="container">
        {/* Section Header */}
        <div className="section-header">
          <h2 className="section-title">How NyayaSetu Works</h2>
          <p className="section-desc">
            From your legal question to a source-backed response through a six-stage pipeline.
          </p>
        </div>

        {/* 6 Stages Grid (3 columns on desktop, 2 on tablet, 1 on mobile) */}
        <div style={styles.grid}>
          {stages.map((stage) => (
            <div key={stage.num} style={styles.card}>
              <div style={styles.stageNum}>{stage.num}</div>
              <h3 style={styles.cardTitle}>{stage.title}</h3>
              <p style={styles.cardDesc}>{stage.desc}</p>
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
  grid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))',
    gap: '1.25rem',
  },
  card: {
    backgroundColor: '#ffffff',
    border: '1px solid #e2e8f0',
    borderRadius: 'var(--radius-sm, 4px)',
    padding: '1.35rem 1.25rem',
    display: 'flex',
    flexDirection: 'column',
    transition: 'border-color 0.18s ease, box-shadow 0.18s ease',
  },
  stageNum: {
    fontSize: '0.75rem', /* 12px */
    fontWeight: '700',
    color: '#0d9488',
    marginBottom: '0.5rem',
    letterSpacing: '0.04em',
  },
  cardTitle: {
    fontSize: '1.0625rem', /* 17px */
    fontWeight: '700',
    color: '#0f172a',
    marginBottom: '0.4rem',
  },
  cardDesc: {
    fontSize: '0.875rem', /* 14px */
    lineHeight: '1.55',
    color: '#475569',
  },
};
