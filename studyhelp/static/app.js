const API = '';
let USER_ID = null;
let currentSession = null;
let timerInterval = null;
let breakInterval = null;
let subjectsCache = [];
let activeSubjectId = null;
let activeTopicId = null;

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
  document.querySelector('.nav-item[data-view="insights"]')
    .addEventListener('click', () => showView('insights'));

  // Insights course filter
  document.getElementById('insights-course')
    .addEventListener('change', loadInsights);

  // Add course
  document.getElementById('btn-add-subject').addEventListener('click', addSubject);

  // Course view
  document.getElementById('btn-add-topic').addEventListener('click', addTopic);
  document.getElementById('btn-study-course').addEventListener('click', () => {
    if (activeSubjectId) startStudySession(activeSubjectId);
  });

  // Topic view
  document.getElementById('btn-back-to-course').addEventListener('click', () => {
    if (activeSubjectId) showCourse(activeSubjectId);
  });
  document.getElementById('btn-add-item').addEventListener('click', addItem);
  document.getElementById('item-type').addEventListener('change', (e) => {
    document.getElementById('steps-group').classList.toggle('hidden', e.target.value !== 'WORKED_EXAMPLE');
  });

  // Session (phased study chat + notes)
  document.getElementById('btn-end-session').addEventListener('click', endSessionEarly);
  document.getElementById('btn-go-home').addEventListener('click', () => showView('study'));
  document.getElementById('btn-skip-break').addEventListener('click', endBreak);
  document.getElementById('btn-send').addEventListener('click', sendMessage);
  document.getElementById('btn-start-focus').addEventListener('click', startFocus);
  document.getElementById('btn-finish-session').addEventListener('click', finishSession);

  // Notes panel: debounced autosave, flush on blur, and a keepalive flush when
  // the tab is hidden or closed so a pending edit isn't lost mid-debounce.
  document.getElementById('notes-area').addEventListener('input', scheduleNotesSave);
  document.getElementById('notes-area').addEventListener('blur', flushNotes);
  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'hidden') flushNotes({ keepalive: true });
  });

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
  if (name === 'insights') loadInsights();
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

// ── STUDY SESSION (phased: level check → work ↔ break → wind-down) ──────

const FOCUS_MS = 25 * 60 * 1000;
const BREAK_MS = 5 * 60 * 1000;
const REFLECT_MS = 5 * 60 * 1000;  // final minutes of a work interval

async function startStudySession(subjectId) {
  const subj = subjectsCache.find(s => s.id === subjectId);
  if (!subj) return;

  // Reset UI before the (LLM-backed) start round-trips.
  document.getElementById('session-topic').textContent = subj.name;
  document.getElementById('chat-messages').innerHTML = '';
  document.getElementById('chat-input').value = '';
  document.getElementById('notes-area').value = '';
  document.getElementById('notes-status').textContent = '';
  document.getElementById('session-done').classList.add('hidden');
  document.getElementById('session-active').classList.remove('hidden');
  document.getElementById('session-summary').classList.add('hidden');
  document.getElementById('chat-input').disabled = true;
  document.getElementById('btn-send').disabled = true;

  currentSession = {
    subjectId,
    sessionId: null,
    phase: 'level_check',
    pomodoroEnd: null,
    pomodorosCompleted: 0,
    intervalOpen: false,
    reflectionAnnounced: false,
  };

  setPhase('level_check');
  showView('session');

  addChatBubble('thinking', 'Preparing your study session...');
  try {
    const session = await api('POST', `/users/${USER_ID}/study-sessions`, {
      subject_id: subjectId,
    });
    currentSession.sessionId = session.id;
    removeBubble('thinking');
    // The start response includes the tutor's level-check opener.
    (session.messages || []).forEach(m =>
      addChatBubble(m.role === 'assistant' ? 'tutor' : 'user', m.content));
    scrollChat();
    document.getElementById('chat-input').disabled = false;
    document.getElementById('btn-send').disabled = false;
    document.getElementById('chat-input').focus();
  } catch (e) {
    removeBubble('thinking');
    addChatBubble('tutor', 'Failed to start the session. Check your API key and try again.');
  }
}

