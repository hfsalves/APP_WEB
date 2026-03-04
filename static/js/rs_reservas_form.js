const rsStamp = String(window.RS_STAMP || '').trim();
const returnUrl = String(window.RS_RETURN_TO || '/generic/view/RS/').trim() || '/generic/view/RS/';

const overlay = document.getElementById('loadingOverlay');
const overlayText = overlay?.querySelector('.loading-text');
const titleEl = document.getElementById('rsTitulo');
const guestsBody = document.getElementById('rsGuestsBody');
const guestsStatusEl = document.getElementById('rsGuestsStatus');
const openPublicLinkBtn = document.getElementById('rsOpenPublicLink');
const copyPublicLinkBtn = document.getElementById('rsCopyPublicLink');
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

const COUNTRY_OPTIONS = [
  '', 'Afeganistão', 'África do Sul', 'Albânia', 'Alemanha', 'Andorra', 'Angola', 'Antígua e Barbuda', 'Arábia Saudita',
  'Argélia', 'Argentina', 'Arménia', 'Austrália', 'Áustria', 'Azerbaijão', 'Bahamas', 'Bangladexe', 'Barbados', 'Barém',
  'Bélgica', 'Belize', 'Benim', 'Bielorrússia', 'Bolívia', 'Bósnia e Herzegovina', 'Botsuana', 'Brasil', 'Brunei',
  'Bulgária', 'Burquina Faso', 'Burúndi', 'Butão', 'Cabo Verde', 'Camarões', 'Camboja', 'Canadá', 'Catar',
  'Cazaquistão', 'Chade', 'Chile', 'China', 'Chipre', 'Colômbia', 'Comores', 'Congo', 'Coreia do Norte', 'Coreia do Sul',
  'Costa do Marfim', 'Costa Rica', 'Croácia', 'Cuba', 'Dinamarca', 'Domínica', 'Egito', 'El Salvador',
  'Emirados Árabes Unidos', 'Equador', 'Eritreia', 'Eslováquia', 'Eslovénia', 'Espanha', 'Estados Unidos', 'Estónia',
  'Essuatíni', 'Etiópia', 'Fiji', 'Filipinas', 'Finlândia', 'França', 'Gabão', 'Gâmbia', 'Gana', 'Geórgia', 'Granada',
  'Grécia', 'Guatemala', 'Guiana', 'Guiné', 'Guiné-Bissau', 'Guiné Equatorial', 'Haiti', 'Honduras', 'Hungria', 'Iémen',
  'Ilhas Marshall', 'Índia', 'Indonésia', 'Irão', 'Iraque', 'Irlanda', 'Islândia', 'Israel', 'Itália', 'Jamaica', 'Japão',
  'Jibuti', 'Jordânia', 'Kosovo', 'Kuwait', 'Laus', 'Lesoto', 'Letónia', 'Líbano', 'Libéria', 'Líbia', 'Listenstaine',
  'Lituânia', 'Luxemburgo', 'Macedónia do Norte', 'Madagáscar', 'Malásia', 'Maláui', 'Maldivas', 'Mali', 'Malta',
  'Marrocos', 'Maurícia', 'Mauritânia', 'México', 'Mianmar', 'Micronésia', 'Moçambique', 'Moldávia', 'Mónaco', 'Mongólia',
  'Montenegro', 'Namíbia', 'Nauru', 'Nepal', 'Nicarágua', 'Níger', 'Nigéria', 'Noruega', 'Nova Zelândia', 'Omã',
  'Países Baixos', 'Palau', 'Panamá', 'Papua-Nova Guiné', 'Paquistão', 'Paraguai', 'Peru', 'Polónia', 'Portugal', 'Quénia',
  'Quirguistão', 'Kiribati', 'Reino Unido', 'República Centro-Africana', 'República Checa', 'República Democrática do Congo',
  'República Dominicana', 'Roménia', 'Ruanda', 'Rússia', 'Salomão', 'Samoa', 'Santa Lúcia', 'São Cristóvão e Neves',
  'São Marinho', 'São Tomé e Príncipe', 'São Vicente e Granadinas', 'Seicheles', 'Senegal', 'Serra Leoa', 'Sérvia',
  'Singapura', 'Síria', 'Somália', 'Sri Lanca', 'Sudão', 'Sudão do Sul', 'Suécia', 'Suíça', 'Suriname', 'Tailândia',
  'Taiuã', 'Tajiquistão', 'Tanzânia', 'Timor-Leste', 'Togo', 'Tonga', 'Trindade e Tobago', 'Tunísia', 'Turcomenistão',
  'Turquia', 'Tuvalu', 'Ucrânia', 'Uganda', 'Uruguai', 'Usbequistão', 'Vanuatu', 'Vaticano', 'Venezuela', 'Vietname',
  'Zâmbia', 'Zimbabué'
];

