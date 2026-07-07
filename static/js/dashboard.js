// static/js/dashboard.js

document.querySelector('.main-content')?.classList.add('sz_dashboard_host');

// Utils -------------------------------------------------
function parseNumber(val) {
  if (val == null || val === '') return 0;
  const s = typeof val === 'string' ? val.replace(/\s/g, '').replace(',', '.') : val;
  const n = Number(s);
  return isNaN(n) ? 0 : n;
}
function isNumericLike(val) {
  if (typeof val === 'number') return Number.isFinite(val);
  if (typeof val !== 'string') return false;
  const s = val.trim();
  if (!s) return false;
  return /^[+-]?[\d\s,.]+$/.test(s) && !Number.isNaN(parseNumber(s));
}
function formatNumber(n) {
  const num = Number(n);
  if (isNaN(num)) return '';
  const rounded = Math.round(num);
  const sign = rounded < 0 ? '-' : '';
  const digits = String(Math.abs(rounded));
  return sign + digits.replace(/\B(?=(\d{3})+(?!\d))/g, ' ');
}
function formatTitle(str) {
  return str.replace(/_/g,' ').replace(/\b\w/g,l=>l.toUpperCase());
}
function escapeAttr(val) {
  return String(val ?? '')
    .replace(/&/g, '&amp;')
    .replace(/"/g, '&quot;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}
function normalizeWidgetUrl(url) {
  const raw = String(url || '').trim();
  if (!raw) return '';
  if (/^(https?:)?\/\//i.test(raw) || raw.startsWith('/')) return raw;
  return `/${raw.replace(/^\/+/, '')}`;
}

async function parseJsonResponse(resp, fallbackMessage) {
  const raw = await resp.text();
  try {
    return JSON.parse(raw);
  } catch (_) {
    const compact = String(raw || '').replace(/\s+/g, ' ').trim();
    const looksHtml = compact.startsWith('<!doctype') || compact.startsWith('<html') || compact.startsWith('<');
    const hint = looksHtml
      ? 'O servidor devolveu HTML em vez de JSON. Normalmente isto significa erro Flask/500 ou redirect para login.'
      : `Resposta invalida: ${compact.slice(0, 180)}`;
    throw new Error(`${fallbackMessage || 'Resposta invalida do servidor'} (${resp.status}). ${hint}`);
  }
}

function showDashboardError(message) {
  const cols = document.querySelectorAll('.sz_dashboard_col');
  cols.forEach((col) => {
    col.innerHTML = `<div class="sz_panel p-4 text-danger">${message}</div>`;
  });
}
function renderWidgetLoading(body) {
  if (!body) return;
  body.classList.remove('sz_dashboard_widget_body_loaded');
  body.classList.add('sz_dashboard_widget_body_loading');
  body.innerHTML = '<div class="sz_dashboard_widget_loading"><span class="sz_dashboard_loading_dot"></span><span>A carregar...</span></div>';
}
function revealWidget(body) {
  if (!body) return;
  body.classList.remove('sz_dashboard_widget_body_loading');
  body.classList.remove('sz_dashboard_widget_body_loaded');
  requestAnimationFrame(() => {
    body.classList.add('sz_dashboard_widget_body_loaded');
  });
}

// Loading ------------------------------------------------
function showLoading() {
  const overlay = document.getElementById('loadingOverlay');
  overlay.style.display = 'flex';
  setTimeout(() => overlay.style.opacity = '1', 15);
}
function hideLoading() {
  const overlay = document.getElementById('loadingOverlay');
  overlay.style.opacity = '0';
  setTimeout(() => overlay.style.display = 'none', 250);
}

// Filtros ------------------------------------------------
const widgetState = new Map(); // name -> {widget, body, filtersDef, currentFilters}
const dashboardLayoutState = {
  editing: false,
  dirty: false,
  columns: 3,
  widths: [33.34, 33.33, 33.33],
};
let dashboardShortcutScreens = [];
let dashboardHiddenWidgets = [];
const dashboardShortcutPalette = [
  '#5b9dff',
  '#36c690',
  '#ff5f9e',
  '#a875ff',
  '#f6a23a',
  '#49c6e5',
  '#ff6b6b',
  '#88d66c',
];
let dashboardShortcutColor = dashboardShortcutPalette[0];

function clampDashboardColumnCount(value) {
  const n = parseInt(value, 10);
  if (!Number.isFinite(n)) return 3;
  return Math.max(1, Math.min(5, n));
}

function normalizeDashboardWidths(widths, count = dashboardLayoutState.columns) {
  const colCount = clampDashboardColumnCount(count);
  const raw = Array.isArray(widths) ? widths : [];
  const values = Array.from({ length: colCount }, (_, index) => {
    const n = parseFloat(raw[index]);
    return Number.isFinite(n) && n > 0 ? n : 100 / colCount;
  });
  const total = values.reduce((sum, value) => sum + value, 0) || 1;
  return values.map((value) => Math.round((value / total) * 1000) / 10);
}

function setDashboardLayoutPreferences(settings = {}, options = {}) {
  const columns = clampDashboardColumnCount(settings.columns ?? dashboardLayoutState.columns);
  dashboardLayoutState.columns = columns;
  dashboardLayoutState.widths = normalizeDashboardWidths(settings.widths, columns);
  ensureDashboardColumns();
  applyDashboardGridTemplate();
  renderDashboardColumnWidthControls();
  if (options.markDirty) markDashboardLayoutDirty();
}

function closeDashboardContextMenu() {
  const menu = document.getElementById('dashboardContextMenu');
  if (!menu) return;
  menu.hidden = true;
  menu.style.left = '';
  menu.style.top = '';
}

function openDashboardContextMenu(x, y) {
  const menu = document.getElementById('dashboardContextMenu');
  if (!menu) return;
  menu.hidden = false;
  const rect = menu.getBoundingClientRect();
  const margin = 10;
  const left = Math.min(Math.max(margin, x), window.innerWidth - rect.width - margin);
  const top = Math.min(Math.max(margin, y), window.innerHeight - rect.height - margin);
  menu.style.left = `${left}px`;
  menu.style.top = `${top}px`;
}

function renderDashboardShortcutList(items) {
  const list = document.getElementById('dashboardShortcutList');
  if (!list) return;
  if (!Array.isArray(items) || !items.length) {
    list.innerHTML = '<div class="sz_dashboard_shortcut_empty">Sem ecrãs disponíveis.</div>';
    return;
  }
  list.innerHTML = items.map((item) => `
    <button type="button" class="sz_dashboard_shortcut_item" data-menustamp="${escapeAttr(item.menustamp)}">
      <span class="sz_dashboard_shortcut_icon"><i class="fa-solid ${escapeAttr(item.icon || 'fa-window-maximize')}"></i></span>
      <span class="sz_dashboard_shortcut_text">
        <strong>${escapeAttr(item.name)}</strong>
        <small>${escapeAttr(item.group || item.url || '')}</small>
      </span>
      <i class="fa-solid fa-plus"></i>
    </button>
  `).join('');
}

function renderDashboardShortcutColors() {
  const host = document.getElementById('dashboardShortcutColors');
  if (!host) return;
  host.innerHTML = dashboardShortcutPalette.map((color) => `
    <button
      type="button"
      class="sz_dashboard_shortcut_color${color === dashboardShortcutColor ? ' is-selected' : ''}"
      data-shortcut-color="${escapeAttr(color)}"
      style="--shortcut-color: ${escapeAttr(color)}"
      aria-label="Cor ${escapeAttr(color)}">
    </button>
  `).join('');
}

function filterDashboardShortcutList() {
  const search = String(document.getElementById('dashboardShortcutSearch')?.value || '').trim().toLowerCase();
  if (!search) {
    renderDashboardShortcutList(dashboardShortcutScreens);
    return;
  }
  renderDashboardShortcutList(dashboardShortcutScreens.filter((item) => {
    const haystack = `${item.name || ''} ${item.group || ''} ${item.url || ''}`.toLowerCase();
    return haystack.includes(search);
  }));
}

async function openDashboardShortcutModal() {
  const modalEl = document.getElementById('dashboardShortcutModal');
  const search = document.getElementById('dashboardShortcutSearch');
  const titleInput = document.getElementById('dashboardShortcutTitle');
  const urlInput = document.getElementById('dashboardShortcutUrl');
  if (!modalEl) return;
  if (search) search.value = '';
  if (titleInput) titleInput.value = '';
  if (urlInput) urlInput.value = '';
  dashboardShortcutColor = dashboardShortcutColor || dashboardShortcutPalette[0];
  renderDashboardShortcutColors();
  renderDashboardShortcutList([]);
  const modal = bootstrap.Modal.getOrCreateInstance(modalEl);
  modal.show();
  const list = document.getElementById('dashboardShortcutList');
  if (list) list.innerHTML = '<div class="sz_dashboard_shortcut_empty">A carregar...</div>';
  try {
    const resp = await fetch('/api/dashboard/shortcuts/screens');
    const data = await parseJsonResponse(resp, 'Erro ao carregar ecrãs');
    if (!resp.ok || data.error) throw new Error(data.error || 'Erro ao carregar ecrãs.');
    dashboardShortcutScreens = Array.isArray(data.screens) ? data.screens : [];
    renderDashboardShortcutList(dashboardShortcutScreens);
  } catch (error) {
    console.error(error);
    if (list) list.innerHTML = `<div class="sz_dashboard_shortcut_empty is-error">${escapeAttr(error.message || 'Erro ao carregar ecrãs.')}</div>`;
  }
}

async function addDashboardShortcut(payload, button) {
  const body = typeof payload === 'string'
    ? { menustamp: String(payload || '').trim(), color: dashboardShortcutColor }
    : { ...(payload || {}), color: dashboardShortcutColor };
  if (!body.menustamp && !body.url) return;
  if (button) button.disabled = true;
  try {
    const resp = await fetch('/api/dashboard/shortcuts', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    const data = await parseJsonResponse(resp, 'Erro ao adicionar atalho');
    if (!resp.ok || data.error) throw new Error(data.error || 'Erro ao adicionar atalho.');
    bootstrap.Modal.getInstance(document.getElementById('dashboardShortcutModal'))?.hide();
    loadDashboard();
  } catch (error) {
    console.error(error);
    alert(error.message || 'Erro ao adicionar atalho.');
  } finally {
    if (button) button.disabled = false;
  }
}

async function addDashboardScreenShortcut(menustamp) {
  const stamp = String(menustamp || '').trim();
  if (!stamp) return;
  const button = Array.from(document.querySelectorAll('.sz_dashboard_shortcut_item'))
    .find((item) => String(item.dataset.menustamp || '') === stamp);
  addDashboardShortcut({ menustamp: stamp }, button);
}

function addDashboardUrlShortcut() {
  const titleInput = document.getElementById('dashboardShortcutTitle');
  const urlInput = document.getElementById('dashboardShortcutUrl');
  const title = String(titleInput?.value || '').trim();
  const url = String(urlInput?.value || '').trim();
  if (!url) {
    alert('Indica o URL do atalho.');
    urlInput?.focus();
    return;
  }
  addDashboardShortcut({ title, url }, document.getElementById('dashboardShortcutUrlBtn'));
}

function renderDashboardWidgetList(items) {
  const list = document.getElementById('dashboardWidgetList');
  if (!list) return;
  if (!Array.isArray(items) || !items.length) {
    list.innerHTML = '<div class="sz_dashboard_shortcut_empty">Sem widgets invisíveis.</div>';
    return;
  }
  list.innerHTML = items.map((item) => `
    <button type="button" class="sz_dashboard_shortcut_item" data-widget-id="${escapeAttr(item.NOME || item.nome || '')}">
      <span class="sz_dashboard_shortcut_icon"><i class="fa-solid fa-table-cells-large"></i></span>
      <span class="sz_dashboard_shortcut_text">
        <strong>${escapeAttr(item.TITULO || item.titulo || item.NOME || item.nome || '')}</strong>
        <small>${escapeAttr(item.TIPO || item.tipo || item.FONTE || item.fonte || '')}</small>
      </span>
      <i class="fa-solid fa-plus"></i>
    </button>
  `).join('');
}

function filterDashboardWidgetList() {
  const search = String(document.getElementById('dashboardWidgetSearch')?.value || '').trim().toLowerCase();
  if (!search) {
    renderDashboardWidgetList(dashboardHiddenWidgets);
    return;
  }
  renderDashboardWidgetList(dashboardHiddenWidgets.filter((item) => {
    const haystack = `${item.NOME || item.nome || ''} ${item.TITULO || item.titulo || ''} ${item.TIPO || item.tipo || ''}`.toLowerCase();
    return haystack.includes(search);
  }));
}

async function openDashboardWidgetModal() {
  const modalEl = document.getElementById('dashboardWidgetModal');
  const search = document.getElementById('dashboardWidgetSearch');
  if (!modalEl) return;
  if (search) search.value = '';
  const modal = bootstrap.Modal.getOrCreateInstance(modalEl);
  modal.show();
  const list = document.getElementById('dashboardWidgetList');
  if (list) list.innerHTML = '<div class="sz_dashboard_shortcut_empty">A carregar...</div>';
  try {
    const resp = await fetch('/api/dashboard/widgets/hidden');
    const data = await parseJsonResponse(resp, 'Erro ao carregar widgets');
    if (!resp.ok || data.error) throw new Error(data.error || 'Erro ao carregar widgets.');
    dashboardHiddenWidgets = Array.isArray(data.widgets) ? data.widgets : [];
    renderDashboardWidgetList(dashboardHiddenWidgets);
  } catch (error) {
    console.error(error);
    if (list) list.innerHTML = `<div class="sz_dashboard_shortcut_empty is-error">${escapeAttr(error.message || 'Erro ao carregar widgets.')}</div>`;
  }
}

async function showDashboardWidget(widgetId) {
  const id = String(widgetId || '').trim();
  if (!id) return;
  const button = Array.from(document.querySelectorAll('.sz_dashboard_shortcut_item'))
    .find((item) => String(item.dataset.widgetId || '') === id);
  if (button) button.disabled = true;
  try {
    const resp = await fetch(`/api/dashboard/widgets/${encodeURIComponent(id)}/show`, { method: 'POST' });
    const data = await parseJsonResponse(resp, 'Erro ao mostrar widget');
    if (!resp.ok || data.error) throw new Error(data.error || 'Erro ao mostrar widget.');
    bootstrap.Modal.getInstance(document.getElementById('dashboardWidgetModal'))?.hide();
    loadDashboard();
  } catch (error) {
    console.error(error);
    alert(error.message || 'Erro ao mostrar widget.');
  } finally {
    if (button) button.disabled = false;
  }
}

async function hideDashboardItem(element) {
  if (!element) return;
  const kind = String(element.dataset.dashboardKind || '').trim();
  const id = String(element.dataset.dashboardId || '').trim();
  if (!kind || !id) return;
  const ok = window.confirm('Remover este widget do dashboard?');
  if (!ok) return;
  try {
    const resp = await fetch('/api/dashboard/items/hide', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ kind, id }),
    });
    const data = await parseJsonResponse(resp, 'Erro ao remover widget');
    if (!resp.ok || data.error) throw new Error(data.error || 'Erro ao remover widget.');
    element.remove();
  } catch (error) {
    console.error(error);
    alert(error.message || 'Erro ao remover widget.');
  }
}

async function removeDashboardShortcut(linkId) {
  if (!dashboardLayoutState.editing) return;
  const id = String(linkId || '').trim();
  if (!id) return;
  const ok = window.confirm('Remover este atalho?');
  if (!ok) return;
  try {
    const resp = await fetch(`/api/dashboard/shortcuts/${encodeURIComponent(id)}`, { method: 'DELETE' });
    const data = await parseJsonResponse(resp, 'Erro ao remover atalho');
    if (!resp.ok || data.error) throw new Error(data.error || 'Erro ao remover atalho.');
    loadDashboard();
  } catch (error) {
    console.error(error);
    alert(error.message || 'Erro ao remover atalho.');
  }
}

function parseFiltersDef(widget) {
  try {
    const js = JSON.parse(widget.filtros || '{}');
    return Array.isArray(js.fields) ? js.fields : [];
  } catch { return []; }
}
function resolveDefault(val) {
  if (val === 'CURRENT_YEAR') return new Date().getFullYear();
  return val;
}
function buildDefaultFilters(fields) {
  const obj = {};
  fields.forEach(f => { if (f && f.key) obj[f.key] = resolveDefault(f.default); });
  return obj;
}
async function fetchOptions(widgetId, field) {
  if (field.options_source !== 'query' || !field.options_query) return [];
  const resp = await fetch(`/api/widgets/${encodeURIComponent(widgetId)}/filters/options`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ options_query: field.options_query })
  });
  const js = await parseJsonResponse(resp, `Erro ao carregar opcoes do widget ${widgetId}`);
  if (!resp.ok || js.error) throw new Error(js.error || 'Erro ao carregar opcoes');
  return Array.isArray(js.options) ? js.options : [];
}

