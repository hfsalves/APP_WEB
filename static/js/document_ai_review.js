document.addEventListener('DOMContentLoaded', () => {
  const cfg = window.DOCUMENT_AI_REVIEW_CONFIG || {};
  const documentId = String(cfg.documentId || '').trim();

  const els = {
    subtitle: document.getElementById('docAiReviewSubtitle'),
    state: document.getElementById('docAiReviewState'),
    previewMeta: document.getElementById('docAiPreviewMeta'),
    previewBody: document.getElementById('docAiPreviewBody'),
    previewPrev: document.getElementById('docAiPreviewPrev'),
    previewNext: document.getElementById('docAiPreviewNext'),
    previewPageLabel: document.getElementById('docAiPreviewPageLabel'),
    ocrMeta: document.getElementById('docAiOcrMeta'),
    ocrSearch: document.getElementById('docAiOcrSearch'),
    ocrList: document.getElementById('docAiOcrList'),
    sidebarMeta: document.getElementById('docAiSidebarMeta'),
    selectedText: document.getElementById('docAiSelectedText'),
    assignButtons: Array.from(document.querySelectorAll('.docai-assign-btn')),
    docType: document.getElementById('docAiDocType'),
    supplierNo: document.getElementById('docAiSupplierNo'),
    supplierName: document.getElementById('docAiSupplierName'),
    templateSelect: document.getElementById('docAiTemplateSelect'),
    confidence: document.getElementById('docAiConfidence'),
    extractionMethod: document.getElementById('docAiExtractionMethod'),
    extractionQuality: document.getElementById('docAiExtractionQuality'),
    extractionFallback: document.getElementById('docAiExtractionFallback'),
    processingStage: document.getElementById('docAiProcessingStage'),
    extractionError: document.getElementById('docAiExtractionError'),
    documentNumber: document.getElementById('docAiDocumentNumber'),
    documentDate: document.getElementById('docAiDocumentDate'),
    currency: document.getElementById('docAiCurrency'),
    customerName: document.getElementById('docAiCustomerName'),
    netTotal: document.getElementById('docAiNetTotal'),
    taxTotal: document.getElementById('docAiTaxTotal'),
    grossTotal: document.getElementById('docAiGrossTotal'),
    linesSummary: document.getElementById('docAiLinesSummary'),
    warnings: document.getElementById('docAiWarnings'),
    errors: document.getElementById('docAiErrors'),
    templateName: document.getElementById('docAiTemplateName'),
    templateFingerprint: document.getElementById('docAiTemplateFingerprint'),
    templateScoreMin: document.getElementById('docAiTemplateScoreMin'),
    templateKeywords: document.getElementById('docAiTemplateKeywords'),
    suggestBtn: document.getElementById('docAiSuggestBtn'),
    reviewStatus: document.getElementById('docAiReviewStatus'),
    reprocessBtn: document.getElementById('docAiReprocessBtn'),
    reprocessOcrBtn: document.getElementById('docAiReprocessOcrBtn'),
    reprocessFallbackBtn: document.getElementById('docAiReprocessFallbackBtn'),
    saveTemplateBtn: document.getElementById('docAiSaveTemplateBtn'),
    validateBtn: document.getElementById('docAiValidateBtn'),
    backBtn: document.getElementById('docAiBackBtn'),
    linesModal: document.getElementById('docAiLinesModal'),
    linesModalBody: document.getElementById('docAiLinesModalBody'),
    closeLinesModal: document.getElementById('docAiCloseLinesModal'),
    closeLinesModalBottom: document.getElementById('docAiCloseLinesModalBottom'),
  };

  const state = {
    lookups: null,
    document: null,
    selectedBlockId: '',
    selectedText: '',
    draftTemplate: null,
    templateMap: new Map(),
    previewPage: 1,
    ocrSearch: '',
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

  function setStatus(message, isError = false) {
    if (!els.reviewStatus) return;
    els.reviewStatus.textContent = message || '';
    els.reviewStatus.style.color = isError ? 'var(--sz-color-danger)' : '';
  }

  function formatPct(value) {
    return `${Math.round(Number(value || 0) * 100)}%`;
  }

  function statusLabel(value) {
    const items = Array.isArray(state.lookups?.statuses) ? state.lookups.statuses : [];
    const match = items.find((item) => item.value === value);
    return match ? match.label : (value || 'n/a');
  }

  function extractionMethodLabel(value) {
    const mapping = {
      direct_pdf_text: 'Texto direto PDF',
      ocr_image_fallback: 'OCR fallback',
      direct_image_ocr: 'OCR imagem',
      plain_text: 'Texto direto',
      failed: 'Falhou',
    };
    return mapping[String(value || '').trim()] || (value || 'n/a');
  }

  function processingStageLabel(value) {
    const mapping = {
      new: 'Novo',
      extract_text: 'Extração',
      text_extracted: 'Texto extraído',
      supplier_detect: 'Fornecedor',
      template_match: 'Template',
      parse: 'Parsing',
      completed: 'Concluído',
      failed: 'Falhou',
    };
    return mapping[String(value || '').trim()] || (value || 'n/a');
  }

  function normalizeDateInputValue(rawValue) {
    const raw = String(rawValue || '').trim();
    if (!raw) return '';
    if (/^\d{4}-\d{2}-\d{2}$/.test(raw)) return raw;
    const match = raw.match(/(\d{2})[\/.-](\d{2})[\/.-](\d{4})|(\d{4})[\/.-](\d{2})[\/.-](\d{2})/);
    if (!match) return raw;
    if (match[1] && match[2] && match[3]) {
      return `${match[3]}-${match[2]}-${match[1]}`;
    }
    if (match[4] && match[5] && match[6]) {
      return `${match[4]}-${match[5]}-${match[6]}`;
    }
    return raw;
  }

  function normalizeNumericValue(rawValue) {
    const raw = String(rawValue || '').trim();
    if (!raw) return '';
    const matched = raw.match(/-?\d{1,3}(?:[.\s]\d{3})*(?:,\d{2})|-?\d+(?:[.,]\d{2})|-?\d+/);
    return matched ? matched[0].replace(/\s+/g, '') : raw.replace(/[^\d,.\-]/g, '');
  }

  function fetchJson(url, options = {}) {
    return fetch(url, options).then(async (response) => {
      let payload = {};
      try {
        payload = await response.json();
      } catch (_) {}
      if (!response.ok) {
        throw new Error(payload.error || `HTTP ${response.status}`);
      }
      return payload;
    });
  }

  function getSelectedTextValue() {
    return String(els.selectedText?.value || state.selectedText || '').trim();
  }

  function getSelectedBlock() {
    return (state.document?.text_blocks || []).find((item) => item.id === state.selectedBlockId) || null;
  }

  function getPreviewPageCount(documentPayload) {
    return Math.max(1, Number(documentPayload?.preview?.page_count || documentPayload?.preview?.pages?.length || 1) || 1);
  }

  function buildPreviewHighlight(block) {
    if (!block) return '';
    const pageWidth = Number(block.page_width || 0);
    const pageHeight = Number(block.page_height || 0);
    const left = Number(block.left || 0);
    const top = Number(block.top || 0);
    const width = Number(block.width || 0);
    const height = Number(block.height || 0);
    if (!(pageWidth > 0 && pageHeight > 0 && width > 0 && height > 0)) {
      return '';
    }
    const leftPct = Math.max(0, Math.min(100, (left / pageWidth) * 100));
    const topPct = Math.max(0, Math.min(100, (top / pageHeight) * 100));
    const widthPct = Math.max(0.8, Math.min(100 - leftPct, (width / pageWidth) * 100));
    const heightPct = Math.max(0.8, Math.min(100 - topPct, (height / pageHeight) * 100));
    return `<div class="docai-preview-highlight" style="left:${leftPct}%;top:${topPct}%;width:${widthPct}%;height:${heightPct}%;"></div>`;
  }

  function updatePreviewNav(documentPayload) {
    const pageCount = getPreviewPageCount(documentPayload);
    state.previewPage = Math.min(pageCount, Math.max(1, Number(state.previewPage || 1) || 1));
    if (els.previewPageLabel) {
      els.previewPageLabel.textContent = `${state.previewPage} / ${pageCount}`;
    }
    if (els.previewPrev) els.previewPrev.disabled = state.previewPage <= 1;
    if (els.previewNext) els.previewNext.disabled = state.previewPage >= pageCount;
  }

  function renderPreview(documentPayload, focusBlock = null) {
    if (!els.previewBody) return;
    const path = documentPayload.file_path || '';
    const mime = documentPayload.mime_type || '';
    const ext = String(documentPayload.file_ext || '').toLowerCase();
    const preview = documentPayload.preview || {};
    if (focusBlock?.page) {
      state.previewPage = Number(focusBlock.page || 1) || 1;
    }
    updatePreviewNav(documentPayload);
    const activeBlock = focusBlock || getSelectedBlock();
    const highlightBlock = activeBlock && Number(activeBlock.page || 1) === Number(state.previewPage || 1) ? activeBlock : null;
    if (!path) {
      els.previewBody.innerHTML = '<div class="docai-preview-empty">Sem preview disponível.</div>';
      return;
    }
    if (ext === '.pdf' || mime.includes('pdf')) {
      const previewUrl = `/api/document_ai/documents/${encodeURIComponent(documentId)}/preview?page=${encodeURIComponent(state.previewPage || 1)}&_=${encodeURIComponent(documentPayload.updated_at || documentPayload.processed_at || documentPayload.created_at || '')}`;
      els.previewBody.innerHTML = `
        <div class="docai-preview-stage is-pdf">
          <div class="docai-preview-image-host is-pdf">
            <img class="docai-preview-image is-pdf" src="${escapeHtml(previewUrl)}" alt="${escapeHtml(documentPayload.file_name || 'Documento')}">
            ${buildPreviewHighlight(highlightBlock)}
          </div>
        </div>
      `;
      return;
    }
    if (mime.startsWith('image/') || ['.png', '.jpg', '.jpeg', '.tif', '.tiff', '.bmp', '.webp'].includes(ext)) {
      els.previewBody.innerHTML = `
        <div class="docai-preview-stage">
          <div class="docai-preview-image-host">
            <img class="docai-preview-image" src="${escapeHtml(path)}" alt="${escapeHtml(documentPayload.file_name || 'Documento')}">
            ${buildPreviewHighlight(highlightBlock)}
          </div>
        </div>
      `;
      return;
    }
    els.previewBody.innerHTML = `<div class="docai-preview-empty"><a href="${escapeHtml(path)}" target="_blank" rel="noopener">Abrir ficheiro original</a></div>`;
  }

  function renderOcrList(blocks) {
    if (!els.ocrList) return;
    const sourceItems = Array.isArray(blocks) ? blocks : [];
    const term = normalizeSearchValue(state.ocrSearch);
    const items = !term
      ? sourceItems
      : sourceItems.filter((block) => normalizeSearchValue(block.text || '').includes(term));
    if (!items.length) {
      els.ocrList.innerHTML = sourceItems.length
        ? '<div class="sz_text_muted">Sem resultados para a pesquisa atual.</div>'
        : '<div class="sz_text_muted">Sem texto extraído disponível.</div>';
      if (els.ocrMeta) els.ocrMeta.textContent = sourceItems.length ? '0 linha(s) visíveis após filtro.' : 'Sem texto extraído disponível.';
      return;
    }
    els.ocrList.innerHTML = items.map((block) => `
      <button type="button" class="docai-ocr-line${state.selectedBlockId === block.id ? ' is-active' : ''}" data-block-id="${escapeHtml(block.id)}">
        <div class="docai-ocr-line-top">
          <span>Página ${escapeHtml(block.page || 1)} · Linha ${escapeHtml(block.line_no || '')}</span>
        </div>
        <div>${escapeHtml(block.text || '')}</div>
      </button>
    `).join('');
    if (els.ocrMeta) {
      els.ocrMeta.textContent = term
        ? `${items.length} de ${sourceItems.length} linha(s) visíveis.`
        : `${items.length} linha(s) de texto disponíveis.`;
    }
  }

  function normalizeSearchValue(value) {
    return String(value || '')
      .toLowerCase()
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '')
      .trim();
  }

  function renderTags(host, items, type) {
    if (!host) return;
    const arr = Array.isArray(items) ? items : [];
    if (!arr.length) {
      host.innerHTML = '';
      return;
    }
    host.innerHTML = arr.map((item) => `
      <span class="docai-tag ${type === 'error' ? 'status-parse_error' : 'status-review_required'}">${escapeHtml(item)}</span>
    `).join('');
  }

  function updateLinesSummary(lines) {
    const arr = Array.isArray(lines) ? lines : [];
    if (!els.linesSummary) return;
    if (!arr.length) {
      els.linesSummary.textContent = 'Sem linhas detetadas.';
      els.linesSummary.style.cursor = 'default';
      return;
    }
    els.linesSummary.textContent = `${arr.length} linha(s) detetada(s). Clique para ver detalhe.`;
    els.linesSummary.style.cursor = 'pointer';
  }

  function populateDocTypes() {
    if (!els.docType) return;
    const docTypes = state.lookups?.doc_types || [];
    els.docType.innerHTML = docTypes.map((item) => (
      `<option value="${escapeHtml(item.value)}">${escapeHtml(item.label)}</option>`
    )).join('');
  }

  function populateTemplateSelect(templates, selectedId) {
    if (!els.templateSelect) return;
    state.templateMap.clear();
    const options = ['<option value="">Sem template</option>'];
    (templates || []).forEach((template) => {
      state.templateMap.set(template.id, template);
      options.push(`<option value="${escapeHtml(template.id)}">${escapeHtml(template.name)}${template.supplier_name ? ` · ${escapeHtml(template.supplier_name)}` : ''}</option>`);
    });
    els.templateSelect.innerHTML = options.join('');
    els.templateSelect.value = selectedId || '';
  }

  function applyDocumentToForm(documentPayload) {
    const result = documentPayload.result || {};
    els.docType.value = documentPayload.doc_type || result.document_type || 'unknown';
    els.supplierNo.value = documentPayload.supplier_no || result.supplier?.supplier_no || '';
    els.supplierName.value = documentPayload.supplier_name || result.supplier?.name || '';
    els.confidence.value = Number(documentPayload.confidence || 0).toFixed(2);
    els.documentNumber.value = result.document_number || '';
    els.documentDate.value = result.document_date || '';
    els.currency.value = result.currency || '';
    els.customerName.value = result.customer?.name || '';
    els.netTotal.value = result.totals?.net_total ?? 0;
    els.taxTotal.value = result.totals?.tax_total ?? 0;
    els.grossTotal.value = result.totals?.gross_total ?? 0;
    renderTags(els.warnings, documentPayload.warnings, 'warning');
    renderTags(els.errors, documentPayload.errors, 'error');
    updateLinesSummary(result.lines || []);

    els.templateName.value = documentPayload.template_draft?.name || '';
    els.templateFingerprint.value = documentPayload.template?.fingerprint || '';
    els.templateScoreMin.value = documentPayload.template?.score_min_match || documentPayload.template_draft?.score_min_match || 0.55;
    const keywords = documentPayload.template?.match_rules?.keywords || documentPayload.template_draft?.match_rules?.keywords || [];
    els.templateKeywords.value = Array.isArray(keywords) ? keywords.join(', ') : '';
    populateTemplateSelect(documentPayload.available_templates || [], documentPayload.template?.id || '');

    const label = documentPayload.status || 'new';
    if (els.state) {
      els.state.className = `docai-status-chip status-${label}`;
      els.state.innerHTML = `<i class="fa-solid fa-circle-info"></i><span>${escapeHtml(statusLabel(label))}</span>`;
    }
    if (els.subtitle) {
      els.subtitle.textContent = `${documentPayload.file_name || ''} · ${formatPct(documentPayload.confidence)}`;
    }
    if (els.previewMeta) {
      els.previewMeta.textContent = `${documentPayload.mime_type || documentPayload.file_ext || ''} · ${documentPayload.created_at ? new Date(documentPayload.created_at).toLocaleString('pt-PT') : ''}`;
    }
    if (els.extractionMethod) {
      els.extractionMethod.textContent = extractionMethodLabel(documentPayload.extraction_method);
    }
    if (els.extractionQuality) {
      els.extractionQuality.textContent = formatPct(documentPayload.extraction_quality_score || 0);
    }
    if (els.extractionFallback) {
      const fallbackUsed = !!documentPayload.extraction_notes?.fallback_triggered || documentPayload.extraction_method === 'ocr_image_fallback';
      els.extractionFallback.textContent = fallbackUsed ? 'Sim' : 'Não';
    }
    if (els.processingStage) {
      els.processingStage.textContent = processingStageLabel(documentPayload.processing_stage);
    }
    if (els.extractionError) {
      els.extractionError.textContent = documentPayload.last_processing_error
        ? `Último erro: ${documentPayload.last_processing_error}`
        : (documentPayload.preprocessed_image_path
          ? 'Pré-processamento visual aplicado antes do OCR.'
          : 'Sem erros no pipeline de extração.');
    }
  }

  function guessAnchorFromSelection(textValue) {
    const raw = String(textValue || '').trim();
    if (!raw) return [];
    const colonMatch = raw.match(/^(.{2,40}?)(?:\s*[:\-])/);
    if (colonMatch) return [colonMatch[1].trim()];
    return [raw.split(/\s+/).slice(0, 3).join(' ').trim()].filter(Boolean);
  }

  function ensureDraftTemplate() {
    if (state.draftTemplate) return state.draftTemplate;
    state.draftTemplate = {
      id: '',
      name: els.templateName?.value || 'Novo template',
      supplier_no: Number(els.supplierNo?.value || 0) || null,
      doc_type: els.docType?.value || 'unknown',
      score_min_match: Number(els.templateScoreMin?.value || 0.55) || 0.55,
      match_rules: { keywords: [], required: [], forbidden: [] },
      lines: { enabled: true, header_aliases: ['ref', 'description', 'qty', 'price', 'amount'], stop_keywords: ['total', 'subtotal', 'iva'] },
      fields: [],
    };
    return state.draftTemplate;
  }

  function upsertDraftField(fieldKey, selectedText) {
    const draft = ensureDraftTemplate();
    const labelMap = {
      document_number: 'Número documento',
      document_date: 'Data documento',
      net_total: 'Base',
      tax_total: 'IVA',
      gross_total: 'Total bruto',
      currency: 'Moeda',
      supplier_tax_id: 'NIF fornecedor',
      supplier_name: 'Nome fornecedor',
      customer_name: 'Cliente',
    };
    const genericRegex = {
      document_number: '(?i)([A-Z0-9][A-Z0-9/.-]{2,})',
      document_date: '(\\d{4}[-/]\\d{2}[-/]\\d{2}|\\d{2}[-/]\\d{2}[-/]\\d{4})',
      net_total: '(-?\\d{1,3}(?:[.\\s]\\d{3})*(?:,\\d{2})|-?\\d+(?:[.,]\\d{2}))',
      tax_total: '(-?\\d{1,3}(?:[.\\s]\\d{3})*(?:,\\d{2})|-?\\d+(?:[.,]\\d{2}))',
      gross_total: '(-?\\d{1,3}(?:[.\\s]\\d{3})*(?:,\\d{2})|-?\\d+(?:[.,]\\d{2}))',
      currency: '(?i)\\b(EUR|USD|GBP|CHF|BRL|AOA|MZN)\\b',
      supplier_tax_id: '(\\d{9,14})',
      supplier_name: '(.+)',
      customer_name: '(.+)',
    };
    let item = (draft.fields || []).find((entry) => entry.field_key === fieldKey);
    if (!item) {
      item = {
        field_key: fieldKey,
        label: labelMap[fieldKey] || fieldKey,
        order: (draft.fields || []).length + 1,
        required: ['document_number', 'document_date', 'gross_total'].includes(fieldKey),
        match_mode: 'anchor_regex',
        anchors: [],
        regex: genericRegex[fieldKey] || '',
        aliases: [],
        postprocess: fieldKey === 'document_date'
          ? 'date'
          : (['net_total', 'tax_total', 'gross_total'].includes(fieldKey)
            ? 'decimal'
            : (fieldKey === 'currency'
              ? 'currency'
              : (fieldKey.includes('tax_id') ? 'tax_id' : 'text'))),
        config: {},
        active: true,
      };
      draft.fields.push(item);
    }
    item.anchors = [selectedText, ...guessAnchorFromSelection(selectedText)]
      .map((itemValue) => String(itemValue || '').trim())
      .filter(Boolean)
      .filter((itemValue, index, arr) => arr.findIndex((entry) => entry.toLowerCase() === itemValue.toLowerCase()) === index);
    item.config = { sample_text: selectedText };
  }

  function assignSelectedToField(fieldKey) {
    const raw = getSelectedTextValue();
    if (!raw) {
      showMessage('Seleciona primeiro uma linha de texto.', 'warning');
      return;
    }
    if (fieldKey === 'document_number') els.documentNumber.value = raw;
    if (fieldKey === 'document_date') els.documentDate.value = normalizeDateInputValue(raw.match(/\d{4}-\d{2}-\d{2}|\d{2}[-/.]\d{2}[-/.]\d{4}|\d{4}[-/.]\d{2}[-/.]\d{2}/)?.[0] || raw);
    if (fieldKey === 'net_total') els.netTotal.value = normalizeNumericValue(raw);
    if (fieldKey === 'tax_total') els.taxTotal.value = normalizeNumericValue(raw);
    if (fieldKey === 'gross_total') els.grossTotal.value = normalizeNumericValue(raw);
    if (fieldKey === 'currency') {
      const currencyMatch = raw.match(/\b(EUR|USD|GBP|CHF|BRL|AOA|MZN)\b/i);
      els.currency.value = currencyMatch ? currencyMatch[1].toUpperCase() : raw.toUpperCase();
    }
    if (fieldKey === 'customer_name') els.customerName.value = raw;
    if (fieldKey === 'supplier_tax_id') els.supplierNo.value = els.supplierNo.value || ''; // keep no
    if (fieldKey === 'supplier_tax_id' && !els.supplierName.value) {
      els.supplierName.value = state.document?.supplier_name || '';
    }
    if (fieldKey === 'supplier_name') els.supplierName.value = raw;
    upsertDraftField(fieldKey, raw);
    showMessage(`Linha atribuída a ${fieldKey}.`, 'success');
  }

  function currentResultPayload() {
    return {
      document_type: els.docType.value || 'unknown',
      supplier: {
        supplier_no: Number(els.supplierNo.value || 0) || null,
        tax_id: state.document?.result?.supplier?.tax_id || state.document?.supplier_tax_id_detected || '',
        name: els.supplierName.value || '',
      },
      customer: {
        tax_id: state.document?.result?.customer?.tax_id || '',
        name: els.customerName.value || '',
      },
      document_number: els.documentNumber.value || '',
      document_date: els.documentDate.value || '',
      currency: els.currency.value || '',
      totals: {
        net_total: Number(els.netTotal.value || 0) || 0,
        tax_total: Number(els.taxTotal.value || 0) || 0,
        gross_total: Number(els.grossTotal.value || 0) || 0,
      },
      taxes: state.document?.result?.taxes || [],
      lines: state.document?.result?.lines || [],
      warnings: state.document?.warnings || [],
    };
  }

  function currentTemplatePayload() {
    const draft = ensureDraftTemplate();
    draft.id = els.templateSelect.value || draft.id || '';
    draft.name = els.templateName.value || 'Novo template';
    draft.fingerprint = els.templateFingerprint.value || '';
    draft.supplier_no = Number(els.supplierNo.value || 0) || null;
    draft.doc_type = els.docType.value || 'unknown';
    draft.score_min_match = Number(els.templateScoreMin.value || 0.55) || 0.55;
    draft.match_rules = {
      keywords: els.templateKeywords.value.split(',').map((item) => item.trim()).filter(Boolean),
      required: Array.isArray(draft.match_rules?.required) ? draft.match_rules.required : [],
      forbidden: Array.isArray(draft.match_rules?.forbidden) ? draft.match_rules.forbidden : [],
    };
    draft.lines = state.draftTemplate?.lines || draft.lines || {};
    draft.definition_json = {
      doc_type: draft.doc_type,
      match: draft.match_rules,
      fields: Object.fromEntries((draft.fields || []).map((field) => [field.field_key, {
        anchors: field.anchors || [],
        regex: field.regex || '',
        aliases: field.aliases || [],
        required: !!field.required,
        postprocess: field.postprocess || '',
        config: field.config || {},
        match_mode: field.match_mode || 'anchor_regex',
      }])),
      lines: draft.lines,
    };
    return draft;
  }

  function applySuggestedTemplate(suggestion) {
    if (!suggestion || typeof suggestion !== 'object') return;
    const draft = ensureDraftTemplate();
    const suggestedFields = Array.isArray(suggestion.fields) ? suggestion.fields : [];
    draft.name = suggestion.name || draft.name || 'Template sugerido';
    draft.fingerprint = suggestion.fingerprint || draft.fingerprint || '';
    draft.doc_type = suggestion.doc_type || draft.doc_type || 'unknown';
    draft.score_min_match = Number(suggestion.score_min_match || draft.score_min_match || 0.55) || 0.55;
    draft.match_rules = suggestion.match_rules || draft.match_rules || { keywords: [], required: [], forbidden: [] };
    draft.lines = suggestion.lines || draft.lines || {};
    draft.fields = suggestedFields.map((field, index) => ({
      id: '',
      field_key: field.field_key || '',
      label: field.label || field.field_key || '',
      order: index + 1,
      required: !!field.required,
      match_mode: 'anchor_regex',
      anchors: Array.isArray(field.anchors) ? field.anchors : [],
      regex: field.regex || '',
      aliases: Array.isArray(field.aliases) ? field.aliases : [],
      postprocess: field.postprocess || '',
      config: {},
      active: true,
    })).filter((field) => field.field_key);

    els.templateName.value = draft.name || '';
    els.templateFingerprint.value = draft.fingerprint || '';
    els.templateScoreMin.value = draft.score_min_match || 0.55;
    els.templateKeywords.value = Array.isArray(draft.match_rules?.keywords) ? draft.match_rules.keywords.join(', ') : '';
    if (draft.doc_type) {
      els.docType.value = draft.doc_type;
    }
  }

  async function suggestFromReview() {
    setStatus('A gerar sugestão automática...');
    try {
      const payload = await fetchJson('/api/document_ai/suggest', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          document_type: els.docType.value || state.document?.doc_type || 'unknown',
          supplier_no: Number(els.supplierNo.value || 0) || null,
          supplier_name: els.supplierName.value || state.document?.supplier_name || '',
          file_name: state.document?.file_name || '',
          selected_text: getSelectedTextValue(),
          extracted_text: state.document?.extracted_text || '',
          current_result: currentResultPayload(),
          current_template: currentTemplatePayload(),
        }),
      });
      if (!payload.ok || !payload.suggestion) {
        throw new Error(payload.message || 'A sugestão automática não devolveu conteúdo utilizável.');
      }
      applySuggestedTemplate(payload.suggestion);
      showMessage(payload.message || 'Sugestão automática aplicada.', 'success');
      setStatus(payload.message || 'Sugestão automática aplicada.');
    } catch (error) {
      console.error(error);
      showMessage(error.message || 'Falha na sugestão automática.', 'error');
      setStatus(error.message || 'Falha na sugestão automática.', true);
    }
  }

  async function loadData() {
    setStatus('A carregar documento...');
    try {
      const [lookups, detail] = await Promise.all([
        fetchJson('/api/document_ai/lookups'),
        fetchJson(`/api/document_ai/documents/${encodeURIComponent(documentId)}`),
      ]);
      state.lookups = lookups;
      state.document = detail;
      state.draftTemplate = detail.template ? {
        id: detail.template.id,
        name: detail.template.name,
        fingerprint: detail.template.fingerprint || '',
        supplier_no: detail.template.supplier_no,
        doc_type: detail.template.doc_type,
        score_min_match: detail.template.score_min_match,
        match_rules: detail.template.match_rules || { keywords: [], required: [], forbidden: [] },
        lines: detail.template.definition?.lines || {},
        fields: detail.template.fields || [],
      } : detail.template_draft;
      populateDocTypes();
      renderPreview(detail);
      renderOcrList(detail.text_blocks || []);
      applyDocumentToForm(detail);
      els.suggestBtn.disabled = !(detail.llm && detail.llm.available);
      setStatus('Documento carregado.');
    } catch (error) {
      console.error(error);
      setStatus(error.message || 'Erro ao carregar documento.', true);
      showMessage(error.message || 'Erro ao carregar documento.', 'error');
    }
  }

  async function saveValidation() {
    setStatus('A gravar validação...');
    try {
      const payload = await fetchJson(`/api/document_ai/documents/${encodeURIComponent(documentId)}/validate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          doc_type: els.docType.value || 'unknown',
          supplier_no: Number(els.supplierNo.value || 0) || null,
          template_id: els.templateSelect.value || '',
          confidence: Number(els.confidence.value || 0) || 0,
          status: 'parsed_ok',
          result: currentResultPayload(),
          warnings: state.document?.warnings || [],
          errors: state.document?.errors || [],
        }),
      });
      state.document = payload;
      showMessage('Validação gravada.', 'success');
      applyDocumentToForm(payload);
      setStatus('Validação gravada.');
    } catch (error) {
      console.error(error);
      showMessage(error.message || 'Falha ao gravar validação.', 'error');
      setStatus(error.message || 'Falha ao gravar.', true);
    }
  }

  async function saveTemplateFromReview() {
    const templatePayload = currentTemplatePayload();
    setStatus('A guardar template...');
    try {
      const payload = await fetchJson(`/api/document_ai/documents/${encodeURIComponent(documentId)}/save_template`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(templatePayload),
      });
      showMessage('Template guardado.', 'success');
      if (state.document) {
        state.document.template = payload;
        state.document.doctemplatestamp = payload.id;
      }
      templatePayload.id = payload.id;
      populateTemplateSelect(state.document?.available_templates || [], payload.id);
      els.templateSelect.value = payload.id;
      setStatus('Template guardado.');
    } catch (error) {
      console.error(error);
      showMessage(error.message || 'Falha ao guardar template.', 'error');
      setStatus(error.message || 'Falha ao guardar template.', true);
    }
  }

  async function reprocess(mode = 'auto') {
    const statusMap = {
      auto: 'A reprocessar documento...',
      ocr: 'A reprocessar com OCR...',
      visual_fallback: 'A reprocessar com fallback visual...',
    };
    setStatus(statusMap[mode] || 'A reprocessar documento...');
    try {
      const payload = await fetchJson(`/api/document_ai/documents/${encodeURIComponent(documentId)}/reprocess`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          template_id: els.templateSelect.value || '',
          reprocess_mode: mode,
        }),
      });
      state.document = payload;
      state.draftTemplate = payload.template ? {
        id: payload.template.id,
        name: payload.template.name,
        fingerprint: payload.template.fingerprint || '',
        supplier_no: payload.template.supplier_no,
        doc_type: payload.template.doc_type,
        score_min_match: payload.template.score_min_match,
        match_rules: payload.template.match_rules || { keywords: [], required: [], forbidden: [] },
        lines: payload.template.definition?.lines || {},
        fields: payload.template.fields || [],
      } : payload.template_draft;
      renderPreview(payload);
      renderOcrList(payload.text_blocks || []);
      applyDocumentToForm(payload);
      showMessage('Documento reprocessado.', 'success');
      setStatus('Reprocessamento concluído.');
    } catch (error) {
      console.error(error);
      showMessage(error.message || 'Falha ao reprocessar.', 'error');
      setStatus(error.message || 'Falha ao reprocessar.', true);
    }
  }

  function openLinesModal() {
    const lines = state.document?.result?.lines || [];
    if (!lines.length || !els.linesModalBody || !els.linesModal) return;
    els.linesModalBody.innerHTML = `
      <div class="sz_table_host">
        <div class="sz_table_wrap">
          <table class="sz_table">
            <thead class="sz_table_head">
              <tr><th>Descrição</th><th>Qtd</th><th>P. Unit.</th><th>Total</th></tr>
            </thead>
            <tbody>
              ${lines.map((line) => `
                <tr>
                  <td>${escapeHtml(line.description || '')}</td>
                  <td>${escapeHtml(line.qty ?? '')}</td>
                  <td>${escapeHtml(line.unit_price ?? '')}</td>
                  <td>${escapeHtml(line.gross_amount ?? '')}</td>
                </tr>
              `).join('')}
            </tbody>
          </table>
        </div>
      </div>
    `;
    els.linesModal.classList.add('is-open');
  }

  function closeLinesModal() {
    els.linesModal?.classList.remove('is-open');
  }

  els.ocrList?.addEventListener('click', (event) => {
    const button = event.target.closest('button[data-block-id]');
    if (!button) return;
    state.selectedBlockId = button.dataset.blockId || '';
    const block = (state.document?.text_blocks || []).find((item) => item.id === state.selectedBlockId);
    state.selectedText = block?.text || '';
    if (els.selectedText) els.selectedText.value = state.selectedText || '';
    state.previewPage = Number(block?.page || 1) || 1;
    renderOcrList(state.document?.text_blocks || []);
    renderPreview(state.document || {}, block);
  });
  els.ocrSearch?.addEventListener('input', () => {
    state.ocrSearch = els.ocrSearch?.value || '';
    renderOcrList(state.document?.text_blocks || []);
  });
  els.selectedText?.addEventListener('input', () => {
    state.selectedText = String(els.selectedText?.value || '').trim();
  });
  els.previewPrev?.addEventListener('click', () => {
    state.previewPage = Math.max(1, Number(state.previewPage || 1) - 1);
    renderPreview(state.document || {});
  });
  els.previewNext?.addEventListener('click', () => {
    state.previewPage = Math.min(getPreviewPageCount(state.document || {}), Number(state.previewPage || 1) + 1);
    renderPreview(state.document || {});
  });
  els.assignButtons.forEach((button) => button.addEventListener('click', () => assignSelectedToField(button.dataset.field || '')));
  els.validateBtn?.addEventListener('click', saveValidation);
  els.saveTemplateBtn?.addEventListener('click', saveTemplateFromReview);
  els.reprocessBtn?.addEventListener('click', () => reprocess('auto'));
  els.reprocessOcrBtn?.addEventListener('click', () => reprocess('ocr'));
  els.reprocessFallbackBtn?.addEventListener('click', () => reprocess('visual_fallback'));
  els.suggestBtn?.addEventListener('click', suggestFromReview);
  els.backBtn?.addEventListener('click', () => { window.location.href = '/document_ai/inbox'; });
  els.closeLinesModal?.addEventListener('click', closeLinesModal);
  els.closeLinesModalBottom?.addEventListener('click', closeLinesModal);
  els.linesSummary?.addEventListener('click', openLinesModal);
  els.templateSelect?.addEventListener('change', async () => {
    const templateId = els.templateSelect.value || '';
    if (!templateId) return;
    try {
      const detail = await fetchJson(`/api/document_ai/templates/${encodeURIComponent(templateId)}`);
      state.draftTemplate = {
        id: detail.id,
        name: detail.name,
        fingerprint: detail.fingerprint || '',
        supplier_no: detail.supplier_no,
        doc_type: detail.doc_type,
        score_min_match: detail.score_min_match,
        match_rules: detail.match_rules || { keywords: [], required: [], forbidden: [] },
        lines: detail.definition?.lines || {},
        fields: detail.fields || [],
      };
      els.templateName.value = detail.name || '';
      els.templateFingerprint.value = detail.fingerprint || '';
      els.templateScoreMin.value = detail.score_min_match || 0.55;
      els.templateKeywords.value = (detail.match_rules?.keywords || []).join(', ');
    } catch (error) {
      console.error(error);
    }
  });

  loadData();
});
