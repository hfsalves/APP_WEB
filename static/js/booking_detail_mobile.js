(function () {
  "use strict";
  const form = document.querySelector("[data-booking-calendar-form]");
  const dialog = document.querySelector("[data-detail-calendar-dialog]");
  if (!form || !dialog || typeof dialog.showModal !== "function") return;
  const panel = form.closest(".booking-reserve-panel");
  const calendar = form.querySelector("[data-calendar]");
  const guestGrid = form.querySelector(".booking-guest-grid");
  const calendarHome = form.querySelector("[data-detail-calendar-home]");
  const guestsHome = form.querySelector("[data-detail-guests-home]");
  const calendarSlot = dialog.querySelector("[data-detail-calendar-slot]");
  const guestsSlot = panel.querySelector("[data-detail-guests-slot]");
  const guestField = panel.querySelector("[data-detail-guest-field]");
  const guestTrigger = panel.querySelector("[data-detail-guests-trigger]");
  const guestPopover = panel.querySelector("[data-detail-guest-popover]");
  const dateTriggers = Array.from(panel.querySelectorAll("[data-detail-date-trigger]"));
  const checkin = form.querySelector("[data-checkin-input]");
  const checkout = form.querySelector("[data-checkout-input]");
  const guestInputs = Array.from(guestGrid.querySelectorAll("input"));
  const inputs = [checkin, checkout, ...guestInputs];
  // Hidden input.value updates its defaultValue too; use the server's date
  // attributes so initial calendar normalization cannot validate an old quote.
  const originalValues = [calendar.dataset.selectedCheckin || "", calendar.dataset.selectedCheckout || "", ...guestInputs.map(input => input.defaultValue)];
  const reserve = panel.querySelector("[data-detail-reserve-action]");
  const reserveHref = reserve && reserve.getAttribute("href");
  const notice = form.querySelector("[data-detail-update-notice]");
  const cancellation = panel.querySelector(".booking-cancellation-note");
  const i18n = JSON.parse(document.getElementById("booking-i18n").textContent || "{}");
  const mobile = window.matchMedia("(max-width: 720px)");
  let enhanced = false;
  let changedOnMobile = false;
  let datesValid = form.dataset.datesValid !== "0";
  let lastDateTrigger = null;
  let restoreDateFocus = true;

  function sync() {
    panel.querySelector('[data-detail-date-value="checkin"]').textContent = checkin.value || i18n.choose;
    panel.querySelector('[data-detail-date-value="checkout"]').textContent = checkout.value || i18n.choose;
    const labels = [i18n.adults, i18n.children, i18n.babies];
    panel.querySelector("[data-detail-guest-summary]").textContent = guestInputs.map((input, index) => {
      const value = Number(input.value);
      return Number.isFinite(value) && value > 0 ? String(value) + " " + labels[index] : "";
    }).filter(Boolean).join(" / ") || i18n.choose;
    if (dialog.open) {
      dialog.querySelector("h2").textContent = i18n[calendar.dataset.editingDate] || i18n.calendar;
    }
    const changed = inputs.some((input, index) => input.value !== originalValues[index]);
    if (enhanced && changed) changedOnMobile = true;
    // Once edited on mobile, resizing must not reactivate a stale reservation link.
    if (!enhanced && !changedOnMobile) return;
    notice.hidden = !changed;
    if (cancellation) cancellation.hidden = checkin.value !== originalValues[0];
    if (!reserveHref) return; // A server-disabled reservation is never enabled here.
    const disabled = changed || !checkin.value || !checkout.value || !datesValid || form.dataset.datesValid === "0" || form.dataset.guestsValid === "0";
    if (disabled) {
      reserve.removeAttribute("href");
      reserve.setAttribute("aria-disabled", "true");
      reserve.setAttribute("tabindex", "-1");
    } else {
      reserve.setAttribute("href", reserveHref);
      reserve.removeAttribute("aria-disabled");
      reserve.removeAttribute("tabindex");
    }
  }

  function closeGuests(restoreFocus) {
    guestPopover.hidden = true;
    guestTrigger.setAttribute("aria-expanded", "false");
    if (restoreFocus && enhanced) guestTrigger.focus({ preventScroll: true });
  }
  function openGuests() {
    if (!enhanced) return;
    guestPopover.hidden = false;
    guestTrigger.setAttribute("aria-expanded", "true");
  }
  function closeCalendar(restoreFocus) {
    restoreDateFocus = restoreFocus;
    if (dialog.open) dialog.close();
  }
  function openCalendar(field) {
    if (!enhanced) return;
    closeGuests(false);
    lastDateTrigger = dateTriggers.find(button => button.dataset.detailDateTrigger === field);
    restoreDateFocus = true;
    form.dispatchEvent(new CustomEvent("booking:edit-date", { detail: { field } }));
    dialog.querySelector("h2").textContent = i18n[calendar.dataset.editingDate] || i18n[field];
    if (!dialog.open) dialog.showModal();
    document.body.classList.add("booking-detail-calendar-open");
  }

  dateTriggers.forEach(button => button.addEventListener("click", () => openCalendar(button.dataset.detailDateTrigger)));
  dialog.querySelectorAll("[data-detail-calendar-close]").forEach(button => button.addEventListener("click", () => closeCalendar(true)));
  dialog.addEventListener("close", () => {
    document.body.classList.remove("booking-detail-calendar-open");
    form.dispatchEvent(new CustomEvent("booking:finish-date-edit"));
    if (restoreDateFocus && enhanced && lastDateTrigger) lastDateTrigger.focus({ preventScroll: true });
  });
  dialog.addEventListener("click", event => {
    if (event.target !== dialog) return;
    const bounds = dialog.getBoundingClientRect();
    if (event.clientX < bounds.left || event.clientX > bounds.right || event.clientY < bounds.top || event.clientY > bounds.bottom) closeCalendar(true);
  });
  guestTrigger.addEventListener("click", () => {
    if (guestPopover.hidden) openGuests();
    else closeGuests(false);
  });
  panel.querySelector("[data-detail-guests-close]").addEventListener("click", () => closeGuests(true));
  guestField.addEventListener("focusout", event => {
    if (event.relatedTarget && !guestField.contains(event.relatedTarget)) closeGuests(false);
  });
  guestField.addEventListener("keydown", event => {
    if (event.key === "Escape" && !guestPopover.hidden) {
      event.preventDefault();
      closeGuests(true);
    }
  });
  document.addEventListener("click", event => {
    if (!guestField.contains(event.target)) closeGuests(false);
  });
  guestInputs.forEach(input => {
    input.addEventListener("input", sync);
    input.addEventListener("change", sync);
    input.addEventListener("invalid", openGuests);
  });
  form.addEventListener("booking:dates-changed", event => {
    datesValid = event.detail.valid;
    sync();
  });
  form.addEventListener("booking:dates-required", event => openCalendar(event.detail.field));
  if (reserveHref) reserve.addEventListener("click", event => {
    if (reserve.getAttribute("aria-disabled") === "true") event.preventDefault();
  });

  function applyViewport() {
    if (mobile.matches && !enhanced) {
      calendarSlot.appendChild(calendar);
      guestsSlot.appendChild(guestGrid);
      enhanced = true;
      panel.setAttribute("data-mobile-detail-enhanced", "");
    } else if (!mobile.matches && enhanced) {
      closeGuests(false);
      closeCalendar(false);
      calendarHome.appendChild(calendar);
      guestsHome.appendChild(guestGrid);
      enhanced = false;
      panel.removeAttribute("data-mobile-detail-enhanced");
    }
    sync();
  }
  mobile.addEventListener("change", applyViewport);
  window.addEventListener("pageshow", sync);
  applyViewport();
})();
