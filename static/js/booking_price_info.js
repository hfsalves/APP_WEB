(function () {
  "use strict";
  const dialog = document.querySelector("[data-price-info-dialog]");
  if (!dialog) return;

  document.addEventListener("click", function (event) {
    const opener = event.target.closest("[data-price-info-open]");
    if (opener) {
      event.preventDefault();
      if (!dialog.open) dialog.showModal();
      return;
    }
    if (event.target.closest("[data-price-info-close]")) dialog.close();
  });

  dialog.addEventListener("click", function (event) {
    if (event.target === dialog) dialog.close();
  });
})();
