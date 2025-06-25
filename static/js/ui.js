// static/js/ui.js
// Controla o toggle do menu em mobile

// Flag para verificar carga
window.uiLoaded = false;

window.addEventListener('DOMContentLoaded', () => {
  console.log('ui.js: DOMContentLoaded');
  const sidebar = document.querySelector('.sidebar');
  const main    = document.querySelector('.main-content');
  const btn     = document.getElementById('menuToggleMobile');

  if (!sidebar || !btn) {
    console.warn('ui.js: sidebar or button not found', { sidebar, btn });
    return;
  }

  window.uiLoaded = true;
  btn.addEventListener('click', () => {
    console.log('ui.js: toggle click');
    sidebar.classList.toggle('open');
    main.classList.toggle('shifted');
  });
});