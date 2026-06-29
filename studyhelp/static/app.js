const API = '';
let USER_ID = null;
let currentSession = null;
let timerInterval = null;
let breakInterval = null;
let subjectsCache = [];
let activeSubjectId = null;
let activeTopicId = null;
let chatMessages = [];

// ── Init ─────────────────────────────────────────────

async function init() {
  const stored = localStorage.getItem('studyhelp_user_id');
  if (stored) {
    try {
      await api('GET', `/users/${stored}/subjects`);
      USER_ID = parseInt(stored);
    } catch {
      localStorage.removeItem('studyhelp_user_id');
    }
  }
  if (!USER_ID) {
    const res = await api('POST', '/users', { display_name: 'Default User' });
    USER_ID = res.id;
    localStorage.setItem('studyhelp_user_id', USER_ID);
  }

  document.getElementById('study-date').textContent =
    new Date().toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric' });

  setupEventListeners();
  await refreshSidebar();
  showView('study');
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

function setupEventListeners() {
  // Sidebar nav
  document.querySelector('.nav-item[data-view="study"]')
    .addEventListener('click', () => showView('study'));
  document.querySelector('.nav-item[data-view="add-course"]')
    .addEventListener('click', () => showView('add-course'));

  // Add course
  document.getElementById('btn-add-subject').addEventListener('click', addSubject);

  // Course view
  document.getElementById('btn-add-topic').addEventListener('click', addTopic);
  document.getElementById('btn-study-course').addEventListener('click', () => {
    if (activeSubjectId) startChatSession(activeSubjectId, null);
  });

  // Topic view
  document.getElementById('btn-back-to-course').addEventListener('click', () => {
    if (activeSubjectId) showCourse(activeSubjectId);
  });
  document.getElementById('btn-add-item').addEventListener('click', addItem);
  document.getElementById('item-type').addEventListener('change', (e) => {
    document.getElementById('steps-group').classList.toggle('hidden', e.target.value !== 'WORKED_EXAMPLE');
  });

  // Session (chat)
  document.getElementById('btn-end-session').addEventListener('click', endSessionEarly);
  document.getElementById('btn-go-home').addEventListener('click', () => showView('study'));
  document.getElementById('btn-skip-break').addEventListener('click', endBreak);
  document.getElementById('btn-send').addEventListener('click', sendMessage);

  // Send on Enter (Shift+Enter for newline)
  document.getElementById('chat-input').addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });
}

function showView(name) {
  document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
  document.getElementById(`view-${name}`).classList.add('active');

  const sidebar = document.getElementById('sidebar');
  const main = document.getElementById('main');

  if (name === 'session') {
    sidebar.classList.add('hidden');
    main.classList.add('full');
  } else {
    sidebar.classList.remove('hidden');
    main.classList.remove('full');
  }

  // Highlight sidebar
  document.querySelectorAll('.nav-item, .nav-subject').forEach(el => el.classList.remove('active'));
  const navBtn = document.querySelector(`.nav-item[data-view="${name}"]`);
  if (navBtn) navBtn.classList.add('active');

  if (name === 'study') loadStudy();
  if (name === 'add-course') document.getElementById('subject-name').focus();
}

// ── Sidebar ──────────────────────────────────────────

async function refreshSidebar() {
  try {
    subjectsCache = await api('GET', `/users/${USER_ID}/subjects`);
  } catch {
    subjectsCache = [];
  }

  const container = document.getElementById('sidebar-subjects');
  if (subjectsCache.length === 0) {
    container.innerHTML = '<div class="nav-empty">No courses yet</div>';
    return;
  }

  container.innerHTML = subjectsCache.map(s => `
    <button class="nav-subject" data-subject-id="${s.id}">
      <span class="dot" style="background: ${esc(s.color)}"></span>
      <span class="subject-name">${esc(s.name)}</span>
    </button>
  `).join('');

  container.querySelectorAll('.nav-subject').forEach(btn => {
    btn.addEventListener('click', () => {
      const id = parseInt(btn.dataset.subjectId);
      showCourse(id);
    });
  });
}

// ── Study view ───────────────────────────────────────

async function loadStudy() {
  await refreshSidebar();

  try {
    const counts = await api('GET', `/users/${USER_ID}/sessions/due`);
    document.getElementById('stat-reviews').textContent = counts.reviews_due;
    document.getElementById('stat-new').textContent = counts.new_available;
    document.getElementById('stat-calibration').textContent = '-';
  } catch {
    document.getElementById('stat-reviews').textContent = '0';
    document.getElementById('stat-new').textContent = '0';
  }

  const empty = document.getElementById('study-empty');

  // Show per-subject cards
  const container = document.getElementById('study-subjects');
  if (subjectsCache.length === 0) {
    container.innerHTML = '';
    empty.classList.remove('hidden');
    return;
  }

  empty.classList.add('hidden');
  container.innerHTML = '<h3 style="margin-bottom: 12px; margin-top: 8px;">Your Courses</h3>' +
    subjectsCache.map(s => `
      <div class="study-subject-card" data-subject-id="${s.id}">
        <div class="study-subject-info">
          <span class="dot" style="background: ${esc(s.color)}"></span>
          <span class="name">${esc(s.name)}</span>
        </div>
        <div class="counts">
          <span>${esc(s.type)}</span>
        </div>
      </div>
    `).join('');

  container.querySelectorAll('.study-subject-card').forEach(card => {
    card.addEventListener('click', () => showCourse(parseInt(card.dataset.subjectId)));
  });
}

