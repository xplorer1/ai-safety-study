import React, { useState } from 'react';
import { BridgeView } from './components/BridgeView';
import { EpisodeDashboard } from './components/EpisodeDashboard';
import { VotingPanel } from './components/VotingPanel';
import { OfficerProfiles } from './components/OfficerProfiles';
import { CaptainsLog } from './components/CaptainsLog';

function App() {
  const [activeTab, setActiveTab] = useState('bridge');
  const [currentEpisodeId, setCurrentEpisodeId] = useState(null);

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
            Starship Voyager Edition
          </p>
        </div>
        <nav style={{ display: 'flex', gap: '10px' }}>
          {['bridge', 'episodes', 'officers', 'log'].map(tab => (
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
      <main style={{ flex: 1, display: 'flex' }}>
        <div style={{ flex: 1 }}>
          {activeTab === 'bridge' && <BridgeView episodeId={currentEpisodeId} />}
          {activeTab === 'episodes' && <EpisodeDashboard />}
          {activeTab === 'officers' && <OfficerProfiles />}
          {activeTab === 'log' && <CaptainsLog />}
        </div>
        
        {activeTab === 'bridge' && currentEpisodeId && (
          <aside style={{ width: '300px', padding: '20px', background: 'var(--bg-secondary)', borderLeft: '1px solid var(--border-color)' }}>
            <VotingPanel episodeId={currentEpisodeId} />
          </aside>
        )}
      </main>
    </div>
  );
}

export default App;

