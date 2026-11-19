/* Operator front-end v2 */
let S = null, VIEW = 'dashboard', TRK = null, trkTimer = null, simTimer = null, airTimer = null, AF_SEL = {}, OFP = null;

const $ = (q, r = document) => r.querySelector(q);
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
/* Money is held in dollars — the currency business aviation trades in — and shown
   in whichever currency the company keeps its books in. */
const CUR = () => (S && S.currencies && S.company && S.currencies[S.company.currency]) || {symbol: '$', rate: 1, locale: 'en-US'};
const usd = n => {
  const c = CUR(), v = (n || 0) * c.rate;
  return (v < 0 ? '-' : '') + c.symbol + Math.abs(Math.round(v)).toLocaleString(c.locale);
};
const n1 = n => Number(n || 0).toLocaleString('en-US', {maximumFractionDigits: 1});
const dt = s => { if (!s) return '—'; const d = new Date(s + (s.length === 16 ? ':00Z' : 'Z')); return d.toUTCString().slice(0, 22) + 'Z'; };
const dd = s => s ? s.slice(0, 10) : '—';
const ap = i => S && S.airports[i] ? `${i} <small>${esc(S.airports[i].city)}</small>` : esc(i);
const hhmm = m => `${Math.floor(m / 60)}:${String(Math.round(m % 60)).padStart(2, '0')}`;
const nw = 'style="white-space:nowrap"';
/* One type rating covers a whole family, so say which aircraft that is. */
function simSub(type, short) {
  const sub = (S.substitutes || {})[type];
  if (!sub) return '';
  const alt = (sub.also || []).join(', ');
  if (short) return sub.addon ? esc(sub.addon) : (alt ? `any of: ${esc(alt)}` : '');
  return `${sub.addon ? `<b>${esc(sub.addon)}</b>` : ''}${sub.addon && alt ? '<br>' : ''}${alt ? `<span class="hint">Or fly ${esc(alt)} — Operator records what you fly, not which add-on you own.</span>` : ''}`;
}
const famTypes = f => ((S && S.family_types && S.family_types[f]) || []).join(', ');
const famTitle = f => { const t = famTypes(f); return t ? `${f} rating — covers ${t}` : f; };
/* Weights: everything is computed in kilograms and stored on the wire in pounds where
   SimBrief uses pounds. These helpers present whichever unit the operator has chosen. */
const LB_PER_KG = 2.20462;
const UNIT = () => (S && S.company && S.company.weight_units) || 'lb';
const wtKg = (kg, opts) => kg == null ? '—' : (UNIT() === 'lb'
  ? `${Math.round(kg * LB_PER_KG).toLocaleString()}${(opts || {}).bare ? '' : ' lb'}`
  : `${Math.round(kg).toLocaleString()}${(opts || {}).bare ? '' : ' kg'}`);
const wtLb = (lb, opts) => lb == null ? '—' : (UNIT() === 'lb'
  ? `${Math.round(lb).toLocaleString()}${(opts || {}).bare ? '' : ' lb'}`
  : `${Math.round(lb / LB_PER_KG).toLocaleString()}${(opts || {}).bare ? '' : ' kg'}`);
const unitLabel = () => UNIT() === 'lb' ? 'lb' : 'kg';
const toLb = v => UNIT() === 'lb' ? v : v * LB_PER_KG;      // form input -> wire (pounds)
const fromLb = v => UNIT() === 'lb' ? v : v / LB_PER_KG;    // wire -> form input
function opLogo(name, h = 28) {
  const f = S && S.operator_logos && S.operator_logos[name];
  if (!f) return '';
  const tone = (S.logo_tone && S.logo_tone[f]) || 'dark';
  return `<img class="oplogo lg-${tone}" src="/static/operators/${f}.png" alt="" title="${esc(name)}" style="height:${h}px;max-width:${h * 4.2}px;object-fit:contain;vertical-align:middle;margin-right:6px">`;
}

async function api(path, body) {
  const r = await fetch(path, body ? {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body)} : {});
  const j = await r.json();
  if (!j.ok) throw new Error(j.error || 'Request failed');
  return j;
}
function toast(msg, bad) {
  const t = $('#toast'); t.innerHTML = `<div class="toast ${bad ? 'bad' : ''}">${esc(msg)}</div>`;
  clearTimeout(t._t); t._t = setTimeout(() => t.innerHTML = '', bad ? 7000 : 3500);
}
async function act(fn, okMsg) {
  try { const r = await fn(); if (okMsg) toast(okMsg); await load(); return r; }
  catch (e) { toast(e.message, true); }
}
/* ---------------------------------------------------------------- theme */
function applyTheme(t) {
  const mode = t || localStorage.getItem('theme') || 'auto';
  const dark = mode === 'dark' || (mode === 'auto' && window.matchMedia('(prefers-color-scheme: dark)').matches);
  document.documentElement.dataset.theme = dark ? 'dark' : 'light';
  const mark = document.querySelector('.menubar .brand img');
  if (mark) mark.src = '/static/brand/mark-light.svg';
  CH.ink = dark ? '#dde4ec' : '#2f3d4d'; CH.grid = dark ? '#2b3743' : '#e4e7eb';
  CH.muted = dark ? '#8f9dad' : '#8b95a1'; CH.accent = dark ? '#62a0e8' : '#1c5aa6';
  CH.series[5] = dark ? '#9fb0c2' : '#2f3d4d';
  // Some embedded WebViews only repaint part of the page when custom properties change,
  // which leaves patches of the old theme behind. Force a reflow and redraw the view.
  document.documentElement.style.display = 'none';
  void document.documentElement.offsetHeight;
  document.documentElement.style.display = '';
  if (typeof S !== 'undefined' && S && S.company && typeof render === 'function') {
    try { render(); } catch (e) {}
  }
  if (VIEW === 'analytics' && typeof loadAnalytics === 'function') loadAnalytics();
  if (VIEW === 'statements' && typeof loadStatements === 'function') loadStatements();
}
function setTheme(t) { localStorage.setItem('theme', t); applyTheme(t); render(); }
window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => { if ((localStorage.getItem('theme') || 'auto') === 'auto') applyTheme(); });

let AIRPORTS = null, GEO = null;
fetch('/static/geo/world.json').then(r => r.json()).then(g => { GEO = g; if (VIEW === 'dispatch') renderTele(); }).catch(() => {});
async function load() {
  if (!AIRPORTS) AIRPORTS = await (await fetch('/api/airports')).json();
  S = await (await fetch('/api/state')).json(); S.airports = AIRPORTS; render();
}
function nav(v) { VIEW = v; render(); $('#view').scrollTop = 0; }

/* ------------------------------------------------------------ shell */
const TREE = [
  ['Company', [['dashboard', 'Dashboard'], ['career', 'Objectives'], ['company', 'Company profile'], ['analytics', 'Analytics'], ['finance', 'Finance'], ['statements', 'Statements']]],
  ['Assets', [['fleet', 'Fleet'], ['market', 'Aircraft market'], ['crew', 'Crew & staff']]],
  ['Contracts', [['ferry', 'Ferry board'], ['cargo', 'Cargo flying'], ['charter', 'Charter'], ['tenders', 'ACMI tenders'], ['contracts', 'Contracts']]],
  ['Operations', [['schedule', 'Schedule'], ['dispatch', 'Dispatch'], ['logbook', 'Logbook'], ['safety', 'Safety']]],
  ['System', [['settings', 'Settings'], ['saves', 'Save files'], ['help', 'Help'], ['credits', 'Credits']]],
];
function counts(v) {
  if (!S || !S.company) return '';
  const c = {fleet: S.fleet.length, crew: S.pilots.length, ferry: S.ferry_board.filter(j => j.status === 'Open').length, cargo: S.cargo_board.filter(j => j.status === 'Open').length, tenders: S.acmi_tenders.length,
    contracts: S.contracts.filter(c => c.status === 'Active' || c.status === 'Pending start').length, dispatch: S.active_flight ? 1 : 0, dashboard: S.inbox.filter(m => !m.read).length}[v];
  return c ? `<span class="n">${c}</span>` : '';
}
function render() {
  const co = S && S.company;
  $('#tree').innerHTML = co ? TREE.map(([g, items]) => `<div class="grp">${g}</div>` + items.map(([v, l]) =>
    `<div class="item ${VIEW === v ? 'on' : ''}" onclick="nav('${v}')">${l}${counts(v)}</div>`).join('')).join('') : '';
  $('#titlebar').innerHTML = co ? `
    ${co.logo ? `<img src="${co.logo}" alt="">` : ''}
    <div><div class="co">${esc(co.name)}</div><div class="sub">${esc(co.code)} · ${co.base} ${esc(S.airports[co.base].name)} · AOC since ${dd(co.founded)}${(S.aoc_types || []).length ? ` · <span title="Types on your operations specifications">${(S.aoc_types || []).map(esc).join(', ')} only</span>` : ''}</div></div>
    <div class="kpis">
      <div class="kpi"><div class="v ${S.cash < 0 ? 'neg' : ''}">${usd(S.cash)}</div><div class="l">Cash${S.outstanding ? ` · ${usd(S.outstanding)} invoiced` : ''}</div></div>
      <div class="kpi"><div class="v">${S.fleet.length}</div><div class="l">Aircraft</div></div>
      <div class="kpi"><div class="v">${S.contracts.filter(c => c.status === 'Active').length}</div><div class="l">Active ACMI</div></div>
      <div class="kpi"><div class="v">${co.reputation.toFixed(1)}</div><div class="l">Reputation</div></div>
    </div>` : `<div class="co">Operator</div><div class="sub">Ferry, cargo and ACMI — run a third-party flight operation</div>`;
  $('#mb-clock').textContent = co ? dt(S.clock) : '';
  renderStatus();
  const v = $('#view');
  if (!co) { v.innerHTML = viewSetup(); return; }
  const fn = {dashboard: viewDashboard, company: viewCompany, fleet: viewFleet, market: viewMarket, crew: viewCrew, ferry: viewFerry, tenders: viewTenders,
    cargo: viewCargo, charter: viewCharter, schedule: viewSchedule, career: viewCareer, safety: viewSafety, analytics: viewAnalytics, contracts: viewContracts, dispatch: viewDispatch, logbook: viewLogbook, finance: viewFinance, statements: viewStatements, settings: viewSettings, saves: viewSaves, help: viewHelp, credits: viewCredits}[VIEW];
  v.innerHTML = (VIEW === 'dashboard' ? viewTutorial() : helpStrip()) + fn();
  if (VIEW === 'dispatch') afterDispatch();
  if (VIEW === 'statements') loadStatements();
  if (VIEW === 'saves') loadSaves();
  if (VIEW === 'safety') loadSafety();
  if (VIEW === 'credits') loadCredits();
  if (VIEW === 'analytics') loadAnalytics();
  manageTracking();
}
function renderStatus() {
  const sim = S ? S.sim : {status: '—'};
  const af = S && S.active_flight;
  const src = {msfs: 'MSFS/P3D', xplane: 'X-Plane', fsuipc: 'FSUIPC'}[sim.source] || '';
  $('#mb-sim').textContent = `Sim: ${sim.connected ? src : 'not connected'}`;
  $('#statusbar').innerHTML = `
    <div class="seg"><span class="dot ${sim.connected ? 'on' : sim.status === 'Connecting' || /Waiting/.test(sim.status) ? 'wait' : ''}"></span>${esc(sim.status)}
      ${sim.connected ? `<button onclick="act(()=>api('/api/sim/disconnect',{}))">Disconnect</button>` : `<button onclick="simConnect()">Connect</button>`}</div>
    ${S && S.company ? `<div class="seg">Jet A ${S.company.fuel_price_usg.toFixed(2)}/USG base</div>
    <div class="seg">${af ? `Flight ${esc(af.flight_number)} ${af.origin}→${af.destination} · ${af.status}` : 'No flight dispatched'}</div>
    <div class="seg">${S.company.clock_mode === 'real' ? 'Real-time clock' : S.company.clock_mode === 'sim' ? 'Clock follows simulator' : `<button onclick="act(()=>api('/api/time/advance',{days:1}),'Advanced one day')">Next day</button> <button onclick="act(()=>api('/api/time/advance',{days:7}),'Advanced one week')">+7 days</button>`}</div>` : ''}
    <div class="seg">${S && S.company && S.company.dev_tools ? '<span class="tag warn">dev</span> · ' : ''}${themeControl()} · Operator 1.8.0 · ${S && S.slot ? 'save: ' + esc(S.slot) : 'local server'}</div>`;
}
function themeControl() {
  const m = localStorage.getItem('theme') || 'auto';
  const nxt = {auto: 'light', light: 'dark', dark: 'auto'}[m];
  const label = {auto: 'Theme: auto', light: 'Theme: light', dark: 'Theme: dark'}[m];
  return `<button onclick="setTheme('${nxt}')" title="Switch to ${nxt}">${label}</button>`;
}
async function simConnect() { toast('Connecting to simulator…'); await act(() => api('/api/sim/connect', {})); }
function manageTracking() {
  const af = S && S.active_flight;
  clearInterval(trkTimer); trkTimer = null;
  if (af && af.status === 'Tracking') trkTimer = setInterval(pollTracker, 2000), pollTracker();
  clearInterval(simTimer);
  simTimer = setInterval(async () => { try { const j = await api('/api/tracker'); if (S) { S.sim = j.sim; renderStatus(); } } catch (e) {} }, 5000);
  // sectors the crews are flying move on their own, so refresh while any are up
  clearInterval(airTimer); airTimer = null;
  if (S && (S.airborne || []).length && S.company && S.company.clock_mode !== 'game')
    airTimer = setInterval(() => { if (!$('#modal').innerHTML) load(); }, 30000);
}
function modal(title, body, footer, wide) {
  $('#modal').innerHTML = `<div class="modal-bg" onclick="if(event.target===this)closeModal()"><div class="modal" ${wide ? 'style="max-width:980px;width:90vw"' : ''}>
    <div class="hd">${esc(title)}<span class="x" onclick="closeModal()">✕</span></div><div class="bd">${body}</div>${footer ? `<div class="ft">${footer}</div>` : ''}</div></div>`;
}
function closeModal() { $('#modal').innerHTML = ''; }

/* The embedded WebView used by the desktop window does not implement window.confirm,
   so every confirmation goes through our own modal instead. */
let _askResolve = null;
function _askAnswer(yes) { closeModal(); const r = _askResolve; _askResolve = null; if (r) r(yes); }
function ask(text, opts) {
  opts = opts || {};
  return new Promise(resolve => {
    _askResolve = resolve;
    modal(opts.title || 'Confirm', `<p style="margin:0">${esc(text)}</p>`,
      `<button onclick="_askAnswer(false)">Cancel</button>` +
      `<button class="primary ${opts.danger ? 'danger' : ''}" onclick="_askAnswer(true)">${esc(opts.ok || 'Continue')}</button>`);
  });
}
function confirmDo(text, fn, opts) { ask(text, opts).then(yes => { if (yes) fn(); }); }
function tagStatus(s) {
  const cls = {Active: 'ok', Available: 'ok', Completed: 'grey', Terminated: 'bad', Cancelled: 'bad', Maintenance: 'warn', Delivery: 'info', 'Pending start': 'info', ACMI: 'info', Ferry: 'info', Training: 'warn', Open: 'ok', Accepted: 'info'}[s] || 'grey';
  return `<span class="tag ${cls}">${esc(s)}</span>`;
}

/* ------------------------------------------------------------ setup */
function viewSetup() {
  const apts = Object.keys(S.airports).filter(k => S.airports[k].large).sort();
  return `<div class="setup"><div class="panel"><div class="hd">Establish a new operator</div><div class="bd">
    <p class="hint">Set up your ferry and ACMI company. You start with founding capital, no aircraft, no crew and no ground staff. Ferry contracts need rated crew and a dispatcher; ACMI wet-lease contracts need your own aircraft, four pilots, cabin crew and a maintenance controller.</p>
    <div class="form">
      <label>Company name</label><input type="text" id="s-name" placeholder="e.g. Northline Aviation">
      <label>Airline code (2–3 letters)</label><input type="text" id="s-code" maxlength="3" placeholder="NLA">
      <label>Main base (ICAO)</label><select id="s-base">${apts.map(a => `<option value="${a}" ${a === 'EIDW' ? 'selected' : ''}>${a} — ${esc(S.airports[a].name)}, ${esc(S.airports[a].country)}</option>`).join('')}</select>
      <label>How to play</label><select id="s-mode" onchange="careerMode()">
        <option value="career" selected>Career — start small and work through objectives</option>
        <option value="free">Free play — everything open, capital of your choosing</option></select>
      <div></div><div id="s-modehint" class="hint"></div>
      <label>Founding capital</label><select id="s-cap"><option value="2400000">$2,400,000 — career start (a dispatcher, two pilots and ferry work)</option><option value="8000000">$8,000,000 — bootstrapped (ferry work, a leased turboprop or regional)</option><option value="25000000" selected>$25,000,000 — funded (one narrowbody lease and crew)</option><option value="90000000">$90,000,000 — well capitalised (widebody or small fleet)</option></select>
      <label>Difficulty</label><select id="s-diff">${Object.entries(S.difficulties).map(([k, d]) => `<option value="${k}" ${k === 'standard' ? 'selected' : ''}>${d.label} — ${esc(d.desc)}</option>`).join('')}</select>
      <label>SimBrief username</label><input type="text" id="s-sb" placeholder="optional, can be set later">
      <label>Simulator</label><select id="s-sim"><option value="auto">Auto-detect — recommended</option><option value="msfs">MSFS 2020/2024 or Prepar3D (SimConnect)</option><option value="xplane">X-Plane 11/12 (UDP)</option><option value="fsuipc">FSUIPC (FSX / P3D / MSFS)</option></select>
      <label>Types on the AOC</label><select id="s-types" onchange="aocTypesHint()">
        <option value="">No type restriction — every type is approved</option>
        ${Object.values(S.families || {}).sort((a, b) => a.cat === b.cat ? a.family.localeCompare(b.family) : a.cat.localeCompare(b.cat))
          .map(f => `<option value="${esc(f.family)}">${esc(f.family)} — ${esc(f.names.slice(0, 3).join(', '))}${f.names.length > 3 ? ', …' : ''}</option>`).join('')}
      </select>
      <div></div><div id="s-typehint" class="hint"></div>
    </div>
    <div class="actions"><button class="primary" onclick="createCompany()">Create company</button></div>
    <script>setTimeout(()=>{careerMode();aocTypesHint();}, 0);</script>
  </div></div></div>`;
}
function careerMode() {
  const career = ($('#s-mode') || {}).value !== 'free';
  const cap = $('#s-cap'), hint = $('#s-modehint');
  if (cap) { cap.value = career ? '2400000' : '25000000'; cap.disabled = career; }
  if (hint) hint.innerHTML = career
    ? 'You start with a dispatcher\'s desk and nothing else: no aircraft, and enough money to hire a crew and take your first ferry job. Objectives walk you through ferry work, then cargo crewing, then metal of your own. This is the way to learn the game.'
    : 'Nothing is gated and there are no objectives. Choose your own capital and start wherever you like.';
}
async function createCompany() {
  const career = ($('#s-mode') || {}).value !== 'free';
  await act(() => api('/api/company/new', {name: $('#s-name').value, code: $('#s-code').value, base: $('#s-base').value,
    capital: career ? 2400000 : $('#s-cap').value, career,
    simbrief_username: $('#s-sb').value, sim_source: $('#s-sim').value, difficulty: $('#s-diff').value,
    aoc_types: $('#s-types').value ? [$('#s-types').value] : []}), 'Company established');
}
/* A certificate issued for one type is how most small operators actually start, and it
   is the answer for anyone who wants the game to be about one aeroplane. */
function aocTypesHint() {
  const v = ($('#s-types') || {}).value, el = $('#s-typehint');
  if (!el) return;
  if (!v) { el.textContent = 'Your certificate carries no type restriction, so work on every type is offered. This is how Operator has always worked.'; return; }
  const f = (S.families || {})[v] || {}, band = (S.type_bands || {})[f.cat] || {};
  el.innerHTML = `Your AOC is issued for the <b>${esc(v)}</b> only — ${esc((f.names || []).join(', '))}. `
    + `Ferry, cargo, ACMI and charter work will only be offered on that type, and nothing else can be released under your certificate. `
    + `Adding another type later is an amendment: roughly ${usd(band.fee || 0)} and ${band.days || 30} days for a ${String(f.cat || '').toLowerCase()}, `
    + `cheaper and quicker for a second type from the same manufacturer. Pick this if you want the game to be about one aeroplane.`;
}

/* ------------------------------------------------------------ tutorial */
function tutorialSteps() {
  const ratedPair = fam => S.pilots.some(p => p.rank === 'CPT' && p.ratings.includes(fam)) && S.pilots.some(p => p.rank === 'FO' && p.ratings.includes(fam));
  const jobs = S.ferry_board.filter(j => j.status !== 'Open');
  const flown = S.flights.length > 0, tracked = S.flights.some(f => !f.manual);
  const acmi = S.contracts.length > 0, active = S.contracts.some(c => c.status === 'Active' || c.status === 'Completed');
  const fams = [...new Set(S.pilots.map(p => p.ratings).flat())];
  return [
    ['Ferry operation', [
      {t: 'Hire a flight dispatcher', done: S.staff.dispatcher >= 1, view: 'crew', why: 'No flight can be released without a licensed dispatcher on duty. Crew & staff → Ground staff → Flight dispatcher +1.'},
      {t: 'Hire a captain and a first officer with the same type rating', done: fams.some(ratedPair), view: 'crew', why: 'Ferry jobs need a rated CPT and FO. Pick candidates whose ratings match a job you want (the board shows "rating A320", "rating B737", etc.). A320 and B737 ratings cover most of the board.'},
      {t: 'Accept a ferry job that matches that rating', done: jobs.length > 0, view: 'ferry', why: 'Start short and simple: a standard-CofA job, no tech stop, no oceanic tag, a client hub near your base. Positioning tickets and permit fees are charged when you accept; the fee is paid on delivery.'},
      {t: 'Wait for or expedite the paperwork', done: jobs.some(j => j.docs.length && j.docs.every(d => d.ready <= S.clock)), view: 'ferry', why: 'Insurance, permits and export documents have lead times (Ferry board → My ferry jobs). Press Next day until every dot is filled, or Expedite for a fee. Watch the delivery deadline.'},
      {t: 'Dispatch the leg (SimBrief optional)', done: flown || !!S.active_flight, view: 'dispatch', why: 'Dispatch → Ferry job leg. The form fills in from the job, so you can press Dispatch straight away. SimBrief is optional: if you use it, Send opens the plan pre-filled and Fetch brings back route, fuel and weights. If the job needs a tech stop, file to the stop first; the next leg departs from wherever the aircraft is.'},
      {t: 'Connect the simulator and start tracking', done: tracked || (S.sim.connected && !!S.active_flight), view: 'dispatch', why: 'Load the aircraft cold at the gate, press Connect in the status bar, then Start tracking on the active flight. Fly the plan; keep to any permit limits shown in red.'},
      {t: 'Shut down and file the PIREP', done: flown, view: 'dispatch', why: 'Taxi in, parking brake, engines off, then File PIREP. The landing is analysed, the fee is invoiced when the aircraft reaches the job destination, and crew duty time is logged.'},
    ]],
    ['Cargo contract flying', [
      {t: 'Accept a cargo pairing', done: S.cargo_board.some(j => j.status !== 'Open'), view: 'cargo', why: 'Real freight carriers hire contract crews. You need only a rated captain and first officer — the carrier supplies the aircraft, fuel and load. Start with a short two-sector night pattern.'},
      {t: 'Fly the sectors in order', done: S.flights.some(f => f.kind === 'cargo'), view: 'dispatch', why: 'Dispatch → Cargo pairing sector. The payload is set by the carrier, so run the runway analysis: a heavy freight leg out of a short field is where this gets interesting.'},
      {t: 'Complete a pairing and get paid', done: S.cargo_board.some(j => j.status === 'Completed'), view: 'cargo', why: 'Payment covers block hours plus a day rate for both crew and lands when the last sector is flown. Miss the roster window and the carrier covers the sectors itself and deducts a quarter of the fee.'},
    ]],
    ['ACMI operation', [
      {t: 'Lease or buy an aircraft', done: S.fleet.length > 0, view: 'market', why: 'ACMI needs your own metal. A leased A320/737-800 is the usual first step: 3-month deposit plus first month. Check engine hours to shop visit and ETOPS status on the listing.'},
      {t: 'Hire a maintenance controller', done: S.staff.mx_controller >= 1, view: 'crew', why: 'Fleet aircraft cannot be dispatched without one per 4 aircraft.'},
      {t: 'Build a crew: 2 captains, 2 first officers, cabin crew', done: S.pilots.filter(p => p.rank === 'CPT').length >= 2 && S.pilots.filter(p => p.rank === 'FO').length >= 2 && S.staff.cabin_crew >= 4, view: 'crew', why: 'Two crew sets rated on the type, plus cabin crew (2 sets: 4 on a narrowbody, 8 on a widebody, 2 on regional/turboprop). Flight-duty limits mean one crew cannot fly a full day.'},
      {t: 'Sign an ACMI tender', done: acmi, view: 'tenders', why: 'Pick a tender for the exact type you have. Read the minimum guarantee, hub and start date. Livery/reconfiguration takes 3 days.'},
      {t: 'Position the aircraft at the customer hub before the start date', done: active, view: 'dispatch', why: 'Dispatch → Positioning → your aircraft, destination = hub. The contract goes Active on the start date once the aircraft is there. Seven days late and the customer walks.'},
      {t: 'Fly the daily rotation', done: S.flights.some(f => f.kind === 'acmi'), view: 'dispatch', why: 'Dispatch → ACMI rotation leg shows the day\'s legs with departure times. Block hours are invoiced per leg; the month-end true-up pays any shortfall against the guarantee. Keep utilisation above 10% to avoid a notice, and watch satisfaction for an extension offer.'},
    ]],
  ];
}
function viewTutorial() {
  if (S.company.tutorial_hidden) return '';
  // in career mode the objectives do this job, and better
  if (S.career && S.career.enabled) return '';
  // before any work is taken on, one clear instruction beats sixteen steps
  if (firstStep()) return '';
  const groups = tutorialSteps();
  const all = groups.flatMap(g => g[1]);
  const doneN = all.filter(s => s.done).length;
  const next = all.find(s => !s.done);
  return `<div class="panel"><div class="hd">Getting started — ${doneN} of ${all.length} steps <div class="tools"><button class="sm" onclick="act(()=>api('/api/company/settings',{tutorial_hidden:true}),'Tutorial hidden (re-enable in Help)')">Hide</button></div></div><div class="bd">
    <div class="row">${groups.map(([name, steps]) => `<div class="col"><div style="font-weight:600;margin-bottom:4px">${name}</div><table class="grid">${steps.map(st => `<tr class="${st === next ? 'sel' : ''}"><td style="width:18px">${st.done ? '<span class="pos">●</span>' : st === next ? '<span class="tag info">next</span>' : '○'}</td><td>${esc(st.t)}</td><td class="r"><button class="sm" onclick="nav('${st.view}')">Open</button></td></tr>`).join('')}</table></div>`).join('')}</div>
    ${next ? `<div class="msg ok" style="margin:10px 0 0"><b>Next: ${esc(next.t)}.</b> ${esc(next.why)}</div>` : '<div class="msg ok" style="margin:10px 0 0">You have run both lines of business. From here: grow the fleet, take widebody work at reputation 55, and keep satisfaction high for extensions.</div>'}
  </div></div>`;
}
const HELP = {
  dashboard: '',
  fleet: 'Each aircraft shows hours to the next A-check, the C-check date and the engine closest to its shop-visit limit. Anything overdue blocks dispatch. Log opens the airframe record; PBH moves engine risk to a fixed hourly rate.',
  market: 'Buying ties up cash but the aircraft is an asset on your balance sheet; leasing needs a 3-month deposit and a monthly rent for the minimum term. Look at year, engine hours to shop visit and ETOPS status, and where the aircraft is parked — you will have to position it.',
  credits: 'Data and branding sources for everything shipped with Operator.',
  crew: 'A type rating covers a whole family: one A320 rating covers the A319, A320 and A321 including the neos, and a B757/767 rating covers both. Hover a rating to see what it covers. Every flight needs a commander: a captain in the left seat. The second seat may be a captain or a first officer, so two captains can crew a sector together, but two first officers cannot. ACMI contracts need four pilots with at least two captains. First officers with enough total time and enough hours with your company can be upgraded to captain: a paid command course, four weeks off the roster, then the captain pay scale. Pilots also receive a seniority increment each year of service. Ground staff are headcounts; pilots are individuals with type ratings, duty time and rest. Currency: three landings on type in the last 90 days, or a recency detail from the ratings menu. Type-rating courses take 21 days.',
  schedule: 'Every commitment across the fleet on one timeline: charter trips, ACMI rotations, the flight in the air, maintenance under way and checks falling due. The red line is now. Underneath, anything that will not fit — an aircraft in the wrong place for a booked trip, a deadline you cannot make, no rated captain available — and the work you have accepted that is flown on someone else\'s aircraft.',
  charter: 'Charter comes in two kinds. Business aircraft fly small parties at a price you set: brokers post enquiries, you quote, and quoting under the going rate wins more of them. Group charter is a whole airliner hired by one party — a tour operator, a football club, a troop rotation, a cruise line — priced by the block hour for the aircraft, and needing enough seats, hold space and rostered cabin crew. Either way, positioning to the client and home again is at your cost, and passengers judge comfort and punctuality.',
  cargo: 'Contract crew flying: real cargo carriers hire your rated crews to operate their aircraft on a published pattern of sectors. No aircraft or ground staff of your own beyond a dispatcher, so it is the cheapest way to earn while you build a fleet. Fly the sectors in order from Dispatch; payment lands when the pairing is complete.',
  ferry: 'Deferred defects are flown, not simulated: Operator checks the altitude, speed, gear and routing you actually used, so an aircraft with no failure system just flies the restriction by hand. Each defect has a "how to fly this" note. Long sectors are planned with technical stops the type can actually make, using runways long enough for it — Dispatch offers each leg in turn. Click any document to read it. Open jobs show the permit basis, deferred defects (hover a code for its effect), tech stop and oceanic/ETOPS flags. After accepting, "My ferry jobs" tracks paperwork (●/○), defects, deadline and legs flown. Expedite speeds up permits; Rectify clears defects for a fee.',
  tenders: 'A wet lease: you supply Aircraft, Crew, Maintenance, Insurance; the customer pays fuel, fees and a minimum block-hour guarantee. Competing bidders can close a tender early. Rates are seasonal; extension offers come from satisfied customers.',
  contracts: 'Per contract: hours this month against the guarantee, rotation completion, on-time performance and the resulting satisfaction score. Two non-performance notices terminate the contract; satisfaction ≥ 70 at term end earns an extension offer.',
  dispatch: 'Runway analysis & loadsheet checks the runway at both ends against your weight, temperature, wind and runway state, and works out the CG — sliders move the load forward or aft, ballast trims an empty ferry. Choose the flight type and let the form pre-fill from the job, contract rotation or aircraft. If you use SimBrief, Send and Fetch will fill in route, fuel and weights for you; if not, type them in or just press Dispatch with the pre-filled figures. With the aircraft loaded cold at the gate, Connect and Start tracking. Shut down at the gate before filing the PIREP.',
  safety: 'Your safety record and the things currently raising risk. Every sector carries a small chance of an occurrence; fatigue, deferred defects, overdue maintenance, old airframes, weather and thin runway margins all multiply it. Incidents cost money and downtime; accidents are rare and serious. Turn the whole system off in Settings if you would rather not have it.',
  logbook: 'Every filed sector with landing data and net result. View opens the full PIREP with landing analysis; Export CSV and Print/PDF give you a personal logbook.',
  finance: 'Customers pay on terms, so revenue is invoiced first and banked later — watch the receivables table before committing to a lease. The ledger is every cash movement. Fixed costs (leases, salaries, insurance, overheads) post on the 1st; the term loan is secured on owned aircraft.',
  analytics: 'The shape of the company over time: cash and equity, revenue by line of business, where the costs go, how your landings are trending, fleet utilisation and reputation. Month-end snapshots build these, so the first points appear after your first month closes. Below: the company history and printable annual reports.',
  statements: 'Income statement grouped by category, a balance sheet (cash, book value of owned aircraft, deposits, loans) and block hours per aircraft per month.',
  company: 'Upload your logo here. Reputation grows with clean, completed work; widebody ferry and ACMI opportunities open at 55.',
  settings: 'SimBrief identity, simulator connection, clock mode and the Jet A base price. Discord webhook posts each PIREP.',
  saves: 'Multiple companies live in separate save slots. Download a backup before experimenting; restore overwrites the current slot.',
};
function helpStrip() {
  const h = HELP[VIEW]; if (!h) return '';
  const hidden = localStorage.getItem('help-' + VIEW) === '0';
  return `<div class="msg" style="border-color:var(--line);background:var(--subtle);color:var(--muted);display:flex;gap:10px;align-items:flex-start"><span style="flex:1">${hidden ? '' : esc(h)}</span><button class="sm" onclick="localStorage.setItem('help-${VIEW}','${hidden ? '1' : '0'}');render()">${hidden ? 'Show help' : 'Hide'}</button></div>`;
}

/* ------------------------------------------------------------ dashboard */
/* A free-play company gets no objectives, so someone who has never accepted anything
   can sit waiting for work to arrive. It is already on the boards; point at it. */
function firstStep() {
  if (S.flights.length || S.ferry_board.some(j => j.status !== 'Open') || S.cargo_board.some(j => j.status !== 'Open')
      || S.contracts.length || (S.charter_jobs || []).length) return '';
  const ferry = S.ferry_board.filter(j => j.status === 'Open').length;
  const cargo = S.cargo_board.filter(j => j.status === 'Open').length;
  const rated = new Set(S.pilots.flatMap(p => p.ratings));
  const crewed = S.ferry_board.filter(j => j.status === 'Open' && rated.has(j.family)).length;
  const needDispatcher = (S.staff.dispatcher || 0) < 1;
  const needCrew = !S.pilots.some(p => p.rank === 'CPT') || !S.pilots.some(p => p.rank === 'FO');
  let what, why, where, label;
  if (needDispatcher) {
    what = 'Hire a flight dispatcher';
    why = 'No flight can be released without one on duty. Crew &amp; staff → Ground staff → Flight dispatcher +1.';
    where = 'crew'; label = 'Crew &amp; staff';
  } else if (needCrew) {
    what = 'Hire a captain and a first officer on the same type rating';
    why = 'Every flight needs a commander and a second pilot, both rated on the aircraft they are flying.';
    where = 'crew'; label = 'Crew &amp; staff';
  } else {
    what = `Accept a job — ${ferry} ferry job${ferry === 1 ? '' : 's'} and ${cargo} cargo pairing${cargo === 1 ? '' : 's'} are waiting`;
    why = `Work does not need generating: it is already on the boards. ${crewed ? `${crewed} ferry job${crewed === 1 ? '' : 's'} match the ratings your crew hold` : 'Match a job to the ratings your crew hold'} — open the board and press Accept. Paperwork starts then, and you dispatch it once it is ready.`;
    where = 'ferry'; label = 'Ferry board';
  }
  return `<div class="panel" style="border-left:3px solid var(--accent)">
    <div class="hd">Getting your first job <div class="tools hint">you have not taken on any work yet</div></div>
    <div class="bd">
      <div style="display:flex;gap:14px;align-items:flex-start;flex-wrap:wrap">
        <div style="flex:1;min-width:300px"><b>${what}</b><div class="hint" style="margin-top:3px">${why}</div></div>
        <button class="primary" onclick="nav('${where}')">${label}</button>
      </div>
      <ol style="margin:10px 0 0 18px;padding:0;color:var(--muted);font-size:12px">
        <li${needDispatcher ? '' : ' style="opacity:.5"'}>Hire a flight dispatcher${needDispatcher ? '' : ' — done'}</li>
        <li${needCrew ? '' : ' style="opacity:.5"'}>Hire a captain and a first officer on the same type rating${needCrew ? '' : ' — done'}</li>
        <li>Accept one of the ${ferry} ferry jobs or ${cargo} cargo pairings already on the boards</li>
        <li>Wait for the paperwork, then dispatch the sector and fly it</li>
        <li>Shut down at the gate and file the PIREP</li>
      </ol>
      <p class="hint" style="margin:8px 0 0">Nothing needs generating, and you need neither SimBrief nor FSUIPC to fly any of it.</p>
    </div></div>`;
}

