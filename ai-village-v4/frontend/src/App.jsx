import React, { useState } from 'react';
import { ResearchView } from './components/ResearchView';
import { EpisodeDashboard } from './components/EpisodeDashboard';

function App() {
  const [activeTab, setActiveTab] = useState('research');

  const tabs = [
    { id: 'research', label: 'Research Lab', color: 'var(--accent-lavender)' },
    { id: 'episodes', label: 'Episodes History', color: 'var(--accent-turquoise)' },
  ];

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      {/* Header */}
      <header style={{
        padding: '15px 30px',
        background: 'var(--bg-secondary)',
        borderBottom: '1px solid var(--border-color)',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center'
      }}>
        <div>
          <h1 style={{ margin: 0, color: 'var(--accent-gold)', fontSize: '24px' }}>
            USS AI Village
          </h1>
          <p style={{ margin: '5px 0 0 0', color: 'var(--text-muted)', fontSize: '12px' }}>
            AI Safety Research Platform v5
          </p>
        </div>
        <nav style={{ display: 'flex', gap: '10px' }}>
          {tabs.map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              style={{
                padding: '8px 16px',
                background: activeTab === tab.id ? tab.color : 'var(--bg-tertiary)',
                border: '1px solid var(--border-color)',
                borderRadius: '6px',
                color: activeTab === tab.id ? 'var(--bg-primary)' : 'var(--text-primary)',
                cursor: 'pointer',
                fontWeight: activeTab === tab.id ? '600' : 'normal'
              }}
            >
              {tab.label}
            </button>
          ))}
        </nav>
      </header>

      {/* Main Content */}
      <main style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
        <div style={{ flex: 1, overflow: 'auto' }}>
          {activeTab === 'research' && <ResearchView />}
          {activeTab === 'episodes' && <EpisodeDashboard />}
        </div>
      </main>
    </div>
  );
}

export default App;

