"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const html = fs.readFileSync(path.join(__dirname, "../templates/booking_portal/detail.html"), "utf8");
const marker = html.indexOf('var root = document.querySelector("[data-calendar]");');
assert.ok(marker >= 0, "calendar IIFE must exist");
const source = html.slice(html.lastIndexOf("(function () {", marker), html.indexOf("})();", marker) + 5);

class Event {
  constructor(type, options = {}) { this.type = type; Object.assign(this, options); this.defaultPrevented = false; }
  preventDefault() { this.defaultPrevented = true; }
}

class Element {
  constructor(tag) {
    this.tag = tag; this.children = []; this.parent = null; this.dataset = {};
    this.attributes = new Map(); this.selectors = new Map(); this.listeners = new Map();
    this.classList = { add() {} }; this.value = ""; this.textContent = "";
  }
  appendChild(child) { child.parent = this; this.children.push(child); return child; }
  set innerHTML(value) { this.children = []; }
  querySelector(selector) { return this.selectors.get(selector) || null; }
  setAttribute(name, value) { this.attributes.set(name, String(value)); }
  getAttribute(name) { return this.attributes.get(name) ?? null; }
  addEventListener(type, listener) {
    const callbacks = this.listeners.get(type) || [];
    callbacks.push(listener); this.listeners.set(type, callbacks);
  }
  dispatchEvent(event) {
    if (!event.target) event.target = this;
    event.currentTarget = this;
    for (const listener of this.listeners.get(event.type) || []) listener(event);
    if (event.bubbles && this.parent) this.parent.dispatchEvent(event);
    return !event.defaultPrevented;
  }
}

class FixedDate extends Date {
  constructor(...args) { super(...(args.length ? args : [2030, 8, 18])); }
}

async function harness(options = {}) {
  const root = new Element("calendar");
  const form = new Element("form");
  form.appendChild(root);
  root.dataset = {
    initialMonth: "2030-10-01", selectedCheckin: "2030-10-14", selectedCheckout: "2030-10-18",
    occupiedUrl: "", ...options.dates,
  };
  const months = root.appendChild(new Element("months"));
  const message = root.appendChild(new Element("message"));
  for (const [selector, element] of [
    ["[data-calendar-months]", months], ["[data-calendar-title]", new Element("title")],
    ["[data-calendar-message]", message], ["[data-calendar-prev]", new Element("previous")],
    ["[data-calendar-next]", new Element("next")],
  ]) root.selectors.set(selector, element);
  const checkin = form.appendChild(new Element("input"));
  const checkout = form.appendChild(new Element("input"));
  checkin.value = root.dataset.selectedCheckin;
  checkout.value = root.dataset.selectedCheckout;
  form.selectors.set("[data-checkin-input]", checkin);
  form.selectors.set("[data-checkout-input]", checkout);
  form.selectors.set("[data-update-button]", new Element("submit"));
  const payloads = {
    "booking-occupied-nights": options.occupied || [],
    "booking-calendar-policy": { min_nights: 2, ...options.policy },
    "booking-i18n": {},
  };
  const document = {
    documentElement: { lang: "pt" },
    querySelector: (selector) => selector === "[data-calendar]" ? root : form,
    getElementById: (id) => ({ textContent: JSON.stringify(payloads[id]) }),
    createElement: (tag) => new Element(tag),
  };
  const states = [];
  const required = [];
  form.addEventListener("booking:dates-changed", (event) => {
    assert.equal(checkin.value, event.detail.checkin, "check-in input must be current before emitting");
    assert.equal(checkout.value, event.detail.checkout, "check-out input must be current before emitting");
    states.push(JSON.parse(JSON.stringify(event.detail)));
  });
  form.addEventListener("booking:dates-required", (event) => required.push(event.detail.field));
  vm.runInNewContext(source, { document, Date: FixedDate, CustomEvent: Event, URLSearchParams, Promise, Set });
  await Promise.resolve();

  function findDay(iso, node = months) {
    if (node.dataset.date === iso) return node;
    for (const child of node.children) { const found = findDay(iso, child); if (found) return found; }
    return null;
  }
  function click(iso) {
    const day = findDay(iso);
    assert.ok(day, "day should be visible: " + iso);
    day.dispatchEvent(new Event("click"));
  }
  function edit(field, target = form) { target.dispatchEvent(new Event("booking:edit-date", { detail: { field }, bubbles: true })); }
  function finish(target = form) { target.dispatchEvent(new Event("booking:finish-date-edit", { bubbles: true })); }
  function values() { return [checkin.value, checkout.value]; }
  function state() { return states[states.length - 1]; }
  return { root, form, message, states, required, findDay, click, edit, finish, values, state };
}