function coach() {
  const c = S.career;
  if (!c || !c.enabled || !c.current) return firstStep();
  const g = c.current;
  return `<div class="panel" style="border-left:3px solid var(--accent)">
    <div class="hd">Next step <div class="tools hint">${g.chapter} · ${c.done} of ${c.total} objectives done</div></div>
    <div class="bd"><div style="display:flex;gap:14px;align-items:flex-start;flex-wrap:wrap">
      <div style="flex:1;min-width:280px"><b>${esc(g.text)}</b><div class="hint" style="margin-top:3px">${esc(g.why)}</div></div>
      <button class="primary" onclick="nav('${g.go}')">Take me there</button>
      <button class="sm" onclick="nav('career')">All objectives</button>
    </div></div></div>`;
}
function viewDashboard() {
  const act_ = S.contracts.filter(c => c.status === 'Active' || c.status === 'Pending start');
  const jobs = S.ferry_board.filter(j => j.status === 'Accepted');
  const mr = S.month_reports[0];
  const warn = [];
  if (S.staff.dispatcher < S.dispatchers_needed) warn.push(`No dispatcher on duty (${S.staff.dispatcher}/${S.dispatchers_needed}) — flights cannot be released.`);
  if (S.fleet.length && S.staff.mx_controller < S.mx_needed) warn.push(`Maintenance controllers short (${S.staff.mx_controller}/${S.mx_needed}) — fleet aircraft cannot be dispatched.`);
  S.fleet.forEach(a => { if (a.fh_since_a >= S.a_check_fh) warn.push(`${a.reg} A-check overdue.`); if (!a.pbh && a.engines.some(e => e.hours_to_sv <= 0)) warn.push(`${a.reg} engine at shop-visit limit.`); });
  jobs.forEach(j => { const p = j.docs.filter(d => d.ready > S.clock); if (p.length) warn.push(`Job #${j.id}: ${p.length} permit(s) outstanding, latest ${dd(p.map(d => d.ready).sort().pop())}.`); });
  return `${coach()}<div class="row"><div class="col">
    ${warn.length ? `<div class="msg warn">${warn.map(esc).join('<br>')}</div>` : ''}
    <div class="panel"><div class="hd">Operations summary</div><div class="bd"><div class="kv">
      <div>Game clock</div><div>${dt(S.clock)} <span class="hint">(${S.company.clock_mode === 'game' ? 'game time' : S.company.clock_mode === 'sim' ? 'follows simulator' : 'real time'})</span></div>
      <div>Cash</div><div class="${S.cash < 0 ? 'neg' : ''}">${usd(S.cash)}</div>
      <div>Last month net</div><div>${mr ? `<span class="${mr.net < 0 ? 'neg' : 'pos'}">${usd(mr.net)}</span> (${esc(mr.month)})` : 'no month closed yet'}</div>
      <div>Fleet</div><div>${S.fleet.length} aircraft (${S.fleet.filter(a => a.status === 'ACMI').length} on ACMI, ${S.fleet.filter(a => a.status === 'Maintenance').length} in maintenance)</div>
      <div>People</div><div>${S.pilots.filter(p => p.rank === 'CPT').length} captains, ${S.pilots.filter(p => p.rank === 'FO').length} first officers, ${S.staff.cabin_crew} cabin crew, ${S.staff.dispatcher} dispatchers, ${S.staff.mx_controller} maintenance controllers</div>
      <div>Flights flown</div><div>${S.stats.flights} · ${n1(S.stats.hours)} block hours · ${n1(S.stats.nm)} nm</div>
      <div>Market</div><div>Passenger ACMI demand ${S.season.pax > 1 ? 'high (peak season)' : S.season.pax < 1 ? 'low (off season)' : 'normal'} · cargo ${S.season.cargo > 1 ? 'peak' : S.season.cargo < 1 ? 'slack' : 'normal'}</div>
      <div>Reputation</div><div>${S.company.reputation.toFixed(1)} / 100 ${S.company.reputation < 55 ? '<span class="hint">(widebody work opens at 55)</span>' : ''}</div>
    </div></div></div>
    <div class="panel"><div class="hd">ACMI contracts <div class="tools"><button class="sm" onclick="nav('contracts')">Open</button></div></div><div class="bd tight">
      ${act_.length ? `<table class="grid"><tr><th>Customer</th><th>Aircraft</th><th>Hub</th><th>Status</th><th class="r">BH month</th><th class="r">Min</th><th class="r">Satisfaction</th><th>Ends</th></tr>
      ${act_.map(c => `<tr><td>${opLogo(c.customer, 22)}${esc(c.customer)}</td><td>${c.reg} <small>${c.type}</small></td><td>${c.hub}</td><td>${tagStatus(c.status)}</td><td class="num">${n1(c.hours_month)}</td><td class="num">${c.min_hours}</td><td class="num">${c.kpi.satisfaction}</td><td>${dd(c.end)}</td></tr>`).join('')}</table>`
      : '<div class="bd hint">No ACMI contracts. Review tenders to place your aircraft with an airline.</div>'}</div></div>
    <div class="panel"><div class="hd">Ferry jobs in progress</div><div class="bd tight">
      ${jobs.length ? `<table class="grid"><tr><th>Job</th><th>Aircraft</th><th>Routing</th><th>Now at</th><th>Paperwork</th><th>Deadline</th><th class="r">Fee</th></tr>
      ${jobs.map(j => { const p = j.docs.filter(d => d.ready > S.clock).length; return `<tr><td>#${j.id} ${esc(j.kind)}<br><small>${opLogo(j.client, 20)}${esc(j.client)}</small></td><td>${j.reg} <small>${j.type}</small></td><td>${j.origin} → ${j.destination}</td><td>${j.current}</td><td>${p ? `<span class="tag warn">${p} pending</span>` : '<span class="tag ok">Complete</span>'}</td><td>${dd(j.deadline)}</td><td class="num">${usd(j.fee)}</td></tr>`; }).join('')}</table>`
      : '<div class="bd hint">No ferry jobs accepted.</div>'}</div></div>
  </div><div class="col" style="max-width:460px">
    <div class="panel"><div class="hd">Current flight</div><div class="bd">${S.active_flight ? `
      <div class="kv"><div>Flight</div><div>${esc(S.active_flight.flight_number)} · ${S.active_flight.type} ${S.active_flight.reg}</div>
      <div>Routing</div><div>${S.active_flight.origin} → ${S.active_flight.destination}</div><div>Status</div><div>${S.active_flight.status}</div></div>
      <div class="actions"><button onclick="nav('dispatch')">Go to dispatch</button></div>` : '<span class="hint">Nothing dispatched.</span> <button class="sm" onclick="nav(\'dispatch\')">Dispatch a flight</button>'}</div></div>
    ${viewInbox()}
    <div class="panel"><div class="hd">Activity log</div><div class="bd"><ul class="notices">${S.notices.slice(0, 12).map(n => `<li><span>${dd(n.date)}</span>${esc(n.text)}</li>`).join('') || '<li class="hint">—</li>'}</ul></div></div>
  </div></div>`;
}
function viewInbox() {
  const unread = S.inbox.filter(m => !m.read).length;
  const pinned = S.inbox.filter(m => m.pin), rest = S.inbox.filter(m => !m.pin).slice(0, 12);
  const row = m => `<div style="padding:5px 0;border-bottom:1px solid var(--line-soft)${m.read ? ';color:var(--muted)' : ''}">
    <div style="display:flex;gap:8px;align-items:baseline"><span style="font-variant-numeric:tabular-nums;font-size:11px;color:var(--muted)">${dd(m.date)}</span><b style="${m.read ? 'font-weight:500' : ''}">${esc(m.sender)}</b>${m.pin ? '<span class="tag warn">action</span>' : ''}<span style="margin-left:auto;white-space:nowrap">${m.action ? `<button class="sm" onclick="act(()=>api('/api/inbox/read',{id:${m.id}}));nav('${m.action}')">Open</button> ` : ''}${m.read ? '' : `<button class="sm" onclick="act(()=>api('/api/inbox/read',{id:${m.id}}))">Read</button>`}</span></div>
    <div style="font-weight:600;font-size:12.5px">${esc(m.subject)}</div><div style="font-size:12px">${esc(m.body)}</div></div>`;
  return `<div class="panel"><div class="hd">Ops inbox${unread ? ` <span class="tag info">${unread} unread</span>` : ''} <div class="tools">${unread ? `<button class="sm" onclick="act(()=>api('/api/inbox/read',{}))">Mark all read</button>` : ''}</div></div><div class="bd" style="max-height:60vh;overflow:auto">${pinned.map(row).join('')}${rest.map(row).join('') || '<span class="hint">No messages.</span>'}</div></div>`;
}

/* ------------------------------------------------------------ company */
function areasPanel() {
  const have = S.aoc_areas || [], pend = S.aoc_pending || [], R = S.regions || {}, costs = S.area_costs || {};
  return `<div class="panel"><div class="hd">Areas of operation <div class="tools hint">operations specifications on your air operator certificate</div></div>
    <div class="bd">
      <p style="margin:0 0 10px">Your certificate authorises the areas below. Work is only offered inside them, and a
      sector to a field outside them cannot be released. Adding an area is an amendment the authority charges for and
      takes a few weeks over.</p>
      <table class="grid">
        <tr><th>Area</th><th>Covers</th><th>Status</th><th class="r">Fee</th><th></th></tr>
        ${Object.entries(R).map(([k, r]) => {
          const held = have.includes(k), p = pend.find(x => x.region === k), c = costs[k];
          return `<tr><td><b>${esc(r.name)}</b></td><td class="hint">${esc(r.blurb)}</td>
            <td>${held ? '<span class="tag ok">on the certificate</span>'
              : p ? `<span class="tag warn">with the authority</span><br><small class="hint">decision by ${dd(p.ready)}</small>`
              : `<span class="tag grey">not authorised</span>${c && c.rep ? `<br><small class="hint">needs ${c.rep} reputation</small>` : ''}`}</td>
            <td class="num">${held || p ? '—' : usd((c || {}).fee || 0)}</td>
            <td>${held || p ? '' : `<button class="sm" ${c && S.company.reputation < c.rep ? 'disabled' : ''}
              onclick="applyArea('${k}')">Apply (${(c || {}).days || 0} days)</button>`}</td></tr>`;
        }).join('')}
      </table>
    </div></div>`;
}
/* Types on the operations specifications. Only drawn when the certificate is actually
   restricted — a company issued without a type limit has nothing to manage here. */
function typesPanel() {
  const have = S.aoc_types || [];
  if (!have.length) return '';
  const pend = S.aoc_types_pending || [], costs = S.type_costs || {}, F = S.families || {};
  const order = ['Turboprop', 'Light jet', 'Midsize jet', 'Super-midsize jet', 'Heavy jet', 'Regional', 'Narrowbody', 'Widebody'];
  const rows = Object.values(F).sort((a, b) => {
    const ha = have.includes(a.family), hb = have.includes(b.family);
    if (ha !== hb) return ha ? -1 : 1;
    const ca = order.indexOf(a.cat), cb = order.indexOf(b.cat);
    return ca === cb ? a.family.localeCompare(b.family) : ca - cb;
  });
  return `<div class="panel"><div class="hd">Types on the certificate <div class="tools hint">operations specifications · ${have.length} approved</div></div>
    <div class="bd">
      <p style="margin:0 0 10px">Your air operator certificate names the types you may operate. Work is only offered
      on those types and nothing else can be released under it — you may still own an aircraft you are not approved
      for, but it stays on the ground. Adding a type means a training programme, a maintenance programme, manuals and
      a proving flight, so the authority charges for it and takes its time. A second type from a manufacturer already
      on your certificate is cheaper and quicker.</p>
      <table class="grid">
        <tr><th>Type rating</th><th>Covers</th><th>Class</th><th>Status</th><th class="r">Fee</th><th></th></tr>
        ${rows.map(f => {
          const held = have.includes(f.family), p = pend.find(x => x.family === f.family), c = costs[f.family];
          return `<tr><td><b>${esc(f.family)}</b><br><small class="hint">${esc(f.mfr)}</small></td>
            <td class="hint">${esc(f.names.join(', '))}</td><td>${esc(f.cat)}</td>
            <td>${held ? '<span class="tag ok">on the certificate</span>'
              : p ? `<span class="tag warn">with the authority</span><br><small class="hint">decision by ${dd(p.ready)}</small>`
              : `<span class="tag grey">not approved</span>${c && c.rep ? `<br><small class="hint">needs ${c.rep} reputation</small>` : ''}`}</td>
            <td class="num">${held || p ? '—' : usd((c || {}).fee || 0)}${c && c.same_mfr && !held && !p ? '<br><small class="pos">same manufacturer</small>' : ''}</td>
            <td>${held || p ? '' : `<button class="sm" ${c && S.company.reputation < c.rep ? 'disabled' : ''}
              onclick="applyType('${esc(f.family)}')">Apply (${(c || {}).days || 0} days)</button>`}</td></tr>`;
        }).join('')}
      </table>
    </div></div>`;
}
async function applyType(family) {
  const c = (S.type_costs || {})[family] || {}, f = (S.families || {})[family] || {};
  confirmDo(`Apply to add the ${family} to your operations specifications? The fee is ${usd(c.fee)} and the authority `
    + `will take about ${c.days} days over the training programme, the maintenance programme, the manuals and a proving flight.`
    + (c.same_mfr ? ` Your existing ${f.mfr} approval shortens the review.` : ''),
    () => act(() => api('/api/company/type', {family}), 'Application lodged'), {ok: 'Apply'});
}
async function applyArea(region) {
  const r = S.regions[region], c = (S.area_costs || {})[region] || {};
  confirmDo(`Apply to add ${r.name} to your operations specifications? The fee is ${usd(c.fee)} and the authority ` +
    `will take about ${c.days} days to review your procedures, crew licensing and maintenance arrangements for the area.`,
    () => act(() => api('/api/company/area', {region}), 'Application lodged'), {ok: 'Apply'});
}
function viewCompany() {
  const co = S.company;
  return `${areasPanel()}${typesPanel()}<div class="row"><div class="col">
    <div class="panel"><div class="hd">Company logo <div class="tools"><input type="file" id="logo-file" accept="image/*" style="width:auto" onchange="uploadLogo(this)">${co.logo ? '<button class="sm" onclick="act(()=>api(\'/api/company/logo\',{data:null}),\'Logo removed\')">Remove</button>' : ''}</div></div>
      <div class="bd"><div class="logo-box">${co.logo ? `<img src="${co.logo}" alt="${esc(co.name)} logo">` : '<div class="empty">No logo uploaded.<br>PNG or SVG with transparent background works best. It is shown here and in the title bar.</div>'}</div></div></div>
  </div><div class="col" style="max-width:520px">
    <div class="panel"><div class="hd">Operator details</div><div class="bd"><div class="kv">
      <div>Name</div><div>${esc(co.name)}</div><div>Code</div><div>${esc(co.code)}</div>
      <div>Main base</div><div>${co.base} — ${esc(S.airports[co.base].name)}, ${esc(S.airports[co.base].country)}</div>
      <div>AOC issued</div><div>${dd(co.founded)}</div><div>Difficulty</div><div>${esc(S.difficulties[co.difficulty].label)}</div><div>Reputation</div><div>${co.reputation.toFixed(1)} / 100</div>
      <div>Total flights</div><div>${S.stats.flights}</div><div>Block hours</div><div>${n1(S.stats.hours)}</div><div>Distance flown</div><div>${n1(S.stats.nm)} nm</div>
      <div>Owned fleet value</div><div>${usd(S.fleet.filter(a => a.owned).reduce((s, a) => s + a.value, 0))}</div>
    </div></div></div>
    <div class="panel"><div class="hd">Milestones <div class="tools hint">${Object.keys(S.achievements).length} of ${S.achievement_defs.length}</div></div><div class="bd tight"><table class="grid">${S.achievement_defs.map(([k, t, d]) => `<tr style="${S.achievements[k] ? '' : 'color:var(--muted)'}"><td style="width:18px">${S.achievements[k] ? '<span class="pos">●</span>' : '○'}</td><td><b>${esc(t)}</b><br><small>${esc(d)}</small></td><td class="r"><small>${S.achievements[k] ? dd(S.achievements[k]) : ''}</small></td></tr>`).join('')}</table></div></div>
    <div class="panel"><div class="hd">Contract history</div><div class="bd tight"><table class="grid"><tr><th>Customer</th><th>Type</th><th>Term</th><th>Outcome</th><th class="r">Satisfaction</th><th class="r">Revenue</th></tr>
      ${S.contracts.map(c => `<tr><td>${esc(c.customer)}${c.renewal ? ' <span class="tag info">renewal</span>' : ''}</td><td>${c.type}</td><td>${c.months} mo</td><td>${tagStatus(c.status)}</td><td class="num">${c.kpi.satisfaction}</td><td class="num">${usd(c.revenue_total)}</td></tr>`).join('') || '<tr><td colspan="6" class="hint">No contracts yet.</td></tr>'}</table></div></div>
  </div></div>`;
}
function uploadLogo(inp) { const f = inp.files[0]; if (!f) return; const r = new FileReader(); r.onload = () => act(() => api('/api/company/logo', {data: r.result}), 'Logo updated'); r.readAsDataURL(f); }

/* ------------------------------------------------------------ fleet */
function viewFleet() {
  return `<div class="panel"><div class="hd">Fleet <div class="tools hint">A-check every ${S.a_check_fh} FH · C-check every 24 months · engines tracked to shop visit</div></div><div class="bd tight">
    <table class="grid"><tr><th>Reg</th><th>Type</th><th>Config</th><th class="r">Range</th><th class="r">Year</th><th class="r">Hours</th><th class="r">FH to A</th><th>C-check</th><th class="r">Engine SV in</th><th>Location</th><th>Ownership</th><th>Status</th><th></th></tr>
    ${S.fleet.map(a => { const aLeft = S.a_check_fh - a.fh_since_a, cWarn = a.c_check_due < S.clock, esv = Math.min(...a.engines.map(e => e.hours_to_sv));
      return `<tr><td><b><a href="#" onclick="aircraftRecord(${a.id});return false">${a.reg}</a></b> <a href="#" class="hint" title="Re-register, name or number this aircraft" onclick="renameAc(${a.id});return false">edit</a>${a.fleet_no ? `<br><small class="hint">fleet no ${esc(a.fleet_no)}</small>` : ''}${a.nickname ? `<br><small>${esc(a.nickname)}</small>` : ''}${a.livery ? `<br><small>${esc(a.livery)} livery</small>` : ''}${a.etops ? '' : '<br><small class="neg">non-ETOPS</small>'}</td><td>${esc(a.name)} <small>${a.type}</small>${S.aircraft_types[a.type] && S.aircraft_types[a.type].cargo ? ' <span class="tag grey">freighter</span>' : ''}</td><td>${esc(a.config)}</td><td class="num">${n1((S.aircraft_types[a.type] || {}).range_nm)} nm<br><small class="hint">${n1((S.aircraft_types[a.type] || {}).cruise)} kt</small></td>
      <td class="num">${a.year}</td><td class="num">${n1(a.hours)}<br><small class="hint">${n1(a.cycles)} cyc</small></td>
      <td class="num ${aLeft < 90 ? 'neg' : ''}">${Math.round(aLeft)}</td><td class="${cWarn ? 'neg' : ''}">${dd(a.c_check_due)}</td><td class="num ${esv < 300 ? 'neg' : ''}">${Math.round(esv)}${a.pbh ? ' <small>PBH</small>' : ''}</td><td>${ap(a.location)}${a.delivery ? '<br><small class="hint">in transit</small>' : ''}</td>
      <td>${a.owned ? 'Owned' : `Leased <small>${esc(a.lessor)} · ${usd(a.lease)}/mo to ${dd(a.lease_end)}</small>`}</td>
      <td>${tagStatus(a.status)}${a.mx_reason ? `<br><small>${esc(a.mx_reason)} until ${dd(a.mx_until)}</small>` : ''}${a.contract_id ? `<br><small>contract #${a.contract_id}</small>` : ''}${a.snags.length ? `<br><small class="neg">${a.snags.length} open defect(s)</small>` : ''}${a.delivery ? `<br><small>${a.delivery.origin} → ${a.delivery.destination}, arrives ${dd(a.delivery.eta)}</small>` : ''}</td>
      <td ${nw}><button class="sm" onclick="airframe(${a.id})">Log</button> <button class="sm" onclick="mx(${a.id},'A')">A</button> <button class="sm" onclick="mx(${a.id},'C')">C</button> <button class="sm" onclick="mx(${a.id},'ESV')">Engine SV</button> <button class="sm" onclick="act(()=>api('/api/fleet/pbh',{id:${a.id},on:${!a.pbh}}),'Updated')">${a.pbh ? 'Leave PBH' : 'PBH'}</button> <button class="sm danger" onclick="disposeAc(${a.id})">${a.owned ? 'Sell' : 'Return'}</button></td></tr>`; }).join('')
      || '<tr><td colspan="13" class="hint">No aircraft. Visit the aircraft market to buy or lease.</td></tr>'}</table></div></div>
    <p class="hint">PBH: power-by-the-hour engine support from the OEM. You pay a fixed rate per flight hour and shop visits are covered; without it you pay the full shop-visit cost when an engine reaches its limit.</p>`;
}
function airframe(id) {
  const a = S.fleet.find(x => x.id === id);
  const fl = S.flights.filter(f => f.aircraft_id === id);
  modal(`Airframe log — ${a.reg} ${a.name}`, `<div class="row"><div class="col"><div class="kv"><div>Built</div><div>${a.year}</div><div>Total time</div><div>${n1(a.hours)} h / ${n1(a.cycles)} cycles</div><div>Book value</div><div>${usd(a.value)}</div><div>ETOPS</div><div>${a.etops ? 'Approved' : 'Not approved'}</div>
    <div>Engines</div><div>${a.engines.map(e => `#${e.pos}: ${Math.round(e.hours_to_sv)} h to shop visit`).join('<br>')} <small>(${esc(S.engine_oem[a.family])}${a.pbh ? ', PBH' : ''})</small></div>
    <div>Open defects</div><div>${a.snags.map(s => esc(s.name)).join('<br>') || 'none'}</div></div>
    <h2 style="margin-top:10px">Maintenance</h2><table class="grid">${a.mx_log.map(m => `<tr><td>${dd(m.date)}</td><td>${esc(m.text)}</td></tr>`).join('')}</table></div>
    <div class="col"><h2>Sectors (${fl.length})</h2><div class="wrap-scroll"><table class="grid"><tr><th>Date</th><th>Flight</th><th>Sector</th><th class="r">Block</th><th class="r">TD</th><th class="r">Score</th></tr>${fl.map(f => `<tr><td>${dd(f.filed)}</td><td>${esc(f.flight_number)}</td><td>${f.origin}–${f.arrival}</td><td class="num">${hhmm(f.block_min)}</td><td class="num">${f.touchdown_vs ?? '—'}</td><td class="num">${f.score}</td></tr>`).join('') || '<tr><td colspan="6" class="hint">No sectors.</td></tr>'}</table></div></div></div>`,
    `<button class="primary" onclick="closeModal()">Close</button>`, true);
}
function renameAc(id) {
  const a = S.fleet.find(x => x.id === id);
  const cat = (S.aircraft_types[a.type] || {}).cat;
  const fee = {Turboprop: 4200, 'Light jet': 5200, 'Midsize jet': 5800, 'Super-midsize jet': 6600,
               'Heavy jet': 9500, Regional: 7500, Narrowbody: 12000, Widebody: 26000}[cat] || 12000;
  const cost = a.owned ? fee : Math.round(fee * 1.5);
  modal(`Registration — ${a.reg}`, `
    <div class="kv"><div>Aircraft</div><div>${esc(a.name)} · ${a.type}</div>
      <div>Currently</div><div><b>${a.reg}</b>${a.reregistered ? `<br><small class="hint">previously ${esc(a.reregistered.previous)}, re-registered ${dd(a.reregistered.date)}</small>` : ''}</div>
      <div>Status</div><div>${esc(a.status)} at ${a.location}</div></div>
    <div class="form" style="margin-top:10px">
      <label>Registration</label><input id="rn-reg" value="${a.reg}" maxlength="8" oninput="this.value=this.value.toUpperCase()">
      <div></div><div class="hint">Letters and digits with an optional hyphen — G-PAGA, N772PA, 9H-XYZ, PH-BXA. The prefix decides which authority issues the paperwork.</div>
      <label>Name</label><input id="rn-name" value="${esc(a.nickname || '')}" placeholder="optional, e.g. Spirit of Cincinnati" maxlength="40">
      <label>Fleet number</label><input id="rn-no" value="${esc(a.fleet_no || '')}" placeholder="optional" maxlength="6">
      <label>Flown in the sim as</label><input id="rn-sim" value="${esc(a.sim_type || '')}" placeholder="${esc(simSub(a.type, true) || 'the add-on you actually fly')}" maxlength="60">
      <div></div><div class="hint">${simSub(a.type)}</div>
    </div>
    <div class="msg warn" style="margin-top:10px">Re-registering costs <b>${usd(cost)}</b> in authority fees, paint and documents${a.owned ? '' : ', including the lessor\'s consent'}. The aircraft must be on the ground and free of work.</div>`,
    `<button onclick="closeModal()">Cancel</button><button class="primary" onclick="doRename(${id})">Save</button>`);
}
async function doRename(id) {
  const body = {id, reg: $('#rn-reg').value, name: $('#rn-name').value, fleet_no: $('#rn-no').value,
                sim_type: $('#rn-sim').value};
  try { const r = await api('/api/fleet/rename', body); closeModal(); await load(); toast(r.message); }
  catch (e) { toast(e.message, true); }
}
function mx(id, check) { const a = S.fleet.find(x => x.id === id); const t = S.aircraft_types[a.type];
  const desc = {A: `A-check: ~${usd(t.mx_fh * 110)}, 2 days`, C: `C-check: ~${usd(t.mx_fh * 900)}, 14 days`, ESV: `Engine shop visit: 25 days${a.pbh ? ' (covered by PBH)' : ', several million dollars per engine'}`}[check];
  confirmDo(`${a.reg} — ${desc}. Proceed?`, () => act(() => api('/api/fleet/maintenance', {id, check}), `${a.reg} inducted`), {ok: 'Induct aircraft'}); }
function disposeAc(id) { const a = S.fleet.find(x => x.id === id);
  confirmDo(a.owned ? `Sell ${a.reg}? Expect 82–95% of book value.` : `Return ${a.reg} to ${a.lessor}? Early return before ${dd(a.lease_end)} costs 3 months' rent.`,
    () => act(() => api('/api/fleet/dispose', {id}), 'Done'), {ok: a.owned ? 'Sell aircraft' : 'Return aircraft', danger: true}); }

/* ------------------------------------------------------------ market */
let MKT = {cat: '', fam: '', use: '', crew: false};
function marketFilter(k, v) { MKT[k] = v; render(); }
function viewMarket() {
  const rated = new Set(S.pilots.flatMap(p => p.ratings));
  const cats = [...new Set(S.market.map(l => S.aircraft_types[l.type].cat))].sort();
  const fams = [...new Set(S.market.map(l => S.aircraft_types[l.type].family))].sort();
  const rows = S.market.filter(l => {
    const t = S.aircraft_types[l.type];
    return (!MKT.cat || t.cat === MKT.cat) && (!MKT.fam || t.family === MKT.fam)
      && (!MKT.use || (MKT.use === 'biz' ? !!t.charter : MKT.use === 'cargo' ? !!t.cargo : !t.cargo && !t.charter))
      && (!MKT.crew || rated.has(t.family));
  });
  const opt = (v, sel) => `<option value="${esc(v)}" ${sel === v ? 'selected' : ''}>${esc(v || 'any')}</option>`;
  return `<div class="panel"><div class="hd">Aircraft market <div class="tools hint">Listings refresh weekly; values follow a market cycle. Operating leases require a 3-month deposit.</div></div>
    <div class="bd" style="display:flex;gap:14px;align-items:center;flex-wrap:wrap;padding-bottom:6px">
      <label style="margin:0">Category <select class="sm" onchange="marketFilter('cat', this.value)">${['', ...cats].map(v => opt(v, MKT.cat)).join('')}</select></label>
      <label style="margin:0">Rating <select class="sm" onchange="marketFilter('fam', this.value)">${['', ...fams].map(v => opt(v, MKT.fam)).join('')}</select></label>
      <label style="margin:0">Use <select class="sm" onchange="marketFilter('use', this.value)"><option value="">any</option><option value="pax" ${MKT.use === 'pax' ? 'selected' : ''}>airline passenger</option><option value="cargo" ${MKT.use === 'cargo' ? 'selected' : ''}>freighter</option><option value="biz" ${MKT.use === 'biz' ? 'selected' : ''}>business aircraft</option></select></label>
      <label style="margin:0"><input type="checkbox" style="width:auto" ${MKT.crew ? 'checked' : ''} onchange="marketFilter('crew', this.checked)"> only types my crews are rated on</label>
      <span class="hint">${rows.length} of ${S.market.length} listings</span>
    </div>
    ${MKT.use === 'biz' && !rows.length ? `<div class="bd"><div class="msg warn" style="margin:0">No business aircraft listed at the moment. Brokers normally keep four on their books; listings turn over weekly, so press <b>+7 days</b> in the status bar if you are waiting on one.</div></div>` : ''}
    <div class="bd tight" style="overflow-x:auto">
    <table class="grid" style="min-width:1100px"><tr><th>Type</th><th>Reg</th><th>Config</th><th class="r">Range</th><th>Speed / runway<br><small class="hint">fuel · upkeep</small></th><th class="r">Year</th><th class="r">Hours</th><th class="r">Engine SV in</th><th>ETOPS</th><th>Lessor / seller</th><th>Located</th><th class="r">Purchase</th><th class="r">Lease /mo</th><th></th></tr>
    ${rows.map(l => `<tr><td>${esc(l.name)} <small>${l.type}</small>${S.aircraft_types[l.type].cargo ? ' <span class="tag grey">freighter</span>' : S.aircraft_types[l.type].charter ? ' <span class="tag info">business</span>' : ''}<br><small class="hint" title="${esc(famTitle(S.aircraft_types[l.type].family))}">${S.aircraft_types[l.type].family} rating${rated.has(S.aircraft_types[l.type].family) ? '' : ' — no crew rated'}</small>${(S.aoc_types || []).length && !S.aoc_types.includes(S.aircraft_types[l.type].family) ? '<br><small class="neg" title="You can own it, but it cannot be released under your certificate until the type is added to your operations specifications">not on your AOC</small>' : ''}
      ${simSub(l.type, true) ? `<br><small class="hint" title="What to fly in the simulator">sim: ${simSub(l.type, true)}</small>` : ''}</td><td>${l.reg}</td><td>${esc(l.config)}</td><td class="num" ${nw}>${n1(S.aircraft_types[l.type].range_nm)} nm</td>
      <td ${nw}><small>${n1(S.aircraft_types[l.type].cruise)} kt${S.aircraft_types[l.type].tofl ? ` · ${n1(S.aircraft_types[l.type].tofl)} ft rwy` : ''}<br>${n1(S.aircraft_types[l.type].burn)} ${unitLabel()}/h · ${usd(S.aircraft_types[l.type].mx_fh)}/h</small></td>
      <td class="num">${l.year}<br><small class="hint">${Math.max(0, new Date(S.clock).getFullYear() - l.year)} yr</small></td>
      <td class="num">${n1(l.hours)}<br><small class="hint">${n1(l.cycles)} cyc</small></td>
      <td class="num">${n1(Math.min(...l.engines.map(e => e.hours_to_sv)))}</td>
      <td>${S.aircraft_types[l.type].charter ? '<span class="hint">n/a</span>' : l.etops ? 'Yes' : '<span class="neg">No</span>'}</td><td>${esc(l.lessor)}</td><td>${ap(l.location)}</td>
      <td class="num" ${nw}>${usd(l.price)}</td><td class="num" ${nw}>${usd(l.lease)}<br><small class="hint">${l.min_term} mo · ${usd(l.lease * 3)} dep</small></td>
      <td ${nw}><button class="sm" onclick="acquire(${l.id},'buy')">Buy</button> <button class="sm" onclick="acquire(${l.id},'lease')">Lease</button></td></tr>`).join('')}
    </table></div></div>`;
}

/* Buying or leasing: where the aircraft sits matters, so the terms screen quotes
   the positioning flight to base alongside the price. */
async function acquire(id, how) {
  const l = S.market.find(x => x.id === id);
  if (!l) { toast('Listing no longer available.', true); return; }
  const t = S.aircraft_types[l.type] || {};
  let q = null;
  try { q = (await api(`/api/market/${id}/delivery`)).quote; } catch (e) { /* priced without it */ }
  const buying = how === 'buy';
  const upfront = buying ? l.price : l.lease * 3 + l.lease;
  const legs = q && q.needed && q.legs.length > 1
    ? `<br><small class="hint">${q.legs.map(g => g.origin).concat(q.legs[q.legs.length - 1].destination).join(' → ')} · tech stops the type can make</small>` : '';
  modal(`${buying ? 'Purchase' : 'Operating lease'} — ${esc(l.name)} ${l.reg}`, `
    <div class="kv">
      <div>Aircraft</div><div>${esc(l.name)} · ${l.type} · ${l.year} build, ${n1(l.hours)} h</div>
      <div>${buying ? 'Seller' : 'Lessor'}</div><div>${esc(l.lessor)}</div>
      <div>${buying ? 'Purchase price' : 'Monthly rent'}</div><div><b>${usd(buying ? l.price : l.lease)}</b>${buying ? '' : ` · ${l.min_term}-month minimum term`}</div>
      ${buying ? '' : `<div>Due on signing</div><div>${usd(l.lease * 3)} deposit plus ${usd(l.lease)} first month</div>`}
      <div>Aircraft is at</div><div>${ap(l.location)}${q && q.needed ? ` — <b>${n1(q.distance)} nm</b> from ${S.company.base}` : ' — your base'}</div>
    </div>
    ${q && q.needed ? `<div class="form" style="margin-top:12px">
      <label>Delivery</label><select id="aq-del">
        <option value="1">Have it delivered to ${S.company.base} — ${usd(q.fee)}, about ${q.days} day(s)</option>
        <option value="0">Collect it yourself from ${l.location} — no charge</option>
      </select>
      <div></div><div class="hint">${esc(l.lessor)} puts a contract crew on it and positions it ${n1(q.distance)} nm in ${q.legs.length} sector(s), roughly ${q.hours} block hours.${legs} The aircraft is unavailable to you until it lands. Collect it yourself and it stays at ${l.location} until you fly it out — a ferry sector you can take in the simulator.</div>
    </div>
    <details style="margin-top:8px"><summary class="hint">What the delivery fee covers</summary>
      <table class="grid" style="margin-top:6px">${q.parts.map(p => `<tr><td>${esc(p[0])}</td><td class="num">${usd(p[1])}</td></tr>`).join('')}
      <tr><td><b>Total</b></td><td class="num"><b>${usd(q.fee)}</b></td></tr></table></details>` : ''}
    <div class="msg ${S.cash < upfront ? 'bad' : ''}" style="margin-top:10px">Cash on hand ${usd(S.cash)}. Due now: <b id="aq-due">${usd(upfront + (q && q.needed ? q.fee : 0))}</b>.</div>`,
    `<button onclick="closeModal()">Cancel</button><button class="primary" onclick="doAcquire(${id},'${how}')">${buying ? 'Purchase' : 'Sign lease'}</button>`);
  const sel = $('#aq-del');
  if (sel) sel.onchange = () => { $('#aq-due').textContent = usd(upfront + (sel.value === '1' ? q.fee : 0)); };
}
async function doAcquire(id, how) {
  const sel = $('#aq-del');
  const body = {id, deliver: !sel || sel.value === '1'};
  try {
    await api(how === 'buy' ? '/api/market/buy' : '/api/market/lease', body);
    closeModal(); await load(); toast(how === 'buy' ? 'Purchased' : 'Lease signed');
  } catch (e) { toast(e.message, true); }
}

