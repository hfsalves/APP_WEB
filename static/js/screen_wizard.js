document.addEventListener('DOMContentLoaded', () => {
  const cfg = window.SCREEN_WIZARD_CONFIG || {};
  const tableSelect = document.getElementById('swzTable');
  const screenTypeSelect = document.getElementById('swzScreenType');
  const titleInput = document.getElementById('swzTitle');
  const iconInput = document.getElementById('swzIcon');
  const orderInput = document.getElementById('swzOrder');
  const orderByInput = document.getElementById('swzOrderBy');
  const adminInput = document.getElementById('swzAdmin');
  const novoInput = document.getElementById('swzNovo');
  const modulesHost = document.getElementById('swzModules');
  const aclBody = document.getElementById('swzAclBody');
  const availableBody = document.getElementById('swzAvailableBody');
  const layoutBody = document.getElementById('swzLayoutBody');
  const menuUrlPreview = document.getElementById('swzMenuUrlPreview');
  const formUrlPreview = document.getElementById('swzFormUrlPreview');
  const statusEl = document.getElementById('swzStatus');
  const saveBtn = document.getElementById('swzSaveBtn');
  const clearBtn = document.getElementById('swzClearBtn');
  const separatorBtn = document.getElementById('swzSeparatorBtn');
  const orderPickerBtn = document.getElementById('swzOrderPickerBtn');
  const orderModalEl = document.getElementById('swzOrderModal');
  const orderBody = document.getElementById('swzOrderBody');
  const orderSearch = document.getElementById('swzOrderSearch');
  const orderLastBtn = document.getElementById('swzOrderLastBtn');

  const state = {
    tables: [],
    modules: [],
    menuPositions: { items: [], before_first: 0, after_last: 10 },
    aclUsers: [],
    columns: [],
    layout: [],
    selectedTableMeta: null,
    loadingColumns: false,
    saving: false,
  };

  const FIELD_TYPE_OPTIONS = [
    { value: 'TEXT', label: 'Texto' },
    { value: 'INT', label: 'Inteiro' },
    { value: 'DECIMAL', label: 'Decimal' },
    { value: 'DATE', label: 'Data' },
    { value: 'HOUR', label: 'Hora' },
    { value: 'BIT', label: 'Bit' },
    { value: 'MEMO', label: 'Memo' },
    { value: 'COLOR', label: 'Cor' },
  ];

  function escapeHtml(value) {
    return String(value ?? '')
      .replaceAll('&', '&amp;')
      .replaceAll('<', '&lt;')
      .replaceAll('>', '&gt;')
      .replaceAll('"', '&quot;')
      .replaceAll("'", '&#39;');
  }

  function setStatus(message, tone = 'muted') {
    if (!statusEl) return;
    statusEl.textContent = message || '';
    statusEl.className = `swz-status ${tone ? `is-${tone}` : ''}`.trim();
  }

  async function fetchJson(url, options = {}) {
    const response = await fetch(url, options);
    const rawText = await response.text();
    let payload = {};
    if (rawText) {
      try {
        payload = JSON.parse(rawText);
      } catch (_) {
        payload = { error: rawText };
      }
    }
    if (!response.ok) {
      throw new Error(payload.error || `HTTP ${response.status}`);
    }
    return payload;
  }

  function prettifyTableName(value) {
    return String(value || '')
      .trim()
      .replace(/_/g, ' ')
      .toLowerCase()
      .replace(/\b\w/g, ch => ch.toUpperCase());
  }

  function screenMenuUrl(tableName, screenType) {
    const table = String(tableName || '').trim().toUpperCase();
    if (!table) return '--';
    if (screenType === 'dynamic_form') return `/generic/form/${table}/`;
    return `/generic/view/${table}/`;
  }

  function screenFormUrl(tableName) {
    const table = String(tableName || '').trim().toUpperCase();
    if (!table) return '--';
    return `/generic/form/${table}`;
  }

  function currentFieldNames() {
    const names = new Set();
    state.layout.forEach(item => {
      if (item.kind === 'field') names.add(item.name);
    });
    return names;
  }

  function currentRowNumberUntil(index) {
    let row = 1;
    for (let pointer = 0; pointer < index; pointer += 1) {
      if (state.layout[pointer]?.kind === 'separator') row += 1;
    }
    return row;
  }

  function selectedTableName() {
    return String(tableSelect?.value || '').trim().toUpperCase();
  }

  function updatePreview() {
    const tableName = selectedTableName();
    const screenType = String(screenTypeSelect?.value || 'dynamic_list').trim().toLowerCase();
    if (menuUrlPreview) menuUrlPreview.textContent = screenMenuUrl(tableName, screenType);
    if (formUrlPreview) formUrlPreview.textContent = screenFormUrl(tableName);
  }

  function tableIsBlocked() {
    const meta = state.selectedTableMeta;
    if (!meta) return 'Seleciona uma tabela.';
    if (!meta.supported) return meta.warning || 'Tabela não suportada.';
    if (meta.has_menu || meta.has_campos) return 'A tabela já tem MENU ou CAMPOS configurados.';
    return '';
  }

  function renderOrderPickerRows(filter = '') {
    if (!orderBody) return;
    const needle = String(filter || '').trim().toLowerCase();
    const rows = (Array.isArray(state.menuPositions?.items) ? state.menuPositions.items : []).filter(item => {
      if (!needle) return true;
      return `${item.LABEL || ''} ${item.TABELA || ''}`.toLowerCase().includes(needle);
    });

    if (!rows.length) {
      orderBody.innerHTML = '<tr><td colspan="3" class="sz_text_muted">Sem itens para mostrar.</td></tr>';
      return;
    }

    orderBody.innerHTML = rows.map(item => `
      <tr class="${item.IS_GROUP ? 'is-group' : ''}">
        <td class="sz_col_fit">${Number(item.ORDEM || 0)}</td>
        <td>
          <div class="swz-order-label">
            ${'<span class="swz-order-indent"></span>'.repeat(Number(item.INDENT || 0))}
            <div class="swz-order-label-text">
              <strong>${escapeHtml(item.LABEL || 'Menu')}</strong>
              <span>${escapeHtml(item.TABELA || (item.IS_GROUP ? 'Grupo' : 'Item'))}</span>
            </div>
          </div>
        </td>
        <td class="sz_col_fit">
          <button
            type="button"
            class="sz_button sz_button_secondary swz-order-pick"
            data-order="${Number(item.SUGGESTED_AFTER || 0)}"
            data-label="${escapeHtml(`Depois de ${item.LABEL || 'item'}`)}">
            Depois
          </button>
        </td>
      </tr>
    `).join('');

    orderBody.querySelectorAll('.swz-order-pick').forEach(button => {
      button.addEventListener('click', () => {
        const nextOrder = Number(button.dataset.order || 0);
        const label = String(button.dataset.label || '').trim();
        if (orderInput) orderInput.value = String(nextOrder);
        setStatus(`Ordem definida para ${nextOrder}. ${label}.`, 'muted');
        try {
          window.bootstrap?.Modal.getInstance(orderModalEl)?.hide();
        } catch (_) {}
      });
    });
  }

  function openOrderPicker() {
    const firstButton = orderModalEl?.querySelector('.swz-order-quick-actions .swz-order-pick');
    if (firstButton) {
      firstButton.dataset.order = String(Number(state.menuPositions?.before_first || 0));
    }
    renderOrderPickerRows(orderSearch?.value || '');
    try {
      window.bootstrap?.Modal.getOrCreateInstance(orderModalEl)?.show();
    } catch (_) {}
  }

  function renderModules() {
    if (!modulesHost) return;
    if (!state.modules.length) {
      modulesHost.innerHTML = '<div class="sz_text_muted">Sem módulos ativos.</div>';
      return;
    }
    modulesHost.innerHTML = state.modules.map(mod => `
      <label class="swz-module-card">
        <input type="checkbox" value="${mod.MODSTAMP}" />
        <span class="swz-module-meta">
          <strong>${mod.NOME || mod.CODIGO || 'Módulo'}</strong>
          <span>${mod.CODIGO || ''}${mod.DESCR ? ` · ${mod.DESCR}` : ''}</span>
        </span>
      </label>
    `).join('');
  }

  function renderAclUsers() {
    if (!aclBody) return;
    if (!state.aclUsers.length) {
      aclBody.innerHTML = '<tr><td colspan="5" class="sz_text_muted">Sem utilizadores elegíveis.</td></tr>';
      return;
    }
    aclBody.innerHTML = state.aclUsers.map(user => `
      <tr>
        <td>
          <span class="swz-layout-name">${user.NOME || user.LOGIN}</span>
          <span class="swz-layout-note">${user.LOGIN}${user.ADMIN_USER ? ' · Admin' : ''}</span>
        </td>
        <td class="sz_col_fit"><input type="checkbox" class="swz-acl-flag" data-login="${user.LOGIN}" data-flag="consultar" ${user.consultar ? 'checked' : ''}></td>
        <td class="sz_col_fit"><input type="checkbox" class="swz-acl-flag" data-login="${user.LOGIN}" data-flag="inserir" ${user.inserir ? 'checked' : ''}></td>
        <td class="sz_col_fit"><input type="checkbox" class="swz-acl-flag" data-login="${user.LOGIN}" data-flag="editar" ${user.editar ? 'checked' : ''}></td>
        <td class="sz_col_fit"><input type="checkbox" class="swz-acl-flag" data-login="${user.LOGIN}" data-flag="eliminar" ${user.eliminar ? 'checked' : ''}></td>
      </tr>
    `).join('');

    aclBody.querySelectorAll('.swz-acl-flag').forEach(input => {
      input.addEventListener('change', () => {
        const login = String(input.dataset.login || '').trim();
        const flag = String(input.dataset.flag || '').trim();
        const user = state.aclUsers.find(row => row.LOGIN === login);
        if (!user || !flag) return;
        user[flag] = input.checked;
      });
    });
  }

  function renderTables() {
    if (!tableSelect) return;
    const current = selectedTableName();
    const options = ['<option value="">Seleciona tabela</option>'].concat(
      state.tables.map(item => {
        const flags = [];
        if (!item.supported) flags.push('não suportada');
        if (item.has_menu || item.has_campos) flags.push('já configurada');
        const label = flags.length ? `${item.table_name} [${flags.join(' / ')}]` : item.table_name;
        return `<option value="${item.table_name}">${label}</option>`;
      })
    );
    tableSelect.innerHTML = options.join('');
    if (current) tableSelect.value = current;
  }

  function renderAvailableFields() {
    if (!availableBody) return;
    if (!selectedTableName()) {
      availableBody.innerHTML = '<tr><td colspan="4" class="sz_text_muted">Seleciona uma tabela.</td></tr>';
      return;
    }
    if (state.loadingColumns) {
      availableBody.innerHTML = '<tr><td colspan="4" class="sz_text_muted">A carregar campos...</td></tr>';
      return;
    }
    if (!state.columns.length) {
      availableBody.innerHTML = '<tr><td colspan="4" class="sz_text_muted">Sem campos disponíveis.</td></tr>';
      return;
    }

    const selectedNames = currentFieldNames();
    availableBody.innerHTML = state.columns.map(col => {
      const disabled = !col.supported || selectedNames.has(col.name);
      const noteParts = [];
      if (col.is_pk) noteParts.push('PK');
      if (col.is_identity) noteParts.push('Identity');
      if (col.is_computed) noteParts.push('Computado');
      if (col.warning) noteParts.push(col.warning);
      if (col.nullable) noteParts.push('Nullable');
      const notes = noteParts.join(' · ') || '--';
      return `
        <tr>
          <td class="sz_col_fit">
            <button type="button"
                    class="sz_button sz_button_ghost swz-add-field"
                    data-name="${col.name}"
                    ${disabled ? 'disabled' : ''}>
              <i class="fa-solid fa-plus"></i>
            </button>
          </td>
          <td>
            <span class="swz-layout-name">${col.name}</span>
            <span class="swz-layout-note">${col.default_label || ''}</span>
          </td>
          <td>${col.sql_type || '--'}</td>
          <td class="${col.supported ? '' : 'swz-unsupported'}">${notes}</td>
        </tr>
      `;
    }).join('');

    availableBody.querySelectorAll('.swz-add-field').forEach(button => {
      button.addEventListener('click', () => addField(button.dataset.name || ''));
    });
  }

  function renderLayout() {
    if (!layoutBody) return;
    if (!state.layout.length) {
      layoutBody.innerHTML = '<tr><td colspan="9" class="sz_text_muted">Ainda não existem campos selecionados.</td></tr>';
      renderAvailableFields();
      return;
    }

    layoutBody.innerHTML = state.layout.map((item, index) => {
      if (item.kind === 'separator') {
        return `
          <tr class="swz-separator-row">
            <td class="sz_col_fit">${currentRowNumberUntil(index)}</td>
            <td colspan="7"><strong>Separador de linha</strong></td>
            <td class="sz_col_fit">
              <div class="swz-action-buttons">
                <button type="button" class="sz_button sz_button_ghost swz-move-up" data-index="${index}" ${index === 0 ? 'disabled' : ''}><i class="fa-solid fa-arrow-up"></i></button>
                <button type="button" class="sz_button sz_button_ghost swz-move-down" data-index="${index}" ${index === state.layout.length - 1 ? 'disabled' : ''}><i class="fa-solid fa-arrow-down"></i></button>
                <button type="button" class="sz_button sz_button_danger swz-remove-item" data-index="${index}"><i class="fa-solid fa-trash"></i></button>
              </div>
            </td>
          </tr>
        `;
      }

      const typeOptions = FIELD_TYPE_OPTIONS.map(opt => `
        <option value="${opt.value}" ${item.field_type === opt.value ? 'selected' : ''}>${opt.label}</option>
      `).join('');

      return `
        <tr>
          <td class="sz_col_fit">${currentRowNumberUntil(index)}</td>
          <td>
            <span class="swz-layout-name">${item.name}</span>
            <span class="swz-layout-note">${item.sql_type || ''}</span>
          </td>
          <td>
            <input type="text" class="sz_input swz-layout-description" data-index="${index}" value="${item.description || ''}" maxlength="60" />
          </td>
          <td class="sz_col_fit">
            <select class="sz_select swz-layout-type" data-index="${index}">
              ${typeOptions}
            </select>
          </td>
          <td class="sz_col_fit">
            <input type="checkbox" class="swz-layout-lista" data-index="${index}" ${item.lista ? 'checked' : ''} />
          </td>
          <td class="sz_col_fit">
            <input type="checkbox" class="swz-layout-filtro" data-index="${index}" ${item.filtro ? 'checked' : ''} />
          </td>
          <td class="sz_col_fit">
            <input type="checkbox" class="swz-layout-readonly" data-index="${index}" ${item.readonly ? 'checked' : ''} ${item.readonlyLocked ? 'disabled' : ''} />
          </td>
          <td class="sz_col_fit">
            <input type="checkbox" class="swz-layout-required" data-index="${index}" ${item.required ? 'checked' : ''} ${item.readonly ? 'disabled' : ''} />
          </td>
          <td class="sz_col_fit">
            <div class="swz-action-buttons">
              <button type="button" class="sz_button sz_button_ghost swz-move-up" data-index="${index}" ${index === 0 ? 'disabled' : ''}><i class="fa-solid fa-arrow-up"></i></button>
              <button type="button" class="sz_button sz_button_ghost swz-move-down" data-index="${index}" ${index === state.layout.length - 1 ? 'disabled' : ''}><i class="fa-solid fa-arrow-down"></i></button>
              <button type="button" class="sz_button sz_button_danger swz-remove-item" data-index="${index}"><i class="fa-solid fa-trash"></i></button>
            </div>
          </td>
        </tr>
      `;
    }).join('');

    layoutBody.querySelectorAll('.swz-layout-description').forEach(input => {
      input.addEventListener('input', () => {
        const index = Number(input.dataset.index || -1);
        if (!Number.isInteger(index) || !state.layout[index]) return;
        state.layout[index].description = input.value.trim();
      });
    });

    layoutBody.querySelectorAll('.swz-layout-type').forEach(select => {
      select.addEventListener('change', () => {
        const index = Number(select.dataset.index || -1);
        if (!Number.isInteger(index) || !state.layout[index]) return;
        state.layout[index].field_type = select.value;
      });
    });

    layoutBody.querySelectorAll('.swz-layout-lista').forEach(input => {
      input.addEventListener('change', () => {
        const index = Number(input.dataset.index || -1);
        if (!Number.isInteger(index) || !state.layout[index]) return;
        state.layout[index].lista = input.checked;
      });
    });

    layoutBody.querySelectorAll('.swz-layout-filtro').forEach(input => {
      input.addEventListener('change', () => {
        const index = Number(input.dataset.index || -1);
        if (!Number.isInteger(index) || !state.layout[index]) return;
        state.layout[index].filtro = input.checked;
      });
    });

    layoutBody.querySelectorAll('.swz-layout-readonly').forEach(input => {
      input.addEventListener('change', () => {
        const index = Number(input.dataset.index || -1);
        if (!Number.isInteger(index) || !state.layout[index]) return;
        state.layout[index].readonly = input.checked;
        if (input.checked) {
          state.layout[index].required = false;
        }
        renderLayout();
      });
    });

    layoutBody.querySelectorAll('.swz-layout-required').forEach(input => {
      input.addEventListener('change', () => {
        const index = Number(input.dataset.index || -1);
        if (!Number.isInteger(index) || !state.layout[index]) return;
        state.layout[index].required = input.checked;
      });
    });

    layoutBody.querySelectorAll('.swz-remove-item').forEach(button => {
      button.addEventListener('click', () => removeItem(Number(button.dataset.index || -1)));
    });
    layoutBody.querySelectorAll('.swz-move-up').forEach(button => {
      button.addEventListener('click', () => moveItem(Number(button.dataset.index || -1), -1));
    });
    layoutBody.querySelectorAll('.swz-move-down').forEach(button => {
      button.addEventListener('click', () => moveItem(Number(button.dataset.index || -1), 1));
    });

    renderAvailableFields();
  }

  function addField(fieldName) {
    const field = state.columns.find(col => col.name === String(fieldName || '').trim().toUpperCase());
    if (!field) return;
    if (!field.supported) {
      setStatus(field.warning || 'Campo não suportado.', 'danger');
      return;
    }
    if (currentFieldNames().has(field.name)) {
      setStatus(`O campo ${field.name} já está no layout.`, 'warning');
      return;
    }
    state.layout.push({
      kind: 'field',
      name: field.name,
      description: field.default_label || field.name,
      field_type: field.default_type || 'TEXT',
      lista: String(screenTypeSelect?.value || '').trim().toLowerCase() === 'dynamic_list',
      filtro: false,
      readonly: !!(field.is_pk || field.is_identity || field.is_computed),
      readonlyLocked: !!(field.is_pk || field.is_identity || field.is_computed),
      required: false,
      sql_type: field.sql_type || '',
    });
    renderLayout();
    setStatus(`Campo ${field.name} adicionado.`, 'success');
  }

  function addSeparator() {
    if (!state.layout.length) {
      setStatus('Adiciona primeiro pelo menos um campo.', 'warning');
      return;
    }
    if (state.layout[state.layout.length - 1]?.kind === 'separator') {
      setStatus('O último item já é um separador.', 'warning');
      return;
    }
    state.layout.push({ kind: 'separator' });
    renderLayout();
    setStatus('Separador de linha adicionado.', 'success');
  }

  function removeItem(index) {
    if (!Number.isInteger(index) || index < 0 || index >= state.layout.length) return;
    state.layout.splice(index, 1);
    while (state.layout.length && state.layout[0]?.kind === 'separator') state.layout.shift();
    while (state.layout.length && state.layout[state.layout.length - 1]?.kind === 'separator') state.layout.pop();
    renderLayout();
  }

  function moveItem(index, direction) {
    const target = index + direction;
    if (!Number.isInteger(index) || index < 0 || target < 0 || target >= state.layout.length) return;
    const current = state.layout[index];
    state.layout[index] = state.layout[target];
    state.layout[target] = current;
    renderLayout();
  }

  function resetLayout() {
    state.layout = [];
    renderLayout();
  }

  function clearWizard() {
    if (tableSelect) tableSelect.value = '';
    if (screenTypeSelect) screenTypeSelect.value = 'dynamic_list';
    if (titleInput) titleInput.value = '';
    if (iconInput) iconInput.value = 'fa-solid fa-table-list';
    if (orderInput) orderInput.value = '0';
    if (orderByInput) orderByInput.value = '';
    if (adminInput) adminInput.checked = false;
    if (novoInput) novoInput.checked = true;
    modulesHost?.querySelectorAll('input[type="checkbox"]').forEach(input => {
      input.checked = false;
    });
    state.selectedTableMeta = null;
    state.columns = [];
    resetLayout();
    state.aclUsers = state.aclUsers.map(user => ({
      ...user,
      consultar: false,
      inserir: false,
      editar: false,
      eliminar: false,
    }));
    renderAclUsers();
    updatePreview();
    renderAvailableFields();
    setStatus('Wizard limpo.', 'muted');
  }

  function collectModules() {
    return Array.from(modulesHost?.querySelectorAll('input[type="checkbox"]:checked') || [])
      .map(input => String(input.value || '').trim())
      .filter(Boolean);
  }

  function collectPayload() {
    return {
      table_name: selectedTableName(),
      screen_type: String(screenTypeSelect?.value || 'dynamic_list').trim().toLowerCase(),
      title: String(titleInput?.value || '').trim(),
      icon: String(iconInput?.value || '').trim(),
      menu_order: Number(orderInput?.value || 0),
      orderby: String(orderByInput?.value || '').trim(),
      admin: !!adminInput?.checked,
      novo: !!novoInput?.checked,
      modules: collectModules(),
      acl_rows: state.aclUsers
        .filter(user => user.consultar || user.inserir || user.editar || user.eliminar)
        .map(user => ({
          utilizador: user.LOGIN,
          usstamp: user.USSTAMP,
          consultar: !!user.consultar,
          inserir: !!user.inserir,
          editar: !!user.editar,
          eliminar: !!user.eliminar,
        })),
      layout: state.layout.map(item => ({ ...item })),
    };
  }

  async function loadColumns(tableName) {
    const normalized = String(tableName || '').trim().toUpperCase();
    state.loadingColumns = true;
    state.columns = [];
    renderAvailableFields();
    try {
      const data = await fetchJson(`${cfg.columnsUrl}?table=${encodeURIComponent(normalized)}`);
      state.columns = Array.isArray(data.columns) ? data.columns : [];
      setStatus(`Tabela ${normalized}: ${state.columns.length} campos carregados.`, 'muted');
    } catch (error) {
      state.columns = [];
      setStatus(error.message || 'Erro ao carregar os campos.', 'danger');
    } finally {
      state.loadingColumns = false;
      renderAvailableFields();
    }
  }

  async function handleTableChange() {
    const nextTable = selectedTableName();
    const nextMeta = state.tables.find(item => item.table_name === nextTable) || null;
    if (state.layout.length && nextTable !== (state.selectedTableMeta?.table_name || '')) {
      const ok = window.confirm('Mudar de tabela limpa o layout atual. Continuar?');
      if (!ok) {
        if (tableSelect) tableSelect.value = state.selectedTableMeta?.table_name || '';
        return;
      }
      resetLayout();
    }
    state.selectedTableMeta = nextMeta;
    if (titleInput && nextTable && !titleInput.value.trim()) {
      titleInput.value = prettifyTableName(nextTable);
    }
    updatePreview();
    const blocked = tableIsBlocked();
    if (blocked) {
      setStatus(blocked, nextMeta?.supported === false ? 'danger' : 'warning');
    }
    if (nextTable) {
      await loadColumns(nextTable);
    } else {
      state.columns = [];
      renderAvailableFields();
    }
  }

  async function saveWizard() {
    if (state.saving) return;
    const blocked = tableIsBlocked();
    if (blocked) {
      setStatus(blocked, 'danger');
      return;
    }

    const payload = collectPayload();
    if (!payload.table_name) {
      setStatus('Seleciona a tabela.', 'danger');
      return;
    }
    if (!payload.modules.length) {
      setStatus('Seleciona pelo menos um módulo.', 'danger');
      return;
    }
    if (!payload.layout.some(item => item.kind === 'field')) {
      setStatus('Seleciona pelo menos um campo.', 'danger');
      return;
    }

    state.saving = true;
    saveBtn?.setAttribute('disabled', 'disabled');
    setStatus('A gravar MENU, MOD_OBJETOS e CAMPOS...', 'muted');
    try {
      const result = await fetchJson(cfg.saveUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      setStatus(`Ecrã criado. MENU ${result.menu?.tabela || payload.table_name} com ${result.campos_count || 0} campos.`, 'success');
    } catch (error) {
      setStatus(error.message || 'Erro ao gravar o wizard.', 'danger');
    } finally {
      state.saving = false;
      saveBtn?.removeAttribute('disabled');
    }
  }

  async function init() {
    try {
      setStatus('A carregar wizard...', 'muted');
      const data = await fetchJson(cfg.bootstrapUrl);
      state.tables = Array.isArray(data.tables) ? data.tables : [];
      state.modules = Array.isArray(data.modules) ? data.modules : [];
      state.menuPositions = data.menu_positions && typeof data.menu_positions === 'object'
        ? data.menu_positions
        : { items: [], before_first: 0, after_last: 10 };
      state.aclUsers = (Array.isArray(data.acl_users) ? data.acl_users : []).map(user => ({
        ...user,
        consultar: String(user.LOGIN || '').trim() === String(data.current_user_login || '').trim(),
        inserir: String(user.LOGIN || '').trim() === String(data.current_user_login || '').trim(),
        editar: String(user.LOGIN || '').trim() === String(data.current_user_login || '').trim(),
        eliminar: false,
      }));
      if (iconInput) iconInput.value = data.defaults?.icon || 'fa-solid fa-table-list';
      if (screenTypeSelect) screenTypeSelect.value = data.defaults?.screen_type || 'dynamic_list';
      if (novoInput) novoInput.checked = !!data.defaults?.novo;
      if (adminInput) adminInput.checked = !!data.defaults?.admin;
      if (orderByInput) orderByInput.value = data.defaults?.orderby || '';
      renderTables();
      renderModules();
      renderAclUsers();
      renderAvailableFields();
      renderLayout();
      updatePreview();
      setStatus('Wizard pronto.', 'muted');
    } catch (error) {
      setStatus(error.message || 'Erro ao carregar o wizard.', 'danger');
    }
  }

  tableSelect?.addEventListener('change', handleTableChange);
  screenTypeSelect?.addEventListener('change', updatePreview);
  saveBtn?.addEventListener('click', saveWizard);
  clearBtn?.addEventListener('click', clearWizard);
  separatorBtn?.addEventListener('click', addSeparator);
  orderPickerBtn?.addEventListener('click', openOrderPicker);
  orderSearch?.addEventListener('input', () => renderOrderPickerRows(orderSearch.value));
  orderLastBtn?.addEventListener('click', () => {
    const order = Number(state.menuPositions?.after_last || 10);
    if (orderInput) orderInput.value = String(order);
    setStatus(`Ordem definida para ${order}. No fim do menu.`, 'muted');
    try {
      window.bootstrap?.Modal.getInstance(orderModalEl)?.hide();
    } catch (_) {}
  });
  orderModalEl?.querySelectorAll('.swz-order-quick-actions .swz-order-pick').forEach(button => {
    button.addEventListener('click', () => {
      const order = Number(button.dataset.order || 0);
      const label = String(button.dataset.label || 'No topo').trim();
      if (orderInput) orderInput.value = String(order);
      setStatus(`Ordem definida para ${order}. ${label}.`, 'muted');
      try {
        window.bootstrap?.Modal.getInstance(orderModalEl)?.hide();
      } catch (_) {}
    });
  });
  orderModalEl?.addEventListener('shown.bs.modal', () => {
    orderSearch?.focus();
    orderSearch?.select?.();
  });

  init().catch(error => {
    setStatus(error.message || 'Erro inesperado ao iniciar o wizard.', 'danger');
  });
});
