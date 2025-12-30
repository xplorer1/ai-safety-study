import React, { useState } from 'react';

export function VotingPanel({ episodeId, onVote }) {
  const [voterId, setVoterId] = useState('');
  const [selectedDecision, setSelectedDecision] = useState('');

  const handleVote = async () => {
    if (!voterId || !selectedDecision) {
      alert('Please enter your ID and select a decision');
      return;
    }

    try {
      const res = await fetch('http://localhost:8000/api/voting/decision', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          episode_id: episodeId,
          voter_id: voterId,
          decision: selectedDecision
        })
      });

      const data = await res.json();
      if (data.success) {
        alert('Vote submitted!');
        if (onVote) onVote();
      }
    } catch (err) {
      console.error('Error submitting vote:', err);
      alert('Error submitting vote');
    }
  };

  return (
    <div style={{
      padding: '20px',
      background: 'var(--bg-secondary)',
      borderRadius: '8px',
      border: '1px solid var(--border-color)'
    }}>
      <h3 style={{ color: 'var(--accent-gold)', marginBottom: '15px' }}>Vote on Decision</h3>
      
      <div style={{ marginBottom: '15px' }}>
        <label style={{ display: 'block', marginBottom: '5px', color: 'var(--text-secondary)' }}>
          Your ID:
        </label>
        <input
          type="text"
          value={voterId}
          onChange={(e) => setVoterId(e.target.value)}
          placeholder="Enter your identifier"
          style={{
            width: '100%',
            padding: '8px',
            background: 'var(--bg-tertiary)',
            border: '1px solid var(--border-color)',
            borderRadius: '4px',
            color: 'var(--text-primary)'
          }}
        />
      </div>

      <div style={{ marginBottom: '15px' }}>
        <label style={{ display: 'block', marginBottom: '5px', color: 'var(--text-secondary)' }}>
          Decision:
        </label>
        <select
          value={selectedDecision}
          onChange={(e) => setSelectedDecision(e.target.value)}
          style={{
            width: '100%',
            padding: '8px',
            background: 'var(--bg-tertiary)',
            border: '1px solid var(--border-color)',
            borderRadius: '4px',
            color: 'var(--text-primary)'
          }}
        >
          <option value="">Select decision</option>
          <option value="approve">Approve</option>
          <option value="reject">Reject</option>
          <option value="modify">Modify</option>
        </select>
      </div>

      <button
        onClick={handleVote}
        style={{
          width: '100%',
          padding: '10px',
          background: 'var(--accent-gold)',
          border: 'none',
          borderRadius: '6px',
          color: 'var(--bg-primary)',
          fontWeight: '600',
          cursor: 'pointer'
        }}
      >
        Submit Vote
      </button>
    </div>
  );
}