function ensureFiltersModal(widget, fields) {
  const modalId = `widget-filters-${widget.nome}`;
  if (document.getElementById(modalId)) return modalId;
  const modal = document.createElement('div');
  modal.className = 'modal fade sz_dashboard_filters_modal';
  modal.id = modalId;
  modal.tabIndex = -1;
  modal.innerHTML = `
    <div class="modal-dialog modal-dialog-centered">
      <div class="modal-content sz_panel">
        <div class="modal-header sz_modal_header sz_dynamic_filters_header">
          <h3 class="sz_h4 sz_modal_title"><i class="fa-solid fa-filter me-2"></i>Filtros - ${widget.titulo || widget.nome}</h3>
          <button type="button" class="btn-close sz_dashboard_filters_close" data-bs-dismiss="modal" aria-label="Fechar"></button>
        </div>
        <div class="modal-body sz_modal_body">
          <form id="${modalId}-form" class="sz_dynamic_filters_form"></form>
        </div>
        <div class="modal-footer sz_modal_footer">
          <button type="button" class="sz_button sz_button_ghost" data-bs-dismiss="modal">Cancelar</button>
          <button type="button" class="sz_button sz_button_primary" id="${modalId}-apply">Aplicar</button>
        </div>
      </div>
    </div>`;
  document.body.appendChild(modal);

  const form = modal.querySelector('form');
  fields.forEach(f => {
    const wrap = document.createElement('div');
    wrap.className = 'sz_field';
    const label = document.createElement('label');
    label.className = 'sz_label';
    label.textContent = f.label || f.key;
    label.htmlFor = `${modalId}-${f.key}`;
    wrap.appendChild(label);

    let input;
    if (f.input_type === 'select') {
      input = document.createElement('select');
      input.className = 'sz_select';
      input.innerHTML = '<option value="">---</option>';
      if (f.options_source !== 'query' && Array.isArray(f.options)) {
        f.options.forEach(opt => {
          const o = document.createElement('option');
          o.value = opt.value;
          o.textContent = opt.label;
          input.appendChild(o);
        });
      }
      if (f.options_source === 'query') {
        fetchOptions(widget.nome, f).then(opts => {
          opts.forEach(opt => {
            const o = document.createElement('option');
            o.value = opt.value;
            o.textContent = opt.label;
            input.appendChild(o);
          });
        }).catch(()=>{});
      }
    } else {
      input = document.createElement('input');
      input.type = f.input_type || 'text';
      input.className = (f.input_type === 'number') ? 'sz_input_number' : 'sz_input';
    }
    input.id = `${modalId}-${f.key}`;
    input.dataset.key = f.key;
    if (f.required) input.required = true;
    wrap.appendChild(input);
    form.appendChild(wrap);
  });

  document.getElementById(`${modalId}-apply`).addEventListener('click', () => applyFilters(widget.nome));
  return modalId;
}

