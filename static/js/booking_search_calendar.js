(function () {
  "use strict";
  const form = document.querySelector("[data-search-form]");
  const dialog = document.querySelector("[data-search-calendar]");
  const configNode = document.getElementById("booking-search-calendar-config");
  if (!form || !dialog || !configNode || typeof dialog.showModal !== "function" || typeof dialog.show !== "function") return;
  let config;
  try { config = JSON.parse(configNode.textContent); } catch (_) { return; }
  const labels = config.labels || {};
  const locale = { pt: "pt-PT", en: "en-GB", es: "es-ES", fr: "fr-FR" }[config.lang] || "pt-PT";
  const checkin = form.querySelector('[name="checkin"]');
  const checkout = form.querySelector('[name="checkout"]');
  const triggers = Array.from(form.querySelectorAll("[data-search-date-toggle]"));
  const months = dialog.querySelector("[data-search-calendar-months]");
  const scrollBody = dialog.querySelector(".booking-search-calendar-body");
  const message = dialog.querySelector("[data-search-calendar-message]");
  const title = dialog.querySelector("[data-search-calendar-title]");
  const previous = dialog.querySelector("[data-search-calendar-prev]");
  const next = dialog.querySelector("[data-search-calendar-next]");
  if (!checkin || !checkout || triggers.length !== 2 || !months || !message || !title || !previous || !next) return;
  const shortDate = new Intl.DateTimeFormat(locale, { day: "2-digit", month: "2-digit", year: "numeric", timeZone: "UTC" });
  const fullDate = new Intl.DateTimeFormat(locale, { weekday: "long", day: "numeric", month: "long", year: "numeric", timeZone: "UTC" });
  const monthDate = new Intl.DateTimeFormat(locale, { month: "long", year: "numeric", timeZone: "UTC" });
  const weekday = new Intl.DateTimeFormat(locale, { weekday: "short", timeZone: "UTC" });
  let today = todayISO();
  let cursor = firstMonth(today);
  let start = "", end = "", editing = "checkin", focusDate = "", lastTrigger = null;
  let days = new Map();

  function todayISO() {
    // Search dates follow the destination's civil day, even for guests abroad.
    const parts = new Intl.DateTimeFormat("en-CA", {
      timeZone: "Europe/Lisbon", year: "numeric", month: "2-digit", day: "2-digit",
    }).formatToParts(new Date());
    const values = Object.fromEntries(parts.map(part => [part.type, part.value]));
    return values.year + "-" + values.month + "-" + values.day;
  }
  function parseISO(value) {
    if (!/^\d{4}-\d{2}-\d{2}$/.test(value || "")) return null;
    const date = new Date(value + "T12:00:00Z");
    return Number.isFinite(date.getTime()) && date.toISOString().slice(0, 10) === value ? date : null;
  }
  function iso(date) { return date.toISOString().slice(0, 10); }
  function firstMonth(value) { return value.slice(0, 7) + "-01"; }
  function addDays(value, amount) {
    const date = parseISO(value);
    date.setUTCDate(date.getUTCDate() + amount);
    return iso(date);
  }
  function addMonths(value, amount) {
    const date = parseISO(value);
    const day = date.getUTCDate();
    date.setUTCDate(1);
    date.setUTCMonth(date.getUTCMonth() + amount);
    const last = new Date(Date.UTC(date.getUTCFullYear(), date.getUTCMonth() + 1, 0)).getUTCDate();
    date.setUTCDate(Math.min(day, last));
    return iso(date);
  }
  function mobile() { return window.innerWidth <= 720; }
  function syncFields() {
    triggers.forEach(trigger => {
      const field = trigger.dataset.searchDateToggle;
      const value = field === "checkin" ? checkin.value : checkout.value;
      const parsed = parseISO(value);
      const text = parsed ? shortDate.format(parsed) : labels.choose;
      trigger.querySelector("[data-search-date-value]").textContent = text || "—";
      trigger.setAttribute("aria-label", (labels[field] || field) + ": " + (text || "—"));
      trigger.setAttribute("aria-expanded", String(dialog.open));
      if (dialog.open && editing === field) trigger.setAttribute("data-active", "");
      else trigger.removeAttribute("data-active");
    });
  }
  function position() {
    if (!dialog.open || mobile()) return;
    const anchor = triggers[0].getBoundingClientRect();
    const box = dialog.getBoundingClientRect();
    dialog.style.left = Math.max(12, Math.min(anchor.left, window.innerWidth - box.width - 12)) + "px";
    dialog.style.top = Math.max(12, Math.min(anchor.bottom + 8, window.innerHeight - box.height - 12)) + "px";
  }
  function show() {
    dialog.dataset.presentation = mobile() ? "modal" : "dropdown";
    dialog.setAttribute("aria-modal", String(mobile()));
    dialog.style.removeProperty("left");
    dialog.style.removeProperty("top");
    if (mobile()) dialog.showModal();
    else dialog.show();
    position();
  }
  function close(restoreFocus) {
    if (!dialog.open) return;
    dialog.close();
    syncFields();
    if (restoreFocus && lastTrigger) lastTrigger.focus({ preventScroll: true });
  }
  function setMessage(text, error) {
    message.textContent = text;
    message.dataset.tone = error ? "error" : "";
  }
  function instruction() {
    setMessage(editing === "checkout" ? labels.calendar_pick_checkout : labels.calendar_start, false);
  }
  function includeDate(value) {
    const month = firstMonth(value);
    if (month < cursor || month > addMonths(cursor, 1)) cursor = month;
  }
  function focusDay() {
    const day = days.get(focusDate);
    if (!day || day.disabled) return;
    day.focus({ preventScroll: true });
    // Reveal keyboard focus within the calendar, without scrolling the page
    // behind a mobile modal or moving the anchored desktop dropdown.
    if (scrollBody) {
      const box = day.getBoundingClientRect();
      const visible = scrollBody.getBoundingClientRect();
      if (box.top < visible.top) scrollBody.scrollTop -= visible.top - box.top + 4;
      else if (box.bottom > visible.bottom) scrollBody.scrollTop += box.bottom - visible.bottom + 4;
    }
  }
  function open(field) {
    if (dialog.open) close(false);
    today = todayISO();
    start = parseISO(checkin.value) && checkin.value >= today ? checkin.value : "";
    end = start && parseISO(checkout.value) && checkout.value > start ? checkout.value : "";
    editing = field === "checkout" && start ? "checkout" : "checkin";
    lastTrigger = triggers.find(trigger => trigger.dataset.searchDateToggle === field) || triggers[0];
    focusDate = editing === "checkout" ? (end || addDays(start, 1)) : (start || today);
    cursor = firstMonth(editing === "checkout" ? start : focusDate);
    includeDate(focusDate);
    // Map buttons stop propagation; explicitly close an already open guest picker.
    const party = form.querySelector("[data-search-party]");
    if (party) {
      party.removeAttribute("data-open");
      party.querySelector("[data-party-toggle]").setAttribute("aria-expanded", "false");
    }
    instruction();
    render();
    show();
    syncFields();
    focusDay();
    return true;
  }
  function commit(first, last) {
    checkin.value = first;
    checkout.value = last;
    [checkin, checkout].forEach(input => {
      input.dispatchEvent(new Event("input", { bubbles: true }));
      input.dispatchEvent(new Event("change", { bubbles: true }));
    });
    close(true);
    syncFields();
  }
  function select(value) {
    if (!parseISO(value) || value < today) return;
    if (editing === "checkin") {
      start = value;
      end = "";
      editing = "checkout";
      focusDate = value;
      instruction();
      render();
      syncFields();
      focusDay();
    } else if (value <= start) {
      setMessage(labels.checkout_after_checkin, true);
    } else {
      end = value;
      commit(start, end);
    }
  }
  function onDayKey(event) {
    const value = event.currentTarget.dataset.date;
    const offset = (parseISO(value).getUTCDay() + 6) % 7;
    let target;
    if (event.key === "ArrowLeft") target = addDays(value, -1);
    else if (event.key === "ArrowRight") target = addDays(value, 1);
    else if (event.key === "ArrowUp") target = addDays(value, -7);
    else if (event.key === "ArrowDown") target = addDays(value, 7);
    else if (event.key === "Home") target = addDays(value, -offset);
    else if (event.key === "End") target = addDays(value, 6 - offset);
    else if (event.key === "PageUp") target = addMonths(value, -1);
    else if (event.key === "PageDown") target = addMonths(value, 1);
    else return;
    event.preventDefault();
    focusDate = target < today ? today : target;
    includeDate(focusDate);
    render();
    focusDay();
  }
  function renderMonth(value) {
    const date = parseISO(value);
    const section = document.createElement("section");
    section.className = "booking-calendar-month";
    const heading = document.createElement("h3");
    heading.textContent = monthDate.format(date);
    section.appendChild(heading);
    const weekdays = document.createElement("div");
    weekdays.className = "booking-calendar-weekdays";
    weekdays.setAttribute("aria-hidden", "true");
    for (let index = 0; index < 7; index += 1) {
      const label = document.createElement("span");
      label.textContent = weekday.format(new Date(Date.UTC(2024, 0, 1 + index, 12))).replace(/\.$/, "").slice(0, 3);
      weekdays.appendChild(label);
    }
    section.appendChild(weekdays);
    const grid = document.createElement("div");
    grid.className = "booking-calendar-grid";
    const offset = (date.getUTCDay() + 6) % 7;
    for (let index = 0; index < offset; index += 1) {
      const blank = document.createElement("span");
      blank.className = "booking-calendar-empty";
      grid.appendChild(blank);
    }
    const count = new Date(Date.UTC(date.getUTCFullYear(), date.getUTCMonth() + 1, 0)).getUTCDate();
    for (let index = 0; index < count; index += 1) {
      const value = addDays(iso(date), index);
      const button = document.createElement("button");
      button.type = "button";
      button.className = "booking-calendar-day";
      button.textContent = String(index + 1);
      button.dataset.date = value;
      button.disabled = value < today;
      button.tabIndex = value === focusDate ? 0 : -1;
      if (button.disabled) button.classList.add("is-past");
      if (value === start) button.classList.add("is-start");
      if (value === end) button.classList.add("is-end");
      if (start && end && value > start && value < end) button.classList.add("is-range");
      if (value === today) button.setAttribute("aria-current", "date");
      let label = fullDate.format(parseISO(value));
      if (value === start) label += ". " + labels.checkin;
      if (value === end) label += ". " + labels.checkout;
      button.setAttribute("aria-label", label);
      button.setAttribute("aria-pressed", String(Boolean(start && (value === start || (end && value > start && value <= end)))));
      button.addEventListener("click", event => {
        // Rendering replaces the clicked day. Do not let that detached target
        // reach the outside-click handler and dismiss the unfinished interval.
        event.stopPropagation();
        select(value);
      });
      button.addEventListener("keydown", onDayKey);
      days.set(value, button);
      grid.appendChild(button);
    }
    section.appendChild(grid);
    return section;
  }
  function render() {
    days = new Map();
    months.replaceChildren(renderMonth(cursor), renderMonth(addMonths(cursor, 1)));
    title.textContent = monthDate.format(parseISO(cursor)) + " — " + monthDate.format(parseISO(addMonths(cursor, 1)));
    previous.disabled = cursor <= firstMonth(today);
    position();
  }
  triggers.forEach(trigger => trigger.addEventListener("click", () => {
    if (dialog.open && lastTrigger === trigger) close(true);
    else open(trigger.dataset.searchDateToggle);
  }));
  previous.addEventListener("click", () => {
    if (cursor <= firstMonth(today)) return;
    cursor = addMonths(cursor, -1);
    focusDate = cursor < today ? today : cursor;
    render();
    if (scrollBody) scrollBody.scrollTop = 0;
  });
  next.addEventListener("click", () => {
    cursor = addMonths(cursor, 1);
    focusDate = cursor;
    render();
    if (scrollBody) scrollBody.scrollTop = 0;
  });
  dialog.querySelectorAll("[data-search-calendar-close]").forEach(button => button.addEventListener("click", () => close(true)));
  dialog.querySelector("[data-search-calendar-clear]").addEventListener("click", () => commit("", ""));
  dialog.addEventListener("cancel", event => { event.preventDefault(); close(true); });
  dialog.addEventListener("keydown", event => {
    if (event.key === "Escape") { event.preventDefault(); close(true); }
  });
  dialog.addEventListener("click", event => {
    if (event.target !== dialog || !mobile()) return;
    const box = dialog.getBoundingClientRect();
    if (event.clientX < box.left || event.clientX > box.right || event.clientY < box.top || event.clientY > box.bottom) close(true);
  });
  document.addEventListener("click", event => {
    if (dialog.open && !mobile() && !dialog.contains(event.target) && !triggers.some(trigger => trigger.contains(event.target))) close(false);
  });
  document.addEventListener("focusin", event => {
    if (dialog.open && !mobile() && !dialog.contains(event.target) && !triggers.includes(event.target)) close(false);
  });
  form.addEventListener("booking:search-dates-open", event => {
    if (open(event.detail && event.detail.field || "checkin")) event.preventDefault();
  });
  [checkin, checkout].forEach(input => {
    input.addEventListener("change", syncFields);
    input.addEventListener("focus", () => open(input === checkin ? "checkin" : "checkout"));
  });
  form.addEventListener("submit", event => {
    today = todayISO();
    if (!checkin.value && !checkout.value) return;
    if (parseISO(checkin.value) && checkin.value >= today && parseISO(checkout.value) && checkout.value > checkin.value) return;
    event.preventDefault();
    event.stopImmediatePropagation();
    open(parseISO(checkin.value) && checkin.value >= today ? "checkout" : "checkin");
  }, true);
  form.addEventListener("reset", () => { close(false); setTimeout(syncFields, 0); });
  window.addEventListener("pageshow", syncFields);
  window.addEventListener("scroll", position, { passive: true });
  window.addEventListener("resize", () => {
    if (!dialog.open) return;
    const presentation = mobile() ? "modal" : "dropdown";
    if (dialog.dataset.presentation !== presentation) {
      dialog.close();
      show();
      focusDay();
    } else position();
  });
  syncFields();
  form.setAttribute("data-date-picker-enhanced", "");
})();
