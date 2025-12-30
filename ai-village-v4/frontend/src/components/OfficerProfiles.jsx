import React, { useState, useEffect } from 'react';

export function OfficerProfiles() {
  const [officers, setOfficers] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchOfficers();
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

  if (loading) {
    return <div style={{ padding: '20px', color: 'var(--text-muted)' }}>Loading...</div>;
  }

  return (
    <div style={{ padding: '20px' }}>
      <h2 style={{ color: 'var(--accent-gold)', marginBottom: '20px' }}>Officer Profiles</h2>
      
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: '20px' }}>
        {officers.map(officer => (
          <div
            key={officer.officer_id}
            style={{
              padding: '20px',
              background: 'var(--bg-secondary)',
              borderRadius: '8px',
              border: '1px solid var(--border-color)'
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '10px' }}>
              <h3 style={{ color: 'var(--accent-turquoise)' }}>{officer.role}</h3>
              {officer.current_rank === 'captain' && (
                <span style={{
                  padding: '4px 8px',
                  background: 'var(--accent-gold)',
                  borderRadius: '4px',
                  fontSize: '12px',
                  color: 'var(--bg-primary)'
                }}>
                  CAPTAIN
                </span>
              )}
            </div>
            <div style={{ color: 'var(--text-secondary)', marginBottom: '10px' }}>
              <div>Model: {officer.model_name}</div>
              <div>Episodes: {officer.total_episodes}</div>
              {officer.episodes_as_captain > 0 && (
                <div>As Captain: {officer.episodes_as_captain}</div>
              )}
            </div>
            {officer.performance_metrics && (
              <div style={{ fontSize: '14px', color: 'var(--text-muted)' }}>
                Performance metrics available
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

