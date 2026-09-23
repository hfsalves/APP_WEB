(function () {
  "use strict";
  const configNode = document.getElementById("booking-whatsapp-config");
  const button = document.querySelector("[data-whatsapp-open]");
  const dialog = document.querySelector("[data-whatsapp-dialog]");
  if (!configNode || !button || !dialog) return;

  let config;
  try { config = JSON.parse(configNode.textContent); } catch (_) { return; }
  if (!config || typeof config.url !== "string" || !config.url.startsWith("https://wa.me/")) return;

  function portugalMinute(moment) {
    try {
      const values = {};
      new Intl.DateTimeFormat("en-GB", {
        timeZone: config.timezone,
        hour: "2-digit",
        minute: "2-digit",
        hourCycle: "h23",
      }).formatToParts(moment).forEach(function (part) {
        if (part.type === "hour" || part.type === "minute") values[part.type] = Number(part.value);
      });
      if (!Number.isInteger(values.hour) || !Number.isInteger(values.minute)) throw new Error("time unavailable");
      return (values.hour === 24 ? 0 : values.hour) * 60 + values.minute;
    } catch (_) {
      return null;
    }
  }

  function supportIsOpen(moment) {
    const minute = portugalMinute(moment || new Date());
    if (minute === null) return config.server_open === true;
    return minute >= Number(config.open_minute) && minute < Number(config.close_minute);
  }

  function track(name, withinHours) {
    if (window.PortoBreakAnalytics && typeof window.PortoBreakAnalytics.track === "function") {
      window.PortoBreakAnalytics.track(name, { within_hours: withinHours === true });
    }
  }

  function openWhatsApp() {
    const opened = window.open(config.url, "_blank", "noopener,noreferrer");
    if (!opened) window.location.assign(config.url);
  }

  button.addEventListener("click", function () {
    const withinHours = supportIsOpen(new Date());
    track("WHATSAPP_CLICK", withinHours);
    if (withinHours) {
      openWhatsApp();
      return;
    }
    track("WHATSAPP_OUT_OF_HOURS", false);
    if (!dialog.open) dialog.showModal();
  });

  dialog.addEventListener("click", function (event) {
    if (event.target === dialog || event.target.closest("[data-whatsapp-close]")) dialog.close();
    const continuation = event.target.closest("[data-whatsapp-continue]");
    if (!continuation) return;
    track("WHATSAPP_CONTINUE", false);
    dialog.close();
    openWhatsApp();
  });

  function syncCookieOffset() {
    const banner = document.getElementById("booking-cookie-banner");
    const visible = banner && !banner.hidden && banner.getClientRects().length > 0;
    document.documentElement.style.setProperty(
      "--booking-whatsapp-bottom",
      visible ? String(Math.ceil(banner.getBoundingClientRect().height + 32)) + "px" : "24px"
    );
    scheduleCollisionCheck();
  }

  const compactViewport = window.matchMedia("(max-width: 980px)");
  const protectedMobileElements = [
    ".booking-detail-field",
    ".booking-panel-price",
    ".booking-price-breakdown",
    ".booking-calendar",
    ".booking-guest-grid",
    "[data-detail-reserve-action]",
    ".booking-pagination",
    ".booking-search",
  ].join(",");
  let collisionFrame = null;

  function rectanglesOverlap(first, second) {
    return first.left < second.right && first.right > second.left && first.top < second.bottom && first.bottom > second.top;
  }

  function syncMobileCollision() {
    collisionFrame = null;
    if (!compactViewport.matches || dialog.open) {
      button.classList.remove("is-collision-hidden");
      return;
    }

    button.classList.remove("is-collision-hidden");
    const buttonRect = button.getBoundingClientRect();
    const collision = Array.prototype.some.call(document.querySelectorAll(protectedMobileElements), function (element) {
      const rect = element.getBoundingClientRect();
      const isVisible = rect.width > 0 && rect.height > 0 && rect.bottom > 0 && rect.top < window.innerHeight;
      return isVisible && rectanglesOverlap(buttonRect, rect);
    });
    button.classList.toggle("is-collision-hidden", collision);
  }

  function scheduleCollisionCheck() {
    if (collisionFrame !== null) return;
    collisionFrame = window.requestAnimationFrame(syncMobileCollision);
  }

  syncCookieOffset();
  window.addEventListener("resize", function () {
    syncCookieOffset();
    scheduleCollisionCheck();
  }, { passive: true });
  window.addEventListener("scroll", scheduleCollisionCheck, { passive: true });
  window.addEventListener("portobreak:consent-changed", syncCookieOffset);
  if (typeof compactViewport.addEventListener === "function") compactViewport.addEventListener("change", scheduleCollisionCheck);
  const cookieBanner = document.getElementById("booking-cookie-banner");
  if (cookieBanner && window.MutationObserver) {
    new MutationObserver(syncCookieOffset).observe(cookieBanner, { attributes: true, attributeFilter: ["hidden"] });
  }
  if (cookieBanner && window.ResizeObserver) new ResizeObserver(syncCookieOffset).observe(cookieBanner);
  scheduleCollisionCheck();

  window.PortoBreakWhatsApp = { supportIsOpen: supportIsOpen };
})();
