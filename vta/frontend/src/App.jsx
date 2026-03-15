import React, { useState, useEffect, useCallback } from 'react';
import useWebSocket from './hooks/useWebSocket';
import useAudioStream from './hooks/useAudioStream';
import ChatTranscript from './components/ChatTranscript';
import SlideViewer from './components/SlideViewer';
import NoVNCPanel from './components/NoVNCPanel';
import ConfirmationBar from './components/ConfirmationBar';
import TaskProgress from './components/TaskProgress';
import MicrophoneInput from './components/MicrophoneInput';
import CurriculumBuilder from './components/CurriculumBuilder';


// Direct connection to WSL2 IP address
const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
const WS_URL = `${wsProtocol}//${window.location.host}/ws`;
const NOVNC_URL = `${wsProtocol}//${window.location.host}/websockify`;

const EXECUTION_MODES = [
  {
    value: 'demo_only',
    label: 'Demo Only',
    description: 'Watch Nexora demonstrate. Great for first-time learners.',
  },
  {
    value: 'follow_along_realtime',
    label: 'Follow Along (Real-time)',
    description: 'Do actions with Nexora in real-time. Fast-paced.',
  },
  {
    value: 'follow_along_paced',
    label: 'Follow Along (Self-paced)',
    description: 'Watch demo, then try yourself. Click Continue when ready.',
  },
];

const MODEL_CONFIG = {
  voice: {
    label: 'Voice Model',
    description: 'Real-time bidirectional audio for Nexora\'s voice. Speaks instructions and listens to student responses.',
    fixedId: 'gemini-2.5-flash-native-audio-preview-12-2025',
  },
  brain: {
    label: 'Brain Model',
    description: 'Classifies student intent (continue, repeat, question), answers off-script questions, and generates slide explanations from images.',
    presets: [
      { value: 'flash', label: 'Gemini 3 Flash', id: 'gemini-3-flash-preview' },
      { value: 'pro', label: 'Gemini 2.5 Pro', id: 'gemini-2.5-pro-preview-05-06' },
    ],
  },
  desktopVision: {
    label: 'Desktop Vision Model',
    description: 'Plans desktop automation actions from screenshots. Sees the screen, decides what to click, type, or open — executed by Agent S3.',
    presets: [
      { value: 'gemini-3-flash-preview', label: 'Gemini 3 Flash' },
      { value: 'gemini-2.5-pro-preview-05-06', label: 'Gemini 2.5 Pro' },
    ],
  },
  browserVision: {
    label: 'Browser Vision Model',
    description: 'Controls the browser via Gemini Computer Use API. Navigates web pages, clicks elements, fills forms for web-based tutorial tasks.',
    presets: [
      { value: 'gemini-3-flash-preview', label: 'Gemini 3 Flash' },
      { value: 'gemini-2.5-pro-preview-05-06', label: 'Gemini 2.5 Pro' },
    ],
  },
};

