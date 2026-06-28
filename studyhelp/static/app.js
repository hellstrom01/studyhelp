const API = '';
let USER_ID = null;
let currentSession = null;  // { id, queue, index, startTime, pomodoroEnd }
let timerInterval = null;
let breakInterval = null;

// ── Init ─────────────────────────────────────────────

async function init() {
  // Single-user app: reuse stored user or create one
  const stored = localStorage.getItem('studyhelp_user_id');
  if (stored) {
    USER_ID = parseInt(stored);
  } else {
    const res = await api('POST', '/users', { display_name: 'Default User' });
    USER_ID = res.id;
    localStorage.setItem('studyhelp_user_id', USER_ID);
  }

  document.getElementById('home-date').textContent =
    new Date().toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric' });

  setupNav();
  setupManage();
  setupAddItem();
  setupSession();
  loadHome();
}

// ── API helper ───────────────────────────────────────

async function api(method, path, body) {
  const opts = { method, headers: { 'Content-Type': 'application/json' } };
  if (body) opts.body = JSON.stringify(body);
  const res = await fetch(API + path, opts);
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`${res.status}: ${text}`);
  }
  return res.json();
}

function toast(msg) {
  const el = document.createElement('div');
  el.className = 'toast';
  el.textContent = msg;
  document.body.appendChild(el);
  setTimeout(() => el.remove(), 2500);
}

// ── Navigation ───────────────────────────────────────

function setupNav() {
  document.querySelectorAll('nav button').forEach(btn => {
    btn.addEventListener('click', () => showView(btn.dataset.view));
  });
}

function showView(name) {
  document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
  document.querySelectorAll('nav button').forEach(b => b.classList.remove('active'));

  document.getElementById(`view-${name}`).classList.add('active');
  const navBtn = document.querySelector(`nav button[data-view="${name}"]`);
  if (navBtn) navBtn.classList.add('active');

  document.querySelector('nav').classList.remove('hidden');

  if (name === 'home') loadHome();
  if (name === 'manage') loadSubjects();
  if (name === 'add') loadItemForm();
}

// ── HOME ─────────────────────────────────────────────

async function loadHome() {
  try {
    const counts = await api('GET', `/users/${USER_ID}/sessions/due`);

    document.getElementById('stat-reviews').textContent = counts.reviews_due;
    document.getElementById('stat-new').textContent = counts.new_available;
    document.getElementById('stat-calibration').textContent = '-';

    const total = counts.reviews_due + counts.new_available;
    const btn = document.getElementById('btn-start-session');
    const empty = document.getElementById('home-empty');

    if (total > 0) {
      btn.disabled = false;
      btn.textContent = `Start Session (${total} items)`;
      empty.classList.add('hidden');
    } else {
      btn.disabled = true;
      btn.textContent = 'No items to study';
      empty.classList.remove('hidden');
    }
    currentSession = null;
  } catch (e) {
    document.getElementById('stat-reviews').textContent = '0';
    document.getElementById('stat-new').textContent = '0';
    document.getElementById('home-empty').classList.remove('hidden');
  }
}

// ── MANAGE ───────────────────────────────────────────

let selectedSubjectId = null;

function setupManage() {
  document.getElementById('btn-add-subject').addEventListener('click', addSubject);
  document.getElementById('btn-add-topic').addEventListener('click', addTopic);
}

async function loadSubjects() {
  const subjects = await api('GET', `/users/${USER_ID}/subjects`);
  const list = document.getElementById('subject-list');

  if (subjects.length === 0) {
    list.innerHTML = '<p class="empty">No subjects yet. Create one below.</p>';
    document.getElementById('topic-section').classList.add('hidden');
    return;
  }

  list.innerHTML = subjects.map(s => `
    <div class="list-item" data-id="${s.id}">
      <span class="name">${esc(s.name)}</span>
      <span class="detail">${s.type}</span>
    </div>
  `).join('');

  list.querySelectorAll('.list-item').forEach(el => {
    el.addEventListener('click', () => selectSubject(el.dataset.id, subjects));
  });

  if (selectedSubjectId) {
    selectSubject(selectedSubjectId, subjects);
  }
}