function openFilters(widgetName) {
  const state = widgetState.get(widgetName);
  if (!state) return;
  const modalId = ensureFiltersModal(state.widget, state.filtersDef);
  const form = document.getElementById(`${modalId}-form`);
  if (!form) return;
  const vals = Object.keys(state.currentFilters || {}).length ? state.currentFilters : buildDefaultFilters(state.filtersDef);
  Array.from(form.elements).forEach(el => {
    const key = el.dataset.key;
    if (!key) return;
    el.value = vals[key] ?? '';
  });
  bootstrap.Modal.getOrCreateInstance(document.getElementById(modalId)).show();
}

async function applyFilters(widgetName) {
  const state = widgetState.get(widgetName);
  if (!state) return;
  const modalId = `widget-filters-${widgetName}`;
  const form = document.getElementById(`${modalId}-form`);
  if (!form) return;
  const filters = {};
  Array.from(form.elements).forEach(el => {
    const key = el.dataset.key;
    if (!key) return;
    if (el.value !== '') filters[key] = el.value;
  });
  state.currentFilters = filters;
  const data = await runWidget(widgetName, filters);
  renderDataIntoWidget(state, data);
  bootstrap.Modal.getInstance(document.getElementById(modalId))?.hide();
}

async function runWidget(widgetName, filters) {
  const resp = await fetch(`/api/widgets/${encodeURIComponent(widgetName)}/run`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ filters: filters || {} })
  });
  const js = await parseJsonResponse(resp, `Erro ao executar widget ${widgetName}`);
  if (!resp.ok || js.error) throw new Error(js.error || 'Falha ao executar widget');
  return js;
}

function renderDataIntoWidget(state, data) {
  const { widget, body } = state;
  if (widget.tipo === 'ANALISE') renderAnalise(body, data);
  else if (widget.tipo === 'GRAFICO') renderGrafico(body, widget, data);
  applyWidgetTableClass(body);
}

function parseDashboardHeight(value, fallback = 0) {
  if (value === null || value === undefined || value === '') return fallback;
  const n = parseInt(value, 10);
  return Number.isFinite(n) && n >= 0 ? n : fallback;
}

