import React, { useEffect, useRef } from 'react';

/**
 * Chat transcript panel showing real-time Sonic + student speech.
 */
export default function ChatTranscript({ messages }) {
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  return (
    <div className="chat-transcript">
      <div className="chat-header">Chat Transcript</div>
      <div className="chat-messages">
        {messages.map((msg, i) => (
          <div key={i} className={`chat-message chat-${msg.role}`}>
            <span className="chat-role">
              {msg.role === 'assistant' ? 'TRAINER' : 'YOU'}:
            </span>
            <span className="chat-text">{msg.text}</span>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}
