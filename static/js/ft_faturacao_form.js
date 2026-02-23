const ftStamp = (window.FT_STAMP || '').toString().trim();
const titleEl = document.getElementById('ftTitulo');
const linesBody = document.getElementById('ftLinesBody');
const feSel = document.getElementById('FT_FESTAMP');
const ndocSel = document.getElementById('FT_NDOC');
const serieSel = document.getElementById('FT_SERIE');
const addBtn = document.getElementById('ftAddLinha');
const nomeInput = document.getElementById('FT_NOME');
const noInput = document.getElementById('FT_NO');
const nifInput = document.getElementById('FT_NCONT');
const clientDetailBtn = document.getElementById('FT_CLIENT_DETAIL');
const clientSugg = document.getElementById('FT_CLIENT_SUGG');
const clienteModalEl = document.getElementById('ftClienteModal');
const clienteModal = clienteModalEl && window.bootstrap?.Modal ? new window.bootstrap.Modal(clienteModalEl) : null;
const artigoModalEl = document.getElementById('ftArtigoModal');
const artigoModal = artigoModalEl && window.bootstrap?.Modal ? new window.bootstrap.Modal(artigoModalEl) : null;
const artigoSearchInput = document.getElementById('ftArtigoSearch');
const artigoTableBody = document.getElementById('ftArtigoTableBody');
const artigoTable = document.getElementById('ftArtigoTable');
const overlay = document.getElementById('loadingOverlay');
const overlayText = overlay?.querySelector('.loading-text');
const FT_RETURN_URL = '/generic/view/FT/';

let header = {};
let lines = [];
let feRows = [];
let ftsRows = [];
let ccustoOptions = [];
let tabivaOptions = [];
let isBlocked = false;
let clientTimer = null;
let artigoSearchTimer = null;
let artigoPickRowId = null;
let artigoRowsState = [];
let artigoSortKey = 'REF';
let artigoSortDir = 'asc';
const LAST_FE_KEY = 'ft_last_festamp';
const lastNdocKey = (festamp) => `ft_last_ndoc_${String(festamp || '').trim()}`;
const lastSerieKey = (festamp) => `ft_last_serie_${String(festamp || '').trim()}`;

const n = (v, d = 0) => {
  const x = Number(String(v ?? '').replace(',', '.'));
  return Number.isFinite(x) ? x : d;
};
const n2 = (v, d = 0) => Number(n(v, d).toFixed(2));
const fmt = (v, dec = 2) => n(v, 0).toLocaleString('pt-PT', { minimumFractionDigits: dec, maximumFractionDigits: dec });
const todayISO = () => new Date().toISOString().slice(0, 10);
const stamp = () => (crypto?.randomUUID?.().replace(/-/g, '') || `${Date.now()}${Math.random()}`.replace(/\D/g, '')).slice(0, 25).toUpperCase();
const safeDate = (v) => {
  const raw = String(v || '').trim();
  if (!raw) return todayISO();
  const s = raw.slice(0, 10);
  if (/^\d{4}-\d{2}-\d{2}$/.test(s) && s !== '1900-01-01' && s !== '0001-01-01') return s;
  const d = new Date(raw);
  if (!Number.isNaN(d.getTime())) return d.toISOString().slice(0, 10);
  return todayISO();
};

function showOverlay(message = 'A carregar...', signing = false) {
  if (!overlay) return;
  overlay.classList.toggle('ft-signing', !!signing);
  if (overlayText) {
    if (signing) {
      overlayText.innerHTML = '<span class="ft-lock-wrap"><i class="fa-solid fa-lock-open ft-lock-open"></i><i class="fa-solid fa-lock ft-lock-close"></i></span>A assinar documento...';
    } else {
      overlayText.textContent = message;
    }
  }
  overlay.style.display = 'flex';
  requestAnimationFrame(() => { overlay.style.opacity = '1'; });
}

function hideOverlay() {
  if (!overlay) return;
  overlay.style.opacity = '0';
  setTimeout(() => {
    overlay.style.display = 'none';
    overlay.classList.remove('ft-signing');
  }, 180);
}

function syncDocSelectorsFromHeader() {
  if (!header.NDOC && ftsRows.length) {
    header.NDOC = n(ftsRows[0].NDOC, 0);
    header.NMDOC = (ftsRows[0].NMDOC || '').trim();
  }
  const ndoc = String(n(header.NDOC, 0));
  if (ndocSel) ndocSel.value = ndoc;
  const series = ftsRows.filter(r => String(n(r.NDOC, 0)) === ndoc);
  if (series.length) {
    const hasCurrent = series.some(s => String(s.SERIE || '').trim() === String(header.SERIE || '').trim());
    if (!hasCurrent) header.SERIE = String(series[0].SERIE || '').trim();
  } else {
    header.SERIE = '';
  }
  if (serieSel) serieSel.value = header.SERIE || '';
}