function applyDashboardWidgetHeight(widgetEl, body, height, tipo) {
  if (!widgetEl || !body) return;
  const requestedHeight = parseDashboardHeight(height, 0);
  widgetEl.dataset.dashboardHeight = String(requestedHeight);
  widgetEl.classList.remove('expanded');
  widgetEl.classList.toggle('is-dashboard-height-full', requestedHeight === 0);
  if (requestedHeight === 0) {
    body.style.height = '';
    body.style.maxHeight = 'none';
    body.style.overflowY = tipo === 'GRAFICO' ? 'hidden' : 'visible';
    return;
  }
  if (tipo === 'GRAFICO') {
    body.style.height = `${requestedHeight}px`;
    body.style.maxHeight = `${requestedHeight}px`;
    body.style.overflowY = 'hidden';
  } else {
    body.style.height = '';
    body.style.maxHeight = `${requestedHeight}px`;
    body.style.overflowY = 'auto';
  }
}

function getDashboardWidgetExpandedHeight(widgetEl) {
  const body = widgetEl?.querySelector('.sz_dashboard_widget_body');
  if (!body) return 0;
  const previousMaxHeight = body.style.maxHeight;
  const previousHeight = body.style.height;
  const previousOverflow = body.style.overflowY;
  body.style.maxHeight = 'none';
  body.style.height = '';
  body.style.overflowY = 'visible';
  const expandedHeight = Math.ceil(Math.max(body.scrollHeight, body.offsetHeight, body.clientHeight));
  body.style.maxHeight = previousMaxHeight;
  body.style.height = previousHeight;
  body.style.overflowY = previousOverflow;
  return expandedHeight;
}

// Render -------------------------------------------------
function applyWidgetTableClass(body) {
  if (!body) return;
  body.querySelectorAll('table').forEach((table) => {
    table.classList.add('sz_dashboard_widget_table');
  });
}

function renderAnalise(body, data) {
  if (data.error) {
    body.innerHTML = `<span class="error-msg">${data.error}</span>`;
    return;
  }
  if (!Array.isArray(data.rows) || data.rows.length === 0) {
    body.innerHTML = `<div class="sz_dashboard_grid_empty">Sem dados</div>`;
    return;
  }

  const numericCols = data.columns.filter(c =>
    data.rows.every(row => {
      const v = row[c];
      return isNumericLike(v);
    })
  );

  const dateCols = data.columns.filter(c =>
    data.rows.every(row => {
      const v = row[c];
      return v != null && isNaN(parseNumber(v)) && !isNaN(Date.parse(v));
    })
  );

  const totals = {};
  numericCols.forEach(c => totals[c] = 0);
  data.rows.forEach(row => numericCols.forEach(c => { totals[c] += parseNumber(row[c]); }));

  let html = '<div class="sz_dashboard_grid_wrap"><table class="sz_dashboard_grid_table sz_dashboard_widget_table">';
  html += '<thead><tr>' +
    data.columns.map(c =>
      `<th${numericCols.includes(c) ? ' class="num"' : ''}>${c}</th>`
    ).join('') +
  '</tr></thead>';

  html += '<tbody>' +
    data.rows.map(row => '<tr>' +
      data.columns.map(c => {
        if (dateCols.includes(c)) {
          const d = new Date(row[c]);
          const dd = String(d.getDate()).padStart(2,'0');
          const mm = String(d.getMonth()+1).padStart(2,'0');
          const yyyy = d.getFullYear();
          return `<td>${dd}.${mm}.${yyyy}</td>`;
        }
        if (numericCols.includes(c)) {
          return `<td class="num">${formatNumber(parseNumber(row[c]))}</td>`;
        }
        return `<td>${row[c]}</td>`;
      }).join('') +
    '</tr>').join('') +
  '</tbody>';

  if (numericCols.length > 0) {
    html += '<tfoot><tr>' +
      data.columns.map((c,i) => {
        if (i === 0) return '<td>Total</td>';
        if (numericCols.includes(c)) {
          return `<td class="num">${formatNumber(totals[c])}</td>`;
        }
        return '<td></td>';
      }).join('') +
    '</tr></tfoot>';
  }

  html += '</table></div>';
  body.innerHTML = html;
}

function renderGrafico(body, widget, data) {
  if (data.error) {
    body.innerHTML = `<span class="error-msg">${data.error}</span>`;
    return;
  }
  let cfg = {};
  try { cfg = JSON.parse(widget.config || '{}'); } catch {}
  const chartType = cfg.tipo_grafico || 'bar';
  const labelCol = cfg.label_col || data.columns[0];
  const dataCol = cfg.data_col || data.columns[1];
  const stackCol = cfg.stack_col || null;
  const uiMode = String(cfg.ui_style || '').toLowerCase();
  const useGanttLook = uiMode === 'gantt' || uiMode === 'modern';
  const showLegend = (cfg.legend ?? (stackCol ? true : false)) === true;
  const gridColor = cfg.grid_color || (useGanttLook ? 'rgba(148,163,184,0.22)' : '#e0e0e0');
  const tickColor = cfg.tick_color || (useGanttLook ? '#334155' : '#64748b');
  const barRadius = 0;
  const barThickness = Number.isFinite(+cfg.bar_thickness) ? +cfg.bar_thickness : undefined;
  const barAlpha = Number.isFinite(+cfg.bar_alpha) ? Math.max(0, Math.min(1, +cfg.bar_alpha)) : (useGanttLook ? 0.34 : 0.6);
  const radiusValue = 0;

  const hexToRgba = (hex, alpha = 1) => {
    if (!hex || typeof hex !== 'string') return `rgba(59,130,246,${alpha})`;
    const h = hex.replace('#', '').trim();
    if (h.length !== 3 && h.length !== 6) return hex;
    const full = h.length === 3 ? h.split('').map(c => c + c).join('') : h;
    const num = parseInt(full, 16);
    if (Number.isNaN(num)) return hex;
    const r = (num >> 16) & 255;
    const g = (num >> 8) & 255;
    const b = num & 255;
    return `rgba(${r},${g},${b},${alpha})`;
  };

  const borderFromColor = (color) => {
    if (typeof color === 'string' && color.startsWith('#')) return hexToRgba(color, 0.95);
    if (typeof color === 'string' && color.startsWith('rgba(')) return color.replace(/,\s*([0-9.]+)\)/, ',0.95)');
    return color;
  };

  const labels = stackCol
    ? Array.from(new Map(data.rows.map(r => [r[labelCol], r[labelCol]])).values())
    : data.rows.map(r => r[labelCol]);

  let datasets = [];

  if (stackCol) {
    const stacks = [...new Set(data.rows.map(r => r[stackCol]))];
    const palette = cfg.stack_colors || {};
    datasets = stacks.map((stack, idx) => {
      const baseHue = Math.round(idx * 360 / Math.max(stacks.length,1));
      const baseColor = palette[stack] || `hsl(${baseHue}, 65%, 55%)`;
      const fillColor = String(baseColor).startsWith('#')
        ? hexToRgba(baseColor, barAlpha)
        : String(baseColor).startsWith('hsl(')
          ? baseColor.replace('hsl(', 'hsla(').replace(')', `, ${barAlpha})`)
          : baseColor;
      const vals = labels.map(label =>
        data.rows
          .filter(r => r[labelCol] === label && r[stackCol] === stack)
          .reduce((sum, row) => sum + parseNumber(row[dataCol]), 0)
      );
      return {
        label: stack,
        data: vals,
        backgroundColor: fillColor,
        borderColor: borderFromColor(baseColor),
        borderWidth: useGanttLook ? 1.6 : 1,
        borderRadius: radiusValue,
        borderSkipped: false,
        barThickness
      };
    });
  } else {
    const values = data.rows.map(r => parseNumber(r[dataCol]));
    const dataset = { label: widget.titulo || widget.nome, data: values };
    if (chartType === 'bar' || chartType === 'line') {
      const baseColor = cfg.color || '#38bdf8';
      Object.assign(dataset, {
        backgroundColor: String(baseColor).startsWith('#') ? hexToRgba(baseColor, barAlpha) : baseColor,
        borderColor: borderFromColor(baseColor),
        borderWidth: useGanttLook ? 1.6 : 1,
        borderRadius: radiusValue,
        borderSkipped: false,
        barThickness
      });
    } else {
      dataset.backgroundColor = labels.map((_,i) => `hsl(${Math.round(i*360/labels.length)},70%,60%)`);
      dataset.borderWidth = 1;
    }
    datasets = [dataset];
  }

  body.innerHTML = '';
  const canvas = document.createElement('canvas');
  canvas.style.width = '100%';
  canvas.style.height = '100%';
  body.appendChild(canvas);
  new Chart(canvas.getContext('2d'), {
    type: chartType,
    data: { labels, datasets },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          display: showLegend,
          labels: {
            color: tickColor,
            boxWidth: 10,
            boxHeight: 10,
            useBorderRadius: true,
            borderRadius: 3
          }
        },
        tooltip: {
          backgroundColor: useGanttLook ? 'rgba(255,251,235,0.98)' : 'rgba(15,23,42,0.92)',
          titleColor: useGanttLook ? '#111827' : '#fff',
          bodyColor: useGanttLook ? '#111827' : '#fff',
          borderColor: useGanttLook ? '#e5e7eb' : 'rgba(15,23,42,0.92)',
          borderWidth: 1
        }
      },
      scales: (chartType === 'bar' || chartType === 'line') ? {
        x: {
          stacked: !!stackCol,
          grid: { display: false },
          ticks: { color: tickColor, font: { size: useGanttLook ? 11 : 10, weight: useGanttLook ? 600 : 400 } }
        },
        y: {
          stacked: !!stackCol,
          beginAtZero: true,
          grid: { display: true, color: gridColor, borderDash: useGanttLook ? [4, 4] : [] },
          ticks: { color: tickColor, font: { size: useGanttLook ? 11 : 10 } }
        }
      } : {}
    }
  });
}

