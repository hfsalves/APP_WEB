document.addEventListener('DOMContentLoaded', () => {
  const els = {
    backBtn: document.getElementById('docAiExtractBackBtn'),
    resetBtn: document.getElementById('docAiExtractResetBtn'),
    input: document.getElementById('docAiExtractInput'),
    chooseBtn: document.getElementById('docAiExtractChooseBtn'),
    runBtn: document.getElementById('docAiExtractRunBtn'),
    dropzone: document.getElementById('docAiExtractDropzone'),
    preview: document.getElementById('docAiExtractPreview'),
    previewFrame: document.getElementById('docAiExtractPreviewFrame'),
    fileMeta: document.getElementById('docAiExtractFileMeta'),
    resultMeta: document.getElementById('docAiExtractResultMeta'),
    confidence: document.getElementById('docAiExtractConfidence'),
    empty: document.getElementById('docAiExtractEmpty'),
    loading: document.getElementById('docAiExtractLoading'),
    results: document.getElementById('docAiExtractResults'),
    status: document.getElementById('docAiExtractStatus'),
    customerName: document.getElementById('docAiExtractCustomerName'),
    customerTax: document.getElementById('docAiExtractCustomerTax'),
    supplierName: document.getElementById('docAiExtractSupplierName'),
    supplierTax: document.getElementById('docAiExtractSupplierTax'),
    supplierNo: document.getElementById('docAiExtractSupplierNo'),
    supplierCard: document.getElementById('docAiExtractSupplierCard'),
    supplierHint: document.getElementById('docAiExtractSupplierHint'),
    documentTitle: document.getElementById('docAiExtractDocumentTitle'),
    documentDate: document.getElementById('docAiExtractDocumentDate'),
    lineCount: document.getElementById('docAiExtractLineCount'),
    linesBody: document.getElementById('docAiExtractLinesBody'),
    taxesBody: document.getElementById('docAiExtractTaxesBody'),
    netTotal: document.getElementById('docAiExtractNetTotal'),
    taxTotal: document.getElementById('docAiExtractTaxTotal'),
    grossTotal: document.getElementById('docAiExtractGrossTotal'),
    notesSection: document.getElementById('docAiExtractNotesSection'),
    notes: document.getElementById('docAiExtractNotes'),
    batchAlert: document.getElementById('docAiExtractBatchAlert'),
    batchMessage: document.getElementById('docAiExtractBatchMessage'),
    batchDocuments: document.getElementById('docAiExtractBatchDocuments'),
    splitBtn: document.getElementById('docAiExtractSplitBtn'),
    groupNavigator: document.getElementById('docAiExtractGroupNavigator'),
    groupPrevious: document.getElementById('docAiExtractGroupPrevious'),
    groupNext: document.getElementById('docAiExtractGroupNext'),
    groupPosition: document.getElementById('docAiExtractGroupPosition'),
    groupFileName: document.getElementById('docAiExtractGroupFileName'),
    supplierModal: document.getElementById('docAiSupplierMatchModal'),
    supplierModalContext: document.getElementById('docAiSupplierMatchContext'),
    supplierModalSearch: document.getElementById('docAiSupplierMatchSearch'),
    supplierModalSearchBtn: document.getElementById('docAiSupplierMatchSearchBtn'),
    supplierModalList: document.getElementById('docAiSupplierMatchList'),
    supplierModalCloseTop: document.getElementById('docAiSupplierMatchCloseTop'),
    supplierModalClose: document.getElementById('docAiSupplierMatchClose'),
  };

  const state = {
    file: null,
    previewUrl: '',
    loading: false,
    documentData: null,
    matching: {},
    supplierCandidates: [],
    currentDocumentId: '',
    group: null,
    groupIndex: 0,
    splitting: false,
  };

  const typeLabels = {
    invoice: 'Fatura',
    credit_note: 'Nota de crédito',
    debit_note: 'Nota de débito',
    purchase_order: 'Nota de encomenda',
    delivery_note: 'Guia',
    proforma_invoice: 'Fatura pró-forma',
    receipt: 'Recibo',
    unknown: 'Tipo desconhecido',
    other: 'Outro documento',
  };

  function escapeHtml(value) {
    return String(value == null ? '' : value)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function setStatus(message, isError = false) {
    els.status.textContent = message || '';
    els.status.style.color = isError ? 'var(--sz-color-danger)' : '';
  }

  function showMessage(message, type = 'info') {
    if (typeof window.showToast === 'function') {
      window.showToast(message, type);
    }
  }

  function formatFileSize(bytes) {
    const size = Number(bytes || 0);
    if (size < 1024 * 1024) return `${Math.max(1, Math.round(size / 1024))} KB`;
    return `${(size / (1024 * 1024)).toFixed(1)} MB`;
  }

  function formatNumber(value, maximumFractionDigits = 3) {
    const number = Number(value || 0);
    return new Intl.NumberFormat('pt-PT', { maximumFractionDigits }).format(number);
  }

  function formatMoney(value, currency) {
    const number = Number(value || 0);
    const normalizedCurrency = String(currency || '').trim().toUpperCase();
    if (/^[A-Z]{3}$/.test(normalizedCurrency)) {
      try {
        return new Intl.NumberFormat('pt-PT', {
          style: 'currency',
          currency: normalizedCurrency,
          minimumFractionDigits: 2,
        }).format(number);
      } catch (_) {}
    }
    return `${formatNumber(number, 2)}${normalizedCurrency ? ` ${normalizedCurrency}` : ''}`;
  }

  function formatDate(value) {
    const raw = String(value || '').trim();
    if (!raw) return '--';
    const match = raw.match(/^(\d{4})-(\d{2})-(\d{2})$/);
    return match ? `${match[3]}/${match[2]}/${match[1]}` : raw;
  }

  function cleanupPreview() {
    if (state.previewUrl) URL.revokeObjectURL(state.previewUrl);
    state.previewUrl = '';
    els.previewFrame.removeAttribute('src');
  }

  function setFile(file, options = {}) {
    if (!file) return;
    if (file.type !== 'application/pdf' && !file.name.toLowerCase().endsWith('.pdf')) {
      showMessage('Seleciona um ficheiro PDF.', 'error');
      setStatus('Formato não suportado.', true);
      return;
    }
    if (file.size > 50 * 1024 * 1024) {
      showMessage('O PDF excede o limite de 50 MB.', 'error');
      setStatus('Ficheiro demasiado grande.', true);
      return;
    }

    cleanupPreview();
    state.file = file;
    state.previewUrl = URL.createObjectURL(file);
    els.previewFrame.src = state.previewUrl;
    els.preview.hidden = false;
    els.dropzone.hidden = true;
    els.runBtn.disabled = false;
    els.resetBtn.disabled = false;
    els.fileMeta.textContent = `${file.name} · ${formatFileSize(file.size)}`;
    setStatus(options.autoExtract === false ? 'PDF pronto para leitura.' : 'PDF pronto; a iniciar leitura automática...');
    if (options.autoExtract !== false) {
      window.setTimeout(() => extractDocument(), 0);
    }
  }

  function resetScreen() {
    cleanupPreview();
    state.file = null;
    state.loading = false;
    state.documentData = null;
    state.matching = {};
    state.supplierCandidates = [];
    state.currentDocumentId = '';
    state.group = null;
    state.groupIndex = 0;
    state.splitting = false;
    els.input.value = '';
    els.preview.hidden = true;
    els.dropzone.hidden = false;
    els.runBtn.disabled = true;
    els.resetBtn.disabled = true;
    els.empty.hidden = false;
    els.empty.querySelector('strong').textContent = 'Nenhum documento analisado';
    els.empty.querySelector('span').textContent = 'Carrega um PDF para identificar cliente, fornecedor, cabeçalho, linhas, IVA e totais.';
    els.loading.hidden = true;
    els.results.hidden = true;
    els.confidence.hidden = true;
    els.fileMeta.textContent = 'Seleciona um PDF até 50 MB.';
    els.resultMeta.textContent = 'Os resultados aparecem aqui depois da leitura.';
    els.groupNavigator.hidden = true;
    window.history.replaceState({}, '', '/document_ai/extract');
    setStatus('Pronto.');
  }

  async function fetchJson(url, options = {}) {
    const response = await fetch(url, options);
    let payload = {};
    try {
      payload = await response.json();
    } catch (_) {}
    if (!response.ok) throw new Error(payload.error || `HTTP ${response.status}`);
    return payload;
  }

  function fileNameFromDisposition(value) {
    const header = String(value || '');
    const encodedMatch = header.match(/filename\*=UTF-8''([^;]+)/i);
    if (encodedMatch) {
      try {
        return decodeURIComponent(encodedMatch[1]);
      } catch (_) {}
    }
    const quotedMatch = header.match(/filename="([^"]+)"/i);
    if (quotedMatch) return quotedMatch[1];
    const plainMatch = header.match(/filename=([^;]+)/i);
    return plainMatch ? plainMatch[1].trim() : '';
  }

  function clearCurrentAnalysis() {
    state.documentData = null;
    state.matching = {};
    state.supplierCandidates = [];
    els.results.hidden = true;
    els.confidence.hidden = true;
    els.batchAlert.hidden = true;
    els.empty.hidden = false;
    els.empty.querySelector('strong').textContent = 'A iniciar leitura automática';
    els.empty.querySelector('span').textContent = 'O PDF será enviado ao LLM assim que ficar carregado.';
    els.resultMeta.textContent = 'A preparar o documento selecionado para leitura automática.';
  }

  function renderGroupNavigator() {
    const documents = Array.isArray(state.group?.documents) ? state.group.documents : [];
    const grouped = documents.length > 0;
    els.groupNavigator.hidden = !grouped;
    if (!grouped) return;
    state.groupIndex = Math.max(0, Math.min(state.groupIndex, documents.length - 1));
    const current = documents[state.groupIndex] || {};
    els.groupPosition.textContent = `Documento ${state.groupIndex + 1} de ${documents.length}`;
    els.groupFileName.textContent = current.file_name || '';
    els.groupPrevious.disabled = state.groupIndex <= 0;
    els.groupNext.disabled = state.groupIndex >= documents.length - 1;
  }

  function applyDocumentGroup(group, currentDocumentId = '') {
    const documents = Array.isArray(group?.documents) ? group.documents : [];
    state.group = documents.length ? group : null;
    const currentIndex = documents.findIndex((item) => item.id === currentDocumentId);
    state.groupIndex = currentIndex >= 0 ? currentIndex : Number(group?.current_index || 0);
    renderGroupNavigator();
  }

  async function loadDocumentGroup(documentId) {
    try {
      const group = await fetchJson(`/api/document_ai/documents/${encodeURIComponent(documentId)}/group`);
      applyDocumentGroup(group, documentId);
    } catch (error) {
      console.warn('Não foi possível carregar o grupo documental.', error);
    }
  }

  async function loadInboxDocument(documentId, options = {}) {
    if (!documentId) return;
    state.currentDocumentId = documentId;
    els.dropzone.hidden = true;
    els.empty.hidden = true;
    els.loading.hidden = false;
    els.loading.querySelector('strong').textContent = 'A carregar documento do inbox...';
    els.loading.querySelector('span').textContent = 'O PDF será enviado automaticamente ao LLM.';
    els.fileMeta.textContent = 'A carregar PDF original...';
    setStatus('A carregar documento do inbox...');
    try {
      const response = await fetch(`/api/document_ai/documents/${encodeURIComponent(documentId)}/original`);
      if (!response.ok) {
        let message = `HTTP ${response.status}`;
        try {
          const payload = await response.json();
          message = payload.error || message;
        } catch (_) {}
        throw new Error(message);
      }
      const blob = await response.blob();
      const fileName = fileNameFromDisposition(response.headers.get('Content-Disposition')) || `documento-${documentId}.pdf`;
      const file = new File([blob], fileName, { type: blob.type || 'application/pdf' });
      setFile(file);
      els.loading.hidden = true;
      els.empty.hidden = false;
      els.empty.querySelector('strong').textContent = 'Leitura automática iniciada';
      els.empty.querySelector('span').textContent = 'O documento foi enviado ao LLM.';
      els.resultMeta.textContent = 'PDF carregado a partir do inbox; leitura LLM iniciada automaticamente.';
      setStatus('Documento do inbox enviado automaticamente ao LLM.');
      window.history.replaceState({}, '', `/document_ai/extract?document_id=${encodeURIComponent(documentId)}`);
      if (!options.skipGroup) await loadDocumentGroup(documentId);
      renderGroupNavigator();
    } catch (error) {
      console.error(error);
      els.loading.hidden = true;
      els.empty.hidden = false;
      els.dropzone.hidden = false;
      els.empty.querySelector('strong').textContent = 'Não foi possível carregar o documento';
      els.empty.querySelector('span').textContent = error.message || 'Seleciona o PDF manualmente.';
      els.fileMeta.textContent = 'Seleciona um PDF até 50 MB.';
      setStatus(error.message || 'Falha ao carregar documento.', true);
      showMessage(error.message || 'Falha ao carregar documento do inbox.', 'error');
    }
  }

  async function openGroupDocument(index) {
    const documents = Array.isArray(state.group?.documents) ? state.group.documents : [];
    const nextIndex = Math.max(0, Math.min(Number(index || 0), documents.length - 1));
    const target = documents[nextIndex];
    if (!target || target.id === state.currentDocumentId) {
      state.groupIndex = nextIndex;
      renderGroupNavigator();
      return;
    }
    state.groupIndex = nextIndex;
    clearCurrentAnalysis();
    renderGroupNavigator();
    await loadInboxDocument(target.id, { skipGroup: true });
    renderGroupNavigator();
  }

  function renderLines(lines, currency) {
    const items = Array.isArray(lines) ? lines : [];
    els.lineCount.textContent = `${items.length} linha(s)`;
    if (!items.length) {
      els.linesBody.innerHTML = '<tr><td colspan="9" class="sz_text_muted">Não foram encontradas linhas comerciais visíveis.</td></tr>';
      return;
    }
    els.linesBody.innerHTML = items.map((line) => `
      <tr>
        <td>${escapeHtml(line.ref || '--')}</td>
        <td class="docai-extract-description">${escapeHtml(line.description || '--')}</td>
        <td class="docai-extract-number">${escapeHtml(formatNumber(line.qty))}</td>
        <td>${escapeHtml(line.unit || '--')}</td>
        <td class="docai-extract-number">${escapeHtml(formatMoney(line.unit_price, currency))}</td>
        <td class="docai-extract-number">${escapeHtml(`${formatNumber(line.discount, 2)}%`)}</td>
        <td class="docai-extract-number">${escapeHtml(`${formatNumber(line.tax_rate, 2)}%`)}</td>
        <td class="docai-extract-number">${escapeHtml(formatMoney(line.net_amount, currency))}</td>
        <td class="docai-extract-number">${escapeHtml(formatMoney(line.gross_amount, currency))}</td>
      </tr>
    `).join('');
  }

  function renderTaxes(taxes, currency) {
    const items = Array.isArray(taxes) ? taxes : [];
    if (!items.length) {
      els.taxesBody.innerHTML = '<tr><td colspan="4" class="sz_text_muted">Sem discriminação de IVA visível.</td></tr>';
      return;
    }
    els.taxesBody.innerHTML = items.map((tax) => `
      <tr>
        <td>${escapeHtml(`${formatNumber(tax.tax_rate, 2)}%`)}</td>
        <td class="docai-extract-number">${escapeHtml(formatMoney(tax.taxable_base, currency))}</td>
        <td class="docai-extract-number">${escapeHtml(formatMoney(tax.tax_amount, currency))}</td>
        <td class="docai-extract-number">${escapeHtml(formatMoney(tax.gross_total, currency))}</td>
      </tr>
    `).join('');
  }

  function renderSupplierCard(supplier = {}, matching = {}) {
    const supplierNo = Number(supplier.supplier_no || supplier.no || 0);
    const matched = Boolean(supplierNo);
    els.supplierName.textContent = supplier.name || supplier.llm_name || '--';
    els.supplierTax.textContent = supplier.tax_id ? `NIF/NCONT: ${supplier.tax_id}` : 'NIF/NCONT não identificado';
    els.supplierNo.textContent = `Nº fornecedor: ${supplierNo || '--'}`;
    els.supplierCard.classList.toggle('is-unmatched', !matched);
    els.supplierCard.classList.toggle('is-matched', matched);
    els.supplierHint.innerHTML = matched
      ? '<i class="fa-solid fa-pen"></i> Alterar fornecedor'
      : '<i class="fa-solid fa-hand-pointer"></i> Escolher fornecedor semelhante';
    els.supplierCard.setAttribute('aria-label', matched ? 'Alterar fornecedor' : 'Escolher fornecedor semelhante');
    if (!matching?.supplier_query?.feid) {
      els.supplierHint.innerHTML = '<i class="fa-solid fa-triangle-exclamation"></i> Empresa cliente não identificada na FE';
    } else if (matching?.supplier_lookup_error) {
      els.supplierHint.innerHTML = '<i class="fa-solid fa-triangle-exclamation"></i> Não foi possível consultar a FL';
    }
  }

  function renderDocumentBatch(batch = {}) {
    const documents = Array.isArray(batch.documents) ? batch.documents : [];
    const multiple = Boolean(batch.contains_multiple_documents && documents.length > 1);
    els.batchAlert.hidden = !multiple;
    if (!multiple) {
      els.batchMessage.textContent = '';
      els.batchDocuments.innerHTML = '';
      return;
    }
    els.batchMessage.textContent = batch.message || `Foram detetados ${documents.length} documentos neste PDF.`;
    els.splitBtn.disabled = state.splitting;
    els.batchDocuments.innerHTML = documents.map((item, index) => {
      const typeLabel = typeLabels[item.document_type] || item.document_type || typeLabels.unknown;
      const startPage = Number(item.start_page || 1);
      const endPage = Number(item.end_page || startPage);
      const pagesLabel = startPage === endPage ? `Página ${startPage}` : `Páginas ${startPage}–${endPage}`;
      const confidence = Math.round(Math.max(0, Math.min(1, Number(item.confidence || 0))) * 100);
      return `
        <article class="docai-extract-batch-document">
          <span class="docai-extract-batch-index">${index + 1}</span>
          <span class="docai-extract-batch-main">
            <strong>${escapeHtml(typeLabel)}${item.document_number ? ` · ${escapeHtml(item.document_number)}` : ''}</strong>
            <span>${escapeHtml(pagesLabel)} · começa na página ${startPage}</span>
          </span>
          <span class="docai-extract-batch-confidence">${confidence}%</span>
        </article>
      `;
    }).join('');
  }

  async function splitDocumentBatch() {
    const batch = state.documentData?.document_batch || {};
    const documents = Array.isArray(batch.documents) ? batch.documents : [];
    if (!state.file || !batch.contains_multiple_documents || documents.length < 2 || state.splitting) return;
    state.splitting = true;
    els.splitBtn.disabled = true;
    els.runBtn.disabled = true;
    els.resetBtn.disabled = true;
    setStatus(`A separar ${documents.length} documentos e a criar o grupo no inbox...`);
    const formData = new FormData();
    formData.append('file', state.file);
    formData.append('document_batch', JSON.stringify(batch));
    formData.append('document_data', JSON.stringify(state.documentData || {}));
    formData.append('source_document_id', state.currentDocumentId || '');
    try {
      const payload = await fetchJson('/api/document_ai/extract/split', { method: 'POST', body: formData });
      const group = payload.group || {};
      applyDocumentGroup(group);
      setStatus(payload.message || 'Documentos separados e adicionados ao inbox.');
      showMessage(payload.message || 'Documentos separados com sucesso.', 'success');
      await openGroupDocument(0);
    } catch (error) {
      console.error(error);
      setStatus(error.message || 'Não foi possível separar o PDF.', true);
      showMessage(error.message || 'Não foi possível separar o PDF.', 'error');
    } finally {
      state.splitting = false;
      els.splitBtn.disabled = false;
      els.runBtn.disabled = state.loading || !state.file;
      els.resetBtn.disabled = !state.file;
    }
  }

  function closeSupplierModal() {
    els.supplierModal.classList.remove('sz_is_open');
    els.supplierModal.setAttribute('aria-hidden', 'true');
  }

  function renderSupplierCandidates(items) {
    state.supplierCandidates = Array.isArray(items) ? items : [];
    if (!state.supplierCandidates.length) {
      els.supplierModalList.innerHTML = '<div class="docai-empty-state">Não foram encontrados fornecedores semelhantes nesta empresa.</div>';
      return;
    }
    els.supplierModalList.innerHTML = state.supplierCandidates.map((item, index) => {
      const score = Math.round(Math.max(0, Math.min(1, Number(item.score || 0))) * 100);
      const taxLabel = String(item.tax_field || 'nif').toUpperCase();
      const matchLabel = item.matched_by === 'tax_id' ? `${taxLabel} coincidente` : 'Nome semelhante';
      return `
        <button type="button" class="docai-supplier-match-option" data-supplier-index="${index}">
          <span class="docai-supplier-match-main">
            <strong>${escapeHtml(item.name || '--')}</strong>
            <span>Nº ${escapeHtml(item.no || '--')} · ${escapeHtml(taxLabel)} ${escapeHtml(item.tax_id || '--')}</span>
          </span>
          <span class="docai-supplier-match-score">${escapeHtml(matchLabel)} · ${score}%</span>
        </button>
      `;
    }).join('');
  }

  function openSupplierModal() {
    const feid = Number(state.matching?.supplier_query?.feid || state.documentData?.customer?.feid || 0);
    if (!feid) {
      showMessage('Não foi possível identificar a empresa cliente na tabela FE.', 'error');
      return;
    }
    const customerName = state.documentData?.customer?.name || `FE ${feid}`;
    const supplier = state.documentData?.supplier || {};
    els.supplierModalContext.textContent = `Fornecedores de ${customerName} · FEID ${feid}`;
    els.supplierModalSearch.value = supplier.llm_name || supplier.name || supplier.llm_tax_id || supplier.tax_id || '';
    renderSupplierCandidates(state.matching?.supplier_candidates || []);
    els.supplierModal.classList.add('sz_is_open');
    els.supplierModal.setAttribute('aria-hidden', 'false');
    window.setTimeout(() => els.supplierModalSearch.focus(), 50);
  }

  async function searchSupplierCandidates() {
    const feid = Number(state.matching?.supplier_query?.feid || state.documentData?.customer?.feid || 0);
    const query = els.supplierModalSearch.value.trim();
    if (!feid || query.length < 2) {
      showMessage('Indica pelo menos dois caracteres para pesquisar.', 'error');
      return;
    }
    els.supplierModalSearchBtn.disabled = true;
    els.supplierModalList.innerHTML = '<div class="docai-empty-state">A procurar fornecedores semelhantes...</div>';
    try {
      const params = new URLSearchParams({ q: query, feid: String(feid), limit: '12' });
      const items = await fetchJson(`/api/document_ai/suppliers/search?${params.toString()}`);
      renderSupplierCandidates(items);
    } catch (error) {
      els.supplierModalList.innerHTML = `<div class="docai-empty-state">${escapeHtml(error.message || 'Erro na pesquisa.')}</div>`;
    } finally {
      els.supplierModalSearchBtn.disabled = false;
    }
  }

  function selectSupplier(index) {
    const selected = state.supplierCandidates[index];
    if (!selected || !state.documentData) return;
    const current = state.documentData.supplier || {};
    state.documentData.supplier = {
      ...current,
      supplier_no: selected.no,
      name: selected.name || current.name || '',
      tax_id: selected.tax_id || current.tax_id || '',
      feid: selected.feid || state.documentData.customer?.feid || null,
      match_score: selected.score || 0,
      matched_by: selected.matched_by || 'manual',
      manually_selected: true,
    };
    state.matching.supplier_matched = true;
    state.matching.supplier_needs_selection = false;
    renderSupplierCard(state.documentData.supplier, state.matching);
    closeSupplierModal();
    setStatus(`Fornecedor ${selected.name} (#${selected.no}) selecionado.`);
    showMessage('Fornecedor selecionado.', 'success');
  }

  function renderResult(payload) {
    const documentData = payload.document || {};
    const customer = documentData.customer || {};
    const supplier = documentData.supplier || {};
    const totals = documentData.totals || {};
    const currency = documentData.currency || '';
    const docType = typeLabels[documentData.document_type] || documentData.document_type || typeLabels.unknown;

    state.documentData = documentData;
    state.matching = payload.matching || {};
    state.supplierCandidates = state.matching.supplier_candidates || [];
    renderDocumentBatch(documentData.document_batch || {});
    els.customerName.textContent = customer.name || '--';
    els.customerTax.textContent = customer.tax_id ? `NIF: ${customer.tax_id}` : 'NIF não identificado';
    renderSupplierCard(supplier, state.matching);
    els.documentTitle.textContent = `${docType}${documentData.document_number ? ` · ${documentData.document_number}` : ''}`;
    els.documentDate.textContent = `Data: ${formatDate(documentData.document_date)}${documentData.due_date ? ` · Vencimento: ${formatDate(documentData.due_date)}` : ''}`;

    renderLines(documentData.lines, currency);
    renderTaxes(documentData.taxes, currency);
    els.netTotal.textContent = formatMoney(totals.net_total, currency);
    els.taxTotal.textContent = formatMoney(totals.tax_total, currency);
    els.grossTotal.textContent = formatMoney(totals.gross_total, currency);

    const notes = Array.isArray(documentData.notes) ? documentData.notes.filter(Boolean) : [];
    els.notesSection.hidden = !notes.length;
    els.notes.innerHTML = notes.map((note) => `<li>${escapeHtml(note)}</li>`).join('');

    const confidence = Math.max(0, Math.min(1, Number(documentData.confidence || 0)));
    els.confidence.innerHTML = `<i class="fa-solid fa-circle-check"></i><span>${Math.round(confidence * 100)}% confiança</span>`;
    els.confidence.className = `docai-status-chip ${confidence >= 0.75 ? 'status-parsed_ok' : 'status-review_required'}`;
    els.confidence.hidden = false;
    const batch = documentData.document_batch || {};
    const batchSuffix = batch.contains_multiple_documents
      ? ` · ${Number(batch.document_count || 0)} documentos em ${Number(batch.page_count || 0)} páginas`
      : '';
    els.resultMeta.textContent = `Leitura concluída com ${payload.model || 'LLM'} · ${documentData.visible_language || 'idioma não identificado'}${batchSuffix}`;
    els.empty.hidden = true;
    els.loading.hidden = true;
    els.results.hidden = false;
  }

  async function extractDocument() {
    if (!state.file || state.loading) return;
    state.loading = true;
    els.runBtn.disabled = true;
    els.resetBtn.disabled = true;
    els.empty.hidden = true;
    els.results.hidden = true;
    els.confidence.hidden = true;
    els.loading.hidden = false;
    els.resultMeta.textContent = 'A analisar o documento completo...';
    setStatus('A enviar e ler o PDF com o LLM...');

    const formData = new FormData();
    formData.append('file', state.file);
    try {
      const payload = await fetchJson('/api/document_ai/extract', { method: 'POST', body: formData });
      renderResult(payload);
      const batch = payload.document?.document_batch || {};
      if (batch.contains_multiple_documents) {
        setStatus(batch.message || 'Foram encontrados vários documentos no PDF.');
        showMessage(`${batch.document_count} documentos encontrados.`, 'warning');
      } else {
        setStatus('Leitura concluída.');
        showMessage('Documento lido com sucesso.', 'success');
      }
    } catch (error) {
      console.error(error);
      els.loading.hidden = true;
      els.empty.hidden = false;
      els.empty.querySelector('strong').textContent = 'Não foi possível ler o documento';
      els.empty.querySelector('span').textContent = error.message || 'O LLM não devolveu uma resposta utilizável.';
      els.resultMeta.textContent = 'Erro na leitura do documento.';
      setStatus(error.message || 'Falha na leitura.', true);
      showMessage(error.message || 'Falha na leitura do documento.', 'error');
    } finally {
      state.loading = false;
      els.runBtn.disabled = !state.file;
      els.resetBtn.disabled = !state.file;
    }
  }

  els.backBtn?.addEventListener('click', () => { window.location.href = '/document_ai/inbox'; });
  els.resetBtn?.addEventListener('click', resetScreen);
  els.chooseBtn?.addEventListener('click', (event) => {
    event.stopPropagation();
    els.input?.click();
  });
  els.dropzone?.addEventListener('click', () => els.input?.click());
  els.dropzone?.addEventListener('keydown', (event) => {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      els.input?.click();
    }
  });
  els.input?.addEventListener('change', (event) => setFile(event.target.files?.[0]));
  ['dragenter', 'dragover'].forEach((eventName) => {
    els.dropzone?.addEventListener(eventName, (event) => {
      event.preventDefault();
      els.dropzone.classList.add('is-dragover');
    });
  });
  ['dragleave', 'drop'].forEach((eventName) => {
    els.dropzone?.addEventListener(eventName, (event) => {
      event.preventDefault();
      els.dropzone.classList.remove('is-dragover');
    });
  });
  els.dropzone?.addEventListener('drop', (event) => setFile(event.dataTransfer?.files?.[0]));
  els.runBtn?.addEventListener('click', extractDocument);
  els.splitBtn?.addEventListener('click', splitDocumentBatch);
  els.groupPrevious?.addEventListener('click', () => {
    if (!state.loading && !state.splitting) openGroupDocument(state.groupIndex - 1);
  });
  els.groupNext?.addEventListener('click', () => {
    if (!state.loading && !state.splitting) openGroupDocument(state.groupIndex + 1);
  });
  els.supplierCard?.addEventListener('click', openSupplierModal);
  els.supplierCard?.addEventListener('keydown', (event) => {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      openSupplierModal();
    }
  });
  els.supplierModalSearchBtn?.addEventListener('click', searchSupplierCandidates);
  els.supplierModalSearch?.addEventListener('keydown', (event) => {
    if (event.key === 'Enter') searchSupplierCandidates();
  });
  els.supplierModalCloseTop?.addEventListener('click', closeSupplierModal);
  els.supplierModalClose?.addEventListener('click', closeSupplierModal);
  els.supplierModal?.addEventListener('click', (event) => {
    if (event.target === els.supplierModal) closeSupplierModal();
  });
  els.supplierModalList?.addEventListener('click', (event) => {
    const option = event.target.closest('[data-supplier-index]');
    if (!option) return;
    selectSupplier(Number(option.dataset.supplierIndex));
  });
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && els.supplierModal?.classList.contains('sz_is_open')) closeSupplierModal();
  });
  window.addEventListener('beforeunload', cleanupPreview);

  const documentId = new URLSearchParams(window.location.search).get('document_id');
  if (documentId) loadInboxDocument(documentId);
});
