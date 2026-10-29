/* Forge visual kit: lets the live options board (scripts/direction_board.py, board-live.html) switch this page's
   direction. On load it reads ?dir=name from the address; afterwards it accepts postMessage({forgeDir: name}) from the
   parent frame only, and answers {forgeDirApplied: name}. It only ever changes the data-dir attribute.
   Include it in every page that will be shown on the board: <script src="kit-dir.js"></script> */
(function () {
  function apply(d) {
    if (typeof d !== 'string' || !/^[a-z0-9-]{2,40}$/.test(d)) return false;
    document.documentElement.setAttribute('data-dir', d);
    document.querySelectorAll('[data-dir]').forEach(function (e) { e.setAttribute('data-dir', d); });
    return true;
  }
  try { var q = new URLSearchParams(location.search).get('dir'); if (q) apply(q); } catch (e) { /* no query access */ }
  window.addEventListener('message', function (e) {
    if (e.source !== window.parent || !e.data || typeof e.data !== 'object' || !('forgeDir' in e.data)) return;
    if (apply(e.data.forgeDir)) { try { e.source.postMessage({ forgeDirApplied: e.data.forgeDir }, '*'); } catch (err) { /* parent gone */ } }
  });
})();
