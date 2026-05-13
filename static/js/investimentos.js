(function () {
  const state = {
    ano: Number(window.INV_ANO_INICIAL || new Date().getFullYear()),
    mes: Number(window.INV_MES_INICIAL || (new Date().getMonth() + 1)),
    excluirGestao: true,
    rows: [],
    selected: new Set(),
  };

  const els = {
    ano: document.getElementById('invAno'),
    mes: document.getElementById('invMes'),
    excluiGestao: document.getElementById('invExcluiGestao'),
    body: document.getElementById('invBody'),
    resumo: document.getElementById('invResumoSel'),
    criarBtn: document.getElementById('invCriarBtn'),
    modalEl: document.getElementById('invCreateModal'),
    descr: document.getElementById('invDescr'),
    ccusto: document.getElementById('invCcusto'),
    datainv: document.getElementById('invDataInv'),
    dataini: document.getElementById('invDataIni'),
    meses: document.getElementById('invMeses'),
    valortotal: document.getElementById('invValorTotal'),
    obs: document.getElementById('invObs'),
    previewBody: document.getElementById('invPreviewBody'),
    recalcBtn: document.getElementById('invRecalcBtn'),
    saveBtn: document.getElementById('invSaveBtn'),
    selInfo: document.getElementById('invSelInfo'),
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

  const fmtMoney = (v) => Number(v || 0).toLocaleString('pt-PT', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  const escapeHtml = (s) => String(s || '').replace(/[&<>"']/g, (m) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[m]));
  const isoToDmy = (iso) => {
    const v = String(iso || '').trim();
    return /^\d{4}-\d{2}-\d{2}$/.test(v) ? `${v.slice(8, 10)}/${v.slice(5, 7)}/${v.slice(0, 4)}` : '';
  };
  const todayIso = () => new Date().toISOString().slice(0, 10);
  const firstDayIso = (y, m) => `${String(y).padStart(4, '0')}-${String(m).padStart(2, '0')}-01`;

  function rowKey(row) {
    return `${String(row?.ORIGEM || '').trim()}|${String(row?.CABSTAMP || '').trim()}|${String(row?.STAMP || '').trim()}`;
  }

  function selectedRows() {
    return state.rows.filter((r) => state.selected.has(rowKey(r)));
  }

  function selectedCcusto() {
    const rows = selectedRows();
    return rows.length ? String(rows[0].CCUSTO || '').trim() : '';
  }

  function selectedTotal() {
    return selectedRows().reduce((acc, r) => acc + Number(r.VALOR || 0), 0);
  }

  function updateSummary() {
    const rows = selectedRows();
    const total = selectedTotal();
    const cc = selectedCcusto();
    const base = `${rows.length} custos selecionados - Total: ${fmtMoney(total)} €`;
    if (els.resumo) els.resumo.textContent = cc ? `${base} (${cc})` : base;
    if (els.criarBtn) els.criarBtn.disabled = rows.length === 0;
  }

  function renderRows() {
    if (!els.body) return;
    if (!state.rows.length) {
      els.body.innerHTML = '<tr><td colspan="6" class="sz_table_cell sz_text_muted p-3">Sem custos elegíveis no período.</td></tr>';
      updateSummary();
      return;
    }

    els.body.innerHTML = state.rows.map((r) => {
      const key = rowKey(r);
      const checked = state.selected.has(key) ? 'checked' : '';
      const rowClass = state.selected.has(key) ? 'invp-row-selected' : '';
      return `
        <tr class="${rowClass}" data-key="${escapeHtml(key)}">
          <td class="text-center"><input type="checkbox" class="invp-check" ${checked}></td>
          <td>${escapeHtml(isoToDmy(r.DATA))}</td>
          <td>${escapeHtml(r.CCUSTO || '')}</td>
          <td>${escapeHtml(r.FAMILIA || '')}</td>
          <td>${escapeHtml(r.DESCR || '')}</td>
          <td class="text-end">${fmtMoney(r.VALOR)}</td>
        </tr>
      `;
    }).join('');

    els.body.querySelectorAll('tr[data-key]').forEach((tr) => {
      const key = String(tr.getAttribute('data-key') || '');
      const row = state.rows.find((r) => rowKey(r) === key);
      const ck = tr.querySelector('.invp-check');
      if (!row || !ck) return;
      ck.addEventListener('change', () => {
        const rowCcusto = String(row.CCUSTO || '').trim();
        const currentCcusto = selectedCcusto();
        if (ck.checked) {
          if (currentCcusto && rowCcusto && currentCcusto !== rowCcusto) {
            ck.checked = false;
            alert(`Só podes selecionar custos do mesmo CCUSTO.\nAtual: ${currentCcusto}\nTentativa: ${rowCcusto}`);
            return;
          }
          state.selected.add(key);
          tr.classList.add('invp-row-selected');
        } else {
          state.selected.delete(key);
          tr.classList.remove('invp-row-selected');
        }
        updateSummary();
      });
    });

    updateSummary();
  }

  async function loadRows() {
    const ano = Number(els.ano?.value || state.ano || new Date().getFullYear());
    const mes = Number(els.mes?.value || state.mes || (new Date().getMonth() + 1));
    const excluirGestao = !!els.excluiGestao?.checked;
    state.ano = Number.isFinite(ano) ? ano : new Date().getFullYear();
    state.mes = Math.max(1, Math.min(12, Number.isFinite(mes) ? mes : (new Date().getMonth() + 1)));
    state.excluirGestao = excluirGestao;
    if (els.ano) els.ano.value = String(state.ano);
    if (els.mes) els.mes.value = String(state.mes);

    if (els.body) els.body.innerHTML = '<tr><td colspan="6" class="sz_table_cell sz_text_muted p-3">A carregar...</td></tr>';
    try {
      const qs = new URLSearchParams({
        ano: String(state.ano),
        mes: String(state.mes),
        exclude_gestao: state.excluirGestao ? '1' : '0'
      });
      const res = await fetch(`/api/investimentos/custos?${qs.toString()}`);
      const data = await res.json().catch(() => ({}));
      if (!res.ok || data.error) throw new Error(data.error || 'Erro ao carregar custos');
      state.rows = Array.isArray(data.rows) ? data.rows : [];
      const validKeys = new Set(state.rows.map((r) => rowKey(r)));
      state.selected = new Set([...state.selected].filter((k) => validKeys.has(k)));
      renderRows();
    } catch (e) {
      if (els.body) els.body.innerHTML = `<tr><td colspan="6" class="sz_table_cell sz_inv_error p-3">${escapeHtml(e.message || 'Erro')}</td></tr>`;
      state.rows = [];
      state.selected.clear();
      updateSummary();
    }
  }

  function addMonthsFirstDay(isoDate, add) {
    const base = /^\d{4}-\d{2}-\d{2}$/.test(String(isoDate || '')) ? new Date(`${isoDate}T00:00:00`) : new Date();
    const d = new Date(base.getFullYear(), base.getMonth() + Number(add || 0), 1);
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-01`;
  }

  function buildPreviewLines() {
    const meses = Math.max(1, Number(els.meses?.value || 1));
    const totalCents = Math.round(selectedTotal() * 100);
    const baseCents = Math.floor(totalCents / meses);
    const rem = totalCents - (baseCents * meses);
    const dataIni = String(els.dataini?.value || firstDayIso(state.ano, state.mes));
    const ccusto = String(els.ccusto?.value || '').trim();
    const descr = String(els.descr?.value || '').trim();
    const out = [];
    for (let i = 0; i < meses; i += 1) {
      let cents = baseCents;
      if (i === meses - 1) cents += rem;
      out.push({
        NUM: i + 1,
        DATAREF: addMonthsFirstDay(dataIni, i),
        CCUSTO: ccusto,
        DESCR: descr,
        VALOR: cents / 100.0,
      });
    }
    return out;
  }

  function renderPreview() {
    if (!els.previewBody) return;
    const lines = buildPreviewLines();
    if (!lines.length) {
      els.previewBody.innerHTML = '<tr><td colspan="5" class="sz_table_cell sz_text_muted p-2">Sem linhas.</td></tr>';
      return;
    }
    els.previewBody.innerHTML = lines.map((ln) => `
      <tr>
        <td>${ln.NUM}</td>
        <td>${escapeHtml(isoToDmy(ln.DATAREF))}</td>
        <td>${escapeHtml(ln.CCUSTO)}</td>
        <td>${escapeHtml(ln.DESCR)}</td>
        <td class="text-end">${fmtMoney(ln.VALOR)}</td>
      </tr>
    `).join('');
  }

  function renderSelectionInfo() {
    if (!els.selInfo) return;
    const rows = selectedRows();
    if (!rows.length) {
      els.selInfo.textContent = '';
      return;
    }
    els.selInfo.textContent = `${rows.length} linhas · Total ${fmtMoney(selectedTotal())} € · ${selectedCcusto()}`;
  }

  function openModal() {
    const rows = selectedRows();
    if (!rows.length) return;
    const cc = selectedCcusto();
    const total = selectedTotal();

    if (els.descr && !String(els.descr.value || '').trim()) {
      els.descr.value = `Investimento ${cc} ${String(state.mes).padStart(2, '0')}/${state.ano}`;
    }
    if (els.ccusto) els.ccusto.value = cc;
    if (els.datainv) els.datainv.value = todayIso();
    if (els.dataini) els.dataini.value = firstDayIso(state.ano, state.mes);
    if (els.meses) els.meses.value = String(Math.max(1, Number(els.meses.value || 12)));
    if (els.valortotal) els.valortotal.value = fmtMoney(total);
    if (els.obs) els.obs.value = '';

    renderSelectionInfo();
    renderPreview();

    const modal = getModal();
    if (!modal) {
      alert('Não foi possível abrir o modal. Recarrega a página e tenta novamente.');
      return;
    }
    modal.show();
  }

  async function saveInvestment() {
    const rows = selectedRows();
    if (!rows.length) return alert('Seleciona custos antes de gravar.');
    const cc = selectedCcusto();
    const descr = String(els.descr?.value || '').trim();
    const datainv = String(els.datainv?.value || '').trim();
    const dataini = String(els.dataini?.value || '').trim();
    const meses = Number(els.meses?.value || 0);
    const valortotal = selectedTotal();
    const obs = String(els.obs?.value || '').trim();

    if (!descr) return alert('DESCR é obrigatório.');
    if (!cc) return alert('CCUSTO inválido.');
    if (!datainv || !dataini) return alert('Preenche DATAINV e DATAINI.');
    if (!Number.isFinite(meses) || meses <= 0) return alert('MESES tem de ser maior que zero.');
    if (!(valortotal > 0)) return alert('VALORTOTAL tem de ser maior que zero.');

    const payload = {
      ano: state.ano,
      mes: state.mes,
      exclude_gestao: state.excluirGestao ? 1 : 0,
      selected: rows.map((r) => ({
        ORIGEM: r.ORIGEM,
        CABSTAMP: r.CABSTAMP,
        STAMP: r.STAMP,
        DATA: r.DATA,
        CCUSTO: r.CCUSTO,
        FAMILIA: r.FAMILIA,
        DESCR: r.DESCR,
        VALOR: r.VALOR,
      })),
      header: {
        DESCR: descr,
        CCUSTO: cc,
        DATAINV: datainv,
        DATAINI: dataini,
        MESES: meses,
        VALORTOTAL: valortotal,
        OBS: obs,
      },
    };

    if (els.saveBtn) els.saveBtn.disabled = true;
    try {
      const res = await fetch('/api/investimentos/criar', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok || data.error) throw new Error(data.error || 'Erro ao gravar investimento');
      alert(`Investimento criado com sucesso (${data.invstamp}).`);
      state.selected.clear();
      getModal()?.hide();
      await loadRows();
    } catch (e) {
      alert(e.message || 'Erro ao gravar investimento');
    } finally {
      if (els.saveBtn) els.saveBtn.disabled = false;
    }
  }

  els.criarBtn?.addEventListener('click', openModal);
  els.recalcBtn?.addEventListener('click', renderPreview);
  els.saveBtn?.addEventListener('click', saveInvestment);
  els.meses?.addEventListener('input', renderPreview);
  els.dataini?.addEventListener('change', renderPreview);
  els.descr?.addEventListener('input', renderPreview);
  els.mes?.addEventListener('change', loadRows);
  els.ano?.addEventListener('change', loadRows);
  els.excluiGestao?.addEventListener('change', loadRows);
  els.ano?.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') loadRows();
  });
  els.ano?.addEventListener('blur', loadRows);

  if (els.mes) els.mes.value = String(state.mes);
  if (els.ano) els.ano.value = String(state.ano);
  if (els.excluiGestao) els.excluiGestao.checked = true;
  updateSummary();
  loadRows();
})();
