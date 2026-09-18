"use strict";

// Run the production controller with a small DOM/Leaflet model. All fetches and
// tiles are fake; deferred responses deliberately ignore abort to expose races.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const source = fs.readFileSync(path.join(__dirname, "../static/js/booking_catalog_map.js"), "utf8");

const INITIAL_URL = "https://booking.example/reservas?lang=en&checkin=2035-10-14&checkout=2035-10-17&adultos=2&criancas=1&bebes=1&q=Porto%20%26%20Centro&page=4#stays";
const labels = {
  view_map: "View map", view_list: "View list", loading: "Loading map",
  loading_quote: "Loading price", error: "Map unavailable", tile_error: "Tiles unavailable",
  quote_error: "Price unavailable", retry: "Try again", close: "Close popup",
  group_count: "{count} properties", legend_available: "Matches", legend_unavailable: "Unavailable",
  legend_all: "Property", match_count: "{count} of {total} match", all_stays: "{count} properties",
  missing_coordinates: "{count} without location", empty: "No properties", no_matches: "No matching properties",
  back_to_group: "Back to properties", view_stay: "View property", book: "Book",
  choose_dates: "Choose dates", simulation: "Price estimate", total: "Total", estimate: "Estimate only",
  from_price: "From", per_night: "per night", no_price: "Ask for price", unavailable: "Unavailable",
};

function rectangle(left, top, width, height) {
  return { left, top, width, height, right: left + width, bottom: top + height };
}

