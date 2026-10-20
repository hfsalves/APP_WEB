(() => {
  'use strict';

  const app = document.getElementById('touristTaxApp');
  if (!app) return;

  const form = document.getElementById('touristTaxFilters');
  const type = document.getElementById('taxType');
  const year = document.getElementById('taxYear');
  const period = document.getElementById('taxPeriod');
  const periodCaption = document.getElementById('taxPeriodCaption');
  const loadButton = document.getElementById('taxLoad');
  const exportButton = document.getElementById('taxExport');
  const status = document.getElementById('taxStatus');
  const error = document.getElementById('taxError');
  const numberFormat = new Intl.NumberFormat('pt-PT');
  const monthNames = [
    'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
    'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro'
  ];

  const escapeHtml = (value) => String(value ?? '').replace(/[&<>"']/g, (char) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
  }[char]));

  const formatNumber = (value) => numberFormat.format(Number(value || 0));
  const formatDate = (value) => {
    const match = String(value || '').match(/^(\d{4})-(\d{2})-(\d{2})$/);
    return match ? `${match[3]}/${match[2]}/${match[1]}` : String(value || '—');
  };

  function query() {
    return new URLSearchParams({ tipo: type.value, ano: year.value, periodo: period.value });
  }

  function updatePeriodOptions(preserve = true) {
    const previous = preserve ? Number(period.value || period.dataset.initialMonth || 1) : 1;
    const quarterly = type.value === 'trimestral';
    const length = quarterly ? 4 : 12;
    periodCaption.textContent = quarterly ? 'Trimestre' : 'Mês';
    period.innerHTML = Array.from({ length }, (_, index) => {
      const value = index + 1;
      const label = quarterly ? `Q${value}` : monthNames[index];
      return `<option value="${value}">${label}</option>`;
    }).join('');
    period.value = String(Math.min(Math.max(previous, 1), length));
  }

  function renderEmpty(columns, message = 'Sem registos para este período.') {
    return `<tr><td colspan="${columns}" class="tourist-tax-empty">${escapeHtml(message)}</td></tr>`;
  }

  function setLoading(loading) {
    loadButton.disabled = loading;
    exportButton.disabled = loading;
    app.classList.toggle('is-loading', loading);
  }

  function render(payload) {
    const totals = payload.totais || {};
    document.querySelectorAll('[data-kpi]').forEach((node) => {
      node.textContent = formatNumber(totals[node.dataset.kpi]);
    });

    const selectedType = payload.periodo?.tipo || '—';
    document.getElementById('taxDeliveryBadge').textContent = selectedType;
    document.getElementById('taxPeriodSummary').textContent = `${formatDate(payload.periodo?.inicio)} a ${formatDate(payload.periodo?.fim)} · apenas alojamentos de entrega ${selectedType.toLowerCase()}`;
    document.getElementById('taxDetailSummary').textContent = `${formatNumber((payload.linhas || []).length)} reservas carregadas`;
    document.getElementById('taxMonthlyConfigured').textContent = formatNumber(payload.configuracao?.alojamentos_mensais);
    document.getElementById('taxQuarterlyConfigured').textContent = formatNumber(payload.configuracao?.alojamentos_trimestrais);

    const accommodationRows = (payload.resumo_alojamento || []).map((row) => `
      <tr>
        <td class="tourist-tax-strong">${escapeHtml(row.alojamento)}</td>
        <td><span class="tourist-tax-cadence">${escapeHtml(row.entrega)}</span></td>
        <td>${formatNumber(row.reservas)}</td><td>${formatNumber(row.dormidas_totais)}</td>
        <td>${formatNumber(row.dormidas_acima_limite)}</td><td>${formatNumber(row.adultos)}</td>
        <td>${formatNumber(row.criancas)}</td><td>${formatNumber(row.noites_periodo)}</td>
      </tr>`).join('');
    document.getElementById('taxAccommodationRows').innerHTML = accommodationRows || renderEmpty(8);

    const originRows = (payload.resumo_origem || []).map((row) => `
      <tr>
        <td class="tourist-tax-strong">${escapeHtml(row.origem)}</td><td>${formatNumber(row.reservas)}</td>
        <td>${formatNumber(row.dormidas_totais)}</td><td>${formatNumber(row.dormidas_acima_limite)}</td>
        <td>${formatNumber(row.adultos)}</td><td>${formatNumber(row.criancas)}</td><td>${formatNumber(row.noites_periodo)}</td>
      </tr>`).join('');
    document.getElementById('taxOriginRows').innerHTML = originRows || renderEmpty(7);

    const detailRows = (payload.linhas || []).map((row) => `
      <tr>
        <td class="tourist-tax-reservation">${escapeHtml(row.reserva)}</td><td>${escapeHtml(row.origem)}</td>
        <td>${escapeHtml(row.alojamento)}</td><td>${escapeHtml(formatDate(row.checkin))}</td><td>${escapeHtml(formatDate(row.checkout))}</td>
        <td>${formatNumber(row.noites_periodo)}</td><td>${formatNumber(row.adultos)}</td><td>${formatNumber(row.criancas)}</td>
        <td>${formatNumber(row.hospedes_total)}</td><td>${formatNumber(row.dormidas_totais)}</td>
        <td>${formatNumber(row.dormidas_acima_limite)}</td><td>${formatNumber(row.limite_noites)}</td>
      </tr>`).join('');
    document.getElementById('taxDetailRows').innerHTML = detailRows || renderEmpty(12);

    const warnings = payload.avisos || [];
    document.getElementById('taxWarningCount').textContent = formatNumber(warnings.length);
    document.getElementById('taxWarnings').innerHTML = warnings.length
      ? warnings.map((warning) => `<li>${escapeHtml(warning)}</li>`).join('')
      : '<li>Sem avisos.</li>';
    document.getElementById('taxWarningsPanel').classList.toggle('has-warnings', warnings.length > 0);
  }

  async function load() {
    error.hidden = true;
    status.textContent = 'A carregar mapa…';
    setLoading(true);
    try {
      const response = await fetch(`${app.dataset.apiUrl}?${query()}`, { credentials: 'same-origin' });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok || !payload.ok) throw new Error(payload.error || `Erro HTTP ${response.status}`);
      render(payload);
      status.textContent = `${payload.periodo.rotulo} · ${formatNumber(payload.totais.reservas)} reservas`;
    } catch (exception) {
      error.textContent = exception.message || 'Não foi possível carregar o mapa.';
      error.hidden = false;
      status.textContent = 'Erro ao carregar.';
    } finally {
      setLoading(false);
    }
  }

  form.addEventListener('submit', (event) => { event.preventDefault(); load(); });
  type.addEventListener('change', () => { updatePeriodOptions(false); load(); });
  exportButton.addEventListener('click', () => {
    window.location.assign(`${app.dataset.exportUrl}?${query()}`);
  });

  updatePeriodOptions();
  load();
})();
