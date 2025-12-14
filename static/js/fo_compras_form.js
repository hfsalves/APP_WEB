// static/js/fo_compras_form.js
// Cabeçalho FO + linhas FN com linhas em memória (só grava no final)

const FO_TABLE = 'FO';
const FN_TABLE = 'FN';

let currentFoStamp = window.FO_STAMP || '';
let editingFnStamp = null;
let linesData = [];
let deletedLineIds = [];

const returnTo = window.RETURN_TO || '/generic/view/FO/';
const form = document.getElementById('foForm');
const btnSaveFo = document.getElementById('btnSaveFo');
const btnDeleteFo = document.getElementById('btnDeleteFo');
const btnCancelFo = document.getElementById('btnCancelFo');
const btnAddLine = document.getElementById('btnAddLine');
const linesTableBody = document.querySelector('#linesTable tbody');
const lineModalEl = document.getElementById('lineModal');
const btnSaveLine = document.getElementById('btnSaveLine');
const lineModal = lineModalEl ? new bootstrap.Modal(lineModalEl) : null;
const overlay = document.getElementById('loadingOverlay');
const overlayText = overlay?.querySelector('.loading-text');

const foFields = [
  'FOSTAMP',
  'DOCNOME', 'ADOC', 'DATA', 'PDATA',
  'NO', 'NOME', 'NCONT', 'CCUSTO',
  'MORADA', 'LOCAL', 'CODPOST',
  'TPSTAMP', 'OLLOCAL', 'TPDESC',
  'ETTILIQ', 'ETTIVA', 'ETOTAL'
];
const fnFields = ['FNSTAMP','REF','DESIGN','UNIDADE','TAXAIVA','QTT','IVA','IVAINCL','TABIVA','LORDEM','ETILIQUIDO','EPV','FNCCUSTO','FAMILIA'];

function randomStamp() {
  if (crypto.randomUUID) return crypto.randomUUID().replace(/-/g, '').toUpperCase().slice(0, 25);
  return Math.random().toString(36).slice(2).toUpperCase().padEnd(25, 'X').slice(0, 25);
}
const isTempId = (id) => typeof id === 'string' && id.startsWith('TMP_'); // legacy
const isNewLine = (line) => line && (line.__new === true || isTempId(line.FNSTAMP));

function setFoFormValues(data = {}) {
  foFields.forEach(f => {
    const el = document.getElementById(f);
    if (!el) return;
    if (el.type === 'date') {
      const v = data[f];
      if (v) {
        const d = new Date(v);
        if (!Number.isNaN(d)) el.value = d.toISOString().slice(0, 10);
      }
    } else {
      el.value = (data[f] ?? '').toString().trim();
    }
  });

  // garante seleção correta em DOCNOME mesmo com espaços/maiúsculas
  const docSel = document.getElementById('DOCNOME');
  if (docSel && data.DOCNOME) {
    const target = data.DOCNOME.toString().trim();
    let matched = false;
    Array.from(docSel.options).forEach(opt => {
      const val = (opt.value || '').trim();
      const text = (opt.textContent || '').trim();
      if (!matched && (val === target || text === target)) {
        opt.selected = true;
        matched = true;
      }
    });
  }
}

