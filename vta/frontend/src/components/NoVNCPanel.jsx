import React, { useRef, useEffect, useState } from 'react';

  /**
   * noVNC panel — embeds the noVNC web client via iframe.
   * Much simpler than importing the noVNC JS library which has CJS/ESM issues.
   * The noVNC websockify server serves its own web client at port 6080.
   */
  export default function NoVNCPanel({ visible, novncUrl }) {
    const [noVncWebUrl, setNoVncWebUrl] = useState('');

    useEffect(() => {
      // Build the noVNC web client URL
      // noVNC's websockify serves a web client at its HTTP port
      const host = window.location.hostname;
      const protocol = window.location.protocol === 'https:' ? 'https' : 'http';
      setNoVncWebUrl(`${protocol}://${host}:6080/vnc.html?autoconnect=true&resize=scale`);
    }, []);

    return (
      <div
        className="novnc-panel"
        style={{ display: visible ? 'block' : 'none' }}
      >
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
