import React from 'react';

export function ScoutPanel({ queueStatus, currentIssue, events = [], status = 'idle' }) {
  const recentEvents = events.slice(-5);
  
  return (
    <div className="scout-panel">
      <div className="panel-header">
        <h2>Scout</h2>
        <span className={`status-badge ${status}`}>
          {status === 'running' ? 'Running...' : status === 'complete' ? 'Complete' : 'Auto @ Noon'}
        </span>
      </div>

      {/* Discovery Activity */}
      {status === 'running' && (
        <div className="discovery-activity">
          <div className="section-label">Discovery Progress</div>
          <div className="activity-feed">
            {recentEvents.map((event, i) => (
              <div key={i} className={`activity-item ${event.type}`}>
                <span className="activity-message">{event.message}</span>
              </div>
            ))}
            <div className="thinking-indicator">
              <span className="dot"></span>
              <span className="dot"></span>
              <span className="dot"></span>
            </div>
          </div>
        </div>
      )}

      {/* Current Issue */}
      {currentIssue && (
        <div className="current-issue">
          <div className="section-label">Now Processing</div>
          <div className="issue-card active">
            <div className="issue-number">#{currentIssue.github_number || currentIssue.number}</div>
            <div className="issue-title">{currentIssue.title?.slice(0, 60)}...</div>
            <div className="issue-meta">
              <span className="repo">{currentIssue.repo_name || currentIssue.repo}</span>
              {currentIssue.score && (
                <span className="score">Score: {currentIssue.score}/10</span>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Queue Stats */}
      <div className="queue-section">
        <div className="section-label">Issue Queue</div>
        <div className="queue-stats">
          <div className="stat">
            <span className="stat-value">{queueStatus.ready || 0}</span>
            <span className="stat-label">Ready</span>
          </div>
          <div className="stat">
            <span className="stat-value">{queueStatus.processing || 0}</span>
            <span className="stat-label">Processing</span>
          </div>
        </div>
      </div>

      {/* Pending Issues */}
      <div className="pending-section">
        <div className="section-label">Up Next</div>
        <div className="pending-list">
          {queueStatus.pending?.slice(0, 5).map((issue, i) => (
            <div key={issue.id || i} className="pending-item">
              <span className="pending-score">{issue.score}</span>
              <span className="pending-title">{issue.title?.slice(0, 35)}...</span>
            </div>
          ))}
          {(!queueStatus.pending || queueStatus.pending.length === 0) && (
            <div className="empty-queue">
              Queue empty. Click "Run Scout Now" to discover issues.
            </div>
          )}
        </div>
      </div>

      <style>{`
        .scout-panel {
          height: 100%;
          display: flex;
          flex-direction: column;
        }

        .panel-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 16px;
          border-bottom: 1px solid var(--border-color);
        }

        .panel-header h2 {
          font-size: 16px;
          font-weight: 600;
          margin: 0;
        }

        .status-badge {
          font-size: 10px;
          padding: 3px 8px;
          border-radius: 10px;
          font-weight: 600;
        }

        .status-badge.idle {
          background: var(--accent-lavender);
          color: var(--bg-primary);
        }

        .status-badge.running {
          background: var(--accent-turquoise);
          color: var(--bg-primary);
          animation: pulse 1.5s infinite;
        }

        .status-badge.complete {
          background: var(--accent-gold);
          color: var(--bg-primary);
        }

        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.7; }
        }

        /* Discovery Activity */
        .discovery-activity {
          padding: 16px;
          border-bottom: 1px solid var(--border-color);
          max-height: 200px;
          overflow-y: auto;
        }

        .activity-feed {
          display: flex;
          flex-direction: column;
          gap: 6px;
        }

        .activity-item {
          padding: 8px;
          background: var(--bg-tertiary);
          border-radius: 6px;
          font-size: 11px;
          border-left: 2px solid var(--accent-turquoise);
        }

        .activity-message {
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
          background: var(--accent-turquoise);
          border-radius: 50%;
          animation: bounce 1.4s infinite ease-in-out both;
        }

        .thinking-indicator .dot:nth-child(1) { animation-delay: -0.32s; }
        .thinking-indicator .dot:nth-child(2) { animation-delay: -0.16s; }

        @keyframes bounce {
          0%, 80%, 100% { transform: scale(0); }
          40% { transform: scale(1); }
        }

        .section-label {
          font-size: 10px;
          text-transform: uppercase;
          color: var(--text-muted);
          letter-spacing: 0.5px;
          margin-bottom: 8px;
          font-weight: 600;
        }

        /* Current Issue */
        .current-issue {
          padding: 16px;
          border-bottom: 1px solid var(--border-color);
        }

        .issue-card {
          padding: 12px;
          background: var(--bg-tertiary);
          border-radius: 8px;
          border-left: 3px solid var(--accent-gold);
        }

        .issue-card.active {
          background: color-mix(in srgb, var(--accent-gold) 10%, var(--bg-tertiary));
          animation: glow 2s ease-in-out infinite;
        }

        @keyframes glow {
          0%, 100% { box-shadow: 0 0 0 0 rgba(251, 191, 36, 0); }
          50% { box-shadow: 0 0 8px 2px rgba(251, 191, 36, 0.2); }
        }

        .issue-number {
          font-size: 11px;
          color: var(--accent-gold);
          font-weight: 600;
          margin-bottom: 4px;
        }

        .issue-title {
          font-size: 13px;
          color: var(--text-primary);
          line-height: 1.4;
          margin-bottom: 8px;
        }

        .issue-meta {
          display: flex;
          justify-content: space-between;
          font-size: 11px;
        }

        .repo {
          color: var(--accent-lavender);
          font-family: var(--font-mono);
        }

        .score {
          color: var(--text-muted);
        }

        /* Queue */
        .queue-section {
          padding: 16px;
          border-bottom: 1px solid var(--border-color);
        }

        .queue-stats {
          display: flex;
          gap: 12px;
        }

        .stat {
          flex: 1;
          padding: 12px;
          background: var(--bg-tertiary);
          border-radius: 8px;
          text-align: center;
        }

        .stat-value {
          font-size: 24px;
          font-weight: 700;
          color: var(--accent-turquoise);
          display: block;
        }

        .stat-label {
          font-size: 10px;
          color: var(--text-muted);
          text-transform: uppercase;
        }

        /* Pending */
        .pending-section {
          flex: 1;
          padding: 16px;
          overflow-y: auto;
        }

        .pending-list {
          display: flex;
          flex-direction: column;
          gap: 6px;
        }

        .pending-item {
          display: flex;
          align-items: center;
          gap: 8px;
          padding: 8px;
          background: var(--bg-tertiary);
          border-radius: 6px;
          font-size: 12px;
        }

        .pending-score {
          width: 24px;
          height: 24px;
          background: var(--accent-gold);
          color: var(--bg-primary);
          border-radius: 4px;
          display: flex;
          align-items: center;
          justify-content: center;
          font-weight: 700;
          font-size: 11px;
          flex-shrink: 0;
        }

        .pending-title {
          color: var(--text-secondary);
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
        }

        .empty-queue {
          padding: 20px;
          text-align: center;
          color: var(--text-muted);
          font-size: 12px;
        }
      `}</style>
    </div>
  );
}