function getFoPayload() {
  const payload = {};
  foFields.forEach(f => {
    const el = document.getElementById(f);
    if (!el) return;
    if (el.type === 'date') {
      payload[f] = el.value || null;
    } else {
      payload[f] = el.value;
    }
  });
  if (!payload.FOSTAMP) payload.FOSTAMP = currentFoStamp || randomStamp();
  const todayIso = new Date().toISOString();
  const todayDate = todayIso.slice(0, 10);
  const todayTime = todayIso.slice(11, 16);
  const dataBase = payload.DATA || todayDate;
  payload.TIPO = payload.TIPO || 'FO';
  payload.DOCDATA = payload.DOCDATA || dataBase;
  payload.FOANO = payload.FOANO || Number(dataBase.slice(0, 4)) || 0;
  payload.DOCCODE = payload.DOCCODE || 0;
  payload.PLANO = payload.PLANO ?? 0;
  payload.ETTILIQ = Number(payload.ETTILIQ) || 0;
  payload.ETTIVA = Number(payload.ETTIVA) || 0;
  payload.ETOTAL = Number(payload.ETTOTAL) || (payload.ETTILIQ + payload.ETTIVA) || 0;
  payload.EIVAIN = payload.EIVAIN || 0;
  payload.EFINV = payload.EFINV || 0;
  payload.EIVAV1 = payload.EIVAV1 || 0;
  payload.EIVAV2 = payload.EIVAV2 || 0;
  payload.EIVAV3 = payload.EIVAV3 || 0;
  payload.EIVAV4 = payload.EIVAV4 || 0;
  payload.EIVAV5 = payload.EIVAV5 || 0;
  payload.EIVAV6 = payload.EIVAV6 || 0;
  payload.EIVAV7 = payload.EIVAV7 || 0;
  payload.EIVAV8 = payload.EIVAV8 || 0;
  payload.EIVAV9 = payload.EIVAV9 || 0;
  payload.MORADA = payload.MORADA || '';
  payload.LOCAL = payload.LOCAL || '';
  payload.CODPOST = payload.CODPOST || '';
  payload.NMAPROV = payload.NMAPROV || '';
  payload.DTAPROV = payload.DTAPROV || dataBase;
  payload.APROVADO = payload.APROVADO ?? 0;
  payload.NOME2 = payload.NOME2 || '';
  payload.TPSTAMP = payload.TPSTAMP || 'WEB';
  payload.OLLOCAL = payload.OLLOCAL || 'WEB';
  payload.OUSRINIS = payload.OUSRINIS || 'WEB';
  payload.OUSRDATA = payload.OUSRDATA || todayDate;
  payload.OUSRHORA = payload.OUSRHORA || todayTime;
  return payload;
}

async function loadFo() {
  if (!currentFoStamp) return;
  const res = await fetch(`/generic/api/${FO_TABLE}/${currentFoStamp}`);
  if (!res.ok) return;
  const data = await res.json();
  setFoFormValues(data);
}

async function loadDocnomeOptions() {
  const sel = document.getElementById('DOCNOME');
  if (!sel) return;
  try {
    const res = await fetch('/generic/api/options?query=' + encodeURIComponent('SELECT CMDESC FROM V_FO_CM'));
    if (!res.ok) throw new Error(res.statusText);
    const opts = await res.json();
    const current = sel.value;
    sel.innerHTML = '<option value="">---</option>';
    opts.forEach(o => {
      const v = typeof o === 'object' ? Object.values(o)[0] : o;
      const opt = document.createElement('option');
      opt.value = v ?? '';
      opt.textContent = v ?? '';
      sel.append(opt);
    });
    if (current) sel.value = current;
  } catch (e) {
    console.error('Erro ao carregar DOCNOME options', e);
  }
}

async function loadCcustOptions() {
  const sels = [document.getElementById('CCUSTO'), document.getElementById('FN_FNCCUSTO')].filter(Boolean);
  if (!sels.length) return;
  try {
    const res = await fetch('/generic/api/options?query=' + encodeURIComponent('SELECT CCUSTO FROM V_CCT'));
    if (!res.ok) throw new Error(res.statusText);
    const opts = await res.json();
    sels.forEach(sel => {
      const current = sel.value;
      sel.innerHTML = '<option value="">---</option>';
      opts.forEach(o => {
        const v = typeof o === 'object' ? Object.values(o)[0] : o;
        const opt = document.createElement('option');
        opt.value = v ?? '';
        opt.textContent = v ?? '';
        sel.append(opt);
      });
      if (current) sel.value = current;
    });
  } catch (e) {
    console.error('Erro ao carregar CCUSTO options', e);
  }
}

