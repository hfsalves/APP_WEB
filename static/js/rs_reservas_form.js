const rsStamp = String(window.RS_STAMP || '').trim();
const returnUrl = String(window.RS_RETURN_TO || '/generic/view/RS/').trim() || '/generic/view/RS/';

function showReservationToast(message, type = 'success', options = {}) {
  if (typeof window.showToast === 'function') {
    window.showToast(message, type, options);
    return;
  }
  window.alert(message);
}

function queueReservationToast(message, type = 'success', options = {}) {
  if (typeof window.queueToastOnNextPage === 'function') {
    window.queueToastOnNextPage(message, type, options);
  }
}

async function showReservationMessage(message, title = 'Reserva') {
  const text = String(message || '').trim();
  if (!text) return;
  if (typeof window.szAlert === 'function') {
    await window.szAlert(text, { title });
    return;
  }
  window.alert(text);
}

const overlay = document.getElementById('loadingOverlay');
const overlayText = overlay?.querySelector('.loading-text');
const titleEl = document.getElementById('rsTitulo');
const guestsBody = document.getElementById('rsGuestsBody');
const guestsStatusEl = document.getElementById('rsGuestsStatus');
const openPublicLinkBtn = document.getElementById('rsOpenPublicLink');
const copyPublicLinkBtn = document.getElementById('rsCopyPublicLink');
const sibaCommunicateBtn = document.getElementById('rsSibaCommunicateBtn');
const sibaStatusEl = document.getElementById('rsSibaStatus');
const alojamentoList = document.getElementById('RS_ALOJAMENTO_LIST');
const origemList = document.getElementById('RS_ORIGEM_LIST');
const cancelFieldsWrap = document.getElementById('rsCancelFields');
const cleaningBeforeEl = document.getElementById('rsCleaningBefore');
const cleaningAfterEl = document.getElementById('rsCleaningAfter');

const guestModalEl = document.getElementById('rsGuestModal');
const guestModal = guestModalEl && window.bootstrap?.Modal ? new window.bootstrap.Modal(guestModalEl) : null;
const guestModalTitle = document.getElementById('rsGuestModalTitle');
const guestSaveBtn = document.getElementById('rsGuestSaveBtn');
const guestDeleteBtn = document.getElementById('rsGuestDeleteBtn');
const billingBody = document.getElementById('rsBillingBody');
const addBillingBtn = document.getElementById('rsAddBilling');
const billingModalEl = document.getElementById('rsBillingModal');
const billingModal = billingModalEl && window.bootstrap?.Modal ? new window.bootstrap.Modal(billingModalEl) : null;
const billingSaveBtn = document.getElementById('rsBillingSaveBtn');
const openGuestChatBtn = document.getElementById('rsOpenGuestChat');
const chatModalEl = document.getElementById('rsChatModal');
const chatModal = chatModalEl && window.bootstrap?.Modal ? new window.bootstrap.Modal(chatModalEl) : null;
const chatMetaEl = document.getElementById('rsChatMeta');
const chatBodyEl = document.getElementById('rsChatBody');
const chatRefreshBtn = document.getElementById('rsChatRefreshBtn');
const billingFieldIds = ['FTNOME', 'FTMORADA', 'FTLOCAL', 'FTCODPOST', 'FTNCONT', 'FTEMAIL'];
const billingInputMap = Object.fromEntries(billingFieldIds.map((name) => [name, document.getElementById(`RSB_${name}`)]));

const fieldIds = [
  'ALOJAMENTO', 'RDATA', 'ORIGEM', 'RESERVA', 'DATAIN', 'DATAOUT', 'HORAIN', 'HORAOUT', 'NOITES', 'NOME', 'PAIS',
  'ADULTOS', 'CRIANCAS', 'ESTADIA', 'LIMPEZA', 'COMISSAO', 'OBS',
  'READY', 'ENTROU', 'SAIU', 'ALERTA', 'CANCELADA', 'DTCANCEL', 'DIASCANCEL', 'NOTIF', 'NOTIF2', 'PCANCEL',
  'BERCO', 'SOFACAMA', 'RTOTAL', 'USRCHECKIN', 'PRESENCIAL', 'SEF', 'USRSEF', 'INSTR', 'USRINSTR',
  'FTNOME', 'FTMORADA', 'FTLOCAL', 'FTCODPOST', 'FTNCONT', 'FTEMAIL'
];
const inputMap = Object.fromEntries(fieldIds.map((name) => [name, document.getElementById(`RS_${name}`)]));

const guestFieldIds = [
  'NOME', 'APELIDO', 'DTNASC', 'NACIONALIDADE', 'PAIS_RESIDENCIA',
  'TIPO_DOC', 'NUM_DOC', 'PAIS_EMISSOR_DOC'
];
const guestInputMap = Object.fromEntries(guestFieldIds.map((name) => [name, document.getElementById(`RSG_${name}`)]));

