(function () {
  const state = {
    rows: [],
    current: null,
    modules: [],
    selectedFestamp: String(window.ENTIDADES_INITIAL_FESTAMP || '').trim(),
    searchTimer: null,
  };

  const permissions = {
    create: !!window.FE_CAN_CREATE,
    edit: !!window.FE_CAN_EDIT,
    delete: !!window.FE_CAN_DELETE,
  };
  const logoEnabled = !!window.FE_LOGO_ENABLED;

  const els = {
    list: document.getElementById('entList'),
    listSummary: document.getElementById('entListSummary'),
    editorTitle: document.getElementById('entEditorTitle'),
    seriesTotal: document.getElementById('entSeriesTotal'),
    seriesAtivas: document.getElementById('entSeriesAtivas'),
    wsEstado: document.getElementById('entWsEstado'),
    modulesList: document.getElementById('entModulesList'),
    modulesSummary: document.getElementById('entModulesSummary'),
    search: document.getElementById('entSearch'),
    activeFilter: document.getElementById('entActiveFilter'),
    btnNewTop: document.getElementById('entBtnNewTop'),
    btnSaveBottom: document.getElementById('entBtnSaveBottom'),
    btnCancel: document.getElementById('entBtnCancel'),
    btnDelete: document.getElementById('entBtnDelete'),
    btnUploadLogo: document.getElementById('entBtnUploadLogo'),
    btnRemoveLogo: document.getElementById('entBtnRemoveLogo'),
    logoFile: document.getElementById('entLogoFile'),
    logoPreview: document.getElementById('entLogoPreview'),
    logoImg: document.getElementById('entLogoImg'),
    logoPlaceholder: document.getElementById('entLogoPlaceholder'),
    logoStatus: document.getElementById('entLogoStatus'),
    fields: {
      FESTAMP: document.getElementById('entFESTAMP'),
      NIF: document.getElementById('entNIF'),
      NOME: document.getElementById('entNOME'),
      NOMEFISCAL: document.getElementById('entNOMEFISCAL'),
      ATIVIDADE: document.getElementById('entATIVIDADE'),
      MORADA: document.getElementById('entMORADA'),
      MORADA2: document.getElementById('entMORADA2'),
      CODPOST: document.getElementById('entCODPOST'),
      LOCAL: document.getElementById('entLOCAL'),
      PAISISO2: document.getElementById('entPAISISO2'),
      EMAIL: document.getElementById('entEMAIL'),
      TELEFONE: document.getElementById('entTELEFONE'),
      ATIVA: document.getElementById('entATIVA'),
      OBS: document.getElementById('entOBS'),
      CERTNUM: document.getElementById('entCERTNUM'),
      ATCUD_PREFIX: document.getElementById('entATCUD_PREFIX'),
      QRVER: document.getElementById('entQRVER'),
      HASHVER: document.getElementById('entHASHVER'),
      KEYID: document.getElementById('entKEYID'),
      RSA_PRIV_PATH: document.getElementById('entRSA_PRIV_PATH'),
      RSA_PUB_PATH: document.getElementById('entRSA_PUB_PATH'),
      AT_WS_ATIVO: document.getElementById('entAT_WS_ATIVO'),
      AT_WS_AMBIENTE: document.getElementById('entAT_WS_AMBIENTE'),
      AT_WS_USER: document.getElementById('entAT_WS_USER'),
      AT_WS_PASS: document.getElementById('entAT_WS_PASS'),
      LOGOTIPO_PATH: document.getElementById('entLOGOTIPO_PATH'),
      DTCriacao: document.getElementById('entDTCriacao'),
      DTAlteracao: document.getElementById('entDTAlteracao'),
      USERCRIACAO: document.getElementById('entUSERCRIACAO'),
      USERALTERACAO: document.getElementById('entUSERALTERACAO'),
    },
  };

  const editableKeys = [
    'NIF', 'NOME', 'NOMEFISCAL', 'ATIVIDADE', 'MORADA', 'MORADA2', 'CODPOST', 'LOCAL', 'PAISISO2',
    'EMAIL', 'TELEFONE', 'ATIVA', 'OBS', 'CERTNUM', 'ATCUD_PREFIX', 'QRVER', 'HASHVER', 'KEYID',
    'RSA_PRIV_PATH', 'RSA_PUB_PATH', 'AT_WS_ATIVO', 'AT_WS_AMBIENTE', 'AT_WS_USER', 'AT_WS_PASS',
  ];

  const esc = (value) => String(value ?? '').replace(/[&<>"']/g, (match) => (
    { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[match]
  ));

  function showToast(message, type = 'success') {
    if (typeof window.showToast === 'function') {
      window.showToast(message, type);
      return;
    }
    window.alert(message);
  }

  function emptyRow() {
    return {
      FESTAMP: '',
      NIF: '',
      NOME: '',
      NOMEFISCAL: '',
      ATIVIDADE: '',
      MORADA: '',
      MORADA2: '',
      CODPOST: '',
      LOCAL: '',
      PAISISO2: 'PT',
      EMAIL: '',
      TELEFONE: '',
      ATIVA: 1,
      OBS: '',
      CERTNUM: '',
      ATCUD_PREFIX: '',
      QRVER: '',
      HASHVER: '',
      KEYID: '',
      RSA_PRIV_PATH: '',
      RSA_PUB_PATH: '',
      AT_WS_ATIVO: 0,
      AT_WS_AMBIENTE: '',
      AT_WS_USER: '',
      AT_WS_PASS: '',
      LOGOTIPO_PATH: '',
      DTCriacao: '',
      DTAlteracao: '',
      USERCRIACAO: '',
      USERALTERACAO: '',
      SERIES_TOTAL: 0,
      SERIES_ATIVAS: 0,
    };
  }

  function normalizeRow(row) {
    return { ...emptyRow(), ...(row || {}) };
  }

  function isExisting() {
    return !!String(els.fields.FESTAMP?.value || '').trim();
  }

  function canWriteCurrent() {
    return isExisting() ? permissions.edit : permissions.create;
  }

  function setEditable(enabled) {
    editableKeys.forEach((key) => {
      const field = els.fields[key];
      if (!field) return;
      field.disabled = !enabled;
    });
  }

  function modulesSummaryText() {
    const total = state.modules.length;
    const selected = state.modules.filter((item) => Number(item.ATIVO || 0) === 1).length;
    return `${selected} módulo${selected === 1 ? '' : 's'} associado${selected === 1 ? '' : 's'} / ${total}`;
  }

  function renderModules() {
    if (!els.modulesList) return;
    if (!state.modules.length) {
      els.modulesList.innerHTML = `
        <tr class="sz_table_row">
          <td colspan="4" class="sz_table_cell sz_text_muted">Sem módulos disponíveis.</td>
        </tr>
      `;
      if (els.modulesSummary) els.modulesSummary.textContent = '0 módulos associados';
      return;
    }

    els.modulesList.innerHTML = state.modules.map((row, idx) => `
      <tr class="sz_table_row">
        <td class="sz_table_cell">${esc(row.CODIGO || '')}</td>
        <td class="sz_table_cell">${esc(row.NOME || '')}</td>
        <td class="sz_table_cell">${esc(row.DESCR || '')}</td>
        <td class="sz_table_cell sz_text_right">
          <label class="sz_checkbox">
            <input type="checkbox" data-module-index="${idx}" ${Number(row.ATIVO || 0) === 1 ? 'checked' : ''} ${!canWriteCurrent() ? 'disabled' : ''}>
            <span></span>
          </label>
        </td>
      </tr>
    `).join('');

    if (els.modulesSummary) els.modulesSummary.textContent = modulesSummaryText();

    els.modulesList.querySelectorAll('[data-module-index]').forEach((node) => {
      node.addEventListener('change', () => {
        const index = Number(node.getAttribute('data-module-index'));
        if (Number.isNaN(index) || !state.modules[index]) return;
        state.modules[index].ATIVO = node.checked ? 1 : 0;
        if (els.modulesSummary) els.modulesSummary.textContent = modulesSummaryText();
      });
    });
  }

  function currentLogoUrl() {
    const festamp = String(els.fields.FESTAMP?.value || '').trim();
    const path = String(els.fields.LOGOTIPO_PATH?.value || '').trim();
    if (!logoEnabled || !festamp || !path) return '';
    return `/api/entidades/${encodeURIComponent(festamp)}/logo?_ts=${Date.now()}`;
  }

  function renderLogo() {
    if (!els.logoPreview) return;
    const festamp = String(els.fields.FESTAMP?.value || '').trim();
    const path = String(els.fields.LOGOTIPO_PATH?.value || '').trim();
    const canWrite = canWriteCurrent();
    const hasLogo = Boolean(festamp && path);
    if (els.btnUploadLogo) els.btnUploadLogo.disabled = !logoEnabled || !festamp || !canWrite;
    if (els.btnRemoveLogo) els.btnRemoveLogo.disabled = !logoEnabled || !hasLogo || !canWrite;
    if (els.logoStatus) {
      if (!logoEnabled) els.logoStatus.textContent = 'A base de dados ainda não tem o campo LOGOTIPO_PATH.';
      else if (!festamp) els.logoStatus.textContent = 'Guarde a entidade primeiro para carregar um logotipo.';
      else if (hasLogo) els.logoStatus.textContent = 'Logotipo carregado no servidor.';
      else els.logoStatus.textContent = 'Sem logotipo associado.';
    }
    if (els.logoImg) {
      if (hasLogo) {
        els.logoImg.src = currentLogoUrl();
        els.logoImg.style.display = '';
      } else {
        els.logoImg.removeAttribute('src');
        els.logoImg.style.display = 'none';
      }
    }
    if (els.logoPlaceholder) els.logoPlaceholder.style.display = hasLogo ? 'none' : '';
  }

  function updateButtons() {
    const existing = isExisting();
    const canWrite = canWriteCurrent();
    setEditable(canWrite);

    if (els.btnNewTop) els.btnNewTop.disabled = !permissions.create;
    if (els.btnSaveBottom) els.btnSaveBottom.disabled = !canWrite;
    if (els.btnDelete) els.btnDelete.disabled = !existing || !permissions.delete;
    renderModules();
    renderLogo();
  }

  function updateSummary(row) {
    const current = normalizeRow(row);
    if (els.editorTitle) {
      els.editorTitle.textContent = current.NOME || current.NOMEFISCAL || 'Nova entidade';
    }
    if (els.seriesTotal) els.seriesTotal.textContent = String(current.SERIES_TOTAL || 0);
    if (els.seriesAtivas) els.seriesAtivas.textContent = String(current.SERIES_ATIVAS || 0);
    if (els.wsEstado) els.wsEstado.textContent = current.AT_WS_ATIVO ? 'Ligado' : 'Desligado';
  }

  function fillForm(row) {
    const current = normalizeRow(row);
    state.current = current;
    Object.entries(els.fields).forEach(([key, field]) => {
      if (!field) return;
      if (field.type === 'checkbox') {
        field.checked = !!current[key];
      } else {
        field.value = current[key] ?? '';
      }
    });
    updateSummary(current);
    updateButtons();
  }

  function collectForm() {
    return {
      FESTAMP: String(els.fields.FESTAMP?.value || '').trim(),
      NIF: Number(els.fields.NIF?.value || 0),
      NOME: String(els.fields.NOME?.value || '').trim(),
      NOMEFISCAL: String(els.fields.NOMEFISCAL?.value || '').trim(),
      ATIVIDADE: String(els.fields.ATIVIDADE?.value || '').trim(),
      MORADA: String(els.fields.MORADA?.value || '').trim(),
      MORADA2: String(els.fields.MORADA2?.value || '').trim(),
      CODPOST: String(els.fields.CODPOST?.value || '').trim(),
      LOCAL: String(els.fields.LOCAL?.value || '').trim(),
      PAISISO2: String(els.fields.PAISISO2?.value || '').trim().toUpperCase(),
      EMAIL: String(els.fields.EMAIL?.value || '').trim(),
      TELEFONE: String(els.fields.TELEFONE?.value || '').trim(),
      ATIVA: els.fields.ATIVA?.checked ? 1 : 0,
      OBS: String(els.fields.OBS?.value || '').trim(),
      CERTNUM: String(els.fields.CERTNUM?.value || '').trim(),
      ATCUD_PREFIX: String(els.fields.ATCUD_PREFIX?.value || '').trim(),
      QRVER: String(els.fields.QRVER?.value || '').trim(),
      HASHVER: String(els.fields.HASHVER?.value || '').trim(),
      KEYID: String(els.fields.KEYID?.value || '').trim(),
      RSA_PRIV_PATH: String(els.fields.RSA_PRIV_PATH?.value || '').trim(),
      RSA_PUB_PATH: String(els.fields.RSA_PUB_PATH?.value || '').trim(),
      AT_WS_ATIVO: els.fields.AT_WS_ATIVO?.checked ? 1 : 0,
      AT_WS_AMBIENTE: String(els.fields.AT_WS_AMBIENTE?.value || '').trim(),
      AT_WS_USER: String(els.fields.AT_WS_USER?.value || '').trim(),
      AT_WS_PASS: String(els.fields.AT_WS_PASS?.value || '').trim(),
      LOGOTIPO_PATH: String(els.fields.LOGOTIPO_PATH?.value || '').trim(),
      MODULES: state.modules.map((item) => ({
        MODSTAMP: String(item.MODSTAMP || '').trim(),
        ATIVO: Number(item.ATIVO || 0),
        OBS: String(item.OBS || '').trim(),
      })),
    };
  }

  function listItemHtml(row) {
    const active = !!row.ATIVA;
    return `
      <div class="sz_panel sz_stack sz_entities_list_item ${state.selectedFestamp === row.FESTAMP ? 'sz_is_active' : ''}" data-festamp="${esc(row.FESTAMP)}">
        <div class="sz_entities_list_item_head">
          <div>
            <div class="sz_label">${esc(row.NOME || row.NOMEFISCAL || '(Sem nome)')}</div>
            <div class="sz_text_muted">NIF ${esc(row.NIF || '')}</div>
          </div>
          <span class="sz_entities_badge ${active ? 'sz_is_active' : 'sz_is_inactive'}">${active ? 'Ativa' : 'Inativa'}</span>
        </div>
        <div class="sz_entities_meta">
          <span><strong>Local:</strong> ${esc(row.LOCAL || '-')}</span>
          <span><strong>País:</strong> ${esc(row.PAISISO2 || '-')}</span>
          <span><strong>Séries:</strong> ${esc(row.SERIES_ATIVAS || 0)}/${esc(row.SERIES_TOTAL || 0)}</span>
          <span><strong>Cert.:</strong> ${esc(row.CERTNUM || '-')}</span>
        </div>
      </div>
    `;
  }

  function renderList() {
    if (!els.list) return;
    if (!state.rows.length) {
      els.list.innerHTML = '<div class="sz_panel sz_entities_empty">Sem entidades para os filtros aplicados.</div>';
      if (els.listSummary) els.listSummary.textContent = '0 entidades';
      return;
    }

    els.list.innerHTML = state.rows.map(listItemHtml).join('');
    if (els.listSummary) {
      els.listSummary.textContent = `${state.rows.length} entidade${state.rows.length === 1 ? '' : 's'}`;
    }
    els.list.querySelectorAll('[data-festamp]').forEach((node) => {
      node.addEventListener('click', () => openDetail(node.getAttribute('data-festamp') || ''));
    });
  }

  async function loadList() {
    if (!els.list) return;
    const qs = new URLSearchParams();
    const q = String(els.search?.value || '').trim();
    const active = String(els.activeFilter?.value || '').trim();
    if (q) qs.set('q', q);
    if (active) qs.set('active', active);

    els.list.innerHTML = '<div class="sz_panel sz_entities_empty">A carregar...</div>';

    try {
      const res = await fetch(`/api/entidades?${qs.toString()}`);
      const data = await res.json().catch(() => ({}));
      if (!res.ok || data.error) throw new Error(data.error || 'Erro ao carregar entidades.');
      state.rows = Array.isArray(data.rows) ? data.rows : [];
      renderList();

      const targetFestamp = state.selectedFestamp || (state.rows[0]?.FESTAMP || '');
      if (targetFestamp) {
        await openDetail(targetFestamp, { silent: true });
      } else {
        fillForm(emptyRow());
      }
    } catch (error) {
      state.rows = [];
      els.list.innerHTML = `<div class="sz_panel sz_entities_empty">${esc(error.message || 'Erro ao carregar entidades.')}</div>`;
      if (els.listSummary) els.listSummary.textContent = '0 entidades';
      fillForm(emptyRow());
    }
  }

  async function openDetail(festamp, options = {}) {
    const normalized = String(festamp || '').trim();
    if (!normalized) {
      state.selectedFestamp = '';
      state.modules = [];
      fillForm(emptyRow());
      renderList();
      return;
    }
    try {
      const res = await fetch(`/api/entidades/${encodeURIComponent(normalized)}`);
      const data = await res.json().catch(() => ({}));
      if (!res.ok || data.error) throw new Error(data.error || 'Erro ao carregar entidade.');
      state.selectedFestamp = normalized;
      state.modules = Array.isArray(data.modules) ? data.modules : [];
      fillForm(data.row || {});
      renderList();
    } catch (error) {
      if (!options.silent) showToast(error.message || 'Erro ao carregar entidade.', 'danger');
    }
  }

  async function newEntity() {
    state.selectedFestamp = '';
    try {
      const res = await fetch('/api/entidades/modules');
      const data = await res.json().catch(() => ({}));
      if (!res.ok || data.error) throw new Error(data.error || 'Erro ao carregar módulos.');
      state.modules = Array.isArray(data.rows) ? data.rows : [];
    } catch (error) {
      state.modules = [];
      showToast(error.message || 'Erro ao carregar módulos.', 'danger');
    }
    fillForm(emptyRow());
    renderList();
    if (els.fields.NIF) els.fields.NIF.focus();
  }

  async function saveEntity() {
    if (!canWriteCurrent()) return;
    const row = collectForm();
    try {
      const res = await fetch('/api/entidades/save', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ row, modules: row.MODULES }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok || data.error) throw new Error(data.error || 'Erro ao gravar entidade.');
      state.selectedFestamp = String(data.festamp || row.FESTAMP || '').trim();
      showToast('Entidade gravada.', 'success');
      await loadList();
    } catch (error) {
      showToast(error.message || 'Erro ao gravar entidade.', 'danger');
    }
  }

  async function uploadLogo(file) {
    const festamp = String(els.fields.FESTAMP?.value || '').trim();
    if (!logoEnabled || !festamp || !file) return;
    const formData = new FormData();
    formData.append('file', file);
    try {
      const res = await fetch(`/api/entidades/${encodeURIComponent(festamp)}/upload_logo`, {
        method: 'POST',
        body: formData,
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok || data.error) throw new Error(data.error || 'Erro ao carregar logotipo.');
      if (els.fields.LOGOTIPO_PATH) els.fields.LOGOTIPO_PATH.value = String(data.LOGOTIPO_PATH || '').trim();
      renderLogo();
      showToast('Logotipo carregado.', 'success');
    } catch (error) {
      showToast(error.message || 'Erro ao carregar logotipo.', 'danger');
    } finally {
      if (els.logoFile) els.logoFile.value = '';
    }
  }

  async function removeLogo() {
    const festamp = String(els.fields.FESTAMP?.value || '').trim();
    if (!logoEnabled || !festamp || !String(els.fields.LOGOTIPO_PATH?.value || '').trim()) return;
    try {
      const res = await fetch(`/api/entidades/${encodeURIComponent(festamp)}/delete_logo`, { method: 'POST' });
      const data = await res.json().catch(() => ({}));
      if (!res.ok || data.error) throw new Error(data.error || 'Erro ao remover logotipo.');
      if (els.fields.LOGOTIPO_PATH) els.fields.LOGOTIPO_PATH.value = '';
      renderLogo();
      showToast('Logotipo removido.', 'success');
    } catch (error) {
      showToast(error.message || 'Erro ao remover logotipo.', 'danger');
    }
  }

  async function deleteEntity() {
    const festamp = String(els.fields.FESTAMP?.value || '').trim();
    if (!festamp || !permissions.delete) return;
    const nome = String(els.fields.NOME?.value || els.fields.NOMEFISCAL?.value || festamp).trim();
    if (!window.confirm(`Eliminar a entidade "${nome}"?`)) return;
    try {
      const res = await fetch(`/api/entidades/${encodeURIComponent(festamp)}/delete`, {
        method: 'POST',
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok || data.error) throw new Error(data.error || 'Erro ao eliminar entidade.');
      showToast('Entidade eliminada.', 'success');
      state.selectedFestamp = '';
      await loadList();
    } catch (error) {
      showToast(error.message || 'Erro ao eliminar entidade.', 'danger');
    }
  }

  function cancelEdit() {
    if (state.selectedFestamp) {
      openDetail(state.selectedFestamp, { silent: true });
      return;
    }
    newEntity();
  }

  function bindEvents() {
    els.btnNewTop?.addEventListener('click', newEntity);
    els.btnSaveBottom?.addEventListener('click', saveEntity);
    els.btnCancel?.addEventListener('click', cancelEdit);
    els.btnDelete?.addEventListener('click', deleteEntity);
    els.btnUploadLogo?.addEventListener('click', () => {
      if (!logoEnabled) {
        showToast('A base de dados ainda não tem o campo LOGOTIPO_PATH.', 'danger');
        return;
      }
      if (!String(els.fields.FESTAMP?.value || '').trim()) {
        showToast('Guarde primeiro a entidade antes de carregar o logotipo.', 'warning');
        return;
      }
      els.logoFile?.click();
    });
    els.btnRemoveLogo?.addEventListener('click', removeLogo);
    els.logoFile?.addEventListener('change', () => {
      const file = els.logoFile?.files?.[0];
      if (file) uploadLogo(file);
    });
    els.search?.addEventListener('input', () => {
      window.clearTimeout(state.searchTimer);
      state.searchTimer = window.setTimeout(loadList, 250);
    });
    els.activeFilter?.addEventListener('change', loadList);
    document.addEventListener('keydown', (event) => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 's') {
        event.preventDefault();
        saveEntity();
      }
    });
  }

  bindEvents();
  fillForm(emptyRow());
  updateButtons();
  loadList();
})();