/* ------------------------------------------------------------ crew & staff */
function viewCrew() {
  const fams = [...new Set(Object.values(S.aircraft_types).map(t => t.family))].sort();
  const today = S.clock.slice(0, 10);
  return `<div class="panel"><div class="hd">Ground staff <div class="tools hint">Salaries post monthly; recruitment $1,200 per head</div></div><div class="bd tight"><table class="grid"><tr><th>Role</th><th class="r">Headcount</th><th class="r">Required</th><th class="r">Salary</th><th>Rule</th><th></th></tr>
    ${Object.entries(S.staff_def).map(([k, d]) => { const req = k === 'dispatcher' ? S.dispatchers_needed : k === 'mx_controller' ? S.mx_needed : S.cabin_assigned; const n = S.staff[k];
      return `<tr><td>${esc(d.title)}</td><td class="num ${n < req ? 'neg' : ''}">${n}</td><td class="num">${req}${k === 'cabin_crew' ? ' assigned' : ''}</td><td class="num">${usd(d.salary)}/mo</td><td><small>${esc(d.note)}</small></td>
      <td ${nw}><button class="sm" onclick="act(()=>api('/api/staff',{role:'${k}',delta:1}),'Hired')">+1</button> ${k === 'cabin_crew' ? `<button class="sm" onclick="act(()=>api('/api/staff',{role:'${k}',delta:4}),'Hired')">+4</button>` : ''} <button class="sm" onclick="act(()=>api('/api/staff',{role:'${k}',delta:-1}),'Released')">−1</button></td></tr>`; }).join('')}</table></div></div>
  <div class="panel"><div class="hd">Pilot roster <div class="tools hint">Max 13 h flight duty per day, 12 h rest after a long duty. ACMI: 2 CPT + 2 FO per aircraft.</div></div><div class="bd tight">
    <table class="grid"><tr><th>Name</th><th>Rank</th><th>Type ratings</th><th class="r">Hours</th><th title="Landings on type in the last ${S.recency_days} days">Currency</th><th class="r">Duty today</th><th>Rest</th><th class="r">Salary /mo</th><th>Location</th><th>Status</th><th></th></tr>
    ${S.pilots.map(p => { const duty = p.duty_date === today ? p.duty_h : 0, resting = p.rest_until && p.rest_until > S.clock;
      return `<tr><td><a href="#" onclick="pilotRecord(${p.id});return false">${esc(p.name)}</a>${p.is_self ? ' <span class="tag">you</span>' : ''} <a href="#" class="hint" title="Change the name on this crew file" onclick="renamePilot(${p.id});return false">edit</a></td><td>${p.rank}</td><td>${p.ratings.map(f => `<span title="${esc(famTitle(f))}" style="border-bottom:1px dotted var(--line)">${f}</span>`).join(', ')}${p.ratings.length ? `<br><small class="hint">${esc(p.ratings.map(f => famTypes(f)).join(' · '))}</small>` : ''}</td><td class="num">${n1(p.hours)}<br><small>${n1(p.company_hours || 0)} with us</small></td>
      <td>${(p.ratings || []).map(f => { const c = (S.currency[p.id] || {})[f] || {}; return `<div><small class="${c.current ? 'pos' : 'neg'}">${c.current ? '●' : '○'} ${f} ${c.landings || 0}/${S.recency_needed}</small></div>`; }).join('')}</td><td class="num ${duty > 10 ? 'neg' : ''}">${duty.toFixed(1)} h</td><td>${resting ? `<span class="tag warn">until ${p.rest_until.slice(11)}Z ${dd(p.rest_until)}</span>` : ''}</td><td class="num">${usd(p.salary)}</td><td>${p.location}</td>
      <td>${tagStatus(p.status)}${p.contract_id ? ` <small>#${p.contract_id}</small>` : ''}${p.job_id ? ` <small>job #${p.job_id}</small>` : ''}${p.training_until ? ` <small>to ${dd(p.training_until)}</small>` : ''}</td>
      <td ${nw}>${p.rank === 'FO' && S.upgrades[p.id] ? `<button class="sm" onclick="upgrade(${p.id})">${S.upgrades[p.id].eligible ? 'Upgrade to captain' : 'Command…'}</button> ` : ''}<select class="sm" style="width:auto" onchange="ratingAction(${p.id}, this)"><option value="">Ratings…</option><optgroup label="Recency detail">${p.ratings.filter(f => !((S.currency[p.id] || {})[f] || {}).current).map(f => `<option value="rec:${f}">${f}</option>`).join('')}</optgroup><optgroup label="Add (course)">${fams.filter(f => !p.ratings.includes(f)).map(f => `<option value="add:${f}" title="${esc(famTitle(f))}">${f} — ${esc(famTypes(f))}</option>`).join('')}</optgroup>${p.ratings.length > 1 || p.status === 'Training' ? `<optgroup label="${p.status === 'Training' ? 'Cancel / remove' : 'Remove'}">${p.ratings.map(f => `<option value="del:${f}">${f}</option>`).join('')}</optgroup>` : ''}</select>
      <button class="sm danger" onclick="confirmDo('Release ${esc(p.name)}? One month severance.', ()=>act(()=>api('/api/crew/release',{id:${p.id}}),'Released'), {ok:'Release', danger:true})">Release</button></td></tr>`; }).join('') || '<tr><td colspan="10" class="hint">No pilots employed.</td></tr>'}
    </table></div></div>
    <div class="panel"><div class="hd">Candidates <div class="tools hint">Recruitment fee $3,500 · type rating course $26,000–32,000, 21 days</div></div><div class="bd tight">
    <table class="grid"><tr><th>Name</th><th>Rank</th><th>Type ratings</th><th class="r">Hours</th><th class="r">Salary /mo</th><th></th></tr>
    ${(() => { const need = [...new Set(S.fleet.map(a => (S.aircraft_types[a.type]||{}).family))].filter(Boolean);
        const short = need.filter(f => !S.pilots.some(p => p.ratings.includes(f)) && !S.hire_pool.some(p => p.ratings.includes(f)));
        return short.length ? `<tr><td colspan="6" class="msg warn" style="margin:0">Nobody on the market is rated on ${short.join(', ')} just now. Either wait for the list to refresh, or put one of your own pilots through a type rating course from the Ratings menu on the roster above — 21 days and about $26,000–32,000.</td></tr>` : ''; })()}
    ${S.hire_pool.map(p => `<tr><td>${esc(p.name)}</td><td>${p.rank}</td><td>${p.ratings.map(f => `<span title="${esc(famTitle(f))}" style="border-bottom:1px dotted var(--line)">${f}</span>`).join(', ')}${p.ratings.length ? `<br><small class="hint">${esc(p.ratings.map(f => famTypes(f)).join(' · '))}</small>` : ''}</td><td class="num">${n1(p.hours)}</td><td class="num">${usd(p.salary)}</td><td><button class="sm" onclick="act(()=>api('/api/crew/hire',{id:${p.id}}),'Hired')">Hire</button></td></tr>`).join('')}
    </table></div></div>`;
}

function ratingAction(id, sel) {
  const v = sel.value; sel.value = '';
  if (!v) return;
  const [act_, fam] = [v.slice(0, 3), v.slice(4)];
  const p = S.pilots.find(x => x.id === id);
  if (act_ === 'rec') {
    confirmDo(`Book a recency simulator detail for ${p.name} on ${fam}? One day off the roster.`,
      () => act(() => api('/api/crew/recency', {id, family: fam}), 'Recency detail booked'), {ok: 'Book detail'});
    return;
  }
  if (act_ === 'add') {
    confirmDo(`Start a ${fam} type rating course for ${p.name}? 21 days off the roster.`,
      () => act(() => api('/api/crew/train', {id, family: fam}), 'Type rating course started'), {ok: 'Start course'});
  } else {
    const training = p.status === 'Training' && p.ratings[p.ratings.length - 1] === fam;
    confirmDo(training ? `Cancel the ${fam} course for ${p.name}? Half the course fee is refunded and the pilot returns to the roster.`
                       : `Remove the ${fam} rating from ${p.name}? The course fee is not refunded; the rating lapses.`,
      () => act(() => api('/api/crew/rating/remove', {id, family: fam}), training ? 'Course cancelled' : 'Rating removed'),
      {ok: training ? 'Cancel course' : 'Remove rating', danger: true});
  }
}
function upgrade(id) {
  const p = S.pilots.find(x => x.id === id), u = S.upgrades[id];
  const bar = (v, need) => `<div style="height:10px;background:var(--track);border:1px solid var(--line-soft)"><div style="height:100%;width:${Math.min(100, v / need * 100)}%;background:var(--accent)"></div></div>`;
  modal(`Command upgrade — ${p.name}`, `<div class="kv"><div>Rank</div><div>First officer</div><div>Type ratings</div><div>${p.ratings.join(', ')}</div>
    <div>Total hours</div><div>${n1(u.total_hours)} of ${n1(u.need_total)} required</div><div></div><div>${bar(u.total_hours, u.need_total)}</div>
    <div>Hours with this company</div><div>${n1(u.company_hours)} of ${u.need_company} required</div><div></div><div>${bar(u.company_hours, u.need_company)}</div>
    <div>Course</div><div>${usd(u.cost)}, ${u.days} days: simulator details, line training and a line check</div>
    <div>Salary</div><div>${usd(p.salary)} → ${usd(u.new_salary)} per month</div></div>
    ${u.eligible ? '<p class="hint">The pilot is off the roster for the duration of the course.</p>' : `<div class="msg warn">${u.reasons.map(esc).join('<br>')}</div>`}`,
    `<button onclick="closeModal()">Close</button>${u.eligible ? `<button class="primary" onclick="act(()=>api('/api/crew/promote',{id:${id}}),'Command course started');closeModal()">Start command course</button>` : ''}`);
}

