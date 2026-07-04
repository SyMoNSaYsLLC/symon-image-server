const API = '/api/iptv';

const loadBtn     = document.getElementById('loadBtn');
const m3uUrl      = document.getElementById('m3uUrl');
const searchInput = document.getElementById('searchInput');
const groupSelect = document.getElementById('groupSelect');
const channelList = document.getElementById('channelList');
const playerWrapper = document.getElementById('playerWrapper');
const emptyState  = document.getElementById('emptyState');
const playerEl    = document.getElementById('player');
const nowPlaying  = document.getElementById('nowPlaying');

let hls = null;
let allChannels = [];

// ---- Load playlist -------------------------------------------------------

loadBtn.addEventListener('click', async () => {
  const url = m3uUrl.value.trim();
  if (!url) { alert('Please enter an M3U URL.'); return; }

  loadBtn.disabled = true;
  loadBtn.textContent = 'Loading…';
  channelList.innerHTML = '<p class="hint">Fetching playlist…</p>';

  try {
    const resp = await fetch(`${API}/parse`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url }),
    });
    if (!resp.ok) {
      const err = await resp.json();
      throw new Error(err.detail || `HTTP ${resp.status}`);
    }
    const data = await resp.json();
    allChannels = data.channels || [];
    populateGroups(data.groups || []);
    renderChannels(allChannels);
  } catch (err) {
    channelList.innerHTML = `<p class="hint" style="color:#f87">Error: ${err.message}</p>`;
  } finally {
    loadBtn.disabled = false;
    loadBtn.textContent = 'Load Playlist';
  }
});

// ---- Filtering -----------------------------------------------------------

function filteredChannels() {
  const q     = searchInput.value.toLowerCase();
  const group = groupSelect.value;
  return allChannels.filter((c) => {
    const nameMatch  = !q || (c.name || '').toLowerCase().includes(q);
    const groupMatch = !group || (c.group || '') === group;
    return nameMatch && groupMatch;
  });
}

searchInput.addEventListener('input', () => renderChannels(filteredChannels()));
groupSelect.addEventListener('change', () => renderChannels(filteredChannels()));

function populateGroups(groups) {
  groupSelect.innerHTML = '<option value="">All categories</option>';
  groups.forEach((g) => {
    const opt = document.createElement('option');
    opt.value = g;
    opt.textContent = g;
    groupSelect.appendChild(opt);
  });
}

function renderChannels(channels) {
  if (!channels.length) {
    channelList.innerHTML = '<p class="hint">No channels found.</p>';
    return;
  }
  channelList.innerHTML = channels.map((c, idx) => `
    <div class="channel-item" data-url="${escapeAttr(c.url)}" data-name="${escapeAttr(c.name)}">
      ${c.logo ? `<img class="channel-logo" src="${escapeAttr(c.logo)}" alt="" loading="lazy" onerror="this.style.display='none'" />` : ''}
      <span class="channel-name">${escapeHtml(c.name || c.url)}</span>
      ${c.group ? `<span class="channel-group">${escapeHtml(c.group)}</span>` : ''}
    </div>
  `).join('');

  channelList.querySelectorAll('.channel-item').forEach((el) => {
    el.addEventListener('click', () => playChannel(el.dataset.url, el.dataset.name));
  });
}

// ---- Playback ------------------------------------------------------------

function playChannel(streamUrl, name) {
  emptyState.classList.add('hidden');
  playerWrapper.classList.remove('hidden');
  nowPlaying.textContent = `▶ ${name}`;

  if (hls) { hls.destroy(); hls = null; }

  if (Hls.isSupported()) {
    hls = new Hls();
    hls.loadSource(streamUrl);
    hls.attachMedia(playerEl);
    hls.on(Hls.Events.MANIFEST_PARSED, () => playerEl.play());
  } else if (playerEl.canPlayType('application/vnd.apple.mpegurl')) {
    playerEl.src = streamUrl;
    playerEl.play();
  } else {
    nowPlaying.textContent = 'HLS not supported in this browser.';
  }
}

// ---- Utilities -----------------------------------------------------------

function escapeHtml(s) {
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}
function escapeAttr(s) {
  return String(s).replace(/"/g,'&quot;').replace(/'/g,'&#39;');
}
