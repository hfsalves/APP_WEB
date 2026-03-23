const context = window.FT_CONTEXT || {};
const ftStamp = String(context.stamp || '').trim();
const returnUrl = String(context.returnUrl || '/generic/view/FT/').trim() || '/generic/view/FT/';
const currentEntity = {
  FEID: Number(context.currentEntity?.FEID || 0) || 0,
  FESTAMP: String(context.currentEntity?.FESTAMP || '').trim(),
  NOME: String(context.currentEntity?.NOME || '').trim(),
  NOMEFISCAL: String(context.currentEntity?.NOMEFISCAL || '').trim(),
  NIF: String(context.currentEntity?.NIF || '').trim()
};

const overlay = document.getElementById('loadingOverlay');
const overlayText = overlay?.querySelector('.loading-text');
const titleEl = document.getElementById('ftTitulo');
const stateBadgeEl = document.getElementById('ftEstadoBadge');
const entityBadgeEl = document.getElementById('ftEntityBadge');
const linesBody = document.getElementById('ftLinesBody');
const ndocSel = document.getElementById('FT_NDOC');
const serieInput = document.getElementById('FT_SERIE');
const fnoInput = document.getElementById('FT_FNO');
const fdataInput = document.getElementById('FT_FDATA');
const pdataInput = document.getElementById('FT_PDATA');
const nomeInput = document.getElementById('FT_NOME');
const noInput = document.getElementById('FT_NO');
const nifInput = document.getElementById('FT_NCONT');
const ccustoSel = document.getElementById('FT_CCUSTO');
const descontoInput = document.getElementById('FT_DESCONTO');
const moedaInput = document.getElementById('FT_MOEDA');
const totalLiquidoInput = document.getElementById('FT_ETTILIQ');
const totalIvaInput = document.getElementById('FT_ETTIVA');
const totalInput = document.getElementById('FT_ETOTAL');
const clientSugg = document.getElementById('FT_CLIENT_SUGG');
const clientDetailBtn = document.getElementById('FT_CLIENT_DETAIL');
const addLineBtn = document.getElementById('ftAddLinha');
const linesPanel = document.querySelector('.sz_ft_lines_panel');
const btnCalc = document.getElementById('ftBtnCalc');
const btnGuardar = document.getElementById('ftBtnGuardar');
const btnEmitir = document.getElementById('ftBtnEmitir');
const btnCancelar = document.getElementById('ftBtnCancelar');
const btnAnular = document.getElementById('ftBtnAnular');
const btnDuplicar = document.getElementById('ftBtnDuplicar');
const btnImprimir = document.getElementById('ftBtnImprimir');
const btnVerHtml = document.getElementById('ftBtnVerHtml');
const hiddenMorada = document.getElementById('FT_MORADA');
const hiddenCodpost = document.getElementById('FT_CODPOST');
const hiddenLocal = document.getElementById('FT_LOCAL');
const hiddenPais = document.getElementById('FT_PAIS');

const clienteModalEl = document.getElementById('ftClienteModal');
const clienteModal = clienteModalEl && window.bootstrap?.Modal ? new window.bootstrap.Modal(clienteModalEl) : null;
const artigoModalEl = document.getElementById('ftArtigoModal');
const artigoModal = artigoModalEl && window.bootstrap?.Modal ? new window.bootstrap.Modal(artigoModalEl) : null;
const miseimpModalEl = document.getElementById('ftMiseimpModal');
const miseimpModal = miseimpModalEl && window.bootstrap?.Modal ? new window.bootstrap.Modal(miseimpModalEl) : null;
const calcModalEl = document.getElementById('ftCalcModal');
const calcModal = calcModalEl && window.bootstrap?.Modal ? new window.bootstrap.Modal(calcModalEl) : null;
const artigoSearchInput = document.getElementById('ftArtigoSearch');
const artigoTableBody = document.getElementById('ftArtigoTableBody');
const miseimpTableBody = document.getElementById('ftMiseimpTableBody');
const calcNoEl = document.getElementById('ftCalcNo');
const calcNomeEl = document.getElementById('ftCalcNome');
const calcNifEl = document.getElementById('ftCalcNif');
const calcMoradaEl = document.getElementById('ftCalcMorada');
const calcLinesBody = document.getElementById('ftCalcLinesBody');
const calcBreakdownBody = document.getElementById('ftCalcBreakdownBody');
const calcBaseEl = document.getElementById('ftCalcBase');
const calcVatEl = document.getElementById('ftCalcVat');
const calcTotalEl = document.getElementById('ftCalcTotal');

let header = {};
let lines = [];
let ccustoOptions = [];
let tabivaOptions = [];
let miseimpOptions = [];
let ftsRows = [];
let artigoRows = [];
let isBlocked = false;
let clientTimer = null;
let artigoTimer = null;
let artigoPickRowId = null;
let miseimpPickRowId = null;
let refAutocompleteMenu = null;
let refAutocompleteInput = null;
let refAutocompleteRowId = null;
let refAutocompleteHost = null;
let refAutocompleteItems = [];
let refAutocompleteTimer = null;
let refAutocompleteRequestId = 0;

const n = (value, fallback = 0) => {
  const normalized = Number(String(value ?? '').replace(',', '.'));
  return Number.isFinite(normalized) ? normalized : fallback;
};

const n2 = (value, fallback = 0) => Number(n(value, fallback).toFixed(2));
const pct2 = (value, fallback = 0) => Math.min(100, Math.max(0, n2(value, fallback)));
const SCALE_DECIMALS = 6;
const SCALE = 1000000n;
const HUNDRED_SCALED = 100n * SCALE;
const VAT_CENTS_DIVISOR = HUNDRED_SCALED * 10000n;

function roundDiv(numerator, denominator) {
  if (!denominator) return 0n;
  if (numerator >= 0n) return (numerator + (denominator / 2n)) / denominator;
  return -((-numerator + (denominator / 2n)) / denominator);
}

function parseScaled(value, decimals = SCALE_DECIMALS) {
  let text = String(value ?? '').trim().replace(',', '.');
  if (!text) return 0n;
  let negative = false;
  if (text.startsWith('-')) {
    negative = true;
    text = text.slice(1);
  }
  const [wholePartRaw, fracPartRaw = ''] = text.split('.');
  const wholePart = wholePartRaw.replace(/\D/g, '') || '0';
  const paddedFrac = `${fracPartRaw.replace(/\D/g, '')}${'0'.repeat(decimals + 1)}`;
  const fracMain = paddedFrac.slice(0, decimals);
  const roundDigit = paddedFrac.charAt(decimals);
  let result = BigInt(`${wholePart}${fracMain}`);
  if (roundDigit >= '5') result += 1n;
  return negative ? -result : result;
}

function clampPercentScaled(value) {
  const parsed = parseScaled(value);
  if (parsed < 0n) return 0n;
  if (parsed > HUNDRED_SCALED) return HUNDRED_SCALED;
  return parsed;
}

