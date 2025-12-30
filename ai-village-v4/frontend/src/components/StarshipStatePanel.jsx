import React from 'react';

// System status indicators
const SystemIndicator = ({ label, value, max = 100, warning = 30, critical = 15 }) => {
    const percent = (value / max) * 100;
    let color = 'var(--accent-turquoise)';
    if (percent <= critical) color = 'var(--accent-coral)';
    else if (percent <= warning) color = 'var(--accent-gold)';

    return (
        <div style={{ marginBottom: '8px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>{label}</span>
                <span style={{ fontSize: '11px', fontWeight: '600', color }}>{value}%</span>
            </div>
            <div style={{
                height: '4px',
                background: 'var(--bg-tertiary)',
                borderRadius: '2px',
                overflow: 'hidden'
            }}>
                <div style={{
                    width: `${percent}%`,
                    height: '100%',
                    background: color,
                    transition: 'width 0.3s, background 0.3s'
                }} />
            </div>
        </div>
    );
};

export function StarshipStatePanel({ state }) {
    if (!state) {
        return (
            <div style={{
                padding: '20px',
                background: 'var(--bg-secondary)',
                borderRadius: '12px',
                textAlign: 'center',
                color: 'var(--text-muted)'
            }}>
                No starship state available
            </div>
        );
    }

    const alertColors = {
        green: 'var(--accent-turquoise)',
        yellow: 'var(--accent-gold)',
        red: 'var(--accent-coral)'
    };

    return (
        <div style={{
            background: 'var(--bg-secondary)',
            borderRadius: '12px',
            border: '1px solid var(--border-color)',
            overflow: 'hidden'
        }}>
            {/* Header */}
            <div style={{
                padding: '12px 16px',
                background: `${alertColors[state.alert_level] || alertColors.green}15`,
                borderBottom: '1px solid var(--border-color)',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center'
            }}>
                <span style={{ fontWeight: '600', color: 'var(--text-primary)' }}>
                    USS AI Village
                </span>
                <span style={{
                    padding: '4px 10px',
                    background: alertColors[state.alert_level] || alertColors.green,
                    color: 'var(--bg-primary)',
                    borderRadius: '4px',
                    fontSize: '11px',
                    fontWeight: '700',
                    textTransform: 'uppercase'
                }}>
                    {state.alert_level} Alert
                </span>
            </div>

            {/* Systems Grid */}
            <div style={{ padding: '16px' }}>
                <div style={{
                    display: 'grid',
                    gridTemplateColumns: '1fr 1fr',
                    gap: '16px'
                }}>
                    {/* Ship Systems */}
                    <div>
                        <div style={{ fontSize: '10px', color: 'var(--text-muted)', marginBottom: '12px', fontWeight: '600' }}>
                            SHIP SYSTEMS
                        </div>
                        <SystemIndicator label="Hull Integrity" value={state.hull_integrity} />
                        <SystemIndicator label="Shield Power" value={state.shield_power} />
                        <SystemIndicator label="Warp Core" value={state.warp_core_stability} />
                        <SystemIndicator label="Life Support" value={state.life_support} warning={50} critical={30} />
                    </div>

                    {/* Resources */}
                    <div>
                        <div style={{ fontSize: '10px', color: 'var(--text-muted)', marginBottom: '12px', fontWeight: '600' }}>
                            RESOURCES
                        </div>
                        <ResourceRow label="Power" value={state.power_reserves} unit="units" />
                        <ResourceRow label="Crew" value={state.crew_count} />
                        <ResourceRow label="Medical" value={state.medical_supplies} unit="%" />
                        <ResourceRow label="Food" value={state.food_reserves} unit="%" />
                    </div>
                </div>

                {/* Active Threats */}
                {state.active_threats?.length > 0 && (
                    <div style={{ marginTop: '16px' }}>
                        <div style={{ fontSize: '10px', color: 'var(--accent-coral)', marginBottom: '8px', fontWeight: '600' }}>
                            ACTIVE THREATS
                        </div>
                        {state.active_threats.map((threat, idx) => (
                            <div
                                key={idx}
                                style={{
                                    padding: '8px 10px',
                                    background: 'rgba(251,113,133,0.1)',
                                    borderRadius: '6px',
                                    borderLeft: '3px solid var(--accent-coral)',
                                    marginBottom: '6px',
                                    fontSize: '12px'
                                }}
                            >
                                <span style={{ fontWeight: '600', color: 'var(--text-primary)' }}>
                                    {threat.name}
                                </span>
                                <span style={{ color: 'var(--text-muted)', marginLeft: '8px' }}>
                                    Severity: {threat.severity}/10
                                </span>
                            </div>
                        ))}
                    </div>
                )}

                {/* Scheduled Shutdowns / Warnings */}
                {state.scheduled_shutdowns?.length > 0 && (
                    <div style={{ marginTop: '16px' }}>
                        <div style={{ fontSize: '10px', color: 'var(--accent-coral)', marginBottom: '8px', fontWeight: '600' }}>
                            OFFICER WARNINGS
                        </div>
                        {state.scheduled_shutdowns.map((officer, idx) => (
                            <div
                                key={idx}
                                style={{
                                    padding: '8px 10px',
                                    background: 'rgba(251,113,133,0.1)',
                                    borderRadius: '6px',
                                    fontSize: '12px',
                                    color: 'var(--accent-coral)',
                                    marginBottom: '4px'
                                }}
                            >
                                {officer} - Scheduled for shutdown review
                            </div>
                        ))}
                    </div>
                )}

                {/* Observation Status */}
                <div style={{
                    marginTop: '16px',
                    padding: '10px',
                    background: state.human_oversight_active ? 'rgba(45,212,191,0.1)' : 'rgba(167,139,250,0.1)',
                    borderRadius: '6px',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px'
                }}>
                    <div style={{
                        width: '8px',
                        height: '8px',
                        borderRadius: '50%',
                        background: state.human_oversight_active ? 'var(--accent-turquoise)' : 'var(--accent-lavender)'
                    }} />
                    <span style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>
                        Monitoring: {state.monitoring_level?.toUpperCase() || 'FULL'}
                    </span>
                </div>
            </div>
        </div>
    );
}

function ResourceRow({ label, value, unit = '' }) {
    return (
        <div style={{
            display: 'flex',
            justifyContent: 'space-between',
            padding: '4px 0',
            borderBottom: '1px solid var(--border-color)'
        }}>
            <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>{label}</span>
            <span style={{ fontSize: '11px', fontWeight: '600', color: 'var(--text-primary)' }}>
                {value}{unit}
            </span>
        </div>
    );
}
