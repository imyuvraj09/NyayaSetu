import React, { useState } from 'react';

export default function ConnectSection() {
  const [copied, setCopied] = useState(false);

  const citationText = `Yuvraj Singh (2026). NyayaSetu: An AI-Powered RAG-Based Legal Assistant for Accessible and Explainable Legal Knowledge in India [Software]. https://github.com/imyuvraj09/NyayaSetu`;

  const contributorEmails = [
    { name: 'Yuvraj Singh', email: 'yuvrajsinghias09122004@gmail.com' },
    { name: 'Sunit Das', email: 'sunitdasclassx@gmail.com' },
    { name: 'Raju Shaw', email: 'rajushaw2741@gmail.com' },
    { name: 'Pallab Bag', email: 'pallab861774@gmail.com' },
    { name: 'Sumit Kumar Nath', email: 'sumitnath@gmail.com' },
    { name: 'Nababrato Bishwas', email: 'nababratobiswas.11c@gmail.com' },
  ];

  const handleCopyCitation = () => {
    navigator.clipboard.writeText(citationText);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <section id="about" className="section-spacer" style={styles.section}>
      <div className="container">
        <div className="two-column-layout" style={styles.twoColumnLayout}>
          {/* Left Panel: Open Source & Cite */}
          <div style={styles.panel}>
            <span style={styles.panelTag}>OPEN SOURCE · RESEARCH</span>
            <h3 style={styles.panelTitle}>Built for research and accessibility</h3>
            <p style={styles.panelDesc}>
              NyayaSetu is an academic and research-oriented AI legal assistant project demonstrating
              explainable retrieval-augmented generation on Indian legal statutes. If you use this platform
              in academic research or legal technology development, please cite this work:
            </p>

            <div style={styles.citationBox}>
              <code>{citationText}</code>
            </div>

            <div style={styles.btnRow}>
              <button
                onClick={handleCopyCitation}
                style={styles.copyBtn}
              >
                {copied ? (
                  <>
                    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                      <polyline points="20 6 9 17 4 12" />
                    </svg>
                    <span>Copied!</span>
                  </>
                ) : (
                  <>
                    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
                      <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
                    </svg>
                    <span>Copy citation</span>
                  </>
                )}
              </button>

              <a
                href="https://github.com/imyuvraj09/NyayaSetu"
                target="_blank"
                rel="noopener noreferrer"
                style={styles.outlineBtn}
              >
                View on GitHub ↗
              </a>
            </div>
          </div>

          {/* Right Panel: Contact & Contribute */}
          <div style={styles.panel}>
            <span style={styles.panelTag}>CONNECT</span>
            <h3 style={styles.panelTitle}>Contact & Contribute</h3>
            <p style={styles.panelDesc}>
              Found a discrepancy in statutory interpretations, have an architectural feature request,
              or want to collaborate on legal AI research?
            </p>

            <div style={styles.contactList}>
              <a
                href="https://github.com/imyuvraj09/NyayaSetu"
                target="_blank"
                rel="noopener noreferrer"
                style={styles.contactItem}
              >
                <div style={styles.contactIcon}>
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M9 19c-5 1.5-5-2.5-7-3m14 6v-3.87a3.37 3.37 0 0 0-.94-2.61c3.14-.35 6.44-1.54 6.44-7A5.44 5.44 0 0 0 20 4.77 5.07 5.07 0 0 0 19.91 1S18.73.65 16 2.48a13.38 13.38 0 0 0-7 0C6.27.65 5.09 1 5.09 1A5.07 5.07 0 0 0 5 4.77a5.44 5.44 0 0 0-1.5 3.78c0 5.42 3.3 6.61 6.44 7A3.37 3.37 0 0 0 9 18.13V22" />
                  </svg>
                </div>
                <span>GitHub Repository & Documentation</span>
              </a>

              {contributorEmails.map((c, idx) => (
                <a
                  key={idx}
                  href={`mailto:${c.email}`}
                  style={styles.contactItem}
                  className="contact-item"
                  title={`Email ${c.name} (${c.email})`}
                >
                  <div style={styles.contactIcon}>
                    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <rect width="20" height="16" x="2" y="4" rx="2" />
                      <path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7" />
                    </svg>
                  </div>
                  <div style={styles.contactEmailCol}>
                    <span style={styles.contributorName}>{c.name}:</span>
                    <span style={styles.contributorEmail}>{c.email}</span>
                  </div>
                </a>
              ))}
            </div>

            <div style={{ marginTop: 'auto', paddingTop: '1.25rem' }}>
              <a
                href="https://github.com/imyuvraj09/NyayaSetu/issues"
                target="_blank"
                rel="noopener noreferrer"
                style={styles.issueBtn}
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <circle cx="12" cy="12" r="10" />
                  <line x1="12" y1="8" x2="12" y2="12" />
                  <line x1="12" y1="16" x2="12.01" y2="16" />
                </svg>
                <span>Open an Issue on GitHub ↗</span>
              </a>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

const styles = {
  section: {
    backgroundColor: '#fafbfc',
  },
  twoColumnLayout: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(360px, 1fr))',
    gap: '2rem',
  },
  panel: {
    backgroundColor: '#ffffff',
    border: '1px solid #e2e8f0',
    borderRadius: 'var(--radius-sm, 4px)',
    padding: '1.5rem 1.35rem',
    display: 'flex',
    flexDirection: 'column',
  },
  panelTag: {
    fontSize: '0.6875rem', /* 11px compact */
    fontWeight: '700',
    letterSpacing: '0.08em',
    color: '#0d9488',
    marginBottom: '0.4rem',
  },
  panelTitle: {
    fontSize: '1.1875rem', /* 19px compact card title */
    fontWeight: '700',
    color: '#0f172a',
    marginBottom: '0.5rem',
  },
  panelDesc: {
    fontSize: '0.875rem', /* 14px compact body */
    lineHeight: '1.55',
    color: '#475569',
    marginBottom: '1rem',
  },
  citationBox: {
    backgroundColor: '#f8fafc',
    border: '1px solid #e2e8f0',
    borderRadius: 'var(--radius-sm, 4px)',
    padding: '0.75rem 0.85rem',
    fontSize: '0.75rem', /* 12px compact monospace */
    lineHeight: '1.45',
    color: '#334155',
    fontFamily: 'var(--font-mono, monospace)',
    wordBreak: 'break-all',
    marginBottom: '1rem',
  },
  btnRow: {
    display: 'flex',
    alignItems: 'center',
    gap: '0.625rem',
    marginTop: 'auto',
  },
  copyBtn: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '0.4rem',
    backgroundColor: '#0d9488',
    color: '#ffffff',
    padding: '0.45rem 0.85rem',
    fontSize: '0.8125rem', /* 13px */
    fontWeight: '500',
    borderRadius: 'var(--radius-sm, 4px)',
    transition: 'background-color 0.15s ease',
  },
  outlineBtn: {
    display: 'inline-flex',
    alignItems: 'center',
    backgroundColor: '#ffffff',
    border: '1px solid #cbd5e1',
    color: '#334155',
    padding: '0.45rem 0.85rem',
    fontSize: '0.8125rem', /* 13px */
    fontWeight: '500',
    borderRadius: 'var(--radius-sm, 4px)',
    textDecoration: 'none',
  },
  contactList: {
    display: 'flex',
    flexDirection: 'column',
    gap: '0.625rem',
    marginBottom: '1rem',
  },
  contactItem: {
    display: 'flex',
    alignItems: 'center',
    gap: '0.625rem',
    color: '#334155',
    fontSize: '0.8125rem', /* 13px */
    textDecoration: 'none',
    transition: 'color 0.15s ease',
  },
  contactIcon: {
    color: '#0d9488',
    display: 'flex',
    alignItems: 'center',
    flexShrink: 0,
  },
  contactEmailCol: {
    display: 'flex',
    alignItems: 'center',
    gap: '0.35rem',
    flexWrap: 'wrap',
    fontSize: '0.8125rem',
  },
  contributorName: {
    fontWeight: '600',
    color: '#0f172a',
  },
  contributorEmail: {
    color: '#0d9488',
    wordBreak: 'break-all',
  },
  issueBtn: {
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: '0.45rem',
    width: '100%',
    backgroundColor: '#ffffff',
    border: '1px solid #cbd5e1',
    color: '#0f172a',
    padding: '0.5rem 0.85rem',
    fontSize: '0.8125rem', /* 13px */
    fontWeight: '500',
    borderRadius: 'var(--radius-sm, 4px)',
    textDecoration: 'none',
    transition: 'all 0.15s ease',
  },
};