function fillDocSelectors() {
  const ndocMap = new Map();
  ftsRows.forEach(r => {
    const nd = String(n(r.NDOC, 0));
    if (!ndocMap.has(nd)) ndocMap.set(nd, String(r.NMDOC || ''));
  });
  ndocSel.innerHTML = '<option value="">(Escolher)</option>' + Array.from(ndocMap.entries()).map(([nd, nm]) =>
    `<option value="${nd}">${nm || nd}</option>`
  ).join('');
  syncDocSelectorsFromHeader();
}

async function loadFe() {
  const r = await fetch('/api/lookups/fe');
  feRows = await r.json().catch(() => []);
  feSel.innerHTML = '<option value="">(Escolher entidade emissora)</option>' + feRows.map(x =>
    `<option value="${x.FESTAMP}">${x.NOME || ''}${x.NIF ? ` (${x.NIF})` : ''}</option>`
  ).join('');
  const lastFe = (localStorage.getItem(LAST_FE_KEY) || '').trim();
  if (lastFe && feRows.some(x => String(x.FESTAMP || '').trim() === lastFe)) {
    feSel.value = lastFe;
  }
}

async function loadCcustoOptions() {
  const ccSel = document.getElementById('FT_CCUSTO');
  if (!ccSel) return;
  try {
    const res = await fetch('/generic/api/options?query=' + encodeURIComponent('SELECT CCUSTO FROM V_CCT'));
    if (!res.ok) throw new Error(res.statusText);
    const opts = await res.json().catch(() => []);
    ccustoOptions = (Array.isArray(opts) ? opts : [])
      .map(o => (typeof o === 'object' ? Object.values(o)[0] : o))
      .filter(v => (v ?? '').toString().trim() !== '');
    const current = (header.CCUSTO || ccSel.value || '').toString().trim();
    ccSel.innerHTML = '<option value="">---</option>';
    ccustoOptions.forEach(v => {
      const opt = document.createElement('option');
      opt.value = String(v);
      opt.textContent = String(v);
      ccSel.appendChild(opt);
    });
    if (current) ccSel.value = current;
  } catch (e) {
    console.error('Erro ao carregar CCUSTO options', e);
  }
}

async function loadTaxaOptions() {
  try {
    const res = await fetch('/generic/api/fo/taxas');
    if (!res.ok) throw new Error(res.statusText);
    const opts = await res.json().catch(() => []);
    tabivaOptions = (Array.isArray(opts) ? opts : [])
      .map(o => ({
        tab: String(o?.TABIVA ?? (Array.isArray(o) ? o[0] : '')).trim(),
        taxa: n(o?.TAXAIVA ?? (Array.isArray(o) ? o[1] : 0), 0)
      }))
      .filter(x => x.tab !== '');
  } catch (e) {
    console.error('Erro ao carregar taxas de IVA', e);
    tabivaOptions = [];
  }
}

function getTaxaByTabiva(tabiva) {
  const key = String(tabiva ?? '').trim();
  if (!key) return null;
  const hit = tabivaOptions.find(x => String(x.tab) === key);
  return hit ? n(hit.taxa, 0) : null;
}

function applyArtigoToLine(row, art) {
  if (!row || !art) return;
  row.REF = art.REF || row.REF || '';
  row.DESIGN = art.DESIGN || row.DESIGN || '';
  row.UNIDADE = art.UNIDADE || row.UNIDADE || '';
  row.FAMILIA = art.FAMILIA || row.FAMILIA || '';
  if (String(art.TABIVA || '').trim() !== '') row.TABIVA = String(art.TABIVA).trim();
  const tx = n(art.TAXAIVA ?? art.IVA, NaN);
  if (Number.isFinite(tx)) row.IVA = tx;
  else {
    const tabTx = getTaxaByTabiva(row.TABIVA);
    if (tabTx != null) row.IVA = tabTx;
  }
}

