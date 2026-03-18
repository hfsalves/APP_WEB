// static/js/ui.js
window.addEventListener('DOMContentLoaded', () => {
  const sidebar = document.querySelector('.sidebar');
  const main    = document.querySelector('.main-content');
  const btn     = document.getElementById('menuToggleMobile');
  const collapseBtn = document.getElementById('sidebarCollapseToggle');
  const icon    = btn ? btn.querySelector('i') : null;
  const flyout = document.createElement('div');
  flyout.className = 'sidebar-flyout';
  document.body.appendChild(flyout);

  if (btn && sidebar) btn.addEventListener('click', () => {
    const open = sidebar.classList.toggle('open');
    if (main) main.classList.toggle('shifted');
    document.body.classList.toggle('sidebar-open', open);

    if (icon && open) {
      icon.classList.replace('fa-bars', 'fa-xmark');
    } else if (icon) {
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
  
  const pendingToastStorageKey = 'sz_pending_toasts';

  function flushPendingToasts() {
    try {
      const raw = sessionStorage.getItem(pendingToastStorageKey);
      if (!raw) return;
      sessionStorage.removeItem(pendingToastStorageKey);
      const items = JSON.parse(raw);
      if (!Array.isArray(items) || !items.length) return;
      window.setTimeout(() => {
        items.forEach(item => {
          if (!item || !item.message) return;
          window.showToast(item.message, item.type || 'success', item.options || {});
        });
      }, 120);
    } catch (_) {}
  }

  window.queueToastOnNextPage = function(message, type = 'success', options = {}) {
    try {
      const raw = sessionStorage.getItem(pendingToastStorageKey);
      const items = raw ? JSON.parse(raw) : [];
      const queue = Array.isArray(items) ? items : [];
      queue.push({ message, type, options });
      sessionStorage.setItem(pendingToastStorageKey, JSON.stringify(queue));
    } catch (_) {}
  };

  const isMobileMessageUi = () => {
    try {
      return window.matchMedia('(max-width: 768px)').matches
        || /Mobi|Android|iPhone|iPad|iPod/i.test(navigator.userAgent || '');
    } catch (_) {
      return false;
    }
  };

  let messageModalEl = null;
  let messageModalInstance = null;
  let messageModalState = null;

  function ensureMessageModal() {
    if (messageModalEl) return messageModalEl;

    messageModalEl = document.createElement('div');
    messageModalEl.className = 'modal fade sz_message_modal';
    messageModalEl.tabIndex = -1;
    messageModalEl.setAttribute('aria-hidden', 'true');
    messageModalEl.innerHTML = `
      <div class="modal-dialog modal-dialog-centered">
        <div class="modal-content">
          <div class="modal-header sz_modal_header">
            <div class="sz_message_modal_head">
              <div class="sz_message_modal_eyebrow" data-sz-message-eyebrow hidden></div>
              <h5 class="modal-title sz_modal_title" data-sz-message-title>Mensagem</h5>
            </div>
            <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Fechar"></button>
          </div>
          <div class="modal-body sz_modal_body">
            <div class="sz_message_modal_text" data-sz-message-text></div>
          </div>
          <div class="modal-footer sz_modal_footer" data-sz-message-footer></div>
        </div>
      </div>
    `;
    document.body.appendChild(messageModalEl);
    messageModalInstance = bootstrap.Modal.getOrCreateInstance(messageModalEl, {
      backdrop: true,
      keyboard: true
    });

    messageModalEl.addEventListener('hidden.bs.modal', () => {
      if (!messageModalState?.resolve) return;
      const action = messageModalEl.dataset.szMessageAction || messageModalState.dismissAction || 'dismiss';
      messageModalEl.dataset.szMessageAction = '';
      const resolve = messageModalState.resolve;
      messageModalState = null;
      resolve(action);
    });

    return messageModalEl;
  }

  function renderMessageModal(options = {}) {
    const modalEl = ensureMessageModal();
    const titleEl = modalEl.querySelector('[data-sz-message-title]');
    const eyebrowEl = modalEl.querySelector('[data-sz-message-eyebrow]');
    const textEl = modalEl.querySelector('[data-sz-message-text]');
    const footerEl = modalEl.querySelector('[data-sz-message-footer]');
    const intent = String(options.intent || 'info').trim().toLowerCase();
    const buttons = Array.isArray(options.buttons) && options.buttons.length
      ? options.buttons
      : [{ key: 'ok', label: 'OK', className: 'sz_button_primary' }];

    modalEl.classList.remove('sz_message_info', 'sz_message_success', 'sz_message_warning', 'sz_message_danger');
    modalEl.classList.add(`sz_message_${intent}`);

    titleEl.textContent = options.title || 'Mensagem';
    textEl.textContent = options.message || '';

    const eyebrow = (options.eyebrow || '').toString().trim();
    if (eyebrow) {
      eyebrowEl.hidden = false;
      eyebrowEl.textContent = eyebrow;
    } else {
      eyebrowEl.hidden = true;
      eyebrowEl.textContent = '';
    }

    footerEl.innerHTML = '';
    buttons.forEach((button, index) => {
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = `sz_button ${button.className || (index === 0 ? 'sz_button_primary' : 'sz_button_secondary')}`;
      btn.textContent = button.label || button.key || 'OK';
      btn.addEventListener('click', () => {
        modalEl.dataset.szMessageAction = button.key || 'ok';
        messageModalInstance.hide();
      });
      footerEl.appendChild(btn);
    });

    window.setTimeout(() => {
      footerEl.querySelector('.sz_button_primary, .sz_button_danger, .sz_button')?.focus();
    }, 30);
  }

  window.szMessage = function(options = {}) {
    if (isMobileMessageUi() || !window.bootstrap?.Modal) {
      return Promise.resolve('dismiss');
    }
    ensureMessageModal();
    if (messageModalState?.resolve) {
      const resolve = messageModalState.resolve;
      messageModalState = null;
      resolve('dismiss');
    }
    renderMessageModal(options);
    return new Promise((resolve) => {
      messageModalState = {
        resolve,
        dismissAction: options.dismissAction || 'dismiss'
      };
      messageModalEl.dataset.szMessageAction = '';
      messageModalInstance.show();
    });
  };

  window.szAlert = async function(message, options = {}) {
    if (isMobileMessageUi() || !window.bootstrap?.Modal) {
      window.alert(message);
      return 'ok';
    }
    return window.szMessage({
      title: options.title || 'Mensagem',
      eyebrow: options.eyebrow || '',
      message,
      intent: options.intent || 'info',
      buttons: [{ key: 'ok', label: options.okText || 'OK', className: options.okClassName || 'sz_button_primary' }],
      dismissAction: 'ok'
    });
  };

  window.szConfirm = async function(message, options = {}) {
    if (isMobileMessageUi() || !window.bootstrap?.Modal) {
      return window.confirm(message);
    }
    const result = await window.szMessage({
      title: options.title || 'Confirmar',
      eyebrow: options.eyebrow || '',
      message,
      intent: options.intent || 'warning',
      buttons: [
        { key: 'ok', label: options.okText || 'OK', className: options.okClassName || 'sz_button_primary' },
        { key: 'cancel', label: options.cancelText || 'Cancelar', className: options.cancelClassName || 'sz_button_secondary' }
      ],
      dismissAction: 'cancel'
    });
    return result === 'ok';
  };

  window.szYesNo = async function(message, options = {}) {
    if (isMobileMessageUi() || !window.bootstrap?.Modal) {
      return window.confirm(message);
    }
    const result = await window.szMessage({
      title: options.title || 'Confirmar',
      eyebrow: options.eyebrow || '',
      message,
      intent: options.intent || 'info',
      buttons: [
        { key: 'yes', label: options.yesText || 'Sim', className: options.yesClassName || 'sz_button_primary' },
        { key: 'no', label: options.noText || 'Não', className: options.noClassName || 'sz_button_secondary' }
      ],
      dismissAction: 'no'
    });
    return result === 'yes';
  };

  window.szConfirmDelete = async function(message, options = {}) {
    if (isMobileMessageUi() || !window.bootstrap?.Modal) {
      return window.confirm(message);
    }
    const result = await window.szMessage({
      title: options.title || 'Confirmar eliminação',
      eyebrow: options.eyebrow || 'Atenção!',
      message,
      intent: 'danger',
      buttons: [
        { key: 'delete', label: options.deleteText || 'Eliminar', className: 'sz_button_danger' },
        { key: 'cancel', label: options.cancelText || 'Cancelar', className: 'sz_button_secondary' }
      ],
      dismissAction: 'cancel'
    });
    return result === 'delete';
  };

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

  flushPendingToasts();
});