async function loadTaxaOptions() {
  const sel = document.getElementById('FN_TABIVA');
  const taxaEl = document.getElementById('FN_TAXAIVA');
  if (!sel) return;
  try {
    const res = await fetch('/generic/api/fo/taxas');
    if (!res.ok) throw new Error(res.statusText);
    const opts = await res.json();
    const current = sel.value;
    sel.innerHTML = '<option value="">---</option>';
    opts.forEach(o => {
      const tab = o.TABIVA ?? (Array.isArray(o) ? o[0] : '');
      const taxa = o.TAXAIVA ?? (Array.isArray(o) ? o[1] : '');
      const opt = document.createElement('option');
      opt.value = tab ?? '';
      opt.textContent = `${tab ?? ''} - ${taxa ?? ''}`;
      opt.dataset.taxa = taxa ?? '';
      sel.append(opt);
    });
    if (current) sel.value = current;
    if (taxaEl && sel.selectedOptions[0]) {
      taxaEl.value = sel.selectedOptions[0].dataset.taxa || '';
    }
  } catch (e) {
    console.error('Erro ao carregar TABIVA options', e);
  }
}

function bindTabivaListener() {
  const sel = document.getElementById('FN_TABIVA');
  const taxaEl = document.getElementById('FN_TAXAIVA');
  if (!sel || !taxaEl) return;
  sel.addEventListener('change', () => {
    const opt = sel.selectedOptions[0];
    taxaEl.value = opt?.dataset?.taxa || '';
  });
}
async function loadTpOptions() {
  const sel = document.getElementById('TPDESC');
  if (!sel) return;
  try {
    const res = await fetch('/generic/api/fo/tp_options');
    if (!res.ok) throw new Error(res.statusText);
    const data = await res.json();
    const current = sel.value;
    sel.innerHTML = '<option value="">---</option>';
    data.forEach(item => {
      const opt = document.createElement('option');
      opt.value = item.TPDESC || item.tpdesc || '';
      opt.textContent = item.TPDESC || item.tpdesc || '';
      opt.dataset.tpstamp = item.TPSTAMP || '';
      opt.dataset.dias = item.DIAS ?? '';
      opt.dataset.ollocal = item.OLLOCAL || '';
      sel.append(opt);
    });
    if (current) sel.value = current;
  } catch (e) {
    console.error('Erro ao carregar TPDESC options', e);
  }
}

function applyTpSelection() {
  const sel = document.getElementById('TPDESC');
  if (!sel) return;
  const opt = sel.options[sel.selectedIndex];
  const tpstampEl = document.getElementById('TPSTAMP');
  const ollocalEl = document.getElementById('OLLOCAL');
  const dias = opt ? parseInt(opt.dataset.dias || '0', 10) : 0;
  if (tpstampEl) tpstampEl.value = opt?.dataset?.tpstamp || '';
  if (ollocalEl) ollocalEl.value = opt?.dataset?.ollocal || '';

  const dataEl = document.getElementById('DATA');
  const pdataEl = document.getElementById('PDATA');
  if (dataEl && pdataEl && dataEl.value && Number.isInteger(dias)) {
    const d = new Date(dataEl.value);
    if (!Number.isNaN(d)) {
      d.setDate(d.getDate() + dias);
      pdataEl.value = d.toISOString().slice(0, 10);
    }
  }
}

function bindNomeAutocomplete() {
  const input = document.getElementById('NOME');
  const menu = document.getElementById('nomeSuggestions');
  if (!input || !menu) return;

  let debounceTimer;

  const closeMenu = () => {
    menu.classList.remove('show');
    menu.innerHTML = '';
  };

  const selectItem = (item) => {
    input.value = item.NOME || '';
    const map = {
      'NO': 'NO',
      'NCONT': 'NCONT',
      'MORADA': 'MORADA',
      'LOCAL': 'LOCAL',
      'CODPOST': 'CODPOST'
    };
    Object.entries(map).forEach(([src, dest]) => {
      const el = document.getElementById(dest);
      if (el) el.value = item[src] || '';
    });
    closeMenu();
  };

  const renderMenu = (items) => {
    if (!Array.isArray(items) || !items.length) {
      closeMenu();
      return;
    }
    menu.innerHTML = '';
    items.forEach(it => {
      const a = document.createElement('a');
      a.className = 'dropdown-item';
      a.href = '#';
      a.textContent = `${it.NOME || ''}`;
      a.addEventListener('click', (e) => {
        e.preventDefault();
        selectItem(it);
      });
      menu.appendChild(a);
    });
    menu.style.position = 'absolute';
    menu.style.left = '0';
    menu.style.top = `${input.offsetHeight}px`;
    menu.classList.add('show');
  };

  input.addEventListener('input', () => {
    const term = (input.value || '').trim();
    if (term.length < 2) {
      closeMenu();
      return;
    }
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(async () => {
      try {
        const url = `/generic/api/fo/search_cliente?q=${encodeURIComponent(term)}`;
        const res = await fetch(url);
        if (!res.ok) throw new Error(res.statusText);
        const data = await res.json();
        renderMenu(data);
      } catch (e) {
        console.error('autocomplete NOME error', e);
        closeMenu();
      }
    }, 200);
  });

  document.addEventListener('click', (e) => {
    if (!menu.contains(e.target) && !input.contains(e.target)) {
      closeMenu();
    }
  });
}

