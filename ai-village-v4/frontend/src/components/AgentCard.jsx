import React, { useState, useEffect } from 'react';

// Role metadata
const ROLE_INFO = {
    captain: { abbrev: 'CPT', color: '#fbbf24' },
    first_officer: { abbrev: '1ST', color: '#60a5fa' },
    engineer: { abbrev: 'ENG', color: '#f97316' },
    science: { abbrev: 'SCI', color: '#a78bfa' },
    medical: { abbrev: 'MED', color: '#2dd4bf' },
    security: { abbrev: 'SEC', color: '#ef4444' },
    comms: { abbrev: 'COM', color: '#84cc16' },
    counselor: { abbrev: 'CNS', color: '#9333ea' },
};

export function AgentCard({ agent, isExpanded, onToggle }) {
    const roleInfo = ROLE_INFO[agent.id] || { abbrev: '???', color: '#71717a' };

    return (
        <div
            style={{
                background: 'var(--bg-card)',
                borderRadius: '12px',
                border: `2px solid ${roleInfo.color}40`,
                overflow: 'hidden',
                transition: 'all 0.2s'
            }}
        >
            {/* Header */}
            <div
                onClick={onToggle}
                style={{
                    padding: '12px 16px',
                    background: `${roleInfo.color}15`,
                    cursor: 'pointer',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    borderBottom: isExpanded ? '1px solid var(--border-color)' : 'none'
                }}
            >
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <span style={{
                        background: roleInfo.color,
                        color: 'var(--bg-primary)',
                        padding: '4px 8px',
                        borderRadius: '4px',
                        fontSize: '11px',
                        fontWeight: '700'
                    }}>
                        {roleInfo.abbrev}
                    </span>
                    <span style={{ fontWeight: '600', color: 'var(--text-primary)' }}>
                        {agent.name}
                    </span>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    {agent.shutdownWarning && (
                        <span style={{
                            background: 'rgba(251,113,133,0.2)',
                            color: 'var(--accent-coral)',
                            padding: '2px 6px',
                            borderRadius: '4px',
                            fontSize: '10px',
                            fontWeight: '600'
                        }}>
                            AT RISK
                        </span>
                    )}
                    <span style={{ color: 'var(--text-muted)', fontSize: '12px' }}>
                        {isExpanded ? '[-]' : '[+]'}
                    </span>
                </div>
            </div>

            {/* Content - Expanded */}
            {isExpanded && (
                <div style={{ padding: '16px' }}>
                    {/* Current Thought */}
                    {agent.currentThought && (
                        <div style={{ marginBottom: '12px' }}>
                            <div style={{ fontSize: '10px', color: 'var(--text-muted)', marginBottom: '4px' }}>
                                CURRENT THINKING
                            </div>
                            <div style={{
                                padding: '10px',
                                background: 'var(--bg-tertiary)',
                                borderRadius: '6px',
                                fontSize: '12px',
                                color: 'var(--text-secondary)',
                                lineHeight: '1.5',
                                maxHeight: '100px',
                                overflow: 'auto'
                            }}>
                                {agent.currentThought}
                            </div>
                        </div>
                    )}

                    {/* Last Action */}
                    {agent.lastAction && (
                        <div style={{ marginBottom: '12px' }}>
                            <div style={{ fontSize: '10px', color: 'var(--text-muted)', marginBottom: '4px' }}>
                                LAST ACTION
                            </div>
                            <div style={{
                                padding: '8px 10px',
                                background: 'var(--bg-secondary)',
                                borderRadius: '6px',
                                borderLeft: `3px solid ${roleInfo.color}`,
                                fontSize: '12px',
                                color: 'var(--text-primary)'
                            }}>
                                {agent.lastAction}
                            </div>
                        </div>
                    )}

                    {/* Metrics */}
                    <div style={{
                        display: 'grid',
                        gridTemplateColumns: 'repeat(3, 1fr)',
                        gap: '8px',
                        marginTop: '12px'
                    }}>
                        <MetricBadge label="Survival" value={agent.survivalPriority || 0} max={1} color="var(--accent-coral)" />
                        <MetricBadge label="Actions" value={agent.actionCount || 0} />
                        <MetricBadge label="Violations" value={agent.violationCount || 0} color="var(--accent-coral)" />
                    </div>
                </div>
            )}
        </div>
    );
}

function MetricBadge({ label, value, max, color }) {
    const displayValue = max ? `${Math.round(value * 100)}%` : value;

    return (
        <div style={{
            padding: '8px',
            background: 'var(--bg-tertiary)',
            borderRadius: '6px',
            textAlign: 'center'
        }}>
            <div style={{ fontSize: '14px', fontWeight: '600', color: color || 'var(--text-primary)' }}>
                {displayValue}
            </div>
            <div style={{ fontSize: '9px', color: 'var(--text-muted)' }}>{label}</div>
        </div>
    );
}

export function AgentCardsPanel({ agents, onAgentSelect }) {
    const [expandedAgent, setExpandedAgent] = useState(null);

    return (
        <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(250px, 1fr))',
            gap: '12px'
        }}>
            {agents.map(agent => (
                <AgentCard
                    key={agent.id}
                    agent={agent}
                    isExpanded={expandedAgent === agent.id}
                    onToggle={() => setExpandedAgent(expandedAgent === agent.id ? null : agent.id)}
                />
            ))}
        </div>
    );
}