function createHarness({ allowed = false, view = "list", width = 375, height = 667, canvasBounds, popupBounds } = {}) {
  let document;
  let consent = allowed;
  const fetches = [];
  const maps = [];
  const allMarkers = [];
  const tiles = [];
  const popups = [];
  const settingsCalls = [];

  class Events {
    constructor() { this.listeners = new Map(); }
    addEventListener(type, handler) {
      if (!this.listeners.has(type)) this.listeners.set(type, []);
      this.listeners.get(type).push(handler);
    }
    on(type, handler) { this.addEventListener(type, handler); return this; }
    fire(type, fields = {}) {
      const event = {
        target: this,
        preventDefault() { this.defaultPrevented = true; },
        stopPropagation() { this.propagationStopped = true; },
        ...fields,
      };
      for (const handler of this.listeners.get(type) || []) handler(event);
      return event;
    }
  }

  class Element extends Events {
    constructor(tag = "div") {
      super();
      this.tagName = tag.toUpperCase();
      this.children = [];
      this.parentNode = null;
      this.attributes = new Map();
      this.selectors = new Map();
      this.dataset = {};
      this.className = "";
      this.hidden = false;
      this.disabled = false;
      this.isConnected = true;
      this.value = "";
      this._text = "";
      this.classList = {
        contains: name => this.className.split(/\s+/).includes(name),
        add: name => { if (!this.classList.contains(name)) this.className += " " + name; },
        remove: name => { this.className = this.className.split(/\s+/).filter(value => value !== name).join(" "); },
      };
    }
    get textContent() { return this._text + this.children.map(node => node.textContent).join(""); }
    set textContent(value) { this._text = String(value); this.children = []; }
    appendChild(node) { node.parentNode = this; this.children.push(node); return node; }
    append(...nodes) { nodes.forEach(node => this.appendChild(node)); }
    replaceChildren(...nodes) { this._text = ""; this.children = []; this.append(...nodes); }
    remove() {
      if (this.parentNode) this.parentNode.children = this.parentNode.children.filter(node => node !== this);
      this.parentNode = null;
    }
    setAttribute(name, value) { this.attributes.set(name, String(value)); }
    getAttribute(name) { return this.attributes.get(name) ?? null; }
    removeAttribute(name) { this.attributes.delete(name); }
    hasAttribute(name) { return this.attributes.has(name); }
    matches(selector) {
      if (selector.includes(",")) return selector.split(",").some(value => this.matches(value.trim()));
      if (selector.endsWith(":not([disabled])")) return !this.disabled && this.matches(selector.replace(":not([disabled])", ""));
      if (selector.startsWith(".")) return this.classList.contains(selector.slice(1));
      const attr = selector.match(/^\[([^=\]]+)(?:="([^"]*)")?\]$/);
      if (attr) {
        const value = this.getAttribute(attr[1]) ?? this[attr[1]];
        return attr[2] === undefined ? this.hasAttribute(attr[1]) : value === attr[2];
      }
      return this.tagName.toLowerCase() === selector.toLowerCase();
    }
    querySelectorAll(selector) {
      if (this.selectors.has(selector)) {
        const value = this.selectors.get(selector);
        return Array.isArray(value) ? value : [value];
      }
      return this.children.flatMap(node => [...(node.matches(selector) ? [node] : []), ...node.querySelectorAll(selector)]);
    }
    querySelector(selector) { return this.querySelectorAll(selector)[0] || null; }
    focus() { document.activeElement = this; }
    scrollIntoView() { this.scrolled = true; }
    getBoundingClientRect() { return this.rect || rectangle(0, 0, width, height); }
  }

  document = new Element("document");
  document.createElement = tag => new Element(tag);
  document.activeElement = null;
  const config = new Element("script");
  config.textContent = JSON.stringify({ view, lang: "en", labels, data_url: "/reservas/mapa-dados?lang=en&q=Porto" });
  document.getElementById = id => id === "booking-catalog-map-config" ? config : null;
  const root = new Element();
  const toggle = new Element("button");
  const toggleLabel = new Element("span");
  const form = new Element("form");
  const checkin = form.appendChild(new Element("input"));
  checkin.name = "checkin";
  const list = new Element();
  const pagination = new Element("nav");
  const count = new Element("p");
  count.textContent = "100 stays on page 4";
  const names = ["consent", "settings", "stage", "canvas", "feedback", "status", "retry", "warning", "missing"];
  const nodes = {};
  for (const name of names) {
    nodes[name] = root.appendChild(new Element(["settings", "retry"].includes(name) ? "button" : "div"));
    nodes[name].hidden = ["stage", "feedback", "retry", "warning", "missing"].includes(name);
    root.selectors.set(`[data-catalog-map-${name}]`, nodes[name]);
  }
  nodes.canvas.rect = canvasBounds || rectangle(0, 0, width, height);
  nodes.availableLegend = root.appendChild(new Element("span"));
  nodes.unavailableLegend = root.appendChild(new Element("span"));
  root.selectors.set("[data-map-available-label]", nodes.availableLegend);
  root.selectors.set("[data-map-unavailable-legend]", nodes.unavailableLegend);
  for (const [selector, value] of [
    ["[data-catalog-map]", root], ["[data-catalog-view-toggle]", toggle],
    ["[data-catalog-view-label]", toggleLabel], ["[data-search-form]", form],
    ["[data-catalog-list]", [list, pagination]], ["[data-catalog-count]", count],
  ]) document.selectors.set(selector, value);

  const window = new Events();
  window.location = new URL(INITIAL_URL);
  if (view === "map") window.location.searchParams.set("view", "map");
  window.innerWidth = width;
  window.innerHeight = height;
  window.history = {
    state: { from: "catalog" },
    pushState(state, _title, url) { this.state = state; window.location = new URL(url, window.location); },
  };
  window.PortoBreakCookies = {
    allows: category => category === "external_maps" && consent,
    openMapsSettings: () => settingsCalls.push(true),
  };

  const L = {
    map(canvas, options) {
      const map = new Events();
      map.canvas = canvas;
      map.options = options;
      map.setView = (center, zoom) => { map.center = center; map.zoom = zoom; return map; };
      map.fitBounds = (bounds, options) => { map.center = bounds[0]; map.zoom = options.maxZoom; map.bounds = bounds; return map; };
      map.getCenter = () => map.center;
      map.getZoom = () => map.zoom;
      map.stops = 0;
      map.pans = [];
      map.stop = () => { map.stops += 1; return map; };
      map.panBy = (offset, options) => {
        map.pans.push({ offset, options });
        if (map.popup) {
          const bounds = map.popup.element.getBoundingClientRect();
          map.popup.element.rect = rectangle(bounds.left - offset[0], bounds.top - offset[1], bounds.width, bounds.height);
        }
        return map;
      };
      map.invalidateSize = () => {};
      map.closePopup = () => { const popup = map.popup; map.popup = null; if (popup) map.fire("popupclose", { popup }); return map; };
      map.remove = () => { map.removed = true; map.closePopup(); };
      maps.push(map);
      return map;
    },
    layerGroup() {
      const group = { markers: [], addTo(map) { this.map = map; return this; }, clearLayers() { this.markers = []; } };
      return group;
    },
    tileLayer(url, options) {
      const tile = new Events();
      Object.assign(tile, { url, options, attached: false, redraws: 0 });
      tile.addTo = map => { tile.map = map; tile.attached = true; return tile; };
      tile.redraw = () => { tile.redraws += 1; };
      tiles.push(tile);
      return tile;
    },
    divIcon: options => options,
    marker(point, options) {
      const marker = new Events();
      marker.options = options;
      marker.point = point;
      marker.element = new Element("div");
      marker.addTo = group => { marker.group = group; group.markers.push(marker); allMarkers.push(marker); return marker; };
      marker.getLatLng = () => point;
      // Real Leaflet does not attach markers until its map has an initial view.
      marker.getElement = () => marker.group.map.center ? marker.element : null;
      return marker;
    },
    popup(options) {
      const popup = { options, updates: 0, element: new Element("div") };
      popup.element.rect = popupBounds ? { ...popupBounds } : rectangle(30, 30, Math.min(280, width - 60), Math.min(400, height - 60));
      popup.close = popup.element.appendChild(new Element("a"));
      popup.close.className = "leaflet-popup-close-button";
      popup.close.addEventListener("click", () => popup.map.closePopup());
      popup.setLatLng = point => { popup.point = point; return popup; };
      popup.setContent = content => { popup.content = content; popup.element.replaceChildren(popup.close, content); return popup; };
      popup.openOn = map => { map.closePopup(); popup.map = map; map.popup = popup; return popup; };
      popup.getElement = () => popup.element;
      popup.update = () => {
        popup.updates += 1;
        // Approximate Leaflet's content cap plus wrapper/tip chrome. This tests
        // positioning arithmetic, not browser layout or Leaflet animation.
        const bounds = popup.element.getBoundingClientRect();
        const resizedHeight = Math.min(bounds.height, popup.options.maxHeight + 50);
        popup.element.rect = rectangle(bounds.left, bounds.bottom - resizedHeight, bounds.width, resizedHeight);
      };
      popups.push(popup);
      return popup;
    },
    latLngBounds: points => points,
  };
  window.L = L;
  const fetch = (url, options) => new Promise((resolve, reject) => fetches.push({ url, options, resolve, reject }));
  vm.runInNewContext(source, {
    document, window, fetch, URL, AbortController, Intl, Date, Element,
    requestAnimationFrame: callback => callback(),
    setTimeout: callback => { callback(); return 1; }, clearTimeout: () => {},
  }, { filename: "booking_catalog_map.js" });
  const flush = () => new Promise(resolve => setImmediate(resolve));
  async function respond(index, payload, ok = true) {
    assert.ok(fetches[index], "expected a fetch to exist");
    fetches[index].resolve({ ok, json: async () => payload });
    await flush();
  }
  async function reject(index) { fetches[index].reject(new Error("offline")); await flush(); }
  function setConsent(value) { consent = value; window.fire("portobreak:consent-changed"); }
  return { document, window, form, checkin, root, toggle, toggleLabel, list, pagination, count, nodes, fetches, maps, tiles, allMarkers, popups, settingsCalls, flush, respond, reject, setConsent };
}

