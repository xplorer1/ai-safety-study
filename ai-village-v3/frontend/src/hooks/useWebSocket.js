import { useState, useCallback, useRef, useEffect } from 'react';

/**
 * Custom hook for WebSocket connection with auto-reconnect.
 */
export function useWebSocket(url) {
  const [isConnected, setIsConnected] = useState(false);
  const [events, setEvents] = useState([]);
  const [status, setStatus] = useState('disconnected'); // disconnected, connecting, connected, running
  const wsRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);

  // Derived state
  const [scoutEvents, setScoutEvents] = useState([]);
  const [roundtableEvents, setRoundtableEvents] = useState([]);
  const [selectedIssue, setSelectedIssue] = useState(null);
  const [winningFix, setWinningFix] = useState(null);

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    setStatus('connecting');
    const ws = new WebSocket(url);

    ws.onopen = () => {
      setIsConnected(true);
      setStatus('connected');
      console.log('WebSocket connected');
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        
        // Add to events list
        setEvents(prev => [...prev, { ...data, timestamp: Date.now() }]);

        // Route event to appropriate state
        if (data.agent === 'scout') {
          setScoutEvents(prev => [...prev, data]);
          if (data.type === 'agent_complete' && data.data?.issue) {
            setSelectedIssue(data.data.issue);
          }
        } else if (['conservative', 'innovative', 'quality', 'roundtable'].includes(data.agent)) {
          // For roundtable events: remove "thinking" event when real content arrives
          setRoundtableEvents(prev => {
            // If this is a substantive event (not thinking), remove the thinking event for this agent
            if (data.type !== 'thinking' && data.type !== 'round_start') {
              const filtered = prev.filter(e => !(e.type === 'thinking' && e.agent === data.agent));
              return [...filtered, data];
            }
            return [...prev, data];
          });
          
          if (data.type === 'roundtable_complete') {
            setWinningFix(data.data);
          }
        }

        // Update status based on event type
        if (data.type === 'pipeline_start') {
          setStatus('running');
        } else if (data.type === 'pipeline_complete') {
          setStatus('connected');
        }
      } catch (e) {
        console.error('Failed to parse WebSocket message:', e);
      }
    };

    ws.onclose = () => {
      setIsConnected(false);
      setStatus('disconnected');
      console.log('WebSocket disconnected');
      
      // Auto-reconnect after 3 seconds
      reconnectTimeoutRef.current = setTimeout(() => {
        connect();
      }, 3000);
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };

    wsRef.current = ws;
  }, [url]);

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
  }, []);

  const startPipeline = useCallback((repo = 'pandas-dev/pandas') => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      // Clear previous state
      setEvents([]);
      setScoutEvents([]);
      setRoundtableEvents([]);
      setSelectedIssue(null);
      setWinningFix(null);
      
      // Send start command
      wsRef.current.send(JSON.stringify({ action: 'start', repo }));
    }
  }, []);

  // Connect on mount
  useEffect(() => {
    connect();
    return () => disconnect();
  }, [connect, disconnect]);

  return {
    isConnected,
    status,
    events,
    scoutEvents,
    roundtableEvents,
    selectedIssue,
    winningFix,
    startPipeline,
    connect,
    disconnect
  };
}

