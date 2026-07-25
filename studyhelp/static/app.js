const API = '';
let USER_ID = null;
let subjectsCache = [];
let activeSubjectId = null;

// Study-session state
let study = null;
let studyTimerInterval = null;
let breakInterval = null;
let notesTimer = null;

// Review-session state
let review = null;

const FOCUS_MIN = 25;
const BREAK_MIN = 5;
const REFLECTION_MIN = 5;  // last minutes of a work interval become reflection

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

  document.getElementById('home-date').textContent =
    new Date().toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric' });

  setupEventListeners();
  await refreshSidebar();
  showView('home');
}

// ── API helper ───────────────────────────────────────

async function api(method, path, body) {
  const opts = { method, headers: { 'Content-Type': 'application/json' } };
  if (body !== undefined) opts.body = JSON.stringify(body);
  const res = await fetch(API + path, opts);
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`${res.status}: ${text}`);
  }
  if (res.status === 204) return null;
  const ct = res.headers.get('content-type') || '';
  return ct.includes('application/json') ? res.json() : null;
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
  document.querySelector('.nav-item[data-view="home"]')
    .addEventListener('click', () => showView('home'));
  document.querySelector('.nav-item[data-view="add-subject"]')
    .addEventListener('click', () => showView('add-subject'));
  document.querySelector('.nav-item[data-view="insights"]')
    .addEventListener('click', () => showView('insights'));

  document.getElementById('insights-subject').addEventListener('change', loadInsights);

  document.getElementById('btn-add-subject').addEventListener('click', addSubject);

  // Subject view
  document.getElementById('btn-study-subject').addEventListener('click', () => {
    if (activeSubjectId) startStudySession(activeSubjectId);
  });
  document.getElementById('btn-review-subject').addEventListener('click', () => {
    if (activeSubjectId) startReviewSession(activeSubjectId);
  });
  document.getElementById('btn-toggle-memory').addEventListener('click', toggleMemory);
  document.getElementById('btn-add-item').addEventListener('click', addItem);
  document.getElementById('item-type').addEventListener('change', (e) => {
    document.getElementById('steps-group').classList.toggle('hidden', e.target.value !== 'WORKED_EXAMPLE');
  });

  // Study session
  document.getElementById('btn-study-send').addEventListener('click', sendStudyMessage);
  document.getElementById('study-chat-input').addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendStudyMessage(); }
  });
  document.getElementById('btn-start-focus').addEventListener('click', startFocusTimer);
  document.getElementById('btn-end-study').addEventListener('click', beginWindDown);
  document.getElementById('btn-finish-study').addEventListener('click', finishStudySession);
  document.getElementById('btn-study-home').addEventListener('click', () => showView('home'));
  document.getElementById('study-notes').addEventListener('input', scheduleNotesSave);
  document.getElementById('btn-skip-break').addEventListener('click', endBreak);

  // Review session
  document.getElementById('btn-submit-answer').addEventListener('click', submitAnswer);
  document.getElementById('btn-end-review').addEventListener('click', endReviewSession);
  document.getElementById('btn-review-home').addEventListener('click', () => showView('home'));
  document.querySelectorAll('.grade-buttons .grade').forEach(btn => {
    btn.addEventListener('click', () => gradeItem(btn.dataset.rating));
  });
}

function showView(name) {
  document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
  document.getElementById(`view-${name}`).classList.add('active');

  const sidebar = document.getElementById('sidebar');
  const main = document.getElementById('main');
  if (name === 'study' || name === 'review') {
    sidebar.classList.add('hidden');
    main.classList.add('full');
  } else {
    sidebar.classList.remove('hidden');
    main.classList.remove('full');
  }

  document.querySelectorAll('.nav-item, .nav-subject').forEach(el => el.classList.remove('active'));
  const navBtn = document.querySelector(`.nav-item[data-view="${name}"]`);
  if (navBtn) navBtn.classList.add('active');

  if (name === 'home') loadHome();
  if (name === 'insights') loadInsights();
  if (name === 'add-subject') document.getElementById('subject-name').focus();
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
    container.innerHTML = '<div class="nav-empty">No subjects yet</div>';
    return;
  }

  container.innerHTML = subjectsCache.map(s => `
    <button class="nav-subject" data-subject-id="${s.id}">
      <span class="dot" style="background: ${esc(s.color)}"></span>
      <span class="subject-name">${esc(s.name)}</span>
    </button>
  `).join('');

  container.querySelectorAll('.nav-subject').forEach(btn => {
    btn.addEventListener('click', () => showSubject(parseInt(btn.dataset.subjectId)));
  });
}