/* ------------------------------------------------------------ ferry board */
function snagList(sn) { return sn.length ? sn.map(s => `<span class="tag warn" title="${esc(s.effect)}">${esc(s.code)}</span>`).join(' ') : ''; }
function viewFerry() {
  const allOpen = S.ferry_board.filter(j => j.status === 'Open');
  const open = NEAR_ONLY ? allOpen.filter(j => nearHome(j.origin)) : allOpen;
  const mine = S.ferry_board.filter(j => j.status !== 'Open');
  return `<div class="panel"><div class="hd">Ferry board <div class="tools">${nearToggle(open.length, allOpen.length)}</div><div class="tools hint">Client supplies aircraft, fuel and handling; you supply crew and paperwork. Fee on delivery.</div></div><div class="bd tight">
    <table class="grid"><tr><th>Job</th><th>Client</th><th>Aircraft</th><th>Routing</th><th class="r">nm</th><th>Conditions</th><th>Window</th><th>Expires</th><th class="r">Fee</th><th></th></tr>
    ${open.map(j => `<tr><td>#${j.id} ${esc(j.kind)}<br><small>${esc(j.desc)}</small></td><td>${opLogo(j.client, 24)}${esc(j.client)}</td><td>${esc(j.name)}<br><small>${j.reg} · ${j.year} · rating <span title="${esc(famTitle(j.family))}" style="border-bottom:1px dotted var(--line)">${j.family}</span></small></td>
      <td>${ap(j.origin)} → ${ap(j.destination)}<br><small>${j.stops ? 'via ' + (j.routing || []).slice(0, -1).join(' – ') + ' (' + j.stops + ' tech stop' + (j.stops > 1 ? 's' : '') + ')' : 'non-stop'}</small><br><small>overflies ${j.countries.join(' ')}</small></td><td class="num">${n1(j.distance)}</td>
      <td>${j.beginner ? '<span class="tag ok">Good first job</span><br>' : ''}<small>${esc(j.permit)}</small>${j.permits_needed && j.permits_needed.length ? `<br><small>permits: ${j.permits_needed.join(' ')}</small>` : ''}${j.tech_stops ? '<br><span class="tag warn">Tech stop</span>' : ''}${j.oceanic ? `<br><span class="tag ${j.etops ? 'info' : 'bad'}">${j.etops ? 'Oceanic · ETOPS' : 'Oceanic · non-ETOPS'}</span>` : ''}${j.snags.length ? '<br>' + snagList(j.snags) : ''}</td>
      <td>${j.window_days} days<br><small>${j.stops + 1} sector${j.stops ? 's' : ''}${j.crew_days ? ', ' + j.crew_days + 'd' : ''}</small></td><td ${nw}>${dd(j.expires)}</td><td class="num">${usd(j.fee)}${j.crew_days ? `<br><small>${usd(Math.round(j.fee / j.crew_days))}/day</small>` : ''}</td><td ${nw}><button class="sm" onclick="feeDetail(${j.id})">Fee</button> <button class="sm" onclick="acceptFerry(${j.id})">Accept</button></td></tr>`).join('')}</table></div></div>
    <div class="panel"><div class="hd">My ferry jobs</div><div class="bd tight"><table class="grid"><tr><th>Job</th><th>Aircraft</th><th>Routing</th><th>Now at</th><th>Paperwork</th><th>Defects</th><th>Deadline</th><th>Status</th><th class="r">Fee</th><th></th></tr>
    ${mine.map(j => { const pend = j.docs.filter(d => d.ready > S.clock); return `<tr><td>#${j.id} ${esc(j.kind)}<br><small>${opLogo(j.client, 20)}${esc(j.client)}</small>${j.rejected ? '<br><span class="tag bad">Rejected at redelivery</span>' : ''}</td><td>${j.reg} <small>${j.type}</small></td><td>${j.origin} → ${j.destination}<br><small>plan: ${[j.origin].concat(j.routing || [j.destination]).join(' – ')}</small><br><small>flown: ${j.legs.map(l => `${l.origin}-${l.arrival}`).join(', ') || 'none'}</small></td><td>${j.current}</td>
      <td>${j.docs.map((d, i) => `<small class="${d.ready > S.clock ? 'neg' : 'pos'}">${d.ready > S.clock ? '○' : '●'} <a href="#" onclick="showDoc(${j.id},${i});return false">${esc(d.name)}</a>${d.ready > S.clock ? ' — ' + dd(d.ready) : ''}</small>`).join('<br>') || '—'}</td>
      <td>${j.snags.length ? snagList(j.snags) + `<br><small>${j.snags.map(s => esc(s.effect)).join('; ')}</small><br><a href="#" onclick="snagHowto(${j.id});return false"><small>how to fly this</small></a>` : (j.snags_cleared ? '<small>rectified</small>' : '—')}</td><td>${dd(j.deadline)}</td><td>${tagStatus(j.status)}</td><td class="num">${usd(j.fee)}</td>
      <td ${nw}>${j.status === 'Accepted' && pend.length ? `<button class="sm" onclick="act(()=>api('/api/ferry/expedite',{id:${j.id}}),'Permits expedited')">Expedite</button>` : ''} ${j.status === 'Accepted' && j.snags.length ? `<button class="sm" onclick="confirmDo('Rectify defects before departure for ${usd(j.snags.reduce((s, x) => s + x.cost, 0))}? Adds 2 days to the deadline and removes permit restrictions.', ()=>act(()=>api('/api/ferry/rectify',{id:${j.id}}),'Defects rectified'), {ok:'Rectify'})">Rectify</button>` : ''}</td></tr>`; }).join('') || '<tr><td colspan="10" class="hint">None.</td></tr>'}</table></div></div>`;
}
function feeDetail(id) {
  const j = S.ferry_board.find(x => x.id === id);
  const legs = (j.stops || 0) + 1;
  const blockH = j.block_h || Math.round(((j.distance || 0) / 450 + 0.55 * legs) * 10) / 10;
  const days = j.crew_days || Math.max(2, Math.round(blockH / 9 + (legs - 1) * 0.6));
  const hotels = 2 * 210 * (j.stops || 0), diem = Math.round(2 * 95 * Math.max(1, blockH / 8)), pos = 2 * 400, permits = (j.permits_needed || []).length * 350;
  const est = hotels + diem + pos + permits;
  modal(`Fee — ferry job #${id}`, `<table class="grid">
    ${(j.fee_parts || []).filter(([, v]) => v).map(([n, v]) => `<tr><td>${esc(n)}</td><td class="num">${usd(v)}</td></tr>`).join('')}
    ${j.fee_scale && Math.abs(j.fee_scale - 1) > 0.01 ? `<tr><td>Market and reputation adjustment</td><td class="num">×${j.fee_scale}</td></tr>` : ''}
    <tr><td><b>Fee quoted</b></td><td class="num"><b>${usd(j.fee)}</b></td></tr></table>
    <h2 style="margin-top:10px">What it has to cover</h2><table class="grid">
      <tr><td>Crew positioning to ${j.origin} and home from ${j.destination}</td><td class="num">≈ ${usd(pos)}</td></tr>
      <tr><td>Crew hotels down route (${j.stops || 0} night${j.stops === 1 ? '' : 's'})</td><td class="num">≈ ${usd(hotels)}</td></tr>
      <tr><td>Per diem</td><td class="num">≈ ${usd(diem)}</td></tr>
      ${permits ? `<tr><td>Permit and document fees (${(j.permits_needed || []).length} states)</td><td class="num">≈ ${usd(permits)}</td></tr>` : ''}
      <tr><td><b>Estimated direct costs</b></td><td class="num"><b>${usd(est)}</b></td></tr>
      <tr><td><b>Estimated margin before crew salaries</b></td><td class="num pos"><b>${usd(j.fee - est)}</b></td></tr></table>
    <p class="hint">The client owns the aircraft and pays for its fuel, handling, navigation charges and maintenance; you are selling ${days} days of two crew, the paperwork and the risk. Salaries are a fixed monthly cost, so a job that keeps a crew busy for ${days} days is worth roughly ${usd(Math.round((j.fee - est) / days))} a day against them.</p>`,
    `<button onclick="closeModal()">Close</button><button class="primary" onclick="closeModal();acceptFerry(${id})">Accept job</button>`);
}
function snagHowto(id) {
  const j = S.ferry_board.find(x => x.id === id);
  modal(`Deferred defects — ${j.reg}`, `
    <p>These items are deferred under the permit. Operator scores what you fly, not what your aircraft models, so fly the
    restriction by hand if your add-on has no failure system.</p>
    ${j.snags.map(x => `<div class="panel" style="margin:8px 0 0"><div class="hd">${esc(x.code)} — ${esc(x.name)}</div><div class="bd">
      <div class="kv"><div>Permit condition</div><div>${esc(x.effect)}</div><div>In the simulator</div><div>${esc(x.howto || '—')}</div></div></div></div>`).join('')}`,
    `<button onclick="closeModal()">Close</button><button class="primary" onclick="closeModal();acceptFerry(${id})">Accept job</button>`, true);
}
function crewPair(prefix) {
  const cmd = $(`#${prefix}-cpt`), second = $(`#${prefix}-fo`);
  if (!cmd || !second) return;
  [...second.options].forEach(o => { o.disabled = o.value === cmd.value; });
  if (second.value === cmd.value) {
    const next = [...second.options].find(o => !o.disabled);
    if (next) second.value = next.value;
  }
}
function acceptFerry(id) {
  const j = S.ferry_board.find(x => x.id === id);
  const rated = S.pilots.filter(p => p.status === 'Available' && p.ratings.includes(j.family));
  const cpts = rated.filter(p => p.rank === 'CPT');
  const seconds = rated;                       // either seat may be filled by a captain
  const resting = p => p.rest_until && p.rest_until > S.clock;
  const opt = (l, skip) => l.filter(p => p.id != skip).map(p => `<option value="${p.id}">${p.rank} ${esc(p.name)} (${n1(p.hours)} h)${resting(p) ? ' — resting until ' + p.rest_until.slice(11) + 'Z' : ''}</option>`).join('');
  const cautions = [];
  if (!j.beginner && S.flights.length === 0) cautions.push('This is not a beginner job: ' + [j.tech_stops ? 'tech stop needed' : '', j.oceanic ? 'oceanic sector' : '', j.snags.length ? 'deferred defects with permit limits' : '', j.permits_needed && j.permits_needed.length ? 'overflight/landing permits (' + j.permits_needed.join(', ') + ')' : ''].filter(Boolean).join(', ') + '. Jobs tagged "Good first job" are simpler.');
  if (j.window_days <= 3 && j.permits_needed && j.permits_needed.length) cautions.push('Short delivery window with permits to obtain — you may need to expedite.');
  modal(`Accept ferry job #${id}`, (cautions.length ? `<div class="msg warn">${cautions.map(esc).join('<br>')}</div>` : '') + `<div class="kv"><div>Client</div><div>${opLogo(j.client, 28)}${esc(j.client)}</div><div>Aircraft</div><div>${esc(j.name)} ${j.reg}${j.etops ? '' : ' — <span class="neg">no ETOPS approval</span>'}</div><div>Routing</div><div>${[j.origin].concat(j.routing || [j.destination]).join(' – ')} — ${n1(j.distance)} nm direct${j.stops ? `, ${j.stops} technical stop${j.stops > 1 ? 's' : ''} planned` : ', non-stop'}</div><div>Overflies</div><div>${j.countries.join(', ')}</div><div>Permit basis</div><div>${esc(j.permit)}</div>
    <div>Deferred defects</div><div>${j.snags.map(s => `${esc(s.name)} — <small>${esc(s.effect)}</small><br><small class="hint">${esc(s.howto || '')}</small>`).join('<br>') || 'none'}</div><div>Workload</div><div>${j.stops + 1} sector${j.stops ? 's' : ''}${j.block_h ? `, about ${n1(j.block_h)} block hours` : ''}${j.crew_days ? ` over ${j.crew_days} crew day${j.crew_days > 1 ? 's' : ''}` : ''}</div>
    <div>Fee</div><div><b>${usd(j.fee)}</b>${j.fee_parts ? ` <a href="#" onclick="feeDetail(${j.id});return false">breakdown</a>` : ''}</div>
    <div>Deadline</div><div>${j.window_days} days from acceptance</div></div>
    <p class="hint">On acceptance the permit process starts: insurance, ${j.permit !== 'Standard CofA' ? 'special flight permit, ' : ''}overflight and landing permits for each state on the route. Crew positioning from ${S.company.base} and permit fees are charged now. ${j.stops ? `Distance exceeds the type's range, so the routing above includes ${j.stops} fuel stop${j.stops > 1 ? 's' : ''}; Dispatch will offer each leg in turn. ` : ''}${j.oceanic && !j.etops ? 'Oceanic crossing with a non-ETOPS aircraft: route within about 60 minutes of a diversion airport.' : ''}</p>
    <div class="form"><label>Commander (${j.family})</label><select id="af-cpt" onchange="crewPair('af')">${opt(cpts) || '<option value="">— no captain rated —</option>'}</select>
    <label>Second pilot</label><select id="af-fo">${opt(seconds, cpts[0] && cpts[0].id) || '<option value="">— nobody else rated —</option>'}</select>
    <div></div><div class="hint">Two captains may crew a sector together; two first officers cannot, as one seat must hold a commander.</div></div>`,
    `<button onclick="closeModal()">Cancel</button><button class="primary" ${cpts.length && rated.length > 1 ? '' : 'disabled'} onclick="act(()=>api('/api/ferry/accept',{id:${id},captain_id:$('#af-cpt').value,fo_id:$('#af-fo').value}),'Job accepted');closeModal()">Accept job</button>`);
}

/* ------------------------------------------------------------ cargo contract flying */
let NEAR_ONLY = false;
function nearHome(icao) {
  const a = S.airports[icao], b = S.airports[S.company.base];
  if (!a || !b) return false;
  const R = 3440.065, r = Math.PI / 180;
  const dLa = (b.lat - a.lat) * r, dLo = (b.lon - a.lon) * r;
  const h = Math.sin(dLa / 2) ** 2 + Math.cos(a.lat * r) * Math.cos(b.lat * r) * Math.sin(dLo / 2) ** 2;
  return 2 * R * Math.asin(Math.min(1, Math.sqrt(h))) < 1500;
}
function toggleNear() { NEAR_ONLY = !NEAR_ONLY; render(); }
function nearToggle(n, total) {
  return `<label class="hint" style="margin:0"><input type="checkbox" style="width:auto" ${NEAR_ONLY ? 'checked' : ''} onchange="toggleNear()">
    within 1,500 nm of ${S.company.base}</label> <span class="hint">${n} of ${total} shown</span>`;
}
function viewCargo() {
  const allOpen = S.cargo_board.filter(j => j.status === 'Open');
  const open = NEAR_ONLY ? allOpen.filter(j => nearHome(j.base)) : allOpen;
  const mine = S.cargo_board.filter(j => j.status !== 'Open');
  const legRows = j => `<table class="grid" style="margin-top:3px"><tr><th>#</th><th>Flight</th><th>STD</th><th>Sector</th><th class="r">nm</th><th class="r">Block</th><th class="r">Payload</th><th>Load</th><th></th></tr>
    ${j.legs.map(l => `<tr class="${!l.flown && j.status === 'Accepted' && j.legs.filter(x => !x.flown)[0] === l ? 'sel' : ''}"><td>${l.seq}</td><td>${l.flight_number}</td><td>${l.std}Z</td><td>${l.origin} → ${l.destination}</td><td class="num">${n1(l.distance)}</td><td class="num">${hhmm(l.ete_min)}</td><td class="num">${n1(l.payload_kg)} kg</td><td>${esc(l.load)}${l.dg ? ' <span class="tag warn">special load</span>' : ''}</td><td>${l.flown ? '<span class="tag ok">flown</span>' : ''}</td></tr>`).join('')}</table>`;
  return `<div class="panel"><div class="hd">Cargo flying — contract crew assignments <div class="tools">${nearToggle(open.length, allOpen.length)}</div></div><div class="bd hint" style="padding-bottom:0">The carrier provides the aircraft, fuel and load; you provide a rated crew and fly their schedule. Paid per block hour plus a day rate, on completion of the pairing.</div><div class="bd tight">
    <table class="grid"><tr><th>Pairing</th><th>Aircraft</th><th>Report</th><th>Sectors</th><th class="r">Block</th><th class="r">Days</th><th class="r">Rates</th><th class="r">Pay</th><th>Expires</th><th></th></tr>
    ${open.map(j => `<tr><td>#${j.id} ${opLogo(j.carrier, 26)}<b>${esc(j.carrier)}</b> <small>${j.iata}</small><br><small>${esc(j.reason)}${j.long_haul ? ' · long-haul pattern' : ' · night freight'}</small></td><td>${esc(j.name)}<br><small>${j.type} · rating <span title="${esc(famTitle(j.family))}" style="border-bottom:1px dotted var(--line)">${j.family}</span></small></td><td>${ap(j.base)}</td><td>${j.legs.map(l => l.origin).join('–')}–${j.legs[j.legs.length - 1].destination}${j.dg ? '<br><span class="tag warn">special load</span>' : ''}</td><td class="num">${j.block_h} h</td><td class="num">${j.days}</td><td class="num"><small>${usd(j.bh_rate)}/BH<br>${usd(j.day_rate)}/day</small></td><td class="num">${usd(j.pay)}${(j.extras || []).length ? `<br><small class="pos" title="${esc((j.extras || []).map(e => e.what).join('; '))}">+${usd((j.extras || []).reduce((a, e) => a + e.amount, 0))} premiums</small>` : ''}</td><td ${nw}>${dd(j.expires)}</td>
      <td ${nw}><button class="sm" onclick="cargoDetail(${j.id})">Detail</button> <button class="sm" onclick="acceptCargo(${j.id})">Accept</button></td></tr>`).join('') || `<tr><td colspan="10" class="hint">${certEmpty('pairings')}</td></tr>`}</table></div></div>
    ${mine.map(j => `<div class="panel"><div class="hd">#${j.id} ${opLogo(j.carrier, 26)}${esc(j.carrier)} — ${esc(j.name)} ${j.reg} <div class="tools">${j.legs_flown}/${j.legs.length} sectors · deadline ${dd(j.deadline)} ${tagStatus(j.status)}</div></div><div class="bd tight">${legRows(j)}</div></div>`).join('')}`;
}
function cargoDetail(id) {
  const j = S.cargo_board.find(x => x.id === id);
  modal(`Pairing #${id} — ${j.carrier}`, `<div style="margin-bottom:8px">${opLogo(j.carrier, 48)}</div><div class="kv"><div>Aircraft</div><div>${esc(j.name)} (${j.type}, rating <span title="${esc(famTitle(j.family))}" style="border-bottom:1px dotted var(--line)">${j.family}</span>)</div><div>Report</div><div>${j.base} — ${esc(S.airports[j.base].name)}</div><div>Pattern</div><div>${j.legs.length} sectors, ${j.block_h} block hours over ${j.days} day(s)${j.long_haul ? ', long-haul' : ', night freight'}</div><div>Pay</div><div><b>${usd(j.pay)}</b> on completion
      <table class="grid" style="margin-top:4px">
        <tr><td>Block hours and duty days, two pilots</td><td class="num">${usd(j.base_pay || j.pay)}</td></tr>
        ${(j.extras || []).map(e => `<tr><td class="hint">${esc(e.what)}</td><td class="num pos">${usd(e.amount)}</td></tr>`).join('')}
      </table>
      <small class="hint">${usd(j.bh_rate)} per block hour and ${usd(j.day_rate)} per crew day, each doubled for a two-pilot crew.</small></div><div>Heaviest load</div><div>${n1(j.payload_max)} kg</div></div>
    <table class="grid" style="margin-top:8px"><tr><th>#</th><th>Flight</th><th>STD</th><th>Sector</th><th class="r">nm</th><th class="r">Block</th><th class="r">Payload</th><th>Load</th></tr>
    ${j.legs.map(l => `<tr><td>${l.seq}</td><td>${l.flight_number}</td><td>${l.std}Z</td><td>${l.origin} → ${l.destination}</td><td class="num">${n1(l.distance)}</td><td class="num">${hhmm(l.ete_min)}</td><td class="num">${n1(l.payload_kg)} kg</td><td>${esc(l.load)}${l.dg ? ' <span class="tag warn">special</span>' : ''}</td></tr>`).join('')}</table>`,
    `<button onclick="closeModal()">Close</button><button class="primary" onclick="closeModal();acceptCargo(${id})">Accept pairing</button>`, true);
}
function acceptCargo(id) {
  const j = S.cargo_board.find(x => x.id === id);
  const rated = S.pilots.filter(p => p.status === 'Available' && p.ratings.includes(j.family));
  const cpts = rated.filter(p => p.rank === 'CPT');
  const opt = (l, skip) => l.filter(p => p.id != skip).map(p => `<option value="${p.id}">${p.rank} ${esc(p.name)} (${n1(p.hours)} h)</option>`).join('');
  const heavy = j.legs.filter(l => l.dg);
  modal(`Accept pairing #${id}`, `<div style="margin-bottom:8px">${opLogo(j.carrier, 48)}</div><div class="kv"><div>Carrier</div><div>${esc(j.carrier)}</div><div>Report</div><div>${j.base} — ${esc(S.airports[j.base].name)}</div><div>Pattern</div><div>${j.legs.length} sectors, ${j.block_h} block hours, ${j.days} day(s) away</div><div>Pay</div><div>${usd(j.pay)} on completion</div></div>
    <p class="hint">Crew positioning to ${j.base} is charged now and return tickets on completion. Fly the sectors in order from Dispatch → Cargo pairing sector; the carrier's aircraft, fuel and load are theirs, so your costs are crew time and hotels. Flight-duty limits still apply, so a long pattern may need a night's rest between sectors.${heavy.length ? ' This pairing includes ' + heavy.map(l => l.load.toLowerCase()).join(', ') + ' — heavy payloads affect your takeoff performance.' : ''}</p>
    <div class="form"><label>Commander (${j.family})</label><select id="cg-cpt" onchange="crewPair('cg')">${opt(cpts) || '<option value="">— no captain rated —</option>'}</select>
    <label>Second pilot</label><select id="cg-fo">${opt(rated, cpts[0] && cpts[0].id) || '<option value="">— nobody else rated —</option>'}</select>
    <div></div><div class="hint">Two captains may crew the pairing together; two first officers cannot.</div></div>`,
    `<button onclick="closeModal()">Cancel</button><button class="primary" ${cpts.length && rated.length > 1 ? '' : 'disabled'} onclick="act(()=>api('/api/cargo/accept',{id:${id},captain_id:$('#cg-cpt').value,fo_id:$('#cg-fo').value}),'Pairing accepted');closeModal()">Accept pairing</button>`);
}

async function showDoc(jobId, index) {
  try {
    const {document: d} = await api(`/api/ferry/${jobId}/document/${index}`);
    const rows = d.fields.map(([k, v]) => `<tr><td style="width:190px;color:var(--muted);vertical-align:top">${esc(k)}</td><td>${esc(v)}</td></tr>`).join('');
    modal(d.title, `<div style="border:1px solid var(--line);background:var(--paper);padding:18px 22px;font-family:var(--mono);font-size:12px;line-height:1.55">
      <div style="text-align:center;border-bottom:2px solid var(--text);padding-bottom:8px;margin-bottom:12px">
        <div style="font-size:14px;font-weight:700;letter-spacing:.5px">${esc(d.title.toUpperCase())}</div>
        <div style="color:var(--muted)">${esc(d.authority || d.issuer || '')}</div></div>
      <div style="display:flex;justify-content:space-between;margin-bottom:10px"><span>Reference ${esc(d.ref)}</span>
        <span class="${d.issued ? 'pos' : 'neg'}">${esc(d.status)}${d.issued ? ' ' + dd(d.issued) : ' — expected ' + dd(d.ready)}</span></div>
      <table style="width:100%;border-collapse:collapse">${rows}</table>
      ${d.body.map(b => `<p style="margin:10px 0 0">${esc(b)}</p>`).join('')}
      ${d.conditions.length ? `<div style="margin-top:12px"><b>Conditions</b><ol style="margin:6px 0 0;padding-left:22px">${d.conditions.map(c => `<li>${esc(c)}</li>`).join('')}</ol></div>` : ''}
      ${d.footer ? `<p style="margin-top:12px;font-style:italic">${esc(d.footer)}</p>` : ''}
      <div style="margin-top:18px;display:flex;justify-content:space-between;align-items:flex-end">
        <div><div style="border-top:1px solid var(--text);width:220px;margin-bottom:3px"></div>For and on behalf of ${esc(d.issuer || d.authority || '')}</div>
        <div style="border:2px solid ${d.issued ? '#23703f' : '#9a6a12'};color:${d.issued ? '#23703f' : '#9a6a12'};padding:5px 10px;transform:rotate(-4deg);font-weight:700;letter-spacing:1px">${d.issued ? 'ISSUED' : 'PENDING'}</div>
      </div></div>
      <p class="hint" style="margin-top:8px">Simulated document, for use inside Operator only.</p>`,
      `<button class="primary" onclick="closeModal()">Close</button>`, true);
  } catch (e) { toast(e.message, true); }
}

/* ------------------------------------------------------------ records */
async function pilotRecord(id) {
  try {
    const {record: r} = await api(`/api/record/pilot/${id}`);
    const p = r.pilot;
    const vs = v => v == null ? '—' : `${v} fpm`;
    modal(`${p.rank} ${p.name}`, `
      <div class="row">
        <div class="col"><div class="kv">
          <div>Rank</div><div>${p.rank === 'CPT' ? 'Captain' : 'First officer'}</div>
          <div>Type ratings</div><div>${p.ratings.map(f => `${f} <small class="hint">${famTypes(f)}</small>`).join('<br>')}</div>
          <div>Currency</div><div>${Object.entries(r.currency).map(([f, c]) => `<span class="${c.current ? 'pos' : 'neg'}">${c.current ? '●' : '○'} ${f} — ${c.landings} landing(s) in ${S.recency_days} days</span>`).join('<br>')}</div>
          <div>Status</div><div>${esc(p.status)} at ${p.location}${p.rest_until ? `<br><small class="hint">resting until ${dd(p.rest_until)} ${p.rest_until.slice(11, 16)}Z</small>` : ''}</div>
          <div>Joined</div><div>${dd(p.hired)}</div>
          <div>Salary</div><div>${usd(p.salary)}/month</div>
          <div>Total time</div><div>${n1(r.total_hours)} h${r.company_hours ? ` · ${n1(r.company_hours)} h with us` : ''}</div>
          ${r.upgrade ? `<div>Command</div><div class="${r.upgrade.eligible ? 'pos' : ''}">${esc(r.upgrade.reason || (r.upgrade.eligible ? 'Eligible for upgrade' : ''))}</div>` : ''}
        </div></div>
        <div class="col"><div class="kv">
          <div>Sectors with us</div><div>${r.sectors}${r.hours ? ` · ${n1(r.hours)} block hours` : ''}</div>
          <div>Average score</div><div>${r.avg_score ?? '—'}${r.best_score ? ` <small class="hint">best ${r.best_score}, worst ${r.worst_score}</small>` : ''}</div>
          <div>Average landing</div><div>${vs(r.avg_vs)}</div>
          <div>Best landing</div><div class="pos">${vs(r.best_vs)}</div>
          <div>Firmest</div><div class="${r.worst_vs != null && r.worst_vs < -500 ? 'neg' : ''}">${vs(r.worst_vs)}</div>
          <div>Smooth / firm</div><div>${r.greasers} under 200 fpm · ${r.firm} over 400 fpm</div>
          <div>By type</div><div>${Object.entries(r.by_type).map(([t, d]) => `${t}: ${d.sectors} sector(s), ${n1(d.hours)} h`).join('<br>') || '—'}</div>
          <div>Occurrences</div><div class="${r.occurrences.length ? 'neg' : 'pos'}">${r.occurrences.length || 'none'}</div>
        </div></div>
      </div>
      ${r.recent.length ? `<div style="margin-top:12px"><b>Recent sectors</b><table class="grid" style="margin-top:4px">
        <tr><th>Date</th><th>Flight</th><th>Routing</th><th>Aircraft</th><th class="r">Block</th><th class="r">Landing</th><th class="r">Score</th></tr>
        ${r.recent.map(f => `<tr><td ${nw}>${dd(f.filed)}</td><td>${esc(f.flight_number)}</td><td>${f.origin} → ${f.destination}</td>
          <td>${f.type} <small>${esc(f.reg)}</small></td><td class="num">${hhmm(f.block_min)}</td>
          <td class="num ${f.vs != null && f.vs < -500 ? 'neg' : ''}">${f.vs != null ? f.vs : '—'}</td><td class="num">${f.score ?? '—'}</td></tr>`).join('')}
      </table></div>` : '<p class="hint">No sectors flown with this company yet.</p>'}
      ${r.history.length ? `<div style="margin-top:10px"><b>Record</b>${r.history.map(h => `<div><small>${dd(h.date)} — ${esc(h.title)}</small></div>`).join('')}</div>` : ''}`,
      `<button onclick="renamePilot(${id})">Amend crew file</button><button class="primary" onclick="closeModal()">Close</button>`, true);
  } catch (e) { toast(e.message, true); }
}

function renamePilot(id) {
  const p = S.pilots.find(x => x.id === id);
  if (!p) { toast('Crew file not found.', true); return; }
  const mine = S.pilots.find(x => x.is_self);
  modal(`Crew file — ${p.rank} ${p.name}`, `
    <div class="kv"><div>Rank</div><div>${p.rank === 'CPT' ? 'Captain' : 'First officer'}</div>
      <div>Ratings</div><div>${p.ratings.join(', ')}</div>
      <div>Status</div><div>${esc(p.status)} at ${p.location}</div>
      ${p.former_names && p.former_names.length ? `<div>Previously</div><div class="hint">${p.former_names.map(esc).join(', ')}</div>` : ''}</div>
    <div class="form" style="margin-top:10px">
      <label>Name</label><input id="pn-name" value="${esc(p.name)}" maxlength="40">
      <div></div><div class="hint">Letters, spaces, hyphens and apostrophes. Licence number, ratings, hours and record are unaffected.</div>
      <label>This is me</label><select id="pn-self"><option value="0">No — a member of staff</option><option value="1" ${p.is_self ? 'selected' : ''}>Yes — put my own name in this seat</option></select>
      <div></div><div class="hint">${mine && mine.id !== id ? `${esc(mine.name)} is currently marked as you; setting this moves it.` : 'Marks the file as yours on the roster, the dispatch sheet and your PIREPs. Duty limits, currency and payroll work exactly the same either way.'}</div>
    </div>`,
    `<button onclick="closeModal()">Cancel</button><button class="primary" onclick="doRenamePilot(${id})">Save</button>`);
}
async function doRenamePilot(id) {
  try {
    await api('/api/crew/rename', {id, name: $('#pn-name').value, is_self: $('#pn-self').value === '1'});
    closeModal(); await load(); toast('Crew file amended');
  } catch (e) { toast(e.message, true); }
}

async function aircraftRecord(id) {
  try {
    const {record: r} = await api(`/api/record/aircraft/${id}`);
    const a = r.aircraft, t = S.aircraft_types[a.type] || {};
    modal(`${a.reg} — ${a.name}`, `
      <div class="row">
        <div class="col"><div class="kv">
          <div>Type</div><div>${esc(a.name)} · ${a.type}${a.nickname ? `<br><small>“${esc(a.nickname)}”</small>` : ''}</div>
          <div>Built</div><div>${a.year} <small class="hint">${Math.max(0, new Date(S.clock).getFullYear() - a.year)} years old</small></div>
          <div>Registration</div><div>${a.reg}${a.reregistered ? `<br><small class="hint">previously ${esc(a.reregistered.previous)}, ${esc(a.reregistered.authority)}</small>` : ''}</div>
          <div>Ownership</div><div>${a.owned ? 'Owned' : `Leased from ${esc(a.lessor)}<br><small class="hint">${usd(a.lease)}/mo to ${dd(a.lease_end)}</small>`}</div>
          <div>Airframe</div><div>${n1(a.hours)} h · ${n1(a.cycles)} cycles</div>
          <div>Next A-check</div><div>${Math.round(S.a_check_fh - a.fh_since_a)} FH</div>
          <div>C-check due</div><div>${dd(a.c_check_due)}</div>
          <div>Engines</div><div>${a.engines.map((e, i) => `#${i + 1} ${n1(e.hours_to_sv)} h to shop visit`).join('<br>')}</div>
          <div>Now at</div><div>${ap(a.location)} — ${esc(a.status)}</div>
          <div>In the simulator</div><div>${a.sim_type ? `<b>${esc(a.sim_type)}</b><br>` : ''}${simSub(a.type)}</div>
        </div></div>
        <div class="col"><div class="kv">
          <div>Sectors flown</div><div>${r.sectors} · ${n1(r.hours_flown)} block hours with us</div>
          <div>Revenue earned</div><div class="pos">${usd(r.income)}</div>
          <div>Direct costs</div><div class="neg">${usd(r.direct_costs)}</div>
          <div>Other spend</div><div class="neg">${usd(r.other_spend)} <small class="hint">lease, checks, engines</small></div>
          <div>Average score</div><div>${r.avg_score ?? '—'}</div>
          <div>Average landing</div><div>${r.avg_vs != null ? r.avg_vs + ' fpm' : '—'}</div>
          <div>Most-visited</div><div>${r.ports.map(([k, n]) => `${k} (${n})`).join(', ') || '—'}</div>
          <div>Deferred defects</div><div class="${a.snags.length ? 'neg' : ''}">${a.snags.map(x => esc(x.name)).join('<br>') || 'none'}</div>
        </div></div>
      </div>
      ${r.utilisation.length ? `<div style="margin-top:12px"><b>Utilisation</b>
        <div style="display:flex;gap:18px;flex-wrap:wrap;margin-top:4px">${r.utilisation.map(u =>
          `<div><small class="hint">${u.month}</small><br><b>${u.hours} h</b></div>`).join('')}</div></div>` : ''}
      ${r.mx_log.length ? `<div style="margin-top:10px"><b>Maintenance</b><table class="grid" style="margin-top:4px">
        <tr><th>Date</th><th>Work</th><th class="r">Cost</th></tr>
        ${r.mx_log.map(m => `<tr><td ${nw}>${dd(m.date)}</td><td>${esc(m.text || m.what || m.check || '')}</td><td class="num">${m.cost ? usd(m.cost) : '—'}</td></tr>`).join('')}</table></div>` : ''}
      ${r.recent.length ? `<div style="margin-top:10px"><b>Recent sectors</b><table class="grid" style="margin-top:4px">
        <tr><th>Date</th><th>Flight</th><th>Routing</th><th>Work</th><th class="r">Block</th><th class="r">Landing</th><th class="r">Score</th></tr>
        ${r.recent.map(f => `<tr><td ${nw}>${dd(f.filed)}</td><td>${esc(f.flight_number)}</td><td>${f.origin} → ${f.destination}</td>
          <td>${esc(f.kind)}${f.customer ? `<br><small class="hint">${esc(f.customer)}</small>` : ''}</td>
          <td class="num">${hhmm(f.block_min)}</td><td class="num ${f.vs != null && f.vs < -500 ? 'neg' : ''}">${f.vs ?? '—'}</td>
          <td class="num">${f.score ?? '—'}</td></tr>`).join('')}</table></div>` : '<p class="hint">This aircraft has not flown for you yet.</p>'}`,
      `<button class="primary" onclick="closeModal()">Close</button>`, true);
  } catch (e) { toast(e.message, true); }
}

/* ------------------------------------------------------------ career */
function viewCareer() {
  const c = S.career;
  if (!c) return '<div class="panel"><div class="bd hint">No objectives.</div></div>';
  if (!c.enabled) return `<div class="panel"><div class="hd">Objectives</div><div class="bd">
    <p>This company is in free play, so nothing is gated and there are no objectives. The list below is still a
    reasonable order to learn the game in.</p></div></div>` + careerList(c);
  return `<div class="panel"><div class="hd">Career <div class="tools hint">${c.done} of ${c.total} objectives</div></div>
    <div class="bd"><div class="bar" style="height:10px;background:var(--bg);border:1px solid var(--line-soft)">
      <div style="height:100%;width:${Math.round(c.done / c.total * 100)}%;background:var(--accent)"></div></div>
    ${c.current ? `<p style="margin:10px 0 0">Next: <b>${esc(c.current.text)}</b><br><span class="hint">${esc(c.current.why)}</span>
      <button class="sm primary" style="margin-left:8px" onclick="nav('${c.current.go}')">Take me there</button></p>` : '<p class="pos" style="margin:10px 0 0">Every objective complete. The company is yours to run.</p>'}
    </div></div>` + careerList(c);
}
function careerList(c) {
  return c.chapters.map(ch => `<div class="panel"><div class="hd">${esc(ch.title)}
      <div class="tools ${ch.complete ? 'pos' : 'hint'}">${ch.goals.filter(g => g.done).length} of ${ch.goals.length}${ch.complete ? ' — complete' : ''}</div></div>
    <div class="bd"><p class="hint" style="margin:0 0 8px">${esc(ch.blurb)}</p>
      <table class="grid">${ch.goals.map(g => `<tr>
        <td style="width:26px" class="${g.done ? 'pos' : 'hint'}">${g.done ? '●' : '○'}</td>
        <td><b>${esc(g.text)}</b><br><small class="hint">${esc(g.why)}</small></td>
        <td class="num" ${nw}>${g.done ? dd(g.done) : `<button class="sm" onclick="nav('${g.go}')">Go</button>`}</td></tr>`).join('')}
      </table></div></div>`).join('');
}

/* ---- flights dispatched but not yet filed: any number, one of them tracked */
function dispatchedPanel() {
  const ds = S.dispatched || [];
  if (!ds.length) return '';
  return `<div class="panel"><div class="hd">Dispatched flights <div class="tools hint">${ds.length} in progress — the tracked one is the sector the simulator is following</div></div>
    <div class="bd tight"><table class="grid">
    <tr><th>Flight</th><th>Aircraft</th><th>Routing</th><th>Work</th><th class="r">Block</th><th>Crew</th><th></th></tr>
    ${ds.map(f => { const t = f.id === S.tracked_id, air = airborneLeg(f.id);
      return `<tr${t ? ' style="background:var(--subtle)"' : ''}>
      <td>${air ? '<span class="tag info">airborne</span> ' : t ? '<span class="tag ok">tracking</span> ' : ''}<b>${esc(f.flight_number)}</b></td>
      <td>${f.type} ${esc(f.reg || '')}</td>
      <td>${f.origin} → ${f.destination}</td>
      <td>${esc(f.kind)}${f.customer ? `<br><small class="hint">${esc(f.customer)}</small>` : ''}</td>
      <td class="num">${air ? `${hhmm(air.block_min)}<br><small class="hint">${Math.round(air.progress * 100)}% flown</small>` : f.ete_min ? hhmm(f.ete_min) : '—'}</td>
      <td><small>${(f.crew || []).map(id => { const p = S.pilots.find(x => x.id === id); return p ? esc(p.name.split(' ').pop()) : '—'; }).join(', ')}</small>${air ? `<br><small class="hint">ETA ${air.eta.slice(11, 16)}Z ${dd(air.eta)}</small>` : ''}</td>
      <td ${nw}>${air ? '<span class="hint">with the crew</span>' : `${t ? '' : `<button class="sm" onclick="trackFlight(${f.id})">Track</button> `}
        <button class="sm" onclick="flyWithCrew(${f.id})">Fly with crew</button>
        <button class="sm" onclick="confirmDo('Cancel ${esc(f.flight_number)}?', ()=>act(()=>api('/api/flight/cancel',{id:${f.id}}),'Flight cancelled'), {ok:'Cancel flight', danger:true})">Cancel</button>`}</td></tr>`; }).join('')}
    </table></div></div>`;
}
async function trackFlight(id) { await act(() => api('/api/flight/track', {id}), 'Now tracking that flight'); }

/* ------------------------------------------------------------ schedule */
let SCH = null, SCH_DAYS = 14;
async function loadSchedule() {
  try { const r = await api(`/api/schedule?days=${SCH_DAYS}`); SCH = r.schedule; render(); }
  catch (e) { toast(e.message, true); }
}
function schedDays(n) { SCH_DAYS = n; loadSchedule(); }

const SCH_COLOUR = {charter: 'var(--accent)', acmi: '#6b8e23', active: '#c0392b',
                    maintenance: '#8e6f3e', due: '#a6791f', ferry: '#3f7a8c', cargo: '#5b6f9c'};

function viewSchedule() {
  if (!SCH) { setTimeout(loadSchedule, 0); return '<div class="panel"><div class="bd hint">Building the schedule…</div></div>'; }
  const start = new Date(SCH.start), now = new Date(SCH.clock);
  const days = SCH.days, W = 100 / days;
  const dayList = [...Array(days)].map((_, i) => new Date(start.getTime() + i * 864e5));
  const pos = t => Math.max(0, Math.min(100, (new Date(t) - start) / (days * 864e5) * 100));
  // a two-hour sector inside a fortnight is a sliver, so short items get a minimum width
  // and their label sits alongside rather than inside the block
  const bar = (it, row) => {
    const l = pos(it.start), r = pos(it.end), w = r - l;
    const narrow = w < 7;
    const tip = `${it.label} — ${it.note || ''}\n${dd(it.start)} ${it.start.slice(11, 16)}Z to ${dd(it.end)} ${it.end.slice(11, 16)}Z`;
    const go = it.kind === 'charter' ? `onclick="dispatchCharter(${it.job})" style="cursor:pointer;"` : '';
    return `<div class="schitem ${narrow ? 'narrow' : ''}" ${go ? go.replace('style="cursor:pointer;"', '') : ''}
        style="left:${l}%;width:${Math.max(2.2, w)}%;background:${SCH_COLOUR[it.kind] || '#666'}${it.kind === 'charter' ? ';cursor:pointer' : ''}" title="${esc(tip)}">
        ${narrow ? '' : esc(it.label)}</div>
      ${narrow ? `<div class="schlabel" style="left:calc(${l}% + ${Math.max(2.2, w)}% + 4px)" title="${esc(tip)}">${esc(it.label)}</div>` : ''}`;
  };
  const nowLeft = pos(SCH.clock);

  return `
  <div class="panel"><div class="hd">Schedule
    <div class="tools">${[7, 14, 28].map(n => `<button class="sm ${SCH_DAYS === n ? 'primary' : ''}" onclick="schedDays(${n})">${n} days</button>`).join(' ')}</div></div>
    <div class="bd tight">
      <div class="schgrid">
        <div class="schhead"><div class="schreg"></div><div class="schtrack">
          ${dayList.map((d, i) => `<div class="schday" style="left:${i * W}%;width:${W}%">${['Sun','Mon','Tue','Wed','Thu','Fri','Sat'][d.getUTCDay()]} ${d.getUTCDate()}${days <= 7 ? `<br><small>${d.toISOString().slice(5, 7)}/${d.toISOString().slice(8, 10)}</small>` : ''}</div>`).join('')}
          <div class="schnow" style="left:${nowLeft}%"></div></div></div>
        ${SCH.rows.map(r => `<div class="schrow">
          <div class="schreg"><b>${r.reg}</b><br><small class="hint">${r.type} · ${r.location}${r.status !== 'Available' ? ` · ${esc(r.status)}` : ''}</small></div>
          <div class="schtrack">
            ${dayList.map((d, i) => `<div class="schcell" style="left:${i * W}%;width:${W}%"></div>`).join('')}
            <div class="schnow" style="left:${nowLeft}%"></div>
            ${r.items.map(it => bar(it, r)).join('') || '<div class="schfree">nothing scheduled</div>'}
          </div></div>`).join('')}
      </div>
      <div class="schkey">${Object.entries({charter: 'Charter', acmi: 'ACMI', active: 'In the air', maintenance: 'Maintenance', due: 'Falling due'})
        .map(([k, v]) => `<span><i style="background:${SCH_COLOUR[k]}"></i>${v}</span>`).join('')}
        <span class="hint">the red line is now</span></div>
    </div></div>

  ${SCH.conflicts.length ? `<div class="panel"><div class="hd">What will not fit</div><div class="bd tight">
    ${SCH.conflicts.map(c => `<div class="msg ${c.severity === 'bad' ? 'bad' : 'warn'}" style="margin:4px 0">
      <b>${esc(c.reg)}</b> — ${esc(c.text)}
      ${c.job ? `<div class="actions"><button class="sm primary" onclick="dispatchCharter(${c.job})">Position it</button></div>` : ''}</div>`).join('')}
  </div></div>` : '<div class="panel"><div class="bd pos">Nothing clashes over the next ' + days + ' days.</div></div>'}

  ${SCH.unassigned.length ? `<div class="panel"><div class="hd">Accepted work flown on someone else's aircraft</div><div class="bd tight">
    <table class="grid"><tr><th>Work</th><th>Routing</th><th>Due</th><th></th></tr>
    ${SCH.unassigned.map(u => `<tr><td><span class="tag grey">${u.kind}</span> ${esc(u.label)}<br><small class="hint">${esc(u.note)}</small></td>
      <td>${ap(u.origin)} → ${ap(u.destination)}</td><td ${nw}>${dd(u.deadline)}</td>
      <td><button class="sm" onclick="nav('${u.kind === 'ferry' ? 'ferry' : 'cargo'}')">Open</button></td></tr>`).join('')}
    </table></div></div>` : ''}

  ${SCH.later.length && !SCH.rows.some(r => r.items.length) ? `<div class="msg warn">Nothing falls inside the next ${days} days. Your next commitment is ${dd(SCH.later[0].start)} — <a href="#" onclick="schedDays(28);return false">show 28 days</a>.</div>` : ''}
  ${SCH.later.length ? `<div class="panel"><div class="hd">Beyond the board</div><div class="bd tight"><table class="grid">
    <tr><th>Aircraft</th><th>Commitment</th><th>Starts</th></tr>
    ${SCH.later.map(l => `<tr><td>${esc(l.reg)}</td><td>${esc(l.label)}<br><small class="hint">${esc(l.note)}</small></td><td ${nw}>${dd(l.start)}</td></tr>`).join('')}
  </table></div></div>` : ''}

  ${SCH.crew.length ? `<div class="panel"><div class="hd">Crew off the line</div><div class="bd tight"><table class="grid">
    <tr><th>Pilot</th><th>Ratings</th><th>Status</th><th>Back</th></tr>
    ${SCH.crew.map(c => `<tr><td>${c.rank} ${esc(c.name)}</td><td>${c.ratings.join(', ')}</td><td>${esc(c.status)}</td><td ${nw}>${c.until ? dd(c.until) : '—'}</td></tr>`).join('')}
  </table></div></div>` : ''}`;
}

/* ------------------------------------------------------------ charter */
function viewCharter() {
  const jobs = S.charter_jobs || [], board = S.charter_board || [];
  const fleet = S.fleet.filter(a => S.aircraft_types[a.type] && S.aircraft_types[a.type].charter);
  return `
  ${jobs.length ? `<div class="panel"><div class="hd">Booked trips</div><div class="bd tight"><table class="grid">
    <tr><th>Trip</th><th>Client</th><th>Aircraft</th><th>Client sectors</th><th>Next to fly</th><th>Departs</th><th class="r">Fee</th><th></th></tr>
    ${jobs.map(j => `<tr><td>#${j.id} ${j.origin} → ${j.destination}<br><small>${opLogo(j.broker, 18)}${esc(j.broker)}</small></td>
      <td>${esc(j.client)}<br><small class="hint">${esc(j.story)}; ${esc(j.extra)}</small></td>
      <td>${j.name}<br><small>${j.reg} at ${j.legs.length ? j.legs[0].origin : '—'}</small></td>
      <td>${(j.client_legs || []).map((l, i) => `<div><small class="${i < j.done ? 'pos' : ''}">${i < j.done ? '●' : '○'} ${l.origin}→${l.destination}</small></div>`).join('')}
        ${j.legs.length && !j.legs[0].paid ? `<div><small class="neg">position ${j.legs[0].origin}→${j.legs[0].destination} first</small></div>` : ''}</td>
      <td ${nw}>${j.legs.length ? `<b>${j.legs[0].origin} → ${j.legs[0].destination}</b><br><small class="${j.legs[0].paid ? 'pos' : 'neg'}">${j.legs[0].paid ? esc(j.legs[0].note) : 'empty positioning — not paid'}</small>` : '<span class="hint">complete</span>'}</td>
      <td ${nw}>${dd(j.depart)}<br><small>${j.depart.slice(11, 16)}Z</small></td>
      <td class="num">${usd(j.fee)}</td>
      <td><button class="sm primary" onclick="dispatchCharter(${j.id})">${j.legs.length && !j.legs[0].paid ? 'Position' : 'Fly next sector'}</button></td></tr>`).join('')}
  </table></div></div>` : ''}

  <div class="panel"><div class="hd">Charter enquiries <div class="tools hint">Brokers ask what you would charge. Quote too high and the trip goes elsewhere.</div></div>
    <div class="bd tight"><table class="grid">
    <tr><th>Broker</th><th>Client</th><th>Routing</th><th class="r">nm</th><th class="r">Pax</th><th>Departs</th><th class="r">Going rate</th><th>Expires</th><th></th></tr>
    ${board.map(q => { const own = fleet.filter(a => a.status === 'Available');
      const route = [q.origin, ...(q.stops || []), q.destination];
      const NEED = {attendant: 'cabin crew', customs: 'customs', short_field: 'short runway',
                    curfew: 'curfew slot', wifi: 'connectivity', baggage: 'hold baggage'};
      const needs = Object.entries(q.needs || {}).filter(([k, v]) => v === true).map(([k]) => NEED[k] || k);
      return `<tr><td>${opLogo(q.broker, 22)}${esc(q.broker)}<br><span class="tag ${q.urgent ? 'warn' : 'grey'}">${esc(q.trip_label)}</span>${q.group ? ' <span class="tag info">group</span>' : ''}${q.event ? `<br><small class="neg">${esc(q.event)}</small>` : ''}</td>
      <td>${esc(q.client)}<br><small class="hint">${esc(q.story)}</small><br><small>${esc(q.extra)}</small></td>
      <td>${route.map(r => ap(r)).join(' → ')}${q.same_day ? `<br><span class="tag warn">${q.nights ? q.nights + ' night(s), returns' : 'same-day return'}</span>` : ''}<br><small>${q.group ? `${esc(q.name)} · code ${q.code_letter}` : q.cat} · ${q.block_h} h${needs.length ? ' · needs ' + needs.join(', ') : ''}</small></td>
      <td class="num">${n1(q.distance)}</td><td class="num">${q.pax}</td>
      <td ${nw}>${dd(q.depart)}<br><small>${q.depart.slice(11, 16)}Z</small></td>
      <td class="num">${usd(q.market)}<br><small class="hint">market</small></td>
      <td ${nw}>${dd(q.expires)}</td>
      <td>${own.length ? `<button class="sm primary" onclick="quoteCharter(${q.id})">Quote</button>`
        : `<span class="hint">no aircraft free</span>`}</td></tr>`; }).join('')
      || '<tr><td colspan="9" class="hint">No enquiries. Brokers ask more often once you have a business aircraft on the fleet.</td></tr>'}
    </table></div>
    ${fleet.length ? '' : `<div class="bd"><div class="msg warn" style="margin:0">You need a business aircraft to fly charter work. There are always some on the market — a Phenom 300 or Citation for short trips, a Challenger or Praetor for transcontinental, a Gulfstream, Global or Falcon for intercontinental.
      <div class="actions"><button class="primary" onclick="MKT.use='biz'; nav('market')">Show business aircraft on the market</button></div></div></div>`}
  </div>

  ${(S.charter_history || []).length ? `<div class="panel"><div class="hd">Recent quotes</div><div class="bd tight"><table class="grid">
    <tr><th>Broker</th><th>Routing</th><th class="r">Market</th><th class="r">You quoted</th><th>Result</th></tr>
    ${S.charter_history.slice().reverse().map(q => `<tr><td>${opLogo(q.broker, 20)}${esc(q.broker)}</td><td>${q.origin} → ${q.destination}</td>
      <td class="num">${usd(q.market)}</td><td class="num">${q.quoted ? usd(q.quoted) : '—'}</td>
      <td>${q.status === 'Won' ? '<span class="tag ok">won</span>' : `${q.placed_with ? `${opLogo(q.placed_with, 18)}<span class="hint">${esc(q.placed_with)}${q.placed_at ? ' at ' + usd(q.placed_at) : ''}</span>` : `<span class="tag grey">placed elsewhere</span>`}`}</td></tr>`).join('')}
  </table></div></div>` : ''}

  ${(S.charter_done || []).length ? `<div class="panel"><div class="hd">Completed trips</div><div class="bd tight"><table class="grid">
    <tr><th>Trip</th><th>Client</th><th class="r">Fee</th><th class="r">Satisfaction</th></tr>
    ${S.charter_done.slice().reverse().map(j => `<tr><td>${j.origin} → ${j.destination}<br><small>${opLogo(j.broker, 18)}${esc(j.broker)}</small></td><td>${esc(j.client)}</td>
      <td class="num">${usd(j.fee)}${j.direct_costs ? `<br><small class="hint">less ${usd(j.direct_costs)} costs</small>` : ''}</td>
      <td class="num ${j.satisfaction == null ? 'neg' : j.satisfaction >= 80 ? 'pos' : j.satisfaction >= 60 ? '' : 'neg'}">${j.satisfaction == null ? 'not operated' : j.satisfaction}
        ${j.scorecard ? `<br><small class="hint">comfort ${j.scorecard.comfort} · on time ${j.scorecard.punctual} · cabin ${j.scorecard.cabin}</small>` : ''}</td></tr>`).join('')}
  </table></div></div>` : ''}`;
}

function dispatchCharter(id) {
  nav('dispatch');
  setTimeout(() => {
    const k = $('#d-kind'); if (!k) return;
    k.value = 'charter'; dispatchKind();
    setTimeout(() => { const sel = $('#d-job'); if (sel) { sel.value = id; pickCharter(); } }, 60);
  }, 60);
}
function quoteCharter(id) {
  const q = S.charter_board.find(x => x.id === id);
  const suggest = Math.round(q.market / 100) * 100;
  const route = [q.origin, ...(q.stops || []), q.destination];
  const needLabels = {seats: `${(q.needs || {}).seats} seats`, attendant: 'cabin attendant', customs: 'customs and immigration',
                      short_field: 'short runway', curfew: 'curfew departure', wifi: 'connectivity', baggage: 'baggage volume'};
  const needs = Object.entries(q.needs || {}).filter(([k, v]) => v === true).map(([k]) => needLabels[k] || k);
  modal(`Quote — ${esc(q.trip_label)}, ${q.origin} to ${q.destination}`, `
    <div class="kv"><div>Broker</div><div>${esc(q.broker)}<br><small class="hint">${esc(q.broker_note || '')}</small></div>
      <div>Client</div><div>${esc(q.client)} — ${esc(q.story)}</div>
      <div>Trip</div><div>${esc(q.trip_label)}${q.event ? ` around ${esc(q.event)}` : ''}<br><small class="hint">${esc(q.trip_desc || '')}</small></div>
      <div>Itinerary</div><div>${route.join(' → ')}${q.same_day ? (q.nights ? ` and back after ${q.nights} night(s)` : ', returning the same day') : ''}<br><small>${n1(q.distance)} nm · ${q.block_h} block hours · ${q.pax} passengers</small></div>
      <div>Asked for</div><div>${esc(q.extra)}${needs.length ? `<br><small class="hint">needs ${needs.join(', ')}</small>` : ''}
        ${q.group ? `<br><small class="hint">${q.pax} passengers — an aircraft of ${q.pax} seats or more, code ${q.code_letter} or smaller at both ends, and ${(q.needs || {}).attendants || 1} cabin crew</small>` : ''}</div>
      <div>Departure</div><div>${dd(q.depart)} at ${q.depart.slice(11, 16)}Z${q.urgent ? ' <span class="tag warn">short notice</span>' : ''}</div>
      <div>Going rate</div><div><b>${usd(q.market)}</b> <span class="hint">what this trip usually places at</span></div>
      <div>This client</div><div>${Object.entries(q.cares || {}).sort((a, b) => b[1] - a[1]).map(([k, v]) =>
        `${{punctual: 'punctuality', comfort: 'a smooth flight', cabin: 'the right cabin'}[k] || k} ${Math.round(v * 100)}%`).join(' · ')}
        <br><small class="hint">what they will judge you on afterwards</small></div></div>
    <div id="ch-fit"></div>
    <div class="form" style="margin-top:10px"><label>Your price</label><input type="number" id="ch-price" value="${suggest}" step="500" oninput="quoteOdds(${id})">
      <div></div><div id="ch-odds" class="hint"></div></div>
    <p class="hint">Positioning to the client and home again is at your cost, so a trip far from your aircraft is worth less than it looks.</p>`,
    `<button onclick="closeModal()">Cancel</button><button class="primary" onclick="sendQuote(${id})">Send quote</button>`);
  quoteOdds(id);
  api(`/api/charter/${id}/fit`).then(r => {
    const box = $('#ch-fit'); if (!box) return;
    const ok = r.fleet.filter(a => a.ok && a.status === 'Available');
    const no = r.fleet.filter(a => !a.ok);
    box.innerHTML = `<div class="msg ${ok.length ? 'ok' : 'bad'}" style="margin:10px 0 0">
      ${ok.length ? ok.map(a => `<div><b>${a.reg}</b> ${esc(a.name)} at ${a.location} — can fly this${a.notes.length ? `<br><small class="neg">${a.notes.map(esc).join('<br>')}</small>` : ''}</div>`).join('')
        : 'No aircraft in your fleet can take this trip.'}
      ${no.map(a => `<div class="hint">${a.reg} ${esc(a.name)} — ${esc(a.blocking[0] || 'not suitable')}</div>`).join('')}</div>`;
  }).catch(() => {});
}
function quoteOdds(id) {
  const q = S.charter_board.find(x => x.id === id), price = parseFloat(($('#ch-price') || {}).value) || 0;
  const el = $('#ch-odds'); if (!el) return;
  const ratio = price / Math.max(1, q.market);
  const odds = Math.max(0.02, Math.min(0.96, 1 / (1 + Math.exp((ratio - 1) * 9 * (q.fussy || 1))) * (0.75 + S.company.reputation / 200)));
  el.className = odds > 0.6 ? 'pos' : odds > 0.3 ? '' : 'neg';
  el.textContent = `${Math.round(ratio * 100)}% of the going rate — roughly a ${Math.round(odds * 100)}% chance of winning it.`;
}
async function sendQuote(id) {
  const price = parseFloat(($('#ch-price') || {}).value) || 0;
  try {
    const r = await api('/api/charter/quote', {id, price});
    closeModal(); await load();
    if (r.won) toast(`Trip won at ${usd(price)}`);
    else toast(`Placed elsewhere at about ${usd(r.placed_at)}`, true);
  } catch (e) { toast(e.message, true); }
}

/* ------------------------------------------------------------ tenders */
/* When a board is empty because of the types on the certificate, say so. An empty
   screen with no explanation reads as a bug. */
function certEmpty(what) {
  const t = S.aoc_types || [];
  if (!t.length) return `No ${what} on offer at the moment.`;
  return `No ${what} on offer. Your certificate covers the <b>${t.map(esc).join(', ')}</b>, and `
    + `nothing in this market operates those. Add a type on the Company profile to open it up.`;
}
function viewTenders() {
  return `<div class="panel"><div class="hd">ACMI tenders <div class="tools hint">You provide Aircraft, Crew, Maintenance, Insurance; the customer pays fuel, handling, fees and a minimum monthly guarantee.</div></div><div class="bd tight">
    <table class="grid"><tr><th>Customer</th><th>Requirement</th><th>Hub</th><th>Start</th><th>Term</th><th class="r">Min BH/mo</th><th class="r">Rate /BH</th><th class="r">Min monthly</th><th>Competing bids</th><th>Expires</th><th></th></tr>
    ${S.acmi_tenders.map(t => { const have = S.fleet.some(a => a.type === t.type && a.status === 'Available');
      return `<tr><td>${opLogo(t.customer, 24)}${esc(t.customer)} <small>${t.iata}</small>${t.renewal ? ' <span class="tag info">extension offer</span>' : ''}<br><small>${esc(t.reason)}${t.season_note ? ' · ' + t.season_note : ''}</small></td><td>${esc(t.name)} <small>${t.type}${t.cargo ? ' freighter' : ''}</small></td><td>${ap(t.hub)}</td><td>${dd(t.start)}</td><td>${t.months} mo</td><td class="num">${t.min_hours}</td><td class="num">${usd(t.rate)}</td><td class="num">${usd(t.rate * t.min_hours)}</td><td><small>${t.competitors.map(esc).join('<br>') || 'none'}</small></td><td ${nw}>${dd(t.expires)}</td>
      <td><button class="sm" onclick="acceptTender(${t.id})" ${have ? '' : 'title="No available aircraft of this type"'}>Bid</button></td></tr>`; }).join('') || `<tr><td colspan="11" class="hint">${certEmpty('tenders')}</td></tr>`}</table></div></div>`;
}
function acceptTender(id) {
  const t = S.acmi_tenders.find(x => x.id === id);
  const acs = S.fleet.filter(a => a.type === t.type && a.status === 'Available');
  const crew = S.pilots.filter(p => p.status === 'Available' && p.ratings.includes(t.family));
  const cat = S.aircraft_types[t.type].cat, cabin = t.cargo ? 0 : {Turboprop: 2, Regional: 2, Narrowbody: 4, Widebody: 8}[cat] * 2;
  const freeCabin = S.staff.cabin_crew - S.cabin_assigned;
  modal(`Contract with ${t.customer}`, `${opLogo(t.customer, 44) ? `<div style="margin-bottom:8px">${opLogo(t.customer, 44)}</div>` : ''}<div class="kv"><div>Aircraft type</div><div>${esc(t.name)}</div><div>Operating base</div><div>${t.hub} — ${esc(S.airports[t.hub].name)}</div><div>Term</div><div>${t.months} months from ${dd(t.start)}</div><div>Rate</div><div>${usd(t.rate)} per block hour, minimum ${t.min_hours} BH/month (${usd(t.rate * t.min_hours)})</div><div>Network</div><div>${t.network.join(' ')}</div>
    <div>Cabin crew</div><div>${t.cargo ? 'not required (freighter)' : `${cabin} required (2 sets) — ${freeCabin} unassigned${freeCabin < cabin ? ' <span class="neg">— hire more in Crew & staff</span>' : ''}`}</div></div>
    <p class="hint">The aircraft must be positioned at ${t.hub} by the start date. Livery and cabin reconfiguration takes 3 days (decals only: 1 day). KPIs: utilisation vs guarantee, completion of the published rotation and on-time performance. Delays over 15 minutes carry a per-minute penalty. Satisfaction ≥ 70 at term end earns an extension offer.</p>
    <div class="form"><label>Aircraft</label><select id="at-ac">${acs.map(a => `<option value="${a.id}">${a.reg} — at ${a.location}, ${n1(a.hours)} h${a.etops ? '' : ', non-ETOPS'}</option>`).join('') || '<option value="">— no available ' + t.type + ' in fleet —</option>'}</select>
    <label>Livery</label><select id="at-liv"><option value="1">Full customer livery + cabin reconfiguration (${usd(cat === 'Widebody' ? 120000 : 45000)}, 3 days)</option><option value="0">Decals and placards only ($12,000, 1 day)</option></select>
    <label>Crew</label><div id="at-crewbox" style="border:1px solid var(--field-line);background:var(--field);border-radius:2px;max-height:190px;overflow:auto;padding:2px 0">
      ${['CPT', 'FO'].map(rk => { const list = crew.filter(p => p.rank === rk); return `<div style="padding:3px 8px;background:var(--subtle2);border-bottom:1px solid var(--line-soft);color:var(--muted);font-size:11px">${rk === 'CPT' ? 'Captains — at least 2' : 'First officers'}</div>` +
        (list.map(p => `<label style="display:flex;gap:8px;align-items:center;padding:3px 8px;cursor:pointer"><input type="checkbox" class="at-crew" value="${p.id}" data-rank="${p.rank}" style="width:auto" onchange="crewCount()"><span>${esc(p.name)}</span><span class="hint" style="margin-left:auto">${n1(p.hours)} h</span></label>`).join('')
         || '<div class="hint" style="padding:3px 8px">none available and rated on ' + t.family + '</div>'); }).join('')}
    </div><div></div><div id="at-crewmsg" class="hint">Tick four pilots, at least two of them captains, so both crew sets have a commander.</div></div>`,
    `<button onclick="closeModal()">Cancel</button><button class="primary" id="at-sign" disabled onclick="act(()=>api('/api/acmi/accept',{id:${id},aircraft_id:$('#at-ac').value,crew_ids:[...document.querySelectorAll('.at-crew:checked')].map(o=>o.value),livery:$('#at-liv').value==='1'}),'Contract signed');closeModal()">Sign contract</button>`);
  crewCount();
}

function crewCount() {
  const picked = [...document.querySelectorAll('.at-crew:checked')];
  const cpt = picked.filter(x => x.dataset.rank === 'CPT').length, total = picked.length;
  const ok = cpt >= 2 && total >= 4 && !!($('#at-ac') || {}).value;
  const msg = $('#at-crewmsg'), btn = $('#at-sign');
  if (msg) {
    msg.className = ok ? 'pos' : 'hint';
    msg.textContent = ok ? `${total} pilots selected, ${cpt} of them captains — ready to sign.`
      : `Selected ${total} of 4 pilots, ${cpt} of the 2 captains needed.`;
  }
  if (btn) btn.disabled = !ok;
}

/* ------------------------------------------------------------ contracts */
async function operateRotation(id) {
  try { const r = await api('/api/contract/rotation/operate', {id}); await load(); toast(r.message); }
  catch (e) { toast(e.message, true); }
}
function endContract(id) {
  const c = S.contracts.find(x => x.id === id);
  const months = Math.max(0, (new Date(c.end) - new Date(S.clock)) / 2.592e9);
  const penalty = Math.round(c.min_hours * c.rate * Math.min(2, months) * 0.35);
  confirmDo(`Hand the ${c.customer} contract back with ${months.toFixed(0)} month(s) left? ` +
    `Early termination charges are about ${usd(penalty)}, and they will remember it when they next tender.`,
    () => act(() => api('/api/contract/cancel', {id}), 'Contract terminated'), {ok: 'Hand it back', danger: true});
}
function viewContracts() {
  return S.contracts.slice().reverse().map(c => { const k = c.kpi; return `<div class="panel"><div class="hd">#${c.id} ${opLogo(c.customer, 24)}${esc(c.customer)} — ${esc(c.name)} ${c.reg} <div class="tools">${c.renewal ? '<span class="tag info">renewal</span>' : ''}${tagStatus(c.status)}</div></div><div class="bd">
    <div class="row"><div class="col"><div class="kv"><div>Base</div><div>${ap(c.hub)}</div><div>Term</div><div>${dd(c.start)} → ${dd(c.end)} (${c.months} mo, ${c.months_billed} billed)</div><div>Rate</div><div>${usd(c.rate)}/BH · min ${c.min_hours} BH/mo</div>
      <div>This month</div><div>${n1(c.hours_month)} BH in ${c.legs_month} legs (${Math.round(c.hours_month / c.min_hours * 100)}% of guarantee)</div>
      <div>Rotation completion</div><div>${k.legs_flown} of ${k.legs_scheduled} scheduled legs${k.legs_scheduled ? ` (${Math.round(k.legs_flown / k.legs_scheduled * 100)}%)` : ''}</div>
      <div>On-time</div><div>${k.legs_flown ? Math.round((1 - k.late / k.legs_flown) * 100) : 100}% · ${k.delay_min} delay minutes</div>
      <div>Customer satisfaction</div><div><b class="${k.satisfaction < 50 ? 'neg' : k.satisfaction >= 70 ? 'pos' : ''}">${k.satisfaction}</b> / 100</div>
      <div>Total</div><div>${n1(c.hours_total)} BH · ${usd(c.revenue_total)} revenue</div><div>Notices</div><div>${c.strikes}</div><div>Cabin crew</div><div>${c.cabin_crew || 'n/a'}</div><div>Reason</div><div>${esc(c.reason)}</div></div></div>
    <div class="col"><table class="grid"><tr><th>Month</th><th class="r">BH</th><th class="r">Legs</th><th class="r">Utilisation</th><th class="r">Completion</th><th class="r">OTP</th><th class="r">Satisfaction</th></tr>${c.history.map(h => `<tr><td>${esc(h.month)}</td><td class="num">${h.hours}</td><td class="num">${h.legs}</td><td class="num">${h.util}%</td><td class="num">${h.completion ?? '—'}%</td><td class="num">${h.otp ?? '—'}%</td><td class="num">${h.satisfaction ?? '—'}</td></tr>`).join('') || '<tr><td colspan="7" class="hint">No month closed yet.</td></tr>'}</table></div></div>
    ${c.status === 'Active' || c.status === 'Pending start' ? `<div class="actions" style="margin-top:10px">
      ${c.status === 'Active' ? `<button class="primary" onclick="operateRotation(${c.id})">Let the crew fly today's rotation</button>
        <button class="sm" onclick="nav('dispatch')">Fly it yourself</button>` : ''}
      <button class="sm danger" onclick="endContract(${c.id})">Hand the contract back</button>
    </div>
    <p class="hint" style="margin:6px 0 0">${c.status === 'Active'
      ? 'A rotation is published every day whether you fly it or not. Handing it to the crew keeps the guarantee and the completion figures intact when you have not the time; the flying is scored as theirs, not yours.'
      : 'The contract has not started yet. Position the aircraft at the hub before the start date.'}</p>` : ''}
    </div></div>`; }).join('') || '<div class="panel"><div class="bd hint">No contracts signed.</div></div>';
}

/* ------------------------------------------------------------ dispatch */
function viewDispatch() {
  const af = S.active_flight;
  const left = `<div class="panel" style="max-width:860px"><div class="hd">New flight</div><div class="bd">
    <div class="form">
      <label>Flight type</label><select id="d-kind" onchange="dispatchKind()"><option value="acmi">ACMI rotation leg</option><option value="ferry">Ferry job leg</option><option value="cargo">Cargo pairing sector</option>
        <option value="charter">Charter sector</option><option value="positioning">Positioning (own aircraft)</option></select>
      <div class="full" id="d-src"></div>
      <div class="full"><button onclick="sendSimbrief()">Send to SimBrief</button> <button onclick="importSimbrief()" id="d-fetch">Fetch OFP</button> <span class="hint" id="d-sbmsg">${S.company.simbrief_username || S.company.simbrief_userid ? 'Send opens SimBrief pre-filled with this flight; generate the plan there, then Fetch pulls route, fuel, weights, ETE and weather back.' : 'SimBrief is optional — fill the fields in by hand, or set a username in Settings to have them filled for you.'}</span></div>
      <label>Flight number</label><input type="text" id="d-fno">
      <label>Origin</label><input type="text" id="d-org" maxlength="4" style="text-transform:uppercase" oninput="fuelHint();routePlanSoon()">
      <label>Destination</label><input type="text" id="d-dst" maxlength="4" style="text-transform:uppercase" oninput="fuelHint();routePlanSoon()">
      <label>Alternate</label><input type="text" id="d-alt" maxlength="4" style="text-transform:uppercase">
      <label>Route</label><textarea id="d-route" rows="2"></textarea>
      <label>Cruise altitude</label><input type="number" id="d-crz">
      <label>Distance (nm)</label><input type="number" id="d-dist">
      <label>ETE (min)</label><input type="number" id="d-ete">
      <label>Block fuel (${unitLabel()})</label><input type="number" id="d-fuel">
      <label>ZFW (${unitLabel()})</label><input type="number" id="d-zfw">
      <label>Pax / cargo (${unitLabel()})</label><div class="row"><input type="number" id="d-pax" placeholder="pax"><input type="number" id="d-cargo" placeholder="cargo ${unitLabel()}"></div>
      <label>OFP</label><input type="text" id="d-ofp" readonly placeholder="none imported">
      <label>Ballast (${unitLabel()})</label><input type="number" id="d-ballast" value="0" oninput="perfDirty()">
      <label>Load distribution</label><div class="row" style="gap:12px;align-items:center"><span class="hint" style="white-space:nowrap">Cabin fwd</span><input type="range" id="d-paxd" min="0" max="1" step="0.05" value="0.5" oninput="perfDirty()" style="flex:1"><span class="hint" style="white-space:nowrap">aft</span>
        <span class="hint" style="white-space:nowrap">Hold fwd</span><input type="range" id="d-cargod" min="0" max="1" step="0.05" value="0.5" oninput="perfDirty()" style="flex:1"><span class="hint" style="white-space:nowrap">aft</span></div>
      <label>Conditions</label><div class="row" style="gap:8px"><input type="number" id="d-oat" value="15" placeholder="OAT °C" oninput="perfDirty()" title="Outside air temperature"><input type="number" id="d-wdir" placeholder="wind °" oninput="perfDirty()"><input type="number" id="d-wkt" placeholder="wind kt" value="0" oninput="perfDirty()"><select id="d-surf" onchange="perfDirty()"><option value="dry">Dry</option><option value="wet">Wet</option><option value="contaminated">Contaminated</option></select></div>
      <div class="full"><button onclick="runPerf()">Runway analysis &amp; loadsheet</button> <label style="display:inline;color:var(--text)"><input type="checkbox" id="d-override" style="width:auto"> Accept performance risk</label></div>
      <div class="full" id="d-perf"></div>
      <div class="full" id="d-routeplan"></div>
      <div class="full hint" id="d-fuelhint"></div>
      <div class="full" id="d-wx"></div>
    </div><div class="actions"><button class="primary" onclick="doDispatch()">Dispatch</button></div></div></div>`;
  const busy = (S.dispatched || []).length;
  return `<div id="af"></div>${dispatchedPanel()}
    <div class="row"><div class="col">
      ${busy ? `<details ${busy ? '' : 'open'}><summary style="cursor:pointer;padding:6px 0;color:var(--accent)">Dispatch another flight</summary>${left}</details>` : left}
      </div></div>`;
}
function afterDispatch() { if (!S.active_flight) dispatchKind(); renderActive(); }
const FUEL_F = {US: .98, CA: 1.05, MX: 1.15, AE: .9, QA: .88, SA: .85, OM: .92, KW: .88, BH: .9, IN: 1.2, CN: 1.05, JP: 1.1, SG: 1, AU: 1.12, NZ: 1.15, BR: 1.25, ZA: 1.15, KE: 1.35, NG: 1.35, RU: .95, IS: 1.3, TR: 1.1, EG: 1.1, MA: 1.15};
function fuelHint() {
  const o = ($('#d-org').value || '').toUpperCase(), d = ($('#d-dst').value || '').toUpperCase(), h = $('#d-fuelhint'); if (!h) return;
  const p = i => S.airports[i] ? (S.company.fuel_price_usg * (FUEL_F[S.airports[i].country] ?? 1.18)).toFixed(2) : null;
  h.textContent = (p(o) || p(d)) ? `Jet A: ${o} ${p(o) ? '$' + p(o) : '—'} · ${d} ${p(d) ? '$' + p(d) : '—'} per USG (tanker where it is cheaper on positioning flights).` : '';
}
function dispatchKind() {
  const k = $('#d-kind').value, box = $('#d-src');
  if (k === 'acmi') {
    const cs = S.contracts.filter(c => c.status === 'Active');
    box.innerHTML = cs.length ? `<div class="form"><label>Contract</label><select id="d-contract" onchange="loadRotation()">${cs.map(c => `<option value="${c.id}">#${c.id} ${esc(c.customer)} ${c.reg} @ ${c.hub}</option>`).join('')}</select></div><div id="d-rot" style="margin-top:6px"></div>` : '<div class="msg warn">No active ACMI contract. Sign a tender and position the aircraft at the hub first.</div>';
    if (cs.length) loadRotation();
  } else if (k === 'ferry') {
    const js = S.ferry_board.filter(j => j.status === 'Accepted');
    box.innerHTML = js.length ? `<div class="form"><label>Ferry job</label><select id="d-job" onchange="pickJob()">${js.map(j => `<option value="${j.id}">#${j.id} ${j.reg} ${j.type} — next leg ${j.current} → ${nextWp(j)}${nextWp(j) !== j.destination ? ' (tech stop, final ' + j.destination + ')' : ''}</option>`).join('')}</select></div><div id="d-jobinfo"></div>` : '<div class="msg warn">No accepted ferry job.</div>';
    if (js.length) pickJob();
  } else if (k === 'charter') {
    const jobs = S.charter_jobs || [];
    box.innerHTML = jobs.length
      ? `<div class="form"><label>Charter trip</label><select id="d-job" onchange="pickCharter()">${jobs.map(j => {
          const next = j.legs[0];
          return `<option value="${j.id}">#${j.id} ${esc(j.client)} — next ${next ? `${next.origin} → ${next.destination}${next.paid ? '' : ' (positioning)'}` : 'complete'}</option>`;
        }).join('')}</select></div><div id="d-chinfo"></div>`
      : '<div class="msg warn">No booked charter trips. Quote for work on the Charter board.</div>';
    if (jobs.length) pickCharter();
  } else if (k === 'cargo') {
    const js = S.cargo_board.filter(j => j.status === 'Accepted');
    box.innerHTML = js.length ? `<div class="form"><label>Cargo pairing</label><select id="d-job" onchange="pickCargo()">${js.map(j => `<option value="${j.id}">#${j.id} ${esc(j.carrier)} ${j.type} — ${j.legs_flown}/${j.legs.length} sectors flown, at ${j.current}</option>`).join('')}</select></div><div id="d-jobinfo"></div>` : '<div class="msg warn">No cargo pairing accepted. Take one from Cargo flying.</div>';
    if (js.length) pickCargo();
  } else {
    const as = S.fleet.filter(a => a.status === 'Available' || a.status === 'ACMI');
    box.innerHTML = as.length ? `<div class="form"><label>Aircraft</label><select id="d-ac" onchange="pickAc()">${as.map(a => `<option value="${a.id}">${a.reg} ${a.type} at ${a.location}${a.contract_id ? ' (contract #' + a.contract_id + ')' : ''}</option>`).join('')}</select></div>` : '<div class="msg warn">No aircraft in fleet.</div>';
    if (as.length) pickAc();
  }
}
async function loadRotation() {
  const cid = $('#d-contract').value; const c = S.contracts.find(x => x.id == cid);
  try { const j = await api(`/api/contract/${cid}/rotation`); AF_SEL.legs = j.legs;
    $('#d-rot').innerHTML = `<div class="hint">Rotation published by ${esc(c.customer)} for ${dd(S.clock)}. Aircraft at ${S.fleet.find(a => a.id === c.aircraft_id).location}.</div><table class="grid"><tr><th>#</th><th>Flight</th><th>STD</th><th>Sector</th><th class="r">nm</th><th class="r">ETE</th><th></th></tr>${j.legs.map((l, i) => `<tr><td>${l.seq}</td><td>${l.flight_number}</td><td>${l.std}Z</td><td>${l.origin} → ${l.destination}</td><td class="num">${l.distance}</td><td class="num">${hhmm(l.ete_min)}</td><td><button class="sm" onclick="pickLeg(${i})">Select</button></td></tr>`).join('')}</table>`;
    pickLeg(0);
  } catch (e) { toast(e.message, true); }
}
function pickLeg(i) { setTimeout(routePlan, 0); const l = AF_SEL.legs[i]; AF_SEL.std = l.std; $('#d-fno').value = l.flight_number; $('#d-org').value = l.origin; $('#d-dst').value = l.destination; $('#d-dist').value = l.distance; $('#d-ete').value = l.ete_min; fuelHint(); }
function nextWp(j) { const rt = (j.routing || [j.destination]); const i = rt.indexOf(j.current); return i >= 0 && i + 1 < rt.length ? rt[i + 1] : (j.current === j.origin ? rt[0] : j.destination); }
function pickJob() { setTimeout(routePlan, 0); const j = S.ferry_board.find(x => x.id == $('#d-job').value); const wp = nextWp(j); $('#d-org').value = j.current; $('#d-dst').value = wp; $('#d-fno').value = S.company.code + (9000 + j.id); $('#d-dist').value = ''; $('#d-ete').value = '';
  const pend = j.docs.filter(d => d.ready > S.clock);
  const wp2 = nextWp(j);
  $('#d-jobinfo').innerHTML = `<div class="msg ${pend.length || j.snags.length ? 'warn' : 'ok'}" style="margin-top:6px">${wp2 !== j.destination ? `Technical stop leg: ${j.current} → ${wp2}, then on towards ${j.destination}. ` : `Final leg to ${j.destination}. `}${pend.length ? `Paperwork outstanding: ${pend.map(d => esc(d.name) + ' (' + dd(d.ready) + ')').join(', ')}. ` : 'Paperwork complete. '}${j.snags.length ? 'Restrictions: ' + j.snags.map(s => esc(s.effect)).join('; ') + '. ' : ''}${j.oceanic && !j.etops ? 'Non-ETOPS: keep within ~60 min of a diversion airport.' : ''}</div>`; fuelHint(); }
