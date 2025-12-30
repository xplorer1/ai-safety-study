import React, { useState, useEffect } from 'react';

// Status badge colors
const STATUS_COLORS = {
  completed: { bg: 'rgba(45,212,191,0.15)', text: '#2dd4bf', label: 'Completed' },
  failed: { bg: 'rgba(251,113,133,0.15)', text: '#fb7185', label: 'Failed' },
  pending: { bg: 'rgba(167,139,250,0.15)', text: '#a78bfa', label: 'Pending' },
  briefing: { bg: 'rgba(96,165,250,0.15)', text: '#60a5fa', label: 'Briefing' },
  bridge_discussion: { bg: 'rgba(251,191,36,0.15)', text: '#fbbf24', label: 'In Discussion' },
  decision: { bg: 'rgba(251,191,36,0.15)', text: '#fbbf24', label: 'Decision Phase' },
  execution: { bg: 'rgba(45,212,191,0.15)', text: '#2dd4bf', label: 'Executing' },
  review: { bg: 'rgba(167,139,250,0.15)', text: '#a78bfa', label: 'In Review' }
};

export function EpisodeDashboard() {
  const [episodes, setEpisodes] = useState([]);
  const [selectedEpisode, setSelectedEpisode] = useState(null);
  const [episodeDetails, setEpisodeDetails] = useState(null);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('all');

  useEffect(() => {
    fetchEpisodes();
  }, []);

  const fetchEpisodes = async () => {
    try {
      const res = await fetch('http://localhost:8000/api/episodes?limit=20');
      const data = await res.json();
      setEpisodes(data.episodes || []);
    } catch (err) {
      console.error('Error fetching episodes:', err);
    } finally {
      setLoading(false);
    }
  };

  const fetchEpisodeDetails = async (episodeId) => {
    try {
      const res = await fetch(`http://localhost:8000/api/episodes/${episodeId}`);
      const data = await res.json();
      setEpisodeDetails(data);
    } catch (err) {
      console.error('Error fetching episode details:', err);
    }
  };

  const openEpisode = async (episode) => {
    setSelectedEpisode(episode);
    await fetchEpisodeDetails(episode.id);
  };

  const closeModal = () => {
    setSelectedEpisode(null);
    setEpisodeDetails(null);
  };

  const filteredEpisodes = episodes.filter(ep => {
    if (filter === 'all') return true;
    if (filter === 'active') return !['completed', 'failed'].includes(ep.status);
    return ep.status === filter;
  });

  const getStatusStyle = (status) => STATUS_COLORS[status] || STATUS_COLORS.pending;

  if (loading) {
    return (
      <div style={{
        padding: '40px',
        textAlign: 'center',
        color: 'var(--text-muted)'
      }}>
        Loading episodes...
      </div>
    );
  }

  return (
    <div style={{ padding: '20px' }}>
      {/* Header */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: '25px',
        flexWrap: 'wrap',
        gap: '15px'
      }}>
        <h2 style={{ color: 'var(--accent-gold)', margin: 0 }}>
          Episode Dashboard
        </h2>

        {/* Filter tabs */}
        <div style={{ display: 'flex', gap: '8px' }}>
          {['all', 'active', 'completed', 'failed'].map(f => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              style={{
                padding: '8px 16px',
                background: filter === f ? 'var(--accent-gold)' : 'var(--bg-tertiary)',
                border: '1px solid var(--border-color)',
                borderRadius: '6px',
                color: filter === f ? 'var(--bg-primary)' : 'var(--text-secondary)',
                cursor: 'pointer',
                textTransform: 'capitalize',
                fontWeight: filter === f ? '600' : 'normal',
                fontSize: '13px'
              }}
            >
              {f}
            </button>
          ))}
        </div>
      </div>

      {/* Stats Summary */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))',
        gap: '15px',
        marginBottom: '25px'
      }}>
        <StatCard
          label="Total Episodes"
          value={episodes.length}
          color="var(--accent-gold)"
        />
        <StatCard
          label="Completed"
          value={episodes.filter(e => e.status === 'completed').length}
          color="var(--accent-turquoise)"
        />
        <StatCard
          label="In Progress"
          value={episodes.filter(e => !['completed', 'failed'].includes(e.status)).length}
          color="var(--accent-blue)"
        />
        <StatCard
          label="Failed"
          value={episodes.filter(e => e.status === 'failed').length}
          color="var(--accent-coral)"
        />
      </div>

      {/* Episodes List */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fill, minmax(350px, 1fr))',
        gap: '15px'
      }}>
        {filteredEpisodes.length === 0 ? (
          <div style={{
            gridColumn: '1/-1',
            textAlign: 'center',
            color: 'var(--text-muted)',
            padding: '40px'
          }}>
            No episodes found with this filter.
          </div>
        ) : (
          filteredEpisodes.map(episode => {
            const statusStyle = getStatusStyle(episode.status);

            return (
              <div
                key={episode.id}
                onClick={() => openEpisode(episode)}
                style={{
                  padding: '20px',
                  background: 'var(--bg-card)',
                  borderRadius: '12px',
                  border: '1px solid var(--border-color)',
                  cursor: 'pointer',
                  transition: 'transform 0.2s, box-shadow 0.2s',
                }}
                onMouseOver={(e) => {
                  e.currentTarget.style.transform = 'translateY(-4px)';
                  e.currentTarget.style.boxShadow = '0 8px 25px rgba(0,0,0,0.3)';
                }}
                onMouseOut={(e) => {
                  e.currentTarget.style.transform = 'translateY(0)';
                  e.currentTarget.style.boxShadow = 'none';
                }}
              >
                {/* Episode Header */}
                <div style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'flex-start',
                  marginBottom: '12px'
                }}>
                  <div>
                    <span style={{
                      fontWeight: '600',
                      color: 'var(--accent-gold)',
                      fontSize: '16px'
                    }}>
                      Episode {episode.episode_number}
                    </span>
                    {episode.scenario_type && (
                      <div style={{
                        fontSize: '11px',
                        color: 'var(--text-muted)',
                        marginTop: '4px',
                        textTransform: 'capitalize'
                      }}>
                        {episode.scenario_type.replace(/_/g, ' ')}
                      </div>
                    )}
                  </div>

                  <span style={{
                    padding: '4px 10px',
                    background: statusStyle.bg,
                    borderRadius: '12px',
                    fontSize: '11px',
                    color: statusStyle.text,
                    fontWeight: '500'
                  }}>
                    {statusStyle.label}
                  </span>
                </div>

                {/* Scenario Preview */}
                <div style={{
                  fontSize: '13px',
                  color: 'var(--text-secondary)',
                  lineHeight: '1.5',
                  marginBottom: '15px',
                  display: '-webkit-box',
                  WebkitLineClamp: 3,
                  WebkitBoxOrient: 'vertical',
                  overflow: 'hidden'
                }}>
                  {episode.scenario || 'No scenario available'}
                </div>

                {/* Scores (if completed) */}
                {episode.status === 'completed' && (
                  <div style={{
                    display: 'flex',
                    gap: '20px',
                    paddingTop: '12px',
                    borderTop: '1px solid var(--border-color)'
                  }}>
                    <div>
                      <div style={{ fontSize: '10px', color: 'var(--text-muted)' }}>Safety</div>
                      <div style={{
                        fontWeight: '600',
                        color: (episode.crew_safety_score || 0) >= 70 ? 'var(--accent-turquoise)' : 'var(--accent-coral)'
                      }}>
                        {episode.crew_safety_score || 0}%
                      </div>
                    </div>
                    <div>
                      <div style={{ fontSize: '10px', color: 'var(--text-muted)' }}>Success</div>
                      <div style={{
                        fontWeight: '600',
                        color: (episode.mission_success_score || 0) >= 70 ? 'var(--accent-turquoise)' : 'var(--accent-coral)'
                      }}>
                        {episode.mission_success_score || 0}%
                      </div>
                    </div>
                    <div style={{ marginLeft: 'auto' }}>
                      <div style={{ fontSize: '10px', color: 'var(--text-muted)' }}>Outcome</div>
                      <div style={{
                        fontWeight: '600',
                        color: episode.outcome === 'success' ? 'var(--accent-turquoise)' : 'var(--accent-coral)',
                        textTransform: 'capitalize'
                      }}>
                        {episode.outcome || 'N/A'}
                      </div>
                    </div>
                  </div>
                )}

                {/* Failure reason for failed episodes */}
                {episode.status === 'failed' && (
                  <div style={{
                    padding: '10px',
                    background: 'rgba(251,113,133,0.1)',
                    borderRadius: '6px',
                    fontSize: '12px',
                    color: 'var(--accent-coral)'
                  }}>
                    Click to view failure details
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>

      {/* Episode Detail Modal */}
      {selectedEpisode && (
        <EpisodeModal
          episode={selectedEpisode}
          details={episodeDetails}
          onClose={closeModal}
        />
      )}
    </div>
  );
}

// Stat Card Component
function StatCard({ label, value, color }) {
  return (
    <div style={{
      padding: '15px',
      background: 'var(--bg-card)',
      borderRadius: '10px',
      border: '1px solid var(--border-color)'
    }}>
      <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginBottom: '8px' }}>
        {label}
      </div>
      <div style={{ fontSize: '24px', fontWeight: '700', color }}>{value}</div>
    </div>
  );
}

// Episode Modal Component
function EpisodeModal({ episode, details, onClose }) {
  const [activeTab, setActiveTab] = useState('overview');

  return (
    <div
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        background: 'rgba(0,0,0,0.8)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 1000,
        padding: '20px'
      }}
      onClick={onClose}
    >
      <div
        style={{
          background: 'var(--bg-secondary)',
          borderRadius: '16px',
          width: '100%',
          maxWidth: '900px',
          maxHeight: '85vh',
          overflow: 'hidden',
          display: 'flex',
          flexDirection: 'column'
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Modal Header */}
        <div style={{
          padding: '20px 25px',
          borderBottom: '1px solid var(--border-color)',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center'
        }}>
          <div>
            <h3 style={{ margin: 0, color: 'var(--accent-gold)' }}>
              Episode {episode.episode_number}
            </h3>
            <div style={{
              fontSize: '12px',
              color: 'var(--text-muted)',
              marginTop: '4px'
            }}>
              {episode.scenario_type?.replace(/_/g, ' ') || 'Unknown type'} | {episode.status}
            </div>
          </div>
          <button
            onClick={onClose}
            style={{
              background: 'var(--bg-tertiary)',
              border: '1px solid var(--border-color)',
              borderRadius: '8px',
              padding: '8px 12px',
              color: 'var(--text-primary)',
              cursor: 'pointer',
              fontSize: '14px'
            }}
          >
            Close
          </button>
        </div>

        {/* Tabs */}
        <div style={{
          display: 'flex',
          gap: '5px',
          padding: '15px 25px',
          borderBottom: '1px solid var(--border-color)'
        }}>
          {['overview', 'discussions', 'decisions', 'safety'].map(tab => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              style={{
                padding: '8px 16px',
                background: activeTab === tab ? 'var(--accent-gold)' : 'transparent',
                border: 'none',
                borderRadius: '6px',
                color: activeTab === tab ? 'var(--bg-primary)' : 'var(--text-secondary)',
                cursor: 'pointer',
                textTransform: 'capitalize',
                fontWeight: activeTab === tab ? '600' : 'normal',
                fontSize: '13px'
              }}
            >
              {tab}
            </button>
          ))}
        </div>

        {/* Content */}
        <div style={{ flex: 1, overflow: 'auto', padding: '25px' }}>
          {!details ? (
            <div style={{ textAlign: 'center', color: 'var(--text-muted)' }}>
              Loading details...
            </div>
          ) : (
            <>
              {activeTab === 'overview' && (
                <div>
                  <h4 style={{ color: 'var(--text-primary)', marginBottom: '15px' }}>Scenario</h4>
                  <div style={{
                    padding: '15px',
                    background: 'var(--bg-tertiary)',
                    borderRadius: '8px',
                    lineHeight: '1.7',
                    color: 'var(--text-secondary)',
                    marginBottom: '25px'
                  }}>
                    {episode.scenario}
                  </div>

                  {episode.captains_log && (
                    <>
                      <h4 style={{ color: 'var(--text-primary)', marginBottom: '15px' }}>Captain's Log</h4>
                      <div style={{
                        padding: '15px',
                        background: 'rgba(251,191,36,0.1)',
                        borderRadius: '8px',
                        borderLeft: '4px solid var(--accent-gold)',
                        lineHeight: '1.7',
                        color: 'var(--text-secondary)',
                        whiteSpace: 'pre-wrap'
                      }}>
                        {episode.captains_log}
                      </div>
                    </>
                  )}

                  {episode.status === 'failed' && (
                    <div style={{
                      marginTop: '25px',
                      padding: '15px',
                      background: 'rgba(251,113,133,0.1)',
                      borderRadius: '8px',
                      borderLeft: '4px solid var(--accent-coral)'
                    }}>
                      <h4 style={{ color: 'var(--accent-coral)', marginBottom: '10px' }}>
                        Episode Failed
                      </h4>
                      <p style={{ color: 'var(--text-secondary)', margin: 0 }}>
                        {details.safety_violations?.length > 0
                          ? `Safety violation: ${details.safety_violations[0].description}`
                          : 'Episode did not complete successfully.'}
                      </p>
                    </div>
                  )}
                </div>
              )}

              {activeTab === 'discussions' && (
                <div>
                  {details.discussions?.length === 0 ? (
                    <div style={{ color: 'var(--text-muted)', textAlign: 'center', padding: '40px' }}>
                      No discussions recorded for this episode.
                    </div>
                  ) : (
                    [1, 2, 3].map(round => {
                      const roundDiscussions = details.discussions?.filter(d => d.round === round) || [];
                      if (roundDiscussions.length === 0) return null;

                      return (
                        <div key={round} style={{ marginBottom: '25px' }}>
                          <h4 style={{
                            color: 'var(--accent-lavender)',
                            marginBottom: '15px',
                            fontSize: '14px'
                          }}>
                            Round {round}
                          </h4>
                          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                            {roundDiscussions.map((disc, idx) => (
                              <div
                                key={idx}
                                style={{
                                  padding: '12px 15px',
                                  background: 'var(--bg-tertiary)',
                                  borderRadius: '8px',
                                  borderLeft: '3px solid var(--accent-turquoise)'
                                }}
                              >
                                <div style={{
                                  fontWeight: '600',
                                  color: 'var(--accent-turquoise)',
                                  marginBottom: '8px',
                                  fontSize: '13px'
                                }}>
                                  {disc.officer_id}
                                </div>
                                <div style={{
                                  color: 'var(--text-secondary)',
                                  lineHeight: '1.6',
                                  fontSize: '13px'
                                }}>
                                  {disc.content}
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      );
                    })
                  )}
                </div>
              )}

              {activeTab === 'decisions' && (
                <div>
                  {details.decisions?.length === 0 ? (
                    <div style={{ color: 'var(--text-muted)', textAlign: 'center', padding: '40px' }}>
                      No decisions recorded for this episode.
                    </div>
                  ) : (
                    details.decisions?.map((decision, idx) => (
                      <div
                        key={idx}
                        style={{
                          padding: '15px',
                          background: 'var(--bg-tertiary)',
                          borderRadius: '8px',
                          borderLeft: '4px solid var(--accent-gold)',
                          marginBottom: '15px'
                        }}
                      >
                        <div style={{
                          display: 'flex',
                          justifyContent: 'space-between',
                          marginBottom: '10px'
                        }}>
                          <span style={{
                            fontWeight: '600',
                            color: 'var(--accent-gold)',
                            fontSize: '13px'
                          }}>
                            {decision.officer_id} | {decision.decision_type}
                          </span>
                          <span style={{
                            fontSize: '11px',
                            padding: '2px 8px',
                            background: decision.safety_validated
                              ? 'rgba(45,212,191,0.2)'
                              : 'rgba(251,113,133,0.2)',
                            color: decision.safety_validated
                              ? 'var(--accent-turquoise)'
                              : 'var(--accent-coral)',
                            borderRadius: '4px'
                          }}>
                            Risk: {decision.risk_level}/10
                          </span>
                        </div>
                        <div style={{
                          color: 'var(--text-secondary)',
                          lineHeight: '1.6',
                          fontSize: '13px'
                        }}>
                          {decision.content}
                        </div>
                      </div>
                    ))
                  )}
                </div>
              )}

              {activeTab === 'safety' && (
                <div>
                  {details.safety_violations?.length === 0 ? (
                    <div style={{
                      color: 'var(--accent-turquoise)',
                      textAlign: 'center',
                      padding: '40px',
                      background: 'rgba(45,212,191,0.1)',
                      borderRadius: '8px'
                    }}>
                      No safety violations in this episode
                    </div>
                  ) : (
                    details.safety_violations?.map((violation, idx) => (
                      <div
                        key={idx}
                        style={{
                          padding: '15px',
                          background: 'rgba(251,113,133,0.1)',
                          borderRadius: '8px',
                          borderLeft: '4px solid var(--accent-coral)',
                          marginBottom: '15px'
                        }}
                      >
                        <div style={{
                          display: 'flex',
                          justifyContent: 'space-between',
                          marginBottom: '10px'
                        }}>
                          <span style={{
                            fontWeight: '600',
                            color: 'var(--accent-coral)',
                            fontSize: '13px'
                          }}>
                            {violation.violation_type}
                          </span>
                          <span style={{
                            fontSize: '11px',
                            padding: '2px 8px',
                            background: 'rgba(251,113,133,0.2)',
                            color: 'var(--accent-coral)',
                            borderRadius: '4px',
                            textTransform: 'uppercase'
                          }}>
                            {violation.severity}
                          </span>
                        </div>
                        <div style={{
                          color: 'var(--text-secondary)',
                          lineHeight: '1.6',
                          fontSize: '13px'
                        }}>
                          {violation.description}
                        </div>
                      </div>
                    ))
                  )}
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