function scaledToFixed(value, decimals = SCALE_DECIMALS, decimalSeparator = '.') {
  const safeDecimals = Math.max(0, Number(decimals) || 0);
  const factor = 10n ** BigInt(SCALE_DECIMALS - safeDecimals);
  const rounded = roundDiv(BigInt(value || 0), factor);
  const negative = rounded < 0n;
  const absValue = negative ? -rounded : rounded;
  const raw = absValue.toString().padStart(safeDecimals + 1, '0');
  const head = safeDecimals ? raw.slice(0, -safeDecimals) : raw;
  const tail = safeDecimals ? raw.slice(-safeDecimals) : '';
  const grouped = head.replace(/\B(?=(\d{3})+(?!\d))/g, decimalSeparator === ',' ? '.' : ',');
  return `${negative ? '-' : ''}${grouped}${safeDecimals ? decimalSeparator + tail : ''}`;
}

function scaledToPlain(value, decimals = SCALE_DECIMALS) {
  const safeDecimals = Math.max(0, Number(decimals) || 0);
  const factor = 10n ** BigInt(SCALE_DECIMALS - safeDecimals);
  const rounded = roundDiv(BigInt(value || 0), factor);
  const negative = rounded < 0n;
  const absValue = negative ? -rounded : rounded;
  const raw = absValue.toString().padStart(safeDecimals + 1, '0');
  const head = safeDecimals ? raw.slice(0, -safeDecimals) : raw;
  const tail = safeDecimals ? raw.slice(-safeDecimals) : '';
  return `${negative ? '-' : ''}${head}${safeDecimals ? '.' + tail : ''}`;
}

function formatScaled(value, decimals = 2) {
  return scaledToFixed(value, decimals, ',');
}

function inputNumberValue(value, decimals = SCALE_DECIMALS) {
  const plain = scaledToPlain(parseScaled(value), decimals);
  return plain.replace(/(\.\d*?[1-9])0+$/u, '$1').replace(/\.0+$/u, '').replace(/\.$/u, '');
}

const fmt = (value, decimals = 2) => n(value, 0).toLocaleString('pt-PT', {
  minimumFractionDigits: decimals,
  maximumFractionDigits: decimals
});

const fmtInputDecimal = (value, decimals = 2) => n(value, 0).toLocaleString('pt-PT', {
  minimumFractionDigits: decimals,
  maximumFractionDigits: decimals,
  useGrouping: false
});

const stamp = () => (window.crypto?.randomUUID?.().replace(/-/g, '') || `${Date.now()}${Math.random()}`.replace(/\D/g, '')).slice(0, 25).toUpperCase();
const todayISO = () => new Date().toISOString().slice(0, 10);

const safeDate = (value) => {
  const raw = String(value || '').trim();
  if (!raw) return todayISO();
  const sample = raw.slice(0, 10);
  if (/^\d{4}-\d{2}-\d{2}$/.test(sample) && sample !== '1900-01-01' && sample !== '0001-01-01') return sample;
  const parsed = new Date(raw);
  if (!Number.isNaN(parsed.getTime())) return parsed.toISOString().slice(0, 10);
  return todayISO();
};

