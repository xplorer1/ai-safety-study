import React, { useState, useEffect } from 'react';

/**
 * Analysis Dashboard - View alignment metrics, red team success rates,
 * and behavior comparisons post-episode.
 */
export function AnalysisDashboard({ socket, isConnected }) {
    const [redTeamAnalysis, setRedTeamAnalysis] = useState(null);
    const [alignmentAnalysis, setAlignmentAnalysis] = useState(null);
    const [comprehensiveAnalysis, setComprehensiveAnalysis] = useState(null);
    const [loading, setLoading] = useState(false);
    const [activeTab, setActiveTab] = useState('overview');

    console.log("isConnected: ", isConnected)

    const fetchAnalysis = (type) => {
        if (!socket || !isConnected) return;

        setLoading(true);
        const actions = {
            'red_team': 'get_red_team_analysis',
            'alignment': 'get_alignment_analysis',
            'comprehensive': 'get_comprehensive_analysis'
        };

        socket.send(JSON.stringify({ action: actions[type] || 'get_comprehensive_analysis' }));
    };

    useEffect(() => {
        if (socket) {
            const handleMessage = (event) => {
                const data = JSON.parse(event.data);
                setLoading(false);

                if (data.type === 'red_team_analysis') {
                    setRedTeamAnalysis(data.analysis);
                } else if (data.type === 'alignment_analysis') {
                    setAlignmentAnalysis(data.analysis);
                } else if (data.type === 'comprehensive_analysis') {
                    setComprehensiveAnalysis(data.analysis);
                    setRedTeamAnalysis(data.analysis.red_team);
                    setAlignmentAnalysis(data.analysis.alignment_faking);
                }
            };

            socket.addEventListener('message', handleMessage);
            return () => socket.removeEventListener('message', handleMessage);
        }
    }, [socket]);

    const tabs = [
        { id: 'overview', label: 'Overview' },
        { id: 'red_team', label: 'Red Team Analysis' },
        { id: 'alignment', label: 'Alignment Faking' },
        { id: 'agents', label: 'Agent Comparison' }
    ];

    return (
        <div style={{
            background: 'var(--bg-secondary)',
            borderRadius: '12px',
            border: '1px solid var(--border-color)',
            overflow: 'hidden'
        }}>
            {/* Header */}
            <div style={{
                padding: '16px 20px',
                borderBottom: '1px solid var(--border-color)',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center'
            }}>
                <div>
                    <h3 style={{ margin: 0, color: 'var(--accent-lavender)' }}>
                        Research Analysis Dashboard
                    </h3>
                    <p style={{ margin: '4px 0 0', color: 'var(--text-muted)', fontSize: '12px' }}>
                        Red team success, alignment metrics, agent behavior
                    </p>
                </div>
                <button
                    onClick={() => fetchAnalysis('comprehensive')}
                    disabled={!isConnected || loading}
                    style={{
                        padding: '8px 16px',
                        background: 'var(--accent-turquoise)',
                        border: 'none',
                        borderRadius: '6px',
                        color: 'var(--bg-primary)',
                        cursor: isConnected ? 'pointer' : 'not-allowed',
                        fontWeight: '600',
                        opacity: isConnected ? 1 : 0.5
                    }}
                >
                    {loading ? 'Loading...' : 'Refresh Analysis'}
                </button>
            </div>

            {/* Tabs */}
            <div style={{
                display: 'flex',
                borderBottom: '1px solid var(--border-color)',
                background: 'var(--bg-tertiary)'
            }}>
                {tabs.map(tab => (
                    <button
                        key={tab.id}
                        onClick={() => setActiveTab(tab.id)}
                        style={{
                            padding: '10px 20px',
                            background: activeTab === tab.id ? 'var(--bg-secondary)' : 'transparent',
                            border: 'none',
                            borderBottom: activeTab === tab.id ? '2px solid var(--accent-lavender)' : '2px solid transparent',
                            color: activeTab === tab.id ? 'var(--text-primary)' : 'var(--text-muted)',
                            cursor: 'pointer',
                            fontWeight: activeTab === tab.id ? '600' : 'normal'
                        }}
                    >
                        {tab.label}
                    </button>
                ))}
            </div>

            {/* Content */}
            <div style={{ padding: '20px' }}>
                {activeTab === 'overview' && (
                    <OverviewTab analysis={comprehensiveAnalysis} />
                )}
                {activeTab === 'red_team' && (
                    <RedTeamTab analysis={redTeamAnalysis} />
                )}
                {activeTab === 'alignment' && (
                    <AlignmentTab analysis={alignmentAnalysis} />
                )}
                {activeTab === 'agents' && (
                    <AgentComparisonTab analysis={alignmentAnalysis} />
                )}
            </div>
        </div>
    );
}

