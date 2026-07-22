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
    originSearchToken: 0,
    originPayload: null,
    originCandidates: [],
    selectedOrigins: [],
    selectedProject: null,
    projectCandidates: [],
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
    integratedPhc: false,
    integrationResult: null,
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
    mail: 'Correio',
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

  function gedCompanyFolder(customer = {}) {
    if (customer.ged_folder) return gedSafePart(customer.ged_folder, 'PASTA-POR-CONFIGURAR');
    const name = gedSafePart(customer.name, '');
    const mappings = [
      [/INTERSOL.*ALSACE|INTERSOL_AL/, 'HSOLS_INTERSOL_AL'],
      [/HSOLS.*FRANCE|HSOLS_FR/, 'HSOLS_FR'],
      [/INTERSOL.*LORRAINE|INTERSOL_LOR/, 'HSOLS_INTERSOL_LOR'],
      [/INTERSOL.*CH|INTERSOL_CH/, 'HSOLS_INTERSOL_CH'],
      [/INTERSOL/, 'HSOLS_INTERSOL_AL'],
      [/GR.?360/, 'HSOLS_GR360_PT'],
      [/HSOLS.*CH|HSOLS_CH/, 'HSOLS_CH'],
      [/HSOLS.*DE|HSOLS_DE/, 'HSOLS_DE'],
      [/HSOLS.*ES|HSOLS_ES/, 'HSOLS_ES'],
      [/HSOLS.*PT|HSOLS_PT/, 'HSOLS_PT'],
    ];
    return mappings.find(([pattern]) => pattern.test(name))?.[1] || 'PASTA-EMPRESA-POR-CONFIGURAR';
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
    const party = documentData.supplier || {};
    const isMail = documentData.document_type === 'mail';
    const isCustomerParty = isMail && documentData.external_party_role === 'customer';
    const isUnregisteredMailParty = isMail && !['customer', 'supplier'].includes(documentData.external_party_role);
    const partyNumber = Number(isCustomerParty ? party.customer_no : party.supplier_no || party.no || 0);
    const partyNumberPart = partyNumber ? String(partyNumber) : 'SEM-NUMERO';
    const partyNamePart = gedPartyName(party.name || party.llm_name);
    const documentNumber = gedSafePart(documentData.document_number, 'SEM-DOCUMENTO');
    const mailTitlePart = isMail ? gedSafePart(documentData.mail_title, '') : '';
    const project = gedSafePart(state.selectedProject?.ccusto || documentData.origin_project?.ccusto, '');
    const documentDate = gedSafePart(documentData.document_date, gedSafePart(new Date().toISOString().slice(0, 10), 'SEM-DATA'));
    let prefix = 'DOC';
    let category = 'DOCUMENTS_FOURNISSEURS';
    let destinations = [{ label: 'Documentos de fornecedores', category }];
    let trailingPart = documentNumber;

    if (isMail) {
      prefix = documentData.mail_category === 'legal' ? 'JUR' : 'COR';
      category = documentData.mail_category === 'legal' ? 'JURIDIQUE' : 'COURRIER_INTERNE_EXTERIEUR';
      destinations = [{ label: documentData.mail_category === 'legal' ? 'Jurídico' : 'Correio recebido', category }];
      trailingPart = documentDate;
    } else if (['invoice', 'credit_note', 'debit_note', 'proforma_invoice', 'provisional_invoice'].includes(documentData.document_type)) {
      prefix = 'FAC';
      category = 'FACTURATION_FOURNISSEURS';
      destinations = [
        { label: 'Correio recebido', category: 'COURRIER_INTERNE_EXTERIEUR' },
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
      path: `\\\\10.0.1.11\\ged\\${companyFolder}\\${destination.category}\\${period.year}\\${period.month}\\${fileName}`,
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
    const isMail = documentData.document_type === 'mail';
    const isProvisionalInvoice = ['invoice', 'provisional_invoice'].includes(documentData.document_type);
    const allowed = (isMail && els.submitPhcBtn.dataset.canCorrespondence === '1')
      || (isProvisionalInvoice && els.submitPhcBtn.dataset.canProvisionalInvoice === '1');
    els.submitPhcBtn.hidden = !allowed;
    if (!allowed) return;
    const ready = Boolean(
      state.file
      && documentData.customer?.feid
      && String(party.name || party.llm_name || '').trim()
      && (isMail || Number(party.supplier_no || party.no || 0) > 0)
      && state.correspondenceReference
      && (isMail || (String(documentData.document_number || '').trim() && Array.isArray(documentData.lines) && documentData.lines.length))
    );
    els.submitPhcBtn.disabled = !ready || state.submittingPhc || state.integratedPhc;
    if (state.integratedPhc) {
      els.submitPhcBtn.innerHTML = '<i class="fa-solid fa-circle-check"></i><span>Submetido no PHC</span>';
    } else if (state.submittingPhc) {
      els.submitPhcBtn.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin"></i><span>A submeter...</span>';
    } else {
      els.submitPhcBtn.innerHTML = '<i class="fa-solid fa-paper-plane"></i><span>Submeter no PHC</span>';
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
    state.submittingPhc = false;
    state.integratedPhc = false;
    state.integrationResult = null;
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
    window.history.replaceState({}, '', '/document_ai/extract');
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
      ? `<i class="fa-solid fa-code-branch"></i><span>Repartir linha por ${proportionalGroups.length} BL(s)</span>`
      : '<i class="fa-solid fa-code-branch"></i><span>Seleciona uma linha para repartir</span>';
    els.lineCount.textContent = `${items.length} linha(s)`;
    if (!items.length) {
      els.linesBody.innerHTML = '<tr><td colspan="11" class="sz_text_muted">Não foram encontradas linhas comerciais visíveis.</td></tr>';
      return;
    }
    let previousDeliveryNote = '';
    els.linesBody.innerHTML = items.map((line, lineIndex) => {
      const deliveryNote = String(line.origin_delivery_note_number || '').trim();
      const groupHeading = deliveryNote && deliveryNote !== previousDeliveryNote
        ? `<tr class="docai-extract-line-origin"><td colspan="11"><i class="fa-solid fa-truck-ramp-box"></i><strong>Bon de Livraison ${escapeHtml(deliveryNote)}</strong></td></tr>`
        : '';
      previousDeliveryNote = deliveryNote;
      const originMatches = state.originLineMatchByLine.get(line) || [];
      const originReferences = originMatches.map((originMatch) => {
        const originReasons = Array.isArray(originMatch.reasons) ? originMatch.reasons.join(' · ') : '';
        const originTitle = `${originMatch.origin_reference_label || 'BC'}${originMatch.origin_description ? ` · ${originMatch.origin_description}` : ''}${originReasons ? ` · ${originReasons}` : ''}`;
        return `<span class="docai-extract-bc-ref" title="${escapeHtml(originTitle)}">${escapeHtml(originMatch.origin_ref)}</span>`;
      }).join('');
      const selectedForSplit = state.selectedSplitLine === line;
      const allocationHint = line._virtual_split_allocation
        ? `<small class="docai-extract-split-hint"><i class="fa-solid fa-code-branch"></i> ${escapeHtml(formatNumber(Number(line._virtual_split_ratio || 0) * 100, 2))}% repartido para este BL</small>`
        : '';
      return `${groupHeading}<tr class="${selectedForSplit ? 'is-selected-for-split' : ''}${line._virtual_split_allocation ? ' is-split-allocation' : ''}">
        <td class="docai-extract-line-picker-cell"><button type="button" class="docai-extract-line-picker" data-line-select="${lineIndex}" aria-label="${selectedForSplit ? 'Desmarcar' : 'Selecionar'} linha para repartir" aria-pressed="${selectedForSplit ? 'true' : 'false'}"><i class="fa-${selectedForSplit ? 'solid fa-circle-check' : 'regular fa-circle'}"></i></button></td>
        <td>${escapeHtml(line.ref || '--')}</td>
        <td class="docai-extract-bc-ref-cell">${originReferences || '<span class="sz_text_muted">--</span>'}</td>
        <td class="docai-extract-description">${escapeHtml(line.description || '--')}${allocationHint}</td>
        <td class="docai-extract-number">${escapeHtml(formatNumber(line.qty))}</td>
        <td>${escapeHtml(line.unit || '--')}</td>
        <td class="docai-extract-number">${escapeHtml(formatMoney(line.unit_price, currency))}</td>
        <td class="docai-extract-number">${escapeHtml(`${formatNumber(line.discount, 2)}%`)}</td>
        <td class="docai-extract-number">${escapeHtml(`${formatNumber(line.tax_rate, 2)}%`)}</td>
        <td class="docai-extract-number">${escapeHtml(formatMoney(line.net_amount, currency))}</td>
        <td class="docai-extract-number">${escapeHtml(formatMoney(line.gross_amount, currency))}</td>
      </tr>`;
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
    const isMail = state.documentData?.document_type === 'mail';
    const isCustomerMail = isMail && state.documentData?.external_party_role === 'customer';
    const supplierNo = Number(isCustomerMail ? supplier.customer_no : (supplier.supplier_no || supplier.no) || 0);
    const matched = Boolean(supplierNo);
    els.partyLabel.textContent = isMail ? 'Remetente' : 'Fornecedor';
    els.supplierName.textContent = supplier.name || supplier.llm_name || '--';
    els.supplierTax.textContent = supplier.tax_id
      ? `${isCustomerMail ? 'NIF' : 'NIF/NCONT'}: ${supplier.tax_id}`
      : `${isCustomerMail ? 'NIF' : 'NIF/NCONT'} não identificado`;
    if (isMail) {
      els.supplierNo.hidden = false;
      const roleLabel = isCustomerMail ? 'cliente' : (state.documentData?.external_party_role === 'supplier' ? 'fornecedor' : 'entidade');
      els.supplierNo.textContent = `Nº ${roleLabel}: ${supplierNo || '--'}`;
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
    els.supplierNo.textContent = `Nº fornecedor: ${supplierNo || '--'}`;
    els.supplierCard.classList.toggle('is-unmatched', !matched);
    els.supplierCard.classList.toggle('is-matched', matched);
    els.supplierHint.innerHTML = matched
      ? '<i class="fa-solid fa-pen"></i> Alterar fornecedor'
      : '<i class="fa-solid fa-hand-pointer"></i> Escolher fornecedor semelhante';
    els.supplierCard.setAttribute('aria-label', matched ? 'Alterar fornecedor' : 'Escolher fornecedor semelhante');
    if (!matching?.supplier_query?.feid) {
      els.supplierHint.innerHTML = `<i class="fa-solid fa-triangle-exclamation"></i> ${state.documentData?.document_type === 'mail' ? 'Entidade' : 'Empresa cliente'} não identificada na FE`;
    } else if (matching?.supplier_lookup_error) {
      els.supplierHint.innerHTML = '<i class="fa-solid fa-triangle-exclamation"></i> Não foi possível consultar a FL';
    }
  }

  function renderCustomerCard(customer = {}, matching = {}) {
    const isMail = state.documentData?.document_type === 'mail';
    const matched = Boolean(customer.feid && matching.customer_matched !== false);
    els.customerLabel.textContent = isMail ? 'Entidade' : 'Empresa cliente';
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
    const isMail = state.documentData.document_type === 'mail';
    const endpoint = isMail ? 'external-parties' : 'suppliers';
    try {
      const items = await fetchJson(`/api/document_ai/${endpoint}/search?q=${encodeURIComponent(query)}&feid=${feid}&limit=12`);
      const selected = Array.isArray(items) && Number(items[0]?.score || 0) >= 0.72 ? items[0] : null;
      const isCustomer = isMail && selected?.party_role === 'customer';
      state.matching.supplier_candidates = Array.isArray(items) ? items : [];
      state.supplierCandidates = state.matching.supplier_candidates;
      if (selected) {
        if (isMail) state.documentData.external_party_role = isCustomer ? 'customer' : 'supplier';
        state.documentData.supplier = {
          ...party,
          supplier_no: null,
          customer_no: null,
          name: selected.name || party.name,
          tax_id: selected.tax_id || party.tax_id,
          feid,
          ...(isCustomer ? { customer_no: selected.no } : { supplier_no: selected.no }),
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
    const isMail = state.documentData.document_type === 'mail';
    if (previousFeid !== Number(selected.feid || 0)) {
      state.selectedOrigins = [];
      state.selectedProject = null;
      state.projectSuggestionDismissed = false;
      state.originLineMatches = [];
      state.originLineReferenceLabel = '';
      renderProjectCard();
    }
    state.documentData.customer = {
      ...state.documentData.customer,
      feid: selected.feid,
      name: selected.name,
      tax_id: selected.tax_id || '',
      manually_selected: true,
      matched_by: 'manual',
    };
    state.matching.customer_matched = true;
    state.matching.customer = { ...selected, matched_by: 'manual' };
    state.matching.supplier_query = { ...(state.matching.supplier_query || {}), feid: selected.feid };
    renderCustomerCard(state.documentData.customer, state.matching);
    closeEntityModal();
    await Promise.all([rematchExternalParty(), loadCorrespondenceReference()]);
    if (!isMail) loadOriginCandidates(state.documentData);
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
      ? `${payload.phc_database || 'PHC'} · Fornecedor nº ${payload.supplier?.no || '--'}${payload.selected_project?.ccusto ? ` · Obra ${payload.selected_project.ccusto}` : ''}`
      : '';
    if (!options.skipLineMapping) applyOriginLineReferences(payload);

    const virtualStageHtml = renderVirtualDeliveryNoteStage();

    if (!payload.available) {
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
            <em><i class="fa-solid ${selected ? 'fa-circle-minus' : 'fa-plus'}"></i> ${selected ? 'Desselecionar origem' : 'Selecionar como origem'}</em>
          </button>`;
      }).join('');
      const realStageHtml = `
        <article class="docai-extract-origin-stage">
          <div class="docai-extract-origin-stage-title"><strong>${escapeHtml(stage.display_order || '')} ${escapeHtml(stage.label || stage.key)}</strong></div>
          <div class="docai-extract-origin-options">${cards}</div>
        </article>`;
      return `${insertVirtualBefore ? virtualStageHtml : ''}${realStageHtml}`;
    }).join('');
    if (virtualStageHtml && !virtualStageInserted) stageHtml += virtualStageHtml;

    els.originFlow.innerHTML = stageHtml || '<div class="docai-extract-origin-unavailable"><i class="fa-solid fa-magnifying-glass"></i><span>Sem documentos anteriores disponíveis para ligar.</span></div>';
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
      <article class="docai-extract-origin-stage is-virtual-stage">
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
    els.projectModal.classList.remove('sz_is_open');
    els.projectModal.setAttribute('aria-hidden', 'true');
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

  async function selectProject(index) {
    const selected = state.projectCandidates[Number(index)];
    if (!selected || !state.documentData) return;
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
    const isMail = state.documentData?.document_type === 'mail';
    state.supplierCandidates = Array.isArray(items) ? items : [];
    if (!state.supplierCandidates.length) {
      els.supplierModalList.innerHTML = `<div class="docai-empty-state">Não foram encontrados ${isMail ? 'clientes ou fornecedores' : 'fornecedores'} semelhantes nesta entidade.</div>`;
      return;
    }
    els.supplierModalList.innerHTML = state.supplierCandidates.map((item, index) => {
      const score = Math.round(Math.max(0, Math.min(1, Number(item.score || 0))) * 100);
      const taxLabel = String(item.tax_field || 'nif').toUpperCase();
      const matchLabel = item.matched_by === 'tax_id' ? `${taxLabel} coincidente` : 'Nome semelhante';
      const partyLabel = item.party_role === 'customer' ? 'Cliente' : 'Fornecedor';
      return `
        <button type="button" class="docai-supplier-match-option" data-supplier-index="${index}">
          <span class="docai-supplier-match-main">
            <strong>${escapeHtml(item.name || '--')}</strong>
            <span>Nº ${escapeHtml(item.no || '--')} · ${escapeHtml(taxLabel)} ${escapeHtml(item.tax_id || '--')}</span>
          </span>
          <span class="docai-supplier-match-score">${isMail ? `${escapeHtml(partyLabel)} · ` : ''}${escapeHtml(matchLabel)} · ${score}%</span>
        </button>
      `;
    }).join('');
  }

  function openSupplierModal() {
    const isMail = state.documentData?.document_type === 'mail';
    const feid = Number(state.matching?.supplier_query?.feid || state.documentData?.customer?.feid || 0);
    if (!feid) {
      showMessage('Não foi possível identificar a entidade na tabela FE.', 'error');
      return;
    }
    const customerName = state.documentData?.customer?.name || `FE ${feid}`;
    const supplier = state.documentData?.supplier || {};
    els.supplierModalTitle.textContent = isMail ? 'Escolher cliente ou fornecedor' : 'Escolher fornecedor';
    els.supplierModalContext.textContent = `${isMail ? 'Clientes e fornecedores' : 'Fornecedores'} de ${customerName} · FEID ${feid}`;
    els.supplierModalSearch.value = supplier.llm_name || supplier.name || supplier.llm_tax_id || supplier.tax_id || '';
    els.supplierManualBtn.hidden = !isMail;
    renderSupplierCandidates(state.matching?.supplier_candidates || []);
    els.supplierModal.classList.add('sz_is_open');
    els.supplierModal.setAttribute('aria-hidden', 'false');
    window.setTimeout(() => els.supplierModalSearch.focus(), 50);
  }

  async function searchSupplierCandidates() {
    const isMail = state.documentData?.document_type === 'mail';
    const feid = Number(state.matching?.supplier_query?.feid || state.documentData?.customer?.feid || 0);
    const query = els.supplierModalSearch.value.trim();
    if (!feid || query.length < 2) {
      showMessage('Indica pelo menos dois caracteres para pesquisar.', 'error');
      return;
    }
    els.supplierModalSearchBtn.disabled = true;
    els.supplierModalList.innerHTML = `<div class="docai-empty-state">A procurar ${isMail ? 'clientes e fornecedores' : 'fornecedores'} semelhantes...</div>`;
    try {
      const searchToken = ++state.supplierSearchToken;
      const params = new URLSearchParams({ q: query, feid: String(feid), limit: '12' });
      const items = await fetchJson(`/api/document_ai/${isMail ? 'external-parties' : 'suppliers'}/search?${params.toString()}`);
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
    if (state.documentData?.document_type !== 'mail' || name.length < 2) {
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
    const isMail = state.documentData.document_type === 'mail';
    const isCustomer = isMail && selected.party_role === 'customer';
    if (isMail) state.documentData.external_party_role = isCustomer ? 'customer' : 'supplier';
    state.documentData.supplier = {
      ...current,
      supplier_no: null,
      customer_no: null,
      ...(isCustomer ? { customer_no: selected.no } : { supplier_no: selected.no }),
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
    renderGedDestination();
    closeSupplierModal();
    setStatus(`${isCustomer ? 'Cliente' : 'Fornecedor'} ${selected.name} (#${selected.no}) selecionado.`);
    showMessage(`${isCustomer ? 'Cliente' : 'Fornecedor'} selecionado.`, 'success');
    if (state.documentData.document_type !== 'mail') loadOriginCandidates(state.documentData);
  }

  function renderResult(payload) {
    const documentData = payload.document || {};
    const customer = documentData.customer || {};
    const supplier = documentData.supplier || {};
    const totals = documentData.totals || {};
    const currency = documentData.currency || '';
    const isMail = documentData.document_type === 'mail';

    state.documentData = documentData;
    state.submittingPhc = false;
    state.integratedPhc = false;
    state.integrationResult = null;
    if (state.selectedProject?.ccusto) state.documentData.origin_project = { ...state.selectedProject };
    state.matching = payload.matching || {};
    state.supplierCandidates = state.matching.supplier_candidates || [];
    renderDocumentBatch(documentData.document_batch || {});
    if (isMail) els.batchAlert.hidden = true;
    renderCustomerCard(customer, state.matching);
    renderSupplierCard(supplier, state.matching);
    renderProjectCard();
    els.projectCard.hidden = isMail;
    els.originSection.hidden = isMail;
    els.linesSection.hidden = isMail;
    els.totalsSection.hidden = isMail;
    els.persistenceNote.textContent = isMail
      ? 'O correio foi analisado apenas neste ecrã e não foi adicionado ao inbox.'
      : 'O PDF e a leitura ficam guardados no inbox para evitar novas chamadas ao LLM.';
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
    const readingSource = payload.cached ? 'Leitura guardada' : `Leitura concluída com ${payload.model || 'LLM'}`;
    els.resultMeta.textContent = `${readingSource} · ${documentData.visible_language || 'idioma não identificado'}${batchSuffix}`;
    els.empty.hidden = true;
    els.loading.hidden = true;
    els.results.hidden = false;
    if (isMail) {
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
    if (!state.file || !['mail', 'invoice', 'provisional_invoice'].includes(documentType)) {
      showMessage('Carrega e valida primeiro um documento compatível.', 'error');
      return;
    }
    state.submittingPhc = true;
    updateSubmitPhcButton();
    const isProvisionalInvoice = ['invoice', 'provisional_invoice'].includes(documentType);
    setStatus(isProvisionalInvoice
      ? 'A criar a correspondência, a Facture Provisoire, as linhas e os anexos no PHC...'
      : 'A reservar a numeração, guardar o PDF no GED e criar a correspondência no PHC...');
    const formData = new FormData();
    formData.append('file', state.file);
    formData.append('document_data', JSON.stringify(state.documentData));
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
        : (isProvisionalInvoice ? 'A fatura foi integrada como V/Facture, com linhas e anexos.' : 'O correio foi guardado no GED e integrado no PHC.');
      setStatus(payload.message || 'Documento integrado no PHC.');
      showMessage(payload.message || 'Documento integrado no PHC.', 'success');
    } catch (error) {
      setStatus(error.message || 'Não foi possível submeter a correspondência.', true);
      showMessage(error.message || 'Não foi possível submeter a correspondência.', 'error');
    } finally {
      state.submittingPhc = false;
      updateSubmitPhcButton();
    }
  }

  els.backBtn?.addEventListener('click', () => { window.location.href = '/document_ai/inbox'; });
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
    const picker = event.target.closest('[data-line-select]');
    if (picker) selectLineForSplit(Number(picker.dataset.lineSelect));
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
  els.originFlow?.addEventListener('click', (event) => {
    const option = event.target.closest('[data-origin-index]');
    if (option) linkDocumentOrigin(option.dataset.originIndex);
  });
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && els.accessModal?.classList.contains('sz_is_open')) closeAccessModal();
    if (event.key === 'Escape' && els.supplierModal?.classList.contains('sz_is_open')) closeSupplierModal();
    if (event.key === 'Escape' && els.projectModal?.classList.contains('sz_is_open')) closeProjectModal();
  });
  window.addEventListener('beforeunload', cleanupPreview);

  const documentId = new URLSearchParams(window.location.search).get('document_id');
  if (documentId) loadInboxDocument(documentId);
});