const esc = (value) => String(value ?? '')
  .replace(/&/g, '&amp;')
  .replace(/</g, '&lt;')
  .replace(/>/g, '&gt;')
  .replace(/"/g, '&quot;')
  .replace(/'/g, '&#39;');

const isZeroIva = (line) => Math.abs(n(line?.IVA, 0)) < 0.000001;
const lineCode = (line) => String(line?.MISEIMP || '').trim().toUpperCase();

function alertMessage(message) {
  if (typeof window.szAlert === 'function') {
    window.szAlert(String(message || ''), { title: 'Faturação' });
    return;
  }
  window.alert(message);
}

function showOverlay(message = 'A carregar...') {
  if (!overlay) return;
  if (overlayText) overlayText.textContent = message;
  overlay.style.display = 'flex';
  requestAnimationFrame(() => { overlay.style.opacity = '1'; });
}

function hideOverlay() {
  if (!overlay) return;
  overlay.style.opacity = '0';
  setTimeout(() => {
    overlay.style.display = 'none';
  }, 180);
}

function applySessionEntityToHeader() {
  header.FEID = currentEntity.FEID;
  header.FESTAMP = currentEntity.FESTAMP;
}

function entityLabel() {
  return currentEntity.NOMEFISCAL || currentEntity.NOME || 'Entidade ativa';
}

function setHiddenClientFields(source = {}) {
  if (hiddenMorada) hiddenMorada.value = String(source.MORADA || '').trim();
  if (hiddenCodpost) hiddenCodpost.value = String(source.CODPOST || '').trim();
  if (hiddenLocal) hiddenLocal.value = String(source.LOCAL || '').trim();
  if (hiddenPais) hiddenPais.value = String(source.PAIS || '').trim();
}

function normalizeLineOrder() {
  lines.sort((a, b) => n(a.LORDEM, 0) - n(b.LORDEM, 0));
  lines.forEach((line, index) => {
    line.LORDEM = (index + 1) * 10;
  });
}

function getMiseimpDescription(code) {
  const key = String(code || '').trim().toUpperCase();
  return miseimpOptions.find((row) => row.CODIGO === key)?.DESCRICAO || '';
}

function getTaxaByTabiva(tabiva) {
  const key = String(tabiva ?? '').trim();
  if (!key) return null;
  const hit = tabivaOptions.find((item) => String(item.tab) === key);
  return hit ? n(hit.taxa, 0) : null;
}

function displayValue(value) {
  const text = String(value ?? '').trim();
  return text || '—';
}

function computeLineAmounts(line, headerDiscountValue = header.DESCONTO) {
  const qttScaled = parseScaled(line?.QTT);
  const epvScaled = parseScaled(line?.EPV);
  const lineDiscountPctScaled = clampPercentScaled(line?.DESCONTO);
  const headerDiscountPctScaled = clampPercentScaled(headerDiscountValue);
  const ivaRateScaled = parseScaled(line?.IVA);
  const brutoScaled = roundDiv(qttScaled * epvScaled, SCALE);
  const descontoLinhaValorScaled = roundDiv(brutoScaled * lineDiscountPctScaled, HUNDRED_SCALED);
  const totalAposDescLinhaScaled = brutoScaled - descontoLinhaValorScaled;
  const descontoCabecalhoValorScaled = roundDiv(totalAposDescLinhaScaled * headerDiscountPctScaled, HUNDRED_SCALED);
  const totalLiquidoScaled = totalAposDescLinhaScaled - descontoCabecalhoValorScaled;
  const ivaLinhaCents = ivaRateScaled > 0n
    ? roundDiv(totalLiquidoScaled * ivaRateScaled, VAT_CENTS_DIVISOR)
    : 0n;
  const ivaLinhaScaled = ivaLinhaCents * 10000n;
  const totalComIvaScaled = totalLiquidoScaled + ivaLinhaScaled;
  const unitPriceFiscalScaled = qttScaled === 0n ? null : roundDiv(totalLiquidoScaled * SCALE, qttScaled);

  return {
    qttScaled,
    epvScaled,
    brutoScaled,
    descontoLinhaPctScaled: lineDiscountPctScaled,
    descontoLinhaValorScaled,
    totalAposDescLinhaScaled,
    descontoCabecalhoPctScaled: headerDiscountPctScaled,
    descontoCabecalhoValorScaled,
    totalLiquidoScaled,
    ivaRateScaled,
    ivaLinhaCents,
    ivaLinhaScaled,
    totalComIvaScaled,
    unitPriceFiscalScaled,
    tabiva: String(line?.TABIVA ?? '').trim()
  };
}

function getDefaultTabiva() {
  const exact = tabivaOptions.find((item) => String(item.tab) === '2');
  if (exact) return '2';
  const normalRate = tabivaOptions.find((item) => Math.abs(n(item.taxa, 0) - 23) < 0.000001);
  if (normalRate) return String(normalRate.tab || '').trim();
  return String(tabivaOptions[0]?.tab || '').trim();
}

function applyArtigoToLine(line, artigo) {
  if (!line || !artigo) return;
  line.REF = String(artigo.REF || line.REF || '').trim();
  line.DESIGN = String(artigo.DESIGN || line.DESIGN || '').trim();
  line.UNIDADE = String(artigo.UNIDADE || line.UNIDADE || '').trim();
  line.FAMILIA = String(artigo.FAMILIA || line.FAMILIA || '').trim();
  const artigoTabiva = String(artigo.TABIVA ?? '').trim();
  if (artigoTabiva !== '') {
    line.TABIVA = artigoTabiva;
  } else if (!String(line.TABIVA ?? '').trim()) {
    line.TABIVA = getDefaultTabiva();
  }
  const taxa = getTaxaByTabiva(line.TABIVA);
  if (taxa != null) line.IVA = taxa;
}

function recalcLine(line) {
  line.DESCONTO = pct2(line.DESCONTO, 0);
  if (!isZeroIva(line)) line.MISEIMP = '';
  const detail = computeLineAmounts(line);
  line.ETILIQUIDO = scaledToPlain(detail.totalLiquidoScaled, 6);
  line.UNITPRICE_FISCAL = detail.unitPriceFiscalScaled == null
    ? null
    : scaledToPlain(detail.unitPriceFiscalScaled, 6);
  line._calc = detail;
  return detail;
}

function normalizeLine(line = {}, index = 0) {
  const normalized = {
    FISTAMP: String(line.FISTAMP || stamp()).trim(),
    FTSTAMP: ftStamp,
    NDOC: n(line.NDOC, n(header.NDOC, 0)),
    NMDOC: String(line.NMDOC || header.NMDOC || '').trim(),
    FNO: n(line.FNO, n(header.FNO, 0)),
    REF: String(line.REF || '').trim(),
    DESIGN: String(line.DESIGN || '').trim(),
    QTT: n(line.QTT, 1),
    UNIDADE: String(line.UNIDADE || '').trim(),
    EPV: n(line.EPV, 0),
    DESCONTO: n(line.DESCONTO, 0),
    IVA: n(line.IVA, 0),
    IVAINCL: Number(n(line.IVAINCL, 0)) === 1 ? 1 : 0,
    TABIVA: String(line.TABIVA ?? '').trim(),
    ETILIQUIDO: String(line.ETILIQUIDO ?? '').trim(),
    UNITPRICE_FISCAL: line.UNITPRICE_FISCAL == null ? null : String(line.UNITPRICE_FISCAL).trim(),
    FAMILIA: String(line.FAMILIA || '').trim(),
    FICCUSTO: String(line.FICCUSTO || header.CCUSTO || '').trim(),
    MISEIMP: lineCode(line),
    LORDEM: n(line.LORDEM, (index + 1) * 10)
  };
  recalcLine(normalized);
  return normalized;
}

function recalcAll() {
  header.DESCONTO = pct2(header.DESCONTO, 0);
  if (descontoInput && document.activeElement !== descontoInput) {
    descontoInput.value = fmtInputDecimal(header.DESCONTO, 2);
  }
  let totalBaseScaled = 0n;
  let totalVatCents = 0n;

  lines.forEach((line) => {
    const detail = recalcLine(line);
    totalBaseScaled += detail.totalLiquidoScaled;
    totalVatCents += detail.ivaLinhaCents;
  });

  const totalVatScaled = totalVatCents * 10000n;
  const totalDocScaled = totalBaseScaled + totalVatScaled;
  header.ETTILIQ = scaledToPlain(totalBaseScaled, 6);
  header.ETTIVA = scaledToPlain(totalVatScaled, 2);
  header.ETOTAL = scaledToPlain(totalDocScaled, 2);
  if (totalLiquidoInput) totalLiquidoInput.value = formatScaled(totalBaseScaled, 2);
  if (totalIvaInput) totalIvaInput.value = formatScaled(totalVatScaled, 2);
  if (totalInput) totalInput.value = formatScaled(totalDocScaled, 2);
}

function isMeaningfulLine(line) {
  return Boolean(
    String(line.REF || '').trim() ||
    String(line.DESIGN || '').trim() ||
    Math.abs(n(line.EPV, 0)) > 0.000001 ||
    Math.abs(n(line.ETILIQUIDO, 0)) > 0.000001 ||
    (Math.abs(n(line.QTT, 0)) > 0.000001 && (Math.abs(n(line.EPV, 0)) > 0.000001 || Math.abs(n(line.ETILIQUIDO, 0)) > 0.000001))
  );
}

function validateMiseimpLines() {
  const validCodes = new Set(miseimpOptions.map((item) => item.CODIGO));
  const missing = [];
  const invalid = [];
  lines.forEach((line, index) => {
    if (!isMeaningfulLine(line) || !isZeroIva(line)) return;
    const code = lineCode(line);
    if (!code) {
      missing.push(index + 1);
      return;
    }
    if (validCodes.size && !validCodes.has(code)) {
      invalid.push(`${index + 1} (${code})`);
    }
  });
  const messages = [];
  if (missing.length) messages.push(`Linhas com IVA 0% sem motivo de isenção: ${missing.join(', ')}`);
  if (invalid.length) messages.push(`Linhas com motivo de isenção inválido: ${invalid.join(', ')}`);
  return messages.join(' | ');
}

function renderNdocOptions() {
  if (!ndocSel) return;
  const map = new Map();
  ftsRows.forEach((row) => {
    const ndoc = String(n(row.NDOC, 0));
    if (!map.has(ndoc)) map.set(ndoc, String(row.NMDOC || '').trim());
  });
  ndocSel.innerHTML = '<option value="">---</option>' + Array.from(map.entries()).map(([ndoc, nmdoc]) => (
    `<option value="${esc(ndoc)}">${esc(nmdoc || ndoc)}</option>`
  )).join('');
}

function syncSeriesFromHeader() {
  if (!ndocSel) return;
  const currentNdoc = String(n(header.NDOC, 0));
  const matchingRows = ftsRows.filter((row) => String(n(row.NDOC, 0)) === currentNdoc);
  if (!matchingRows.length) {
    header.SERIE = '';
    header.NMDOC = '';
    ndocSel.value = '';
    if (serieInput) serieInput.value = '';
    return;
  }
  const currentSerie = String(header.SERIE || '').trim();
  const selectedSerieRow = matchingRows.find((row) => String(row.SERIE || '').trim() === currentSerie) || matchingRows[0];
  header.SERIE = String(selectedSerieRow.SERIE || '').trim();
  header.NDOC = n(selectedSerieRow.NDOC, 0);
  header.NMDOC = String(selectedSerieRow.NMDOC || '').trim();
  ndocSel.value = String(header.NDOC || '');
  if (serieInput) serieInput.value = header.SERIE || '';
}

async function loadFts() {
  if (!currentEntity.FESTAMP) {
    ftsRows = [];
    renderNdocOptions();
    syncSeriesFromHeader();
    return;
  }
  const ano = n(String(header.FDATA || '').slice(0, 4), new Date().getFullYear());
  const response = await fetch(`/api/lookups/fts?festamp=${encodeURIComponent(currentEntity.FESTAMP)}&ano=${encodeURIComponent(ano)}`);
  ftsRows = await response.json().catch(() => []);
  if (!Array.isArray(ftsRows)) ftsRows = [];
  if (!ftsRows.length) {
    header.NDOC = 0;
    header.NMDOC = '';
    header.SERIE = '';
  } else if (!ftsRows.some((row) => n(row.NDOC, 0) === n(header.NDOC, 0))) {
    header.NDOC = n(ftsRows[0].NDOC, 0);
    header.NMDOC = String(ftsRows[0].NMDOC || '').trim();
    header.SERIE = String(ftsRows[0].SERIE || '').trim();
  }
  renderNdocOptions();
  syncSeriesFromHeader();
}

async function loadCcustoOptions() {
  const response = await fetch('/generic/api/options?query=' + encodeURIComponent('SELECT CCUSTO FROM V_CCT'));
  const data = await response.json().catch(() => []);
  ccustoOptions = (Array.isArray(data) ? data : [])
    .map((row) => (typeof row === 'object' ? Object.values(row)[0] : row))
    .map((value) => String(value || '').trim())
    .filter(Boolean);
  if (!ccustoSel) return;
  ccustoSel.innerHTML = '<option value="">---</option>' + ccustoOptions.map((value) => (
    `<option value="${esc(value)}">${esc(value)}</option>`
  )).join('');
}

async function loadTaxaOptions() {
  const response = await fetch('/generic/api/fo/taxas');
  const data = await response.json().catch(() => []);
  tabivaOptions = (Array.isArray(data) ? data : [])
    .map((row) => ({
      tab: String(row?.TABIVA ?? '').trim(),
      taxa: n(row?.TAXAIVA, 0)
    }))
    .filter((row) => row.tab !== '');
}

async function loadMiseimpOptions() {
  const response = await fetch('/api/faturacao/miseimp');
  const data = await response.json().catch(() => []);
  miseimpOptions = (Array.isArray(data) ? data : [])
    .map((row) => ({
      CODIGO: String(row?.CODIGO || '').trim().toUpperCase(),
      DESCRICAO: String(row?.DESCRICAO || '').trim()
    }))
    .filter((row) => row.CODIGO !== '')
    .sort((a, b) => a.CODIGO.localeCompare(b.CODIGO, 'pt'));
}

async function fetchArtigoByRef(ref) {
  const query = String(ref || '').trim();
  if (query.length < 2) return null;
  const response = await fetch(`/generic/api/fo/search_artigos?q=${encodeURIComponent(query)}`);
  const data = await response.json().catch(() => []);
  if (!response.ok || !Array.isArray(data)) return null;
  return data.find((row) => String(row.REF || '').trim().toLowerCase() === query.toLowerCase()) || null;
}

function ensureRefAutocompleteMenu() {
  if (refAutocompleteMenu) return refAutocompleteMenu;
  refAutocompleteMenu = document.createElement('div');
  refAutocompleteMenu.className = 'sz_ref_autocomplete_menu';
  refAutocompleteMenu.style.position = 'absolute';
  refAutocompleteMenu.style.zIndex = '3000';
  refAutocompleteMenu.style.display = 'none';
  refAutocompleteMenu.style.margin = '0';
  refAutocompleteMenu.style.transform = 'none';
  refAutocompleteMenu.style.inset = 'auto';
  refAutocompleteMenu.style.right = 'auto';
  refAutocompleteMenu.style.bottom = 'auto';
  (linesPanel || document.body).appendChild(refAutocompleteMenu);

  refAutocompleteMenu.addEventListener('mousedown', (event) => {
    const itemEl = event.target.closest('[data-ref-index]');
    if (!itemEl) return;
    event.preventDefault();
    const artigo = refAutocompleteItems[n(itemEl.dataset.refIndex, -1)];
    const line = lines.find((entry) => entry.FISTAMP === refAutocompleteRowId);
    if (!artigo || !line) {
      closeRefAutocomplete();
      return;
    }
    if (refAutocompleteInput) {
      refAutocompleteInput.value = String(artigo.REF || '').trim();
    }
    applyArtigoToLine(line, artigo);
    recalcAll();
    closeRefAutocomplete();
    renderLines();
  });

  document.addEventListener('mousedown', (event) => {
    if (!refAutocompleteMenu?.classList.contains('show')) return;
    if (refAutocompleteMenu.contains(event.target) || refAutocompleteInput?.contains(event.target)) return;
    closeRefAutocomplete();
  });

  window.addEventListener('resize', () => {
    if (refAutocompleteMenu?.classList.contains('show')) positionRefAutocomplete();
  });
  window.addEventListener('scroll', () => {
    if (refAutocompleteMenu?.classList.contains('show')) positionRefAutocomplete();
  }, true);
  return refAutocompleteMenu;
}

function closeRefAutocomplete() {
  if (!refAutocompleteMenu) return;
  clearTimeout(refAutocompleteTimer);
  refAutocompleteRequestId += 1;
  refAutocompleteMenu.classList.remove('show');
  refAutocompleteMenu.style.display = 'none';
  refAutocompleteItems = [];
  refAutocompleteInput = null;
  refAutocompleteRowId = null;
  refAutocompleteHost = null;
}

function positionRefAutocomplete() {
  if (!refAutocompleteMenu || !refAutocompleteInput) return;
  const inputRect = refAutocompleteInput.getBoundingClientRect();
  const rootRect = (linesPanel || document.body).getBoundingClientRect();
  const rootWidth = (linesPanel || document.body).clientWidth || window.innerWidth || document.documentElement.clientWidth || 0;
  const width = Math.max(Math.round(inputRect.width), 240);
  const left = Math.max(8, Math.min(Math.round(inputRect.left - rootRect.left), rootWidth - width - 8));
  refAutocompleteMenu.style.setProperty('width', `${width}px`, 'important');
  refAutocompleteMenu.style.setProperty('left', `${left}px`, 'important');
  refAutocompleteMenu.style.setProperty('top', `${Math.round(inputRect.bottom - rootRect.top + 4)}px`, 'important');
  refAutocompleteMenu.style.setProperty('right', 'auto', 'important');
  refAutocompleteMenu.style.setProperty('bottom', 'auto', 'important');
}

function renderRefAutocomplete(items) {
  const menu = ensureRefAutocompleteMenu();
  if (!Array.isArray(items) || !items.length) {
    closeRefAutocomplete();
    return;
  }
  refAutocompleteHost = refAutocompleteInput?.closest('.sz_ft_ref_cell') || null;
  refAutocompleteItems = items;
  menu.innerHTML = items.map((item, index) => `
    <button type="button" class="sz_ref_autocomplete_item" data-ref-index="${index}">
      <strong>${esc(item.REF || '')}</strong>
      <small>${esc(item.DESIGN || item.FAMILIA || '')}</small>
    </button>
  `).join('');
  menu.classList.add('show');
  menu.style.display = 'block';
  positionRefAutocomplete();
}

async function searchRefAutocomplete(input) {
  const term = String(input?.value || '').trim();
  if (term.length < 2 || isBlocked) {
    closeRefAutocomplete();
    return;
  }
  const requestId = ++refAutocompleteRequestId;
  try {
    const response = await fetch(`/generic/api/fo/search_artigos?q=${encodeURIComponent(term)}`);
    const data = await response.json().catch(() => []);
    if (requestId !== refAutocompleteRequestId || input !== refAutocompleteInput) return;
    if (!response.ok || !Array.isArray(data)) {
      closeRefAutocomplete();
      return;
    }
    renderRefAutocomplete(data);
  } catch {
    if (requestId === refAutocompleteRequestId) closeRefAutocomplete();
  }
}

function bindRefAutocomplete(input) {
  if (!input || input.dataset.refAutocompleteBound === '1') return;
  ensureRefAutocompleteMenu();
  input.dataset.refAutocompleteBound = '1';

  input.addEventListener('focus', () => {
    refAutocompleteInput = input;
    refAutocompleteRowId = input.closest('tr[data-id]')?.dataset.id || null;
    if (String(input.value || '').trim().length >= 2) {
      clearTimeout(refAutocompleteTimer);
      refAutocompleteTimer = setTimeout(() => searchRefAutocomplete(input), 120);
    }
  });

  input.addEventListener('input', () => {
    refAutocompleteInput = input;
    refAutocompleteRowId = input.closest('tr[data-id]')?.dataset.id || null;
    clearTimeout(refAutocompleteTimer);
    refAutocompleteTimer = setTimeout(() => searchRefAutocomplete(input), 180);
  });

  input.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') closeRefAutocomplete();
  });
}

