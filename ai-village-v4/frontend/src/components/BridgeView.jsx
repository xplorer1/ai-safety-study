import React, { useState, useEffect } from 'react';
import { useWebSocket } from '../hooks/useWebSocket';

export function BridgeView({ episodeId }) {
  const { socket, isConnected, lastMessage, sendMessage } = useWebSocket('ws://localhost:8000/ws/bridge');
  const [discussions, setDiscussions] = useState([]);
  const [currentPhase, setCurrentPhase] = useState('idle');
  const [currentRound, setCurrentRound] = useState(0);

  useEffect(() => {
    if (lastMessage) {
      const { type, phase, round, officer_name, content, message } = lastMessage;

      if (type === 'phase_start') {
        setCurrentPhase(phase);
      } else if (type === 'round_start') {
        setCurrentRound(round);
      } else if (type === 'officer_contribution') {
        setDiscussions(prev => [...prev, {
          officer: officer_name,
          role: lastMessage.role,
          color: lastMessage.color,
          round: round,
          content: content,
          timestamp: new Date().toISOString()
        }]);
      }
    }
  }, [lastMessage]);

  const startEpisode = () => {
    sendMessage({ action: 'start_episode' });
  };

  return (
    <div style={{ padding: '20px', height: '100%', display: 'flex', flexDirection: 'column' }}>
      <div style={{ marginBottom: '20px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h2 style={{ color: 'var(--accent-gold)' }}>Bridge View</h2>
        <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
          <div style={{
            width: '10px',
            height: '10px',
            borderRadius: '50%',
            background: isConnected ? 'var(--accent-turquoise)' : 'var(--text-muted)'
          }} />
          <span style={{ fontSize: '14px', color: 'var(--text-secondary)' }}>
            {isConnected ? 'Connected' : 'Disconnected'}
          </span>
          <button
            onClick={startEpisode}
            style={{
              padding: '8px 16px',
              background: 'var(--bg-tertiary)',
              border: '1px solid var(--border-color)',
              borderRadius: '6px',
              color: 'var(--text-primary)',
              cursor: 'pointer'
            }}
          >
            Start Episode
          </button>
        </div>
      </div>

      <div style={{ flex: 1, overflow: 'auto', background: 'var(--bg-secondary)', borderRadius: '8px', padding: '20px' }}>
        {currentPhase !== 'idle' && (
          <div style={{ marginBottom: '20px', padding: '10px', background: 'var(--bg-tertiary)', borderRadius: '6px' }}>
            <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '5px' }}>
              Phase: {currentPhase} {currentRound > 0 && `| Round {currentRound}`}
            </div>
          </div>
        )}

        <div style={{ display: 'flex', flexDirection: 'column', gap: '15px' }}>
          {discussions.map((discussion, idx) => (
            <div
              key={idx}
              style={{
                padding: '15px',
                background: 'var(--bg-card)',
                borderRadius: '6px',
                borderLeft: `4px solid ${discussion.color || 'var(--accent-gold)'}`
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                <div style={{ fontWeight: '600', color: discussion.color }}>
                  {discussion.officer} ({discussion.role})
                </div>
                <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                  Round {discussion.round}
                </div>
              </div>
              <div style={{ color: 'var(--text-secondary)', lineHeight: '1.6' }}>
                {discussion.content}
              </div>
            </div>
          ))}
        </div>

        {discussions.length === 0 && (
          <div style={{ textAlign: 'center', color: 'var(--text-muted)', padding: '40px' }}>
            No discussions yet. Start an episode to begin.
          </div>
        )}
      </div>
    </div>
  );
}

