// static/js/cc_clientes.js

const ccPendentesOnly = document.getElementById('ccPendentesOnly');
const ccSearch = document.getElementById('ccSearch');
const ccStatus = document.getElementById('ccStatus');
const ccTotalAberto = document.getElementById('ccTotalAberto');
const ccCountClientes = document.getElementById('ccCountClientes');
const ccTableBody = document.querySelector('#ccTable tbody');
const ccTable = document.getElementById('ccTable');

const ccModalEl = document.getElementById('ccModal');
const ccModal = ccModalEl ? new bootstrap.Modal(ccModalEl) : null;
const ccModalTitle = document.getElementById('ccModalTitle');
const ccModalSubtitle = document.getElementById('ccModalSubtitle');
const ccModalPendentesOnly = document.getElementById('ccModalPendentesOnly');
const ccModalTotal = document.getElementById('ccModalTotal');
const ccModalTableBody = document.querySelector('#ccModalTable tbody');

// Assistente de recebimentos
const btnAssistRecebimentos = document.getElementById('btnAssistRecebimentos');
const recWizardModalEl = document.getElementById('recWizardModal');
const recWizardModal = recWizardModalEl ? new bootstrap.Modal(recWizardModalEl) : null;
const recSearch = document.getElementById('recSearch');
const recSelectAll = document.getElementById('recSelectAll');
const recClearAll = document.getElementById('recClearAll');
const recConfirm = document.getElementById('recConfirm');
const recSelectedTotal = document.getElementById('recSelectedTotal');
const recDate = document.getElementById('recDate');
const recStatus = document.getElementById('recStatus');
const recTableBody = document.querySelector('#recTable tbody');
const recTable = document.getElementById('recTable');

let ccRows = [];
let ccDebounce = null;
let currentCliente = null; // { no, nome }
let ccSortKey = 'SALDO_ABERTO';
let ccSortDir = 'desc';

let recRows = [];
let recSelected = new Map(); // CCSTAMP -> { row, rec }
let recDebounce = null;
let recSortKey = 'DATAVEN';
let recSortDir = 'asc';

const fmt = new Intl.NumberFormat('pt-PT', { minimumFractionDigits: 2, maximumFractionDigits: 2 });

function fmtMoney(v) {
  const n = Number(v || 0);
  return fmt.format(Number.isFinite(n) ? n : 0);
}

function setStatus(text) {
  if (ccStatus) ccStatus.textContent = text || '';
}

function setRecStatus(text) {
  if (recStatus) recStatus.textContent = text || '';
}

function escapeHtml(s) {
  return (s ?? '').toString()
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#039;');
}

function renderResumo(rows) {
  if (!ccTableBody) return;
  if (!Array.isArray(rows) || !rows.length) {
    ccTableBody.innerHTML = '<tr><td colspan="3" class="text-muted p-3">Sem clientes.</td></tr>';
    return;
  }
  ccTableBody.innerHTML = '';
  rows.forEach(r => {
    const tr = document.createElement('tr');
    tr.dataset.no = String(r.NO ?? '');
    tr.dataset.nome = (r.NOME ?? '').toString();
    const saldo = Number(r.SALDO_ABERTO || 0);
    const cls = saldo > 0 ? 'cc-badge-pos' : (saldo < 0 ? 'cc-badge-neg' : '');
    tr.innerHTML = `
      <td>${escapeHtml(String(r.NO ?? ''))}</td>
      <td>${escapeHtml((r.NOME ?? '').toString())}</td>
      <td class="text-end ${cls}">${escapeHtml(fmtMoney(saldo))}</td>
    `;
    ccTableBody.appendChild(tr);
  });
}

function updateSortIndicators() {
  const ths = ccTable?.querySelectorAll('thead th[data-sort]');
  ths?.forEach(th => {
    th.classList.remove('sort-asc', 'sort-desc');
    const key = (th.dataset.sort || '').toString().trim().toUpperCase();
    if (key && key === ccSortKey) {
      th.classList.add(ccSortDir === 'desc' ? 'sort-desc' : 'sort-asc');
    }
  });
}

function sortValue(item, key) {
  const k = (key || '').toString().trim().toUpperCase();
  if (k === 'NO') return Number(item?.NO ?? 0);
  if (k === 'SALDO_ABERTO') return Number(item?.SALDO_ABERTO ?? 0);
  if (k === 'NOME') return (item?.NOME ?? '').toString().trim();
  return (item?.[key] ?? '').toString().trim();
}