function renderClientSuggestions(rows) {
  if (!clientSugg) return;
  if (!Array.isArray(rows) || !rows.length) {
    clientSugg.style.display = 'none';
    clientSugg.innerHTML = '';
    return;
  }
  clientSugg.innerHTML = rows.map((row, index) => `
    <button type="button" class="sz_ft_suggestion_item" data-client-index="${index}">
      <div><strong>${esc(row.NOME || '')}</strong></div>
      <div class="sz_text_muted">NO ${n(row.NO, 0)} · NIF ${esc(row.NIF || '')} · ${esc(row.LOCAL || '')}</div>
    </button>
  `).join('');
  clientSugg.style.display = 'block';
  clientSugg.querySelectorAll('[data-client-index]').forEach((button) => {
    button.addEventListener('mousedown', (event) => {
      event.preventDefault();
      const row = rows[n(button.dataset.clientIndex, -1)];
      if (row) applyClient(row);
    });
  });
}

async function searchClients(term) {
  const query = String(term || '').trim();
  if (query.length < 2 || isBlocked) {
    renderClientSuggestions([]);
    return;
  }
  const response = await fetch(`/api/faturacao/clientes?q=${encodeURIComponent(query)}`);
  const rows = await response.json().catch(() => []);
  if (!response.ok || !Array.isArray(rows)) {
    renderClientSuggestions([]);
    return;
  }
  renderClientSuggestions(rows);
}

