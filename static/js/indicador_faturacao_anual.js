(function () {
  function escapeHtml(value) {
    return String(value ?? '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function formatInt(value) {
    const num = Number(value || 0);
    if (!Number.isFinite(num)) return '0';
    return Math.round(num).toLocaleString('pt-PT').replace(/\u00a0/g, ' ');
  }

  function formatMoney2(value) {
    const num = Number(value || 0);
    if (!Number.isFinite(num)) return '0,00';
    return num.toLocaleString('pt-PT', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    }).replace(/\u00a0/g, ' ');
  }

  function setResumoLoading() {
    const body = document.getElementById('fatResumoBody');
    if (body) {
      body.innerHTML = '<tr class="sz_table_row"><td class="sz_table_cell sz_text_muted text-center" colspan="5" data-label="Resumo">A carregar...</td></tr>';
    }
    ['fatResumoTotalExploracao', 'fatResumoTotalGestao', 'fatResumoTotalValor', 'fatResumoTotalEstimativa'].forEach((id) => {
      const el = document.getElementById(id);
      if (el) el.textContent = '0';
    });
  }

  function bindDetailButtons(root) {
    (root || document).querySelectorAll('[data-fat-detail]').forEach((btn) => {
      btn.addEventListener('click', () => openDetail(btn));
    });
  }

  function renderResumo(data) {
    const body = document.getElementById('fatResumoBody');
    if (!body) return;
    const ano = data.ano || document.getElementById('fatAno')?.value || '';
    const rows = Array.isArray(data.rows) ? data.rows : [];
    if (!rows.length) {
      body.innerHTML = '<tr class="sz_table_row"><td class="sz_table_cell sz_text_muted text-center" colspan="5" data-label="Resumo">Sem dados.</td></tr>';
    } else {
      body.innerHTML = rows.map((row) => `
        <tr class="sz_table_row">
          <td class="sz_table_cell sz_indicator_primary_col" data-label="Mês">${escapeHtml(row.MES)}</td>
          <td class="sz_table_cell text-end" data-label="Exploração">
            <button type="button" class="sz_indicator_value_btn" data-fat-detail data-ano="${escapeHtml(ano)}" data-mes="${escapeHtml(row.NMES)}" data-tipo="EXPLORACAO">${formatInt(row.EXPLORACAO)}</button>
          </td>
          <td class="sz_table_cell text-end" data-label="Gestão">
            <button type="button" class="sz_indicator_value_btn" data-fat-detail data-ano="${escapeHtml(ano)}" data-mes="${escapeHtml(row.NMES)}" data-tipo="GESTAO">${formatInt(row.GESTAO)}</button>
          </td>
          <td class="sz_table_cell text-end" data-label="Total">${formatInt(row.TOTAL)}</td>
          <td class="sz_table_cell text-end" data-label="Estimativa">${formatInt(row.ESTIMATIVA)}</td>
        </tr>
      `).join('');
      bindDetailButtons(body);
    }

    const totals = data.totals || {};
    const totalExploracao = document.getElementById('fatResumoTotalExploracao');
    const totalGestao = document.getElementById('fatResumoTotalGestao');
    const totalValor = document.getElementById('fatResumoTotalValor');
    const totalEstimativa = document.getElementById('fatResumoTotalEstimativa');
    if (totalExploracao) totalExploracao.textContent = formatInt(totals.EXPLORACAO);
    if (totalGestao) totalGestao.textContent = formatInt(totals.GESTAO);
    if (totalValor) totalValor.textContent = formatInt(totals.TOTAL);
    if (totalEstimativa) totalEstimativa.textContent = formatInt(totals.ESTIMATIVA);
  }

  async function loadResumo(ano, options) {
    setResumoLoading();
    try {
      const qs = new URLSearchParams({ ano: ano || '' });
      const response = await fetch(`/api/indicadores/faturacao-anual/resumo?${qs.toString()}`);
      const data = await response.json();
      if (!response.ok || data.error) throw new Error(data.error || 'Erro ao carregar resumo.');
      renderResumo(data);
      if (options && options.updateUrl) {
        const url = new URL(window.location.href);
        url.searchParams.set('ano', data.ano || ano);
        window.history.replaceState({}, '', url.toString());
      }
    } catch (error) {
      const body = document.getElementById('fatResumoBody');
      if (body) {
        body.innerHTML = `<tr class="sz_table_row"><td class="sz_table_cell text-center text-danger" colspan="5" data-label="Resumo">${escapeHtml(error.message || 'Erro ao carregar resumo.')}</td></tr>`;
      }
    }
  }

  function setLoading() {
    const body = document.getElementById('fatDetailBody');
    if (body) {
      body.innerHTML = '<tr class="sz_table_row"><td class="sz_table_cell sz_text_muted text-center" colspan="8" data-label="Detalhe">A carregar...</td></tr>';
    }
    [
      'fatDetailTotalNoites',
      'fatDetailTotalDisponiveis',
      'fatDetailTotalAdr',
      'fatDetailTotalValor',
      'fatDetailTotalEstimativaPreco',
      'fatDetailTotalEstimativaVazias',
      'fatDetailTotalGeral'
    ].forEach((id) => {
      const el = document.getElementById(id);
      if (el) el.textContent = id === 'fatDetailTotalAdr' || id === 'fatDetailTotalEstimativaPreco' ? '0,00' : '0';
    });
    document.querySelectorAll('.fat-detail-future-col').forEach((el) => {
      el.style.display = 'none';
    });
  }

  function renderDetail(data) {
    const title = document.getElementById('fatDetailTitle');
    const subtitle = document.getElementById('fatDetailSubtitle');
    const body = document.getElementById('fatDetailBody');
    const tipoLabel = data.tipo === 'GESTAO' ? 'Gestão' : 'Exploração';

    if (title) title.textContent = `${data.mes_nome || ''} · ${tipoLabel}`;
    if (subtitle) subtitle.textContent = `${data.ano || ''}`;

    const rows = Array.isArray(data.rows) ? data.rows : [];
    const showDisponiveis = Boolean(data.show_disponiveis);
    document.querySelectorAll('.fat-detail-future-col').forEach((el) => {
      el.style.display = showDisponiveis ? '' : 'none';
    });
    if (body) {
      if (!rows.length) {
        body.innerHTML = `<tr class="sz_table_row"><td class="sz_table_cell sz_text_muted text-center" colspan="${showDisponiveis ? 8 : 4}" data-label="Detalhe">Sem dados.</td></tr>`;
      } else {
        body.innerHTML = rows.map((row) => `
          <tr class="sz_table_row">
            <td class="sz_table_cell sz_indicator_primary_col" data-label="Alojamento">${escapeHtml(row.ALOJAMENTO)}</td>
            <td class="sz_table_cell text-end" data-label="Noites">${formatInt(row.NOITES)}</td>
            <td class="sz_table_cell text-end" data-label="Média/noite">${formatMoney2(row.ADR)}</td>
            <td class="sz_table_cell text-end" data-label="Total">${formatInt(row.TOTAL)}</td>
            ${showDisponiveis ? `<td class="sz_table_cell text-end" data-label="Disp.">${formatInt(row.DISPONIVEIS)}</td>` : ''}
            ${showDisponiveis ? `<td class="sz_table_cell text-end" data-label="Preço est.">${formatMoney2(row.ESTIMATIVA_PRECO)}</td>` : ''}
            ${showDisponiveis ? `<td class="sz_table_cell text-end" data-label="Est. vazias">${formatInt(row.ESTIMATIVA_VAZIAS)}</td>` : ''}
            ${showDisponiveis ? `<td class="sz_table_cell text-end" data-label="Total geral">${formatInt(row.TOTAL_GERAL)}</td>` : ''}
          </tr>
        `).join('');
      }
    }

    const totals = data.totals || {};
    const totalNoites = document.getElementById('fatDetailTotalNoites');
    const totalDisponiveis = document.getElementById('fatDetailTotalDisponiveis');
    const totalAdr = document.getElementById('fatDetailTotalAdr');
    const totalValor = document.getElementById('fatDetailTotalValor');
    const totalEstimativaPreco = document.getElementById('fatDetailTotalEstimativaPreco');
    const totalEstimativaVazias = document.getElementById('fatDetailTotalEstimativaVazias');
    const totalGeral = document.getElementById('fatDetailTotalGeral');
    if (totalNoites) totalNoites.textContent = formatInt(totals.NOITES);
    if (totalDisponiveis) totalDisponiveis.textContent = formatInt(totals.DISPONIVEIS);
    if (totalAdr) totalAdr.textContent = formatMoney2(totals.ADR);
    if (totalValor) totalValor.textContent = formatInt(totals.TOTAL);
    if (totalEstimativaPreco) totalEstimativaPreco.textContent = formatMoney2(totals.ESTIMATIVA_PRECO);
    if (totalEstimativaVazias) totalEstimativaVazias.textContent = formatInt(totals.ESTIMATIVA_VAZIAS);
    if (totalGeral) totalGeral.textContent = formatInt(totals.TOTAL_GERAL);
  }

  async function openDetail(btn) {
    const modalEl = document.getElementById('fatDetailModal');
    if (!modalEl) return;

    setLoading();
    const modal = window.bootstrap ? window.bootstrap.Modal.getOrCreateInstance(modalEl) : null;
    if (modal) modal.show();

    const qs = new URLSearchParams({
      ano: btn.dataset.ano || '',
      mes: btn.dataset.mes || '',
      tipo: btn.dataset.tipo || ''
    });

    try {
      const response = await fetch(`/api/indicadores/faturacao-anual/detalhe?${qs.toString()}`);
      const data = await response.json();
      if (!response.ok || data.error) throw new Error(data.error || 'Erro ao carregar detalhe.');
      renderDetail(data);
    } catch (error) {
      const body = document.getElementById('fatDetailBody');
      if (body) {
        body.innerHTML = `<tr class="sz_table_row"><td class="sz_table_cell text-center text-danger" colspan="8" data-label="Detalhe">${escapeHtml(error.message || 'Erro ao carregar detalhe.')}</td></tr>`;
      }
    }
  }

  document.addEventListener('DOMContentLoaded', () => {
    const yearSelect = document.getElementById('fatAno');
    const initialYear = yearSelect ? (yearSelect.value || yearSelect.dataset.currentYear) : '';
    if (yearSelect) {
      yearSelect.addEventListener('change', () => loadResumo(yearSelect.value, { updateUrl: true }));
    }
    loadResumo(initialYear, { updateUrl: false });
  });
})();