function attachRefAutocompleteInline(input, row) {
  if (!input || !row) return;
  let debounceTimer;
  const menu = document.createElement('div');
  menu.className = 'dropdown-menu';
  menu.style.maxHeight = '220px';
  menu.style.overflowY = 'auto';
  menu.style.position = 'absolute';
  menu.style.zIndex = 3000;
  menu.style.minWidth = '220px';
  menu.style.display = 'none';
  document.body.appendChild(menu);

  const closeMenu = () => { menu.classList.remove('show'); menu.style.display = 'none'; };
  const positionMenu = () => {
    const rect = input.getBoundingClientRect();
    const width = Math.min((rect.width || 0) * 2, Math.max(320, rect.width));
    const left = rect.left + window.scrollX;
    const maxLeft = document.documentElement.scrollWidth - width - 16;
    const finalLeft = Math.max(0, Math.min(left, maxLeft));
    menu.style.left = `${finalLeft}px`;
    menu.style.top = `${rect.bottom + window.scrollY}px`;
    if (width) menu.style.width = `${width}px`;
  };
  const renderMenu = (items) => {
    if (!Array.isArray(items) || !items.length) { closeMenu(); return; }
    menu.innerHTML = '';
    items.forEach(item => {
      const a = document.createElement('a');
      a.href = '#';
      a.className = 'dropdown-item';
      a.textContent = `${item.REF || ''} ${item.DESIGN ? '· ' + item.DESIGN : ''}`;
      a.addEventListener('mousedown', (e) => {
        e.preventDefault();
        applyArtigoToLine(row, item);
        closeMenu();
        recalcAll();
        renderLines();
      });
      menu.appendChild(a);
    });
    positionMenu();
    menu.classList.add('show');
    menu.style.display = 'block';
  };

  input.addEventListener('input', () => {
    const term = (input.value || '').trim();
    if (term.length < 2) { closeMenu(); return; }
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(async () => {
      try {
        const res = await fetch(`/generic/api/fo/search_artigos?q=${encodeURIComponent(term)}`);
        if (!res.ok) throw new Error(res.statusText);
        const data = await res.json();
        renderMenu(data);
      } catch (_) { closeMenu(); }
    }, 180);
  });
  document.addEventListener('click', (e) => {
    if (!menu.contains(e.target) && !input.contains(e.target)) closeMenu();
  });
}

function renderArtigoModalRows(rows) {
  if (!artigoTableBody) return;
  if (!Array.isArray(rows) || !rows.length) {
    artigoTableBody.innerHTML = '<tr><td colspan="3" class="text-muted">Sem artigos.</td></tr>';
    return;
  }
  artigoTableBody.innerHTML = rows.map((r, idx) => `
    <tr data-aidx="${idx}" style="cursor:pointer;">
      <td class="artigo-ref">${r.REF || ''}</td>
      <td>${r.DESIGN || ''}</td>
      <td>${(r.FAMILIA || '')}${(r.FAMILIA_NOME || '') ? ` - ${r.FAMILIA_NOME}` : ''}</td>
    </tr>
  `).join('');
  artigoTableBody.querySelectorAll('tr[data-aidx]').forEach(tr => {
    tr.addEventListener('click', () => {
      const idx = n(tr.getAttribute('data-aidx'), -1);
      const art = rows[idx];
      const row = lines.find(x => x.FISTAMP === artigoPickRowId);
      if (!row || !art) return;
      applyArtigoToLine(row, art);
      recalcAll();
      renderLines();
      artigoModal?.hide();
    });
  });
}

function updateArtigoSortIndicators() {
  artigoTable?.querySelectorAll('thead th[data-sort]')?.forEach(th => {
    th.classList.remove('sort-asc', 'sort-desc');
    const key = (th.dataset.sort || '').trim();
    if (key === artigoSortKey) th.classList.add(artigoSortDir === 'desc' ? 'sort-desc' : 'sort-asc');
  });
}

function artigoSortValue(item, key) {
  const k = (key || '').toUpperCase();
  if (k === 'REF') return (item?.REF ?? '').toString().trim();
  if (k === 'DESIGN') return (item?.DESIGN ?? '').toString().trim();
  if (k === 'FAMILIA') {
    const cod = (item?.FAMILIA ?? '').toString().trim();
    const nome = (item?.FAMILIA_NOME ?? '').toString().trim();
    return `${cod}${nome ? ' - ' + nome : ''}`.trim();
  }
  return (item?.[key] ?? '').toString().trim();
}

function sortArtigosInPlace() {
  if (!Array.isArray(artigoRowsState) || !artigoRowsState.length) return;
  const dir = artigoSortDir === 'desc' ? -1 : 1;
  const collator = new Intl.Collator('pt-PT', { numeric: true, sensitivity: 'base' });
  artigoRowsState.sort((a, b) => dir * collator.compare(artigoSortValue(a, artigoSortKey), artigoSortValue(b, artigoSortKey)));
}

function applyArtigoSortAndRender() {
  sortArtigosInPlace();
  renderArtigoModalRows(artigoRowsState);
  updateArtigoSortIndicators();
}

function setArtigoSort(key) {
  const k = (key || '').trim().toUpperCase();
  if (!k) return;
  if (k === artigoSortKey) artigoSortDir = artigoSortDir === 'asc' ? 'desc' : 'asc';
  else {
    artigoSortKey = k;
    artigoSortDir = 'asc';
  }
  applyArtigoSortAndRender();
}

