document.addEventListener('DOMContentLoaded', () => {
  const els = {
    backBtn: document.getElementById('docAiExtractBackBtn'),
    resetBtn: document.getElementById('docAiExtractResetBtn'),
    input: document.getElementById('docAiExtractInput'),
    chooseBtn: document.getElementById('docAiExtractChooseBtn'),
    runBtn: document.getElementById('docAiExtractRunBtn'),
    openPdfBtn: document.getElementById('docAiExtractOpenPdfBtn'),
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
    customerCard: document.getElementById('docAiExtractCustomerCard'),
    customerLabel: document.getElementById('docAiExtractCustomerLabel'),
    customerHint: document.getElementById('docAiExtractCustomerHint'),
    supplierName: document.getElementById('docAiExtractSupplierName'),
    partyLabel: document.getElementById('docAiExtractPartyLabel'),
    supplierTax: document.getElementById('docAiExtractSupplierTax'),
    supplierNo: document.getElementById('docAiExtractSupplierNo'),
    supplierCard: document.getElementById('docAiExtractSupplierCard'),
    supplierHint: document.getElementById('docAiExtractSupplierHint'),
    documentTitle: document.getElementById('docAiExtractDocumentTitle'),
    documentDate: document.getElementById('docAiExtractDocumentDate'),
    correspondenceReference: document.getElementById('docAiExtractCorrespondenceReference'),
    correspondenceSource: document.getElementById('docAiExtractCorrespondenceSource'),
    legalBadge: document.getElementById('docAiExtractLegalBadge'),
    gedDestination: document.getElementById('docAiExtractGedDestination'),
    gedStatus: document.getElementById('docAiExtractGedStatus'),
    gedFileName: document.getElementById('docAiExtractGedFileName'),
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
    totalsSection: document.getElementById('docAiExtractTotalsSection'),
    originMeta: document.getElementById('docAiExtractOriginMeta'),
    originSource: document.getElementById('docAiExtractOriginSource'),
    originLoading: document.getElementById('docAiExtractOriginLoading'),
    originFlow: document.getElementById('docAiExtractOriginFlow'),
    originTabs: document.getElementById('docAiExtractOriginTabs'),
    lineCount: document.getElementById('docAiExtractLineCount'),
    suggestBlsBtn: document.getElementById('docAiExtractSuggestBlsBtn'),
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
    persistenceNote: document.getElementById('docAiExtractPersistenceNote'),
    entityModal: document.getElementById('docAiEntityModal'),
    entitySearch: document.getElementById('docAiEntitySearch'),
    entitySearchBtn: document.getElementById('docAiEntitySearchBtn'),
    entityList: document.getElementById('docAiEntityList'),
    entityCloseTop: document.getElementById('docAiEntityCloseTop'),
    entityClose: document.getElementById('docAiEntityClose'),
    accessBtn: document.getElementById('docAiIntegrationAccessBtn'),
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
    viewTabs: document.getElementById('docAiExtractViewTabs'),
    modeLabel: document.getElementById('docAiExtractModeLabel'),
    modeValue: document.getElementById('docAiExtractModeValue'),
    modeMeta: document.getElementById('docAiExtractModeMeta'),
  };

  const allowedViews = new Set(['home', 'management', 'accounting']);
  const initialParams = new URLSearchParams(window.location.search);
  const initialView = initialParams.get('view');
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
    selectedOrigins: [],
    selectedProject: null,
    projectCandidates: [],
    projectTargetLineIndex: null,
    articleCandidates: [],
    articleTargetLineIndex: null,
    expandedBcLines: new Set(),
    projectSuggestionDismissed: false,
    deliveryNoteGroups: [],
    virtualDeliveryNotesActive: false,
    originLineMatches: [],
    originLineReferenceLabel: '',
    originLineMatchByLine: new WeakMap(),
    selectedSplitLine: null,
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
    view: allowedViews.has(initialView) ? initialView : 'home',
  };

  const typeLabels = {
    invoice: 'Fatura',
    credit_note: 'Nota de crédito',
    debit_note: 'Nota de débito',
    purchase_order: 'Nota de encomenda',
    delivery_note: 'Guia',
    proforma_invoice: 'Fatura pró-forma',
    provisional_invoice: 'Facture Provisoire',
    receipt: 'Recibo',
    bank_statement: 'RB',
    mail: 'Lettre',
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

  function extractUrl(documentId = state.currentDocumentId) {
    const params = new URLSearchParams();
    if (documentId) params.set('document_id', documentId);
    if (state.view !== 'home') params.set('view', state.view);
    const query = params.toString();
    return `/document_ai/extract${query ? `?${query}` : ''}`;
  }

  function inboxUrl() {
    return state.view === 'home' ? '/document_ai/inbox' : `/document_ai/inbox?view=${encodeURIComponent(state.view)}`;
  }

  function renderViewTabs() {
    els.viewTabs?.querySelectorAll('[data-view]').forEach((button) => {
      const active = button.dataset.view === state.view;
      button.classList.toggle('is-active', active);
      button.setAttribute('aria-selected', active ? 'true' : 'false');
      button.tabIndex = active ? 0 : -1;
    });
  }

  function renderModeCard() {
    if (!els.modeLabel || !els.modeValue || !els.modeMeta) return;
    const documentData = state.documentData || {};
    if (state.view === 'home') {
      const docType = typeLabels[documentData.document_type] || documentData.document_type || typeLabels.unknown;
      const confidence = Math.round(Math.max(0, Math.min(1, Number(documentData.confidence || 0))) * 100);
      els.modeLabel.textContent = 'Classement';
      els.modeValue.textContent = documentData.document_type ? docType : '--';
      els.modeMeta.textContent = documentData.document_type ? `${confidence}% confiance` : 'En attente de lecture';
      return;
    }
    const totals = documentData.totals || {};
    const currency = documentData.currency || '';
    els.modeLabel.textContent = 'Totaux';
    els.modeValue.textContent = documentData.document_type ? formatMoney(totals.gross_total, currency) : '--';
    els.modeMeta.textContent = documentData.document_type
      ? `HT ${formatMoney(totals.net_total, currency)} · TVA ${formatMoney(totals.tax_total, currency)}`
      : 'En attente de lecture';
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
      documentData.mail_title,
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
    const selectedFolder = customer.ged_folder || 'HSOLS_INTERSOL_AL';
    els.gedFolderSelect.replaceChildren(...intersolGedFolders.map((option) => {
      const element = document.createElement('option');
      element.value = option.value;
      element.textContent = option.label;
      element.selected = option.value === selectedFolder;
      return element;
    }));
    els.gedFolderHint.textContent = state.gedFolderManuallySelected
      ? 'Destino escolhido manualmente'
      : (customer.ged_folder_suggested_by || 'Alsace por defeito; confirma antes de submeter');
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
    els.gedPath.replaceChildren(...paths.map((destination) => {
      const item = document.createElement('div');
      item.className = 'docai-extract-ged-path-item';
      const label = document.createElement('span');
      label.textContent = destination.label;
      const pathCode = document.createElement('code');
      pathCode.textContent = destination.path;
      item.append(label, pathCode);
      return item;
    }));
    els.gedDestination.classList.toggle('is-incomplete', incomplete);
    els.gedStatus.textContent = incomplete
      ? 'Destino provisório: falta obter a correspondência, identificar o número do remetente/fornecedor ou configurar a pasta GED da entidade.'
      : `${paths.length} ${paths.length === 1 ? 'ficheiro previsto' : 'ficheiros previstos'} com os dados identificados.`;
    if (state.integrationResult?.ged_path) {
      els.gedFileName.textContent = state.integrationResult.file_name || fileName;
      const integratedPath = els.gedPath.querySelector('code');
      if (integratedPath) integratedPath.textContent = state.integrationResult.ged_path;
      els.gedDestination.classList.remove('is-incomplete');
      els.gedStatus.textContent = `Guardado no PHC ${state.integrationResult.phc_database || ''} e ligado à correspondência nº ${state.integrationResult.reference}.`;
    }
    updateSubmitPhcButton();
  }

  function updateSubmitPhcButton() {
    if (!els.submitPhcBtn) return;
    const documentData = state.documentData || {};
    const party = documentData.supplier || {};
    const isCorrespondence = ['mail', 'bank_statement'].includes(documentData.document_type);
    const isProvisionalInvoice = ['invoice', 'provisional_invoice', 'credit_note'].includes(documentData.document_type);
    const allowed = (isCorrespondence && els.submitPhcBtn.dataset.canCorrespondence === '1')
      || (isProvisionalInvoice && els.submitPhcBtn.dataset.canProvisionalInvoice === '1');
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
        ? (state.controlOk ? 'Contrôle OK concluído.' : 'Confirmar o controlo do documento.')
        : 'Identifica a sociedade, o fornecedor, o número e as linhas do documento.';
      els.controlOkBtn.innerHTML = state.submittingControl
        ? '<i class="fa-solid fa-circle-notch fa-spin"></i><span>A confirmar...</span>'
        : state.controlOk
          ? '<i class="fa-solid fa-circle-check"></i><span>Contrôle OK</span>'
          : '<i class="fa-solid fa-clipboard-check"></i><span>Contrôle OK</span>';
    }
    els.submitPhcBtn.disabled = !ready || (isProvisionalInvoice && !state.controlOk) || state.submittingPhc || state.integratedPhc;
    els.submitPhcBtn.title = isProvisionalInvoice && !state.controlOk
      ? 'Efetua primeiro o Contrôle OK.'
      : '';
    if (state.integratedPhc) {
      els.submitPhcBtn.innerHTML = '<i class="fa-solid fa-circle-check"></i><span>Comptabilité</span>';
    } else if (state.submittingPhc) {
      els.submitPhcBtn.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin"></i><span>Validation...</span>';
    } else {
      els.submitPhcBtn.innerHTML = isProvisionalInvoice
        ? '<i class="fa-solid fa-check"></i><span>Validation</span>'
        : '<i class="fa-solid fa-paper-plane"></i><span>Submeter no PHC</span>';
    }
  }

  function renderDocumentCard() {
    const documentData = state.documentData || {};
    const docType = typeLabels[documentData.document_type] || documentData.document_type || typeLabels.unknown;
    const displayedNumber = documentData.document_type === 'mail'
      ? documentData.mail_title
      : documentData.document_number;
    els.documentTitle.textContent = `${docType}${displayedNumber ? ` · ${displayedNumber}` : ''}`;
    els.documentDate.textContent = `Data: ${formatDate(documentData.document_date)}${documentData.due_date ? ` · Vencimento: ${formatDate(documentData.due_date)}` : ''}`;
    if (state.correspondenceReference) {
      els.correspondenceReference.textContent = `Correspondência nº ${state.correspondenceReference} · ${state.correspondenceYear}`;
    } else {
      els.correspondenceReference.textContent = 'Correspondência: a consultar sequência anual…';
    }
  }

  async function loadCorrespondenceReference() {
    const documentData = state.documentData;
    const customer = documentData?.customer || {};
    const token = ++state.correspondenceLookupToken;
    state.correspondenceReference = null;
    state.correspondenceYear = new Date().getFullYear();
    renderDocumentCard();
    els.correspondenceSource.hidden = true;
    renderGedDestination();
    if (!customer.feid) {
      els.correspondenceReference.textContent = 'Correspondência: escolhe primeiro a entidade';
      return;
    }
    try {
      const payload = await fetchJson('/api/document_ai/correspondence/next-reference', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ customer, year: state.correspondenceYear }),
      });
      if (token !== state.correspondenceLookupToken || documentData !== state.documentData) return;
      state.correspondenceReference = Number(payload.reference || 0) || null;
      state.correspondenceYear = Number(payload.year || state.correspondenceYear);
      documentData.correspondence_reference = state.correspondenceReference;
      documentData.correspondence_year = state.correspondenceYear;
      renderDocumentCard();
      els.correspondenceSource.textContent = `${payload.phc_database || 'PHC'} · sequência anual da entidade`;
      els.correspondenceSource.hidden = false;
      renderGedDestination();
    } catch (error) {
      if (token !== state.correspondenceLookupToken) return;
      els.correspondenceReference.textContent = 'Correspondência: numeração PHC indisponível';
      els.correspondenceSource.textContent = error.message || 'Não foi possível consultar a tabela CR.';
      els.correspondenceSource.hidden = false;
      renderGedDestination();
    }
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
    state.selectedSplitLine = null;
    state.controlOk = false;
    state.submittingControl = false;
    state.correspondenceLookupToken += 1;
    state.correspondenceReference = null;
    state.correspondenceYear = null;
    state.submittingPhc = false;
    state.submittingControl = false;
    state.controlOk = Boolean(payload.workflow?.control_ok);
    state.integratedPhc = payload.processing_status === 'provisional_invoice' || Boolean(payload.phc_integration?.fostamp);
    state.integrationResult = state.integratedPhc ? (payload.phc_integration || {}) : null;
    els.input.value = '';
    els.preview.hidden = true;
    els.dropzone.hidden = false;
    els.runBtn.disabled = true;
    els.openPdfBtn.disabled = true;
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
    renderProjectCard();
    window.history.replaceState({}, '', extractUrl(''));
    setStatus('Pronto.');
    updateSubmitPhcButton();
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
    state.selectedSplitLine = null;
    state.correspondenceLookupToken += 1;
    state.correspondenceReference = null;
    state.correspondenceYear = null;
    state.documentData = null;
    state.matching = {};
    state.supplierCandidates = [];
    els.results.hidden = true;
    els.confidence.hidden = true;
    els.batchAlert.hidden = true;
    els.originFlow.hidden = true;
    if (els.originTabs) {
      els.originTabs.hidden = true;
      els.originTabs.innerHTML = '';
    }
    els.originLoading.hidden = false;
    els.empty.hidden = false;
    els.empty.querySelector('strong').textContent = 'A iniciar leitura automática';
    els.empty.querySelector('span').textContent = 'O PDF será enviado ao LLM assim que ficar carregado.';
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
    els.loading.querySelector('span').textContent = 'A leitura guardada será reutilizada; o LLM só será chamado se ainda não existir resultado.';
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
      els.empty.querySelector('strong').textContent = 'A carregar leitura do documento';
      els.empty.querySelector('span').textContent = 'Será usado o resultado guardado no inbox quando estiver disponível.';
      els.resultMeta.textContent = 'PDF carregado a partir do inbox; a verificar leitura guardada.';
      setStatus('A verificar se o documento já tem uma leitura guardada...');
      window.history.replaceState({}, '', extractUrl(documentId));
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
    if (!state.deliveryNoteGroups.length) state.virtualDeliveryNotesActive = false;
    els.suggestBlsBtn.hidden = !state.deliveryNoteGroups.length;
    els.suggestBlsBtn.disabled = state.virtualDeliveryNotesActive;
    els.suggestBlsBtn.innerHTML = state.virtualDeliveryNotesActive
      ? `<i class="fa-solid fa-circle-check"></i><span>${state.deliveryNoteGroups.length} BL(s) sugeridos</span>`
      : `<i class="fa-solid fa-wand-magic-sparkles"></i><span>Sugerir criação de ${state.deliveryNoteGroups.length} BL(s)</span>`;
    if (state.selectedSplitLine && !items.includes(state.selectedSplitLine)) state.selectedSplitLine = null;
    const proportionalGroups = state.deliveryNoteGroups.filter((group) => Number(group.base_quantity || 0) > 0);
    const canSplitAcrossDeliveryNotes = proportionalGroups.length >= 2;
    els.splitLineBtn.hidden = !canSplitAcrossDeliveryNotes;
    els.splitLineBtn.disabled = !canSplitAcrossDeliveryNotes || !state.selectedSplitLine;
    els.splitLineBtn.innerHTML = state.selectedSplitLine
      ? `<i class="fa-solid fa-code-branch"></i><span>Répartir BL (${proportionalGroups.length})</span>`
      : '<i class="fa-solid fa-code-branch"></i><span>Répartir BL</span>';
    els.lineCount.textContent = `${items.length} linha(s)`;
    if (!items.length) {
      els.linesBody.innerHTML = '<tr><td colspan="9" class="sz_text_muted">Não foram encontradas linhas comerciais visíveis.</td></tr>';
      return;
    }
    els.linesBody.innerHTML = items.map((line, lineIndex) => {
      const originMatches = state.originLineMatchByLine.get(line) || [];
      const selectedForSplit = state.selectedSplitLine === line;
      const action = originMatches.length ? 'Rattacher' : (line.ref ? 'Contrôler' : 'Créer');
      const project = String(line.ccusto || line.project_ccusto || state.selectedProject?.ccusto || '').trim();
      const bcCell = originMatches.length > 1
        ? `<button type="button" class="docai-extract-bc-toggle" data-line-bc-toggle="${lineIndex}" title="Ouvrir" aria-expanded="${state.expandedBcLines.has(lineIndex) ? 'true' : 'false'}">${originMatches.length} BC <i class="fa-solid fa-chevron-${state.expandedBcLines.has(lineIndex) ? 'up' : 'down'}"></i></button>`
        : originMatches.length === 1
          ? `<span class="docai-extract-bc-ref">${escapeHtml(originMatches[0].origin_ref || '--')}</span>`
          : '<span class="sz_text_muted">--</span>';
      const bcRows = originMatches.length > 1 && state.expandedBcLines.has(lineIndex)
        ? originMatches.map((originMatch) => {
            const reasons = Array.isArray(originMatch.reasons) ? originMatch.reasons.join(' · ') : '';
            return `<tr class="docai-extract-bc-detail-row">
              <td></td><td></td><td>${escapeHtml(originMatch.origin_description || reasons || 'Correspondance BC')}</td>
              <td></td><td></td><td></td><td></td>
              <td><span class="docai-extract-bc-ref">${escapeHtml(originMatch.origin_ref || '--')}</span></td><td></td>
            </tr>`;
          }).join('')
        : '';
      return `<tr class="${selectedForSplit ? 'is-selected-for-split' : ''}${line._virtual_split_allocation ? ' is-split-allocation' : ''}">
        <td><span class="docai-extract-line-action">${escapeHtml(action)}</span></td>
        <td><button type="button" class="docai-extract-cell-link" data-line-article="${lineIndex}" title="Choisir un article PHC">${escapeHtml(line.ref || 'Choisir')}</button></td>
        <td><input class="sz_input docai-extract-line-description-input" data-line-description="${lineIndex}" value="${escapeHtml(line.description || '')}" aria-label="Désignation de la ligne"></td>
        <td class="docai-extract-number">${escapeHtml(formatNumber(line.qty))}</td>
        <td class="docai-extract-number">${escapeHtml(formatMoney(line.unit_price, currency))}</td>
        <td class="docai-extract-number">${escapeHtml(formatMoney(line.net_amount, currency))}</td>
        <td><button type="button" class="docai-extract-cell-link" data-line-project="${lineIndex}" title="Choisir un chantier">${escapeHtml(project || 'Choisir')}</button></td>
        <td class="docai-extract-bc-ref-cell">${bcCell}</td>
        <td class="docai-extract-line-picker-cell"><input type="checkbox" data-line-select="${lineIndex}" aria-label="Sélectionner pour répartir BL" ${selectedForSplit ? 'checked' : ''}></td>
      </tr>${bcRows}`;
    }).join('');
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
    const isCorrespondence = ['mail', 'bank_statement'].includes(state.documentData?.document_type);
    const isCustomerMail = isCorrespondence && state.documentData?.external_party_role === 'customer';
    const supplierNo = Number(isCustomerMail ? supplier.customer_no : (supplier.supplier_no || supplier.no) || 0);
    const supplierNumberLabel = phcPartyNumber(supplierNo, supplier.estab);
    const matched = Boolean(supplierNo);
    els.partyLabel.textContent = isCorrespondence ? 'Remetente' : 'Fournisseur';
    els.supplierName.textContent = supplier.name || supplier.llm_name || '--';
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
  }

  function renderCustomerCard(customer = {}, matching = {}) {
    const isMail = state.documentData?.document_type === 'mail';
    const matched = Boolean(customer.feid && matching.customer_matched !== false);
    els.customerLabel.textContent = isMail ? 'Entidade' : 'Société';
    els.customerName.textContent = isMail && !matched ? 'Por escolher' : (customer.name || '--');
    els.customerTax.textContent = matched && customer.tax_id ? `NIF: ${customer.tax_id}` : (matched ? 'NIF não identificado' : 'Empresa do grupo não identificada');
    els.customerHint.hidden = false;
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

    const virtualStageHtml = renderVirtualDeliveryNoteStage();

    if (!payload.available) {
      els.originTabs.hidden = true;
      els.originTabs.innerHTML = '';
      els.originMeta.textContent = virtualStageHtml
        ? `${state.deliveryNoteGroups.length} BL(s) identificado(s) na fatura, ainda por criar no PHC.`
        : payload.message || 'Não foi possível procurar origens no PHC.';
      const unavailableHtml = `<div class="docai-extract-origin-unavailable"><i class="fa-solid fa-circle-info"></i><span>${escapeHtml(payload.message || 'Pesquisa PHC indisponível.')}</span></div>`;
      els.originFlow.innerHTML = `${virtualStageHtml}${unavailableHtml}`;
      return;
    }

    const stages = (Array.isArray(payload.stages) ? payload.stages : [])
      .filter((stage) => Array.isArray(stage.candidates) && stage.candidates.length);
    const detectedOrigins = Array.isArray(payload.detected_origins) ? payload.detected_origins : [];
    const detectedOriginLabel = (item) => {
      if (item.document_type === 'delivery_note') return 'BL';
      if (item.document_type === 'contract') return 'Contrato';
      return 'BC';
    };
    const detectedLabel = detectedOrigins.length
      ? ` O PDF refere: ${detectedOrigins.map((item) => `${detectedOriginLabel(item)} ${item.document_number}`).join(', ')}.`
      : '';
    const virtualLabel = virtualStageHtml ? ` ${state.deliveryNoteGroups.length} BL(s) virtual(is) proposto(s) para criação.` : '';
    els.originMeta.textContent = payload.candidate_count
      ? `${payload.candidate_count} possível(eis) origem(ns) do mesmo fornecedor.${detectedLabel}${virtualLabel}`
      : `Não foram encontrados documentos anteriores abertos com quantidades pendentes.${detectedLabel}${virtualLabel}`;

    let virtualStageInserted = false;
    let stageHtml = stages.map((stage) => {
      const insertVirtualBefore = virtualStageHtml && !virtualStageInserted && ['delivery_note', 'purchase_order'].includes(stage.key);
      if (insertVirtualBefore) virtualStageInserted = true;
      const candidates = Array.isArray(stage.candidates) ? stage.candidates : [];
      const cards = candidates.map((candidate) => {
        const candidateIndex = state.originCandidates.push(candidate) - 1;
        const selected = state.selectedOrigins.some((origin) => origin.stamp === candidate.stamp);
        const reasons = Array.isArray(candidate.reasons) ? candidate.reasons.slice(0, 2).join(' · ') : '';
        return `
          <button type="button" class="docai-extract-origin-candidate${selected ? ' is-selected' : ''}" data-origin-index="${candidateIndex}" aria-pressed="${selected ? 'true' : 'false'}">
            <span class="docai-extract-origin-candidate-top">
              <strong>Nº ${escapeHtml(candidate.number || '--')}${candidate.year ? ` / ${escapeHtml(candidate.year)}` : ''}</strong>
              <span>${Math.round(Number(candidate.score || 0) * 100)}%</span>
            </span>
            <span>${escapeHtml(formatDate(candidate.date))} · ${escapeHtml(formatMoney(candidate.total, state.documentData?.currency))} · ${escapeHtml(formatNumber(candidate.pending_quantity))} pendente</span>
            <small>${escapeHtml(reasons || `${candidate.line_count || 0} linha(s)`)}</small>
            <em><i class="fa-solid ${selected ? 'fa-circle-minus' : 'fa-link'}"></i> ${selected ? 'Détacher' : 'Rattacher'}</em>
          </button>`;
      }).join('');
      const realStageHtml = `
        <article class="docai-extract-origin-stage" data-origin-stage="${escapeHtml(stage.key)}">
          <div class="docai-extract-origin-stage-title"><strong>${escapeHtml(stage.display_order || '')} ${escapeHtml(stage.label || stage.key)}</strong></div>
          <div class="docai-extract-origin-options">${cards}</div>
        </article>`;
      return `${insertVirtualBefore ? virtualStageHtml : ''}${realStageHtml}`;
    }).join('');
    if (virtualStageHtml && !virtualStageInserted) stageHtml += virtualStageHtml;

    els.originFlow.innerHTML = stageHtml || '<div class="docai-extract-origin-unavailable"><i class="fa-solid fa-magnifying-glass"></i><span>Sem documentos anteriores disponíveis para ligar.</span></div>';
    const tabStages = stages.map((stage) => ({
      key: String(stage.key || ''),
      label: String(stage.label || stage.key || ''),
      count: Array.isArray(stage.candidates) ? stage.candidates.length : 0,
    }));
    if (virtualStageHtml) {
      const virtualIndex = Math.max(0, tabStages.findIndex((stage) => ['delivery_note', 'purchase_order'].includes(stage.key)));
      tabStages.splice(virtualIndex, 0, { key: 'virtual_delivery_note', label: 'BL à créer', count: state.deliveryNoteGroups.length });
    }
    renderOriginTabs(tabStages);
  }

  function renderOriginTabs(stages = []) {
    const availableKeys = stages.map((stage) => stage.key).filter(Boolean);
    if (!availableKeys.length) {
      els.originTabs.hidden = true;
      els.originTabs.innerHTML = '';
      return;
    }
    if (!availableKeys.includes(state.activeOriginStage)) state.activeOriginStage = availableKeys[0];
    els.originTabs.hidden = false;
    els.originTabs.innerHTML = stages.map((stage) => {
      const active = stage.key === state.activeOriginStage;
      return `<button type="button" class="docai-extract-origin-tab${active ? ' is-active' : ''}" role="tab" data-origin-tab="${escapeHtml(stage.key)}" aria-selected="${active ? 'true' : 'false'}">${escapeHtml(stage.label)} <span>${Number(stage.count || 0)}</span></button>`;
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
      origin_reference_label: `BC ${origin.number || ''}${origin.year ? ` / ${origin.year}` : ''}`.trim(),
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
    state.originLineReferenceLabel = purchaseOrders.map((origin) => `BC ${origin.number || ''}`).join(', ');
    if (state.documentData?.lines) renderLines(state.documentData.lines, state.documentData.currency || '');
  }

  function renderVirtualDeliveryNoteStage() {
    if (!state.virtualDeliveryNotesActive || !state.deliveryNoteGroups.length) return '';
    const cards = state.deliveryNoteGroups.map((group) => {
      const quantityLabel = group.quantity
        ? `${formatNumber(group.quantity)}${group.unit ? ` ${escapeHtml(group.unit)}` : ''}`
        : 'Quantidade por confirmar';
      const description = group.lines.find((line) => String(line.description || '').trim())?.description || '';
      return `
        <article class="docai-extract-origin-candidate is-selected is-virtual" aria-label="BL virtual ${escapeHtml(group.number)} sugerido para criação">
          <span class="docai-extract-origin-candidate-top">
            <strong>BL ${escapeHtml(group.number)}</strong>
            <span>Sugestão · a criar</span>
          </span>
          <span>${escapeHtml(group.line_count)} linha(s) · ${quantityLabel}${group.net_total ? ` · ${escapeHtml(formatMoney(group.net_total, state.documentData?.currency))}` : ''}</span>
          <small>${escapeHtml(description || 'Linhas agrupadas pelo número de BL identificado na fatura')}</small>
          <em><i class="fa-solid fa-flag"></i> Virtual — ainda não existe no PHC</em>
        </article>`;
    }).join('');
    return `
      <article class="docai-extract-origin-stage is-virtual-stage" data-origin-stage="virtual_delivery_note">
        <div class="docai-extract-origin-stage-title">
          <strong>${state.deliveryNoteGroups.length} Bon de Livraison Fournisseur a criar</strong>
          <span class="docai-extract-virtual-flag"><i class="fa-solid fa-wand-magic-sparkles"></i> Sugestão</span>
        </div>
        <div class="docai-extract-origin-options">${cards}</div>
      </article>`;
  }

  function suggestVirtualDeliveryNotes() {
    if (!state.deliveryNoteGroups.length || state.virtualDeliveryNotesActive) return;
    state.virtualDeliveryNotesActive = true;
    els.suggestBlsBtn.disabled = true;
    els.suggestBlsBtn.innerHTML = `<i class="fa-solid fa-circle-check"></i><span>${state.deliveryNoteGroups.length} BL(s) sugeridos</span>`;
    if (state.originPayload) renderOriginCandidates(state.originPayload, { skipLineMapping: true });
    els.originSection?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    setStatus(`${state.deliveryNoteGroups.length} BL(s) virtual(is) adicionados às sugestões de origem. Ainda não foram criados no PHC.`);
    showMessage('BLs adicionados como sugestões virtuais. Ainda não foram criados no PHC.', 'success');
  }

  function selectLineForSplit(lineIndex) {
    const line = state.documentData?.lines?.[Number(lineIndex)];
    if (!line) return;
    state.selectedSplitLine = state.selectedSplitLine === line ? null : line;
    renderLines(state.documentData.lines, state.documentData.currency || '');
  }

  function proportionalPart(total, ratio, allocated, isLast) {
    if (isLast) return Math.round((Number(total || 0) - allocated) * 1000000) / 1000000;
    return Math.round((Number(total || 0) * ratio) * 1000000) / 1000000;
  }

  async function splitSelectedLineAcrossDeliveryNotes() {
    const selectedLine = state.selectedSplitLine;
    const lines = state.documentData?.lines;
    if (!selectedLine || !Array.isArray(lines)) return;
    const targetGroups = state.deliveryNoteGroups.filter((group) => Number(group.base_quantity || 0) > 0);
    const totalWeight = targetGroups.reduce((total, group) => total + Number(group.base_quantity || 0), 0);
    if (targetGroups.length < 2 || totalWeight <= 0) {
      showMessage('São necessários pelo menos dois BLs com quantidades identificadas.', 'error');
      return;
    }

    const originalLines = [...lines];
    const remainingLines = lines.filter((line) => line !== selectedLine);
    const selectedMatch = state.originLineMatchByLine.get(selectedLine) || null;
    const allocatedTotals = { qty: 0, net_amount: 0, gross_amount: 0 };
    const createdLines = [];
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
      remainingLines.forEach((line, lineIndexValue) => {
        if (String(line.origin_delivery_note_number || '').trim() === group.number) insertionIndex = lineIndexValue;
      });
      remainingLines.splice(insertionIndex >= 0 ? insertionIndex + 1 : remainingLines.length, 0, allocation);
      if (selectedMatch) state.originLineMatchByLine.set(allocation, selectedMatch);
      createdLines.push(allocation);
    });

    state.documentData.lines = remainingLines;
    state.selectedSplitLine = null;
    renderLines(state.documentData.lines, state.documentData.currency || '');
    if (state.originPayload && state.virtualDeliveryNotesActive) {
      renderOriginCandidates(state.originPayload, { skipLineMapping: true });
    }
    els.splitLineBtn.disabled = true;
    setStatus(`A guardar a repartição proporcional por ${createdLines.length} BLs...`);
    if (state.currentDocumentId) {
      try {
        await fetchJson(`/api/document_ai/documents/${encodeURIComponent(state.currentDocumentId)}/lines`, {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ lines: state.documentData.lines }),
        });
      } catch (error) {
        state.documentData.lines = originalLines;
        state.selectedSplitLine = selectedLine;
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
      .map((line) => `BL ${line.origin_delivery_note_number}: ${formatNumber(line.qty)}`)
      .join(' · ');
    setStatus(`Linha repartida proporcionalmente. ${allocationSummary}`);
    showMessage(`Linha repartida por ${createdLines.length} BLs sem alterar a quantidade total.`, 'success');
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
    const button = els.originFlow.querySelector(`[data-origin-index="${Number(index)}"]`);
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
      state.selectedOrigins = Array.isArray(payload.origins) ? payload.origins : (alreadySelected ? previousOrigins.filter((origin) => origin.stamp !== selected.stamp) : [...previousOrigins, payload.origin || selected]);
      renderOriginCandidates({ ...(state.originPayload || {}), selected_origins: state.selectedOrigins });
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
    els.projectName.textContent = selected ? project.ccusto : 'Todas as obras';
    const projectDetails = [project.machine, project.location].filter(Boolean).join(' · ');
    els.projectMeta.textContent = hasWorkConflict
      ? `Atenção: os BCs selecionados pertencem a ${selectedOriginWorks.length} obras (${selectedOriginWorks.join(', ')})`
      : selected
        ? [project.suggested_by_document ? `Sugerida por ${project.suggested_by_document}` : '', projectDetails].filter(Boolean).join(' · ') || 'Filtro de obra ativo'
        : 'Sem filtro de obra';
    els.projectHint.innerHTML = hasWorkConflict
      ? '<i class="fa-solid fa-triangle-exclamation"></i> BCs de obras diferentes'
      : selected
      ? '<i class="fa-solid fa-pen"></i> Alterar obra'
      : '<i class="fa-solid fa-magnifying-glass"></i> Pesquisar obra';
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
        await fetchJson(`/api/document_ai/documents/${encodeURIComponent(state.currentDocumentId)}/origin`, {
          method: 'DELETE',
        });
      } catch (error) {
        setStatus(error.message || 'Não foi possível desmarcar a origem anterior.', true);
        showMessage(error.message || 'Não foi possível desmarcar a origem anterior.', 'error');
        return false;
      }
    }
    state.selectedOrigins = [];
    return true;
  }

  function closeProjectModal() {
    state.projectTargetLineIndex = null;
    els.projectModal.classList.remove('sz_is_open');
    els.projectModal.setAttribute('aria-hidden', 'true');
  }

  async function saveAdjustedLines(successMessage = 'Ligne mise à jour.') {
    if (!state.currentDocumentId || !state.documentData) {
      setStatus(successMessage);
      return true;
    }
    try {
      await fetchJson(`/api/document_ai/documents/${encodeURIComponent(state.currentDocumentId)}/lines`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ lines: state.documentData.lines || [] }),
      });
      setStatus(successMessage);
      return true;
    } catch (error) {
      setStatus(error.message || 'La ligne n’a pas pu être enregistrée.', true);
      showMessage(error.message || 'La ligne n’a pas pu être enregistrée.', 'error');
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
    els.projectContext.textContent = `Chantiers de ${state.documentData.customer?.name || 'la société cliente'}`;
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
      state.projectTargetLineIndex = null;
      closeProjectModal();
      renderLines(state.documentData.lines || [], state.documentData.currency || '');
      await saveAdjustedLines(`Chantier ${selected.ccusto} enregistré sur la ligne.`);
      return;
    }
    const changed = String(state.selectedProject?.ccusto || '').trim() !== String(selected.ccusto || '').trim();
    if (changed && !await clearSelectedOriginsForProjectChange(selected.ccusto)) return;
    state.projectSuggestionDismissed = true;
    state.selectedProject = { ...selected };
    state.documentData.origin_project = { ...selected };
    renderProjectCard();
    closeProjectModal();
    setStatus(`Filtro de obra ${selected.ccusto} aplicado às origens.`);
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
      els.articleList.innerHTML = '<div class="docai-empty-state">Aucun article trouvé.</div>';
      return;
    }
    els.articleList.innerHTML = state.articleCandidates.map((article, index) => `
      <button type="button" class="docai-supplier-match-option" data-article-index="${index}">
        <span class="docai-supplier-match-main">
          <strong>${escapeHtml(article.ref || '--')}</strong>
          <span>${escapeHtml(article.design || 'Sans désignation')}</span>
        </span>
        <span class="docai-supplier-match-score">${escapeHtml([article.family, article.unit].filter(Boolean).join(' · '))}</span>
      </button>
    `).join('');
  }

  async function searchArticleCandidates() {
    if (!state.documentData?.customer) return;
    els.articleSearchBtn.disabled = true;
    els.articleList.innerHTML = '<div class="docai-empty-state">Recherche des articles PHC...</div>';
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
      els.articleContext.textContent = `Articles de ${state.documentData.customer?.name || 'la société cliente'} · ${payload.phc_database || 'PHC'}`;
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
      showMessage('Identifie d’abord la société cliente.', 'error');
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
    line.ref = article.ref || '';
    line.article_ref = article.ref || '';
    line.description = article.design || line.description || '';
    if (article.unit) line.unit = article.unit;
    state.articleTargetLineIndex = null;
    closeArticleModal();
    renderLines(state.documentData.lines || [], state.documentData.currency || '');
    await saveAdjustedLines(`Article ${article.ref} enregistré sur la ligne.`);
  }

  async function clearProject(event) {
    event?.stopPropagation();
    state.projectSuggestionDismissed = true;
    state.selectedProject = null;
    if (state.documentData) delete state.documentData.origin_project;
    renderProjectCard();
    setStatus('Filtro de obra removido.');
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
    els.supplierManualBtn.hidden = !isCorrespondence;
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
  }

  function selectSupplier(index) {
    const selected = state.supplierCandidates[index];
    if (!selected || !state.documentData) return;
    const current = state.documentData.supplier || {};
    const isCorrespondence = ['mail', 'bank_statement'].includes(state.documentData.document_type);
    const isCustomer = isCorrespondence && selected.party_role === 'customer';
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
    if (!['mail', 'bank_statement'].includes(state.documentData.document_type)) loadOriginCandidates(state.documentData);
  }

  function renderResult(payload) {
    const documentData = payload.document || {};
    const customer = documentData.customer || {};
    const supplier = documentData.supplier || {};
    const totals = documentData.totals || {};
    const currency = documentData.currency || '';
    const isMail = documentData.document_type === 'mail';
    const isCorrespondence = ['mail', 'bank_statement'].includes(documentData.document_type);

    state.documentData = documentData;
    state.gedFolderManuallySelected = Boolean(documentData.customer?.ged_folder_manually_selected);
    state.submittingPhc = false;
    state.integratedPhc = false;
    state.integrationResult = null;
    if (state.selectedProject?.ccusto) state.documentData.origin_project = { ...state.selectedProject };
    state.matching = payload.matching || {};
    state.supplierCandidates = state.matching.supplier_candidates || [];
    renderDocumentBatch(documentData.document_batch || {});
    if (isCorrespondence) els.batchAlert.hidden = true;
    renderCustomerCard(customer, state.matching);
    renderSupplierCard(supplier, state.matching);
    renderProjectCard();
    els.projectCard.hidden = isCorrespondence;
    els.originSection.hidden = isCorrespondence;
    els.linesSection.hidden = isCorrespondence;
    els.totalsSection.hidden = true;
    els.notesSection.hidden = true;
    els.gedDestination.hidden = true;
    els.persistenceNote.textContent = isMail
      ? 'O correio foi analisado apenas neste ecrã e não foi adicionado ao inbox.'
      : (documentData.document_type === 'bank_statement'
        ? 'O relevé fica no inbox e pode ser integrado como correspondência RB no PHC.'
        : 'O PDF e a leitura ficam guardados no inbox para evitar novas chamadas ao LLM.');
    state.correspondenceReference = null;
    state.correspondenceYear = new Date().getFullYear();
    renderDocumentCard();
    els.legalBadge.hidden = !(isMail && documentData.mail_category === 'legal');
    renderGedDestination();
    loadCorrespondenceReference();

    renderLines(documentData.lines, currency);
    renderTaxes(documentData.taxes, currency);
    els.netTotal.textContent = formatMoney(totals.net_total, currency);
    els.taxTotal.textContent = formatMoney(totals.tax_total, currency);
    els.grossTotal.textContent = formatMoney(totals.gross_total, currency);
    renderModeCard();

    const notes = Array.isArray(documentData.notes) ? documentData.notes.filter(Boolean) : [];
    els.notesSection.hidden = true;
    els.notes.innerHTML = notes.map((note) => `<li>${escapeHtml(note)}</li>`).join('');

    const confidence = Math.max(0, Math.min(1, Number(documentData.confidence || 0)));
    els.confidence.innerHTML = `<i class="fa-solid fa-circle-check"></i><span>${Math.round(confidence * 100)}% confiança</span>`;
    els.confidence.className = `docai-status-chip ${confidence >= 0.75 ? 'status-parsed_ok' : 'status-review_required'}`;
    els.confidence.hidden = false;
    const batch = documentData.document_batch || {};
    const batchSuffix = batch.contains_multiple_documents
      ? ` · ${Number(batch.document_count || 0)} documentos em ${Number(batch.page_count || 0)} páginas`
      : '';
    const readingSource = payload.cached ? 'Leitura guardada' : `Leitura concluída com ${payload.model || 'LLM'}`;
    els.resultMeta.textContent = `${readingSource} · ${documentData.visible_language || 'idioma não identificado'}${batchSuffix}`;
    els.empty.hidden = true;
    els.loading.hidden = true;
    els.results.hidden = false;
    if (isCorrespondence) {
      state.originSearchToken += 1;
      state.originPayload = null;
      state.originCandidates = [];
      state.selectedOrigins = [];
    } else {
      loadOriginCandidates(documentData);
    }
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
    state.selectedSplitLine = null;
    state.correspondenceLookupToken += 1;
    state.correspondenceReference = null;
    state.correspondenceYear = null;
    els.suggestBlsBtn.hidden = true;
    els.suggestBlsBtn.disabled = false;
    els.splitLineBtn.hidden = true;
    els.splitLineBtn.disabled = true;
    els.originFlow.innerHTML = '';
    els.originFlow.hidden = true;
    els.originLoading.hidden = false;
    els.originSource.hidden = true;
    closeProjectModal();
    closeSupplierModal();
    renderProjectCard();
  }

  async function extractDocument(options = {}) {
    if (!state.file || state.loading) return;
    if (options.force) clearSuggestionsForForcedRead();
    state.loading = true;
    els.runBtn.disabled = true;
    els.resetBtn.disabled = true;
    els.empty.hidden = true;
    els.results.hidden = true;
    els.confidence.hidden = true;
    els.loading.hidden = false;
    els.resultMeta.textContent = options.force
      ? 'A eliminar a leitura anterior e a iniciar uma nova análise...'
      : 'A procurar uma leitura guardada no inbox...';
    setStatus(options.force
      ? 'Nova leitura forçada: os dados anteriores serão substituídos pelo resultado do LLM...'
      : 'A verificar os dados guardados; o LLM só será chamado se necessário...');

    const formData = new FormData();
    formData.append('file', state.file);
    formData.append('document_id', state.currentDocumentId || '');
    formData.append('force', options.force ? '1' : '0');
    try {
      const payload = await fetchJson('/api/document_ai/extract', { method: 'POST', body: formData });
      if (payload.document_id) {
        state.currentDocumentId = payload.document_id;
        window.history.replaceState({}, '', `/document_ai/extract?document_id=${encodeURIComponent(payload.document_id)}`);
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
        setStatus('Leitura carregada do inbox sem utilizar tokens do LLM.');
        showMessage('Foi reutilizada a leitura guardada.', 'success');
      } else {
        setStatus('Leitura concluída.');
        showMessage(payload.inbox_created ? 'Documento lido e adicionado ao inbox.' : 'Documento lido com sucesso.', 'success');
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

  async function submitDocumentToPhc() {
    if (!els.submitPhcBtn || state.submittingPhc || state.integratedPhc) return;
    const documentType = state.documentData?.document_type;
    if (!state.file || !['mail', 'bank_statement', 'invoice', 'provisional_invoice', 'credit_note'].includes(documentType)) {
      showMessage('Carrega e valida primeiro um documento compatível.', 'error');
      return;
    }
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
      showMessage(payload.message || 'Documento integrado no PHC.', 'success');
      if (isProvisionalInvoice) {
        state.view = 'accounting';
        window.setTimeout(() => {
          window.location.href = '/document_ai/inbox?view=accounting';
        }, 700);
      }
    } catch (error) {
      setStatus(error.message || 'Não foi possível submeter a correspondência.', true);
      showMessage(error.message || 'Não foi possível submeter a correspondência.', 'error');
    } finally {
      state.submittingPhc = false;
      updateSubmitPhcButton();
    }
  }

  async function confirmDocumentControl() {
    if (!els.controlOkBtn || !state.currentDocumentId || state.submittingControl || state.controlOk) return;
    state.submittingControl = true;
    updateSubmitPhcButton();
    setStatus('A confirmar o Contrôle OK...');
    try {
      const payload = await fetchJson(`/api/document_ai/documents/${encodeURIComponent(state.currentDocumentId)}/control-ok`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ document: state.documentData || {} }),
      });
      state.controlOk = Boolean(payload.workflow?.control_ok);
      setStatus('Contrôle OK concluído. A validação está disponível.');
      showMessage('Contrôle OK concluído.', 'success');
    } catch (error) {
      setStatus(error.message || 'Não foi possível concluir o controlo.', true);
      showMessage(error.message || 'Não foi possível concluir o controlo.', 'error');
    } finally {
      state.submittingControl = false;
      updateSubmitPhcButton();
    }
  }

  els.backBtn?.addEventListener('click', () => { window.location.href = inboxUrl(); });
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
    state.view = allowedViews.has(requested) ? requested : 'home';
    renderViewTabs();
    renderModeCard();
  });
  els.gedFolderSelect?.addEventListener('change', () => {
    if (!state.documentData?.customer) return;
    state.gedFolderManuallySelected = true;
    state.documentData.customer.ged_folder = els.gedFolderSelect.value;
    state.documentData.customer.ged_folder_manually_selected = true;
    state.documentData.customer.ged_folder_suggested_by = '';
    renderGedDestination();
    setStatus(`Destino GED alterado para ${els.gedFolderSelect.selectedOptions[0]?.textContent || els.gedFolderSelect.value}.`);
  });
  els.accessBtn?.addEventListener('click', openAccessModal);
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
  els.openPdfBtn?.addEventListener('click', () => {
    const pdfUrl = state.currentDocumentId
      ? `/api/document_ai/documents/${encodeURIComponent(state.currentDocumentId)}/original`
      : state.previewUrl;
    if (pdfUrl) window.open(pdfUrl, '_blank', 'noopener,noreferrer');
  });
  els.splitBtn?.addEventListener('click', splitDocumentBatch);
  els.suggestBlsBtn?.addEventListener('click', suggestVirtualDeliveryNotes);
  els.splitLineBtn?.addEventListener('click', splitSelectedLineAcrossDeliveryNotes);
  els.linesBody?.addEventListener('click', (event) => {
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
    const input = event.target.closest('[data-line-description]');
    if (!input) return;
    const line = state.documentData?.lines?.[Number(input.dataset.lineDescription)];
    if (!line) return;
    line.description = input.value.trim();
    await saveAdjustedLines('Désignation enregistrée.');
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
  els.originFlow?.addEventListener('click', (event) => {
    const option = event.target.closest('[data-origin-index]');
    if (option) linkDocumentOrigin(option.dataset.originIndex);
  });
  els.originTabs?.addEventListener('click', (event) => {
    const key = event.target.closest('[data-origin-tab]')?.dataset.originTab;
    if (!key || key === state.activeOriginStage) return;
    state.activeOriginStage = key;
    const stages = [...els.originTabs.querySelectorAll('[data-origin-tab]')].map((button) => ({
      key: button.dataset.originTab,
      label: button.childNodes[0]?.textContent?.trim() || button.dataset.originTab,
      count: Number(button.querySelector('span')?.textContent || 0),
    }));
    renderOriginTabs(stages);
  });
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && els.accessModal?.classList.contains('sz_is_open')) closeAccessModal();
    if (event.key === 'Escape' && els.supplierModal?.classList.contains('sz_is_open')) closeSupplierModal();
    if (event.key === 'Escape' && els.projectModal?.classList.contains('sz_is_open')) closeProjectModal();
    if (event.key === 'Escape' && els.articleModal?.classList.contains('sz_is_open')) closeArticleModal();
  });
  window.addEventListener('beforeunload', cleanupPreview);

  renderViewTabs();
  renderModeCard();
  const documentId = initialParams.get('document_id');
  if (documentId) loadInboxDocument(documentId);
});
