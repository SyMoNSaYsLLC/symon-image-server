const KEY_STORAGE = 'symon_frontend_user_api_key';

const apiKeyInput = document.getElementById('apiKeyInput');
const saveKeyBtn = document.getElementById('saveKeyBtn');
const refreshBtn = document.getElementById('refreshBtn');
const accountOutput = document.getElementById('accountOutput');

function getKey() {
  return localStorage.getItem(KEY_STORAGE) || '';
}

function setKey(value) {
  localStorage.setItem(KEY_STORAGE, value.trim());
}

async function getJson(url) {
  const resp = await fetch(url, {
    headers: { 'X-API-Key': getKey() },
  });

  const data = await resp.json().catch(() => ({}));

  if (!resp.ok) {
    throw new Error(data.detail || `HTTP ${resp.status}`);
  }

  return data;
}

async function refreshDashboard() {
  if (!accountOutput) return;

  if (!getKey()) {
    accountOutput.textContent = 'Paste your user API key and click Save Key.';
    return;
  }

  try {
    const [me, runtime] = await Promise.all([
      getJson('/me'),
      getJson('/runtime/status'),
    ]);

    accountOutput.textContent = JSON.stringify({
      account_id: me.account_id,
      credits: me.credits,
      api_key: me.api_key,
      models: runtime.models,
    }, null, 2);
  } catch (err) {
    accountOutput.textContent = `Error: ${err.message}`;
  }
}

if (apiKeyInput) apiKeyInput.value = getKey();

if (saveKeyBtn) {
  saveKeyBtn.addEventListener('click', async () => {
    setKey(apiKeyInput.value);
    await refreshDashboard();
  });
}

if (refreshBtn) {
  refreshBtn.addEventListener('click', refreshDashboard);
}

refreshDashboard();
