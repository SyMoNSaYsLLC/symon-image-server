const POLL_INTERVAL = 1500;
const KEY_STORAGE = 'symon_frontend_user_api_key';

const accountStatus = document.getElementById('accountStatus');
const apiKeyInput = document.getElementById('apiKeyInput');
const saveKeyBtn = document.getElementById('saveKeyBtn');
const refreshMeBtn = document.getElementById('refreshMeBtn');
const creditBox = document.getElementById('creditBox');
const packSelect = document.getElementById('packSelect');
const buyBtn = document.getElementById('buyBtn');
const modeSelect = document.getElementById('modeSelect');
const promptInput = document.getElementById('promptInput');
const negPromptInput = document.getElementById('negPromptInput');
const widthInput = document.getElementById('widthInput');
const heightInput = document.getElementById('heightInput');
const generateBtn = document.getElementById('generateBtn');
const refreshJobsBtn = document.getElementById('refreshJobsBtn');
const jobStatus = document.getElementById('jobStatus');
const gallery = document.getElementById('gallery');
const emptyState = document.getElementById('emptyState');

function getKey() { return localStorage.getItem(KEY_STORAGE) || ''; }
function setKey(value) { localStorage.setItem(KEY_STORAGE, value.trim()); }
function authHeaders(extra = {}) { return { 'X-API-Key': getKey(), ...extra }; }

async function getJson(url, options = {}) {
  const resp = await fetch(url, options);
  let data = {};
  try { data = await resp.json(); } catch {}
  if (!resp.ok) throw new Error(data.detail || `HTTP ${resp.status}`);
  return data;
}

function escapeHtml(value) {
  return String(value ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#039;');
}

async function loadMe() {
  apiKeyInput.value = getKey();
  if (!getKey()) {
    accountStatus.textContent = 'Account: no user key saved';
    creditBox.textContent = 'Credits: unknown';
    return;
  }
  try {
    const data = await getJson('/me', { headers: authHeaders() });
    accountStatus.textContent = `Account: ${data.account_id} | key: ${data.api_key?.label || data.api_key?.key_id || 'active'}`;
    creditBox.textContent = `Credits: ${data.credits}`;
  } catch (err) {
    accountStatus.textContent = `Account error: ${err.message}`;
    creditBox.textContent = 'Credits: unavailable';
  }
}

async function loadJobs() {
  if (!getKey()) {
    gallery.innerHTML = '';
    emptyState.classList.remove('hidden');
    return;
  }
  try {
    const data = await getJson('/me/jobs', { headers: authHeaders() });
    renderJobs(data.jobs || []);
  } catch (err) {
    jobStatus.textContent = `Job list error: ${err.message}`;
  }
}

function renderJobs(jobs) {
  if (!jobs.length) {
    gallery.innerHTML = '';
    emptyState.classList.remove('hidden');
    return;
  }
  emptyState.classList.add('hidden');
  gallery.innerHTML = jobs.map((job) => {
    const image = job.url
      ? `<a href="${job.url}" target="_blank"><img src="${job.url}" alt="Generated image ${job.job_id}" /></a>`
      : `<div class="image-placeholder">${escapeHtml(job.status)}</div>`;
    return `
      <article class="image-card">
        ${image}
        <div class="image-meta">
          <strong>${escapeHtml(job.mode || 'job')}</strong>
          <span class="status-pill">${escapeHtml(job.status)}</span>
          <small>${escapeHtml(job.job_id)}</small>
          ${job.credit_cost ? `<small>Cost: ${job.credit_cost} credits</small>` : ''}
          ${job.seconds ? `<small>Time: ${job.seconds}s</small>` : ''}
          ${job.error ? `<small class="error-text">Error: ${escapeHtml(job.error)}</small>` : ''}
        </div>
      </article>`;
  }).join('');
}

async function buyCredits() {
  buyBtn.disabled = true;
  jobStatus.textContent = 'Creating checkout session…';
  try {
    const data = await getJson('/me/checkout', {
      method: 'POST',
      headers: authHeaders({ 'Content-Type': 'application/json' }),
      body: JSON.stringify({ pack: packSelect.value }),
    });
    window.location.href = data.checkout_url;
  } catch (err) {
    jobStatus.textContent = `Checkout error: ${err.message}`;
    buyBtn.disabled = false;
  }
}

async function generate() {
  const prompt = promptInput.value.trim();
  if (!getKey()) return alert('Paste and save your user API key first.');
  if (!prompt) return alert('Please enter a prompt.');
  generateBtn.disabled = true;
  jobStatus.textContent = 'Submitting job…';
  try {
    const data = await getJson('/sdxl/txt2img/queue', {
      method: 'POST',
      headers: authHeaders({ 'Content-Type': 'application/json' }),
      body: JSON.stringify({
        mode: modeSelect.value,
        prompt,
        negative_prompt: negPromptInput.value.trim() || null,
        width: Number(widthInput.value),
        height: Number(heightInput.value),
      }),
    });
    jobStatus.textContent = `Queued ${data.mode} job ${data.job_id.slice(0, 8)}. Remaining credits: ${data.remaining_credits}`;
    pollJob(data.job_id);
  } catch (err) {
    jobStatus.textContent = `Error: ${err.message}`;
    generateBtn.disabled = false;
  }
}

function pollJob(jobId) {
  const timer = setInterval(async () => {
    try {
      const data = await getJson(`/me/jobs/${jobId}`, { headers: authHeaders() });
      const job = data.job;
      jobStatus.textContent = `Job ${jobId.slice(0, 8)}: ${job.status}`;
      await loadMe();
      await loadJobs();
      if (['done', 'error'].includes(job.status)) {
        clearInterval(timer);
        generateBtn.disabled = false;
      }
    } catch (err) {
      clearInterval(timer);
      jobStatus.textContent = `Poll error: ${err.message}`;
      generateBtn.disabled = false;
    }
  }, POLL_INTERVAL);
}

saveKeyBtn.addEventListener('click', async () => { setKey(apiKeyInput.value); await loadMe(); await loadJobs(); });
refreshMeBtn.addEventListener('click', loadMe);
refreshJobsBtn.addEventListener('click', loadJobs);
buyBtn.addEventListener('click', buyCredits);
generateBtn.addEventListener('click', generate);
apiKeyInput.value = getKey();
loadMe();
loadJobs();
