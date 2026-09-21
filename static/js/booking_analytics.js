(function () {
  "use strict";

  var configNode = document.getElementById("booking-analytics-config");
  if (!configNode) return;
  var config;
  try { config = JSON.parse(configNode.textContent); } catch (_) { return; }
  if (!config || config.enabled !== true || typeof config.context !== "string" ||
      !config.context || config.endpoint !== "/reservas/analitica/eventos") return;
  if (!window.fetch || !window.crypto || !window.crypto.randomUUID || !window.AbortController) return;

  var SAMPLE_MS = 5000;
  var REPORT_MS = 30000;
  var IDLE_MS = 60000;
  var RETRY_MS = 15000;
  var current = null;
  var blocked = false;
  var recoveryOnResume = 0;
  var previouslyAllowed = allowed();

  function now() { return window.performance.now(); }
  function allowed() {
    return Boolean(window.PortoBreakCookies && window.PortoBreakCookies.allows("analytics"));
  }
  function visible() { return document.visibilityState === "visible"; }
  function isCurrent(state) { return current === state && allowed(); }
  function clearTimer(state) {
    if (state.timer !== null) window.clearInterval(state.timer);
    state.timer = null;
  }
  function stop() {
    recoveryOnResume = 0;
    if (!current) return;
    var previous = current;
    current = null;
    clearTimer(previous);
    if (previous.controller) previous.controller.abort();
  }

  // Only foreground time shortly after an interaction is counted. Clamping a
  // late sample prevents suspended tabs/devices from adding hours on wake-up.
  function sample(state) {
    var time = now();
    if (state.visible && !state.paused) {
      var start = Math.max(state.lastSample, time - SAMPLE_MS);
      var end = Math.min(time, state.lastInteraction + IDLE_MS);
      state.activeMs += Math.max(0, end - start);
    }
    state.lastSample = time;
  }

  function startTimer(state) {
    if (state.timer !== null || !state.visible || state.paused) return;
    state.timer = window.setInterval(function () {
      if (!isCurrent(state)) {
        if (current === state) stop();
        else clearTimer(state);
        return;
      }
      sample(state);
      if (now() - state.lastReport >= REPORT_MS) state.pendingFlush = true;
      pump(state);
    }, SAMPLE_MS);
  }

  function start(recoveries) {
    if (current || blocked || !allowed()) return;
    var time = now();
    var state = {
      pageId: window.crypto.randomUUID(),
      activeMs: 0, acknowledgedSeconds: 0, pageAcknowledged: false,
      lastSample: time, lastInteraction: time, lastReport: time,
      nextAttempt: 0, pendingFlush: false, inFlight: false,
      visible: visible(), paused: false, timer: null, controller: null,
      recoveries: recoveries || recoveryOnResume,
    };
    recoveryOnResume = 0;
    current = state;
    startTimer(state);
    pump(state);
  }

  function pump(state) {
    if (!isCurrent(state) || state.inFlight || now() < state.nextAttempt) return;
    var seconds = Math.floor(state.activeMs / 1000);
    var isPageview = !state.pageAcknowledged;
    // Do not start a visit in a tab that has never been foregrounded.
    if (isPageview && (!state.visible || state.paused)) return;
    if (!isPageview && (!state.pendingFlush || seconds <= state.acknowledgedSeconds)) return;
    var payload = isPageview ? {
      type: "pageview", context: config.context, page_id: state.pageId,
    } : {
      type: "engagement", page_id: state.pageId, active_seconds: seconds,
    };
    state.inFlight = true;
    state.pendingFlush = false;
    state.lastReport = now();
    var controller = new window.AbortController();
    state.controller = controller;
    window.fetch(config.endpoint, {
      method: "POST", credentials: "same-origin", cache: "no-store",
      headers: { "Content-Type": "application/json", "Accept": "application/json" },
      body: JSON.stringify(payload), keepalive: true, signal: controller.signal,
    }).then(function (response) {
      if (!isCurrent(state)) return;
      // Invalid/expired signed contexts require a fresh document, not retries.
      if (response.status === 400 || response.status === 403) {
        blocked = true;
        stop();
        return;
      }
      if (response.status === 409) {
        // A session can expire while a page remains open. Retry with a new
        // page once, but never spin if the server keeps rejecting the context.
        var recoveries = state.recoveries + 1;
        var canRestart = state.visible && !state.paused;
        stop();
        if (recoveries > 1) { blocked = true; return; }
        if (canRestart) start(recoveries);
        else recoveryOnResume = recoveries;
        return;
      }
      if (!response.ok) throw new Error("Analytics unavailable");
      if (isPageview) state.pageAcknowledged = true;
      else {
        state.acknowledgedSeconds = Math.max(state.acknowledgedSeconds, seconds);
        // A completed heartbeat proves the renewed session works. A later
        // genuine idle expiry may recover again, unlike a rejection loop.
        state.recoveries = 0;
      }
      state.nextAttempt = 0;
    }).catch(function () {
      if (!isCurrent(state)) return;
      state.nextAttempt = now() + RETRY_MS;
      state.pendingFlush = true;
    }).finally(function () {
      if (!isCurrent(state)) return;
      state.inFlight = false;
      state.controller = null;
      pump(state);
    });
  }

  function flush(state) {
    state.pendingFlush = true;
    pump(state);
  }
  function interaction() {
    if (!current || !allowed() || !current.visible || current.paused) return;
    sample(current);
    current.lastInteraction = now();
    pump(current);
  }

  window.addEventListener("portobreak:consent-changed", function () {
    var hasConsent = allowed();
    var wasAllowed = previouslyAllowed;
    previouslyAllowed = hasConsent;
    if (!hasConsent) { blocked = false; stop(); return; }
    if (!wasAllowed) { blocked = false; start(); }
  });
  ["pointerdown", "keydown", "touchstart", "scroll"].forEach(function (eventName) {
    window.addEventListener(eventName, interaction, { passive: true });
  });
  document.addEventListener("visibilitychange", function () {
    if (!allowed()) return;
    if (!current) {
      if (visible()) start();
      return;
    }
    var state = current;
    sample(state);
    state.visible = visible();
    if (!state.visible) {
      clearTimer(state);
      flush(state);
      return;
    }
    state.lastSample = now();
    state.lastInteraction = now();
    startTimer(state);
    pump(state);
  });
  window.addEventListener("pagehide", function () {
    if (!current || !allowed()) return;
    var state = current;
    sample(state);
    state.paused = true;
    clearTimer(state);
    flush(state);
  });
  window.addEventListener("pageshow", function () {
    if (!allowed()) { stop(); return; }
    if (!current) { start(); return; }
    if (!current.paused) return;
    current.paused = false;
    current.visible = visible();
    current.lastSample = now();
    current.lastInteraction = now();
    startTimer(current);
    pump(current);
  });
  start();
})();
