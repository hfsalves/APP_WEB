document.addEventListener('DOMContentLoaded', () => {
  const cfg = window.DATABASE_MANAGER_CONFIG || {};
  const els = {
    subtitle: document.getElementById('dbmSubtitle'),
    repoMeta: document.getElementById('dbmRepoMeta'),
    tableSearch: document.getElementById('dbmTableSearch'),
    refreshBtn: document.getElementById('dbmRefreshBtn'),
    syncSchemaBtn: document.getElementById('dbmSyncSchemaBtn'),
    actionRefreshBtn: document.getElementById('dbmActionRefreshBtn'),
    backBtn: document.getElementById('dbmBackBtn'),
    sortTablesBtn: document.getElementById('dbmSortTablesBtn'),
    sortModal: document.getElementById('dbmSortModal'),
    sortModalClose: document.getElementById('dbmSortModalClose'),
    sortModalCloseTop: document.getElementById('dbmSortModalCloseTop'),
    sortApply: document.getElementById('dbmSortApply'),
    sortOptionList: document.getElementById('dbmSortOptionList'),
    indexMaintModal: document.getElementById('dbmIndexMaintModal'),
    indexMaintClose: document.getElementById('dbmIndexMaintClose'),
    indexMaintCloseTop: document.getElementById('dbmIndexMaintCloseTop'),
    indexMaintStart: document.getElementById('dbmIndexMaintStart'),
    indexMaintTableLabel: document.getElementById('dbmIndexMaintTableLabel'),
    indexMaintModeList: document.getElementById('dbmIndexMaintModeList'),
    indexMaintPlanMeta: document.getElementById('dbmIndexMaintPlanMeta'),
    indexMaintPlanList: document.getElementById('dbmIndexMaintPlanList'),
    indexMaintRunState: document.getElementById('dbmIndexMaintRunState'),
    indexMaintJobSummary: document.getElementById('dbmIndexMaintJobSummary'),
    indexMaintJobItems: document.getElementById('dbmIndexMaintJobItems'),
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
    indexMaintMode: 'auto',
    pendingIndexMaintMode: 'auto',
    indexMaintJobId: '',
    indexMaintJobPayload: null,
    indexMaintPollTimer: null,
    schemaRepository: {
      state: null,
      warning: '',
    },
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

  function renderSchemaRepositoryState() {
    if (!els.repoMeta) return;
    const repo = state.schemaRepository || {};
    const info = repo.state || null;
    const warning = String(repo.warning || '').trim();

    els.repoMeta.classList.toggle('is-error', !!warning || String(info?.last_sync_status || '').trim().toLowerCase() === 'error');

    if (!info) {
      els.repoMeta.textContent = warning || 'Repositorio de estrutura indisponivel.';
      return;
    }

    const counts = info.counts || {};
    const scopeLabel = info.is_development_source ? 'DEV SOURCE' : 'TARGET DB';
    const databaseLabel = String(info.database_name || '').trim() || 'DB';
    const syncLabel = info.last_sync_at
      ? `Sync ${formatDateTime(info.last_sync_at)}`
      : 'Sem sync';
    const sourceLabel = info.last_sync_source
      ? `via ${String(info.last_sync_source).toUpperCase()}`
      : 'sem origem';
    const byLabel = info.last_sync_requested_by ? `por ${info.last_sync_requested_by}` : '';
    const countLabel = `${formatInt(counts.table_count)} tabelas, ${formatInt(counts.column_count)} campos, ${formatInt(counts.index_count)} indices`;
    const messageLabel = warning || info.last_sync_message || '';

    els.repoMeta.textContent = [
      `Repositorio: ${scopeLabel}`,
      databaseLabel,
      syncLabel,
      sourceLabel,
      byLabel,
      countLabel,
      messageLabel,
    ].filter(Boolean).join(' | ');
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

  function closeIndexMaintPoll() {
    if (!state.indexMaintPollTimer) return;
    window.clearInterval(state.indexMaintPollTimer);
    state.indexMaintPollTimer = null;
  }

  function normalizeIndexMaintMode(value) {
    const mode = String(value || '').trim().toLowerCase();
    return ['auto', 'reorganize', 'rebuild'].includes(mode) ? mode : 'auto';
  }

  function indexMaintStateBadgeClass(value) {
    switch (String(value || '').trim().toLowerCase()) {
      case 'running':
        return 'dbm-badge is-primary';
      case 'done':
        return 'dbm-badge is-success';
      case 'error':
        return 'dbm-badge is-danger';
      case 'skipped':
        return 'dbm-badge is-warning';
      default:
        return 'dbm-badge';
    }
  }

  function computeIndexMaintPlanItem(index, mode) {
    const requestedMode = normalizeIndexMaintMode(mode);
    const typeName = String(index?.type || '').trim().toUpperCase();
    const indexName = String(index?.name || '').trim();
    const pageCount = Number(index?.page_count || 0);
    const fragmentation = index?.fragmentation_pct == null ? null : Number(index.fragmentation_pct);
    const allowPageLocks = !!index?.allow_page_locks;
    const isDisabled = !!index?.is_disabled;
    let plannedAction = '';
    let stateValue = 'pending';
    let message = '';

    if (!indexName) {
      stateValue = 'skipped';
      message = 'Índice sem nome.';
    } else if (isDisabled) {
      stateValue = 'skipped';
      message = 'Índice desativado.';
    } else if (!['CLUSTERED', 'NONCLUSTERED'].includes(typeName)) {
      stateValue = 'skipped';
      message = `Tipo não suportado: ${typeName || 'n/a'}.`;
    } else if (pageCount <= 0) {
      stateValue = 'skipped';
      message = 'Sem páginas para otimizar.';
    } else if (requestedMode === 'rebuild') {
      plannedAction = 'REBUILD';
      message = 'REBUILD forçado.';
    } else if (requestedMode === 'reorganize') {
      if (!allowPageLocks) {
        stateValue = 'skipped';
        message = 'REORGANIZE requer ALLOW_PAGE_LOCKS = ON.';
      } else {
        plannedAction = 'REORGANIZE';
        message = 'REORGANIZE forçado.';
      }
    } else if (fragmentation == null || Number.isNaN(fragmentation)) {
      stateValue = 'skipped';
      message = 'Sem métricas de fragmentação.';
    } else if (pageCount < 1000) {
      stateValue = 'skipped';
      message = 'Abaixo do limiar mínimo de páginas (1000).';
    } else if (fragmentation < 10) {
      stateValue = 'skipped';
      message = 'Fragmentação abaixo de 10%.';
    } else if (fragmentation >= 30) {
      plannedAction = 'REBUILD';
      message = `Auto: REBUILD com fragmentação ${formatDecimal(fragmentation)}%.`;
    } else if (!allowPageLocks) {
      plannedAction = 'REBUILD';
      message = 'Auto: fallback para REBUILD porque ALLOW_PAGE_LOCKS = OFF.';
    } else {
      plannedAction = 'REORGANIZE';
      message = `Auto: REORGANIZE com fragmentação ${formatDecimal(fragmentation)}%.`;
    }

    return {
      index_id: Number(index?.id || 0),
      index_name: indexName,
      index_type: typeName,
      fragmentation_pct: fragmentation == null || Number.isNaN(fragmentation) ? null : fragmentation,
      page_count: pageCount,
      planned_action: plannedAction,
      state: stateValue,
      message,
    };
  }

  function buildIndexMaintPlan(mode) {
    const indexes = Array.isArray(state.detail?.indexes) ? state.detail.indexes : [];
    return indexes.map((index, idx) => ({
      seq_no: idx + 1,
      ...computeIndexMaintPlanItem(index, mode),
    }));
  }

  function renderIndexMaintModeOptions() {
    if (!els.indexMaintModeList) return;
    const options = [
      { field: 'auto', label: 'Auto', hint: 'Reorganize >10% e Rebuild >30%' },
      { field: 'reorganize', label: 'Reorganize', hint: 'Força REORGANIZE nos elegíveis' },
      { field: 'rebuild', label: 'Rebuild', hint: 'Força REBUILD nos elegíveis' },
    ];
    els.indexMaintModeList.innerHTML = options.map((option) => {
      const active = option.field === String(state.pendingIndexMaintMode || '');
      return `
        <button type="button" class="sz_button sz_button_ghost dbm-sort-option${active ? ' is-active' : ''}" data-db-index-maint-mode="${escapeHtml(option.field)}">
          <span class="dbm-sort-option-main">
            <span class="dbm-sort-option-label">${escapeHtml(option.label)}</span>
            <span class="dbm-sort-option-hint">${escapeHtml(option.hint)}</span>
          </span>
          <span class="dbm-sort-option-state" aria-hidden="true">
            <i class="fa-solid ${active ? 'fa-check' : 'fa-minus'}"></i>
          </span>
        </button>
      `;
    }).join('');
  }

  function renderIndexMaintPlan() {
    if (!els.indexMaintPlanList || !els.indexMaintPlanMeta) return;
    const plan = buildIndexMaintPlan(state.pendingIndexMaintMode);
    const actionable = plan.filter((item) => item.planned_action);
    els.indexMaintPlanMeta.textContent = `${formatInt(actionable.length)} / ${formatInt(plan.length)}`;
    if (!plan.length) {
      els.indexMaintPlanList.innerHTML = '<div class="dbm-empty">Sem índices na tabela selecionada.</div>';
      if (els.indexMaintStart) els.indexMaintStart.disabled = true;
      return;
    }

    els.indexMaintPlanList.innerHTML = plan.map((item) => `
      <div class="dbm-maint-plan-row ${item.planned_action ? 'is-actionable' : 'is-skipped'}">
        <div class="dbm-maint-plan-head">
          <div class="dbm-maint-plan-title">${escapeHtml(item.index_name || `(index ${item.index_id})`)}</div>
          <span class="${indexMaintStateBadgeClass(item.planned_action ? item.planned_action.toLowerCase() : 'skipped')}">${escapeHtml(item.planned_action || 'Ignorar')}</span>
        </div>
        <div class="dbm-maint-plan-meta">
          ${escapeHtml(item.index_type || 'n/a')} | ${item.fragmentation_pct == null ? 'Frag n/a' : `Frag ${formatDecimal(item.fragmentation_pct)}%`} | ${formatInt(item.page_count)} páginas
        </div>
        <div class="dbm-maint-plan-meta">${escapeHtml(item.message || '')}</div>
      </div>
    `).join('');
    if (els.indexMaintStart) {
      els.indexMaintStart.disabled = actionable.length <= 0;
    }
  }

  function renderIndexMaintJob(payload) {
    state.indexMaintJobPayload = payload || null;
    const job = payload?.job || null;
    const items = Array.isArray(payload?.items) ? payload.items : [];
    const running = ['running', 'stopping'].includes(String(job?.state || '').trim().toLowerCase());

    if (els.indexMaintRunState) {
      if (!job) {
        els.indexMaintRunState.className = 'dbm-badge';
        els.indexMaintRunState.textContent = 'Inativa';
      } else {
        els.indexMaintRunState.className = indexMaintStateBadgeClass(job.state);
        els.indexMaintRunState.textContent = String(job.state || 'n/a').toUpperCase();
      }
    }

    if (els.indexMaintJobSummary) {
      if (!job) {
        els.indexMaintJobSummary.textContent = 'Sem job em execução.';
      } else {
        els.indexMaintJobSummary.textContent =
          `${formatInt(job.processed)} / ${formatInt(job.total)} processados | ${formatInt(job.executed)} executados | ${formatInt(job.skipped)} ignorados | ${formatInt(job.errors)} erros${job.message ? ` | ${job.message}` : ''}`;
      }
    }

    if (!els.indexMaintJobItems) return;
    if (!job) {
      els.indexMaintJobItems.innerHTML = '<div class="dbm-empty">Ainda não existe execução para esta tabela.</div>';
      if (els.indexMaintStart) {
        renderIndexMaintPlan();
      }
      return;
    }
    els.indexMaintJobItems.innerHTML = items.map((item) => `
      <div class="dbm-maint-job-row is-${escapeHtml(item.state || 'pending')}">
        <div class="dbm-maint-job-head">
          <div class="dbm-maint-job-title">${escapeHtml(item.index_name || `(index ${item.index_id})`)}</div>
          <span class="${indexMaintStateBadgeClass(item.state)}">${escapeHtml(item.executed_action || item.planned_action || item.state || 'n/a')}</span>
        </div>
        <div class="dbm-maint-job-meta">
          ${escapeHtml(item.index_type || 'n/a')} | ${item.fragmentation_pct == null ? 'Frag n/a' : `Frag ${formatDecimal(item.fragmentation_pct)}%`} | ${formatInt(item.page_count)} páginas
        </div>
        <div class="dbm-maint-job-meta">${escapeHtml(item.message || '')}</div>
      </div>
    `).join('') || '<div class="dbm-empty">Sem itens registados.</div>';
    if (els.indexMaintStart) {
      if (running) {
        els.indexMaintStart.disabled = true;
      } else {
        renderIndexMaintPlan();
      }
    }
  }

  async function loadIndexMaintStatus(params) {
    const query = new URLSearchParams(params || {});
    const payload = await fetchJson(`/api/database_manager/index_maintenance/status?${query.toString()}`);
    state.indexMaintJobId = String(payload?.job?.job_id || '').trim();
    renderIndexMaintJob(payload);
    return payload;
  }

  async function pollIndexMaintStatus(jobId) {
    if (!jobId) return;
    try {
      const payload = await loadIndexMaintStatus({ job_id: jobId });
      const stateValue = String(payload?.job?.state || '').trim().toLowerCase();
      if (!['running', 'stopping'].includes(stateValue)) {
        closeIndexMaintPoll();
        if (state.selectedTable) {
          loadTableDetail(state.selectedTable);
        }
      }
    } catch (error) {
      closeIndexMaintPoll();
      setStatus(error.message || 'Erro ao consultar o job de manutenção.', true);
    }
  }

  function startIndexMaintPoll(jobId) {
    closeIndexMaintPoll();
    if (!jobId) return;
    state.indexMaintPollTimer = window.setInterval(() => {
      pollIndexMaintStatus(jobId);
    }, 2000);
  }

  async function openIndexMaintModal() {
    if (!els.indexMaintModal) return;
    state.pendingIndexMaintMode = normalizeIndexMaintMode(state.indexMaintMode);
    if (els.indexMaintTableLabel) {
      els.indexMaintTableLabel.textContent = currentTableLabel() || 'Seleciona uma tabela.';
    }
    renderIndexMaintModeOptions();
    renderIndexMaintPlan();
    renderIndexMaintJob(null);
    document.body.classList.add('modal-db-index-maint-open');
    els.indexMaintModal.classList.add('sz_is_open');
    els.indexMaintModal.setAttribute('aria-hidden', 'false');
    if (currentTableLabel()) {
      try {
        const payload = await loadIndexMaintStatus({ table: currentTableLabel() });
        const currentState = String(payload?.job?.state || '').trim().toLowerCase();
        if (state.indexMaintJobId && ['running', 'stopping'].includes(currentState)) {
          startIndexMaintPoll(state.indexMaintJobId);
        }
      } catch (error) {
        renderIndexMaintJob(null);
      }
    }
  }

  function closeIndexMaintModal() {
    if (!els.indexMaintModal) return;
    closeIndexMaintPoll();
    els.indexMaintModal.classList.remove('sz_is_open');
    els.indexMaintModal.setAttribute('aria-hidden', 'true');
    document.body.classList.remove('modal-db-index-maint-open');
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
            <div class="dbm-inline-list">
              <span class="dbm-badge">${formatInt(state.detail.indexes.length)}</span>
              <button type="button" class="sz_button sz_button_ghost dbm-inline-action-btn" data-db-index-maint-open ${state.detail.indexes.length ? '' : 'disabled'}>
                <i class="fa-solid fa-screwdriver-wrench"></i>
                <span>Otimizar</span>
              </button>
            </div>
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

  async function sendJson(url, options = {}, acceptedStatuses = []) {
    const response = await fetch(url, {
      credentials: 'same-origin',
      ...options,
      headers: {
        Accept: 'application/json',
        ...(options.headers || {}),
      },
    });
    const data = await response.json().catch(() => ({}));
    const accepted = Array.isArray(acceptedStatuses) ? acceptedStatuses : [];
    const statusAccepted = accepted.includes(response.status);
    if ((!response.ok && !statusAccepted) || (data.error && !statusAccepted)) {
      const error = new Error(data.error || `HTTP ${response.status}`);
      error.status = response.status;
      error.data = data;
      throw error;
    }
    return { status: response.status, data };
  }

  async function loadBootstrap(options = {}) {
    const skipRepoSync = !!options.skipRepoSync;
    const successStatus = String(options.successStatus || '').trim();
    state.loading = true;
    setStatus('A carregar metadata da base de dados...');
    try {
      const params = new URLSearchParams();
      if (state.selectedTable) params.set('table', state.selectedTable);
      if (skipRepoSync) params.set('skip_repo_sync', '1');
      const data = await fetchJson(`/api/database_manager/bootstrap?${params.toString()}`);
      state.tables = Array.isArray(data.tables) ? data.tables : [];
      state.selectedTable = String(data.selected_table || '').trim();
      state.detail = data.detail || null;
      state.schemaRepository = data.schema_repository || { state: null, warning: '' };
      renderTables();
      renderColumns();
      renderDetail();
      renderSchemaRepositoryState();
      updateUrl(state.selectedTable);
      if (state.schemaRepository?.warning) {
        setStatus(state.schemaRepository.warning, true);
      } else {
        setStatus(successStatus || `${formatInt(state.tables.length)} tabelas carregadas.`);
      }
    } catch (error) {
      state.schemaRepository = { state: null, warning: error.message || '' };
      renderSchemaRepositoryState();
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

  async function syncSchemaRepository() {
    if (!els.syncSchemaBtn) return;
    els.syncSchemaBtn.disabled = true;
    setStatus('A sincronizar o repositorio de estrutura...');
    try {
      const { data } = await sendJson('/api/database_manager/schema_repository/sync', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({}),
      });
      state.schemaRepository = {
        state: data?.state || null,
        warning: '',
      };
      renderSchemaRepositoryState();
      await loadBootstrap({
        skipRepoSync: true,
        successStatus: 'Repositorio de estrutura sincronizado e metadata atualizada.',
      });
    } catch (error) {
      state.schemaRepository = {
        state: error?.data?.state || state.schemaRepository?.state || null,
        warning: error.message || 'Erro ao sincronizar o repositorio de estrutura.',
      };
      renderSchemaRepositoryState();
      setStatus(error.message || 'Erro ao sincronizar o repositorio de estrutura.', true);
    } finally {
      els.syncSchemaBtn.disabled = false;
    }
  }

  els.tableSearch?.addEventListener('input', (event) => {
    state.search = String(event.target.value || '');
    renderTables();
  });

  if (els.sortModal) {
    document.body.appendChild(els.sortModal);
  }
  if (els.indexMaintModal) {
    document.body.appendChild(els.indexMaintModal);
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
    if (event.key === 'Escape' && els.indexMaintModal?.classList.contains('sz_is_open')) {
      closeIndexMaintModal();
    }
  });

  els.detailContent?.addEventListener('click', (event) => {
    const trigger = event.target.closest('[data-db-index-maint-open]');
    if (!trigger) return;
    event.preventDefault();
    openIndexMaintModal();
  });

  els.indexMaintClose?.addEventListener('click', closeIndexMaintModal);
  els.indexMaintCloseTop?.addEventListener('click', closeIndexMaintModal);
  els.indexMaintModal?.addEventListener('click', (event) => {
    if (event.target === els.indexMaintModal) {
      closeIndexMaintModal();
    }
  });
  els.indexMaintModeList?.addEventListener('click', (event) => {
    const option = event.target.closest('[data-db-index-maint-mode]');
    if (!option) return;
    state.pendingIndexMaintMode = normalizeIndexMaintMode(option.dataset.dbIndexMaintMode || 'auto');
    renderIndexMaintModeOptions();
    renderIndexMaintPlan();
  });
  els.indexMaintStart?.addEventListener('click', async () => {
    const tableKey = currentTableLabel();
    if (!tableKey) {
      setStatus('Seleciona uma tabela antes de iniciar a manutenção.', true);
      return;
    }
    const plan = buildIndexMaintPlan(state.pendingIndexMaintMode);
    const actionable = plan.filter((item) => item.planned_action);
    if (!actionable.length) {
      setStatus('Não existem índices elegíveis para a ação selecionada.', true);
      return;
    }

    els.indexMaintStart.disabled = true;
    try {
      const { status, data } = await sendJson('/api/database_manager/index_maintenance/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          table: tableKey,
          mode: state.pendingIndexMaintMode,
        }),
      }, [409]);

      state.indexMaintMode = normalizeIndexMaintMode(state.pendingIndexMaintMode);
      state.indexMaintJobId = String(data?.job?.job_id || '').trim();
      renderIndexMaintJob(data);

      if (status === 409) {
        setStatus(data?.error || 'Já existe uma manutenção de índices em execução.', true);
      } else {
        setStatus(`Manutenção de índices iniciada para ${tableKey}.`);
      }

      const jobState = String(data?.job?.state || '').trim().toLowerCase();
      if (state.indexMaintJobId && ['running', 'stopping'].includes(jobState)) {
        startIndexMaintPoll(state.indexMaintJobId);
      } else if (state.selectedTable) {
        loadTableDetail(state.selectedTable);
      }
    } catch (error) {
      setStatus(error.message || 'Erro ao iniciar a manutenção de índices.', true);
    } finally {
      renderIndexMaintPlan();
      if (!state.indexMaintJobId || !['running', 'stopping'].includes(String(state.indexMaintJobPayload?.job?.state || '').trim().toLowerCase())) {
        els.indexMaintStart.disabled = false;
      }
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

  els.syncSchemaBtn?.addEventListener('click', syncSchemaRepository);
  els.refreshBtn?.addEventListener('click', refreshCurrent);
  els.actionRefreshBtn?.addEventListener('click', refreshCurrent);
  els.backBtn?.addEventListener('click', () => {
    window.history.back();
  });

  loadBootstrap();
});
