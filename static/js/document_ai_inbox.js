document.addEventListener('DOMContentLoaded', () => {
  const els = {
    counts: document.getElementById('docAiCounts'),
    inboxBody: document.getElementById('docAiInboxBody'),
    uploadBtn: document.getElementById('docAiUploadBtn'),
    uploadInput: document.getElementById('docAiUploadInput'),
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
  const initialView = new URLSearchParams(window.location.search).get('view');
  const filterFields = ['entity', 'supplier', 'cost_center', 'document_number'];
  const state = {
    allItems: [],
    filteredItems: [],
    docTypes: [],
    loading: false,
    view: allowedViews.has(initialView) ? initialView : (availableViewButtons[0]?.dataset.view || ''),
    total: 0,
    archived: false,
    permissions: {},
    stateFilters: new Set(),
    typeFilters: new Set(),
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
    if (excludedField !== 'type' && state.typeFilters.size && !state.typeFilters.has(String(item.doc_type || ''))) return false;
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
    try {
      if (code) return new Intl.NumberFormat('pt-PT', { style: 'currency', currency: code }).format(numeric);
    } catch (_) {}
    return new Intl.NumberFormat('pt-PT', { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(numeric);
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
    return `/document_ai/extract?${params.toString()}`;
  }

  function renderTable() {
    if (!els.inboxBody) return;
    state.filteredItems = state.allItems.filter((item) => matchesFilters(item));
    if (!state.filteredItems.length) {
      const message = state.allItems.length ? 'Nenhum resultado.' : 'Sem documentos.';
      els.inboxBody.innerHTML = `<tr><td colspan="9" class="sz_text_muted">${message}</td></tr>`;
      renderCounts();
      return;
    }
    els.inboxBody.innerHTML = state.filteredItems.map((item) => `
      <tr>
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
            ${state.permissions.analyze ? `<button type="button" class="sz_button sz_button_ghost docai-row-ai" data-action="extract" data-id="${escapeHtml(item.id)}" title="Analisar" aria-label="Analisar ${escapeHtml(item.file_name)}">
              <i class="fa-solid fa-wand-magic-sparkles"></i>
            </button>` : ''}
            ${(state.view === 'home' || state.view === 'management') && state.permissions.delete ? `
              <button type="button" class="sz_button sz_button_ghost docai-row-delete" data-action="delete" data-id="${escapeHtml(item.id)}" data-file="${escapeHtml(item.file_name)}" title="Eliminar">
                <i class="fa-solid fa-trash"></i>
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
    const typeCounts = new Map();
    const statePopulation = state.allItems.filter((item) => matchesFilters(item, 'state'));
    const typePopulation = state.allItems.filter((item) => matchesFilters(item, 'type'));
    const total = state.allItems.filter((item) => matchesFilters(item)).length;
    const requiredStates = state.view === 'accounting'
      ? ['Pendente', 'Validado']
      : ['OK', 'Ação', 'Bloqueio'];

    requiredStates.forEach((value) => stateCounts.set(value, 0));
    statePopulation.forEach((item) => {
      const businessState = String(item.business_state || '-');
      stateCounts.set(businessState, (stateCounts.get(businessState) || 0) + 1);
    });
    state.docTypes.forEach((item) => {
      const value = String(item.value || 'unknown');
      typeCounts.set(value, { count: 0, label: item.label || docTypeLabel(value) });
    });
    typePopulation.forEach((item) => {
      const documentType = String(item.doc_type || 'unknown');
      typeCounts.set(documentType, {
        count: (typeCounts.get(documentType)?.count || 0) + 1,
        label: item.doc_type_label || docTypeLabel(documentType),
      });
    });
    const orderedTypes = [...typeCounts.entries()].sort((left, right) =>
      String(left[1].label || '').localeCompare(String(right[1].label || ''), 'pt', { sensitivity: 'base' })
    );
    els.counts.innerHTML = `
      <div class="docai-business-count-group" aria-label="Filtros de estado">
        <span class="docai-business-count-title">Estado</span>
        <div class="docai-business-count-options">
          ${[...stateCounts.entries()].map(([value, count]) => `
            <button type="button" class="docai-business-count-chip ${state.stateFilters.has(value) ? 'is-active' : ''}"
                    data-count-filter="state" data-value="${escapeHtml(value)}">
              <span>${escapeHtml(value)}</span><strong>${count}</strong>
            </button>
          `).join('') || '<span class="sz_text_muted">Sem estados</span>'}
        </div>
      </div>
      <div class="docai-business-count-group" aria-label="Filtros de tipo">
        <span class="docai-business-count-title">Tipo</span>
        <div class="docai-business-count-options">
          ${orderedTypes.map(([value, data]) => `
            <button type="button" class="docai-business-count-chip ${state.typeFilters.has(value) ? 'is-active' : ''}"
                    data-count-filter="type" data-value="${escapeHtml(value)}">
              <span>${escapeHtml(data.label)}</span><strong>${data.count}</strong>
            </button>
          `).join('') || '<span class="sz_text_muted">Sem tipos</span>'}
        </div>
      </div>
      <button type="button" class="docai-count-card docai-count-card-action docai-filtered-total" data-action="reset-filters" title="Limpar filtros" aria-label="Mostrar todos os documentos e limpar filtros">
        <span class="count">${total}</span>
        <span class="label">Total</span>
      </button>
    `;
  }

  function applyFilters() {
    if (els.tableScroller) els.tableScroller.scrollTop = 0;
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
      state.permissions = payload.permissions || {};
      state.total = Number(payload.total || 0);
      if (allowedViews.has(payload.view)) state.view = payload.view;
      renderViewTabs();
      applyFilters();
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
    renderViewTabs();
    if (updateHistory) {
      const url = new URL(window.location.href);
      url.search = '';
      url.searchParams.set('view', view);
      window.history.pushState({ documentAiView: view }, '', url);
    }
    loadInbox();
  }

  function toggleArchive() {
    state.archived = !state.archived;
    resetFilters();
    renderViewTabs();
    loadInbox();
  }

  async function uploadDocument(file) {
    if (!file) return;
    const formData = new FormData();
    formData.append('file', file);
    formData.append('view', state.view);
    try {
      const payload = await fetchJson('/api/document_ai/documents/upload', { method: 'POST', body: formData });
      showMessage('Documento importado e processado.', 'success');
      window.location.href = analysisUrl(payload.id);
    } catch (error) {
      showMessage(error.message || 'Falha ao importar documento.', 'error');
    } finally {
      if (els.uploadInput) els.uploadInput.value = '';
    }
  }

  async function deleteDocument(id, fileName = '') {
    const label = fileName ? ` "${fileName}"` : '';
    if (!window.confirm(`Eliminar o documento${label} do inbox?`)) return;
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
    const target = filterButton.dataset.countFilter === 'state' ? state.stateFilters : state.typeFilters;
    const value = filterButton.dataset.value || '';
    target.has(value) ? target.delete(value) : target.add(value);
    applyFilters();
  });
  els.refreshBtn?.addEventListener('click', loadInbox);
  els.archiveBtn?.addEventListener('click', toggleArchive);
  els.uploadBtn?.addEventListener('click', () => els.uploadInput?.click());
  els.uploadInput?.addEventListener('change', (event) => uploadDocument(event.target.files?.[0]));
  els.viewTabs?.addEventListener('click', (event) => {
    if (availableViewButtons.length < 2) return;
    const view = event.target.closest('[data-view]')?.dataset.view;
    if (view) selectView(view);
  });
  els.inboxBody?.addEventListener('click', (event) => {
    const button = event.target.closest('button[data-action]');
    if (!button?.dataset.id) return;
    if (button.dataset.action === 'extract') window.location.href = analysisUrl(button.dataset.id);
    if (button.dataset.action === 'delete') deleteDocument(button.dataset.id, button.dataset.file || '');
  });
  window.addEventListener('popstate', () => {
    const requested = new URLSearchParams(window.location.search).get('view');
    const view = allowedViews.has(requested) ? requested : (availableViewButtons[0]?.dataset.view || '');
    if (view && view !== state.view) selectView(view, { updateHistory: false });
  });

  refreshColumnFilters();
  renderViewTabs();
  loadInbox();
});
