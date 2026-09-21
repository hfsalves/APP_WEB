"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const vm = require("node:vm");

const source = fs.readFileSync(path.join(__dirname, "../static/js/booking_cookie_preferences.js"), "utf8");
const initialTime = 1800000000000;
const choice = (overrides = {}) => ({
  version: "2026-09-21.1", decided_at: "2026-09-21T12:00:00+00:00",
  expires_at: initialTime / 1000 + 180 * 86400,
  preferences: false, external_maps: false, analytics: false, ...overrides,
});

function harness(initialConsent = null) {
  let now = initialTime;
  let serverConsent = initialConsent;
  let responder = null;
  const requests = [], events = [], timers = new Map(), channels = [];
  let timerId = 0;

  class EventTarget {
    constructor() { this.listeners = new Map(); }
    addEventListener(type, handler) {
      if (!this.listeners.has(type)) this.listeners.set(type, []);
      this.listeners.get(type).push(handler);
    }
    dispatchEvent(event) {
      for (const handler of this.listeners.get(event.type) || []) handler(event);
    }
  }
  class Element extends EventTarget {
    constructor() {
      super();
      this.checked = false; this.hidden = false; this.disabled = false;
      this.open = false; this.isConnected = true; this.dataset = {};
      this.attributes = {}; this.textContent = "";
    }
    setAttribute(name, value) { this.attributes[name] = value; }
    hasAttribute(name) { return Object.hasOwn(this.attributes, name); }
    closest(selector) {
      return selector.startsWith("[") && this.hasAttribute(selector.slice(1, -1)) ? this : null;
    }
    getClientRects() { return this.hidden ? [] : [{}]; }
    focus() { document.activeElement = this; }
    showModal() { this.open = true; }
    close() { this.open = false; this.dispatchEvent({ type: "close" }); }
  }
  const document = new EventTarget();
  document.activeElement = null;
  document.visibilityState = "visible";
  const elements = Object.fromEntries([
    "config", "banner", "dialog", "preferences", "external-maps", "analytics", "status", "banner-error", "dialog-error",
  ].map(name => [name, new Element()]));
  elements.config.textContent = JSON.stringify({
    consent: initialConsent, endpoint: "/reservas/preferencias-cookies",
    ui: { saved: "Saved", save_error: "Failed" },
  });
  const buttons = ["accept", "reject", "selection"].map(value => {
    const button = new Element();
    button.attributes["data-cookie-save"] = value;
    button.dataset.cookieSave = value;
    return button;
  });
  document.getElementById = id => elements[id.replace("booking-cookie-", "")] || null;
  document.querySelectorAll = selector => selector === "[data-cookie-save]" ? buttons : [];
  const window = new EventTarget();
  window.dispatchEvent = event => { events.push(event); EventTarget.prototype.dispatchEvent.call(window, event); };
  const context = {
    window, document, Element,
    Date: class extends Date { static now() { return now; } },
    CustomEvent: class { constructor(type, options) { this.type = type; this.detail = options.detail; } },
    setTimeout(callback, delay) { const id = ++timerId; timers.set(id, { callback, delay }); return id; },
    clearTimeout(id) { timers.delete(id); },
    BroadcastChannel: class extends EventTarget {
      constructor() { super(); this.sent = []; channels.push(this); }
      postMessage(message) { this.sent.push(message); }
    },
    async fetch(url, options) {
      requests.push({ url, options });
      if (responder) return responder(url, options);
      if (options.method === "POST") serverConsent = choice(JSON.parse(options.body));
      return { ok: true, json: async () => ({ consent: serverConsent }) };
    },
  };
  vm.runInNewContext(source, context);
  return {
    elements, requests, events, channels, timers, api: window.PortoBreakCookies,
    click(action) {
      document.dispatchEvent({ type: "click", target: buttons.find(b => b.dataset.cookieSave === action), preventDefault() {} });
    },
    setServerConsent(value) { serverConsent = value; },
    setResponder(callback) { responder = callback; },
    changeFromOtherTab() { channels[0].dispatchEvent({ type: "message", data: { type: "changed" } }); },
    visibilityRefresh() { document.dispatchEvent({ type: "visibilitychange" }); },
    expire() { now += 181 * 86400 * 1000; [...timers.values()].forEach(timer => timer.callback()); },
  };
}

