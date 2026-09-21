"use strict";

// Exercise the production picker without a browser, property inventory or writes.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const test = require("node:test");
const source = fs.readFileSync(path.join(__dirname, "../static/js/booking_search_calendar.js"), "utf8");

function createHarness({ checkin = "2030-10-14", checkout = "2030-10-18", width = 1280, lang = "pt", now = "2030-09-18T12:00:00Z", dialogSupported = true } = {}) {
  let document;
  const pending = [];
  const dayRects = new Map();
  const calls = { fetch: 0, submit: 0, modal: 0, dropdown: 0 };
  class FakeEvent {
    constructor(type, options = {}) { this.type = type; this.cancelable = true; this.bubbles = false; this.defaultPrevented = false; Object.assign(this, options); }
    preventDefault() { if (this.cancelable) this.defaultPrevented = true; }
    stopPropagation() { this.stopped = true; }
    stopImmediatePropagation() { this.immediateStopped = true; this.stopped = true; }
  }
  class Element {
    constructor(tagName, attributes = {}) {
      this.tagName = tagName.toUpperCase(); this.children = []; this.parentElement = null;
      this.attributes = new Map(); this.dataset = {}; this.listeners = new Map(); this.style = {
        setProperty(name, value) { this[name] = value; }, removeProperty(name) { delete this[name]; },
      };
      this.value = ""; this.disabled = false; this.hidden = false; this.open = false;
      this.tabIndex = 0; this.scrollTop = 0; this._text = ""; this._className = "";
      this.classList = {
        add: (...names) => { this._className = [...new Set([...this._className.split(/\s+/).filter(Boolean), ...names])].join(" "); },
        remove: (...names) => { this._className = this._className.split(/\s+/).filter((name) => !names.includes(name)).join(" "); },
        contains: (name) => this._className.split(/\s+/).includes(name),
        toggle: (name, force) => {
          const add = force ?? !this.classList.contains(name);
          this.classList[add ? "add" : "remove"](name); return add;
        },
      };
      for (const [name, value] of Object.entries(attributes)) this.setAttribute(name, value);
    }
    get textContent() { return this._text + this.children.map((child) => child.textContent).join(""); }
    set textContent(value) { this.children.forEach((child) => { child.parentElement = null; }); this._text = String(value); this.children = []; }
    get innerHTML() { return this.textContent; }
    set innerHTML(value) { this.textContent = value; }
    get className() { return this._className; }
    set className(value) { this._className = String(value); }
    get parentNode() { return this.parentElement; }
    get firstChild() { return this.children[0] || null; }
    get firstElementChild() { return this.firstChild; }
    get childNodes() { return this.children; }
    get offsetWidth() { return this.getBoundingClientRect().width; }
    get offsetHeight() { return this.getBoundingClientRect().height; }
    getAttribute(name) {
      if (name === "class") return this.className;
      if (name.startsWith("data-")) return this.dataset[name.slice(5).replace(/-([a-z])/g, (_, letter) => letter.toUpperCase())] ?? null;
      return this.attributes.get(name) ?? null;
    }
    setAttribute(name, value) {
      this.attributes.set(name, String(value));
      if (name === "class") this.className = value;
      if (name === "id") this.id = value;
      if (name === "name") this.name = value;
      if (name === "tabindex") this.tabIndex = Number(value);
      if (name.startsWith("data-")) this.dataset[name.slice(5).replace(/-([a-z])/g, (_, letter) => letter.toUpperCase())] = String(value);
    }
    removeAttribute(name) {
      this.attributes.delete(name);
      if (name.startsWith("data-")) delete this.dataset[name.slice(5).replace(/-([a-z])/g, (_, letter) => letter.toUpperCase())];
    }
    hasAttribute(name) { return this.getAttribute(name) !== null; }
    appendChild(child) { child.parentElement = this; this.children.push(child); return child; }
    append(...children) { children.forEach((child) => this.appendChild(child)); }
    replaceChildren(...children) { this.children.forEach((child) => { child.parentElement = null; }); this.children = []; this._text = ""; this.append(...children); }
    removeChild(child) { this.children = this.children.filter((item) => item !== child); child.parentElement = null; }
    contains(target) { for (let node = target; node; node = node.parentElement) if (node === this) return true; return false; }
    matches(selector) {
      return selector.split(",").some((part) => {
        part = part.trim();
        const not = [...part.matchAll(/:not\(([^)]+)\)/g)];
        if (not.some((match) => this.matches(match[1]))) return false;
        part = part.replace(/:not\([^)]+\)/g, "");
        if (part.includes(":disabled") && !this.disabled) return false;
        part = part.replace(":disabled", "");
        const tag = part.match(/^[a-z]+/i);
        if (tag && this.tagName !== tag[0].toUpperCase()) return false;
        for (const match of part.matchAll(/\.([a-zA-Z0-9_-]+)/g)) if (!this.classList.contains(match[1])) return false;
        for (const match of part.matchAll(/#([a-zA-Z0-9_-]+)/g)) if (this.id !== match[1]) return false;
        for (const match of part.matchAll(/\[([^=\]\s]+)(?:=["']?([^\]"']*)["']?)?\]/g)) {
          if (match[1] === "disabled") { if (!this.disabled) return false; continue; }
          if (!this.hasAttribute(match[1])) return false;
          if (match[2] !== undefined && this.getAttribute(match[1]) !== match[2]) return false;
        }
        return true;
      });
    }
    querySelectorAll(selector) {
      const results = [];
      for (const child of this.children) {
        if (child.matches(selector)) results.push(child);
        results.push(...child.querySelectorAll(selector));
      }
      return results;
    }
    querySelector(selector) { return this.querySelectorAll(selector)[0] || null; }
    closest(selector) { for (let node = this; node; node = node.parentElement) if (node.matches(selector)) return node; return null; }
    addEventListener(type, listener, options = {}) {
      const listeners = this.listeners.get(type) || [];
      listeners.push({ listener, capture: options === true || options.capture }); this.listeners.set(type, listeners);
    }
    removeEventListener(type, listener) { this.listeners.set(type, (this.listeners.get(type) || []).filter((entry) => entry.listener !== listener)); }
    dispatchEvent(event) {
      if (!event.target) event.target = this;
      // A browser retains the original event path even if a click rebuilds the
      // calendar and detaches its target before the outside-click listener runs.
      const path = [this];
      if (event.bubbles) for (let ancestor = this.parentElement; ancestor; ancestor = ancestor.parentElement) path.push(ancestor);
      for (const current of path) {
        event.currentTarget = current;
        const listeners = [...(current.listeners.get(event.type) || [])].sort((a, b) => Number(!!b.capture) - Number(!!a.capture));
        for (const { listener } of listeners) { listener(event); if (event.immediateStopped) break; }
        if (event.stopped) break;
      }
      return !event.defaultPrevented;
    }
    fire(type, options = {}) { const event = new FakeEvent(type, options); this.dispatchEvent(event); flush(); return event; }
    click() { if (!this.disabled) this.fire("click", { bubbles: true }); }
    focus(options) { this.focusOptions = options; if (document.activeElement === this) return; document.activeElement = this; this.fire("focus"); }
    getBoundingClientRect() {
      if (this.rect) return this.rect;
      if (dayRects.has(this.dataset.date)) return dayRects.get(this.dataset.date);
      if (this.tagName === "DIALOG") return { left: 200, top: 160, right: 840, bottom: 660, width: 640, height: 500 };
      return { left: 200, top: 70, right: 360, bottom: 114, width: 160, height: 44 };
    }
    show() { this.open = true; calls.dropdown += 1; }
    showModal() { this.open = true; calls.modal += 1; }
    close() { this.open = false; this.fire("close"); }
    scrollIntoView() {}
    setCustomValidity(value) { this.validationMessage = value; }
    reportValidity() { return !this.validationMessage; }
  }
  function node(tag, attrs = {}, parent) { const element = new Element(tag, attrs); if (parent) parent.appendChild(element); return element; }
  document = node("document");
  const html = node("html", { lang }, document); document.documentElement = html; html.lang = lang;
  const body = node("body", {}, html); document.body = body; document.activeElement = body;
  const form = node("form", { "data-search-form": "" }, body);
  const fields = {};
  const toggles = {};
  const labels = {};
  for (const [name, value] of Object.entries({ checkin, checkout, adultos: "2", criancas: "1", bebes: "0", q: "Porto", lang, view: "map" })) {
    fields[name] = node("input", { name, type: ["checkin", "checkout"].includes(name) ? "date" : "text" }, form);
    fields[name].value = value;
  }
  for (const name of ["checkin", "checkout"]) {
    toggles[name] = node("button", { "data-search-date-toggle": name, "aria-expanded": "false", type: "button" }, form);
    labels[name] = node("span", { "data-search-date-value": "" }, toggles[name]);
  }
  const dialog = node("dialog", { "data-search-calendar": "", id: "booking-search-calendar" }, body);
  const scrollBody = node("div", { class: "booking-search-calendar-body" }, dialog);
  const controls = {};
  for (const name of ["title", "message", "months", "prev", "next", "close", "clear"]) {
    controls[name] = node(["prev", "next", "close", "clear"].includes(name) ? "button" : "div", { ["data-search-calendar-" + name]: "" }, name === "months" ? scrollBody : dialog);
  }
  const secondClose = node("button", { "data-search-calendar-close": "" }, dialog);
  const outside = node("input", { name: "outside" }, body);
  const config = node("script", { id: "booking-search-calendar-config" }, body);
  config.textContent = JSON.stringify({ lang, labels: {
    calendar_start: "Escolha a data de check-in.", calendar_pick_checkout: "Agora escolha a data de check-out.",
    checkout_after_checkin: "O check-out deve ser posterior ao check-in.", checkin: "Check-in", checkout: "Check-out", choose: "A escolher",
  } });
  document.getElementById = (id) => document.querySelector("#" + id);
  document.createElement = (tag) => new Element(tag);
  document.createDocumentFragment = () => new Element("fragment");
  const window = node("window"); window.innerWidth = width; window.innerHeight = 900; window.scrollX = 0; window.scrollY = 0;
  const media = node("media"); media.matches = width <= 720; window.matchMedia = () => media;
  if (dialogSupported) window.HTMLDialogElement = Element;
  else { dialog.show = undefined; dialog.showModal = undefined; }
  class FixedDate extends Date { constructor(...args) { super(...(args.length ? args : [now])); } static now() { return new Date(now).getTime(); } }
  const schedule = (fn) => { pending.push(fn); return pending.length; };
  function flush() { let count = 0; while (pending.length) { assert.ok(count++ < 100, "Scheduled callback loop"); pending.shift()(); } }
  const context = { document, window, Intl, Date: FixedDate, CustomEvent: FakeEvent, Event: FakeEvent, Node: Element,
    HTMLElement: Element, HTMLDialogElement: dialogSupported ? Element : undefined,
    requestAnimationFrame: schedule, cancelAnimationFrame() {}, queueMicrotask: schedule, setTimeout: schedule, clearTimeout() {},
    fetch: () => { calls.fetch += 1; throw new Error("Search calendar must not fetch availability"); },
  };
  Object.assign(window, { requestAnimationFrame: schedule, cancelAnimationFrame() {}, setTimeout: schedule, clearTimeout() {} });
  vm.runInNewContext(source, context, { filename: "booking_search_calendar.js" }); flush();
  function open(field = "checkin") { toggles[field].click(); assert.equal(dialog.open, true); }
  function day(iso) { return controls.months.querySelector('[data-date="' + iso + '"]'); }
  function select(iso) { assert.ok(day(iso), "Visible calendar date: " + iso); day(iso).click(); }
  function values() { return [fields.checkin.value, fields.checkout.value]; }
  function submit() { return form.fire("submit"); }
  return { document, window, form, fields, toggles, labels, dialog, controls, secondClose, outside, calls, media, scrollBody, dayRects, flush, open, day, select, values, submit, FakeEvent };
}

