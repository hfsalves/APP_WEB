// static/js/ui.js
window.addEventListener('DOMContentLoaded', () => {
  const sidebar = document.querySelector('.sidebar');
  const main    = document.querySelector('.main-content');
  const btn     = document.getElementById('menuToggleMobile');
  const collapseBtn = document.getElementById('sidebarCollapseToggle');
  const icon    = btn.querySelector('i');
  const flyout = document.createElement('div');
  flyout.className = 'sidebar-flyout';
  document.body.appendChild(flyout);

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

  const applyCollapsed = (collapsed) => {
    document.body.classList.toggle('sidebar-collapsed', collapsed);
    if (collapseBtn) {
      const iconEl = collapseBtn.querySelector('i');
      if (iconEl) {
        iconEl.className = collapsed ? 'fa-solid fa-angles-right' : 'fa-solid fa-angles-left';
      }
    }
  };

  const collapseMq = window.matchMedia('(min-width: 769px)');
  const storedCollapsed = localStorage.getItem('sidebarCollapsed') === '1';
  if (collapseMq.matches && storedCollapsed) {
    applyCollapsed(true);
  }

  collapseMq.addEventListener('change', (e) => {
    if (!e.matches) {
      applyCollapsed(false);
    } else {
      const stored = localStorage.getItem('sidebarCollapsed') === '1';
      if (stored) applyCollapsed(true);
    }
  });

  if (collapseBtn) {
    collapseBtn.addEventListener('click', () => {
      const next = !document.body.classList.contains('sidebar-collapsed');
      if (next) {
        const activeLinks = sidebar ? sidebar.querySelectorAll('a.active') : [];
        activeLinks.forEach((link) => {
          link.dataset.wasActive = '1';
          link.classList.remove('active');
        });
        document.body.classList.add('sidebar-fading');
        document.body.classList.add('sidebar-icons-hidden');
        setTimeout(() => {
          applyCollapsed(true);
          document.body.classList.remove('sidebar-fading');
          requestAnimationFrame(() => {
            document.body.classList.add('sidebar-fading');
            document.body.classList.remove('sidebar-icons-hidden');
            setTimeout(() => {
              document.body.classList.remove('sidebar-fading');
              activeLinks.forEach((link) => {
                if (link.dataset.wasActive === '1') {
                  link.classList.add('active');
                  delete link.dataset.wasActive;
                }
              });
            }, 320);
          });
        }, 320);
      } else {
        const activeLinks = sidebar ? sidebar.querySelectorAll('a.active') : [];
        activeLinks.forEach((link) => {
          link.dataset.wasActive = '1';
          link.classList.remove('active');
        });
        document.body.classList.add('sidebar-fading');
        document.body.classList.add('sidebar-menu-hidden');
        setTimeout(() => {
          applyCollapsed(false);
          requestAnimationFrame(() => {
            document.body.classList.remove('sidebar-menu-hidden');
            setTimeout(() => {
              document.body.classList.remove('sidebar-fading');
              activeLinks.forEach((link) => {
                if (link.dataset.wasActive === '1') {
                  link.classList.add('active');
                  delete link.dataset.wasActive;
                }
              });
            }, 320);
          });
        }, 320);
      }
      localStorage.setItem('sidebarCollapsed', next ? '1' : '0');
      if (!next) {
        flyout.style.display = 'none';
      }
    });
  }

  const closeFlyout = () => {
    if (flyout.style.display !== 'none') {
      flyout.classList.remove('sidebar-flyout-show');
      setTimeout(() => {
        flyout.style.display = 'none';
        flyout.dataset.anchor = '';
      }, 320);
    } else {
      flyout.dataset.anchor = '';
    }
  };

  const openFlyout = (anchor) => {
    const href = anchor.getAttribute('href') || '';
    if (!href.startsWith('#')) return;
    const submenu = document.querySelector(href);
    if (!submenu) return;
    const items = Array.from(submenu.querySelectorAll('a'));
    if (!items.length) return;

    const title = anchor.getAttribute('title') || '';
    flyout.innerHTML = `
      ${title ? `<div class="flyout-title">${title}</div>` : ''}
      ${items.map(a => {
        const icon = a.getAttribute('data-icon');
        const iconHtml = icon ? `<i class="fa-solid ${icon} me-2"></i>` : '';
        return `<a href="${a.getAttribute('href') || '#'}">${iconHtml}${a.textContent.trim()}</a>`;
      }).join('')}
    `;

    const rect = anchor.getBoundingClientRect();
    const sidebarRect = sidebar.getBoundingClientRect();
    const left = sidebarRect.right + 8;
    let top = rect.top - 6;
    flyout.style.display = 'block';
    flyout.style.left = `${left}px`;
    flyout.style.top = `${top}px`;
    requestAnimationFrame(() => {
      flyout.classList.add('sidebar-flyout-show');
    });

    const flyoutRect = flyout.getBoundingClientRect();
    const maxTop = window.innerHeight - flyoutRect.height - 8;
    if (top > maxTop) {
      top = Math.max(8, maxTop);
      flyout.style.top = `${top}px`;
    }
    flyout.dataset.anchor = href;
  };

  document.querySelectorAll('.sidebar-group').forEach((group) => {
    group.addEventListener('click', (e) => {
      if (!document.body.classList.contains('sidebar-collapsed')) return;
      e.preventDefault();
      e.stopPropagation();
      const href = group.getAttribute('href') || '';
      if (flyout.dataset.anchor === href && flyout.style.display === 'block') {
        closeFlyout();
        return;
      }
      openFlyout(group);
    });
  });

  document.querySelectorAll('.sidebar-nav .collapse').forEach((submenu) => {
    submenu.addEventListener('show.bs.collapse', (e) => {
      if (document.body.classList.contains('sidebar-collapsed')) {
        e.preventDefault();
        e.stopPropagation();
      }
    });
  });

  document.addEventListener('click', (e) => {
    if (flyout.contains(e.target)) return;
    if (e.target.closest && e.target.closest('.sidebar-group')) return;
    closeFlyout();
  });

  window.addEventListener('resize', closeFlyout);
  window.addEventListener('scroll', closeFlyout, true);
  
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
