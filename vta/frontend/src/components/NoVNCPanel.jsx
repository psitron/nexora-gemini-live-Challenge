import React, { useEffect, useState } from 'react';

  /**
   * noVNC panel — embeds the desktop viewer via iframe.
   * Both app and noVNC run on HTTP so no mixed content issues.
   */
  export default function NoVNCPanel({ visible }) {
    const [noVncWebUrl, setNoVncWebUrl] = useState('');

    useEffect(() => {
      const host = window.location.hostname;
      setNoVncWebUrl(`http://${host}:6080/vnc.html?autoconnect=true&resize=scale&view_only=true`);
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
