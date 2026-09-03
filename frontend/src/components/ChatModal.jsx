import React, { useState, useEffect, useRef } from 'react';
import ChatWorkspace from './chat/ChatWorkspace';

export default function ChatModal({ isOpen, onClose }) {
  const [isExpanded, setIsExpanded] = useState(false);
  const overlayRef = useRef(null);

  // Focus and body scroll lock
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden';
      return () => {
        document.body.style.overflow = '';
      };
    }
  }, [isOpen]);

  // Keyboard Escape to close
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const handleOverlayClick = (e) => {
    if (e.target === overlayRef.current) {
      onClose();
    }
  };

  return (
    <div
      ref={overlayRef}
      onClick={handleOverlayClick}
      style={styles.overlay}
      className="legal-modal-backdrop"
      aria-modal="true"
      role="dialog"
    >
      <div
        style={{
          ...styles.modalWindow,
          ...(isExpanded ? styles.modalExpanded : {}),
        }}
        className="legal-chat-modal"
      >
        <ChatWorkspace
          onClose={onClose}
          isExpanded={isExpanded}
          onToggleExpand={() => setIsExpanded(!isExpanded)}
        />
      </div>
    </div>
  );
}

const styles = {
  overlay: {
    position: 'fixed',
    inset: 0,
    zIndex: 9999,
    backgroundColor: 'rgba(15, 23, 42, 0.52)',
    backdropFilter: 'blur(8px)',
    WebkitBackdropFilter: 'blur(8px)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    padding: '1rem',
    animation: 'modalBackdropFadeIn 0.22s ease-out forwards',
  },
  modalWindow: {
    width: 'min(1080px, 95vw)',
    height: 'min(720px, 90vh)',
    backgroundColor: '#ffffff',
    borderRadius: '16px',
    border: '1px solid #cbd5e1',
    boxShadow:
      '0 25px 60px -15px rgba(15, 23, 42, 0.35), 0 10px 25px -5px rgba(15, 23, 42, 0.15)',
    display: 'flex',
    flexDirection: 'column',
    overflow: 'hidden',
    animation: 'modalScaleIn 0.24s cubic-bezier(0.16, 1, 0.3, 1) forwards',
    transition: 'width 0.2s ease, height 0.2s ease, border-radius 0.2s ease',
  },
  modalExpanded: {
    width: '98vw',
    height: '96vh',
    borderRadius: '10px',
  },
};