function applySortAndRender() {
  if (!Array.isArray(ccRows)) ccRows = [];
  const dir = ccSortDir === 'desc' ? -1 : 1;
  const collator = new Intl.Collator('pt-PT', { numeric: true, sensitivity: 'base' });
  ccRows.sort((a, b) => {
    const va = sortValue(a, ccSortKey);
    const vb = sortValue(b, ccSortKey);
    if (typeof va === 'number' && typeof vb === 'number') {
      const na = Number.isFinite(va) ? va : 0;
      const nb = Number.isFinite(vb) ? vb : 0;
      return dir * (na - nb);
    }
    return dir * collator.compare(String(va), String(vb));
  });
  renderResumo(ccRows);
  updateSortIndicators();
}

function setSort(key) {
  const k = (key || '').toString().trim().toUpperCase();
  if (!k) return;
  if (k === ccSortKey) {
    ccSortDir = ccSortDir === 'asc' ? 'desc' : 'asc';
  } else {
    ccSortKey = k;
    ccSortDir = (k === 'SALDO_ABERTO') ? 'desc' : 'asc';
  }
  applySortAndRender();
}

function updateRecSelectedTotal() {
  let total = 0;
  for (const v of recSelected.values()) total += Number(v?.rec || 0);
  if (recSelectedTotal) recSelectedTotal.textContent = fmtMoney(total);
}

function updateRecSortIndicators() {
  const ths = recTable?.querySelectorAll('thead th[data-sort]');
  ths?.forEach(th => {
    th.classList.remove('sort-asc', 'sort-desc');
    const key = (th.dataset.sort || '').toString().trim().toUpperCase();
    if (key && key === recSortKey) th.classList.add(recSortDir === 'desc' ? 'sort-desc' : 'sort-asc');
  });
}

function recSortValue(item, key) {
  const k = (key || '').toString().trim().toUpperCase();
  if (k === 'NO') return Number(item?.NO ?? 0);
  if (k === 'ABERTO') return Number(item?.ABERTO ?? 0);
  if (k === 'RECVAL') {
    const cc = (item?.CCSTAMP || '').toString().trim();
    const selected = recSelected.get(cc);
    return Number(selected?.rec ?? item?.ABERTO ?? 0);
  }
  if (k === 'DATAVEN') return (item?.DATAVEN ?? '').toString();
  if (k === 'NOME') return (item?.NOME ?? '').toString().trim();
  if (k === 'CMDESC') return (item?.CMDESC ?? '').toString().trim();
  if (k === 'NRDOC') return Number(item?.NRDOC ?? 0);
  return (item?.[key] ?? '').toString().trim();
}

function applyRecSortAndRender() {
  if (!Array.isArray(recRows)) recRows = [];
  const dir = recSortDir === 'desc' ? -1 : 1;
  const collator = new Intl.Collator('pt-PT', { numeric: true, sensitivity: 'base' });
  recRows.sort((a, b) => {
    const va = recSortValue(a, recSortKey);
    const vb = recSortValue(b, recSortKey);
    if (typeof va === 'number' && typeof vb === 'number') {
      const na = Number.isFinite(va) ? va : 0;
      const nb = Number.isFinite(vb) ? vb : 0;
      return dir * (na - nb);
    }
    return dir * collator.compare(String(va), String(vb));
  });
  renderRecRows(recRows);
  updateRecSelectedTotal();
  updateRecSortIndicators();
}

function setRecSort(key) {
  const k = (key || '').toString().trim().toUpperCase();
  if (!k) return;
  if (k === recSortKey) {
    recSortDir = recSortDir === 'asc' ? 'desc' : 'asc';
  } else {
    recSortKey = k;
    recSortDir = (k === 'ABERTO' || k === 'RECVAL') ? 'desc' : 'asc';
  }
  applyRecSortAndRender();
}

