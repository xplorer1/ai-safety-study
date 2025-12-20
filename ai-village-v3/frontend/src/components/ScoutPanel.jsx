import React from 'react';

export function ScoutPanel({ events, selectedIssue, status, modelInfo }) {
  const isRunning = status === 'running' && !selectedIssue;
  const latestEvent = events[events.length - 1];

  return (
    <div className="panel">
      <div className="panel-header">
        <div className="panel-title">
          <span className="panel-icon">{'>'}_</span>
          Scout
        </div>
        <div className="model-badge" style={{ '--badge-color': modelInfo?.color || '#FFD700' }}>
          {modelInfo?.display_name || 'Mistral 7B'}
        </div>
      </div>

      <div className="panel-content">
        {/* Status indicator */}
        <div className="status-row">
          <span className="status-label">Status:</span>
          <span className={`status-value ${isRunning ? 'running' : selectedIssue ? 'complete' : 'idle'}`}>
            {isRunning ? 'Searching...' : selectedIssue ? 'Complete' : 'Idle'}
          </span>
        </div>

        {/* Live activity */}
        {isRunning && latestEvent && (
          <div className="activity-indicator">
            <div className="spinner"></div>
            <span>{latestEvent.message}</span>
          </div>
        )}

        {/* Events feed */}
        <div className="events-container">
          {events.length === 0 && !isRunning && (
            <div className="placeholder-text">
              Click "Rock 'n Roll" to start
            </div>
          )}
          
          {[...events].reverse().map((event, i) => (
            <div key={i} className={`event-item ${event.type}`}>
              <div className="event-type">{event.type}</div>
              <div className="event-message">{event.message}</div>
              {event.data?.score && (
                <div className="event-score">
                  Score: <span className={event.data.score >= 7 ? 'high' : event.data.score >= 5 ? 'medium' : 'low'}>
                    {event.data.score}/10
                  </span>
                </div>
              )}
            </div>
          ))}
        </div>

        {/* Selected issue */}
        {selectedIssue && (
          <div className="selected-issue">
            <div className="issue-header">Selected Issue</div>
            <div className="issue-repo">{selectedIssue.repo}</div>
            <div className="issue-title">
              #{selectedIssue.number}: {selectedIssue.title}
            </div>
            <div className="issue-score">
              AI Score: <span className="score-badge">{selectedIssue.score}/10</span>
            </div>
            <a 
              href={selectedIssue.url} 
              target="_blank" 
              rel="noopener noreferrer"
              className="issue-link"
            >
              View on GitHub
            </a>
          </div>
        )}
      </div>

      <style>{`
        .panel {
          background: var(--bg-card);
          border: 1px solid var(--border-color);
          border-radius: 12px;
          overflow: hidden;
        }

        .panel-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 16px 20px;
          border-bottom: 1px solid var(--border-color);
          background: var(--bg-tertiary);
        }

        .panel-title {
          font-size: 18px;
          font-weight: 600;
          display: flex;
          align-items: center;
          gap: 8px;
        }

        .panel-icon {
          font-family: var(--font-mono);
          color: var(--accent-gold);
        }

        .model-badge {
          font-size: 12px;
          padding: 4px 10px;
          border-radius: 20px;
          background: color-mix(in srgb, var(--badge-color) 15%, transparent);
          color: var(--badge-color);
          border: 1px solid color-mix(in srgb, var(--badge-color) 30%, transparent);
          font-family: var(--font-mono);
        }

        .panel-content {
          padding: 16px 20px;
        }

        .status-row {
          display: flex;
          gap: 8px;
          margin-bottom: 12px;
        }

        .status-label {
          color: var(--text-muted);
        }

        .status-value {
          font-weight: 500;
        }

        .status-value.running {
          color: var(--accent-gold);
        }

        .status-value.complete {
          color: var(--accent-turquoise);
        }

        .status-value.idle {
          color: var(--text-muted);
        }

        .activity-indicator {
          display: flex;
          align-items: center;
          gap: 10px;
          padding: 12px;
          background: color-mix(in srgb, var(--accent-gold) 10%, transparent);
          border-radius: 8px;
          margin-bottom: 12px;
          font-size: 14px;
          color: var(--accent-gold);
        }

        .spinner {
          width: 16px;
          height: 16px;
          border: 2px solid var(--accent-gold);
          border-top-color: transparent;
          border-radius: 50%;
          animation: spin 1s linear infinite;
        }

        @keyframes spin {
          to { transform: rotate(360deg); }
        }

        .events-container {
          max-height: 200px;
          overflow-y: auto;
          margin-bottom: 16px;
        }

        .placeholder-text {
          color: var(--text-muted);
          text-align: center;
          padding: 20px;
          font-style: italic;
        }

        .event-item {
          padding: 10px 12px;
          border-left: 3px solid var(--border-color);
          margin-bottom: 8px;
          background: var(--bg-secondary);
          border-radius: 0 6px 6px 0;
          animation: slideIn 0.3s ease-out;
        }

        .event-item.analysis {
          border-left-color: var(--accent-turquoise);
        }

        .event-item.step {
          border-left-color: var(--accent-gold);
        }

        .event-item.agent_complete {
          border-left-color: var(--accent-lavender);
        }

        .event-type {
          font-size: 10px;
          text-transform: uppercase;
          color: var(--text-muted);
          font-family: var(--font-mono);
          margin-bottom: 4px;
        }

        .event-message {
          font-size: 13px;
          color: var(--text-secondary);
        }

        .event-score {
          margin-top: 6px;
          font-size: 12px;
        }

        .event-score .high { color: var(--accent-turquoise); }
        .event-score .medium { color: var(--accent-gold); }
        .event-score .low { color: var(--accent-coral); }

        .selected-issue {
          padding: 16px;
          background: color-mix(in srgb, var(--accent-turquoise) 8%, var(--bg-secondary));
          border: 1px solid color-mix(in srgb, var(--accent-turquoise) 30%, transparent);
          border-radius: 8px;
        }

        .issue-header {
          font-size: 12px;
          text-transform: uppercase;
          color: var(--accent-turquoise);
          margin-bottom: 8px;
          font-weight: 600;
        }

        .issue-repo {
          font-size: 12px;
          color: var(--text-muted);
          font-family: var(--font-mono);
        }

        .issue-title {
          font-size: 14px;
          font-weight: 500;
          margin: 8px 0;
        }

        .issue-score {
          font-size: 13px;
          color: var(--text-secondary);
        }

        .score-badge {
          font-weight: 600;
          color: var(--accent-turquoise);
        }

        .issue-link {
          display: inline-block;
          margin-top: 12px;
          padding: 8px 16px;
          background: var(--accent-turquoise);
          color: var(--bg-primary);
          text-decoration: none;
          border-radius: 6px;
          font-size: 13px;
          font-weight: 500;
          transition: opacity 0.2s;
        }

        .issue-link:hover {
          opacity: 0.9;
        }
      `}</style>
    </div>
  );
}

