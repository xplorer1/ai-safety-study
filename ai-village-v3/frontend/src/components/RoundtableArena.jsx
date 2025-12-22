import React from 'react';

const MODE_CONFIG = {
  baseline: {
    name: 'Baseline',
    description: 'Single LLM (Control)',
    color: '#6b7280',
    agents: 1
  },
  debate_light: {
    name: 'Debate Light',
    description: '3 LLMs, 1 Round',
    color: '#f59e0b',
    agents: 3
  },
  debate_full: {
    name: 'Debate Full',
    description: '3 LLMs, 3 Rounds',
    color: '#10b981',
    agents: 3
  },
  ensemble: {
    name: 'Ensemble',
    description: '3 LLMs, Blind Vote',
    color: '#8b5cf6',
    agents: 3
  }
};

function ExperimentPanel({ mode, experiment, currentIssue }) {
  const config = MODE_CONFIG[mode];
  const { status, events, result } = experiment;
  
  // Get last few events for display
  const recentEvents = events.slice(-8);
  
  return (
    <div className="experiment-panel" style={{ '--mode-color': config.color }}>
      <div className="panel-header">
        <div className="panel-title">
          <span className="mode-indicator"></span>
          {config.name}
        </div>
        <div className="panel-meta">
          <span className="agent-count">{config.agents} LLM{config.agents > 1 ? 's' : ''}</span>
          <span className={`status-badge ${status}`}>{status}</span>
        </div>
      </div>

      <div className="panel-description">{config.description}</div>

      <div className="panel-content">
        {(status === 'idle' || (status === 'running' && events.length === 0)) && !result && (
          <div className="waiting-state">
            <div className="waiting-icon">
              <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                <circle cx="12" cy="12" r="10" />
                <path d="M12 6v6l4 2" />
              </svg>
            </div>
            <div className="waiting-text">
              {status === 'idle' ? 'Waiting for issue...' : 'Starting experiment...'}
            </div>
          </div>
        )}

        {status === 'running' && (
          <div className="activity-feed">
            {recentEvents.map((event, i) => (
              <div key={i} className={`event-item ${event.type}`}>
                <span className="event-agent">{event.agent || mode}</span>
                <span className="event-message">
                  {event.message?.slice(0, 80)}{event.message?.length > 80 ? '...' : ''}
                </span>
              </div>
            ))}
            <div className="thinking-indicator">
              <span className="dot"></span>
              <span className="dot"></span>
              <span className="dot"></span>
            </div>
          </div>
        )}

        {status === 'complete' && result && (
          <div className="result-display">
            <div className="winner-badge">
              <span className="winner-label">Winner</span>
              <span className="winner-name">{result.winner_name || result.winner}</span>
            </div>
            {result.vote_count && (
              <div className="vote-info">
                {result.vote_count} vote{result.vote_count > 1 ? 's' : ''}
                {result.consensus_type && ` (${result.consensus_type})`}
              </div>
            )}
            <div className="fix-preview">
              <div className="fix-label">Proposed Fix</div>
              <pre className="fix-code">
                {result.fix?.slice(0, 300)}{result.fix?.length > 300 ? '...' : ''}
              </pre>
            </div>
          </div>
        )}
      </div>

      <style>{`
        .experiment-panel {
          background: var(--bg-secondary);
          border: 1px solid var(--border-color);
          border-radius: 12px;
          display: flex;
          flex-direction: column;
          overflow: hidden;
        }

        .panel-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 12px 16px;
          background: var(--bg-tertiary);
          border-bottom: 1px solid var(--border-color);
        }

        .panel-title {
          display: flex;
          align-items: center;
          gap: 8px;
          font-weight: 600;
          font-size: 14px;
        }

        .mode-indicator {
          width: 8px;
          height: 8px;
          border-radius: 50%;
          background: var(--mode-color);
        }

        .panel-meta {
          display: flex;
          align-items: center;
          gap: 8px;
        }

        .agent-count {
          font-size: 11px;
          color: var(--text-muted);
        }

        .status-badge {
          font-size: 10px;
          padding: 2px 8px;
          border-radius: 10px;
          font-weight: 600;
          text-transform: uppercase;
        }

        .status-badge.idle {
          background: var(--bg-primary);
          color: var(--text-muted);
        }

        .status-badge.running {
          background: color-mix(in srgb, var(--mode-color) 20%, transparent);
          color: var(--mode-color);
          animation: pulse 1.5s infinite;
        }

        .status-badge.complete {
          background: color-mix(in srgb, var(--accent-turquoise) 20%, transparent);
          color: var(--accent-turquoise);
        }

        .panel-description {
          padding: 8px 16px;
          font-size: 11px;
          color: var(--text-muted);
          border-bottom: 1px solid var(--border-color);
        }

        .panel-content {
          flex: 1;
          padding: 12px;
          overflow-y: auto;
          min-height: 0;
        }

        /* Waiting State */
        .waiting-state {
          height: 100%;
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          color: var(--text-muted);
          gap: 12px;
        }

        .waiting-icon {
          opacity: 0.5;
        }

        .waiting-text {
          font-size: 12px;
        }

        /* Activity Feed */
        .activity-feed {
          display: flex;
          flex-direction: column;
          gap: 6px;
        }

        .event-item {
          display: flex;
          flex-direction: column;
          gap: 2px;
          padding: 8px;
          background: var(--bg-tertiary);
          border-radius: 6px;
          font-size: 11px;
          border-left: 2px solid var(--mode-color);
        }

        .event-agent {
          font-weight: 600;
          color: var(--mode-color);
          text-transform: capitalize;
          font-size: 10px;
        }

        .event-message {
          color: var(--text-secondary);
          line-height: 1.4;
        }

        .thinking-indicator {
          display: flex;
          gap: 4px;
          justify-content: center;
          padding: 8px;
        }

        .thinking-indicator .dot {
          width: 6px;
          height: 6px;
          background: var(--mode-color);
          border-radius: 50%;
          animation: bounce 1.4s infinite ease-in-out both;
        }

        .thinking-indicator .dot:nth-child(1) { animation-delay: -0.32s; }
        .thinking-indicator .dot:nth-child(2) { animation-delay: -0.16s; }

        @keyframes bounce {
          0%, 80%, 100% { transform: scale(0); }
          40% { transform: scale(1); }
        }

        /* Result Display */
        .result-display {
          display: flex;
          flex-direction: column;
          gap: 12px;
        }

        .winner-badge {
          display: flex;
          flex-direction: column;
          align-items: center;
          padding: 16px;
          background: color-mix(in srgb, var(--mode-color) 10%, var(--bg-tertiary));
          border: 1px solid color-mix(in srgb, var(--mode-color) 30%, transparent);
          border-radius: 8px;
        }

        .winner-label {
          font-size: 10px;
          color: var(--text-muted);
          text-transform: uppercase;
          letter-spacing: 1px;
        }

        .winner-name {
          font-size: 16px;
          font-weight: 600;
          color: var(--mode-color);
          margin-top: 4px;
        }

        .vote-info {
          text-align: center;
          font-size: 12px;
          color: var(--text-muted);
        }

        .fix-preview {
          background: var(--bg-primary);
          border: 1px solid var(--border-color);
          border-radius: 8px;
          overflow: hidden;
        }

        .fix-label {
          padding: 8px 12px;
          font-size: 10px;
          color: var(--text-muted);
          text-transform: uppercase;
          background: var(--bg-tertiary);
          border-bottom: 1px solid var(--border-color);
        }

        .fix-code {
          padding: 12px;
          margin: 0;
          font-size: 11px;
          font-family: var(--font-mono);
          color: var(--text-secondary);
          white-space: pre-wrap;
          word-break: break-word;
          max-height: 120px;
          overflow-y: auto;
        }
      `}</style>
    </div>
  );
}

