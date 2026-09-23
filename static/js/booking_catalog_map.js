(function () {
  "use strict";
  const configNode = document.getElementById("booking-catalog-map-config");
  if (!configNode) return;
  let config;
  try { config = JSON.parse(configNode.textContent); } catch (_) { return; }
  const labels = config.labels || {};
  const root = document.querySelector("[data-catalog-map]");
  const toggle = document.querySelector("[data-catalog-view-toggle]");
  const toggleLabel = document.querySelector("[data-catalog-view-label]");
  const form = document.querySelector("[data-search-form]");
  if (!root || !toggle || !form) return;
  const listElements = Array.from(document.querySelectorAll("[data-catalog-list]"));
  const countElement = document.querySelector("[data-catalog-count]");
  const listCount = countElement.textContent;
  const consentPane = root.querySelector("[data-catalog-map-consent]");
  const consentButton = root.querySelector("[data-catalog-map-settings]");
  const stage = root.querySelector("[data-catalog-map-stage]");
  const canvas = root.querySelector("[data-catalog-map-canvas]");
  const feedback = root.querySelector("[data-catalog-map-feedback]");
  const status = root.querySelector("[data-catalog-map-status]");
  const retry = root.querySelector("[data-catalog-map-retry]");
  const warning = root.querySelector("[data-catalog-map-warning]");
  const missing = root.querySelector("[data-catalog-map-missing]");
  const availableLegend = root.querySelector("[data-map-available-label]");
  const unavailableLegend = root.querySelector("[data-map-unavailable-legend]");
  const desktopPointer = typeof window.matchMedia === "function"
    ? window.matchMedia("(min-width: 981px) and (hover: hover) and (pointer: fine)")
    : null;
  let mapView = false;
  let map = null;
  let tileLayer = null;
  let markers = null;
  let activePopup = null;
  let catalogRequest = null;
  let quoteRequest = null;
  let generation = 0;
  let quoteGeneration = 0;
  let camera = null;
  let catalog = null;
  let retryAction = null;
  let fittingPopup = false;
  let navigationBounds = null;
  let updatingNavigation = false;

  function label(key, values) {
    let result = String(labels[key] || key);
    Object.entries(values || {}).forEach(([name, value]) => {
      result = result.split("{" + name + "}").join(String(value));
    });
    return result;
  }
  function element(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined && text !== null) node.textContent = String(text);
    return node;
  }
  function airbnbIcon() {
    const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    svg.setAttribute("viewBox", "0 0 24 24");
    svg.setAttribute("aria-hidden", "true");
    svg.setAttribute("focusable", "false");
    const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
    path.setAttribute("d", "M12 3.1c-1.8 0-2.9 1.8-3.7 3.6l-4 9.1c-.9 2.1.2 4.6 2.5 5.1 2.2.5 3.8-1.6 5.2-3.8 1.4 2.2 3 4.3 5.2 3.8 2.3-.5 3.4-3 2.5-5.1l-4-9.1c-.8-1.8-1.9-3.6-3.7-3.6Zm0 5.4c1.5 2.2 2.8 4.2 2.8 5.7a2.8 2.8 0 1 1-5.6 0c0-1.5 1.3-3.5 2.8-5.7Z");
    svg.appendChild(path);
    return svg;
  }
  function mapsAllowed() {
    return Boolean(window.PortoBreakCookies && window.PortoBreakCookies.allows("external_maps"));
  }
  function wheelZoomAllowed() {
    return desktopPointer ? desktopPointer.matches : window.innerWidth > 980;
  }
  function refreshWheelZoom() {
    if (!map) return;
    if (wheelZoomAllowed()) map.scrollWheelZoom.enable();
    else map.scrollWheelZoom.disable();
  }
  function refreshNavigationLimits() {
    if (!map || !navigationBounds || updatingNavigation) return;
    const size = canvas.getBoundingClientRect();
    if (size.width <= 0 || size.height <= 0) return;
    updatingNavigation = true;
    try {
      const center = map.getCenter();
      const zoom = map.getZoom();
      map.stop();
      map.setMaxBounds(navigationBounds);
      map.stop();
      // getBoundsZoom respects the current minimum. Reset it so a narrower
      // viewport can zoom out far enough after switching to mobile/tablet.
      map.setMinZoom(0);
      const minimum = Math.max(1, Math.min(14, Math.floor(map.getBoundsZoom(navigationBounds, false, [0, 0]))));
      map.setMinZoom(minimum);
      map.setView(center, Math.max(zoom, minimum), { animate: false });
    } finally {
      updatingNavigation = false;
    }
  }
  function configureNavigation(items) {
    // Use the full catalog, including unavailable properties, not just matches.
    // Keep a useful Porto overview when there are no georeferenced properties.
    const points = items.length ? items.map(item => [Number(item.lat), Number(item.lon)]) : [[41.123, -8.704], [41.191, -8.568]];
    const latitudes = points.map(point => point[0]);
    const longitudes = points.map(point => point[1]);
    const south = Math.min(...latitudes), north = Math.max(...latitudes);
    const west = Math.min(...longitudes), east = Math.max(...longitudes);
    const latitude = (south + north) / 2, longitude = (west + east) / 2;
    // Single/coincident properties still need a neighbourhood to navigate.
    const halfHeight = Math.max(north - south, 0.02) / 2;
    const halfWidth = Math.max(east - west, 0.03) / 2;
    navigationBounds = window.L.latLngBounds([
      [latitude - halfHeight, longitude - halfWidth],
      [latitude + halfHeight, longitude + halfWidth],
    ]).pad(0.3);
    refreshNavigationLimits();
  }
  function safeURL(value, sameOrigin) {
    if (typeof value !== "string" || !value) return null;
    try {
      const url = new URL(value, window.location.href);
      if (url.protocol !== "https:" && url.protocol !== "http:") return null;
      if (sameOrigin && url.origin !== window.location.origin) return null;
      return url.href;
    } catch (_) { return null; }
  }
  function link(text, url, className) {
    const safe = safeURL(url, true);
    if (!safe) return null;
    const node = element("a", className, text);
    node.href = safe;
    return node;
  }
  function button(text, handler, className) {
    const node = element("button", className || "booking-button", text);
    node.type = "button";
    node.addEventListener("click", event => {
      // A selection replaces its own popup subtree. Stop before detaching the
      // target, otherwise Leaflet can interpret the bubbling click as a map click.
      event.stopPropagation();
      handler(event);
    });
    return node;
  }
  function showFeedback(text, action) {
    status.textContent = text || "";
    feedback.hidden = !text;
    retry.hidden = !action;
    retryAction = action || null;
  }
  function abortQuote() {
    quoteGeneration += 1;
    if (quoteRequest) quoteRequest.abort();
    quoteRequest = null;
  }
  function destroyMap(rememberCamera) {
    generation += 1;
    if (catalogRequest) catalogRequest.abort();
    catalogRequest = null;
    abortQuote();
    if (map) {
      if (rememberCamera) camera = { center: map.getCenter(), zoom: map.getZoom() };
      map.remove();
    }
    map = null;
    tileLayer = null;
    markers = null;
    activePopup = null;
    catalog = null;
    navigationBounds = null;
    stage.hidden = true;
    root.removeAttribute("aria-busy");
  }
  function dateLabel(value) {
    if (typeof value !== "string" || !/^\d{4}-\d{2}-\d{2}$/.test(value)) return value || "";
    const date = new Date(value + "T12:00:00");
    if (Number.isNaN(date.getTime())) return value;
    const locale = { pt: "pt-PT", en: "en-GB", es: "es-ES", fr: "fr-FR" }[config.lang] || "en-GB";
    return new Intl.DateTimeFormat(locale, { day: "numeric", month: "short", year: "numeric" }).format(date);
  }
  function chooseDates() {
    if (map) map.closePopup();
    form.scrollIntoView({ block: "start", behavior: "smooth" });
    if (!form.dispatchEvent(new CustomEvent("booking:search-dates-open", { cancelable: true, detail: { field: "checkin" } }))) return;
    const input = form.querySelector('[name="checkin"]');
    if (input) {
      input.focus({ preventScroll: true });
    }
  }
  function appendMessages(parent, values, className) {
    if (!Array.isArray(values) || !values.length) return;
    const list = element("ul", className);
    values.forEach(value => list.appendChild(element("li", "", value)));
    parent.appendChild(list);
  }
  function renderQuote(quote, item) {
    const card = element("article", "booking-map-quote");
    const imageURL = safeURL(quote.image, false);
    if (imageURL) {
      const photo = element("img", "booking-map-quote-image");
      photo.src = imageURL;
      photo.alt = String(quote.name || item.name || "");
      photo.loading = "lazy";
      photo.decoding = "async";
      photo.addEventListener("error", () => { photo.hidden = true; }, { once: true });
      card.appendChild(photo);
    }
    card.appendChild(element("h3", "booking-map-quote-title", quote.name || item.name));
    const meta = [quote.tipologia, quote.location];
    if (quote.capacity) meta.push(String(quote.capacity) + " " + label("guests"));
    card.appendChild(element("p", "booking-map-quote-meta", meta.filter(Boolean).join(" · ")));
    const dates = quote.dates || {};
    if (dates.checkin || dates.checkout) {
      const dateRow = element("dl", "booking-map-quote-dates");
      [["checkin", dates.checkin], ["checkout", dates.checkout]].forEach(([key, value]) => {
        const group = element("div");
        group.appendChild(element("dt", "", label(key)));
        group.appendChild(element("dd", "", dateLabel(value) || "—"));
        dateRow.appendChild(group);
      });
      card.appendChild(dateRow);
    }
    if (quote.guest_summary) card.appendChild(element("p", "booking-map-quote-guests", quote.guest_summary));
    if (quote.price && quote.price.label) {
      const pricing = element("section", "booking-map-quote-pricing");
      pricing.appendChild(element("h4", "", label("simulation")));
      if (quote.price.airbnb_total_label && quote.price.direct_total_label && quote.price.saving_label) {
        const comparison = element("div", "booking-map-quote-comparison");
        const reference = element("div");
        const badge = element(quote.price.airbnb_url ? "a" : "span", "booking-airbnb-badge" + (quote.price.airbnb_url ? "" : " booking-airbnb-badge-static"));
        if (quote.price.airbnb_url) {
          badge.href = quote.price.airbnb_url;
          badge.target = "_blank";
          badge.rel = "noopener noreferrer";
        }
        badge.setAttribute("aria-label", label("airbnb_price") + ": " + quote.price.airbnb_total_label);
        badge.appendChild(airbnbIcon());
        badge.appendChild(element("span", "", "Airbnb:"));
        badge.appendChild(element("span", "booking-airbnb-price", quote.price.airbnb_total_label));
        reference.appendChild(badge);
        comparison.appendChild(reference);
        const direct = element("div", "booking-map-quote-direct");
        direct.appendChild(element("span", "", label("direct_booking")));
        direct.appendChild(element("strong", "", quote.price.direct_total_label));
        comparison.appendChild(direct);
        const savingGroup = element("div", "booking-price-saving-group booking-map-quote-saving");
        savingGroup.appendChild(element("span", "booking-price-saving", label("you_save").replace("{value}", quote.price.saving_label)));
        const savingInfo = element("button", "booking-price-info-button", "?");
        savingInfo.type = "button";
        savingInfo.setAttribute("data-price-info-open", "");
        savingInfo.setAttribute("aria-label", label("saving_info_open"));
        savingInfo.setAttribute("aria-haspopup", "dialog");
        savingInfo.setAttribute("aria-controls", "bookingPriceInfoDialog");
        savingGroup.appendChild(savingInfo);
        comparison.appendChild(savingGroup);
        pricing.appendChild(comparison);
      }
      const lines = element("dl", "booking-map-quote-lines");
      (Array.isArray(quote.price.lines) ? quote.price.lines : []).forEach(line => {
        const row = element("div");
        row.appendChild(element("dt", "", line.label));
        row.appendChild(element("dd", "", line.value));
        lines.appendChild(row);
      });
      const total = element("div", "booking-map-quote-total");
      total.appendChild(element("dt", "", label("total")));
      total.appendChild(element("dd", "", quote.price.label));
      lines.appendChild(total);
      pricing.appendChild(lines);
      if (quote.price.nights) pricing.appendChild(element("p", "booking-map-quote-meta", String(quote.price.nights) + " " + label("nights")));
      if (quote.price.is_estimate) pricing.appendChild(element("p", "booking-map-quote-meta", label("estimate")));
      card.appendChild(pricing);
    } else if (!dates.checkin && !dates.checkout) {
      const from = quote.from_price;
      card.appendChild(element("p", "booking-map-quote-from", from ? label("from_price") + " " + String(from) + " · " + label("per_night") : label("no_price")));
      card.appendChild(button(label("choose_dates"), chooseDates, "booking-map-choose-dates"));
    }
    if (quote.available === false && (!Array.isArray(quote.errors) || !quote.errors.length)) card.appendChild(element("p", "booking-map-quote-unavailable", label("unavailable")));
    appendMessages(card, quote.errors, "booking-map-quote-errors");
    appendMessages(card, quote.notes, "booking-map-quote-notes");
    if (quote.cancellation && quote.cancellation.label) {
      const cancellation = link(quote.cancellation.label, quote.cancellation.url, "booking-map-quote-cancellation");
      if (cancellation) card.appendChild(cancellation);
    }
    const actions = element("div", "booking-map-quote-actions");
    const reserve = quote.reserve_enabled === true ? link(label("book"), quote.reserve_url, "booking-button booking-button-primary") : null;
    if (reserve) actions.appendChild(reserve);
    else {
      const disabled = button(label("book"), () => {}, "booking-button booking-button-primary");
      disabled.disabled = true;
      actions.appendChild(disabled);
    }
    const details = link(label("view_stay"), quote.detail_url || item.detail_url, "booking-button");
    if (details) actions.appendChild(details);
    card.appendChild(actions);
    return card;
  }
  function updatePopupSize(popup) {
    if (!popup || popup !== activePopup || !map || fittingPopup || updatingNavigation) return;
    fittingPopup = true;
    try {
      // Fit synchronously: animated auto-pan competes with popup content updates.
      map.stop();
      const mapBounds = canvas.getBoundingClientRect();
      const padding = 12;
      popup.options.maxHeight = Math.max(120, Math.min(560, mapBounds.height - 96, window.innerHeight * 0.6));
      popup.options.offset = [0, 7];
      popup.update();
      const popupElement = popup.getElement();
      if (!popupElement) return;
      popupElement.classList.remove("is-map-edge");
      const overflow = () => {
        const box = popupElement.getBoundingClientRect();
        const left = mapBounds.left + padding, right = mapBounds.right - padding;
        const top = mapBounds.top + padding, bottom = mapBounds.bottom - padding;
        let dx = 0, dy = 0;
        if (box.right > right) dx = box.right - right;
        if (box.left - dx < left) dx = box.left - left;
        if (box.bottom > bottom) dy = box.bottom - bottom;
        if (box.top - dy < top) dy = box.top - top;
        return [dx, dy];
      };
      const [dx, dy] = overflow();
      if (Math.abs(dx) > 1 || Math.abs(dy) > 1) {
        const zoom = map.getZoom();
        const center = map.unproject(map.project(map.getCenter(), zoom).add([Math.round(dx), Math.round(dy)]), zoom);
        // Unlike panBy, setView clamps the target centre to maxBounds.
        map.setView(center, zoom, { animate: false });
        popup.update();
        const [remainingX, remainingY] = overflow();
        if (Math.abs(remainingX) > 1 || Math.abs(remainingY) > 1) {
          // At the boundary move the card, not the map. Hide its pointer because
          // the shifted card no longer necessarily points at the marker.
          popup.options.offset = [-remainingX, 7 - remainingY];
          popupElement.classList.add("is-map-edge");
          popup.update();
        }
      }
    } finally {
      fittingPopup = false;
    }
  }
  function showProperty(item, group, popup) {
    abortQuote();
    const token = quoteGeneration;
    const currentGeneration = generation;
    const container = element("div", "booking-map-popup-content");
    if (group.length > 1) container.appendChild(button(label("back_to_group"), () => showGroup(group, popup), "booking-map-back"));
    const body = element("div", "booking-map-popup-body");
    body.setAttribute("aria-live", "polite");
    body.setAttribute("aria-busy", "true");
    body.appendChild(element("p", "booking-map-popup-loading", label("loading_quote")));
    container.appendChild(body);
    popup.setContent(container);
    body.tabIndex = -1;
    body.focus({ preventScroll: true });
    updatePopupSize(popup);
    const endpoint = safeURL(item.quote_url, true);
    quoteRequest = new AbortController();
    const controller = quoteRequest;
    const stillActive = () => token === quoteGeneration && currentGeneration === generation && mapView && mapsAllowed() && activePopup === popup;
    const failure = () => {
      if (!stillActive()) return;
      body.replaceChildren(element("p", "booking-map-quote-errors", label("quote_error")));
      body.appendChild(button(label("retry"), () => showProperty(item, group, popup)));
      const detail = link(label("view_stay"), item.detail_url, "booking-button");
      if (detail) body.appendChild(detail);
      body.removeAttribute("aria-busy");
      updatePopupSize(popup);
    };
    if (!endpoint) { failure(); return; }
    fetch(endpoint, { credentials: "same-origin", cache: "no-store", headers: { Accept: "application/json" }, signal: controller.signal })
      .then(response => { if (!response.ok) throw new Error("quote_failed"); return response.json(); })
      .then(quote => {
        if (!stillActive()) return;
        if (!quote || String(quote.id) !== String(item.id)) throw new Error("quote_mismatch");
        body.replaceChildren(renderQuote(quote, item));
        body.removeAttribute("aria-busy");
        body.querySelectorAll("img").forEach(photo => photo.addEventListener("load", () => updatePopupSize(popup), { once: true }));
        updatePopupSize(popup);
      })
      .catch(error => { if (error.name !== "AbortError") failure(); })
      .finally(() => { if (quoteRequest === controller) quoteRequest = null; });
  }
  function showGroup(group, popup) {
    abortQuote();
    if (group.length === 1) { showProperty(group[0], group, popup); return; }
    const container = element("section", "booking-map-group");
    container.appendChild(element("h3", "", label("group_count", { count: group.length })));
    const list = element("ul", "booking-map-group-list");
    group.forEach(item => {
      const row = element("li");
      const available = item.available === true;
      const choice = button("", () => showProperty(item, group, popup), "booking-map-group-choice");
      choice.appendChild(element("span", "booking-catalog-map-dot" + (available ? "" : " is-unavailable")));
      choice.appendChild(element("strong", "", item.name));
      choice.appendChild(element("small", "", label(catalog && catalog.has_search ? (available ? "legend_available" : "legend_unavailable") : "legend_all")));
      row.appendChild(choice);
      list.appendChild(row);
    });
    container.appendChild(list);
    popup.setContent(container);
    updatePopupSize(popup);
    const firstChoice = container.querySelector("button");
    if (firstChoice) firstChoice.focus({ preventScroll: true });
  }
  function openGroup(group, marker) {
    if (!map || !mapsAllowed()) return;
    map.stop();
    map.closePopup();
    const popup = window.L.popup({
      className: "booking-catalog-popup", maxWidth: 340,
      minWidth: Math.max(210, Math.min(280, window.innerWidth - 80)),
      maxHeight: Math.max(230, Math.min(560, window.innerHeight * 0.6)),
      autoPan: false, closeButton: true, offset: [0, 7],
    }).setLatLng(marker.getLatLng());
    activePopup = popup;
    popup.setContent(element("div"));
    popup.openOn(map);
    const popupElement = popup.getElement();
    const restoreMarkerFocus = () => {
      const markerElement = marker.getElement();
      if (markerElement && markerElement.isConnected) markerElement.focus({ preventScroll: true });
    };
    popupElement.addEventListener("keydown", event => {
      if (event.key !== "Escape") return;
      event.preventDefault();
      event.stopPropagation();
      if (map) map.closePopup();
      restoreMarkerFocus();
    });
    const close = popupElement.querySelector(".leaflet-popup-close-button");
    if (close) {
      close.setAttribute("aria-label", label("close"));
      close.addEventListener("click", restoreMarkerFocus);
    }
    showGroup(group, popup);
  }
  function renderMarkers(payload) {
    markers.clearLayers();
    const groups = new Map();
    const items = (Array.isArray(payload.items) ? payload.items : []).filter(item => {
      return Number.isFinite(Number(item.lat)) && Number.isFinite(Number(item.lon)) && item.lat !== null && item.lon !== null && Math.abs(Number(item.lat)) <= 90 && Math.abs(Number(item.lon)) <= 180;
    });
    configureNavigation(items);
    items.forEach(item => {
      const key = Number(item.lat) + "," + Number(item.lon);
      if (!groups.has(key)) groups.set(key, []);
      groups.get(key).push(item);
    });
    groups.forEach(group => {
      group.sort((a, b) => String(a.name).localeCompare(String(b.name), config.lang));
      const available = group.some(item => item.available === true);
      const dot = element("span", "booking-catalog-pin" + (available ? "" : " is-unavailable"), group.length > 1 ? group.length : "");
      if (group.length === 1) dot.appendChild(element("span", "booking-catalog-pin-core"));
      const title = group.length > 1 ? label("group_count", { count: group.length }) : String(group[0].name) + (payload.has_search ? " — " + label(available ? "legend_available" : "legend_unavailable") : "");
      const icon = window.L.divIcon({ html: dot, className: "booking-catalog-marker", iconSize: [38, 38], iconAnchor: [19, 19], popupAnchor: [0, -16] });
      const marker = window.L.marker([Number(group[0].lat), Number(group[0].lon)], { icon, title, alt: title, keyboard: true, riseOnHover: true, autoPanOnFocus: false }).addTo(markers);
      marker.on("click", () => openGroup(group, marker));
      const markerElement = marker.getElement();
      markerElement.setAttribute("aria-label", title);
      markerElement.addEventListener("keydown", event => {
        if (event.key !== "Enter" && event.key !== " ") return;
        event.preventDefault();
        event.stopPropagation();
        openGroup(group, marker);
      });
    });
    const matches = items.filter(item => item.available === true);
    if (camera) map.setView(camera.center, camera.zoom, { animate: false });
    else if (items.length) {
      const focusItems = payload.has_search && matches.length ? matches : items;
      map.fitBounds(window.L.latLngBounds(focusItems.map(item => [Number(item.lat), Number(item.lon)])), { padding: [36, 36], maxZoom: 14, animate: false });
    } else map.fitBounds(navigationBounds, { padding: [36, 36], maxZoom: 14, animate: false });
    availableLegend.textContent = label(payload.has_search ? "legend_available" : "legend_all");
    unavailableLegend.hidden = !payload.has_search;
    countElement.textContent = payload.has_search ? label("match_count", { count: matches.length, total: items.length }) : label("all_stays", { count: items.length });
    missing.hidden = !payload.missing_coordinates;
    missing.textContent = payload.missing_coordinates ? label("missing_coordinates", { count: payload.missing_coordinates }) : "";
    const errors = Array.isArray(payload.errors) ? payload.errors : [];
    warning.hidden = !errors.length;
    warning.textContent = errors.join(" ");
    if (!items.length) showFeedback(label("empty"));
    else if (payload.has_search && !matches.length) showFeedback(label("no_matches"));
    else showFeedback("");
  }
  async function loadCatalog() {
    if (!mapView || !mapsAllowed()) return;
    const endpoint = safeURL(config.data_url, true);
    if (!endpoint || !window.L) { showFeedback(label("error"), loadCatalog); return; }
    if (catalogRequest) catalogRequest.abort();
    const token = ++generation;
    const controller = new AbortController();
    catalogRequest = controller;
    root.setAttribute("aria-busy", "true");
    showFeedback(label("loading"));
    try {
      const response = await fetch(endpoint, { credentials: "same-origin", cache: "no-store", headers: { Accept: "application/json" }, signal: controller.signal });
      if (!response.ok) throw new Error("catalog_failed");
      const payload = await response.json();
      if (token !== generation || !mapView || !mapsAllowed()) return;
      if (!payload || !Array.isArray(payload.items)) throw new Error("catalog_invalid");
      catalog = payload;
      if (!map) {
        stage.hidden = false;
        map = window.L.map(canvas, {
          scrollWheelZoom: wheelZoomAllowed(), keyboard: true,
          zoomAnimation: false, markerZoomAnimation: false,
          maxZoom: 19, maxBoundsViscosity: 1, bounceAtZoomLimits: false,
        }).setView([41.1579, -8.6291], 12, { animate: false });
        markers = window.L.layerGroup().addTo(map);
        map.on("popupclose", event => {
          if (event.popup === activePopup) { activePopup = null; abortQuote(); }
        });
        map.on("resize", () => {
          refreshNavigationLimits();
          if (activePopup) updatePopupSize(activePopup);
        });
        map.on("moveend zoomend", () => { if (activePopup) updatePopupSize(activePopup); });
        tileLayer = window.L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
          maxZoom: 19, noWrap: true,
          attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap contributors</a>',
        });
        tileLayer.on("tileerror", () => {
          if (mapView && mapsAllowed()) showFeedback(label("tile_error"), () => { showFeedback(""); if (tileLayer) tileLayer.redraw(); });
        });
        // Tiles are attached only after verified consent, including after the fetch.
        if (!mapsAllowed()) { destroyMap(false); return; }
        tileLayer.addTo(map);
      }
      renderMarkers(payload);
      map.invalidateSize();
    } catch (error) {
      if (error.name !== "AbortError" && token === generation && mapView && mapsAllowed()) showFeedback(label("error"), loadCatalog);
    } finally {
      if (catalogRequest === controller) catalogRequest = null;
      if (token === generation) root.removeAttribute("aria-busy");
    }
  }
  function refreshConsent() {
    const allowed = mapsAllowed();
    consentButton.hidden = !window.PortoBreakCookies;
    consentPane.hidden = allowed;
    if (!allowed) {
      destroyMap(false);
      missing.hidden = true;
      warning.hidden = true;
      showFeedback("");
      return;
    }
    if (mapView && !map && !catalogRequest) loadCatalog();
  }
  function setView(nextMapView, pushHistory) {
    mapView = nextMapView;
    root.hidden = !mapView;
    listElements.forEach(node => { node.hidden = mapView; });
    toggle.setAttribute("aria-pressed", String(mapView));
    toggleLabel.textContent = label(mapView ? "view_list" : "view_map");
    let input = form.querySelector("[data-catalog-view-input]");
    if (mapView && !input) {
      input = element("input");
      input.type = "hidden";
      input.name = "view";
      input.value = "map";
      input.setAttribute("data-catalog-view-input", "");
      form.appendChild(input);
    } else if (!mapView && input) input.remove();
    if (pushHistory) {
      const url = new URL(window.location.href);
      if (mapView) url.searchParams.set("view", "map");
      else url.searchParams.delete("view");
      window.history.pushState(window.history.state, "", url.pathname + url.search + url.hash);
    }
    if (mapView) refreshConsent();
    else { destroyMap(true); countElement.textContent = listCount; }
  }
  toggle.addEventListener("click", () => setView(!mapView, true));
  consentButton.addEventListener("click", () => {
    if (window.PortoBreakCookies) window.PortoBreakCookies.openMapsSettings();
  });
  retry.addEventListener("click", () => { if (retryAction) retryAction(); });
  if (desktopPointer && desktopPointer.addEventListener) {
    desktopPointer.addEventListener("change", refreshWheelZoom);
  } else if (desktopPointer && desktopPointer.addListener) {
    desktopPointer.addListener(refreshWheelZoom);
  } else {
    window.addEventListener("resize", refreshWheelZoom);
  }
  window.addEventListener("portobreak:consent-changed", refreshConsent);
  window.addEventListener("popstate", () => setView(new URL(window.location.href).searchParams.get("view") === "map", false));
  window.addEventListener("pagehide", () => destroyMap(true));
  window.addEventListener("pageshow", event => { if (event.persisted) refreshConsent(); });
  toggle.hidden = false;
  setView(config.view === "map", false);
})();