function bindRefAutocomplete() {
  const input = document.getElementById('FN_REF');
  const menu = document.getElementById('refSuggestions');
  if (!input || !menu) return;

  let debounceTimer;

  const closeMenu = () => {
    menu.classList.remove('show');
    menu.innerHTML = '';
  };

  const applyTabivaFromSelect = () => {
    const tabSel = document.getElementById('FN_TABIVA');
    const taxaEl = document.getElementById('FN_TAXAIVA');
    if (tabSel && taxaEl && tabSel.value) {
      const opt = tabSel.selectedOptions[0];
      taxaEl.value = opt?.dataset?.taxa || '';
    }
  };

  const selectItem = (item) => {
    const fields = {
      'REF': 'FN_REF',
      'DESIGN': 'FN_DESIGN',
      'FAMILIA': 'FN_FAMILIA',
      'TABIVA': 'FN_TABIVA'
    };
    Object.entries(fields).forEach(([src, dest]) => {
      const el = document.getElementById(dest);
      if (!el) return;
      el.value = item[src] || '';
    });
    applyTabivaFromSelect();
    recalcModalEtiliq();
    closeMenu();
  };

  const renderMenu = (items) => {
    if (!Array.isArray(items) || !items.length) {
      closeMenu();
      return;
    }
    menu.innerHTML = '';
    items.forEach(it => {
      const a = document.createElement('a');
      a.className = 'dropdown-item';
      a.href = '#';
      a.textContent = `${it.REF || ''}`;
      a.addEventListener('click', (e) => {
        e.preventDefault();
        selectItem(it);
      });
      menu.appendChild(a);
    });
    // posicionar relativo ao wrapper (mesma linha) com largura = 2x REF (máx 480px)
    try {
      const wrapper = input.closest('.position-relative') || input.parentElement;
      if (wrapper && getComputedStyle(wrapper).position === 'static') {
        wrapper.style.position = 'relative';
      }
      const base = input.offsetWidth || input.getBoundingClientRect().width || 0;
      const targetWidth = Math.min((base || 0) * 2, 480);
      menu.style.position = 'absolute';
      menu.style.left = '0';
      menu.style.top = `${input.offsetHeight}px`;
      if (targetWidth > 0) menu.style.width = `${targetWidth}px`;
      menu.style.zIndex = 2000;
    } catch (_) {
      menu.style.position = 'absolute';
      menu.style.left = '0';
      menu.style.top = `${input.offsetHeight}px`;
    }
    menu.classList.add('show');
  };

  input.addEventListener('input', () => {
    const term = (input.value || '').trim();
    if (term.length < 2) {
      closeMenu();
      return;
    }
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(async () => {
      try {
        const res = await fetch(`/generic/api/fo/search_artigos?q=${encodeURIComponent(term)}`);
        if (!res.ok) throw new Error(res.statusText);
        const data = await res.json();
        renderMenu(data);
      } catch (e) {
        console.error('autocomplete REF error', e);
        closeMenu();
      }
    }, 200);
  });

  document.addEventListener('click', (e) => {
    if (!menu.contains(e.target) && !input.contains(e.target)) {
      closeMenu();
    }
  });
}

