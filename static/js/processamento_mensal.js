document.addEventListener('DOMContentLoaded', () => {
  const body = document.getElementById('pmBody');
  const label = document.getElementById('pmMonthLabel');
  const countEl = document.getElementById('pmCount');
  const btnPrev = document.getElementById('pmPrev');
  const btnNext = document.getElementById('pmNext');
  const btnAddClientes = document.getElementById('pmAddClientes');
  const btnCalcValores = document.getElementById('pmCalcValores');
  const btnFetch = document.getElementById('pmFetchDossiers');
  const clientesModalEl = document.getElementById('pmClientesModal');
  const clientesBody = document.getElementById('pmClientesBody');
  const clientesSave = document.getElementById('pmAddClientesSave');
  const selectAllEl = document.getElementById('pmSelectAll');
  const clientesModal = clientesModalEl ? new bootstrap.Modal(clientesModalEl) : null;
  const fModalEl = document.getElementById('pmFaturaModal');
  const fNumEl = document.getElementById('pmFaturaNum');
  const fValEl = document.getElementById('pmFaturaVal');
  const fPerEl = document.getElementById('pmFaturaPer');
  const fTargetEl = document.getElementById('pmFaturaTarget');
  const fHintEl = document.getElementById('pmFaturaHint');
  const fSaveBtn = document.getElementById('pmFaturaSave');
  const fModal = fModalEl ? new bootstrap.Modal(fModalEl) : null;
  let currentStamp = '';
  let lastRows = [];
  const drillModalEl = document.getElementById('pmDrillModal');
  const drillTitle = document.getElementById('pmDrillTitle');
  const drillHead = document.getElementById('pmDrillHead');
  const drillBody = document.getElementById('pmDrillBody');
  const drillFoot = document.getElementById('pmDrillFoot');
  const drillModal = drillModalEl ? new bootstrap.Modal(drillModalEl) : null;

  let cur = new Date();
  cur.setDate(1);

  const fmtMonth = new Intl.DateTimeFormat('pt-PT', { month: 'long', year: 'numeric' });

  const escapeHtml = (s) => (s ?? '').toString()
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#039;');

  function setLabel() {
    if (label) label.textContent = fmtMonth.format(cur);
  }

  function monthParams() {
    return { ano: cur.getFullYear(), mes: cur.getMonth() + 1 };
  }

  function render(rows) {
    if (!body) return;
    let totalDos = 0;
    let totalFat = 0;
    if (!rows.length) {
      body.innerHTML = '<tr><td colspan="13" class="text-muted p-3">Sem registos.</td></tr>';
      if (countEl) countEl.textContent = '0 registos';
      const td = document.getElementById('pmTotalDossier');
      const tf = document.getElementById('pmTotalFatura');
      if (td) td.textContent = '0.00';
      if (tf) tf.textContent = '0.00';
      return;
    }
    body.innerHTML = rows.map(r => {
      const ftfile = (r.FTFILE || '').toString().trim();
      let webFile = '';
      if (ftfile) {
        const m = ftfile.replace(/\//g, '\\').match(/\\static\\images\\(.+)$/i);
        if (m && m[1]) {
          webFile = `https://hfsalves.mooo.com/static/images/${m[1].replace(/\\/g, '/')}`;
        } else if (/^https?:\/\//i.test(ftfile)) {
          webFile = ftfile;
        }
      }
      const fileLink = webFile ? `<a class="pm-file" href="${escapeHtml(webFile)}" target="_blank" rel="noopener">PDF</a>` : '';
      const enviado = Number(r.ENVIADO || 0) === 1;
      const boVal = Number(r.BOVALOR || 0);
      const ftVal = Number(r.FTVALOR || 0);
      totalDos += boVal;
      totalFat += ftVal;
      const isDiff = Number(r.BOVALOR || 0) !== Number(r.FTVALOR || 0);
      const canDelete = !r.FATURATG && !r.DOSSIER;
      const com = Number(r.COMISSOES || 0);
      const imp = Number(r.IMPUTACOES || 0);
      const tot = Number(r.TOTAL || 0);
      const totIva = tot * 1.23;
      const bo = Number(r.BOVALOR || 0);
      const ft = Number(r.FTVALOR || 0);
      const ti = Number(totIva.toFixed(2));
      const lineOk = bo > 0 && ft > 0 && ti > 0 && bo === ft && bo === ti;
      return `
        <tr data-stamp="${escapeHtml(r.DMSTAMP || '')}" class="${lineOk ? 'pm-ok' : ''}">
          <td>${escapeHtml(r.NO)}</td>
          <td title="${escapeHtml(r.NOME)}">${escapeHtml(r.NOME)}</td>
          <td class="text-end"><span class="pm-cell-link pm-comm" data-stamp="${escapeHtml(r.DMSTAMP || '')}">${escapeHtml(com.toFixed(2))}</span></td>
          <td class="text-end"><span class="pm-cell-link pm-imp" data-stamp="${escapeHtml(r.DMSTAMP || '')}">${escapeHtml(imp.toFixed(2))}</span></td>
          <td class="text-end">${escapeHtml(tot.toFixed(2))}</td>
          <td class="text-end">${escapeHtml(totIva.toFixed(2))}</td>
          <td title="${escapeHtml(r.DOSSIER)}">${escapeHtml(r.DOSSIER)}</td>
          <td class="text-end ${isDiff ? 'pm-diff' : ''}">
            ${escapeHtml(Number(r.BOVALOR || 0).toFixed(2))}
          </td>
          <td title="${escapeHtml(r.FATURATG)}">
            ${r.FATURATG ? `<div class="pm-fatura-link" data-stamp="${escapeHtml(r.DMSTAMP || '')}">${escapeHtml(r.FATURATG)}</div>` : ''}
            ${(!r.FATURATG && r.DOSSIER) ? '<div class="pm-missing">Fatura não encontrada</div>' : ''}
            ${isDiff && !!r.FATURATG ? '<div class="pm-flag">Valor Errado</div>' : ''}
          </td>
          <td class="text-end ${isDiff ? 'pm-diff' : ''}">
            ${escapeHtml(Number(r.FTVALOR || 0).toFixed(2))}
          </td>
          <td>${fileLink}</td>
          <td><span class="pm-badge ${enviado ? 'y' : 'n'}">${enviado ? 'Sim' : 'Não'}</span></td>
          <td>${canDelete ? '<button class="pm-del" title="Eliminar"><i class="fa-solid fa-trash"></i></button>' : ''}</td>
        </tr>
      `;
    }).join('');
    if (countEl) countEl.textContent = `${rows.length} registo(s)`;
    const td = document.getElementById('pmTotalDossier');
    const tf = document.getElementById('pmTotalFatura');
    if (td) td.textContent = totalDos.toFixed(2);
    if (tf) tf.textContent = totalFat.toFixed(2);

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

    body.querySelectorAll('.pm-fatura-link').forEach(el => {
      el.addEventListener('click', async () => {
        const stamp = el.getAttribute('data-stamp') || '';
        if (!stamp || !fModal) return;
        currentStamp = stamp;
        fTargetEl.innerHTML = '';
        fHintEl.textContent = '';
        fSaveBtn.disabled = true;
        try {
          const res = await fetch(`/api/processamento_mensal/fatura_info?stamp=${encodeURIComponent(stamp)}`);
          const data = await res.json().catch(() => ({}));
          if (!res.ok || data.error) throw new Error(data.error || res.statusText);
          fNumEl.textContent = data.fatura || '';
          fValEl.textContent = data.valor || '';
          fPerEl.textContent = data.periodo || '';
          const options = (data.targets || []).map(t => `<option value="${escapeHtml(t.stamp)}">${escapeHtml(t.label)}</option>`).join('');
          fTargetEl.innerHTML = options || '<option value="">(sem períodos disponíveis)</option>';
          fSaveBtn.disabled = !options;
          fHintEl.textContent = options ? '' : 'Não existem períodos sem fatura para este cliente.';
          fModal.show();
        } catch (e) {
          alert(`Erro: ${e.message || e}`);
        }
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
    body.innerHTML = '<tr><td colspan="13" class="text-muted p-3">A carregar...</td></tr>';
    const res = await fetch(`/api/processamento_mensal?ano=${ano}&mes=${mes}`);
    const data = await res.json().catch(() => ({}));
    if (!res.ok || data.error) {
      body.innerHTML = `<tr><td colspan="13" class="text-danger p-3">Erro: ${escapeHtml(data.error || res.statusText)}</td></tr>`;
      return;
    }
    lastRows = Array.isArray(data.rows) ? data.rows : [];
    render(lastRows);
  }

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
  btnAddClientes?.addEventListener('click', async () => {
    if (!clientesModal) return;
    const { ano, mes } = monthParams();
    clientesBody.innerHTML = '<tr><td colspan="3" class="text-muted p-3">A carregar...</td></tr>';
    if (selectAllEl) selectAllEl.checked = false;
    try {
      const res = await fetch(`/api/processamento_mensal/clientes_disponiveis?ano=${ano}&mes=${mes}`);
      const data = await res.json().catch(() => ({}));
      if (!res.ok || data.error) throw new Error(data.error || res.statusText);
      const rows = Array.isArray(data.rows) ? data.rows : [];
      if (!rows.length) {
        clientesBody.innerHTML = '<tr><td colspan="3" class="text-muted p-3">Sem clientes para adicionar.</td></tr>';
      } else {
        clientesBody.innerHTML = rows.map(r => `
          <tr data-no="${escapeHtml(r.NO)}" data-nome="${escapeHtml(r.NOME)}">
            <td><input type="checkbox" class="form-check-input pm-cli"></td>
            <td>${escapeHtml(r.NO)}</td>
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
      return { no: tr?.getAttribute('data-no') || '', nome: tr?.getAttribute('data-nome') || '' };
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
  btnFetch?.addEventListener('click', async () => {
    const { ano, mes } = monthParams();
    btnFetch.disabled = true;
    try {
      const res = await fetch('/api/processamento_mensal/fetch_dossier', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ano, mes })
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok || data.error) throw new Error(data.error || res.statusText);
      await load();
    } catch (e) {
      alert(`Erro: ${e.message || e}`);
    } finally {
      btnFetch.disabled = false;
    }
  });

  fSaveBtn?.addEventListener('click', async () => {
    const target = fTargetEl?.value || '';
    if (!currentStamp || !target) return;
    fSaveBtn.disabled = true;
    try {
      const res = await fetch('/api/processamento_mensal/mover_fatura', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ from_stamp: currentStamp, to_stamp: target })
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok || data.error) throw new Error(data.error || res.statusText);
      fModal?.hide();
      await load();
    } catch (e) {
      alert(`Erro: ${e.message || e}`);
    } finally {
      fSaveBtn.disabled = false;
    }
  });

  async function openDrill(stamp, type) {
    if (!stamp || !drillModal) return;
    drillTitle.textContent = type === 'comissoes' ? 'Detalhe Comissões' : 'Detalhe Imputações';
    drillHead.innerHTML = '';
    drillBody.innerHTML = '<tr><td class="text-muted p-3">A carregar...</td></tr>';
    if (drillFoot) drillFoot.innerHTML = '';
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
              if (isCancel && ['ESTADIA','LIMPEZA','COMISSAO','VALOR'].includes(key)) return;
              const n = Number(r[c] || 0);
              totals[key] = (totals[key] || 0) + (Number.isFinite(n) ? n : 0);
            });
            if (isCancel) {
              const pc = Number(r.PCANCEL || 0);
              totals.VALOR = (totals.VALOR || 0) + (Number.isFinite(pc) ? pc : 0);
            }
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
      drillModal.show();
    } catch (e) {
      alert(`Erro: ${e.message || e}`);
    }
  }

  load();
});
