import React from 'react';

export default function KnowledgeBaseSection() {
  const documents = [
    {
      title: 'Constitution of India',
      type: 'Constitutional Law',
      year: '1950',
      desc: 'The fundamental legal charter of India, enshrining fundamental rights, directive principles, and the constitutional framework of the Republic.',
      statuteCode: 'Part I – Part XXII',
    },
    {
      title: 'Bharatiya Nyaya Sanhita, 2023',
      type: 'Criminal Law (Substantive)',
      year: '2023',
      desc: 'The primary substantive penal code of India, defining criminal acts, liabilities, exceptions, and statutory punishments replacing IPC 1860.',
      statuteCode: 'Act No. 45 of 2023',
    },
    {
      title: 'Bharatiya Nagarik Suraksha Sanhita, 2023',
      type: 'Criminal Procedure',
      year: '2023',
      desc: 'The procedural statute regulating criminal investigation, arrest warrants, bail jurisprudence, and trial processes replacing CrPC 1973.',
      statuteCode: 'Act No. 46 of 2023',
    },
    {
      title: 'Bharatiya Sakshya Adhiniyam, 2023',
      type: 'Law of Evidence',
      year: '2023',
      desc: 'Statutory rules governing admissibility of facts, witness examinations, electronic evidence certificates, and burden of proof.',
      statuteCode: 'Act No. 47 of 2023',
    },
    {
      title: 'Consumer Protection Act, 2019',
      type: 'Consumer Law',
      year: '2019',
      desc: 'Statutory framework protecting consumer rights, addressing unfair trade practices, product liability, and establishing Redressal Commissions.',
      statuteCode: 'Act No. 35 of 2019',
    },
    {
      title: 'Information Technology Act, 2000',
      type: 'Cyber & Digital Law',
      year: '2000',
      desc: 'Regulating electronic transactions, digital records, intermediary safe harbors, computer offences, and certifying authorities.',
      statuteCode: 'Act No. 21 of 2000',
    },
    {
      title: 'Motor Vehicles Act, 1988',
      type: 'Transport & Safety Law',
      year: '1988',
      desc: 'Regulating driver licensing, vehicle registration, road traffic safety, third-party mandatory insurance, and accident claims tribunals.',
      statuteCode: 'Act No. 59 of 1988',
    },
  ];

  return (
    <section id="legal-sources" className="section-spacer" style={styles.section}>
      <div className="container">
        <div className="section-header">
          <h2 className="section-title">Built on Indian Legal Sources</h2>
          <p className="section-desc">
            NyayaSetu retrieves statutory information strictly from curated, official Indian legal enactments.
          </p>
        </div>

        {/* Document Grid */}
        <div style={styles.docGrid}>
          {documents.map((doc, idx) => (
            <div key={idx} style={styles.docCard}>
              <div style={styles.docHeader}>
                <div style={styles.docIcon}>
                  {/* Book / Document Icon */}
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
                    <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
                  </svg>
                </div>
                <span style={styles.docBadge}>{doc.type}</span>
              </div>

              <h3 style={styles.docTitle}>{doc.title}</h3>
              <p style={styles.docDesc}>{doc.desc}</p>

              <div style={styles.docFooter}>
                <span style={styles.statuteLabel}>{doc.statuteCode}</span>
                <span style={styles.yearTag}>{doc.year}</span>
              </div>
            </div>
          ))}
        </div>

        {/* Curated Scope Notice */}
        <div style={styles.scopeNotice}>
          <div style={styles.noticeIcon}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="10" />
              <line x1="12" y1="16" x2="12" y2="12" />
              <line x1="12" y1="8" x2="12.01" y2="8" />
            </svg>
          </div>
          <p style={styles.noticeText}>
            <strong>Note on corpus coverage:</strong> Responses are synthesized from the currently indexed statutory documents above and do not represent an exhaustive repository of all central, state, or municipal laws in India. Information provided is for educational and legal research purposes only.
          </p>
        </div>
      </div>
    </section>
  );
}

const styles = {
  section: {
    backgroundColor: '#ffffff',
  },
  docGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fill, minmax(330px, 1fr))',
    gap: '1.25rem',
    marginBottom: '2rem',
  },
  docCard: {
    backgroundColor: '#ffffff',
    border: '1px solid #e2e8f0',
    borderRadius: 'var(--radius-sm, 4px)',
    padding: '1.25rem',
    display: 'flex',
    flexDirection: 'column',
  },
  docHeader: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: '0.75rem',
  },
  docIcon: {
    color: '#0d9488',
    display: 'flex',
    alignItems: 'center',
  },
  docBadge: {
    fontSize: '0.6875rem', /* 11px */
    fontWeight: '600',
    color: '#0f766e',
    backgroundColor: '#f0fdfa',
    padding: '0.15rem 0.5rem',
    borderRadius: 'var(--radius-sm, 4px)',
    border: '1px solid #ccfbf1',
  },
  docTitle: {
    fontSize: '1rem', /* 16px */
    fontWeight: '700',
    color: '#0f172a',
    marginBottom: '0.4rem',
    lineHeight: '1.35',
  },
  docDesc: {
    fontSize: '0.8125rem', /* 13px */
    lineHeight: '1.5',
    color: '#475569',
    marginBottom: '0.85rem',
    flexGrow: 1,
  },
  docFooter: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingTop: '0.65rem',
    borderTop: '1px solid #f1f5f9',
    fontSize: '0.75rem',
    color: '#64748b',
  },
  statuteLabel: {
    fontFamily: 'var(--font-mono, monospace)',
    fontSize: '0.6875rem',
  },
  yearTag: {
    fontWeight: '600',
  },
  scopeNotice: {
    display: 'flex',
    alignItems: 'flex-start',
    gap: '0.75rem',
    padding: '0.85rem 1rem',
    backgroundColor: '#f8fafc',
    border: '1px solid #e2e8f0',
    borderRadius: 'var(--radius-sm, 4px)',
  },
  noticeIcon: {
    color: '#0d9488',
    marginTop: '0.1rem',
    flexShrink: 0,
  },
  noticeText: {
    fontSize: '0.8125rem',
    lineHeight: '1.5',
    color: '#475569',
  },
};
