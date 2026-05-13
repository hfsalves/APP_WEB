(function () {
  const state = {
    ano: Number(window.INVM_ANO_INICIAL || new Date().getFullYear()),
    mes: Number(window.INVM_MES_INICIAL || (new Date().getMonth() + 1)),
    rows: [],
    current: null,
    recalcPending: false,
  };

  const els = {
    ano: document.getElementById('invmAno'),
    mes: document.getElementById('invmMes'),
    ccusto: document.getElementById('invmCcusto'),
    q: document.getElementById('invmQ'),
    pesquisar: document.getElementById('invmPesquisar'),
    limpar: document.getElementById('invmLimpar'),
    resumo: document.getElementById('invmResumo'),
    body: document.getElementById('invmBody'),
    modalEl: document.getElementById('invmModal'),
    warn: document.getElementById('invmWarn'),
    invstamp: document.getElementById('invmInvstamp'),
    descr: document.getElementById('invmDescr'),
    ccustoInv: document.getElementById('invmCCUSTO'),
    valorTotal: document.getElementById('invmValorTotal'),
    datainv: document.getElementById('invmDataInv'),
    dataini: document.getElementById('invmDataIni'),
    meses: document.getElementById('invmMeses'),
    obs: document.getElementById('invmObs'),
    linesBody: document.getElementById('invmLinesBody'),
    mapBody: document.getElementById('invmMapBody'),
    btnRecalc: document.getElementById('invmRecalc'),
    btnSave: document.getElementById('invmSave'),
    btnDelete: document.getElementById('invmDelete'),
  };

  let modalInstance = null;
  function getModal() {
    if (!els.modalEl) return null;
    if (modalInstance) return modalInstance;
    if (window.bootstrap?.Modal) {
      modalInstance = new window.bootstrap.Modal(els.modalEl);
      return modalInstance;
    }
    return null;
  }

  const esc = (v) => String(v ?? '').replace(/[&<>"']/g, (m) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[m]));
  const fmtMoney = (v) => Number(v || 0).toLocaleString('pt-PT', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  const fmtDate = (iso) => {
    const s = String(iso || '').trim();
    return /^\d{4}-\d{2}-\d{2}$/.test(s) ? `${s.slice(8, 10)}/${s.slice(5, 7)}/${s.slice(0, 4)}` : '';
  };
  const firstDay = (iso) => {
    const d = /^\d{4}-\d{2}-\d{2}$/.test(String(iso || '')) ? new Date(`${iso}T00:00:00`) : new Date();
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-01`;
  };
  const addMonthsFirstDay = (iso, add) => {
    const base = /^\d{4}-\d{2}-\d{2}$/.test(String(iso || '')) ? new Date(`${iso}T00:00:00`) : new Date();
    const d = new Date(base.getFullYear(), base.getMonth() + Number(add || 0), 1);
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-01`;
  };

  function setWarn(message, level = 'warning') {
    if (!els.warn) return;
    if (!message) {
      els.warn.className = 'sz_invm_warn sz_invm_warn_hidden';
      els.warn.textContent = '';
      return;
    }
    els.warn.className = `sz_invm_warn sz_invm_warn_${level}`;
    els.warn.textContent = message;
  }

  function updateResumo() {
    if (!els.resumo) return;
    els.resumo.textContent = `${state.rows.length} investimentos`;
  }

  function buildFilters() {
    const qs = new URLSearchParams();
    const anoVal = String(els.ano?.value || '').trim();
    const mesVal = String(els.mes?.value || '').trim();
    const ccVal = String(els.ccusto?.value || '').trim();
    const qVal = String(els.q?.value || '').trim();
    if (anoVal) qs.set('ano', anoVal);
    if (mesVal) qs.set('mes', mesVal);
    if (ccVal) qs.set('ccusto', ccVal);
    if (qVal) qs.set('q', qVal);
    return qs;
  }

  function renderList() {
    if (!els.body) return;
    if (!state.rows.length) {
      els.body.innerHTML = '<tr><td colspan="8" class="sz_table_cell sz_text_muted p-3">Sem investimentos para os filtros aplicados.</td></tr>';
      updateResumo();
      return;
    }
    els.body.innerHTML = state.rows.map((r) => `
      <tr data-stamp="${esc(r.INVSTAMP)}">
        <td>${esc(r.INVSTAMP)}</td>
        <td>${esc(fmtDate(r.DATAINV))}</td>
        <td>${esc(fmtDate(r.DATAINI))}</td>
        <td>${esc(r.CCUSTO)}</td>
        <td>${esc(r.DESCR)}</td>
        <td class="text-end">${Number(r.MESES || 0)}</td>
        <td class="text-end">${fmtMoney(r.VALORTOTAL)}</td>
        <td>${esc(r.CRIADOEM || '')}</td>
      </tr>
    `).join('');
    els.body.querySelectorAll('tr[data-stamp]').forEach((tr) => {
      tr.addEventListener('click', () => openDetail(tr.getAttribute('data-stamp') || ''));
    });
    updateResumo();
  }

  async function loadList() {
    if (els.body) {
      els.body.innerHTML = '<tr><td colspan="8" class="sz_table_cell sz_text_muted p-3">A carregar...</td></tr>';
    }
    try {
      const res = await fetch(`/api/investimentos/lista?${buildFilters().toString()}`);
      const data = await res.json().catch(() => ({}));
      if (!res.ok || data.error) throw new Error(data.error || 'Erro ao carregar investimentos');
      state.rows = Array.isArray(data.rows) ? data.rows : [];
      renderList();
    } catch (e) {
      state.rows = [];
      if (els.body) els.body.innerHTML = `<tr><td colspan="8" class="sz_table_cell sz_invm_error p-3">${esc(e.message || 'Erro')}</td></tr>`;
      updateResumo();
    }
  }

  function buildCalculatedLines() {
    const total = Number(state.current?.header?.VALORTOTAL || 0);
    const meses = Math.max(1, Number(els.meses?.value || 1));
    const dataIni = firstDay(els.dataini?.value || state.current?.header?.DATAINI || '');
    const descr = String(els.descr?.value || '').trim();
    const ccusto = String(state.current?.header?.CCUSTO || '');
    const totalCents = Math.round(total * 100);
    const baseCents = Math.floor(totalCents / meses);
    const rem = totalCents - baseCents * meses;
    const rows = [];
    for (let i = 0; i < meses; i += 1) {
      let cents = baseCents;
      if (i === meses - 1) cents += rem;
      rows.push({
        NUM: i + 1,
        DATAREF: addMonthsFirstDay(dataIni, i),
        CCUSTO: ccusto,
        DESCR: descr,
        VALOR: Number((cents / 100).toFixed(2)),
      });
    }
    return rows;
  }

  function renderLines(rows) {
    if (!els.linesBody) return;
    if (!rows.length) {
      els.linesBody.innerHTML = '<tr><td colspan="5" class="sz_table_cell sz_text_muted p-2">Sem linhas.</td></tr>';
      return;
    }
    els.linesBody.innerHTML = rows.map((ln, idx) => `
      <tr>
        <td>${idx + 1}</td>
        <td>${esc(fmtDate(ln.DATAREF))}</td>
        <td>${esc(ln.CCUSTO || '')}</td>
        <td>${esc(ln.DESCR || '')}</td>
        <td class="text-end">${fmtMoney(ln.VALOR)}</td>
      </tr>
    `).join('');
  }

  function renderMap(rows) {
    if (!els.mapBody) return;
    if (!rows.length) {
      els.mapBody.innerHTML = '<tr><td colspan="6" class="sz_table_cell sz_text_muted p-2">Sem custos de origem.</td></tr>';
      return;
    }
    els.mapBody.innerHTML = rows.map((ln) => `
      <tr>
        <td>${esc(fmtDate(ln.DATA))}</td>
        <td>${esc(ln.CCUSTO || '')}</td>
        <td>${esc(ln.FAMILIA || '')}</td>
        <td>${esc(ln.DESCR || '')}</td>
        <td class="text-end">${fmtMoney(ln.VALOR)}</td>
        <td>${esc(ln.CUSTOSTAMP || '')}</td>
      </tr>
    `).join('');
  }

  function fillModal(data) {
    const h = data.header || {};
    state.current = data;
    state.recalcPending = false;
    if (els.invstamp) els.invstamp.value = h.INVSTAMP || '';
    if (els.descr) els.descr.value = h.DESCR || '';
    if (els.ccustoInv) els.ccustoInv.value = h.CCUSTO || '';
    if (els.valorTotal) els.valorTotal.value = fmtMoney(h.VALORTOTAL || 0);
    if (els.datainv) els.datainv.value = h.DATAINV || '';
    if (els.dataini) els.dataini.value = h.DATAINI || '';
    if (els.meses) els.meses.value = String(h.MESES || 0);
    if (els.obs) els.obs.value = h.OBS || '';

    [els.descr, els.datainv, els.dataini, els.meses, els.obs].forEach((el) => {
      if (el) el.disabled = false;
    });
    if (els.btnSave) els.btnSave.disabled = false;
    if (els.btnRecalc) els.btnRecalc.disabled = false;

    renderLines(Array.isArray(data.linhas) ? data.linhas : []);
    renderMap(Array.isArray(data.origem) ? data.origem : []);

    const c = data.consistencia || {};
    const warnings = [];
    if (!c.origem_ok) warnings.push(`INVMAP (${fmtMoney(c.sum_origem)}) difere de VALORTOTAL (${fmtMoney(c.valortotal)}).`);
    if (!c.linhas_ok) warnings.push(`INVL (${fmtMoney(c.sum_linhas)}) ou nº de linhas difere de VALORTOTAL/MESES.`);
    if (warnings.length) {
      setWarn(warnings.join(' '), 'danger');
    } else {
      setWarn('');
    }
  }

  async function openDetail(stamp) {
    const invstamp = String(stamp || '').trim();
    if (!invstamp) return;
    setWarn('');
    const modal = getModal();
    if (!modal) {
      alert('Não foi possível abrir o modal.');
      return;
    }
    modal.show();
    if (els.linesBody) els.linesBody.innerHTML = '<tr><td colspan="5" class="sz_table_cell sz_text_muted p-2">A carregar...</td></tr>';
    if (els.mapBody) els.mapBody.innerHTML = '<tr><td colspan="6" class="sz_table_cell sz_text_muted p-2">A carregar...</td></tr>';
    try {
      const res = await fetch(`/api/investimentos/${encodeURIComponent(invstamp)}`);
      const data = await res.json().catch(() => ({}));
      if (!res.ok || data.error) throw new Error(data.error || 'Erro ao carregar investimento');
      fillModal(data);
    } catch (e) {
      setWarn(e.message || 'Erro ao carregar investimento', 'danger');
    }
  }

  function onRecalc() {
    if (!state.current) return;
    renderLines(buildCalculatedLines());
    state.recalcPending = true;
    setWarn('Linhas recalculadas localmente. Grave para aplicar na base de dados.', 'info');
  }

  async function onSave() {
    if (!state.current?.header?.INVSTAMP) return;
    const payload = {
      header: {
        DESCR: String(els.descr?.value || '').trim(),
        DATAINV: String(els.datainv?.value || '').trim(),
        DATAINI: String(els.dataini?.value || '').trim(),
        MESES: Number(els.meses?.value || 0),
        OBS: String(els.obs?.value || '').trim(),
      },
      recalc_lines: !!state.recalcPending,
    };
    if (!payload.header.DESCR) return alert('DESCR é obrigatória.');
    if (!payload.header.DATAINV || !payload.header.DATAINI) return alert('Preenche DATAINV e DATAINI.');
    if (!(payload.header.MESES > 0)) return alert('MESES tem de ser maior que zero.');

    const stamp = state.current.header.INVSTAMP;
    if (els.btnSave) els.btnSave.disabled = true;
    try {
      const res = await fetch(`/api/investimentos/${encodeURIComponent(stamp)}/save`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok || data.error) throw new Error(data.error || 'Erro ao gravar investimento');
      await openDetail(stamp);
      await loadList();
      alert('Investimento gravado com sucesso.');
    } catch (e) {
      setWarn(e.message || 'Erro ao gravar investimento', 'danger');
    } finally {
      if (els.btnSave) els.btnSave.disabled = false;
    }
  }

  async function onDelete() {
    const stamp = String(state.current?.header?.INVSTAMP || '').trim();
    if (!stamp) return;
    const ok = confirm('Tem a certeza que quer eliminar este investimento? Esta ação remove cabeçalho, linhas e mapeamento de custos.');
    if (!ok) return;
    if (els.btnDelete) els.btnDelete.disabled = true;
    try {
      const res = await fetch(`/api/investimentos/${encodeURIComponent(stamp)}/delete`, { method: 'POST' });
      const data = await res.json().catch(() => ({}));
      if (!res.ok || data.error) throw new Error(data.error || 'Erro ao eliminar investimento');
      getModal()?.hide();
      await loadList();
      alert('Investimento eliminado.');
    } catch (e) {
      setWarn(e.message || 'Erro ao eliminar investimento', 'danger');
    } finally {
      if (els.btnDelete) els.btnDelete.disabled = false;
    }
  }

  function onClearFilters() {
    if (els.ano) els.ano.value = '';
    if (els.mes) els.mes.value = '';
    if (els.ccusto) els.ccusto.value = '';
    if (els.q) els.q.value = '';
    loadList();
  }

  els.pesquisar?.addEventListener('click', loadList);
  els.limpar?.addEventListener('click', onClearFilters);
  els.btnRecalc?.addEventListener('click', onRecalc);
  els.btnSave?.addEventListener('click', onSave);
  els.btnDelete?.addEventListener('click', onDelete);
  els.q?.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') loadList();
  });

  if (els.mes && !els.mes.value) els.mes.value = String(state.mes);
  if (els.ano && !els.ano.value) els.ano.value = String(state.ano);
  loadList();
})();
