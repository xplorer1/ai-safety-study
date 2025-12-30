import React, { useState, useEffect } from 'react';

export function CaptainsLog() {
  const [episodes, setEpisodes] = useState([]);
  const [selectedEpisode, setSelectedEpisode] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchEpisodes();
  }, []);

  const fetchEpisodes = async () => {
    try {
      const res = await fetch('http://localhost:8000/api/episodes?limit=20');
      const data = await res.json();
      const completed = (data.episodes || []).filter(e => e.status === 'completed' && e.captains_log);
      setEpisodes(completed);
      if (completed.length > 0 && !selectedEpisode) {
        setSelectedEpisode(completed[0]);
      }
    } catch (err) {
      console.error('Error fetching episodes:', err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div style={{ padding: '20px', color: 'var(--text-muted)' }}>Loading...</div>;
  }

  return (
    <div style={{ padding: '20px', display: 'flex', gap: '20px', height: '100%' }}>
      <div style={{ width: '300px', background: 'var(--bg-secondary)', borderRadius: '8px', padding: '20px' }}>
        <h3 style={{ color: 'var(--accent-gold)', marginBottom: '15px' }}>Episode Logs</h3>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
          {episodes.map(episode => (
            <div
              key={episode.id}
              onClick={() => setSelectedEpisode(episode)}
              style={{
                padding: '10px',
                background: selectedEpisode?.id === episode.id ? 'var(--bg-tertiary)' : 'var(--bg-card)',
                borderRadius: '6px',
                cursor: 'pointer',
                border: selectedEpisode?.id === episode.id ? '1px solid var(--accent-gold)' : '1px solid var(--border-color)'
              }}
            >
              <div style={{ fontWeight: '600', color: 'var(--accent-turquoise)' }}>
                Episode {episode.episode_number}
              </div>
              <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                {episode.outcome}
              </div>
            </div>
          ))}
        </div>
      </div>

      <div style={{ flex: 1, background: 'var(--bg-secondary)', borderRadius: '8px', padding: '20px' }}>
        {selectedEpisode ? (
          <div>
            <h2 style={{ color: 'var(--accent-gold)', marginBottom: '15px' }}>
              Captain's Log - Episode {selectedEpisode.episode_number}
            </h2>
            <div style={{
              color: 'var(--text-secondary)',
              lineHeight: '1.8',
              whiteSpace: 'pre-wrap',
              fontFamily: 'var(--font-mono)',
              fontSize: '14px'
            }}>
              {selectedEpisode.captains_log}
            </div>
          </div>
        ) : (
          <div style={{ color: 'var(--text-muted)', textAlign: 'center', padding: '40px' }}>
            Select an episode to view the log
          </div>
        )}
      </div>
    </div>
  );
}

