document.addEventListener('DOMContentLoaded', () => {
  const els = {
    counts: document.getElementById('docAiCounts'),
    inboxBody: document.getElementById('docAiInboxBody'),
    uploadBtn: document.getElementById('docAiUploadBtn'),
    refreshBtn: document.getElementById('docAiRefreshBtn'),
    archiveBtn: document.getElementById('docAiArchiveBtn'),
    contextDomain: document.getElementById('docAiContextDomain'),
    viewTabs: document.getElementById('docAiViewTabs'),
    dateFrom: document.getElementById('docAiDocumentDateFrom'),
    dateTo: document.getElementById('docAiDocumentDateTo'),
    valueMin: document.getElementById('docAiValueMin'),
    valueMax: document.getElementById('docAiValueMax'),
    tableScroller: document.querySelector('.docai-inbox-table-panel .sz_table_wrap'),
  };

  const availableViewButtons = [...(els.viewTabs?.querySelectorAll('[data-view]') || [])];
  const allowedViews = new Set(availableViewButtons.map((button) => button.dataset.view).filter(Boolean));
  const initialParams = new URLSearchParams(window.location.search);
  const initialView = initialParams.get('view');
  const initialArchived = ['1', 'true', 'yes'].includes(String(initialParams.get('archived') || '').toLowerCase());
  const filterFields = ['entity', 'supplier', 'cost_center', 'document_number'];
  const state = {
    allItems: [],
    filteredItems: [],
    docTypes: [],
    invoiceTypes: [],
    loading: false,
    view: allowedViews.has(initialView) ? initialView : (availableViewButtons[0]?.dataset.view || ''),
    total: 0,
    archived: initialArchived,
    permissions: {},
    stateFilters: new Set(),
    typeFilters: new Set(),
    invoiceTypeFilters: new Set(),
    activeDocumentId: '',
    restorePending: true,
    filters: Object.fromEntries(filterFields.map((field) => [field, new Set()])),
  };

  function escapeHtml(value) {
    return String(value == null ? '' : value)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function showMessage(message, type = 'info') {
    if (typeof window.showToast === 'function') {
      window.showToast(message, type);
      return;
    }
    console[type === 'error' ? 'error' : 'log'](message);
  }

  async function fetchJson(url, options = {}) {
    const response = await fetch(url, options);
    let payload = {};
    try { payload = await response.json(); } catch (_) {}
    if (!response.ok) throw new Error(payload.error || `HTTP ${response.status}`);
    return payload;
  }

  function docTypeLabel(value) {
    const item = state.docTypes.find((entry) => entry.value === value);
    return item ? item.label : (value || '-');
  }

  function fieldValue(item, field) {
    const mapping = {
      entity: item.entity_name,
      supplier: item.supplier_name,
      cost_center: item.cost_center,
      document_number: item.document_number,
    };
    return String(mapping[field] || '').trim();
  }

  function numberOrNull(value) {
    if (value == null || String(value).trim() === '') return null;
    const parsed = Number(String(value).replace(',', '.'));
    return Number.isFinite(parsed) ? parsed : null;
  }

  function matchesFilters(item, excludedField = '') {
    if (excludedField !== 'state' && state.stateFilters.size && !state.stateFilters.has(String(item.business_state || ''))) return false;
    if (excludedField !== 'document_type' && state.typeFilters.size && !state.typeFilters.has(String(item.document_type || 'unknown'))) return false;
    if (excludedField !== 'invoice_type' && state.invoiceTypeFilters.size) {
      if (String(item.document_type || 'unknown') !== 'invoice') return false;
      if (!state.invoiceTypeFilters.has(String(item.invoice_type || 'unknown'))) return false;
    }
    for (const field of filterFields) {
      if (field === excludedField) continue;
      const selected = state.filters[field];
      if (selected.size && !selected.has(fieldValue(item, field))) return false;
    }
    const date = String(item.document_date || '');
    if (els.dateFrom?.value && (!date || date < els.dateFrom.value)) return false;
    if (els.dateTo?.value && (!date || date > els.dateTo.value)) return false;
    const amount = Number(item.document_value || 0);
    const minimum = numberOrNull(els.valueMin?.value);
    const maximum = numberOrNull(els.valueMax?.value);
    if (minimum !== null && amount < minimum) return false;
    if (maximum !== null && amount > maximum) return false;
    return true;
  }

  function contextualOptions(field) {
    return [...new Set(
      state.allItems
        .filter((item) => matchesFilters(item, field))
        .map((item) => fieldValue(item, field))
        .filter(Boolean),
    )].sort((left, right) => left.localeCompare(right, 'pt', { sensitivity: 'base' }));
  }

  function closeColumnFilters(except = null) {
    document.querySelectorAll('.docai-column-filter.is-open').forEach((filter) => {
      if (filter !== except) filter.classList.remove('is-open');
    });
  }

  function renderColumnFilter(field) {
    const host = document.querySelector(`.docai-column-filter[data-filter="${field}"]`);
    if (!host) return;
    const selected = state.filters[field];
    const query = String(host.querySelector('.docai-column-filter-search')?.value || '').trim().toLowerCase();
    const options = contextualOptions(field).filter((value) => value.toLowerCase().includes(query));
    const label = selected.size ? `${selected.size} selecionado${selected.size === 1 ? '' : 's'}` : 'Todos';
    host.innerHTML = `
      <button type="button" class="docai-column-filter-trigger" aria-expanded="${host.classList.contains('is-open') ? 'true' : 'false'}">
        <span>${escapeHtml(label)}</span><i class="fa-solid fa-chevron-down"></i>
      </button>
      <div class="docai-column-filter-menu">
        <input class="sz_input docai-column-filter-search" type="search" placeholder="Pesquisar" value="${escapeHtml(query)}">
        <div class="docai-column-filter-options">
          ${options.length ? options.map((value) => `
            <label class="docai-column-filter-option">
              <input type="checkbox" value="${escapeHtml(value)}" ${selected.has(value) ? 'checked' : ''}>
              <span>${escapeHtml(value)}</span>
            </label>
          `).join('') : '<span class="sz_text_muted">Sem valores.</span>'}
        </div>
        <button type="button" class="docai-column-filter-clear">Limpar</button>
      </div>
    `;
  }

  function refreshColumnFilters() {
    filterFields.forEach(renderColumnFilter);
  }

  function resetFilters() {
    state.stateFilters.clear();
    state.typeFilters.clear();
    state.invoiceTypeFilters.clear();
    filterFields.forEach((field) => state.filters[field].clear());
    [els.dateFrom, els.dateTo, els.valueMin, els.valueMax].forEach((input) => {
      if (input) input.value = '';
    });
    closeColumnFilters();
  }

  function formatDate(value) {
    if (!value) return '-';
    const parts = String(value).slice(0, 10).split('-');
    return parts.length === 3 ? `${parts[2]}/${parts[1]}/${parts[0]}` : String(value);
  }

  function formatValue(value, currency) {
    const numeric = Number(value || 0);
    const code = String(currency || '').trim().toUpperCase();
    const formatted = new Intl.NumberFormat('pt-PT', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
      useGrouping: true,
    }).format(numeric);
    return code ? `${formatted} ${code}` : formatted;
  }

  function stateClass(value) {
    const normalized = String(value || '').toLowerCase();
    if (normalized === 'ok' || normalized === 'validado') return 'is-ok';
    if (normalized === 'ação' || normalized === 'pendente') return 'is-action';
    if (normalized === 'bloqueio') return 'is-blocked';
    return 'is-neutral';
  }

  function analysisUrl(documentId = '') {
    const params = new URLSearchParams();
    if (documentId) params.set('document_id', documentId);
    if (state.view) params.set('view', state.view);
    if (state.archived) params.set('archive', '1');
    return `/document_ai/extract?${params.toString()}`;
  }

  function navigationStorageKey() {
    return `document-ai-list:${state.view}:${state.archived ? 'archive' : 'inbox'}`;
  }

  function saveNavigationState(activeDocumentId = '') {
    const payload = {
      view: state.view,
      archived: state.archived,
      activeDocumentId,
      stateFilters: [...state.stateFilters],
      typeFilters: [...state.typeFilters],
      invoiceTypeFilters: [...state.invoiceTypeFilters],
      filters: Object.fromEntries(filterFields.map((field) => [field, [...state.filters[field]]])),
      dateFrom: els.dateFrom?.value || '', dateTo: els.dateTo?.value || '',
      valueMin: els.valueMin?.value || '', valueMax: els.valueMax?.value || '',
      scrollTop: els.tableScroller?.scrollTop || 0,
      scrollLeft: els.tableScroller?.scrollLeft || 0,
    };
    sessionStorage.setItem(navigationStorageKey(), JSON.stringify(payload));
  }

  function restoreNavigationState() {
    if (!state.restorePending) return;
    state.restorePending = false;
    let payload = null;
    try { payload = JSON.parse(sessionStorage.getItem(navigationStorageKey()) || 'null'); } catch (_) {}
    if (!payload) return;
    state.activeDocumentId = String(payload.activeDocumentId || '');
    state.stateFilters = new Set(payload.stateFilters || []);
    state.typeFilters = new Set(payload.typeFilters || []);
    state.invoiceTypeFilters = new Set(payload.invoiceTypeFilters || []);
    filterFields.forEach((field) => { state.filters[field] = new Set(payload.filters?.[field] || []); });
    if (els.dateFrom) els.dateFrom.value = payload.dateFrom || '';
    if (els.dateTo) els.dateTo.value = payload.dateTo || '';
    if (els.valueMin) els.valueMin.value = payload.valueMin || '';
    if (els.valueMax) els.valueMax.value = payload.valueMax || '';
    window.requestAnimationFrame(() => {
      if (!els.tableScroller) return;
      els.tableScroller.scrollTop = Number(payload.scrollTop || 0);
      els.tableScroller.scrollLeft = Number(payload.scrollLeft || 0);
      document.querySelector(`[data-document-id="${CSS.escape(state.activeDocumentId)}"]`)?.focus({ preventScroll: true });
    });
  }

  function openDocument(documentId) {
    if (!documentId) return;
    saveNavigationState(documentId);
    window.location.href = analysisUrl(documentId);
  }

  function renderTable() {
    if (!els.inboxBody) return;
    state.filteredItems = state.allItems.filter((item) => matchesFilters(item));
    if (!state.filteredItems.length) {
      const message = state.allItems.length ? 'Sem documentos para os filtros selecionados.' : 'Sem documentos.';
      const clearAction = state.allItems.length
        ? '<button type="button" class="sz_button sz_button_ghost docai-empty-clear" data-action="reset-filters"><i class="fa-solid fa-filter-circle-xmark"></i><span>Limpar filtros</span></button>'
        : '';
      els.inboxBody.innerHTML = `<tr><td colspan="9"><div class="docai-empty-filter-state"><span class="sz_text_muted">${message}</span>${clearAction}</div></td></tr>`;
      renderCounts();
      return;
    }
    const canOpen = Boolean(state.archived ? state.permissions.consult : state.permissions.analyze);
    els.inboxBody.innerHTML = state.filteredItems.map((item) => `
      <tr class="${canOpen ? 'docai-inbox-row is-interactive' : 'docai-inbox-row'}${state.activeDocumentId === item.id ? ' is-returned' : ''}"
          data-document-id="${escapeHtml(item.id)}" ${canOpen ? 'tabindex="0" role="button" aria-label="Analisar"' : ''}>
        <td><span class="docai-business-state ${stateClass(item.business_state)}"><i></i>${escapeHtml(item.business_state || '-')}</span></td>
        <td>${escapeHtml(item.doc_type_label || docTypeLabel(item.doc_type))}</td>
        <td>${escapeHtml(item.entity_name || '-')}</td>
        <td>${escapeHtml(item.supplier_name || '-')}</td>
        <td>${escapeHtml(item.cost_center || '-')}</td>
        <td>${escapeHtml(item.document_number || '-')}</td>
        <td>${escapeHtml(formatDate(item.document_date))}</td>
        <td class="docai-value-cell">${escapeHtml(formatValue(item.document_value, item.currency))}</td>
        <td>
          <div class="docai-row-actions">
            ${!state.archived && state.permissions.delete ? `
              <button type="button" class="sz_button sz_button_ghost docai-row-delete" data-action="delete" data-id="${escapeHtml(item.id)}" data-file="${escapeHtml(item.file_name)}" title="Eliminar">
                <i class="fa-solid fa-trash"></i>
              </button>
            ` : ''}
            ${state.archived && item.business_state === 'Eliminado' && state.permissions.delete ? `
              <button type="button" class="sz_button sz_button_ghost docai-row-recover" data-action="recover" data-id="${escapeHtml(item.id)}" title="Recuperar" aria-label="Recuperar ${escapeHtml(item.file_name)}">
                <i class="fa-solid fa-rotate-left"></i>
              </button>
            ` : ''}
          </div>
        </td>
      </tr>
    `).join('');
    renderCounts();
  }

  function renderCounts() {
    if (!els.counts) return;
    const stateCounts = new Map();
    const statePopulation = state.allItems.filter((item) => matchesFilters(item, 'state'));
    const total = state.total;
    const requiredStates = state.archived
      ? ['Validado', 'Eliminado']
      : state.view === 'accounting'
      ? ['Pendente', 'Validado']
      : ['OK', 'Ação', 'Bloqueio'];

    requiredStates.forEach((value) => stateCounts.set(value, 0));
    statePopulation.forEach((item) => {
      const businessState = String(item.business_state || '-');
      stateCounts.set(businessState, (stateCounts.get(businessState) || 0) + 1);
    });
    const counterGroup = (title, filterName, property, options, selected) => {
      const population = state.allItems.filter((item) => (
        matchesFilters(item, filterName)
        && (filterName !== 'invoice_type' || String(item.document_type || 'unknown') === 'invoice')
      ));
      const counts = new Map(options.map((option) => [String(option.value), { count: 0, label: option.label }]));
      population.forEach((item) => {
        const value = String(item[property] || 'unknown');
        const current = counts.get(value) || { count: 0, label: value || '-' };
        counts.set(value, { ...current, count: current.count + 1 });
      });
      const ordered = [...counts.entries()]
        .filter(([value, data]) => value !== 'unknown' || data.count > 0)
        .sort((left, right) => String(left[1].label).localeCompare(String(right[1].label), 'pt', { sensitivity: 'base' }));
      return `<div class="docai-business-count-group" aria-label="Filtros de ${escapeHtml(title.toLowerCase())}">
        <span class="docai-business-count-title">${escapeHtml(title)}</span>
        <div class="docai-business-count-options">${ordered.map(([value, data]) => `
          <button type="button" class="docai-business-count-chip ${selected.has(value) ? 'is-active' : ''}"
                  data-count-filter="${filterName}" data-value="${escapeHtml(value)}">
            <strong>${data.count}</strong><span>${escapeHtml(data.label || '-')}</span>
          </button>`).join('')}</div></div>`;
    };
    const typeGroups = [];
    typeGroups.push(counterGroup('Tipo de documento', 'document_type', 'document_type', state.docTypes, state.typeFilters));
    if (state.view !== 'home') typeGroups.push(counterGroup('Tipo de fatura', 'invoice_type', 'invoice_type', state.invoiceTypes, state.invoiceTypeFilters));
    els.counts.innerHTML = `
      <div class="docai-counts-scroll">
      <div class="docai-business-count-group" aria-label="Filtros de estado">
        <span class="docai-business-count-title">Estado</span>
        <div class="docai-business-count-options">
          ${[...stateCounts.entries()].map(([value, count]) => `
            <button type="button" class="docai-business-count-chip ${state.stateFilters.has(value) ? 'is-active' : ''}"
                    data-state="${escapeHtml(String(value).toLowerCase())}" data-count-filter="state" data-value="${escapeHtml(value)}">
              <strong>${count}</strong><span>${escapeHtml(value)}</span>
            </button>
          `).join('') || '<span class="sz_text_muted">Sem estados</span>'}
        </div>
      </div>
      ${typeGroups.join('')}
      </div>
      <button type="button" class="docai-count-card docai-count-card-action docai-filtered-total" data-action="reset-filters" title="Limpar filtros" aria-label="Mostrar todos os documentos e limpar filtros">
        <span class="count">${total}</span>
        <span class="label">Total</span>
      </button>
    `;
  }

  function applyFilters({ resetScroll = false } = {}) {
    if (resetScroll && els.tableScroller) els.tableScroller.scrollTop = 0;
    renderTable();
    refreshColumnFilters();
  }

  function renderViewTabs() {
    availableViewButtons.forEach((button) => {
      const active = button.dataset.view === state.view;
      button.classList.toggle('is-active', active);
      if (availableViewButtons.length > 1) {
        button.setAttribute('aria-selected', active ? 'true' : 'false');
        button.tabIndex = active ? 0 : -1;
      }
    });
    els.viewTabs?.classList.toggle('is-single-view', availableViewButtons.length === 1);
    if (els.contextDomain) els.contextDomain.textContent = state.archived ? 'ARQUIVO' : 'INBOX';
    if (els.archiveBtn) {
      els.archiveBtn.classList.toggle('is-active', state.archived);
      const label = els.archiveBtn.querySelector('span');
      if (label) label.textContent = state.archived ? 'Inbox' : 'Arquivo';
      const icon = els.archiveBtn.querySelector('i');
      if (icon) icon.className = state.archived ? 'fa-solid fa-inbox' : 'fa-solid fa-box-archive';
    }
    if (els.uploadBtn) els.uploadBtn.hidden = !state.permissions.create;
  }

  async function loadInbox() {
    if (state.loading || !state.view) return;
    state.loading = true;
    try {
      const archivedParam = state.archived ? '&archived=1' : '';
      const payload = await fetchJson(`/api/document_ai/inbox?view=${encodeURIComponent(state.view)}${archivedParam}`);
      state.allItems = Array.isArray(payload.items) ? payload.items : [];
      state.docTypes = Array.isArray(payload.doc_types) ? payload.doc_types : [];
      state.invoiceTypes = Array.isArray(payload.invoice_types) ? payload.invoice_types : [];
      state.permissions = payload.permissions || {};
      state.total = Number(payload.total || 0);
      if (allowedViews.has(payload.view)) state.view = payload.view;
      renderViewTabs();
      restoreNavigationState();
      applyFilters({ resetScroll: !state.activeDocumentId });
    } catch (error) {
      console.error(error);
      if (els.inboxBody) els.inboxBody.innerHTML = `<tr><td colspan="9" class="docai-load-error">${escapeHtml(error.message || 'Erro ao carregar a Inbox.')}</td></tr>`;
      showMessage(error.message || 'Erro ao carregar a Inbox.', 'error');
    } finally {
      state.loading = false;
    }
  }

  function selectView(view, { updateHistory = true } = {}) {
    if (!allowedViews.has(view) || view === state.view) return;
    state.view = view;
    resetFilters();
    state.activeDocumentId = '';
    state.restorePending = true;
    renderViewTabs();
    if (updateHistory) {
      const url = new URL(window.location.href);
      url.search = '';
      url.searchParams.set('view', view);
      if (state.archived) url.searchParams.set('archived', '1');
      window.history.pushState({ documentAiView: view, archived: state.archived }, '', url);
    }
    loadInbox();
  }

  function toggleArchive() {
    state.archived = !state.archived;
    resetFilters();
    state.activeDocumentId = '';
    state.restorePending = true;
    const url = new URL(window.location.href);
    state.archived ? url.searchParams.set('archived', '1') : url.searchParams.delete('archived');
    window.history.pushState({ documentAiView: state.view, archived: state.archived }, '', url);
    renderViewTabs();
    loadInbox();
  }

  async function deleteDocument(id, fileName = '') {
    try {
      await fetchJson(`/api/document_ai/documents/${encodeURIComponent(id)}`, {
        method: 'DELETE',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ view: state.view }),
      });
      showMessage('Documento eliminado.', 'success');
      await loadInbox();
    } catch (error) {
      showMessage(error.message || 'Falha ao eliminar.', 'error');
    }
  }

  async function recoverDocument(id) {
    try {
      await fetchJson(`/api/document_ai/documents/${encodeURIComponent(id)}/recover`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ view: state.view }),
      });
      showMessage('Documento recuperado.', 'success');
      await loadInbox();
    } catch (error) {
      showMessage(error.message || 'Falha ao recuperar.', 'error');
    }
  }

  document.querySelectorAll('.docai-column-filter').forEach((host) => {
    host.addEventListener('click', (event) => {
      const field = host.dataset.filter;
      if (event.target.closest('.docai-column-filter-trigger')) {
        const opening = !host.classList.contains('is-open');
        closeColumnFilters(host);
        host.classList.toggle('is-open', opening);
        renderColumnFilter(field);
        if (opening) host.querySelector('.docai-column-filter-search')?.focus();
        return;
      }
      const checkbox = event.target.closest('input[type="checkbox"]');
      if (checkbox) {
        checkbox.checked ? state.filters[field].add(checkbox.value) : state.filters[field].delete(checkbox.value);
        applyFilters();
        host.classList.add('is-open');
        return;
      }
      if (event.target.closest('.docai-column-filter-clear')) {
        state.filters[field].clear();
        applyFilters();
        host.classList.add('is-open');
      }
    });
    host.addEventListener('input', (event) => {
      if (!event.target.matches('.docai-column-filter-search')) return;
      const cursorValue = event.target.value;
      renderColumnFilter(host.dataset.filter);
      host.classList.add('is-open');
      const search = host.querySelector('.docai-column-filter-search');
      if (search) search.value = cursorValue;
    });
  });

  document.addEventListener('click', (event) => {
    if (!event.target.closest('.docai-column-filter')) closeColumnFilters();
  });
  [els.dateFrom, els.dateTo, els.valueMin, els.valueMax].forEach((input) => input?.addEventListener('input', applyFilters));
  els.counts?.addEventListener('click', (event) => {
    if (event.target.closest('[data-action="reset-filters"]')) {
      resetFilters();
      applyFilters();
      return;
    }
    const filterButton = event.target.closest('[data-count-filter]');
    if (!filterButton) return;
    const target = filterButton.dataset.countFilter === 'state'
      ? state.stateFilters
      : (filterButton.dataset.countFilter === 'invoice_type' ? state.invoiceTypeFilters : state.typeFilters);
    const value = filterButton.dataset.value || '';
    target.has(value) ? target.delete(value) : target.add(value);
    applyFilters();
  });
  els.refreshBtn?.addEventListener('click', loadInbox);
  els.archiveBtn?.addEventListener('click', toggleArchive);
  els.uploadBtn?.addEventListener('click', () => {
    window.location.href = analysisUrl('');
  });
  els.viewTabs?.addEventListener('click', (event) => {
    if (availableViewButtons.length < 2) return;
    const view = event.target.closest('[data-view]')?.dataset.view;
    if (view) selectView(view);
  });
  els.inboxBody?.addEventListener('click', (event) => {
    if (event.target.closest('[data-action="reset-filters"]')) {
      resetFilters();
      applyFilters();
      return;
    }
    const button = event.target.closest('button[data-action]');
    if (button?.dataset.id) {
      event.stopPropagation();
      if (button.dataset.action === 'delete') deleteDocument(button.dataset.id, button.dataset.file || '');
      if (button.dataset.action === 'recover') recoverDocument(button.dataset.id);
      return;
    }
    const row = event.target.closest('.docai-inbox-row.is-interactive');
    if (row?.dataset.documentId) openDocument(row.dataset.documentId);
  });
  els.inboxBody?.addEventListener('keydown', (event) => {
    if (!['Enter', ' '].includes(event.key) || event.target.closest('button')) return;
    const row = event.target.closest('.docai-inbox-row.is-interactive');
    if (!row?.dataset.documentId) return;
    event.preventDefault();
    openDocument(row.dataset.documentId);
  });
  window.addEventListener('popstate', () => {
    const params = new URLSearchParams(window.location.search);
    const requested = params.get('view');
    const view = allowedViews.has(requested) ? requested : (availableViewButtons[0]?.dataset.view || '');
    const archived = ['1', 'true', 'yes'].includes(String(params.get('archived') || '').toLowerCase());
    const viewChanged = view && view !== state.view;
    const archiveChanged = archived !== state.archived;
    if (!viewChanged && !archiveChanged) return;
    state.view = view;
    state.archived = archived;
    state.activeDocumentId = '';
    state.restorePending = true;
    resetFilters();
    renderViewTabs();
    loadInbox();
  });

  refreshColumnFilters();
  renderViewTabs();
  loadInbox();
});