async function loadArtigoModalRows(term = '') {
  if (!artigoTableBody) return;
  artigoTableBody.innerHTML = '<tr><td colspan="3" class="text-muted">A carregar...</td></tr>';
  try {
    const q = (term || '').toString().trim();
    const res = await fetch(`/generic/api/fo/artigos?q=${encodeURIComponent(q)}&limit=200`);
    if (!res.ok) throw new Error(res.statusText);
    artigoRowsState = await res.json().catch(() => []);
    applyArtigoSortAndRender();
  } catch (_) {
    artigoTableBody.innerHTML = '<tr><td colspan="3" class="text-danger">Erro a carregar artigos.</td></tr>';
    artigoRowsState = [];
  }
}

async function loadFts() {
  const festamp = (header.FESTAMP || '').toString().trim();
  if (!festamp) {
    ftsRows = [];
    ndocSel.innerHTML = '<option value="">(Escolher)</option>';
    if (serieSel) serieSel.value = '';
    return;
  }
  const ano = n((header.FDATA || '').toString().slice(0, 4), new Date().getFullYear());
  const r = await fetch(`/api/lookups/fts?festamp=${encodeURIComponent(festamp)}&ano=${encodeURIComponent(ano)}`);
  ftsRows = await r.json().catch(() => []);
  const savedNdoc = n(localStorage.getItem(lastNdocKey(festamp)), 0);
  const savedSerie = (localStorage.getItem(lastSerieKey(festamp)) || '').trim();
  const currentNdoc = n(header.NDOC, 0);
  const hasCurrentNdoc = currentNdoc && ftsRows.some(x => n(x.NDOC, 0) === currentNdoc);
  if (!hasCurrentNdoc && savedNdoc && ftsRows.some(x => n(x.NDOC, 0) === savedNdoc)) {
    header.NDOC = savedNdoc;
    const nd = ftsRows.find(x => n(x.NDOC, 0) === savedNdoc);
    header.NMDOC = (nd?.NMDOC || '').trim();
  }
  const hasCurrentSerie = (header.SERIE || '').toString().trim();
  if (!hasCurrentSerie && savedSerie) header.SERIE = savedSerie;
  fillDocSelectors();
}

function mapHeaderToUi() {
  feSel.value = header.FESTAMP || '';
  document.getElementById('FT_FNO').value = n(header.FNO, 0) || 0;
  document.getElementById('FT_FDATA').value = safeDate(header.FDATA);
  document.getElementById('FT_PDATA').value = safeDate(header.PDATA);
  document.getElementById('FT_MOEDA').value = header.MOEDA || 'EUR';
  document.getElementById('FT_NO').value = n(header.NO, 0) || '';
  document.getElementById('FT_NOME').value = header.NOME || '';
  document.getElementById('FT_NCONT').value = header.NCONT || '';
  document.getElementById('FT_CCUSTO').value = header.CCUSTO || '';
  document.getElementById('FT_ETTILIQ').value = fmt(header.ETTILIQ, 2);
  document.getElementById('FT_ETTIVA').value = fmt(header.ETTIVA, 2);
  document.getElementById('FT_ETOTAL').value = fmt(header.ETOTAL, 2);
  titleEl.textContent = Number(header.ANULADA || 0) === 1
    ? 'Anulada'
    : (Number(header.ESTADO || 0) === 1 ? `Emitida #${n(header.FNO, 0)}` : 'Rascunho');
}

function mapUiToHeader() {
  header.FESTAMP = (feSel?.value || '').trim();
  header.NDOC = n(ndocSel?.value, 0);
  const pickedSerie = (header.SERIE || '').trim();
  const hit = ftsRows.find(r => String(n(r.NDOC, 0)) === String(header.NDOC) && String(r.SERIE || '').trim() === pickedSerie);
  header.NMDOC = (hit?.NMDOC || '').trim();
  header.SERIE = pickedSerie;
  header.FDATA = document.getElementById('FT_FDATA').value || todayISO();
  header.FTANO = Number(String(header.FDATA).slice(0, 4)) || new Date().getFullYear();
  header.PDATA = document.getElementById('FT_PDATA').value || header.FDATA;
  header.MOEDA = document.getElementById('FT_MOEDA').value || 'EUR';
  header.NO = n(document.getElementById('FT_NO').value, 0);
  header.NOME = document.getElementById('FT_NOME').value || '';
  header.NCONT = document.getElementById('FT_NCONT').value || '';
  header.CCUSTO = document.getElementById('FT_CCUSTO').value || '';
  const moradaEl = document.getElementById('FT_MORADA');
  const codpostEl = document.getElementById('FT_CODPOST');
  const localEl = document.getElementById('FT_LOCAL');
  const paisEl = document.getElementById('FT_PAIS');
  if (moradaEl) header.MORADA = moradaEl.value || '';
  if (codpostEl) header.CODPOST = codpostEl.value || '';
  if (localEl) header.LOCAL = localEl.value || '';
  if (paisEl) header.PAIS = n(paisEl.value, 0);
}

