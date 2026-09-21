(function () {
  "use strict";

  const configElement = document.getElementById("booking-cookie-config");
  if (!configElement) return;

  let config;
  try {
    config = JSON.parse(configElement.textContent);
  } catch (_) {
    return;
  }

  const banner = document.getElementById("booking-cookie-banner");
  const dialog = document.getElementById("booking-cookie-dialog");
  const preferencesInput = document.getElementById("booking-cookie-preferences");
  const mapsInput = document.getElementById("booking-cookie-external-maps");
  const analyticsInput = document.getElementById("booking-cookie-analytics");
  const status = document.getElementById("booking-cookie-status");
  const errors = [
    document.getElementById("booking-cookie-banner-error"),
    document.getElementById("booking-cookie-dialog-error"),
  ];
  let consent = null;
  let saving = false;
  let opener = null;
  let openedForMaps = false;
  let expiryTimer = null;
  let consentGeneration = 0;
  let refreshPending = null;
  let refreshAgain = false;
  let channel = null;

  function activeConsent(value) {
    return value && typeof value.preferences === "boolean" &&
      typeof value.external_maps === "boolean" &&
      typeof value.analytics === "boolean" &&
      typeof value.expires_at === "number" && value.expires_at > Date.now() / 1000
      ? value : null;
  }

  function decisionKey(value) {
    return value ? [value.version, value.decided_at, value.expires_at,
      value.preferences, value.external_maps, value.analytics].join("|") : "";
  }

  function allows(category) {
    if (category === "necessary") return true;
    return (category === "preferences" || category === "external_maps" || category === "analytics") &&
      activeConsent(consent) !== null && consent[category] === true;
  }

  function scheduleExpiry() {
    clearTimeout(expiryTimer);
    if (!consent) return;
    const delay = Math.max(0, consent.expires_at * 1000 - Date.now());
    expiryTimer = setTimeout(function () {
      if (activeConsent(consent)) scheduleExpiry();
      else applyConsent(null);
    }, Math.min(delay + 50, 2147483647));
  }

  function applyConsent(value, announce) {
    const next = activeConsent(value);
    const changed = decisionKey(consent) !== decisionKey(next);
    consent = next;
    banner.hidden = consent !== null;
    scheduleExpiry();
    if (!changed) return;
    consentGeneration += 1;
    if (dialog.open && !saving) {
      preferencesInput.checked = allows("preferences");
      mapsInput.checked = allows("external_maps");
      analyticsInput.checked = allows("analytics");
    }
    if (announce !== false) {
      window.dispatchEvent(new CustomEvent("portobreak:consent-changed", {
        detail: consent ? Object.assign({}, consent) : null,
      }));
    }
  }

  function refreshConsent() {
    if (consent && !activeConsent(consent)) applyConsent(null);
    if (saving || refreshPending) {
      refreshAgain = true;
      return;
    }
    refreshAgain = false;
    const generation = consentGeneration;
    refreshPending = fetch(config.endpoint, {
      credentials: "same-origin",
      cache: "no-store",
      headers: { "Accept": "application/json" },
    }).then(function (response) {
      if (!response.ok) throw new Error("Cookie preferences could not be refreshed");
      return response.json();
    }).then(function (result) {
      if (generation === consentGeneration && !saving &&
          Object.prototype.hasOwnProperty.call(result, "consent")) {
        applyConsent(result.consent);
      }
    }).catch(function () {
      // Preserve the last confirmed decision if the server cannot be reached.
    }).finally(function () {
      refreshPending = null;
      if (refreshAgain) refreshConsent();
    });
  }

  function clearErrors() {
    errors.forEach(function (element) {
      element.textContent = "";
      element.hidden = true;
    });
  }

  function openSettings(focusMaps) {
    if (saving || typeof dialog.showModal !== "function") return;
    clearErrors();
    preferencesInput.checked = allows("preferences");
    mapsInput.checked = allows("external_maps");
    analyticsInput.checked = allows("analytics");
    if (!dialog.open) {
      opener = document.activeElement;
      openedForMaps = focusMaps === true;
      dialog.showModal();
    }
    if (focusMaps === true) {
      mapsInput.focus();
    }
  }

  function setBusy(value) {
    saving = value;
    document.querySelectorAll("[data-cookie-save]").forEach(function (button) {
      button.disabled = value;
    });
    preferencesInput.disabled = value;
    mapsInput.disabled = value;
    analyticsInput.disabled = value;
    dialog.setAttribute("aria-busy", String(value));
    banner.setAttribute("aria-busy", String(value));
  }

  async function save(choice) {
    if (saving) return;
    let selection;
    if (choice === "accept") {
      selection = { preferences: true, external_maps: true, analytics: true };
    } else if (choice === "reject") {
      selection = { preferences: false, external_maps: false, analytics: false };
    } else if (choice === "selection") {
      selection = {
        preferences: preferencesInput.checked,
        external_maps: mapsInput.checked,
        analytics: analyticsInput.checked,
      };
    } else {
      return;
    }

    clearErrors();
    consentGeneration += 1;
    setBusy(true);
    try {
      const response = await fetch(config.endpoint, {
        method: "POST",
        credentials: "same-origin",
        headers: { "Content-Type": "application/json", "Accept": "application/json" },
        body: JSON.stringify(selection),
      });
      if (!response.ok) throw new Error("Cookie preferences could not be saved");
      const result = await response.json();
      if (!activeConsent(result.consent)) {
        throw new Error("Invalid cookie preferences response");
      }
      applyConsent(result.consent);
      if (dialog.open) dialog.close();
      status.textContent = config.ui.saved;
      if (channel) channel.postMessage({ type: "changed" });
    } catch (_) {
      const error = dialog.open ? errors[1] : errors[0];
      error.textContent = config.ui.save_error;
      error.hidden = false;
    } finally {
      setBusy(false);
      if (refreshAgain && !refreshPending) refreshConsent();
    }
  }

  document.addEventListener("click", function (event) {
    if (!(event.target instanceof Element)) return;
    const settingsButton = event.target.closest("[data-cookie-settings-open]");
    if (settingsButton) {
      event.preventDefault();
      openSettings(settingsButton.hasAttribute("data-cookie-maps-settings"));
      return;
    }
    const saveButton = event.target.closest("[data-cookie-save]");
    if (saveButton) {
      event.preventDefault();
      save(saveButton.dataset.cookieSave);
      return;
    }
    if (event.target.closest("[data-cookie-close]")) dialog.close();
  });

  dialog.addEventListener("close", function () {
    let target = opener && opener.isConnected && opener.getClientRects().length > 0
      ? opener : null;
    if (!target && openedForMaps) {
      target = Array.from(document.querySelectorAll("[data-map-open]")).find(function (element) {
        return element.getClientRects().length > 0;
      });
    }
    if (!target) {
      target = Array.from(document.querySelectorAll("[data-cookie-settings-open]:not([disabled])")).find(function (element) {
        return element.getClientRects().length > 0;
      });
    }
    if (target) target.focus({ preventScroll: true });
    opener = null;
    openedForMaps = false;
  });

  window.PortoBreakCookies = Object.freeze({
    allows: allows,
    openSettings: function () { openSettings(false); },
    openMapsSettings: function () { openSettings(true); },
  });

  applyConsent(config.consent, false);

  try {
    channel = new BroadcastChannel("portobreak-cookie-preferences");
    channel.addEventListener("message", function (event) {
      if (event.data && event.data.type === "changed") refreshConsent();
    });
  } catch (_) {
    // Visibility and history checks also work in browsers without this API.
  }
  window.addEventListener("pageshow", function (event) {
    if (event.persisted) refreshConsent();
  });
  document.addEventListener("visibilitychange", function () {
    if (document.visibilityState === "visible") refreshConsent();
  });

  document.querySelectorAll("[data-cookie-enhanced], [data-cookie-settings-open]").forEach(function (element) {
    element.hidden = false;
  });
})();
