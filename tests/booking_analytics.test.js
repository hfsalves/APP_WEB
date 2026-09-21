"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const test = require("node:test");

const source = fs.readFileSync(path.join(__dirname, "../static/js/booking_analytics.js"), "utf8");

async function settle() {
  for (let index = 0; index < 12; index++) await Promise.resolve();
}

async function harness(options = {}) {
  let time = 0;
  let consent = Boolean(options.consent);
  let nextId = 0;
  let uuidCalls = 0;
  const timers = new Map();
  const requests = [];
  const windowListeners = new Map();
  const documentListeners = new Map();
  function listen(collection, type, callback) {
    const callbacks = collection.get(type) || [];
    callbacks.push(callback);
    collection.set(type, callbacks);
  }
  function dispatch(collection, type, properties = {}) {
    for (const callback of collection.get(type) || []) callback({ type, ...properties });
  }
  const config = {
    enabled: true, endpoint: "/reservas/analitica/eventos", context: "signed-context",
    ...options.config,
  };
  const document = {
    visibilityState: options.hidden ? "hidden" : "visible",
    getElementById: () => ({ textContent: JSON.stringify(config) }),
    addEventListener: (type, callback) => listen(documentListeners, type, callback),
  };
  const window = {
    performance: { now: () => time },
    crypto: { randomUUID: () => `00000000-0000-4000-8000-${String(++uuidCalls).padStart(12, "0")}` },
    AbortController,
    PortoBreakCookies: { allows: category => category === "analytics" && consent },
    addEventListener: (type, callback) => listen(windowListeners, type, callback),
    setInterval: (callback, delay) => {
      const id = ++nextId;
      timers.set(id, { callback, delay, at: time + delay });
      return id;
    },
    clearInterval: id => timers.delete(id),
    fetch: (url, init) => {
      const request = { url, init, payload: JSON.parse(init.body) };
      requests.push(request);
      return options.fetch ? options.fetch(request, requests.length) : Promise.resolve({ ok: true, status: 200 });
    },
  };
  vm.runInNewContext(source, { window, document, JSON, Boolean, Math, Error });
  await settle();
  return {
    requests, timers, uuids: () => uuidCalls,
    async consent(value) {
      consent = value;
      dispatch(windowListeners, "portobreak:consent-changed");
      await settle();
    },
    async advance(milliseconds) {
      const end = time + milliseconds;
      while (true) {
        const due = [...timers].filter(([, timer]) => timer.at <= end).sort((a, b) => a[1].at - b[1].at)[0];
        if (!due) break;
        const [id, timer] = due;
        time = timer.at;
        timer.at += timer.delay;
        if (timers.has(id)) timer.callback();
        await settle();
      }
      time = end;
      await settle();
    },
    async visibility(value) {
      document.visibilityState = value;
      dispatch(documentListeners, "visibilitychange");
      await settle();
    },
    async event(type, properties) {
      dispatch(windowListeners, type, properties);
      await settle();
    },
  };
}

test("no identifiers, requests or timers exist before analytics consent", async () => {
  const h = await harness();
  await h.advance(120000);
  await h.event("scroll");
  await h.visibility("hidden");
  await h.visibility("visible");
  assert.equal(h.uuids(), 0);
  assert.equal(h.requests.length, 0);
  assert.equal(h.timers.size, 0);
});

test("disabled analytics and foreign endpoints are inert even with consent", async () => {
  for (const config of [{ enabled: false }, { endpoint: "https://example.com/collect" }]) {
    const h = await harness({ consent: true, config });
    assert.equal(h.requests.length, 0);
    assert.equal(h.uuids(), 0);
    assert.equal(h.timers.size, 0);
  }
});

test("grant starts first-party collection, withdrawal stops it, regrant uses a new page", async () => {
  const h = await harness();
  await h.consent(true);
  assert.equal(h.requests.length, 1);
  const first = h.requests[0];
  assert.equal(first.payload.type, "pageview");
  assert.deepEqual(Object.keys(first.payload).sort(), ["context", "page_id", "type"]);
  assert.equal(first.payload.context, "signed-context");
  assert.equal(first.init.credentials, "same-origin");
  assert.equal(first.init.headers["Content-Type"], "application/json");
  await h.advance(30000);
  await h.consent(false);
  const before = h.requests.length;
  assert.equal(h.timers.size, 0);
  await h.advance(120000);
  await h.event("scroll");
  assert.equal(h.requests.length, before);
  await h.consent(true);
  assert.equal(h.requests.at(-1).payload.type, "pageview");
  assert.notEqual(h.requests.at(-1).payload.page_id, first.payload.page_id);
});

test("withdrawal aborts an in-flight request and ignores its late response", async () => {
  let finishFirst;
  const h = await harness({ consent: true, fetch: (request, index) => {
    if (index === 1) return new Promise(resolve => { finishFirst = resolve; });
    return Promise.resolve({ ok: true, status: 200 });
  } });
  await h.advance(30000);
  assert.equal(h.requests.length, 1, "no engagement can overlap the pageview");
  await h.consent(false);
  assert.equal(h.requests[0].init.signal.aborted, true);
  await h.consent(true);
  finishFirst({ ok: true, status: 200 });
  await settle();
  assert.deepEqual(h.requests.map(request => request.payload.type), ["pageview", "pageview"]);
  await h.advance(30000);
  assert.equal(h.requests.at(-1).payload.page_id, h.requests[1].payload.page_id);
});