export default function App() {
  // Connection state
  const { isConnected, send, on } = useWebSocket(WS_URL);
  const { isMicActive, startMic, stopMic, playAudioChunk, handleInterruption } = useAudioStream(send);

  // Session state
  const [sessionId, setSessionId] = useState(null);
  const [tutorialTitle, setTutorialTitle] = useState('');
  const [pdfUrl, setPdfUrl] = useState('');
  const [executionMode, setExecutionMode] = useState('demo_only');
  const [brainModel, setBrainModel] = useState(localStorage.getItem('vta_brain_model') || 'flash');
  const [apiKey, setApiKey] = useState(localStorage.getItem('gemini_api_key') || '');
  const [selectedTutorialId, setSelectedTutorialId] = useState(null);
  const [uploadedFile, setUploadedFile] = useState(null);
  const [uploadedCurriculum, setUploadedCurriculum] = useState(null);
  const [uploadTitle, setUploadTitle] = useState('');
  const [uploading, setUploading] = useState(false);
  const [availableTutorials, setAvailableTutorials] = useState([]);
  const [showUploadForm, setShowUploadForm] = useState(null); // null | 'slides' | 'curriculum'
  const [showBuilder, setShowBuilder] = useState(false);

  // Model configuration state
  const [showModelConfig, setShowModelConfig] = useState(false);
  const [configSaved, setConfigSaved] = useState(false);
  const [desktopVisionModel, setDesktopVisionModel] = useState(localStorage.getItem('vta_desktop_vision_model') || 'gemini-3-flash-preview');
  const [customDesktopVisionModel, setCustomDesktopVisionModel] = useState(localStorage.getItem('vta_custom_desktop_vision_model') || '');
  const [browserVisionModel, setBrowserVisionModel] = useState(localStorage.getItem('vta_browser_vision_model') || 'gemini-3-flash-preview');
  const [customBrowserVisionModel, setCustomBrowserVisionModel] = useState(localStorage.getItem('vta_custom_browser_vision_model') || '');
  const [customBrainModel, setCustomBrainModel] = useState(localStorage.getItem('vta_custom_brain_model') || '');

  // UI state
  const [messages, setMessages] = useState([]);
  const [tasks, setTasks] = useState([]);
  const [currentTaskId, setCurrentTaskId] = useState(null);
  const [rightPanel, setRightPanel] = useState('welcome'); // 'welcome' | 'slides' | 'desktop'
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
      setRightPanel('welcome');
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
    if (!uploadedFile && !uploadedCurriculum) return;
    setUploading(true);

    const formData = new FormData();
    if (uploadedFile) formData.append('pdf', uploadedFile);
    if (uploadedCurriculum) formData.append('curriculum', uploadedCurriculum);
    const defaultTitle = uploadedFile ? uploadedFile.name.replace('.pdf', '') : (uploadedCurriculum ? uploadedCurriculum.name.replace('.json', '') : 'Untitled');
    formData.append('title', uploadTitle || defaultTitle);

    try {
      const resp = await fetch('/api/upload-tutorial', { method: 'POST', body: formData });
      if (!resp.ok) {
        const errText = await resp.text();
        throw new Error(`Upload failed (${resp.status}): ${errText}`);
      }
      const data = await resp.json();
      setSelectedTutorialId(data.tutorial_id);
      setAvailableTutorials(prev => [...prev, { tutorial_id: data.tutorial_id, title: data.title, task_count: data.task_count }]);
      setUploadedFile(null);
      setUploadedCurriculum(null);
      setUploadTitle('');
      setShowUploadForm(null);
      alert(`Course "${data.title}" uploaded successfully!`);
    } catch (err) {
      console.error('Upload failed:', err);
      alert('Upload failed. Please try again.');
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

  // Save configuration to localStorage
  const handleSaveConfig = useCallback(() => {
    localStorage.setItem('gemini_api_key', apiKey);
    localStorage.setItem('vta_brain_model', brainModel);
    localStorage.setItem('vta_desktop_vision_model', desktopVisionModel);
    localStorage.setItem('vta_custom_desktop_vision_model', customDesktopVisionModel);
    localStorage.setItem('vta_browser_vision_model', browserVisionModel);
    localStorage.setItem('vta_custom_browser_vision_model', customBrowserVisionModel);
    localStorage.setItem('vta_custom_brain_model', customBrainModel);
    setConfigSaved(true);
    setTimeout(() => setConfigSaved(false), 2000);
  }, [apiKey, brainModel, desktopVisionModel, customDesktopVisionModel,
      browserVisionModel, customBrowserVisionModel, customBrainModel]);

  // Start session
  const handleStartSession = useCallback(() => {
    const effectiveBrain = brainModel === 'custom' ? customBrainModel : brainModel;
    const effectiveDesktopVision = desktopVisionModel === 'custom' ? customDesktopVisionModel : desktopVisionModel;
    const effectiveBrowserVision = browserVisionModel === 'custom' ? customBrowserVisionModel : browserVisionModel;
    send({
      event: 'start_session',
      tutorial_id: selectedTutorialId,
      student_id: 'student_1',
      execution_mode: executionMode,
      brain_model: effectiveBrain,
      desktop_vision_model: effectiveDesktopVision,
      browser_vision_model: effectiveBrowserVision,
      api_key: apiKey,
    });
  }, [send, executionMode, brainModel, customBrainModel, desktopVisionModel,
      customDesktopVisionModel, browserVisionModel, customBrowserVisionModel,
      selectedTutorialId, apiKey]);

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
        <h1>✦ Nexora AI</h1>
        {tutorialTitle && <span className="tutorial-title">{tutorialTitle}</span>}
        {sessionId && (
          <>
            <span className="execution-mode-badge">
              {EXECUTION_MODES.find(m => m.value === executionMode)?.label || executionMode}
            </span>
            <span className="brain-model-badge">
              Brain: {MODEL_CONFIG.brain.presets.find(m => m.value === brainModel)?.label || brainModel}
            </span>
          </>
        )}
        {sessionId && ariaStatus !== 'idle' && (
          <span className={`aria-status aria-status-${ariaStatus}`}>
            {ariaStatus === 'thinking' && '⏳ Nexora is preparing...'}
            {ariaStatus === 'speaking' && '🔊 Nexora is speaking'}
            {ariaStatus === 'listening' && '🎤 Your turn — speak now'}
          </span>
        )}
        <button
          className="model-config-btn"
          onClick={() => setShowModelConfig(!showModelConfig)}
          title="Configuration"
        >
          &#9881;
        </button>
        <span className={`connection-status ${isConnected ? 'connected' : 'disconnected'}`}>
          {isConnected ? 'Connected' : 'Disconnected'}
        </span>
      </header>

      {showModelConfig && (
        <div className="model-config-overlay" onClick={() => setShowModelConfig(false)}>
          <div className="model-config-panel" onClick={(e) => e.stopPropagation()}>
            <div className="config-header">
              <h2>Configuration</h2>
              <button className="config-close-btn" onClick={() => setShowModelConfig(false)}>&#10005;</button>
            </div>

            <div className="config-section">
              <label className="config-label">Gemini API Key</label>
              <p className="config-desc">Required for all AI features — voice, vision, and brain models.</p>
              <input
                type="password"
                className="config-input"
                placeholder="Enter your Gemini API key"
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
              />
              <span className="api-key-hint" style={{ marginTop: '6px' }}>
                Get your key at <a href="https://aistudio.google.com/apikey" target="_blank" rel="noopener noreferrer">Google AI Studio</a>
              </span>
            </div>

            <div className="config-section">
              <label className="config-label">{MODEL_CONFIG.voice.label}</label>
              <p className="config-desc">{MODEL_CONFIG.voice.description}</p>
              <div className="config-fixed">{MODEL_CONFIG.voice.fixedId}</div>
            </div>

            <div className="config-section">
              <label className="config-label">{MODEL_CONFIG.brain.label}</label>
              <p className="config-desc">{MODEL_CONFIG.brain.description}</p>
              <select
                className="config-select"
                value={brainModel}
                onChange={(e) => setBrainModel(e.target.value)}
                disabled={!!sessionId}
              >
                {MODEL_CONFIG.brain.presets.map((p) => (
                  <option key={p.value} value={p.value}>{p.label} ({p.id})</option>
                ))}
                <option value="custom">Custom</option>
              </select>
              {brainModel === 'custom' && (
                <input
                  type="text"
                  className="config-input"
                  placeholder="e.g. gemini-2.5-pro-preview-05-06"
                  value={customBrainModel}
                  onChange={(e) => setCustomBrainModel(e.target.value)}
                  disabled={!!sessionId}
                />
              )}
            </div>

            <div className="config-section">
              <label className="config-label">{MODEL_CONFIG.desktopVision.label}</label>
              <p className="config-desc">{MODEL_CONFIG.desktopVision.description}</p>
              <select
                className="config-select"
                value={desktopVisionModel}
                onChange={(e) => setDesktopVisionModel(e.target.value)}
                disabled={!!sessionId}
              >
                {MODEL_CONFIG.desktopVision.presets.map((p) => (
                  <option key={p.value} value={p.value}>{p.label} ({p.value})</option>
                ))}
                <option value="custom">Custom</option>
              </select>
              {desktopVisionModel === 'custom' && (
                <input
                  type="text"
                  className="config-input"
                  placeholder="e.g. gemini-3-flash-preview"
                  value={customDesktopVisionModel}
                  onChange={(e) => setCustomDesktopVisionModel(e.target.value)}
                  disabled={!!sessionId}
                />
              )}
            </div>

            <div className="config-section">
              <label className="config-label">{MODEL_CONFIG.browserVision.label}</label>
              <p className="config-desc">{MODEL_CONFIG.browserVision.description}</p>
              <select
                className="config-select"
                value={browserVisionModel}
                onChange={(e) => setBrowserVisionModel(e.target.value)}
                disabled={!!sessionId}
              >
                {MODEL_CONFIG.browserVision.presets.map((p) => (
                  <option key={p.value} value={p.value}>{p.label} ({p.value})</option>
                ))}
                <option value="custom">Custom</option>
              </select>
              {browserVisionModel === 'custom' && (
                <input
                  type="text"
                  className="config-input"
                  placeholder="e.g. gemini-3-flash-preview"
                  value={customBrowserVisionModel}
                  onChange={(e) => setCustomBrowserVisionModel(e.target.value)}
                  disabled={!!sessionId}
                />
              )}
            </div>

            <div className="config-save-section">
              <button className="config-save-btn" onClick={handleSaveConfig}>
                Save Configuration
              </button>
              {configSaved && <span className="config-saved-msg">Settings saved</span>}
            </div>
          </div>
        </div>
      )}

      <main className="vta-main">
        {/* Left Panel */}
        <div className="left-panel">
          {sessionId && (
            <>
              <ChatTranscript messages={messages} />
              <TaskProgress tasks={tasks} currentTaskId={currentTaskId} />
            </>
          )}

          <ConfirmationBar
            visible={showConfirmation}
            taskTitle={confirmationTask}
            message={confirmationMessage}
            onConfirm={handleConfirm}
          />

          {sessionId && !sessionComplete && (
            <MicrophoneInput
              isMicActive={isMicActive}
              onStart={startMic}
              onStop={stopMic}
            />
          )}

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

          {!sessionId && showBuilder && (
            <CurriculumBuilder
              onSave={(data) => {
                setAvailableTutorials(prev => [...prev, { tutorial_id: data.tutorial_id, title: data.title, task_count: data.task_count }]);
                setSelectedTutorialId(data.tutorial_id);
                setShowBuilder(false);
              }}
              onCancel={() => setShowBuilder(false)}
            />
          )}

          {!sessionId && !showBuilder && (
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

              {/* Course Action Buttons */}
              <div className="course-action-buttons">
                <button className="toggle-upload-btn" onClick={() => setShowBuilder(true)}>
                  Create Course
                </button>
                <button
                  className={`toggle-upload-btn ${showUploadForm === 'slides' ? 'toggle-upload-active' : ''}`}
                  onClick={() => setShowUploadForm(showUploadForm === 'slides' ? null : 'slides')}
                >
                  Import from Slides
                </button>
                <button
                  className={`toggle-upload-btn ${showUploadForm === 'curriculum' ? 'toggle-upload-active' : ''}`}
                  onClick={() => setShowUploadForm(showUploadForm === 'curriculum' ? null : 'curriculum')}
                >
                  Import with Curriculum
                </button>
              </div>

              {showUploadForm === 'slides' && (
                <div className="upload-section">
                  <div className="upload-hint">Upload a PDF — one theory task will be auto-generated per slide. Nexora will use AI vision to narrate each slide.</div>
                  <div className="upload-row">
                    <label className="upload-label">Course Title:</label>
                    <input type="text" className="upload-input" placeholder="e.g. Introduction to Python" value={uploadTitle} onChange={(e) => setUploadTitle(e.target.value)} />
                  </div>
                  <div className="upload-row">
                    <label className="upload-label">
                      Slides (PDF):
                      <input type="file" accept=".pdf" onChange={(e) => setUploadedFile(e.target.files[0])} />
                    </label>
                  </div>
                  {uploadedFile && (
                    <button className="upload-btn" onClick={handleUpload} disabled={uploading}>
                      {uploading ? 'Importing...' : 'Import Slides'}
                    </button>
                  )}
                </div>
              )}

              {showUploadForm === 'curriculum' && (
                <div className="upload-section">
                  <div className="upload-hint">Upload a curriculum JSON file that defines tasks, subtasks, and narration. PDF is optional — only needed if your curriculum has theory slides.</div>
                  <div className="upload-row">
                    <label className="upload-label">
                      Curriculum (JSON):
                      <input type="file" accept=".json" onChange={(e) => setUploadedCurriculum(e.target.files[0])} />
                    </label>
                  </div>
                  <div className="upload-row">
                    <label className="upload-label">
                      Slides (PDF, optional):
                      <input type="file" accept=".pdf" onChange={(e) => setUploadedFile(e.target.files[0])} />
                    </label>
                  </div>
                  {uploadedCurriculum && (
                    <button className="upload-btn" onClick={handleUpload} disabled={uploading}>
                      {uploading ? 'Importing...' : 'Import Course'}
                    </button>
                  )}
                </div>
              )}

              {/* Settings (only show when a course is selected) */}
              {selectedTutorialId && (<>
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
              <button
                className="start-btn"
                onClick={handleStartSession}
                disabled={!isConnected || !selectedTutorialId || !apiKey}
              >
                Start Course
              </button>
              </>)}
            </div>
          )}

          {sessionComplete && (
            <div className="session-complete">
              Tutorial Complete! Great job!
              <button
                className="back-to-courses-btn"
                onClick={() => {
                  setSessionId(null);
                  setSessionComplete(false);
                  setMessages([]);
                  setTasks([]);
                  setAriaStatus('idle');
                  setRightPanel('welcome');
                  setTutorialTitle('');
                  setPdfUrl('');
                  setCurrentTask(null);
                  setCurrentTaskId(null);
                  setCurrentPage(1);
                }}
              >
                Back to Courses
              </button>
            </div>
          )}
        </div>

        {/* Right Panel */}
        <div className="right-panel">
          {rightPanel === 'welcome' && (
            <div className="welcome-panel">
              <div className="welcome-icon">&#10022;</div>
              <h2 className="welcome-title">Welcome to Nexora AI</h2>
              <p className="welcome-subtitle">Select a course and press Start to begin your learning session.</p>
            </div>
          )}

          <div
            className="slide-panel"
            style={{ display: rightPanel === 'slides' ? 'flex' : 'none' }}
          >
            <SlideViewer
              pdfUrl={pdfUrl}
              currentPage={currentPage}
              currentTask={currentTask}
              onSlideLoaded={handleSlideLoaded}
              visible={rightPanel === 'slides'}
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
