'use strict';
// Explicit opt-in; the session stays in memory until the user chooses to download it.
window.FILAnalytics = (() => {
  const stages = ['discovery', 'candidate', 'player_profile', 'evidence', 'completed_investigation'];
  let started = null, events = [];
  function record(stage) {
    if (started === null || stage !== stages[events.length]) return false;
    events.push({stage, elapsed_ms: Math.round(performance.now() - started)});
    return true;
  }
  return {
    start() { started = performance.now(); events = [{stage: 'discovery', elapsed_ms: 0}]; },
    record,
    snapshot() { return {version: 1, sessions: started === null ? [] : [{events: events.map(e => ({...e}))}]}; },
    download() {
      if (started === null) return false;
      const url = URL.createObjectURL(new Blob([JSON.stringify(this.snapshot(), null, 2)], {type: 'application/json'}));
      const a = document.createElement('a'); a.href = url; a.download = 'fil-local-journey.json'; a.click(); URL.revokeObjectURL(url); return true;
    },
    stop() { started = null; events = []; },
  };
})();
