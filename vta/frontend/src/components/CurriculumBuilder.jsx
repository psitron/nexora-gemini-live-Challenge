import React, { useState, useCallback } from 'react';

const TASK_TYPES = [
  { value: 'theory', label: 'Theory', description: 'Show a slide and Nexora narrates the content' },
  { value: 'practical', label: 'Practical (Hands-on)', description: 'Nexora executes predefined commands on desktop' },
  { value: 'vision', label: 'Vision (AI Desktop)', description: 'AI autonomously accomplishes a goal on desktop or browser' },
];

const PRACTICAL_ACTIONS = [
  { value: 'open_terminal', label: 'Open Terminal' },
  { value: 'run_command', label: 'Run Command' },
  { value: 'click_text', label: 'Click Text' },
  { value: 'type_text', label: 'Type Text' },
  { value: 'keyboard', label: 'Press Keys' },
];

function emptyTask(index) {
  return {
    type: 'theory',
    title: '',
    slide_number: index + 1,
    slide_context: '',
    sonic_prompt: '',
    subtasks: [],
  };
}

function emptyPracticalSubtask() {
  return { title: '', sonic_prompt: '', action: 'open_terminal', params: {}, cmd: '' };
}

function emptyVisionSubtask() {
  return { title: '', sonic_prompt: '', goal: '' };
}

