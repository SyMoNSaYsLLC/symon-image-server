// tensor_lab.js — Tensor Lab frontend module
// Handles: Create Tensor, Tensor Ops, Model Inspector, Custom Chat, Guide tabs

const API = '/api/tensor';
const CHAT_MODELS_API = '/api/chat/models';

// ---------------------------------------------------------------------------
// Tab switching
// ---------------------------------------------------------------------------

document.querySelectorAll('.tl-tab').forEach((btn) => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.tl-tab').forEach((b) => b.classList.remove('active'));
    document.querySelectorAll('.tl-pane').forEach((p) => p.classList.remove('active'));
    btn.classList.add('active');
    document.getElementById(`pane-${btn.dataset.pane}`).classList.add('active');
  });
});

// ---------------------------------------------------------------------------
// Helper utilities
// ---------------------------------------------------------------------------

function escapeHtml(s) {
  return String(s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}

function escapeAttr(s) {
  return String(s).replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}

function showError(el, msg) {
  el.style.display = 'block';
  el.innerHTML = `<span style="color:#c0392b;">⚠ ${escapeHtml(msg)}</span>`;
}

// ---------------------------------------------------------------------------
// Load model list for selects
// ---------------------------------------------------------------------------

async function loadModels(selectEl) {
  try {
    const data = await (await fetch(CHAT_MODELS_API)).json();
    const models = data.models || [];
    selectEl.innerHTML = models.length
      ? models.map((m) => `<option value="${escapeAttr(m.name)}">${escapeHtml(m.name)}</option>`).join('')
      : '<option value="">No models found — is Ollama running?</option>';
  } catch {
    selectEl.innerHTML = '<option value="">Ollama unavailable</option>';
  }
}

loadModels(document.getElementById('tl-inspectModel'));
loadModels(document.getElementById('tl-chatModel'));

// ---------------------------------------------------------------------------
// Create Tensor
// ---------------------------------------------------------------------------

document.getElementById('tl-createBtn').addEventListener('click', async () => {
  const shapeRaw = document.getElementById('tl-shape').value.trim();
  const dtype = document.getElementById('tl-dtype').value;
  const fill = document.getElementById('tl-fill').value;

  const resultSection = document.getElementById('tl-createResult');
  const badge = document.getElementById('tl-createBadge');
  const meta = document.getElementById('tl-createMeta');
  const preview = document.getElementById('tl-createPreview');

  const shape = shapeRaw.split(',').map((s) => parseInt(s.trim(), 10));
  if (shape.some(isNaN) || shape.some((d) => d <= 0)) {
    resultSection.style.display = 'block';
    showError(preview, 'Invalid shape. Enter positive integers separated by commas (e.g. 3,4).');
    return;
  }

  try {
    const resp = await fetch(`${API}/create`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ shape, dtype, fill }),
    });
    const data = await resp.json();
    if (!resp.ok) throw new Error(data.detail || `HTTP ${resp.status}`);

    const kb = (data.nbytes / 1024).toFixed(2);
    badge.textContent = `${data.shape.join('×')} · ${data.dtype}`;
    meta.innerHTML = [
      `Shape: <strong>${data.shape.join(' × ')}</strong>`,
      `dtype: <strong>${data.dtype}</strong>`,
      `Elements: <strong>${data.n_elements.toLocaleString()}</strong>`,
      `Memory: <strong>${kb} KB</strong>`,
    ].join('&emsp;|&emsp;');

    const truncNote = data.truncated ? `\n… (showing first 64 of ${data.n_elements} elements)` : '';
    preview.textContent = JSON.stringify(data.preview, null, 2) + truncNote;
    resultSection.style.display = 'block';
  } catch (err) {
    resultSection.style.display = 'block';
    showError(preview, err.message);
  }
});

// ---------------------------------------------------------------------------
// Tensor Operations
// ---------------------------------------------------------------------------

document.getElementById('tl-opBtn').addEventListener('click', async () => {
  const aRaw = document.getElementById('tl-opA').value.trim();
  const bRaw = document.getElementById('tl-opB').value.trim();
  const op = document.getElementById('tl-op').value;

  const resultSection = document.getElementById('tl-opResult');
  const meta = document.getElementById('tl-opMeta');
  const preview = document.getElementById('tl-opPreview');

  let a, b;
  try {
    a = JSON.parse(aRaw);
    b = JSON.parse(bRaw);
  } catch (e) {
    resultSection.style.display = 'block';
    showError(preview, `JSON parse error: ${e.message}`);
    return;
  }

  try {
    const resp = await fetch(`${API}/op`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ a, b, op }),
    });
    const data = await resp.json();
    if (!resp.ok) throw new Error(data.detail || `HTTP ${resp.status}`);

    meta.innerHTML = [
      `A: <strong>${escapeHtml(data.shape_a.join('×'))}</strong>`,
      `B: <strong>${escapeHtml(data.shape_b.join('×'))}</strong>`,
      `Result: <strong>${escapeHtml(data.shape_result.join('×'))}</strong>`,
      `op: <strong>${escapeHtml(op)}</strong>`,
    ].join('&emsp;|&emsp;');

    preview.textContent = JSON.stringify(data.result, null, 2);
    resultSection.style.display = 'block';
  } catch (err) {
    resultSection.style.display = 'block';
    showError(preview, err.message);
  }
});

// ---------------------------------------------------------------------------
// Model Inspector
// ---------------------------------------------------------------------------

