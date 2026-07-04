const API = '/api/calc';

const exprInput   = document.getElementById('exprInput');
const modeSelect  = document.getElementById('modeSelect');
const varInput    = document.getElementById('varInput');
const calcBtn     = document.getElementById('calcBtn');
const latexOut    = document.getElementById('latexOut');
const numericOut  = document.getElementById('numericOut');
const historyList = document.getElementById('historyList');

// Mode-specific option panels
const modeOpts = {
  derivative: document.getElementById('derivOpts'),
  integral:   document.getElementById('intOpts'),
  limit:      document.getElementById('limOpts'),
  ode:        document.getElementById('odeOpts'),
};

const orderInput = document.getElementById('orderInput');
const lowerInput = document.getElementById('lowerInput');
const upperInput = document.getElementById('upperInput');
const pointInput = document.getElementById('pointInput');
const dirSelect  = document.getElementById('dirSelect');
const funcInput  = document.getElementById('funcInput');

// Show/hide panels on mode change
modeSelect.addEventListener('change', () => {
  const m = modeSelect.value;
  Object.entries(modeOpts).forEach(([key, el]) => {
    el.classList.toggle('hidden', key !== m);
  });
});
// Init
modeSelect.dispatchEvent(new Event('change'));

// ---- Calculate -----------------------------------------------------------

calcBtn.addEventListener('click', calculate);
exprInput.addEventListener('keydown', (e) => { if (e.key === 'Enter') calculate(); });

async function calculate() {
  const expr = exprInput.value.trim();
  if (!expr) { exprInput.focus(); return; }

  calcBtn.disabled = true;
  calcBtn.textContent = 'Calculating…';
  latexOut.textContent  = '';
  numericOut.textContent = '';

  const mode = modeSelect.value;
  const payload = {
    mode,
    expr,
    var:   varInput.value.trim() || 'x',
    order: parseInt(orderInput.value, 10) || 1,
    lower: lowerInput.value.trim() || null,
    upper: upperInput.value.trim() || null,
    point: pointInput.value.trim() || '0',
    direction: dirSelect.value,
    func:  funcInput.value.trim() || 'y',
    precision: 15,
  };

  try {
    const resp = await fetch(API, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!resp.ok) {
      const err = await resp.json();
      throw new Error(err.detail || `HTTP ${resp.status}`);
    }
    const data = await resp.json();
    renderResult(data, expr, mode);
    addHistory(expr, mode, data);
  } catch (err) {
    latexOut.innerHTML = `<span style="color:#f87">Error: ${escapeHtml(err.message)}</span>`;
  } finally {
    calcBtn.disabled  = false;
    calcBtn.textContent = 'Calculate';
  }
}

function renderResult(data, expr, mode) {
  // LaTeX output
  if (data.latex && window.katex) {
    try {
      latexOut.innerHTML = '';
      katex.render(data.latex, latexOut, { throwOnError: false, displayMode: true });
    } catch {
      latexOut.textContent = data.latex;
    }
  } else {
    latexOut.textContent = data.latex || data.expr || '';
  }

  // Numeric output
  if (data.numeric) {
    numericOut.textContent = `≈ ${data.numeric}`;
  } else {
    numericOut.textContent = '';
  }
}

// ---- History -------------------------------------------------------------

const _history = [];

function addHistory(expr, mode, result) {
  _history.unshift({ expr, mode, latex: result.latex, numeric: result.numeric });
  if (_history.length > 50) _history.pop();
  renderHistory();
}

function renderHistory() {
  historyList.innerHTML = _history.slice(0, 20).map((item) => `
    <li class="history-item" title="Click to restore">
      <span class="history-mode">${escapeHtml(item.mode)}</span>
      <code class="history-expr">${escapeHtml(item.expr)}</code>
      <span class="history-numeric">${item.numeric ? '≈ ' + escapeHtml(item.numeric) : ''}</span>
    </li>
  `).join('');

  historyList.querySelectorAll('.history-item').forEach((li, idx) => {
    li.addEventListener('click', () => {
      exprInput.value = _history[idx].expr;
    });
  });
}

function escapeHtml(s) {
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}
