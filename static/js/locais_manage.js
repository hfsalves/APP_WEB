(function () {
  const currentEntity = window.LOCAIS_CURRENT_ENTITY || {};
  const state = {
    rows: [],
    selectedStamp: String(window.LOCAIS_INITIAL_STAMP || '').trim(),
    current: null,
    searchTimer: null,
    clientTimer: null,
    clientResults: [],
    selectedClient: null,
  };

  const permissions = {
    create: !!window.LOCAIS_CAN_CREATE,
    edit: !!window.LOCAIS_CAN_EDIT,
    delete: !!window.LOCAIS_CAN_DELETE,
  };

  const els = {
    list: document.getElementById('locList'),
    listSummary: document.getElementById('locListSummary'),
    editorTitle: document.getElementById('locEditorTitle'),
    btnNewTop: document.getElementById('locBtnNewTop'),
    btnSaveBottom: document.getElementById('locBtnSaveBottom'),
    btnCancel: document.getElementById('locBtnCancel'),
    btnDelete: document.getElementById('locBtnDelete'),
    filters: {
      search: document.getElementById('locFilterSearch'),
      ownerType: document.getElementById('locFilterOwnerType'),
      ativo: document.getElementById('locFilterAtivo'),
    },
    fields: {
      LOCALSTAMP: document.getElementById('locLOCALSTAMP'),
      OWNER_TYPE: document.getElementById('locOwnerType'),
      NO: document.getElementById('locClientNo'),
      DESIGNACAO: document.getElementById('locDESIGNACAO'),
      MORADA: document.getElementById('locMORADA'),
      MORADA2: document.getElementById('locMORADA2'),
      CP: document.getElementById('locCP'),
      LOCALIDADE: document.getElementById('locLOCALIDADE'),
      PAIS: document.getElementById('locPAIS'),
      ATIVO: document.getElementById('locATIVO'),
    },
    ownerFeWrap: document.getElementById('locOwnerFeWrap'),
    ownerFeLabel: document.getElementById('locOwnerFeLabel'),
    ownerClientWrap: document.getElementById('locOwnerClientWrap'),
    clientSearch: document.getElementById('locClientSearch'),
    clientResults: document.getElementById('locClientResults'),
    clientSelected: document.getElementById('locClientSelected'),
  };

  const editableKeys = ['OWNER_TYPE', 'DESIGNACAO', 'MORADA', 'MORADA2', 'CP', 'LOCALIDADE', 'PAIS', 'ATIVO'];

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

  async function fetchJson(url, options = {}) {
    const response = await fetch(url, options);
    const text = await response.text();
    let data = {};
    if (text) {
      try { data = JSON.parse(text); } catch (_) { data = {}; }
    }
    if (!response.ok || data.error) throw new Error(data.error || 'Erro de comunicação.');
    return data;
  }

  function emptyRow() {
    return {
      LOCALSTAMP: '',
      OWNER_TYPE: 'FE',
      NO: 0,
      FEID: Number(currentEntity.FEID || 0),
      OWNER_LABEL: String(currentEntity.NOMEFISCAL || currentEntity.NOME || '').trim(),
      DESIGNACAO: '',
      MORADA: '',
      MORADA2: '',
      CP: '',
      LOCALIDADE: '',
      PAIS: 'PT',
      ATIVO: 1,
    };
  }

  function normalizeRow(row) {
    const current = { ...emptyRow(), ...(row || {}) };
    current.OWNER_TYPE = String(current.OWNER_TYPE || (Number(current.NO || 0) > 0 ? 'CLIENTE' : 'FE')).trim().toUpperCase() || 'FE';
    current.NO = Number(current.NO || current.CLIENTE_NO || 0);
    current.FEID = Number(current.FEID || current.ENTITY_FEID || 0);
    return current;
  }

  function isExisting() {
    return !!String(els.fields.LOCALSTAMP?.value || '').trim();
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
    if (els.clientSearch) {
      const allowClient = enabled && String(els.fields.OWNER_TYPE?.value || '').trim().toUpperCase() === 'CLIENTE';
      els.clientSearch.disabled = !allowClient;
    }
  }

  function updateButtons() {
    if (els.btnNewTop) els.btnNewTop.disabled = !permissions.create;
    if (els.btnSaveBottom) els.btnSaveBottom.disabled = !canWriteCurrent();
    if (els.btnDelete) els.btnDelete.disabled = !isExisting() || !permissions.delete;
    setEditable(canWriteCurrent());
  }

  function renderClientResults() {
    if (!els.clientResults) return;
    if (!state.clientResults.length) {
      els.clientResults.innerHTML = '';
      return;
    }
    els.clientResults.innerHTML = state.clientResults.map((row) => `
      <button type="button" class="sz_locais_client_result" data-no="${esc(row.NO)}">
        <strong>${esc(row.NOME || '')}</strong><br>
        <span class="sz_text_muted">${esc(row.NO)} · ${esc(row.LOCAL || '')}</span>
      </button>
    `).join('');
    els.clientResults.querySelectorAll('[data-no]').forEach((node) => {
      node.addEventListener('click', () => {
        const no = Number(node.getAttribute('data-no') || 0);
        const row = state.clientResults.find((item) => Number(item.NO || 0) === no);
        if (!row) return;
        applyClient(row);
      });
    });
  }

  function applyClient(row) {
    state.selectedClient = row ? { ...row } : null;
    if (els.fields.NO) els.fields.NO.value = state.selectedClient ? String(state.selectedClient.NO || '') : '';
    if (els.clientSelected) {
      els.clientSelected.textContent = state.selectedClient
        ? `${String(state.selectedClient.NOME || '').trim()}`
        : 'Sem cliente selecionado';
    }
    if (els.clientSearch && state.selectedClient) {
      els.clientSearch.value = String(state.selectedClient.NOME || '').trim();
    }
    state.clientResults = [];
    renderClientResults();
  }

  function updateOwnerUi() {
    const ownerType = String(els.fields.OWNER_TYPE?.value || 'FE').trim().toUpperCase();
    if (els.ownerFeWrap) els.ownerFeWrap.style.display = ownerType === 'FE' ? '' : 'none';
    if (els.ownerClientWrap) els.ownerClientWrap.style.display = ownerType === 'CLIENTE' ? '' : 'none';
    if (els.ownerFeLabel) els.ownerFeLabel.textContent = String(currentEntity.NOMEFISCAL || currentEntity.NOME || '').trim() || 'Entidade atual';
    if (ownerType === 'FE') {
      applyClient(null);
    } else if (!state.selectedClient && Number(els.fields.NO?.value || 0) > 0) {
      const no = Number(els.fields.NO.value || 0);
      fetchJson(`/api/faturacao/clientes/${encodeURIComponent(no)}`)
        .then((row) => applyClient(row))
        .catch(() => applyClient(null));
    } else if (!state.selectedClient) {
      if (els.clientSelected) els.clientSelected.textContent = 'Sem cliente selecionado';
    }
    updateButtons();
  }

  function fillForm(row) {
    const current = normalizeRow(row);
    state.current = current;
    if (els.fields.LOCALSTAMP) els.fields.LOCALSTAMP.value = current.LOCALSTAMP || '';
    if (els.fields.OWNER_TYPE) els.fields.OWNER_TYPE.value = current.OWNER_TYPE || 'FE';
    if (els.fields.DESIGNACAO) els.fields.DESIGNACAO.value = current.DESIGNACAO || '';
    if (els.fields.MORADA) els.fields.MORADA.value = current.MORADA || '';
    if (els.fields.MORADA2) els.fields.MORADA2.value = current.MORADA2 || '';
    if (els.fields.CP) els.fields.CP.value = current.CP || '';
    if (els.fields.LOCALIDADE) els.fields.LOCALIDADE.value = current.LOCALIDADE || '';
    if (els.fields.PAIS) els.fields.PAIS.value = current.PAIS || '';
    if (els.fields.ATIVO) els.fields.ATIVO.checked = Number(current.ATIVO || 0) === 1;
    if (els.editorTitle) els.editorTitle.textContent = current.DESIGNACAO || 'Novo local';
    if (current.OWNER_TYPE === 'CLIENTE' && Number(current.NO || 0) > 0) {
      applyClient({
        NO: current.NO,
        NOME: current.OWNER_LABEL || current.CLIENTE_NOME || '',
        LOCAL: '',
      });
    } else {
      applyClient(null);
    }
    updateOwnerUi();
  }

  function listItemHtml(row) {
    return `
      <div class="sz_panel sz_stack sz_locais_list_item ${state.selectedStamp === row.LOCALSTAMP ? 'sz_is_active' : ''}" data-localstamp="${esc(row.LOCALSTAMP)}">
        <div class="sz_locais_list_head">
          <div>
            <div class="sz_label">${esc(row.DESIGNACAO || '(Sem designação)')}</div>
            <div class="sz_text_muted">${esc(row.OWNER_LABEL || '')}</div>
          </div>
          <span class="sz_fts_badge ${Number(row.ATIVO || 0) === 1 ? 'sz_fts_badge_ok' : 'sz_fts_badge_warn'}">${Number(row.ATIVO || 0) === 1 ? 'Ativo' : 'Inativo'}</span>
        </div>
        <div class="sz_locais_meta">
          <span><strong>Tipo:</strong> ${esc(row.OWNER_TYPE === 'CLIENTE' ? 'Cliente' : 'Entidade')}</span>
          <span><strong>Localidade:</strong> ${esc(row.LOCALIDADE || '-')}</span>
          <span><strong>Morada:</strong> ${esc(row.MORADA || '-')}</span>
        </div>
      </div>
    `;
  }

  function renderList() {
    if (!els.list) return;
    if (!state.rows.length) {
      els.list.innerHTML = '<div class="sz_panel sz_locais_empty">Sem locais para os filtros aplicados.</div>';
      if (els.listSummary) els.listSummary.textContent = '0 locais';
      return;
    }
    els.list.innerHTML = state.rows.map(listItemHtml).join('');
    if (els.listSummary) els.listSummary.textContent = `${state.rows.length} local${state.rows.length === 1 ? '' : 'ais'}`;
    els.list.querySelectorAll('[data-localstamp]').forEach((node) => {
      node.addEventListener('click', () => openDetail(node.getAttribute('data-localstamp') || ''));
    });
  }

  function buildListQuery() {
    const qs = new URLSearchParams();
    const q = String(els.filters.search?.value || '').trim();
    const ownerType = String(els.filters.ownerType?.value || '').trim().toUpperCase();
    const ativo = String(els.filters.ativo?.value || '').trim();
    if (q) qs.set('q', q);
    if (ownerType) qs.set('owner_type', ownerType);
    if (ativo) qs.set('ativo', ativo);
    return qs.toString();
  }

  async function loadList() {
    if (!els.list) return;
    els.list.innerHTML = '<div class="sz_panel sz_locais_empty">A carregar...</div>';
    try {
      const data = await fetchJson(`/api/faturacao/locais-manage${buildListQuery() ? `?${buildListQuery()}` : ''}`);
      state.rows = Array.isArray(data.rows) ? data.rows : [];
      renderList();
      const target = state.selectedStamp && state.rows.some((row) => row.LOCALSTAMP === state.selectedStamp)
        ? state.selectedStamp
        : (state.rows[0]?.LOCALSTAMP || '');
      if (target) await openDetail(target, { silent: true });
      else fillForm(emptyRow());
    } catch (error) {
      state.rows = [];
      renderList();
      fillForm(emptyRow());
      showToast(error.message || 'Erro ao carregar locais.', 'danger');
    }
  }

  async function openDetail(localstamp, options = {}) {
    const normalized = String(localstamp || '').trim();
    if (!normalized) {
      state.selectedStamp = '';
      fillForm(emptyRow());
      renderList();
      return;
    }
    try {
      const data = await fetchJson(`/api/faturacao/locais-manage/${encodeURIComponent(normalized)}`);
      state.selectedStamp = normalized;
      fillForm(data.row || {});
      renderList();
    } catch (error) {
      if (!options.silent) showToast(error.message || 'Erro ao carregar o local.', 'danger');
    }
  }

  function collectForm() {
    const ownerType = String(els.fields.OWNER_TYPE?.value || 'FE').trim().toUpperCase();
    return {
      LOCALSTAMP: String(els.fields.LOCALSTAMP?.value || '').trim(),
      OWNER_TYPE: ownerType,
      NO: ownerType === 'CLIENTE' ? Number(els.fields.NO?.value || 0) : 0,
      DESIGNACAO: String(els.fields.DESIGNACAO?.value || '').trim(),
      MORADA: String(els.fields.MORADA?.value || '').trim(),
      MORADA2: String(els.fields.MORADA2?.value || '').trim(),
      CP: String(els.fields.CP?.value || '').trim(),
      LOCALIDADE: String(els.fields.LOCALIDADE?.value || '').trim(),
      PAIS: String(els.fields.PAIS?.value || '').trim(),
      ATIVO: els.fields.ATIVO?.checked ? 1 : 0,
    };
  }

  async function saveCurrent() {
    if (!canWriteCurrent()) return;
    try {
      const data = await fetchJson('/api/faturacao/locais-manage/save', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ row: collectForm() }),
      });
      state.selectedStamp = String(data.localstamp || '').trim();
      showToast('Local gravado.', 'success');
      await loadList();
    } catch (error) {
      showToast(error.message || 'Erro ao gravar o local.', 'danger');
    }
  }

  async function deleteCurrent() {
    const localstamp = String(els.fields.LOCALSTAMP?.value || '').trim();
    if (!localstamp || !permissions.delete) return;
    const designacao = String(els.fields.DESIGNACAO?.value || localstamp).trim();
    if (!window.confirm(`Eliminar o local "${designacao}"?`)) return;
    try {
      await fetchJson(`/api/faturacao/locais-manage/${encodeURIComponent(localstamp)}/delete`, { method: 'POST' });
      state.selectedStamp = '';
      showToast('Local eliminado.', 'success');
      await loadList();
    } catch (error) {
      showToast(error.message || 'Erro ao eliminar o local.', 'danger');
    }
  }

  function newLocal() {
    state.selectedStamp = '';
    fillForm(emptyRow());
    renderList();
    if (els.fields.DESIGNACAO) els.fields.DESIGNACAO.focus();
  }

  function cancelEdit() {
    if (state.selectedStamp) openDetail(state.selectedStamp, { silent: true });
    else fillForm(emptyRow());
  }

  async function searchClients() {
    const q = String(els.clientSearch?.value || '').trim();
    if (String(els.fields.OWNER_TYPE?.value || '').trim().toUpperCase() !== 'CLIENTE' || q.length < 1) {
      state.clientResults = [];
      renderClientResults();
      return;
    }
    try {
      const data = await fetch(`/api/faturacao/clientes?q=${encodeURIComponent(q)}`);
      const rows = await data.json().catch(() => []);
      state.clientResults = Array.isArray(rows) ? rows : [];
      renderClientResults();
    } catch (_) {
      state.clientResults = [];
      renderClientResults();
    }
  }

  function bindEvents() {
    els.btnNewTop?.addEventListener('click', newLocal);
    els.btnSaveBottom?.addEventListener('click', () => { saveCurrent().catch(() => {}); });
    els.btnCancel?.addEventListener('click', cancelEdit);
    els.btnDelete?.addEventListener('click', () => { deleteCurrent().catch(() => {}); });
    els.fields.OWNER_TYPE?.addEventListener('change', updateOwnerUi);
    els.filters.search?.addEventListener('input', () => {
      window.clearTimeout(state.searchTimer);
      state.searchTimer = window.setTimeout(() => { loadList().catch(() => {}); }, 250);
    });
    els.filters.ownerType?.addEventListener('change', () => { loadList().catch(() => {}); });
    els.filters.ativo?.addEventListener('change', () => { loadList().catch(() => {}); });
    els.clientSearch?.addEventListener('input', () => {
      window.clearTimeout(state.clientTimer);
      state.clientTimer = window.setTimeout(() => { searchClients().catch(() => {}); }, 250);
    });
    document.addEventListener('keydown', (event) => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 's') {
        event.preventDefault();
        saveCurrent().catch(() => {});
      }
    });
  }

  bindEvents();
  fillForm(emptyRow());
  loadList().catch(() => {});
})();
