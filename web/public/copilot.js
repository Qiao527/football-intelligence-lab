'use strict';
const form = $('copilot-form');
let fixturePromise;
function fixture() {
  if (!fixturePromise) fixturePromise = fetch('/api/scout-fixture').then(r => {
    if (!r.ok) throw Error('The fictional fixture could not be loaded.');
    return r.json();
  }).catch(e => { fixturePromise = null; throw e; });
  return fixturePromise;
}
function pitch(events) {
  const ns = 'http://www.w3.org/2000/svg', svg = document.createElementNS(ns, 'svg');
  svg.setAttribute('viewBox', '0 0 120 80'); svg.setAttribute('role', 'img');
  svg.setAttribute('aria-label', 'Fictional action locations on the native 120 by 80 pitch');
  for (const [tag, attrs] of [
    ['rect', {x:1,y:1,width:118,height:78}], ['line', {x1:60,y1:1,x2:60,y2:79}],
    ['circle', {cx:60,cy:40,r:10}], ['rect', {x:1,y:18,width:18,height:44}],
    ['rect', {x:101,y:18,width:18,height:44}]
  ]) {
    const shape = document.createElementNS(ns, tag); Object.entries(attrs).forEach(([k,v]) => shape.setAttribute(k,v));
    shape.setAttribute('fill','none'); shape.setAttribute('stroke','#789885'); shape.setAttribute('stroke-width','.45'); svg.append(shape);
  }
  events.forEach(e => {
    if (!Array.isArray(e.location) || e.location.length !== 2 || !e.location.every(Number.isFinite)) return;
    const dot = document.createElementNS(ns, 'circle'); dot.setAttribute('cx',e.location[0]); dot.setAttribute('cy',e.location[1]); dot.setAttribute('r','1.2'); dot.setAttribute('fill','#d7f785');
    const title = document.createElementNS(ns, 'title'); title.textContent = `${e.id} · ${e.type.name}`; dot.append(title); svg.append(dot);
  });
  const box = node('div', undefined, 'pitch'); box.append(svg); return box;
}
async function openCandidate(c, eventId) {
  try {
    const data = await fixture();
    if (data.provenance.mode !== 'synthetic' || c.match_id !== 'demo-scout') throw Error('Unsupported fixture.');
    const events = data.events.filter(e => e.player?.id === c.player_id && e.team?.name === c.team);
    if (!events.length) throw Error('Player evidence is unavailable.');
    FILAnalytics.record('candidate');
    showPlayer({name:c.name, team:c.team, fixture:c.fixture, matchId:c.match_id, playerId:c.player_id, events,
      passes:events.filter(e => e.type.name === 'Pass').length, shots:events.filter(e => e.type.name === 'Shot').length});
    if (eventId) {
      const index = events.findIndex(e => e.id === eventId);
      if (index >= 0) { document.querySelectorAll('#actions .action')[index].click(); $('inspector').scrollIntoView({block:'nearest'}); }
    }
  } catch (_) { $('copilot-status').textContent = 'Could not open the fictional player evidence. Please retry.'; }
}
function renderCopilot(result) {
  const container = $('copilot-results'); container.replaceChildren();
  if (result.abstention) container.append(node('p', result.abstention, 'copilot-abstain'));
  result.candidates.forEach(c => {
    const card = node('article', undefined, 'candidate-card');
    card.append(node('p', 'FICTIONAL CANDIDATE / SINGLE MATCH', 'eyebrow'), node('h3', c.name), node('p', `${c.team} · ${c.fixture}`), node('p', c.explanation));
    const counts = c.counts;
    card.append(node('p', `Conventional context: ${counts.passes} recorded passes · ${counts.shots} recorded shots. No exposure-adjusted comparison is available.`));
    const evidence = node('div');
    for (const [title, ids] of [['Supporting actions', c.supporting_event_ids], ['Contradictory actions', c.opposing_event_ids]]) {
      const heading = node('strong', `${title}: `); evidence.append(heading);
      if (!ids.length) evidence.append(document.createTextNode('None recorded in this sample.'));
      ids.forEach(id => { const b = node('button', id, 'evidence-link'); b.type = 'button'; b.onclick = () => openCandidate(c, id); evidence.append(b); });
      evidence.append(node('br'));
    }
    card.append(evidence);
    const b = node('button','Open player & pitch ↗'); b.type = 'button'; b.onclick = () => openCandidate(c); card.append(b); container.append(card);
  });
  const limits = node('p', result.limitations.join(' '), 'footnote'); container.append(limits);
}
form.addEventListener('submit', async e => {
  e.preventDefault(); $('copilot-run').disabled = true; $('copilot-results').replaceChildren(); $('copilot-status').textContent = 'Checking the fictional records…';
  try {
    const res = await fetch('/api/scout', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({query:$('scout-need').value})});
    if (!res.ok) throw Error(); const result = await res.json();
    if (result.source_mode !== 'synthetic') throw Error();
    renderCopilot(result); $('copilot-status').textContent = 'Rule-based preview · no live AI model used';
  } catch (_) { $('copilot-status').textContent = 'The scouting request could not be completed. Please retry.'; }
  finally { $('copilot-run').disabled = false; }
});
