import React, { useState, useEffect } from 'react';
import { useWebSocket } from './hooks/useWebSocket';
import { ScoutPanel } from './components/ScoutPanel';
import { RoundtablePanel } from './components/RoundtablePanel';
import { ResultsPanel } from './components/ResultsPanel';

function App() {
  const [config, setConfig] = useState(null);
  const [repo, setRepo] = useState('pandas-dev/pandas');
  
  const {
    isConnected,
    status,
    scoutEvents,
    roundtableEvents,
    selectedIssue,
    winningFix,
    startPipeline
  } = useWebSocket('ws://localhost:8000/ws/pipeline');

  // Fetch config on mount
  useEffect(() => {
    fetch('http://localhost:8000/api/config')
      .then(res => res.json())
      .then(data => setConfig(data))
      .catch(err => console.error('Failed to fetch config:', err));
  }, []);

  const handleStart = () => {
    startPipeline(repo);
  };

  const isRunning = status === 'running';

  return (
    <div className="app">
      {/* Header */}
      <header className="header">
        <div className="header-left">
          <h1 className="logo">
            <span className="logo-bracket">[</span>
            AI Village
            <span className="logo-bracket">]</span>
          </h1>
          <p className="tagline">
            Multi-Agent OSS Collaboration
            <span className="mode-badge">{config?.mode?.toUpperCase() || 'REMOTE'}</span>
          </p>
        </div>
        
        <div className="header-center">
          <div className={`connection-status ${isConnected ? 'connected' : 'disconnected'}`}>
            <span className="status-dot"></span>
            {isConnected ? 'Connected' : 'Connecting...'}
          </div>
          
          {status === 'running' && (
            <div className="pipeline-status">
              <div className="pulse-ring"></div>
              Pipeline Running
            </div>
          )}
        </div>

        <div className="header-right">
          <div className="repo-input-group">
            <input
              type="text"
              value={repo}
              onChange={(e) => setRepo(e.target.value)}
              placeholder="owner/repo"
              className="repo-input"
              disabled={isRunning}
            />
          </div>
          <button 
            className={`start-button ${isRunning ? 'running' : ''}`}
            onClick={handleStart}
            disabled={!isConnected || isRunning}
          >
            {isRunning ? 'Running...' : "Rock 'n Roll"}
          </button>
        </div>
      </header>

      {/* Main content */}
      <main className="main-grid">
        <div className="panel-wrapper scout">
          <ScoutPanel 
            events={scoutEvents}
            selectedIssue={selectedIssue}
            status={status}
            modelInfo={config?.models?.scout}
          />
        </div>
        
        <div className="panel-wrapper roundtable">
          <RoundtablePanel 
            events={roundtableEvents}
            status={status}
            models={config?.models}
          />
        </div>
        
        <div className="panel-wrapper results">
          <ResultsPanel 
            winningFix={winningFix}
            status={status}
          />
        </div>
      </main>

      {/* Footer */}
      <footer className="footer">
        <div className="footer-left">
          {selectedIssue && (
            <span>Working on: #{selectedIssue.number} in {selectedIssue.repo}</span>
          )}
        </div>
        <div className="footer-right">
          <span className="tech-stack">FastAPI + React + WebSocket</span>
        </div>
      </footer>

      <style>{`
        .app {
          min-height: 100vh;
          display: flex;
          flex-direction: column;
        }

        /* Header */
        .header {
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 16px 24px;
          background: var(--bg-secondary);
          border-bottom: 1px solid var(--border-color);
        }

        .header-left {
          display: flex;
          flex-direction: column;
          gap: 4px;
        }

        .logo {
          font-size: 24px;
          font-weight: 700;
          margin: 0;
          letter-spacing: -0.5px;
        }

        .logo-bracket {
          color: var(--accent-gold);
          font-weight: 400;
        }

        .tagline {
          font-size: 13px;
          color: var(--text-muted);
          display: flex;
          align-items: center;
          gap: 10px;
        }

        .mode-badge {
          font-size: 10px;
          padding: 2px 8px;
          background: var(--accent-lavender);
          color: var(--bg-primary);
          border-radius: 4px;
          font-weight: 600;
        }

        .header-center {
          display: flex;
          align-items: center;
          gap: 20px;
        }

        .connection-status {
          display: flex;
          align-items: center;
          gap: 8px;
          font-size: 13px;
          color: var(--text-muted);
        }

        .status-dot {
          width: 8px;
          height: 8px;
          border-radius: 50%;
          background: var(--text-muted);
        }

        .connection-status.connected .status-dot {
          background: var(--accent-turquoise);
          box-shadow: 0 0 8px var(--accent-turquoise);
        }

        .pipeline-status {
          display: flex;
          align-items: center;
          gap: 10px;
          font-size: 14px;
          color: var(--accent-gold);
          font-weight: 500;
        }

        .pulse-ring {
          width: 12px;
          height: 12px;
          border-radius: 50%;
          background: var(--accent-gold);
          animation: pulse-ring 1.5s ease-out infinite;
        }

        @keyframes pulse-ring {
          0% {
            box-shadow: 0 0 0 0 rgba(251, 191, 36, 0.7);
          }
          70% {
            box-shadow: 0 0 0 10px rgba(251, 191, 36, 0);
          }
          100% {
            box-shadow: 0 0 0 0 rgba(251, 191, 36, 0);
          }
        }

        .header-right {
          display: flex;
          align-items: center;
          gap: 12px;
        }

        .repo-input-group {
          position: relative;
        }

        .repo-input {
          padding: 10px 16px;
          background: var(--bg-tertiary);
          border: 1px solid var(--border-color);
          border-radius: 8px;
          color: var(--text-primary);
          font-size: 14px;
          font-family: var(--font-mono);
          width: 200px;
          transition: border-color 0.2s;
        }

        .repo-input:focus {
          outline: none;
          border-color: var(--accent-gold);
        }

        .repo-input:disabled {
          opacity: 0.5;
        }

        .start-button {
          padding: 10px 24px;
          background: linear-gradient(135deg, var(--accent-gold), #f59e0b);
          border: none;
          border-radius: 8px;
          color: var(--bg-primary);
          font-size: 14px;
          font-weight: 600;
          cursor: pointer;
          transition: all 0.2s;
          font-family: var(--font-sans);
        }

        .start-button:hover:not(:disabled) {
          transform: translateY(-2px);
          box-shadow: 0 4px 12px rgba(251, 191, 36, 0.4);
        }

        .start-button:disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }

        .start-button.running {
          background: var(--bg-tertiary);
          color: var(--accent-gold);
          border: 1px solid var(--accent-gold);
        }

        /* Main grid */
        .main-grid {
          flex: 1;
          display: grid;
          grid-template-columns: 1fr 2fr 1fr;
          gap: 20px;
          padding: 20px 24px;
          min-height: 0;
        }

        .panel-wrapper {
          min-height: 0;
          overflow: hidden;
          display: flex;
          flex-direction: column;
        }

        .panel-wrapper > * {
          flex: 1;
          min-height: 0;
        }

        /* Footer */
        .footer {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 12px 24px;
          background: var(--bg-secondary);
          border-top: 1px solid var(--border-color);
          font-size: 12px;
          color: var(--text-muted);
        }

        .tech-stack {
          font-family: var(--font-mono);
          color: var(--text-muted);
        }

        /* Responsive */
        @media (max-width: 1200px) {
          .main-grid {
            grid-template-columns: 1fr 1fr;
          }
          
          .panel-wrapper.results {
            grid-column: span 2;
          }
        }

        @media (max-width: 768px) {
          .main-grid {
            grid-template-columns: 1fr;
          }
          
          .panel-wrapper.results {
            grid-column: span 1;
          }
          
          .header {
            flex-wrap: wrap;
            gap: 12px;
          }
          
          .header-center {
            order: 3;
            width: 100%;
            justify-content: center;
          }
        }
      `}</style>
    </div>
  );
}

export default App;

