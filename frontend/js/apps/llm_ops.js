const API = '/api/llm';

const createForm = document.getElementById('createForm');
const updateForm = document.getElementById('updateForm');
const queueStatus = document.getElementById('queueStatus');
const llmOutput = document.getElementById('llmOutput');

let activeJobId = null;

async function getJson(url, opts = {}) {
  const res = await fetch(url, opts);
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`);
  return data;
}

async function refreshQueue() {
  const data = await getJson(`${API}/queue`);
  queueStatus.textContent = `Queued: ${data.queue_depth} | current: ${data.worker.current_job || 'idle'}`;
}

async function refreshJob() {
  if (!activeJobId) return;
  const data = await getJson(`/api/jobs/${activeJobId}`);
  const lines = [];
  lines.push(`Status: ${data.status}`);
  lines.push(...(data.logs || []));
  if (data.result?.response) lines.push('\n=== RESPONSE ===\n' + data.result.response);
  llmOutput.textContent = lines.join('\n');
}

async function submit(url, payload) {
  const data = await getJson(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
  activeJobId = data.job_id;
}

createForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  const form = new FormData(e.target);
  await submit(`${API}/create`, { model: form.get('model').trim(), prompt: form.get('prompt').trim() });
});

updateForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  const form = new FormData(e.target);
  await submit(`${API}/update`, {
    model: form.get('model').trim(),
    artifact_id: form.get('artifact_id').trim(),
    diff: form.get('diff').trim(),
  });
});

setInterval(() => { refreshQueue().catch(() => {}); refreshJob().catch(() => {}); }, 2500);
refreshQueue().catch(() => {});