async function selectSubject(id, subjects) {
  selectedSubjectId = parseInt(id);
  const subj = subjects.find(s => s.id === selectedSubjectId);
  if (!subj) return;

  document.getElementById('topic-section').classList.remove('hidden');
  document.getElementById('topic-section-title').textContent = `Topics in ${subj.name}`;

  document.querySelectorAll('#subject-list .list-item').forEach(el => {
    el.style.borderColor = parseInt(el.dataset.id) === selectedSubjectId ? 'var(--accent)' : '';
  });

  const topics = await api('GET', `/users/${USER_ID}/subjects/${id}/topics`);
  const tl = document.getElementById('topic-list');

  if (topics.length === 0) {
    tl.innerHTML = '<p class="empty">No topics yet.</p>';
  } else {
    tl.innerHTML = topics.map(t => `
      <div class="list-item">
        <span class="name">${esc(t.name)}</span>
      </div>
    `).join('');
  }
}

async function addSubject() {
  const name = document.getElementById('subject-name').value.trim();
  const type = document.getElementById('subject-type').value;
  if (!name) return;

  await api('POST', `/users/${USER_ID}/subjects`, { name, type });
  document.getElementById('subject-name').value = '';
  toast('Subject created');
  loadSubjects();
}

async function addTopic() {
  if (!selectedSubjectId) return;
  const name = document.getElementById('topic-name').value.trim();
  if (!name) return;

  await api('POST', `/users/${USER_ID}/subjects/${selectedSubjectId}/topics`, { name });
  document.getElementById('topic-name').value = '';
  toast('Topic created');
  loadSubjects();
  loadItemForm();
}

// ── ADD ITEMS ────────────────────────────────────────

function setupAddItem() {
  const typeSelect = document.getElementById('item-type');
  typeSelect.addEventListener('change', () => {
    document.getElementById('steps-group').classList.toggle('hidden', typeSelect.value !== 'WORKED_EXAMPLE');
  });
  // Initial state
  document.getElementById('steps-group').classList.add('hidden');

  document.getElementById('item-subject').addEventListener('change', loadTopicsForItem);
  document.getElementById('btn-add-item').addEventListener('click', addItem);
}

async function loadItemForm() {
  const subjects = await api('GET', `/users/${USER_ID}/subjects`);
  const sel = document.getElementById('item-subject');
  sel.innerHTML = '<option value="">Select subject...</option>' +
    subjects.map(s => `<option value="${s.id}">${esc(s.name)}</option>`).join('');
  document.getElementById('item-topic').innerHTML = '<option value="">Select topic...</option>';
}

async function loadTopicsForItem() {
  const subjId = document.getElementById('item-subject').value;
  const sel = document.getElementById('item-topic');
  if (!subjId) {
    sel.innerHTML = '<option value="">Select topic...</option>';
    return;
  }
  const topics = await api('GET', `/users/${USER_ID}/subjects/${subjId}/topics`);
  sel.innerHTML = '<option value="">Select topic...</option>' +
    topics.map(t => `<option value="${t.id}">${esc(t.name)}</option>`).join('');
}

async function addItem() {
  const topicId = document.getElementById('item-topic').value;
  if (!topicId) { toast('Select a topic first'); return; }

  const type = document.getElementById('item-type').value;
  const front = document.getElementById('item-front').value.trim();
  const back = document.getElementById('item-back').value.trim();
  if (!front) { toast('Front is required'); return; }

  const body = { type, front, back };

  if (type === 'WORKED_EXAMPLE') {
    const stepsText = document.getElementById('item-steps').value.trim();
    if (stepsText) {
      body.worked_steps = stepsText.split('\n').filter(s => s.trim());
    }
  }

  await api('POST', `/topics/${topicId}/items`, body);
  document.getElementById('item-front').value = '';
  document.getElementById('item-back').value = '';
  document.getElementById('item-steps').value = '';
  toast('Item added');
}

// ── SESSION PLAYER ───────────────────────────────────

let itemShownAt = 0;

