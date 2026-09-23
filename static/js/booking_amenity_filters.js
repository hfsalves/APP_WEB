(function () {
  "use strict";

  var filters = Array.prototype.slice.call(document.querySelectorAll("[data-amenity-filter]"));
  if (!filters.length) return;

  filters.forEach(function (filter) {
    filter.addEventListener("toggle", function () {
      if (!filter.open) return;
      filters.forEach(function (other) {
        if (other !== filter) other.open = false;
      });
    });
  });

  document.addEventListener("pointerdown", function (event) {
    filters.forEach(function (filter) {
      if (filter.open && !filter.contains(event.target)) filter.open = false;
    });
  });

  document.addEventListener("keydown", function (event) {
    if (event.key !== "Escape") return;
    filters.forEach(function (filter) {
      if (!filter.open) return;
      filter.open = false;
      var summary = filter.querySelector("summary");
      if (summary) summary.focus();
    });
  });
})();
