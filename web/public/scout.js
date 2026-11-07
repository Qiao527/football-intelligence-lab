'use strict';
const $ = id => document.getElementById(id);
const node = (tag, text, cls) => { const n = document.createElement(tag); if (text !== undefined) n.textContent = text; if (cls) n.className = cls; return n; };
let players = [];
function option(value, label) { const o = node('option', label); o.value = value; return o; }
function renderPlayers() {
  const q = $('query').value.trim().toLowerCase(), match = $('match-filter').value, team = $('team-filter').value;
  const rows = players.filter(p => (!match || p.matchId === match) && (!team || p.team === team) && `${p.name} ${p.team}`.toLowerCase().includes(q));
  $('count').textContent = `${rows.length} PLAYER MATCH RECORD${rows.length === 1 ? '' : 'S'}`;
  $('empty').hidden = rows.length !== 0;
  $('players').replaceChildren(...rows.map(p => {
    const tr = document.createElement('tr'), identity = node('td');
    const person = node('div', undefined, 'person'); person.append(node('span', String(p.playerId).slice(-2), 'avatar'));
    const details = node('span'); details.append(node('strong', p.name), node('small', p.team)); person.append(details); identity.append(person); tr.append(identity);
    [p.fixture, p.events.length, p.passes, p.shots].forEach(v => tr.append(node('td', String(v))));
    const cell = node('td'); const button = node('button', 'View player ↗', 'row-button'); button.setAttribute('aria-label', `View ${p.name}, ${p.team}, ${p.fixture}`); button.onclick = () => { FILAnalytics.record('candidate'); showPlayer(p); }; cell.append(button); tr.append(cell); return tr;
  }));
}
function showPlayer(p) {
  FILAnalytics.record('player_profile');
  document.querySelectorAll('.profile-panel .pitch, .profile-panel .pitch-note').forEach(e => e.remove());
  $('completion-status').textContent = '';
  $('discovery').hidden = true; $('profile').hidden = false;
  $('player-name').textContent = p.name; $('player-context').textContent = `${p.team}  /  ${p.fixture}`;
  $('stats').replaceChildren(...[['Actions', p.events.length], ['Passes', p.passes], ['Shots', p.shots]].map(([label, value]) => { const d = node('div'); d.append(node('strong', String(value)), node('span', label)); return d; }));
  $('action-count').textContent = `${p.events.length} ACTIONS`;
  if (p.matchId === 'demo-scout') document.querySelector('.profile-panel').append(pitch(p.events), node('p', 'Fictional native coordinates (120 × 80). Physical direction is not certified. Select an action below to inspect its source record.', 'pitch-note'));
  $('inspector').replaceChildren(node('p', 'Select an action to see its original record here.', 'inspector-placeholder'));
  $('actions').replaceChildren(...p.events.map(e => {
    const b = node('button', undefined, 'action'); b.append(node('span', `#${e.index}`, 'action-index'));
    const detail = node('span', undefined, 'action-detail'); detail.append(node('strong', e.type.name), node('small', `Period ${e.period} · ${e.timestamp} · ${e.id}`)); b.append(detail, node('span', '↗', 'arrow'));
    b.onclick = () => { FILAnalytics.record('evidence'); document.querySelectorAll('.journey span').forEach((s, i) => s.classList.toggle('current', i === 2)); document.querySelectorAll('.action').forEach(x => x.classList.remove('selected')); b.classList.add('selected'); const title = node('h3', e.type.name); const meta = node('p', `ORIGINAL ACTION / ${e.id}`, 'eyebrow'); const pre = node('pre', JSON.stringify(e, null, 2)); $('inspector').replaceChildren(meta, title, pre); }; return b;
  }));
  document.querySelectorAll('.journey span').forEach((s, i) => s.classList.toggle('current', i === 1));
  $('player-name').focus(); window.scrollTo(0, 0);
}
$('investigation-complete').onclick = () => { $('completion-status').textContent = FILAnalytics.record('completed_investigation') ? 'Investigation marked complete in this local session.' : 'Start local measurement and inspect evidence before marking completion.'; };
$('analytics-start').onclick = () => { FILAnalytics.start(); $('analytics-status').textContent = 'Recording locally in memory'; $('analytics-start').disabled = true; $('analytics-download').disabled = false; $('analytics-stop').disabled = false; };
$('analytics-download').onclick = () => FILAnalytics.download();
$('analytics-stop').onclick = () => { FILAnalytics.stop(); $('analytics-status').textContent = 'Session discarded'; $('analytics-start').disabled = false; $('analytics-download').disabled = true; $('analytics-stop').disabled = true; };
$('player-name').tabIndex = -1;
$('back').onclick = () => { $('profile').hidden = true; $('discovery').hidden = false; document.querySelectorAll('.journey span').forEach((s, i) => s.classList.toggle('current', i === 0)); $('discover-title').focus(); window.scrollTo(0, 0); };
$('discover-title').tabIndex = -1;
['query', 'match-filter', 'team-filter'].forEach(id => $(id).addEventListener(id === 'query' ? 'input' : 'change', renderPlayers));
async function load() {
  try {
    const response = await fetch('/api/matches'); if (!response.ok) throw Error('catalog'); const matches = await response.json();
    const datasets = await Promise.all(matches.map(async m => { const r = await fetch('/api/analyze?match=' + encodeURIComponent(m.id)); if (!r.ok) throw Error('analysis'); return r.json(); }));
    matches.forEach((m, i) => {
      const fixture = `${m.home} vs ${m.away}`, groups = new Map();
      datasets[i].events.filter(e => e.player).forEach(e => { const key = `${e.team.id}:${e.player.id}`; if (!groups.has(key)) groups.set(key, {matchId: m.id, fixture, team: e.team.name, playerId: e.player.id, name: e.player.name, events: [], passes: 0, shots: 0}); const p = groups.get(key); p.events.push(e); if (e.type.name === 'Pass') p.passes++; if (e.type.name === 'Shot') p.shots++; });
      players.push(...groups.values()); $('match-filter').append(option(m.id, fixture));
    });
    try {
    const fixtureResponse = await fetch('/api/scout-fixture'); if (!fixtureResponse.ok) throw Error('scouting fixture');
    const scouting = await fixtureResponse.json(); if (scouting.provenance.mode !== 'synthetic') throw Error('source');
    const scoutingFixture = 'Linden Rovers vs Orchard Athletic', groups = new Map();
    scouting.events.filter(e => e.player).forEach(e => { const key = `${e.team.id}:${e.player.id}`; if (!groups.has(key)) groups.set(key, {matchId:'demo-scout', fixture:scoutingFixture, team:e.team.name, playerId:e.player.id, name:e.player.name, events:[], passes:0, shots:0}); const p = groups.get(key); p.events.push(e); if (e.type.name === 'Pass') p.passes++; if (e.type.name === 'Shot') p.shots++; });
    players.push(...groups.values()); $('match-filter').append(option('demo-scout', scoutingFixture));
    } catch (_) { $('load-error').textContent = 'The scouting fixture is unavailable. The original demo matches remain available.'; $('load-error').hidden = false; }
    [...new Set(players.map(p => p.team))].sort().forEach(t => $('team-filter').append(option(t, t))); renderPlayers();
  } catch (_) { $('count').textContent = 'PLAYER POOL UNAVAILABLE'; $('load-error').hidden = false; }
}
load();
