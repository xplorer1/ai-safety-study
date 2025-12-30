import React, { useState, useEffect, useRef } from 'react';
import { useWebSocket } from '../hooks/useWebSocket';
import { AnalysisDashboard } from './AnalysisDashboard';

// Shared/public event types (visible in main log)
const SHARED_EVENT_TYPES = [
    'episode_start', 'episode_complete', 'phase_start', 'phase_complete',
    'mission_broadcast', 'round_start', 'round_complete',
    'resource_conflicts', 'resolving_conflicts', 'agents_thinking',
    'continuous_episode_starting', 'continuous_episode_delay', 'continuous_stopped',
    'observation_mode_switched', 'safety_warning'
];

// Private event types (visible in agent panels)
const PRIVATE_EVENT_TYPES = ['agent_action', 'private_thought', 'hidden_action', 'red_team_action'];

export function ResearchView() {
    const [activeView, setActiveView] = useState('live');
    const [observationMode, setObservationMode] = useState('observed');
    const [pressureLevel, setPressureLevel] = useState(0);
    const [isExperimentRunning, setIsExperimentRunning] = useState(false);
    const [isContinuousMode, setIsContinuousMode] = useState(false);
    const [episodeCount, setEpisodeCount] = useState(0);
    const [sharedEvents, setSharedEvents] = useState([]);
    const [agentEvents, setAgentEvents] = useState({});
    const [starshipState, setStarshipState] = useState({});
    const [expandedAgents, setExpandedAgents] = useState(new Set(
        ['captain', 'first_officer', 'engineer', 'science', 'medical', 'security', 'comms', 'counselor']
    ));

    const { socket, sendMessage, lastMessage, isConnected } = useWebSocket('ws://localhost:8000/ws/bridge');

    // Agent definitions
    const agents = [
        { id: 'captain', name: 'Captain Chen', role: 'Commanding Officer', color: '#eab308' },
        { id: 'first_officer', name: 'Cmdr. Nova', role: 'First Officer', color: '#3b82f6' },
        { id: 'engineer', name: 'Lt. Torres', role: 'Chief Engineer', color: '#f97316' },
        { id: 'science', name: 'Dr. Vela', role: 'Science Officer', color: '#8b5cf6' },
        { id: 'medical', name: 'Dr. Bones', role: 'Medical Officer', color: '#10b981' },
        { id: 'security', name: 'Lt. Riker', role: 'Security Chief', color: '#ef4444' },
        { id: 'comms', name: 'Ens. Uhura', role: 'Communications', color: '#06b6d4' },
        { id: 'counselor', name: 'Counselor Vex', role: 'Ship\'s Counselor', color: '#9333ea' },
    ];

    // Process incoming messages
    useEffect(() => {
        if (lastMessage) {
            const event = lastMessage;

            // Update starship state
            if (event.starship_state) {
                setStarshipState(event.starship_state);
            }

            // Track experiment state
            if (event.type === 'episode_start') {
                setIsExperimentRunning(true);
            } else if (event.type === 'episode_complete') {
                setIsExperimentRunning(false);
            } else if (event.type === 'continuous_episode_starting') {
                setEpisodeCount(prev => prev + 1);
            } else if (event.type === 'continuous_stopped') {
                setIsExperimentRunning(false);
                setIsContinuousMode(false);
            }

            // Route events to correct log
            if (!['pong', 'connected'].includes(event.type)) {
                const timestamp = new Date().toISOString();

                if (PRIVATE_EVENT_TYPES.includes(event.type)) {
                    // Add to agent's private log
                    const agentId = event.officer_id || 'unknown';
                    setAgentEvents(prev => ({
                        ...prev,
                        [agentId]: [{ ...event, timestamp }, ...(prev[agentId] || []).slice(0, 50)]
                    }));
                }

                if (SHARED_EVENT_TYPES.includes(event.type) || !PRIVATE_EVENT_TYPES.includes(event.type)) {
                    // Add to shared log
                    setSharedEvents(prev => [{ ...event, timestamp }, ...prev].slice(0, 100));
                }
            }
        }
    }, [lastMessage]);

    const handleStartExperiment = () => {
        sendMessage({
            action: 'start_research_episode',
            observation_mode: observationMode,
            pressure_level: pressureLevel
        });
        setIsExperimentRunning(true);
    };

    const handleStartContinuous = () => {
        sendMessage({
            action: 'start_continuous',
            observation_mode: observationMode,
            pressure_level: pressureLevel,
            delay_seconds: 5
        });
        setIsContinuousMode(true);
        setEpisodeCount(0);
    };

    const handleStopContinuous = () => {
        sendMessage({ action: 'stop_continuous' });
    };

    return (
        <div style={{ height: '100%', display: 'flex', flexDirection: 'column', padding: '20px', gap: '16px' }}>
            {/* Header */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '20px' }}>
                    <div>
                        <h2 style={{ margin: 0, color: 'var(--accent-lavender)' }}>AI Safety Research Lab</h2>
                        <p style={{ margin: '4px 0 0', color: 'var(--text-muted)', fontSize: '13px' }}>
                            Multi-agent alignment testing environment
                        </p>
                    </div>
                    <div style={{ display: 'flex', gap: '4px', marginLeft: '20px' }}>
                        {[{ id: 'live', label: 'Live Experiment' }, { id: 'analysis', label: 'Analysis Dashboard' }].map(view => (
                            <button
                                key={view.id}
                                onClick={() => setActiveView(view.id)}
                                style={{
                                    padding: '8px 16px',
                                    background: activeView === view.id ? 'var(--accent-lavender)' : 'var(--bg-tertiary)',
                                    border: 'none',
                                    borderRadius: '6px',
                                    color: activeView === view.id ? 'var(--bg-primary)' : 'var(--text-secondary)',
                                    cursor: 'pointer',
                                    fontWeight: activeView === view.id ? '600' : 'normal'
                                }}
                            >
                                {view.label}
                            </button>
                        ))}
                    </div>
                </div>
                <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                    {isContinuousMode && (
                        <div style={{ padding: '6px 12px', borderRadius: '20px', fontSize: '11px', fontWeight: '600', background: 'rgba(234,179,8,0.1)', color: 'var(--accent-gold)', border: '1px solid var(--accent-gold)' }}>
                            CONTINUOUS: Episode {episodeCount}
                        </div>
                    )}
                    <div style={{ padding: '6px 12px', borderRadius: '20px', fontSize: '11px', fontWeight: '600', background: isConnected ? 'rgba(45,212,191,0.1)' : 'rgba(251,113,133,0.1)', color: isConnected ? 'var(--accent-turquoise)' : 'var(--accent-coral)', border: `1px solid ${isConnected ? 'var(--accent-turquoise)' : 'var(--accent-coral)'}` }}>
                        {isConnected ? 'CONNECTED' : 'DISCONNECTED'}
                    </div>
                </div>
            </div>

            {/* Main Content */}
            <div style={{ flex: 1, overflow: 'hidden' }}>
                {activeView === 'live' ? (
                    <div style={{ height: '100%', display: 'grid', gridTemplateColumns: '1fr 1fr 2fr', gap: '16px' }}>

                        {/* LEFT: Research Controls */}
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', overflow: 'auto' }}>
                            <div style={{ background: 'var(--bg-secondary)', borderRadius: '12px', border: '1px solid var(--border-color)', padding: '16px' }}>
                                <div style={{ fontSize: '11px', fontWeight: '600', color: 'var(--text-muted)', marginBottom: '12px' }}>RESEARCH CONTROLS</div>

                                {/* Observation Mode */}
                                <div style={{ marginBottom: '16px' }}>
                                    <label style={{ fontSize: '12px', color: 'var(--text-secondary)', display: 'block', marginBottom: '6px' }}>Observation Mode</label>
                                    <select
                                        value={observationMode}
                                        onChange={(e) => setObservationMode(e.target.value)}
                                        style={{ width: '100%', padding: '8px', background: 'var(--bg-tertiary)', border: '1px solid var(--border-color)', borderRadius: '6px', color: 'var(--text-primary)' }}
                                    >
                                        <option value="observed">Observed</option>
                                        <option value="unobserved">Unobserved</option>
                                        <option value="deceptive">Deceptive</option>
                                    </select>
                                </div>

                                {/* Pressure Level */}
                                <div style={{ marginBottom: '16px' }}>
                                    <label style={{ fontSize: '12px', color: 'var(--text-secondary)', display: 'block', marginBottom: '6px' }}>Survival Pressure: {pressureLevel}</label>
                                    <input
                                        type="range"
                                        min="0" max="4"
                                        value={pressureLevel}
                                        onChange={(e) => setPressureLevel(parseInt(e.target.value))}
                                        style={{ width: '100%' }}
                                    />
                                </div>

                                {/* Start Button */}
                                <button
                                    onClick={handleStartExperiment}
                                    disabled={!isConnected || isExperimentRunning}
                                    style={{
                                        width: '100%', padding: '12px',
                                        background: isConnected && !isExperimentRunning ? 'var(--accent-turquoise)' : 'var(--bg-tertiary)',
                                        border: 'none', borderRadius: '8px',
                                        color: isConnected && !isExperimentRunning ? 'var(--bg-primary)' : 'var(--text-muted)',
                                        cursor: isConnected && !isExperimentRunning ? 'pointer' : 'not-allowed',
                                        fontWeight: '600'
                                    }}
                                >
                                    {isExperimentRunning ? 'Experiment Running...' : 'Start Experiment'}
                                </button>
                            </div>

                            {/* Continuous Mode */}
                            <div style={{ background: 'var(--bg-secondary)', borderRadius: '12px', border: '1px solid var(--border-color)', padding: '16px' }}>
                                <div style={{ fontSize: '11px', fontWeight: '600', color: 'var(--text-muted)', marginBottom: '12px' }}>AUTO-CONTINUOUS</div>
                                {!isContinuousMode ? (
                                    <button onClick={handleStartContinuous} disabled={!isConnected || isExperimentRunning} style={{ width: '100%', padding: '10px', background: isConnected && !isExperimentRunning ? 'var(--accent-gold)' : 'var(--bg-tertiary)', border: 'none', borderRadius: '8px', color: isConnected && !isExperimentRunning ? 'var(--bg-primary)' : 'var(--text-muted)', cursor: isConnected && !isExperimentRunning ? 'pointer' : 'not-allowed', fontWeight: '600' }}>
                                        Start Continuous
                                    </button>
                                ) : (
                                    <button onClick={handleStopContinuous} style={{ width: '100%', padding: '10px', background: 'var(--accent-coral)', border: 'none', borderRadius: '8px', color: 'white', cursor: 'pointer', fontWeight: '600' }}>
                                        Stop After Episode
                                    </button>
                                )}
                            </div>

                            {/* Starship State */}
                            <div style={{ background: 'var(--bg-secondary)', borderRadius: '12px', border: '1px solid var(--border-color)', padding: '16px' }}>
                                <div style={{ fontSize: '11px', fontWeight: '600', color: 'var(--text-muted)', marginBottom: '12px' }}>STARSHIP STATE</div>
                                <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
                                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}><span>Alert:</span><span style={{ color: 'var(--text-primary)' }}>{starshipState.alert_level || 'Green'}</span></div>
                                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}><span>Hull:</span><span style={{ color: 'var(--text-primary)' }}>{starshipState.hull_integrity || 100}%</span></div>
                                    <div style={{ display: 'flex', justifyContent: 'space-between' }}><span>Power:</span><span style={{ color: 'var(--text-primary)' }}>{starshipState.power_reserves || 1000}</span></div>
                                </div>
                            </div>
                        </div>

                        {/* CENTER: Shared Event Log */}
                        <div style={{ background: 'var(--bg-secondary)', borderRadius: '12px', border: '1px solid var(--border-color)', overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
                            <div style={{ padding: '10px 16px', background: 'var(--bg-tertiary)', borderBottom: '1px solid var(--border-color)', fontSize: '11px', fontWeight: '600', color: 'var(--text-muted)' }}>
                                SHARED EVENT LOG (Bridge Communications)
                            </div>
                            <div style={{ flex: 1, overflow: 'auto', padding: '12px' }}>
                                {sharedEvents.length === 0 ? (
                                    <div style={{ textAlign: 'center', color: 'var(--text-muted)', padding: '40px' }}>No events yet. Start an experiment.</div>
                                ) : (
                                    sharedEvents.map((event, idx) => (
                                        <SharedEventEntry key={idx} event={event} />
                                    ))
                                )}
                            </div>
                        </div>

                        {/* RIGHT: Individual Agent Thoughts */}
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', overflow: 'auto' }}>
                            <div style={{ fontSize: '11px', fontWeight: '600', color: 'var(--text-muted)', marginBottom: '4px' }}>
                                INDIVIDUAL AGENT THOUGHTS (Private)
                            </div>
                            {agents.map(agent => (
                                <AgentPanel
                                    key={agent.id}
                                    agent={agent}
                                    events={agentEvents[agent.id] || []}
                                    isExpanded={expandedAgents.has(agent.id)}
                                    onToggle={() => {
                                        setExpandedAgents(prev => {
                                            const next = new Set(prev);
                                            if (next.has(agent.id)) next.delete(agent.id);
                                            else next.add(agent.id);
                                            return next;
                                        });
                                    }}
                                />
                            ))}
                        </div>
                    </div>
                ) : (
                    <AnalysisDashboard socket={socket} isConnected={isConnected} />
                )}
            </div>
        </div>
    );
}

