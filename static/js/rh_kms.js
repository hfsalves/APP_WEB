(function () {
  const initial = window.KMS_INITIAL_CONTEXT || {};
  const monthSelect = document.getElementById('kmsMes');
  const yearSelect = document.getElementById('kmsAno');
  const userSelect = document.getElementById('kmsUtilizador');
  const tableBody = document.getElementById('kmsTableBody');
  const totalKmsEl = document.getElementById('kmsTotalKms');
  const totalValorEl = document.getElementById('kmsTotalValor');
  const valorKmEl = document.getElementById('kmsValorKm');
  const statusEl = document.getElementById('kmsStatus');
  const refreshBtn = document.getElementById('kmsAtualizar');
  const currentMonthBtn = document.getElementById('kmsMesAtual');
  const pdfBtn = document.getElementById('kmsGerarPdf');

  const state = {
    mes: Number(initial.mes || new Date().getMonth() + 1),
    ano: Number(initial.ano || new Date().getFullYear()),
    utilizador: String(initial.utilizador || initial.current_user || '').trim(),
    currentUser: String(initial.current_user || '').trim(),
    isAdmin: Boolean(initial.is_admin),
    users: Array.isArray(initial.users) ? initial.users : [],
    rows: [],
    busy: false,
    pending: new Set()
  };

  const monthNames = [
    'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
    'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'
  ];

  function escapeHtml(value) {
    return String(value ?? '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function formatKm(value, withUnit = true) {
    const amount = Number(value || 0);
    const text = amount.toLocaleString('pt-PT', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    return withUnit ? `${text} km` : text;
  }

  function formatEuro(value) {
    const amount = Number(value || 0);
    return `${amount.toLocaleString('pt-PT', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} €`;
  }

  function setStatus(message, isError = false) {
    if (!statusEl) return;
    statusEl.textContent = message || '';
    statusEl.className = isError ? 'sz_text_danger' : 'sz_text_muted';
  }

  async function fetchJson(url, options) {
    const response = await fetch(url, options || {});
    const data = await response.json().catch(() => ({}));
    if (!response.ok || data.ok === false || data.error) {
      const message = data.message || data.error || 'Erro inesperado.';
      const error = new Error(message);
      error.status = response.status;
      error.payload = data;
      throw error;
    }
    return data;
  }

  function buildMonthOptions() {
    monthSelect.innerHTML = monthNames.map((name, index) => {
      const month = index + 1;
      const selected = month === state.mes ? ' selected' : '';
      return `<option value="${month}"${selected}>${name}</option>`;
    }).join('');
  }

  function buildYearOptions() {
    const currentYear = new Date().getFullYear();
    const years = [];
    for (let year = currentYear - 3; year <= currentYear + 2; year += 1) {
      years.push(year);
    }
    if (!years.includes(state.ano)) {
      years.push(state.ano);
      years.sort((a, b) => a - b);
    }
    yearSelect.innerHTML = years.map((year) => {
      const selected = year === state.ano ? ' selected' : '';
      return `<option value="${year}"${selected}>${year}</option>`;
    }).join('');
  }

  function buildUserOptions() {
    userSelect.innerHTML = state.users.map((user) => {
      const login = String(user.login || '').trim();
      const label = String(user.nome || '').trim() || login;
      const selected = login.toUpperCase() === state.utilizador.toUpperCase() ? ' selected' : '';
      return `<option value="${escapeHtml(login)}"${selected}>${escapeHtml(label)}</option>`;
    }).join('');
    userSelect.disabled = !state.isAdmin;
  }

  function renderSummary(data) {
    totalKmsEl.textContent = formatKm(data.total_kms);
    totalValorEl.textContent = formatEuro(data.total_valor);
    valorKmEl.textContent = `${formatEuro(data.valor_km)} / km`;
  }

  function findRow(rsstamp) {
    return state.rows.find((row) => String(row.rsstamp || '').trim() === String(rsstamp || '').trim()) || null;
  }

  function applyRowState(rsstamp, nextState) {
    const row = findRow(rsstamp);
    if (!row || !nextState) return;
    row.estado = nextState.estado || row.estado;
    row.estado_label = nextState.estado_label || row.estado_label;
    row.checked = Boolean(nextState.checked);
    row.disabled = Boolean(nextState.disabled);
    row.marcado_por = nextState.marcado_por || '';
    row.marcado_por_nome = nextState.marcado_por_nome || '';
  }

  function applyTotals(totalKms, totalValor) {
    totalKmsEl.textContent = formatKm(totalKms);
    totalValorEl.textContent = formatEuro(totalValor);
  }

  function badgeClass(row) {
    if (row.estado === 'mine') return 'sz_badge_success';
    if (row.estado === 'other') return 'sz_badge_warning';
    return 'sz_badge_info';
  }

  function renderRows() {
    if (!Array.isArray(state.rows) || !state.rows.length) {
      tableBody.innerHTML = `
        <tr class="sz_table_row">
          <td colspan="8" class="sz_table_cell sz_kms_empty">Sem reservas para este mês.</td>
        </tr>
      `;
      return;
    }

    tableBody.innerHTML = state.rows.map((row) => {
      const pending = state.pending.has(row.rsstamp);
      const disabled = row.disabled || pending;
      const checked = row.checked ? ' checked' : '';
      const disabledAttr = disabled ? ' disabled' : '';
      const rowClass = row.estado === 'other' ? ' sz_kms_table_row_blocked' : '';
      const hospede = row.hospede ? escapeHtml(row.hospede) : '<span class="sz_text_muted">-</span>';
      const distanceText = row.has_distance ? formatKm(row.distancia) : '<span class="sz_text_muted">-</span>';
      const stateMeta = row.marcado_por_nome
        ? `<span class="sz_kms_table_meta">${row.estado === 'other' ? 'Marcado por' : 'Utilizador'}: ${escapeHtml(row.marcado_por_nome)}</span>`
        : '';
      const registoLabel = row.estado === 'mine' ? 'Registado' : (row.estado === 'other' ? 'Indisponível' : 'Marcar');
      return `
        <tr class="sz_table_row${rowClass}" data-rsstamp="${escapeHtml(row.rsstamp)}" data-disabled="${disabled ? '1' : '0'}">
          <td class="sz_table_cell">
            <label class="sz_checkbox sz_kms_table_toggle">
              <input
                type="checkbox"
                data-rsstamp="${escapeHtml(row.rsstamp)}"
                ${checked}
                ${disabledAttr}
              >
              <span>${registoLabel}</span>
            </label>
          </td>
          <td class="sz_table_cell">${escapeHtml(row.data_checkin || '')}</td>
          <td class="sz_table_cell">
            ${escapeHtml(row.reserva_codigo || row.rsstamp || '')}
            <span class="sz_kms_table_meta">${escapeHtml(row.ccusto || '')}</span>
          </td>
          <td class="sz_table_cell">${escapeHtml(row.alojamento || '')}</td>
          <td class="sz_table_cell">${hospede}</td>
          <td class="sz_table_cell sz_text_right">${distanceText}</td>
          <td class="sz_table_cell sz_text_right">${formatKm(row.kms)}</td>
          <td class="sz_table_cell">
            <span class="sz_badge ${badgeClass(row)}">${escapeHtml(row.estado_label || '')}</span>
            ${stateMeta}
          </td>
        </tr>
      `;
    }).join('');
  }

  async function loadRows() {
    if (state.busy) return;
    state.busy = true;
    if (refreshBtn) refreshBtn.disabled = true;
    if (pdfBtn) pdfBtn.disabled = true;
    setStatus('A carregar...');
    tableBody.innerHTML = `
      <tr class="sz_table_row">
        <td colspan="8" class="sz_table_cell sz_text_muted">A carregar...</td>
      </tr>
    `;

    try {
      const params = new URLSearchParams({
        mes: String(state.mes),
        ano: String(state.ano),
        utilizador: state.utilizador
      });
      const data = await fetchJson(`/api/kms/reservas?${params.toString()}`);
      state.rows = Array.isArray(data.rows) ? data.rows : [];
      state.utilizador = String(data.utilizador || state.utilizador || '').trim();
      renderSummary(data);
      renderRows();
      setStatus('Os registos são gravados automaticamente ao clicar.');
    } catch (error) {
      state.rows = [];
      renderRows();
      renderSummary({ total_kms: 0, total_valor: 0, valor_km: 0 });
      setStatus(error.message || 'Erro ao carregar.', true);
      if (typeof window.showToast === 'function') {
        window.showToast(error.message || 'Erro ao carregar kms.', 'danger');
      }
    } finally {
      state.busy = false;
      if (refreshBtn) refreshBtn.disabled = false;
      if (pdfBtn) pdfBtn.disabled = false;
    }
  }

  async function toggleReservation(rsstamp, checked) {
    if (!rsstamp || state.pending.has(rsstamp)) return;
    state.pending.add(rsstamp);
    renderRows();
    setStatus('A gravar...');
    try {
      const endpoint = checked ? '/api/kms/marcar' : '/api/kms/desmarcar';
      const data = await fetchJson(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          reserva: rsstamp,
          mes: state.mes,
          ano: state.ano,
          utilizador: state.utilizador
        })
      });
      if (typeof window.showToast === 'function') {
        window.showToast(data.message || (checked ? 'Reserva registada.' : 'Reserva removida.'), 'success');
      }
      applyRowState(rsstamp, data.state || {});
      applyTotals(data.total_kms || 0, data.total_valor || 0);
      renderRows();
      setStatus(data.message || 'Registo atualizado.');
    } catch (error) {
      if (typeof window.showToast === 'function') {
        window.showToast(error.message || 'Não foi possível atualizar o registo.', 'warning');
      }
      const row = findRow(rsstamp);
      if (row) {
        row.checked = !checked;
      }
      renderRows();
      setStatus(error.message || 'Não foi possível atualizar o registo.', true);
    } finally {
      state.pending.delete(rsstamp);
      renderRows();
    }
  }

  function openPdf() {
    const params = new URLSearchParams({
      mes: String(state.mes),
      ano: String(state.ano),
      utilizador: state.utilizador
    });
    const url = `/api/kms/pdf?${params.toString()}`;
    const popup = window.open(url, '_blank');
    if (!popup) {
      window.location.href = url;
      return;
    }
    try {
      popup.opener = null;
    } catch (_) {}
  }

  function bindEvents() {
    monthSelect.addEventListener('change', () => {
      state.mes = Number(monthSelect.value || state.mes);
      loadRows();
    });

    yearSelect.addEventListener('change', () => {
      state.ano = Number(yearSelect.value || state.ano);
      loadRows();
    });

    userSelect.addEventListener('change', () => {
      state.utilizador = String(userSelect.value || state.utilizador || '').trim();
      loadRows();
    });

    if (refreshBtn) {
      refreshBtn.addEventListener('click', () => loadRows());
    }

    if (currentMonthBtn) {
      currentMonthBtn.addEventListener('click', () => {
        const now = new Date();
        state.mes = now.getMonth() + 1;
        state.ano = now.getFullYear();
        monthSelect.value = String(state.mes);
        yearSelect.value = String(state.ano);
        loadRows();
      });
    }

    if (pdfBtn) {
      pdfBtn.addEventListener('click', openPdf);
    }

    tableBody.addEventListener('change', (event) => {
      const input = event.target;
      if (!(input instanceof HTMLInputElement) || input.type !== 'checkbox') return;
      const rsstamp = String(input.dataset.rsstamp || '').trim();
      toggleReservation(rsstamp, input.checked);
    });

    tableBody.addEventListener('click', (event) => {
      const target = event.target;
      if (!(target instanceof Element)) return;
      if (target.closest('input, button, a, label')) return;
      const rowEl = target.closest('tr[data-rsstamp]');
      if (!rowEl) return;
      if (rowEl.dataset.disabled === '1') return;
      const rsstamp = String(rowEl.dataset.rsstamp || '').trim();
      const row = findRow(rsstamp);
      if (!row || state.pending.has(rsstamp) || row.disabled) return;
      toggleReservation(rsstamp, !row.checked);
    });
  }

  function init() {
    buildMonthOptions();
    buildYearOptions();
    buildUserOptions();
    bindEvents();
    loadRows();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init, { once: true });
  } else {
    init();
  }
})();
