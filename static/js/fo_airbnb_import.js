(function () {
  const state = {
    rows: [],
    logs: [],
    busy: false,
    fileName: '',
  };

  const els = {
    file: document.getElementById('airbnbCsvFile'),
    btnPreview: document.getElementById('airbnbBtnPreview'),
    btnImport: document.getElementById('airbnbBtnImport'),
    btnClear: document.getElementById('airbnbBtnClear'),
    btnClearTop: document.getElementById('airbnbBtnClearTop'),
    fileMeta: document.getElementById('airbnbFileMeta'),
    previewMeta: document.getElementById('airbnbPreviewMeta'),
    importSummary: document.getElementById('airbnbImportSummary'),
    previewBody: document.getElementById('airbnbPreviewBody'),
    log: document.getElementById('airbnbLog'),
    depSupplier: document.getElementById('depSupplier'),
    depArticle: document.getElementById('depArticle'),
    statTotalRows: document.getElementById('statTotalRows'),
    statValidRows: document.getElementById('statValidRows'),
    statErrorRows: document.getElementById('statErrorRows'),
    statDuplicateRows: document.getElementById('statDuplicateRows'),
    statReadyRows: document.getElementById('statReadyRows'),
  };

  const esc = (value) => String(value ?? '').replace(/[&<>"']/g, (match) => (
    { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[match]
  ));

  function showToast(message, type = 'info') {
    if (typeof window.showToast === 'function') {
      window.showToast(message, type);
      return;
    }
    window.alert(message);
  }

  function fmtMoney(value) {
    const amount = Number(value || 0);
    return Number.isFinite(amount)
      ? amount.toLocaleString('pt-PT', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
      : '0,00';
  }

  function badgeHtml(status) {
    const value = String(status || '').toLowerCase();
    if (value === 'ok') return '<span class="sz_badge sz_badge_success">OK</span>';
    if (value === 'duplicate') return '<span class="sz_badge sz_badge_warning">Já existe</span>';
    return '<span class="sz_badge sz_badge_danger">Erro</span>';
  }

  function setBusy(flag, message) {
    state.busy = !!flag;
    [els.btnPreview, els.btnImport, els.btnClear, els.btnClearTop, els.file].forEach((el) => {
      if (el) el.disabled = !!flag;
    });
    if (message && els.importSummary) {
      els.importSummary.textContent = message;
    }
  }

  function setStats(stats = {}) {
    if (els.statTotalRows) els.statTotalRows.textContent = String(stats.total_rows || 0);
    if (els.statValidRows) els.statValidRows.textContent = String(stats.valid_rows || 0);
    if (els.statErrorRows) els.statErrorRows.textContent = String(stats.error_rows || 0);
    if (els.statDuplicateRows) els.statDuplicateRows.textContent = String(stats.duplicate_rows || 0);
    if (els.statReadyRows) els.statReadyRows.textContent = String(stats.ready_rows || 0);
  }

  function setDependencies(dependencies = {}) {
    if (els.depSupplier) {
      els.depSupplier.className = `sz_badge ${dependencies.supplier_found ? 'sz_badge_success' : 'sz_badge_danger'}`;
      els.depSupplier.textContent = dependencies.supplier_found
        ? `Fornecedor OK: ${dependencies.supplier_name || '#15'}`
        : 'Fornecedor no=15 não encontrado';
    }
    if (els.depArticle) {
      els.depArticle.className = `sz_badge ${dependencies.article_found ? 'sz_badge_success' : 'sz_badge_danger'}`;
      els.depArticle.textContent = dependencies.article_found
        ? `Artigo OK: ${dependencies.article_ref || 'TX.SERVICO'}`
        : "Artigo TX.SERVICO não encontrado";
    }
  }

  function renderPreview() {
    if (!els.previewBody) return;
    if (!state.rows.length) {
      els.previewBody.innerHTML = `
        <tr class="sz_table_row">
          <td colspan="11" class="sz_table_cell sz_text_muted">Sem dados para mostrar.</td>
        </tr>
      `;
      return;
    }
    els.previewBody.innerHTML = state.rows.map((row) => `
      <tr class="sz_table_row">
        <td class="sz_table_cell">${esc(row.row_no)}</td>
        <td class="sz_table_cell">
          <div>${esc(row.document || '')}</div>
          ${row.document_source ? `<div class="sz_text_muted">${esc(row.document_source)}</div>` : ''}
        </td>
        <td class="sz_table_cell">${esc(row.service_date || '')}</td>
        <td class="sz_table_cell">${esc(row.confirmation_code || '')}</td>
        <td class="sz_table_cell">${esc(row.reservation_checkin || '')}</td>
        <td class="sz_table_cell">${esc(row.listing || '')}</td>
        <td class="sz_table_cell sz_airbnb_import_amount">${fmtMoney(row.net_amount)}</td>
        <td class="sz_table_cell sz_airbnb_import_amount">${fmtMoney(row.vat_amount)}</td>
        <td class="sz_table_cell sz_airbnb_import_amount">${fmtMoney(row.total_amount)}</td>
        <td class="sz_table_cell sz_airbnb_import_status_cell">${badgeHtml(row.status)}</td>
        <td class="sz_table_cell">${esc(row.message || '')}</td>
      </tr>
    `).join('');
  }

  function renderLogs(extraLogs) {
    if (Array.isArray(extraLogs)) state.logs = extraLogs.slice();
    if (!els.log) return;
    els.log.textContent = state.logs.length ? state.logs.join('\n') : 'Sem logs.';
    els.log.scrollTop = els.log.scrollHeight;
  }

  function updateSummary() {
    const readyCount = state.rows.filter((row) => row.can_import).length;
    if (els.importSummary) {
      els.importSummary.textContent = readyCount
        ? `${readyCount} documento(s) prontos a importar.`
        : 'Nenhuma linha pronta a importar.';
    }
    if (els.btnImport) {
      els.btnImport.disabled = state.busy || readyCount === 0;
    }
  }

  function clearAll() {
    state.rows = [];
    state.logs = [];
    state.fileName = '';
    if (els.file) els.file.value = '';
    if (els.fileMeta) els.fileMeta.textContent = 'Sem ficheiro analisado.';
    if (els.previewMeta) els.previewMeta.textContent = 'Ainda sem dados.';
    setStats({});
    setDependencies({});
    renderPreview();
    renderLogs(['À espera de ficheiro.']);
    updateSummary();
  }

  async function previewCsv() {
    const file = els.file?.files?.[0];
    if (!file) {
      showToast('Selecione um ficheiro CSV.', 'warning');
      return;
    }
    setBusy(true, 'A analisar ficheiro...');
    if (els.fileMeta) els.fileMeta.textContent = `A analisar ${file.name}...`;
    try {
      const formData = new FormData();
      formData.append('file', file);
      const res = await fetch('/api/fo_airbnb_import/preview', {
        method: 'POST',
        body: formData,
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok || data.error) throw new Error(data.error || 'Erro ao analisar o CSV.');
      state.rows = Array.isArray(data.rows) ? data.rows : [];
      state.fileName = file.name;
      if (els.fileMeta) {
        els.fileMeta.textContent = `${file.name} · ${data.stats?.total_rows || 0} linha(s) lida(s)`;
      }
      if (els.previewMeta) {
        els.previewMeta.textContent = 'Pré-visualização concluída. Revê as linhas antes de importar.';
      }
      setStats(data.stats || {});
      setDependencies(data.dependencies || {});
      renderPreview();
      renderLogs(data.logs || []);
      updateSummary();
    } catch (error) {
      showToast(error.message || 'Erro ao analisar o ficheiro.', 'danger');
      renderLogs([String(error.message || 'Erro ao analisar o ficheiro.')]);
    } finally {
      setBusy(false);
      updateSummary();
    }
  }

  async function importRows() {
    const rows = state.rows.filter((row) => row.can_import);
    if (!rows.length) {
      showToast('Não há linhas prontas a importar.', 'warning');
      return;
    }
    setBusy(true, 'A importar documentos...');
    try {
      const res = await fetch('/api/fo_airbnb_import/import', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ rows }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok || data.error) throw new Error(data.error || 'Erro ao importar documentos.');

      const createdCount = Number(data.stats?.created || 0);
      const skippedCount = Number(data.stats?.skipped || 0);
      const failedCount = Number(data.stats?.failed || 0);

      if (els.previewMeta) {
        els.previewMeta.textContent = `Importação concluída: ${createdCount} criado(s), ${skippedCount} ignorado(s), ${failedCount} falhado(s).`;
      }
      renderLogs(data.logs || []);
      showToast(`Importação concluída. Criados: ${createdCount}. Falhados: ${failedCount}.`, failedCount ? 'warning' : 'success');

      if (createdCount > 0) {
        state.rows = state.rows.map((row) => {
          const hit = (data.created || []).find((item) => Number(item.row_no || 0) === Number(row.row_no || 0));
          if (!hit) return row;
          return {
            ...row,
            status: 'duplicate',
            can_import: false,
            message: `Importado em ${hit.fostamp}`,
          };
        });
        const remainingReady = state.rows.filter((row) => row.can_import).length;
        setStats({
          total_rows: state.rows.length,
          valid_rows: remainingReady,
          error_rows: state.rows.filter((row) => row.status === 'error').length,
          duplicate_rows: state.rows.filter((row) => row.status === 'duplicate').length,
          ready_rows: remainingReady,
        });
        renderPreview();
      }
    } catch (error) {
      showToast(error.message || 'Erro ao importar.', 'danger');
      renderLogs([...(state.logs || []), `IMPORT_ERROR ${error.message || 'Erro ao importar.'}`]);
    } finally {
      setBusy(false);
      updateSummary();
    }
  }

  function bindEvents() {
    els.btnPreview?.addEventListener('click', previewCsv);
    els.btnImport?.addEventListener('click', importRows);
    els.btnClear?.addEventListener('click', clearAll);
    els.btnClearTop?.addEventListener('click', clearAll);
    els.file?.addEventListener('change', () => {
      const file = els.file?.files?.[0];
      if (els.fileMeta) {
        els.fileMeta.textContent = file ? `${file.name} selecionado.` : 'Sem ficheiro analisado.';
      }
    });
  }

  bindEvents();
  clearAll();
})();