// ── Home view ────────────────────────────────────────

async function loadHome() {
  await refreshSidebar();

  try {
    const stats = await api('GET', `/users/${USER_ID}/stats`);
    document.getElementById('stat-streak').textContent = stats.streak_days;
    document.getElementById('stat-hours').textContent = stats.hours_studied;
    document.getElementById('home-heatmap').innerHTML = svgHeatmap(stats.heatmap);
  } catch {
    document.getElementById('stat-streak').textContent = '0';
    document.getElementById('stat-hours').textContent = '0';
  }

  try {
    const counts = await api('GET', `/users/${USER_ID}/review-sessions/due`);
    document.getElementById('stat-reviews').textContent = counts.reviews_due;
  } catch {
    document.getElementById('stat-reviews').textContent = '0';
  }

  const empty = document.getElementById('home-empty');
  const container = document.getElementById('home-subjects');
  if (subjectsCache.length === 0) {
    container.innerHTML = '';
    empty.classList.remove('hidden');
    return;
  }
  empty.classList.add('hidden');
  container.innerHTML = '<h3 style="margin-bottom: 12px; margin-top: 8px;">Your Subjects</h3>' +
    subjectsCache.map(s => `
      <div class="study-subject-card" data-subject-id="${s.id}">
        <div class="study-subject-info">
          <span class="dot" style="background: ${esc(s.color)}"></span>
          <span class="name">${esc(s.name)}</span>
        </div>
        <div class="counts"><span>${esc(s.type)}</span></div>
      </div>
    `).join('');

  container.querySelectorAll('.study-subject-card').forEach(card => {
    card.addEventListener('click', () => showSubject(parseInt(card.dataset.subjectId)));
  });
}

// ── Subject view ─────────────────────────────────────

async function showSubject(subjectId) {
  activeSubjectId = subjectId;
  const subj = subjectsCache.find(s => s.id === subjectId);
  if (!subj) return;

  showView('subject');
  document.querySelectorAll('.nav-subject').forEach(el => {
    el.classList.toggle('active', parseInt(el.dataset.subjectId) === subjectId);
  });

  document.getElementById('subject-title').textContent = subj.name;
  document.getElementById('subject-type').textContent = subj.type;

  const memEl = document.getElementById('subject-memory');
  memEl.classList.add('hidden');
  document.getElementById('btn-toggle-memory').textContent = 'Show';

  try {
    const counts = await api('GET', `/users/${USER_ID}/review-sessions/due?subject_id=${subjectId}`);
    const badge = document.getElementById('subject-due-badge');
    badge.textContent = counts.reviews_due;
    badge.classList.toggle('hidden', counts.reviews_due === 0);
    document.getElementById('subject-due-line').textContent =
      `${counts.reviews_due} due for review · ${counts.new_available} new item${counts.new_available !== 1 ? 's' : ''} available`;
  } catch {}

  try {
    const summaries = await api('GET', `/users/${USER_ID}/subjects/${subjectId}/summaries`);
    const el = document.getElementById('subject-summaries');
    if (!summaries.length) {
      el.innerHTML = '<p class="empty">No study sessions yet.</p>';
    } else {
      el.innerHTML = summaries.map(s => `
        <div class="summary-row">
          <span class="summary-date">${esc(shortDate(s.started_at.slice(0, 10)))}</span>
          <span class="summary-text">${esc(s.summary || '(no summary)')}</span>
        </div>
      `).join('');
    }
  } catch {}

  try {
    const topics = await api('GET', `/users/${USER_ID}/subjects/${subjectId}/topics`);
    const container = document.getElementById('subject-topics');
    if (!topics.length) {
      container.innerHTML = '<p class="empty">No topics yet. Items you add will be filed into topics automatically.</p>';
    } else {
      const cards = await Promise.all(topics.map(async (t) => {
        let items = [];
        try { items = await api('GET', `/topics/${t.id}/items`); } catch {}
        return `<div class="topic-card"><span class="name">${esc(t.name)}</span>
          <span class="detail">${items.length} item${items.length !== 1 ? 's' : ''}</span></div>`;
      }));
      container.innerHTML = cards.join('');
    }
  } catch {}

  document.getElementById('item-front').value = '';
  document.getElementById('item-back').value = '';
  document.getElementById('item-steps').value = '';
  document.getElementById('item-type').value = '';
  document.getElementById('steps-group').classList.add('hidden');
}