function setPhase(phase) {
  if (!currentSession) return;
  currentSession.phase = phase;
  const badge = document.getElementById('phase-badge');
  const label = {
    level_check: 'Level check',
    work: 'Work interval',
    reflection: 'Reflection',
    wind_down: 'Wind-down',
  }[phase] || phase;
  badge.textContent = label;
  badge.className = 'phase-badge' + (phase === 'reflection' ? ' reflection'
    : phase === 'wind_down' ? ' wind-down' : '');

  // The level check is untimed and gates the focus timer.
  const gate = document.getElementById('level-check-gate');
  gate.classList.toggle('hidden', phase !== 'level_check');
  if (phase === 'level_check') {
    const timer = document.getElementById('session-timer');
    timer.textContent = '--:--';
    timer.className = 'timer idle';
  }
}

async function sendMessage() {
  const input = document.getElementById('chat-input');
  const text = input.value.trim();
  if (!text || !currentSession || !currentSession.sessionId) return;

  input.value = '';
  input.style.height = 'auto';
  addChatBubble('user', text);
  scrollChat();

  input.disabled = true;
  document.getElementById('btn-send').disabled = true;
  addChatBubble('thinking', 'Thinking...');

  try {
    const res = await api('POST',
      `/users/${USER_ID}/study-sessions/${currentSession.sessionId}/messages`,
      { phase: currentSession.phase, content: text });
    removeBubble('thinking');
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

// ── Notes autosave ───────────────────────────────────

let notesTimer = null;

function scheduleNotesSave() {
  document.getElementById('notes-status').textContent = 'Saving...';
  clearTimeout(notesTimer);
  notesTimer = setTimeout(flushNotes, 800);
}

async function flushNotes({ keepalive = false } = {}) {
  clearTimeout(notesTimer);
  if (!currentSession || !currentSession.sessionId) return;
  const notes = document.getElementById('notes-area').value;
  const path = `/users/${USER_ID}/study-sessions/${currentSession.sessionId}/notes`;
  try {
    // keepalive lets the write complete even as the tab is unloading.
    await fetch(path, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ notes }),
      keepalive,
    });
    document.getElementById('notes-status').textContent = 'Saved';
  } catch {
    document.getElementById('notes-status').textContent = 'Not saved — will retry';
  }
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

// ── Timer, intervals & breaks ────────────────────────

// The level check gates the timer: the focus clock only starts here.
async function startFocus() {
  if (!currentSession) return;
  await beginInterval();
}

async function beginInterval() {
  if (!currentSession) return;
  try {
    await api('POST',
      `/users/${USER_ID}/study-sessions/${currentSession.sessionId}/interval/start`);
    currentSession.intervalOpen = true;
  } catch {
    // Already open, or a transient error — keep the timer running regardless.
  }
  currentSession.reflectionAnnounced = false;
  currentSession.pomodoroEnd = Date.now() + FOCUS_MS;
  setPhase('work');
  startTimer();
}

async function endOpenInterval() {
  if (!currentSession || !currentSession.intervalOpen) return;
  try {
    await api('POST',
      `/users/${USER_ID}/study-sessions/${currentSession.sessionId}/interval/end`);
  } catch {}
  currentSession.intervalOpen = false;
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
  el.classList.toggle('warning', remaining <= REFLECT_MS);
  el.classList.remove('idle');

  // The closing minutes of a work interval are the reflection.
  if (remaining <= REFLECT_MS && currentSession.phase === 'work'
      && !currentSession.reflectionAnnounced) {
    currentSession.reflectionAnnounced = true;
    setPhase('reflection');
    addChatBubble('system',
      'Reflection time — recap what you just learned. The tutor will probe, not correct.');
    scrollChat();
  }

  if (remaining === 0) {
    clearInterval(timerInterval);
    onIntervalComplete();
  }
}

async function onIntervalComplete() {
  await endOpenInterval();
  startBreak();
}

