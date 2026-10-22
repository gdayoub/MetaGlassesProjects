// Keep a visible diagnostic even if the main module fails to initialize.
(function () {
  function showFailure() {
    if (document.documentElement.dataset.lensagentReady === 'true') return;
    var notice = document.getElementById('startup-status');
    if (notice) {
      notice.textContent =
        'Controls did not load. Reload from the glasses menu. Check the laptop and tunnel are still running.';
      notice.className = 'status error';
    }
  }
  window.addEventListener('error', showFailure);
  window.setTimeout(showFailure, 15000);
})();