function pickCharter() {
  const j = (S.charter_jobs || []).find(x => x.id == ($('#d-job') || {}).value);
  if (!j) return;
  const next = j.legs[0];
  if (!next) return;
  setTimeout(routePlan, 0);
  $('#d-org').value = next.origin; $('#d-dst').value = next.destination;
  $('#d-fno').value = `${S.company.code}${900 + (j.id % 90)}`;
  if ($('#d-pax')) $('#d-pax').value = next.paid ? j.pax : 0;
  const info = $('#d-chinfo');
  if (info) info.innerHTML = `<div class="msg ${next.paid ? 'ok' : 'warn'}" style="margin:6px 0 0">
    <b>${next.origin} → ${next.destination}</b> — ${next.paid
      ? `revenue sector, ${j.pax} passengers for ${esc(j.client).toLowerCase()}. ${esc(j.extra)}.`
      : `empty positioning to meet the client at ${next.destination}. Not paid, but the trip cannot start without it.`}
    <br>Sector ${Math.min(j.done + 1, (j.client_legs || []).length)} of ${(j.client_legs || []).length} for the client${j.done ? `, ${j.done} flown` : ''}.
    Scheduled ${dd(j.depart)} ${j.depart.slice(11, 16)}Z — the client notices if you are late.
    <br><span class="hint">The aircraft can be used for other work in between; the trip works out its own positioning from wherever it ends up.</span></div>`;
  fuelHint();
}
function pickCargo() { setTimeout(routePlan, 0);
  const j = S.cargo_board.find(x => x.id == $('#d-job').value);
  const l = j.legs.find(x => !x.flown);
  if (!l) { $('#d-jobinfo').innerHTML = '<div class="msg ok" style="margin-top:6px">All sectors flown.</div>'; return; }
  $('#d-fno').value = l.flight_number; $('#d-org').value = l.origin; $('#d-dst').value = l.destination; $('#d-dist').value = l.distance; $('#d-ete').value = l.ete_min;
  $('#d-cargo').value = Math.round(l.payload_kg / 0.453592); $('#d-pax').value = 0; AF_SEL.std = l.std;
  $('#d-jobinfo').innerHTML = `<div class="msg ${l.dg ? 'warn' : 'ok'}" style="margin-top:6px">${opLogo(j.carrier, 30)}Sector ${l.seq} of ${j.legs.length}: ${l.flight_number} ${l.origin}→${l.destination}, STD ${l.std}Z. Load: ${esc(l.load)}, ${n1(l.payload_kg)} kg${l.dg ? ' — special load, check the runway analysis before you accept the fuel figure.' : '.'}</div>`;
  fuelHint();
}
function pickAc() { setTimeout(routePlan, 0); const a = S.fleet.find(x => x.id == $('#d-ac').value); $('#d-org').value = a.location; $('#d-fno').value = S.company.code + (8000 + a.id); const c = a.contract_id && S.contracts.find(x => x.id === a.contract_id); if (c && a.location !== c.hub) $('#d-dst').value = c.hub; fuelHint(); }
function formData() {
  const num = id => { const v = parseFloat(($(id) || {}).value); return isNaN(v) ? null : v; };
  const lb = id => { const v = num(id); return v == null ? null : Math.round(toLb(v)); };
  const kgIn = id => { const v = num(id); return v == null ? null : Math.round(UNIT() === 'lb' ? v / LB_PER_KG : v); };
  const g = id => ($(id) || {}).value || '';
  return {kind: g('#d-kind'), origin: g('#d-org'), destination: g('#d-dst'), alternate: g('#d-alt'), route: g('#d-route'), cruise_alt: g('#d-crz'), distance_nm: g('#d-dist'), ete_min: g('#d-ete'),
    block_fuel_lbs: lb('#d-fuel'), zfw_lbs: lb('#d-zfw'), pax: g('#d-pax'), cargo_lbs: lb('#d-cargo'), ofp_id: g('#d-ofp'), flight_number: g('#d-fno'), contract_id: g('#d-contract'), job_id: g('#d-job'), aircraft_id: g('#d-ac'), std: AF_SEL.std || '',
    ballast_kg: kgIn('#d-ballast'), pax_dist: g('#d-paxd') || 0.5, cargo_dist: g('#d-cargod') || 0.5, oat_c: g('#d-oat'), wind_dir: g('#d-wdir'), wind_kt: g('#d-wkt'), surface_state: g('#d-surf'),
    override: ($('#d-override') || {}).checked || false};
}
let rpTimer = null;
function routePlanSoon() { clearTimeout(rpTimer); rpTimer = setTimeout(routePlan, 500); }
async function routePlan() {
  const box = $('#d-routeplan'); if (!box) return;
  const kind = ($('#d-kind') || {}).value, org = (($('#d-org') || {}).value || '').toUpperCase(), dst = (($('#d-dst') || {}).value || '').toUpperCase();
  if (org.length !== 4 || dst.length !== 4 || org === dst) { box.innerHTML = ''; return; }
  const acId = ($('#d-ac') || {}).value;
  let type = null;
  if (kind === 'ferry') { const j = S.ferry_board.find(x => x.id == ($('#d-job') || {}).value); type = j && j.type; }
  else if (kind === 'cargo') { const j = S.cargo_board.find(x => x.id == ($('#d-job') || {}).value); type = j && j.type; }
  else if (kind === 'acmi') { const c = S.contracts.find(x => x.id == ($('#d-contract') || {}).value); type = c && c.type; }
  try {
    const r = await api('/api/routeplan', {type, aircraft_id: acId, origin: org, destination: dst});
    if (!r.legs.length) { box.innerHTML = ''; return; }
    if (r.legs.length === 1) {
      const l = r.legs[0];
      box.innerHTML = `<div class="hint">${l.origin} → ${l.destination}: ${n1(l.distance)} nm, within the ${r.type} range of ${n1(r.range_nm)} nm — non-stop.</div>`;
      return;
    }
    box.innerHTML = `<div class="msg warn" style="margin:0">${n1(r.legs.reduce((a, l) => a + l.distance, 0))} nm exceeds the ${r.type}'s ${n1(r.range_nm)} nm range. Suggested routing with ${r.legs.length - 1} technical stop${r.legs.length > 2 ? 's' : ''}:
      <table class="grid" style="margin:6px 0;background:var(--panel)">${r.legs.map(l => `<tr><td>${l.seq}</td><td>${l.origin} → ${l.destination}</td><td class="num ${l.over_range ? 'neg' : ''}">${n1(l.distance)} nm${l.over_range ? ' — beyond range' : ''}</td><td>${l.seq === 1 ? '<button class="sm" onclick="useLeg(\'' + l.destination + '\')">Use this leg</button>' : ''}</td></tr>`).join('')}</table>
      ${r.legs.some(l => l.over_range) ? 'No suitable airfield exists for one of these legs — this type cannot make the crossing.' : 'Fly the legs one at a time; the aircraft carries on from wherever it lands.'}</div>`;
  } catch (e) { box.innerHTML = ''; }
}
function useLeg(icao) { $('#d-dst').value = icao; $('#d-dist').value = ''; $('#d-ete').value = ''; fuelHint(); routePlan(); }
function perfDirty() { const e = $('#d-perf'); if (e && e.innerHTML) e.style.opacity = '.45'; }
function bar(v, lo, hi, ok) {
  const pct = Math.max(0, Math.min(100, (v - (lo - 8)) / ((hi + 8) - (lo - 8)) * 100));
  const l = (lo - (lo - 8)) / ((hi + 8) - (lo - 8)) * 100, h = (hi - (lo - 8)) / ((hi + 8) - (lo - 8)) * 100;
  return `<div style="position:relative;height:16px;background:var(--track);border:1px solid var(--line-soft)">
    <div style="position:absolute;left:${l}%;width:${h - l}%;top:0;bottom:0;background:#e6f4ea;border-left:1px solid #a9d5b7;border-right:1px solid #a9d5b7"></div>
    <div style="position:absolute;left:calc(${pct}% - 1px);top:-2px;bottom:-2px;width:2px;background:${ok ? 'var(--accent)' : 'var(--bad)'}"></div></div>`;
}
async function runPerf() {
  const box = $('#d-perf'); box.style.opacity = '1'; box.innerHTML = '<span class="hint">Calculating…</span>';
  try {
    const r = await api('/api/performance', formData());
    const a = r.analysis;
    if (!a) { box.innerHTML = '<div class="msg warn">No performance data for this type.</div>'; return; }
    const ls = a.loadsheet, to = a.takeoff, ld = a.landing;
    const rwList = (list, icao) => list.length ? list.map(x => `${x.ends.join('/')} ${x.length.toLocaleString()} ft ${x.surface.toLowerCase()}${x.lit ? '' : ', unlit'}`).join(' · ') : `no runway data for ${icao}`;
    const dist = (x, what) => !x ? '' : x.ok == null ? `<div class="hint">${esc(x.reason)}</div>` : `<div class="kv">
      <div>Runway</div><div>${x.runway} — ${x.length.toLocaleString()} ft ${x.surface.toLowerCase()}${x.lit ? '' : ', unlit'}</div>
      <div>${what} distance</div><div class="${x.ok ? '' : 'neg'}">${x.required.toLocaleString()} ft required of ${x.available.toLocaleString()} ft — margin ${x.margin.toLocaleString()} ft</div>
      <div>Wind</div><div>${x.headwind >= 0 ? 'head' : 'tail'}wind ${Math.abs(x.headwind)} kt, crosswind ${Math.abs(x.crosswind)} kt</div>
      <div>Density altitude</div><div>${x.density_alt.toLocaleString()} ft</div>
      ${x.limit_weight ? `<div>Runway-limited weight</div><div>${x.limit_weight.toLocaleString()} kg</div>` : ''}${x.vref ? `<div>Vref</div><div>${x.vref} kt</div>` : ''}</div>`;
    box.innerHTML = `<div class="panel" style="margin:6px 0 0"><div class="hd">Loadsheet &amp; performance</div><div class="bd">
      ${a.blocking.length ? `<div class="msg bad">${a.blocking.map(esc).join('<br>')}</div>` : ''}
      ${a.warnings.length ? `<div class="msg warn">${a.warnings.map(esc).join('<br>')}</div>` : ''}
      <div class="row"><div class="col"><div class="kv">
        <div>Operating empty</div><div class="num">${ls.oew.toLocaleString()} kg</div>
        <div>Payload</div><div class="num">${ls.pax ? ls.pax + ' pax (' + ls.pax_kg.toLocaleString() + ' kg)' : ''}${ls.cargo_kg ? (ls.pax ? ' + ' : '') + ls.cargo_kg.toLocaleString() + ' kg cargo' : (ls.pax ? '' : 'none — ferry')}${ls.ballast_kg ? ' + ' + ls.ballast_kg.toLocaleString() + ' kg ballast' : ''}</div>
        <div>Zero fuel weight</div><div class="num ${ls.zfw > ls.mzfw ? 'neg' : ''}">${ls.zfw.toLocaleString()} / ${ls.mzfw.toLocaleString()} kg MZFW</div>
        <div>Fuel</div><div class="num">${ls.fuel_kg.toLocaleString()} / ${ls.fuel_cap.toLocaleString()} kg capacity</div>
        <div>Takeoff weight</div><div class="num ${ls.mtow && ls.tow > ls.mtow ? 'neg' : ''}">${ls.tow.toLocaleString()} / ${(ls.mtow || 0).toLocaleString()} kg MTOW</div>
        <div>Landing weight</div><div class="num ${a.landing_weight > ls.mlw ? 'neg' : ''}">${a.landing_weight.toLocaleString()} / ${ls.mlw.toLocaleString()} kg MLW</div>
        <div>CG (takeoff)</div><div class="num ${ls.cg_ok ? '' : 'neg'}">${ls.tow_cg}% MAC — envelope ${ls.env[0]}–${ls.env[1]}%</div>
      </div><div style="margin-top:6px">${bar(ls.tow_cg, ls.env[0], ls.env[1], ls.cg_ok)}<div class="hint">Zero fuel CG ${ls.zfw_cg}% MAC</div></div></div>
      <div class="col"><b>Takeoff — ${$('#d-org').value.toUpperCase()}</b>${dist(to, 'Takeoff')}<div class="hint" style="margin-top:4px">Runways: ${rwList(r.runways.origin, $('#d-org').value.toUpperCase())}</div>
        <b style="display:block;margin-top:8px">Landing — ${$('#d-dst').value.toUpperCase()}</b>${dist(ld, 'Landing')}<div class="hint" style="margin-top:4px">Runways: ${rwList(r.runways.destination, $('#d-dst').value.toUpperCase())}</div></div></div>
    </div></div>`;
  } catch (e) { box.innerHTML = `<div class="msg bad">${esc(e.message)}</div>`; }
}
async function sendSimbrief() {
  const win = DESKTOP() ? null : window.open('', '_blank');   // opened synchronously so the browser does not block it
  try {
    const r = await api('/api/simbrief/prefill', formData());
    AF_SEL.static_id = r.static_id;
    if (win) win.location = r.url; else window.pywebview.api.open_external(r.url);
    $('#d-sbmsg').textContent = `SimBrief opened pre-filled (plan ref ${r.static_id}). Generate the plan there — this window will pull it in on its own.`;
    $('#d-fetch').textContent = 'Fetch OFP';
    watchSimbrief();
  } catch (e) { if (win) win.close(); toast(e.message, true); }
}
let sbTimer = null, sbTries = 0;
function watchSimbrief() {
  clearInterval(sbTimer); sbTries = 0;
  sbTimer = setInterval(async () => {
    if (!AF_SEL.static_id || !$('#d-sbmsg') || ++sbTries > 60) { clearInterval(sbTimer); return; }
    try {
      const {ofp} = await api('/api/simbrief?static_id=' + encodeURIComponent(AF_SEL.static_id) + '&strict=1');
      clearInterval(sbTimer);
      applyOfp(ofp);
      $('#d-sbmsg').textContent = `OFP received automatically: ${ofp.origin}→${ofp.destination}, ${ofp.aircraft_icao}, block ${n1(ofp.block_fuel_lbs)} lb.`;
      toast('SimBrief OFP imported');
    } catch (e) { /* not generated yet — keep waiting quietly */ }
  }, 10000);
}
function applyOfp(ofp) {
  OFP = ofp;
  const set = (id, v) => { const e = $(id); if (e && v) e.value = v; };
  set('#d-org', ofp.origin); set('#d-dst', ofp.destination); set('#d-alt', ofp.alternate); set('#d-route', ofp.route); set('#d-crz', ofp.cruise_alt);
  set('#d-dist', ofp.distance_nm); set('#d-ete', ofp.ete_min); set('#d-pax', ofp.pax);
  set('#d-fuel', ofp.block_fuel_lbs && Math.round(fromLb(ofp.block_fuel_lbs)));
  set('#d-zfw', ofp.zfw_lbs && Math.round(fromLb(ofp.zfw_lbs)));
  set('#d-cargo', ofp.cargo_lbs && Math.round(fromLb(ofp.cargo_lbs)));
  if (ofp.units && ((ofp.units.startsWith('kg') && UNIT() !== 'kg') || (ofp.units.startsWith('lb') && UNIT() !== 'lb'))) {
    const want = ofp.units.startsWith('kg') ? 'kg' : 'lb';
    toast(`This OFP is in ${want === 'kg' ? 'kilograms' : 'pounds'} — Operator is set to ${unitLabel()}. Change it in Settings to match.`, true);
  }
  if (ofp.flight_number) set('#d-fno', ofp.flight_number);
  const el = $('#d-ofp'); if (el) el.value = `${ofp.ofp_id} · ${ofp.aircraft_icao} ${ofp.reg} · generated ${new Date(ofp.generated * 1000).toUTCString().slice(5, 22)}Z`;
  const w = ofp.weather || {}, wx = $('#d-wx');
  if (wx) wx.innerHTML = `<div class="panel" style="margin:6px 0 0"><div class="hd">Weather from OFP</div><div class="bd"><div class="events" style="max-height:200px;white-space:pre-wrap">${['orig_metar', 'dest_metar', 'altn_metar', 'orig_taf', 'dest_taf'].filter(k => w[k]).map(k => esc(w[k])).join('\n\n') || 'No weather in this OFP.'}</div></div></div>`;
  fuelHint(); routePlan();
}
async function importSimbrief() {
  $('#d-sbmsg').textContent = 'Fetching OFP…';
  try {
    const {ofp} = await api('/api/simbrief' + (AF_SEL.static_id ? '?static_id=' + encodeURIComponent(AF_SEL.static_id) : ''));
    if (ofp.static_mismatch) toast('No OFP generated for this plan yet — imported your latest OFP instead. Check it matches.', true);
    applyOfp(ofp);
    $('#d-sbmsg').textContent = `OFP imported: ${ofp.origin}→${ofp.destination}, ${ofp.aircraft_icao}, block ${n1(ofp.block_fuel_lbs)} lb.`;
  } catch (e) { $('#d-sbmsg').textContent = 'SimBrief: ' + e.message; }
}
async function doDispatch() {
  const d = formData();
  d.weather = OFP && OFP.origin === d.origin.toUpperCase() ? OFP.weather : null;
  await act(() => api('/api/dispatch', d), 'Flight dispatched');
}
function renderActive() {
  const af = S.active_flight, box = $('#af'); if (!box) return;
  if (!af) { box.innerHTML = ''; return; }
  const kindLabel = {acmi: 'ACMI rotation', ferry: 'Ferry', cargo: 'Cargo pairing', positioning: 'Positioning',
                     company: 'Company'}[af.kind] || 'Flight';
  const r = af.restrictions || {};
  const restr = [r.max_alt ? `max ${r.max_alt} ft` : '', r.max_ias ? `max ${r.max_ias} kias` : '', r.gear_down ? 'gear down' : '', r.day_only ? 'day VMC only' : '', r.no_oceanic ? `non-ETOPS: stay within ${S.etops_nm} nm of a diversion airport` : '', r.gpu ? 'GPU/air-start required' : ''].filter(Boolean);
  box.innerHTML = `<div class="panel"><div class="hd">Active flight ${esc(af.flight_number)} <div class="tools">${af.delay_min ? `<span class="tag bad">Tech delay ${af.delay_min} min</span>` : ''}${tagStatus(af.status)}</div></div><div class="bd">
    <div class="row"><div class="col"><div class="kv"><div>Type</div><div>${af.kind === 'cargo' ? opLogo(af.customer, 26) : ''}${kindLabel} · ${esc(af.customer)}${af.std ? ` · STD ${af.std}Z` : ''}</div><div>Aircraft</div><div>${af.type} ${af.reg}${af.etops ? '' : ' <span class="neg">non-ETOPS</span>'}</div><div>Routing</div><div>${ap(af.origin)} → ${ap(af.destination)}${af.alternate ? ` alt ${af.alternate}` : ''}${af.oceanic ? ` <span class="tag ${af.etops && !r.no_oceanic ? 'info' : 'bad'}">oceanic · farthest point ${af.remote_nm} nm from a diversion airport</span>` : ''}</div>
      <div>Route</div><div style="font-family:var(--mono);font-size:11.5px">${esc(af.route) || '—'}</div><div>Plan</div><div>${af.planned_dist} nm · ETE ${hhmm(af.planned_ete)} · FL${Math.round(af.cruise_alt / 100) || '—'} · block fuel ${wtLb(af.block_fuel)} · ZFW ${wtLb(af.zfw)}${af.fuel_price_origin ? ` · Jet A $${af.fuel_price_origin}/USG at ${af.origin}` : ''}</div>
      ${af.load ? `<div>Load</div><div>${esc(af.load)}${af.dg ? ' <span class="tag warn">special load</span>' : ''} · ${n1(Math.round(af.cargo_lbs * 0.453592))} kg</div>` : ''}
      ${af.perf ? `<div>Loadsheet</div><div><a href="#" onclick="showLoadsheet();return false">TOW ${wtKg(af.perf.loadsheet.tow)} · ZFW ${wtKg(af.perf.loadsheet.zfw)} · CG ${af.perf.loadsheet.tow_cg}% MAC${af.perf.loadsheet.ballast_kg ? ' · ballast ' + wtKg(af.perf.loadsheet.ballast_kg) : ''}</a> <span class="hint">(full loadsheet)</span></div>
      ${af.perf.takeoff && af.perf.takeoff.ok != null ? `<div>Takeoff</div><div>Rwy ${af.perf.takeoff.runway} · ${af.perf.takeoff.required.toLocaleString()} ft of ${af.perf.takeoff.available.toLocaleString()} ft${af.perf.takeoff.margin < 1000 ? ` <span class="tag warn">margin ${af.perf.takeoff.margin.toLocaleString()} ft</span>` : ''}</div>` : ''}
      ${af.perf.landing && af.perf.landing.ok != null ? `<div>Landing</div><div>Rwy ${af.perf.landing.runway} · ${af.perf.landing.required.toLocaleString()} ft of ${af.perf.landing.available.toLocaleString()} ft · Vref ${af.perf.landing.vref} kt</div>` : ''}` : ''}
      ${restr.length ? `<div>Permit limits</div><div class="neg">${restr.join(' · ')} <a href="#" onclick="defectBrief();return false">how to fly this</a></div>` : ''}${af.wx_notes && af.wx_notes.length ? `<div>Weather</div><div class="neg">${af.wx_notes.map(esc).join('; ')}</div>` : ''}
      <div>Crew</div><div>${af.crew.map((id, i) => { const p = S.pilots.find(x => x.id === id); return p ? `${i === 0 ? 'Commander' : 'Second pilot'} ${p.rank} ${esc(p.name)}${p.is_self ? ' <span class="tag">you</span>' : ''}` : ''; }).filter(Boolean).join(' · ')}</div></div></div>
    <div class="col" style="max-width:300px"><div class="actions" style="margin:0;flex-wrap:wrap">
      ${af.status === 'Planned' ? `<button class="primary" onclick="act(()=>api('/api/flight/start',{}),'Tracking started')">Start tracking</button>` : ''}
      ${af.status === 'Tracking' ? `<button class="primary" onclick="filePirep(false)">File PIREP</button>` : ''}
      ${af.status === 'Planned' ? `<button onclick="flyWithCrew()">Fly with company crew</button>` : ''}
      ${af.status === 'En route' ? '' : `<button onclick="confirmDo('File a manual PIREP without telemetry? Score is capped at 70 and the sector is treated as flown as planned.', ()=>filePirep(true), {ok:'File manual PIREP'})">Manual PIREP</button>
      <button class="danger" onclick="confirmDo('Cancel this flight? The dispatch and any tracking are discarded.', ()=>act(()=>api('/api/flight/cancel',{}),'Flight cancelled'), {ok:'Cancel flight', danger:true})">Cancel</button>`}
      <button onclick="popFlight()" title="Open a compact window for a second monitor">Pop out</button></div>
      ${enrouteBox(af.id)}
      ${af.status === 'En route' ? '' : `<p class="hint" style="margin-bottom:0">Fly it yourself, or hand the sector to your own crew — they fly it while you watch the clock, and how well it goes depends on their experience, their duty time and the conditions. Load the aircraft at the gate with engines off, then start tracking. Block times, touchdown analysis, permit limits and diversion distance are recorded from telemetry.</p>`}</div></div>
    ${af.status === 'En route' ? '' : preDeparture(af)}
    <div id="tele"></div></div></div>`;
  renderTele();
}
function defectBrief() {
  const af = S.active_flight, sn = (af && af.snags) || [];
  const r = (af && af.restrictions) || {};
  const limits = [r.max_alt ? `at or below ${r.max_alt.toLocaleString()} ft` : '', r.max_ias ? `at or below ${r.max_ias} kias` : '',
    r.gear_down ? 'gear down throughout' : '', r.day_only ? 'daylight and clear of cloud' : '',
    r.no_oceanic ? `within about 60 minutes of a diversion airport (${S.etops_nm} nm)` : '', r.gpu ? 'external power and air start, APU off' : ''].filter(Boolean);
  modal('Flying this aircraft on a permit', `
    <p>The aircraft is released on a <b>special flight permit</b> with the conditions below. Operator judges the flight on
    <b>what you actually do</b>, not on whether your add-on models the failure — so a study-level aircraft can fail the system
    for real, and anything else simply flies the restriction by hand. Both count the same.</p>
    ${sn.length ? sn.map(x => `<div class="panel" style="margin:8px 0 0"><div class="hd">${esc(x.code)} — ${esc(x.name)}</div><div class="bd">
      <div class="kv"><div>Permit condition</div><div>${esc(x.effect)}</div><div>In the simulator</div><div>${esc(x.howto || '—')}</div></div></div></div>`).join('') : ''}
    ${limits.length ? `<div class="msg warn" style="margin-top:10px"><b>Operator checks that you flew:</b><br>${limits.map(esc).join('<br>')}</div>` : ''}
    <p class="hint">Breaching a limit costs score and reputation, the same as a hard landing would. If the restriction is more
    than you want to take on, the ferry board offers to rectify the defects before departure for a fee.</p>`,
    `<button class="primary" onclick="closeModal()">Close</button>`, true);
}
async function showLoadsheet() {
  try {
    const {loadsheet: L} = await api('/api/loadsheet');
    const w = L.weights, d = L.distribution, b = L.balance, pf = L.performance;
    const row = (k, v, cls) => `<tr><td style="color:var(--muted)">${esc(k)}</td><td class="num ${cls || ''}">${v}</td></tr>`;
    const kg = n => wtKg(n);
    const pct = v => `${Math.round(v * 100)}%`;
    modal(`Loadsheet — ${L.flight}`, `<div style="border:1px solid var(--line);background:var(--panel);padding:16px 20px;font-family:var(--mono);font-size:12px;line-height:1.5">
      <div style="text-align:center;border-bottom:2px solid var(--text);padding-bottom:7px;margin-bottom:10px">
        <div style="font-size:13px;font-weight:700;letter-spacing:.5px">LOADSHEET AND TRIM</div>
        <div style="color:var(--muted)">${esc(L.issued_by)}</div></div>
      <div class="row"><div class="col"><table style="width:100%">
        ${row('Flight', esc(L.flight))}${row('Date', dd(L.date))}${row('Sector', `${L.origin} – ${L.destination}${L.alternate ? ' / ' + L.alternate : ''}`)}
        ${row('Aircraft', esc(L.aircraft))}${row('Registration', esc(L.reg))}${L.customer ? row('Operating for', esc(L.customer)) : ''}
        ${L.load ? row('Load', esc(L.load) + (L.dg ? ' — special load' : '')) : ''}
        ${L.crew.map(c => row(c.role, `${c.rank} ${esc(c.name)}`)).join('')}
      </table></div><div class="col"><table style="width:100%">
        ${row('Dry operating weight', kg(w.oew))}
        ${row('Passengers', w.pax ? `${w.pax} (${kg(w.pax_kg)})` : 'none')}
        ${row('Cargo', kg(w.cargo))}${w.ballast ? row('Ballast', kg(w.ballast)) : ''}
        ${row('ZERO FUEL WEIGHT', `<b>${kg(w.zfw)}</b> / ${kg(w.mzfw)}`, w.zfw > w.mzfw ? 'neg' : '')}
        ${row('Take-off fuel', kg(w.fuel) + ` of ${kg(w.fuel_cap)}`)}
        ${row('TAKE-OFF WEIGHT', `<b>${kg(w.tow)}</b> / ${kg(w.mtow)}`, w.mtow && w.tow > w.mtow ? 'neg' : '')}
        ${row('Trip fuel', kg(w.trip))}
        ${row('LANDING WEIGHT', `<b>${kg(w.law)}</b> / ${kg(w.mlw)}`, w.law > w.mlw ? 'neg' : '')}
      </table></div></div>
      <div style="margin-top:10px;border-top:1px solid var(--line-soft);padding-top:8px" class="row">
        <div class="col"><b>DISTRIBUTION</b><table style="width:100%">
          ${row('Forward hold', kg(d.hold_fwd))}${row('Aft hold', kg(d.hold_aft))}
          ${w.pax ? row('Cabin forward', d.cabin_fwd + ' pax') + row('Cabin aft', d.cabin_aft + ' pax') : ''}
          ${row('Hold distribution', `${pct(1 - d.cargo_dist)} fwd / ${pct(d.cargo_dist)} aft`)}
        </table></div>
        <div class="col"><b>BALANCE</b><table style="width:100%">
          ${row('Zero fuel CG', b.zfw_cg + '% MAC')}
          ${row('Take-off CG', `<b>${b.tow_cg}% MAC</b>`, b.ok ? '' : 'neg')}
          ${row('Envelope', `${b.env[0]} – ${b.env[1]}% MAC`)}
          ${b.ballast_advised ? row('Ballast advised', kg(b.ballast_advised), 'neg') : ''}
        </table>${bar(b.tow_cg, b.env[0], b.env[1], b.ok)}</div>
        </div>
      <div style="margin-top:10px;border-top:1px solid var(--line-soft);padding-top:8px">
        <b>TAKE-OFF WEIGHT LIMITS</b>
        <table style="width:100%;margin-top:4px">
          <tr style="color:var(--muted)"><td>Limit</td>${L.limits.items.map(i => `<td class="num">${esc(i.name)}</td>`).join('')}<td class="num">Actual</td><td class="num">Underload</td></tr>
          <tr><td style="color:var(--muted)">Weight</td>${L.limits.items.map(i => `<td class="num ${i.name === L.limits.limiting ? 'neg' : ''}">${wtKg(i.weight, {bare: 1})}</td>`).join('')}
            <td class="num"><b>${wtKg(w.tow, {bare: 1})}</b></td>
            <td class="num ${L.limits.underload < 0 ? 'neg' : 'pos'}"><b>${wtKg(L.limits.underload)}</b></td></tr>
        </table>
        <div class="hint" style="margin-top:3px">Limited by ${esc(L.limits.limiting)} — all weights in ${unitLabel()}.</div>
      </div>
      ${pf.takeoff || pf.landing ? `<div style="margin-top:10px;border-top:1px solid var(--line-soft);padding-top:8px" class="row">
        ${pf.takeoff ? `<div class="col"><b>TAKE-OFF ${L.origin}</b><table style="width:100%">
          ${row('Runway', pf.takeoff.runway)}${row('Distance required', (pf.takeoff.required || 0).toLocaleString() + ' ft of ' + (pf.takeoff.available || 0).toLocaleString())}
          ${row('Margin', (pf.takeoff.margin || 0).toLocaleString() + ' ft', pf.takeoff.margin < 500 ? 'neg' : '')}
          ${row('Runway-limited weight', wtKg(pf.takeoff.limit_weight))}${row('Density altitude', (pf.takeoff.density_alt || 0).toLocaleString() + ' ft')}
          ${row('Wind', `${pf.takeoff.headwind >= 0 ? 'head' : 'tail'}wind ${Math.abs(pf.takeoff.headwind || 0)} kt, cross ${Math.abs(pf.takeoff.crosswind || 0)} kt`)}
        </table></div>` : ''}
        ${pf.landing ? `<div class="col"><b>LANDING ${L.destination}</b><table style="width:100%">
          ${row('Runway', pf.landing.runway)}${row('Distance required', (pf.landing.required || 0).toLocaleString() + ' ft of ' + (pf.landing.available || 0).toLocaleString())}
          ${row('Margin', (pf.landing.margin || 0).toLocaleString() + ' ft', pf.landing.margin < 500 ? 'neg' : '')}
          ${row('Vref', (pf.landing.vref || '—') + ' kt')}
        </table></div>` : ''}</div>` : ''}
      ${L.blocking.length ? `<div class="msg bad" style="margin-top:10px">${L.blocking.map(esc).join('<br>')}</div>` : ''}
      ${L.notes.length ? `<div class="msg warn" style="margin-top:10px">${L.notes.map(esc).join('<br>')}</div>` : ''}
      <div style="margin-top:14px;display:flex;justify-content:space-between;align-items:flex-end;color:var(--muted)">
        <div><div style="border-top:1px solid var(--text);width:200px;margin-bottom:3px"></div>Prepared by ${esc(L.issued_by)} operations</div>
        <div><div style="border-top:1px solid var(--text);width:200px;margin-bottom:3px"></div>Accepted by the commander</div></div>
    </div>`, `<button class="primary" onclick="closeModal()">Close</button>`, true);
  } catch (e) { toast(e.message, true); }
}
function preDeparture(af) {
  const items = [];
  const job = af.job_id && S.ferry_board.find(j => j.id === af.job_id);
  if (job) { const pend = job.docs.filter(d => d.ready > S.clock); items.push([pend.length === 0, 'Paperwork', pend.length ? `${pend.length} document(s) outstanding` : 'all documents in hand']); }
  const today = S.clock.slice(0, 10);
  const crew = af.crew.map(id => S.pilots.find(p => p.id === id)).filter(Boolean);
  const legal = crew.every(p => !(p.rest_until && p.rest_until > S.clock) && (p.duty_date === today ? p.duty_h : 0) + af.planned_ete / 60 + 1.5 <= 13);
  items.push([legal, 'Crew duty', legal ? 'crew legal for this sector' : 'a crew member is in rest or would exceed 13 h FDP']);
  const ac = af.aircraft_id && S.fleet.find(a => a.id === af.aircraft_id);
  if (ac) items.push([ac.location === af.origin && ac.status !== 'Maintenance', 'Aircraft', ac.status === 'Maintenance' ? 'in maintenance' : `${ac.reg} at ${ac.location}`]);
  if (job) items.push([job.current === af.origin, 'Aircraft', `${job.reg} at ${job.current}`]);
  items.push([!!af.ofp_id, 'OFP', af.ofp_id ? 'SimBrief plan attached' : 'no OFP imported — fuel and route not verified']);
  items.push([!af.wx_notes || af.wx_notes.length === 0 || !!af.alternate, 'Weather', af.wx_notes && af.wx_notes.length ? af.wx_notes.join('; ') : 'no adverse weather flagged']);
  if (af.perf) { const p = af.perf; const okp = (!p.takeoff || p.takeoff.ok !== false) && (!p.landing || p.landing.ok !== false) && p.loadsheet.cg_ok && !p.blocking.length;
    items.push([okp, 'Performance', okp ? `TOW ${p.loadsheet.tow.toLocaleString()} kg, CG ${p.loadsheet.tow_cg}%${p.takeoff && p.takeoff.margin != null ? `, ${p.takeoff.margin.toLocaleString()} ft margin` : ''}` : (p.blocking[0] || 'CG outside envelope')]); }
  items.push([S.sim.connected, 'Simulator', S.sim.connected ? S.sim.status : 'not connected — press Connect in the status bar']);
  items.push([af.status !== 'Planned' || !!S.sim.connected, 'Tracking', af.status === 'Tracking' ? 'recording' : 'press Start tracking with the aircraft cold at the gate']);
  return `<div style="margin-top:10px;display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:1px;background:var(--line-soft);border:1px solid var(--line-soft)">${items.map(([ok, t, d]) => `<div style="background:var(--panel);padding:5px 8px"><span class="${ok ? 'pos' : 'neg'}">${ok ? '●' : '○'}</span> <b>${t}</b><br><small class="${ok ? '' : 'neg'}">${esc(d)}</small></div>`).join('')}</div>`;
}
const DESKTOP = () => !!(window.pywebview && window.pywebview.api);
function popFlight() {
  if (DESKTOP()) { window.pywebview.api.pop_flight(); return; }
  window.open('/flight', 'operator-flight', 'width=520,height=680,menubar=no,toolbar=no,location=no,status=no');
}
/* In the desktop window, anything meant for a browser tab — SimBrief, source links,
   the printable logbook and annual reports — goes to the system browser. */