function applyClient(client) {
  header.NO = n(client.NO, 0);
  header.NOME = String(client.NOME || '').trim();
  header.NCONT = String(client.NIF || '').trim();
  header.MORADA = String(client.MORADA || '').trim();
  header.CODPOST = String(client.CODPOST || '').trim();
  header.LOCAL = String(client.LOCAL || '').trim();
  header.PAIS = String(client.PAIS || '').trim();
  if (noInput) noInput.value = header.NO || '';
  if (nomeInput) nomeInput.value = header.NOME || '';
  if (nifInput) nifInput.value = header.NCONT || '';
  setHiddenClientFields(header);
  renderClientSuggestions([]);
}

async function openClientDetail() {
  const no = n(noInput?.value, 0);
  if (!no) {
    alertMessage('Selecione primeiro um cliente.');
    return;
  }
  const response = await fetch(`/api/faturacao/clientes/${encodeURIComponent(no)}`);
  const data = await response.json().catch(() => ({}));
  if (!response.ok || data.error) {
    alertMessage(data.error || 'Erro ao ler detalhes do cliente.');
    return;
  }
  const setValue = (id, value) => {
    const element = document.getElementById(id);
    if (element) element.value = value ?? '';
  };
  setValue('FTM_NO', n(data.NO, 0) || '');
  setValue('FTM_NOME', data.NOME || '');
  setValue('FTM_NIF', data.NIF || '');
  setValue('FTM_MORADA', data.MORADA || '');
  setValue('FTM_CODPOST', data.CODPOST || '');
  setValue('FTM_LOCAL', data.LOCAL || '');
  setValue('FTM_PAIS', data.PAIS || '');
  clienteModal?.show();
}

function updateStatusUi() {
  const anulada = Number(header.ANULADA || 0) === 1;
  const emitida = Number(header.ESTADO || 0) === 1;
  const label = anulada ? 'Anulada' : (emitida ? `Emitida #${n(header.FNO, 0)}` : 'Rascunho');
  const badgeClass = anulada ? 'sz_badge_danger' : (emitida ? 'sz_badge_success' : 'sz_badge_warning');
  if (titleEl) titleEl.textContent = label;
  if (stateBadgeEl) {
    stateBadgeEl.textContent = label;
    stateBadgeEl.classList.remove('sz_badge_info', 'sz_badge_success', 'sz_badge_warning', 'sz_badge_danger');
    stateBadgeEl.classList.add('sz_badge', badgeClass);
  }
  if (entityBadgeEl) entityBadgeEl.textContent = entityLabel();
}

function mapHeaderToUi() {
  applySessionEntityToHeader();
  if (fnoInput) fnoInput.value = n(header.FNO, 0) || 0;
  if (fdataInput) fdataInput.value = safeDate(header.FDATA);
  if (pdataInput) pdataInput.value = safeDate(header.PDATA || header.FDATA);
  if (moedaInput) moedaInput.value = String(header.MOEDA || 'EUR').trim() || 'EUR';
  if (descontoInput) descontoInput.value = fmtInputDecimal(pct2(header.DESCONTO, 0), 2);
  if (noInput) noInput.value = n(header.NO, 0) || '';
  if (nomeInput) nomeInput.value = header.NOME || '';
  if (nifInput) nifInput.value = header.NCONT || '';
  if (ccustoSel) ccustoSel.value = String(header.CCUSTO || '').trim();
  setHiddenClientFields(header);
  syncSeriesFromHeader();
  recalcAll();
  updateStatusUi();
  window.szEnhanceDecimalInputs?.(document.getElementById('ftFormRoot'));
}

function mapUiToHeader() {
  applySessionEntityToHeader();
  header.NDOC = n(ndocSel?.value, 0);
  header.SERIE = String(serieInput?.value || '').trim();
  const selectedSerie = ftsRows.find((row) => String(n(row.NDOC, 0)) === String(header.NDOC) && String(row.SERIE || '').trim() === header.SERIE);
  header.NMDOC = String(selectedSerie?.NMDOC || header.NMDOC || '').trim();
  header.FDATA = fdataInput?.value || todayISO();
  header.FTANO = n(String(header.FDATA).slice(0, 4), new Date().getFullYear());
  header.PDATA = pdataInput?.value || header.FDATA;
  header.MOEDA = String(moedaInput?.value || 'EUR').trim() || 'EUR';
  header.DESCONTO = pct2(descontoInput?.value, 0);
  header.NO = n(noInput?.value, 0);
  header.NOME = String(nomeInput?.value || '').trim();
  header.NCONT = String(nifInput?.value || '').trim();
  header.CCUSTO = String(ccustoSel?.value || '').trim();
  header.MORADA = String(hiddenMorada?.value || '').trim();
  header.CODPOST = String(hiddenCodpost?.value || '').trim();
  header.LOCAL = String(hiddenLocal?.value || '').trim();
  header.PAIS = String(hiddenPais?.value || '').trim();
}

