(function () {
  'use strict';

  const root = document.getElementById('grBudgetApp');
  if (!root) return;

  const apiBase = '/api/gr_orcamentos';
  const tr = (key, vars) => (typeof window.t === 'function' ? window.t(key, vars) : key);
  const languageTag = window.SZ_LANGUAGE_TAG || 'pt-PT';
  const initialBudget = {
    feid: String(root.dataset.initialFeid || '').trim(),
    bostamp: String(root.dataset.initialBostamp || '').trim(),
    applied: false
  };

  function plural(oneKey, otherKey, count) {
    return tr(Number(count) === 1 ? oneKey : otherKey, { count });
  }
  const elements = {
    company: document.getElementById('budgetCompany'),
    series: document.getElementById('budgetSeries'),
    year: document.getElementById('budgetYear'),
    search: document.getElementById('budgetSearch'),
    refresh: document.getElementById('budgetRefresh'),
    document: document.getElementById('budgetDocument'),
    previous: document.getElementById('budgetPrevious'),
    next: document.getElementById('budgetNext'),
    actionsMenu: document.getElementById('budgetActionsMenu'),
    actionsToggle: document.getElementById('budgetActionsToggle'),
    printBudget: document.getElementById('budgetPrint'),
    approvalBudget: document.getElementById('budgetApproval'),
    approvalBudgetLabel: document.getElementById('budgetApprovalLabel'),
    convertExecution: document.getElementById('budgetConvertExecution'),
    assignWork: document.getElementById('budgetAssignWork'),
    duplicateBudget: document.getElementById('budgetDuplicate'),
    finalPriceBudget: document.getElementById('budgetFinalPrice'),
    discountBudget: document.getElementById('budgetDiscount'),
    applyVatBudget: document.getElementById('budgetApplyVat'),
    newBudget: document.getElementById('budgetNew'),
    editBudget: document.getElementById('budgetEdit'),
    cancelEdit: document.getElementById('budgetCancelEdit'),
    saveBudget: document.getElementById('budgetSave'),
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
    associatedWork: document.getElementById('budgetAssociatedWork'),
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
    ociDuplicate: document.getElementById('budgetOciDuplicate'),
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
    positionSwitchSave: document.getElementById('budgetPositionSwitchSave'),
    positionDuplicateConfirm: document.getElementById('budgetPositionDuplicateConfirm'),
    positionDuplicateTitle: document.getElementById('budgetPositionDuplicateTitle'),
    positionDuplicateText: document.getElementById('budgetPositionDuplicateText'),
    positionDuplicateActionText: document.getElementById('budgetPositionDuplicateActionText'),
    positionDuplicateSave: document.getElementById('budgetPositionDuplicateSave'),
    commercialAdjustment: document.getElementById('budgetCommercialAdjustment'),
    commercialAdjustmentTitle: document.getElementById('budgetCommercialAdjustmentTitle'),
    commercialAdjustmentText: document.getElementById('budgetCommercialAdjustmentText'),
    commercialAdjustmentLabel: document.getElementById('budgetCommercialAdjustmentLabel'),
    commercialAdjustmentValue: document.getElementById('budgetCommercialAdjustmentValue'),
    commercialAdjustmentError: document.getElementById('budgetCommercialAdjustmentError'),
    commercialAdjustmentApply: document.getElementById('budgetCommercialAdjustmentApply'),
    approvalConfirm: document.getElementById('budgetApprovalConfirm'),
    approvalConfirmTitle: document.getElementById('budgetApprovalConfirmTitle'),
    approvalConfirmText: document.getElementById('budgetApprovalConfirmText'),
    approvalCredit: document.getElementById('budgetApprovalCredit'),
    approvalError: document.getElementById('budgetApprovalError'),
    approvalApply: document.getElementById('budgetApprovalApply'),
    approvalApplyLabel: document.getElementById('budgetApprovalApplyLabel'),
    convertExecutionConfirm: document.getElementById('budgetConvertExecutionConfirm'),
    convertExecutionApply: document.getElementById('budgetConvertExecutionApply'),
    convertExecutionError: document.getElementById('budgetConvertExecutionError'),
    convertWorkField: document.getElementById('budgetConvertWorkField'),
    convertWorkSearch: document.getElementById('budgetConvertWorkSearch'),
    convertWorkResults: document.getElementById('budgetConvertWorkResults'),
    convertWorkMeta: document.getElementById('budgetConvertWorkMeta'),
    assignWorkConfirm: document.getElementById('budgetAssignWorkConfirm'),
    assignWorkApply: document.getElementById('budgetAssignWorkApply'),
    assignWorkError: document.getElementById('budgetAssignWorkError'),
    assignWorkSearch: document.getElementById('budgetAssignWorkSearch'),
    assignWorkResults: document.getElementById('budgetAssignWorkResults'),
    assignWorkMeta: document.getElementById('budgetAssignWorkMeta'),
    lineDeleteConfirm: document.getElementById('budgetLineDeleteConfirm'),
    lineDeleteText: document.getElementById('budgetLineDeleteText'),
    lineDeleteApply: document.getElementById('budgetLineDeleteApply'),
    vatApply: document.getElementById('budgetVatApply'),
    vatApplySelect: document.getElementById('budgetVatApplySelect'),
    vatApplyError: document.getElementById('budgetVatApplyError'),
    vatApplyConfirm: document.getElementById('budgetVatApplyConfirm')
  };

  const state = {
    companies: [],
    series: [],
    taxRates: [],
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
    pendingPositionDuplicate: null,
    commercialAdjustmentMode: '',
    approvalTarget: null,
    convertWorkRows: [],
    convertWorkStamp: '',
    convertWorkSearchTimer: 0,
    convertWorkRequestVersion: 0,
    assignWorkRows: [],
    assignWorkStamp: '',
    assignWorkSearchTimer: 0,
    assignWorkRequestVersion: 0,
    pendingLineDelete: null,
    draftSequence: 0,
    ociPriceLocked: true,
    ociTargetMargin: 0,
    mode: 'view',
    returnStamp: '',
    loadingCount: 0,
    searchTimer: 0,
    requestVersion: 0
  };

  const numberFormatter = new Intl.NumberFormat(languageTag, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  const lineAmountFormatter = new Intl.NumberFormat(languageTag, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  const quantityFormatter = new Intl.NumberFormat(languageTag, { minimumFractionDigits: 0, maximumFractionDigits: 4 });
  const percentFormatter = new Intl.NumberFormat(languageTag, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  const newDocumentValue = '__new_budget__';

  function isEditing() {
    return state.mode !== 'view';
  }

  function budgetCanBeEdited() {
    const header = state.detail && state.detail.header;
    return Boolean(header && !header.closed && !header.awarded && !header.cancelled);
  }

  function selectedBudgetStamp() {
    const stamp = String(elements.document.value || '').trim();
    return stamp && stamp !== newDocumentValue ? stamp : '';
  }

  function budgetPdfUrl() {
    const selectedFeid = String(elements.company.value || '').trim();
    const detailFeid = String(state.detail?.company?.feid || '').trim();
    const bostamp = selectedBudgetStamp();
    if (!selectedFeid || !detailFeid || selectedFeid !== detailFeid || !bostamp) return '';
    const url = new URL(`${apiBase}/orcamento/${encodeURIComponent(bostamp)}/pdf`, window.location.origin);
    url.searchParams.set('feid', detailFeid);
    url.searchParams.set('style', 'modern');
    return url.toString();
  }

  function printBudget() {
    if (isEditing() || state.loadingCount || !state.detail) return;
    const url = budgetPdfUrl();
    if (!url) {
      showError(tr('gr_budgets.error.pdf_missing_selection'));
      return;
    }
    showError('');
    const printWindow = window.open(url, '_blank');
    if (!printWindow) {
      showError(tr('gr_budgets.error.pdf_popup_blocked'));
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
      throw new Error(payload.error || tr('gr_budgets.error.load_data', { status: response.status }));
    }
    return payload;
  }

  async function postJson(path, body) {
    const response = await fetch(apiBase + path, {
      method: 'POST',
      headers: { Accept: 'application/json', 'Content-Type': 'application/json' },
      body: JSON.stringify(body || {})
    });
    let payload = {};
    try { payload = await response.json(); } catch (_) { payload = {}; }
    if (!response.ok || payload.ok === false) {
      const error = new Error(payload.error || tr('gr_budgets.error.save_budget', { status: response.status }));
      error.payload = payload;
      throw error;
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
      const selected = state.companies.find((row) => String(row.feid) === initialBudget.feid)
        || state.companies.find((row) => String(row.feid) === stored)
        || state.companies.find((row) => String(row.phc_db || '').toUpperCase() === preferredDatabase)
        || state.companies[0];
      setOptions(elements.company, state.companies, 'feid', (row) => row.name || row.phc_db, selected && selected.feid);
      if (!selected) {
        renderNoResults(tr('gr_budgets.error.no_companies'));
        return;
      }
      await loadSeries();
    } catch (error) {
      state.ociContext = null;
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
      state.taxRates = seriesPayload.tax_rates || [];
      state.salespeople = salespeoplePayload.rows || [];
      renderSalespeople();
      setOptions(elements.series, state.series, 'ndos', (row) => `${row.name} · ${row.ndos}`, seriesPayload.default_ndos);
      if (!state.series.length) {
        renderNoResults(tr('gr_budgets.error.series_unavailable'));
        return;
      }
      if (initialBudget.bostamp && !initialBudget.applied) {
        const direct = await getJson('/orcamento', { feid, bostamp: initialBudget.bostamp });
        const header = direct.header || {};
        if (header.ndos && Array.from(elements.series.options).some((option) => option.value === String(header.ndos))) {
          elements.series.value = String(header.ndos);
        }
        if (header.year) elements.year.value = String(header.year);
        initialBudget.applied = true;
        await loadBudgets(initialBudget.bostamp);
      } else {
        await loadBudgets();
      }
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
        (row) => `${row.series} ${row.number} · ${row.client_name || tr('gr_budgets.label.no_client')}${row.process ? ` · ${row.process}` : ''}${row.work_name ? ` — ${row.work_name}` : ''}`,
        selected && selected.bostamp
      );
      elements.resultCount.textContent = plural('gr_budgets.count.budget_one', 'gr_budgets.count.budget_other', state.budgets.length);
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
    if (strong) strong.textContent = message || tr('gr_budgets.empty.title');
    elements.document.replaceChildren();
    elements.resultCount.textContent = tr('gr_budgets.count.budget_other', { count: 0 });
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
    emptyOption.textContent = tr('gr_budgets.label.no_salesperson');
    elements.salesperson.appendChild(emptyOption);
    state.salespeople.forEach((row) => {
      const option = document.createElement('option');
      option.value = String(row.number || '');
      option.textContent = `${row.name || row.number}${row.inactive ? ` · ${tr('gr_budgets.client.inactive')}` : ''}`;
      elements.salesperson.appendChild(option);
    });
    const wanted = String(selectedNumber || '');
    if (wanted && !Array.from(elements.salesperson.options).some((option) => option.value === wanted)) {
      const option = document.createElement('option');
      option.value = wanted;
      option.textContent = selectedName || tr('gr_budgets.label.salesperson_fallback', { number: wanted });
      elements.salesperson.appendChild(option);
    }
    elements.salesperson.value = wanted;
  }

  function syncEditableHeaderToState() {
    if (!state.detail) return;
    const header = state.detail.header || {};
    const salespersonNumber = Number(elements.salesperson.value || 0);
    const salesperson = state.salespeople.find((row) => Number(row.number || 0) === salespersonNumber);
    state.detail.header = {
      ...header,
      client_name: elements.clientSearch.value.trim(),
      client_number: Number(elements.clientNumber.value || 0),
      establishment: Number(elements.clientEstablishment.value || 0),
      work_name: elements.workInput.value.trim(),
      locality: elements.localityInput.value.trim(),
      date: elements.dateInput.value,
      salesperson_number: salespersonNumber,
      salesperson: salesperson ? salesperson.name : '',
      attention: elements.attentionInput.value.trim()
    };
  }

  function money(value, currency) {
    const code = currency || 'EUR';
    try {
      return new Intl.NumberFormat(languageTag, { style: 'currency', currency: code }).format(Number(value || 0));
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
        ? { kind: 0, number: Number.parseInt(match[1], 10), suffix: match[2].trim().toLocaleLowerCase(languageTag) }
        : { kind: 1, number: 0, suffix: token.toLocaleLowerCase(languageTag) };
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
      const suffixOrder = leftSegment.suffix.localeCompare(rightSegment.suffix, languageTag, { numeric: true });
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

    text('budgetDocumentEyebrow', tr('gr_budgets.document.dossier_series', { series: header.series || tr('gr_budgets.label.budget') }));
    setInputValue(elements.clientSearch, header.client_name);
    setInputValue(elements.clientNumber, header.client_number);
    setInputValue(elements.clientEstablishment, header.establishment);
    elements.clientMeta.textContent = header.client_number
      ? tr(
        header.establishment ? 'gr_budgets.client.label_number_establishment' : 'gr_budgets.client.label_number',
        { number: header.client_number, establishment: header.establishment }
      )
      : tr('gr_budgets.client.meta_unselected');
    setInputValue(elements.workInput, header.work_name);
    renderAssociatedWork(payload.work, header.process);
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
    text('budgetLineCount', `${plural('gr_budgets.count.line_one', 'gr_budgets.count.line_other', lines.length)} · BI + BI2`);

    renderStatuses(header);
    updateApprovalAction(header);
    renderLines(lines, header.currency, totals);
  }

  function renderAssociatedWork(work, process) {
    if (!elements.associatedWork) return;
    const associated = work && typeof work === 'object' ? work : null;
    const label = associated
      ? [associated.process, associated.description].filter(Boolean).join(' · ')
      : (process ? tr('gr_budgets.assign_work.process_without_opc', { process }) : tr('gr_budgets.assign_work.unassigned'));
    elements.associatedWork.replaceChildren();
    const icon = document.createElement('i');
    icon.className = `fa-solid ${associated ? 'fa-link' : 'fa-link-slash'}`;
    icon.setAttribute('aria-hidden', 'true');
    const textValue = document.createElement('strong');
    textValue.textContent = label;
    elements.associatedWork.append(icon, textValue);
    elements.associatedWork.classList.toggle('is-unlinked', !associated);
    elements.associatedWork.title = label;
  }

  function renderStatuses(header) {
    const statuses = [];
    if (header._draft) statuses.push(['warning', 'fa-pen', tr('gr_budgets.status.new_editing')]);
    if (!header._draft && isEditing()) statuses.push(['warning', 'fa-pen', tr('gr_budgets.status.editing')]);
    if (!header._draft && header.cancelled) statuses.push(['danger', 'fa-ban', tr('gr_budgets.status.cancelled')]);
    if (!header._draft && header.closed) statuses.push(['danger', 'fa-lock', tr('gr_budgets.status.closed')]);
    if (!header._draft && header.approved) statuses.push(['success', 'fa-circle-check', tr('gr_budgets.status.approved')]);
    if (!header._draft && header.awarded) statuses.push(['info', 'fa-trophy', tr('gr_budgets.status.awarded')]);
    if (!statuses.length) statuses.push(['warning', 'fa-clock', tr('gr_budgets.status.preparation')]);
    document.getElementById('budgetStatus').innerHTML = statuses.map(([kind, icon, label]) =>
      `<span class="sz_badge sz_badge_${kind}"><i class="fa-solid ${icon}"></i>${escapeHtml(label)}</span>`
    ).join('');
  }

  function budgetApprovalAvailable() {
    const header = state.detail && state.detail.header;
    if (!header || !budgetCanBeEdited()) return false;
    const series = String(header.series || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').trim().toLowerCase();
    return series === 'devis';
  }

  function budgetConversionAvailable() {
    const header = state.detail && state.detail.header;
    if (!header || header.closed || header.cancelled) return false;
    const series = String(header.series || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').trim().toLowerCase();
    return series === 'devis';
  }

  function updateApprovalAction(header) {
    const approved = Boolean(header && header.approved);
    const key = approved ? 'gr_budgets.action.unapprove' : 'gr_budgets.action.approve';
    elements.approvalBudgetLabel.textContent = tr(key);
    elements.approvalBudget.querySelector('i').className = approved
      ? 'fa-solid fa-circle-xmark'
      : 'fa-solid fa-circle-check';
  }

  function closeApprovalConfirm() {
    elements.approvalConfirm.classList.remove('sz_is_open');
    elements.approvalConfirm.setAttribute('aria-hidden', 'true');
    elements.approvalCredit.hidden = true;
    elements.approvalCredit.replaceChildren();
    elements.approvalError.hidden = true;
    elements.approvalError.textContent = '';
    elements.approvalApply.disabled = false;
    state.approvalTarget = null;
  }

  function openApprovalConfirm() {
    if (isEditing() || state.loadingCount || !selectedBudgetStamp() || !budgetApprovalAvailable()) return;
    const approved = Boolean(state.detail && state.detail.header && state.detail.header.approved);
    state.approvalTarget = !approved;
    const prefix = state.approvalTarget ? 'approve' : 'unapprove';
    elements.approvalConfirmTitle.textContent = tr(`gr_budgets.approval.${prefix}_title`);
    elements.approvalConfirmText.textContent = tr(`gr_budgets.approval.${prefix}_text`);
    elements.approvalApplyLabel.textContent = tr(`gr_budgets.action.${prefix}`);
    elements.approvalApply.classList.toggle('sz_button_danger', !state.approvalTarget);
    elements.approvalCredit.hidden = true;
    elements.approvalCredit.replaceChildren();
    elements.approvalError.hidden = true;
    elements.approvalError.textContent = '';
    elements.approvalConfirm.classList.add('sz_is_open');
    elements.approvalConfirm.setAttribute('aria-hidden', 'false');
    elements.approvalApply.focus();
  }

  function showApprovalCredit(credit, currency) {
    if (!credit) return;
    const rows = [
      ['gr_budgets.approval.total_credit', credit.total_credit],
      ['gr_budgets.approval.open_total', credit.open_total],
      ['gr_budgets.approval.budget_total', credit.budget_total],
      ['gr_budgets.approval.available', credit.available]
    ];
    elements.approvalCredit.innerHTML = rows.map(([key, value]) =>
      `<div><small>${escapeHtml(tr(key))}</small><strong>${escapeHtml(money(value, currency))}</strong></div>`
    ).join('');
    elements.approvalCredit.hidden = false;
  }

  async function applyBudgetApproval() {
    if (state.approvalTarget == null || !state.detail || state.loadingCount) return;
    const bostamp = selectedBudgetStamp();
    if (!bostamp) return;
    const target = state.approvalTarget;
    const currency = (state.detail.header && state.detail.header.currency) || 'EUR';
    elements.approvalApply.disabled = true;
    elements.approvalError.hidden = true;
    elements.approvalError.textContent = '';
    showLoading(true);
    try {
      await postJson(`/orcamento/${encodeURIComponent(bostamp)}/aprovacao`, {
        feid: elements.company.value,
        approved: target
      });
      closeApprovalConfirm();
      await loadBudgets(bostamp);
    } catch (error) {
      elements.approvalError.textContent = error.message;
      elements.approvalError.hidden = false;
      showApprovalCredit(error.payload && error.payload.credit, currency);
      elements.approvalApply.disabled = false;
    } finally {
      showLoading(false);
    }
  }

  function conversionTarget() {
    return root.querySelector('input[name="budgetConvertTarget"]:checked')?.value || 'new';
  }

  function closeConvertWorkLookup() {
    window.clearTimeout(state.convertWorkSearchTimer);
    state.convertWorkRequestVersion += 1;
    state.convertWorkRows = [];
    elements.convertWorkResults.hidden = true;
    elements.convertWorkResults.replaceChildren();
  }

  function renderConvertWorkRows(rows) {
    state.convertWorkRows = Array.isArray(rows) ? rows : [];
    elements.convertWorkResults.replaceChildren();
    if (!state.convertWorkRows.length) {
      const empty = document.createElement('div');
      empty.className = 'sz_table_lookup_empty';
      empty.textContent = tr('gr_budgets.convert.work_empty');
      elements.convertWorkResults.append(empty);
      elements.convertWorkResults.hidden = false;
      return;
    }
    state.convertWorkRows.forEach((row) => {
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'sz_table_lookup_item';
      const title = document.createElement('span');
      title.className = 'sz_table_lookup_item_label';
      title.textContent = [row.process, row.description].filter(Boolean).join(' · ');
      const meta = document.createElement('span');
      meta.className = 'sz_table_lookup_item_value';
      meta.textContent = row.client_name || '';
      button.append(title, meta);
      button.addEventListener('mousedown', (event) => {
        event.preventDefault();
        state.convertWorkStamp = String(row.opcstamp || '');
        elements.convertWorkSearch.value = [row.process, row.description].filter(Boolean).join(' · ');
        elements.convertWorkMeta.textContent = tr('gr_budgets.convert.work_selected', { process: row.process || '' });
        closeConvertWorkLookup();
      });
      elements.convertWorkResults.append(button);
    });
    elements.convertWorkResults.hidden = false;
  }

  function scheduleConvertWorkSearch() {
    window.clearTimeout(state.convertWorkSearchTimer);
    state.convertWorkStamp = '';
    elements.convertWorkMeta.textContent = tr('gr_budgets.convert.work_unselected');
    const query = elements.convertWorkSearch.value.trim();
    if (query.length < 2) {
      closeConvertWorkLookup();
      return;
    }
    state.convertWorkSearchTimer = window.setTimeout(async () => {
      const version = ++state.convertWorkRequestVersion;
      try {
        const payload = await getJson('/obras', { feid: elements.company.value, q: query });
        if (version !== state.convertWorkRequestVersion) return;
        renderConvertWorkRows(payload.rows || []);
      } catch (error) {
        if (version !== state.convertWorkRequestVersion) return;
        elements.convertWorkMeta.textContent = error.message;
      }
    }, 250);
  }

  function updateConvertTarget() {
    const existing = conversionTarget() === 'existing';
    elements.convertWorkField.hidden = !existing;
    if (!existing) {
      state.convertWorkStamp = '';
      elements.convertWorkSearch.value = '';
      elements.convertWorkMeta.textContent = tr('gr_budgets.convert.work_unselected');
      closeConvertWorkLookup();
    } else {
      elements.convertWorkSearch.focus();
    }
  }

  function closeBudgetConversion() {
    elements.convertExecutionConfirm.classList.remove('sz_is_open');
    elements.convertExecutionConfirm.setAttribute('aria-hidden', 'true');
    elements.convertExecutionError.hidden = true;
    elements.convertExecutionError.textContent = '';
    elements.convertExecutionApply.disabled = false;
    root.querySelector('input[name="budgetConvertTarget"][value="new"]').checked = true;
    updateConvertTarget();
  }

  function closeAssignWorkLookup() {
    window.clearTimeout(state.assignWorkSearchTimer);
    state.assignWorkRequestVersion += 1;
    state.assignWorkRows = [];
    elements.assignWorkResults.hidden = true;
    elements.assignWorkResults.replaceChildren();
  }

  function renderAssignWorkRows(rows) {
    state.assignWorkRows = Array.isArray(rows) ? rows : [];
    elements.assignWorkResults.replaceChildren();
    if (!state.assignWorkRows.length) {
      const empty = document.createElement('div');
      empty.className = 'sz_table_lookup_empty';
      empty.textContent = tr('gr_budgets.convert.work_empty');
      elements.assignWorkResults.append(empty);
      elements.assignWorkResults.hidden = false;
      return;
    }
    state.assignWorkRows.forEach((row) => {
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'sz_table_lookup_item';
      const title = document.createElement('span');
      title.className = 'sz_table_lookup_item_label';
      title.textContent = [row.process, row.description].filter(Boolean).join(' · ');
      const meta = document.createElement('span');
      meta.className = 'sz_table_lookup_item_value';
      meta.textContent = row.client_name || '';
      button.append(title, meta);
      button.addEventListener('mousedown', (event) => {
        event.preventDefault();
        state.assignWorkStamp = String(row.opcstamp || '');
        elements.assignWorkSearch.value = [row.process, row.description].filter(Boolean).join(' · ');
        elements.assignWorkMeta.textContent = tr('gr_budgets.convert.work_selected', { process: row.process || '' });
        closeAssignWorkLookup();
      });
      elements.assignWorkResults.append(button);
    });
    elements.assignWorkResults.hidden = false;
  }

  function scheduleAssignWorkSearch() {
    window.clearTimeout(state.assignWorkSearchTimer);
    state.assignWorkStamp = '';
    elements.assignWorkMeta.textContent = tr('gr_budgets.convert.work_unselected');
    const query = elements.assignWorkSearch.value.trim();
    if (query.length < 2) {
      closeAssignWorkLookup();
      return;
    }
    state.assignWorkSearchTimer = window.setTimeout(async () => {
      const version = ++state.assignWorkRequestVersion;
      try {
        const payload = await getJson('/obras', { feid: elements.company.value, q: query });
        if (version !== state.assignWorkRequestVersion) return;
        renderAssignWorkRows(payload.rows || []);
      } catch (error) {
        if (version !== state.assignWorkRequestVersion) return;
        elements.assignWorkMeta.textContent = error.message;
      }
    }, 250);
  }

  function closeAssignWork() {
    elements.assignWorkConfirm.classList.remove('sz_is_open');
    elements.assignWorkConfirm.setAttribute('aria-hidden', 'true');
    elements.assignWorkError.hidden = true;
    elements.assignWorkError.textContent = '';
    elements.assignWorkApply.disabled = false;
    state.assignWorkStamp = '';
    elements.assignWorkSearch.value = '';
    elements.assignWorkMeta.textContent = tr('gr_budgets.convert.work_unselected');
    closeAssignWorkLookup();
  }

  function openAssignWork() {
    const header = state.detail && state.detail.header;
    if (isEditing() || state.loadingCount || !selectedBudgetStamp() || !header || header.closed || header.cancelled) return;
    elements.assignWorkError.hidden = true;
    elements.assignWorkError.textContent = '';
    const work = state.detail && state.detail.work;
    if (work && work.opcstamp) {
      state.assignWorkStamp = String(work.opcstamp);
      elements.assignWorkSearch.value = [work.process, work.description].filter(Boolean).join(' · ');
      elements.assignWorkMeta.textContent = tr('gr_budgets.convert.work_selected', { process: work.process || '' });
    } else {
      state.assignWorkStamp = '';
      elements.assignWorkSearch.value = '';
      elements.assignWorkMeta.textContent = tr('gr_budgets.convert.work_unselected');
    }
    elements.assignWorkConfirm.classList.add('sz_is_open');
    elements.assignWorkConfirm.setAttribute('aria-hidden', 'false');
    elements.assignWorkSearch.focus();
  }

  async function applyAssignWork() {
    const bostamp = selectedBudgetStamp();
    if (!bostamp || state.loadingCount) return;
    if (!state.assignWorkStamp) {
      elements.assignWorkError.textContent = tr('gr_budgets.convert.work_required');
      elements.assignWorkError.hidden = false;
      return;
    }
    elements.assignWorkApply.disabled = true;
    elements.assignWorkError.hidden = true;
    showLoading(true);
    try {
      await postJson(`/orcamento/${encodeURIComponent(bostamp)}/obra`, {
        feid: elements.company.value,
        opcstamp: state.assignWorkStamp
      });
      closeAssignWork();
      await loadBudgets(bostamp);
    } catch (error) {
      elements.assignWorkError.textContent = error.message;
      elements.assignWorkError.hidden = false;
      elements.assignWorkApply.disabled = false;
    } finally {
      showLoading(false);
    }
  }

  function openBudgetConversion() {
    if (isEditing() || state.loadingCount || !selectedBudgetStamp() || !budgetConversionAvailable()) return;
    elements.convertExecutionError.hidden = true;
    elements.convertExecutionError.textContent = '';
    root.querySelector('input[name="budgetConvertTarget"][value="new"]').checked = true;
    updateConvertTarget();
    elements.convertExecutionConfirm.classList.add('sz_is_open');
    elements.convertExecutionConfirm.setAttribute('aria-hidden', 'false');
    elements.convertExecutionApply.focus();
  }

  async function applyBudgetConversion() {
    const bostamp = selectedBudgetStamp();
    const target = conversionTarget();
    if (!bostamp || state.loadingCount) return;
    if (target === 'existing' && !state.convertWorkStamp) {
      elements.convertExecutionError.textContent = tr('gr_budgets.convert.work_required');
      elements.convertExecutionError.hidden = false;
      return;
    }
    elements.convertExecutionApply.disabled = true;
    elements.convertExecutionError.hidden = true;
    showLoading(true);
    try {
      const payload = await postJson(`/orcamento/${encodeURIComponent(bostamp)}/converter-estudo-execucao`, {
        feid: elements.company.value,
        target,
        opcstamp: state.convertWorkStamp
      });
      closeBudgetConversion();
      await loadSeries();
      elements.series.value = String(payload.ndos || elements.series.value);
      elements.year.value = String(payload.year || elements.year.value);
      await loadBudgets(bostamp);
    } catch (error) {
      elements.convertExecutionError.textContent = error.message;
      elements.convertExecutionError.hidden = false;
      elements.convertExecutionApply.disabled = false;
    } finally {
      showLoading(false);
    }
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
      ? tr(
        row.establishment ? 'gr_budgets.client.label_number_establishment' : 'gr_budgets.client.label_number',
        { number: row.number, establishment: row.establishment }
      )
      : tr('gr_budgets.client.meta_selected');
    if (row.contact) setInputValue(elements.attentionInput, row.contact);
    if (row.salesperson_number) {
      renderSalespeople(row.salesperson_number, row.salesperson);
    }
    syncEditableHeaderToState();
    closeClientLookup();
    if (state.detail && state.detail.header) {
      const rates = availableVatRates();
      const requestedVatTable = Number(row.vat_table || 0);
      const defaultVat = rates.find((rate) => Number(rate.table || 0) === requestedVatTable)
        || rates.find((rate) => Number(rate.table || 0) === 2)
        || rates[0]
        || { table: 0, rate: 0 };
      const defaultVatTable = Number(defaultVat.table || 0);
      const defaultVatRate = Number(defaultVat.rate || 0);
      state.detail.header.default_vat_table = defaultVatTable;
      state.detail.header.default_vat_rate = defaultVatRate;
      if (defaultVatTable > 0) {
        (state.detail.lines || []).forEach((line) => {
          if (Number(line.vat_table || 0) <= 0) {
            line.vat_table = defaultVatTable;
            line.vat_rate = defaultVatRate;
          }
        });
      }
      renderLines(state.detail.lines || [], state.detail.header.currency, state.detail.totals || {});
    }
    elements.clientSearch.focus();
  }

  function renderClientRows(rows) {
    state.clientRows = Array.isArray(rows) ? rows : [];
    elements.clientResults.replaceChildren();
    if (!state.clientRows.length) {
      renderClientMessage(tr('gr_budgets.label.no_results'));
      return;
    }
    state.clientRows.forEach((row, index) => {
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'sz_table_lookup_item';
      const title = document.createElement('span');
      title.className = 'sz_table_lookup_item_label';
      title.textContent = row.name || tr('gr_budgets.label.client_fallback', { number: row.number });
      const meta = document.createElement('span');
      meta.className = 'sz_table_lookup_item_value';
      meta.textContent = [
        row.number ? tr('gr_budgets.client.number_short', { number: row.number }) : '',
        row.vat_number ? tr('gr_budgets.client.vat_number', { number: row.vat_number }) : '',
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
      renderClientMessage(tr('gr_budgets.client.searching'));
      try {
        const payload = await getJson('/clientes', { feid: elements.company.value, q: query });
        if (version !== state.clientRequestVersion) return;
        renderClientRows(payload.rows || []);
      } catch (error) {
        if (version !== state.clientRequestVersion) return;
        renderClientMessage(error.message || tr('gr_budgets.error.search'), true);
      }
    }, 250);
  }

  function availableVatRates() {
    const detailRates = state.detail && state.detail.tax_rates;
    const rows = Array.isArray(detailRates) && detailRates.length ? detailRates : (state.taxRates || []);
    const seen = new Set();
    return rows.filter((row) => {
      const table = Number(row && row.table || 0);
      if (table <= 0 || seen.has(table)) return false;
      seen.add(table);
      return true;
    });
  }

  function vatRateForTable(table, fallback) {
    const selected = availableVatRates().find((row) => Number(row.table || 0) === Number(table || 0));
    return selected ? Number(selected.rate || 0) : Number(fallback || 0);
  }

  function vatLabel(line) {
    const table = Number(line && line.vat_table || 0);
    if (table <= 0) return '—';
    const rate = vatRateForTable(table, line && line.vat_rate);
    return `${table} · ${percentFormatter.format(rate)}%`;
  }

  function vatControl(line, index) {
    const selectedTable = Number(line && line.vat_table || 0);
    const rates = availableVatRates().slice();
    if (selectedTable > 0 && !rates.some((row) => Number(row.table || 0) === selectedTable)) {
      rates.push({ table: selectedTable, rate: Number(line.vat_rate || 0) });
    }
    if (!isEditing()) return escapeHtml(vatLabel(line));
    const options = ['<option value="">—</option>'].concat(rates.map((row) => {
      const table = Number(row.table || 0);
      const selected = table === selectedTable ? ' selected' : '';
      return `<option value="${table}"${selected}>${escapeHtml(`${table} · ${percentFormatter.format(Number(row.rate || 0))}%`)}</option>`;
    }));
    return `<select class="sz_select gr-budget-vat-select" data-budget-line-vat="${index}" aria-label="${escapeHtml(tr('gr_budgets.field.vat'))}">${options.join('')}</select>`;
  }

  function closeVatApply() {
    elements.vatApply.classList.remove('sz_is_open');
    elements.vatApply.setAttribute('aria-hidden', 'true');
    elements.vatApplyError.hidden = true;
    elements.vatApplyError.textContent = '';
  }

  function openVatApply() {
    if (isEditing() || state.loadingCount || !state.detail || !selectedBudgetStamp() || !budgetCanBeEdited()) return;
    const rates = availableVatRates();
    if (!rates.length) {
      showError(tr('gr_budgets.error.vat_rates_unavailable'));
      return;
    }
    showError('');
    elements.vatApplySelect.replaceChildren(...rates.map((row) => {
      const option = document.createElement('option');
      option.value = String(Number(row.table || 0));
      option.textContent = `${Number(row.table || 0)} · ${percentFormatter.format(Number(row.rate || 0))}%`;
      return option;
    }));
    const headerTable = Number(state.detail.header?.default_vat_table || 0);
    const lineTable = Number((state.detail.lines || []).find((line) => Number(line.vat_table || 0) > 0)?.vat_table || 0);
    const wantedTable = headerTable || lineTable;
    if (wantedTable && Array.from(elements.vatApplySelect.options).some((option) => Number(option.value) === wantedTable)) {
      elements.vatApplySelect.value = String(wantedTable);
    }
    elements.vatApplyError.hidden = true;
    elements.vatApplyError.textContent = '';
    elements.vatApply.classList.add('sz_is_open');
    elements.vatApply.setAttribute('aria-hidden', 'false');
    elements.vatApplySelect.focus();
  }

  function applyVatToAllLines() {
    if (!state.detail) return;
    const vatTable = Number(elements.vatApplySelect.value || 0);
    const selected = availableVatRates().find((row) => Number(row.table || 0) === vatTable);
    if (!selected) {
      elements.vatApplyError.textContent = tr('gr_budgets.vat_apply.invalid');
      elements.vatApplyError.hidden = false;
      elements.vatApplySelect.focus();
      return;
    }
    const vatRate = Number(selected.rate || 0);
    syncEditableHeaderToState();
    state.detail.header.default_vat_table = vatTable;
    state.detail.header.default_vat_rate = vatRate;
    (state.detail.lines || []).forEach((line) => {
      line.vat_table = vatTable;
      line.vat_rate = vatRate;
    });
    state.returnStamp = selectedBudgetStamp();
    state.mode = 'edit';
    closeVatApply();
    renderDetail(state.detail);
    updateInteractionState();
  }

  function renderLines(lines, currency, totals) {
    elements.lines.innerHTML = lines.map((line, index) => {
      const title = line.designation || line.description || tr('gr_budgets.line.no_designation');
      const secondary = line.description && line.description !== line.designation ? line.description : '';
      const plusValue = isPlusValue(line.reference);
      const commercialAdjustment = isBudgetDiscountLine(line);
      const nonTechnicalLine = plusValue || commercialAdjustment;
      const technicalControl = nonTechnicalLine
        ? '<span class="sz_text_muted">—</span>'
        : `<button type="button" class="sz_button sz_button_ghost gr-budget-technical-button" data-technical-line="${index}" aria-label="${escapeHtml(tr('gr_budgets.action.technical_line_aria', { line: line.item_label || line.item || index + 1 }))}" title="${escapeHtml(tr('gr_budgets.action.technical_detail_title'))}">+</button>`;
      const duplicateControl = nonTechnicalLine || !budgetCanBeEdited()
        ? ''
        : `<button type="button" class="sz_button sz_button_ghost gr-budget-duplicate-line-button" data-duplicate-line="${index}" data-tooltip="${escapeHtml(tr('gr_budgets.title.duplicate_position'))}" aria-label="${escapeHtml(tr('gr_budgets.action.duplicate_position_aria', { position: line.item_label || line.item || index + 1 }))}"><i class="fa-solid fa-copy" aria-hidden="true"></i></button>`;
      const editControl = nonTechnicalLine || !budgetCanBeEdited()
        ? ''
        : `<button type="button" class="sz_button sz_button_ghost gr-budget-edit-line-button" data-edit-line="${index}" title="${escapeHtml(tr('gr_budgets.action.edit'))}" aria-label="${escapeHtml(tr('gr_budgets.action.edit'))}"><i class="fa-solid fa-pen" aria-hidden="true"></i></button>`;
      const deleteControl = !isEditing()
        ? ''
        : `<button type="button" class="sz_button sz_button_ghost gr-budget-delete-line-button" data-delete-line="${index}" title="${escapeHtml(tr('gr_budgets.action.delete_position'))}" aria-label="${escapeHtml(tr('gr_budgets.action.delete_position_aria', { position: line.item_label || line.item || index + 1 }))}"><i class="fa-solid fa-trash-can" aria-hidden="true"></i></button>`;
      return `<tr class="sz_table_row${plusValue ? ' is-plus-value' : ''}${commercialAdjustment ? ' is-commercial-adjustment' : ''}">
        <td class="gr-budget-num">${escapeHtml(line.item_label || line.item || index + 1)}</td>
        <td>${escapeHtml(line.reference || '—')}</td>
        <td title="${escapeHtml(secondary || title)}"><div class="gr-budget-line-title">${escapeHtml(title)}</div>${secondary ? `<div class="gr-budget-line-subtitle">${escapeHtml(secondary)}</div>` : ''}</td>
        <td class="gr-budget-num">${quantityFormatter.format(Number(line.quantity || 0))}</td>
        <td class="gr-budget-col-unit">${escapeHtml(line.unit || '—')}</td>
        <td class="gr-budget-num">${quantityFormatter.format(Number(line.thickness || 0))}</td>
        <td class="gr-budget-num">${lineAmountFormatter.format(Number(line.unit_price || 0))}</td>
        <td class="gr-budget-num"><strong>${lineAmountFormatter.format(Number(line.total || 0))}</strong></td>
        <td class="gr-budget-vat">${vatControl(line, index)}</td>
        <td class="gr-budget-check">${technicalControl}</td>
        <td class="gr-budget-num">${lineAmountFormatter.format(Number(line.cost_total || 0))}</td>
        <td class="gr-budget-num">${percentFormatter.format(Number(line.margin_percentage || 0))}%</td>
        <td class="gr-budget-num">${lineAmountFormatter.format(Number(line.profit || 0))}</td>
        <td class="gr-budget-line-actions-column"><span class="gr-budget-line-actions">${editControl}${duplicateControl}${deleteControl}</span></td>
      </tr>`;
    }).join('');
    elements.linesFooter.innerHTML = `<tr>
      <td colspan="7">${escapeHtml(tr(lines.length === 1 ? 'gr_budgets.total.row_one' : 'gr_budgets.total.rows', { count: lines.length }))}</td>
      <td class="gr-budget-num">${escapeHtml(money(totals.total, currency))}</td>
      <td></td>
      <td></td>
      <td class="gr-budget-num">${escapeHtml(money(totals.cost, currency))}</td>
      <td class="gr-budget-num">${percentFormatter.format(Number(totals.margin_percentage || 0))}%</td>
      <td class="gr-budget-num">${escapeHtml(money(totals.profit, currency))}</td>
      <td></td>
    </tr>`;
  }

  function cloneData(value) {
    return JSON.parse(JSON.stringify(value == null ? null : value));
  }

  function parseLocalizedNumber(rawValue) {
    let raw = String(rawValue == null ? '' : rawValue).trim().replace(/[\s\u00a0\u202f]/g, '');
    if (!raw) return null;
    if (raw.includes(',') && raw.includes('.')) {
      raw = raw.lastIndexOf(',') > raw.lastIndexOf('.')
        ? raw.replaceAll('.', '').replace(',', '.')
        : raw.replaceAll(',', '');
    } else {
      raw = raw.replace(',', '.');
    }
    const value = Number.parseFloat(raw);
    return Number.isFinite(value) ? value : null;
  }

  function numericInput(element) {
    if (!element) return 0;
    if (typeof element.valueAsNumber === 'number' && Number.isFinite(element.valueAsNumber)) {
      return element.valueAsNumber;
    }
    const value = parseLocalizedNumber(element.value);
    return value == null ? 0 : value;
  }

  function ociNumericInput(element) {
    if (!element) return 0;
    const parsed = parseLocalizedNumber(element.value);
    if (parsed != null) {
      element.dataset.lastValidValue = String(parsed);
      return parsed;
    }
    const remembered = parseLocalizedNumber(element.dataset.lastValidValue);
    return remembered == null ? 0 : remembered;
  }

  function finiteNumber(value, fallback) {
    const number = Number(value);
    return Number.isFinite(number) ? number : (fallback == null ? 0 : fallback);
  }

  function roundMoney(value) {
    const number = finiteNumber(value);
    const rounded = Math.round((Math.abs(number) + Number.EPSILON) * 100) / 100;
    return number < 0 ? -rounded : rounded;
  }

  function newDraftId(kind) {
    state.draftSequence += 1;
    return `draft-${kind}-${Date.now()}-${state.draftSequence}`;
  }

  function clonedTechnicalRows(sourceLine, newLineStamp) {
    const sourceRows = Array.isArray(sourceLine && sourceLine._ociRows)
      ? sourceLine._ociRows
      : (Array.isArray(sourceLine && sourceLine.technical_lines) ? sourceLine.technical_lines : []);
    return cloneData(sourceRows).map((row) => ({
      ...row,
      stamp: newDraftId('oci'),
      budget_stamp: '',
      line_stamp: newLineStamp
    }));
  }

  function cloneLineForDraft(sourceLine, item, itemLabel, order) {
    const bistamp = newDraftId('line');
    const technicalRows = clonedTechnicalRows(sourceLine, bistamp);
    return {
      ...cloneData(sourceLine),
      bistamp,
      budget_stamp: '',
      item,
      item_label: String(itemLabel),
      order,
      _parent_bistamp: '',
      _ociRows: cloneData(technicalRows),
      technical_lines: cloneData(technicalRows)
    };
  }

  function cloneBudgetLinesForDraft(sourceLines) {
    const stampMap = new Map();
    const clonedLines = (sourceLines || []).map((sourceLine, index) => {
      const itemLabel = String(sourceLine.item_label || sourceLine.item || index + 1);
      const labelItem = Number.parseInt(itemLabel.split('.', 1)[0], 10);
      const orderItem = Math.trunc(finiteNumber(sourceLine.order) / 10000);
      const item = labelItem > 0 ? labelItem : (orderItem > 0 ? orderItem : index + 1);
      const copy = cloneLineForDraft(
        sourceLine,
        item,
        itemLabel,
        finiteNumber(sourceLine.order, (index + 1) * 10000)
      );
      if (sourceLine.bistamp) stampMap.set(sourceLine.bistamp, copy.bistamp);
      return copy;
    });
    clonedLines.forEach((copy, index) => {
      const sourceParent = (sourceLines[index] && sourceLines[index]._parent_bistamp) || '';
      if (sourceParent && stampMap.has(sourceParent)) copy._parent_bistamp = stampMap.get(sourceParent);
    });
    return clonedLines;
  }

  function nextBudgetPosition() {
    return ((state.detail && state.detail.lines) || []).reduce((maximum, line, index) => {
      const label = String(line.item_label || line.item || '').trim();
      const labelPosition = Number.parseInt(label.split('.', 1)[0], 10);
      const orderPosition = Math.trunc(finiteNumber(line.order) / 10000);
      return Math.max(
        maximum,
        Number.isFinite(labelPosition) ? labelPosition : 0,
        orderPosition > 0 ? orderPosition : 0,
        index + 1
      );
    }, 0) + 1;
  }

  function setNumericInput(element, value, decimals) {
    const number = Number(value || 0);
    if (!element) return;
    const precision = decimals == null ? 4 : decimals;
    if (!Number.isFinite(number)) {
      element.value = precision === 2 ? '0.00' : '0';
      return;
    }
    const formatted = number.toFixed(precision);
    element.value = precision === 2 ? formatted : formatted.replace(/\.?0+$/, '');
  }

  function commitOciNumericInputs() {
    elements.ociRows.querySelectorAll('[data-oci-numeric]').forEach((input) => {
      const precision = Number.parseInt(input.dataset.ociPrecision || '4', 10);
      const value = ociNumericInput(input);
      setNumericInput(input, value, Number.isFinite(precision) ? precision : 4);
      input.dataset.lastValidValue = String(value);
    });
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
    const defaultVatTable = Number(state.detail?.header?.default_vat_table || 0);
    const defaultVatRate = Number(state.detail?.header?.default_vat_rate || 0);
    return {
      bistamp: `draft-line-${Date.now()}`,
      order: nextItem * 10000,
      item: nextItem,
      reference: '',
      designation: '',
      description: '',
      quantity: 0,
      surface: 0,
      unit: 'M²',
      thickness: 0,
      volume: 0,
      unit_cost: 0,
      cost_total: 0,
      unit_price: 0,
      total: 0,
      vat_table: defaultVatTable,
      vat_rate: defaultVatRate,
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
      base_purchase_price: 0,
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
    elements.componentFamilyTitle.textContent = family ? family.name : tr('gr_budgets.component.articles');
    elements.componentArticleCount.textContent = plural('gr_budgets.count.article_one', 'gr_budgets.count.article_other', articles.length);
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
    }).join('') : `<tr><td colspan="5" class="sz_text_muted">${escapeHtml(tr('gr_budgets.component.empty_family'))}</td></tr>`;
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
      : tr('gr_budgets.component.select_article');
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
      showOciError(tr('gr_budgets.error.no_component_families'));
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
      purchase_price: roundMoney(article.purchase_price),
      base_purchase_price: roundMoney(article.base_purchase_price),
      forfait: roundMoney(article.forfait),
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
    return [`<option value="">${escapeHtml(tr('gr_budgets.formula.none'))}</option>`].concat(formulas.map((row) => {
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
    return `<tr class="sz_table_row${plusValue ? ' is-plus-value' : ''}" data-oci-stamp="${escapeHtml(row.stamp || '')}" data-oci-family="${escapeHtml(row.family || '')}" data-oci-reference="${escapeHtml(row.reference || '')}" data-oci-quantity="${escapeHtml(row.quantity == null ? 1 : row.quantity)}" data-oci-total-quantity="${escapeHtml(row.total_quantity || 0)}" data-oci-base-purchase-price="${escapeHtml(roundMoney(row.base_purchase_price || 0))}" data-oci-source-designation="${escapeHtml(sourceDesignation)}" data-oci-plus-value="${plusValue ? '1' : '0'}">
      <td data-oci-cell="designation"><input class="sz_input" data-oci-field="designation" value="${escapeHtml(row.designation || '')}" maxlength="220"></td>
      <td data-oci-cell="formula"><select class="sz_select" data-oci-field="formula">${formulaOptions(row.formula)}</select></td>
      <td data-oci-cell="purchase_price"><input class="sz_input gr-budget-number-input" data-oci-field="purchase_price" data-oci-numeric data-oci-precision="2" data-last-valid-value="${escapeHtml(roundMoney(row.purchase_price || 0))}" type="text" inputmode="decimal" autocomplete="off" value="${escapeHtml(roundMoney(row.purchase_price).toFixed(2))}"></td>
      <td data-oci-cell="forfait"><input class="sz_input gr-budget-number-input" data-oci-field="forfait" data-oci-numeric data-oci-precision="2" data-last-valid-value="${escapeHtml(roundMoney(row.forfait || 0))}" type="text" inputmode="decimal" autocomplete="off" value="${escapeHtml(roundMoney(row.forfait).toFixed(2))}"></td>
      <td data-oci-cell="area"><input class="sz_input gr-budget-number-input" data-oci-field="area" type="number" min="0" step="0.01" value="${escapeHtml(row.area || 0)}" readonly></td>
      <td data-oci-cell="thickness"><input class="sz_input gr-budget-number-input" data-oci-field="thickness" type="number" min="0" step="0.001" value="${escapeHtml(row.thickness || 0)}" readonly></td>
      <td data-oci-cell="volume"><input class="sz_input gr-budget-number-input" data-oci-field="volume" type="number" min="0" step="0.001" value="${escapeHtml(row.volume || 0)}" readonly></td>
      <td data-oci-cell="weight"><input class="sz_input gr-budget-number-input" data-oci-field="weight" data-oci-numeric data-oci-precision="2" data-last-valid-value="${escapeHtml(finiteNumber(row.weight))}" type="text" inputmode="decimal" autocomplete="off" value="${escapeHtml(row.weight || 0)}"></td>
      <td data-oci-cell="consumption"><input class="sz_input gr-budget-number-input" data-oci-field="consumption" data-oci-numeric data-oci-precision="4" data-last-valid-value="${escapeHtml(finiteNumber(row.consumption))}" type="text" inputmode="decimal" autocomplete="off" value="${escapeHtml(row.consumption || 0)}"></td>
      <td data-oci-cell="coefficient"><input class="sz_input gr-budget-number-input" data-oci-field="coefficient" data-oci-numeric data-oci-precision="4" data-last-valid-value="${escapeHtml(finiteNumber(row.coefficient))}" type="text" inputmode="decimal" autocomplete="off" value="${escapeHtml(row.coefficient || 0)}"></td>
      <td data-oci-cell="cost"><input class="sz_input gr-budget-number-input" data-oci-cost data-last-valid-cost="${initialCost > 0 ? escapeHtml(initialCost) : ''}" type="text" inputmode="decimal" readonly value="${escapeHtml(numberFormatter.format(initialCost))}"></td>
      <td data-oci-cell="unit">${unitControl}</td>
      <td><button type="button" class="sz_button sz_button_ghost gr-budget-oci-delete" data-oci-delete title="${escapeHtml(tr('gr_budgets.action.remove_component'))}" aria-label="${escapeHtml(tr('gr_budgets.action.remove_component'))}"><i class="fa-solid fa-trash-can" aria-hidden="true"></i></button></td>
    </tr>`;
  }

  function renderOciRows(rows) {
    const safeRows = Array.isArray(rows) ? rows : [];
    elements.ociRows.innerHTML = safeRows.map(ociRowMarkup).join('');
    text('budgetOciRowCount', plural('gr_budgets.count.oci_line_one', 'gr_budgets.count.oci_line_other', safeRows.length));
    elements.ociRows.querySelectorAll('tr').forEach(updateOciRowFormulaState);
    recalculateOci();
    renderOciFamilySidebar();
  }

  function appendOciRow(row) {
    elements.ociRows.insertAdjacentHTML('beforeend', ociRowMarkup(row));
    const appendedRow = elements.ociRows.lastElementChild;
    if (appendedRow) updateOciRowFormulaState(appendedRow);
    const rowCount = elements.ociRows.querySelectorAll('tr').length;
    text('budgetOciRowCount', plural('gr_budgets.count.oci_line_one', 'gr_budgets.count.oci_line_other', rowCount));
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
    if (input.matches('[data-oci-numeric]')) return ociNumericInput(input);
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
      purchase_price: roundMoney(ociRowValue(row, 'purchase_price')),
      purchase_price_text: row.querySelector('[data-oci-field="purchase_price"]')?.value || '',
      base_purchase_price: roundMoney(row.dataset.ociBasePurchasePrice),
      forfait: roundMoney(ociRowValue(row, 'forfait')),
      area: ociRowValue(row, 'area'),
      thickness: ociRowValue(row, 'thickness'),
      volume: ociRowValue(row, 'volume'),
      weight: ociRowValue(row, 'weight'),
      consumption: ociRowValue(row, 'consumption'),
      coefficient: ociRowValue(row, 'coefficient'),
      quantity: finiteNumber(row.dataset.ociQuantity, 1),
      total_quantity: finiteNumber(row.dataset.ociTotalQuantity),
      cost_per_unit: roundMoney(numericInput(row.querySelector('[data-oci-cost]'))),
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
    const purchasePrice = roundMoney(row.purchase_price);
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
    const purchasePrice = roundMoney(row.purchase_price);
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

  function recalculateOci(options) {
    const preserveMarginInput = Boolean(options && options.preserveMarginInput);
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
    purchasePrice = roundMoney(finiteNumber(purchasePrice, 0.1));

    const prorata = Math.min(99.99, Math.max(0, numericInput(elements.ociProrata)));
    const purchaseTotal = roundMoney(purchasePrice * surface);
    let salePrice = roundMoney(numericInput(elements.ociSalePrice));
    if (!state.ociPriceLocked) {
      const targetMargin = Math.min(99.99, Math.max(-999.99, Number(state.ociTargetMargin || 0)));
      const marginFactor = 1 - targetMargin / 100;
      const prorataFactor = 1 - prorata / 100;
      salePrice = roundMoney(marginFactor > 0 && prorataFactor > 0 ? purchasePrice / marginFactor / prorataFactor : 0);
      setNumericInput(elements.ociSalePrice, salePrice, 2);
    }
    const saleTotal = roundMoney(salePrice * surface * (1 - prorata / 100));
    const marginUnit = roundMoney(salePrice - purchasePrice);
    const marginTotal = roundMoney(saleTotal - purchaseTotal);
    const marginPercentage = saleTotal ? marginTotal / saleTotal * 100 : 0;
    setNumericInput(elements.ociPurchasePrice, purchasePrice, 2);
    setNumericInput(elements.ociPurchaseTotal, purchaseTotal, 2);
    setNumericInput(elements.ociSaleTotal, saleTotal, 2);
    setNumericInput(elements.ociMarginUnit, marginUnit, 4);
    setNumericInput(elements.ociMarginTotal, marginTotal, 2);
    // Do not replace the value while the user is still typing the target
    // margin. Otherwise entering "15" becomes "1.00" after the first key
    // stroke and the following key can no longer form the intended value.
    if (!preserveMarginInput) setNumericInput(elements.ociMarginPercent, marginPercentage, 2);
    if (state.ociPriceLocked) state.ociTargetMargin = marginPercentage;
    updatePriceDriver();

    const rowCount = elements.ociRows.querySelectorAll('tr').length;
    const linesLabel = tr(rowCount === 1 ? 'gr_budgets.label.line_singular' : 'gr_budgets.label.line_plural');
    elements.ociFooter.innerHTML = `<tr><td colspan="10">${escapeHtml(tr('gr_budgets.total.oci', { count: rowCount, lines: linesLabel }))}</td><td class="gr-budget-num">${lineAmountFormatter.format(purchasePrice)}</td><td></td><td></td></tr>`;
  }

  function collectSingleOciRow(row) {
    return {
      formula: ociRowValue(row, 'formula'),
      purchase_price: roundMoney(ociRowValue(row, 'purchase_price')),
      forfait: roundMoney(ociRowValue(row, 'forfait')),
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
    empty.textContent = tr('gr_budgets.label.select_ouvrage_type');
    elements.ociOuvrage.appendChild(empty);
    ouvrages.forEach((row) => {
      const option = document.createElement('option');
      option.value = row.reference;
      option.textContent = `${row.reference} · ${row.designation}`;
      elements.ociOuvrage.appendChild(option);
    });
    elements.ociOuvrage.value = selectedReference || '';
  }

  function populateLineUnitOptions(selectedUnit) {
    const unitKey = (value) => String(value || '').trim().toLocaleUpperCase();
    const defaultUnit = 'M²';
    const uniqueUnits = [];
    const seen = new Set();
    [defaultUnit, ...((state.technicalOptions && state.technicalOptions.units) || [])].forEach((value) => {
      const unit = String(value || '').trim();
      const key = unitKey(unit);
      if (!unit || seen.has(key)) return;
      seen.add(key);
      uniqueUnits.push(unit);
    });

    const requested = String(selectedUnit || '').trim() || defaultUnit;
    let selected = uniqueUnits.find((unit) => unitKey(unit) === unitKey(requested));
    if (!selected) {
      selected = requested;
      uniqueUnits.push(requested);
    }

    elements.ociUnit.replaceChildren();
    uniqueUnits.forEach((unit) => {
      const option = document.createElement('option');
      option.value = unit;
      option.textContent = unit;
      elements.ociUnit.appendChild(option);
    });
    elements.ociUnit.value = selected;
  }

  function budgetProrata() {
    const lines = ((state.detail && state.detail.lines) || []).slice().reverse();
    const line = lines.find((row) => Number(row.discount_2 || 0) > 0);
    return Number((line && line.discount_2) || 0);
  }

  function renderOciView(line, rows, newLine) {
    populateOuvrageOptions(line.reference);
    populateLineUnitOptions(line.unit || 'M²');
    setInputValue(elements.ociPosition, line.item);
    setInputValue(elements.ociReference, line.reference);
    setInputValue(elements.ociDesignation, line.designation);
    setInputValue(elements.ociDescription, line.description || line.designation);
    setNumericInput(elements.ociSurface, line.surface == null ? line.quantity : line.surface, 4);
    setNumericInput(elements.ociThickness, line.thickness, 4);
    setNumericInput(elements.ociSalePrice, line.unit_price, 2);
    setNumericInput(elements.ociProrata, Number(line.discount_2 || 0) > 0 ? line.discount_2 : budgetProrata(), 2);
    state.ociPriceLocked = newLine ? true : Boolean(line.blocked_price || !Number(line.margin_percentage || 0));
    state.ociTargetMargin = Number(line.margin_percentage || 0);
    elements.ociSimultaneous.checked = Boolean(line.simultaneous);
    elements.ociVariant.checked = Boolean(line.variant);
    elements.ociOption.checked = Boolean(line.option);
    elements.ociBlockedPrice.checked = Boolean(line.blocked_price);
    elements.ociPump.checked = Boolean(line.pump);
    elements.ociLabour.checked = Boolean(line.labour);
    elements.ociMode.textContent = newLine
      ? tr('gr_budgets.action.new_line')
      : tr('gr_budgets.label.line_number', { number: line.item || '—' });
    elements.ociMode.className = `sz_badge ${newLine ? 'sz_badge_warning' : 'sz_badge_info'}`;
    elements.ociDuplicate.disabled = !budgetCanBeEdited();
    const budgetHeader = (state.detail && state.detail.header) || {};
    elements.ociSubtitle.textContent = `${budgetHeader.series || tr('gr_budgets.label.budget')} ${budgetHeader.number || tr('gr_budgets.label.budget_new')} · ${line.reference || tr('gr_budgets.label.no_reference')}${line.designation ? ` — ${line.designation}` : ''}`;
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
    const lines = ((state.detail && state.detail.lines) || []).filter((line) => !isBudgetDiscountLine(line));
    const count = lines.length;
    elements.ociPositions.hidden = count <= 1;
    elements.ociPositionsCount.textContent = plural('gr_budgets.count.position_one', 'gr_budgets.count.position_other', count);
  }

  function positionCardMarkup(line, index, currency) {
    const label = positionLabel(line, index);
    const current = isCurrentOciPosition(line, index);
    const subposition = label.includes('.');
    const description = line.description || line.designation || tr('gr_budgets.label.position_without_description');
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
    const stateLabel = current
      ? tr('gr_budgets.label.position_current')
      : (subposition ? tr('gr_budgets.label.subposition') : tr('gr_budgets.label.position'));
    return `<button type="button" class="gr-budget-position-card${classes}" data-position-line="${index}" title="${stateLabel} ${escapeHtml(label)}"${current ? ' aria-current="true"' : ''}>
      <span class="gr-budget-position-number">${escapeHtml(label)}</span>
      <span class="gr-budget-position-card-content">
        <span class="gr-budget-position-description">${escapeHtml(description)}</span>
        <span class="gr-budget-position-quantity">${escapeHtml(tr('gr_budgets.label.position_quantity', {
          quantity: quantityFormatter.format(quantity),
          unit,
          thickness: quantityFormatter.format(thickness),
          volume: quantityFormatter.format(volume)
        }))}</span>
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
    const indexedLines = lines
      .map((line, index) => ({ line, index }))
      .filter(({ line }) => !isBudgetDiscountLine(line))
      .sort((left, right) => compareBudgetLines(left.line, right.line));
    elements.positionPickerSubtitle.textContent = plural(
      'gr_budgets.count.position_available_one',
      'gr_budgets.count.position_available_other',
      indexedLines.length
    );
    elements.positionCards.innerHTML = indexedLines.map(({ line, index }) => positionCardMarkup(line, index, currency)).join('');
  }

  function openPositionPicker() {
    const lines = ((state.detail && state.detail.lines) || []).filter((line) => !isBudgetDiscountLine(line));
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

  function closePositionDuplicateConfirm() {
    elements.positionDuplicateConfirm.classList.remove('sz_is_open');
    elements.positionDuplicateConfirm.setAttribute('aria-hidden', 'true');
    state.pendingPositionDuplicate = null;
  }

  function closeLineDeleteConfirm() {
    elements.lineDeleteConfirm.classList.remove('sz_is_open');
    elements.lineDeleteConfirm.setAttribute('aria-hidden', 'true');
    state.pendingLineDelete = null;
  }

  function requestBudgetLineDelete(lineIndex) {
    if (!isEditing() || !state.detail || !budgetCanBeEdited()) return;
    const line = (state.detail.lines || [])[lineIndex];
    if (!line) return;
    const position = String(line.item_label || line.item || lineIndex + 1);
    state.pendingLineDelete = {
      bistamp: String(line.bistamp || ''),
      position
    };
    elements.lineDeleteText.textContent = tr('gr_budgets.confirm.delete_position_question', { position });
    elements.lineDeleteConfirm.classList.add('sz_is_open');
    elements.lineDeleteConfirm.setAttribute('aria-hidden', 'false');
    elements.lineDeleteApply.focus();
  }

  function confirmBudgetLineDelete() {
    const pending = state.pendingLineDelete;
    if (!pending || !state.detail || !isEditing()) return;
    syncEditableHeaderToState();
    const prefix = `${pending.position}.`;
    const removedStamps = [];
    state.detail.lines = (state.detail.lines || []).filter((line) => {
      const stamp = String(line.bistamp || '');
      const label = String(line.item_label || line.item || '');
      const remove = stamp === pending.bistamp
        || label === pending.position
        || label.startsWith(prefix)
        || String(line._parent_bistamp || '') === pending.bistamp;
      if (remove && stamp) removedStamps.push(stamp);
      return !remove;
    });
    removedStamps.forEach((stamp) => state.ociCache.delete(stamp));
    closeLineDeleteConfirm();
    recalculateBudgetDraftTotals();
    renderDetail(state.detail);
    updateInteractionState();
  }

  function requestPositionDuplicate() {
    if (!state.ociContext || !budgetCanBeEdited()) return;
    state.pendingPositionDuplicate = { saveCurrent: true, lineIndex: state.ociContext.lineIndex };
    elements.positionDuplicateTitle.textContent = tr('gr_budgets.confirm.duplicate_position_title');
    elements.positionDuplicateText.textContent = tr('gr_budgets.confirm.duplicate_position_question');
    elements.positionDuplicateActionText.textContent = tr('gr_budgets.action.save_and_duplicate');
    elements.positionDuplicateConfirm.classList.add('sz_is_open');
    elements.positionDuplicateConfirm.setAttribute('aria-hidden', 'false');
    elements.positionDuplicateSave.focus();
  }

  function requestGridPositionDuplicate(lineIndex) {
    const line = state.detail && (state.detail.lines || [])[lineIndex];
    if (!line || !budgetCanBeEdited() || isPlusValue(line.reference)) return;
    const position = line.item_label || line.item || lineIndex + 1;
    state.pendingPositionDuplicate = { saveCurrent: false, lineIndex };
    elements.positionDuplicateTitle.textContent = tr('gr_budgets.confirm.duplicate_grid_position_title');
    elements.positionDuplicateText.textContent = tr('gr_budgets.confirm.duplicate_grid_position_question', { position });
    elements.positionDuplicateActionText.textContent = tr('gr_budgets.action.duplicate');
    elements.positionDuplicateConfirm.classList.add('sz_is_open');
    elements.positionDuplicateConfirm.setAttribute('aria-hidden', 'false');
    elements.positionDuplicateSave.focus();
  }

  function saveAndDuplicateCurrentPosition() {
    if (!state.ociContext) return;
    const sourceStamp = state.ociContext.line && state.ociContext.line.bistamp;
    closePositionDuplicateConfirm();
    if (!saveOciLine()) return;
    const sourceIndex = (state.detail.lines || []).findIndex((line) => line.bistamp === sourceStamp);
    if (sourceIndex < 0) return;
    const duplicateIndex = duplicatePosition(sourceIndex);
    if (duplicateIndex >= 0) openOci(duplicateIndex, false);
  }

  function confirmPositionDuplicate() {
    const pending = state.pendingPositionDuplicate;
    if (!pending) return;
    if (pending.saveCurrent) {
      saveAndDuplicateCurrentPosition();
      return;
    }
    const lineIndex = pending.lineIndex;
    closePositionDuplicateConfirm();
    duplicatePosition(lineIndex);
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
    elements.positionSwitchText.textContent = tr('gr_budgets.confirm.change_position_question', { position: state.pendingPositionTarget.label });
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
    if (!state.detail || state.loadingCount) return;
    if (state.ociContext && !elements.ociView.hidden) return;
    if (state.ociContext) state.ociContext = null;
    syncEditableHeaderToState();
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
    closePositionDuplicateConfirm();
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
    const total = roundMoney(included.reduce((sum, line) => sum + Number(line.total || 0), 0));
    const cost = roundMoney(included.reduce((sum, line) => sum + Number(line.cost_total || 0), 0));
    const profit = roundMoney(total - cost);
    state.detail.totals = {
      total,
      cost,
      profit,
      margin_percentage: total ? profit / total * 100 : 0,
      line_count: lines.length
    };
  }

  function isBudgetDiscountLine(line) {
    return normalizedCode(line && line.item_label) === 'ZZ'
      || normalizedCode(line && line.item) === 'ZZ'
      || normalizedCode(line && line.reference) === 'ZZ';
  }

  function budgetLinesWithoutDiscount() {
    return ((state.detail && state.detail.lines) || []).filter((line) => !isBudgetDiscountLine(line));
  }

  function budgetBaseTotal(lines) {
    return roundMoney((lines || [])
      .filter((line) => !line.variant && !line.option)
      .reduce((sum, line) => sum + Number(line.total || 0), 0));
  }

  function closeCommercialAdjustment() {
    elements.commercialAdjustment.classList.remove('sz_is_open');
    elements.commercialAdjustment.setAttribute('aria-hidden', 'true');
    elements.commercialAdjustmentError.hidden = true;
    elements.commercialAdjustmentError.textContent = '';
    state.commercialAdjustmentMode = '';
  }

  function openCommercialAdjustment(mode) {
    if (isEditing() || state.loadingCount || !state.detail || !selectedBudgetStamp() || !budgetCanBeEdited()) return;
    const baseLines = budgetLinesWithoutDiscount();
    const baseTotal = budgetBaseTotal(baseLines);
    const currentTotal = roundMoney(Number((state.detail.totals && state.detail.totals.total) || 0));
    const discountPercentage = baseTotal ? Math.max(0, (baseTotal - currentTotal) / baseTotal * 100) : 0;
    const finalPriceMode = mode === 'final';
    state.commercialAdjustmentMode = finalPriceMode ? 'final' : 'discount';
    elements.commercialAdjustmentTitle.textContent = tr(finalPriceMode
      ? 'gr_budgets.adjustment.final_title'
      : 'gr_budgets.adjustment.discount_title');
    elements.commercialAdjustmentText.textContent = tr(finalPriceMode
      ? 'gr_budgets.adjustment.final_text'
      : 'gr_budgets.adjustment.discount_text');
    elements.commercialAdjustmentLabel.textContent = tr(finalPriceMode
      ? 'gr_budgets.adjustment.final_label'
      : 'gr_budgets.adjustment.discount_label');
    elements.commercialAdjustmentValue.value = (finalPriceMode ? currentTotal : discountPercentage).toFixed(2);
    elements.commercialAdjustmentError.hidden = true;
    elements.commercialAdjustmentError.textContent = '';
    elements.commercialAdjustment.classList.add('sz_is_open');
    elements.commercialAdjustment.setAttribute('aria-hidden', 'false');
    elements.commercialAdjustmentValue.focus();
    elements.commercialAdjustmentValue.select();
  }

  function showCommercialAdjustmentError(message) {
    elements.commercialAdjustmentError.textContent = message;
    elements.commercialAdjustmentError.hidden = false;
  }

  function applyCommercialAdjustment() {
    if (!state.commercialAdjustmentMode || !state.detail) return;
    const value = parseLocalizedNumber(elements.commercialAdjustmentValue.value);
    if (value == null) {
      showCommercialAdjustmentError(tr('gr_budgets.adjustment.invalid_number'));
      elements.commercialAdjustmentValue.focus();
      return;
    }
    if (state.commercialAdjustmentMode === 'discount' && (value < 0 || value > 100)) {
      showCommercialAdjustmentError(tr('gr_budgets.adjustment.invalid_discount'));
      elements.commercialAdjustmentValue.focus();
      return;
    }
    if (state.commercialAdjustmentMode === 'final' && value < 0) {
      showCommercialAdjustmentError(tr('gr_budgets.adjustment.invalid_final_price'));
      elements.commercialAdjustmentValue.focus();
      return;
    }

    syncEditableHeaderToState();
    const baseLines = budgetLinesWithoutDiscount();
    const baseTotal = budgetBaseTotal(baseLines);
    const adjustment = roundMoney(state.commercialAdjustmentMode === 'discount'
      ? baseTotal * value / 100
      : baseTotal - value);
    const total = roundMoney(-adjustment);
    const vatSource = baseLines.find((line) => Number(line.vat_table || 0) > 0) || {};
    const header = state.detail.header || {};
    const vatTable = Number(header.default_vat_table || vatSource.vat_table || 0);
    const vatRate = vatRateForTable(vatTable, header.default_vat_rate || vatSource.vat_rate || 0);
    const discountLine = {
      bistamp: newDraftId('line'),
      budget_stamp: header.bostamp || '',
      order: 999999999,
      item: 'ZZ',
      item_label: 'ZZ',
      reference: '',
      designation: 'ESCOMPTE',
      description: 'ESCOMPTE',
      quantity: -1,
      surface: -1,
      unit: '',
      thickness: 0,
      volume: 0,
      discount_1: 0,
      discount_2: 0,
      unit_cost: 0,
      cost_total: 0,
      unit_price: adjustment,
      total,
      vat_table: vatTable,
      vat_rate: vatRate,
      margin_per_unit: adjustment,
      margin_value: total,
      margin_percentage: total ? 100 : 0,
      profit: total,
      has_technical_detail: false,
      simultaneous: false,
      variant: false,
      option: false,
      blocked_price: true,
      pump: false,
      labour: false,
      pro_rata: false,
      _ociRows: [],
      technical_lines: []
    };

    state.detail.lines = [...baseLines, discountLine].sort(compareBudgetLines);
    state.mode = 'edit';
    state.returnStamp = selectedBudgetStamp();
    state.ociCache.clear();
    closeCommercialAdjustment();
    recalculateBudgetDraftTotals();
    renderDetail(state.detail);
    updateInteractionState();
  }

  function duplicatePosition(lineIndex) {
    if (!state.detail || !budgetCanBeEdited()) return -1;
    const lines = state.detail.lines || [];
    const sourceLine = lines[lineIndex];
    if (!sourceLine || isPlusValue(sourceLine.reference) || isBudgetDiscountLine(sourceLine)) return -1;

    syncEditableHeaderToState();
    if (!isEditing()) {
      state.mode = 'edit';
      state.returnStamp = selectedBudgetStamp();
    }

    const newPosition = nextBudgetPosition();
    const sourceLabel = String(sourceLine.item_label || sourceLine.item || lineIndex + 1);
    const copy = cloneLineForDraft(sourceLine, newPosition, newPosition, newPosition * 10000);
    const childLines = lines
      .filter((candidate, index) => index !== lineIndex && String(candidate.item_label || '').startsWith(`${sourceLabel}.`))
      .sort(compareBudgetLines);

    const copiedChildren = childLines.map((child, index) => {
      const childLabel = String(child.item_label || '');
      const suffix = childLabel.slice(sourceLabel.length + 1) || String(index + 1);
      const childOrder = newPosition * 10000 + (index + 1) * 100;
      const childCopy = cloneLineForDraft(child, newPosition, `${newPosition}.${suffix}`, childOrder);
      childCopy._parent_bistamp = copy.bistamp;
      return childCopy;
    });

    state.detail.lines = [...lines, copy, ...copiedChildren].sort(compareBudgetLines);
    state.ociCache.clear();
    recalculateBudgetDraftTotals();
    renderDetail(state.detail);
    updateInteractionState();
    return state.detail.lines.findIndex((line) => line.bistamp === copy.bistamp);
  }

  function saveOciLine() {
    if (!state.ociContext) return false;
    if (!budgetCanBeEdited()) {
      showOciError(tr('gr_budgets.error.budget_locked'));
      return false;
    }
    const reference = elements.ociReference.value.trim();
    const designation = elements.ociDesignation.value.trim();
    const descriptionInput = elements.ociDescription.value.trim();
    const position = Math.max(1, Math.trunc(numericInput(elements.ociPosition)));
    const surface = numericInput(elements.ociSurface);
    if (!reference) {
      showOciError(tr('gr_budgets.error.detail_line_reference_required'));
      elements.ociOuvrage.focus();
      return false;
    }
    if (!designation) {
      showOciError(tr('gr_budgets.error.detail_line_designation_required'));
      elements.ociDesignation.focus();
      return false;
    }
    if (surface <= 0) {
      showOciError(tr('gr_budgets.error.detail_line_surface_positive'));
      elements.ociSurface.focus();
      return false;
    }

    commitOciNumericInputs();
    recalculateOci();
    const rows = collectOciRows();
    const purchasePrice = roundMoney(numericInput(elements.ociPurchasePrice));
    const salePrice = roundMoney(numericInput(elements.ociSalePrice));
    const costTotal = roundMoney(numericInput(elements.ociPurchaseTotal));
    const saleTotal = roundMoney(numericInput(elements.ociSaleTotal));
    const profit = roundMoney(numericInput(elements.ociMarginTotal));
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
        family: row.family,
        quantity: 0,
        surface: 0,
        unit: row.unit,
        thickness: 0,
        volume: 0,
        unit_cost: 0,
        cost_total: 0,
        unit_price: roundMoney(row.purchase_price),
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
        u_formula: row.formula,
        coefficient: Number(row.coefficient || 0),
        consumption: Number(row.consumption || 0),
        _parent_bistamp: line.bistamp
      });
    });
    state.detail.lines.forEach((candidate) => {
      candidate.discount_2 = prorata;
      if (candidate.variant || candidate.option || isPlusValue(candidate.reference)) return;
      candidate.total = roundMoney(Number(candidate.unit_price || 0) * Number(candidate.quantity || 0) * (1 - prorata / 100));
      candidate.profit = roundMoney(Number(candidate.total || 0) - Number(candidate.cost_total || 0));
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
    elements.duplicateBudget.disabled = busy || !state.detail || !selectedBudgetStamp() || !elements.company.value;
    elements.finalPriceBudget.disabled = busy || !state.detail || !selectedBudgetStamp() || !elements.company.value || !budgetCanBeEdited();
    elements.discountBudget.disabled = busy || !state.detail || !selectedBudgetStamp() || !elements.company.value || !budgetCanBeEdited();
    elements.applyVatBudget.disabled = busy || !state.detail || !selectedBudgetStamp() || !elements.company.value || !budgetCanBeEdited() || !availableVatRates().length;
    elements.approvalBudget.disabled = navigationLocked || !state.detail || !selectedBudgetStamp() || !elements.company.value || !budgetApprovalAvailable();
    elements.convertExecution.disabled = navigationLocked || !state.detail || !selectedBudgetStamp() || !elements.company.value || !budgetConversionAvailable();
    elements.assignWork.disabled = navigationLocked || !state.detail || !selectedBudgetStamp() || !elements.company.value || state.detail.header.closed || state.detail.header.cancelled;
    elements.actionsMenu.hidden = editing;
    elements.actionsToggle.disabled = busy || !state.detail || !selectedBudgetStamp() || !elements.company.value;
    elements.newBudget.hidden = editing;
    elements.newBudget.disabled = busy || !elements.company.value || !elements.series.value;
    elements.editBudget.hidden = editing || !budgetCanBeEdited() || !selectedBudgetStamp();
    elements.editBudget.disabled = busy || !state.detail;
    elements.cancelEdit.hidden = !editing;
    elements.cancelEdit.disabled = busy;
    elements.saveBudget.hidden = !editing;
    elements.saveBudget.disabled = busy || !state.detail;
    elements.addLine.disabled = busy || !state.detail || !budgetCanBeEdited();

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
    draftOption.textContent = tr('gr_budgets.document.new_draft', { series: seriesName });
    draftOption.dataset.draft = 'true';
    elements.document.appendChild(draftOption);
    elements.document.value = newDocumentValue;
    elements.resultCount.textContent = tr('gr_budgets.document.new_label');

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

  function startDuplicateBudget() {
    if (isEditing() || state.loadingCount || !state.detail || !selectedBudgetStamp()) return;
    window.clearTimeout(state.searchTimer);
    state.requestVersion += 1;
    const sourceDetail = cloneData(state.detail);
    const sourceHeader = sourceDetail.header || {};
    const sourceStamp = selectedBudgetStamp();
    const sourceNumber = sourceHeader.number || '';
    const seriesName = sourceHeader.series || tr('gr_budgets.label.budget');

    state.returnStamp = sourceStamp;
    state.mode = 'new';
    state.ociCache.clear();

    const draftOption = document.createElement('option');
    draftOption.value = newDocumentValue;
    draftOption.textContent = tr('gr_budgets.document.duplicate_draft', {
      series: seriesName,
      number: sourceNumber || '—'
    });
    draftOption.dataset.draft = 'true';
    elements.document.appendChild(draftOption);
    elements.document.value = newDocumentValue;
    elements.resultCount.textContent = tr('gr_budgets.document.duplicate_label');

    state.detail = {
      ...sourceDetail,
      header: {
        ...sourceHeader,
        _draft: true,
        _duplicated: true,
        bostamp: '',
        number: '',
        revision: '',
        date: todayForInput(),
        approved: false,
        awarded: false,
        cancelled: false,
        closed: false
      },
      lines: cloneBudgetLinesForDraft(sourceDetail.lines || []),
      vat_rows: []
    };
    recalculateBudgetDraftTotals();
    renderDetail(state.detail);
    updateInteractionState();
  }

  function startEditBudget() {
    if (isEditing() || state.loadingCount || !selectedBudgetStamp() || !budgetCanBeEdited()) return;
    state.returnStamp = selectedBudgetStamp();
    state.mode = 'edit';
    syncEditableHeaderToState();
    renderLines(
      state.detail.lines || [],
      (state.detail.header && state.detail.header.currency) || 'EUR',
      state.detail.totals || {}
    );
    renderStatuses(state.detail.header || {});
    updateInteractionState();
    elements.clientSearch.focus();
  }

  function budgetWritePayload() {
    const currentHeader = (state.detail && state.detail.header) || {};
    const lines = ((state.detail && state.detail.lines) || []).map((line) => {
      const technicalRows = Array.isArray(line._ociRows)
        ? line._ociRows
        : (Array.isArray(line.technical_lines) ? line.technical_lines : []);
      return { ...line, technical_lines: technicalRows };
    });
    return {
      feid: elements.company.value,
      bostamp: currentHeader._draft ? '' : (currentHeader.bostamp || selectedBudgetStamp()),
      ndos: Number(elements.series.value || currentHeader.ndos || 0),
      header: {
        bostamp: currentHeader.bostamp || '',
        revision: currentHeader.revision || '',
        client_number: Number(elements.clientNumber.value || 0),
        establishment: Number(elements.clientEstablishment.value || 0),
        work_name: elements.workInput.value.trim(),
        locality: elements.localityInput.value.trim(),
        date: elements.dateInput.value,
        salesperson_number: Number(elements.salesperson.value || 0),
        attention: elements.attentionInput.value.trim(),
        currency: currentHeader.currency || 'EUR',
        process: currentHeader.process || '',
        area: currentHeader.area || '',
        cost_center: currentHeader.cost_center || ''
      },
      lines
    };
  }

  async function saveBudget() {
    if (!isEditing() || state.loadingCount || !state.detail) return;
    if (!Number(elements.clientNumber.value || 0)) {
      showError(tr('gr_budgets.error.client_required'));
      elements.clientSearch.focus();
      return;
    }
    if (!elements.dateInput.value) {
      showError(tr('gr_budgets.error.date_required'));
      elements.dateInput.focus();
      return;
    }
    showLoading(true);
    showError('');
    try {
      const saved = await postJson('/orcamento', budgetWritePayload());
      state.mode = 'view';
      state.returnStamp = '';
      state.ociCache.clear();
      elements.document.querySelectorAll('[data-draft="true"]').forEach((option) => option.remove());
      if (saved.year) elements.year.value = String(saved.year);
      updateInteractionState();
      await loadBudgets(saved.bostamp);
    } catch (error) {
      showError(error.message);
    } finally {
      showLoading(false);
    }
  }

  function cancelEdit() {
    if (!isEditing()) return;
    const returnStamp = state.returnStamp;
    state.mode = 'view';
    state.returnStamp = '';
    state.ociCache.clear();
    closeClientLookup();
    elements.document.querySelectorAll('[data-draft="true"]').forEach((option) => option.remove());
    elements.resultCount.textContent = plural('gr_budgets.count.budget_one', 'gr_budgets.count.budget_other', state.budgets.length);
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
  elements.approvalBudget.addEventListener('click', openApprovalConfirm);
  elements.convertExecution.addEventListener('click', openBudgetConversion);
  elements.printBudget.addEventListener('click', printBudget);
  elements.duplicateBudget.addEventListener('click', startDuplicateBudget);
  elements.finalPriceBudget.addEventListener('click', () => openCommercialAdjustment('final'));
  elements.discountBudget.addEventListener('click', () => openCommercialAdjustment('discount'));
  elements.applyVatBudget.addEventListener('click', openVatApply);
  elements.newBudget.addEventListener('click', startNewBudget);
  elements.editBudget.addEventListener('click', startEditBudget);
  elements.cancelEdit.addEventListener('click', cancelEdit);
  elements.saveBudget.addEventListener('click', saveBudget);
  elements.clientSearch.addEventListener('input', () => {
    if (!isEditing()) return;
    setInputValue(elements.clientNumber, '');
    setInputValue(elements.clientEstablishment, '');
    elements.clientMeta.textContent = elements.clientSearch.value.trim()
      ? tr('gr_budgets.client.select_from_list')
      : tr('gr_budgets.client.meta_unselected');
    syncEditableHeaderToState();
    scheduleClientSearch();
  });
  [elements.workInput, elements.localityInput, elements.dateInput, elements.attentionInput]
    .forEach((input) => input.addEventListener('input', syncEditableHeaderToState));
  elements.salesperson.addEventListener('change', syncEditableHeaderToState);
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
  elements.lines.addEventListener('change', (event) => {
    const selector = event.target.closest('[data-budget-line-vat]');
    if (!selector || !isEditing() || !state.detail) return;
    const index = Number(selector.dataset.budgetLineVat);
    const line = (state.detail.lines || [])[index];
    if (!line) return;
    const vatTable = Number(selector.value || 0);
    line.vat_table = vatTable;
    line.vat_rate = vatRateForTable(vatTable, 0);
  });
  elements.lines.addEventListener('click', (event) => {
    const editButton = event.target.closest('[data-edit-line]');
    if (editButton && state.detail && budgetCanBeEdited()) {
      const lineIndex = Number(editButton.dataset.editLine);
      if (!isEditing()) startEditBudget();
      if (isEditing()) openOci(lineIndex, false);
      return;
    }
    const technicalButton = event.target.closest('[data-technical-line]');
    if (technicalButton && state.detail) {
      openOci(Number(technicalButton.dataset.technicalLine), false);
      return;
    }
    const duplicateButton = event.target.closest('[data-duplicate-line]');
    if (duplicateButton) {
      requestGridPositionDuplicate(Number(duplicateButton.dataset.duplicateLine));
      return;
    }
    const deleteButton = event.target.closest('[data-delete-line]');
    if (deleteButton) {
      requestBudgetLineDelete(Number(deleteButton.dataset.deleteLine));
    }
  });
  elements.addLine.addEventListener('click', () => openOci(-1, true));
  elements.ociDuplicate.addEventListener('click', requestPositionDuplicate);
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
  root.querySelectorAll('[data-position-duplicate-cancel]').forEach((button) => {
    button.addEventListener('click', closePositionDuplicateConfirm);
  });
  elements.positionDuplicateConfirm.addEventListener('click', (event) => {
    if (event.target === elements.positionDuplicateConfirm) closePositionDuplicateConfirm();
  });
  elements.positionDuplicateSave.addEventListener('click', confirmPositionDuplicate);
  root.querySelectorAll('[data-commercial-adjustment-cancel]').forEach((button) => {
    button.addEventListener('click', closeCommercialAdjustment);
  });
  elements.commercialAdjustment.addEventListener('click', (event) => {
    if (event.target === elements.commercialAdjustment) closeCommercialAdjustment();
  });
  elements.commercialAdjustmentApply.addEventListener('click', applyCommercialAdjustment);
  elements.commercialAdjustmentValue.addEventListener('keydown', (event) => {
    if (event.key !== 'Enter') return;
    event.preventDefault();
    applyCommercialAdjustment();
  });
  root.querySelectorAll('[data-approval-cancel]').forEach((button) => {
    button.addEventListener('click', closeApprovalConfirm);
  });
  elements.approvalConfirm.addEventListener('click', (event) => {
    if (event.target === elements.approvalConfirm) closeApprovalConfirm();
  });
  elements.approvalApply.addEventListener('click', applyBudgetApproval);
  root.querySelectorAll('[data-convert-execution-cancel]').forEach((button) => {
    button.addEventListener('click', closeBudgetConversion);
  });
  elements.convertExecutionConfirm.addEventListener('click', (event) => {
    if (event.target === elements.convertExecutionConfirm) closeBudgetConversion();
  });
  root.querySelectorAll('input[name="budgetConvertTarget"]').forEach((input) => {
    input.addEventListener('change', updateConvertTarget);
  });
  elements.convertWorkSearch.addEventListener('input', scheduleConvertWorkSearch);
  elements.convertWorkSearch.addEventListener('blur', () => window.setTimeout(closeConvertWorkLookup, 150));
  elements.convertExecutionApply.addEventListener('click', applyBudgetConversion);
  elements.assignWork.addEventListener('click', openAssignWork);
  root.querySelectorAll('[data-assign-work-cancel]').forEach((button) => {
    button.addEventListener('click', closeAssignWork);
  });
  elements.assignWorkConfirm.addEventListener('click', (event) => {
    if (event.target === elements.assignWorkConfirm) closeAssignWork();
  });
  elements.assignWorkSearch.addEventListener('input', scheduleAssignWorkSearch);
  elements.assignWorkSearch.addEventListener('blur', () => window.setTimeout(closeAssignWorkLookup, 150));
  elements.assignWorkApply.addEventListener('click', applyAssignWork);
  root.querySelectorAll('[data-line-delete-cancel]').forEach((button) => {
    button.addEventListener('click', closeLineDeleteConfirm);
  });
  elements.lineDeleteConfirm.addEventListener('click', (event) => {
    if (event.target === elements.lineDeleteConfirm) closeLineDeleteConfirm();
  });
  elements.lineDeleteApply.addEventListener('click', confirmBudgetLineDelete);
  root.querySelectorAll('[data-vat-apply-cancel]').forEach((button) => {
    button.addEventListener('click', closeVatApply);
  });
  elements.vatApply.addEventListener('click', (event) => {
    if (event.target === elements.vatApply) closeVatApply();
  });
  elements.vatApplyConfirm.addEventListener('click', applyVatToAllLines);
  elements.ociRows.addEventListener('click', (event) => {
    const button = event.target.closest('[data-oci-delete]');
    if (!button) return;
    button.closest('tr').remove();
    const count = elements.ociRows.querySelectorAll('tr').length;
    text('budgetOciRowCount', plural('gr_budgets.count.oci_line_one', 'gr_budgets.count.oci_line_other', count));
    recalculateOci();
    renderOciFamilySidebar();
  });
  elements.ociRows.addEventListener('input', (event) => {
    const row = event.target.closest('tr');
    if (!row) return;
    if (event.target.matches('[data-oci-numeric]')) ociNumericInput(event.target);
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
    if (event.target.matches('[data-oci-field="purchase_price"], [data-oci-field="forfait"]')) {
      setNumericInput(event.target, ociNumericInput(event.target), 2);
    }
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
  elements.ociSalePrice.addEventListener('change', () => {
    setNumericInput(elements.ociSalePrice, numericInput(elements.ociSalePrice), 2);
    recalculateOci();
  });
  elements.ociMarginPercent.addEventListener('input', () => {
    state.ociPriceLocked = false;
    state.ociTargetMargin = numericInput(elements.ociMarginPercent);
    recalculateOci({ preserveMarginInput: true });
  });
  elements.ociMarginPercent.addEventListener('change', () => {
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
    // A new position always starts in square metres. Changing the ouvrage
    // must not silently replace a unit that the user has already selected.
    populateLineUnitOptions(elements.ociUnit.value || 'M²');
    if (!numericInput(elements.ociSalePrice) && ouvrage.sale_price) {
      setNumericInput(elements.ociSalePrice, ouvrage.sale_price, 2);
    }
    recalculateOci();
    renderOciFamilySidebar();
  });
  document.addEventListener('keydown', (event) => {
    if (event.key !== 'Escape') return;
    if (elements.vatApply.classList.contains('sz_is_open')) {
      closeVatApply();
    } else if (elements.lineDeleteConfirm.classList.contains('sz_is_open')) {
      closeLineDeleteConfirm();
    } else if (elements.assignWorkConfirm.classList.contains('sz_is_open')) {
      closeAssignWork();
    } else if (elements.convertExecutionConfirm.classList.contains('sz_is_open')) {
      closeBudgetConversion();
    } else if (elements.approvalConfirm.classList.contains('sz_is_open')) {
      closeApprovalConfirm();
    } else if (elements.commercialAdjustment.classList.contains('sz_is_open')) {
      closeCommercialAdjustment();
    } else if (elements.positionDuplicateConfirm.classList.contains('sz_is_open')) {
      closePositionDuplicateConfirm();
    } else if (elements.positionSwitchConfirm.classList.contains('sz_is_open')) {
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
