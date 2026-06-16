(function () {
  const state = {
    data: null,
    loading: false,
  };

  const els = {
    alojamento: document.getElementById("revparAlojamento"),
    tipo: document.getElementById("revparTipo"),
    ano: document.getElementById("revparAno"),
    refresh: document.getElementById("revparRefresh"),
    head: document.getElementById("revparHead"),
    body: document.getElementById("revparBody"),
    foot: document.getElementById("revparFoot"),
    kpiCurrent: document.getElementById("revparKpiCurrent"),
    kpiPrevious: document.getElementById("revparKpiPrevious"),
    kpiDelta: document.getElementById("revparKpiDelta"),
    kpiCurrentLabel: document.getElementById("revparKpiCurrentLabel"),
    kpiPreviousLabel: document.getElementById("revparKpiPreviousLabel"),
  };

  const moneyFormatter = new Intl.NumberFormat("pt-PT", {
    style: "currency",
    currency: "EUR",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });

  const percentFormatter = new Intl.NumberFormat("pt-PT", {
    minimumFractionDigits: 1,
    maximumFractionDigits: 1,
  });

  function esc(value) {
    return String(value ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function formatMoney(value) {
    return moneyFormatter.format(Number(value || 0));
  }

  function formatPercent(value) {
    if (value === null || value === undefined || Number.isNaN(Number(value))) {
      return "--";
    }
    return `${percentFormatter.format(Number(value))}%`;
  }

  function deltaClass(value) {
    if (value === null || value === undefined || Number.isNaN(Number(value))) {
      return "is-empty";
    }
    if (Number(value) < -0.05) return "is-negative";
    if (Number(value) > 0.05) return "is-positive";
    return "is-empty";
  }

  function deltaHtml(value) {
    return `<span class="sz_revpar_delta ${deltaClass(value)}">${formatPercent(value)}</span>`;
  }

  function activeColspan(data) {
    const months = data?.months?.length || state.data?.months?.length || 12;
    return 5 + months * 3;
  }

  function currentFilters() {
    return {
      alojamento: els.alojamento?.value || "",
      tipo: els.tipo?.value || "Todos",
      ano: els.ano?.value || new Date().getFullYear(),
    };
  }

  function setLoading(message) {
    state.loading = true;
    if (els.refresh) {
      els.refresh.disabled = true;
      els.refresh.classList.add("is-loading");
    }
    els.body.innerHTML = `
      <tr class="sz_table_row">
        <td class="sz_table_cell sz_text_muted text-center" colspan="${activeColspan()}">${esc(message || "A carregar...")}</td>
      </tr>
    `;
    els.foot.innerHTML = "";
  }

  function clearLoading() {
    state.loading = false;
    if (els.refresh) {
      els.refresh.disabled = false;
      els.refresh.classList.remove("is-loading");
    }
  }

  function renderAlojamentoOptions(alojamentos, selected) {
    if (!els.alojamento) return;
    const keep = selected || els.alojamento.value || els.alojamento.dataset.initial || "";
    const options = ['<option value="">Todos</option>'];
    (alojamentos || []).forEach((item) => {
      const nome = item.nome || "";
      const isSelected = nome === keep ? "selected" : "";
      options.push(`<option value="${esc(nome)}" ${isSelected}>${esc(nome)}</option>`);
    });
    els.alojamento.innerHTML = options.join("");
  }

  function renderHead(data) {
    const year = data.ano;
    const previousYear = data.ano_anterior;
    const currentTotalLabel = data.is_ytd ? `YTD ${year}` : `Total ${year}`;
    const previousTotalLabel = data.is_ytd ? `YTD ${previousYear}` : `Total ${previousYear}`;
    const fixed = `
      <th class="sz_table_cell sz_revpar_col-name">Alojamento</th>
      <th class="sz_table_cell sz_revpar_col-type">Tipo</th>
      <th class="sz_table_cell sz_revpar_col-money text-end">${currentTotalLabel}</th>
      <th class="sz_table_cell sz_revpar_col-money text-end">${previousTotalLabel}</th>
      <th class="sz_table_cell sz_revpar_col-delta text-end">Δ %</th>
    `;
    const months = data.months
      .map((month) => `
        <th class="sz_table_cell sz_revpar_col-money text-end">${esc(month.short)} ${year}</th>
        <th class="sz_table_cell sz_revpar_col-money text-end">${esc(month.short)} ${previousYear}</th>
        <th class="sz_table_cell sz_revpar_col-delta text-end">Δ ${esc(month.short)} %</th>
      `)
      .join("");
    els.head.innerHTML = `<tr>${fixed}${months}</tr>`;
    const table = els.head.closest("table");
    if (table) {
      const minWidth = 540 + (data.months?.length || 12) * 306;
      table.style.minWidth = `${Math.max(1500, minWidth)}px`;
    }
  }

  function renderRow(row) {
    const months = (row.months || [])
      .map((month) => `
        <td class="sz_table_cell text-end" title="Receita: ${esc(formatMoney(month.current_revenue))} | Noites disp.: ${esc(month.current_available)}">${formatMoney(month.current)}</td>
        <td class="sz_table_cell text-end" title="Receita: ${esc(formatMoney(month.previous_revenue))} | Noites disp.: ${esc(month.previous_available)}">${formatMoney(month.previous)}</td>
        <td class="sz_table_cell text-end">${deltaHtml(month.delta_pct)}</td>
      `)
      .join("");

    return `
      <tr class="sz_table_row">
        <td class="sz_table_cell sz_revpar_col-name"><strong>${esc(row.alojamento)}</strong></td>
        <td class="sz_table_cell sz_revpar_col-type"><span class="sz_revpar_type_badge">${esc(row.tipo || "-")}</span></td>
        <td class="sz_table_cell text-end" title="Receita: ${esc(formatMoney(row.current_revenue_total))} | Noites disp.: ${esc(row.current_available_total)}"><strong>${formatMoney(row.current_total)}</strong></td>
        <td class="sz_table_cell text-end" title="Receita: ${esc(formatMoney(row.previous_revenue_total))} | Noites disp.: ${esc(row.previous_available_total)}"><strong>${formatMoney(row.previous_total)}</strong></td>
        <td class="sz_table_cell text-end">${deltaHtml(row.delta_total_pct)}</td>
        ${months}
      </tr>
    `;
  }

  function renderFoot(data) {
    const totals = data.totals || {};
    const monthCells = (totals.months || [])
      .map((month) => `
        <td class="sz_table_cell text-end" title="Receita: ${esc(formatMoney(month.current_revenue))} | Noites disp.: ${esc(month.current_available)}">${formatMoney(month.current)}</td>
        <td class="sz_table_cell text-end" title="Receita: ${esc(formatMoney(month.previous_revenue))} | Noites disp.: ${esc(month.previous_available)}">${formatMoney(month.previous)}</td>
        <td class="sz_table_cell text-end">${deltaHtml(month.delta_pct)}</td>
      `)
      .join("");

    els.foot.innerHTML = `
      <tr class="sz_table_row">
        <th class="sz_table_cell sz_revpar_col-name">Total</th>
        <td class="sz_table_cell sz_revpar_col-type">${esc((data.rows || []).length)} aloj.</td>
        <td class="sz_table_cell text-end" title="Receita: ${esc(formatMoney(totals.current_revenue))} | Noites disp.: ${esc(totals.current_available)}">${formatMoney(totals.current_revpar)}</td>
        <td class="sz_table_cell text-end" title="Receita: ${esc(formatMoney(totals.previous_revenue))} | Noites disp.: ${esc(totals.previous_available)}">${formatMoney(totals.previous_revpar)}</td>
        <td class="sz_table_cell text-end">${deltaHtml(totals.delta_pct)}</td>
        ${monthCells}
      </tr>
    `;
  }

  function renderKpis(data) {
    const totals = data.totals || {};
    const suffix = data.is_ytd ? " YTD" : "";
    if (els.kpiCurrentLabel) els.kpiCurrentLabel.textContent = `RevPAR ${data.ano}${suffix}`;
    if (els.kpiPreviousLabel) els.kpiPreviousLabel.textContent = `RevPAR ${data.ano_anterior}${suffix}`;
    if (els.kpiCurrent) els.kpiCurrent.textContent = formatMoney(totals.current_revpar);
    if (els.kpiPrevious) els.kpiPrevious.textContent = formatMoney(totals.previous_revpar);
    if (els.kpiDelta) {
      els.kpiDelta.textContent = formatPercent(totals.delta_pct);
      els.kpiDelta.classList.remove("is-positive", "is-negative", "is-empty");
      els.kpiDelta.classList.add(deltaClass(totals.delta_pct));
    }
  }

  function render(data) {
    state.data = data;
    renderAlojamentoOptions(data.alojamentos || [], data.filters?.alojamento || "");
    renderHead(data);
    renderKpis(data);

    if (!data.rows || !data.rows.length) {
      els.body.innerHTML = `
        <tr class="sz_table_row">
          <td class="sz_table_cell sz_text_muted text-center" colspan="${activeColspan(data)}">Sem alojamentos para os filtros selecionados.</td>
        </tr>
      `;
      els.foot.innerHTML = "";
      return;
    }

    els.body.innerHTML = data.rows.map(renderRow).join("");
    renderFoot(data);
  }

  function syncUrl(filters) {
    const url = new URL(window.location.href);
    url.searchParams.set("ano", filters.ano);
    url.searchParams.set("tipo", filters.tipo);
    if (filters.alojamento) {
      url.searchParams.set("alojamento", filters.alojamento);
    } else {
      url.searchParams.delete("alojamento");
    }
    window.history.replaceState({}, "", url.toString());
  }

  async function loadData() {
    if (state.loading) return;
    const filters = currentFilters();
    setLoading("A calcular RevPAR...");
    syncUrl(filters);

    const params = new URLSearchParams(filters);
    try {
      const response = await fetch(`/api/analytics/revpar?${params.toString()}`, {
        headers: { Accept: "application/json" },
      });
      const payload = await response.json();
      if (!response.ok || !payload.ok) {
        throw new Error(payload.error || "Nao foi possivel carregar os dados.");
      }
      render(payload.data);
    } catch (error) {
      els.body.innerHTML = `
        <tr class="sz_table_row">
          <td class="sz_table_cell text-center" colspan="${activeColspan()}">
            <span class="sz_revpar_delta is-negative">${esc(error.message || "Erro ao carregar dados.")}</span>
          </td>
        </tr>
      `;
      els.foot.innerHTML = "";
    } finally {
      clearLoading();
    }
  }

  function initFromUrl() {
    const params = new URLSearchParams(window.location.search);
    if (els.ano && params.get("ano")) els.ano.value = params.get("ano");
    if (els.tipo && params.get("tipo")) els.tipo.value = params.get("tipo");
    if (els.alojamento && params.get("alojamento")) {
      els.alojamento.dataset.initial = params.get("alojamento");
    }
  }

  function bindEvents() {
    els.refresh?.addEventListener("click", loadData);
    els.tipo?.addEventListener("change", () => {
      if (els.alojamento) els.alojamento.value = "";
      loadData();
    });
    els.ano?.addEventListener("change", loadData);
    els.alojamento?.addEventListener("change", loadData);
  }

  document.addEventListener("DOMContentLoaded", () => {
    initFromUrl();
    bindEvents();
    loadData();
  });
})();
