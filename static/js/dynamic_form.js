// static/js/dynamic_form.js
function toDynamicAppRelativeUrl(value, fallback = '') {
  const raw = String(value || '').trim();
  if (!raw) return fallback;
  if (/^(javascript|data|vbscript):/i.test(raw)) return fallback;
  if (/^https?:\/\//i.test(raw) || raw.startsWith('//')) {
    try {
      const parsed = new URL(raw.startsWith('//') ? `${window.location.protocol}${raw}` : raw);
      return `${parsed.pathname}${parsed.search}${parsed.hash}` || fallback;
    } catch (_) {
      return fallback;
    }
  }
  return raw;
}

function navigateDynamic(url, fallback = '/') {
  window.location.href = toDynamicAppRelativeUrl(url, fallback);
}

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
  const tableFieldTargetValues = {};

  // ─── DEBUG: find all custom‐action buttons ───
  console.log('modal triggers encontrados:', document.querySelectorAll('.btn-custom'));

  const TABLE_NAME   = window.TABLE_NAME;
  const TABLE_NAME_UPPER = String(TABLE_NAME || '').toUpperCase();
  const RECORD_STAMP = window.RECORD_STAMP;
  const isAdminUser  = window.IS_ADMIN_USER;
  const MENU_STAMP = String(window.MENU_STAMP || '').trim();
  const useExactWidths = Boolean(window.DYNAMIC_FORM_EXACT_WIDTHS);
  const DEV_MODE = window.DEV_MODE || false;
  const isPartnerForm = ['CL', 'FL'].includes(TABLE_NAME_UPPER);
  const partnerApiBase = `/generic/api/${String(TABLE_NAME || '').toLowerCase()}`;

  console.log('[dynamic_form.js] TABLE_NAME:', TABLE_NAME);
  console.log('[dynamic_form.js] exact widths:', useExactWidths);

  // ─── Guardar para onde voltar + que detalhe ancorar ───
  // Captura o return_to (e detail_* se vierem) da URL
  const urlParams = new URLSearchParams(window.location.search);

  // Este form é acedido a partir de outro? Ou diretamente?
  const returnTo = urlParams.get('return_to');
  const RETURN_URL = returnTo && returnTo.trim() !== ''
    ? toDynamicAppRelativeUrl(returnTo, `/generic/view/${TABLE_NAME}/`)
    : `/generic/view/${TABLE_NAME}/`;

  console.log('📍 RETURN_URL =', RETURN_URL);


  const DETAIL_TAB = urlParams.get('detail_table')|| null;
  const DETAIL_PK  = urlParams.get('detail_pk')   || null;

    
