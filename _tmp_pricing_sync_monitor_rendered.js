(() => {
  const apiUrl = "/pricing/api/sync-monitor";
  const detailApiUrl = "/pricing/api/sync-monitor/detail";
  const initialState = {"generated_at": "2026-03-26T12:00:00", "robots": [{"primeira_data": "2026-03-26", "robot": "R2-D2", "total_alojamentos": 3, "total_registos": 10, "ultima_data": "2026-03-29"}], "rows": [{"alojamento": "AAA", "primeira_data": "2026-03-26", "registos": 4, "robot": "R2-D2", "ultima_data": "2026-03-27"}]};
  const robotARegistosEl = document.getElementById('pszmRobotARegistos');
  const robotAAlojamentosEl = document.getElementById('pszmRobotAAlojamentos');
  const robotAIntervaloEl = document.getElementById('pszmRobotAIntervalo');
  const robotARateEl = document.getElementById('pszmRobotARate');
  const robotAEtaEl = document.getElementById('pszmRobotAEta');
  const generatedEl = document.getElementById('pszmGenerated');
  const cardGridEl = document.getElementById('pszmCardGrid');
  const reloadBtn = document.getElementById('pszmReload');
  const detailModalEl = document.getElementById('pszmDetailModal');
  const detailTitleEl = document.getElementById('pszmDetailTitle');
  const detailStatusEl = document.getElementById('pszmDetailStatus');
  const detailMetaEl = document.getElementById('pszmDetailMeta');
  const detailMonthsEl = document.getElementById('pszmDetailMonths');
  const detailModal = detailModalEl ? bootstrap.Modal.getOrCreateInstance(detailModalEl) : null;
  let monitorPollTimer = null;
  let syncLoadInFlight = false;
  let detailLoadInFlight = false;
  let monitorState = {
    rows: new Map(((initialState.rows || [])).map((row) => [`${row.robot}::${row.alojamento}`, row])),
    openedAtMs: null,
    snapshot: null,
    processed: {
      robotA: 0,
    },
  };

  function fmtDate(value) {
    if (!value) return '--';
    const [year, month, day] = String(value).slice(0, 10).split('-');
    if (!year || !month || !day) return value;
    return `${day}/${month}/${year}`;
  }

  function fmtInterval(firstDate, lastDate) {
    if (!firstDate && !lastDate) return '--';
    if (firstDate && lastDate && firstDate !== lastDate) return `${fmtDate(firstDate)} -> ${fmtDate(lastDate)}`;
    return fmtDate(firstDate || lastDate);
  }

  function escapeHtml(value) {
    return String(value ?? '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function renderDetailMeta(detail) {
    const badges = [
      `<span class="sz_badge sz_badge_info">${escapeHtml(detail.total_unsynced || 0)} dias por sincronizar</span>`,
      `<span class="sz_badge sz_badge_primary">${escapeHtml(detail.total_occupied || 0)} noites ocupadas</span>`,
      `<span class="sz_badge sz_badge_warning">${escapeHtml(fmtDate(detail.date_from))} -> ${escapeHtml(fmtDate(detail.date_to))}</span>`,
    ];
    detailMetaEl.innerHTML = badges.join('');
  }

  function renderDetailMonths(detail) {
    const months = Array.isArray(detail?.months) ? detail.months : [];
    if (!months.length) {
      detailMonthsEl.innerHTML = '<div class="pszm-empty">Sem detalhe disponivel.</div>';
      return;
    }
    detailMonthsEl.innerHTML = months.map((month) => {
      const cells = Array.isArray(month.cells) ? month.cells : [];
      const cellsHtml = cells.map((cell) => {
        if (cell.kind === 'pad') {
          return '<div class="pszm-month-cell is-pad"></div>';
        }
        const classes = ['pszm-month-cell'];
        if (cell.active) classes.push('is-active'); else classes.push('is-inactive');
        if (cell.occupied) classes.push('is-occupied');
        if (cell.unsynced) classes.push('is-unsynced');
        return `<div class="${classes.join(' ')}" title="${escapeHtml(cell.date || '')}"></div>`;
      }).join('');
      return `
        <article class="pszm-month-card">
          <div class="pszm-month-head">
            <div class="pszm-month-title">${escapeHtml(month.label || '')}</div>
            <div style="display:flex; gap:6px; align-items:center;">
              <span class="sz_badge ${Number(month.occupied_count || 0) > 0 ? 'sz_badge_primary' : 'sz_badge_ghost'}">${escapeHtml(month.occupied_count || 0)}</span>
              <span class="sz_badge ${Number(month.unsynced_count || 0) > 0 ? 'sz_badge_danger' : 'sz_badge_ghost'}">${escapeHtml(month.unsynced_count || 0)}</span>
            </div>
          </div>
          <div class="pszm-month-grid">${cellsHtml}</div>
        </article>
      `;
    }).join('');
  }

  async function openDetailModal(alojamento) {
    if (!alojamento || detailLoadInFlight || !detailModal) return;
    detailLoadInFlight = true;
    detailTitleEl.textContent = alojamento;
    detailStatusEl.textContent = 'A carregar detalhe...';
    detailMetaEl.innerHTML = '';
    detailMonthsEl.innerHTML = '<div class="pszm-empty">A carregar...</div>';
    detailModal.show();
    try {
      const response = await fetch(`${detailApiUrl}?alojamento=${encodeURIComponent(alojamento)}`, {
        credentials: 'same-origin',
        cache: 'no-store',
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.error || 'Erro ao ler detalhe do alojamento.');
      detailTitleEl.textContent = payload.alojamento || alojamento;
      detailStatusEl.textContent = payload.generated_at
        ? `Gerado em ${new Date(payload.generated_at).toLocaleString('pt-PT')}`
        : '--';
      renderDetailMeta(payload);
      renderDetailMonths(payload);
    } catch (error) {
      detailStatusEl.textContent = error.message || 'Erro ao carregar.';
      detailMonthsEl.innerHTML = `<div class="pszm-empty">${escapeHtml(error.message || 'Erro ao carregar.')}</div>`;
    } finally {
      detailLoadInFlight = false;
    }
  }

  function bumpElement(el) {
    if (!el) return;
    el.classList.remove('pszm-value-bump');
    void el.offsetWidth;
    el.classList.add('pszm-value-bump');
  }

  function updateTextWithBump(el, nextText) {
    if (!el) return;
    const normalized = String(nextText ?? '');
    if (el.textContent !== normalized) {
      el.textContent = normalized;
      bumpElement(el);
    } else {
      el.textContent = normalized;
    }
  }

  function renderCards(rows, emptyText) {
    const previousRows = monitorState.rows || new Map();
    if (!rows.length) {
      cardGridEl.innerHTML = `<div class="pszm-empty">${escapeHtml(emptyText)}</div>`;
      return;
    }
    cardGridEl.innerHTML = rows.map((row) => {
      const rowKey = `${row.robot}::${row.alojamento}`;
      const prev = previousRows.get(rowKey);
      const changed = !prev || Number(prev.registos || 0) !== Number(row.registos || 0);
      return `
        <article class="pszm-aloj-card${changed ? ' pszm-row-glow' : ''}" data-row-key="${escapeHtml(rowKey)}" data-alojamento="${escapeHtml(row.alojamento)}">
          <div class="pszm-aloj-card-head">
            <h2 class="pszm-aloj-title">${escapeHtml(row.alojamento)}</h2>
            <div class="pszm-aloj-registos">
              <span class="pszm-registos-value${changed ? ' pszm-value-bump' : ''}">${escapeHtml(row.registos)}</span>
            </div>
          </div>
          <div class="pszm-aloj-meta">
            <div class="pszm-aloj-meta-item">
              <div class="pszm-aloj-meta-label">Primeira data</div>
              <div class="pszm-aloj-meta-value">${escapeHtml(fmtDate(row.primeira_data))}</div>
            </div>
            <div class="pszm-aloj-meta-item">
              <div class="pszm-aloj-meta-label">Ultima data</div>
              <div class="pszm-aloj-meta-value">${escapeHtml(fmtDate(row.ultima_data))}</div>
            </div>
          </div>
        </article>
      `;
    }).join('');
  }

  function renderRows(rows) {
    const allRows = Array.isArray(rows) ? rows : [];
    const rowsA = allRows.filter((row) => row.robot === 'R2-D2');
    renderCards(rowsA, 'Sem precos por sincronizar para o R2-D2.');
    monitorState.rows = new Map(allRows.map((row) => [`${row.robot}::${row.alojamento}`, row]));
  }

  function buildSnapshot(payload) {
    const robots = Array.isArray(payload?.robots) ? payload.robots : [];
    const robotAData = robots.find((item) => item.robot === 'R2-D2') || {};
    return {
      atMs: Date.now(),
      robotARegistos: Number(robotAData.total_registos || 0),
    };
  }

  function formatSecondsPerReg(elapsedMs, processedCount) {
    const diff = Number(processedCount || 0);
    if (elapsedMs <= 0 || diff <= 0) return '--/reg';
    const seconds = (elapsedMs / 1000) / diff;
    if (!Number.isFinite(seconds) || seconds <= 0) return '--/reg';
    if (seconds < 10) return `${seconds.toFixed(1)}s/reg`;
    return `${Math.round(seconds)}s/reg`;
  }

  function calcSecondsPerReg(elapsedMs, processedCount) {
    const diff = Number(processedCount || 0);
    if (elapsedMs <= 0 || diff <= 0) return null;
    const seconds = (elapsedMs / 1000) / diff;
    if (!Number.isFinite(seconds) || seconds <= 0) return null;
    return seconds;
  }

  function formatEta(secondsPerReg, remainingRegs) {
    const remaining = Number(remainingRegs || 0);
    if (!Number.isFinite(secondsPerReg) || secondsPerReg <= 0 || remaining <= 0) return '--';
    const totalSeconds = Math.round(secondsPerReg * remaining);
    if (totalSeconds < 60) return '<1m';
    const hours = Math.floor(totalSeconds / 3600);
    const minutes = Math.ceil((totalSeconds % 3600) / 60);
    if (hours <= 0) return `${minutes}m`;
    if (minutes === 60) return `${hours + 1}h 0m`;
    return `${hours}h ${minutes}m`;
  }

  function updateRates(payload) {
    const previousSnapshot = monitorState.snapshot;
    const nextSnapshot = buildSnapshot(payload);
    if (!previousSnapshot) {
      monitorState.openedAtMs = nextSnapshot.atMs;
      robotARateEl.textContent = '--/reg';
      robotAEtaEl.textContent = '--';
      monitorState.snapshot = nextSnapshot;
      return;
    }

    monitorState.processed.robotA += Math.max(0, previousSnapshot.robotARegistos - nextSnapshot.robotARegistos);

    const elapsedMs = nextSnapshot.atMs - (monitorState.openedAtMs || nextSnapshot.atMs);
    const robotASecondsPerReg = calcSecondsPerReg(elapsedMs, monitorState.processed.robotA);
    robotARateEl.textContent = formatSecondsPerReg(elapsedMs, monitorState.processed.robotA);
    robotAEtaEl.textContent = formatEta(robotASecondsPerReg, nextSnapshot.robotARegistos);
    monitorState.snapshot = nextSnapshot;
  }

  function applyState(payload) {
    const robots = Array.isArray(payload?.robots) ? payload.robots : [];
    const rows = Array.isArray(payload?.rows) ? payload.rows : [];
    const robotAData = robots.find((item) => item.robot === 'R2-D2') || {};

    updateTextWithBump(robotARegistosEl, String(robotAData.total_registos || 0));
    robotAAlojamentosEl.textContent = `${robotAData.total_alojamentos || 0} alojamentos`;
    robotAIntervaloEl.textContent = fmtInterval(robotAData.primeira_data, robotAData.ultima_data);

    generatedEl.textContent = payload?.generated_at
      ? `Gerado em ${new Date(payload.generated_at).toLocaleString('pt-PT')}`
      : '--';

    renderRows(rows);
    updateRates(payload);
  }

  async function loadSyncMonitor({ silent = false } = {}) {
    if (syncLoadInFlight) return;
    syncLoadInFlight = true;
    if (!silent && reloadBtn) reloadBtn.disabled = true;
    try {
      const response = await fetch(apiUrl, {
        credentials: 'same-origin',
        cache: 'no-store',
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.error || 'Erro ao ler monitor de sync.');
      applyState(payload);
    } catch (error) {
      console.error('pricing sync monitor refresh failed', error);
    } finally {
      if (!silent && reloadBtn) reloadBtn.disabled = false;
      syncLoadInFlight = false;
    }
  }

  function ensurePolling() {
    if (monitorPollTimer) return;
    monitorPollTimer = window.setInterval(() => {
      loadSyncMonitor({ silent: true });
    }, 3000);
  }

  reloadBtn?.addEventListener('click', () => loadSyncMonitor());
  cardGridEl?.addEventListener('click', (event) => {
    const card = event.target.closest('.pszm-aloj-card');
    if (!card) return;
    openDetailModal(card.dataset.alojamento || '');
  });
  applyState(initialState);
  ensurePolling();
})();