const cases = [
  ["checkout editing preserves check-in and existing dates until a valid day is clicked", async () => {
    const h = await harness();
    h.root.parent = null; // The mobile UI moves the actual calendar into its dialog.
    h.edit("checkout", h.root);
    assert.deepEqual(h.values(), ["2030-10-14", "2030-10-18"]);
    assert.equal(h.root.dataset.editingDate, "checkout");
    h.click("2030-10-20");
    assert.deepEqual(h.values(), ["2030-10-14", "2030-10-20"]);
    assert.equal(h.state().valid, true);
    assert.equal(h.root.dataset.editingDate, "");
  }],
  ["check-in editing only resets the interval after a valid click", async () => {
    const h = await harness();
    h.edit("checkin");
    assert.deepEqual(h.values(), ["2030-10-14", "2030-10-18"]);
    h.click("2030-10-16");
    assert.deepEqual(h.values(), ["2030-10-16", ""]);
    assert.equal(h.state().complete, false);
    assert.equal(h.state().valid, false);
    assert.equal(h.root.dataset.editingDate, "checkout");
    h.click("2030-10-19");
    assert.deepEqual(h.values(), ["2030-10-16", "2030-10-19"]);
    assert.equal(h.state().valid, true);
  }],
  ["minimum nights and checkout before check-in cannot replace an existing valid interval", async () => {
    const h = await harness();
    h.edit("checkout");
    for (const invalid of ["2030-10-13", "2030-10-14", "2030-10-15"]) {
      h.click(invalid);
      assert.deepEqual(h.values(), ["2030-10-14", "2030-10-18"]);
      assert.equal(h.state().valid, false);
      assert.equal(h.form.dataset.datesValid, "0");
    }
    h.click("2030-10-16");
    assert.equal(h.state().valid, true);
  }],
  ["blocked check-in and checkout restrictions remain enforced", async () => {
    const h = await harness({ policy: { blocked_checkin: ["2030-10-13"], blocked_checkout: ["2030-10-19"] } });
    h.edit("checkin"); h.click("2030-10-13");
    assert.deepEqual(h.values(), ["2030-10-14", "2030-10-18"]);
    assert.equal(h.state().valid, false);
    h.edit("checkout"); h.click("2030-10-19");
    assert.deepEqual(h.values(), ["2030-10-14", "2030-10-18"]);
    assert.equal(h.state().valid, false);
    h.click("2030-10-20");
    assert.equal(h.state().valid, true);
  }],
  ["occupied nights reject crossing but allow checkout on another stay's arrival day", async () => {
    const h = await harness({ occupied: ["2030-10-19"] });
    h.edit("checkout"); h.click("2030-10-20");
    assert.deepEqual(h.values(), ["2030-10-14", "2030-10-18"]);
    assert.equal(h.state().valid, false);
    h.click("2030-10-19");
    assert.deepEqual(h.values(), ["2030-10-14", "2030-10-19"]);
    assert.equal(h.state().valid, true);
  }],
  ["missing dates request the correct editor and checkout without check-in starts at check-in", async () => {
    const h = await harness({ dates: { selectedCheckin: "", selectedCheckout: "" } });
    const submit = new Event("submit"); h.form.dispatchEvent(submit);
    assert.equal(submit.defaultPrevented, true);
    assert.deepEqual(h.required, ["checkin"]);
    h.edit("checkout");
    assert.equal(h.root.dataset.editingDate, "checkin");
    h.click("2030-10-14");
    const incomplete = new Event("submit"); h.form.dispatchEvent(incomplete);
    assert.equal(incomplete.defaultPrevented, true);
    assert.deepEqual(h.required, ["checkin", "checkout"]);
    h.click("2030-10-18");
    assert.equal(h.state().valid, true);
  }],
  ["finishing an editor leaves dates and validity untouched and restores desktop selection", async () => {
    for (const targetName of ["form", "root"]) {
      const h = await harness();
      h.edit("checkout");
      const before = [h.values(), h.form.dataset.datesValid, h.states.length];
      h.finish(h[targetName]);
      assert.equal(h.root.dataset.editingDate, "");
      assert.deepEqual([h.values(), h.form.dataset.datesValid, h.states.length], before);
      h.click("2030-10-20");
      assert.deepEqual(h.values(), ["2030-10-20", ""]);
      h.click("2030-10-23");
      assert.deepEqual(h.values(), ["2030-10-20", "2030-10-23"]);
      assert.equal(h.state().valid, true);
    }
  }],
  ["initial normalization emits incomplete invalid state after syncing the hidden dates", async () => {
    const h = await harness({ dates: { selectedCheckout: "2030-10-15" } });
    assert.deepEqual(h.values(), ["2030-10-14", ""]);
    assert.equal(h.state().complete, false);
    assert.equal(h.state().valid, false);
    assert.equal(h.form.dataset.datesValid, "0");
  }],
  ["calendar days expose full localized dates and selected range state", async () => {
    const h = await harness();
    const selected = h.findDay("2030-10-14");
    assert.match(selected.getAttribute("aria-label"), /14.*outubro.*2030/i);
    assert.equal(selected.getAttribute("aria-pressed"), "true");
    assert.equal(h.findDay("2030-10-15").getAttribute("aria-pressed"), "true");
    assert.equal(h.findDay("2030-10-18").getAttribute("aria-pressed"), "true");
    assert.equal(h.findDay("2030-10-20").getAttribute("aria-pressed"), "false");
  }],
];

(async function () {
  let failures = 0;
  for (const [name, test] of cases) {
    try { await test(); console.log("PASS " + name); }
    catch (error) { failures += 1; console.error("FAIL " + name + "\n" + error.stack); }
  }
  console.log(`${cases.length - failures}/${cases.length} calendar behavior checks passed`);
  if (failures) process.exitCode = 1;
})();
