import React, { useState } from 'react';

export default function Navbar({ activeTab = 'home', onNavigate, onClearChat, isChatView = false }) {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const navItems = [
    { id: 'home', label: 'Home', href: '/' },
    { id: 'chat', label: 'Chat NyayaSetu', href: '#chat' },
    { id: 'about', label: 'About', href: '/about' },
  ];

  const handleNavClick = (id, e) => {
    e.preventDefault();
    setMobileMenuOpen(false);
    if (id === 'about') {
      onNavigate('about');
    } else if (id === 'chat') {
      onNavigate('chat');
    } else {
      onNavigate('home');
    }
  };

  return (
    <header style={styles.header}>
      <div className="container" style={styles.navContainer}>
        {/* Brand Logo */}
        <a
          href="#top"
          onClick={(e) => {
            e.preventDefault();
            onNavigate('home');
            window.scrollTo({ top: 0, behavior: 'smooth' });
          }}
          style={styles.logoLink}
        >
          <img
            src="/nyayasetu-mark.png"
            alt="NyayaSetu Logo"
            style={styles.logoImg}
          />
          <div style={styles.logoTextWrapper}>
            <span style={styles.logoTitle}>Nyaya<span style={styles.logoAccent}>Setu</span></span>
            <span style={styles.logoSubtitle}>The Bridge to Justice</span>
          </div>
        </a>

        {/* Desktop Navigation Links */}
        <nav className="desktop-nav" style={styles.desktopNav}>
          {navItems.map((item) => {
            const isActive = !isChatView && activeTab === item.id;
            return (
              <a
                key={item.id}
                href={item.href}
                onClick={(e) => handleNavClick(item.id, e)}
                style={{
                  ...styles.navLink,
                  ...(isActive ? styles.navLinkActive : {}),
                }}
              >
                {item.label}
              </a>
            );
          })}
        </nav>

        {/* Right Actions: GitHub -> Start Conversation -> Ashoka Emblem */}
        <div style={styles.actions}>
          <a
            href="https://github.com/imyuvraj09/NyayaSetu"
            target="_blank"
            rel="noopener noreferrer"
            style={styles.githubBtn}
            title="View on GitHub"
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
              <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z"/>
            </svg>
            <span>GitHub</span>
          </a>

          {isChatView ? (
            <button
              onClick={onClearChat}
              style={styles.clearBtn}
              title="Clear current legal conversation"
            >
              Clear chat
            </button>
          ) : (
            <button
              onClick={() => onNavigate('chat')}
              style={styles.chatBtn}
            >
              <span>Start Conversation</span>
              <span style={{ fontSize: '1rem', lineHeight: 1 }}>→</span>
            </button>
          )}

          <img
            src="/ashoka-emblem.png"
            alt="Ashoka Emblem"
            style={styles.navEmblemLogo}
            title="State Emblem of India"
          />

          {/* Mobile Menu Button */}
          <button
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="mobile-menu-btn"
            style={styles.mobileMenuBtn}
            aria-label="Toggle navigation menu"
          >
            <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              {mobileMenuOpen ? (
                <path d="M18 6L6 18M6 6l12 12" />
              ) : (
                <path d="M4 6h16M4 12h16M4 18h16" />
              )}
            </svg>
          </button>
        </div>
      </div>

      {/* Mobile Dropdown Menu */}
      {mobileMenuOpen && (
        <div style={styles.mobileDropdown}>
          {navItems.map((item) => (
            <a
              key={item.id}
              href={item.href}
              onClick={(e) => handleNavClick(item.id, e)}
              style={{
                ...styles.mobileNavLink,
                ...(activeTab === item.id ? { color: '#0d9488', fontWeight: '700' } : {}),
              }}
            >
              {item.label}
            </a>
          ))}
          <a
            href="https://github.com/imyuvraj09/NyayaSetu"
            target="_blank"
            rel="noopener noreferrer"
            style={{
              ...styles.mobileNavLink,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
            }}
            onClick={() => setMobileMenuOpen(false)}
          >
            <span>GitHub ↗</span>
            <img
              src="/ashoka-emblem.png"
              alt="Ashoka Emblem"
              style={{ height: '30px', width: 'auto', objectFit: 'contain' }}
            />
          </a>
          <button
            onClick={() => {
              setMobileMenuOpen(false);
              onNavigate('chat');
            }}
            style={styles.mobileChatBtn}
          >
            Start Legal Conversation
          </button>
        </div>
      )}
    </header>
  );
}

