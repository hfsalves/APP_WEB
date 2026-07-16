(function () {
  const cfg = window.GR_WORKSHOP || {};
  const state = {
    meta: null,
    items: [],
    lines: [],
    vehicleTimer: null,
    vehicleRows: [],
    vehicleActiveIndex: -1,
    typeTimer: null,
    articleTimer: null,
  };

  const els = {
    search: document.getElementById('workshopSearch'),
    stateFilter: document.getElementById('workshopStateFilter'),
    refreshBtn: document.getElementById('workshopRefreshBtn'),
    newBtn: document.getElementById('workshopNewBtn'),
    typesBtn: document.getElementById('workshopTypesBtn'),
    body: document.getElementById('workshopTableBody'),
    metricTotal: document.getElementById('workshopMetricTotal'),
    metricOpen: document.getElementById('workshopMetricOpen'),
    metricDone: document.getElementById('workshopMetricDone'),
    metricVoid: document.getElementById('workshopMetricVoid'),

    sheetModalEl: document.getElementById('workshopSheetModal'),
    sheetTitle: document.getElementById('workshopSheetTitle'),
    sheetStatus: document.getElementById('workshopSheetStatus'),
    sheetStamp: document.getElementById('workshopSheetStamp'),
    sheetNo: document.getElementById('workshopSheetNo'),
    vehicleStamp: document.getElementById('workshopVehicleStamp'),
    vehicleSearch: document.getElementById('workshopVehicleSearch'),
    vehicleResults: document.getElementById('workshopVehicleResults'),
    typeStamp: document.getElementById('workshopTypeStamp'),
    typeSearch: document.getElementById('workshopTypeSearch'),
    typeResults: document.getElementById('workshopTypeResults'),
    aiSuggestBtn: document.getElementById('workshopAiSuggestBtn'),
    jobText: document.getElementById('workshopJobText'),
    date: document.getElementById('workshopDate'),
    start: document.getElementById('workshopStart'),
    end: document.getElementById('workshopEnd'),
    tempo: document.getElementById('workshopTempo'),
    mechanic: document.getElementById('workshopMechanic'),
    planDate: document.getElementById('workshopPlanDate'),
    planStart: document.getElementById('workshopPlanStart'),
    planEnd: document.getElementById('workshopPlanEnd'),
    sheetState: document.getElementById('workshopState'),
    obs: document.getElementById('workshopObs'),
    linesBody: document.getElementById('workshopLinesBody'),
    addLineBtn: document.getElementById('workshopAddLineBtn'),
    total: document.getElementById('workshopSheetTotal'),
    annulBtn: document.getElementById('workshopAnnulBtn'),
    saveBtn: document.getElementById('workshopSaveBtn'),

    typesModalEl: document.getElementById('workshopTypesModal'),
    typeEditStamp: document.getElementById('workshopTypeEditStamp'),
    typeCode: document.getElementById('workshopTypeCode'),
    typeDescription: document.getElementById('workshopTypeDescription'),
    typeOrder: document.getElementById('workshopTypeOrder'),
    typeActive: document.getElementById('workshopTypeActive'),
    typeSaveBtn: document.getElementById('workshopTypeSaveBtn'),
    typesList: document.getElementById('workshopTypesList'),
  };

  if (!els.body || !els.sheetModalEl) return;

  const sheetModal = new bootstrap.Modal(els.sheetModalEl);
  const typesModal = new bootstrap.Modal(els.typesModalEl);

  const esc = (value) => String(value ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');

  const money = (value) => Number(value || 0).toLocaleString('pt-PT', {
    style: 'currency',
    currency: 'EUR',
  });

  const fmtDate = (value) => {
    if (!value) return '-';
    try {
      if (/^\d{4}-\d{2}-\d{2}$/.test(value)) {
        const [year, month, day] = value.split('-').map(Number);
        return new Intl.DateTimeFormat('pt-PT', { dateStyle: 'short' }).format(new Date(year, month - 1, day));
      }
      return new Intl.DateTimeFormat('pt-PT', {
        dateStyle: 'short',
      }).format(new Date(value));
    } catch (_) {
      return value;
    }
  };

  const todayLocal = () => {
    const d = new Date();
    d.setMinutes(d.getMinutes() - d.getTimezoneOffset());
    return d.toISOString().slice(0, 10);
  };

  const toNum = (value) => {
    const parsed = Number(String(value ?? '').replace(',', '.'));
    return Number.isFinite(parsed) ? parsed : 0;
  };

  async function api(url, options = {}) {
    const response = await fetch(url, {
      headers: {
        Accept: 'application/json',
        ...(options.body ? { 'Content-Type': 'application/json' } : {}),
      },
      ...options,
    });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(payload.error || 'Erro inesperado.');
    return payload;
  }

  function toast(message, type = 'success') {
    if (window.showToast) window.showToast(message, type);
    else window.alert(message);
  }

  function badge(label, tone) {
    return `<span class="sz_badge sz_badge_${esc(tone || 'secondary')}">${esc(label || '-')}</span>`;
  }

  function mechanicDot(item) {
    if (!item.MECANICO) return '<span class="sz_text_muted">-</span>';
    return `
      <span class="gr-workshop-mechanic-pill">
        <span style="background:${esc(item.MECANICO_COR || '#60A5FA')}"></span>
        ${esc(item.MECANICO)}
      </span>
    `;
  }

  function can(action) {
    return !!(state.meta && state.meta.permissions && state.meta.permissions[action]);
  }

  function refreshAiSuggestionButton() {
    if (!els.aiSuggestBtn) return;
    const ready = can('aiSuggestion')
      && !!els.vehicleStamp.value.trim()
      && !!els.typeStamp.value.trim();
    els.aiSuggestBtn.disabled = !ready || els.aiSuggestBtn.classList.contains('is-loading');
  }

  function setSheetStatus(message, tone = 'muted') {
    els.sheetStatus.className = tone === 'danger' ? 'gr-workshop-modal-subtitle text-danger' : 'gr-workshop-modal-subtitle';
    els.sheetStatus.textContent = message || '';
  }

  function renderMechanicOptions() {
    const mechanics = state.meta?.mechanics || [];
    if (!els.mechanic) return;
    els.mechanic.innerHTML = [
      '<option value="">Sem mecânico</option>',
      ...mechanics.map((item) => `<option value="${esc(item.OFICINA_MECSTAMP)}">${esc(item.NOME)}</option>`),
    ].join('');
  }

  function updateMetrics(summary = {}) {
    els.metricTotal.textContent = String(summary.total || 0);
    els.metricOpen.textContent = String(summary.open || 0);
    els.metricDone.textContent = String(summary.done || 0);
    els.metricVoid.textContent = String(summary.void || 0);
  }

  function renderTable() {
    if (!state.items.length) {
      els.body.innerHTML = '<tr><td colspan="9" class="sz_table_cell sz_text_muted">Sem folhas para os filtros atuais.</td></tr>';
      return;
    }
    els.body.innerHTML = state.items.map((item) => `
      <tr class="sz_table_row" data-open="${esc(item.OFICINA_FOLHASTAMP)}">
        <td class="sz_table_cell"><strong>${esc(item.NO || '')}</strong></td>
        <td class="sz_table_cell">
          <div class="gr-workshop-row-title">${esc(item.MATRICULA || '-')}</div>
          <div class="gr-workshop-row-subtitle">${esc(item.VEICULO_LABEL || '')}</div>
        </td>
        <td class="sz_table_cell">
          <div class="gr-workshop-row-title">${esc(item.TRAB_DESCRICAO || item.TRABALHO || '-')}</div>
          <div class="gr-workshop-row-subtitle">${esc(item.TRABALHO || '')}</div>
        </td>
        <td class="sz_table_cell">${esc(fmtDate(item.DATA))} ${esc(item.HORAINI || '')}</td>
        <td class="sz_table_cell">${esc(item.HORAFIM || '-')}</td>
        <td class="sz_table_cell">${mechanicDot(item)}</td>
        <td class="sz_table_cell">${badge(item.ESTADO_LABEL, item.ESTADO_TONE)}</td>
        <td class="sz_table_cell sz_text_right"><strong>${esc(money(item.TOTAL))}</strong></td>
        <td class="sz_table_cell sz_text_right">
          <button type="button" class="sz_button sz_button_ghost" data-edit="${esc(item.OFICINA_FOLHASTAMP)}" aria-label="Editar">
            <i class="fa-solid fa-pen"></i>
          </button>
        </td>
      </tr>
    `).join('');
    els.body.querySelectorAll('[data-open]').forEach((row) => {
      row.addEventListener('click', (event) => {
        if (event.target.closest('[data-edit]')) return;
        openExisting(row.dataset.open);
      });
    });
    els.body.querySelectorAll('[data-edit]').forEach((btn) => {
      btn.addEventListener('click', () => openExisting(btn.dataset.edit));
    });
  }

  async function loadMeta() {
    const payload = await api(cfg.metaUrl);
    state.meta = payload;
    renderMechanicOptions();
    els.newBtn.disabled = !can('insert') && !can('edit');
    els.typesBtn.hidden = !can('workTypes');
    refreshAiSuggestionButton();
  }

  async function loadSheets() {
    const params = new URLSearchParams();
    if (els.search.value.trim()) params.set('q', els.search.value.trim());
    if (els.stateFilter.value) params.set('estado', els.stateFilter.value);
    els.body.innerHTML = '<tr><td colspan="9" class="sz_table_cell sz_text_muted">A carregar...</td></tr>';
    const payload = await api(`${cfg.sheetsUrl}?${params.toString()}`);
    state.items = payload.items || [];
    updateMetrics(payload.summary || {});
    renderTable();
  }

  function resetSheetForm() {
    els.sheetStamp.value = '';
    els.sheetNo.value = '';
    els.vehicleStamp.value = '';
    els.vehicleSearch.value = '';
    els.typeStamp.value = '';
    els.typeSearch.value = '';
    els.jobText.value = '';
    els.date.value = todayLocal();
    els.start.value = '';
    els.end.value = '';
    els.tempo.value = '';
    els.mechanic.value = '';
    els.planDate.value = '';
    els.planStart.value = '';
    els.planEnd.value = '';
    els.sheetState.value = 'ABERTA';
    els.obs.value = '';
    state.lines = [];
    setSheetStatus('');
    renderLines();
    refreshAiSuggestionButton();
  }

  function fillSheet(sheet) {
    els.sheetStamp.value = sheet.OFICINA_FOLHASTAMP || '';
    els.sheetNo.value = sheet.NO || '';
    els.vehicleStamp.value = sheet.VASTAMP || '';
    els.vehicleSearch.value = sheet.MATRICULA || '';
    els.typeStamp.value = sheet.OFICINA_TRABSTAMP || '';
    els.typeSearch.value = sheet.TRAB_DESCRICAO || '';
    els.jobText.value = sheet.TRABALHO || '';
    els.date.value = sheet.DATA || '';
    els.start.value = sheet.HORAINI || '';
    els.end.value = sheet.HORAFIM || '';
    els.tempo.value = sheet.TEMPO || '';
    els.mechanic.value = sheet.OFICINA_MECSTAMP || '';
    els.planDate.value = sheet.PLAN_DATA || '';
    els.planStart.value = sheet.PLAN_HORAINI || '';
    els.planEnd.value = sheet.PLAN_HORAFIM || '';
    els.sheetState.value = sheet.ESTADO || 'ABERTA';
    els.obs.value = sheet.OBS || '';
    state.lines = (sheet.lines || []).map((line) => ({ ...line, cid: line.OFICINA_LINHASTAMP || crypto.randomUUID() }));
    renderLines();
    refreshAiSuggestionButton();
  }

  function openNew() {
    resetSheetForm();
    els.sheetTitle.textContent = 'Nova folha de obra';
    els.annulBtn.hidden = true;
    sheetModal.show();
  }

  async function openExisting(stamp) {
    resetSheetForm();
    els.sheetTitle.textContent = 'Folha de obra';
    setSheetStatus('A carregar...');
    sheetModal.show();
    try {
      const payload = await api(`${cfg.sheetsUrl}/${encodeURIComponent(stamp)}`);
      fillSheet(payload.sheet);
      els.sheetTitle.textContent = `Folha de obra ${payload.sheet.NO || ''}`;
      els.annulBtn.hidden = !can('delete') || payload.sheet.ESTADO === 'ANULADA';
      setSheetStatus('');
    } catch (error) {
      setSheetStatus(error.message, 'danger');
    }
  }

  function collectSheetPayload() {
    return {
      OFICINA_FOLHASTAMP: els.sheetStamp.value,
      VASTAMP: els.vehicleStamp.value,
      MATRICULA: els.vehicleSearch.value,
      OFICINA_TRABSTAMP: els.typeStamp.value,
      TRABALHO: els.jobText.value,
      DATA: els.date.value,
      HORAINI: els.start.value,
      HORAFIM: els.end.value,
      TEMPO: els.tempo.value,
      OFICINA_MECSTAMP: els.mechanic.value,
      PLAN_DATA: els.planDate.value,
      PLAN_HORAINI: els.planStart.value,
      PLAN_HORAFIM: els.planEnd.value,
      ESTADO: els.sheetState.value,
      OBS: els.obs.value,
      lines: state.lines.map((line, index) => ({
        STSTAMP: line.STSTAMP || '',
        REF: line.REF || '',
        DESIGN: line.DESIGN || '',
        UNIDADE: line.UNIDADE || '',
        QTT: line.QTT || 0,
        PUNIT: line.PUNIT || 0,
        OBS: line.OBS || '',
        ORDEM: index + 1,
      })),
    };
  }

  async function saveCurrentSheet() {
    const stamp = els.sheetStamp.value.trim();
    const url = stamp ? `${cfg.sheetsUrl}/${encodeURIComponent(stamp)}` : cfg.sheetsUrl;
    const method = stamp ? 'PUT' : 'POST';
    els.saveBtn.disabled = true;
    setSheetStatus('A gravar...');
    try {
      const payload = await api(url, {
        method,
        body: JSON.stringify(collectSheetPayload()),
      });
      fillSheet(payload.sheet);
      els.sheetTitle.textContent = `Folha de obra ${payload.sheet.NO || ''}`;
      els.annulBtn.hidden = !can('delete') || payload.sheet.ESTADO === 'ANULADA';
      setSheetStatus('Gravado.');
      toast('Folha de obra gravada.');
      await loadSheets();
    } catch (error) {
      setSheetStatus(error.message, 'danger');
    } finally {
      els.saveBtn.disabled = false;
    }
  }

  async function annulCurrentSheet() {
    const stamp = els.sheetStamp.value.trim();
    if (!stamp) return;
    if (!window.confirm('Anular esta folha de obra?')) return;
    try {
      const payload = await api(`${cfg.sheetsUrl}/${encodeURIComponent(stamp)}`, { method: 'DELETE' });
      fillSheet(payload.sheet);
      els.annulBtn.hidden = true;
      toast('Folha de obra anulada.');
      await loadSheets();
    } catch (error) {
      setSheetStatus(error.message, 'danger');
    }
  }

  async function suggestWithAi() {
    if (!can('aiSuggestion')) return;
    const vastamp = els.vehicleStamp.value.trim();
    const workTypeStamp = els.typeStamp.value.trim();
    if (!vastamp || !workTypeStamp) {
      toast('Seleciona a matrícula e o trabalho pré-definido.', 'warning');
      refreshAiSuggestionButton();
      return;
    }
    els.aiSuggestBtn.classList.add('is-loading');
    els.aiSuggestBtn.setAttribute('aria-busy', 'true');
    els.aiSuggestBtn.disabled = true;
    setSheetStatus('A gerar sugestão AI...');
    const controller = new AbortController();
    const requestTimeout = window.setTimeout(() => controller.abort(), 60000);
    try {
      const payload = await api(cfg.aiSuggestionUrl, {
        method: 'POST',
        signal: controller.signal,
        body: JSON.stringify({
          VASTAMP: vastamp,
          OFICINA_TRABSTAMP: workTypeStamp,
        }),
      });
      const suggestion = payload.suggestion || {};
      els.tempo.value = suggestion.estimated_minutes || '';
      els.obs.value = suggestion.instructions || '';
      setSheetStatus('Sugestão AI aplicada. Revê antes de gravar.');
      toast('Tempo e instruções sugeridos pela AI.');
    } catch (error) {
      const message = error?.name === 'AbortError'
        ? 'A pesquisa AI está a demorar demasiado. Tenta novamente dentro de instantes.'
        : error.message;
      setSheetStatus(message, 'danger');
    } finally {
      window.clearTimeout(requestTimeout);
      els.aiSuggestBtn.classList.remove('is-loading');
      els.aiSuggestBtn.removeAttribute('aria-busy');
      refreshAiSuggestionButton();
    }
  }

  function updateLine(cid, field, value) {
    const line = state.lines.find((item) => item.cid === cid);
    if (!line) return;
    line[field] = value;
    renderLines();
  }

  function addLine(seed = {}) {
    state.lines.push({
      cid: crypto.randomUUID(),
      STSTAMP: '',
      REF: '',
      DESIGN: '',
      UNIDADE: '',
      QTT: 1,
      PUNIT: 0,
      OBS: '',
      ...seed,
    });
    renderLines();
  }

  function removeLine(cid) {
    state.lines = state.lines.filter((line) => line.cid !== cid);
    renderLines();
  }

  function lineTotal(line) {
    return Math.max(0, toNum(line.QTT) * toNum(line.PUNIT));
  }

  function renderLines() {
    if (!state.lines.length) {
      els.linesBody.innerHTML = '<tr><td colspan="8" class="sz_table_cell sz_text_muted">Sem consumos.</td></tr>';
      els.total.textContent = money(0);
      return;
    }
    const total = state.lines.reduce((sum, line) => sum + lineTotal(line), 0);
    els.total.textContent = money(total);
    els.linesBody.innerHTML = state.lines.map((line) => `
      <tr class="sz_table_row" data-line="${esc(line.cid)}">
        <td class="sz_table_cell gr-workshop-line-ref">
          <input class="sz_input" data-line-field="REF" value="${esc(line.REF || '')}" autocomplete="off">
          <div class="gr-workshop-line-results" hidden></div>
        </td>
        <td class="sz_table_cell"><input class="sz_input" data-line-field="DESIGN" value="${esc(line.DESIGN || '')}"></td>
        <td class="sz_table_cell"><input class="sz_input" data-line-field="UNIDADE" value="${esc(line.UNIDADE || '')}"></td>
        <td class="sz_table_cell"><input class="sz_input" data-line-field="QTT" type="number" min="0" step="0.001" value="${esc(line.QTT || 0)}"></td>
        <td class="sz_table_cell"><input class="sz_input" data-line-field="PUNIT" type="number" min="0" step="0.0001" value="${esc(line.PUNIT || 0)}"></td>
        <td class="sz_table_cell"><div class="gr-workshop-line-total">${esc(money(lineTotal(line)))}</div></td>
        <td class="sz_table_cell"><input class="sz_input" data-line-field="OBS" value="${esc(line.OBS || '')}"></td>
        <td class="sz_table_cell sz_text_right">
          <button type="button" class="sz_icon_button" data-remove-line="${esc(line.cid)}" aria-label="Remover">
            <i class="fa-solid fa-xmark"></i>
          </button>
        </td>
      </tr>
    `).join('');
    bindLineEvents();
  }

  function bindLineEvents() {
    els.linesBody.querySelectorAll('[data-line-field]').forEach((input) => {
      const row = input.closest('[data-line]');
      const cid = row.dataset.line;
      const field = input.dataset.lineField;
      input.addEventListener('change', () => updateLine(cid, field, input.value));
      if (field === 'REF') {
        input.addEventListener('input', () => {
          const line = state.lines.find((item) => item.cid === cid);
          if (line) line.REF = input.value;
          queueArticleSearch(input, cid);
        });
      }
    });
    els.linesBody.querySelectorAll('[data-remove-line]').forEach((btn) => {
      btn.addEventListener('click', () => removeLine(btn.dataset.removeLine));
    });
  }

  function renderDropdown(container, rows, renderer, onPick) {
    if (!container) return;
    if (!rows.length) {
      container.innerHTML = '<div class="gr-workshop-result"><span>Sem resultados.</span></div>';
      container.hidden = false;
      return;
    }
    container.innerHTML = rows.map((row, index) => renderer(row, index)).join('');
    container.hidden = false;
    container.querySelectorAll('[data-pick-index]').forEach((btn) => {
      btn.addEventListener('click', () => onPick(rows[Number(btn.dataset.pickIndex)]));
    });
  }

  function closeVehicleLookup() {
    els.vehicleResults.hidden = true;
    els.vehicleResults.innerHTML = '';
    state.vehicleRows = [];
    state.vehicleActiveIndex = -1;
  }

  function renderVehicleLookupMessage(message, tone = 'muted') {
    els.vehicleResults.innerHTML = `<div class="sz_table_lookup_empty ${tone === 'danger' ? 'is-danger' : ''}">${esc(message)}</div>`;
    els.vehicleResults.hidden = false;
    state.vehicleRows = [];
    state.vehicleActiveIndex = -1;
  }

  function setVehicleLookupActive(index) {
    const buttons = Array.from(els.vehicleResults.querySelectorAll('.sz_table_lookup_item'));
    if (!buttons.length) {
      state.vehicleActiveIndex = -1;
      return;
    }
    const nextIndex = Math.max(0, Math.min(buttons.length - 1, index));
    buttons.forEach((button, buttonIndex) => {
      button.classList.toggle('is-active', buttonIndex === nextIndex);
    });
    state.vehicleActiveIndex = nextIndex;
  }

  function pickVehicleRow(row) {
    if (!row) return;
    const source = row.row && typeof row.row === 'object' ? row.row : row;
    const plate = String(row.value || source.MATRICULA || '').trim();
    els.vehicleStamp.value = source.VASTAMP || row.VASTAMP || '';
    els.vehicleSearch.value = plate;
    closeVehicleLookup();
    els.vehicleSearch.focus();
    refreshAiSuggestionButton();
  }

  function renderVehicleLookupRows(rows) {
    state.vehicleRows = Array.isArray(rows) ? rows : [];
    els.vehicleResults.innerHTML = '';
    if (!state.vehicleRows.length) {
      renderVehicleLookupMessage('Sem resultados');
      return;
    }
    state.vehicleRows.forEach((row, index) => {
      const fallbackValue = row.value === undefined || row.value === null ? '' : row.value;
      const displayValues = Array.isArray(row.display)
        ? row.display.map((value) => String(value ?? '').trim()).filter(Boolean)
        : [];
      const primaryValue = String(fallbackValue ?? '').trim() || displayValues[0] || '-';
      const metaValues = displayValues.filter((value) => value !== primaryValue);
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'sz_table_lookup_item';
      button.dataset.index = String(index);
      button.innerHTML = `
        <span class="sz_table_lookup_item_label">${esc(primaryValue)}</span>
        ${metaValues.length ? `<span class="sz_table_lookup_item_value">${esc(metaValues.join(' · '))}</span>` : ''}
      `;
      button.addEventListener('mouseenter', () => setVehicleLookupActive(index));
      button.addEventListener('mousedown', (event) => {
        event.preventDefault();
        pickVehicleRow(row);
      });
      els.vehicleResults.appendChild(button);
    });
    els.vehicleResults.hidden = false;
    setVehicleLookupActive(0);
  }

  function queueVehicleSearch() {
    clearTimeout(state.vehicleTimer);
    state.vehicleTimer = setTimeout(async () => {
      try {
        const term = els.vehicleSearch.value.trim();
        if (!term) {
          closeVehicleLookup();
          return;
        }
        renderVehicleLookupMessage('A procurar...');
        const payload = await api(`${cfg.vehiclesUrl}?q=${encodeURIComponent(term)}`);
        renderVehicleLookupRows(payload.rows || []);
      } catch (error) {
        renderVehicleLookupMessage(error.message || 'Erro na pesquisa', 'danger');
      }
    }, 180);
  }

  function queueTypeSearch() {
    clearTimeout(state.typeTimer);
    state.typeTimer = setTimeout(async () => {
      try {
        const term = els.typeSearch.value.trim();
        const payload = await api(`${cfg.workTypesUrl}?q=${encodeURIComponent(term)}`);
        renderDropdown(
          els.typeResults,
          payload.rows || [],
          (row, index) => `
            <button type="button" class="gr-workshop-result" data-pick-index="${index}">
              <strong>${esc(row.CODIGO || '')}</strong>
              <span>${esc(row.DESCRICAO || '')}</span>
            </button>
          `,
          (row) => {
            els.typeStamp.value = row.OFICINA_TRABSTAMP || '';
            els.typeSearch.value = row.DESCRICAO || '';
            if (!els.jobText.value.trim()) els.jobText.value = row.DESCRICAO || '';
            els.typeResults.hidden = true;
            refreshAiSuggestionButton();
          }
        );
      } catch (_) {
        els.typeResults.hidden = true;
      }
    }, 180);
  }

  function queueArticleSearch(input, cid) {
    clearTimeout(state.articleTimer);
    state.articleTimer = setTimeout(async () => {
      const container = input.parentElement.querySelector('.gr-workshop-line-results');
      try {
        const term = input.value.trim();
        if (term.length < 1) {
          container.hidden = true;
          return;
        }
        const payload = await api(`${cfg.articlesUrl}?q=${encodeURIComponent(term)}`);
        renderDropdown(
          container,
          payload.rows || [],
          (row, index) => `
            <button type="button" class="gr-workshop-result" data-pick-index="${index}">
              <strong>${esc(row.REF || '')}</strong>
              <span>${esc(row.DESIGN || '')}</span>
            </button>
          `,
          (row) => {
            const line = state.lines.find((item) => item.cid === cid);
            if (!line) return;
            line.STSTAMP = row.STSTAMP || '';
            line.REF = row.REF || '';
            line.DESIGN = row.DESIGN || '';
            line.UNIDADE = row.UNIDADE || '';
            line.PUNIT = row.PUNIT || 0;
            container.hidden = true;
            renderLines();
          }
        );
      } catch (_) {
        container.hidden = true;
      }
    }, 180);
  }

  async function loadWorkTypesList() {
    els.typesList.innerHTML = '<div class="sz_text_muted">A carregar...</div>';
    const payload = await api(`${cfg.workTypesUrl}?include_inactive=1`);
    const rows = payload.rows || [];
    if (!rows.length) {
      els.typesList.innerHTML = '<div class="sz_text_muted">Sem trabalhos pré-definidos.</div>';
      return;
    }
    els.typesList.innerHTML = rows.map((row) => `
      <div class="gr-workshop-type-row">
        <strong>${esc(row.CODIGO || '')}</strong>
        <span>${esc(row.DESCRICAO || '')}</span>
        <span>${esc(row.ORDEM || 0)}</span>
        ${badge(row.ATIVO ? 'Ativo' : 'Inativo', row.ATIVO ? 'success' : 'secondary')}
        <button type="button" class="sz_icon_button" data-edit-type="${esc(row.OFICINA_TRABSTAMP)}" aria-label="Editar">
          <i class="fa-solid fa-pen"></i>
        </button>
      </div>
    `).join('');
    els.typesList.querySelectorAll('[data-edit-type]').forEach((btn) => {
      const row = rows.find((item) => item.OFICINA_TRABSTAMP === btn.dataset.editType);
      btn.addEventListener('click', () => fillTypeForm(row));
    });
  }

  function fillTypeForm(row = null) {
    els.typeEditStamp.value = row?.OFICINA_TRABSTAMP || '';
    els.typeCode.value = row?.CODIGO || '';
    els.typeDescription.value = row?.DESCRICAO || '';
    els.typeOrder.value = row?.ORDEM || 0;
    els.typeActive.checked = row ? !!row.ATIVO : true;
  }

  async function saveType() {
    const stamp = els.typeEditStamp.value.trim();
    const url = stamp ? `${cfg.workTypesUrl}/${encodeURIComponent(stamp)}` : cfg.workTypesUrl;
    const method = stamp ? 'PUT' : 'POST';
    els.typeSaveBtn.disabled = true;
    try {
      await api(url, {
        method,
        body: JSON.stringify({
          CODIGO: els.typeCode.value,
          DESCRICAO: els.typeDescription.value,
          ORDEM: els.typeOrder.value,
          ATIVO: els.typeActive.checked,
        }),
      });
      fillTypeForm(null);
      await loadWorkTypesList();
      toast('Trabalho gravado.');
    } catch (error) {
      toast(error.message, 'error');
    } finally {
      els.typeSaveBtn.disabled = false;
    }
  }

  let searchTimer = null;
  function queueLoadSheets() {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(() => loadSheets().catch((error) => toast(error.message, 'error')), 200);
  }

  els.search.addEventListener('input', queueLoadSheets);
  els.stateFilter.addEventListener('change', queueLoadSheets);
  els.refreshBtn.addEventListener('click', () => loadSheets().catch((error) => toast(error.message, 'error')));
  els.newBtn.addEventListener('click', openNew);
  els.saveBtn.addEventListener('click', saveCurrentSheet);
  els.annulBtn.addEventListener('click', annulCurrentSheet);
  els.addLineBtn.addEventListener('click', () => addLine());
  els.aiSuggestBtn?.addEventListener('click', suggestWithAi);
  els.vehicleSearch.addEventListener('input', () => {
    els.vehicleStamp.value = '';
    refreshAiSuggestionButton();
    queueVehicleSearch();
  });
  els.vehicleSearch.addEventListener('focus', queueVehicleSearch);
  els.vehicleSearch.addEventListener('keydown', (event) => {
    if (els.vehicleResults.hidden) return;
    if (event.key === 'ArrowDown') {
      event.preventDefault();
      setVehicleLookupActive(state.vehicleActiveIndex + 1);
    } else if (event.key === 'ArrowUp') {
      event.preventDefault();
      setVehicleLookupActive(state.vehicleActiveIndex - 1);
    } else if (event.key === 'Enter') {
      if (state.vehicleActiveIndex >= 0 && state.vehicleRows[state.vehicleActiveIndex]) {
        event.preventDefault();
        pickVehicleRow(state.vehicleRows[state.vehicleActiveIndex]);
      }
    } else if (event.key === 'Escape') {
      closeVehicleLookup();
    }
  });
  els.vehicleSearch.addEventListener('blur', () => {
    window.setTimeout(closeVehicleLookup, 150);
  });
  els.typeSearch.addEventListener('input', () => {
    els.typeStamp.value = '';
    refreshAiSuggestionButton();
    queueTypeSearch();
  });
  els.typeSearch.addEventListener('focus', queueTypeSearch);
  els.typesBtn.addEventListener('click', async () => {
    fillTypeForm(null);
    typesModal.show();
    await loadWorkTypesList().catch((error) => toast(error.message, 'error'));
  });
  els.typeSaveBtn.addEventListener('click', saveType);
  document.addEventListener('click', (event) => {
    if (!event.target.closest('.sz_table_lookup_field')) {
      closeVehicleLookup();
    }
    if (!event.target.closest('.gr-workshop-autocomplete')) {
      els.typeResults.hidden = true;
    }
    if (!event.target.closest('.gr-workshop-line-ref')) {
      document.querySelectorAll('.gr-workshop-line-results').forEach((node) => {
        node.hidden = true;
      });
    }
  });

  loadMeta()
    .then(loadSheets)
    .then(() => {
      const stamp = new URLSearchParams(window.location.search).get('folha');
      if (stamp) openExisting(stamp);
    })
    .catch((error) => {
      els.body.innerHTML = `<tr><td colspan="9" class="sz_table_cell text-danger">${esc(error.message)}</td></tr>`;
    });
})();
