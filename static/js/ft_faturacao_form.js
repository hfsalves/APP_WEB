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
const fsConfig = {
  clientNo: Number(context.fsConfig?.clientNo || 0) || 0,
  client: context.fsConfig?.client && typeof context.fsConfig.client === 'object' ? context.fsConfig.client : null,
  limit: Number(String(context.fsConfig?.limit || '').replace(',', '.')) || 0,
  clientError: String(context.fsConfig?.clientError || '').trim(),
  limitError: String(context.fsConfig?.limitError || '').trim()
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
const moedaSugg = document.getElementById('FT_MOEDA_SUGG');
const moedaStatus = document.getElementById('FT_MOEDA_STATUS');
const cambioInput = document.getElementById('FT_CAMBIO');
const totalLiquidoInput = document.getElementById('FT_ETTILIQ');
const totalIvaInput = document.getElementById('FT_ETTIVA');
const totalInput = document.getElementById('FT_ETOTAL');
const clientSugg = document.getElementById('FT_CLIENT_SUGG');
const clientDetailBtn = document.getElementById('FT_CLIENT_DETAIL');
const addLineBtn = document.getElementById('ftAddLinha');
const linesPanel = document.querySelector('.sz_ft_lines_panel');
const btnCalc = document.getElementById('ftBtnCalc');
const btnCopiarOrigem = document.getElementById('ftBtnCopiarOrigem');
const btnCopiarOrigemText = document.getElementById('ftBtnCopiarOrigemText');
const btnGuardar = document.getElementById('ftBtnGuardar');
const btnEmitir = document.getElementById('ftBtnEmitir');
const btnCancelar = document.getElementById('ftBtnCancelar');
const btnAnular = document.getElementById('ftBtnAnular');
const btnDuplicar = document.getElementById('ftBtnDuplicar');
const btnImprimir = document.getElementById('ftBtnImprimir');
const btnImprimirSemValores = document.getElementById('ftBtnImprimirSemValores');
const btnVerHtml = document.getElementById('ftBtnVerHtml');
const hiddenMorada = document.getElementById('FT_MORADA');
const hiddenCodpost = document.getElementById('FT_CODPOST');
const hiddenLocal = document.getElementById('FT_LOCAL');
const hiddenPais = document.getElementById('FT_PAIS');
const transportSection = document.getElementById('ftTransportSection');
const transportEstadoBadge = document.getElementById('ftTransportEstadoBadge');
const localCargaSel = document.getElementById('FT_LOCAL_CARGA_ID');
const localDescargaSel = document.getElementById('FT_LOCAL_DESCARGA_ID');
const dataHoraInicioTransporteInput = document.getElementById('FT_DATA_HORA_INICIO_TRANSPORTE');
const matriculaInput = document.getElementById('FT_MATRICULA');
const codigoAtInput = document.getElementById('FT_CODIGO_AT');

const clienteModalEl = document.getElementById('ftClienteModal');
const clienteModal = clienteModalEl && window.bootstrap?.Modal ? new window.bootstrap.Modal(clienteModalEl) : null;
const clienteApplyBtn = document.getElementById('ftClienteApply');
const artigoModalEl = document.getElementById('ftArtigoModal');
const artigoModal = artigoModalEl && window.bootstrap?.Modal ? new window.bootstrap.Modal(artigoModalEl) : null;
const origemModalEl = document.getElementById('ftOrigemModal');
const origemModal = origemModalEl && window.bootstrap?.Modal ? new window.bootstrap.Modal(origemModalEl) : null;
const miseimpModalEl = document.getElementById('ftMiseimpModal');
const miseimpModal = miseimpModalEl && window.bootstrap?.Modal ? new window.bootstrap.Modal(miseimpModalEl) : null;
const calcModalEl = document.getElementById('ftCalcModal');
const calcModal = calcModalEl && window.bootstrap?.Modal ? new window.bootstrap.Modal(calcModalEl) : null;
const artigoSearchInput = document.getElementById('ftArtigoSearch');
const artigoTableBody = document.getElementById('ftArtigoTableBody');
const origemClientInfo = document.getElementById('ftOrigemClientInfo');
const origemModalTitle = document.getElementById('ftOrigemModalTitle');
const origemIncludeUsed = document.getElementById('ftOrigemIncludeUsed');
const origemIncludeUsedWrap = document.getElementById('ftOrigemIncludeUsedWrap');
const origemIncludeUsedText = document.getElementById('ftOrigemIncludeUsedText');
const origemTableBody = document.getElementById('ftOrigemTableBody');
const origemConfirmBtn = document.getElementById('ftOrigemConfirm');
const origemInfoWrap = document.getElementById('ftOrigemInfoWrap');
const origemInfoInput = document.getElementById('FT_ORIGEM_INFO');
const motivoReferenciaWrap = document.getElementById('ftMotivoReferenciaWrap');
const motivoReferenciaInput = document.getElementById('FT_MOTIVO_REFERENCIA');
const clienteModalNoInput = document.getElementById('FTM_NO');
const clienteModalNomeInput = document.getElementById('FTM_NOME');
const clienteModalNifInput = document.getElementById('FTM_NIF');
const clienteModalMoradaInput = document.getElementById('FTM_MORADA');
const clienteModalCodpostInput = document.getElementById('FTM_CODPOST');
const clienteModalLocalInput = document.getElementById('FTM_LOCAL');
const clienteModalPaisInput = document.getElementById('FTM_PAIS');
const miseimpTableBody = document.getElementById('ftMiseimpTableBody');
const calcNoEl = document.getElementById('ftCalcNo');
const calcNomeEl = document.getElementById('ftCalcNome');
const calcNifEl = document.getElementById('ftCalcNif');
const calcMoradaEl = document.getElementById('ftCalcMorada');
const calcMoedaEl = document.getElementById('ftCalcMoeda');
const calcCambioEl = document.getElementById('ftCalcCambio');
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
let origemRows = [];
let origemPickStamp = '';
let isBlocked = false;
let clientTimer = null;
let artigoTimer = null;
let artigoPickRowId = null;
let miseimpPickRowId = null;
let lastLineCursorRowId = null;
let refAutocompleteMenu = null;
let refAutocompleteInput = null;
let refAutocompleteRowId = null;
let refAutocompleteHost = null;
let refAutocompleteItems = [];
let refAutocompleteTimer = null;
let refAutocompleteRequestId = 0;
let currencyOptions = [];
let currencyTimer = null;
let currencyPromise = null;
let currencySearchRequestId = 0;
let transportLocais = { carga: [], descarga: [] };

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

function currentClientNo() {
  return n(header.NO, n(noInput?.value, 0));
}

function hasCurrentLinesToReplace() {
  return lines.some((line) => isMeaningfulLine(line));
}

async function confirmReplaceCurrentLines() {
  if (!hasCurrentLinesToReplace()) return true;
  const message = 'Substituir as linhas atuais e os dados comerciais copiados do documento origem?';
  if (typeof window.szConfirm === 'function') {
    return await window.szConfirm(message, { title: 'Copiar de outro documento' });
  }
  return window.confirm(message);
}

function normalizeLineOrder(preserveCurrentOrder = false) {
  if (!preserveCurrentOrder) {
    lines.sort((a, b) => n(a.LORDEM, 0) - n(b.LORDEM, 0));
  }
  lines.forEach((line, index) => {
    line.LORDEM = (index + 1) * 10;
  });
}

function resolveNewLineInsertIndex() {
  normalizeLineOrder();
  const anchorId = String(lastLineCursorRowId || '').trim();
  if (!anchorId) return lines.length;
  const currentIndex = lines.findIndex((line) => line.FISTAMP === anchorId);
  return currentIndex >= 0 ? currentIndex + 1 : lines.length;
}

function focusLineField(rowId, field = 'REF') {
  if (!linesBody || !rowId) return;
  const selector = `tr[data-id="${String(rowId).trim()}"] [data-f="${field}"]`;
  const target = linesBody.querySelector(selector);
  if (!target) return;
  target.focus();
  if (typeof target.select === 'function') target.select();
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

function currencyCode(value) {
  return String(value || '').trim().toUpperCase().slice(0, 3);
}

function currencyCambioValue(code, cambio) {
  const normalizedCode = currencyCode(code) || 'EUR';
  const raw = String(cambio ?? '').trim();
  if (!raw) return normalizedCode === 'EUR' ? '1.000000' : '';
  return scaledToPlain(parseScaled(raw), 6);
}

function setCurrencyStatus(message = '', tone = 'muted') {
  if (!moedaStatus) return;
  const text = String(message || '');
  moedaStatus.textContent = text;
  moedaStatus.classList.remove('sz_text_muted', 'sz_text_warning', 'sz_text_success');
  if (tone === 'warning') moedaStatus.classList.add('sz_text_warning');
  else if (tone === 'success') moedaStatus.classList.add('sz_text_success');
  else moedaStatus.classList.add('sz_text_muted');
  moedaStatus.style.display = text ? 'block' : 'none';
  moedaInput?.closest('.sz_ft_autocomplete')?.classList.toggle('has-status', Boolean(text));
}

function syncCurrencyInputsFromHeader() {
  const code = currencyCode(header.MOEDA) || 'EUR';
  const cambioValue = currencyCambioValue(code, header.CAMBIO);
  header.MOEDA = code;
  header.CAMBIO = cambioValue;
  if (moedaInput && document.activeElement !== moedaInput) moedaInput.value = code;
  if (cambioInput && document.activeElement !== cambioInput) cambioInput.value = cambioValue ? fmtInputDecimal(cambioValue, 6) : '';
}

async function ensureCurrencyOptions(force = false) {
  if (!force && currencyOptions.length) return currencyOptions;
  if (!force && currencyPromise) return currencyPromise;
  currencyPromise = fetch('/api/faturacao/fx-rates')
    .then(async (response) => {
      const data = await response.json().catch(() => ({}));
      if (!response.ok || !Array.isArray(data)) {
        throw new Error(data?.error || 'Não foi possível carregar as moedas.');
      }
      currencyOptions = data.map((row) => ({
        CODIGO: currencyCode(row?.CODIGO || ''),
        DESCRICAO: String(row?.DESCRICAO || '').trim(),
        CAMBIO: currencyCambioValue(row?.CODIGO || '', row?.CAMBIO),
        DATA_REF: String(row?.DATA_REF || '').trim(),
        FONTE: String(row?.FONTE || '').trim()
      })).filter((row) => row.CODIGO);
      return currencyOptions;
    })
    .finally(() => {
      currencyPromise = null;
    });
  return currencyPromise;
}

function hideCurrencySuggestions() {
  if (!moedaSugg) return;
  moedaSugg.style.display = 'none';
  moedaSugg.innerHTML = '';
}

function filterCurrencyOptions(term) {
  const query = currencyCode(term);
  if (!query) return currencyOptions.slice(0, 12);
  const starts = [];
  const contains = [];
  currencyOptions.forEach((item) => {
    const code = item.CODIGO;
    const desc = String(item.DESCRICAO || '').toUpperCase();
    if (code.startsWith(query) || desc.startsWith(query)) starts.push(item);
    else if (code.includes(query) || desc.includes(query)) contains.push(item);
  });
  return starts.concat(contains).slice(0, 12);
}

function applyCurrencyOption(item) {
  if (!item) return;
  header.MOEDA = currencyCode(item.CODIGO) || 'EUR';
  header.CAMBIO = currencyCambioValue(header.MOEDA, item.CAMBIO);
  syncCurrencyInputsFromHeader();
  if (moedaInput) moedaInput.value = header.MOEDA;
  if (cambioInput) cambioInput.value = header.CAMBIO ? fmtInputDecimal(header.CAMBIO, 6) : '';
  const refDate = String(item.DATA_REF || '').trim();
  const source = String(item.FONTE || '').trim().toUpperCase();
  if (header.MOEDA === 'EUR') setCurrencyStatus('');
  else if (source === 'OXR') setCurrencyStatus('Moeda encontrada no Open Exchange Rates. Introduza o câmbio manualmente.', 'warning');
  else setCurrencyStatus(refDate ? `Taxa BCE de ${refDate}` : 'Taxa encontrada no BCE.', 'success');
  hideCurrencySuggestions();
}

function renderCurrencySuggestions(items) {
  if (!moedaSugg) return;
  if (!Array.isArray(items) || !items.length || isBlocked) {
    hideCurrencySuggestions();
    return;
  }
  moedaSugg.innerHTML = items.map((item, index) => `
    <button type="button" class="sz_ft_suggestion_item" data-currency-index="${index}">
      <strong>${esc(item.CODIGO)}</strong>
      <small>${esc(item.DESCRICAO || item.CODIGO)}${item.CAMBIO ? ` · ${esc(fmtInputDecimal(item.CAMBIO || '', 6))}` : ' · câmbio manual'}</small>
    </button>
  `).join('');
  moedaSugg.style.display = 'block';
  moedaSugg.querySelectorAll('[data-currency-index]').forEach((button) => {
    button.addEventListener('mousedown', (event) => {
      event.preventDefault();
      const item = items[n(button.dataset.currencyIndex, -1)];
      applyCurrencyOption(item);
    });
  });
}

async function searchCurrencyOptions(term = '') {
  if (isBlocked) {
    hideCurrencySuggestions();
    return;
  }
  const query = currencyCode(term);
  const requestId = ++currencySearchRequestId;
  setCurrencyStatus('A pesquisar no BCE...', 'muted');
  try {
    const items = await ensureCurrencyOptions();
    if (requestId !== currencySearchRequestId) return;
    if (!Array.isArray(items) || !items.length) {
      hideCurrencySuggestions();
      setCurrencyStatus('BCE sem resposta útil. Pode introduzir moeda e câmbio manualmente.', 'warning');
      return;
    }
    const filtered = filterCurrencyOptions(query);
    if (filtered.length || !query) {
      renderCurrencySuggestions(filtered);
      if (query) setCurrencyStatus('Selecione uma moeda do BCE ou introduza o câmbio manualmente.', 'muted');
      else setCurrencyStatus('');
      return;
    }

    setCurrencyStatus('Não encontrado no BCE. A pesquisar no Open Exchange Rates...', 'muted');
    const response = await fetch(`/api/faturacao/fx-rates?q=${encodeURIComponent(query)}`);
    const data = await response.json().catch(() => []);
    if (requestId !== currencySearchRequestId) return;
    if (!response.ok || !Array.isArray(data) || !data.length) {
      hideCurrencySuggestions();
      setCurrencyStatus('Moeda não encontrada no BCE. Introduza o câmbio manualmente.', 'warning');
      return;
    }
    renderCurrencySuggestions(data);
    setCurrencyStatus('Moeda encontrada no Open Exchange Rates. O câmbio continua manual.', 'warning');
  } catch {
    if (requestId !== currencySearchRequestId) return;
    hideCurrencySuggestions();
    setCurrencyStatus('Não foi possível pesquisar a moeda. Introduza o câmbio manualmente.', 'warning');
  }
}

async function resolveCurrencyInput() {
  const typed = currencyCode(moedaInput?.value || '');
  if (!typed) {
    syncCurrencyInputsFromHeader();
    hideCurrencySuggestions();
    setCurrencyStatus('');
    return;
  }
  const exact = currencyOptions.find((item) => item.CODIGO === typed);
  if (exact) {
    applyCurrencyOption(exact);
    return;
  }
  try {
    const response = await fetch(`/api/faturacao/fx-rates?q=${encodeURIComponent(typed)}`);
    const data = await response.json().catch(() => []);
    if (response.ok && Array.isArray(data)) {
      const exactFallback = data.find((item) => currencyCode(item.CODIGO) === typed);
      if (exactFallback) {
        applyCurrencyOption(exactFallback);
        return;
      }
    }
  } catch {
  }
  const previousCode = currencyCode(header.MOEDA);
  header.MOEDA = typed;
  if (typed === 'EUR') {
    header.CAMBIO = '1.000000';
  } else if (previousCode !== typed) {
    header.CAMBIO = '';
  }
  syncCurrencyInputsFromHeader();
  if (moedaInput) moedaInput.value = typed;
  setCurrencyStatus('Moeda não encontrada no BCE. Introduza o câmbio manualmente.', 'warning');
  hideCurrencySuggestions();
}

function getCalcCurrencyContext() {
  const code = currencyCode(header.MOEDA) || 'EUR';
  if (code === 'EUR') {
    return { code, cambioText: '1.000000', cambioScaled: SCALE, hasEuroConversion: true };
  }
  const cambioText = currencyCambioValue(code, header.CAMBIO);
  const cambioScaled = cambioText ? parseScaled(cambioText) : 0n;
  return {
    code,
    cambioText,
    cambioScaled: cambioScaled > 0n ? cambioScaled : 0n,
    hasEuroConversion: cambioScaled > 0n
  };
}

function convertDocScaledToEuro(amountScaled, currencyCtx) {
  const safeAmount = BigInt(amountScaled || 0n);
  if (!currencyCtx || currencyCtx.code === 'EUR') return safeAmount;
  if (!currencyCtx.hasEuroConversion || !currencyCtx.cambioScaled) return null;
  return roundDiv(safeAmount * SCALE, currencyCtx.cambioScaled);
}

function formatCalcMoneyCell(amountScaled, currencyCtx, decimals = 2, euroDecimals = decimals) {
  const docText = `${formatScaled(amountScaled, decimals)} ${currencyCtx?.code || 'EUR'}`;
  if (!currencyCtx || currencyCtx.code === 'EUR') {
    return { doc: docText, eur: '', html: `<div class="sz_ft_calc_money"><strong>${esc(docText)}</strong></div>` };
  }
  const euroScaled = convertDocScaledToEuro(amountScaled, currencyCtx);
  const eurText = euroScaled == null ? '— EUR' : `${formatScaled(euroScaled, euroDecimals)} EUR`;
  return {
    doc: docText,
    eur: eurText,
    html: `<div class="sz_ft_calc_money"><strong>${esc(docText)}</strong><small>${esc(eurText)}</small></div>`
  };
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
    FISTAMP_ORIGEM: String(line.FISTAMP_ORIGEM || '').trim(),
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

function serializeHeaderForSave(source = {}) {
  return { ...source };
}

function serializeLineForSave(line = {}) {
  return {
    FISTAMP: String(line.FISTAMP || '').trim(),
    FISTAMP_ORIGEM: String(line.FISTAMP_ORIGEM || '').trim(),
    FTSTAMP: String(line.FTSTAMP || '').trim(),
    NDOC: n(line.NDOC, 0),
    NMDOC: String(line.NMDOC || '').trim(),
    FNO: n(line.FNO, 0),
    REF: String(line.REF || '').trim(),
    DESIGN: String(line.DESIGN || '').trim(),
    QTT: n(line.QTT, 0),
    UNIDADE: String(line.UNIDADE || '').trim(),
    EPV: n(line.EPV, 0),
    DESCONTO: n(line.DESCONTO, 0),
    IVA: n(line.IVA, 0),
    IVAINCL: Number(n(line.IVAINCL, 0)) === 1 ? 1 : 0,
    TABIVA: String(line.TABIVA ?? '').trim(),
    ETILIQUIDO: String(line.ETILIQUIDO ?? '').trim(),
    UNITPRICE_FISCAL: line.UNITPRICE_FISCAL == null ? null : String(line.UNITPRICE_FISCAL).trim(),
    FAMILIA: String(line.FAMILIA || '').trim(),
    FICCUSTO: String(line.FICCUSTO || '').trim(),
    MISEIMP: lineCode(line),
    LORDEM: n(line.LORDEM, 0)
  };
}

function currentFtsRow() {
  const currentSerie = String(header.SERIE || '').trim();
  const currentNdoc = n(header.NDOC, 0);
  return ftsRows.find((row) => n(row.NDOC, 0) === currentNdoc && String(row.SERIE || '').trim() === currentSerie)
    || ftsRows.find((row) => n(row.NDOC, 0) === currentNdoc)
    || null;
}

function currentDocType() {
  const code = String(currentFtsRow()?.TIPOSAFT || '').trim().toUpperCase();
  if (code) return code;
  const nmdoc = String(header.NMDOC || '').trim().toUpperCase();
  if (nmdoc.includes('SIMPLIFICADA') || nmdoc.startsWith('FS')) return 'FS';
  if (nmdoc.includes('PRO-FORMA') || nmdoc.includes('PRO FORMA') || nmdoc.startsWith('PF')) return 'PF';
  if (nmdoc.includes('ORÇAMENTO') || nmdoc.includes('ORCAMENTO') || nmdoc.startsWith('OR')) return 'OR';
  if (nmdoc.includes('CRÉDITO') || nmdoc.includes('CREDITO') || nmdoc.startsWith('NC')) return 'NC';
  if (nmdoc.includes('RECIBO') || nmdoc.startsWith('FR')) return 'FR';
  return 'FT';
}

function isCurrentTransportDoc() {
  return Number(header.IS_DOC_TRANSPORTE || currentFtsRow()?.IS_DOC_TRANSPORTE || 0) === 1;
}

function currentTransportState() {
  if (!isCurrentTransportDoc()) return 'RASCUNHO';
  const raw = String(header.DOC_TRANSPORTE_ESTADO || '').trim().toUpperCase();
  if (['RASCUNHO', 'EMITIDO', 'PRONTO', 'IMPRESSO'].includes(raw)) return raw;
  return Number(header.ESTADO || 0) === 1 ? 'EMITIDO' : 'RASCUNHO';
}

function isTransportTransportOnlyPhase() {
  return isCurrentTransportDoc() && Number(header.ESTADO || 0) === 1 && currentTransportState() !== 'IMPRESSO' && Number(header.ANULADA || 0) !== 1;
}

function isCurrentNcDoc() {
  return currentDocType() === 'NC';
}

function isCurrentFsDoc() {
  return currentDocType() === 'FS';
}

function setClientDetailEditable(editable) {
  const allowEdit = Boolean(editable);
  [clienteModalNomeInput, clienteModalNifInput, clienteModalMoradaInput, clienteModalCodpostInput, clienteModalLocalInput, clienteModalPaisInput].forEach((input) => {
    if (!input) return;
    input.readOnly = !allowEdit;
    input.disabled = false;
  });
  if (clienteModalNoInput) {
    clienteModalNoInput.readOnly = true;
    clienteModalNoInput.disabled = false;
  }
  if (clienteApplyBtn) {
    clienteApplyBtn.style.display = allowEdit ? '' : 'none';
    clienteApplyBtn.disabled = isBlocked;
  }
}

function fillClientModal(values = {}) {
  if (clienteModalNoInput) clienteModalNoInput.value = n(values.NO, 0) || '';
  if (clienteModalNomeInput) clienteModalNomeInput.value = String(values.NOME || '').trim();
  if (clienteModalNifInput) clienteModalNifInput.value = String(values.NIF || values.NCONT || '').trim();
  if (clienteModalMoradaInput) clienteModalMoradaInput.value = String(values.MORADA || '').trim();
  if (clienteModalCodpostInput) clienteModalCodpostInput.value = String(values.CODPOST || '').trim();
  if (clienteModalLocalInput) clienteModalLocalInput.value = String(values.LOCAL || '').trim();
  if (clienteModalPaisInput) clienteModalPaisInput.value = String(values.PAIS || '').trim();
}

function applyClientModalToHeader() {
  if (!isCurrentFsDoc()) return;
  header.NOME = String(clienteModalNomeInput?.value || '').trim();
  header.NCONT = String(clienteModalNifInput?.value || '').trim();
  header.MORADA = String(clienteModalMoradaInput?.value || '').trim();
  header.CODPOST = String(clienteModalCodpostInput?.value || '').trim();
  header.LOCAL = String(clienteModalLocalInput?.value || '').trim();
  header.PAIS = String(clienteModalPaisInput?.value || '').trim();
  if (nomeInput) nomeInput.value = header.NOME || '';
  if (nifInput) nifInput.value = header.NCONT || '';
  setHiddenClientFields(header);
  clienteModal?.hide();
}

async function applyFsConfiguredClient(force = false) {
  if (!isCurrentFsDoc()) return true;
  if (fsConfig.clientError) {
    alertMessage(fsConfig.clientError);
    return false;
  }
  if (!fsConfig.client || n(fsConfig.client.NO, 0) <= 0) {
    alertMessage('O parâmetro CLIENTE_FS não está configurado corretamente.');
    return false;
  }
  if (!force && n(header.NO, 0) === n(fsConfig.client.NO, 0)) {
    return true;
  }
  applyClient(fsConfig.client);
  return true;
}

function validateFsHeader() {
  if (!isCurrentFsDoc()) return '';
  if (fsConfig.clientError) return fsConfig.clientError;
  if (fsConfig.limitError) return fsConfig.limitError;
  if (n(header.NO, 0) !== n(fsConfig.clientNo, 0)) {
    return 'A fatura simplificada tem de usar o cliente genérico configurado em CLIENTE_FS.';
  }
  if (n(header.ETOTAL, 0) > n(fsConfig.limit, 0)) {
    return 'O total da fatura simplificada excede o limite configurado.';
  }
  return '';
}

function buildOrigemSummary() {
  const parts = [];
  if (String(header.NUMDOC_ORIGEM || '').trim()) parts.push(String(header.NUMDOC_ORIGEM || '').trim());
  if (String(header.DATA_ORIGEM || '').trim()) parts.push(safeDate(header.DATA_ORIGEM));
  return parts.join(' · ') || '';
}

function updateOrigemUi() {
  const isNc = isCurrentNcDoc();
  const hasOrigem = Boolean(String(header.FTSTAMP_ORIGEM || '').trim());
  if (btnCopiarOrigemText) {
    btnCopiarOrigemText.textContent = isNc ? 'Copiar de documento de venda' : 'Copiar de outro documento';
  }
  if (origemModalTitle) {
    origemModalTitle.textContent = isNc ? 'Selecionar documento origem' : 'Copiar de outro documento';
  }
  if (origemIncludeUsedWrap) {
    origemIncludeUsedWrap.style.display = isNc ? 'none' : '';
  }
  if (origemIncludeUsedText) {
    origemIncludeUsedText.textContent = 'Mostrar pró-forma já copiada';
  }
  if (origemInfoWrap) {
    origemInfoWrap.style.display = (isNc || hasOrigem) ? '' : 'none';
  }
  if (origemInfoInput) {
    origemInfoInput.value = buildOrigemSummary();
  }
  if (motivoReferenciaWrap) {
    motivoReferenciaWrap.style.display = isNc ? '' : 'none';
  }
  if (motivoReferenciaInput && document.activeElement !== motivoReferenciaInput) {
    motivoReferenciaInput.value = String(header.MOTIVO_REFERENCIA || '').trim();
  }
}

function buildLocalOptionLabel(item) {
  return String(item?.LABEL || item?.DESIGNACAO || '').trim();
}

function renderLocalSelect(selectEl, rows, currentValue) {
  if (!selectEl) return;
  const current = String(currentValue || '').trim();
  const options = Array.isArray(rows) ? rows : [];
  const exists = options.some((row) => String(row?.LOCALSTAMP || '').trim() === current);
  const html = ['<option value="">---</option>']
    .concat(options.map((row) => `<option value="${esc(String(row?.LOCALSTAMP || '').trim())}" ${String(row?.LOCALSTAMP || '').trim() === current ? 'selected' : ''}>${esc(buildLocalOptionLabel(row))}</option>`))
    .join('');
  selectEl.innerHTML = exists || !current ? html : `${html}<option value="${esc(current)}" selected>${esc(current)}</option>`;
}

function updateTransportUi() {
  const active = isCurrentTransportDoc();
  const state = currentTransportState();
  if (transportSection) transportSection.style.display = active ? '' : 'none';
  if (transportEstadoBadge) {
    transportEstadoBadge.textContent = state;
    transportEstadoBadge.classList.remove('sz_badge_info', 'sz_badge_warning', 'sz_badge_success', 'sz_badge_danger');
    if (state === 'IMPRESSO') transportEstadoBadge.classList.add('sz_badge', 'sz_badge_danger');
    else if (state === 'PRONTO') transportEstadoBadge.classList.add('sz_badge', 'sz_badge_success');
    else if (state === 'EMITIDO') transportEstadoBadge.classList.add('sz_badge', 'sz_badge_info');
    else transportEstadoBadge.classList.add('sz_badge', 'sz_badge_warning');
  }
  renderLocalSelect(localCargaSel, transportLocais.carga, header.LOCAL_CARGA_ID);
  renderLocalSelect(localDescargaSel, transportLocais.descarga, header.LOCAL_DESCARGA_ID);
  if (dataHoraInicioTransporteInput && document.activeElement !== dataHoraInicioTransporteInput) dataHoraInicioTransporteInput.value = String(header.DATA_HORA_INICIO_TRANSPORTE || '').trim();
  if (matriculaInput && document.activeElement !== matriculaInput) matriculaInput.value = String(header.MATRICULA || '').trim();
  if (codigoAtInput && document.activeElement !== codigoAtInput) codigoAtInput.value = String(header.CODIGO_AT || '').trim();
  if (btnImprimirSemValores) btnImprimirSemValores.style.display = active ? '' : 'none';
}

async function loadTransportLocais() {
  if (!isCurrentTransportDoc()) {
    transportLocais = { carga: [], descarga: [] };
    updateTransportUi();
    return;
  }
  const cargaResponse = await fetch('/api/faturacao/locais?tipo=carga');
  const cargaRows = await cargaResponse.json().catch(() => []);
  const no = n(header.NO, 0);
  let descargaRows = [];
  if (no > 0) {
    const descargaResponse = await fetch(`/api/faturacao/locais?tipo=descarga&no=${encodeURIComponent(no)}`);
    descargaRows = await descargaResponse.json().catch(() => []);
  }
  transportLocais = {
    carga: Array.isArray(cargaRows) ? cargaRows : [],
    descarga: Array.isArray(descargaRows) ? descargaRows : [],
  };
  updateTransportUi();
}

function validateTransportForFinalPrint() {
  if (!isCurrentTransportDoc()) return '';
  mapUiToHeader();
  if (!String(header.CODIGO_AT || '').trim()) return 'Não é possível imprimir o documento de transporte sem código AT.';
  if (!String(header.LOCAL_CARGA_ID || '').trim()) return 'Não é possível imprimir o documento de transporte sem local de carga.';
  if (!String(header.LOCAL_DESCARGA_ID || '').trim()) return 'Não é possível imprimir o documento de transporte sem local de descarga.';
  if (!String(header.MATRICULA || '').trim()) return 'Não é possível imprimir o documento de transporte sem matrícula.';
  if (!String(header.DATA_HORA_INICIO_TRANSPORTE || '').trim()) return 'Não é possível imprimir o documento de transporte sem data/hora de início.';
  return '';
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
    const label = String(row.NMDOC || row.DESCR || '').trim();
    if (!map.has(ndoc)) map.set(ndoc, label);
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
    header.IS_DOC_TRANSPORTE = 0;
    ndocSel.value = '';
    if (serieInput) serieInput.value = '';
    return;
  }
  const currentSerie = String(header.SERIE || '').trim();
  const selectedSerieRow = matchingRows.find((row) => String(row.SERIE || '').trim() === currentSerie) || matchingRows[0];
  header.SERIE = String(selectedSerieRow.SERIE || '').trim();
  header.NDOC = n(selectedSerieRow.NDOC, 0);
  header.NMDOC = String(selectedSerieRow.NMDOC || selectedSerieRow.DESCR || '').trim();
  header.IS_DOC_TRANSPORTE = Number(selectedSerieRow.IS_DOC_TRANSPORTE || 0) === 1 ? 1 : 0;
  ndocSel.value = String(header.NDOC || '');
  if (serieInput) serieInput.value = header.SERIE || '';
}

async function loadFts() {
  if (!currentEntity.FEID && !currentEntity.FESTAMP) {
    ftsRows = [];
    renderNdocOptions();
    syncSeriesFromHeader();
    return;
  }
  const ano = n(String(header.FDATA || '').slice(0, 4), new Date().getFullYear());
  const query = currentEntity.FEID
    ? `feid=${encodeURIComponent(currentEntity.FEID)}&ano=${encodeURIComponent(ano)}`
    : `festamp=${encodeURIComponent(currentEntity.FESTAMP)}&ano=${encodeURIComponent(ano)}`;
  const response = await fetch(`/api/lookups/fts?${query}`);
  ftsRows = await response.json().catch(() => []);
  if (!Array.isArray(ftsRows)) ftsRows = [];
  if (!ftsRows.length) {
    header.NDOC = 0;
    header.NMDOC = '';
    header.SERIE = '';
  } else if (!ftsRows.some((row) => n(row.NDOC, 0) === n(header.NDOC, 0))) {
    header.NDOC = n(ftsRows[0].NDOC, 0);
    header.NMDOC = String(ftsRows[0].NMDOC || ftsRows[0].DESCR || '').trim();
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
  if (query.length < 2 || isBlocked || isCurrentFsDoc()) {
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
  const previousNo = n(header.NO, 0);
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
  if (previousNo && previousNo !== header.NO && String(header.FTSTAMP_ORIGEM || '').trim()) {
    header.FTSTAMP_ORIGEM = '';
    header.TIPODOC_ORIGEM = '';
    header.NUMDOC_ORIGEM = '';
    header.DATA_ORIGEM = '';
    header.MOTIVO_REFERENCIA = '';
  }
  setHiddenClientFields(header);
  updateOrigemUi();
  renderClientSuggestions([]);
  if (isCurrentTransportDoc()) {
    loadTransportLocais().catch(() => {
      transportLocais = { carga: [], descarga: [] };
      updateTransportUi();
    });
  }
}

async function openClientDetail() {
  if (isCurrentFsDoc()) {
    const no = n(header.NO, 0) || n(fsConfig.clientNo, 0);
    if (!no) {
      alertMessage(fsConfig.clientError || 'O parâmetro CLIENTE_FS não está configurado.');
      return;
    }
    fillClientModal({
      NO: no,
      NOME: header.NOME,
      NCONT: header.NCONT,
      MORADA: header.MORADA,
      CODPOST: header.CODPOST,
      LOCAL: header.LOCAL,
      PAIS: header.PAIS,
    });
    setClientDetailEditable(true);
    clienteModal?.show();
    return;
  }
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
  fillClientModal(data);
  setClientDetailEditable(false);
  clienteModal?.show();
}

function updateStatusUi() {
  const anulada = Number(header.ANULADA || 0) === 1;
  const emitida = Number(header.ESTADO || 0) === 1;
  let label = anulada ? 'Anulada' : (emitida ? `Emitida #${n(header.FNO, 0)}` : 'Rascunho');
  let badgeClass = anulada ? 'sz_badge_danger' : (emitida ? 'sz_badge_success' : 'sz_badge_warning');
  if (!anulada && isCurrentTransportDoc()) {
    const transportState = currentTransportState();
    if (transportState === 'IMPRESSO') {
      label = `Impresso #${n(header.FNO, 0)}`;
      badgeClass = 'sz_badge_danger';
    } else if (transportState === 'PRONTO') {
      label = `Pronto #${n(header.FNO, 0)}`;
      badgeClass = 'sz_badge_success';
    } else if (transportState === 'EMITIDO') {
      label = `Emitido #${n(header.FNO, 0)}`;
      badgeClass = 'sz_badge_info';
    } else {
      label = 'Rascunho transporte';
      badgeClass = 'sz_badge_warning';
    }
  }
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
  syncCurrencyInputsFromHeader();
  const currentCurrency = currencyCode(header.MOEDA);
  if (currentCurrency === 'EUR') setCurrencyStatus('');
  else if (currencyOptions.some((item) => item.CODIGO === currentCurrency)) setCurrencyStatus('Moeda disponível no BCE.', 'muted');
  else if (currentCurrency) setCurrencyStatus('Moeda fora do BCE. Câmbio manual.', 'warning');
  else setCurrencyStatus('');
  if (descontoInput) descontoInput.value = fmtInputDecimal(pct2(header.DESCONTO, 0), 2);
  if (noInput) noInput.value = n(header.NO, 0) || '';
  if (nomeInput) nomeInput.value = header.NOME || '';
  if (nifInput) nifInput.value = header.NCONT || '';
  if (ccustoSel) ccustoSel.value = String(header.CCUSTO || '').trim();
  updateOrigemUi();
  setHiddenClientFields(header);
  syncSeriesFromHeader();
  recalcAll();
  updateStatusUi();
  updateTransportUi();
  window.szEnhanceDecimalInputs?.(document.getElementById('ftFormRoot'));
}

function mapUiToHeader() {
  applySessionEntityToHeader();
  header.NDOC = n(ndocSel?.value, 0);
  header.SERIE = String(serieInput?.value || '').trim();
  const selectedSerie = ftsRows.find((row) => String(n(row.NDOC, 0)) === String(header.NDOC) && String(row.SERIE || '').trim() === header.SERIE);
  header.NMDOC = String(selectedSerie?.NMDOC || selectedSerie?.DESCR || header.NMDOC || '').trim();
  header.IS_DOC_TRANSPORTE = Number(selectedSerie?.IS_DOC_TRANSPORTE || header.IS_DOC_TRANSPORTE || 0) === 1 ? 1 : 0;
  header.FDATA = fdataInput?.value || todayISO();
  header.FTANO = n(String(header.FDATA).slice(0, 4), new Date().getFullYear());
  header.PDATA = pdataInput?.value || header.FDATA;
  header.MOEDA = currencyCode(moedaInput?.value || header.MOEDA || 'EUR') || 'EUR';
  header.CAMBIO = currencyCambioValue(header.MOEDA, cambioInput?.value || header.CAMBIO);
  header.DESCONTO = pct2(descontoInput?.value, 0);
  header.NO = n(noInput?.value, 0);
  header.NOME = String(nomeInput?.value || '').trim();
  header.NCONT = String(nifInput?.value || '').trim();
  header.CCUSTO = String(ccustoSel?.value || '').trim();
  header.MOTIVO_REFERENCIA = String(motivoReferenciaInput?.value || header.MOTIVO_REFERENCIA || '').trim();
  header.MORADA = String(hiddenMorada?.value || '').trim();
  header.CODPOST = String(hiddenCodpost?.value || '').trim();
  header.LOCAL = String(hiddenLocal?.value || '').trim();
  header.PAIS = String(hiddenPais?.value || '').trim();
  header.LOCAL_CARGA_ID = String(localCargaSel?.value || header.LOCAL_CARGA_ID || '').trim();
  header.LOCAL_DESCARGA_ID = String(localDescargaSel?.value || header.LOCAL_DESCARGA_ID || '').trim();
  header.DATA_HORA_INICIO_TRANSPORTE = String(dataHoraInicioTransporteInput?.value || header.DATA_HORA_INICIO_TRANSPORTE || '').trim();
  header.MATRICULA = String(matriculaInput?.value || header.MATRICULA || '').trim();
  header.CODIGO_AT = String(codigoAtInput?.value || header.CODIGO_AT || '').trim();
  updateOrigemUi();
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
  const fiscalLocked = isBlocked || isTransportTransportOnlyPhase();
  const disabled = fiscalLocked ? 'disabled' : '';
  linesBody.innerHTML = lines.map((line) => {
    const isCreditOriginLine = isCurrentNcDoc() && Boolean(String(line.FISTAMP_ORIGEM || '').trim());
    const refDisabled = (fiscalLocked || isCreditOriginLine) ? 'disabled' : '';
    const designDisabled = (fiscalLocked || isCreditOriginLine) ? 'disabled' : '';
    const unidadeDisabled = (fiscalLocked || isCreditOriginLine) ? 'disabled' : '';
    const tabivaDisabled = (fiscalLocked || isCreditOriginLine) ? 'disabled' : '';
    const ivainclDisabled = (fiscalLocked || isCreditOriginLine) ? 'disabled' : '';
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
            <input ${refDisabled} class="sz_input sz_ft_table_input" data-f="REF" value="${esc(line.REF)}">
          </div>
        </td>
        <td><input ${designDisabled} class="sz_input sz_ft_table_input" data-f="DESIGN" value="${esc(line.DESIGN)}"></td>
        <td><input ${disabled} class="sz_input sz_ft_table_input sz_text_right" type="number" step="0.01" data-sz-decimal="true" data-f="QTT" value="${inputNumberValue(line.QTT, 2)}"></td>
        <td><input ${unidadeDisabled} class="sz_input sz_ft_table_input" data-f="UNIDADE" value="${esc(line.UNIDADE)}"></td>
        <td><input ${disabled} class="sz_input sz_ft_table_input sz_text_right" type="number" step="0.01" data-sz-decimal="true" data-f="EPV" value="${inputNumberValue(line.EPV, 2)}"></td>
        <td><input ${disabled} class="sz_input sz_ft_table_input sz_text_right" type="number" step="0.01" min="0" data-sz-decimal="true" data-f="DESCONTO" value="${inputNumberValue(line.DESCONTO, 2)}"></td>
        <td><input class="sz_input sz_ft_table_input sz_text_right" readonly data-f="ETILIQUIDO" value="${fmt(line.ETILIQUIDO, 2)}"></td>
        <td><select ${tabivaDisabled} class="sz_select sz_ft_table_select" data-f="TABIVA">${buildTabivaOptions(line.TABIVA)}</select></td>
        <td>${badgeHtml}</td>
        <td class="sz_text_center"><input ${ivainclDisabled} class="sz_ft_table_checkbox" type="checkbox" data-f="IVAINCL" ${Number(line.IVAINCL || 0) === 1 ? 'checked' : ''}></td>
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

function renderOrigemRows() {
  if (!origemTableBody) return;
  if (!origemRows.length) {
    origemTableBody.innerHTML = '<tr><td colspan="5" class="sz_text_muted">Sem documentos elegíveis.</td></tr>';
    if (origemConfirmBtn) origemConfirmBtn.disabled = true;
    return;
  }
  origemTableBody.innerHTML = origemRows.map((row) => {
    const selectedClass = row.FTSTAMP === origemPickStamp ? ' class="is-selected"' : '';
    let statusHtml = '<span class="sz_badge sz_badge_warning">Rascunho</span>';
    if (Number(row.ANULADA || 0) === 1) {
      statusHtml = '<span class="sz_badge sz_badge_danger">Anulado</span>';
    } else if (Number(row.ESTADO || 0) === 1) {
      statusHtml = '<span class="sz_badge sz_badge_success">Emitido</span>';
    }
    if (row.JA_COPIADO && !isCurrentNcDoc()) {
      statusHtml += '<span class="sz_badge sz_badge_warning sz_ft_copy_status">Já copiado</span>';
    }
    return `
      <tr data-origem-ftstamp="${esc(row.FTSTAMP)}"${selectedClass}>
        <td><strong>${esc(row.TIPODOC || 'PF')}</strong></td>
        <td>
          <div>${esc(row.NUMDOC_FORMATADO || '—')}</div>
        </td>
        <td>${esc(safeDate(row.FDATA || row.DATA || ''))}</td>
        <td>${statusHtml}</td>
        <td class="sz_text_right">${fmt(row.ETOTAL ?? row.TOTALDOC ?? 0, 2)}</td>
      </tr>
    `;
  }).join('');
  if (origemConfirmBtn) origemConfirmBtn.disabled = !origemPickStamp;
}

async function loadOrigemRows() {
  if (!origemTableBody) return;
  mapUiToHeader();
  const no = currentClientNo();
  if (no <= 0) {
    origemRows = [];
    origemPickStamp = '';
    renderOrigemRows();
    return;
  }
  origemTableBody.innerHTML = '<tr><td colspan="5" class="sz_text_muted">A carregar...</td></tr>';
  if (origemConfirmBtn) origemConfirmBtn.disabled = true;
  const includeUsed = origemIncludeUsed?.checked ? 1 : 0;
  const query = new URLSearchParams({
    no: String(no),
    include_used: String(includeUsed),
    ndoc: String(header.NDOC || ''),
    serie: String(header.SERIE || ''),
    ftano: String(header.FTANO || ''),
    fdata: String(header.FDATA || ''),
    nmdoc: String(header.NMDOC || '')
  });
  const response = await fetch(`/api/faturacao/ft/${encodeURIComponent(ftStamp)}/copy-origins?${query.toString()}`);
  const data = await response.json().catch(() => ([]));
  if (!response.ok || !Array.isArray(data)) {
    origemRows = [];
    origemPickStamp = '';
    renderOrigemRows();
    throw new Error(data?.error || 'Não foi possível carregar os documentos origem.');
  }
  origemRows = data;
  if (!origemRows.some((row) => row.FTSTAMP === origemPickStamp)) {
    origemPickStamp = '';
  }
  renderOrigemRows();
}

async function openCopyOrigemModal() {
  mapUiToHeader();
  if (currentClientNo() <= 0) {
    alertMessage('Selecione primeiro o cliente do documento atual.');
    return;
  }
  if (origemClientInfo) {
    origemClientInfo.textContent = `Cliente ${currentClientNo()} · ${(header.NOME || '').trim() || 'sem nome'}`;
  }
  origemPickStamp = '';
  origemRows = [];
  renderOrigemRows();
  origemModal?.show();
  try {
    await loadOrigemRows();
  } catch (error) {
    alertMessage(error?.message || 'Não foi possível carregar os documentos origem.');
  }
}

async function copyFromSelectedOrigem() {
  mapUiToHeader();
  if (!origemPickStamp) {
    alertMessage('Selecione um documento origem.');
    return;
  }
  if (currentClientNo() <= 0) {
    alertMessage('Selecione primeiro o cliente do documento atual.');
    return;
  }
  const confirmed = await confirmReplaceCurrentLines();
  if (!confirmed) return;
  showOverlay('A copiar documento origem...');
  try {
    const response = await fetch(`/api/faturacao/ft/${encodeURIComponent(ftStamp)}/copy-from`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        origem_ftstamp: origemPickStamp,
        no: currentClientNo(),
        dest_header: serializeHeaderForSave(header),
      })
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok || data.error) {
      alertMessage(data.error || 'Não foi possível copiar o documento origem.');
      return;
    }
    origemModal?.hide();
    await loadDoc();
    alertMessage(data.message || 'Documento copiado com sucesso.');
  } finally {
    hideOverlay();
  }
}

function validateNcHeader() {
  if (!isCurrentNcDoc()) return '';
  if (!String(header.FTSTAMP_ORIGEM || '').trim()) {
    return 'A nota de crÃ©dito tem de indicar um documento de venda de origem.';
  }
  if (!String(header.MOTIVO_REFERENCIA || '').trim()) {
    return 'Indique o motivo da nota de crÃ©dito.';
  }
  const invalidLines = lines.filter((line) => isMeaningfulLine(line) && !String(line.FISTAMP_ORIGEM || '').trim());
  if (invalidLines.length) {
    return 'A nota de crÃ©dito nÃ£o pode ter linhas sem correspondÃªncia no documento de origem.';
  }
  return '';
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
  const currencyCtx = getCalcCurrencyContext();
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
      EPV: formatCalcMoneyCell(detail.epvScaled, currencyCtx, 2, 6),
      DESCONTO_LINHA: formatScaled(detail.descontoLinhaPctScaled, 2),
      TOTAL_LINHA: formatCalcMoneyCell(detail.totalAposDescLinhaScaled, currencyCtx, 6, 6),
      DESCONTO_CAB: formatScaled(detail.descontoCabecalhoPctScaled, 2),
      TOTAL_APOS_CAB: formatCalcMoneyCell(detail.totalLiquidoScaled, currencyCtx, 6, 6),
      TAXA_IVA: formatScaled(detail.ivaRateScaled, 2),
      IVA_LINHA: formatCalcMoneyCell(detail.ivaLinhaScaled, currencyCtx, 2, 2)
    });
  });

  const totalVatScaled = totalVatCents * 10000n;
  const totalDocScaled = totalBaseScaled + totalVatScaled;
  let cambioLabel = `1 EUR = ${formatScaled(SCALE, 6)} EUR`;
  if (currencyCtx.code !== 'EUR') {
    cambioLabel = currencyCtx.hasEuroConversion
      ? `1 EUR = ${formatScaled(parseScaled(currencyCtx.cambioText), 6)} ${currencyCtx.code}`
      : `Câmbio manual (${currencyCtx.code})`;
  }

  return {
    no: displayValue(header.NO),
    nome: displayValue(header.NOME),
    nif: displayValue(header.NCONT),
    morada: displayValue([header.MORADA, header.CODPOST, header.LOCAL].filter(Boolean).join(', ')),
    moeda: currencyCtx.code,
    cambio: cambioLabel,
    lines: detailLines,
    breakdown: Array.from(breakdown.values()).map((row) => ({
      label: row.label,
      base: formatCalcMoneyCell(row.baseScaled, currencyCtx, 2, 2),
      iva: formatCalcMoneyCell(row.ivaCents * 10000n, currencyCtx, 2, 2)
    })),
    totalBase: formatCalcMoneyCell(totalBaseScaled, currencyCtx, 2, 2),
    totalVat: formatCalcMoneyCell(totalVatScaled, currencyCtx, 2, 2),
    totalDoc: formatCalcMoneyCell(totalDocScaled, currencyCtx, 2, 2)
  };
}

function renderCalcModal() {
  const snapshot = computeCalcSnapshot();
  if (calcNoEl) calcNoEl.textContent = snapshot.no;
  if (calcNomeEl) calcNomeEl.textContent = snapshot.nome;
  if (calcNifEl) calcNifEl.textContent = snapshot.nif;
  if (calcMoradaEl) calcMoradaEl.textContent = snapshot.morada;
  if (calcMoedaEl) calcMoedaEl.textContent = snapshot.moeda;
  if (calcCambioEl) calcCambioEl.textContent = snapshot.cambio;

  if (calcLinesBody) {
    if (!snapshot.lines.length) {
      calcLinesBody.innerHTML = '<tr><td colspan="10" class="sz_text_muted">Sem linhas.</td></tr>';
    } else {
      calcLinesBody.innerHTML = snapshot.lines.map((row) => `
        <tr>
          <td>${esc(row.REF || '—')}</td>
          <td>${esc(row.DESIGN || '—')}</td>
          <td class="sz_text_right">${row.QTT}</td>
          <td class="sz_text_right">${row.EPV.html}</td>
          <td class="sz_text_right">${row.DESCONTO_LINHA}</td>
          <td class="sz_text_right">${row.TOTAL_LINHA.html}</td>
          <td class="sz_text_right">${row.DESCONTO_CAB}</td>
          <td class="sz_text_right">${row.TOTAL_APOS_CAB.html}</td>
          <td class="sz_text_right">${row.TAXA_IVA}</td>
          <td class="sz_text_right">${row.IVA_LINHA.html}</td>
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
          <td class="sz_text_right">${row.base.html}</td>
          <td class="sz_text_right">${row.iva.html}</td>
        </tr>
      `).join('');
    }
  }

  if (calcBaseEl) calcBaseEl.innerHTML = snapshot.totalBase.html;
  if (calcVatEl) calcVatEl.innerHTML = snapshot.totalVat.html;
  if (calcTotalEl) calcTotalEl.innerHTML = snapshot.totalDoc.html;
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
  const transportOnlyEditable = isTransportTransportOnlyPhase();
  const transportPrinted = isCurrentTransportDoc() && currentTransportState() === 'IMPRESSO';
  isBlocked = anulada || transportPrinted || (Number(header.BLOQUEADO || 0) === 1 && !transportOnlyEditable);
  const fiscalLocked = isBlocked || transportOnlyEditable;
  const transportDisabled = !isCurrentTransportDoc() || isBlocked;

  [ndocSel, fdataInput, pdataInput, ccustoSel, descontoInput, moedaInput, cambioInput, clientDetailBtn, addLineBtn, btnCopiarOrigem].forEach((element) => {
    if (element) element.disabled = fiscalLocked;
  });
  if (nomeInput) {
    nomeInput.disabled = fiscalLocked;
    nomeInput.readOnly = isCurrentFsDoc();
  }
  if (fiscalLocked || isCurrentFsDoc()) {
    renderClientSuggestions([]);
  }
  if (addLineBtn && (isCurrentNcDoc() || transportOnlyEditable)) addLineBtn.disabled = true;
  if (motivoReferenciaInput) motivoReferenciaInput.disabled = fiscalLocked || !isCurrentNcDoc();
  if (clienteApplyBtn) clienteApplyBtn.disabled = fiscalLocked;
  [localCargaSel, localDescargaSel, dataHoraInicioTransporteInput, matriculaInput, codigoAtInput].forEach((element) => {
    if (element) element.disabled = transportDisabled;
  });

  if (btnGuardar) btnGuardar.disabled = isBlocked;
  if (btnEmitir) btnEmitir.disabled = isBlocked || emitida;
  if (btnAnular) btnAnular.disabled = anulada || !emitida || transportPrinted;
  updateTransportUi();
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
  header.MOEDA = currencyCode(header.MOEDA || 'EUR') || 'EUR';
  header.CAMBIO = currencyCambioValue(header.MOEDA, header.CAMBIO);
  header.FDATA = safeDate(header.FDATA);
  header.PDATA = safeDate(header.PDATA || header.FDATA);
  lines = Array.isArray(data.lines) ? data.lines.map((line, index) => normalizeLine(line, index)) : [];
  await loadFts();
  await loadTransportLocais();
  mapHeaderToUi();
  if (isCurrentFsDoc() && n(header.NO, 0) <= 0 && !String(header.NOME || '').trim()) {
    await applyFsConfiguredClient(true);
  }
  renderLines();
  updateEditableState();
}

async function saveDoc(redirectAfter = true, reloadAfter = true) {
  if (isBlocked) return false;
  mapUiToHeader();
  recalcAll();
  const fsHeaderError = validateFsHeader();
  if (fsHeaderError) {
    alertMessage(fsHeaderError);
    return false;
  }
  const ncHeaderError = validateNcHeader();
  if (ncHeaderError) {
    alertMessage(ncHeaderError);
    return false;
  }
  const miseimpError = validateMiseimpLines();
  if (miseimpError) {
    alertMessage(miseimpError);
    return false;
  }
  const payload = {
    header: serializeHeaderForSave(header),
    lines: lines.map((line) => serializeLineForSave(line))
  };
  const response = await fetch(`/api/faturacao/ft/${encodeURIComponent(ftStamp)}/save`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
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

async function imprimirDoc(showValues = true) {
  if (!isCurrentTransportDoc()) {
    openNewTab(`/api/faturacao/ft/${encodeURIComponent(ftStamp)}/pdf?force_html=1&_ts=${Date.now()}`);
    return;
  }
  const transportState = currentTransportState();
  if (transportState === 'IMPRESSO') {
    openNewTab(`/api/faturacao/ft/${encodeURIComponent(ftStamp)}/pdf?final=1&show_values=${showValues ? '1' : '0'}&_ts=${Date.now()}`);
    return;
  }
  const validationError = validateTransportForFinalPrint();
  if (validationError) {
    alertMessage(validationError);
    return;
  }
  showOverlay('A preparar documento de transporte...');
  try {
    const saved = await saveDoc(false, true);
    if (!saved) return;
    openNewTab(`/api/faturacao/ft/${encodeURIComponent(ftStamp)}/pdf?final=1&show_values=${showValues ? '1' : '0'}&_ts=${Date.now()}`);
    window.setTimeout(() => {
      loadDoc().catch(() => {});
    }, 1200);
  } finally {
    hideOverlay();
  }
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
  if (isTransportTransportOnlyPhase()) {
    alertMessage('Depois de emitido, o documento de transporte só permite editar os dados de transporte.');
    return;
  }
  if (isCurrentNcDoc()) {
    alertMessage('As linhas da nota de crÃ©dito tÃªm de vir do documento de origem.');
    return;
  }
  const line = normalizeLine({
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
  }, lines.length);
  const insertIndex = resolveNewLineInsertIndex();
  lines.splice(insertIndex, 0, line);
  normalizeLineOrder(true);
  lastLineCursorRowId = line.FISTAMP;
  renderLines();
  recalcAll();
  focusLineField(line.FISTAMP);
}

function getLineByRow(target) {
  const rowEl = target.closest('tr[data-id]');
  if (!rowEl) return null;
  return lines.find((line) => line.FISTAMP === rowEl.dataset.id) || null;
}

linesBody?.addEventListener('focusin', (event) => {
  const rowEl = event.target.closest('tr[data-id]');
  if (!rowEl) return;
  lastLineCursorRowId = String(rowEl.dataset.id || '').trim() || null;
});

linesBody?.addEventListener('click', async (event) => {
  const actionEl = event.target.closest('[data-a]');
  if (!actionEl) return;
  const row = getLineByRow(actionEl);
  if (!row) return;
  const isCreditOriginLine = isCurrentNcDoc() && Boolean(String(row.FISTAMP_ORIGEM || '').trim());

  if (actionEl.dataset.a === 'choose_ref') {
    if (isCreditOriginLine) {
      alertMessage('A linha da nota de crÃ©dito tem de manter a referÃªncia da linha de origem.');
      return;
    }
    artigoPickRowId = row.FISTAMP;
    if (artigoSearchInput) artigoSearchInput.value = '';
    await loadArtigoRows('');
    artigoModal?.show();
    return;
  }

  if (actionEl.dataset.a === 'miseimp') {
    if (isCreditOriginLine) {
      alertMessage('O motivo de isenÃ§Ã£o tem de manter coerÃªncia com a linha de origem.');
      return;
    }
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

document.addEventListener('focusin', (event) => {
  const target = event.target;
  if (!(target instanceof Element)) return;
  if (target.closest('#ftLinesBody')) return;
  if (target.closest('#ftAddLinha')) return;
  lastLineCursorRowId = null;
});

document.addEventListener('pointerdown', (event) => {
  const target = event.target;
  if (!(target instanceof Element)) return;
  if (target.closest('#ftLinesBody')) return;
  if (target.closest('#ftAddLinha')) return;
  lastLineCursorRowId = null;
});

linesBody?.addEventListener('change', async (event) => {
  const fieldEl = event.target.closest('[data-f]');
  if (!fieldEl) return;
  const row = getLineByRow(fieldEl);
  if (!row) return;

  const field = fieldEl.dataset.f;
  const isCreditOriginLine = isCurrentNcDoc() && Boolean(String(row.FISTAMP_ORIGEM || '').trim());
  if (isCreditOriginLine && ['REF', 'DESIGN', 'UNIDADE', 'TABIVA', 'IVAINCL'].includes(field)) {
    renderLines();
    return;
  }
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

origemTableBody?.addEventListener('click', (event) => {
  const rowEl = event.target.closest('tr[data-origem-ftstamp]');
  if (!rowEl) return;
  origemPickStamp = String(rowEl.dataset.origemFtstamp || '').trim();
  renderOrigemRows();
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

moedaInput?.addEventListener('focus', async () => {
  try {
    await searchCurrencyOptions(moedaInput.value || '');
  } catch (error) {
    hideCurrencySuggestions();
    alertMessage(error?.message || 'Não foi possível carregar as moedas.');
  }
});

moedaInput?.addEventListener('input', () => {
  if (isBlocked) return;
  moedaInput.value = currencyCode(moedaInput.value || '');
  if (currencyTimer) clearTimeout(currencyTimer);
  currencyTimer = setTimeout(async () => {
    try {
      await searchCurrencyOptions(moedaInput.value || '');
    } catch (error) {
      hideCurrencySuggestions();
      alertMessage(error?.message || 'Não foi possível carregar as moedas.');
    }
  }, 120);
});

moedaInput?.addEventListener('keydown', (event) => {
  if (event.key === 'Escape') {
    hideCurrencySuggestions();
    return;
  }
  if (event.key === 'Enter') {
    event.preventDefault();
    resolveCurrencyInput();
  }
});

moedaInput?.addEventListener('blur', () => {
  setTimeout(() => {
    resolveCurrencyInput();
  }, 180);
});

cambioInput?.addEventListener('input', () => {
  if (isBlocked) return;
  header.CAMBIO = currencyCambioValue(header.MOEDA, cambioInput.value || '');
});

cambioInput?.addEventListener('blur', () => {
  if (isBlocked) return;
  header.CAMBIO = currencyCambioValue(header.MOEDA, cambioInput.value || '');
  syncCurrencyInputsFromHeader();
});

clientDetailBtn?.addEventListener('click', openClientDetail);
clienteApplyBtn?.addEventListener('click', applyClientModalToHeader);
btnCalc?.addEventListener('click', openCalcModal);
btnCopiarOrigem?.addEventListener('click', openCopyOrigemModal);
localCargaSel?.addEventListener('change', () => {
  header.LOCAL_CARGA_ID = String(localCargaSel.value || '').trim();
  updateTransportUi();
});
localDescargaSel?.addEventListener('change', () => {
  header.LOCAL_DESCARGA_ID = String(localDescargaSel.value || '').trim();
  updateTransportUi();
});
dataHoraInicioTransporteInput?.addEventListener('change', () => {
  header.DATA_HORA_INICIO_TRANSPORTE = String(dataHoraInicioTransporteInput.value || '').trim();
  updateTransportUi();
});
matriculaInput?.addEventListener('input', () => {
  header.MATRICULA = String(matriculaInput.value || '').trim();
});
codigoAtInput?.addEventListener('input', () => {
  header.CODIGO_AT = String(codigoAtInput.value || '').trim();
});

ndocSel?.addEventListener('change', async () => {
  const previousDocType = currentDocType();
  header.NDOC = n(ndocSel.value, 0);
  syncSeriesFromHeader();
  updateOrigemUi();
  await loadTransportLocais();
  updateEditableState();
  if (currentDocType() === 'FS' && previousDocType !== 'FS') {
    const applied = await applyFsConfiguredClient(true);
    if (!applied) return;
  }
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
  await loadTransportLocais();
  updateEditableState();
});

btnGuardar?.addEventListener('click', () => { saveDoc(true, true); });
btnEmitir?.addEventListener('click', emitirDoc);
btnCancelar?.addEventListener('click', cancelarDoc);
btnAnular?.addEventListener('click', anularDoc);
btnDuplicar?.addEventListener('click', duplicarDoc);
btnImprimir?.addEventListener('click', () => { imprimirDoc(true); });
btnImprimirSemValores?.addEventListener('click', () => { imprimirDoc(false); });
btnVerHtml?.addEventListener('click', verHtmlDoc);
addLineBtn?.addEventListener('click', newLine);
origemIncludeUsed?.addEventListener('change', () => {
  loadOrigemRows().catch((error) => {
    alertMessage(error?.message || 'Não foi possível carregar os documentos origem.');
  });
});
origemConfirmBtn?.addEventListener('click', copyFromSelectedOrigem);
motivoReferenciaInput?.addEventListener('input', () => {
  header.MOTIVO_REFERENCIA = String(motivoReferenciaInput.value || '').trim();
});

miseimpModalEl?.addEventListener('hidden.bs.modal', () => {
  miseimpPickRowId = null;
});

artigoModalEl?.addEventListener('hidden.bs.modal', () => {
  artigoPickRowId = null;
});

origemModalEl?.addEventListener('hidden.bs.modal', () => {
  origemPickStamp = '';
  origemRows = [];
  if (origemIncludeUsed) origemIncludeUsed.checked = false;
  renderOrigemRows();
});

showOverlay('A carregar...');
try {
  await Promise.all([
    loadCcustoOptions(),
    loadTaxaOptions(),
    loadMiseimpOptions(),
    ensureCurrencyOptions().catch(() => [])
  ]);
  await loadDoc();
} finally {
  hideOverlay();
}