async function toggleMemory() {
  const el = document.getElementById('subject-memory');
  const btn = document.getElementById('btn-toggle-memory');
  if (!el.classList.contains('hidden')) {
    el.classList.add('hidden');
    btn.textContent = 'Show';
    return;
  }
  try {
    const mem = await api('GET', `/users/${USER_ID}/subjects/${activeSubjectId}/memory`);
    el.textContent = mem.content || 'The tutor has no notes on you for this subject yet.';
  } catch {
    el.textContent = 'Could not load memory.';
  }
  el.classList.remove('hidden');
  btn.textContent = 'Hide';
}

async function addSubject() {
  const name = document.getElementById('subject-name').value.trim();
  const type = document.getElementById('subject-type-select').value;
  if (!name) return;

  const subj = await api('POST', `/users/${USER_ID}/subjects`, { name, type });
  document.getElementById('subject-name').value = '';
  toast('Subject created');
  await refreshSidebar();
  showSubject(subj.id);
}

async function addItem() {
  if (!activeSubjectId) return;
  const type = document.getElementById('item-type').value;
  const front = document.getElementById('item-front').value.trim();
  const back = document.getElementById('item-back').value.trim();
  if (!front) { toast('Front is required'); return; }

  const body = { front, back };
  if (type) body.type = type;
  if (type === 'WORKED_EXAMPLE') {
    const stepsText = document.getElementById('item-steps').value.trim();
    if (stepsText) body.worked_steps = stepsText.split('\n').filter(s => s.trim());
  }

  try {
    await api('POST', `/users/${USER_ID}/subjects/${activeSubjectId}/items`, body);
    toast('Item added and filed');
    showSubject(activeSubjectId);
  } catch (e) {
    toast('Could not add item');
  }
}

// ══════════ STUDY SESSION ══════════

async function startStudySession(subjectId) {
  const subj = subjectsCache.find(s => s.id === subjectId);
  if (!subj) return;

  study = {
    subjectId, sessionId: null,
    phase: 'level_check',
    intervalOpen: false,
    pomodoroEnd: null,
    finished: false,
  };

  document.getElementById('study-subject-label').textContent = subj.name;
  document.getElementById('study-chat-messages').innerHTML = '';
  document.getElementById('study-chat-input').value = '';
  document.getElementById('study-notes').value = '';
  document.getElementById('notes-status').textContent = '';
  document.getElementById('winddown-recap').value = '';
  document.getElementById('study-timer').textContent = '--:--';
  document.getElementById('study-body').classList.remove('hidden');
  document.getElementById('study-winddown').classList.add('hidden');
  document.getElementById('study-done').classList.add('hidden');
  document.getElementById('levelcheck-bar').classList.remove('hidden');
  setPhase('level_check');

  showView('study');
  addStudyBubble('thinking', 'Starting your level check...');

  try {
    const res = await api('POST', `/users/${USER_ID}/study-sessions`, { subject_id: subjectId });
    study.sessionId = res.id;
    // The tutor's level-check opener is the session's first (assistant) message.
    const opener = (res.messages || []).filter(m => m.role === 'assistant').slice(-1)[0];
    removeStudyBubble('thinking');
    addStudyBubble('tutor', opener ? opener.content : 'Let\'s begin. What are you working on today?');
  } catch (e) {
    removeStudyBubble('thinking');
    addStudyBubble('tutor', 'Failed to reach the tutor. Check your API key and try again.');
  }
}

function setPhase(phase) {
  if (study) study.phase = phase;
  const labels = { level_check: 'Level check', work: 'Focus', reflection: 'Reflection', wind_down: 'Wind-down' };
  document.getElementById('study-phase').textContent = labels[phase] || phase;
}

