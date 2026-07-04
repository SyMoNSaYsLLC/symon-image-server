const KEY_STORAGE = 'symon_frontend_user_api_key';

const apiKeyInput = document.getElementById('apiKeyInput');
const saveKeyBtn = document.getElementById('saveKeyBtn');
const checkStatusBtn = document.getElementById('checkStatusBtn');
const visionStatus = document.getElementById('visionStatus');

const imageInput = document.getElementById('imageInput');
const captionBtn = document.getElementById('captionBtn');
const requestStatus = document.getElementById('requestStatus');
const previewBox = document.getElementById('previewBox');
const captionOutput = document.getElementById('captionOutput');

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
    visionStatus.textContent = 'Vision status: no user key saved';
    return;
  }

  try {
    const data = await getJson('/vision/status', { headers: headers() });
    visionStatus.textContent = data.loaded
      ? `Vision status: loaded (${data.model})`
      : `Vision status: ready (${data.model})`;
  } catch (err) {
    visionStatus.textContent = `Vision status error: ${err.message}`;
  }
}

function showPreview(file) {
  previewBox.innerHTML = '';
  if (!file) return;

  const img = document.createElement('img');
  img.src = URL.createObjectURL(file);
  img.alt = 'Upload preview';
  previewBox.appendChild(img);
}

async function captionImage() {
  if (!getKey()) {
    alert('Paste and save your user API key first.');
    return;
  }

  const file = imageInput.files[0];
  if (!file) {
    alert('Choose an image first.');
    return;
  }

  showPreview(file);

  const form = new FormData();
  form.append('image', file);

  captionBtn.disabled = true;
  requestStatus.textContent = 'Captioning image...';
  captionOutput.textContent = '';

  try {
    const data = await getJson('/vision/caption', {
      method: 'POST',
      headers: headers(),
      body: form,
    });

    captionOutput.textContent = data.caption;
    requestStatus.textContent = `Done with ${data.model}`;
    await checkStatus();
  } catch (err) {
    requestStatus.textContent = `Caption error: ${err.message}`;
    captionOutput.textContent = '';
  } finally {
    captionBtn.disabled = false;
  }
}

saveKeyBtn.addEventListener('click', async () => {
  setKey(apiKeyInput.value);
  await checkStatus();
});

checkStatusBtn.addEventListener('click', checkStatus);
captionBtn.addEventListener('click', captionImage);
imageInput.addEventListener('change', () => showPreview(imageInput.files[0]));

apiKeyInput.value = getKey();
checkStatus();
