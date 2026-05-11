(function () {
  const state = {
    reservas: [],
    billingLodgesLoaded: false,
    loadingText: null,
    loading: false,
  };

  const els = {
    subtitle: document.getElementById('clientPortalSubtitle'),
    summary: document.getElementById('clientReservationsSummary'),
    total: document.getElementById('clientReservationsTotal'),
    groups: document.getElementById('clientReservationsGroups'),
    billingSummary: document.getElementById('clientBillingSummary'),
    billingReservations: document.getElementById('clientBillingReservations'),
    billingYear: document.getElementById('clientBillingYear'),
    billingLodge: document.getElementById('clientBillingLodge'),
    billingTotal: document.getElementById('clientBillingTotal'),
    billingGross: document.getElementById('clientBillingGross'),
    billingMonths: document.getElementById('clientBillingMonths'),
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

  function initBillingYears() {
    if (!els.billingYear || els.billingYear.options.length) return;
    const year = new Date().getFullYear();
    const years = [];
    for (let item = year + 1; item >= year - 5; item -= 1) years.push(item);
    els.billingYear.innerHTML = years.map((item) => `<option value="${item}">${item}</option>`).join('');
    els.billingYear.value = String(year);
  }

  function reservationCard(row) {
    const cls = row.estado === 'current' ? 'is-current' : 'is-future';
    const dateText = `${formatDate(row.datain)}${row.horain ? ` ${escapeHtml(row.horain)}` : ''} - ${formatDate(row.dataout)}${row.horaout ? ` ${escapeHtml(row.horaout)}` : ''}`;
    const meta = [
      row.noites ? `${row.noites} noite${Number(row.noites) === 1 ? '' : 's'}` : '',
      row.hospedes ? `${row.hospedes} hospede${Number(row.hospedes) === 1 ? '' : 's'}` : '',
      row.origem || '',
    ].filter(Boolean);

    return `
      <article class="client-reservation-card ${cls}">
        <div class="client-reservation-head">
          <div>
            <div class="client-reservation-code">${escapeHtml(row.reserva || 'Reserva')}</div>
            <div class="client-reservation-lodge">${escapeHtml(row.alojamento || '')}</div>
          </div>
          <div class="client-reservation-value">${escapeHtml(formatMoney(row.valor_liquido))}</div>
        </div>
        <div class="client-reservation-meta">
          <span><i class="fa-solid fa-calendar-days"></i> ${dateText}</span>
          ${row.hospede ? `<span><i class="fa-solid fa-user"></i> ${escapeHtml(row.hospede)}</span>` : ''}
          ${row.pais ? `<span><i class="fa-solid fa-earth-europe"></i> ${escapeHtml(row.pais)}</span>` : ''}
        </div>
        ${meta.length ? `<div class="client-reservation-meta">${meta.map((item) => `<span>${escapeHtml(item)}</span>`).join('')}</div>` : ''}
      </article>
    `;
  }

  function groupHtml(title, rows, badgeClass) {
    if (!rows.length) return '';
    return `
      <section class="client-reservation-group">
        <div class="client-reservation-group-title">
          <span>${escapeHtml(title)}</span>
          <span class="sz_badge ${badgeClass}">${rows.length}</span>
        </div>
        ${rows.map(reservationCard).join('')}
      </section>
    `;
  }

  function render(data) {
    const reservas = Array.isArray(data.reservas) ? data.reservas : [];
    state.reservas = reservas;
    if (els.subtitle && data.cliente?.nome) els.subtitle.textContent = data.cliente.nome;

    const current = reservas.filter((row) => row.estado === 'current')
      .sort((a, b) => String(a.dataout || '').localeCompare(String(b.dataout || '')));
    const future = reservas.filter((row) => row.estado === 'future')
      .sort((a, b) => String(a.datain || '').localeCompare(String(b.datain || '')))
      .slice(0, 5);
    const visibleTotal = current.length + future.length;

    if (els.total) els.total.textContent = String(visibleTotal);
    if (els.summary) {
      els.summary.textContent = `${current.length} em curso \u00b7 ${future.length} proxima${future.length === 1 ? '' : 's'}`;
    }

    if (!visibleTotal) {
      els.groups.innerHTML = '<div class="client-empty-state">Sem reservas em curso ou futuras.</div>';
      return;
    }
    els.groups.innerHTML = [
      groupHtml('Em curso', current, 'sz_badge_success'),
      groupHtml('Proximas', future, 'sz_badge_info'),
    ].join('');
  }

  async function loadReservations(options = {}) {
    if (options.loading !== false) showLoading('A carregar portal...');
    try {
      const response = await fetch('/api/cliente/reservas?scope=dashboard');
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data.error || 'Erro ao carregar reservas.');
      render(data);
    } catch (error) {
      if (els.groups) {
        els.groups.innerHTML = `<div class="client-empty-state">Erro: ${escapeHtml(error.message || 'Nao foi possivel carregar reservas.')}</div>`;
      }
      showToast(error.message || 'Erro ao carregar portal.', 'danger');
    } finally {
      if (options.loading !== false) hideLoading();
    }
  }

  function ensureBillingTotalsLayout() {
    const total = document.querySelector('.client-billing-total');
    if (!total || total.dataset.normalized === '1') return;
    total.innerHTML = `
      <div class="client-billing-total-metric">
        <span>Fatura\u00e7\u00e3o</span>
        <div id="clientBillingTotal" class="client-billing-total-value">0,00 EUR</div>
      </div>
    `;
    total.dataset.normalized = '1';
    els.billingTotal = document.getElementById('clientBillingTotal');
    els.billingGross = null;
  }

  function renderBilling(data) {
    ensureBillingTotalsLayout();
    const meses = Array.isArray(data.meses) ? data.meses : [];
    const totals = data.totals || {};
    const maxValue = Math.max(1, ...meses.map((item) => Number(item.faturado ?? item.liquido ?? 0)));

    if (els.billingSummary) {
      els.billingSummary.textContent = `${data.ano || ''} \u00b7 ${totals.reservas || 0} reserva${Number(totals.reservas || 0) === 1 ? '' : 's'}`;
    }
    if (els.billingReservations) els.billingReservations.textContent = String(totals.reservas || 0);
    if (els.billingTotal) els.billingTotal.textContent = formatMoney(totals.faturado ?? totals.liquido ?? 0);
    if (els.billingLodge && !state.billingLodgesLoaded) {
      const alojamentos = Array.isArray(data.alojamentos) ? data.alojamentos : [];
      els.billingLodge.innerHTML = '<option value="">Todos os alojamentos</option>' + alojamentos
        .map((name) => `<option value="${escapeHtml(name)}">${escapeHtml(name)}</option>`)
        .join('');
      els.billingLodge.classList.toggle('d-none', alojamentos.length <= 1);
      state.billingLodgesLoaded = true;
    }

    if (!els.billingMonths) return;
    const rows = meses.map((item) => {
      const value = Number(item.faturado ?? item.liquido ?? 0);
      const commission = Number(item.comissao_gestao ?? item.comissao ?? 0);
      const width = Math.max(0, Math.min(100, (value / maxValue) * 100));
      return `
        <div class="client-billing-month ${value || commission ? 'has-value' : 'is-empty'}">
          <strong>${escapeHtml(item.label || '')}</strong>
          <div class="client-billing-month-bar" title="${escapeHtml(formatMoney(value))}">
            <span style="width:${width.toFixed(2)}%"></span>
          </div>
          <div class="client-billing-month-value">${escapeHtml(formatMoney(value))}</div>
          <div class="client-billing-month-commission">${escapeHtml(formatMoney(commission))}</div>
        </div>
      `;
    }).join('');
    els.billingMonths.innerHTML = `
      <div class="client-billing-month client-billing-month-header">
        <span>M\u00eas</span>
        <span></span>
        <span>Fatura\u00e7\u00e3o</span>
        <span>Comiss\u00f5es</span>
      </div>
      ${rows}
    `;
  }

  async function loadBilling(options = {}) {
    if (options.loading !== false) showLoading('A carregar faturacao...');
    try {
      const params = new URLSearchParams();
      params.set('ano', els.billingYear?.value || String(new Date().getFullYear()));
      if (els.billingLodge?.value) params.set('alojamento', els.billingLodge.value);
      const response = await fetch(`/api/cliente/faturacao_mensal?${params.toString()}`);
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data.error || 'Erro ao carregar faturacao.');
      renderBilling(data);
    } catch (error) {
      if (els.billingMonths) {
        els.billingMonths.innerHTML = `<div class="client-empty-state">Erro: ${escapeHtml(error.message || 'Nao foi possivel carregar faturacao.')}</div>`;
      }
      showToast(error.message || 'Erro ao carregar faturacao.', 'danger');
    } finally {
      if (options.loading !== false) hideLoading();
    }
  }

  document.addEventListener('DOMContentLoaded', () => {
    initBillingYears();
    els.billingYear?.addEventListener('change', () => loadBilling());
    els.billingLodge?.addEventListener('change', () => loadBilling());
    Promise.all([
      loadReservations(),
      loadBilling({ loading: false }),
    ]).finally(() => hideLoading());
    window.addEventListener('focus', () => {
      loadReservations({ loading: false });
      loadBilling({ loading: false });
    });
  });
})();
