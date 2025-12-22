import React, { useState, useEffect } from 'react';
import { ScoutPanel } from './components/ScoutPanel';
import { RoundtableArena } from './components/RoundtableArena';

function App() {
  const [config, setConfig] = useState(null);
  const [ws, setWs] = useState(null);
  const [isConnected, setIsConnected] = useState(false);
  const [queueStatus, setQueueStatus] = useState({ ready: 0, processing: 0 });
  const [currentIssue, setCurrentIssue] = useState(null);
  const [scoutEvents, setScoutEvents] = useState([]);
  const [scoutStatus, setScoutStatus] = useState('idle'); // idle, running, complete
  const [experiments, setExperiments] = useState({
    baseline: { status: 'idle', events: [], result: null },
    debate_light: { status: 'idle', events: [], result: null },
    debate_full: { status: 'idle', events: [], result: null },
    ensemble: { status: 'idle', events: [], result: null },
  });

  // Fetch config and queue status
  useEffect(() => {
    fetch('http://localhost:8000/api/config')
      .then(res => res.json())
      .then(data => setConfig(data))
      .catch(err => console.error('Config error:', err));

    // Initial queue fetch (WebSocket will update it)
    let abortController = new AbortController();
    let isMounted = true;
    
    const fetchQueue = () => {
      if (!isMounted) return;
      
      fetch('http://localhost:8000/api/queue', {
        signal: abortController.signal,
        headers: { 'Cache-Control': 'no-cache' },
        keepalive: false  // Don't keep connection alive
      })
        .then(res => {
          if (!isMounted) return null;
          if (!res.ok) throw new Error('Failed to fetch queue');
          return res.json();
        })
        .then(data => {
          if (!isMounted || !data) return;
          setQueueStatus({
            ready: data.stats?.ready_to_process || 0,
            processing: data.stats?.by_status?.processing || 0,
            pending: data.pending_issues || []
          });
        })
        .catch(err => {
          if (err.name !== 'AbortError' && isMounted) {
            console.error('Queue fetch error:', err);
          }
        });
    };
    
    // Fetch once on mount (WebSocket will provide updates)
    fetchQueue();
    
    return () => {
      isMounted = false;
      abortController.abort();
    };
  }, []);

  // WebSocket connection
  useEffect(() => {
    let socket = null;
    let reconnectTimeout = null;
    let isMounted = true;
    
    const connect = () => {
      if (!isMounted) return;
      
      // Close existing connection if any
      if (socket && socket.readyState === WebSocket.OPEN) {
        socket.close();
      }
      
      socket = new WebSocket('ws://localhost:8000/ws/arena');
      
      socket.onopen = () => {
        if (!isMounted) {
          socket.close();
          return;
        }
        setIsConnected(true);
        console.log('Arena WebSocket connected - auto-starting...');
      };

      socket.onmessage = (event) => {
        if (!isMounted) return;
        try {
          const data = JSON.parse(event.data);
          console.log('Arena event:', data.type, data.message);
          handleArenaEvent(data);
        } catch (err) {
          console.error('Error parsing WebSocket message:', err);
        }
      };

      socket.onclose = (event) => {
        if (!isMounted) return;
        setIsConnected(false);
        console.log('Arena WebSocket closed', event.code, event.reason);
        
        // Only reconnect if it wasn't a clean close and component is still mounted
        if (event.code !== 1000 && isMounted) {
          reconnectTimeout = setTimeout(() => {
            if (isMounted) {
              console.log('Reconnecting WebSocket...');
              connect();
            }
          }, 3000);
        }
      };

      socket.onerror = (err) => {
        console.error('WebSocket error:', err);
      };

      setWs(socket);
    };

    connect();
    
    return () => {
      isMounted = false;
      if (reconnectTimeout) {
        clearTimeout(reconnectTimeout);
      }
      if (socket) {
        socket.close(1000, 'Component unmounting');
      }
    };
  }, []);

  const handleArenaEvent = (event) => {
    const { mode, type, source, ...rest } = event;

    // Handle discovery events
    if (source === 'discovery') {
      if (type === 'discovery_start') {
        setScoutStatus('running');
        setScoutEvents([event]);
      } else if (type === 'discovery_complete') {
        setScoutStatus('complete');
        setScoutEvents(prev => [...prev, event]);
        // Refresh queue after discovery completes
        fetch('http://localhost:8000/api/queue')
          .then(res => res.json())
          .then(data => {
            setQueueStatus({
              ready: data.stats?.ready_to_process || 0,
              processing: data.stats?.by_status?.processing || 0,
              pending: data.pending_issues || []
            });
          })
          .catch(err => console.error('Queue fetch error:', err));
      } else if (type === 'error' && source === 'discovery') {
        setScoutStatus('idle');
        setScoutEvents(prev => [...prev, event]);
      } else {
        // Other discovery events (language_start, repos_found, issue_scored, etc.)
        setScoutEvents(prev => [...prev.slice(-9), event]); // Keep last 10 events
      }
      return; // Don't process discovery events as arena events
    }

    // Update queue status from WebSocket events
    if (event.data?.queue_stats) {
      const stats = event.data.queue_stats;
      setQueueStatus(prev => ({
        ...prev,
        ready: stats.ready_to_process || 0,
        processing: stats.by_status?.processing || 0,
        pending: prev.pending || []
      }));
    }

    // Handle global arena events
    if (type === 'arena_connected') {
      console.log('Arena connected and starting...');
      // Set all experiments to running when arena starts
      setExperiments(prev => {
        const updated = {};
        for (const mode in prev) {
          updated[mode] = { ...prev[mode], status: 'running' };
        }
        return updated;
      });
    } else if (type === 'arena_start') {
      console.log('Arena starting new round...');
    } else if (type === 'queue_empty') {
      console.log('Queue empty - waiting for issues...');
      // Show queue empty message in all experiments
      setExperiments(prev => {
        const updated = {};
        for (const mode in prev) {
          updated[mode] = {
            ...prev[mode],
            status: 'idle',
            events: [...prev[mode].events.slice(-1), {
              type: 'queue_empty',
              message: 'Queue empty. Run Scout to discover issues.',
              timestamp: Date.now()
            }]
          };
        }
        return updated;
      });
    } else if (type === 'issue_selected') {
      setCurrentIssue(event.data?.issue);
      console.log('Issue selected:', event.data?.issue?.title);
      // Reset all experiments for new issue
      setExperiments(prev => {
        const updated = {};
        for (const mode in prev) {
          updated[mode] = {
            status: 'running',
            events: [],
            result: null
          };
        }
        return updated;
      });
    } else if (type === 'arena_complete') {
      console.log('Arena round complete');
    } else if (type === 'arena_pause') {
      console.log('Arena pausing before next round...');
    }

    // Handle mode-specific events
    if (mode && experiments[mode]) {
      setExperiments(prev => ({
        ...prev,
        [mode]: {
          ...prev[mode],
          status: type === 'complete' || type === 'roundtable_complete' || type === 'mode_complete' ? 'complete' : 'running',
          events: [...prev[mode].events.slice(-20), { type, ...rest, timestamp: Date.now() }],
          result: (type === 'complete' || type === 'roundtable_complete') ? event.data : prev[mode].result
        }
      }));
    }
  };

  const triggerDiscovery = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/discovery/run-now', { 
        method: 'POST' 
      });
      const data = await response.json();
      console.log('Discovery started:', data.message);
      // Status will be updated via WebSocket events
    } catch (err) {
      console.error('Failed to start discovery:', err);
    }
  };

  return (
    <div className="app">
      {/* Header */}
      <header className="header">
        <div className="header-left">
          <h1 className="logo">
            <span className="logo-bracket">[</span>
            AI Village
            <span className="logo-bracket">]</span>
          </h1>
          <p className="tagline">Multi-Agent Research Arena</p>
        </div>
        
        <div className="header-center">
          <div className={`connection-status ${isConnected ? 'connected' : 'disconnected'}`}>
            <span className="status-dot"></span>
            {isConnected ? 'Arena Active' : 'Connecting...'}
          </div>
        </div>

        <div className="header-right">
          <div className="queue-status">
            <span className="queue-label">Queue:</span>
            <span className="queue-count">{queueStatus.ready} ready</span>
          </div>
          <button className="scout-trigger" onClick={triggerDiscovery}>
            Run Scout Now
          </button>
        </div>
      </header>

      {/* Main content - 2 columns */}
      <main className="main-layout">
        <aside className="scout-sidebar">
          <ScoutPanel 
            queueStatus={queueStatus}
            currentIssue={currentIssue}
            events={scoutEvents}
            status={scoutStatus}
          />
        </aside>
        
        <section className="arena-section">
          <RoundtableArena 
            experiments={experiments}
            currentIssue={currentIssue}
          />
        </section>
      </main>

      <style>{`
        .app {
          min-height: 100vh;
          display: flex;
          flex-direction: column;
          background: var(--bg-primary);
        }

        /* Header */
        .header {
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 12px 24px;
          background: var(--bg-secondary);
          border-bottom: 1px solid var(--border-color);
        }

        .header-left {
          display: flex;
          flex-direction: column;
        }

        .logo {
          font-size: 22px;
          font-weight: 700;
          margin: 0;
        }

        .logo-bracket {
          color: var(--accent-gold);
        }

        .tagline {
          font-size: 12px;
          color: var(--text-muted);
          margin: 0;
        }

        .header-center {
          display: flex;
          align-items: center;
        }

        .connection-status {
          display: flex;
          align-items: center;
          gap: 8px;
          font-size: 13px;
          color: var(--text-muted);
        }

        .status-dot {
          width: 8px;
          height: 8px;
          border-radius: 50%;
          background: var(--text-muted);
        }

        .connection-status.connected .status-dot {
          background: var(--accent-turquoise);
          box-shadow: 0 0 8px var(--accent-turquoise);
          animation: pulse 2s infinite;
        }

        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.5; }
        }

        .header-right {
          display: flex;
          align-items: center;
          gap: 16px;
        }

        .queue-status {
          font-size: 13px;
          color: var(--text-secondary);
        }

        .queue-label {
          color: var(--text-muted);
          margin-right: 4px;
        }

        .queue-count {
          color: var(--accent-gold);
          font-weight: 600;
        }

        .scout-trigger {
          padding: 8px 16px;
          background: var(--bg-tertiary);
          border: 1px solid var(--border-color);
          border-radius: 6px;
          color: var(--text-secondary);
          font-size: 13px;
          cursor: pointer;
          transition: all 0.2s;
        }

        .scout-trigger:hover {
          background: var(--bg-primary);
          border-color: var(--accent-lavender);
          color: var(--accent-lavender);
        }

        /* Main Layout */
        .main-layout {
          flex: 1;
          display: grid;
          grid-template-columns: 280px 1fr;
          gap: 0;
          min-height: 0;
        }

        .scout-sidebar {
          background: var(--bg-secondary);
          border-right: 1px solid var(--border-color);
          overflow-y: auto;
        }

        .arena-section {
          overflow: hidden;
          padding: 16px;
        }
      `}</style>
    </div>
  );
}

export default App;
