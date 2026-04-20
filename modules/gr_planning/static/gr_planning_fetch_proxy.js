(function () {
  const originalFetch = window.fetch ? window.fetch.bind(window) : null;
  if (!originalFetch || window.__grPlanningFetchProxyInstalled) {
    return;
  }
  window.__grPlanningFetchProxyInstalled = true;

  function rewriteUrl(input) {
    if (typeof input !== 'string') {
      return input;
    }
    if (/^https?:\/\//i.test(input) || input.startsWith('/api/gr_planning/')) {
      return input;
    }
    if (input.startsWith('/api/')) {
      return '/api/gr_planning/' + input.slice(5);
    }
    return input;
  }

  window.fetch = function (input, init) {
    return originalFetch(rewriteUrl(input), init);
  };
})();
