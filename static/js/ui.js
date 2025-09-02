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
  
  // Toast helper
  window.showToast = function(message, type = 'success', options = {}) {
    try {
      const container = document.getElementById('toastContainer');
      if (!container) return alert(message);

      const bgClass = (
        type === 'danger' ? 'text-bg-danger' :
        type === 'warning' ? 'text-bg-warning' :
        type === 'info' ? 'text-bg-info' :
        'text-bg-success'
      );

      const toast = document.createElement('div');
      toast.className = `toast align-items-center ${bgClass} border-0`;
      toast.setAttribute('role', 'status');
      toast.setAttribute('aria-live', 'polite');
      toast.setAttribute('aria-atomic', 'true');
      toast.innerHTML = `
        <div class="d-flex">
          <div class="toast-body">${message}</div>
          <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Fechar"></button>
        </div>`;
      container.appendChild(toast);
      const t = new bootstrap.Toast(toast, { delay: options.delay ?? 2500, autohide: options.autohide ?? true });
      toast.addEventListener('hidden.bs.toast', () => toast.remove());
      t.show();
    } catch (e) {
      try { console.warn('Toast fallback to alert:', e); } catch(_){ }
      alert(message);
    }
  };
});