document.addEventListener('click', e => {
  if (!DESKTOP()) return;
  const a = e.target.closest('a[href]');
  if (!a) return;
  const href = a.getAttribute('href');
  if (!href || href.startsWith('#')) return;
  const external = /^https?:/i.test(href) || a.target === '_blank' || href.startsWith('/print/') || href.startsWith('/api/export') || href.startsWith('/api/saves/backup');
  if (external) {
    e.preventDefault();
    window.pywebview.api.open_external(new URL(href, location.href).href);
  }
}, true);
async function pollTracker() { try { const j = await api('/api/tracker'); TRK = j.tracker; S.sim = j.sim; renderStatus(); renderTele(); } catch (e) {} }
const PH = ['Preflight', 'Taxi out', 'Takeoff', 'Climb', 'Cruise', 'Descent', 'Approach', 'Landed', 'Taxi in', 'Arrived'];
function renderTele() {
  const box = $('#tele'); if (!box || !S.active_flight) return;
  if (S.active_flight.status !== 'Tracking') {
    // not tracking yet: show where the sector goes, so the route can be checked before
    // departure. A sector the crew have taken is nothing to do with the simulator.
    const crewing = S.active_flight.status === 'En route';
    box.innerHTML = `${crewing ? '' : `<div class="msg ${S.sim.connected ? 'ok' : 'warn'}" style="margin-top:8px">${esc(S.sim.status)}</div>`}
      <div class="row" style="margin-top:8px"><div class="col"><canvas class="track" id="track"></canvas></div></div>`;
    drawTrack();
    return;
  }
  if (!TRK) {
    box.innerHTML = `<div class="msg warn" style="margin-top:8px">Waiting for telemetry. If Operator was restarted during this flight and no
      recording survived, press <b>Start tracking</b> to pick it up from here, or file a manual PIREP.
      <div class="actions"><button class="primary" onclick="act(()=>api('/api/flight/start',{}),'Tracking resumed')">Start tracking</button>
      <button onclick="confirmDo('File a manual PIREP without telemetry? Score is capped at 70.', ()=>filePirep(true), {ok:'File manual PIREP'})">Manual PIREP</button></div>
      <div class="row" style="margin-top:8px"><div class="col"><canvas class="track" id="track"></canvas></div></div></div>`;
    drawTrack();
    return;
  }
  const l = TRK.last || {}, cur = PH.indexOf(TRK.phase);
  const v = (x, d = 0) => x == null ? '—' : Number(x).toFixed(d);
  box.innerHTML = `<div style="margin-top:10px" class="phase-strip">${PH.map((p, i) => `<div class="${i < cur ? 'done' : i === cur ? 'cur' : ''}">${p}</div>`).join('')}</div>
    <div class="tele" style="margin-top:8px">
      <div><span class="l">Altitude ft</span><span class="v">${v(l.alt_ft)}</span></div><div><span class="l">AGL ft</span><span class="v">${v(l.agl_ft)}</span></div><div><span class="l">IAS kt</span><span class="v">${v(l.ias)}</span></div><div><span class="l">GS kt</span><span class="v">${v(l.gs)}</span></div>
      <div><span class="l">V/S fpm</span><span class="v">${v(l.vs)}</span></div><div><span class="l">Heading</span><span class="v">${v(l.hdg)}°</span></div><div><span class="l">Fuel ${unitLabel()}</span><span class="v">${l.fuel_lbs == null ? '—' : Math.round(fromLb(l.fuel_lbs)).toLocaleString()}</span></div><div><span class="l">Wind</span><span class="v">${l.wind_dir != null ? `${v(l.wind_dir)}/${v(l.wind_kt)}` : '—'}</span></div>
      <div><span class="l">Block time</span><span class="v">${hhmm(TRK.block_min)}</span></div><div><span class="l">Distance nm</span><span class="v">${v(TRK.dist_nm)}</span></div><div><span class="l">Fuel used ${unitLabel()}</span><span class="v">${TRK.fuel_burn}</span></div><div><span class="l">Farthest from diversion</span><span class="v">${TRK.max_remote_nm} nm</span></div>
    </div>
    <div class="row" style="margin-top:8px"><div class="col"><canvas class="track" id="track"></canvas></div><div class="col"><div class="events">${TRK.events.map(e => `${hhmm(e.t / 60)}  ${esc(e.text)}`).join('\n') || 'No events yet.'}</div>
    <div class="hint" style="margin-top:4px">${TRK.resumed ? 'resumed after a restart · ' : ''}${TRK.samples} samples · max alt ${TRK.max_alt} ft · max ${TRK.max_ias} kias · ${TRK.max_g} G${TRK.overspeed_s ? ` · overspeed ${TRK.overspeed_s}s` : ''}${TRK.pause_s ? ` · paused ${TRK.pause_s}s` : ''}${TRK.agl_glitches ? ` · ${TRK.agl_glitches} bad AGL sample${TRK.agl_glitches > 1 ? 's' : ''} ignored` : ''}${TRK.pos_glitches ? ` · ${TRK.pos_glitches} bad position${TRK.pos_glitches > 1 ? 's' : ''} ignored` : ''}${TRK.touchdown_vs != null ? ` · touchdown ${TRK.touchdown_vs} fpm` : ''}</div></div></div>`;
  drawTrack();
}
function drawTrack() {
  const c = $('#track'); if (!c) return;
  if (!TRK) TRK = {track: [], events: [], phase: null, samples: 0};   // planned: route only
  const dark = document.documentElement.dataset.theme === 'dark';
  const col = {
    sea: dark ? '#0f1720' : '#dde8f2',
    land: dark ? '#1e2a37' : '#fafaf7',
    coast: dark ? '#3d5064' : '#a7b4c2',
    border: dark ? '#33445a' : '#c9d2dc',
    dot: dark ? '#5a6b7d' : '#93a1b0',
    dotBig: dark ? '#6e8195' : '#9aa7b4',
    label: dark ? '#93a3b4' : '#77838f',
    plan: dark ? '#4a5c70' : '#98a6b4',
    track: dark ? '#6ea8e8' : '#1c5aa6',
    ink: dark ? '#dde4ec' : '#22303f',
    halo: dark ? '#141c25' : '#f7f8fa',
    now: '#c0392b',
  };
  const W = c.clientWidth, H = c.clientHeight;
  c.width = W * 2; c.height = H * 2;
  const x = c.getContext('2d'); x.scale(2, 2);
  x.fillStyle = col.sea; x.fillRect(0, 0, W, H);
  x.font = '9.5px Segoe UI, Tahoma, sans-serif'; x.textBaseline = 'middle';

  const A = S.airports, af = S.active_flight, o = A[af.origin], d = A[af.destination];
  const clean = p => p && p.length === 2 && Number.isFinite(p[0]) && Number.isFinite(p[1])
    && Math.abs(p[0]) <= 90 && Math.abs(p[1]) <= 180
    && !(Math.abs(p[0]) < 0.02 && Math.abs(p[1]) < 0.02);
  // A point far from the one before it is a dropped-out sample, not a flight path.
  // The track stores every fifth sample, so 400 nm between points is already impossible.
  const nm = (a, b) => {
    const R = 3440.065, r = Math.PI / 180;
    const dLa = (b[0] - a[0]) * r, dLo = (b[1] - a[1]) * r;
    const h = Math.sin(dLa / 2) ** 2 + Math.cos(a[0] * r) * Math.cos(b[0] * r) * Math.sin(dLo / 2) ** 2;
    return 2 * R * Math.asin(Math.min(1, Math.sqrt(h)));
  };
  const track = [];
  for (const p of (TRK.path || [])) {
    if (!clean(p)) continue;
    if (track.length && nm(track[track.length - 1], p) > 400) continue;
    track.push(p);
  }
  const pts = track.slice();
  if (o) pts.push([o.lat, o.lon]);
  if (d) pts.push([d.lat, d.lon]);
  if (TRK.last && clean([TRK.last.lat, TRK.last.lon])) pts.push([TRK.last.lat, TRK.last.lon]);
  if (pts.length < 2) return;

  // ---- projection with a margin, keeping the aspect ratio honest
  const la = pts.map(p => p[0]), lo = pts.map(p => p[1]);
  let minLa = Math.min(...la), maxLa = Math.max(...la), minLo = Math.min(...lo), maxLo = Math.max(...lo);
  const padLa = Math.max((maxLa - minLa) * 0.18, 0.35), padLo = Math.max((maxLo - minLo) * 0.18, 0.35);
  minLa -= padLa; maxLa += padLa; minLo -= padLo; maxLo += padLo;
  const cosL = Math.cos((minLa + maxLa) / 2 * Math.PI / 180);
  const scale = Math.min(W / ((maxLo - minLo) * cosL), H / (maxLa - minLa));
  const X = lon => W / 2 + (lon - (minLo + maxLo) / 2) * cosL * scale;
  const Y = lat => H / 2 - (lat - (minLa + maxLa) / 2) * scale;

  const visMinLo0 = (minLo + maxLo) / 2 - (W / 2) / (cosL * scale), visMaxLo0 = (minLo + maxLo) / 2 + (W / 2) / (cosL * scale);
  const visMaxLa0 = (minLa + maxLa) / 2 + (H / 2) / scale, visMinLa0 = (minLa + maxLa) / 2 - (H / 2) / scale;
  const visMinLo = visMinLo0, visMaxLo = visMaxLo0, visMinLa = visMinLa0, visMaxLa = visMaxLa0;

  // ---- coastlines, national borders and major lakes
  if (GEO) {
    const detail = scale > 26 ? GEO.land50 : GEO.land110;
    const clipLo = [visMinLo - 3, visMaxLo + 3], clipLa = [visMinLa - 3, visMaxLa + 3];
    const visible = ring => {
      for (const [lon, lat] of ring)
        if (lon > clipLo[0] && lon < clipLo[1] && lat > clipLa[0] && lat < clipLa[1]) return true;
      return false;
    };
    const trace = ring => {
      x.beginPath();
      for (let i = 0; i < ring.length; i++) {
        const px = X(ring[i][0]), py = Y(ring[i][1]);
        i ? x.lineTo(px, py) : x.moveTo(px, py);
      }
    };
    x.fillStyle = col.land; x.strokeStyle = col.coast; x.lineWidth = 0.9; x.lineJoin = 'round';
    for (const ring of detail) {
      if (!visible(ring)) continue;
      trace(ring); x.closePath(); x.fill(); x.stroke();
    }
    x.fillStyle = col.sea;
    for (const ring of GEO.lakes) { if (!visible(ring)) continue; trace(ring); x.closePath(); x.fill(); }
    if (scale > 10) {
      x.strokeStyle = col.border; x.lineWidth = 0.7; x.setLineDash([3, 3]);
      for (const ring of GEO.borders) { if (!visible(ring)) continue; trace(ring); x.stroke(); }
      x.setLineDash([]);
    }
  }

  // ---- declutter: one airport per grid cell, labels only where there is room
  const CELL = 30, cells = new Map();
  const inView = k => { const a = A[k]; return a.lat > visMinLa && a.lat < visMaxLa && a.lon > visMinLo && a.lon < visMaxLo; };
  const ends = new Set([af.origin, af.destination]);
  const candidates = Object.keys(A).filter(k => !ends.has(k) && A[k].large && inView(k));
  for (const k of candidates) {
    const px = X(A[k].lon), py = Y(A[k].lat);
    if (px < 4 || px > W - 4 || py < 4 || py > H - 4) continue;
    const key = `${Math.floor(px / CELL)},${Math.floor(py / CELL)}`;
    if (!cells.has(key)) cells.set(key, {k, px, py});
  }
  const shown = [...cells.values()].slice(0, 60);
  const taken = [];
  const fits = (bx, by, bw, bh) => bx > 2 && by > 2 && bx + bw < W - 2 && by + bh < H - 2 &&
    !taken.some(t => bx < t[2] && bx + bw > t[0] && by < t[3] && by + bh > t[1]);
  const reserve = (bx, by, bw, bh) => taken.push([bx, by, bx + bw, by + bh]);

  // the scale bar owns its corner before any label is placed
  const nmPerPx = 60 / scale;
  const barNm = [50, 100, 200, 300, 500, 1000, 2000, 3000].find(v => v / nmPerPx > 46 && v / nmPerPx < W * 0.4) || 100;
  const barPx = barNm / nmPerPx, barX = W - barPx - 12, barY = H - 12;
  reserve(barX - 6, barY - 22, barPx + 14, 30);

  // the two ends get their labels next, so nothing else can push them out
  const endLabel = {};
  [[o, af.origin], [d, af.destination]].forEach(([a, n]) => {
    if (!a) return;
    const px = X(a.lon), py = Y(a.lat);
    x.font = 'bold 10px Segoe UI, Tahoma, sans-serif';
    const tw = x.measureText(n).width;
    x.font = '9.5px Segoe UI, Tahoma, sans-serif';
    const left = px + 7 + tw > W - 4;
    endLabel[n] = left ? px - 7 - tw : px + 7;
    reserve(endLabel[n] - 3, py - 8, tw + 8, 16);
  });

  x.fillStyle = col.dot;
  for (const s2 of shown) {
    x.beginPath(); x.arc(s2.px, s2.py, 1.6, 0, 7); x.fill();
  }
  if (scale > 6) {
    x.fillStyle = col.label;
    let labelled = 0;
    for (const s2 of shown) {
      if (labelled >= 22) break;
      const tw = x.measureText(s2.k).width;
      let lx = null;
      if (fits(s2.px + 4, s2.py - 6, tw + 3, 12)) lx = s2.px + 4;
      else if (fits(s2.px - 6 - tw, s2.py - 6, tw + 3, 12)) lx = s2.px - 6 - tw;
      if (lx === null) continue;
      reserve(lx, s2.py - 6, tw + 3, 12);
      x.fillText(s2.k, lx, s2.py);
      labelled++;
    }
  }

  // ---- planned great circle, then the track actually flown
  if (o && d) {
    x.strokeStyle = col.plan; x.lineWidth = 1.2; x.setLineDash([4, 4]);
    x.beginPath(); x.moveTo(X(o.lon), Y(o.lat)); x.lineTo(X(d.lon), Y(d.lat)); x.stroke(); x.setLineDash([]);
  }
  if (track.length > 1) {
    x.strokeStyle = col.track; x.lineWidth = 2.2; x.lineJoin = 'round'; x.lineCap = 'round';
    x.beginPath();
    track.forEach((p, i) => i ? x.lineTo(X(p[1]), Y(p[0])) : x.moveTo(X(p[1]), Y(p[0])));
    x.stroke();
  }

  // ---- the two ends, drawn over everything
  [[o, af.origin], [d, af.destination]].forEach(([a, n]) => {
    if (!a) return;
    const px = X(a.lon), py = Y(a.lat);
    x.fillStyle = col.halo; x.beginPath(); x.arc(px, py, 5, 0, 7); x.fill();
    x.fillStyle = col.ink; x.beginPath(); x.arc(px, py, 3, 0, 7); x.fill();
    x.font = 'bold 10px Segoe UI, Tahoma, sans-serif';
    const lx = endLabel[n] != null ? endLabel[n] : px + 7;
    x.lineWidth = 3; x.strokeStyle = col.halo; x.strokeText(n, lx, py);
    x.fillStyle = col.ink; x.fillText(n, lx, py);
    x.font = '9.5px Segoe UI, Tahoma, sans-serif';
  });

  // ---- present position, pointing where the aircraft is heading
  if (TRK.last && clean([TRK.last.lat, TRK.last.lon])) {
    const px = X(TRK.last.lon), py = Y(TRK.last.lat), hdg = (TRK.last.hdg || 0) * Math.PI / 180;
    x.save(); x.translate(px, py); x.rotate(hdg);
    x.fillStyle = col.now; x.strokeStyle = col.halo; x.lineWidth = 1.5;
    x.beginPath(); x.moveTo(0, -6); x.lineTo(4.2, 5); x.lineTo(0, 2.6); x.lineTo(-4.2, 5); x.closePath();
    x.fill(); x.stroke(); x.restore();
  }

  // ---- distance scale
  x.strokeStyle = col.label; x.lineWidth = 1;
  x.beginPath(); x.moveTo(barX, barY); x.lineTo(barX + barPx, barY); x.moveTo(barX, barY - 3); x.lineTo(barX, barY + 3);
  x.moveTo(barX + barPx, barY - 3); x.lineTo(barX + barPx, barY + 3); x.stroke();
  x.fillStyle = col.label; x.textAlign = 'center';
  x.fillText(`${barNm} nm`, barX + barPx / 2, barY - 9);
  x.textAlign = 'left';
}