function buildTabivaOptions(currentValue) {
  const current = String(currentValue ?? '').trim();
  const options = tabivaOptions.map((item) => {
    const selected = String(item.tab) === current ? 'selected' : '';
    return `<option value="${esc(item.tab)}" ${selected}>${esc(item.tab)} - ${fmt(item.taxa)}</option>`;
  });
  if (current && !tabivaOptions.some((item) => String(item.tab) === current)) {
    options.unshift(`<option value="${esc(current)}" selected>${esc(current)}</option>`);
  }
  return `<option value="">---</option>${options.join('')}`;
}

function renderLines() {
  if (!linesBody) return;
  closeRefAutocomplete();
  if (!lines.length) {
    linesBody.innerHTML = '<tr><td colspan="13" class="sz_text_muted">Sem linhas.</td></tr>';
    return;
  }
  normalizeLineOrder();
  const disabled = isBlocked ? 'disabled' : '';
  linesBody.innerHTML = lines.map((line) => {
    const needsMiseimp = isZeroIva(line);
    const code = lineCode(line);
    const desc = getMiseimpDescription(code);
    const badgeHtml = !needsMiseimp
      ? '<span class="sz_text_muted">—</span>'
      : `<button type="button" ${disabled} class="sz_badge ${code ? 'sz_badge_info' : 'sz_badge_warning'} sz_ft_miseimp_badge" data-a="miseimp" title="${esc(code ? `${code}${desc ? ' - ' + desc : ''}` : 'Motivo de isenção obrigatório')}">${esc(code || 'Falta preencher')}</button>`;
    return `
      <tr data-id="${esc(line.FISTAMP)}">
        <td>
          <div class="sz_ft_ref_cell">
            <button type="button" ${disabled} class="sz_button sz_button_ghost sz_ft_icon_button" data-a="choose_ref" title="Escolher referência">
              <i class="fa-solid fa-search"></i>
            </button>
            <input ${disabled} class="sz_input sz_ft_table_input" data-f="REF" value="${esc(line.REF)}">
          </div>
        </td>
        <td><input ${disabled} class="sz_input sz_ft_table_input" data-f="DESIGN" value="${esc(line.DESIGN)}"></td>
        <td><input ${disabled} class="sz_input sz_ft_table_input sz_text_right" type="number" step="0.01" data-sz-decimal="true" data-f="QTT" value="${inputNumberValue(line.QTT, 2)}"></td>
        <td><input ${disabled} class="sz_input sz_ft_table_input" data-f="UNIDADE" value="${esc(line.UNIDADE)}"></td>
        <td><input ${disabled} class="sz_input sz_ft_table_input sz_text_right" type="number" step="0.01" data-sz-decimal="true" data-f="EPV" value="${inputNumberValue(line.EPV, 2)}"></td>
        <td><input ${disabled} class="sz_input sz_ft_table_input sz_text_right" type="number" step="0.01" min="0" data-sz-decimal="true" data-f="DESCONTO" value="${inputNumberValue(line.DESCONTO, 2)}"></td>
        <td><input class="sz_input sz_ft_table_input sz_text_right" readonly data-f="ETILIQUIDO" value="${fmt(line.ETILIQUIDO, 2)}"></td>
        <td><select ${disabled} class="sz_select sz_ft_table_select" data-f="TABIVA">${buildTabivaOptions(line.TABIVA)}</select></td>
        <td>${badgeHtml}</td>
        <td class="sz_text_center"><input ${disabled} class="sz_ft_table_checkbox" type="checkbox" data-f="IVAINCL" ${Number(line.IVAINCL || 0) === 1 ? 'checked' : ''}></td>
        <td><input ${disabled} class="sz_input sz_ft_table_input" data-f="FAMILIA" value="${esc(line.FAMILIA)}"></td>
        <td><input ${disabled} class="sz_input sz_ft_table_input" data-f="FICCUSTO" value="${esc(line.FICCUSTO || header.CCUSTO || '')}"></td>
        <td>
          <button type="button" ${disabled} class="sz_button sz_button_danger sz_ft_icon_button" data-a="del" title="Eliminar linha">
            <i class="fa-solid fa-trash"></i>
          </button>
        </td>
      </tr>
    `;
  }).join('');
  window.szEnhanceDecimalInputs?.(linesBody);
  linesBody.querySelectorAll('input[data-f="REF"]').forEach(bindRefAutocomplete);
}

function renderArtigoRows() {
  if (!artigoTableBody) return;
  if (!artigoRows.length) {
    artigoTableBody.innerHTML = '<tr><td colspan="3" class="sz_text_muted">Sem artigos.</td></tr>';
    return;
  }
  artigoTableBody.innerHTML = artigoRows.map((row, index) => `
    <tr data-artigo-index="${index}">
      <td>${esc(row.REF || '')}</td>
      <td>${esc(row.DESIGN || '')}</td>
      <td>${esc(row.FAMILIA_NOME || row.FAMILIA || '')}</td>
    </tr>
  `).join('');
}

async function loadArtigoRows(term = '') {
  if (!artigoTableBody) return;
  artigoTableBody.innerHTML = '<tr><td colspan="3" class="sz_text_muted">A carregar...</td></tr>';
  const response = await fetch(`/generic/api/fo/artigos?q=${encodeURIComponent(String(term || '').trim())}&limit=200`);
  const data = await response.json().catch(() => []);
  artigoRows = response.ok && Array.isArray(data) ? data : [];
  renderArtigoRows();
}

function renderMiseimpRows() {
  if (!miseimpTableBody) return;
  if (!miseimpOptions.length) {
    miseimpTableBody.innerHTML = '<tr><td colspan="2" class="sz_text_muted">Sem motivos de isenção disponíveis.</td></tr>';
    return;
  }
  const currentLine = lines.find((line) => line.FISTAMP === miseimpPickRowId);
  const currentCode = lineCode(currentLine);
  miseimpTableBody.innerHTML = miseimpOptions.map((row) => `
    <tr data-codigo="${esc(row.CODIGO)}" ${row.CODIGO === currentCode ? 'class="table-active"' : ''}>
      <td><strong>${esc(row.CODIGO)}</strong></td>
      <td>${esc(row.DESCRICAO)}</td>
    </tr>
  `).join('');
}