// Render widget entry point --------------------------------------------
async function renderWidget(widget, colDiv) {
  const filtersDef = parseFiltersDef(widget);
  const hasFilters = filtersDef.length > 0;
  const widgetUrl = normalizeWidgetUrl(widget.url);

  const wDiv = document.createElement('div');
  wDiv.className = 'sz_dashboard_widget sz_dashboard_widget_' + widget.tipo.toLowerCase();
  wDiv.dataset.dashboardKind = 'widget';
  wDiv.dataset.dashboardId = widget.nome || widget.id || '';
  wDiv.classList.add('sz_dashboard_draggable');
  const linkBtn = widgetUrl
    ? `<button class="sz_button sz_button_ghost sz_dashboard_link_btn widget-link-btn" data-url="${escapeAttr(widgetUrl)}" title="Abrir indicador"><i class="fa-solid fa-arrow-up-right-from-square"></i></button>`
    : '';
  const filterBtn = hasFilters
    ? `<button class="sz_button sz_button_ghost sz_dashboard_filter_btn widget-filter-btn" data-widget="${widget.nome}" title="Filtros"><i class="fa fa-filter"></i></button>`
    : '';
  wDiv.innerHTML = `
    <button type="button" class="sz_dashboard_item_remove_btn" data-dashboard-remove-item title="Remover widget">
      <i class="fa-solid fa-xmark"></i>
    </button>
    <div class="sz_dashboard_widget_header">
      <h3 class="sz_h2 sz_dashboard_widget_title">${widget.titulo || formatTitle(widget.nome)}</h3>
      <div class="sz_dashboard_widget_tools">
        ${linkBtn}
        ${filterBtn}
        <button class="sz_dashboard_expand_btn" title="Expandir">&#8693;</button>
      </div>
    </div>
    <div class="sz_dashboard_widget_body"></div>
    <div class="sz_dashboard_widget_resize_handle" data-dashboard-resize-widget title="Ajustar altura"></div>
  `;
  colDiv.appendChild(wDiv);
  syncDashboardItemDragState(wDiv);

  const body = wDiv.querySelector('.sz_dashboard_widget_body');
  const expandBtn = wDiv.querySelector('.sz_dashboard_expand_btn');
  expandBtn.style.display = 'none';

  const hasStoredMaxHeight = widget.maxheight !== null && widget.maxheight !== undefined && widget.maxheight !== '';
  let maxH = hasStoredMaxHeight ? parseDashboardHeight(widget.maxheight, 0) : 0;
  try {
    const cfg = JSON.parse(widget.config || '{}');
    if (!hasStoredMaxHeight && cfg.maxheight) maxH = parseDashboardHeight(cfg.maxheight, 0);
  } catch {}
  applyDashboardWidgetHeight(wDiv, body, maxH, widget.tipo);
  if (widget.tipo === 'GRAFICO' && !maxH) {
    body.style.minHeight = '240px';
  }

  const toggleExpandBtn = () => {
    if (maxH && body.scrollHeight > body.clientHeight) expandBtn.style.display = '';
    else expandBtn.style.display = 'none';
  };
  expandBtn.addEventListener('click', () => wDiv.classList.toggle('expanded'));
  const linkBtnEl = wDiv.querySelector('.widget-link-btn');
  if (linkBtnEl) {
    linkBtnEl.addEventListener('click', () => {
      const url = normalizeWidgetUrl(linkBtnEl.dataset.url);
      if (url) window.location.href = url;
    });
  }

  if (hasFilters) {
    widgetState.set(widget.nome, { widget, body, filtersDef, currentFilters: buildDefaultFilters(filtersDef) });
    const btn = wDiv.querySelector('.widget-filter-btn');
    if (btn) btn.addEventListener('click', () => openFilters(widget.nome));
  }

  renderWidgetLoading(body);

  try {
    if (widget.tipo === 'ANALISE' || widget.tipo === 'GRAFICO') {
      const state = widgetState.get(widget.nome) || { widget, body, filtersDef, currentFilters: {} };
      const filters = hasFilters ? (state.currentFilters || buildDefaultFilters(filtersDef)) : {};
      const data = await runWidget(widget.nome, filters);
      widgetState.set(widget.nome, { widget, body, filtersDef, currentFilters: filters });
      renderDataIntoWidget(widgetState.get(widget.nome), data);
      revealWidget(body);
    } else if (widget.tipo === 'HTML') {
      body.innerHTML = widget.config || '<em>(sem conteudo)</em>';
      applyWidgetTableClass(body);
      revealWidget(body);
    }
  } catch (err) {
    body.innerHTML = `<span class="error-msg">Erro: ${err.message}</span>`;
    revealWidget(body);
  } finally {
    toggleExpandBtn();
  }
}