function startBreak() {
  const overlay = document.getElementById('break-overlay');
  overlay.classList.add('active');
  let breakEnd = Date.now() + BREAK_MS;

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

async function endBreak() {
  clearInterval(breakInterval);
  document.getElementById('break-overlay').classList.remove('active');
  if (!currentSession) return;
  currentSession.pomodorosCompleted = (currentSession.pomodorosCompleted || 0) + 1;
  await beginInterval();  // next work interval
}

// End the session: stop timers, close any open interval, then capture the
// user's wind-down recap before finishing on the server.
async function endSessionEarly() {
  if (!currentSession) return;
  clearInterval(timerInterval);
  clearInterval(breakInterval);
  document.getElementById('break-overlay').classList.remove('active');

  await flushNotes();
  await endOpenInterval();

  setPhase('wind_down');
  document.getElementById('session-active').classList.add('hidden');
  document.getElementById('session-done').classList.remove('hidden');
  document.getElementById('recap-area').focus();
}

async function finishSession() {
  if (!currentSession) return;
  const recap = document.getElementById('recap-area').value.trim();
  document.getElementById('btn-finish-session').disabled = true;

  let session = null;
  try {
    session = await api('POST',
      `/users/${USER_ID}/study-sessions/${currentSession.sessionId}/end`,
      { wind_down_recap: recap });
  } catch {}

  const minutes = session ? Math.round(session.work_seconds / 60) : 0;
  const replies = session
    ? session.messages.filter(m => m.role === 'user').length : 0;
  const summary = document.getElementById('session-summary');
  summary.innerHTML = `
    <div class="summary-stat"><span>Focused time</span><span class="val">${minutes} min</span></div>
    <div class="summary-stat"><span>Your responses</span><span class="val">${replies}</span></div>
    <div class="summary-stat"><span>Pomodoros</span><span class="val">${currentSession.pomodorosCompleted || 0}</span></div>
  `;
  summary.classList.remove('hidden');
  document.getElementById('btn-finish-session').disabled = false;
  currentSession = null;
}

// ── INSIGHTS (calibration) ───────────────────────────

function populateInsightsCourses() {
  const sel = document.getElementById('insights-course');
  const current = sel.value;
  sel.innerHTML = ['<option value="">All courses</option>']
    .concat(subjectsCache.map(s => `<option value="${s.id}">${esc(s.name)}</option>`))
    .join('');
  if ([...sel.options].some(o => o.value === current)) sel.value = current;
}

async function loadInsights() {
  populateInsightsCourses();

  const subjectId = document.getElementById('insights-course').value;
  const qs = subjectId ? `?subject_id=${subjectId}` : '';

  let data;
  try {
    data = await api('GET', `/users/${USER_ID}/insights/calibration${qs}`);
  } catch {
    document.getElementById('insights-charts').classList.add('hidden');
    const empty = document.getElementById('insights-empty');
    empty.classList.remove('hidden');
    empty.textContent = 'Could not load insights.';
    return;
  }

  renderInsights(data);
}

function renderInsights(data) {
  const empty = document.getElementById('insights-empty');
  const charts = document.getElementById('insights-charts');
  const cov = data.coverage;

  // Coverage note is always shown, so the numbers are never a mystery.
  let covText = `${cov.trustworthy_count} trustworthy review${cov.trustworthy_count !== 1 ? 's' : ''} scored`;
  if (cov.excluded_chat_count > 0) {
    covText += ` · ${cov.excluded_chat_count} tutor-chat review${cov.excluded_chat_count !== 1 ? 's' : ''} excluded (recorded before exact attribution)`;
  }
  document.getElementById('insights-coverage').textContent = covText;

  if (!cov.threshold_met) {
    charts.classList.add('hidden');
    empty.classList.remove('hidden');
    const floor = cov.min_trustworthy;
    const need = Math.max(0, floor - cov.trustworthy_count);
    empty.innerHTML =
      `<strong>Not enough data yet.</strong><br>` +
      `Keep studying — calibration needs at least ${floor} scored reviews` +
      (need > 0 ? ` (${need} to go).` : `.`) +
      `<br><span class="subtitle">Tutor-chat answers count once they're tied to a specific due item; ` +
      `only broad questions not linked to an item are left out.</span>`;
    return;
  }

  empty.classList.add('hidden');
  charts.classList.remove('hidden');

  document.getElementById('cal-headline').textContent = fmtPct(data.headline);
  document.getElementById('cal-bias').textContent = fmtSignedPct(data.bias);
  document.getElementById('cal-bias-label').textContent = data.bias_label || 'Bias';
  document.getElementById('cal-count').textContent = cov.trustworthy_count;

  document.getElementById('cal-reliability').innerHTML = svgReliability(data.curve);
  document.getElementById('cal-trend').innerHTML = svgTrend(data.trend);
}

function svgReliability(curve) {
  const S = 300, pad = 34, plot = S - pad * 2;
  const X = v => pad + v * plot;
  const Y = v => pad + (1 - v) * plot;  // invert y

  let g = '';
  for (let i = 0; i <= 5; i++) {
    const t = i / 5;
    g += `<line x1="${X(t)}" y1="${Y(0)}" x2="${X(t)}" y2="${Y(1)}" class="grid"/>`;
    g += `<line x1="${X(0)}" y1="${Y(t)}" x2="${X(1)}" y2="${Y(t)}" class="grid"/>`;
    g += `<text x="${X(t)}" y="${Y(0) + 15}" class="tick" text-anchor="middle">${t.toFixed(1)}</text>`;
    g += `<text x="${X(0) - 6}" y="${Y(t) + 3}" class="tick" text-anchor="end">${t.toFixed(1)}</text>`;
  }

  const diag = `<line x1="${X(0)}" y1="${Y(0)}" x2="${X(1)}" y2="${Y(1)}" class="diagonal"/>`;

  const pts = curve.map(b => {
    const r = Math.min(12, 4 + Math.sqrt(b.n));
    return `<circle cx="${X(b.mean_predicted)}" cy="${Y(b.actual_accuracy)}" r="${r}" class="cal-point">` +
      `<title>Predicted ${Math.round(b.mean_predicted * 100)}% · actual ${Math.round(b.actual_accuracy * 100)}% · n=${b.n}</title>` +
      `</circle>`;
  }).join('');

  const xlab = `<text x="${X(0.5)}" y="${S - 2}" class="axis-label" text-anchor="middle">Predicted recall</text>`;
  const ylab = `<text x="10" y="${Y(0.5)}" class="axis-label" text-anchor="middle" transform="rotate(-90 10 ${Y(0.5)})">Actual accuracy</text>`;

  return `<svg viewBox="0 0 ${S} ${S}" class="cal-svg" preserveAspectRatio="xMidYMid meet" role="img">${g}${diag}${pts}${xlab}${ylab}</svg>`;
}

function svgTrend(trend) {
  const W = 620, H = 200, padL = 44, padR = 16, padT = 16, padB = 34;
  const n = trend.length;
  const maxErr = Math.max(0.5, ...trend.map(p => p.mean_abs_error));
  const X = i => padL + (n <= 1 ? 0.5 : i / (n - 1)) * (W - padL - padR);
  const Y = v => padT + (1 - v / maxErr) * (H - padT - padB);

  let g = '';
  [0, maxErr / 2, maxErr].forEach(t => {
    g += `<line x1="${X(0)}" y1="${Y(t)}" x2="${W - padR}" y2="${Y(t)}" class="grid"/>`;
    g += `<text x="${padL - 6}" y="${Y(t) + 3}" class="tick" text-anchor="end">${Math.round(t * 100)}%</text>`;
  });

  const pointsStr = trend.map((p, i) => `${X(i)},${Y(p.mean_abs_error)}`).join(' ');
  const line = n > 1 ? `<polyline points="${pointsStr}" class="trend-line"/>` : '';
  const dots = trend.map((p, i) =>
    `<circle cx="${X(i)}" cy="${Y(p.mean_abs_error)}" r="3.5" class="trend-dot">` +
    `<title>${esc(p.date)}: ${(p.mean_abs_error * 100).toFixed(1)}% (n=${p.n})</title></circle>`
  ).join('');

  let xlabels = '';
  if (n > 0) {
    xlabels += `<text x="${X(0)}" y="${H - 8}" class="tick" text-anchor="start">${esc(shortDate(trend[0].date))}</text>`;
    if (n > 1) {
      xlabels += `<text x="${X(n - 1)}" y="${H - 8}" class="tick" text-anchor="end">${esc(shortDate(trend[n - 1].date))}</text>`;
    }
  }

  return `<svg viewBox="0 0 ${W} ${H}" class="cal-svg" preserveAspectRatio="xMidYMid meet" role="img">${g}${line}${dots}${xlabels}</svg>`;
}

function shortDate(iso) {
  const d = new Date(iso + 'T00:00:00Z');
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', timeZone: 'UTC' });
}

function fmtPct(v) { return v == null ? '-' : Math.round(v * 100) + '%'; }

function fmtSignedPct(v) {
  if (v == null) return '-';
  return (v >= 0 ? '+' : '−') + Math.round(Math.abs(v) * 100) + '%';
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