function setupSession() {
  document.getElementById('btn-start-session').addEventListener('click', startSession);
  document.getElementById('btn-reveal').addEventListener('click', revealAnswer);
  document.getElementById('btn-end-session').addEventListener('click', endSessionEarly);
  document.getElementById('btn-go-home').addEventListener('click', () => showView('home'));
  document.getElementById('btn-skip-break').addEventListener('click', endBreak);

  document.querySelectorAll('#rating-buttons .btn').forEach(btn => {
    btn.addEventListener('click', () => submitRating(btn.dataset.rating));
  });
}

async function startSession() {
  const btn = document.getElementById('btn-start-session');
  btn.disabled = true;
  btn.textContent = 'Loading...';

  try {
    const queue = await api('POST', `/users/${USER_ID}/sessions`);
    if (queue.items.length === 0) {
      toast('No items to study');
      btn.disabled = false;
      btn.textContent = 'No items to study';
      return;
    }

    currentSession = {
      id: queue.session_id,
      queue: queue.items,
      index: 0,
      startTime: Date.now(),
      pomodoroEnd: Date.now() + 25 * 60 * 1000,
      pomodorosCompleted: 0,
      reviewCount: 0,
      correctCount: 0,
      totalMs: 0,
    };

    showView('session');
    document.querySelector('nav').classList.add('hidden');
    startTimer();
    showCurrentItem();
  } catch (e) {
    toast('Failed to start session');
    btn.disabled = false;
  }
}

function startTimer() {
  clearInterval(timerInterval);
  timerInterval = setInterval(updateTimer, 1000);
  updateTimer();
}

function updateTimer() {
  if (!currentSession) return;
  const remaining = Math.max(0, currentSession.pomodoroEnd - Date.now());
  const mins = Math.floor(remaining / 60000);
  const secs = Math.floor((remaining % 60000) / 1000);
  const el = document.getElementById('session-timer');
  el.textContent = `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;

  if (remaining <= 5 * 60 * 1000) el.classList.add('warning');
  else el.classList.remove('warning');

  if (remaining === 0) {
    clearInterval(timerInterval);
    startBreak();
  }
}

function startBreak() {
  const breakMin = 5;
  const overlay = document.getElementById('break-overlay');
  overlay.classList.add('active');
  let breakEnd = Date.now() + breakMin * 60 * 1000;

  clearInterval(breakInterval);
  breakInterval = setInterval(() => {
    const rem = Math.max(0, breakEnd - Date.now());
    const m = Math.floor(rem / 60000);
    const s = Math.floor((rem % 60000) / 1000);
    document.getElementById('break-timer').textContent =
      `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
    if (rem === 0) endBreak();
  }, 1000);
}

function endBreak() {
  clearInterval(breakInterval);
  document.getElementById('break-overlay').classList.remove('active');

  if (!currentSession) return;
  currentSession.pomodorosCompleted = (currentSession.pomodorosCompleted || 0) + 1;
  // Start a new pomodoro
  currentSession.pomodoroEnd = Date.now() + 25 * 60 * 1000;
  startTimer();
}

function showCurrentItem() {
  const s = currentSession;
  if (s.index >= s.queue.length) {
    finishSession();
    return;
  }

  const item = s.queue[s.index];
  itemShownAt = Date.now();

  // Progress
  document.getElementById('session-progress').textContent =
    `${s.index + 1} / ${s.queue.length}`;

  // Meta tags
  const meta = document.getElementById('session-meta');
  meta.innerHTML = `
    <span class="tag">${esc(item.subject_name)}</span>
    <span class="tag">${esc(item.topic_name)}</span>
    <span class="tag">${formatType(item.type)}</span>
    ${item.is_new ? '<span class="tag new">New</span>' : ''}
  `;

  // Prompt
  document.getElementById('session-prompt').textContent = item.front;

  // Worked steps (faded)
  const stepsEl = document.getElementById('session-steps');
  if (item.worked_steps && item.worked_steps.length > 0) {
    const reveal = item.steps_to_reveal ?? item.worked_steps.length;
    stepsEl.innerHTML = item.worked_steps.map((step, i) => {
      if (i < reveal) {
        return `<div class="worked-step">${esc(step)}</div>`;
      }
      return `<div class="worked-step hidden">Step ${i + 1}: Try to recall this step</div>`;
    }).join('');
  } else {
    stepsEl.innerHTML = '';
  }

  // Reset answer/buttons
  document.getElementById('session-answer').classList.add('hidden');
  document.getElementById('session-answer').innerHTML = '';
  document.getElementById('btn-reveal').classList.remove('hidden');
  document.getElementById('rating-buttons').classList.add('hidden');
  document.getElementById('session-item').classList.remove('hidden');
  document.getElementById('session-done').classList.add('hidden');
}

