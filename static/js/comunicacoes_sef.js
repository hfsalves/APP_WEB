(function () {
  const initial = window.SIBA_COMMS_INITIAL || {};
  const state = {
    rows: [],
    selected: new Set(),
    loadingText: null,
    loading: false,
  };

  const els = {
    dateFrom: document.getElementById('sibaDateFrom'),
    dateTo: document.getElementById('sibaDateTo'),
    alojamento: document.getElementById('sibaAlojamento'),
    comunicada: document.getElementById('sibaComunicada'),
    refresh: document.getElementById('sibaRefresh'),
    rows: document.getElementById('sibaRows'),
    selectAll: document.getElementById('sibaSelectAll'),
    sendSelected: document.getElementById('sibaSendSelected'),
    clearSelection: document.getElementById('sibaClearSelection'),
    selectionInfo: document.getElementById('sibaSelectionInfo'),
    subtitle: document.getElementById('sibaSubtitle'),
    kpiTotal: document.getElementById('sibaKpiTotal'),
    kpiPending: document.getElementById('sibaKpiPending'),
    kpiReady: document.getElementById('sibaKpiReady'),
    kpiPartial: document.getElementById('sibaKpiPartial'),
  };

  function escapeHtml(value) {
    return String(value ?? '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function showToast(message, type = 'success', options = {}) {
    if (typeof window.showToast === 'function') {
      window.showToast(message, type, options);
      return;
    }
    if (message) window.alert(message);
  }

  function showLoading(message = 'A carregar...') {
    const overlay = document.getElementById('loadingOverlay');
    if (!overlay) return;
    const text = overlay.querySelector('.loading-text');
    if (text) {
      if (state.loadingText === null) state.loadingText = text.textContent;
      text.textContent = message;
    }
    state.loading = true;
    overlay.style.display = 'flex';
    overlay.setAttribute('aria-hidden', 'false');
    requestAnimationFrame(() => {
      overlay.style.opacity = '1';
    });
  }

  function hideLoading() {
    const overlay = document.getElementById('loadingOverlay');
    state.loading = false;
    if (!overlay) return;
    const text = overlay.querySelector('.loading-text');
    if (text && state.loadingText !== null) text.textContent = state.loadingText;
    overlay.style.opacity = '0';
    overlay.setAttribute('aria-hidden', 'true');
    setTimeout(() => {
      if (!state.loading) overlay.style.display = 'none';
    }, 250);
  }

  function fmtDate(value) {
    const raw = String(value || '').trim();
    if (!raw) return '';
    const parts = raw.slice(0, 10).split('-');
    if (parts.length !== 3) return raw;
    return `${parts[2]}/${parts[1]}/${parts[0]}`;
  }

  function badge(label, kind, icon = '') {
    const cls = {
      ok: 'sz_badge_success',
      warn: 'sz_badge_warning',
      danger: 'sz_badge_danger',
      info: 'sz_badge_info',
    }[kind] || 'sz_badge_info';
    const iconHtml = icon ? `<i class="fa-solid ${icon}"></i> ` : '';
    return `<span class="sz_badge ${cls}">${iconHtml}${escapeHtml(label)}</span>`;
  }

  function rowByStamp(stamp) {
    return state.rows.find((row) => String(row.rsstamp || '') === String(stamp || ''));
  }

  function updateSelectionUi() {
    const total = state.selected.size;
    const sendableSelected = Array.from(state.selected)
      .map(rowByStamp)
      .filter((row) => row && row.ready_to_send).length;

    if (els.selectionInfo) {
      els.selectionInfo.textContent = `${total} selecionada${total === 1 ? '' : 's'} (${sendableSelected} prontas).`;
    }
    if (els.sendSelected) els.sendSelected.disabled = sendableSelected === 0;
    if (els.clearSelection) els.clearSelection.disabled = total === 0;
    if (els.selectAll) {
      const sendableRows = state.rows.filter((row) => row.ready_to_send);
      els.selectAll.checked = sendableRows.length > 0 && sendableRows.every((row) => state.selected.has(row.rsstamp));
      els.selectAll.indeterminate = !els.selectAll.checked && sendableRows.some((row) => state.selected.has(row.rsstamp));
    }
  }

  function renderRows() {
    if (!els.rows) return;
    if (!state.rows.length) {
      els.rows.innerHTML = '<tr class="sz_table_row"><td colspan="8" class="sz_table_cell"><div class="siba-empty">Sem reservas para os filtros selecionados.</div></td></tr>';
      updateSelectionUi();
      return;
    }

    els.rows.innerHTML = state.rows.map((row) => {
      const blockers = Array.isArray(row.send_blockers) ? row.send_blockers : [];
      const blockedTitle = blockers.join(' ');
      const communicatedBadge = row.communicated
        ? badge(row.usrsef ? `Comunicada por ${row.usrsef}` : 'Comunicada', 'ok', 'fa-check')
        : badge('Por comunicar', 'warn', 'fa-clock');
      const dataKind = row.data_state === 'complete' ? 'ok' : (row.data_state === 'partial' ? 'warn' : 'danger');
      const dataIcon = row.data_state === 'complete' ? 'fa-user-check' : (row.data_state === 'partial' ? 'fa-user-pen' : 'fa-user-xmark');
      const credentialsBadge = row.credentials_ok
        ? badge('Configuradas', 'ok', 'fa-key')
        : badge('Em falta', 'danger', 'fa-key');
      const checked = state.selected.has(row.rsstamp) ? ' checked' : '';
      const pickDisabled = row.ready_to_send ? '' : ' disabled';
      const sendDisabled = row.ready_to_send ? '' : ' disabled';
      const trClass = row.ready_to_send ? 'sz_table_row' : 'sz_table_row siba-row-blocked';
      const openUrl = `/generic/rs_reservas_form/${encodeURIComponent(row.rsstamp)}?return_to=${encodeURIComponent('/reservas/comunicacoes-sef')}`;

      return `
        <tr class="${trClass}" data-rsstamp="${escapeHtml(row.rsstamp)}">
          <td class="sz_table_cell siba-pick-cell">
            <input type="checkbox" class="siba-row-check" data-rsstamp="${escapeHtml(row.rsstamp)}"${checked}${pickDisabled} aria-label="Selecionar reserva ${escapeHtml(row.reserva)}">
          </td>
          <td class="sz_table_cell">
            <div class="siba-reservation-main">
              <span class="siba-reservation-code">${escapeHtml(row.reserva || row.rsstamp)}</span>
              <span class="siba-reservation-guest">${escapeHtml(row.hospede || 'Sem nome de hóspede')}</span>
              ${row.pais ? `<span class="siba-muted-line">${escapeHtml(row.pais)}</span>` : ''}
            </div>
          </td>
          <td class="sz_table_cell">
            <div>${escapeHtml(fmtDate(row.datain))} ${row.horain ? `<span class="siba-muted-line">${escapeHtml(row.horain)}</span>` : ''}</div>
            <div class="siba-muted-line">Saída ${escapeHtml(fmtDate(row.dataout))}${row.horaout ? ` ${escapeHtml(row.horaout)}` : ''}</div>
          </td>
          <td class="sz_table_cell">${escapeHtml(row.alojamento)}</td>
          <td class="sz_table_cell"><div class="siba-status-stack">${communicatedBadge}</div></td>
          <td class="sz_table_cell">
            <div class="siba-status-stack">
              ${badge(row.data_label || 'Dados', dataKind, dataIcon)}
              <span class="siba-progress">${escapeHtml(row.complete_guests || 0)}/${escapeHtml(row.expected_guests || 0)} completos · ${escapeHtml(row.registered_guests || 0)} registos</span>
            </div>
          </td>
          <td class="sz_table_cell">
            <div class="siba-status-stack">
              ${credentialsBadge}
              ${row.credentials_ok ? '' : `<span class="siba-progress">${escapeHtml((row.credentials_missing || []).join(', '))}</span>`}
            </div>
          </td>
          <td class="sz_table_cell sz_text_right">
            <span class="siba-table-actions">
              <a class="sz_button sz_button_ghost" href="${openUrl}" title="Abrir reserva">
                <i class="fa-solid fa-arrow-up-right-from-square"></i>
              </a>
              <button type="button" class="sz_button sz_button_primary siba-send-one" data-rsstamp="${escapeHtml(row.rsstamp)}"${sendDisabled} title="${escapeHtml(blockedTitle || 'Enviar dados ao SIBA')}">
                <i class="fa-solid fa-paper-plane"></i>
                <span>Enviar</span>
              </button>
            </span>
          </td>
        </tr>
      `;
    }).join('');
    updateSelectionUi();
  }

  function renderSummary(summary = {}) {
    const total = Number(summary.total || 0);
    if (els.kpiTotal) els.kpiTotal.textContent = String(total);
    if (els.kpiPending) els.kpiPending.textContent = String(summary.pending || 0);
    if (els.kpiReady) els.kpiReady.textContent = String(summary.ready || 0);
    if (els.kpiPartial) els.kpiPartial.textContent = String(summary.partial || 0);
    if (els.subtitle) {
      els.subtitle.textContent = `${total} reserva${total === 1 ? '' : 's'} no período selecionado.`;
    }
  }

  async function loadAlojamentos() {
    if (!els.alojamento) return;
    try {
      const response = await fetch('/api/reservas/rs/config');
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data.error || 'Erro ao carregar alojamentos');
      const current = els.alojamento.value;
      const rows = Array.isArray(data.alojamentos) ? data.alojamentos : [];
      els.alojamento.innerHTML = '<option value="">Todos os alojamentos</option>' + rows
        .map((name) => `<option value="${escapeHtml(name)}">${escapeHtml(name)}</option>`)
        .join('');
      els.alojamento.value = current;
    } catch (error) {
      showToast(error.message || 'Erro ao carregar alojamentos.', 'warning');
    }
  }

  function queryString() {
    const params = new URLSearchParams();
    params.set('date_from', els.dateFrom?.value || '');
    params.set('date_to', els.dateTo?.value || '');
    params.set('alojamento', els.alojamento?.value || '');
    params.set('comunicada', els.comunicada?.value || 'pending');
    return params.toString();
  }

  async function loadRows(options = {}) {
    if (!els.rows) return;
    if (options.showLoading !== false) showLoading('A carregar comunicações...');
    try {
      const response = await fetch(`/api/reservas/siba/comunicacoes?${queryString()}`);
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data.error || 'Erro ao carregar comunicações');
      state.rows = Array.isArray(data.rows) ? data.rows : [];
      state.selected.clear();
      renderSummary(data.summary || {});
      renderRows();
    } catch (error) {
      state.rows = [];
      state.selected.clear();
      renderSummary({});
      els.rows.innerHTML = `<tr class="sz_table_row"><td colspan="8" class="sz_table_cell"><span class="sz_error">Erro: ${escapeHtml(error.message || 'Erro ao carregar')}</span></td></tr>`;
      updateSelectionUi();
      showToast(error.message || 'Erro ao carregar comunicações.', 'danger');
    } finally {
      if (options.showLoading !== false) hideLoading();
    }
  }

  function formatSendError(data) {
    const base = data?.error || 'Erro ao comunicar a reserva.';
    const missing = Array.isArray(data?.missing) ? data.missing.filter(Boolean) : [];
    if (!missing.length) return base;
    return `${base} ${missing.slice(0, 4).join(' ')}`;
  }

  async function sendReservation(row) {
    const response = await fetch(`/api/reservas/rs/${encodeURIComponent(row.rsstamp)}/siba/communicate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(formatSendError(data));
    return data;
  }

  async function sendOne(stamp) {
    const row = rowByStamp(stamp);
    if (!row) return;
    if (!row.ready_to_send) {
      showToast((row.send_blockers || []).join(' ') || 'Reserva não está pronta para envio.', 'warning', { delay: 5000 });
      return;
    }
    const confirmed = await (window.szConfirm?.(
      `Enviar a reserva ${row.reserva || row.rsstamp} ao AIMA/SEF?`,
      { title: 'Comunicar AIMA/SEF' }
    ) ?? Promise.resolve(window.confirm(`Enviar a reserva ${row.reserva || row.rsstamp} ao AIMA/SEF?`)));
    if (!confirmed) return;

    showLoading('A enviar AIMA/SEF...');
    try {
      const data = await sendReservation(row);
      showToast(data.message || 'Reserva comunicada ao SIBA.', 'success');
      await loadRows({ showLoading: false });
    } catch (error) {
      showToast(error.message || 'Erro ao comunicar reserva.', 'danger', { delay: 8000 });
    } finally {
      hideLoading();
    }
  }

  async function sendSelected() {
    const selectedRows = Array.from(state.selected).map(rowByStamp).filter(Boolean);
    const sendable = selectedRows.filter((row) => row.ready_to_send);
    if (!sendable.length) {
      showToast('Não há reservas selecionadas prontas para envio.', 'warning');
      return;
    }

    const skipped = selectedRows.length - sendable.length;
    const suffix = skipped > 0 ? ` (${skipped} ignorada${skipped === 1 ? '' : 's'} por não estar${skipped === 1 ? '' : 'em'} pronta${skipped === 1 ? '' : 's'}).` : '.';
    const confirmed = await (window.szConfirm?.(
      `Enviar ${sendable.length} reserva${sendable.length === 1 ? '' : 's'} ao AIMA/SEF${suffix}`,
      { title: 'Comunicar AIMA/SEF' }
    ) ?? Promise.resolve(window.confirm(`Enviar ${sendable.length} reserva${sendable.length === 1 ? '' : 's'} ao AIMA/SEF?`)));
    if (!confirmed) return;

    showLoading('A enviar AIMA/SEF...');
    let sent = 0;
    let failed = 0;
    for (const row of sendable) {
      const text = document.querySelector('#loadingOverlay .loading-text');
      if (text) text.textContent = `A enviar ${row.reserva || row.rsstamp}...`;
      try {
        await sendReservation(row);
        sent += 1;
      } catch (error) {
        failed += 1;
        console.warn('Erro ao comunicar SIBA', row.rsstamp, error);
      }
    }

    hideLoading();
    await loadRows({ showLoading: true });
    if (failed) {
      showToast(`${sent} enviada${sent === 1 ? '' : 's'}, ${failed} falhada${failed === 1 ? '' : 's'}.`, 'warning', { delay: 7000 });
    } else {
      showToast(`${sent} reserva${sent === 1 ? '' : 's'} comunicada${sent === 1 ? '' : 's'} ao SIBA.`, 'success');
    }
  }

  function bindEvents() {
    els.refresh?.addEventListener('click', () => loadRows());
    els.dateFrom?.addEventListener('change', () => loadRows());
    els.dateTo?.addEventListener('change', () => loadRows());
    els.alojamento?.addEventListener('change', () => loadRows());
    els.comunicada?.addEventListener('change', () => loadRows());
    els.sendSelected?.addEventListener('click', sendSelected);
    els.clearSelection?.addEventListener('click', () => {
      state.selected.clear();
      renderRows();
    });
    els.selectAll?.addEventListener('change', () => {
      const sendableRows = state.rows.filter((row) => row.ready_to_send);
      if (els.selectAll.checked) {
        sendableRows.forEach((row) => state.selected.add(row.rsstamp));
      } else {
        sendableRows.forEach((row) => state.selected.delete(row.rsstamp));
      }
      renderRows();
    });
    els.rows?.addEventListener('change', (event) => {
      const target = event.target;
      if (!target?.classList?.contains('siba-row-check')) return;
      const stamp = target.getAttribute('data-rsstamp') || '';
      if (target.checked) state.selected.add(stamp);
      else state.selected.delete(stamp);
      updateSelectionUi();
    });
    els.rows?.addEventListener('click', (event) => {
      const btn = event.target?.closest?.('.siba-send-one');
      if (!btn) return;
      sendOne(btn.getAttribute('data-rsstamp') || '');
    });
  }

  function initDates() {
    if (els.dateFrom) els.dateFrom.value = initial.date_from || '';
    if (els.dateTo) els.dateTo.value = initial.date_to || '';
  }

  document.addEventListener('DOMContentLoaded', async () => {
    initDates();
    bindEvents();
    showLoading('A carregar comunicações...');
    await loadAlojamentos();
    await loadRows({ showLoading: false });
    hideLoading();
  });
})();
