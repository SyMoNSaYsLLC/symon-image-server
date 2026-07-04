const API = '/api/mining';

const poolList = document.getElementById('poolList');
const minerStatus = document.getElementById('minerStatus');
const txFeed = document.getElementById('txFeed');
const minerForm = document.getElementById('minerForm');
const stopBtn = document.getElementById('stopBtn');
const refreshPoolsBtn = document.getElementById('refreshPoolsBtn');

let currentDevice = null;

async function getJson(url, opts = {}) {
  const res = await fetch(url, opts);
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`);
  return data;
}

async function refreshPools() {
  const data = await getJson(`${API}/pools`);
  const pools = data.pools || [];
  poolList.innerHTML = pools.map((p) => `
    <article class="mining-card">
      <strong>${p.name}</strong>
      <div>${p.network} • fee ${p.fee}%</div>
      <code>${p.stratum_url}</code>
    </article>
  `).join('') || '<p>No pools discovered.</p>';
}

async function refreshStatus() {
  const data = await getJson(`${API}/status`);
  const miners = data.miners || [];
  minerStatus.innerHTML = miners.map((m) => `${m.device_id}: ${m.hashrate} H/s, ${m.temperature}°C, A/R ${m.accepted_shares}/${m.rejected_shares}`).join('<br>') || 'No active miners.';
}

async function refreshTx() {
  const data = await getJson(`${API}/transactions`);
  const tx = data.transactions || [];
  txFeed.innerHTML = tx.map((t) => `<div>${t.txid} (${t.verified_at})</div>`).join('') || 'No verified transactions yet.';
}

minerForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  const form = new FormData(e.target);
  const payload = { device_id: form.get('device_id').trim(), pool: form.get('pool').trim() };
  currentDevice = payload.device_id;
  await getJson(`${API}/start`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
  await refreshStatus();
});

stopBtn.addEventListener('click', async () => {
  if (!currentDevice) return;
  await getJson(`${API}/stop`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ device_id: currentDevice }) });
  await refreshStatus();
});

refreshPoolsBtn.addEventListener('click', refreshPools);
setInterval(() => { refreshStatus().catch(() => {}); refreshTx().catch(() => {}); }, 3000);
refreshPools().catch((e) => { poolList.textContent = e.message; });
refreshStatus().catch(() => {});
refreshTx().catch(() => {});
