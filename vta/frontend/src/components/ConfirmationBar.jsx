import React from 'react';

/**
 * Confirmation bar - appears after each task completes.
 * Student can click Yes/Continue, No, or Repeat.
 * Supports custom messages for per-subtask confirmation (self-paced mode).
 */
export default function ConfirmationBar({ visible, taskTitle, message, onConfirm }) {
  if (!visible) return null;

  // If a custom message is provided (e.g., per-subtask in paced mode), show it
  // with a simpler "Continue" / "Show me again" button set
  const isSubtaskConfirmation = !!message;

  return (
    <div className="confirmation-bar">
      <div className="confirmation-message">
        {isSubtaskConfirmation ? (
          <>
            <strong>{taskTitle}</strong>
            <br />
            {message}
          </>
        ) : (
          <>That's <strong>{taskTitle}</strong> done. Ready to move on?</>
        )}
      </div>
      <div className="confirmation-buttons">
        <button
          className="confirm-btn confirm-yes"
          onClick={() => onConfirm('yes')}
        >
          {isSubtaskConfirmation ? 'Continue' : 'Yes'}
        </button>
        <button
          className="confirm-btn confirm-repeat"
          onClick={() => onConfirm('repeat')}
        >
          {isSubtaskConfirmation ? 'Show me again' : 'Repeat'}
        </button>
        {!isSubtaskConfirmation && (
          <button
            className="confirm-btn confirm-no"
            onClick={() => onConfirm('no')}
          >
            Not yet
          </button>
        )}
      </div>
    </div>
  );
}
