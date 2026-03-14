import React, { useState, useEffect, useCallback } from 'react';
import useWebSocket from './hooks/useWebSocket';
import useAudioStream from './hooks/useAudioStream';
import ChatTranscript from './components/ChatTranscript';
import SlideViewer from './components/SlideViewer';
import NoVNCPanel from './components/NoVNCPanel';
import ConfirmationBar from './components/ConfirmationBar';
import TaskProgress from './components/TaskProgress';
import MicrophoneInput from './components/MicrophoneInput';


// Direct connection to WSL2 IP address
const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
const WS_URL = `${wsProtocol}//${window.location.host}/ws`;
const NOVNC_URL = `${wsProtocol}//${window.location.host}/websockify`;

const EXECUTION_MODES = [
  {
    value: 'demo_only',
    label: 'Demo Only',
    description: 'Watch ARIA demonstrate. Great for first-time learners.',
  },
  {
    value: 'follow_along_realtime',
    label: 'Follow Along (Real-time)',
    description: 'Do actions with ARIA in real-time. Fast-paced.',
  },
  {
    value: 'follow_along_paced',
    label: 'Follow Along (Self-paced)',
    description: 'Watch demo, then try yourself. Click Continue when ready.',
  },
];

const BRAIN_MODELS = [
  { value: 'flash', label: 'Gemini Flash', description: 'Gemini 3 Flash — fast intent & Q&A' },
  { value: 'pro', label: 'Gemini Pro', description: 'Gemini 2.5 Pro — deeper reasoning' },
];

