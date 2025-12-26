'use strict';

(function () {
  const tableEl = document.getElementById('radarTable');
  if (!tableEl || !window.$ || !$.fn?.DataTable) return;

  const data = Array.isArray(window.RADAR_DATA) ? window.RADAR_DATA : [];
  const fmtInt = new Intl.NumberFormat('pt-PT', { maximumFractionDigits: 0 });
  const fmtPct1 = new Intl.NumberFormat('pt-PT', { minimumFractionDigits: 1, maximumFractionDigits: 1 });
  const fmtPct0 = new Intl.NumberFormat('pt-PT', { maximumFractionDigits: 0 });
  const fmtCurrency = new Intl.NumberFormat('pt-PT', { style: 'currency', currency: 'EUR', minimumFractionDigits: 0, maximumFractionDigits: 0 });
  const fmtCurrency2 = new Intl.NumberFormat('pt-PT', { style: 'currency', currency: 'EUR', minimumFractionDigits: 0, maximumFractionDigits: 2 });

  const urgentChk = document.getElementById('filterUrgent');
  const tipoSel = document.getElementById('filterTipo');
  const pressaoRange = document.getElementById('filterPressao');
  const pressaoValue = document.getElementById('pressaoValue');
  const csvBtn = document.getElementById('btnCsvExport');

  const escapeHtml = (str) => String(str ?? '').replace(/[&<>"']/g, (s) => ({
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#39;',
  }[s] || s));

  const acaoNivel = (texto) => {
    const val = (texto || '').toString().toLowerCase();
    if (val.includes('urgente')) return 'red';
    if (val.includes('ajuste')) return 'orange';
    if (val.includes('aten')) return 'yellow';
    return 'green';
  };

  const actionBadge = (text) => {
    const nivel = acaoNivel(text);
    const val = String(text || '').trim();
    const cls = nivel === 'red'
      ? 'bg-danger text-white'
      : (nivel === 'orange' || nivel === 'yellow')
        ? 'bg-warning text-dark'
        : 'bg-success text-white';
    return `<span class="badge ${cls}">${escapeHtml(val)}</span>`;
  };

  const formatDesvio = (v) => {
    const num = Number(v || 0) * 100;
    const sign = num > 0 ? '+' : '';
    return `${sign}${fmtPct1.format(num)}%`;
  };

  const formatPressao = (v) => `${fmtPct1.format((Number(v) || 0) * 100)}%`;

  const typeOptions = ['TODOS', 'EXPLORACAO', 'GESTAO'];

  $.fn.dataTable.ext.search.push((settings, _data, _dataIndex, rowData) => {
    if (settings.nTable?.id !== 'radarTable') return true;
    const onlyUrgent = urgentChk?.checked;
    const tipoFiltro = (tipoSel?.value || 'TODOS').toUpperCase();
    const minPressao = Number(pressaoRange?.value || 0);
    const acao = (rowData.Acao || '').trim();
    const tipo = (rowData.TIPO || '').toString().toUpperCase();
    const pressaoD7 = (Number(rowData.Pressao_D7) || 0) * 100;

    const nivel = acaoNivel(acao);
    if (onlyUrgent && nivel !== 'red') return false;
    if (typeOptions.includes(tipoFiltro) && tipoFiltro !== 'TODOS' && tipo !== tipoFiltro) return false;
    if (pressaoD7 < minPressao) return false;
    return true;
  });

  const table = $('#radarTable').DataTable({
    data,
    columns: [
      { data: 'Alojamento', title: 'Alojamento', defaultContent: '' },
      { data: 'TIPO', title: 'Tipo', defaultContent: '' },
      { data: 'Livres_D7', title: 'Livres D7', className: 'text-end', defaultContent: 0 },
      { data: 'Livres_D14', title: 'Livres D14', className: 'text-end', defaultContent: 0 },
      { data: 'Livres_D30', title: 'Livres D30', className: 'text-end', defaultContent: 0 },
      {
        data: 'Pressao_D7',
        title: 'Pressão D7',
        className: 'text-end',
        render: (value, type) => {
          const num = Number(value || 0);
          if (type === 'display') return formatPressao(num);
          return num;
        }
      },
      {
        data: 'Pressao_D14',
        title: 'Pressão D14',
        className: 'text-end',
        render: (value, type) => {
          const num = Number(value || 0);
          if (type === 'display') return formatPressao(num);
          return num;
        }
      },
      {
        data: 'Pressao_D30',
        title: 'Pressão D30',
        className: 'text-end',
        render: (value, type) => {
          const num = Number(value || 0);
          if (type === 'display') return formatPressao(num);
          return num;
        }
      },
      {
        data: 'ADR_Usado_60d',
        title: 'ADR 60d',
        className: 'text-end',
        render: (value, type) => {
          const num = Number(value || 0);
          if (type === 'display') return fmtCurrency.format(num);
          return num;
        }
      },
      {
        data: 'ADR_Portfolio_60d',
        title: 'ADR Portfólio 60d',
        className: 'text-end',
        render: (value, type) => {
          const num = Number(value || 0);
          if (type === 'display') return fmtCurrency.format(num);
          return num;
        }
      },
      {
        data: 'Desvio_ADR',
        title: 'Desvio ADR',
        className: 'text-end',
        render: (value, type) => {
          const num = Number(value || 0);
          if (type === 'display') return formatDesvio(num);
          return num;
        }
      },
      {
        data: 'Acao',
        title: 'Ação',
        className: 'text-wrap',
        render: (value, type) => {
          if (type === 'display') return actionBadge(value);
          return value;
        }
      }
    ],
    order: [
      [5, 'desc'],
      [6, 'desc'],
      [7, 'desc'],
      [0, 'asc']
    ],
    paging: false,
    pageLength: 25,
    autoWidth: false,
    dom: "<'row mb-2'<'col-sm-12 col-md-6 d-flex align-items-center'B><'col-sm-12 col-md-6'f>>" +
         "tr" +
         "<'row mt-2'<'col-sm-12 col-md-5'i><'col-sm-12 col-md-7'p>>",
    buttons: [
      {
        extend: 'csvHtml5',
        text: 'Exportar CSV',
        className: 'btn btn-outline-secondary btn-sm',
        title: 'radar_atencao',
        exportOptions: {
          columns: ':visible',
          modifier: { search: 'applied' }
        }
      }
    ],
    language: {
      emptyTable: 'Sem dados para mostrar',
      info: 'A mostrar _START_ a _END_ de _TOTAL_ alojamentos',
      infoEmpty: 'Sem alojamentos',
      infoFiltered: '(filtrado de _MAX_)',
      lengthMenu: 'Mostrar _MENU_',
      loadingRecords: 'A carregar...',
      processing: 'A processar...',
      search: 'Procurar:',
      zeroRecords: 'Sem resultados com os filtros atuais',
      paginate: {
        first: 'Primeiro',
        last: 'Último',
        next: 'Seguinte',
        previous: 'Anterior'
      }
    }
  });

  $(table.buttons().container()).addClass('d-none');

  const updateSummary = () => {
    const rows = table.rows({ search: 'applied' }).data().toArray();
    let red = 0, orange = 0, green = 0;
    let livres7 = 0, livres14 = 0, livres30 = 0;

    rows.forEach((r) => {
      const nivel = acaoNivel(r.Acao);
      if (nivel === 'red') red += 1;
      else if (nivel === 'orange' || nivel === 'yellow') orange += 1;
      else green += 1;

      livres7 += Number(r.Livres_D7) || 0;
      livres14 += Number(r.Livres_D14) || 0;
      livres30 += Number(r.Livres_D30) || 0;
    });

    const setText = (id, val) => {
      const el = document.getElementById(id);
      if (el) el.textContent = val;
    };

    setText('kpiRed', fmtInt.format(red));
    setText('kpiOrange', fmtInt.format(orange));
    setText('kpiGreen', fmtInt.format(green));
    setText('kpiLivres7', fmtInt.format(livres7));
    setText('kpiLivres14', fmtInt.format(livres14));
    setText('kpiLivres30', fmtInt.format(livres30));
  };

  const updateFooter = () => {
    const rows = table.rows({ search: 'applied' }).data().toArray();
    let livres7 = 0, livres14 = 0, livres30 = 0;
    let pressao7 = 0, pressao14 = 0, pressao30 = 0;
    let adrUsadoWeighted = 0, adrPortfolioWeighted = 0, weightAdr = 0;
    let desvio = 0;

    rows.forEach((r) => {
      const l7 = Number(r.Livres_D7) || 0;
      const l14 = Number(r.Livres_D14) || 0;
      const l30 = Number(r.Livres_D30) || 0;
      const p7 = Number(r.Pressao_D7) || 0;
      const p14 = Number(r.Pressao_D14) || 0;
      const p30 = Number(r.Pressao_D30) || 0;
      const adrUsado = Number(r.ADR_Usado_60d) || 0;
      const adrPort = Number(r.ADR_Portfolio_60d) || 0;
      const dev = Number(r.Desvio_ADR) || 0;
      const weight = Math.max(l30, 1); // pondera pelo horizonte de 30 dias, garantindo peso > 0

      livres7 += l7;
      livres14 += l14;
      livres30 += l30;
      pressao7 += p7;
      pressao14 += p14;
      pressao30 += p30;
      desvio += dev;

      adrUsadoWeighted += adrUsado * weight;
      adrPortfolioWeighted += adrPort * weight;
      weightAdr += weight;
    });

    const count = rows.length || 1;
    const avgPressao7 = pressao7 / count;
    const avgPressao14 = pressao14 / count;
    const avgPressao30 = pressao30 / count;
    const avgAdrUsado = weightAdr ? adrUsadoWeighted / weightAdr : 0;
    const avgAdrPort = weightAdr ? adrPortfolioWeighted / weightAdr : 0;
    const avgDesvio = desvio / count;

    const setVal = (id, text) => {
      const el = document.getElementById(id);
      if (el) el.textContent = text;
    };

    setVal('ftLivres7', fmtInt.format(livres7));
    setVal('ftLivres14', fmtInt.format(livres14));
    setVal('ftLivres30', fmtInt.format(livres30));
    setVal('ftPressao7', formatPressao(avgPressao7));
    setVal('ftPressao14', formatPressao(avgPressao14));
    setVal('ftPressao30', formatPressao(avgPressao30));
    setVal('ftAdrUsado', fmtCurrency2.format(avgAdrUsado));
    setVal('ftAdrPortfolio', fmtCurrency2.format(avgAdrPort));
    setVal('ftDesvioAdr', formatDesvio(avgDesvio));
  };

  const bindFilters = () => {
    if (pressaoRange && pressaoValue) {
      pressaoValue.textContent = `${pressaoRange.value}%`;
      pressaoRange.addEventListener('input', () => {
        pressaoValue.textContent = `${pressaoRange.value}%`;
        table.draw();
      });
    }
    if (urgentChk) {
      urgentChk.addEventListener('change', () => table.draw());
    }
    if (tipoSel) {
      tipoSel.addEventListener('change', () => table.draw());
    }
  };

  const bindExport = () => {
    if (!csvBtn) return;
    csvBtn.addEventListener('click', () => {
      const btn = table.button('.buttons-csv');
      if (btn) btn.trigger();
    });
  };

  table.on('draw', () => {
    updateSummary();
    updateFooter();
  });

  bindFilters();
  bindExport();
  updateSummary();
  updateFooter();
})();
