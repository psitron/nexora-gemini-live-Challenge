import React, { useRef, useEffect, useState } from 'react';

  /**
   * noVNC panel — shows the desktop viewer.
   * Uses iframe when same protocol, or a link to open in new tab.
   */
  export default function NoVNCPanel({ visible, novncUrl }) {
    const [noVncWebUrl, setNoVncWebUrl] = useState('');
    const [iframeError, setIframeError] = useState(false);
    const isHttps = window.location.protocol === 'https:';

    useEffect(() => {
      const host = window.location.hostname;
      setNoVncWebUrl(`http://${host}:6080/vnc.html?autoconnect=true&resize=scale`);
    }, []);

    if (!visible) return null;

    // On HTTPS, iframe can't load HTTP content — show link instead
    if (isHttps || iframeError) {
      return (
        <div className="novnc-panel" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%' }}>
          <div style={{ textAlign: 'center', padding: '40px' }}>
            <p style={{ color: '#cbd5e1', fontSize: '16px', marginBottom: '16px' }}>
              Desktop viewer opens in a separate window
            </p>
            <a
              href={noVncWebUrl}
              target="_blank"
              rel="noopener noreferrer"
              style={{
                display: 'inline-block',
                padding: '12px 32px',
                background: '#6366f1',
                color: 'white',
                borderRadius: '8px',
                textDecoration: 'none',
                fontSize: '16px',
                fontWeight: '600',
              }}
            >
              Open Desktop Viewer
            </a>
            <p style={{ color: '#64748b', fontSize: '13px', marginTop: '12px' }}>
              Tip: Place this window side-by-side with the desktop viewer
            </p>
          </div>
        </div>
      );
    }

    return (
      <div className="novnc-panel">
        <iframe
          src={noVncWebUrl}
          className="novnc-iframe"
          title="Desktop View"
          allow="clipboard-read; clipboard-write"
          onError={() => setIframeError(true)}
        />
      </div>
    );
  }
