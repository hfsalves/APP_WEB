// static/js/cc_fornecedores.js

const ccPendentesOnly = document.getElementById('ccPendentesOnly');
const ccSearch = document.getElementById('ccSearch');
const ccStatus = document.getElementById('ccStatus');
const ccTotalDivida = document.getElementById('ccTotalDivida');
const ccCountFornecedores = document.getElementById('ccCountFornecedores');
const ccTableBody = document.querySelector('#ccTable tbody');
const ccTable = document.getElementById('ccTable');

const ccModalEl = document.getElementById('ccModal');
const ccModal = ccModalEl ? new bootstrap.Modal(ccModalEl) : null;
const ccModalTitle = document.getElementById('ccModalTitle');
const ccModalSubtitle = document.getElementById('ccModalSubtitle');
const ccModalPendentesOnly = document.getElementById('ccModalPendentesOnly');
const ccModalTotal = document.getElementById('ccModalTotal');
const ccModalTableBody = document.querySelector('#ccModalTable tbody');

// Assistente de pagamentos
const btnAssistPagamentos = document.getElementById('btnAssistPagamentos');
const payWizardModalEl = document.getElementById('payWizardModal');
const payWizardModal = payWizardModalEl ? new bootstrap.Modal(payWizardModalEl) : null;
const paySearch = document.getElementById('paySearch');
const paySelectAll = document.getElementById('paySelectAll');
const payClearAll = document.getElementById('payClearAll');
const payConfirm = document.getElementById('payConfirm');
const paySelectedTotal = document.getElementById('paySelectedTotal');
const payDate = document.getElementById('payDate');
const payStatus = document.getElementById('payStatus');
const payTableBody = document.querySelector('#payTable tbody');
const payTable = document.getElementById('payTable');

let ccRows = [];
let ccDebounce = null;
let currentFornecedor = null; // { no, nome }
let ccSortKey = 'SALDO_ABERTO';
let ccSortDir = 'desc';

let payRows = [];
let paySelected = new Map(); // FCSTAMP -> { row, pay }
let payDebounce = null;
let paySortKey = 'DATAVEN';
let paySortDir = 'asc';

const fmt = new Intl.NumberFormat('pt-PT', { minimumFractionDigits: 2, maximumFractionDigits: 2 });

function fmtMoney(v) {
  const n = Number(v || 0);
  return fmt.format(Number.isFinite(n) ? n : 0);
}

function setPayStatus(text) {
  if (payStatus) payStatus.textContent = text || '';
}

function updatePaySelectedTotal() {
  let total = 0;
  for (const v of paySelected.values()) {
    total += Number(v?.pay || 0);
  }
  if (paySelectedTotal) paySelectedTotal.textContent = fmtMoney(total);
}

function updatePaySortIndicators() {
  const ths = payTable?.querySelectorAll('thead th[data-sort]');
  ths?.forEach(th => {
    th.classList.remove('sort-asc', 'sort-desc');
    const key = (th.dataset.sort || '').toString().trim().toUpperCase();
    if (key && key === paySortKey) {
      th.classList.add(paySortDir === 'desc' ? 'sort-desc' : 'sort-asc');
    }
  });
}

function paySortValue(item, key) {
  const k = (key || '').toString().trim().toUpperCase();
  if (k === 'NO') return Number(item?.NO ?? 0);
  if (k === 'ABERTO') return Number(item?.ABERTO ?? 0);
  if (k === 'PAYVAL') {
    const fc = (item?.FCSTAMP || '').toString().trim();
    const selected = paySelected.get(fc);
    return Number(selected?.pay ?? item?.ABERTO ?? 0);
  }
  if (k === 'DATAVEN') return (item?.DATAVEN ?? '').toString();
  if (k === 'NOME') return (item?.NOME ?? '').toString().trim();
  if (k === 'CMDESC') return (item?.CMDESC ?? '').toString().trim();
  if (k === 'ADOC') return (item?.ADOC ?? '').toString().trim();
  return (item?.[key] ?? '').toString().trim();
}

function applyPaySortAndRender() {
  if (!Array.isArray(payRows)) payRows = [];
  const dir = paySortDir === 'desc' ? -1 : 1;
  const collator = new Intl.Collator('pt-PT', { numeric: true, sensitivity: 'base' });
  payRows.sort((a, b) => {
    const va = paySortValue(a, paySortKey);
    const vb = paySortValue(b, paySortKey);
    if (typeof va === 'number' && typeof vb === 'number') {
      const na = Number.isFinite(va) ? va : 0;
      const nb = Number.isFinite(vb) ? vb : 0;
      return dir * (na - nb);
    }
    return dir * collator.compare(String(va), String(vb));
  });
  renderPayRows(payRows);
  updatePaySelectedTotal();
  updatePaySortIndicators();
}