async function revealAnswer() {
  const s = currentSession;
  const item = s.queue[s.index];

  const data = await api('GET', `/users/${USER_ID}/sessions/${s.id}/reveal/${item.item_id}`);

  const answerEl = document.getElementById('session-answer');
  let html = `<div class="item-answer">${esc(data.back)}</div>`;

  // Show all worked steps on reveal
  if (data.worked_steps && data.worked_steps.length > 0) {
    html += data.worked_steps.map((step, i) =>
      `<div class="worked-step">${esc(step)}</div>`
    ).join('');
  }
  answerEl.innerHTML = html;
  answerEl.classList.remove('hidden');

  document.getElementById('btn-reveal').classList.add('hidden');
  document.getElementById('rating-buttons').classList.remove('hidden');
}

async function submitRating(rating) {
  const s = currentSession;
  const item = s.queue[s.index];
  const responseMs = Date.now() - itemShownAt;

  const wasCorrect = rating !== 'AGAIN';

  await api('POST', `/users/${USER_ID}/sessions/${s.id}/reviews/${item.item_id}`, {
    rating,
    was_correct: wasCorrect,
    response_ms: responseMs,
  });

  s.reviewCount++;
  if (wasCorrect) s.correctCount++;
  s.totalMs += responseMs;

  s.index++;
  showCurrentItem();
}

async function finishSession() {
  clearInterval(timerInterval);
  const s = currentSession;

  const result = await api('POST', `/users/${USER_ID}/sessions/${s.id}/end`);

  document.getElementById('session-item').classList.add('hidden');
  document.getElementById('session-done').classList.remove('hidden');

  const avgTime = s.reviewCount > 0 ? Math.round(s.totalMs / s.reviewCount / 1000) : 0;
  const accuracy = s.reviewCount > 0 ? Math.round(s.correctCount / s.reviewCount * 100) : 0;
  const calibration = result.avg_calibration_error != null
    ? (result.avg_calibration_error * 100).toFixed(1) + '%'
    : '-';

  document.getElementById('session-summary').innerHTML = `
    <div class="summary-stat"><span>Items reviewed</span><span class="val">${result.items_seen}</span></div>
    <div class="summary-stat"><span>Accuracy</span><span class="val">${accuracy}%</span></div>
    <div class="summary-stat"><span>Avg response time</span><span class="val">${avgTime}s</span></div>
    <div class="summary-stat"><span>Calibration error</span><span class="val">${calibration}</span></div>
    <div class="summary-stat"><span>Pomodoros</span><span class="val">${s.pomodorosCompleted || 0}</span></div>
  `;
}

async function endSessionEarly() {
  if (!currentSession) return;
  await finishSession();
}

// ── Helpers ──────────────────────────────────────────

function esc(str) {
  const d = document.createElement('div');
  d.textContent = str || '';
  return d.innerHTML;
}

function formatType(type) {
  const map = {
    CONCEPT_QA: 'Concept Q&A',
    THEOREM_TRIGGER: 'Theorem/Rule',
    WORKED_EXAMPLE: 'Worked Example',
    PROBLEM_HIDDEN: 'Problem',
    CODE_FROM_SCRATCH: 'Code',
    FEYNMAN_PROMPT: 'Explain',
    CLOZE: 'Cloze',
  };
  return map[type] || type;
}

// ── Boot ─────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', init);
