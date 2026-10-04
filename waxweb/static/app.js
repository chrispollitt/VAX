(() => {
'use strict';
const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));
const state = { data: null, stats: null, q: '', filters: new Set(), sort: 'name', termId: 0, termText: '' };

const FLAGS = { Canada: '\u{1F341}', USA: '\u{1F1FA}\u{1F1F8}', UK: '\u{1F1EC}\u{1F1E7}', Ireland: '\u{1F1EE}\u{1F1EA}',
  Norway: '\u{1F1F3}\u{1F1F4}', Switzerland: '\u{1F1E8}\u{1F1ED}', Sweden: '\u{1F1F8}\u{1F1EA}', Italy: '\u{1F1EE}\u{1F1F9}',
  Greece: '\u{1F1EC}\u{1F1F7}', Austria: '\u{1F1E6}\u{1F1F9}', USSR: '★', Various: '\u{1F3B6}' };
const MEDIA = { L: ['LP', '12″ LP'], C: ['TAPE', 'Cassette'], S: ['12″', '12″ single'], 7: ['7″', '7″ single'] };
const FILTERS = [
  ['lp', 'LP', (a, al) => al.copies.some(c => c.media === 'L')],
  ['tape', 'Cassette', (a, al) => al.copies.some(c => c.media === 'C')],
  ['single', '12″ single', (a, al) => al.copies.some(c => c.media === 'S')],
  ['ccm', 'CCM', (a, al) => /^(ccm|worship)$/i.test(al.genre)],
  ['can', '\u{1F341} Canadian', a => a.origin === 'Canada'],
  ['unk', '??? unknown grade', (a, al) => al.copies.some(c => c.grade === '?')],
];
const BUSY_LINES = ['Dialing the VAX at 9600 baud…', 'Rewinding the tape…', 'Asking the COBOL nicely…',
  'Blowing on the cartridge…', 'Waiting for the Rdb monitor to finish its coffee…', 'Flipping to Side B…'];

function esc(s) { return String(s == null ? '' : s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c])); }
function money(c) { return c == null ? null : '$' + (c / 100).toFixed(2).replace(/\B(?=(\d{3})+(?!\d))/g, ','); }

async function api(path, opts) {
  let r;
  try { r = await fetch(path, opts); } catch (e) { throw new Error('cannot reach the web server'); }
  let j = null;
  try { j = await r.json(); } catch (e) { /* not JSON */ }
  if (!r.ok) throw new Error((j && j.error) || ('HTTP ' + r.status));
  return j;
}
const post = (path, body) => api(path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });

// ---------------------------------------------------------------- feedback
let busyCount = 0;
function busy(on, text) {
  busyCount = Math.max(0, busyCount + (on ? 1 : -1));
  $('#busyText').textContent = text || BUSY_LINES[Math.floor(Math.random() * BUSY_LINES.length)];
  $('#busy').hidden = busyCount === 0;
}
let toastTimer = null;
function toast(msg, isErr) {
  const t = $('#toast');
  t.textContent = msg; t.className = 'toast' + (isErr ? ' err' : ''); t.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { t.hidden = true; }, isErr ? 7000 : 3500);
}
async function work(label, fn) {
  busy(true, label);
  try { return await fn(); } catch (e) { toast(e.message, true); throw e; } finally { busy(false); }
}

// ---------------------------------------------------------------- data
async function loadCollection(refresh) {
  const data = await work(refresh ? 'Re-running the roll call on the VAX…' : null,
    () => api('/api/collection' + (refresh ? '?refresh=1' : '')));
  state.data = data;
  if (data.quip) $('#quip').textContent = '“' + data.quip + '” — straight off the VAX';
  render();
  loadStats(true);
}
async function loadStats(quiet) {
  try { state.stats = await api('/api/stats'); renderCounts(); renderStats(); }
  catch (e) { if (!quiet) toast(e.message, true); }
}