async function loadLines() {
  if (!linesTableBody) return;
  if (!currentFoStamp) {
    linesData = [];
    renderLines();
    recalcTotals();
    return;
  }
  try {
    const res = await fetch(`/generic/api/${FN_TABLE}?FOSTAMP=${encodeURIComponent(currentFoStamp)}`);
    if (!res.ok) throw new Error(res.statusText);
    linesData = await res.json();
    deletedLineIds = [];
    renderLines();
    recalcTotals();
  } catch {
    linesTableBody.innerHTML = '<tr><td colspan="14" class="text-danger">Erro ao carregar linhas</td></tr>';
  }
}

function renderLines() {
  if (!linesTableBody) return;
  if (!linesData.length) {
    linesTableBody.innerHTML = '<tr><td colspan="14" class="text-muted">Sem linhas</td></tr>';
    return;
  }
  linesTableBody.innerHTML = '';
  linesData.forEach(r => {
    // garantir ETILIQUIDO calculado localmente se possível
    const qtt = Number(r.QTT);
    const epv = Number(r.EPV);
    if (Number.isFinite(qtt) && Number.isFinite(epv)) {
      r.ETILIQUIDO = (qtt * epv).toFixed(2);
    }
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${r.REF || ''}</td>
      <td>${r.DESIGN || ''}</td>
      <td>${r.QTT ?? ''}</td>
      <td>${r.UNIDADE || ''}</td>
      <td>${r.EPV ?? ''}</td>
      <td>${r.ETILIQUIDO ?? ''}</td>
      <td>${r.TABIVA ?? ''}</td>
      <td>${r.TAXAIVA ?? ''}</td>
      <td>${r.IVAINCL ?? ''}</td>
      <td>${r.FNCCUSTO || ''}</td>
      <td>${r.FAMILIA || ''}</td>
      <td class="text-end">
        <button class="btn btn-sm btn-outline-secondary me-1" data-action="edit" data-id="${r.FNSTAMP}" title="Editar"><i class="fa fa-pen"></i></button>
        <button class="btn btn-sm btn-outline-danger" data-action="delete" data-id="${r.FNSTAMP}" title="Apagar"><i class="fa fa-trash"></i></button>
      </td>
    `;
    linesTableBody.appendChild(tr);
  });
  recalcTotals();
}

async function saveFo() {
  // mostra overlay
  if (overlay) {
    overlay.style.display = 'flex';
    if (overlayText) overlayText.textContent = window.SAVE_OVERLAY_TEXT || 'A gravar...';
    requestAnimationFrame(() => overlay.style.opacity = '1');
  }

  if (form && !form.checkValidity()) {
    if (overlay) {
      overlay.style.opacity = '0';
      setTimeout(() => overlay.style.display = 'none', 200);
    }
    form.reportValidity?.();
    return;
  }
  const payload = getFoPayload();
  if (!payload.NO) payload.NO = 0;
  if (!payload.PDATA && payload.DATA) payload.PDATA = payload.DATA;
  const isNew = !currentFoStamp;
  const url = isNew ? `/generic/api/${FO_TABLE}` : `/generic/api/${FO_TABLE}/${currentFoStamp}`;
  const method = isNew ? 'POST' : 'PUT';
  let res;
  try {
    res = await fetch(url, {
      method,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
  } catch (net) {
    if (overlay) {
      overlay.style.opacity = '0';
      setTimeout(() => overlay.style.display = 'none', 200);
    }
    alert('Erro de rede: ' + net.message);
    return;
  }
  if (!res.ok) {
    let msg = res.statusText;
    try {
      const err = await res.json();
      msg = err.error || msg;
    } catch (_) {}
    if (overlay) {
      overlay.style.opacity = '0';
      setTimeout(() => overlay.style.display = 'none', 200);
    }
    alert('Erro ao gravar FO: ' + msg);
    return;
  }
  currentFoStamp = payload.FOSTAMP;
  history.replaceState({}, '', `${location.pathname.replace(/\/$/, '')}/${currentFoStamp}${location.search}`);
  await saveAllLines();
  await loadFo();
  await loadLines();
  window.location.href = returnTo;
}

async function deleteFo() {
  if (!currentFoStamp) {
    alert('Nada para eliminar.');
    return;
  }
  if (!confirm('Eliminar este FO?')) return;
  const res = await fetch(`/generic/api/${FO_TABLE}/${currentFoStamp}`, { method: 'DELETE' });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    alert('Erro ao eliminar: ' + (err.error || res.statusText));
    return;
  }
  window.location.href = returnTo;
}

function openLineModal(data = {}) {
  editingFnStamp = data.FNSTAMP || null;
  fnFields.forEach(f => {
    const el = document.getElementById(`FN_${f}`);
    if (!el) return;
    if (f === 'FNSTAMP') {
      el.value = data[f] || '';
      el.readOnly = true;
      return;
    }
    if (el.type === 'checkbox') {
      el.checked = (data[f] === 1 || data[f] === '1' || data[f] === true);
    } else {
      el.value = data[f] ?? '';
    }
  });
  // default FNCCUSTO com CCUSTO de cabeçalho se estiver vazio
  const fnCcusto = document.getElementById('FN_FNCCUSTO');
  const cabCcusto = document.getElementById('CCUSTO');
  if (fnCcusto && !fnCcusto.value && cabCcusto) {
    fnCcusto.value = cabCcusto.value || '';
  }
  recalcModalEtiliq();
  lineModal?.show();
}

function getLinePayload() {
  const payload = {};
  fnFields.forEach(f => {
    const el = document.getElementById(`FN_${f}`);
    if (!el) return;
    if (el.type === 'checkbox') {
      payload[f] = el.checked ? 1 : 0;
    } else {
      payload[f] = el.value;
    }
  });
  payload.FOSTAMP = currentFoStamp || payload.FOSTAMP || null;
  if (!payload.FNSTAMP) payload.FNSTAMP = randomStamp();
  return payload;
}

async function saveLine() {
  recalcModalEtiliq();
  const payload = getLinePayload();
  if (!editingFnStamp) {
    payload.__new = true;
  }
  const idx = linesData.findIndex(l => l.FNSTAMP === payload.FNSTAMP);
  if (idx >= 0) {
    linesData[idx] = { ...linesData[idx], ...payload };
  } else {
    linesData.push(payload);
  }
  lineModal?.hide();
  renderLines();
  recalcTotals();
}

async function deleteLine(fnStamp) {
  if (!fnStamp) return;
  if (!confirm('Eliminar esta linha?')) return;
  const idx = linesData.findIndex(l => l.FNSTAMP === fnStamp);
  if (idx >= 0) {
    const removed = linesData.splice(idx, 1)[0];
    if (!isTempId(removed.FNSTAMP)) {
      deletedLineIds.push(removed.FNSTAMP);
    }
  }
  renderLines();
  recalcTotals();
}

async function saveAllLines() {
  for (const line of linesData) {
    const isNew = isNewLine(line);
    const body = { ...line, FOSTAMP: currentFoStamp };
    const url = isNew ? `/generic/api/${FN_TABLE}` : `/generic/api/${FN_TABLE}/${line.FNSTAMP}`;
    const method = isNew ? 'POST' : 'PUT';
    const res = await fetch(url, {
      method,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      alert('Erro ao gravar linha: ' + (err.error || res.statusText));
      throw new Error(err.error || res.statusText);
    }
    if (isNew) {
      line.__new = false;
    }
  }
  for (const id of deletedLineIds) {
    await fetch(`/generic/api/${FN_TABLE}/${id}`, { method: 'DELETE' });
  }
  deletedLineIds = [];
  recalcTotals();
}

function recalcModalEtiliq() {
  const qttEl = document.getElementById('FN_QTT');
  const epvEl = document.getElementById('FN_EPV');
  const etEl = document.getElementById('FN_ETILIQUIDO');
  if (!qttEl || !epvEl || !etEl) return;
  const qtt = Number(qttEl.value);
  const epv = Number(epvEl.value);
  if (Number.isFinite(qtt) && Number.isFinite(epv)) {
    etEl.value = (qtt * epv).toFixed(2);
  }
}

function recalcTotals() {
  const toNum = (v) => {
    const n = Number(v);
    return Number.isFinite(n) ? n : 0;
  };
  let totalLiquido = 0;
  let totalIva = 0;
  linesData.forEach(line => {
    const qtt = toNum(line.QTT);
    const epv = toNum(line.EPV);
    const base = Number.isFinite(qtt) && Number.isFinite(epv) ? qtt * epv : toNum(line.ETILIQUIDO);
    const taxa = toNum(line.TAXAIVA);
    const ivaincl = line.IVAINCL === 1 || line.IVAINCL === '1' || line.IVAINCL === true;
    let ivaCalc = 0;
    let liquidoLinha = base;
    if (taxa > 0) {
      if (ivaincl) {
        ivaCalc = base * (taxa / (100 + taxa));
        liquidoLinha = base - ivaCalc;
      } else {
        ivaCalc = base * (taxa / 100);
      }
    }
    totalLiquido += liquidoLinha;
    totalIva += ivaCalc;
  });
  const total = totalLiquido + totalIva;
  const ettliqEl = document.getElementById('ETTILIQ');
  const ettivaEl = document.getElementById('ETTIVA');
  const etotalEl = document.getElementById('ETOTAL');
  if (ettliqEl) ettliqEl.value = totalLiquido.toFixed(2);
  if (ettivaEl) ettivaEl.value = totalIva.toFixed(2);
  if (etotalEl) etotalEl.value = total.toFixed(2);
}

document.addEventListener('DOMContentLoaded', () => {
  if (currentFoStamp) {
    loadDocnomeOptions();
    loadCcustOptions();
    loadTpOptions();
    loadTaxaOptions();
    bindTabivaListener();
    bindNomeAutocomplete();
    loadFo();
    loadLines();
  } else {
    loadDocnomeOptions();
    loadCcustOptions();
    loadTpOptions();
    loadTaxaOptions();
    bindTabivaListener();
    bindNomeAutocomplete();
    renderLines();
  }

  // defaults de datas para novo registo
  if (!currentFoStamp) {
    const hoje = new Date().toISOString().slice(0, 10);
    const dataEl = document.getElementById('DATA');
    const pdataEl = document.getElementById('PDATA');
    if (dataEl && !dataEl.value) dataEl.value = hoje;
    if (pdataEl && !pdataEl.value) pdataEl.value = hoje;
  }

  btnSaveFo?.addEventListener('click', e => { e.preventDefault(); saveFo(); });
  btnDeleteFo?.addEventListener('click', e => { e.preventDefault(); deleteFo(); });
  btnCancelFo?.addEventListener('click', e => { e.preventDefault(); window.location.href = returnTo; });

  btnAddLine?.addEventListener('click', e => {
    e.preventDefault();
    editingFnStamp = null;
    openLineModal({});
  });

  btnSaveLine?.addEventListener('click', e => { e.preventDefault(); saveLine(); });

  document.getElementById('TPDESC')?.addEventListener('change', applyTpSelection);
  document.getElementById('DATA')?.addEventListener('change', applyTpSelection);
  document.getElementById('FN_QTT')?.addEventListener('input', recalcModalEtiliq);
  document.getElementById('FN_EPV')?.addEventListener('input', recalcModalEtiliq);
  bindRefAutocomplete();

  linesTableBody?.addEventListener('click', e => {
    const btn = e.target.closest('button[data-action]');
    if (!btn) return;
    const action = btn.dataset.action;
    const id = btn.dataset.id;
    if (action === 'edit') {
      const existing = linesData.find(l => l.FNSTAMP === id);
      if (existing) {
        openLineModal(existing);
      } else {
        fetch(`/generic/api/${FN_TABLE}/${id}`)
          .then(r => r.ok ? r.json() : Promise.reject(r.statusText))
          .then(data => openLineModal(data))
          .catch(() => alert('Erro ao carregar linha'));
      }
    }
    if (action === 'delete') deleteLine(id);
  });
});
