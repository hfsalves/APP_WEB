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
    cropToggle: document.getElementById('docAiCropToggle'),
    cropClear: document.getElementById('docAiCropClear'),
    rotateLeft: document.getElementById('docAiRotateLeft'),
    rotateRight: document.getElementById('docAiRotateRight'),
    openOriginalBtn: document.getElementById('docAiOpenOriginalBtn'),
    ocrMeta: document.getElementById('docAiOcrMeta'),
    ocrSearch: document.getElementById('docAiOcrSearch'),
    ocrList: document.getElementById('docAiOcrList'),
    sidebarMeta: document.getElementById('docAiSidebarMeta'),
    selectedText: document.getElementById('docAiSelectedText'),
    assignButtons: Array.from(document.querySelectorAll('.docai-assign-btn')),
    docType: document.getElementById('docAiDocType'),
    supplierNo: document.getElementById('docAiSupplierNo'),
    supplierNoDisplay: document.getElementById('docAiSupplierNoDisplay'),
    supplierName: document.getElementById('docAiSupplierName'),
    templateSelect: document.getElementById('docAiTemplateSelect'),
    confidence: document.getElementById('docAiConfidence'),
    confidenceDisplay: document.getElementById('docAiConfidenceDisplay'),
    dueDate: document.getElementById('docAiDueDate'),
    supplierTaxId: document.getElementById('docAiSupplierTaxId'),
    customerTaxId: document.getElementById('docAiCustomerTaxId'),
    customerFeid: document.getElementById('docAiCustomerFeid'),
    customerFeDisplay: document.getElementById('docAiCustomerFeDisplay'),
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
    taxBase0: document.getElementById('docAiTaxBase0'),
    taxAmount0: document.getElementById('docAiTaxAmount0'),
    taxBase6: document.getElementById('docAiTaxBase6'),
    taxAmount6: document.getElementById('docAiTaxAmount6'),
    taxBase13: document.getElementById('docAiTaxBase13'),
    taxAmount13: document.getElementById('docAiTaxAmount13'),
    taxBase23: document.getElementById('docAiTaxBase23'),
    taxAmount23: document.getElementById('docAiTaxAmount23'),
    lineStartAnchor: document.getElementById('docAiLineStartAnchor'),
    lineEndAnchor: document.getElementById('docAiLineEndAnchor'),
    lineRefAnchor: document.getElementById('docAiLineRefAnchor'),
    lineDescriptionAnchor: document.getElementById('docAiLineDescriptionAnchor'),
    lineQtyAnchor: document.getElementById('docAiLineQtyAnchor'),
    lineUnitPriceAnchor: document.getElementById('docAiLineUnitPriceAnchor'),
    lineDiscountAnchor: document.getElementById('docAiLineDiscountAnchor'),
    lineTotalAnchor: document.getElementById('docAiLineTotalAnchor'),
    lineVatAnchor: document.getElementById('docAiLineVatAnchor'),
    lineAreaBtn: document.getElementById('docAiLineAreaBtn'),
    openLinesDetailBtn: document.getElementById('docAiOpenLinesDetailBtn'),
    lineAreaStatus: document.getElementById('docAiLineAreaStatus'),
    linesSummary: document.getElementById('docAiLinesSummary'),
    warnings: document.getElementById('docAiWarnings'),
    errors: document.getElementById('docAiErrors'),
    templateName: document.getElementById('docAiTemplateName'),
    templateFingerprint: document.getElementById('docAiTemplateFingerprint'),
    templateScoreMin: document.getElementById('docAiTemplateScoreMin'),
    templateKeywords: document.getElementById('docAiTemplateKeywords'),
    templateKeywordsBtn: document.getElementById('docAiTemplateKeywordsBtn'),
    suggestBtn: document.getElementById('docAiSuggestBtn'),
    classifyLlmBtn: document.getElementById('docAiClassifyLlmBtn'),
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
    valueModal: document.getElementById('docAiValueModal'),
    valueModalFieldLabel: document.getElementById('docAiValueModalFieldLabel'),
    valueSource: document.getElementById('docAiValueSource'),
    valuePreview: document.getElementById('docAiValuePreview'),
    closeValueModal: document.getElementById('docAiCloseValueModal'),
    closeValueModalBottom: document.getElementById('docAiCloseValueModalBottom'),
    applyValueModal: document.getElementById('docAiApplyValueModal'),
    supplierModal: document.getElementById('docAiSupplierModal'),
    supplierModalBody: document.getElementById('docAiSupplierModalBody'),
    closeSupplierModal: document.getElementById('docAiCloseSupplierModal'),
    closeSupplierModalBottom: document.getElementById('docAiCloseSupplierModalBottom'),
    keywordsModal: document.getElementById('docAiKeywordsModal'),
    keywordsText: document.getElementById('docAiKeywordsText'),
    closeKeywordsModal: document.getElementById('docAiCloseKeywordsModal'),
    closeKeywordsModalBottom: document.getElementById('docAiCloseKeywordsModalBottom'),
    applyKeywordsModal: document.getElementById('docAiApplyKeywordsModal'),
    dropTargets: Array.from(document.querySelectorAll('[data-drop-field]')),
    fieldDisplays: Array.from(document.querySelectorAll('[data-field-display]')),
  };

  const state = {
    lookups: null,
    document: null,
    selectedBlockId: '',
    selectedText: '',
    draggingBlockId: '',
    fieldAssignments: {},
    draftTemplate: null,
    templateMap: new Map(),
    previewPage: 1,
    ocrSearch: '',
    valueEditor: {
      fieldKey: '',
      sourceText: '',
      selectedText: '',
      blockId: '',
      selectionStart: 0,
      selectionEnd: 0,
    },
    supplierCandidates: [],
    dragClearTimer: null,
    pointerDrag: {
      active: false,
      started: false,
      pointerId: null,
      blockId: '',
      startX: 0,
      startY: 0,
      overField: '',
      ghostEl: null,
    },
    adjustments: {
      rotate: 0,
      crop: null,
      cropMode: false,
      lineArea: null,
      lineAreaMode: false,
      dragging: false,
      draggingKind: '',
      dragStart: null,
      dragRect: null,
    },
  };

  function currentDraggedBlockId(explicitBlockId = '') {
    return String(explicitBlockId || state.draggingBlockId || state.selectedBlockId || '').trim();
  }

  function clearDropHighlights() {
    els.dropTargets.forEach((target) => target.classList.remove('is-dragover'));
  }

  function dropSlotFromPoint(clientX, clientY) {
    const node = document.elementFromPoint(clientX, clientY);
    return node?.closest?.('[data-drop-field]') || null;
  }

  function dropFieldKey(slot) {
    return String(slot?.dataset?.dropField || '').trim();
  }

  function destroyPointerGhost() {
    const ghost = state.pointerDrag.ghostEl;
    if (ghost?.parentNode) {
      ghost.parentNode.removeChild(ghost);
    }
    state.pointerDrag.ghostEl = null;
  }

  function updatePointerGhost(clientX, clientY) {
    const ghost = state.pointerDrag.ghostEl;
    if (!ghost) return;
    ghost.style.left = `${clientX + 14}px`;
    ghost.style.top = `${clientY + 14}px`;
  }

  function beginPointerDrag(blockId, clientX, clientY) {
    const block = (state.document?.text_blocks || []).find((item) => item.id === blockId);
    if (!block) return;
    state.pointerDrag.started = true;
    state.draggingBlockId = blockId;
    const ghost = document.createElement('div');
    ghost.className = 'docai-drag-ghost';
    ghost.textContent = String(block.text || '').trim() || 'OCR';
    document.body.appendChild(ghost);
    state.pointerDrag.ghostEl = ghost;
    updatePointerGhost(clientX, clientY);
  }

  function cleanupPointerDrag() {
    destroyPointerGhost();
    clearDropHighlights();
    state.pointerDrag.active = false;
    state.pointerDrag.started = false;
    state.pointerDrag.pointerId = null;
    state.pointerDrag.blockId = '';
    state.pointerDrag.startX = 0;
    state.pointerDrag.startY = 0;
    state.pointerDrag.overField = '';
    state.draggingBlockId = '';
  }

  function startPointerDrag(blockId, event) {
    const block = (state.document?.text_blocks || []).find((item) => item.id === blockId);
    if (!block) return;
    state.selectedBlockId = blockId;
    state.selectedText = String(block.text || '').trim();
    if (els.selectedText) els.selectedText.value = state.selectedText || '';
    state.previewPage = Number(block.page || 1) || 1;
    renderOcrList(state.document?.text_blocks || []);
    renderPreview(state.document || {}, block);
    state.pointerDrag.active = true;
    state.pointerDrag.started = false;
    state.pointerDrag.pointerId = event.pointerId;
    state.pointerDrag.blockId = blockId;
    state.pointerDrag.startX = event.clientX;
    state.pointerDrag.startY = event.clientY;
    state.pointerDrag.overField = '';
  }

  const taxFieldMap = {
    0: { base: els.taxBase0, tax: els.taxAmount0 },
    6: { base: els.taxBase6, tax: els.taxAmount6 },
    13: { base: els.taxBase13, tax: els.taxAmount13 },
    23: { base: els.taxBase23, tax: els.taxAmount23 },
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

  function normalizeTaxIdValue(rawValue) {
    const raw = String(rawValue || '').trim();
    const match = raw.match(/(?:PT|ES|FR|DE|IT|NL|BE)?\s*(\d[\d\s./-]{7,20}\d)/i);
    if (match) {
      return match[1].replace(/\D+/g, '');
    }
    return raw.replace(/[^\dA-Z]/gi, '').trim();
  }

  function numericInputValue(element) {
    if (!element) return 0;
    const raw = String(element.value || '').trim().replace(/\s+/g, '').replace(/\.(?=\d{3}(?:\D|$))/g, '').replace(',', '.');
    const parsed = Number(raw || 0);
    return Number.isFinite(parsed) ? parsed : 0;
  }

  function setInputValue(element, value) {
    if (!element) return;
    element.value = value == null ? '' : value;
  }

  function getFieldInput(fieldKey) {
    const mapping = {
      document_number: els.documentNumber,
      document_date: els.documentDate,
      due_date: els.dueDate,
      currency: els.currency,
      supplier_tax_id: els.supplierTaxId,
      supplier_name: els.supplierName,
      customer_tax_id: els.customerTaxId,
      customer_name: els.customerName,
      tax_base_0: els.taxBase0,
      tax_amount_0: els.taxAmount0,
      tax_base_6: els.taxBase6,
      tax_amount_6: els.taxAmount6,
      tax_base_13: els.taxBase13,
      tax_amount_13: els.taxAmount13,
      tax_base_23: els.taxBase23,
      tax_amount_23: els.taxAmount23,
      net_total: els.netTotal,
      tax_total: els.taxTotal,
      gross_total: els.grossTotal,
      line_start_anchor: els.lineStartAnchor,
      line_end_anchor: els.lineEndAnchor,
      line_ref_anchor: els.lineRefAnchor,
      line_description_anchor: els.lineDescriptionAnchor,
      line_qty_anchor: els.lineQtyAnchor,
      line_unit_price_anchor: els.lineUnitPriceAnchor,
      line_discount_anchor: els.lineDiscountAnchor,
      line_total_anchor: els.lineTotalAnchor,
      line_vat_anchor: els.lineVatAnchor,
    };
    return mapping[fieldKey] || null;
  }

  function fieldDisplayElement(fieldKey) {
    return els.fieldDisplays.find((element) => element.dataset.fieldDisplay === fieldKey) || null;
  }

  function isDroppableField(fieldKey) {
    return !!fieldDisplayElement(fieldKey);
  }

  function fieldCurrentValue(fieldKey) {
    const input = getFieldInput(fieldKey);
    if (!input) return '';
    return String(input.value || '').trim();
  }

  function formatFieldDisplayValue(fieldKey, value) {
    const raw = String(value == null ? '' : value).trim();
    if (!raw) return '--';
    if (fieldKey === 'document_date' || fieldKey === 'due_date') {
      const normalized = normalizeDateInputValue(raw);
      if (/^\d{4}-\d{2}-\d{2}$/.test(normalized)) {
        const [year, month, day] = normalized.split('-');
        return `${day}/${month}/${year}`;
      }
      return raw;
    }
    if ([
      'net_total',
      'tax_total',
      'gross_total',
      'tax_base_0',
      'tax_amount_0',
      'tax_base_6',
      'tax_amount_6',
      'tax_base_13',
      'tax_amount_13',
      'tax_base_23',
      'tax_amount_23',
    ].includes(fieldKey)) {
      const numeric = Number(String(raw).replace(/\s+/g, '').replace(/\.(?=\d{3}(?:\D|$))/g, '').replace(',', '.'));
      if (Number.isFinite(numeric)) {
        return numeric.toLocaleString('pt-PT', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
      }
    }
    if (fieldKey === 'currency') return raw.toUpperCase();
    return raw;
  }

  function setDropDisplay(fieldKey, value) {
    const element = fieldDisplayElement(fieldKey);
    if (!element) return;
    const text = formatFieldDisplayValue(fieldKey, value);
    element.textContent = text;
    element.classList.toggle('docai-drop-value-empty', text === '--');
    const slot = element.closest('[data-drop-field]');
    slot?.classList.toggle('is-filled', text !== '--');
    if (slot) {
      slot.querySelector('.docai-clear-field-btn')?.remove();
      if (text !== '--') {
        const clearBtn = document.createElement('button');
        clearBtn.type = 'button';
        clearBtn.className = 'docai-clear-field-btn';
        clearBtn.dataset.clearField = fieldKey;
        clearBtn.title = 'Remover atribuição';
        clearBtn.setAttribute('aria-label', `Remover atribuição de ${fieldKeyLabel(fieldKey)}`);
        clearBtn.innerHTML = '<i class="fa-solid fa-xmark"></i>';
        slot.appendChild(clearBtn);
      }
    }
  }

  function extractedTextContainsDigits(digits) {
    const needle = String(digits || '').replace(/\D+/g, '');
    if (!needle) return false;
    const pieces = [];
    if (state.document?.extracted_text) pieces.push(state.document.extracted_text);
    (state.document?.text_blocks || []).forEach((block) => {
      if (block?.text) pieces.push(block.text);
    });
    return pieces.some((piece) => String(piece || '').replace(/\D+/g, '').includes(needle));
  }

  function setFieldNote(fieldKey, message = '') {
    const slot = fieldDisplayElement(fieldKey)?.closest('[data-drop-field]');
    if (!slot) return;
    let note = slot.querySelector('.docai-field-note');
    if (!message) {
      note?.remove();
      return;
    }
    if (!note) {
      note = document.createElement('div');
      note.className = 'docai-field-note';
      slot.appendChild(note);
    }
    note.textContent = message;
  }

  function refreshCustomerTaxVisibility() {
    const entityTaxId = normalizeTaxIdValue(state.document?.entity?.tax_id || '');
    const feid = Number(els.customerFeid?.value || state.document?.entity?.feid || state.document?.feid || 0) || 0;
    const display = fieldDisplayElement('customer_tax_id');
    if (!display) return;
    display.classList.remove('docai-drop-value-warning');
    setFieldNote('customer_tax_id', '');
    if (!feid || !entityTaxId) return;

    if (normalizeTaxIdValue(els.customerTaxId?.value || '') !== entityTaxId) {
      setInputValue(els.customerTaxId, entityTaxId);
      setDropDisplay('customer_tax_id', entityTaxId);
    }
    if (!extractedTextContainsDigits(entityTaxId)) {
      display.classList.add('docai-drop-value-warning');
      setFieldNote('customer_tax_id', 'não visível no pdf');
    }
  }

  function updateStaticDisplays() {
    if (els.confidenceDisplay) {
      const numeric = Number(els.confidence?.value || 0) || 0;
      els.confidenceDisplay.textContent = numeric ? formatPct(numeric) : '--';
    }
    if (els.supplierNoDisplay) {
      els.supplierNoDisplay.textContent = String(els.supplierNo?.value || '').trim() || '--';
    }
    if (els.customerFeDisplay) {
      const feid = String(els.customerFeid?.value || '').trim();
      const entityName = String(state.document?.entity?.name || '').trim();
      els.customerFeDisplay.textContent = feid ? `${feid}${entityName ? ` · ${entityName}` : ''}` : '--';
    }
  }

  function refreshAllFieldDisplays() {
    [
      'document_number', 'document_date', 'due_date', 'currency',
      'supplier_tax_id', 'supplier_name', 'customer_tax_id', 'customer_name',
      'tax_base_0', 'tax_amount_0', 'tax_base_6', 'tax_amount_6',
      'tax_base_13', 'tax_amount_13', 'tax_base_23', 'tax_amount_23',
      'net_total', 'tax_total', 'gross_total',
      'line_start_anchor', 'line_end_anchor', 'line_ref_anchor', 'line_description_anchor',
      'line_qty_anchor', 'line_unit_price_anchor', 'line_discount_anchor', 'line_total_anchor', 'line_vat_anchor',
    ].forEach((fieldKey) => setDropDisplay(fieldKey, fieldCurrentValue(fieldKey)));
    updateStaticDisplays();
    refreshCustomerTaxVisibility();
    updateLineAreaStatus();
  }

  function updateLineAreaStatus() {
    if (!els.lineAreaStatus) return;
    const area = state.adjustments.lineArea;
    if (!area) {
      els.lineAreaStatus.textContent = 'Sem area definida.';
      return;
    }
    const widthPct = Math.round((Number(area.width || 0) || 0) * 100);
    const heightPct = Math.round((Number(area.height || 0) || 0) * 100);
    els.lineAreaStatus.textContent = `Area definida (${widthPct}% x ${heightPct}%).`;
  }

  function activeDrawMode() {
    if (state.adjustments.cropMode) return 'crop';
    if (state.adjustments.lineAreaMode) return 'line_area';
    return '';
  }

  function parseAssignedDate(rawValue) {
    return normalizeDateInputValue(rawValue.match(/\d{4}-\d{2}-\d{2}|\d{2}[-/.]\d{2}[-/.]\d{4}|\d{4}[-/.]\d{2}[-/.]\d{2}/)?.[0] || rawValue);
  }

  function taxBucketFromRate(rateValue) {
    const rate = Number(rateValue || 0);
    return taxFieldMap[rate] || null;
  }

  function lineConfigFromForm() {
    return {
      enabled: true,
      start_anchor: String(els.lineStartAnchor?.value || '').trim(),
      end_anchor: String(els.lineEndAnchor?.value || '').trim(),
      area: state.adjustments.lineArea ? {
        ...state.adjustments.lineArea,
        page: Number(state.previewPage || 1) || 1,
      } : null,
      columns: {
        ref: { anchor: String(els.lineRefAnchor?.value || '').trim() },
        description: { anchor: String(els.lineDescriptionAnchor?.value || '').trim() },
        qty: { anchor: String(els.lineQtyAnchor?.value || '').trim() },
        unit_price: { anchor: String(els.lineUnitPriceAnchor?.value || '').trim() },
        discount: { anchor: String(els.lineDiscountAnchor?.value || '').trim() },
        total: { anchor: String(els.lineTotalAnchor?.value || '').trim() },
        vat: { anchor: String(els.lineVatAnchor?.value || '').trim() },
      },
    };
  }

  function applyLineConfigToForm(linesConfig = {}) {
    const columns = linesConfig.columns || {};
    setInputValue(els.lineStartAnchor, linesConfig.start_anchor || '');
    setInputValue(els.lineEndAnchor, linesConfig.end_anchor || '');
    setInputValue(els.lineRefAnchor, columns.ref?.anchor || '');
    setInputValue(els.lineDescriptionAnchor, columns.description?.anchor || '');
    setInputValue(els.lineQtyAnchor, columns.qty?.anchor || '');
    setInputValue(els.lineUnitPriceAnchor, columns.unit_price?.anchor || '');
    setInputValue(els.lineDiscountAnchor, columns.discount?.anchor || '');
    setInputValue(els.lineTotalAnchor, columns.total?.anchor || '');
    setInputValue(els.lineVatAnchor, columns.vat?.anchor || '');
    state.adjustments.lineArea = linesConfig.area && typeof linesConfig.area === 'object'
      ? {
          left: Number(linesConfig.area.left || 0) || 0,
          top: Number(linesConfig.area.top || 0) || 0,
          width: Number(linesConfig.area.width || 0) || 0,
          height: Number(linesConfig.area.height || 0) || 0,
        }
      : null;
    updateLineAreaStatus();
    updateCropOverlay();
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

  async function resolveCustomerEntity(matchMode = 'auto') {
    const taxId = String(els.customerTaxId?.value || '').trim();
    const name = String(els.customerName?.value || '').trim();
    const query = matchMode === 'name' ? name : (taxId || name);
    if (!query || query.length < 2) {
      setInputValue(els.customerFeid, '');
      if (state.document) {
        state.document.entity = {};
        state.document.feid = null;
      }
      refreshAllFieldDisplays();
      return null;
    }
    try {
      const payload = await fetchJson(`/api/document_ai/entities/resolve?q=${encodeURIComponent(query)}&mode=${encodeURIComponent(matchMode)}`);
      if (payload?.feid) {
        setInputValue(els.customerFeid, payload.feid);
        if (state.document) state.document.feid = payload.feid;
        if (payload.tax_id && !taxId) {
          setInputValue(els.customerTaxId, payload.tax_id);
        }
        if (payload.name && !name) {
          setInputValue(els.customerName, payload.name);
        }
        if (state.document) state.document.entity = payload;
        refreshAllFieldDisplays();
        refreshTemplateSelectLabels();
        setStatus(`Entidade FE identificada: ${payload.feid} · ${payload.name || ''}`.trim());
        return payload;
      }
      setInputValue(els.customerFeid, '');
      if (state.document) {
        state.document.entity = {};
        state.document.feid = null;
      }
      refreshAllFieldDisplays();
      setStatus('Entidade FE não identificada para o cliente.', true);
      return null;
    } catch (error) {
      console.error(error);
      setStatus(error.message || 'Falha ao identificar entidade FE.', true);
      return null;
    }
  }

  function supplierSearchQuery(matchMode = 'auto') {
    const taxId = String(els.supplierTaxId?.value || '').trim();
    const name = String(els.supplierName?.value || '').trim();
    const no = String(els.supplierNo?.value || '').trim();
    if (matchMode === 'name') return name;
    if (matchMode === 'tax_id') return taxId;
    return taxId || name || no;
  }

  function currentDocumentFeid() {
    return Number(els.customerFeid?.value || state.document?.feid || state.document?.entity?.feid || 0) || 0;
  }

  function applySupplierCandidate(candidate) {
    if (!candidate) return;
    setInputValue(els.supplierNo, candidate.no || candidate.supplier_no || '');
    setInputValue(els.supplierName, candidate.name || candidate.supplier_name || '');
    setInputValue(els.supplierTaxId, candidate.tax_id || candidate.supplier_tax_id || '');
    if (state.document) {
      state.document.supplier_no = candidate.no || candidate.supplier_no || null;
      state.document.supplier_name = candidate.name || candidate.supplier_name || '';
      state.document.supplier_tax_id_detected = candidate.tax_id || candidate.supplier_tax_id || '';
    }
    refreshAllFieldDisplays();
    refreshTemplateSelectLabels();
    setStatus(`Fornecedor identificado: ${candidate.no || candidate.supplier_no || ''} · ${candidate.name || candidate.supplier_name || ''}`.trim());
  }

  function closeSupplierModal() {
    els.supplierModal?.classList.remove('is-open');
    els.supplierModal?.setAttribute('aria-hidden', 'true');
  }

  function openSupplierModal(candidates) {
    state.supplierCandidates = Array.isArray(candidates) ? candidates : [];
    if (!els.supplierModal || !els.supplierModalBody) return;
    els.supplierModalBody.innerHTML = state.supplierCandidates.length
      ? state.supplierCandidates.map((candidate, index) => `
          <button type="button" class="docai-candidate-option" data-supplier-index="${index}">
            <span class="docai-candidate-main">
              <strong>${escapeHtml(candidate.name || '--')}</strong>
              <span>Nº ${escapeHtml(String(candidate.no || '--'))}${candidate.tax_id ? ` · NIF ${escapeHtml(candidate.tax_id)}` : ''}</span>
            </span>
            <span class="docai-candidate-score">${Math.round(Number(candidate.score || 0) * 100)}%</span>
          </button>
        `).join('')
      : '<div class="docai-empty-state">Sem fornecedores compatíveis.</div>';
    els.supplierModal.classList.add('is-open');
    els.supplierModal.setAttribute('aria-hidden', 'false');
  }

  async function resolveSupplierFromField(matchMode = 'auto') {
    const query = supplierSearchQuery(matchMode);
    if (!query || query.length < 2) {
      setStatus('Indica primeiro o nome ou NIF do fornecedor.', true);
      return null;
    }
    const feid = currentDocumentFeid();
    if (!feid) {
      setStatus('Identifica primeiro a Entidade FE do cliente antes de escolher o fornecedor.', true);
      showMessage('Identifica primeiro a Entidade FE do cliente antes de escolher o fornecedor.', 'warning');
      return null;
    }
    try {
      const params = new URLSearchParams({
        q: query,
        limit: '8',
        feid: String(feid),
      });
      const candidates = await fetchJson(`/api/document_ai/suppliers/search?${params.toString()}`);
      if (!Array.isArray(candidates) || candidates.length === 0) {
        setStatus('Fornecedor não identificado em FL.', true);
        return null;
      }
      if (candidates.length === 1) {
        applySupplierCandidate(candidates[0]);
        return candidates[0];
      }
      openSupplierModal(candidates);
      setStatus(`${candidates.length} fornecedores possíveis. Escolhe a opção correta.`);
      return null;
    } catch (error) {
      console.error(error);
      setStatus(error.message || 'Falha ao pesquisar fornecedor.', true);
      return null;
    }
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

  function getPreviewHost() {
    return els.previewBody?.querySelector('.docai-preview-image-host') || null;
  }

  function getPreviewImage() {
    return els.previewBody?.querySelector('.docai-preview-image') || null;
  }

  function updatePreviewTransform() {
    const host = getPreviewHost();
    const image = getPreviewImage();
    if (!host || !image) return;
    const rotate = Number(state.adjustments.rotate || 0) || 0;
    host.classList.toggle('is-rotated', !!rotate);
    host.style.transform = rotate ? `rotate(${rotate}deg)` : '';
  }

  function updateCropOverlay() {
    const host = getPreviewHost();
    if (!host) return;
    let layer = host.querySelector('.docai-crop-layer');
    if (!layer) {
      layer = document.createElement('div');
      layer.className = 'docai-crop-layer';
      host.appendChild(layer);
    }
    layer.classList.toggle('is-active', !!state.adjustments.cropMode);
    layer.innerHTML = '';
    const committedCrop = state.adjustments.crop;
    const committedLineArea = state.adjustments.lineArea;
    const transientRect = state.adjustments.dragRect;
    const transientKind = state.adjustments.draggingKind || activeDrawMode();
    const boxes = [];
    if (committedCrop) boxes.push({ rect: committedCrop, className: 'docai-crop-rect' });
    if (committedLineArea) boxes.push({ rect: committedLineArea, className: 'docai-line-area-rect' });
    if (transientRect && transientKind === 'crop') boxes.push({ rect: transientRect, className: 'docai-crop-rect' });
    if (transientRect && transientKind === 'line_area') boxes.push({ rect: transientRect, className: 'docai-line-area-rect' });
    boxes.forEach(({ rect, className }) => {
      if (!rect) return;
      const box = document.createElement('div');
      box.className = className;
      box.style.left = `${rect.left * 100}%`;
      box.style.top = `${rect.top * 100}%`;
      box.style.width = `${rect.width * 100}%`;
      box.style.height = `${rect.height * 100}%`;
      layer.appendChild(box);
    });
  }

  function setCropMode(enabled) {
    state.adjustments.cropMode = !!enabled;
    if (enabled) {
      state.adjustments.lineAreaMode = false;
    }
    if (!enabled) {
      state.adjustments.dragging = false;
      state.adjustments.dragStart = null;
      state.adjustments.dragRect = null;
      state.adjustments.draggingKind = '';
    }
    if (els.cropToggle) {
      els.cropToggle.classList.toggle('is-active', state.adjustments.cropMode);
    }
    updateCropOverlay();
  }

  function setLineAreaMode(enabled) {
    state.adjustments.lineAreaMode = !!enabled;
    if (enabled) {
      state.adjustments.cropMode = false;
    }
    if (!enabled) {
      state.adjustments.dragging = false;
      state.adjustments.dragStart = null;
      state.adjustments.dragRect = null;
      state.adjustments.draggingKind = '';
    }
    if (els.lineAreaBtn) {
      els.lineAreaBtn.classList.toggle('is-active', state.adjustments.lineAreaMode);
    }
    updateCropOverlay();
  }

  function buildManualAdjustments() {
    const adjustments = {};
    const rotate = Number(state.adjustments.rotate || 0) || 0;
    if (rotate) adjustments.rotate = rotate;
    if (state.adjustments.crop) {
      adjustments.crop = {
        ...state.adjustments.crop,
        unit: 'ratio',
        page: Number(state.previewPage || 1) || 1,
      };
    }
    return Object.keys(adjustments).length ? adjustments : null;
  }

  function describePendingAdjustments() {
    const adjustments = buildManualAdjustments();
    if (!adjustments) return '';
    const parts = [];
    if (adjustments.crop) parts.push('recorte');
    if (adjustments.rotate) parts.push(`rotação ${adjustments.rotate}°`);
    return parts.join(' + ');
  }

  function notifyPendingAdjustments() {
    const description = describePendingAdjustments();
    if (!description) {
      setStatus('Ajustes removidos.');
      return;
    }
    setStatus(`Ajuste pendente: ${description}. Clique em "Reprocessar com OCR", "Fallback visual" ou "Reprocessar auto" para aplicar.`);
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
      updatePreviewTransform();
      updateCropOverlay();
      return;
    }
    if (mime.startsWith('image/') || ['.png', '.jpg', '.jpeg', '.tif', '.tiff', '.bmp', '.webp'].includes(ext)) {
      els.previewBody.innerHTML = `
        <div class="docai-preview-stage is-image">
          <div class="docai-preview-image-host is-image">
            <img class="docai-preview-image is-image" src="${escapeHtml(path)}" alt="${escapeHtml(documentPayload.file_name || 'Documento')}">
            ${buildPreviewHighlight(highlightBlock)}
          </div>
        </div>
      `;
      updatePreviewTransform();
      updateCropOverlay();
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
      <div draggable="true" class="docai-ocr-line${state.selectedBlockId === block.id ? ' is-active' : ''}" data-block-id="${escapeHtml(block.id)}" role="button" tabindex="0">
        <div class="docai-ocr-line-top">
          <span>Página ${escapeHtml(block.page || 1)} · Linha ${escapeHtml(block.line_no || '')}</span>
        </div>
        <div>${escapeHtml(block.text || '')}</div>
      </div>
    `).join('');
    els.ocrList.querySelectorAll('[data-block-id]').forEach((blockEl) => {
      blockEl.draggable = false;
      blockEl.addEventListener('pointerdown', () => {
        const blockId = blockEl.dataset.blockId || '';
        if (!blockId) return;
        const block = (state.document?.text_blocks || []).find((item) => item.id === blockId);
        state.selectedBlockId = blockId;
        state.draggingBlockId = blockId;
        state.selectedText = String(block?.text || '').trim();
        if (els.selectedText) els.selectedText.value = state.selectedText || '';
      });
      blockEl.addEventListener('pointerdown', (event) => {
        if (event.button !== 0) return;
        const blockId = blockEl.dataset.blockId || '';
        if (!blockId) return;
        startPointerDrag(blockId, event);
      });
      blockEl.addEventListener('keydown', (event) => {
        if (event.key !== 'Enter' && event.key !== ' ') return;
        event.preventDefault();
        const blockId = blockEl.dataset.blockId || '';
        if (!blockId) return;
        const block = (state.document?.text_blocks || []).find((item) => item.id === blockId);
        state.selectedBlockId = blockId;
        state.selectedText = String(block?.text || '').trim();
        if (els.selectedText) els.selectedText.value = state.selectedText || '';
        state.previewPage = Number(block?.page || 1) || 1;
        renderOcrList(state.document?.text_blocks || []);
        renderPreview(state.document || {}, block);
      });
    });
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

  function uniqueList(values) {
    const out = [];
    (values || []).forEach((value) => {
      const text = String(value || '').trim();
      if (!text) return;
      const key = normalizeSearchValue(text);
      if (!key || out.some((item) => normalizeSearchValue(item) === key)) return;
      out.push(text);
    });
    return out;
  }

  function keywordListFromInput() {
    return uniqueList(String(els.templateKeywords?.value || '')
      .split(/[\n,;]+/)
      .map((item) => item.trim()));
  }

  function keywordNameVariants(name) {
    const raw = String(name || '').trim();
    if (!raw) return [];
    const compact = raw.replace(/\s+/g, ' ').trim();
    const suffixes = ['SA', 'SAS', 'SARL', 'LDA', 'LIMITED', 'LTD', 'GMBH', 'BV', 'SL'];
    const tokens = compact.split(' ').filter(Boolean);
    const variants = [compact];
    if (tokens.length > 1 && suffixes.includes(tokens[0].toUpperCase())) {
      variants.push([...tokens.slice(1), tokens[0]].join(' '));
      variants.push(tokens.slice(1).join(' '));
    }
    if (tokens.length > 1 && suffixes.includes(tokens[tokens.length - 1].toUpperCase())) {
      variants.push(tokens.slice(0, -1).join(' '));
    }
    return uniqueList(variants);
  }

  function defaultTemplateKeywords() {
    const supplierName = String(els.supplierName?.value || state.document?.supplier_name || state.document?.supplier_name_detected || '').trim();
    const entityName = String(state.document?.entity?.name || els.customerName?.value || '').trim();
    const selectedText = String(state.selectedText || '').trim();
    const docType = String(els.docType?.value || state.document?.doc_type || '').trim();
    const out = [
      ...keywordNameVariants(supplierName),
      ...keywordNameVariants(entityName),
    ];
    if (docType === 'delivery_note') out.unshift('BON');
    if (/bon/i.test(selectedText) && selectedText.length <= 80) out.unshift(selectedText);
    return uniqueList(out);
  }

  function setTemplateKeywords(values) {
    const keywords = uniqueList(values);
    setInputValue(els.templateKeywords, keywords.join(', '));
    if (els.templateKeywordsBtn) {
      els.templateKeywordsBtn.classList.toggle('is-active', keywords.length > 0);
      els.templateKeywordsBtn.title = keywords.length
        ? `Palavras-chave: ${keywords.join(', ')}`
        : 'Palavras-chave do template';
    }
    const draft = ensureDraftTemplate();
    draft.match_rules = {
      ...(draft.match_rules || {}),
      keywords,
    };
  }

  function ensureDefaultTemplateKeywords() {
    setTemplateKeywords([...keywordListFromInput(), ...defaultTemplateKeywords()]);
  }

  function openKeywordsModal() {
    if (!els.keywordsModal || !els.keywordsText) return;
    ensureDefaultTemplateKeywords();
    els.keywordsText.value = keywordListFromInput().join('\n');
    els.keywordsModal.classList.add('is-open');
    els.keywordsModal.setAttribute('aria-hidden', 'false');
    setTimeout(() => els.keywordsText?.focus(), 0);
  }

  function closeKeywordsModal() {
    els.keywordsModal?.classList.remove('is-open');
    els.keywordsModal?.setAttribute('aria-hidden', 'true');
  }

  function applyKeywordsModal() {
    setTemplateKeywords(String(els.keywordsText?.value || '').split(/\n+/));
    closeKeywordsModal();
    setStatus('Palavras-chave do template atualizadas.');
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

  function isPlaceholderTemplateName(name) {
    const normalized = normalizeSearchValue(name);
    return !normalized
      || normalized === 'template'
      || normalized === 'novo template'
      || normalized.includes('unknown')
      || normalized.includes('desconhecido');
  }

  function docTypeLabel(value) {
    const docType = String(value || '').trim() || 'unknown';
    const item = (state.lookups?.doc_types || []).find((entry) => entry.value === docType);
    return item?.label || docType;
  }

  function templateDisplayName(template) {
    const rawName = String(template?.name || '').trim();
    if (!isPlaceholderTemplateName(rawName)) return rawName;
    const currentFeid = Number(els.customerFeid?.value || state.document?.feid || 0) || 0;
    const currentSupplierNo = Number(els.supplierNo?.value || 0) || 0;
    const templateFeid = Number(template?.feid || 0) || 0;
    const templateSupplierNo = Number(template?.supplier_no || 0) || 0;
    const canUseCurrentValues = (!templateFeid || templateFeid === currentFeid) && (!templateSupplierNo || templateSupplierNo === currentSupplierNo);
    const selectedDocType = String(els.docType?.value || '').trim();
    const docType = selectedDocType && selectedDocType !== 'unknown' && canUseCurrentValues
      ? selectedDocType
      : (template?.doc_type || selectedDocType || 'unknown');
    const supplierName = canUseCurrentValues
      ? String(els.supplierName?.value || template?.supplier_name || '').trim()
      : String(template?.supplier_name || '').trim();
    const entityName = canUseCurrentValues
      ? String(state.document?.entity?.name || els.customerName?.value || '').trim()
      : '';
    const parts = [docTypeLabel(docType), supplierName, entityName].filter(Boolean);
    return parts.join(' · ') || rawName || 'Novo template';
  }

  function populateTemplateSelect(templates, selectedId) {
    if (!els.templateSelect) return;
    state.templateMap.clear();
    const options = ['<option value="">Sem template</option>'];
    (templates || []).forEach((template) => {
      state.templateMap.set(template.id, template);
      const displayName = templateDisplayName(template);
      options.push(`<option value="${escapeHtml(template.id)}">${escapeHtml(displayName)}</option>`);
    });
    els.templateSelect.innerHTML = options.join('');
    els.templateSelect.value = selectedId || '';
  }

  function refreshTemplateSelectLabels() {
    if (!els.templateSelect || !state.templateMap.size) return;
    populateTemplateSelect(Array.from(state.templateMap.values()), els.templateSelect.value || '');
  }

  function applyDocumentToForm(documentPayload) {
    const result = documentPayload.result || {};
    els.docType.value = documentPayload.doc_type || result.document_type || 'unknown';
    setInputValue(els.supplierNo, documentPayload.supplier_no || result.supplier?.supplier_no || '');
    setInputValue(els.supplierName, documentPayload.supplier_name || result.supplier?.name || '');
    setInputValue(els.supplierTaxId, result.supplier?.tax_id || documentPayload.supplier_tax_id_detected || '');
    setInputValue(els.customerTaxId, result.customer?.tax_id || '');
    setInputValue(els.customerFeid, documentPayload.feid || documentPayload.entity?.feid || result.customer?.feid || '');
    setInputValue(els.confidence, Number(documentPayload.confidence || 0).toFixed(2));
    setInputValue(els.documentNumber, result.document_number || '');
    setInputValue(els.documentDate, result.document_date || '');
    setInputValue(els.dueDate, result.due_date || '');
    setInputValue(els.currency, result.currency || '');
    setInputValue(els.customerName, result.customer?.name || '');
    setInputValue(els.netTotal, result.totals?.net_total ?? '');
    setInputValue(els.taxTotal, result.totals?.tax_total ?? '');
    setInputValue(els.grossTotal, result.totals?.gross_total ?? '');
    Object.values(taxFieldMap).forEach((bucket) => {
      setInputValue(bucket.base, '');
      setInputValue(bucket.tax, '');
    });
    (result.taxes || []).forEach((item) => {
      const bucket = taxBucketFromRate(item.tax_rate);
      if (!bucket) return;
      setInputValue(bucket.base, item.taxable_base ?? item.net_total ?? item.base_amount ?? '');
      setInputValue(bucket.tax, item.tax_amount ?? item.vat_amount ?? '');
    });
    applyLineConfigToForm(documentPayload.template_draft?.lines || documentPayload.template?.definition?.lines || {});
    renderTags(els.warnings, documentPayload.warnings, 'warning');
    renderTags(els.errors, documentPayload.errors, 'error');
    updateLinesSummary(result.lines || []);

    setInputValue(els.templateName, documentPayload.template_draft?.name || '');
    setInputValue(els.templateFingerprint, documentPayload.template?.fingerprint || '');
    setInputValue(els.templateScoreMin, documentPayload.template?.score_min_match || documentPayload.template_draft?.score_min_match || 0.55);
    const keywords = documentPayload.template?.match_rules?.keywords || documentPayload.template_draft?.match_rules?.keywords || [];
    setTemplateKeywords([...(Array.isArray(keywords) ? keywords : []), ...defaultTemplateKeywords()]);
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
      feid: Number(els.customerFeid?.value || 0) || null,
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
      due_date: 'Data vencimento',
      net_total: 'Base',
      tax_total: 'IVA',
      gross_total: 'Total bruto',
      currency: 'Moeda',
      supplier_tax_id: 'NIF fornecedor',
      supplier_name: 'Nome fornecedor',
      customer_tax_id: 'NIF cliente',
      customer_name: 'Cliente',
      tax_base_0: 'Base 0%',
      tax_amount_0: 'IVA 0%',
      tax_base_6: 'Base 6%',
      tax_amount_6: 'IVA 6%',
      tax_base_13: 'Base 13%',
      tax_amount_13: 'IVA 13%',
      tax_base_23: 'Base 23%',
      tax_amount_23: 'IVA 23%',
    };
    const genericRegex = {
      document_number: '(?i)([A-Z0-9][A-Z0-9/.-]{2,})',
      document_date: '(\\d{4}[-/]\\d{2}[-/]\\d{2}|\\d{2}[-/]\\d{2}[-/]\\d{4})',
      due_date: '(\\d{4}[-/]\\d{2}[-/]\\d{2}|\\d{2}[-/]\\d{2}[-/]\\d{4})',
      net_total: '(-?\\d{1,3}(?:[.\\s]\\d{3})*(?:,\\d{2})|-?\\d+(?:[.,]\\d{2}))',
      tax_total: '(-?\\d{1,3}(?:[.\\s]\\d{3})*(?:,\\d{2})|-?\\d+(?:[.,]\\d{2}))',
      gross_total: '(-?\\d{1,3}(?:[.\\s]\\d{3})*(?:,\\d{2})|-?\\d+(?:[.,]\\d{2}))',
      tax_base_0: '(-?\\d{1,3}(?:[.\\s]\\d{3})*(?:,\\d{2})|-?\\d+(?:[.,]\\d{2}))',
      tax_amount_0: '(-?\\d{1,3}(?:[.\\s]\\d{3})*(?:,\\d{2})|-?\\d+(?:[.,]\\d{2}))',
      tax_base_6: '(-?\\d{1,3}(?:[.\\s]\\d{3})*(?:,\\d{2})|-?\\d+(?:[.,]\\d{2}))',
      tax_amount_6: '(-?\\d{1,3}(?:[.\\s]\\d{3})*(?:,\\d{2})|-?\\d+(?:[.,]\\d{2}))',
      tax_base_13: '(-?\\d{1,3}(?:[.\\s]\\d{3})*(?:,\\d{2})|-?\\d+(?:[.,]\\d{2}))',
      tax_amount_13: '(-?\\d{1,3}(?:[.\\s]\\d{3})*(?:,\\d{2})|-?\\d+(?:[.,]\\d{2}))',
      tax_base_23: '(-?\\d{1,3}(?:[.\\s]\\d{3})*(?:,\\d{2})|-?\\d+(?:[.,]\\d{2}))',
      tax_amount_23: '(-?\\d{1,3}(?:[.\\s]\\d{3})*(?:,\\d{2})|-?\\d+(?:[.,]\\d{2}))',
      currency: '(?i)\\b(EUR|USD|GBP|CHF|BRL|AOA|MZN)\\b',
      supplier_tax_id: '(\\d{9,14})',
      supplier_name: '(.+)',
      customer_tax_id: '(\\d{9,14})',
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
        postprocess: ['document_date', 'due_date'].includes(fieldKey)
          ? 'date'
          : (['net_total', 'tax_total', 'gross_total', 'tax_base_0', 'tax_amount_0', 'tax_base_6', 'tax_amount_6', 'tax_base_13', 'tax_amount_13', 'tax_base_23', 'tax_amount_23'].includes(fieldKey)
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

  function fieldKeyLabel(fieldKey) {
    const mapping = {
      document_number: 'Nº documento',
      document_date: 'Data documento',
      due_date: 'Data vencimento',
      supplier_tax_id: 'NIF fornecedor',
      supplier_name: 'Nome fornecedor',
      customer_tax_id: 'NIF cliente',
      customer_name: 'Nome cliente',
      currency: 'Moeda',
      net_total: 'Total base',
      tax_total: 'Total IVA',
      gross_total: 'Total documento',
      tax_base_0: 'Base 0%',
      tax_amount_0: 'IVA 0%',
      tax_base_6: 'Base 6%',
      tax_amount_6: 'IVA 6%',
      tax_base_13: 'Base 13%',
      tax_amount_13: 'IVA 13%',
      tax_base_23: 'Base 23%',
      tax_amount_23: 'IVA 23%',
      line_start_anchor: 'Início das linhas',
      line_end_anchor: 'Fim das linhas',
      line_ref_anchor: 'Coluna referência',
      line_description_anchor: 'Coluna designação',
      line_qty_anchor: 'Coluna quantidade',
      line_unit_price_anchor: 'Coluna preço',
      line_discount_anchor: 'Coluna desconto',
      line_total_anchor: 'Coluna total',
      line_vat_anchor: 'Coluna IVA',
    };
    return mapping[fieldKey] || fieldKey;
  }

  function lineFieldElement(fieldKey) {
    const mapping = {
      line_start_anchor: els.lineStartAnchor,
      line_end_anchor: els.lineEndAnchor,
      line_ref_anchor: els.lineRefAnchor,
      line_description_anchor: els.lineDescriptionAnchor,
      line_qty_anchor: els.lineQtyAnchor,
      line_unit_price_anchor: els.lineUnitPriceAnchor,
      line_discount_anchor: els.lineDiscountAnchor,
      line_total_anchor: els.lineTotalAnchor,
      line_vat_anchor: els.lineVatAnchor,
    };
    return mapping[fieldKey] || null;
  }

  function assignTextToField(fieldKey, rawValue) {
    const raw = String(rawValue || '').trim();
    if (!raw || !fieldKey) {
      showMessage('Seleciona ou arrasta primeiro uma linha de texto.', 'warning');
      return;
    }

    if (fieldKey.startsWith('line_')) {
      setInputValue(lineFieldElement(fieldKey), raw);
      ensureDraftTemplate().lines = lineConfigFromForm();
      showMessage(`Linha atribuída a ${fieldKeyLabel(fieldKey)}.`, 'success');
      setStatus(`Regra de linhas atualizada em ${fieldKeyLabel(fieldKey)}. Guarda o template ou reprocessa para testar o parsing das linhas.`);
      return;
    }

    if (fieldKey === 'document_number') setInputValue(els.documentNumber, raw);
    if (fieldKey === 'document_date') setInputValue(els.documentDate, parseAssignedDate(raw));
    if (fieldKey === 'due_date') setInputValue(els.dueDate, parseAssignedDate(raw));
    if (fieldKey === 'net_total') setInputValue(els.netTotal, normalizeNumericValue(raw));
    if (fieldKey === 'tax_total') setInputValue(els.taxTotal, normalizeNumericValue(raw));
    if (fieldKey === 'gross_total') setInputValue(els.grossTotal, normalizeNumericValue(raw));
    if (fieldKey === 'currency') {
      const currencyMatch = raw.match(/\b(EUR|USD|GBP|CHF|BRL|AOA|MZN)\b/i);
      setInputValue(els.currency, currencyMatch ? currencyMatch[1].toUpperCase() : raw.toUpperCase());
    }
    if (fieldKey === 'supplier_tax_id') setInputValue(els.supplierTaxId, normalizeTaxIdValue(raw) || raw);
    if (fieldKey === 'supplier_name') setInputValue(els.supplierName, raw);
    if (fieldKey === 'customer_tax_id') setInputValue(els.customerTaxId, normalizeTaxIdValue(raw) || raw);
    if (fieldKey === 'customer_name') setInputValue(els.customerName, raw);
    if (fieldKey === 'tax_base_0') setInputValue(els.taxBase0, normalizeNumericValue(raw));
    if (fieldKey === 'tax_amount_0') setInputValue(els.taxAmount0, normalizeNumericValue(raw));
    if (fieldKey === 'tax_base_6') setInputValue(els.taxBase6, normalizeNumericValue(raw));
    if (fieldKey === 'tax_amount_6') setInputValue(els.taxAmount6, normalizeNumericValue(raw));
    if (fieldKey === 'tax_base_13') setInputValue(els.taxBase13, normalizeNumericValue(raw));
    if (fieldKey === 'tax_amount_13') setInputValue(els.taxAmount13, normalizeNumericValue(raw));
    if (fieldKey === 'tax_base_23') setInputValue(els.taxBase23, normalizeNumericValue(raw));
    if (fieldKey === 'tax_amount_23') setInputValue(els.taxAmount23, normalizeNumericValue(raw));

    upsertDraftField(fieldKey, raw);
    showMessage(`Linha atribuída a ${fieldKeyLabel(fieldKey)}.`, 'success');
    setStatus(`Campo ${fieldKeyLabel(fieldKey)} atualizado a partir do OCR.`);
  }

  function assignBlockToField(blockId, fieldKey) {
    const block = (state.document?.text_blocks || []).find((item) => item.id === blockId);
    if (!block || !fieldKey) {
      if (!blockId) {
        setStatus('Nenhuma linha OCR selecionada para atribuir.', true);
      }
      return;
    }
    state.selectedBlockId = block.id || '';
    state.selectedText = String(block.text || '').trim();
    if (els.selectedText) els.selectedText.value = state.selectedText || '';
    state.previewPage = Number(block.page || 1) || 1;
    renderOcrList(state.document?.text_blocks || []);
    renderPreview(state.document || {}, block);
    assignTextToField(fieldKey, state.selectedText);
  }

  function currentResultPayload() {
    const taxes = [0, 6, 13, 23]
      .map((rate) => {
        const bucket = taxBucketFromRate(rate);
        if (!bucket) return null;
        const taxableBase = numericInputValue(bucket.base);
        const taxAmount = numericInputValue(bucket.tax);
        if (!taxableBase && !taxAmount) return null;
        return {
          tax_rate: rate,
          taxable_base: taxableBase,
          tax_amount: taxAmount,
          gross_total: Number((taxableBase + taxAmount).toFixed(2)),
        };
      })
      .filter(Boolean);

    return {
      document_type: els.docType.value || 'unknown',
      supplier: {
        supplier_no: Number(els.supplierNo.value || 0) || null,
        tax_id: String(els.supplierTaxId.value || '').trim(),
        name: els.supplierName.value || '',
      },
      customer: {
        feid: Number(els.customerFeid?.value || 0) || null,
        tax_id: String(els.customerTaxId.value || '').trim(),
        name: els.customerName.value || '',
      },
      document_number: els.documentNumber.value || '',
      document_date: els.documentDate.value || '',
      due_date: els.dueDate.value || '',
      currency: els.currency.value || '',
      totals: {
        net_total: numericInputValue(els.netTotal),
        tax_total: numericInputValue(els.taxTotal),
        gross_total: numericInputValue(els.grossTotal),
      },
      taxes,
      lines: state.document?.result?.lines || [],
      warnings: state.document?.warnings || [],
    };
  }

  function currentTemplatePayload() {
    const draft = ensureDraftTemplate();
    const linesConfig = lineConfigFromForm();
    const headerAliases = Object.values(linesConfig.columns || {})
      .map((item) => String(item?.anchor || '').trim())
      .filter(Boolean);
    const stopKeywords = [String(linesConfig.end_anchor || '').trim()]
      .filter(Boolean);
    const draftSamples = {
      document_number: String(els.documentNumber?.value || '').trim(),
      document_date: String(els.documentDate?.value || '').trim(),
      due_date: String(els.dueDate?.value || '').trim(),
      supplier_tax_id: String(els.supplierTaxId?.value || '').trim(),
      supplier_name: String(els.supplierName?.value || '').trim(),
      customer_tax_id: String(els.customerTaxId?.value || '').trim(),
      customer_name: String(els.customerName?.value || '').trim(),
      currency: String(els.currency?.value || '').trim(),
      net_total: String(els.netTotal?.value || '').trim(),
      tax_total: String(els.taxTotal?.value || '').trim(),
      gross_total: String(els.grossTotal?.value || '').trim(),
      tax_base_0: String(els.taxBase0?.value || '').trim(),
      tax_amount_0: String(els.taxAmount0?.value || '').trim(),
      tax_base_6: String(els.taxBase6?.value || '').trim(),
      tax_amount_6: String(els.taxAmount6?.value || '').trim(),
      tax_base_13: String(els.taxBase13?.value || '').trim(),
      tax_amount_13: String(els.taxAmount13?.value || '').trim(),
      tax_base_23: String(els.taxBase23?.value || '').trim(),
      tax_amount_23: String(els.taxAmount23?.value || '').trim(),
    };

    draft.id = els.templateSelect.value || '';
    draft.name = isPlaceholderTemplateName(els.templateName.value) ? '' : (els.templateName.value || '');
    draft.fingerprint = els.templateFingerprint.value || '';
    draft.feid = Number(els.customerFeid?.value || 0) || state.document?.feid || null;
    draft.supplier_no = Number(els.supplierNo.value || 0) || null;
    draft.doc_type = els.docType.value || 'unknown';
    draft.score_min_match = Number(els.templateScoreMin.value || 0.55) || 0.55;
    ensureDefaultTemplateKeywords();
    draft.match_rules = {
      keywords: keywordListFromInput(),
      required: Array.isArray(draft.match_rules?.required) ? draft.match_rules.required : [],
      forbidden: Array.isArray(draft.match_rules?.forbidden) ? draft.match_rules.forbidden : [],
    };
    draft.lines = {
      ...(state.draftTemplate?.lines || draft.lines || {}),
      ...linesConfig,
      enabled: true,
      header_aliases: headerAliases,
      stop_keywords: stopKeywords,
    };
    Object.entries(draftSamples).forEach(([fieldKey, sampleValue]) => {
      if (!sampleValue) return;
      let item = (draft.fields || []).find((entry) => entry.field_key === fieldKey);
      if (!item) {
        upsertDraftField(fieldKey, sampleValue);
        item = (draft.fields || []).find((entry) => entry.field_key === fieldKey);
      }
      if (!item) return;
      item.config = {
        ...(item.config || {}),
        sample_text: sampleValue,
        sample_value: sampleValue,
      };
    });
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

  function rememberFieldAssignment(fieldKey, rawText, value, blockId = '') {
    if (!fieldKey) return;
    state.fieldAssignments[fieldKey] = {
      rawText: String(rawText || '').trim(),
      value: String(value || '').trim(),
      blockId: String(blockId || '').trim(),
    };
  }

  function removeDraftFieldAssignment(fieldKey) {
    const draft = ensureDraftTemplate();
    draft.fields = (draft.fields || []).filter((entry) => entry.field_key !== fieldKey);
    if (fieldKey.startsWith('line_')) {
      ensureDraftTemplate().lines = lineConfigFromForm();
    }
  }

  function clearFieldAssignment(fieldKey) {
    if (!fieldKey) return;
    const input = getFieldInput(fieldKey);
    setInputValue(input, '');
    delete state.fieldAssignments[fieldKey];
    removeDraftFieldAssignment(fieldKey);
    if (fieldKey === 'customer_tax_id' || fieldKey === 'customer_name') {
      setInputValue(els.customerFeid, '');
      if (state.document) {
        state.document.entity = {};
        state.document.feid = null;
      }
    }
    if ((fieldKey === 'supplier_tax_id' || fieldKey === 'supplier_name')
        && !String(els.supplierTaxId?.value || '').trim()
        && !String(els.supplierName?.value || '').trim()) {
      setInputValue(els.supplierNo, '');
      if (state.document) {
        state.document.supplier_no = null;
        state.document.supplier_name = '';
        state.document.supplier_tax_id_detected = '';
      }
    }
    refreshAllFieldDisplays();
    refreshTemplateSelectLabels();
    setStatus(`Atribuição removida de ${fieldKeyLabel(fieldKey)}.`);
  }

  function applyValueToFieldInput(fieldKey, rawValue) {
    const raw = String(rawValue || '').trim();
    if (fieldKey === 'document_number') setInputValue(els.documentNumber, raw);
    if (fieldKey === 'document_date') setInputValue(els.documentDate, parseAssignedDate(raw));
    if (fieldKey === 'due_date') setInputValue(els.dueDate, parseAssignedDate(raw));
    if (fieldKey === 'net_total') setInputValue(els.netTotal, normalizeNumericValue(raw));
    if (fieldKey === 'tax_total') setInputValue(els.taxTotal, normalizeNumericValue(raw));
    if (fieldKey === 'gross_total') setInputValue(els.grossTotal, normalizeNumericValue(raw));
    if (fieldKey === 'currency') {
      const currencyMatch = raw.match(/\b(EUR|USD|GBP|CHF|BRL|AOA|MZN)\b/i);
      setInputValue(els.currency, currencyMatch ? currencyMatch[1].toUpperCase() : raw.toUpperCase());
    }
    if (fieldKey === 'supplier_tax_id') setInputValue(els.supplierTaxId, normalizeTaxIdValue(raw) || raw);
    if (fieldKey === 'supplier_name') setInputValue(els.supplierName, raw);
    if (fieldKey === 'customer_tax_id') setInputValue(els.customerTaxId, normalizeTaxIdValue(raw) || raw);
    if (fieldKey === 'customer_name') setInputValue(els.customerName, raw);
    if (fieldKey === 'tax_base_0') setInputValue(els.taxBase0, normalizeNumericValue(raw));
    if (fieldKey === 'tax_amount_0') setInputValue(els.taxAmount0, normalizeNumericValue(raw));
    if (fieldKey === 'tax_base_6') setInputValue(els.taxBase6, normalizeNumericValue(raw));
    if (fieldKey === 'tax_amount_6') setInputValue(els.taxAmount6, normalizeNumericValue(raw));
    if (fieldKey === 'tax_base_13') setInputValue(els.taxBase13, normalizeNumericValue(raw));
    if (fieldKey === 'tax_amount_13') setInputValue(els.taxAmount13, normalizeNumericValue(raw));
    if (fieldKey === 'tax_base_23') setInputValue(els.taxBase23, normalizeNumericValue(raw));
    if (fieldKey === 'tax_amount_23') setInputValue(els.taxAmount23, normalizeNumericValue(raw));
    if (fieldKey.startsWith('line_')) setInputValue(lineFieldElement(fieldKey), raw);
  }

  function upsertDraftField(fieldKey, sourceText, selectedValue = sourceText) {
    const draft = ensureDraftTemplate();
    const source = String(sourceText || '').trim();
    const sampleValue = String(selectedValue || source).trim();
    const labelMap = {
      document_number: 'Numero documento',
      document_date: 'Data documento',
      due_date: 'Data vencimento',
      net_total: 'Base',
      tax_total: 'IVA',
      gross_total: 'Total bruto',
      currency: 'Moeda',
      supplier_tax_id: 'NIF fornecedor',
      supplier_name: 'Nome fornecedor',
      customer_tax_id: 'NIF cliente',
      customer_name: 'Cliente',
      tax_base_0: 'Base 0%',
      tax_amount_0: 'IVA 0%',
      tax_base_6: 'Base 6%',
      tax_amount_6: 'IVA 6%',
      tax_base_13: 'Base 13%',
      tax_amount_13: 'IVA 13%',
      tax_base_23: 'Base 23%',
      tax_amount_23: 'IVA 23%',
    };
    const genericRegex = {
      document_number: '(?i)([A-Z0-9][A-Z0-9/.-]{2,})',
      document_date: '(\\d{4}[-/]\\d{2}[-/]\\d{2}|\\d{2}[-/]\\d{2}[-/]\\d{4})',
      due_date: '(\\d{4}[-/]\\d{2}[-/]\\d{2}|\\d{2}[-/]\\d{2}[-/]\\d{4})',
      net_total: '(-?\\d{1,3}(?:[.\\s]\\d{3})*(?:,\\d{2})|-?\\d+(?:[.,]\\d{2}))',
      tax_total: '(-?\\d{1,3}(?:[.\\s]\\d{3})*(?:,\\d{2})|-?\\d+(?:[.,]\\d{2}))',
      gross_total: '(-?\\d{1,3}(?:[.\\s]\\d{3})*(?:,\\d{2})|-?\\d+(?:[.,]\\d{2}))',
      tax_base_0: '(-?\\d{1,3}(?:[.\\s]\\d{3})*(?:,\\d{2})|-?\\d+(?:[.,]\\d{2}))',
      tax_amount_0: '(-?\\d{1,3}(?:[.\\s]\\d{3})*(?:,\\d{2})|-?\\d+(?:[.,]\\d{2}))',
      tax_base_6: '(-?\\d{1,3}(?:[.\\s]\\d{3})*(?:,\\d{2})|-?\\d+(?:[.,]\\d{2}))',
      tax_amount_6: '(-?\\d{1,3}(?:[.\\s]\\d{3})*(?:,\\d{2})|-?\\d+(?:[.,]\\d{2}))',
      tax_base_13: '(-?\\d{1,3}(?:[.\\s]\\d{3})*(?:,\\d{2})|-?\\d+(?:[.,]\\d{2}))',
      tax_amount_13: '(-?\\d{1,3}(?:[.\\s]\\d{3})*(?:,\\d{2})|-?\\d+(?:[.,]\\d{2}))',
      tax_base_23: '(-?\\d{1,3}(?:[.\\s]\\d{3})*(?:,\\d{2})|-?\\d+(?:[.,]\\d{2}))',
      tax_amount_23: '(-?\\d{1,3}(?:[.\\s]\\d{3})*(?:,\\d{2})|-?\\d+(?:[.,]\\d{2}))',
      currency: '(?i)\\b(EUR|USD|GBP|CHF|BRL|AOA|MZN)\\b',
      supplier_tax_id: '(\\d{9,14})',
      supplier_name: '(.+)',
      customer_tax_id: '(\\d{9,14})',
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
        postprocess: ['document_date', 'due_date'].includes(fieldKey)
          ? 'date'
          : (['net_total', 'tax_total', 'gross_total', 'tax_base_0', 'tax_amount_0', 'tax_base_6', 'tax_amount_6', 'tax_base_13', 'tax_amount_13', 'tax_base_23', 'tax_amount_23'].includes(fieldKey)
            ? 'decimal'
            : (fieldKey === 'currency' ? 'currency' : (fieldKey.includes('tax_id') ? 'tax_id' : 'text'))),
        config: {},
        active: true,
      };
      draft.fields.push(item);
    }
    item.anchors = [source, ...guessAnchorFromSelection(source)]
      .map((value) => String(value || '').trim())
      .filter(Boolean)
      .filter((value, index, arr) => arr.findIndex((entry) => entry.toLowerCase() === value.toLowerCase()) === index);
    item.config = {
      ...(item.config || {}),
      sample_text: source,
      sample_value: sampleValue,
    };
  }

  function assignTextToField(fieldKey, rawValue, options = {}) {
    const sourceText = String(options.sourceText || rawValue || '').trim();
    const selectedValue = String(options.selectedValue || rawValue || '').trim();
    const blockId = String(options.blockId || '').trim();
    if (!fieldKey || !selectedValue) {
      showMessage('Seleciona ou arrasta primeiro uma linha de texto.', 'warning');
      return;
    }
    if ((fieldKey === 'supplier_tax_id' || fieldKey === 'supplier_name') && !currentDocumentFeid()) {
      setStatus('Identifica primeiro a Entidade FE do cliente antes de escolher o fornecedor.', true);
      showMessage('Identifica primeiro a Entidade FE do cliente antes de escolher o fornecedor.', 'warning');
      return;
    }
    applyValueToFieldInput(fieldKey, selectedValue);
    if (fieldKey.startsWith('line_')) {
      ensureDraftTemplate().lines = lineConfigFromForm();
      rememberFieldAssignment(fieldKey, sourceText, selectedValue, blockId);
      refreshAllFieldDisplays();
      setStatus(`Regra de linhas atualizada em ${fieldKeyLabel(fieldKey)}.`);
      return;
    }
    upsertDraftField(fieldKey, sourceText, fieldCurrentValue(fieldKey) || selectedValue);
    rememberFieldAssignment(fieldKey, sourceText, fieldCurrentValue(fieldKey) || selectedValue, blockId);
    refreshAllFieldDisplays();
    setStatus(`Campo ${fieldKeyLabel(fieldKey)} atualizado a partir do OCR.`);
    if (fieldKey === 'customer_tax_id' || fieldKey === 'customer_name') {
      resolveCustomerEntity(fieldKey === 'customer_name' ? 'name' : 'tax_id');
    }
    if (fieldKey === 'supplier_tax_id' || fieldKey === 'supplier_name') {
      resolveSupplierFromField(fieldKey === 'supplier_name' ? 'name' : 'tax_id');
    }
  }

  function assignBlockToField(blockId, fieldKey) {
    const block = (state.document?.text_blocks || []).find((item) => item.id === blockId);
    if (!block || !fieldKey) {
      setStatus(`Drop invalido. bloco=${String(blockId || '') || '-'} campo=${String(fieldKey || '') || '-'}`, true);
      showMessage(`Drop invalido -> campo: ${String(fieldKey || '-')}, bloco: ${String(blockId || '-')}`, 'warning');
      return;
    }
    state.selectedBlockId = block.id || '';
    state.selectedText = String(block.text || '').trim();
    if (els.selectedText) els.selectedText.value = state.selectedText || '';
    state.previewPage = Number(block.page || 1) || 1;
    renderOcrList(state.document?.text_blocks || []);
    renderPreview(state.document || {}, block);
    const debugText = state.selectedText.length > 140 ? `${state.selectedText.slice(0, 140)}...` : state.selectedText;
    showMessage(`Drop em ${fieldKeyLabel(fieldKey)}: ${debugText}`, 'info');
    setStatus(`Drop em ${fieldKeyLabel(fieldKey)} -> ${debugText}`);
    assignTextToField(fieldKey, state.selectedText, {
      sourceText: state.selectedText,
      selectedValue: state.selectedText,
      blockId: block.id || '',
    });
  }

  function applyDocumentToForm(documentPayload) {
    const result = documentPayload.result || {};
    els.docType.value = documentPayload.doc_type || result.document_type || 'unknown';
    setInputValue(els.supplierNo, documentPayload.supplier_no || result.supplier?.supplier_no || '');
    setInputValue(els.supplierName, documentPayload.supplier_name || result.supplier?.name || '');
    setInputValue(els.supplierTaxId, result.supplier?.tax_id || documentPayload.supplier_tax_id_detected || '');
    setInputValue(els.customerTaxId, result.customer?.tax_id || '');
    setInputValue(els.customerFeid, documentPayload.feid || documentPayload.entity?.feid || result.customer?.feid || '');
    setInputValue(els.confidence, Number(documentPayload.confidence || 0).toFixed(2));
    setInputValue(els.documentNumber, result.document_number || '');
    setInputValue(els.documentDate, result.document_date || '');
    setInputValue(els.dueDate, result.due_date || '');
    setInputValue(els.currency, result.currency || '');
    setInputValue(els.customerName, result.customer?.name || '');
    setInputValue(els.netTotal, result.totals?.net_total ?? '');
    setInputValue(els.taxTotal, result.totals?.tax_total ?? '');
    setInputValue(els.grossTotal, result.totals?.gross_total ?? '');
    Object.values(taxFieldMap).forEach((bucket) => {
      setInputValue(bucket.base, '');
      setInputValue(bucket.tax, '');
    });
    (result.taxes || []).forEach((item) => {
      const bucket = taxBucketFromRate(item.tax_rate);
      if (!bucket) return;
      setInputValue(bucket.base, item.taxable_base ?? item.net_total ?? item.base_amount ?? '');
      setInputValue(bucket.tax, item.tax_amount ?? item.vat_amount ?? '');
    });
    applyLineConfigToForm(documentPayload.template?.definition?.lines || documentPayload.template_draft?.lines || {});
    renderTags(els.warnings, documentPayload.warnings, 'warning');
    renderTags(els.errors, documentPayload.errors, 'error');
    updateLinesSummary(result.lines || []);

    setInputValue(els.templateName, documentPayload.template_draft?.name || '');
    setInputValue(els.templateFingerprint, documentPayload.template?.fingerprint || '');
    setInputValue(els.templateScoreMin, documentPayload.template?.score_min_match || documentPayload.template_draft?.score_min_match || 0.55);
    const keywords = documentPayload.template?.match_rules?.keywords || documentPayload.template_draft?.match_rules?.keywords || [];
    setTemplateKeywords([...(Array.isArray(keywords) ? keywords : []), ...defaultTemplateKeywords()]);
    populateTemplateSelect(documentPayload.available_templates || [], documentPayload.template?.id || '');

    const label = documentPayload.status || 'new';
    if (els.state) {
      els.state.className = `docai-status-chip status-${label}`;
      els.state.innerHTML = `<i class="fa-solid fa-circle-info"></i><span>${escapeHtml(statusLabel(label))}</span>`;
    }
    if (els.subtitle) {
      els.subtitle.textContent = `${documentPayload.file_name || ''} | ${formatPct(documentPayload.confidence)}`;
    }
    if (els.previewMeta) {
      els.previewMeta.textContent = `${documentPayload.mime_type || documentPayload.file_ext || ''} | ${documentPayload.created_at ? new Date(documentPayload.created_at).toLocaleString('pt-PT') : ''}`;
    }
    if (els.extractionMethod) {
      els.extractionMethod.textContent = extractionMethodLabel(documentPayload.extraction_method);
    }
    if (els.extractionQuality) {
      els.extractionQuality.textContent = formatPct(documentPayload.extraction_quality_score || 0);
    }
    if (els.extractionFallback) {
      const fallbackUsed = !!documentPayload.extraction_notes?.fallback_triggered || documentPayload.extraction_method === 'ocr_image_fallback';
      els.extractionFallback.textContent = fallbackUsed ? 'Sim' : 'Nao';
    }
    if (els.processingStage) {
      els.processingStage.textContent = processingStageLabel(documentPayload.processing_stage);
    }
    if (els.extractionError) {
      els.extractionError.textContent = documentPayload.last_processing_error
        ? `Ultimo erro: ${documentPayload.last_processing_error}`
        : (documentPayload.preprocessed_image_path
          ? 'Pre-processamento visual aplicado antes do OCR.'
          : 'Sem erros no pipeline de extracao.');
    }
    state.fieldAssignments = {};
    refreshAllFieldDisplays();
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
    setTemplateKeywords(Array.isArray(draft.match_rules?.keywords) ? draft.match_rules.keywords : []);
    if (draft.doc_type) {
      els.docType.value = draft.doc_type;
    }
  }

  function applyLlmClassification(classification) {
    if (!classification || typeof classification !== 'object') return;
    const visibleValue = (value, fallback = '') => {
      if (value === null || value === undefined || value === '') return fallback;
      return value;
    };
    if (classification.document_type) {
      els.docType.value = classification.document_type || 'unknown';
      if (state.document) state.document.doc_type = classification.document_type || 'unknown';
    }
    setInputValue(els.documentNumber, visibleValue(classification.document_number, els.documentNumber?.value || ''));
    setInputValue(els.documentDate, visibleValue(classification.document_date, els.documentDate?.value || ''));
    setInputValue(els.dueDate, visibleValue(classification.due_date, els.dueDate?.value || ''));
    setInputValue(els.currency, visibleValue(classification.currency, els.currency?.value || ''));
    if (classification.supplier && typeof classification.supplier === 'object') {
      setInputValue(els.supplierNo, visibleValue(classification.supplier.supplier_no, els.supplierNo?.value || ''));
      setInputValue(els.supplierTaxId, visibleValue(classification.supplier.tax_id, els.supplierTaxId?.value || ''));
      setInputValue(els.supplierName, visibleValue(classification.supplier.name, els.supplierName?.value || ''));
    }
    if (classification.customer && typeof classification.customer === 'object') {
      setInputValue(els.customerFeid, visibleValue(classification.customer.feid, els.customerFeid?.value || ''));
      setInputValue(els.customerTaxId, visibleValue(classification.customer.tax_id, els.customerTaxId?.value || ''));
      setInputValue(els.customerName, visibleValue(classification.customer.name, els.customerName?.value || ''));
    }
    if (classification.totals && typeof classification.totals === 'object') {
      setInputValue(els.netTotal, visibleValue(classification.totals.net_total, els.netTotal?.value || ''));
      setInputValue(els.taxTotal, visibleValue(classification.totals.tax_total, els.taxTotal?.value || ''));
      setInputValue(els.grossTotal, visibleValue(classification.totals.gross_total, els.grossTotal?.value || ''));
    }
    Object.values(taxFieldMap).forEach((bucket) => {
      setInputValue(bucket.base, '');
      setInputValue(bucket.tax, '');
    });
    (classification.taxes || []).forEach((item) => {
      const bucket = taxBucketFromRate(item.tax_rate);
      if (!bucket) return;
      setInputValue(bucket.base, visibleValue(item.taxable_base, ''));
      setInputValue(bucket.tax, visibleValue(item.tax_amount, ''));
    });
    if (state.document) {
      state.document.result = {
        ...(state.document.result || {}),
        document_type: classification.document_type || state.document.result?.document_type || 'unknown',
        supplier: {
          ...(state.document.result?.supplier || {}),
          supplier_no: classification.supplier?.supplier_no || state.document.result?.supplier?.supplier_no || null,
          tax_id: classification.supplier?.tax_id || state.document.result?.supplier?.tax_id || '',
          name: classification.supplier?.name || state.document.result?.supplier?.name || '',
        },
        customer: {
          ...(state.document.result?.customer || {}),
          feid: classification.customer?.feid || state.document.result?.customer?.feid || null,
          tax_id: classification.customer?.tax_id || state.document.result?.customer?.tax_id || '',
          name: classification.customer?.name || state.document.result?.customer?.name || '',
        },
        document_number: classification.document_number || state.document.result?.document_number || '',
        document_date: classification.document_date || state.document.result?.document_date || '',
        due_date: classification.due_date || state.document.result?.due_date || '',
        currency: classification.currency || state.document.result?.currency || '',
        totals: classification.totals || state.document.result?.totals || {},
        taxes: Array.isArray(classification.taxes) ? classification.taxes : (state.document.result?.taxes || []),
      };
    }
    if (classification.confidence != null) {
      setInputValue(els.confidence, Number(classification.confidence || 0).toFixed(2));
    }
    refreshTemplateSelectLabels();
  }

  function llmClassificationSummary(classification) {
    const parts = [];
    const totals = classification?.totals || {};
    if (classification?.supplier?.name) parts.push(`Fornecedor: ${classification.supplier.name}`);
    if (classification?.customer?.name) parts.push(`Cliente: ${classification.customer.name}`);
    if (classification?.document_date) parts.push(`Data: ${classification.document_date}`);
    if (totals.net_total != null) parts.push(`S/IVA: ${totals.net_total}`);
    if (totals.tax_total != null) parts.push(`IVA: ${totals.tax_total}`);
    if (totals.gross_total != null) parts.push(`C/IVA: ${totals.gross_total}`);
    if (Array.isArray(classification?.taxes) && classification.taxes.length) {
      parts.push(`Taxas: ${classification.taxes.map((item) => `${item.tax_rate}%`).join(', ')}`);
    }
    return parts.join(' · ');
  }

  async function classifyWithLlm() {
    setStatus('A enviar documento para classificação LLM...');
    if (els.classifyLlmBtn) els.classifyLlmBtn.disabled = true;
    try {
      const payload = await fetchJson(`/api/document_ai/documents/${encodeURIComponent(documentId)}/classify_llm`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({}),
      });
      if (!payload.ok || !payload.classification) {
        throw new Error(payload.message || 'A classificação LLM não devolveu conteúdo utilizável.');
      }
      applyLlmClassification(payload.classification);
      const label = docTypeLabel(payload.classification.document_type || 'unknown');
      const summary = llmClassificationSummary(payload.classification);
      const message = `${payload.message || 'Classificação LLM aplicada.'} Tipo: ${label}${summary ? ` · ${summary}` : ''}.`;
      showMessage(message, 'success');
      setStatus(message);
    } catch (error) {
      console.error(error);
      showMessage(error.message || 'Falha na classificação LLM.', 'error');
      setStatus(error.message || 'Falha na classificação LLM.', true);
    } finally {
      if (els.classifyLlmBtn) els.classifyLlmBtn.disabled = !(state.document?.llm && state.document.llm.available);
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
        feid: detail.template.feid || detail.feid || null,
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
      if (els.classifyLlmBtn) els.classifyLlmBtn.disabled = !(detail.llm && detail.llm.available);
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
          feid: Number(els.customerFeid?.value || 0) || null,
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
      const savedMessage = payload.action === 'updated' ? 'Template existente atualizado.' : 'Template criado.';
      showMessage(savedMessage, 'success');
      if (state.document) {
        state.document.template = payload;
        state.document.doctemplatestamp = payload.id;
        const available = Array.isArray(state.document.available_templates) ? state.document.available_templates : [];
        const nextTemplate = {
          id: payload.id,
          name: payload.name,
          supplier_name: payload.supplier_name || '',
          supplier_no: payload.supplier_no || null,
          feid: payload.feid || null,
          doc_type: payload.doc_type || '',
        };
        const existingIndex = available.findIndex((item) => item.id === payload.id);
        if (existingIndex >= 0) {
          available[existingIndex] = { ...available[existingIndex], ...nextTemplate };
        } else {
          available.push(nextTemplate);
        }
        state.document.available_templates = available;
      }
      templatePayload.id = payload.id;
      populateTemplateSelect(state.document?.available_templates || [], payload.id);
      els.templateSelect.value = payload.id;
      setStatus(savedMessage);
    } catch (error) {
      console.error(error);
      showMessage(error.message || 'Falha ao guardar template.', 'error');
      setStatus(error.message || 'Falha ao guardar template.', true);
    }
  }

  async function reprocess(mode = 'auto') {
    const pendingAdjustments = describePendingAdjustments();
    const statusMap = {
      auto: 'A reprocessar documento...',
      ocr: 'A reprocessar com OCR...',
      visual_fallback: 'A reprocessar com fallback visual...',
    };
    setStatus(
      pendingAdjustments
        ? `${statusMap[mode] || 'A reprocessar documento...'} Ajustes: ${pendingAdjustments}.`
        : (statusMap[mode] || 'A reprocessar documento...')
    );
    try {
      const payload = await fetchJson(`/api/document_ai/documents/${encodeURIComponent(documentId)}/reprocess`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          template_id: els.templateSelect.value || '',
          reprocess_mode: mode,
          manual_adjustments: buildManualAdjustments(),
          current_template: currentTemplatePayload(),
        }),
      });
      state.document = payload;
      state.draftTemplate = payload.template_draft || (payload.template ? {
          id: payload.template.id,
          name: payload.template.name,
          feid: payload.template.feid || payload.feid || null,
          fingerprint: payload.template.fingerprint || '',
        supplier_no: payload.template.supplier_no,
        doc_type: payload.template.doc_type,
        score_min_match: payload.template.score_min_match,
        match_rules: payload.template.match_rules || { keywords: [], required: [], forbidden: [] },
        lines: payload.template.definition?.lines || {},
        fields: payload.template.fields || [],
      } : payload.template_draft);
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
    if (!lines.length || !els.linesModalBody || !els.linesModal) {
      showMessage('Ainda não há linhas detetadas para mostrar.', 'warning');
      setStatus('Ainda não há linhas detetadas. Reprocessa com as regras atuais para testar as linhas.', true);
      return;
    }
    els.linesModalBody.innerHTML = `
      <div class="sz_table_host">
        <div class="sz_table_wrap">
          <table class="sz_table">
            <thead class="sz_table_head">
              <tr><th>Referência</th><th>Descrição</th><th>Qtd</th><th>Un.</th><th>P. Unit.</th><th>Desc.</th><th>IVA</th><th>Total</th></tr>
            </thead>
            <tbody>
              ${lines.map((line) => `
                <tr>
                  <td>${escapeHtml(line.ref ?? '')}</td>
                  <td>${escapeHtml(line.description || '')}</td>
                  <td>${escapeHtml(line.qty ?? '')}</td>
                  <td>${escapeHtml(line.unit ?? '')}</td>
                  <td>${escapeHtml(line.unit_price ?? '')}</td>
                  <td>${escapeHtml(line.discount ?? '')}</td>
                  <td>${escapeHtml(line.tax_rate ?? '')}</td>
                  <td>${escapeHtml(line.net_amount ?? line.gross_amount ?? '')}</td>
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

  function renderValueSourceSelection() {
    if (!els.valueSource) return;
    const raw = String(state.valueEditor.sourceText || '').trim();
    const start = Number(state.valueEditor.selectionStart || 0);
    const end = Number(state.valueEditor.selectionEnd || 0);
    if (!raw) {
      els.valueSource.innerHTML = '';
      if (els.valuePreview) els.valuePreview.textContent = '--';
      return;
    }
    if (start >= 0 && end > start) {
      const before = escapeHtml(raw.slice(0, start));
      const middle = escapeHtml(raw.slice(start, end));
      const after = escapeHtml(raw.slice(end));
      els.valueSource.innerHTML = `${before}<mark>${middle}</mark>${after}`;
      if (els.valuePreview) els.valuePreview.textContent = raw.slice(start, end);
      return;
    }
    els.valueSource.textContent = raw;
    if (els.valuePreview) els.valuePreview.textContent = state.valueEditor.selectedText || raw;
  }

  function selectionOffsetsWithin(container) {
    const selection = window.getSelection();
    if (!selection || selection.rangeCount < 1) return null;
    const range = selection.getRangeAt(0);
    if (!container.contains(range.startContainer) || !container.contains(range.endContainer)) return null;
    const preRange = range.cloneRange();
    preRange.selectNodeContents(container);
    preRange.setEnd(range.startContainer, range.startOffset);
    const start = preRange.toString().length;
    const selected = range.toString();
    if (!selected.trim()) return null;
    return {
      start,
      end: start + selected.length,
      text: selected,
    };
  }

  function openValueModal(fieldKey) {
    if (!fieldKey || !els.valueModal) return;
    const assignment = state.fieldAssignments[fieldKey] || {};
    const sourceText = String(assignment.rawText || fieldCurrentValue(fieldKey) || '').trim();
    if (!sourceText) return;
    state.valueEditor.fieldKey = fieldKey;
    state.valueEditor.sourceText = sourceText;
    state.valueEditor.selectedText = String(assignment.value || fieldCurrentValue(fieldKey) || sourceText).trim();
    const selectedStart = sourceText.indexOf(state.valueEditor.selectedText);
    state.valueEditor.selectionStart = selectedStart >= 0 ? selectedStart : 0;
    state.valueEditor.selectionEnd = selectedStart >= 0 ? selectedStart + state.valueEditor.selectedText.length : 0;
    state.valueEditor.blockId = assignment.blockId || '';
    if (els.valueModalFieldLabel) {
      els.valueModalFieldLabel.textContent = fieldKeyLabel(fieldKey);
    }
    renderValueSourceSelection();
    els.valueModal.classList.add('is-open');
  }

  function closeValueModal() {
    els.valueModal?.classList.remove('is-open');
    state.valueEditor = {
      fieldKey: '',
      sourceText: '',
      selectedText: '',
      blockId: '',
      selectionStart: 0,
      selectionEnd: 0,
    };
  }

  function applyValueModalSelection() {
    const fieldKey = state.valueEditor.fieldKey;
    if (!fieldKey) return;
    const selected = String(state.valueEditor.selectedText || '').trim() || String(state.valueEditor.sourceText || '').trim();
    assignTextToField(fieldKey, selected, {
      sourceText: state.valueEditor.sourceText,
      selectedValue: selected,
      blockId: state.valueEditor.blockId,
    });
    closeValueModal();
  }

  els.ocrList?.addEventListener('click', (event) => {
    const button = event.target.closest('[data-block-id]');
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
  document.addEventListener('pointermove', (event) => {
    if (!state.pointerDrag.active || state.pointerDrag.pointerId !== event.pointerId) return;
    const dx = Math.abs(event.clientX - state.pointerDrag.startX);
    const dy = Math.abs(event.clientY - state.pointerDrag.startY);
    if (!state.pointerDrag.started) {
      if (Math.max(dx, dy) < 6) return;
      beginPointerDrag(state.pointerDrag.blockId, event.clientX, event.clientY);
    }
    updatePointerGhost(event.clientX, event.clientY);
    clearDropHighlights();
    const slot = dropSlotFromPoint(event.clientX, event.clientY);
    if (slot) {
      slot.classList.add('is-dragover');
      state.pointerDrag.overField = dropFieldKey(slot);
    } else {
      state.pointerDrag.overField = '';
    }
  });
  document.addEventListener('pointerup', (event) => {
    if (!state.pointerDrag.active || state.pointerDrag.pointerId !== event.pointerId) return;
    if (state.pointerDrag.started) {
      const slot = dropSlotFromPoint(event.clientX, event.clientY);
      const fieldKey = dropFieldKey(slot) || state.pointerDrag.overField || '';
      if (fieldKey) {
        assignBlockToField(state.pointerDrag.blockId, fieldKey);
      }
    }
    cleanupPointerDrag();
  });
  document.addEventListener('pointercancel', () => {
    if (!state.pointerDrag.active) return;
    cleanupPointerDrag();
  });
  document.addEventListener('click', (event) => {
    const button = event.target.closest?.('[data-clear-field]');
    if (!button) return;
    event.preventDefault();
    event.stopPropagation();
    clearFieldAssignment(String(button.dataset.clearField || '').trim());
  });
  els.dropTargets.forEach((target) => {
    target.addEventListener('dragenter', (event) => {
      event.preventDefault();
      target.classList.add('is-dragover');
    });
    target.addEventListener('dragover', (event) => {
      event.preventDefault();
      if (event.dataTransfer) {
        event.dataTransfer.dropEffect = 'copy';
      }
      target.classList.add('is-dragover');
    });
    target.addEventListener('dragleave', () => {
      target.classList.remove('is-dragover');
    });
    target.addEventListener('drop', (event) => {
      event.preventDefault();
      target.classList.remove('is-dragover');
      const blockId = currentDraggedBlockId(
        event.dataTransfer?.getData('text/plain')
          || event.dataTransfer?.getData('application/x-docai-block')
          || ''
      );
      assignBlockToField(blockId, dropFieldKey(target));
      if (state.dragClearTimer) {
        clearTimeout(state.dragClearTimer);
        state.dragClearTimer = null;
      }
      setTimeout(() => {
        state.draggingBlockId = '';
      }, 0);
    });
    target.addEventListener('click', (event) => {
      if (event.target.closest('input, textarea, select, button')) return;
      const valueEl = event.target.closest('.docai-drop-value');
      if (valueEl && !valueEl.classList.contains('docai-drop-value-empty')) {
        openValueModal(dropFieldKey(target));
        return;
      }
      if (!state.selectedBlockId) return;
      assignBlockToField(state.selectedBlockId, dropFieldKey(target));
    });
  });
  document.addEventListener('drop', (event) => {
    const slot = event.target.closest?.('[data-drop-field]');
    if (!slot) return;
    event.preventDefault();
    const blockId = currentDraggedBlockId(
      event.dataTransfer?.getData('text/plain')
        || event.dataTransfer?.getData('application/x-docai-block')
        || ''
    );
    slot.classList.remove('is-dragover');
    assignBlockToField(blockId, dropFieldKey(slot));
    if (state.dragClearTimer) {
      clearTimeout(state.dragClearTimer);
      state.dragClearTimer = null;
    }
    state.draggingBlockId = '';
  });
  document.addEventListener('dragover', (event) => {
    const slot = event.target.closest?.('[data-drop-field]');
    if (!slot) return;
    event.preventDefault();
  });
  els.previewPrev?.addEventListener('click', () => {
    state.previewPage = Math.max(1, Number(state.previewPage || 1) - 1);
    renderPreview(state.document || {});
  });
  els.previewNext?.addEventListener('click', () => {
    state.previewPage = Math.min(getPreviewPageCount(state.document || {}), Number(state.previewPage || 1) + 1);
    renderPreview(state.document || {});
  });
  els.openOriginalBtn?.addEventListener('click', () => {
    if (!documentId) return;
    window.open(`/api/document_ai/documents/${encodeURIComponent(documentId)}/original`, '_blank', 'noopener');
  });
  els.validateBtn?.addEventListener('click', saveValidation);
  els.saveTemplateBtn?.addEventListener('click', saveTemplateFromReview);
  els.reprocessBtn?.addEventListener('click', () => reprocess('auto'));
  els.reprocessOcrBtn?.addEventListener('click', () => reprocess('ocr'));
  els.reprocessFallbackBtn?.addEventListener('click', () => reprocess('visual_fallback'));
  els.docType?.addEventListener('change', () => {
    if (state.document) {
      state.document.doc_type = els.docType.value || 'unknown';
    }
    if (isPlaceholderTemplateName(els.templateName?.value || '')) {
      setInputValue(els.templateName, '');
    }
    ensureDefaultTemplateKeywords();
    refreshTemplateSelectLabels();
  });

  els.cropToggle?.addEventListener('click', () => {
    setCropMode(!state.adjustments.cropMode);
    if (state.adjustments.cropMode) {
      setStatus('Modo recorte ativo. Arrasta sobre a área útil da imagem e larga para preparar o recorte.');
    } else if (state.adjustments.crop) {
      notifyPendingAdjustments();
    }
  });
  els.cropClear?.addEventListener('click', () => {
    state.adjustments.crop = null;
    state.adjustments.dragRect = null;
    setCropMode(false);
    notifyPendingAdjustments();
  });
  els.lineAreaBtn?.addEventListener('click', () => {
    setLineAreaMode(!state.adjustments.lineAreaMode);
    if (state.adjustments.lineAreaMode) {
      setStatus('Modo area de linhas ativo. Desenha a area da tabela de linhas no documento.');
    } else {
      updateLineAreaStatus();
    }
  });
  els.openLinesDetailBtn?.addEventListener('click', openLinesModal);
  els.rotateLeft?.addEventListener('click', () => {
    state.adjustments.rotate = (Number(state.adjustments.rotate || 0) - 90) % 360;
    updatePreviewTransform();
    notifyPendingAdjustments();
  });
  els.rotateRight?.addEventListener('click', () => {
    state.adjustments.rotate = (Number(state.adjustments.rotate || 0) + 90) % 360;
    updatePreviewTransform();
    notifyPendingAdjustments();
  });

  const previewBody = els.previewBody;
  previewBody?.addEventListener('pointerdown', (event) => {
    const mode = activeDrawMode();
    if (!mode) return;
    const host = getPreviewHost();
    if (!host) return;
    const rect = host.getBoundingClientRect();
    if (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom) {
      return;
    }
    const x = (event.clientX - rect.left) / rect.width;
    const y = (event.clientY - rect.top) / rect.height;
    state.adjustments.dragging = true;
    state.adjustments.draggingKind = mode;
    state.adjustments.dragStart = { x, y };
    state.adjustments.dragRect = { left: x, top: y, width: 0.001, height: 0.001 };
    updateCropOverlay();
    previewBody.setPointerCapture?.(event.pointerId);
  });

  previewBody?.addEventListener('pointermove', (event) => {
    if (!state.adjustments.dragging) return;
    const host = getPreviewHost();
    if (!host || !state.adjustments.dragStart) return;
    const rect = host.getBoundingClientRect();
    const x = Math.max(0, Math.min(1, (event.clientX - rect.left) / rect.width));
    const y = Math.max(0, Math.min(1, (event.clientY - rect.top) / rect.height));
    const start = state.adjustments.dragStart;
    const left = Math.min(start.x, x);
    const top = Math.min(start.y, y);
    const width = Math.max(0.001, Math.abs(x - start.x));
    const height = Math.max(0.001, Math.abs(y - start.y));
    state.adjustments.dragRect = { left, top, width, height };
    updateCropOverlay();
  });

  previewBody?.addEventListener('pointerup', (event) => {
    if (!state.adjustments.dragging) return;
    state.adjustments.dragging = false;
    const targetKind = state.adjustments.draggingKind || activeDrawMode();
    if (state.adjustments.dragRect && state.adjustments.dragRect.width > 0.01 && state.adjustments.dragRect.height > 0.01) {
      if (targetKind === 'line_area') {
        state.adjustments.lineArea = { ...state.adjustments.dragRect };
      } else {
        state.adjustments.crop = { ...state.adjustments.dragRect };
      }
    } else {
      if (targetKind === 'line_area') {
        state.adjustments.lineArea = null;
      } else {
        state.adjustments.crop = null;
      }
    }
    state.adjustments.dragRect = null;
    state.adjustments.dragStart = null;
    state.adjustments.draggingKind = '';
    if (targetKind === 'line_area') {
      setLineAreaMode(false);
      updateLineAreaStatus();
      setStatus('Area das linhas atualizada.');
    } else {
      setCropMode(false);
      notifyPendingAdjustments();
    }
    updateCropOverlay();
    previewBody.releasePointerCapture?.(event.pointerId);
  });
  els.suggestBtn?.addEventListener('click', suggestFromReview);
  els.classifyLlmBtn?.addEventListener('click', classifyWithLlm);
  els.backBtn?.addEventListener('click', () => { window.location.href = '/document_ai/inbox'; });
  els.closeLinesModal?.addEventListener('click', closeLinesModal);
  els.closeLinesModalBottom?.addEventListener('click', closeLinesModal);
  els.linesSummary?.addEventListener('click', openLinesModal);
  els.closeValueModal?.addEventListener('click', closeValueModal);
  els.closeValueModalBottom?.addEventListener('click', closeValueModal);
  els.applyValueModal?.addEventListener('click', applyValueModalSelection);
  els.closeSupplierModal?.addEventListener('click', closeSupplierModal);
  els.closeSupplierModalBottom?.addEventListener('click', closeSupplierModal);
  els.templateKeywordsBtn?.addEventListener('click', openKeywordsModal);
  els.closeKeywordsModal?.addEventListener('click', closeKeywordsModal);
  els.closeKeywordsModalBottom?.addEventListener('click', closeKeywordsModal);
  els.applyKeywordsModal?.addEventListener('click', applyKeywordsModal);
  els.supplierModalBody?.addEventListener('click', (event) => {
    const button = event.target.closest('[data-supplier-index]');
    if (!button) return;
    const candidate = state.supplierCandidates[Number(button.dataset.supplierIndex || -1)];
    if (!candidate) return;
    applySupplierCandidate(candidate);
    closeSupplierModal();
  });
  els.valueSource?.addEventListener('mouseup', () => {
    const selection = selectionOffsetsWithin(els.valueSource);
    if (!selection) return;
    state.valueEditor.selectionStart = selection.start;
    state.valueEditor.selectionEnd = selection.end;
    state.valueEditor.selectedText = selection.text.trim();
    renderValueSourceSelection();
  });
  els.valueSource?.addEventListener('keyup', () => {
    const selection = selectionOffsetsWithin(els.valueSource);
    if (!selection) return;
    state.valueEditor.selectionStart = selection.start;
    state.valueEditor.selectionEnd = selection.end;
    state.valueEditor.selectedText = selection.text.trim();
    renderValueSourceSelection();
  });
  els.templateSelect?.addEventListener('change', async () => {
    const templateId = els.templateSelect.value || '';
    if (!templateId) return;
    try {
      const detail = await fetchJson(`/api/document_ai/templates/${encodeURIComponent(templateId)}`);
      state.draftTemplate = {
        id: detail.id,
        name: detail.name,
        feid: detail.feid || state.document?.feid || null,
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
      setTemplateKeywords(detail.match_rules?.keywords || []);
      applyLineConfigToForm(detail.definition?.lines || {});
    } catch (error) {
      console.error(error);
    }
  });

  loadData();
});
