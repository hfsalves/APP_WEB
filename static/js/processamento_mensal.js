document.addEventListener('DOMContentLoaded', () => {
  const body = document.getElementById('pmBody');
  const foot = document.getElementById('pmFoot');
  const label = document.getElementById('pmMonthLabel');
  const countEl = document.getElementById('pmCount');
  const btnPrev = document.getElementById('pmPrev');
  const btnNext = document.getElementById('pmNext');
  const btnAddClientes = document.getElementById('pmAddClientes');
  const btnCalcValores = document.getElementById('pmCalcValores');
  const btnFaturacao = document.getElementById('pmFaturacao');
  const clientesModalEl = document.getElementById('pmClientesModal');
  const clientesBody = document.getElementById('pmClientesBody');
  const clientesSave = document.getElementById('pmAddClientesSave');
  const selectAllEl = document.getElementById('pmSelectAll');
  const clientesModal = clientesModalEl ? new bootstrap.Modal(clientesModalEl) : null;
  const docsModalEl = document.getElementById('pmDocsModal');
  const docsTitle = document.getElementById('pmDocsTitle');
  const docsFolder = document.getElementById('pmDocsFolder');
  const docsBody = document.getElementById('pmDocsBody');
  const docsStatus = document.getElementById('pmDocsStatus');
  const docsInput = document.getElementById('pmDocsInput');
  const docsPick = document.getElementById('pmDocsPick');
  const docsModal = docsModalEl ? new bootstrap.Modal(docsModalEl) : null;
  let lastRows = [];
  let currentDocsStamp = '';
  const drillModalEl = document.getElementById('pmDrillModal');
  const drillTitle = document.getElementById('pmDrillTitle');
  const drillHead = document.getElementById('pmDrillHead');
  const drillBody = document.getElementById('pmDrillBody');
  const drillFoot = document.getElementById('pmDrillFoot');
  const drillFilter = document.getElementById('pmDrillFilter');
  const drillAlojamento = document.getElementById('pmDrillAlojamento');
  const drillModal = drillModalEl ? new bootstrap.Modal(drillModalEl) : null;
  let currentDrill = { type: '', columns: [], rows: [] };

  let cur = new Date();
  cur.setDate(1);

  const fmtMonth = new Intl.DateTimeFormat('pt-PT', { month: 'long', year: 'numeric' });

  const escapeHtml = (s) => (s ?? '').toString()
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#039;');

  function invoiceBadge(row) {
    const faturado = Number(row.FATURADO_GESTAO || 0) === 1;
    if (faturado) {
      const label = [row.PHC_DOC, row.PHC_NUMERO].filter(Boolean).join(' ') || 'Emitida';
      return `<span class="pm-invoice-badge ok" title="${escapeHtml(label)}"><i class="fa-solid fa-circle-check"></i><span>${escapeHtml(label)}</span></span>`;
    }
    const warnings = Array.isArray(row.FATURACAO_WARNINGS) ? row.FATURACAO_WARNINGS.filter(Boolean) : [];
    if (warnings.length) {
      return `<span class="pm-invoice-badge warn" title="${escapeHtml(warnings.join('; '))}"><i class="fa-solid fa-triangle-exclamation"></i><span>${escapeHtml(warnings[0])}</span></span>`;
    }
    return '<span class="pm-invoice-badge"><i class="fa-regular fa-clock"></i><span>Por faturar</span></span>';
  }

  function pdfCell(row) {
    const url = (row.PHC_PDF_URL || '').toString().trim();
    if (url) {
      return `<a class="pm-pdf-link" href="${escapeHtml(url)}" target="_blank" rel="noopener" title="Abrir PDF"><i class="fa-solid fa-file-pdf"></i></a>`;
    }
    return '<span class="pm-pdf-empty" title="PDF indisponível"><i class="fa-regular fa-file-pdf"></i></span>';
  }

  function docsButton(row) {
    const count = Number(row.DOC_COUNT || 0);
    const badge = count > 0 ? `<span class="pm-doc-count">${escapeHtml(String(count))}</span>` : '';
    return `<button class="pm-doc-btn" title="Documentos do cliente"><i class="fa-solid fa-paperclip"></i>${badge}</button>`;
  }

  function invoiceEligibleRows() {
    return lastRows.filter(r => Number(r.FATURADO_GESTAO || 0) !== 1 && Number(r.FATURACAO_OK || 0) === 1);
  }

  function setLabel() {
    if (label) label.textContent = fmtMonth.format(cur);
  }

  function monthParams() {
    return { ano: cur.getFullYear(), mes: cur.getMonth() + 1 };
  }

  function render(rows) {
    if (!body) return;
    if (!rows.length) {
      body.innerHTML = '<tr><td colspan="10" class="text-muted p-3">Sem registos.</td></tr>';
      if (foot) {
        foot.innerHTML = `
          <tr class="pm-total-row">
            <th colspan="3">Totais</th>
            <td class="text-end">0.00</td>
            <td class="text-end">0.00</td>
            <td class="text-end">0.00</td>
            <td class="text-end">0.00</td>
            <td></td>
            <td></td>
            <td></td>
          </tr>
        `;
      }
      if (countEl) countEl.textContent = '0 registos';
      if (btnFaturacao) btnFaturacao.disabled = true;
      return;
    }
    const totals = rows.reduce((acc, r) => {
      const com = Number(r.COMISSOES || 0);
      const imp = Number(r.IMPUTACOES || 0);
      const tot = Number(r.TOTAL || 0);
      acc.COMISSOES += Number.isFinite(com) ? com : 0;
      acc.IMPUTACOES += Number.isFinite(imp) ? imp : 0;
      acc.TOTAL += Number.isFinite(tot) ? tot : 0;
      acc.TOTAL_IVA += Number.isFinite(tot) ? tot * 1.23 : 0;
      return acc;
    }, { COMISSOES: 0, IMPUTACOES: 0, TOTAL: 0, TOTAL_IVA: 0 });
    body.innerHTML = rows.map(r => {
      const canDelete = Number(r.CAN_DELETE || 0) === 1;
      const com = Number(r.COMISSOES || 0);
      const imp = Number(r.IMPUTACOES || 0);
      const tot = Number(r.TOTAL || 0);
      const totIva = tot * 1.23;
      const canInvoice = Number(r.FATURADO_GESTAO || 0) !== 1 && Number(r.FATURACAO_OK || 0) === 1;
      return `
        <tr data-stamp="${escapeHtml(r.DMSTAMP || '')}">
          <td>${escapeHtml(r.NO)}</td>
          <td>${escapeHtml(r.CLESTAB ?? 0)}</td>
          <td title="${escapeHtml(r.NOME)}">${escapeHtml(r.NOME)}</td>
          <td class="text-end"><span class="pm-cell-link pm-comm" data-stamp="${escapeHtml(r.DMSTAMP || '')}">${escapeHtml(com.toFixed(2))}</span></td>
          <td class="text-end"><span class="pm-cell-link pm-imp" data-stamp="${escapeHtml(r.DMSTAMP || '')}">${escapeHtml(imp.toFixed(2))}</span></td>
          <td class="text-end">${escapeHtml(tot.toFixed(2))}</td>
          <td class="text-end">${escapeHtml(totIva.toFixed(2))}</td>
          <td>${invoiceBadge(r)}</td>
          <td>${pdfCell(r)}</td>
          <td><span class="pm-row-actions">${docsButton(r)}${canInvoice ? '<button class="pm-fat-btn" title="Emitir fatura"><i class="fa-solid fa-file-invoice"></i></button>' : ''}${canDelete ? '<button class="pm-del" title="Eliminar"><i class="fa-solid fa-trash"></i></button>' : ''}</span></td>
        </tr>
      `;
    }).join('');
    if (foot) {
      foot.innerHTML = `
        <tr class="pm-total-row">
          <th colspan="3">Totais</th>
          <td class="text-end">${escapeHtml(totals.COMISSOES.toFixed(2))}</td>
          <td class="text-end">${escapeHtml(totals.IMPUTACOES.toFixed(2))}</td>
          <td class="text-end">${escapeHtml(totals.TOTAL.toFixed(2))}</td>
          <td class="text-end">${escapeHtml(totals.TOTAL_IVA.toFixed(2))}</td>
          <td></td>
          <td></td>
          <td></td>
        </tr>
      `;
    }
    if (countEl) countEl.textContent = `${rows.length} registo(s)`;
    if (btnFaturacao) btnFaturacao.disabled = invoiceEligibleRows().length === 0;

    body.querySelectorAll('.pm-del').forEach(btn => {
      btn.addEventListener('click', async () => {
        const tr = btn.closest('tr');
        const stamp = tr?.getAttribute('data-stamp') || '';
        if (!stamp) return;
        if (!confirm('Eliminar este registo?')) return;
        btn.disabled = true;
        try {
          const res = await fetch('/api/processamento_mensal/delete', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ stamp })
          });
          const data = await res.json().catch(() => ({}));
          if (!res.ok || data.error) throw new Error(data.error || res.statusText);
          lastRows = lastRows.filter(r => String(r.DMSTAMP) !== String(stamp));
          render(lastRows);
        } catch (e) {
          alert(`Erro: ${e.message || e}`);
        } finally {
          btn.disabled = false;
        }
      });
    });

    body.querySelectorAll('.pm-fat-btn').forEach(btn => {
      btn.addEventListener('click', async () => {
        const tr = btn.closest('tr');
        const stamp = tr?.getAttribute('data-stamp') || '';
        if (!stamp) return;
        await emitirFaturacao([stamp]);
      });
    });

    body.querySelectorAll('.pm-doc-btn').forEach(btn => {
      btn.addEventListener('click', async () => {
        const tr = btn.closest('tr');
        const stamp = tr?.getAttribute('data-stamp') || '';
        if (!stamp) return;
        await openDocs(stamp);
      });
    });

    body.querySelectorAll('.pm-comm').forEach(el => {
      el.addEventListener('click', () => openDrill(el.getAttribute('data-stamp') || '', 'comissoes'));
    });
    body.querySelectorAll('.pm-imp').forEach(el => {
      el.addEventListener('click', () => openDrill(el.getAttribute('data-stamp') || '', 'imputacoes'));
    });
  }

  async function load() {
    if (!body) return;
    setLabel();
    const { ano, mes } = monthParams();
    body.innerHTML = '<tr><td colspan="10" class="text-muted p-3">A carregar...</td></tr>';
    const res = await fetch(`/api/processamento_mensal?ano=${ano}&mes=${mes}`);
    const data = await res.json().catch(() => ({}));
    if (!res.ok || data.error) {
      body.innerHTML = `<tr><td colspan="10" class="text-danger p-3">Erro: ${escapeHtml(data.error || res.statusText)}</td></tr>`;
      return;
    }
    lastRows = Array.isArray(data.rows) ? data.rows : [];
    render(lastRows);
  }

  function formatFileSize(bytes) {
    const n = Number(bytes || 0);
    if (!Number.isFinite(n) || n <= 0) return '0 KB';
    if (n < 1024 * 1024) return `${Math.max(1, Math.round(n / 1024))} KB`;
    return `${(n / (1024 * 1024)).toFixed(1)} MB`;
  }

  function formatFileDate(value) {
    if (!value) return '';
    const d = new Date(value);
    if (Number.isNaN(d.getTime())) return '';
    return d.toLocaleString('pt-PT', { dateStyle: 'short', timeStyle: 'short' });
  }

  function renderDocs(files) {
    if (!docsBody) return;
    const rows = Array.isArray(files) ? files : [];
    if (!rows.length) {
      docsBody.innerHTML = '<div class="text-muted p-3">Sem documentos para este processamento.</div>';
      return;
    }
    docsBody.innerHTML = rows.map(file => {
      const name = (file.name || '').toString();
      const ext = (file.ext || '').toString().toUpperCase();
      const meta = [ext, formatFileSize(file.size), formatFileDate(file.modified)].filter(Boolean).join(' · ');
      const url = (file.download_url || '').toString();
      return `
        <div class="pm-doc-row">
          <div class="pm-doc-main">
            <span class="pm-doc-name" title="${escapeHtml(name)}">${escapeHtml(name)}</span>
            <span class="pm-doc-meta">${escapeHtml(meta)}</span>
          </div>
          <a class="pm-doc-download" href="${escapeHtml(url)}" target="_blank" rel="noopener" title="Descarregar">
            <i class="fa-solid fa-download"></i>
          </a>
        </div>
      `;
    }).join('');
  }

  function setDocsStatus(message, isError = false) {
    if (!docsStatus) return;
    docsStatus.textContent = message || '';
    docsStatus.classList.toggle('is-error', Boolean(isError));
  }

  function updateRowDocCount(stamp, count) {
    lastRows = lastRows.map(row => (
      String(row.DMSTAMP || '') === String(stamp || '')
        ? { ...row, DOC_COUNT: count }
        : row
    ));
    render(lastRows);
  }

  async function openDocs(stamp) {
    if (!docsModal || !stamp) return;
    currentDocsStamp = stamp;
    const row = lastRows.find(r => String(r.DMSTAMP || '') === String(stamp));
    if (docsTitle) docsTitle.textContent = row ? `Documentos - ${row.NOME || ''}` : 'Documentos';
    if (docsFolder) docsFolder.textContent = '';
    if (docsBody) docsBody.innerHTML = '<div class="text-muted p-3">A carregar...</div>';
    setDocsStatus('');
    docsModal.show();
    try {
      const res = await fetch(`/api/processamento_mensal/documentos/${encodeURIComponent(stamp)}`);
      const data = await res.json().catch(() => ({}));
      if (!res.ok || data.error) throw new Error(data.error || res.statusText);
      if (docsFolder) docsFolder.textContent = data.folder ? `Pasta no portal: ${data.folder}` : '';
      renderDocs(data.files || []);
      updateRowDocCount(stamp, Array.isArray(data.files) ? data.files.length : 0);
    } catch (e) {
      setDocsStatus(`Erro: ${e.message || e}`, true);
      if (docsBody) docsBody.innerHTML = '<div class="text-muted p-3">Não foi possível carregar os documentos.</div>';
    }
  }

  docsPick?.addEventListener('click', () => {
    if (!currentDocsStamp || !docsInput) return;
    docsInput.click();
  });

  docsInput?.addEventListener('change', async () => {
    const files = Array.from(docsInput.files || []);
    if (!files.length || !currentDocsStamp) return;
    const form = new FormData();
    files.forEach(file => form.append('files', file));
    if (docsPick) docsPick.disabled = true;
    setDocsStatus(`A enviar ${files.length} ficheiro(s)...`);
    try {
      const res = await fetch(`/api/processamento_mensal/documentos/${encodeURIComponent(currentDocsStamp)}/upload`, {
        method: 'POST',
        body: form
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok || data.error) throw new Error(data.error || res.statusText);
      const uploaded = Array.isArray(data.uploaded) ? data.uploaded.length : files.length;
      setDocsStatus(`${uploaded} ficheiro(s) adicionado(s).`);
      renderDocs(data.files || []);
      updateRowDocCount(currentDocsStamp, Array.isArray(data.files) ? data.files.length : uploaded);
    } catch (e) {
      setDocsStatus(`Erro: ${e.message || e}`, true);
    } finally {
      docsInput.value = '';
      if (docsPick) docsPick.disabled = false;
    }
  });

  btnPrev?.addEventListener('click', () => {
    cur.setMonth(cur.getMonth() - 1);
    load();
  });
  btnNext?.addEventListener('click', () => {
    cur.setMonth(cur.getMonth() + 1);
    load();
  });
  btnCalcValores?.addEventListener('click', async () => {
    const { ano, mes } = monthParams();
    btnCalcValores.disabled = true;
    try {
      const res = await fetch('/api/processamento_mensal/calcular', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ano, mes })
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok || data.error) throw new Error(data.error || res.statusText);
      if (Array.isArray(data.rows)) {
        const map = new Map(data.rows.map(r => [String(r.DMSTAMP), r]));
        lastRows = lastRows.map(r => {
          const upd = map.get(String(r.DMSTAMP));
          return upd ? { ...r, ...upd } : r;
        });
        render(lastRows);
      }
    } catch (e) {
      alert(`Erro: ${e.message || e}`);
    } finally {
      btnCalcValores.disabled = false;
    }
  });
  async function emitirFaturacao(dmstamps) {
    const ids = (dmstamps || []).map(x => String(x || '').trim()).filter(Boolean);
    if (!ids.length) {
      alert('Não há registos elegíveis para faturar.');
      return;
    }
    if (!confirm(`Emitir ${ids.length} fatura(s) de gestão AL no PHC?`)) return;
    if (btnFaturacao) btnFaturacao.disabled = true;
    try {
      const res = await fetch('/api/processamento_mensal/faturar', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ dmstamps: ids })
      });
      const data = await res.json().catch(() => ({}));
      const created = Array.isArray(data.created) ? data.created : [];
      const errors = Array.isArray(data.errors) ? data.errors : [];
      if (!res.ok && data.error) throw new Error(data.error);
      if (errors.length) {
        alert(`Faturas emitidas: ${created.length}\nErros: ${errors.length}\n\n${errors.slice(0, 8).map(e => `${e.CLIENTE || e.DMSTAMP}: ${e.error}`).join('\n')}`);
      } else {
        alert(`Faturas emitidas: ${created.length}`);
      }
      await load();
    } catch (e) {
      alert(`Erro: ${e.message || e}`);
    } finally {
      if (btnFaturacao) btnFaturacao.disabled = invoiceEligibleRows().length === 0;
    }
  }
  btnFaturacao?.addEventListener('click', async () => {
    const ids = invoiceEligibleRows().map(r => String(r.DMSTAMP || '').trim()).filter(Boolean);
    await emitirFaturacao(ids);
  });
  btnAddClientes?.addEventListener('click', async () => {
    if (!clientesModal) return;
    const { ano, mes } = monthParams();
    clientesBody.innerHTML = '<tr><td colspan="4" class="text-muted p-3">A carregar...</td></tr>';
    if (selectAllEl) selectAllEl.checked = false;
    try {
      const res = await fetch(`/api/processamento_mensal/clientes_disponiveis?ano=${ano}&mes=${mes}`);
      const data = await res.json().catch(() => ({}));
      if (!res.ok || data.error) throw new Error(data.error || res.statusText);
      const rows = Array.isArray(data.rows) ? data.rows : [];
      if (!rows.length) {
        clientesBody.innerHTML = '<tr><td colspan="4" class="text-muted p-3">Sem clientes para adicionar.</td></tr>';
      } else {
        clientesBody.innerHTML = rows.map(r => `
          <tr data-no="${escapeHtml(r.NO)}" data-estab="${escapeHtml(r.CLESTAB ?? 0)}" data-nome="${escapeHtml(r.NOME)}">
            <td><input type="checkbox" class="form-check-input pm-cli"></td>
            <td>${escapeHtml(r.NO)}</td>
            <td>${escapeHtml(r.CLESTAB ?? 0)}</td>
            <td>${escapeHtml(r.NOME)}</td>
          </tr>
        `).join('');
        clientesBody.querySelectorAll('tr').forEach(tr => {
          tr.addEventListener('click', (e) => {
            if (e.target && e.target.tagName === 'INPUT') return;
            const cb = tr.querySelector('.pm-cli');
            if (cb) cb.checked = !cb.checked;
          });
        });
      }
      clientesModal.show();
    } catch (e) {
      alert(`Erro: ${e.message || e}`);
    }
  });
  selectAllEl?.addEventListener('change', () => {
    const all = Array.from(clientesBody.querySelectorAll('.pm-cli'));
    all.forEach(c => { c.checked = selectAllEl.checked; });
  });
  clientesSave?.addEventListener('click', async () => {
    const checks = Array.from(clientesBody.querySelectorAll('.pm-cli')).filter(c => c.checked);
    if (!checks.length) {
      clientesModal?.hide();
      return;
    }
    const { ano, mes } = monthParams();
    const items = checks.map(c => {
      const tr = c.closest('tr');
      return {
        no: tr?.getAttribute('data-no') || '',
        clestab: tr?.getAttribute('data-estab') || '0',
        nome: tr?.getAttribute('data-nome') || ''
      };
    });
    clientesSave.disabled = true;
    try {
      const res = await fetch('/api/processamento_mensal/add_clientes', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ano, mes, items })
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok || data.error) throw new Error(data.error || res.statusText);
      if (Array.isArray(data.rows) && data.rows.length) {
        lastRows = lastRows.concat(data.rows);
        render(lastRows);
      }
      clientesModal?.hide();
    } catch (e) {
      alert(`Erro: ${e.message || e}`);
    } finally {
      clientesSave.disabled = false;
    }
  });
  async function openDrill(stamp, type) {
    if (!stamp || !drillModal) return;
    drillTitle.textContent = type === 'comissoes' ? 'Detalhe Comissões' : 'Detalhe Imputações';
    drillHead.innerHTML = '';
    drillBody.innerHTML = '<tr><td class="text-muted p-3">A carregar...</td></tr>';
    if (drillFoot) drillFoot.innerHTML = '';
    if (drillFilter) drillFilter.classList.add('is-hidden');
    if (drillAlojamento) drillAlojamento.innerHTML = '<option value="">Todos</option>';
    const fmtNum = (v) => {
      const n = Number(v);
      if (!Number.isFinite(n)) return (v ?? '').toString();
      return n.toFixed(2);
    };
    const fmtDate = (v) => {
      if (!v) return '';
      const d = new Date(v);
      if (Number.isNaN(d.getTime())) return (v ?? '').toString();
      return d.toISOString().slice(0, 10);
    };
    try {
      const res = await fetch(`/api/processamento_mensal/drilldown?stamp=${encodeURIComponent(stamp)}&type=${encodeURIComponent(type)}`);
      const data = await res.json().catch(() => ({}));
      if (!res.ok || data.error) throw new Error(data.error || res.statusText);
      const cols = data.columns || [];
      const rows = data.rows || [];
      currentDrill = { type, columns: cols, rows };
      setupDrillFilter(type, rows);
      renderDrillTable();
      drillModal.show();
    } catch (e) {
      alert(`Erro: ${e.message || e}`);
    }
  }

  function setupDrillFilter(type, rows) {
    if (!drillFilter || !drillAlojamento) return;
    if (type !== 'comissoes') {
      drillFilter.classList.add('is-hidden');
      drillAlojamento.innerHTML = '<option value="">Todos</option>';
      return;
    }
    const alojamentos = [...new Set(rows.map(r => (r.ALOJAMENTO ?? '').toString().trim()).filter(Boolean))]
      .sort((a, b) => a.localeCompare(b, 'pt', { sensitivity: 'base' }));
    drillAlojamento.innerHTML = '<option value="">Todos</option>' + alojamentos
      .map(a => `<option value="${escapeHtml(a)}">${escapeHtml(a)}</option>`)
      .join('');
    drillFilter.classList.remove('is-hidden');
  }

  function drillRowsForFilter() {
    const rows = currentDrill.rows || [];
    if (currentDrill.type !== 'comissoes') return rows;
    const selected = (drillAlojamento?.value || '').toString().trim();
    if (!selected) return rows;
    return rows.filter(r => (r.ALOJAMENTO ?? '').toString().trim() === selected);
  }

  function renderDrillTable() {
    const cols = currentDrill.columns || [];
    const rows = drillRowsForFilter();
    const fmtNum = (v) => {
      const n = Number(v);
      if (!Number.isFinite(n)) return (v ?? '').toString();
      return n.toFixed(2);
    };
    const fmtDate = (v) => {
      if (!v) return '';
      const d = new Date(v);
      if (Number.isNaN(d.getTime())) return (v ?? '').toString();
      return d.toISOString().slice(0, 10);
    };

      drillHead.innerHTML = cols.map(c => `<th>${escapeHtml(c)}</th>`).join('');
      if (!rows.length) {
        drillBody.innerHTML = `<tr><td class="text-muted p-3" colspan="${cols.length || 1}">Sem dados.</td></tr>`;
        if (drillFoot) drillFoot.innerHTML = '';
      } else {
        drillBody.innerHTML = rows.map(r => `
          <tr class="${String(r.ESTADO || '').toLowerCase().includes('cancel') ? 'pm-cancel' : ''}">
            ${cols.map(c => {
              const key = (c || '').toUpperCase();
              const val = r[c];
              if (key.includes('DATA')) return `<td>${escapeHtml(fmtDate(val))}</td>`;
              if (['ESTADIA','LIMPEZA','COMISSAO','COMISSAO_PERC','VALOR','PCANCEL'].includes(key)) {
                const txt = fmtNum(val);
                const suf = key === 'COMISSAO_PERC' ? '%' : '';
                const strike = (String(r.ESTADO || '').toLowerCase().includes('cancel') && ['ESTADIA','LIMPEZA','COMISSAO'].includes(key)) ? ' pm-strike' : '';
                return `<td class="text-end${strike}">${escapeHtml(txt + suf)}</td>`;
              }
              if (key === 'ORIGEM') {
                return `<td><span class="pm-origin-badge">${escapeHtml((val ?? '').toString())}</span></td>`;
              }
              if (key === 'RESERVA') {
                const code = (val ?? '').toString().trim();
                const origem = (r.ORIGEM ?? '').toString().trim().toLowerCase();
                if (code && origem.includes('airbnb')) {
                  const href = `https://www.airbnb.pt/hosting/stay/${encodeURIComponent(code)}`;
                  return `<td class="pm-drill-text" title="${escapeHtml(code)}"><a class="pm-reservation-link" href="${escapeHtml(href)}" target="_blank" rel="noopener noreferrer">${escapeHtml(code)}</a></td>`;
                }
                return `<td class="pm-drill-text" title="${escapeHtml(code)}">${escapeHtml(code)}</td>`;
              }
              if (['DOCUMENTO','FORNECEDOR','ALOJAMENTO','DESCRICAO'].includes(key)) {
                const text = (val ?? '').toString();
                const cls = key === 'DESCRICAO' ? ' pm-drill-description' : '';
                return `<td class="pm-drill-text${cls}" title="${escapeHtml(text)}">${escapeHtml(text)}</td>`;
              }
              if (key === 'NO' || key === 'CLIENTE') {
                return `<td>${escapeHtml((val ?? '').toString())}</td>`;
              }
              return `<td>${escapeHtml((val ?? '').toString())}</td>`;
            }).join('')}
          </tr>
        `).join('');
        if (drillFoot) {
          const numericCols = new Set(['ESTADIA','LIMPEZA','COMISSAO','VALOR','PCANCEL']);
          const totals = {};
          rows.forEach(r => {
            const isCancel = String(r.ESTADO || '').toLowerCase().includes('cancel');
            cols.forEach(c => {
              const key = (c || '').toUpperCase();
              if (!numericCols.has(key)) return;
              if (isCancel && ['ESTADIA','LIMPEZA','COMISSAO'].includes(key)) return;
              const rawValue = key === 'VALOR' && r.VALOR_RAW !== undefined && r.VALOR_RAW !== null ? r.VALOR_RAW : r[c];
              const n = Number(rawValue || 0);
              totals[key] = (totals[key] || 0) + (Number.isFinite(n) ? n : 0);
            });
          });
          drillFoot.innerHTML = cols.map((c, idx) => {
            const key = (c || '').toUpperCase();
            if (idx === 0) return '<th class="text-end">Totais</th>';
            if (numericCols.has(key)) {
              const txt = fmtNum(totals[key] || 0);
              return `<th class="text-end">${escapeHtml(txt)}</th>`;
            }
            return '<th></th>';
          }).join('');
        }
      }
  }

  drillAlojamento?.addEventListener('change', renderDrillTable);

  load();
});