document.getElementById('tl-inspectBtn').addEventListener('click', async () => {
  const model = document.getElementById('tl-inspectModel').value;
  const resultSection = document.getElementById('tl-inspectResult');
  const content = document.getElementById('tl-inspectContent');

  if (!model) {
    resultSection.style.display = 'block';
    showError(content, 'Please select a model.');
    return;
  }

  content.textContent = 'Loading…';
  resultSection.style.display = 'block';

  try {
    const resp = await fetch(`${API}/model/info?model=${encodeURIComponent(model)}`);
    const data = await resp.json();
    if (!resp.ok) throw new Error(data.detail || `HTTP ${resp.status}`);

    content.textContent = JSON.stringify(data, null, 2);
  } catch (err) {
    showError(content, err.message);
  }
});

// ---------------------------------------------------------------------------
// API key persistence
// ---------------------------------------------------------------------------

const KEY_STORAGE = 'tl_api_key';   // reserved but key is not persisted to localStorage
const URL_STORAGE = 'tl_base_url';

const apiKeyInput = document.getElementById('tl-apiKey');
const baseUrlInput = document.getElementById('tl-baseUrl');

// Restore saved base URL (API key is intentionally not persisted)
const savedKey = '';
const savedUrl = localStorage.getItem(URL_STORAGE) || '';
if (savedKey) apiKeyInput.value = savedKey;
if (savedUrl) baseUrlInput.value = savedUrl;

document.getElementById('tl-saveKeyBtn').addEventListener('click', () => {
  // Only persist the base URL — never store the API key in localStorage
  // to avoid leaving credentials in browser storage.
  localStorage.setItem(URL_STORAGE, baseUrlInput.value);
  const btn = document.getElementById('tl-saveKeyBtn');
  btn.textContent = '✅ Saved';
  setTimeout(() => { btn.textContent = '💾 Save'; }, 1500);
});

// ---------------------------------------------------------------------------
// Custom Chat
// ---------------------------------------------------------------------------

let tlHistory = [];

const chatHistory = document.getElementById('tl-chatHistory');
const chatForm = document.getElementById('tl-chatForm');
const chatInput = document.getElementById('tl-chatInput');
const sendBtn = document.getElementById('tl-sendBtn');

document.getElementById('tl-clearChatBtn').addEventListener('click', () => {
  tlHistory = [];
  chatHistory.innerHTML = '<div class="hint" style="align-self:center;color:#999;">Messages will appear here…</div>';
});

chatForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  const content = chatInput.value.trim();
  if (!content) return;
  chatInput.value = '';

  appendChatMsg('user', content);
  tlHistory.push({ role: 'user', content });

  sendBtn.disabled = true;
  const assistantEl = appendChatMsg('assistant', '');

  const model = document.getElementById('tl-chatModel').value;
  const baseUrl = baseUrlInput.value.trim() || 'http://localhost:11434';
  const apiKey = apiKeyInput.value.trim();
  const sysPrompt = document.getElementById('tl-sysPrompt').value.trim();

  const messages = sysPrompt
    ? [{ role: 'system', content: sysPrompt }, ...tlHistory]
    : [...tlHistory];

  const payload = {
    model,
    messages,
    temperature: parseFloat(document.getElementById('tl-temperature').value),
    top_p:        parseFloat(document.getElementById('tl-topP').value),
    top_k:        parseInt(document.getElementById('tl-topK').value, 10),
    repeat_penalty: parseFloat(document.getElementById('tl-repeatPenalty').value),
    num_predict:  parseInt(document.getElementById('tl-numPredict').value, 10),
    num_ctx:      parseInt(document.getElementById('tl-numCtx').value, 10),
    stream:       true,
    base_url:     baseUrl,
    api_key:      apiKey || null,
  };

  try {
    const resp = await fetch(`${API}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });

    if (!resp.ok) {
      const err = await resp.json();
      throw new Error(err.detail || `HTTP ${resp.status}`);
    }

    const reader = resp.body.getReader();
    const decoder = new TextDecoder();
    let fullText = '';

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      fullText += decoder.decode(value, { stream: true });
      assistantEl.textContent = fullText;
      chatHistory.scrollTop = chatHistory.scrollHeight;
    }

    tlHistory.push({ role: 'assistant', content: fullText });
  } catch (err) {
    assistantEl.innerHTML = `<span style="color:#f87;">⚠ ${escapeHtml(err.message)}</span>`;
  } finally {
    sendBtn.disabled = false;
    chatHistory.scrollTop = chatHistory.scrollHeight;
  }
});

// Ctrl+Enter to send
chatInput.addEventListener('keydown', (e) => {
  if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) chatForm.requestSubmit();
});

function appendChatMsg(role, content) {
  // Remove placeholder text on first real message
  const placeholder = chatHistory.querySelector('.hint');
  if (placeholder) placeholder.remove();

  const el = document.createElement('div');
  el.className = `tl-msg ${role}`;
  el.textContent = content;
  chatHistory.appendChild(el);
  chatHistory.scrollTop = chatHistory.scrollHeight;
  return el;
}

// ---------------------------------------------------------------------------
// Guide — populate dtype table from /api/tensor/dtypes
// ---------------------------------------------------------------------------

(async () => {
  try {
    const data = await (await fetch(`${API}/dtypes`)).json();
    const tbody = document.getElementById('tl-dtypeBody');
    tbody.innerHTML = (data.dtypes || []).map((d) => `
      <tr>
        <td style="padding:0.3rem 0.5rem;font-family:monospace;">${escapeHtml(d.name)} / ${escapeHtml(d.alias)}</td>
        <td style="padding:0.3rem 0.5rem;">${escapeHtml(String(d.bits))}</td>
        <td style="padding:0.3rem 0.5rem;">${escapeHtml(d.description)}</td>
      </tr>
    `).join('');
  } catch {
    // Guide still works without the dynamic table
  }
})();
