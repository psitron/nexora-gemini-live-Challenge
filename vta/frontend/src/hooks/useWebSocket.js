import { useState, useEffect, useRef, useCallback } from 'react';

/**
 * WebSocket hook for communicating with the VTA Orchestrator.
 *
 * Handles connection lifecycle, message routing, and reconnection.
 */
export default function useWebSocket(url) {
  const [isConnected, setIsConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState(null);
  const wsRef = useRef(null);
  const handlersRef = useRef({});
  const reconnectTimerRef = useRef(null);

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => {
      setIsConnected(true);
      console.log('WebSocket connected');
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        setLastMessage(data);

        // Route to registered event handlers
        const eventType = data.event;
        if (eventType && handlersRef.current[eventType]) {
          handlersRef.current[eventType](data);
        }

        // Also fire the global handler
        if (handlersRef.current['*']) {
          handlersRef.current['*'](data);
        }
      } catch (e) {
        console.error('WebSocket message parse error:', e);
      }
    };

    ws.onclose = () => {
      setIsConnected(false);
      console.log('WebSocket disconnected');
      // Auto-reconnect after 3 seconds
      reconnectTimerRef.current = setTimeout(connect, 3000);
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };
  }, [url]);

  useEffect(() => {
    connect();
    return () => {
      clearTimeout(reconnectTimerRef.current);
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [connect]);

  const send = useCallback((data) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(data));
    }
  }, []);

  const on = useCallback((eventType, handler) => {
    handlersRef.current[eventType] = handler;
  }, []);

  const off = useCallback((eventType) => {
    delete handlersRef.current[eventType];
  }, []);

  return { isConnected, lastMessage, send, on, off };
}