function renderDashboardLinksItem(item, colDiv) {
  const temp = document.createElement('div');
  temp.innerHTML = item.html || '';
  const element = temp.firstElementChild;
  if (!element) return;
  element.dataset.dashboardKind = 'links';
  element.dataset.dashboardId = item.id || '';
  element.classList.add('sz_dashboard_draggable');
  const removeItemBtn = document.createElement('button');
  removeItemBtn.type = 'button';
  removeItemBtn.className = 'sz_dashboard_item_remove_btn';
  removeItemBtn.dataset.dashboardRemoveItem = '1';
  removeItemBtn.title = 'Remover widget';
  removeItemBtn.innerHTML = '<i class="fa-solid fa-xmark"></i>';
  element.prepend(removeItemBtn);
  element.querySelectorAll('.dashboard-link-btn[data-dashboard-link-id]').forEach((link) => {
    const linkId = String(link.dataset.dashboardLinkId || '').trim();
    if (!linkId || link.parentElement?.classList.contains('dashboard-link-wrap')) return;
    const wrap = document.createElement('div');
    wrap.className = 'dashboard-link-wrap';
    wrap.dataset.dashboardLinkId = linkId;
    link.replaceWith(wrap);
    wrap.appendChild(link);
    const removeLinkBtn = document.createElement('button');
    removeLinkBtn.type = 'button';
    removeLinkBtn.className = 'dashboard-link-remove-btn';
    removeLinkBtn.dataset.dashboardRemoveShortcut = linkId;
    removeLinkBtn.title = 'Remover atalho';
    removeLinkBtn.innerHTML = '<i class="fa-solid fa-xmark"></i>';
    wrap.appendChild(removeLinkBtn);
  });
  colDiv.appendChild(element);
  syncDashboardItemDragState(element);
}

function dashboardGrid() {
  return document.querySelector('.sz_dashboard_grid');
}

function ensureDashboardColumns() {
  const grid = dashboardGrid();
  if (!grid) return;
  const count = clampDashboardColumnCount(dashboardLayoutState.columns);
  for (let col = 1; col <= count; col += 1) {
    if (!document.getElementById(`col-${col}`)) {
      const column = document.createElement('div');
      column.className = 'sz_dashboard_col';
      column.id = `col-${col}`;
      grid.appendChild(column);
    }
  }
  const lastVisibleColumn = document.getElementById(`col-${count}`);
  if (lastVisibleColumn) {
    Array.from(grid.querySelectorAll('.sz_dashboard_col')).forEach((column) => {
      const colNo = parseInt(String(column.id || '').replace('col-', ''), 10);
      if (Number.isFinite(colNo) && colNo > count) {
        Array.from(column.children).forEach((child) => lastVisibleColumn.appendChild(child));
      }
    });
  }
  Array.from(grid.querySelectorAll('.sz_dashboard_col')).forEach((column) => {
    const colNo = parseInt(String(column.id || '').replace('col-', ''), 10);
    column.hidden = !Number.isFinite(colNo) || colNo < 1 || colNo > count;
  });
  bindDashboardColumnDragEvents();
}

function applyDashboardGridTemplate() {
  const grid = dashboardGrid();
  if (!grid) return;
  const count = clampDashboardColumnCount(dashboardLayoutState.columns);
  const widths = normalizeDashboardWidths(dashboardLayoutState.widths, count);
  grid.style.gridTemplateColumns = widths.map((value) => `minmax(0, ${value}fr)`).join(' ');
  grid.style.setProperty('--sz-dashboard-column-count', String(count));
}

function renderDashboardColumnWidthControls() {
  const countInput = document.getElementById('dashboardColumnCount');
  const host = document.getElementById('dashboardColumnWidthControls');
  if (countInput) countInput.value = String(clampDashboardColumnCount(dashboardLayoutState.columns));
  if (!host) return;
  const count = clampDashboardColumnCount(dashboardLayoutState.columns);
  const widths = normalizeDashboardWidths(dashboardLayoutState.widths, count);
  host.innerHTML = widths.map((width, index) => `
    <div class="sz_dashboard_column_width">
      <label class="sz_label" for="dashboardColumnWidth${index + 1}">
        <span>Coluna ${index + 1}</span>
        <strong>${width.toFixed(1)}%</strong>
      </label>
      <input
        id="dashboardColumnWidth${index + 1}"
        class="sz_dashboard_column_width_range"
        type="range"
        min="10"
        max="80"
        step="1"
        value="${Math.round(width)}"
        data-dashboard-column-width="${index}">
    </div>
  `).join('');
}

function dashboardColumns() {
  return Array.from(document.querySelectorAll('.sz_dashboard_col:not([hidden])'));
}

function dashboardItems(root = document) {
  return Array.from(root.querySelectorAll('.sz_dashboard_draggable'));
}

function dashboardShortcutItems(root = document) {
  return Array.from(root.querySelectorAll('.dashboard-link-wrap[data-dashboard-link-id]'));
}

function syncDashboardItemDragState(item) {
  if (!item) return;
  item.draggable = dashboardLayoutState.editing;
  item.classList.toggle('is-dashboard-layout-editable', dashboardLayoutState.editing);
}

function syncDashboardShortcutDragState(item) {
  if (!item) return;
  item.draggable = dashboardLayoutState.editing;
  item.classList.toggle('is-dashboard-shortcut-editable', dashboardLayoutState.editing);
}

function syncDashboardLayoutControls() {
  const saveBtn = document.getElementById('dashboardSaveLayoutBtn');
  const cancelBtn = document.getElementById('dashboardCancelLayoutBtn');
  const layoutBar = document.getElementById('dashboardLayoutBar');
  if (saveBtn) saveBtn.hidden = !dashboardLayoutState.editing;
  if (cancelBtn) cancelBtn.hidden = !dashboardLayoutState.editing;
  if (layoutBar) layoutBar.hidden = !dashboardLayoutState.editing;
  document.body?.classList.toggle('sz_dashboard_layout_editing', dashboardLayoutState.editing);
  dashboardItems().forEach(syncDashboardItemDragState);
  dashboardShortcutItems().forEach(syncDashboardShortcutDragState);
  if (dashboardLayoutState.editing) closeDashboardContextMenu();
}

function setDashboardLayoutMode(editing) {
  dashboardLayoutState.editing = Boolean(editing);
  dashboardLayoutState.dirty = false;
  syncDashboardLayoutControls();
}

function markDashboardLayoutDirty() {
  dashboardLayoutState.dirty = true;
}

function getDashboardDragAfterElement(container, y) {
  const draggableElements = Array.from(container.querySelectorAll('.sz_dashboard_draggable:not(.is-dragging)'));
  return draggableElements.reduce((closest, child) => {
    const box = child.getBoundingClientRect();
    const offset = y - box.top - box.height / 2;
    if (offset < 0 && offset > closest.offset) {
      return { offset, element: child };
    }
    return closest;
  }, { offset: Number.NEGATIVE_INFINITY, element: null }).element;
}

function getDashboardShortcutAfterElement(container, x, y) {
  const items = Array.from(container.querySelectorAll('.dashboard-link-wrap:not(.is-shortcut-dragging)'));
  return items.find((child) => {
    const box = child.getBoundingClientRect();
    const midY = box.top + box.height / 2;
    const midX = box.left + box.width / 2;
    return y < midY || (y <= box.bottom && x < midX);
  }) || null;
}