let header = {};
let guests = [];
let config = { alojamentos: [], origens: [] };
let guestEditIndex = -1;

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
  const current = String(el.value || '').trim();
  el.innerHTML = COUNTRY_OPTIONS.map((country) => {
    const selected = country === current ? ' selected' : '';
    const label = country || '---';
    const value = country ? escapeHtml(country) : '';
    return `<option value="${value}"${selected}>${label}</option>`;
  }).join('');
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
  titleEl.textContent = ref ? `Reserva ${ref}${aloj ? ` · ${aloj}` : ''}` : (aloj ? `Reserva · ${aloj}` : 'Reserva');
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
  const token = String(header.GUIDE_TOKEN || '').trim();
  if (!token) return '';
  return `https://szeroguests.com/r/${encodeURIComponent(token)}`;
}

function updatePublicLinkUi() {
  const url = buildPublicGuideUrl();
  if (openPublicLinkBtn) openPublicLinkBtn.disabled = !url;
  if (copyPublicLinkBtn) copyPublicLinkBtn.disabled = !url;
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
    billingBody.innerHTML = `<div class="text-muted p-3">Sem dados de fatura&ccedil;&atilde;o.</div>`;
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
        <div>${escapeHtml(header.FTNCONT || '')}${header.FTNCONT && header.FTEMAIL ? ' · ' : ''}${escapeHtml(header.FTEMAIL || '')}</div>
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
  });
  current.NOME_COMPLETO = guestFullName(current);
  return current;
}

function openGuestModal(index = -1) {
  guestEditIndex = index;
  const editing = index >= 0 && guests[index];
  if (guestModalTitle) guestModalTitle.textContent = editing ? `Hóspede ${index + 1}` : 'Adicionar Hóspede';
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
    guestsBody.innerHTML = `<div class="text-muted p-3">Completos 0/${expectedGuestCount()}</div>`;
    return;
  }

  guestsBody.innerHTML = guests.map((guest, index) => `
    <div class="rsf-guest-card" data-idx="${index}">
      <div class="rsf-guest-card-head">
        <div class="rsf-guest-card-title">Hóspede ${index + 1}</div>
        <button type="button" class="btn btn-outline-primary btn-sm" data-action="edit">Abrir</button>
      </div>
      <div class="rsf-guest-card-meta">
        <div><strong>${escapeHtml(guestFullName(guest) || 'Sem nome')}</strong></div>
        <div>${escapeHtml(guest.NACIONALIDADE || '')}${guest.NACIONALIDADE && guest.NUM_DOC ? ' · ' : ''}${escapeHtml(guest.NUM_DOC || '')}</div>
        <div>${escapeHtml(guest.TIPO_DOC || '')}${guest.TIPO_DOC && guest.PAIS_EMISSOR_DOC ? ' · ' : ''}${escapeHtml(guest.PAIS_EMISSOR_DOC || '')}</div>
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
      return { key: 'done', label: 'Concluída' };
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

async function loadConfig() {
  const resp = await fetch('/api/reservas/rs/config');
  if (!resp.ok) throw new Error('Erro ao carregar configuração');
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
  renderBillingCard();
  renderGuests();
  await loadCleaningInfo();
}

async function saveDocument() {
  header = { ...header, ...readHeaderFromForm() };
  guests = (Array.isArray(guests) ? guests : []).map((guest) => ({
    ...guest,
    NOME_COMPLETO: guestFullName(guest),
  }));

  showOverlay('A gravar...');
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
    renderBillingCard();
    await loadCleaningInfo();
  } finally {
    hideOverlay();
  }
}

async function deleteDocument() {
  if (!window.confirm('Eliminar esta reserva?')) return;
  showOverlay('A eliminar...');
  try {
    const resp = await fetch(`/api/reservas/rs/${encodeURIComponent(rsStamp)}/delete`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
    });
    const data = await resp.json().catch(() => ({}));
    if (!resp.ok) throw new Error(data.error || 'Erro ao eliminar reserva');
    window.location.href = returnUrl;
  } catch (err) {
    hideOverlay();
    window.alert(err.message || 'Erro ao eliminar reserva');
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
        window.alert('Erro ao copiar link');
      }
    });

    document.getElementById('rsBtnSave')?.addEventListener('click', async () => {
      try {
        await saveDocument();
      } catch (err) {
        window.alert(err.message || 'Erro ao gravar reserva');
      }
    });
    document.getElementById('rsBtnCancel')?.addEventListener('click', async () => {
      try {
        showOverlay('A carregar...');
        await loadDocument();
      } catch (err) {
        window.alert(err.message || 'Erro ao repor reserva');
      } finally {
        hideOverlay();
      }
    });

    ['rsBtnDeleteBottom'].forEach((id) => {
      document.getElementById(id)?.addEventListener('click', deleteDocument);
    });

    await Promise.all([loadConfig(), loadDocument()]);
  } catch (err) {
    window.alert(err.message || 'Erro ao iniciar ecrã de reservas');
  } finally {
    hideOverlay();
  }
}

init();
