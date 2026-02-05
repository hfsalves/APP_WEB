// static/js/reconciliacao_bancaria.js

document.addEventListener('DOMContentLoaded', () => {
  const selExt = document.getElementById('rbExtrato');
  const inpConta = document.getElementById('rbConta');
  const inpPeriodo = document.getElementById('rbPeriodo');
  const statusEl = document.getElementById('rbStatus');
  const sumElEl = document.getElementById('rbSumEl');
  const sumBaEl = document.getElementById('rbSumBa');
  const diffEl = document.getElementById('rbDiff');
  const btnRec = document.getElementById('rbReconciliar');
  const btnRemove = document.getElementById('rbRemoveRec');
  const onlyOpen = document.getElementById('rbOnlyOpen');

  const searchEl = document.getElementById('rbSearchEl');
  const searchBa = document.getElementById('rbSearchBa');
  const clearEl = document.getElementById('rbClearEl');
  const clearBa = document.getElementById('rbClearBa');
  const tbEl = document.querySelector('#rbTableEl tbody');
  const tbBa = document.querySelector('#rbTableBa tbody');

  const state = {
    ext: null,
    elRows: [],
    baRows: [],
    selEl: new Set(),
    selBa: new Set(),
    activeGroupId: 0,
  };

  const esc = (s) => (s ?? '').toString()
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#039;');

  const fmtMoney = (v) => {
    const n = Number(v || 0) || 0;
    return n.toLocaleString('pt-PT', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  };

  function setStatus(msg, kind) {
    if (!statusEl) return;
    statusEl.className = 'small ' + (kind === 'err' ? 'text-danger' : kind === 'ok' ? 'text-success' : 'text-muted');
    statusEl.textContent = msg || '';
  }

  function moneyClass(v) {
    const n = Number(v || 0) || 0;
    return n < 0 ? 'rb-money rb-neg' : 'rb-money rb-pos';
  }

  function computeSums() {
    let sumEl = 0;
    let sumBa = 0;
    for (const r of state.elRows) if (state.selEl.has(r.STAMP)) sumEl += Number(r.VALOR || 0) || 0;
    for (const r of state.baRows) if (state.selBa.has(r.BASTAMP)) sumBa += Number(r.VALOR || 0) || 0;
    const diff = sumEl - sumBa;
    if (sumElEl) sumElEl.textContent = fmtMoney(sumEl);
    if (sumBaEl) sumBaEl.textContent = fmtMoney(sumBa);
    if (diffEl) diffEl.textContent = fmtMoney(diff);
    const ok = Math.abs(diff) < 0.01 && state.selEl.size > 0 && state.selBa.size > 0;
    if (btnRec) btnRec.disabled = !ok;
    const canRemove = !onlyOpen?.checked && Number(state.activeGroupId || 0) > 0;
    if (btnRemove) btnRemove.disabled = !canRemove;
  }

  function setActiveGroupFromRow(tr) {
    const gid = Number(tr?.getAttribute('data-groupid') || 0) || 0;
    state.activeGroupId = gid;
  }

  function filterRows(rows, term, fields) {
    const q = (term || '').trim().toLowerCase();
    let base = rows;
    if (onlyOpen?.checked) base = base.filter(r => Number(r.RECONCILIADO || 0) !== 1);
    if (!q) return base;
    return base.filter(r => fields.some(f => (r[f] ?? '').toString().toLowerCase().includes(q)));
  }

  function renderEl() {
    if (!tbEl) return;
    const rows = filterRows(state.elRows, searchEl?.value, ['DATA', 'DTVALOR', 'DESCRICAO']);
    if (!rows.length) {
      tbEl.innerHTML = '<tr><td colspan="5" class="text-muted">Sem linhas.</td></tr>';
      return;
    }
    tbEl.innerHTML = rows.map(r => {
      const checked = state.selEl.has(r.STAMP) ? 'checked' : '';
      const rec = r.RECONCILIADO ? 'rb-reconciled' : '';
      const pill = r.RECONCILIADO ? `<span class="rb-pill">G${esc(r.GROUPID)}</span>` : '';
      return `
        <tr class="${rec}" data-stamp="${esc(r.STAMP)}" data-groupid="${esc(r.GROUPID || 0)}">
          <td><input class="form-check-input rb-chk-el" type="checkbox" ${checked}></td>
          <td>${esc(r.DATA || '')}</td>
          <td>${esc(r.DTVALOR || '')}</td>
          <td class="text-truncate" style="max-width:420px;" title="${esc(r.DESCRICAO || '')}">${esc(r.DESCRICAO || '')}${pill}</td>
          <td class="text-end ${moneyClass(r.VALOR)}">${fmtMoney(r.VALOR)}</td>
        </tr>
      `;
    }).join('');
  }

  function renderBa() {
    if (!tbBa) return;
    const rows = filterRows(state.baRows, searchBa?.value, ['DATA', 'DOCUMENTO', 'DESCRICAO']);
    if (!rows.length) {
      tbBa.innerHTML = '<tr><td colspan="5" class="text-muted">Sem movimentos.</td></tr>';
      return;
    }
    tbBa.innerHTML = rows.map(r => {
      const checked = state.selBa.has(r.BASTAMP) ? 'checked' : '';
      const rec = r.RECONCILIADO ? 'rb-reconciled' : '';
      const pill = r.RECONCILIADO ? `<span class="rb-pill">G${esc(r.GROUPID)}</span>` : '';
      return `
        <tr class="${rec}" data-bastamp="${esc(r.BASTAMP)}" data-groupid="${esc(r.GROUPID || 0)}">
          <td><input class="form-check-input rb-chk-ba" type="checkbox" ${checked}></td>
          <td>${esc(r.DATA || '')}</td>
          <td class="text-truncate" style="max-width:160px;" title="${esc(r.DOCUMENTO || '')}">${esc(r.DOCUMENTO || '')}</td>
          <td class="text-truncate" style="max-width:420px;" title="${esc(r.DESCRICAO || '')}">${esc(r.DESCRICAO || '')}${pill}</td>
          <td class="text-end ${moneyClass(r.VALOR)}">${fmtMoney(r.VALOR)}</td>
        </tr>
      `;
    }).join('');
  }

  async function loadExtratos() {
    if (!selExt) return;
    selExt.innerHTML = '<option value="">A carregar...</option>';
    try {
      const r = await fetch('/api/extratos');
      const js = await r.json().catch(() => ([]));
      if (!r.ok || js.error) throw new Error(js.error || r.statusText);
      const rows = Array.isArray(js) ? js : [];
      selExt.innerHTML = '<option value="">(Seleciona)</option>' + rows.map(x => {
        const id = (x.EXTSTAMP || '').toString();
        const noconta = (x.NOCONTA ?? '').toString();
        const di = (x.DATAINI || '').toString();
        const df = (x.DATAFIM || '').toString();
        const label = `Conta ${noconta} | ${di} a ${df}`;
        return `<option value="${esc(id)}">${esc(label)}</option>`;
      }).join('');
    } catch (e) {
      selExt.innerHTML = '<option value="">(Erro)</option>';
      setStatus(e?.message || String(e), 'err');
    }
  }

  async function loadForExt(extstamp) {
    if (!extstamp) return;
    setStatus('A carregar...', '');
    state.selEl.clear();
    state.selBa.clear();
    state.activeGroupId = 0;
    computeSums();
    try {
      const r = await fetch(`/api/extratos/${encodeURIComponent(extstamp)}`);
      const js = await r.json().catch(() => ({}));
      if (!r.ok || js.error) throw new Error(js.error || r.statusText);
      state.ext = js.ext;
      state.elRows = Array.isArray(js.el) ? js.el : [];
      state.baRows = Array.isArray(js.ba) ? js.ba : [];

      if (inpConta) inpConta.value = `Conta ${(state.ext?.NOCONTA ?? '')}`;
      if (inpPeriodo) inpPeriodo.value = `${state.ext?.DATAINI || ''} a ${state.ext?.DATAFIM || ''}`;

      renderEl();
      renderBa();
      computeSums();
      setStatus('', '');
    } catch (e) {
      setStatus(e?.message || String(e), 'err');
      if (tbEl) tbEl.innerHTML = '<tr><td colspan="5" class="text-muted">Erro.</td></tr>';
      if (tbBa) tbBa.innerHTML = '<tr><td colspan="5" class="text-muted">Erro.</td></tr>';
    }
  }

  selExt?.addEventListener('change', () => {
    const v = (selExt.value || '').trim();
    if (!v) return;
    loadForExt(v);
  });

  searchEl?.addEventListener('input', () => renderEl());
  searchBa?.addEventListener('input', () => renderBa());
  onlyOpen?.addEventListener('change', () => {
    // Para evitar reconciliar seleções "invisíveis"
    state.selEl.clear();
    state.selBa.clear();
    state.activeGroupId = 0;
    renderEl();
    renderBa();
    computeSums();
  });
  clearEl?.addEventListener('click', () => {
    if (searchEl) searchEl.value = '';
    renderEl();
    try { searchEl?.focus(); } catch (_) {}
  });
  clearBa?.addEventListener('click', () => {
    if (searchBa) searchBa.value = '';
    renderBa();
    try { searchBa?.focus(); } catch (_) {}
  });

  document.addEventListener('click', (e) => {
    const trEl = e.target.closest('tr[data-stamp]');
    if (trEl && tbEl && tbEl.contains(trEl)) {
      const stamp = trEl.getAttribute('data-stamp');
      const chk = trEl.querySelector('.rb-chk-el');
      if (e.target !== chk) chk.checked = !chk.checked;
      if (chk.checked) state.selEl.add(stamp); else state.selEl.delete(stamp);
      setActiveGroupFromRow(trEl);
      computeSums();
      return;
    }
    const trBa = e.target.closest('tr[data-bastamp]');
    if (trBa && tbBa && tbBa.contains(trBa)) {
      const stamp = trBa.getAttribute('data-bastamp');
      const chk = trBa.querySelector('.rb-chk-ba');
      if (e.target !== chk) chk.checked = !chk.checked;
      if (chk.checked) state.selBa.add(stamp); else state.selBa.delete(stamp);
      setActiveGroupFromRow(trBa);
      computeSums();
      return;
    }
  });

  btnRemove?.addEventListener('click', async () => {
    const extstamp = (selExt?.value || '').trim();
    const gid = Number(state.activeGroupId || 0) || 0;
    if (!extstamp || gid <= 0) return;
    if (onlyOpen?.checked) return;
    if (!confirm(`Remover a reconciliação do grupo ${gid}?\n\nIsto vai desfazer a reconciliação do banco e da tesouraria.`)) return;
    try {
      btnRemove.disabled = true;
      setStatus('A remover reconciliação...', '');
      const r = await fetch(`/api/reconciliacao/${encodeURIComponent(extstamp)}/${gid}`, { method: 'DELETE' });
      const js = await r.json().catch(() => ({}));
      if (!r.ok || js.error) throw new Error(js.error || r.statusText);
      setStatus(`Reconciliação removida (grupo ${gid}).`, 'ok');
      await loadForExt(extstamp);
    } catch (e) {
      setStatus(e?.message || String(e), 'err');
      computeSums();
    }
  });

  btnRec?.addEventListener('click', async () => {
    const extstamp = (selExt?.value || '').trim();
    if (!extstamp) return;
    computeSums();
    if (btnRec.disabled) return;
    try {
      btnRec.disabled = true;
      setStatus('A reconciliar...', '');
      const payload = {
        EXTSTAMP: extstamp,
        EL: Array.from(state.selEl),
        BA: Array.from(state.selBa),
      };
      const r = await fetch('/api/reconciliacao', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      const js = await r.json().catch(() => ({}));
      if (!r.ok || js.error) throw new Error(js.error || r.statusText);
      setStatus(`Reconciliado (grupo ${js.GROUPID}).`, 'ok');
      await loadForExt(extstamp);
    } catch (e) {
      setStatus(e?.message || String(e), 'err');
    } finally {
      computeSums();
    }
  });

  loadExtratos();

  // Garantir scroll autónomo nas grelhas (cadeia de alturas explícita)
  let rbResizeTimer = null;
  function recalcHeights() {
    try {
      const page = document.querySelector('.rb-page');
      if (page) {
        const r = page.getBoundingClientRect();
        const h = Math.floor(window.innerHeight - r.top - 12);
        if (h > 260) page.style.height = `${h}px`;
      }

      const top = document.querySelector('.rb-top');
      const split = document.querySelector('.rb-split');
      if (top && split && page) {
        const gap = 12;
        const sh = page.clientHeight - top.offsetHeight - gap;
        if (sh > 220) split.style.height = `${sh}px`;
      }
    } catch (_) {}
  }

  window.addEventListener('resize', () => {
    try { if (rbResizeTimer) clearTimeout(rbResizeTimer); } catch (_) {}
    rbResizeTimer = setTimeout(recalcHeights, 80);
  });
  recalcHeights();
  setTimeout(recalcHeights, 0);
});
