(() => {
  "use strict";
  const menus = Array.from(document.querySelectorAll("[data-booking-navigation-menu]"));

  menus.forEach((menu) => {
    menu.addEventListener("toggle", () => {
      if (!menu.open) return;
      menus.forEach((other) => {
        if (other !== menu) other.open = false;
      });
    });
  });

  document.addEventListener("click", (event) => {
    menus.forEach((menu) => {
      if (menu.open && !menu.contains(event.target)) menu.open = false;
    });
  });

  document.addEventListener("keydown", (event) => {
    if (event.key !== "Escape") return;
    const openMenu = menus.find((menu) => menu.open);
    if (!openMenu) return;
    openMenu.open = false;
    openMenu.querySelector("summary").focus({ preventScroll: true });
    event.preventDefault();
  });
})();
