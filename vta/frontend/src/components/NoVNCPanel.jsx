import React, { useEffect, useState } from 'react';

  /**
   * noVNC panel — embeds the desktop viewer via iframe.
   * Uses nginx reverse proxy so everything is same-origin HTTPS.
   * noVNC is served at /vnc/ path through nginx proxy.
   */
  export default function NoVNCPanel({ visible }) {
    const [noVncWebUrl, setNoVncWebUrl] = useState('');

    useEffect(() => {
      // Use same origin — nginx proxies /vnc/ to websockify port 6080
      const origin = window.location.origin;
      setNoVncWebUrl(`${origin}/vnc/vnc.html?autoconnect=true&resize=scale&view_only=true&path=websockify`);
    }, []);

    if (!visible) return null;

    return (
      <div className="novnc-panel">
        {noVncWebUrl ? (
          <iframe
            src={noVncWebUrl}
            className="novnc-iframe"
            title="Desktop View"
            allow="clipboard-read; clipboard-write"
          />
        ) : (
          <div className="novnc-connecting">
            Connecting to desktop...
          </div>
        )}
      </div>
    );
  }