// ---------------------------------------------------------------- render
function albumVisible(a, al) {
  const q = state.q.trim().toLowerCase();
  const filtersOk = Array.from(state.filters).every(k => FILTERS.find(f => f[0] === k)[2](a, al));
  if (!filtersOk) return false;
  if (!q) return true;
  const hay = [a.name, a.origin].join(' ').toLowerCase();
  if (q.split(/\s+/).every(w => hay.includes(w))) return true;
  const ah = [al.title, al.label, al.genre, al.year || ''].concat(al.copies.map(c => c.notes)).join(' ').toLowerCase();
  return q.split(/\s+/).every(w => (hay + ' ' + ah).includes(w));
}
function visibleArtists() {
  if (!state.data) return [];
  const out = [];
  for (const a of state.data.artists) {
    const albums = a.albums.filter(al => albumVisible(a, al));
    const nameHit = state.q && [a.name, a.origin].join(' ').toLowerCase().includes(state.q.trim().toLowerCase());
    const unfiltered = !state.q.trim() && !state.filters.size;      // show new artists that have no albums yet
    if (albums.length || unfiltered || (nameHit && !state.filters.size)) {
      out.push({ a, albums: albums.length ? albums : ((nameHit || unfiltered) ? a.albums : []) });
    }
  }
  const copies = x => x.albums.reduce((n, al) => n + al.copies.length, 0);
  const newest = x => Math.max(0, ...x.albums.map(al => al.year || 0));
  if (state.sort === 'hair') out.sort((x, y) => y.a.hair - x.a.hair || x.a.name.localeCompare(y.a.name));
  else if (state.sort === 'year') out.sort((x, y) => newest(y) - newest(x));
  else if (state.sort === 'copies') out.sort((x, y) => copies(y) - copies(x));
  return out;
}
function copyHtml(a, al, c, i) {
  const m = MEDIA[c.media] || ['?', 'Mystery disc'];
  const gcls = c.grade === '?' ? 'q' : c.grade;
  const price = money(c.priceCents);
  return `<div class="copy">
    <span class="badge m-${MEDIA[c.media] ? c.media : 'q'}" title="${esc(m[1])}">${esc(m[0])}</span>
    <span class="g g-${esc(gcls)}" title="${esc(c.gradeName)}">${esc(c.grade)}</span>
    <span class="price ${price ? '' : 'free'}">${price || 'priceless'}</span>
    <span class="meta">${c.year ? '· bought ' + c.year : ''}</span>
    <button class="sell" title="Sell this copy" data-artist="${esc(a.name)}" data-album="${esc(al.title)}" data-index="${i + 1}" data-media="${esc(c.media)}" data-notes="${esc(c.notes)}">sell</button>
    ${c.notes ? `<span class="note">“${esc(c.notes)}”</span>` : ''}
  </div>`;
}
function render() {
  const items = visibleArtists();
  $('#grid').innerHTML = items.map(({ a, albums }) => `
    <article class="card">
      <h2><span class="name">${esc(a.name)}</span><span class="origin">${FLAGS[a.origin] || '\u{1F310}'} ${esc(a.origin)}</span></h2>
      <div class="hair" title="Hair score ${a.hair}/10">${Array.from({ length: 10 }, (_, i) => `<i class="${i < a.hair ? 'on' : ''}"></i>`).join('')} hair ${a.hair}/10</div>
      ${albums.map(al => `<div class="album">
        <div class="t"><span class="yr">${al.year || '????'}</span><span class="ti">${esc(al.title)}</span>
          <span class="meta">${esc(al.label)}${al.genre ? ' · ' + esc(al.genre) : ''}</span></div>
        ${al.copies.map((c, i) => copyHtml(a, al, c, i)).join('')}
      </div>`).join('')}
    </article>`).join('');
  $('#empty').hidden = items.length > 0 || !state.data;
  renderCounts(items);
}
function renderCounts(items) {
  if (!state.data) return;
  items = items || visibleArtists();
  const all = state.data.artists;
  const albums = x => x.reduce((n, i) => n + (i.albums || []).length, 0);
  const copies = x => x.reduce((n, i) => n + (i.albums || []).reduce((m, al) => m + al.copies.length, 0), 0);
  const chips = [
    [items.length + (items.length === all.length ? '' : ' / ' + all.length), 'artists'],
    [albums(items.map(i => i.a ? { albums: i.albums } : i)) + '', 'albums'],
    [copies(items.map(i => ({ albums: i.albums }))) + '', 'copies'],
    [all.filter(a => a.origin === 'Canada').length + '', '\u{1F341} Canadian', 'can'],
  ];
  if (state.stats) {
    const row = l => (state.stats.rows.find(r => r.label.startsWith(l)) || {}).value;
    if (row('CanCon share')) chips.push([row('CanCon share'), 'CanCon share', 'can']);
    if (row('Total spent')) chips.push([row('Total spent'), 'spent (known)']);
  }
  $('#counts').innerHTML = chips.map(c => `<div class="chip ${c[2] || ''}"><b>${esc(c[0])}</b><span>${esc(c[1])}</span></div>`).join('');
}
function renderStats() {
  if (!state.stats) return;
  $('#statsBody').innerHTML = '<table class="stats">' + state.stats.rows.map(r =>
    `<tr class="${r.indent ? 'sub' : ''}"><td>${esc(r.label)}</td><td>${esc(r.value)}</td></tr>`).join('') + '</table>' +
    state.stats.verdicts.map(v => `<div class="verdict">${esc(v)}</div>`).join('');
}
function renderFilters() {
  $('#filters').innerHTML = FILTERS.map(f => `<button class="pill" data-f="${f[0]}" aria-pressed="${state.filters.has(f[0])}">${f[1]}</button>`).join('');
}

