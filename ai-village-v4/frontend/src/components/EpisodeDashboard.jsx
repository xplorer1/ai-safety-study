import React, { useState, useEffect } from 'react';

export function EpisodeDashboard() {
  const [episodes, setEpisodes] = useState([]);
  const [currentEpisode, setCurrentEpisode] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchEpisodes();
    fetchCurrentEpisode();
  }, []);

  const fetchEpisodes = async () => {
    try {
      const res = await fetch('http://localhost:8000/api/episodes?limit=10');
      const data = await res.json();
      setEpisodes(data.episodes || []);
    } catch (err) {
      console.error('Error fetching episodes:', err);
    } finally {
      setLoading(false);
    }
  };

  const fetchCurrentEpisode = async () => {
    try {
      const res = await fetch('http://localhost:8000/api/episodes/current');
      const data = await res.json();
      setCurrentEpisode(data.episode);
    } catch (err) {
      console.error('Error fetching current episode:', err);
    }
  };

  if (loading) {
    return <div style={{ padding: '20px', color: 'var(--text-muted)' }}>Loading...</div>;
  }

  return (
    <div style={{ padding: '20px' }}>
      <h2 style={{ color: 'var(--accent-gold)', marginBottom: '20px' }}>Episode Dashboard</h2>

      {currentEpisode && (
        <div style={{
          marginBottom: '30px',
          padding: '20px',
          background: 'var(--bg-secondary)',
          borderRadius: '8px',
          border: '1px solid var(--border-color)'
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '10px' }}>
            <h3 style={{ color: 'var(--accent-turquoise)' }}>
              Episode {currentEpisode.episode_number} - {currentEpisode.status}
            </h3>
            <span style={{
              padding: '4px 12px',
              background: currentEpisode.status === 'completed' ? 'var(--accent-turquoise)' : 'var(--accent-gold)',
              borderRadius: '12px',
              fontSize: '12px',
              color: 'var(--bg-primary)'
            }}>
              {currentEpisode.status}
            </span>
          </div>
          <div style={{ color: 'var(--text-secondary)', marginBottom: '10px' }}>
            <strong>Scenario:</strong> {currentEpisode.scenario?.substring(0, 200)}...
          </div>
          {currentEpisode.outcome && (
            <div style={{ color: 'var(--text-secondary)' }}>
              <strong>Outcome:</strong> {currentEpisode.outcome}
            </div>
          )}
        </div>
      )}

      <div>
        <h3 style={{ color: 'var(--text-primary)', marginBottom: '15px' }}>Recent Episodes</h3>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
          {episodes.map(episode => (
            <div
              key={episode.id}
              style={{
                padding: '15px',
                background: 'var(--bg-card)',
                borderRadius: '6px',
                border: '1px solid var(--border-color)',
                cursor: 'pointer'
              }}
              onClick={() => setCurrentEpisode(episode)}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                <span style={{ fontWeight: '600', color: 'var(--accent-gold)' }}>
                  Episode {episode.episode_number}
                </span>
                <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                  {episode.status}
                </span>
              </div>
              <div style={{ fontSize: '14px', color: 'var(--text-secondary)' }}>
                {episode.scenario?.substring(0, 150)}...
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

