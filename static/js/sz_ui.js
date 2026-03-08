(function () {
  function onReady(fn) {
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", fn, { once: true });
      return;
    }
    fn();
  }

  onReady(function () {
    var page = document.querySelector("[data-sz-ui-page]");
    if (!page) {
      return;
    }

    var root = document.documentElement;
    var themeKey = "sz_theme_mode";
    var legacyThemeKey = "sz_ui_theme";
    var defaultTheme = "light";

    function setTheme(theme) {
      var safeTheme = ["light", "dark", "geek"].indexOf(theme) >= 0 ? theme : defaultTheme;
      root.setAttribute("data-sz-theme", safeTheme);

      try {
        localStorage.setItem(themeKey, safeTheme);
      } catch (_) {}

      var buttons = document.querySelectorAll("[data-sz-theme-set]");
      buttons.forEach(function (btn) {
        var isActive = btn.getAttribute("data-sz-theme-set") === safeTheme;
        btn.setAttribute("aria-pressed", isActive ? "true" : "false");
        btn.classList.toggle("sz_is_active", isActive);
        if (btn.classList.contains("sz_button") || btn.classList.contains("sz_button_primary") || btn.classList.contains("sz_button_secondary")) {
          btn.classList.toggle("sz_button_primary", isActive);
          btn.classList.toggle("sz_button_secondary", !isActive);
        }
        if (btn.classList.contains("btn")) {
          btn.classList.toggle("btn-primary", isActive);
          btn.classList.toggle("btn-outline-light", !isActive);
        }
      });
    }

    var storedTheme = null;
    try {
      storedTheme = localStorage.getItem(themeKey) || localStorage.getItem(legacyThemeKey);
    } catch (_) {}

    setTheme(storedTheme || root.getAttribute("data-sz-theme") || defaultTheme);

    document.querySelectorAll("[data-sz-theme-set]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        setTheme(btn.getAttribute("data-sz-theme-set"));
      });
    });

    var modal = page.querySelector("#szDemoModal");

    function closeModal() {
      if (!modal) {
        return;
      }
      modal.classList.remove("sz_is_open");
      modal.setAttribute("aria-hidden", "true");
    }

    function openModal() {
      if (!modal) {
        return;
      }
      modal.classList.add("sz_is_open");
      modal.setAttribute("aria-hidden", "false");
    }

    page.querySelectorAll("[data-sz-modal-open]").forEach(function (btn) {
      btn.addEventListener("click", openModal);
    });

    page.querySelectorAll("[data-sz-modal-close]").forEach(function (btn) {
      btn.addEventListener("click", closeModal);
    });

    if (modal) {
      modal.addEventListener("click", function (event) {
        if (event.target === modal) {
          closeModal();
        }
      });
    }

    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape") {
        closeModal();
      }
    });

    var tooltip = document.createElement("div");
    tooltip.className = "sz_demo_tooltip sz_hidden";
    tooltip.innerHTML = '<div class="sz_demo_tooltip_code"></div><span class="sz_demo_copy_hint">click to copy</span>';
    page.appendChild(tooltip);

    var tooltipCode = tooltip.querySelector(".sz_demo_tooltip_code");
    var activeTarget = null;

    function positionTooltip(event) {
      var x = event.clientX + 14;
      var y = event.clientY + 16;
      var maxX = window.innerWidth - tooltip.offsetWidth - 10;
      var maxY = window.innerHeight - tooltip.offsetHeight - 10;

      tooltip.style.left = Math.max(10, Math.min(x, maxX)) + "px";
      tooltip.style.top = Math.max(10, Math.min(y, maxY)) + "px";
    }

    function showTooltip(target, event) {
      var classLabel = target.getAttribute("data-sz-class");
      if (!classLabel) {
        return;
      }
      activeTarget = target;
      tooltipCode.textContent = classLabel;
      tooltip.classList.remove("sz_hidden");
      positionTooltip(event);
    }

    function hideTooltip() {
      activeTarget = null;
      tooltip.classList.add("sz_hidden");
    }

    page.querySelectorAll("[data-sz-class]").forEach(function (el) {
      el.classList.add("sz_demo_hover");

      el.addEventListener("mouseenter", function (event) {
        showTooltip(el, event);
      });

      el.addEventListener("mousemove", function (event) {
        if (!activeTarget) {
          return;
        }
        positionTooltip(event);
      });

      el.addEventListener("mouseleave", hideTooltip);

      el.addEventListener("click", function () {
        var classLabel = el.getAttribute("data-sz-class");
        if (!classLabel) {
          return;
        }

        if (navigator.clipboard && navigator.clipboard.writeText) {
          navigator.clipboard.writeText(classLabel).catch(function () {
            /* ignore clipboard write errors */
          });
        }

        tooltip.querySelector(".sz_demo_copy_hint").textContent = "copied";
        window.setTimeout(function () {
          var hint = tooltip.querySelector(".sz_demo_copy_hint");
          if (hint) {
            hint.textContent = "click to copy";
          }
        }, 700);
      });
    });
  });
})();