// ── Course view ──────────────────────────────────────

async function showCourse(subjectId) {
  activeSubjectId = subjectId;
  const subj = subjectsCache.find(s => s.id === subjectId);
  if (!subj) return;

  showView('course');

  // Highlight in sidebar
  document.querySelectorAll('.nav-subject').forEach(el => {
    el.classList.toggle('active', parseInt(el.dataset.subjectId) === subjectId);
  });

  document.getElementById('course-title').textContent = subj.name;
  document.getElementById('course-type').textContent = subj.type;

  const topics = await api('GET', `/users/${USER_ID}/subjects/${subjectId}/topics`);
  const container = document.getElementById('course-topics');

  if (topics.length === 0) {
    container.innerHTML = '<p class="empty">No topics yet. Add one below.</p>';
  } else {
    const topicCards = await Promise.all(topics.map(async (t) => {
      let items = [];
      try { items = await api('GET', `/topics/${t.id}/items`); } catch {}
      return `
        <div class="topic-card" data-topic-id="${t.id}">
          <span class="name">${esc(t.name)}</span>
          <span class="detail">${items.length} item${items.length !== 1 ? 's' : ''}</span>
        </div>
      `;
    }));
    container.innerHTML = topicCards.join('');

    container.querySelectorAll('.topic-card').forEach(card => {
      card.addEventListener('click', () => showTopic(parseInt(card.dataset.topicId)));
    });
  }

  document.getElementById('topic-name').value = '';
}

// ── Topic view (add items) ───────────────────────────

async function showTopic(topicId) {
  activeTopicId = topicId;
  showView('topic');

  const topics = await api('GET', `/users/${USER_ID}/subjects/${activeSubjectId}/topics`);
  const topic = topics.find(t => t.id === topicId);
  document.getElementById('topic-title').textContent = topic ? topic.name : 'Topic';

  await refreshTopicItems();

  document.getElementById('item-front').value = '';
  document.getElementById('item-back').value = '';
  document.getElementById('item-steps').value = '';
  document.getElementById('item-type').value = 'CONCEPT_QA';
  document.getElementById('steps-group').classList.add('hidden');
}

async function refreshTopicItems() {
  const items = await api('GET', `/topics/${activeTopicId}/items`);
  document.getElementById('topic-item-count').textContent = `${items.length} item${items.length !== 1 ? 's' : ''}`;

  const container = document.getElementById('topic-items-list');
  if (items.length === 0) {
    container.innerHTML = '<p class="empty">No items yet. Add your first one below.</p>';
  } else {
    container.innerHTML = items.map(item => `
      <div class="item-card">
        <div class="item-card-type">${formatType(item.type)}</div>
        <div class="item-card-front">${esc(item.front)}</div>
      </div>
    `).join('');
  }
}

// ── Actions ──────────────────────────────────────────

async function addSubject() {
  const name = document.getElementById('subject-name').value.trim();
  const type = document.getElementById('subject-type').value;
  if (!name) return;

  const subj = await api('POST', `/users/${USER_ID}/subjects`, { name, type });
  document.getElementById('subject-name').value = '';
  toast('Course created');
  await refreshSidebar();
  showCourse(subj.id);
}

async function addTopic() {
  if (!activeSubjectId) return;
  const name = document.getElementById('topic-name').value.trim();
  if (!name) return;

  await api('POST', `/users/${USER_ID}/subjects/${activeSubjectId}/topics`, { name });
  document.getElementById('topic-name').value = '';
  toast('Topic added');
  showCourse(activeSubjectId);
}

async function addItem() {
  if (!activeTopicId) return;

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

  await api('POST', `/topics/${activeTopicId}/items`, body);
  document.getElementById('item-front').value = '';
  document.getElementById('item-back').value = '';
  document.getElementById('item-steps').value = '';
  toast('Item added');
  await refreshTopicItems();
}

// ── CHAT SESSION ─────────────────────────────────────

async function startChatSession(subjectId, topicId) {
  const subj = subjectsCache.find(s => s.id === subjectId);
  if (!subj) return;

  // Create a session on the backend
  let sessionId = null;
  try {
    const queue = await api('POST', `/users/${USER_ID}/sessions`);
    sessionId = queue.session_id;
  } catch {
    // Session creation is optional — chat still works without it
  }

  currentSession = {
    subjectId,
    topicId,
    sessionId,
    startTime: Date.now(),
    pomodoroEnd: Date.now() + 25 * 60 * 1000,
    pomodorosCompleted: 0,
  };

  chatMessages = [];

  // Set up session UI
  const topicLabel = topicId
    ? (await getTopicName(subjectId, topicId))
    : null;
  document.getElementById('session-topic').textContent =
    subj.name + (topicLabel ? ` > ${topicLabel}` : '');
  document.getElementById('chat-messages').innerHTML = '';
  document.getElementById('chat-input').value = '';
  document.getElementById('session-done').classList.add('hidden');
  document.getElementById('chat-input').disabled = false;
  document.getElementById('btn-send').disabled = false;

  showView('session');
  startTimer();

  // Send initial message to get the tutor started
  await sendInitialMessage();
}