export default function CurriculumBuilder({ onSave, onCancel }) {
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [pdfFile, setPdfFile] = useState(null);
  const [tasks, setTasks] = useState([emptyTask(0)]);
  const [saving, setSaving] = useState(false);

  const addTask = () => {
    setTasks(prev => [...prev, emptyTask(prev.length)]);
  };

  const removeTask = (index) => {
    setTasks(prev => prev.filter((_, i) => i !== index));
  };

  const updateTask = (index, field, value) => {
    setTasks(prev => prev.map((t, i) => {
      if (i !== index) return t;
      const updated = { ...t, [field]: value };
      if (field === 'type') {
        updated.subtasks = [];
        if (value === 'theory') {
          updated.slide_number = index + 1;
          updated.slide_context = '';
          updated.sonic_prompt = '';
        } else {
          updated.slide_number = null;
          updated.slide_context = null;
        }
      }
      return updated;
    }));
  };

  const addSubtask = (taskIndex) => {
    setTasks(prev => prev.map((t, i) => {
      if (i !== taskIndex) return t;
      const newSub = t.type === 'practical' ? emptyPracticalSubtask() : emptyVisionSubtask();
      return { ...t, subtasks: [...t.subtasks, newSub] };
    }));
  };

  const removeSubtask = (taskIndex, subIndex) => {
    setTasks(prev => prev.map((t, i) => {
      if (i !== taskIndex) return t;
      return { ...t, subtasks: t.subtasks.filter((_, si) => si !== subIndex) };
    }));
  };

  const updateSubtask = (taskIndex, subIndex, field, value) => {
    setTasks(prev => prev.map((t, i) => {
      if (i !== taskIndex) return t;
      const updatedSubs = t.subtasks.map((s, si) => {
        if (si !== subIndex) return s;
        return { ...s, [field]: value };
      });
      return { ...t, subtasks: updatedSubs };
    }));
  };

  const handleSave = useCallback(async () => {
    if (!title.trim()) { alert('Please enter a course title.'); return; }
    if (!pdfFile) { alert('Please upload a PDF file.'); return; }

    setSaving(true);

    const curriculum = {
      title: title.trim(),
      description: description.trim(),
      tasks: tasks.map((t, i) => {
        const taskId = `T${i + 1}`;
        const base = {
          task_id: taskId,
          type: t.type,
          title: t.title || `Task ${i + 1}`,
          sonic_prompt: t.sonic_prompt || null,
          subtasks: [],
        };

        if (t.type === 'theory') {
          base.slide_number = t.slide_number || i + 1;
          base.slide_context = t.slide_context || '';
        } else {
          base.slide_number = null;
          base.slide_context = null;
        }

        if (t.type === 'practical') {
          base.subtasks = t.subtasks.map((s, si) => ({
            subtask_id: `${taskId}.${si + 1}`,
            title: s.title || `Step ${si + 1}`,
            sonic_prompt: s.sonic_prompt || '',
            action: s.action,
            params: s.action === 'run_command' ? { cmd: s.cmd || '' } : {},
            reflex_check: null,
          }));
        }

        if (t.type === 'vision') {
          base.subtasks = t.subtasks.map((s, si) => ({
            subtask_id: `${taskId}.${si + 1}`,
            title: s.title || `Step ${si + 1}`,
            sonic_prompt: s.sonic_prompt || '',
            goal: s.goal || '',
          }));
        }

        return base;
      }),
    };

    const formData = new FormData();
    formData.append('pdf', pdfFile);
    const curriculumBlob = new Blob([JSON.stringify(curriculum, null, 2)], { type: 'application/json' });
    formData.append('curriculum', curriculumBlob, 'curriculum.json');
    formData.append('title', title.trim());

    try {
      const resp = await fetch('/api/upload-tutorial', { method: 'POST', body: formData });
      if (!resp.ok) throw new Error(`Upload failed: ${resp.status}`);
      const data = await resp.json();
      alert(`Course "${data.title}" created successfully!`);
      if (onSave) onSave(data);
    } catch (err) {
      console.error('Save failed:', err);
      alert('Failed to save curriculum. Please try again.');
    }
    setSaving(false);
  }, [title, description, pdfFile, tasks, onSave]);

  return (
    <div className="curriculum-builder">
      <div className="cb-header">
        <h2>Create New Course</h2>
        <button className="cb-cancel-btn" onClick={onCancel}>Back</button>
      </div>

      <div className="cb-section">
        <label className="cb-label">Course Title *</label>
        <input type="text" className="cb-input" placeholder="e.g. Introduction to Python" value={title} onChange={(e) => setTitle(e.target.value)} />
        <label className="cb-label">Description</label>
        <textarea className="cb-textarea" placeholder="Brief course description..." value={description} onChange={(e) => setDescription(e.target.value)} rows={2} />
        <label className="cb-label">Slides (PDF) *</label>
        <input type="file" accept=".pdf" className="cb-file" onChange={(e) => setPdfFile(e.target.files[0])} />
        {pdfFile && <span className="cb-file-name">{pdfFile.name}</span>}
      </div>

      <div className="cb-section">
        <div className="cb-section-header">
          <label className="cb-label">Tasks</label>
          <button className="cb-add-btn" onClick={addTask}>+ Add Task</button>
        </div>

        {tasks.map((task, ti) => (
          <div key={ti} className="cb-task-card">
            <div className="cb-task-header">
              <span className="cb-task-number">Task {ti + 1}</span>
              <select className="cb-select" value={task.type} onChange={(e) => updateTask(ti, 'type', e.target.value)}>
                {TASK_TYPES.map(t => (<option key={t.value} value={t.value}>{t.label}</option>))}
              </select>
              {tasks.length > 1 && (<button className="cb-remove-btn" onClick={() => removeTask(ti)}>Remove</button>)}
            </div>
            <div className="cb-type-hint">{TASK_TYPES.find(t => t.value === task.type)?.description}</div>
            <input type="text" className="cb-input" placeholder="Task title" value={task.title} onChange={(e) => updateTask(ti, 'title', e.target.value)} />

            {task.type === 'theory' && (<>
              <div className="cb-row">
                <label className="cb-label-sm">Slide Page #</label>
                <input type="number" className="cb-input-sm" min="1" value={task.slide_number || ''} onChange={(e) => updateTask(ti, 'slide_number', parseInt(e.target.value) || 1)} />
              </div>
              <label className="cb-label-sm">What Nexora should explain about this slide:</label>
              <textarea className="cb-textarea" placeholder="Content for Nexora to narrate..." value={task.slide_context || ''} onChange={(e) => updateTask(ti, 'slide_context', e.target.value)} rows={3} />
            </>)}

            {(task.type === 'practical' || task.type === 'vision') && (<>
              <label className="cb-label-sm">Nexora introduction:</label>
              <textarea className="cb-textarea" placeholder="e.g. 'Now let us put everything into practice...'" value={task.sonic_prompt || ''} onChange={(e) => updateTask(ti, 'sonic_prompt', e.target.value)} rows={2} />
            </>)}

            {task.type === 'practical' && (
              <div className="cb-subtasks">
                <div className="cb-subtask-header">
                  <span className="cb-label-sm">Steps (desktop actions):</span>
                  <button className="cb-add-btn-sm" onClick={() => addSubtask(ti)}>+ Add Step</button>
                </div>
                {task.subtasks.map((sub, si) => (
                  <div key={si} className="cb-subtask-card">
                    <div className="cb-subtask-top">
                      <span className="cb-step-num">{si + 1}.</span>
                      <input type="text" className="cb-input-sm" placeholder="Step title" value={sub.title} onChange={(e) => updateSubtask(ti, si, 'title', e.target.value)} />
                      <select className="cb-select-sm" value={sub.action} onChange={(e) => updateSubtask(ti, si, 'action', e.target.value)}>
                        {PRACTICAL_ACTIONS.map(a => (<option key={a.value} value={a.value}>{a.label}</option>))}
                      </select>
                      <button className="cb-remove-btn-sm" onClick={() => removeSubtask(ti, si)}>x</button>
                    </div>
                    {sub.action === 'run_command' && (
                      <input type="text" className="cb-input-sm" placeholder="Command (e.g. ls, pwd)" value={sub.cmd || ''} onChange={(e) => updateSubtask(ti, si, 'cmd', e.target.value)} />
                    )}
                    <input type="text" className="cb-input-sm" placeholder="What Nexora says..." value={sub.sonic_prompt} onChange={(e) => updateSubtask(ti, si, 'sonic_prompt', e.target.value)} />
                  </div>
                ))}
              </div>
            )}

            {task.type === 'vision' && (
              <div className="cb-subtasks">
                <div className="cb-subtask-header">
                  <span className="cb-label-sm">Steps (AI goals):</span>
                  <button className="cb-add-btn-sm" onClick={() => addSubtask(ti)}>+ Add Step</button>
                </div>
                {task.subtasks.map((sub, si) => (
                  <div key={si} className="cb-subtask-card">
                    <div className="cb-subtask-top">
                      <span className="cb-step-num">{si + 1}.</span>
                      <input type="text" className="cb-input-sm" placeholder="Step title" value={sub.title} onChange={(e) => updateSubtask(ti, si, 'title', e.target.value)} />
                      <button className="cb-remove-btn-sm" onClick={() => removeSubtask(ti, si)}>x</button>
                    </div>
                    <textarea className="cb-textarea-sm" placeholder="Goal for AI (e.g. 'Open terminal and run ls')" value={sub.goal || ''} onChange={(e) => updateSubtask(ti, si, 'goal', e.target.value)} rows={2} />
                    <input type="text" className="cb-input-sm" placeholder="What Nexora says..." value={sub.sonic_prompt} onChange={(e) => updateSubtask(ti, si, 'sonic_prompt', e.target.value)} />
                  </div>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>

      <div className="cb-actions">
        <button className="cb-save-btn" onClick={handleSave} disabled={saving}>
          {saving ? 'Saving...' : 'Save & Create Course'}
        </button>
      </div>
    </div>
  );
}
