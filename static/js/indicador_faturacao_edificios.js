(function () {
  const els = {
    ano: document.getElementById('fatEdificioAno'),
    refresh: document.getElementById('fatEdificioRefresh'),
    head: document.getElementById('fatEdificioHead'),
    body: document.getElementById('fatEdificioBody'),
    foot: document.getElementById('fatEdificioFoot'),
    total: document.getElementById('fatEdificioKpiTotal'),
  };

  const formatter = new Intl.NumberFormat('pt-PT', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });

  function esc(value) {
    return String(value ?? '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function money(value) {
    const num = Number(value || 0);
    if (!Number.isFinite(num)) return '0,00';
    return formatter.format(num).replace(/\u00a0/g, ' ');
  }

  function setLoading(message) {
    if (els.refresh) {
      els.refresh.disabled = true;
      els.refresh.classList.add('is-loading');
    }
    if (els.body) {
      els.body.innerHTML = `
        <tr class="sz_table_row">
          <td class="sz_table_cell sz_text_muted text-center" colspan="14">${esc(message || 'A carregar...')}</td>
        </tr>
      `;
    }
    if (els.foot) els.foot.innerHTML = '';
  }

  function clearLoading() {
    if (els.refresh) {
      els.refresh.disabled = false;
      els.refresh.classList.remove('is-loading');
    }
  }

  function renderHead(data) {
    const monthHeads = (data.months || [])
      .map((month) => `<th class="sz_table_cell sz_faturacao_edificios_col-money text-end">${esc(month.short)}</th>`)
      .join('');
    els.head.innerHTML = `
      <tr>
        <th class="sz_table_cell sz_faturacao_edificios_col-name">Edifício</th>
        ${monthHeads}
        <th class="sz_table_cell sz_faturacao_edificios_col-total text-end">Total</th>
      </tr>
    `;
  }

  function renderBody(data) {
    const rows = Array.isArray(data.rows) ? data.rows : [];
    if (!rows.length) {
      els.body.innerHTML = `
        <tr class="sz_table_row">
          <td class="sz_table_cell sz_text_muted text-center" colspan="14">Sem dados.</td>
        </tr>
      `;
      return;
    }

    els.body.innerHTML = rows.map((row) => {
      const months = (row.months || [])
        .map((value) => `<td class="sz_table_cell text-end">${money(value)}</td>`)
        .join('');
      return `
        <tr class="sz_table_row">
          <td class="sz_table_cell sz_faturacao_edificios_col-name"><strong>${esc(row.edificio)}</strong></td>
          ${months}
          <td class="sz_table_cell text-end"><strong>${money(row.total)}</strong></td>
        </tr>
      `;
    }).join('');
  }

  function renderFoot(data) {
    const totals = data.totals || {};
    const monthTotals = (totals.months || [])
      .map((value) => `<td class="sz_table_cell text-end">${money(value)}</td>`)
      .join('');
    els.foot.innerHTML = `
      <tr class="sz_table_row">
        <th class="sz_table_cell sz_faturacao_edificios_col-name">Total</th>
        ${monthTotals}
        <td class="sz_table_cell text-end">${money(totals.total)}</td>
      </tr>
    `;
    if (els.total) els.total.textContent = money(totals.total);
  }

  function syncUrl(ano) {
    const url = new URL(window.location.href);
    url.searchParams.set('ano', ano);
    window.history.replaceState({}, '', url.toString());
  }

  async function loadData(options) {
    const ano = els.ano?.value || new Date().getFullYear();
    setLoading('A calcular faturação...');
    if (options && options.updateUrl) syncUrl(ano);
    try {
      const qs = new URLSearchParams({ ano });
      const response = await fetch(`/api/indicadores/faturacao-edificios?${qs.toString()}`, {
        headers: { Accept: 'application/json' },
      });
      const data = await response.json();
      if (!response.ok || data.error) throw new Error(data.error || 'Erro ao carregar dados.');
      renderHead(data);
      renderBody(data);
      renderFoot(data);
    } catch (error) {
      if (els.total) els.total.textContent = '--';
      if (els.body) {
        els.body.innerHTML = `
          <tr class="sz_table_row">
            <td class="sz_table_cell text-center text-danger" colspan="14">${esc(error.message || 'Erro ao carregar dados.')}</td>
          </tr>
        `;
      }
    } finally {
      clearLoading();
    }
  }

  document.addEventListener('DOMContentLoaded', () => {
    els.ano?.addEventListener('change', () => loadData({ updateUrl: true }));
    els.refresh?.addEventListener('click', () => loadData({ updateUrl: true }));
    loadData({ updateUrl: false });
  });
})();
