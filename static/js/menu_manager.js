(function () {
  const state = {
    rows: [],
    current: null,
    selectedMenustamp: String(window.MENU_MANAGER_INITIAL_MENUSTAMP || '').trim(),
    listSearchTimer: null,
    dragMenustamp: '',
    dropMenustamp: '',
    dropPlacement: '',
    modulesRows: [],
    modulesMenustamp: '',
    usersRows: [],
    usersMenustamp: '',
    usersSupported: false,
  };

  const ICON_CATALOG = Array.isArray(window.MENU_MANAGER_ICON_CATALOG) && window.MENU_MANAGER_ICON_CATALOG.length
    ? window.MENU_MANAGER_ICON_CATALOG
    : [
        ['fa-solid fa-table-list', 'Lista'],
        ['fa-solid fa-folder-open', 'Pasta'],
        ['fa-solid fa-folder-tree', 'Hierarquia'],
        ['fa-solid fa-bars', 'Menu'],
        ['fa-solid fa-house', 'Casa'],
        ['fa-solid fa-chart-line', 'Gr?fico linha'],
        ['fa-solid fa-chart-column', 'Gr?fico colunas'],
        ['fa-solid fa-calendar', 'Calend?rio'],
        ['fa-solid fa-gear', 'Configura??o'],
        ['fa-solid fa-users', 'Utilizadores'],
        ['fa-solid fa-file-invoice', 'Fatura'],
        ['fa-solid fa-truck', 'Transporte'],
        ['fa-solid fa-bed', 'Alojamento'],
        ['fa-solid fa-broom', 'Limpeza'],
        ['fa-solid fa-envelope', 'Email'],
      ];

  const permissions = {
    create: !!window.MENU_MANAGER_CAN_CREATE,
    edit: !!window.MENU_MANAGER_CAN_EDIT,
    delete: !!window.MENU_MANAGER_CAN_DELETE,
  };

  const els = {
    list: document.getElementById('menuMgrList'),
    listSummary: document.getElementById('menuMgrListSummary'),
    search: document.getElementById('menuMgrSearch'),
    kindFilter: document.getElementById('menuMgrKindFilter'),
    btnNew: document.getElementById('menuMgrBtnNew'),
    btnUp: document.getElementById('menuMgrBtnUp'),
    btnDown: document.getElementById('menuMgrBtnDown'),
    btnCancel: document.getElementById('menuMgrBtnCancel'),
    btnDelete: document.getElementById('menuMgrBtnDelete'),
    btnSave: document.getElementById('menuMgrBtnSave'),
    btnOpenModules: document.getElementById('menuMgrOpenModules'),
    btnOpenUsers: document.getElementById('menuMgrOpenUsers'),
    btnIconPicker: document.getElementById('menuMgrIconPickerBtn'),
    editorModalEl: document.getElementById('menuMgrEditorModal'),
    editorTitle: document.getElementById('menuMgrEditorTitle'),
    moduleCount: document.getElementById('menuMgrModuleCount'),
    userCount: document.getElementById('menuMgrUserCount'),
    kindBadge: document.getElementById('menuMgrKindBadge'),
    inactiveBadge: document.getElementById('menuMgrInactiveBadge'),
    iconPreview: document.getElementById('menuMgrIconPreview'),
    modulesModalEl: document.getElementById('menuMgrModulesModal'),
    modulesSubtitle: document.getElementById('menuMgrModulesSubtitle'),
    modulesSearch: document.getElementById('menuMgrModulesSearch'),
    modulesBody: document.getElementById('menuMgrModulesBody'),
    modulesSave: document.getElementById('menuMgrModulesSave'),
    usersModalEl: document.getElementById('menuMgrUsersModal'),
    usersSubtitle: document.getElementById('menuMgrUsersSubtitle'),
    usersSearch: document.getElementById('menuMgrUsersSearch'),
    usersBody: document.getElementById('menuMgrUsersBody'),
    usersNotice: document.getElementById('menuMgrUsersNotice'),
    usersSave: document.getElementById('menuMgrUsersSave'),
    iconsModalEl: document.getElementById('menuMgrIconsModal'),
    iconsSearch: document.getElementById('menuMgrIconsSearch'),
    iconsGrid: document.getElementById('menuMgrIconsGrid'),
    fields: {
      MENUSTAMP: document.getElementById('menuMgrMENUSTAMP'),
      ORDEM: document.getElementById('menuMgrORDEM'),
      NOME: document.getElementById('menuMgrNOME'),
      TABELA: document.getElementById('menuMgrTABELA'),
      URL: document.getElementById('menuMgrURL'),
      ADMIN: document.getElementById('menuMgrADMIN'),
      INATIVO: document.getElementById('menuMgrINATIVO'),
      ICONE: document.getElementById('menuMgrICONE'),
      FORM: document.getElementById('menuMgrFORM'),
      ORDERBY: document.getElementById('menuMgrORDERBY'),
      NOVO: document.getElementById('menuMgrNOVO'),
    },
  };

  const editorModal = els.editorModalEl ? bootstrap.Modal.getOrCreateInstance(els.editorModalEl) : null;
  const modulesModal = els.modulesModalEl ? bootstrap.Modal.getOrCreateInstance(els.modulesModalEl) : null;
  const usersModal = els.usersModalEl ? bootstrap.Modal.getOrCreateInstance(els.usersModalEl) : null;
  const iconsModal = els.iconsModalEl ? bootstrap.Modal.getOrCreateInstance(els.iconsModalEl) : null;

  function esc(value) {
    return String(value ?? '').replace(/[&<>"']/g, (match) => (
      { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[match]
    ));
  }

  function showToast(message, type = 'success') {
    if (typeof window.showToast === 'function') {
      window.showToast(message, type);
      return;
    }
    window.alert(message);
  }

  function nextDefaultOrder() {
    if (!state.rows.length) return 10;
    return Number(state.rows[state.rows.length - 1]?.ORDEM || 0) + 10;
  }

  function emptyRow() {
    return {
      MENUSTAMP: '',
      ORDEM: nextDefaultOrder(),
      NOME: '',
      TABELA: '',
      URL: '',
      ADMIN: 0,
      INATIVO: 0,
      ICONE: 'fa-solid fa-folder-open',
      FORM: '',
      ORDERBY: '',
      NOVO: 0,
      MODULE_COUNT: 0,
      USER_COUNT: 0,
      IS_GROUP: false,
      CHILD_COUNT: 0,
      INDENT: 0,
    };
  }

  function normalizeRow(row) {
    return { ...emptyRow(), ...(row || {}) };
  }

  function isExisting() {
    return !!String(els.fields.MENUSTAMP?.value || '').trim();
  }

  function formatKind(row) {
    return row?.IS_GROUP ? 'Agrupador' : 'Submenu';
  }

  function normalizeIconValue(value) {
    const raw = String(value || '').trim();
    if (!raw) return 'fa-solid fa-folder-open';
    if (/\bfa-(solid|regular|brands|light|thin|duotone|sharp)\b/.test(raw)) return raw;
    if (/\bfa-[a-z0-9-]+\b/.test(raw)) return `fa-solid ${raw}`;
    return 'fa-solid fa-folder-open';
  }

  function currentIconClass(row) {
    return normalizeIconValue(row?.ICONE);
  }

  function syncIconPreview(value) {
    if (!els.iconPreview) return;
    els.iconPreview.className = normalizeIconValue(value);
  }

  function fillForm(row) {
    const current = normalizeRow(row);
    state.current = current;
    state.selectedMenustamp = String(current.MENUSTAMP || '').trim();

    Object.entries(els.fields).forEach(([key, field]) => {
      if (!field) return;
      if (field.type === 'checkbox') {
        field.checked = !!current[key];
      } else {
        field.value = key === 'ICONE' ? normalizeIconValue(current[key]) : (current[key] ?? '');
      }
    });
    syncIconPreview(current.ICONE);

    if (els.editorTitle) els.editorTitle.textContent = current.NOME || 'Novo registo';
    if (els.kindBadge) {
      els.kindBadge.textContent = formatKind(current);
      els.kindBadge.className = `sz_badge ${current.IS_GROUP ? 'sz_badge_warning' : 'sz_badge_info'}`;
    }
    if (els.inactiveBadge) {
      els.inactiveBadge.classList.toggle('sz_hidden', !current.INATIVO);
    }
    if (els.moduleCount) els.moduleCount.textContent = String(current.MODULE_COUNT || 0);
    if (els.userCount) els.userCount.textContent = String(current.USER_COUNT || 0);

    const existing = !!current.MENUSTAMP;
    if (els.btnDelete) els.btnDelete.disabled = !existing || !permissions.delete;
    if (els.btnUp) els.btnUp.disabled = !existing || !permissions.edit;
    if (els.btnDown) els.btnDown.disabled = !existing || !permissions.edit;
    if (els.btnOpenModules) els.btnOpenModules.disabled = !existing;
    if (els.btnOpenUsers) els.btnOpenUsers.disabled = !existing;
    if (els.btnSave) els.btnSave.disabled = !(existing ? permissions.edit : permissions.create);

    renderList();
  }

  function collectForm() {
    return {
      MENUSTAMP: String(els.fields.MENUSTAMP?.value || '').trim(),
      ORDEM: Number(els.fields.ORDEM?.value || 0),
      NOME: String(els.fields.NOME?.value || '').trim(),
      TABELA: String(els.fields.TABELA?.value || '').trim().toUpperCase(),
      URL: String(els.fields.URL?.value || '').trim(),
      ADMIN: els.fields.ADMIN?.checked ? 1 : 0,
      INATIVO: els.fields.INATIVO?.checked ? 1 : 0,
      ICONE: normalizeIconValue(els.fields.ICONE?.value),
      FORM: String(els.fields.FORM?.value || '').trim(),
      ORDERBY: String(els.fields.ORDERBY?.value || '').trim(),
      NOVO: els.fields.NOVO?.checked ? 1 : 0,
    };
  }

  function cardSecondaryText(row) {
    const parts = [];
    if (row.TABELA) parts.push(row.TABELA);
    else if (row.IS_GROUP) parts.push('Agrupador');
    if (row.URL) parts.push(row.URL);
    parts.push(`Ordem ${row.ORDEM}`);
    return parts.join(' · ');
  }

  function renderList() {
    if (!els.list) return;
    if (!state.rows.length) {
      els.list.innerHTML = '<div class="sz_panel sz_menu_manager_empty">Sem registos para os filtros aplicados.</div>';
      if (els.listSummary) els.listSummary.textContent = '0 registos';
      return;
    }

    els.list.innerHTML = state.rows.map((row) => `
      <div class="sz_panel sz_menu_manager_card ${state.selectedMenustamp === row.MENUSTAMP ? 'is-selected' : ''} ${row.INDENT ? 'is-child' : ''} ${row.INATIVO ? 'is-inactive' : ''}" data-menustamp="${esc(row.MENUSTAMP)}" draggable="${permissions.edit ? 'true' : 'false'}">
        <div class="sz_menu_manager_card_icon" data-action="pickIcon" data-menustamp="${esc(row.MENUSTAMP)}" title="Alterar ícone">
          <i class="${esc(currentIconClass(row))}"></i>
        </div>
        <div class="sz_menu_manager_card_body" data-action="edit" data-menustamp="${esc(row.MENUSTAMP)}">
          <div class="sz_menu_manager_card_line1">
            <span class="sz_menu_manager_card_name">${esc(row.NOME || '(Sem nome)')}</span>
            <span class="sz_badge ${row.IS_GROUP ? 'sz_badge_warning' : 'sz_badge_info'}">${row.IS_GROUP ? 'Agrupador' : 'Submenu'}</span>
            ${row.TABELA ? `<span class="sz_badge sz_badge_info">${esc(row.TABELA)}</span>` : ''}
            <span class="sz_badge sz_badge_info">Ordem ${esc(row.ORDEM)}</span>
            ${row.INATIVO ? '<span class="sz_badge sz_badge_warning">Inativo</span>' : ''}
          </div>
        </div>
        <div class="sz_menu_manager_card_actions">
          <button type="button" class="sz_button sz_button_ghost sz_button_xs sz_menu_manager_count_btn" data-action="modules" data-menustamp="${esc(row.MENUSTAMP)}">
            <i class="fa-solid fa-cubes"></i>
            <span>${esc(row.MODULE_COUNT || 0)}</span>
          </button>
          <button type="button" class="sz_button sz_button_ghost sz_button_xs sz_menu_manager_count_btn" data-action="users" data-menustamp="${esc(row.MENUSTAMP)}" ${row.TABELA ? '' : 'disabled'}>
            <i class="fa-solid fa-users"></i>
            <span>${esc(row.USER_COUNT || 0)}</span>
          </button>
          <button type="button" class="sz_button sz_button_ghost sz_button_xs sz_menu_manager_card_btn" data-action="up" data-menustamp="${esc(row.MENUSTAMP)}" title="Subir">
            <i class="fa-solid fa-arrow-up"></i>
          </button>
          <button type="button" class="sz_button sz_button_ghost sz_button_xs sz_menu_manager_card_btn" data-action="down" data-menustamp="${esc(row.MENUSTAMP)}" title="Descer">
            <i class="fa-solid fa-arrow-down"></i>
          </button>
          <button type="button" class="sz_button sz_button_ghost sz_button_xs sz_menu_manager_card_btn" data-action="edit" data-menustamp="${esc(row.MENUSTAMP)}" title="Editar">
            <i class="fa-solid fa-pen"></i>
          </button>
          <button type="button" class="sz_button sz_button_ghost sz_button_xs sz_menu_manager_card_btn" data-action="toggleInactive" data-menustamp="${esc(row.MENUSTAMP)}" title="${row.INATIVO ? 'Ativar' : 'Inativar'}">
            <i class="fa-solid ${row.INATIVO ? 'fa-toggle-off' : 'fa-toggle-on'}"></i>
          </button>
          <button type="button" class="sz_button sz_button_danger sz_button_xs sz_menu_manager_card_btn" data-action="delete" data-menustamp="${esc(row.MENUSTAMP)}" title="Eliminar">
            <i class="fa-solid fa-trash"></i>
          </button>
        </div>
      </div>
    `).join('');

    if (els.listSummary) {
      els.listSummary.textContent = `${state.rows.length} registo${state.rows.length === 1 ? '' : 's'}`;
    }
  }

  function currentFilters() {
    return {
      q: String(els.search?.value || '').trim().toLowerCase(),
      kind: String(els.kindFilter?.value || '').trim(),
    };
  }

  function rowMatchesFilters(row) {
    const filters = currentFilters();
    if (!row) return false;
    if (filters.kind === 'group' && !row.IS_GROUP) return false;
    if (filters.kind === 'item' && row.IS_GROUP) return false;
    if (!filters.q) return true;
    const haystack = [
      row.NOME,
      row.TABELA,
      row.URL,
      row.ICONE,
    ].map((value) => String(value || '').toLowerCase());
    return haystack.some((value) => value.includes(filters.q));
  }

  function sortRows(rows) {
    return [...(rows || [])].sort((a, b) => {
      const ordemDiff = Number(a?.ORDEM || 0) - Number(b?.ORDEM || 0);
      if (ordemDiff !== 0) return ordemDiff;
      const nomeA = String(a?.NOME || '');
      const nomeB = String(b?.NOME || '');
      const nomeDiff = nomeA.localeCompare(nomeB, 'pt');
      if (nomeDiff !== 0) return nomeDiff;
      return String(a?.MENUSTAMP || '').localeCompare(String(b?.MENUSTAMP || ''), 'pt');
    });
  }

  function updateCurrentStateFromRows() {
    if (!state.selectedMenustamp) {
      state.current = null;
      return;
    }
    const row = state.rows.find((item) => String(item.MENUSTAMP || '').trim() === state.selectedMenustamp);
    if (row) {
      state.current = normalizeRow(row);
      if (els.editorModalEl?.classList.contains('show')) fillForm(row);
      return;
    }
    state.current = null;
  }

  function applyRowUpdate(row, { select = true } = {}) {
    const normalized = normalizeRow(row);
    const menustamp = String(normalized.MENUSTAMP || '').trim();
    if (!menustamp) return;

    const existingIndex = state.rows.findIndex((item) => String(item.MENUSTAMP || '').trim() === menustamp);
    const matches = rowMatchesFilters(normalized);

    if (existingIndex >= 0) {
      if (matches) state.rows.splice(existingIndex, 1, normalized);
      else state.rows.splice(existingIndex, 1);
    } else if (matches) {
      state.rows.push(normalized);
    }

    state.rows = sortRows(state.rows);
    if (select) state.selectedMenustamp = menustamp;
    updateCurrentStateFromRows();
    renderList();
  }

  function removeRowFromState(menustamp) {
    const target = String(menustamp || '').trim();
    if (!target) return;
    state.rows = state.rows.filter((row) => String(row.MENUSTAMP || '').trim() !== target);
    if (state.selectedMenustamp === target) {
      state.selectedMenustamp = '';
      state.current = null;
    } else {
      updateCurrentStateFromRows();
    }
    renderList();
  }

  async function loadList() {
    const qs = new URLSearchParams();
    const q = String(els.search?.value || '').trim();
    const kind = String(els.kindFilter?.value || '').trim();
    if (q) qs.set('q', q);
    if (kind) qs.set('kind', kind);

    els.list.innerHTML = '<div class="sz_panel sz_menu_manager_empty">A carregar...</div>';
    try {
      const res = await fetch(`/api/menu_manager?${qs.toString()}`);
      const data = await res.json().catch(() => ({}));
      if (!res.ok || data.error) throw new Error(data.error || 'Erro ao carregar o menu.');
      state.rows = Array.isArray(data.rows) ? data.rows : [];
      renderList();

      if (state.selectedMenustamp && state.rows.some((row) => row.MENUSTAMP === state.selectedMenustamp)) {
        const row = state.rows.find((item) => item.MENUSTAMP === state.selectedMenustamp);
        if (row) fillForm(row);
      } else {
        state.current = null;
        state.selectedMenustamp = '';
      }
    } catch (error) {
      els.list.innerHTML = `<div class="sz_panel sz_menu_manager_empty">${esc(error.message || 'Erro ao carregar o menu.')}</div>`;
      showToast(error.message || 'Erro ao carregar o menu.', 'error');
    }
  }

  async function openEditor(menustamp) {
    const target = String(menustamp || '').trim();
    if (!target) {
      fillForm(emptyRow());
      editorModal?.show();
      return;
    }

    try {
      const res = await fetch(`/api/menu_manager/${encodeURIComponent(target)}`);
      const data = await res.json().catch(() => ({}));
      if (!res.ok || data.error) throw new Error(data.error || 'Erro ao carregar o registo.');
      fillForm(data.row || emptyRow());
      editorModal?.show();
    } catch (error) {
      showToast(error.message || 'Erro ao carregar o registo.', 'error');
    }
  }

  async function openEditorAndIcons(menustamp) {
    await openEditor(menustamp);
    openIconsModal();
  }

  async function saveCurrent() {
    const row = collectForm();
    try {
      const res = await fetch('/api/menu_manager/save', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ row }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok || data.error) throw new Error(data.error || 'Erro ao gravar o menu.');
      const savedRow = data.row || { ...row, MENUSTAMP: data.menustamp || row.MENUSTAMP };
      applyRowUpdate(savedRow, { select: true });
      editorModal?.hide();
      showToast('Registo de menu gravado.', 'success');
    } catch (error) {
      showToast(error.message || 'Erro ao gravar o menu.', 'error');
    }
  }

  async function deleteMenu(menustamp) {
    const target = String(menustamp || '').trim();
    if (!target) return;
    if (!window.confirm('Eliminar este registo do menu?')) return;

    try {
      const res = await fetch(`/api/menu_manager/${encodeURIComponent(target)}/delete`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok || data.error) throw new Error(data.error || 'Erro ao eliminar o registo do menu.');
      if (state.selectedMenustamp === target) {
        editorModal?.hide();
      }
      removeRowFromState(target);
      showToast('Registo de menu eliminado.', 'success');
    } catch (error) {
      showToast(error.message || 'Erro ao eliminar o registo do menu.', 'error');
    }
  }

  async function moveMenu(menustamp, direction) {
    const target = String(menustamp || '').trim();
    if (!target) return;
    const currentIndex = state.rows.findIndex((row) => String(row.MENUSTAMP || '').trim() === target);
    if (currentIndex < 0) return;
    const swapIndex = direction === 'up' ? currentIndex - 1 : currentIndex + 1;
    if (swapIndex < 0 || swapIndex >= state.rows.length) return;
    const previousRows = [...state.rows];
    const reordered = [...state.rows];
    [reordered[currentIndex], reordered[swapIndex]] = [reordered[swapIndex], reordered[currentIndex]];
    state.rows = reordered;
    state.selectedMenustamp = target;
    renderList();
    await saveReorderedRows(previousRows, reordered);
  }

  async function toggleInactiveMenu(menustamp) {
    const target = String(menustamp || '').trim();
    if (!target) return;
    const row = state.rows.find((item) => String(item.MENUSTAMP || '').trim() === target);
    if (!row) return;

    const payload = {
      MENUSTAMP: row.MENUSTAMP,
      ORDEM: Number(row.ORDEM || 0),
      NOME: String(row.NOME || '').trim(),
      TABELA: String(row.TABELA || '').trim(),
      URL: String(row.URL || '').trim(),
      ADMIN: row.ADMIN ? 1 : 0,
      INATIVO: row.INATIVO ? 0 : 1,
      ICONE: String(row.ICONE || '').trim(),
      FORM: String(row.FORM || '').trim(),
      ORDERBY: String(row.ORDERBY || '').trim(),
      NOVO: row.NOVO ? 1 : 0,
    };

    try {
      const res = await fetch('/api/menu_manager/save', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ row: payload }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok || data.error) throw new Error(data.error || 'Erro ao atualizar o estado do menu.');
      applyRowUpdate({
        ...row,
        ...payload,
      }, { select: true });
      showToast(payload.INATIVO ? 'Menu inativado.' : 'Menu ativado.', 'success');
    } catch (error) {
      showToast(error.message || 'Erro ao atualizar o estado do menu.', 'error');
    }
  }

  function clearDragState() {
    state.dragMenustamp = '';
    state.dropMenustamp = '';
    state.dropPlacement = '';
    els.list?.querySelectorAll('.sz_menu_manager_card').forEach((card) => {
      card.classList.remove('is-dragging', 'is-drop-before', 'is-drop-after');
    });
  }

  function applyDropIndicator(targetCard, placement) {
    els.list?.querySelectorAll('.sz_menu_manager_card').forEach((card) => {
      card.classList.remove('is-drop-before', 'is-drop-after');
    });
    if (!targetCard || !placement) return;
    targetCard.classList.add(placement === 'before' ? 'is-drop-before' : 'is-drop-after');
  }

  function reorderRowsLocally(rows, draggedMenustamp, targetMenustamp, placement) {
    const ordered = Array.isArray(rows) ? [...rows] : [];
    const fromIndex = ordered.findIndex((row) => String(row.MENUSTAMP || '').trim() === draggedMenustamp);
    const targetIndex = ordered.findIndex((row) => String(row.MENUSTAMP || '').trim() === targetMenustamp);
    if (fromIndex < 0 || targetIndex < 0) return ordered;
    const [moved] = ordered.splice(fromIndex, 1);
    let insertIndex = targetIndex + (placement === 'after' ? 1 : 0);
    if (fromIndex < insertIndex) insertIndex -= 1;
    ordered.splice(insertIndex, 0, moved);
    return ordered;
  }

  async function saveReorderedRows(previousRows, nextRows) {
    const menustamps = nextRows.map((row) => String(row.MENUSTAMP || '').trim()).filter(Boolean);
    try {
      const res = await fetch('/api/menu_manager/reorder', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ menustamps }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok || data.error) throw new Error(data.error || 'Erro ao reordenar o menu.');
      state.rows = nextRows;
      updateCurrentStateFromRows();
      renderList();
    } catch (error) {
      state.rows = previousRows;
      updateCurrentStateFromRows();
      renderList();
      showToast(error.message || 'Erro ao reordenar o menu.', 'error');
    }
  }

  function renderIconsModal() {
    if (!els.iconsGrid) return;
    const query = String(els.iconsSearch?.value || '').trim().toLowerCase();
    const currentValue = normalizeIconValue(els.fields.ICONE?.value);
    const rows = ICON_CATALOG.filter(([icon, label]) => {
      if (!query) return true;
      return icon.toLowerCase().includes(query) || label.toLowerCase().includes(query);
    });

    if (!rows.length) {
      els.iconsGrid.innerHTML = '<div class="sz_panel sz_menu_manager_empty">Sem ícones para a pesquisa.</div>';
      return;
    }

    els.iconsGrid.innerHTML = rows.map(([icon, label]) => {
      const value = normalizeIconValue(icon);
      const selected = value === currentValue;
      return `
        <button type="button" class="sz_button sz_button_ghost sz_menu_manager_icon_option ${selected ? 'is-selected' : ''}" data-icon="${esc(value)}" title="${esc(label)}">
          <i class="${esc(value)}"></i>
          <span class="sz_menu_manager_icon_option_label">${esc(label)}</span>
        </button>
      `;
    }).join('');
  }

  function openIconsModal() {
    if (els.iconsSearch) els.iconsSearch.value = '';
    renderIconsModal();
    iconsModal?.show();
  }

  function renderModulesModal() {
    const q = String(els.modulesSearch?.value || '').trim().toLowerCase();
    const rows = state.modulesRows.filter((row) => (
      !q
      || String(row.CODIGO || '').toLowerCase().includes(q)
      || String(row.NOME || '').toLowerCase().includes(q)
      || String(row.DESCR || '').toLowerCase().includes(q)
    ));

    if (!rows.length) {
      els.modulesBody.innerHTML = `
        <tr class="sz_table_row">
          <td colspan="4" class="sz_table_cell sz_text_muted">Sem módulos para os filtros aplicados.</td>
        </tr>
      `;
      return;
    }

    els.modulesBody.innerHTML = rows.map((row) => `
      <tr class="sz_table_row">
        <td class="sz_table_cell">
          <input type="checkbox" class="form-check-input" data-modstamp="${esc(row.MODSTAMP)}" ${row.SELECTED ? 'checked' : ''}>
        </td>
        <td class="sz_table_cell">${esc(row.CODIGO)}</td>
        <td class="sz_table_cell">${esc(row.NOME)}</td>
        <td class="sz_table_cell">${esc(row.DESCR || '')}</td>
      </tr>
    `).join('');
  }

  async function openModulesModal(menustamp) {
    const target = String(menustamp || state.selectedMenustamp || '').trim();
    if (!target) return;

    try {
      const detail = state.rows.find((row) => row.MENUSTAMP === target) || state.current || {};
      if (els.modulesSubtitle) {
        els.modulesSubtitle.textContent = `Seleciona os módulos do menu ${detail.NOME || ''}.`;
      }
      const res = await fetch(`/api/menu_manager/${encodeURIComponent(target)}/modules`);
      const data = await res.json().catch(() => ({}));
      if (!res.ok || data.error) throw new Error(data.error || 'Erro ao carregar módulos.');
      state.modulesMenustamp = target;
      state.modulesRows = Array.isArray(data.rows) ? data.rows.map((row) => ({ ...row, SELECTED: !!row.SELECTED })) : [];
      if (els.modulesSearch) els.modulesSearch.value = '';
      renderModulesModal();
      modulesModal?.show();
    } catch (error) {
      showToast(error.message || 'Erro ao carregar módulos.', 'error');
    }
  }

  async function saveModulesModal() {
    if (!state.modulesMenustamp) return;
    const moduleStamps = state.modulesRows.filter((row) => row.SELECTED).map((row) => row.MODSTAMP);
    try {
      const res = await fetch(`/api/menu_manager/${encodeURIComponent(state.modulesMenustamp)}/modules/save`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ module_stamps: moduleStamps }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok || data.error) throw new Error(data.error || 'Erro ao gravar módulos.');
      modulesModal?.hide();
      const row = state.rows.find((item) => String(item.MENUSTAMP || '').trim() === state.modulesMenustamp);
      if (row) {
        applyRowUpdate({
          ...row,
          MODULE_COUNT: Number(data.count || moduleStamps.length || 0),
        }, { select: state.selectedMenustamp === state.modulesMenustamp });
      } else {
        renderList();
      }
      showToast('Módulos atualizados.', 'success');
    } catch (error) {
      showToast(error.message || 'Erro ao gravar módulos.', 'error');
    }
  }

  function renderUsersModal() {
    if (els.usersNotice) els.usersNotice.classList.toggle('sz_hidden', state.usersSupported);
    if (els.usersSave) els.usersSave.disabled = !state.usersSupported;

    const q = String(els.usersSearch?.value || '').trim().toLowerCase();
    const rows = state.usersRows.filter((row) => (
      !q
      || String(row.nome || '').toLowerCase().includes(q)
      || String(row.utilizador || '').toLowerCase().includes(q)
    ));

    if (!rows.length) {
      els.usersBody.innerHTML = `
        <tr class="sz_table_row">
          <td colspan="5" class="sz_table_cell sz_text_muted">${state.usersSupported ? 'Sem utilizadores para os filtros aplicados.' : 'Sem acessos próprios neste menu.'}</td>
        </tr>
      `;
      return;
    }

    els.usersBody.innerHTML = rows.map((row) => `
      <tr class="sz_table_row" data-login="${esc(row.utilizador)}">
        <td class="sz_table_cell">
          <div class="sz_stack">
            <strong>${esc(row.nome || row.utilizador)}</strong>
            <span class="sz_text_muted">${esc(row.utilizador)}${row.admin_user ? ' · admin' : ''}</span>
          </div>
        </td>
        <td class="sz_table_cell sz_text_center">
          <input type="checkbox" class="form-check-input" data-field="consultar" ${row.consultar ? 'checked' : ''} ${state.usersSupported ? '' : 'disabled'}>
        </td>
        <td class="sz_table_cell sz_text_center">
          <input type="checkbox" class="form-check-input" data-field="inserir" ${row.inserir ? 'checked' : ''} ${state.usersSupported ? '' : 'disabled'}>
        </td>
        <td class="sz_table_cell sz_text_center">
          <input type="checkbox" class="form-check-input" data-field="editar" ${row.editar ? 'checked' : ''} ${state.usersSupported ? '' : 'disabled'}>
        </td>
        <td class="sz_table_cell sz_text_center">
          <input type="checkbox" class="form-check-input" data-field="eliminar" ${row.eliminar ? 'checked' : ''} ${state.usersSupported ? '' : 'disabled'}>
        </td>
      </tr>
    `).join('');
  }

  async function openUsersModal(menustamp) {
    const target = String(menustamp || state.selectedMenustamp || '').trim();
    if (!target) return;

    try {
      const detail = state.rows.find((row) => row.MENUSTAMP === target) || state.current || {};
      if (els.usersSubtitle) {
        els.usersSubtitle.textContent = detail.TABELA
          ? `Permissões de acesso à tabela ${detail.TABELA}.`
          : 'Os agrupadores sem tabela não têm acessos próprios.';
      }
      const res = await fetch(`/api/menu_manager/${encodeURIComponent(target)}/users`);
      const data = await res.json().catch(() => ({}));
      if (!res.ok || data.error) throw new Error(data.error || 'Erro ao carregar utilizadores.');
      state.usersMenustamp = target;
      state.usersSupported = !!data.supported;
      state.usersRows = Array.isArray(data.rows) ? data.rows : [];
      if (els.usersSearch) els.usersSearch.value = '';
      renderUsersModal();
      usersModal?.show();
    } catch (error) {
      showToast(error.message || 'Erro ao carregar utilizadores.', 'error');
    }
  }

  async function saveUsersModal() {
    if (!state.usersMenustamp || !state.usersSupported) return;
    try {
      const res = await fetch(`/api/menu_manager/${encodeURIComponent(state.usersMenustamp)}/users/save`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ rows: state.usersRows }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok || data.error) throw new Error(data.error || 'Erro ao gravar acessos.');
      usersModal?.hide();
      const row = state.rows.find((item) => String(item.MENUSTAMP || '').trim() === state.usersMenustamp);
      if (row) {
        applyRowUpdate({
          ...row,
          USER_COUNT: Number(data.count || state.usersRows.filter((item) => item.consultar).length || 0),
        }, { select: state.selectedMenustamp === state.usersMenustamp });
      } else {
        renderList();
      }
      showToast('Acessos atualizados.', 'success');
    } catch (error) {
      showToast(error.message || 'Erro ao gravar acessos.', 'error');
    }
  }

  function bindEvents() {
    els.search?.addEventListener('input', () => {
      window.clearTimeout(state.listSearchTimer);
      state.listSearchTimer = window.setTimeout(() => loadList(), 180);
    });
    els.kindFilter?.addEventListener('change', () => loadList());
    els.btnNew?.addEventListener('click', () => openEditor(''));
    els.btnCancel?.addEventListener('click', () => editorModal?.hide());
    els.btnSave?.addEventListener('click', saveCurrent);
    els.btnDelete?.addEventListener('click', () => deleteMenu(state.selectedMenustamp));
    els.btnUp?.addEventListener('click', () => moveMenu(state.selectedMenustamp, 'up'));
    els.btnDown?.addEventListener('click', () => moveMenu(state.selectedMenustamp, 'down'));
    els.btnOpenModules?.addEventListener('click', () => openModulesModal(state.selectedMenustamp));
    els.btnOpenUsers?.addEventListener('click', () => openUsersModal(state.selectedMenustamp));
    els.btnIconPicker?.addEventListener('click', openIconsModal);
    els.fields.ICONE?.addEventListener('input', () => syncIconPreview(els.fields.ICONE?.value));
    els.fields.ICONE?.addEventListener('dblclick', openIconsModal);

    els.list?.addEventListener('click', (event) => {
      const actionNode = event.target.closest('[data-action]');
      if (!actionNode) return;
      const action = String(actionNode.getAttribute('data-action') || '').trim();
      const menustamp = String(actionNode.getAttribute('data-menustamp') || actionNode.closest('[data-menustamp]')?.getAttribute('data-menustamp') || '').trim();
      if (!action) return;
      event.preventDefault();
      if (action === 'edit') openEditor(menustamp);
      else if (action === 'pickIcon') openEditorAndIcons(menustamp);
      else if (action === 'modules') openModulesModal(menustamp);
      else if (action === 'users') openUsersModal(menustamp);
      else if (action === 'up') moveMenu(menustamp, 'up');
      else if (action === 'down') moveMenu(menustamp, 'down');
      else if (action === 'toggleInactive') toggleInactiveMenu(menustamp);
      else if (action === 'delete') deleteMenu(menustamp);
    });

    els.list?.addEventListener('dragstart', (event) => {
      const card = event.target.closest('.sz_menu_manager_card[data-menustamp]');
      if (!card || !permissions.edit) return;
      const menustamp = String(card.getAttribute('data-menustamp') || '').trim();
      if (!menustamp) return;
      state.dragMenustamp = menustamp;
      card.classList.add('is-dragging');
      if (event.dataTransfer) {
        event.dataTransfer.effectAllowed = 'move';
        event.dataTransfer.setData('text/plain', menustamp);
      }
    });

    els.list?.addEventListener('dragover', (event) => {
      const card = event.target.closest('.sz_menu_manager_card[data-menustamp]');
      if (!card || !state.dragMenustamp) return;
      const targetMenustamp = String(card.getAttribute('data-menustamp') || '').trim();
      if (!targetMenustamp || targetMenustamp === state.dragMenustamp) return;
      event.preventDefault();
      const rect = card.getBoundingClientRect();
      const placement = (event.clientY - rect.top) < (rect.height / 2) ? 'before' : 'after';
      state.dropMenustamp = targetMenustamp;
      state.dropPlacement = placement;
      applyDropIndicator(card, placement);
      if (event.dataTransfer) event.dataTransfer.dropEffect = 'move';
    });

    els.list?.addEventListener('drop', async (event) => {
      const card = event.target.closest('.sz_menu_manager_card[data-menustamp]');
      if (!card || !state.dragMenustamp) return;
      event.preventDefault();
      const targetMenustamp = String(card.getAttribute('data-menustamp') || '').trim();
      const placement = state.dropPlacement || 'after';
      if (!targetMenustamp || targetMenustamp === state.dragMenustamp) {
        clearDragState();
        return;
      }
      const previousRows = [...state.rows];
      const reordered = reorderRowsLocally(state.rows, state.dragMenustamp, targetMenustamp, placement);
      state.rows = reordered;
      state.selectedMenustamp = state.dragMenustamp;
      renderList();
      clearDragState();
      await saveReorderedRows(previousRows, reordered);
    });

    els.list?.addEventListener('dragend', () => {
      clearDragState();
    });

    els.modulesSearch?.addEventListener('input', renderModulesModal);
    els.modulesBody?.addEventListener('change', (event) => {
      const checkbox = event.target.closest('input[data-modstamp]');
      if (!checkbox) return;
      const modstamp = String(checkbox.getAttribute('data-modstamp') || '').trim();
      const row = state.modulesRows.find((item) => String(item.MODSTAMP || '').trim() === modstamp);
      if (row) row.SELECTED = checkbox.checked;
    });
    els.modulesSave?.addEventListener('click', saveModulesModal);

    els.usersSearch?.addEventListener('input', renderUsersModal);
    els.usersBody?.addEventListener('change', (event) => {
      const checkbox = event.target.closest('input[data-field]');
      const rowEl = event.target.closest('tr[data-login]');
      if (!checkbox || !rowEl) return;
      const login = String(rowEl.getAttribute('data-login') || '').trim();
      const field = String(checkbox.getAttribute('data-field') || '').trim();
      const row = state.usersRows.find((item) => String(item.utilizador || '').trim() === login);
      if (!row || !field) return;
      row[field] = checkbox.checked ? 1 : 0;
      if (field !== 'consultar' && row[field]) row.consultar = 1;
      if (field === 'consultar' && !row.consultar) {
        row.inserir = 0;
        row.editar = 0;
        row.eliminar = 0;
      }
      renderUsersModal();
    });
    els.usersSave?.addEventListener('click', saveUsersModal);

    els.iconsSearch?.addEventListener('input', renderIconsModal);
    els.iconsGrid?.addEventListener('click', (event) => {
      const button = event.target.closest('[data-icon]');
      if (!button) return;
      const icon = String(button.getAttribute('data-icon') || '').trim();
      if (!icon) return;
      if (els.fields.ICONE) els.fields.ICONE.value = icon;
      syncIconPreview(icon);
      renderIconsModal();
      iconsModal?.hide();
    });
  }

  bindEvents();
  loadList();
})();
