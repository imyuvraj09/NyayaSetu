import React from 'react';

export default function HeroSection({ onStartChat, onNavigate }) {
  const handleLearnMore = (e) => {
    e.preventDefault();
    const whySection = document.getElementById('why-nyayasetu');
    if (whySection) {
      whySection.scrollIntoView({ behavior: 'smooth' });
    } else if (onNavigate) {
      onNavigate('about');
    }
  };

  return (
    <div id="top" style={styles.wrapper}>
      {/* =========================================================================
          HERO LANDING SECTION (Supreme Court of India Background / Visual)
          ========================================================================= */}
      <section style={styles.heroSection}>
        {/* Right side Supreme Court of India backdrop image */}
        <div style={styles.courtBackdrop}>
          <img
            src="/supreme-court-transparent.png"
            alt="Supreme Court of India"
            style={styles.courtBackdropImg}
          />
        </div>

        <div className="container hero-container" style={styles.heroContainer}>
          {/* Left Column: Typography, Feature Checks, CTAs */}
          <div style={styles.heroLeft}>
            <div style={styles.heroTag}>
              AI-POWERED LEGAL ASSISTANT FOR INDIA
            </div>

            <h1 className="hero-heading" style={styles.heroHeading}>
              Understand Indian Law.<br />
              <span style={styles.headingHighlight}>Know Your Rights.</span>
            </h1>

            <p style={styles.heroDescription}>
              NyayaSetu helps citizens, students, and legal professionals explore Indian legal information
              through an AI-powered Retrieval-Augmented Generation system built strictly on verified
              statutory enactments.
            </p>

            <ul style={styles.checkList}>
              <li style={styles.checkItem}>
                <svg width="20" height="20" viewBox="0 0 20 20" fill="none" style={styles.checkIcon}>
                  <circle cx="10" cy="10" r="10" fill="#0d9488" />
                  <path d="M6 10.2l2.8 2.8 5.4-5.5" stroke="#ffffff" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
                <span>Plain-language, easy to understand explanations</span>
              </li>
              <li style={styles.checkItem}>
                <svg width="20" height="20" viewBox="0 0 20 20" fill="none" style={styles.checkIcon}>
                  <circle cx="10" cy="10" r="10" fill="#0d9488" />
                  <path d="M6 10.2l2.8 2.8 5.4-5.5" stroke="#ffffff" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
                <span>Source-backed statutory citations</span>
              </li>
              <li style={styles.checkItem}>
                <svg width="20" height="20" viewBox="0 0 20 20" fill="none" style={styles.checkIcon}>
                  <circle cx="10" cy="10" r="10" fill="#0d9488" />
                  <path d="M6 10.2l2.8 2.8 5.4-5.5" stroke="#ffffff" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
                <span>Transparent and verifiable legal information</span>
              </li>
            </ul>

            <div className="cta-group" style={styles.ctaGroup}>
              <button
                onClick={onStartChat}
                style={styles.primaryCta}
                className="btn-primary-hover"
              >
                <span>Start a Legal Conversation</span>
                <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M5 12h14M12 5l7 7-7 7" />
                </svg>
              </button>

              <button
                onClick={handleLearnMore}
                style={styles.secondaryCta}
                className="btn-secondary-hover"
              >
                Learn More
              </button>
            </div>
          </div>

          {/* Right Column Spacer for balance */}
          <div style={styles.heroRightSpacer} />
        </div>
      </section>

      {/* =========================================================================
          FLOATING STATS STRIP BAR (4 Stat Metrics)
          ========================================================================= */}
      <div className="container" style={styles.statsContainer}>
        <div style={styles.statsBar}>
          {/* Stat 1 */}
          <div style={styles.statCol}>
            <div style={styles.statIconWrapper}>
              <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#0d9488" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
                <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
              </svg>
            </div>
            <div>
              <div style={styles.statNumber}>4,184+</div>
              <div style={styles.statLabel}>Indexed Statutory Passages</div>
            </div>
          </div>

          <div style={styles.statDivider} />

          {/* Stat 2 */}
          <div style={styles.statCol}>
            <div style={styles.statIconWrapper}>
              <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#0d9488" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                <polyline points="14 2 14 8 20 8" />
                <line x1="16" y1="13" x2="8" y2="13" />
                <line x1="16" y1="17" x2="8" y2="17" />
                <polyline points="10 9 9 9 8 9" />
              </svg>
            </div>
            <div>
              <div style={styles.statNumber}>7</div>
              <div style={styles.statLabel}>Major Enactments</div>
            </div>
          </div>

          <div style={styles.statDivider} />

          {/* Stat 3 */}
          <div style={styles.statCol}>
            <div style={styles.statIconWrapper}>
              <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#0d9488" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
                <path d="M9 12l2 2 4-4" />
              </svg>
            </div>
            <div>
              <div style={styles.statNumber}>100%</div>
              <div style={styles.statLabel}>Source-Backed Responses</div>
            </div>
          </div>

          <div style={styles.statDivider} />

          {/* Stat 4 */}
          <div style={styles.statCol}>
            <div style={styles.statIconWrapper}>
              <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#0d9488" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
                <circle cx="9" cy="7" r="4" />
                <path d="M23 21v-2a4 4 0 0 0-3-3.87" />
                <path d="M16 3.13a4 4 0 0 1 0 7.75" />
              </svg>
            </div>
            <div>
              <div style={styles.statNumber}>For Everyone</div>
              <div style={styles.statLabel}>Citizens · Students · Legal Professionals</div>
            </div>
          </div>
        </div>
      </div>

      {/* =========================================================================
          "WHY NYAYASETU?" SECTION (4 Feature Cards Grid)
          ========================================================================= */}
      <section id="why-nyayasetu" style={styles.whySection}>
        <div className="container">
          <div style={styles.whyHeader}>
            <h2 style={styles.whyTitle}>
              Why <span style={styles.whyTitleAccent}>NyayaSetu?</span>
            </h2>
            <p style={styles.whySubtitle}>
              A more accessible, transparent, and reliable way to explore Indian law.
            </p>
          </div>

          <div className="why-grid" style={styles.whyGrid}>
            {/* Card 1: Explainable Answers */}
            <div style={styles.whyCard} className="why-card-hover">
              <div style={{ ...styles.whyIconBadge, backgroundColor: '#ecfdf5', color: '#059669' }}>
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
                  <line x1="8" y1="9" x2="16" y2="9" />
                  <line x1="8" y1="13" x2="14" y2="13" />
                </svg>
              </div>
              <div style={styles.whyCardContent}>
                <h3 style={styles.whyCardTitle}>Explainable Answers</h3>
                <p style={styles.whyCardText}>
                  Get clear, plain-language summaries of complex legal provisions.
                </p>
              </div>
            </div>

            {/* Card 2: Verified Sources */}
            <div style={styles.whyCard} className="why-card-hover">
              <div style={{ ...styles.whyIconBadge, backgroundColor: '#eff6ff', color: '#2563eb' }}>
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                  <polyline points="14 2 14 8 20 8" />
                  <line x1="16" y1="13" x2="8" y2="13" />
                  <line x1="16" y1="17" x2="8" y2="17" />
                </svg>
              </div>
              <div style={styles.whyCardContent}>
                <h3 style={styles.whyCardTitle}>Verified Sources</h3>
                <p style={styles.whyCardText}>
                  Every response is backed by authoritative Indian statutes.
                </p>
              </div>
            </div>

            {/* Card 3: Transparent Traceability */}
            <div style={styles.whyCard} className="why-card-hover">
              <div style={{ ...styles.whyIconBadge, backgroundColor: '#ecfeff', color: '#0891b2' }}>
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <circle cx="11" cy="11" r="8" />
                  <line x1="21" y1="21" x2="16.65" y2="16.65" />
                </svg>
              </div>
              <div style={styles.whyCardContent}>
                <h3 style={styles.whyCardTitle}>Transparent Traceability</h3>
                <p style={styles.whyCardText}>
                  Trace each answer to the exact legal provision.
                </p>
              </div>
            </div>

            {/* Card 4: For a Stronger, Informed India */}
            <div style={styles.whyCard} className="why-card-hover">
              <div style={{ ...styles.whyIconBadge, backgroundColor: '#f0f9ff', color: '#0284c7' }}>
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
                  <circle cx="9" cy="7" r="4" />
                  <path d="M23 21v-2a4 4 0 0 0-3-3.87" />
                  <path d="M16 3.13a4 4 0 0 1 0 7.75" />
                </svg>
              </div>
              <div style={styles.whyCardContent}>
                <h3 style={styles.whyCardTitle}>For a Stronger, Informed India</h3>
                <p style={styles.whyCardText}>
                  Empowering citizens with accessible legal knowledge.
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}

const styles = {
  wrapper: {
    backgroundColor: '#ffffff',
  },
  heroSection: {
    position: 'relative',
    background: 'linear-gradient(180deg, #edf6fc 0%, #f4f9fd 45%, #ffffff 100%)',
    paddingTop: '3.75rem',
    paddingBottom: '2.8rem',
    overflow: 'hidden',
    minHeight: '480px',
  },
  courtBackdrop: {
    position: 'absolute',
    top: 0,
    right: 0,
    bottom: 0,
    width: '58%',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'flex-end',
    pointerEvents: 'none',
    zIndex: 1,
    overflow: 'hidden',
  },
  courtBackdropImg: {
    width: '100%',
    height: '100%',
    objectFit: 'contain',
    objectPosition: 'right center',
    display: 'block',
  },
  heroContainer: {
    display: 'grid',
    gridTemplateColumns: '1.05fr 1fr',
    gap: '2.5rem',
    alignItems: 'center',
    position: 'relative',
    zIndex: 2,
  },
  heroLeft: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'flex-start',
    position: 'relative',
    zIndex: 3,
  },
  heroRightSpacer: {
    minHeight: '380px',
    display: 'block',
  },
  heroTag: {
    fontSize: '0.8125rem', /* 13px */
    fontWeight: '700',
    letterSpacing: '0.06em',
    color: '#0d9488',
    marginBottom: '1rem',
    textTransform: 'uppercase',
  },
  heroHeading: {
    fontSize: '3.25rem',
    fontWeight: '800',
    lineHeight: '1.14',
    letterSpacing: '-0.03em',
    color: '#0f172a',
    marginBottom: '1.25rem',
  },
  headingHighlight: {
    color: '#0284c7',
  },
  heroDescription: {
    fontSize: '1.0625rem',
    lineHeight: '1.65',
    color: '#475569',
    marginBottom: '1.5rem',
    maxWidth: '540px',
  },
  checkList: {
    listStyle: 'none',
    padding: 0,
    margin: '0 0 2rem 0',
    display: 'flex',
    flexDirection: 'column',
    gap: '0.7rem',
  },
  checkItem: {
    display: 'flex',
    alignItems: 'center',
    gap: '0.65rem',
    fontSize: '0.9375rem',
    color: '#334155',
    fontWeight: '500',
  },
  checkIcon: {
    flexShrink: 0,
  },
  ctaGroup: {
    display: 'flex',
    alignItems: 'center',
    gap: '1rem',
    flexWrap: 'wrap',
  },
  primaryCta: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '0.5rem',
    backgroundColor: '#0d9488',
    color: '#ffffff',
    fontSize: '0.9375rem',
    fontWeight: '600',
    padding: '0.75rem 1.45rem',
    borderRadius: '8px',
    border: 'none',
    cursor: 'pointer',
    boxShadow: '0 4px 12px rgba(13, 148, 136, 0.25)',
    transition: 'all 0.15s ease',
  },
  secondaryCta: {
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#ffffff',
    color: '#0f172a',
    fontSize: '0.9375rem',
    fontWeight: '600',
    padding: '0.75rem 1.5rem',
    borderRadius: '8px',
    border: '1px solid #cbd5e1',
    cursor: 'pointer',
    transition: 'all 0.15s ease',
  },
  statsContainer: {
    position: 'relative',
    marginTop: '-1.8rem',
    marginBottom: '2.5rem',
    zIndex: 10,
  },
  statsBar: {
    backgroundColor: '#ffffff',
    border: '1px solid #e2e8f0',
    borderRadius: '16px',
    boxShadow: '0 8px 30px rgba(0, 0, 0, 0.05)',
    padding: '1.25rem 2rem',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    flexWrap: 'wrap',
    gap: '1.5rem',
  },
  statCol: {
    display: 'flex',
    alignItems: 'center',
    gap: '1rem',
    flex: 1,
    minWidth: '200px',
  },
  statIconWrapper: {
    color: '#0d9488',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    flexShrink: 0,
  },
  statNumber: {
    fontSize: '1.4375rem', /* 23px */
    fontWeight: '700',
    color: '#0284c7',
    lineHeight: '1.2',
  },
  statLabel: {
    fontSize: '0.8125rem', /* 13px */
    color: '#64748b',
    fontWeight: '500',
    marginTop: '0.15rem',
  },
  statDivider: {
    width: '1px',
    height: '42px',
    backgroundColor: '#e2e8f0',
  },
  whySection: {
    padding: '1rem 0 3.5rem 0',
    backgroundColor: '#ffffff',
  },
  whyHeader: {
    textAlign: 'center',
    marginBottom: '2rem',
  },
  whyTitle: {
    fontSize: '1.875rem', /* 30px */
    fontWeight: '800',
    color: '#0f172a',
    letterSpacing: '-0.02em',
    marginBottom: '0.4rem',
  },
  whyTitleAccent: {
    color: '#0284c7',
  },
  whySubtitle: {
    fontSize: '0.9375rem', /* 15px */
    color: '#64748b',
  },
  whyGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(4, 1fr)',
    gap: '1.25rem',
  },
  whyCard: {
    backgroundColor: '#ffffff',
    border: '1px solid #e2e8f0',
    borderRadius: '12px',
    padding: '1.35rem 1.25rem',
    display: 'flex',
    gap: '0.85rem',
    alignItems: 'flex-start',
    boxShadow: '0 2px 8px rgba(0, 0, 0, 0.03)',
    transition: 'transform 0.15s ease, box-shadow 0.15s ease',
  },
  whyIconBadge: {
    width: '42px',
    height: '42px',
    borderRadius: '50%',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    flexShrink: 0,
  },
  whyCardContent: {
    display: 'flex',
    flexDirection: 'column',
    gap: '0.35rem',
  },
  whyCardTitle: {
    fontSize: '0.9375rem', /* 15px */
    fontWeight: '700',
    color: '#0f172a',
    lineHeight: '1.3',
    margin: 0,
  },
  whyCardText: {
    fontSize: '0.8125rem', /* 13px */
    color: '#64748b',
    lineHeight: '1.5',
    margin: 0,
  },
};
