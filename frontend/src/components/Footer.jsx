import React from 'react';

export default function Footer({ onNavigate }) {
  return (
    <footer style={styles.footer}>
      <div className="container footer-container" style={styles.footerContainer}>
        {/* Left */}
        <div style={styles.brandCol}>
          <div style={styles.brandRow}>
            <img
              src="/nyayasetu-mark.png"
              alt="NyayaSetu"
              style={styles.footerLogoMark}
            />
            <div>
              <div style={styles.brandTitle}>
                Nyaya<span style={{ color: '#0284c7' }}>Setu</span>
              </div>
              <div style={styles.brandSub}>
                The Bridge to Justice
              </div>
            </div>
          </div>
        </div>

        {/* Center */}
        <div style={styles.centerCol}>
          <div>© 2026 NyayaSetu. All rights reserved.</div>
          <div style={styles.linkRow}>
            <a
              href="/"
              onClick={(e) => {
                e.preventDefault();
                onNavigate('home');
                window.scrollTo({ top: 0, behavior: 'smooth' });
              }}
              style={styles.footerLink}
            >
              Home
            </a>
            <span style={styles.divider}>·</span>
            <a
              href="/about"
              onClick={(e) => {
                e.preventDefault();
                onNavigate('about');
              }}
              style={styles.footerLink}
            >
              About
            </a>
            <span style={styles.divider}>·</span>
            <a
              href="https://github.com/imyuvraj09/NyayaSetu"
              target="_blank"
              rel="noopener noreferrer"
              style={styles.footerLink}
            >
              GitHub ↗
            </a>
          </div>
        </div>

        {/* Right */}
        <div className="right-col" style={styles.rightCol}>
          <div style={styles.emblemBadge}>
            <img
              src="/ashoka-emblem.png"
              alt="Ashoka Emblem"
              style={styles.emblemLogo}
            />
            <span>AI-powered legal information platform</span>
          </div>
        </div>
      </div>
    </footer>
  );
}

const styles = {
  footer: {
    backgroundColor: '#ffffff',
    borderTop: '1px solid #e2e8f0',
    padding: '2rem 0',
    fontSize: '0.8125rem', /* 13px */
    color: '#64748b',
  },
  footerContainer: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    flexWrap: 'wrap',
    gap: '1.25rem',
  },
  brandCol: {
    display: 'flex',
    flexDirection: 'column',
  },
  brandRow: {
    display: 'flex',
    alignItems: 'center',
    gap: '0.65rem',
  },
  footerLogoMark: {
    height: '32px',
    width: 'auto',
    maxHeight: '34px',
    objectFit: 'contain',
    display: 'block',
    background: 'transparent',
    border: 'none',
    boxShadow: 'none',
  },
  brandTitle: {
    fontSize: '1.0625rem', /* 17px */
    fontWeight: '700',
    color: '#0f172a',
  },
  brandSub: {
    fontSize: '0.75rem', /* 12px */
    color: '#64748b',
  },
  centerCol: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    gap: '0.3rem',
    fontSize: '0.8125rem',
  },
  linkRow: {
    display: 'flex',
    alignItems: 'center',
    gap: '0.5rem',
    fontSize: '0.8125rem',
  },
  footerLink: {
    color: '#475569',
    textDecoration: 'none',
  },
  divider: {
    color: '#cbd5e1',
  },
  rightCol: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'flex-end',
    fontSize: '0.8125rem', /* 13px */
    color: '#334155',
  },
  emblemBadge: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '0.625rem',
  },
  emblemLogo: {
    height: '36px',
    width: 'auto',
    maxHeight: '38px',
    objectFit: 'contain',
    display: 'block',
    background: 'transparent',
  },
};
