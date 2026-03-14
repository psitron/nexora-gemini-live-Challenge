import { useRef, useEffect, useCallback } from 'react';

/**
 * noVNC hook for embedding a VNC client.
 *
 * The VNC connection stays open the entire session even when the panel
 * is hidden (CSS display:none). This ensures instant panel switching.
 */
export default function useNoVNC(containerRef, wsUrl) {
  const rfbRef = useRef(null);
  const isConnectedRef = useRef(false);

  const connect = useCallback(async () => {
    if (isConnectedRef.current || !containerRef.current) return;

    try {
      // Dynamic import of noVNC
      const { default: RFB } = await import('@novnc/novnc/core/rfb');

      const rfb = new RFB(containerRef.current, wsUrl, {
        wsProtocols: ['binary'],
      });

      rfb.viewOnly = true; // Students observe, Agent S3 controls
      rfb.scaleViewport = true;
      rfb.resizeSession = false;
      rfb.showDotCursor = true;

      rfb.addEventListener('connect', () => {
        isConnectedRef.current = true;
        console.log('noVNC connected');
      });

      rfb.addEventListener('disconnect', (e) => {
        isConnectedRef.current = false;
        console.log('noVNC disconnected:', e.detail);
        // Auto-reconnect after 3 seconds
        setTimeout(connect, 3000);
      });

      rfbRef.current = rfb;
    } catch (err) {
      console.error('noVNC connection error:', err);
      // Retry
      setTimeout(connect, 3000);
    }
  }, [containerRef, wsUrl]);

  const disconnect = useCallback(() => {
    if (rfbRef.current) {
      rfbRef.current.disconnect();
      rfbRef.current = null;
      isConnectedRef.current = false;
    }
  }, []);

  useEffect(() => {
    connect();
    return () => disconnect();
  }, [connect, disconnect]);

  return { isConnected: isConnectedRef.current, disconnect };
}
