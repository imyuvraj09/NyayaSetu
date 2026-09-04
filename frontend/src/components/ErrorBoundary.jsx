import React from 'react';

/**
 * Global Error Boundary for NyayaSetu.
 * Catches uncaught React render errors and displays a recovery UI
 * instead of a blank white page.
 */
export default class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, errorMessage: '' };
  }

  static getDerivedStateFromError(error) {
    return {
      hasError: true,
      errorMessage: error?.message || 'An unexpected error occurred.',
    };
  }

  componentDidCatch(error, errorInfo) {
    console.error('[NyayaSetu ErrorBoundary] Caught render error:', error, errorInfo);
  }

  handleReload = () => {
    window.location.href = '/';
  };

  handleRetry = () => {
    this.setState({ hasError: false, errorMessage: '' });
  };

  render() {
    if (this.state.hasError) {
      return (
        <div style={styles.container}>
          <div style={styles.card}>
            {/* Error Icon */}
            <div style={styles.iconWrapper}>
              <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="#ef4444" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="12" cy="12" r="10" />
                <line x1="12" y1="8" x2="12" y2="12" />
                <line x1="12" y1="16" x2="12.01" y2="16" />
              </svg>
            </div>

            <h1 style={styles.title}>Something went wrong</h1>
            <p style={styles.message}>
              NyayaSetu encountered an unexpected error while rendering this page.
              Your data is safe — please try again.
            </p>

            {this.state.errorMessage && (
              <pre style={styles.errorDetail}>{this.state.errorMessage}</pre>
            )}

            <div style={styles.actions}>
              <button type="button" onClick={this.handleRetry} style={styles.retryBtn}>
                Try Again
              </button>
              <button type="button" onClick={this.handleReload} style={styles.homeBtn}>
                Go to Home
              </button>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

const styles = {
  container: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    minHeight: '100vh',
    backgroundColor: '#f8fafc',
    padding: '2rem',
    fontFamily: "'Inter', 'Segoe UI', system-ui, -apple-system, sans-serif",
  },
  card: {
    maxWidth: '480px',
    width: '100%',
    textAlign: 'center',
    padding: '2.5rem 2rem',
    backgroundColor: '#ffffff',
    borderRadius: '16px',
    border: '1px solid #e2e8f0',
    boxShadow: '0 4px 24px rgba(15, 23, 42, 0.06)',
  },
  iconWrapper: {
    marginBottom: '1.25rem',
  },
  title: {
    fontSize: '1.375rem',
    fontWeight: '700',
    color: '#0f172a',
    margin: '0 0 0.5rem 0',
  },
  message: {
    fontSize: '0.9375rem',
    color: '#64748b',
    lineHeight: '1.6',
    margin: '0 0 1.25rem 0',
  },
  errorDetail: {
    fontSize: '0.75rem',
    color: '#94a3b8',
    backgroundColor: '#f1f5f9',
    borderRadius: '8px',
    padding: '0.75rem 1rem',
    margin: '0 0 1.5rem 0',
    textAlign: 'left',
    overflow: 'auto',
    maxHeight: '80px',
    whiteSpace: 'pre-wrap',
    wordBreak: 'break-word',
  },
  actions: {
    display: 'flex',
    gap: '0.75rem',
    justifyContent: 'center',
  },
  retryBtn: {
    padding: '0.6rem 1.5rem',
    fontSize: '0.875rem',
    fontWeight: '600',
    color: '#ffffff',
    backgroundColor: '#0f3a68',
    border: 'none',
    borderRadius: '8px',
    cursor: 'pointer',
    transition: 'background-color 0.15s ease',
  },
  homeBtn: {
    padding: '0.6rem 1.5rem',
    fontSize: '0.875rem',
    fontWeight: '600',
    color: '#475569',
    backgroundColor: '#f1f5f9',
    border: '1px solid #e2e8f0',
    borderRadius: '8px',
    cursor: 'pointer',
    transition: 'background-color 0.15s ease',
  },
};
