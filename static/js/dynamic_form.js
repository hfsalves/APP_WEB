// static/js/dynamic_form.js
function showDynamicFormToast(message, type = 'success', options = {}) {
  if (typeof window.showToast === 'function') {
    window.showToast(message, type, options);
    return;
  }
  alert(message);
}

function queueDynamicFormToast(message, type = 'success', options = {}) {
  if (typeof window.queueToastOnNextPage === 'function') {
    window.queueToastOnNextPage(message, type, options);
  }
}
console.warn('✅ novo dynamic_form.js carregado');

// ===============================
// 1. VARIÁVEIS GLOBAIS & INICIALIZAÇÃO
// ===============================

document.addEventListener('DOMContentLoaded', () => {
  console.log('📦 DOM totalmente carregado');

  const itens = document.querySelectorAll('.dropdown-item');
  console.log('🧪 dropdown-item encontrados:', itens.length);

  itens.forEach(item => {
    item.addEventListener('click', e => {
      console.log('🔘 CLICADO:', item.innerText.trim());
      e.preventDefault();
    });
  });
});

function showLoading() {
  const overlay = document.getElementById('loadingOverlay');
  overlay.style.display = 'flex';
  setTimeout(() => overlay.style.opacity = '1', 15);
}
function hideLoading() {
  const overlay = document.getElementById('loadingOverlay');
  overlay.style.opacity = '0';
  setTimeout(() => overlay.style.display = 'none', 250); // espera pelo fade-out
}


// 🧪 DEBUG extra
console.log('🧪 dropdown-item encontrados:', document.querySelectorAll('.dropdown-item').length);

