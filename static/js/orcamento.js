// static/js/orcamento.js

document.addEventListener('DOMContentLoaded', () => {
  const anoInput = document.getElementById('orcAno');
  const btnAplicar = document.getElementById('orcBtnAplicar');
  const btnReplicarJan = document.getElementById('orcBtnReplicarJan');
  const tbody = document.getElementById('orcBody');
  const statusEl = document.getElementById('orcStatus');
  const totalsRow = document.getElementById('orcTotalsRow');

  const defaultYear = window.ORC_ANO_PADRAO || new Date().getFullYear();
  const fmt = new Intl.NumberFormat('pt-PT', { minimumFractionDigits: 0, maximumFractionDigits: 0, useGrouping: true });

  let lastData = null;
  let index = { byRef: new Map(), childrenDirect: new Map() };
  let saveTimer = null;
  let pending = new Map(); // key: familia|mes -> {familia, mes, valor}

  if (anoInput && !anoInput.value) anoInput.value = defaultYear;

  const escapeHtml = (s) => String(s == null ? '' : s)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');

  function setStatus(text, cls = '') {
    if (!statusEl) return;
    statusEl.className = cls ? `${cls}` : '';
    statusEl.textContent = text || '';
  }

  function setLoading(text) {
    if (!tbody) return;
    tbody.innerHTML = `<tr><td colspan="14" class="text-center text-muted">${escapeHtml(text)}</td></tr>`;
  }

  function toNumber(str) {
    if (str == null) return 0;
    const s = String(str).trim().replace(/\s/g, '');
    if (!s) return 0;
    // allow "1.234,56" or "1234.56"
    const normalized = s.includes(',') && !s.includes('.')
      ? s.replace(',', '.')
      : s.replace(/\./g, '').replace(',', '.');
    const n = Number(normalized);
    return Number.isFinite(n) ? n : 0;
  }

  function buildIndex(data) {
    const byRef = new Map();
    const childrenDirect = new Map();
    const rows = Array.isArray(data?.familias) ? data.familias : [];
    rows.forEach(r => {
      const ref = (r.ref || '').toString().trim();
      if (!ref) return;
      byRef.set(ref, r);
    });
    rows.forEach(r => {
      const ref = (r.ref || '').toString().trim();
      if (!ref) return;
      const level = Number(r.nivel || 1);
      const idxDot = ref.lastIndexOf('.');
      if (idxDot < 0) return;
      const parent = ref.slice(0, idxDot);
      const parentRow = byRef.get(parent);
      if (!parentRow) return;
      const parentLevel = Number(parentRow.nivel || 1);
      if (parentLevel !== level - 1) return;
      const arr = childrenDirect.get(parent) || [];
      arr.push(ref);
      childrenDirect.set(parent, arr);
    });
    index = { byRef, childrenDirect };
  }

  function updateReadonlyCell(ref, mes) {
    const row = index.byRef.get(ref);
    if (!row) return;
    const td = tbody?.querySelector?.(`td.orc-readonly[data-ref="${CSS.escape(ref)}"][data-mes="${mes}"]`);
    if (!td) return;
    const v = Number(row.meses?.[mes - 1] || 0);
    td.textContent = v ? fmt.format(v) : '';
  }

  function recalcParentsForMonth(ref, mes) {
    let cur = ref;
    while (true) {
      const dot = cur.lastIndexOf('.');
      if (dot < 0) break;
      const parent = cur.slice(0, dot);
      const parentRow = index.byRef.get(parent);
      if (!parentRow) {
        cur = parent;
        continue;
      }
      const children = index.childrenDirect.get(parent) || [];
      if (children.length) {
        const sum = children.reduce((acc, childRef) => {
          const child = index.byRef.get(childRef);
          const v = Number(child?.meses?.[mes - 1] || 0);
          return acc + (Number.isFinite(v) ? v : 0);
        }, 0);
        parentRow.meses = Array.isArray(parentRow.meses) ? parentRow.meses : Array(12).fill(0);
        parentRow.meses[mes - 1] = Math.round(sum);
        updateReadonlyCell(parent, mes);
      }
      cur = parent;
    }
  }

  function applyLocalUpdate(familia, mes, valor) {
    const row = index.byRef.get(familia);
    if (!row) return;
    row.meses = Array.isArray(row.meses) ? row.meses : Array(12).fill(0);
    row.meses[mes - 1] = Math.round(Number(valor || 0) || 0);
    recalcParentsForMonth(familia, mes);
    renderTotals();
  }

  function render(data) {
    if (!tbody) return;
    const rows = Array.isArray(data?.familias) ? data.familias : [];
    if (!rows.length) {
      tbody.innerHTML = `<tr><td colspan="14" class="text-center text-muted">Sem famílias.</td></tr>`;
      return;
    }
    tbody.innerHTML = rows.map(r => {
      const nivel = Number(r.nivel || 1);
      const famCls = `fam-cell level-${Math.min(3, Math.max(1, nivel))}`;
      const nome = (r.nome || '').toString().trim();
      const label = nome ? `${r.ref} - ${nome}` : `${r.ref}`;
      const editable = !!r.editable;
      const meses = Array.isArray(r.meses) ? r.meses : Array(12).fill(0);
      const rowTotal = meses.slice(0, 12).reduce((acc, v) => acc + (Number(v || 0) || 0), 0);
      const cells = meses.slice(0, 12).map((v, idx) => {
        const mes = idx + 1;
        const num = Number(v || 0);
        if (!editable) {
          const txt = num ? fmt.format(num) : '';
          return `<td class="text-end orc-readonly" data-ref="${escapeHtml(r.ref)}" data-mes="${mes}">${escapeHtml(txt)}</td>`;
        }
        return `
          <td>
            <input
              class="form-control form-control-sm orc-input"
              inputmode="decimal"
              type="text"
              data-familia="${escapeHtml(r.ref)}"
              data-mes="${mes}"
              value="${escapeHtml(num ? fmt.format(num) : '')}"
              placeholder=""
            />
          </td>
        `;
      }).join('');
      return `
        <tr>
          <td class="${famCls}">${escapeHtml(label)}</td>
          ${cells}
          <td class="text-end orc-readonly orc-row-total" data-ref="${escapeHtml(r.ref)}" data-total="1">${escapeHtml(rowTotal ? fmt.format(rowTotal) : '')}</td>
        </tr>
      `;
    }).join('');
  }

  function renderTotals() {
    if (!totalsRow || !lastData) return;
    const rows = Array.isArray(lastData?.familias) ? lastData.familias : [];
    const totals = Array(12).fill(0);
    let grand = 0;
    rows.forEach(r => {
      const ref = (r.ref || '').toString().trim();
      if (!ref || ref.includes('.')) return; // totalizar só nível 1 (evita duplicações)
      const meses = Array.isArray(r.meses) ? r.meses : [];
      for (let i = 0; i < 12; i++) {
        totals[i] += Number(meses[i] || 0) || 0;
      }
    });
    const cells = totalsRow.querySelectorAll('th,td');
    for (let i = 1; i <= 12; i++) {
      const cell = cells[i];
      const v = totals[i - 1];
      if (cell) cell.textContent = v ? fmt.format(v) : '';
    }
    grand = totals.reduce((acc, v) => acc + (Number(v || 0) || 0), 0);
    const totalCell = cells[13];
    if (totalCell) totalCell.textContent = grand ? fmt.format(grand) : '';

    // atualizar totais por linha (todas as linhas)
    rows.forEach(r => {
      const ref = (r.ref || '').toString().trim();
      if (!ref) return;
      const meses = Array.isArray(r.meses) ? r.meses : [];
      const sum = meses.slice(0, 12).reduce((acc, v) => acc + (Number(v || 0) || 0), 0);
      const td = tbody?.querySelector?.(`td.orc-row-total[data-ref="${CSS.escape(ref)}"][data-total="1"]`);
      if (td) td.textContent = sum ? fmt.format(sum) : '';
    });
  }

  async function load() {
    const ano = parseInt(anoInput?.value, 10) || defaultYear;
    setLoading('A carregar...');
    setStatus('');
    try {
      const qs = new URLSearchParams({ ano: String(ano) });
      const res = await fetch(`/api/orcamento?${qs.toString()}`);
      const data = await res.json().catch(() => ({}));
      if (!res.ok || data.error) throw new Error(data.error || res.statusText);
      lastData = data;
      render(data);
      buildIndex(data);
      renderTotals();
    } catch (err) {
      tbody.innerHTML = `<tr><td colspan="14" class="text-center text-danger">${escapeHtml(err.message || 'Erro')}</td></tr>`;
    }
  }

  function scheduleSave() {
    if (saveTimer) clearTimeout(saveTimer);
    saveTimer = setTimeout(flushSave, 450);
  }

  async function flushSave() {
    if (!pending.size) return;
    const ano = parseInt(anoInput?.value, 10) || defaultYear;
    const updates = Array.from(pending.values());
    pending.clear();
    setStatus('A gravar...', 'orc-saving');
    try {
      const res = await fetch('/api/orcamento/batch', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ano, updates })
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok || data.error) throw new Error(data.error || res.statusText);
      setStatus('Gravado', 'orc-saved');
    } catch (err) {
      setStatus('Erro ao gravar', '');
      alert(err.message || 'Erro ao gravar');
    }
  }

  tbody?.addEventListener('change', (e) => {
    const input = e.target.closest('input.orc-input');
    if (!input) return;
    const familia = (input.dataset.familia || '').trim();
    const mes = parseInt(input.dataset.mes || '0', 10) || 0;
    const valor = Math.round(toNumber(input.value));
    input.value = valor ? fmt.format(valor) : '';
    if (!familia || mes < 1 || mes > 12) return;
    applyLocalUpdate(familia, mes, valor);
    pending.set(`${familia}|${mes}`, { familia, mes, valor });
    scheduleSave();
  });

  btnAplicar?.addEventListener('click', load);
  btnReplicarJan?.addEventListener('click', () => {
    if (!tbody) return;
    if (!confirm('Replicar os valores de Janeiro para os restantes meses nas famílias editáveis?')) return;
    const janInputs = Array.from(tbody.querySelectorAll('input.orc-input[data-mes="1"]'));
    janInputs.forEach((janInput) => {
      const familia = (janInput.dataset.familia || '').trim();
      if (!familia) return;
      const janVal = Math.round(toNumber(janInput.value));
      for (let mes = 2; mes <= 12; mes++) {
        const inp = tbody.querySelector(`input.orc-input[data-familia="${CSS.escape(familia)}"][data-mes="${mes}"]`);
        if (!inp) continue;
        inp.value = janVal ? fmt.format(janVal) : '';
        applyLocalUpdate(familia, mes, janVal);
        pending.set(`${familia}|${mes}`, { familia, mes, valor: janVal });
      }
      pending.set(`${familia}|1`, { familia, mes: 1, valor: janVal });
      applyLocalUpdate(familia, 1, janVal);
    });
    scheduleSave();
  });

  load();
});
