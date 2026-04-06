'use strict';

(function () {
  const cardsEl = document.getElementById('radarCards');
  if (!cardsEl) return;

  const data = Array.isArray(window.RADAR_DATA) ? window.RADAR_DATA.slice() : [];

  const searchInput = document.getElementById('filterSearch');
  const urgentChk = document.getElementById('filterUrgent');
  const tipoSel = document.getElementById('filterTipo');
  const pressaoRange = document.getElementById('filterPressao');
  const pressaoValue = document.getElementById('pressaoValue');
  const csvBtn = document.getElementById('btnCsvExport');
  const resetBtn = document.getElementById('btnResetFilters');
  const emptyStateEl = document.getElementById('radarEmptyState');
  const summaryTextEl = document.getElementById('radarSummaryText');

  const fmtInt = new Intl.NumberFormat('pt-PT', { maximumFractionDigits: 0 });
  const fmtPct1 = new Intl.NumberFormat('pt-PT', { minimumFractionDigits: 1, maximumFractionDigits: 1 });
  const fmtCurrency2 = new Intl.NumberFormat('pt-PT', { style: 'currency', currency: 'EUR', minimumFractionDigits: 0, maximumFractionDigits: 2 });

  const indicatorIds = {
    critical: 'kpiCritical',
    red: 'kpiRed',
    orange: 'kpiOrange',
    green: 'kpiGreen',
    livres7: 'kpiLivres7',
    livres14: 'kpiLivres14',
    livres30: 'kpiLivres30'
  };

  const typeLabels = {
    EXPLORACAO: 'Exploracao',
    GESTAO: 'Gestao'
  };

  const badgeClasses = {
    critical: 'sz_badge sz_badge_danger',
    red: 'sz_badge sz_badge_danger',
    orange: 'sz_badge sz_badge_warning',
    yellow: 'sz_badge sz_badge_warning',
    green: 'sz_badge sz_badge_success'
  };

  const csvColumns = [
    ['Alojamento', 'Alojamento'],
    ['TIPO', 'Tipo'],
    ['Livres_D7', 'Livres D7'],
    ['Livres_D14', 'Livres D14'],
    ['Livres_D30', 'Livres D30'],
    ['Pressao_D7', 'Pressao D7'],
    ['Pressao_D14', 'Pressao D14'],
    ['Pressao_D30', 'Pressao D30'],
    ['ADR_Usado_60d', 'ADR 60d'],
    ['ADR_Portfolio_60d', 'ADR Portfolio 60d'],
    ['Desvio_ADR', 'Desvio ADR'],
    ['Acao', 'Acao']
  ];

  const escapeHtml = (str) => String(str ?? '').replace(/[&<>"']/g, (s) => ({
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#39;'
  }[s] || s));

  const plannerUrlFor = (alojamento) => `/pricing/planner?alojamento=${encodeURIComponent(String(alojamento || '').trim())}`;

  const normalizeText = (value) => String(value ?? '')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .trim();

  const acaoNivel = (texto) => {
    const val = normalizeText(texto);
    if (val.includes('critico')) return 'critical';
    if (val.includes('urgente')) return 'red';
    if (val.includes('ajuste')) return 'orange';
    if (val.includes('atencao') || val.includes('atenc')) return 'yellow';
    return 'green';
  };

  const acaoRank = (texto) => {
    const nivel = acaoNivel(texto);
    if (nivel === 'critical') return 0;
    if (nivel === 'red') return 1;
    if (nivel === 'orange') return 2;
    if (nivel === 'yellow') return 3;
    return 4;
  };

  const numberOrZero = (value) => Number(value) || 0;

  const formatPressao = (value) => `${fmtPct1.format(numberOrZero(value) * 100)}%`;

  const formatDesvio = (value) => {
    const num = numberOrZero(value) * 100;
    const sign = num > 0 ? '+' : '';
    return `${sign}${fmtPct1.format(num)}%`;
  };

  const setText = (id, value) => {
    const el = document.getElementById(id);
    if (el) el.textContent = value;
  };

  const getFilteredRows = () => {
    const search = normalizeText(searchInput?.value || '');
    const onlyUrgent = Boolean(urgentChk?.checked);
    const tipoFiltro = String(tipoSel?.value || 'TODOS').toUpperCase();
    const minPressao = numberOrZero(pressaoRange?.value);

    return data
      .filter((row) => {
        const nome = normalizeText(row.Alojamento);
        const tipo = String(row.TIPO || '').toUpperCase();
        const nivel = acaoNivel(row.Acao);
        const pressaoD7 = numberOrZero(row.Pressao_D7) * 100;

        if (search && !nome.includes(search)) return false;
        if (tipoFiltro !== 'TODOS' && tipo !== tipoFiltro) return false;
        if (onlyUrgent && nivel !== 'red' && nivel !== 'critical') return false;
        if (pressaoD7 < minPressao) return false;
        return true;
      })
      .sort((a, b) => {
        const rankDiff = acaoRank(a.Acao) - acaoRank(b.Acao);
        if (rankDiff !== 0) return rankDiff;

        const p7Diff = numberOrZero(b.Pressao_D7) - numberOrZero(a.Pressao_D7);
        if (p7Diff !== 0) return p7Diff;

        const p14Diff = numberOrZero(b.Pressao_D14) - numberOrZero(a.Pressao_D14);
        if (p14Diff !== 0) return p14Diff;

        const p30Diff = numberOrZero(b.Pressao_D30) - numberOrZero(a.Pressao_D30);
        if (p30Diff !== 0) return p30Diff;

        return String(a.Alojamento || '').localeCompare(String(b.Alojamento || ''), 'pt');
      });
  };

  const renderCard = (row) => {
    const nivel = acaoNivel(row.Acao);
    const tipo = String(row.TIPO || '').toUpperCase();
    const tipoLabel = typeLabels[tipo] || String(row.TIPO || '-');
    const actionBadgeClass = badgeClasses[nivel] || badgeClasses.green;
    const alojamento = String(row.Alojamento || '').trim();
    return `
      <article class="sz_card sz_stack sz_radar_card is-${nivel}">
        <header class="sz_radar_card_header">
          <div>
            <h3 class="sz_radar_card_title">
              <a class="sz_radar_card_link" href="${plannerUrlFor(alojamento)}" title="Abrir no Price Manager">
                <span>${escapeHtml(alojamento)}</span>
                <i class="fa-solid fa-arrow-up-right-from-square" aria-hidden="true"></i>
              </a>
            </h3>
          </div>
          <div class="sz_radar_card_badges">
            <span class="sz_badge sz_badge_info sz_radar_badge_type">${escapeHtml(tipoLabel)}</span>
          </div>
        </header>

        <section class="sz_grid sz_radar_card_stats">
          <div class="sz_card sz_stack sz_radar_metric">
            <div class="sz_caption">Livres D7</div>
            <div class="sz_radar_metric_value">${fmtInt.format(numberOrZero(row.Livres_D7))}</div>
            <div class="sz_text_muted">${escapeHtml(formatPressao(row.Pressao_D7))}</div>
          </div>
          <div class="sz_card sz_stack sz_radar_metric">
            <div class="sz_caption">Livres D14</div>
            <div class="sz_radar_metric_value">${fmtInt.format(numberOrZero(row.Livres_D14))}</div>
            <div class="sz_text_muted">${escapeHtml(formatPressao(row.Pressao_D14))}</div>
          </div>
          <div class="sz_card sz_stack sz_radar_metric">
            <div class="sz_caption">Livres D30</div>
            <div class="sz_radar_metric_value">${fmtInt.format(numberOrZero(row.Livres_D30))}</div>
            <div class="sz_text_muted">${escapeHtml(formatPressao(row.Pressao_D30))}</div>
          </div>
        </section>

        <section class="sz_stack sz_radar_action">
          <span class="${actionBadgeClass}">${escapeHtml(row.Acao || 'OK')}</span>
        </section>
      </article>
    `;
  };

  const updateIndicators = (rows) => {
    let red = 0;
    let critical = 0;
    let orange = 0;
    let green = 0;
    let livres7 = 0;
    let livres14 = 0;
    let livres30 = 0;

    rows.forEach((row) => {
      const nivel = acaoNivel(row.Acao);
      if (nivel === 'critical') critical += 1;
      else if (nivel === 'red') red += 1;
      else if (nivel === 'orange' || nivel === 'yellow') orange += 1;
      else green += 1;

      livres7 += numberOrZero(row.Livres_D7);
      livres14 += numberOrZero(row.Livres_D14);
      livres30 += numberOrZero(row.Livres_D30);
    });

    setText(indicatorIds.critical, fmtInt.format(critical));
    setText(indicatorIds.red, fmtInt.format(red));
    setText(indicatorIds.orange, fmtInt.format(orange));
    setText(indicatorIds.green, fmtInt.format(green));
    setText(indicatorIds.livres7, fmtInt.format(livres7));
    setText(indicatorIds.livres14, fmtInt.format(livres14));
    setText(indicatorIds.livres30, fmtInt.format(livres30));
  };

  const buildFilterSummary = (rows) => {
    const parts = [];
    const total = data.length;
    const visible = rows.length;
    const search = String(searchInput?.value || '').trim();
    const tipo = String(tipoSel?.value || 'TODOS').toUpperCase();
    const minPressao = numberOrZero(pressaoRange?.value);

    if (search) parts.push(`pesquisa "${search}"`);
    if (tipo !== 'TODOS') parts.push(`tipo ${typeLabels[tipo] || tipo}`);
    if (urgentChk?.checked) parts.push('apenas urgentes');
    if (minPressao > 0) parts.push(`pressao D7 >= ${minPressao}%`);

    if (summaryTextEl) {
      if (window.RADAR_ERROR) {
        summaryTextEl.textContent = 'Nao foi possivel atualizar os dados do radar.';
      } else if (!parts.length) {
        summaryTextEl.textContent = `${fmtInt.format(visible)} alojamentos visiveis de ${fmtInt.format(total)}. Ordenacao por criticidade, urgencia e pressao D7.`;
      } else {
        summaryTextEl.textContent = `${fmtInt.format(visible)} de ${fmtInt.format(total)} alojamentos com filtros: ${parts.join(', ')}.`;
      }
    }

  };

  const updateExportState = (rows) => {
    if (!csvBtn) return;
    csvBtn.disabled = rows.length === 0;
  };

  const renderRows = (rows) => {
    if (!rows.length) {
      cardsEl.innerHTML = '';
      if (emptyStateEl) emptyStateEl.hidden = false;
      return;
    }

    if (emptyStateEl) emptyStateEl.hidden = true;
    cardsEl.innerHTML = rows.map(renderCard).join('');
  };

  const toCsvValue = (row, key) => {
    if (key === 'Pressao_D7' || key === 'Pressao_D14' || key === 'Pressao_D30') {
      return formatPressao(row[key]);
    }
    if (key === 'ADR_Usado_60d' || key === 'ADR_Portfolio_60d') {
      return fmtCurrency2.format(numberOrZero(row[key]));
    }
    if (key === 'Desvio_ADR') {
      return formatDesvio(row[key]);
    }
    return row[key] ?? '';
  };

  const exportCsv = (rows) => {
    if (!rows.length) return;

    const header = csvColumns.map(([, label]) => label).join(';');
    const lines = rows.map((row) => csvColumns.map(([key]) => {
      const raw = String(toCsvValue(row, key)).replace(/"/g, '""');
      return `"${raw}"`;
    }).join(';'));

    const csv = ['\uFEFF' + header].concat(lines).join('\r\n');
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    const stamp = new Date().toISOString().slice(0, 10);

    link.href = url;
    link.download = `radar_atencao_${stamp}.csv`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  };

  const applyState = () => {
    const rows = getFilteredRows();

    if (pressaoValue && pressaoRange) {
      pressaoValue.textContent = `${pressaoRange.value}%`;
    }

    updateIndicators(rows);
    buildFilterSummary(rows);
    renderRows(rows);
    updateExportState(rows);

    return rows;
  };

  let currentRows = applyState();

  const refresh = () => {
    currentRows = applyState();
  };

  searchInput?.addEventListener('input', refresh);
  urgentChk?.addEventListener('change', refresh);
  tipoSel?.addEventListener('change', refresh);
  pressaoRange?.addEventListener('input', refresh);

  resetBtn?.addEventListener('click', () => {
    if (searchInput) searchInput.value = '';
    if (urgentChk) urgentChk.checked = false;
    if (tipoSel) tipoSel.value = 'TODOS';
    if (pressaoRange) pressaoRange.value = '0';
    refresh();
  });

  csvBtn?.addEventListener('click', () => exportCsv(currentRows));
})();