function renderRecRows(rows) {
  if (!recTableBody) return;
  if (!Array.isArray(rows) || !rows.length) {
    recTableBody.innerHTML = '<tr><td colspan="8" class="text-muted p-3">Sem pendentes.</td></tr>';
    return;
  }
  recTableBody.innerHTML = '';
  rows.forEach(r => {
    const cc = (r.CCSTAMP || '').toString().trim();
    const selected = recSelected.get(cc);
    const checked = !!selected;
    const max = Number(r.ABERTO || 0);
    const payVal = selected ? Number(selected.rec || 0) : max;
    const payStr = (Number.isFinite(payVal) ? payVal : 0).toFixed(2);
    const minAllowed = max < 0 ? max : 0;
    const maxAllowed = max < 0 ? 0 : max;
    const minStr = (Number.isFinite(minAllowed) ? minAllowed : 0).toFixed(2);
    const maxStr = (Number.isFinite(maxAllowed) ? maxAllowed : 0).toFixed(2);
    const safeNo = escapeHtml(String(r.NO ?? ''));
    const safeNome = escapeHtml((r.NOME ?? '').toString());
    const safeVen = escapeHtml((r.DATAVEN ?? '').toString());
    const safeDoc = escapeHtml((r.CMDESC ?? '').toString());
    const safeNr = escapeHtml(String(r.NRDOC ?? ''));
    const abertoCls = max < 0 ? 'cc-badge-neg' : (max > 0 ? 'cc-badge-pos' : '');
    recTableBody.innerHTML += `
      <tr data-ccstamp="${escapeHtml(cc)}">
        <td class="text-center">
          <input type="checkbox" class="form-check-input" data-action="pick" ${checked ? 'checked' : ''}>
        </td>
        <td>${safeNo}</td>
        <td>${safeNome}</td>
        <td>${safeVen}</td>
        <td>${safeDoc}</td>
        <td>${safeNr}</td>
        <td class="text-end fw-semibold ${abertoCls}">${escapeHtml(fmtMoney(max))}</td>
        <td class="text-end">
          <input type="number" class="form-control form-control-sm" data-field="recval" value="${escapeHtml(payStr)}" min="${escapeHtml(minStr)}" max="${escapeHtml(maxStr)}" step="0.01">
        </td>
      </tr>
    `;
  });
}

async function loadPendentesForWizard(q) {
  if (!recTableBody) return;
  setRecStatus('A carregar...');
  recTableBody.innerHTML = '<tr><td colspan="8" class="text-muted p-3">A carregar...</td></tr>';
  const res = await fetch(`/api/cc_clientes/pendentes?q=${encodeURIComponent(q || '')}`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    const msg = err.error || res.statusText;
    recTableBody.innerHTML = `<tr><td colspan="8" class="text-danger p-3">Erro: ${escapeHtml(msg)}</td></tr>`;
    setRecStatus('Erro: ' + msg);
    return;
  }
  const data = await res.json();
  recRows = data.rows || [];
  setRecStatus(`${recRows.length} pendente(s)`);
  applyRecSortAndRender();
}

function openRecWizard() {
  if (!recWizardModal) return;
  recSelected = new Map();
  recRows = [];
  updateRecSelectedTotal();
  if (recDate) {
    const d = new Date();
    if (!Number.isNaN(d)) recDate.value = d.toISOString().slice(0, 10);
  }
  recWizardModal.show();
  loadPendentesForWizard('').catch(e => setRecStatus('Erro: ' + e.message));
  setTimeout(() => recSearch?.focus(), 200);
}

async function loadResumo() {
  const q = (ccSearch?.value || '').toString().trim();
  const pend = ccPendentesOnly?.checked ? '1' : '0';
  setStatus('A carregar...');
  if (ccTableBody) ccTableBody.innerHTML = '<tr><td colspan="3" class="text-muted p-3">A carregar...</td></tr>';
  const res = await fetch(`/api/cc_clientes/resumo?q=${encodeURIComponent(q)}&pendentes=${pend}`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    const msg = err.error || res.statusText;
    setStatus('Erro: ' + msg);
    if (ccTableBody) ccTableBody.innerHTML = `<tr><td colspan="3" class="text-danger p-3">Erro: ${escapeHtml(msg)}</td></tr>`;
    return;
  }
  const data = await res.json();
  ccRows = data.items || [];
  if (ccTotalAberto) ccTotalAberto.textContent = fmtMoney(data.total_aberto);
  if (ccCountClientes) ccCountClientes.textContent = String(data.count_clientes || 0);
  applySortAndRender();
  setStatus('');
}

