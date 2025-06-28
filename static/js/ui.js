// static/js/ui.js
window.addEventListener('DOMContentLoaded', () => {
  const sidebar = document.querySelector('.sidebar');
  const main    = document.querySelector('.main-content');
  const btn     = document.getElementById('menuToggleMobile');
  const icon    = btn.querySelector('i');

  btn.addEventListener('click', () => {
    const open = sidebar.classList.toggle('open');
    main.classList.toggle('shifted');
    document.body.classList.toggle('sidebar-open', open);

    if (open) {
      icon.classList.replace('fa-bars', 'fa-xmark');
    } else {
      icon.classList.replace('fa-xmark', 'fa-bars');
    }
  });
});