test("desktop opens one dropdown with two months; mobile opens a modal", () => {
  for (const [width, presentation] of [[1280, "dropdown"], [721, "dropdown"], [720, "modal"], [390, "modal"]]) {
    const h = createHarness({ width }); h.open();
    assert.equal(h.dialog.dataset.presentation, presentation);
    assert.equal(h.calls.modal, presentation === "modal" ? 1 : 0);
    assert.equal(h.calls.dropdown, presentation === "dropdown" ? 1 : 0);
    assert.equal(h.controls.months.querySelectorAll(".booking-calendar-month").length, 2);
    assert.equal(h.toggles.checkin.getAttribute("aria-expanded"), "true");
    assert.ok(h.form.hasAttribute("data-date-picker-enhanced"));
    assert.equal(h.calls.fetch, 0);
  }
});

test("a range is committed together only after checkout; no other search filters change", () => {
  const h = createHarness(); h.open(); h.select("2030-10-16");
  assert.deepEqual(h.values(), ["2030-10-14", "2030-10-18"]);
  assert.equal(h.dialog.open, true);
  h.select("2030-10-20");
  assert.deepEqual(h.values(), ["2030-10-16", "2030-10-20"]);
  assert.equal(h.dialog.open, false);
  assert.equal(h.document.activeElement, h.toggles.checkin);
  assert.deepEqual([h.fields.adultos.value, h.fields.criancas.value, h.fields.bebes.value, h.fields.q.value, h.fields.lang.value, h.fields.view.value], ["2", "1", "0", "Porto", "pt", "map"]);
  assert.equal(h.submit().defaultPrevented, false);
});

