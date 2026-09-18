(function () {
  "use strict";
  const form = document.querySelector("[data-search-form]");
  if (!form) return;
  const party = form.querySelector("[data-search-party]");
  const toggle = party.querySelector("[data-party-toggle]");
  const fields = party.querySelector(".booking-search-party-fields");
  const count = party.querySelector("[data-party-count]");
  const inputs = Array.from(fields.querySelectorAll("input"));

  function close(restoreFocus) {
    party.removeAttribute("data-open");
    toggle.setAttribute("aria-expanded", "false");
    if (restoreFocus) toggle.focus({ preventScroll: true });
  }

  function open() {
    party.setAttribute("data-open", "");
    toggle.setAttribute("aria-expanded", "true");
  }

  function updateCount() {
    const total = inputs.reduce(function (sum, input) {
      const value = Number(input.value);
      return sum + (Number.isFinite(value) && value > 0 ? value : 0);
    }, 0);
    count.textContent = total > 0 ? String(total) : count.dataset.emptyLabel;
  }

  toggle.addEventListener("click", function () {
    if (party.hasAttribute("data-open")) close(false);
    else open(); // Keep focus on the toggle until a counter is selected.
  });
  party.querySelector("[data-party-close]").addEventListener("click", function () { close(true); });
  inputs.forEach(function (input) { input.addEventListener("input", updateCount); });
  document.addEventListener("click", function (event) {
    if (!party.contains(event.target)) close(false);
  });
  party.addEventListener("keydown", function (event) {
    if (event.key === "Escape" && party.hasAttribute("data-open")) {
      event.preventDefault();
      close(true);
    }
  });
  party.addEventListener("focusout", function (event) {
    // activeElement can temporarily be body before the next input receives focus.
    // A missing destination is not an outside interaction; the click handler
    // still closes the picker when a pointer actually lands outside it.
    if (event.relatedTarget && !party.contains(event.relatedTarget)) close(false);
  });
  form.addEventListener("invalid", function (event) {
    if (fields.contains(event.target)) open();
  }, true);
  form.addEventListener("reset", function () { setTimeout(updateCount, 0); });
  window.addEventListener("pageshow", updateCount);
  updateCount();
  form.setAttribute("data-mobile-search-enhanced", "");
})();