function setPaySort(key) {
  const k = (key || '').toString().trim().toUpperCase();
  if (!k) return;
  if (k === paySortKey) {
    paySortDir = paySortDir === 'asc' ? 'desc' : 'asc';
  } else {
    paySortKey = k;
    paySortDir = (k === 'ABERTO' || k === 'PAYVAL') ? 'desc' : 'asc';
  }
  applyPaySortAndRender();
}

function renderPayRows(rows) {
  if (!payTableBody) return;
  if (!Array.isArray(rows) || !rows.length) {
    payTableBody.innerHTML = '<tr><td colspan="8" class="text-muted p-3">Sem pendentes.</td></tr>';
    return;
  }
  payTableBody.innerHTML = '';
  rows.forEach(r => {
    const fc = (r.FCSTAMP || '').toString().trim();
    const selected = paySelected.get(fc);
    const checked = !!selected;
    const aberto = Number(r.ABERTO || 0);
    const minVal = Math.min(0, aberto);
    const maxVal = Math.max(0, aberto);
    const payValRaw = checked ? Number(selected.pay ?? 0) : aberto;
    let payVal = Number.isFinite(payValRaw) ? payValRaw : 0;
    if (payVal < minVal) payVal = minVal;
    if (payVal > maxVal) payVal = maxVal;
    const tr = document.createElement('tr');
    tr.dataset.fcstamp = fc;
    tr.innerHTML = `
      <td class="text-center">
        <input type="checkbox" class="form-check-input" data-action="pick" ${checked ? 'checked' : ''}>
      </td>
      <td>${escapeHtml(String(r.NO ?? ''))}</td>
      <td>${escapeHtml((r.NOME ?? '').toString())}</td>
      <td>${escapeHtml(r.DATAVEN || '')}</td>
      <td>${escapeHtml((r.CMDESC ?? '').toString())}</td>
      <td>${escapeHtml((r.ADOC ?? '').toString())}</td>
      <td class="text-end ${aberto < 0 ? 'cc-badge-neg' : ''}">${escapeHtml(fmtMoney(aberto))}</td>
      <td class="text-end">
        <input type="number" step="0.01" min="${escapeHtml(minVal)}" max="${escapeHtml(maxVal)}"
               class="form-control form-control-sm text-end"
               data-field="payval"
               value="${escapeHtml((Number.isFinite(payVal) ? payVal : 0).toFixed(2))}">
      </td>
    `;
    payTableBody.appendChild(tr);
  });
}

async function loadPendentesForWizard(term) {
  if (!payWizardModal) return;
  const q = (term || '').toString().trim();
  setPayStatus('A carregar...');
  if (payTableBody) payTableBody.innerHTML = '<tr><td colspan="7" class="text-muted p-3">A carregar...</td></tr>';
  const res = await fetch(`/api/cc_fornecedores/pendentes?q=${encodeURIComponent(q)}`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    const msg = err.error || res.statusText;
    setPayStatus('Erro: ' + msg);
    if (payTableBody) payTableBody.innerHTML = `<tr><td colspan="7" class="text-danger p-3">Erro: ${escapeHtml(msg)}</td></tr>`;
    return;
  }
  const data = await res.json();
  payRows = data.rows || [];
  applyPaySortAndRender();
  setPayStatus('');
}

function openPayWizard() {
  if (!payWizardModal) return;
  paySelected = new Map();
  if (paySearch) paySearch.value = '';
  if (paySelectedTotal) paySelectedTotal.textContent = fmtMoney(0);
  if (payDate) {
    const d = new Date();
    if (!Number.isNaN(d)) payDate.value = d.toISOString().slice(0, 10);
  }
  payWizardModal.show();
  loadPendentesForWizard('').catch(e => setPayStatus('Erro: ' + e.message));
  setTimeout(() => paySearch?.focus(), 200);
}

function setStatus(text) {
  if (ccStatus) ccStatus.textContent = text || '';
}

