(function () {
  const state = {
    companies: [],
    contracts: [],
    detail: null,
    autosModal: null,
    activeView: 'contracts',
  };

  const els = {};

  function byId(id) {
    return document.getElementById(id);
  }

  function initEls() {
    [
      'submeasureCompany',
      'submeasureDateStart',
      'submeasureDateEnd',
      'submeasureCostCenter',
      'submeasureSupplier',
      'submeasureOnlyOpen',
      'submeasureRefreshBtn',
      'submeasureContractsBody',
      'submeasureContractsView',
      'submeasureMeasurementView',
      'submeasureContractsTab',
      'submeasureMeasurementTab',
      'submeasureMetricContracts',
      'submeasureMetricContracted',
      'submeasureMetricExecuted',
      'submeasureMetricRemaining',
      'submeasureBackBtn',
      'submeasureFillRemainingBtn',
      'submeasureClearLinesBtn',
      'submeasureCancelBtn',
      'submeasureDraftBtn',
      'submeasureSelectedTitle',
      'submeasureSelectedMeta',
      'submeasureDetailContracted',
      'submeasureDetailExecuted',
      'submeasureDetailRemaining',
      'submeasureDetailDraft',
      'submeasureLinesBody',
      'submeasureAutosModal',
      'submeasureAutosModalClose',
      'submeasureAutosModalTitle',
      'submeasureAutosModalMeta',
      'submeasureAutosList',
      'submeasureSelectedAutoTitle',
      'submeasureSelectedAutoMeta',
      'submeasureOpenAutoAttachmentBtn',
      'submeasureAutosLinesBody',
    ].forEach((id) => {
      els[id] = byId(id);
    });
  }

  function escapeHtml(value) {
    return String(value ?? '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function formatPtNumber(value, decimals, useGrouping = true) {
    const num = Number(value || 0);
    if (!Number.isFinite(num)) return '';
    const fixed = Math.abs(num).toFixed(decimals);
    const [integerPart, decimalPart] = fixed.split('.');
    const groupedInteger = useGrouping
      ? integerPart.replace(/\B(?=(\d{3})+(?!\d))/g, ' ')
      : integerPart;
    return `${num < 0 ? '-' : ''}${groupedInteger}${decimals ? `,${decimalPart}` : ''}`;
  }

  function formatMoney(value) {
    return formatPtNumber(value, 2, true);
  }

  function selectedCompany() {
    const feid = String(selectedFeid() || '');
    return state.companies.find((company) => String(company.feid || '') === feid) || null;
  }

  function currentCurrency(fallback = 'EUR') {
    return String(
      state.detail?.contract?.currency
      || selectedCompany()?.currency
      || fallback
      || 'EUR'
    ).trim().toUpperCase() || 'EUR';
  }

  function formatTotalMoney(value, currency) {
    const suffix = String(currency || currentCurrency()).trim().toUpperCase() || 'EUR';
    return `${formatMoney(value)} ${suffix}`;
  }

  function formatQty(value) {
    return formatPtNumber(value, 2, true);
  }

  function formatPercent(value) {
    return formatPtNumber(value, 2, true) + '%';
  }

  function parseNumber(value) {
    let raw = String(value ?? '').trim().replace(/\s/g, '');
    if (!raw) return 0;
    if (raw.includes(',')) {
      raw = raw.replace(/\./g, '').replace(',', '.');
    }
    const num = Number(raw);
    return Number.isFinite(num) ? num : 0;
  }

  function formatInputNumber(value, decimals) {
    const num = Number(value || 0);
    if (!Number.isFinite(num)) return '';
    return formatPtNumber(num, decimals, false);
  }

  function setLoading(message, colSpan) {
    els.submeasureContractsBody.innerHTML = `<tr><td colspan="${colSpan}" class="sz_table_cell sz_text_muted">${escapeHtml(message)}</td></tr>`;
  }

  function showView(view) {
    state.activeView = view;
    const isMeasurement = view === 'measurement';
    els.submeasureContractsView.classList.toggle('is-active', !isMeasurement);
    els.submeasureMeasurementView.classList.toggle('is-active', isMeasurement);
    els.submeasureContractsTab.classList.toggle('is-active', !isMeasurement);
    els.submeasureMeasurementTab.classList.toggle('is-active', isMeasurement);
  }

  async function fetchJson(url) {
    const response = await fetch(url, { headers: { Accept: 'application/json' } });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok || payload.ok === false) {
      throw new Error(payload.error || 'Erro ao consultar dados.');
    }
    return payload;
  }

  async function postJson(url, body) {
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        Accept: 'application/json',
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body || {}),
    });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok || payload.ok === false) {
      throw new Error(payload.error || 'Erro ao gravar dados.');
    }
    return payload;
  }

  function selectedFeid() {
    return els.submeasureCompany.value || '';
  }

  function buildContractsUrl() {
    const params = new URLSearchParams();
    params.set('feid', selectedFeid());
    if (els.submeasureDateStart.value) params.set('data_inicio', els.submeasureDateStart.value);
    if (els.submeasureDateEnd.value) params.set('data_fim', els.submeasureDateEnd.value);
    if (els.submeasureCostCenter.value.trim()) params.set('ccusto', els.submeasureCostCenter.value.trim());
    if (els.submeasureSupplier.value.trim()) params.set('fornecedor', els.submeasureSupplier.value.trim());
    params.set('only_open', els.submeasureOnlyOpen.checked ? '1' : '0');
    return `/api/gr_autos_subempreitada/contratos?${params.toString()}`;
  }

  async function loadCompanies() {
    const payload = await fetchJson('/api/gr_autos_subempreitada/empresas');
    state.companies = payload.rows || [];
    if (!state.companies.length) {
      els.submeasureCompany.innerHTML = '<option value="">Sem empresas PHC</option>';
      throw new Error('Sem empresas PHC disponíveis para o utilizador.');
    }
    els.submeasureCompany.innerHTML = state.companies.map((company) => (
      `<option value="${escapeHtml(company.feid)}">${escapeHtml(company.name)} · ${escapeHtml(company.phc_db)}</option>`
    )).join('');
  }

  function updateContractMetrics() {
    const totals = state.contracts.reduce((acc, row) => {
      acc.contracted += Number(row.contract_value || 0);
      acc.executed += Number(row.executed_value || 0);
      acc.remaining += Number(row.remaining_value || 0);
      return acc;
    }, { contracted: 0, executed: 0, remaining: 0 });
    els.submeasureMetricContracts.textContent = String(state.contracts.length);
    els.submeasureMetricContracted.textContent = formatTotalMoney(totals.contracted);
    els.submeasureMetricExecuted.textContent = formatTotalMoney(totals.executed);
    els.submeasureMetricRemaining.textContent = formatTotalMoney(totals.remaining);
  }

  function renderContracts() {
    updateContractMetrics();
    if (!state.contracts.length) {
      els.submeasureContractsBody.innerHTML = '<tr><td colspan="10" class="sz_table_cell sz_text_muted">Sem contratos para os filtros selecionados.</td></tr>';
      return;
    }
    els.submeasureContractsBody.innerHTML = state.contracts.map((row) => {
      const remainingClass = Number(row.remaining_value || 0) < 0 ? ' gr-submeasure-negative' : '';
      return `
        <tr data-bostamp="${escapeHtml(row.bostamp)}">
          <td>
            <div class="gr-submeasure-status">
              <span class="gr-submeasure-doc">${escapeHtml(row.doc_name || 'Contrato')} nº ${escapeHtml(row.number)}</span>
              <span class="gr-submeasure-muted">${escapeHtml(row.year)}</span>
            </div>
          </td>
          <td>${escapeHtml(row.date || '')}</td>
          <td>${escapeHtml(row.cost_center || row.process || '')}</td>
          <td>
            <div class="gr-submeasure-status">
              <span>${escapeHtml(row.supplier_name || '')}</span>
              <span class="gr-submeasure-muted">${escapeHtml(row.supplier_no || '')}</span>
            </div>
          </td>
          <td class="sz_text_right">${escapeHtml(formatMoney(row.contract_value))}</td>
          <td class="sz_text_right">${escapeHtml(formatMoney(row.executed_value))}</td>
          <td class="sz_text_right${remainingClass}">${escapeHtml(formatMoney(row.remaining_value))}</td>
          <td class="sz_text_right">${escapeHtml(formatPercent(row.progress))}</td>
          <td class="sz_text_right">
            <button type="button" class="sz_button sz_button_secondary gr-submeasure-count-button" data-open-autos="${escapeHtml(row.bostamp)}" ${Number(row.auto_count || 0) > 0 ? '' : 'disabled'}>
              ${escapeHtml(row.auto_count || 0)}
            </button>
          </td>
          <td class="sz_text_right">
            <button type="button" class="sz_button sz_button_primary" data-open-contract="${escapeHtml(row.bostamp)}">
              <i class="fa-solid fa-ruler-combined"></i>
              <span>Medir</span>
            </button>
          </td>
        </tr>
      `;
    }).join('');
  }

  async function loadContracts() {
    if (!selectedFeid()) return;
    setLoading('A carregar contratos...', 10);
    try {
      const payload = await fetchJson(buildContractsUrl());
      state.contracts = payload.rows || [];
      renderContracts();
    } catch (error) {
      state.contracts = [];
      updateContractMetrics();
      els.submeasureContractsBody.innerHTML = `<tr><td colspan="10" class="sz_table_cell sz_text_muted">${escapeHtml(error.message || 'Erro ao carregar contratos.')}</td></tr>`;
    }
  }

  function buildAutosUrl(bostamp) {
    const params = new URLSearchParams({ feid: selectedFeid(), bostamp });
    return `/api/gr_autos_subempreitada/autos?${params.toString()}`;
  }

  function buildAutoAttachmentUrl(attachment) {
    const stamp = String(attachment?.stamp || '').trim();
    if (!stamp) return '';
    const params = new URLSearchParams({ feid: selectedFeid(), anexosstamp: stamp });
    return `/api/gr_autos_subempreitada/anexo?${params.toString()}`;
  }

  function renderAutosList(activeBostamp = '') {
    const autos = state.autosModal?.autos || [];
    if (!autos.length) {
      els.submeasureAutosList.innerHTML = '<div class="gr-submeasure-empty">Sem autos.</div>';
      return;
    }
    const active = activeBostamp || autos[0].bostamp;
    els.submeasureAutosList.innerHTML = autos.map((auto) => {
      const isActive = String(auto.bostamp || '') === String(active || '');
      return `
        <button type="button" class="gr-submeasure-auto-item${isActive ? ' is-active' : ''}" data-select-auto="${escapeHtml(auto.bostamp)}">
          <strong>${escapeHtml(auto.doc_name || 'Auto')} nº ${escapeHtml(auto.number)} / ${escapeHtml(auto.year)}</strong>
          <span>${escapeHtml(auto.date || '')} · ${escapeHtml(formatTotalMoney(auto.value, auto.currency))}</span>
          <span>Auto contrato nº ${escapeHtml(auto.contract_auto_number || 0)} · ${escapeHtml(auto.closed ? 'Fechado' : 'Aberto')}${auto.attachment?.stamp ? ' · Anexo' : ''}</span>
        </button>
      `;
    }).join('');
  }

  function syncAutoAttachmentButton(auto) {
    const attachment = auto?.attachment || null;
    const url = buildAutoAttachmentUrl(attachment);
    if (!url) {
      els.submeasureOpenAutoAttachmentBtn.hidden = true;
      els.submeasureOpenAutoAttachmentBtn.removeAttribute('href');
      els.submeasureOpenAutoAttachmentBtn.removeAttribute('title');
      return;
    }
    els.submeasureOpenAutoAttachmentBtn.hidden = false;
    els.submeasureOpenAutoAttachmentBtn.href = url;
    els.submeasureOpenAutoAttachmentBtn.title = attachment.name || 'Abrir anexo';
  }

  function renderAutoLines(auto) {
    if (!auto) {
      els.submeasureSelectedAutoTitle.textContent = 'Auto';
      els.submeasureSelectedAutoMeta.textContent = '';
      syncAutoAttachmentButton(null);
      els.submeasureAutosLinesBody.innerHTML = '<tr><td colspan="7" class="sz_table_cell sz_text_muted">Sem auto selecionado.</td></tr>';
      return;
    }
    els.submeasureSelectedAutoTitle.textContent = `${auto.doc_name || 'Auto'} nº ${auto.number} / ${auto.year}`;
    els.submeasureSelectedAutoMeta.textContent = `${auto.date || ''} · ${formatTotalMoney(auto.value, auto.currency)} · ${auto.closed ? 'Fechado' : 'Aberto'}`;
    syncAutoAttachmentButton(auto);
    const lines = auto.lines || [];
    if (!lines.length) {
      els.submeasureAutosLinesBody.innerHTML = '<tr><td colspan="7" class="sz_table_cell sz_text_muted">Auto sem linhas.</td></tr>';
      return;
    }
    els.submeasureAutosLinesBody.innerHTML = lines.map((line) => `
      <tr>
        <td>${escapeHtml(line.ref || '')}</td>
        <td>${escapeHtml(line.design || '')}</td>
        <td>${escapeHtml(line.unit || '')}</td>
        <td class="sz_text_right">${escapeHtml(formatQty(line.qty))}</td>
        <td class="sz_text_right">${escapeHtml(formatMoney(line.unit_price))}</td>
        <td class="sz_text_right">${escapeHtml(formatMoney(line.value))}</td>
        <td class="sz_text_right">${escapeHtml(formatPercent(line.percent))}</td>
      </tr>
    `).join('');
  }

  function selectAuto(autoBostamp) {
    const autos = state.autosModal?.autos || [];
    const auto = autos.find((row) => String(row.bostamp || '') === String(autoBostamp || '')) || autos[0] || null;
    renderAutosList(auto?.bostamp || '');
    renderAutoLines(auto);
  }

  function closeAutosModal() {
    els.submeasureAutosModal.hidden = true;
    state.autosModal = null;
  }

  async function openAutosModal(contractBostamp) {
    els.submeasureAutosModal.hidden = false;
    els.submeasureAutosModalTitle.textContent = 'Autos do contrato';
    els.submeasureAutosModalMeta.textContent = 'A carregar...';
    els.submeasureAutosList.innerHTML = '<div class="gr-submeasure-empty">A carregar...</div>';
    renderAutoLines(null);
    try {
      const payload = await fetchJson(buildAutosUrl(contractBostamp));
      state.autosModal = payload;
      const contract = payload.contract || {};
      els.submeasureAutosModalTitle.textContent = `${contract.doc_name || 'Contrato'} nº ${contract.number || ''} / ${contract.year || ''}`;
      els.submeasureAutosModalMeta.textContent = `${contract.supplier_name || ''} · ${contract.cost_center || ''} · ${payload.company?.name || payload.company?.phc_db || ''}`;
      selectAuto((payload.autos || [])[0]?.bostamp || '');
    } catch (error) {
      state.autosModal = { autos: [] };
      els.submeasureAutosModalMeta.textContent = error.message || 'Erro ao carregar autos.';
      els.submeasureAutosList.innerHTML = `<div class="gr-submeasure-empty">${escapeHtml(error.message || 'Erro ao carregar autos.')}</div>`;
      renderAutoLines(null);
    }
  }

  function lineDraftValue(line) {
    return parseNumber(line.draftValue);
  }

  function updateDraftTotals() {
    if (!state.detail) return;
    const total = state.detail.lines.reduce((acc, line) => acc + lineDraftValue(line), 0);
    els.submeasureDetailDraft.textContent = formatTotalMoney(total);
    els.submeasureDraftBtn.disabled = total <= 0;
  }

  function resetLineDraft(line) {
    line.draftQty = 0;
    line.draftValue = 0;
    line.draftPercent = 0;
  }

  function capValue(value, maxValue) {
    const parsed = Math.max(0, Number(value || 0));
    const max = Number(maxValue || 0);
    return max > 0 ? Math.min(parsed, max) : parsed;
  }

  function valueFromQty(line, qty, unitPrice) {
    const contractQty = Number(line.qty || 0);
    const contractValue = Number(line.value || 0);
    if (unitPrice) return qty * unitPrice;
    return contractQty ? contractValue * qty / contractQty : 0;
  }

  function percentFromQty(line, qty) {
    const contractQty = Number(line.qty || 0);
    if (!contractQty) return 0;
    return qty / contractQty * 100;
  }

  function maxPendingPercent(line) {
    const contractQty = Number(line.qty || 0);
    const remainingQty = Math.max(0, Number(line.remaining_qty || 0));
    const contractValue = Number(line.value || 0);
    const remainingValue = Math.max(0, Number(line.remaining_value || 0));
    if (contractQty) return remainingQty / contractQty * 100;
    if (contractValue) return remainingValue / contractValue * 100;
    return 0;
  }

  function setLineDraft(line, source, value) {
    const contractQty = Number(line.qty || 0);
    const contractValue = Number(line.value || 0);
    const unitPrice = contractQty ? contractValue / contractQty : Number(line.unit_price || 0);
    const remainingQty = Math.max(0, Number(line.remaining_qty || 0));
    const remainingValue = Math.max(0, Number(line.remaining_value || 0));
    let qty = 0;
    let amount = 0;
    let percent = 0;

    if (source === 'qty') {
      qty = capValue(value, remainingQty);
    } else if (source === 'value') {
      amount = capValue(value, remainingValue);
      qty = unitPrice ? amount / unitPrice : (contractValue && contractQty ? contractQty * amount / contractValue : 0);
      qty = capValue(qty, remainingQty);
    } else if (source === 'percent') {
      percent = capValue(value, maxPendingPercent(line));
      if (contractQty) {
        qty = contractQty * percent / 100;
      } else if (unitPrice) {
        qty = contractValue * percent / 100 / unitPrice;
      } else {
        amount = capValue(contractValue * percent / 100, remainingValue);
      }
      qty = capValue(qty, remainingQty);
    }

    if (contractQty || unitPrice) {
      amount = capValue(valueFromQty(line, qty, unitPrice), remainingValue);
      if (unitPrice && amount < valueFromQty(line, qty, unitPrice)) {
        qty = capValue(amount / unitPrice, remainingQty);
      }
    } else if (source === 'value') {
      amount = capValue(value, remainingValue);
    }
    percent = contractQty ? percentFromQty(line, qty) : (contractValue ? amount / contractValue * 100 : 0);

    line.draftQty = qty;
    line.draftValue = amount;
    line.draftPercent = percent;
  }

  function lineFieldValue(line, field) {
    if (field === 'qty') return Number(line.draftQty || 0);
    if (field === 'value') return Number(line.draftValue || 0);
    if (field === 'percent') return Number(line.draftPercent || 0);
    return 0;
  }

  function lineFieldDecimals(field) {
    if (field === 'qty') return 2;
    if (field === 'value') return 2;
    if (field === 'percent') return 2;
    return 2;
  }

  function syncLineInputs(tr, line, activeField = '') {
    const rowInputs = tr.querySelectorAll('.gr-submeasure-input');
    rowInputs.forEach((rowInput) => {
      const field = rowInput.dataset.field;
      if (field === activeField) return;
      rowInput.value = formatInputNumber(lineFieldValue(line, field), lineFieldDecimals(field));
    });
  }

  function syncActiveInputIfCapped(input, line) {
    const field = input.dataset.field;
    const current = parseNumber(input.value);
    const capped = lineFieldValue(line, field);
    if (current > capped + 0.000001) {
      input.value = formatInputNumber(capped, lineFieldDecimals(field));
    }
  }

  function renderLines() {
    if (!state.detail) {
      els.submeasureLinesBody.innerHTML = '<tr><td colspan="11" class="sz_table_cell sz_text_muted">Escolhe um contrato.</td></tr>';
      return;
    }
    const lines = state.detail.lines || [];
    if (!lines.length) {
      els.submeasureLinesBody.innerHTML = '<tr><td colspan="11" class="sz_table_cell sz_text_muted">Contrato sem linhas.</td></tr>';
      return;
    }
    els.submeasureLinesBody.innerHTML = lines.map((line, index) => {
      const disabled = !line.measurable || Number(line.remaining_value || 0) <= 0;
      return `
        <tr data-line-index="${index}">
          <td>${escapeHtml(line.ref || '')}</td>
          <td>
            <div class="gr-submeasure-status">
              <span>${escapeHtml(line.design || '')}</span>
            </div>
          </td>
          <td class="gr-submeasure-unit-col">${escapeHtml(line.unit || '')}</td>
          <td class="sz_text_right">${escapeHtml(formatQty(line.qty))}</td>
          <td class="sz_text_right">${escapeHtml(formatQty(line.executed_qty))}</td>
          <td class="sz_text_right">${escapeHtml(formatQty(line.remaining_qty))}</td>
          <td class="sz_text_right">${escapeHtml(formatMoney(line.unit_price))}</td>
          <td class="sz_text_right">${escapeHtml(formatMoney(line.remaining_value))}</td>
          <td class="sz_text_right"><input class="gr-submeasure-input" data-field="qty" type="text" inputmode="decimal" ${disabled ? 'disabled' : ''} value="${escapeHtml(formatInputNumber(line.draftQty, 4))}"></td>
          <td class="sz_text_right"><input class="gr-submeasure-input" data-field="value" type="text" inputmode="decimal" ${disabled ? 'disabled' : ''} value="${escapeHtml(formatInputNumber(line.draftValue, 2))}"></td>
          <td class="sz_text_right"><input class="gr-submeasure-input" data-field="percent" type="text" inputmode="decimal" ${disabled ? 'disabled' : ''} value="${escapeHtml(formatInputNumber(line.draftPercent, 2))}"></td>
        </tr>
      `;
    }).join('');
    updateDraftTotals();
  }

  function renderDetail() {
    const detail = state.detail;
    const contract = detail.contract;
    els.submeasureSelectedTitle.textContent = `${contract.doc_name || 'Contrato'} nº ${contract.number} · ${contract.cost_center || ''}`;
    els.submeasureSelectedMeta.textContent = `${contract.supplier_name || ''} · ${contract.date || ''} · ${detail.company.name || detail.company.phc_db}`;
    els.submeasureDetailContracted.textContent = formatTotalMoney(contract.contract_value, contract.currency);
    els.submeasureDetailExecuted.textContent = formatTotalMoney(contract.executed_value, contract.currency);
    els.submeasureDetailRemaining.textContent = formatTotalMoney(contract.remaining_value, contract.currency);
    els.submeasureMeasurementTab.disabled = false;
    renderLines();
  }

  async function openContract(bostamp) {
    els.submeasureLinesBody.innerHTML = '<tr><td colspan="11" class="sz_table_cell sz_text_muted">A carregar linhas...</td></tr>';
    showView('measurement');
    const params = new URLSearchParams({ feid: selectedFeid(), bostamp });
    try {
      const payload = await fetchJson(`/api/gr_autos_subempreitada/contrato?${params.toString()}`);
      state.detail = payload;
      state.detail.lines = (state.detail.lines || []).map((line) => ({
        ...line,
        draftQty: 0,
        draftValue: 0,
        draftPercent: 0,
      }));
      renderDetail();
    } catch (error) {
      state.detail = null;
      els.submeasureLinesBody.innerHTML = `<tr><td colspan="11" class="sz_table_cell sz_text_muted">${escapeHtml(error.message || 'Erro ao carregar contrato.')}</td></tr>`;
    }
  }

  function clearDraft() {
    if (!state.detail) return;
    state.detail.lines.forEach((line) => {
      line.draftQty = 0;
      line.draftValue = 0;
      line.draftPercent = 0;
    });
    renderLines();
  }

  function fillRemainingDraft() {
    if (!state.detail) return;
    state.detail.lines.forEach((line) => {
      const remainingQty = Number(line.remaining_qty || 0);
      const remainingValue = Number(line.remaining_value || 0);
      if (!line.measurable || remainingValue <= 0) {
        resetLineDraft(line);
      } else if (remainingQty > 0) {
        setLineDraft(line, 'qty', remainingQty);
      } else {
        setLineDraft(line, 'value', remainingValue);
      }
    });
    renderLines();
  }

  function cancelMeasurement() {
    clearDraft();
    showView('contracts');
  }

  function draftLinesForSave() {
    if (!state.detail) return [];
    return state.detail.lines
      .filter((line) => Number(line.draftQty || 0) > 0 && Number(line.draftValue || 0) > 0)
      .map((line) => ({
        bistamp: line.bistamp,
        qty: Number(line.draftQty || 0),
        value: Number(line.draftValue || 0),
        percent: Number(line.draftPercent || 0),
      }));
  }

  async function saveMeasurement() {
    if (!state.detail || els.submeasureDraftBtn.disabled) return;
    const lines = draftLinesForSave();
    if (!lines.length) {
      window.alert('Indique pelo menos uma linha para gravar.');
      return;
    }
    const total = state.detail.lines.reduce((acc, line) => acc + lineDraftValue(line), 0);
    if (!window.confirm(`Gravar auto no PHC com total de ${formatTotalMoney(total)}?`)) return;

    els.submeasureDraftBtn.disabled = true;
    const previousLabel = els.submeasureDraftBtn.querySelector('span')?.textContent || 'Gravar';
    const label = els.submeasureDraftBtn.querySelector('span');
    if (label) label.textContent = 'A gravar...';
    try {
      const payload = await postJson('/api/gr_autos_subempreitada/autos', {
        feid: selectedFeid(),
        bostamp: state.detail.contract.bostamp,
        data_auto: els.submeasureDateEnd.value,
        lines,
      });
      const auto = payload.auto || {};
      window.alert(`Auto gravado no PHC: ${auto.nmdos || 'Auto'} nº ${auto.obrano || ''}/${auto.boano || ''}.`);
      await openContract(state.detail.contract.bostamp);
      await loadContracts();
    } catch (error) {
      window.alert(error.message || 'Erro ao gravar auto no PHC.');
      updateDraftTotals();
    } finally {
      if (label) label.textContent = previousLabel;
      updateDraftTotals();
    }
  }

  function bindEvents() {
    els.submeasureRefreshBtn.addEventListener('click', loadContracts);
    els.submeasureCompany.addEventListener('change', () => {
      state.detail = null;
      els.submeasureMeasurementTab.disabled = true;
      showView('contracts');
      loadContracts();
    });
    [els.submeasureDateStart, els.submeasureDateEnd, els.submeasureCostCenter, els.submeasureSupplier].forEach((input) => {
      input.addEventListener('keydown', (event) => {
        if (event.key === 'Enter') loadContracts();
      });
    });
    els.submeasureOnlyOpen.addEventListener('change', loadContracts);
    els.submeasureContractsBody.addEventListener('click', (event) => {
      const autosButton = event.target.closest('[data-open-autos]');
      if (autosButton && !autosButton.disabled) {
        openAutosModal(autosButton.dataset.openAutos || '');
        return;
      }
      const button = event.target.closest('[data-open-contract]');
      if (!button) return;
      openContract(button.dataset.openContract || '');
    });
    els.submeasureAutosModalClose.addEventListener('click', closeAutosModal);
    els.submeasureAutosModal.addEventListener('click', (event) => {
      if (event.target.closest('[data-close-autos-modal]')) {
        closeAutosModal();
        return;
      }
      const autoButton = event.target.closest('[data-select-auto]');
      if (autoButton) selectAuto(autoButton.dataset.selectAuto || '');
    });
    document.addEventListener('keydown', (event) => {
      if (event.key === 'Escape' && !els.submeasureAutosModal.hidden) closeAutosModal();
    });
    els.submeasureContractsTab.addEventListener('click', () => showView('contracts'));
    els.submeasureMeasurementTab.addEventListener('click', () => {
      if (!els.submeasureMeasurementTab.disabled) showView('measurement');
    });
    els.submeasureBackBtn.addEventListener('click', () => showView('contracts'));
    els.submeasureFillRemainingBtn.addEventListener('click', fillRemainingDraft);
    els.submeasureClearLinesBtn.addEventListener('click', clearDraft);
    els.submeasureCancelBtn.addEventListener('click', cancelMeasurement);
    els.submeasureDraftBtn.addEventListener('click', saveMeasurement);
    els.submeasureLinesBody.addEventListener('input', (event) => {
      const input = event.target.closest('.gr-submeasure-input');
      if (!input || !state.detail) return;
      const tr = input.closest('tr[data-line-index]');
      const index = Number(tr?.dataset.lineIndex || -1);
      const line = state.detail.lines[index];
      if (!line) return;
      if (!String(input.value || '').trim()) {
        resetLineDraft(line);
      } else {
        setLineDraft(line, input.dataset.field, parseNumber(input.value));
      }
      syncActiveInputIfCapped(input, line);
      syncLineInputs(tr, line, input.dataset.field);
      updateDraftTotals();
    });
    els.submeasureLinesBody.addEventListener('blur', (event) => {
      const input = event.target.closest('.gr-submeasure-input');
      if (!input || !state.detail) return;
      const tr = input.closest('tr[data-line-index]');
      const index = Number(tr?.dataset.lineIndex || -1);
      const line = state.detail.lines[index];
      if (!line) return;
      syncLineInputs(tr, line);
      updateDraftTotals();
    }, true);
  }

  function setDefaultDates() {
    const today = new Date();
    const start = new Date(today.getFullYear(), 0, 1);
    els.submeasureDateStart.value = start.toISOString().slice(0, 10);
    els.submeasureDateEnd.value = today.toISOString().slice(0, 10);
  }

  async function init() {
    initEls();
    bindEvents();
    setDefaultDates();
    try {
      await loadCompanies();
      await loadContracts();
    } catch (error) {
      els.submeasureContractsBody.innerHTML = `<tr><td colspan="10" class="sz_table_cell sz_text_muted">${escapeHtml(error.message || 'Erro ao iniciar ecrã.')}</td></tr>`;
    }
  }

  document.addEventListener('DOMContentLoaded', init);
})();