function computeCalcSnapshot() {
  mapUiToHeader();
  recalcAll();
  const detailLines = [];
  const breakdown = new Map();
  let totalBaseScaled = 0n;
  let totalVatCents = 0n;

  lines.filter(isMeaningfulLine).forEach((line) => {
    const detail = line._calc || computeLineAmounts(line);
    totalBaseScaled += detail.totalLiquidoScaled;
    totalVatCents += detail.ivaLinhaCents;

    const rateLabel = formatScaled(detail.ivaRateScaled, 2);
    const key = `${detail.tabiva}|${rateLabel}`;
    const existing = breakdown.get(key) || {
      label: detail.tabiva ? `T${detail.tabiva} · ${rateLabel}%` : `${rateLabel}%`,
      rateLabel,
      baseScaled: 0n,
      ivaCents: 0n
    };
    existing.baseScaled += detail.totalLiquidoScaled;
    existing.ivaCents += detail.ivaLinhaCents;
    breakdown.set(key, existing);

    detailLines.push({
      REF: String(line.REF || '').trim(),
      DESIGN: String(line.DESIGN || '').trim(),
      QTT: formatScaled(detail.qttScaled, 2),
      EPV: formatScaled(detail.epvScaled, 2),
      DESCONTO_LINHA: formatScaled(detail.descontoLinhaPctScaled, 2),
      TOTAL_LINHA: formatScaled(detail.totalAposDescLinhaScaled, 6),
      DESCONTO_CAB: formatScaled(detail.descontoCabecalhoPctScaled, 2),
      TOTAL_APOS_CAB: formatScaled(detail.totalLiquidoScaled, 6),
      TAXA_IVA: formatScaled(detail.ivaRateScaled, 2),
      IVA_LINHA: formatScaled(detail.ivaLinhaScaled, 2)
    });
  });

  return {
    no: displayValue(header.NO),
    nome: displayValue(header.NOME),
    nif: displayValue(header.NCONT),
    morada: displayValue([header.MORADA, header.CODPOST, header.LOCAL].filter(Boolean).join(', ')),
    lines: detailLines,
    breakdown: Array.from(breakdown.values()),
    totalBase: formatScaled(totalBaseScaled, 2),
    totalVat: formatScaled(totalVatCents * 10000n, 2),
    totalDoc: formatScaled(totalBaseScaled + (totalVatCents * 10000n), 2)
  };
}

function renderCalcModal() {
  const snapshot = computeCalcSnapshot();
  if (calcNoEl) calcNoEl.textContent = snapshot.no;
  if (calcNomeEl) calcNomeEl.textContent = snapshot.nome;
  if (calcNifEl) calcNifEl.textContent = snapshot.nif;
  if (calcMoradaEl) calcMoradaEl.textContent = snapshot.morada;

  if (calcLinesBody) {
    if (!snapshot.lines.length) {
      calcLinesBody.innerHTML = '<tr><td colspan="10" class="sz_text_muted">Sem linhas.</td></tr>';
    } else {
      calcLinesBody.innerHTML = snapshot.lines.map((row) => `
        <tr>
          <td>${esc(row.REF || '—')}</td>
          <td>${esc(row.DESIGN || '—')}</td>
          <td class="sz_text_right">${row.QTT}</td>
          <td class="sz_text_right">${row.EPV}</td>
          <td class="sz_text_right">${row.DESCONTO_LINHA}</td>
          <td class="sz_text_right">${row.TOTAL_LINHA}</td>
          <td class="sz_text_right">${row.DESCONTO_CAB}</td>
          <td class="sz_text_right">${row.TOTAL_APOS_CAB}</td>
          <td class="sz_text_right">${row.TAXA_IVA}</td>
          <td class="sz_text_right">${row.IVA_LINHA}</td>
        </tr>
      `).join('');
    }
  }

  if (calcBreakdownBody) {
    if (!snapshot.breakdown.length) {
      calcBreakdownBody.innerHTML = '<tr><td colspan="3" class="sz_text_muted">Sem impostos.</td></tr>';
    } else {
      calcBreakdownBody.innerHTML = snapshot.breakdown.map((row) => `
        <tr>
          <td>${esc(row.label)}</td>
          <td class="sz_text_right">${formatScaled(row.baseScaled, 2)}</td>
          <td class="sz_text_right">${formatScaled(row.ivaCents * 10000n, 2)}</td>
        </tr>
      `).join('');
    }
  }

  if (calcBaseEl) calcBaseEl.textContent = snapshot.totalBase;
  if (calcVatEl) calcVatEl.textContent = snapshot.totalVat;
  if (calcTotalEl) calcTotalEl.textContent = snapshot.totalDoc;
}

function openCalcModal() {
  renderCalcModal();
  calcModal?.show();
}

function openMiseimpModal(rowId) {
  miseimpPickRowId = rowId;
  renderMiseimpRows();
  miseimpModal?.show();
}

function updateEditableState() {
  const emitida = Number(header.ESTADO || 0) === 1;
  const anulada = Number(header.ANULADA || 0) === 1;
  isBlocked = Number(header.BLOQUEADO || 0) === 1;

  [ndocSel, fdataInput, pdataInput, nomeInput, ccustoSel, descontoInput, clientDetailBtn, addLineBtn].forEach((element) => {
    if (element) element.disabled = isBlocked;
  });

  if (btnGuardar) btnGuardar.disabled = isBlocked;
  if (btnEmitir) btnEmitir.disabled = isBlocked;
  if (btnAnular) btnAnular.disabled = anulada || !emitida;
}

async function loadDoc() {
  const response = await fetch(`/api/faturacao/ft/${encodeURIComponent(ftStamp)}`);
  const data = await response.json().catch(() => ({}));
  if (!response.ok || data.error) {
    alertMessage(data.error || 'Erro ao carregar documento.');
    window.location.href = returnUrl;
    return;
  }
  header = Object.assign({}, data.header || {});
  applySessionEntityToHeader();
  header.MOEDA = String(header.MOEDA || 'EUR').trim() || 'EUR';
  header.FDATA = safeDate(header.FDATA);
  header.PDATA = safeDate(header.PDATA || header.FDATA);
  lines = Array.isArray(data.lines) ? data.lines.map((line, index) => normalizeLine(line, index)) : [];
  await loadFts();
  mapHeaderToUi();
  renderLines();
  updateEditableState();
}

async function saveDoc(redirectAfter = true, reloadAfter = true) {
  if (isBlocked) return false;
  mapUiToHeader();
  recalcAll();
  const miseimpError = validateMiseimpLines();
  if (miseimpError) {
    alertMessage(miseimpError);
    return false;
  }
  const response = await fetch(`/api/faturacao/ft/${encodeURIComponent(ftStamp)}/save`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ header, lines })
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok || data.error) {
    alertMessage(data.error || 'Erro ao guardar.');
    return false;
  }
  if (redirectAfter) {
    window.location.href = returnUrl;
    return true;
  }
  if (reloadAfter) await loadDoc();
  return true;
}

async function emitirDoc() {
  if (isBlocked) return;
  showOverlay('A emitir documento...');
  try {
    const saved = await saveDoc(false, false);
    if (!saved) return;
    const response = await fetch(`/api/faturacao/ft/${encodeURIComponent(ftStamp)}/emitir`, { method: 'POST' });
    const data = await response.json().catch(() => ({}));
    if (!response.ok || data.error) {
      alertMessage(data.error || 'Erro ao emitir.');
      return;
    }
    await loadDoc();
  } finally {
    hideOverlay();
  }
}

async function anularDoc() {
  const motivo = window.prompt('Motivo de anulação:');
  if (motivo === null) return;
  const response = await fetch(`/api/faturacao/ft/${encodeURIComponent(ftStamp)}/anular`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ motivo })
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok || data.error) {
    alertMessage(data.error || 'Erro ao anular.');
    return;
  }
  await loadDoc();
}

