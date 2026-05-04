(function () {
  'use strict';

  const lanes = {
    pending: document.getElementById('grLanePending'),
    overdue: document.getElementById('grLaneOverdue'),
    today: document.getElementById('grLaneToday'),
    future: document.getElementById('grLaneFuture'),
    treated: document.getElementById('grLaneTreated'),
  };

  const counts = {
    pending: document.getElementById('grCountPending'),
    overdue: document.getElementById('grCountOverdue'),
    today: document.getElementById('grCountToday'),
    future: document.getElementById('grCountFuture'),
    treated: document.getElementById('grCountTreated'),
  };

  const summary = document.getElementById('grMonitorSummary');
  const refreshButton = document.getElementById('grMonitorRefresh');
  const modalEl = document.getElementById('grTaskModal');
  const modalTitle = document.getElementById('grModalTaskTitle');
  const modalMeta = document.getElementById('grModalTaskMeta');
  const modalDescription = document.getElementById('grModalTaskDescription');
  const modalStatus = document.getElementById('grModalTaskStatus');
  const modalStatusHint = document.getElementById('grModalStatusHint');
  const modalOpenTask = document.getElementById('grModalOpenTask');
  const modalSaveStatus = document.getElementById('grModalSaveStatus');
  let rowsCache = [];
  let statusOptions = [];
  let currentTask = null;

  function t(key, vars) {
    if (typeof window.t === 'function') return window.t(key, vars);
    return key;
  }

  function escapeHtml(value) {
    return String(value == null ? '' : value).replace(/[&<>"']/g, function (char) {
      return ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[char];
    });
  }

  function localDateIso(date) {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return year + '-' + month + '-' + day;
  }

  function todayIso() {
    return localDateIso(new Date());
  }

  function addDaysIso(days) {
    const now = new Date();
    const local = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    local.setDate(local.getDate() + days);
    return localDateIso(local);
  }

  function formatDate(isoDate) {
    if (!isoDate) return '';
    try {
      const date = new Date(String(isoDate) + 'T00:00:00');
      return new Intl.DateTimeFormat(window.SZ_LANGUAGE_TAG || undefined, {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
      }).format(date);
    } catch (_) {
      return String(isoDate);
    }
  }

  function formatNumber(value) {
    const number = Number(value || 0);
    if (!Number.isFinite(number) || Math.abs(number) < 0.0001) return '';
    try {
      return new Intl.NumberFormat(window.SZ_LANGUAGE_TAG || undefined, {
        maximumFractionDigits: 2,
      }).format(number);
    } catch (_) {
      return String(number);
    }
  }

  function classifyTask(task) {
    if (Number(task.treated || 0) === 1) return 'treated';
    const date = String(task.date || '');
    const today = todayIso();
    if (date && date < today) return 'overdue';
    if (date === today) return 'today';
    return 'future';
  }

  function cardHtml(task, lane) {
    const title = task.title || task.description || t('gr_monitor.no_description');
    const user = task.user_name || task.user_code || '';
    const company = task.company_name || '';
    const dateTime = [formatDate(task.date), task.time || ''].filter(Boolean).join(' · ');

    return [
      '<article class="gr-monitor-card gr-monitor-card--' + escapeHtml(lane || 'default') + '" role="button" tabindex="0" data-task-id="' + escapeHtml(task.id || '') + '">',
      '  <div class="gr-monitor-card-topline">',
      '    <div class="gr-monitor-card-company">' + escapeHtml(company) + '</div>',
      user ? '    <div class="gr-monitor-card-user-badge">' + escapeHtml(user) + '</div>' : '',
      '  </div>',
      '  <div class="gr-monitor-card-title">' + escapeHtml(title) + '</div>',
      dateTime ? '  <div class="gr-monitor-card-date">' + escapeHtml(dateTime) + '</div>' : '',
      '</article>',
    ].join('');
  }

  function taskMetaText(task) {
    return [
      task.user_name || task.user_code || '',
      formatDate(task.date),
      task.time || '',
      task.origin || '',
      task.location || '',
    ].filter(Boolean).join(' · ');
  }

  function renderStatusOptions(task) {
    if (!modalStatus) return;
    modalStatus.innerHTML = '';
    if (!statusOptions.length) {
      const opt = document.createElement('option');
      opt.value = '';
      opt.textContent = t('gr_monitor.no_status_options');
      modalStatus.appendChild(opt);
      modalStatus.disabled = true;
      if (modalSaveStatus) modalSaveStatus.disabled = true;
      if (modalStatusHint) modalStatusHint.textContent = t('gr_monitor.no_status_options');
      return;
    }
    statusOptions.forEach(function (status) {
      const opt = document.createElement('option');
      opt.value = String(status.code);
      opt.textContent = status.name || String(status.code);
      modalStatus.appendChild(opt);
    });
    modalStatus.value = String(task.status_code || '');
    modalStatus.disabled = false;
    if (modalSaveStatus) modalSaveStatus.disabled = !task.id;
    if (modalStatusHint) modalStatusHint.textContent = '';
  }

  function openTaskModal(task) {
    if (!task || !modalEl) return;
    currentTask = task;
    if (modalTitle) modalTitle.textContent = task.title || task.description || t('gr_monitor.no_description');
    if (modalMeta) modalMeta.textContent = taskMetaText(task);
    if (modalDescription) {
      modalDescription.textContent = task.description && task.description !== task.title ? task.description : '';
      modalDescription.hidden = !modalDescription.textContent;
    }
    renderStatusOptions(task);
    if (modalOpenTask) {
      if (task.id) {
        modalOpenTask.href = '/generic/form/TAREFAS/' + encodeURIComponent(task.id) + '?return_to=/gr_monitor';
        modalOpenTask.classList.remove('disabled');
        modalOpenTask.removeAttribute('aria-disabled');
      } else {
        modalOpenTask.href = '#';
        modalOpenTask.classList.add('disabled');
        modalOpenTask.setAttribute('aria-disabled', 'true');
      }
    }
    bootstrap.Modal.getOrCreateInstance(modalEl).show();
  }

  function attachCardHandlers() {
    document.querySelectorAll('.gr-monitor-card[data-task-id]').forEach(function (card) {
      const open = function () {
        const id = card.getAttribute('data-task-id') || '';
        const task = rowsCache.find(function (row) { return String(row.id || '') === id; });
        openTaskModal(task);
      };
      card.addEventListener('click', open);
      card.addEventListener('keydown', function (event) {
        if (event.key === 'Enter' || event.key === ' ') {
          event.preventDefault();
          open();
        }
      });
    });
  }

  function setLoading() {
    Object.keys(lanes).forEach(function (lane) {
      if (!lanes[lane]) return;
      lanes[lane].innerHTML = '<div class="gr-monitor-empty">' + escapeHtml(t('gr_monitor.loading')) + '</div>';
    });
  }

  function setEmpty(lane) {
    if (!lanes[lane]) return;
    const key = lane === 'pending' ? 'gr_monitor.empty_pending' : 'gr_monitor.empty_lane';
    lanes[lane].innerHTML = '<div class="gr-monitor-empty">' + escapeHtml(t(key)) + '</div>';
  }

  function render(rows) {
    rowsCache = Array.isArray(rows) ? rows : [];
    const grouped = { pending: [], overdue: [], today: [], future: [], treated: [] };
    rowsCache.forEach(function (task) {
      grouped[classifyTask(task)].push(task);
    });

    grouped.pending = [];

    Object.keys(lanes).forEach(function (lane) {
      if (!lanes[lane]) return;
      const items = grouped[lane] || [];
      if (counts[lane]) counts[lane].textContent = String(items.length);
      if (!items.length) {
        setEmpty(lane);
        return;
      }
      lanes[lane].innerHTML = items.map(function (item) { return cardHtml(item, lane); }).join('');
    });

    const total = grouped.overdue.length + grouped.today.length + grouped.future.length + grouped.treated.length;
    if (summary) {
      summary.textContent = t(total === 1 ? 'gr_monitor.task_count_one' : 'gr_monitor.task_count', { count: total });
    }
    attachCardHandlers();
  }

  async function loadTasks() {
    setLoading();
    if (refreshButton) refreshButton.disabled = true;
    try {
      const params = new URLSearchParams();
      params.set('start', addDaysIso(-30));
      params.set('end', addDaysIso(60));
      params.set('_', String(Date.now()));
      const requests = [
        fetch('/api/gr_planning/monitor/tasks?' + params.toString(), { headers: { Accept: 'application/json' } }),
        fetch('/api/gr_planning/monitor/status-options', { headers: { Accept: 'application/json' } }),
      ];
      const results = await Promise.all(requests);
      const response = results[0];
      const statusResponse = results[1];
      const payload = await response.json().catch(function () { return {}; });
      const statusPayload = await statusResponse.json().catch(function () { return {}; });
      if (!response.ok) throw new Error(payload.error || t('gr_monitor.load_error'));
      statusOptions = Array.isArray(statusPayload.rows) ? statusPayload.rows : [];
      render(payload.rows || []);
    } catch (error) {
      Object.keys(lanes).forEach(function (lane) {
        if (lanes[lane]) {
          lanes[lane].innerHTML = '<div class="gr-monitor-empty gr-monitor-empty-error">' + escapeHtml(error.message || t('gr_monitor.load_error')) + '</div>';
        }
      });
    } finally {
      if (refreshButton) refreshButton.disabled = false;
    }
  }

  if (modalSaveStatus) {
    modalSaveStatus.addEventListener('click', async function () {
      if (!currentTask || !currentTask.id || !modalStatus || !modalStatus.value) return;
      modalSaveStatus.disabled = true;
      try {
        const response = await fetch('/api/gr_planning/monitor/tasks/' + encodeURIComponent(currentTask.id) + '/status', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
          body: JSON.stringify({ status_code: Number(modalStatus.value) }),
        });
        const payload = await response.json().catch(function () { return {}; });
        if (!response.ok || payload.ok === false) throw new Error(payload.error || t('gr_monitor.status_save_error'));
        if (window.showToast) window.showToast(t('gr_monitor.status_saved'), 'success');
        bootstrap.Modal.getOrCreateInstance(modalEl).hide();
        await loadTasks();
      } catch (error) {
        if (window.showToast) window.showToast(error.message || t('gr_monitor.status_save_error'), 'danger');
        else window.alert(error.message || t('gr_monitor.status_save_error'));
      } finally {
        modalSaveStatus.disabled = false;
      }
    });
  }

  if (refreshButton) refreshButton.addEventListener('click', loadTasks);
  document.addEventListener('DOMContentLoaded', loadTasks);
})();