test("engagement is cumulative, idempotent and stops after sixty seconds without interaction", async () => {
  const h = await harness({ consent: true });
  await h.advance(90000);
  assert.deepEqual(h.requests.slice(1).map(request => request.payload.active_seconds), [30, 60]);
  assert.ok(h.requests.every(request => request.payload.page_id === h.requests[0].payload.page_id));
  await h.event("scroll");
  await h.advance(30000);
  assert.equal(h.requests.at(-1).payload.active_seconds, 65);
  await h.advance(5000);
  assert.equal(h.requests.at(-1).payload.active_seconds, 95);
  await h.visibility("hidden");
  await h.event("pagehide", { persisted: true });
  const count = h.requests.length;
  await h.event("pagehide", { persisted: true });
  assert.equal(h.requests.length, count, "the same cumulative total is never resent after acknowledgement");
});

test("hidden time is excluded and a hidden page is not initially counted", async () => {
  const hidden = await harness({ consent: true, hidden: true });
  await hidden.advance(120000);
  assert.equal(hidden.requests.length, 0);
  assert.equal(hidden.timers.size, 0);
  await hidden.visibility("visible");
  assert.equal(hidden.requests.length, 1);

  const h = await harness({ consent: true });
  await h.advance(20000);
  await h.visibility("hidden");
  assert.equal(h.requests.at(-1).payload.active_seconds, 20);
  assert.equal(h.requests.at(-1).init.keepalive, true);
  await h.advance(120000);
  assert.equal(h.requests.length, 2);
  await h.visibility("visible");
  await h.advance(30000);
  await h.visibility("hidden");
  assert.equal(h.requests.at(-1).payload.active_seconds, 50);
});

test("BFCache restores the same page without counting time spent away", async () => {
  const h = await harness({ consent: true });
  await h.advance(12000);
  await h.event("pagehide", { persisted: true });
  assert.equal(h.requests.at(-1).payload.active_seconds, 12);
  await h.advance(120000);
  await h.event("pageshow", { persisted: true });
  await h.advance(30000);
  assert.equal(h.requests.filter(request => request.payload.type === "pageview").length, 1);
  await h.event("pagehide", { persisted: true });
  assert.equal(h.requests.at(-1).payload.active_seconds, 42);
});

test("pageview retries keep the same id and do not overlap", async () => {
  const h = await harness({ consent: true, fetch: (_request, index) =>
    Promise.resolve({ ok: index > 1, status: index === 1 ? 503 : 200 }) });
  await h.advance(10000);
  assert.equal(h.requests.length, 1);
  await h.advance(5000);
  assert.equal(h.requests[1].payload.type, "pageview");
  assert.equal(h.requests[1].payload.page_id, h.requests[0].payload.page_id);
});

test("400/403 stop collection and repeated 409 permits only one recovery", async () => {
  for (const status of [400, 403]) {
    const denied = await harness({ consent: true, fetch: () => Promise.resolve({ ok: false, status }) });
    await denied.advance(120000);
    await denied.consent(true);
    assert.equal(denied.requests.length, 1);
    assert.equal(denied.timers.size, 0);
  }

  const expired = await harness({ consent: true, fetch: () => Promise.resolve({ ok: false, status: 409 }) });
  await expired.advance(120000);
  assert.equal(expired.requests.length, 2);
  assert.notEqual(expired.requests[0].payload.page_id, expired.requests[1].payload.page_id);
  assert.equal(expired.timers.size, 0);
});

test("409 received on the final hidden flush waits for foreground before recovering", async () => {
  const h = await harness({ consent: true, fetch: (_request, index) =>
    Promise.resolve({ ok: index !== 2, status: index === 2 ? 409 : 200 }) });
  await h.advance(10000);
  await h.visibility("hidden");
  assert.equal(h.requests.length, 2);
  assert.equal(h.timers.size, 0);
  await h.advance(120000);
  assert.equal(h.requests.length, 2);
  await h.visibility("visible");
  assert.equal(h.requests[2].payload.type, "pageview");
  assert.notEqual(h.requests[2].payload.page_id, h.requests[0].payload.page_id);
  await h.advance(30000);
  assert.equal(h.requests.at(-1).payload.active_seconds, 30);
});

test("a successfully renewed session can recover from a later independent expiry", async () => {
  let heartbeats = 0;
  const h = await harness({ consent: true, fetch: request => {
    if (request.payload.type === "engagement") {
      heartbeats++;
      if ([1, 3].includes(heartbeats)) return Promise.resolve({ ok: false, status: 409 });
    }
    return Promise.resolve({ ok: true, status: 200 });
  } });
  await h.advance(90000);
  assert.equal(h.requests.filter(request => request.payload.type === "pageview").length, 3);
  assert.equal(h.timers.size, 1);
});

test("analytics partial is included after consent UI and uses escaped JSON configuration", () => {
  const footer = fs.readFileSync(path.join(__dirname, "../templates/booking_portal/_footer.html"), "utf8");
  const partial = fs.readFileSync(path.join(__dirname, "../templates/booking_portal/_analytics.html"), "utf8");
  assert.ok(footer.indexOf("_cookie_preferences.html") < footer.indexOf("_analytics.html"));
  assert.match(partial, /booking_analytics is defined and booking_analytics\.enabled/);
  assert.match(partial, /booking_analytics\|tojson/);
  assert.match(partial, /script defer/);
});
