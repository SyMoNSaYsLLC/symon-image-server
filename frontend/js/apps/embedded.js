const API = '/api/embedded';

const buildForm = document.getElementById('buildForm');
const layerForm = document.getElementById('layerForm');
const buildStatus = document.getElementById('buildStatus');
const buildLogs = document.getElementById('buildLogs');
const layerList = document.getElementById('layerList');
const artifactList = document.getElementById('artifactList');

let activeBuild = null;

async function getJson(url, opts = {}) {
  const res = await fetch(url, opts);
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`);
  return data;
}

async function refreshLayers() {
  const data = await getJson(`${API}/layers`);
  layerList.innerHTML = (data.layers || []).map((x) => `<li>${x}</li>`).join('') || '<li>No layers configured</li>';
}

async function refreshArtifacts() {
  const data = await getJson(`${API}/artifacts`);
  artifactList.innerHTML = (data.artifacts || []).map((a) => `<div><a href="${API}/artifacts/${encodeURIComponent(a.name)}">${a.name}</a> (${a.size} bytes)</div>`).join('') || 'No artifacts yet.';
}

async function refreshBuild() {
  if (!activeBuild) return;
  const job = await getJson(`${API}/build/${activeBuild}`);
  buildStatus.textContent = `${job.status} @ ${job.stage}`;
  buildLogs.textContent = (job.logs || []).join('\n');
}

buildForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  const form = new FormData(e.target);
  const payload = { machine: form.get('machine').trim(), recipe: form.get('recipe').trim() };
  const data = await getJson(`${API}/build`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
  activeBuild = data.job_id;
  buildStatus.textContent = `queued (${activeBuild})`;
});

layerForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  const form = new FormData(e.target);
  const payload = { layer_url: form.get('layer_url').trim() };
  await getJson(`${API}/layers`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
  e.target.reset();
  await refreshLayers();
});

setInterval(() => { refreshBuild().catch(() => {}); refreshArtifacts().catch(() => {}); }, 3000);
refreshLayers().catch(() => {});
refreshArtifacts().catch(() => {});