// ===============================
// 2. CONSTRUÇÃO DO FORMULÁRIO
// ===============================

  const describeParams = new URLSearchParams({ action: 'describe' });
  if (MENU_STAMP) describeParams.set('menustamp', MENU_STAMP);
  describeParams.set('include_screen_meta', '1');
  const res  = await fetch(`/generic/api/${TABLE_NAME}?${describeParams.toString()}`);
  const describePayload = await res.json();
  const cols = Array.isArray(describePayload)
    ? describePayload
    : Array.isArray(describePayload?.columns)
    ? describePayload.columns
    : [];
  const screenMeta = !Array.isArray(describePayload) && describePayload && typeof describePayload === 'object'
    ? (describePayload.screen && typeof describePayload.screen === 'object' ? describePayload.screen : {})
    : {};

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

  const layoutWidthUnits = useExactWidths ? (isMobile ? 40 : 100) : null;
  const isColumnVisible = col => !(col && (col.visivel === false || Number(col.visivel) === 0));
  const isUiOnlyColumn = col => !!(col && (col.ui_only || col.is_menu_object));
  const getColumnProperties = col => {
    if (!col || typeof col !== 'object') return {};
    if (col.propriedades && typeof col.propriedades === 'object') return col.propriedades;
    if (col.properties && typeof col.properties === 'object') return col.properties;
    if (col.PROPRIEDADES && typeof col.PROPRIEDADES === 'object') return col.PROPRIEDADES;
    return {};
  };
  const setFormStateValue = (key, value) => {
    const rawKey = String(key || '').trim();
    if (!rawKey) return;
    formState[rawKey] = value;
    formState[rawKey.toUpperCase()] = value;
  };
  const normalizeBoundVariableName = value => String(value || '')
    .trim()
    .toUpperCase()
    .replace(/[^A-Z0-9_]+/g, '_')
    .replace(/_+/g, '_')
    .replace(/^_+|_+$/g, '')
    .slice(0, 60);
  const getBoundVariableName = col => normalizeBoundVariableName(getColumnProperties(col).variable_name);
  const hasBoundVariable = col => !!getBoundVariableName(col);
  const getBoundVariableDefault = col => {
    const props = getColumnProperties(col);
    return props.variable_default === undefined || props.variable_default === null
      ? ''
      : String(props.variable_default).trim();
  };
  const isButtonEnabled = col => {
    const props = getColumnProperties(col);
    if (!Object.prototype.hasOwnProperty.call(props, 'enabled')) return true;
    return isTruthyLike(props.enabled);
  };
  const getButtonClickAction = col => String(getColumnProperties(col).click_action || '').trim();
  const getButtonClickFlow = col => {
    const props = getColumnProperties(col);
    const events = props && typeof props.events === 'object' && props.events ? props.events : {};
    const flow = events && typeof events.click === 'object' && events.click ? events.click : null;
    return flow && Array.isArray(flow.lines) ? flow : null;
  };
  const getScreenEvents = () => (screenMeta && typeof screenMeta.events === 'object' && screenMeta.events) ? screenMeta.events : {};
  const getScreenEventFlow = eventName => {
    const key = String(eventName || '').trim().toLowerCase();
    const flow = key ? getScreenEvents()[key] : null;
    return flow && typeof flow === 'object' && Array.isArray(flow.lines) ? flow : null;
  };
  const hasScreenEventFlow = eventName => hasMeaningfulVisualEventFlow(getScreenEventFlow(eventName));
  const isTruthyLike = value => {
    if (typeof value === 'boolean') return value;
    const raw = String(value ?? '').trim().toLowerCase();
    return ['1', 'true', 'yes', 'sim', 'on'].includes(raw);
  };
  const toDisplayDateValue = value => {
    const raw = String(value ?? '').trim();
    if (!raw) return '';
    if (/^\d{4}-\d{2}-\d{2}/.test(raw)) {
      const [y, m, d] = raw.slice(0, 10).split('-');
      return `${d}.${m}.${y}`;
    }
    const parts = raw.split(/[./-]/).filter(Boolean);
    if (parts.length === 3) {
      if (parts[0].length === 4) return `${parts[2].padStart(2, '0')}.${parts[1].padStart(2, '0')}.${parts[0]}`;
      return `${parts[0].padStart(2, '0')}.${parts[1].padStart(2, '0')}.${parts[2].padStart(4, '0')}`;
    }
    return raw;
  };
  const toColorValue = value => {
    const raw = String(value ?? '').trim();
    if (!raw) return '#000000';
    const normalized = raw.startsWith('#') ? raw : `#${raw}`;
    return /^#[0-9a-fA-F]{6}$/.test(normalized) ? normalized : '#000000';
  };
  const boundVariableInputs = new Map();
  const boundVariableState = {};
  const isEditableBoundObject = col => hasBoundVariable(col) && !col.readonly && !['SPACE', 'BUTTON', 'TABLE', 'TABLE_FIELD'].includes((col.tipo || '').toUpperCase());
  const applyBoundValueToInput = (col, input, rawValue) => {
    if (!input) return;
    if (input.type === 'checkbox') {
      input.checked = isTruthyLike(rawValue);
      return;
    }
    if (input.type === 'color') {
      input.value = toColorValue(rawValue);
      return;
    }
    if (input.classList.contains('flatpickr-date')) {
      input.value = toDisplayDateValue(rawValue);
      return;
    }
    if (isDecimalInput(input)) {
      input.value = toDisplayDecimal(rawValue, getDecimalPlacesForInput(input));
      return;
    }
    input.value = rawValue === undefined || rawValue === null ? '' : String(rawValue);
  };
  const syncBoundVariableValue = (variableName, nextValue, { source = null } = {}) => {
    const key = normalizeBoundVariableName(variableName);
    if (!key) return;
    boundVariableState[key] = nextValue;
    const items = boundVariableInputs.get(key) || [];
    items.forEach(({ col, input }) => {
      if (!input) return;
      if (input !== source) {
        applyBoundValueToInput(col, input, nextValue);
      }
      const inputValue = readValueForState(input);
      if (input.name) setFormStateValue(input.name, inputValue);
    });
    setFormStateValue(key, items.length && items[0]?.input ? readValueForState(items[0].input) : nextValue);
  };
  const registerBoundVariableInput = (col, input) => {
    const variableName = getBoundVariableName(col);
    if (!variableName || !input) return false;
    input.dataset.variableName = variableName;
    const items = boundVariableInputs.get(variableName) || [];
    items.push({ col, input });
    boundVariableInputs.set(variableName, items);
    if (!Object.prototype.hasOwnProperty.call(boundVariableState, variableName)) {
      boundVariableState[variableName] = getBoundVariableDefault(col);
    }
    applyBoundValueToInput(col, input, boundVariableState[variableName]);
    const currentValue = readValueForState(input);
    if (input.name) setFormStateValue(input.name, currentValue);
    setFormStateValue(variableName, currentValue);
    return true;
  };
  const bindVariableInputEvents = input => {
    if (!input || !input.dataset?.variableName) return;
    const handler = () => {
      syncBoundVariableValue(input.dataset.variableName, readValueForState(input), { source: input });
      aplicarCondicoesDeVisibilidade();
    };
    input.addEventListener('input', handler);
    input.addEventListener('change', handler);
  };
  const syncAllBoundVariableInputs = () => {
    boundVariableInputs.forEach((items, variableName) => {
      if (!items.length) return;
      const current = Object.prototype.hasOwnProperty.call(boundVariableState, variableName)
        ? boundVariableState[variableName]
        : getBoundVariableDefault(items[0].col);
      syncBoundVariableValue(variableName, current);
    });
  };
  const getLayoutFieldSize = col => {
    const rawValue = Number(isMobile ? col.tam_mobile : col.tam);
    if (Number.isFinite(rawValue) && rawValue > 0) {
      if (!useExactWidths || !Number.isFinite(layoutWidthUnits)) {
        return rawValue;
      }
      return Math.min(rawValue, layoutWidthUnits);
    }
    return useExactWidths ? 5 : 1;
  };


  // 2. Prepara o form
  const form = document.getElementById('editForm');
  const DECIMAL_SEPARATOR = ',';

  function getVisualEventLines(flow) {
    const rawLines = Array.isArray(flow?.lines) ? flow.lines : [];
    return rawLines
      .map(line => {
        const kind = String(line?.kind || line?.type || 'command').trim().toLowerCase() === 'empty'
          ? 'empty'
          : 'command';
        return {
          kind,
          command: kind === 'command'
            ? String(line?.command || line?.id || line?.type || '').trim().toUpperCase()
            : '',
          config: line?.config && typeof line.config === 'object' && !Array.isArray(line.config)
            ? { ...line.config }
            : {},
        };
      })
      .filter(line => line.kind === 'empty' || line.command);
  }

  function hasMeaningfulVisualEventFlow(flow) {
    return getVisualEventLines(flow).some(line => (
      line.kind !== 'empty'
      && !['START', 'ELSE', 'ENDIF', 'ENDWHILE', 'ENDFOR', 'ENDCURSOR_SCAN'].includes(line.command)
    ));
  }

  function normalizePhysicalFieldName(fieldName) {
    const raw = String(fieldName || '').trim();
    if (!raw) return '';
    const normalized = raw
      .split('.')
      .map(part => part.trim().replace(/^\[|\]$/g, ''))
      .filter(Boolean);
    return (normalized[normalized.length - 1] || raw).trim();
  }

  function getFieldInputCandidates(fieldName) {
    const rawName = String(fieldName || '').trim();
    const physicalName = normalizePhysicalFieldName(rawName);
    const names = [...new Set([
      rawName,
      rawName.toUpperCase(),
      rawName.toLowerCase(),
      physicalName,
      physicalName.toUpperCase(),
      physicalName.toLowerCase(),
    ].filter(Boolean))];
    const candidates = [];
    names.forEach(name => {
      const input = camposByName[name];
      if (input && !candidates.includes(input)) candidates.push(input);
    });
    Array.from(form?.elements || []).forEach(input => {
      if (!input?.name) return;
      const inputName = String(input.name || '').trim();
      if (names.includes(inputName) && !candidates.includes(input)) {
        candidates.push(input);
      }
    });
    return candidates;
  }

  function getFieldInputByName(fieldName, { includeUiOnly = true, preferWritable = false } = {}) {
    const candidates = getFieldInputCandidates(fieldName);
    const writable = candidates.find(input => input.dataset?.uiOnly !== 'true' && !input.disabled);
    if (preferWritable || !includeUiOnly) return writable || null;
    return candidates[0] || null;
  }

  function setTableFieldTargetValue(fieldName, nextValue) {
    const targetName = normalizePhysicalFieldName(fieldName);
    if (!targetName) return false;
    tableFieldTargetValues[targetName] = nextValue;
    setFormStateValue(targetName, nextValue);
    return true;
  }

  function clearTableFieldTargetValue(fieldName, { writeEmpty = false } = {}) {
    const targetName = normalizePhysicalFieldName(fieldName);
    if (!targetName) return false;
    if (writeEmpty) {
      tableFieldTargetValues[targetName] = '';
      setFormStateValue(targetName, '');
      return true;
    }
    delete tableFieldTargetValues[targetName];
    return true;
  }

  function getFieldWrapperByName(fieldName) {
    const input = getFieldInputByName(fieldName);
    if (!input?.closest) return null;
    return input.closest('.col-12') || input.closest('.sz_field') || input.closest('.sz_checkbox') || input.closest('.mb-3');
  }

  function getFieldCurrentValue(fieldName) {
    const rawName = String(fieldName || '').trim();
    if (!rawName) return '';
    if (Object.prototype.hasOwnProperty.call(formState, rawName)) return formState[rawName];
    if (Object.prototype.hasOwnProperty.call(formState, rawName.toUpperCase())) return formState[rawName.toUpperCase()];
    const input = getFieldInputByName(rawName);
    return input ? readValueForState(input) : '';
  }

  function deepReadValue(source, path) {
    if (!path) return source;
    return String(path)
      .split('.')
      .filter(Boolean)
      .reduce((acc, key) => {
        if (acc === undefined || acc === null) return undefined;
        if (Array.isArray(acc) && /^\d+$/.test(key)) return acc[Number(key)];
        return acc[key];
      }, source);
  }

  function storeRuntimeValue(runtime, key, value) {
    const rawKey = String(key || '').trim();
    if (!rawKey) return value;
    runtime.vars[rawKey] = value;
    runtime.vars[rawKey.toUpperCase()] = value;
    setFormStateValue(rawKey, value);
    return value;
  }

  function readRuntimeValue(runtime, value) {
    if (value === undefined || value === null) return '';
    if (typeof value !== 'string') return value;
    const raw = String(value).trim();
    if (!raw) return '';
    if ((raw.startsWith('"') && raw.endsWith('"')) || (raw.startsWith("'") && raw.endsWith("'"))) {
      return raw.slice(1, -1);
    }
    if (/^-?\d+(?:[.,]\d+)?$/.test(raw)) {
      return Number(raw.replace(',', '.'));
    }
    if (/^(true|false)$/i.test(raw)) {
      return /^true$/i.test(raw);
    }
    if (/^(yes|no|sim|nao|não|on|off)$/i.test(raw)) {
      return isTruthyLike(raw);
    }
    if (Object.prototype.hasOwnProperty.call(runtime.vars, raw)) return runtime.vars[raw];
    if (Object.prototype.hasOwnProperty.call(runtime.vars, raw.toUpperCase())) return runtime.vars[raw.toUpperCase()];
    if (raw.includes('.')) {
      const [head, ...tail] = raw.split('.');
      const path = tail.join('.');
      const activeCursorRow = getActiveCursorScanRow(runtime, head);
      if (activeCursorRow && path) return deepReadValue(activeCursorRow, path);
      if (Object.prototype.hasOwnProperty.call(runtime.vars, head)) return deepReadValue(runtime.vars[head], path);
      if (Object.prototype.hasOwnProperty.call(runtime.vars, head.toUpperCase())) return deepReadValue(runtime.vars[head.toUpperCase()], path);
      if (Object.prototype.hasOwnProperty.call(formState, head)) return deepReadValue(formState[head], path);
      if (Object.prototype.hasOwnProperty.call(formState, head.toUpperCase())) return deepReadValue(formState[head.toUpperCase()], path);
    }
    if (Object.prototype.hasOwnProperty.call(formState, raw)) return formState[raw];
    if (Object.prototype.hasOwnProperty.call(formState, raw.toUpperCase())) return formState[raw.toUpperCase()];
    if (raw === 'TABLE_NAME') return TABLE_NAME;
    if (raw === 'RECORD_STAMP') return RECORD_STAMP;
    if (raw === 'MENU_STAMP') return MENU_STAMP;
    if (raw === 'USER' || raw === 'CURRENT_USER') return window.CURRENT_USER || window.USERNAME || '';
    if (raw === 'FEID') return window.FEID || window.EMPRESA_FEID || '';
    const input = getFieldInputByName(raw);
    if (input) return readValueForState(input);
    return raw;
  }

  function evaluateRuntimeExpression(runtime, expr) {
    const rawExpr = String(expr || '').trim();
    if (!rawExpr) return false;
    const scope = {
      TABLE_NAME,
      RECORD_STAMP,
      MENU_STAMP,
      USER: window.CURRENT_USER || window.USERNAME || '',
      CURRENT_USER: window.CURRENT_USER || window.USERNAME || '',
      FEID: window.FEID || window.EMPRESA_FEID || '',
      ...formState,
      ...runtime.vars,
    };
    const keys = Object.keys(scope).filter(key => /^[A-Za-z_$][A-Za-z0-9_$]*$/.test(key));
    const values = keys.map(key => scope[key]);
    try {
      const fn = new Function(...keys, `'use strict'; return (${rawExpr});`);
      return !!fn(...values);
    } catch (_) {
      return !!readRuntimeValue(runtime, rawExpr);
    }
  }

  function normalizeRuntimeComparableValue(value) {
    if (value === undefined || value === null) return value;
    if (typeof value === 'string') {
      const raw = value.trim();
      if (!raw) return '';
      if (/^-?\d+(?:[.,]\d+)?$/.test(raw)) {
        return Number(raw.replace(',', '.'));
      }
      if (/^(true|false)$/i.test(raw)) {
        return /^true$/i.test(raw);
      }
      if (/^(yes|no|sim|nao|nÃ£o|on|off)$/i.test(raw)) {
        return isTruthyLike(raw);
      }
      return raw;
    }
    return value;
  }

  function isVisualEventCancelResult(value) {
    if (value === false || value === 0) return true;
    if (typeof value === 'string') {
      const raw = value.trim().toLowerCase();
      return ['false', '0', 'no', 'nao', 'não', 'off'].includes(raw);
    }
    return false;
  }

  function normalizeToList(value) {
    if (Array.isArray(value)) return value;
    if (value === undefined || value === null || value === '') return [];
    return [value];
  }

  function ensureVisualEventRuntime(runtime) {
    if (!runtime || typeof runtime !== 'object') return { vars: {}, cursors: {}, cursorScanStack: [] };
    if (!runtime.vars || typeof runtime.vars !== 'object') runtime.vars = {};
    if (!runtime.cursors || typeof runtime.cursors !== 'object') runtime.cursors = {};
    if (!Array.isArray(runtime.cursorScanStack)) runtime.cursorScanStack = [];
    return runtime;
  }

  function getCursorRuntimeKey(cursorName) {
    return String(cursorName || '').trim().toUpperCase();
  }

  function normalizeCursorSchemaEntry(entry = {}) {
    const name = String(entry?.name || '')
      .trim()
      .toUpperCase()
      .replace(/[^A-Z0-9_]+/g, '_')
      .replace(/_+/g, '_')
      .replace(/^_+|_+$/g, '')
      .slice(0, 60);
    const allowed = ['TEXT', 'MEMO', 'INT', 'DECIMAL', 'DATE', 'BOOL', 'JSON'];
    const type = String(entry?.type || 'TEXT').trim().toUpperCase();
    return {
      name,
      type: allowed.includes(type) ? type : 'TEXT',
    };
  }

  function normalizeCursorSchema(schema = []) {
    return (Array.isArray(schema) ? schema : [])
      .map(normalizeCursorSchemaEntry)
      .filter(entry => entry.name);
  }

  function detectCursorFieldType(value) {
    if (value === undefined || value === null || value === '') return 'TEXT';
    if (typeof value === 'boolean') return 'BOOL';
    if (typeof value === 'number') return Number.isInteger(value) ? 'INT' : 'DECIMAL';
    if (value instanceof Date) return 'DATE';
    if (Array.isArray(value) || (value && typeof value === 'object')) return 'JSON';
    const raw = String(value).trim();
    if (!raw) return 'TEXT';
    if (/^(true|false|yes|no|sim|nao|não|on|off)$/i.test(raw)) return 'BOOL';
    if (/^-?\d+$/.test(raw)) return 'INT';
    if (/^-?\d+(?:[.,]\d+)?$/.test(raw)) return 'DECIMAL';
    if (/^\d{4}-\d{2}-\d{2}/.test(raw)) return 'DATE';
    if ((raw.startsWith('{') && raw.endsWith('}')) || (raw.startsWith('[') && raw.endsWith(']'))) return 'JSON';
    return 'TEXT';
  }

  function coerceCursorValue(value, type = 'TEXT') {
    const normalizedType = String(type || 'TEXT').trim().toUpperCase();
    if (value === undefined || value === null || value === '') {
      if (['TEXT', 'MEMO', 'DATE'].includes(normalizedType)) return '';
      return null;
    }
    if (normalizedType === 'BOOL') return isTruthyLike(value);
    if (normalizedType === 'INT') {
      const parsed = Number.parseInt(String(value).replace(',', '.'), 10);
      return Number.isFinite(parsed) ? parsed : null;
    }
    if (normalizedType === 'DECIMAL') {
      const parsed = Number(String(value).replace(',', '.'));
      return Number.isFinite(parsed) ? parsed : null;
    }
    if (normalizedType === 'JSON') {
      if (typeof value === 'object') return value;
      const raw = String(value).trim();
      if (!raw) return null;
      try {
        return JSON.parse(raw);
      } catch (_) {
        return raw;
      }
    }
    return String(value);
  }

  function parseCursorSourceValue(value) {
    if (value === undefined || value === null || value === '') return null;
    if (typeof value === 'object') return value;
    const raw = String(value).trim();
    if (!raw) return null;
    if ((raw.startsWith('{') && raw.endsWith('}')) || (raw.startsWith('[') && raw.endsWith(']'))) {
      try {
        return JSON.parse(raw);
      } catch (_) {
        return raw;
      }
    }
    return raw;
  }

  function createBlankCursorRow(cursor) {
    const row = {};
    normalizeCursorSchema(cursor?.schema || []).forEach((field) => {
      row[field.name] = coerceCursorValue('', field.type);
    });
    return row;
  }

  function getValueFromObjectCaseInsensitive(source, key) {
    if (!source || typeof source !== 'object') return undefined;
    if (Object.prototype.hasOwnProperty.call(source, key)) return source[key];
    const upperKey = String(key || '').trim().toUpperCase();
    const foundKey = Object.keys(source).find((item) => String(item || '').trim().toUpperCase() === upperKey);
    return foundKey ? source[foundKey] : undefined;
  }

  function materializeCursorRow(cursor, sourceValue) {
    const parsedSource = parseCursorSourceValue(sourceValue);
    const schema = normalizeCursorSchema(cursor?.schema || []);
    if (!schema.length) {
      if (parsedSource && typeof parsedSource === 'object' && !Array.isArray(parsedSource)) {
        return { ...parsedSource };
      }
      return {};
    }
    const row = createBlankCursorRow(cursor);
    if (parsedSource && typeof parsedSource === 'object' && !Array.isArray(parsedSource)) {
      schema.forEach((field) => {
        row[field.name] = coerceCursorValue(getValueFromObjectCaseInsensitive(parsedSource, field.name), field.type);
      });
      return row;
    }
    if (schema.length === 1 && parsedSource !== null) {
      row[schema[0].name] = coerceCursorValue(parsedSource, schema[0].type);
    }
    return row;
  }

  function inferCursorSchemaFromRows(rows = [], columns = []) {
    const columnNames = Array.isArray(columns) && columns.length
      ? columns
      : Array.from(new Set((Array.isArray(rows) ? rows : []).flatMap((row) => Object.keys(row || {}))));
    return columnNames.map((name) => {
      const sampleRow = (Array.isArray(rows) ? rows : []).find((row) => getValueFromObjectCaseInsensitive(row, name) !== undefined && getValueFromObjectCaseInsensitive(row, name) !== null);
      const sampleValue = sampleRow ? getValueFromObjectCaseInsensitive(sampleRow, name) : undefined;
      return normalizeCursorSchemaEntry({
        name,
        type: detectCursorFieldType(sampleValue),
      });
    }).filter((entry) => entry.name);
  }

  function setRuntimeCursor(runtime, cursorName, cursor) {
    ensureVisualEventRuntime(runtime);
    const key = getCursorRuntimeKey(cursorName);
    if (!key) return null;
    runtime.cursors[key] = {
      name: String(cursorName || '').trim(),
      schema: normalizeCursorSchema(cursor?.schema || []),
      rows: Array.isArray(cursor?.rows) ? cursor.rows : [],
    };
    runtime.vars[cursorName] = runtime.cursors[key].rows;
    runtime.vars[key] = runtime.cursors[key].rows;
    return runtime.cursors[key];
  }

  function getRuntimeCursor(runtime, cursorName) {
    ensureVisualEventRuntime(runtime);
    const key = getCursorRuntimeKey(cursorName);
    if (!key) return null;
    return runtime.cursors[key] || null;
  }

  function clearRuntimeCursor(runtime, cursorName) {
    ensureVisualEventRuntime(runtime);
    const key = getCursorRuntimeKey(cursorName);
    if (!key) return;
    delete runtime.cursors[key];
    delete runtime.vars[cursorName];
    delete runtime.vars[key];
  }

  function getActiveCursorScanContext(runtime, cursorName = '') {
    ensureVisualEventRuntime(runtime);
    const key = getCursorRuntimeKey(cursorName);
    for (let index = runtime.cursorScanStack.length - 1; index >= 0; index -= 1) {
      const item = runtime.cursorScanStack[index];
      if (!key || item.cursorKey === key) return item;
    }
    return null;
  }

  function getActiveCursorScanRow(runtime, cursorName = '') {
    const context = getActiveCursorScanContext(runtime, cursorName);
    if (!context) return null;
    const cursor = runtime?.cursors?.[context.cursorKey];
    if (!cursor || !Array.isArray(cursor.rows)) return null;
    return cursor.rows[context.index] || null;
  }

  function syncCursorDeleteWithScanStack(runtime, cursorName, deletedIndex) {
    ensureVisualEventRuntime(runtime);
    const key = getCursorRuntimeKey(cursorName);
    runtime.cursorScanStack.forEach((item) => {
      if (item.cursorKey !== key) return;
      if (item.index > deletedIndex) item.index -= 1;
      if (item.index === deletedIndex) item.deletedCurrent = true;
    });
  }

  function resolveCursorRowIndex(runtime, cursorName, rowRef) {
    const cursor = getRuntimeCursor(runtime, cursorName);
    if (!cursor) return -1;
    const resolved = rowRef === undefined || rowRef === null || rowRef === ''
      ? ''
      : readRuntimeValue(runtime, rowRef);
    if (resolved === '' || resolved === undefined || resolved === null) {
      const context = getActiveCursorScanContext(runtime, cursorName);
      return context ? context.index : -1;
    }
    if (typeof resolved === 'number' && Number.isFinite(resolved)) {
      return Math.max(0, Math.trunc(resolved));
    }
    if (typeof resolved === 'string' && /^\d+$/.test(resolved.trim())) {
      return Number(resolved.trim());
    }
    if (typeof resolved === 'object') {
      return cursor.rows.findIndex((row) => row === resolved);
    }
    return -1;
  }

  function serializeCursorSqlParamValue(value) {
    if (value === undefined) return undefined;
    if (value === null) return null;
    if (typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean') return value;
    if (value instanceof Date) return value.toISOString();
    try {
      return JSON.stringify(value);
    } catch (_) {
      return String(value);
    }
  }

  function buildCursorSqlParams(runtime) {
    ensureVisualEventRuntime(runtime);
    const params = {};
    const assignValues = (source) => {
      Object.entries(source || {}).forEach(([key, value]) => {
        if (!/^[A-Za-z_][A-Za-z0-9_]*$/.test(String(key || ''))) return;
        const normalized = serializeCursorSqlParamValue(value);
        if (normalized === undefined) return;
        params[key] = normalized;
      });
    };
    assignValues(formState);
    assignValues(runtime.vars);
    params.TABLE_NAME = TABLE_NAME;
    params.RECORD_STAMP = RECORD_STAMP;
    params.MENU_STAMP = MENU_STAMP;
    params.CURRENT_USER = window.CURRENT_USER || window.USERNAME || '';
    params.USER = window.CURRENT_USER || window.USERNAME || '';
    params.FEID = window.FEID || window.EMPRESA_FEID || '';
    return params;
  }

  async function runCursorSqlQuery(runtime, sqlQuery) {
    const response = await fetch('/generic/api/event/cursor_query', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        table_name: TABLE_NAME,
        menustamp: MENU_STAMP,
        sql: sqlQuery,
        params: buildCursorSqlParams(runtime),
      }),
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok || data?.success === false) {
      throw new Error(data?.error || 'Nao foi possivel executar a query do cursor.');
    }
    return {
      rows: Array.isArray(data?.rows) ? data.rows : [],
      columns: Array.isArray(data?.columns) ? data.columns : [],
    };
  }

  function updateFieldValue(fieldName, nextValue, { preferWritable = false } = {}) {
    const input = getFieldInputByName(fieldName, { preferWritable });
    if (!input) return false;
    if (input.type === 'checkbox') {
      input.checked = isTruthyLike(nextValue);
    } else if (input.type === 'color') {
      input.value = toColorValue(nextValue);
    } else if (isDecimalInput(input)) {
      input.value = toDisplayDecimal(nextValue, getDecimalPlacesForInput(input));
    } else {
      input.value = nextValue === undefined || nextValue === null ? '' : String(nextValue);
    }
    const normalizedValue = readValueForState(input);
    if (input.name) setFormStateValue(input.name, normalizedValue);
    if (input.dataset?.variableName) {
      syncBoundVariableValue(input.dataset.variableName, normalizedValue, { source: input });
    }
    input.dispatchEvent(new Event('input', { bubbles: true }));
    input.dispatchEvent(new Event('change', { bubbles: true }));
    aplicarCondicoesDeVisibilidade();
    return true;
  }

  async function showVisualMessage(message) {
    const text = String(message ?? '').trim();
    if (typeof window.szAlert === 'function') {
      await window.szAlert(text, { title: 'Mensagem' });
      return;
    }
    showDynamicFormToast(text || 'Mensagem', 'info');
  }

  async function showVisualConfirm(message) {
    const text = String(message ?? '').trim();
    if (typeof window.szConfirm === 'function') {
      return !!(await window.szConfirm(text, { title: 'Confirmar' }));
    }
    return window.confirm(text);
  }

  function findIfMarkers(lines, startIndex, endExclusive = lines.length) {
    let depth = 0;
    let elseIndex = -1;
    for (let i = startIndex + 1; i < endExclusive; i += 1) {
      const command = String(lines[i]?.command || '').trim().toUpperCase();
      if (command === 'IF') {
        depth += 1;
        continue;
      }
      if (command === 'ENDIF') {
        if (depth === 0) {
          return { elseIndex, endIndex: i };
        }
        depth -= 1;
        continue;
      }
      if (command === 'ELSE' && depth === 0 && elseIndex < 0) {
        elseIndex = i;
      }
    }
    return { elseIndex, endIndex: endExclusive };
  }

  function findBlockEnd(lines, startIndex, openCommand, closeCommand, endExclusive = lines.length) {
    let depth = 0;
    for (let i = startIndex + 1; i < endExclusive; i += 1) {
      const command = String(lines[i]?.command || '').trim().toUpperCase();
      if (command === openCommand) {
        depth += 1;
        continue;
      }
      if (command === closeCommand) {
        if (depth === 0) return i;
        depth -= 1;
      }
    }
    return endExclusive;
  }

  async function executeVisualEventCommand(line, runtime) {
    ensureVisualEventRuntime(runtime);
    const command = String(line?.command || '').trim().toUpperCase();
    const config = line?.config && typeof line.config === 'object' ? line.config : {};
    const outputName = String(config.store_as || '').trim();
    const left = readRuntimeValue(runtime, config.left);
    const right = readRuntimeValue(runtime, config.right);
    switch (command) {
      case 'START':
      case 'ELSE':
      case 'ENDIF':
      case 'ENDWHILE':
      case 'ENDFOR':
      case 'ENDCURSOR_SCAN':
        return { type: 'continue' };
      case 'MESSAGE':
        await showVisualMessage(readRuntimeValue(runtime, config.message));
        return { type: 'continue' };
      case 'CONFIRM':
        storeRuntimeValue(runtime, outputName, await showVisualConfirm(readRuntimeValue(runtime, config.message)));
        return { type: 'continue' };
      case 'INPUT_BOX': {
        const answer = window.prompt(
          String(readRuntimeValue(runtime, config.prompt) ?? ''),
          String(readRuntimeValue(runtime, config.default_value) ?? '')
        );
        storeRuntimeValue(runtime, outputName, answer === null ? '' : answer);
        return { type: 'continue' };
      }
      case 'RETURN':
        return { type: 'return', value: readRuntimeValue(runtime, config.value) };
      case 'DELAY': {
        const durationMs = Math.max(0, Number(readRuntimeValue(runtime, config.duration_ms)) || 0);
        await new Promise(resolve => window.setTimeout(resolve, durationMs));
        return { type: 'continue' };
      }
      case 'DEFINE_VARIABLE':
        storeRuntimeValue(runtime, config.name, readRuntimeValue(runtime, config.default_value));
        return { type: 'continue' };
      case 'GET_VALUE':
        storeRuntimeValue(runtime, outputName, readRuntimeValue(runtime, config.source));
        return { type: 'continue' };
      case 'SET_VALUE':
        storeRuntimeValue(runtime, config.target, readRuntimeValue(runtime, config.value));
        return { type: 'continue' };
      case 'COPY_VALUE':
        storeRuntimeValue(runtime, config.target, readRuntimeValue(runtime, config.source));
        return { type: 'continue' };
      case 'CREATE_OBJECT':
        storeRuntimeValue(runtime, config.name, {});
        return { type: 'continue' };
      case 'CREATE_LIST':
        storeRuntimeValue(runtime, config.name, []);
        return { type: 'continue' };
      case 'ADD_TO_LIST': {
        const listName = String(config.list_name || '').trim();
        const current = normalizeToList(readRuntimeValue(runtime, listName));
        current.push(readRuntimeValue(runtime, config.value));
        storeRuntimeValue(runtime, listName, current);
        return { type: 'continue' };
      }
      case 'GET_ITEM': {
        const list = normalizeToList(readRuntimeValue(runtime, config.list_name));
        const index = Number(readRuntimeValue(runtime, config.index)) || 0;
        storeRuntimeValue(runtime, outputName, list[index]);
        return { type: 'continue' };
      }
      case 'COUNT': {
        const source = readRuntimeValue(runtime, config.source);
        const count = Array.isArray(source)
          ? source.length
          : typeof source === 'string'
          ? source.length
          : source && typeof source === 'object'
          ? Object.keys(source).length
          : 0;
        storeRuntimeValue(runtime, outputName, count);
        return { type: 'continue' };
      }
      case 'IS_EMPTY': {
        const source = readRuntimeValue(runtime, config.source);
        const empty = Array.isArray(source)
          ? source.length === 0
          : source && typeof source === 'object'
          ? Object.keys(source).length === 0
          : String(source ?? '').trim() === '';
        storeRuntimeValue(runtime, outputName, empty);
        return { type: 'continue' };
      }
      case 'CURSOR_NEW': {
        const cursorName = String(config.cursor_name || '').trim();
        if (!cursorName) {
          throw new Error('Cursor name is required.');
        }
        const cursorMode = String(readRuntimeValue(runtime, config.cursor_mode) ?? 'manual').trim().toLowerCase() || 'manual';
        if (cursorMode === 'sql') {
          const sqlQuery = String(readRuntimeValue(runtime, config.sql_query) ?? '').trim();
          if (!sqlQuery) {
            throw new Error('SQL query is required for Cursor New in SQL mode.');
          }
          const queryResult = await runCursorSqlQuery(runtime, sqlQuery);
          const schema = inferCursorSchemaFromRows(queryResult.rows, queryResult.columns);
          const cursor = setRuntimeCursor(runtime, cursorName, {
            name: cursorName,
            schema,
            rows: queryResult.rows.map((row) => materializeCursorRow({ schema }, row)),
          });
          if (outputName) storeRuntimeValue(runtime, outputName, cursor?.rows || []);
          return { type: 'continue' };
        }
        const schema = normalizeCursorSchema(Array.isArray(config.cursor_fields) ? config.cursor_fields : []);
        if (!schema.length) {
          throw new Error('Manual Cursor New requires at least one field.');
        }
        const cursor = setRuntimeCursor(runtime, cursorName, {
          name: cursorName,
          schema,
          rows: [],
        });
        if (outputName) storeRuntimeValue(runtime, outputName, cursor?.rows || []);
        return { type: 'continue' };
      }
      case 'CURSOR_RECCOUNT': {
        const cursorName = String(config.cursor_name || '').trim();
        const cursor = getRuntimeCursor(runtime, cursorName);
        if (!cursor) throw new Error(`Cursor not found: ${cursorName || '?'}`);
        storeRuntimeValue(runtime, outputName, cursor.rows.length);
        return { type: 'continue' };
      }
      case 'CURSOR_APPEND': {
        const cursorName = String(config.cursor_name || '').trim();
        const cursor = getRuntimeCursor(runtime, cursorName);
        if (!cursor) throw new Error(`Cursor not found: ${cursorName || '?'}`);
        const rowValue = readRuntimeValue(runtime, config.value);
        const row = materializeCursorRow(cursor, rowValue);
        cursor.rows.push(row);
        if (outputName) storeRuntimeValue(runtime, outputName, row);
        return { type: 'continue' };
      }
      case 'CURSOR_DELETE': {
        const cursorName = String(config.cursor_name || '').trim();
        const cursor = getRuntimeCursor(runtime, cursorName);
        if (!cursor) throw new Error(`Cursor not found: ${cursorName || '?'}`);
        const rowIndex = resolveCursorRowIndex(runtime, cursorName, config.row_ref);
        if (rowIndex >= 0 && rowIndex < cursor.rows.length) {
          cursor.rows.splice(rowIndex, 1);
          syncCursorDeleteWithScanStack(runtime, cursorName, rowIndex);
        }
        return { type: 'continue' };
      }
      case 'CURSOR_REPLACE': {
        const cursorName = String(config.cursor_name || '').trim();
        const cursor = getRuntimeCursor(runtime, cursorName);
        if (!cursor) throw new Error(`Cursor not found: ${cursorName || '?'}`);
        const rowIndex = resolveCursorRowIndex(runtime, cursorName, config.row_ref);
        if (rowIndex < 0 || rowIndex >= cursor.rows.length) return { type: 'continue' };
        const rawFieldName = String(readRuntimeValue(runtime, config.field_name) ?? '').trim().toUpperCase();
        if (!rawFieldName) throw new Error('Cursor Replace requires a field name.');
        let fieldMeta = normalizeCursorSchema(cursor.schema).find((entry) => entry.name === rawFieldName) || null;
        if (!fieldMeta) {
          fieldMeta = normalizeCursorSchemaEntry({
            name: rawFieldName,
            type: detectCursorFieldType(readRuntimeValue(runtime, config.value)),
          });
          cursor.schema.push(fieldMeta);
        }
        cursor.rows[rowIndex][fieldMeta.name] = coerceCursorValue(readRuntimeValue(runtime, config.value), fieldMeta.type);
        return { type: 'continue' };
      }
      case 'CURSOR_CLOSE': {
        const cursorName = String(config.cursor_name || '').trim();
        clearRuntimeCursor(runtime, cursorName);
        return { type: 'continue' };
      }
      case 'EQUALS':
        storeRuntimeValue(
          runtime,
          outputName,
          normalizeRuntimeComparableValue(left) === normalizeRuntimeComparableValue(right),
        );
        return { type: 'continue' };
      case 'NOT_EQUALS':
        storeRuntimeValue(
          runtime,
          outputName,
          normalizeRuntimeComparableValue(left) !== normalizeRuntimeComparableValue(right),
        );
        return { type: 'continue' };
      case 'GREATER':
        storeRuntimeValue(runtime, outputName, Number(left) > Number(right));
        return { type: 'continue' };
      case 'LESS':
        storeRuntimeValue(runtime, outputName, Number(left) < Number(right));
        return { type: 'continue' };
      case 'AND':
        storeRuntimeValue(runtime, outputName, !!left && !!right);
        return { type: 'continue' };
      case 'OR':
        storeRuntimeValue(runtime, outputName, !!left || !!right);
        return { type: 'continue' };
      case 'NOT':
        storeRuntimeValue(runtime, outputName, !isTruthyLike(readRuntimeValue(runtime, config.value)));
        return { type: 'continue' };
      case 'SUM':
        storeRuntimeValue(runtime, outputName, (Number(left) || 0) + (Number(right) || 0));
        return { type: 'continue' };
      case 'SUBTRACT':
        storeRuntimeValue(runtime, outputName, (Number(left) || 0) - (Number(right) || 0));
        return { type: 'continue' };
      case 'MULTIPLY':
        storeRuntimeValue(runtime, outputName, (Number(left) || 0) * (Number(right) || 0));
        return { type: 'continue' };
      case 'DIVIDE':
        storeRuntimeValue(runtime, outputName, Number(right) ? (Number(left) || 0) / Number(right) : 0);
        return { type: 'continue' };
      case 'ROUND':
        storeRuntimeValue(runtime, outputName, Number(Number(readRuntimeValue(runtime, config.value) || 0).toFixed(Math.max(0, Number(readRuntimeValue(runtime, config.decimals)) || 0))));
        return { type: 'continue' };
      case 'CONCAT':
        storeRuntimeValue(runtime, outputName, `${left ?? ''}${right ?? ''}`);
        return { type: 'continue' };
      case 'SUBSTRING': {
        const value = String(readRuntimeValue(runtime, config.value) ?? '');
        const start = Math.max(0, Number(readRuntimeValue(runtime, config.start)) || 0);
        const length = Number(readRuntimeValue(runtime, config.length));
        storeRuntimeValue(runtime, outputName, Number.isFinite(length) ? value.substring(start, start + length) : value.substring(start));
        return { type: 'continue' };
      }
      case 'TRIM':
        storeRuntimeValue(runtime, outputName, String(readRuntimeValue(runtime, config.value) ?? '').trim());
        return { type: 'continue' };
      case 'UPPER':
        storeRuntimeValue(runtime, outputName, String(readRuntimeValue(runtime, config.value) ?? '').toUpperCase());
        return { type: 'continue' };
      case 'LOWER':
        storeRuntimeValue(runtime, outputName, String(readRuntimeValue(runtime, config.value) ?? '').toLowerCase());
        return { type: 'continue' };
      case 'DATE_ADD': {
        const base = new Date(readRuntimeValue(runtime, config.date_value));
        const delta = String(readRuntimeValue(runtime, config.delta) ?? '').trim().toLowerCase();
        if (Number.isNaN(base.getTime())) {
          storeRuntimeValue(runtime, outputName, '');
          return { type: 'continue' };
        }
        const match = delta.match(/^([+-]?\d+)\s*([dmyh])$/);
        if (match) {
          const amount = Number(match[1]) || 0;
          const unit = match[2];
          if (unit === 'd') base.setDate(base.getDate() + amount);
          if (unit === 'm') base.setMonth(base.getMonth() + amount);
          if (unit === 'y') base.setFullYear(base.getFullYear() + amount);
          if (unit === 'h') base.setHours(base.getHours() + amount);
        }
        storeRuntimeValue(runtime, outputName, base.toISOString());
        return { type: 'continue' };
      }
      case 'DATE_DIFF': {
        const startDate = new Date(readRuntimeValue(runtime, config.date_start));
        const endDate = new Date(readRuntimeValue(runtime, config.date_end));
        const diff = (!Number.isNaN(startDate.getTime()) && !Number.isNaN(endDate.getTime()))
          ? Math.round((endDate.getTime() - startDate.getTime()) / 86400000)
          : 0;
        storeRuntimeValue(runtime, outputName, diff);
        return { type: 'continue' };
      }
      case 'OPEN_MODAL':
        document.dispatchEvent(new CustomEvent('dynamic-form:open-modal', { detail: { name: readRuntimeValue(runtime, config.modal_name), button: runtime.button, col: runtime.col } }));
        return { type: 'continue' };
      case 'CLOSE_MODAL':
        document.dispatchEvent(new CustomEvent('dynamic-form:close-modal', { detail: { name: readRuntimeValue(runtime, config.modal_name), button: runtime.button, col: runtime.col } }));
        return { type: 'continue' };
      case 'FOCUS_FIELD': {
        const input = getFieldInputByName(config.field_name);
        input?.focus?.();
        return { type: 'continue' };
      }
      case 'SHOW_HIDE': {
        const wrapper = getFieldWrapperByName(config.target);
        if (wrapper) wrapper.style.display = String(config.mode || '').trim().toLowerCase() === 'hide' ? 'none' : '';
        return { type: 'continue' };
      }
      case 'ENABLE_DISABLE': {
        const input = getFieldInputByName(config.target);
        if (input) input.disabled = String(config.mode || '').trim().toLowerCase() === 'disable';
        return { type: 'continue' };
      }
      case 'SET_REQUIRED': {
        const input = getFieldInputByName(config.field_name);
        if (input) input.required = String(config.mode || '').trim().toLowerCase() === 'required';
        return { type: 'continue' };
      }
      case 'REFRESH_SCREEN':
        window.location.reload();
        return { type: 'return', value: undefined };
      case 'REFRESH_GRID':
        document.dispatchEvent(new CustomEvent('dynamic-form:refresh-grid', { detail: { name: readRuntimeValue(runtime, config.grid_name), button: runtime.button, col: runtime.col } }));
        return { type: 'continue' };
      case 'GET_SYSTEM_VALUE': {
        const systemKey = String(readRuntimeValue(runtime, config.system_key) ?? '').trim().toUpperCase();
        const systemValueMap = {
          USER: window.CURRENT_USER || window.USERNAME || '',
          CURRENT_USER: window.CURRENT_USER || window.USERNAME || '',
          FEID: window.FEID || window.EMPRESA_FEID || '',
          TABLE_NAME,
          RECORD_STAMP,
          MENU_STAMP,
        };
        storeRuntimeValue(runtime, outputName, systemValueMap[systemKey] ?? '');
        return { type: 'continue' };
      }
      case 'CALL_API': {
        const endpoint = String(readRuntimeValue(runtime, config.endpoint) ?? '').trim();
        const method = String(readRuntimeValue(runtime, config.method) ?? 'GET').trim().toUpperCase() || 'GET';
        const response = await fetch(toDynamicAppRelativeUrl(endpoint, endpoint), { method, headers: { 'Content-Type': 'application/json' } });
        const data = await response.json().catch(() => ({}));
        runtime.lastApiResponse = data;
        storeRuntimeValue(runtime, outputName, data);
        return { type: 'continue' };
      }
      case 'GET_API_VALUE':
        storeRuntimeValue(runtime, outputName, deepReadValue(runtime.lastApiResponse, readRuntimeValue(runtime, config.path)));
        return { type: 'continue' };
      case 'CALL_SCREEN_ACTION': {
        const actionName = String(readRuntimeValue(runtime, config.action_name) ?? '').trim();
        const fn = actionName && typeof window[actionName] === 'function' ? window[actionName] : null;
        if (fn) {
          await Promise.resolve(fn({ TABLE_NAME, RECORD_STAMP, MENU_STAMP, formState, camposByName, button: runtime.button, col: runtime.col }));
        }
        return { type: 'continue' };
      }
      case 'EMIT_EVENT': {
        const eventName = String(readRuntimeValue(runtime, config.event_name) ?? '').trim();
        if (eventName) {
          document.dispatchEvent(new CustomEvent(eventName, { detail: { TABLE_NAME, RECORD_STAMP, MENU_STAMP, formState, camposByName, button: runtime.button, col: runtime.col } }));
        }
        return { type: 'continue' };
      }
      case 'LOG_DEBUG':
        console.debug('[dynamic_form][event]', readRuntimeValue(runtime, config.message), { formState, vars: runtime.vars, col: runtime.col });
        return { type: 'continue' };
      case 'GET_FIELD':
        storeRuntimeValue(runtime, outputName, getFieldCurrentValue(config.field_name));
        return { type: 'continue' };
      case 'SET_FIELD':
        updateFieldValue(config.field_name, readRuntimeValue(runtime, config.value));
        return { type: 'continue' };
      case 'GET_ROW':
        storeRuntimeValue(runtime, outputName, readRuntimeValue(runtime, config.row_ref));
        return { type: 'continue' };
      case 'SET_ROW':
        storeRuntimeValue(runtime, config.row_ref, readRuntimeValue(runtime, config.value));
        return { type: 'continue' };
      case 'GET_SELECTED_ROWS':
        storeRuntimeValue(runtime, outputName, []);
        return { type: 'continue' };
      case 'VALIDATE_FIELD': {
        const input = getFieldInputByName(config.field_name);
        const valid = input ? input.checkValidity() : false;
        storeRuntimeValue(runtime, outputName, valid);
        return { type: 'continue' };
      }
      case 'VALIDATE_FORM': {
        const valid = !!form?.checkValidity?.();
        storeRuntimeValue(runtime, outputName, valid);
        return { type: 'continue' };
      }
      case 'BREAK':
        return { type: 'break' };
      case 'CONTINUE':
        return { type: 'continue_loop' };
      default:
        throw new Error(`Comando visual ainda nao suportado: ${command}`);
    }
  }

  async function executeVisualEventRange(lines, runtime, startIndex = 0, endExclusive = lines.length) {
    ensureVisualEventRuntime(runtime);
    for (let index = startIndex; index < endExclusive; index += 1) {
      const line = lines[index];
      if (!line || line.kind === 'empty') continue;
      const command = String(line.command || '').trim().toUpperCase();
      if (command === 'ELSE' || command === 'ENDIF' || command === 'ENDWHILE' || command === 'ENDFOR' || command === 'ENDCURSOR_SCAN') {
        continue;
      }
      if (command === 'IF') {
        const { elseIndex, endIndex } = findIfMarkers(lines, index, endExclusive);
        const condition = evaluateRuntimeExpression(runtime, line.config?.condition);
        const result = condition
          ? await executeVisualEventRange(lines, runtime, index + 1, elseIndex >= 0 ? elseIndex : endIndex)
          : elseIndex >= 0
          ? await executeVisualEventRange(lines, runtime, elseIndex + 1, endIndex)
          : { type: 'continue' };
        if (result.type !== 'continue') return result;
        index = endIndex;
        continue;
      }
      if (command === 'WHILE') {
        const endIndex = findBlockEnd(lines, index, 'WHILE', 'ENDWHILE', endExclusive);
        let guard = 0;
        while (evaluateRuntimeExpression(runtime, line.config?.condition)) {
          guard += 1;
          if (guard > 100) throw new Error('Loop WHILE excedeu o limite de 100 iteracoes.');
          const result = await executeVisualEventRange(lines, runtime, index + 1, endIndex);
          if (result.type === 'return') return result;
          if (result.type === 'break') break;
          if (result.type !== 'continue' && result.type !== 'continue_loop') return result;
        }
        index = endIndex;
        continue;
      }
      if (command === 'FOR_EACH') {
        const endIndex = findBlockEnd(lines, index, 'FOR_EACH', 'ENDFOR', endExclusive);
        const items = normalizeToList(readRuntimeValue(runtime, line.config?.source));
        const itemName = String(line.config?.item_name || 'ITEM').trim() || 'ITEM';
        for (const item of items) {
          storeRuntimeValue(runtime, itemName, item);
          const result = await executeVisualEventRange(lines, runtime, index + 1, endIndex);
          if (result.type === 'return') return result;
          if (result.type === 'break') break;
          if (result.type !== 'continue' && result.type !== 'continue_loop') return result;
        }
        index = endIndex;
        continue;
      }
      if (command === 'CURSOR_SCAN') {
        const cursorName = String(line.config?.cursor_name || '').trim();
        const cursor = getRuntimeCursor(runtime, cursorName);
        if (!cursor) throw new Error(`Cursor not found: ${cursorName || '?'}`);
        const endIndex = findBlockEnd(lines, index, 'CURSOR_SCAN', 'ENDCURSOR_SCAN', endExclusive);
        const rowName = String(line.config?.row_name || 'ROW').trim() || 'ROW';
        let pointer = 0;
        while (pointer < cursor.rows.length) {
          const currentRow = cursor.rows[pointer];
          const scanContext = {
            cursorKey: getCursorRuntimeKey(cursorName),
            cursorName,
            index: pointer,
            rowName,
            deletedCurrent: false,
          };
          runtime.cursorScanStack.push(scanContext);
          storeRuntimeValue(runtime, rowName, currentRow);
          const result = await executeVisualEventRange(lines, runtime, index + 1, endIndex);
          runtime.cursorScanStack.pop();
          if (result.type === 'return') return result;
          if (result.type === 'break') break;
          if (result.type !== 'continue' && result.type !== 'continue_loop') return result;
          if (cursor.rows[pointer] === currentRow && !scanContext.deletedCurrent) {
            pointer += 1;
          }
        }
        index = endIndex;
        continue;
      }
      const result = await executeVisualEventCommand(line, runtime);
      if (result.type === 'return' || result.type === 'break' || result.type === 'continue_loop') {
        return result;
      }
    }
    return { type: 'continue' };
  }

  async function executeVisualEventFlow(flow, runtime) {
    const lines = getVisualEventLines(flow);
    if (!lines.length) return undefined;
    const preparedRuntime = ensureVisualEventRuntime(runtime || {});
    const result = await executeVisualEventRange(lines, preparedRuntime, 0, lines.length);
    return result.value;
  }

  async function runScreenEventHook(eventName) {
    const flow = getScreenEventFlow(eventName);
    if (!hasMeaningfulVisualEventFlow(flow)) return undefined;
    return executeVisualEventFlow(flow, {
      vars: {},
      button: null,
      col: null,
      lastApiResponse: null,
    });
  }

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
    const nextValue = readValueForState(target);
    setFormStateValue(target.name, nextValue);
    if (target.dataset?.variableName) {
      syncBoundVariableValue(target.dataset.variableName, nextValue, { source: target });
    }
    aplicarCondicoesDeVisibilidade();
  }
  // ——— Montagem customizada por ORDEM (uma row por dezena) ———

  function getLookupPropertyFromProps(props, ...names) {
    for (const name of names) {
      if (props && Object.prototype.hasOwnProperty.call(props, name)) {
        return String(props[name] ?? '').trim();
      }
    }
    return '';
  }

  function getLookupProperty(col, ...names) {
    return getLookupPropertyFromProps(getColumnProperties(col), ...names);
  }

  function makeTableFieldLookupConfig(col) {
    return {
      lookupTable: getLookupProperty(col, 'lookup_table', 'table', 'source'),
      displayFields: getLookupProperty(col, 'lookup_display_fields', 'display_fields'),
      valueField: getLookupProperty(col, 'lookup_value_field', 'value_field', 'source_field'),
      targetField: getLookupProperty(col, 'lookup_target_field', 'target_field', 'field_name'),
      objectName: String(col?.name || '').trim(),
    };
  }

  function hasRequiredTableFieldLookupConfig(config) {
    return !!(String(config?.lookupTable || '').trim() && String(config?.valueField || '').trim());
  }

  function getTableFieldLookupConfig(col) {
    const directConfig = makeTableFieldLookupConfig(col);
    if (hasRequiredTableFieldLookupConfig(directConfig)) return directConfig;

    const fieldName = normalizePhysicalFieldName(col?.name).toUpperCase();
    const directTargetName = normalizePhysicalFieldName(directConfig.targetField || col?.name).toUpperCase();
    const fallback = cols.find(candidate => {
      if (candidate === col || (candidate?.tipo || '').toUpperCase() !== 'TABLE_FIELD') return false;
      const candidateConfig = makeTableFieldLookupConfig(candidate);
      if (!hasRequiredTableFieldLookupConfig(candidateConfig)) return false;
      const candidateName = normalizePhysicalFieldName(candidate?.name).toUpperCase();
      const candidateTargetName = normalizePhysicalFieldName(candidateConfig.targetField || candidate?.name).toUpperCase();
      return (
        candidateName === fieldName
        || candidateTargetName === fieldName
        || (directTargetName && candidateTargetName === directTargetName)
      );
    });

    if (fallback) {
      const fallbackConfig = makeTableFieldLookupConfig(fallback);
      return {
        ...fallbackConfig,
        targetField: directConfig.targetField || fallbackConfig.targetField,
      };
    }

    return directConfig;
  }

  function getTableFieldLookupInput(col) {
    return getFieldInputCandidates(col?.name)
      .find(input => input?.dataset?.lookupValueField !== undefined || input?.dataset?.lookupTargetField !== undefined)
      || null;
  }

  async function fetchTableFieldLookupRows(col, { q = '', value = '', signal = null } = {}) {
    const config = getTableFieldLookupConfig(col);
    const payload = {
      table_name: TABLE_NAME,
      record_stamp: RECORD_STAMP,
      menustamp: MENU_STAMP,
      object_name: config.objectName || col.name,
      q,
      form_state: formState,
      config: {
        lookup_table: config.lookupTable,
        lookup_display_fields: config.displayFields,
        lookup_value_field: config.valueField,
        lookup_target_field: config.targetField,
      },
    };
    const rawValue = String(value ?? '').trim();
    if (rawValue) {
      payload.mode = 'value';
      payload.value = rawValue;
    }
    const response = await fetch('/generic/api/menu_object_lookup', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      signal,
      body: JSON.stringify(payload),
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok || data?.success === false) {
      throw new Error(data?.error || 'Nao foi possivel pesquisar.');
    }
    return Array.isArray(data.rows) ? data.rows : [];
  }

  function readRecordFieldValue(record, fieldName) {
    const targetName = normalizePhysicalFieldName(fieldName);
    if (!record || typeof record !== 'object' || !targetName) return undefined;
    const directKeys = [fieldName, targetName, targetName.toUpperCase(), targetName.toLowerCase()]
      .map(key => String(key || '').trim())
      .filter(Boolean);
    for (const key of directKeys) {
      if (Object.prototype.hasOwnProperty.call(record, key)) return record[key];
    }
    const wanted = targetName.toUpperCase();
    const found = Object.keys(record).find(key => String(key || '').trim().toUpperCase() === wanted);
    return found ? record[found] : undefined;
  }

  async function hydrateTableFieldLookupObjects(record) {
    const lookupObjects = cols.filter(col => (col.tipo || '').toUpperCase() === 'TABLE_FIELD');
    await Promise.all(lookupObjects.map(async col => {
      const input = getTableFieldLookupInput(col);
      if (!input) return;
      const config = getTableFieldLookupConfig(col);
      const targetField = config.targetField || col.name;
      const rawValue = readRecordFieldValue(record, targetField);
      const value = rawValue === undefined || rawValue === null ? '' : String(rawValue).trim();
      if (!value) {
        input.value = '';
        setFormStateValue(col.name, '');
        setFormStateValue(`${col.name}_LABEL`, '');
        clearTableFieldTargetValue(targetField, { writeEmpty: true });
        return;
      }

      input.value = value;
      setFormStateValue(col.name, value);
      setFormStateValue(`${col.name}_LABEL`, value);
      setTableFieldTargetValue(targetField, value);

      try {
        const rows = await fetchTableFieldLookupRows(col, { value });
        const row = rows.find(item => String(item?.value ?? '').trim() === value) || rows[0];
        const label = String(row?.label || value).trim() || value;
        input.value = label;
        setFormStateValue(`${col.name}_LABEL`, label);
      } catch (error) {
        console.warn(`Nao foi possivel carregar o texto do campo tabela ${col.name}:`, error);
      }
    }));
  }

  function renderTableFieldLookupObject(col, colDiv) {
    const { lookupTable, valueField, targetField } = getTableFieldLookupConfig(col);
    let debounceTimer = null;
    let abortController = null;
    let currentRows = [];
    let activeIndex = -1;
    let requestSeq = 0;

    const wrapper = document.createElement('div');
    wrapper.className = 'mb-3 sz_field sz_table_lookup_field';

    const label = document.createElement('label');
    label.setAttribute('for', col.name);
    label.className = 'sz_label';
    label.textContent = String(col.descricao || col.name || '').trim() || 'Pesquisa';

    const host = document.createElement('div');
    host.className = 'sz_table_lookup';

    const input = document.createElement('input');
    input.type = 'search';
    input.name = col.name;
    input.id = col.name;
    input.className = 'sz_input';
    input.autocomplete = 'off';
    input.spellcheck = false;
    input.dataset.uiOnly = 'true';
    input.dataset.lookupTable = lookupTable;
    input.dataset.lookupValueField = valueField;
    input.dataset.lookupTargetField = targetField;
    input.placeholder = lookupTable && valueField ? 'Pesquisar...' : 'Configura a tabela e o campo valor';

    const menu = document.createElement('div');
    menu.className = 'sz_table_lookup_dropdown';
    menu.hidden = true;

    const closeMenu = () => {
      menu.hidden = true;
      menu.innerHTML = '';
      currentRows = [];
      activeIndex = -1;
    };

    const renderLookupMessage = (message, tone = 'muted') => {
      menu.innerHTML = '';
      const item = document.createElement('div');
      item.className = `sz_table_lookup_empty ${tone === 'danger' ? 'is-danger' : ''}`;
      item.textContent = message;
      menu.appendChild(item);
      menu.hidden = false;
    };

    const setActiveResult = index => {
      const buttons = Array.from(menu.querySelectorAll('.sz_table_lookup_item'));
      buttons.forEach((button, buttonIndex) => {
        button.classList.toggle('is-active', buttonIndex === index);
      });
      activeIndex = index;
    };

    const selectLookupRow = row => {
      if (!row) return;
      const value = row.value === undefined || row.value === null ? '' : String(row.value);
      const labelValue = String(row.label || value || '').trim();
      input.value = labelValue;
      setFormStateValue(col.name, value);
      setFormStateValue(`${col.name}_LABEL`, labelValue);
      if (targetField) {
        const updated = updateFieldValue(targetField, value, { preferWritable: true });
        const stored = setTableFieldTargetValue(targetField, value);
        if (!updated && !stored) {
          showDynamicFormToast(`Campo destino nao encontrado: ${targetField}`, 'warning');
        }
      }
      closeMenu();
      input.focus();
    };

    const renderLookupRows = rows => {
      currentRows = Array.isArray(rows) ? rows : [];
      menu.innerHTML = '';
      if (!currentRows.length) {
        renderLookupMessage('Sem resultados');
        return;
      }
      currentRows.forEach((row, index) => {
        const button = document.createElement('button');
        button.type = 'button';
        button.className = 'sz_table_lookup_item';
        button.dataset.index = String(index);
        const title = document.createElement('span');
        title.className = 'sz_table_lookup_item_label';
        const fallbackValue = row.value === undefined || row.value === null ? '' : row.value;
        title.textContent = String(row.label || fallbackValue).trim() || '-';
        button.appendChild(title);
        const displayValues = Array.isArray(row.display) ? row.display.filter(value => String(value ?? '').trim() !== '') : [];
        if (displayValues.length > 1) {
          const meta = document.createElement('span');
          meta.className = 'sz_table_lookup_item_value';
          meta.textContent = displayValues.slice(1).map(value => String(value ?? '').trim()).join(' · ');
          button.appendChild(meta);
        }
        button.addEventListener('mouseenter', () => setActiveResult(index));
        button.addEventListener('mousedown', event => {
          event.preventDefault();
          selectLookupRow(row);
        });
        menu.appendChild(button);
      });
      menu.hidden = false;
      setActiveResult(0);
    };

    const fetchLookupRows = async () => {
      const q = input.value.trim();
      setFormStateValue(col.name, q);
      setFormStateValue(`${col.name}_LABEL`, q);
      if (!q) {
        closeMenu();
        return;
      }
      if (!lookupTable || !valueField) {
        renderLookupMessage('Objeto sem tabela ou campo valor configurado', 'danger');
        return;
      }
      if (abortController) {
        abortController.abort();
      }
      abortController = new AbortController();
      const seq = ++requestSeq;
      renderLookupMessage('A procurar...');
      try {
        const rows = await fetchTableFieldLookupRows(col, { q, signal: abortController.signal });
        if (seq !== requestSeq) return;
        renderLookupRows(rows);
      } catch (error) {
        if (error?.name === 'AbortError') return;
        console.error('Erro na pesquisa do campo de tabela:', error);
        renderLookupMessage(error.message || 'Erro na pesquisa', 'danger');
      }
    };

    const scheduleLookup = () => {
      window.clearTimeout(debounceTimer);
      debounceTimer = window.setTimeout(fetchLookupRows, 250);
    };

    input.addEventListener('input', () => {
      setFormStateValue(col.name, input.value);
      setFormStateValue(`${col.name}_LABEL`, input.value);
      if (targetField) {
        clearTableFieldTargetValue(targetField, { writeEmpty: !input.value.trim() });
      }
      scheduleLookup();
    });
    input.addEventListener('focus', () => {
      if (input.value.trim()) scheduleLookup();
    });
    input.addEventListener('keydown', event => {
      if (menu.hidden) return;
      if (event.key === 'ArrowDown') {
        event.preventDefault();
        setActiveResult(Math.min(currentRows.length - 1, activeIndex + 1));
      } else if (event.key === 'ArrowUp') {
        event.preventDefault();
        setActiveResult(Math.max(0, activeIndex - 1));
      } else if (event.key === 'Enter') {
        if (activeIndex >= 0 && currentRows[activeIndex]) {
          event.preventDefault();
          selectLookupRow(currentRows[activeIndex]);
        }
      } else if (event.key === 'Escape') {
        closeMenu();
      }
    });
    input.addEventListener('blur', () => {
      window.setTimeout(closeMenu, 150);
    });

    camposByName[col.name] = input;
    setFormStateValue(col.name, '');
    setFormStateValue(`${col.name}_LABEL`, '');

    host.appendChild(input);
    host.appendChild(menu);
    wrapper.appendChild(label);
    wrapper.appendChild(host);
    colDiv.appendChild(wrapper);
  }

  // limpa o form
  form.innerHTML = '';

  // agrupa por dezena de ORDEM
  const grupos = {};
  cols
    .filter(c => (!c.admin || isAdminUser) && isColumnVisible(c))
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
      const totalTam = fields.reduce((acc, f) => acc + getLayoutFieldSize(f), 0);


      row.style.display = 'flex';
      row.style.flexWrap = 'nowrap';


      fields.forEach(col => {
        const tamUsado = getLayoutFieldSize(col);
        const fraction = useExactWidths
          ? (tamUsado / layoutWidthUnits)
          : (tamUsado / totalTam);
        const colDiv = document.createElement('div');
        // fixa largura proporcional e impede flex-grow/shrink
        colDiv.style.flex = `0 0 ${fraction * 100}%`;
        colDiv.style.maxWidth = `${fraction * 100}%`;
        colDiv.style.boxSizing = 'border-box';
        // mantém o mesmo comportamento de responsive para mobile
        colDiv.classList.add('col-12');
        row.appendChild(colDiv);

        // se for um campo "vazio", desenha apenas um espaço reservado
        if (!col.name) {
          colDiv.innerHTML = '<div class="invisible">.</div>'; // ocupa espaço mas invisível
          return;
        }

        if ((col.tipo || '').toUpperCase() === 'SPACE') {
          const wrapper = document.createElement('div');
          wrapper.className = 'mb-3 sz_field';

          const marker = document.createElement('input');
          marker.type = 'text';
          marker.name = col.name;
          marker.dataset.uiOnly = 'true';
          marker.disabled = true;
          marker.hidden = true;
          camposByName[col.name] = marker;
          formState[col.name] = '';

          const spacer = document.createElement('div');
          spacer.className = 'sz_surface_alt';
          spacer.style.minHeight = '2.25rem';
          spacer.style.border = '1px dashed var(--sz-color-border)';
          spacer.style.borderRadius = 'var(--sz-radius-md)';
          spacer.style.background = 'transparent';

          wrapper.appendChild(marker);
          wrapper.appendChild(spacer);
          colDiv.appendChild(wrapper);
          return;
        }

        if ((col.tipo || '').toUpperCase() === 'BUTTON') {
          const wrapper = document.createElement('div');
          wrapper.className = 'mb-3 sz_field';

          const button = document.createElement('button');
          button.type = 'button';
          button.name = col.name;
          button.id = col.name;
          button.className = 'sz_button sz_button_secondary';
          button.style.width = '100%';
          button.textContent = String(col.descricao || col.name || 'Button').trim() || 'Button';
          button.dataset.uiOnly = 'true';
          button.disabled = !isButtonEnabled(col);

          const clickFlow = getButtonClickFlow(col);
          const clickAction = getButtonClickAction(col);
          if ((hasMeaningfulVisualEventFlow(clickFlow) || clickAction) && !button.disabled) {
            button.addEventListener('click', async event => {
              event.preventDefault();
              try {
                if (hasMeaningfulVisualEventFlow(clickFlow)) {
                  await executeVisualEventFlow(clickFlow, {
                    vars: {},
                    button,
                    col,
                    lastApiResponse: null,
                  });
                  return;
                }
                const fn = new Function(
                  'TABLE_NAME',
                  'RECORD_STAMP',
                  'MENU_STAMP',
                  'formState',
                  'button',
                  'camposByName',
                  'col',
                  clickAction
                );
                await Promise.resolve(fn(TABLE_NAME, RECORD_STAMP, MENU_STAMP, formState, button, camposByName, col));
              } catch (error) {
                console.error('Erro ao executar click do botao personalizado:', error);
                showDynamicFormToast(`Erro ao executar evento do botao: ${error.message}`, 'danger');
              }
            });
          }

          camposByName[col.name] = button;
          setFormStateValue(col.name, '');

          wrapper.appendChild(button);
          colDiv.appendChild(wrapper);
          return;
        }

        if ((col.tipo || '').toUpperCase() === 'TABLE') {
          const wrapper = document.createElement('div');
          wrapper.className = 'mb-3 sz_field';
          const props = getColumnProperties(col);
          const showAddButton = !!Number(props.show_add_button || 0);
          const showDeleteButton = !!Number(props.show_delete_button || 0);

          const marker = document.createElement('input');
          marker.type = 'text';
          marker.name = col.name;
          marker.dataset.uiOnly = 'true';
          marker.disabled = true;
          marker.hidden = true;
          camposByName[col.name] = marker;
          setFormStateValue(col.name, '');

          const host = document.createElement('div');
          host.className = 'sz_surface_alt';
          host.style.border = '1px solid var(--sz-color-border)';
          host.style.borderRadius = 'var(--sz-radius-md)';
          host.style.overflow = 'hidden';
          host.style.minHeight = '10rem';
          host.style.background = 'color-mix(in srgb, var(--sz-color-surface) 90%, transparent)';
          host.style.display = 'flex';
          host.style.flexDirection = 'column';
          host.style.gap = '.45rem';
          host.style.padding = '.6rem';

          const title = document.createElement('div');
          title.textContent = String(col.name || col.descricao || 'TABLE').trim() || 'TABLE';
          title.style.fontSize = '.92rem';
          title.style.fontWeight = '700';
          title.style.color = 'var(--sz-color-text)';
          host.appendChild(title);

          if (showAddButton) {
            const toolbar = document.createElement('div');
            toolbar.style.display = 'flex';
            toolbar.style.justifyContent = 'flex-end';
            const addBtn = document.createElement('button');
            addBtn.type = 'button';
            addBtn.className = 'sz_button sz_button_secondary';
            addBtn.disabled = true;
            addBtn.innerHTML = '<i class="fa-solid fa-plus"></i><span>Adicionar linha</span>';
            toolbar.appendChild(addBtn);
            host.appendChild(toolbar);
          }

          const table = document.createElement('div');
          table.style.display = 'grid';
          table.style.gridTemplateRows = 'auto repeat(3, minmax(2rem, auto))';

          const makeRow = (cells, { head = false } = {}) => {
            const rowEl = document.createElement('div');
            rowEl.style.display = 'grid';
            rowEl.style.gridTemplateColumns = showDeleteButton ? '4rem 1fr 6rem 2rem' : '4rem 1fr 6rem';
            rowEl.style.gap = '.4rem';
            rowEl.style.alignItems = 'center';
            rowEl.style.padding = '.45rem .6rem';
            rowEl.style.fontSize = '.82rem';
            rowEl.style.borderBottom = head ? '1px solid var(--sz-color-border)' : '1px solid color-mix(in srgb, var(--sz-color-border) 70%, transparent)';
            if (head) {
              rowEl.style.fontWeight = '700';
              rowEl.style.color = 'var(--sz-color-text)';
              rowEl.style.background = 'color-mix(in srgb, var(--sz-color-primary) 10%, var(--sz-color-surface))';
            } else {
              rowEl.style.color = 'var(--sz-color-text-secondary)';
            }
            cells.forEach((cell) => {
              const span = document.createElement('span');
              span.textContent = cell;
              rowEl.appendChild(span);
            });
            if (!head && showDeleteButton) {
              const actionWrap = document.createElement('div');
              actionWrap.style.display = 'flex';
              actionWrap.style.justifyContent = 'center';
              const deleteBtn = document.createElement('button');
              deleteBtn.type = 'button';
              deleteBtn.disabled = true;
              deleteBtn.title = 'Eliminar';
              deleteBtn.style.border = 'none';
              deleteBtn.style.background = 'transparent';
              deleteBtn.style.color = 'var(--sz-color-text-secondary)';
              deleteBtn.style.width = '1.75rem';
              deleteBtn.style.height = '1.75rem';
              deleteBtn.style.borderRadius = 'var(--sz-radius-sm)';
              deleteBtn.innerHTML = '<i class="fa-solid fa-trash"></i>';
              actionWrap.appendChild(deleteBtn);
              rowEl.appendChild(actionWrap);
            } else if (head && showDeleteButton) {
              rowEl.appendChild(document.createElement('span'));
            }
            return rowEl;
          };

          table.appendChild(makeRow(['ID', 'Descricao', 'Valor'], { head: true }));
          table.appendChild(makeRow(['1', 'Registo exemplo', '123,45']));
          table.appendChild(makeRow(['2', 'Outra linha', '67,89']));
          const lastRow = makeRow(['3', 'Mais uma linha', '10,00']);
          lastRow.style.borderBottom = 'none';
          table.appendChild(lastRow);

          host.appendChild(table);
          wrapper.appendChild(marker);
          wrapper.appendChild(host);
          colDiv.appendChild(wrapper);
          return;
        }

        if ((col.tipo || '').toUpperCase() === 'TABLE_FIELD') {
          renderTableFieldLookupObject(col, colDiv);
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
          setFormStateValue(col.name, input.value);
          camposByName[col.name] = input;
          input.addEventListener('change', handleFieldChange);
          const isBound = registerBoundVariableInput(col, input);
          if (isBound) bindVariableInputEvents(input);
          if (isUiOnlyColumn(col)) {
            input.dataset.uiOnly = 'true';
            if (!isEditableBoundObject(col)) {
              input.disabled = true;
              input.classList.add('sz_surface_alt');
            }
          }

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

              setFormStateValue(col.name, false);
              camposByName[col.name] = input;

              input.addEventListener('change', handleFieldChange);
              const isBound = registerBoundVariableInput(col, input);
              if (isBound) bindVariableInputEvents(input);
              if (isUiOnlyColumn(col)) {
                input.dataset.uiOnly = 'true';
                if (!isEditableBoundObject(col)) {
                  input.disabled = true;
                  input.classList.add('sz_surface_alt');
                }
              }
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

              setFormStateValue(col.name, '');
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

              setFormStateValue(col.name, '');
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
              const minValue = col.minimo !== undefined && col.minimo !== null && String(col.minimo).trim() !== ''
                ? String(col.minimo).trim()
                : '';
              const maxValue = col.maximo !== undefined && col.maximo !== null && String(col.maximo).trim() !== ''
                ? String(col.maximo).trim()
                : '';

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
                if (minValue) input.min = minValue;
                if (maxValue) input.max = maxValue;
              } else if (col.tipo === 'DECIMAL') {
                attachDecimalInputBehavior(input, decimalPlaces);
                if (minValue) input.dataset.minValue = minValue;
                if (maxValue) input.dataset.maxValue = maxValue;
              } else {
                input.type = 'text';
              }

              if (col.readonly) {
                input.readOnly = true;
                input.classList.add('sz_surface_alt');
              }

              setFormStateValue(col.name, '');
              input.addEventListener('change', handleFieldChange);
            }

            const isBound = registerBoundVariableInput(col, input);
            if (isBound) bindVariableInputEvents(input);

            if (isUiOnlyColumn(col)) {
              input.dataset.uiOnly = 'true';
              input.required = false;
              if (!isEditableBoundObject(col)) {
                if (input.tagName === 'SELECT' || input.type === 'checkbox' || input.type === 'color' || input.type === 'time' || input.classList.contains('flatpickr-date')) {
                  input.disabled = true;
                } else {
                  input.readOnly = true;
                }
                input.classList.add('sz_surface_alt');
              }
            }

            const props = getColumnProperties(col);
            if (props.placeholder && 'placeholder' in input) {
              input.placeholder = String(props.placeholder);
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
            opts = await (await fetch(toDynamicAppRelativeUrl(c.combo, c.combo))).json();
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

  syncAllBoundVariableInputs();

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
          setFormStateValue(el.name, el.value);
          if (el.dataset?.variableName) {
            syncBoundVariableValue(el.dataset.variableName, readValueForState(el), { source: el });
          }
          aplicarCondicoesDeVisibilidade();
        }
      }
      else if (el.type === 'checkbox') {
        el.checked = ['1','true','True'].includes(val);
        setFormStateValue(el.name, el.checked);
        if (el.dataset?.variableName) {
          syncBoundVariableValue(el.dataset.variableName, readValueForState(el), { source: el });
        }
        aplicarCondicoesDeVisibilidade();
      } else if (isDecimalInput(el)) {
        const places = getDecimalPlacesForInput(el);
        el.value = toDisplayDecimal(val, places);
        setFormStateValue(el.name, toServerDecimal(el.value, places));
        if (el.dataset?.variableName) {
          syncBoundVariableValue(el.dataset.variableName, readValueForState(el), { source: el });
        }
        aplicarCondicoesDeVisibilidade();
      } else {
        el.value = val;
        setFormStateValue(el.name, el.value);
        if (el.dataset?.variableName) {
          syncBoundVariableValue(el.dataset.variableName, readValueForState(el), { source: el });
        }
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
        setFormStateValue(nome, el.value);
      } else if (el.type === 'checkbox') {
        el.checked = !!val;
        setFormStateValue(nome, el.checked);
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
        setFormStateValue(nome, el.value);
        } else if (el.type === 'color') {
        // se a cor vier sem "#", adiciona
        let cor = (val || '').toString().trim();
        if (cor && !cor.startsWith('#')) cor = '#' + cor;
        el.value = cor || '#000000';
        setFormStateValue(nome, el.value);
      } else if (isDecimalInput(el)) {
        const places = getDecimalPlacesForInput(el);
        const display = toDisplayDecimal(val ?? '', places);
        el.value = display;
        setFormStateValue(nome, toServerDecimal(display, places));
      } else {
        el.value = val;
        setFormStateValue(nome, el.value);
      }
      if (el.dataset?.variableName) {
        syncBoundVariableValue(el.dataset.variableName, readValueForState(el), { source: el });
      }
    });
    await hydrateTableFieldLookupObjects(rec);
  } catch (e) {
    console.error('Erro ao carregar registro:', e);
  }

  syncAllBoundVariableInputs();
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
  if (hasScreenEventFlow('init')) {
    try {
      await runScreenEventHook('init');
      aplicarCondicoesDeVisibilidade();
    } catch (error) {
      console.error('Erro ao executar evento init do ecrã:', error);
      showDynamicFormToast(`Erro ao executar evento init: ${error.message}`, 'danger');
    }
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

                  navigateDynamic(`/generic/form/${det.tabela}/${pk}?${p.toString()}`);
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

              navigateDynamic(`/generic/form/${det.tabela}/?${params.toString()}`);
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
              navigateDynamic(`/generic/form/${det.tabela}/${id}`
                + `?return_to=${ret}`
                + `&detail_table=${det.tabela}`
                + `&detail_anchor=${id}`);
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

          <a href="${toDynamicAppRelativeUrl(a.CAMINHO, '#')}" target="_blank" class="sz_dynamic_anexo_link">
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
          navigateDynamic(`/generic/form/ANEXOS/${id}`);
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
    navigateDynamic(RETURN_URL, `/generic/view/${TABLE_NAME}/`);
    });
    // Eliminar
    document.getElementById('btnDelete')?.addEventListener('click', async () => {
      if (!RECORD_STAMP || !TABLE_NAME) return;

      if (hasScreenEventFlow('before_delete')) {
        try {
          const beforeDeleteResult = await runScreenEventHook('before_delete');
          if (isVisualEventCancelResult(beforeDeleteResult)) {
            showDynamicFormToast('Eliminação cancelada pelo evento before delete.', 'info');
            return;
          }
        } catch (error) {
          console.error('Erro ao executar evento before delete:', error);
          showDynamicFormToast(`Erro ao executar before delete: ${error.message}`, 'danger');
          return;
        }
      }

      if (!(await (window.szConfirmDelete?.('Pretende eliminar este registo?') ?? Promise.resolve(confirm('Confirmar elimina??o?'))))) return;

      try {
        const resp = await fetch(`/generic/api/${TABLE_NAME}/${RECORD_STAMP}`, { method: 'DELETE' });
        if (!resp.ok) {
          const err = await resp.json().catch(() => ({}));
          showDynamicFormToast('Erro: ' + (err.error || resp.statusText), 'danger');
          return;
        }
        queueDynamicFormToast('Registo eliminado.', 'success');
        navigateDynamic(RETURN_URL, `/generic/view/${TABLE_NAME}/`);
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
        navigateDynamic(RETURN_URL, `/generic/view/${TABLE_NAME}/`);
      } else {
        history.back();
      }
    });


    const userPerms = window.USER_PERMS[TABLE_NAME] || window.USER_PERMS[TABLE_NAME_UPPER] || {};

    // Se for edi??o (RECORD_STAMP), valida `editar` e `eliminar`
    if (RECORD_STAMP) {
      if (!isAdminUser && !userPerms.editar) {
        form.querySelectorAll('input, select, textarea').forEach(el => el.disabled = true);
        document.getElementById('btnSave').style.display = 'none';
        console.warn('[dynamic_form] Formul?rio desativado por falta de permiss?o de editar em ACESSOS para a tabela', TABLE_NAME_UPPER);
      }
      if (!isAdminUser && !userPerms.eliminar) {
        document.getElementById('btnDelete').style.display = 'none';
      }
    } else {
      // se for cria??o, valida `inserir`
      if (!isAdminUser && !userPerms.inserir) {
        document.getElementById('btnSave').style.display = 'none';
        console.warn('[dynamic_form] Bot?o gravar ocultado por falta de permiss?o de inserir em ACESSOS para a tabela', TABLE_NAME_UPPER);
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

    if (hasScreenEventFlow('before_save')) {
      try {
        const beforeSaveResult = await runScreenEventHook('before_save');
        if (isVisualEventCancelResult(beforeSaveResult)) {
          showDynamicFormToast('Gravação cancelada pelo evento before save.', 'info');
          return;
        }
      } catch (error) {
        console.error('Erro ao executar evento before save:', error);
        showDynamicFormToast(`Erro ao executar before save: ${error.message}`, 'danger');
        return;
      }
    }

    if (!form.checkValidity()) {
      form.classList.add('was-validated');
      showDynamicFormToast('Existem campos obrigat?rios por preencher.', 'warning');
      return;
    }

    const data = {};
    const uiOnlyControls = Array.from(form.querySelectorAll('[data-ui-only="true"]'));
    const temporarilyDisabled = [];
    uiOnlyControls.forEach(input => {
      if (input.disabled) return;
      input.disabled = true;
      temporarilyDisabled.push(input);
    });
    try {
      new FormData(form).forEach((v, k) => data[k] = v);
    } finally {
      temporarilyDisabled.forEach(input => {
        input.disabled = false;
      });
    }
    Object.entries(tableFieldTargetValues).forEach(([fieldName, value]) => {
      const targetName = normalizePhysicalFieldName(fieldName);
      if (targetName) data[targetName] = value;
    });
    // BIT para booleano
    form.querySelectorAll('input[type="checkbox"]').forEach(cb => {
      if (!cb.name || cb.dataset.uiOnly === 'true') return;
      data[cb.name] = cb.checked;
    });
    // Decimais usam vírgula mas o backend espera ponto
    form.querySelectorAll('input[data-decimal="true"]').forEach(input => {
      if (!input.name || input.dataset.uiOnly === 'true') return;
      data[input.name] = toServerDecimal(
        input.value,
        getDecimalPlacesForInput(input)
      );
    });
    // Datas para ISO
    form.querySelectorAll('.flatpickr-date').forEach(input => {
      if (!input.name || input.dataset.uiOnly === 'true') return;
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
      navigateDynamic(RETURN_URL, `/generic/view/${TABLE_NAME}/`);
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