async function loadDetalhe(no, pendentes) {
  if (!ccModalTableBody) return;
  ccModalTableBody.innerHTML = '<tr><td colspan="9" class="text-muted p-3">A carregar...</td></tr>';
  const res = await fetch(`/api/cc_clientes/detalhe?no=${encodeURIComponent(no)}&pendentes=${pendentes ? '1' : '0'}`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    const msg = err.error || res.statusText;
    ccModalTableBody.innerHTML = `<tr><td colspan="9" class="text-danger p-3">Erro: ${escapeHtml(msg)}</td></tr>`;
    return;
  }
  const data = await res.json();
  const rows = data.rows || [];
  if (!rows.length) {
    ccModalTableBody.innerHTML = '<tr><td colspan="9" class="text-muted p-3">Sem movimentos.</td></tr>';
    if (ccModalTotal) ccModalTotal.textContent = fmtMoney(data.total_aberto || 0);
    return;
  }
  if (ccModalTotal) ccModalTotal.textContent = fmtMoney(data.total_aberto || 0);
  ccModalTableBody.innerHTML = '';
  let running = 0;
  rows.forEach(r => {
    const tr = document.createElement('tr');
    const aberto = Number(r.ABERTO || 0);
    const cls = aberto > 0 ? 'cc-badge-pos' : (aberto < 0 ? 'cc-badge-neg' : '');
    const deb = Number(r.EDEB || 0);
    const cred = Number(r.ECRED || 0);
    const delta = deb - cred;
    running += Number.isFinite(delta) ? delta : 0;
    const runCls = running > 0 ? 'cc-badge-pos' : (running < 0 ? 'cc-badge-neg' : '');
    tr.innerHTML = `
      <td>${escapeHtml(r.DATALC || '')}</td>
      <td>${escapeHtml(r.DATAVEN || '')}</td>
      <td>${escapeHtml((r.CMDESC || '').toString())}</td>
      <td>${escapeHtml((r.NRDOC || '').toString())}</td>
      <td class="text-end">${escapeHtml(fmtMoney(deb))}</td>
      <td class="text-end">${escapeHtml(fmtMoney(cred))}</td>
      <td class="text-end ${cls}">${escapeHtml(fmtMoney(aberto))}</td>
      <td class="text-end ${runCls}">${escapeHtml(fmtMoney(running))}</td>
      <td>${escapeHtml(r.CCUSTO || '')}</td>
    `;
    ccModalTableBody.appendChild(tr);
  });
}

function openModal(no, nome) {
  if (!ccModal) return;
  currentCliente = { no, nome };
  if (ccModalTitle) ccModalTitle.textContent = 'Extrato';
  if (ccModalSubtitle) ccModalSubtitle.textContent = `${no} - ${nome || ''}`.trim();
  if (ccModalPendentesOnly) ccModalPendentesOnly.checked = !!ccPendentesOnly?.checked;
  ccModal.show();
  loadDetalhe(no, ccModalPendentesOnly?.checked);
}