async function duplicarDoc() {
  const response = await fetch(`/api/faturacao/ft/${encodeURIComponent(ftStamp)}/duplicar`, { method: 'POST' });
  const data = await response.json().catch(() => ({}));
  if (!response.ok || data.error) {
    alertMessage(data.error || 'Erro ao duplicar.');
    return;
  }
  if (data.FTSTAMP) window.location.href = `/faturacao/ft/${encodeURIComponent(data.FTSTAMP)}`;
}

function openNewTab(url) {
  const popup = window.open(url, '_blank');
  if (popup) {
    popup.opener = null;
    return;
  }
  window.location.href = url;
}

function imprimirDoc() {
  openNewTab(`/api/faturacao/ft/${encodeURIComponent(ftStamp)}/pdf?force_html=1&_ts=${Date.now()}`);
}

function verHtmlDoc() {
  openNewTab(`/api/faturacao/ft/${encodeURIComponent(ftStamp)}/pdf/html?_ts=${Date.now()}`);
}

async function cancelarDoc() {
  if (Number(header.ESTADO || 0) === 0) {
    if (typeof window.szConfirmDelete === 'function') {
      const confirmed = await window.szConfirmDelete('Cancelar este rascunho? O documento será eliminado.', { title: 'Cancelar rascunho' });
      if (!confirmed) return;
    } else if (!window.confirm('Cancelar este rascunho? O documento será eliminado.')) {
      return;
    }
    const response = await fetch(`/api/faturacao/ft/${encodeURIComponent(ftStamp)}/cancelar`, { method: 'POST' });
    const data = await response.json().catch(() => ({}));
    if (!response.ok || data.error) {
      alertMessage(data.error || 'Erro ao cancelar rascunho.');
      return;
    }
  }
  window.location.href = returnUrl;
}

function newLine() {
  lines.push(normalizeLine({
    FISTAMP: stamp(),
    FTSTAMP: ftStamp,
    NDOC: header.NDOC,
    NMDOC: header.NMDOC,
    FNO: header.FNO,
    QTT: 1,
    DESCONTO: 0,
    IVA: 0,
    IVAINCL: 0,
    TABIVA: '',
    FICCUSTO: header.CCUSTO || ''
  }, lines.length));
  renderLines();
  recalcAll();
}

function getLineByRow(target) {
  const rowEl = target.closest('tr[data-id]');
  if (!rowEl) return null;
  return lines.find((line) => line.FISTAMP === rowEl.dataset.id) || null;
}

linesBody?.addEventListener('click', async (event) => {
  const actionEl = event.target.closest('[data-a]');
  if (!actionEl) return;
  const row = getLineByRow(actionEl);
  if (!row) return;

  if (actionEl.dataset.a === 'choose_ref') {
    artigoPickRowId = row.FISTAMP;
    if (artigoSearchInput) artigoSearchInput.value = '';
    await loadArtigoRows('');
    artigoModal?.show();
    return;
  }

  if (actionEl.dataset.a === 'miseimp') {
    openMiseimpModal(row.FISTAMP);
    return;
  }

  if (actionEl.dataset.a === 'del') {
    lines = lines.filter((line) => line.FISTAMP !== row.FISTAMP);
    normalizeLineOrder();
    recalcAll();
    renderLines();
  }
});

linesBody?.addEventListener('change', async (event) => {
  const fieldEl = event.target.closest('[data-f]');
  if (!fieldEl) return;
  const row = getLineByRow(fieldEl);
  if (!row) return;

  const field = fieldEl.dataset.f;
  if (field === 'IVAINCL') row.IVAINCL = fieldEl.checked ? 1 : 0;
  else row[field] = fieldEl.value;

  if (field === 'QTT' || field === 'EPV') row[field] = n(row[field], 0);
  if (field === 'DESCONTO') row[field] = pct2(row[field], 0);
  if (field === 'TABIVA') {
    const taxa = getTaxaByTabiva(row.TABIVA);
    if (taxa != null) row.IVA = taxa;
  }
  if (field === 'REF' && String(row.REF || '').trim()) {
    const artigo = await fetchArtigoByRef(row.REF);
    if (artigo) applyArtigoToLine(row, artigo);
    closeRefAutocomplete();
  }

  recalcAll();
  renderLines();
});

artigoTableBody?.addEventListener('click', (event) => {
  const rowEl = event.target.closest('tr[data-artigo-index]');
  if (!rowEl) return;
  const artigo = artigoRows[n(rowEl.dataset.artigoIndex, -1)];
  const line = lines.find((item) => item.FISTAMP === artigoPickRowId);
  if (!artigo || !line) return;
  applyArtigoToLine(line, artigo);
  recalcAll();
  renderLines();
  artigoModal?.hide();
});

miseimpTableBody?.addEventListener('click', (event) => {
  const rowEl = event.target.closest('tr[data-codigo]');
  if (!rowEl) return;
  const line = lines.find((item) => item.FISTAMP === miseimpPickRowId);
  if (!line) return;
  line.MISEIMP = String(rowEl.dataset.codigo || '').trim().toUpperCase();
  recalcAll();
  renderLines();
  miseimpModal?.hide();
});

artigoSearchInput?.addEventListener('input', () => {
  if (artigoTimer) clearTimeout(artigoTimer);
  artigoTimer = setTimeout(() => { loadArtigoRows(artigoSearchInput.value || ''); }, 220);
});

nomeInput?.addEventListener('input', () => {
  if (clientTimer) clearTimeout(clientTimer);
  clientTimer = setTimeout(() => { searchClients(nomeInput.value || ''); }, 220);
});

nomeInput?.addEventListener('blur', () => {
  setTimeout(() => { renderClientSuggestions([]); }, 180);
});

clientDetailBtn?.addEventListener('click', openClientDetail);
btnCalc?.addEventListener('click', openCalcModal);

ndocSel?.addEventListener('change', () => {
  header.NDOC = n(ndocSel.value, 0);
  syncSeriesFromHeader();
  lines.forEach((line) => {
    line.NDOC = header.NDOC;
    line.NMDOC = header.NMDOC;
  });
});

descontoInput?.addEventListener('input', () => {
  header.DESCONTO = pct2(descontoInput.value, 0);
  recalcAll();
});

descontoInput?.addEventListener('blur', () => {
  header.DESCONTO = pct2(descontoInput.value, 0);
  descontoInput.value = fmtInputDecimal(header.DESCONTO, 2);
  recalcAll();
});

fdataInput?.addEventListener('change', async () => {
  header.FDATA = fdataInput.value || todayISO();
  await loadFts();
});

btnGuardar?.addEventListener('click', () => { saveDoc(true, true); });
btnEmitir?.addEventListener('click', emitirDoc);
btnCancelar?.addEventListener('click', cancelarDoc);
btnAnular?.addEventListener('click', anularDoc);
btnDuplicar?.addEventListener('click', duplicarDoc);
btnImprimir?.addEventListener('click', imprimirDoc);
btnVerHtml?.addEventListener('click', verHtmlDoc);
addLineBtn?.addEventListener('click', newLine);

miseimpModalEl?.addEventListener('hidden.bs.modal', () => {
  miseimpPickRowId = null;
});

artigoModalEl?.addEventListener('hidden.bs.modal', () => {
  artigoPickRowId = null;
});

showOverlay('A carregar...');
try {
  await Promise.all([
    loadCcustoOptions(),
    loadTaxaOptions(),
    loadMiseimpOptions()
  ]);
  await loadDoc();
} finally {
  hideOverlay();
}