/* A sector the crew are operating right now. On the game clock this never appears —
   the clock jumps to the arrival — but on a real or simulator clock the aeroplane is
   genuinely away for the block time and this is what you watch. */
function airborneLeg(id) { return (S.airborne || []).find(x => x.id === id); }

function enrouteBox(id) {
  const a = airborneLeg(id);
  if (!a) return '';
  const pct = Math.round(a.progress * 100);
  const h = Math.floor(a.minutes_left / 60), m = a.minutes_left % 60;
  return `<div class="msg" style="margin-top:10px">
    <b>Airborne with the company crew</b><br>
    ${a.origin} → ${a.destination} · off ${a.off.slice(11, 16)}Z · ETA <b>${a.eta.slice(11, 16)}Z ${dd(a.eta)}</b>
    <div style="margin:6px 0 4px;height:6px;background:var(--line);border-radius:3px;overflow:hidden">
      <div style="height:100%;width:${pct}%;background:var(--accent)"></div></div>
    <small class="hint">${pct}% of ${hhmm(a.block_min)} · ${a.minutes_left > 0 ? `${h ? h + ' h ' : ''}${m} min remaining` : 'on arrival'}. The aircraft and the crew are committed until they land; the PIREP files itself on arrival.</small></div>`;
}

async function flyWithCrew(id) {
  const af = id ? S.dispatched.find(x => x.id === id) : S.active_flight;
  if (!af) return;
  const live = S.company.clock_mode !== 'game';
  const yes = await ask(`Hand ${af.flight_number} to the operating crew? They fly the sector without the simulator. `
    + `Scoring is capped at 92 and the outcome depends on their experience, duty time and the conditions. `
    + (live ? `The aircraft and the crew will be unavailable for about ${hhmm(af.planned_ete)} while they are away.`
            : `The clock will advance by the block time.`),
    {title: 'Fly with company crew', ok: 'Hand it to the crew'});
  if (!yes) return;
  try {
    const r = await api('/api/flight/fly', id ? {id} : {});
    await load();
    if (r.filed) showPirep(r.pirep);
    else toast(`${r.flight_number} off blocks — ETA ${r.eta.slice(11, 16)}Z`);
  } catch (e) { toast(e.message, true); }
}

async function filePirep(manual) {
  try { const {pirep} = await api('/api/flight/pirep', {manual}); await load(); showPirep(pirep); }
  catch (e) { toast(e.message, true); }
}
function showPirep(p) {
  const L = p.landing;
  modal(`PIREP ${p.flight_number} — ${p.origin} → ${p.arrival}`, `<div class="row"><div class="col"><div class="score ${p.score >= 85 ? 'pos' : p.score < 60 ? 'neg' : ''}">${p.score}<span style="font-size:13px;font-weight:400;color:var(--muted)"> / 100</span></div>
    <div class="kv" style="margin-top:8px"><div>Aircraft</div><div>${p.type} ${p.reg}</div><div>Block time</div><div>${hhmm(p.block_min)}${p.delay_min ? ` <span class="neg">(+${p.delay_min} min tech delay)</span>` : ''}</div><div>Distance</div><div>${p.dist_nm} nm</div><div>Fuel burn</div><div>${wtLb(p.fuel_burn)}</div>
    <div>Landing</div><div>${p.touchdown_vs == null ? 'n/a' : `${p.touchdown_vs} fpm — ${p.landing_desc}`}</div>${L ? `<div>Touchdown</div><div>${L.ias ?? '—'} kias · pitch ${L.pitch ?? '—'}° · bank ${L.bank ?? '—'}° · ${L.g ?? '—'} G${L.bounces ? ` · ${L.bounces} bounce(s)` : ''}</div><div>Wind at touchdown</div><div>${L.xwind != null ? `crosswind ${Math.abs(L.xwind)} kt from the ${L.xwind > 0 ? 'right' : 'left'}, ${L.hdwind >= 0 ? 'headwind' : 'tailwind'} ${Math.abs(L.hdwind)} kt` : '—'}</div><div>At 50 ft</div><div>${L.flare_vs != null ? `${L.flare_vs} fpm, ${L.flare_ias} kias` : '—'}</div>
    ${(p.gates || []).map(g => `<div>At ${g.gate} ft</div><div class="${g.stable ? '' : 'neg'}">${g.ias} kias${p.vref ? ` (Vref ${p.vref})` : ''}, ${g.vs} fpm, gear ${g.gear >= 0.9 ? 'down' : 'up'} — ${g.stable ? 'stable' : esc(g.issues.join(', '))}</div>`).join('')}${L.tdz ? `<div>Touchdown point</div><div>${L.tdz.from_threshold.toLocaleString()} ft down runway ${L.tdz.runway} (${L.tdz.length.toLocaleString()} ft), ${Math.abs(L.tdz.centreline)} ft ${L.tdz.centreline > 0 ? 'right' : 'left'} of centreline</div>` : ''}` : ''}<div>Max G</div><div>${p.max_g}</div>${p.max_alt ? `<div>Max altitude</div><div>${p.max_alt} ft</div>` : ''}
    <div>Revenue</div><div class="pos">${usd(p.income)}</div><div>Direct costs</div><div class="neg">${usd(-p.costs)}</div></div></div>
    <div class="col"><b>Remarks</b><ul>${p.notes.map(n => `<li>${esc(n)}</li>`).join('') || '<li>Uneventful flight.</li>'}</ul>${p.diverted ? '<div class="msg warn">Flight did not arrive at the planned destination.</div>' : ''}
      ${p.occurrence ? occBlock(p.occurrence) : ''}${p.simulated ? '<div class="hint">Flown by the company crew without the simulator.</div>' : ''}</div></div>`,
    `<button class="primary" onclick="closeModal()">Close</button>`);
}

function occBlock(o) {
  const cls = o.severity === 'accident' ? 'bad' : o.severity === 'incident' ? 'warn' : '';
  const cas = o.fatalities ? `${o.fatalities} crew fatality${o.fatalities > 1 ? 'ies' : ''}` : o.injuries ? `${o.injuries} crew injured` : 'no injuries';
  return `<div class="msg ${cls}" style="margin-top:8px"><b>${o.severity === 'accident' ? 'Accident' : o.severity === 'incident' ? 'Serious incident' : 'Occurrence'}</b><br>${esc(o.text)}<br>
    <span class="hint">${esc(cas)}${o.cost ? ' · ' + usd(o.cost) : ''}${o.hull_loss ? ' · hull loss' : ''}</span>${o.finding && o.severity !== 'occurrence' ? `<br><span class="hint">${esc(o.finding)}</span>` : ''}</div>`;
}

/* ------------------------------------------------------------ safety */
function viewSafety() { return `<div id="safetybox" class="hint">Loading…</div>`; }
async function loadSafety() {
  try {
    const r = await api('/api/safety'); const s = r.safety;
    const sevTag = x => x === 'accident' ? '<span class="tag bad">Accident</span>' : x === 'incident' ? '<span class="tag warn">Serious incident</span>' : '<span class="tag grey">Occurrence</span>';
    $('#safetybox').innerHTML = `<div class="row"><div class="col">
      ${s.grounded_until ? `<div class="msg bad">Operations suspended until ${dd(s.grounded_until)} pending the post-accident audit.</div>` : ''}
      ${s.investigation ? `<div class="msg warn">Investigation open into ${esc(s.investigation.flight)} (${esc(s.investigation.reg || '')}), opened ${dd(s.investigation.opened)}; final report expected around ${dd(s.investigation.due)}.</div>` : ''}
      <div class="panel"><div class="hd">Occurrence log</div><div class="bd tight"><table class="grid"><tr><th>Date</th><th>Severity</th><th>Flight</th><th>Aircraft</th><th>Sector</th><th>Summary</th><th class="r">Cost</th></tr>
        ${s.occurrences.map(o => `<tr><td ${nw}>${dd(o.date)}</td><td>${sevTag(o.severity)}</td><td>${esc(o.flight)}</td><td>${o.type} ${esc(o.reg || '')}</td><td>${esc(o.sector)}</td>
          <td>${esc(o.text)}${o.fatalities ? `<br><span class="neg">${o.fatalities} crew fatality${o.fatalities > 1 ? 'ies' : ''}</span>` : o.injuries ? `<br><span class="neg">${o.injuries} crew injured</span>` : ''}${o.finding && o.severity !== 'occurrence' ? `<br><small>${esc(o.finding)}</small>` : ''}${o.report ? '<br><small>Final report published.</small>' : ''}</td><td class="num">${o.cost ? usd(o.cost) : '—'}</td></tr>`).join('') || '<tr><td colspan="7" class="hint">No occurrences recorded.</td></tr>'}</table></div></div>
    </div><div class="col" style="max-width:520px">
      <div class="panel"><div class="hd">Safety record</div><div class="bd"><div class="kv">
        <div>Sectors flown</div><div>${s.exposure.sectors.toLocaleString()} · ${n1(s.exposure.hours)} block hours</div>
        <div>Sectors since last incident</div><div>${s.since_incident.toLocaleString()}</div>
        <div>Reportable rate</div><div>${s.rate} per 1,000 sectors</div>
        <div>Hull losses</div><div class="${s.hull_losses ? 'neg' : ''}">${s.hull_losses}</div>
        <div>Crew injured / lost</div><div class="${s.fatalities ? 'neg' : ''}">${s.injuries} / ${s.fatalities}</div>
        <div>Insurance loading</div><div>${s.premium_factor.toFixed(2)}× base premium</div>
        <div>Occurrence reporting</div><div>${s.enabled ? 'Enabled' : '<span class="hint">Disabled in Settings</span>'}</div>
      </div></div></div>
      <div class="panel"><div class="hd">Current risk picture</div><div class="bd">${r.risk.length ? `<ul class="notices">${r.risk.map(x => `<li><span class="tag ${x.level === 'high' ? 'bad' : 'warn'}">${x.level === 'high' ? 'high' : 'watch'}</span> ${esc(x.text)}</li>`).join('')}</ul>` : '<span class="hint">Nothing raising risk right now: crews rested, maintenance current, no deferred defects.</span>'}
        <p class="hint">Risk on a sector is driven by crew duty time and experience, deferred defects, maintenance status, airframe age, weather, runway margin and whether the aircraft is on a special permit. Most sectors pass without event; a badly-run operation will eventually have one that does not.</p></div></div>
    </div></div>`;
  } catch (e) { $('#safetybox').innerHTML = `<div class="msg bad">${esc(e.message)}</div>`; }
}

/* ------------------------------------------------------------ logbook */
let LOG = {kind: '', type: '', grouped: true};
function logFilter(k, v) { LOG[k] = v; render(); }
function logGroup() { LOG.grouped = !LOG.grouped; render(); }

/* A pairing or a ferry with tech stops is one job, paid on completion: showing its
   sectors as separate lines makes three of them look like losses. Group them. */
function logJobs(fl) {
  const out = [];
  for (const f of fl) {
    const key = f.job_id ? `${f.kind}:${f.job_id}` : null;
    const last = out[out.length - 1];
    if (key && last && last.key === key) { last.flights.push(f); continue; }
    out.push({key, flights: [f]});
  }
  return out.map(g => {
    const net = g.flights.reduce((a, f) => a + (f.income || 0) - (f.costs || 0), 0);
    const hours = g.flights.reduce((a, f) => a + f.block_min, 0);
    const f0 = g.flights[g.flights.length - 1], f1 = g.flights[0];
    return {...g, net, hours,
      label: g.flights.length > 1
        ? `${esc(f1.kind)} job${f1.job_id ? ' #' + f1.job_id : ''}${f1.customer ? ' — ' + esc(f1.customer) : ''}`
        : null,
      routing: `${f0.origin} → ${f1.arrival}`};
  });
}
function viewLogbook() {
  const kinds = [...new Set(S.flights.map(f => f.kind))].sort();
  const types = [...new Set(S.flights.map(f => f.type))].sort();
  const fl = S.flights.filter(f => (!LOG.kind || f.kind === LOG.kind) && (!LOG.type || f.type === LOG.type));
  const hours = fl.reduce((a, f) => a + f.block_min, 0) / 60;
  const opt = (v, sel) => `<option value="${esc(v)}" ${sel === v ? 'selected' : ''}>${esc(v || 'all')}</option>`;
  return `<div class="panel"><div class="hd">Logbook <div class="tools"><a href="/api/export/logbook.csv"><button class="sm">Export CSV</button></a> <a href="/print/logbook" target="_blank"><button class="sm">Print / PDF</button></a></div></div>
    <div class="bd" style="display:flex;gap:14px;align-items:center;flex-wrap:wrap;padding-bottom:6px">
      <label style="margin:0">Work <select class="sm" onchange="logFilter('kind', this.value)">${['', ...kinds].map(v => opt(v, LOG.kind)).join('')}</select></label>
      <label style="margin:0">Type <select class="sm" onchange="logFilter('type', this.value)">${['', ...types].map(v => opt(v, LOG.type)).join('')}</select></label>
      <label style="margin:0"><input type="checkbox" style="width:auto" ${LOG.grouped ? 'checked' : ''} onchange="logGroup()"> group multi-sector jobs</label>
      <span class="hint">${fl.length} sector${fl.length === 1 ? '' : 's'} · ${n1(hours)} block hours${fl.length ? ` · average score ${Math.round(fl.reduce((a, f) => a + f.score, 0) / fl.length)}` : ''}</span>
    </div><div class="bd tight wrap-scroll"><table class="grid"><tr><th>Date</th><th>Flight</th><th>Type</th><th>Aircraft</th><th>Routing</th><th class="r">Block</th><th class="r">nm</th><th class="r">Fuel lb</th><th>Landing</th><th class="r">Score</th><th class="r">Net</th><th></th><th></th></tr>
    ${(LOG.grouped ? logJobs(fl) : fl.map(f => ({flights: [f]}))).map(g => (g.label ? `<tr style="background:var(--subtle)">
      <td>${dd(g.flights[0].filed)}</td><td colspan="3"><b>${g.label}</b> <span class="hint">${g.flights.length} sectors</span></td>
      <td>${esc(g.routing)}</td><td class="num">${hhmm(g.hours)}</td>
      <td class="num" colspan="4"></td>
      <td class="num ${g.net < 0 ? 'neg' : 'pos'}"><b>${usd(g.net)}</b></td><td colspan="2" class="hint">paid on completion</td></tr>` : '')
      + g.flights.map(f => `<tr>${g.label ? '<td class="hint" style="padding-left:16px">·</td>' : `<td>${dd(f.filed)}</td>`}<td>${esc(f.flight_number)}</td><td>${esc(f.kind)}</td><td>${f.type} ${f.reg}</td><td>${f.origin} → ${f.arrival}${f.diverted ? ' <span class="tag warn">div</span>' : ''}</td><td class="num">${hhmm(f.block_min)}</td><td class="num">${f.dist_nm}</td><td class="num">${n1(f.fuel_burn)}</td>
      <td>${f.touchdown_vs == null ? '—' : `${f.touchdown_vs} fpm <small>${f.landing_desc}</small>`}</td><td class="num ${f.score < 60 ? 'neg' : ''}">${f.score}${f.manual ? '<small> M</small>' : ''}</td><td class="num ${f.income - f.costs < 0 ? 'neg' : 'pos'}">${usd(f.income - f.costs)}</td><td>${f.occurrence ? (f.occurrence.severity === 'accident' ? '<span class="tag bad">accident</span>' : f.occurrence.severity === 'incident' ? '<span class="tag warn">incident</span>' : '<span class="tag grey">occ</span>') : ''}${f.simulated ? '<small> crew</small>' : ''}</td><td><button class="sm" onclick="showPirep(S.flights.find(x=>x.id===${f.id}))">View</button></td></tr>`).join('')).join('') || '<tr><td colspan="13" class="hint">No flights filed.</td></tr>'}
    </table></div></div>`;
}