test("checkout editing preserves the check-in and rejects same-day or earlier checkout", () => {
  const h = createHarness(); h.open("checkout");
  for (const iso of ["2030-10-13", "2030-10-14"]) {
    h.select(iso);
    assert.deepEqual(h.values(), ["2030-10-14", "2030-10-18"]);
    assert.equal(h.dialog.open, true);
  }
  h.select("2030-10-15");
  assert.deepEqual(h.values(), ["2030-10-14", "2030-10-15"]);
  assert.equal(h.dialog.open, false);
});

test("close, native Escape cancellation and outside pointer discard an incomplete draft", () => {
  for (const close of [
    (h) => h.controls.close.click(),
    (h) => h.secondClose.click(),
    (h) => h.dialog.fire("cancel"),
    (h) => h.document.fire("click", { target: h.outside, clientX: 20, clientY: 20 }),
  ]) {
    const h = createHarness(); h.open(); h.select("2030-10-16"); close(h);
    assert.equal(h.dialog.open, false);
    assert.deepEqual(h.values(), ["2030-10-14", "2030-10-18"]);
    assert.equal(h.toggles.checkin.getAttribute("aria-expanded"), "false");
    h.open("checkout"); h.select("2030-10-19");
    assert.deepEqual(h.values(), ["2030-10-14", "2030-10-19"]);
  }
});

