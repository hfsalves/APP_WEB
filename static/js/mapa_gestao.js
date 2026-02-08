// static/js/mapa_gestao.js

document.addEventListener('DOMContentLoaded', () => {
  const anoInput = document.getElementById('mapAno');
  const diffEnableEl = document.getElementById('mapDiffEnable');
  const diffPctEl = document.getElementById('mapDiffPct');
  const showBudgetEl = document.getElementById('mapShowBudget');
  const btnViewTable = document.getElementById('mapViewTable');
  const btnViewCharts = document.getElementById('mapViewCharts');
  const tableViewEl = document.getElementById('mapTableView');
  const chartViewEl = document.getElementById('mapChartView');
  const treeControlsEl = document.getElementById('mapTreeControls');
  const ccModalEl = document.getElementById('mapCcustoModal');
  const ccList = document.getElementById('mapCcList');
  const ccLabel = document.getElementById('mapCcustoLabel');
  const ccCount = document.getElementById('mapCcustoCount');
  const btnCcusto = document.getElementById('mapBtnCcusto');
  const btnCcAll = document.getElementById('mapCcAll');
  const btnCcNone = document.getElementById('mapCcNone');
  const btnCcEstrutura = document.getElementById('mapCcEstrutura');
  const btnCcExploracao = document.getElementById('mapCcExploracao');
  const btnCcGestao = document.getElementById('mapCcGestao');
  const btnCcApply = document.getElementById('mapCcApply');
  const btnAplicar = document.getElementById('mapBtnAplicar');
  const btnLimpar = document.getElementById('mapBtnLimpar');
  const btnExpandAll = document.getElementById('mapExpandAll');
  const btnCollapseAll = document.getElementById('mapCollapseAll');
  const detailModalEl = document.getElementById('mapDetailModal');
  const detailBody = document.getElementById('mapDetailBody');
  const detailTitle = document.getElementById('mapDetailTitle');
  const detailTotal = document.getElementById('mapDetailTotal');
  const detailModal = detailModalEl ? new bootstrap.Modal(detailModalEl) : null;
  const tbody = document.getElementById('mapaBody');
  const totalLbl = document.getElementById('mapTotal');
  const filtrosLbl = document.getElementById('mapFiltros');
  const defaultYear = window.MAPA_ANO_PADRAO || new Date().getFullYear();
  const modalCcusto = ccModalEl ? new bootstrap.Modal(ccModalEl) : null;
  let ccOptions = []; // [{ccusto, tipo}]
  let ccSelected = new Set();
  let lastRows = [];
  let treeExpanded = new Set(); // refs abertos (por defeito vazio: apenas nivel 1 visivel)
  let levelOneRefs = [];
  let allRefs = [];
  let currentView = 'table'; // table | charts
  let chartSalesVsGoal = null;
  let chartCostsVsBudget = null;
  let chartMarginRealVsForecast = null;
  let chartResDaily = null;
  let resDailyYear = null;
  let resDailyMonth = null; // 1..12
  let chartAdrDaily = null;
  let adrDailyYear = null;
  let adrDailyMonth = null; // 1..12
  let chartCostsRubrics = null;
  let costsRubricsYear = null;
  let costsRubricsMonth = null; // 1..12
  let chartSalesAloj = null;
  let salesAlojYear = null;
  let salesAlojMonth = null; // 1..12
  let chartMarginAloj = null;
  let marginAlojYear = null;
  let marginAlojMonth = null; // 1..12
  let lastKpis = {};

  const fmtNum = new Intl.NumberFormat('pt-PT', { minimumFractionDigits: 0, maximumFractionDigits: 0, useGrouping: true });
  const fmtPct = new Intl.NumberFormat('pt-PT', { minimumFractionDigits: 1, maximumFractionDigits: 1, useGrouping: true });
  const fmtCur = new Intl.NumberFormat('pt-PT', { style: 'currency', currency: 'EUR', maximumFractionDigits: 0, useGrouping: true });
  const fmtCur2 = new Intl.NumberFormat('pt-PT', { style: 'currency', currency: 'EUR', minimumFractionDigits: 2, maximumFractionDigits: 2, useGrouping: true });
  const fmtNum2 = new Intl.NumberFormat('pt-PT', { minimumFractionDigits: 2, maximumFractionDigits: 2, useGrouping: true });
  const attrEscape = (str) => String(str == null ? '' : str).replace(/"/g, '&quot;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  const monthNames = ['Jan','Fev','Mar','Abr','Mai','Jun','Jul','Ago','Set','Out','Nov','Dez'];

  if (anoInput && !anoInput.value) {
    anoInput.value = defaultYear;
  }

  // evidenciar diferenças vs orçamento (persistência)
  const savedPct = localStorage.getItem('mapDiffPct');
  if (diffPctEl && savedPct != null && savedPct !== '') diffPctEl.value = savedPct;
  // Por defeito: não evidenciar (sem visto), independentemente de preferências anteriores
  if (diffEnableEl) diffEnableEl.checked = false;
  if (diffPctEl && (!diffPctEl.value || diffPctEl.value === '0')) diffPctEl.value = '3';
  if (showBudgetEl) showBudgetEl.checked = false;

  function escapeHtml(str) {
    return String(str == null ? '' : str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function setView(view) {
    const v = (view || '').toString().trim().toLowerCase();
    currentView = (v === 'charts') ? 'charts' : 'table';
    if (tableViewEl) tableViewEl.style.display = currentView === 'table' ? '' : 'none';
    if (chartViewEl) chartViewEl.style.display = currentView === 'charts' ? '' : 'none';
    if (treeControlsEl) treeControlsEl.style.display = currentView === 'table' ? '' : 'none';
    btnViewTable?.classList.toggle('active', currentView === 'table');
    btnViewCharts?.classList.toggle('active', currentView === 'charts');
    if (currentView === 'charts') renderCharts();
  }

  function findRow(ref) {
    const key = String(ref || '').trim();
    if (!key) return null;
    return lastRows.find(r => String(r.ref || '').trim() === key) || null;
  }

  function renderCharts() {
    if (typeof Chart === 'undefined') return;

    // KPIs (Totais do ano)
    {
      const salesMain = document.getElementById('mapKpiSalesMain');
      const salesSub = document.getElementById('mapKpiSalesSub');
      const salesDelta = document.getElementById('mapKpiSalesDelta');
      const costsMain = document.getElementById('mapKpiCostsMain');
      const costsSub = document.getElementById('mapKpiCostsSub');
      const costsDelta = document.getElementById('mapKpiCostsDelta');
      const marginMain = document.getElementById('mapKpiMarginMain');
      const marginSub = document.getElementById('mapKpiMarginSub');
      const marginDelta = document.getElementById('mapKpiMarginDelta');
      const adrMain = document.getElementById('mapKpiAdrMain');
      const adrSub = document.getElementById('mapKpiAdrSub');
      const resMain = document.getElementById('mapKpiResMain');
      const resSub = document.getElementById('mapKpiResSub');
      const kpi6Main = document.getElementById('mapKpi6Main');
      const kpi6Sub = document.getElementById('mapKpi6Sub');

      const safePct = (num) => {
        if (!isFinite(num)) return '--';
        return `${fmtPct.format(num)}%`;
      };

      const setDeltaBadge = (el, pct, goodWhenPositive) => {
        if (!el) return;
        const clsGood = 'bg-success-subtle text-success';
        const clsBad = 'bg-danger-subtle text-danger';
        const clsNeutral = 'bg-secondary-subtle text-secondary';
        el.className = `badge rounded-pill ${clsNeutral}`;
        if (!isFinite(pct)) {
          el.textContent = '--';
          return;
        }
        el.textContent = safePct(pct);
        const isGood = goodWhenPositive ? pct >= 0 : pct <= 0;
        el.className = `badge rounded-pill ${isGood ? clsGood : clsBad}`;
      };

      // Proveitos (famílias 9): preferir a linha agregada "9", senão somar nível 1 começadas por 9
      let salesActualTotal = 0;
      let salesGoalTotal = 0;
      const r9 = findRow('9');
      if (r9) {
        salesActualTotal = Number(r9.total || 0);
        salesGoalTotal = Number(r9.orc_total || 0);
      } else {
        lastRows
          .filter(r => Number(r.nivel || 1) === 1 && String(r.ref || '').trim().startsWith('9'))
          .forEach(r => {
            salesActualTotal += Number(r.total || 0);
            salesGoalTotal += Number(r.orc_total || 0);
          });
      }

      // Custos (exceto 9): somar apenas nível 1
      let costsActualTotal = 0;
      let costsBudgetTotal = 0;
      lastRows
        .filter(r => Number(r.nivel || 1) === 1 && !String(r.ref || '').trim().startsWith('9'))
        .forEach(r => {
          costsActualTotal += Number(r.total || 0);
          costsBudgetTotal += Number(r.orc_total || 0);
        });

      const marginActualTotal = salesActualTotal - costsActualTotal;
      const marginForecastTotal = salesGoalTotal - costsBudgetTotal;

      if (salesMain) salesMain.textContent = fmtCur.format(salesActualTotal);
      if (salesSub) salesSub.textContent = `Objetivo: ${fmtCur.format(salesGoalTotal)}`;
      setDeltaBadge(salesDelta, salesGoalTotal ? ((salesActualTotal - salesGoalTotal) / salesGoalTotal) * 100 : NaN, true);

      if (costsMain) costsMain.textContent = fmtCur.format(costsActualTotal);
      if (costsSub) costsSub.textContent = `Orçamento: ${fmtCur.format(costsBudgetTotal)}`;
      // custos: bom quando Real <= Orçamento
      setDeltaBadge(costsDelta, costsBudgetTotal ? ((costsActualTotal - costsBudgetTotal) / costsBudgetTotal) * 100 : NaN, false);

      if (marginMain) marginMain.textContent = fmtCur.format(marginActualTotal);
      if (marginSub) marginSub.textContent = `Previsão: ${fmtCur.format(marginForecastTotal)}`;
      setDeltaBadge(marginDelta, marginForecastTotal ? ((marginActualTotal - marginForecastTotal) / marginForecastTotal) * 100 : NaN, true);

      if (adrMain) {
        const rawAdr = lastKpis?.preco_medio_noite;
        if (rawAdr === null || rawAdr === undefined || rawAdr === '') {
          adrMain.textContent = '--';
        } else {
          const adr = Number(rawAdr);
          adrMain.textContent = isFinite(adr) ? fmtCur2.format(adr) : '--';
        }
      }
      if (adrSub) {
        const rawNoites = lastKpis?.preco_medio_noite_noites;
        if (rawNoites === null || rawNoites === undefined || rawNoites === '') {
          adrSub.textContent = 'Noites: --';
        } else {
          const noites = Number(rawNoites);
          adrSub.textContent = isFinite(noites) ? `Noites: ${fmtNum.format(noites)}` : 'Noites: --';
        }
      }

      if (resMain) {
        const rawRes = lastKpis?.numero_reservas;
        if (rawRes === null || rawRes === undefined || rawRes === '') resMain.textContent = '--';
        else {
          const n = Number(rawRes);
          resMain.textContent = isFinite(n) ? fmtNum.format(n) : '--';
        }
      }
      if (resSub) {
        const rawHosp = lastKpis?.numero_hospedes;
        if (rawHosp === null || rawHosp === undefined || rawHosp === '') resSub.textContent = 'Hospedes: --';
        else {
          const n = Number(rawHosp);
          resSub.textContent = isFinite(n) ? `Hospedes: ${fmtNum.format(n)}` : 'Hospedes: --';
        }
      }

      if (kpi6Main) {
        const rawAvg = lastKpis?.reservas_ano_media_dia;
        if (rawAvg === null || rawAvg === undefined || rawAvg === '') kpi6Main.textContent = '--';
        else {
          const n = Number(rawAvg);
          kpi6Main.textContent = isFinite(n) ? fmtCur2.format(n) : '--';
        }
      }
      if (kpi6Sub) {
        const rawTot = lastKpis?.reservas_ano_total;
        if (rawTot === null || rawTot === undefined || rawTot === '') kpi6Sub.textContent = 'Total ano: --';
        else {
          const n = Number(rawTot);
          kpi6Sub.textContent = isFinite(n) ? `Total ano: ${fmtCur.format(n)}` : 'Total ano: --';
        }
      }
    }
    // 1) Vendas vs Objetivo (Famílias 9)
    {
      const canvas = document.getElementById('mapChartSalesVsGoal');
      if (canvas) {
        const r9 = findRow('9') || findRow('9.1') || null;
        const actual = (r9?.meses || Array(12).fill(0)).slice(0, 12).map(v => Number(v || 0));
        const goal = (r9?.orc_meses || Array(12).fill(0)).slice(0, 12).map(v => Number(v || 0));

        try { chartSalesVsGoal?.destroy?.(); } catch (_) {}
        chartSalesVsGoal = new Chart(canvas.getContext('2d'), {
          type: 'bar',
          data: {
            labels: monthNames,
            datasets: [
              {
                label: 'Real',
                data: actual,
                backgroundColor: 'rgba(14, 165, 233, 0.35)',
                borderColor: 'rgba(14, 165, 233, 0.85)',
                borderWidth: 1,
                borderRadius: 6,
                borderSkipped: false
              },
              {
                label: 'Objetivo',
                data: goal,
                backgroundColor: 'rgba(124, 58, 237, 0.25)',
                borderColor: 'rgba(124, 58, 237, 0.85)',
                borderWidth: 1,
                borderRadius: 6,
                borderSkipped: false
              }
            ]
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
              legend: { display: true, position: 'bottom' },
              tooltip: {
                callbacks: {
                  label: (ctx) => {
                    const v = Number(ctx.parsed?.y || 0);
                    return `${ctx.dataset.label}: ${fmtCur.format(v)}`;
                  }
                }
              }
            },
            scales: {
              x: { grid: { display: false } },
              y: {
                beginAtZero: true,
                ticks: {
                  callback: (v) => {
                    try { return fmtNum.format(Number(v || 0)); } catch (_) { return v; }
                  }
                },
                grid: { display: true, color: '#e5e7eb' }
              }
            }
          }
        });
      }
    }

    // 2) Custos vs Orçamento (Famílias exceto 9) - somar apenas nível 1 para evitar duplicações
    {
      const canvas = document.getElementById('mapChartCostsVsBudget');
      if (canvas) {
        const costActual = Array(12).fill(0);
        const costBudget = Array(12).fill(0);
        lastRows
          .filter(r => Number(r.nivel || 1) === 1 && !String(r.ref || '').trim().startsWith('9'))
          .forEach(r => {
            const a = (r.meses || Array(12).fill(0)).slice(0, 12);
            const b = (r.orc_meses || Array(12).fill(0)).slice(0, 12);
            for (let i = 0; i < 12; i++) {
              costActual[i] += Number(a[i] || 0);
              costBudget[i] += Number(b[i] || 0);
            }
          });

        try { chartCostsVsBudget?.destroy?.(); } catch (_) {}
        chartCostsVsBudget = new Chart(canvas.getContext('2d'), {
          type: 'bar',
          data: {
            labels: monthNames,
            datasets: [
              {
                label: 'Real',
                data: costActual,
                backgroundColor: 'rgba(244, 63, 94, 0.25)',
                borderColor: 'rgba(244, 63, 94, 0.85)',
                borderWidth: 1,
                borderRadius: 6,
                borderSkipped: false
              },
              {
                label: 'Orçamento',
                data: costBudget,
                backgroundColor: 'rgba(107, 114, 128, 0.18)',
                borderColor: 'rgba(107, 114, 128, 0.75)',
                borderWidth: 1,
                borderRadius: 6,
                borderSkipped: false
              }
            ]
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
              legend: { display: true, position: 'bottom' },
              tooltip: {
                callbacks: {
                  label: (ctx) => {
                    const v = Number(ctx.parsed?.y || 0);
                    return `${ctx.dataset.label}: ${fmtCur.format(v)}`;
                  }
                }
              }
            },
            scales: {
              x: { grid: { display: false } },
              y: {
                beginAtZero: true,
                ticks: {
                  callback: (v) => {
                    try { return fmtNum.format(Number(v || 0)); } catch (_) { return v; }
                  }
                },
                grid: { display: true, color: '#e5e7eb' }
              }
            }
          }
        });
      }
    }

    // 3) Margem Real vs Previsional (Proveitos 9 - Custos exceto 9) - nível 1
    {
      const canvas = document.getElementById('mapChartMarginRealVsForecast');
      if (canvas) {
        const provActual = Array(12).fill(0);
        const provForecast = Array(12).fill(0);
        const costActual = Array(12).fill(0);
        const costForecast = Array(12).fill(0);

        lastRows
          .filter(r => Number(r.nivel || 1) === 1)
          .forEach(r => {
            const ref = String(r.ref || '').trim();
            const isProv = ref.startsWith('9');
            const a = (r.meses || Array(12).fill(0)).slice(0, 12);
            const b = (r.orc_meses || Array(12).fill(0)).slice(0, 12);
            for (let i = 0; i < 12; i++) {
              if (isProv) {
                provActual[i] += Number(a[i] || 0);
                provForecast[i] += Number(b[i] || 0);
              } else {
                costActual[i] += Number(a[i] || 0);
                costForecast[i] += Number(b[i] || 0);
              }
            }
          });

        const marginActual = provActual.map((v, i) => Number(v || 0) - Number(costActual[i] || 0));
        const marginForecast = provForecast.map((v, i) => Number(v || 0) - Number(costForecast[i] || 0));

        try { chartMarginRealVsForecast?.destroy?.(); } catch (_) {}
        chartMarginRealVsForecast = new Chart(canvas.getContext('2d'), {
          type: 'bar',
          data: {
            labels: monthNames,
            datasets: [
              {
                label: 'Real',
                data: marginActual,
                backgroundColor: 'rgba(34, 197, 94, 0.25)',
                borderColor: 'rgba(34, 197, 94, 0.85)',
                borderWidth: 1,
                borderRadius: 6,
                borderSkipped: false
              },
              {
                label: 'Previsional',
                data: marginForecast,
                backgroundColor: 'rgba(59, 130, 246, 0.18)',
                borderColor: 'rgba(59, 130, 246, 0.80)',
                borderWidth: 1,
                borderRadius: 6,
                borderSkipped: false
              }
            ]
          },
          options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
              legend: { display: true, position: 'bottom' },
              tooltip: {
                callbacks: {
                  label: (ctx) => {
                    const v = Number(ctx.parsed?.y || 0);
                    return `${ctx.dataset.label}: ${fmtCur.format(v)}`;
                  }
                }
              }
            },
            scales: {
              x: { grid: { display: false } },
              y: {
                ticks: {
                  callback: (v) => {
                    try { return fmtNum.format(Number(v || 0)); } catch (_) { return v; }
                  }
                },
                grid: {
                  color: (ctx) => (Number(ctx.tick?.value) === 0 ? '#94a3b8' : '#e5e7eb'),
                  lineWidth: (ctx) => (Number(ctx.tick?.value) === 0 ? 2 : 1)
                }
              }
            }
          }
        });
      }
    }
  }

  const resDailyModalEl = document.getElementById('mapResDailyModal');
  const resDailyModal = resDailyModalEl ? new bootstrap.Modal(resDailyModalEl) : null;
  const resPrevBtn = document.getElementById('mapResPrev');
  const resNextBtn = document.getElementById('mapResNext');
  const resMonthLabelEl = document.getElementById('mapResMonthLabel');
  const resTotalEl = document.getElementById('mapResDailyTotal');

  const adrDailyModalEl = document.getElementById('mapAdrDailyModal');
  const adrDailyModal = adrDailyModalEl ? new bootstrap.Modal(adrDailyModalEl) : null;
  const adrPrevBtn = document.getElementById('mapAdrPrev');
  const adrNextBtn = document.getElementById('mapAdrNext');
  const adrMonthLabelEl = document.getElementById('mapAdrMonthLabel');
  const adrTotalEl = document.getElementById('mapAdrDailyTotal');

  const costsRubricModalEl = document.getElementById('mapCostsRubricModal');
  const costsRubricModal = costsRubricModalEl ? new bootstrap.Modal(costsRubricModalEl) : null;
  const costsPrevBtn = document.getElementById('mapCostsPrev');
  const costsNextBtn = document.getElementById('mapCostsNext');
  const costsMonthLabelEl = document.getElementById('mapCostsMonthLabel');
  const costsTotalEl = document.getElementById('mapCostsRubricTotal');

  const salesAlojModalEl = document.getElementById('mapSalesAlojModal');
  const salesAlojModal = salesAlojModalEl ? new bootstrap.Modal(salesAlojModalEl) : null;
  const salesPrevBtn = document.getElementById('mapSalesPrev');
  const salesNextBtn = document.getElementById('mapSalesNext');
  const salesMonthLabelEl = document.getElementById('mapSalesMonthLabel');
  const salesTotalEl = document.getElementById('mapSalesAlojTotal');

  const marginAlojModalEl = document.getElementById('mapMarginAlojModal');
  const marginAlojModal = marginAlojModalEl ? new bootstrap.Modal(marginAlojModalEl) : null;
  const marginPrevBtn = document.getElementById('mapMarginPrev');
  const marginNextBtn = document.getElementById('mapMarginNext');
  const marginMonthLabelEl = document.getElementById('mapMarginMonthLabel');
  const marginTotalEl = document.getElementById('mapMarginAlojTotal');

  const countryModalEl = document.getElementById('mapResCountryModal');
  const countryModal = countryModalEl ? new bootstrap.Modal(countryModalEl) : null;
  const countryPrevBtn = document.getElementById('mapCountryPrev');
  const countryNextBtn = document.getElementById('mapCountryNext');
  const countryMonthLabelEl = document.getElementById('mapCountryMonthLabel');
  const countryBodyEl = document.getElementById('mapCountryBody');
  const countryTotalEl = document.getElementById('mapCountryTotal');
  let countryYear = null;
  let countryRowsCache = [];
  let countryTotalValCache = 0;
  let countrySort = { key: 'valor', dir: 'desc' }; // default: maior valor

  function monthLabel(ano, mes) {
    const m = Number(mes);
    const y = Number(ano);
    if (!isFinite(m) || !isFinite(y) || m < 1 || m > 12) return '--';
    return `${monthNames[m - 1]} ${y}`;
  }

  async function loadResDaily() {
    if (!resDailyModalEl) return;
    const ano = Number(resDailyYear || parseInt(anoInput?.value, 10) || new Date().getFullYear());
    const mes = Number(resDailyMonth || (new Date().getMonth() + 1));
    if (resMonthLabelEl) resMonthLabelEl.textContent = monthLabel(ano, mes);
    if (resTotalEl) resTotalEl.textContent = 'Total: --';

    const ccustos = getSelectedCcustos();
    const qs = new URLSearchParams({ ano: String(ano), mes: String(mes) });
    if (ccustos.length) qs.set('ccustos', ccustos.join(','));

    let data;
    try {
      const res = await fetch(`/api/mapa_gestao/reservas_diarias?${qs.toString()}`);
      data = await res.json();
      if (!res.ok || data.error) throw new Error(data.error || 'Erro ao obter reservas diárias');
    } catch (err) {
      console.error(err);
      if (resTotalEl) resTotalEl.textContent = `Erro: ${err.message || err}`;
      return;
    }

    const canvas = document.getElementById('mapResDailyChart');
    if (!canvas || typeof Chart === 'undefined') return;

    const labels = (Array.isArray(data.labels) ? data.labels : []).map(n => String(n));
    const values = (Array.isArray(data.values) ? data.values : []).map(v => Number(v || 0));
    const total = Number(data.total || 0);
    if (resTotalEl) resTotalEl.textContent = `Total: ${fmtCur.format(total)}`;

    const dayNums = (Array.isArray(data.labels) ? data.labels : []).map(n => Number(n));
    const bgColors = dayNums.map((d) => {
      const day = Number(d);
      const wd = new Date(ano, mes - 1, day).getDay(); // 0=Dom,6=Sáb
      const weekend = (wd === 0 || wd === 6);
      return weekend ? 'rgba(59, 130, 246, 0.38)' : 'rgba(59, 130, 246, 0.22)';
    });
    const borderColors = dayNums.map((d) => {
      const day = Number(d);
      const wd = new Date(ano, mes - 1, day).getDay();
      const weekend = (wd === 0 || wd === 6);
      return weekend ? 'rgba(30, 64, 175, 0.95)' : 'rgba(59, 130, 246, 0.85)';
    });

    try { chartResDaily?.destroy?.(); } catch (_) {}
    chartResDaily = new Chart(canvas.getContext('2d'), {
      type: 'bar',
      data: {
        labels,
        datasets: [
          {
            label: 'Reservas recebidas',
            data: values,
            backgroundColor: bgColors,
            borderColor: borderColors,
            borderWidth: 1,
            borderRadius: 6,
            borderSkipped: false
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: (ctx) => {
                const v = Number(ctx.parsed?.y || 0);
                return fmtCur.format(v);
              }
            }
          }
        },
        scales: {
          x: { grid: { display: false } },
          y: {
            beginAtZero: true,
            ticks: {
              callback: (v) => {
                try { return fmtNum.format(Number(v || 0)); } catch (_) { return v; }
              }
            },
            grid: { display: true, color: '#e5e7eb' }
          }
        }
      }
    });
  }

  async function loadAdrDaily() {
    if (!adrDailyModalEl) return;
    const ano = Number(adrDailyYear || parseInt(anoInput?.value, 10) || new Date().getFullYear());
    const mes = Number(adrDailyMonth || (new Date().getMonth() + 1));
    if (adrMonthLabelEl) adrMonthLabelEl.textContent = monthLabel(ano, mes);
    if (adrTotalEl) adrTotalEl.textContent = 'ADR: --';

    const ccustos = getSelectedCcustos();
    const qs = new URLSearchParams({ ano: String(ano), mes: String(mes) });
    if (ccustos.length) qs.set('ccustos', ccustos.join(','));

    let data;
    try {
      const res = await fetch(`/api/mapa_gestao/adr_diario?${qs.toString()}`);
      data = await res.json();
      if (!res.ok || data.error) throw new Error(data.error || 'Erro ao obter ADR diário');
    } catch (err) {
      console.error(err);
      if (adrTotalEl) adrTotalEl.textContent = `Erro: ${err.message || err}`;
      return;
    }

    const canvas = document.getElementById('mapAdrDailyChart');
    if (!canvas || typeof Chart === 'undefined') return;

    const labels = (Array.isArray(data.labels) ? data.labels : []).map(n => String(n));
    const values = (Array.isArray(data.values) ? data.values : []).map(v => (v === null || v === undefined || v === '' ? null : Number(v)));
    const adr = (data.adr === null || data.adr === undefined || data.adr === '' ? null : Number(data.adr));
    const noites = Number(data.noites || 0);
    const noitesByDay = (Array.isArray(data.noites_by_day) ? data.noites_by_day : []).map(v => Number(v || 0));
    const netByDay = (Array.isArray(data.net_by_day) ? data.net_by_day : []).map(v => Number(v || 0));
    if (adrTotalEl) {
      const adrTxt = (adr !== null && isFinite(adr)) ? fmtCur2.format(adr) : '--';
      adrTotalEl.textContent = `ADR: ${adrTxt}  •  Noites: ${fmtNum.format(noites)}`;
    }

    const dayNums = (Array.isArray(data.labels) ? data.labels : []).map(n => Number(n));
    const bgColors = dayNums.map((d) => {
      const day = Number(d);
      const wd = new Date(ano, mes - 1, day).getDay();
      const weekend = (wd === 0 || wd === 6);
      return weekend ? 'rgba(14, 165, 233, 0.35)' : 'rgba(14, 165, 233, 0.18)';
    });
    const borderColors = dayNums.map((d) => {
      const day = Number(d);
      const wd = new Date(ano, mes - 1, day).getDay();
      const weekend = (wd === 0 || wd === 6);
      return weekend ? 'rgba(12, 74, 110, 0.95)' : 'rgba(14, 165, 233, 0.80)';
    });

    try { chartAdrDaily?.destroy?.(); } catch (_) {}
    chartAdrDaily = new Chart(canvas.getContext('2d'), {
      type: 'bar',
      data: {
        labels,
        datasets: [
          {
            label: 'ADR',
            data: values,
            _noitesByDay: noitesByDay,
            _netByDay: netByDay,
            backgroundColor: bgColors,
            borderColor: borderColors,
            borderWidth: 1,
            borderRadius: 6,
            borderSkipped: false
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: (ctx) => {
                const v = ctx.parsed?.y;
                if (v === null || v === undefined || !isFinite(Number(v))) return 'Sem dados';
                const idx = Number(ctx.dataIndex || 0);
                const ds = ctx.dataset || {};
                const n = Array.isArray(ds._noitesByDay) ? Number(ds._noitesByDay[idx] || 0) : 0;
                const net = Array.isArray(ds._netByDay) ? Number(ds._netByDay[idx] || 0) : 0;
                return `${fmtCur2.format(Number(v))}  •  Noites: ${fmtNum.format(n)}  •  Net: ${fmtCur.format(net)}`;
              }
            }
          }
        },
        scales: {
          x: { grid: { display: false } },
          y: {
            beginAtZero: true,
            ticks: {
              callback: (v) => {
                try { return fmtNum2.format(Number(v || 0)); } catch (_) { return v; }
              }
            },
            grid: { display: true, color: '#e5e7eb' }
          }
        }
      }
    });
  }

  function getCostRubricsForMonth(mes) {
    const mIdx = Number(mes) - 1;
    if (!isFinite(mIdx) || mIdx < 0 || mIdx > 11) return [];

    const level1NameByRef = new Map(
      lastRows
        .filter(r => Number(r.nivel || 1) === 1)
        .map(r => [String(r.ref || '').trim(), String(r.nome || '').trim()])
        .filter(([ref]) => !!ref)
    );

    const sortKey = (ref) => {
      const parts = String(ref || '').trim().split('.').map(p => parseInt(p, 10));
      const a = (isFinite(parts[0]) ? parts[0] : 0);
      const b = (isFinite(parts[1]) ? parts[1] : 0);
      return [a, b];
    };

    return lastRows
      .filter(r => Number(r.nivel || 1) === 2)
      .filter(r => {
        const ref = String(r.ref || '').trim();
        // apenas familias 1 a 3, nivel 2 (ex: 1.1, 2.3, 3.2), excluir nivel 3 (1.1.1)
        return /^[1-3]\.\d+$/.test(ref);
      })
      .map(r => {
        const ref = String(r.ref || '').trim();
        const nome = String(r.nome || '').trim();
        const parentRef = ref.split('.')[0];
        const parentNome = String(level1NameByRef.get(parentRef) || '').trim();
        const real = Number((r.meses || [])[mIdx] || 0);
        const orc = Number((r.orc_meses || [])[mIdx] || 0);
        return { ref, nome, parentNome, real, orc };
      })
      .filter(x => Math.abs(Number(x.real || 0)) > 0.005 || Math.abs(Number(x.orc || 0)) > 0.005)
      .sort((a, b) => {
        const [a1, a2] = sortKey(a.ref);
        const [b1, b2] = sortKey(b.ref);
        if (a1 !== b1) return a1 - b1;
        return a2 - b2;
      });
  }

  function renderCostsRubricsChart(ano, mes) {
    if (!costsRubricModalEl || typeof Chart === 'undefined') return;
    const canvas = document.getElementById('mapCostsRubricChart');
    if (!canvas) return;

    const items = getCostRubricsForMonth(mes);
    const labels = items.map(x => {
      const left = String(x.ref || '').trim();
      const p = String(x.parentNome || '').trim();
      const n = String(x.nome || '').trim();
      if (p && n) return `${left} ${p} - ${n}`;
      if (n) return `${left} - ${n}`;
      return left;
    });
    const actual = items.map(x => Number(x.real || 0));
    const budget = items.map(x => Number(x.orc || 0));

    const totalActual = actual.reduce((a, v) => a + Number(v || 0), 0);
    const totalBudget = budget.reduce((a, v) => a + Number(v || 0), 0);
    if (costsTotalEl) costsTotalEl.textContent = `Total: ${fmtCur.format(totalActual)}  •  Orçamento: ${fmtCur.format(totalBudget)}`;
    if (costsMonthLabelEl) costsMonthLabelEl.textContent = monthLabel(ano, mes);

    try { chartCostsRubrics?.destroy?.(); } catch (_) {}
    chartCostsRubrics = new Chart(canvas.getContext('2d'), {
      type: 'bar',
      data: {
        labels,
        datasets: [
          {
            label: 'Real',
            data: actual,
            backgroundColor: 'rgba(244, 63, 94, 0.25)',
            borderColor: 'rgba(244, 63, 94, 0.85)',
            borderWidth: 1,
            borderRadius: 6,
            borderSkipped: false
          },
          {
            label: 'Orçamento',
            data: budget,
            backgroundColor: 'rgba(107, 114, 128, 0.18)',
            borderColor: 'rgba(107, 114, 128, 0.75)',
            borderWidth: 1,
            borderRadius: 6,
            borderSkipped: false
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        indexAxis: 'y',
        plugins: {
          legend: { display: true, position: 'bottom' },
          tooltip: {
            callbacks: {
              label: (ctx) => `${ctx.dataset.label}: ${fmtCur.format(Number(ctx.parsed?.x || 0))}`
            }
          }
        },
        scales: {
          x: {
            beginAtZero: true,
            ticks: {
              callback: (v) => {
                try { return fmtNum.format(Number(v || 0)); } catch (_) { return v; }
              }
            },
            grid: { display: true, color: '#e5e7eb' }
          },
          y: {
            grid: { display: false },
            ticks: {
              align: 'start',
              autoSkip: false,
              maxTicksLimit: 50,
              padding: 6
            }
          }
        }
      }
    });
  }

  async function loadSalesAloj(ano, mes) {
    if (!salesAlojModalEl) return;
    if (salesMonthLabelEl) salesMonthLabelEl.textContent = monthLabel(ano, mes);
    if (salesTotalEl) salesTotalEl.textContent = 'Total: --';

    const ccustos = getSelectedCcustos();
    const qs = new URLSearchParams({ ano: String(ano), mes: String(mes) });
    if (ccustos.length) qs.set('ccustos', ccustos.join(','));

    let data;
    try {
      const res = await fetch(`/api/mapa_gestao/vendas_alojamentos?${qs.toString()}`);
      data = await res.json();
      if (!res.ok || data.error) throw new Error(data.error || 'Erro ao obter vendas por alojamento');
    } catch (err) {
      console.error(err);
      if (salesTotalEl) salesTotalEl.textContent = `Erro: ${err.message || err}`;
      return;
    }

    const rows = Array.isArray(data.rows) ? data.rows : [];
    const labels = rows.map(r => String(r.alojamento || '').trim());
    const actual = rows.map(r => Number(r.real || 0));
    const goal = rows.map(r => Number(r.objetivo || 0));
    const totalReal = Number(data.total_real || 0);
    const totalObj = Number(data.total_objetivo || 0);
    if (salesTotalEl) salesTotalEl.textContent = `Total: ${fmtCur.format(totalReal)}  •  Objetivo: ${fmtCur.format(totalObj)}`;

    const canvas = document.getElementById('mapSalesAlojChart');
    if (!canvas || typeof Chart === 'undefined') return;

    // ajustar altura do canvas para muitos alojamentos (barras horizontais)
    const minH = 420;
    const h = Math.max(minH, labels.length * 22 + 120);
    canvas.style.width = '100%';
    canvas.style.height = `${h}px`;
    canvas.height = h;

    try { chartSalesAloj?.destroy?.(); } catch (_) {}
    chartSalesAloj = new Chart(canvas.getContext('2d'), {
      type: 'bar',
      data: {
        labels,
        datasets: [
          {
            label: 'Faturado',
            data: actual,
            backgroundColor: 'rgba(14, 165, 233, 0.35)',
            borderColor: 'rgba(14, 165, 233, 0.85)',
            borderWidth: 1,
            borderRadius: 6,
            borderSkipped: false
          },
          {
            label: 'Objetivo',
            data: goal,
            backgroundColor: 'rgba(124, 58, 237, 0.25)',
            borderColor: 'rgba(124, 58, 237, 0.85)',
            borderWidth: 1,
            borderRadius: 6,
            borderSkipped: false
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        indexAxis: 'y',
        plugins: {
          legend: { display: true, position: 'bottom' },
          tooltip: {
            callbacks: {
              label: (ctx) => `${ctx.dataset.label}: ${fmtCur.format(Number(ctx.parsed?.x || 0))}`
            }
          }
        },
        scales: {
          x: {
            beginAtZero: true,
            ticks: {
              callback: (v) => {
                try { return fmtNum.format(Number(v || 0)); } catch (_) { return v; }
              }
            }
          },
          y: {
            grid: { display: false },
            ticks: {
              align: 'start',
              autoSkip: false,
              padding: 6
            }
          }
        }
      }
    });
  }

  async function loadMarginAloj(ano, mes) {
    if (!marginAlojModalEl) return;
    if (marginMonthLabelEl) marginMonthLabelEl.textContent = monthLabel(ano, mes);
    if (marginTotalEl) marginTotalEl.textContent = 'Total: --';

    const ccustos = getSelectedCcustos();
    const qs = new URLSearchParams({ ano: String(ano), mes: String(mes) });
    if (ccustos.length) qs.set('ccustos', ccustos.join(','));

    let data;
    try {
      const res = await fetch(`/api/mapa_gestao/margem_alojamentos?${qs.toString()}`);
      data = await res.json();
      if (!res.ok || data.error) throw new Error(data.error || 'Erro ao obter margem por alojamento');
    } catch (err) {
      console.error(err);
      if (marginTotalEl) marginTotalEl.textContent = `Erro: ${err.message || err}`;
      return;
    }

    const rows = Array.isArray(data.rows) ? data.rows : [];
    const labels = rows.map(r => String(r.alojamento || '').trim());
    const marginVals = rows.map(r => Number(r.margem || 0));
    const salesVals = rows.map(r => Number(r.vendas || 0));
    const costVals = rows.map(r => Number(r.custos || 0));

    const totalSales = Number(data.total_vendas || 0);
    const totalCosts = Number(data.total_custos || 0);
    const totalMargin = Number(data.total_margem || 0);
    if (marginTotalEl) {
      marginTotalEl.textContent = `Total: ${fmtCur.format(totalMargin)}  •  Vendas: ${fmtCur.format(totalSales)}  •  Custos: ${fmtCur.format(totalCosts)}`;
    }

    const canvas = document.getElementById('mapMarginAlojChart');
    if (!canvas || typeof Chart === 'undefined') return;

    const minH = 420;
    const h = Math.max(minH, labels.length * 22 + 120);
    canvas.style.width = '100%';
    canvas.style.height = `${h}px`;
    canvas.height = h;

    const bg = marginVals.map(v => (Number(v || 0) < 0 ? 'rgba(239, 68, 68, 0.25)' : 'rgba(34, 197, 94, 0.22)'));
    const border = marginVals.map(v => (Number(v || 0) < 0 ? 'rgba(239, 68, 68, 0.85)' : 'rgba(34, 197, 94, 0.85)'));

    try { chartMarginAloj?.destroy?.(); } catch (_) {}
    chartMarginAloj = new Chart(canvas.getContext('2d'), {
      type: 'bar',
      data: {
        labels,
        datasets: [
          {
            label: 'Margem',
            data: marginVals,
            _sales: salesVals,
            _costs: costVals,
            backgroundColor: bg,
            borderColor: border,
            borderWidth: 1,
            borderRadius: 6,
            borderSkipped: false
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        indexAxis: 'y',
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: (ctx) => {
                const idx = Number(ctx.dataIndex || 0);
                const ds = ctx.dataset || {};
                const v = Number(ctx.parsed?.x || 0);
                const s = Array.isArray(ds._sales) ? Number(ds._sales[idx] || 0) : 0;
                const c = Array.isArray(ds._costs) ? Number(ds._costs[idx] || 0) : 0;
                return `Margem: ${fmtCur.format(v)}  •  Vendas: ${fmtCur.format(s)}  •  Custos: ${fmtCur.format(c)}`;
              }
            }
          }
        },
        scales: {
          x: {
            ticks: {
              callback: (v) => {
                try { return fmtNum.format(Number(v || 0)); } catch (_) { return v; }
              }
            },
            grid: {
              color: (ctx) => (Number(ctx.tick?.value) === 0 ? '#94a3b8' : '#e5e7eb'),
              lineWidth: (ctx) => (Number(ctx.tick?.value) === 0 ? 2 : 1)
            }
          },
          y: {
            grid: { display: false },
            ticks: { align: 'start', autoSkip: false, padding: 6 }
          }
        }
      }
    });
  }

  function flagFromPais(pais) {
    const p = String(pais || '').trim();
    if (p.length === 2 && /^[a-zA-Z]{2}$/.test(p)) {
      const code = p.toUpperCase();
      const A = 0x1F1E6;
      const first = code.charCodeAt(0) - 65 + A;
      const second = code.charCodeAt(1) - 65 + A;
      try { return String.fromCodePoint(first, second); } catch (_) { return ''; }
    }
    return '';
  }

  async function loadCountryStats(ano) {
    if (!countryModalEl || !countryBodyEl) return;
    if (countryMonthLabelEl) countryMonthLabelEl.textContent = `Ano ${ano}`;
    countryBodyEl.innerHTML = '<tr><td colspan="8" class="text-center text-muted">A carregar...</td></tr>';
    if (countryTotalEl) countryTotalEl.textContent = 'Total: --';

    const ccustos = getSelectedCcustos();
    const qs = new URLSearchParams({ ano: String(ano) });
    if (ccustos.length) qs.set('ccustos', ccustos.join(','));

    let data;
    try {
      const res = await fetch(`/api/mapa_gestao/reservas_paises?${qs.toString()}`);
      data = await res.json();
      if (!res.ok || data.error) throw new Error(data.error || 'Erro ao obter reservas por país');
    } catch (err) {
      console.error(err);
      countryBodyEl.innerHTML = `<tr><td colspan="6" class="text-center text-danger">${escapeHtml(err.message || String(err))}</td></tr>`;
      return;
    }

    const rows = Array.isArray(data.rows) ? data.rows : [];
    const totalVal = Number(data.total_valor || 0);
    const totalRes = Number(data.total_reservas || 0);
    if (countryTotalEl) countryTotalEl.textContent = `Total: ${fmtCur.format(totalVal)}  •  Reservas: ${fmtNum.format(totalRes)}`;

    countryRowsCache = rows;
    countryTotalValCache = totalVal;
    renderCountryRows();
  }

  function getCountrySortVal(r, key) {
    const k = String(key || '').trim();
    if (k === 'pais') return String(r.pais || '').trim().toUpperCase();
    if (k === 'pct') {
      const v = Number(r.valor || 0);
      return countryTotalValCache ? (v / countryTotalValCache) * 100 : 0;
    }
    const raw = r[k];
    if (raw === null || raw === undefined || raw === '') return 0;
    const n = Number(raw);
    return isFinite(n) ? n : 0;
  }

  function setCountrySortIndicators() {
    document.querySelectorAll('#mapCountryTable thead th.country-sort').forEach(th => {
      const key = th.getAttribute('data-key') || '';
      const ind = th.querySelector('.sort-ind');
      if (!ind) return;
      if (key === countrySort.key) ind.textContent = countrySort.dir === 'asc' ? '▲' : '▼';
      else ind.textContent = '';
    });
  }

  function renderCountryRows() {
    if (!countryBodyEl) return;
    const rows = Array.isArray(countryRowsCache) ? [...countryRowsCache] : [];
    if (!rows.length) {
      countryBodyEl.innerHTML = '<tr><td colspan="8" class="text-center text-muted">Sem dados.</td></tr>';
      setCountrySortIndicators();
      return;
    }

    const dirMul = countrySort.dir === 'asc' ? 1 : -1;
    rows.sort((a, b) => {
      const av = getCountrySortVal(a, countrySort.key);
      const bv = getCountrySortVal(b, countrySort.key);
      if (countrySort.key === 'pais') return String(av).localeCompare(String(bv), 'pt-PT') * dirMul;
      return (Number(av) - Number(bv)) * dirMul;
    });

    countryBodyEl.innerHTML = rows.map(r => {
      const pais = String(r.pais || '').trim() || '(Sem país)';
      const flag = flagFromPais(pais);
      const valor = Number(r.valor || 0);
      const pct = countryTotalValCache ? (valor / countryTotalValCache) * 100 : 0;
      const reservas = Number(r.reservas || 0);
      const mn = Number(r.media_noites || 0);
      const adr = (r.media_noite === null || r.media_noite === undefined) ? null : Number(r.media_noite);
      const mh = Number(r.media_hospedes || 0);
      const ant = Number(r.media_antecip || 0);
      const paisTxt = flag ? `${flag} ${pais}` : pais;
      return `
        <tr>
          <td>${escapeHtml(paisTxt)}</td>
          <td class="text-end">${fmtNum.format(reservas)}</td>
          <td class="text-end">${fmtPct.format(pct)}%</td>
          <td class="text-end">${fmtCur.format(valor)}</td>
          <td class="text-end">${fmtNum2.format(mn)}</td>
          <td class="text-end">${(adr === null || !isFinite(adr)) ? '--' : fmtCur2.format(adr)}</td>
          <td class="text-end">${fmtNum2.format(mh)}</td>
          <td class="text-end">${fmtNum2.format(ant)}</td>
        </tr>
      `;
    }).join('');

    setCountrySortIndicators();
  }

  function shiftMonth(delta) {
    const baseYear = Number(resDailyYear || parseInt(anoInput?.value, 10) || new Date().getFullYear());
    const baseMonth = Number(resDailyMonth || (new Date().getMonth() + 1));
    let y = baseYear;
    let m = baseMonth + Number(delta || 0);
    while (m < 1) { m += 12; y -= 1; }
    while (m > 12) { m -= 12; y += 1; }
    resDailyYear = y;
    resDailyMonth = m;
    loadResDaily();
  }

  document.getElementById('mapKpi6Card')?.addEventListener('click', () => {
    const now = new Date();
    resDailyYear = parseInt(anoInput?.value, 10) || now.getFullYear();
    resDailyMonth = now.getMonth() + 1;
    resDailyModal?.show();
    // esperar a animação do modal para garantir canvas com tamanho
    setTimeout(loadResDaily, 150);
  });
  resPrevBtn?.addEventListener('click', () => shiftMonth(-1));
  resNextBtn?.addEventListener('click', () => shiftMonth(1));

  function shiftAdrMonth(delta) {
    const baseYear = Number(adrDailyYear || parseInt(anoInput?.value, 10) || new Date().getFullYear());
    const baseMonth = Number(adrDailyMonth || (new Date().getMonth() + 1));
    let y = baseYear;
    let m = baseMonth + Number(delta || 0);
    while (m < 1) { m += 12; y -= 1; }
    while (m > 12) { m -= 12; y += 1; }
    adrDailyYear = y;
    adrDailyMonth = m;
    loadAdrDaily();
  }

  document.getElementById('mapKpiAdrCard')?.addEventListener('click', () => {
    const now = new Date();
    adrDailyYear = parseInt(anoInput?.value, 10) || now.getFullYear();
    adrDailyMonth = now.getMonth() + 1;
    adrDailyModal?.show();
    setTimeout(loadAdrDaily, 150);
  });
  adrPrevBtn?.addEventListener('click', () => shiftAdrMonth(-1));
  adrNextBtn?.addEventListener('click', () => shiftAdrMonth(1));

  function shiftCostsMonth(delta) {
    const baseYear = Number(costsRubricsYear || parseInt(anoInput?.value, 10) || new Date().getFullYear());
    const baseMonth = Number(costsRubricsMonth || (new Date().getMonth() + 1));
    let y = baseYear;
    let m = baseMonth + Number(delta || 0);
    while (m < 1) { m += 12; y -= 1; }
    while (m > 12) { m -= 12; y += 1; }
    costsRubricsYear = y;
    costsRubricsMonth = m;
    renderCostsRubricsChart(y, m);
  }

  document.getElementById('mapKpiCostsCard')?.addEventListener('click', () => {
    const now = new Date();
    costsRubricsYear = parseInt(anoInput?.value, 10) || now.getFullYear();
    costsRubricsMonth = now.getMonth() + 1;
    costsRubricModal?.show();
    setTimeout(() => renderCostsRubricsChart(costsRubricsYear, costsRubricsMonth), 150);
  });
  costsPrevBtn?.addEventListener('click', () => shiftCostsMonth(-1));
  costsNextBtn?.addEventListener('click', () => shiftCostsMonth(1));

  function shiftSalesMonth(delta) {
    const baseYear = Number(salesAlojYear || parseInt(anoInput?.value, 10) || new Date().getFullYear());
    const baseMonth = Number(salesAlojMonth || (new Date().getMonth() + 1));
    let y = baseYear;
    let m = baseMonth + Number(delta || 0);
    while (m < 1) { m += 12; y -= 1; }
    while (m > 12) { m -= 12; y += 1; }
    salesAlojYear = y;
    salesAlojMonth = m;
    loadSalesAloj(y, m);
  }

  document.getElementById('mapKpiSalesCard')?.addEventListener('click', () => {
    const now = new Date();
    salesAlojYear = parseInt(anoInput?.value, 10) || now.getFullYear();
    salesAlojMonth = now.getMonth() + 1;
    salesAlojModal?.show();
    setTimeout(() => loadSalesAloj(salesAlojYear, salesAlojMonth), 150);
  });
  salesPrevBtn?.addEventListener('click', () => shiftSalesMonth(-1));
  salesNextBtn?.addEventListener('click', () => shiftSalesMonth(1));

  function shiftMarginMonth(delta) {
    const baseYear = Number(marginAlojYear || parseInt(anoInput?.value, 10) || new Date().getFullYear());
    const baseMonth = Number(marginAlojMonth || (new Date().getMonth() + 1));
    let y = baseYear;
    let m = baseMonth + Number(delta || 0);
    while (m < 1) { m += 12; y -= 1; }
    while (m > 12) { m -= 12; y += 1; }
    marginAlojYear = y;
    marginAlojMonth = m;
    loadMarginAloj(y, m);
  }

  document.getElementById('mapKpiMarginCard')?.addEventListener('click', () => {
    const now = new Date();
    marginAlojYear = parseInt(anoInput?.value, 10) || now.getFullYear();
    marginAlojMonth = now.getMonth() + 1;
    marginAlojModal?.show();
    setTimeout(() => loadMarginAloj(marginAlojYear, marginAlojMonth), 150);
  });
  marginPrevBtn?.addEventListener('click', () => shiftMarginMonth(-1));
  marginNextBtn?.addEventListener('click', () => shiftMarginMonth(1));

  function shiftCountryYear(delta) {
    const baseYear = Number(countryYear || parseInt(anoInput?.value, 10) || new Date().getFullYear());
    const y = baseYear + Number(delta || 0);
    countryYear = y;
    loadCountryStats(y);
  }

  document.getElementById('mapKpiResCard')?.addEventListener('click', () => {
    const now = new Date();
    countryYear = parseInt(anoInput?.value, 10) || now.getFullYear();
    countryModal?.show();
    setTimeout(() => loadCountryStats(countryYear), 150);
  });
  countryPrevBtn?.addEventListener('click', () => shiftCountryYear(-1));
  countryNextBtn?.addEventListener('click', () => shiftCountryYear(1));

  document.querySelectorAll('#mapCountryTable thead th.country-sort').forEach(th => {
    th.addEventListener('click', () => {
      const key = th.getAttribute('data-key') || '';
      if (!key) return;
      if (countrySort.key === key) {
        countrySort.dir = countrySort.dir === 'asc' ? 'desc' : 'asc';
      } else {
        countrySort.key = key;
        countrySort.dir = (key === 'pais') ? 'asc' : 'desc';
      }
      renderCountryRows();
    });
  });

  function getSelectedCcustos() {
    return Array.from(ccSelected);
  }

  function isAllCentersSelected() {
    const selected = getSelectedCcustos();
    if (!ccOptions.length) return true;
    return selected.length === 0 || selected.length === ccOptions.length;
  }

  function updateDiffAvailability() {
    if (!diffEnableEl || !diffPctEl) return;
    const all = isAllCentersSelected();
    if (showBudgetEl?.checked) diffEnableEl.checked = false;
    if (!all) diffEnableEl.checked = false;
    diffEnableEl.disabled = !all || !!showBudgetEl?.checked;
    diffPctEl.disabled = !all || !diffEnableEl.checked || !!showBudgetEl?.checked;
    const title = all ? '' : 'Disponível apenas com Todos os centros selecionados';
    diffEnableEl.title = title;
    diffPctEl.title = title;
  }

  function updateBudgetAvailability() {
    if (!showBudgetEl) return;
    const all = isAllCentersSelected();
    if (!all) showBudgetEl.checked = false;
    showBudgetEl.disabled = !all;
    showBudgetEl.title = all ? '' : 'Disponível apenas com Todos os centros selecionados';
    if (showBudgetEl.checked && diffEnableEl) diffEnableEl.checked = false;
    updateDiffAvailability();
  }

  function setLoading(message) {
    if (!tbody) return;
    tbody.innerHTML = `<tr><td colspan="15" class="text-center text-muted">${escapeHtml(message)}</td></tr>`;
  }

  function renderCcList() {
    if (!ccList) return;
    ccList.innerHTML = ccOptions.map((cc) => {
      const checked = ccSelected.has(cc.ccusto) ? 'checked' : '';
      const tipoNorm = (cc.tipo || '').trim().toUpperCase();
      let badge = '<span class="badge bg-secondary-subtle text-secondary ms-auto">Estrutura</span>';
      if (tipoNorm === 'EXPLORACAO') badge = '<span class="badge bg-info-subtle text-info ms-auto">Exploração</span>';
      else if (tipoNorm === 'GESTAO') badge = '<span class="badge bg-success-subtle text-success ms-auto">Gestão</span>';
      return `
        <label class="list-group-item d-flex align-items-center gap-2">
          <input class="form-check-input" type="checkbox" value="${cc.ccusto}" ${checked}>
          <span>${cc.ccusto}</span>
          ${badge}
        </label>
      `;
    }).join('') || '<div class="text-muted">Sem centros de custo.</div>';
    updateCcSummary();
  }

  function updateCcSummary() {
    const total = ccOptions.length;
    const sel = ccSelected.size;
    const label = !sel || sel === total ? 'Todos os centros' : `${sel} selecionado(s)`;
    if (ccLabel) ccLabel.textContent = label;
    if (ccCount) ccCount.textContent = `${sel || total} selecionados${sel ? '' : ' (todos)'}`;
    updateBudgetAvailability();
  }

  async function loadCcustos() {
    setLoading('A carregar...');
    try {
      const res = await fetch('/api/mapa_gestao/ccustos');
      const data = await res.json();
      const optsRaw = Array.isArray(data.options)
        ? data.options
        : (data.options ? Object.values(data.options) : []);
      ccOptions = optsRaw.map(o => {
        if (typeof o === 'string') return { ccusto: o, tipo: '' };
        if (o && typeof o === 'object') {
          return { ccusto: o.ccusto || o.CCUSTO || o.Ccusto || '', tipo: o.tipo || o.TIPO || o.Tipo || '' };
        }
        return { ccusto: '', tipo: '' };
      }).filter(o => o.ccusto);

      // garantir unicidade (vistas/joins podem devolver duplicados)
      const byCc = new Map();
      ccOptions.forEach(o => {
        const k = String(o.ccusto || '').trim();
        if (!k) return;
        if (!byCc.has(k)) byCc.set(k, { ccusto: k, tipo: o.tipo || '' });
      });
      ccOptions = Array.from(byCc.values());

      ccSelected = new Set(ccOptions.map(o => o.ccusto)); // default = todos
      renderCcList();
      updateBudgetAvailability();
    } catch (err) {
      console.error(err);
      ccOptions = [];
      ccSelected = new Set();
      if (ccList) ccList.innerHTML = '<div class="text-danger">Erro ao carregar centros de custo.</div>';
      setLoading('Erro ao carregar centros de custo');
      updateBudgetAvailability();
    }
  }

  async function loadMapa() {
    setLoading('A carregar...');
    const ano = parseInt(anoInput?.value, 10) || defaultYear;
    const ccustos = getSelectedCcustos();
    const qs = new URLSearchParams({ ano: String(ano) });
    if (ccustos.length) qs.set('ccustos', ccustos.join(','));

    try {
      const res = await fetch(`/api/mapa_gestao?${qs.toString()}`);
      const data = await res.json();
      if (!res.ok || data.error) {
        throw new Error(data.error || 'Erro ao carregar o mapa');
      }
      const fams = Array.isArray(data.familias) ? data.familias : [];
      const normalized = fams.map(r => {
        const meses = Array.isArray(r.meses) ? r.meses.slice(0, 12) : [];
        while (meses.length < 12) meses.push(0);
        const orc_meses = Array.isArray(r.orc_meses) ? r.orc_meses.slice(0, 12) : [];
        while (orc_meses.length < 12) orc_meses.push(0);
        return { ...r, meses, orc_meses };
      });
      lastKpis = (data && typeof data === 'object' && data.kpis && typeof data.kpis === 'object') ? data.kpis : {};
      lastRows = normalized;
      levelOneRefs = lastRows.filter(r => Number(r.nivel || 1) === 1).map(r => String(r.ref || '').trim());
      allRefs = lastRows.map(r => String(r.ref || '').trim());
      treeExpanded = new Set(); // por defeito: apenas nivel 1 visivel; restantes fechados
      updateBudgetAvailability();
      renderTabela();
      if (currentView === 'charts') renderCharts();
    } catch (err) {
      console.error(err);
      setLoading(err.message || 'Erro ao carregar dados');
      if (totalLbl) totalLbl.textContent = '--';
      if (filtrosLbl) filtrosLbl.textContent = '';
    }
  }

  function renderTabela() {
    if (!tbody) return;
    if (!lastRows.length) {
      tbody.innerHTML = '<tr><td colspan="15" class="text-center text-muted">Sem dados para os filtros.</td></tr>';
      return;
    }

    // map ref->hasChildren
    const hasChild = {};
    lastRows.forEach(r => {
      const ref = String(r.ref || '');
      const parts = ref.split('.');
      if (parts.length > 1) {
        const parent = parts.slice(0, -1).join('.');
        hasChild[parent] = true;
      }
    });

    const isVisible = (ref) => {
      const parts = String(ref || '').split('.');
      if (parts.length === 1) return true;
      for (let i = 1; i < parts.length; i++) {
        const ancestor = parts.slice(0, i).join('.');
        if (!treeExpanded.has(ancestor)) return false;
      }
      return true;
    };

    const showBudget = !!showBudgetEl?.checked;
    const baseForPctCosts = lastRows
      .filter(r => Number(r.nivel || 1) === 1 && !String(r.ref || '').trim().startsWith('9'))
      .reduce((acc, r) => acc + Number((showBudget ? r.orc_total : r.total) || 0), 0);

    const rowsHtml = lastRows
      .filter(r => isVisible(r.ref))
      .map(r => {
        const nivel = Number(r.nivel || 1);
        const ref = String(r.ref || '');
        const isProveito = ref.trim().startsWith('9');
        const diffEnabled = !showBudget && isAllCentersSelected() && !!diffEnableEl?.checked;
        const diffPct = Math.abs(Number(diffPctEl?.value || 3) || 3);
        const displayArr = showBudget ? (r.orc_meses || []) : (r.meses || []);
        const displayTotal = Number((showBudget ? r.orc_total : r.total) || 0);
        let percVal = '';
        if (!isProveito) {
          if (showBudget) {
            percVal = baseForPctCosts > 0 ? `${fmtPct.format((displayTotal / baseForPctCosts) * 100)}%` : '';
          } else {
            percVal = (r.percent === '' || r.percent == null) ? '' : `${fmtPct.format(Number(r.percent || 0))}%`;
          }
        }
        const mesesHtml = (displayArr || []).map((v, idx) => {
          const mesNum = idx + 1;
          let diffClass = '';
          if (diffEnabled) {
            const bArr = Array.isArray(r.orc_meses) ? r.orc_meses : null;
            const budget = bArr ? Number(bArr[idx] || 0) : 0;
            const actual = Number(v || 0);
            if (budget > 0) {
              const pct = ((actual - budget) / budget) * 100;
              // Custos: acima orçamento = vermelho; abaixo = verde
              // Proveitos: abaixo objetivo = vermelho; acima = verde (inverso)
              if (!isProveito) {
                if (pct >= diffPct) diffClass = ' diff-over';
                else if (pct <= -diffPct) diffClass = ' diff-under';
              } else {
                if (pct >= diffPct) diffClass = ' diff-under';
                else if (pct <= -diffPct) diffClass = ' diff-over';
              }
            }
          }
          if (showBudget) {
            return `<td class="text-end${diffClass}">${fmtNum.format(Number(v || 0))}</td>`;
          }
          return `<td class="text-end cell-drill${diffClass}" data-level="${nivel}" data-ref="${attrEscape(ref)}" data-nome="${attrEscape(r.nome || '')}" data-mes="${mesNum}">${fmtNum.format(Number(v || 0))}</td>`;
        }).join('');
        let toggle = '<span class="toggle-spacer"></span>';
        if (nivel <= 2 && hasChild[ref]) {
          const isOpen = treeExpanded.has(ref);
          const icon = isOpen ? 'fa-minus' : 'fa-plus';
          toggle = `<button class="toggle-node" data-ref="${ref}" title="${isOpen ? 'Colapsar' : 'Expandir'}" aria-label="${isOpen ? 'Colapsar' : 'Expandir'}"><i class="fa-solid ${icon}"></i></button>`;
        }
        const rowClass = `mapa-row level-${nivel}${isProveito ? ' row-proveito' : ''}`;
        let totalDiffClass = '';
        if (diffEnabled) {
          const budgetTotal = Number(r.orc_total || 0);
          const actualTotal = Number(r.total || 0);
          if (budgetTotal > 0) {
            const pct = ((actualTotal - budgetTotal) / budgetTotal) * 100;
            if (!isProveito) {
              if (pct >= diffPct) totalDiffClass = ' diff-over';
              else if (pct <= -diffPct) totalDiffClass = ' diff-under';
            } else {
              if (pct >= diffPct) totalDiffClass = ' diff-under';
              else if (pct <= -diffPct) totalDiffClass = ' diff-over';
            }
          }
        }
        const totalCell = showBudget
          ? `<td class="text-end fw-semibold${totalDiffClass}">${fmtNum.format(displayTotal)}</td>`
          : `<td class="text-end fw-semibold cell-drill${totalDiffClass}" data-level="${nivel}" data-ref="${attrEscape(ref)}" data-nome="${attrEscape(r.nome || '')}" data-mes="all">${fmtNum.format(Number(r.total || 0))}</td>`;
        return `
          <tr class="${rowClass}" data-level="${nivel}">
            <td class="fam-cell level-${nivel} d-flex align-items-center gap-1">${toggle}<span>${escapeHtml(ref)} - ${escapeHtml(r.nome || '')}</span></td>
            ${mesesHtml}
            ${totalCell}
            <td class="text-end text-muted">${percVal}</td>
          </tr>
        `;
      }).join('');

    // Totais (apenas nivel 1 para evitar duplicar somas dos pais/filhos)
    const custoMeses = Array(12).fill(0);
    const provMeses = Array(12).fill(0);
    let totalCustos = 0;
    let totalProv = 0;
    lastRows.filter(r => Number(r.nivel || 1) === 1).forEach(r => {
      const ref = String(r.ref || '').trim();
      const isProv = ref.startsWith('9');
      const arr = showBudget ? (r.orc_meses || []) : (r.meses || []);
      (arr || []).forEach((v, idx) => {
        if (isProv) provMeses[idx] += Number(v || 0);
        else custoMeses[idx] += Number(v || 0);
      });
      if (isProv) totalProv += Number((showBudget ? r.orc_total : r.total) || 0);
      else totalCustos += Number((showBudget ? r.orc_total : r.total) || 0);
    });
    const saldoMeses = custoMeses.map((c, i) => provMeses[i] - c);
    const totalSaldo = totalProv - totalCustos;
    let runSaldo = 0;
    const acumuladoMeses = saldoMeses.map(v => {
      runSaldo += Number(v || 0);
      return runSaldo;
    });
    const rowResumo = (label, arr, total, extraClass='') => `
      <tr class="mapa-row total-row ${extraClass}">
        <td class="fam-cell level-1 d-flex align-items-center gap-1"><span class="fw-semibold">${label}</span></td>
        ${arr.map(v => `<td class="text-end fw-semibold">${fmtNum.format(v)}</td>`).join('')}
        <td class="text-end fw-semibold">${fmtNum.format(total)}</td>
        <td class="text-end text-muted fw-semibold"></td>
      </tr>
    `;
    const totalRowHtml = [
      rowResumo('Custos', custoMeses, totalCustos, 'total-custos'),
      rowResumo('Proveitos', provMeses, totalProv, 'total-proveitos'),
      rowResumo('Saldo', saldoMeses, totalSaldo, 'total-saldo'),
      rowResumo('Acumulado', acumuladoMeses, runSaldo, 'total-acumulado')
    ].join('');

    tbody.innerHTML = rowsHtml
      ? rowsHtml + totalRowHtml
      : '<tr><td colspan="15" class="text-center text-muted">Sem dados visíveis.</td></tr>';

    tbody.querySelectorAll('.toggle-node').forEach(btn => {
      btn.addEventListener('click', () => {
        const ref = btn.dataset.ref;
        if (!ref) return;
        if (treeExpanded.has(ref)) treeExpanded.delete(ref); else treeExpanded.add(ref);
        renderTabela();
      });
    });
    tbody.querySelectorAll('.cell-drill').forEach(td => {
      td.addEventListener('click', () => {
        const ref = td.dataset.ref || '';
        const nome = td.dataset.nome || '';
        const mes = td.dataset.mes || '';
        const level = Number(td.dataset.level || '1');
        openDetalhe(ref, mes, nome, level);
      });
    });
  }

  function resolveDescendants(ref) {
    const prefix = ref ? ref + '.' : '';
    return lastRows
      .map(r => String(r.ref || ''))
      .filter(r => r.startsWith(prefix));
  }

  async function openDetalhe(ref, mes, nome, level) {
    if (!detailBody || !detailModal) return;
    const ano = parseInt(anoInput?.value, 10) || defaultYear;
    const ccustos = getSelectedCcustos();
    const qs = new URLSearchParams({ ano: String(ano), familia: ref });
    if (mes && mes !== 'all') qs.set('mes', mes);
    if (ccustos.length) qs.set('ccustos', ccustos.join(','));
    if (level <= 2) qs.set('include_children', '1');

    detailBody.innerHTML = `<tr><td colspan="11" class="text-center text-muted">A carregar...</td></tr>`;
    const mesLabel = mes && mes !== 'all' ? `(${monthNames[(Number(mes) - 1) || 0] || ''})` : '';
    if (detailTitle) detailTitle.textContent = `Detalhe ${ref} ${nome ? '- ' + nome : ''} ${mesLabel}`.trim();
    if (detailTotal) detailTotal.textContent = 'Total: --';
    detailModal.show();

    try {
      const res = await fetch(`/api/mapa_gestao/detalhe?${qs.toString()}`);
      const data = await res.json();
      if (!res.ok || data.error) throw new Error(data.error || 'Erro ao carregar detalhe');
      const rows = Array.isArray(data.rows) ? data.rows : [];
      if (!rows.length) {
        detailBody.innerHTML = '<tr><td colspan="11" class="text-center text-muted">Sem registos.</td></tr>';
      } else {
        detailBody.innerHTML = rows.map(r => {
          const url = r.anexo_url || '';
          const btn = url ? `<a class="btn btn-outline-primary btn-sm" target="_blank" href="${escapeHtml(url)}">Abrir</a>` : '';
          return `
          <tr>
            <td>${escapeHtml(r.documento || '')}</td>
            <td>${escapeHtml(r.numero || '')}</td>
            <td>${escapeHtml(r.data || '')}</td>
            <td>${escapeHtml(r.nome || '')}</td>
            <td>${escapeHtml(r.ccusto || '')}</td>
            <td>${escapeHtml(r.referencia || '')}</td>
            <td>${escapeHtml(r.designacao || '')}</td>
            <td class="text-end">${fmtNum2.format(Number(r.quantidade || 0))}</td>
            <td class="text-end">${fmtNum2.format(Number(r.preco || 0))}</td>
            <td class="text-end fw-semibold">${fmtNum2.format(Number(r.total || 0))}</td>
            <td class="text-center">${btn}</td>
          </tr>
        `;
        }).join('');
      }
      if (detailTotal) {
        const total = Number(data.total || 0);
        const orc = Number(data.orc_total || 0);
        const desvio = Number(data.desvio || 0);
        const pct = data.desvio_pct == null ? null : Number(data.desvio_pct || 0);
        if (orc > 0) {
          const isProveito = String(ref || '').trim().startsWith('9');
          const cls = !isProveito
            ? (desvio > 0 ? 'text-danger' : (desvio < 0 ? 'text-success' : 'text-muted'))
            : (desvio > 0 ? 'text-success' : (desvio < 0 ? 'text-danger' : 'text-muted'));
          const pctTxt = pct == null ? '' : ` (${fmtPct.format(pct)}%)`;
          detailTotal.innerHTML = `
            <span class="fw-bold">Total: ${fmtNum2.format(total)}</span>
            <span class="text-muted small ms-2">Orçamento: ${fmtNum2.format(orc)}</span>
            <span class="text-muted small ms-2">Desvio: <span class="${cls} opacity-75">${fmtNum2.format(desvio)}${pctTxt}</span></span>
          `.trim();
        } else {
          detailTotal.innerHTML = `<span class="fw-bold">Total: ${fmtNum2.format(total)}</span>`;
        }
      }
    } catch (err) {
      console.error(err);
      detailBody.innerHTML = `<tr><td colspan="10" class="text-center text-danger">${escapeHtml(err.message || 'Erro ao carregar detalhe')}</td></tr>`;
      if (detailTotal) detailTotal.textContent = 'Total: --';
    }
  }

  if (btnAplicar) btnAplicar.addEventListener('click', loadMapa);
  diffEnableEl?.addEventListener('change', () => {
    updateDiffAvailability();
    renderTabela();
  });
  diffPctEl?.addEventListener('change', () => {
    localStorage.setItem('mapDiffPct', diffPctEl.value || '3');
    renderTabela();
  });
  diffPctEl?.addEventListener('input', () => {
    // live update, but avoid spamming storage
    renderTabela();
  });
  showBudgetEl?.addEventListener('change', () => {
    updateBudgetAvailability();
    renderTabela();
  });
  if (btnLimpar) btnLimpar.addEventListener('click', () => {
    ccSelected = new Set(ccOptions.map(o => o.ccusto)); // todos
    if (anoInput) anoInput.value = defaultYear;
    updateCcSummary();
    renderCcList();
    loadMapa();
  });

  if (btnCcusto && modalCcusto) btnCcusto.addEventListener('click', () => modalCcusto.show());
  if (btnCcAll) btnCcAll.addEventListener('click', () => {
    ccSelected = new Set(ccOptions.map(o => o.ccusto));
    renderCcList();
  });
  if (btnCcNone) btnCcNone.addEventListener('click', () => {
    ccSelected = new Set();
    renderCcList();
  });
  if (btnCcApply && modalCcusto) btnCcApply.addEventListener('click', () => {
    if (ccList) {
      ccSelected = new Set(
        Array.from(ccList.querySelectorAll('input[type="checkbox"]:checked')).map(i => i.value)
      );
    }
    updateCcSummary();
    modalCcusto.hide();
    loadMapa();
  });
  if (btnCcEstrutura) btnCcEstrutura.addEventListener('click', () => {
    const filtered = ccOptions.filter(o => !(o.tipo || '').trim());
    ccSelected = new Set(filtered.map(o => o.ccusto));
    renderCcList();
  });
  if (btnCcExploracao) btnCcExploracao.addEventListener('click', () => {
    const filtered = ccOptions.filter(o => (o.tipo || '').trim().toUpperCase() === 'EXPLORACAO');
    ccSelected = new Set(filtered.map(o => o.ccusto));
    renderCcList();
  });
  if (btnCcGestao) btnCcGestao.addEventListener('click', () => {
    const filtered = ccOptions.filter(o => (o.tipo || '').trim().toUpperCase() === 'GESTAO');
    ccSelected = new Set(filtered.map(o => o.ccusto));
    renderCcList();
  });
  if (btnExpandAll) btnExpandAll.addEventListener('click', () => {
    treeExpanded = new Set(allRefs);
    renderTabela();
  });
  if (btnCollapseAll) btnCollapseAll.addEventListener('click', () => {
    treeExpanded = new Set(); // apenas nivel 1 visivel
    renderTabela();
  });

  btnViewTable?.addEventListener('click', () => setView('table'));
  btnViewCharts?.addEventListener('click', () => setView('charts'));
  setView('table');

  loadCcustos().then(loadMapa).catch(err => console.error(err));
});