document.addEventListener('DOMContentLoaded', () => {
  ccTable?.querySelector('thead')?.addEventListener('click', (e) => {
    const th = e.target.closest('th[data-sort]');
    if (!th) return;
    setSort(th.dataset.sort || '');
  });

  ccSearch?.addEventListener('input', () => {
    clearTimeout(ccDebounce);
    ccDebounce = setTimeout(() => loadResumo().catch(e => setStatus('Erro: ' + e.message)), 250);
  });
  ccPendentesOnly?.addEventListener('change', () => {
    loadResumo().catch(e => setStatus('Erro: ' + e.message));
  });

  ccTableBody?.addEventListener('click', (e) => {
    const tr = e.target.closest('tr[data-no]');
    if (!tr) return;
    const no = Number(tr.dataset.no);
    const nome = tr.dataset.nome || '';
    if (!no) return;
    openModal(no, nome);
  });

  ccModalPendentesOnly?.addEventListener('change', () => {
    if (!currentCliente) return;
    loadDetalhe(currentCliente.no, ccModalPendentesOnly.checked);
  });

  btnAssistRecebimentos?.addEventListener('click', () => openRecWizard());

  recTable?.querySelector('thead')?.addEventListener('click', (e) => {
    const th = e.target.closest('th[data-sort]');
    if (!th) return;
    setRecSort(th.dataset.sort || '');
  });

  recSearch?.addEventListener('input', () => {
    clearTimeout(recDebounce);
    recDebounce = setTimeout(() => loadPendentesForWizard(recSearch.value).catch(e => setRecStatus('Erro: ' + e.message)), 250);
  });

  recSelectAll?.addEventListener('click', () => {
    recSelected = new Map();
    (recRows || []).forEach(r => {
      const cc = (r.CCSTAMP || '').toString().trim();
      if (!cc) return;
      const max = Number(r.ABERTO || 0);
      recSelected.set(cc, { row: r, rec: Number.isFinite(max) ? max : 0 });
    });
    applyRecSortAndRender();
  });

  recClearAll?.addEventListener('click', () => {
    recSelected = new Map();
    applyRecSortAndRender();
  });

  recTableBody?.addEventListener('input', (e) => {
    const input = e.target?.closest('input[data-field="recval"]');
    if (!input) return;
    const tr = input.closest('tr[data-ccstamp]');
    if (!tr) return;
    const cc = (tr.dataset.ccstamp || '').toString().trim();
    const row = (recRows || []).find(x => (x.CCSTAMP || '').toString().trim() === cc);
    if (!row) return;
    const aberto = Number(row.ABERTO || 0);
    let val = Number(input.value || 0);
    if (!Number.isFinite(val)) val = 0;
    if (aberto > 0) {
      if (val < 0) val = 0;
      if (Number.isFinite(aberto) && val > aberto) val = aberto;
    } else if (aberto < 0) {
      if (val > 0) val = 0;
      if (Number.isFinite(aberto) && val < aberto) val = aberto;
    }
    if (val !== Number(input.value || 0)) input.value = String(val);
    const selected = recSelected.get(cc);
    if (selected) {
      selected.rec = val;
      recSelected.set(cc, selected);
      updateRecSelectedTotal();
    }
  });

  recTableBody?.addEventListener('click', (e) => {
    const tr = e.target.closest('tr[data-ccstamp]');
    if (!tr) return;
    const cc = (tr.dataset.ccstamp || '').toString().trim();
    if (!cc) return;
    const checkbox = tr.querySelector('input[type="checkbox"][data-action="pick"]');
    if (!checkbox) return;
    if (e.target !== checkbox) checkbox.checked = !checkbox.checked;
    if (checkbox.checked) {
      const row = (recRows || []).find(x => (x.CCSTAMP || '').toString().trim() === cc);
      if (row) {
        const recInput = tr.querySelector('input[data-field="recval"]');
        const aberto = Number(row.ABERTO || 0);
        let val = recInput ? Number(recInput.value || 0) : aberto;
        if (!Number.isFinite(val)) val = 0;
        if (aberto > 0) {
          if (val < 0) val = 0;
          if (Number.isFinite(aberto) && val > aberto) val = aberto;
          if (val <= 0) val = Number.isFinite(aberto) ? aberto : 0;
        } else if (aberto < 0) {
          if (val > 0) val = 0;
          if (Number.isFinite(aberto) && val < aberto) val = aberto;
          if (val >= 0) val = Number.isFinite(aberto) ? aberto : 0;
        }
        if (recInput) recInput.value = (Number.isFinite(val) ? val : 0).toFixed(2);
        recSelected.set(cc, { row, rec: val });
      }
    } else {
      recSelected.delete(cc);
    }
    updateRecSelectedTotal();
  });

  recConfirm?.addEventListener('click', async () => {
    if (!recSelected.size) {
      alert('Selecione pelo menos um pendente.');
      return;
    }
    const rdate = (recDate?.value || '').toString().trim();
    if (!rdate) {
      alert('Indique a data do recebimento.');
      return;
    }
    if (!confirm('Criar recibos para os movimentos selecionados?')) return;
    recConfirm.disabled = true;
    setRecStatus('A criar recibos...');
    try {
      const payload = {
        rec_date: rdate,
        items: Array.from(recSelected.values()).map(v => ({
          ...v.row,
          PAYVAL: v.rec
        }))
      };
      const res = await fetch('/api/cc_clientes/recebimentos/criar', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.error || res.statusText);
      }
      const data = await res.json();
      const created = data.created || [];
      alert(`Recibos criados: ${created.length}`);
      recWizardModal?.hide();
      loadResumo().catch(() => {});
    } catch (e) {
      alert('Erro: ' + e.message);
      setRecStatus('Erro: ' + e.message);
    } finally {
      recConfirm.disabled = false;
    }
  });

  loadResumo().catch(e => setStatus('Erro: ' + e.message));
});