test("clear resets only both dates and closes without submitting", () => {
  const h = createHarness(); h.open(); h.controls.clear.click();
  assert.deepEqual(h.values(), ["", ""]);
  assert.equal(h.dialog.open, false);
  assert.equal(h.fields.q.value, "Porto");
  assert.equal(h.submit().defaultPrevented, false);
  assert.equal(h.calls.fetch, 0);
});

test("empty search is valid; incomplete, reversed and malformed ranges block busy handlers", () => {
  for (const [checkin, checkout] of [["2030-10-14", ""], ["", "2030-10-18"], ["2030-10-18", "2030-10-14"], ["2030-02-31", "2030-10-18"]]) {
    const h = createHarness({ checkin, checkout });
    let busy = false; h.form.addEventListener("submit", () => { busy = true; });
    assert.equal(h.submit().defaultPrevented, true);
    assert.equal(busy, false, "Invalid search must not activate existing loading state");
    assert.equal(h.dialog.open, true);
  }
  const empty = createHarness({ checkin: "", checkout: "" });
  assert.equal(empty.submit().defaultPrevented, false);
});

test("checkout without a start first asks for check-in; today works and past dates are disabled", () => {
  const h = createHarness({ checkin: "", checkout: "" }); h.open("checkout");
  assert.equal(h.controls.prev.disabled, true);
  assert.equal(h.day("2030-09-17").disabled, true);
  assert.equal(h.day("2030-09-18").disabled, false);
  h.select("2030-09-18"); assert.deepEqual(h.values(), ["", ""]);
  h.select("2030-09-19"); assert.deepEqual(h.values(), ["2030-09-18", "2030-09-19"]);
});