function serializeDashboardLayout() {
  const columns = {};
  dashboardColumns().forEach((col) => {
    const colNo = String(col.id || '').replace('col-', '');
    columns[colNo] = dashboardItems(col)
      .map((item) => ({
        kind: String(item.dataset.dashboardKind || '').trim(),
        id: String(item.dataset.dashboardId || '').trim(),
      }))
      .filter((item) => item.kind && item.id);
  });
  const linkOrders = {};
  document.querySelectorAll('.dashboard-links-widget').forEach((widget) => {
    const widgetId = String(widget.dataset.dashboardId || '').trim();
    if (!widgetId) return;
    linkOrders[widgetId] = dashboardShortcutItems(widget)
      .map((item) => String(item.dataset.dashboardLinkId || '').trim())
      .filter(Boolean);
  });
  const widgetHeights = {};
  document.querySelectorAll('.sz_dashboard_widget[data-dashboard-kind="widget"]').forEach((widget) => {
    const widgetId = String(widget.dataset.dashboardId || '').trim();
    if (!widgetId) return;
    widgetHeights[widgetId] = parseDashboardHeight(widget.dataset.dashboardHeight, 0);
  });
  return {
    columns,
    link_orders: linkOrders,
    widget_heights: widgetHeights,
    settings: {
      columns: clampDashboardColumnCount(dashboardLayoutState.columns),
      widths: normalizeDashboardWidths(dashboardLayoutState.widths, dashboardLayoutState.columns),
    },
  };
}

async function saveDashboardLayout() {
  const saveBtn = document.getElementById('dashboardSaveLayoutBtn');
  if (saveBtn) saveBtn.disabled = true;
  try {
    const resp = await fetch('/api/dashboard/layout', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(serializeDashboardLayout()),
    });
    const data = await parseJsonResponse(resp, 'Erro ao gravar layout do dashboard');
    if (!resp.ok || data.error) throw new Error(data.error || 'Erro ao gravar layout.');
    setDashboardLayoutMode(false);
  } catch (error) {
    console.error(error);
    alert(error.message || 'Erro ao gravar layout do dashboard.');
  } finally {
    if (saveBtn) saveBtn.disabled = false;
  }
}

function openDashboardLayoutSettingsModal() {
  renderDashboardColumnWidthControls();
  const modalEl = document.getElementById('dashboardLayoutSettingsModal');
  if (!modalEl) return;
  bootstrap.Modal.getOrCreateInstance(modalEl).show();
}

function applyDashboardLayoutSettingsFromModal() {
  const count = clampDashboardColumnCount(document.getElementById('dashboardColumnCount')?.value || dashboardLayoutState.columns);
  const widths = Array.from(document.querySelectorAll('[data-dashboard-column-width]')).map((input) => parseFloat(input.value));
  setDashboardLayoutPreferences({ columns: count, widths }, { markDirty: true });
  bootstrap.Modal.getInstance(document.getElementById('dashboardLayoutSettingsModal'))?.hide();
  if (!dashboardLayoutState.editing) {
    setDashboardLayoutMode(true);
  }
}

function equalizeDashboardColumnWidths() {
  const count = clampDashboardColumnCount(document.getElementById('dashboardColumnCount')?.value || dashboardLayoutState.columns);
  dashboardLayoutState.columns = count;
  dashboardLayoutState.widths = Array.from({ length: count }, () => 100 / count);
  renderDashboardColumnWidthControls();
}

function bindDashboardColumnDragEvents() {
  dashboardColumns().forEach((col) => {
    if (col.dataset.dashboardDropBound === '1') return;
    col.dataset.dashboardDropBound = '1';
    col.addEventListener('dragover', (event) => {
      if (!dashboardLayoutState.editing) return;
      if (document.querySelector('.dashboard-link-wrap.is-shortcut-dragging')) return;
      event.preventDefault();
      const dragging = document.querySelector('.sz_dashboard_draggable.is-dragging');
      if (!dragging) return;
      const afterElement = getDashboardDragAfterElement(col, event.clientY);
      if (afterElement == null) col.appendChild(dragging);
      else col.insertBefore(dragging, afterElement);
      markDashboardLayoutDirty();
    });
    col.addEventListener('drop', (event) => {
      if (!dashboardLayoutState.editing) return;
      event.preventDefault();
      markDashboardLayoutDirty();
    });
  });
}

function startDashboardWidgetResize(handle, event) {
  if (!dashboardLayoutState.editing || !handle) return;
  const widgetEl = handle.closest('.sz_dashboard_widget[data-dashboard-kind="widget"]');
  const body = widgetEl?.querySelector('.sz_dashboard_widget_body');
  if (!widgetEl || !body) return;
  event.preventDefault();
  event.stopPropagation();

  const tipo = widgetEl.classList.contains('sz_dashboard_widget_grafico') ? 'GRAFICO' : '';
  const startY = event.clientY;
  const startHeight = Math.ceil(body.getBoundingClientRect().height || body.clientHeight || 0);
  const minHeight = tipo === 'GRAFICO' ? 180 : 96;
  const expandedHeight = Math.max(getDashboardWidgetExpandedHeight(widgetEl), startHeight, minHeight);
  const pointerId = event.pointerId;

  widgetEl.classList.add('is-dashboard-resizing');
  try {
    handle.setPointerCapture(pointerId);
  } catch (_) {}

  const onMove = (moveEvent) => {
    const delta = moveEvent.clientY - startY;
    const nextHeight = Math.max(minHeight, Math.min(expandedHeight, startHeight + delta));
    const saveHeight = nextHeight >= expandedHeight - 4 ? 0 : Math.round(nextHeight);
    applyDashboardWidgetHeight(widgetEl, body, saveHeight || expandedHeight, tipo);
    widgetEl.dataset.dashboardHeight = String(saveHeight);
    if (saveHeight === 0) {
      applyDashboardWidgetHeight(widgetEl, body, 0, tipo);
    }
    markDashboardLayoutDirty();
  };

  const onEnd = () => {
    widgetEl.classList.remove('is-dashboard-resizing');
    document.removeEventListener('pointermove', onMove);
    document.removeEventListener('pointerup', onEnd);
    document.removeEventListener('pointercancel', onEnd);
    try {
      handle.releasePointerCapture(pointerId);
    } catch (_) {}
  };

  document.addEventListener('pointermove', onMove);
  document.addEventListener('pointerup', onEnd);
  document.addEventListener('pointercancel', onEnd);
}