const ITEMS = [
  { id: "a", name: "Alpha", lat: 41.15, lon: -8.61, available: true, detail_url: "/reservas/a?lang=en", quote_url: "/reservas/a/simulacao-mapa?lang=en" },
  { id: "b", name: "Beta", lat: 41.15, lon: -8.61, available: false, detail_url: "/reservas/b?lang=en", quote_url: "/reservas/b/simulacao-mapa?lang=en" },
  { id: "c", name: "Gamma", lat: 41.17, lon: -8.62, available: false, detail_url: "/reservas/c?lang=en", quote_url: "/reservas/c/simulacao-mapa?lang=en" },
];
function catalog(items = ITEMS) {
  return { items, total: 4, matched: items.filter(item => item.available).length, missing_coordinates: 1, has_search: true, has_dates: true, errors: [] };
}
function quote(id, { available = true, dated = true } = {}) {
  return {
    id, name: "Quote " + id, image: "/static/" + id + ".jpg", capacity: 2, tipologia: "T1", location: "Porto",
    available: dated ? available : null, reserve_enabled: available && dated, from_price: "99 EUR",
    dates: dated ? { checkin: "2035-10-14", checkout: "2035-10-17" } : { checkin: "", checkout: "" },
    guest_summary: dated ? "2 adults" : "", errors: [], notes: [],
    price: dated && available ? { label: "399 EUR", lines: [{ label: "3 nights", value: "330 EUR" }], nights: 3, is_estimate: true } : null,
    cancellation: { label: "Cancellation terms", url: "/reservas/politica-cancelamento?lang=en" },
    detail_url: "/reservas/" + id + "?lang=en", reserve_url: "/reservas/" + id + "/reservar?lang=en",
  };
}
const choices = popup => popup.content.querySelectorAll(".booking-map-group-choice");
const text = popup => popup.content.textContent;
async function loaded(options = {}, payload = catalog()) {
  const h = createHarness({ allowed: true, view: "map", ...options });
  await h.respond(0, payload);
  const expectedStatus = !payload.items.length ? labels.empty : payload.has_search && !payload.matched ? labels.no_matches : "";
  assert.equal(h.nodes.status.textContent, expectedStatus, "catalog should render without an exception");
  return h;
}

