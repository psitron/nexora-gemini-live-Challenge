import React from 'react';

/**
 * Microphone start/stop button.
 */
export default function MicrophoneInput({ isMicActive, onStart, onStop }) {
  return (
    <div className="microphone-input">
      <button
        className={`mic-btn ${isMicActive ? 'mic-active' : 'mic-inactive'}`}
        onClick={isMicActive ? onStop : onStart}
      >
        {isMicActive ? (
          <>
            <span className="mic-icon">{'\uD83C\uDFA4'}</span>
            <span className="mic-label">Speaking...</span>
          </>
        ) : (
          <>
            <span className="mic-icon">{'\uD83C\uDFA4'}</span>
            <span className="mic-label">Click to Speak</span>
          </>
        )}
      </button>
    </div>
  );
}