const COUNTRY_PRIORITY_CODES = [
  'PT', 'ES', 'FR', 'GB', 'IE', 'DE', 'IT', 'NL', 'BE', 'CH', 'AT', 'LU',
  'US', 'CA', 'BR', 'MX', 'AO', 'MZ', 'CV'
];
const COUNTRY_ALL_CODES = [
  'AF', 'AX', 'AL', 'DZ', 'AS', 'AD', 'AO', 'AI', 'AQ', 'AG', 'AR', 'AM', 'AW', 'AU', 'AT', 'AZ',
  'BS', 'BH', 'BD', 'BB', 'BY', 'BE', 'BZ', 'BJ', 'BM', 'BT', 'BO', 'BQ', 'BA', 'BW', 'BV', 'BR', 'IO', 'BN', 'BG', 'BF', 'BI',
  'CV', 'KH', 'CM', 'CA', 'KY', 'CF', 'TD', 'CL', 'CN', 'CX', 'CC', 'CO', 'KM', 'CG', 'CD', 'CK', 'CR', 'CI', 'HR', 'CU', 'CW', 'CY', 'CZ',
  'DK', 'DJ', 'DM', 'DO', 'EC', 'EG', 'SV', 'GQ', 'ER', 'EE', 'SZ', 'ET',
  'FK', 'FO', 'FJ', 'FI', 'FR', 'GF', 'PF', 'TF',
  'GA', 'GM', 'GE', 'DE', 'GH', 'GI', 'GR', 'GL', 'GD', 'GP', 'GU', 'GT', 'GG', 'GN', 'GW', 'GY',
  'HT', 'HM', 'VA', 'HN', 'HK', 'HU',
  'IS', 'IN', 'ID', 'IR', 'IQ', 'IE', 'IM', 'IL', 'IT',
  'JM', 'JP', 'JE', 'JO',
  'KZ', 'KE', 'KI', 'KP', 'KR', 'KW', 'KG',
  'LA', 'LV', 'LB', 'LS', 'LR', 'LY', 'LI', 'LT', 'LU',
  'MO', 'MG', 'MW', 'MY', 'MV', 'ML', 'MT', 'MQ', 'MR', 'MU', 'YT', 'MX', 'FM', 'MD', 'MC', 'MN', 'ME', 'MS', 'MA', 'MZ', 'MM',
  'NA', 'NR', 'NP', 'NL', 'NC', 'NZ', 'NI', 'NE', 'NG', 'NU', 'NF', 'MK', 'MP', 'NO',
  'OM',
  'PK', 'PW', 'PS', 'PA', 'PG', 'PY', 'PE', 'PH', 'PN', 'PL', 'PT', 'PR',
  'QA',
  'RE', 'RO', 'RU', 'RW',
  'BL', 'SH', 'KN', 'LC', 'MF', 'PM', 'VC', 'WS', 'SM', 'ST', 'SA', 'SN', 'RS', 'SC', 'SL', 'SG', 'SX', 'SK', 'SI', 'SB', 'SO', 'ZA', 'GS', 'SS', 'ES', 'LK', 'SD', 'SR', 'SJ', 'SE', 'CH', 'SY',
  'TW', 'TJ', 'TZ', 'TH', 'TL', 'TG', 'TK', 'TO', 'TT', 'TN', 'TR', 'TM', 'TC', 'TV',
  'UG', 'UA', 'AE', 'GB', 'US', 'UM', 'UY', 'UZ',
  'VU', 'VE', 'VN', 'VG', 'VI',
  'WF', 'EH',
  'YE',
  'ZM', 'ZW',
  'XK'
];
const COUNTRY_CODE_LIST = [...new Set([...COUNTRY_PRIORITY_CODES, ...COUNTRY_ALL_CODES])];
const COUNTRY_CUSTOM_LABELS = { XK: 'Kosovo' };
const COUNTRY_DISPLAY_PT = typeof Intl !== 'undefined' && Intl.DisplayNames
  ? new Intl.DisplayNames(['pt-PT'], { type: 'region' })
  : null;

function countryOptionLabel(code) {
  const key = String(code || '').trim().toUpperCase();
  if (!key) return '';
  return COUNTRY_CUSTOM_LABELS[key] || COUNTRY_DISPLAY_PT?.of(key) || key;
}

const GUEST_COUNTRY_CODE_FIELDS = {
  NACIONALIDADE: 'NACIONALIDADE_ICAO',
  PAIS_RESIDENCIA: 'PAIS_RESIDENCIA_ICAO',
  PAIS_EMISSOR_DOC: 'PAIS_EMISSOR_DOC_ICAO',
};

let header = {};
let guests = [];
let config = { alojamentos: [], origens: [] };
let guestEditIndex = -1;
let chatRefreshRunning = false;

const n = (value, fallback = 0) => {
  if (typeof value === 'boolean') return value ? 1 : 0;
  const num = Number(String(value ?? '').replace(',', '.'));
  return Number.isFinite(num) ? num : fallback;
};

const safeDate = (value, fallback = '') => {
  const raw = String(value || '').trim();
  if (!raw) return fallback;
  return raw.slice(0, 10);
};

const dateInputValue = (value) => {
  const raw = String(value || '').trim();
  if (!raw) return '';
  const iso = /^(\d{4})-(\d{2})-(\d{2})/.exec(raw);
  if (iso) return `${iso[1]}-${iso[2]}-${iso[3]}`;
  const pt = /^(\d{1,2})[/-](\d{1,2})[/-](\d{4})/.exec(raw);
  if (pt) return `${pt[3]}-${String(pt[2]).padStart(2, '0')}-${String(pt[1]).padStart(2, '0')}`;
  return raw.slice(0, 10);
};

function showOverlay(message = 'A carregar...') {
  if (!overlay) return;
  if (overlayText) overlayText.textContent = message;
  overlay.style.display = 'flex';
  requestAnimationFrame(() => { overlay.style.opacity = '1'; });
}

function hideOverlay() {
  if (!overlay) return;
  overlay.style.opacity = '0';
  setTimeout(() => { overlay.style.display = 'none'; }, 180);
}

function fillDatalist(el, values) {
  if (!el) return;
  el.innerHTML = (values || [])
    .filter((x) => String(x || '').trim() !== '')
    .map((x) => `<option value="${String(x).replace(/"/g, '&quot;')}"></option>`)
    .join('');
}

function fillCountrySelect(el) {
  if (!el) return;
  const current = normalizeMojibake(el.value || '').trim();
  const values = [{ code: '', label: '' }].concat(
    COUNTRY_CODE_LIST
      .map((code) => ({ code, label: countryOptionLabel(code) }))
      .filter((country) => country.label)
  );
  const hasCurrent = current && values.some((country) => normalizeMojibake(country.label).trim() === current);
  if (current && !hasCurrent) values.push({ code: '', label: current });
  el.innerHTML = values.map((country) => {
    const normalized = normalizeMojibake(country.label).trim();
    const selected = normalized === current ? ' selected' : '';
    const label = normalized || '---';
    const value = normalized ? escapeHtml(normalized) : '';
    const code = String(country.code || '').trim().toUpperCase();
    const codeAttr = code ? ` data-code="${escapeHtml(code)}"` : '';
    return `<option value="${value}"${codeAttr}${selected}>${escapeHtml(label)}</option>`;
  }).join('');
}

function setSelectValuePreservingOption(el, value) {
  if (!el) return;
  const raw = String(value ?? '').trim();
  if (!raw) {
    el.value = '';
    return;
  }
  const exists = Array.from(el.options || []).some((opt) => String(opt.value || '').trim() === raw);
  if (!exists) {
    const option = document.createElement('option');
    option.value = raw;
    option.textContent = raw;
    el.appendChild(option);
  }
  el.value = raw;
}

function normalizeGuestDocType(value) {
  const raw = normalizeMojibake(value).trim();
  const key = raw
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toUpperCase();
  if (!key) return '';
  if (['ID_NACIONAL', 'ID', 'CC', 'BI', 'CARTAO DE CIDADAO', 'DOCUMENTO DE IDENTIFICACAO NACIONAL', 'DOC. IDENTIFICACAO NACIONAL', 'DOC. IDENTIFICACAO', 'NATIONAL IDENTITY DOCUMENT', 'NATIONAL ID', 'DOCUMENT NATIONAL DIDENTITE', 'DOCUMENTO NACIONAL DE IDENTIDAD'].includes(key)) {
    return 'Doc. Identificação Nacional';
  }
  if (['PASSAPORTE', 'PASSPORT'].includes(key)) return 'Passaporte';
  if (['OUTRO', 'OTHER', 'AUTRE'].includes(key)) return 'Outro';
  return raw;
}

