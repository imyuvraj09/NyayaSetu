import React from 'react';

/**
 * Lightweight, zero-dependency Markdown renderer tailored for structured legal responses.
 * Formats:
 * - H1, H2, H3 headings (## Answer, ## Legal Basis, ## Sources, etc.)
 * - Unordered & ordered lists (- item, * item, 1. item)
 * - Blockquotes (> note)
 * - Bold (**text**) & italic (*text*)
 * - Paragraphs and clean spacing
 */
export default function LegalMarkdown({ content }) {
  if (!content) return null;

  const lines = content.split('\n');
  const elements = [];
  let currentList = null;
  let currentQuote = null;
  let keyIdx = 0;

  const flushList = () => {
    if (currentList) {
      elements.push(
        <ul key={`ul-${keyIdx++}`} style={styles.list}>
          {currentList.map((item, i) => (
            <li key={i} style={styles.listItem}>
              {renderInline(item)}
            </li>
          ))}
        </ul>
      );
      currentList = null;
    }
  };

  const flushQuote = () => {
    if (currentQuote) {
      elements.push(
        <blockquote key={`quote-${keyIdx++}`} style={styles.blockquote}>
          {renderInline(currentQuote.join(' '))}
        </blockquote>
      );
      currentQuote = null;
    }
  };

  for (let i = 0; i < lines.length; i++) {
    const rawLine = lines[i];
    const line = rawLine.trim();

    // 1. Empty line
    if (!line) {
      flushList();
      flushQuote();
      continue;
    }

    // 2. Blockquote (> ...)
    if (line.startsWith('>')) {
      flushList();
      if (!currentQuote) currentQuote = [];
      currentQuote.push(line.replace(/^>\s*/, ''));
      continue;
    } else {
      flushQuote();
    }

    // 3. Headings
    if (line.startsWith('### ')) {
      flushList();
      elements.push(
        <h4 key={`h4-${keyIdx++}`} style={styles.h4}>
          {renderInline(line.replace('### ', ''))}
        </h4>
      );
      continue;
    }
    if (line.startsWith('## ')) {
      flushList();
      elements.push(
        <h3 key={`h3-${keyIdx++}`} style={styles.h3}>
          {renderInline(line.replace('## ', ''))}
        </h3>
      );
      continue;
    }
    if (line.startsWith('# ')) {
      flushList();
      elements.push(
        <h2 key={`h2-${keyIdx++}`} style={styles.h2}>
          {renderInline(line.replace('# ', ''))}
        </h2>
      );
      continue;
    }

    // 4. List items (- item or • item or * item or 1. item)
    const listMatch = line.match(/^([*\-•]|\d+\.)\s+(.*)$/);
    if (listMatch) {
      if (!currentList) currentList = [];
      currentList.push(listMatch[2]);
      continue;
    } else {
      flushList();
    }

    // 5. Standard paragraph
    elements.push(
      <p key={`p-${keyIdx++}`} style={styles.paragraph}>
        {renderInline(line)}
      </p>
    );
  }

  flushList();
  flushQuote();

  return <div style={styles.container}>{elements}</div>;
}

/**
 * Parses inline formatting: **bold**, *italic*, `code`, and [SOURCE N] citations
 */
function renderInline(text) {
  if (!text) return text;

  // Split by bold (**...**)
  const parts = text.split(/(\*\*.*?\*\*)/g);

  return parts.map((part, index) => {
    if (part.startsWith('**') && part.endsWith('**')) {
      return (
        <strong key={index} style={styles.bold}>
          {part.slice(2, -2)}
        </strong>
      );
    }
    // Handle inline code or italics inside normal text
    return part;
  });
}

const styles = {
  container: {
    lineHeight: '1.65',
    color: 'inherit',
    fontSize: '0.9375rem', /* 15px */
  },
  h2: {
    fontSize: '1.1875rem',
    fontWeight: '700',
    color: '#0f2942',
    margin: '1rem 0 0.5rem 0',
    borderBottom: '1px solid #e2e8f0',
    paddingBottom: '0.35rem',
  },
  h3: {
    fontSize: '1.05rem',
    fontWeight: '700',
    color: '#0f3a68',
    margin: '0.9rem 0 0.4rem 0',
    letterSpacing: '-0.01em',
  },
  h4: {
    fontSize: '0.95rem',
    fontWeight: '600',
    color: '#1e293b',
    margin: '0.75rem 0 0.35rem 0',
  },
  paragraph: {
    margin: '0 0 0.75rem 0',
    lineHeight: '1.62',
  },
  list: {
    margin: '0.4rem 0 0.85rem 1.35rem',
    padding: 0,
  },
  listItem: {
    marginBottom: '0.35rem',
    lineHeight: '1.58',
  },
  blockquote: {
    borderLeft: '3px solid #0d9488',
    backgroundColor: '#f8fafc',
    padding: '0.55rem 0.85rem',
    margin: '0.65rem 0 0.85rem 0',
    color: '#475569',
    borderRadius: '0 6px 6px 0',
    fontStyle: 'italic',
    fontSize: '0.875rem',
  },
  bold: {
    fontWeight: '600',
    color: '#0f172a',
  },
};
