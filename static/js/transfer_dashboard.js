(function () {
  'use strict';

  const root = document.getElementById('transferDashboard');
  if (!root) return;

  const form = document.getElementById('transferFilters');
  const periodInput = document.getElementById('transferPeriod');
  const customDates = Array.from(document.querySelectorAll('[data-custom-date]'));
  const rowsRoot = document.getElementById('transferRows');
  const empty = document.getElementById('transferEmpty');
  const statusMessage = document.getElementById('transferStatusMessage');
  const summary = document.getElementById('transferListSummary');
  const exportButton = document.getElementById('transferExport');
  const optionInputs = {
    accommodations: document.getElementById('transferAccommodation'),
    origins: document.getElementById('transferOrigin'),
    statuses: document.getElementById('transferStatus'),
  };
  let activeRequest = null;

  function showCustomDates() {
    const visible = periodInput.value === 'custom';
    customDates.forEach((field) => { field.hidden = !visible; });
  }

  function queryString() {
    const params = new URLSearchParams(new FormData(form));
    if (params.get('period') !== 'custom') {
      params.delete('start');
      params.delete('end');
    }
    for (const [key, value] of Array.from(params.entries())) {
      if (!String(value || '').trim()) params.delete(key);
    }
    return params.toString();
  }

  function setText(element, value) {
    element.textContent = value == null || value === '' ? '—' : String(value);
  }

  function option(select, value, label) {
    const item = document.createElement('option');
    item.value = value;
    item.textContent = label;
    select.appendChild(item);
  }

  function updateOptions(options) {
    const configs = [
      ['accommodations', (item) => ({ value: item, label: item })],
      ['origins', (item) => item],
      ['statuses', (item) => item],
    ];
    configs.forEach(([key, mapper]) => {
      const select = optionInputs[key];
      const selected = select.value;
      while (select.options.length > 1) select.remove(1);
      (options[key] || []).forEach((raw) => {
        const item = mapper(raw);
        option(select, item.value, item.label);
      });
      select.value = selected;
    });
  }

  function formatDateTime(day, hour) {
    if (!day) return '—';
    const parts = String(day).split('-');
    const label = parts.length === 3 ? `${parts[2]}/${parts[1]}/${parts[0]}` : day;
    return `${label}${hour ? ` · ${hour}` : ''}`;
  }

  function formatTimestamp(value) {
    if (!value) return '—';
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return String(value);
    return new Intl.DateTimeFormat('pt-PT', {
      day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit',
    }).format(date);
  }

  function formatMoney(value) {
    return new Intl.NumberFormat('pt-PT', { style: 'currency', currency: 'EUR' }).format(Number(value || 0));
  }

  function badge(text, className, title) {
    const item = document.createElement('span');
    item.className = `transfer-badge ${className || ''}`.trim();
    item.textContent = text;
    if (title) item.title = title;
    return item;
  }

  function cell(label, className) {
    const item = document.createElement('td');
    item.dataset.label = label;
    if (className) item.className = className;
    return item;
  }

  function renderRow(item) {
    const row = document.createElement('tr');
    row.className = [
      item.status === 'PENDENTE' ? 'is-pending' : '',
      item.incomplete ? 'is-incomplete' : '',
    ].filter(Boolean).join(' ');
    row.tabIndex = 0;
    row.dataset.url = item.reservation_url || '';

    let current = cell('Reserva', 'transfer-reservation-cell');
    const link = document.createElement('a');
    link.href = item.reservation_url;
    link.textContent = item.reservation || 'Sem código';
    current.appendChild(link);
    if (item.multiple_for_reservation) {
      current.appendChild(badge(`${item.reservation_transfer_count} pedidos`, 'is-multiple', 'Existem vários pedidos de transfer para esta reserva.'));
    }
    row.appendChild(current);

    current = cell('Alojamento'); setText(current, item.accommodation); row.appendChild(current);
    current = cell('Percurso', 'transfer-route-cell'); setText(current, item.origin_label); row.appendChild(current);
    current = cell('Hóspede'); setText(current, item.guest_name); row.appendChild(current);
    current = cell('Pessoas', 'is-number'); setText(current, item.people || 0); row.appendChild(current);
    current = cell('Chegada'); setText(current, formatDateTime(item.arrival_date, item.arrival_time)); row.appendChild(current);
    current = cell('Voo'); setText(current, item.flight); row.appendChild(current);
    current = cell('Partida'); setText(current, formatDateTime(item.departure_date, item.departure_time)); row.appendChild(current);
    current = cell('Valor', 'is-number'); setText(current, formatMoney(item.value)); row.appendChild(current);

    current = cell('Estado', 'transfer-status-cell');
    const stateClass = `is-${String(item.status || 'unknown').toLowerCase().replace('_', '-')}`;
    current.appendChild(badge(item.status_label, stateClass));
    if (item.incomplete) current.appendChild(badge('Incompleto', 'is-warning', `Falta: ${(item.incomplete_fields || []).join(', ')}`));
    row.appendChild(current);

    current = cell('Criado / alterado', 'transfer-dates-cell');
    const created = document.createElement('span'); created.textContent = `Criado: ${formatTimestamp(item.created_at)}`;
    const updated = document.createElement('small'); updated.textContent = `Alterado: ${formatTimestamp(item.updated_at)}`;
    current.append(created, updated); row.appendChild(current);

    const open = () => { if (row.dataset.url) window.location.assign(row.dataset.url); };
    row.addEventListener('click', (event) => { if (!event.target.closest('a, button')) open(); });
    row.addEventListener('keydown', (event) => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); open(); } });
    return row;
  }

  function render(data) {
    updateOptions(data.options || {});
    Object.entries(data.kpis || {}).forEach(([key, value]) => {
      const target = root.querySelector(`[data-kpi="${key}"]`);
      if (target) setText(target, value);
    });
    rowsRoot.replaceChildren();
    const rows = data.rows || [];
    rows.forEach((item) => rowsRoot.appendChild(renderRow(item)));
    rowsRoot.closest('table').hidden = rows.length === 0;
    empty.hidden = rows.length !== 0;
    const period = data.period || {};
    summary.textContent = `${rows.length} ${rows.length === 1 ? 'pedido' : 'pedidos'} · ${period.label || 'Período selecionado'}`;
  }

  async function load() {
    if (activeRequest) activeRequest.abort();
    activeRequest = new AbortController();
    statusMessage.hidden = false;
    statusMessage.classList.remove('is-error');
    statusMessage.textContent = 'A carregar pedidos…';
    try {
      const query = queryString();
      const response = await fetch(`${root.dataset.apiUrl}${query ? `?${query}` : ''}`, {
        signal: activeRequest.signal,
        headers: { Accept: 'application/json' },
      });
      const payload = await response.json();
      if (!response.ok || !payload.ok) throw new Error(payload.error || 'Não foi possível carregar os pedidos.');
      render(payload.data);
      statusMessage.hidden = true;
    } catch (error) {
      if (error.name === 'AbortError') return;
      statusMessage.hidden = false;
      statusMessage.classList.add('is-error');
      statusMessage.textContent = error.message || 'Não foi possível carregar os pedidos.';
    }
  }

  form.addEventListener('submit', (event) => { event.preventDefault(); load(); });
  periodInput.addEventListener('change', showCustomDates);
  exportButton.addEventListener('click', () => {
    const query = queryString();
    window.location.assign(`${root.dataset.exportUrl}${query ? `?${query}` : ''}`);
  });
  showCustomDates();
  load();
}());