function recalcLine(line) {
  const qtt = n2(line.QTT, 0);
  const epv = n2(line.EPV, 0);
  line.QTT = qtt;
  line.EPV = epv;
  line.ETILIQUIDO = qtt * epv;
  line.ETILIQUIDO = Number(line.ETILIQUIDO.toFixed(2));
}

function recalcAll() {
  lines.forEach(recalcLine);
  let base = 0, vat = 0;
  lines.forEach(l => {
    const totalLinha = n(l.ETILIQUIDO, 0);
    const tx = n(l.IVA, 0);
    const inc = Number(l.IVAINCL || 0) === 1;
    if (tx > 0) {
      if (inc) {
        const ivaLinha = totalLinha * (tx / (100 + tx));
        base += (totalLinha - ivaLinha);
        vat += ivaLinha;
      } else {
        base += totalLinha;
        vat += (totalLinha * tx / 100);
      }
    } else {
      base += totalLinha;
    }
  });
  header.ETTILIQ = Number(base.toFixed(6));
  header.ETTIVA = Number(vat.toFixed(6));
  header.ETOTAL = Number((base + vat).toFixed(6));
  document.getElementById('FT_ETTILIQ').value = fmt(header.ETTILIQ);
  document.getElementById('FT_ETTIVA').value = fmt(header.ETTIVA);
  document.getElementById('FT_ETOTAL').value = fmt(header.ETOTAL);
}

async function fetchArtigoByRef(ref) {
  const r = await fetch(`/generic/api/fo/search_artigos?q=${encodeURIComponent(ref || '')}`);
  const arr = await r.json().catch(() => []);
  if (!r.ok || !Array.isArray(arr) || !arr.length) return null;
  return arr.find(x => String(x.REF || '').trim().toLowerCase() === String(ref || '').trim().toLowerCase()) || arr[0];
}

function renderLines() {
  if (!lines.length) {
    linesBody.innerHTML = '<tr><td colspan="11" class="text-muted">Sem linhas.</td></tr>';
    return;
  }
  const dis = isBlocked ? 'disabled' : '';
  linesBody.innerHTML = lines.map((l) => {
    const checked = Number(l.IVAINCL || 0) === 1 ? 'checked' : '';
    const lineTab = String(l.TABIVA ?? '').trim();
    const tabivaSelect = `<select ${dis} class="form-select form-select-sm" data-f="TABIVA">
      <option value="">---</option>
      ${tabivaOptions.map(t => {
        const tab = String(t.tab || '');
        const tx = n(t.taxa, 0).toLocaleString('pt-PT', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
        const sel = tab === lineTab ? 'selected' : '';
        return `<option value="${tab}" ${sel}>${tab} - ${tx}</option>`;
      }).join('')}
    </select>`;
    return `<tr data-id="${l.FISTAMP}">
      <td>
        <div class="input-group input-group-sm">
          <button type="button" ${dis} class="btn btn-outline-secondary" data-a="choose_ref" title="Escolher referência"><i class="fa fa-search"></i></button>
          <input ${dis} class="form-control form-control-sm" data-f="REF" value="${l.REF || ''}">
        </div>
      </td>
      <td><input ${dis} class="form-control form-control-sm" data-f="DESIGN" value="${l.DESIGN || ''}"></td>
      <td><input ${dis} class="form-control form-control-sm text-end" type="number" step="0.01" data-f="QTT" value="${n2(l.QTT,0)}"></td>
      <td><input ${dis} class="form-control form-control-sm" data-f="UNIDADE" value="${l.UNIDADE || ''}"></td>
      <td><input ${dis} class="form-control form-control-sm text-end" type="number" step="0.01" data-f="EPV" value="${n2(l.EPV,0)}"></td>
      <td><input class="form-control form-control-sm text-end" readonly data-f="ETILIQUIDO" value="${fmt(l.ETILIQUIDO, 2)}"></td>
      <td>${tabivaSelect}</td>
      <td class="text-center"><input ${dis} class="form-check-input" type="checkbox" data-f="IVAINCL" ${checked}></td>
      <td><input ${dis} class="form-control form-control-sm" data-f="FAMILIA" value="${l.FAMILIA || ''}"></td>
      <td><input ${dis} class="form-control form-control-sm" data-f="FICCUSTO" value="${l.FICCUSTO || header.CCUSTO || ''}"></td>
      <td class="text-end"><button ${dis} class="btn btn-sm btn-outline-danger" data-a="del">✕</button></td>
    </tr>`;
  }).join('');

  linesBody.querySelectorAll('tr[data-id]').forEach(tr => {
    const id = tr.getAttribute('data-id');
    const row = lines.find(x => x.FISTAMP === id);
    if (!row) return;
    const refInput = tr.querySelector('input[data-f="REF"]');
    if (refInput) attachRefAutocompleteInline(refInput, row);
    tr.querySelector('[data-a="choose_ref"]')?.addEventListener('click', () => {
      artigoPickRowId = row.FISTAMP;
      artigoSearchInput && (artigoSearchInput.value = '');
      loadArtigoModalRows('');
      artigoModal?.show();
      setTimeout(() => artigoSearchInput?.focus(), 200);
    });
    tr.querySelectorAll('[data-f]').forEach(inp => {
      inp.addEventListener('change', async () => {
        const f = inp.getAttribute('data-f');
        if (f === 'IVAINCL') row[f] = inp.checked ? 1 : 0;
        else row[f] = inp.value;
        if (f === 'QTT' || f === 'EPV') row[f] = n2(row[f], 0);
        if (f === 'TABIVA') {
          const tx = getTaxaByTabiva(row.TABIVA);
          if (tx != null) row.IVA = tx;
        }
        if (f === 'REF' && row.REF) {
          const art = await fetchArtigoByRef(row.REF);
          if (art) {
            row.REF = art.REF || row.REF;
            row.DESIGN = art.DESIGN || row.DESIGN;
            row.UNIDADE = art.UNIDADE || row.UNIDADE;
            row.FAMILIA = art.FAMILIA || row.FAMILIA;
            row.TABIVA = n(art.TABIVA, row.TABIVA || 0);
            row.IVA = n(art.TAXAIVA ?? art.IVA, row.IVA || 0);
          }
        }
        recalcAll();
        renderLines();
      });
    });
    tr.querySelector('[data-a="del"]')?.addEventListener('click', () => {
      lines = lines.filter(x => x.FISTAMP !== id);
      lines.forEach((x, i) => x.LORDEM = (i + 1) * 10);
      recalcAll();
      renderLines();
    });
  });
}

