(function () {
  const state = {
    loadingText: null,
    loading: false,
    alojamentosLoaded: false,
  };

  const els = {
    subtitle: document.getElementById('clientReservationsPageSubtitle'),
    list: document.getElementById('clientReservationsList'),
    dateFrom: document.getElementById('clientReservationsFrom'),
    dateTo: document.getElementById('clientReservationsTo'),
    lodge: document.getElementById('clientReservationsLodge'),
    status: document.getElementById('clientReservationsStatus'),
    refresh: document.getElementById('clientReservationsRefresh'),
    clear: document.getElementById('clientReservationsClear'),
    total: document.getElementById('clientReservationsTotal'),
    current: document.getElementById('clientReservationsCurrent'),
    future: document.getElementById('clientReservationsFuture'),
    cancelled: document.getElementById('clientReservationsCancelled'),
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

  function formatDate(value) {
    const raw = String(value || '').trim();
    if (!raw) return '';
    const parts = raw.slice(0, 10).split('-');
    if (parts.length !== 3) return raw;
    return `${parts[2]}/${parts[1]}/${parts[0]}`;
  }

  function formatMoney(value) {
    const number = Number(value || 0);
    return number.toLocaleString('pt-PT', { style: 'currency', currency: 'EUR' });
  }

  function queryString() {
    const params = new URLSearchParams();
    params.set('include_cancelled', '1');
    params.set('status', els.status?.value || 'all');
    if (els.dateFrom?.value) params.set('date_from', els.dateFrom.value);
    if (els.dateTo?.value) params.set('date_to', els.dateTo.value);
    if (els.lodge?.value) params.set('alojamento', els.lodge.value);
    return params.toString();
  }

  function stateBadge(row) {
    if (row.cancelada) return '<span class="sz_badge sz_badge_danger">Cancelada</span>';
    if (row.estado === 'current') return '<span class="sz_badge sz_badge_success">Em curso</span>';
    if (row.estado === 'future') return '<span class="sz_badge sz_badge_info">Futura</span>';
    return '<span class="sz_badge sz_badge_warning">Passada</span>';
  }

  function reservationCard(row) {
    const cls = row.cancelada ? 'is-cancelled' : (row.estado === 'current' ? 'is-current' : (row.estado === 'future' ? 'is-future' : 'is-past'));
    const dateText = `${formatDate(row.datain)}${row.horain ? ` ${escapeHtml(row.horain)}` : ''} - ${formatDate(row.dataout)}${row.horaout ? ` ${escapeHtml(row.horaout)}` : ''}`;
    const meta = [
      row.noites ? `${row.noites} noite${Number(row.noites) === 1 ? '' : 's'}` : '',
      row.hospedes ? `${row.hospedes} hospede${Number(row.hospedes) === 1 ? '' : 's'}` : '',
      row.origem || '',
    ].filter(Boolean);
    const cancelPaid = Number(row.pcancel || 0) > 0
      ? `<span class="sz_badge sz_badge_warning">Pago pelo hospede: ${escapeHtml(formatMoney(row.pcancel))}</span>`
      : '';
    const cancelDate = row.cancelada && row.dtcancel
      ? `<span><i class="fa-solid fa-ban"></i> Cancelada em ${escapeHtml(formatDate(row.dtcancel))}</span>`
      : '';
    const displayValue = row.cancelada ? row.pcancel : row.valor_liquido;

    return `
      <article class="client-reservation-card ${cls}">
        <div class="client-reservation-head">
          <div>
            <div class="client-reservation-code">${escapeHtml(row.reserva || 'Reserva')}</div>
            <div class="client-reservation-lodge">${escapeHtml(row.alojamento || '')}</div>
          </div>
          <div class="client-reservation-value">${escapeHtml(formatMoney(displayValue))}</div>
        </div>
        <div class="client-reservation-meta">
          ${stateBadge(row)}
          ${cancelPaid}
        </div>
        <div class="client-reservation-meta">
          <span><i class="fa-solid fa-calendar-days"></i> ${dateText}</span>
          ${cancelDate}
          ${row.hospede ? `<span><i class="fa-solid fa-user"></i> ${escapeHtml(row.hospede)}</span>` : ''}
          ${row.pais ? `<span><i class="fa-solid fa-earth-europe"></i> ${escapeHtml(row.pais)}</span>` : ''}
        </div>
        ${meta.length ? `<div class="client-reservation-meta">${meta.map((item) => `<span>${escapeHtml(item)}</span>`).join('')}</div>` : ''}
      </article>
    `;
  }

  function render(data) {
    const rows = Array.isArray(data.reservas) ? data.reservas : [];
    const summary = data.summary || {};
    if (els.subtitle && data.cliente?.nome) els.subtitle.textContent = data.cliente.nome;
    if (els.total) els.total.textContent = String(summary.total || 0);
    if (els.current) els.current.textContent = String(summary.current || 0);
    if (els.future) els.future.textContent = String(summary.future || 0);
    if (els.cancelled) els.cancelled.textContent = String(summary.cancelled || 0);

    if (els.lodge && !state.alojamentosLoaded) {
      const alojamentos = Array.isArray(data.alojamentos) ? data.alojamentos : [];
      els.lodge.innerHTML = '<option value="">Todos os alojamentos</option>' + alojamentos
        .map((name) => `<option value="${escapeHtml(name)}">${escapeHtml(name)}</option>`)
        .join('');
      els.lodge.classList.toggle('d-none', alojamentos.length <= 1);
      state.alojamentosLoaded = true;
    }

    if (!rows.length) {
      els.list.innerHTML = '<div class="client-reservations-empty">Sem reservas para os filtros selecionados.</div>';
      return;
    }
    els.list.innerHTML = rows.map(reservationCard).join('');
  }

  async function loadReservations() {
    showLoading('A carregar reservas...');
    try {
      const response = await fetch(`/api/cliente/reservas?${queryString()}`);
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data.error || 'Erro ao carregar reservas.');
      render(data);
    } catch (error) {
      if (els.list) {
        els.list.innerHTML = `<div class="client-reservations-empty">Erro: ${escapeHtml(error.message || 'Nao foi possivel carregar reservas.')}</div>`;
      }
      showToast(error.message || 'Erro ao carregar reservas.', 'danger');
    } finally {
      hideLoading();
    }
  }

  function bindEvents() {
    els.refresh?.addEventListener('click', loadReservations);
    els.dateFrom?.addEventListener('change', loadReservations);
    els.dateTo?.addEventListener('change', loadReservations);
    els.lodge?.addEventListener('change', loadReservations);
    els.status?.addEventListener('change', loadReservations);
    els.clear?.addEventListener('click', () => {
      if (els.dateFrom) els.dateFrom.value = '';
      if (els.dateTo) els.dateTo.value = '';
      if (els.lodge) els.lodge.value = '';
      if (els.status) els.status.value = 'all';
      loadReservations();
    });
  }

  document.addEventListener('DOMContentLoaded', () => {
    bindEvents();
    loadReservations();
  });
})();