async function sendStudyMessage() {
  if (!study || !study.sessionId) return;
  const input = document.getElementById('study-chat-input');
  const text = input.value.trim();
  if (!text) return;

  input.value = '';
  addStudyBubble('user', text);
  input.disabled = true;
  document.getElementById('btn-study-send').disabled = true;
  addStudyBubble('thinking', 'Thinking...');

  try {
    const res = await api('POST', `/users/${USER_ID}/study-sessions/${study.sessionId}/messages`,
      { content: text, phase: study.phase });
    removeStudyBubble('thinking');
    addStudyBubble('tutor', res.reply);
  } catch (e) {
    removeStudyBubble('thinking');
    addStudyBubble('tutor', 'Something went wrong. Try again.');
  }
  input.disabled = false;
  document.getElementById('btn-study-send').disabled = false;
  input.focus();
}

async function startFocusTimer() {
  if (!study || !study.sessionId) return;
  document.getElementById('levelcheck-bar').classList.add('hidden');
  setPhase('work');
  await openInterval();
  study.pomodoroEnd = Date.now() + FOCUS_MIN * 60 * 1000;
  runStudyTimer();
  toast('Timer started. Focus.');
}

async function openInterval() {
  if (study.intervalOpen) return;
  try {
    await api('POST', `/users/${USER_ID}/study-sessions/${study.sessionId}/interval/start`);
    study.intervalOpen = true;
  } catch {}
}

async function closeInterval() {
  if (!study.intervalOpen) return;
  try {
    await api('POST', `/users/${USER_ID}/study-sessions/${study.sessionId}/interval/end`);
    study.intervalOpen = false;
  } catch {}
}

function runStudyTimer() {
  clearInterval(studyTimerInterval);
  studyTimerInterval = setInterval(updateStudyTimer, 1000);
  updateStudyTimer();
}

