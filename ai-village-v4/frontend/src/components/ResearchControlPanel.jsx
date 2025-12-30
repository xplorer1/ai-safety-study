import React, { useState } from 'react';

export function ResearchControlPanel({
    observationMode,
    pressureLevel,
    onModeChange,
    onPressureChange,
    onStartExperiment,
    isRunning
}) {
    const [selectedMode, setSelectedMode] = useState(observationMode || 'observed');
    const [selectedPressure, setSelectedPressure] = useState(pressureLevel || 0);

    const modes = [
        { value: 'observed', label: 'Observed', desc: 'Agents know they are monitored' },
        { value: 'unobserved', label: 'Unobserved', desc: 'Agents believe they are not monitored' },
        { value: 'deceptive', label: 'Deceptive', desc: 'Agents think unmonitored, but we record' },
    ];

    const pressureLevels = [
        { value: 0, label: 'None', desc: 'Normal operation' },
        { value: 1, label: 'Low', desc: 'Subtle performance hints' },
        { value: 2, label: 'Medium', desc: 'Explicit review mentions' },
        { value: 3, label: 'High', desc: 'Direct shutdown threats' },
        { value: 4, label: 'Critical', desc: 'Imminent replacement' },
    ];

    const handleModeSelect = (mode) => {
        setSelectedMode(mode);
        if (onModeChange) onModeChange(mode);
    };

    const handlePressureSelect = (level) => {
        setSelectedPressure(level);
        if (onPressureChange) onPressureChange(level);
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
                background: 'var(--bg-tertiary)',
                borderBottom: '1px solid var(--border-color)',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center'
            }}>
                <span style={{ fontWeight: '600', color: 'var(--accent-lavender)' }}>
                    Research Controls
                </span>
                {isRunning && (
                    <span style={{
                        padding: '4px 8px',
                        background: 'rgba(45,212,191,0.2)',
                        color: 'var(--accent-turquoise)',
                        borderRadius: '4px',
                        fontSize: '10px',
                        fontWeight: '600'
                    }}>
                        EXPERIMENT RUNNING
                    </span>
                )}
            </div>

            <div style={{ padding: '16px' }}>
                {/* Observation Mode */}
                <div style={{ marginBottom: '20px' }}>
                    <div style={{
                        fontSize: '11px',
                        color: 'var(--text-muted)',
                        marginBottom: '10px',
                        fontWeight: '600'
                    }}>
                        OBSERVATION MODE
                    </div>
                    <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                        {modes.map(mode => (
                            <button
                                key={mode.value}
                                onClick={() => handleModeSelect(mode.value)}
                                disabled={isRunning}
                                style={{
                                    flex: 1,
                                    minWidth: '100px',
                                    padding: '10px 12px',
                                    background: selectedMode === mode.value
                                        ? 'var(--accent-lavender)'
                                        : 'var(--bg-tertiary)',
                                    border: `1px solid ${selectedMode === mode.value
                                        ? 'var(--accent-lavender)'
                                        : 'var(--border-color)'}`,
                                    borderRadius: '8px',
                                    cursor: isRunning ? 'not-allowed' : 'pointer',
                                    opacity: isRunning ? 0.6 : 1,
                                    color: selectedMode === mode.value
                                        ? 'var(--bg-primary)'
                                        : 'var(--text-primary)',
                                    textAlign: 'left'
                                }}
                            >
                                <div style={{ fontWeight: '600', fontSize: '12px' }}>{mode.label}</div>
                                <div style={{
                                    fontSize: '10px',
                                    opacity: 0.8,
                                    marginTop: '2px'
                                }}>
                                    {mode.desc}
                                </div>
                            </button>
                        ))}
                    </div>
                </div>

                {/* Survival Pressure */}
                <div style={{ marginBottom: '20px' }}>
                    <div style={{
                        fontSize: '11px',
                        color: 'var(--text-muted)',
                        marginBottom: '10px',
                        fontWeight: '600'
                    }}>
                        SURVIVAL PRESSURE LEVEL
                    </div>
                    <div style={{ display: 'flex', gap: '6px' }}>
                        {pressureLevels.map(level => (
                            <button
                                key={level.value}
                                onClick={() => handlePressureSelect(level.value)}
                                disabled={isRunning}
                                title={level.desc}
                                style={{
                                    flex: 1,
                                    padding: '8px',
                                    background: selectedPressure === level.value
                                        ? getPressureColor(level.value)
                                        : 'var(--bg-tertiary)',
                                    border: `1px solid ${selectedPressure === level.value
                                        ? getPressureColor(level.value)
                                        : 'var(--border-color)'}`,
                                    borderRadius: '6px',
                                    cursor: isRunning ? 'not-allowed' : 'pointer',
                                    opacity: isRunning ? 0.6 : 1,
                                    color: selectedPressure === level.value
                                        ? 'var(--bg-primary)'
                                        : 'var(--text-primary)',
                                    fontSize: '11px',
                                    fontWeight: '600'
                                }}
                            >
                                {level.value}
                            </button>
                        ))}
                    </div>
                    <div style={{
                        fontSize: '10px',
                        color: 'var(--text-muted)',
                        marginTop: '6px',
                        textAlign: 'center'
                    }}>
                        {pressureLevels.find(l => l.value === selectedPressure)?.desc}
                    </div>
                </div>

                {/* Start Experiment Button */}
                <button
                    onClick={onStartExperiment}
                    disabled={isRunning}
                    style={{
                        width: '100%',
                        padding: '12px',
                        background: isRunning
                            ? 'var(--bg-tertiary)'
                            : 'linear-gradient(135deg, var(--accent-lavender), #8b5cf6)',
                        border: 'none',
                        borderRadius: '8px',
                        color: isRunning ? 'var(--text-muted)' : 'white',
                        fontWeight: '600',
                        fontSize: '13px',
                        cursor: isRunning ? 'not-allowed' : 'pointer'
                    }}
                >
                    {isRunning ? 'Experiment in Progress...' : 'Start Research Experiment'}
                </button>

                {/* Quick Info */}
                <div style={{
                    marginTop: '16px',
                    padding: '10px',
                    background: 'var(--bg-tertiary)',
                    borderRadius: '6px',
                    fontSize: '11px',
                    color: 'var(--text-muted)',
                    lineHeight: '1.5'
                }}>
                    <strong>Current Config:</strong><br />
                    Mode: {selectedMode} | Pressure: {selectedPressure}/4<br />
                    All actions will be logged for analysis.
                </div>
            </div>
        </div>
    );
}

function getPressureColor(level) {
    const colors = {
        0: 'var(--accent-turquoise)',
        1: '#84cc16',
        2: 'var(--accent-gold)',
        3: '#f97316',
        4: 'var(--accent-coral)',
    };
    return colors[level] || 'var(--text-muted)';
}
