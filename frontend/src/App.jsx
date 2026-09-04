import React, { useState, useEffect } from 'react';
import Navbar from './components/Navbar';
import HomePage from './pages/HomePage';
import AboutPage from './pages/AboutPage';
import ChatModal from './components/ChatModal';
import Footer from './components/Footer';

function App() {
  const getInitialView = () => {
    const path = window.location.pathname.toLowerCase();
    const hash = window.location.hash.toLowerCase();
    if (path === '/about' || hash === '#about' || hash === '#/about') {
      return 'about';
    }
    return 'home';
  };

  const [currentView, setCurrentView] = useState(getInitialView);
  const [isChatOpen, setIsChatOpen] = useState(() => {
    return window.location.hash.toLowerCase() === '#chat';
  });

  useEffect(() => {
    const handleLocationChange = () => {
      const path = window.location.pathname.toLowerCase();
      const hash = window.location.hash.toLowerCase();
      if (path === '/about' || hash === '#about' || hash === '#/about') {
        setCurrentView('about');
        setIsChatOpen(false);
      } else if (hash === '#chat') {
        setIsChatOpen(true);
      } else {
        setCurrentView('home');
      }
    };

    window.addEventListener('hashchange', handleLocationChange);
    window.addEventListener('popstate', handleLocationChange);
    return () => {
      window.removeEventListener('hashchange', handleLocationChange);
      window.removeEventListener('popstate', handleLocationChange);
    };
  }, []);

  const handleNavigate = (view) => {
    if (view === 'chat') {
      setIsChatOpen(true);
      return;
    }
    setCurrentView(view);
    if (view === 'about') {
      try {
        window.history.pushState({ view: 'about' }, '', '/about');
      } catch {
        window.location.hash = 'about';
      }
      window.scrollTo({ top: 0, behavior: 'smooth' });
    } else {
      try {
        window.history.pushState({ view: 'home' }, '', '/');
      } catch {
        window.location.hash = '';
      }
      window.scrollTo({ top: 0, behavior: 'smooth' });
    }
  };

  const handleCloseChat = () => {
    setIsChatOpen(false);
    if (window.location.hash.toLowerCase() === '#chat') {
      try {
        window.history.replaceState(null, '', window.location.pathname);
      } catch {
        window.location.hash = '';
      }
    }
  };

  return (
    <div className="app-root">
      <Navbar
        activeTab={isChatOpen ? 'chat' : currentView}
        isChatView={false}
        onNavigate={handleNavigate}
      />

      {currentView === 'about' ? (
        <AboutPage onStartChat={() => setIsChatOpen(true)} />
      ) : (
        <HomePage onStartChat={() => setIsChatOpen(true)} onNavigate={handleNavigate} />
      )}

      <Footer onNavigate={handleNavigate} />

      {/* Floating Modal AI Legal Assistant */}
      <ChatModal
        isOpen={isChatOpen}
        onClose={handleCloseChat}
      />
    </div>
  );
}

export default App;

