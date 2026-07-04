const KEY_STORAGE = 'symon_frontend_user_api_key';

const apiKeyInput = document.getElementById('apiKeyInput');
const saveKeyBtn = document.getElementById('saveKeyBtn');
const refreshBtn = document.getElementById('refreshBtn');
const statusOutput = document.getElementById('statusOutput');

function getKey() {
  return localStorage.getItem(KEY_STORAGE) || '';
}

function setKey(value) {
  localStorage.setItem(KEY_STORAGE, value.trim());
}

async function refreshStatus() {
  if (!getKey()) {
    statusOutput.textContent = 'No user key saved.';
    return;
  }

  try {
    const resp = await fetch('/runtime/status', {
      headers: { 'X-API-Key': getKey() },
    });

    const data = await resp.json();

    if (!resp.ok) {
      throw new Error(data.detail || `HTTP ${resp.status}`);
    }

    statusOutput.textContent = JSON.stringify(data, null, 2);
  } catch (err) {
    statusOutput.textContent = `Error: ${err.message}`;
  }
}

saveKeyBtn.addEventListener('click', async () => {
  setKey(apiKeyInput.value);
  await refreshStatus();
});

refreshBtn.addEventListener('click', refreshStatus);

apiKeyInput.value = getKey();
refreshStatus();
