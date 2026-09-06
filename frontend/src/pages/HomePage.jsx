import React from 'react';
import HeroSection from '../components/HeroSection';
import TrustSection from '../components/TrustSection';
import ConnectSection from '../components/ConnectSection';

export default function HomePage({ onStartChat, onNavigate }) {
  return (
    <main>
      <HeroSection onStartChat={onStartChat} onNavigate={onNavigate} />
      <ConnectSection />
    </main>
  );
}
