// static/js/dashboard.js

// Utils -------------------------------------------------
function parseNumber(val) {
  if (val == null || val === '') return 0;
  const s = typeof val === 'string' ? val.replace(/\s/g, '').replace(',', '.') : val;
  const n = Number(s);
  return isNaN(n) ? 0 : n;
}
function formatNumber(n) {
  const num = Number(n);
  if (isNaN(num)) return '';
  const parts = num.toFixed(2).split('.');
  parts[0] = parts[0].replace(/\B(?=(\d{3})+(?!\d))/g,' ');
  return parts.join(',');
}
function formatTitle(str) {
  return str.replace(/_/g,' ').replace(/\b\w/g,l=>l.toUpperCase());
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
  const js = await resp.json();
  if (!resp.ok || js.error) throw new Error(js.error || 'Erro ao carregar opções');
  return Array.isArray(js.options) ? js.options : [];
}

function ensureFiltersModal(widget, fields) {
  const modalId = `widget-filters-${widget.nome}`;
  if (document.getElementById(modalId)) return modalId;
  const modal = document.createElement('div');
  modal.className = 'modal fade';
  modal.id = modalId;
  modal.tabIndex = -1;
  modal.innerHTML = `
    <div class="modal-dialog">
      <div class="modal-content">
        <div class="modal-header">
          <h5 class="modal-title"><i class="fa-solid fa-filter me-2"></i>Filtros - ${widget.titulo || widget.nome}</h5>
          <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Fechar"></button>
        </div>
        <div class="modal-body">
          <form id="${modalId}-form" class="row g-2"></form>
        </div>
        <div class="modal-footer">
          <button type="button" class="btn btn-cancel" data-bs-dismiss="modal">Cancelar</button>
          <button type="button" class="btn btn-primary" id="${modalId}-apply">Aplicar</button>
        </div>
      </div>
    </div>`;
  document.body.appendChild(modal);

  const form = modal.querySelector('form');
  fields.forEach(f => {
    const wrap = document.createElement('div');
    wrap.className = 'col-12';
    const label = document.createElement('label');
    label.className = 'form-label';
    label.textContent = f.label || f.key;
    label.htmlFor = `${modalId}-${f.key}`;
    wrap.appendChild(label);

    let input;
    if (f.input_type === 'select') {
      input = document.createElement('select');
      input.className = 'form-select';
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
      input.className = 'form-control';
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
  const js = await resp.json();
  if (!resp.ok || js.error) throw new Error(js.error || 'Falha ao executar widget');
  return js;
}

function renderDataIntoWidget(state, data) {
  const { widget, body } = state;
  if (widget.tipo === 'ANALISE') renderAnalise(body, data);
  else if (widget.tipo === 'GRAFICO') renderGrafico(body, widget, data);
}

// Render -------------------------------------------------
function renderAnalise(body, data) {
  if (data.error) {
    body.innerHTML = `<span class="error-msg">${data.error}</span>`;
    return;
  }

  const numericCols = data.columns.filter(c =>
    data.rows.every(row => {
      const v = row[c];
      if (typeof v === 'number') return true;
      if (typeof v === 'string') return /^[\d\s,\.]+$/.test(v);
      return false;
    })
  );

  const decimalCols = numericCols.filter(c =>
    data.rows.some(row => parseNumber(row[c]) % 1 !== 0)
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

  let html = '<table>';
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

  if (decimalCols.length > 0) {
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

  html += '</table>';
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

  const labels = stackCol
    ? Array.from(new Map(data.rows.map(r => [r[labelCol], r[labelCol]])).values())
    : data.rows.map(r => r[labelCol]);

  let datasets = [];

  if (stackCol) {
    const stacks = [...new Set(data.rows.map(r => r[stackCol]))];
    const palette = cfg.stack_colors || {};
    datasets = stacks.map((stack, idx) => {
      const baseHue = Math.round(idx * 360 / Math.max(stacks.length,1));
      const color = palette[stack] || `hsla(${baseHue}, 65%, 68%, 0.6)`;
      const vals = labels.map(label =>
        data.rows
          .filter(r => r[labelCol] === label && r[stackCol] === stack)
          .reduce((sum, row) => sum + parseNumber(row[dataCol]), 0)
      );
      return {
        label: stack,
        data: vals,
        backgroundColor: color,
        borderColor: color,
        borderWidth: 1,
        borderRadius: 4
      };
    });
  } else {
    const values = data.rows.map(r => parseNumber(r[dataCol]));
    const dataset = { label: widget.titulo || widget.nome, data: values };
    if (chartType === 'bar' || chartType === 'line') {
      Object.assign(dataset, {
        backgroundColor: 'rgba(56, 189, 248, 0.35)',
        borderColor: 'rgba(56, 189, 248, 0.8)',
        borderWidth: 1,
        borderRadius: 5,
        borderSkipped: false
      });
    } else {
      dataset.backgroundColor = labels.map((_,i) => `hsl(${Math.round(i*360/labels.length)},70%,60%)`);
      dataset.borderWidth = 1;
    }
    datasets = [dataset];
  }

  body.innerHTML = '';
  const canvas = document.createElement('canvas');
  body.appendChild(canvas);
  new Chart(canvas.getContext('2d'), {
    type: chartType,
    data: { labels, datasets },
    options: {
      responsive: true,
      plugins: { legend: { display: false } },
      scales: (chartType === 'bar' || chartType === 'line') ? {
        x: { stacked: !!stackCol, grid: { display: false } },
        y: { stacked: !!stackCol, beginAtZero: true, grid: { display: true, color: '#e0e0e0' } }
      } : {}
    }
  });
}

// Render widget entry point --------------------------------------------
async function renderWidget(widget, colDiv) {
  const filtersDef = parseFiltersDef(widget);
  const hasFilters = filtersDef.length > 0;

  const wDiv = document.createElement('div');
  wDiv.className = 'widget widget-' + widget.tipo.toLowerCase();
  const filterBtn = hasFilters ? `<button class="btn btn-outline-secondary btn-sm widget-filter-btn" data-widget="${widget.nome}" title="Filtros"><i class="fa fa-filter"></i></button>` : '';
  wDiv.innerHTML = `
    <div class="widget-header">
      <h3>${widget.titulo || formatTitle(widget.nome)}</h3>
      <div class="d-flex align-items-center gap-2">
        ${filterBtn}
        <button class="expand-btn" title="Expandir">⇵</button>
      </div>
    </div>
    <div class="widget-body"></div>
  `;
  colDiv.appendChild(wDiv);

  const body = wDiv.querySelector('.widget-body');
  const expandBtn = wDiv.querySelector('.expand-btn');
  expandBtn.style.display = 'none';

  let maxH = widget.maxheight;
  try {
    const cfg = JSON.parse(widget.config || '{}');
    if (!maxH && cfg.maxheight) maxH = cfg.maxheight;
  } catch {}
  if (maxH) {
    body.style.maxHeight = maxH + 'px';
    body.style.overflowY = 'auto';
  }

  const toggleExpandBtn = () => {
    if (maxH && body.scrollHeight > body.clientHeight) expandBtn.style.display = '';
    else expandBtn.style.display = 'none';
  };
  expandBtn.addEventListener('click', () => wDiv.classList.toggle('expanded'));

  if (hasFilters) {
    widgetState.set(widget.nome, { widget, body, filtersDef, currentFilters: buildDefaultFilters(filtersDef) });
    const btn = wDiv.querySelector('.widget-filter-btn');
    if (btn) btn.addEventListener('click', () => openFilters(widget.nome));
  }

  try {
    if (widget.tipo === 'ANALISE' || widget.tipo === 'GRAFICO') {
      const state = widgetState.get(widget.nome) || { widget, body, filtersDef, currentFilters: {} };
      const filters = hasFilters ? (state.currentFilters || buildDefaultFilters(filtersDef)) : {};
      const data = await runWidget(widget.nome, filters);
      widgetState.set(widget.nome, { widget, body, filtersDef, currentFilters: filters });
      renderDataIntoWidget(widgetState.get(widget.nome), data);
    } else if (widget.tipo === 'HTML') {
      body.innerHTML = widget.config || '<em>(sem conteúdo)</em>';
    }
  } catch (err) {
    body.innerHTML = `<span class="error-msg">Erro: ${err.message}</span>`;
  } finally {
    toggleExpandBtn();
  }
}

// Boot ---------------------------------------------------
document.addEventListener('DOMContentLoaded', () => {
  showLoading();
  fetch('/api/dashboard')
    .then(r => r.json())
    .then(data => {
      const widgetPromises = [];
      [1,2,3].forEach(col => {
        const colDiv = document.getElementById('col-' + col);
        colDiv.innerHTML = '';
        data[col].forEach(widget => {
          const prom = renderWidget(widget, colDiv);
          if (prom && typeof prom.then === 'function') widgetPromises.push(prom);
        });
      });
      return Promise.all(widgetPromises);
    })
    .finally(hideLoading);
});