function bindDashboardLayoutEvents() {
  document.getElementById('dashboardContextMenu')?.addEventListener('click', (event) => {
    const action = event.target.closest?.('[data-dashboard-action]')?.dataset.dashboardAction;
    if (action === 'customize') {
      closeDashboardContextMenu();
      setDashboardLayoutMode(true);
    } else if (action === 'layout') {
      closeDashboardContextMenu();
      openDashboardLayoutSettingsModal();
    } else if (action === 'shortcut') {
      closeDashboardContextMenu();
      openDashboardShortcutModal();
    } else if (action === 'widget') {
      closeDashboardContextMenu();
      openDashboardWidgetModal();
    }
  });

  document.getElementById('dashboardColumnCount')?.addEventListener('change', (event) => {
    const nextCount = clampDashboardColumnCount(event.target.value);
    dashboardLayoutState.columns = nextCount;
    dashboardLayoutState.widths = normalizeDashboardWidths(dashboardLayoutState.widths, nextCount);
    renderDashboardColumnWidthControls();
  });
  document.getElementById('dashboardColumnWidthControls')?.addEventListener('input', (event) => {
    const input = event.target.closest?.('[data-dashboard-column-width]');
    if (!input) return;
    const index = parseInt(input.dataset.dashboardColumnWidth, 10);
    const widths = normalizeDashboardWidths(dashboardLayoutState.widths, dashboardLayoutState.columns);
    if (Number.isFinite(index) && index >= 0 && index < widths.length) {
      widths[index] = parseFloat(input.value);
      dashboardLayoutState.widths = normalizeDashboardWidths(widths, dashboardLayoutState.columns);
      document.querySelectorAll('[data-dashboard-column-width]').forEach((range, rangeIndex) => {
        const normalized = dashboardLayoutState.widths[rangeIndex] || 0;
        range.value = String(Math.round(normalized));
        const labelValue = range.closest('.sz_dashboard_column_width')?.querySelector('label strong');
        if (labelValue) labelValue.textContent = `${normalized.toFixed(1)}%`;
      });
    }
  });
  document.getElementById('dashboardEqualizeColumnsBtn')?.addEventListener('click', equalizeDashboardColumnWidths);
  document.getElementById('dashboardApplyLayoutSettingsBtn')?.addEventListener('click', applyDashboardLayoutSettingsFromModal);

  document.getElementById('dashboardShortcutSearch')?.addEventListener('input', filterDashboardShortcutList);
  document.getElementById('dashboardShortcutColors')?.addEventListener('click', (event) => {
    const btn = event.target.closest?.('[data-shortcut-color]');
    if (!btn) return;
    dashboardShortcutColor = String(btn.dataset.shortcutColor || dashboardShortcutPalette[0]);
    renderDashboardShortcutColors();
  });
  document.getElementById('dashboardShortcutUrlBtn')?.addEventListener('click', addDashboardUrlShortcut);
  document.getElementById('dashboardShortcutUrl')?.addEventListener('keydown', (event) => {
    if (event.key !== 'Enter') return;
    event.preventDefault();
    addDashboardUrlShortcut();
  });
  document.getElementById('dashboardWidgetSearch')?.addEventListener('input', filterDashboardWidgetList);
  document.getElementById('dashboardShortcutList')?.addEventListener('click', (event) => {
    const item = event.target.closest?.('.sz_dashboard_shortcut_item');
    if (!item) return;
    addDashboardScreenShortcut(item.dataset.menustamp || '');
  });
  document.getElementById('dashboardWidgetList')?.addEventListener('click', (event) => {
    const item = event.target.closest?.('.sz_dashboard_shortcut_item');
    if (!item) return;
    showDashboardWidget(item.dataset.widgetId || '');
  });

  document.querySelector('.sz_dashboard_body')?.addEventListener('contextmenu', (event) => {
    if (dashboardLayoutState.editing) return;
    if (event.target.closest?.('.sz_dashboard_draggable, a, button, input, select, textarea, .sz_dashboard_context_menu')) return;
    event.preventDefault();
    openDashboardContextMenu(event.clientX, event.clientY);
  });

  document.addEventListener('click', (event) => {
    const removeShortcutBtn = event.target.closest?.('[data-dashboard-remove-shortcut]');
    if (removeShortcutBtn) {
      event.preventDefault();
      event.stopPropagation();
      removeDashboardShortcut(removeShortcutBtn.dataset.dashboardRemoveShortcut || '');
      return;
    }
    const removeItemBtn = event.target.closest?.('[data-dashboard-remove-item]');
    if (removeItemBtn) {
      event.preventDefault();
      event.stopPropagation();
      if (!dashboardLayoutState.editing) return;
      hideDashboardItem(removeItemBtn.closest('.sz_dashboard_draggable'));
      return;
    }
    if (event.target.closest?.('#dashboardContextMenu')) return;
    closeDashboardContextMenu();
  });
  document.addEventListener('pointerdown', (event) => {
    const handle = event.target.closest?.('[data-dashboard-resize-widget]');
    if (!handle) return;
    startDashboardWidgetResize(handle, event);
  });
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') closeDashboardContextMenu();
  });
  window.addEventListener('resize', closeDashboardContextMenu);
  window.addEventListener('scroll', closeDashboardContextMenu, true);

  document.getElementById('dashboardSaveLayoutBtn')?.addEventListener('click', saveDashboardLayout);
  document.getElementById('dashboardCancelLayoutBtn')?.addEventListener('click', () => {
    setDashboardLayoutMode(false);
    loadDashboard();
  });

  bindDashboardColumnDragEvents();

  document.addEventListener('dragover', (event) => {
    if (!dashboardLayoutState.editing) return;
    const dragging = document.querySelector('.dashboard-link-wrap.is-shortcut-dragging');
    if (!dragging) return;
    const grid = event.target.closest?.('.links-grid');
    if (!grid) return;
    event.preventDefault();
    const afterElement = getDashboardShortcutAfterElement(grid, event.clientX, event.clientY);
    if (afterElement == null) grid.appendChild(dragging);
    else grid.insertBefore(dragging, afterElement);
    markDashboardLayoutDirty();
  });

  document.addEventListener('drop', (event) => {
    if (!dashboardLayoutState.editing) return;
    if (!document.querySelector('.dashboard-link-wrap.is-shortcut-dragging')) return;
    if (!event.target.closest?.('.links-grid')) return;
    event.preventDefault();
    markDashboardLayoutDirty();
  });

  document.addEventListener('dragstart', (event) => {
    if (event.target.closest?.('[data-dashboard-resize-widget]')) {
      event.preventDefault();
      return;
    }
    const shortcut = event.target.closest?.('.dashboard-link-wrap');
    if (dashboardLayoutState.editing && shortcut && !event.target.closest?.('button')) {
      shortcut.classList.add('is-shortcut-dragging');
      event.dataTransfer.effectAllowed = 'move';
      event.dataTransfer.setData('text/plain', shortcut.dataset.dashboardLinkId || '');
      event.stopPropagation();
      return;
    }
    const item = event.target.closest?.('.sz_dashboard_draggable');
    if (!dashboardLayoutState.editing || !item) return;
    item.classList.add('is-dragging');
    event.dataTransfer.effectAllowed = 'move';
    event.dataTransfer.setData('text/plain', item.dataset.dashboardId || '');
  });

  document.addEventListener('dragend', (event) => {
    document.querySelectorAll('.dashboard-link-wrap.is-shortcut-dragging').forEach((item) => {
      item.classList.remove('is-shortcut-dragging');
    });
    const item = event.target.closest?.('.sz_dashboard_draggable');
    if (!item) return;
    item.classList.remove('is-dragging');
  });
}

// Boot ---------------------------------------------------
function loadDashboard() {
  showLoading();
  fetch('/api/dashboard')
    .then(r => parseJsonResponse(r, 'Erro ao carregar configuracao do dashboard'))
    .then(data => {
      setDashboardLayoutPreferences(data.layout || { columns: 3, widths: [33.34, 33.33, 33.33] });
      for (let col = 1; col <= dashboardLayoutState.columns; col += 1) {
        const colDiv = document.getElementById('col-' + col);
        if (!colDiv) return;
        colDiv.innerHTML = '';
        const widgets = Array.isArray(data[col]) ? data[col] : [];
        widgets.forEach(item => {
          if (String(item.kind || '').toLowerCase() === 'links') {
            renderDashboardLinksItem(item, colDiv);
          } else {
            renderWidget(item, colDiv);
          }
        });
      }
      syncDashboardLayoutControls();
      hideLoading();
    })
    .catch((err) => {
      console.error('Dashboard bootstrap failed:', err);
      showDashboardError(err.message || 'Falha ao carregar dashboard.');
      hideLoading();
    });
}

document.addEventListener('DOMContentLoaded', () => {
  bindDashboardLayoutEvents();
  loadDashboard();
});
