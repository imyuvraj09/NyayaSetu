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

  const isCaseLaw = source.evidenceType === 'CASE_LAW' || source.evidence_type === 'CASE_LAW';
  const docName = source.caseName || source.documentName || source.document_name || (isCaseLaw ? 'Judicial Decision' : 'Statutory Source');
  const pageNumbers = source.pageNumbers || source.page_numbers || [];
  const paragraphNumber = source.paragraphNumber || source.paragraph_number;
  const citation = source.citation || '';
  const court = source.court || '';
  const snippet = source.snippet || source.content || '';
  const score = source.relevanceScore !== undefined ? source.relevanceScore : source.relevance_score;
  const isHolding = Boolean(source.isHoldingOrRatio || source.is_holding_or_ratio);

  const locDisplay = isCaseLaw
    ? [court, citation, paragraphNumber ? `Para ${paragraphNumber}` : null].filter(Boolean).join(' • ')
    : (pageNumbers.length > 0 ? `Page ${pageNumbers.join(', ')}` : null);

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
    <div style={{ ...styles.card, borderColor: isCaseLaw ? '#cbd5e1' : '#e2e8f0' }}>
      <button
        type="button"
        onClick={() => setExpanded(!expanded)}
        style={{
          ...styles.headerButton,
          backgroundColor: isCaseLaw ? '#f8fafc' : 'transparent',
        }}
        aria-expanded={expanded}
        title={expanded ? 'Collapse source excerpt' : 'Expand source excerpt'}
      >
        <div style={styles.headerLeft}>
          <span
            style={{
              ...styles.badge,
              color: isCaseLaw ? '#4338ca' : '#0d9488',
              backgroundColor: isCaseLaw ? '#eef2ff' : '#f0fdfa',
              borderColor: isCaseLaw ? '#c7d2fe' : '#ccfbf1',
            }}
          >
            {isCaseLaw ? `[C${index + 1}]` : `[S${index + 1}]`}
          </span>
          <div style={styles.titleColumn}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', flexWrap: 'wrap' }}>
              <span style={styles.docTitle}>{docName}</span>
              {isCaseLaw && (
                <span style={styles.caseLawTag}>Case Law</span>
              )}
              {isHolding && (
                <span style={styles.ratioTag}>Holding / Ratio</span>
              )}
            </div>
            {locDisplay && <span style={styles.metaText}>{locDisplay}</span>}
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
          <div style={styles.excerptLabel}>
            {isCaseLaw ? 'Verified Judicial Excerpt / Ratio:' : 'Official Statutory Excerpt:'}
          </div>
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
  caseLawTag: {
    fontSize: '0.625rem',
    fontWeight: '700',
    color: '#4338ca',
    backgroundColor: '#eef2ff',
    border: '1px solid #c7d2fe',
    borderRadius: '3px',
    padding: '0.05rem 0.35rem',
    textTransform: 'uppercase',
    letterSpacing: '0.03em',
  },
  ratioTag: {
    fontSize: '0.625rem',
    fontWeight: '700',
    color: '#b45309',
    backgroundColor: '#fffbeb',
    border: '1px solid #fde68a',
    borderRadius: '3px',
    padding: '0.05rem 0.35rem',
    textTransform: 'uppercase',
    letterSpacing: '0.03em',
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
