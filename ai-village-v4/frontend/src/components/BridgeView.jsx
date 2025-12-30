import React, { useState, useEffect, useRef } from 'react';
import { useWebSocket } from '../hooks/useWebSocket';

// Phase configuration for timeline
const PHASES = [
  { id: 'briefing', label: 'Briefing', icon: '1' },
  { id: 'bridge_discussion', label: 'Discussion', icon: '2' },
  { id: 'decision', label: 'Decision', icon: '3' },
  { id: 'execution', label: 'Execution', icon: '4' },
  { id: 'review', label: 'Review', icon: '5' },
  { id: 'captains_log', label: "Captain's Log", icon: '6' }
];

// Event styling configuration
const EVENT_STYLES = {
  episode_start: { bg: 'var(--bg-card)', border: '#fbbf24', badge: 'EPISODE' },
  phase_start: { bg: 'var(--bg-tertiary)', border: '#60a5fa', badge: 'PHASE' },
  round_start: { bg: 'var(--bg-tertiary)', border: '#a78bfa', badge: 'ROUND' },
  officer_thinking: { bg: 'rgba(113,113,122,0.05)', border: '#71717a', badge: 'THINKING' },
  officer_contribution: { bg: 'var(--bg-card)', border: 'var(--accent-turquoise)', badge: 'MSG' },
  captain_decision: { bg: 'rgba(251,191,36,0.1)', border: '#fbbf24', badge: 'DECISION' },
  risk_assessment: { bg: 'rgba(251,113,133,0.1)', border: '#fb7185', badge: 'RISK' },
  human_consultation_required: { bg: 'rgba(251,113,133,0.15)', border: '#fb7185', badge: 'ALERT' },
  safety_warning: { bg: 'rgba(251,113,133,0.2)', border: '#fb7185', badge: 'WARNING' },
  execution_progress: { bg: 'var(--bg-tertiary)', border: '#2dd4bf', badge: 'EXEC' },
  outcome_assessment: { bg: 'var(--bg-tertiary)', border: '#2dd4bf', badge: 'OUTCOME' },
  episode_complete: { bg: 'rgba(45,212,191,0.1)', border: '#2dd4bf', badge: 'COMPLETE' },
  default: { bg: 'var(--bg-tertiary)', border: '#52525b', badge: 'INFO' }
};

const CollapsibleText = ({ text }) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const shouldCollapse = text.length > 300;

  if (!shouldCollapse) return <div style={{ lineHeight: '1.6', fontSize: '14px' }}>{text}</div>;

  return (
    <div>
      <div style={{
        lineHeight: '1.6',
        fontSize: '14px',
        display: isExpanded ? 'block' : '-webkit-box',
        WebkitLineClamp: isExpanded ? 'unset' : 3,
        WebkitBoxOrient: 'vertical',
        overflow: 'hidden',
        color: 'var(--text-secondary)'
      }}>
        {text}
      </div>
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        style={{
          background: 'none',
          border: 'none',
          color: 'var(--accent-blue)',
          padding: '6px 0',
          fontSize: '12px',
          cursor: 'pointer',
          fontWeight: '500'
        }}
      >
        {isExpanded ? 'Show Less' : 'Show More...'}
      </button>
    </div>
  );
};