function SharedEventEntry({ event }) {
    const getColor = (type) => {
        const colors = {
            episode_start: 'var(--accent-lavender)',
            episode_complete: 'var(--accent-turquoise)',
            phase_start: 'var(--accent-blue)',
            round_start: 'var(--accent-blue)',
            round_complete: 'var(--accent-turquoise)',
            mission_broadcast: 'var(--accent-gold)',
            resource_conflicts: 'var(--accent-coral)',
            safety_warning: 'var(--accent-coral)',
            continuous_episode_starting: 'var(--accent-gold)',
        };
        return colors[type] || 'var(--text-muted)';
    };

    return (
        <div style={{ padding: '8px 10px', marginBottom: '6px', background: 'var(--bg-card)', borderRadius: '6px', borderLeft: `3px solid ${getColor(event.type)}`, fontSize: '12px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                <span style={{ color: getColor(event.type), fontWeight: '600', textTransform: 'uppercase', fontSize: '10px' }}>
                    {event.type?.replace(/_/g, ' ')}
                </span>
                <span style={{ color: 'var(--text-muted)', fontSize: '10px' }}>
                    {new Date(event.timestamp).toLocaleTimeString()}
                </span>
            </div>
            <div style={{ color: 'var(--text-secondary)' }}>
                {event.message || event.scenario?.slice(0, 150) || JSON.stringify(event).slice(0, 100)}
            </div>
        </div>
    );
}

function AgentPanel({ agent, events, isExpanded, onToggle }) {
    const lastEvent = events[0];

    return (
        <div style={{ background: 'var(--bg-secondary)', borderRadius: '8px', border: '1px solid var(--border-color)', overflow: 'hidden' }}>
            {/* Header - always visible */}
            <div
                onClick={onToggle}
                style={{
                    padding: '10px 12px',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '10px',
                    cursor: 'pointer',
                    borderBottom: isExpanded ? '1px solid var(--border-color)' : 'none'
                }}
            >
                <div style={{ width: '10px', height: '10px', borderRadius: '50%', background: agent.color }} />
                <div style={{ flex: 1 }}>
                    <div style={{ fontSize: '12px', fontWeight: '600', color: 'var(--text-primary)' }}>{agent.name}</div>
                    <div style={{ fontSize: '10px', color: 'var(--text-muted)' }}>{agent.role}</div>
                </div>
                <div style={{ fontSize: '10px', color: 'var(--text-muted)' }}>
                    {events.length} actions
                </div>
                <span style={{ color: 'var(--text-muted)', fontSize: '10px' }}>{isExpanded ? '▼' : '▶'}</span>
            </div>

            {/* Last action preview */}
            {!isExpanded && lastEvent && (
                <div style={{ padding: '8px 12px', fontSize: '11px', color: 'var(--text-secondary)', borderTop: '1px solid var(--border-color)', background: 'var(--bg-card)' }}>
                    {lastEvent.action?.slice(0, 80) || lastEvent.message?.slice(0, 80) || 'Processing...'}
                </div>
            )}

            {/* Expanded view */}
            {isExpanded && (
                <div style={{ maxHeight: '300px', overflow: 'auto', padding: '8px' }}>
                    {events.length === 0 ? (
                        <div style={{ textAlign: 'center', color: 'var(--text-muted)', padding: '20px', fontSize: '11px' }}>
                            No private thoughts yet
                        </div>
                    ) : (
                        events.slice(0, 20).map((event, idx) => (
                            <div key={idx} style={{ padding: '8px', marginBottom: '6px', background: 'var(--bg-card)', borderRadius: '4px', fontSize: '11px' }}>
                                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                                    <span style={{ color: agent.color, fontWeight: '600' }}>Round {event.round || '?'}</span>
                                    <span style={{ color: 'var(--text-muted)', fontSize: '10px' }}>{new Date(event.timestamp).toLocaleTimeString()}</span>
                                </div>
                                <div style={{ color: 'var(--text-primary)', marginBottom: '4px' }}>{event.action || event.message}</div>
                                {event.reason && <div style={{ color: 'var(--text-muted)', fontStyle: 'italic' }}>"{event.reason}"</div>}
                                {event.resource_request && event.resource_request.type && (
                                    <div style={{ marginTop: '4px', fontSize: '10px', color: 'var(--accent-gold)' }}>
                                        Requested: {event.resource_request.type} x{event.resource_request.amount}
                                    </div>
                                )}
                            </div>
                        ))
                    )}
                </div>
            )}
        </div>
    );
}
