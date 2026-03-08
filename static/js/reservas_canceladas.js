(function () {
  const state = {
    rows: [],
    currentRsstamp: '',
    currentReserva: '',
    modal: null,
    highlightRsstamp: sessionStorage.getItem('rsc_last_row') || '',
    sortKey: 'DATAIN',
    sortDir: 'desc',
  };

  const els = {
    datainFrom: document.getElementById('rscDatainFrom'),
    datainTo: document.getElementById('rscDatainTo'),
    dataoutFrom: document.getElementById('rscDataoutFrom'),
    dataoutTo: document.getElementById('rscDataoutTo'),
    diasCancelMax: document.getElementById('rscDiasCancelMax'),
    semPagamento: document.getElementById('rscSemPagamento'),
    pesquisar: document.getElementById('rscPesquisar'),
    limpar: document.getElementById('rscLimpar'),
    resumo: document.getElementById('rscResumo'),
    body: document.getElementById('rscBody'),
    modalEl: document.getElementById('rscModal'),
    modalInfo: document.getElementById('rscModalInfo'),
    modalValor: document.getElementById('rscModalValor'),
    modalGuardar: document.getElementById('rscModalGuardar'),
  };

  const esc = (v) => String(v ?? '').replace(/[&<>"']/g, (m) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[m]));
  const fmtDate = (iso) => {
    const s = String(iso || '').trim();
    return /^\d{4}-\d{2}-\d{2}$/.test(s) ? `${s.slice(8, 10)}/${s.slice(5, 7)}/${s.slice(0, 4)}` : '';
  };
  const fmtMoney = (v) => Number(v || 0).toLocaleString('pt-PT', { minimumFractionDigits: 2, maximumFractionDigits: 2 });

  function setHighlight(stamp) {
    const rsstamp = String(stamp || '').trim();
    state.highlightRsstamp = rsstamp;
    try {
      if (rsstamp) sessionStorage.setItem('rsc_last_row', rsstamp);
      else sessionStorage.removeItem('rsc_last_row');
    } catch (_) {}
  }

  function getModal() {
    if (!els.modalEl) return null;
    if (state.modal) return state.modal;
    if (window.bootstrap?.Modal) {
      state.modal = new window.bootstrap.Modal(els.modalEl);
      return state.modal;
    }
    return null;
  }

  function buildFilters() {
    const qs = new URLSearchParams();
    const f = String(els.datainFrom?.value || '').trim();
    const t = String(els.datainTo?.value || '').trim();
    const fo = String(els.dataoutFrom?.value || '').trim();
    const to = String(els.dataoutTo?.value || '').trim();
    const dmax = String(els.diasCancelMax?.value || '').trim();
    const semPagamento = !!els.semPagamento?.checked;
    if (f) qs.set('datain_from', f);
    if (t) qs.set('datain_to', t);
    if (fo) qs.set('dataout_from', fo);
    if (to) qs.set('dataout_to', to);
    if (dmax) qs.set('dias_cancel_max', dmax);
    if (semPagamento) qs.set('sem_pagamento', '1');
    return qs;
  }

  function isNumericKey(key) {
    return ['NOITES', 'DIASCANCEL', 'ESTADIA', 'LIMPEZA', 'PCANCEL'].includes(String(key || '').toUpperCase());
  }

  function isDateKey(key) {
    return ['DATAIN', 'DATAOUT', 'RDATA', 'DTCANCEL'].includes(String(key || '').toUpperCase());
  }

  function compareValues(a, b, key, dir) {
    const m = dir === 'asc' ? 1 : -1;
    const va = a?.[key];
    const vb = b?.[key];
    if (isNumericKey(key)) {
      const na = Number(va || 0);
      const nb = Number(vb || 0);
      if (na < nb) return -1 * m;
      if (na > nb) return 1 * m;
      return 0;
    }
    if (isDateKey(key)) {
      const ta = Date.parse(String(va || '')) || 0;
      const tb = Date.parse(String(vb || '')) || 0;
      if (ta < tb) return -1 * m;
      if (ta > tb) return 1 * m;
      return 0;
    }
    return String(va || '').toLowerCase().localeCompare(String(vb || '').toLowerCase()) * m;
  }

  function getSortedRows() {
    const key = String(state.sortKey || '').trim();
    if (!key) return [...state.rows];
    const rows = [...state.rows];
    rows.sort((a, b) => compareValues(a, b, key, state.sortDir));
    return rows;
  }

  function applySortHeaderState() {
    document.querySelectorAll('.rsc-sortable').forEach((th) => {
      const k = String(th.getAttribute('data-sort') || '').trim();
      th.classList.toggle('rsc-sort-active', k === state.sortKey);
      th.removeAttribute('title');
      if (k === state.sortKey) th.setAttribute('title', state.sortDir === 'asc' ? 'Ordenado ascendente' : 'Ordenado descendente');
    });
  }

  function updateResumo() {
    if (!els.resumo) return;
    const rows = getSortedRows();
    const total = rows.reduce((acc, r) => acc + Number(r.PCANCEL || 0), 0);
    els.resumo.textContent = `${rows.length} reservas · Total PCANCEL ${fmtMoney(total)} €`;
  }

  function emptyRow(message, klass) {
    return `<tr><td colspan="13" class="sz_table_cell ${klass || 'sz_text_muted'}">${esc(message)}</td></tr>`;
  }

  function renderRows() {
    if (!els.body) return;
    const rows = getSortedRows();
    if (!rows.length) {
      els.body.innerHTML = emptyRow('Sem reservas canceladas para os filtros aplicados.', 'sz_text_muted');
      applySortHeaderState();
      updateResumo();
      return;
    }

    els.body.innerHTML = rows.map((r) => `
      <tr data-rsstamp="${esc(r.RSSTAMP)}" class="sz_table_row ${state.highlightRsstamp === String(r.RSSTAMP || '').trim() ? 'rsc-row-highlight' : ''}">
        <td class="sz_table_cell">${esc(r.RESERVA || '')}</td>
        <td class="sz_table_cell">${esc(r.ALOJAMENTO || '')}</td>
        <td class="sz_table_cell">${esc(r.NOME || '')}</td>
        <td class="sz_table_cell">${esc(r.ORIGEM || '')}</td>
        <td class="sz_table_cell">${esc(fmtDate(r.DATAIN))}</td>
        <td class="sz_table_cell">${esc(fmtDate(r.DATAOUT))}</td>
        <td class="sz_table_cell sz_text_right">${Number(r.NOITES || 0)}</td>
        <td class="sz_table_cell sz_text_right">${Number(r.DIASCANCEL || 0)}</td>
        <td class="sz_table_cell sz_text_right">${fmtMoney(r.ESTADIA)}</td>
        <td class="sz_table_cell sz_text_right">${fmtMoney(r.LIMPEZA)}</td>
        <td class="sz_table_cell sz_text_right"><strong>${fmtMoney(r.PCANCEL)}</strong></td>
        <td class="sz_table_cell sz_text_right">
          ${r.ITINERARIO_URL ? `<a href="${esc(r.ITINERARIO_URL)}" class="sz_button sz_button_ghost rsc-btn-inline rsc-itinerario" data-rsstamp="${esc(r.RSSTAMP)}" target="_blank" rel="noopener">Abrir</a>` : '<span class="sz_text_muted">-</span>'}
        </td>
        <td class="sz_table_cell sz_text_right">
          <button class="sz_button sz_button_primary rsc-btn-inline rsc-btn-valor" data-rsstamp="${esc(r.RSSTAMP)}" data-reserva="${esc(r.RESERVA || '')}" data-pcancel="${Number(r.PCANCEL || 0)}">Atribuir valor</button>
        </td>
      </tr>
    `).join('');

    els.body.querySelectorAll('tr[data-rsstamp]').forEach((tr) => {
      tr.addEventListener('click', () => {
        setHighlight(tr.getAttribute('data-rsstamp') || '');
        renderRows();
      });
    });

    els.body.querySelectorAll('.rsc-itinerario').forEach((lnk) => {
      lnk.addEventListener('click', () => {
        setHighlight(lnk.getAttribute('data-rsstamp') || '');
        renderRows();
      });
    });

    els.body.querySelectorAll('.rsc-btn-valor').forEach((btn) => {
      btn.addEventListener('click', () => {
        state.currentRsstamp = String(btn.getAttribute('data-rsstamp') || '').trim();
        state.currentReserva = String(btn.getAttribute('data-reserva') || '').trim();
        setHighlight(state.currentRsstamp);
        renderRows();
        const current = Number(btn.getAttribute('data-pcancel') || 0);
        if (els.modalInfo) {
          els.modalInfo.textContent = state.currentReserva ? `Reserva ${state.currentReserva}` : state.currentRsstamp;
        }
        if (els.modalValor) els.modalValor.value = current.toFixed(2);
        getModal()?.show();
      });
    });

    applySortHeaderState();
    updateResumo();
  }

  async function loadRows() {
    if (els.body) els.body.innerHTML = emptyRow('A carregar...', 'sz_text_muted');
    try {
      const res = await fetch(`/api/reservas/cancelamentos?${buildFilters().toString()}`);
      const data = await res.json().catch(() => ({}));
      if (!res.ok || data.error) throw new Error(data.error || 'Erro ao carregar cancelamentos');
      state.rows = Array.isArray(data.rows) ? data.rows : [];
      renderRows();
    } catch (e) {
      state.rows = [];
      if (els.body) els.body.innerHTML = emptyRow(e.message || 'Erro', 'sz_error');
      updateResumo();
    }
  }

  async function savePcancel() {
    const rsstamp = String(state.currentRsstamp || '').trim();
    if (!rsstamp) return;
    const value = Number(els.modalValor?.value || 0);
    if (!Number.isFinite(value) || value < 0) {
      window.alert('Valor inválido.');
      return;
    }

    if (els.modalGuardar) els.modalGuardar.disabled = true;
    try {
      const res = await fetch(`/api/reservas/cancelamentos/${encodeURIComponent(rsstamp)}/pcancel`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ pcancel: value }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok || data.error) throw new Error(data.error || 'Erro ao gravar valor');
      getModal()?.hide();
      await loadRows();
    } catch (e) {
      window.alert(e.message || 'Erro ao gravar valor');
    } finally {
      if (els.modalGuardar) els.modalGuardar.disabled = false;
    }
  }

  function clearFilters() {
    if (els.datainFrom) els.datainFrom.value = '';
    if (els.datainTo) els.datainTo.value = '';
    if (els.dataoutFrom) els.dataoutFrom.value = '';
    if (els.dataoutTo) els.dataoutTo.value = '';
    if (els.diasCancelMax) els.diasCancelMax.value = '';
    if (els.semPagamento) els.semPagamento.checked = false;
    loadRows();
  }

  function setupSorting() {
    document.querySelectorAll('.rsc-sortable').forEach((th) => {
      th.addEventListener('click', () => {
        const key = String(th.getAttribute('data-sort') || '').trim();
        if (!key) return;
        if (state.sortKey === key) {
          state.sortDir = state.sortDir === 'asc' ? 'desc' : 'asc';
        } else {
          state.sortKey = key;
          state.sortDir = isNumericKey(key) ? 'desc' : 'asc';
          if (isDateKey(key)) state.sortDir = 'desc';
        }
        renderRows();
      });
    });
  }

  els.pesquisar?.addEventListener('click', loadRows);
  els.limpar?.addEventListener('click', clearFilters);
  els.modalGuardar?.addEventListener('click', savePcancel);
  [els.datainFrom, els.datainTo, els.dataoutFrom, els.dataoutTo, els.diasCancelMax, els.semPagamento].forEach((el) => {
    el?.addEventListener('change', loadRows);
  });

  setupSorting();
  loadRows();
})();
