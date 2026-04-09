// static/js/ui.js
(() => {
  const DECIMAL_SEPARATOR = ',';

  function getDecimalPlaces(input) {
    const places = Number(input?.dataset?.szDecimals);
    return Number.isFinite(places) ? Math.max(0, places) : 2;
  }

  function shouldEnhanceDecimalInput(input) {
    if (!input || input.dataset?.szNoDecimalMask === 'true') return false;
    if (input.dataset?.szDecimal === 'true') return true;
    if (input.dataset?.szInt === 'true') return false;
    if (!['sz_input', 'sz_input_number'].some(cls => input.classList.contains(cls))) return false;
    if ((input.type || '').toLowerCase() !== 'number') return false;
    const step = String(input.getAttribute('step') || input.step || '').trim().toLowerCase();
    return step !== '' && step !== '1' && step !== '1.0';
  }

  function parseDecimalString(value) {
    if (value === null || value === undefined) {
      return { sign: false, integers: '', decimals: '', hasDigits: false };
    }
    let text = String(value).trim();
    let sign = false;
    if (text.startsWith('-')) {
      sign = true;
      text = text.slice(1);
    }
    text = text.replace(/\./g, DECIMAL_SEPARATOR);
    const allowed = new RegExp(`[^0-9${DECIMAL_SEPARATOR}]`, 'g');
    text = text.replace(allowed, '');
    const parts = text.split(DECIMAL_SEPARATOR);
    const integers = parts.shift() || '';
    const decimals = parts.join('');
    const hasDigits = (integers + decimals).length > 0;
    return { sign, integers, decimals, hasDigits };
  }

  function formatDecimalString(parsed, places, { padDecimals = false, forceComma = false } = {}) {
    const { sign, integers, decimals, hasDigits } = parsed;
    if (!hasDigits) return '';
    const normalizedPlaces = Number.isFinite(places) ? Math.max(0, places) : 2;
    let integerPart = integers.replace(/^0+(?=\d)/, '');
    if (!integerPart) integerPart = '0';
    let decimalPart = decimals.slice(0, normalizedPlaces);
    if (padDecimals && normalizedPlaces > 0) {
      decimalPart = decimalPart.padEnd(normalizedPlaces, '0');
    }
    let result = integerPart;
    if (normalizedPlaces > 0 && (decimalPart.length > 0 || padDecimals || forceComma)) {
      result += DECIMAL_SEPARATOR + decimalPart;
    }
    return (sign ? '-' : '') + result;
  }

  function toDisplayDecimal(value, places) {
    const parsed = parseDecimalString(value);
    if (!parsed.hasDigits) return '';
    return formatDecimalString(parsed, places, {
      padDecimals: places > 0,
      forceComma: places > 0
    });
  }

  function setCaretPosition(input, pos) {
    if (typeof input.setSelectionRange === 'function') {
      requestAnimationFrame(() => input.setSelectionRange(pos, pos));
    }
  }

  function collectDigits(text = '') {
    return (text.match(/\d+/g) || []).join('');
  }

  function attachDecimalBehavior(input) {
    if (!shouldEnhanceDecimalInput(input) || input.dataset.szDecimalReady === '1') return;
    const decimalPlaces = getDecimalPlaces(input);
    input.dataset.szDecimal = 'true';
    input.dataset.szDecimalReady = '1';
    input.type = 'text';
    input.inputMode = 'decimal';
    input.autocomplete = 'off';

    input.addEventListener('keydown', (event) => {
      if (event.key === ',' || event.key === '.' || event.key === 'Decimal') {
        event.preventDefault();
        const value = input.value || '';
        const start = input.selectionStart ?? value.length;
        const existingComma = value.indexOf(DECIMAL_SEPARATOR);
        if (existingComma >= 0 && start > existingComma) {
          setCaretPosition(input, existingComma + 1);
          return;
        }
        const sign = value.trim().startsWith('-') ? '-' : '';
        const leftDigits = collectDigits(value.slice(0, start));
        const nextCommaIndex = value.indexOf(DECIMAL_SEPARATOR, start);
        const segmentForDecimals = nextCommaIndex >= 0 ? value.slice(start, nextCommaIndex) : value.slice(start);
        const rightDigits = collectDigits(segmentForDecimals);
        const paddedRight = decimalPlaces > 0
          ? rightDigits.slice(0, decimalPlaces).padEnd(decimalPlaces, '0')
          : '';
        let newValue = leftDigits || '0';
        if (decimalPlaces > 0) newValue += DECIMAL_SEPARATOR + paddedRight;
        input.value = (sign && newValue !== '0' ? sign : '') + newValue;
        const caretPos = input.value.indexOf(DECIMAL_SEPARATOR);
        if (caretPos >= 0) setCaretPosition(input, caretPos + 1);
        input.dispatchEvent(new Event('input', { bubbles: true }));
        return;
      }

      if (/^[0-9]$/.test(event.key)) {
        const value = input.value || '';
        const commaIndex = value.indexOf(DECIMAL_SEPARATOR);
        if (commaIndex >= 0) {
          const start = input.selectionStart ?? value.length;
          if (start > commaIndex) {
            event.preventDefault();
            const offset = Math.min(Math.max(start - commaIndex - 1, 0), Math.max(decimalPlaces - 1, 0));
            const decimals = value.slice(commaIndex + 1).padEnd(decimalPlaces, '0');
            const decimalArray = decimals.split('');
            decimalArray[offset] = event.key;
            input.value = value.slice(0, commaIndex + 1) + decimalArray.join('').slice(0, decimalPlaces);
            setCaretPosition(input, commaIndex + 1 + Math.min(offset + 1, decimalPlaces));
            input.dispatchEvent(new Event('input', { bubbles: true }));
          }
        }
      }
    });

    input.addEventListener('input', () => {
      const hadComma = (input.value || '').includes(DECIMAL_SEPARATOR);
      const parsed = parseDecimalString(input.value);
      const sanitized = parsed.hasDigits
        ? formatDecimalString(parsed, decimalPlaces, {
          padDecimals: hadComma && decimalPlaces > 0,
          forceComma: hadComma && decimalPlaces > 0
        })
        : '';
      if (sanitized !== input.value) {
        const cursor = input.selectionStart ?? sanitized.length;
        input.value = sanitized;
        setCaretPosition(input, Math.min(cursor, sanitized.length));
      }
    });

    input.addEventListener('blur', () => {
      if (!input.value) return;
      input.value = toDisplayDecimal(input.value, decimalPlaces);
    });

    if (input.value) {
      input.value = toDisplayDecimal(input.value, decimalPlaces);
    }
  }

  window.szEnhanceDecimalInputs = function(root = document) {
    const scope = root && typeof root.querySelectorAll === 'function' ? root : document;
    scope.querySelectorAll('input').forEach(attachDecimalBehavior);
  };
})();

