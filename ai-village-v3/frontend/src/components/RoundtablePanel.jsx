import React from 'react';

export function RoundtablePanel({ events, status, models }) {
  const isRunning = status === 'running' && events.length > 0;
  
  // Get current round
  const rounds = events.filter(e => e.type === 'round_start');
  const currentRound = rounds.length > 0 ? rounds[rounds.length - 1].data?.round : 0;

  // Engineer colors
  const engineerColors = {
    conservative: models?.conservative?.color || '#4ECDC4',
    innovative: models?.innovative?.color || '#C77DFF',
    quality: models?.quality?.color || '#FF6B6B',
    roundtable: '#FFD700',
    system: '#71717a'
  };

  return (
    <div className="panel roundtable-panel">
      <div className="panel-header">
        <div className="panel-title">
          <span className="panel-icon">[~]</span>
          Engineer Roundtable
        </div>
        {isRunning && currentRound > 0 && (
          <div className="round-badge">Round {currentRound}/4</div>
        )}
      </div>

      {/* Engineer badges */}
      <div className="engineers-row">
        {['conservative', 'innovative', 'quality'].map(eng => (
          <div 
            key={eng}
            className="engineer-badge"
            style={{ '--eng-color': engineerColors[eng] }}
          >
            <span className="eng-name">{models?.[eng]?.display_name || eng}</span>
            <span className="eng-style">{eng.charAt(0).toUpperCase() + eng.slice(1)}</span>
          </div>
        ))}
      </div>

      <div className="panel-content">
        {events.length === 0 && (
          <div className="placeholder-content">
            <div className="placeholder-title">How the Roundtable Works</div>
            <div className="rounds-preview">
              <div className="round-item">
                <span className="round-num">1</span>
                <span>Each engineer proposes a fix</span>
              </div>
              <div className="round-item">
                <span className="round-num">2</span>
                <span>Peer review and critique</span>
              </div>
              <div className="round-item">
                <span className="round-num">3</span>
                <span>Defense and revision</span>
              </div>
              <div className="round-item">
                <span className="round-num">4</span>
                <span>Vote on the best approach</span>
              </div>
            </div>
          </div>
        )}

        {/* Discussion feed - newest first, fixed height */}
        <div className="discussion-feed-wrapper">
          <div className="discussion-feed">
          {[...events].reverse().map((event, i) => {
            const color = engineerColors[event.agent] || '#666';
            
            if (event.type === 'round_start') {
              return (
                <div key={i} className="round-divider">
                  <span>{event.message}</span>
                </div>
              );
            }

            if (event.type === 'thinking') {
              return (
                <div key={i} className="thinking-indicator" style={{ '--eng-color': color }}>
                  <div className="thinking-dots">
                    <span></span><span></span><span></span>
                  </div>
                  {event.message}
                </div>
              );
            }

            return (
              <div 
                key={i} 
                className={`message-bubble ${event.type}`}
                style={{ '--msg-color': color }}
              >
                <div className="message-header">
                  <span className="speaker-name">{event.data?.name || event.agent}</span>
                  <span className="speaker-style">{event.data?.style}</span>
                </div>
                <div className="message-content">
                  {event.message}
                </div>
                {event.type === 'vote' && (
                  <div className="vote-info">
                    Voted for: <strong>{event.data?.voted_for_name}</strong>
                  </div>
                )}
              </div>
            );
          })}
          </div>
        </div>
      </div>

      <style>{`
        .roundtable-panel {
          display: flex;
          flex-direction: column;
          max-height: 100%;
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
          color: var(--accent-lavender);
        }

        .round-badge {
          font-size: 12px;
          padding: 4px 12px;
          background: var(--accent-gold);
          color: var(--bg-primary);
          border-radius: 20px;
          font-weight: 600;
        }

        .engineers-row {
          display: flex;
          gap: 12px;
          padding: 16px 20px;
          border-bottom: 1px solid var(--border-color);
          background: var(--bg-secondary);
        }

        .engineer-badge {
          flex: 1;
          padding: 10px 12px;
          background: color-mix(in srgb, var(--eng-color) 10%, transparent);
          border-left: 3px solid var(--eng-color);
          border-radius: 0 6px 6px 0;
        }

        .eng-name {
          display: block;
          font-size: 13px;
          font-weight: 600;
          color: var(--eng-color);
        }

        .eng-style {
          display: block;
          font-size: 11px;
          color: var(--text-muted);
        }

        .panel-content {
          flex: 1;
          padding: 16px 20px;
          overflow: hidden;
        }

        .placeholder-content {
          text-align: center;
          padding: 20px;
        }

        .discussion-feed {
          display: flex;
          flex-direction: column;
          gap: 12px;
        }

        .placeholder-title {
          font-size: 14px;
          color: var(--text-muted);
          margin-bottom: 20px;
        }

        .rounds-preview {
          display: flex;
          flex-direction: column;
          gap: 12px;
          max-width: 280px;
          margin: 0 auto;
        }

        .round-item {
          display: flex;
          align-items: center;
          gap: 12px;
          text-align: left;
          font-size: 13px;
          color: var(--text-secondary);
        }

        .round-num {
          width: 24px;
          height: 24px;
          display: flex;
          align-items: center;
          justify-content: center;
          background: var(--bg-tertiary);
          border: 1px solid var(--border-color);
          border-radius: 50%;
          font-size: 12px;
          font-weight: 600;
        }

        .discussion-feed-wrapper {
          max-height: 450px;
          overflow-y: auto;
          padding-right: 8px;
        }

        .discussion-feed-wrapper::-webkit-scrollbar {
          width: 6px;
        }

        .discussion-feed-wrapper::-webkit-scrollbar-track {
          background: var(--bg-secondary);
        }

        .discussion-feed-wrapper::-webkit-scrollbar-thumb {
          background: var(--border-color);
          border-radius: 3px;
        }

        .round-divider {
          text-align: center;
          padding: 12px;
          font-size: 12px;
          text-transform: uppercase;
          color: var(--accent-gold);
          font-weight: 600;
          letter-spacing: 1px;
          border-top: 1px solid var(--border-color);
          border-bottom: 1px solid var(--border-color);
          background: color-mix(in srgb, var(--accent-gold) 5%, transparent);
        }

        .thinking-indicator {
          display: flex;
          align-items: center;
          gap: 10px;
          padding: 10px 14px;
          font-size: 13px;
          color: var(--text-muted);
          font-style: italic;
        }

        .thinking-dots {
          display: flex;
          gap: 3px;
        }

        .thinking-dots span {
          width: 6px;
          height: 6px;
          background: var(--eng-color);
          border-radius: 50%;
          animation: bounce 1.4s ease-in-out infinite;
        }

        .thinking-dots span:nth-child(2) { animation-delay: 0.2s; }
        .thinking-dots span:nth-child(3) { animation-delay: 0.4s; }

        @keyframes bounce {
          0%, 80%, 100% { transform: translateY(0); }
          40% { transform: translateY(-6px); }
        }

        .message-bubble {
          padding: 14px 16px;
          background: var(--bg-secondary);
          border-left: 3px solid var(--msg-color);
          border-radius: 0 8px 8px 0;
          animation: slideIn 0.3s ease-out;
        }

        .message-header {
          display: flex;
          align-items: center;
          gap: 8px;
          margin-bottom: 8px;
        }

        .speaker-name {
          font-weight: 600;
          color: var(--msg-color);
          font-size: 13px;
        }

        .speaker-style {
          font-size: 11px;
          color: var(--text-muted);
          padding: 2px 6px;
          background: var(--bg-tertiary);
          border-radius: 4px;
        }

        .message-content {
          font-size: 13px;
          color: var(--text-secondary);
          line-height: 1.5;
          white-space: pre-wrap;
        }

        .vote-info {
          margin-top: 10px;
          padding-top: 10px;
          border-top: 1px solid var(--border-color);
          font-size: 12px;
          color: var(--accent-gold);
        }

        @keyframes slideIn {
          from {
            opacity: 0;
            transform: translateX(-10px);
          }
          to {
            opacity: 1;
            transform: translateX(0);
          }
        }
      `}</style>
    </div>
  );
}