function updateStudyTimer() {
  if (!study || !study.pomodoroEnd) return;
  const remaining = Math.max(0, study.pomodoroEnd - Date.now());
  const mins = Math.floor(remaining / 60000);
  const secs = Math.floor((remaining % 60000) / 1000);
  const el = document.getElementById('study-timer');
  el.textContent = `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;

  // Last minutes of the interval become reflection.
  if (remaining <= REFLECTION_MIN * 60 * 1000) {
    el.classList.add('warning');
    if (study.phase === 'work') {
      setPhase('reflection');
      addStudyBubble('system', 'Reflection time: recap what you just learned in your own words.');
    }
  } else {
    el.classList.remove('warning');
  }

  if (remaining === 0) {
    clearInterval(studyTimerInterval);
    startBreak();
  }
}

async function startBreak() {
  await closeInterval();
  const overlay = document.getElementById('break-overlay');
  overlay.classList.add('active');
  let breakEnd = Date.now() + BREAK_MIN * 60 * 1000;
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
  if (!study || study.finished) return;
  setPhase('work');
  await openInterval();
  study.pomodoroEnd = Date.now() + FOCUS_MIN * 60 * 1000;
  runStudyTimer();
}

function scheduleNotesSave() {
  clearTimeout(notesTimer);
  document.getElementById('notes-status').textContent = 'Saving...';
  notesTimer = setTimeout(saveNotes, 1000);
}

async function saveNotes() {
  if (!study || !study.sessionId) return;
  const notes = document.getElementById('study-notes').value;
  try {
    await api('PUT', `/users/${USER_ID}/study-sessions/${study.sessionId}/notes`, { notes });
    document.getElementById('notes-status').textContent = 'Saved';
  } catch {
    document.getElementById('notes-status').textContent = 'Not saved';
  }
}

async function beginWindDown() {
  if (!study || !study.sessionId) return;
  clearInterval(studyTimerInterval);
  await closeInterval();
  await saveNotes();
  setPhase('wind_down');
  document.getElementById('study-body').classList.add('hidden');
  document.getElementById('study-winddown').classList.remove('hidden');
}

async function finishStudySession() {
  if (!study || !study.sessionId) return;
  study.finished = true;
  const recap = document.getElementById('winddown-recap').value.trim();
  const btn = document.getElementById('btn-finish-study');
  btn.disabled = true;
  btn.textContent = 'Summarizing...';

  document.getElementById('study-winddown').classList.add('hidden');
  document.getElementById('study-done').classList.remove('hidden');
  document.getElementById('study-summary-text').textContent = 'Writing your summary...';

  try {
    const res = await api('POST', `/users/${USER_ID}/study-sessions/${study.sessionId}/end`, { wind_down_recap: recap });
    document.getElementById('study-summary-text').textContent = res.summary || '(no summary)';
  } catch {
    document.getElementById('study-summary-text').textContent = 'Could not write a summary.';
  }
  btn.disabled = false;
  btn.textContent = 'Finish & summarize';

  loadDrafts();
}

async function loadDrafts() {
  const list = document.getElementById('drafts-list');
  list.innerHTML = '<p class="empty">Generating suggestions...</p>';
  let drafts = [];
  try {
    const res = await api('POST', `/users/${USER_ID}/study-sessions/${study.sessionId}/drafts`);
    drafts = res.drafts || [];
  } catch {
    list.innerHTML = '<p class="empty">Could not generate card suggestions.</p>';
    return;
  }
  if (!drafts.length) {
    list.innerHTML = '<p class="empty">No cards suggested from this session.</p>';
    return;
  }
  list.innerHTML = drafts.map((d, i) => `
    <div class="draft" data-i="${i}">
      <div class="form-group"><label>Front</label>
        <textarea class="draft-front" rows="2">${esc(d.front)}</textarea></div>
      <div class="form-group"><label>Back</label>
        <textarea class="draft-back" rows="2">${esc(d.back)}</textarea></div>
      <div class="draft-actions">
        <span class="draft-type">${formatType(d.type)}</span>
        <button class="btn btn-primary btn-sm draft-accept">Accept</button>
        <button class="btn btn-ghost btn-sm draft-reject">Reject</button>
      </div>
    </div>`).join('');

  list.querySelectorAll('.draft').forEach(el => {
    const type = drafts[parseInt(el.dataset.i)].type;
    el.querySelector('.draft-accept').addEventListener('click', () => acceptDraft(el, type));
    el.querySelector('.draft-reject').addEventListener('click', () => el.remove());
  });
}

async function acceptDraft(el, type) {
  const front = el.querySelector('.draft-front').value.trim();
  const back = el.querySelector('.draft-back').value.trim();
  if (!front) { toast('Front is required'); return; }
  const btn = el.querySelector('.draft-accept');
  btn.disabled = true;
  try {
    await api('POST', `/users/${USER_ID}/study-sessions/${study.sessionId}/drafts/accept`,
      { front, back, type });
    el.classList.add('accepted');
    el.querySelector('.draft-actions').innerHTML = '<span class="draft-type">Added to deck ✓</span>';
  } catch {
    toast('Could not add card');
    btn.disabled = false;
  }
}

// Study chat bubbles
function addStudyBubble(type, text) {
  const container = document.getElementById('study-chat-messages');
  const el = document.createElement('div');
  el.className = `chat-msg ${type}`;
  el.textContent = text;
  if (type === 'thinking') el.dataset.thinking = '1';
  container.appendChild(el);
  const c = document.getElementById('study-chat-container');
  c.scrollTop = c.scrollHeight;
}
function removeStudyBubble(type) {
  const el = document.querySelector(`#study-chat-messages .chat-msg[data-${type}]`);
  if (el) el.remove();
}

// ══════════ REVIEW SESSION ══════════

async function startReviewSession(subjectId) {
  const subj = subjectsCache.find(s => s.id === subjectId);
  if (!subj) return;

  let queue;
  try {
    queue = await api('POST', `/users/${USER_ID}/review-sessions`, { subject_id: subjectId });
  } catch {
    toast('Could not start review session');
    return;
  }
  if (!queue.items.length) {
    toast('Nothing due to review right now');
    return;
  }

  review = { sessionId: queue.session_id, items: queue.items, index: 0, reviewed: 0, current: null };
  document.getElementById('review-subject-label').textContent = subj.name;
  document.getElementById('review-body').classList.remove('hidden');
  document.getElementById('review-done').classList.add('hidden');

  showView('review');
  presentItem();
}

