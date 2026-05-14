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
  const btnCreateOw = document.getElementById('rbCreateOW');
  const btnGroup = document.getElementById('rbGroupExtratos');
  const btnSuggest = document.getElementById('rbSuggestMatches');
  const onlyOpen = document.getElementById('rbOnlyOpen');
  const groupModalEl = document.getElementById('rbGroupModal');
  const groupModal = groupModalEl && window.bootstrap ? new bootstrap.Modal(groupModalEl) : null;
  const suggestModalEl = document.getElementById('rbSuggestModal');
  const suggestModal = suggestModalEl && window.bootstrap ? new bootstrap.Modal(suggestModalEl) : null;
  const suggestStatus = document.getElementById('rbSuggestStatus');
  const suggestTableBody = document.querySelector('#rbSuggestTable tbody');
  const suggestSelectAll = document.getElementById('rbSuggestSelectAll');
  const btnSuggestAccept = document.getElementById('rbSuggestAccept');
  const groupConta = document.getElementById('rbGroupConta');
  const groupAno = document.getElementById('rbGroupAno');
  const groupMes = document.getElementById('rbGroupMes');
  const groupStatus = document.getElementById('rbGroupStatus');
  const groupSubmit = document.getElementById('rbGroupSubmit');

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
    suggestions: [],
    selectedSuggestions: new Set(),
    activeGroupId: 0,
    groupAccounts: [],
  };

  const monthNames = [
    'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
    'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro',
  ];

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

  function setGroupStatus(msg, kind) {
    if (!groupStatus) return;
    groupStatus.className = 'rb-group-status sz_text_sm ' + (kind === 'err' ? 'text-danger' : kind === 'ok' ? 'text-success' : 'text-muted');
    groupStatus.textContent = msg || '';
  }

  function isOpenRow(row) {
    return Number(row?.RECONCILIADO || 0) !== 1;
  }

  function valueCents(value) {
    return Math.round((Number(value || 0) || 0) * 100);
  }

  function parseRowDate(value) {
    const raw = (value || '').toString().slice(0, 10);
    if (!raw) return null;
    const d = new Date(`${raw}T00:00:00`);
    return Number.isFinite(d.getTime()) ? d : null;
  }

  function dateGapDays(a, b) {
    const da = parseRowDate(a);
    const db = parseRowDate(b);
    if (!da || !db) return 999999;
    return Math.abs(Math.round((da.getTime() - db.getTime()) / 86400000));
  }

  function updateSuggestButton() {
    if (!btnSuggest) return;
    const hasOpenEl = (state.elRows || []).some(isOpenRow);
    const hasOpenBa = (state.baRows || []).some(isOpenRow);
    btnSuggest.disabled = !(state.ext && hasOpenEl && hasOpenBa);
  }

  function updateSuggestSelectionUi() {
    const total = state.suggestions.length;
    const selected = state.selectedSuggestions.size;
    if (btnSuggestAccept) btnSuggestAccept.disabled = selected <= 0;
    if (suggestSelectAll) {
      suggestSelectAll.checked = total > 0 && selected === total;
      suggestSelectAll.indeterminate = selected > 0 && selected < total;
      suggestSelectAll.disabled = total <= 0;
    }
  }

  function buildSuggestions() {
    const elRows = (state.elRows || [])
      .filter(row => isOpenRow(row) && valueCents(row.VALOR) !== 0)
      .slice()
      .sort((a, b) => {
        const ad = (a.DTVALOR || a.DATA || '').toString();
        const bd = (b.DTVALOR || b.DATA || '').toString();
        return ad.localeCompare(bd) || (a.STAMP || '').toString().localeCompare((b.STAMP || '').toString());
      });

    const baByValue = new Map();
    (state.baRows || [])
      .filter(row => isOpenRow(row) && valueCents(row.VALOR) !== 0)
      .forEach(row => {
        const key = valueCents(row.VALOR);
        if (!baByValue.has(key)) baByValue.set(key, []);
        baByValue.get(key).push(row);
      });

    for (const rows of baByValue.values()) {
      rows.sort((a, b) => {
        const ad = (a.DATA || '').toString();
        const bd = (b.DATA || '').toString();
        return ad.localeCompare(bd) || (a.BASTAMP || '').toString().localeCompare((b.BASTAMP || '').toString());
      });
    }

    const usedBa = new Set();
    const suggestions = [];
    for (const el of elRows) {
      const key = valueCents(el.VALOR);
      const elDate = el.DTVALOR || el.DATA || '';
      const candidates = (baByValue.get(key) || []).filter(ba => !usedBa.has((ba.BASTAMP || '').toString()));
      if (!candidates.length) continue;
      candidates.sort((a, b) => (
        dateGapDays(elDate, a.DATA) - dateGapDays(elDate, b.DATA)
        || (a.DATA || '').toString().localeCompare((b.DATA || '').toString())
        || (a.BASTAMP || '').toString().localeCompare((b.BASTAMP || '').toString())
      ));
      const ba = candidates[0];
      usedBa.add((ba.BASTAMP || '').toString());
      suggestions.push({
        el,
        ba,
        valor: Number(el.VALOR || 0) || 0,
        days: dateGapDays(elDate, ba.DATA),
      });
    }
    return suggestions;
  }

  function renderSuggestions(rows) {
    state.suggestions = Array.isArray(rows) ? rows : [];
    state.selectedSuggestions.clear();
    if (suggestStatus) {
      suggestStatus.textContent = rows.length
        ? `${rows.length} sugestao(oes) encontrada(s) por valor igual.`
        : 'Sem sugestoes para os movimentos pendentes deste extrato.';
    }
    if (!suggestTableBody) return;
    if (!rows.length) {
      suggestTableBody.innerHTML = '<tr><td colspan="9" class="text-muted">Sem movimentos pendentes com valor igual.</td></tr>';
      updateSuggestSelectionUi();
      return;
    }
    suggestTableBody.innerHTML = rows.map((row, idx) => {
      const el = row.el || {};
      const ba = row.ba || {};
      return `
        <tr>
          <td>
            <input class="form-check-input rb-suggest-check" type="checkbox" data-suggest-index="${idx}">
          </td>
          <td>${idx + 1}</td>
          <td>${esc(el.DTVALOR || el.DATA || '')}</td>
          <td><div class="rb-suggest-desc" title="${esc(el.DESCRICAO || '')}">${esc(el.DESCRICAO || '')}</div></td>
          <td class="text-end ${moneyClass(row.valor)}">${fmtMoney(row.valor)}</td>
          <td>${esc(ba.DATA || '')}</td>
          <td><div class="rb-suggest-desc" title="${esc(ba.DOCUMENTO || '')}">${esc(ba.DOCUMENTO || '')}</div></td>
          <td><div class="rb-suggest-desc" title="${esc(ba.DESCRICAO || '')}">${esc(ba.DESCRICAO || '')}</div></td>
          <td class="text-end">${row.days === 999999 ? '-' : esc(row.days)}</td>
        </tr>
      `;
    }).join('');
    updateSuggestSelectionUi();
  }

  async function reconcileSelectedSuggestions() {
    const extstamp = (selExt?.value || '').trim();
    if (!extstamp || !state.selectedSuggestions.size) return;
    const selected = Array.from(state.selectedSuggestions).sort((a, b) => a - b);
    let done = 0;
    try {
      if (btnSuggestAccept) btnSuggestAccept.disabled = true;
      if (suggestStatus) suggestStatus.textContent = `A reconciliar ${selected.length} sugestao(oes)...`;
      for (const idx of selected) {
        const suggestion = state.suggestions[idx];
        const elStamp = (suggestion?.el?.STAMP || '').toString();
        const baStamp = (suggestion?.ba?.BASTAMP || '').toString();
        if (!elStamp || !baStamp) continue;
        const r = await fetch('/api/reconciliacao', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ EXTSTAMP: extstamp, EL: [elStamp], BA: [baStamp] }),
        });
        const js = await r.json().catch(() => ({}));
        if (!r.ok || js.error) throw new Error(`Linha ${idx + 1}: ${js.error || r.statusText}`);
        done += 1;
      }
      setStatus(`${done} reconciliacao(oes) criada(s).`, 'ok');
      suggestModal?.hide();
      await loadForExt(extstamp);
    } catch (e) {
      if (suggestStatus) {
        suggestStatus.textContent = `${e?.message || String(e)}${done ? ` (${done} reconciliada(s) antes do erro).` : ''}`;
      }
      setStatus(e?.message || String(e), 'err');
      if (done) await loadForExt(extstamp);
    } finally {
      updateSuggestSelectionUi();
    }
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

    let eligibleOw = 0;
    for (const stamp of state.selEl) {
      const row = (state.elRows || []).find(x => (x.STAMP || '').toString() === stamp);
      if (!row) continue;
      const valor = Number(row.VALOR || 0) || 0;
      const rec = Number(row.RECONCILIADO || 0) === 1;
      if (!rec && valor > 0.005) eligibleOw += 1;
    }
    if (btnCreateOw) btnCreateOw.disabled = eligibleOw <= 0;
    updateSuggestButton();
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

  function accountLabel(account) {
    const banco = (account?.BANCO || '').toString().trim();
    const conta = (account?.CONTA || '').toString().trim();
    const noconta = (account?.NOCONTA ?? '').toString().trim();
    const extCount = Number(account?.EXT_COUNT || 0) || 0;
    const base = [banco, conta].filter(Boolean).join(' - ') || `Conta ${noconta}`;
    return `${base} · ${extCount} estrato(s)`;
  }

  function fillGroupAccounts(selectedAccount) {
    if (!groupConta) return;
    const accounts = Array.isArray(state.groupAccounts) ? state.groupAccounts : [];
    if (!accounts.length) {
      groupConta.innerHTML = '<option value="">Sem contas com estratos</option>';
      groupConta.disabled = true;
      return;
    }
    groupConta.disabled = false;
    groupConta.innerHTML = accounts.map(acc => (
      `<option value="${esc(acc.NOCONTA)}">${esc(accountLabel(acc))}</option>`
    )).join('');
    const wanted = (selectedAccount ?? '').toString().trim();
    if (wanted && accounts.some(acc => (acc.NOCONTA ?? '').toString() === wanted)) {
      groupConta.value = wanted;
    }
  }

  async function loadGroupAccounts() {
    if (!groupConta) return;
    groupConta.disabled = true;
    groupConta.innerHTML = '<option value="">A carregar...</option>';
    try {
      const r = await fetch('/api/extratos/contas');
      const js = await r.json().catch(() => ([]));
      if (!r.ok || js.error) throw new Error(js.error || r.statusText);
      state.groupAccounts = Array.isArray(js) ? js : [];
      fillGroupAccounts(state.ext?.NOCONTA ?? '');
      setGroupStatus('', '');
    } catch (e) {
      groupConta.innerHTML = '<option value="">(Erro ao carregar)</option>';
      groupConta.disabled = true;
      setGroupStatus(e?.message || String(e), 'err');
    }
  }

  function prefillGroupForm() {
    const refDate = (state.ext?.DATAINI || state.ext?.DATAFIM || '').toString();
    const parsed = refDate ? new Date(`${refDate}T00:00:00`) : new Date();
    const year = Number.isFinite(parsed.getTime()) ? parsed.getFullYear() : new Date().getFullYear();
    const month = Number.isFinite(parsed.getTime()) ? parsed.getMonth() + 1 : new Date().getMonth() + 1;
    if (groupAno) groupAno.value = year;
    if (groupMes) groupMes.value = String(month);
    fillGroupAccounts(state.ext?.NOCONTA ?? '');
    setGroupStatus('', '');
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
    state.ext = null;
    state.elRows = [];
    state.baRows = [];
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
    if (!v) {
      state.ext = null;
      state.elRows = [];
      state.baRows = [];
      state.selEl.clear();
      state.selBa.clear();
      state.activeGroupId = 0;
      if (inpConta) inpConta.value = '';
      if (inpPeriodo) inpPeriodo.value = '';
      if (tbEl) tbEl.innerHTML = '<tr><td colspan="5" class="text-muted">Seleciona um extrato.</td></tr>';
      if (tbBa) tbBa.innerHTML = '<tr><td colspan="5" class="text-muted">Seleciona um extrato.</td></tr>';
      computeSums();
      return;
    }
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

  btnSuggest?.addEventListener('click', () => {
    if (!state.ext) {
      setStatus('Seleciona um extrato.', 'err');
      return;
    }
    const suggestions = buildSuggestions();
    renderSuggestions(suggestions);
    suggestModal?.show();
  });

  suggestSelectAll?.addEventListener('change', () => {
    state.selectedSuggestions.clear();
    if (suggestSelectAll.checked) {
      state.suggestions.forEach((_, idx) => state.selectedSuggestions.add(idx));
    }
    suggestTableBody?.querySelectorAll('.rb-suggest-check').forEach(chk => {
      const idx = Number(chk.getAttribute('data-suggest-index') || -1);
      chk.checked = state.selectedSuggestions.has(idx);
    });
    updateSuggestSelectionUi();
  });

  suggestTableBody?.addEventListener('change', (e) => {
    const chk = e.target.closest('.rb-suggest-check');
    if (!chk) return;
    const idx = Number(chk.getAttribute('data-suggest-index') || -1);
    if (idx < 0) return;
    if (chk.checked) state.selectedSuggestions.add(idx);
    else state.selectedSuggestions.delete(idx);
    updateSuggestSelectionUi();
  });

  btnSuggestAccept?.addEventListener('click', () => {
    reconcileSelectedSuggestions();
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

  btnCreateOw?.addEventListener('click', async () => {
    const extstamp = (selExt?.value || '').trim();
    if (!extstamp) return;
    const elStamps = Array.from(state.selEl);
    if (!elStamps.length) return;
    const eligible = elStamps.filter(st => {
      const row = (state.elRows || []).find(x => (x.STAMP || '').toString() === st);
      if (!row) return false;
      return Number(row.RECONCILIADO || 0) !== 1 && (Number(row.VALOR || 0) || 0) > 0.005;
    });
    if (!eligible.length) return;
    if (!confirm(`Gerar movimentos OLBB no ERP para ${eligible.length} entrada(s)?`)) return;
    try {
      btnCreateOw.disabled = true;
      setStatus('A gerar OLBB...', '');
      const r = await fetch('/api/reconciliacao/olbb', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ EXTSTAMP: extstamp, EL: eligible })
      });
      const js = await r.json().catch(() => ({}));
      if (!r.ok || js.error) throw new Error(js.error || r.statusText);
      setStatus(`OLBB gerado(s): ${js.inserted || 0}.`, 'ok');
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

  btnGroup?.addEventListener('click', async () => {
    prefillGroupForm();
    if (!state.groupAccounts.length) await loadGroupAccounts();
    groupModal?.show();
  });

  groupSubmit?.addEventListener('click', async () => {
    const noconta = Number(groupConta?.value || 0) || 0;
    const ano = Number(groupAno?.value || 0) || 0;
    const mes = Number(groupMes?.value || 0) || 0;
    if (noconta <= 0 || ano <= 0 || mes <= 0) {
      setGroupStatus('Seleciona a conta, o ano e o mês.', 'err');
      return;
    }
    const monthLabel = monthNames[mes - 1] || `Mês ${mes}`;
    if (!confirm(`Criar um estrato único para ${monthLabel} de ${ano} na conta selecionada?\n\nOs movimentos desse mês serão movidos para um novo estrato.`)) {
      return;
    }
    try {
      groupSubmit.disabled = true;
      setGroupStatus('A agrupar estratos...', '');
      const r = await fetch('/api/extratos/agrupar', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ NOCONTA: noconta, ANO: ano, MES: mes }),
      });
      const js = await r.json().catch(() => ({}));
      if (!r.ok || js.error) throw new Error(js.error || r.statusText);
      setGroupStatus(`Estrato mensal criado com ${js.moved_lines || 0} movimento(s).`, 'ok');
      setStatus(`Estrato mensal ${monthLabel}/${ano} criado com sucesso.`, 'ok');
      await loadExtratos();
      if (selExt && js.EXTSTAMP) {
        selExt.value = js.EXTSTAMP;
        await loadForExt(js.EXTSTAMP);
      }
      setTimeout(() => groupModal?.hide(), 220);
    } catch (e) {
      setGroupStatus(e?.message || String(e), 'err');
    } finally {
      groupSubmit.disabled = false;
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
