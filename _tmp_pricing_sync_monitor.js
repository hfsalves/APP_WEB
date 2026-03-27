(() => {
  const apiUrl = {{ url_for('pricing.pricing_api_sync_monitor') | tojson }};
  const initialState = {{ (initial_state or {}) | tojson }};
  const totalRegistosEl = document.getElementById('pszmTotalRegistos');
  const totalAlojamentosEl = document.getElementById('pszmTotalAlojamentos');
  const totalIntervaloEl = document.getElementById('pszmTotalIntervalo');
  const robotARegistosEl = document.getElementById('pszmRobotARegistos');
  const robotAAlojamentosEl = document.getElementById('pszmRobotAAlojamentos');
  const robotAIntervaloEl = document.getElementById('pszmRobotAIntervalo');
  const robotBRegistosEl = document.getElementById('pszmRobotBRegistos');
  const robotBAlojamentosEl = document.getElementById('pszmRobotBAlojamentos');
  const robotBIntervaloEl = document.getElementById('pszmRobotBIntervalo');
  const generatedEl = document.getElementById('pszmGenerated');
  const tableBodyAEl = document.getElementById('pszmTableBodyA');
  const tableBodyBEl = document.getElementById('pszmTableBodyB');
  const reloadBtn = document.getElementById('pszmReload');
  let monitorPollTimer = null;
  let syncLoadInFlight = false;
  let monitorState = {
    rows: new Map(((initialState.rows || [])).map((row) => [`${row.robot}::${row.alojamento}`, row])),
  };

  function fmtDate(value) {
    if (!value) return '?';
    const [year, month, day] = String(value).slice(0, 10).split('-');
    if (!year || !month || !day) return value;
    return `${day}/${month}/${year}`;
  }

  function fmtInterval(firstDate, lastDate) {
    if (!firstDate && !lastDate) return '?';
    if (firstDate && lastDate && firstDate !== lastDate) return `${fmtDate(firstDate)} ? ${fmtDate(lastDate)}`;
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

  function renderTableRows(tableBodyEl, rows, emptyText) {
    const previousRows = monitorState.rows || new Map();
    if (!rows.length) {
      tableBodyEl.innerHTML = `<tr><td colspan="4" class="pszm-empty">${escapeHtml(emptyText)}</td></tr>`;
      return;
    }
    tableBodyEl.innerHTML = rows.map((row) => {
      const rowKey = `${row.robot}::${row.alojamento}`;
      const prev = previousRows.get(rowKey);
      const changed = !prev || Number(prev.registos || 0) !== Number(row.registos || 0);
      return `
        <tr data-row-key="${escapeHtml(rowKey)}">
          <td>${escapeHtml(row.alojamento)}</td>
          <td class="is-number"><span class="pszm-registos-value${changed ? ' pszm-value-bump' : ''}">${escapeHtml(row.registos)}</span></td>
          <td>${escapeHtml(fmtDate(row.primeira_data))}</td>
          <td>${escapeHtml(fmtDate(row.ultima_data))}</td>
        </tr>
      `;
    }).join('');
  }

  function renderRows(rows) {
    const allRows = Array.isArray(rows) ? rows : [];
    const rowsA = allRows.filter((row) => row.robot === 'R2-D2');
    const rowsB = allRows.filter((row) => row.robot === 'C-3PO');
    renderTableRows(tableBodyAEl, rowsA, 'Sem pre?os por sincronizar para o R2-D2.');
    renderTableRows(tableBodyBEl, rowsB, 'Sem pre?os por sincronizar para o C-3PO.');
    monitorState.rows = new Map(allRows.map((row) => [`${row.robot}::${row.alojamento}`, row]));
  }

  function applyState(payload) {
    const totals = payload?.totals || {};
    const robots = Array.isArray(payload?.robots) ? payload.robots : [];
    const rows = Array.isArray(payload?.rows) ? payload.rows : [];
    const robotAData = robots.find((item) => item.robot === 'R2-D2') || {};
    const robotBData = robots.find((item) => item.robot === 'C-3PO') || {};

    updateTextWithBump(totalRegistosEl, String(totals.total_registos || 0));
    totalAlojamentosEl.textContent = `${totals.total_alojamentos || 0} alojamentos`;
    totalIntervaloEl.textContent = fmtInterval(totals.primeira_data, totals.ultima_data);

    updateTextWithBump(robotARegistosEl, String(robotAData.total_registos || 0));
    robotAAlojamentosEl.textContent = `${robotAData.total_alojamentos || 0} alojamentos`;
    robotAIntervaloEl.textContent = fmtInterval(robotAData.primeira_data, robotAData.ultima_data);

    updateTextWithBump(robotBRegistosEl, String(robotBData.total_registos || 0));
    robotBAlojamentosEl.textContent = `${robotBData.total_alojamentos || 0} alojamentos`;
    robotBIntervaloEl.textContent = fmtInterval(robotBData.primeira_data, robotBData.ultima_data);

    generatedEl.textContent = payload?.generated_at
      ? `Gerado em ${new Date(payload.generated_at).toLocaleString('pt-PT')}`
      : '?';

    renderRows(rows);
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
    }, 15000);
  }

  reloadBtn?.addEventListener('click', () => loadSyncMonitor());
  applyState(initialState);
  ensurePolling();
})();