(function () {
  const root = document.getElementById('opcPhcInfo');
  if (!root) return;

  const infoUrl = root.dataset.infoUrl || '';
  const numberFmt = new Intl.NumberFormat('pt-PT', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });

  function asNumber(value) {
    const number = Number(value || 0);
    return Number.isFinite(number) ? number : 0;
  }

  function text(value) {
    return String(value || '').trim();
  }

  function formatNumber(value) {
    return numberFmt.format(asNumber(value));
  }

  function formatPercent(value) {
    return `${numberFmt.format(asNumber(value))}%`;
  }

  function cell(value, className) {
    const td = document.createElement('td');
    if (className) td.className = className;
    td.textContent = value;
    return td;
  }

  function emptyRow(colspan, message) {
    const tr = document.createElement('tr');
    tr.className = 'opc-phc-empty-row';
    const td = cell(message, 'sz_text_muted');
    td.colSpan = colspan;
    tr.appendChild(td);
    return tr;
  }

  function renderRows(tableId, rows, columns, emptyMessage) {
    const tbody = document.querySelector(`#${tableId} tbody`);
    if (!tbody) return;
    tbody.replaceChildren();
    if (!rows.length) {
      tbody.appendChild(emptyRow(columns.length, emptyMessage));
      return;
    }

    rows.forEach((row) => {
      const tr = document.createElement('tr');
      columns.forEach((column) => {
        let value = row[column.key];
        let className = column.className || '';
        if (column.type === 'number') value = formatNumber(value);
        if (column.type === 'percent') value = formatPercent(value);
        if (column.type === 'check') {
          value = row[column.key] ? '✓' : '';
          className = `${className} opc-phc-check_value`.trim();
        }
        tr.appendChild(cell(value, className));
      });
      tbody.appendChild(tr);
    });
  }

  function totals(rows) {
    return rows.reduce((acc, row) => {
      [
        'producao',
        'ajustes',
        'multas',
        'ret_garantia',
        'ret_fim_trabalho',
        'prorata',
        'outras_retencoes',
        'iva',
        'total_iva',
        'adiantamento',
        'desc_financeiro',
      ].forEach((key) => {
        acc[key] = asNumber(acc[key]) + asNumber(row[key]);
      });
      return acc;
    }, {});
  }

  function renderTotals(payload) {
    const groups = {
      orcamentos: totals(payload.orcamentos || []),
      autos: totals(payload.autos || []),
    };
    root.querySelectorAll('[data-total]').forEach((el) => {
      const [group, key] = String(el.dataset.total || '').split('.');
      el.textContent = formatNumber(groups[group] ? groups[group][key] : 0);
    });
  }

  function render(payload) {
    const orcamentos = Array.isArray(payload.orcamentos) ? payload.orcamentos : [];
    const autos = Array.isArray(payload.autos) ? payload.autos : [];

    renderRows('opcPhcDevisTable', orcamentos, [
      { key: 'descricao' },
      { key: 'producao', type: 'number', className: 'opc-phc-num' },
      { key: 'ajustes', type: 'number', className: 'opc-phc-num' },
      { key: 'multas', type: 'number', className: 'opc-phc-num' },
      { key: 'ret_garantia', type: 'number', className: 'opc-phc-num' },
      { key: 'ret_fim_trabalho', type: 'number', className: 'opc-phc-num' },
      { key: 'prorata', type: 'number', className: 'opc-phc-num' },
      { key: 'outras_retencoes', type: 'number', className: 'opc-phc-num' },
      { key: 'iva_percentagem', type: 'percent', className: 'opc-phc-num' },
      { key: 'iva', type: 'number', className: 'opc-phc-num' },
      { key: 'total_iva', type: 'number', className: 'opc-phc-num' },
    ], 'Sem registos.');

    renderRows('opcPhcSituationsTable', autos, [
      { key: 'descricao' },
      { key: 'producao', type: 'number', className: 'opc-phc-num' },
      { key: 'ajustes', type: 'number', className: 'opc-phc-num' },
      { key: 'ret_garantia', type: 'number', className: 'opc-phc-num' },
      { key: 'ret_fim_trabalho', type: 'number', className: 'opc-phc-num' },
      { key: 'prorata', type: 'number', className: 'opc-phc-num' },
      { key: 'outras_retencoes', type: 'number', className: 'opc-phc-num' },
      { key: 'multas', type: 'number', className: 'opc-phc-num' },
      { key: 'iva', type: 'number', className: 'opc-phc-num' },
      { key: 'iva_percentagem', type: 'percent', className: 'opc-phc-num' },
      { key: 'total_iva', type: 'number', className: 'opc-phc-num' },
      { key: 'desc_financeiro', type: 'number', className: 'opc-phc-num' },
      { key: 'adiantamento', type: 'number', className: 'opc-phc-num' },
      { key: 'faturado', type: 'check', className: 'opc-phc-check' },
      { key: 'ft_descricao' },
    ], 'Sem registos.');

    renderTotals({ orcamentos, autos });
  }

  function renderError(message) {
    renderRows('opcPhcDevisTable', [], new Array(11).fill(null), message);
    renderRows('opcPhcSituationsTable', [], new Array(15).fill(null), message);
  }

  if (!infoUrl) {
    renderError('Grava a obra para consultar a informação PHC.');
    return;
  }

  fetch(infoUrl, { headers: { Accept: 'application/json' } })
    .then((response) => response.json().then((body) => {
      if (!response.ok) throw new Error(text(body.error) || 'Não foi possível consultar a informação PHC.');
      return body;
    }))
    .then(render)
    .catch((error) => {
      renderError(error.message || 'Não foi possível consultar a informação PHC.');
      renderTotals({ orcamentos: [], autos: [] });
    });
})();