function normalizeMojibake(value) {
  let out = String(value ?? '');
  if (!/[ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â‚¬Å¾Ã‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€šÃ‚Â ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¾Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â‚¬Å¾Ã‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€¦Ã‚Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â¦ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¡]/.test(out)) return out;
  for (let i = 0; i < 2; i += 1) {
    try {
      const fixed = decodeURIComponent(escape(out));
      if (fixed === out) break;
      out = fixed;
      if (!/[ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â‚¬Å¾Ã‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€šÃ‚Â ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¾Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â‚¬Å¾Ã‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€¦Ã‚Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â¦ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¡]/.test(out)) break;
    } catch (_) {
      break;
    }
  }
  return out;
}

function escapeHtml(value) {
  return String(value ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function updateTitle() {
  if (!titleEl) return;
  const ref = String(header.RESERVA || '').trim();
  const aloj = String(header.ALOJAMENTO || '').trim();
  titleEl.textContent = ref ? `Reserva ${ref}${aloj ? ` - ${aloj}` : ''}` : (aloj ? `Reserva - ${aloj}` : 'Reserva');
}

function toggleCancelFields() {
  if (!cancelFieldsWrap) return;
  cancelFieldsWrap.style.display = inputMap.CANCELADA?.checked ? '' : 'none';
}

function syncNights() {
  const datain = safeDate(inputMap.DATAIN?.value);
  const dataout = safeDate(inputMap.DATAOUT?.value);
  if (!datain || !dataout) return;
  const d1 = new Date(`${datain}T00:00:00`);
  const d2 = new Date(`${dataout}T00:00:00`);
  if (Number.isNaN(d1.getTime()) || Number.isNaN(d2.getTime())) return;
  const diff = Math.max(0, Math.round((d2 - d1) / 86400000));
  if (inputMap.NOITES) inputMap.NOITES.value = String(diff);
}

function readHeaderFromForm() {
  const out = {};
  fieldIds.forEach((name) => {
    const el = inputMap[name];
    if (!el) return;
    out[name] = el.type === 'checkbox' ? (el.checked ? 1 : 0) : (el.value ?? '');
  });
  return out;
}

function writeHeaderToForm() {
  fieldIds.forEach((name) => {
    const el = inputMap[name];
    if (!el) return;
    const value = header?.[name];
    if (el.type === 'checkbox') el.checked = n(value, 0) === 1;
    else el.value = value == null ? '' : value;
  });
  toggleCancelFields();
  updateTitle();
}

function defaultGuest() {
  return {
    RSGUESTSTAMP: '',
    NOME_COMPLETO: '',
    NOME: '',
    APELIDO: '',
    DTNASC: '',
    NACIONALIDADE: '',
    PAIS_RESIDENCIA: '',
    TIPO_DOC: '',
    NUM_DOC: '',
    PAIS_EMISSOR_DOC: '',
    HORAIN: '',
    HORAOUT: '',
    TRANSPORTE: '',
    VOO: '',
    BERCO: 0,
    ATIVO: 1,
  };
}

function guestFullName(guest) {
  return `${String(guest.NOME || '').trim()} ${String(guest.APELIDO || '').trim()}`.trim();
}

function expectedGuestCount() {
  return Math.max(0, n(header.ADULTOS, 0) + n(header.CRIANCAS, 0));
}

function isGuestComplete(guest) {
  const item = guest || {};
  return Boolean(
    guestFullName(item) &&
    String(item.DTNASC || '').trim() &&
    String(item.NACIONALIDADE || '').trim() &&
    String(item.TIPO_DOC || '').trim() &&
    String(item.NUM_DOC || '').trim() &&
    String(item.PAIS_EMISSOR_DOC || '').trim()
  );
}

function updateGuestsStatus() {
  if (!guestsStatusEl) return;
  const total = expectedGuestCount();
  const complete = (Array.isArray(guests) ? guests : []).filter(isGuestComplete).length;
  guestsStatusEl.textContent = `Completos ${complete}/${total}`;
}

function buildPublicGuideUrl() {
  const reservationCode = String(header.RESERVA || '').trim();
  if (!reservationCode) return '';
  return `https://szeroguests.com/r/${encodeURIComponent(reservationCode)}`;
}

function updatePublicLinkUi() {
  const url = buildPublicGuideUrl();
  if (openPublicLinkBtn) openPublicLinkBtn.disabled = !url;
  if (copyPublicLinkBtn) copyPublicLinkBtn.disabled = !url;
}

function updateChatUi() {
  const code = String(header.RESERVA || '').trim();
  if (openGuestChatBtn) openGuestChatBtn.disabled = !code;
}

function setSibaStatus(message, state = '') {
  if (!sibaStatusEl) return;
  sibaStatusEl.textContent = String(message || '').trim();
  sibaStatusEl.classList.toggle('is-ok', state === 'ok');
  sibaStatusEl.classList.toggle('is-warn', state === 'warn');
  sibaStatusEl.classList.toggle('is-error', state === 'error');
}

function updateSibaUi(message = '') {
  const communicated = n(header.SEF, 0) === 1;
  if (sibaCommunicateBtn) sibaCommunicateBtn.disabled = !rsStamp;
  if (message) {
    setSibaStatus(message, communicated ? 'ok' : 'warn');
    return;
  }
  if (communicated) {
    const user = String(header.USRSEF || '').trim();
    setSibaStatus(user ? `Comunicado por ${user}` : 'Comunicado', 'ok');
  } else {
    setSibaStatus('Por comunicar', '');
  }
}

function formatSibaMissing(missing) {
  const rows = Array.isArray(missing) ? missing : [];
  if (!rows.length) return '';
  return rows.map((item) => `- ${String(item || '').trim()}`).join('\n');
}

function billingHasData() {
  return billingFieldIds.some((name) => String(header?.[name] || '').trim() !== '');
}

function clearBillingData() {
  billingFieldIds.forEach((name) => {
    header[name] = '';
  });
}

function writeBillingToModal() {
  billingFieldIds.forEach((name) => {
    const el = billingInputMap[name];
    if (!el) return;
    el.value = header?.[name] == null ? '' : header[name];
  });
}

function readBillingFromModal() {
  const out = {};
  billingFieldIds.forEach((name) => {
    const el = billingInputMap[name];
    if (!el) return;
    out[name] = String(el.value || '').trim();
  });
  return out;
}

function openBillingModal() {
  writeBillingToModal();
  billingModal?.show();
}

function saveBillingModal() {
  header = { ...header, ...readBillingFromModal() };
  renderBillingCard();
  billingModal?.hide();
}

function deleteBillingData() {
  clearBillingData();
  renderBillingCard();
  billingModal?.hide();
}

function renderBillingCard() {
  if (!billingBody) return;
  if (addBillingBtn) addBillingBtn.style.display = billingHasData() ? 'none' : '';
  if (!billingHasData()) {
    billingBody.innerHTML = `<div class="rsf-empty-state p-3">Sem dados de fatura&ccedil;&atilde;o.</div>`;
    return;
  }

  billingBody.innerHTML = `
    <div class="rsf-billing-card" id="rsBillingCard">
      <div class="rsf-billing-card-head">
        <div class="rsf-billing-card-title">Dados de Fatura&ccedil;&atilde;o</div>
        <div class="d-flex gap-2">
          <button type="button" class="btn btn-outline-primary btn-sm" data-action="edit">Abrir</button>
          <button type="button" class="btn btn-outline-danger btn-sm" data-action="delete">Eliminar</button>
        </div>
      </div>
      <div class="rsf-billing-card-meta">
        <div><strong>${escapeHtml(header.FTNOME || 'Sem nome')}</strong></div>
        <div>${escapeHtml(header.FTMORADA || '')}</div>
        <div>${escapeHtml(header.FTCODPOST || '')}${header.FTCODPOST && header.FTLOCAL ? ' ' : ''}${escapeHtml(header.FTLOCAL || '')}</div>
        <div>${escapeHtml(header.FTNCONT || '')}${header.FTNCONT && header.FTEMAIL ? ' &middot; ' : ''}${escapeHtml(header.FTEMAIL || '')}</div>
      </div>
    </div>
  `;

  const card = document.getElementById('rsBillingCard');
  card?.addEventListener('click', openBillingModal);
  card?.querySelector('[data-action="edit"]')?.addEventListener('click', (ev) => {
    ev.preventDefault();
    ev.stopPropagation();
    openBillingModal();
  });
  card?.querySelector('[data-action="delete"]')?.addEventListener('click', (ev) => {
    ev.preventDefault();
    ev.stopPropagation();
    deleteBillingData();
  });
}

function writeGuestToModal(guest) {
  const current = guest || defaultGuest();
  guestFieldIds.forEach((name) => {
    const el = guestInputMap[name];
    if (!el) return;
    if (el.type === 'checkbox') {
      el.checked = n(current[name], name === 'ATIVO' ? 1 : 0) === 1;
    } else if (el.tagName === 'SELECT') {
      const value = name === 'TIPO_DOC'
        ? normalizeGuestDocType(current[name])
        : normalizeMojibake(current[name]);
      setSelectValuePreservingOption(el, value);
    } else if (name === 'DTNASC') {
      const value = dateInputValue(current[name]);
      el.value = value && value !== '1900-01-01' && value !== '0001-01-01' ? value : '';
    } else {
      el.value = current[name] == null ? '' : current[name];
    }
  });
}

function readGuestFromModal() {
  const current = guestEditIndex >= 0 && guests[guestEditIndex] ? { ...guests[guestEditIndex] } : defaultGuest();
  guestFieldIds.forEach((name) => {
    const el = guestInputMap[name];
    if (!el) return;
    current[name] = el.type === 'checkbox' ? (el.checked ? 1 : 0) : (el.value ?? '');
    const countryCodeField = GUEST_COUNTRY_CODE_FIELDS[name];
    if (countryCodeField) {
      const selected = el.options?.[el.selectedIndex];
      current[countryCodeField] = String(selected?.dataset?.code || '').trim();
    }
  });
  current.NOME_COMPLETO = guestFullName(current);
  return current;
}

function openGuestModal(index = -1) {
  guestEditIndex = index;
  const editing = index >= 0 && guests[index];
  if (guestModalTitle) guestModalTitle.textContent = editing ? `H\u00F3spede ${index + 1}` : 'Adicionar H\u00F3spede';
  if (guestDeleteBtn) guestDeleteBtn.style.display = editing ? '' : 'none';
  writeGuestToModal(editing ? guests[index] : defaultGuest());
  guestModal?.show();
}

function saveGuestModal() {
  const guest = readGuestFromModal();
  if (guestEditIndex >= 0 && guests[guestEditIndex]) guests[guestEditIndex] = guest;
  else guests.push(guest);
  renderGuests();
  guestModal?.hide();
}

function deleteGuestModal() {
  if (!(guestEditIndex >= 0 && guests[guestEditIndex])) return;
  guests.splice(guestEditIndex, 1);
  renderGuests();
  guestModal?.hide();
}

function renderGuests() {
  if (!guestsBody) return;
  updateGuestsStatus();
  if (!Array.isArray(guests) || !guests.length) {
    guestsBody.innerHTML = `<div class="rsf-empty-state p-3">Completos 0/${expectedGuestCount()}</div>`;
    return;
  }

  guestsBody.innerHTML = guests.map((guest, index) => `
    <div class="rsf-guest-card" data-idx="${index}">
      <div class="rsf-guest-card-head">
        <div class="rsf-guest-card-title">H\u00F3spede ${index + 1}</div>
        <button type="button" class="btn btn-outline-primary btn-sm" data-action="edit">Abrir</button>
      </div>
      <div class="rsf-guest-card-meta">
        <div><strong>${escapeHtml(guestFullName(guest) || 'Sem nome')}</strong></div>
        <div>${escapeHtml(guest.NACIONALIDADE || '')}${guest.NACIONALIDADE && guest.NUM_DOC ? ' &middot; ' : ''}${escapeHtml(guest.NUM_DOC || '')}</div>
        <div>${escapeHtml(guest.TIPO_DOC || '')}${guest.TIPO_DOC && guest.PAIS_EMISSOR_DOC ? ' &middot; ' : ''}${escapeHtml(guest.PAIS_EMISSOR_DOC || '')}</div>
        <div>${escapeHtml(guest.PAIS_RESIDENCIA || '')}</div>
      </div>
    </div>
  `).join('');

  guestsBody.querySelectorAll('.rsf-guest-card[data-idx]').forEach((card) => {
    const idx = n(card.getAttribute('data-idx'), -1);
    if (idx < 0 || !guests[idx]) return;
    card.addEventListener('click', () => openGuestModal(idx));
    card.querySelector('[data-action="edit"]')?.addEventListener('click', (ev) => {
      ev.preventDefault();
      ev.stopPropagation();
      openGuestModal(idx);
    });
  });
}

function timeToMin(value) {
  const raw = String(value || '').trim();
  const m = /^(\d{1,2}):(\d{2})$/.exec(raw);
  if (!m) return null;
  const hh = Math.max(0, Math.min(23, Number(m[1])));
  const mm = Math.max(0, Math.min(59, Number(m[2])));
  return hh * 60 + mm;
}

function minToTime(total) {
  if (total == null || !Number.isFinite(total)) return '';
  let v = Math.round(total);
  if (v < 0) v = 0;
  const hh = Math.floor(v / 60);
  const mm = v % 60;
  return `${String(hh).padStart(2, '0')}:${String(mm).padStart(2, '0')}`;
}

function formatDuration(total) {
  const mins = Number(total);
  if (!Number.isFinite(mins) || mins <= 0) return '--';
  if (mins < 60) return `${mins}m`;
  const hh = Math.floor(mins / 60);
  const mm = mins % 60;
  if (!mm) return `${hh}h`;
  return `${hh}h${String(mm).padStart(2, '0')}`;
}

function formatDatePt(value) {
  const raw = String(value || '').trim();
  if (!raw) return '';
  const bits = raw.slice(0, 10).split('-');
  if (bits.length !== 3) return raw;
  return `${bits[2]}/${bits[1]}/${bits[0]}`;
}

function formatDateTime(value) {
  const raw = String(value || '').trim();
  if (!raw) return '';
  const d = new Date(raw);
  if (!Number.isNaN(d.getTime())) {
    try {
      return new Intl.DateTimeFormat('pt-PT', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      }).format(d);
    } catch (_) {
      return raw;
    }
  }
  return raw;
}

function isImageType(ext) {
  return /^(png|jpg|jpeg|gif|webp)$/i.test(String(ext || ''));
}

function isVideoType(ext) {
  return /^(mp4|webm|ogg|mov|m4v)$/i.test(String(ext || ''));
}

function renderCleaningCard(container, task) {
  if (!container) return;
  if (!task) {
    container.innerHTML = `<div class="rsf-clean-card-empty">Sem limpeza associada.</div>`;
    return;
  }

  const plannedStart = String(task.HORA || '').trim();
  const plannedMins = n(task.PLANNED_MINUTES, 0);
  const plannedEnd = plannedStart && plannedMins > 0 ? minToTime((timeToMin(plannedStart) ?? 0) + plannedMins) : '';
  const plannedLabel = plannedStart
    ? `${escapeHtml(plannedStart)}${plannedEnd ? ` - ${escapeHtml(plannedEnd)}` : ''} &middot; ${escapeHtml(formatDuration(plannedMins))}`
    : (plannedMins > 0 ? escapeHtml(formatDuration(plannedMins)) : '--');
  const realStart = String(task.HORAINI || '').trim();
  const realEnd = String(task.HORAFIM || '').trim();
  const realDur = formatDuration(task.ACTUAL_MINUTES);
  const who = String(task.UTILIZADOR_NOME || task.UTILIZADOR || '').trim() || 'Sem equipa';
  const when = formatDatePt(task.DATA);
  const status = (() => {
    if (n(task.TRATADO, 0) === 1 || (realStart && realEnd)) {
      return { key: 'done', label: 'Conclu\u00EDda' };
    }
    const taskDate = String(task.DATA || '').trim();
    const plannedMin = timeToMin(plannedStart);
    if (taskDate) {
      const compare = new Date(`${taskDate}T${plannedStart || '00:00'}:00`);
      if (!Number.isNaN(compare.getTime())) {
        if (compare.getTime() < Date.now() && plannedMin != null) {
          return { key: 'late', label: 'Atrasada' };
        }
      }
    }
    return { key: 'todo', label: 'Planeada' };
  })();
  const realLabel = realStart || realEnd
    ? `${escapeHtml(realStart || '--:--')}${realEnd ? ` - ${escapeHtml(realEnd)}` : ''} &middot; ${escapeHtml(realDur)}`
    : '--';

  container.innerHTML = `
    <div class="rsf-clean-card" data-id="${escapeHtml(task.TAREFASSTAMP || '')}">
      <div class="rsf-clean-card-head">
        <div class="rsf-clean-card-who">${escapeHtml(who)}</div>
        <div class="d-flex align-items-center gap-2 flex-wrap justify-content-end">
          <span class="rsf-clean-status ${status.key}">${status.label}</span>
          <div class="rsf-clean-card-date">${escapeHtml(when || '--/--/----')}</div>
        </div>
      </div>
      <div class="rsf-clean-card-body">
        <div class="rsf-clean-card-split">
          <div class="rsf-clean-card-meta-box">
            <div class="rsf-clean-card-label">Planeado</div>
            <div class="rsf-clean-card-value">${plannedLabel}</div>
          </div>
          <div class="rsf-clean-card-meta-box">
            <div class="rsf-clean-card-label">Real</div>
            <div class="rsf-clean-card-value">${realLabel}</div>
          </div>
        </div>
      </div>
      <div class="rsf-clean-anexos js-clean-anexos">
        <div class="rsf-clean-anexos-empty">${task.TAREFASSTAMP ? 'A carregar anexos...' : 'Sem anexos.'}</div>
      </div>
    </div>
  `;
}

function renderCleaningAttachments(container, rows) {
  if (!container) return;
  if (!Array.isArray(rows) || !rows.length) {
    container.innerHTML = '<div class="rsf-clean-anexos-empty">Sem anexos.</div>';
    return;
  }
  container.innerHTML = rows.map((item) => {
    const url = String(item.CAMINHO || '').trim();
    const typ = String(item.TIPO || '').trim();
    const name = String(item.FICHEIRO || item.TIPO || '').trim();
    let media = '<div class="d-flex align-items-center justify-content-center h-100 text-muted"><i class="fa-regular fa-file-lines fa-lg"></i></div>';
    if (url && isImageType(typ)) media = `<img src="${escapeHtml(url)}" alt="">`;
    else if (url && isVideoType(typ)) media = `<video src="${escapeHtml(url)}" muted playsinline></video>`;
    const href = url ? `href="${escapeHtml(url)}" target="_blank" rel="noopener"` : '';
    return `
      <div class="rsf-clean-anexo" title="${escapeHtml(name)}">
        <a ${href} class="d-block h-100 w-100" style="text-decoration:none;color:inherit;">
          ${media}
        </a>
      </div>
    `;
  }).join('');
}

async function loadCleaningAttachments(taskId) {
  const id = String(taskId || '').trim();
  if (!id) return [];
  const resp = await fetch(`/api/anexos?table=TAREFAS&rec=${encodeURIComponent(id)}`);
  if (!resp.ok) throw new Error('Erro ao carregar anexos');
  const rows = await resp.json().catch(() => ([]));
  return Array.isArray(rows) ? rows : [];
}

async function loadCleaningInfo() {
  if (!cleaningBeforeEl || !cleaningAfterEl) return;
  cleaningBeforeEl.innerHTML = '<div class="text-muted p-3">A carregar...</div>';
  cleaningAfterEl.innerHTML = '<div class="text-muted p-3">A carregar...</div>';

  try {
    const resp = await fetch(`/api/reservas/rs/${encodeURIComponent(rsStamp)}/limpezas`);
    const data = await resp.json().catch(() => ({}));
    if (!resp.ok) throw new Error(data.error || 'Erro ao carregar limpezas');

    const before = data.before || null;
    const after = data.after || null;

    renderCleaningCard(cleaningBeforeEl, before);
    renderCleaningCard(cleaningAfterEl, after);

    await Promise.all([
      (async () => {
        if (!before?.TAREFASSTAMP) return;
        try {
          const rows = await loadCleaningAttachments(before.TAREFASSTAMP);
          renderCleaningAttachments(cleaningBeforeEl.querySelector('.js-clean-anexos'), rows);
        } catch (_) {
          renderCleaningAttachments(cleaningBeforeEl.querySelector('.js-clean-anexos'), []);
        }
      })(),
      (async () => {
        if (!after?.TAREFASSTAMP) return;
        try {
          const rows = await loadCleaningAttachments(after.TAREFASSTAMP);
          renderCleaningAttachments(cleaningAfterEl.querySelector('.js-clean-anexos'), rows);
        } catch (_) {
          renderCleaningAttachments(cleaningAfterEl.querySelector('.js-clean-anexos'), []);
        }
      })(),
    ]);
  } catch (_) {
    cleaningBeforeEl.innerHTML = '<div class="rsf-clean-card-empty">Erro ao carregar.</div>';
    cleaningAfterEl.innerHTML = '<div class="rsf-clean-card-empty">Erro ao carregar.</div>';
  }
}

function renderChat(messages, reservationCode) {
  if (!chatBodyEl || !chatMetaEl) return;
  const list = Array.isArray(messages) ? messages : [];
  chatMetaEl.textContent = reservationCode
    ? `Reserva ${reservationCode} ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã¢â‚¬Â¦Ãƒâ€šÃ‚Â¡ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€¦Ã‚Â¡ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â· ${list.length} mensagem(ns)`
    : `${list.length} mensagem(ns)`;
  if (!list.length) {
    chatBodyEl.innerHTML = '<div class="rsf-chat-empty">Sem mensagens para esta reserva.</div>';
    return;
  }

  const sorted = [...list].sort((a, b) => {
    const da = new Date(String(a.created_at || ''));
    const db = new Date(String(b.created_at || ''));
    const va = Number.isNaN(da.getTime()) ? 0 : da.getTime();
    const vb = Number.isNaN(db.getTime()) ? 0 : db.getTime();
    return va - vb;
  });

  chatBodyEl.innerHTML = sorted.map((msg) => {
    const dir = String(msg.direction || '').toLowerCase() === 'host' ? 'host' : 'guest';
    const sender = String(msg.sender_name || '').trim() || (dir === 'host' ? 'NÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â³s' : 'HÃƒÆ’Ã‚Â³spede');
    const textMsg = String(msg.text || '').trim() || '(sem texto)';
    const timeTxt = formatDateTime(msg.created_at || '');
    return `
      <div class="rsf-chat-row ${dir}">
        <div class="rsf-chat-bubble">
          <div class="rsf-chat-sender">${escapeHtml(sender)}</div>
          <div class="rsf-chat-text">${escapeHtml(textMsg)}</div>
          <div class="rsf-chat-time">${escapeHtml(timeTxt || '')}</div>
        </div>
      </div>
    `;
  }).join('');
  requestAnimationFrame(() => {
    chatBodyEl.scrollTop = chatBodyEl.scrollHeight;
  });
}

async function _openGuestChatModalLegacy() {
  if (!chatModal || !chatMetaEl || !chatBodyEl) return;
  chatMetaEl.textContent = 'A carregar...';
  chatBodyEl.innerHTML = '<div class="rsf-chat-empty">A carregar mensagens...</div>';
  chatModal.show();

  try {
    const resp = await fetch(`/api/reservas/rs/${encodeURIComponent(rsStamp)}/chat`);
    const data = await resp.json().catch(() => ({}));
    if (!resp.ok) throw new Error(data.error || 'Erro ao carregar chat');
    renderChat(data.messages || [], data.reservation_code || '');
  } catch (err) {
    chatMetaEl.textContent = 'Chat do HÃƒÆ’Ã‚Â³spede';
    chatBodyEl.innerHTML = `<div class="rsf-chat-empty text-danger">${escapeHtml(err.message || 'Erro ao carregar chat')}</div>`;
  }
}

function chatErrorMessage(status, payload, fallback = 'Erro ao carregar chat') {
  const msg = String((payload && (payload.error || payload.message)) || '').trim();
  if (status === 401 || status === 403) return msg || 'Token invÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¡lido para integraÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â§ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â£o do chat.';
  if (status === 404) return msg || 'Chat/reserva ainda nÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â£o importados.';
  if (status === 503) return msg || 'sync_engine temporariamente indisponÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â­vel.';
  return msg || fallback;
}

function setChatRefreshing(on, label = '') {
  chatRefreshRunning = !!on;
  if (chatRefreshBtn) {
    chatRefreshBtn.disabled = chatRefreshRunning;
    chatRefreshBtn.innerHTML = chatRefreshRunning
      ? '<i class="fa-solid fa-spinner fa-spin me-1"></i> A atualizar...'
      : '<i class="fa-solid fa-rotate me-1"></i> Atualizar Chat';
  }
  if (label && chatMetaEl) chatMetaEl.textContent = label;
}

async function loadGuestChatMessages(showLoading = true) {
  if (!chatMetaEl || !chatBodyEl) return { reservation_code: '', messages: [] };
  if (showLoading) {
    chatMetaEl.textContent = 'A carregar...';
    chatBodyEl.innerHTML = '<div class="rsf-chat-empty">A carregar mensagens...</div>';
  }
  const resp = await fetch(`/api/reservas/rs/${encodeURIComponent(rsStamp)}/chat`);
  const data = await resp.json().catch(() => ({}));
  if (!resp.ok) {
    const err = new Error(chatErrorMessage(resp.status, data, 'Erro ao carregar chat'));
    err.status = resp.status;
    throw err;
  }
  renderChat(data.messages || [], data.reservation_code || '');
  return data;
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function normalizeJobStatus(job) {
  return String((job && (job.status || job.state)) || '').trim().toLowerCase();
}

function formatJobFailure(job) {
  const parts = [];
  const msg = String((job && (job.error_message || job.error || job.message)) || '').trim();
  const stdoutTail = String((job && job.stdout_tail) || '').trim();
  const stderrTail = String((job && job.stderr_tail) || '').trim();
  if (msg) parts.push(msg);
  if (stdoutTail) parts.push(`stdout: ${stdoutTail}`);
  if (stderrTail) parts.push(`stderr: ${stderrTail}`);
  return parts.join('\n');
}

async function pollChatRefreshJob(jobId) {
  const timeoutMs = 180000;
  const intervalMs = 2500;
  const startedAt = Date.now();

  while (Date.now() - startedAt < timeoutMs) {
    const resp = await fetch(`/api/reservas/rs/${encodeURIComponent(rsStamp)}/chat/refresh/jobs/${encodeURIComponent(jobId)}`);
    const data = await resp.json().catch(() => ({}));
    if (!resp.ok) throw new Error(chatErrorMessage(resp.status, data, 'Erro a consultar estado de atualizaÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â§ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â£o'));

    const job = (data && typeof data === 'object' ? data.job : null) || {};
    const status = normalizeJobStatus(job);
    if (chatMetaEl) chatMetaEl.textContent = `A atualizar chat... (${status || 'running'})`;

    if (status === 'success' || status === 'done' || status === 'completed') return job;
    if (status === 'failed' || status === 'error' || status === 'stopped' || status === 'cancelled' || status === 'canceled') {
      throw new Error(formatJobFailure(job) || 'AtualizaÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â§ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â£o de chat falhou.');
    }
    await sleep(intervalMs);
  }

  throw new Error('Timeout ao atualizar chat (180s).');
}

async function refreshGuestChat() {
  if (chatRefreshRunning || !chatMetaEl || !chatBodyEl) return;
  const reservationCode = String(header.RESERVA || '').trim();
  if (!reservationCode) {
    chatMetaEl.textContent = 'Chat do HÃƒÆ’Ã‚Â³spede';
    chatBodyEl.innerHTML = '<div class="rsf-chat-empty text-danger">Reserva sem cÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â‚¬Å¾Ã‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€šÃ‚Â ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¾Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€¦Ã‚Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€¦Ã‚Â¾ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â‚¬Å¾Ã‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€¦Ã‚Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â¦ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¡ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã¢â‚¬Â¦Ãƒâ€šÃ‚Â¡ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€¦Ã‚Â¡ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â³digo Airbnb.</div>';
    return;
  }

  try {
    setChatRefreshing(true, 'A atualizar chat...');
    const resp = await fetch(`/api/reservas/rs/${encodeURIComponent(rsStamp)}/chat/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
    });
    const data = await resp.json().catch(() => ({}));
    if (!resp.ok) throw new Error(chatErrorMessage(resp.status, data, 'Erro ao pedir atualizaÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â§ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â£o do chat'));

    const jobId = String((data && data.job && (data.job.job_id || data.job.id)) || '').trim();
    if (!jobId) throw new Error('Resposta de refresh sem job_id.');

    await pollChatRefreshJob(jobId);
    setChatRefreshing(true, 'Chat atualizado. A carregar mensagens...');
    await loadGuestChatMessages(false);
  } catch (err) {
    if (chatMetaEl) chatMetaEl.textContent = 'Falha ao atualizar chat';
    if (chatBodyEl && String(chatBodyEl.innerHTML || '').trim() === '') {
      chatBodyEl.innerHTML = '<div class="rsf-chat-empty">Sem mensagens.</div>';
    }
    chatBodyEl?.insertAdjacentHTML('beforeend', `<div class="rsf-chat-empty text-danger">${escapeHtml((err && err.message) || 'Erro ao atualizar chat')}</div>`);
  } finally {
    setChatRefreshing(false);
  }
}

async function openGuestChatModal() {
  if (!chatModal || !chatMetaEl || !chatBodyEl) return;
  chatModal.show();
  try {
    await loadGuestChatMessages(true);
  } catch (err) {
    const status = Number(err?.status || 0);
    const msg = String(err?.message || '');
    const shouldAutoRefresh = status === 404 || /nao importados|n.o importados|ainda/i.test(msg);
    if (shouldAutoRefresh) {
      chatMetaEl.textContent = 'Sem mensagens importadas. A iniciar atualizacao...';
      chatBodyEl.innerHTML = '<div class="rsf-chat-empty">A iniciar atualizacao do chat...</div>';
      await refreshGuestChat();
      return;
    }
    chatMetaEl.textContent = 'Chat do hospede';
    chatBodyEl.innerHTML = `<div class="rsf-chat-empty text-danger">${escapeHtml(msg || 'Erro ao carregar chat')}</div>`;
  }
}

async function loadConfig() {
  const resp = await fetch('/api/reservas/rs/config');
  if (!resp.ok) throw new Error('Erro ao carregar configuraÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â§ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â£o');
  config = await resp.json();
  fillDatalist(alojamentoList, config.alojamentos || []);
  fillDatalist(origemList, config.origens || []);
}

async function loadDocument() {
  const resp = await fetch(`/api/reservas/rs/${encodeURIComponent(rsStamp)}`);
  const data = await resp.json().catch(() => ({}));
  if (!resp.ok) throw new Error(data.error || 'Erro ao carregar reserva');
  header = data.header || {};
  guests = Array.isArray(data.guests) ? data.guests : [];
  writeHeaderToForm();
  updatePublicLinkUi();
  updateChatUi();
  updateSibaUi();
  renderBillingCard();
  renderGuests();
  await loadCleaningInfo();
}

async function saveDocument(options = {}) {
  const useOverlay = options.overlay !== false;
  const silent = options.silent === true;
  header = { ...header, ...readHeaderFromForm() };
  guests = (Array.isArray(guests) ? guests : []).map((guest) => ({
    ...guest,
    NOME_COMPLETO: guestFullName(guest),
  }));

  if (useOverlay) showOverlay('A gravar...');
  try {
    const resp = await fetch(`/api/reservas/rs/${encodeURIComponent(rsStamp)}/save`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ header, guests }),
    });
    const data = await resp.json().catch(() => ({}));
    if (!resp.ok) throw new Error(data.error || 'Erro ao gravar reserva');
    header = { ...header, ...readHeaderFromForm() };
    updateTitle();
    updateGuestsStatus();
    updatePublicLinkUi();
    updateChatUi();
    updateSibaUi();
    renderBillingCard();
    await loadCleaningInfo();
    if (!silent) showReservationToast('Reserva gravada.', 'success');
  } finally {
    if (useOverlay) hideOverlay();
  }
}

async function communicateSiba() {
  const confirmed = await (window.szConfirm?.(
    'Gravar a reserva e preparar a comunicacao AIMA/SEF?',
    { title: 'AIMA/SEF' }
  ) ?? Promise.resolve(window.confirm('Gravar a reserva e preparar a comunicacao AIMA/SEF?')));
  if (!confirmed) return;

  showOverlay('A gravar...');
  let overlayVisible = true;
  const closeSibaOverlay = async () => {
    if (!overlayVisible) return;
    overlayVisible = false;
    hideOverlay();
    await sleep(220);
  };
  if (sibaCommunicateBtn) sibaCommunicateBtn.disabled = true;
  try {
    await saveDocument({ silent: true, overlay: false });
    if (overlayText) overlayText.textContent = 'A validar dados AIMA/SEF...';

    const resp = await fetch(`/api/reservas/rs/${encodeURIComponent(rsStamp)}/siba/communicate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
    });
    const data = await resp.json().catch(() => ({}));

    if (!resp.ok) {
      const missing = formatSibaMissing(data.missing);
      const message = missing
        ? `${data.error || 'Existem dados em falta para comunicar.'}\n\n${missing}`
        : (data.error || 'Erro ao preparar comunicacao AIMA/SEF');
      setSibaStatus(data.error || 'Validacao AIMA/SEF falhou', 'error');
      await closeSibaOverlay();
      await showReservationMessage(message, 'AIMA/SEF');
      return;
    }

    if (data.header && typeof data.header === 'object') {
      header = { ...header, ...data.header };
      writeHeaderToForm();
    }
    updateSibaUi(data.message || 'Dados prontos para comunicacao AIMA/SEF.');
    await closeSibaOverlay();
    showReservationToast(data.message || 'Dados prontos para comunicacao AIMA/SEF.', data.sent ? 'success' : 'warning');
  } catch (err) {
    setSibaStatus(err.message || 'Erro AIMA/SEF', 'error');
    await closeSibaOverlay();
    showReservationToast(err.message || 'Erro ao preparar comunicacao AIMA/SEF', 'danger');
  } finally {
    if (sibaCommunicateBtn) sibaCommunicateBtn.disabled = !rsStamp;
    if (overlayVisible) hideOverlay();
  }
}

async function deleteDocument() {
  if (!(await (window.szConfirmDelete?.('Pretende eliminar esta reserva?') ?? Promise.resolve(window.confirm('Eliminar esta reserva?'))))) return;
  showOverlay('A eliminar...');
  try {
    const resp = await fetch(`/api/reservas/rs/${encodeURIComponent(rsStamp)}/delete`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
    });
    const data = await resp.json().catch(() => ({}));
    if (!resp.ok) throw new Error(data.error || 'Erro ao eliminar reserva');
    queueReservationToast('Reserva eliminada.', 'success');
    window.location.href = returnUrl;
  } catch (err) {
    hideOverlay();
    showReservationToast(err.message || 'Erro ao eliminar reserva', 'danger');
  }
}