const flush = () => new Promise(resolve => setImmediate(resolve));

test("first visit and legacy decisions never enable analytics", () => {
  for (const consent of [null, { preferences: true, external_maps: true, expires_at: initialTime / 1000 + 500 }]) {
    const h = harness(consent);
    assert.equal(h.api.allows("analytics"), false);
    assert.equal(h.api.allows("necessary"), true);
    assert.equal(h.elements.banner.hidden, false);
    h.api.openSettings();
    assert.equal(h.elements.analytics.checked, false);
    assert.equal(h.requests.length, 0);
  }
});

test("accept optional saves three true categories and announces analytics", async () => {
  const h = harness();
  h.click("accept");
  await flush();
  assert.deepEqual(JSON.parse(h.requests[0].options.body), { preferences: true, external_maps: true, analytics: true });
  assert.equal(h.api.allows("analytics"), true);
  assert.equal(h.elements.banner.hidden, true);
  assert.equal(h.events.at(-1).detail.analytics, true);
  assert.equal(h.channels[0].sent.length, 1);
});

test("analytics can be selected without maps or language", async () => {
  const h = harness();
  h.api.openSettings();
  h.elements.analytics.checked = true;
  h.click("selection");
  await flush();
  assert.deepEqual(JSON.parse(h.requests[0].options.body), { preferences: false, external_maps: false, analytics: true });
  assert.equal(h.api.allows("analytics"), true);
  assert.equal(h.api.allows("external_maps"), false);
  assert.equal(h.api.allows("preferences"), false);
});

test("reject optional stops all optional categories without requiring a reload", async () => {
  const h = harness(choice({ analytics: true, preferences: true, external_maps: true }));
  h.click("reject");
  await flush();
  assert.deepEqual(JSON.parse(h.requests[0].options.body), { preferences: false, external_maps: false, analytics: false });
  assert.equal(h.api.allows("analytics"), false);
  assert.equal(h.events.at(-1).detail.analytics, false);
});

test("consent expiry revokes analytics and resets an open settings checkbox", () => {
  const h = harness(choice({ analytics: true }));
  h.api.openSettings();
  assert.equal(h.elements.analytics.checked, true);
  h.expire();
  assert.equal(h.api.allows("analytics"), false);
  assert.equal(h.elements.analytics.checked, false);
  assert.equal(h.elements.banner.hidden, false);
  assert.equal(h.events.at(-1).detail, null);
});

test("cross-tab revocation refreshes permission and the open dialog", async () => {
  const h = harness(choice({ analytics: true }));
  h.api.openSettings();
  h.setServerConsent(choice({ analytics: false }));
  h.changeFromOtherTab();
  await flush();
  assert.equal(h.api.allows("analytics"), false);
  assert.equal(h.elements.analytics.checked, false);
  assert.equal(h.requests[0].options.cache, "no-store");
});

test("a stale refresh cannot restore analytics after a newer rejection", async () => {
  const accepted = choice({ analytics: true });
  const h = harness(accepted);
  let finishRefresh;
  h.setResponder((_url, options) => {
    if (options.method === "POST") return { ok: true, json: async () => ({ consent: choice() }) };
    return new Promise(resolve => { finishRefresh = resolve; });
  });
  h.visibilityRefresh();
  h.click("reject");
  await flush();
  assert.equal(h.api.allows("analytics"), false);
  finishRefresh({ ok: true, json: async () => ({ consent: accepted }) });
  await flush();
  assert.equal(h.api.allows("analytics"), false);
});

test("failed persistence does not silently grant analytics", async () => {
  const h = harness();
  h.setResponder(async () => ({ ok: false }));
  h.click("accept");
  await flush();
  assert.equal(h.api.allows("analytics"), false);
  assert.equal(h.elements["banner-error"].hidden, false);
  assert.equal(h.elements.analytics.disabled, false);
});