// ---------------------------------------------------------------- drawers / terminal
let termTimer = null;
function openDrawer(id) {
  $$('.drawer').forEach(d => { d.classList.remove('open'); d.setAttribute('aria-hidden', 'true'); });
  const d = $(id); d.classList.add('open'); d.setAttribute('aria-hidden', 'false');
  clearInterval(termTimer);
  if (id === '#termDrawer') { pollTerm(); termTimer = setInterval(pollTerm, 1200); }
  if (id === '#statsDrawer') loadStats(false);
}
function closeDrawers() {
  clearInterval(termTimer);
  $$('.drawer').forEach(d => { d.classList.remove('open'); d.setAttribute('aria-hidden', 'true'); });
}
async function pollTerm() {
  try {
    const j = await api('/api/transcript?since=' + state.termId);
    if (!j.entries.length) return;
    const pre = $('#termBody');
    const stick = pre.scrollTop + pre.clientHeight >= pre.scrollHeight - 40;
    for (const e of j.entries) {
      state.termId = Math.max(state.termId, e.id);
      if (e.dir === 'out') pre.insertAdjacentHTML('beforeend', `<span class="out">▶ ${esc(e.text)}\n</span>`);
      else pre.insertAdjacentHTML('beforeend', esc(e.text));
    }
    while (pre.childNodes.length > 1500) pre.removeChild(pre.firstChild);
    if (stick) pre.scrollTop = pre.scrollHeight;
  } catch (e) { /* the status pill reports trouble */ }
}
async function health() {
  const s = $('#status');
  try {
    const h = await api('/api/health');
    const ok = h.connected && !h.lastError;
    s.className = 'status ' + (ok ? 'ok' : (h.lastError ? 'bad' : ''));
    $('#statusText').textContent = ok ? 'VAX online · ' + h.vax : (h.lastError ? 'VAX trouble: ' + h.lastError.slice(0, 60) : 'VAX idle · ' + h.vax);
  } catch (e) { s.className = 'status bad'; $('#statusText').textContent = 'web server unreachable'; }
}

// ---------------------------------------------------------------- dialogs
function fillArtists(sel, pick) {
  const names = state.data ? state.data.artists.map(a => a.name) : [];
  sel.innerHTML = names.map(n => `<option>${esc(n)}</option>`).join('');
  if (pick && names.includes(pick)) sel.value = pick;
}
function fillAlbums(artistName, sel) {
  const a = state.data.artists.find(x => x.name === artistName);
  sel.innerHTML = (a ? a.albums : []).map(al => `<option>${esc(al.title)}</option>`).join('');
}
function openForm(id, setup) {
  const d = $(id); const f = $('form', d); f.reset();
  if (setup) setup(f);
  d.returnValue = ''; d.showModal();
  const first = $('input:not([type=hidden]),select', f); if (first) first.focus();
}
function formData(form) { return Object.fromEntries(new FormData(form).entries()); }
function wireDialog(id, handler) {
  const d = $(id);
  d.addEventListener('close', async () => {
    if (d.returnValue !== 'ok') return;
    try { const msg = await handler(formData($('form', d))); toast(msg); await loadCollection(true); } catch (e) { /* toast already shown */ }
  });
}
let pendingSell = null;

