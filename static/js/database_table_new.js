document.addEventListener('DOMContentLoaded', () => {
  const els = {
    status: document.getElementById('dbcreateStatus'),
    footerStatus: document.getElementById('dbcreateFooterStatus'),
    schema: document.getElementById('dbcreateSchema'),
    tableName: document.getElementById('dbcreateTableName'),
    ifNotExists: document.getElementById('dbcreateIfNotExists'),
    columnsMeta: document.getElementById('dbcreateColumnsMeta'),
    columnsList: document.getElementById('dbcreateColumnsList'),
    addColumnBtn: document.getElementById('dbcreateAddColumnBtn'),
    importTableBtn: document.getElementById('dbcreateImportTableBtn'),
    previewBtn: document.getElementById('dbcreatePreviewBtn'),
    createBtn: document.getElementById('dbcreateCreateBtn'),
    backBtn: document.getElementById('dbcreateBackBtn'),
    backManagerBtn: document.getElementById('dbcreateBackManagerBtn'),
    sqlPreview: document.getElementById('dbcreateSqlPreview'),
    importModal: document.getElementById('dbcreateImportModal'),
    importClose: document.getElementById('dbcreateImportClose'),
    importCloseTop: document.getElementById('dbcreateImportCloseTop'),
    importMeta: document.getElementById('dbcreateImportMeta'),
    importMode: document.getElementById('dbcreateImportMode'),
    importDatabaseField: document.getElementById('dbcreateImportDatabaseField'),
    importDatabase: document.getElementById('dbcreateImportDatabase'),
    importDatabaseOptions: document.getElementById('dbcreateImportDatabaseOptions'),
    importFeField: document.getElementById('dbcreateImportFeField'),
    importFe: document.getElementById('dbcreateImportFe'),
    importTable: document.getElementById('dbcreateImportTable'),
    importLoadBtn: document.getElementById('dbcreateImportLoadBtn'),
    importColumns: document.getElementById('dbcreateImportColumns'),
    importCount: document.getElementById('dbcreateImportCount'),
    importApplyBtn: document.getElementById('dbcreateImportApplyBtn'),
  };

  const typeOptions = [
    'varchar', 'nvarchar', 'char', 'nchar',
    'int', 'bigint', 'smallint', 'tinyint',
    'bit', 'decimal', 'numeric', 'money',
    'date', 'datetime', 'datetime2', 'time',
    'uniqueidentifier', 'float', 'real',
    'varbinary',
  ];

  const state = {
    columns: [],
    nextId: 1,
    busy: false,
    importSources: null,
    importPayload: null,
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
    [els.status, els.footerStatus].forEach((node) => {
      if (!node) return;
      node.textContent = message || '';
      node.style.color = isError ? 'var(--sz-color-danger)' : '';
    });
  }

  function newColumn(overrides = {}) {
    const id = state.nextId;
    state.nextId += 1;
    return {
      id,
      name: '',
      data_type: 'varchar',
      length: 100,
      precision: 18,
      scale: 2,
      nullable: true,
      primary_key: false,
      identity: false,
      unique: false,
      default: '',
      ...overrides,
    };
  }

  function typeNeedsLength(type) {
    return ['varchar', 'nvarchar', 'char', 'nchar', 'varbinary'].includes(String(type || '').toLowerCase());
  }

  function typeNeedsPrecision(type) {
    return ['decimal', 'numeric'].includes(String(type || '').toLowerCase());
  }

  function renderColumns() {
    if (els.columnsMeta) {
      els.columnsMeta.textContent = String(state.columns.length);
    }
    if (!els.columnsList) return;
    if (!state.columns.length) {
      els.columnsList.innerHTML = '<div class="dbm-empty">Adiciona pelo menos um campo.</div>';
      return;
    }

    els.columnsList.innerHTML = state.columns.map((column, index) => {
      const type = String(column.data_type || 'varchar').toLowerCase();
      return `
        <article class="dbcreate-column-row" data-column-id="${column.id}">
          <div class="dbcreate-column-head">
            <span class="dbm-badge">${index + 1}</span>
            <strong>${escapeHtml(column.name || 'Novo campo')}</strong>
            <button type="button" class="sz_button sz_button_ghost dbcreate-remove-column" title="Remover campo" aria-label="Remover campo">
              <i class="fa-solid fa-trash"></i>
            </button>
          </div>
          <div class="dbcreate-column-grid">
            <div class="sz_field">
              <label class="sz_label">Nome</label>
              <input class="sz_input dbcreate-col-name" type="text" value="${escapeHtml(column.name)}" placeholder="Ex: OPCSTAMP">
            </div>
            <div class="sz_field">
              <label class="sz_label">Tipo</label>
              <select class="sz_input dbcreate-col-type">
                ${typeOptions.map((option) => `<option value="${option}" ${option === type ? 'selected' : ''}>${option}</option>`).join('')}
              </select>
            </div>
            <div class="sz_field ${typeNeedsLength(type) ? '' : 'is-disabled'}">
              <label class="sz_label">Tamanho</label>
              <input class="sz_input dbcreate-col-length" type="number" min="1" max="8000" value="${escapeHtml(column.length || '')}" ${typeNeedsLength(type) ? '' : 'disabled'}>
            </div>
            <div class="sz_field ${typeNeedsPrecision(type) ? '' : 'is-disabled'}">
              <label class="sz_label">Precisão</label>
              <input class="sz_input dbcreate-col-precision" type="number" min="1" max="38" value="${escapeHtml(column.precision || '')}" ${typeNeedsPrecision(type) ? '' : 'disabled'}>
            </div>
            <div class="sz_field ${typeNeedsPrecision(type) ? '' : 'is-disabled'}">
              <label class="sz_label">Escala</label>
              <input class="sz_input dbcreate-col-scale" type="number" min="0" max="38" value="${escapeHtml(column.scale || '')}" ${typeNeedsPrecision(type) ? '' : 'disabled'}>
            </div>
            <div class="sz_field">
              <label class="sz_label">Default</label>
              <input class="sz_input dbcreate-col-default" type="text" value="${escapeHtml(column.default)}" placeholder="Ex: '' ou 0 ou GETDATE()">
            </div>
          </div>
          <div class="dbcreate-column-flags">
            <label class="dbmap-mini-check">
              <input class="dbcreate-col-nullable" type="checkbox" ${column.nullable ? 'checked' : ''}>
              <span>NULL</span>
            </label>
            <label class="dbmap-mini-check">
              <input class="dbcreate-col-pk" type="checkbox" ${column.primary_key ? 'checked' : ''}>
              <span>PK</span>
            </label>
            <label class="dbmap-mini-check">
              <input class="dbcreate-col-identity" type="checkbox" ${column.identity ? 'checked' : ''}>
              <span>Identity</span>
            </label>
            <label class="dbmap-mini-check">
              <input class="dbcreate-col-unique" type="checkbox" ${column.unique ? 'checked' : ''}>
              <span>Unique</span>
            </label>
          </div>
        </article>
      `;
    }).join('');
  }

  function syncFromDom() {
    if (!els.columnsList) return;
    state.columns = Array.from(els.columnsList.querySelectorAll('.dbcreate-column-row')).map((row) => ({
      id: Number(row.dataset.columnId || 0),
      name: String(row.querySelector('.dbcreate-col-name')?.value || '').trim().toUpperCase(),
      data_type: String(row.querySelector('.dbcreate-col-type')?.value || 'varchar').trim().toLowerCase(),
      length: Number(row.querySelector('.dbcreate-col-length')?.value || 0),
      precision: Number(row.querySelector('.dbcreate-col-precision')?.value || 0),
      scale: Number(row.querySelector('.dbcreate-col-scale')?.value || 0),
      nullable: !!row.querySelector('.dbcreate-col-nullable')?.checked,
      primary_key: !!row.querySelector('.dbcreate-col-pk')?.checked,
      identity: !!row.querySelector('.dbcreate-col-identity')?.checked,
      unique: !!row.querySelector('.dbcreate-col-unique')?.checked,
      default: String(row.querySelector('.dbcreate-col-default')?.value || '').trim(),
    }));
  }

  function buildPayload() {
    syncFromDom();
    return {
      schema: String(els.schema?.value || 'dbo').trim(),
      table_name: String(els.tableName?.value || '').trim(),
      if_not_exists: !!els.ifNotExists?.checked,
      columns: state.columns.map((column) => ({ ...column })),
    };
  }

  async function sendJson(url, body) {
    const response = await fetch(url, {
      method: 'POST',
      credentials: 'same-origin',
      headers: {
        Accept: 'application/json',
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body || {}),
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok || data.error) {
      throw new Error(data.error || `HTTP ${response.status}`);
    }
    return data;
  }

  async function fetchJson(url) {
    const response = await fetch(url, {
      headers: { Accept: 'application/json' },
      credentials: 'same-origin',
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok || data.error) {
      throw new Error(data.error || `HTTP ${response.status}`);
    }
    return data;
  }

  function updateImportModeVisibility() {
    const mode = String(els.importMode?.value || 'FIXED').trim().toUpperCase();
    if (els.importDatabaseField) els.importDatabaseField.style.display = mode === 'FE' ? 'none' : '';
    if (els.importFeField) els.importFeField.style.display = mode === 'FE' ? '' : 'none';
  }

  function renderImportSources(payload) {
    state.importSources = payload || {};
    const items = Array.isArray(payload?.fe_databases) ? payload.fe_databases : [];
    if (els.importFe) {
      els.importFe.innerHTML = items.map((item) => `
        <option value="${escapeHtml(item.feid || '')}">
          ${escapeHtml(item.fe_name || `FE ${item.feid || ''}`)} - ${escapeHtml(item.target_database || '')}
        </option>
      `).join('') || '<option value="">Sem FE disponíveis</option>';
    }
    if (els.importDatabaseOptions) {
      const databases = Array.isArray(payload?.databases) ? payload.databases : [];
      els.importDatabaseOptions.innerHTML = databases.map((name) => `<option value="${escapeHtml(name)}"></option>`).join('');
    }
    if (els.importMeta) {
      els.importMeta.textContent = payload?.warning || `${items.length} FE disponíveis.`;
    }
  }

  async function loadImportSources() {
    if (state.importSources) return state.importSources;
    const payload = await fetchJson('/api/database_manager/create_table/import_sources');
    renderImportSources(payload);
    return payload;
  }

  function importedColumnTypeLabel(column) {
    const type = String(column.data_type || '').toLowerCase();
    if (typeNeedsLength(type)) return `${type}(${column.length || 0})`;
    if (typeNeedsPrecision(type)) return `${type}(${column.precision || 18},${column.scale || 0})`;
    return type || 'n/a';
  }

  function renderImportedColumns(payload) {
    state.importPayload = payload || null;
    const columns = Array.isArray(payload?.columns) ? payload.columns : [];
    if (els.importCount) els.importCount.textContent = String(columns.length);
    if (els.importApplyBtn) els.importApplyBtn.disabled = !columns.length;
    if (!els.importColumns) return;
    if (!columns.length) {
      els.importColumns.innerHTML = '<div class="dbm-empty">Sem campos encontrados.</div>';
      return;
    }
    els.importColumns.innerHTML = columns.map((column, index) => `
      <label class="dbcreate-import-column-row">
        <input class="dbcreate-import-column-check" type="checkbox" value="${index}" checked>
        <span class="dbcreate-import-column-main">
          <strong>${escapeHtml(column.name)}</strong>
          <small>${escapeHtml(importedColumnTypeLabel(column))} | ${column.nullable ? 'NULL' : 'NOT NULL'}${column.primary_key ? ' | PK' : ''}${column.identity ? ' | IDENTITY' : ''}</small>
        </span>
      </label>
    `).join('');
  }

  async function openImportModal() {
    if (!els.importModal) return;
    updateImportModeVisibility();
    document.body.classList.add('modal-dbcreate-import-open');
    els.importModal.classList.add('sz_is_open');
    els.importModal.setAttribute('aria-hidden', 'false');
    try {
      await loadImportSources();
    } catch (error) {
      if (els.importMeta) els.importMeta.textContent = error.message || 'Erro ao carregar FE.';
    }
  }

  function closeImportModal() {
    if (!els.importModal) return;
    els.importModal.classList.remove('sz_is_open');
    els.importModal.setAttribute('aria-hidden', 'true');
    document.body.classList.remove('modal-dbcreate-import-open');
  }

  async function loadSourceColumns() {
    if (els.importLoadBtn) els.importLoadBtn.disabled = true;
    if (els.importApplyBtn) els.importApplyBtn.disabled = true;
    if (els.importColumns) els.importColumns.innerHTML = '<div class="dbm-empty">A ler campos...</div>';
    try {
      const payload = await sendJson('/api/database_manager/create_table/source_columns', {
        source_mode: String(els.importMode?.value || 'FIXED').trim().toUpperCase(),
        database: String(els.importDatabase?.value || '').trim(),
        feid: Number(els.importFe?.value || 0),
        table_name: String(els.importTable?.value || '').trim(),
      });
      renderImportedColumns(payload);
      if (els.importMeta) {
        els.importMeta.textContent = `${payload.database || ''}.${payload.schema || 'dbo'}.${payload.table_name || ''}`;
      }
    } catch (error) {
      state.importPayload = null;
      if (els.importColumns) els.importColumns.innerHTML = `<div class="dbm-empty">${escapeHtml(error.message || 'Erro ao ler campos.')}</div>`;
    } finally {
      if (els.importLoadBtn) els.importLoadBtn.disabled = false;
    }
  }

  function applyImportedColumns() {
    const columns = Array.isArray(state.importPayload?.columns) ? state.importPayload.columns : [];
    if (!columns.length || !els.importColumns) return;
    const selectedIndexes = Array.from(els.importColumns.querySelectorAll('.dbcreate-import-column-check:checked'))
      .map((input) => Number(input.value))
      .filter((idx) => Number.isInteger(idx) && idx >= 0);
    const selected = selectedIndexes.map((idx) => columns[idx]).filter(Boolean);
    if (!selected.length) {
      setStatus('Seleciona pelo menos um campo para importar.', true);
      return;
    }

    state.columns = selected.map((column) => newColumn({
      name: String(column.name || '').toUpperCase(),
      data_type: String(column.data_type || 'varchar').toLowerCase(),
      length: Number(column.length || 0),
      precision: Number(column.precision || 18),
      scale: Number(column.scale || 0),
      nullable: !!column.nullable && !column.primary_key,
      primary_key: !!column.primary_key,
      identity: !!column.identity,
      unique: !!column.unique,
      default: String(column.default || ''),
    }));
    if (els.tableName && !String(els.tableName.value || '').trim()) {
      els.tableName.value = state.importPayload?.table_name || '';
    }
    renderColumns();
    closeImportModal();
    setStatus(`${selected.length} campos importados para o formulário.`);
  }

  async function previewSql() {
    if (state.busy) return null;
    state.busy = true;
    if (els.previewBtn) els.previewBtn.disabled = true;
    setStatus('A validar definição...');
    try {
      const payload = await sendJson('/api/database_manager/create_table/preview', buildPayload());
      if (els.sqlPreview) els.sqlPreview.textContent = payload.sql || '';
      setStatus('Definição válida.');
      return payload;
    } catch (error) {
      if (els.sqlPreview) els.sqlPreview.textContent = error.message || 'Erro na validação.';
      setStatus(error.message || 'Erro na validação.', true);
      return null;
    } finally {
      state.busy = false;
      if (els.previewBtn) els.previewBtn.disabled = false;
    }
  }

  async function createTable() {
    if (state.busy) return;
    state.busy = true;
    if (els.createBtn) els.createBtn.disabled = true;
    setStatus('A criar tabela...');
    try {
      const payload = await sendJson('/api/database_manager/create_table', buildPayload());
      if (els.sqlPreview) els.sqlPreview.textContent = payload.sql || '';
      if (payload.already_exists) {
        setStatus(`A tabela ${payload.table_key || ''} já existe. Nada foi criado.`, true);
        return;
      }
      setStatus(`Tabela ${payload.table_key || ''} criada.`);
      if (payload.table_key) {
        window.setTimeout(() => {
          const target = new URL('/database_manager', window.location.origin);
          target.searchParams.set('table', payload.table_key);
          window.location.href = target.toString();
        }, 650);
      }
    } catch (error) {
      setStatus(error.message || 'Erro ao criar tabela.', true);
    } finally {
      state.busy = false;
      if (els.createBtn) els.createBtn.disabled = false;
    }
  }

  function addColumn(overrides) {
    syncFromDom();
    state.columns.push(newColumn(overrides));
    renderColumns();
  }

  els.addColumnBtn?.addEventListener('click', () => addColumn());
  els.importTableBtn?.addEventListener('click', openImportModal);
  els.importClose?.addEventListener('click', closeImportModal);
  els.importCloseTop?.addEventListener('click', closeImportModal);
  els.importModal?.addEventListener('click', (event) => {
    if (event.target === els.importModal) closeImportModal();
  });
  els.importMode?.addEventListener('change', updateImportModeVisibility);
  els.importLoadBtn?.addEventListener('click', loadSourceColumns);
  els.importApplyBtn?.addEventListener('click', applyImportedColumns);
  els.previewBtn?.addEventListener('click', previewSql);
  els.createBtn?.addEventListener('click', createTable);
  els.backBtn?.addEventListener('click', () => window.history.back());
  els.backManagerBtn?.addEventListener('click', () => {
    window.location.href = new URL('/database_manager', window.location.origin).toString();
  });
  els.columnsList?.addEventListener('input', (event) => {
    if (event.target.closest('.dbcreate-col-name')) {
      const input = event.target.closest('.dbcreate-col-name');
      const start = input.selectionStart;
      const end = input.selectionEnd;
      input.value = String(input.value || '').toUpperCase();
      if (start != null && end != null) input.setSelectionRange(start, end);
    }
    if (event.target.closest('.dbcreate-col-type')) {
      syncFromDom();
      renderColumns();
    }
  });
  els.columnsList?.addEventListener('change', syncFromDom);
  els.columnsList?.addEventListener('click', (event) => {
    const remove = event.target.closest('.dbcreate-remove-column');
    if (!remove) return;
    const row = remove.closest('.dbcreate-column-row');
    const id = Number(row?.dataset.columnId || 0);
    syncFromDom();
    state.columns = state.columns.filter((column) => column.id !== id);
    renderColumns();
  });

  state.columns = [
    newColumn({ name: '', data_type: 'varchar', length: 25, nullable: false, primary_key: true }),
    newColumn({ name: '', data_type: 'varchar', length: 100, nullable: false }),
  ];
  renderColumns();
});