(function () {
  const trigger = document.getElementById('btnOpcMaintenance');
  const modalElement = document.getElementById('opcMaintenanceModal');
  const list = document.getElementById('opcMaintenanceList');
  if (!trigger || !modalElement || !list) return;

  const recordStamp = String(window.RECORD_STAMP || '').trim();
  const endpoint = `/generic/api/opc/${encodeURIComponent(recordStamp)}/maintenance`;
  const status = document.getElementById('opcMaintenanceStatus');
  const addButton = document.getElementById('btnOpcMaintenanceAdd');
  const saveButton = document.getElementById('btnOpcMaintenanceSave');
  const modal = window.bootstrap ? window.bootstrap.Modal.getOrCreateInstance(modalElement) : null;

  function setStatus(message, error) {
    if (!status) return;
    status.hidden = !message;
    status.textContent = message || '';
    status.classList.toggle('is-error', Boolean(error));
  }

  function makeField(label, name, value, type, className) {
    const wrapper = document.createElement('label');
    wrapper.className = `sz_opc_maintenance_field ${className || ''}`.trim();
    const title = document.createElement('span');
    title.className = 'sz_label';
    title.textContent = label;
    const input = document.createElement(type === 'textarea' ? 'textarea' : 'input');
    input.className = type === 'textarea' ? 'sz_textarea' : 'sz_input';
    input.name = name;
    if (type === 'textarea') {
      input.rows = 1;
      input.maxLength = 200;
    } else {
      input.type = type;
    }
    input.value = value || '';
    wrapper.append(title, input);
    return wrapper;
  }

  function renderEmpty() {
    if (list.children.length) return;
    const empty = document.createElement('div');
    empty.className = 'sz_opc_maintenance_empty';
    empty.textContent = 'Sem períodos de manutenção definidos.';
    list.appendChild(empty);
  }

  function addPeriod(period) {
    list.querySelector('.sz_opc_maintenance_empty')?.remove();
    const row = document.createElement('div');
    row.className = 'sz_opc_maintenance_row';
    row.append(
      makeField('Início', 'data_inicio', period?.data_inicio, 'date'),
      makeField('Fim', 'data_fim', period?.data_fim, 'date'),
      makeField('Observações', 'observacoes', period?.observacoes, 'textarea', 'sz_opc_maintenance_field--observation'),
    );
    const remove = document.createElement('button');
    remove.type = 'button';
    remove.className = 'sz_button sz_button_danger sz_opc_maintenance_remove';
    remove.title = 'Remover período';
    remove.innerHTML = '<i class="fa-solid fa-trash"></i>';
    remove.addEventListener('click', () => {
      row.remove();
      renderEmpty();
    });
    row.appendChild(remove);
    list.appendChild(row);
  }

  function currentPeriods() {
    return Array.from(list.querySelectorAll('.sz_opc_maintenance_row')).map((row) => ({
      data_inicio: row.querySelector('[name="data_inicio"]')?.value || '',
      data_fim: row.querySelector('[name="data_fim"]')?.value || '',
      observacoes: row.querySelector('[name="observacoes"]')?.value || '',
    }));
  }

  async function load() {
    list.replaceChildren();
    setStatus('A carregar períodos de manutenção…');
    try {
      const response = await fetch(endpoint, { headers: { Accept: 'application/json' } });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.error || 'Não foi possível carregar os períodos.');
      (payload.periodos || []).forEach(addPeriod);
      renderEmpty();
      setStatus('');
    } catch (error) {
      setStatus(error.message || 'Não foi possível carregar os períodos.', true);
    }
  }

  trigger.addEventListener('click', async () => {
    if (!modal) return;
    modal.show();
    await load();
  });
  addButton?.addEventListener('click', () => addPeriod({}));
  saveButton?.addEventListener('click', async () => {
    const periods = currentPeriods();
    saveButton.disabled = true;
    setStatus('A gravar períodos de manutenção…');
    try {
      const response = await fetch(endpoint, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
        body: JSON.stringify({ periodos: periods }),
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.error || 'Não foi possível gravar os períodos.');
      setStatus('Períodos de manutenção gravados.');
      window.setTimeout(() => modal?.hide(), 350);
    } catch (error) {
      setStatus(error.message || 'Não foi possível gravar os períodos.', true);
    } finally {
      saveButton.disabled = false;
    }
  });
})();
