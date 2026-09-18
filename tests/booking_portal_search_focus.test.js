"use strict";

// Exercise the production event handlers in isolation. In particular, WebKit can
// expose body as activeElement while focusout already identifies the next input.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const source = fs.readFileSync(
  path.join(__dirname, "../static/js/booking_mobile_search.js"), "utf8"
);

function createHarness() {
  let document;
  const microtasks = [];

  class Element {
    constructor(name) {
      this.name = name;
      this.parent = null;
      this.listeners = new Map();
      this.attributes = new Map();
      this.selectors = new Map();
      this.dataset = {};
      this.value = "";
      this.textContent = "";
    }
    add(child) { child.parent = this; return child; }
    contains(target) {
      for (let node = target; node; node = node.parent) if (node === this) return true;
      return false;
    }
    querySelector(selector) { return this.selectors.get(selector) || null; }
    querySelectorAll(selector) { return this.selectors.get(selector) || []; }
    setAttribute(name, value) { this.attributes.set(name, String(value)); }
    getAttribute(name) { return this.attributes.get(name) ?? null; }
    removeAttribute(name) { this.attributes.delete(name); }
    hasAttribute(name) { return this.attributes.has(name); }
    focus() { document.activeElement = this; }
    addEventListener(type, listener) {
      const callbacks = this.listeners.get(type) || [];
      callbacks.push(listener);
      this.listeners.set(type, callbacks);
    }
    fire(type, properties = {}) {
      const event = {
        target: this,
        relatedTarget: null,
        defaultPrevented: false,
        preventDefault() { this.defaultPrevented = true; },
        ...properties,
      };
      for (const listener of this.listeners.get(type) || []) listener(event);
      return event;
    }
  }

  document = new Element("document");
  const body = document.add(new Element("body"));
  document.activeElement = body;
  const form = body.add(new Element("form"));
  const party = form.add(new Element("party"));
  const toggle = party.add(new Element("toggle"));
  const fields = party.add(new Element("fields"));
  const count = toggle.add(new Element("count"));
  count.dataset.emptyLabel = "Hóspedes";
  const closeButton = fields.add(new Element("close"));
  const label = fields.add(new Element("label"));
  const inputs = ["adultos", "criancas", "bebes"].map((name) => fields.add(new Element(name)));
  inputs[0].value = "2";
  inputs[1].value = inputs[2].value = "0";
  const outside = form.add(new Element("location-input"));
  document.selectors.set("[data-search-form]", form);
  form.selectors.set("[data-search-party]", party);
  party.selectors.set("[data-party-toggle]", toggle);
  party.selectors.set(".booking-search-party-fields", fields);
  party.selectors.set("[data-party-count]", count);
  party.selectors.set("[data-party-close]", closeButton);
  fields.selectors.set("input", inputs);

  vm.runInNewContext(source, {
    document, window: new Element("window"), Node: Element,
    queueMicrotask: (callback) => microtasks.push(callback),
    setTimeout: (callback) => microtasks.push(callback),
  }, { filename: "booking_mobile_search.js" });

  function flushMicrotasks() {
    while (microtasks.length) microtasks.shift()();
  }
  function open() {
    toggle.focus();
    toggle.fire("click");
    assert.equal(party.hasAttribute("data-open"), true);
    assert.equal(toggle.getAttribute("aria-expanded"), "true");
  }
  function assertOpen() {
    assert.equal(party.hasAttribute("data-open"), true, "the guest picker must remain open");
    assert.equal(toggle.getAttribute("aria-expanded"), "true");
  }
  function assertClosed() {
    assert.equal(party.hasAttribute("data-open"), false, "the guest picker must close");
    assert.equal(toggle.getAttribute("aria-expanded"), "false");
  }
  return {
    document, body, form, party, toggle, fields, count, inputs, outside, label,
    closeButton, flushMicrotasks, open, assertOpen, assertClosed,
  };
}

const cases = [
  ["focusout to a guest input stays open while activeElement is temporarily body", () => {
    const h = createHarness();
    h.open();
    h.document.activeElement = h.body;
    h.party.fire("focusout", { target: h.toggle, relatedTarget: h.inputs[0] });
    h.flushMicrotasks();
    h.assertOpen();
    h.inputs[0].focus();
    h.document.fire("click", { target: h.inputs[0] });
    h.inputs[0].value = "4";
    h.inputs[0].fire("input");
    h.assertOpen();
    assert.equal(h.document.activeElement, h.inputs[0]);
    assert.equal(h.count.textContent, "4");
  }],
  ["focusout without a known destination does not close or steal focus", () => {
    const h = createHarness();
    h.open();
    h.document.activeElement = h.body;
    h.party.fire("focusout", { target: h.toggle, relatedTarget: null });
    h.flushMicrotasks();
    h.assertOpen();
    assert.equal(h.document.activeElement, h.body);
  }],
  ["clicks on labels, panel whitespace and guest inputs stay inside the picker", () => {
    const h = createHarness();
    h.open();
    for (const target of [h.label, h.fields, ...h.inputs]) {
      h.document.fire("click", { target });
      h.flushMicrotasks();
      h.assertOpen();
    }
  }],
  ["click outside closes without taking focus from the clicked field", () => {
    const h = createHarness();
    h.open();
    h.outside.focus();
    h.document.fire("click", { target: h.outside });
    h.flushMicrotasks();
    h.assertClosed();
    assert.equal(h.document.activeElement, h.outside);
  }],
  ["Escape from a guest input closes and restores focus to the toggle", () => {
    const h = createHarness();
    h.open();
    h.inputs[1].focus();
    const event = h.party.fire("keydown", { target: h.inputs[1], key: "Escape" });
    h.assertClosed();
    assert.equal(event.defaultPrevented, true);
    assert.equal(h.document.activeElement, h.toggle);
  }],
  ["Tab between guest fields remains open and Tab to an outside field closes", () => {
    const h = createHarness();
    h.open();
    const targets = [...h.inputs, h.closeButton];
    let previous = h.toggle;
    for (const destination of targets) {
      h.document.activeElement = h.body;
      h.party.fire("focusout", { target: previous, relatedTarget: destination });
      h.flushMicrotasks();
      h.assertOpen();
      destination.focus();
      previous = destination;
    }
    h.document.activeElement = h.body;
    h.party.fire("focusout", { target: previous, relatedTarget: h.outside });
    h.flushMicrotasks();
    h.assertClosed();
    h.outside.focus();
    assert.equal(h.document.activeElement, h.outside);
  }],
  ["explicit close restores focus and native invalid guest input reopens the picker", () => {
    const h = createHarness();
    h.open();
    h.closeButton.fire("click");
    h.assertClosed();
    assert.equal(h.document.activeElement, h.toggle);
    h.form.fire("invalid", { target: h.inputs[0] });
    h.assertOpen();
  }],
];

let failures = 0;
for (const [name, test] of cases) {
  try {
    test();
    console.log("PASS " + name);
  } catch (error) {
    failures += 1;
    console.error("FAIL " + name + "\n" + error.stack);
  }
}
console.log(`${cases.length - failures}/${cases.length} guest-picker behavior checks passed`);
if (failures) process.exitCode = 1;