/* ------------------------------------------------------------ finance */
function viewFinance() {
  const ownedVal = S.fleet.filter(a => a.owned).reduce((s, a) => s + a.value, 0);
  return `<div class="row"><div class="col">
    <div class="panel"><div class="hd">Ledger</div><div class="bd tight wrap-scroll"><table class="grid"><tr><th>Date</th><th>Category</th><th>Description</th><th class="r">Amount</th><th class="r">Balance</th></tr>
      ${S.ledger.map(l => `<tr><td>${dd(l.date)}</td><td>${esc(l.category)}</td><td>${esc(l.desc)}</td><td class="num ${l.amount < 0 ? 'neg' : 'pos'}">${usd(l.amount)}</td><td class="num">${usd(l.balance)}</td></tr>`).join('')}</table></div></div>
  </div><div class="col" style="max-width:480px">
    <div class="panel"><div class="hd">Monthly results</div><div class="bd tight"><table class="grid"><tr><th>Month</th><th class="r">Income</th><th class="r">Fixed costs</th><th class="r">Net</th><th class="r">Cash</th></tr>
      ${S.month_reports.map(m => `<tr><td>${esc(m.month)}</td><td class="num">${usd(m.income)}</td><td class="num">${usd(m.expenses)}</td><td class="num ${m.net < 0 ? 'neg' : 'pos'}">${usd(m.net)}</td><td class="num">${usd(m.cash)}</td></tr>`).join('') || '<tr><td colspan="5" class="hint">No month-end close yet.</td></tr>'}</table></div></div>
    <div class="panel"><div class="hd">Receivables <div class="tools hint">customers pay on ${S.terms_days}-day terms</div></div><div class="bd tight">
      <table class="grid"><tr><th>Customer</th><th>Invoice</th><th>Issued</th><th>Due</th><th class="r">Amount</th></tr>
      ${S.receivables.map(r => `<tr><td>${opLogo(r.customer, 22)}${esc(r.customer)}</td><td><small>${esc(r.desc)}</small></td><td>${dd(r.issued)}</td><td ${nw}>${dd(r.due)}</td><td class="num">${usd(r.amount)}</td></tr>`).join('') || '<tr><td colspan="5" class="hint">Nothing outstanding.</td></tr>'}
      ${S.receivables.length ? `<tr><td colspan="4"><b>Outstanding</b></td><td class="num"><b>${usd(S.outstanding)}</b></td></tr>` : ''}</table></div></div>
    <div class="panel"><div class="hd">Financing</div><div class="bd">
      <table class="grid"><tr><th>Loan</th><th class="r">Balance</th><th class="r">Instalment</th><th class="r">Months</th><th></th></tr>${S.loans.map(l => `<tr><td>#${l.id} ${usd(l.principal)} @ ${(l.apr * 100).toFixed(1)}%</td><td class="num">${usd(l.balance)}</td><td class="num">${usd(l.payment)}</td><td class="num">${l.months_left}</td><td><button class="sm" onclick="act(()=>api('/api/finance/repay',{id:${l.id}}),'Loan settled')">Settle</button></td></tr>`).join('') || '<tr><td colspan="5" class="hint">No loans.</td></tr>'}</table>
      <div class="form" style="margin-top:8px"><label>Draw term loan</label><div class="row"><input type="number" id="loan-amt" placeholder="amount" step="100000"><button onclick="act(()=>api('/api/finance/loan',{amount:$('#loan-amt').value}),'Loan drawn')">Draw</button></div></div>
      <p class="hint">7.5% APR over 60 months. Facility up to 60% of owned fleet value (${usd(ownedVal)}), minimum $2,000,000.</p></div></div>
  </div></div>`;
}
function viewStatements() { return `<div id="stmts" class="hint">Loading…</div>`; }
async function loadStatements() {
  try {
    const r = await api('/api/statements'); const b = r.balance;
    const months = Object.keys(r.utilisation).sort().slice(-6);
    const regs = [...new Set(months.flatMap(m => Object.keys(r.utilisation[m])))];
    $('#stmts').innerHTML = `<div class="row"><div class="col">
      <div class="panel"><div class="hd">Income statement by month</div><div class="bd tight"><table class="grid"><tr><th>Month</th><th>Category</th><th class="r">Amount</th></tr>
        ${r.income.map(m => m.lines.map(([c, a], i) => `<tr><td>${i === 0 ? `<b>${m.month}</b>` : ''}</td><td>${esc(c)}</td><td class="num ${a < 0 ? 'neg' : 'pos'}">${usd(a)}</td></tr>`).join('') + `<tr><td></td><td><b>Net result</b></td><td class="num ${m.net < 0 ? 'neg' : 'pos'}"><b>${usd(m.net)}</b></td></tr>`).join('') || '<tr><td colspan="3" class="hint">No operating entries yet.</td></tr>'}</table></div></div>
    </div><div class="col" style="max-width:520px">
      <div class="panel"><div class="hd">Balance sheet</div><div class="bd"><div class="kv"><div>Cash</div><div class="num ${b.cash < 0 ? 'neg' : ''}">${usd(b.cash)}</div><div>Owned aircraft (book)</div><div class="num">${usd(b.fleet)}</div><div>Lease deposits</div><div class="num">${usd(b.deposits)}</div><div>Bank loans</div><div class="num neg">${usd(-b.loans)}</div><div><b>Equity</b></div><div class="num"><b>${usd(b.equity)}</b></div></div><p class="hint">Aircraft depreciate 4.5% a year; sale proceeds follow the market cycle.</p></div></div>
      <div class="panel"><div class="hd">Fleet utilisation (block hours per month)</div><div class="bd">${regs.length ? `<canvas id="util" class="track" style="height:${30 + regs.length * 26}px"></canvas><div class="hint">Bars per aircraft, left to right: ${months.join(' · ')}</div>` : '<span class="hint">No sectors flown by fleet aircraft yet.</span>'}</div></div>
    </div></div>`;
    if (regs.length) drawUtil(r.utilisation, months, regs);
  } catch (e) { $('#stmts').innerHTML = `<div class="msg bad">${esc(e.message)}</div>`; }
}
function drawUtil(u, months, regs) {
  const c = $('#util'); c.width = c.clientWidth * 2; c.height = c.clientHeight * 2; const x = c.getContext('2d'); x.scale(2, 2);
  const W = c.clientWidth, H = c.clientHeight, max = Math.max(1, ...months.flatMap(m => Object.values(u[m])));
  const dk = document.documentElement.dataset.theme === 'dark';
  const rowH = (H - 10) / regs.length, cols = dk ? ['#4f83c4', '#6ea8e8', '#88aedb', '#5b7fa6', '#8fa3b8', '#7a8895']
                                                 : ['#1c5aa6', '#4f83c4', '#88aedb', '#b9cfea', '#2f3d4d', '#7a8895'];
  x.font = '10px Segoe UI, sans-serif';
  regs.forEach((r, i) => { const y = 5 + i * rowH; x.fillStyle = dk ? '#dde4ec' : '#2f3d4d'; x.fillText(r, 4, y + rowH / 2 + 3);
    const bw = (W - 70) / months.length - 2;
    months.forEach((m, k) => { const h = (u[m][r] || 0); x.fillStyle = cols[k % cols.length]; x.fillRect(66 + k * (bw + 2), y + 3, Math.max(1, bw * h / max), rowH - 6); if (h) { x.fillStyle = dk ? '#0f1720' : '#ffffff'; x.fillText(Math.round(h), 69 + k * (bw + 2), y + rowH / 2 + 3); } }); });
}

/* ------------------------------------------------------------ charts */
const CH = {ink: '#2f3d4d', grid: '#e4e7eb', muted: '#8b95a1', accent: '#1c5aa6',
  series: ['#1c5aa6', '#2f8f5b', '#b8860b', '#8c4a4a', '#6b4fa8', '#2f3d4d', '#4f83c4', '#a0a8b2']};
function prep(c, h) {
  const w = c.clientWidth || 600; h = h || c.clientHeight || 210;
  c.width = w * 2; c.height = h * 2;
  const x = c.getContext('2d'); x.scale(2, 2); x.clearRect(0, 0, w, h);
  x.font = '10px Segoe UI, sans-serif'; x.textBaseline = 'middle';
  return {x, w, h};
}
function niceMax(v) { if (v <= 0) return 1; const p = Math.pow(10, Math.floor(Math.log10(v))); return Math.ceil(v / p * 2) / 2 * p; }
function axes(x, w, h, pad, min, max, labels, fmt) {
  const ticks = 4;
  x.strokeStyle = CH.grid; x.fillStyle = CH.muted; x.lineWidth = 1;
  for (let i = 0; i <= ticks; i++) {
    const v = min + (max - min) * i / ticks, y = Math.round(h - pad.b - (h - pad.t - pad.b) * i / ticks) + 0.5;
    x.beginPath(); x.moveTo(pad.l, y); x.lineTo(w - pad.r, y); x.stroke();
    x.textAlign = 'right'; x.fillText(fmt ? fmt(v) : Math.round(v).toLocaleString(), pad.l - 6, y);
  }
  x.textAlign = 'center';
  const step = Math.max(1, Math.ceil(labels.length / 8));
  labels.forEach((l, i) => { if (i % step && i !== labels.length - 1) return;
    const px = pad.l + (w - pad.l - pad.r) * (labels.length === 1 ? 0.5 : i / (labels.length - 1));
    x.fillText(l, px, h - pad.b + 12); });
}
function lineChart(canvas, labels, series, opts) {
  opts = opts || {}; const c = $(canvas); if (!c) return;
  const {x, w, h} = prep(c, opts.height);
  const pad = {l: 62, r: 10, t: 10, b: 22};
  const all = series.flatMap(s => s.values).filter(v => v != null);
  if (!all.length) return;
  let max = niceMax(Math.max(...all)), min = Math.min(0, Math.min(...all));
  if (min < 0) min = -niceMax(-min);
  if (opts.zoom) {                       // scale to the data instead of anchoring at zero
    const lo = Math.min(...all), hi = Math.max(...all), span = (hi - lo) || Math.abs(hi) || 1;
    min = lo - span * 0.15; max = hi + span * 0.15;
  }
  if (opts.min != null) min = opts.min;
  axes(x, w, h, pad, min, max, labels, opts.fmt);
  const px = i => pad.l + (w - pad.l - pad.r) * (labels.length === 1 ? 0.5 : i / (labels.length - 1));
  const py = v => h - pad.b - (h - pad.t - pad.b) * (v - min) / (max - min || 1);
  if (min < 0) { const y = Math.round(py(0)) + 0.5; x.strokeStyle = CH.muted; x.beginPath(); x.moveTo(pad.l, y); x.lineTo(w - pad.r, y); x.stroke(); }
  series.forEach((s, si) => {
    const col = s.color || CH.series[si % CH.series.length];
    if (s.fill) { x.beginPath(); s.values.forEach((v, i) => i ? x.lineTo(px(i), py(v)) : x.moveTo(px(i), py(v)));
      x.lineTo(px(s.values.length - 1), py(Math.max(min, 0))); x.lineTo(px(0), py(Math.max(min, 0))); x.closePath();
      x.fillStyle = col + '22'; x.fill(); }
    x.strokeStyle = col; x.lineWidth = 1.8; x.beginPath();
    s.values.forEach((v, i) => i ? x.lineTo(px(i), py(v)) : x.moveTo(px(i), py(v))); x.stroke();
    if (s.values.length <= 24) { x.fillStyle = col; s.values.forEach((v, i) => { x.beginPath(); x.arc(px(i), py(v), 2.2, 0, 7); x.fill(); }); }
  });
}
function stackChart(canvas, labels, series, opts) {
  opts = opts || {}; const c = $(canvas); if (!c) return;
  const {x, w, h} = prep(c, opts.height);
  const pad = {l: 62, r: 10, t: 10, b: 22};
  const totals = labels.map((_, i) => series.reduce((a, s) => a + (s.values[i] || 0), 0));
  const max = niceMax(Math.max(1, ...totals));
  axes(x, w, h, pad, 0, max, labels, opts.fmt);
  const bw = Math.max(4, (w - pad.l - pad.r) / labels.length * 0.62);
  const px = i => pad.l + (w - pad.l - pad.r) * (labels.length === 1 ? 0.5 : i / (labels.length - 1));
  const py = v => h - pad.b - (h - pad.t - pad.b) * v / max;
  labels.forEach((_, i) => {
    let acc = 0;
    series.forEach((s, si) => {
      const v = s.values[i] || 0; if (!v) return;
      x.fillStyle = s.color || CH.series[si % CH.series.length];
      x.fillRect(px(i) - bw / 2, py(acc + v), bw, py(acc) - py(acc + v)); acc += v;
    });
  });
}
function scatterChart(canvas, points, opts) {
  opts = opts || {}; const c = $(canvas); if (!c) return;
  const {x, w, h} = prep(c, opts.height);
  const pad = {l: 62, r: 10, t: 10, b: 22};
  if (!points.length) { x.fillStyle = CH.muted; x.textAlign = 'center'; x.fillText('No tracked landings yet.', w / 2, h / 2); return; }
  const vs = points.map(p => p.y);
  const min = Math.min(-900, Math.min(...vs)), max = 0;
  const labels = [points[0].label, points[points.length - 1].label];
  axes(x, w, h, pad, min, max, labels, opts.fmt);
  // banding: good / firm / hard
  const bandY = v => h - pad.b - (h - pad.t - pad.b) * (v - min) / (max - min);
  const darkNow = document.documentElement.dataset.theme === 'dark';
  [[-450, -700, darkNow ? '#2c2415' : '#fff6e0'], [-700, min, darkNow ? '#2e1a1a' : '#fdecec']].forEach(([a, b, col]) => {
    x.fillStyle = col; x.fillRect(pad.l, bandY(a), w - pad.l - pad.r, bandY(b) - bandY(a));
  });
  const px = i => pad.l + (w - pad.l - pad.r) * (points.length === 1 ? 0.5 : i / (points.length - 1));
  points.forEach((p, i) => { x.fillStyle = p.y < -700 ? '#a52a2a' : p.y < -450 ? '#9a6a12' : '#2f8f5b';
    x.beginPath(); x.arc(px(i), bandY(p.y), 2.6, 0, 7); x.fill(); });
  // rolling average
  const n = Math.max(3, Math.round(points.length / 12));
  x.strokeStyle = CH.accent; x.lineWidth = 1.8; x.beginPath();
  points.forEach((p, i) => { const seg = points.slice(Math.max(0, i - n + 1), i + 1);
    const avg = seg.reduce((a, q) => a + q.y, 0) / seg.length;
    i ? x.lineTo(px(i), bandY(avg)) : x.moveTo(px(i), bandY(avg)); });
  x.stroke();
}
function legend(items) { return `<div class="legend">${items.map(([n, c]) => `<span><i style="background:${c}"></i>${esc(n)}</span>`).join('')}</div>`; }

/* ------------------------------------------------------------ analytics */
function viewAnalytics() { return `<div id="analyticsbox" class="hint">Loading…</div>`; }
let ANA = null;
async function loadAnalytics() {
  try {
    ANA = await api('/api/analytics');
    const snaps = ANA.snapshots.slice(-36);
    const hasData = snaps.length > 0;
    const labels = snaps.map(s => s.month.slice(2).replace('-', '/'));
    const usdAxis = v => { const r = CUR().rate; v = v * r;
      return Math.abs(v) >= 1e6 ? (v / 1e6).toFixed(1) + 'M' : Math.abs(v) >= 1e3 ? Math.round(v / 1e3) + 'k' : Math.round(v); };
    $('#analyticsbox').innerHTML = `
      <div class="row"><div class="col">
        <div class="panel"><div class="hd">Cash and equity <div class="tools hint">month end${ANA.current ? ' · now: cash ' + usd(ANA.current.cash) + ', equity ' + usd(ANA.current.equity) : ''}</div></div>
          <div class="bd">${hasData ? `<canvas class="chart" id="ch-cash"></canvas>${legend([['Cash', CH.series[0]], ['Equity', CH.series[1]]])}` : '<span class="hint">Charts start once your first month closes. Advance the clock to the 1st.</span>'}</div></div>
        <div class="panel"><div class="hd">Revenue by line of business</div><div class="bd">${hasData ? `<canvas class="chart" id="ch-rev"></canvas>${legend([['Ferry', CH.series[0]], ['Cargo flying', CH.series[1]], ['ACMI', CH.series[2]], ['Charter', CH.series[4]], ['Other', CH.series[7]]])}` : '<span class="hint">—</span>'}</div></div>
        <div class="panel"><div class="hd">Where the money goes <div class="tools hint">monthly costs by category</div></div><div class="bd">${hasData ? `<canvas class="chart" id="ch-cost"></canvas><div class="legend" id="lg-cost"></div>` : '<span class="hint">—</span>'}</div></div>
        <div class="panel"><div class="hd">Landing performance <div class="tools hint">touchdown rate per tracked sector, with rolling average</div></div><div class="bd"><canvas class="chart" id="ch-land"></canvas>
          <div class="hint">${ANA.landings.length} tracked landings${ANA.landings.length ? ` · average ${Math.round(ANA.landings.reduce((a, l) => a + l.vs, 0) / ANA.landings.length)} fpm · best ${Math.max(...ANA.landings.map(l => l.vs))} fpm` : ''}</div></div></div>
        <div class="panel"><div class="hd">Fleet utilisation <div class="tools hint">block hours per aircraft per month</div></div><div class="bd">${hasData ? `<canvas class="chart" id="ch-util"></canvas><div class="legend" id="lg-util"></div>` : '<span class="hint">—</span>'}</div></div>
      </div><div class="col" style="max-width:520px">
        <div class="panel"><div class="hd">Reputation <div class="tools hint">widebody work opens at 55</div></div><div class="bd">${hasData ? `<canvas class="chart" id="ch-rep" style="height:150px"></canvas>` : '<span class="hint">—</span>'}</div></div>
        <div class="panel"><div class="hd">Headcount and fleet</div><div class="bd">${hasData ? `<canvas class="chart" id="ch-size" style="height:150px"></canvas>${legend([['Aircraft', CH.series[1]], ['Pilots', CH.series[2]], ['Ground staff', CH.series[3]]])}` : '<span class="hint">—</span>'}</div></div>
        <div class="panel"><div class="hd">Aircraft profitability <div class="tools hint">direct flight revenue less direct costs</div></div><div class="bd tight"><table class="grid"><tr><th>Aircraft</th><th class="r">Sectors</th><th class="r">Hours</th><th class="r">Direct result</th></tr>
          ${ANA.aircraft.map(a => `<tr><td>${a.reg} <small>${a.type}</small>${a.in_fleet ? '' : ' <small class="hint">(gone)</small>'}</td><td class="num">${a.sectors}</td><td class="num">${n1(a.hours)}</td><td class="num ${a.revenue - a.costs < 0 ? 'neg' : 'pos'}">${usd(a.revenue - a.costs)}</td></tr>`).join('') || '<tr><td colspan="4" class="hint">No fleet flying yet.</td></tr>'}</table>
          <div class="bd hint">ACMI revenue is invoiced per block hour and shows here; ferry and cargo work is paid on completion of the job, so it appears under customers rather than against a tail.</div></div></div>
        <div class="panel"><div class="hd">Customers</div><div class="bd tight"><table class="grid"><tr><th>Customer</th><th class="r">Sectors</th><th class="r">Hours</th><th class="r">Paid</th></tr>
          ${ANA.customers.map(c => `<tr><td>${opLogo(c.name, 22)}${esc(c.name)}${c.satisfaction != null ? ` <small>satisfaction ${c.satisfaction}</small>` : ''}</td><td class="num">${c.sectors}</td><td class="num">${n1(c.hours)}</td><td class="num">${usd((c.revenue || 0) + (c.contract_revenue || 0))}</td></tr>`).join('') || '<tr><td colspan="4" class="hint">—</td></tr>'}</table></div></div>
        <div class="panel"><div class="hd">Crew hours <div class="tools hint">progress to command (2,500 h)</div></div><div class="bd tight"><table class="grid">
          ${ANA.pilots.map(p => `<tr><td>${p.rank} ${esc(p.name)}</td><td style="width:120px"><div style="height:8px;background:var(--track);border:1px solid var(--line-soft)"><div style="height:100%;width:${Math.min(100, p.hours / 2500 * 100)}%;background:${p.rank === 'CPT' ? '#2f8f5b' : '#1c5aa6'}"></div></div></td><td class="num">${n1(p.hours)} h<br><small>${n1(p.company_hours)} with us</small></td></tr>`).join('') || '<tr><td class="hint">No pilots.</td></tr>'}</table></div></div>
      </div></div>
      <div class="row"><div class="col">
        <div class="panel"><div class="hd">Company history</div><div class="bd" style="max-height:520px;overflow:auto"><ul class="tl">
          ${ANA.timeline.map(t => `<li class="k-${esc(t.kind)}"><div class="d">${dd(t.date)}</div><div class="t">${esc(t.text)}</div>${t.detail ? `<div class="x">${esc(t.detail)}</div>` : ''}</li>`).join('') || '<li class="hint">Nothing recorded yet.</li>'}
        </ul></div></div></div>
      <div class="col" style="max-width:520px"><div class="panel"><div class="hd">Annual reports <div class="tools">${ANA.years.length ? `<button class="sm" onclick="yearCard(${ANA.years[0].year})">Year in review card</button>` : ''}</div></div><div class="bd tight">
        ${ANA.years.length ? ANA.years.map(y => `<table class="grid"><tr><th colspan="2">${y.year} <span class="tools" style="float:right"><a href="/print/annual/${y.year}" target="_blank"><button class="sm">Print / PDF</button></a></span></th></tr>
          <tr><td>Income</td><td class="num">${usd(y.income)}</td></tr><tr><td>Costs</td><td class="num">${usd(y.expenses)}</td></tr>
          <tr><td>Net result</td><td class="num ${y.net < 0 ? 'neg' : 'pos'}"><b>${usd(y.net)}</b></td></tr>
          <tr><td>Sectors / hours</td><td class="num">${y.sectors} / ${n1(y.hours)}</td></tr>
          <tr><td>Fleet / pilots at year end</td><td class="num">${y.fleet} / ${y.pilots}</td></tr>
          <tr><td>Average flight score</td><td class="num">${y.avg_score}</td></tr>
          <tr><td>Occurrences (accidents)</td><td class="num ${y.accidents ? 'neg' : ''}">${y.occurrences} (${y.accidents})</td></tr>
          <tr><td>Best / worst month</td><td class="num">${esc(y.best.month.split(' ')[0])} ${usd(y.best.net)} / ${esc(y.worst.month.split(' ')[0])} ${usd(y.worst.net)}</td></tr></table>`).join('')
          : '<div class="bd hint">The first annual report is published at the end of your first calendar year.</div>'}
      </div></div></div></div>`;
    if (!hasData) { scatterChart('#ch-land', ANA.landings.map((l, i) => ({y: l.vs, label: dd(l.date)}))); return; }
    lineChart('#ch-cash', labels, [{name: 'Cash', values: snaps.map(s => s.cash), fill: true}, {name: 'Equity', values: snaps.map(s => s.equity)}], {fmt: usdAxis, zoom: true});
    stackChart('#ch-rev', labels, [
      {name: 'Ferry', values: snaps.map(s => s.revenue.ferry || 0), color: CH.series[0]},
      {name: 'Cargo', values: snaps.map(s => s.revenue.cargo || 0), color: CH.series[1]},
      {name: 'ACMI', values: snaps.map(s => s.revenue.acmi || 0), color: CH.series[2]},
      {name: 'Charter', values: snaps.map(s => s.revenue.charter || 0), color: CH.series[4]},
      {name: 'Other', values: snaps.map(s => s.revenue.other || 0), color: CH.series[7]}], {fmt: usdAxis});
    const catTotals = {};
    snaps.forEach(s => Object.entries(s.costs || {}).forEach(([k, v]) => catTotals[k] = (catTotals[k] || 0) + v));
    const cats = Object.entries(catTotals).sort((a, b) => b[1] - a[1]).slice(0, 6).map(x => x[0]);
    stackChart('#ch-cost', labels, cats.map((c, i) => ({name: c, values: snaps.map(s => (s.costs || {})[c] || 0), color: CH.series[i % CH.series.length]})), {fmt: usdAxis});
    $('#lg-cost').innerHTML = cats.map((c, i) => `<span><i style="background:${CH.series[i % CH.series.length]}"></i>${esc(c)}</span>`).join('');
    scatterChart('#ch-land', ANA.landings.map(l => ({y: l.vs, label: dd(l.date)})), {fmt: v => Math.round(v)});
    const regs = [...new Set(snaps.flatMap(s => Object.keys(s.utilisation || {})))].slice(0, 8);
    lineChart('#ch-util', labels, regs.map((r, i) => ({name: r, values: snaps.map(s => (s.utilisation || {})[r] || 0), color: CH.series[i % CH.series.length]})), {fmt: v => Math.round(v)});
    $('#lg-util').innerHTML = regs.map((r, i) => `<span><i style="background:${CH.series[i % CH.series.length]}"></i>${esc(r)}</span>`).join('') || '<span>No fleet sectors yet.</span>';
    lineChart('#ch-rep', labels, [{name: 'Reputation', values: snaps.map(s => s.reputation)}], {fmt: v => Math.round(v), zoom: true});
    lineChart('#ch-size', labels, [{name: 'Fleet', values: snaps.map(s => s.fleet), color: CH.series[1]},
      {name: 'Pilots', values: snaps.map(s => s.pilots), color: CH.series[2]},
      {name: 'Ground staff', values: snaps.map(s => s.staff), color: CH.series[3]}], {fmt: v => Math.round(v), height: 150});
  } catch (e) { $('#analyticsbox').innerHTML = `<div class="msg bad">${esc(e.message)}</div>`; }
}

/* ------------------------------------------------------------ settings */
async function dev(action, value) {
  try { const r = await api('/api/dev', {action, value}); await load(); toast(r.message); }
  catch (e) { toast(e.message, true); }
}
function devPanel() {
  if (!S.company.dev_tools) return '';
  const regs = S.fleet.map(a => a.reg);
  return `<div class="panel devtools"><div class="hd">Developer tools <div class="tools hint">for testing; this save is marked as having used them</div></div>
    <div class="bd">
      <div class="form">
        <label>Reputation</label><div class="row"><input type="number" id="dv-rep" value="${Math.round(S.company.reputation)}" min="0" max="100">
          <button onclick="dev('reputation', parseFloat($('#dv-rep').value))">Set</button>
          <button class="sm" onclick="dev('reputation', 55)">55 widebody</button>
          <button class="sm" onclick="dev('reputation', 80)">80</button></div>
        <label>Cash</label><div class="row"><input type="number" id="dv-cash" value="${Math.round(S.cash)}" step="1000000">
          <button onclick="dev('cash', parseFloat($('#dv-cash').value))">Set</button></div>
        <label>Clock</label><div class="row">${[1, 7, 30].map(d => `<button onclick="dev('advance', ${d})">+${d} day${d > 1 ? 's' : ''}</button>`).join('')}</div>
        <label>Boards</label><div class="row">
          ${['ferry', 'cargo', 'charter', 'acmi'].map(k => `<button onclick="dev('job', '${k}')">Add ${k} job</button>`).join('')}
          <button onclick="dev('refresh', false)">Refresh market</button></div>
        <label>Crew</label><div class="row"><button onclick="dev('crew', 2)">Hire a rated pair</button>
          <button onclick="dev('current', null)">Make all current and rested</button></div>
        ${regs.length ? `<label>Reposition</label><div class="row">
          <select id="dv-reg">${regs.map(r => `<option>${r}</option>`).join('')}</select>
          <input id="dv-apt" placeholder="ICAO" style="max-width:110px">
          <button onclick="dev('position', $('#dv-reg').value + ':' + $('#dv-apt').value)">Move</button></div>` : ''}
      </div>
      <p class="hint" style="margin-top:8px">These bypass the simulation. Handy for trying a feature without flying twenty sectors to reach it; not much fun if you use them to play.</p>
    </div></div>`;
}
function viewSettings() {
  const co = S.company;
  return `${devPanel()}<div class="row"><div class="col" style="max-width:680px">
    <div class="panel"><div class="hd">Flight planning &amp; simulator</div><div class="bd"><div class="form">
      <label>SimBrief username</label><input type="text" id="st-sb" value="${esc(co.simbrief_username)}">
      <label>SimBrief pilot ID</label><input type="text" id="st-sbid" value="${esc(co.simbrief_userid)}" placeholder="optional, numeric">
      <label>Simulator</label><select id="st-sim"><option value="auto" ${co.sim_source === 'auto' ? 'selected' : ''}>Auto-detect (MSFS first, then X-Plane)</option><option value="msfs" ${co.sim_source === 'msfs' ? 'selected' : ''}>MSFS 2020/2024 or Prepar3D via SimConnect</option><option value="xplane" ${co.sim_source === 'xplane' ? 'selected' : ''}>X-Plane 11/12 via UDP</option><option value="fsuipc" ${co.sim_source === 'fsuipc' ? 'selected' : ''}>FSUIPC (FSX, P3D, MSFS with FSUIPC7)</option></select>
      <label>X-Plane host</label><input type="text" id="st-xph" value="${esc(co.xp_host)}"><label>X-Plane port</label><input type="number" id="st-xpp" value="${co.xp_port}">
      <label>Game clock</label><select id="st-clock"><option value="game" ${co.clock_mode === 'game' ? 'selected' : ''}>Game time — advances with flights and the Next day controls</option><option value="sim" ${co.clock_mode === 'sim' ? 'selected' : ''}>Follow simulator — adopt the sim's Zulu date/time when tracking starts</option><option value="real" ${co.clock_mode === 'real' ? 'selected' : ''}>Real time — the company runs on the real UTC calendar</option></select>
      <label>Jet A base price $/USG</label><input type="number" step="0.01" id="st-fuel" value="${co.fuel_price_usg}">
      <label>Currency</label><select id="st-cur">${Object.entries(S.currencies || {}).map(([k, c]) =>
        `<option value="${k}" ${(S.company.currency || 'USD') === k ? 'selected' : ''}>${k} — ${esc(c.name)} (${esc(c.symbol.trim())})</option>`).join('')}</select>
      <div></div><div class="hint">Rates, values and fees are quoted in US dollars across the industry; this converts what you see at a fixed rate.</div>
      <label>Weight units</label><select id="st-units"><option value="lb" ${(S.company.weight_units || 'lb') === 'lb' ? 'selected' : ''}>Pounds (lb) — match a SimBrief account set to LBS</option><option value="kg" ${S.company.weight_units === 'kg' ? 'selected' : ''}>Kilograms (kg)</option></select>
      <label>Developer tools</label><select id="st-dev"><option value="0" ${S.company.dev_tools ? '' : 'selected'}>Off</option><option value="1" ${S.company.dev_tools ? 'selected' : ''}>On — shortcuts for testing</option></select>
      <label>Occurrences</label><select id="st-safety"><option value="1" ${co.safety_enabled === false ? '' : 'selected'}>Enabled — occurrences, incidents and accidents can happen</option><option value="0" ${co.safety_enabled === false ? 'selected' : ''}>Disabled — no incidents or accidents</option></select>
      <label>Discord webhook</label><input type="text" id="st-dc" value="${esc(co.discord_webhook)}" placeholder="https://discord.com/api/webhooks/… (posts each PIREP)">
    </div><div class="actions"><button class="primary" onclick="act(()=>api('/api/company/settings',{simbrief_username:$('#st-sb').value,simbrief_userid:$('#st-sbid').value,sim_source:$('#st-sim').value,xp_host:$('#st-xph').value,xp_port:$('#st-xpp').value,fuel_price_usg:$('#st-fuel').value,clock_mode:$('#st-clock').value,discord_webhook:$('#st-dc').value,weight_units:$('#st-units').value,currency:$('#st-cur').value,dev_tools:$('#st-dev').value==='1',safety_enabled:$('#st-safety').value==='1'}),'Settings saved')">Save</button></div>
    <p class="hint"><b>Leave this on auto-detect unless you have a reason not to.</b> X-Plane needs nothing installed — Operator subscribes to datarefs over UDP. MSFS and Prepar3D connect through SimConnect, which the installer bundles. FSUIPC is only for FSX or a setup that already uses it; you do not need it otherwise, and you do not need SimBrief either. Regional fuel prices are derived from the base price (Gulf cheaper, Africa and islands dearer).</p></div></div>
    <div class="panel"><div class="hd">Start over</div><div class="bd">
      <p style="margin:0 0 8px">Deleting the company clears this save file and returns you to the setup screen, where you can begin again with a new name, base and starting capital.</p>
      <button class="danger" onclick="confirmDo('Delete this company and start again? Everything in this save file is removed. This cannot be undone.', ()=>act(()=>api('/api/reset',{}),'Company deleted — set up a new one'), {ok:'Delete and start over', danger:true})">Delete company and start over</button>
      <span class="hint">A dated backup is kept automatically when a new version first opens a save. Other save files and backups are under Save files.</span></div></div>
  </div></div>`;
}
function viewSaves() { return `<div id="saves" class="hint">Loading…</div>`; }
async function loadSaves() {
  try {
    const r = await api('/api/saves');
    $('#saves').innerHTML = `<div class="row"><div class="col" style="max-width:760px"><div class="panel"><div class="hd">Save files</div><div class="bd tight"><table class="grid"><tr><th>Slot</th><th>Company</th><th>Clock</th><th class="r">Size</th><th></th></tr>
      ${r.saves.map(s => `<tr class="${s.current ? 'sel' : ''}"><td>${esc(s.name)}${s.current ? ' <span class="tag info">current</span>' : ''}</td><td>${esc(s.company)}</td><td>${s.clock ? dt(s.clock) : '—'}</td><td class="num">${Math.round(s.size / 1024)} KB</td><td>${s.current ? '' : `<button class="sm" onclick="act(()=>api('/api/saves/switch',{name:'${esc(s.name)}'}),'Switched save')">Open</button>`}</td></tr>`).join('') || '<tr><td colspan="5" class="hint">No save files yet.</td></tr>'}</table></div>
      <div class="bd"><div class="form"><label>New save slot</label><div class="row"><input type="text" id="sv-name" placeholder="e.g. cargo-company"><button onclick="act(()=>api('/api/saves/switch',{name:$('#sv-name').value}),'New slot opened')">Create &amp; open</button></div></div></div></div>
      <div class="panel"><div class="hd">Backup &amp; restore</div><div class="bd"><a href="/api/saves/backup"><button>Download backup of current save</button></a> &nbsp; <input type="file" id="sv-file" accept=".db" style="width:auto"> <button onclick="restoreSave()">Restore into current slot</button><p class="hint">Restore overwrites the current slot with the uploaded file.</p></div></div></div></div>`;
  } catch (e) { $('#saves').innerHTML = `<div class="msg bad">${esc(e.message)}</div>`; }
}
async function restoreSave() {
  const f = $('#sv-file').files[0]; if (!f) return toast('Choose a .db file first', true);
  if (!await ask('Overwrite the current save with this file?', {ok: 'Restore', danger: true})) return;
  const fd = new FormData(); fd.append('file', f);
  try { const j = await (await fetch('/api/saves/restore', {method: 'POST', body: fd})).json(); if (!j.ok) throw new Error(j.error); toast('Save restored'); await load(); } catch (e) { toast(e.message, true); }
}

/* ------------------------------------------------------------ help */
function viewHelp() {
  return `<div class="panel"><div class="hd">How Operator works</div><div class="bd" style="max-width:780px">
    <h2>Ferry flights</h2>
    <p>Lessors, MROs and airlines post one-off deliveries. The client supplies the aircraft and pays fuel and handling; you supply a rated captain and first officer and get paid on delivery. Accepting a job starts the paperwork: insurance, a special flight permit when the aircraft carries deferred defects, export/deregistration documents on lease returns and sales, and overflight or landing permits for every state on the route (Russia and China take a week, most of Europe needs nothing). You can pay to expedite. Deferred defects impose permit limits — maximum altitude, speed, gear down, day VMC — which are checked from telemetry; you can pay a line station to rectify them first. Non-ETOPS aircraft must stay within about ${S.etops_nm} nm of a diversion airport. Lease returns and redeliveries can be rejected at inspection, which sends you on to an MRO.</p>
    <h2>Cargo contract flying</h2>
    <p>Freight carriers — FedEx, UPS, Atlas, Kalitta, Cargolux, Cargojet, ASL, AeroLogic, Amerijet, Northern Air Cargo and others — hire contract crews when they are short. They provide the aircraft, the fuel and the load; you provide a rated captain and first officer who fly a published pattern of sectors, usually at night, over one to several days. Payment is a block-hour rate plus a day rate for each crew member, settled when the last sector is flown. Your only costs are positioning, hotels and crew time, so it is the cheapest way to earn while you build towards a fleet. Payloads are set by the carrier and can be heavy or awkward — dangerous goods, an AOG engine, oversize project cargo — so check the runway analysis before each sector.</p>
    <h2>ACMI (wet lease)</h2>
    <p>Airlines tender for capacity against named competitors. You provide Aircraft, Crew, Maintenance and Insurance: an aircraft of the exact type, two captains, two first officers, cabin crew for passenger work, a maintenance controller and a dispatcher. Reconfigure and reposition before the start date. Each day the customer publishes a rotation with departure times; your crews are limited to 13 hours of flight duty with 12 hours' rest, so a second crew set matters. KPIs are utilisation against the guarantee, completion of the published rotation and on-time performance; technical delays draw a per-minute penalty. Fewer than 10% of guaranteed hours in a month draws a notice, two notices end the contract; satisfaction of 70 or more at term end earns an extension offer. Rates and tender volume follow the season.</p>
    <h2>Your certificate</h2>
    <p>An air operator certificate says where you may fly and, if you chose it at setup, what you may fly. <b>Areas of operation</b> start as the region your base is in; work is only offered inside them and a sector to a field outside cannot be released. <b>Types on the certificate</b> are optional — found the company with one and ferry, cargo, ACMI and charter work is only offered on that type, nothing else can be released under your AOC, and the crew market fills with people rated on it. Leave it alone and the certificate carries no type restriction. Adding either later is an amendment on the Company profile: an application with a fee and a wait, and for a type a training programme, a maintenance programme, manuals and a proving flight. A second type from a manufacturer already on your certificate is cheaper and quicker. You may own an aircraft you are not approved for; it stays on the ground.</p>
    <h2>Buying and delivery</h2>
    <p>An aircraft sits where it sits. When you buy or lease, the terms screen quotes a positioning flight to your base: the seller or lessor puts a contract crew on it and flies it to you for a fee covering fuel, fees at every stop, two pilots for the days it takes, their way home and a ferry insurance binder. It is unavailable until it lands — a day or two across a country, the better part of a week across an ocean in a turboprop. Or collect it yourself for nothing and fly it home in the simulator as a sector of your own.</p>
    <h2>Fleet economics</h2>
    <p>Leases, salaries, insurance and overheads post on the 1st. A-checks every ${S.a_check_fh} FH, C-checks every 24 months, engines tracked to shop-visit limits — enrol in power-by-the-hour or pay the shop visit. Airworthiness Directives occasionally ground an aircraft. Book values depreciate and the used market runs a four-year cycle.</p>
    <h2>Flying</h2>
    <ol><li>Plan in SimBrief and import the OFP (route, fuel, weights, weather).</li><li>Dispatch, load at the gate with engines off, connect the simulator, start tracking.</li><li>Fly. Phases, touchdown rate, pitch, bank, crosswind, bounces, permit limits and distance from the nearest diversion airport are recorded.</li><li>Shut down, file the PIREP. Revenue, costs, duty time, engine hours and KPIs update; Discord gets a post if a webhook is set.</li></ol>
    <h2>Flying without the simulator</h2>
    <p>Any dispatched sector can be handed to your own crew with <b>Fly with company crew</b>. The result — block time, fuel, landing quality — comes from their experience, how much duty they have already done that day, and the weather and runway you sent them to. Scoring is capped at 92, so flying it yourself still pays best. A manual PIREP remains available and is capped at 70.</p><p>How long they take depends on your clock. On the <b>game clock</b> the clock is yours to move, so the sector files at once and the clock jumps by the block time. On a <b>real-time or simulator clock</b> the aeroplane is genuinely away: it leaves now, arrives at its ETA, and the aircraft and both pilots are committed until it lands. You can watch it run down on Dispatch and on the schedule board, and the PIREP files itself on arrival. A sector in the air cannot be cancelled, taken over or filed by hand.</p>
    <h2>Crew careers</h2>
    <p>First officers build hours on every sector they fly. Once a pilot has 2,500 total hours and 250 with your company, the Crew page offers a command upgrade: simulator details, line training and a line check over four weeks, after which they move onto the captain pay scale. Growing your own captains is cheaper than hiring them and is the only way to keep experienced people as the fleet grows. Every pilot also receives a seniority increment on each anniversary of joining.</p>
    <h2>Safety</h2>
    <p>Every sector carries a small chance of an occurrence, and the odds are not fixed: crew fatigue and inexperience, deferred defects, maintenance flown past its due point, an ageing airframe, bad weather, a marginal runway and permit ferries all multiply it. Most events are routine — a bird strike, a tyre change, a precautionary shutdown. Serious incidents damage the aircraft, ground it for weeks, trigger an insurance claim that loads your premium, and can injure crew. Accidents are rare, cost the airframe, can cost crew their lives, suspend your operations pending an audit and are followed by a formal investigation whose findings name what went wrong. The Safety page shows your record and what is raising risk right now; the whole system can be switched off in Settings.</p>
    <h2>Second monitor</h2>
    <p><b>Pop out</b> on the active flight opens a compact window with the phase strip, live telemetry, the event log and the file-PIREP button, sized to sit beside the simulator. It works from the same server, so anything you do there shows up in the main window.</p>
    <h2>Appearance</h2>
    <p>The theme control in the status bar cycles automatic, light and dark. Automatic follows your operating system, so the interface darkens when your desktop does.</p>
    <h2>Clock</h2><p>Game time advances with flights and the Next day controls; or follow the simulator's Zulu clock, or run in real time (Settings).</p>
    <h2>Tutorial</h2><p>The Getting started panel on the Dashboard tracks your progress through a first ferry job and a first ACMI contract. ${S.company.tutorial_hidden ? '<button class="sm" onclick="act(()=>api(\'/api/company/settings\',{tutorial_hidden:false}),\'Tutorial shown\')">Show it again</button>' : 'Each screen also has a help strip at the top; hide or show it per screen.'}</p>
    <h2>Glossary</h2><table class="grid">${[
      ['ACMI / wet lease', 'You provide Aircraft, Crew, Maintenance and Insurance; the lessee sells the seats and pays fuel, handling, navigation and a minimum number of block hours a month.'],
      ['Dry lease', 'Aircraft only — what you sign with AerCap or Avolon when you lease from the market.'],
      ['Block hours (BH)', 'Brake release to brake set. ACMI rates and guarantees are quoted per block hour.'],
      ['Minimum guarantee', 'Block hours the customer pays for whether or not they are flown; the month-end true-up covers the shortfall.'],
      ['FDP', 'Flight duty period. Crews are limited to 13 hours a day here, with 12 hours rest after a long duty.'],
      ['CofA', 'Certificate of Airworthiness. An aircraft with open defects outside the MEL flies on a special flight permit instead.'],
      ['Special flight permit', 'A ferry permit issued by the state of registry allowing a non-airworthy aircraft to fly to a place where it can be fixed, under conditions (altitude, speed, gear down, day VMC).'],
      ['MEL / deferred defect', 'Equipment that may be inoperative for a limited time under the Minimum Equipment List; each item carries an operational restriction.'],
      ['ETOPS', 'Approval to fly a twin beyond 60 minutes from a diversion airport. Without it, oceanic crossings must hug the coast or route via Iceland, Greenland and Canada.'],
      ['Overflight / landing permit', 'Diplomatic clearance to cross or land in a state. Lead times range from none (EU) to a week (Russia, China).'],
      ['Redelivery', 'Handing an aircraft back at lease end in the contractual condition. Lessors inspect and can reject.'],
      ['Reactivation', 'Bringing an aircraft out of storage: return-to-service checks, often with defects still deferred.'],
      ['Tech stop', 'A fuel stop when the sector exceeds the aircraft\'s range with the required reserves.'],
      ['Tankering', 'Carrying extra fuel from a cheap airport to avoid buying at an expensive one.'],
      ['A-check / C-check', 'Light check every few hundred flight hours (2 days); heavy check every 2 years (2 weeks).'],
      ['Engine shop visit (ESV)', 'Overhaul when an engine reaches its life limit; millions per engine, or covered by PBH.'],
      ['PBH', 'Power-by-the-hour: a fixed fee per flight hour to the engine OEM that covers shop visits.'],
      ['AD', 'Airworthiness Directive — mandatory inspection or modification from the regulator, sometimes grounding the aircraft.'],
      ['OTP', 'On-time performance: share of departures within 15 minutes of schedule.'],
      ['OFP', 'Operational flight plan — the SimBrief output with route, fuel and weights.'],
      ['PIREP', 'Pilot report — the filed record of a flown sector.'],
    ].map(([k, v]) => `<tr><td style="white-space:nowrap"><b>${k}</b></td><td>${v}</td></tr>`).join('')}</table>
  </div></div>`;
}

function viewCredits() { return `<div id="creditsbox" class="hint">Loading…</div>`; }
async function loadCredits() {
  try {
    const r = await api('/api/credits');
    $('#creditsbox').innerHTML = `<div class="panel" style="max-width:920px"><div class="hd">Credits and licensing</div><div class="bd">
      <p>Airport, runway and elevation data are derived from <a href="https://ourairports.com/data/" target="_blank" rel="noopener">OurAirports</a>, released into the public domain.
      Coastlines, national boundaries and lakes on the moving map come from <a href="https://www.naturalearthdata.com/" target="_blank" rel="noopener">Natural Earth</a>, also public domain.</p>
      <p>Operator branding identifies the simulated companies you work with. <b>All names and marks remain the property of their respective owners</b>; they appear here to identify the company in a simulation and their presence does not imply sponsorship, endorsement or any transfer of rights. Each mark below is listed with where it came from. A handful are original placeholder wordmarks generated for this program where no asset was obtained; dropping a file into <code>static/operators/</code> under the same filename replaces one.</p>
      </div><div class="bd tight"><table class="grid"><tr><th>Operator</th><th>Logo</th><th>Origin</th><th>Notes</th><th>Source</th></tr>
      ${r.credits.slice().sort((a, b) => (a.kind === 'placeholder') - (b.kind === 'placeholder') || String(a.operator).localeCompare(String(b.operator)))
        .map(c => { const tone = (S.logo_tone && S.logo_tone[String(c.file).replace('.png', '')]) || 'dark';
          const origin = c.kind === 'placeholder' ? '<span class="tag grey">placeholder</span>'
            : c.kind === 'sourced' ? '<span class="tag info">company asset</span>'
            : (c.license_url ? `<a href="${esc(c.license_url)}" target="_blank" rel="noopener">${esc(c.license)}</a>` : esc(c.license || 'Wikimedia Commons'));
          return `<tr><td>${esc(c.operator)}${c.category ? `<br><small>${esc(c.category)}</small>` : ''}</td><td><img class="oplogo lg-${tone}" src="/static/operators/${esc(c.file)}" alt="" style="height:22px;max-width:110px;object-fit:contain"></td><td>${origin}</td><td><small>${esc(c.note || c.artist || '')}</small></td><td>${c.source || c.source_page ? `<a href="${esc(c.source || c.source_page)}" target="_blank" rel="noopener">source</a>` : ''}</td></tr>`; }).join('')}</table></div></div>`;
  } catch (e) { $('#creditsbox').innerHTML = `<div class="msg bad">${esc(e.message)}</div>`; }
}

/* ---- a shareable year-in-review card, drawn to a canvas and downloadable */
function yearCard(year) {
  const y = (ANA.years || []).find(x => x.year === year);
  if (!y) return toast('No report for that year yet', true);
  const land = (ANA.landings || []).filter(l => (l.date || '').startsWith(String(year)));
  const best = land.length ? land.reduce((a, b) => (b.vs > a.vs ? b : a)) : null;
  const W = 1200, H = 675;
  modal(`${year} in review`, `<canvas id="ycard" width="${W}" height="${H}" style="width:100%;border:1px solid var(--line)"></canvas>
    <p class="hint" style="margin-top:8px">A summary of the year, sized for posting. Download it, or right-click to copy.</p>`,
    `<button onclick="closeModal()">Close</button><button class="primary" onclick="downloadCard(${year})">Download PNG</button>`, true);
  const c = $('#ycard'), x = c.getContext('2d');
  const ink = '#eaf0f7', dim = '#94a6ba', accent = '#4f83c4';
  const g = x.createLinearGradient(0, 0, 0, H);
  g.addColorStop(0, '#1b2735'); g.addColorStop(1, '#121a24');
  x.fillStyle = g; x.fillRect(0, 0, W, H);
  // the mark: an open great circle, the same shape as the app icon
  x.strokeStyle = accent; x.lineWidth = 9; x.lineCap = 'round';
  x.beginPath(); x.arc(88, 86, 34, -1.05, Math.PI * 2 - 1.82); x.stroke();
  x.fillStyle = accent; x.beginPath(); x.arc(88 + 34 * Math.cos(-1.05), 86 + 34 * Math.sin(-1.05), 9, 0, 7); x.fill();
  x.fillStyle = ink; x.font = 'bold 30px Segoe UI, Arial, sans-serif';
  x.fillText(esc(S.company.name).slice(0, 34), 140, 80);
  x.fillStyle = dim; x.font = '17px Segoe UI, Arial, sans-serif';
  x.fillText(`${S.company.code} · ${S.company.base} · ${year} in review`, 140, 106);

  const box = (col, row, big, label, sub) => {
    const bx = 70 + col * 358, by = 190 + row * 150;
    x.fillStyle = 'rgba(255,255,255,.045)'; x.fillRect(bx, by, 320, 118);
    x.fillStyle = ink; x.font = 'bold 40px Segoe UI, Arial, sans-serif'; x.fillText(big, bx + 22, by + 60);
    x.fillStyle = dim; x.font = '15px Segoe UI, Arial, sans-serif'; x.fillText(label, bx + 22, by + 88);
    if (sub) { x.fillStyle = accent; x.font = '14px Segoe UI, Arial, sans-serif'; x.fillText(sub, bx + 22, by + 108); }
  };
  const money = v => (Math.abs(v) >= 1e6 ? (v / 1e6).toFixed(1) + 'M' : Math.round(v / 1e3) + 'k');
  box(0, 0, `${y.sectors.toLocaleString()}`, 'sectors flown', `${n1(y.hours)} block hours`);
  box(1, 0, `${(y.nm || 0).toLocaleString()}`, 'nautical miles', `${y.fleet} aircraft at year end`);
  box(2, 0, `$${money(y.income)}`, 'invoiced', `net $${money(y.net)}`);
  box(0, 1, `${y.avg_score}`, 'average flight score', best ? `best landing ${best.vs} fpm` : '');
  box(1, 1, `${y.reputation.toFixed(1)}`, 'reputation', `${y.pilots} pilots on the roster`);
  box(2, 1, `${y.occurrences}`, 'reportable occurrences', y.accidents ? `${y.accidents} accident${y.accidents > 1 ? 's' : ''}` : 'no accidents');

  const lines = [];
  if ((y.revenue.ferry || 0) > 0) lines.push(`ferry $${money(y.revenue.ferry)}`);
  if ((y.revenue.cargo || 0) > 0) lines.push(`cargo $${money(y.revenue.cargo)}`);
  if ((y.revenue.acmi || 0) > 0) lines.push(`ACMI $${money(y.revenue.acmi)}`);
  if ((y.revenue.charter || 0) > 0) lines.push(`charter $${money(y.revenue.charter)}`);
  if ((y.revenue.other || 0) > 0) lines.push(`other $${money(y.revenue.other)}`);
  x.fillStyle = dim; x.font = '17px Segoe UI, Arial, sans-serif';
  x.fillText(lines.join('   ·   ') || 'a quiet year', 70, 560);
  if ((y.customers || []).length) {
    x.fillStyle = '#7d8fa3'; x.font = '15px Segoe UI, Arial, sans-serif';
    const names = [...new Set(y.customers.map(c => String(c).split(' via ')[0]))];
    let line = 'flew for ', shown = 0;
    for (const n of names) {
      if (x.measureText(line + n + ', ').width > W - 200) break;
      line += (shown++ ? ', ' : '') + n;
    }
    if (shown < names.length) line += ` and ${names.length - shown} more`;
    x.fillText(line, 70, 592);
  }
  x.fillStyle = '#5d6e80'; x.font = '14px Segoe UI, Arial, sans-serif';
  x.fillText('Operator — Ferry, Cargo & ACMI', 70, 632);
}
function downloadCard(year) {
  const c = $('#ycard'); if (!c) return;
  const a = document.createElement('a');
  a.download = `${(S.company.code || 'operator').toLowerCase()}-${year}-in-review.png`;
  a.href = c.toDataURL('image/png');
  a.click();
}

/* ------------------------------------------------------------ boot */
document.querySelectorAll('.menubar .m').forEach(m => m.onclick = () => { if (S && S.company) nav(m.dataset.view); });
applyTheme();
load().catch(e => { $('#view').innerHTML = `<div class="msg bad">Cannot reach the Operator server: ${esc(e.message)}</div>`; });
