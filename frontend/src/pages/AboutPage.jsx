import React from 'react';
import yuvrajImg from '../assets/contributors/yuvraj-singh.jpg';
import deepImg from '../assets/contributors/deep-suman-dev.jpg';
import sunitImg from '../assets/contributors/sunit-das.jpg';
import pallabImg from '../assets/contributors/pallab-bag.jpg';
import rajuImg from '../assets/contributors/raju-shaw.jpg';
import sumitImg from '../assets/contributors/sumit-kumar-nath.jpg';
import nababratoImg from '../assets/contributors/nababrato-bishwas.jpg';

export default function AboutPage({ onStartChat }) {
  const statutoryLaws = [
    'The Constitution of India',
    'Bharatiya Nyaya Sanhita, 2023',
    'Bharatiya Nagarik Suraksha Sanhita, 2023',
    'Bharatiya Sakshya Adhiniyam, 2023',
    'Consumer Protection Act, 2019',
    'Motor Vehicles Act, 1988',
    'Information Technology Act, 2000',
    'Sexual Harassment of Women at Workplace Act, 2013',
    'Protection of Children from Sexual Offences Act, 2012',
    'Right to Information Act, 2005',
    'Right to Education Act, 2009',
    'Goods and Services Tax Act, 2017',
    'Companies Act, 2013',
    'Insolvency and Bankruptcy Code, 2016',
  ];

  const workflowStages = [
    { num: '01', title: 'Ask a Question', desc: 'Users submit legal questions in plain natural language.' },
    { num: '02', title: 'Process the Query', desc: 'The system cleans, normalizes, and embeds the inquiry into semantic vector space.' },
    { num: '03', title: 'Retrieve Relevant Sources', desc: 'Top statutory passages are retrieved using dense embeddings from indexed law documents.' },
    { num: '04', title: 'Rerank the Results', desc: 'A neural cross-encoder scores and reranks candidates to isolate the most precise provisions.' },
    { num: '05', title: 'Generate a Response', desc: 'An LLM synthesizes an explainable legal response grounded strictly on retrieved context.' },
    { num: '06', title: 'Provide Source Information', desc: 'The answer includes statutory references, page numbers, and traceable citations.' },
  ];

  const whyChooseUs = [
    {
      label: 'SOURCE-BACKED',
      desc: 'Answers are grounded in retrieved legal documents rather than ungrounded generation.',
    },
    {
      label: 'EXPLAINABLE',
      desc: 'Sources and citations help users understand where statutory information originates.',
    },
    {
      label: 'ACCESSIBLE',
      desc: 'Users can explore complex legal concepts through intuitive, plain-language questions.',
    },
    {
      label: 'RESEARCH-ORIENTED',
      desc: 'The project investigates AI safety, legal retrieval, and evaluation methodologies.',
    },
  ];

  const contributors = [
    {
      name: "Yuvraj Singh",
      initials: "YS",
      role: "Lead Developer",
      organization: "MCKV Institute of Engineering, West Bengal",
      linkedin: "https://www.linkedin.com/in/imyuvraj-singh/",
      email: "yuvrajsinghias09122004@gmail.com",
      image: yuvrajImg,
    },
    {
      name: "Dr. Deep Suman Dev",
      initials: "DSD",
      role: "Supervisor",
      organization: "MCKV Institute of Engineering, West Bengal",
      linkedin: "https://www.linkedin.com/in/dr-deep-suman-dev-phd-8a500622/",
      email: "deepsuman.dev@mckvie.edu.in",
      image: deepImg,
    },
    {
      name: "Sunit Das",
      initials: "SD",
      role: "Developer",
      organization: "MCKV Institute of Engineering, West Bengal",
      linkedin: "https://www.linkedin.com/in/dassunit/",
      email: "sunitdasclassx@gmail.com",
      image: sunitImg,
    },
    {
      name: "Raju Shaw",
      initials: "RS",
      role: "Developer",
      organization: "MCKV Institute of Engineering, West Bengal",
      linkedin: "https://www.linkedin.com/in/rajushaw-tech4u/",
      email: "rajushaw2741@gmail.com",
      image: rajuImg,
    },
    {
      name: "Pallab Bag",
      initials: "PB",
      role: "Developer",
      organization: "MCKV Institute of Engineering, West Bengal",
      linkedin: "https://www.linkedin.com/in/pallab-bag/",
      email: "pallab861774@gmail.com",
      image: pallabImg,
    },
    {
      name: "Sumit Kumar Nath",
      initials: "SKN",
      role: "Developer",
      organization: "MCKV Institute of Engineering, West Bengal",
      linkedin: "https://www.linkedin.com/in/sumit-nath-b8b972198/",
      email: "sumitnath@gmail.com",
      image: sumitImg,
    },
    {
      name: "Nababrato Bishwas",
      initials: "NB",
      role: "Developer",
      organization: "MCKV Institute of Engineering, West Bengal",
      linkedin: "https://www.linkedin.com/in/nababrato-biswas-77bb992b7/",
      email: "nababratobiswas.11c@gmail.com",
      image: nababratoImg,
    },
  ];

  return (
    <div style={styles.pageWrapper}>
      <div style={styles.aboutContainer}>

        {/* 1. Header: About NyayaSetu */}
        <div style={styles.headerSection}>
          <div style={styles.logoBrandingWrapper}>
            <img
              src="/nyayasetu-logo.png"
              alt="NyayaSetu — The Bridge to Justice"
              style={styles.largeLogoImg}
            />
          </div>
          <div style={styles.tag}>AI-POWERED LEGAL KNOWLEDGE INITIATIVE</div>
          <p style={styles.leadParagraph}>
            NyayaSetu is an AI-powered, open-source initiative designed to make legal information more
            accessible and understandable. Using Retrieval-Augmented Generation (RAG), NyayaSetu retrieves
            relevant information from verified and indexed legal documents to provide source-backed responses.
          </p>
          <p style={styles.leadParagraphSecondary}>
            The platform is designed to help students, researchers, professionals, and citizens explore
            Indian legal knowledge in a more accessible, transparent, and structured way.
          </p>
        </div>

        {/* 2. Our Mission */}
        <div style={styles.sectionBlock}>
          <h2 style={styles.sectionTitle}>Our Mission</h2>
          <div style={styles.missionCard}>
            <div style={styles.missionIcon}>
              <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M12 3v18" />
                <path d="M5 6l14 0" />
                <path d="M5 6l-3 7a4 4 0 0 0 6 0l-3 -7" />
                <path d="M19 6l-3 7a4 4 0 0 0 6 0l-3 -7" />
                <path d="M9 21h6" />
              </svg>
            </div>
            <div style={styles.missionQuote}>
              "Justice and legal knowledge should be accessible to everyone. NyayaSetu aims to bridge
              the gap between complex legal information and the people who need to understand it."
            </div>
          </div>
          <p style={styles.bodyText}>
            NyayaSetu focuses on making legal information easier to explore while maintaining transparency
            through source-backed retrieval, strict provenance, and statutory references.
          </p>
        </div>

        {/* 3. How to Use NyayaSetu */}
        <div style={styles.sectionBlock}>
          <h2 style={styles.sectionTitle}>How to Use NyayaSetu</h2>
          <p style={styles.bodyText}>
            To get started, simply click the <strong>"Start a Legal Conversation"</strong> button and begin asking
            your legal questions using natural language.
          </p>
          <p style={styles.bodyText}>
            NyayaSetu processes the query, retrieves relevant passages from its available legal knowledge base,
            and generates an explainable response based strictly on the retrieved context. Where applicable,
            source information and statutory references are provided to help users understand the basis of the response.
          </p>
          <div style={{ marginTop: '1rem' }}>
            <button
              onClick={onStartChat}
              style={styles.chatActionBtn}
            >
              Start a Legal Conversation →
            </button>
          </div>
        </div>

        {/* 4. Legal Coverage */}
        <div style={styles.sectionBlock}>
          <h2 style={styles.sectionTitle}>Legal Coverage</h2>
          <p style={styles.bodyText}>
            NyayaSetu currently retrieves information from a curated collection of Indian statutory documents:
          </p>

          <div style={styles.statuteGrid}>
            {statutoryLaws.map((law, index) => (
              <div key={index} style={styles.statuteCard}>
                <div style={styles.statuteIcon}>
                  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
                    <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
                  </svg>
                </div>
                <span style={styles.statuteTitle}>{law}</span>
              </div>
            ))}
          </div>

          <div style={styles.subtleNote}>
            <strong>Coverage Note:</strong> The available legal coverage depends on the documents currently indexed
            in the NyayaSetu knowledge base and should not be interpreted as a complete representation of all Indian laws.
          </div>
        </div>

        {/* 5. Planned Coverage */}
        <div style={styles.sectionBlock}>
          <h2 style={styles.sectionTitle}>Planned Coverage</h2>
          <div style={styles.plannedGrid}>
            <div style={styles.plannedCard}>
              <h3 style={styles.plannedTitle}>Expanded Indian Legal Coverage</h3>
              <p style={styles.plannedDesc}>
                Future development may include additional Indian central and state statutes, regulatory notifications,
                and appellate court precedent summaries.
              </p>
            </div>
            <div style={styles.plannedCard}>
              <h3 style={styles.plannedTitle}>International Legal Systems</h3>
              <p style={styles.plannedDesc}>
                Potential future expansion may explore legal systems from other common-law jurisdictions and international
                legal frameworks.
              </p>
            </div>
            <div style={{ ...styles.plannedCard, gridColumn: '1 / -1' }}>
              <h3 style={styles.plannedTitle}>Specialized Legal Areas</h3>
              <div style={styles.specializedBadges}>
                {['Corporate Law', 'Intellectual Property', 'International Arbitration', 'Commercial Law', 'Cyber Law', 'Cross-Border Legal Frameworks'].map((area, i) => (
                  <span key={i} style={styles.specialBadge}>{area}</span>
                ))}
              </div>
            </div>
          </div>
          <div style={styles.subtleNote}>
            <em>Note: These represent future research and development directions and are not currently active features.</em>
          </div>
        </div>

        {/* 6. Our Vision for the Future */}
        <div style={styles.sectionBlock}>
          <h2 style={styles.sectionTitle}>Our Vision for the Future</h2>
          <p style={styles.bodyText}>
            NyayaSetu aims to bridge the gap between people and legal knowledge. We envision a future
            where accessing understandable legal information is as simple as having a conversation.
          </p>
          <p style={styles.bodyText}>
            Future development directions include multilingual support across Indian scheduled languages,
            improved dense-sparse hybrid retrieval systems, voice-based accessibility interaction, expanded statutory coverage,
            and more advanced citation explainability features.
          </p>
        </div>

        {/* 7. How NyayaSetu Works */}
        <div style={styles.sectionBlock}>
          <h2 style={styles.sectionTitle}>How NyayaSetu Works</h2>
          <div style={styles.stagesGrid}>
            {workflowStages.map((stage) => (
              <div key={stage.num} style={styles.stageCard}>
                <div style={styles.stageNum}>{stage.num}</div>
                <h3 style={styles.stageTitle}>{stage.title}</h3>
                <p style={styles.stageDesc}>{stage.desc}</p>
              </div>
            ))}
          </div>
        </div>

        {/* 8. Why Choose NyayaSetu? */}
        <div style={styles.sectionBlock}>
          <h2 style={styles.sectionTitle}>Why Choose NyayaSetu?</h2>
          <div style={styles.whyGrid}>
            {whyChooseUs.map((item, idx) => (
              <div key={idx} style={styles.whyCard}>
                <div style={styles.whyLabel}>{item.label}</div>
                <p style={styles.whyDesc}>{item.desc}</p>
              </div>
            ))}
          </div>
        </div>

        {/* 9. Legal Disclaimer */}
        <div style={styles.sectionBlock}>
          <div style={styles.disclaimerPanel}>
            <div style={styles.disclaimerHeader}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="12" cy="12" r="10" />
                <line x1="12" y1="8" x2="12" y2="12" />
                <line x1="12" y1="16" x2="12.01" y2="16" />
              </svg>
              <span>Legal Information, Not Legal Advice</span>
            </div>
            <p style={styles.disclaimerText}>
              NyayaSetu is designed to make legal information more accessible through AI-powered retrieval
              and source-backed responses. It <strong>does not replace qualified legal professionals</strong> and
              does not provide formal legal counsel. Users should consult a licensed advocate for legal advice
              related to their specific legal circumstances.
            </p>
          </div>
        </div>

        {/* 10. About the Project */}
        <div style={styles.sectionBlock}>
          <h2 style={styles.sectionTitle}>About the Project</h2>
          <p style={styles.bodyText}>
            NyayaSetu is an academic and research-oriented project exploring the application of Artificial Intelligence,
            Large Language Models, and Retrieval-Augmented Generation for accessible and explainable legal knowledge.
          </p>
          <p style={styles.bodyText}>
            The project combines information retrieval, semantic document chunking, cross-encoder neural reranking,
            and grounded citation verification to create a more transparent approach to AI-assisted legal exploration in India.
          </p>
        </div>

        {/* 11. Contributors */}
        <div style={styles.sectionBlock}>
          <h2 style={styles.sectionTitle}>Contributors</h2>
          <div className="contributors-grid" style={styles.contributorsGrid}>
            {contributors.map((c, idx) => (
              <div key={idx} style={styles.contributorCard}>
                {/* Professional Profile Image with Initial Fallback */}
                <div style={styles.avatarWrapper}>
                  {c.image ? (
                    <img
                      src={c.image}
                      alt={c.name}
                      style={styles.contributorPhoto}
                      loading="lazy"
                      onError={(e) => {
                        e.currentTarget.style.display = 'none';
                        const fallback = e.currentTarget.parentElement.querySelector('.contributor-fallback');
                        if (fallback) fallback.style.display = 'flex';
                      }}
                    />
                  ) : null}
                  <div
                    className="contributor-fallback"
                    style={{
                      ...styles.contributorAvatar,
                      display: c.image ? 'none' : 'flex',
                    }}
                  >
                    {c.initials}
                  </div>
                </div>

                <div style={styles.contributorName}>{c.name}</div>
                <div style={styles.contributorRole}>{c.role}</div>
                <div style={styles.contributorAffiliation}>{c.organization}</div>

                {/* Professional Contact Buttons */}
                <div style={styles.contributorLinks}>
                  {c.linkedin && (
                    <a
                      href={c.linkedin}
                      target="_blank"
                      rel="noopener noreferrer"
                      style={styles.contactBtn}
                      className="contrib-btn"
                      aria-label={`LinkedIn profile of ${c.name}`}
                      title={`LinkedIn - ${c.name}`}
                    >
                      <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor">
                        <path d="M19 3a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h14m-.5 15.5v-5.3a3.26 3.26 0 0 0-3.26-3.26c-.85 0-1.84.52-2.28 1.3v-1.11h-2.79v8.37h2.79v-4.93c0-.77.62-1.4 1.39-1.4a1.4 1.4 0 0 1 1.4 1.4v4.93h2.75M6.46 10.9v8.37H9.2V10.9H6.46M7.83 6.64a1.5 1.5 0 1 0 0 3 1.5 1.5 0 0 0 0-3" />
                      </svg>
                      <span>LinkedIn</span>
                    </a>
                  )}

                  {c.email && (
                    <a
                      href={`mailto:${c.email}`}
                      style={styles.contactBtn}
                      className="contrib-btn"
                      aria-label={`Send email to ${c.name}`}
                      title={`Email - ${c.name}`}
                    >
                      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <rect width="20" height="16" x="2" y="4" rx="2" />
                        <path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7" />
                      </svg>
                      <span>Email</span>
                    </a>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>



      </div>
    </div>
  );
}

const styles = {
  pageWrapper: {
    backgroundColor: '#fafbfc',
    minHeight: 'calc(100vh - var(--header-height, 58px) - 90px)',
    padding: '3rem 1rem 4rem 1rem',
  },
  aboutContainer: {
    maxWidth: '820px', /* Centered narrow container with generous side margins */
    margin: '0 auto',
    backgroundColor: '#ffffff',
    border: '1px solid #e2e8f0',
    borderRadius: 'var(--radius-md, 6px)',
    padding: '2.5rem 2.25rem',
    display: 'flex',
    flexDirection: 'column',
    gap: '2.25rem',
  },
  headerSection: {
    paddingBottom: '1.5rem',
    borderBottom: '1px solid #f1f5f9',
  },
  logoBrandingWrapper: {
    display: 'flex',
    alignItems: 'flex-start',
    marginBottom: '1rem',
    background: 'transparent',
  },
  largeLogoImg: {
    height: '100px',
    width: 'auto',
    maxHeight: '115px',
    maxWidth: '100%',
    objectFit: 'contain',
    display: 'block',
    background: 'transparent',
    border: 'none',
    boxShadow: 'none',
  },
  tag: {
    fontSize: '0.6875rem',
    fontWeight: '700',
    letterSpacing: '0.08em',
    color: '#0d9488',
    marginBottom: '0.5rem',
    textTransform: 'uppercase',
  },
  mainTitle: {
    fontSize: '2.25rem', /* 36px clean heading */
    fontWeight: '700',
    color: '#0f172a',
    letterSpacing: '-0.02em',
    marginBottom: '0.75rem',
  },
  leadParagraph: {
    fontSize: '0.9375rem', /* 15px */
    lineHeight: '1.65',
    color: '#334155',
    marginBottom: '0.625rem',
  },
  leadParagraphSecondary: {
    fontSize: '0.9375rem',
    lineHeight: '1.65',
    color: '#475569',
  },
  sectionBlock: {
    display: 'flex',
    flexDirection: 'column',
    gap: '0.625rem',
  },
  sectionTitle: {
    fontSize: '1.25rem', /* 20px compact heading */
    fontWeight: '700',
    color: '#0f172a',
    marginBottom: '0.25rem',
    letterSpacing: '-0.01em',
  },
  bodyText: {
    fontSize: '0.875rem', /* 14px */
    lineHeight: '1.6',
    color: '#475569',
  },
  missionCard: {
    display: 'flex',
    gap: '1rem',
    alignItems: 'center',
    padding: '1.125rem 1.35rem',
    backgroundColor: '#fafbfc',
    border: '1px solid #e2e8f0',
    borderRadius: 'var(--radius-sm, 4px)',
    margin: '0.25rem 0 0.5rem 0',
  },
  missionIcon: {
    color: '#0d9488',
    flexShrink: 0,
  },
  missionQuote: {
    fontSize: '0.9375rem',
    lineHeight: '1.55',
    fontWeight: '500',
    fontStyle: 'italic',
    color: '#0f172a',
  },
  chatActionBtn: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '0.45rem',
    backgroundColor: '#0d9488',
    color: '#ffffff',
    padding: '0.55rem 1.15rem',
    fontSize: '0.875rem',
    fontWeight: '500',
    borderRadius: 'var(--radius-sm, 4px)',
    transition: 'background-color 0.15s ease',
  },
  statuteGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(2, 1fr)',
    gap: '0.5rem 0.75rem',
    marginTop: '0.25rem',
  },
  statuteCard: {
    display: 'flex',
    alignItems: 'center',
    gap: '0.55rem',
    padding: '0.55rem 0.75rem',
    backgroundColor: '#fafbfc',
    border: '1px solid #e2e8f0',
    borderRadius: 'var(--radius-sm, 4px)',
    fontSize: '0.8125rem', /* 13px */
    color: '#1e293b',
  },
  statuteIcon: {
    color: '#0d9488',
    display: 'flex',
    alignItems: 'center',
    flexShrink: 0,
  },
  statuteTitle: {
    lineHeight: '1.3',
    fontWeight: '500',
  },
  subtleNote: {
    fontSize: '0.75rem',
    lineHeight: '1.5',
    color: '#64748b',
    marginTop: '0.5rem',
  },
  plannedGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(2, 1fr)',
    gap: '0.75rem',
    marginTop: '0.25rem',
  },
  plannedCard: {
    padding: '0.875rem 1rem',
    backgroundColor: '#fafbfc',
    border: '1px solid #e2e8f0',
    borderRadius: 'var(--radius-sm, 4px)',
  },
  plannedTitle: {
    fontSize: '0.875rem',
    fontWeight: '600',
    color: '#0f172a',
    marginBottom: '0.25rem',
  },
  plannedDesc: {
    fontSize: '0.8125rem',
    lineHeight: '1.5',
    color: '#475569',
  },
  specializedBadges: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: '0.4rem',
    marginTop: '0.35rem',
  },
  specialBadge: {
    fontSize: '0.75rem',
    backgroundColor: '#ffffff',
    border: '1px solid #e2e8f0',
    padding: '0.2rem 0.5rem',
    borderRadius: 'var(--radius-sm, 4px)',
    color: '#334155',
  },
  stagesGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(3, 1fr)',
    gap: '0.75rem',
    marginTop: '0.25rem',
  },
  stageCard: {
    padding: '0.875rem 1rem',
    backgroundColor: '#ffffff',
    border: '1px solid #e2e8f0',
    borderRadius: 'var(--radius-sm, 4px)',
    display: 'flex',
    flexDirection: 'column',
  },
  stageNum: {
    fontSize: '0.6875rem',
    fontWeight: '700',
    color: '#0d9488',
    marginBottom: '0.3rem',
  },
  stageTitle: {
    fontSize: '0.875rem',
    fontWeight: '600',
    color: '#0f172a',
    marginBottom: '0.25rem',
  },
  stageDesc: {
    fontSize: '0.75rem',
    lineHeight: '1.45',
    color: '#475569',
  },
  whyGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(2, 1fr)',
    gap: '0.75rem',
    marginTop: '0.25rem',
  },
  whyCard: {
    padding: '0.875rem 1rem',
    backgroundColor: '#ffffff',
    border: '1px solid #e2e8f0',
    borderRadius: 'var(--radius-sm, 4px)',
  },
  whyLabel: {
    fontSize: '0.6875rem',
    fontWeight: '700',
    color: '#0d9488',
    letterSpacing: '0.06em',
    marginBottom: '0.3rem',
  },
  whyDesc: {
    fontSize: '0.8125rem',
    lineHeight: '1.5',
    color: '#475569',
  },
  disclaimerPanel: {
    padding: '1rem 1.25rem',
    backgroundColor: '#fafbfc',
    border: '1px solid #e2e8f0',
    borderRadius: 'var(--radius-sm, 4px)',
  },
  disclaimerHeader: {
    display: 'flex',
    alignItems: 'center',
    gap: '0.5rem',
    fontSize: '0.875rem',
    fontWeight: '700',
    color: '#0f172a',
    marginBottom: '0.35rem',
  },
  disclaimerText: {
    fontSize: '0.8125rem',
    lineHeight: '1.55',
    color: '#475569',
  },
  contributorsGrid: {
    display: 'grid',
    gap: '1rem',
    marginTop: '0.25rem',
  },
  contributorCard: {
    padding: '1.35rem 1rem',
    backgroundColor: '#ffffff',
    border: '1px solid #e2e8f0',
    borderRadius: 'var(--radius-sm, 4px)',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    textAlign: 'center',
    minHeight: '220px',
  },
  avatarWrapper: {
    width: '84px',
    height: '84px',
    position: 'relative',
    marginBottom: '0.75rem',
  },
  contributorPhoto: {
    width: '84px',
    height: '84px',
    borderRadius: '50%',
    objectFit: 'cover',
    objectPosition: 'center 15%',
    border: '2.5px solid #0d9488',
    display: 'block',
  },
  contributorAvatar: {
    width: '84px',
    height: '84px',
    borderRadius: '50%',
    backgroundColor: '#e6f4f1',
    color: '#0d9488',
    border: '2.5px solid #99f6e4',
    alignItems: 'center',
    justifyContent: 'center',
    fontSize: '1.25rem',
    fontWeight: '700',
    letterSpacing: '0.02em',
  },
  contributorName: {
    fontSize: '0.9375rem',
    fontWeight: '700',
    color: '#0f172a',
    marginBottom: '0.15rem',
  },
  contributorRole: {
    fontSize: '0.75rem',
    color: '#0d9488',
    fontWeight: '600',
    marginBottom: '0.25rem',
  },
  contributorAffiliation: {
    fontSize: '0.75rem',
    color: '#64748b',
    marginBottom: '0.75rem',
    lineHeight: '1.35',
  },
  contributorLinks: {
    display: 'flex',
    alignItems: 'center',
    gap: '0.45rem',
    fontSize: '0.75rem',
    marginTop: 'auto',
    flexWrap: 'wrap',
    justifyContent: 'center',
  },
  contactBtn: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '0.35rem',
    padding: '0.28rem 0.55rem',
    fontSize: '0.75rem',
    fontWeight: '500',
    color: '#0d9488',
    backgroundColor: '#f0fdfa',
    border: '1px solid #ccfbf1',
    borderRadius: 'var(--radius-sm, 4px)',
    textDecoration: 'none',
    transition: 'all 0.15s ease',
  },
};