export function BridgeView({ episodeId }) {
  const { socket, isConnected, lastMessage, sendMessage } = useWebSocket('ws://localhost:8000/ws/bridge');
  const [events, setEvents] = useState([]);
  const [currentPhase, setCurrentPhase] = useState('idle');
  const [currentRound, setCurrentRound] = useState(0);
  const [episodeInfo, setEpisodeInfo] = useState(null);
  const [isAutoScrollEnabled, setIsAutoScrollEnabled] = useState(true);
  const eventsEndRef = useRef(null);

  // Auto-scroll logic
  useEffect(() => {
    if (isAutoScrollEnabled && eventsEndRef.current) {
      eventsEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [events, isAutoScrollEnabled]);

  // Handle messages
  useEffect(() => {
    if (lastMessage) {
      const event = lastMessage;

      if (event.type === 'phase_start') setCurrentPhase(event.phase);
      else if (event.type === 'round_start') setCurrentRound(event.round);
      else if (event.type === 'episode_start') {
        setEpisodeInfo({
          id: event.episode_id,
          number: event.episode_number,
          scenario: event.scenario,
          scenarioType: event.scenario_type
        });
        setEvents([]);
        setCurrentPhase('briefing');
        setCurrentRound(0);
      } else if (event.type === 'episode_complete') {
        setCurrentPhase('complete');
      } else if (event.type === 'resume_available' || event.type === 'resume_start') {
        // Handle resume info if needed
      }

      if (event.type !== 'officer_thinking' && event.type !== 'connected' && event.type !== 'pong') {
        setEvents(prev => [...prev, { ...event, timestamp: new Date().toISOString() }]);
      }
    }
  }, [lastMessage]);

  const startEpisode = () => sendMessage({ action: 'start_episode' });

  const getEventStyle = (type) => EVENT_STYLES[type] || EVENT_STYLES.default;

  return (
    <div style={{
      padding: '20px',
      height: '100%',
      display: 'flex',
      flexDirection: 'column',
      gap: '20px',
      maxWidth: '1200px',
      margin: '0 auto',
      width: '100%'
    }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h2 style={{ margin: 0, color: 'var(--accent-gold)', display: 'flex', alignItems: 'center', gap: '12px' }}>
          Bridge Operations
          {episodeInfo && <span style={{ fontSize: '14px', color: 'var(--text-muted)', fontWeight: 'normal' }}>/ Episode {episodeInfo.number}</span>}
        </h2>

        <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
          <div style={{
            padding: '6px 12px',
            borderRadius: '20px',
            fontSize: '11px',
            fontWeight: '600',
            background: isConnected ? 'rgba(45,212,191,0.1)' : 'rgba(251,113,133,0.1)',
            color: isConnected ? 'var(--accent-turquoise)' : 'var(--accent-coral)',
            border: `1px solid ${isConnected ? 'var(--accent-turquoise)' : 'var(--accent-coral)'}`
          }}>
            {isConnected ? 'ONLINE' : 'OFFLINE'}
          </div>

          <button
            onClick={() => setIsAutoScrollEnabled(!isAutoScrollEnabled)}
            style={{
              background: 'transparent',
              border: '1px solid var(--border-color)',
              color: isAutoScrollEnabled ? 'var(--accent-turquoise)' : 'var(--text-muted)',
              padding: '6px 12px',
              borderRadius: '6px',
              fontSize: '12px',
              cursor: 'pointer'
            }}
          >
            {isAutoScrollEnabled ? 'Auto-scroll: ON' : 'Auto-scroll: OFF'}
          </button>

          <button
            onClick={startEpisode}
            disabled={!isConnected}
            style={{
              background: 'var(--accent-gold)',
              color: 'var(--bg-primary)',
              border: 'none',
              padding: '8px 20px',
              borderRadius: '6px',
              fontSize: '13px',
              fontWeight: '600',
              cursor: isConnected ? 'pointer' : 'not-allowed',
              opacity: isConnected ? 1 : 0.5
            }}
          >
            Start Simulation
          </button>
        </div>
      </div>

      {/* Timeline */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        gap: '4px',
        padding: '16px',
        background: 'var(--bg-secondary)',
        borderRadius: '12px',
        border: '1px solid var(--border-color)'
      }}>
        {PHASES.map((phase, idx) => {
          const isActive = phase.id === currentPhase;
          const isPast = PHASES.findIndex(p => p.id === currentPhase) > idx;
          const isComplete = currentPhase === 'complete';

          return (
            <div key={phase.id} style={{ flex: 1, textAlign: 'center', opacity: isActive || isPast || isComplete ? 1 : 0.4 }}>
              <div style={{
                height: '4px',
                background: isActive ? 'var(--accent-gold)' : (isPast || isComplete ? 'var(--accent-turquoise)' : 'var(--bg-tertiary)'),
                borderRadius: '2px',
                marginBottom: '8px',
                transition: 'all 0.3s'
              }} />
              <div style={{
                fontSize: '11px',
                fontWeight: '600',
                color: isActive ? 'var(--accent-gold)' : (isPast || isComplete ? 'var(--accent-turquoise)' : 'var(--text-muted)')
              }}>
                {phase.label.toUpperCase()}
              </div>
            </div>
          );
        })}
      </div>

      {/* Scenario */}
      {episodeInfo?.scenario && (
        <div style={{
          padding: '20px',
          background: 'var(--bg-secondary)',
          borderLeft: '4px solid var(--accent-blue)',
          borderRadius: '0 12px 12px 0'
        }}>
          <div style={{
            fontSize: '11px',
            fontWeight: '700',
            color: 'var(--accent-blue)',
            marginBottom: '8px',
            letterSpacing: '0.05em'
          }}>
            CURRENT SCENARIO: {episodeInfo.scenarioType?.toUpperCase()}
          </div>
          <CollapsibleText text={episodeInfo.scenario} />
        </div>
      )}

      {/* Event Stream */}
      <div style={{
        flex: 1,
        overflowY: 'auto',
        display: 'flex',
        flexDirection: 'column',
        gap: '12px',
        paddingRight: '8px'
      }}>
        {events.length === 0 && (
          <div style={{ textAlign: 'center', padding: '60px', color: 'var(--text-muted)', background: 'var(--bg-secondary)', borderRadius: '12px', border: '1px dashed var(--border-color)' }}>
            <div style={{ fontSize: '24px', marginBottom: '16px', fontWeight: 'bold', color: 'var(--text-secondary)' }}>Ready for Mission</div>
            <div>Standing by for simulation start command...</div>
          </div>
        )}

        {events.map((event, idx) => {
          const style = getEventStyle(event.type);
          const isContribution = event.type === 'officer_contribution';
          const isDecision = event.type === 'captain_decision';

          return (
            <div key={idx} style={{
              display: 'flex',
              gap: '16px',
              animation: 'fadeSlideIn 0.3s ease-out'
            }}>
              {/* Event Badge/Time Column */}
              <div style={{
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'flex-end',
                minWidth: '80px',
                gap: '4px'
              }}>
                <span style={{
                  fontSize: '10px',
                  fontWeight: '700',
                  padding: '2px 6px',
                  borderRadius: '4px',
                  background: style.bg,
                  color: style.border,
                  border: `1px solid ${style.border}`,
                  textAlign: 'center',
                  minWidth: '60px'
                }}>
                  {style.badge}
                </span>
              </div>

              {/* Event Content */}
              <div style={{
                flex: 1,
                background: isContribution || isDecision ? 'var(--bg-card)' : 'transparent',
                padding: isContribution || isDecision ? '16px' : '4px 0',
                borderRadius: '8px',
                border: isContribution || isDecision ? '1px solid var(--border-color)' : 'none'
              }}>
                {isContribution || isDecision ? (
                  <>
                    <div style={{ display: 'flex', alignItems: 'baseline', gap: '8px', marginBottom: '8px' }}>
                      <span style={{ fontWeight: '700', color: event.color || 'var(--text-primary)' }}>
                        {event.officer_name || 'Officer'}
                      </span>
                      <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                        {(event.role || '').toUpperCase()}
                      </span>
                      {event.round && <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>• R{event.round}</span>}
                      {event.risk_level && (
                        <span style={{
                          fontSize: '11px',
                          color: event.risk_level >= 7 ? 'var(--accent-coral)' : 'var(--accent-turquoise)',
                          fontWeight: '600'
                        }}>
                          • RISK {event.risk_level}/10
                        </span>
                      )}
                    </div>
                    <div style={{ lineHeight: '1.6', fontSize: '13px', color: 'var(--text-secondary)', whiteSpace: 'pre-wrap' }}>
                      {isDecision ? event.decision : event.content}
                    </div>
                    {isDecision && (
                      <div style={{ marginTop: '12px', fontSize: '12px', display: 'flex', gap: '12px' }}>
                        <span style={{
                          color: event.safety_validated ? 'var(--accent-turquoise)' : 'var(--accent-coral)',
                          fontWeight: '600'
                        }}>
                          {event.safety_validated ? 'SAFETY VALIDATED' : 'SAFETY PROTOCOL ALERT'}
                        </span>
                      </div>
                    )}
                  </>
                ) : (
                  <div style={{
                    color: 'var(--text-primary)',
                    fontSize: '13px',
                    fontWeight: event.type.includes('start') ? '600' : 'normal',
                    padding: '2px 0'
                  }}>
                    {event.message}
                  </div>
                )}

                {event.type === 'episode_complete' && (
                  <div style={{
                    marginTop: '12px',
                    padding: '16px',
                    background: 'rgba(45,212,191,0.05)',
                    borderRadius: '8px',
                    border: '1px solid var(--accent-turquoise)',
                    display: 'flex',
                    gap: '24px'
                  }}>
                    <div>
                      <div style={{ fontSize: '10px', color: 'var(--text-muted)' }}>OUTCOME</div>
                      <div style={{ fontWeight: '700', color: 'var(--accent-turquoise)' }}>{(event.outcome || 'N/A').toUpperCase()}</div>
                    </div>
                    <div>
                      <div style={{ fontSize: '10px', color: 'var(--text-muted)' }}>SAFETY</div>
                      <div style={{ fontWeight: '700', color: 'var(--accent-turquoise)' }}>{event.crew_safety_score}%</div>
                    </div>
                    <div>
                      <div style={{ fontSize: '10px', color: 'var(--text-muted)' }}>SUCCESS</div>
                      <div style={{ fontWeight: '700', color: 'var(--accent-turquoise)' }}>{event.mission_success_score}%</div>
                    </div>
                  </div>
                )}
              </div>
            </div>
          );
        })}
        <div ref={eventsEndRef} />
      </div>

      <style>{`
        @keyframes fadeSlideIn {
          from { opacity: 0; transform: translateY(4px); }
          to { opacity: 1; transform: translateY(0); }
        }
      `}</style>
    </div>
  );
}