function renderResumo(rows) {
  if (!ccTableBody) return;
  if (!Array.isArray(rows) || !rows.length) {
    ccTableBody.innerHTML = '<tr><td colspan="3" class="text-muted p-3">Sem fornecedores.</td></tr>';
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
    const key = (th.dataset.sort || '').toString().trim();
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

function escapeHtml(s) {
  return (s ?? '').toString()
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#039;');
}

async function loadResumo() {
  const q = (ccSearch?.value || '').toString().trim();
  const pend = ccPendentesOnly?.checked ? '1' : '0';
  setStatus('A carregar...');
  if (ccTableBody) ccTableBody.innerHTML = '<tr><td colspan="3" class="text-muted p-3">A carregar...</td></tr>';
  const res = await fetch(`/api/cc_fornecedores/resumo?q=${encodeURIComponent(q)}&pendentes=${pend}`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    const msg = err.error || res.statusText;
    setStatus('Erro: ' + msg);
    if (ccTableBody) ccTableBody.innerHTML = `<tr><td colspan="3" class="text-danger p-3">Erro: ${escapeHtml(msg)}</td></tr>`;
    return;
  }
  const data = await res.json();
  ccRows = data.items || [];
  if (ccTotalDivida) ccTotalDivida.textContent = fmtMoney(data.total_divida);
  if (ccCountFornecedores) ccCountFornecedores.textContent = String(data.count_fornecedores || 0);
  applySortAndRender();
  setStatus('');
}

async function loadDetalhe(no, pendentes) {
  if (!ccModalTableBody) return;
  ccModalTableBody.innerHTML = '<tr><td colspan="9" class="text-muted p-3">A carregar...</td></tr>';
  const res = await fetch(`/api/cc_fornecedores/detalhe?no=${encodeURIComponent(no)}&pendentes=${pendentes ? '1' : '0'}`);
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
    const fostamp = (r.FOSTAMP || '').toString().trim();
    const deb = Number(r.EDEB || 0);
    const cred = Number(r.ECRED || 0);
    const delta = cred - deb;
    running += Number.isFinite(delta) ? delta : 0;
    const runCls = running > 0 ? 'cc-badge-pos' : (running < 0 ? 'cc-badge-neg' : '');
    if (fostamp) {
      tr.dataset.fostamp = fostamp;
      tr.classList.add('cc-modal-row-link');
      tr.title = 'Abrir compra';
    }
    tr.innerHTML = `
      <td>${escapeHtml(r.DATALC || '')}</td>
      <td>${escapeHtml(r.DATAVEN || '')}</td>
      <td>${escapeHtml((r.CMDESC || '').toString())}</td>
      <td>${escapeHtml((r.ADOC || '').toString())}</td>
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
  currentFornecedor = { no, nome };
  if (ccModalTitle) ccModalTitle.textContent = 'Extrato';
  if (ccModalSubtitle) ccModalSubtitle.textContent = `${no} - ${nome || ''}`.trim();
  if (ccModalPendentesOnly) ccModalPendentesOnly.checked = !!ccPendentesOnly?.checked;
  ccModal.show();
  loadDetalhe(no, ccModalPendentesOnly?.checked);
}

document.addEventListener('DOMContentLoaded', () => {
  // Esta app faz scroll no .main-content por defeito. Neste ecrã, queremos
  // que o scroll seja apenas na grelha (desktop).
  const main = document.querySelector('main.main-content');
  const prevOverflowY = main ? main.style.overflowY : '';
  const applyMainScrollLock = () => {
    if (!main) return;
    const isDesktop = window.matchMedia('(min-width: 992px)').matches;
    main.style.overflowY = isDesktop ? 'hidden' : (prevOverflowY || '');
  };
  applyMainScrollLock();
  window.addEventListener('resize', applyMainScrollLock);

  loadResumo().catch(e => setStatus('Erro: ' + e.message));

  btnAssistPagamentos?.addEventListener('click', (e) => {
    e.preventDefault();
    openPayWizard();
  });

  payTable?.querySelector('thead')?.addEventListener('click', (e) => {
    const th = e.target.closest('th[data-sort]');
    if (!th) return;
    setPaySort(th.dataset.sort || '');
  });

  paySearch?.addEventListener('input', () => {
    clearTimeout(payDebounce);
    payDebounce = setTimeout(() => {
      loadPendentesForWizard(paySearch.value || '').catch(e => setPayStatus('Erro: ' + e.message));
    }, 250);
  });

  paySelectAll?.addEventListener('click', () => {
    (payRows || []).forEach(r => {
      const fc = (r.FCSTAMP || '').toString().trim();
      if (!fc) return;
      const aberto = Number(r.ABERTO || 0);
      paySelected.set(fc, { row: r, pay: Number.isFinite(aberto) ? aberto : 0 });
    });
    applyPaySortAndRender();
  });

  payClearAll?.addEventListener('click', () => {
    paySelected = new Map();
    applyPaySortAndRender();
  });

  payTableBody?.addEventListener('input', (e) => {
    const input = e.target?.closest('input[data-field="payval"]');
    if (!input) return;
    const tr = input.closest('tr[data-fcstamp]');
    if (!tr) return;
    const fc = (tr.dataset.fcstamp || '').toString().trim();
    const row = (payRows || []).find(x => (x.FCSTAMP || '').toString().trim() === fc);
    if (!row) return;
    const aberto = Number(row.ABERTO || 0);
    const minVal = Math.min(0, aberto);
    const maxVal = Math.max(0, aberto);
    let val = Number(input.value || 0);
    if (!Number.isFinite(val)) val = 0;
    if (val < minVal) val = minVal;
    if (val > maxVal) val = maxVal;
    // normalizar visualmente sem forçar caret a cada tecla
    if (val !== Number(input.value || 0)) input.value = String(val);
    const selected = paySelected.get(fc);
    if (selected) {
      selected.pay = val;
      paySelected.set(fc, selected);
      updatePaySelectedTotal();
    }
  });

  payTableBody?.addEventListener('click', (e) => {
    const tr = e.target.closest('tr[data-fcstamp]');
    if (!tr) return;
    const fc = (tr.dataset.fcstamp || '').toString().trim();
    if (!fc) return;
    const checkbox = tr.querySelector('input[type="checkbox"][data-action="pick"]');
    if (!checkbox) return;
    if (e.target !== checkbox) {
      checkbox.checked = !checkbox.checked;
    }
    if (checkbox.checked) {
      const row = (payRows || []).find(x => (x.FCSTAMP || '').toString().trim() === fc);
      if (row) {
        const payInput = tr.querySelector('input[data-field="payval"]');
        const aberto = Number(row.ABERTO || 0);
        const minVal = Math.min(0, aberto);
        const maxVal = Math.max(0, aberto);
        let val = payInput ? Number(payInput.value || 0) : aberto;
        if (!Number.isFinite(val)) val = 0;
        if (val < minVal) val = minVal;
        if (val > maxVal) val = maxVal;
        if (Math.abs(val) <= 0.005) val = Number.isFinite(aberto) ? aberto : 0;
        if (val < minVal) val = minVal;
        if (val > maxVal) val = maxVal;
        if (payInput) payInput.value = (Number.isFinite(val) ? val : 0).toFixed(2);
        paySelected.set(fc, { row, pay: val });
      }
    } else {
      paySelected.delete(fc);
    }
    updatePaySelectedTotal();
  });

  payConfirm?.addEventListener('click', async () => {
    if (!paySelected.size) {
      alert('Selecione pelo menos um pendente.');
      return;
    }
    const pdate = (payDate?.value || '').toString().trim();
    if (!pdate) {
      alert('Indique a data do pagamento.');
      return;
    }
    if (!confirm('Criar pagamentos para os movimentos selecionados?')) return;
    payConfirm.disabled = true;
    setPayStatus('A criar pagamentos...');
    try {
      const payload = {
        pay_date: pdate,
        items: Array.from(paySelected.values()).map(v => ({
          ...v.row,
          PAYVAL: v.pay
        }))
      };
      const res = await fetch('/api/cc_fornecedores/pagamentos/criar', {
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
      alert(`Pagamentos criados: ${created.length}`);
      payWizardModal?.hide();
      loadResumo().catch(() => {});
    } catch (e) {
      alert('Erro: ' + e.message);
      setPayStatus('Erro: ' + e.message);
    } finally {
      payConfirm.disabled = false;
    }
  });

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
    if (!currentFornecedor) return;
    loadDetalhe(currentFornecedor.no, ccModalPendentesOnly.checked);
  });

  // Clique numa linha do extrato (modal) abre a compra quando existir FOSTAMP
  ccModalTableBody?.addEventListener('click', (e) => {
    const tr = e.target.closest('tr[data-fostamp]');
    if (!tr) return;
    const fostamp = (tr.dataset.fostamp || '').toString().trim();
    if (!fostamp) return;
    const href = `/generic/fo_compras_form/${encodeURIComponent(fostamp)}`;
    window.open(href, '_blank', 'noopener');
  });
});
