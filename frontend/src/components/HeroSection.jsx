import React from 'react';

export default function HeroSection({ onStartChat, onNavigate }) {
  const handleNavigateAbout = (e) => {
    e.preventDefault();
    if (onNavigate) {
      onNavigate('about');
    } else {
      window.location.hash = 'about';
    }
  };

  return (
    <section id="top" style={styles.heroSection}>
      <div className="container hero-container" style={styles.heroContainer}>
        {/* Left Column: Typography & CTAs */}
        <div style={styles.heroLeft}>
          <div style={styles.heroTag}>
            AI-POWERED LEGAL ASSISTANT FOR INDIA
          </div>

          <h1 className="hero-heading" style={styles.heroHeading}>
            Navigate law.<br />
            <span style={styles.headingHighlight}>Understand your rights.</span>
          </h1>

          <p style={styles.heroDescription}>
            NyayaSetu helps citizens, students, and legal professionals explore Indian legal information
            through an AI-powered Retrieval-Augmented Generation system built strictly on verified
            statutory enactments.
          </p>

          <ul className="hero-features" style={styles.featuresList}>
            <li style={styles.featureItem}>
              <span style={styles.checkIcon}>✓</span>
              <span>Explainable, plain-language summaries</span>
            </li>
            <li style={styles.featureItem}>
              <span style={styles.checkIcon}>✓</span>
              <span>Source-backed statutory citations</span>
            </li>
            <li style={styles.featureItem}>
              <span style={styles.checkIcon}>✓</span>
              <span>7 verified Indian statutory codes indexed</span>
            </li>
            <li style={styles.featureItem}>
              <span style={styles.checkIcon}>✓</span>
              <span>Transparent citation traceability</span>
            </li>
          </ul>

          <div className="cta-group" style={styles.ctaGroup}>
            <button
              onClick={onStartChat}
              style={styles.primaryCta}
            >
              Start a Legal Conversation
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M5 12h14M12 5l7 7-7 7" />
              </svg>
            </button>

            <a
              href="/about"
              onClick={handleNavigateAbout}
              style={styles.secondaryCta}
            >
              About NyayaSetu
            </a>
          </div>
        </div>

        {/* Right Column: Abstract Legal-AI Radar / Knowledge Node Diagram */}
        <div style={styles.heroRight}>
          <div style={styles.visualContainer}>
            <svg
              viewBox="0 0 400 400"
              style={styles.svgDiagram}
              aria-label="Abstract NyayaSetu Statutory Knowledge Graph"
            >
              {/* --- STATIC CALIBRATED COORDINATE FRAME --- */}
              <circle cx="200" cy="200" r="170" fill="none" stroke="#e2e8f0" strokeWidth="1" strokeDasharray="3 3" />
              <circle cx="200" cy="200" r="75" fill="none" stroke="#f1f5f9" strokeWidth="1" />
              <line x1="30" y1="200" x2="370" y2="200" stroke="#f1f5f9" strokeWidth="1.5" />
              <line x1="200" y1="30" x2="200" y2="370" stroke="#f1f5f9" strokeWidth="1.5" />

              {/* --- ROTATING STATUTORY KNOWLEDGE NETWORK (28s smooth continuous orbit) --- */}
              <g className="rotating-knowledge-network">
                {/* Orbital Rings */}
                <circle cx="200" cy="200" r="125" fill="none" stroke="#cbd5e1" strokeWidth="1" />
                <circle cx="200" cy="200" r="125" fill="none" stroke="#14b8a6" strokeWidth="1.5" strokeOpacity="0.4" />

                {/* Connecting Spokes */}
                <line x1="200" y1="200" x2="200" y2="75" stroke="#99f6e4" strokeWidth="1.5" />
                <line x1="200" y1="200" x2="306" y2="138" stroke="#99f6e4" strokeWidth="1.5" />
                <line x1="200" y1="200" x2="320" y2="245" stroke="#99f6e4" strokeWidth="1.5" />
                <line x1="200" y1="200" x2="250" y2="315" stroke="#99f6e4" strokeWidth="1.5" />
                <line x1="200" y1="200" x2="140" y2="310" stroke="#99f6e4" strokeWidth="1.5" />
                <line x1="200" y1="200" x2="85" y2="230" stroke="#99f6e4" strokeWidth="1.5" />
                <line x1="200" y1="200" x2="95" y2="135" stroke="#99f6e4" strokeWidth="1.5" />

                {/* Satellite Nodes with Counter-Rotating Text Labels (Remain Horizontally Readable) */}
                {[
                  { label: 'Constitution', x: 200, y: 75, r: 7, color: '#1e40af' },
                  { label: 'BNS 2023', x: 306, y: 138, r: 6, color: '#0284c7' },
                  { label: 'BNSS 2023', x: 320, y: 245, r: 6, color: '#0d9488' },
                  { label: 'BSA Evidence', x: 250, y: 315, r: 6, color: '#14b8a6' },
                  { label: 'Consumer Act', x: 140, y: 310, r: 6, color: '#0284c7' },
                  { label: 'IT Act', x: 85, y: 230, r: 6, color: '#1e40af' },
                  { label: 'MV Act', x: 95, y: 135, r: 6, color: '#0d9488' },
                ].map((node, i) => (
                  <g key={i} transform={`translate(${node.x}, ${node.y})`}>
                    {/* Satellite Node Dot */}
                    <circle cx="0" cy="0" r={node.r} fill={node.color} />

                    {/* Counter-Rotating Group: text maintains 0deg net horizontal rotation */}
                    <g className="counter-rotating-label">
                      <text
                        x="0"
                        y="-12"
                        textAnchor="middle"
                        fill="#0f172a"
                        fontSize="9.5"
                        fontWeight="600"
                        stroke="#ffffff"
                        strokeWidth="3"
                        strokeLinejoin="round"
                        style={{ paintOrder: 'stroke fill' }}
                      >
                        {node.label}
                      </text>
                    </g>
                  </g>
                ))}
              </g>

              {/* --- FIXED CENTRAL AI KNOWLEDGE CORE (Remains Stationary) --- */}
              <circle cx="200" cy="200" r="18" fill="#0d9488" />
              <circle cx="200" cy="200" r="7" fill="#ffffff" />
            </svg>

            <div style={styles.diagramCaption}>
              <span style={styles.captionDot}></span>
              <span>4,184 Indexed Statutory Passages across 7 Enactments</span>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

const styles = {
  heroSection: {
    padding: '3.25rem 0 3.75rem 0',
    backgroundColor: '#ffffff',
    borderBottom: '1px solid #e2e8f0',
  },
  heroContainer: {
    display: 'grid',
    gridTemplateColumns: '1.08fr 0.92fr', /* Balanced: ~54% left, ~46% right */
    gap: '2.5rem',
    alignItems: 'center',
  },
  heroLeft: {
    display: 'flex',
    flexDirection: 'column',
  },
  heroTag: {
    fontSize: '0.6875rem', /* 11px compact label */
    fontWeight: '700',
    letterSpacing: '0.08em',
    color: '#0d9488',
    marginBottom: '0.75rem',
    textTransform: 'uppercase',
  },
  heroHeading: {
    fontSize: '3rem', /* 48px - 50px compact prominent heading (recommended 48px to 56px) */
    fontWeight: '700',
    lineHeight: '1.1',
    color: '#0f172a',
    letterSpacing: '-0.025em',
    marginBottom: '1rem',
  },
  headingHighlight: {
    color: '#0f172a',
  },
  heroDescription: {
    fontSize: '1.0625rem', /* 17px compact body */
    lineHeight: '1.6',
    color: '#475569',
    marginBottom: '1.25rem',
    maxWidth: '480px', /* Reduced width so left content does not visually dominate */
  },
  featuresList: {
    listStyle: 'none',
    display: 'grid',
    gridTemplateColumns: 'repeat(2, 1fr)',
    gap: '0.45rem 1rem',
    marginBottom: '1.625rem',
  },
  featureItem: {
    fontSize: '0.875rem', /* 14px */
    color: '#334155',
    display: 'flex',
    alignItems: 'center',
    gap: '0.45rem',
  },
  checkIcon: {
    color: '#0d9488',
    fontWeight: '700',
    fontSize: '0.85rem',
  },
  ctaGroup: {
    display: 'flex',
    alignItems: 'center',
    gap: '0.75rem',
  },
  primaryCta: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '0.45rem',
    backgroundColor: '#0d9488',
    color: '#ffffff',
    padding: '0.575rem 1.25rem',
    fontSize: '0.875rem', /* 14px */
    fontWeight: '500',
    borderRadius: 'var(--radius-sm, 4px)',
    transition: 'background-color 0.15s ease',
  },
  secondaryCta: {
    display: 'inline-flex',
    alignItems: 'center',
    backgroundColor: '#ffffff',
    color: '#1e293b',
    border: '1px solid #cbd5e1',
    padding: '0.575rem 1.25rem',
    fontSize: '0.875rem', /* 14px */
    fontWeight: '500',
    borderRadius: 'var(--radius-sm, 4px)',
    textDecoration: 'none',
    transition: 'all 0.15s ease',
  },
  heroRight: {
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
  },
  visualContainer: {
    width: '100%',
    maxWidth: '380px',
    background: 'transparent',
    border: 'none',
    boxShadow: 'none',
    outline: 'none',
    padding: '0.5rem 0',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
  },
  svgDiagram: {
    width: '100%',
    height: 'auto',
    maxHeight: '310px',
  },
  diagramCaption: {
    marginTop: '0.625rem',
    fontSize: '0.75rem', /* 12px */
    color: '#64748b',
    display: 'flex',
    alignItems: 'center',
    gap: '0.45rem',
  },
  captionDot: {
    width: '6px',
    height: '6px',
    borderRadius: '50%',
    backgroundColor: '#0d9488',
  },
};