function newLine() {
  lines.push({
    FISTAMP: stamp(),
    FTSTAMP: ftStamp,
    NDOC: n(header.NDOC, 0),
    NMDOC: header.NMDOC || '',
    FNO: n(header.FNO, 0),
    REF: '', DESIGN: '', QTT: 1, UNIDADE: '', EPV: 0, IVA: 0, IVAINCL: 0, TABIVA: 0,
    ETILIQUIDO: 0, FAMILIA: '', FICCUSTO: header.CCUSTO || '', LORDEM: (lines.length + 1) * 10
  });
  recalcAll();
  renderLines();
}

async function loadDoc() {
  const r = await fetch(`/api/faturacao/ft/${encodeURIComponent(ftStamp)}`);
  const data = await r.json().catch(() => ({}));
  if (!r.ok || data.error) {
    alert(data.error || 'Erro ao carregar documento.');
    return;
  }
  header = data.header || {};
  if (!(header.FESTAMP || '').toString().trim()) {
    const lastFe = (localStorage.getItem(LAST_FE_KEY) || '').trim();
    if (lastFe && feRows.some(x => String(x.FESTAMP || '').trim() === lastFe)) {
      header.FESTAMP = lastFe;
    } else if (feRows.length) {
      header.FESTAMP = String(feRows[feRows.length - 1].FESTAMP || '').trim();
    }
  }
  lines = Array.isArray(data.lines) ? data.lines : [];
  isBlocked = Number(header.BLOQUEADO || 0) === 1;
  mapHeaderToUi();
  await loadFts();
  syncDocSelectorsFromHeader();
  recalcAll();
  renderLines();
  setButtons();
}

function setButtons() {
  const emitted = Number(header.ESTADO || 0) === 1 || isBlocked;
  document.getElementById('ftBtnGuardar').disabled = isBlocked;
  document.getElementById('ftBtnEmitir').disabled = isBlocked;
  document.getElementById('ftBtnAnular').disabled = Number(header.ANULADA || 0) === 1;
  addBtn.disabled = isBlocked;
  feSel.disabled = isBlocked;
  ndocSel.disabled = isBlocked;
  if (serieSel) serieSel.readOnly = true;
  if (emitted) titleEl.textContent = Number(header.ANULADA || 0) === 1 ? 'Anulada' : `Emitida #${n(header.FNO, 0)}`;
}

function hideClientSuggest() {
  if (!clientSugg) return;
  clientSugg.style.display = 'none';
  clientSugg.innerHTML = '';
}

