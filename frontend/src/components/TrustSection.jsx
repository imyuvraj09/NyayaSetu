import React from 'react';

export default function TrustSection() {
  return (
    <section className="section-spacer" style={styles.section}>
      <div className="container">
        <div style={styles.banner}>
          <div style={styles.iconBox}>
            {/* Scales of Justice Shield Icon */}
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
              <path d="M9 12l2 2 4-4" />
            </svg>
          </div>

          <div style={styles.content}>
            <h3 style={styles.title}>Legal Information, Not Legal Advice</h3>
            <p style={styles.text}>
              NyayaSetu is designed to make Indian statutory information more accessible and transparent
              through AI-powered retrieval and source-grounded answers. It is intended strictly for academic,
              informational, and research purposes and <strong>does not constitute formal legal counsel</strong>.
              Users with active civil or criminal disputes must consult an enrolled Advocate or qualified legal professional.
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}

const styles = {
  section: {
    backgroundColor: '#ffffff',
  },
  banner: {
    display: 'flex',
    gap: '1rem',
    alignItems: 'flex-start',
    backgroundColor: '#fafbfc',
    border: '1px solid #e2e8f0',
    borderRadius: 'var(--radius-sm, 4px)',
    padding: '1.25rem 1.5rem',
  },
  iconBox: {
    width: '36px',
    height: '36px',
    borderRadius: 'var(--radius-sm, 4px)',
    backgroundColor: '#e6f4f1',
    color: '#0d9488',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    flexShrink: 0,
    marginTop: '0.1rem',
  },
  content: {
    flex: 1,
  },
  title: {
    fontSize: '1.0625rem', /* 17px compact title */
    fontWeight: '700',
    color: '#0f172a',
    marginBottom: '0.3rem',
  },
  text: {
    fontSize: '0.875rem', /* 14px compact body */
    lineHeight: '1.6',
    color: '#475569',
  },
};