test("today follows Lisbon at midnight rather than the visitor timezone or UTC date", () => {
  const h = createHarness({ checkin: "", checkout: "", now: "2030-09-18T23:30:00Z" }); h.open();
  assert.equal(h.day("2030-09-18").disabled, true);
  assert.equal(h.day("2030-09-19").disabled, false);
});

test("range selection crosses month and year boundaries and includes leap day", () => {
  for (const [checkin, checkout] of [["2030-10-31", "2030-11-02"], ["2030-12-31", "2031-01-02"], ["2032-02-28", "2032-03-01"]]) {
    const h = createHarness({ checkin, checkout }); h.open();
    if (checkin.startsWith("2032")) assert.ok(h.day("2032-02-29"), "Leap day exists");
    h.select(checkin); h.select(checkout);
    assert.deepEqual(h.values(), [checkin, checkout]);
  }
});

test("previous navigation stops at this month; next advances the pair one month", () => {
  const h = createHarness({ checkin: "", checkout: "" }); h.open();
  assert.equal(h.controls.prev.disabled, true);
  assert.ok(h.day("2030-09-18")); assert.ok(h.day("2030-10-01"));
  h.controls.next.click();
  assert.equal(h.controls.prev.disabled, false);
  assert.equal(h.day("2030-09-18"), null); assert.ok(h.day("2030-11-01"));
  h.controls.prev.click();
  assert.equal(h.controls.prev.disabled, true);
});

test("dates have localized accessible labels and selected interval state in every language", () => {
  for (const [lang, month] of [["pt", "outubro"], ["en", "October"], ["es", "octubre"], ["fr", "octobre"]]) {
    const h = createHarness({ lang }); h.open();
    assert.match(h.day("2030-10-14").getAttribute("aria-label"), new RegExp(month, "i"));
    assert.match(h.day("2030-10-14").getAttribute("aria-label"), /2030/);
    for (const iso of ["2030-10-14", "2030-10-15", "2030-10-18"]) assert.equal(h.day(iso).getAttribute("aria-pressed"), "true");
    assert.equal(h.day("2030-10-20").getAttribute("aria-pressed"), "false");
  }
});

test("calendar keyboard navigation moves day, week and month without committing dates", () => {
  const h = createHarness(); h.open();
  const keyboard = (iso, key, expected) => {
    const day = h.day(iso); assert.ok(day); day.focus();
    assert.equal(day.fire("keydown", { key }).defaultPrevented, true);
    assert.equal(h.document.activeElement.dataset.date, expected);
  };
  keyboard("2030-10-14", "ArrowRight", "2030-10-15");
  keyboard("2030-10-15", "ArrowLeft", "2030-10-14");
  keyboard("2030-10-14", "ArrowDown", "2030-10-21");
  keyboard("2030-10-21", "ArrowUp", "2030-10-14");
  keyboard("2030-10-16", "Home", "2030-10-14");
  keyboard("2030-10-16", "End", "2030-10-20");
  keyboard("2030-10-14", "PageDown", "2030-11-14");
  keyboard("2030-11-14", "PageUp", "2030-10-14");
  assert.deepEqual(h.values(), ["2030-10-14", "2030-10-18"]);
});