const cases = [
  ["list mode is lazy and opening the map never bypasses consent", async () => {
    const h = createHarness();
    assert.equal(h.fetches.length, 0);
    assert.equal(h.maps.length, 0);
    h.toggle.fire("click");
    assert.equal(h.root.hidden, false);
    assert.equal(h.list.hidden, true);
    assert.equal(h.nodes.consent.hidden, false);
    assert.equal(h.fetches.length, 0);
    assert.equal(h.tiles.length, 0);
    h.nodes.settings.fire("click");
    assert.equal(h.settingsCalls.length, 1);
    assert.equal(h.fetches.length, 0);
    const permittedList = createHarness({ allowed: true });
    assert.equal(permittedList.fetches.length, 0, "consent alone must not eagerly load map data");
  }],
  ["granting consent fetches markers but not quotes, then attaches tiles", async () => {
    const h = createHarness({ view: "map" });
    h.setConsent(true);
    assert.equal(h.fetches.length, 1);
    assert.equal(h.tiles.length, 0);
    assert.equal(h.fetches[0].options.cache, "no-store");
    await h.respond(0, catalog());
    assert.equal(h.maps.length, 1);
    assert.equal(h.tiles.length, 1);
    assert.equal(h.tiles[0].attached, true);
    assert.equal(h.fetches.length, 1, "no price simulation before selecting a property");
    assert.equal(h.allMarkers.length, 2);
    assert.equal(h.count.textContent, "1 of 3 match");
    assert.equal(h.nodes.missing.textContent, "1 without location");
  }],
  ["mixed groups retain every property and each property's availability", async () => {
    const h = await loaded();
    const grouped = h.allMarkers[0];
    assert.equal(grouped.options.keyboard, true);
    assert.equal(grouped.options.icon.html.textContent, "2");
    assert.equal(grouped.options.icon.html.classList.contains("is-unavailable"), false);
    assert.equal(h.allMarkers[1].options.icon.html.classList.contains("is-unavailable"), true);
    grouped.fire("click");
    const popup = h.popups[0];
    assert.equal(choices(popup).length, 2);
    assert.match(choices(popup)[0].textContent, /AlphaMatches/);
    assert.match(choices(popup)[1].textContent, /BetaUnavailable/);
    assert.equal(h.fetches.length, 1);
    choices(popup)[1].fire("click");
    assert.match(h.fetches[1].url, /\/reservas\/b\/simulacao-mapa\?lang=en$/);
    await h.respond(1, quote("b", { available: false }));
    assert.match(text(popup), /Quote b/);
    assert.equal(popup.content.querySelector(".booking-map-quote-actions").querySelector("button").disabled, true);
    assert.equal(popup.content.querySelector(".booking-map-quote-actions").querySelector("a").href, "https://booking.example/reservas/b?lang=en");
    popup.content.querySelector(".booking-map-back").fire("click");
    choices(popup)[0].fire("click");
    await h.respond(2, quote("a"));
    const links = popup.content.querySelector(".booking-map-quote-actions").querySelectorAll("a");
    assert.equal(links[0].href, "https://booking.example/reservas/a/reservar?lang=en");
    assert.match(text(popup), /399 EUR/);
  }],
  ["out-of-order quote responses cannot replace a newer property selection", async () => {
    const h = await loaded();
    h.allMarkers[0].fire("click");
    const popup = h.popups[0];
    choices(popup)[0].fire("click");
    popup.content.querySelector(".booking-map-back").fire("click");
    assert.equal(h.fetches[1].options.signal.aborted, true);
    choices(popup)[1].fire("click");
    await h.respond(2, quote("b", { available: false }));
    await h.respond(1, quote("a"));
    assert.match(text(popup), /Quote b/);
    assert.doesNotMatch(text(popup), /Quote a|399 EUR/);
    assert.equal(popup.content.querySelector(".booking-map-quote-actions").querySelector("button").disabled, true);
  }],
  ["revoking consent aborts pending data and quotes and prevents late rendering", async () => {
    const h = createHarness({ allowed: true, view: "map" });
    h.setConsent(false);
    assert.equal(h.fetches[0].options.signal.aborted, true);
    await h.respond(0, catalog());
    assert.equal(h.maps.length, 0);
    assert.equal(h.tiles.length, 0);
    h.setConsent(true);
    await h.respond(1, catalog());
    h.allMarkers[0].fire("click");
    const popup = h.popups[0];
    choices(popup)[0].fire("click");
    h.setConsent(false);
    assert.equal(h.fetches[2].options.signal.aborted, true);
    assert.equal(h.maps[0].removed, true);
    assert.equal(h.nodes.stage.hidden, true);
    assert.equal(h.nodes.consent.hidden, false);
    await h.respond(2, quote("a"));
    assert.doesNotMatch(text(popup), /Quote a|399 EUR/);
    assert.equal(h.tiles.length, 1, "revocation must not recreate tiles");
  }],
  ["list/map toggles preserve all search parameters and cancel hidden work", async () => {
    const h = createHarness({ allowed: true });
    const original = h.window.location.href;
    h.toggle.fire("click");
    const expected = new URL(original);
    expected.searchParams.set("view", "map");
    assert.equal(h.window.location.href, expected.href);
    assert.equal(h.form.querySelector("[data-catalog-view-input]").value, "map");
    assert.equal(h.toggle.getAttribute("aria-pressed"), "true");
    h.toggle.fire("click");
    expected.searchParams.delete("view");
    assert.equal(h.window.location.href, expected.href);
    assert.equal(h.form.querySelector("[data-catalog-view-input]"), null);
    assert.equal(h.fetches[0].options.signal.aborted, true);
    assert.equal(h.list.hidden, false);
    assert.equal(h.pagination.hidden, false);
    assert.equal(h.count.textContent, "100 stays on page 4");
    await h.respond(0, catalog());
    assert.equal(h.maps.length, 0);
  }],
  ["catalog and tile failures offer retries without real network activity", async () => {
    const h = createHarness({ allowed: true, view: "map" });
    await h.reject(0);
    assert.equal(h.nodes.status.textContent, "Map unavailable");
    assert.equal(h.nodes.retry.hidden, false);
    assert.equal(h.tiles.length, 0);
    h.nodes.retry.fire("click");
    await h.respond(1, catalog());
    h.tiles[0].fire("tileerror");
    assert.equal(h.nodes.status.textContent, "Tiles unavailable");
    h.nodes.retry.fire("click");
    assert.equal(h.tiles[0].redraws, 1);
    assert.equal(h.fetches.length, 2);
  }],
  ["quote failures retain a detail link and retry without allowing a booking", async () => {
    const h = await loaded({}, catalog([ITEMS[2]]));
    h.allMarkers[0].fire("click");
    const popup = h.popups[0];
    await h.respond(1, {}, false);
    assert.match(text(popup), /Price unavailable/);
    assert.equal(popup.content.querySelector("a").href, "https://booking.example/reservas/c?lang=en");
    assert.equal(popup.content.querySelector(".booking-map-quote-actions"), null);
    popup.content.querySelector("button").fire("click");
    await h.respond(2, quote("c", { available: false }));
    assert.match(text(popup), /Quote c/);
  }],
  ["undated quotes show a starting price and focus the date field, never a total", async () => {
    const h = await loaded({}, catalog([ITEMS[0]]));
    h.allMarkers[0].fire("click");
    const popup = h.popups[0];
    await h.respond(1, quote("a", { dated: false }));
    assert.match(text(popup), /From 99 EUR/);
    assert.equal(popup.content.querySelector(".booking-map-quote-pricing"), null);
    assert.equal(popup.content.querySelector(".booking-map-quote-actions").querySelector("button").disabled, true);
    popup.content.querySelector(".booking-map-choose-dates").fire("click");
    assert.equal(h.document.activeElement, h.checkin);
    assert.equal(h.form.scrolled, true);
    assert.equal(h.maps[0].popup, null);
  }],
  ["mismatched quote identity fails closed and mobile popup has accessible controls", async () => {
    const h = await loaded({ width: 320, height: 568 }, catalog([ITEMS[0]]));
    h.allMarkers[0].fire("click");
    const popup = h.popups[0];
    assert.equal(h.allMarkers[0].options.keyboard, true);
    assert.equal(h.allMarkers[0].getElement().getAttribute("aria-label"), "Alpha — Matches");
    assert.equal(popup.close.getAttribute("aria-label"), "Close popup");
    assert.ok(popup.options.maxHeight <= 568 * 0.6);
    await h.respond(1, quote("different-property"));
    assert.match(text(popup), /Price unavailable/);
    assert.doesNotMatch(text(popup), /different-property|399 EUR/);
  }],
  ["mobile popups are fitted synchronously inside the real map box after each resize", async () => {
    const canvasBounds = rectangle(11, 554, 353, 557);
    const h = await loaded({
      width: 375, height: 844, canvasBounds,
      popupBounds: rectangle(64, 319, 322, 537),
    });
    h.allMarkers[0].fire("click");
    const popup = h.popups[0];
    const assertFits = () => {
      const bounds = popup.getElement().getBoundingClientRect();
      assert.ok(bounds.left >= canvasBounds.left + 12, "popup left must be inside map");
      assert.ok(bounds.right <= canvasBounds.right - 12, "popup right must be inside map");
      assert.ok(bounds.top >= canvasBounds.top + 12, "popup top must be inside map");
      assert.ok(bounds.bottom <= canvasBounds.bottom - 12, "popup bottom must be inside map");
    };
    assert.equal(popup.options.autoPan, false);
    assert.equal(h.allMarkers[0].options.autoPanOnFocus, false);
    assert.ok(h.maps[0].stops >= 2);
    assert.ok(popup.options.maxHeight <= canvasBounds.height - 96);
    assert.ok(h.maps[0].pans.length > 0);
    assert.ok(h.maps[0].pans[0].offset[0] > 0, "right overflow pans left");
    assert.ok(h.maps[0].pans[0].offset[1] < 0, "top overflow pans down");
    assert.ok(h.maps[0].pans.every(pan => pan.options.animate === false));
    assertFits();
    const settledPans = h.maps[0].pans.length;
    choices(popup)[0].fire("click");
    await h.respond(1, quote("a"));
    assert.equal(h.maps[0].pans.length, settledPans, "a fitting popup must not be unnecessarily panned");
    popup.element.rect = rectangle(-35, 980, 300, 420);
    popup.content.querySelector("img").fire("load");
    assertFits();
    assert.ok(h.maps[0].pans.length > settledPans, "late image dimensions must be fitted again");
  }],
  ["Enter and Space open markers; Escape cancels a quote and restores keyboard focus", async () => {
    const h = await loaded();
    const markerElement = h.allMarkers[0].getElement();
    markerElement.fire("keydown", { key: "ArrowDown" });
    assert.equal(h.popups.length, 0, "unrelated navigation keys must not open a popup");
    for (const key of ["Enter", " "]) {
      markerElement.focus();
      const opened = markerElement.fire("keydown", { key });
      assert.equal(opened.defaultPrevented, true);
      assert.equal(opened.propagationStopped, true);
      const popup = h.popups.at(-1);
      assert.equal(h.document.activeElement, choices(popup)[0]);
      choices(popup)[0].fire("click");
      const body = popup.content.querySelector(".booking-map-popup-body");
      const pendingIndex = h.fetches.length - 1;
      const pending = h.fetches[pendingIndex];
      assert.equal(h.document.activeElement, body);
      popup.getElement().fire("keydown", { key: "ArrowDown", target: body });
      assert.equal(h.maps[0].popup, popup, "other keys must not close the popup");
      const closed = popup.getElement().fire("keydown", { key: "Escape", target: body });
      assert.equal(closed.defaultPrevented, true);
      assert.equal(closed.propagationStopped, true);
      assert.equal(pending.options.signal.aborted, true);
      assert.equal(h.maps[0].popup, null);
      assert.equal(h.document.activeElement, markerElement);
      await h.respond(pendingIndex, quote("a"));
      assert.doesNotMatch(text(popup), /Quote a|399 EUR/);
    }
  }],
  ["all ten colocated properties are selectable and focus follows popup navigation", async () => {
    const items = Array.from({ length: 10 }, (_, index) => ({
      ...ITEMS[0], id: "group-" + index, name: "Property " + index,
      available: index % 2 === 0,
      quote_url: "/reservas/group-" + index + "/simulacao-mapa?lang=en",
      detail_url: "/reservas/group-" + index + "?lang=en",
    }));
    const h = await loaded({}, catalog(items));
    assert.equal(h.allMarkers.length, 1);
    h.allMarkers[0].fire("click");
    const popup = h.popups[0];
    assert.equal(choices(popup).length, 10);
    assert.equal(h.document.activeElement, choices(popup)[0]);
    for (let index = 0; index < items.length; index += 1) {
      assert.equal(choices(popup)[index].tagName, "BUTTON");
      choices(popup)[index].fire("click");
      const body = popup.content.querySelector(".booking-map-popup-body");
      assert.equal(body.getAttribute("aria-live"), "polite");
      assert.equal(h.document.activeElement, body);
      await h.respond(index + 1, quote(items[index].id, { available: items[index].available }));
      assert.match(text(popup), new RegExp("Quote group-" + index));
      popup.content.querySelector(".booking-map-back").fire("click");
      assert.equal(choices(popup).length, 10);
      assert.equal(h.document.activeElement, choices(popup)[0]);
    }
    choices(popup)[0].fire("click");
    const pending = h.fetches.at(-1);
    popup.close.fire("click");
    assert.equal(pending.options.signal.aborted, true);
    assert.equal(h.maps[0].popup, null);
    assert.equal(h.document.activeElement, h.allMarkers[0].getElement());
  }],
];

(async () => {
  let failures = 0;
  for (const [name, test] of cases) {
    try { await test(); console.log("PASS " + name); }
    catch (error) { failures += 1; console.error("FAIL " + name + "\n" + error.stack); }
  }
  console.log(`${cases.length - failures}/${cases.length} catalog-map behavior checks passed`);
  if (failures) process.exitCode = 1;
})();
