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
    gedFolderTrigger: document.getElementById('docAiExtractGedFolderTrigger'),
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
    originDetailSubtitle: document.getElementById('docAiOriginDetailSubtitle'),
    originDetailLoading: document.getElementById('docAiOriginDetailLoading'),
    originDetailTable: document.getElementById('docAiOriginDetailTable'),
    originDetailHead: document.getElementById('docAiOriginDetailHead'),
    originDetailBody: document.getElementById('docAiOriginDetailBody'),
    originDetailEmpty: document.getElementById('docAiOriginDetailEmpty'),
    originDetailCloseTop: document.getElementById('docAiOriginDetailCloseTop'),
    originDetailClose: document.getElementById('docAiOriginDetailClose'),
    originDetailValidate: document.getElementById('docAiOriginDetailValidate'),
    originMeta: document.getElementById('docAiExtractOriginMeta'),
    originAction: document.getElementById('docAiExtractOriginAction'),
    originLoading: document.getElementById('docAiExtractOriginLoading'),
    originFlow: document.getElementById('docAiExtractOriginFlow'),
    originTabs: document.getElementById('docAiExtractOriginTabs'),
    lineCount: document.getElementById('docAiExtractLineCount'),
    splitLineBtn: document.getElementById('docAiExtractSplitLineBtn'),
    linesBody: document.getElementById('docAiExtractLinesBody'),
    groupDropzone: document.getElementById('docAiExtractGroupDropzone'),
    lineDistributionModal: document.getElementById('docAiLineDistributionModal'),
    lineDistributionTitle: document.getElementById('docAiLineDistributionTitle'),
    lineDistributionContext: document.getElementById('docAiLineDistributionContext'),
    lineDistributionMain: document.getElementById('docAiLineDistributionMain'),
    lineDistributionSearchPane: document.getElementById('docAiLineDistributionSearchPane'),
    lineDistributionSearchBack: document.getElementById('docAiLineDistributionSearchBack'),
    lineDistributionSearchLabel: document.getElementById('docAiLineDistributionSearchLabel'),
    lineDistributionSearchInput: document.getElementById('docAiLineDistributionSearchInput'),
    lineDistributionSearchButton: document.getElementById('docAiLineDistributionSearchButton'),
    lineDistributionSearchResults: document.getElementById('docAiLineDistributionSearchResults'),
    lineDistributionQuantityBalance: document.getElementById('docAiLineDistributionQuantityBalance'),
    lineDistributionTotalBalance: document.getElementById('docAiLineDistributionTotalBalance'),
    lineDistributionTable: document.getElementById('docAiLineDistributionTable'),
    lineDistributionHead: document.getElementById('docAiLineDistributionHead'),
    lineDistributionBody: document.getElementById('docAiLineDistributionBody'),
    lineDistributionAdd: document.getElementById('docAiLineDistributionAdd'),
    lineDistributionError: document.getElementById('docAiLineDistributionError'),
    lineDistributionCloseTop: document.getElementById('docAiLineDistributionCloseTop'),
    lineDistributionClose: document.getElementById('docAiLineDistributionClose'),
    lineDistributionSave: document.getElementById('docAiLineDistributionSave'),
    lineCostsModal: document.getElementById('docAiLineCostsModal'),
    lineCostsTitle: document.getElementById('docAiLineCostsTitle'),
    lineCostsContext: document.getElementById('docAiLineCostsContext'),
    lineCostsTabs: document.getElementById('docAiLineCostsTabs'),
    lineCostsList: document.getElementById('docAiLineCostsList'),
    lineCostsBody: document.getElementById('docAiLineCostsBody'),
    lineCostsDetail: document.getElementById('docAiLineCostsDetail'),
    lineCostsDetailFields: document.getElementById('docAiLineCostsDetailFields'),
    lineCostsBack: document.getElementById('docAiLineCostsBack'),
    lineCostsCloseTop: document.getElementById('docAiLineCostsCloseTop'),
    lineCostsClose: document.getElementById('docAiLineCostsClose'),
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
    projectDistribute: document.getElementById('docAiProjectDistribute'),
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
    vehicleDistribute: document.getElementById('docAiVehicleDistribute'),
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
    archiveAudit: document.getElementById('docAiExtractArchiveAudit'),
    archiveAuditState: document.getElementById('docAiExtractArchiveAuditState'),
    archiveAuditActor: document.getElementById('docAiExtractArchiveAuditActor'),
    archiveAuditRelations: document.getElementById('docAiExtractArchiveAuditRelations'),
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
    splitting: false,
    originSearchToken: 0,
    originPayload: null,
    originCandidates: [],
    creditNoteCandidates: [],
    creditNoteSelectedFo: '',
    activeOriginStage: '',
    consultedOriginStamp: '',
    selectedOrigins: [],
    selectedProject: null,
    projectCandidates: [],
    projectTargetLineIndex: null,
    articleCandidates: [],
    articleSuggestionConfidence: 'none',
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
    deliveryNoteDistributionMode: false,
    originLineMatches: [],
    originLineReferenceLabel: '',
    originLineMatchByLine: new WeakMap(),
    originLineageChanged: false,
    originLineageSaveScheduled: false,
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
    headerPreflight: null,
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
    headerEditing: '',
    confirmInvoiceTypeRemoval: false,
    validationVisible: false,
    validationMissing: new Set(),
    originOperation: null,
    draggedLineId: '',
    keyboardGroupLineId: '',
    lineDistributionTargetIndex: null,
    lineDistributionMode: 'project',
    lineDistributionDraft: [],
    lineDistributionSearchRow: null,
    lineDistributionSearchField: '',
    lineDistributionSearchItems: [],
    lineCostsTargetIndex: null,
    lineCostsType: '',
    readOnly,
    archiveSnapshot: null,
    view: allowedViews.has(initialView) ? initialView : ([...allowedViews][0] || ''),
  };
  const originActionHandlers = new Map();

  const typeLabels = {
    invoice: 'Fatura',
    credit_note: 'Nota de crédito',
    contract: 'Contrato',
    subcontract: 'Contrato Sub.Emp.',
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
    const visibleMessage = /^(Leitura guardada carregada do inbox\.|Leitura concluída\.|Centro de Custo .* aplicado às origens\.)$/i.test(String(message || '').trim())
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

  async function selectView(view, { updateHistory = true } = {}) {
    if (!allowedViews.has(view) || view === state.view) return;
    const targetLabel = workflowViewLabel(view);
    if (state.currentDocumentId && view === 'management' && !state.workflow?.reception_validated) {
      showMessage(`O documento ainda não chegou ao ${targetLabel}: falta validar na Receção.`, 'warning');
      return;
    }
    if (state.currentDocumentId && view === 'accounting' && !state.workflow?.management_validated) {
      showMessage(`O documento ainda não chegou à ${targetLabel}: falta validar no Controlo de Gestão.`, 'warning');
      return;
    }
    if (!await flushAnalysisSave()) {
      showMessage('Erro ao guardar. Resolve a gravação antes de mudar de departamento.', 'error');
      return;
    }
    state.view = view;
    if (updateHistory) window.location.href = extractUrl();
    else {
      renderViewTabs();
      renderModeCard();
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

  function countLabel(value, singular, plural) {
    const count = Number(value || 0);
    return `${formatNumber(count, 0)} ${count === 1 ? singular : plural}`;
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

  function ensureLineIdentities(lines = state.documentData?.lines || []) {
    (lines || []).forEach((line) => {
      if (!line.line_id) line.line_id = window.crypto.randomUUID();
      markLineManualFields(line, 'line_id');
      (line.sub_lines || line.sublines || []).forEach((child) => {
        if (!child.subline_id) child.subline_id = window.crypto.randomUUID();
        child.parent_line_id = line.line_id;
      });
    });
    return lines;
  }

  function groupMembers(line) {
    const groupId = String(line?.group_id || '');
    return groupId ? (state.documentData?.lines || []).filter((item) => String(item.group_id || '') === groupId) : [line];
  }

  function lineDestinations(line, kind) {
    const fields = kind === 'project' ? ['ccusto', 'project_ccusto'] : ['registration', 'matricula'];
    const values = new Set(fields.map((field) => String(line?.[field] || '').trim()).filter(Boolean));
    (line?.sub_lines || []).forEach((child) => fields.forEach((field) => {
      const value = String(child?.[field] || '').trim();
      if (value) values.add(value);
    }));
    return [...values];
  }

  function groupConflict(principal, associated) {
    const checks = [
      ['Artigo', principal.article_ref || principal.article, associated.article_ref || associated.article],
      ['Origem', principal.phc_origin_stamp || principal.origin_stamp, associated.phc_origin_stamp || associated.origin_stamp],
      ['Data', principal.date || principal.data, associated.date || associated.data],
      ['IVA', principal.tax_rate, associated.tax_rate],
    ];
    for (const [label, left, right] of checks) {
      if (String(left ?? '').trim() && String(right ?? '').trim() && String(left) !== String(right)) {
        return `Impossível agrupar: ${label} diferente.`;
      }
    }
    for (const [label, kind] of [['Centro de Custo', 'project'], ['Matrícula', 'vehicle']]) {
      const left = lineDestinations(principal, kind);
      const right = lineDestinations(associated, kind);
      if (left.length && right.length && JSON.stringify(left.sort()) !== JSON.stringify(right.sort())) return `Impossível agrupar: ${label} diferente.`;
    }
    return '';
  }

  function inheritPrincipalFields(principal, associated) {
    const aliases = [
      ['article_ref', 'article'], ['ccusto', 'project_ccusto'],
      ['phc_origin_stamp', 'origin_stamp', 'bostamp'],
      ['phc_origin_line_stamp', 'origin_line_stamp', 'bistamp'],
      ['date', 'data'], ['tax_rate'],
      ['registration', 'matricula'],
    ];
    aliases.forEach((fields) => {
      const value = fields.map((field) => principal[field]).find((item) => String(item ?? '').trim());
      fields.forEach((field) => { associated[field] = value ?? ''; });
    });
  }

  function applyPrincipalDistribution(principal, member) {
    const sourceRows = Array.isArray(principal?.sub_lines) ? principal.sub_lines : [];
    if (!sourceRows.length || !member) return;
    const memberQuantity = Number(member.qty ?? member.quantity ?? 0);
    const memberTotal = Number(member.net_amount ?? member.pt ?? 0);
    member.sub_lines = sourceRows.map((row) => ({
      subline_id: window.crypto.randomUUID(), parent_line_id: member.line_id,
      ccusto: row.ccusto, project_ccusto: row.ccusto,
      registration: row.registration, matricula: row.registration,
      vehicle_stamp: row.vehicle_stamp || '', percentage: Number(row.percentage || 0),
      qty: distributionRound(memberQuantity * Number(row.percentage || 0) / 100, 6),
      net_amount: distributionRound(memberTotal * Number(row.percentage || 0) / 100, 2),
      unit_price: Number(member.unit_price || 0), tax_rate: member.tax_rate ?? '',
      unit: member.unit || '', date: member.date || member.data || '', article_ref: member.article_ref || member.article || '',
    }));
    const last = member.sub_lines[member.sub_lines.length - 1];
    if (last) {
      last.qty = distributionRound(memberQuantity - member.sub_lines.slice(0, -1).reduce((sum, row) => sum + Number(row.qty || 0), 0), 6);
      last.net_amount = distributionRound(memberTotal - member.sub_lines.slice(0, -1).reduce((sum, row) => sum + Number(row.net_amount || 0), 0), 2);
    }
    const projects = [...new Set(member.sub_lines.map((row) => row.ccusto).filter(Boolean))];
    const vehicles = [...new Set(member.sub_lines.map((row) => row.registration).filter(Boolean))];
    member.ccusto = projects.length === 1 ? projects[0] : '';
    member.project_ccusto = member.ccusto;
    member.registration = vehicles.length === 1 ? vehicles[0] : '';
    member.matricula = member.registration;
    markLineManualFields(member, 'sub_lines', 'ccusto', 'project_ccusto', 'registration', 'matricula');
  }

  function detachAssociatedLine(line) {
    if (!line?.group_id || line.group_role !== 'associated') return false;
    const previousGroup = line.group_id;
    line.group_id = '';
    line.group_role = '';
    markLineManualFields(line, 'group_id', 'group_role');
    const remaining = (state.documentData?.lines || []).filter((item) => item.group_id === previousGroup);
    if (remaining.length === 1) {
      remaining[0].group_id = '';
      remaining[0].group_role = '';
      markLineManualFields(remaining[0], 'group_id', 'group_role');
    }
    showMessage('Linha desagrupada devido à alteração de um campo comum obrigatório.', 'info');
    return true;
  }

  async function groupLineOnTarget(sourceId, targetId) {
    if (!sourceId || !targetId || sourceId === targetId) return;
    const lines = ensureLineIdentities();
    const source = lines.find((line) => line.line_id === sourceId);
    const target = lines.find((line) => line.line_id === targetId);
    if (!source || !target) return;
    if (source.group_role === 'principal' && source.group_id && target.group_id && source.group_id !== target.group_id) {
      showMessage('Impossível fundir dois grupos existentes.', 'error');
      return;
    }
    const previousSourceGroup = String(source.group_id || '');
    const moving = source.group_role === 'principal' ? groupMembers(source) : [source];
    const destination = groupMembers(target);
    const combined = [...new Set([...destination, ...moving])];
    for (const line of combined) {
      if (line === target) continue;
      const conflict = groupConflict(target, line);
      if (conflict) {
        showMessage(conflict, 'error');
        setStatus(conflict, true);
        return;
      }
    }
    const groupId = String(target.group_id || `group-${window.crypto.randomUUID()}`);
    combined.forEach((line) => {
      line.group_id = groupId;
      line.group_role = line === target ? 'principal' : 'associated';
      inheritPrincipalFields(target, line);
      if (line !== target) applyPrincipalDistribution(target, line);
      markLineManualFields(line, 'group_id', 'group_role');
    });
    if (previousSourceGroup && previousSourceGroup !== groupId) {
      const oldMembers = lines.filter((line) => line.group_id === previousSourceGroup);
      if (oldMembers.length === 1) {
        oldMembers[0].group_id = '';
        oldMembers[0].group_role = '';
        markLineManualFields(oldMembers[0], 'group_id', 'group_role');
      }
    }
    const insertion = Math.max(0, lines.indexOf(target));
    const remaining = lines.filter((line) => !combined.includes(line));
    remaining.splice(Math.min(insertion, remaining.length), 0, target, ...combined.filter((line) => line !== target));
    state.documentData.lines = remaining;
    state.keyboardGroupLineId = '';
    renderLines(remaining, state.documentData.currency || '');
    await saveAdjustedLines(`Grupo guardado com ${combined.length} linhas.`);
  }

  async function ungroupLine(lineId) {
    const lines = ensureLineIdentities();
    const line = lines.find((item) => item.line_id === lineId);
    if (!line?.group_id) return;
    const previousGroup = line.group_id;
    const affected = line.group_role === 'principal'
      ? lines.filter((item) => item.group_id === previousGroup)
      : [line];
    affected.forEach((item) => {
      item.group_id = '';
      item.group_role = '';
      markLineManualFields(item, 'group_id', 'group_role');
    });
    const remaining = lines.filter((item) => item.group_id === previousGroup);
    if (remaining.length === 1) {
      remaining[0].group_id = '';
      remaining[0].group_role = '';
      markLineManualFields(remaining[0], 'group_id', 'group_role');
    }
    state.keyboardGroupLineId = '';
    renderLines(lines, state.documentData.currency || '');
    await saveAdjustedLines('Linha desagrupada.');
  }

  function distributionOptionalNumber(value) {
    if (value === null || value === undefined || String(value).trim() === '') return null;
    const number = Number(String(value).trim().replace(/\s/g, '').replace(',', '.'));
    return Number.isFinite(number) ? number : null;
  }

  function distributionRound(value, digits = 6) {
    const factor = 10 ** digits;
    return Math.round((Number(value || 0) + Number.EPSILON) * factor) / factor;
  }

  function formatDistributionInput(value) {
    if (value === null || value === undefined || value === '') return '';
    return String(value).replace('.', ',');
  }

  function distributionSourceLine() {
    return state.documentData?.lines?.[state.lineDistributionTargetIndex] || null;
  }

  function distributionRowsFromLine(line) {
    const lineQuantity = Number(line?.qty ?? line?.quantity ?? 0);
    const lineTotal = Number(line?.net_amount ?? line?.pt ?? 0);
    const sourceRows = Array.isArray(line?.sub_lines) && line.sub_lines.length
      ? line.sub_lines
      : [{
          ccusto: line?.ccusto || line?.project_ccusto || '',
          registration: line?.registration || line?.matricula || '',
          qty: line?.qty ?? line?.quantity ?? '',
          net_amount: line?.net_amount ?? line?.pt ?? '',
          tax_rate: line?.tax_rate ?? '',
          vehicle_stamp: line?.vehicle_stamp || '',
        }];
    const rows = sourceRows.map((source) => ({
      ...source,
      subline_id: source.subline_id || window.crypto.randomUUID(),
      parent_line_id: line.line_id,
      ccusto: String(source.ccusto || source.project_ccusto || '').trim(),
      project_ccusto: String(source.ccusto || source.project_ccusto || '').trim(),
      registration: String(source.registration || source.matricula || '').trim(),
      matricula: String(source.registration || source.matricula || '').trim(),
      qty: source.qty ?? source.quantity ?? '',
      net_amount: source.net_amount ?? source.pt ?? '',
      percentage: source.percentage ?? (lineTotal
        ? distributionRound(Number(source.net_amount ?? source.pt ?? 0) * 100 / lineTotal, 6)
        : (lineQuantity ? distributionRound(Number(source.qty ?? source.quantity ?? 0) * 100 / lineQuantity, 6) : 100)),
      tax_rate: source.tax_rate ?? line.tax_rate ?? '',
      unit_price: Number(line.unit_price || 0),
      unit: line.unit || '',
      date: line.date || line.data || '',
      article_ref: line.article_ref || line.article || '',
    }));
    if (rows.length) rows[rows.length - 1].percentage = distributionRound(100 - rows.slice(0, -1).reduce((sum, row) => sum + Number(row.percentage || 0), 0), 6);
    return rows;
  }

  function reconcileDistributionDraft(line, changedIndex = -1, changedField = '') {
    const rows = state.lineDistributionDraft;
    if (!rows.length) return;
    const lineQuantity = Number(line?.qty ?? line?.quantity ?? 0);
    const lineTotal = Number(line?.net_amount ?? line?.pt ?? 0);
    const lastIndex = rows.length - 1;
    if (changedIndex >= 0 && changedIndex < lastIndex) {
      const row = rows[changedIndex];
      const entered = distributionOptionalNumber(row[changedField]);
      let percentage = distributionOptionalNumber(row.percentage) || 0;
      if (changedField === 'qty' && lineQuantity) percentage = Number(entered || 0) * 100 / lineQuantity;
      if (changedField === 'net_amount' && lineTotal) percentage = Number(entered || 0) * 100 / lineTotal;
      row.percentage = distributionRound(percentage, 6);
      row.qty = distributionRound(lineQuantity * percentage / 100, 6);
      row.net_amount = distributionRound(lineTotal * percentage / 100, 2);
    }
    const last = rows[lastIndex];
    const previous = rows.slice(0, lastIndex);
    last.percentage = distributionRound(100 - previous.reduce((sum, row) => sum + (distributionOptionalNumber(row.percentage) || 0), 0), 6);
    last.qty = distributionRound(lineQuantity - previous.reduce((sum, row) => sum + (distributionOptionalNumber(row.qty) || 0), 0), 6);
    last.net_amount = distributionRound(lineTotal - previous.reduce((sum, row) => sum + (distributionOptionalNumber(row.net_amount) || 0), 0), 2);
  }

  function distributionDraftErrors(line, rows = state.lineDistributionDraft) {
    const errors = [];
    const lineQuantity = Number(line?.qty ?? line?.quantity ?? 0);
    const lineTotal = Number(line?.net_amount ?? line?.pt ?? 0);
    const unitPrice = Number(line?.unit_price || 0);
    const combinations = new Set();
    let quantity = 0;
    let total = 0;
    let percentage = 0;
    rows.forEach((row) => {
      const ccusto = String(row.ccusto || '').trim();
      const registration = String(row.registration || '').trim();
      const rowQuantity = distributionOptionalNumber(row.qty);
      const rowTotal = distributionOptionalNumber(row.net_amount);
      const taxRate = distributionOptionalNumber(row.tax_rate ?? line?.tax_rate);
      const rowPercentage = distributionOptionalNumber(row.percentage);
      if (!ccusto) errors.push(registration ? 'Matrícula s/Centro de Custo' : 'Falta Centro de Custo numa sublinha.');
      if (line?.vehicle_required && !registration) errors.push('Falta Matrícula numa sublinha.');
      if (rowQuantity === null || rowTotal === null || rowPercentage === null) errors.push('Falta distribuir %, Quantidade e PT numa sublinha.');
      if (taxRate === null) errors.push('Falta IVA numa sublinha.');
      if ((rowQuantity ?? 0) < 0 || (rowTotal ?? 0) < 0) errors.push('Quantidade e PT não podem ser negativos.');
      const combination = `${ccusto.toLocaleLowerCase('pt')}\u0000${registration.toLocaleLowerCase('pt')}`;
      if (combinations.has(combination)) errors.push('Existe uma combinação Centro de Custo/Matrícula duplicada.');
      combinations.add(combination);
      quantity += rowQuantity || 0;
      total += rowTotal || 0;
      percentage += rowPercentage || 0;
      if (unitPrice && rowQuantity !== null && rowTotal !== null && Math.abs((rowQuantity * unitPrice) - rowTotal) > 0.01) {
        errors.push('Quantidade × PU não corresponde ao PT numa sublinha.');
      }
    });
    if (!unitPrice) errors.push('PU igual a zero: corrige explicitamente a linha antes de validar.');
    if (quantity > lineQuantity + 0.01 || total > lineTotal + 0.01) errors.push('Uma sublinha excede o saldo por distribuir.');
    if (Math.abs(quantity - lineQuantity) > 0.01) errors.push('A Quantidade distribuída não corresponde à linha.');
    if (Math.abs(total - lineTotal) > 0.01) errors.push('O Valor distribuído não corresponde à linha.');
    if (Math.abs(percentage - 100) > 0.0001) errors.push('A distribuição deve totalizar exatamente 100 %.');
    return [...new Set(errors)];
  }

  function distributionBalanceLabel(label, distributed, expected) {
    const balance = distributionRound(expected - distributed, 6);
    return `${label} Distribuído: ${formatNumber(distributed, 2)} · Por distribuir: ${formatNumber(Math.abs(balance) <= 0.01 ? 0 : balance, 2)}`;
  }

  function renderLineDistribution() {
    const line = distributionSourceLine();
    if (!line) return;
    const mode = state.lineDistributionMode;
    const firstColumns = mode === 'vehicle'
      ? [['registration', 'Matrícula'], ['ccusto', 'Centro de Custo']]
      : [['ccusto', 'Centro de Custo'], ['registration', 'Matrícula']];
    els.lineDistributionHead.innerHTML = `${firstColumns.map(([, label]) => `<th>${label}</th>`).join('')}<th>%</th><th>Quantidade</th><th>PU</th><th>PT</th><th>IVA</th><th aria-label="Ações"></th>`;
    els.lineDistributionTable.dataset.mode = mode;
    const unitPrice = Number(line.unit_price || 0);
    els.lineDistributionBody.innerHTML = state.lineDistributionDraft.map((row, index) => {
      const missingVehicleProject = String(row.registration || '').trim() && !String(row.ccusto || '').trim();
      const destinationCells = firstColumns.map(([field, label]) => `<td><button type="button" class="docai-line-distribution-destination" data-distribution-search="${field}" data-distribution-row="${index}" aria-label="Selecionar ${label}">${escapeHtml(row[field] || `Selecionar ${label}`)}</button>${field === 'ccusto' && missingVehicleProject ? '<small class="docai-line-distribution-vehicle-warning">Matrícula s/Centro de Custo</small>' : ''}</td>`).join('');
      return `<tr data-distribution-row-index="${index}">
        ${destinationCells}
        <td><span class="docai-line-distribution-percent"><input class="sz_input" inputmode="decimal" data-distribution-field="percentage" data-distribution-row="${index}" value="${escapeHtml(formatDistributionInput(row.percentage))}" aria-label="Percentagem"><span>%</span></span></td>
        <td><input class="sz_input" inputmode="decimal" data-distribution-field="qty" data-distribution-row="${index}" value="${escapeHtml(formatDistributionInput(row.qty))}" aria-label="Quantidade"></td>
        <td><input class="sz_input" value="${escapeHtml(formatEditableAmount(unitPrice))}" aria-label="PU" readonly tabindex="-1"></td>
        <td><input class="sz_input" inputmode="decimal" data-distribution-field="net_amount" data-distribution-row="${index}" value="${escapeHtml(formatDistributionInput(row.net_amount))}" aria-label="PT"></td>
        <td><span class="docai-line-distribution-percent"><input class="sz_input" inputmode="decimal" data-distribution-field="tax_rate" data-distribution-row="${index}" value="${escapeHtml(formatDistributionInput(row.tax_rate))}" aria-label="IVA"><span>%</span></span></td>
        <td><button type="button" class="sz_icon_button" data-distribution-remove="${index}" aria-label="Remover destino"><i class="fa-solid fa-trash"></i></button></td>
      </tr>`;
    }).join('');
    const distributedQuantity = state.lineDistributionDraft.reduce((sum, row) => sum + (distributionOptionalNumber(row.qty) || 0), 0);
    const distributedTotal = state.lineDistributionDraft.reduce((sum, row) => sum + (distributionOptionalNumber(row.net_amount) || 0), 0);
    els.lineDistributionQuantityBalance.innerHTML = distributionBalanceLabel('Quantidade', distributedQuantity, Number(line.qty ?? line.quantity ?? 0));
    els.lineDistributionTotalBalance.innerHTML = distributionBalanceLabel('Valor', distributedTotal, Number(line.net_amount ?? line.pt ?? 0));
    const errors = distributionDraftErrors(line);
    els.lineDistributionError.textContent = errors[0] || '';
    els.lineDistributionError.hidden = !errors.length;
    els.lineDistributionSave.disabled = Boolean(errors.length);
  }

  function lineDistributionTitle() {
    return state.lineDistributionMode === 'vehicle' ? 'Distribuir por Matrículas' : 'Distribuir por CdC';
  }

  function returnToLineDistribution() {
    state.lineDistributionSearchRow = null;
    state.lineDistributionSearchField = '';
    state.lineDistributionSearchItems = [];
    els.lineDistributionSearchPane.hidden = true;
    els.lineDistributionMain.hidden = false;
    els.lineDistributionSave.hidden = false;
    els.lineDistributionTitle.textContent = lineDistributionTitle();
    renderLineDistribution();
  }

  async function searchLineDistributionDestinations() {
    const field = state.lineDistributionSearchField;
    if (!field) return;
    els.lineDistributionSearchButton.disabled = true;
    els.lineDistributionSearchResults.innerHTML = '<div class="docai-empty-state">A pesquisar no PHC...</div>';
    try {
      const endpoint = field === 'registration' ? 'vehicles' : 'projects';
      const payload = await fetchJson(`/api/document_ai/${endpoint}/search`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          customer: state.documentData?.customer || {},
          query: els.lineDistributionSearchInput.value.trim(),
          limit: 30,
        }),
      });
      state.lineDistributionSearchItems = payload.items || [];
      const clearOption = field === 'registration'
        ? '<button type="button" class="docai-supplier-match-option" data-distribution-search-index="-1"><span class="docai-supplier-match-main"><strong>Sem Matrícula</strong><span>Imputação direta ao Centro de Custo</span></span><span class="docai-supplier-match-score">Selecionar</span></button>'
        : '';
      els.lineDistributionSearchResults.innerHTML = clearOption + state.lineDistributionSearchItems.map((item, index) => {
        const value = field === 'registration' ? item.registration : item.ccusto;
        const detail = field === 'registration'
          ? [item.brand, item.model, item.ccusto ? `CdC ${item.ccusto}` : 'Matrícula s/Centro de Custo'].filter(Boolean).join(' · ')
          : [item.name, item.client, item.city].filter(Boolean).join(' · ');
        return `<button type="button" class="docai-supplier-match-option" data-distribution-search-index="${index}">
          <span class="docai-supplier-match-main"><strong>${escapeHtml(value || '--')}</strong><span>${escapeHtml(detail)}</span></span>
          <span class="docai-supplier-match-score">Selecionar</span>
        </button>`;
      }).join('');
      if (!clearOption && !state.lineDistributionSearchItems.length) {
        els.lineDistributionSearchResults.innerHTML = '<div class="docai-empty-state">Sem resultados.</div>';
      }
    } catch (error) {
      els.lineDistributionSearchResults.innerHTML = `<div class="docai-empty-state">${escapeHtml(error.message || 'Erro na pesquisa.')}</div>`;
    } finally {
      els.lineDistributionSearchButton.disabled = false;
    }
  }

  function openLineDistributionSearch(rowIndex, field) {
    state.lineDistributionSearchRow = Number(rowIndex);
    state.lineDistributionSearchField = field;
    const row = state.lineDistributionDraft[state.lineDistributionSearchRow];
    if (!row) return;
    const vehicle = field === 'registration';
    els.lineDistributionTitle.textContent = vehicle ? 'Selecionar matrícula' : 'Selecionar CdC';
    els.lineDistributionSearchLabel.textContent = vehicle ? 'Matrícula, marca, modelo ou n.º de frota' : 'Código, nome, cliente, morada ou localidade';
    els.lineDistributionSearchInput.value = row[field] || '';
    els.lineDistributionMain.hidden = true;
    els.lineDistributionSearchPane.hidden = false;
    els.lineDistributionSave.hidden = true;
    searchLineDistributionDestinations();
    window.setTimeout(() => els.lineDistributionSearchInput.focus(), 50);
  }

  function selectLineDistributionDestination(index) {
    const row = state.lineDistributionDraft[state.lineDistributionSearchRow];
    if (!row) return;
    if (index < 0 && state.lineDistributionSearchField === 'registration') {
      row.registration = '';
      row.matricula = '';
      row.vehicle_stamp = '';
    } else {
      const item = state.lineDistributionSearchItems[index];
      if (!item) return;
      if (state.lineDistributionSearchField === 'registration') {
        row.registration = item.registration || '';
        row.matricula = row.registration;
        row.vehicle_stamp = item.vehicle_stamp || '';
        if (!String(row.ccusto || '').trim() && String(item.ccusto || '').trim()) {
          row.ccusto = item.ccusto;
          row.project_ccusto = item.ccusto;
        }
      } else {
        row.ccusto = item.ccusto || '';
        row.project_ccusto = row.ccusto;
      }
    }
    returnToLineDistribution();
  }

  function closeLineDistributionModal() {
    state.lineDistributionTargetIndex = null;
    state.lineDistributionDraft = [];
    state.lineDistributionSearchItems = [];
    els.lineDistributionModal.classList.remove('sz_is_open');
    els.lineDistributionModal.setAttribute('aria-hidden', 'true');
  }

  function openLineDistribution(lineIndex, mode = 'project') {
    const line = state.documentData?.lines?.[Number(lineIndex)];
    if (!line) return;
    detachAssociatedLine(line);
    closeProjectModal();
    closeVehicleModal();
    state.lineDistributionTargetIndex = Number(lineIndex);
    state.lineDistributionMode = mode === 'vehicle' ? 'vehicle' : 'project';
    state.lineDistributionDraft = distributionRowsFromLine(line);
    els.lineDistributionTitle.textContent = lineDistributionTitle();
    els.lineDistributionContext.textContent = `${line.article_ref || line.article || 'Linha'} · ${line.description || ''}`;
    reconcileDistributionDraft(line);
    renderLineDistribution();
    els.lineDistributionMain.hidden = false;
    els.lineDistributionSearchPane.hidden = true;
    els.lineDistributionSave.hidden = false;
    els.lineDistributionModal.classList.add('sz_is_open');
    els.lineDistributionModal.setAttribute('aria-hidden', 'false');
  }

  function addLineDistributionRow() {
    const line = distributionSourceLine();
    if (!line) return;
    state.lineDistributionDraft.push({
      subline_id: window.crypto.randomUUID(), parent_line_id: line.line_id,
      ccusto: '', project_ccusto: '', registration: '', matricula: '',
      percentage: 0, qty: 0, net_amount: 0, unit_price: Number(line.unit_price || 0), tax_rate: line.tax_rate ?? '',
      unit: line.unit || '', date: line.date || line.data || '', article_ref: line.article_ref || line.article || '',
    });
    reconcileDistributionDraft(line);
    renderLineDistribution();
  }

  function updateLineDistributionField(input) {
    const row = state.lineDistributionDraft[Number(input.dataset.distributionRow)];
    const line = distributionSourceLine();
    if (!row || !line) return;
    const field = input.dataset.distributionField;
    if (['ccusto', 'registration'].includes(field)) {
      row[field] = input.value.trim();
      if (field === 'ccusto') row.project_ccusto = row.ccusto;
      if (field === 'registration') row.matricula = row.registration;
    } else {
      row[field] = input.value.trim();
      const number = distributionOptionalNumber(row[field]);
      if (['percentage', 'qty', 'net_amount'].includes(field) && number !== null) {
        reconcileDistributionDraft(line, Number(input.dataset.distributionRow), field);
      }
    }
    renderLineDistribution();
    const selector = `[data-distribution-row="${input.dataset.distributionRow}"][data-distribution-field="${field}"]`;
    const replacement = els.lineDistributionBody.querySelector(selector);
    replacement?.focus();
    replacement?.setSelectionRange?.(replacement.value.length, replacement.value.length);
  }

  async function saveLineDistribution() {
    const line = distributionSourceLine();
    if (!line) return;
    const errors = distributionDraftErrors(line);
    if (errors.length) {
      els.lineDistributionError.textContent = errors[0];
      els.lineDistributionError.hidden = false;
      return;
    }
    line.sub_lines = state.lineDistributionDraft.map((row) => ({
      ...row,
      parent_line_id: line.line_id,
      ccusto: String(row.ccusto || '').trim(), project_ccusto: String(row.ccusto || '').trim(),
      registration: String(row.registration || '').trim(), matricula: String(row.registration || '').trim(),
      qty: distributionOptionalNumber(row.qty), net_amount: distributionOptionalNumber(row.net_amount),
      percentage: distributionOptionalNumber(row.percentage),
      unit_price: Number(line.unit_price || 0), tax_rate: distributionOptionalNumber(row.tax_rate),
      unit: line.unit || '', date: line.date || line.data || '', article_ref: line.article_ref || line.article || '',
    }));
    const distinctProjects = [...new Set(line.sub_lines.map((row) => row.ccusto).filter(Boolean))];
    const distinctVehicles = [...new Set(line.sub_lines.map((row) => row.registration).filter(Boolean))];
    line.ccusto = distinctProjects.length === 1 ? distinctProjects[0] : '';
    line.project_ccusto = line.ccusto;
    line.registration = distinctVehicles.length === 1 ? distinctVehicles[0] : '';
    line.matricula = line.registration;
    markLineManualFields(line, 'sub_lines', 'ccusto', 'project_ccusto', 'registration', 'matricula');
    if (line.group_role === 'principal') {
      groupMembers(line).forEach((member) => {
        if (member === line) return;
        applyPrincipalDistribution(line, member);
      });
    }
    closeLineDistributionModal();
    renderLines(state.documentData.lines || [], state.documentData.currency || '');
    updateSubmitPhcButton();
    await saveAdjustedLines('Distribuição guardada.');
  }

  function closeLineCostsModal() {
    state.lineCostsTargetIndex = null;
    state.lineCostsType = '';
    els.lineCostsModal?.classList.remove('sz_is_open');
    els.lineCostsModal?.setAttribute('aria-hidden', 'true');
  }

  function selectedLineCosts() {
    const line = state.documentData?.lines?.[state.lineCostsTargetIndex];
    const costs = Array.isArray(line?.detailed_costs) ? line.detailed_costs : [];
    return state.lineCostsType ? costs.filter((row) => row.cost_type === state.lineCostsType) : costs;
  }

  function renderLineCosts() {
    const rows = selectedLineCosts();
    const line = state.documentData?.lines?.[state.lineCostsTargetIndex] || {};
    const sum = rows.reduce((total, row) => total + Number(row.net_amount ?? row.pt ?? 0), 0);
    const expected = Number(line.net_amount ?? line.pt ?? 0);
    const family = state.lineCostsType === 'included' ? 'Custos Incluídos' : 'Custos Adicionais';
    els.lineCostsContext.textContent = `${family}: ${formatMoney(sum, state.documentData?.currency)} · Total da linha: ${formatMoney(expected, state.documentData?.currency)} · Diferença: ${formatMoney(expected - sum, state.documentData?.currency)}`;
    els.lineCostsList.hidden = false;
    els.lineCostsDetail.hidden = true;
    els.lineCostsTabs.querySelectorAll('[data-line-cost-type]').forEach((button) => {
      button.classList.toggle('is-active', button.dataset.lineCostType === state.lineCostsType);
      button.setAttribute('aria-selected', button.dataset.lineCostType === state.lineCostsType ? 'true' : 'false');
    });
    els.lineCostsBody.innerHTML = rows.map((row, index) => `<tr data-line-cost-detail="${index}" tabindex="0" title="Abrir detalhe do custo">
      <td>${escapeHtml(row.description || row.product || row.produto || '')}</td>
      <td>${escapeHtml(formatEditableAmount(row.quantity ?? row.qty))}</td>
      <td>${escapeHtml(row.unit || row.unidade || '')}</td>
      <td>${escapeHtml(formatEditableAmount(row.unit_price))}</td>
      <td>${escapeHtml(formatEditableAmount(row.net_amount ?? row.pt))}</td>
      <td>${escapeHtml(row.reference || row.transaction_id || '')}</td>
      <td>${escapeHtml(String(row.date || row.data || '').slice(0, 10))}</td>
    </tr>`).join('');
  }

  function openLineCosts(lineIndex) {
    const line = state.documentData?.lines?.[Number(lineIndex)];
    if (!line || !Array.isArray(line.detailed_costs) || !line.detailed_costs.length || !els.lineCostsModal) return;
    state.lineCostsTargetIndex = Number(lineIndex);
    const included = line.detailed_costs.filter((row) => row.cost_type === 'included').length;
    const additional = line.detailed_costs.filter((row) => row.cost_type === 'additional').length;
    state.lineCostsType = included && additional ? 'included' : (included ? 'included' : 'additional');
    els.lineCostsTitle.textContent = line.description || 'Custos detalhados';
    els.lineCostsContext.textContent = [
      included ? `${included} Custos Incluídos` : '',
      additional ? `${additional} Custos Adicionais` : '',
    ].filter(Boolean).join(' · ');
    els.lineCostsTabs.hidden = !(included && additional);
    els.lineCostsTabs.innerHTML = included && additional
      ? '<button type="button" role="tab" data-line-cost-type="included">Custos Incluídos</button><button type="button" role="tab" data-line-cost-type="additional">Custos Adicionais</button>'
      : '';
    renderLineCosts();
    els.lineCostsModal.classList.add('sz_is_open');
    els.lineCostsModal.setAttribute('aria-hidden', 'false');
    window.setTimeout(() => els.lineCostsCloseTop?.focus(), 0);
  }

  function showLineCostDetail(index) {
    const row = selectedLineCosts()[Number(index)];
    if (!row) return;
    const labels = {
      transaction_id: 'ID estável', date: 'Data', data: 'Data', location: 'Local', local: 'Local',
      product: 'Produto', produto: 'Produto', quantity: 'Quantidade', qty: 'Quantidade',
      unit: 'Unidade', unidade: 'Unidade', unit_price: 'PU', net_amount: 'PT', pt: 'PT',
      registration: 'Matrícula', matricula: 'Matrícula', ccusto: 'CdC', tax_rate: 'IVA',
    };
    const source = row.original && typeof row.original === 'object' ? {...row.original, ...row} : row;
    els.lineCostsDetailFields.innerHTML = Object.entries(source)
      .filter(([key, value]) => labels[key] && value !== null && value !== undefined && value !== '')
      .map(([key, value]) => `<div><dt>${escapeHtml(labels[key])}</dt><dd>${escapeHtml(value)}</dd></div>`).join('');
    els.lineCostsList.hidden = true;
    els.lineCostsDetail.hidden = false;
    els.lineCostsBack?.focus();
  }

  function formatBcLabel(origin) {
    const number = String(origin?.origin_number || origin?.number || '').trim();
    const year = String(origin?.origin_year || origin?.year || '').trim();
    if (!number) return 'NdE';
    return `NdE N.º ${number}${year ? ` · ${year}` : ''}`;
  }

  function associatedBcOrigins() {
    return state.selectedOrigins.map((selected) => (
      state.originCandidates.find((candidate) => candidate.stamp === selected.stamp) || selected
    )).filter((origin) => origin?.document_type === 'purchase_order' || [102, 119, 129, 130].includes(Number(origin?.ndos || 0)));
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

  function selectedPrimaryOriginFamilies() {
    return new Set(state.selectedOrigins.map(originFamily).filter((family) => ['bc', 'contract', 'subcontract'].includes(family)));
  }

  function originDisplayStage(stageKey) {
    if (['purchase_order', 'contract', 'subcontract_contract'].includes(stageKey)) return stageKey;
    if (stageKey === 'subcontract') return 'subcontract_contract';
    if (stageKey === 'delivery_note' || stageKey === 'virtual_delivery_note') return 'delivery_note';
    if (stageKey === 'subcontract_measurement') return 'work_situation';
    return stageKey;
  }

  function lineOriginLinks(line, family = '') {
    const links = [];
    const visit = (item) => {
      (item?.phc_origin_links || []).forEach((link) => {
        const linkFamily = String(link.origin_family || '');
        if (!family || linkFamily === family) links.push(link);
      });
      if ((!family || family === 'bc') && (item?.bc_allocations || []).length) {
        item.bc_allocations.forEach((allocation) => links.push({
          origin_family: 'bc', bostamp: allocation.origin_stamp || '', bistamp: allocation.origin_line_stamp || '',
          origin_number: allocation.origin_number || '',
        }));
      }
      if ((!family || family === 'delivery_note') && String(item?.origin_delivery_note_number || '').trim()) {
        links.push({ origin_family: 'delivery_note', origin_number: item.origin_delivery_note_number });
      }
      (item?.sub_lines || []).forEach(visit);
    };
    visit(line);
    return links;
  }

  function originControlInfo(line, family, singular, plural) {
    const links = lineOriginLinks(line, family);
    const unique = new Set(links.map((link) => String(
      link.bostamp || link.origin_stamp || link.origin_number || link.bistamp || link.origin_line_stamp || ''
    )).filter(Boolean));
    const count = unique.size;
    return {
      count,
      tooltip: count ? `${count} ${count === 1 ? singular : plural}` : 'Associar Origem',
    };
  }

  function compactOriginControl(line, lineIndex, family, singular, plural) {
    const info = originControlInfo(line, family, singular, plural);
    return `<button type="button" class="docai-origin-compact-control${info.count ? ' is-associated' : ''}" data-line-bc="${lineIndex}" title="${escapeHtml(info.tooltip)}" aria-label="${escapeHtml(info.tooltip)}"><i class="fa-solid ${info.count ? 'fa-link' : 'fa-link-slash'}"></i></button>`;
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
    if (!isIntersol) {
      els.gedFolderSelect.hidden = true;
      els.gedFolderTrigger.hidden = false;
      return;
    }
    els.gedFolderTrigger.hidden = false;

    const suggestion = suggestIntersolGedFolder(state.documentData);
    if (!state.gedFolderManuallySelected && suggestion) {
      customer.ged_folder = suggestion.value;
      customer.ged_folder_suggested_by = suggestion.reason;
    }
    const selectedFolder = customer.ged_folder || '';
    const placeholder = document.createElement('option');
    placeholder.value = '';
    placeholder.textContent = 'Associar';
    els.gedFolderSelect.replaceChildren(placeholder, ...intersolGedFolders.map((option) => {
      const element = document.createElement('option');
      element.value = option.value;
      element.textContent = option.label.replace('INTERSOL ', '');
      element.selected = option.value === selectedFolder;
      return element;
    }));
    placeholder.selected = !selectedFolder;
    const selectedLabel = intersolGedFolders.find((option) => option.value === selectedFolder)?.label;
    if (selectedLabel && els.customerName) els.customerName.textContent = selectedLabel;
    els.gedFolderTrigger.innerHTML = selectedFolder
      ? '<i class="fa-solid fa-pen"></i><span>Alterar agência</span>'
      : 'Associar agência';
    els.gedFolderTrigger.setAttribute('aria-label', selectedFolder
      ? `Alterar agência ${selectedLabel}` : 'Associar agência INTERSOL');
    els.gedFolderHint.textContent = state.gedFolderManuallySelected
      ? 'Destino escolhido manualmente'
      : (customer.ged_folder_suggested_by || (selectedFolder ? 'Agência definida pela entidade' : 'Falta a agência.'));
  }

  function gedPeriodFolders() {
    const sourceDate = String(state.documentData?.document_date || '').trim();
    const now = /^\d{4}-\d{2}-\d{2}$/.test(sourceDate)
      ? new Date(`${sourceDate}T12:00:00`)
      : new Date();
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
    const incompleteDistribution = (documentData.lines || []).some((line) => (
      Array.isArray(line.sub_lines) && line.sub_lines.length && distributionDraftErrors(line, line.sub_lines).length
    ));
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
        || incompleteDistribution
        || isAccountingPending;
      els.workflowValidateBtn.dataset.view = state.view;
      els.workflowValidateBtn.title = incompleteDistribution
        ? 'Completa a distribuição das linhas antes de validar.'
        : isAccountingPending
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
      els.controlOkBtn.disabled = !ready || incompleteDistribution || state.submittingControl || state.controlOk || state.integratedPhc;
      els.controlOkBtn.title = ready
        ? (state.controlOk ? 'Controlo OK concluído.' : 'Confirmar o controlo do documento.')
        : 'Identifica a sociedade, o fornecedor, o número e as linhas do documento.';
      els.controlOkBtn.innerHTML = state.submittingControl
        ? '<i class="fa-solid fa-circle-notch fa-spin"></i><span>A confirmar...</span>'
        : state.controlOk
          ? '<i class="fa-solid fa-circle-check"></i><span>Controlo OK</span>'
          : '<i class="fa-solid fa-clipboard-check"></i><span>Controlo OK</span>';
    }
    els.submitPhcBtn.disabled = !ready || incompleteDistribution || (isProvisionalInvoice && !state.controlOk) || state.submittingPhc || state.integratedPhc;
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
    const normalizedDocumentType = String(documentData.document_type || '').trim().toLowerCase();
    const docType = normalizedDocumentType && normalizedDocumentType !== 'unknown'
      ? (typeLabels[normalizedDocumentType] || documentData.document_type)
      : '';
    const displayedNumber = documentData.document_type === 'mail'
      ? documentData.mail_title
      : documentData.document_number;
    const invoiceType = ['invoice', 'provisional_invoice'].includes(documentData.document_type)
      ? invoiceTypeLabels[String(documentData.invoice_type || '').toLowerCase()]
      : '';
    const editable = !state.readOnly && state.view === 'home' && !state.workflow?.reception_validated;
    const text = (field, value, fallback) => editable
      ? `<button type="button" class="docai-header-editable" data-header-edit="${field}">${escapeHtml(value || fallback)}</button>`
      : escapeHtml(value || fallback);
    const editing = state.headerEditing;
    const forbiddenManualTypes = new Set(['unknown', 'proforma_invoice', 'provisional_invoice', 'other']);
    const documentTypes = Object.entries(typeLabels).filter(([key]) => !forbiddenManualTypes.has(key))
      .map(([key, label]) => `<option value="${key}" ${documentData.document_type === key ? 'selected' : ''}>${escapeHtml(label)}</option>`).join('');
    const invoiceTypes = Object.entries(invoiceTypeLabels)
      .map(([key, label]) => `<option value="${key}" ${documentData.invoice_type === key ? 'selected' : ''}>${escapeHtml(label)}</option>`).join('');
    const isInvoice = ['invoice', 'provisional_invoice'].includes(documentData.document_type);
    const parts = [
      editing === 'document_type' ? `<select class="sz_select docai-header-inline-input" data-header-input="document_type">${documentTypes}</select>` : text('document_type', docType, 'Tipo de documento'),
      ...(isInvoice || editing === 'document_type' ? [editing === 'invoice_type' ? `<select class="sz_select docai-header-inline-input" data-header-input="invoice_type">${invoiceTypes}</select>` : text('invoice_type', invoiceType, 'Tipo de fatura')] : []),
      editing === 'document_number' ? `<input class="sz_input docai-header-inline-input" data-header-input="document_number" value="${escapeHtml(displayedNumber || '')}">` : text('document_number', displayedNumber, 'Nº do documento'),
      editing === 'document_date' ? `<input class="sz_input docai-header-inline-input" data-header-input="document_date" value="${escapeHtml(documentData.document_date ? formatDate(documentData.document_date) : '')}" placeholder="DD/MM/AAAA">` : text('document_date', documentData.document_date ? formatDate(documentData.document_date) : '', 'Data do documento'),
    ];
    els.documentSummary.innerHTML = parts.join('<span class="docai-header-separator"> · </span>');
    const editor = els.documentSummary.querySelector('[data-header-input]');
    if (editor && editing === 'document_date' && window.flatpickr) window.flatpickr(editor, {
      dateFormat: 'd/m/Y', allowInput: true, defaultDate: documentData.document_date || null,
      locale: window.flatpickr.l10ns?.pt || { firstDayOfWeek: 1 },
      onReady: (_, __, instance) => {
        if (instance.calendarContainer.querySelector('.docai-calendar-actions')) return;
        const actions = document.createElement('div');
        actions.className = 'docai-calendar-actions';
        const clear = document.createElement('button');
        clear.type = 'button'; clear.textContent = 'Limpar';
        clear.addEventListener('click', () => { instance.clear(); editor.value = ''; });
        const today = document.createElement('button');
        today.type = 'button'; today.textContent = 'Hoje';
        today.addEventListener('click', () => { instance.setDate(new Date(), true, 'd/m/Y'); });
        actions.append(clear, today);
        instance.calendarContainer.append(actions);
      },
    });
    if (editor) window.setTimeout(() => editor.focus(), 0);
    if (state.correspondenceReference) {
      els.correspondenceReference.textContent = `Correspondência n.º ${state.correspondenceReference} · ${state.correspondenceYear}`;
    } else {
      els.correspondenceReference.textContent = 'Correspondência por criar';
    }
  }

  async function saveHeaderField(field, value) {
    const data = state.documentData;
    if (!data) return;
    if (field === 'document_date') {
      const match = String(value || '').trim().match(/^(\d{2})\/(\d{2})\/(\d{4})$/);
      if (!match) return showMessage('Indica a data no formato DD/MM/AAAA.', 'error');
      value = `${match[3]}-${match[2]}-${match[1]}`;
    }
    if (field === 'document_type') {
      const leavingInvoice = ['invoice', 'provisional_invoice'].includes(data.document_type) && !['invoice', 'provisional_invoice'].includes(value) && data.invoice_type;
      if (leavingInvoice && !window.confirm('Ao alterar o tipo de documento será removido o tipo de fatura. Continuar?')) return;
      state.confirmInvoiceTypeRemoval = Boolean(leavingInvoice);
      data.document_type = value;
      if (leavingInvoice) data.invoice_type = 'unknown';
    } else data[field] = value;
    data._manual_fields = [...new Set([...(data._manual_fields || []), field])];
    state.headerEditing = '';
    renderDocumentCard();
    renderGedDestination();
    const saved = await scheduleAnalysisSave({ immediate: true });
    state.confirmInvoiceTypeRemoval = false;
    if (!saved) {
      state.headerEditing = field;
      renderDocumentCard();
      renderGedDestination();
      setStatus('Erro ao guardar', true);
      showMessage('Erro ao guardar. A edição foi mantida para repetires a gravação.', 'error');
      return;
    }
    await refreshHeaderDependencies();
  }

  async function refreshHeaderDependencies() {
    if (!state.currentDocumentId || !state.documentData) return;
    const [, preflight] = await Promise.allSettled([
      loadCorrespondenceReference(),
      fetchJson(`/api/document_ai/documents/${encodeURIComponent(state.currentDocumentId)}/workflow/preflight`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ view: state.view, document: state.documentData }),
      }),
    ]);
    if (preflight.status === 'fulfilled') {
      state.headerPreflight = preflight.value;
      const duplicates = Array.isArray(preflight.value?.duplicates) ? preflight.value.duplicates : [];
      state.duplicateMatches = duplicates;
      if (duplicates.length) openDuplicateModal(duplicates);
    }
    renderDocumentCard();
    renderGedDestination();
    updateSubmitPhcButton();
  }

  async function loadCorrespondenceReference() {
    const integration = state.integrationResult || {};
    state.correspondenceReference = Number(integration.reference || 0) || null;
    state.correspondenceYear = Number(integration.year || 0) || null;
    if (state.readOnly) {
      renderDocumentCard();
      renderGedDestination();
      updateSubmitPhcButton();
      return;
    }
    state.correspondenceYear ||= new Date().getFullYear();
    if (!state.correspondenceReference && state.documentData?.customer?.feid) {
      const year = Number(String(state.documentData.document_date || '').slice(0, 4)) || new Date().getFullYear();
      try {
        const preview = await fetchJson('/api/document_ai/correspondence/next-reference', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ customer: state.documentData.customer || {}, year }),
        });
        if (preview?.available) {
          state.correspondenceReference = Number(preview.reference || 0) || null;
          state.correspondenceYear = Number(preview.year || year);
        }
      } catch (_) {
        setStatus('Não foi possível obter o próximo número de correspondência.', true);
      }
    }
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
    els.fileMeta.innerHTML = `<span class="docai-file-meta-name" title="${escapeHtml(file.name)}">${escapeHtml(file.name)}</span><span class="docai-file-meta-separator"> · </span><span class="docai-file-meta-size">${escapeHtml(formatFileSize(file.size))}</span>`;
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
    state.deliveryNoteDistributionMode = false;
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
    const manualHeaderFields = Array.isArray(documentData._manual_fields) ? documentData._manual_fields : [];
    if (manualHeaderFields.length) {
      snapshot.header = Object.fromEntries(
        manualHeaderFields.map((field) => [field, structuredClone(documentData[field])]),
      );
      snapshot.header_fields = [...manualHeaderFields];
    }
    if ((documentData.lines || []).some((line) => line?.group_id || (line?.sub_lines || []).length || (line?.detailed_costs || []).length)) {
      snapshot.manual_line_layout = structuredClone(documentData.lines);
    }
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
    return snapshot.header || snapshot.customer || snapshot.supplier || snapshot.origin_project_manually_selected
      || snapshot.origin_project_manually_cleared || snapshot.manual_line_layout || snapshot.lines.length ? snapshot : null;
  }

  function applyManualOverrides(documentData, snapshot) {
    if (!snapshot) return documentData;
    const merged = structuredClone(documentData || {});
    if (snapshot.header) {
      Object.assign(merged, structuredClone(snapshot.header));
      merged._manual_fields = [...new Set([
        ...(merged._manual_fields || []), ...(snapshot.header_fields || Object.keys(snapshot.header)),
      ])];
    }
    if (snapshot.manual_line_layout) merged.lines = structuredClone(snapshot.manual_line_layout);
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
    else if (status === 'error') setStatus('Erro ao guardar', true);
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
    if (state.readOnly || state.view === 'accounting') return Promise.resolve(true);
    if (!state.currentDocumentId || !state.documentData || state.draftConflict) return Promise.resolve(false);
    state.draftRevision += 1;
    window.clearTimeout(state.draftTimer);
    setDraftStatus('saving');
    if (immediate) return flushAnalysisSave();
    state.draftTimer = window.setTimeout(() => flushAnalysisSave(), 450);
    return Promise.resolve(true);
  }

  async function flushAnalysisSave() {
    if (state.readOnly || state.view === 'accounting') return true;
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
      body: JSON.stringify({ expected_version: state.draftVersion, view: state.view, confirm_invoice_type_removal: state.confirmInvoiceTypeRemoval, document: snapshot }),
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
    state.deliveryNoteDistributionMode = false;
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
          phc_integration: detail.phc_integration || cached.phc_integration || {},
          archive_snapshot: detail.archive_snapshot || null,
        });
      }
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

  function renderLines(lines, currency) {
    const items = ensureLineIdentities(Array.isArray(lines) ? lines : []);
    const createdDeliveryNumbers = new Set(
      state.selectedOrigins
        .filter((origin) => (
          String(origin.origin_family || origin.document_type || '').trim() === 'delivery_note'
          && String(origin.delivery_note_number || '').trim()
        ))
        .map((origin) => String(origin.delivery_note_number).trim()),
    );
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
      created: createdDeliveryNumbers.has(group.number),
    }));
    const availableDeliveryNotes = new Set(
      state.deliveryNoteGroups.filter((group) => !group.created).map((group) => group.number),
    );
    state.selectedDeliveryNoteGroups = new Set(
      [...state.selectedDeliveryNoteGroups].filter((number) => availableDeliveryNotes.has(number)),
    );
    if (!state.selectedDeliveryNoteGroups.size) {
      state.deliveryNoteGroups
        .filter((group) => !group.created)
        .forEach((group) => state.selectedDeliveryNoteGroups.add(group.number));
    }
    state.virtualDeliveryNotesActive = state.deliveryNoteGroups.length > 0;
    Array.from(state.selectedSplitLines).forEach((line) => {
      if (!items.includes(line)) state.selectedSplitLines.delete(line);
    });
    const proportionalGroups = state.deliveryNoteGroups.filter((group) => (
      Number(group.base_quantity || 0) > 0 && state.selectedDeliveryNoteGroups.has(group.number)
    ));
    const primaryFamilies = selectedPrimaryOriginFamilies();
    const primaryFamily = selectedPrimaryOriginFamily() || 'bc';
    const hasDeliveryNoteColumn = Boolean(primaryFamilies.has('bc') || primaryFamilies.has('contract')) && state.virtualDeliveryNotesActive;
    const hasWorkSituationColumn = primaryFamilies.has('subcontract');
    const primaryHead = document.getElementById('docAiExtractPrimaryOriginHead');
    const secondaryHead = document.getElementById('docAiExtractSecondaryOriginHead');
    if (primaryHead) primaryHead.textContent = 'Princ.';
    if (secondaryHead) {
      secondaryHead.textContent = 'Assoc.';
      secondaryHead.classList.remove('is-empty');
    }
    const canDistributeDeliveryNotes = state.virtualDeliveryNotesActive && proportionalGroups.length > 0;
    els.splitLineBtn.hidden = !canDistributeDeliveryNotes;
    els.splitLineBtn.disabled = !canDistributeDeliveryNotes || (state.deliveryNoteDistributionMode && state.selectedSplitLines.size === 0);
    els.splitLineBtn.innerHTML = state.deliveryNoteDistributionMode
      ? '<i class="fa-solid fa-floppy-disk"></i><span>Guardar distribuição GdR</span>'
      : `<i class="fa-solid fa-code-branch"></i><span>${proportionalGroups.length === 1 ? 'Distribuir Guia de Remessa' : `Distribuir ${proportionalGroups.length} Guias de Remessa`}</span>`;
    els.lineCount.textContent = countLabel(items.length, 'linha', 'linhas');
    if (!items.length) {
      els.linesBody.innerHTML = '<tr><td colspan="12" class="sz_text_muted">Não foram encontradas linhas comerciais visíveis.</td></tr>';
      return;
    }
    const mappedItems = items.map((line, lineIndex) => {
      const costCenter = String(line.ccusto || line.project_ccusto || state.selectedProject?.ccusto || '').trim();
      const registration = String(line.registration || line.matricula || '').trim();
      const groupKey = String(line.group_id || '') || `${costCenter}\u0000${registration}`;
      return { line, lineIndex, costCenter, registration, groupKey };
    });
    const displayItems = items.some((line) => String(line.group_id || '')) ? mappedItems : mappedItems.sort((left, right) => (
      left.costCenter.localeCompare(right.costCenter, 'pt', { sensitivity: 'base' })
      || left.registration.localeCompare(right.registration, 'pt', { sensitivity: 'base' })
      || left.lineIndex - right.lineIndex
    ));
    const validationTitle = (condition, title) => condition ? ` title="${escapeHtml(title)}"` : '';
    const validationClass = (condition) => condition ? ' docai-validation-field-error' : '';
    els.linesBody.innerHTML = displayItems.map(({ line, lineIndex, groupKey }, displayIndex) => {
      const groupStart = displayIndex === 0 || displayItems[displayIndex - 1].groupKey !== groupKey;
      const selectedForSplit = state.selectedSplitLines.has(line);
      const subLines = Array.isArray(line.sub_lines) ? line.sub_lines : [];
      const distinctProjects = [...new Set(subLines.map((row) => String(row.ccusto || row.project_ccusto || '').trim()).filter(Boolean))];
      const distinctVehicles = [...new Set(subLines.map((row) => String(row.registration || row.matricula || '').trim()).filter(Boolean))];
      const detailedCosts = Array.isArray(line.detailed_costs) ? line.detailed_costs : [];
      const directProject = String(line.ccusto || line.project_ccusto || state.selectedProject?.ccusto || '').trim();
      const project = distinctProjects.length > 1 ? `${distinctProjects.length} CdC` : (distinctProjects[0] || directProject);
      const groupRole = String(line.group_role || '');
      const memberCount = groupMembers(line).length;
      const registration = distinctVehicles.length === 1 ? distinctVehicles[0] : String(line.registration || line.matricula || '').trim();
      const vehicleInvalid = Boolean(registration) && Boolean(
        line.vehicle_not_found || line.vehicle_invalid || line.registration_valid === false
      );
      const effectivePrimaryFamily = primaryFamily || 'bc';
      const validation = state.validationVisible ? {
        article: state.validationMissing.has('article') && !String(line.article_ref || line.article || '').trim(),
        description: state.validationMissing.has('description') && !String(line.description || '').trim(),
        quantity: state.validationMissing.has('quantity') && (line.qty === null || line.qty === undefined || line.qty === ''),
        unitPrice: state.validationMissing.has('unit_price') && (line.unit_price === null || line.unit_price === undefined || line.unit_price === ''),
        total: state.validationMissing.has('line_total') && (line.net_amount === null || line.net_amount === undefined || line.net_amount === ''),
        value: Number.isFinite(Number(line.qty)) && Number.isFinite(Number(line.unit_price)) && Number.isFinite(Number(line.net_amount))
          && Math.abs((Number(line.qty) * Number(line.unit_price)) - Number(line.net_amount)) > 0.01,
        project: state.validationMissing.has('project') && !project,
        vehicle: (state.validationMissing.has('vehicle') && Boolean(line.vehicle_required) && !registration) || vehicleInvalid,
        date: state.validationMissing.has('date') && !String(line.date || line.data || state.documentData?.document_date || '').trim(),
        distribution: state.validationMissing.has('delivery_note') && !String(line.origin_delivery_note_number || '').trim(),
      } : {};
      const lineError = Object.values(validation).some(Boolean);
      const originIncomplete = selectedPrimaryOriginFamilies().size > 0
        && lineOriginLinks(line, effectivePrimaryFamily).length === 0;
      const validationTone = groupRole === 'associated' || line._virtual_split_allocation
        ? 'docai-validation-subline-error'
        : 'docai-validation-primary-line-error';
      const vehicleTooltip = distinctVehicles.length > 1 ? `${distinctVehicles.length} Matrículas` : (vehicleInvalid ? canonicalValidationTooltips.invalidRegistration : canonicalValidationTooltips.vehicleAssociated);
      const vehicleCell = registration || distinctVehicles.length
        ? `<button type="button" class="docai-extract-vehicle-btn is-selected" data-line-vehicle="${lineIndex}" title="${escapeHtml(vehicleTooltip)}" aria-label="${escapeHtml(vehicleTooltip)}"><i class="fa-solid fa-car"></i></button>`
        : `<button type="button" class="docai-extract-vehicle-btn is-empty" data-line-vehicle="${lineIndex}" title="${canonicalValidationTooltips.vehicleToAssociate}" aria-label="${canonicalValidationTooltips.vehicleToAssociate}"></button>`;
      const lineDate = String(line.date || line.data || '').trim().slice(0, 10);
      const currencyCode = String(currency || '').trim().toUpperCase();
      const currencySuffix = /^[A-Z]{3}$/.test(currencyCode)
        ? `<span class="docai-extract-line-currency">${escapeHtml(currencyCode)}</span>`
        : '';
      const primaryNames = effectivePrimaryFamily === 'contract'
        ? ['Contrato', 'Contratos']
        : effectivePrimaryFamily === 'subcontract'
          ? ['Contrato Sub.Emp.', 'Contratos Sub.Emp.']
          : ['NdE', 'NdE'];
      const primaryReference = compactOriginControl(line, lineIndex, effectivePrimaryFamily, ...primaryNames);
      const secondaryFamily = hasWorkSituationColumn ? 'work_situation' : 'delivery_note';
      const secondaryNames = secondaryFamily === 'work_situation' ? ['SdTSub.Emp.', 'SdTSub.Emp.'] : ['GdR', 'GdR'];
      const secondaryCell = state.deliveryNoteDistributionMode && hasDeliveryNoteColumn
        ? `<td class="docai-extract-line-picker-cell"><input type="checkbox" class="docai-extract-bl-selector" data-line-select="${lineIndex}" role="checkbox" aria-label="Selecionar para distribuir por Guia de Remessa" aria-checked="${selectedForSplit ? 'true' : 'false'}" ${selectedForSplit ? 'checked' : ''} ${line._virtual_split_allocation ? 'disabled' : ''}></td>`
        : `<td class="docai-origin-secondary-cell">${hasDeliveryNoteColumn || hasWorkSituationColumn ? compactOriginControl(line, lineIndex, secondaryFamily, ...secondaryNames) : ''}</td>`;
      const includedCount = detailedCosts.filter((cost) => cost.cost_type === 'included').length;
      const additionalCount = detailedCosts.filter((cost) => cost.cost_type === 'additional').length;
      const costTooltip = [
        includedCount ? `${includedCount} Custos Incluídos` : '',
        additionalCount ? `${additionalCount} Custos Adicionais` : '',
      ].filter(Boolean).join(' · ');
      const costInfoCell = detailedCosts.length
        ? `<button type="button" class="docai-line-costs-trigger" data-line-costs="${lineIndex}" title="${escapeHtml(costTooltip)}" aria-label="${escapeHtml(costTooltip)}"><i class="fa-solid fa-circle-info"></i></button>`
        : '';
      return `<tr draggable="false" data-line-index="${lineIndex}" data-line-id="${escapeHtml(line.line_id)}" data-group-role="${escapeHtml(groupRole)}" class="${line._virtual_split_allocation ? 'is-split-allocation ' : ''}${groupRole ? `docai-line-group-${groupRole} ` : ''}${groupStart ? 'docai-extract-line-group-start ' : ''}${originIncomplete ? 'docai-origin-line-incomplete ' : ''}${lineError ? `docai-validation-line-error ${validationTone}` : ''}"${validationTitle(lineError || originIncomplete || line.informative || line.is_informative, lineError ? (validation.value || validation.total ? 'Valor não Conforme' : validation.article ? 'Artigo não Conforme' : validation.vehicle ? 'Falta Matrícula' : validation.project ? 'Falta Centro de Custo' : validation.distribution ? 'Falta Distribuição' : 'Valor não Conforme') : originIncomplete ? 'Confirma o dossier, a linha PHC e a quantidade de origem.' : 'Linha Ignorada')}>
        <td class="docai-line-group-zone"><button type="button" class="docai-line-group-handle${state.keyboardGroupLineId === line.line_id ? ' is-armed' : ''}" draggable="true" data-line-group-handle="${escapeHtml(line.line_id)}" title="Arrastar para agrupar" aria-label="Arrastar para agrupar"><i class="fa-solid fa-grip-vertical" aria-hidden="true"></i></button>${groupRole === 'principal' ? `<span class="docai-line-group-count">${memberCount} linhas</span>` : ''}</td>
        <td><button type="button" class="docai-extract-cell-link${validationClass(validation.article)}" data-line-article="${lineIndex}" title="${validation.article ? 'Artigo não Conforme' : 'Selecionar artigo'}">${escapeHtml(line.article_ref || line.article || 'Selecionar artigo')}</button></td>
        <td><input class="sz_input docai-extract-line-description-input${validationClass(validation.description)}" data-line-description="${lineIndex}" value="${escapeHtml(line.description || '')}" aria-label="Designação da linha"${validationTitle(validation.description, 'Valor não Conforme')}></td>
        <td><input class="sz_input docai-extract-line-number-input${validationClass(validation.quantity)}" inputmode="decimal" data-line-qty="${lineIndex}" value="${escapeHtml(formatEditableAmount(line.qty))}" aria-label="Quantidade"${validationTitle(validation.quantity, 'Valor não Conforme')}></td>
        <td><span class="docai-extract-line-money-input"><input class="sz_input docai-extract-line-number-input${validationClass(validation.unitPrice)}" inputmode="decimal" data-line-unit-price="${lineIndex}" value="${escapeHtml(formatEditableAmount(line.unit_price))}" aria-label="Preço unitário"${validationTitle(validation.unitPrice, 'Valor não Conforme')}>${currencySuffix}</span></td>
        <td><span class="docai-extract-line-money-input"><input class="sz_input docai-extract-line-number-input${validationClass(validation.total || validation.value)}" inputmode="decimal" data-line-total="${lineIndex}" value="${escapeHtml(formatEditableAmount(line.net_amount))}" aria-label="Preço total"${validationTitle(validation.total || validation.value, 'Valor não Conforme')}>${currencySuffix}</span></td>
        <td><input class="sz_input docai-extract-line-number-input" inputmode="decimal" data-line-tax-rate="${lineIndex}" value="${escapeHtml(formatEditableAmount(line.tax_rate))}" aria-label="Taxa de IVA"></td>
        <td><button type="button" class="docai-extract-cell-link${validationClass(validation.project)}" data-line-project="${lineIndex}" title="${validation.project ? 'Falta Centro de Custo' : 'Selecionar CdC'}">${escapeHtml(project || 'Selecionar CdC')}</button></td>
        <td><input type="date" class="sz_input docai-extract-line-date-input${validationClass(validation.date)}" data-line-date="${lineIndex}" value="${escapeHtml(lineDate)}" aria-label="Data da linha"${validationTitle(validation.date, 'Valor não Conforme')}></td>
        <td class="docai-extract-bc-ref-cell">${primaryReference}</td>
        ${secondaryCell}
        <td class="docai-line-costs-cell">${costInfoCell}</td>
        <td class="docai-extract-vehicle-cell${validationClass(validation.vehicle)}"${validationTitle(validation.vehicle, 'Falta Matrícula')}>${vehicleCell}</td>
      </tr>`;
    }).join('');
    window.setTimeout(refreshValidationHighlights, 0);
  }

  function applyReadOnlyState() {
    const analysisReadOnly = state.readOnly || state.view === 'accounting';
    if (!analysisReadOnly || !pageRoot) return;
    pageRoot.querySelectorAll('input, select, textarea').forEach((control) => {
      control.disabled = true;
      control.setAttribute('aria-readonly', 'true');
    });
    els.results?.querySelectorAll('button').forEach((control) => {
      control.disabled = true;
      control.setAttribute('aria-disabled', 'true');
    });
    [els.customerCard, els.supplierCard, els.projectCard].forEach((card) => {
      if (!card) return;
      card.removeAttribute('tabindex');
      card.removeAttribute('role');
      card.setAttribute('aria-disabled', 'true');
    });
    if (els.splitLineBtn) els.splitLineBtn.hidden = true;
    if (state.readOnly && els.status) {
      els.status.textContent = 'Consulta do Arquivo';
      els.status.hidden = false;
    }
  }

  function renderTaxes(taxes, currency) {
    const sourceItems = Array.isArray(taxes) ? taxes : [];
    const grouped = new Map();
    sourceItems.forEach((tax) => {
      const rate = Number(tax?.tax_rate || 0);
      const technicalKey = [
        rate.toFixed(6),
        String(tax?.tax_code || tax?.code || ''),
        String(tax?.regime || tax?.tax_type || ''),
        String(tax?.exemption_reason || ''),
      ].join('|');
      const current = grouped.get(technicalKey) || {
        ...tax,
        tax_rate: rate,
        taxable_base: 0,
        tax_amount: 0,
        gross_total: 0,
      };
      current.taxable_base += Number(tax?.taxable_base || 0);
      current.tax_amount += Number(tax?.tax_amount || 0);
      current.gross_total += Number(tax?.gross_total || 0);
      grouped.set(technicalKey, current);
    });
    const items = [...grouped.values()];
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
      els.supplierCard.setAttribute('aria-label', 'Associar ou escrever remetente');
      els.supplierHint.hidden = true;
      return;
    }
    els.supplierNo.hidden = false;
    els.supplierNo.textContent = `Nº fornecedor: ${supplierNumberLabel || '--'}`;
    els.supplierCard.classList.toggle('is-unmatched', !matched);
    els.supplierCard.classList.toggle('is-matched', matched);
    els.supplierHint.innerHTML = matched
      ? '<i class="fa-solid fa-pen"></i> Alterar fornecedor'
      : '<i class="fa-solid fa-hand-pointer"></i> Associar Fornecedor';
    els.supplierCard.setAttribute('aria-label', matched ? 'Alterar Fornecedor' : 'Associar Fornecedor');
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
    els.customerCard.setAttribute('aria-label', matched ? 'Alterar Entidade' : 'Associar Entidade');
    els.customerHint.innerHTML = matched
      ? '<i class="fa-solid fa-pen"></i> Alterar entidade'
      : '<i class="fa-solid fa-hand-pointer"></i> Associar Entidade';
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
    if (!state.documentData || state.readOnly || state.view !== 'home') return;
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
    renderOriginContextAction();
    if (!options.skipLineMapping) applyOriginLineReferences(payload);

    const primaryFamilies = selectedPrimaryOriginFamilies();
    const hasExplicitDeliveryNotes = state.virtualDeliveryNotesActive && state.deliveryNoteGroups.length > 0;
    const virtualStageHtml = (primaryFamilies.has('bc') || primaryFamilies.has('contract')) && hasExplicitDeliveryNotes ? renderVirtualDeliveryNoteStage() : '';

    if (!payload.available) {
      els.originMeta.hidden = false;
      els.originTabs.hidden = true;
      els.originTabs.innerHTML = '';
      els.originMeta.textContent = virtualStageHtml
        ? `${countLabel(state.deliveryNoteGroups.length, 'Guia de Remessa identificada', 'Guias de Remessa identificadas')} na fatura, ainda por criar no PHC.`
        : payload.message || 'Não foi possível procurar origens no PHC.';
      const unavailableHtml = `<div class="docai-extract-origin-unavailable"><i class="fa-solid fa-circle-info"></i><span>${escapeHtml(payload.message || 'Pesquisa PHC indisponível.')}</span></div>`;
      els.originFlow.innerHTML = `${virtualStageHtml}${unavailableHtml}`;
      return;
    }

    const sourceStages = (Array.isArray(payload.stages) ? payload.stages : []).map((stage) => ({
      ...stage,
      candidates: Array.isArray(stage.candidates) ? [...stage.candidates] : [],
    }));
    const selectedProformas = state.selectedOrigins.filter((origin) => (
      String(origin.document_type || '').toLowerCase() === 'proforma_invoice' || Number(origin.ndos || 0) === 218
    ));
    if (selectedProformas.length) {
      let proformaStage = sourceStages.find((stage) => originDisplayStage(String(stage.key || '')) === 'proforma_invoice');
      if (!proformaStage) {
        proformaStage = { key: 'proforma_invoice', label: 'Pré-Fatura', candidates: [] };
        sourceStages.push(proformaStage);
      }
      proformaStage.candidates = selectedProformas.map((selected) => (
        proformaStage.candidates.find((candidate) => candidate.stamp === selected.stamp) || selected
      ));
    }
    const stages = sourceStages
      .filter((stage) => Array.isArray(stage.candidates) && stage.candidates.length)
      .filter((stage) => {
        const displayStage = originDisplayStage(String(stage.key || ''));
        if (['purchase_order', 'contract', 'subcontract_contract'].includes(displayStage)) return true;
        if (displayStage === 'proforma_invoice') return selectedProformas.length > 0;
        if (displayStage === 'delivery_note') return (primaryFamilies.has('bc') || primaryFamilies.has('contract')) && hasExplicitDeliveryNotes;
        if (displayStage === 'work_situation') return primaryFamilies.has('subcontract');
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
        const consulted = state.consultedOriginStamp === candidate.stamp;
        const score = Number(candidate.score || 0);
        const scoreLabel = score > 0 ? `${Math.round(score * 100)}%` : '';
        const dateLabel = candidate.date ? formatDate(candidate.date) : '';
        const hasTotal = candidate.total !== null && candidate.total !== undefined && candidate.total !== '';
        const totalLabel = hasTotal ? formatMoney(candidate.total, state.documentData?.currency) : '';
        const canAssociate = originDisplayStage(String(stage.key || '')) !== 'proforma_invoice'
          && candidate.selectable !== false && candidate.available_balance !== false;
        return `
          <article class="docai-extract-origin-candidate${consulted ? ' is-selected' : ''}${associated ? ' is-associated' : ''}" data-origin-index="${candidateIndex}" ${state.readOnly ? 'aria-readonly="true"' : `role="button" tabindex="0" aria-label="Consultar ${escapeHtml(stage.label || 'origem')} ${escapeHtml(candidate.number || '')}"`}>
            <span class="docai-extract-origin-candidate-top">
              <strong>${candidate.number ? `N.º ${escapeHtml(candidate.number)}${candidate.year ? ` · ${escapeHtml(candidate.year)}` : ''}` : '&nbsp;'}</strong>
              ${canAssociate ? `<button type="button" class="docai-origin-link-button${associated ? ' is-associated' : ''}" data-origin-link="${candidateIndex}" aria-label="${associated ? 'Desassociar' : 'Selecionar origem'}" title="${associated ? 'Desassociar' : 'Selecionar origem'}"><i class="fa-solid ${associated ? 'fa-link-slash' : 'fa-link'}"></i></button>` : ''}
            </span>
            <strong class="docai-origin-card-score">${escapeHtml(scoreLabel) || '&nbsp;'}</strong>
            <span>${escapeHtml(dateLabel) || '&nbsp;'}</span>
            <strong class="docai-origin-card-total">${escapeHtml(totalLabel) || '&nbsp;'}</strong>
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

    els.originFlow.innerHTML = stageHtml || `<div class="docai-extract-origin-unavailable"><i class="fa-solid fa-magnifying-glass"></i><span>${escapeHtml(payload.no_selectable_reason || 'Sem documentos anteriores disponíveis para ligar.')}</span></div>`;
    const tabStages = stages.map((stage) => ({
      key: originDisplayStage(String(stage.key || '')),
      label: String(stage.label || stage.key || ''),
    }));
    if (virtualStageHtml) {
      const virtualIndex = Math.max(0, tabStages.findIndex((stage) => ['delivery_note', 'purchase_order'].includes(stage.key)));
      tabStages.splice(virtualIndex, 0, { key: 'delivery_note', label: 'GdR', count: state.deliveryNoteGroups.length });
    }
    renderOriginTabs(tabStages.filter((stage, index, items) => items.findIndex((item) => item.key === stage.key) === index));
    renderOriginContextAction();
  }

  function originContextAction() {
    const stage = state.activeOriginStage;
    const selected = state.selectedOrigins.find((origin) => originDisplayStage(String(origin.document_type || origin.key || '')) === stage);
    if (stage === 'purchase_order') {
      return selected
        ? { key: 'correct_purchase_order', label: 'Corrigir Nota de Encomenda', origin: selected }
        : { key: 'create_purchase_order', label: 'Criar Nota de Encomenda' };
    }
    if (stage === 'contract') return selected
      ? { key: 'correct_contract', label: 'Corrigir Contrato', origin: selected }
      : { key: 'create_contract', label: 'Criar Contrato' };
    if (stage === 'subcontract_contract') return selected
      ? { key: 'correct_subcontract', label: 'Corrigir Contrato Sub.Emp.', origin: selected }
      : { key: 'create_subcontract', label: 'Criar Contrato Sub.Emp.' };
    if (stage === 'delivery_note') {
      return state.selectedDeliveryNoteGroups.size > 1
        ? { key: 'distribute_delivery_note', label: 'Distribuir GdR' }
        : state.selectedDeliveryNoteGroups.size === 1
          ? { key: 'create_delivery_note', label: 'Criar GdR' }
          : null;
    }
    if (stage === 'work_situation') return {
      key: 'create_work_situation', label: 'Criar STSE',
      contract: state.selectedOrigins.find((origin) => String(origin.origin_family || '') === 'subcontract'),
    };
    return null;
  }

  function renderOriginContextAction() {
    if (!els.originAction) return;
    const action = originContextAction();
    const allowedByIntegration = action?.key !== 'create_delivery_note'
      || els.originAction.dataset.canDeliveryNote === '1';
    const available = Boolean(
      action && allowedByIntegration && state.view === 'management'
      && !state.readOnly && originActionHandlers.has(action.key)
    );
    els.originAction.hidden = !available;
    els.originAction.textContent = available ? action.label : '';
    els.originAction.dataset.originAction = available ? action.key : '';
  }

  window.registerDocumentAiOriginAction = (key, handler) => {
    const cleanKey = String(key || '').trim();
    if (!cleanKey || typeof handler !== 'function') return;
    originActionHandlers.set(cleanKey, handler);
    renderOriginContextAction();
  };

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
        purchase_order: 'NdE',
        delivery_note: 'GdR',
        proforma_invoice: 'Pré-Fatura',
        contract: 'Contrato',
        subcontract_contract: 'Contrato Sub.Emp.',
        work_situation: 'SdTSub.Emp.',
        subcontract_measurement: 'SdTSub.Emp.',
      };
      const label = officialLabels[stage.key] || stage.label;
      return `<button type="button" class="docai-extract-origin-tab${active ? ' is-active' : ''}" role="tab" data-origin-tab="${escapeHtml(stage.key)}" aria-selected="${active ? 'true' : 'false'}">${escapeHtml(label)}</button>`;
    }).join('');
    els.originFlow.querySelectorAll('[data-origin-stage]').forEach((panel) => {
      panel.hidden = panel.dataset.originStage !== state.activeOriginStage;
    });
    renderOriginContextAction();
  }

  function applyOriginLineReferences(payload = {}) {
    const candidatePool = (Array.isArray(payload.stages) ? payload.stages : [])
      .flatMap((stage) => Array.isArray(stage.candidates) ? stage.candidates : []);
    // Candidates and their line matches are proposals only. A user must first
    // associate the dossier and then explicitly confirm each PHC line/quantity.
    const selected = state.selectedOrigins;
    const selectedCandidates = selected.map((origin) => {
      const candidate = candidatePool.find((item) => item.stamp === origin.stamp);
      return candidate || origin;
    });
    const matches = selectedCandidates.flatMap((origin) => (Array.isArray(origin.line_matches) ? origin.line_matches : []).map((match) => ({
      ...match,
      origin_stamp: origin.stamp || '',
      origin_number: origin.number || '',
      origin_year: origin.year || null,
      origin_family: originFamily(origin),
      origin_reference_label: `${origin.stage_label || 'Origem'} ${origin.number || ''}${origin.year ? ` / ${origin.year}` : ''}`.trim(),
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
    state.originLineageChanged = false;
    state.originLineReferenceLabel = selectedCandidates.map((origin) => `${origin.stage_label || 'Origem'} ${origin.number || ''}`).join(', ');
    if (state.documentData?.lines) renderLines(state.documentData.lines, state.documentData.currency || '');
  }

  function renderVirtualDeliveryNoteStage() {
    if (!state.virtualDeliveryNotesActive || !state.deliveryNoteGroups.length) return '';
    const cards = state.deliveryNoteGroups.map((group) => {
      const checked = state.selectedDeliveryNoteGroups.has(group.number);
      return `
        <label class="docai-extract-origin-proposal${group.created ? ' is-linked' : ''}">
          <input type="checkbox" data-virtual-bl="${escapeHtml(group.number)}" ${checked ? 'checked' : ''} ${group.created ? 'disabled' : ''}>
          <strong>GdR ${escapeHtml(group.number)}</strong>
          <span>${group.created ? 'Criada no PHC' : escapeHtml(countLabel(group.line_count, 'linha', 'linhas'))}</span>
        </label>`;
    }).join('');
    const pendingCount = state.deliveryNoteGroups.filter((group) => !group.created).length;
    return `
      <article class="docai-extract-origin-stage is-virtual-stage" data-origin-stage="delivery_note">
        <div class="docai-extract-origin-stage-title">
          <strong>${pendingCount ? `${pendingCount} ${pendingCount === 1 ? 'Guia de Remessa a criar' : 'Guias de Remessa a criar'}` : 'Guias de Remessa criadas'}</strong>
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
    state.deliveryNoteDistributionMode = false;
    renderLines(state.documentData.lines, state.documentData.currency || '');
    if (state.originPayload && state.virtualDeliveryNotesActive) {
      renderOriginCandidates(state.originPayload, { skipLineMapping: true });
    }
    els.splitLineBtn.disabled = true;
    setStatus(`A guardar ${countLabel(selectedLines.length, 'linha', 'linhas')} por ${countLabel(targetGroups.length, 'Guia de Remessa', 'Guias de Remessa')}...`);
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
        state.deliveryNoteDistributionMode = true;
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
    setStatus(`${countLabel(selectedLines.length, 'linha repartida', 'linhas repartidas')} proporcionalmente. ${allocationSummary}`);
    showMessage(`${countLabel(selectedLines.length, 'linha distribuída', 'linhas distribuídas')} por ${countLabel(targetGroups.length, 'Guia de Remessa', 'Guias de Remessa')} sem alterar os totais.`, 'success');
  }

  function toggleDeliveryNoteDistribution() {
    if (!state.deliveryNoteDistributionMode) {
      state.deliveryNoteDistributionMode = true;
      state.selectedSplitLines = new Set();
      renderLines(state.documentData?.lines || [], state.documentData?.currency || '');
      setStatus('Seleciona as linhas pelos círculos e guarda a distribuição GdR.');
      return;
    }
    distributeSelectedLinesAcrossDeliveryNotes();
  }

  async function loadOriginCandidates(documentData) {
    const token = ++state.originSearchToken;
    state.originPayload = null;
    state.originCandidates = [];
    state.selectedOrigins = [];
    els.originLoading.hidden = false;
    els.originFlow.hidden = true;
    if (els.originAction) els.originAction.hidden = true;
    els.originMeta.textContent = 'A procurar documentos anteriores no PHC...';
    try {
      if (documentData?.document_type === 'credit_note' && state.view === 'accounting' && state.currentDocumentId) {
        const payload = await fetchJson(`/api/document_ai/documents/${encodeURIComponent(state.currentDocumentId)}/credit-note/origins?view=accounting`, {
          method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ document: documentData || {} }),
        });
        if (token !== state.originSearchToken) return;
        renderCreditNoteOrigins(payload);
        return;
      }
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

  function effectiveCreditLines() {
    const rows = [];
    ensureLineIdentities();
    (state.documentData?.lines || []).forEach((line) => {
      const children = Array.isArray(line.sub_lines) && line.sub_lines.length ? line.sub_lines
        : (Array.isArray(line.sublines) && line.sublines.length ? line.sublines : null);
      if (children) children.forEach((child) => rows.push(child));
      else rows.push(line);
    });
    return rows;
  }

  function renderCreditNoteOrigins(payload = {}) {
    state.creditNoteCandidates = Array.isArray(payload.candidates) ? payload.candidates : [];
    const storedFo = String(payload.mapping?.original_fostamp || '');
    state.creditNoteSelectedFo = storedFo || state.creditNoteSelectedFo;
    els.originLoading.hidden = true;
    els.originFlow.hidden = false;
    els.originTabs.hidden = true;
    els.originMeta.hidden = false;
    els.originMeta.textContent = 'Seleciona manualmente a FO original e uma FN para cada linha. Nenhuma proposta é aplicada automaticamente.';
    if (!state.creditNoteCandidates.length) {
      els.originFlow.innerHTML = '<div class="docai-extract-origin-unavailable"><span>Não foram encontradas compras anteriores deste fornecedor.</span></div>';
      return;
    }
    const lines = effectiveCreditLines();
    els.originFlow.innerHTML = state.creditNoteCandidates.map((candidate, candidateIndex) => {
      const selected = candidate.fostamp === state.creditNoteSelectedFo;
      const mappings = selected ? lines.map((line, index) => {
        const lineId = String(line.subline_id || line.line_id || line.id || `line-${index + 1}`);
        const selectedFn = String(line.credit_origin_fnstamp || '');
        const options = (candidate.lines || []).map((originLine) => `<option value="${escapeHtml(originLine.fnstamp)}" ${originLine.fnstamp === selectedFn ? 'selected' : ''}>${escapeHtml(originLine.ref || 'Sem artigo')} · ${escapeHtml(originLine.design || '')} · ${escapeHtml(formatEditableAmount(Math.abs(Number(originLine.etiliquido || 0))))}</option>`).join('');
        return `<label class="docai-extract-origin-proposal"><span>${escapeHtml(line.description || `Linha ${index + 1}`)}</span><select data-credit-line="${escapeHtml(lineId)}"><option value="">Selecionar FN original…</option>${options}</select></label>`;
      }).join('') : '';
      return `<article class="docai-extract-origin-candidate${selected ? ' is-selected' : ''}">
        <label><input type="radio" name="credit-original-fo" data-credit-fo="${candidateIndex}" ${selected ? 'checked' : ''}> <strong>${escapeHtml(candidate.docnome || 'Compra')} ${escapeHtml(candidate.adoc || '')}</strong> · ${escapeHtml(String(candidate.docdata || ''))}</label>
        ${selected ? `<div class="docai-extract-origin-proposals">${mappings}<button type="button" class="sz_button sz_button_primary" data-credit-save>Guardar associação</button></div>` : ''}
      </article>`;
    }).join('');
  }

  async function saveCreditNoteMapping() {
    const candidate = state.creditNoteCandidates.find((item) => item.fostamp === state.creditNoteSelectedFo);
    if (!candidate) return;
    const mappings = [...els.originFlow.querySelectorAll('[data-credit-line]')].map((select) => ({
      portal_line_id: select.dataset.creditLine, fnstamp: select.value,
    }));
    if (mappings.some((item) => !item.fnstamp)) {
      showMessage('Seleciona uma FN original para cada linha da Nota de Crédito.', 'warning');
      return;
    }
    try {
      const payload = await fetchJson(`/api/document_ai/documents/${encodeURIComponent(state.currentDocumentId)}/credit-note/mapping?view=accounting`, {
        method: 'PUT', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ original_fostamp: candidate.fostamp, mappings }),
      });
      state.documentData = payload.document || state.documentData;
      state.draftVersion = String(payload.version || state.draftVersion || '');
      showMessage(payload.message || 'Origem guardada.', 'success');
      await loadOriginCandidates(state.documentData);
    } catch (error) {
      showMessage(error.message || 'Não foi possível guardar a origem.', 'error');
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
      if (state.originLineageChanged) {
        await saveAdjustedLines('Filiação PHC das linhas guardada.');
        state.originLineageChanged = false;
      }
      await pruneLineBcAllocations();
      renderLines(state.documentData?.lines || [], state.documentData?.currency || '');
      renderProjectCard();
      const mappedLineCount = new Set(state.originLineMatches.map((match) => Number(match.document_line_index))).size;
      setStatus(isPurchaseOrder
        ? `${payload.message || 'Seleção de origem atualizada.'} ${countLabel(mappedLineCount, 'linha tem proposta', 'linhas têm propostas')}; confirma o dossier, a linha PHC e a quantidade em cada linha.`
        : `${payload.message || 'Seleção de origem atualizada.'} Confirma a linha PHC e a quantidade em cada linha.`);
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
    state.originOperation = null;
    if (els.originDetailValidate) {
      els.originDetailValidate.hidden = true;
      els.originDetailValidate.disabled = false;
    }
    els.originDetailModal?.classList.remove('sz_is_open');
    els.originDetailModal?.querySelector('.docai-origin-detail-modal')?.classList.remove('is-purchase-order-operation');
    els.originDetailModal?.setAttribute('aria-hidden', 'true');
    if (els.originDetailClose) els.originDetailClose.textContent = 'Fechar';
  }

  async function openOriginDetail(index) {
    const candidate = state.originCandidates[Number(index)];
    if (!candidate || !state.currentDocumentId || !els.originDetailModal) return;
    state.consultedOriginStamp = candidate.stamp || '';
    els.originDetailModal?.querySelector('.docai-origin-detail-modal')?.classList.remove('is-purchase-order-operation');
    state.originOperation = null;
    if (els.originDetailClose) els.originDetailClose.textContent = 'Fechar';
    if (els.originDetailValidate) els.originDetailValidate.hidden = true;
    renderOriginCandidates({ ...(state.originPayload || {}), selected_origins: state.selectedOrigins }, { skipLineMapping: true });
    const number = candidate.number ? ` n.º ${candidate.number}${candidate.year ? ` · ${candidate.year}` : ''}` : '';
    els.originDetailTitle.textContent = `${candidate.stage_label || 'Origem'}${number}`;
    els.originDetailTitle.title = els.originDetailTitle.textContent;
    if (els.originDetailSubtitle) {
      els.originDetailSubtitle.hidden = true;
      els.originDetailSubtitle.textContent = '';
      els.originDetailSubtitle.title = '';
    }
    els.originDetailLoading.hidden = false;
    els.originDetailTable.hidden = true;
    els.originDetailEmpty.hidden = true;
    els.originDetailModal.classList.add('sz_is_open');
    els.originDetailModal.setAttribute('aria-hidden', 'false');
    try {
      const payload = await fetchJson(`/api/document_ai/documents/${encodeURIComponent(state.currentDocumentId)}/origins/${encodeURIComponent(candidate.stamp)}?view=${encodeURIComponent(state.view)}`);
      const rows = Array.isArray(payload.lines) ? payload.lines : [];
      const origin = payload.origin || candidate;
      const totals = payload.totals || {};
      const lineTotals = payload.line_totals || totals;
      const detailNumber = String(origin.number || '').trim();
      const detailYear = String(origin.year || '').trim();
      els.originDetailTitle.textContent = `${origin.stage_label || candidate.stage_label || 'Origem'}${detailNumber ? ` n.º ${detailNumber}` : ''}${detailYear ? ` · ${detailYear}` : ''}`;
      els.originDetailTitle.title = els.originDetailTitle.textContent;
      if (els.originDetailSubtitle) {
        const subtitleParts = [
          origin.date ? formatDate(origin.date) : '',
          lineTotals.net_total !== null && lineTotals.net_total !== undefined ? `Total s/IVA ${formatMoney(lineTotals.net_total, state.documentData?.currency)}` : '',
          lineTotals.tax_total !== null && lineTotals.tax_total !== undefined ? `IVA ${formatMoney(lineTotals.tax_total, state.documentData?.currency)}` : '',
          lineTotals.gross_total !== null && lineTotals.gross_total !== undefined ? `Total c/IVA ${formatMoney(lineTotals.gross_total, state.documentData?.currency)}` : '',
        ].filter(Boolean);
        els.originDetailSubtitle.textContent = subtitleParts.join(' · ');
        els.originDetailSubtitle.classList.toggle('is-warning', payload.totals_reconciled === false);
        const totalsWarning = payload.totals_reconciled === false
          ? `Totais globais PHC (não reconciliados com estas linhas): s/IVA ${formatMoney(totals.net_total, state.documentData?.currency)} · IVA ${formatMoney(totals.tax_total, state.documentData?.currency)} · c/IVA ${formatMoney(totals.gross_total, state.documentData?.currency)}`
          : '';
        els.originDetailSubtitle.title = [els.originDetailSubtitle.textContent, totalsWarning].filter(Boolean).join(' — ');
        els.originDetailSubtitle.hidden = !subtitleParts.length;
      }
      els.originDetailHead.innerHTML = '<th>Artigo</th><th>Designação</th><th>Quantidade</th><th title="Preço unitário">PU</th><th title="Preço total">PT</th><th>IVA</th><th title="Centro de Custo">CdC</th><th>Data</th><th>Matrícula</th>';
      els.originDetailBody.innerHTML = rows.map((line) => `<tr><td>${escapeHtml(line.article || '')}</td><td title="${escapeHtml(line.description || '')}">${escapeHtml(line.description || '')}</td><td>${escapeHtml(formatNumber(line.quantity))}</td><td>${escapeHtml(formatMoney(line.unit_price, state.documentData?.currency))}</td><td>${escapeHtml(formatMoney(line.line_total, state.documentData?.currency))}</td><td>${line.tax_rate === null || line.tax_rate === undefined || line.tax_rate === '' ? '' : `${escapeHtml(formatNumber(line.tax_rate, 2))}%`}</td><td>${escapeHtml(line.project || '')}</td><td>${line.date ? escapeHtml(formatDate(line.date)) : ''}</td><td>${escapeHtml(line.registration || '')}</td></tr>`).join('');
      els.originDetailLoading.hidden = true;
      els.originDetailTable.hidden = !rows.length;
      els.originDetailEmpty.hidden = Boolean(rows.length);
    } catch (error) {
      els.originDetailSubtitle?.classList.remove('is-warning');
      els.originDetailLoading.hidden = true;
      els.originDetailEmpty.hidden = false;
      els.originDetailEmpty.textContent = error.message || 'Não foi possível consultar a origem no PHC.';
    }
  }

  function purchaseOrderComparisonRows(preview) {
    const current = Array.isArray(preview.current?.lines) ? preview.current.lines : [];
    const proposed = Array.isArray(preview.proposal?.lines) ? preview.proposal.lines : [];
    const fields = ['article', 'description', 'quantity', 'unit', 'unit_price', 'line_total', 'tax_rate', 'project', 'date'];
    const row = (item, source, changed = false) => `<tr class="${changed ? 'docai-origin-comparison-changed' : ''}" title="${escapeHtml(source)}" aria-label="${escapeHtml(source)}">
      <td>${escapeHtml(item.article || '')}</td>
      <td title="${escapeHtml(item.description || '')}">${escapeHtml(item.description || '')}</td>
      <td>${escapeHtml(formatNumber(item.quantity))}</td>
      <td>${escapeHtml(formatMoney(item.unit_price, preview.currency))}</td>
      <td>${escapeHtml(formatMoney(item.line_total, preview.currency))}</td>
      <td>${item.tax_rate === null || item.tax_rate === undefined ? '' : `${escapeHtml(formatNumber(item.tax_rate, 2))}%`}</td>
      <td>${escapeHtml(item.project || '')}</td>
      <td>${item.date ? escapeHtml(formatDate(item.date)) : ''}</td>
      <td>${escapeHtml(item.registration || '')}</td>
    </tr>`;
    if (preview.mode !== 'correct') return proposed.map((item) => row(item, 'Proposto')).join('');
    const output = [];
    const count = Math.max(current.length, proposed.length);
    for (let index = 0; index < count; index += 1) {
      const before = current[index] || {};
      const after = proposed[index] || {};
      const changed = fields.some((field) => String(before[field] ?? '') !== String(after[field] ?? ''));
      if (current[index]) output.push(row(before, 'PHC', changed));
      if (proposed[index]) output.push(row(after, 'Proposto', changed));
    }
    return output.join('');
  }

  async function openPurchaseOrderOperation(action) {
    if (!state.currentDocumentId || !state.documentData || !els.originDetailModal) return;
    if (!await flushAnalysisSave()) {
      showMessage('Guarda primeiro os dados da Análise.', 'error');
      return;
    }
    const family = action?.key?.includes('subcontract') ? 'subcontract'
      : action?.key?.includes('contract') ? 'contract' : 'purchase_order';
    const familyLabel = family === 'subcontract' ? 'Contrato Sub.Emp.'
      : family === 'contract' ? 'Contrato' : 'Nota de Encomenda';
    const originStamp = String(action?.origin?.stamp || '');
    state.originOperation = null;
    if (els.originDetailClose) els.originDetailClose.textContent = 'Cancelar';
    els.originDetailModal.querySelector('.docai-origin-detail-modal')?.classList.add('is-purchase-order-operation');
    els.originDetailTitle.textContent = `${originStamp ? 'Corrigir' : 'Criar'} ${familyLabel}`;
    els.originDetailSubtitle.hidden = true;
    els.originDetailLoading.hidden = false;
    els.originDetailTable.hidden = true;
    els.originDetailEmpty.hidden = true;
    els.originDetailValidate.hidden = true;
    els.originDetailModal.classList.add('sz_is_open');
    els.originDetailModal.setAttribute('aria-hidden', 'false');
    try {
      const previewPath = family === 'purchase_order' ? 'purchase-order/preview' : 'phc-source/preview';
      const preview = await fetchJson(`/api/document_ai/documents/${encodeURIComponent(state.currentDocumentId)}/${previewPath}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ view: state.view, origin_stamp: originStamp, family }),
      });
      state.originOperation = { kind: family, originStamp, snapshot: preview.snapshot || '', submitting: false };
      const currentOrigin = preview.current?.origin || {};
      els.originDetailTitle.textContent = `${familyLabel}${currentOrigin.number ? ` n.º ${currentOrigin.number}${currentOrigin.year ? ` · ${currentOrigin.year}` : ''}` : ''}`;
      els.originDetailTitle.title = els.originDetailTitle.textContent;
      const proposal = preview.proposal || {};
      const parts = [
        state.documentData?.document_date ? formatDate(state.documentData.document_date) : '',
        proposal.net_total !== null && proposal.net_total !== undefined ? `Total s/IVA ${formatMoney(proposal.net_total, preview.currency)}` : '',
        proposal.tax_total !== null && proposal.tax_total !== undefined ? `IVA ${formatMoney(proposal.tax_total, preview.currency)}` : '',
        proposal.gross_total !== null && proposal.gross_total !== undefined ? `Total c/IVA ${formatMoney(proposal.gross_total, preview.currency)}` : '',
      ].filter(Boolean);
      els.originDetailSubtitle.textContent = parts.join(' · ');
      els.originDetailSubtitle.title = els.originDetailSubtitle.textContent;
      els.originDetailSubtitle.hidden = false;
      els.originDetailHead.innerHTML = '<th>Artigo</th><th>Designação</th><th>Quantidade</th><th title="Preço unitário">PU</th><th title="Preço total">PT</th><th>IVA</th><th title="Centro de Custo">CdC</th><th>Data</th><th>Matrícula</th>';
      els.originDetailBody.innerHTML = purchaseOrderComparisonRows(preview);
      els.originDetailLoading.hidden = true;
      els.originDetailTable.hidden = false;
      els.originDetailValidate.hidden = false;
    } catch (error) {
      state.originOperation = null;
      els.originDetailLoading.hidden = true;
      els.originDetailEmpty.hidden = false;
      els.originDetailEmpty.textContent = error.message || `Não foi possível preparar ${familyLabel}.`;
    }
  }

  async function validatePurchaseOrderOperation() {
    const operation = state.originOperation;
    if (!operation || operation.submitting) return;
    const familyLabel = operation.kind === 'subcontract' ? 'Contrato Sub.Emp.'
      : operation.kind === 'contract' ? 'Contrato' : 'Nota de Encomenda';
    operation.submitting = true;
    els.originDetailValidate.disabled = true;
    try {
      const validatePath = operation.kind === 'purchase_order' ? 'purchase-order/validate' : 'phc-source/validate';
      const payload = await fetchJson(`/api/document_ai/documents/${encodeURIComponent(state.currentDocumentId)}/${validatePath}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          view: state.view,
          origin_stamp: operation.originStamp,
          expected_snapshot: operation.snapshot,
          family: operation.kind,
        }),
      });
      closeOriginDetailModal();
      showMessage(payload.message || `${familyLabel} atualizado no PHC.`, 'success');
      setStatus(payload.message || `${familyLabel} atualizado no PHC.`);
      await loadInboxDocument(state.currentDocumentId, { skipGroup: true });
    } catch (error) {
      operation.submitting = false;
      els.originDetailValidate.disabled = false;
      showMessage(error.message || `Não foi possível atualizar ${familyLabel}.`, 'error');
    }
  }

  async function openDeliveryNoteOperation() {
    if (!state.currentDocumentId || !state.documentData || !els.originDetailModal) return;
    const selectedNumbers = [...state.selectedDeliveryNoteGroups].filter(Boolean);
    if (selectedNumbers.length !== 1) {
      showMessage('Seleciona exatamente uma GdR para criar.', 'error');
      return;
    }
    if (!await flushAnalysisSave()) {
      showMessage('Guarda primeiro os dados da Análise.', 'error');
      return;
    }
    const deliveryNumber = selectedNumbers[0];
    state.originOperation = null;
    if (els.originDetailClose) els.originDetailClose.textContent = 'Cancelar';
    els.originDetailModal.querySelector('.docai-origin-detail-modal')?.classList.add('is-purchase-order-operation');
    els.originDetailTitle.textContent = 'GdR';
    els.originDetailSubtitle.hidden = true;
    els.originDetailLoading.hidden = false;
    els.originDetailTable.hidden = true;
    els.originDetailEmpty.hidden = true;
    els.originDetailValidate.hidden = true;
    els.originDetailModal.classList.add('sz_is_open');
    els.originDetailModal.setAttribute('aria-hidden', 'false');
    try {
      const preview = await fetchJson(`/api/document_ai/documents/${encodeURIComponent(state.currentDocumentId)}/delivery-note/preview`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ view: state.view, delivery_note_number: deliveryNumber }),
      });
      state.originOperation = {
        kind: 'delivery_note',
        deliveryNumber: preview.delivery_note_number || deliveryNumber,
        submitting: false,
      };
      els.originDetailTitle.textContent = 'GdR';
      els.originDetailTitle.title = els.originDetailTitle.textContent;
      const parts = [
        state.documentData?.document_date ? formatDate(state.documentData.document_date) : '',
      ].filter(Boolean);
      els.originDetailSubtitle.textContent = parts.join(' · ');
      els.originDetailSubtitle.title = els.originDetailSubtitle.textContent;
      els.originDetailSubtitle.hidden = false;
      els.originDetailHead.innerHTML = '<th>Artigo</th><th>Designação</th><th>Quantidade</th><th title="Preço unitário">PU</th><th title="Preço total">PT</th><th>IVA</th><th title="Centro de Custo">CdC</th><th>Data</th><th>Matrícula</th>';
      els.originDetailBody.innerHTML = (preview.lines || []).map((line) => `
        <tr>
          <td>${escapeHtml(line.article || '')}</td>
          <td title="${escapeHtml(line.description || '')}">${escapeHtml(line.description || '')}</td>
          <td title="Saldo Contrato: ${escapeHtml(formatNumber(line.available_quantity))}">${escapeHtml(formatNumber(line.quantity))}</td>
          <td></td><td></td><td></td><td>${escapeHtml(line.project || '')}</td><td></td><td></td>
        </tr>`).join('');
      els.originDetailLoading.hidden = true;
      els.originDetailTable.hidden = false;
      els.originDetailValidate.hidden = false;
    } catch (error) {
      state.originOperation = null;
      els.originDetailLoading.hidden = true;
      els.originDetailEmpty.hidden = false;
      els.originDetailEmpty.textContent = error.message || 'Não foi possível preparar a GdR.';
    }
  }

  async function validateDeliveryNoteOperation() {
    const operation = state.originOperation;
    if (!operation || operation.kind !== 'delivery_note' || operation.submitting) return;
    operation.submitting = true;
    els.originDetailValidate.disabled = true;
    try {
      const payload = await fetchJson(`/api/document_ai/documents/${encodeURIComponent(state.currentDocumentId)}/delivery-note/validate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          view: state.view,
          delivery_note_number: operation.deliveryNumber,
        }),
      });
      closeOriginDetailModal();
      showMessage(payload.message || 'GdR criada no PHC.', 'success');
      setStatus(payload.message || 'GdR criada no PHC.');
      await loadInboxDocument(state.currentDocumentId, { skipGroup: true });
    } catch (error) {
      operation.submitting = false;
      els.originDetailValidate.disabled = false;
      showMessage(error.message || 'Não foi possível criar a GdR.', 'error');
    }
  }

  async function openWorkSituationOperation(action) {
    if (!state.currentDocumentId || !state.documentData || !els.originDetailModal) return;
    const contractStamp = String(action?.contract?.stamp || '');
    if (!contractStamp) {
      showMessage('Associa primeiro um Contrato Sub.Emp.', 'error');
      return;
    }
    if (!await flushAnalysisSave()) {
      showMessage('Guarda primeiro os dados da Análise.', 'error');
      return;
    }
    state.originOperation = null;
    if (els.originDetailClose) els.originDetailClose.textContent = 'Cancelar';
    els.originDetailTitle.textContent = 'SdTSub.Emp.';
    els.originDetailSubtitle.hidden = true;
    els.originDetailLoading.hidden = false;
    els.originDetailTable.hidden = true;
    els.originDetailEmpty.hidden = true;
    els.originDetailValidate.hidden = true;
    els.originDetailModal.classList.add('sz_is_open');
    els.originDetailModal.setAttribute('aria-hidden', 'false');
    try {
      const preview = await fetchJson(`/api/document_ai/documents/${encodeURIComponent(state.currentDocumentId)}/work-situation/preview`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ view: state.view, contract_stamp: contractStamp }),
      });
      state.originOperation = { kind: 'work_situation', contractStamp, submitting: false };
      const contract = preview.contract || {};
      const proposalLines = preview.proposal?.lines || [];
      const net = proposalLines.reduce((sum, line) => sum + Number(line.line_total || 0), 0);
      const tax = proposalLines.reduce((sum, line) => sum + Number(line.line_total || 0) * Number(line.tax_rate || 0) / 100, 0);
      els.originDetailSubtitle.textContent = [
        state.documentData?.document_date ? formatDate(state.documentData.document_date) : '',
        `Total s/IVA ${formatMoney(net, state.documentData?.currency)}`,
        `IVA ${formatMoney(tax, state.documentData?.currency)}`,
        `Total c/IVA ${formatMoney(net + tax, state.documentData?.currency)}`,
      ].filter(Boolean).join(' · ');
      els.originDetailSubtitle.title = els.originDetailSubtitle.textContent;
      els.originDetailSubtitle.hidden = !els.originDetailSubtitle.textContent;
      els.originDetailHead.innerHTML = '<th>Artigo</th><th>Designação</th><th>Quantidade</th><th title="Preço unitário">PU</th><th title="Preço total">PT</th><th>IVA</th><th title="Centro de Custo">CdC</th><th>Data</th><th>Matrícula</th>';
      els.originDetailBody.innerHTML = (preview.proposal?.lines || []).map((line) => `<tr>
        <td>${escapeHtml(line.article || '')}</td><td title="${escapeHtml(line.description || '')}">${escapeHtml(line.description || '')}</td>
        <td>${escapeHtml(formatNumber(line.quantity))}</td><td>${escapeHtml(formatMoney(line.unit_price, state.documentData?.currency))}</td>
        <td>${escapeHtml(formatMoney(line.line_total, state.documentData?.currency))}</td><td>${escapeHtml(formatNumber(line.tax_rate, 2))}%</td>
        <td>${escapeHtml(line.project || '')}</td><td>${line.date ? escapeHtml(formatDate(line.date)) : ''}</td><td></td></tr>`).join('');
      els.originDetailLoading.hidden = true;
      els.originDetailTable.hidden = false;
      els.originDetailValidate.hidden = false;
    } catch (error) {
      state.originOperation = null;
      els.originDetailLoading.hidden = true;
      els.originDetailEmpty.hidden = false;
      els.originDetailEmpty.textContent = error.message || 'Não foi possível preparar a STSE.';
    }
  }

  async function validateWorkSituationOperation() {
    const operation = state.originOperation;
    if (!operation || operation.kind !== 'work_situation' || operation.submitting) return;
    operation.submitting = true;
    els.originDetailValidate.disabled = true;
    try {
      const payload = await fetchJson(`/api/document_ai/documents/${encodeURIComponent(state.currentDocumentId)}/work-situation/validate`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ view: state.view, contract_stamp: operation.contractStamp }),
      });
      closeOriginDetailModal();
      showMessage(payload.message || 'STSE criada no PHC.', 'success');
      await loadInboxDocument(state.currentDocumentId, { skipGroup: true });
    } catch (error) {
      operation.submitting = false;
      els.originDetailValidate.disabled = false;
      showMessage(error.message || 'Não foi possível criar a STSE.', 'error');
    }
  }

  function validateOriginOperation() {
    if (state.originOperation?.kind === 'delivery_note') return validateDeliveryNoteOperation();
    if (state.originOperation?.kind === 'work_situation') return validateWorkSituationOperation();
    return validatePurchaseOrderOperation();
  }

  window.registerDocumentAiOriginAction('create_purchase_order', openPurchaseOrderOperation);
  window.registerDocumentAiOriginAction('correct_purchase_order', openPurchaseOrderOperation);
  window.registerDocumentAiOriginAction('create_contract', openPurchaseOrderOperation);
  window.registerDocumentAiOriginAction('correct_contract', openPurchaseOrderOperation);
  window.registerDocumentAiOriginAction('create_subcontract', openPurchaseOrderOperation);
  window.registerDocumentAiOriginAction('correct_subcontract', openPurchaseOrderOperation);
  window.registerDocumentAiOriginAction('create_delivery_note', openDeliveryNoteOperation);
  window.registerDocumentAiOriginAction('distribute_delivery_note', toggleDeliveryNoteDistribution);
  window.registerDocumentAiOriginAction('create_work_situation', openWorkSituationOperation);

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
    setStatus(`A separar ${documents.length} documentos independentes no inbox...`);
    const formData = new FormData();
    formData.append('file', state.file);
    formData.append('document_batch', JSON.stringify(batch));
    formData.append('document_data', JSON.stringify(state.documentData || {}));
    formData.append('source_document_id', state.currentDocumentId || '');
    try {
      const payload = await fetchJson('/api/document_ai/extract/split', { method: 'POST', body: formData });
      setStatus(payload.message || 'Documentos separados e adicionados ao inbox.');
      showMessage(payload.message || 'Documentos separados com sucesso.', 'success');
      const firstDocument = (payload.batch_audit?.documents || [])[0];
      if (firstDocument?.id) {
        clearCurrentAnalysis();
        await loadInboxDocument(firstDocument.id, { skipGroup: true });
      }
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
    const projectDetails = [project.name || project.machine, project.client, project.city || project.location].filter(Boolean).join(' · ');
    els.projectMeta.textContent = hasWorkConflict
      ? `Atenção: as origens selecionadas pertencem a ${selectedOriginWorks.length} Centros de Custo (${selectedOriginWorks.join(', ')})`
      : selected
        ? [project.suggested_by_document ? `Sugerido por ${project.suggested_by_document}` : '', projectDetails].filter(Boolean).join(' · ') || 'Centro de Custo associado'
        : '-';
    els.projectHint.innerHTML = hasWorkConflict
      ? '<i class="fa-solid fa-triangle-exclamation"></i> Origens com Centros de Custo diferentes'
      : selected
      ? '<i class="fa-solid fa-pen"></i> Alterar Centro de Custo'
      : '<i class="fa-solid fa-magnifying-glass"></i> Selecionar CdC';
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
    els.projectDistribute.hidden = true;
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
      els.projectList.innerHTML = '<div class="docai-empty-state">Não foram encontrados Centros de Custo com esta pesquisa.</div>';
      return;
    }
    els.projectList.innerHTML = state.projectCandidates.map((project, index) => `
      <button type="button" class="docai-supplier-match-option" data-project-index="${index}">
        <span class="docai-supplier-match-main">
          <strong>${escapeHtml(project.ccusto || '--')}</strong>
          <span>${escapeHtml([project.name, project.client, [project.address, project.city].filter(Boolean).join(' · ')].filter(Boolean).join(' · '))}</span>
        </span>
        <span class="docai-supplier-match-score">Selecionar</span>
      </button>
    `).join('');
  }

  async function searchProjectCandidates() {
    if (!state.documentData?.customer) return;
    els.projectSearchBtn.disabled = true;
    els.projectList.innerHTML = '<div class="docai-empty-state">A procurar Centros de Custo no PHC...</div>';
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
      els.projectContext.textContent = `Centros de Custo de ${state.documentData.customer?.name || 'Entidade'} · ${payload.phc_database || 'PHC'}`;
    } catch (error) {
      els.projectList.innerHTML = `<div class="docai-empty-state">${escapeHtml(error.message || 'Erro ao pesquisar obras.')}</div>`;
    } finally {
      els.projectSearchBtn.disabled = false;
    }
  }

  function openProjectModal() {
    if (state.readOnly || state.view !== 'management') return;
    if (!state.documentData?.customer?.feid && !state.documentData?.customer?.name) {
      showMessage('É necessário identificar primeiro a empresa cliente.', 'error');
      return;
    }
    els.projectSearch.value = state.selectedProject?.ccusto || '';
    els.projectDistribute.hidden = true;
    els.projectContext.textContent = `Centros de Custo de ${state.documentData.customer?.name || 'Entidade'}`;
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
    els.projectDistribute.hidden = false;
    els.projectSearch.value = String(line.ccusto || line.project_ccusto || '').trim();
    els.projectContext.textContent = `Centros de Custo de ${state.documentData.customer?.name || 'Entidade'}`;
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
      detachAssociatedLine(line);
      line.ccusto = selected.ccusto || '';
      line.project_ccusto = selected.ccusto || '';
      line.project_machine = selected.machine || '';
      line.project_location = selected.location || '';
      markLineManualFields(line, 'ccusto', 'project_ccusto', 'project_machine', 'project_location');
      if (line.group_role === 'principal') groupMembers(line).forEach((member) => {
        if (member === line) return;
        member.ccusto = line.ccusto;
        member.project_ccusto = line.project_ccusto;
        member.project_machine = line.project_machine;
        member.project_location = line.project_location;
        (member.sub_lines || []).forEach((child) => {
          child.ccusto = line.ccusto;
          child.project_ccusto = line.project_ccusto;
        });
        markLineManualFields(member, 'ccusto', 'project_ccusto', 'project_machine', 'project_location');
      });
      state.projectTargetLineIndex = null;
      closeProjectModal();
      renderLines(state.documentData.lines || [], state.documentData.currency || '');
      await saveAdjustedLines(`Centro de Custo ${selected.ccusto} guardado na linha.`);
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
    setStatus(`Centro de Custo ${selected.ccusto} aplicado às origens.`);
    await scheduleAnalysisSave({ immediate: true });
    loadOriginCandidates(state.documentData);
  }

  function closeArticleModal() {
    state.articleTargetLineIndex = null;
    els.articleModal.classList.remove('sz_is_open');
    els.articleModal.setAttribute('aria-hidden', 'true');
  }

  function renderArticleCandidates(items, confidence = 'none') {
    state.articleCandidates = Array.isArray(items) ? items : [];
    state.articleSuggestionConfidence = confidence;
    if (!state.articleCandidates.length) {
      els.articleList.innerHTML = '<div class="docai-empty-state">Nenhum artigo encontrado.</div>';
      return;
    }
    els.articleList.innerHTML = state.articleCandidates.map((article, index) => `
      <button type="button" class="docai-supplier-match-option" data-article-index="${index}">
        <span class="docai-supplier-match-main">
          <strong>${escapeHtml(article.ref || '--')}${index === 0 && confidence === 'strong' ? ' · Proposta forte' : ''}</strong>
          <span>${escapeHtml(article.design || 'Sem designação')}</span>
        </span>
        <span class="docai-supplier-match-score">${escapeHtml([
          ...(article.match_reasons || []), article.family, article.unit,
        ].filter(Boolean).join(' · '))}</span>
      </button>
    `).join('');
  }

  async function searchArticleCandidates() {
    if (!state.documentData?.customer) return;
    const line = state.documentData?.lines?.[state.articleTargetLineIndex];
    if (!line) return;
    els.articleSearchBtn.disabled = true;
    els.articleList.innerHTML = '<div class="docai-empty-state">A pesquisar artigos PHC...</div>';
    try {
      const payload = await fetchJson('/api/document_ai/articles/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          customer: state.documentData.customer || {},
          supplier_no: state.documentData.supplier?.supplier_no || state.documentData.supplier?.no || 0,
          line: {
            source_ref: line.source_ref || line.extracted_ref || line.ref || '',
            description: line.description || '',
            unit: line.unit || '',
            unit_price: line.unit_price,
            net_amount: line.net_amount,
            tax_rate: line.tax_rate,
            ccusto: line.ccusto || line.project_ccusto || '',
            origin_article_refs: (line.bc_allocations || []).map((item) => item.article_ref || '').filter(Boolean),
          },
          selected_article_ref: line.article_ref || line.article || '',
          query: els.articleSearch.value.trim(),
          limit: 30,
        }),
      });
      if (line.article_ref && payload.selected_article_valid === false) {
        line.article_ref = '';
        line.article_family = '';
        markLineManualFields(line, 'article_ref', 'article_family');
        renderLines(state.documentData.lines || [], state.documentData.currency || '');
        await saveAdjustedLines('Artigo não encontrado. Escolhe um artigo válido para esta entidade.');
        showMessage('Artigo não encontrado.', 'error');
      }
      renderArticleCandidates(payload.items || [], payload.suggestion_confidence || 'none');
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
    els.articleSearch.value = line.article_ref || line.source_ref || line.extracted_ref || line.ref || line.description || '';
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
    detachAssociatedLine(line);
    const groupedLines = line.group_role === 'principal' ? groupMembers(line) : [line];
    groupedLines.forEach((candidate) => {
      if (!candidate.source_ref) candidate.source_ref = candidate.extracted_ref || candidate.ref || '';
      candidate.article_ref = article.ref || '';
      candidate.article_family = article.family || candidate.article_family || '';
      if (candidate === line && article.unit) candidate.unit = article.unit;
      (candidate.sub_lines || []).forEach((child) => {
        child.article_ref = candidate.article_ref;
        child.article_family = candidate.article_family;
      });
      candidate.article_selection = 'manual';
      markLineManualFields(candidate, 'article_ref', 'article_family', ...(candidate === line ? ['unit'] : []), 'article_selection');
    });
    state.articleTargetLineIndex = null;
    closeArticleModal();
    renderLines(state.documentData.lines || [], state.documentData.currency || '');
    await saveAdjustedLines(line.group_id
      ? `Artigo ${article.ref} guardado no grupo.`
      : `Artigo ${article.ref} guardado na linha.`);
  }

  function closeVehicleModal() {
    state.vehicleTargetLineIndex = null;
    els.vehicleDistribute.hidden = true;
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
        <span class="docai-supplier-match-score">${escapeHtml([vehicle.fleet_number, 'Selecionar'].filter(Boolean).join(' · '))}</span>
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
    els.vehicleDistribute.hidden = false;
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
    detachAssociatedLine(line);
    line.registration = vehicle.registration || '';
    line.matricula = vehicle.registration || '';
    line.vehicle_stamp = vehicle.vehicle_stamp || '';
    line.vehicle_source = 'V_ALL_VA';
    if (!String(line.ccusto || line.project_ccusto || '').trim() && String(vehicle.ccusto || '').trim()) {
      line.ccusto = vehicle.ccusto;
      line.project_ccusto = vehicle.ccusto;
    }
    markLineManualFields(line, 'registration', 'matricula', 'vehicle_stamp', 'vehicle_source', 'ccusto', 'project_ccusto');
    if (line.group_role === 'principal') groupMembers(line).forEach((member) => {
      if (member === line) return;
      member.registration = line.registration;
      member.matricula = line.matricula;
      member.vehicle_stamp = line.vehicle_stamp;
      member.vehicle_source = line.vehicle_source;
      (member.sub_lines || []).forEach((child) => {
        child.registration = line.registration;
        child.matricula = line.matricula;
        child.vehicle_stamp = line.vehicle_stamp;
      });
      markLineManualFields(member, 'registration', 'matricula', 'vehicle_stamp', 'vehicle_source');
    });
    closeVehicleModal();
    renderLines(state.documentData.lines || [], state.documentData.currency || '');
    await saveAdjustedLines(`Viatura ${vehicle.registration} guardada na linha.`);
  }

  async function removeVehicle() {
    const line = state.documentData?.lines?.[state.vehicleTargetLineIndex];
    if (!line) return;
    detachAssociatedLine(line);
    line.registration = '';
    line.matricula = '';
    line.vehicle_stamp = '';
    line.vehicle_source = '';
    markLineManualFields(line, 'registration', 'matricula', 'vehicle_stamp', 'vehicle_source');
    if (line.group_role === 'principal') groupMembers(line).forEach((member) => {
      member.registration = '';
      member.matricula = '';
      member.vehicle_stamp = '';
      member.vehicle_source = '';
      (member.sub_lines || []).forEach((child) => {
        child.registration = '';
        child.matricula = '';
        child.vehicle_stamp = '';
      });
      markLineManualFields(member, 'registration', 'matricula', 'vehicle_stamp', 'vehicle_source');
    });
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

  function allocatedOriginQuantityElsewhere(originStamp, lineStamp, currentLine) {
    let total = 0;
    const visit = (item) => {
      if (item !== currentLine) {
        (item.bc_allocations || []).forEach((allocation) => {
          if (String(allocation.origin_stamp || '') === originStamp
              && String(allocation.origin_line_stamp || '') === lineStamp) {
            total += Number(allocation.quantity || 0);
          }
        });
      }
      (item.sub_lines || item.sublines || []).forEach(visit);
    };
    (state.documentData?.lines || []).forEach(visit);
    return total;
  }

  function renderBcAssignments() {
    const origins = associatedBcOrigins();
    const line = state.documentData?.lines?.[state.bcTargetLineIndex];
    if (!origins.length) {
      els.bcList.innerHTML = '<div class="docai-empty-state">Sem origens associadas.</div>';
      els.bcSave.disabled = true;
      return;
    }
    els.bcSave.disabled = false;
    els.bcList.innerHTML = origins.map((origin) => {
      const stamp = String(origin.stamp || '');
      const label = `${origin.stage_label || origin.document_name || origin.document_type || 'Origem'} ${origin.number || ''}`;
      return relevantBcLines(origin, line, state.bcTargetLineIndex).map((sourceLine) => {
        const lineStamp = String(sourceLine.line_stamp || '');
        if (!lineStamp) return '';
        const saved = (line.bc_allocations || []).find((part) => part.origin_line_stamp === lineStamp && part.origin_stamp === stamp);
        const phcBalance = Number(sourceLine.pending_qty ?? sourceLine.qty ?? 0);
        const allocatedElsewhere = allocatedOriginQuantityElsewhere(stamp, lineStamp, line);
        const available = Math.max(0, phcBalance - allocatedElsewhere);
        return `<label class="docai-bc-assignment-option">
          <span><strong>Dossier: ${escapeHtml(label)}</strong>
            <small>Linha PHC: ${escapeHtml(sourceLine.ref || 'sem referência')} · ${escapeHtml(sourceLine.description || '')}</small>
            <small>${escapeHtml(origin.ccusto || 'Sem CdC')} · Quantidade origem: ${escapeHtml(formatNumber(sourceLine.qty ?? phcBalance))} ${escapeHtml(sourceLine.unit || '')} · Saldo disponível: ${escapeHtml(formatNumber(available))} ${escapeHtml(sourceLine.unit || '')}</small>
          </span>
          <input type="number" min="0" max="${escapeHtml(available)}" step="0.0001"
            class="sz_input docai-origin-quantity" aria-label="Quantidade a distribuir do ${escapeHtml(label)}"
            data-bc-origin-stamp="${escapeHtml(stamp)}" data-bc-line-stamp="${escapeHtml(lineStamp)}"
            value="${escapeHtml(saved?.quantity ?? 0)}">
        </label>`;
      }).join('');
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
    const exactRef = String(documentLine.article_ref || documentLine.article || documentLine.ref || '').trim().toUpperCase();
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
    return selected.length ? selected : officialLines;
  }

  function bindBcLineage(target, allocations) {
    const exact = (allocations || []).filter((allocation) => (
      String(allocation.origin_stamp || '').trim() && String(allocation.origin_line_stamp || '').trim()
    ));
    if (!target || !exact.length) return;
    const nonBc = (target.phc_origin_links || []).filter((link) => String(link.origin_family || '') !== 'bc');
    const links = exact.map((allocation) => ({
      origin_family: 'bc', bostamp: allocation.origin_stamp, bistamp: allocation.origin_line_stamp,
      origin_stamp: allocation.origin_stamp, origin_line_stamp: allocation.origin_line_stamp,
      origin_number: allocation.origin_number || '', origin_year: allocation.origin_year || null,
      origin_line_order: Number(allocation.origin_line_order || 0),
    }));
    target.phc_origin_links = [...nonBc, ...links];
    target.phc_origin_stamp = links[0].bostamp;
    target.phc_origin_line_stamp = links[0].bistamp;
    target.bostamp = links[0].bostamp;
    target.bistamp = links[0].bistamp;
  }

  function applyBcAllocationLineage(line, allocations) {
    const children = Array.isArray(line.sub_lines) ? line.sub_lines : [];
    const clearBc = (target) => {
      const previous = target.phc_origin_links || [];
      const oldBcStamps = new Set(previous.filter((link) => String(link.origin_family || '') === 'bc').map((link) => String(link.bostamp || link.origin_stamp || '')));
      const links = previous.filter((link) => String(link.origin_family || '') !== 'bc');
      target.phc_origin_links = links;
      if (oldBcStamps.has(String(target.phc_origin_stamp || ''))) {
        target.phc_origin_stamp = '';
        target.phc_origin_line_stamp = '';
        target.bostamp = '';
        target.bistamp = '';
      }
    };
    clearBc(line);
    children.forEach(clearBc);
    if (!children.length) {
      bindBcLineage(line, allocations);
      return;
    }
    const unused = [...allocations];
    children.forEach((child) => {
      const quantity = Number(child.qty ?? child.quantity ?? 0);
      let index = unused.findIndex((allocation) => Math.abs(Number(allocation.quantity || 0) - quantity) <= 0.00001);
      if (index < 0 && unused.length) index = 0;
      if (index >= 0) bindBcLineage(child, [unused.splice(index, 1)[0]]);
    });
  }

  async function saveBcAssignments() {
    const lineIndex = state.bcTargetLineIndex;
    const line = state.documentData?.lines?.[lineIndex];
    if (!line) return;
    detachAssociatedLine(line);
    const origins = associatedBcOrigins();
    const allocations = [];
    const inputs = [...els.bcList.querySelectorAll('[data-bc-line-stamp]')];
    if (inputs.some((input) => !input.checkValidity() || !Number.isFinite(Number(input.value)))) {
      showMessage('Confirma as quantidades distribuídas.', 'error');
      return;
    }
    inputs.forEach((input) => {
      const quantity = Number(input.value);
      if (quantity <= 0) return;
      const origin = origins.find((item) => String(item.stamp) === input.dataset.bcOriginStamp);
      const originLine = relevantBcLines(origin, line, lineIndex).find((item) => String(item.line_stamp) === input.dataset.bcLineStamp);
      if (!originLine) return;
      allocations.push({
        origin_stamp: origin.stamp || '',
        origin_number: origin.number || '',
        origin_year: origin.year || null,
        origin_line_stamp: originLine.line_stamp || '',
        origin_line_order: Number(originLine.line_order || 0),
        article_ref: originLine.ref || '',
        quantity,
        unit_price: Number(originLine.unit_price || 0),
        total: quantity * Number(originLine.unit_price || 0),
      });
    });
    const assigned = allocations.reduce((sum, item) => sum + item.quantity, 0);
    if (allocations.length && Math.abs(assigned - Number(line.quantity ?? line.qty ?? 0)) > 0.00001) {
      showMessage('A quantidade distribuída deve coincidir com a quantidade da linha.', 'error');
      return;
    }
    line.bc_allocations = allocations;
    applyBcAllocationLineage(line, allocations);
    markLineManualFields(line, 'bc_allocations', 'phc_origin_links', 'phc_origin_stamp', 'phc_origin_line_stamp', 'bostamp', 'bistamp', 'sub_lines');
    if (line.group_role === 'principal') groupMembers(line).forEach((member) => {
      if (member === line) return;
      inheritPrincipalFields(line, member);
      markLineManualFields(member, 'phc_origin_stamp', 'phc_origin_line_stamp', 'bostamp', 'bistamp');
    });
    if (allocations.length < 2) state.expandedBcLines.delete(lineIndex);
    closeBcModal();
    renderLines(state.documentData.lines || [], state.documentData.currency || '');
    await saveAdjustedLines(allocations.length ? 'Distribuição por origem guardada.' : 'Associação à origem removida.');
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
    setStatus('Centro de Custo removido.');
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
    if (state.readOnly || state.view !== 'home') return;
    const isCorrespondence = ['mail', 'bank_statement'].includes(state.documentData?.document_type);
    const isAdvertising = state.documentData?.document_type === 'advertising';
    const feid = Number(state.matching?.supplier_query?.feid || state.documentData?.customer?.feid || 0);
    if (!feid) {
      showMessage('Não foi possível identificar a entidade na tabela FE.', 'error');
      return;
    }
    const customerName = state.documentData?.customer?.name || `FE ${feid}`;
    const supplier = state.documentData?.supplier || {};
    els.supplierModalTitle.textContent = isCorrespondence ? 'Associar Cliente ou Fornecedor' : 'Associar Fornecedor';
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
    ensureLineIdentities(documentData.lines || []);
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
    state.archiveSnapshot = payload.archive_snapshot || null;
    state.controlOk = Boolean(payload.workflow?.control_ok);
    state.integratedPhc = payload.processing_status === 'provisional_invoice'
      || Boolean(payload.phc_integration?.fostamp || payload.phc_integration?.crstamp || payload.phc_integration?.bostamp);
    state.integrationResult = state.readOnly
      ? (payload.phc_integration || {})
      : (state.integratedPhc ? (payload.phc_integration || {}) : null);
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
    const archivedOrigins = Array.isArray(state.archiveSnapshot?.origins) ? state.archiveSnapshot.origins : [];
    els.originSection.hidden = isCorrespondence || (isReception && !state.readOnly) || (state.readOnly && !archivedOrigins.length);
    els.linesSection.hidden = isCorrespondence || (isReception && !state.readOnly);
    els.notesSection.hidden = true;
    els.persistenceNote.textContent = isMail
      ? 'O correio foi analisado apenas neste ecrã e não foi adicionado ao inbox.'
      : (documentData.document_type === 'bank_statement'
        ? 'O extrato fica no inbox e pode ser integrado como correspondência RB no PHC.'
        : 'O PDF e a leitura ficam guardados no inbox.');
    state.correspondenceReference = null;
    state.correspondenceYear = state.readOnly ? null : new Date().getFullYear();
    renderDocumentCard();
    renderClassificationCard();
    els.legalBadge.hidden = !(isMail && documentData.mail_category === 'legal');
    renderGedDestination();
    loadCorrespondenceReference();
    renderArchiveAudit(state.archiveSnapshot);

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
    if (isCorrespondence) {
      state.originSearchToken += 1;
      state.originPayload = null;
      state.originCandidates = [];
      state.selectedOrigins = [];
    } else if (state.readOnly) {
      renderArchivedOrigins(archivedOrigins);
    } else if (isReception) {
      state.originSearchToken += 1;
      state.originPayload = null;
      state.originCandidates = [];
      state.selectedOrigins = [];
    } else {
      loadOriginCandidates(documentData);
    }
    if (state.currentDocumentId && draftFingerprint() !== serverFingerprint) scheduleAnalysisSave();
    applyReadOnlyState();
  }

  function renderArchiveAudit(snapshot) {
    if (!els.archiveAudit) return;
    els.archiveAudit.hidden = !state.readOnly;
    if (!state.readOnly) return;
    const event = snapshot?.latest_event || {};
    const validated = Boolean(snapshot?.validated);
    const eventLabel = event.event === 'deleted' ? 'Eliminado' : (validated ? 'Validado' : 'Arquivado');
    const actor = event.actor || snapshot?.validated_by || '--';
    const at = event.at || snapshot?.validated_at || '';
    const relationCount = (snapshot?.origins || []).length;
    const operationCount = Object.keys(snapshot?.phc_operations || {}).length;
    const integration = snapshot?.phc_integration || {};
    const relations = [
      relationCount ? `${relationCount} origem${relationCount === 1 ? '' : 's'} PHC` : '',
      operationCount ? `${operationCount} operação${operationCount === 1 ? '' : 'ões'} PHC` : '',
      integration.ged_path || integration.unc_path ? 'PDF no GED' : '',
      integration.fostamp || integration.crstamp || integration.bostamp ? 'relação PHC persistida' : '',
    ].filter(Boolean);
    els.archiveAuditState.textContent = `${eventLabel} · ${workflowViewLabel(snapshot?.view)}`;
    els.archiveAuditActor.textContent = at ? `${actor} · ${formatDate(at)}` : actor;
    els.archiveAuditRelations.textContent = relations.join(' · ') || 'Sem relações externas registadas';
  }

  function renderArchivedOrigins(origins = []) {
    const groups = new Map();
    origins.forEach((origin) => {
      const rawKey = String(origin.document_type || origin.origin_family || origin.key || '');
      const key = originDisplayStage(({ bc: 'purchase_order', proforma_invoice: 'proforma_invoice' })[rawKey] || rawKey);
      if (!groups.has(key)) groups.set(key, []);
      groups.get(key).push({ ...origin, selectable: false });
    });
    const labels = {
      purchase_order: 'Nota de encomenda', delivery_note: 'Guia de remessa',
      proforma_invoice: 'Pré-Fatura', contract: 'Contrato',
      subcontract_contract: 'Contrato Sub.Emp.', work_situation: 'Situação de trabalho',
    };
    renderOriginCandidates({
      available: true,
      selected_origins: origins,
      stages: [...groups.entries()].map(([key, candidates]) => ({ key, label: labels[key] || 'Origem', candidates })),
    });
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
    state.deliveryNoteDistributionMode = false;
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
      if (options.force) state.pendingManualOverrides = null;
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

  const canonicalValidationTooltips = Object.freeze({
    missingVehicle: 'Falta Matrícula',
    missingProject: 'Falta Centro de Custo',
    missingCategory: 'Falta Categoria ADM/LOG',
    missingDistribution: 'Falta Distribuição',
    invalidArticle: 'Artigo não Conforme',
    invalidValue: 'Valor não Conforme',
    duplicate: 'Movimento Duplicado',
    invalidRegistration: 'Matrícula não Conforme',
    ignoredLine: 'Linha Ignorada',
    openSublines: 'Abrir Sublinhas',
    groupLine: 'Agrupar linha',
    ungroupLine: 'Desagrupar linha',
    vehicleToAssociate: 'Selecionar matrícula',
    vehicleAssociated: 'Veículo associado',
  });

  const validationTooltipByCode = {
    project: canonicalValidationTooltips.missingProject,
    article: canonicalValidationTooltips.invalidArticle,
    vehicle: canonicalValidationTooltips.missingVehicle,
    delivery_note: canonicalValidationTooltips.missingDistribution,
    distribution: canonicalValidationTooltips.missingDistribution,
    duplicate: canonicalValidationTooltips.duplicate,
    category: canonicalValidationTooltips.missingCategory,
    description: canonicalValidationTooltips.invalidValue,
    quantity: canonicalValidationTooltips.invalidValue,
    unit_price: canonicalValidationTooltips.invalidValue,
    line_total: canonicalValidationTooltips.invalidValue,
    date: canonicalValidationTooltips.invalidValue,
  };

  const validationTooltipByTarget = {
    docAiExtractProjectCard: canonicalValidationTooltips.missingProject,
    docAiExtractTotalsCard: canonicalValidationTooltips.invalidValue,
  };

  function restoreValidationTarget(element) {
    element.classList.remove('docai-required-missing');
    if (!element.dataset.docaiValidationTitle) return;
    if (element.dataset.docaiPreviousTitle) element.title = element.dataset.docaiPreviousTitle;
    else element.removeAttribute('title');
    delete element.dataset.docaiValidationTitle;
    delete element.dataset.docaiPreviousTitle;
  }

  function clearRequiredInfoHighlights({ resetState = true } = {}) {
    document.querySelectorAll('.docai-required-missing').forEach((element) => {
      restoreValidationTarget(element);
    });
    if (resetState) {
      state.validationVisible = false;
      state.validationMissing = new Set();
    }
  }

  function refreshValidationHighlights() {
    if (!state.validationVisible) return;
    document.querySelectorAll('.docai-required-missing').forEach((element) => {
      const resolved = {
        docAiExtractCustomerCard: Boolean(state.documentData?.customer?.feid),
        docAiExtractSupplierCard: Boolean(state.documentData?.supplier?.supplier_no || state.documentData?.supplier?.no || state.documentData?.supplier_explicitly_absent),
        docAiExtractProjectCard: Boolean(state.selectedProject?.ccusto || ((state.documentData?.lines || []).length && (state.documentData?.lines || []).every((line) => String(line.ccusto || line.project_ccusto || '').trim()))),
        docAiExtractModeCard: Boolean(state.documentData?.document_type && state.documentData.document_type !== 'unknown'),
        docAiExtractOriginSection: Boolean(state.selectedOrigins.length),
        docAiExtractLinesSection: !document.querySelector('.docai-validation-line-error'),
      }[element.id];
      if (resolved === true) restoreValidationTarget(element);
    });
  }

  function showRequiredInfo(requiredInfo) {
    clearRequiredInfoHighlights();
    const targets = Array.isArray(requiredInfo?.targets) ? requiredInfo.targets : [];
    const messages = Array.isArray(requiredInfo?.messages) ? requiredInfo.messages : [];
    const tooltips = Array.isArray(requiredInfo?.tooltips) ? requiredInfo.tooltips : [];
    const missing = Array.isArray(requiredInfo?.missing) ? requiredInfo.missing : [];
    state.validationVisible = true;
    state.validationMissing = new Set(missing);
    renderLines(state.documentData?.lines || [], state.documentData?.currency || '');
    let firstTarget = null;
    targets.forEach((targetId, index) => {
      const target = document.getElementById(targetId);
      if (!target) return;
      target.classList.add('docai-required-missing');
      const codeTooltip = validationTooltipByCode[missing[index]]
        || missing.map((code) => validationTooltipByCode[code]).find(Boolean);
      const message = String(validationTooltipByTarget[targetId] || codeTooltip || tooltips[index] || tooltips[0] || messages[index] || messages[0] || '').trim().replace(/[.]+$/, '');
      if (message) {
        target.dataset.docaiPreviousTitle = target.getAttribute('title') || '';
        target.title = message;
        target.dataset.docaiValidationTitle = 'true';
      }
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
        showRequiredInfo({
          missing: ['duplicate'],
          targets: ['docAiExtractLinesSection'],
          tooltips: ['Movimento Duplicado'],
        });
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
        body: JSON.stringify({
          view: state.view,
          expected_version: state.draftVersion,
          document: state.documentData,
        }),
      });
      showMessage('Documento validado.', 'success');
      window.location.href = inboxUrl();
    } catch (error) {
      if (error.status === 409 || error.payload?.code === 'document_version_conflict') {
        openDraftConflict();
      } else {
        setStatus(error.message || 'Não foi possível validar a etapa.', true);
      }
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
  els.gedFolderTrigger?.addEventListener('click', () => {
    if (els.customerName) els.customerName.textContent = 'INTERSOL';
    els.gedFolderTrigger.hidden = true;
    els.gedFolderSelect.hidden = false;
    els.gedFolderSelect.focus();
  });
  els.gedFolderSelect?.addEventListener('change', async () => {
    if (!state.documentData?.customer || state.readOnly || state.view !== 'home') return;
    state.gedFolderManuallySelected = true;
    state.documentData.customer.ged_folder = els.gedFolderSelect.value;
    state.documentData.customer.ged_folder_manually_selected = true;
    state.documentData.customer.ged_folder_suggested_by = '';
    renderGedDestination();
    els.gedFolderSelect.hidden = true;
    const agency = els.gedFolderSelect.selectedOptions[0]?.textContent || 'Associar';
    setStatus(els.gedFolderSelect.value ? `Agência INTERSOL alterada para ${agency}.` : 'Falta a agência.', !els.gedFolderSelect.value);
    if (!state.currentDocumentId) return;
    try {
      const saved = await scheduleAnalysisSave({ immediate: true });
      if (!saved) throw new Error('save_failed');
      setStatus(`Agência INTERSOL ${agency} guardada.`);
    } catch (error) {
      renderGedDestination();
      els.gedFolderSelect.hidden = false;
      setStatus('Erro ao guardar', true);
    }
  });
  els.gedFolderSelect?.addEventListener('click', (event) => event.stopPropagation());
  els.gedFolderTrigger?.addEventListener('click', (event) => event.stopPropagation());
  els.gedFolderSelect?.addEventListener('blur', () => {
    if (!els.gedFolderSelect.hidden) {
      els.gedFolderSelect.hidden = true;
      configureGedFolderControl();
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
  els.splitLineBtn?.addEventListener('click', toggleDeliveryNoteDistribution);
  els.linesBody?.addEventListener('click', (event) => {
    const lineCosts = event.target.closest('[data-line-costs]');
    if (lineCosts) {
      openLineCosts(Number(lineCosts.dataset.lineCosts));
      return;
    }
    const groupHandle = event.target.closest('[data-line-group-handle]');
    if (groupHandle) {
      const lineId = groupHandle.dataset.lineGroupHandle;
      if (state.keyboardGroupLineId && state.keyboardGroupLineId !== lineId) groupLineOnTarget(state.keyboardGroupLineId, lineId);
      else {
        state.keyboardGroupLineId = state.keyboardGroupLineId === lineId ? '' : lineId;
        els.linesBody.querySelectorAll('[data-line-group-handle].is-armed').forEach((item) => item.classList.remove('is-armed'));
        groupHandle.classList.toggle('is-armed', Boolean(state.keyboardGroupLineId));
        if (state.keyboardGroupLineId) setStatus('Seleciona a linha de destino para agrupar. Delete desagrupa a linha atual.');
      }
      return;
    }
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
  els.linesBody?.addEventListener('keydown', (event) => {
    const handle = event.target.closest('[data-line-group-handle]');
    if (!handle) return;
    if (['Delete', 'Backspace'].includes(event.key)) {
      event.preventDefault();
      ungroupLine(handle.dataset.lineGroupHandle);
    } else if (event.key === 'Escape') {
      state.keyboardGroupLineId = '';
      handle.classList.remove('is-armed');
    }
  });
  els.linesBody?.addEventListener('dragstart', (event) => {
    const handle = event.target.closest('[data-line-group-handle]');
    if (!handle) { event.preventDefault(); return; }
    state.draggedLineId = handle.dataset.lineGroupHandle;
    event.dataTransfer.effectAllowed = 'move';
    event.dataTransfer.setData('text/plain', state.draggedLineId);
    const dragged = (state.documentData?.lines || []).find((line) => line.line_id === state.draggedLineId);
    els.groupDropzone.textContent = dragged?.group_role === 'principal' ? 'Desfazer grupo' : 'Retirar linha do grupo';
    els.groupDropzone.hidden = false;
  });
  els.linesBody?.addEventListener('dragover', (event) => {
    const target = event.target.closest('tr[data-line-id]');
    if (!state.draggedLineId || !target) return;
    event.preventDefault();
    event.dataTransfer.dropEffect = 'move';
    els.linesBody.querySelectorAll('tr.is-group-drop-target').forEach((row) => row.classList.remove('is-group-drop-target'));
    if (target.dataset.lineId !== state.draggedLineId) target.classList.add('is-group-drop-target');
  });
  els.linesBody?.addEventListener('drop', (event) => {
    const target = event.target.closest('tr[data-line-id]');
    if (!target || !state.draggedLineId) return;
    event.preventDefault();
    const sourceId = state.draggedLineId;
    state.draggedLineId = '';
    target.classList.remove('is-group-drop-target');
    els.groupDropzone.hidden = true;
    groupLineOnTarget(sourceId, target.dataset.lineId);
  });
  els.linesBody?.addEventListener('dragend', () => {
    state.draggedLineId = '';
    els.linesBody.querySelectorAll('tr.is-group-drop-target').forEach((row) => row.classList.remove('is-group-drop-target'));
    if (els.groupDropzone) els.groupDropzone.hidden = true;
  });
  els.groupDropzone?.addEventListener('dragover', (event) => event.preventDefault());
  els.groupDropzone?.addEventListener('drop', (event) => {
    event.preventDefault();
    const lineId = state.draggedLineId || event.dataTransfer.getData('text/plain');
    state.draggedLineId = '';
    els.groupDropzone.hidden = true;
    ungroupLine(lineId);
  });
  els.documentSummary?.addEventListener('click', (event) => {
    const field = event.target.closest('[data-header-edit]')?.dataset.headerEdit;
    if (!field) return;
    state.headerEditing = field;
    renderDocumentCard();
  });
  els.documentSummary?.addEventListener('change', (event) => {
    const input = event.target.closest('[data-header-input]');
    if (input) saveHeaderField(input.dataset.headerInput, input.value);
  });
  els.documentSummary?.addEventListener('keydown', (event) => {
    const input = event.target.closest('[data-header-input]');
    if (!input) return;
    if (event.key === 'Escape') { state.headerEditing = ''; renderDocumentCard(); }
    if (event.key === 'Enter') { event.preventDefault(); saveHeaderField(input.dataset.headerInput, input.value); }
  });
  els.documentSummary?.addEventListener('focusout', (event) => {
    const input = event.target.closest('[data-header-input]');
    if (!input) return;
    window.setTimeout(() => {
      if (state.headerEditing === input.dataset.headerInput) {
        saveHeaderField(input.dataset.headerInput, input.value);
      }
    }, 0);
  });
  els.linesBody?.addEventListener('change', async (event) => {
    const input = event.target.closest('[data-line-description], [data-line-qty], [data-line-unit-price], [data-line-total], [data-line-tax-rate], [data-line-date]');
    if (!input) return;
    const lineIndex = Number(input.dataset.lineDescription ?? input.dataset.lineQty ?? input.dataset.lineUnitPrice ?? input.dataset.lineTotal ?? input.dataset.lineTaxRate ?? input.dataset.lineDate);
    const line = state.documentData?.lines?.[lineIndex];
    if (!line) return;
    const isCommonField = input.matches('[data-line-tax-rate], [data-line-date]');
    if (isCommonField) detachAssociatedLine(line);
    let message = 'Linha guardada.';
    if (input.matches('[data-line-description]')) {
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
    } else if (input.matches('[data-line-tax-rate]')) {
      line.tax_rate = parseEditableNumber(input.value);
      markLineManualFields(line, 'tax_rate');
      message = 'Taxa de IVA guardada.';
    } else {
      if (input.matches('[data-line-qty]')) line.qty = parseEditableNumber(input.value);
      if (input.matches('[data-line-unit-price]')) line.unit_price = parseEditableNumber(input.value);
      line.net_amount = Math.round((Number(line.qty || 0) * Number(line.unit_price || 0) + Number.EPSILON) * 100) / 100;
      markLineManualFields(line, input.matches('[data-line-qty]') ? 'qty' : 'unit_price', 'net_amount');
      message = 'Quantidade e valores guardados.';
    }
    if (line.group_role === 'principal') {
      const commonField = input.matches('[data-line-tax-rate]') ? 'tax_rate'
        : input.matches('[data-line-date]') ? 'date' : '';
      if (commonField) groupMembers(line).forEach((member) => {
        if (member === line) return;
        member[commonField] = line[commonField];
        (member.sub_lines || []).forEach((child) => { child[commonField] = line[commonField]; });
        markLineManualFields(member, commonField);
      });
    }
    renderLines(state.documentData.lines || [], state.documentData.currency || '');
    scheduleAnalysisSave();
  });
  els.supplierCard?.addEventListener('click', openSupplierModal);
  els.customerCard?.addEventListener('click', (event) => {
    if (!event.target.closest('[data-agency-control]')) openEntityModal();
  });
  els.customerCard?.addEventListener('keydown', (event) => {
    if (!event.target.closest('[data-agency-control]') && (event.key === 'Enter' || event.key === ' ')) {
      event.preventDefault(); openEntityModal();
    }
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
  els.projectDistribute?.addEventListener('click', () => openLineDistribution(state.projectTargetLineIndex, 'project'));
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
  els.vehicleDistribute?.addEventListener('click', () => openLineDistribution(state.vehicleTargetLineIndex, 'vehicle'));
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
  els.lineDistributionAdd?.addEventListener('click', addLineDistributionRow);
  els.lineDistributionCloseTop?.addEventListener('click', closeLineDistributionModal);
  els.lineDistributionClose?.addEventListener('click', closeLineDistributionModal);
  els.lineDistributionSave?.addEventListener('click', saveLineDistribution);
  els.lineDistributionSearchBack?.addEventListener('click', returnToLineDistribution);
  els.lineDistributionSearchButton?.addEventListener('click', searchLineDistributionDestinations);
  els.lineDistributionSearchInput?.addEventListener('keydown', (event) => {
    if (event.key === 'Enter') searchLineDistributionDestinations();
  });
  els.lineDistributionSearchResults?.addEventListener('click', (event) => {
    const option = event.target.closest('[data-distribution-search-index]');
    if (option) selectLineDistributionDestination(Number(option.dataset.distributionSearchIndex));
  });
  els.lineDistributionModal?.addEventListener('click', (event) => {
    if (event.target === els.lineDistributionModal) closeLineDistributionModal();
  });
  els.lineDistributionBody?.addEventListener('input', (event) => {
    const input = event.target.closest('[data-distribution-field]');
    if (input) updateLineDistributionField(input);
  });
  els.lineDistributionBody?.addEventListener('click', (event) => {
    const search = event.target.closest('[data-distribution-search]');
    if (search) {
      openLineDistributionSearch(search.dataset.distributionRow, search.dataset.distributionSearch);
      return;
    }
    const remove = event.target.closest('[data-distribution-remove]');
    if (!remove) return;
    state.lineDistributionDraft.splice(Number(remove.dataset.distributionRemove), 1);
    if (!state.lineDistributionDraft.length) addLineDistributionRow();
    else renderLineDistribution();
  });
  els.lineCostsCloseTop?.addEventListener('click', closeLineCostsModal);
  els.lineCostsClose?.addEventListener('click', closeLineCostsModal);
  els.lineCostsBack?.addEventListener('click', renderLineCosts);
  els.lineCostsTabs?.addEventListener('click', (event) => {
    const type = event.target.closest('[data-line-cost-type]')?.dataset.lineCostType;
    if (type) { state.lineCostsType = type; renderLineCosts(); }
  });
  els.lineCostsModal?.addEventListener('click', (event) => {
    if (event.target === els.lineCostsModal) closeLineCostsModal();
  });
  els.lineCostsBody?.addEventListener('click', (event) => {
    const detail = event.target.closest('[data-line-cost-detail]');
    if (detail) showLineCostDetail(Number(detail.dataset.lineCostDetail));
  });
  els.lineCostsBody?.addEventListener('keydown', (event) => {
    const detail = event.target.closest('[data-line-cost-detail]');
    if (detail && ['Enter', ' '].includes(event.key)) {
      event.preventDefault();
      showLineCostDetail(Number(detail.dataset.lineCostDetail));
    }
  });
  els.bcCloseTop?.addEventListener('click', closeBcModal);
  els.bcClose?.addEventListener('click', closeBcModal);
  els.bcSave?.addEventListener('click', saveBcAssignments);
  els.bcModal?.addEventListener('click', (event) => {
    if (event.target === els.bcModal) closeBcModal();
  });
  els.originFlow?.addEventListener('click', (event) => {
    if (state.readOnly) return;
    if (event.target.closest('[data-credit-save]')) {
      event.preventDefault();
      saveCreditNoteMapping();
      return;
    }
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
    if (state.readOnly) return;
    const creditFo = event.target.closest('[data-credit-fo]');
    if (creditFo) {
      state.creditNoteSelectedFo = state.creditNoteCandidates[Number(creditFo.dataset.creditFo)]?.fostamp || '';
      renderCreditNoteOrigins({ candidates: state.creditNoteCandidates, mapping: { original_fostamp: state.creditNoteSelectedFo } });
      return;
    }
    const input = event.target.closest('[data-virtual-bl]');
    if (!input) return;
    if (input.checked) state.selectedDeliveryNoteGroups.add(input.dataset.virtualBl);
    else state.selectedDeliveryNoteGroups.delete(input.dataset.virtualBl);
    renderLines(state.documentData?.lines || [], state.documentData?.currency || '');
  });
  els.originFlow?.addEventListener('keydown', (event) => {
    if (state.readOnly) return;
    if (!['Enter', ' '].includes(event.key) || event.target.closest('[data-origin-link]')) return;
    const option = event.target.closest('[data-origin-index]');
    if (!option) return;
    event.preventDefault();
    openOriginDetail(option.dataset.originIndex);
  });
  els.originAction?.addEventListener('click', () => {
    const action = originContextAction();
    const handler = action ? originActionHandlers.get(action.key) : null;
    if (handler) handler(action);
  });
  els.originDetailCloseTop?.addEventListener('click', closeOriginDetailModal);
  els.originDetailClose?.addEventListener('click', closeOriginDetailModal);
  els.originDetailValidate?.addEventListener('click', validateOriginOperation);
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
    if (event.key === 'Escape' && els.lineDistributionModal?.classList.contains('sz_is_open')) closeLineDistributionModal();
    if (event.key === 'Escape' && els.lineCostsModal?.classList.contains('sz_is_open')) closeLineCostsModal();
    if (event.key === 'Escape' && els.bcModal?.classList.contains('sz_is_open')) closeBcModal();
    if (event.key === 'Escape' && els.originDetailModal?.classList.contains('sz_is_open')) closeOriginDetailModal();
  });
  window.addEventListener('beforeunload', cleanupPreview);

  renderViewTabs();
  renderModeCard();
  const documentId = initialParams.get('document_id');
  if (documentId) loadInboxDocument(documentId);
});
