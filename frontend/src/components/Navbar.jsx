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
          <span style={styles.logoTitle}>Nyaya<span style={styles.logoAccent}>Setu</span></span>
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

        {/* Right Actions */}
        <div style={styles.actions}>
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
              Start Conversation
            </button>
          )}

          <a
            href="https://github.com/imyuvraj09/NyayaSetu"
            target="_blank"
            rel="noopener noreferrer"
            style={styles.githubBtn}
          >
            <span>GitHub</span>
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M7 17L17 7" />
              <path d="M7 7h10v10" />
            </svg>
          </a>

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
            style={styles.mobileNavLink}
            onClick={() => setMobileMenuOpen(false)}
          >
            GitHub ↗
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
    height: '36px',
    width: 'auto',
    maxHeight: '38px',
    objectFit: 'contain',
    display: 'block',
    background: 'transparent',
    border: 'none',
    boxShadow: 'none',
  },
  logoTitle: {
    fontSize: '1.2rem',
    fontWeight: '700',
    letterSpacing: '-0.02em',
    color: '#0f172a',
  },
  logoAccent: {
    color: '#0284c7',
    fontWeight: '500',
  },
  desktopNav: {
    display: 'flex',
    alignItems: 'center',
    gap: '0.35rem',
  },
  navLink: {
    fontSize: '0.875rem', /* 14px */
    fontWeight: '500',
    color: '#475569',
    padding: '0.35rem 0.75rem',
    borderRadius: 'var(--radius-sm, 4px)',
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
    gap: '0.55rem',
  },
  chatBtn: {
    backgroundColor: '#0d9488',
    color: '#ffffff',
    fontSize: '0.8125rem', /* 13px */
    fontWeight: '600',
    padding: '0.4rem 0.9rem',
    borderRadius: 'var(--radius-sm, 4px)',
    transition: 'background-color 0.15s ease',
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
    gap: '0.3rem',
    backgroundColor: '#ffffff',
    border: '1px solid #e2e8f0',
    color: '#475569',
    fontSize: '0.8125rem',
    fontWeight: '500',
    padding: '0.4rem 0.75rem',
    borderRadius: 'var(--radius-sm, 4px)',
    textDecoration: 'none',
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