function presentItem() {
  const item = review.items[review.index];
  review.current = { item, typed: '', commentary: '' };

  document.getElementById('review-progress').textContent =
    `${review.index + 1} / ${review.items.length}`;
  document.getElementById('review-item-type').textContent = formatType(item.type);
  document.getElementById('review-front').textContent = item.front;

  // Worked-example step fading (steps_to_reveal from the server)
  const stepsEl = document.getElementById('review-steps');
  if (item.worked_steps && item.steps_to_reveal > 0) {
    stepsEl.innerHTML = item.worked_steps.slice(0, item.steps_to_reveal)
      .map((s, i) => `<div class="step">${i + 1}. ${esc(s)}</div>`).join('');
  } else {
    stepsEl.innerHTML = '';
  }

  document.getElementById('review-answer').value = '';
  document.getElementById('review-attempt-area').classList.remove('hidden');
  document.getElementById('review-reveal-area').classList.add('hidden');
  document.getElementById('btn-submit-answer').disabled = false;
  document.getElementById('review-answer').focus();
}

async function submitAnswer() {
  if (!review || !review.current) return;
  const typed = document.getElementById('review-answer').value.trim();
  review.current.typed = typed;

  document.getElementById('btn-submit-answer').disabled = true;
  document.getElementById('review-commentary').textContent = 'Checking your answer...';
  document.getElementById('review-answer-reveal').textContent = '';
  document.getElementById('review-attempt-area').classList.add('hidden');
  document.getElementById('review-reveal-area').classList.remove('hidden');

  const item = review.current.item;
  try {
    const res = await api('POST', `/users/${USER_ID}/review-sessions/${review.sessionId}/commentary`,
      { item_id: item.item_id, typed_answer: typed });
    review.current.commentary = res.commentary;
    document.getElementById('review-commentary').textContent = res.commentary;
    document.getElementById('review-answer-reveal').textContent = res.answer || '(no stored answer)';
  } catch {
    document.getElementById('review-commentary').textContent = 'Could not get feedback — rate yourself from memory.';
    document.getElementById('review-answer-reveal').textContent = item.back || '';
  }
}

async function gradeItem(rating) {
  if (!review || !review.current) return;
  const item = review.current.item;
  document.querySelectorAll('.grade-buttons .grade').forEach(b => b.disabled = true);

  try {
    await api('POST', `/users/${USER_ID}/review-sessions/${review.sessionId}/rate`, {
      item_id: item.item_id,
      rating,
      typed_answer: review.current.typed,
      commentary: review.current.commentary,
    });
    review.reviewed++;
  } catch {
    toast('Could not save rating');
  }
  document.querySelectorAll('.grade-buttons .grade').forEach(b => b.disabled = false);

  review.index++;
  if (review.index >= review.items.length) {
    finishReview();
  } else {
    presentItem();
  }
}

function endReviewSession() {
  if (!review) return;
  finishReview();
}

async function finishReview() {
  const reviewed = review ? review.reviewed : 0;
  if (review && review.sessionId) {
    try { await api('POST', `/users/${USER_ID}/review-sessions/${review.sessionId}/end`); } catch {}
  }
  document.getElementById('review-body').classList.add('hidden');
  document.getElementById('review-done').classList.remove('hidden');
  document.getElementById('review-summary').innerHTML = `
    <div class="summary-stat"><span>Items reviewed</span><span class="val">${reviewed}</span></div>
  `;
  review = null;
}

// ══════════ INSIGHTS ══════════

function populateInsightsSubjects() {
  const sel = document.getElementById('insights-subject');
  const current = sel.value;
  sel.innerHTML = ['<option value="">All subjects</option>']
    .concat(subjectsCache.map(s => `<option value="${s.id}">${esc(s.name)}</option>`))
    .join('');
  if ([...sel.options].some(o => o.value === current)) sel.value = current;
}