function bindHeaderEvents() {
  ['DATAIN', 'DATAOUT'].forEach((key) => {
    inputMap[key]?.addEventListener('change', syncNights);
  });
  ['ADULTOS', 'CRIANCAS'].forEach((key) => {
    inputMap[key]?.addEventListener('input', updateGuestsStatus);
    inputMap[key]?.addEventListener('change', updateGuestsStatus);
  });
  inputMap.CANCELADA?.addEventListener('change', toggleCancelFields);
  inputMap.SEF?.addEventListener('change', () => {
    header = { ...header, SEF: inputMap.SEF.checked ? 1 : 0 };
    updateSibaUi();
  });
}

async function init() {
  try {
    showOverlay('A carregar...');
    bindHeaderEvents();

    document.getElementById('rsAddGuest')?.addEventListener('click', (ev) => {
      ev.preventDefault();
      openGuestModal(-1);
    });
    document.getElementById('rsAddBilling')?.addEventListener('click', (ev) => {
      ev.preventDefault();
      openBillingModal();
    });
    ['NACIONALIDADE', 'PAIS_RESIDENCIA', 'PAIS_EMISSOR_DOC'].forEach((name) => fillCountrySelect(guestInputMap[name]));
    guestSaveBtn?.addEventListener('click', saveGuestModal);
    guestDeleteBtn?.addEventListener('click', deleteGuestModal);
    billingSaveBtn?.addEventListener('click', saveBillingModal);
    openGuestChatBtn?.addEventListener('click', (ev) => {
      ev.preventDefault();
      openGuestChatModal();
    });
    sibaCommunicateBtn?.addEventListener('click', (ev) => {
      ev.preventDefault();
      communicateSiba();
    });
    chatRefreshBtn?.addEventListener('click', (ev) => {
      ev.preventDefault();
      refreshGuestChat();
    });
    openPublicLinkBtn?.addEventListener('click', () => {
      const url = buildPublicGuideUrl();
      if (url) window.open(url, '_blank', 'noopener');
    });
    copyPublicLinkBtn?.addEventListener('click', async () => {
      const url = buildPublicGuideUrl();
      if (!url) return;
      try {
        if (navigator.clipboard?.writeText) {
          await navigator.clipboard.writeText(url);
        } else {
          const tmp = document.createElement('textarea');
          tmp.value = url;
          tmp.setAttribute('readonly', '');
          tmp.style.position = 'absolute';
          tmp.style.left = '-9999px';
          document.body.appendChild(tmp);
          tmp.select();
          document.execCommand('copy');
          tmp.remove();
        }
      } catch (_) {
        showReservationToast('Erro ao copiar link', 'danger');
      }
    });

    document.getElementById('rsBtnSave')?.addEventListener('click', async () => {
      try {
        await saveDocument();
      } catch (err) {
        showReservationToast(err.message || 'Erro ao gravar reserva', 'danger');
      }
    });
    document.getElementById('rsBtnCancel')?.addEventListener('click', async () => {
      try {
        showOverlay('A carregar...');
        await loadDocument();
      } catch (err) {
        showReservationToast(err.message || 'Erro ao repor reserva', 'danger');
      } finally {
        hideOverlay();
      }
    });

    ['rsBtnDeleteBottom'].forEach((id) => {
      document.getElementById(id)?.addEventListener('click', deleteDocument);
    });

    await Promise.all([loadConfig(), loadDocument()]);
  } catch (err) {
    showReservationToast(err.message || 'Erro ao iniciar ecr? de reservas', 'danger');
  } finally {
    hideOverlay();
  }
}

init();