function hoistBootstrapModals(root = document) {
  if (!document.body) return;
  const scope = root && typeof root.querySelectorAll === 'function' ? root : document;
  scope.querySelectorAll('.modal').forEach((modalEl) => {
    if (!(modalEl instanceof HTMLElement)) return;
    if (modalEl.parentElement === document.body) return;
    document.body.appendChild(modalEl);
  });
}

window.addEventListener('DOMContentLoaded', () => {
  window.szEnhanceDecimalInputs?.(document);
  hoistBootstrapModals(document);
  if (document.body && typeof MutationObserver === 'function') {
    const decimalObserver = new MutationObserver((mutations) => {
      mutations.forEach((mutation) => {
        mutation.addedNodes.forEach((node) => {
          if (!(node instanceof HTMLElement)) return;
          if (node.matches?.('.modal')) {
            hoistBootstrapModals(node.parentElement || document);
          } else if (node.querySelectorAll) {
            hoistBootstrapModals(node);
          }
          if (node.matches?.('input')) {
            window.szEnhanceDecimalInputs?.(node.parentElement || document);
          } else if (node.querySelectorAll) {
            window.szEnhanceDecimalInputs?.(node);
          }
        });
      });
    });
    decimalObserver.observe(document.body, { childList: true, subtree: true });
  }
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