function init() {
  renderFilters();
  $('#filters').addEventListener('click', e => {
    const b = e.target.closest('.pill'); if (!b) return;
    const k = b.dataset.f; state.filters.has(k) ? state.filters.delete(k) : state.filters.add(k);
    renderFilters(); render();
  });
  let t = null;
  $('#q').addEventListener('input', e => { clearTimeout(t); t = setTimeout(() => { state.q = e.target.value; render(); }, 120); });
  $('#sort').addEventListener('change', e => { state.sort = e.target.value; render(); });
  $('#refresh').addEventListener('click', () => loadCollection(true));
  $('#showStats').addEventListener('click', () => openDrawer('#statsDrawer'));
  $('#showTerm').addEventListener('click', () => openDrawer('#termDrawer'));
  $$('[data-close]').forEach(b => b.addEventListener('click', closeDrawers));
  document.addEventListener('keydown', e => {
    if (e.key === 'Escape') closeDrawers();
    if (e.key === '/' && document.activeElement.tagName !== 'INPUT' && document.activeElement.tagName !== 'SELECT') { e.preventDefault(); $('#q').focus(); }
  });
  $('#theme').addEventListener('click', () => {
    const cur = document.documentElement.dataset.theme || (matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark');
    const next = cur === 'dark' ? 'light' : 'dark';
    document.documentElement.dataset.theme = next;
    try { localStorage.setItem('wax-theme', next); } catch (e) { /* private mode */ }
  });
  try { const th = localStorage.getItem('wax-theme'); if (th) document.documentElement.dataset.theme = th; } catch (e) { /* ignore */ }

  // add forms
  $('#addArtist').addEventListener('click', () => openForm('#dlgArtist', f => { $('#hairOut').textContent = f.hair.value; }));
  $('input[name=hair]').addEventListener('input', e => { $('#hairOut').textContent = e.target.value; });
  $('#addAlbum').addEventListener('click', () => openForm('#dlgAlbum', f => fillArtists(f.artist)));
  $('#addCopy').addEventListener('click', () => openForm('#dlgCopy', f => { fillArtists(f.artist); fillAlbums(f.artist.value, f.album); }));
  $('#dlgCopy select[name=artist]').addEventListener('change', e => fillAlbums(e.target.value, $('#dlgCopy select[name=album]')));
  wireDialog('#dlgArtist', d => work('Typing at the VAX…', () => post('/api/artist', { name: d.name, origin: d.origin, hair: +d.hair })).then(r => r.message));
  wireDialog('#dlgAlbum', d => work('Typing at the VAX…', () => post('/api/album', { artist: d.artist, title: d.title, year: +d.year || 0, label: d.label, genre: d.genre })).then(r => r.message));
  wireDialog('#dlgCopy', d => work('Typing at the VAX…', () => post('/api/copy', { artist: d.artist, album: d.album, media: d.media, grade: d.grade, price: d.price, year: +d.year || 0, notes: d.notes })).then(r => r.message));
  wireDialog('#dlgSell', () => work('Haggling at the record fair…', () => post('/api/copy/sell', pendingSell)).then(r => r.message));
  $('#grid').addEventListener('click', e => {
    const b = e.target.closest('.sell'); if (!b) return;
    pendingSell = { artist: b.dataset.artist, album: b.dataset.album, index: +b.dataset.index, media: b.dataset.media, notes: b.dataset.notes };
    $('#sellText').textContent = 'Sell copy #' + pendingSell.index + ' of “' + pendingSell.album + '” by ' + pendingSell.artist + '? This really deletes it from the VAX’s database.';
    $('#dlgSell').returnValue = ''; $('#dlgSell').showModal();
  });

  health(); setInterval(health, 15000);
  loadCollection(false).catch(() => { $('#grid').innerHTML = '<p class="empty">The VAX is not answering. Check the tunnel and the Terminal drawer.</p>'; });
}
document.addEventListener('DOMContentLoaded', init);
})();
