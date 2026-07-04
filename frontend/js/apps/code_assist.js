const API = '/api/code';

const langSelect  = document.getElementById('langSelect');
const modelInput  = document.getElementById('modelInput');
const statusBar   = document.getElementById('statusBar');
const codeResponse = document.getElementById('codeResponse');
const actionBtns  = document.querySelectorAll('.action-btn');

let monacoEditor = null;

// ---- Monaco Editor -------------------------------------------------------

require(['vs/editor/editor.main'], () => {
  monacoEditor = monaco.editor.create(document.getElementById('editorContainer'), {
    value: '// Paste or type your code here\n',
    language: 'javascript',
    theme: 'vs-dark',
    minimap: { enabled: false },
    fontSize: 13,
    scrollBeyondLastLine: false,
    wordWrap: 'on',
  });
});

langSelect.addEventListener('change', () => {
  if (!monacoEditor) return;
  const lang = langSelect.value || 'plaintext';
  monaco.editor.setModelLanguage(monacoEditor.getModel(), lang);
});

// ---- Action buttons -------------------------------------------------------

actionBtns.forEach((btn) => {
  btn.addEventListener('click', () => runAction(btn.dataset.action));
});

async function runAction(action) {
  if (!monacoEditor) { alert('Editor not ready yet.'); return; }

  const code = monacoEditor.getValue().trim();
  if (!code) { alert('Please enter some code first.'); return; }

  const language = langSelect.value || undefined;
  const model    = modelInput.value.trim() || undefined;

  statusBar.textContent = `Running: ${action}…`;
  codeResponse.textContent = '';
  actionBtns.forEach((b) => { b.disabled = true; });

  const payload = { code, action, stream: true };
  if (language) payload.language = language;
  if (model)    payload.model    = model;

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

    const reader  = resp.body.getReader();
    const decoder = new TextDecoder();

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      codeResponse.textContent += decoder.decode(value, { stream: true });
      codeResponse.scrollTop = codeResponse.scrollHeight;
    }

    statusBar.textContent = 'Done.';
  } catch (err) {
    statusBar.textContent = `Error: ${err.message}`;
    codeResponse.textContent = '';
  } finally {
    actionBtns.forEach((b) => { b.disabled = false; });
  }
}
