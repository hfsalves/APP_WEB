document.addEventListener('DOMContentLoaded', () => {
  const pageRoot = document.querySelector('.docai-extract-page');
  const els = {
    backBtn: document.getElementById('docAiExtractBackBtn'),
    resetBtn: document.getElementById('docAiExtractResetBtn'),
    input: document.getElementById('docAiExtractInput'),
    chooseBtn: document.getElementById('docAiExtractChooseBtn'),
    runBtn: document.getElementById('docAiExtractRunBtn'),
    deleteBtn: document.getElementById('docAiExtractDeleteBtn'),
    openPdfBtn: document.getElementById('docAiExtractOpenPdfBtn'),
    dropzone: document.getElementById('docAiExtractDropzone'),
    preview: document.getElementById('docAiExtractPreview'),
    previewFrame: document.getElementById('docAiExtractPreviewFrame'),
    fileMeta: document.getElementById('docAiExtractFileMeta'),
    resultMeta: document.getElementById('docAiExtractResultMeta'),
    empty: document.getElementById('docAiExtractEmpty'),
    loading: document.getElementById('docAiExtractLoading'),
    results: document.getElementById('docAiExtractResults'),
    status: document.getElementById('docAiExtractStatus'),
    saveRetryBtn: document.getElementById('docAiExtractSaveRetryBtn'),
    customerName: document.getElementById('docAiExtractCustomerName'),
    customerTax: document.getElementById('docAiExtractCustomerTax'),
    customerCard: document.getElementById('docAiExtractCustomerCard'),
    customerLabel: document.getElementById('docAiExtractCustomerLabel'),
    customerHint: document.getElementById('docAiExtractCustomerHint'),
    supplierName: document.getElementById('docAiExtractSupplierName'),
    partyLabel: document.getElementById('docAiExtractPartyLabel'),
    supplierTax: document.getElementById('docAiExtractSupplierTax'),
    supplierNo: document.getElementById('docAiExtractSupplierNo'),
    supplierCard: document.getElementById('docAiExtractSupplierCard'),
    supplierHint: document.getElementById('docAiExtractSupplierHint'),
    documentSummary: document.getElementById('docAiExtractDocumentSummary'),
    correspondenceReference: document.getElementById('docAiExtractCorrespondenceReference'),
    correspondenceSource: document.getElementById('docAiExtractCorrespondenceSource'),
    legalBadge: document.getElementById('docAiExtractLegalBadge'),
    gedDestination: document.getElementById('docAiExtractGedDestination'),
    gedStatus: document.getElementById('docAiExtractGedStatus'),
    gedFileName: document.getElementById('docAiExtractGedFileName'),
    gedFileRow: document.getElementById('docAiExtractGedFileRow'),
    gedPath: document.getElementById('docAiExtractGedPath'),
    gedFolderControl: document.getElementById('docAiExtractGedFolderControl'),
    gedFolderSelect: document.getElementById('docAiExtractGedFolderSelect'),
    gedFolderHint: document.getElementById('docAiExtractGedFolderHint'),
    projectCard: document.getElementById('docAiExtractProjectCard'),
    projectName: document.getElementById('docAiExtractProjectName'),
    projectMeta: document.getElementById('docAiExtractProjectMeta'),
    projectHint: document.getElementById('docAiExtractProjectHint'),
    projectClear: document.getElementById('docAiExtractProjectClear'),
    originSection: document.getElementById('docAiExtractOriginSection'),
    linesSection: document.getElementById('docAiExtractLinesSection'),
    totalsCard: document.getElementById('docAiExtractTotalsCard'),
    totalsModal: document.getElementById('docAiTotalsModal'),
    totalsCloseTop: document.getElementById('docAiTotalsCloseTop'),
    totalsClose: document.getElementById('docAiTotalsClose'),
    originDetailModal: document.getElementById('docAiOriginDetailModal'),
    originDetailTitle: document.getElementById('docAiOriginDetailTitle'),
    originDetailLoading: document.getElementById('docAiOriginDetailLoading'),
    originDetailTable: document.getElementById('docAiOriginDetailTable'),
    originDetailHead: document.getElementById('docAiOriginDetailHead'),
    originDetailBody: document.getElementById('docAiOriginDetailBody'),
    originDetailEmpty: document.getElementById('docAiOriginDetailEmpty'),
    originDetailCloseTop: document.getElementById('docAiOriginDetailCloseTop'),
    originDetailClose: document.getElementById('docAiOriginDetailClose'),
    originMeta: document.getElementById('docAiExtractOriginMeta'),
    originSource: document.getElementById('docAiExtractOriginSource'),
    originLoading: document.getElementById('docAiExtractOriginLoading'),
    originFlow: document.getElementById('docAiExtractOriginFlow'),
    originTabs: document.getElementById('docAiExtractOriginTabs'),
    lineCount: document.getElementById('docAiExtractLineCount'),
    splitLineBtn: document.getElementById('docAiExtractSplitLineBtn'),
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
    supplierModalTitle: document.getElementById('docAiSupplierMatchTitle'),
    supplierModalContext: document.getElementById('docAiSupplierMatchContext'),
    supplierModalSearch: document.getElementById('docAiSupplierMatchSearch'),
    supplierModalSearchBtn: document.getElementById('docAiSupplierMatchSearchBtn'),
    supplierManualBtn: document.getElementById('docAiSupplierManualBtn'),
    supplierModalList: document.getElementById('docAiSupplierMatchList'),
    supplierModalCloseTop: document.getElementById('docAiSupplierMatchCloseTop'),
    supplierModalClose: document.getElementById('docAiSupplierMatchClose'),
    projectModal: document.getElementById('docAiProjectModal'),
    projectContext: document.getElementById('docAiProjectContext'),
    projectSearch: document.getElementById('docAiProjectSearch'),
    projectSearchBtn: document.getElementById('docAiProjectSearchBtn'),
    projectList: document.getElementById('docAiProjectList'),
    projectCloseTop: document.getElementById('docAiProjectCloseTop'),
    projectClose: document.getElementById('docAiProjectClose'),
    articleModal: document.getElementById('docAiArticleModal'),
    articleContext: document.getElementById('docAiArticleContext'),
    articleSearch: document.getElementById('docAiArticleSearch'),
    articleSearchBtn: document.getElementById('docAiArticleSearchBtn'),
    articleList: document.getElementById('docAiArticleList'),
    articleCloseTop: document.getElementById('docAiArticleCloseTop'),
    articleClose: document.getElementById('docAiArticleClose'),
    vehicleModal: document.getElementById('docAiVehicleModal'),
    vehicleContext: document.getElementById('docAiVehicleContext'),
    vehicleSearch: document.getElementById('docAiVehicleSearch'),
    vehicleSearchBtn: document.getElementById('docAiVehicleSearchBtn'),
    vehicleList: document.getElementById('docAiVehicleList'),
    vehicleRemove: document.getElementById('docAiVehicleRemove'),
    vehicleCloseTop: document.getElementById('docAiVehicleCloseTop'),
    vehicleClose: document.getElementById('docAiVehicleClose'),
    bcModal: document.getElementById('docAiBcModal'),
    bcList: document.getElementById('docAiBcList'),
    bcSave: document.getElementById('docAiBcSave'),
    bcCloseTop: document.getElementById('docAiBcCloseTop'),
    bcClose: document.getElementById('docAiBcClose'),
    persistenceNote: document.getElementById('docAiExtractPersistenceNote'),
    entityModal: document.getElementById('docAiEntityModal'),
    entitySearch: document.getElementById('docAiEntitySearch'),
    entitySearchBtn: document.getElementById('docAiEntitySearchBtn'),
    entityList: document.getElementById('docAiEntityList'),
    entityCloseTop: document.getElementById('docAiEntityCloseTop'),
    entityClose: document.getElementById('docAiEntityClose'),
    accessModal: document.getElementById('docAiIntegrationAccessModal'),
    accessCloseTop: document.getElementById('docAiIntegrationAccessCloseTop'),
    accessClose: document.getElementById('docAiIntegrationAccessClose'),
    accessSearch: document.getElementById('docAiIntegrationAccessSearch'),
    accessSearchBtn: document.getElementById('docAiIntegrationAccessSearchBtn'),
    accessUsers: document.getElementById('docAiIntegrationAccessUsers'),
    accessPermissions: document.getElementById('docAiIntegrationAccessPermissions'),
    accessHelp: document.getElementById('docAiIntegrationAccessHelp'),
    accessSelected: document.getElementById('docAiIntegrationAccessSelected'),
    accessSave: document.getElementById('docAiIntegrationAccessSave'),
    submitPhcBtn: document.getElementById('docAiExtractSubmitPhcBtn'),
    controlOkBtn: document.getElementById('docAiExtractControlOkBtn'),
    workflowValidateBtn: document.getElementById('docAiExtractWorkflowValidateBtn'),
    duplicateModal: document.getElementById('docAiDuplicateModal'),
    duplicateList: document.getElementById('docAiDuplicateList'),
    duplicateCloseTop: document.getElementById('docAiDuplicateCloseTop'),
    duplicateCancel: document.getElementById('docAiDuplicateCancel'),
    duplicateConfirm: document.getElementById('docAiDuplicateConfirm'),
    conflictModal: document.getElementById('docAiConflictModal'),
    conflictReload: document.getElementById('docAiConflictReload'),
    conflictKeep: document.getElementById('docAiConflictKeep'),
    viewTabs: document.getElementById('docAiExtractViewTabs'),
    modeLabel: document.getElementById('docAiExtractModeLabel'),
    modeValue: document.getElementById('docAiExtractModeValue'),
    modeMeta: document.getElementById('docAiExtractModeMeta'),
  };

  const allowedViews = new Set([...(els.viewTabs?.querySelectorAll('[data-view]') || [])].map((button) => button.dataset.view));
  const initialParams = new URLSearchParams(window.location.search);
  const initialView = initialParams.get('view');
  const readOnly = pageRoot?.dataset.readOnly === '1';
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
    originSearchToken: 0,
    originPayload: null,
    originCandidates: [],
    activeOriginStage: '',
    consultedOriginStamp: '',
    selectedOrigins: [],
    selectedProject: null,
    projectCandidates: [],
    projectTargetLineIndex: null,
    articleCandidates: [],
    articleTargetLineIndex: null,
    vehicleCandidates: [],
    vehicleTargetLineIndex: null,
    bcTargetLineIndex: null,
    bcSelectedStamps: new Set(),
    expandedBcLines: new Set(),
    projectSuggestionDismissed: false,
    deliveryNoteGroups: [],
    selectedDeliveryNoteGroups: new Set(),
    virtualDeliveryNotesActive: false,
    originLineMatches: [],
    originLineReferenceLabel: '',
    originLineMatchByLine: new WeakMap(),
    selectedSplitLines: new Set(),
    entityCandidates: [],
    supplierSearchToken: 0,
    supplierSearchTimer: null,
    entitySearchTimer: null,
    correspondenceReference: null,
    correspondenceYear: null,
    correspondenceLookupToken: 0,
    accessUsers: [],
    accessSelectedUser: null,
    accessSearchTimer: null,
    accessSearchToken: 0,
    submittingPhc: false,
    submittingControl: false,
    controlOk: false,
    integratedPhc: false,
    integrationResult: null,
    gedFolderManuallySelected: false,
    workflowSubmitting: false,
    workflow: {},
    duplicateMatches: [],
    duplicateModalShownFor: '',
    deletingDocument: false,
    draftVersion: '',
    draftTimer: null,
    draftRequest: null,
    draftRevision: 0,
    draftSavedRevision: 0,
    draftLastFingerprint: '',
    draftError: false,
    draftConflict: false,
    pendingManualOverrides: null,
    readOnly,
    view: allowedViews.has(initialView) ? initialView : ([...allowedViews][0] || ''),
  };

  const typeLabels = {
    invoice: 'Fatura',
    credit_note: 'Nota de crédito',
    contract: 'Contrato',
    subcontract: 'Contrato Sout-Traitant',
    debit_note: 'Nota de débito',
    purchase_order: 'Nota de encomenda',
    delivery_note: 'Guia de remessa',
    proforma_invoice: 'Fatura pró-forma',
    provisional_invoice: 'Fatura provisória',
    receipt: 'Recibo',
    bank_statement: 'Extrato bancário',
    mail: 'Correio',
    unknown: 'Tipo desconhecido',
    other: 'Outro documento',
  };

  const invoiceTypeLabels = {
    concrete: 'Betão',
    material: 'Material',
    services: 'Serviços',
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
    const visibleMessage = /^(Leitura guardada carregada do inbox\.|Leitura concluída\.|Filtro de obra .* aplicado às origens\.)$/i.test(String(message || '').trim())
      ? ''
      : String(message || '');
    els.status.textContent = visibleMessage;
    els.status.hidden = !visibleMessage;
    els.status.style.color = isError ? 'var(--sz-color-danger)' : '';
  }

  function showMessage(message, type = 'info') {
    if (typeof window.showToast === 'function') {
      window.showToast(message, type);
    }
  }

  function extractUrl(documentId = state.currentDocumentId) {
    const params = new URLSearchParams();
    if (documentId) params.set('document_id', documentId);
    if (state.view !== 'home') params.set('view', state.view);
    if (state.readOnly) params.set('archive', '1');
    const query = params.toString();
    return `/document_ai/extract${query ? `?${query}` : ''}`;
  }

  function inboxUrl() {
    const params = new URLSearchParams();
    if (state.view !== 'home') params.set('view', state.view);
    if (state.readOnly) params.set('archived', '1');
    const query = params.toString();
    return `/document_ai/inbox${query ? `?${query}` : ''}`;
  }

  function renderViewTabs() {
    const tabs = [...(els.viewTabs?.querySelectorAll('[data-view]') || [])];
    tabs.forEach((button) => {
      const active = button.dataset.view === state.view;
      button.classList.toggle('is-active', active);
      if (tabs.length > 1) {
        button.setAttribute('aria-selected', active ? 'true' : 'false');
        button.tabIndex = active ? 0 : -1;
      }
    });
    els.viewTabs?.classList.toggle('is-single-view', tabs.length === 1);
    updateSubmitPhcButton();
  }

  function workflowViewLabel(view = state.view) {
    return ({
      home: 'Receção',
      management: 'Controlo',
      accounting: 'Contabilidade',
    })[view] || 'Receção';
  }

  function renderModeCard() {
    if (!els.modeLabel || !els.modeValue || !els.modeMeta) return;
    const documentData = state.documentData || {};
    if (state.view === 'home') {
      const docType = typeLabels[documentData.document_type] || documentData.document_type || typeLabels.unknown;
      const confidence = Math.round(Math.max(0, Math.min(1, Number(documentData.confidence || 0))) * 100);
      els.modeLabel.textContent = 'Classificação';
      els.modeValue.textContent = documentData.document_type ? docType : '--';
      els.modeMeta.textContent = documentData.document_type ? `${confidence}% de confiança` : 'A aguardar leitura';
      return;
    }
    const totals = documentData.totals || {};
    const currency = documentData.currency || '';
    els.modeLabel.textContent = 'Totais';
    els.modeValue.textContent = documentData.document_type ? formatMoney(totals.gross_total, currency) : '--';
    els.modeMeta.textContent = documentData.document_type
      ? `Total s/IVA ${formatMoney(totals.net_total, currency)} · IVA ${formatMoney(totals.tax_total, currency)}`
      : 'A aguardar leitura';
  }

  function selectView(view, { updateHistory = true } = {}) {
    if (!allowedViews.has(view) || view === state.view) return;
    state.view = view;
    renderViewTabs();
    renderModeCard();
    if (updateHistory) window.history.pushState({ documentAiView: view }, '', extractUrl());
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
    const formatted = new Intl.NumberFormat('pt-PT', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
      useGrouping: true,
    }).format(number);
    return `${formatted}${/^[A-Z]{3}$/.test(normalizedCurrency) ? ` ${normalizedCurrency}` : ''}`;
  }

  function formatOptionalMoney(value, currency) {
    return value === null || value === undefined || value === '' ? '-' : formatMoney(value, currency);
  }

  function renderClassificationCard() {
    renderGedDestination();
  }

  function formatEditableAmount(value) {
    return new Intl.NumberFormat('pt-PT', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
      useGrouping: true,
    }).format(Number(value || 0));
  }

  function parseEditableNumber(value) {
    const normalized = String(value ?? '').trim().replace(/\s/g, '').replace(',', '.');
    const parsed = Number(normalized);
    return Number.isFinite(parsed) ? parsed : 0;
  }

  function normalizeLineGroupCode(value) {
    return String(value || '').trim().toUpperCase();
  }

  function validateLineGroupChange(lines, lineIndex, nextCode) {
    const items = Array.isArray(lines) ? lines : [];
    const currentCode = normalizeLineGroupCode(items[lineIndex]?.article_group_code);
    const normalized = normalizeLineGroupCode(nextCode);
    if (normalized && !/^[PA][1-9]\d*$/.test(normalized)) {
      return { ok: false, message: 'Usa um grupo como P1 ou A1.' };
    }
    const currentPrincipal = currentCode.match(/^P([1-9]\d*)$/)?.[1] || '';
    const nextPrincipal = normalized.match(/^P([1-9]\d*)$/)?.[1] || '';
    if (currentPrincipal && currentPrincipal !== nextPrincipal) {
      const hasAssociates = items.some((line, index) => (
        index !== lineIndex && normalizeLineGroupCode(line?.article_group_code) === `A${currentPrincipal}`
      ));
      if (hasAssociates) {
        return { ok: false, message: `O grupo ${currentPrincipal} ainda tem linhas associadas.` };
      }
    }
    if (nextPrincipal) {
      const duplicatePrincipal = items.some((line, index) => (
        index !== lineIndex && normalizeLineGroupCode(line?.article_group_code) === `P${nextPrincipal}`
      ));
      if (duplicatePrincipal) {
        return { ok: false, message: `O grupo ${nextPrincipal} já tem linha principal.` };
      }
    }
    const nextAssociate = normalized.match(/^A([1-9]\d*)$/)?.[1] || '';
    if (nextAssociate) {
      const hasPrincipal = items.some((line, index) => (
        index !== lineIndex && normalizeLineGroupCode(line?.article_group_code) === `P${nextAssociate}`
      ));
      if (!hasPrincipal) {
        return { ok: false, message: `O grupo ${nextAssociate} não tem linha principal.` };
      }
    }
    return { ok: true, code: normalized };
  }

  function formatBcLabel(origin) {
    const number = String(origin?.origin_number || origin?.number || '').trim();
    const year = String(origin?.origin_year || origin?.year || '').trim();
    if (!number) return 'NdE';
    return `NdE N.º ${number}${year ? ` / ${year}` : ''}`;
  }

  function associatedBcOrigins() {
    return state.selectedOrigins.map((selected) => (
      state.originCandidates.find((candidate) => candidate.stamp === selected.stamp) || selected
    )).filter((origin) => origin?.document_type === 'purchase_order' || Number(origin?.ndos || 0) === 102);
  }

  function originFamily(origin) {
    const type = String(origin?.document_type || '').trim().toLowerCase();
    const key = String(origin?.key || origin?.stage_key || '').trim().toLowerCase();
    const ndos = Number(origin?.ndos || 0);
    if (type === 'purchase_order' || key === 'purchase_order' || ndos === 102) return 'bc';
    if (type === 'delivery_note' || key === 'delivery_note' || ndos === 130) return 'delivery_note';
    if (type === 'work_situation' || key === 'subcontract_measurement' || ndos === 129) return 'work_situation';
    if (type === 'subcontract' || key === 'subcontract_contract' || ndos === 128) return 'subcontract';
    if (type === 'contract' || key === 'contract' || ndos === 119) return 'contract';
    return '';
  }

  function selectedPrimaryOriginFamily() {
    return state.selectedOrigins.map(originFamily).find((family) => ['bc', 'contract', 'subcontract'].includes(family)) || '';
  }

  function originDisplayStage(stageKey) {
    if (['purchase_order', 'contract', 'subcontract_contract'].includes(stageKey)) return 'bc_contracts';
    if (stageKey === 'delivery_note' || stageKey === 'virtual_delivery_note') return 'delivery_note';
    if (stageKey === 'subcontract_measurement') return 'work_situation';
    return stageKey;
  }

  function formatDate(value) {
    const raw = String(value || '').trim();
    if (!raw) return '--';
    const match = raw.match(/^(\d{4})-(\d{2})-(\d{2})$/);
    return match ? `${match[3]}/${match[2]}/${match[1]}` : raw;
  }

  function gedSafePart(value, fallback) {
    const cleaned = String(value || '')
      .normalize('NFKC')
      .replace(/[<>:"/\\|?*]+/g, '_')
      .replace(/\s+/g, ' ')
      .replace(/^[\s._-]+|[\s._-]+$/g, '')
      .toUpperCase();
    return cleaned || fallback;
  }

  function gedPartyName(value) {
    return gedSafePart(value, 'NOME-POR-IDENTIFICAR')
      .replace(/\b(SARL|EURL|LDA|LIMITADA|SA|SAS|SPA|SL|SRL)\b[\s.,]*$/i, '')
      .trim() || 'NOME-POR-IDENTIFICAR';
  }

  function phcPartyNumber(value, establishment = 0) {
    const number = Number(value || 0);
    if (!number) return '';
    const estab = Number(establishment || 0);
    return estab > 0 ? `${number}_${estab}` : String(number);
  }

  function gedCompanyFolder(customer = {}) {
    if (customer.ged_folder) return gedSafePart(customer.ged_folder, 'PASTA-POR-CONFIGURAR');
    return 'PASTA-EMPRESA-POR-CONFIGURAR';
  }

  const intersolGedFolders = [
    { value: 'HSOLS_INTERSOL_AL', label: 'INTERSOL Alsace' },
    { value: 'HSOLS_INTERSOL_LOR', label: 'INTERSOL Lorraine' },
    { value: 'HSOLS_INTERSOL_CH', label: 'INTERSOL Champagne' },
  ];

  function normalizedSearchText(value) {
    return String(value || '')
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '')
      .toUpperCase();
  }

  function suggestIntersolGedFolder(documentData = {}) {
    const customer = documentData.customer || {};
    const supplier = documentData.supplier || {};
    const text = normalizedSearchText([
      state.file?.name,
      customer.name,
      customer.llm_name,
      customer.address,
      customer.postal_code,
      customer.city,
      supplier.name,
      supplier.address,
      supplier.postal_code,
      supplier.city,
      state.selectedProject?.ccusto,
      state.selectedProject?.description,
      documentData.origin_project?.ccusto,
      documentData.origin_project?.description,
      documentData.document_number,
      documentData.reference,
      documentData.mail_title,
      ...(documentData.lines || []).map((line) => `${line.description || ''} ${line.project || ''}`),
      ...(documentData.notes || []),
    ].filter(Boolean).join(' '));
    if (/\b(CHAMPAGNE|REIMS|TROYES|EPERNAY|CHALONS EN CHAMPAGNE|CHARLEVILLE MEZIERES|CHAUMONT)\b|\b(08|10|51|52)\d{3}\b/.test(text)) {
      return { value: 'HSOLS_INTERSOL_CH', reason: 'Sugerida pela morada/agência Champagne' };
    }
    if (/\b(LORRAINE|METZ|NANCY|THIONVILLE|SARREGUEMINES|EPINAL|VANDOEUVRE)\b|\b(54|55|57|88)\d{3}\b/.test(text)) {
      return { value: 'HSOLS_INTERSOL_LOR', reason: 'Sugerida pela morada/agência Lorraine' };
    }
    if (/\b(ALSACE|STRASBOURG|COLMAR|MULHOUSE|MOLSHEIM|HAGUENAU|SELESTAT|GEISPOLSHEIM)\b|\b(67|68)\d{3}\b/.test(text)) {
      return { value: 'HSOLS_INTERSOL_AL', reason: 'Sugerida pela morada/agência Alsace' };
    }
    return null;
  }

  function configureGedFolderControl() {
    const customer = state.documentData?.customer || {};
    const isIntersol = customer.phc_database === 'INTERSOL'
      || String(customer.ged_folder || '').startsWith('HSOLS_INTERSOL_');
    els.gedFolderControl.hidden = !isIntersol;
    if (!isIntersol) return;

    const suggestion = suggestIntersolGedFolder(state.documentData);
    if (!state.gedFolderManuallySelected && suggestion) {
      customer.ged_folder = suggestion.value;
      customer.ged_folder_suggested_by = suggestion.reason;
    }
    const selectedFolder = customer.ged_folder || '';
    const placeholder = document.createElement('option');
    placeholder.value = '';
    placeholder.textContent = 'Escolher';
    els.gedFolderSelect.replaceChildren(placeholder, ...intersolGedFolders.map((option) => {
      const element = document.createElement('option');
      element.value = option.value;
      element.textContent = option.label.replace('INTERSOL ', '');
      element.selected = option.value === selectedFolder;
      return element;
    }));
    placeholder.selected = !selectedFolder;
    els.gedFolderHint.textContent = state.gedFolderManuallySelected
      ? 'Destino escolhido manualmente'
      : (customer.ged_folder_suggested_by || (selectedFolder ? 'Agência definida pela entidade' : 'Falta a agência.'));
  }

  function gedPeriodFolders() {
    const now = new Date();
    const months = ['JANV', 'FEV', 'MARS', 'AVR', 'MAI', 'JUIN', 'JUIL', 'AOUT', 'SEPT', 'OCT', 'NOV', 'DEC'];
    const month = now.getMonth() + 1;
    return { year: String(now.getFullYear()), month: `${month} ${months[month - 1]} ${String(now.getFullYear()).slice(-2)}` };
  }

  function renderGedDestination() {
    const documentData = state.documentData;
    if (!documentData) return;
    const customer = documentData.customer || {};
    configureGedFolderControl();
    const party = documentData.supplier || {};
    const isMail = documentData.document_type === 'mail';
    const isCorrespondence = ['mail', 'bank_statement'].includes(documentData.document_type);
    const isCustomerParty = isCorrespondence && documentData.external_party_role === 'customer';
    const isUnregisteredMailParty = isCorrespondence && !['customer', 'supplier'].includes(documentData.external_party_role);
    const partyNumber = Number(isCustomerParty ? party.customer_no : party.supplier_no || party.no || 0);
    const partyNumberPart = phcPartyNumber(partyNumber, party.estab) || 'SEM-NUMERO';
    const partyNamePart = gedPartyName(party.short_name || party.name2 || party.name || party.llm_name);
    const documentNumber = gedSafePart(documentData.document_number, 'SEM-DOCUMENTO');
    const mailTitlePart = isMail ? gedSafePart(documentData.mail_title, '') : '';
    const project = gedSafePart(state.selectedProject?.ccusto || documentData.origin_project?.ccusto, '');
    const documentDate = gedSafePart(documentData.document_date, gedSafePart(new Date().toISOString().slice(0, 10), 'SEM-DATA'));
    let prefix = 'DOC';
    let category = 'DOCUMENTS_FOURNISSEURS';
    let destinations = [{ label: 'Documentos de fornecedores', category }];
    let trailingPart = documentNumber;

    if (isCorrespondence) {
      prefix = documentData.document_type === 'bank_statement' ? 'RB' : 'L';
      category = 'COURRIER_INTERNE_EXTERIEUR';
      destinations = [{ label: 'Correio recebido', category, subfolders: ['Courriers Reçus'] }];
      trailingPart = documentDate;
    } else if (['invoice', 'credit_note', 'debit_note', 'proforma_invoice', 'provisional_invoice'].includes(documentData.document_type)) {
      prefix = 'FAC';
      category = 'FACTURATION_FOURNISSEURS';
      destinations = [
        { label: 'Correio recebido', category: 'COURRIER_INTERNE_EXTERIEUR', subfolders: ['Courriers Reçus'] },
        { label: 'Faturas de fornecedor', category },
      ];
    } else if (documentData.document_type === 'delivery_note') {
      prefix = 'BL';
      category = 'BON_LIVRAISON_FOURNISSEUR';
      destinations = [{ label: 'Guias de fornecedor', category }];
    } else if (documentData.document_type === 'purchase_order') {
      prefix = 'BC';
      category = 'BON_COMMANDE_FOURNISSEUR';
      destinations = [{ label: 'Encomendas de fornecedor', category }];
    }

    const correspondencePart = state.correspondenceReference
      ? String(state.correspondenceReference).padStart(3, '0')
      : 'CORRESP-PENDENTE';
    const fileParts = [prefix, correspondencePart];
    if (!isUnregisteredMailParty) fileParts.push(partyNumberPart);
    fileParts.push(partyNamePart);
    if (mailTitlePart) fileParts.push(mailTitlePart);
    fileParts.push(trailingPart);
    if (project) fileParts.push(project);
    const fileName = `${fileParts.join('-')}.pdf`;
    const companyFolder = gedCompanyFolder(customer);
    const period = gedPeriodFolders();
    const paths = destinations.map((destination) => ({
      ...destination,
      path: `\\\\10.0.1.11\\ged\\${[
        companyFolder,
        destination.category,
        ...(destination.subfolders || []),
        period.year,
        period.month,
        fileName,
      ].join('\\')}`,
    }));
    const incomplete = !state.correspondenceReference
      || (!isUnregisteredMailParty && !partyNumber)
      || companyFolder === 'PASTA-EMPRESA-POR-CONFIGURAR';

    els.gedFileName.textContent = fileName;
    els.gedFileName.title = fileName;
    const originalName = String(state.file?.name || '').trim().toLocaleLowerCase('pt');
    const usefulGedName = Boolean(fileName && fileName.toLocaleLowerCase('pt') !== originalName);
    if (els.gedFileRow) els.gedFileRow.hidden = !usefulGedName;
    els.gedPath.replaceChildren(...paths.map((destination) => {
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'docai-classification-destination';
      button.textContent = destination.label;
      button.title = destination.path;
      button.dataset.copyValue = destination.path;
      return button;
    }));
    const missingAgency = (customer.phc_database === 'INTERSOL'
      || String(customer.ged_folder || '').startsWith('HSOLS_INTERSOL_'))
      && !String(customer.ged_folder || '').trim();
    els.gedDestination.classList.toggle('is-incomplete', incomplete || missingAgency);
    els.gedStatus.textContent = incomplete
      ? 'Destino provisório: falta obter a correspondência, identificar o número do remetente/fornecedor ou configurar a pasta GED da entidade.'
      : (missingAgency
        ? 'Falta a agência.'
        : `${paths.length} ${paths.length === 1 ? 'destino previsto' : 'destinos previstos'}. Seleciona para copiar o caminho.`);
    if (state.integrationResult?.ged_path) {
      els.gedFileName.textContent = state.integrationResult.file_name || fileName;
      const integratedPath = els.gedPath.querySelector('[data-copy-value]');
      if (integratedPath) {
        integratedPath.dataset.copyValue = state.integrationResult.ged_path;
        integratedPath.title = state.integrationResult.ged_path;
      }
      els.gedDestination.classList.remove('is-incomplete');
      els.gedStatus.textContent = `Guardado no PHC ${state.integrationResult.phc_database || ''} e ligado à correspondência nº ${state.integrationResult.reference}.`;
    }
    updateSubmitPhcButton();
  }

  function updateSubmitPhcButton() {
    const documentData = state.documentData || {};
    const party = documentData.supplier || {};
    const isCorrespondence = ['mail', 'bank_statement'].includes(documentData.document_type);
    const isProvisionalInvoice = ['invoice', 'provisional_invoice', 'credit_note'].includes(documentData.document_type);
    const canSubmitCorrespondence = isCorrespondence && els.submitPhcBtn?.dataset.canCorrespondence === '1';
    const canSubmitProvisionalInvoice = isProvisionalInvoice && els.submitPhcBtn?.dataset.canProvisionalInvoice === '1';
    if (els.workflowValidateBtn) {
      const viewLabel = workflowViewLabel();
      const currentAssignment = (state.workflow.assignments || []).find((assignment) => (
        assignment.view === state.view && assignment.active
      ));
      const isAccountingPending = state.view === 'accounting' && currentAssignment?.state === 'pending';
      els.workflowValidateBtn.disabled = !state.currentDocumentId
        || !state.documentData
        || state.workflowSubmitting
        || state.submittingPhc
        || Boolean(state.draftTimer)
        || Boolean(state.draftRequest)
        || state.draftError
        || isAccountingPending;
      els.workflowValidateBtn.dataset.view = state.view;
      els.workflowValidateBtn.title = isAccountingPending
        ? 'Pendente: aguarda validação do Controlo de Gestão.'
        : `Validar ${viewLabel}`;
      els.workflowValidateBtn.setAttribute('aria-label', `Validar ${viewLabel}`);
      els.workflowValidateBtn.innerHTML = state.workflowSubmitting
        ? `<i class="fa-solid fa-circle-notch fa-spin"></i><span>A validar ${viewLabel}...</span>`
        : `<i class="fa-solid fa-check"></i><span>Validar ${viewLabel}</span>`;
    }
    if (!els.submitPhcBtn) return;
    const allowed = canSubmitCorrespondence || canSubmitProvisionalInvoice;
    els.submitPhcBtn.hidden = !allowed;
    if (els.controlOkBtn) els.controlOkBtn.hidden = !isProvisionalInvoice || els.controlOkBtn.dataset.canProvisionalInvoice !== '1';
    if (!allowed) return;
    const ready = Boolean(
      state.file
      && documentData.customer?.feid
      && String(party.name || party.llm_name || '').trim()
      && (isCorrespondence || Number(party.supplier_no || party.no || 0) > 0)
      && state.correspondenceReference
      && (isCorrespondence || (String(documentData.document_number || '').trim() && Array.isArray(documentData.lines) && documentData.lines.length))
    );
    if (els.controlOkBtn && isProvisionalInvoice) {
      els.controlOkBtn.disabled = !ready || state.submittingControl || state.controlOk || state.integratedPhc;
      els.controlOkBtn.title = ready
        ? (state.controlOk ? 'Controlo OK concluído.' : 'Confirmar o controlo do documento.')
        : 'Identifica a sociedade, o fornecedor, o número e as linhas do documento.';
      els.controlOkBtn.innerHTML = state.submittingControl
        ? '<i class="fa-solid fa-circle-notch fa-spin"></i><span>A confirmar...</span>'
        : state.controlOk
          ? '<i class="fa-solid fa-circle-check"></i><span>Controlo OK</span>'
          : '<i class="fa-solid fa-clipboard-check"></i><span>Controlo OK</span>';
    }
    els.submitPhcBtn.disabled = !ready || (isProvisionalInvoice && !state.controlOk) || state.submittingPhc || state.integratedPhc;
    els.submitPhcBtn.title = isProvisionalInvoice && !state.controlOk
      ? 'Efetua primeiro o Controlo OK.'
      : '';
    if (state.integratedPhc) {
      els.submitPhcBtn.innerHTML = '<i class="fa-solid fa-circle-check"></i><span>Contabilidade</span>';
    } else if (state.submittingPhc) {
      els.submitPhcBtn.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin"></i><span>A validar...</span>';
    } else {
      els.submitPhcBtn.innerHTML = isProvisionalInvoice
        ? '<i class="fa-solid fa-check"></i><span>Validar</span>'
        : '<i class="fa-solid fa-paper-plane"></i><span>Submeter no PHC</span>';
    }
  }

  function renderDocumentCard() {
    const documentData = state.documentData || {};
    const docType = typeLabels[documentData.document_type] || documentData.document_type || typeLabels.unknown;
    const displayedNumber = documentData.document_type === 'mail'
      ? documentData.mail_title
      : documentData.document_number;
    const invoiceType = ['invoice', 'provisional_invoice'].includes(documentData.document_type)
      ? invoiceTypeLabels[String(documentData.invoice_type || '').toLowerCase()]
      : '';
    els.documentSummary.textContent = [
      docType,
      invoiceType,
      displayedNumber,
      documentData.document_date ? formatDate(documentData.document_date) : '',
    ].filter(Boolean).join(' · ');
    if (state.correspondenceReference) {
      els.correspondenceReference.textContent = `Correspondência n.º ${state.correspondenceReference} · ${state.correspondenceYear}`;
    } else {
      els.correspondenceReference.textContent = 'Correspondência por criar';
    }
  }

  async function loadCorrespondenceReference() {
    const integration = state.integrationResult || {};
    state.correspondenceReference = Number(integration.reference || 0) || null;
    state.correspondenceYear = Number(integration.year || new Date().getFullYear());
    if (state.documentData) {
      state.documentData.correspondence_reference = state.correspondenceReference;
      state.documentData.correspondence_year = state.correspondenceYear;
    }
    els.correspondenceSource.hidden = true;
    renderDocumentCard();
    renderGedDestination();
    updateSubmitPhcButton();
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
    els.openPdfBtn.disabled = false;
    if (els.deleteBtn) els.deleteBtn.disabled = false;
    if (els.resetBtn) els.resetBtn.disabled = false;
    els.fileMeta.textContent = `${file.name} · ${formatFileSize(file.size)}`;
    els.fileMeta.title = file.name;
    setStatus(options.autoExtract === false ? 'PDF pronto para leitura.' : 'PDF pronto; a iniciar leitura automática...');
    if (options.autoExtract !== false) {
      window.setTimeout(() => extractDocument(), 0);
    }
  }

  function resetScreen() {
    resetDraftState();
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
    state.originSearchToken += 1;
    state.originPayload = null;
    state.originCandidates = [];
    state.activeOriginStage = '';
    state.selectedOrigins = [];
    state.selectedProject = null;
    state.projectCandidates = [];
    state.projectSuggestionDismissed = false;
    state.deliveryNoteGroups = [];
    state.virtualDeliveryNotesActive = false;
    state.originLineMatches = [];
    state.originLineReferenceLabel = '';
    state.originLineMatchByLine = new WeakMap();
    state.selectedSplitLines = new Set();
    state.controlOk = false;
    state.submittingControl = false;
    state.correspondenceLookupToken += 1;
    state.correspondenceReference = null;
    state.correspondenceYear = null;
    state.submittingPhc = false;
    state.submittingControl = false;
    state.workflowSubmitting = false;
    state.workflow = {};
    state.controlOk = false;
    state.integratedPhc = false;
    state.integrationResult = null;
    els.input.value = '';
    els.preview.hidden = true;
    els.dropzone.hidden = false;
    els.runBtn.disabled = true;
    els.openPdfBtn.disabled = true;
    if (els.deleteBtn) els.deleteBtn.disabled = true;
    if (els.resetBtn) els.resetBtn.disabled = true;
    els.empty.hidden = false;
    els.empty.querySelector('strong').textContent = 'Nenhum documento analisado';
    els.empty.querySelector('span').textContent = 'Carrega um PDF para identificar cliente, fornecedor, cabeçalho, linhas, IVA e totais.';
    els.loading.hidden = true;
    els.results.hidden = true;
    els.fileMeta.textContent = 'Seleciona um PDF até 50 MB.';
    els.fileMeta.removeAttribute('title');
    els.resultMeta.textContent = 'Os resultados aparecem aqui depois da leitura.';
    els.correspondenceReference.textContent = 'Correspondência por criar';
    els.documentSummary.textContent = 'Os dados do documento aparecem aqui depois da leitura.';
    els.gedFileName.textContent = '--';
    els.gedPath.textContent = '--';
    els.netTotal.textContent = '--';
    els.taxTotal.textContent = '--';
    els.grossTotal.textContent = '--';
    els.groupNavigator.hidden = true;
    renderProjectCard();
    window.history.replaceState({}, '', extractUrl(''));
    setStatus('Pronto.');
    updateSubmitPhcButton();
  }

  async function fetchJson(url, options = {}) {
    const target = new URL(url, window.location.origin);
    if (target.pathname.startsWith('/api/document_ai/') && !target.searchParams.has('view')) {
      target.searchParams.set('view', state.view);
    }
    const response = await fetch(`${target.pathname}${target.search}`, options);
    let payload = {};
    try {
      payload = await response.json();
    } catch (_) {}
    if (!response.ok) {
      const error = new Error(payload.error || `HTTP ${response.status}`);
      error.status = response.status;
      error.payload = payload;
      throw error;
    }
    return payload;
  }

  function draftFingerprint(documentData = state.documentData) {
    return JSON.stringify(documentData || {});
  }

  function markLineManualFields(line, ...fields) {
    if (!line) return;
    const current = new Set(Array.isArray(line._manual_fields) ? line._manual_fields : []);
    fields.filter(Boolean).forEach((field) => current.add(field));
    line._manual_fields = [...current];
  }

  function captureManualOverrides(documentData = state.documentData) {
    if (!documentData) return null;
    const snapshot = { lines: [] };
    if (documentData.customer?.manually_selected || documentData.customer?.ged_folder_manually_selected) {
      snapshot.customer = structuredClone(documentData.customer);
    }
    if (documentData.supplier?.manually_selected || documentData.supplier_explicitly_absent) {
      snapshot.supplier = structuredClone(documentData.supplier || {});
      snapshot.supplier_explicitly_absent = Boolean(documentData.supplier_explicitly_absent);
      snapshot.external_party_role = documentData.external_party_role;
    }
    if (documentData.origin_project_manually_selected || documentData.origin_project_manually_cleared) {
      snapshot.origin_project = documentData.origin_project ? structuredClone(documentData.origin_project) : null;
      snapshot.origin_project_manually_selected = Boolean(documentData.origin_project_manually_selected);
      snapshot.origin_project_manually_cleared = Boolean(documentData.origin_project_manually_cleared);
    }
    (documentData.lines || []).forEach((line, index) => {
      const fields = Array.isArray(line?._manual_fields) ? line._manual_fields : [];
      if (!fields.length) return;
      snapshot.lines.push({
        index,
        fields: [...fields],
        values: Object.fromEntries(fields.map((field) => [field, structuredClone(line[field])])),
      });
    });
    return snapshot.customer || snapshot.supplier || snapshot.origin_project_manually_selected
      || snapshot.origin_project_manually_cleared || snapshot.lines.length ? snapshot : null;
  }

  function applyManualOverrides(documentData, snapshot) {
    if (!snapshot) return documentData;
    const merged = structuredClone(documentData || {});
    if (snapshot.customer) merged.customer = structuredClone(snapshot.customer);
    if (snapshot.supplier) {
      merged.supplier = structuredClone(snapshot.supplier);
      merged.supplier_explicitly_absent = snapshot.supplier_explicitly_absent;
      if (snapshot.external_party_role) merged.external_party_role = snapshot.external_party_role;
    }
    if (snapshot.origin_project_manually_selected || snapshot.origin_project_manually_cleared) {
      if (snapshot.origin_project) merged.origin_project = structuredClone(snapshot.origin_project);
      else delete merged.origin_project;
      merged.origin_project_manually_selected = snapshot.origin_project_manually_selected;
      merged.origin_project_manually_cleared = snapshot.origin_project_manually_cleared;
    }
    snapshot.lines.forEach(({ index, fields, values }) => {
      const line = merged.lines?.[index];
      if (!line) return;
      fields.forEach((field) => { line[field] = structuredClone(values[field]); });
      line._manual_fields = [...new Set([...(line._manual_fields || []), ...fields])];
    });
    return merged;
  }

  function resetDraftState() {
    window.clearTimeout(state.draftTimer);
    state.draftTimer = null;
    state.draftRequest = null;
    state.draftVersion = '';
    state.draftRevision = 0;
    state.draftSavedRevision = 0;
    state.draftLastFingerprint = '';
    state.draftError = false;
    state.draftConflict = false;
    if (els.saveRetryBtn) els.saveRetryBtn.hidden = true;
    els.conflictModal?.classList.remove('sz_is_open');
    els.conflictModal?.setAttribute('aria-hidden', 'true');
  }

  function setDraftStatus(status) {
    if (status === 'error' || status === 'conflict') state.draftError = true;
    if (status === 'saved') state.draftError = false;
    if (status === 'conflict') state.draftConflict = true;
    if (els.saveRetryBtn) els.saveRetryBtn.hidden = !state.draftError || state.draftConflict;
    if (status === 'saving') setStatus('A guardar...');
    else if (status === 'saved') setStatus('Guardado');
    else if (status === 'error') setStatus('Não foi possível guardar as alterações.', true);
    else if (status === 'conflict') setStatus('Documento alterado por outro utilizador.', true);
    updateSubmitPhcButton();
  }

  function openDraftConflict() {
    setDraftStatus('conflict');
    els.conflictModal?.classList.add('sz_is_open');
    els.conflictModal?.setAttribute('aria-hidden', 'false');
    window.setTimeout(() => els.conflictReload?.focus(), 0);
  }

  function scheduleAnalysisSave({ immediate = false } = {}) {
    if (state.readOnly) return Promise.resolve(true);
    if (!state.currentDocumentId || !state.documentData || state.draftConflict) return Promise.resolve(false);
    state.draftRevision += 1;
    window.clearTimeout(state.draftTimer);
    setDraftStatus('saving');
    if (immediate) return flushAnalysisSave();
    state.draftTimer = window.setTimeout(() => flushAnalysisSave(), 450);
    return Promise.resolve(true);
  }

  async function flushAnalysisSave() {
    if (state.readOnly) return true;
    window.clearTimeout(state.draftTimer);
    state.draftTimer = null;
    if (!state.currentDocumentId || !state.documentData || state.draftConflict) return !state.draftError;
    if (state.draftRequest) {
      try {
        await state.draftRequest;
      } catch (_) {
        return false;
      }
      if (state.draftConflict) return false;
    }
    const revision = state.draftRevision;
    const fingerprint = draftFingerprint();
    if (fingerprint === state.draftLastFingerprint && !state.draftError) {
      state.draftSavedRevision = Math.max(state.draftSavedRevision, revision);
      setDraftStatus('saved');
      return true;
    }
    const snapshot = JSON.parse(fingerprint);
    setDraftStatus('saving');
    state.draftRequest = fetchJson(`/api/document_ai/documents/${encodeURIComponent(state.currentDocumentId)}/draft`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ expected_version: state.draftVersion, document: snapshot }),
    });
    try {
      const payload = await state.draftRequest;
      state.draftVersion = String(payload.version || state.draftVersion || '');
      state.draftLastFingerprint = fingerprint;
      state.draftSavedRevision = revision;
      state.draftError = false;
    } catch (error) {
      if (error.status === 409 || error.payload?.code === 'document_version_conflict') {
        openDraftConflict();
      } else {
        setDraftStatus('error');
      }
      return false;
    } finally {
      state.draftRequest = null;
    }
    if (state.draftRevision > revision || draftFingerprint() !== fingerprint) {
      return flushAnalysisSave();
    }
    setDraftStatus('saved');
    return true;
  }

  function closeDuplicateModal() {
    els.duplicateModal?.classList.remove('sz_is_open');
    els.duplicateModal?.setAttribute('aria-hidden', 'true');
  }

  function openDuplicateModal(matches) {
    state.duplicateMatches = Array.isArray(matches) ? matches : [];
    if (!els.duplicateModal || !els.duplicateList || !state.duplicateMatches.length) return;
    const duplicateFieldLabels = {
      file_hash: 'ficheiro',
      feid: 'entidade',
      supplier: 'fornecedor',
      doc_class: 'tipo de documento',
      document_date: 'data',
      document_number: 'número',
      gross_total: 'valor total',
      currency: 'moeda',
    };
    els.duplicateList.innerHTML = state.duplicateMatches.map((match) => `
      <article class="docai-duplicate-item">
        <div>
          <strong>${escapeHtml(match.file_name || match.document_id || 'Documento existente')}</strong>
          <span class="sz_text_muted">
            ${match.classification === 'possible' ? 'Possível duplicado' : 'Duplicado certo'}
            · ${Number(match.score || 0)}%
            · ${escapeHtml((match.matching_fields || []).map((field) => duplicateFieldLabels[field] || field).join(', ') || 'correspondência documental')}
          </span>
        </div>
        <div class="docai-duplicate-actions">
          <button type="button" class="sz_button sz_button_secondary" data-open-duplicate="${escapeHtml(match.document_id || '')}">
            <i class="fa-solid fa-arrow-up-right-from-square"></i>
            <span>Abrir documento</span>
          </button>
          <button type="button" class="sz_button sz_button_primary" data-associate-duplicate="${escapeHtml(match.document_id || '')}">
            <i class="fa-solid fa-link"></i>
            <span>Associar ao existente</span>
          </button>
        </div>
      </article>
    `).join('');
    els.duplicateModal.classList.add('sz_is_open');
    els.duplicateModal.setAttribute('aria-hidden', 'false');
  }

  async function saveDuplicateDecision(decision, duplicateDocumentId) {
    if (!state.currentDocumentId || !duplicateDocumentId) return null;
    const response = await fetch(
      `/api/document_ai/documents/${encodeURIComponent(state.currentDocumentId)}/duplicate-decision?view=${encodeURIComponent(state.view)}`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ decision, duplicate_document_id: duplicateDocumentId }),
      },
    );
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(payload.error || 'Não foi possível guardar a decisão de duplicado.');
    return payload;
  }

  function accessPermissionInputs() {
    return Array.from(document.querySelectorAll('[data-integration-access-type]'));
  }

  function closeAccessModal() {
    window.clearTimeout(state.accessSearchTimer);
    els.accessModal?.classList.remove('sz_is_open');
    els.accessModal?.setAttribute('aria-hidden', 'true');
  }

  function selectAccessUser(index) {
    const selected = state.accessUsers[Number(index)];
    if (!selected) return;
    state.accessSelectedUser = selected;
    els.accessSelected.textContent = `${selected.name || selected.login} · ${selected.login}`;
    els.accessPermissions?.classList.remove('is-disabled');
    if (els.accessHelp) els.accessHelp.textContent = 'Marca os tipos de documento que este utilizador pode lançar.';
    accessPermissionInputs().forEach((input) => {
      input.disabled = false;
      input.checked = Boolean(selected.permissions?.[input.dataset.integrationAccessType]);
    });
    els.accessSave.disabled = false;
    renderAccessUsers();
  }

  function renderAccessUsers() {
    if (!els.accessUsers) return;
    if (!state.accessUsers.length) {
      els.accessUsers.innerHTML = '<div class="docai-empty-state">Não foram encontrados utilizadores.</div>';
      return;
    }
    els.accessUsers.innerHTML = state.accessUsers.map((user, index) => {
      const selected = state.accessSelectedUser?.login === user.login;
      const activeCount = Object.values(user.permissions || {}).filter(Boolean).length;
      return `
        <button type="button" class="docai-access-user-option${selected ? ' is-selected' : ''}" data-integration-access-user="${index}">
          <span class="docai-access-user-identity">
            <strong>${escapeHtml(user.name || user.login)}</strong>
            <small>${escapeHtml(user.login)}${user.email ? ` · ${escapeHtml(user.email)}` : ''}</small>
          </span>
          <span class="docai-access-user-count">${activeCount}/6</span>
          <i class="fa-solid fa-chevron-right" aria-hidden="true"></i>
        </button>`;
    }).join('');
  }

  async function searchAccessUsers() {
    if (!els.accessUsers) return;
    const token = ++state.accessSearchToken;
    const query = els.accessSearch.value.trim();
    els.accessSearchBtn.disabled = true;
    els.accessUsers.innerHTML = '<div class="docai-empty-state">A procurar utilizadores...</div>';
    try {
      const users = await fetchJson(`/api/document_ai/integration-access/users?q=${encodeURIComponent(query)}&limit=40`);
      if (token !== state.accessSearchToken) return;
      state.accessUsers = Array.isArray(users) ? users : [];
      if (state.accessSelectedUser) {
        const refreshed = state.accessUsers.find((user) => user.login === state.accessSelectedUser.login);
        if (refreshed) state.accessSelectedUser = refreshed;
      }
      renderAccessUsers();
    } catch (error) {
      if (token !== state.accessSearchToken) return;
      els.accessUsers.innerHTML = `<div class="docai-empty-state">${escapeHtml(error.message || 'Erro na pesquisa de utilizadores.')}</div>`;
    } finally {
      if (token === state.accessSearchToken) els.accessSearchBtn.disabled = false;
    }
  }

  function openAccessModal() {
    if (!els.accessModal) return;
    state.accessSelectedUser = null;
    els.accessSelected.textContent = 'Nenhum utilizador selecionado';
    els.accessPermissions?.classList.add('is-disabled');
    if (els.accessHelp) els.accessHelp.textContent = 'Seleciona primeiro um utilizador.';
    els.accessSave.disabled = true;
    accessPermissionInputs().forEach((input) => {
      input.checked = false;
      input.disabled = true;
    });
    els.accessSearch.value = '';
    els.accessModal.classList.add('sz_is_open');
    els.accessModal.setAttribute('aria-hidden', 'false');
    searchAccessUsers();
    window.setTimeout(() => els.accessSearch.focus(), 50);
  }

  async function saveAccessPermissions() {
    const selected = state.accessSelectedUser;
    if (!selected) return;
    const permissions = {};
    accessPermissionInputs().forEach((input) => {
      permissions[input.dataset.integrationAccessType] = input.checked;
    });
    els.accessSave.disabled = true;
    try {
      const payload = await fetchJson('/api/document_ai/integration-access', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ login: selected.login, permissions }),
      });
      selected.permissions = { ...(payload.permissions || permissions) };
      renderAccessUsers();
      if (els.accessHelp) els.accessHelp.textContent = 'Acessos guardados. Podes fazer novas alterações.';
      showMessage(payload.message || 'Acessos atualizados.', 'success');
    } catch (error) {
      showMessage(error.message || 'Não foi possível guardar os acessos.', 'error');
    } finally {
      els.accessSave.disabled = false;
    }
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
    resetDraftState();
    state.originSearchToken += 1;
    state.originPayload = null;
    state.originCandidates = [];
    state.selectedOrigins = [];
    state.selectedProject = null;
    state.projectCandidates = [];
    state.projectSuggestionDismissed = false;
    state.deliveryNoteGroups = [];
    state.virtualDeliveryNotesActive = false;
    state.originLineMatches = [];
    state.originLineReferenceLabel = '';
    state.originLineMatchByLine = new WeakMap();
    state.selectedSplitLines = new Set();
    state.correspondenceLookupToken += 1;
    state.correspondenceReference = null;
    state.correspondenceYear = null;
    state.documentData = null;
    state.matching = {};
    state.supplierCandidates = [];
    els.results.hidden = true;
    els.batchAlert.hidden = true;
    els.originFlow.hidden = true;
    if (els.originTabs) {
      els.originTabs.hidden = true;
      els.originTabs.innerHTML = '';
    }
    els.originLoading.hidden = false;
    els.empty.hidden = false;
    els.empty.querySelector('strong').textContent = 'A iniciar leitura automática';
    els.empty.querySelector('span').textContent = 'A leitura começa assim que o PDF ficar carregado.';
    els.resultMeta.textContent = 'A preparar o documento selecionado para leitura automática.';
    renderProjectCard();
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
    els.loading.querySelector('span').textContent = 'A leitura guardada será reutilizada quando estiver disponível.';
    els.fileMeta.textContent = 'A carregar PDF original...';
    setStatus('A carregar documento do inbox...');
    try {
      const archiveParam = state.readOnly ? '&archive=1' : '';
      const response = await fetch(`/api/document_ai/documents/${encodeURIComponent(documentId)}/original?view=${encodeURIComponent(state.view)}${archiveParam}`);
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
      setFile(file, { autoExtract: !state.readOnly });
      els.loading.hidden = true;
      els.empty.hidden = false;
      els.empty.querySelector('strong').textContent = 'A carregar leitura do documento';
      els.empty.querySelector('span').textContent = 'Será usado o resultado guardado no inbox quando estiver disponível.';
      els.resultMeta.textContent = 'PDF carregado a partir do inbox; a verificar leitura guardada.';
      setStatus(state.readOnly ? 'Consulta do Arquivo.' : 'A verificar se o documento já tem uma leitura guardada...');
      window.history.replaceState({}, '', extractUrl(documentId));
      if (state.readOnly) {
        const detail = await fetchJson(`/api/document_ai/documents/${encodeURIComponent(documentId)}?archive=1`);
        const cached = detail.processing_meta?.llm_full_extraction || {};
        renderResult({
          ...cached,
          document_id: documentId,
          document: detail.result || cached.document || {},
          matching: cached.matching || {},
          workflow: detail.workflow || cached.workflow || {},
          version: detail.version || '',
          processing_status: detail.status || '',
          phc_integration: detail.processing_meta?.phc_integration || cached.phc_integration || {},
        });
      } else if (!options.skipGroup) {
        await loadDocumentGroup(documentId);
      }
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
    const deliveryNoteMap = new Map();
    items.forEach((line) => {
      const number = String(line.origin_delivery_note_number || '').trim();
      if (!number) return;
      if (!deliveryNoteMap.has(number)) {
        deliveryNoteMap.set(number, { number, lines: [], quantity: 0, base_quantity: 0, units: new Set(), net_total: 0 });
      }
      const group = deliveryNoteMap.get(number);
      group.lines.push(line);
      group.quantity += Math.abs(Number(line.qty || 0));
      if (!line._virtual_split_allocation) group.base_quantity += Math.abs(Number(line.qty || 0));
      group.net_total += Number(line.net_amount || 0);
      if (String(line.unit || '').trim()) group.units.add(String(line.unit).trim());
    });
    state.deliveryNoteGroups = Array.from(deliveryNoteMap.values()).map((group) => ({
      number: group.number,
      lines: group.lines,
      line_count: group.lines.length,
      quantity: group.quantity,
      base_quantity: group.base_quantity,
      unit: group.units.size === 1 ? Array.from(group.units)[0] : '',
      net_total: group.net_total,
    }));
    const availableDeliveryNotes = new Set(state.deliveryNoteGroups.map((group) => group.number));
    state.selectedDeliveryNoteGroups = new Set(
      [...state.selectedDeliveryNoteGroups].filter((number) => availableDeliveryNotes.has(number)),
    );
    if (!state.selectedDeliveryNoteGroups.size) {
      state.deliveryNoteGroups.forEach((group) => state.selectedDeliveryNoteGroups.add(group.number));
    }
    state.virtualDeliveryNotesActive = state.deliveryNoteGroups.length > 0;
    Array.from(state.selectedSplitLines).forEach((line) => {
      if (!items.includes(line)) state.selectedSplitLines.delete(line);
    });
    const proportionalGroups = state.deliveryNoteGroups.filter((group) => (
      Number(group.base_quantity || 0) > 0 && state.selectedDeliveryNoteGroups.has(group.number)
    ));
    const primaryFamily = selectedPrimaryOriginFamily() || 'bc';
    const hasDeliveryNoteColumn = primaryFamily === 'bc' && state.virtualDeliveryNotesActive;
    const hasWorkSituationColumn = primaryFamily === 'subcontract';
    const primaryHead = document.getElementById('docAiExtractPrimaryOriginHead');
    const secondaryHead = document.getElementById('docAiExtractSecondaryOriginHead');
    if (primaryHead) primaryHead.textContent = primaryFamily === 'contract' ? 'Contrato' : (primaryFamily === 'subcontract' ? 'C Sub.Emp.' : 'NdE');
    if (secondaryHead) {
      secondaryHead.textContent = hasWorkSituationColumn ? 'SdT Sub.Emp.' : 'GdR';
      secondaryHead.hidden = !hasDeliveryNoteColumn && !hasWorkSituationColumn;
    }
    const canDistributeDeliveryNotes = state.virtualDeliveryNotesActive && proportionalGroups.length > 0;
    els.splitLineBtn.hidden = !canDistributeDeliveryNotes;
    els.splitLineBtn.disabled = !canDistributeDeliveryNotes || state.selectedSplitLines.size === 0;
    els.splitLineBtn.innerHTML = `<i class="fa-solid fa-code-branch"></i><span>${proportionalGroups.length === 1 ? 'Distribuir Guia de Remessa' : `Distribuir ${proportionalGroups.length} Guias de Remessa`}</span>`;
    els.lineCount.textContent = `${items.length} linha(s)`;
    if (!items.length) {
      els.linesBody.innerHTML = '<tr><td colspan="12" class="sz_text_muted">Não foram encontradas linhas comerciais visíveis.</td></tr>';
      return;
    }
    els.linesBody.innerHTML = items.map((line, lineIndex) => {
      const selectedForSplit = state.selectedSplitLines.has(line);
      const project = String(line.ccusto || line.project_ccusto || state.selectedProject?.ccusto || '').trim();
      const groupCode = normalizeLineGroupCode(line.article_group_code);
      const registration = String(line.registration || line.matricula || '').trim();
      const vehicleCell = registration
        ? `<button type="button" class="docai-extract-vehicle-btn is-selected" data-line-vehicle="${lineIndex}" title="${escapeHtml(registration)}" aria-label="${escapeHtml(registration)}"><i class="fa-solid fa-car"></i></button>`
        : `<button type="button" class="docai-extract-vehicle-btn is-empty" data-line-vehicle="${lineIndex}" aria-label="Associar veículo"></button>`;
      const lineDate = String(line.date || line.data || '').trim().slice(0, 10);
      const currencyCode = String(currency || '').trim().toUpperCase();
      const currencySuffix = /^[A-Z]{3}$/.test(currencyCode)
        ? `<span class="docai-extract-line-currency">${escapeHtml(currencyCode)}</span>`
        : '';
      const bcAllocations = Array.isArray(line.bc_allocations) ? line.bc_allocations : [];
      const uniqueBc = new Map();
      bcAllocations.forEach((allocation) => {
        const key = String(allocation.origin_stamp || `${allocation.origin_number || ''}:${allocation.origin_year || ''}`);
        if (!uniqueBc.has(key)) uniqueBc.set(key, allocation);
      });
      const bcSummary = uniqueBc.size > 1
        ? `${uniqueBc.size} NdE`
        : uniqueBc.size === 1
          ? formatBcLabel(Array.from(uniqueBc.values())[0])
          : 'Escolher';
      const hasDistribution = bcAllocations.length > 1;
      const distributionButton = hasDistribution
        ? `<button type="button" class="docai-extract-bc-distribution-toggle" data-line-bc-toggle="${lineIndex}" aria-expanded="${state.expandedBcLines.has(lineIndex) ? 'true' : 'false'}" aria-label="${state.expandedBcLines.has(lineIndex) ? 'Ocultar distribuição por Nota de Encomenda' : 'Mostrar distribuição por Nota de Encomenda'}">${state.expandedBcLines.has(lineIndex) ? '−' : '+'}</button>`
        : '';
      const bcRows = primaryFamily === 'bc' && hasDistribution && state.expandedBcLines.has(lineIndex)
        ? bcAllocations.map((allocation) => `<tr class="docai-extract-bc-allocation-row">
            <td></td><td></td><td></td>
            <td class="docai-extract-number">${escapeHtml(formatNumber(allocation.quantity))}</td>
            <td class="docai-extract-number">${escapeHtml(formatMoney(allocation.unit_price, currency))}</td>
            <td class="docai-extract-number">${escapeHtml(formatMoney(allocation.total, currency))}</td>
            <td></td><td></td><td></td><td hidden></td>
            <td><span class="docai-extract-bc-ref">${escapeHtml(formatBcLabel(allocation))}${allocation.origin_line_order ? ` · Linha ${escapeHtml(formatNumber(allocation.origin_line_order))}` : ''}</span></td>${hasDeliveryNoteColumn ? '<td></td>' : ''}
          </tr>`).join('')
        : '';
      const primaryOrigin = state.selectedOrigins.find((origin) => originFamily(origin) === primaryFamily);
      const primaryReference = primaryFamily === 'bc'
        ? `<button type="button" class="docai-extract-cell-link" data-line-bc="${lineIndex}" title="Associar Nota de Encomenda à linha">${escapeHtml(bcSummary)}</button>${distributionButton}`
        : `<span class="docai-extract-bc-ref">${escapeHtml(primaryOrigin ? `${primaryFamily === 'subcontract' ? 'Contrato de SubEmpreitada' : 'Contrato'} N.º ${primaryOrigin.number || '--'}${primaryOrigin.year ? ` / ${primaryOrigin.year}` : ''}` : '--')}</span>`;
      const workSituation = state.selectedOrigins.find((origin) => originFamily(origin) === 'work_situation');
      const secondaryCell = hasDeliveryNoteColumn
        ? `<td class="docai-extract-line-picker-cell"><input type="checkbox" class="docai-extract-bl-selector" data-line-select="${lineIndex}" role="checkbox" aria-label="Selecionar para distribuir por Guia de Remessa" aria-checked="${selectedForSplit ? 'true' : 'false'}" ${selectedForSplit ? 'checked' : ''} ${line._virtual_split_allocation ? 'disabled' : ''}></td>`
        : hasWorkSituationColumn
          ? `<td><span class="docai-extract-bc-ref">${escapeHtml(workSituation ? `N.º ${workSituation.number || '--'}${workSituation.year ? ` / ${workSituation.year}` : ''}` : '--')}</span></td>`
          : '';
      return `<tr class="${line._virtual_split_allocation ? 'is-split-allocation' : ''}">
        <td><input class="sz_input docai-extract-line-group-input" data-line-group="${lineIndex}" value="${escapeHtml(groupCode)}" title="P = Principal · A = Associado" aria-label="Grupo de artigo"></td>
        <td><button type="button" class="docai-extract-cell-link" data-line-article="${lineIndex}" title="Escolher artigo PHC">${escapeHtml(line.ref || 'Escolher')}</button></td>
        <td><input class="sz_input docai-extract-line-description-input" data-line-description="${lineIndex}" value="${escapeHtml(line.description || '')}" aria-label="Designação da linha"></td>
        <td><input class="sz_input docai-extract-line-number-input" inputmode="decimal" data-line-qty="${lineIndex}" value="${escapeHtml(formatEditableAmount(line.qty))}" aria-label="Quantidade"></td>
        <td><span class="docai-extract-line-money-input"><input class="sz_input docai-extract-line-number-input" inputmode="decimal" data-line-unit-price="${lineIndex}" value="${escapeHtml(formatEditableAmount(line.unit_price))}" aria-label="Preço unitário">${currencySuffix}</span></td>
        <td><span class="docai-extract-line-money-input"><input class="sz_input docai-extract-line-number-input" inputmode="decimal" data-line-total="${lineIndex}" value="${escapeHtml(formatEditableAmount(line.net_amount))}" aria-label="Preço total">${currencySuffix}</span></td>
        <td><button type="button" class="docai-extract-cell-link" data-line-project="${lineIndex}" title="Escolher uma obra">${escapeHtml(project || 'Escolher')}</button></td>
        <td class="docai-extract-vehicle-cell">${vehicleCell}</td>
        <td><input type="date" class="sz_input docai-extract-line-date-input" data-line-date="${lineIndex}" value="${escapeHtml(lineDate)}" aria-label="Data da linha"></td>
        <td class="docai-extract-line-distribution" hidden></td>
        <td class="docai-extract-bc-ref-cell">${primaryReference}</td>
        ${secondaryCell}
      </tr>${bcRows}`;
    }).join('');
  }

  function applyReadOnlyState() {
    if (!state.readOnly || !pageRoot) return;
    pageRoot.querySelectorAll('input, select, textarea').forEach((control) => {
      control.disabled = true;
      control.setAttribute('aria-readonly', 'true');
    });
    [els.customerCard, els.supplierCard, els.projectCard].forEach((card) => {
      if (!card) return;
      card.removeAttribute('tabindex');
      card.removeAttribute('role');
      card.setAttribute('aria-disabled', 'true');
    });
    if (els.splitLineBtn) els.splitLineBtn.hidden = true;
    if (els.status) {
      els.status.textContent = 'Consulta do Arquivo';
      els.status.hidden = false;
    }
  }

  function renderTaxes(taxes, currency) {
    const items = Array.isArray(taxes) ? taxes : [];
    if (!items.length) {
      els.taxesBody.innerHTML = '<tr><td colspan="4" class="sz_text_muted">Sem discriminação de IVA visível.</td></tr>';
      return;
    }
    const rows = items.map((tax) => `
      <tr>
        <td>${escapeHtml(`${formatNumber(tax.tax_rate, 2)}%`)}</td>
        <td class="docai-extract-number">${escapeHtml(formatMoney(tax.taxable_base, currency))}</td>
        <td class="docai-extract-number">${escapeHtml(formatMoney(tax.tax_amount, currency))}</td>
        <td class="docai-extract-number">${escapeHtml(formatMoney(tax.gross_total, currency))}</td>
      </tr>
    `).join('');
    const totals = items.reduce((result, tax) => ({
      taxable_base: result.taxable_base + Number(tax.taxable_base || 0),
      tax_amount: result.tax_amount + Number(tax.tax_amount || 0),
      gross_total: result.gross_total + Number(tax.gross_total || 0),
    }), { taxable_base: 0, tax_amount: 0, gross_total: 0 });
    const totalRow = items.length > 1 ? `<tr class="docai-tax-total-row">
      <th>Total</th>
      <th class="docai-extract-number">${escapeHtml(formatMoney(totals.taxable_base, currency))}</th>
      <th class="docai-extract-number">${escapeHtml(formatMoney(totals.tax_amount, currency))}</th>
      <th class="docai-extract-number">${escapeHtml(formatMoney(totals.gross_total, currency))}</th>
    </tr>` : '';
    els.taxesBody.innerHTML = `${rows}${totalRow}`;
  }

  function openTotalsModal() {
    if (!state.documentData || !els.totalsModal) return;
    els.totalsModal.classList.add('sz_is_open');
    els.totalsModal.setAttribute('aria-hidden', 'false');
    els.totalsCloseTop?.focus();
  }

  function closeTotalsModal() {
    els.totalsModal?.classList.remove('sz_is_open');
    els.totalsModal?.setAttribute('aria-hidden', 'true');
    els.totalsCard?.focus();
  }

  async function copyClassificationValue(value) {
    if (!value) return;
    try {
      await navigator.clipboard.writeText(value);
      showMessage('Copiado.', 'success');
    } catch (_) {
      showMessage('Não foi possível copiar.', 'error');
    }
  }

  function renderSupplierCard(supplier = {}, matching = {}) {
    const isCorrespondence = ['mail', 'bank_statement'].includes(state.documentData?.document_type);
    const isCustomerMail = isCorrespondence && state.documentData?.external_party_role === 'customer';
    const supplierNo = Number(isCustomerMail ? supplier.customer_no : (supplier.supplier_no || supplier.no) || 0);
    const supplierNumberLabel = phcPartyNumber(supplierNo, supplier.estab);
    const matched = Boolean(supplierNo);
    els.partyLabel.textContent = isCorrespondence ? 'Remetente' : 'Fornecedor';
    els.supplierName.textContent = supplier.name || supplier.llm_name || 'Fornecedor por associar';
    els.supplierTax.textContent = supplier.tax_id
      ? `${isCustomerMail ? 'NIF' : 'NIF/NCONT'}: ${supplier.tax_id}`
      : `${isCustomerMail ? 'NIF' : 'NIF/NCONT'} não identificado`;
    if (isCorrespondence) {
      els.supplierNo.hidden = false;
      const roleLabel = isCustomerMail ? 'cliente' : (state.documentData?.external_party_role === 'supplier' ? 'fornecedor' : 'entidade');
      els.supplierNo.textContent = `Nº ${roleLabel}: ${supplierNumberLabel || '--'}`;
      els.supplierCard.classList.toggle('is-unmatched', !matched);
      els.supplierCard.classList.toggle('is-matched', matched);
      if (supplier.manually_named) {
        els.supplierHint.innerHTML = '<i class="fa-solid fa-pen"></i> Nome introduzido manualmente';
      } else if (matched) {
        els.supplierHint.innerHTML = `<i class="fa-solid fa-circle-check"></i> ${isCustomerMail ? 'Cliente encontrado na CL' : 'Fornecedor encontrado na FL'}`;
      } else {
        els.supplierHint.innerHTML = '<i class="fa-solid fa-hand-pointer"></i> Procurar ou escrever o remetente';
      }
      els.supplierCard.setAttribute('aria-label', 'Escolher ou escrever remetente');
      els.supplierHint.hidden = true;
      return;
    }
    els.supplierNo.hidden = false;
    els.supplierNo.textContent = `Nº fornecedor: ${supplierNumberLabel || '--'}`;
    els.supplierCard.classList.toggle('is-unmatched', !matched);
    els.supplierCard.classList.toggle('is-matched', matched);
    els.supplierHint.innerHTML = matched
      ? '<i class="fa-solid fa-pen"></i> Alterar fornecedor'
      : '<i class="fa-solid fa-hand-pointer"></i> Escolher fornecedor semelhante';
    els.supplierCard.setAttribute('aria-label', matched ? 'Alterar fornecedor' : 'Escolher fornecedor semelhante');
    if (!matching?.supplier_query?.feid) {
      els.supplierHint.innerHTML = `<i class="fa-solid fa-triangle-exclamation"></i> ${['mail', 'bank_statement'].includes(state.documentData?.document_type) ? 'Entidade' : 'Empresa cliente'} não identificada na FE`;
    } else if (matching?.supplier_lookup_error) {
      els.supplierHint.innerHTML = '<i class="fa-solid fa-triangle-exclamation"></i> Não foi possível consultar a FL';
    }
    els.supplierHint.hidden = true;
  }

  function renderCustomerCard(customer = {}, matching = {}) {
    const isMail = state.documentData?.document_type === 'mail';
    const matched = Boolean(customer.feid && matching.customer_matched !== false);
    els.customerLabel.textContent = 'Entidade';
    els.customerName.textContent = matched ? (customer.name || '--') : 'Entidade por associar';
    els.customerTax.textContent = matched && customer.tax_id ? `NIF: ${customer.tax_id}` : (matched ? 'NIF não identificado' : '');
    els.customerHint.hidden = true;
    els.customerCard.tabIndex = 0;
    els.customerCard.setAttribute('aria-label', matched ? 'Alterar entidade' : 'Escolher entidade');
    els.customerHint.innerHTML = matched
      ? '<i class="fa-solid fa-pen"></i> Alterar entidade'
      : '<i class="fa-solid fa-hand-pointer"></i> Escolher empresa do grupo';
    els.customerCard.classList.toggle('is-unmatched', !matched);
    els.customerCard.classList.toggle('is-matched', matched);
  }

  function closeEntityModal() {
    window.clearTimeout(state.entitySearchTimer);
    els.entityModal.classList.remove('sz_is_open');
    els.entityModal.setAttribute('aria-hidden', 'true');
  }

  function renderEntityCandidates(items) {
    state.entityCandidates = Array.isArray(items) ? items : [];
    if (!state.entityCandidates.length) {
      els.entityList.innerHTML = '<div class="docai-empty-state">Não foram encontradas empresas do grupo.</div>';
      return;
    }
    els.entityList.innerHTML = state.entityCandidates.map((item, index) => `
      <button type="button" class="docai-supplier-match-option" data-entity-index="${index}">
        <span class="docai-supplier-match-main"><strong>${escapeHtml(item.name || '--')}</strong><span>FEID ${escapeHtml(item.feid || '--')} · NIF ${escapeHtml(item.tax_id || '--')}</span></span>
      </button>
    `).join('');
  }

  async function searchEntityCandidates() {
    els.entitySearchBtn.disabled = true;
    els.entityList.innerHTML = '<div class="docai-empty-state">A procurar empresas do grupo...</div>';
    try {
      const query = els.entitySearch.value.trim();
      const items = await fetchJson(`/api/document_ai/entities/search?q=${encodeURIComponent(query)}&limit=30`);
      renderEntityCandidates(items);
    } catch (error) {
      els.entityList.innerHTML = `<div class="docai-empty-state">${escapeHtml(error.message || 'Erro na pesquisa.')}</div>`;
    } finally {
      els.entitySearchBtn.disabled = false;
    }
  }

  function openEntityModal() {
    if (!state.documentData) return;
    els.entitySearch.value = '';
    els.entityModal.classList.add('sz_is_open');
    els.entityModal.setAttribute('aria-hidden', 'false');
    searchEntityCandidates();
    window.setTimeout(() => els.entitySearch.focus(), 50);
  }

  async function rematchExternalParty() {
    const feid = Number(state.documentData?.customer?.feid || 0);
    const party = state.documentData?.supplier || {};
    const query = party.llm_tax_id || party.tax_id || party.llm_name || party.name || '';
    if (!feid || String(query).trim().length < 2) return;
    const isCorrespondence = ['mail', 'bank_statement'].includes(state.documentData.document_type);
    const endpoint = isCorrespondence ? 'external-parties' : 'suppliers';
    try {
      const items = await fetchJson(`/api/document_ai/${endpoint}/search?q=${encodeURIComponent(query)}&feid=${feid}&limit=12`);
      const first = Array.isArray(items) ? items[0] : null;
      const sameNumber = first ? items.filter((item) => item.party_role === first.party_role && Number(item.no || 0) === Number(first.no || 0)) : [];
      const selected = first && Number(first.score || 0) >= 0.72 && sameNumber.length <= 1 ? first : null;
      const isCustomer = isCorrespondence && selected?.party_role === 'customer';
      state.matching.supplier_candidates = Array.isArray(items) ? items : [];
      state.supplierCandidates = state.matching.supplier_candidates;
      if (selected) {
        if (isCorrespondence) state.documentData.external_party_role = isCustomer ? 'customer' : 'supplier';
        state.documentData.supplier = {
          ...party,
          supplier_no: null,
          customer_no: null,
          name: selected.name || party.name,
          short_name: selected.short_name || '',
          tax_id: selected.tax_id || party.tax_id,
          address: selected.address || party.address || '',
          city: selected.city || party.city || '',
          postal_code: selected.postal_code || party.postal_code || '',
          feid,
          ...(isCustomer ? { customer_no: selected.no } : { supplier_no: selected.no }),
          estab: Number(selected.estab || 0),
          match_score: selected.score,
          matched_by: selected.matched_by,
        };
        state.matching.supplier_matched = true;
      } else {
        delete state.documentData.supplier.customer_no;
        delete state.documentData.supplier.supplier_no;
        state.matching.supplier_matched = false;
      }
      renderSupplierCard(state.documentData.supplier, state.matching);
      renderGedDestination();
      setStatus(selected
        ? `${isCustomer ? 'Cliente' : 'Fornecedor'} ${selected.name} encontrado após escolher a entidade.`
        : 'Não foi encontrado automaticamente um cliente ou fornecedor nesta entidade.');
    } catch (error) {
      showMessage(error.message || 'Não foi possível repetir a pesquisa da entidade externa.', 'error');
    }
  }

  async function selectEntity(index) {
    const selected = state.entityCandidates[Number(index)];
    if (!selected || !state.documentData) return;
    const previousFeid = Number(state.documentData.customer?.feid || 0);
    const isCorrespondence = ['mail', 'bank_statement'].includes(state.documentData.document_type);
    if (previousFeid !== Number(selected.feid || 0)) {
      state.selectedOrigins = [];
      state.selectedProject = null;
      state.projectSuggestionDismissed = false;
      state.originLineMatches = [];
      state.originLineReferenceLabel = '';
      renderProjectCard();
      state.gedFolderManuallySelected = false;
    }
    state.documentData.customer = {
      ...state.documentData.customer,
      feid: selected.feid,
      name: selected.name,
      tax_id: selected.tax_id || '',
      phc_database: selected.phc_database || '',
      ged_folder: selected.ged_folder || '',
      manually_selected: true,
      matched_by: 'manual',
    };
    state.matching.customer_matched = true;
    state.matching.customer = { ...selected, matched_by: 'manual' };
    state.matching.supplier_query = { ...(state.matching.supplier_query || {}), feid: selected.feid };
    renderCustomerCard(state.documentData.customer, state.matching);
    closeEntityModal();
    await Promise.all([rematchExternalParty(), loadCorrespondenceReference()]);
    await scheduleAnalysisSave({ immediate: true });
    if (!isCorrespondence) loadOriginCandidates(state.documentData);
  }

  function renderOriginCandidates(payload = {}, options = {}) {
    state.originPayload = payload;
    if (Array.isArray(payload.selected_origins)) {
      state.selectedOrigins = payload.selected_origins.map((origin) => ({ ...origin }));
    } else if (payload.selected_origin) {
      state.selectedOrigins = [{ ...payload.selected_origin }];
    }
    renderProjectCard();
    state.originCandidates = [];
    els.originLoading.hidden = true;
    els.originFlow.hidden = false;
    els.originSource.hidden = !payload.available;
    els.originSource.textContent = payload.available
      ? `${payload.phc_database || 'PHC'} · Fornecedor nº ${phcPartyNumber(payload.supplier?.no, payload.supplier?.estab) || '--'}${payload.selected_project?.ccusto ? ` · Obra ${payload.selected_project.ccusto}` : ''}`
      : '';
    if (!options.skipLineMapping) applyOriginLineReferences(payload);

    const primaryFamily = selectedPrimaryOriginFamily();
    const hasExplicitDeliveryNotes = state.virtualDeliveryNotesActive && state.deliveryNoteGroups.length > 0;
    const virtualStageHtml = primaryFamily === 'bc' && hasExplicitDeliveryNotes ? renderVirtualDeliveryNoteStage() : '';

    if (!payload.available) {
      els.originMeta.hidden = false;
      els.originTabs.hidden = true;
      els.originTabs.innerHTML = '';
      els.originMeta.textContent = virtualStageHtml
        ? `${state.deliveryNoteGroups.length} Guia(s) de Remessa identificada(s) na fatura, ainda por criar no PHC.`
        : payload.message || 'Não foi possível procurar origens no PHC.';
      const unavailableHtml = `<div class="docai-extract-origin-unavailable"><i class="fa-solid fa-circle-info"></i><span>${escapeHtml(payload.message || 'Pesquisa PHC indisponível.')}</span></div>`;
      els.originFlow.innerHTML = `${virtualStageHtml}${unavailableHtml}`;
      return;
    }

    const stages = (Array.isArray(payload.stages) ? payload.stages : [])
      .filter((stage) => Array.isArray(stage.candidates) && stage.candidates.length)
      .filter((stage) => {
        const displayStage = originDisplayStage(String(stage.key || ''));
        if (displayStage === 'bc_contracts') return true;
        if (displayStage === 'delivery_note') return primaryFamily === 'bc' && hasExplicitDeliveryNotes;
        if (displayStage === 'work_situation') return primaryFamily === 'subcontract';
        return false;
      });
    els.originMeta.textContent = '';
    els.originMeta.hidden = true;

    let virtualStageInserted = false;
    let stageHtml = stages.map((stage) => {
      const insertVirtualBefore = virtualStageHtml && !virtualStageInserted && ['delivery_note', 'purchase_order'].includes(stage.key);
      if (insertVirtualBefore) virtualStageInserted = true;
      const candidates = Array.isArray(stage.candidates) ? stage.candidates : [];
      const cards = candidates.map((candidate) => {
        const candidateIndex = state.originCandidates.push(candidate) - 1;
        const associated = state.selectedOrigins.some((origin) => origin.stamp === candidate.stamp);
        const candidateFamily = originFamily(candidate);
        const contractLocked = ['contract', 'subcontract'].includes(candidateFamily)
          && state.selectedOrigins.some((origin) => ['contract', 'subcontract'].includes(originFamily(origin)) && origin.stamp !== candidate.stamp);
        const consulted = state.consultedOriginStamp === candidate.stamp;
        const score = Number(candidate.score || 0);
        const scoreLabel = score > 0 ? ` · ${Math.round(score * 100)}%` : '';
        return `
          <article class="docai-extract-origin-candidate${consulted ? ' is-selected' : ''}${associated ? ' is-associated' : ''}" data-origin-index="${candidateIndex}" role="button" tabindex="0" aria-label="Consultar ${escapeHtml(stage.label || 'origem')} ${escapeHtml(candidate.number || '')}">
            <span class="docai-extract-origin-candidate-top">
              <strong>N.º ${escapeHtml(candidate.number || '--')}${candidate.year ? ` / ${escapeHtml(candidate.year)}` : ''}${scoreLabel}</strong>
              <button type="button" class="docai-origin-link-button${associated ? ' is-associated' : ''}" data-origin-link="${candidateIndex}" aria-label="${associated ? 'Desassociar do processo' : (contractLocked ? 'Contrato associado.' : 'Associar ao processo')}" title="${associated ? 'Desassociar do processo' : (contractLocked ? 'Contrato associado.' : 'Associar ao processo')}" ${contractLocked && !associated ? 'disabled' : ''}><i class="fa-solid ${associated ? 'fa-link-slash' : 'fa-link'}"></i></button>
            </span>
            <span>${escapeHtml(formatDate(candidate.date))}</span>
            <strong class="docai-origin-card-total">${escapeHtml(formatMoney(candidate.total, state.documentData?.currency))}</strong>
          </article>`;
      }).join('');
      const count = candidates.length;
      const singular = stage.key === 'delivery_note' ? 'Guia de remessa' : (stage.key === 'purchase_order' ? 'Nota de encomenda' : (stage.label || 'Origem'));
      const plural = stage.key === 'delivery_note' ? 'Guias de remessa' : (stage.key === 'purchase_order' ? 'Notas de encomenda' : `${singular}s`);
      const stageTitle = stage.key === 'delivery_note'
        ? 'Guias de Remessa no PHC'
        : stage.key === 'subcontract_measurement'
          ? 'Situações de Trabalho no PHC'
          : `${count} ${count === 1 ? singular : plural}`;
      const realStageHtml = `
        <article class="docai-extract-origin-stage" data-origin-stage="${escapeHtml(originDisplayStage(String(stage.key || '')))}">
          <div class="docai-extract-origin-stage-title"><strong>${escapeHtml(stageTitle)}</strong></div>
          <div class="docai-extract-origin-options">${cards}</div>
        </article>`;
      return `${insertVirtualBefore ? virtualStageHtml : ''}${realStageHtml}`;
    }).join('');
    if (virtualStageHtml && !virtualStageInserted) stageHtml += virtualStageHtml;

    els.originFlow.innerHTML = stageHtml || '<div class="docai-extract-origin-unavailable"><i class="fa-solid fa-magnifying-glass"></i><span>Sem documentos anteriores disponíveis para ligar.</span></div>';
    const tabStages = stages.map((stage) => ({
      key: originDisplayStage(String(stage.key || '')),
      label: String(stage.label || stage.key || ''),
    }));
    if (virtualStageHtml) {
      const virtualIndex = Math.max(0, tabStages.findIndex((stage) => ['delivery_note', 'purchase_order'].includes(stage.key)));
      tabStages.splice(virtualIndex, 0, { key: 'delivery_note', label: 'GdR', count: state.deliveryNoteGroups.length });
    }
    renderOriginTabs(tabStages.filter((stage, index, items) => items.findIndex((item) => item.key === stage.key) === index));
  }

  function renderOriginTabs(stages = []) {
    const availableKeys = stages.map((stage) => stage.key).filter(Boolean);
    if (!availableKeys.length) {
      els.originTabs.hidden = true;
      els.originTabs.innerHTML = '';
      return;
    }
    if (!availableKeys.includes(state.activeOriginStage)) state.activeOriginStage = availableKeys[0];
    els.originTabs.hidden = availableKeys.length === 1;
    els.originTabs.innerHTML = stages.map((stage) => {
      const active = stage.key === state.activeOriginStage;
      const officialLabels = {
        bc_contracts: 'Notas de Encomenda / Contratos',
        purchase_order: 'Notas de Encomenda / Contratos',
        delivery_note: 'Guia de Remessa',
        proforma_invoice: 'Pré-Fatura',
        contract: 'Contrato',
        subcontract_contract: 'Contrato de SubEmpreitada',
        work_situation: 'Situação de Trabalhos de SubEmpreitada',
        subcontract_measurement: 'Situação de Trabalhos de SubEmpreitada',
      };
      const label = officialLabels[stage.key] || stage.label;
      return `<button type="button" class="docai-extract-origin-tab${active ? ' is-active' : ''}" role="tab" data-origin-tab="${escapeHtml(stage.key)}" aria-selected="${active ? 'true' : 'false'}">${escapeHtml(label)}</button>`;
    }).join('');
    els.originFlow.querySelectorAll('[data-origin-stage]').forEach((panel) => {
      panel.hidden = panel.dataset.originStage !== state.activeOriginStage;
    });
  }

  function applyOriginLineReferences(payload = {}) {
    const candidatePool = (Array.isArray(payload.stages) ? payload.stages : [])
      .flatMap((stage) => Array.isArray(stage.candidates) ? stage.candidates : []);
    const selected = state.selectedOrigins.length
      ? state.selectedOrigins
      : (payload.suggested_origin ? [payload.suggested_origin] : []);
    const purchaseOrders = selected.map((origin) => {
      const candidate = candidatePool.find((item) => item.stamp === origin.stamp);
      return candidate || origin;
    }).filter((origin) => origin?.document_type === 'purchase_order' || Number(origin?.ndos || 0) === 102);
    const matches = purchaseOrders.flatMap((origin) => (Array.isArray(origin.line_matches) ? origin.line_matches : []).map((match) => ({
      ...match,
      origin_stamp: origin.stamp || '',
      origin_number: origin.number || '',
      origin_year: origin.year || null,
      origin_reference_label: `NdE ${origin.number || ''}${origin.year ? ` / ${origin.year}` : ''}`.trim(),
    })));
    state.originLineMatches = matches;
    state.originLineMatchByLine = new WeakMap();
    matches.forEach((match) => {
      const line = state.documentData?.lines?.[Number(match.document_line_index)];
      if (line) {
        const lineMatches = state.originLineMatchByLine.get(line) || [];
        lineMatches.push(match);
        state.originLineMatchByLine.set(line, lineMatches);
      }
    });
    state.originLineReferenceLabel = purchaseOrders.map((origin) => `NdE ${origin.number || ''}`).join(', ');
    if (state.documentData?.lines) renderLines(state.documentData.lines, state.documentData.currency || '');
  }

  function renderVirtualDeliveryNoteStage() {
    if (!state.virtualDeliveryNotesActive || !state.deliveryNoteGroups.length) return '';
    const cards = state.deliveryNoteGroups.map((group) => {
      const checked = state.selectedDeliveryNoteGroups.has(group.number);
      return `
        <label class="docai-extract-origin-proposal">
          <input type="checkbox" data-virtual-bl="${escapeHtml(group.number)}" ${checked ? 'checked' : ''}>
          <strong>GdR ${escapeHtml(group.number)}</strong>
          <span>${escapeHtml(group.line_count)} linha(s)</span>
        </label>`;
    }).join('');
    return `
      <article class="docai-extract-origin-stage is-virtual-stage" data-origin-stage="delivery_note">
        <div class="docai-extract-origin-stage-title">
          <strong>${state.deliveryNoteGroups.length} ${state.deliveryNoteGroups.length === 1 ? 'Guia de Remessa a criar' : 'Guias de Remessa a criar'}</strong>
        </div>
        <div class="docai-extract-origin-proposals">${cards}</div>
      </article>`;
  }

  function selectLineForSplit(lineIndex) {
    const line = state.documentData?.lines?.[Number(lineIndex)];
    if (!line || line._virtual_split_allocation) return;
    if (state.selectedSplitLines.has(line)) state.selectedSplitLines.delete(line);
    else state.selectedSplitLines.add(line);
    renderLines(state.documentData.lines, state.documentData.currency || '');
  }

  function proportionalPart(total, ratio, allocated, isLast) {
    if (isLast) return Math.round((Number(total || 0) - allocated) * 1000000) / 1000000;
    return Math.round((Number(total || 0) * ratio) * 1000000) / 1000000;
  }

  async function distributeSelectedLinesAcrossDeliveryNotes() {
    const lines = state.documentData?.lines;
    const selectedLines = Array.from(state.selectedSplitLines).filter((line) => Array.isArray(lines) && lines.includes(line));
    if (!selectedLines.length || !Array.isArray(lines)) return;
    const targetGroups = state.deliveryNoteGroups.filter((group) => (
      Number(group.base_quantity || 0) > 0 && state.selectedDeliveryNoteGroups.has(group.number)
    ));
    const totalWeight = targetGroups.reduce((total, group) => total + Number(group.base_quantity || 0), 0);
    if (!targetGroups.length || totalWeight <= 0) {
      showMessage('É necessária pelo menos uma Guia de Remessa com quantidade identificada.', 'error');
      return;
    }

    const originalLines = [...lines];
    const remainingLines = lines.filter((line) => !state.selectedSplitLines.has(line));
    const createdLines = [];
    selectedLines.forEach((selectedLine) => {
      const selectedMatch = state.originLineMatchByLine.get(selectedLine) || null;
      const allocatedTotals = { qty: 0, net_amount: 0, gross_amount: 0 };
      targetGroups.forEach((group, index) => {
        const ratio = Number(group.base_quantity || 0) / totalWeight;
        const isLast = index === targetGroups.length - 1;
        const allocation = {
          ...selectedLine,
          qty: proportionalPart(selectedLine.qty, ratio, allocatedTotals.qty, isLast),
          net_amount: proportionalPart(selectedLine.net_amount, ratio, allocatedTotals.net_amount, isLast),
          gross_amount: proportionalPart(selectedLine.gross_amount, ratio, allocatedTotals.gross_amount, isLast),
          origin_delivery_note_number: group.number,
          _virtual_split_allocation: true,
          _virtual_split_ratio: ratio,
          _virtual_split_source_description: selectedLine.description || '',
        };
        allocatedTotals.qty += Number(allocation.qty || 0);
        allocatedTotals.net_amount += Number(allocation.net_amount || 0);
        allocatedTotals.gross_amount += Number(allocation.gross_amount || 0);
        let insertionIndex = -1;
        remainingLines.forEach((remainingLine, lineIndexValue) => {
          if (String(remainingLine.origin_delivery_note_number || '').trim() === group.number) insertionIndex = lineIndexValue;
        });
        remainingLines.splice(insertionIndex >= 0 ? insertionIndex + 1 : remainingLines.length, 0, allocation);
        if (selectedMatch) state.originLineMatchByLine.set(allocation, selectedMatch);
        createdLines.push(allocation);
      });
    });

    state.documentData.lines = remainingLines;
    state.selectedSplitLines = new Set();
    renderLines(state.documentData.lines, state.documentData.currency || '');
    if (state.originPayload && state.virtualDeliveryNotesActive) {
      renderOriginCandidates(state.originPayload, { skipLineMapping: true });
    }
    els.splitLineBtn.disabled = true;
    setStatus(`A guardar ${selectedLines.length} linha(s) distribuída(s) por ${targetGroups.length} Guia(s) de Remessa...`);
    if (state.currentDocumentId) {
      try {
        const payload = await fetchJson(`/api/document_ai/documents/${encodeURIComponent(state.currentDocumentId)}/lines`, {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ lines: state.documentData.lines }),
        });
        state.draftVersion = String(payload.version || state.draftVersion || '');
        state.draftLastFingerprint = draftFingerprint();
      } catch (error) {
        state.documentData.lines = originalLines;
        state.selectedSplitLines = new Set(selectedLines);
        renderLines(state.documentData.lines, state.documentData.currency || '');
        if (state.originPayload && state.virtualDeliveryNotesActive) {
          renderOriginCandidates(state.originPayload, { skipLineMapping: true });
        }
        setStatus(error.message || 'Não foi possível guardar a repartição das linhas.', true);
        showMessage(error.message || 'Não foi possível guardar a repartição das linhas.', 'error');
        return;
      }
    }
    const allocationSummary = createdLines
      .map((line) => `GdR ${line.origin_delivery_note_number}: ${formatNumber(line.qty)}`)
      .join(' · ');
    setStatus(`${selectedLines.length} linha(s) repartida(s) proporcionalmente. ${allocationSummary}`);
    showMessage(`${selectedLines.length} linha(s) distribuída(s) por ${targetGroups.length} Guia(s) de Remessa sem alterar os totais.`, 'success');
  }

  async function loadOriginCandidates(documentData) {
    const token = ++state.originSearchToken;
    state.originPayload = null;
    state.originCandidates = [];
    state.selectedOrigins = [];
    els.originLoading.hidden = false;
    els.originFlow.hidden = true;
    els.originSource.hidden = true;
    els.originMeta.textContent = 'A procurar documentos anteriores no PHC...';
    try {
      const payload = await fetchJson('/api/document_ai/origins/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ document: documentData || {}, document_id: state.currentDocumentId || '' }),
      });
      if (token !== state.originSearchToken) return;
      const suggestedProject = projectSuggestedByOrigin(payload);
      if (!state.selectedProject?.ccusto && !state.projectSuggestionDismissed && suggestedProject) {
        state.selectedProject = suggestedProject;
        state.documentData.origin_project = { ...suggestedProject };
        renderProjectCard();
        setStatus(`Obra ${suggestedProject.ccusto} sugerida pela origem ${suggestedProject.suggested_by_document}.`);
        await loadOriginCandidates(state.documentData);
        return;
      }
      renderOriginCandidates(payload);
    } catch (error) {
      if (token !== state.originSearchToken) return;
      renderOriginCandidates({ available: false, message: error.message || 'Erro ao consultar o PHC.' });
    }
  }

  async function linkDocumentOrigin(index) {
    const selected = state.originCandidates[Number(index)];
    if (!selected) return;
    const alreadySelected = state.selectedOrigins.some((origin) => origin.stamp === selected.stamp);
    if (!state.currentDocumentId) {
      state.selectedOrigins = alreadySelected
        ? state.selectedOrigins.filter((origin) => origin.stamp !== selected.stamp)
        : [...state.selectedOrigins, selected];
      renderOriginCandidates({ ...(state.originPayload || {}), selected_origins: state.selectedOrigins });
      renderProjectCard();
      showMessage('Seleção mantida apenas nesta leitura. Abre o documento pelo inbox para guardar.', 'warning');
      return;
    }
    const button = els.originFlow.querySelector(`[data-origin-link="${Number(index)}"]`);
    if (button) button.disabled = true;
    const previousOrigins = [...state.selectedOrigins];
    const previousMatches = state.originLineMatches;
    const previousMatchByLine = state.originLineMatchByLine;
    const previousReferenceLabel = state.originLineReferenceLabel;
    const isPurchaseOrder = selected.document_type === 'purchase_order' || Number(selected.ndos || 0) === 102;
    if (isPurchaseOrder) {
      state.originLineMatches = [];
      state.originLineMatchByLine = new WeakMap();
      state.originLineReferenceLabel = '';
      renderLines(state.documentData?.lines || [], state.documentData?.currency || '');
    }
    setStatus(`${alreadySelected ? 'A desmarcar' : 'A selecionar'} ${selected.stage_label} nº ${selected.number} e a recalcular as referências das linhas...`);
    try {
      const payload = await fetchJson(`/api/document_ai/documents/${encodeURIComponent(state.currentDocumentId)}/origin`, alreadySelected ? {
        method: 'DELETE',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ stamp: selected.stamp }),
      } : {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ origin: selected, document: state.documentData || {} }),
      });
      state.draftVersion = String(payload.version || state.draftVersion || '');
      state.selectedOrigins = Array.isArray(payload.origins) ? payload.origins : (alreadySelected ? previousOrigins.filter((origin) => origin.stamp !== selected.stamp) : [...previousOrigins, payload.origin || selected]);
      renderOriginCandidates({ ...(state.originPayload || {}), selected_origins: state.selectedOrigins });
      await pruneLineBcAllocations();
      renderLines(state.documentData?.lines || [], state.documentData?.currency || '');
      renderProjectCard();
      const mappedLineCount = new Set(state.originLineMatches.map((match) => Number(match.document_line_index))).size;
      setStatus(isPurchaseOrder
        ? `${payload.message || 'Seleção de origem atualizada.'} ${mappedLineCount} linha(s) têm referências dos BCs selecionados.`
        : payload.message || 'Seleção de origem atualizada.');
      showMessage(payload.message || 'Seleção de origem atualizada.', 'success');
    } catch (error) {
      state.selectedOrigins = previousOrigins;
      state.originLineMatches = previousMatches;
      state.originLineMatchByLine = previousMatchByLine;
      state.originLineReferenceLabel = previousReferenceLabel;
      renderLines(state.documentData?.lines || [], state.documentData?.currency || '');
      if (button) button.disabled = false;
      setStatus(error.message || 'Não foi possível ligar a origem.', true);
      showMessage(error.message || 'Não foi possível ligar a origem.', 'error');
    }
  }

  function closeOriginDetailModal() {
    els.originDetailModal?.classList.remove('sz_is_open');
    els.originDetailModal?.setAttribute('aria-hidden', 'true');
  }

  async function openOriginDetail(index) {
    const candidate = state.originCandidates[Number(index)];
    if (!candidate || !state.currentDocumentId || !els.originDetailModal) return;
    state.consultedOriginStamp = candidate.stamp || '';
    renderOriginCandidates({ ...(state.originPayload || {}), selected_origins: state.selectedOrigins }, { skipLineMapping: true });
    const number = `n.º ${candidate.number || '--'}${candidate.year ? ` / ${candidate.year}` : ''}`;
    els.originDetailTitle.textContent = `${candidate.stage_label || 'Origem'} ${number}`;
    els.originDetailLoading.hidden = false;
    els.originDetailTable.hidden = true;
    els.originDetailEmpty.hidden = true;
    els.originDetailModal.classList.add('sz_is_open');
    els.originDetailModal.setAttribute('aria-hidden', 'false');
    try {
      const payload = await fetchJson(`/api/document_ai/documents/${encodeURIComponent(state.currentDocumentId)}/origins/${encodeURIComponent(candidate.stamp)}?view=${encodeURIComponent(state.view)}`);
      const rows = Array.isArray(payload.lines) ? payload.lines : [];
      els.originDetailHead.innerHTML = '<th>Artigo</th><th>Designação</th><th>Quantidade</th><th title="Preço unitário">PU</th><th title="Preço total">PT</th><th>IVA</th><th>Obra</th><th>Matrícula</th><th>Data</th>';
      els.originDetailBody.innerHTML = rows.map((line) => `<tr><td>${escapeHtml(line.article || '—')}</td><td>${escapeHtml(line.description || '—')}</td><td>${escapeHtml(formatNumber(line.quantity))}</td><td>${escapeHtml(formatMoney(line.unit_price, state.documentData?.currency))}</td><td>${escapeHtml(formatMoney(line.line_total, state.documentData?.currency))}</td><td>${escapeHtml(formatNumber(line.tax_rate, 2))}%</td><td>${escapeHtml(line.project || '—')}</td><td>${escapeHtml(line.registration || '—')}</td><td>${escapeHtml(formatDate(line.date))}</td></tr>`).join('');
      els.originDetailLoading.hidden = true;
      els.originDetailTable.hidden = !rows.length;
      els.originDetailEmpty.hidden = Boolean(rows.length);
    } catch (error) {
      els.originDetailLoading.hidden = true;
      els.originDetailEmpty.hidden = false;
      els.originDetailEmpty.textContent = error.message || 'Não foi possível consultar a origem no PHC.';
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
    if (els.resetBtn) els.resetBtn.disabled = true;
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
      if (els.resetBtn) els.resetBtn.disabled = !state.file;
    }
  }

  function closeSupplierModal() {
    window.clearTimeout(state.supplierSearchTimer);
    state.supplierSearchToken += 1;
    els.supplierModal.classList.remove('sz_is_open');
    els.supplierModal.setAttribute('aria-hidden', 'true');
  }

  function renderProjectCard() {
    const project = state.selectedProject || {};
    const selected = Boolean(project.ccusto);
    const selectedOriginWorks = [...new Set(state.selectedOrigins.map((origin) => String(origin.ccusto || '').trim()).filter(Boolean))];
    const hasWorkConflict = selectedOriginWorks.length > 1;
    els.projectName.textContent = selected ? project.ccusto : '-';
    const projectDetails = [project.machine, project.location].filter(Boolean).join(' · ');
    els.projectMeta.textContent = hasWorkConflict
      ? `Atenção: os BCs selecionados pertencem a ${selectedOriginWorks.length} obras (${selectedOriginWorks.join(', ')})`
      : selected
        ? [project.suggested_by_document ? `Sugerida por ${project.suggested_by_document}` : '', projectDetails].filter(Boolean).join(' · ') || 'Filtro de obra ativo'
        : '-';
    els.projectHint.innerHTML = hasWorkConflict
      ? '<i class="fa-solid fa-triangle-exclamation"></i> BCs de obras diferentes'
      : selected
      ? '<i class="fa-solid fa-pen"></i> Alterar obra'
      : '<i class="fa-solid fa-magnifying-glass"></i> Pesquisar obra';
    els.projectHint.hidden = true;
    els.projectClear.hidden = !selected;
    els.projectCard.classList.toggle('is-selected', selected);
    els.projectCard.classList.toggle('is-conflict', hasWorkConflict);
    if (state.documentData) renderGedDestination();
  }

  function projectSuggestedByOrigin(payload = {}) {
    const linkedOrigins = Array.isArray(payload.selected_origins) ? payload.selected_origins : [];
    const linkedWorks = [...new Set(linkedOrigins.map((origin) => String(origin.ccusto || '').trim()).filter(Boolean))];
    if (linkedWorks.length > 1) return null;
    const linkedOrigin = linkedOrigins.find((origin) => String(origin.ccusto || '').trim()) || null;
    const origin = linkedOrigin || payload.suggested_origin || null;
    const ccusto = String(origin?.ccusto || '').trim();
    if (!ccusto) return null;
    const documentLabel = `${origin.stage_label || 'Documento'} ${origin.number || ''}`.trim();
    return {
      ccusto,
      machine: origin.project_machine || '',
      location: origin.project_location || '',
      suggested_by_origin_stamp: origin.stamp || '',
      suggested_by_document: documentLabel,
    };
  }

  async function clearSelectedOriginsForProjectChange(nextCcusto) {
    const cleanCcusto = String(nextCcusto || '').trim();
    const hasDifferentOrigin = state.selectedOrigins.some((origin) => String(origin.ccusto || '').trim() !== cleanCcusto);
    if (!hasDifferentOrigin) return true;
    if (state.currentDocumentId) {
      try {
        const payload = await fetchJson(`/api/document_ai/documents/${encodeURIComponent(state.currentDocumentId)}/origin`, {
          method: 'DELETE',
        });
        state.draftVersion = String(payload.version || state.draftVersion || '');
      } catch (error) {
        setStatus(error.message || 'Não foi possível desmarcar a origem anterior.', true);
        showMessage(error.message || 'Não foi possível desmarcar a origem anterior.', 'error');
        return false;
      }
    }
    state.selectedOrigins = [];
    await pruneLineBcAllocations();
    return true;
  }

  function closeProjectModal() {
    state.projectTargetLineIndex = null;
    els.projectModal.classList.remove('sz_is_open');
    els.projectModal.setAttribute('aria-hidden', 'true');
  }

  async function saveAdjustedLines(successMessage = 'Linha atualizada.') {
    if (!state.currentDocumentId || !state.documentData) {
      setStatus(successMessage);
      return true;
    }
    try {
      const saved = await scheduleAnalysisSave({ immediate: true });
      if (!saved) return false;
      setStatus(successMessage);
      return true;
    } catch (error) {
      setStatus(error.message || 'Não foi possível guardar a linha.', true);
      showMessage(error.message || 'Não foi possível guardar a linha.', 'error');
      return false;
    }
  }

  function renderProjectCandidates(items) {
    state.projectCandidates = Array.isArray(items) ? items : [];
    if (!state.projectCandidates.length) {
      els.projectList.innerHTML = '<div class="docai-empty-state">Não foram encontradas obras com esta pesquisa.</div>';
      return;
    }
    els.projectList.innerHTML = state.projectCandidates.map((project, index) => `
      <button type="button" class="docai-supplier-match-option" data-project-index="${index}">
        <span class="docai-supplier-match-main">
          <strong>${escapeHtml(project.ccusto || '--')}</strong>
          <span>${escapeHtml([project.machine, project.location].filter(Boolean).join(' · ') || 'Sem descrição adicional')}</span>
        </span>
        <span class="docai-supplier-match-score">${escapeHtml(project.document_count || 0)} documento(s)</span>
      </button>
    `).join('');
  }

  async function searchProjectCandidates() {
    if (!state.documentData?.customer) return;
    els.projectSearchBtn.disabled = true;
    els.projectList.innerHTML = '<div class="docai-empty-state">A procurar obras no PHC...</div>';
    try {
      const payload = await fetchJson('/api/document_ai/projects/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          customer: state.documentData.customer || {},
          query: els.projectSearch.value.trim(),
          limit: 30,
        }),
      });
      renderProjectCandidates(payload.items || []);
      els.projectContext.textContent = `Obras de ${state.documentData.customer?.name || 'empresa cliente'} · ${payload.phc_database || 'PHC'}`;
    } catch (error) {
      els.projectList.innerHTML = `<div class="docai-empty-state">${escapeHtml(error.message || 'Erro ao pesquisar obras.')}</div>`;
    } finally {
      els.projectSearchBtn.disabled = false;
    }
  }

  function openProjectModal() {
    if (!state.documentData?.customer?.feid && !state.documentData?.customer?.name) {
      showMessage('É necessário identificar primeiro a empresa cliente.', 'error');
      return;
    }
    els.projectSearch.value = state.selectedProject?.ccusto || '';
    els.projectContext.textContent = `Obras de ${state.documentData.customer?.name || 'empresa cliente'}`;
    els.projectModal.classList.add('sz_is_open');
    els.projectModal.setAttribute('aria-hidden', 'false');
    window.setTimeout(() => {
      els.projectSearch.focus();
      searchProjectCandidates();
    }, 50);
  }

  function openLineProjectModal(lineIndex) {
    const line = state.documentData?.lines?.[Number(lineIndex)];
    if (!line) return;
    state.projectTargetLineIndex = Number(lineIndex);
    els.projectSearch.value = String(line.ccusto || line.project_ccusto || '').trim();
    els.projectContext.textContent = `Obras de ${state.documentData.customer?.name || 'entidade cliente'}`;
    els.projectModal.classList.add('sz_is_open');
    els.projectModal.setAttribute('aria-hidden', 'false');
    window.setTimeout(() => {
      els.projectSearch.focus();
      searchProjectCandidates();
    }, 50);
  }

  async function selectProject(index) {
    const selected = state.projectCandidates[Number(index)];
    if (!selected || !state.documentData) return;
    if (state.projectTargetLineIndex !== null) {
      const line = state.documentData.lines?.[state.projectTargetLineIndex];
      if (!line) return;
      line.ccusto = selected.ccusto || '';
      line.project_ccusto = selected.ccusto || '';
      line.project_machine = selected.machine || '';
      line.project_location = selected.location || '';
      markLineManualFields(line, 'ccusto', 'project_ccusto', 'project_machine', 'project_location');
      state.projectTargetLineIndex = null;
      closeProjectModal();
      renderLines(state.documentData.lines || [], state.documentData.currency || '');
      await saveAdjustedLines(`Obra ${selected.ccusto} guardada na linha.`);
      return;
    }
    const changed = String(state.selectedProject?.ccusto || '').trim() !== String(selected.ccusto || '').trim();
    if (changed && !await clearSelectedOriginsForProjectChange(selected.ccusto)) return;
    state.projectSuggestionDismissed = true;
    state.selectedProject = { ...selected };
    state.documentData.origin_project = { ...selected };
    state.documentData.origin_project_manually_selected = true;
    state.documentData.origin_project_manually_cleared = false;
    renderProjectCard();
    closeProjectModal();
    setStatus(`Filtro de obra ${selected.ccusto} aplicado às origens.`);
    await scheduleAnalysisSave({ immediate: true });
    loadOriginCandidates(state.documentData);
  }

  function closeArticleModal() {
    state.articleTargetLineIndex = null;
    els.articleModal.classList.remove('sz_is_open');
    els.articleModal.setAttribute('aria-hidden', 'true');
  }

  function renderArticleCandidates(items) {
    state.articleCandidates = Array.isArray(items) ? items : [];
    if (!state.articleCandidates.length) {
      els.articleList.innerHTML = '<div class="docai-empty-state">Nenhum artigo encontrado.</div>';
      return;
    }
    els.articleList.innerHTML = state.articleCandidates.map((article, index) => `
      <button type="button" class="docai-supplier-match-option" data-article-index="${index}">
        <span class="docai-supplier-match-main">
          <strong>${escapeHtml(article.ref || '--')}</strong>
          <span>${escapeHtml(article.design || 'Sem designação')}</span>
        </span>
        <span class="docai-supplier-match-score">${escapeHtml([article.family, article.unit].filter(Boolean).join(' · '))}</span>
      </button>
    `).join('');
  }

  async function searchArticleCandidates() {
    if (!state.documentData?.customer) return;
    els.articleSearchBtn.disabled = true;
    els.articleList.innerHTML = '<div class="docai-empty-state">A pesquisar artigos PHC...</div>';
    try {
      const payload = await fetchJson('/api/document_ai/articles/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          customer: state.documentData.customer || {},
          query: els.articleSearch.value.trim(),
          limit: 30,
        }),
      });
      renderArticleCandidates(payload.items || []);
      els.articleContext.textContent = `Artigos de ${state.documentData.customer?.name || 'entidade cliente'} · ${payload.phc_database || 'PHC'}`;
    } catch (error) {
      els.articleList.innerHTML = `<div class="docai-empty-state">${escapeHtml(error.message || 'Erreur de recherche.')}</div>`;
    } finally {
      els.articleSearchBtn.disabled = false;
    }
  }

  function openArticleModal(lineIndex) {
    const line = state.documentData?.lines?.[Number(lineIndex)];
    if (!line) return;
    if (!state.documentData?.customer?.feid && !state.documentData?.customer?.name) {
      showMessage('Identifica primeiro a entidade cliente.', 'error');
      return;
    }
    state.articleTargetLineIndex = Number(lineIndex);
    els.articleSearch.value = line.ref || line.description || '';
    els.articleModal.classList.add('sz_is_open');
    els.articleModal.setAttribute('aria-hidden', 'false');
    window.setTimeout(() => {
      els.articleSearch.focus();
      searchArticleCandidates();
    }, 50);
  }

  async function selectArticle(index) {
    const article = state.articleCandidates[Number(index)];
    const line = state.documentData?.lines?.[state.articleTargetLineIndex];
    if (!article || !line) return;
    const groupCode = normalizeLineGroupCode(line.article_group_code);
    const groupedLines = groupCode
      ? (state.documentData?.lines || []).filter((candidate) => {
          const candidateCode = normalizeLineGroupCode(candidate?.article_group_code);
          return candidateCode && candidateCode.slice(1) === groupCode.slice(1);
        })
      : [line];
    groupedLines.forEach((candidate) => {
      candidate.ref = article.ref || '';
      candidate.article_ref = article.ref || '';
      candidate.article_family = article.family || candidate.article_family || '';
      if (article.unit) candidate.unit = article.unit;
      markLineManualFields(candidate, 'ref', 'article_ref', 'article_family', 'unit');
    });
    state.articleTargetLineIndex = null;
    closeArticleModal();
    renderLines(state.documentData.lines || [], state.documentData.currency || '');
    await saveAdjustedLines(groupCode
      ? `Artigo ${article.ref} guardado no grupo ${groupCode.slice(1)}.`
      : `Artigo ${article.ref} guardado na linha.`);
  }

  function closeVehicleModal() {
    state.vehicleTargetLineIndex = null;
    els.vehicleModal.classList.remove('sz_is_open');
    els.vehicleModal.setAttribute('aria-hidden', 'true');
  }

  function renderVehicleCandidates(items) {
    state.vehicleCandidates = Array.isArray(items) ? items : [];
    if (!state.vehicleCandidates.length) {
      els.vehicleList.innerHTML = '<div class="docai-empty-state">Nenhuma viatura encontrada.</div>';
      return;
    }
    els.vehicleList.innerHTML = state.vehicleCandidates.map((vehicle, index) => `
      <button type="button" class="docai-supplier-match-option" data-vehicle-index="${index}">
        <span class="docai-supplier-match-main">
          <strong>${escapeHtml(vehicle.registration || '--')}</strong>
          <span>${escapeHtml([vehicle.brand, vehicle.model].filter(Boolean).join(' · ') || 'Sem descrição')}</span>
        </span>
        <span class="docai-supplier-match-score">${escapeHtml(vehicle.fleet_number || '')}</span>
      </button>
    `).join('');
  }

  async function searchVehicleCandidates() {
    if (!state.documentData?.customer) return;
    els.vehicleSearchBtn.disabled = true;
    els.vehicleList.innerHTML = '<div class="docai-empty-state">A pesquisar viaturas PHC...</div>';
    try {
      const payload = await fetchJson('/api/document_ai/vehicles/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          customer: state.documentData.customer || {},
          query: els.vehicleSearch.value.trim(),
          limit: 30,
        }),
      });
      renderVehicleCandidates(payload.items || []);
      els.vehicleContext.textContent = `Viaturas de ${state.documentData.customer?.name || 'entidade cliente'} · ${payload.phc_database || 'PHC'}`;
    } catch (error) {
      els.vehicleList.innerHTML = `<div class="docai-empty-state">${escapeHtml(error.message || 'Erro ao pesquisar viaturas.')}</div>`;
    } finally {
      els.vehicleSearchBtn.disabled = false;
    }
  }

  function openVehicleModal(lineIndex) {
    const line = state.documentData?.lines?.[Number(lineIndex)];
    if (!line) return;
    if (!state.documentData?.customer?.feid && !state.documentData?.customer?.name) {
      showMessage('Identifica primeiro a entidade cliente.', 'error');
      return;
    }
    state.vehicleTargetLineIndex = Number(lineIndex);
    els.vehicleSearch.value = String(line.registration || line.matricula || '').trim();
    els.vehicleRemove.hidden = !els.vehicleSearch.value;
    els.vehicleModal.classList.add('sz_is_open');
    els.vehicleModal.setAttribute('aria-hidden', 'false');
    window.setTimeout(() => {
      els.vehicleSearch.focus();
      searchVehicleCandidates();
    }, 50);
  }

  async function selectVehicle(index) {
    const vehicle = state.vehicleCandidates[Number(index)];
    const line = state.documentData?.lines?.[state.vehicleTargetLineIndex];
    if (!vehicle || !line) return;
    line.registration = vehicle.registration || '';
    line.matricula = vehicle.registration || '';
    line.vehicle_stamp = vehicle.vehicle_stamp || '';
    line.vehicle_source = 'V_ALL_VA';
    markLineManualFields(line, 'registration', 'matricula', 'vehicle_stamp', 'vehicle_source');
    closeVehicleModal();
    renderLines(state.documentData.lines || [], state.documentData.currency || '');
    await saveAdjustedLines(`Viatura ${vehicle.registration} guardada na linha.`);
  }

  async function removeVehicle() {
    const line = state.documentData?.lines?.[state.vehicleTargetLineIndex];
    if (!line) return;
    line.registration = '';
    line.matricula = '';
    line.vehicle_stamp = '';
    line.vehicle_source = '';
    markLineManualFields(line, 'registration', 'matricula', 'vehicle_stamp', 'vehicle_source');
    closeVehicleModal();
    renderLines(state.documentData.lines || [], state.documentData.currency || '');
    await saveAdjustedLines('Associação à viatura removida.');
  }

  function closeBcModal() {
    state.bcTargetLineIndex = null;
    state.bcSelectedStamps = new Set();
    els.bcModal.classList.remove('sz_is_open');
    els.bcModal.setAttribute('aria-hidden', 'true');
  }

  function renderBcAssignments() {
    const origins = associatedBcOrigins();
    if (!origins.length) {
      els.bcList.innerHTML = '<div class="docai-empty-state">Associa primeiro uma Nota de Encomenda no bloco Origem.</div>';
      els.bcSave.disabled = true;
      return;
    }
    els.bcSave.disabled = false;
    els.bcList.innerHTML = origins.map((origin) => {
      const stamp = String(origin.stamp || '');
      const checked = state.bcSelectedStamps.has(stamp);
      return `<label class="docai-bc-assignment-option">
        <input type="checkbox" data-bc-origin-stamp="${escapeHtml(stamp)}" ${checked ? 'checked' : ''}>
        <span>
          <strong>${escapeHtml(formatBcLabel(origin))}</strong>
          <small>${escapeHtml([formatDate(origin.date), origin.ccusto].filter(Boolean).join(' · '))}</small>
        </span>
      </label>`;
    }).join('');
  }

  function openBcModal(lineIndex) {
    const line = state.documentData?.lines?.[Number(lineIndex)];
    if (!line) return;
    state.bcTargetLineIndex = Number(lineIndex);
    state.bcSelectedStamps = new Set((line.bc_allocations || []).map((allocation) => String(allocation.origin_stamp || '')).filter(Boolean));
    renderBcAssignments();
    els.bcModal.classList.add('sz_is_open');
    els.bcModal.setAttribute('aria-hidden', 'false');
  }

  function relevantBcLines(origin, documentLine, documentLineIndex) {
    const officialLines = Array.isArray(origin.lines) ? origin.lines : [];
    const matches = (Array.isArray(origin.line_matches) ? origin.line_matches : [])
      .filter((match) => Number(match.document_line_index) === Number(documentLineIndex));
    const matchedIndexes = new Set(matches.map((match) => Number(match.origin_line_index)));
    const exactRef = String(documentLine.ref || '').trim().toUpperCase();
    let selected = officialLines.filter((originLine, index) => matchedIndexes.has(index));
    if (exactRef) {
      const sameArticleLines = officialLines.filter((originLine) => String(originLine.ref || '').trim().toUpperCase() === exactRef);
      if (sameArticleLines.length) selected = sameArticleLines;
    }
    if (!selected.length && matches.length) {
      selected = matches.map((match) => ({
        line_stamp: match.origin_line_stamp || '',
        line_order: match.origin_line_order || 0,
        ref: match.origin_ref || '',
        description: match.origin_description || '',
        qty: match.origin_quantity || 0,
        unit_price: match.origin_unit_price || 0,
        line_total: match.origin_total || 0,
      }));
    }
    return selected;
  }

  async function saveBcAssignments() {
    const lineIndex = state.bcTargetLineIndex;
    const line = state.documentData?.lines?.[lineIndex];
    if (!line) return;
    const origins = associatedBcOrigins().filter((origin) => state.bcSelectedStamps.has(String(origin.stamp || '')));
    const allocations = [];
    origins.forEach((origin) => {
      const relevantLines = relevantBcLines(origin, line, lineIndex);
      if (!relevantLines.length) {
        allocations.push({
          origin_stamp: origin.stamp || '', origin_number: origin.number || '', origin_year: origin.year || null,
          origin_line_stamp: '', origin_line_order: 0, quantity: 0, unit_price: 0, total: 0,
        });
        return;
      }
      relevantLines.forEach((originLine, originLineIndex) => allocations.push({
        origin_stamp: origin.stamp || '',
        origin_number: origin.number || '',
        origin_year: origin.year || null,
        origin_line_stamp: originLine.line_stamp || '',
        origin_line_order: Number(originLine.line_order || originLineIndex + 1),
        article_ref: originLine.ref || '',
        quantity: Number(originLine.pending_qty ?? originLine.qty ?? 0),
        unit_price: Number(originLine.unit_price || 0),
        total: Number(originLine.line_total || 0),
      }));
    });
    line.bc_allocations = allocations;
    markLineManualFields(line, 'bc_allocations');
    if (allocations.length < 2) state.expandedBcLines.delete(lineIndex);
    closeBcModal();
    renderLines(state.documentData.lines || [], state.documentData.currency || '');
    await saveAdjustedLines(allocations.length ? 'Distribuição por Nota de Encomenda guardada.' : 'Associação à Nota de Encomenda removida.');
  }

  async function pruneLineBcAllocations() {
    const allowed = new Set(associatedBcOrigins().map((origin) => String(origin.stamp || '')));
    let changed = false;
    (state.documentData?.lines || []).forEach((line) => {
      if (!Array.isArray(line.bc_allocations)) return;
      const filtered = line.bc_allocations.filter((allocation) => allowed.has(String(allocation.origin_stamp || '')));
      if (filtered.length !== line.bc_allocations.length) {
        line.bc_allocations = filtered;
        changed = true;
      }
    });
    if (changed) await saveAdjustedLines('Distribuições por Nota de Encomenda atualizadas.');
  }

  async function clearProject(event) {
    event?.stopPropagation();
    state.projectSuggestionDismissed = true;
    state.selectedProject = null;
    if (state.documentData) delete state.documentData.origin_project;
    if (state.documentData) {
      state.documentData.origin_project_manually_selected = false;
      state.documentData.origin_project_manually_cleared = true;
    }
    renderProjectCard();
    setStatus('Filtro de obra removido.');
    await scheduleAnalysisSave({ immediate: true });
    if (state.documentData) loadOriginCandidates(state.documentData);
  }

  function renderSupplierCandidates(items) {
    const isCorrespondence = ['mail', 'bank_statement'].includes(state.documentData?.document_type);
    state.supplierCandidates = Array.isArray(items) ? items : [];
    if (!state.supplierCandidates.length) {
      els.supplierModalList.innerHTML = `<div class="docai-empty-state">Não foram encontrados ${isCorrespondence ? 'clientes ou fornecedores' : 'fornecedores'} semelhantes nesta entidade.</div>`;
      return;
    }
    els.supplierModalList.innerHTML = state.supplierCandidates.map((item, index) => {
      const score = Math.round(Math.max(0, Math.min(1, Number(item.score || 0))) * 100);
      const taxLabel = String(item.tax_field || 'nif').toUpperCase();
      const matchLabel = item.matched_by === 'tax_id' ? `${taxLabel} coincidente` : 'Nome semelhante';
      const partyLabel = item.party_role === 'customer' ? 'Cliente' : 'Fornecedor';
      const location = [item.address, item.postal_code, item.city].filter(Boolean).join(' · ');
      return `
        <button type="button" class="docai-supplier-match-option" data-supplier-index="${index}">
          <span class="docai-supplier-match-main">
            <strong>${escapeHtml(item.name || '--')}</strong>
            <span>Nº ${escapeHtml(phcPartyNumber(item.no, item.estab) || '--')} · ${escapeHtml(taxLabel)} ${escapeHtml(item.tax_id || '--')}</span>
            ${location ? `<span>${escapeHtml(location)}</span>` : ''}
          </span>
          <span class="docai-supplier-match-score">${isCorrespondence ? `${escapeHtml(partyLabel)} · ` : ''}${escapeHtml(matchLabel)} · ${score}%</span>
        </button>
      `;
    }).join('');
  }

  function openSupplierModal() {
    const isCorrespondence = ['mail', 'bank_statement'].includes(state.documentData?.document_type);
    const isAdvertising = state.documentData?.document_type === 'advertising';
    const feid = Number(state.matching?.supplier_query?.feid || state.documentData?.customer?.feid || 0);
    if (!feid) {
      showMessage('Não foi possível identificar a entidade na tabela FE.', 'error');
      return;
    }
    const customerName = state.documentData?.customer?.name || `FE ${feid}`;
    const supplier = state.documentData?.supplier || {};
    els.supplierModalTitle.textContent = isCorrespondence ? 'Escolher cliente ou fornecedor' : 'Escolher fornecedor';
    els.supplierModalContext.textContent = `${isCorrespondence ? 'Clientes e fornecedores' : 'Fornecedores'} de ${customerName} · FEID ${feid}`;
    els.supplierModalSearch.value = supplier.llm_name || supplier.name || supplier.llm_tax_id || supplier.tax_id || '';
    els.supplierManualBtn.hidden = !isCorrespondence && !isAdvertising;
    els.supplierManualBtn.innerHTML = isAdvertising
      ? '<i class="fa-solid fa-ban"></i><span>s/Fornecedor</span>'
      : '<i class="fa-solid fa-pen-to-square"></i><span>Usar nome escrito</span>';
    renderSupplierCandidates(state.matching?.supplier_candidates || []);
    els.supplierModal.classList.add('sz_is_open');
    els.supplierModal.setAttribute('aria-hidden', 'false');
    window.setTimeout(() => els.supplierModalSearch.focus(), 50);
  }

  async function searchSupplierCandidates() {
    const isCorrespondence = ['mail', 'bank_statement'].includes(state.documentData?.document_type);
    const feid = Number(state.matching?.supplier_query?.feid || state.documentData?.customer?.feid || 0);
    const query = els.supplierModalSearch.value.trim();
    if (!feid || query.length < 2) {
      showMessage('Indica pelo menos dois caracteres para pesquisar.', 'error');
      return;
    }
    els.supplierModalSearchBtn.disabled = true;
    els.supplierModalList.innerHTML = `<div class="docai-empty-state">A procurar ${isCorrespondence ? 'clientes e fornecedores' : 'fornecedores'} semelhantes...</div>`;
    try {
      const searchToken = ++state.supplierSearchToken;
      const params = new URLSearchParams({ q: query, feid: String(feid), limit: '12' });
      const items = await fetchJson(`/api/document_ai/${isCorrespondence ? 'external-parties' : 'suppliers'}/search?${params.toString()}`);
      if (searchToken !== state.supplierSearchToken) return;
      renderSupplierCandidates(items);
    } catch (error) {
      els.supplierModalList.innerHTML = `<div class="docai-empty-state">${escapeHtml(error.message || 'Erro na pesquisa.')}</div>`;
    } finally {
      els.supplierModalSearchBtn.disabled = false;
    }
  }

  function useManualSenderName() {
    if (state.documentData?.document_type === 'advertising') {
      state.documentData.supplier_explicitly_absent = true;
      state.documentData.supplier = {
        supplier_no: null,
        customer_no: null,
        name: 's/Fornecedor',
        explicitly_absent: true,
        manually_selected: true,
        matched_by: 'explicit_no_supplier',
      };
      state.matching.supplier_matched = true;
      state.matching.supplier_needs_selection = false;
      renderSupplierCard(state.documentData.supplier, state.matching);
      closeSupplierModal();
      setStatus('Ausência de fornecedor confirmada para Publicidade.');
      showMessage('Publicidade definida sem fornecedor.', 'success');
      updateSubmitPhcButton();
      scheduleAnalysisSave({ immediate: true });
      return;
    }
    const name = els.supplierModalSearch.value.trim();
    if (!['mail', 'bank_statement'].includes(state.documentData?.document_type) || name.length < 2) {
      showMessage('Escreve pelo menos dois caracteres para o nome do remetente.', 'error');
      return;
    }
    const current = state.documentData.supplier || {};
    state.documentData.external_party_role = 'unknown';
    state.documentData.supplier = {
      ...current,
      name,
      supplier_no: null,
      customer_no: null,
      manually_named: true,
      manually_selected: true,
      matched_by: 'manual_name',
      match_score: 0,
    };
    state.matching.supplier_matched = false;
    state.matching.supplier_needs_selection = false;
    renderSupplierCard(state.documentData.supplier, state.matching);
    renderGedDestination();
    closeSupplierModal();
    setStatus(`Remetente “${name}” introduzido manualmente.`);
    showMessage('Nome do remetente guardado neste ecrã.', 'success');
    scheduleAnalysisSave({ immediate: true });
  }

  function selectSupplier(index) {
    const selected = state.supplierCandidates[index];
    if (!selected || !state.documentData) return;
    const current = state.documentData.supplier || {};
    const isCorrespondence = ['mail', 'bank_statement'].includes(state.documentData.document_type);
    const isCustomer = isCorrespondence && selected.party_role === 'customer';
    state.documentData.supplier_explicitly_absent = false;
    if (isCorrespondence) state.documentData.external_party_role = isCustomer ? 'customer' : 'supplier';
    state.documentData.supplier = {
      ...current,
      supplier_no: null,
      customer_no: null,
      ...(isCustomer ? { customer_no: selected.no } : { supplier_no: selected.no }),
      estab: Number(selected.estab || 0),
      name: selected.name || current.name || '',
      short_name: selected.short_name || '',
      tax_id: selected.tax_id || current.tax_id || '',
      address: selected.address || current.address || '',
      city: selected.city || current.city || '',
      postal_code: selected.postal_code || current.postal_code || '',
      feid: selected.feid || state.documentData.customer?.feid || null,
      match_score: selected.score || 0,
      matched_by: selected.matched_by || 'manual',
      manually_selected: true,
    };
    state.matching.supplier_matched = true;
    state.matching.supplier_needs_selection = false;
    renderSupplierCard(state.documentData.supplier, state.matching);
    renderGedDestination();
    closeSupplierModal();
    setStatus(`${isCustomer ? 'Cliente' : 'Fornecedor'} ${selected.name} (#${phcPartyNumber(selected.no, selected.estab)}) selecionado.`);
    showMessage(`${isCustomer ? 'Cliente' : 'Fornecedor'} selecionado.`, 'success');
    scheduleAnalysisSave({ immediate: true });
    if (!['mail', 'bank_statement'].includes(state.documentData.document_type)) loadOriginCandidates(state.documentData);
  }

  function renderResult(payload) {
    const documentData = applyManualOverrides(payload.document || {}, state.pendingManualOverrides);
    payload.document = documentData;
    state.pendingManualOverrides = null;
    const serverFingerprint = draftFingerprint(documentData);
    const customer = documentData.customer || {};
    const supplier = documentData.supplier || {};
    const totals = documentData.totals || {};
    const currency = documentData.currency || '';
    const isMail = documentData.document_type === 'mail';
    const isCorrespondence = ['mail', 'bank_statement'].includes(documentData.document_type);
    const isReception = state.view === 'home';

    state.documentData = documentData;
    state.draftVersion = String(payload.version || payload.updated_at || '');
    state.draftRevision = 0;
    state.draftSavedRevision = 0;
    state.draftLastFingerprint = serverFingerprint;
    state.draftError = false;
    state.draftConflict = false;
    if (els.saveRetryBtn) els.saveRetryBtn.hidden = true;
    state.workflow = payload.workflow || {};
    state.controlOk = Boolean(payload.workflow?.control_ok);
    state.integratedPhc = payload.processing_status === 'provisional_invoice'
      || Boolean(payload.phc_integration?.fostamp || payload.phc_integration?.crstamp);
    state.integrationResult = state.integratedPhc ? (payload.phc_integration || {}) : null;
    state.gedFolderManuallySelected = Boolean(documentData.customer?.ged_folder_manually_selected);
    state.submittingPhc = false;
    if (state.selectedProject?.ccusto) state.documentData.origin_project = { ...state.selectedProject };
    state.matching = payload.matching || {};
    state.supplierCandidates = state.matching.supplier_candidates || [];
    const duplicateDetection = payload.duplicate_detection || {};
    const duplicateOverride = payload.duplicate_override || {};
    const duplicateMatches = Array.isArray(duplicateDetection.duplicates) ? duplicateDetection.duplicates : [];
    const duplicateIds = duplicateMatches.map((item) => String(item.document_id || '')).sort().join('|');
    const overrideIds = (duplicateOverride.document_ids || []).map((value) => String(value || '')).sort().join('|');
    state.duplicateMatches = duplicateMatches;
    if (duplicateIds && duplicateIds !== overrideIds && state.duplicateModalShownFor !== `${state.currentDocumentId}:${duplicateIds}`) {
      state.duplicateModalShownFor = `${state.currentDocumentId}:${duplicateIds}`;
      window.setTimeout(() => openDuplicateModal(duplicateMatches), 0);
    }
    renderDocumentBatch(documentData.document_batch || {});
    if (isCorrespondence) els.batchAlert.hidden = true;
    renderCustomerCard(customer, state.matching);
    renderSupplierCard(supplier, state.matching);
    renderProjectCard();
    els.projectCard.hidden = isCorrespondence;
    els.originSection.hidden = isCorrespondence || isReception;
    els.linesSection.hidden = isCorrespondence || isReception;
    els.notesSection.hidden = true;
    els.persistenceNote.textContent = isMail
      ? 'O correio foi analisado apenas neste ecrã e não foi adicionado ao inbox.'
      : (documentData.document_type === 'bank_statement'
        ? 'O extrato fica no inbox e pode ser integrado como correspondência RB no PHC.'
        : 'O PDF e a leitura ficam guardados no inbox.');
    state.correspondenceReference = null;
    state.correspondenceYear = new Date().getFullYear();
    renderDocumentCard();
    renderClassificationCard();
    els.legalBadge.hidden = !(isMail && documentData.mail_category === 'legal');
    renderGedDestination();
    loadCorrespondenceReference();

    renderLines(documentData.lines, currency);
    renderTaxes(documentData.taxes, currency);
    els.netTotal.textContent = formatOptionalMoney(totals.net_total, currency);
    els.taxTotal.textContent = formatOptionalMoney(totals.tax_total, currency);
    els.grossTotal.textContent = formatOptionalMoney(totals.gross_total, currency);
    renderModeCard();

    const notes = Array.isArray(documentData.notes) ? documentData.notes.filter(Boolean) : [];
    els.notesSection.hidden = true;
    els.notes.innerHTML = notes.map((note) => `<li>${escapeHtml(note)}</li>`).join('');

    els.resultMeta.textContent = '';
    els.resultMeta.hidden = true;
    els.empty.hidden = true;
    els.loading.hidden = true;
    els.results.hidden = false;
    if (isCorrespondence || isReception) {
      state.originSearchToken += 1;
      state.originPayload = null;
      state.originCandidates = [];
      state.selectedOrigins = [];
    } else if (!state.readOnly) {
      loadOriginCandidates(documentData);
    }
    if (state.currentDocumentId && draftFingerprint() !== serverFingerprint) scheduleAnalysisSave();
    applyReadOnlyState();
  }

  function clearSuggestionsForForcedRead() {
    state.originSearchToken += 1;
    state.documentData = null;
    state.matching = {};
    state.supplierCandidates = [];
    state.originPayload = null;
    state.originCandidates = [];
    state.selectedOrigins = [];
    state.selectedProject = null;
    state.projectCandidates = [];
    state.projectSuggestionDismissed = false;
    state.deliveryNoteGroups = [];
    state.virtualDeliveryNotesActive = false;
    state.originLineMatches = [];
    state.originLineReferenceLabel = '';
    state.originLineMatchByLine = new WeakMap();
    state.selectedSplitLines = new Set();
    state.correspondenceLookupToken += 1;
    state.correspondenceReference = null;
    state.correspondenceYear = null;
    els.splitLineBtn.hidden = true;
    els.splitLineBtn.disabled = true;
    els.originFlow.innerHTML = '';
    els.originFlow.hidden = true;
    els.originLoading.hidden = false;
    els.originSource.hidden = true;
    closeProjectModal();
    closeSupplierModal();
    renderProjectCard();
    renderClassificationCard();
  }

  async function extractDocument(options = {}) {
    if (!state.file || state.loading) return;
    const hadPreviousResult = Boolean(state.documentData && !els.results.hidden);
    if (options.force) state.pendingManualOverrides = captureManualOverrides();
    state.loading = true;
    els.runBtn.disabled = true;
    if (els.deleteBtn) els.deleteBtn.disabled = true;
    if (els.resetBtn) els.resetBtn.disabled = true;
    els.empty.hidden = true;
    els.results.hidden = !hadPreviousResult;
    els.loading.hidden = false;
    els.resultMeta.textContent = options.force
      ? 'A efetuar uma nova leitura...'
      : 'A procurar uma leitura guardada no inbox...';
    setStatus(options.force
      ? 'A efetuar uma nova leitura do documento...'
      : 'A verificar os dados guardados...');

    const formData = new FormData();
    formData.append('file', state.file);
    formData.append('document_id', state.currentDocumentId || '');
    formData.append('force', options.force ? '1' : '0');
    formData.append('view', state.view);
    try {
      const payload = await fetchJson('/api/document_ai/extract', { method: 'POST', body: formData });
      if (options.force) clearSuggestionsForForcedRead();
      if (payload.document_id) {
        state.currentDocumentId = payload.document_id;
        window.history.replaceState({}, '', extractUrl(payload.document_id));
      }
      renderResult(payload);
      const batch = payload.document?.document_batch || {};
      if (payload.not_saved_to_inbox) {
        setStatus('Correio identificado. O PDF não foi adicionado ao inbox.');
        showMessage('Correio identificado sem criar registo no inbox.', 'success');
      } else if (batch.contains_multiple_documents) {
        setStatus(batch.message || 'Foram encontrados vários documentos no PDF.');
        showMessage(`${batch.document_count} documentos encontrados.`, 'warning');
      } else if (payload.cached) {
        setStatus('Leitura guardada carregada do inbox.');
        showMessage('Foi reutilizada a leitura guardada.', 'success');
      } else {
        setStatus('Leitura concluída.');
        showMessage(payload.inbox_created ? 'Documento lido e adicionado ao inbox.' : 'Documento lido com sucesso.', 'success');
      }
    } catch (error) {
      console.error(error);
      els.loading.hidden = true;
      els.empty.hidden = hadPreviousResult;
      els.results.hidden = !hadPreviousResult;
      els.empty.querySelector('strong').textContent = 'Não foi possível ler o documento';
      els.empty.querySelector('span').textContent = error.message || 'A leitura não devolveu uma resposta utilizável.';
      els.resultMeta.textContent = 'Erro na leitura do documento.';
      setStatus(error.message || 'Falha na leitura.', true);
      showMessage(error.message || 'Falha na leitura do documento.', 'error');
    } finally {
      state.loading = false;
      els.runBtn.disabled = !state.file;
      if (els.deleteBtn) els.deleteBtn.disabled = !state.file;
      if (els.resetBtn) els.resetBtn.disabled = !state.file;
    }
  }

  async function deleteCurrentDocument() {
    if (!state.file || state.deletingDocument) return;
    if (!state.currentDocumentId) {
      resetScreen();
      showMessage('Documento removido.', 'success');
      return;
    }
    state.deletingDocument = true;
    if (els.deleteBtn) els.deleteBtn.disabled = true;
    els.runBtn.disabled = true;
    setStatus('A eliminar o documento...');
    try {
      await fetchJson(`/api/document_ai/documents/${encodeURIComponent(state.currentDocumentId)}`, {
        method: 'DELETE',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ view: state.view }),
      });
      showMessage('Documento eliminado.', 'success');
      window.location.href = inboxUrl();
    } catch (error) {
      setStatus(error.message || 'Não foi possível eliminar o documento.', true);
      showMessage(error.message || 'Não foi possível eliminar o documento.', 'error');
    } finally {
      state.deletingDocument = false;
      if (els.deleteBtn) els.deleteBtn.disabled = !state.file;
      els.runBtn.disabled = !state.file;
    }
  }

  async function submitDocumentToPhc({ navigate = true, announceSuccess = true } = {}) {
    if (!els.submitPhcBtn || state.submittingPhc) return null;
    if (state.integratedPhc) return state.integrationResult || { duplicate: true };
    const documentType = state.documentData?.document_type;
    if (!state.file || !['mail', 'bank_statement', 'invoice', 'provisional_invoice', 'credit_note'].includes(documentType)) {
      showMessage('Carrega e valida primeiro um documento compatível.', 'error');
      return null;
    }
    if (!await flushAnalysisSave()) return null;
    state.submittingPhc = true;
    updateSubmitPhcButton();
    const isProvisionalInvoice = ['invoice', 'provisional_invoice', 'credit_note'].includes(documentType);
    setStatus(isProvisionalInvoice
      ? 'A criar a correspondência, o documento provisório, as linhas e os anexos no PHC...'
      : 'A reservar a numeração, guardar o PDF no GED e criar a correspondência no PHC...');
    const formData = new FormData();
    formData.append('file', state.file);
    formData.append('document_data', JSON.stringify(state.documentData));
    if (state.currentDocumentId) formData.append('document_id', state.currentDocumentId);
    try {
      const endpoint = isProvisionalInvoice
        ? '/api/document_ai/provisional-invoice/submit'
        : '/api/document_ai/correspondence/submit';
      const payload = await fetchJson(endpoint, {
        method: 'POST',
        body: formData,
      });
      state.correspondenceReference = Number(payload.reference || state.correspondenceReference || 0) || null;
      state.correspondenceYear = Number(payload.year || state.correspondenceYear || new Date().getFullYear());
      state.integrationResult = payload;
      state.integratedPhc = true;
      state.documentData.correspondence_reference = state.correspondenceReference;
      state.documentData.correspondence_year = state.correspondenceYear;
      renderDocumentCard();
      renderGedDestination();
      els.persistenceNote.textContent = payload.duplicate
        ? 'Este PDF já se encontrava integrado no PHC; não foi criado um duplicado.'
        : (isProvisionalInvoice ? 'O documento foi integrado no PHC, com linhas e anexos.' : 'O correio foi guardado no GED e integrado no PHC.');
      setStatus(payload.message || 'Documento integrado no PHC.');
      if (announceSuccess) showMessage(payload.message || 'Documento integrado no PHC.', 'success');
      if (isProvisionalInvoice && navigate) {
        state.view = 'accounting';
        window.setTimeout(() => {
          window.location.href = '/document_ai/inbox?view=accounting';
        }, 700);
      }
      return { payload, isProvisionalInvoice };
    } catch (error) {
      setStatus(error.message || 'Não foi possível submeter a correspondência.', true);
      showMessage(error.message || 'Não foi possível submeter a correspondência.', 'error');
      return null;
    } finally {
      state.submittingPhc = false;
      updateSubmitPhcButton();
    }
  }

  async function confirmDocumentControl({ announceSuccess = true } = {}) {
    if (state.controlOk) return true;
    if (!els.controlOkBtn || !state.currentDocumentId || state.submittingControl) return false;
    if (!await flushAnalysisSave()) return false;
    state.submittingControl = true;
    updateSubmitPhcButton();
    setStatus('A confirmar o Controlo OK...');
    try {
      const payload = await fetchJson(`/api/document_ai/documents/${encodeURIComponent(state.currentDocumentId)}/control-ok`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ document: state.documentData || {} }),
      });
      state.controlOk = Boolean(payload.workflow?.control_ok);
      setStatus('Controlo OK concluído. A validação está disponível.');
      if (announceSuccess) showMessage('Controlo OK concluído.', 'success');
      return state.controlOk;
    } catch (error) {
      setStatus(error.message || 'Não foi possível concluir o controlo.', true);
      showMessage(error.message || 'Não foi possível concluir o controlo.', 'error');
      return false;
    } finally {
      state.submittingControl = false;
      updateSubmitPhcButton();
    }
  }

  function clearRequiredInfoHighlights() {
    document.querySelectorAll('.docai-required-missing').forEach((element) => {
      element.classList.remove('docai-required-missing');
    });
  }

  function showRequiredInfo(requiredInfo) {
    clearRequiredInfoHighlights();
    const targets = Array.isArray(requiredInfo?.targets) ? requiredInfo.targets : [];
    let firstTarget = null;
    targets.forEach((targetId) => {
      const target = document.getElementById(targetId);
      if (!target) return;
      target.classList.add('docai-required-missing');
      firstTarget ||= target;
    });
    firstTarget?.scrollIntoView({ behavior: 'smooth', block: 'center' });
    const focusTarget = firstTarget?.matches('input, select, textarea, button, [tabindex]')
      ? firstTarget
      : firstTarget?.querySelector('input, select, textarea, button, [tabindex]');
    window.setTimeout(() => focusTarget?.focus({ preventScroll: true }), 250);
  }

  async function validateWorkflowStage({ confirmDuplicate = false } = {}) {
    if (!els.workflowValidateBtn || !state.currentDocumentId || !state.documentData || state.workflowSubmitting) return;
    if (!await flushAnalysisSave()) return;
    state.workflowSubmitting = true;
    clearRequiredInfoHighlights();
    updateSubmitPhcButton();
    setStatus('A validar a etapa documental...');
    try {
      setStatus('A confirmar as condições da etapa...');
      const preflight = await fetchJson(`/api/document_ai/documents/${encodeURIComponent(state.currentDocumentId)}/workflow/preflight`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          view: state.view,
          document: state.documentData,
          confirm_duplicate: Boolean(confirmDuplicate),
        }),
      });
      if (preflight.duplicate_confirmation_required) {
        openDuplicateModal(preflight.duplicates || []);
        setStatus('Confirma o documento duplicado antes de continuar.', true);
        return;
      }
      if (!preflight.ok) {
        showRequiredInfo(preflight.required_info);
        const messages = Array.isArray(preflight.required_info?.messages)
          ? preflight.required_info.messages
          : [preflight.message || 'Existem informações obrigatórias por preencher.'];
        const message = messages.filter(Boolean).join(' ');
        setStatus(message, true);
        return;
      }
      await fetchJson(`/api/document_ai/documents/${encodeURIComponent(state.currentDocumentId)}/workflow/validate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ view: state.view, document: state.documentData }),
      });
      showMessage('Documento validado.', 'success');
      window.location.href = inboxUrl();
    } catch (error) {
      setStatus(error.message || 'Não foi possível validar a etapa.', true);
    } finally {
      state.workflowSubmitting = false;
      updateSubmitPhcButton();
    }
  }

  els.backBtn?.addEventListener('click', async () => {
    if (await flushAnalysisSave()) window.location.href = inboxUrl();
  });
  els.viewTabs?.addEventListener('click', (event) => {
    const view = event.target.closest('[data-view]')?.dataset.view;
    if (view) selectView(view);
  });
  els.viewTabs?.addEventListener('keydown', (event) => {
    if (!['ArrowLeft', 'ArrowRight'].includes(event.key)) return;
    const tabs = [...els.viewTabs.querySelectorAll('[data-view]')];
    const currentIndex = tabs.findIndex((button) => button.dataset.view === state.view);
    const direction = event.key === 'ArrowRight' ? 1 : -1;
    const next = tabs[(currentIndex + direction + tabs.length) % tabs.length];
    event.preventDefault();
    selectView(next.dataset.view);
    next.focus();
  });
  window.addEventListener('popstate', () => {
    const requested = new URLSearchParams(window.location.search).get('view');
    state.view = allowedViews.has(requested) ? requested : ([...allowedViews][0] || '');
    renderViewTabs();
    renderModeCard();
  });
  els.gedFolderSelect?.addEventListener('change', async () => {
    if (!state.documentData?.customer) return;
    state.gedFolderManuallySelected = true;
    state.documentData.customer.ged_folder = els.gedFolderSelect.value;
    state.documentData.customer.ged_folder_manually_selected = true;
    state.documentData.customer.ged_folder_suggested_by = '';
    renderGedDestination();
    const agency = els.gedFolderSelect.selectedOptions[0]?.textContent || 'Escolher';
    setStatus(els.gedFolderSelect.value ? `Agência INTERSOL alterada para ${agency}.` : 'Falta a agência.', !els.gedFolderSelect.value);
    if (!state.currentDocumentId) return;
    try {
      await scheduleAnalysisSave({ immediate: true });
      setStatus(`Agência INTERSOL ${agency} guardada.`);
    } catch (error) {
      setStatus('Não foi possível guardar a agência INTERSOL.', true);
    }
  });
  els.accessCloseTop?.addEventListener('click', closeAccessModal);
  els.accessClose?.addEventListener('click', closeAccessModal);
  els.accessModal?.addEventListener('click', (event) => { if (event.target === els.accessModal) closeAccessModal(); });
  els.accessSearchBtn?.addEventListener('click', searchAccessUsers);
  els.accessSearch?.addEventListener('input', () => {
    window.clearTimeout(state.accessSearchTimer);
    state.accessSearchTimer = window.setTimeout(searchAccessUsers, 250);
  });
  els.accessSearch?.addEventListener('keydown', (event) => { if (event.key === 'Enter') searchAccessUsers(); });
  els.accessUsers?.addEventListener('click', (event) => {
    const option = event.target.closest('[data-integration-access-user]');
    if (option) selectAccessUser(Number(option.dataset.integrationAccessUser));
  });
  els.accessSave?.addEventListener('click', saveAccessPermissions);
  els.submitPhcBtn?.addEventListener('click', submitDocumentToPhc);
  els.controlOkBtn?.addEventListener('click', confirmDocumentControl);
  els.workflowValidateBtn?.addEventListener('click', validateWorkflowStage);
  els.saveRetryBtn?.addEventListener('click', () => flushAnalysisSave());
  els.conflictReload?.addEventListener('click', () => window.location.reload());
  els.conflictKeep?.addEventListener('click', () => {
    els.conflictModal?.classList.remove('sz_is_open');
    els.conflictModal?.setAttribute('aria-hidden', 'true');
    setStatus('Documento alterado por outro utilizador.', true);
  });
  els.duplicateCloseTop?.addEventListener('click', closeDuplicateModal);
  els.duplicateCancel?.addEventListener('click', closeDuplicateModal);
  els.duplicateConfirm?.addEventListener('click', async () => {
    const duplicateDocumentId = state.duplicateMatches[0]?.document_id;
    try {
      await saveDuplicateDecision('different', duplicateDocumentId);
      closeDuplicateModal();
      validateWorkflowStage({ confirmDuplicate: true });
    } catch (error) {
      setStatus(error.message, true);
    }
  });
  els.duplicateList?.addEventListener('click', (event) => {
    const associateDocumentId = event.target.closest('[data-associate-duplicate]')?.dataset.associateDuplicate;
    if (associateDocumentId) {
      saveDuplicateDecision('associate', associateDocumentId)
        .then((payload) => { window.location.href = extractUrl(payload.open_document_id || associateDocumentId); })
        .catch((error) => setStatus(error.message, true));
      return;
    }
    const documentId = event.target.closest('[data-open-duplicate]')?.dataset.openDuplicate;
    if (!documentId) return;
    window.open(extractUrl(documentId), '_blank', 'noopener');
  });
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
  els.runBtn?.addEventListener('click', () => extractDocument({ force: true }));
  els.deleteBtn?.addEventListener('click', deleteCurrentDocument);
  els.totalsCard?.addEventListener('click', openTotalsModal);
  els.totalsCard?.addEventListener('keydown', (event) => {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      openTotalsModal();
    }
  });
  els.totalsCloseTop?.addEventListener('click', closeTotalsModal);
  els.totalsClose?.addEventListener('click', closeTotalsModal);
  els.totalsModal?.addEventListener('click', (event) => {
    if (event.target === els.totalsModal) closeTotalsModal();
  });
  els.gedFileName?.addEventListener('click', () => copyClassificationValue(els.gedFileName.textContent));
  els.gedFileName?.addEventListener('keydown', (event) => {
    if (event.key === 'Enter' || event.key === ' ') copyClassificationValue(els.gedFileName.textContent);
  });
  els.gedPath?.addEventListener('click', (event) => {
    const target = event.target.closest('[data-copy-value]');
    if (target) copyClassificationValue(target.dataset.copyValue);
  });
  els.openPdfBtn?.addEventListener('click', () => {
    const pdfUrl = state.currentDocumentId
      ? `/api/document_ai/documents/${encodeURIComponent(state.currentDocumentId)}/original?view=${encodeURIComponent(state.view)}${state.readOnly ? '&archive=1' : ''}`
      : state.previewUrl;
    if (pdfUrl) window.open(pdfUrl, '_blank', 'noopener,noreferrer');
  });
  els.splitBtn?.addEventListener('click', splitDocumentBatch);
  els.splitLineBtn?.addEventListener('click', distributeSelectedLinesAcrossDeliveryNotes);
  els.linesBody?.addEventListener('click', (event) => {
    const vehicle = event.target.closest('[data-line-vehicle]');
    if (vehicle) {
      openVehicleModal(Number(vehicle.dataset.lineVehicle));
      return;
    }
    const article = event.target.closest('[data-line-article]');
    if (article) {
      openArticleModal(Number(article.dataset.lineArticle));
      return;
    }
    const project = event.target.closest('[data-line-project]');
    if (project) {
      openLineProjectModal(Number(project.dataset.lineProject));
      return;
    }
    const bc = event.target.closest('[data-line-bc]');
    if (bc) {
      openBcModal(Number(bc.dataset.lineBc));
      return;
    }
    const bcToggle = event.target.closest('[data-line-bc-toggle]');
    if (bcToggle) {
      const lineIndex = Number(bcToggle.dataset.lineBcToggle);
      if (state.expandedBcLines.has(lineIndex)) state.expandedBcLines.delete(lineIndex);
      else state.expandedBcLines.add(lineIndex);
      renderLines(state.documentData?.lines || [], state.documentData?.currency || '');
      return;
    }
    const picker = event.target.closest('[data-line-select]');
    if (picker) selectLineForSplit(Number(picker.dataset.lineSelect));
  });
  els.linesBody?.addEventListener('change', async (event) => {
    const input = event.target.closest('[data-line-group], [data-line-description], [data-line-qty], [data-line-unit-price], [data-line-total], [data-line-date]');
    if (!input) return;
    const lineIndex = Number(input.dataset.lineGroup ?? input.dataset.lineDescription ?? input.dataset.lineQty ?? input.dataset.lineUnitPrice ?? input.dataset.lineTotal ?? input.dataset.lineDate);
    const line = state.documentData?.lines?.[lineIndex];
    if (!line) return;
    let message = 'Linha guardada.';
    if (input.matches('[data-line-group]')) {
      const validation = validateLineGroupChange(state.documentData.lines || [], lineIndex, input.value);
      if (!validation.ok) {
        input.value = normalizeLineGroupCode(line.article_group_code);
        input.classList.add('is-invalid');
        window.setTimeout(() => input.classList.remove('is-invalid'), 1800);
        setStatus(validation.message, true);
        showMessage(validation.message, 'error');
        return;
      }
      line.article_group_code = validation.code;
      markLineManualFields(line, 'article_group_code');
      message = validation.code ? `Grupo ${validation.code} guardado.` : 'Grupo removido.';
    } else if (input.matches('[data-line-description]')) {
      line.description = input.value.trim();
      markLineManualFields(line, 'description');
      message = 'Designação guardada.';
    } else if (input.matches('[data-line-date]')) {
      line.date = input.value || '';
      markLineManualFields(line, 'date');
      message = 'Data guardada.';
    } else if (input.matches('[data-line-total]')) {
      line.net_amount = parseEditableNumber(input.value);
      markLineManualFields(line, 'net_amount');
      message = 'Preço total guardado.';
    } else {
      if (input.matches('[data-line-qty]')) line.qty = parseEditableNumber(input.value);
      if (input.matches('[data-line-unit-price]')) line.unit_price = parseEditableNumber(input.value);
      line.net_amount = Math.round((Number(line.qty || 0) * Number(line.unit_price || 0) + Number.EPSILON) * 100) / 100;
      markLineManualFields(line, input.matches('[data-line-qty]') ? 'qty' : 'unit_price', 'net_amount');
      message = 'Quantidade e valores guardados.';
    }
    renderLines(state.documentData.lines || [], state.documentData.currency || '');
    scheduleAnalysisSave();
  });
  els.groupPrevious?.addEventListener('click', () => {
    if (!state.loading && !state.splitting) openGroupDocument(state.groupIndex - 1);
  });
  els.groupNext?.addEventListener('click', () => {
    if (!state.loading && !state.splitting) openGroupDocument(state.groupIndex + 1);
  });
  els.supplierCard?.addEventListener('click', openSupplierModal);
  els.customerCard?.addEventListener('click', openEntityModal);
  els.customerCard?.addEventListener('keydown', (event) => {
    if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); openEntityModal(); }
  });
  els.supplierCard?.addEventListener('keydown', (event) => {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      openSupplierModal();
    }
  });
  els.projectCard?.addEventListener('click', openProjectModal);
  els.projectCard?.addEventListener('keydown', (event) => {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      openProjectModal();
    }
  });
  els.projectClear?.addEventListener('click', clearProject);
  els.supplierModalSearchBtn?.addEventListener('click', searchSupplierCandidates);
  els.supplierManualBtn?.addEventListener('click', useManualSenderName);
  els.supplierModalSearch?.addEventListener('input', () => {
    window.clearTimeout(state.supplierSearchTimer);
    state.supplierSearchToken += 1;
    const query = els.supplierModalSearch.value.trim();
    if (query.length < 2) {
      els.supplierModalList.innerHTML = '<div class="docai-empty-state">Escreve pelo menos dois caracteres para pesquisar.</div>';
      return;
    }
    state.supplierSearchTimer = window.setTimeout(searchSupplierCandidates, 300);
  });
  els.supplierModalSearch?.addEventListener('keydown', (event) => {
    if (event.key === 'Enter') searchSupplierCandidates();
  });
  els.supplierModalCloseTop?.addEventListener('click', closeSupplierModal);
  els.supplierModalClose?.addEventListener('click', closeSupplierModal);
  els.entitySearchBtn?.addEventListener('click', searchEntityCandidates);
  els.entitySearch?.addEventListener('input', () => {
    window.clearTimeout(state.entitySearchTimer);
    const query = els.entitySearch.value.trim();
    if (query.length === 1) return;
    state.entitySearchTimer = window.setTimeout(searchEntityCandidates, 300);
  });
  els.entitySearch?.addEventListener('keydown', (event) => { if (event.key === 'Enter') searchEntityCandidates(); });
  els.entityCloseTop?.addEventListener('click', closeEntityModal);
  els.entityClose?.addEventListener('click', closeEntityModal);
  els.entityModal?.addEventListener('click', (event) => { if (event.target === els.entityModal) closeEntityModal(); });
  els.entityList?.addEventListener('click', (event) => {
    const option = event.target.closest('[data-entity-index]');
    if (option) selectEntity(Number(option.dataset.entityIndex));
  });
  els.supplierModal?.addEventListener('click', (event) => {
    if (event.target === els.supplierModal) closeSupplierModal();
  });
  els.supplierModalList?.addEventListener('click', (event) => {
    const option = event.target.closest('[data-supplier-index]');
    if (!option) return;
    selectSupplier(Number(option.dataset.supplierIndex));
  });
  els.projectSearchBtn?.addEventListener('click', searchProjectCandidates);
  els.projectSearch?.addEventListener('keydown', (event) => {
    if (event.key === 'Enter') searchProjectCandidates();
  });
  els.projectCloseTop?.addEventListener('click', closeProjectModal);
  els.projectClose?.addEventListener('click', closeProjectModal);
  els.projectModal?.addEventListener('click', (event) => {
    if (event.target === els.projectModal) closeProjectModal();
  });
  els.projectList?.addEventListener('click', (event) => {
    const option = event.target.closest('[data-project-index]');
    if (option) selectProject(Number(option.dataset.projectIndex));
  });
  els.articleSearchBtn?.addEventListener('click', searchArticleCandidates);
  els.articleSearch?.addEventListener('keydown', (event) => {
    if (event.key === 'Enter') searchArticleCandidates();
  });
  els.articleCloseTop?.addEventListener('click', closeArticleModal);
  els.articleClose?.addEventListener('click', closeArticleModal);
  els.articleModal?.addEventListener('click', (event) => {
    if (event.target === els.articleModal) closeArticleModal();
  });
  els.articleList?.addEventListener('click', (event) => {
    const option = event.target.closest('[data-article-index]');
    if (option) selectArticle(Number(option.dataset.articleIndex));
  });
  els.vehicleSearchBtn?.addEventListener('click', searchVehicleCandidates);
  els.vehicleSearch?.addEventListener('keydown', (event) => {
    if (event.key === 'Enter') searchVehicleCandidates();
  });
  els.vehicleCloseTop?.addEventListener('click', closeVehicleModal);
  els.vehicleClose?.addEventListener('click', closeVehicleModal);
  els.vehicleRemove?.addEventListener('click', removeVehicle);
  els.vehicleModal?.addEventListener('click', (event) => {
    if (event.target === els.vehicleModal) closeVehicleModal();
  });
  els.vehicleList?.addEventListener('click', (event) => {
    const option = event.target.closest('[data-vehicle-index]');
    if (option) selectVehicle(Number(option.dataset.vehicleIndex));
  });
  els.bcCloseTop?.addEventListener('click', closeBcModal);
  els.bcClose?.addEventListener('click', closeBcModal);
  els.bcSave?.addEventListener('click', saveBcAssignments);
  els.bcModal?.addEventListener('click', (event) => {
    if (event.target === els.bcModal) closeBcModal();
  });
  els.bcList?.addEventListener('change', (event) => {
    const input = event.target.closest('[data-bc-origin-stamp]');
    if (!input) return;
    if (input.checked) state.bcSelectedStamps.add(input.dataset.bcOriginStamp);
    else state.bcSelectedStamps.delete(input.dataset.bcOriginStamp);
  });
  els.originFlow?.addEventListener('click', (event) => {
    const linkButton = event.target.closest('[data-origin-link]');
    if (linkButton) {
      event.preventDefault();
      event.stopPropagation();
      linkDocumentOrigin(linkButton.dataset.originLink);
      return;
    }
    const option = event.target.closest('[data-origin-index]');
    if (option) openOriginDetail(option.dataset.originIndex);
  });
  els.originFlow?.addEventListener('change', (event) => {
    const input = event.target.closest('[data-virtual-bl]');
    if (!input) return;
    if (input.checked) state.selectedDeliveryNoteGroups.add(input.dataset.virtualBl);
    else state.selectedDeliveryNoteGroups.delete(input.dataset.virtualBl);
    renderLines(state.documentData?.lines || [], state.documentData?.currency || '');
  });
  els.originFlow?.addEventListener('keydown', (event) => {
    if (!['Enter', ' '].includes(event.key) || event.target.closest('[data-origin-link]')) return;
    const option = event.target.closest('[data-origin-index]');
    if (!option) return;
    event.preventDefault();
    openOriginDetail(option.dataset.originIndex);
  });
  els.originDetailCloseTop?.addEventListener('click', closeOriginDetailModal);
  els.originDetailClose?.addEventListener('click', closeOriginDetailModal);
  els.originDetailModal?.addEventListener('click', (event) => {
    if (event.target === els.originDetailModal) closeOriginDetailModal();
  });
  els.originTabs?.addEventListener('click', (event) => {
    const key = event.target.closest('[data-origin-tab]')?.dataset.originTab;
    if (!key || key === state.activeOriginStage) return;
    state.activeOriginStage = key;
    const stages = [...els.originTabs.querySelectorAll('[data-origin-tab]')].map((button) => ({
      key: button.dataset.originTab,
      label: button.childNodes[0]?.textContent?.trim() || button.dataset.originTab,
    }));
    renderOriginTabs(stages);
  });
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && els.accessModal?.classList.contains('sz_is_open')) closeAccessModal();
    if (event.key === 'Escape' && els.supplierModal?.classList.contains('sz_is_open')) closeSupplierModal();
    if (event.key === 'Escape' && els.projectModal?.classList.contains('sz_is_open')) closeProjectModal();
    if (event.key === 'Escape' && els.articleModal?.classList.contains('sz_is_open')) closeArticleModal();
    if (event.key === 'Escape' && els.vehicleModal?.classList.contains('sz_is_open')) closeVehicleModal();
    if (event.key === 'Escape' && els.bcModal?.classList.contains('sz_is_open')) closeBcModal();
    if (event.key === 'Escape' && els.originDetailModal?.classList.contains('sz_is_open')) closeOriginDetailModal();
  });
  window.addEventListener('beforeunload', cleanupPreview);

  renderViewTabs();
  renderModeCard();
  const documentId = initialParams.get('document_id');
  if (documentId) loadInboxDocument(documentId);
});
