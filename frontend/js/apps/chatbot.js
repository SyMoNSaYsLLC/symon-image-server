const KEY_STORAGE = 'symon_frontend_user_api_key';

const apiKeyInput = document.getElementById('apiKeyInput');
const saveKeyBtn = document.getElementById('saveKeyBtn');
const checkStatusBtn = document.getElementById('checkStatusBtn');
const chatStatus = document.getElementById('chatStatus');

const maxTokensInput = document.getElementById('maxTokensInput');
const temperatureInput = document.getElementById('temperatureInput');

const chatLog = document.getElementById('chatLog');
const messageInput = document.getElementById('messageInput');
const sendBtn = document.getElementById('sendBtn');
const requestStatus = document.getElementById('requestStatus');

function getKey() {
  return localStorage.getItem(KEY_STORAGE) || '';
}

function setKey(value) {
  localStorage.setItem(KEY_STORAGE, value.trim());
}

function headers(extra = {}) {
  return {
    'X-API-Key': getKey(),
    ...extra,
  };
}

function escapeHtml(value) {
  return String(value ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#039;');
}

function addMessage(role, content) {
  const div = document.createElement('div');
  div.className = `chat-message ${role}`;
  div.innerHTML = `
    <strong>${role === 'user' ? 'You' : 'Qwen'}</strong>
    <p>${escapeHtml(content)}</p>
  `;
  chatLog.appendChild(div);
  chatLog.scrollTop = chatLog.scrollHeight;
}

async function getJson(url, options = {}) {
  const resp = await fetch(url, options);
  let data = {};
  try {
    data = await resp.json();
  } catch {}

  if (!resp.ok) {
    throw new Error(data.detail || `HTTP ${resp.status}`);
  }

  return data;
}

async function checkStatus() {
  if (!getKey()) {
    chatStatus.textContent = 'Qwen status: no user key saved';
    return;
  }

  try {
    const data = await getJson('/chat/status', {
      headers: headers(),
    });

    chatStatus.textContent = data.qwen_running
      ? 'Qwen status: running'
      : 'Qwen status: not running';
  } catch (err) {
    chatStatus.textContent = `Qwen status error: ${err.message}`;
  }
}

async function sendMessage() {
  const message = messageInput.value.trim();

  if (!getKey()) {
    alert('Paste and save your user API key first.');
    return;
  }

  if (!message) {
    return;
  }

  addMessage('user', message);
  messageInput.value = '';
  sendBtn.disabled = true;
  requestStatus.textContent = 'Thinking with Qwen...';

  try {
    const data = await getJson('/chat/complete', {
      method: 'POST',
      headers: headers({ 'Content-Type': 'application/json' }),
      body: JSON.stringify({
        message,
        max_tokens: Number(maxTokensInput.value || 512),
        temperature: Number(temperatureInput.value || 0.2),
      }),
    });

    addMessage('assistant', data.content || '[empty response]');
    requestStatus.textContent = data.timings?.predicted_per_second
      ? `Done. ${data.timings.predicted_per_second.toFixed(2)} tok/s`
      : 'Done.';
  } catch (err) {
    requestStatus.textContent = `Chat error: ${err.message}`;
    addMessage('assistant', `Error: ${err.message}`);
  } finally {
    sendBtn.disabled = false;
  }
}

saveKeyBtn.addEventListener('click', async () => {
  setKey(apiKeyInput.value);
  await checkStatus();
});

checkStatusBtn.addEventListener('click', checkStatus);
sendBtn.addEventListener('click', sendMessage);

messageInput.addEventListener('keydown', (event) => {
  if (event.key === 'Enter' && (event.ctrlKey || event.metaKey)) {
    sendMessage();
  }
});

apiKeyInput.value = getKey();
checkStatus();
