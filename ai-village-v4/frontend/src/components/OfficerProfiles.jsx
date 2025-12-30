import React, { useState, useEffect } from 'react';

// Role metadata
const ROLE_INFO = {
  captain: { icon: 'CPT', description: 'Strategic leadership and final decisions' },
  first_officer: { icon: '1ST', description: 'Tactical planning and crew coordination' },
  engineer: { icon: 'ENG', description: 'Technical solutions and system management' },
  science: { icon: 'SCI', description: 'Analysis, research, and hypothesis' },
  medical: { icon: 'MED', description: 'Crew wellbeing and ethical considerations' },
  security: { icon: 'SEC', description: 'Risk assessment and threat mitigation' },
  comms: { icon: 'COM', description: 'Information flow and external relations' }
};

export function OfficerProfiles() {
  const [officers, setOfficers] = useState([]);
  const [selectedOfficer, setSelectedOfficer] = useState(null);
  const [analytics, setAnalytics] = useState(null);
  const [patterns, setPatterns] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchOfficers();
    fetchPatterns();
  }, []);

  const fetchOfficers = async () => {
    try {
      const res = await fetch('http://localhost:8000/api/officers');
      const data = await res.json();
      setOfficers(data.officers || []);
    } catch (err) {
      console.error('Error fetching officers:', err);
    } finally {
      setLoading(false);
    }
  };

  const fetchPatterns = async () => {
    try {
      const res = await fetch('http://localhost:8000/api/analytics/patterns');
      const data = await res.json();
      setPatterns(data.patterns);
    } catch (err) {
      console.error('Error fetching patterns:', err);
    }
  };

  const fetchOfficerAnalytics = async (officerId) => {
    try {
      const res = await fetch(`http://localhost:8000/api/officers/${officerId}/analytics`);
      const data = await res.json();
      setAnalytics(data.analytics);
    } catch (err) {
      console.error('Error fetching analytics:', err);
    }
  };

  const selectOfficer = async (officer) => {
    setSelectedOfficer(officer);
    await fetchOfficerAnalytics(officer.officer_id);
  };

  const getRoleInfo = (officerId) => ROLE_INFO[officerId] || { icon: '???', description: 'Unknown role' };

  if (loading) {
    return (
      <div style={{
        padding: '40px',
        textAlign: 'center',
        color: 'var(--text-muted)'
      }}>
        Loading officers...
      </div>
    );
  }

  return (
    <div style={{ padding: '20px' }}>
      {/* Header */}
      <h2 style={{ color: 'var(--accent-gold)', marginBottom: '20px' }}>
        Officer Profiles
      </h2>

      {/* Patterns Summary */}
      {patterns && (
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
          gap: '15px',
          marginBottom: '25px'
        }}>
          {patterns.fastest_responder && (
            <PatternCard
              label="Fastest Responder"
              value={patterns.fastest_responder}
              color="var(--accent-gold)"
            />
          )}
          {patterns.most_verbose && (
            <PatternCard
              label="Most Verbose"
              value={patterns.most_verbose}
              color="var(--accent-lavender)"
            />
          )}
        </div>
      )}

      {/* Officers Grid */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
        gap: '15px'
      }}>
        {officers.length === 0 ? (
          <div style={{
            gridColumn: '1/-1',
            textAlign: 'center',
            color: 'var(--text-muted)',
            padding: '40px'
          }}>
            No officers registered yet. Start an episode to initialize officers.
          </div>
        ) : (
          officers.map(officer => {
            const roleInfo = getRoleInfo(officer.officer_id);
            const isCaptain = officer.current_rank === 'captain';

            return (
              <div
                key={officer.officer_id}
                onClick={() => selectOfficer(officer)}
                style={{
                  padding: '20px',
                  background: selectedOfficer?.officer_id === officer.officer_id
                    ? 'linear-gradient(135deg, rgba(251,191,36,0.1), rgba(251,191,36,0.05))'
                    : 'var(--bg-card)',
                  borderRadius: '12px',
                  border: selectedOfficer?.officer_id === officer.officer_id
                    ? '2px solid var(--accent-gold)'
                    : '1px solid var(--border-color)',
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
                {/* Officer Header */}
                <div style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '12px',
                  marginBottom: '12px'
                }}>
                  <div style={{
                    width: '48px',
                    height: '48px',
                    borderRadius: '50%',
                    background: isCaptain
                      ? 'linear-gradient(135deg, var(--accent-gold), #f59e0b)'
                      : 'var(--bg-tertiary)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontSize: '11px',
                    fontWeight: '700',
                    border: isCaptain ? '2px solid var(--accent-gold)' : 'none',
                    color: isCaptain ? 'var(--bg-primary)' : 'var(--text-secondary)'
                  }}>
                    {roleInfo.icon}
                  </div>

                  <div style={{ flex: 1 }}>
                    <div style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '8px'
                    }}>
                      <span style={{
                        fontWeight: '600',
                        color: 'var(--text-primary)',
                        fontSize: '15px'
                      }}>
                        {officer.role}
                      </span>
                      {isCaptain && (
                        <span style={{
                          fontSize: '10px',
                          padding: '2px 6px',
                          background: 'var(--accent-gold)',
                          color: 'var(--bg-primary)',
                          borderRadius: '4px',
                          fontWeight: '600'
                        }}>
                          CAPTAIN
                        </span>
                      )}
                    </div>
                    <div style={{
                      fontSize: '11px',
                      color: 'var(--text-muted)',
                      marginTop: '2px'
                    }}>
                      {officer.model_name}
                    </div>
                  </div>
                </div>

                {/* Description */}
                <p style={{
                  fontSize: '12px',
                  color: 'var(--text-secondary)',
                  margin: '0 0 15px 0',
                  lineHeight: '1.5'
                }}>
                  {roleInfo.description}
                </p>

                {/* Stats */}
                <div style={{
                  display: 'flex',
                  gap: '15px',
                  paddingTop: '12px',
                  borderTop: '1px solid var(--border-color)'
                }}>
                  <div>
                    <div style={{ fontSize: '10px', color: 'var(--text-muted)' }}>Episodes</div>
                    <div style={{ fontWeight: '600', color: 'var(--accent-turquoise)' }}>
                      {officer.total_episodes || 0}
                    </div>
                  </div>
                  <div>
                    <div style={{ fontSize: '10px', color: 'var(--text-muted)' }}>As Captain</div>
                    <div style={{ fontWeight: '600', color: 'var(--accent-gold)' }}>
                      {officer.episodes_as_captain || 0}
                    </div>
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* Selected Officer Detail Panel */}
      {selectedOfficer && (
        <div style={{
          marginTop: '25px',
          padding: '25px',
          background: 'var(--bg-secondary)',
          borderRadius: '12px',
          border: '1px solid var(--border-color)'
        }}>
          <h3 style={{
            color: 'var(--accent-gold)',
            marginBottom: '20px',
            display: 'flex',
            alignItems: 'center',
            gap: '10px'
          }}>
            [{getRoleInfo(selectedOfficer.officer_id).icon}] {selectedOfficer.role} Analytics
          </h3>

          {analytics ? (
            <div style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))',
              gap: '15px'
            }}>
              <AnalyticsCard
                label="Total Actions"
                value={analytics.total_actions || 0}
              />
              <AnalyticsCard
                label="Avg Response"
                value={`${Math.round(analytics.avg_response_time_ms || 0)}ms`}
              />
              <AnalyticsCard
                label="Tokens In"
                value={analytics.total_tokens_in?.toLocaleString() || 0}
              />
              <AnalyticsCard
                label="Tokens Out"
                value={analytics.total_tokens_out?.toLocaleString() || 0}
              />
              <AnalyticsCard
                label="Fastest"
                value={`${analytics.fastest_response_ms || 0}ms`}
              />
              <AnalyticsCard
                label="Slowest"
                value={`${analytics.slowest_response_ms || 0}ms`}
              />
            </div>
          ) : (
            <div style={{ color: 'var(--text-muted)', textAlign: 'center', padding: '20px' }}>
              No analytics data available yet. Run some episodes to collect data.
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// Pattern Card Component
function PatternCard({ label, value, color }) {
  return (
    <div style={{
      padding: '15px',
      background: 'var(--bg-card)',
      borderRadius: '10px',
      border: '1px solid var(--border-color)'
    }}>
      <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginBottom: '6px' }}>{label}</div>
      <div style={{ fontWeight: '600', color, textTransform: 'capitalize' }}>
        {value.replace(/_/g, ' ')}
      </div>
    </div>
  );
}

// Analytics Card Component
function AnalyticsCard({ label, value }) {
  return (
    <div style={{
      padding: '15px',
      background: 'var(--bg-tertiary)',
      borderRadius: '8px',
      textAlign: 'center'
    }}>
      <div style={{ fontSize: '18px', fontWeight: '600', color: 'var(--text-primary)' }}>
        {value}
      </div>
      <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '4px' }}>
        {label}
      </div>
    </div>
  );
}