function applyClient(c) {
  if (!c) return;
  if (noInput) noInput.value = n(c.NO, 0) || '';
  if (nomeInput) nomeInput.value = c.NOME || '';
  if (nifInput) nifInput.value = c.NIF || '';
  header.NO = n(c.NO, 0);
  header.NOME = c.NOME || '';
  header.NCONT = c.NIF || '';
  header.MORADA = c.MORADA || '';
  header.LOCAL = c.LOCAL || '';
  header.CODPOST = c.CODPOST || '';
  hideClientSuggest();
}

async function openClientDetail() {
  const no = n(noInput?.value, 0);
  if (!no) {
    alert('Selecione primeiro um cliente.');
    return;
  }
  const r = await fetch(`/api/faturacao/clientes/${encodeURIComponent(no)}`);
  const data = await r.json().catch(() => ({}));
  if (!r.ok || data.error) {
    alert(data.error || 'Erro ao ler detalhes do cliente.');
    return;
  }
  const setVal = (id, val) => {
    const el = document.getElementById(id);
    if (el) el.value = val ?? '';
  };
  setVal('FTM_NO', n(data.NO, 0) || '');
  setVal('FTM_NOME', data.NOME || '');
  setVal('FTM_NIF', data.NIF || '');
  setVal('FTM_MORADA', data.MORADA || '');
  setVal('FTM_CODPOST', data.CODPOST || '');
  setVal('FTM_LOCAL', data.LOCAL || '');
  setVal('FTM_PAIS', data.PAIS ?? '');
  if (clienteModal) clienteModal.show();
}

async function searchClients(term) {
  if (!clientSugg || isBlocked) return;
  const q = String(term || '').trim();
  if (q.length < 2) {
    hideClientSuggest();
    return;
  }
  const r = await fetch(`/api/faturacao/clientes?q=${encodeURIComponent(q)}`);
  const rows = await r.json().catch(() => []);
  if (!r.ok || !Array.isArray(rows) || !rows.length) {
    hideClientSuggest();
    return;
  }
  clientSugg.innerHTML = rows.map((x, idx) => `
    <button type="button" class="list-group-item list-group-item-action py-1 px-2" data-client-idx="${idx}">
      <div class="fw-semibold small">${x.NOME || ''}</div>
      <div class="small text-muted">NO ${n(x.NO,0)} · NIF ${x.NIF || ''} · ${x.LOCAL || ''}</div>
    </button>
  `).join('');
  clientSugg.style.display = 'block';
  clientSugg.querySelectorAll('[data-client-idx]').forEach(btn => {
    btn.addEventListener('mousedown', (ev) => {
      ev.preventDefault();
      const i = n(btn.getAttribute('data-client-idx'), -1);
      const c = rows[i];
      if (c) applyClient(c);
    });
  });
}

async function saveDoc(redirectAfter = true, reloadAfter = true) {
  if (isBlocked) return;
  mapUiToHeader();
  recalcAll();
  const payload = { header, lines };
  const r = await fetch(`/api/faturacao/ft/${encodeURIComponent(ftStamp)}/save`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
  const data = await r.json().catch(() => ({}));
  if (!r.ok || data.error) {
    alert(data.error || 'Erro ao guardar.');
    return false;
  }
  if (redirectAfter) {
    window.location.href = FT_RETURN_URL;
    return true;
  }
  if (reloadAfter) await loadDoc();
  return true;
}

async function emitirDoc() {
  if (isBlocked) return;
  showOverlay('A carregar...', true);
  try {
    const saved = await saveDoc(false, false);
    if (!saved) return;
    const r = await fetch(`/api/faturacao/ft/${encodeURIComponent(ftStamp)}/emitir`, { method: 'POST' });
    const data = await r.json().catch(() => ({}));
    if (!r.ok || data.error) {
      alert(data.error || 'Erro ao emitir.');
      return;
    }
    await loadDoc();
  } finally {
    hideOverlay();
  }
}

async function anularDoc() {
  const motivo = prompt('Motivo de anulação:') || '';
  if (motivo === null) return;
  const r = await fetch(`/api/faturacao/ft/${encodeURIComponent(ftStamp)}/anular`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ motivo })
  });
  const data = await r.json().catch(() => ({}));
  if (!r.ok || data.error) return alert(data.error || 'Erro ao anular.');
  await loadDoc();
}

async function duplicarDoc() {
  const r = await fetch(`/api/faturacao/ft/${encodeURIComponent(ftStamp)}/duplicar`, { method: 'POST' });
  const data = await r.json().catch(() => ({}));
  if (!r.ok || data.error) return alert(data.error || 'Erro ao duplicar.');
  if (data.FTSTAMP) window.location.href = `/faturacao/ft/${encodeURIComponent(data.FTSTAMP)}`;
}

