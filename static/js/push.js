(function () {
  const tr = (key, vars) => (typeof window.t === 'function' ? window.t(key, vars) : key);
  const STATE = {
    registration: null,
    subscription: null,
    modal: null,
    summary: null,
    loading: false,
  };

  const els = {};

  function esc(text) {
    return String(text || '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  function currentUserStamp() {
    return String(window.CURRENT_USERSTAMP || '').trim();
  }

  function supportsPush() {
    return 'serviceWorker' in navigator && 'PushManager' in window && 'Notification' in window;
  }

  function isIosStandaloneMissing() {
    const ua = navigator.userAgent || '';
    const isIOS = /iPad|iPhone|iPod/i.test(ua);
    const isStandalone = window.matchMedia('(display-mode: standalone)').matches || window.navigator.standalone === true;
    return isIOS && !isStandalone;
  }

  function detectPlatform() {
    const ua = (navigator.userAgent || '').toLowerCase();
    if (ua.includes('iphone') || ua.includes('ipad') || ua.includes('ios')) return 'ios';
    if (ua.includes('android')) return 'android';
    if (ua.includes('windows') || ua.includes('mac') || ua.includes('linux')) return 'desktop';
    return 'unknown';
  }

  function urlBase64ToUint8Array(base64String) {
    const padding = '='.repeat((4 - (base64String.length % 4)) % 4);
    const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/');
    const rawData = atob(base64);
    return Uint8Array.from([...rawData].map((ch) => ch.charCodeAt(0)));
  }

  async function api(url, options = {}) {
    const response = await fetch(url, {
      credentials: 'same-origin',
      headers: {
        'Accept': 'application/json',
        ...(options.body ? { 'Content-Type': 'application/json' } : {}),
        ...(options.headers || {}),
      },
      ...options,
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(data.error || tr('push.http_error', { status: response.status }));
    }
    return data;
  }

  function setStatus(message, { error = false } = {}) {
    if (!els.status) return;
    els.status.textContent = message || '';
    els.status.classList.toggle('is-error', Boolean(error));
    els.status.classList.toggle('is-success', Boolean(message) && !error);
  }

  function setHint(message) {
    if (els.hint) {
      els.hint.textContent = message || '';
    }
  }

  async function ensureRegistration() {
    if (!supportsPush()) return null;
    if (!STATE.registration) {
      STATE.registration = await navigator.serviceWorker.register('/service-worker.js');
    }
    return STATE.registration;
  }

  async function refreshSummary() {
    const userstamp = currentUserStamp();
    if (!userstamp) return null;
    try {
      STATE.summary = await api(`/api/push/user/${encodeURIComponent(userstamp)}/summary`);
    } catch (_) {
      STATE.summary = null;
    }
    return STATE.summary;
  }

  function renderSummary() {
    if (!STATE.summary) {
      setStatus(tr('push.no_info'), { error: true });
      return;
    }
    const active = Number(STATE.summary.active_devices || 0);
    if (!supportsPush()) {
      setStatus(tr('push.unsupported'), { error: true });
    } else if (Notification.permission === 'granted' && active > 0) {
      setStatus(tr('push.active_summary', { active }));
    } else if (Notification.permission === 'denied') {
      setStatus(tr('push.blocked'), { error: true });
    } else {
      setStatus(active ? tr('push.registered_inactive', { active }) : tr('push.no_devices_active'));
    }

    if (isIosStandaloneMissing()) {
      setHint(tr('push.ios_hint'));
    } else {
      setHint('');
    }
  }

  async function fetchSubscription() {
    if (!supportsPush()) return null;
    const registration = await ensureRegistration();
    STATE.subscription = await registration.pushManager.getSubscription();
    return STATE.subscription;
  }

  async function activatePush() {
    if (!supportsPush()) {
      setStatus(tr('push.unsupported'), { error: true });
      return;
    }
    if (isIosStandaloneMissing()) {
      setStatus(tr('push.ios_install_first'), { error: true });
      return;
    }
    try {
      const permission = await Notification.requestPermission();
      if (permission !== 'granted') {
        setStatus(tr('push.permission_denied'), { error: true });
        return;
      }
      const registration = await ensureRegistration();
      const keyData = await api('/api/push/public-key');
      let subscription = await registration.pushManager.getSubscription();
      if (!subscription) {
        subscription = await registration.pushManager.subscribe({
          userVisibleOnly: true,
          applicationServerKey: urlBase64ToUint8Array(keyData.publicKey),
        });
      }
      const subJson = subscription.toJSON();
      await api('/api/push/subscribe', {
        method: 'POST',
        body: JSON.stringify({
          subscription: subJson,
          platform: detectPlatform(),
          userAgent: navigator.userAgent || '',
          deviceLabel: (els.deviceLabel?.value || '').trim(),
        }),
      });
      STATE.subscription = subscription;
      await refreshSummary();
      renderSummary();
    } catch (error) {
      setStatus(error.message || tr('push.activate_error'), { error: true });
    }
  }

  async function disablePush() {
    if (!supportsPush()) return;
    try {
      const subscription = await fetchSubscription();
      if (subscription) {
        await api('/api/push/unsubscribe', {
          method: 'POST',
          body: JSON.stringify({ endpoint: subscription.endpoint }),
        });
        await subscription.unsubscribe().catch(() => null);
      }
      STATE.subscription = null;
      await refreshSummary();
      renderSummary();
    } catch (error) {
      setStatus(error.message || tr('push.disable_error'), { error: true });
    }
  }

  async function sendSelfTest() {
    try {
      const result = await api('/api/push/test-self', { method: 'POST' });
      if (result.result?.status === 'NO_DEVICES') {
        setStatus(tr('push.no_devices'), { error: true });
        return;
      }
      setStatus(tr('push.test_sent'));
      await refreshSummary();
    } catch (error) {
      setStatus(error.message || tr('push.test_error'), { error: true });
    }
  }

  function openModal() {
    if (!els.modalEl) return;
    if (!STATE.modal) {
      STATE.modal = new bootstrap.Modal(els.modalEl);
    }
    refreshSummary().then(() => {
      renderSummary();
      STATE.modal.show();
    });
  }

  function bindEvents() {
    document.getElementById('btnOpenPushSettings')?.addEventListener('click', openModal);
    els.enable?.addEventListener('click', activatePush);
    els.disable?.addEventListener('click', disablePush);
    els.test?.addEventListener('click', sendSelfTest);
    els.modalEl?.addEventListener('shown.bs.modal', async () => {
      await fetchSubscription();
      await refreshSummary();
      renderSummary();
    });
  }

  async function boot() {
    els.modalEl = document.getElementById('pushSettingsModal');
    els.status = document.getElementById('pushSettingsStatus');
    els.deviceLabel = document.getElementById('pushDeviceLabel');
    els.enable = document.getElementById('btnPushEnable');
    els.disable = document.getElementById('btnPushDisable');
    els.test = document.getElementById('btnPushTestSelf');
    els.hint = document.getElementById('pushSupportHint');

    if (!currentUserStamp()) return;
    bindEvents();
    if (supportsPush()) {
      try {
        await ensureRegistration();
        await fetchSubscription();
      } catch (_) {}
    }
  }

  window.SZPush = {
    openModal,
    activatePush,
    disablePush,
    refreshSummary,
  };

  document.addEventListener('DOMContentLoaded', boot);
})();
