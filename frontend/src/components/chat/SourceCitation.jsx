import React, { useState } from 'react';

/**
 * Expandable Statutory Source Citation Card.
 * Conforms to requirements:
 * - Shows sourceNumber, documentName, pageNumbers, relevanceScore
 * - Compact, subtle border, minimal radius
 * - Expandable: clicking toggles statutory excerpt/snippet
 */
export default function SourceCitation({ source, index }) {
  const [expanded, setExpanded] = useState(false);

  const docName = source.documentName || source.document_name || 'Statutory Source';
  const pageNumbers = source.pageNumbers || source.page_numbers || [];
  const snippet = source.snippet || source.content || '';
  const score = source.relevanceScore !== undefined ? source.relevanceScore : source.relevance_score;

  const pageDisplay = pageNumbers.length > 0 ? `Page ${pageNumbers.join(', ')}` : null;

  const formatRelevance = (val) => {
    if (val === undefined || val === null) return null;
    const num = Number(val);
    if (isNaN(num)) return null;
    if (num >= 0.7) return { text: 'High Relevance', color: '#0d9488', bg: '#f0fdfa' };
    if (num >= 0.4) return { text: 'Relevant', color: '#0284c7', bg: '#f0f9ff' };
    return { text: 'Reference', color: '#64748b', bg: '#f8fafc' };
  };

  const relevance = formatRelevance(score);

  return (
    <div style={styles.card}>
      <button
        type="button"
        onClick={() => setExpanded(!expanded)}
        style={styles.headerButton}
        aria-expanded={expanded}
        title={expanded ? 'Collapse source excerpt' : 'Expand source excerpt'}
      >
        <div style={styles.headerLeft}>
          <span style={styles.badge}>[{index + 1}]</span>
          <div style={styles.titleColumn}>
            <span style={styles.docTitle}>{docName}</span>
            {pageDisplay && <span style={styles.metaText}>{pageDisplay}</span>}
          </div>
        </div>

        <div style={styles.headerRight}>
          {relevance && (
            <span
              style={{
                ...styles.relevancePill,
                color: relevance.color,
                backgroundColor: relevance.bg,
                borderColor: `${relevance.color}33`,
              }}
            >
              {relevance.text}
            </span>
          )}

          <svg
            width="14"
            height="14"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2.2"
            strokeLinecap="round"
            strokeLinejoin="round"
            style={{
              ...styles.chevron,
              transform: expanded ? 'rotate(180deg)' : 'rotate(0deg)',
            }}
          >
            <polyline points="6 9 12 15 18 9" />
          </svg>
        </div>
      </button>

      {expanded && snippet && (
        <div style={styles.excerptBody}>
          <div style={styles.excerptLabel}>Official Statutory Excerpt:</div>
          <div style={styles.excerptText}>"{snippet}"</div>
        </div>
      )}
    </div>
  );
}

const styles = {
  card: {
    backgroundColor: '#ffffff',
    border: '1px solid #e2e8f0',
    borderRadius: '6px',
    marginBottom: '0.45rem',
    overflow: 'hidden',
    transition: 'border-color 0.15s ease, box-shadow 0.15s ease',
  },
  headerButton: {
    width: '100%',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '0.55rem 0.75rem',
    backgroundColor: 'transparent',
    border: 'none',
    cursor: 'pointer',
    textAlign: 'left',
    gap: '0.65rem',
  },
  headerLeft: {
    display: 'flex',
    alignItems: 'flex-start',
    gap: '0.55rem',
    flex: 1,
    minWidth: 0,
  },
  badge: {
    fontSize: '0.75rem',
    fontWeight: '700',
    color: '#0d9488',
    backgroundColor: '#f0fdfa',
    border: '1px solid #ccfbf1',
    borderRadius: '4px',
    padding: '0.1rem 0.35rem',
    flexShrink: 0,
    marginTop: '0.1rem',
  },
  titleColumn: {
    display: 'flex',
    flexDirection: 'column',
    gap: '0.15rem',
    minWidth: 0,
  },
  docTitle: {
    fontSize: '0.8125rem', /* 13px */
    fontWeight: '600',
    color: '#0f172a',
    lineHeight: '1.35',
    wordBreak: 'break-word',
  },
  metaText: {
    fontSize: '0.6875rem', /* 11px */
    color: '#64748b',
    fontWeight: '500',
  },
  headerRight: {
    display: 'flex',
    alignItems: 'center',
    gap: '0.5rem',
    flexShrink: 0,
  },
  relevancePill: {
    fontSize: '0.625rem', /* 10px */
    fontWeight: '600',
    border: '1px solid transparent',
    borderRadius: '9999px',
    padding: '0.15rem 0.5rem',
    textTransform: 'uppercase',
    letterSpacing: '0.04em',
  },
  chevron: {
    color: '#94a3b8',
    transition: 'transform 0.2s ease',
  },
  excerptBody: {
    padding: '0.55rem 0.85rem 0.75rem 0.85rem',
    borderTop: '1px solid #f1f5f9',
    backgroundColor: '#f8fafc',
  },
  excerptLabel: {
    fontSize: '0.6875rem',
    fontWeight: '600',
    color: '#475569',
    marginBottom: '0.3rem',
    textTransform: 'uppercase',
    letterSpacing: '0.03em',
  },
  excerptText: {
    fontSize: '0.78125rem', /* 12.5px */
    color: '#334155',
    lineHeight: '1.55',
    fontStyle: 'italic',
    whiteSpace: 'pre-wrap',
    wordBreak: 'break-word',
  },
};
