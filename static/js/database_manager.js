document.addEventListener('DOMContentLoaded', () => {
  const cfg = window.DATABASE_MANAGER_CONFIG || {};
  const els = {
    subtitle: document.getElementById('dbmSubtitle'),
    tableSearch: document.getElementById('dbmTableSearch'),
    refreshBtn: document.getElementById('dbmRefreshBtn'),
    actionRefreshBtn: document.getElementById('dbmActionRefreshBtn'),
    backBtn: document.getElementById('dbmBackBtn'),
    sortTablesBtn: document.getElementById('dbmSortTablesBtn'),
    sortModal: document.getElementById('dbmSortModal'),
    sortModalClose: document.getElementById('dbmSortModalClose'),
    sortModalCloseTop: document.getElementById('dbmSortModalCloseTop'),
    sortApply: document.getElementById('dbmSortApply'),
    sortOptionList: document.getElementById('dbmSortOptionList'),
    tablesMeta: document.getElementById('dbmTablesMeta'),
    tablesList: document.getElementById('dbmTablesList'),
    columnsMeta: document.getElementById('dbmColumnsMeta'),
    columnsList: document.getElementById('dbmColumnsList'),
    detailMeta: document.getElementById('dbmDetailMeta'),
    detailContent: document.getElementById('dbmDetailContent'),
    status: document.getElementById('dbmStatus'),
  };

  const state = {
    tables: [],
    detail: null,
    selectedTable: String(cfg.initialTableKey || '').trim(),
    loading: false,
    search: '',
    sortField: 'name',
    sortDir: 1,
    pendingSortField: 'name',
    pendingSortDir: 1,
  };

  function escapeHtml(value) {
    return String(value == null ? '' : value)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function formatInt(value) {
    return new Intl.NumberFormat('pt-PT').format(Number(value || 0));
  }

  function formatDecimal(value, digits = 2) {
    return new Intl.NumberFormat('pt-PT', {
      minimumFractionDigits: digits,
      maximumFractionDigits: digits,
    }).format(Number(value || 0));
  }

  function formatDateTime(value) {
    if (!value) return 'n/a';
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return String(value);
    return new Intl.DateTimeFormat('pt-PT', {
      dateStyle: 'short',
      timeStyle: 'short',
    }).format(date);
  }

  function setStatus(message, isError = false) {
    if (!els.status) return;
    els.status.textContent = message || '';
    els.status.style.color = isError ? 'var(--sz-color-danger)' : '';
  }

  function currentTableLabel() {
    const summary = state.detail?.summary || null;
    return summary ? `${summary.schema}.${summary.name}` : '';
  }

  function filteredTables() {
    const term = state.search.trim().toUpperCase();
    const items = !term ? state.tables.slice() : state.tables.filter((table) => {
      const label = `${table.schema}.${table.name}`.toUpperCase();
      return label.includes(term);
    });
    return items.sort(compareTables);
  }

  function compareTables(left, right) {
    const field = String(state.sortField || 'name').trim();
    const direction = Number(state.sortDir || 1) >= 0 ? 1 : -1;
    let result = 0;
    switch (field) {
      case 'row_count':
        result = (Number(left?.row_count || 0) - Number(right?.row_count || 0));
        break;
      case 'reserved_mb':
        result = (Number(left?.reserved_mb || 0) - Number(right?.reserved_mb || 0));
        break;
      case 'name':
      default:
        result = String(left?.name || '').localeCompare(String(right?.name || ''), 'pt', {
          sensitivity: 'base',
          numeric: true,
        });
        break;
    }
    if (result === 0) {
      result = String(left?.key || '').localeCompare(String(right?.key || ''), 'pt', {
        sensitivity: 'base',
        numeric: true,
      });
    }
    return result * direction;
  }

  function fragClass(value) {
    const numeric = Number(value);
    if (!Number.isFinite(numeric)) return '';
    if (numeric >= 30) return 'dbm-frag-bad';
    if (numeric >= 10) return 'dbm-frag-warn';
    return 'dbm-frag-good';
  }

  function updateUrl(tableKey) {
    const url = new URL(window.location.href);
    if (tableKey) {
      url.searchParams.set('table', tableKey);
    } else {
      url.searchParams.delete('table');
    }
    window.history.replaceState({}, '', url.toString());
  }

  function renderSortOptions() {
    if (!els.sortOptionList) return;
    const options = [
      { field: 'name', label: 'Nome', hint: 'Nome da tabela' },
      { field: 'row_count', label: 'Número de registos', hint: 'Total de registos' },
      { field: 'reserved_mb', label: 'Espaço ocupado', hint: 'Espaço reservado em MB' },
    ];
    els.sortOptionList.innerHTML = options.map((option) => {
      const active = option.field === String(state.pendingSortField || '');
      const direction = active && Number(state.pendingSortDir || 1) < 0 ? 'DESC' : 'ASC';
      const icon = active
        ? (direction === 'DESC' ? 'fa-arrow-down-wide-short' : 'fa-arrow-up-short-wide')
        : 'fa-minus';
      return `
        <button type="button" class="sz_button sz_button_ghost dbm-sort-option${active ? ' is-active' : ''}" data-db-sort-field="${escapeHtml(option.field)}">
          <span class="dbm-sort-option-main">
            <span class="dbm-sort-option-label">${escapeHtml(option.label)}</span>
            <span class="dbm-sort-option-hint">${escapeHtml(active ? `Ordenação ${direction}` : option.hint)}</span>
          </span>
          <span class="dbm-sort-option-state" aria-hidden="true">
            <i class="fa-solid ${icon}"></i>
          </span>
        </button>
      `;
    }).join('');
  }

  function openSortModal() {
    if (!els.sortModal) return;
    state.pendingSortField = state.sortField;
    state.pendingSortDir = state.sortDir;
    renderSortOptions();
    document.body.classList.add('modal-sort-open');
    els.sortModal.classList.add('sz_is_open');
    els.sortModal.setAttribute('aria-hidden', 'false');
  }

  function closeSortModal() {
    if (!els.sortModal) return;
    els.sortModal.classList.remove('sz_is_open');
    els.sortModal.setAttribute('aria-hidden', 'true');
    document.body.classList.remove('modal-sort-open');
  }

  function renderTables() {
    const tables = filteredTables();
    if (els.tablesMeta) {
      els.tablesMeta.textContent = `${formatInt(tables.length)} de ${formatInt(state.tables.length)} tabelas`;
    }
    if (!tables.length) {
      els.tablesList.innerHTML = '<div class="dbm-empty">Nenhuma tabela corresponde à pesquisa.</div>';
      return;
    }

    els.tablesList.innerHTML = tables.map((table) => `
      <button type="button" class="dbm-table-item ${table.key === state.selectedTable ? 'is-active' : ''}" data-db-table="${escapeHtml(table.key)}">
        <div class="dbm-table-item-top">
          <div class="dbm-table-heading">
            <div class="dbm-table-name">${escapeHtml(table.name)}</div>
            <span class="dbm-table-schema-flag">${escapeHtml(table.schema)}</span>
          </div>
          <span class="dbm-badge is-primary">${formatInt(table.row_count)}</span>
        </div>
        <div class="dbm-table-meta">
          <span>${formatInt(table.column_count)} campos</span>
          <span>${formatInt(table.index_count)} índices</span>
          <span>${formatDecimal(table.reserved_mb)} MB</span>
        </div>
      </button>
    `).join('');
  }

  function renderColumns() {
    const columns = Array.isArray(state.detail?.columns) ? state.detail.columns : [];
    if (els.columnsMeta) {
      els.columnsMeta.textContent = columns.length
        ? `${formatInt(columns.length)} campos em ${currentTableLabel()}`
        : 'Sem campos para apresentar.';
    }
    if (!columns.length) {
      els.columnsList.innerHTML = '<div class="dbm-empty">Seleciona uma tabela para ver os campos.</div>';
      return;
    }

    els.columnsList.innerHTML = columns.map((column) => {
      const badges = [];
      if (column.is_primary_key) badges.push('<span class="dbm-badge is-primary">PK</span>');
      if (column.is_foreign_key) badges.push('<span class="dbm-badge is-warning">FK</span>');
      if (column.is_identity) badges.push('<span class="dbm-badge is-success">IDENTITY</span>');
      if (column.is_computed) badges.push('<span class="dbm-badge is-danger">COMPUTED</span>');
      badges.push(`<span class="dbm-badge">${column.is_nullable ? 'NULL' : 'NOT NULL'}</span>`);

      const meta = [];
      if (column.default_definition) {
        meta.push(`<div><strong>Default:</strong> <span class="dbm-inline-code">${escapeHtml(column.default_definition)}</span></div>`);
      }
      if (column.reference_target) {
        meta.push(`<div><strong>Ref:</strong> ${escapeHtml(column.reference_target)}</div>`);
      }
      if (column.collation_name) {
        meta.push(`<div><strong>Collation:</strong> ${escapeHtml(column.collation_name)}</div>`);
      }
      if (column.is_identity && column.identity_seed != null && column.identity_increment != null) {
        meta.push(`<div><strong>Identity:</strong> seed ${escapeHtml(column.identity_seed)} / inc ${escapeHtml(column.identity_increment)}</div>`);
      }

      return `
        <article class="dbm-column-item">
          <div class="dbm-column-item-head">
            <code class="dbm-code">${escapeHtml(column.name)}</code>
            <div class="dbm-type">${escapeHtml(column.type_label)}</div>
          </div>
          <div class="dbm-badges">${badges.join('')}</div>
          <div class="dbm-column-meta">
            <div><strong>Ordem:</strong> ${formatInt(column.ordinal)}</div>
            ${meta.join('')}
          </div>
        </article>
      `;
    }).join('');
  }

  function renderSummaryCards(summary) {
    const cards = [
      ['Registos', formatInt(summary.row_count)],
      ['Campos', formatInt(summary.column_count)],
      ['Índices', formatInt(summary.index_count)],
      ['Triggers', formatInt(summary.trigger_count)],
      ['Reservado', `${formatDecimal(summary.reserved_mb)} MB`],
      ['Fragmentação média', summary.average_fragmentation_pct == null ? 'n/a' : `${formatDecimal(summary.average_fragmentation_pct)}%`, fragClass(summary.average_fragmentation_pct)],
    ];
    return cards.map(([label, value, extraClass]) => `
      <article class="dbm-metric-card">
        <div class="dbm-metric-label">${escapeHtml(label)}</div>
        <div class="dbm-metric-value ${extraClass || ''}">${escapeHtml(value)}</div>
      </article>
    `).join('');
  }

  function renderKeyValues(summary) {
    const primaryKey = Array.isArray(summary.primary_key_columns) && summary.primary_key_columns.length
      ? summary.primary_key_columns.join(', ')
      : 'Sem PK';
    return `
      <dl class="dbm-kv">
        <dt>Tabela</dt>
        <dd><span class="dbm-inline-code">${escapeHtml(summary.schema)}.${escapeHtml(summary.name)}</span></dd>
        <dt>PK</dt>
        <dd>${escapeHtml(primaryKey)}</dd>
        <dt>Dados</dt>
        <dd>${formatDecimal(summary.data_mb)} MB</dd>
        <dt>Índices</dt>
        <dd>${formatDecimal(summary.index_mb)} MB</dd>
        <dt>Não usado</dt>
        <dd>${formatDecimal(summary.unused_mb)} MB</dd>
        <dt>FK saída</dt>
        <dd>${formatInt(summary.foreign_key_count)}</dd>
        <dt>FK entrada</dt>
        <dd>${formatInt(summary.incoming_foreign_key_count)}</dd>
        <dt>Identity</dt>
        <dd>${formatInt(summary.identity_count)}</dd>
        <dt>Computed</dt>
        <dd>${formatInt(summary.computed_count)}</dd>
        <dt>Defaults</dt>
        <dd>${formatInt(summary.default_count)}</dd>
        <dt>Escalação lock</dt>
        <dd>${escapeHtml(summary.lock_escalation || 'n/a')}</dd>
        <dt>Temporal</dt>
        <dd>${escapeHtml(summary.temporal_type || 'n/a')}</dd>
        <dt>Criada</dt>
        <dd>${escapeHtml(formatDateTime(summary.created_at))}</dd>
        <dt>Alterada</dt>
        <dd>${escapeHtml(formatDateTime(summary.modified_at))}</dd>
      </dl>
    `;
  }

  function renderForeignKeys(foreignKeys) {
    if (!foreignKeys.length) {
      return '<div class="dbm-empty">Sem foreign keys definidas nesta tabela.</div>';
    }
    return foreignKeys.map((item) => `
      <div class="dbm-list-row">
        <div class="dbm-list-row-head">
          <div class="dbm-list-row-title">${escapeHtml(item.name)}</div>
          ${item.is_disabled ? '<span class="dbm-badge is-danger">Disabled</span>' : '<span class="dbm-badge is-success">Ativa</span>'}
        </div>
        <div class="dbm-list-row-meta"><strong>Campos:</strong> ${escapeHtml(item.columns || '-')}</div>
        <div class="dbm-list-row-meta"><strong>Ref:</strong> ${escapeHtml(item.references || '-')}</div>
        <div class="dbm-list-row-sub">Delete: ${escapeHtml(item.delete_action || 'NO_ACTION')} | Update: ${escapeHtml(item.update_action || 'NO_ACTION')}</div>
      </div>
    `).join('');
  }

  function renderIndexes(indexes) {
    if (!indexes.length) {
      return '<div class="dbm-empty">Sem índices utilizáveis para apresentar.</div>';
    }
    return indexes.map((item) => `
      <div class="dbm-list-row">
        <div class="dbm-list-row-head">
          <div class="dbm-list-row-title">${escapeHtml(item.name || `(index ${item.id})`)}</div>
          <div class="dbm-inline-list">
            ${item.is_primary_key ? '<span class="dbm-badge is-primary">PK</span>' : ''}
            ${item.is_unique ? '<span class="dbm-badge is-success">UNIQUE</span>' : ''}
            ${item.is_disabled ? '<span class="dbm-badge is-danger">Disabled</span>' : ''}
          </div>
        </div>
        <div class="dbm-list-row-meta"><strong>Tipo:</strong> ${escapeHtml(item.type || '-')}</div>
        <div class="dbm-list-row-meta"><strong>Key:</strong> ${escapeHtml(item.key_columns || '-')}</div>
        ${item.included_columns ? `<div class="dbm-list-row-meta"><strong>Included:</strong> ${escapeHtml(item.included_columns)}</div>` : ''}
        <div class="dbm-list-row-sub">
          Registos ${formatInt(item.row_count)} | Fill factor ${formatInt(item.fill_factor)}
          ${item.fragmentation_pct != null ? ` | Frag <span class="${fragClass(item.fragmentation_pct)}">${formatDecimal(item.fragmentation_pct)}%</span>` : ''}
        </div>
        ${item.filter_definition ? `<div class="dbm-list-row-sub"><span class="dbm-inline-code">${escapeHtml(item.filter_definition)}</span></div>` : ''}
      </div>
    `).join('');
  }

  function renderTriggers(triggers) {
    if (!triggers.length) {
      return '<div class="dbm-empty">Sem triggers nesta tabela.</div>';
    }
    return triggers.map((item) => `
      <div class="dbm-list-row">
        <div class="dbm-list-row-head">
          <div class="dbm-list-row-title">${escapeHtml(item.name)}</div>
          <div class="dbm-inline-list">
            ${item.is_instead_of_trigger ? '<span class="dbm-badge is-warning">INSTEAD OF</span>' : '<span class="dbm-badge">AFTER</span>'}
            ${item.is_disabled ? '<span class="dbm-badge is-danger">Disabled</span>' : '<span class="dbm-badge is-success">Ativa</span>'}
          </div>
        </div>
        <div class="dbm-list-row-meta"><strong>Eventos:</strong> ${escapeHtml(item.events || '-')}</div>
        ${item.definition_preview ? `<div class="dbm-list-row-sub"><span class="dbm-inline-code">${escapeHtml(item.definition_preview)}</span></div>` : ''}
      </div>
    `).join('');
  }

  function renderDetail() {
    const summary = state.detail?.summary || null;
    if (!summary) {
      els.detailMeta.textContent = 'Estado e metadados da tabela.';
      els.detailContent.innerHTML = '<div class="dbm-empty">Seleciona uma tabela para ver o detalhe.</div>';
      return;
    }

    els.detailMeta.textContent = `${summary.schema}.${summary.name}`;
    els.subtitle.textContent = `Explora ${summary.schema}.${summary.name}, respetivos campos, chaves, índices, triggers e indicadores físicos.`;
    els.detailContent.innerHTML = `
      <div class="dbm-detail-stack">
        <section class="dbm-section-card">
          <div class="dbm-metric-grid">
            ${renderSummaryCards(summary)}
          </div>
        </section>
        <section class="dbm-section-card">
          <div class="dbm-section-head">
            <h3 class="dbm-section-title">Estado da Tabela</h3>
          </div>
          ${renderKeyValues(summary)}
        </section>
        <section class="dbm-section-card">
          <div class="dbm-section-head">
            <h3 class="dbm-section-title">Chaves</h3>
            <span class="dbm-badge">${formatInt(state.detail.foreign_keys.length)}</span>
          </div>
          <div class="dbm-section-list">
            ${renderForeignKeys(state.detail.foreign_keys)}
          </div>
        </section>
        <section class="dbm-section-card">
          <div class="dbm-section-head">
            <h3 class="dbm-section-title">Índices</h3>
            <span class="dbm-badge">${formatInt(state.detail.indexes.length)}</span>
          </div>
          <div class="dbm-section-list">
            ${renderIndexes(state.detail.indexes)}
          </div>
        </section>
        <section class="dbm-section-card">
          <div class="dbm-section-head">
            <h3 class="dbm-section-title">Triggers</h3>
            <span class="dbm-badge">${formatInt(state.detail.triggers.length)}</span>
          </div>
          <div class="dbm-section-list">
            ${renderTriggers(state.detail.triggers)}
          </div>
        </section>
      </div>
    `;
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

  async function loadBootstrap() {
    state.loading = true;
    setStatus('A carregar metadata da base de dados...');
    try {
      const params = new URLSearchParams();
      if (state.selectedTable) params.set('table', state.selectedTable);
      const data = await fetchJson(`/api/database_manager/bootstrap?${params.toString()}`);
      state.tables = Array.isArray(data.tables) ? data.tables : [];
      state.selectedTable = String(data.selected_table || '').trim();
      state.detail = data.detail || null;
      renderTables();
      renderColumns();
      renderDetail();
      updateUrl(state.selectedTable);
      setStatus(`${formatInt(state.tables.length)} tabelas carregadas.`);
    } catch (error) {
      els.tablesList.innerHTML = `<div class="dbm-empty">${escapeHtml(error.message || 'Erro ao carregar tabelas.')}</div>`;
      els.columnsList.innerHTML = '<div class="dbm-empty">Sem dados.</div>';
      els.detailContent.innerHTML = '<div class="dbm-empty">Sem detalhe.</div>';
      setStatus(error.message || 'Erro ao carregar metadata.', true);
    } finally {
      state.loading = false;
    }
  }

  async function loadTableDetail(tableKey) {
    if (!tableKey) return;
    state.loading = true;
    state.selectedTable = tableKey;
    renderTables();
    setStatus(`A carregar ${tableKey}...`);
    try {
      const detail = await fetchJson(`/api/database_manager/table?table=${encodeURIComponent(tableKey)}`);
      state.detail = detail;
      renderColumns();
      renderDetail();
      updateUrl(tableKey);
      setStatus(`Tabela ${tableKey} carregada.`);
    } catch (error) {
      setStatus(error.message || 'Erro ao carregar tabela.', true);
    } finally {
      state.loading = false;
    }
  }

  els.tableSearch?.addEventListener('input', (event) => {
    state.search = String(event.target.value || '');
    renderTables();
  });

  if (els.sortModal) {
    document.body.appendChild(els.sortModal);
  }

  els.sortTablesBtn?.addEventListener('click', openSortModal);
  els.sortModalClose?.addEventListener('click', closeSortModal);
  els.sortModalCloseTop?.addEventListener('click', closeSortModal);
  els.sortModal?.addEventListener('click', (event) => {
    if (event.target === els.sortModal) {
      closeSortModal();
    }
  });
  els.sortOptionList?.addEventListener('click', (event) => {
    const option = event.target.closest('[data-db-sort-field]');
    if (!option) return;
    const nextField = String(option.dataset.dbSortField || '').trim();
    if (!nextField) return;
    if (state.pendingSortField === nextField) {
      state.pendingSortDir = Number(state.pendingSortDir || 1) * -1;
    } else {
      state.pendingSortField = nextField;
      state.pendingSortDir = 1;
    }
    renderSortOptions();
  });
  els.sortApply?.addEventListener('click', () => {
    state.sortField = String(state.pendingSortField || 'name');
    state.sortDir = Number(state.pendingSortDir || 1) >= 0 ? 1 : -1;
    renderTables();
    closeSortModal();
  });
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && els.sortModal?.classList.contains('sz_is_open')) {
      closeSortModal();
    }
  });

  els.tablesList?.addEventListener('click', (event) => {
    const trigger = event.target.closest('[data-db-table]');
    if (!trigger || state.loading) return;
    const tableKey = String(trigger.dataset.dbTable || '').trim();
    if (!tableKey || tableKey === state.selectedTable) return;
    loadTableDetail(tableKey);
  });

  function refreshCurrent() {
    loadBootstrap();
  }

  els.refreshBtn?.addEventListener('click', refreshCurrent);
  els.actionRefreshBtn?.addEventListener('click', refreshCurrent);
  els.backBtn?.addEventListener('click', () => {
    window.history.back();
  });

  loadBootstrap();
});
