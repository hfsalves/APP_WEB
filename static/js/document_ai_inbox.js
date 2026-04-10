document.addEventListener('DOMContentLoaded', () => {
  const els = {
    search: document.getElementById('docAiSearch'),
    statusFilter: document.getElementById('docAiStatusFilter'),
    typeFilter: document.getElementById('docAiTypeFilter'),
    supplierFilter: document.getElementById('docAiSupplierFilter'),
    dateFrom: document.getElementById('docAiDateFrom'),
    dateTo: document.getElementById('docAiDateTo'),
    applyFilters: document.getElementById('docAiApplyFilters'),
    resetFilters: document.getElementById('docAiResetFilters'),
    counts: document.getElementById('docAiCounts'),
    inboxBody: document.getElementById('docAiInboxBody'),
    inboxMeta: document.getElementById('docAiInboxMeta'),
    inboxStatus: document.getElementById('docAiInboxStatus'),
    uploadBtn: document.getElementById('docAiUploadBtn'),
    uploadInput: document.getElementById('docAiUploadInput'),
    refreshBtn: document.getElementById('docAiRefreshBtn'),
    templatesBtn: document.getElementById('docAiTemplatesBtn'),
    openTemplatesBottom: document.getElementById('docAiOpenTemplatesBottom'),
  };

  const state = {
    items: [],
    statuses: [],
    docTypes: [],
    loading: false,
  };

  function showMessage(message, type = 'info') {
    if (typeof window.showToast === 'function') {
      window.showToast(message, type);
      return;
    }
    console[type === 'error' ? 'error' : 'log'](message);
  }

  function escapeHtml(value) {
    return String(value == null ? '' : value)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function formatDateTime(value) {
    if (!value) return 'n/a';
    const parsed = new Date(value);
    if (Number.isNaN(parsed.getTime())) return String(value);
    return new Intl.DateTimeFormat('pt-PT', { dateStyle: 'short', timeStyle: 'short' }).format(parsed);
  }

  function formatPct(value) {
    const numeric = Number(value || 0);
    return `${Math.round(numeric * 100)}%`;
  }

  function docTypeLabel(value) {
    const item = state.docTypes.find((entry) => entry.value === value);
    return item ? item.label : value || 'n/a';
  }

  function statusLabel(value) {
    const item = state.statuses.find((entry) => entry.value === value);
    return item ? item.label : value || 'n/a';
  }

  function extractionMethodLabel(value) {
    const mapping = {
      direct_pdf_text: 'Texto direto',
      ocr_image_fallback: 'OCR fallback',
      direct_image_ocr: 'OCR imagem',
      plain_text: 'Texto direto',
      failed: 'Falhou',
    };
    return mapping[String(value || '').trim()] || (value || 'n/a');
  }

  function setStatus(message, isError = false) {
    if (!els.inboxStatus) return;
    els.inboxStatus.textContent = message || '';
    els.inboxStatus.style.color = isError ? 'var(--sz-color-danger)' : '';
  }

  async function fetchJson(url, options = {}) {
    const response = await fetch(url, options);
    let payload = {};
    try {
      payload = await response.json();
    } catch (_) {}
    if (!response.ok) {
      throw new Error(payload.error || `HTTP ${response.status}`);
    }
    return payload;
  }

  function populateFilters() {
    if (els.statusFilter && !els.statusFilter.dataset.ready) {
      els.statusFilter.innerHTML = '<option value="">Todos</option>' + state.statuses.map((item) => (
        `<option value="${escapeHtml(item.value)}">${escapeHtml(item.label)}</option>`
      )).join('');
      els.statusFilter.dataset.ready = '1';
    }
    if (els.typeFilter && !els.typeFilter.dataset.ready) {
      els.typeFilter.innerHTML = '<option value="">Todos</option>' + state.docTypes.map((item) => (
        `<option value="${escapeHtml(item.value)}">${escapeHtml(item.label)}</option>`
      )).join('');
      els.typeFilter.dataset.ready = '1';
    }
  }

  function renderCounts(counts = {}) {
    if (!els.counts) return;
    const total = state.items.length;
    const cards = [`<div class="docai-count-card"><div class="count">${total}</div><div class="label">Total</div></div>`];
    state.statuses.forEach((status) => {
      cards.push(`
        <div class="docai-count-card">
          <div class="count">${Number(counts[status.value] || 0)}</div>
          <div class="label">${escapeHtml(status.label)}</div>
        </div>
      `);
    });
    els.counts.innerHTML = cards.join('');
  }

  function renderTable() {
    if (!els.inboxBody) return;
    if (!state.items.length) {
      els.inboxBody.innerHTML = '<tr><td colspan="10" class="sz_text_muted">Sem documentos para os filtros atuais.</td></tr>';
      return;
    }
    els.inboxBody.innerHTML = state.items.map((item) => `
      <tr>
        <td>
          <div><strong>${escapeHtml(item.file_name)}</strong></div>
          <div class="sz_text_muted">${escapeHtml(item.file_ext || item.mime_type || '')}</div>
        </td>
        <td>${escapeHtml(item.supplier_name || (item.supplier_no ? `#${item.supplier_no}` : 'n/a'))}</td>
        <td>${escapeHtml(docTypeLabel(item.doc_type))}</td>
        <td>${escapeHtml(item.template_name || 'n/a')}</td>
        <td>${escapeHtml(formatPct(item.confidence))}</td>
        <td>
          <div class="docai-pipeline-stack">
            <span class="docai-pipeline-badge method-${escapeHtml(item.extraction_method || 'failed')}">${escapeHtml(extractionMethodLabel(item.extraction_method))}</span>
            <span class="sz_text_muted">${escapeHtml(formatPct(item.extraction_quality_score || 0))}</span>
          </div>
        </td>
        <td><span class="docai-state-badge status-${escapeHtml(item.status)}">${escapeHtml(statusLabel(item.status))}</span></td>
        <td>${escapeHtml(formatDateTime(item.created_at))}</td>
        <td>${escapeHtml(formatDateTime(item.processed_at))}</td>
        <td>
          <div class="docai-row-actions">
            <button type="button" class="sz_button sz_button_ghost" data-action="open" data-id="${escapeHtml(item.id)}" title="Abrir">
              <i class="fa-solid fa-folder-open"></i>
            </button>
            <button type="button" class="sz_button sz_button_ghost" data-action="reprocess" data-id="${escapeHtml(item.id)}" title="Reprocessar">
              <i class="fa-solid fa-rotate"></i>
            </button>
            <button type="button" class="sz_button sz_button_ghost" data-action="template" data-id="${escapeHtml(item.id)}" title="Modelos">
              <i class="fa-solid fa-layer-group"></i>
            </button>
          </div>
        </td>
      </tr>
    `).join('');
  }

  async function loadInbox() {
    if (state.loading) return;
    state.loading = true;
    setStatus('A carregar documentos...');
    if (els.inboxMeta) els.inboxMeta.textContent = 'A carregar documentos...';
    try {
      const params = new URLSearchParams();
      if (els.search?.value.trim()) params.set('search', els.search.value.trim());
      if (els.statusFilter?.value) params.set('status', els.statusFilter.value);
      if (els.typeFilter?.value) params.set('doc_type', els.typeFilter.value);
      if (els.supplierFilter?.value.trim()) params.set('supplier', els.supplierFilter.value.trim());
      if (els.dateFrom?.value) params.set('date_from', els.dateFrom.value);
      if (els.dateTo?.value) params.set('date_to', els.dateTo.value);
      const payload = await fetchJson(`/api/document_ai/inbox?${params.toString()}`);
      state.items = Array.isArray(payload.items) ? payload.items : [];
      state.statuses = Array.isArray(payload.statuses) ? payload.statuses : [];
      state.docTypes = Array.isArray(payload.doc_types) ? payload.doc_types : [];
      populateFilters();
      renderCounts(payload.counts || {});
      renderTable();
      if (els.inboxMeta) els.inboxMeta.textContent = `${state.items.length} documento(s) carregado(s).`;
      setStatus('Inbox atualizada.');
    } catch (error) {
      console.error(error);
      if (els.inboxBody) els.inboxBody.innerHTML = `<tr><td colspan="10" class="sz_text_muted">${escapeHtml(error.message)}</td></tr>`;
      if (els.inboxMeta) els.inboxMeta.textContent = 'Erro ao carregar a inbox.';
      setStatus(error.message || 'Erro ao carregar.', true);
    } finally {
      state.loading = false;
    }
  }

  async function uploadDocument(file) {
    if (!file) return;
    const formData = new FormData();
    formData.append('file', file);
    setStatus(`A importar ${file.name}...`);
    try {
      const payload = await fetchJson('/api/document_ai/documents/upload', { method: 'POST', body: formData });
      showMessage('Documento importado e processado.', 'success');
      window.location.href = `/document_ai/review/${encodeURIComponent(payload.id)}`;
    } catch (error) {
      console.error(error);
      showMessage(error.message || 'Falha ao importar documento.', 'error');
      setStatus(error.message || 'Falha ao importar.', true);
    } finally {
      if (els.uploadInput) els.uploadInput.value = '';
    }
  }

  async function reprocessDocument(id) {
    setStatus('A reprocessar documento...');
    try {
      await fetchJson(`/api/document_ai/documents/${encodeURIComponent(id)}/reprocess`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({}),
      });
      showMessage('Documento reprocessado.', 'success');
      loadInbox();
    } catch (error) {
      console.error(error);
      showMessage(error.message || 'Falha ao reprocessar.', 'error');
      setStatus(error.message || 'Falha ao reprocessar.', true);
    }
  }

  function openTemplates() {
    window.location.href = '/document_ai/templates';
  }

  els.applyFilters?.addEventListener('click', loadInbox);
  els.resetFilters?.addEventListener('click', () => {
    [els.search, els.statusFilter, els.typeFilter, els.supplierFilter, els.dateFrom, els.dateTo].forEach((el) => {
      if (el) el.value = '';
    });
    loadInbox();
  });
  els.refreshBtn?.addEventListener('click', loadInbox);
  els.templatesBtn?.addEventListener('click', openTemplates);
  els.openTemplatesBottom?.addEventListener('click', openTemplates);
  els.uploadBtn?.addEventListener('click', () => els.uploadInput?.click());
  els.uploadInput?.addEventListener('change', (event) => uploadDocument(event.target.files?.[0]));
  els.inboxBody?.addEventListener('click', (event) => {
    const button = event.target.closest('button[data-action]');
    if (!button) return;
    const action = button.dataset.action;
    const id = button.dataset.id;
    if (!id) return;
    if (action === 'open') {
      window.location.href = `/document_ai/review/${encodeURIComponent(id)}`;
      return;
    }
    if (action === 'reprocess') {
      reprocessDocument(id);
      return;
    }
    if (action === 'template') {
      openTemplates();
    }
  });

  loadInbox();
});
