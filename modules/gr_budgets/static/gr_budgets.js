(function () {
  'use strict';

  const root = document.getElementById('grBudgetApp');
  if (!root) return;

  const apiBase = '/api/gr_orcamentos';
  const elements = {
    company: document.getElementById('budgetCompany'),
    series: document.getElementById('budgetSeries'),
    year: document.getElementById('budgetYear'),
    search: document.getElementById('budgetSearch'),
    refresh: document.getElementById('budgetRefresh'),
    document: document.getElementById('budgetDocument'),
    previous: document.getElementById('budgetPrevious'),
    next: document.getElementById('budgetNext'),
    resultCount: document.getElementById('budgetResultCount'),
    error: document.getElementById('budgetError'),
    empty: document.getElementById('budgetEmpty'),
    content: document.getElementById('budgetContent'),
    loading: document.getElementById('budgetLoading'),
    lines: document.getElementById('budgetLines'),
    linesFooter: document.getElementById('budgetLinesFooter'),
    dialog: document.getElementById('technicalDetailDialog'),
    dialogLine: document.getElementById('technicalDetailLine')
  };

  const state = {
    companies: [],
    series: [],
    budgets: [],
    detail: null,
    loadingCount: 0,
    searchTimer: 0,
    requestVersion: 0
  };

  const numberFormatter = new Intl.NumberFormat('pt-PT', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  const lineAmountFormatter = new Intl.NumberFormat('pt-PT', { minimumFractionDigits: 2, maximumFractionDigits: 4 });
  const quantityFormatter = new Intl.NumberFormat('pt-PT', { minimumFractionDigits: 0, maximumFractionDigits: 4 });
  const percentFormatter = new Intl.NumberFormat('pt-PT', { minimumFractionDigits: 2, maximumFractionDigits: 2 });

  function escapeHtml(value) {
    return String(value == null ? '' : value)
      .replaceAll('&', '&amp;')
      .replaceAll('<', '&lt;')
      .replaceAll('>', '&gt;')
      .replaceAll('"', '&quot;')
      .replaceAll("'", '&#039;');
  }

  function showLoading(active) {
    state.loadingCount = Math.max(0, state.loadingCount + (active ? 1 : -1));
    elements.loading.hidden = state.loadingCount === 0;
    root.setAttribute('aria-busy', state.loadingCount ? 'true' : 'false');
  }

  function showError(message) {
    elements.error.textContent = message || '';
    elements.error.hidden = !message;
  }

  async function getJson(path, params) {
    const url = new URL(apiBase + path, window.location.origin);
    Object.entries(params || {}).forEach(([key, value]) => {
      if (value !== '' && value != null) url.searchParams.set(key, value);
    });
    const response = await fetch(url, { headers: { Accept: 'application/json' } });
    let payload = {};
    try { payload = await response.json(); } catch (_) { payload = {}; }
    if (!response.ok || payload.ok === false) {
      throw new Error(payload.error || `Não foi possível carregar os dados (${response.status}).`);
    }
    return payload;
  }

  function setOptions(select, rows, valueKey, labelBuilder, selectedValue) {
    select.replaceChildren();
    rows.forEach((row) => {
      const option = document.createElement('option');
      option.value = String(row[valueKey]);
      option.textContent = labelBuilder(row);
      if (String(row[valueKey]) === String(selectedValue)) option.selected = true;
      select.append(option);
    });
  }

  async function loadCompanies() {
    showLoading(true);
    showError('');
    try {
      const payload = await getJson('/empresas');
      state.companies = payload.rows || [];
      const stored = window.localStorage.getItem('gr-budgets-feid');
      const preferredDatabase = (root.dataset.preferredDatabase || '').toUpperCase();
      const selected = state.companies.find((row) => String(row.feid) === stored)
        || state.companies.find((row) => String(row.phc_db || '').toUpperCase() === preferredDatabase)
        || state.companies[0];
      setOptions(elements.company, state.companies, 'feid', (row) => row.name || row.phc_db, selected && selected.feid);
      if (!selected) {
        renderNoResults('Não existem empresas PHC configuradas para este utilizador.');
        return;
      }
      await loadSeries();
    } catch (error) {
      showError(error.message);
      renderNoResults();
    } finally {
      showLoading(false);
    }
  }

  async function loadSeries() {
    const feid = elements.company.value;
    if (!feid) return;
    window.localStorage.setItem('gr-budgets-feid', feid);
    showLoading(true);
    showError('');
    try {
      const payload = await getJson('/series', { feid });
      state.series = payload.rows || [];
      setOptions(elements.series, state.series, 'ndos', (row) => `${row.name} · ${row.ndos}`, payload.default_ndos);
      if (!state.series.length) {
        renderNoResults('Esta empresa não tem séries de orçamento com OCI configuradas no PHC.');
        return;
      }
      await loadBudgets();
    } catch (error) {
      showError(error.message);
      renderNoResults();
    } finally {
      showLoading(false);
    }
  }

  async function loadBudgets(preferredStamp) {
    if (!elements.company.value || !elements.series.value) return;
    const version = ++state.requestVersion;
    showLoading(true);
    showError('');
    try {
      const payload = await getJson('/orcamentos', {
        feid: elements.company.value,
        ndos: elements.series.value,
        year: elements.year.value,
        q: elements.search.value.trim()
      });
      if (version !== state.requestVersion) return;
      state.budgets = payload.rows || [];
      const selected = state.budgets.find((row) => row.bostamp === preferredStamp) || state.budgets[0];
      setOptions(
        elements.document,
        state.budgets,
        'bostamp',
        (row) => `${row.series} ${row.number} · ${row.client_name || 'Sem cliente'}${row.work_name ? ` — ${row.work_name}` : ''}`,
        selected && selected.bostamp
      );
      elements.resultCount.textContent = `${state.budgets.length} ${state.budgets.length === 1 ? 'orçamento' : 'orçamentos'}`;
      updateNavigation();
      if (!selected) {
        renderNoResults();
        return;
      }
      await loadDetail(selected.bostamp, version);
    } catch (error) {
      if (version !== state.requestVersion) return;
      showError(error.message);
      renderNoResults();
    } finally {
      showLoading(false);
    }
  }

  async function loadDetail(bostamp, listVersion) {
    if (!bostamp) return;
    showLoading(true);
    showError('');
    try {
      const payload = await getJson('/orcamento', { feid: elements.company.value, bostamp });
      if (listVersion && listVersion !== state.requestVersion) return;
      state.detail = payload;
      renderDetail(payload);
    } catch (error) {
      showError(error.message);
      elements.content.hidden = true;
    } finally {
      showLoading(false);
    }
  }

  function renderNoResults(message) {
    state.detail = null;
    elements.content.hidden = true;
    elements.empty.hidden = false;
    const strong = elements.empty.querySelector('strong');
    if (strong) strong.textContent = message || 'Não existem orçamentos para os filtros selecionados.';
    elements.document.replaceChildren();
    elements.resultCount.textContent = '0 orçamentos';
    updateNavigation();
  }

  function text(id, value, fallback) {
    const element = document.getElementById(id);
    if (element) element.textContent = value || fallback || '—';
  }

  function formatDate(value) {
    if (!value) return '—';
    const parts = String(value).slice(0, 10).split('-');
    return parts.length === 3 ? `${parts[2]}.${parts[1]}.${parts[0]}` : value;
  }

  function money(value, currency) {
    const code = currency || 'EUR';
    try {
      return new Intl.NumberFormat('pt-PT', { style: 'currency', currency: code }).format(Number(value || 0));
    } catch (_) {
      return `${numberFormatter.format(Number(value || 0))} ${code}`;
    }
  }

  function renderDetail(payload) {
    const header = payload.header || {};
    const totals = payload.totals || {};
    const lines = payload.lines || [];
    elements.empty.hidden = true;
    elements.content.hidden = false;

    text('budgetDocumentEyebrow', `Dossier interno · ${header.series || 'Orçamento'}`);
    text('budgetDocumentTitle', `${header.series || 'Orçamento'} ${header.number || '—'} / ${header.year || '—'}`);
    text('budgetDocumentSubtitle', [header.reference, header.process, header.work_name].filter(Boolean).join(' · '));
    text('budgetClient', header.client_name);
    text('budgetClientNumber', header.client_number ? `Cliente n.º ${header.client_number}` : '');
    text('budgetWork', header.work_name);
    text('budgetLocality', header.locality || header.place);
    text('budgetDate', formatDate(header.date));
    text('budgetSalesperson', header.salesperson);
    text('budgetTeam', header.technician);
    text('budgetAttention', header.attention);
    text('budgetArea', header.area);
    text('budgetProcess', header.process);
    text('budgetCostCenter', header.cost_center);
    text('budgetCurrency', header.currency);
    text('budgetEmail', header.email);
    text('budgetPhone', header.phone);
    text('budgetReference', header.reference);
    text('budgetTotal', money(totals.total, header.currency));
    text('budgetCost', money(totals.cost, header.currency));
    text('budgetMargin', `${percentFormatter.format(Number(totals.margin_percentage || 0))}%`);
    text('budgetProfit', money(totals.profit, header.currency));
    text('budgetLineCount', `${lines.length} ${lines.length === 1 ? 'linha' : 'linhas'} · BI + BI2`);
    text('budgetPayment', header.payment_terms);
    text('budgetObservations', header.observations);
    text('budgetCancellation', header.cancellation_reason);
    document.getElementById('budgetCancellationWrap').hidden = !header.cancelled && !header.cancellation_reason;

    renderStatuses(header);
    renderLines(lines, header.currency, totals);
  }

  function renderStatuses(header) {
    const statuses = [];
    if (header.cancelled) statuses.push(['danger', 'fa-ban', 'Anulado']);
    if (header.approved) statuses.push(['success', 'fa-circle-check', 'Aprovado']);
    if (header.awarded) statuses.push(['info', 'fa-trophy', 'Adjudicado']);
    if (!statuses.length) statuses.push(['warning', 'fa-clock', 'Em preparação']);
    document.getElementById('budgetStatus').innerHTML = statuses.map(([kind, icon, label]) =>
      `<span class="sz_badge sz_badge_${kind}"><i class="fa-solid ${icon}"></i>${escapeHtml(label)}</span>`
    ).join('');
  }

  function flag(value, label) {
    return `<span class="gr-budget-flag${value ? ' gr-budget-flag-on' : ''}" aria-label="${value ? 'Sim' : 'Não'}" title="${escapeHtml(label)}: ${value ? 'Sim' : 'Não'}"><i class="fa-solid ${value ? 'fa-check' : 'fa-minus'}"></i></span>`;
  }

  function renderLines(lines, currency, totals) {
    elements.lines.innerHTML = lines.map((line, index) => {
      const title = line.designation || line.description || 'Linha sem designação';
      const secondary = line.description && line.description !== line.designation ? line.description : '';
      return `<tr class="sz_table_row">
        <td class="gr-budget-num">${escapeHtml(line.item || index + 1)}</td>
        <td>${escapeHtml(line.reference || '—')}</td>
        <td title="${escapeHtml(secondary || title)}"><div class="gr-budget-line-title">${escapeHtml(title)}</div>${secondary ? `<div class="gr-budget-line-subtitle">${escapeHtml(secondary)}</div>` : ''}</td>
        <td class="gr-budget-num">${percentFormatter.format(Number(line.discount_1 || 0))}%</td>
        <td class="gr-budget-num">${percentFormatter.format(Number(line.discount_2 || 0))}%</td>
        <td class="gr-budget-num">${lineAmountFormatter.format(Number(line.unit_price || 0))}</td>
        <td class="gr-budget-num"><strong>${lineAmountFormatter.format(Number(line.total || 0))}</strong></td>
        <td class="gr-budget-num">${percentFormatter.format(Number(line.vat_rate || 0))}%</td>
        <td class="gr-budget-num">${quantityFormatter.format(Number(line.quantity || 0))}</td>
        <td class="gr-budget-num">${lineAmountFormatter.format(Number(line.cost_total || 0))}</td>
        <td class="gr-budget-num">${escapeHtml(line.vat_table || '—')}</td>
        <td class="gr-budget-num">${quantityFormatter.format(Number(line.thickness || 0))}</td>
        <td class="gr-budget-check">${flag(line.variant, 'Variante')}</td>
        <td class="gr-budget-check">${flag(line.blocked_price, 'PV bloqueado')}</td>
        <td class="gr-budget-check">${flag(line.pump, 'Bomba')}</td>
        <td class="gr-budget-check"><button type="button" class="sz_button sz_button_ghost gr-budget-technical-button" data-technical-line="${index}" aria-label="Abrir detalhe técnico da linha ${escapeHtml(line.item || index + 1)}" title="Detalhe técnico (OCI)">+</button></td>
        <td class="gr-budget-check">${flag(line.labour, 'Mão de obra')}</td>
        <td class="gr-budget-check">${flag(line.option, 'Opção')}</td>
        <td class="gr-budget-check">${flag(line.pro_rata, 'Pro rata')}</td>
        <td class="gr-budget-check">${flag(line.simultaneous, 'Simultanée')}</td>
        <td class="gr-budget-num">${percentFormatter.format(Number(line.margin_percentage || 0))}%</td>
        <td class="gr-budget-num">${lineAmountFormatter.format(Number(line.profit || 0))}</td>
      </tr>`;
    }).join('');
    elements.linesFooter.innerHTML = `<tr>
      <td colspan="6">Totais · ${escapeHtml(lines.length)} linhas</td>
      <td class="gr-budget-num">${escapeHtml(money(totals.total, currency))}</td>
      <td colspan="2"></td>
      <td class="gr-budget-num">${escapeHtml(money(totals.cost, currency))}</td>
      <td colspan="10"></td>
      <td class="gr-budget-num">${percentFormatter.format(Number(totals.margin_percentage || 0))}%</td>
      <td class="gr-budget-num">${escapeHtml(money(totals.profit, currency))}</td>
    </tr>`;
  }

  function updateNavigation() {
    const index = state.budgets.findIndex((row) => row.bostamp === elements.document.value);
    elements.previous.disabled = index <= 0;
    elements.next.disabled = index < 0 || index >= state.budgets.length - 1;
  }

  function moveSelection(delta) {
    const index = state.budgets.findIndex((row) => row.bostamp === elements.document.value);
    const nextIndex = Math.min(state.budgets.length - 1, Math.max(0, index + delta));
    if (nextIndex === index || !state.budgets[nextIndex]) return;
    elements.document.value = state.budgets[nextIndex].bostamp;
    updateNavigation();
    loadDetail(elements.document.value);
  }

  elements.company.addEventListener('change', loadSeries);
  elements.series.addEventListener('change', () => loadBudgets());
  elements.year.addEventListener('change', () => loadBudgets());
  elements.search.addEventListener('input', () => {
    window.clearTimeout(state.searchTimer);
    state.searchTimer = window.setTimeout(() => loadBudgets(), 350);
  });
  elements.refresh.addEventListener('click', () => loadBudgets(elements.document.value));
  elements.document.addEventListener('change', () => {
    updateNavigation();
    loadDetail(elements.document.value);
  });
  elements.previous.addEventListener('click', () => moveSelection(-1));
  elements.next.addEventListener('click', () => moveSelection(1));
  elements.lines.addEventListener('click', (event) => {
    const button = event.target.closest('[data-technical-line]');
    if (!button || !state.detail) return;
    const line = (state.detail.lines || [])[Number(button.dataset.technicalLine)];
    if (!line) return;
    elements.dialogLine.textContent = `Linha ${line.item || '—'} · ${line.reference || 'Sem referência'} · ${line.designation || line.description || 'Sem designação'}`;
    elements.dialog.classList.add('sz_is_open');
    elements.dialog.setAttribute('aria-hidden', 'false');
  });

  function closeTechnicalDialog() {
    elements.dialog.classList.remove('sz_is_open');
    elements.dialog.setAttribute('aria-hidden', 'true');
  }

  root.querySelectorAll('[data-technical-close]').forEach((button) => {
    button.addEventListener('click', closeTechnicalDialog);
  });
  elements.dialog.addEventListener('click', (event) => {
    if (event.target === elements.dialog) closeTechnicalDialog();
  });
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && elements.dialog.classList.contains('sz_is_open')) closeTechnicalDialog();
  });

  elements.year.value = String(new Date().getFullYear());
  loadCompanies();
})();