test("map custom event and native input focus open the enhanced picker without native duplicate", () => {
  const h = createHarness();
  const event = h.form.fire("booking:search-dates-open", { detail: { field: "checkout" }, cancelable: true });
  assert.equal(event.defaultPrevented, true); assert.equal(h.dialog.open, true);
  h.controls.close.click(); h.fields.checkin.focus();
  assert.equal(h.dialog.open, true);
});

test("unsupported dialog API leaves the native GET inputs usable", () => {
  const h = createHarness({ dialogSupported: false });
  assert.equal(h.form.hasAttribute("data-date-picker-enhanced"), false);
  assert.deepEqual(h.values(), ["2030-10-14", "2030-10-18"]);
  assert.equal(h.submit().defaultPrevented, false);
});

test("mobile backdrop and Escape cancel without losing the previous committed range", () => {
  for (const close of [
    (h) => h.dialog.fire("click", { clientX: 0, clientY: 0 }),
    (h) => h.dialog.fire("keydown", { key: "Escape" }),
  ]) {
    const h = createHarness({ width: 390 }); h.open(); h.select("2030-10-16"); close(h);
    assert.equal(h.dialog.open, false);
    assert.deepEqual(h.values(), ["2030-10-14", "2030-10-18"]);
    assert.equal(h.document.activeElement, h.toggles.checkin);
  }
});

test("resizing between dropdown and modal preserves the uncommitted range", () => {
  const h = createHarness(); h.open(); h.select("2030-10-16");
  h.window.innerWidth = 390; h.window.fire("resize");
  assert.equal(h.dialog.dataset.presentation, "modal");
  assert.equal(h.dialog.open, true);
  assert.deepEqual(h.values(), ["2030-10-14", "2030-10-18"]);
  h.window.innerWidth = 1280; h.window.fire("resize");
  assert.equal(h.dialog.dataset.presentation, "dropdown");
  h.select("2030-10-20");
  assert.deepEqual(h.values(), ["2030-10-16", "2030-10-20"]);
});

test("keyboard reveals dates only inside the calendar scroller and month navigation resets it", () => {
  const h = createHarness({ width: 390 }); h.window.scrollY = 500; h.open();
  h.scrollBody.rect = { top: 200, bottom: 500, left: 10, right: 380, width: 370, height: 300 };
  h.dayRects.set("2030-10-15", { top: 600, bottom: 640, left: 10, right: 50, width: 40, height: 40 });
  h.day("2030-10-14").fire("keydown", { key: "ArrowRight" });
  assert.equal(h.scrollBody.scrollTop, 144);
  assert.equal(h.document.activeElement.dataset.date, "2030-10-15");
  assert.equal(h.document.activeElement.focusOptions.preventScroll, true);
  h.dayRects.set("2030-10-14", { top: 100, bottom: 140, left: 10, right: 50, width: 40, height: 40 });
  h.day("2030-10-15").fire("keydown", { key: "ArrowLeft" });
  assert.equal(h.scrollBody.scrollTop, 40);
  assert.equal(h.window.scrollY, 500, "The page behind the modal must not scroll");
  h.controls.next.click();
  assert.equal(h.scrollBody.scrollTop, 0);
  h.scrollBody.scrollTop = 120;
  h.controls.prev.click();
  assert.equal(h.scrollBody.scrollTop, 0);
  assert.equal(h.window.scrollY, 500);
});