function imprimirDoc() {
  if (!ftStamp) return;
  const url = `/api/faturacao/ft/${encodeURIComponent(ftStamp)}/pdf?force_html=1&_ts=${Date.now()}`;
  window.open(url, '_blank');
}

function verHtmlDoc() {
  if (!ftStamp) return;
  const url = `/api/faturacao/ft/${encodeURIComponent(ftStamp)}/pdf/html?_ts=${Date.now()}`;
  window.open(url, '_blank');
}

async function cancelarDoc() {
  const estado = Number(header.ESTADO || 0);
  if (estado === 0) {
    const ok = confirm('Cancelar este rascunho? O documento será eliminado.');
    if (!ok) return;
    const r = await fetch(`/api/faturacao/ft/${encodeURIComponent(ftStamp)}/cancelar`, { method: 'POST' });
    const data = await r.json().catch(() => ({}));
    if (!r.ok || data.error) return alert(data.error || 'Erro ao cancelar rascunho.');
    window.location.href = FT_RETURN_URL;
    return;
  }
  window.location.href = FT_RETURN_URL;
}

feSel?.addEventListener('change', async () => {
  header.FESTAMP = (feSel.value || '').trim();
  if (header.FESTAMP) localStorage.setItem(LAST_FE_KEY, header.FESTAMP);
  header.NDOC = 0;
  header.NMDOC = '';
  header.SERIE = '';
  await loadFts();
  syncDocSelectorsFromHeader();
});

ndocSel?.addEventListener('change', () => {
  header.NDOC = n(ndocSel.value, 0);
  const firstSerie = ftsRows.find(r => String(n(r.NDOC, 0)) === String(header.NDOC));
  header.NMDOC = firstSerie?.NMDOC || '';
  header.SERIE = String(firstSerie?.SERIE || '').trim();
  const festamp = (header.FESTAMP || '').toString().trim();
  if (festamp) {
    if (header.NDOC) localStorage.setItem(lastNdocKey(festamp), String(header.NDOC));
    if (header.SERIE) localStorage.setItem(lastSerieKey(festamp), header.SERIE);
  }
  syncDocSelectorsFromHeader();
  lines.forEach(l => { l.NDOC = header.NDOC; l.NMDOC = header.NMDOC; });
});

serieSel?.addEventListener('change', () => {});

document.getElementById('FT_FDATA')?.addEventListener('change', async () => {
  header.FDATA = document.getElementById('FT_FDATA').value || todayISO();
  await loadFts();
  syncDocSelectorsFromHeader();
});

document.getElementById('ftBtnGuardar')?.addEventListener('click', saveDoc);
document.getElementById('ftBtnEmitir')?.addEventListener('click', emitirDoc);
document.getElementById('ftBtnAnular')?.addEventListener('click', anularDoc);
document.getElementById('ftBtnDuplicar')?.addEventListener('click', duplicarDoc);
document.getElementById('ftBtnImprimir')?.addEventListener('click', imprimirDoc);
document.getElementById('ftBtnVerHtml')?.addEventListener('click', verHtmlDoc);
document.getElementById('ftBtnCancelar')?.addEventListener('click', cancelarDoc);
addBtn?.addEventListener('click', newLine);

nomeInput?.addEventListener('input', () => {
  if (clientTimer) clearTimeout(clientTimer);
  clientTimer = setTimeout(() => searchClients(nomeInput.value || ''), 220);
});
nomeInput?.addEventListener('blur', () => setTimeout(hideClientSuggest, 260));
nomeInput?.addEventListener('focus', () => {
  try { nomeInput.setSelectionRange(0, 0); } catch (_) {}
  if ((nomeInput.value || '').trim().length >= 2) searchClients(nomeInput.value || '');
});
nomeInput?.addEventListener('click', () => {
  if ((nomeInput.value || '').trim() !== '') return;
  requestAnimationFrame(() => {
    try { nomeInput.setSelectionRange(0, 0); } catch (_) {}
  });
});
clientDetailBtn?.addEventListener('click', openClientDetail);
artigoSearchInput?.addEventListener('input', () => {
  if (artigoSearchTimer) clearTimeout(artigoSearchTimer);
  artigoSearchTimer = setTimeout(() => loadArtigoModalRows(artigoSearchInput.value || ''), 220);
});
artigoTable?.querySelectorAll('thead th[data-sort]')?.forEach(th => {
  th.addEventListener('click', () => setArtigoSort(th.dataset.sort));
});

showOverlay('A carregar...', false);
try {
  await loadFe();
  await loadCcustoOptions();
  await loadTaxaOptions();
  await loadDoc();
} finally {
  hideOverlay();
}
