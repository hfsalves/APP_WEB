document.addEventListener('DOMContentLoaded', () => {
  const cfg = window.DATABASE_MAPPING_CONFIG || {};
  const url = new URL(window.location.href);
  const els = {
    subtitle: document.getElementById('dbmapSubtitle'),
    meta: document.getElementById('dbmapMeta'),
    tableMeta: document.getElementById('dbmapTableMeta'),
    fieldsMeta: document.getElementById('dbmapFieldsMeta'),
    status: document.getElementById('dbmapStatus'),
    enabled: document.getElementById('dbmapEnabled'),
    sourceTable: document.getElementById('dbmapSourceTable'),
    targetScope: document.getElementById('dbmapTargetScope'),
    targetDatabaseField: document.getElementById('dbmapTargetDatabaseField'),
    targetDatabase: document.getElementById('dbmapTargetDatabase'),
    targetSchema: document.getElementById('dbmapTargetSchema'),
    targetTable: document.getElementById('dbmapTargetTable'),
    targetSchema2: document.getElementById('dbmapTargetSchema2'),
    targetTable2: document.getElementById('dbmapTargetTable2'),
    joinCondition2: document.getElementById('dbmapJoinCondition2'),
    targetSchema3: document.getElementById('dbmapTargetSchema3'),
    targetTable3: document.getElementById('dbmapTargetTable3'),
    joinCondition3: document.getElementById('dbmapJoinCondition3'),
    notes: document.getElementById('dbmapNotes'),
    fieldsList: document.getElementById('dbmapFieldsList'),
    refreshBtn: document.getElementById('dbmapRefreshBtn'),
    saveBtn: document.getElementById('dbmapSaveBtn'),
    backBtn: document.getElementById('dbmapBackBtn'),
    backManagerBtn: document.getElementById('dbmapBackManagerBtn'),
    simOpenBtn: document.getElementById('dbmapSimOpenBtn'),
    simModal: document.getElementById('dbmapSimModal'),
    simClose: document.getElementById('dbmapSimClose'),
    simCloseTop: document.getElementById('dbmapSimCloseTop'),
    simTableLabel: document.getElementById('dbmapSimTableLabel'),
    simDirection: document.getElementById('dbmapSimDirection'),
    simOperation: document.getElementById('dbmapSimOperation'),
    simLimit: document.getElementById('dbmapSimLimit'),
    simRunBtn: document.getElementById('dbmapSimRunBtn'),
    simImportBtn: document.getElementById('dbmapSimImportBtn'),
    simSummary: document.getElementById('dbmapSimSummary'),
    simResults: document.getElementById('dbmapSimResults'),
  };

  const state = {
    tableKey: String(cfg.initialTableKey || url.searchParams.get('table') || '').trim(),
    payload: null,
    simulation: null,
    loading: false,
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

  function setStatus(message, isError = false) {
    if (!els.status) return;
    els.status.textContent = message || '';
    els.status.style.color = isError ? 'var(--sz-color-danger)' : '';
  }

  function currentTableKey() {
    return String(state.payload?.table?.key || state.tableKey || '').trim();
  }

  function updateUrl() {
    const tableKey = currentTableKey();
    const nextUrl = new URL(window.location.href);
    if (tableKey) nextUrl.searchParams.set('table', tableKey);
    window.history.replaceState({}, '', nextUrl.toString());
  }

  function updateTargetScopeVisibility() {
    const scope = String(els.targetScope?.value || 'FE').trim().toUpperCase();
    const fixed = scope === 'FIXED';
    if (els.targetDatabaseField) {
      els.targetDatabaseField.classList.toggle('is-muted', !fixed);
    }
    if (els.targetDatabase) {
      els.targetDatabase.disabled = !fixed;
      els.targetDatabase.placeholder = fixed ? 'Ex: HSOLS_MASTER' : 'Definida pela FE';
    }
  }

  function normalizeTargetTables(mapping = {}, table = {}) {
    const rows = Array.isArray(mapping.target_tables) ? mapping.target_tables : [];
    const byRef = new Map();
    rows.forEach((row) => {
      const ref = String(row?.target_ref || '').trim().toUpperCase();
      if (!['T1', 'T2', 'T3'].includes(ref)) return;
      byRef.set(ref, {
        target_ref: ref,
        target_schema: String(row.target_schema || 'dbo').trim() || 'dbo',
        target_table: String(row.target_table || '').trim(),
        join_condition: String(row.join_condition || '').trim(),
        order: Number(row.order || Number(ref.slice(1)) || 1),
      });
    });

    if (!byRef.has('T1')) {
      byRef.set('T1', {
        target_ref: 'T1',
        target_schema: String(mapping.target_schema || 'dbo').trim() || 'dbo',
        target_table: String(mapping.target_table || table.name || '').trim(),
        join_condition: '',
        order: 1,
      });
    }

    return ['T1', 'T2', 'T3'].map((ref) => byRef.get(ref) || {
      target_ref: ref,
      target_schema: 'dbo',
      target_table: '',
      join_condition: '',
      order: Number(ref.slice(1)),
    });
  }

  function currentTargetTables() {
    return [
      {
        target_ref: 'T1',
        target_schema: String(els.targetSchema?.value || 'dbo').trim() || 'dbo',
        target_table: String(els.targetTable?.value || '').trim(),
        join_condition: '',
        order: 1,
      },
      {
        target_ref: 'T2',
        target_schema: String(els.targetSchema2?.value || 'dbo').trim() || 'dbo',
        target_table: String(els.targetTable2?.value || '').trim(),
        join_condition: String(els.joinCondition2?.value || '').trim(),
        order: 2,
      },
      {
        target_ref: 'T3',
        target_schema: String(els.targetSchema3?.value || 'dbo').trim() || 'dbo',
        target_table: String(els.targetTable3?.value || '').trim(),
        join_condition: String(els.joinCondition3?.value || '').trim(),
        order: 3,
      },
    ];
  }

  function selectableTargetTables() {
    return currentTargetTables().filter((item) => item.target_ref === 'T1' || item.target_table);
  }

  function targetTableOptionLabel(item) {
    const tableName = item.target_table
      ? `${item.target_schema || 'dbo'}.${item.target_table}`
      : 'sem tabela';
    return `${item.target_ref} - ${tableName}`;
  }

  function renderTargetRefOptions(selectedRef) {
    const selected = String(selectedRef || 'T1').trim().toUpperCase();
    const available = selectableTargetTables();
    if (!available.some((item) => item.target_ref === selected)) {
      available.push({
        target_ref: selected,
        target_schema: 'dbo',
        target_table: '',
        join_condition: '',
        order: Number(selected.replace('T', '')) || 1,
      });
    }
    return available
      .sort((a, b) => Number(a.order || 0) - Number(b.order || 0))
      .map((item) => `<option value="${escapeHtml(item.target_ref)}" ${item.target_ref === selected ? 'selected' : ''}>${escapeHtml(targetTableOptionLabel(item))}</option>`)
      .join('');
  }

  function refreshTargetRefSelects() {
    if (!els.fieldsList) return;
    els.fieldsList.querySelectorAll('.dbmap-target-ref').forEach((select) => {
      const selected = String(select.value || 'T1').trim().toUpperCase();
      select.innerHTML = renderTargetRefOptions(selected);
    });
  }

  function renderForm() {
    const payload = state.payload || {};
    const table = payload.table || {};
    const mapping = payload.mapping || {};
    const tableKey = String(table.key || state.tableKey || '').trim();
    const targetScope = String(mapping.target_scope || 'FE').trim().toUpperCase();
    const targetTables = normalizeTargetTables(mapping, table);
    const mainTarget = targetTables[0] || {};
    const secondTarget = targetTables[1] || {};
    const thirdTarget = targetTables[2] || {};

    if (els.subtitle) {
      els.subtitle.textContent = tableKey
        ? `Mapeamento de ${tableKey} para a tabela externa.`
        : 'Seleciona uma tabela no Database Manager para configurar o mapeamento.';
    }
    if (els.meta) {
      const status = mapping.enabled ? 'Ativo' : 'Inativo';
      const relatedCount = targetTables.filter((item) => item.target_ref !== 'T1' && item.target_table).length;
      const target = targetScope === 'FIXED'
        ? `${mapping.target_database || 'sem DB'}.${mainTarget.target_schema || 'dbo'}.${mainTarget.target_table || 'sem tabela'}`
        : `FE.${mainTarget.target_schema || 'dbo'}.${mainTarget.target_table || 'sem tabela'}`;
      els.meta.textContent = `${status} | destino ${target}${relatedCount ? ` | +${relatedCount} tabela(s)` : ''}`;
    }
    if (els.tableMeta) {
      els.tableMeta.textContent = tableKey || 'Sem tabela selecionada.';
    }

    if (els.enabled) els.enabled.checked = !!mapping.enabled;
    if (els.sourceTable) els.sourceTable.value = tableKey;
    if (els.targetScope) els.targetScope.value = ['FE', 'FIXED'].includes(targetScope) ? targetScope : 'FE';
    if (els.targetDatabase) els.targetDatabase.value = mapping.target_database || '';
    if (els.targetSchema) els.targetSchema.value = mainTarget.target_schema || mapping.target_schema || 'dbo';
    if (els.targetTable) els.targetTable.value = mainTarget.target_table || mapping.target_table || table.name || '';
    if (els.targetSchema2) els.targetSchema2.value = secondTarget.target_schema || 'dbo';
    if (els.targetTable2) els.targetTable2.value = secondTarget.target_table || '';
    if (els.joinCondition2) els.joinCondition2.value = secondTarget.join_condition || '';
    if (els.targetSchema3) els.targetSchema3.value = thirdTarget.target_schema || 'dbo';
    if (els.targetTable3) els.targetTable3.value = thirdTarget.target_table || '';
    if (els.joinCondition3) els.joinCondition3.value = thirdTarget.join_condition || '';
    if (els.notes) els.notes.value = mapping.notes || '';
    updateTargetScopeVisibility();
  }

  function renderFields() {
    const fields = Array.isArray(state.payload?.fields) ? state.payload.fields : [];
    if (els.fieldsMeta) {
      els.fieldsMeta.textContent = `${formatInt(fields.length)} campos mapeáveis`;
    }
    if (!els.fieldsList) return;
    if (!fields.length) {
      els.fieldsList.innerHTML = '<div class="dbm-empty">Sem campos para mapear.</div>';
      return;
    }

    els.fieldsList.innerHTML = fields.map((field, index) => {
      const direction = String(field.sync_direction || 'BIDIRECTIONAL').trim().toUpperCase();
      const targetRef = String(field.target_ref || 'T1').trim().toUpperCase();
      const hasTarget = !!String(field.target_column || '').trim();
      return `
        <article class="dbmap-field-row ${field.source_missing ? 'is-missing' : ''}" data-source-column="${escapeHtml(field.source_column)}" data-order="${escapeHtml(field.order || index + 1)}">
          <div class="dbmap-field-source">
            <div class="dbmap-field-source-top">
              <code class="dbm-code">${escapeHtml(field.source_column)}</code>
              <span class="dbm-type">${escapeHtml(field.source_type || 'n/a')}</span>
            </div>
            <div class="dbm-badges">
              ${field.source_primary_key ? '<span class="dbm-badge is-primary">PK</span>' : ''}
              ${field.source_nullable ? '<span class="dbm-badge">NULL</span>' : '<span class="dbm-badge">NOT NULL</span>'}
              ${field.source_missing ? '<span class="dbm-badge is-danger">Sem campo origem</span>' : ''}
              ${hasTarget ? '' : '<span class="dbm-badge is-warning">Só app</span>'}
            </div>
          </div>

          <div class="dbmap-field-target">
            <div class="sz_field dbmap-target-ref-field">
              <label class="sz_label">Tabela</label>
              <select class="sz_input dbmap-target-ref">
                ${renderTargetRefOptions(targetRef)}
              </select>
            </div>
            <div class="sz_field">
              <label class="sz_label">Campo destino</label>
              <input class="sz_input dbmap-target-column" type="text" value="${escapeHtml(field.target_column || '')}" placeholder="Vazio = não existe no PHC">
            </div>
            <div class="sz_field">
              <label class="sz_label">Direção</label>
              <select class="sz_input dbmap-direction">
                <option value="BIDIRECTIONAL" ${direction === 'BIDIRECTIONAL' ? 'selected' : ''}>Bidirecional</option>
                <option value="APP_TO_TARGET" ${direction === 'APP_TO_TARGET' ? 'selected' : ''}>App -> destino</option>
                <option value="TARGET_TO_APP" ${direction === 'TARGET_TO_APP' ? 'selected' : ''}>Destino -> app</option>
              </select>
            </div>
            <label class="dbmap-mini-check">
              <input class="dbmap-is-key" type="checkbox" ${field.is_key ? 'checked' : ''}>
              <span>Chave</span>
            </label>
            <label class="dbmap-mini-check">
              <input class="dbmap-is-required" type="checkbox" ${field.is_required ? 'checked' : ''}>
              <span>Obrigatório</span>
            </label>
            <div class="sz_field dbmap-transform-field">
              <label class="sz_label">Transformação</label>
              <input class="sz_input dbmap-transform" type="text" value="${escapeHtml(field.transform_expr || '')}" placeholder="Opcional">
            </div>
          </div>
        </article>
      `;
    }).join('');
  }

  function actionBadgeClass(action) {
    switch (String(action || '').trim().toLowerCase()) {
      case 'insert':
        return 'dbm-badge is-success';
      case 'update':
        return 'dbm-badge is-primary';
      case 'skip':
        return 'dbm-badge';
      case 'error':
        return 'dbm-badge is-danger';
      default:
        return 'dbm-badge is-primary';
    }
  }

  function actionLabel(action) {
    switch (String(action || '').trim().toLowerCase()) {
      case 'insert':
        return 'inserir';
      case 'update':
        return 'atualizar';
      case 'skip':
        return 'ignorar';
      case 'error':
        return 'erro';
      default:
        return action || 'n/a';
    }
  }

  function renderObjectPreview(values) {
    const entries = Object.entries(values || {});
    if (!entries.length) return '<div class="dbmap-sim-empty-values">Sem valores.</div>';
    return entries.slice(0, 12).map(([key, value]) => `
      <div class="dbmap-sim-kv">
        <span>${escapeHtml(key)}</span>
        <strong>${escapeHtml(value == null ? '' : value)}</strong>
      </div>
    `).join('');
  }

  function renderSimulation(payload) {
    state.simulation = payload || null;
    const totals = payload?.totals || {};
    const insertCandidates = Number(totals.insert_candidates || 0);
    const updateCandidates = Number(totals.update_candidates || 0);
    if (els.simSummary) {
      els.simSummary.textContent = payload
        ? `${formatInt(insertCandidates)} inserir | ${formatInt(updateCandidates)} atualizar | ${formatInt(totals.skipped)} ignorar | ${formatInt(totals.errors)} erros`
        : 'Sem simulação';
    }
    if (els.simImportBtn) {
      els.simImportBtn.disabled = (insertCandidates + updateCandidates) <= 0;
    }
    if (!els.simResults) return;
    if (!payload) {
      els.simResults.innerHTML = '<div class="dbm-empty">Executa uma simulação para ver os registos.</div>';
      return;
    }
    const scopes = Array.isArray(payload.scopes) ? payload.scopes : [];
    if (!scopes.length) {
      els.simResults.innerHTML = '<div class="dbm-empty">A simulação não devolveu dados.</div>';
      return;
    }
    els.simResults.innerHTML = scopes.map((scope) => {
      const scopeLabel = scope.scope_type === 'FE'
        ? `${scope.fe_name || 'FE'} (${scope.feid || 0}) | ${scope.target_database || 'sem BD'}`
        : `BD fixa | ${scope.target_database || 'sem BD'}`;
      const rows = Array.isArray(scope.rows) ? scope.rows : [];
      return `
        <section class="dbmap-sim-scope">
          <div class="dbmap-sim-scope-head">
            <strong>${escapeHtml(scopeLabel)}</strong>
            <span class="dbm-badge">${formatInt(rows.length)}</span>
          </div>
          <div class="dbmap-sim-row-list">
            ${rows.map((row) => `
              <article class="dbmap-sim-row">
                <div class="dbmap-sim-row-head">
                  <span class="${actionBadgeClass(row.action)}">${escapeHtml(actionLabel(row.action))}</span>
                  <span class="dbmap-sim-reason">${escapeHtml(row.reason || '')}</span>
                </div>
                <div class="dbmap-sim-values">
                  ${renderObjectPreview(row.values)}
                </div>
              </article>
            `).join('') || '<div class="dbm-empty">Sem linhas neste âmbito.</div>'}
          </div>
        </section>
      `;
    }).join('');
  }

  async function fetchJson(fetchUrl) {
    const response = await fetch(fetchUrl, {
      headers: { Accept: 'application/json' },
      credentials: 'same-origin',
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok || data.error) {
      throw new Error(data.error || `HTTP ${response.status}`);
    }
    return data;
  }

  async function sendJson(fetchUrl, body) {
    const response = await fetch(fetchUrl, {
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

  async function loadMapping() {
    if (!state.tableKey) {
      setStatus('Abre o mapeamento a partir de uma tabela selecionada no Database Manager.', true);
      if (els.fieldsList) {
        els.fieldsList.innerHTML = '<div class="dbm-empty">Nenhuma tabela selecionada.</div>';
      }
      return;
    }
    state.loading = true;
    setStatus(`A carregar mapeamento de ${state.tableKey}...`);
    try {
      const payload = await fetchJson(`/api/database_manager/mapping?table=${encodeURIComponent(state.tableKey)}`);
      state.payload = payload;
      state.tableKey = currentTableKey();
      renderForm();
      renderFields();
      updateUrl();
      setStatus(`Mapeamento de ${state.tableKey} carregado.`);
    } catch (error) {
      setStatus(error.message || 'Erro ao carregar mapeamento.', true);
      if (els.fieldsList) {
        els.fieldsList.innerHTML = `<div class="dbm-empty">${escapeHtml(error.message || 'Erro ao carregar mapeamento.')}</div>`;
      }
    } finally {
      state.loading = false;
    }
  }

  function collectFields() {
    if (!els.fieldsList) return [];
    return Array.from(els.fieldsList.querySelectorAll('.dbmap-field-row')).map((row, index) => ({
      source_column: String(row.dataset.sourceColumn || '').trim(),
      target_ref: String(row.querySelector('.dbmap-target-ref')?.value || 'T1').trim().toUpperCase(),
      target_column: String(row.querySelector('.dbmap-target-column')?.value || '').trim(),
      sync_direction: String(row.querySelector('.dbmap-direction')?.value || 'BIDIRECTIONAL').trim().toUpperCase(),
      is_key: !!row.querySelector('.dbmap-is-key')?.checked,
      is_required: !!row.querySelector('.dbmap-is-required')?.checked,
      transform_expr: String(row.querySelector('.dbmap-transform')?.value || '').trim(),
      order: Number(row.dataset.order || index + 1),
    })).filter((item) => item.source_column);
  }

  async function saveMapping() {
    const tableKey = currentTableKey();
    if (!tableKey || state.loading) return;
    const body = {
      table: tableKey,
      enabled: !!els.enabled?.checked,
      target_scope: String(els.targetScope?.value || 'FE').trim().toUpperCase(),
      target_database: String(els.targetDatabase?.value || '').trim(),
      target_schema: String(els.targetSchema?.value || 'dbo').trim(),
      target_table: String(els.targetTable?.value || '').trim(),
      target_tables: currentTargetTables(),
      notes: String(els.notes?.value || '').trim(),
      fields: collectFields(),
    };

    if (els.saveBtn) els.saveBtn.disabled = true;
    setStatus(`A guardar mapeamento de ${tableKey}...`);
    try {
      const payload = await sendJson('/api/database_manager/mapping', body);
      state.payload = payload;
      state.tableKey = currentTableKey();
      renderForm();
      renderFields();
      setStatus('Mapeamento guardado.');
    } catch (error) {
      setStatus(error.message || 'Erro ao guardar mapeamento.', true);
    } finally {
      if (els.saveBtn) els.saveBtn.disabled = false;
    }
  }

  function simulationRequestBody() {
    return {
      table: currentTableKey(),
      direction: String(els.simDirection?.value || 'TARGET_TO_APP').trim().toUpperCase(),
      operation: String(els.simOperation?.value || 'INSERT_ONLY').trim().toUpperCase(),
      limit: Number(els.simLimit?.value || 100),
    };
  }

  function openSimulationModal() {
    if (!els.simModal) return;
    if (els.simTableLabel) {
      els.simTableLabel.textContent = currentTableKey() || 'Sem tabela selecionada.';
    }
    updateSimulationImportLabel();
    renderSimulation(null);
    document.body.appendChild(els.simModal);
    document.body.classList.add('modal-dbmap-sim-open');
    els.simModal.classList.add('sz_is_open');
    els.simModal.setAttribute('aria-hidden', 'false');
  }

  function closeSimulationModal() {
    if (!els.simModal) return;
    els.simModal.classList.remove('sz_is_open');
    els.simModal.setAttribute('aria-hidden', 'true');
    document.body.classList.remove('modal-dbmap-sim-open');
  }

  async function runSimulation() {
    const tableKey = currentTableKey();
    if (!tableKey) return;
    if (els.simRunBtn) els.simRunBtn.disabled = true;
    if (els.simImportBtn) els.simImportBtn.disabled = true;
    setStatus('A simular importação/exportação...');
    try {
      const payload = await sendJson('/api/database_manager/mapping/simulate', simulationRequestBody());
      renderSimulation(payload);
      setStatus('Simulação concluída.');
    } catch (error) {
      renderSimulation(null);
      if (els.simResults) {
        els.simResults.innerHTML = `<div class="dbm-empty">${escapeHtml(error.message || 'Erro na simulação.')}</div>`;
      }
      setStatus(error.message || 'Erro na simulação.', true);
    } finally {
      if (els.simRunBtn) els.simRunBtn.disabled = false;
    }
  }

  function updateSimulationImportLabel() {
    if (!els.simImportBtn) return;
    const label = els.simImportBtn.querySelector('span');
    if (!label) return;
    label.textContent = String(els.simDirection?.value || '').trim().toUpperCase() === 'APP_TO_TARGET'
      ? 'Exportar'
      : 'Importar';
  }

  async function importSimulation() {
    const tableKey = currentTableKey();
    if (!tableKey || !state.simulation) return;
    if (els.simImportBtn) els.simImportBtn.disabled = true;
    if (els.simRunBtn) els.simRunBtn.disabled = true;
    setStatus('A importar/exportar todos os registos elegíveis...');
    try {
      const payload = await sendJson('/api/database_manager/mapping/import', simulationRequestBody());
      renderSimulation(payload);
      const totals = payload?.totals || {};
      setStatus(`${formatInt(totals.inserted || 0)} registos inseridos, ${formatInt(totals.updated || 0)} atualizados.`);
      if (els.simImportBtn) els.simImportBtn.disabled = true;
    } catch (error) {
      setStatus(error.message || 'Erro ao importar/exportar.', true);
      if (els.simImportBtn) els.simImportBtn.disabled = false;
    } finally {
      if (els.simRunBtn) els.simRunBtn.disabled = false;
    }
  }

  function goToManager() {
    const tableKey = currentTableKey();
    const managerUrl = new URL('/database_manager', window.location.origin);
    if (tableKey) managerUrl.searchParams.set('table', tableKey);
    window.location.href = managerUrl.toString();
  }

  els.targetScope?.addEventListener('change', updateTargetScopeVisibility);
  [
    els.targetSchema,
    els.targetTable,
    els.targetSchema2,
    els.targetTable2,
    els.targetSchema3,
    els.targetTable3,
  ].forEach((input) => {
    input?.addEventListener('input', refreshTargetRefSelects);
  });
  els.refreshBtn?.addEventListener('click', loadMapping);
  els.saveBtn?.addEventListener('click', saveMapping);
  els.simOpenBtn?.addEventListener('click', openSimulationModal);
  els.simClose?.addEventListener('click', closeSimulationModal);
  els.simCloseTop?.addEventListener('click', closeSimulationModal);
  els.simModal?.addEventListener('click', (event) => {
    if (event.target === els.simModal) {
      closeSimulationModal();
    }
  });
  els.simRunBtn?.addEventListener('click', runSimulation);
  els.simImportBtn?.addEventListener('click', importSimulation);
  els.simDirection?.addEventListener('change', () => {
    updateSimulationImportLabel();
    renderSimulation(null);
  });
  els.simOperation?.addEventListener('change', () => {
    renderSimulation(null);
  });
  els.backManagerBtn?.addEventListener('click', goToManager);
  els.backBtn?.addEventListener('click', () => {
    window.history.back();
  });

  loadMapping();
});
