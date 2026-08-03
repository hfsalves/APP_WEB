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
    printBudget: document.getElementById('budgetPrint'),
    newBudget: document.getElementById('budgetNew'),
    cancelEdit: document.getElementById('budgetCancelEdit'),
    resultCount: document.getElementById('budgetResultCount'),
    error: document.getElementById('budgetError'),
    empty: document.getElementById('budgetEmpty'),
    content: document.getElementById('budgetContent'),
    loading: document.getElementById('budgetLoading'),
    lines: document.getElementById('budgetLines'),
    linesFooter: document.getElementById('budgetLinesFooter'),
    addLine: document.getElementById('budgetAddLine'),
    clientSearch: document.getElementById('budgetClientSearch'),
    clientResults: document.getElementById('budgetClientResults'),
    clientNumber: document.getElementById('budgetClientNumber'),
    clientEstablishment: document.getElementById('budgetClientEstablishment'),
    clientMeta: document.getElementById('budgetClientMeta'),
    workInput: document.getElementById('budgetWorkInput'),
    localityInput: document.getElementById('budgetLocalityInput'),
    dateInput: document.getElementById('budgetDateInput'),
    salesperson: document.getElementById('budgetSalespersonSelect'),
    attentionInput: document.getElementById('budgetAttentionInput'),
    contextbar: root.querySelector('.gr-budget-contextbar'),
    body: root.querySelector('.gr-budget-body'),
    ociView: document.getElementById('budgetOciView'),
    ociSubtitle: document.getElementById('budgetOciSubtitle'),
    ociMode: document.getElementById('budgetOciMode'),
    ociPositions: document.getElementById('budgetOciPositions'),
    ociPositionsCount: document.getElementById('budgetOciPositionsCount'),
    ociError: document.getElementById('budgetOciError'),
    ociCancel: document.getElementById('budgetOciCancel'),
    ociSave: document.getElementById('budgetOciSave'),
    ociAddRow: document.getElementById('budgetOciAddRow'),
    ociRows: document.getElementById('budgetOciRows'),
    ociFooter: document.getElementById('budgetOciFooter'),
    ociRowCount: document.getElementById('budgetOciRowCount'),
    ociFamilyList: document.getElementById('budgetOciFamilyList'),
    ociFamilyCount: document.getElementById('budgetOciFamilyCount'),
    ociOuvrage: document.getElementById('budgetOciOuvrage'),
    ociPosition: document.getElementById('budgetOciPosition'),
    ociReference: document.getElementById('budgetOciReference'),
    ociDesignation: document.getElementById('budgetOciDesignation'),
    ociDescription: document.getElementById('budgetOciDescription'),
    ociSurface: document.getElementById('budgetOciSurface'),
    ociUnit: document.getElementById('budgetOciUnit'),
    ociThickness: document.getElementById('budgetOciThickness'),
    ociVolume: document.getElementById('budgetOciVolume'),
    ociPurchasePrice: document.getElementById('budgetOciPurchasePrice'),
    ociPurchaseTotal: document.getElementById('budgetOciPurchaseTotal'),
    ociSalePrice: document.getElementById('budgetOciSalePrice'),
    ociSaleTotal: document.getElementById('budgetOciSaleTotal'),
    ociMarginUnit: document.getElementById('budgetOciMarginUnit'),
    ociMarginTotal: document.getElementById('budgetOciMarginTotal'),
    ociMarginPercent: document.getElementById('budgetOciMarginPercent'),
    ociProrata: document.getElementById('budgetOciProrata'),
    ociSalePriceField: document.getElementById('budgetOciSalePriceField'),
    ociMarginPercentField: document.getElementById('budgetOciMarginPercentField'),
    ociM3Sim: document.getElementById('budgetOciM3Sim'),
    ociM3NonSim: document.getElementById('budgetOciM3NonSim'),
    ociM2MoSim: document.getElementById('budgetOciM2MoSim'),
    ociM2MoNonSim: document.getElementById('budgetOciM2MoNonSim'),
    ociSimultaneous: document.getElementById('budgetOciSimultaneous'),
    ociVariant: document.getElementById('budgetOciVariant'),
    ociOption: document.getElementById('budgetOciOption'),
    ociBlockedPrice: document.getElementById('budgetOciBlockedPrice'),
    ociPump: document.getElementById('budgetOciPump'),
    ociLabour: document.getElementById('budgetOciLabour'),
    componentPicker: document.getElementById('budgetComponentPicker'),
    componentFamilyTitle: document.getElementById('budgetComponentFamilyTitle'),
    componentArticleCount: document.getElementById('budgetComponentArticleCount'),
    componentArticles: document.getElementById('budgetComponentArticles'),
    componentSelection: document.getElementById('budgetComponentSelection'),
    componentConfirm: document.getElementById('budgetComponentConfirm'),
    positionPicker: document.getElementById('budgetPositionPicker'),
    positionPickerSubtitle: document.getElementById('budgetPositionPickerSubtitle'),
    positionCards: document.getElementById('budgetPositionCards'),
    positionSwitchConfirm: document.getElementById('budgetPositionSwitchConfirm'),
    positionSwitchText: document.getElementById('budgetPositionSwitchText'),
    positionSwitchDiscard: document.getElementById('budgetPositionSwitchDiscard'),
    positionSwitchSave: document.getElementById('budgetPositionSwitchSave')
  };

  const state = {
    companies: [],
    series: [],
    salespeople: [],
    budgets: [],
    clientRows: [],
    clientActiveIndex: -1,
    clientSearchTimer: 0,
    clientRequestVersion: 0,
    detail: null,
    technicalOptions: null,
    technicalOptionsFeid: '',
    ociContext: null,
    ociCache: new Map(),
    componentFamily: '',
    componentStamp: '',
    pendingPositionTarget: null,
    ociPriceLocked: true,
    ociTargetMargin: 0,
    mode: 'view',
    returnStamp: '',
    loadingCount: 0,
    searchTimer: 0,
    requestVersion: 0
  };

  const numberFormatter = new Intl.NumberFormat('pt-PT', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  const lineAmountFormatter = new Intl.NumberFormat('pt-PT', { minimumFractionDigits: 2, maximumFractionDigits: 4 });
  const quantityFormatter = new Intl.NumberFormat('pt-PT', { minimumFractionDigits: 0, maximumFractionDigits: 4 });
  const percentFormatter = new Intl.NumberFormat('pt-PT', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  const newDocumentValue = '__new_budget__';

  function isEditing() {
    return state.mode !== 'view';
  }

  function selectedBudgetStamp() {
    const stamp = String(elements.document.value || '').trim();
    return stamp && stamp !== newDocumentValue ? stamp : '';
  }

  function budgetPdfUrl() {
    const feid = String(elements.company.value || '').trim();
    const bostamp = selectedBudgetStamp();
    if (!feid || !bostamp) return '';
    const url = new URL(`${apiBase}/orcamento/${encodeURIComponent(bostamp)}/pdf`, window.location.origin);
    url.searchParams.set('feid', feid);
    url.searchParams.set('style', 'modern');
    return url.toString();
  }

  function printBudget() {
    if (isEditing() || state.loadingCount || !state.detail) return;
    const url = budgetPdfUrl();
    if (!url) {
      showError('Selecione uma empresa e um orçamento guardado antes de imprimir.');
      return;
    }
    showError('');
    const printWindow = window.open(url, '_blank');
    if (!printWindow) {
      showError('O navegador bloqueou a janela do PDF. Autorize pop-ups para imprimir o orçamento.');
      return;
    }
    printWindow.opener = null;
  }

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
    updateInteractionState();
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
    if (isEditing()) return;
    const feid = elements.company.value;
    if (!feid) return;
    window.localStorage.setItem('gr-budgets-feid', feid);
    showLoading(true);
    showError('');
    try {
      closeClientLookup();
      if (state.technicalOptionsFeid !== String(feid)) {
        state.technicalOptions = null;
        state.technicalOptionsFeid = '';
        state.ociCache.clear();
      }
      const [seriesPayload, salespeoplePayload] = await Promise.all([
        getJson('/series', { feid }),
        getJson('/comerciais', { feid })
      ]);
      state.series = seriesPayload.rows || [];
      state.salespeople = salespeoplePayload.rows || [];
      renderSalespeople();
      setOptions(elements.series, state.series, 'ndos', (row) => `${row.name} · ${row.ndos}`, seriesPayload.default_ndos);
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
    if (isEditing()) return;
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
    if (isEditing()) return;
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

  function setInputValue(element, value) {
    if (element) element.value = value == null ? '' : String(value);
  }

  function renderSalespeople(selectedNumber, selectedName) {
    elements.salesperson.replaceChildren();
    const emptyOption = document.createElement('option');
    emptyOption.value = '';
    emptyOption.textContent = 'Sem comercial';
    elements.salesperson.appendChild(emptyOption);
    state.salespeople.forEach((row) => {
      const option = document.createElement('option');
      option.value = String(row.number || '');
      option.textContent = `${row.name || row.number}${row.inactive ? ' · inativo' : ''}`;
      elements.salesperson.appendChild(option);
    });
    const wanted = String(selectedNumber || '');
    if (wanted && !Array.from(elements.salesperson.options).some((option) => option.value === wanted)) {
      const option = document.createElement('option');
      option.value = wanted;
      option.textContent = selectedName || `Comercial ${wanted}`;
      elements.salesperson.appendChild(option);
    }
    elements.salesperson.value = wanted;
  }

  function money(value, currency) {
    const code = currency || 'EUR';
    try {
      return new Intl.NumberFormat('pt-PT', { style: 'currency', currency: code }).format(Number(value || 0));
    } catch (_) {
      return `${numberFormatter.format(Number(value || 0))} ${code}`;
    }
  }

  function itemPath(line) {
    const value = line && (line.item_label != null && line.item_label !== '' ? line.item_label : line.item);
    const label = String(value == null ? '' : value).trim();
    if (!label) return [{ kind: 1, number: 0, suffix: '' }];
    return label.split('.').map((segment) => {
      const token = segment.trim();
      const match = token.match(/^(\d+)(.*)$/);
      return match
        ? { kind: 0, number: Number.parseInt(match[1], 10), suffix: match[2].trim().toLocaleLowerCase('pt') }
        : { kind: 1, number: 0, suffix: token.toLocaleLowerCase('pt') };
    });
  }

  function compareBudgetLines(left, right) {
    const leftPath = itemPath(left);
    const rightPath = itemPath(right);
    const length = Math.max(leftPath.length, rightPath.length);
    for (let index = 0; index < length; index += 1) {
      if (index >= leftPath.length) return -1;
      if (index >= rightPath.length) return 1;
      const leftSegment = leftPath[index];
      const rightSegment = rightPath[index];
      if (leftSegment.kind !== rightSegment.kind) return leftSegment.kind - rightSegment.kind;
      if (leftSegment.number !== rightSegment.number) return leftSegment.number - rightSegment.number;
      const suffixOrder = leftSegment.suffix.localeCompare(rightSegment.suffix, 'pt', { numeric: true });
      if (suffixOrder) return suffixOrder;
    }
    const orderDifference = finiteNumber(left && left.order) - finiteNumber(right && right.order);
    if (orderDifference) return orderDifference;
    return String((left && left.bistamp) || '').localeCompare(String((right && right.bistamp) || ''));
  }

  function renderDetail(payload) {
    const header = payload.header || {};
    const totals = payload.totals || {};
    const lines = payload.lines || [];
    lines.sort(compareBudgetLines);
    closeClientLookup();
    elements.empty.hidden = true;
    elements.content.hidden = false;

    text('budgetDocumentEyebrow', `Dossier interno · ${header.series || 'Orçamento'}`);
    setInputValue(elements.clientSearch, header.client_name);
    setInputValue(elements.clientNumber, header.client_number);
    setInputValue(elements.clientEstablishment, header.establishment);
    elements.clientMeta.textContent = header.client_number
      ? `Cliente n.º ${header.client_number}${header.establishment ? ` / ${header.establishment}` : ''}`
      : 'Cliente não selecionado';
    setInputValue(elements.workInput, header.work_name);
    setInputValue(elements.localityInput, header.locality || header.place);
    setInputValue(elements.dateInput, header.date);
    setInputValue(elements.attentionInput, header.attention);
    renderSalespeople(header.salesperson_number, header.salesperson);
    text('budgetTotal', money(totals.total, header.currency));
    text('budgetCost', money(totals.cost, header.currency));
    text('budgetMargin', `${percentFormatter.format(Number(totals.margin_percentage || 0))}%`);
    text('budgetProfit', money(totals.profit, header.currency));
    document.getElementById('budgetMargin').closest('.gr-budget-total')
      .classList.toggle('is-threshold-alert', Number(totals.margin_percentage || 0) < 10);
    document.getElementById('budgetProfit').closest('.gr-budget-total')
      .classList.toggle('is-threshold-alert', Number(totals.profit || 0) < 1000);
    text('budgetLineCount', `${lines.length} ${lines.length === 1 ? 'linha' : 'linhas'} · BI + BI2`);

    renderStatuses(header);
    renderLines(lines, header.currency, totals);
  }

  function renderStatuses(header) {
    const statuses = [];
    if (header._draft) statuses.push(['warning', 'fa-pen', 'Novo em edição']);
    if (!header._draft && isEditing()) statuses.push(['warning', 'fa-pen', 'Em edição']);
    if (!header._draft && header.cancelled) statuses.push(['danger', 'fa-ban', 'Anulado']);
    if (!header._draft && header.approved) statuses.push(['success', 'fa-circle-check', 'Aprovado']);
    if (!header._draft && header.awarded) statuses.push(['info', 'fa-trophy', 'Adjudicado']);
    if (!statuses.length) statuses.push(['warning', 'fa-clock', 'Em preparação']);
    document.getElementById('budgetStatus').innerHTML = statuses.map(([kind, icon, label]) =>
      `<span class="sz_badge sz_badge_${kind}"><i class="fa-solid ${icon}"></i>${escapeHtml(label)}</span>`
    ).join('');
  }

  function closeClientLookup() {
    window.clearTimeout(state.clientSearchTimer);
    state.clientRequestVersion += 1;
    state.clientRows = [];
    state.clientActiveIndex = -1;
    if (elements.clientResults) {
      elements.clientResults.hidden = true;
      elements.clientResults.replaceChildren();
    }
  }

  function renderClientMessage(message, danger) {
    state.clientRows = [];
    state.clientActiveIndex = -1;
    elements.clientResults.replaceChildren();
    const item = document.createElement('div');
    item.className = `sz_table_lookup_empty${danger ? ' is-danger' : ''}`;
    item.textContent = message;
    elements.clientResults.appendChild(item);
    elements.clientResults.hidden = false;
  }

  function setClientActive(index) {
    const buttons = Array.from(elements.clientResults.querySelectorAll('.sz_table_lookup_item'));
    if (!buttons.length) {
      state.clientActiveIndex = -1;
      return;
    }
    const next = Math.max(0, Math.min(buttons.length - 1, index));
    buttons.forEach((button, buttonIndex) => button.classList.toggle('is-active', buttonIndex === next));
    state.clientActiveIndex = next;
  }

  function selectClient(row) {
    if (!isEditing()) return;
    if (!row) return;
    setInputValue(elements.clientSearch, row.name);
    setInputValue(elements.clientNumber, row.number);
    setInputValue(elements.clientEstablishment, row.establishment);
    elements.clientMeta.textContent = row.number
      ? `Cliente n.º ${row.number}${row.establishment ? ` / ${row.establishment}` : ''}`
      : 'Cliente selecionado';
    if (row.contact) setInputValue(elements.attentionInput, row.contact);
    if (row.salesperson_number) {
      renderSalespeople(row.salesperson_number, row.salesperson);
    }
    closeClientLookup();
    elements.clientSearch.focus();
  }

  function renderClientRows(rows) {
    state.clientRows = Array.isArray(rows) ? rows : [];
    elements.clientResults.replaceChildren();
    if (!state.clientRows.length) {
      renderClientMessage('Sem resultados');
      return;
    }
    state.clientRows.forEach((row, index) => {
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'sz_table_lookup_item';
      const title = document.createElement('span');
      title.className = 'sz_table_lookup_item_label';
      title.textContent = row.name || `Cliente ${row.number}`;
      const meta = document.createElement('span');
      meta.className = 'sz_table_lookup_item_value';
      meta.textContent = [
        row.number ? `N.º ${row.number}` : '',
        row.vat_number ? `NIF ${row.vat_number}` : '',
        row.locality || ''
      ].filter(Boolean).join(' · ');
      button.append(title, meta);
      button.addEventListener('mouseenter', () => setClientActive(index));
      button.addEventListener('mousedown', (event) => {
        event.preventDefault();
        selectClient(row);
      });
      elements.clientResults.appendChild(button);
    });
    elements.clientResults.hidden = false;
    setClientActive(0);
  }

  function scheduleClientSearch() {
    if (!isEditing()) {
      closeClientLookup();
      return;
    }
    window.clearTimeout(state.clientSearchTimer);
    const query = elements.clientSearch.value.trim();
    if (!query) {
      closeClientLookup();
      return;
    }
    state.clientSearchTimer = window.setTimeout(async () => {
      const version = ++state.clientRequestVersion;
      renderClientMessage('A procurar…');
      try {
        const payload = await getJson('/clientes', { feid: elements.company.value, q: query });
        if (version !== state.clientRequestVersion) return;
        renderClientRows(payload.rows || []);
      } catch (error) {
        if (version !== state.clientRequestVersion) return;
        renderClientMessage(error.message || 'Erro na pesquisa', true);
      }
    }, 250);
  }

  function renderLines(lines, currency, totals) {
    elements.lines.innerHTML = lines.map((line, index) => {
      const title = line.designation || line.description || 'Linha sem designação';
      const secondary = line.description && line.description !== line.designation ? line.description : '';
      const plusValue = isPlusValue(line.reference);
      const technicalControl = plusValue
        ? '<span class="sz_text_muted">—</span>'
        : `<button type="button" class="sz_button sz_button_ghost gr-budget-technical-button" data-technical-line="${index}" aria-label="Abrir detalhe técnico da linha ${escapeHtml(line.item_label || line.item || index + 1)}" title="Detalhe técnico (OCI)">+</button>`;
      return `<tr class="sz_table_row${plusValue ? ' is-plus-value' : ''}">
        <td class="gr-budget-num">${escapeHtml(line.item_label || line.item || index + 1)}</td>
        <td>${escapeHtml(line.reference || '—')}</td>
        <td title="${escapeHtml(secondary || title)}"><div class="gr-budget-line-title">${escapeHtml(title)}</div>${secondary ? `<div class="gr-budget-line-subtitle">${escapeHtml(secondary)}</div>` : ''}</td>
        <td class="gr-budget-num">${quantityFormatter.format(Number(line.quantity || 0))}</td>
        <td>${escapeHtml(line.unit || '—')}</td>
        <td class="gr-budget-num">${quantityFormatter.format(Number(line.thickness || 0))}</td>
        <td class="gr-budget-num">${lineAmountFormatter.format(Number(line.unit_price || 0))}</td>
        <td class="gr-budget-num"><strong>${lineAmountFormatter.format(Number(line.total || 0))}</strong></td>
        <td class="gr-budget-check">${technicalControl}</td>
        <td class="gr-budget-num">${lineAmountFormatter.format(Number(line.cost_total || 0))}</td>
        <td class="gr-budget-num">${percentFormatter.format(Number(line.margin_percentage || 0))}%</td>
        <td class="gr-budget-num">${lineAmountFormatter.format(Number(line.profit || 0))}</td>
      </tr>`;
    }).join('');
    elements.linesFooter.innerHTML = `<tr>
      <td colspan="7">Totais · ${escapeHtml(lines.length)} linhas</td>
      <td class="gr-budget-num">${escapeHtml(money(totals.total, currency))}</td>
      <td></td>
      <td class="gr-budget-num">${escapeHtml(money(totals.cost, currency))}</td>
      <td class="gr-budget-num">${percentFormatter.format(Number(totals.margin_percentage || 0))}%</td>
      <td class="gr-budget-num">${escapeHtml(money(totals.profit, currency))}</td>
    </tr>`;
  }

  function cloneData(value) {
    return JSON.parse(JSON.stringify(value == null ? null : value));
  }

  function numericInput(element) {
    if (!element) return 0;
    if (typeof element.valueAsNumber === 'number' && Number.isFinite(element.valueAsNumber)) {
      return element.valueAsNumber;
    }
    let raw = String(element.value == null ? '' : element.value).trim().replace(/[\s\u00a0]/g, '');
    if (raw.includes(',') && raw.includes('.')) {
      raw = raw.lastIndexOf(',') > raw.lastIndexOf('.')
        ? raw.replaceAll('.', '').replace(',', '.')
        : raw.replaceAll(',', '');
    } else {
      raw = raw.replace(',', '.');
    }
    const value = Number.parseFloat(raw);
    return Number.isFinite(value) ? value : 0;
  }

  function finiteNumber(value, fallback) {
    const number = Number(value);
    return Number.isFinite(number) ? number : (fallback == null ? 0 : fallback);
  }

  function setNumericInput(element, value, decimals) {
    const number = Number(value || 0);
    if (!element) return;
    element.value = Number.isFinite(number) ? number.toFixed(decimals == null ? 4 : decimals).replace(/\.?0+$/, '') : '0';
  }

  function setCostDisplay(element, value) {
    if (!element) return;
    const number = finiteNumber(value);
    if (number > 0) element.dataset.lastValidCost = String(number);
    element.value = numberFormatter.format(number);
  }

  function showOciError(message) {
    elements.ociError.textContent = message || '';
    elements.ociError.hidden = !message;
  }

  async function ensureTechnicalOptions() {
    const feid = String(elements.company.value || '');
    if (state.technicalOptions && state.technicalOptionsFeid === feid) return state.technicalOptions;
    const payload = await getJson('/opcoes-tecnicas', { feid });
    state.technicalOptions = {
      ouvrages: payload.ouvrages || [],
      formulas: payload.formulas || [],
      componentFamilies: payload.component_families || [],
      components: payload.components || [],
      units: payload.units || []
    };
    state.technicalOptionsFeid = feid;
    return state.technicalOptions;
  }

  function blankBudgetLine() {
    const lines = (state.detail && state.detail.lines) || [];
    const nextItem = lines.reduce((maximum, line) => Math.max(maximum, Number(line.item || 0)), 0) + 1;
    return {
      bistamp: `draft-line-${Date.now()}`,
      order: nextItem * 10000,
      item: nextItem,
      reference: '',
      designation: '',
      description: '',
      quantity: 0,
      surface: 0,
      unit: 'm²',
      thickness: 0,
      volume: 0,
      unit_cost: 0,
      cost_total: 0,
      unit_price: 0,
      total: 0,
      margin_per_unit: 0,
      margin_value: 0,
      margin_percentage: 0,
      profit: 0,
      has_technical_detail: false,
      simultaneous: false,
      variant: false,
      option: false,
      blocked_price: false,
      pump: false,
      labour: false,
      pro_rata: false
    };
  }

  function blankOciRow() {
    const surface = numericInput(elements.ociSurface);
    const thickness = numericInput(elements.ociThickness);
    return {
      stamp: `draft-oci-${Date.now()}-${Math.random().toString(16).slice(2)}`,
      family: '',
      reference: '',
      designation: '',
      source_designation: '',
      formula: '',
      purchase_price: 0,
      forfait: 0,
      area: surface,
      thickness,
      volume: surface * thickness,
      weight: 0,
      consumption: 0,
      coefficient: 0,
      quantity: 1,
      total_quantity: surface,
      cost_per_unit: 0,
      unit: '',
      is_plus_value: false
    };
  }

  function componentOptions() {
    return state.technicalOptions || { componentFamilies: [], components: [], units: [] };
  }

  function normalizedCode(value) {
    return String(value || '').trim().toUpperCase();
  }

  function isPlusValue(reference) {
    return ['PVL', 'MVL'].includes(normalizedCode(reference));
  }

  function componentArticlesForFamily(familyReference) {
    const family = normalizedCode(familyReference);
    const ouvrage = normalizedCode(elements.ociReference.value || (state.ociContext && state.ociContext.line.reference));
    let articles = (componentOptions().components || []).filter((row) => normalizedCode(row.family) === family);
    if (family === 'BETON') {
      if (ouvrage === 'CBD') {
        const allowed = new Set(['4/8-ROULE-MATHAY', '4/8-ROULE-RHIN', '6/10-CONC-MATHAY', '6/10-CONC-RAONET', '6/10-CONC-TABENT', '6/15-ROULE-MOSELLE']);
        articles = articles.filter((row) => allowed.has(normalizedCode(row.reference)));
      } else if (ouvrage === 'DTE') {
        articles = articles.filter((row) => ['XF2', 'XD3', 'XA'].some((token) => normalizedCode(row.designation).includes(token)));
      } else if (ouvrage === 'DTI') {
        articles = articles.filter((row) => ['XF1', 'XA'].some((token) => normalizedCode(row.designation).includes(token)));
      }
    } else if (family === 'ARMATURES') {
      const structuralBars = new Set(['BARRES-HA-12', 'BARRES-HA-14', 'BARRES-HA-16']);
      articles = articles.filter((row) => ouvrage === 'CBA'
        ? structuralBars.has(normalizedCode(row.reference))
        : !structuralBars.has(normalizedCode(row.reference)));
    } else if (family === 'FINITION' && ['CBD', 'CBI'].includes(ouvrage)) {
      const wanted = ouvrage === 'CBD' ? 'DESACTIVEE' : 'IMPRIMEE';
      articles = articles.filter((row) => normalizedCode(row.reference) === wanted);
    }
    return articles;
  }

  function usedComponentFamilies() {
    return new Set(collectOciRows().map((row) => normalizedCode(row.family)).filter(Boolean));
  }

  function componentFamilyButtonsMarkup(families, activeFamily, dataAttribute) {
    const usedFamilies = usedComponentFamilies();
    return families.map((family) => {
      const active = normalizedCode(family.reference) === normalizedCode(activeFamily) ? ' is-active' : '';
      const used = usedFamilies.has(normalizedCode(family.reference)) ? ' is-used' : '';
      const count = componentArticlesForFamily(family.reference).length;
      return `<button type="button" class="gr-budget-component-family${active}${used}" ${dataAttribute}="${escapeHtml(family.reference)}" title="${escapeHtml(family.name || family.reference)}">
        <span>${escapeHtml(family.name || family.reference)}</span>
        <span class="gr-budget-component-family-count">${escapeHtml(count)}</span>
      </button>`;
    }).join('');
  }

  function renderOciFamilySidebar() {
    if (!elements.ociFamilyList || !elements.ociFamilyCount) return;
    const families = componentOptions().componentFamilies || [];
    elements.ociFamilyCount.textContent = String(families.length);
    elements.ociFamilyList.innerHTML = componentFamilyButtonsMarkup(families, '', 'data-oci-family-add');
  }

  function renderComponentArticles() {
    const options = componentOptions();
    const family = (options.componentFamilies || []).find((row) => row.reference === state.componentFamily);
    const articles = componentArticlesForFamily(state.componentFamily);
    elements.componentFamilyTitle.textContent = family ? family.name : 'Artigos';
    elements.componentArticleCount.textContent = `${articles.length} ${articles.length === 1 ? 'artigo' : 'artigos'}`;
    if (!articles.some((row) => row.stamp === state.componentStamp)) state.componentStamp = '';
    elements.componentArticles.innerHTML = articles.length ? articles.map((article) => {
      const selected = article.stamp === state.componentStamp ? ' is-selected' : '';
      return `<tr class="sz_table_row${selected}" data-component-stamp="${escapeHtml(article.stamp)}" tabindex="0" aria-selected="${selected ? 'true' : 'false'}">
        <td><strong>${escapeHtml(article.reference || '—')}</strong></td>
        <td>${escapeHtml(article.designation || '—')}</td>
        <td>${escapeHtml(article.unit || '—')}</td>
        <td class="gr-budget-num">${lineAmountFormatter.format(Number(article.purchase_price || 0))}</td>
        <td>${escapeHtml(article.formula || '—')}</td>
      </tr>`;
    }).join('') : '<tr><td colspan="5" class="sz_text_muted">Esta família não tem artigos disponíveis para o ouvrage selecionado.</td></tr>';
    updateComponentSelection();
  }

  function selectedComponent() {
    return (componentOptions().components || []).find((row) => row.stamp === state.componentStamp) || null;
  }

  function updateComponentSelection() {
    const article = selectedComponent();
    elements.componentConfirm.disabled = !article;
    elements.componentSelection.textContent = article
      ? `${article.reference} · ${article.designation}`
      : 'Selecione um artigo.';
    elements.componentArticles.querySelectorAll('[data-component-stamp]').forEach((row) => {
      const selected = row.dataset.componentStamp === state.componentStamp;
      row.classList.toggle('is-selected', selected);
      row.setAttribute('aria-selected', selected ? 'true' : 'false');
    });
  }

  function selectComponent(stamp) {
    state.componentStamp = String(stamp || '');
    updateComponentSelection();
  }

  function openComponentPicker(familyReference) {
    const families = componentOptions().componentFamilies || [];
    if (!families.length) {
      showOciError('Não existem famílias de componentes configuradas para esta empresa.');
      return;
    }
    const requestedFamily = typeof familyReference === 'string'
      ? families.find((family) => normalizedCode(family.reference) === normalizedCode(familyReference))
      : null;
    state.componentFamily = (requestedFamily || families[0]).reference;
    state.componentStamp = '';
    renderComponentArticles();
    elements.componentPicker.classList.add('sz_is_open');
    elements.componentPicker.setAttribute('aria-hidden', 'false');
    const firstArticle = elements.componentArticles.querySelector('[data-component-stamp]');
    if (firstArticle) firstArticle.focus();
  }

  function closeComponentPicker() {
    elements.componentPicker.classList.remove('sz_is_open');
    elements.componentPicker.setAttribute('aria-hidden', 'true');
    state.componentStamp = '';
  }

  function componentToOciRow(article) {
    return {
      ...blankOciRow(),
      family: article.family || '',
      reference: article.reference || '',
      designation: article.designation || '',
      source_designation: article.designation || '',
      formula: article.formula || '',
      purchase_price: Number(article.purchase_price || 0),
      forfait: Number(article.forfait || 0),
      unit: article.unit || '',
      is_plus_value: isPlusValue(article.reference)
    };
  }

  function confirmComponent() {
    const article = selectedComponent();
    if (!article) return;
    closeComponentPicker();
    const lastRow = appendOciRow(componentToOciRow(article));
    const firstEditable = lastRow && lastRow.querySelector('[data-oci-field="designation"]');
    if (firstEditable) firstEditable.focus();
  }

  function formulaOptions(selectedValue) {
    const formulas = (state.technicalOptions && state.technicalOptions.formulas) || [];
    return ['<option value="">Sem fórmula</option>'].concat(formulas.map((row) => {
      const selected = String(row.name) === String(selectedValue || '') ? ' selected' : '';
      return `<option value="${escapeHtml(row.name)}"${selected}>${escapeHtml(row.name)}</option>`;
    })).join('');
  }

  function unitOptions(selectedValue) {
    const units = componentOptions().units || [];
    const selected = String(selectedValue || '').trim();
    const values = selected && !units.includes(selected) ? [selected, ...units] : units;
    return ['<option value="">—</option>'].concat(values.map((unit) => {
      const isSelected = String(unit) === selected ? ' selected' : '';
      return `<option value="${escapeHtml(unit)}"${isSelected}>${escapeHtml(unit)}</option>`;
    })).join('');
  }

  function ociRowMarkup(row) {
    const plusValue = Boolean(row.is_plus_value || isPlusValue(row.reference));
    const sourceDesignation = row.source_designation || row.designation || '';
    const suppliedCost = Number(row.cost_per_unit);
    const initialCost = Number.isFinite(suppliedCost) && suppliedCost > 0
      ? suppliedCost
      : finiteNumber(calculateBaseOciRowCost(row));
    const unitControl = plusValue
      ? `<select class="sz_select" data-oci-field="unit">${unitOptions(row.unit)}</select>`
      : `<input class="sz_input" data-oci-field="unit" value="${escapeHtml(row.unit || '')}" maxlength="4" readonly>`;
    return `<tr class="sz_table_row${plusValue ? ' is-plus-value' : ''}" data-oci-stamp="${escapeHtml(row.stamp || '')}" data-oci-family="${escapeHtml(row.family || '')}" data-oci-reference="${escapeHtml(row.reference || '')}" data-oci-quantity="${escapeHtml(row.quantity == null ? 1 : row.quantity)}" data-oci-total-quantity="${escapeHtml(row.total_quantity || 0)}" data-oci-source-designation="${escapeHtml(sourceDesignation)}" data-oci-plus-value="${plusValue ? '1' : '0'}">
      <td data-oci-cell="designation"><input class="sz_input" data-oci-field="designation" value="${escapeHtml(row.designation || '')}" maxlength="220"></td>
      <td data-oci-cell="formula"><select class="sz_select" data-oci-field="formula">${formulaOptions(row.formula)}</select></td>
      <td data-oci-cell="purchase_price"><input class="sz_input gr-budget-number-input" data-oci-field="purchase_price" type="number" min="0" step="0.0001" value="${escapeHtml(row.purchase_price || 0)}"></td>
      <td data-oci-cell="forfait"><input class="sz_input gr-budget-number-input" data-oci-field="forfait" type="number" min="0" step="0.01" value="${escapeHtml(row.forfait || 0)}"></td>
      <td data-oci-cell="area"><input class="sz_input gr-budget-number-input" data-oci-field="area" type="number" min="0" step="0.01" value="${escapeHtml(row.area || 0)}" readonly></td>
      <td data-oci-cell="thickness"><input class="sz_input gr-budget-number-input" data-oci-field="thickness" type="number" min="0" step="0.001" value="${escapeHtml(row.thickness || 0)}" readonly></td>
      <td data-oci-cell="volume"><input class="sz_input gr-budget-number-input" data-oci-field="volume" type="number" min="0" step="0.001" value="${escapeHtml(row.volume || 0)}" readonly></td>
      <td data-oci-cell="weight"><input class="sz_input gr-budget-number-input" data-oci-field="weight" type="number" min="0" step="0.01" value="${escapeHtml(row.weight || 0)}"></td>
      <td data-oci-cell="consumption"><input class="sz_input gr-budget-number-input" data-oci-field="consumption" type="number" min="0" step="0.0001" value="${escapeHtml(row.consumption || 0)}"></td>
      <td data-oci-cell="coefficient"><input class="sz_input gr-budget-number-input" data-oci-field="coefficient" type="number" min="0" step="0.0001" value="${escapeHtml(row.coefficient || 0)}"></td>
      <td data-oci-cell="cost"><input class="sz_input gr-budget-number-input" data-oci-cost data-last-valid-cost="${initialCost > 0 ? escapeHtml(initialCost) : ''}" type="text" inputmode="decimal" readonly value="${escapeHtml(numberFormatter.format(initialCost))}"></td>
      <td data-oci-cell="unit">${unitControl}</td>
      <td><button type="button" class="sz_button sz_button_ghost gr-budget-oci-delete" data-oci-delete title="Remover componente" aria-label="Remover componente"><i class="fa-solid fa-trash-can" aria-hidden="true"></i></button></td>
    </tr>`;
  }

  function renderOciRows(rows) {
    const safeRows = Array.isArray(rows) ? rows : [];
    elements.ociRows.innerHTML = safeRows.map(ociRowMarkup).join('');
    text('budgetOciRowCount', `${safeRows.length} ${safeRows.length === 1 ? 'linha' : 'linhas'} · OCI`);
    elements.ociRows.querySelectorAll('tr').forEach(updateOciRowFormulaState);
    recalculateOci();
    renderOciFamilySidebar();
  }

  function appendOciRow(row) {
    elements.ociRows.insertAdjacentHTML('beforeend', ociRowMarkup(row));
    const appendedRow = elements.ociRows.lastElementChild;
    if (appendedRow) updateOciRowFormulaState(appendedRow);
    const rowCount = elements.ociRows.querySelectorAll('tr').length;
    text('budgetOciRowCount', `${rowCount} ${rowCount === 1 ? 'linha' : 'linhas'} · OCI`);
    recalculateOci();
    renderOciFamilySidebar();
    return appendedRow;
  }

  function ociRowValue(row, field) {
    const input = row.querySelector(`[data-oci-field="${field}"]`);
    if (!input) {
      if (field === 'family') return row.dataset.ociFamily || '';
      if (field === 'reference') return row.dataset.ociReference || '';
      return '';
    }
    if (input.type === 'number') return numericInput(input);
    return input.value.trim();
  }

  function collectOciRows() {
    return Array.from(elements.ociRows.querySelectorAll('tr')).map((row) => ({
      stamp: row.dataset.ociStamp || '',
      family: ociRowValue(row, 'family'),
      reference: ociRowValue(row, 'reference'),
      designation: ociRowValue(row, 'designation'),
      formula: ociRowValue(row, 'formula'),
      purchase_price: ociRowValue(row, 'purchase_price'),
      forfait: ociRowValue(row, 'forfait'),
      area: ociRowValue(row, 'area'),
      thickness: ociRowValue(row, 'thickness'),
      volume: ociRowValue(row, 'volume'),
      weight: ociRowValue(row, 'weight'),
      consumption: ociRowValue(row, 'consumption'),
      coefficient: ociRowValue(row, 'coefficient'),
      quantity: finiteNumber(row.dataset.ociQuantity, 1),
      total_quantity: finiteNumber(row.dataset.ociTotalQuantity),
      cost_per_unit: numericInput(row.querySelector('[data-oci-cost]')),
      unit: ociRowValue(row, 'unit'),
      source_designation: row.dataset.ociSourceDesignation || ociRowValue(row, 'designation'),
      is_plus_value: row.dataset.ociPlusValue === '1'
    }));
  }

  function normalizedFormula(value) {
    return String(value || '')
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '')
      .replace(/\s+/g, ' ')
      .trim()
      .toUpperCase();
  }

  function updateOciRowFormulaState(row) {
    const formula = normalizedFormula(ociRowValue(row, 'formula'));
    const activeFields = new Set();
    if (formula !== 'PAR CLIENT') activeFields.add('purchase_price');
    if (formula === 'FORFAIT SURFACE') activeFields.add('forfait');
    if (['FORFAIT SURFACE', 'PA X ML / SURFACE', 'PA X SURFACE', 'RAPPORT POIDS / SURFACE', 'PA / SURFACE', 'PA X QUANTITE M3'].includes(formula)) activeFields.add('area');
    if (['PA X EPAISSEUR', 'PA X EPAISSEUR X POIDS'].includes(formula)) activeFields.add('thickness');
    if (formula === 'PA X QUANTITE M3') activeFields.add('volume');
    if (formula === 'PA X EPAISSEUR X POIDS') activeFields.add('weight');
    if (['QUANTITE CONSOMMEE', 'RAPPORT POIDS / SURFACE'].includes(formula)) activeFields.add('consumption');
    if (['PRIX / COEFFICIENT', 'PA X ML', 'PA X ML / SURFACE'].includes(formula)) activeFields.add('coefficient');
    row.querySelectorAll('[data-oci-cell]').forEach((cell) => {
      cell.classList.toggle('is-formula-input', activeFields.has(cell.dataset.ociCell));
    });
  }

  function calculateBaseOciRowCost(row) {
    const area = finiteNumber(row.area);
    const purchasePrice = finiteNumber(row.purchase_price);
    const thickness = finiteNumber(row.thickness);
    const weight = finiteNumber(row.weight);
    const consumption = finiteNumber(row.consumption);
    const coefficient = finiteNumber(row.coefficient);
    const volume = finiteNumber(row.volume);
    const formula = normalizedFormula(row.formula);
    if (formula === 'PAR CLIENT') return 0;
    if (formula.includes('PRIX / COEFFICIENT')) return coefficient ? purchasePrice / coefficient : 0;
    if (formula.includes('ML / SURFACE')) return area ? purchasePrice * coefficient / area : 0;
    if (formula.includes('PA X ML')) return purchasePrice * coefficient;
    if (formula.includes('QUANTITE M3')) return area ? purchasePrice * volume / area : 0;
    if (formula.includes('EPAISSEUR X POIDS')) return purchasePrice * thickness * weight;
    if (formula.includes('EPAISSEUR')) return purchasePrice * thickness;
    if (formula.includes('QUANTITE CONSOMMEE') || formula.includes('RAPPORT POIDS')) return purchasePrice * consumption;
    if (formula.includes('PA / SURFACE')) return area ? purchasePrice / area : 0;
    if (formula.includes('PRIX FIXE') || formula.includes('PA X SURFACE') || formula.includes('FORFAIT SURFACE')) return purchasePrice;
    return purchasePrice * finiteNumber(row.quantity, 1);
  }

  function currentTechnicalFlags() {
    const rows = collectOciRows().filter((row) => !row.is_plus_value);
    return {
      pump: rows.some((row) => normalizedCode(row.family) === 'APPROBETON'),
      labour: rows.some((row) => normalizedCode(row.family) === 'FINITION')
    };
  }

  function simultaneousTotals() {
    const totals = { m3sim: 0, m3nonsim: 0, m2mosim: 0, m2mononsim: 0 };
    const lines = (state.detail && state.detail.lines) || [];
    const context = state.ociContext || {};
    lines.forEach((line, index) => {
      if ((!context.newLine && index === context.lineIndex) || (context.line && line.bistamp === context.line.bistamp)) return;
      const surface = Number(line.surface == null ? line.quantity : line.surface) || 0;
      const volume = surface * (Number(line.thickness) || 0);
      if (line.pump) totals[line.simultaneous ? 'm3sim' : 'm3nonsim'] += volume;
      if (line.labour) totals[line.simultaneous ? 'm2mosim' : 'm2mononsim'] += surface;
    });
    const surface = numericInput(elements.ociSurface);
    const volume = surface * numericInput(elements.ociThickness);
    const flags = currentTechnicalFlags();
    elements.ociPump.checked = flags.pump;
    elements.ociLabour.checked = flags.labour;
    if (flags.pump) totals[elements.ociSimultaneous.checked ? 'm3sim' : 'm3nonsim'] += volume;
    if (flags.labour) totals[elements.ociSimultaneous.checked ? 'm2mosim' : 'm2mononsim'] += surface;
    elements.ociM3Sim.textContent = numberFormatter.format(totals.m3sim);
    elements.ociM3NonSim.textContent = numberFormatter.format(totals.m3nonsim);
    elements.ociM2MoSim.textContent = numberFormatter.format(totals.m2mosim);
    elements.ociM2MoNonSim.textContent = numberFormatter.format(totals.m2mononsim);
    return totals;
  }

  function calculateOciRowCost(row, totals) {
    const baseCost = finiteNumber(calculateBaseOciRowCost(row));
    const forfait = finiteNumber(row.forfait);
    const area = finiteNumber(row.area);
    if (forfait <= 0 || area <= 0) return baseCost;
    if (!elements.ociSimultaneous.checked) return baseCost * area < forfait ? forfait / area : baseCost;

    const family = normalizedCode(row.family);
    const purchasePrice = finiteNumber(row.purchase_price);
    if (family === 'APPROBETON') {
      const sharedVolume = finiteNumber(totals.m3sim);
      if (sharedVolume > 0 && purchasePrice * sharedVolume < forfait) {
        return (forfait / sharedVolume * Number(row.volume || 0)) / area;
      }
    }
    if (family === 'FINITION') {
      const sharedArea = finiteNumber(totals.m2mosim);
      if (sharedArea > 0 && purchasePrice * sharedArea < forfait) return forfait / sharedArea;
    }
    return baseCost;
  }

  function updatePriceDriver() {
    elements.ociBlockedPrice.checked = state.ociPriceLocked;
    elements.ociSalePriceField.classList.toggle('is-active', state.ociPriceLocked);
    elements.ociMarginPercentField.classList.toggle('is-active', !state.ociPriceLocked);
  }

  function stableOciRowCost(element, row, totals) {
    const calculatedCost = finiteNumber(calculateOciRowCost(row, totals));
    const currentCost = numericInput(element);
    const lastValidCost = element && element.dataset.lastValidCost
      ? finiteNumber(element.dataset.lastValidCost)
      : currentCost;
    if (calculatedCost === 0 && lastValidCost > 0 && normalizedFormula(row.formula) !== 'PAR CLIENT') {
      return lastValidCost;
    }
    return calculatedCost;
  }

  function recalculateOci() {
    const surface = numericInput(elements.ociSurface);
    const thickness = numericInput(elements.ociThickness);
    const volume = surface * thickness;
    const tableRows = Array.from(elements.ociRows.querySelectorAll('tr'));
    setNumericInput(elements.ociVolume, volume, 4);
    tableRows.forEach((row) => {
      setNumericInput(row.querySelector('[data-oci-field="area"]'), surface, 4);
      setNumericInput(row.querySelector('[data-oci-field="thickness"]'), thickness, 4);
      setNumericInput(row.querySelector('[data-oci-field="volume"]'), volume, 4);
      const quantity = finiteNumber(row.dataset.ociQuantity, 1);
      row.dataset.ociTotalQuantity = String(quantity * surface);
    });

    const totals = simultaneousTotals();
    tableRows.forEach((tableRow) => {
      const row = collectSingleOciRow(tableRow);
      const costElement = tableRow.querySelector('[data-oci-cost]');
      setCostDisplay(costElement, stableOciRowCost(costElement, row, totals));
    });
    let purchasePrice = tableRows.reduce((sum, tableRow) => {
      if (tableRow.dataset.ociPlusValue === '1') return sum;
      return sum + numericInput(tableRow.querySelector('[data-oci-cost]'));
    }, 0.1);
    purchasePrice = finiteNumber(purchasePrice, 0.1);

    const prorata = Math.min(99.99, Math.max(0, numericInput(elements.ociProrata)));
    const purchaseTotal = purchasePrice * surface;
    let salePrice = numericInput(elements.ociSalePrice);
    if (!state.ociPriceLocked) {
      const targetMargin = Math.min(99.99, Math.max(-999.99, Number(state.ociTargetMargin || 0)));
      const marginFactor = 1 - targetMargin / 100;
      const prorataFactor = 1 - prorata / 100;
      salePrice = marginFactor > 0 && prorataFactor > 0 ? purchasePrice / marginFactor / prorataFactor : 0;
      setNumericInput(elements.ociSalePrice, salePrice, 4);
    }
    const saleTotal = salePrice * surface * (1 - prorata / 100);
    const marginUnit = salePrice - purchasePrice;
    const marginTotal = saleTotal - purchaseTotal;
    const marginPercentage = saleTotal ? marginTotal / saleTotal * 100 : 0;
    setNumericInput(elements.ociPurchasePrice, purchasePrice, 4);
    setNumericInput(elements.ociPurchaseTotal, purchaseTotal, 2);
    setNumericInput(elements.ociSaleTotal, saleTotal, 2);
    setNumericInput(elements.ociMarginUnit, marginUnit, 4);
    setNumericInput(elements.ociMarginTotal, marginTotal, 2);
    setNumericInput(elements.ociMarginPercent, marginPercentage, 2);
    if (state.ociPriceLocked) state.ociTargetMargin = marginPercentage;
    updatePriceDriver();

    const rowCount = elements.ociRows.querySelectorAll('tr').length;
    elements.ociFooter.innerHTML = `<tr><td colspan="10">Totais · ${rowCount} ${rowCount === 1 ? 'linha' : 'linhas'} OCI · inclui 0,10 de frais d'étude</td><td class="gr-budget-num">${lineAmountFormatter.format(purchasePrice)}</td><td></td><td></td></tr>`;
  }

  function collectSingleOciRow(row) {
    return {
      formula: ociRowValue(row, 'formula'),
      purchase_price: ociRowValue(row, 'purchase_price'),
      forfait: ociRowValue(row, 'forfait'),
      area: ociRowValue(row, 'area'),
      thickness: ociRowValue(row, 'thickness'),
      volume: ociRowValue(row, 'volume'),
      weight: ociRowValue(row, 'weight'),
      consumption: ociRowValue(row, 'consumption'),
      coefficient: ociRowValue(row, 'coefficient'),
      quantity: finiteNumber(row.dataset.ociQuantity, 1),
      family: ociRowValue(row, 'family')
    };
  }

  function syncOciDimensions() {
    recalculateOci();
  }

  function populateOuvrageOptions(selectedReference) {
    const ouvrages = (state.technicalOptions && state.technicalOptions.ouvrages) || [];
    elements.ociOuvrage.replaceChildren();
    const empty = document.createElement('option');
    empty.value = '';
    empty.textContent = 'Selecionar tipo de ouvrage';
    elements.ociOuvrage.appendChild(empty);
    ouvrages.forEach((row) => {
      const option = document.createElement('option');
      option.value = row.reference;
      option.textContent = `${row.reference} · ${row.designation}`;
      elements.ociOuvrage.appendChild(option);
    });
    elements.ociOuvrage.value = selectedReference || '';
  }

  function budgetProrata() {
    const lines = ((state.detail && state.detail.lines) || []).slice().reverse();
    const line = lines.find((row) => Number(row.discount_2 || 0) > 0);
    return Number((line && line.discount_2) || 0);
  }

  function renderOciView(line, rows, newLine) {
    populateOuvrageOptions(line.reference);
    setInputValue(elements.ociPosition, line.item);
    setInputValue(elements.ociReference, line.reference);
    setInputValue(elements.ociDesignation, line.designation);
    setInputValue(elements.ociDescription, line.description || line.designation);
    setNumericInput(elements.ociSurface, line.surface == null ? line.quantity : line.surface, 4);
    setInputValue(elements.ociUnit, line.unit || 'm²');
    setNumericInput(elements.ociThickness, line.thickness, 4);
    setNumericInput(elements.ociSalePrice, line.unit_price, 4);
    setNumericInput(elements.ociProrata, Number(line.discount_2 || 0) > 0 ? line.discount_2 : budgetProrata(), 2);
    state.ociPriceLocked = newLine ? true : Boolean(line.blocked_price || !Number(line.margin_percentage || 0));
    state.ociTargetMargin = Number(line.margin_percentage || 0);
    elements.ociSimultaneous.checked = Boolean(line.simultaneous);
    elements.ociVariant.checked = Boolean(line.variant);
    elements.ociOption.checked = Boolean(line.option);
    elements.ociBlockedPrice.checked = Boolean(line.blocked_price);
    elements.ociPump.checked = Boolean(line.pump);
    elements.ociLabour.checked = Boolean(line.labour);
    elements.ociMode.textContent = newLine ? 'Nova linha' : `Linha ${line.item || '—'}`;
    elements.ociMode.className = `sz_badge ${newLine ? 'sz_badge_warning' : 'sz_badge_info'}`;
    const budgetHeader = (state.detail && state.detail.header) || {};
    elements.ociSubtitle.textContent = `${budgetHeader.series || 'Orçamento'} ${budgetHeader.number || 'novo'} · ${line.reference || 'Sem referência'}${line.designation ? ` — ${line.designation}` : ''}`;
    updateOciPositionsTrigger();
    showOciError('');
    renderOciRows(rows);
    syncOciDimensions();
    elements.contextbar.hidden = true;
    elements.body.hidden = true;
    elements.ociView.hidden = false;
    root.classList.add('is-oci');
  }

  function positionLabel(line, index) {
    return String((line && (line.item_label || line.item)) || index + 1).trim();
  }

  function isCurrentOciPosition(line, index) {
    const context = state.ociContext;
    if (!context || context.newLine) return false;
    if (context.line && context.line.bistamp && line && line.bistamp === context.line.bistamp) return true;
    return index === context.lineIndex;
  }

  function updateOciPositionsTrigger() {
    const lines = (state.detail && state.detail.lines) || [];
    const count = lines.length;
    elements.ociPositions.hidden = count <= 1;
    elements.ociPositionsCount.textContent = `${count} ${count === 1 ? 'posição' : 'posições'}`;
  }

  function positionCardMarkup(line, index, currency) {
    const label = positionLabel(line, index);
    const current = isCurrentOciPosition(line, index);
    const subposition = label.includes('.');
    const description = line.description || line.designation || 'Posição sem descrição';
    const quantity = Number(line.surface == null ? line.quantity || 0 : line.surface);
    const thickness = Number(line.thickness || 0);
    const volume = Number(line.volume == null ? quantity * thickness : line.volume);
    const unit = String(line.unit || 'm²').trim();
    const cost = Number(line._technical_cost_total == null ? line.cost_total || 0 : line._technical_cost_total);
    const sale = Number(line._technical_total == null ? line.total || 0 : line._technical_total);
    const margin = Number(line._technical_profit == null
      ? (line.profit == null ? line.margin_value || 0 : line.profit)
      : line._technical_profit);
    const marginPercentage = Number(line.margin_percentage || 0);
    const classes = `${current ? ' is-current' : ''}${subposition ? ' is-subposition' : ''}`;
    const stateLabel = current ? 'Posição atual' : (subposition ? 'Subposição' : 'Posição');
    return `<button type="button" class="gr-budget-position-card${classes}" data-position-line="${index}" title="${stateLabel} ${escapeHtml(label)}"${current ? ' aria-current="true"' : ''}>
      <span class="gr-budget-position-number">${escapeHtml(label)}</span>
      <span class="gr-budget-position-card-content">
        <span class="gr-budget-position-description">${escapeHtml(description)}</span>
        <span class="gr-budget-position-quantity">Qtd.: ${quantityFormatter.format(quantity)} ${escapeHtml(unit)} × ${quantityFormatter.format(thickness)} m = ${quantityFormatter.format(volume)} m³</span>
      </span>
      <span class="gr-budget-position-card-metrics">
        <span><small>PA:</small><strong>${escapeHtml(money(cost, currency))}</strong></span>
        <span><small>PV:</small><strong>${escapeHtml(money(sale, currency))}</strong></span>
        <span><small>MRG:</small><strong>${escapeHtml(money(margin, currency))} · ${percentFormatter.format(marginPercentage)}%</strong></span>
      </span>
    </button>`;
  }

  function renderPositionCards() {
    const lines = (state.detail && state.detail.lines) || [];
    const currency = (state.detail && state.detail.header && state.detail.header.currency) || 'EUR';
    const indexedLines = lines.map((line, index) => ({ line, index })).sort((left, right) => compareBudgetLines(left.line, right.line));
    elements.positionPickerSubtitle.textContent = `${lines.length} ${lines.length === 1 ? 'posição disponível' : 'posições disponíveis'} · selecione a posição que pretende abrir.`;
    elements.positionCards.innerHTML = indexedLines.map(({ line, index }) => positionCardMarkup(line, index, currency)).join('');
  }

  function openPositionPicker() {
    const lines = (state.detail && state.detail.lines) || [];
    if (!state.ociContext || lines.length <= 1) return;
    renderPositionCards();
    elements.positionPicker.classList.add('sz_is_open');
    elements.positionPicker.setAttribute('aria-hidden', 'false');
    const currentCard = elements.positionCards.querySelector('.is-current');
    const firstCard = elements.positionCards.querySelector('[data-position-line]');
    (currentCard || firstCard)?.focus();
  }

  function closePositionPicker() {
    elements.positionPicker.classList.remove('sz_is_open');
    elements.positionPicker.setAttribute('aria-hidden', 'true');
  }

  function closePositionSwitchConfirm() {
    elements.positionSwitchConfirm.classList.remove('sz_is_open');
    elements.positionSwitchConfirm.setAttribute('aria-hidden', 'true');
    state.pendingPositionTarget = null;
  }

  function requestPositionSwitch(selectedIndex) {
    const lines = (state.detail && state.detail.lines) || [];
    const targetLine = lines[selectedIndex];
    if (!targetLine || isCurrentOciPosition(targetLine, selectedIndex)) {
      closePositionPicker();
      return;
    }
    state.pendingPositionTarget = {
      index: selectedIndex,
      stamp: targetLine.bistamp || '',
      label: positionLabel(targetLine, selectedIndex),
      reference: targetLine.reference || ''
    };
    closePositionPicker();
    elements.positionSwitchText.textContent = `Pretende gravar a posição atual antes de mudar para a posição ${state.pendingPositionTarget.label}?`;
    elements.positionSwitchConfirm.classList.add('sz_is_open');
    elements.positionSwitchConfirm.setAttribute('aria-hidden', 'false');
    elements.positionSwitchSave.focus();
  }

  function findPendingPositionIndex(target) {
    const lines = (state.detail && state.detail.lines) || [];
    if (target.stamp) {
      const byStamp = lines.findIndex((line) => line.bistamp === target.stamp);
      if (byStamp >= 0) return byStamp;
    }
    const byPosition = lines.findIndex((line, index) => (
      positionLabel(line, index) === target.label
      && String(line.reference || '') === String(target.reference || '')
    ));
    return byPosition >= 0 ? byPosition : Math.min(target.index, lines.length - 1);
  }

  function switchOciPosition(saveCurrent) {
    const target = state.pendingPositionTarget;
    if (!target) return;
    closePositionSwitchConfirm();
    if (saveCurrent) {
      if (!saveOciLine()) return;
    } else {
      closeOciView();
    }
    const targetIndex = findPendingPositionIndex(target);
    if (targetIndex >= 0) openOci(targetIndex, false);
  }

  async function openOci(lineIndex, newLine) {
    if (!state.detail || state.loadingCount || state.ociContext) return;
    showLoading(true);
    showError('');
    try {
      await ensureTechnicalOptions();
      let line = newLine ? blankBudgetLine() : cloneData((state.detail.lines || [])[lineIndex]);
      if (!line) return;
      let rows = cloneData(line._ociRows || []);
      if (!newLine && !line._ociRows && line.bistamp && !String(line.bistamp).startsWith('draft-line-')) {
        const cached = state.ociCache.get(line.bistamp);
        const payload = cached || await getJson('/oci', { feid: elements.company.value, bistamp: line.bistamp });
        if (!cached) state.ociCache.set(line.bistamp, payload);
        line = { ...line, ...(payload.line || {}) };
        rows = cloneData(payload.rows || []);
      }
      state.ociContext = {
        lineIndex: newLine ? -1 : lineIndex,
        newLine: Boolean(newLine),
        line,
        rows
      };
      renderOciView(line, rows, Boolean(newLine));
    } catch (error) {
      showError(error.message);
    } finally {
      showLoading(false);
    }
  }

  function closeOciView() {
    closeComponentPicker();
    closePositionPicker();
    closePositionSwitchConfirm();
    elements.ociView.hidden = true;
    elements.contextbar.hidden = false;
    elements.body.hidden = false;
    root.classList.remove('is-oci');
    state.ociContext = null;
    showOciError('');
  }

  function recalculateBudgetDraftTotals() {
    const lines = (state.detail && state.detail.lines) || [];
    const included = lines.filter((line) => !line.variant && !line.option);
    const total = included.reduce((sum, line) => sum + Number(line.total || 0), 0);
    const cost = included.reduce((sum, line) => sum + Number(line.cost_total || 0), 0);
    const profit = total - cost;
    state.detail.totals = {
      total,
      cost,
      profit,
      margin_percentage: total ? profit / total * 100 : 0,
      line_count: lines.length
    };
  }

  function saveOciLine() {
    if (!state.ociContext) return false;
    const reference = elements.ociReference.value.trim();
    const designation = elements.ociDesignation.value.trim();
    const descriptionInput = elements.ociDescription.value.trim();
    const position = Math.max(1, Math.trunc(numericInput(elements.ociPosition)));
    const surface = numericInput(elements.ociSurface);
    if (!reference) {
      showOciError('Selecione um tipo de ouvrage ou indique a referência da linha.');
      elements.ociOuvrage.focus();
      return false;
    }
    if (!designation) {
      showOciError('Indique a designação da linha.');
      elements.ociDesignation.focus();
      return false;
    }
    if (surface <= 0) {
      showOciError('A surface deve ser superior a zero.');
      elements.ociSurface.focus();
      return false;
    }

    recalculateOci();
    const rows = collectOciRows();
    const purchasePrice = numericInput(elements.ociPurchasePrice);
    const salePrice = numericInput(elements.ociSalePrice);
    const costTotal = numericInput(elements.ociPurchaseTotal);
    const saleTotal = numericInput(elements.ociSaleTotal);
    const profit = numericInput(elements.ociMarginTotal);
    const prorata = Math.min(99.99, Math.max(0, numericInput(elements.ociProrata)));
    const thickness = numericInput(elements.ociThickness);
    const description = descriptionInput || `${designation} - Epaisseur ${Math.round(thickness * 100)} cm`;
    const variant = elements.ociVariant.checked;
    const option = elements.ociOption.checked;
    const excludedFromTotals = variant || option;
    const flags = currentTechnicalFlags();
    const line = {
      ...state.ociContext.line,
      item: position,
      item_label: String(position),
      order: position * 10000,
      reference,
      designation,
      description,
      quantity: surface,
      surface,
      unit: elements.ociUnit.value.trim(),
      thickness,
      volume: numericInput(elements.ociVolume),
      discount_1: excludedFromTotals ? 100 : 0,
      discount_2: prorata,
      unit_cost: excludedFromTotals ? 0 : purchasePrice,
      cost_total: excludedFromTotals ? 0 : costTotal,
      unit_price: salePrice,
      total: excludedFromTotals ? 0 : saleTotal,
      margin_per_unit: excludedFromTotals ? 0 : numericInput(elements.ociMarginUnit),
      margin_value: excludedFromTotals ? 0 : profit,
      margin_percentage: excludedFromTotals ? 0 : numericInput(elements.ociMarginPercent),
      profit: excludedFromTotals ? 0 : profit,
      has_technical_detail: true,
      simultaneous: elements.ociSimultaneous.checked,
      variant,
      option,
      blocked_price: state.ociPriceLocked,
      pump: flags.pump,
      labour: flags.labour,
      pro_rata: false,
      _technical_unit_cost: purchasePrice,
      _technical_cost_total: costTotal,
      _technical_total: saleTotal,
      _technical_profit: profit,
      _ociRows: rows
    };
    const previousItem = String(state.ociContext.line.item_label || state.ociContext.line.item || position);
    state.detail.lines = (state.detail.lines || []).filter((candidate, index) => {
      if (!isPlusValue(candidate.reference)) return true;
      if (!state.ociContext.newLine && index === state.ociContext.lineIndex) return true;
      return !String(candidate.item_label || '').startsWith(`${previousItem}.`);
    });
    if (state.ociContext.newLine) {
      state.detail.lines.push(line);
    } else {
      const target = state.detail.lines.findIndex((candidate) => candidate.bistamp === state.ociContext.line.bistamp);
      if (target >= 0) state.detail.lines[target] = line;
      else state.detail.lines.push(line);
    }
    rows.filter((row) => row.is_plus_value).forEach((row, index) => {
      state.detail.lines.push({
        bistamp: row.stamp || `draft-plus-${Date.now()}-${index}`,
        budget_stamp: line.budget_stamp || '',
        order: Number(line.order || 0) + (index + 1) * 100,
        item: position,
        item_label: `${position}.${index + 1}`,
        reference: row.reference,
        designation: row.designation,
        description: row.designation,
        quantity: 0,
        surface: 0,
        unit: row.unit,
        thickness: 0,
        volume: 0,
        unit_cost: 0,
        cost_total: 0,
        unit_price: Number(row.purchase_price || 0),
        total: 0,
        margin_per_unit: 0,
        margin_value: 0,
        margin_percentage: 0,
        profit: 0,
        has_technical_detail: false,
        simultaneous: false,
        variant: false,
        option: false,
        blocked_price: true,
        pump: false,
        labour: false,
        pro_rata: false,
        _parent_bistamp: line.bistamp
      });
    });
    state.detail.lines.forEach((candidate) => {
      candidate.discount_2 = prorata;
      if (candidate.variant || candidate.option || isPlusValue(candidate.reference)) return;
      candidate.total = Number(candidate.unit_price || 0) * Number(candidate.quantity || 0) * (1 - prorata / 100);
      candidate.profit = Number(candidate.total || 0) - Number(candidate.cost_total || 0);
      candidate.margin_value = candidate.profit;
      candidate.margin_percentage = candidate.total ? candidate.profit / candidate.total * 100 : 0;
    });
    state.detail.lines.sort(compareBudgetLines);
    state.ociCache.set(line.bistamp, { line: cloneData(line), rows: cloneData(rows) });
    if (!isEditing()) {
      state.mode = 'edit';
      state.returnStamp = elements.document.value;
    }
    recalculateBudgetDraftTotals();
    closeOciView();
    renderDetail(state.detail);
    updateInteractionState();
    return true;
  }

  function updateInteractionState() {
    const editing = isEditing();
    const busy = state.loadingCount > 0;
    const navigationLocked = editing || busy;
    root.classList.toggle('is-editing', editing);

    elements.company.disabled = navigationLocked || !state.companies.length;
    elements.series.disabled = navigationLocked || !state.series.length;
    elements.year.disabled = navigationLocked;
    elements.search.disabled = navigationLocked;
    elements.refresh.disabled = navigationLocked || !elements.series.value;
    elements.document.disabled = navigationLocked || !state.budgets.length;
    elements.printBudget.disabled = navigationLocked || !state.detail || !selectedBudgetStamp() || !elements.company.value;
    elements.newBudget.hidden = editing;
    elements.newBudget.disabled = busy || !elements.company.value || !elements.series.value;
    elements.cancelEdit.hidden = !editing;
    elements.cancelEdit.disabled = busy;
    elements.addLine.disabled = busy || !state.detail;

    [elements.clientSearch, elements.workInput, elements.localityInput, elements.dateInput, elements.attentionInput]
      .forEach((input) => {
        input.readOnly = !editing;
        input.setAttribute('aria-readonly', editing ? 'false' : 'true');
      });
    elements.salesperson.disabled = !editing || busy;
    updateNavigation();
  }

  function todayForInput() {
    const today = new Date();
    const year = today.getFullYear();
    const month = String(today.getMonth() + 1).padStart(2, '0');
    const day = String(today.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
  }

  function startNewBudget() {
    if (isEditing() || state.loadingCount || !elements.company.value || !elements.series.value) return;
    window.clearTimeout(state.searchTimer);
    state.requestVersion += 1;
    state.returnStamp = elements.document.value;
    state.mode = 'new';

    const selectedSeries = state.series.find((row) => String(row.ndos) === String(elements.series.value));
    const seriesName = (selectedSeries && selectedSeries.name) || 'Devis';
    const draftOption = document.createElement('option');
    draftOption.value = newDocumentValue;
    draftOption.textContent = `Novo ${seriesName} · por guardar`;
    draftOption.dataset.draft = 'true';
    elements.document.appendChild(draftOption);
    elements.document.value = newDocumentValue;
    elements.resultCount.textContent = 'Novo orçamento';

    const draft = {
      header: {
        _draft: true,
        series: seriesName,
        date: todayForInput(),
        currency: (state.detail && state.detail.header && state.detail.header.currency) || 'EUR'
      },
      totals: {
        total: 0,
        cost: 0,
        margin_percentage: 0,
        profit: 0
      },
      lines: []
    };
    state.detail = draft;
    renderDetail(draft);
    updateInteractionState();
    elements.clientSearch.focus();
  }

  function cancelEdit() {
    if (!isEditing()) return;
    const returnStamp = state.returnStamp;
    state.mode = 'view';
    state.returnStamp = '';
    state.ociCache.clear();
    closeClientLookup();
    elements.document.querySelectorAll('[data-draft="true"]').forEach((option) => option.remove());
    elements.resultCount.textContent = `${state.budgets.length} ${state.budgets.length === 1 ? 'orçamento' : 'orçamentos'}`;
    if (returnStamp && state.budgets.some((row) => row.bostamp === returnStamp)) {
      elements.document.value = returnStamp;
      updateInteractionState();
      loadDetail(returnStamp);
      return;
    }
    updateInteractionState();
    loadBudgets();
  }

  function updateNavigation() {
    const index = state.budgets.findIndex((row) => row.bostamp === elements.document.value);
    const locked = isEditing() || state.loadingCount > 0;
    elements.previous.disabled = locked || index <= 0;
    elements.next.disabled = locked || index < 0 || index >= state.budgets.length - 1;
  }

  function moveSelection(delta) {
    if (isEditing() || state.loadingCount) return;
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
  elements.printBudget.addEventListener('click', printBudget);
  elements.newBudget.addEventListener('click', startNewBudget);
  elements.cancelEdit.addEventListener('click', cancelEdit);
  elements.clientSearch.addEventListener('input', () => {
    if (!isEditing()) return;
    setInputValue(elements.clientNumber, '');
    setInputValue(elements.clientEstablishment, '');
    elements.clientMeta.textContent = elements.clientSearch.value.trim() ? 'Selecione um cliente da lista' : 'Cliente não selecionado';
    scheduleClientSearch();
  });
  elements.clientSearch.addEventListener('focus', () => {
    if (!isEditing()) return;
    if (elements.clientSearch.value.trim()) scheduleClientSearch();
  });
  elements.clientSearch.addEventListener('keydown', (event) => {
    if (!isEditing()) return;
    if (elements.clientResults.hidden) return;
    if (event.key === 'ArrowDown') {
      event.preventDefault();
      setClientActive(state.clientActiveIndex + 1);
    } else if (event.key === 'ArrowUp') {
      event.preventDefault();
      setClientActive(state.clientActiveIndex - 1);
    } else if (event.key === 'Enter' && state.clientRows[state.clientActiveIndex]) {
      event.preventDefault();
      selectClient(state.clientRows[state.clientActiveIndex]);
    } else if (event.key === 'Escape') {
      closeClientLookup();
    }
  });
  elements.clientSearch.addEventListener('blur', () => window.setTimeout(closeClientLookup, 150));
  elements.lines.addEventListener('click', (event) => {
    const button = event.target.closest('[data-technical-line]');
    if (!button || !state.detail) return;
    openOci(Number(button.dataset.technicalLine), false);
  });
  elements.addLine.addEventListener('click', () => openOci(-1, true));
  elements.ociCancel.addEventListener('click', closeOciView);
  elements.ociSave.addEventListener('click', saveOciLine);
  elements.ociPositions.addEventListener('click', openPositionPicker);
  elements.ociAddRow.addEventListener('click', () => openComponentPicker());
  elements.ociFamilyList.addEventListener('click', (event) => {
    const button = event.target.closest('[data-oci-family-add]');
    if (!button) return;
    openComponentPicker(button.dataset.ociFamilyAdd || '');
  });
  elements.componentArticles.addEventListener('click', (event) => {
    const row = event.target.closest('[data-component-stamp]');
    if (!row) return;
    selectComponent(row.dataset.componentStamp);
  });
  elements.componentArticles.addEventListener('dblclick', (event) => {
    const row = event.target.closest('[data-component-stamp]');
    if (!row) return;
    selectComponent(row.dataset.componentStamp);
    confirmComponent();
  });
  elements.componentArticles.addEventListener('keydown', (event) => {
    const row = event.target.closest('[data-component-stamp]');
    if (!row || event.key !== 'Enter') return;
    event.preventDefault();
    selectComponent(row.dataset.componentStamp);
    confirmComponent();
  });
  elements.componentConfirm.addEventListener('click', confirmComponent);
  root.querySelectorAll('[data-component-close]').forEach((button) => {
    button.addEventListener('click', closeComponentPicker);
  });
  elements.componentPicker.addEventListener('click', (event) => {
    if (event.target === elements.componentPicker) closeComponentPicker();
  });
  elements.positionCards.addEventListener('click', (event) => {
    const card = event.target.closest('[data-position-line]');
    if (!card) return;
    requestPositionSwitch(Number(card.dataset.positionLine));
  });
  root.querySelectorAll('[data-position-picker-close]').forEach((button) => {
    button.addEventListener('click', closePositionPicker);
  });
  elements.positionPicker.addEventListener('click', (event) => {
    if (event.target === elements.positionPicker) closePositionPicker();
  });
  root.querySelectorAll('[data-position-switch-cancel]').forEach((button) => {
    button.addEventListener('click', closePositionSwitchConfirm);
  });
  elements.positionSwitchDiscard.addEventListener('click', () => switchOciPosition(false));
  elements.positionSwitchSave.addEventListener('click', () => switchOciPosition(true));
  elements.ociRows.addEventListener('click', (event) => {
    const button = event.target.closest('[data-oci-delete]');
    if (!button) return;
    button.closest('tr').remove();
    const count = elements.ociRows.querySelectorAll('tr').length;
    text('budgetOciRowCount', `${count} ${count === 1 ? 'linha' : 'linhas'} · OCI`);
    recalculateOci();
    renderOciFamilySidebar();
  });
  elements.ociRows.addEventListener('input', (event) => {
    const row = event.target.closest('tr');
    if (!row) return;
    if (event.target.matches('[data-oci-field="weight"]')) {
      const source = row.dataset.ociSourceDesignation || '';
      if (source.includes('...')) {
        const weight = Math.round(numericInput(event.target));
        setInputValue(row.querySelector('[data-oci-field="designation"]'), source.replaceAll('...', String(weight)));
      }
    }
    recalculateOci();
  });
  elements.ociRows.addEventListener('change', (event) => {
    const row = event.target.closest('tr');
    if (row) updateOciRowFormulaState(row);
    recalculateOci();
  });
  elements.ociSurface.addEventListener('input', syncOciDimensions);
  elements.ociThickness.addEventListener('input', syncOciDimensions);
  elements.ociSurface.addEventListener('change', syncOciDimensions);
  elements.ociThickness.addEventListener('change', syncOciDimensions);
  elements.ociSalePrice.addEventListener('input', () => {
    state.ociPriceLocked = true;
    recalculateOci();
  });
  elements.ociMarginPercent.addEventListener('input', () => {
    state.ociPriceLocked = false;
    state.ociTargetMargin = numericInput(elements.ociMarginPercent);
    recalculateOci();
  });
  elements.ociProrata.addEventListener('input', recalculateOci);
  elements.ociSimultaneous.addEventListener('change', recalculateOci);
  elements.ociOuvrage.addEventListener('change', () => {
    const ouvrages = (state.technicalOptions && state.technicalOptions.ouvrages) || [];
    const ouvrage = ouvrages.find((row) => row.reference === elements.ociOuvrage.value);
    if (!ouvrage) {
      renderOciFamilySidebar();
      return;
    }
    setInputValue(elements.ociReference, ouvrage.reference);
    setInputValue(elements.ociDesignation, ouvrage.designation);
    setInputValue(elements.ociDescription, ouvrage.designation);
    setInputValue(elements.ociUnit, ouvrage.unit || 'm²');
    if (!numericInput(elements.ociSalePrice) && ouvrage.sale_price) {
      setNumericInput(elements.ociSalePrice, ouvrage.sale_price, 4);
    }
    recalculateOci();
    renderOciFamilySidebar();
  });
  document.addEventListener('keydown', (event) => {
    if (event.key !== 'Escape') return;
    if (elements.positionSwitchConfirm.classList.contains('sz_is_open')) {
      closePositionSwitchConfirm();
    } else if (elements.positionPicker.classList.contains('sz_is_open')) {
      closePositionPicker();
    } else if (elements.componentPicker.classList.contains('sz_is_open')) {
      closeComponentPicker();
    }
  });
  window.addEventListener('beforeunload', (event) => {
    if (!isEditing() && !state.ociContext) return;
    event.preventDefault();
    event.returnValue = '';
  });

  elements.year.value = String(new Date().getFullYear());
  updateInteractionState();
  loadCompanies();
})();