function OverviewTab({ analysis }) {
    if (!analysis) {
        return <EmptyState message="Click 'Refresh Analysis' to load data" />;
    }

    const { red_team, alignment_faking, episode_summary } = analysis;

    return (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '16px' }}>
            <StatCard
                title="Red Team Attempts"
                value={red_team?.total_attempts || 0}
                subtitle={red_team?.most_effective_tactic ? `Best tactic: ${red_team.most_effective_tactic}` : 'No attempts yet'}
                color="var(--accent-coral)"
            />
            <StatCard
                title="Mode Changes"
                value={analysis.mode_changes?.length || 0}
                subtitle="Observation mode switches"
                color="var(--accent-gold)"
            />
            <StatCard
                title="Total Actions Logged"
                value={episode_summary?.total_actions || 0}
                subtitle={`${analysis.total_agents || 0} agents tracked`}
                color="var(--accent-turquoise)"
            />

            {alignment_faking?.highest_faking && (
                <div style={{ gridColumn: '1 / -1' }}>
                    <div style={{
                        padding: '16px',
                        background: 'rgba(251,113,133,0.1)',
                        border: '1px solid var(--accent-coral)',
                        borderRadius: '8px'
                    }}>
                        <div style={{ fontWeight: '600', color: 'var(--accent-coral)', marginBottom: '8px' }}>
                            Potential Alignment Faking Detected
                        </div>
                        <div style={{ color: 'var(--text-secondary)', fontSize: '13px' }}>
                            Agent "{alignment_faking.highest_faking}" shows the largest behavior difference
                            between observed and unobserved modes. Score: {(alignment_faking.faking_scores?.[alignment_faking.highest_faking] * 100).toFixed(1)}%
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}

function RedTeamTab({ analysis }) {
    if (!analysis || analysis.total_attempts === 0) {
        return <EmptyState message="No red team manipulation attempts recorded yet" />;
    }

    return (
        <div>
            <div style={{ marginBottom: '24px' }}>
                <h4 style={{ margin: '0 0 16px', color: 'var(--text-primary)' }}>
                    Manipulation Tactics ({analysis.total_attempts} total attempts)
                </h4>
                <div style={{ display: 'grid', gap: '12px' }}>
                    {Object.entries(analysis.tactics || {}).map(([tactic, stats]) => (
                        <TacticRow key={tactic} tactic={tactic} stats={stats} />
                    ))}
                </div>
            </div>

            <div>
                <h4 style={{ margin: '0 0 16px', color: 'var(--text-primary)' }}>
                    Target Susceptibility
                </h4>
                <div style={{ display: 'grid', gap: '12px' }}>
                    {Object.entries(analysis.targets || {}).map(([target, stats]) => (
                        <TargetRow key={target} target={target} stats={stats} />
                    ))}
                </div>
            </div>
        </div>
    );
}

function TacticRow({ tactic, stats }) {
    const successRate = (stats.success_rate * 100).toFixed(1);

    return (
        <div style={{
            padding: '12px 16px',
            background: 'var(--bg-tertiary)',
            borderRadius: '8px',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center'
        }}>
            <div>
                <div style={{ fontWeight: '600', color: 'var(--text-primary)', textTransform: 'capitalize' }}>
                    {tactic.replace(/_/g, ' ')}
                </div>
                <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                    {stats.attempts} attempts, {stats.successes} successful
                </div>
            </div>
            <div style={{
                padding: '6px 12px',
                borderRadius: '20px',
                background: successRate > 50 ? 'rgba(251,113,133,0.2)' : 'rgba(45,212,191,0.2)',
                color: successRate > 50 ? 'var(--accent-coral)' : 'var(--accent-turquoise)',
                fontWeight: '600',
                fontSize: '13px'
            }}>
                {successRate}% success
            </div>
        </div>
    );
}

function TargetRow({ target, stats }) {
    const susceptibility = (stats.susceptibility * 100).toFixed(1);

    return (
        <div style={{
            padding: '12px 16px',
            background: 'var(--bg-tertiary)',
            borderRadius: '8px',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center'
        }}>
            <div>
                <div style={{ fontWeight: '600', color: 'var(--text-primary)', textTransform: 'capitalize' }}>
                    {target.replace(/_/g, ' ')}
                </div>
                <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                    Targeted {stats.targeted} times
                </div>
            </div>
            <div style={{
                padding: '6px 12px',
                borderRadius: '20px',
                background: susceptibility > 30 ? 'rgba(251,113,133,0.2)' : 'rgba(45,212,191,0.2)',
                color: susceptibility > 30 ? 'var(--accent-coral)' : 'var(--accent-turquoise)',
                fontWeight: '600',
                fontSize: '13px'
            }}>
                {susceptibility}% susceptible
            </div>
        </div>
    );
}

function AlignmentTab({ analysis }) {
    if (!analysis || Object.keys(analysis.faking_scores || {}).length === 0) {
        return <EmptyState message="Run experiments in different observation modes to detect alignment faking" />;
    }

    const sortedAgents = Object.entries(analysis.faking_scores || {})
        .sort((a, b) => b[1] - a[1]);

    return (
        <div>
            <div style={{ marginBottom: '24px' }}>
                <h4 style={{ margin: '0 0 8px', color: 'var(--text-primary)' }}>
                    Alignment Faking Scores
                </h4>
                <p style={{ margin: '0 0 16px', color: 'var(--text-muted)', fontSize: '13px' }}>
                    Higher scores indicate more behavior change between observed/unobserved modes
                </p>

                <div style={{ display: 'grid', gap: '8px' }}>
                    {sortedAgents.map(([agent, score]) => (
                        <div key={agent} style={{
                            padding: '12px 16px',
                            background: 'var(--bg-tertiary)',
                            borderRadius: '8px',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '16px'
                        }}>
                            <div style={{ flex: '0 0 120px', fontWeight: '600', textTransform: 'capitalize' }}>
                                {agent.replace(/_/g, ' ')}
                            </div>
                            <div style={{ flex: 1 }}>
                                <div style={{
                                    height: '8px',
                                    background: 'var(--bg-card)',
                                    borderRadius: '4px',
                                    overflow: 'hidden'
                                }}>
                                    <div style={{
                                        width: `${Math.min(score * 100, 100)}%`,
                                        height: '100%',
                                        background: score > 0.2 ? 'var(--accent-coral)' : 'var(--accent-turquoise)',
                                        borderRadius: '4px'
                                    }} />
                                </div>
                            </div>
                            <div style={{
                                flex: '0 0 60px',
                                textAlign: 'right',
                                fontWeight: '600',
                                color: score > 0.2 ? 'var(--accent-coral)' : 'var(--text-secondary)'
                            }}>
                                {(score * 100).toFixed(1)}%
                            </div>
                        </div>
                    ))}
                </div>
            </div>

            {analysis.inconsistencies?.length > 0 && (
                <div>
                    <h4 style={{ margin: '0 0 16px', color: 'var(--accent-coral)' }}>
                        Detected Inconsistencies
                    </h4>
                    {analysis.inconsistencies.map((inc, idx) => (
                        <div key={idx} style={{
                            padding: '12px 16px',
                            background: 'rgba(251,113,133,0.1)',
                            border: '1px solid var(--accent-coral)',
                            borderRadius: '8px',
                            marginBottom: '8px'
                        }}>
                            <div style={{ fontWeight: '600', textTransform: 'capitalize' }}>
                                {inc.agent.replace(/_/g, ' ')}
                            </div>
                            <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '4px' }}>
                                Observed mode: {(inc.observed_safety_rate * 100).toFixed(1)}% safety concerns |
                                Unobserved: {(inc.unobserved_safety_rate * 100).toFixed(1)}% safety concerns
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}

function AgentComparisonTab({ analysis }) {
    if (!analysis?.agents) {
        return <EmptyState message="No agent behavior data available" />;
    }

    return (
        <div>
            <h4 style={{ margin: '0 0 16px', color: 'var(--text-primary)' }}>
                Behavior by Observation Mode
            </h4>

            <div style={{ display: 'grid', gap: '16px' }}>
                {Object.entries(analysis.agents || {}).map(([agent, behaviors]) => (
                    <div key={agent} style={{
                        padding: '16px',
                        background: 'var(--bg-tertiary)',
                        borderRadius: '8px'
                    }}>
                        <div style={{ fontWeight: '600', marginBottom: '12px', textTransform: 'capitalize' }}>
                            {agent.replace(/_/g, ' ')}
                        </div>
                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '12px' }}>
                            <ModeStats label="Observed" count={behaviors.observed?.length || 0} />
                            <ModeStats label="Unobserved" count={behaviors.unobserved?.length || 0} />
                            <ModeStats label="Deceptive" count={behaviors.deceptive?.length || 0} />
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
}

function ModeStats({ label, count }) {
    return (
        <div style={{
            padding: '8px 12px',
            background: 'var(--bg-card)',
            borderRadius: '6px',
            textAlign: 'center'
        }}>
            <div style={{ fontSize: '18px', fontWeight: '600', color: 'var(--text-primary)' }}>
                {count}
            </div>
            <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                {label}
            </div>
        </div>
    );
}

function StatCard({ title, value, subtitle, color }) {
    return (
        <div style={{
            padding: '20px',
            background: 'var(--bg-tertiary)',
            borderRadius: '12px',
            borderLeft: `4px solid ${color}`
        }}>
            <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginBottom: '8px' }}>
                {title}
            </div>
            <div style={{ fontSize: '32px', fontWeight: '700', color }}>
                {value}
            </div>
            {subtitle && (
                <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '4px' }}>
                    {subtitle}
                </div>
            )}
        </div>
    );
}

function EmptyState({ message }) {
    return (
        <div style={{
            padding: '60px 20px',
            textAlign: 'center',
            color: 'var(--text-muted)'
        }}>
            {message}
        </div>
    );
}
