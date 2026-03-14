import React, { useRef, useEffect, useState } from 'react';

  /**
   * noVNC panel for streaming the desktop.
   * Dynamically imports noVNC to avoid top-level await build issues.
   */
  export default function NoVNCPanel({ visible, novncUrl }) {
    const containerRef = useRef(null);
    const rfbRef = useRef(null);
    const [connected, setConnected] = useState(false);
    const [loadError, setLoadError] = useState(false);

    useEffect(() => {
      if (!containerRef.current || !novncUrl) return;

      let cancelled = false;

      (async () => {
      try {
        // Dynamic import — noVNC uses top-level await which breaks static imports
        const RFBModule = await import(/* @vite-ignore */ '@novnc/novnc/lib/rfb.js');
        const RFB = RFBModule.default;
        if (cancelled) return;

        const rfb = new RFB(containerRef.current, novncUrl, {
          wsProtocols: ['binary'],
        });

        rfb.viewOnly = false;
        rfb.scaleViewport = true;
        rfb.resizeSession = false;
        rfb.showDotCursor = true;

        rfb.addEventListener('connect', () => {
          if (!cancelled) setConnected(true);
        });

        rfb.addEventListener('disconnect', () => {
          if (!cancelled) setConnected(false);
        });

        rfbRef.current = rfb;
      } catch (err) {
        console.error('noVNC error:', err);
        if (!cancelled) setLoadError(true);
      }
      })();

      return () => {
        cancelled = true;
        if (rfbRef.current) {
          try {
            rfbRef.current.disconnect();
          } catch (e) {
            console.error('Error disconnecting:', e);
          }
          rfbRef.current = null;
        }
      };
    }, [novncUrl]);

    return (
      <div
        className="novnc-panel"
        style={{ display: visible ? 'block' : 'none' }}
      >
        <div ref={containerRef} className="novnc-container">
          {!connected && (
            <div className="novnc-connecting">
              {loadError ? 'Desktop viewer unavailable (no VNC server)' : 'Connecting to desktop...'}
            </div>
          )}
        </div>
      </div>
    );
  }
