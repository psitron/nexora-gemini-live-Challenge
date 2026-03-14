import React from 'react';

/**
 * Task progress panel showing completion status for each task.
 */
export default function TaskProgress({ tasks, currentTaskId }) {
  return (
    <div className="task-progress">
      <div className="progress-header">Task Progress</div>
      <ul className="progress-list">
        {tasks.map((task) => (
          <li
            key={task.task_id}
            className={`progress-item ${getStatusClass(task.status)} ${
              task.task_id === currentTaskId ? 'progress-current' : ''
            }`}
          >
            <span className="progress-icon">{getStatusIcon(task.status)}</span>
            <span className="progress-title">{task.title}</span>
            {task.subtasks && task.subtasks.length > 0 && (
              <ul className="progress-subtasks">
                {task.subtasks.map((sub) => (
                  <li
                    key={sub.subtask_id}
                    className={`progress-subtask ${getStatusClass(sub.status)}`}
                  >
                    <span className="progress-icon">
                      {getStatusIcon(sub.status)}
                    </span>
                    <span className="progress-title">{sub.title}</span>
                  </li>
                ))}
              </ul>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}

function getStatusIcon(status) {
  switch (status) {
    case 'completed': return '\u2705';
    case 'running': return '\uD83D\uDD04';
    case 'failed': return '\u274C';
    case 'replaying': return '\uD83D\uDD01';
    default: return '\u23F3';
  }
}

function getStatusClass(status) {
  return `status-${status || 'pending'}`;
}
