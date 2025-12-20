import React, { useState } from 'react';

export function ResultsPanel({ winningFix, status }) {
  const [reviewStatus, setReviewStatus] = useState('pending');
  const [editedCode, setEditedCode] = useState('');
  const [isEditing, setIsEditing] = useState(false);

  const handleApprove = () => {
    setReviewStatus('approved');
  };

  const handleReject = () => {
    setReviewStatus('rejected');
  };

  const handleEdit = () => {
    setEditedCode(winningFix?.fix || '');
    setIsEditing(true);
  };

  const handleSaveEdit = () => {
    setReviewStatus('edited');
    setIsEditing(false);
  };

  return (
    <div className="panel results-panel">
      <div className="panel-header">
        <div className="panel-title">
          <span className="panel-icon">{'{}'}</span>
          Winning Fix
        </div>
        {reviewStatus !== 'pending' && (
          <div className={`status-pill ${reviewStatus}`}>
            {reviewStatus}
          </div>
        )}
      </div>

      <div className="panel-content">
        {!winningFix && (
          <div className="placeholder-content">
            <div className="placeholder-icon">
              <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                <path d="M9 12l2 2 4-4" />
                <circle cx="12" cy="12" r="10" />
              </svg>
            </div>
            <div className="placeholder-title">Awaiting Consensus</div>
            <div className="placeholder-text">
              The winning fix will appear here after the roundtable votes.
            </div>
            <div className="review-preview">
              <div className="preview-item">
                <span className="check-icon">+</span>
                Approve to submit PR
              </div>
              <div className="preview-item">
                <span className="edit-icon">/</span>
                Edit before submitting
              </div>
              <div className="preview-item">
                <span className="reject-icon">x</span>
                Reject and restart
              </div>
            </div>
          </div>
        )}

        {winningFix && (
          <>
            {/* Winner card */}
            <div 
              className="winner-card"
              style={{ '--winner-color': winningFix.winner_color }}
            >
              <div className="winner-label">WINNER</div>
              <div className="winner-name">{winningFix.winner_name}</div>
              <div className="winner-style">{winningFix.winner_style} approach</div>
              <div className="vote-count">{winningFix.vote_count} vote(s)</div>
            </div>

            {/* Vote breakdown */}
            <div className="votes-section">
              <div className="section-title">Vote Breakdown</div>
              {Object.entries(winningFix.votes || {}).map(([voter, votedFor]) => (
                <div key={voter} className="vote-row">
                  <span className="voter">{voter}</span>
                  <span className="arrow">→</span>
                  <span className="voted-for">{votedFor}</span>
                </div>
              ))}
            </div>

            {/* Code section */}
            <div className="code-section">
              <div className="section-title">Proposed Fix</div>
              {isEditing ? (
                <textarea
                  className="code-editor"
                  value={editedCode}
                  onChange={(e) => setEditedCode(e.target.value)}
                  rows={10}
                />
              ) : (
                <pre className="code-display">
                  <code>{editedCode || winningFix.fix}</code>
                </pre>
              )}
            </div>

            {/* Review actions */}
            <div className="review-section">
              <div className="section-title">Human Review</div>
              
              {reviewStatus === 'pending' && !isEditing && (
                <div className="action-buttons">
                  <button className="btn approve" onClick={handleApprove}>
                    Approve
                  </button>
                  <button className="btn edit" onClick={handleEdit}>
                    Edit
                  </button>
                  <button className="btn reject" onClick={handleReject}>
                    Reject
                  </button>
                </div>
              )}

              {isEditing && (
                <div className="action-buttons">
                  <button className="btn approve" onClick={handleSaveEdit}>
                    Save Changes
                  </button>
                  <button className="btn secondary" onClick={() => setIsEditing(false)}>
                    Cancel
                  </button>
                </div>
              )}

              {reviewStatus === 'approved' && (
                <div className="approval-message">
                  <div className="approval-icon">✓</div>
                  <div>Fix approved! Ready for PR submission.</div>
                  <button className="btn submit-pr">
                    Submit PR to GitHub
                  </button>
                </div>
              )}

              {reviewStatus === 'rejected' && (
                <div className="rejection-message">
                  Fix rejected. Run the pipeline again with different parameters.
                </div>
              )}

              {reviewStatus === 'edited' && (
                <div className="edited-message">
                  <div className="approval-icon">✓</div>
                  <div>Changes saved! Ready for PR submission.</div>
                  <button className="btn submit-pr">
                    Submit PR to GitHub
                  </button>
                </div>
              )}
            </div>
          </>
        )}
      </div>

      <style>{`
        .results-panel {
          display: flex;
          flex-direction: column;
        }

        .panel-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 16px 20px;
          border-bottom: 1px solid var(--border-color);
          background: var(--bg-tertiary);
        }

        .panel-title {
          font-size: 18px;
          font-weight: 600;
          display: flex;
          align-items: center;
          gap: 8px;
        }

        .panel-icon {
          font-family: var(--font-mono);
          color: var(--accent-coral);
        }

        .status-pill {
          font-size: 11px;
          padding: 4px 10px;
          border-radius: 20px;
          text-transform: uppercase;
          font-weight: 600;
        }

        .status-pill.approved, .status-pill.edited {
          background: color-mix(in srgb, var(--accent-turquoise) 20%, transparent);
          color: var(--accent-turquoise);
        }

        .status-pill.rejected {
          background: color-mix(in srgb, var(--accent-coral) 20%, transparent);
          color: var(--accent-coral);
        }

        .panel-content {
          flex: 1;
          overflow-y: auto;
          padding: 16px 20px;
        }

        .placeholder-content {
          text-align: center;
          padding: 30px 20px;
        }

        .placeholder-icon {
          color: var(--text-muted);
          margin-bottom: 16px;
        }

        .placeholder-title {
          font-size: 16px;
          font-weight: 500;
          color: var(--text-secondary);
          margin-bottom: 8px;
        }

        .placeholder-text {
          font-size: 13px;
          color: var(--text-muted);
          margin-bottom: 24px;
        }

        .review-preview {
          display: flex;
          flex-direction: column;
          gap: 8px;
          max-width: 200px;
          margin: 0 auto;
        }

        .preview-item {
          display: flex;
          align-items: center;
          gap: 10px;
          font-size: 13px;
          color: var(--text-secondary);
          text-align: left;
        }

        .check-icon { color: var(--accent-turquoise); }
        .edit-icon { color: var(--accent-gold); }
        .reject-icon { color: var(--accent-coral); }

        .winner-card {
          padding: 20px;
          background: color-mix(in srgb, var(--winner-color) 10%, var(--bg-secondary));
          border: 1px solid color-mix(in srgb, var(--winner-color) 40%, transparent);
          border-radius: 12px;
          text-align: center;
          margin-bottom: 20px;
        }

        .winner-label {
          font-size: 10px;
          letter-spacing: 2px;
          color: var(--winner-color);
          margin-bottom: 8px;
        }

        .winner-name {
          font-size: 18px;
          font-weight: 600;
          color: var(--winner-color);
          margin-bottom: 4px;
        }

        .winner-style {
          font-size: 13px;
          color: var(--text-muted);
          margin-bottom: 8px;
        }

        .vote-count {
          font-size: 14px;
          color: var(--text-secondary);
        }

        .section-title {
          font-size: 12px;
          text-transform: uppercase;
          color: var(--text-muted);
          margin-bottom: 12px;
          font-weight: 600;
          letter-spacing: 0.5px;
        }

        .votes-section {
          margin-bottom: 20px;
        }

        .vote-row {
          display: flex;
          align-items: center;
          gap: 8px;
          padding: 8px 0;
          font-size: 13px;
          border-bottom: 1px solid var(--border-color);
        }

        .voter {
          color: var(--text-secondary);
        }

        .arrow {
          color: var(--text-muted);
        }

        .voted-for {
          color: var(--accent-gold);
        }

        .code-section {
          margin-bottom: 20px;
        }

        .code-display {
          padding: 16px;
          background: var(--bg-primary);
          border: 1px solid var(--border-color);
          border-radius: 8px;
          overflow-x: auto;
          font-family: var(--font-mono);
          font-size: 12px;
          line-height: 1.6;
          max-height: 200px;
        }

        .code-editor {
          width: 100%;
          padding: 16px;
          background: var(--bg-primary);
          border: 1px solid var(--accent-gold);
          border-radius: 8px;
          font-family: var(--font-mono);
          font-size: 12px;
          line-height: 1.6;
          color: var(--text-primary);
          resize: vertical;
        }

        .review-section {
          border-top: 1px solid var(--border-color);
          padding-top: 20px;
        }

        .action-buttons {
          display: flex;
          gap: 10px;
        }

        .btn {
          flex: 1;
          padding: 12px 16px;
          border: none;
          border-radius: 8px;
          font-size: 13px;
          font-weight: 600;
          cursor: pointer;
          transition: all 0.2s;
          font-family: var(--font-sans);
        }

        .btn.approve {
          background: var(--accent-turquoise);
          color: var(--bg-primary);
        }

        .btn.edit {
          background: var(--accent-gold);
          color: var(--bg-primary);
        }

        .btn.reject {
          background: transparent;
          border: 1px solid var(--accent-coral);
          color: var(--accent-coral);
        }

        .btn.secondary {
          background: var(--bg-tertiary);
          color: var(--text-secondary);
        }

        .btn.submit-pr {
          background: var(--accent-lavender);
          color: var(--bg-primary);
          margin-top: 12px;
          width: 100%;
        }

        .btn:hover {
          opacity: 0.9;
          transform: translateY(-1px);
        }

        .approval-message, .edited-message {
          text-align: center;
          padding: 20px;
          background: color-mix(in srgb, var(--accent-turquoise) 10%, transparent);
          border-radius: 8px;
          color: var(--accent-turquoise);
        }

        .approval-icon {
          font-size: 24px;
          margin-bottom: 8px;
        }

        .rejection-message {
          text-align: center;
          padding: 20px;
          background: color-mix(in srgb, var(--accent-coral) 10%, transparent);
          border-radius: 8px;
          color: var(--accent-coral);
        }
      `}</style>
    </div>
  );
}