export default function App() {
  // Connection state
  const { isConnected, send, on } = useWebSocket(WS_URL);
  const { isMicActive, startMic, stopMic, playAudioChunk, handleInterruption } = useAudioStream(send);

  // Session state
  const [sessionId, setSessionId] = useState(null);
  const [tutorialTitle, setTutorialTitle] = useState('');
  const [pdfUrl, setPdfUrl] = useState('');
  const [executionMode, setExecutionMode] = useState('demo_only');
  const [brainModel, setBrainModel] = useState('flash');
  const [selectedTutorialId, setSelectedTutorialId] = useState(null);
  const [uploadedFile, setUploadedFile] = useState(null);
  const [uploadedCurriculum, setUploadedCurriculum] = useState(null);
  const [uploadTitle, setUploadTitle] = useState('');
  const [uploading, setUploading] = useState(false);
  const [availableTutorials, setAvailableTutorials] = useState([]);
  const [showUploadForm, setShowUploadForm] = useState(false);

  // UI state
  const [messages, setMessages] = useState([]);
  const [tasks, setTasks] = useState([]);
  const [currentTaskId, setCurrentTaskId] = useState(null);
  const [rightPanel, setRightPanel] = useState('slides'); // 'slides' or 'desktop'
  const [currentPage, setCurrentPage] = useState(1);
  const [currentTask, setCurrentTask] = useState(null);
  const [showConfirmation, setShowConfirmation] = useState(false);
  const [confirmationTask, setConfirmationTask] = useState('');
  const [confirmationMessage, setConfirmationMessage] = useState('');
  const [sessionComplete, setSessionComplete] = useState(false);
  const [ariaStatus, setAriaStatus] = useState('idle'); // 'idle' | 'thinking' | 'listening'

  // Register event handlers
  useEffect(() => {
    on('session_started', (data) => {
      setSessionId(data.session_id);
      if (data.execution_mode) {
        setExecutionMode(data.execution_mode);
      }
      if (data.brain_model) {
        setBrainModel(data.brain_model);
      }
    });

    on('tutorial_loaded', (data) => {
      console.log('[DEBUG] tutorial_loaded event received:', data);
      setTutorialTitle(data.title);
      // Proxy external PDF URLs through backend to bypass CORS
      if (data.pdf_url) {
        const proxyUrl = `/api/pdf/proxy?url=${encodeURIComponent(data.pdf_url)}`;
        console.log('[DEBUG] Setting pdfUrl to proxy:', proxyUrl);
        setPdfUrl(proxyUrl);
      } else if (data.pdf_s3_key) {
        console.log('[DEBUG] Using pdf_s3_key:', data.pdf_s3_key);
        setPdfUrl(`/api/pdf/${data.pdf_s3_key}`);
      }
    });

    on('audio_chunk', (data) => {
      if (data.data) {
        setAriaStatus('speaking');
        playAudioChunk(data.data);
      }
    });

    on('transcript_update', (data) => {
      // Check if this is an interruption signal from Sonic
      if (data.role === 'assistant' && data.text && data.text.trim().startsWith('{')) {
        try {
          const parsed = JSON.parse(data.text);
          if (parsed.interrupted === true) {
            console.log('[APP] Sonic signaled interruption');
            handleInterruption();
            return; // Don't add this message to the transcript
          }
        } catch (e) {
          // Not JSON, continue normally
        }
      }

      const role = data.role || 'assistant';
      setMessages((prev) => {
        // Append to last message if same role (avoids word-by-word display)
        if (prev.length > 0 && prev[prev.length - 1].role === role) {
          const updated = [...prev];
          updated[updated.length - 1] = {
            ...updated[updated.length - 1],
            text: updated[updated.length - 1].text + ' ' + data.text,
          };
          return updated;
        }
        return [...prev, { role, text: data.text }];
      });
    });

    on('show_slide', (data) => {
      console.log(`[APP] show_slide event: page ${data.page}`);
      setRightPanel('slides');
      setCurrentPage(data.page);
    });

    on('show_desktop', () => {
      console.log('[APP] show_desktop event - switching to desktop view');
      setRightPanel('desktop');
    });

    on('task_started', (data) => {
      setCurrentTaskId(data.task_id);
      setCurrentTask(data.task || null);
      setTasks((prev) => updateTaskStatus(prev, data.task_id, null, 'running', data.task));
    });

    on('task_completed', (data) => {
      setTasks((prev) => updateTaskStatus(prev, data.task_id, null, 'completed'));
    });

    on('subtask_started', (data) => {
      setTasks((prev) => updateSubtaskStatus(prev, data.subtask_id, 'running'));
    });

    on('subtask_completed', (data) => {
      setTasks((prev) => updateSubtaskStatus(prev, data.subtask_id, 'completed'));
    });

    on('show_confirmation', (data) => {
      setShowConfirmation(true);
      setConfirmationTask(data.task_title || '');
      setConfirmationMessage(data.message || '');
    });

    on('hide_confirmation', () => {
      setShowConfirmation(false);
      setConfirmationMessage('');
    });

    on('aria_thinking', () => {
      setAriaStatus('thinking');
      stopMic();
    });

    on('aria_listening', () => {
      setAriaStatus('listening');
      startMic();
    });

    on('session_complete', () => {
      setSessionComplete(true);
      setAriaStatus('idle');
    });

    on('error', (data) => {
      setMessages((prev) => [...prev, {
        role: 'system',
        text: `Error: ${data.message}`,
      }]);
    });
  }, [on, playAudioChunk, startMic, stopMic]);

  // Fetch available tutorials on mount
  useEffect(() => {
    fetch('/api/tutorials')
      .then(r => r.json())
      .then(data => setAvailableTutorials(data.tutorials || []))
      .catch(() => {});
  }, []);

  // Upload tutorial
  const handleUpload = useCallback(async () => {
    if (!uploadedFile) return;
    setUploading(true);

    const formData = new FormData();
    formData.append('pdf', uploadedFile);
    if (uploadedCurriculum) formData.append('curriculum', uploadedCurriculum);
    formData.append('title', uploadTitle || uploadedFile.name.replace('.pdf', ''));

    try {
      const resp = await fetch('/api/upload-tutorial', { method: 'POST', body: formData });
      const data = await resp.json();
      setSelectedTutorialId(data.tutorial_id);
      setAvailableTutorials(prev => [...prev, { tutorial_id: data.tutorial_id, title: data.title, task_count: data.task_count }]);
      setUploadedFile(null);
      setUploadedCurriculum(null);
      setUploadTitle('');
    } catch (err) {
      console.error('Upload failed:', err);
    }
    setUploading(false);
  }, [uploadedFile, uploadedCurriculum, uploadTitle]);

  // Delete tutorial
  const handleDelete = useCallback(async (tutorialId) => {
    if (!confirm(`Delete this course?`)) return;
    try {
      await fetch(`/api/tutorials/${tutorialId}`, { method: 'DELETE' });
      setAvailableTutorials(prev => prev.filter(t => t.tutorial_id !== tutorialId));
      if (selectedTutorialId === tutorialId) setSelectedTutorialId(null);
    } catch (err) {
      console.error('Delete failed:', err);
    }
  }, [selectedTutorialId]);

  // Start session
  const handleStartSession = useCallback(() => {
    send({
      event: 'start_session',
      tutorial_id: selectedTutorialId,
      student_id: 'student_1',
      execution_mode: executionMode,
      brain_model: brainModel,
    });
  }, [send, executionMode, brainModel, selectedTutorialId]);

  // Send confirmation
  const handleConfirm = useCallback((response) => {
    send({
      event: 'student_confirmation',
      response,
      session_id: sessionId,
    });
  }, [send, sessionId]);

  // Slide loaded callback
  const handleSlideLoaded = useCallback((page) => {
    send({ event: 'slide_loaded', page });
  }, [send]);

  return (
    <div className="vta-app">
      <header className="vta-header">
        <h1>Virtual Trainer Agent</h1>
        {tutorialTitle && <span className="tutorial-title">{tutorialTitle}</span>}
        {sessionId && (
          <>
            <span className="execution-mode-badge">
              {EXECUTION_MODES.find(m => m.value === executionMode)?.label || executionMode}
            </span>
            <span className="brain-model-badge">
              Brain: {BRAIN_MODELS.find(m => m.value === brainModel)?.label || brainModel}
            </span>
          </>
        )}
        {sessionId && ariaStatus !== 'idle' && (
          <span className={`aria-status aria-status-${ariaStatus}`}>
            {ariaStatus === 'thinking' && '⏳ ARIA is preparing...'}
            {ariaStatus === 'speaking' && '🔊 ARIA is speaking'}
            {ariaStatus === 'listening' && '🎤 Your turn — speak now'}
          </span>
        )}
        <span className={`connection-status ${isConnected ? 'connected' : 'disconnected'}`}>
          {isConnected ? 'Connected' : 'Disconnected'}
        </span>
      </header>

      <main className="vta-main">
        {/* Left Panel */}
        <div className="left-panel">
          <ChatTranscript messages={messages} />

          <TaskProgress tasks={tasks} currentTaskId={currentTaskId} />

          <ConfirmationBar
            visible={showConfirmation}
            taskTitle={confirmationTask}
            message={confirmationMessage}
            onConfirm={handleConfirm}
          />

          <MicrophoneInput
            isMicActive={isMicActive}
            onStart={startMic}
            onStop={stopMic}
          />

          {sessionId && !sessionComplete && (
            <div className="ready-button-bar">
              <button
                className="ready-btn"
                onClick={() => send({ event: 'student_confirmation', response: 'ready', session_id: sessionId })}
              >
                ▶ Ready / Next
              </button>
            </div>
          )}

          {!sessionId && (
            <div className="start-session">
              {/* Course List */}
              <div className="course-list">
                <label className="mode-selector-label">Your Courses</label>
                {availableTutorials.length === 0 && (
                  <div className="no-courses">No courses yet. Upload one below to get started.</div>
                )}
                {availableTutorials.map((t) => (
                  <div
                    key={t.tutorial_id}
                    className={`course-card ${selectedTutorialId === t.tutorial_id ? 'course-card-selected' : ''}`}
                    onClick={() => setSelectedTutorialId(t.tutorial_id)}
                  >
                    <div className="course-card-info">
                      <span className="course-card-title">{t.title}</span>
                      <span className="course-card-meta">
                        {t.task_count} tasks {t.has_pdf ? '| PDF' : ''}
                      </span>
                    </div>
                    <button
                      className="course-delete-btn"
                      onClick={(e) => { e.stopPropagation(); handleDelete(t.tutorial_id); }}
                      title="Delete course"
                    >
                      X
                    </button>
                  </div>
                ))}
              </div>

              {/* Upload New Course */}
              <button
                className="toggle-upload-btn"
                onClick={() => setShowUploadForm(!showUploadForm)}
              >
                {showUploadForm ? 'Cancel' : '+ Add New Course'}
              </button>

              {showUploadForm && (
                <div className="upload-section">
                  <div className="upload-row">
                    <input
                      type="text"
                      placeholder="Course title"
                      value={uploadTitle}
                      onChange={(e) => setUploadTitle(e.target.value)}
                      className="upload-input"
                    />
                  </div>
                  <div className="upload-row">
                    <label className="upload-label">
                      Slides (PDF):
                      <input type="file" accept=".pdf" onChange={(e) => setUploadedFile(e.target.files[0])} />
                    </label>
                  </div>
                  <div className="upload-row">
                    <label className="upload-label">
                      Curriculum (JSON, optional):
                      <input type="file" accept=".json" onChange={(e) => setUploadedCurriculum(e.target.files[0])} />
                    </label>
                  </div>
                  {uploadedFile && (
                    <button className="upload-btn" onClick={handleUpload} disabled={uploading}>
                      {uploading ? 'Uploading...' : 'Upload Course'}
                    </button>
                  )}
                </div>
              )}

              {/* Settings (only show when a course is selected) */}
              {selectedTutorialId && (
              <div className="mode-selector">
                <label className="mode-selector-label">Tutorial Mode:</label>
                {EXECUTION_MODES.map((mode) => (
                  <label key={mode.value} className="mode-option">
                    <input
                      type="radio"
                      name="executionMode"
                      value={mode.value}
                      checked={executionMode === mode.value}
                      onChange={(e) => setExecutionMode(e.target.value)}
                    />
                    <div className="mode-option-content">
                      <span className="mode-option-label">{mode.label}</span>
                      <span className="mode-option-desc">{mode.description}</span>
                    </div>
                  </label>
                ))}
              </div>
              <div className="mode-selector">
                <label className="mode-selector-label">Brain Model:</label>
                {BRAIN_MODELS.map((model) => (
                  <label key={model.value} className="mode-option">
                    <input
                      type="radio"
                      name="brainModel"
                      value={model.value}
                      checked={brainModel === model.value}
                      onChange={(e) => setBrainModel(e.target.value)}
                    />
                    <div className="mode-option-content">
                      <span className="mode-option-label">{model.label}</span>
                      <span className="mode-option-desc">{model.description}</span>
                    </div>
                  </label>
                ))}
              </div>
              <button
                className="start-btn"
                onClick={handleStartSession}
                disabled={!isConnected || !selectedTutorialId}
              >
                Start Course
              </button>
              )}
            </div>
          )}

          {sessionComplete && (
            <div className="session-complete">
              Tutorial Complete! Great job!
            </div>
          )}
        </div>

        {/* Right Panel */}
        <div className="right-panel">
          <div
            className="slide-panel"
            style={{ display: rightPanel === 'slides' ? 'flex' : 'none' }}
          >
            <SlideViewer
              pdfUrl={pdfUrl}
              currentPage={currentPage}
              currentTask={currentTask}
              onSlideLoaded={handleSlideLoaded}
            />
          </div>

          <NoVNCPanel
            visible={rightPanel === 'desktop'}
            novncUrl={NOVNC_URL}
          />
        </div>
      </main>
    </div>
  );
}

// Helper: update task status in task list
function updateTaskStatus(tasks, taskId, subtaskId, status, taskData) {
  const existing = tasks.find((t) => t.task_id === taskId);
  if (existing) {
    return tasks.map((t) =>
      t.task_id === taskId ? { ...t, status } : t
    );
  }
  if (taskData) {
    return [...tasks, { ...taskData, status }];
  }
  return tasks;
}

// Helper: update subtask status
function updateSubtaskStatus(tasks, subtaskId, status) {
  return tasks.map((task) => {
    if (!task.subtasks) return task;
    const updatedSubtasks = task.subtasks.map((sub) =>
      sub.subtask_id === subtaskId ? { ...sub, status } : sub
    );
    return { ...task, subtasks: updatedSubtasks };
  });
}
