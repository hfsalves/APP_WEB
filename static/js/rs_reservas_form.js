const rsStamp = String(window.RS_STAMP || '').trim();
const returnUrl = String(window.RS_RETURN_TO || '/generic/view/RS/').trim() || '/generic/view/RS/';

const overlay = document.getElementById('loadingOverlay');
const overlayText = overlay?.querySelector('.loading-text');
const titleEl = document.getElementById('rsTitulo');
const guestsBody = document.getElementById('rsGuestsBody');
const alojamentoList = document.getElementById('RS_ALOJAMENTO_LIST');
const origemList = document.getElementById('RS_ORIGEM_LIST');
const cancelFieldsWrap = document.getElementById('rsCancelFields');

const guestModalEl = document.getElementById('rsGuestModal');
const guestModal = guestModalEl && window.bootstrap?.Modal ? new window.bootstrap.Modal(guestModalEl) : null;
const guestModalTitle = document.getElementById('rsGuestModalTitle');
const guestSaveBtn = document.getElementById('rsGuestSaveBtn');
const guestDeleteBtn = document.getElementById('rsGuestDeleteBtn');

const fieldIds = [
  'ALOJAMENTO', 'RDATA', 'ORIGEM', 'RESERVA', 'DATAIN', 'DATAOUT', 'HORAIN', 'HORAOUT', 'NOITES', 'NOME', 'PAIS',
  'ADULTOS', 'CRIANCAS', 'ESTADIA', 'LIMPEZA', 'COMISSAO', 'OBS',
  'READY', 'ENTROU', 'SAIU', 'ALERTA', 'CANCELADA', 'DTCANCEL', 'DIASCANCEL', 'NOTIF', 'NOTIF2', 'PCANCEL',
  'BERCO', 'SOFACAMA', 'RTOTAL', 'USRCHECKIN', 'PRESENCIAL', 'SEF', 'USRSEF', 'INSTR', 'USRINSTR',
  'FTNOME', 'FTMORADA', 'FTLOCAL', 'FTCODPOST', 'FTNCONT'
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
  if (!Array.isArray(guests) || !guests.length) {
    guestsBody.innerHTML = '<div class="text-muted p-3">Sem hóspedes. Adicione pelo menos um.</div>';
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
  renderGuests();
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
    ['NACIONALIDADE', 'PAIS_RESIDENCIA', 'PAIS_EMISSOR_DOC'].forEach((name) => fillCountrySelect(guestInputMap[name]));
    guestSaveBtn?.addEventListener('click', saveGuestModal);
    guestDeleteBtn?.addEventListener('click', deleteGuestModal);

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