const styles = {
  header: {
    position: 'sticky',
    top: 0,
    zIndex: 100,
    backgroundColor: '#ffffff',
    borderBottom: '1px solid #e2e8f0',
    height: 'var(--header-height, 58px)',
    display: 'flex',
    alignItems: 'center',
  },
  navContainer: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  logoLink: {
    display: 'flex',
    alignItems: 'center',
    gap: '0.65rem',
    textDecoration: 'none',
    color: '#0f172a',
  },
  logoImg: {
    height: '38px',
    width: 'auto',
    maxHeight: '40px',
    objectFit: 'contain',
    display: 'block',
    background: 'transparent',
    border: 'none',
    boxShadow: 'none',
  },
  logoTextWrapper: {
    display: 'flex',
    flexDirection: 'column',
    lineHeight: 1.1,
  },
  logoTitle: {
    fontSize: '1.28rem',
    fontWeight: '800',
    letterSpacing: '-0.02em',
    color: '#0f172a',
  },
  logoAccent: {
    color: '#0284c7',
    fontWeight: '700',
  },
  logoSubtitle: {
    fontSize: '0.6875rem', /* 11px */
    fontWeight: '500',
    color: '#64748b',
    letterSpacing: '0.01em',
    marginTop: '1px',
  },
  desktopNav: {
    display: 'flex',
    alignItems: 'center',
    gap: '0.5rem',
  },
  navLink: {
    fontSize: '0.875rem', /* 14px */
    fontWeight: '500',
    color: '#334155',
    padding: '0.4rem 0.95rem',
    borderRadius: '20px',
    textDecoration: 'none',
    transition: 'all 0.15s ease',
  },
  navLinkActive: {
    backgroundColor: '#e6f4f1',
    color: '#0d9488',
    fontWeight: '600',
  },
  actions: {
    display: 'flex',
    alignItems: 'center',
    gap: '0.85rem',
  },
  chatBtn: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '0.4rem',
    backgroundColor: '#0d9488',
    color: '#ffffff',
    fontSize: '0.875rem', /* 14px */
    fontWeight: '600',
    padding: '0.45rem 1.05rem',
    borderRadius: '6px',
    border: 'none',
    cursor: 'pointer',
    boxShadow: '0 2px 8px rgba(13, 148, 136, 0.2)',
    transition: 'all 0.15s ease',
  },
  clearBtn: {
    backgroundColor: '#ffffff',
    border: '1px solid #e2e8f0',
    color: '#475569',
    fontSize: '0.8125rem',
    fontWeight: '500',
    padding: '0.4rem 0.75rem',
    borderRadius: 'var(--radius-sm, 4px)',
    transition: 'all 0.15s ease',
  },
  githubBtn: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '0.4rem',
    backgroundColor: 'transparent',
    border: 'none',
    color: '#0f172a',
    fontSize: '0.875rem',
    fontWeight: '600',
    padding: '0.35rem 0.6rem',
    borderRadius: '6px',
    textDecoration: 'none',
    cursor: 'pointer',
    transition: 'color 0.15s ease',
  },
  navEmblemLogo: {
    height: '38px',
    width: 'auto',
    maxHeight: '40px',
    objectFit: 'contain',
    display: 'block',
    background: 'transparent',
    marginLeft: '0.1rem',
  },
  mobileMenuBtn: {
    display: 'none',
    color: '#334155',
    padding: '0.25rem',
  },
  mobileDropdown: {
    position: 'absolute',
    top: 'var(--header-height, 58px)',
    left: 0,
    right: 0,
    backgroundColor: '#ffffff',
    borderBottom: '1px solid #e2e8f0',
    padding: '1.25rem 1.5rem',
    display: 'flex',
    flexDirection: 'column',
    gap: '0.75rem',
    boxShadow: '0 4px 12px rgba(0,0,0,0.05)',
  },
  mobileNavLink: {
    padding: '0.5rem 0',
    fontSize: '1rem',
    color: '#334155',
    textDecoration: 'none',
    borderBottom: '1px solid #f1f5f9',
  },
  mobileChatBtn: {
    marginTop: '0.5rem',
    backgroundColor: '#0d9488',
    color: '#ffffff',
    padding: '0.625rem',
    borderRadius: 'var(--radius-sm, 4px)',
    fontWeight: '600',
  },
};
