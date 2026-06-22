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
