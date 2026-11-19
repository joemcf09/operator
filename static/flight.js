/* Compact flight window: telemetry only, for a second monitor. */
const $ = q => document.querySelector(q);
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const hhmm = m => `${Math.floor(m / 60)}:${String(Math.round(m % 60)).padStart(2, '0')}`;
const PH = ['Preflight', 'Taxi out', 'Takeoff', 'Climb', 'Cruise', 'Descent', 'Approach', 'Landed', 'Taxi in', 'Arrived'];
let S = null, TRK = null;

function theme() {
  const m = localStorage.getItem('theme') || 'auto';
  const dark = m === 'dark' || (m === 'auto' && window.matchMedia('(prefers-color-scheme: dark)').matches);
  document.documentElement.dataset.theme = dark ? 'dark' : 'light';
}
async function api(p, body) {
  const r = await fetch(p, body ? {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body)} : {});
  const j = await r.json(); if (!j.ok) throw new Error(j.error || 'failed'); return j;
}
async function tick() {
  try {
    const st = await (await fetch('/api/state')).json();
    S = st;
    const af = st.active_flight;
    $('#fl-clock').textContent = (st.clock || '').replace('T', ' ') + 'Z';
    $('#fl-no').textContent = af ? `${af.flight_number} ${af.origin}→${af.destination}` : 'No flight dispatched';
    if (!af) { $('#mini').innerHTML = `<div class="msg warn">Nothing dispatched. Use the main window to plan a flight.</div>`; return; }
    const j = await api('/api/tracker'); TRK = j.tracker; const sim = j.sim;
    const l = (TRK && TRK.last) || (sim.sample) || {};
    const v = (x, d = 0) => x == null ? '—' : Number(x).toFixed(d);
    const cur = TRK ? PH.indexOf(TRK.phase) : -1;
    $('#mini').innerHTML = `
      <div class="msg ${sim.connected ? 'ok' : 'warn'}" style="margin:0 0 8px">${esc(sim.status)}</div>
      <div class="kv" style="margin-bottom:8px"><div>Aircraft</div><div>${af.type} ${af.reg}</div>
        <div>Plan</div><div>${af.planned_dist} nm · ETE ${hhmm(af.planned_ete)}${af.cruise_alt ? ' · FL' + Math.round(af.cruise_alt / 100) : ''}</div>
        ${af.restrictions && Object.keys(af.restrictions).length ? `<div>Limits</div><div class="neg">${[af.restrictions.max_alt ? 'max ' + af.restrictions.max_alt + ' ft' : '', af.restrictions.max_ias ? 'max ' + af.restrictions.max_ias + ' kias' : '', af.restrictions.gear_down ? 'gear down' : '', af.restrictions.day_only ? 'day VMC' : ''].filter(Boolean).join(' · ')}</div>` : ''}</div>
      ${TRK ? `<div class="phase-strip">${PH.map((p, i) => `<div class="${i < cur ? 'done' : i === cur ? 'cur' : ''}" style="font-size:9.5px;padding:2px 0">${p.split(' ')[0]}</div>`).join('')}</div>` : ''}
      <div class="tele" style="margin-top:8px">
        <div><span class="l">ALT ft</span><span class="v">${v(l.alt_ft)}</span></div>
        <div><span class="l">IAS</span><span class="v">${v(l.ias)}</span></div>
        <div><span class="l">GS</span><span class="v">${v(l.gs)}</span></div>
        <div><span class="l">V/S</span><span class="v">${v(l.vs)}</span></div>
        <div><span class="l">HDG</span><span class="v">${v(l.hdg)}</span></div>
        <div><span class="l">Fuel lb</span><span class="v">${v(l.fuel_lbs)}</span></div>
        ${TRK ? `<div><span class="l">Block</span><span class="v">${hhmm(TRK.block_min)}</span></div>
        <div><span class="l">Dist nm</span><span class="v">${v(TRK.dist_nm)}</span></div>
        <div><span class="l">Touchdown</span><span class="v">${TRK.touchdown_vs == null ? '—' : TRK.touchdown_vs}</span></div>` : ''}
      </div>
      ${TRK ? `<div class="events" style="margin-top:8px;max-height:130px">${TRK.events.map(e => `${hhmm(e.t / 60)}  ${esc(e.text)}`).join('\n') || 'No events yet.'}</div>` : ''}
      <div class="actions">
        ${af.status === 'Planned' ? `<button class="primary" onclick="act('/api/flight/start')" ${sim.connected ? '' : 'disabled'}>Start tracking</button>` : ''}
        ${af.status === 'Tracking' ? `<button class="primary" onclick="act('/api/flight/pirep', {manual:false})">File PIREP</button>` : ''}
        ${sim.connected ? '' : `<button onclick="act('/api/sim/connect')">Connect sim</button>`}
      </div>
      <div id="fl-msg" class="hint" style="margin-top:6px"></div>`;
  } catch (e) { /* server may be busy; try again next tick */ }
}
async function act(path, body) {
  try { const j = await api(path, body || {});
    if (j.pirep) { const p = j.pirep;
      $('#mini').innerHTML = `<div class="panel"><div class="hd">PIREP filed — ${esc(p.flight_number)}</div><div class="bd">
        <div class="score ${p.score >= 85 ? 'pos' : p.score < 60 ? 'neg' : ''}">${p.score}<span style="font-size:12px;color:var(--muted)"> / 100</span></div>
        <div class="kv" style="margin-top:6px"><div>Sector</div><div>${p.origin} → ${p.arrival}</div><div>Block</div><div>${hhmm(p.block_min)}</div>
        <div>Landing</div><div>${p.touchdown_vs == null ? 'n/a' : p.touchdown_vs + ' fpm — ' + p.landing_desc}</div></div>
        <ul>${p.notes.map(n => `<li>${esc(n)}</li>`).join('')}</ul></div></div>`;
      setTimeout(tick, 6000); return; }
    tick();
  } catch (e) { const m = $('#fl-msg'); if (m) { m.textContent = e.message; m.className = 'neg'; } }
}
theme(); tick(); setInterval(tick, 2000);