async function getTopicName(subjectId, topicId) {
  try {
    const topics = await api('GET', `/users/${USER_ID}/subjects/${subjectId}/topics`);
    const t = topics.find(t => t.id === topicId);
    return t ? t.name : null;
  } catch {
    return null;
  }
}

async function sendInitialMessage() {
  addChatBubble('thinking', 'Preparing your study session...');

  try {
    const res = await api('POST', `/users/${USER_ID}/chat`, {
      subject_id: currentSession.subjectId,
      topic_id: currentSession.topicId,
      session_id: currentSession.sessionId,
      messages: [],
    });

    removeBubble('thinking');
    chatMessages.push({ role: 'assistant', content: res.reply });
    addChatBubble('tutor', res.reply);
    scrollChat();
  } catch (e) {
    removeBubble('thinking');
    addChatBubble('tutor', 'Failed to connect to the tutor. Check your API key and try again.');
  }
}

async function sendMessage() {
  const input = document.getElementById('chat-input');
  const text = input.value.trim();
  if (!text) return;
  if (!currentSession) return;

  input.value = '';
  input.style.height = 'auto';

  // Add user message
  chatMessages.push({ role: 'user', content: text });
  addChatBubble('user', text);
  scrollChat();

  // Disable input while waiting
  input.disabled = true;
  document.getElementById('btn-send').disabled = true;
  addChatBubble('thinking', 'Thinking...');

  try {
    const res = await api('POST', `/users/${USER_ID}/chat`, {
      subject_id: currentSession.subjectId,
      topic_id: currentSession.topicId,
      session_id: currentSession.sessionId,
      messages: chatMessages,
    });

    removeBubble('thinking');
    chatMessages.push({ role: 'assistant', content: res.reply });
    addChatBubble('tutor', res.reply);
    scrollChat();
  } catch (e) {
    removeBubble('thinking');
    addChatBubble('tutor', 'Something went wrong. Try sending your message again.');
  }

  input.disabled = false;
  document.getElementById('btn-send').disabled = false;
  input.focus();
}

function addChatBubble(type, text) {
  const container = document.getElementById('chat-messages');
  const el = document.createElement('div');
  el.className = `chat-msg ${type}`;
  el.textContent = text;
  if (type === 'thinking') el.dataset.thinking = '1';
  container.appendChild(el);
}

function removeBubble(type) {
  const el = document.querySelector(`.chat-msg[data-${type}]`);
  if (el) el.remove();
}

function scrollChat() {
  const container = document.getElementById('chat-container');
  container.scrollTop = container.scrollHeight;
}

// ── Timer & Breaks ───────────────────────────────────

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
  const overlay = document.getElementById('break-overlay');
  overlay.classList.add('active');
  let breakEnd = Date.now() + 5 * 60 * 1000;

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
  currentSession.pomodoroEnd = Date.now() + 25 * 60 * 1000;
  startTimer();
}

async function endSessionEarly() {
  if (!currentSession) return;
  clearInterval(timerInterval);

  // End session on backend
  if (currentSession.sessionId) {
    try {
      await api('POST', `/users/${USER_ID}/sessions/${currentSession.sessionId}/end`);
    } catch {}
  }

  const elapsed = Math.round((Date.now() - currentSession.startTime) / 60000);
  const msgCount = chatMessages.filter(m => m.role === 'user').length;

  // Show summary
  document.getElementById('chat-input').disabled = true;
  document.getElementById('btn-send').disabled = true;
  document.getElementById('session-done').classList.remove('hidden');
  document.getElementById('session-summary').innerHTML = `
    <div class="summary-stat"><span>Time studied</span><span class="val">${elapsed} min</span></div>
    <div class="summary-stat"><span>Messages exchanged</span><span class="val">${chatMessages.length}</span></div>
    <div class="summary-stat"><span>Your responses</span><span class="val">${msgCount}</span></div>
    <div class="summary-stat"><span>Pomodoros</span><span class="val">${currentSession.pomodorosCompleted || 0}</span></div>
  `;

  currentSession = null;
}

// ── Helpers ──────────────────────────────────────────

function esc(str) {
  const d = document.createElement('div');
  d.textContent = str || '';
  return d.innerHTML;
}

function formatType(type) {
  return {
    CONCEPT_QA: 'Concept Q&A',
    THEOREM_TRIGGER: 'Theorem/Rule',
    WORKED_EXAMPLE: 'Worked Example',
    PROBLEM_HIDDEN: 'Problem',
    CODE_FROM_SCRATCH: 'Code',
    FEYNMAN_PROMPT: 'Explain',
    CLOZE: 'Cloze',
  }[type] || type;
}

// ── Boot ─────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', init);
