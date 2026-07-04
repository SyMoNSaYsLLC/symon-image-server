const API_VIDEO   = '/api/video';
const POLL_INTERVAL = 3000;

const promptInput  = document.getElementById('promptInput');
const framesInput  = document.getElementById('framesInput');
const fpsInput     = document.getElementById('fpsInput');
const widthInput   = document.getElementById('widthInput');
const heightInput  = document.getElementById('heightInput');
const generateBtn  = document.getElementById('generateBtn');
const jobStatus    = document.getElementById('jobStatus');
const videoPreview = document.getElementById('videoPreview');
const videoEl      = document.getElementById('videoEl');
const downloadBtn  = document.getElementById('downloadBtn');
const jobList      = document.getElementById('jobList');
const emptyState   = document.getElementById('emptyState');

const _jobs = {};

// ---- Generate ------------------------------------------------------------

generateBtn.addEventListener('click', generate);

async function generate() {
  const prompt = promptInput.value.trim();
  if (!prompt) { alert('Please enter a prompt.'); return; }

  generateBtn.disabled = true;
  jobStatus.textContent = 'Submitting job…';

  const payload = {
    prompt,
    frame_count: parseInt(framesInput.value, 10),
    fps:         parseInt(fpsInput.value, 10),
    width:       parseInt(widthInput.value, 10),
    height:      parseInt(heightInput.value, 10),
  };

  try {
    const resp = await fetch(API_VIDEO, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!resp.ok) {
      const err = await resp.json();
      throw new Error(err.detail || `HTTP ${resp.status}`);
    }
    const { job_id } = await resp.json();
    _jobs[job_id] = { id: job_id, status: 'queued', prompt };
    renderJobs();
    jobStatus.textContent = `Job queued (${job_id.slice(0, 8)})…`;
    pollJob(job_id);
  } catch (err) {
    jobStatus.textContent = `Error: ${err.message}`;
    generateBtn.disabled = false;
  }
}

// ---- Polling -------------------------------------------------------------

async function pollJob(jobId) {
  const timer = setInterval(async () => {
    try {
      const resp = await fetch(`${API_VIDEO}/jobs/${jobId}`);
      const job  = await resp.json();
      _jobs[jobId] = { ..._jobs[jobId], ...job };
      renderJobs();
      jobStatus.textContent = `Job ${jobId.slice(0, 8)}: ${job.status}`;

      if (job.status === 'done') {
        clearInterval(timer);
        generateBtn.disabled = false;
        showVideo(job.output);
      } else if (job.status === 'failed') {
        clearInterval(timer);
        generateBtn.disabled = false;
        jobStatus.textContent = `Failed: ${job.error || 'unknown error'}`;
      }
    } catch {
      clearInterval(timer);
      generateBtn.disabled = false;
    }
  }, POLL_INTERVAL);
}

// ---- Render helpers ------------------------------------------------------

function renderJobs() {
  const jobs = Object.values(_jobs).reverse();
  if (!jobs.length) return;
  emptyState.classList.add('hidden');

  jobList.innerHTML = jobs.map((j) => `
    <div class="job-item">
      <span class="status-pill">${escapeHtml(j.status)}</span>
      <strong>${j.id.slice(0, 8)}</strong>
      <span class="hint">${escapeHtml(j.prompt || '')}</span>
    </div>
  `).join('');
}

function showVideo(outputPath) {
  const url = `/models/${outputPath}`;
  videoEl.src = url;
  downloadBtn.href = url;
  downloadBtn.download = outputPath.split('/').pop();
  videoPreview.classList.remove('hidden');
  videoEl.play();
}

function escapeHtml(s) {
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}