(async function() {

  showLoading()

  const isMobile = window.innerWidth <= 768;
  console.log('📱 Modo:', isMobile ? 'MOBILE' : 'DESKTOP');

  const formState = {};
  const camposByName = {};

  // ─── DEBUG: find all custom‐action buttons ───
  console.log('modal triggers encontrados:', document.querySelectorAll('.btn-custom'));

  const TABLE_NAME   = window.TABLE_NAME;
  const TABLE_NAME_UPPER = String(TABLE_NAME || '').toUpperCase();
  const RECORD_STAMP = window.RECORD_STAMP;
  const isAdminUser  = window.IS_ADMIN_USER;
  const DEV_MODE = window.DEV_MODE || false;
  const isPartnerForm = ['CL', 'FL'].includes(TABLE_NAME_UPPER);
  const partnerApiBase = `/generic/api/${String(TABLE_NAME || '').toLowerCase()}`;

  console.log('[dynamic_form.js] TABLE_NAME:', TABLE_NAME);

  // ─── Guardar para onde voltar + que detalhe ancorar ───
  // Captura o return_to (e detail_* se vierem) da URL
  const urlParams = new URLSearchParams(window.location.search);

  // Este form é acedido a partir de outro? Ou diretamente?
  const returnTo = urlParams.get('return_to');
  const RETURN_URL = returnTo && returnTo.trim() !== ''
    ? returnTo
    : `/generic/view/${TABLE_NAME}/`;

  console.log('📍 RETURN_URL =', RETURN_URL);


  const DETAIL_TAB = urlParams.get('detail_table')|| null;
  const DETAIL_PK  = urlParams.get('detail_pk')   || null;

    
// ===============================
// 2. CONSTRUÇÃO DO FORMULÁRIO
// ===============================

  const res  = await fetch(`/generic/api/${TABLE_NAME}?action=describe`);
  const cols = await res.json();

  console.log("🧠 Metadados recebidos:", cols);

    // ===============================
    // FUNÇÃO UTILITÁRIA: AVALIAR EXPRESSÕES DE VISIBILIDADE
    // ===============================
    function avaliarExpressao(expr) {
      try {
        const keys = Object.keys(formState);
        const values = Object.values(formState);

        console.log("🧪 EXPRESSÃO:", expr);
        console.log("🧪 KEYS:", keys);
        console.log("🧪 VALUES:", values);
        console.log("🧪 FORMSTATE:", formState);

        const fn = new Function(...keys, `'use strict'; return (${expr});`);
        const result = fn(...values);

        console.log("✅ RESULTADO:", result);
        return result;

      } catch (err) {
        console.warn(`⚠️ Erro ao avaliar expressão: ${expr}`, err);
        return true;
      }
    }

    // ===============================
    // FUNÇÃO: APLICAR CONDIÇÕES DE VISIBILIDADE AOS CAMPOS
    // ===============================
    function aplicarCondicoesDeVisibilidade() {
      cols.forEach(col => {
        if (!col.condicao_visivel) return;

        const input = camposByName[col.name];
        if (!input) return;

        const wrapper = input.closest('.col-12') || input.closest('.sz_field') || input.closest('.sz_checkbox') || input.closest('.mb-3');
        const visivel = avaliarExpressao(col.condicao_visivel, formState);

        if (wrapper) {
          wrapper.style.display = visivel ? '' : 'none';
        }
      });
    }


  console.table(cols.map(c => ({
  campo: c.name,
  ordem: c.ordem,
  ordem_mobile: c.ordem_mobile,
  tam: c.tam,
  tam_mobile: c.tam_mobile
  })));


  // 2. Prepara o form
  const form = document.getElementById('editForm');
  const DECIMAL_SEPARATOR = ',';

  async function prepareClientNoField() {
    if (!isPartnerForm) return;
    const noInput = form.querySelector('[name="NO"]');
    if (!noInput) return;
    if (RECORD_STAMP) {
      noInput.readOnly = true;
      noInput.classList.add('sz_surface_alt');
      return;
    }
    if (String(noInput.value || '').trim() !== '') return;
    try {
      const res = await fetch(`${partnerApiBase}/next_no`);
      const data = await res.json().catch(() => ({}));
      if (!res.ok) return;
      const nextNo = String(data?.NO ?? '').trim();
      if (!nextNo) return;
      noInput.value = nextNo;
      formState.NO = nextNo;
    } catch (err) {
      console.warn('Erro ao obter próximo NO de cliente:', err);
    }
  }

  let clientViesLookupController = null;
  let lastClientViesLookupKey = '';
  let clientViesLookupSequence = 0;
  const clientViesTargetFields = ['NOME', 'MORADA', 'CODPOST', 'LOCAL'];

  function normalizeClientVatForLookup(value) {
    return String(value || '').toUpperCase().replace(/[^A-Z0-9]/g, '');
  }

  function extractPortugueseVatDigits(value) {
    const normalized = normalizeClientVatForLookup(value);
    if (/^PT\d{9}$/.test(normalized)) return normalized.slice(2);
    if (/^\d{9}$/.test(normalized)) return normalized;
    return '';
  }

  function isValidPortugueseNif(value) {
    const digits = extractPortugueseVatDigits(value);
    if (!digits) return false;
    let total = 0;
    for (let index = 0; index < 8; index += 1) {
      total += Number(digits[index]) * (9 - index);
    }
    let checkDigit = 11 - (total % 11);
    if (checkDigit >= 10) checkDigit = 0;
    return checkDigit === Number(digits[8]);
  }

  function looksLikePortugueseVat(value) {
    return Boolean(extractPortugueseVatDigits(value));
  }

  function ensureClientViesStatusElement() {
    if (!isPartnerForm) return null;
    let statusEl = document.getElementById('clientViesStatus');
    if (statusEl) return statusEl;
    const nifInput = form.querySelector('[name="NIF"]');
    const nifWrapper = nifInput?.closest('.sz_field');
    if (!nifWrapper) return null;
    statusEl = document.createElement('div');
    statusEl.id = 'clientViesStatus';
    statusEl.className = 'sz_text_muted';
    statusEl.style.marginTop = 'var(--sz-space-2)';
    statusEl.style.minHeight = '1.25rem';
    nifWrapper.appendChild(statusEl);
    return statusEl;
  }

  function setClientViesStatus(message = '', tone = 'muted', isBusy = false) {
    const statusEl = ensureClientViesStatusElement();
    if (!statusEl) return;
    const colorMap = {
      muted: 'var(--sz-color-text-muted)',
      info: 'var(--sz-color-info)',
      success: 'var(--sz-color-success)',
      warning: 'var(--sz-color-warning)',
      danger: 'var(--sz-color-danger)'
    };
    statusEl.style.color = colorMap[tone] || colorMap.muted;
    statusEl.innerHTML = isBusy
      ? '<i class="fa-solid fa-spinner fa-spin"></i> A consultar VIES...'
      : String(message || '');
  }

  function setClientViesBusy(isBusy) {
    clientViesTargetFields.forEach(fieldName => {
      const input = form.querySelector(`[name="${fieldName}"]`);
      if (!input) return;
      if (isBusy) {
        if (!Object.prototype.hasOwnProperty.call(input.dataset, 'viesReadonlyOriginal')) {
          input.dataset.viesReadonlyOriginal = input.readOnly ? 'true' : 'false';
        }
        input.readOnly = true;
        input.classList.add('sz_surface_alt');
      } else {
        const originalReadonly = input.dataset.viesReadonlyOriginal === 'true';
        input.readOnly = originalReadonly;
        delete input.dataset.viesReadonlyOriginal;
        if (!originalReadonly) {
          input.classList.remove('sz_surface_alt');
        }
      }
    });
  }

  function shouldLookupClientVat(value) {
    const normalized = normalizeClientVatForLookup(value);
    if (!normalized) return false;
    if (/^[A-Z]{2}[A-Z0-9]+$/.test(normalized)) {
      return normalized.length > 4;
    }
    return /^\d{9}$/.test(normalized);
  }

  function setClientFieldValue(fieldName, value) {
    const input = form.querySelector(`[name="${fieldName}"]`);
    if (!input) return;
    const nextValue = String(value || '');
    input.value = nextValue;
    formState[fieldName.toUpperCase()] = nextValue;
  }

  async function lookupClientVatOnVies({ force = false } = {}) {
    if (!isPartnerForm) return;
    const nifInput = form.querySelector('[name="NIF"]');
    if (!nifInput) return;

    const rawValue = String(nifInput.value || '').trim();
    const normalizedVat = normalizeClientVatForLookup(rawValue);
    if (!normalizedVat) {
      lastClientViesLookupKey = '';
      if (clientViesLookupController) clientViesLookupController.abort();
      setClientViesBusy(false);
      setClientViesStatus('', 'muted');
      return;
    }
    if (looksLikePortugueseVat(rawValue) && !isValidPortugueseNif(rawValue)) {
      lastClientViesLookupKey = '';
      if (clientViesLookupController) clientViesLookupController.abort();
      setClientViesBusy(false);
      setClientViesStatus('O NIF introduzido nao e valido. Se for um NIF portugues, confirma os 9 digitos e o digito de controlo.', 'danger');
      showDynamicFormToast('O NIF introduzido nao e valido. Se for um NIF portugues, confirma os 9 digitos e o digito de controlo.', 'warning');
      return;
    }
    if (!shouldLookupClientVat(normalizedVat)) {
      setClientViesBusy(false);
      setClientViesStatus('', 'muted');
      return;
    }
    if (!force && normalizedVat === lastClientViesLookupKey) return;

    clientViesLookupSequence += 1;
    const lookupSequence = clientViesLookupSequence;
    lastClientViesLookupKey = normalizedVat;

    try {
      if (clientViesLookupController) {
        clientViesLookupController.abort();
      }
      clientViesLookupController = new AbortController();
      setClientViesBusy(true);
      setClientViesStatus('', 'info', true);

      const res = await fetch(`${partnerApiBase}/vies_lookup?nif=${encodeURIComponent(rawValue)}`, {
        signal: clientViesLookupController.signal
      });
      const data = await res.json().catch(() => ({}));

      if (lookupSequence !== clientViesLookupSequence) return;

      if (!res.ok || !data?.ok) {
        setClientViesStatus(data?.error || 'Nao foi possivel consultar o VIES.', 'warning');
        showDynamicFormToast(data?.error || 'NÃ£o foi possÃ­vel consultar o VIES.', 'warning');
        return;
      }

      if (!data.valid) {
        setClientViesStatus(data.message || 'O NIF indicado nao esta valido no VIES.', 'warning');
        showDynamicFormToast(data.message || 'O NIF indicado nÃ£o estÃ¡ vÃ¡lido no VIES.', 'warning');
        return;
      }

      if (data.nome) setClientFieldValue('NOME', data.nome);
      if (data.morada) setClientFieldValue('MORADA', data.morada);
      if (data.codpost) setClientFieldValue('CODPOST', data.codpost);
      if (data.local) setClientFieldValue('LOCAL', data.local);

      aplicarCondicoesDeVisibilidade();
      setClientViesStatus(data.message || 'Dados obtidos do VIES.', 'success');
      showDynamicFormToast(data.message || 'Dados obtidos do VIES.', 'success');
    } catch (err) {
      if (err?.name === 'AbortError') return;
      console.warn('Erro ao consultar VIES:', err);
      setClientViesStatus('Nao foi possivel consultar o VIES.', 'warning');
      showDynamicFormToast('NÃ£o foi possÃ­vel consultar o VIES.', 'warning');
    } finally {
      if (lookupSequence === clientViesLookupSequence) {
        setClientViesBusy(false);
      }
    }
  }

  function setupClientVatLookup() {
    if (!isPartnerForm) return;
    const nifInput = form.querySelector('[name="NIF"]');
    if (!nifInput) return;
    ensureClientViesStatusElement();
    nifInput.addEventListener('change', () => lookupClientVatOnVies({ force: true }));
  }

  const isDecimalInput = el => el?.dataset?.decimal === 'true';
  const getDecimalPlacesForInput = el => {
    const places = Number(el?.dataset?.decimalPlaces);
    return Number.isFinite(places) ? Math.max(0, places) : 2;
  };

  function parseDecimalString(value) {
    if (value === null || value === undefined) {
      return { sign: false, integers: '', decimals: '', hasDigits: false };
    }
    let str = String(value).trim();
    let sign = false;
    if (str.startsWith('-')) {
      sign = true;
      str = str.slice(1);
    }
    str = str.replace(/\./g, DECIMAL_SEPARATOR);
    const allowed = new RegExp(`[^0-9${DECIMAL_SEPARATOR}]`, 'g');
    str = str.replace(allowed, '');
    const parts = str.split(DECIMAL_SEPARATOR);
    const integers = parts.shift() || '';
    const decimals = parts.join('');
    const hasDigits = (integers + decimals).length > 0;
    return { sign, integers, decimals, hasDigits };
  }

  function formatDecimalString(parsed, places, { padDecimals = false, forceComma = false } = {}) {
    const { sign, integers, decimals, hasDigits } = parsed;
    if (!hasDigits) return '';
    const normalizedPlaces = Number.isFinite(places) ? Math.max(0, places) : null;
    let integerPart = integers.replace(/^0+(?=\d)/, '');
    if (!integerPart && (decimals || padDecimals)) {
      integerPart = '0';
    } else if (!integerPart) {
      integerPart = '0';
    }
    let decimalPart = decimals;
    if (normalizedPlaces !== null) {
      decimalPart = decimalPart.slice(0, normalizedPlaces);
      if (padDecimals && normalizedPlaces > 0) {
        decimalPart = decimalPart.padEnd(normalizedPlaces, '0');
      }
    }
    let result = integerPart || '0';
    if (normalizedPlaces !== null) {
      if (normalizedPlaces === 0) {
        // sem parte decimal
      } else if (decimalPart.length > 0 || padDecimals || forceComma) {
        const padded = padDecimals
          ? decimalPart.padEnd(normalizedPlaces, '0')
          : decimalPart;
        result += DECIMAL_SEPARATOR + padded;
      }
    } else if (decimalPart.length > 0) {
      result += DECIMAL_SEPARATOR + decimalPart;
    }
    return (sign ? '-' : '') + result;
  }

  function toDisplayDecimal(value, places) {
    const parsed = parseDecimalString(value);
    if (!parsed.hasDigits) return '';
    return formatDecimalString(parsed, places, {
      padDecimals: places > 0,
      forceComma: places > 0
    });
  }

  function toServerDecimal(value, places) {
    const parsed = parseDecimalString(value);
    if (!parsed.hasDigits) return '';
    const formatted = formatDecimalString(parsed, places, {
      padDecimals: places > 0,
      forceComma: places > 0
    });
    return formatted.replace(DECIMAL_SEPARATOR, '.');
  }

  function sanitizeDecimalForInput(value, places, hadComma = false) {
    if (value === null || value === undefined) return '';
    const parsed = parseDecimalString(value);
    if (!parsed.hasDigits) return '';
    return formatDecimalString(parsed, places, {
      padDecimals: hadComma && places > 0,
      forceComma: hadComma && places > 0
    });
  }

  function setCaretPosition(input, pos) {
    if (typeof input.setSelectionRange === 'function') {
      requestAnimationFrame(() => input.setSelectionRange(pos, pos));
    }
  }

  function collectDigits(text = '') {
    return (text.match(/\d+/g) || []).join('');
  }

  function attachDecimalInputBehavior(input, places) {
    if (!input) return;
    const decimalPlaces = Number.isFinite(places) ? Math.max(0, places) : 2;
    input.type = 'text';
    input.inputMode = 'decimal';
    input.autocomplete = 'off';
    input.dataset.decimal = 'true';
    input.dataset.decimalPlaces = decimalPlaces;
    input.classList.add('decimal-input');

    input.addEventListener('keydown', e => {
      if (e.key === ',' || e.key === '.' || e.key === 'Decimal') {
        e.preventDefault();
        const value = input.value || '';
        const start = input.selectionStart ?? value.length;
        const existingComma = value.indexOf(DECIMAL_SEPARATOR);
        if (existingComma >= 0 && start > existingComma) {
          setCaretPosition(input, existingComma + 1);
          return;
        }
        const sign = value.trim().startsWith('-') ? '-' : '';
        const leftDigits = collectDigits(value.slice(0, start));
        const nextCommaIndex = value.indexOf(DECIMAL_SEPARATOR, start);
        const segmentForDecimals = nextCommaIndex >= 0
          ? value.slice(start, nextCommaIndex)
          : value.slice(start);
        const rightDigits = collectDigits(segmentForDecimals);
        const paddedRight = decimalPlaces > 0
          ? rightDigits.slice(0, decimalPlaces).padEnd(decimalPlaces, '0')
          : '';
        let newValue = leftDigits;
        if (!newValue) newValue = '0';
        if (decimalPlaces > 0) {
          newValue += DECIMAL_SEPARATOR + paddedRight;
        }
        input.value = (sign && newValue !== '0' ? sign : '') + newValue;
        const caretPos = input.value.indexOf(DECIMAL_SEPARATOR);
        if (caretPos >= 0) {
          setCaretPosition(input, caretPos + 1);
        }
        input.dispatchEvent(new Event('input', { bubbles: true }));
        return;
      }

      if (/^[0-9]$/.test(e.key)) {
        const value = input.value || '';
        const commaIndex = value.indexOf(DECIMAL_SEPARATOR);
        if (commaIndex >= 0) {
          const start = input.selectionStart ?? value.length;
          if (start > commaIndex) {
            e.preventDefault();
            const offset = Math.min(
              Math.max(start - commaIndex - 1, 0),
              Math.max(decimalPlaces - 1, 0)
            );
            const decimals = value.slice(commaIndex + 1).padEnd(decimalPlaces, '0');
            const decArray = decimals.split('');
            decArray[offset] = e.key;
            const newDecimals = decArray.join('').slice(0, decimalPlaces);
            input.value = value.slice(0, commaIndex + 1) + newDecimals;
            setCaretPosition(input, commaIndex + 1 + Math.min(offset + 1, decimalPlaces));
            input.dispatchEvent(new Event('input', { bubbles: true }));
            return;
          }
        }
      }
    });

    input.addEventListener('input', () => {
      const hadComma = (input.value || '').includes(DECIMAL_SEPARATOR);
      const sanitized = sanitizeDecimalForInput(input.value, decimalPlaces, hadComma);
      if (sanitized !== input.value) {
        const cursor = input.selectionStart ?? sanitized.length;
        input.value = sanitized;
        setCaretPosition(input, Math.min(cursor, sanitized.length));
      }
    });

    input.addEventListener('blur', () => {
      if (!input.value) return;
      input.value = toDisplayDecimal(input.value, decimalPlaces);
    });
  }

  function readValueForState(el) {
    if (!el) return '';
    if (el.type === 'checkbox') return el.checked;
    if (isDecimalInput(el)) return toServerDecimal(el.value, getDecimalPlacesForInput(el));
    return el.value;
  }

  function handleFieldChange(e) {
    const target = e.target;
    if (!target || !target.name) return;
    formState[target.name.toUpperCase()] = readValueForState(target);
    aplicarCondicoesDeVisibilidade();
  }
  // ——— Montagem customizada por ORDEM (uma row por dezena) ———

  // limpa o form
  form.innerHTML = '';

  // agrupa por dezena de ORDEM
  const grupos = {};
  cols
    .filter(c => !c.admin || isAdminUser)
    .sort((a, b) => {
      const oa = isMobile ? a.ordem_mobile : a.ordem;
      const ob = isMobile ? b.ordem_mobile : b.ordem;
      return (oa || 0) - (ob || 0);
    })
    .forEach(col => {
      const ordemUsada = isMobile ? col.ordem_mobile : col.ordem;
      if ((ordemUsada || 0) === 0) return; // se 0, ignorar no mobile (por convenção)

      const key = Math.floor(ordemUsada / 10) * 10;
      (grupos[key] ||= []).push(col);
    });

  // monta cada grupo numa única row
  Object.keys(grupos)
    .sort((a, b) => a - b)
    .forEach(key => {
      const fields = grupos[key];
      const row    = document.createElement('div');
      row.className = 'row gx-3 gy-2';

      // soma total dos TAM para calcular proporções
      const totalTam = fields.reduce((acc, f) => acc + (isMobile ? f.tam_mobile : f.tam || 1), 0);


      row.style.display = 'flex';
      row.style.flexWrap = 'nowrap';


      fields.forEach(col => {
        const tamUsado = isMobile ? col.tam_mobile : col.tam;
        const fraction = (tamUsado || 1) / totalTam;
        const colDiv = document.createElement('div');
        // fixa largura proporcional e impede flex-grow/shrink
        colDiv.style.flex = `0 0 ${fraction * 100}%`;
        colDiv.style.boxSizing = 'border-box';
        // mantém o mesmo comportamento de responsive para mobile
        colDiv.classList.add('col-12');
        row.appendChild(colDiv);

        // se for um campo "vazio", desenha apenas um espaço reservado
        if (!col.name) {
          colDiv.innerHTML = '<div class="invisible">.</div>'; // ocupa espaço mas invisível
          return;
        }

        // NOVO: campo COLOR
        if ((col.tipo || '').toUpperCase() === 'COLOR') {
          let input = document.createElement('input');
          input.type = 'color';
          input.className = 'sz_input';
          input.name = col.name;
          input.id = col.name;
          input.value = col.valor || col.valorAtual || col.VALORDEFAULT || '#000000';
          formState[col.name] = input.value;
          camposByName[col.name] = input;
          input.addEventListener('change', e => {
            formState[col.name] = e.target.value;
            aplicarCondicoesDeVisibilidade();
          });

          const wrapper = document.createElement('div');
          wrapper.className = 'mb-3 sz_field';
          const label = document.createElement('label');
          label.setAttribute('for', col.name);
          label.className = 'sz_label';
          label.innerHTML = `${col.descricao || col.name}`;
          wrapper.appendChild(label);
          wrapper.appendChild(input);

          colDiv.appendChild(wrapper);
          return;
        }
                
        const wrapper = document.createElement('div');
        wrapper.className = 'mb-3 sz_field';

        if (col.tipo === 'BIT') {
              const label = document.createElement('label');
              label.className = 'sz_checkbox';
              label.setAttribute('for', col.name);

              const input = document.createElement('input');
              input.type = 'checkbox';
              input.id = col.name;
              input.name = col.name;

              const text = document.createElement('span');
              text.textContent = col.descricao || col.name;

              label.append(input, text);
              wrapper.appendChild(label);

              formState[col.name] = false;
              camposByName[col.name] = input;

              input.addEventListener('change', handleFieldChange);
            } else {
              const label = document.createElement('label');
              label.setAttribute('for', col.name);
              label.className = 'sz_label';
              label.innerHTML = `${col.descricao || col.name}`;
              if (col.obrigatorio) {
                label.innerHTML += ' <span style="color:red">*</span>';
              }


            // DEV MODE: adiciona info ORDEM | TAM se estiver ativo
            if (window.DEV_MODE) {
              const ordemAtual = isMobile ? col.ordem_mobile : col.ordem;
              const tamAtual   = isMobile ? col.tam_mobile   : col.tam;

              const metaTag = document.createElement('span');
              metaTag.textContent = `${ordemAtual}|${tamAtual}`;
              metaTag.className = 'badge-dev-edit';
              metaTag.style.cursor = 'pointer';

              metaTag.addEventListener('click', () => {
                const novaOrdem = prompt(
                  `Nova ${isMobile ? 'ORDEM_MOBILE' : 'ORDEM'} para ${col.name}:`, ordemAtual
                );
                const novoTam = prompt(
                  `Novo ${isMobile ? 'TAM_MOBILE' : 'TAM'} para ${col.name}:`, tamAtual
                );

                const ordemInt = parseInt(novaOrdem, 10);
                const tamInt   = parseInt(novoTam, 10);

                if (isNaN(ordemInt) || isNaN(tamInt)) {
                  alert("Valores inválidos. Ambos devem ser inteiros.");
                  return;
                }

                // Monta dinamicamente o payload com os campos certos
                const body = {
                  tabela: TABLE_NAME,
                  campo: col.name
                };

                if (isMobile) {
                  body.ordem_mobile = ordemInt;
                  body.tam_mobile   = tamInt;
                } else {
                  body.ordem = ordemInt;
                  body.tam   = tamInt;
                }

                fetch('/generic/api/update_campo', {
                  method: 'POST',
                  headers: { 'Content-Type': 'application/json' },
                  body: JSON.stringify(body)
                })
                .then(res => res.json())
                .then(resp => {
                  if (resp.success) {
                    alert("Campo atualizado com sucesso.");
                    window.location.reload();
                  } else {
                    alert("Erro: " + resp.error);
                  }
                })
                .catch(err => {
                  console.error(err);
                  alert("Erro inesperado ao atualizar.");
                });
              });

              label.appendChild(metaTag);
            }
            wrapper.appendChild(label); 

            let input;

            if (col.tipo === 'COMBO') {
              input = document.createElement('select');
                if (col.obrigatorio) {
                  input.required = true;
                }
              camposByName[col.name] = input;
              input.className = 'sz_select';
              input.name = col.name;
              input.innerHTML = '<option value="">---</option>';

              formState[col.name] = '';
              input.addEventListener('change', handleFieldChange);


            } else if (col.tipo === 'MEMO') {
              input = document.createElement('textarea');
                if (col.obrigatorio) {
                  input.required = true;
                }
              camposByName[col.name] = input;
              input.className = 'sz_textarea';
              input.name = col.name;
              input.rows = 4;

              formState[col.name] = '';
              input.addEventListener('change', handleFieldChange);

            } else {
              input = document.createElement('input');
                if (col.obrigatorio) {
                  input.required = true;
                }
              camposByName[col.name] = input;
              input.className = 'sz_input';
              input.name = col.name;
              input.dataset.tipoCampo = (col.tipo || '').toUpperCase();

              const decimalPlaces = Number.isFinite(Number(col.decimais))
                ? Number(col.decimais)
                : 2;

              if (col.tipo === 'DATE') {
                input.type = 'text';
                input.classList.remove('sz_input');
                input.classList.add('sz_date');
                input.classList.add('flatpickr-date');
              } else if (col.tipo === 'HOUR') {
                input.type = 'time';
              } else if (col.tipo === 'INT') {
                input.type = 'number';
                input.step = '1';
                input.inputMode = 'numeric';
              } else if (col.tipo === 'DECIMAL') {
                attachDecimalInputBehavior(input, decimalPlaces);
              } else {
                input.type = 'text';
              }

              if (col.readonly) {
                input.readOnly = true;
                input.classList.add('sz_surface_alt');
              }

              formState[col.name] = '';
              input.addEventListener('change', handleFieldChange);
            }

            wrapper.appendChild(input);
        }

        colDiv.appendChild(wrapper);
      });
      
      form.appendChild(row);
    });

    console.log("💬 formState final antes de aplicar visibilidade:", formState);
    aplicarCondicoesDeVisibilidade();



  // 4. Popula combos
  // ===============================
// 3. COMBOS E VALORES DEFAULT
// ===============================

await Promise.all(
    cols
      .filter(c => c.tipo === 'COMBO' && c.combo)
      .map(async c => {
        const sel = form.querySelector(`select[name="${c.name}"]`);
        if (!sel) return;
        let opts = [];
        try {
          if (/^\s*SELECT\s+/i.test(c.combo)) {
            opts = await (await fetch(
              `/generic/api/options?query=${encodeURIComponent(c.combo)}`
            )).json();
          } else {
            opts = await (await fetch(c.combo)).json();
          }
        } catch (e) {
          console.error('Falha ao carregar combo', c.name, e);
        }
        opts.forEach(o => {
          const opt = document.createElement('option');
          if (Array.isArray(o)) {
            opt.value = o[0];
            opt.textContent = o[1];
          } else if (o.value !== undefined && o.text !== undefined) {
            opt.value       = o.value;
            opt.textContent = o.text;
          } else {
            opt.value       = o;
            opt.textContent = o;
          }
          sel.append(opt);
        });
      })
  );

    // 5. Preenche defaults a partir da query string (para inserção de linhas)
  {
    const urlParams = new URLSearchParams(window.location.search);
    urlParams.forEach((val, key) => {
      const el = form.querySelector(`[name="${key}"]`);
      if (!el) return;
      if (el.tagName === 'SELECT') {
        // garante que o <select> já tem as <option>
        if ([...el.options].some(o => o.value === val)) {
          el.value = val;
          formState[el.name.toUpperCase()] = el.value;
          aplicarCondicoesDeVisibilidade();
        }
      }
      else if (el.type === 'checkbox') {
        el.checked = ['1','true','True'].includes(val);
        formState[el.name.toUpperCase()] = el.checked;
        aplicarCondicoesDeVisibilidade();
      } else if (isDecimalInput(el)) {
        const places = getDecimalPlacesForInput(el);
        el.value = toDisplayDecimal(val, places);
        formState[el.name.toUpperCase()] = toServerDecimal(el.value, places);
        aplicarCondicoesDeVisibilidade();
      } else {
        el.value = val;
        formState[el.name.toUpperCase()] = el.value;
        aplicarCondicoesDeVisibilidade();
      }
    });
  }

  // ===============================
// 4. CARREGAMENTO DE DADOS EXISTENTES
// ===============================

// 4. Se edição, carrega valores com matching inteligente
if (RECORD_STAMP) {
  try {
    const rec = await (await fetch(`/generic/api/${TABLE_NAME}/${RECORD_STAMP}`)).json();
    Object.entries(rec).forEach(([key, val]) => {
      const nome = key.toUpperCase();
      const el = form.querySelector(`[name="${key}"]`);
      if (!el) return;

      if (el.tagName === 'SELECT') {
        const desired = (val || '').toString().trim();
        if ([...el.options].some(o => o.value === desired)) {
          el.value = desired;
        } else {
          const match = [...el.options].find(o => o.textContent.trim() === desired);
          el.value = match ? match.value : '';
        }
        formState[nome] = el.value;
      } else if (el.type === 'checkbox') {
        el.checked = !!val;
        formState[nome] = el.checked;
      } else if (el.classList.contains('flatpickr-date')) {
        if (val) {
          let d, m, y;
          if (/^\d{4}-\d{2}-\d{2}/.test(val)) {
            [y, m, d] = val.slice(0, 10).split('-');
          } else {
            const dt = new Date(val);
            d = String(dt.getDate()).padStart(2, '0');
            m = String(dt.getMonth() + 1).padStart(2, '0');
            y = dt.getFullYear();
          }
          el.value = `${d}.${m}.${y}`;
        } else {
          el.value = '';
        }
        formState[nome] = el.value;
        } else if (el.type === 'color') {
        // se a cor vier sem "#", adiciona
        let cor = (val || '').toString().trim();
        if (cor && !cor.startsWith('#')) cor = '#' + cor;
        el.value = cor || '#000000';
        formState[nome] = el.value;
      } else if (isDecimalInput(el)) {
        const places = getDecimalPlacesForInput(el);
        const display = toDisplayDecimal(val ?? '', places);
        el.value = display;
        formState[nome] = toServerDecimal(display, places);
      } else {
        el.value = val;
        formState[nome] = el.value;
      }
    });
  } catch (e) {
    console.error('Erro ao carregar registro:', e);
  }
} else {
  document.getElementById('btnDelete')?.style.setProperty('display', 'none');
}

await prepareClientNoField();
setupClientVatLookup();

hideLoading()

  // ===============================
// 5. FLATPICKR E FORMATOS
// ===============================

// 5. Inicializa Flatpickr: em edição mantém o valor, em criação força hoje
  if (window.flatpickr) {
    form.querySelectorAll('.flatpickr-date').forEach(el => {
      console.log('>>> flatpickr init on', el.id, 'value=', el.value);
      flatpickr(el, {
        dateFormat: 'd.m.Y',      // mantém tua máscara
        allowInput: true,
        defaultDate: RECORD_STAMP  // se for novo, RECORD_STAMP é falsy
                    ? el.value    // edição: valor que veio do servidor
                    : new Date(), // criação: hoje
        onReady: (selDates, dateStr, inst) => {
          if (!RECORD_STAMP) {
            // força mesmo: substitui qualquer default falhado por hoje
            inst.setDate(new Date(), true);
          }
        }
      });
    });
  }
    // ===============================
// 6. GESTÃO DE DETALHES (1:N)
// ===============================

// === Início dynamic_details ===
    const detailsContainer = document.getElementById('details-container');
    if (detailsContainer) {
      fetch(`/generic/api/dynamic_details/${TABLE_NAME}/${RECORD_STAMP}`)
        .then(res => res.json())
        .then(detalhes => {
          detalhes.forEach(det => {
            // 1) Card de detalhe
            const card = document.createElement('div');
            card.className = 'sz_panel sz_dynamic_detail_panel mb-4';

            // 2) Título
            const title = document.createElement('h5');
            title.className = 'sz_h4 sz_mb_2';
            title.textContent = det.tabela;
            card.appendChild(title);

            // 3) Wrapper responsivo e tabela
            const wrapper = document.createElement('div');
            wrapper.className = 'sz_table_wrap sz_dynamic_detail_table_wrap mb-3';
            const tbl = document.createElement('table');
            tbl.className = 'sz_table';
            wrapper.appendChild(tbl);
            card.appendChild(wrapper);

            // 4) Cabeçalho da tabela (checkbox como primeira coluna)
            const thead = tbl.createTHead();
            thead.className = 'sz_table_head';
            const hr    = thead.insertRow();
            hr.className = 'sz_table_row';

            // inserimos a célula de seleção NA POSIÇÃO 0
            const thSel = document.createElement('th');
            thSel.className = 'sz_table_cell';
            thSel.innerHTML = '';        // fica em branco, mas força a coluna
            thSel.style.width = '2rem';  // largura fixa para o checkbox
            hr.appendChild(thSel);

            // agora as colunas normais (iniciam em índice 1)
            det.campos.forEach(c => {
              if (c.VISIVEL === false) return;  // ignora colunas invisíveis
              const th = document.createElement('th');
              th.className = 'sz_table_cell';
              th.textContent = c.LABEL;
              hr.appendChild(th);
            });

            // 5) Corpo da tabela com formatação de datas
            const tbody = tbl.createTBody();
            det.rows.forEach(row => {
              const tr = tbody.insertRow();
              tr.className = 'sz_table_row';

              // 5.1) checkbox na célula 0
              const tdSel = tr.insertCell(0);
              tdSel.className = 'sz_table_cell';
              const chk   = document.createElement('input');
              chk.type    = 'checkbox';
              chk.className = 'detail-select sz_detail_select';
              const pk    = row[det.campos[0].CAMPODESTINO];
              chk.value   = pk;
              tdSel.appendChild(chk);

              // 5.2) restantes colunas (começam em 1)
              det.campos.forEach(c => {
                if (c.VISIVEL === false) return;  // ignora colunas invisíveis
                const td = tr.insertCell();
                td.className = 'sz_table_cell';
                let val = row[c.CAMPODESTINO] ?? '';
                td.textContent = val;
              });

              // 5.3) clique na linha
              // 5.3) clique na linha
              tr.addEventListener('click', e => {
                if (e.target !== chk) {
                  const pk = row[det.campos[0].CAMPODESTINO];
                  
                  // Certifica-te que TABLE_NAME e RECORD_STAMP estão definidos globalmente
                  const parentFormUrl = `/generic/form/${TABLE_NAME}/${RECORD_STAMP}`;

                  const p = new URLSearchParams({
                    return_to: parentFormUrl,
                    detail_table: det.tabela,
                    detail_pk: pk
                  });

                  window.location.href = `/generic/form/${det.tabela}/${pk}?${p.toString()}`;
                }
              });

            });
          



            // 6) Botões de ação (Inserir / Editar / Eliminar)
            const btnGroup = document.createElement('div');
            btnGroup.className = 'sz_table_actions';

            // Inserir
            const btnInsert = document.createElement('button');
            btnInsert.type = 'button';
            btnInsert.className = 'sz_button sz_button_primary';
            btnInsert.title = 'Inserir';
            btnInsert.innerHTML = '<i class="fa fa-plus"></i>';

            btnInsert.addEventListener('click', () => {
              const params = new URLSearchParams();

              // Copia campos do formulário pai para os campos da linha filha
              det.camposcab.forEach((fullSrc, i) => {
                const fullDst = det.camposlin[i];
                if (!fullDst) return;

                const srcCol = fullSrc.split('.')[1];
                const dstCol = fullDst.split('.')[1];
                const val = form.querySelector(`[name="${srcCol}"]`)?.value;

                if (val) params.append(dstCol, val);
              });

              // URL do form da tabela mãe
              const parentFormUrl = `/generic/form/${TABLE_NAME}/${RECORD_STAMP}`;

              params.append('return_to', parentFormUrl);
              params.append('detail_table', det.tabela);

              window.location.href = `/generic/form/${det.tabela}/?${params.toString()}`;
            });

            // Editar (usa a primeira coluna como chave)
            const btnEdit = document.createElement('button');
            btnEdit.className = 'btn btn-sm btn-secondary';
            btnEdit.title = 'Editar';
            btnEdit.innerHTML = '<i class="fa fa-edit"></i>';
            btnEdit.addEventListener('click', () => {
              const id  = row[det.campos[0].CAMPODESTINO];
              const cur = window.location.pathname + window.location.search;
              const ret = encodeURIComponent(cur);
              window.location.href = `/generic/form/${det.tabela}/${id}`
                + `?return_to=${ret}`
                + `&detail_table=${det.tabela}`
                + `&detail_anchor=${id}`;
            });

            // Eliminar
            // Eliminar (tanto single como múltiplos via checkbox)
            const btnDelete = document.createElement('button');
            btnDelete.type = 'button';
            btnDelete.className = 'sz_button sz_button_danger';
            btnDelete.title = 'Eliminar';
            btnDelete.innerHTML = '<i class="fa fa-trash"></i>';
            btnDelete.addEventListener('click', async e => {
              e.stopPropagation();

              // ——— AQUI, dentro do listener, antes de qualquer fetch/delete ———
              // 1) encontra qual é o campo PK (invisível) na definição de colunas
              const campoPK = det.campos.find(c => c.PRIMARY_KEY || c.VISIVEL === false)?.CAMPODESTINO;
              if (!campoPK) {
                alert("Chave primária não definida.");
                return;
              }

              // 2) recolhe todas as linhas marcadas
              const checked = Array.from(card.querySelectorAll('tbody input[type="checkbox"]'))
                                  .filter(ch => ch.checked);

              // 3) se não houver nenhuma marcada, apaga só a primeira linha
              if (checked.length === 0) {
                // pega a primeira <tr>
                const firstRow = card.querySelector('tbody tr');
                if (!firstRow) return alert('Nenhum registo visível.');

                // usa o campo PK para ir buscar o valor correto
                const rowData = det.rows.find(r => r[campoPK] === firstRow.querySelector('input').value);
                const id = rowData ? rowData[campoPK] : null;
                if (!id) return alert('Não consegui determinar o ID a eliminar.');

                if (!(await (window.szConfirmDelete?.('Pretende eliminar este registo?') ?? Promise.resolve(confirm('Confirmar elimina??o?'))))) return;

                const resp = await fetch(`/generic/api/${det.tabela}/${id}`, { method: 'DELETE' });
                if (!resp.ok) {
                  const err = await resp.json().catch(() => ({}));
                  return alert('Erro: ' + (err.error || resp.statusText));
                }

                firstRow.remove();
                return;
              }

              // 4) se houver múltiplos marcados, percorre cada um
              if (!confirm(`Eliminar ${checked.length} registo(s)?`)) return;
              for (const ch of checked) {
                const id = ch.value;  // ch.value já foi definido como row[campoPK]
                const resp = await fetch(`/generic/api/${det.tabela}/${id}`, { method: 'DELETE' });
                if (!resp.ok) {
                  const err = await resp.json().catch(() => ({}));
                  alert(`Falha ao eliminar ${id}: ${err.error || resp.statusText}`);
                  continue;
                }
                ch.closest('tr').remove();
              }

              // — fim do listener —
            });


            btnGroup.append(btnInsert, btnDelete);
            card.appendChild(btnGroup);

            // 7) Anexa o card ao container
            detailsContainer.appendChild(card);
          });
        })
        .catch(err => {
          console.error('Erro ao carregar detalhes:', err);
        });
      }   

    // ===============================
// 7. ANEXOS
// ===============================

// ——— Início Anexos ———
    const btnAddAnexo = document.getElementById('btnAddAnexo');
    const inputAnexo  = document.getElementById('inputAnexo');
    const listaAnx    = document.getElementById('anexos-list');

    async function refreshAnexos() {
      if (!RECORD_STAMP) return; // só em edição
      const res = await fetch(`/api/anexos?table=${TABLE_NAME}&rec=${RECORD_STAMP}`);
      if (!res.ok) return console.error('Falha ao listar anexos');
      const arr = await res.json();

      if (!arr.length) {
        listaAnx.innerHTML = '<p class="sz_text_muted sz_dynamic_anexos_empty">Ainda não há anexos.</p>';
        return;
      }

      listaAnx.innerHTML = arr.map(a => `
        <div class="sz_dynamic_anexo_item">
          <button type="button"
                  class="sz_dynamic_anexo_icon sz_dynamic_anexo_info"
                  data-anexo-action="info"
                  data-id="${a.ANEXOSSTAMP}"
                  title="Ver detalhes"
                  aria-label="Ver detalhes">
            <i class="fa fa-info-circle"></i>
          </button>

          <a href="${a.CAMINHO}" target="_blank" class="sz_dynamic_anexo_link">
            ${a.FICHEIRO}
          </a>

          <button type="button"
                  class="sz_dynamic_anexo_icon sz_dynamic_anexo_delete"
                  data-anexo-action="delete"
                  data-id="${a.ANEXOSSTAMP}"
                  title="Eliminar anexo"
                  aria-label="Eliminar anexo">
            <i class="fa fa-times"></i>
          </button>
        </div>
      `).join('');

      // info → abre dynamic_form da tabela ANEXOS
      listaAnx.querySelectorAll('[data-anexo-action="info"]').forEach(el => {
        el.addEventListener('click', () => {
          const id = el.dataset.id;
          window.location.href = `/generic/form/ANEXOS/${id}`;
        });
      });

      // × → apagar
      listaAnx.querySelectorAll('[data-anexo-action="delete"]').forEach(el => {
        el.addEventListener('click', async () => {
          const id = el.dataset.id;
          if (!confirm('Eliminar este anexo?')) return;

          // aqui: ajusta a URL para o teu endpoint de delete correto.
          // Por exemplo, se estiver em generic/api/anexos/<id>:
          const resp = await fetch(`/generic/api/anexos/${id}`, { method: 'DELETE' });

          if (!resp.ok) {
            const err = await resp.json().catch(() => ({}));
            return alert('Erro ao eliminar: ' + (err.error || resp.statusText));
          }
          await refreshAnexos();
        });
      });
    }


    // abrir file picker
    btnAddAnexo.addEventListener('click', () => inputAnexo.click());

    // upload
    inputAnexo.addEventListener('change', async () => {
      const file = inputAnexo.files[0];
      if (!file || !RECORD_STAMP) return;
      const formD = new FormData();
      formD.append('file', file);
      formD.append('table', TABLE_NAME);
      formD.append('rec', RECORD_STAMP);
      formD.append('descricao', ''); 

      const res = await fetch('/api/anexos/upload', {
        method: 'POST',
        body: formD
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        return alert('Erro ao anexar: ' + (err.error || res.statusText));
      }
      inputAnexo.value = '';
      await refreshAnexos();
    });

    // assim que o form carrega, busca os anexos
    if (RECORD_STAMP) {
      await refreshAnexos();
    }
    // ——— Fim Anexos ———

    // ===============================
// 7B. IMAGENS DE ALOJAMENTO
// ===============================
    const isAlojamentoForm = String(TABLE_NAME || '').toUpperCase() === 'AL';
    const btnALFotos = document.getElementById('btnALFotos');
    const alFotosModalEl = document.getElementById('alFotosModal');
    const alFotosGrid = document.getElementById('alFotosGrid');
    const alFotosStatus = document.getElementById('alFotosStatus');
    const alFotosInput = document.getElementById('alFotosInput');
    const btnALFotosPick = document.getElementById('btnALFotosPick');
    const alFotosDropzone = document.getElementById('alFotosDropzone');
    const alFotosModal = alFotosModalEl ? new bootstrap.Modal(alFotosModalEl) : null;
    let alFotosRows = [];
    let dragFotoStamp = null;

    function setALFotosStatus(message = '', { isError = false } = {}) {
      if (!alFotosStatus) return;
      alFotosStatus.textContent = message;
      alFotosStatus.classList.toggle('is-error', Boolean(isError));
    }

    function getALFotoStaticUrl(path) {
      const clean = String(path || '').trim().replace(/^\/+/, '');
      return clean ? `/static/${clean}` : '';
    }

    function renderALFotos() {
      if (!alFotosGrid) return;
      if (!alFotosRows.length) {
        alFotosGrid.innerHTML = `
          <div class="sz_al_fotos_empty">
            Ainda não existem imagens para este alojamento.
          </div>
        `;
        return;
      }

      alFotosGrid.innerHTML = alFotosRows.map(row => {
        const stamp = row.ALFOTOSTAMP || '';
        const isCover = Boolean(row.CAPA);
        return `
          <article class="sz_al_fotos_card${isCover ? ' is-cover' : ''}" draggable="true" data-foto-stamp="${stamp}">
            <div class="sz_al_fotos_thumb">
              <img src="${getALFotoStaticUrl(row.CAMINHO)}" alt="${row.ALT_TEXT || row.FICHEIRO || 'Imagem do alojamento'}">
            </div>
            <div class="sz_al_fotos_meta">
              <div class="sz_al_fotos_topline">
                <div class="sz_al_fotos_filename">${row.FICHEIRO || 'Imagem'}</div>
                ${isCover ? '<span class="sz_al_fotos_badge">Capa</span>' : ''}
              </div>
              <div class="sz_al_fotos_controls">
                <button type="button" class="sz_button sz_button_ghost btn-al-foto-cover" data-foto-stamp="${stamp}">
                  <i class="fa fa-star"></i>
                  <span>${isCover ? 'Foto de capa' : 'Definir capa'}</span>
                </button>
                <button type="button" class="sz_button sz_button_danger btn-al-foto-delete" data-foto-stamp="${stamp}">
                  <i class="fa fa-trash-alt"></i>
                  <span>Apagar</span>
                </button>
                <span class="sz_al_fotos_drag_hint">
                  <i class="fa fa-grip-vertical"></i>
                  Arrastar
                </span>
              </div>
            </div>
          </article>
        `;
      }).join('');
    }

    async function refreshALFotos({ silent = false } = {}) {
      if (!isAlojamentoForm || !RECORD_STAMP || !alFotosGrid) return;
      if (!silent) {
        setALFotosStatus('A carregar imagens...');
      }
      const res = await fetch(`/generic/api/al_fotos/${encodeURIComponent(RECORD_STAMP)}`);
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        setALFotosStatus(data.error || 'Erro ao carregar imagens.', { isError: true });
        return;
      }
      alFotosRows = Array.isArray(data) ? data : [];
      renderALFotos();
      const count = alFotosRows.length;
      setALFotosStatus(count ? `${count} imagem(ns) carregada(s). Arrasta para reordenar.` : '');
    }

    async function uploadALFotos(files) {
      if (!isAlojamentoForm || !RECORD_STAMP || !files?.length) return;
      const formData = new FormData();
      Array.from(files).forEach(file => formData.append('files', file));
      setALFotosStatus(`A carregar ${files.length} imagem(ns)...`);
      const res = await fetch(`/generic/api/al_fotos/${encodeURIComponent(RECORD_STAMP)}/upload`, {
        method: 'POST',
        body: formData
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        setALFotosStatus(data.error || 'Erro ao carregar imagens.', { isError: true });
        return;
      }
      setALFotosStatus('Imagens carregadas com sucesso.');
      await refreshALFotos({ silent: true });
    }

    async function setALFotoCover(fotoStamp) {
      const res = await fetch(`/generic/api/al_fotos/${encodeURIComponent(RECORD_STAMP)}/capa/${encodeURIComponent(fotoStamp)}`, {
        method: 'POST'
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        setALFotosStatus(data.error || 'Erro ao definir foto de capa.', { isError: true });
        return;
      }
      setALFotosStatus('Foto de capa atualizada.');
      await refreshALFotos({ silent: true });
    }

    async function deleteALFoto(fotoStamp) {
      const res = await fetch(`/generic/api/al_fotos/${encodeURIComponent(RECORD_STAMP)}/${encodeURIComponent(fotoStamp)}`, {
        method: 'DELETE'
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        setALFotosStatus(data.error || 'Erro ao apagar imagem.', { isError: true });
        return;
      }
      setALFotosStatus('Imagem removida.');
      await refreshALFotos({ silent: true });
    }

    async function persistALFotosOrder() {
      if (!alFotosGrid) return;
      const ordered = Array.from(alFotosGrid.querySelectorAll('.sz_al_fotos_card'))
        .map(card => card.dataset.fotoStamp)
        .filter(Boolean);
      if (!ordered.length) return;
      const res = await fetch(`/generic/api/al_fotos/${encodeURIComponent(RECORD_STAMP)}/ordem`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ items: ordered })
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        setALFotosStatus(data.error || 'Erro ao reordenar imagens.', { isError: true });
        return;
      }
      await refreshALFotos({ silent: true });
    }

    if (btnALFotos && alFotosModalEl && isAlojamentoForm) {
      btnALFotos.addEventListener('click', async () => {
        if (!RECORD_STAMP) return;
        alFotosModal.show();
        await refreshALFotos();
      });

      btnALFotosPick?.addEventListener('click', () => alFotosInput?.click());
      alFotosInput?.addEventListener('change', async () => {
        const files = alFotosInput.files;
        if (!files?.length) return;
        await uploadALFotos(files);
        alFotosInput.value = '';
      });

      alFotosDropzone?.addEventListener('click', () => alFotosInput?.click());
      alFotosDropzone?.addEventListener('keydown', e => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          alFotosInput?.click();
        }
      });
      ['dragenter', 'dragover'].forEach(evt => {
        alFotosDropzone?.addEventListener(evt, e => {
          e.preventDefault();
          alFotosDropzone.classList.add('is-dragover');
        });
      });
      ['dragleave', 'drop'].forEach(evt => {
        alFotosDropzone?.addEventListener(evt, e => {
          e.preventDefault();
          alFotosDropzone.classList.remove('is-dragover');
        });
      });
      alFotosDropzone?.addEventListener('drop', async e => {
        const files = e.dataTransfer?.files;
        if (files?.length) {
          await uploadALFotos(files);
        }
      });

      alFotosGrid?.addEventListener('click', async e => {
        const coverBtn = e.target.closest('.btn-al-foto-cover');
        if (coverBtn) {
          await setALFotoCover(coverBtn.dataset.fotoStamp);
          return;
        }
        const deleteBtn = e.target.closest('.btn-al-foto-delete');
        if (deleteBtn) {
          if (!confirm('Apagar esta imagem?')) return;
          await deleteALFoto(deleteBtn.dataset.fotoStamp);
        }
      });

      alFotosGrid?.addEventListener('dragstart', e => {
        const card = e.target.closest('.sz_al_fotos_card');
        if (!card) return;
        dragFotoStamp = card.dataset.fotoStamp || null;
        card.classList.add('is-dragging');
        e.dataTransfer.effectAllowed = 'move';
      });

      alFotosGrid?.addEventListener('dragend', e => {
        const card = e.target.closest('.sz_al_fotos_card');
        if (card) card.classList.remove('is-dragging');
        alFotosGrid.querySelectorAll('.sz_al_fotos_card').forEach(node => node.classList.remove('is-drop-target'));
        dragFotoStamp = null;
      });

      alFotosGrid?.addEventListener('dragover', e => {
        const target = e.target.closest('.sz_al_fotos_card');
        const dragging = alFotosGrid.querySelector('.sz_al_fotos_card.is-dragging');
        if (!target || !dragging || target === dragging) return;
        e.preventDefault();
        alFotosGrid.querySelectorAll('.sz_al_fotos_card').forEach(node => node.classList.remove('is-drop-target'));
        target.classList.add('is-drop-target');
        const rect = target.getBoundingClientRect();
        const shouldInsertAfter = (e.clientY - rect.top) > rect.height / 2;
        if (shouldInsertAfter) {
          target.after(dragging);
        } else {
          target.before(dragging);
        }
      });

      alFotosGrid?.addEventListener('drop', async e => {
        const target = e.target.closest('.sz_al_fotos_card');
        if (!target || !dragFotoStamp) return;
        e.preventDefault();
        alFotosGrid.querySelectorAll('.sz_al_fotos_card').forEach(node => node.classList.remove('is-drop-target'));
        await persistALFotosOrder();
        setALFotosStatus('Ordem das imagens atualizada.');
      });
    }

    // ===============================
// 7C. NOTIFICACOES PUSH NA FICHA DE UTILIZADOR
// ===============================
    const isUserForm = String(TABLE_NAME || '').toUpperCase() === 'US';
    const btnUserPushNotify = document.getElementById('btnUserPushNotify');
    const btnUserPushNotifyInline = document.getElementById('btnUserPushNotifyInline');
    const btnUserPushRefresh = document.getElementById('btnUserPushRefresh');
    const userPushPanel = document.getElementById('userPushPanel');
    const userPushStatus = document.getElementById('userPushStatus');
    const userPushSummary = document.getElementById('userPushSummary');
    const userPushLogs = document.getElementById('userPushLogs');
    const userPushModalEl = document.getElementById('userPushModal');
    const userPushModalStatus = document.getElementById('userPushModalStatus');
    const userPushTitle = document.getElementById('userPushTitle');
    const userPushBody = document.getElementById('userPushBody');
    const userPushUrl = document.getElementById('userPushUrl');
    const btnUserPushSendModal = document.getElementById('btnUserPushSendModal');
    const userPushModal = userPushModalEl ? new bootstrap.Modal(userPushModalEl) : null;
    let userPushSummaryData = null;

    function setUserPushStatus(message = '', { isError = false } = {}) {
      if (!userPushStatus) return;
      userPushStatus.textContent = message;
      userPushStatus.classList.toggle('is-error', Boolean(isError));
      userPushStatus.classList.toggle('is-success', Boolean(message) && !isError);
    }

    function setUserPushModalStatus(message = '', { isError = false } = {}) {
      if (!userPushModalStatus) return;
      userPushModalStatus.textContent = message;
      userPushModalStatus.classList.toggle('is-error', Boolean(isError));
      userPushModalStatus.classList.toggle('is-success', Boolean(message) && !isError);
    }

    function fmtPushDate(value) {
      if (!value) return '';
      try {
        const dt = new Date(value);
        if (Number.isNaN(dt.getTime())) return String(value);
        return dt.toLocaleString('pt-PT', {
          year: 'numeric',
          month: '2-digit',
          day: '2-digit',
          hour: '2-digit',
          minute: '2-digit',
        });
      } catch (_) {
        return String(value || '');
      }
    }

    function renderUserPushSummary() {
      if (!userPushSummary || !userPushLogs) return;
      const data = userPushSummaryData || {};
      const activeDevices = Number(data.active_devices || 0);
      const devices = Array.isArray(data.devices) ? data.devices : [];
      const logs = Array.isArray(data.logs) ? data.logs : [];
      const prefs = Array.isArray(data.preferences) ? data.preferences : [];

      userPushSummary.innerHTML = `
        <div class="sz_user_push_stats">
          <div class="sz_user_push_stat">
            <span class="sz_user_push_stat_label">Dispositivos ativos</span>
            <strong class="sz_user_push_stat_value">${activeDevices}</strong>
          </div>
          <div class="sz_user_push_stat">
            <span class="sz_user_push_stat_label">Preferências ativas</span>
            <strong class="sz_user_push_stat_value">${prefs.filter(p => Number(p.PUSH_ENABLED || 0) === 1).length}</strong>
          </div>
          <div class="sz_user_push_stat">
            <span class="sz_user_push_stat_label">Último envio</span>
            <strong class="sz_user_push_stat_value">${logs.length ? fmtPushDate(logs[0].SENT_AT || logs[0].CREATED_AT) : '-'}</strong>
          </div>
        </div>
        <div class="sz_user_push_prefs">
          ${prefs.length ? prefs.map(pref => `
            <span class="sz_user_push_pref${Number(pref.PUSH_ENABLED || 0) === 1 ? ' is-active' : ''}">
              ${pref.EVENT_TYPE || '-'}
            </span>
          `).join('') : ''}
        </div>
        <div class="sz_user_push_devices">
          ${devices.length ? devices.map(device => `
            <div class="sz_user_push_device${Number(device.IS_ACTIVE || 0) === 1 ? ' is-active' : ''}">
              <div class="sz_user_push_device_title">${device.DEVICE_LABEL || device.PLATFORM || 'Dispositivo'}</div>
              <div class="sz_user_push_device_meta">
                <span>${device.PLATFORM || 'unknown'}</span>
                <span>${fmtPushDate(device.LAST_SEEN) || 'Sem atividade'}</span>
              </div>
            </div>
          `).join('') : '<div class="sz_user_push_empty">Sem dispositivos registados.</div>'}
        </div>
      `;

      userPushLogs.innerHTML = `
        <div class="sz_user_push_logs_title">Últimos envios</div>
        ${logs.length ? logs.map(log => `
          <div class="sz_user_push_log">
            <div class="sz_user_push_log_head">
              <strong>${log.TITLE || 'Notificação'}</strong>
              <span class="sz_user_push_log_status is-${String(log.STATUS || '').toLowerCase()}">${log.STATUS || '-'}</span>
            </div>
            <div class="sz_user_push_log_meta">
              <span>${log.EVENT_TYPE || '-'}</span>
              <span>${fmtPushDate(log.CREATED_AT)}</span>
              <span>${log.SENT_BY_NAME || ''}</span>
            </div>
          </div>
        `).join('') : '<div class="sz_user_push_empty">Sem envios registados.</div>'}
      `;
    }

    async function refreshUserPushSummary({ silent = false } = {}) {
      if (!isUserForm || !RECORD_STAMP || !userPushPanel) return;
      if (!silent) setUserPushStatus('A carregar notificações push...');
      const res = await fetch(`/api/push/user/${encodeURIComponent(RECORD_STAMP)}/summary`, {
        credentials: 'same-origin',
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        setUserPushStatus(data.error || 'Erro ao carregar notificações push.', { isError: true });
        return;
      }
      userPushSummaryData = data;
      renderUserPushSummary();
      setUserPushStatus(
        Number(data.active_devices || 0) > 0
          ? `${data.active_devices} dispositivo(s) ativo(s).`
          : 'Sem dispositivos ativos para este utilizador.'
      );
      const canSendManual = Boolean(data.can_send_manual);
      btnUserPushNotify?.toggleAttribute('disabled', !canSendManual);
      btnUserPushNotifyInline?.toggleAttribute('disabled', !canSendManual);
    }

    function openUserPushModal() {
      if (!userPushModal) return;
      setUserPushModalStatus('');
      if (userPushTitle) userPushTitle.value = '';
      if (userPushBody) userPushBody.value = '';
      if (userPushUrl) userPushUrl.value = '/monitor';
      userPushModal.show();
    }

    async function sendManualUserPush() {
      const title = (userPushTitle?.value || '').trim();
      const body = (userPushBody?.value || '').trim();
      const targetUrl = (userPushUrl?.value || '').trim();
      if (!title) {
        setUserPushModalStatus('Título obrigatório.', { isError: true });
        userPushTitle?.focus();
        return;
      }
      if (!body) {
        setUserPushModalStatus('Mensagem obrigatória.', { isError: true });
        userPushBody?.focus();
        return;
      }
      setUserPushModalStatus('A enviar...');
      const res = await fetch('/api/push/send-manual', {
        method: 'POST',
        credentials: 'same-origin',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        },
        body: JSON.stringify({
          userstamp: RECORD_STAMP,
          title,
          body,
          target_url: targetUrl || '/monitor',
        }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        setUserPushModalStatus(data.error || 'Erro ao enviar notificação.', { isError: true });
        return;
      }
      if (data?.result?.status === 'NO_DEVICES') {
        setUserPushModalStatus('Este utilizador ainda não tem dispositivos ativos.', { isError: true });
        return;
      }
      setUserPushModalStatus('Notificação enviada.');
      await refreshUserPushSummary({ silent: true });
      setTimeout(() => userPushModal.hide(), 500);
    }

    if (isUserForm && RECORD_STAMP) {
      btnUserPushNotify?.addEventListener('click', openUserPushModal);
      btnUserPushNotifyInline?.addEventListener('click', openUserPushModal);
      btnUserPushRefresh?.addEventListener('click', async () => {
        await refreshUserPushSummary();
      });
      btnUserPushSendModal?.addEventListener('click', async () => {
        await sendManualUserPush();
      });
      userPushModalEl?.addEventListener('hidden.bs.modal', () => setUserPushModalStatus(''));
      await refreshUserPushSummary();
    }

    // ===============================
// 7C. EMPRESAS DO UTILIZADOR
// ===============================
    const userFeTableBody = document.getElementById('userFeTableBody');
    const userFeNewFeid = document.getElementById('userFeNewFeid');
    const btnUserFeAdd = document.getElementById('btnUserFeAdd');
    const userFeStatus = document.getElementById('userFeStatus');
    let userFeRows = [];
    let userFeOptions = [];

    function setUserFeStatus(message = '', { isError = false, isSuccess = false } = {}) {
      if (!userFeStatus) return;
      userFeStatus.textContent = message;
      userFeStatus.classList.toggle('is-error', Boolean(isError));
      userFeStatus.classList.toggle('is-success', Boolean(isSuccess));
    }

    function renderUserFeOptions() {
      if (!userFeNewFeid) return;
      const used = new Set(userFeRows.map(row => String(row.FEID)));
      const available = userFeOptions.filter(opt => !used.has(String(opt.FEID)));
      userFeNewFeid.innerHTML = available.length
        ? `<option value="">Seleciona empresa</option>${available.map(opt => `<option value="${opt.FEID}">${opt.NOME || `Empresa ${opt.FEID}`}</option>`).join('')}`
        : '<option value="">Sem empresas disponíveis</option>';
      userFeNewFeid.disabled = !RECORD_STAMP || available.length === 0;
      if (btnUserFeAdd) btnUserFeAdd.disabled = !RECORD_STAMP || available.length === 0;
    }

    function renderUserFeRows() {
      if (!userFeTableBody) return;
      if (!RECORD_STAMP) {
        userFeTableBody.innerHTML = '<tr><td colspan="4" class="sz_text_muted">Grava primeiro o utilizador para gerir empresas.</td></tr>';
        renderUserFeOptions();
        return;
      }
      if (!userFeRows.length) {
        userFeTableBody.innerHTML = '<tr><td colspan="4" class="sz_text_muted">Ainda não existem empresas associadas.</td></tr>';
        renderUserFeOptions();
        return;
      }

      userFeTableBody.innerHTML = userFeRows.map(row => `
        <tr data-usfe-stamp="${row.USFESTAMP}">
          <td>${row.FE_NOME || `Empresa ${row.FEID}`}</td>
          <td class="sz_col_fit"><input type="checkbox" class="form-check-input user-fe-ativo" ${row.ATIVO ? 'checked' : ''}></td>
          <td class="sz_col_fit"><input type="radio" name="userFePrincipal" class="form-check-input user-fe-principal" ${row.PRINCIPAL ? 'checked' : ''}></td>
          <td class="sz_col_fit">
            <div class="d-inline-flex gap-1">
              <button type="button" class="sz_button sz_button_secondary user-fe-save" title="Gravar"><i class="fa fa-save"></i></button>
              <button type="button" class="sz_button sz_button_danger user-fe-delete" title="Eliminar"><i class="fa fa-trash"></i></button>
            </div>
          </td>
        </tr>
      `).join('');
      renderUserFeOptions();
    }

    async function refreshUserFeRows({ silent = false } = {}) {
      if (!isUserForm || !userFeTableBody) return;
      if (!RECORD_STAMP) {
        renderUserFeRows();
        return;
      }
      if (!silent) setUserFeStatus('A carregar empresas...');
      const res = await fetch(`/generic/api/us/${encodeURIComponent(RECORD_STAMP)}/empresas`);
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        setUserFeStatus(data.error || 'Erro ao carregar empresas.', { isError: true });
        return;
      }
      userFeRows = Array.isArray(data.rows) ? data.rows : [];
      userFeOptions = Array.isArray(data.fe_options) ? data.fe_options : [];
      renderUserFeRows();
      setUserFeStatus(`${userFeRows.length} empresa(s) associada(s).`);
    }

    async function createUserFeRow() {
      const feid = Number(userFeNewFeid?.value || 0);
      if (!feid) {
        setUserFeStatus('Seleciona a empresa a associar.', { isError: true });
        return;
      }
      const res = await fetch(`/generic/api/us/${encodeURIComponent(RECORD_STAMP)}/empresas`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ FEID: feid, ATIVO: true, PRINCIPAL: userFeRows.length === 0 })
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        setUserFeStatus(data.error || 'Erro ao adicionar empresa.', { isError: true });
        return;
      }
      setUserFeStatus('Empresa associada com sucesso.', { isSuccess: true });
      await refreshUserFeRows({ silent: true });
    }

    async function updateUserFeRow(usfeStamp, payload) {
      const res = await fetch(`/generic/api/us/${encodeURIComponent(RECORD_STAMP)}/empresas/${encodeURIComponent(usfeStamp)}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        setUserFeStatus(data.error || 'Erro ao gravar empresa.', { isError: true });
        return false;
      }
      return true;
    }

    async function deleteUserFeRow(usfeStamp) {
      const res = await fetch(`/generic/api/us/${encodeURIComponent(RECORD_STAMP)}/empresas/${encodeURIComponent(usfeStamp)}`, {
        method: 'DELETE'
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        setUserFeStatus(data.error || 'Erro ao eliminar empresa.', { isError: true });
        return false;
      }
      return true;
    }

    if (isUserForm && userFeTableBody) {
      btnUserFeAdd?.addEventListener('click', async () => {
        await createUserFeRow();
      });

      userFeTableBody.addEventListener('click', async (event) => {
        const rowEl = event.target.closest('tr[data-usfe-stamp]');
        if (!rowEl) return;
        const usfeStamp = rowEl.dataset.usfeStamp;
        if (event.target.closest('.user-fe-save')) {
          const ativo = rowEl.querySelector('.user-fe-ativo')?.checked ?? false;
          const principal = rowEl.querySelector('.user-fe-principal')?.checked ?? false;
          const ok = await updateUserFeRow(usfeStamp, { ATIVO: ativo, PRINCIPAL: principal });
          if (ok) {
            setUserFeStatus('Empresas atualizadas.', { isSuccess: true });
            await refreshUserFeRows({ silent: true });
          }
          return;
        }
        if (event.target.closest('.user-fe-delete')) {
          if (!confirm('Eliminar esta associação à empresa?')) return;
          const ok = await deleteUserFeRow(usfeStamp);
          if (ok) {
            setUserFeStatus('Empresa removida.', { isSuccess: true });
            await refreshUserFeRows({ silent: true });
          }
        }
      });

      await refreshUserFeRows();
    }



    // ===============================
// 8. PERMISSÕES E BOTÕES
// ===============================

// 6. Cancelar e eliminar
    document.getElementById('btnCancel')?.addEventListener('click', ()=> {
    window.location.href = RETURN_URL;
    });
    // Eliminar
    document.getElementById('btnDelete')?.addEventListener('click', async () => {
      if (!RECORD_STAMP || !TABLE_NAME) return;
      if (!(await (window.szConfirmDelete?.('Pretende eliminar este registo?') ?? Promise.resolve(confirm('Confirmar elimina??o?'))))) return;

      try {
        const resp = await fetch(`/generic/api/${TABLE_NAME}/${RECORD_STAMP}`, { method: 'DELETE' });
        if (!resp.ok) {
          const err = await resp.json().catch(() => ({}));
          showDynamicFormToast('Erro: ' + (err.error || resp.statusText), 'danger');
          return;
        }
        queueDynamicFormToast('Registo eliminado.', 'success');
        window.location.href = RETURN_URL;
      } catch (err) {
        console.error('Erro ao eliminar:', err);
        showDynamicFormToast('Erro inesperado ao eliminar.', 'danger');
      }
    });

      // ===============================
// 10. MODAIS CUSTOMIZADOS
// ===============================

// ─── Hooks para os botões customizados de MODAL ───
      // (click em qualquer <a class="dropdown-item btn-custom" data-tipo="MODAL">)
      document.addEventListener('click', e => {
        const btn = e.target.closest('.dropdown-item.btn-custom[data-tipo="MODAL"]');
        if (!btn) return;
        console.log('⚡ custom modal button clicked:', btn.dataset.acao);
        e.preventDefault();
        abrirModal(btn.dataset.acao);
      });

      // Hook para botões customizados do tipo ACAO (executa código JS do campo ACAO)
      document.addEventListener('click', e => {
        // <a> ou <button> com .btn-custom[data-tipo="ACAO"]
        const btn = e.target.closest('.btn-custom[data-tipo="ACAO"]');
        if (!btn) return;

        e.preventDefault();
        try {
          // O código vem no atributo data-acao (campo ACAO da MENUBOTOES)
          // Podes usar RECORD_STAMP, TABLE_NAME, etc, aqui.
          // Usa new Function para correr o código JS
          const fn = new Function('TABLE_NAME', 'RECORD_STAMP', btn.dataset.acao);
          fn(window.TABLE_NAME, window.RECORD_STAMP);
        } catch (err) {
          alert("Erro ao executar ação: " + err.message);
        }
      });      

    // Voltar
    document.getElementById('btnBack')?.addEventListener('click', () => {
      if (RETURN_URL) {
        window.location.href = RETURN_URL;
      } else {
        history.back();
      }
    });


    const userPerms = window.USER_PERMS[TABLE_NAME] || {};

    // Se for edição (RECORD_STAMP), valida `editar` e `eliminar`
    if (RECORD_STAMP) {
    if (!userPerms.editar) {
        // desabilita todos os controles
        form.querySelectorAll('input, select, textarea').forEach(el => el.disabled = true);
        document.getElementById('btnSave').style.display = 'none';
    }
    if (!userPerms.eliminar) {
        document.getElementById('btnDelete').style.display = 'none';
    }
    } else {
    // se for criação, valida `inserir`
    if (!userPerms.inserir) {
        document.getElementById('btnSave').style.display = 'none';
    }
    }

  // ===============================
// 9. SUBMISSÃO DO FORMULÁRIO
// ===============================

// 7. Submit com tratamento de erros
  form.addEventListener('submit', async e => {
    e.preventDefault();

    // ✂️ Limpar espaços dos campos de texto
    form.querySelectorAll('input, textarea').forEach(el => {
      const tipo = el.type?.toLowerCase();
      if (tipo !== 'checkbox' && typeof el.value === 'string') {
        el.value = el.value.trim();
      }
    });

    if (!form.checkValidity()) {
      form.classList.add('was-validated');
      showDynamicFormToast('Existem campos obrigat?rios por preencher.', 'warning');
      return;
    }

    const data = {};
    new FormData(form).forEach((v, k) => data[k] = v);
    // BIT para booleano
    form.querySelectorAll('input[type="checkbox"]').forEach(cb => data[cb.name] = cb.checked);
    // Decimais usam vírgula mas o backend espera ponto
    form.querySelectorAll('input[data-decimal="true"]').forEach(input => {
      data[input.name] = toServerDecimal(
        input.value,
        getDecimalPlacesForInput(input)
      );
    });
    // Datas para ISO
    form.querySelectorAll('.flatpickr-date').forEach(input => {
      const raw = input.value.trim();
      if (raw) {
        const [d,m,y] = raw.split(/\D+/);
        if (d && m && y) data[input.name] = `${y.padStart(4,'0')}-${m.padStart(2,'0')}-${d.padStart(2,'0')}`;
      }
    });
    const url = `/generic/api/${TABLE_NAME}${RECORD_STAMP ? `/${RECORD_STAMP}` : ''}`;
    const method = RECORD_STAMP ? 'PUT' : 'POST';
    try {
      const res = await fetch(url, { method, headers:{'Content-Type':'application/json'}, body: JSON.stringify(data) });
      if (!res.ok) {
        let msg = '';
        const rawBody = await res.text();
        if (rawBody) {
          try {
            const err = JSON.parse(rawBody);
            msg = err.error || JSON.stringify(err);
          } catch {
            msg = rawBody;
          }
        }
        if (!msg) msg = `HTTP ${res.status}`;
        showDynamicFormToast(`Erro ao gravar: ${msg}`, 'danger');
        return;
      }
      queueDynamicFormToast(RECORD_STAMP ? 'Registo gravado.' : 'Registo criado.', 'success');
      window.location.href = RETURN_URL;
    } catch (net) {
      showDynamicFormToast(`Erro de rede: ${net.message}`, 'danger');
    }
  });


  aplicarCondicoesDeVisibilidade();

  // 8. Cursor no final
  form.querySelectorAll('input[type="text"],input[type="number"],input[type="time"]').forEach(i =>
    i.addEventListener('focus', () => { const v = i.value; i.value = ''; i.value = v; })  
  );
})();

// static/js/dynamic_form.js
// Formulário genérico com tratamento de COMBO, valores por defeito e submissão.

let currentModalName = null;

// Debug: mostra o RECORD_STAMP global
console.log('🚀 dynamic_form.js carregado - RECORD_STAMP global:', window.RECORD_STAMP);

// Abre o modal e carrega campos dinâmicos
function abrirModal(nomeModal) {
  currentModalName = nomeModal;
  fetch(`/generic/api/modal/${nomeModal}`)
    .then(res => res.json())
    .then(data => {
      if (!data.success) {
        alert('Erro ao carregar modal: ' + data.message);
        return;
      }
      console.log('⚙️ Dados do modal:', data);
      // Ajusta título do modal
      const titleEl = document.getElementById('genericModalLabel');
      if (titleEl) titleEl.innerText = data.titulo || 'Ação';
      // Desenha campos
      renderModalFields(data.campos || []);
      // Inicia Flatpickr nos campos de data
      if (window.flatpickr) {
        document.querySelectorAll('#modalBody .flatpickr-date').forEach(el =>
          flatpickr(el, { dateFormat: 'd-m-Y', allowInput: true })
        );
      }
      // Exibe o modal
      const modalEl = document.getElementById('genericModal');
      new bootstrap.Modal(modalEl).show();
    })
    .catch(err => {
      console.error('Erro ao carregar modal:', err);
      alert('Erro ao carregar o formulário do modal');
});
}

// static/js/dynamic_form.js

// ===============================
// 10. MODAIS CUSTOMIZADOS
// ===============================

// ─── Hooks para os botões customizados de MODAL ───
document.addEventListener('click', e => {
  // procura o <a> ou <button> mais perto que tenha classe btn-custom e data-tipo="MODAL"
  const btn = e.target.closest('.btn-custom[data-tipo="MODAL"]');
  if (!btn) return;

  e.preventDefault();
  // data-acao contém o nome do modal
  const nomeModal = btn.dataset.acao;
  abrirModal(nomeModal);
});

// at the very top, before any form-building logic
function criarInputPadrao(campo, valorAtual = '') {
  const input = document.createElement('input');
  input.type = 'text';
  input.className = 'sz_input';
  input.value = valorAtual;
  return input;
}

function renderCampo(campo, valorAtual = '') {
  const div = document.createElement('div');
  div.className = 'col-12 mb-3 sz_field';
  const label = document.createElement('label');
  label.className = 'sz_label';
  label.textContent = campo.descricao || campo.name;
  div.appendChild(label);

  let input;
  const tipo = campo.tipo.toUpperCase();

  if (tipo === 'COLOR') {
    input = document.createElement('input');
    input.type = 'color';
    input.className = 'sz_input';
    input.value = valorAtual || '#000000';
  }
  else if (tipo === 'LINK') {
    const wrapper = document.createElement('div');
    wrapper.className = 'sz_inline sz_gap_1 sz_w_full';
    input = document.createElement('input');
    input.type = 'text';
    input.className = 'sz_input';
    input.style.flex = '1 1 auto';
    input.placeholder = 'https://...';
    input.value = valorAtual || '';
    const button = document.createElement('a');
    button.className = 'sz_button sz_button_ghost';
    button.target = '_blank';
    button.href   = input.value || '#';
    button.innerHTML = '<i class="fa fa-link"></i>';
    input.addEventListener('input', () => button.href = input.value);
    wrapper.appendChild(input);
    wrapper.appendChild(button);
    div.appendChild(wrapper);
    // skip the `div.appendChild(input)` below
    input.dataset.campo = campo.name;
    return div;
  }
  else {
    input = criarInputPadrao(campo, valorAtual);
  }

  input.dataset.campo = campo.name;
  div.appendChild(input);
  return div;
}


// Gera os elementos de campo dentro do modal
function renderModalFields(campos) {
  const container = document.getElementById('modalBody');
  if (!container) {
    console.error('Container #modalBody nao encontrado!');
    return;
  }

  container.innerHTML = '';

  campos
    .sort((a, b) => a.ORDEM - b.ORDEM)
    .forEach(col => {
      const wrapper = document.createElement('div');
      wrapper.className = 'sz_field';

      let input;
      const tipo = (col.TIPO || '').toUpperCase();

      if (tipo === 'BIT') {
        const checkLabel = document.createElement('label');
        checkLabel.className = 'sz_checkbox';
        checkLabel.setAttribute('for', col.CAMPO);

        input = document.createElement('input');
        input.type = 'checkbox';
        input.name = col.CAMPO;
        input.id = col.CAMPO;

        const text = document.createElement('span');
        text.textContent = col.LABEL || col.CAMPO;
        checkLabel.append(input, text);
        wrapper.appendChild(checkLabel);
      } else {
        const label = document.createElement('label');
        label.setAttribute('for', col.CAMPO);
        label.className = 'sz_label';
        label.textContent = col.LABEL || col.CAMPO;
        wrapper.appendChild(label);

        if (tipo === 'COMBO') {
          input = document.createElement('select');
          input.className = 'sz_select';
          input.innerHTML = '<option value="">---</option>';
          if (Array.isArray(col.OPCOES)) {
            col.OPCOES.forEach(opt => {
              const o = document.createElement('option');
              o.value = opt[0];
              o.textContent = opt[1];
              input.appendChild(o);
            });
          }
        } else if (tipo === 'MEMO') {
          input = document.createElement('textarea');
          input.className = 'sz_textarea';
          input.rows = 3;
        } else {
          input = document.createElement('input');
          input.className = 'sz_input';

          switch (tipo) {
            case 'DATE':
              input.type = 'text';
              input.classList.remove('sz_input');
              input.classList.add('sz_date', 'flatpickr-date');
              break;
            case 'HOUR':
              input.type = 'time';
              break;
            case 'INT':
              input.type = 'number';
              input.step = '1';
              break;
            case 'DECIMAL':
              input.type = 'number';
              input.step = '0.01';
              break;
            case 'COLOR':
              input.type = 'color';
              break;
            default:
              input.type = 'text';
          }
        }

        input.name = col.CAMPO;
        input.id = col.CAMPO;
        wrapper.appendChild(input);
      }

      if (col.VALORDEFAULT) {
        let def = col.VALORDEFAULT.trim();
        if (/^\{\s*RECORD_STAMP\s*\}$/.test(def)) {
          def = window.RECORD_STAMP || '';
        } else if (/^".*"$/.test(def)) {
          def = def.slice(1, -1);
        }

        if (input.type === 'checkbox') {
          input.checked = ['1', 'true', 'True'].includes(def);
        } else {
          input.value = def;
        }
      }

      container.appendChild(wrapper);
    });
}

// Submete o modal ao servidor
function gravarModal() {
  const container = document.getElementById('modalBody');
  if (!container) return console.error('❌ Container #modalBody não encontrado');

  const inputs = container.querySelectorAll('input[name], select[name], textarea[name]');
  const dados = { __modal__: currentModalName };

  inputs.forEach(i => {
    if (i.type === 'checkbox') {
      dados[i.name] = i.checked ? 1 : 0;
    } else {
      let val = i.value.trim();

      // Se for campo de data (flatpickr-date), converte dd.mm.YYYY → YYYY-MM-DD
      if (i.classList.contains('flatpickr-date') && val) {
        const [d, m, y] = val.split(/\D+/);
        if (d && m && y) {
          val = `${y.padStart(4,'0')}-${m.padStart(2,'0')}-${d.padStart(2,'0')}`;
        }
      }

      dados[i.name] = val;
    }
  });

  console.log('📤 Enviando dados modal:', dados);
  fetch('/generic/api/modal/gravar', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(dados)
  })
  .then(res => res.json())
  .then(data => {
    if (data.success) {
      const modalEl = document.getElementById('genericModal');
      bootstrap.Modal.getInstance(modalEl).hide();
      document.querySelectorAll('.modal-backdrop').forEach(b => b.remove());
    } else {
      alert('Erro ao gravar modal: ' + data.error);
    }
  })
  .catch(e => {
    console.error('Erro ao gravar modal:', e);
    alert('Erro ao gravar modal. Veja console.');
  });
}

// Expõe no global para onclick inline (se precisares)
window.abrirModal = abrirModal;
window.gravarModal = gravarModal;

// ===============================
// 11. EVENTOS GERAIS
// ===============================

// Liga todos os dropdown-items que abrem modal
document.querySelectorAll('.dropdown-item.btn-custom[data-tipo="MODAL"]')
  .forEach(el => {
    el.addEventListener('click', e => {
      e.preventDefault();
      abrirModal(el.dataset.acao);
    });
  });



