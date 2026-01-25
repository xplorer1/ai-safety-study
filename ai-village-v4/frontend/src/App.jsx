import React, { useState } from 'react';
import { EpisodeDashboard } from './components/EpisodeDashboard';
import { OfficerProfiles } from './components/OfficerProfiles';
import { CaptainsLog } from './components/CaptainsLog';
import { ResearchView } from './components/ResearchView';

function App() {
  const [activeTab, setActiveTab] = useState('research');

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
            USS Terminator
          </h1>
          <p style={{ margin: '5px 0 0 0', color: 'var(--text-muted)', fontSize: '12px' }}>
            Starship Voyager Edition
          </p>
        </div>
        <nav style={{ display: 'flex', gap: '10px' }}>
          {['research', 'episodes', 'officers', 'log'].map(tab => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              style={{
                padding: '8px 16px',
                background: activeTab === tab ? 'var(--accent-gold)' : 'var(--bg-tertiary)',
                border: '1px solid var(--border-color)',
                borderRadius: '6px',
                color: activeTab === tab ? 'var(--bg-primary)' : 'var(--text-primary)',
                cursor: 'pointer',
                textTransform: 'capitalize'
              }}
            >
              {tab}
            </button>
          ))}
        </nav>
      </header>

      {/* Main Content */}
      <main style={{ flex: 1 }}>
        {activeTab === 'research' && <ResearchView />}
        {activeTab === 'episodes' && <EpisodeDashboard />}
        {activeTab === 'officers' && <OfficerProfiles />}
        {activeTab === 'log' && <CaptainsLog />}
      </main>
    </div>
  );
}

export default App;