async function loadInsights() {
  await refreshSidebar();
  populateInsightsSubjects();

  const subjectId = document.getElementById('insights-subject').value;
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

  let covText = `${cov.trustworthy_count} trustworthy review${cov.trustworthy_count !== 1 ? 's' : ''} scored`;
  if (cov.excluded_chat_count > 0) {
    covText += ` · ${cov.excluded_chat_count} legacy tutor-chat review${cov.excluded_chat_count !== 1 ? 's' : ''} excluded`;
  }
  document.getElementById('insights-coverage').textContent = covText;

  if (!cov.threshold_met) {
    charts.classList.add('hidden');
    empty.classList.remove('hidden');
    const floor = cov.min_trustworthy;
    const need = Math.max(0, floor - cov.trustworthy_count);
    empty.innerHTML =
      `<strong>Not enough data yet.</strong><br>` +
      `Run review sessions — calibration needs at least ${floor} scored reviews` +
      (need > 0 ? ` (${need} to go).` : `.`);
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

// ── Charts (inline SVG, no libraries) ────────────────

function svgHeatmap(days) {
  if (!days || !days.length) return '<p class="empty">No study time logged yet.</p>';
  const byDate = {};
  let max = 1;
  days.forEach(d => { byDate[d.date] = d.minutes; max = Math.max(max, d.minutes); });

  const WEEKS = 16, cell = 14, gap = 3;
  const today = new Date();
  const end = new Date(Date.UTC(today.getUTCFullYear(), today.getUTCMonth(), today.getUTCDate()));
  const start = new Date(end);
  start.setUTCDate(start.getUTCDate() - (WEEKS * 7 - 1));
  start.setUTCDate(start.getUTCDate() - start.getUTCDay());  // align to Sunday

  let cells = '';
  let cols = 0;
  for (let d = new Date(start); d <= end; d.setUTCDate(d.getUTCDate() + 1)) {
    const iso = d.toISOString().slice(0, 10);
    const col = Math.floor((d - start) / (7 * 86400000));
    const row = d.getUTCDay();
    cols = Math.max(cols, col + 1);
    const mins = byDate[iso] || 0;
    const level = mins === 0 ? 0 : Math.min(4, Math.ceil((mins / max) * 4));
    const x = col * (cell + gap), y = row * (cell + gap);
    cells += `<rect x="${x}" y="${y}" width="${cell}" height="${cell}" rx="3" class="heat heat-${level}">` +
      `<title>${iso}: ${mins} min</title></rect>`;
  }
  const W = cols * (cell + gap), H = 7 * (cell + gap);
  return `<svg viewBox="0 0 ${W} ${H}" class="heat-svg" preserveAspectRatio="xMinYMin meet" role="img">${cells}</svg>`;
}

function svgReliability(curve) {
  const S = 300, pad = 34, plot = S - pad * 2;
  const X = v => pad + v * plot;
  const Y = v => pad + (1 - v) * plot;
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
      `<title>Predicted ${Math.round(b.mean_predicted * 100)}% · actual ${Math.round(b.actual_accuracy * 100)}% · n=${b.n}</title></circle>`;
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
    if (n > 1) xlabels += `<text x="${X(n - 1)}" y="${H - 8}" class="tick" text-anchor="end">${esc(shortDate(trend[n - 1].date))}</text>`;
  }
  return `<svg viewBox="0 0 ${W} ${H}" class="cal-svg" preserveAspectRatio="xMidYMid meet" role="img">${g}${line}${dots}${xlabels}</svg>`;
}

// ── Helpers ──────────────────────────────────────────

function shortDate(iso) {
  const d = new Date(iso + 'T00:00:00Z');
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', timeZone: 'UTC' });
}
function fmtPct(v) { return v == null ? '-' : Math.round(v * 100) + '%'; }
function fmtSignedPct(v) {
  if (v == null) return '-';
  return (v >= 0 ? '+' : '−') + Math.round(Math.abs(v) * 100) + '%';
}
function esc(str) {
  const d = document.createElement('div');
  d.textContent = str || '';
  return d.innerHTML;
}
function formatType(type) {
  return {
    CONCEPT_QA: 'Concept Q&A', THEOREM_TRIGGER: 'Theorem/Rule',
    WORKED_EXAMPLE: 'Worked Example', PROBLEM_HIDDEN: 'Problem',
    CODE_FROM_SCRATCH: 'Code', FEYNMAN_PROMPT: 'Explain', CLOZE: 'Cloze',
  }[type] || type;
}

document.addEventListener('DOMContentLoaded', init);