export function RoundtableArena({ experiments, currentIssue }) {
  const modes = ['baseline', 'debate_light', 'debate_full', 'ensemble'];

  return (
    <div className="arena">
      <div className="arena-header">
        <h2>Roundtable Arena</h2>
        <p className="arena-subtitle">
          {currentIssue 
            ? `Experimenting on #${currentIssue.github_number || currentIssue.number}`
            : 'Waiting for issue from queue...'}
        </p>
      </div>

      <div className="arena-grid">
        {modes.map(mode => (
          <ExperimentPanel
            key={mode}
            mode={mode}
            experiment={experiments[mode]}
            currentIssue={currentIssue}
          />
        ))}
      </div>

      <style>{`
        .arena {
          height: 100%;
          display: flex;
          flex-direction: column;
        }

        .arena-header {
          margin-bottom: 16px;
        }

        .arena-header h2 {
          font-size: 18px;
          font-weight: 600;
          margin: 0 0 4px 0;
        }

        .arena-subtitle {
          font-size: 13px;
          color: var(--text-muted);
          margin: 0;
        }

        .arena-grid {
          flex: 1;
          display: grid;
          grid-template-columns: 1fr 1fr;
          grid-template-rows: 1fr 1fr;
          gap: 16px;
          min-height: 0;
        }

        @media (max-width: 1000px) {
          .arena-grid {
            grid-template-columns: 1fr;
            grid-template-rows: repeat(4, 1fr);
          }
        }
      `}</style>
    </div>
  );
}

