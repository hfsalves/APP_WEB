(function () {
  const state = {
    rows: [],
    current: null,
    selectedModstamp: String(window.MODULOS_INITIAL_MODSTAMP || '').trim(),
    searchTimer: null,
    objectSearchTimer: null,
    objectRows: [],
    objectSearch: '',
  };

  const permissions = {
    create: !!window.MOD_CAN_CREATE,
    edit: !!window.MOD_CAN_EDIT,
    delete: !!window.MOD_CAN_DELETE,
  };

  const els = {
    list: document.getElementById('modList'),
    listSummary: document.getElementById('modListSummary'),
    editorTitle: document.getElementById('modEditorTitle'),
    totalFe: document.getElementById('modTotalFe'),
    totalFeAtivas: document.getElementById('modTotalFeAtivas'),
    totalObjetos: document.getElementById('modTotalObjetos'),
    estado: document.getElementById('modEstado'),
    estadoBadge: document.getElementById('modEstadoBadge'),
    search: document.getElementById('modSearch'),
    activeFilter: document.getElementById('modActiveFilter'),
    btnNew: document.getElementById('modBtnNew'),
    btnSave: document.getElementById('modBtnSave'),
    btnCancel: document.getElementById('modBtnCancel'),
    btnDelete: document.getElementById('modBtnDelete'),
    btnObjects: document.getElementById('modBtnObjects'),
    objectsModalEl: document.getElementById('modObjectsModal'),
    objectsModalSubtitle: document.getElementById('modObjectsModalSubtitle'),
    objectsTableBody: document.getElementById('modObjectsTableBody'),
    objectsSearch: document.getElementById('modObjectsSearch'),
    objectsAddManual: document.getElementById('modObjectsAddManual'),
    objectsSave: document.getElementById('modObjectsSave'),
    fields: {
      MODSTAMP: document.getElementById('modMODSTAMP'),
      CODIGO: document.getElementById('modCODIGO'),
      NOME: document.getElementById('modNOME'),
      DESCR: document.getElementById('modDESCR'),
      ORDEM: document.getElementById('modORDEM'),
      ATIVO: document.getElementById('modATIVO'),
      DTCRI: document.getElementById('modDTCRI'),
      DTALT: document.getElementById('modDTALT'),
      USERCRIACAO: document.getElementById('modUSERCRIACAO'),
      USERALTERACAO: document.getElementById('modUSERALTERACAO'),
    },
  };

  const editableKeys = ['CODIGO', 'NOME', 'DESCR', 'ORDEM', 'ATIVO'];
  const objectsModal = els.objectsModalEl ? bootstrap.Modal.getOrCreateInstance(els.objectsModalEl) : null;

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
      MODSTAMP: '',
      CODIGO: '',
      NOME: '',
      DESCR: '',
      ORDEM: 0,
      ATIVO: 1,
      DTCRI: '',
      DTALT: '',
      USERCRIACAO: '',
      USERALTERACAO: '',
      TOTAL_FE: 0,
      TOTAL_FE_ATIVAS: 0,
      TOTAL_OBJETOS: 0,
    };
  }

  function normalizeRow(row) {
    return { ...emptyRow(), ...(row || {}) };
  }

  function isExisting() {
    return !!String(els.fields.MODSTAMP?.value || '').trim();
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

  function updateButtons() {
    const existing = isExisting();
    const canWrite = canWriteCurrent();

    setEditable(canWrite);
    if (els.btnNew) els.btnNew.disabled = !permissions.create;
    if (els.btnSave) els.btnSave.disabled = !canWrite;
    if (els.btnDelete) els.btnDelete.disabled = !existing || !permissions.delete;
    if (els.btnObjects) els.btnObjects.disabled = !existing;
  }

  function updateSummary(row) {
    const current = normalizeRow(row);
    if (els.editorTitle) {
      els.editorTitle.textContent = current.NOME || current.CODIGO || 'Novo módulo';
    }
    if (els.totalFe) els.totalFe.textContent = String(current.TOTAL_FE || 0);
    if (els.totalFeAtivas) els.totalFeAtivas.textContent = String(current.TOTAL_FE_ATIVAS || 0);
    if (els.totalObjetos) els.totalObjetos.textContent = String(current.TOTAL_OBJETOS || 0);
    if (els.estado) els.estado.textContent = current.ATIVO ? 'Ativo' : 'Inativo';
    if (els.estadoBadge) {
      els.estadoBadge.textContent = current.ATIVO ? 'Ativo' : 'Inativo';
      els.estadoBadge.className = `sz_badge ${current.ATIVO ? 'sz_badge_success' : 'sz_badge_warning'}`;
    }
  }

  function updateObjectCounters(count) {
    const total = Number(count || 0);
    if (state.current) {
      state.current.TOTAL_OBJETOS = total;
      updateSummary(state.current);
    }
    if (state.selectedModstamp) {
      const row = state.rows.find((item) => String(item.MODSTAMP || '').trim() === state.selectedModstamp);
      if (row) row.TOTAL_OBJETOS = total;
      renderList();
    }
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
      MODSTAMP: String(els.fields.MODSTAMP?.value || '').trim(),
      CODIGO: String(els.fields.CODIGO?.value || '').trim().toUpperCase(),
      NOME: String(els.fields.NOME?.value || '').trim(),
      DESCR: String(els.fields.DESCR?.value || '').trim(),
      ORDEM: Number(els.fields.ORDEM?.value || 0),
      ATIVO: els.fields.ATIVO?.checked ? 1 : 0,
    };
  }

  function listItemHtml(row) {
    const active = !!row.ATIVO;
    return `
      <div class="sz_panel sz_stack sz_modulos_list_item ${state.selectedModstamp === row.MODSTAMP ? 'sz_is_active' : ''}" data-modstamp="${esc(row.MODSTAMP)}">
        <div class="sz_modulos_list_head">
          <div class="sz_stack sz_modulos_list_title_block">
            <div class="sz_label">${esc(row.NOME || '(Sem nome)')}</div>
            <div class="sz_text_muted">${esc(row.CODIGO || '')}</div>
          </div>
          <span class="sz_badge ${active ? 'sz_badge_success' : 'sz_badge_warning'}">${active ? 'Ativo' : 'Inativo'}</span>
        </div>
        <div class="sz_text_muted">${esc(row.DESCR || 'Sem descrição')}</div>
        <div class="sz_modulos_list_meta">
          <span class="sz_badge sz_badge_info">Ordem ${esc(row.ORDEM || 0)}</span>
          <span class="sz_badge sz_badge_info">Objetos ${esc(row.TOTAL_OBJETOS || 0)}</span>
          <span class="sz_badge sz_badge_info">Entidades ${esc(row.TOTAL_FE || 0)}</span>
          <span class="sz_badge sz_badge_success">FE ativas ${esc(row.TOTAL_FE_ATIVAS || 0)}</span>
        </div>
        <div class="sz_modulos_list_actions">
          <button type="button" class="sz_button sz_button_ghost" data-action="objects" data-modstamp="${esc(row.MODSTAMP)}">
            <i class="fa-solid fa-table-cells-large"></i>
            <span>Objetos</span>
          </button>
        </div>
      </div>
    `;
  }

  function renderList() {
    if (!els.list) return;
    if (!state.rows.length) {
      els.list.innerHTML = '<div class="sz_panel sz_modulos_empty">Sem módulos para os filtros aplicados.</div>';
      if (els.listSummary) els.listSummary.textContent = '0 módulos';
      return;
    }
    els.list.innerHTML = state.rows.map(listItemHtml).join('');
    if (els.listSummary) {
      els.listSummary.textContent = `${state.rows.length} módulo${state.rows.length === 1 ? '' : 's'}`;
    }
    els.list.querySelectorAll('[data-modstamp]').forEach((node) => {
      node.addEventListener('click', (event) => {
        if (event.target.closest('[data-action="objects"]')) return;
        openDetail(node.getAttribute('data-modstamp') || '');
      });
    });
    els.list.querySelectorAll('[data-action="objects"]').forEach((node) => {
      node.addEventListener('click', (event) => {
        event.preventDefault();
        event.stopPropagation();
        openObjectsModal(node.getAttribute('data-modstamp') || '');
      });
    });
  }

  async function loadList() {
    if (!els.list) return;

    const qs = new URLSearchParams();
    const q = String(els.search?.value || '').trim();
    const active = String(els.activeFilter?.value || '').trim();
    if (q) qs.set('q', q);
    if (active) qs.set('active', active);

    els.list.innerHTML = '<div class="sz_panel sz_modulos_empty">A carregar...</div>';

    try {
      const res = await fetch(`/api/modulos?${qs.toString()}`);
      const data = await res.json().catch(() => ({}));
      if (!res.ok || data.error) throw new Error(data.error || 'Erro ao carregar módulos.');
      state.rows = Array.isArray(data.rows) ? data.rows : [];
      renderList();

      const targetModstamp = state.selectedModstamp || (state.rows[0]?.MODSTAMP || '');
      if (targetModstamp) {
        await openDetail(targetModstamp, { silent: true });
      } else {
        fillForm(emptyRow());
      }
    } catch (error) {
      state.rows = [];
      els.list.innerHTML = `<div class="sz_panel sz_modulos_empty">${esc(error.message || 'Erro ao carregar módulos.')}</div>`;
      if (els.listSummary) els.listSummary.textContent = '0 módulos';
      fillForm(emptyRow());
    }
  }

  async function openDetail(modstamp, options = {}) {
    const normalized = String(modstamp || '').trim();
    if (!normalized) {
      state.selectedModstamp = '';
      fillForm(emptyRow());
      renderList();
      return;
    }

    try {
      const res = await fetch(`/api/modulos/${encodeURIComponent(normalized)}`);
      const data = await res.json().catch(() => ({}));
      if (!res.ok || data.error) throw new Error(data.error || 'Erro ao carregar módulo.');
      state.selectedModstamp = normalized;
      fillForm(data.row || {});
      renderList();
    } catch (error) {
      if (!options.silent) showToast(error.message || 'Erro ao carregar módulo.', 'danger');
    }
  }

  function newModulo() {
    state.selectedModstamp = '';
    fillForm(emptyRow());
    renderList();
    if (els.fields.CODIGO) els.fields.CODIGO.focus();
  }

  async function saveModulo() {
    if (!canWriteCurrent()) return;
    const row = collectForm();
    try {
      const res = await fetch('/api/modulos/save', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ row }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok || data.error) throw new Error(data.error || 'Erro ao gravar módulo.');
      state.selectedModstamp = String(data.modstamp || row.MODSTAMP || '').trim();
      showToast('Módulo gravado.', 'success');
      await loadList();
    } catch (error) {
      showToast(error.message || 'Erro ao gravar módulo.', 'danger');
    }
  }

  async function deleteModulo() {
    const modstamp = String(els.fields.MODSTAMP?.value || '').trim();
    if (!modstamp || !permissions.delete) return;
    const nome = String(els.fields.NOME?.value || els.fields.CODIGO?.value || modstamp).trim();
    if (!window.confirm(`Eliminar o módulo "${nome}"?`)) return;

    try {
      const res = await fetch(`/api/modulos/${encodeURIComponent(modstamp)}/delete`, {
        method: 'POST',
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok || data.error) throw new Error(data.error || 'Erro ao eliminar módulo.');
      showToast('Módulo eliminado.', 'success');
      state.selectedModstamp = '';
      await loadList();
    } catch (error) {
      showToast(error.message || 'Erro ao eliminar módulo.', 'danger');
    }
  }

  function cancelEdit() {
    if (state.selectedModstamp) {
      openDetail(state.selectedModstamp, { silent: true });
      return;
    }
    newModulo();
  }

  function objectRowKey(row, index) {
    if (row.OBJKEY) return row.OBJKEY;
    return `MANUAL:${index}`;
  }

  function filteredObjectRows() {
    const q = state.objectSearch.trim().toLowerCase();
    if (!q) return state.objectRows;
    return state.objectRows.filter((row) => (
      String(row.OBJNOME || '').toLowerCase().includes(q)
      || String(row.OBJROTA || '').toLowerCase().includes(q)
      || String(row.ORIGEM || '').toLowerCase().includes(q)
      || String(row.TIPO || '').toLowerCase().includes(q)
    ));
  }

  function renderObjectsTable() {
    if (!els.objectsTableBody) return;
    const rows = filteredObjectRows();
    const activeCount = state.objectRows.filter((row) => Number(row.ATIVO || 0) === 1).length;
    updateObjectCounters(activeCount);
    if (!rows.length) {
      els.objectsTableBody.innerHTML = `
        <tr class="sz_table_row">
          <td colspan="5" class="sz_table_cell sz_text_muted">Sem objetos para mostrar.</td>
        </tr>
      `;
      return;
    }

    els.objectsTableBody.innerHTML = rows.map((row) => {
      const idx = state.objectRows.indexOf(row);
      const isManual = row.TIPO === 'MANUAL';
      return `
        <tr class="sz_table_row">
          <td class="sz_table_cell">${esc(row.TIPO || '')}</td>
          <td class="sz_table_cell">
            ${isManual
              ? `<input class="sz_input sz_modulos_manual_input" data-field="OBJNOME" data-index="${idx}" value="${esc(row.OBJNOME || '')}" placeholder="Nome do ecrã">`
              : esc(row.OBJNOME || '')}
          </td>
          <td class="sz_table_cell">
            ${isManual
              ? `<input class="sz_input sz_modulos_manual_input" data-field="OBJROTA" data-index="${idx}" value="${esc(row.OBJROTA || '')}" placeholder="/rota/do/ecra">`
              : esc(row.OBJROTA || '')}
          </td>
          <td class="sz_table_cell">${esc(row.ORIGEM || '')}</td>
          <td class="sz_table_cell sz_text_right">
            <label class="sz_checkbox">
              <input type="checkbox" data-object-toggle="${idx}" ${Number(row.ATIVO || 0) === 1 ? 'checked' : ''}>
              <span></span>
            </label>
          </td>
        </tr>
      `;
    }).join('');

    els.objectsTableBody.querySelectorAll('[data-object-toggle]').forEach((node) => {
      node.addEventListener('change', () => {
        const idx = Number(node.getAttribute('data-object-toggle'));
        if (Number.isNaN(idx) || !state.objectRows[idx]) return;
        state.objectRows[idx].ATIVO = node.checked ? 1 : 0;
        updateObjectCounters(state.objectRows.filter((row) => Number(row.ATIVO || 0) === 1).length);
      });
    });

    els.objectsTableBody.querySelectorAll('[data-field]').forEach((node) => {
      node.addEventListener('input', () => {
        const idx = Number(node.getAttribute('data-index'));
        const field = String(node.getAttribute('data-field') || '').trim();
        if (Number.isNaN(idx) || !state.objectRows[idx] || !field) return;
        state.objectRows[idx][field] = node.value;
      });
    });
  }

  function mergeObjectRows(existingRows, candidates) {
    const existingMap = new Map();
    (Array.isArray(existingRows) ? existingRows : []).forEach((row) => {
      existingMap.set(String(row.OBJKEY || '').trim(), { ...row });
    });

    const merged = (Array.isArray(candidates) ? candidates : []).map((candidate) => {
      const key = String(candidate.OBJKEY || '').trim();
      const existing = existingMap.get(key);
      if (existing) existingMap.delete(key);
      return {
        TIPO: candidate.TIPO || 'SCREEN',
        OBJKEY: key,
        OBJNOME: existing?.OBJNOME || candidate.OBJNOME || '',
        OBJROTA: existing?.OBJROTA || candidate.OBJROTA || '',
        MENUSTAMP: existing?.MENUSTAMP || candidate.MENUSTAMP || '',
        ORDEM: Number(existing?.ORDEM ?? candidate.ORDEM ?? 0),
        ATIVO: Number(existing?.ATIVO ?? 0),
        ORIGEM: candidate.ORIGEM || '',
      };
    });

    existingMap.forEach((row) => {
      merged.push({
        TIPO: row.TIPO || 'MANUAL',
        OBJKEY: row.OBJKEY || '',
        OBJNOME: row.OBJNOME || '',
        OBJROTA: row.OBJROTA || '',
        MENUSTAMP: row.MENUSTAMP || '',
        ORDEM: Number(row.ORDEM || 0),
        ATIVO: Number(row.ATIVO || 0),
        ORIGEM: row.TIPO === 'MANUAL' ? 'MANUAL' : 'ASSOCIADO',
      });
    });

    merged.sort((a, b) => {
      const activeDiff = Number(b.ATIVO || 0) - Number(a.ATIVO || 0);
      if (activeDiff) return activeDiff;
      const ordemDiff = Number(a.ORDEM || 0) - Number(b.ORDEM || 0);
      if (ordemDiff) return ordemDiff;
      return String(a.OBJNOME || '').localeCompare(String(b.OBJNOME || ''), 'pt');
    });

    return merged;
  }

  async function openObjectsModal(modstamp) {
    const normalized = String(modstamp || state.selectedModstamp || '').trim();
    if (!normalized) {
      showToast('Grave o módulo antes de gerir objetos.', 'warning');
      return;
    }

    try {
      const res = await fetch(`/api/modulos/${encodeURIComponent(normalized)}/objetos`);
      const data = await res.json().catch(() => ({}));
      if (!res.ok || data.error) throw new Error(data.error || 'Erro ao carregar objetos do módulo.');
      state.objectRows = mergeObjectRows(data.rows, data.candidates);
      state.objectSearch = '';
      if (els.objectsSearch) els.objectsSearch.value = '';
      if (els.objectsModalSubtitle) {
        const nome = String(els.fields.NOME?.value || els.fields.CODIGO?.value || normalized).trim();
        els.objectsModalSubtitle.textContent = `Menus e ecrãs associados ao módulo ${nome}.`;
      }
      renderObjectsTable();
      objectsModal?.show();
    } catch (error) {
      showToast(error.message || 'Erro ao carregar objetos do módulo.', 'danger');
    }
  }

  function addManualObjectRow() {
    state.objectRows.unshift({
      TIPO: 'MANUAL',
      OBJKEY: '',
      OBJNOME: '',
      OBJROTA: '',
      MENUSTAMP: '',
      ORDEM: (state.objectRows.length + 1) * 10,
      ATIVO: 1,
      ORIGEM: 'MANUAL',
    });
    renderObjectsTable();
  }

  async function saveObjectsModal() {
    const modstamp = String(state.selectedModstamp || '').trim();
    if (!modstamp) return;

    const rows = state.objectRows
      .filter((row) => Number(row.ATIVO || 0) === 1 || row.TIPO === 'MANUAL')
      .filter((row) => String(row.OBJNOME || '').trim() || String(row.OBJROTA || '').trim())
      .map((row, index) => ({
        TIPO: String(row.TIPO || 'MANUAL').trim(),
        OBJKEY: String(row.OBJKEY || '').trim(),
        OBJNOME: String(row.OBJNOME || '').trim(),
        OBJROTA: String(row.OBJROTA || '').trim(),
        MENUSTAMP: String(row.MENUSTAMP || '').trim(),
        ORDEM: Number(row.ORDEM || ((index + 1) * 10)),
        ATIVO: Number(row.ATIVO || 0),
      }));

    try {
      const res = await fetch(`/api/modulos/${encodeURIComponent(modstamp)}/objetos/save`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ rows }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok || data.error) throw new Error(data.error || 'Erro ao gravar objetos do módulo.');
      updateObjectCounters(rows.filter((row) => Number(row.ATIVO || 0) === 1).length);
      showToast('Objetos do módulo gravados.', 'success');
      objectsModal?.hide();
    } catch (error) {
      showToast(error.message || 'Erro ao gravar objetos do módulo.', 'danger');
    }
  }

  function bindEvents() {
    els.btnNew?.addEventListener('click', newModulo);
    els.btnSave?.addEventListener('click', saveModulo);
    els.btnCancel?.addEventListener('click', cancelEdit);
    els.btnDelete?.addEventListener('click', deleteModulo);
    els.btnObjects?.addEventListener('click', () => openObjectsModal());

    els.search?.addEventListener('input', () => {
      window.clearTimeout(state.searchTimer);
      state.searchTimer = window.setTimeout(loadList, 250);
    });
    els.activeFilter?.addEventListener('change', loadList);

    els.objectsSearch?.addEventListener('input', () => {
      window.clearTimeout(state.objectSearchTimer);
      state.objectSearchTimer = window.setTimeout(() => {
        state.objectSearch = String(els.objectsSearch?.value || '').trim();
        renderObjectsTable();
      }, 180);
    });
    els.objectsAddManual?.addEventListener('click', addManualObjectRow);
    els.objectsSave?.addEventListener('click', saveObjectsModal);

    document.addEventListener('keydown', (event) => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 's') {
        if (els.objectsModalEl?.classList.contains('show')) {
          event.preventDefault();
          saveObjectsModal();
          return;
        }
        event.preventDefault();
        saveModulo();
      }
    });
  }

  bindEvents();
  fillForm(emptyRow());
  updateButtons();
  loadList();
})();
