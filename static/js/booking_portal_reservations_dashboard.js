(function () {
  "use strict";

  const root = document.getElementById("pbReservationsDashboard");
  if (!root) return;

  const $ = (selector, scope) => (scope || root).querySelector(selector);
  const numberFormat = new Intl.NumberFormat("pt-PT");
  const moneyFormat = new Intl.NumberFormat("pt-PT", { style: "currency", currency: "EUR" });
  const dateFormat = new Intl.DateTimeFormat("pt-PT", { day: "2-digit", month: "short", year: "numeric" });
  const dateTimeFormat = new Intl.DateTimeFormat("pt-PT", { day: "2-digit", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" });
  let requestController = null;
  let chart = null;
  let currentPage = 1;

  function create(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  }

  function formatNumber(value) {
    return value === null || value === undefined ? "—" : numberFormat.format(Number(value) || 0);
  }

  function formatMoney(value) {
    return value === null || value === undefined ? "—" : moneyFormat.format(Number(value) || 0);
  }

  function formatDate(value, withTime) {
    if (!value) return "—";
    const parsed = new Date(value);
    if (Number.isNaN(parsed.getTime())) return "—";
    return (withTime ? dateTimeFormat : dateFormat).format(parsed);
  }

  function setStatus(message, isError) {
    const node = $("#pbReservationsStatusMessage");
    node.textContent = message || "";
    node.classList.toggle("is-visible", Boolean(message));
    node.classList.toggle("is-error", Boolean(isError));
  }

  function appendCell(row, text, className) {
    const cell = create("td", className, text);
    row.appendChild(cell);
    return cell;
  }

  function appendMainAndSub(cell, main, sub) {
    cell.textContent = "";
    cell.appendChild(create("strong", "pb-cell-main", main || "—"));
    if (sub) cell.appendChild(create("small", "pb-cell-sub", sub));
  }

  function renderKpis(kpis) {
    root.querySelectorAll("[data-kpi]").forEach((node) => {
      node.textContent = formatNumber(kpis[node.dataset.kpi]);
    });
    root.querySelectorAll("[data-money-kpi]").forEach((node) => {
      node.textContent = formatMoney(kpis[node.dataset.moneyKpi]);
    });
    $("[data-money-note='test_revenue']").textContent = `${formatMoney(kpis.test_revenue)} em testes`;
    $("[data-money-note='average_ticket']").textContent = `${formatMoney(kpis.average_ticket)} por reserva LIVE`;
  }

  function renderOptions(options) {
    const select = $("#pbReservationsProperty");
    const selected = select.value || root.dataset.initialProperty || "";
    select.replaceChildren(new Option("Todos os alojamentos", ""));
    (options.properties || []).forEach((item) => select.appendChild(new Option(item.name, item.id)));
    if ([...select.options].some((item) => item.value === selected)) select.value = selected;
    root.dataset.initialProperty = "";
  }

  function renderStatusBreakdown(items) {
    const host = $("#pbReservationStatusBreakdown");
    host.replaceChildren();
    if (!items.length) {
      host.appendChild(create("span", "pb-empty-inline", "Sem pedidos para os filtros escolhidos."));
      return;
    }
    items.forEach((item) => {
      const chip = create("span", `pb-reservation-state is-${item.key}`);
      chip.appendChild(create("strong", "", formatNumber(item.value)));
      chip.appendChild(document.createTextNode(item.label));
      host.appendChild(chip);
    });
  }

  function renderTimeline(items) {
    const canvas = $("#pbReservationsTimeline");
    if (!window.Chart) {
      canvas.hidden = true;
      return;
    }
    if (chart) chart.destroy();
    const styles = getComputedStyle(root);
    chart = new window.Chart(canvas, {
      type: "bar",
      data: {
        labels: items.map((item) => formatDate(`${item.date}T12:00:00`, false)),
        datasets: [
          { label: "Pedidos", data: items.map((item) => item.requests), backgroundColor: "rgba(47,93,168,.72)", borderRadius: 5 },
          { label: "Pagas", data: items.map((item) => item.paid), backgroundColor: "rgba(24,141,86,.78)", borderRadius: 5 }
        ]
      },
      options: {
        maintainAspectRatio: false,
        responsive: true,
        plugins: { legend: { display: false }, tooltip: { padding: 10 } },
        scales: {
          x: { grid: { display: false }, ticks: { color: styles.getPropertyValue("--sz-color-text-muted"), maxTicksLimit: 8, font: { size: 10 } } },
          y: { beginAtZero: true, ticks: { precision: 0, color: styles.getPropertyValue("--sz-color-text-muted"), font: { size: 10 } }, grid: { color: styles.getPropertyValue("--sz-color-border") } }
        }
      }
    });
  }

  function renderProperties(items) {
    const body = $("#pbReservationPropertyRows");
    body.replaceChildren();
    if (!items.length) {
      const row = create("tr");
      const cell = appendCell(row, "Sem alojamentos para os filtros escolhidos.", "pb-table-empty");
      cell.colSpan = 6;
      body.appendChild(row);
      return;
    }
    items.forEach((item) => {
      const row = create("tr");
      appendCell(row, item.name);
      appendCell(row, formatNumber(item.requests));
      appendCell(row, formatNumber(item.live_paid));
      appendCell(row, formatNumber(item.test_paid));
      appendCell(row, formatNumber(item.live_nights));
      appendCell(row, formatMoney(item.live_revenue), "pb-money-cell");
      body.appendChild(row);
    });
  }

  function statusChip(item) {
    return create("span", `pb-reservation-state is-${item.status}`, item.status_label);
  }

  function renderReservations(items, pagination) {
    const body = $("#pbReservationRows");
    body.replaceChildren();
    if (!items.length) {
      const row = create("tr");
      const cell = appendCell(row, "Não existem reservas para os filtros escolhidos.", "pb-table-empty");
      cell.colSpan = 10;
      body.appendChild(row);
    }
    items.forEach((item) => {
      const row = create("tr");
      appendCell(row, formatDate(item.created_at, true));
      const state = appendCell(row, "");
      state.appendChild(statusChip(item));

      const reference = appendCell(row, "");
      appendMainAndSub(reference, item.reservation_code || "Sem reserva RS", item.booking_id ? `Pedido ${item.booking_id.slice(0, 8)}` : "");

      appendCell(row, item.property_name || "—");
      const stay = appendCell(row, "");
      appendMainAndSub(stay, `${formatDate(`${item.checkin}T12:00:00`, false)} → ${formatDate(`${item.checkout}T12:00:00`, false)}`, `${item.nights} noite(s)`);

      const customer = appendCell(row, "");
      appendMainAndSub(customer, item.customer_name, item.customer_email);
      appendCell(row, `${item.adults + item.children + item.babies}`);

      const value = appendCell(row, "", "pb-money-cell");
      appendMainAndSub(value, formatMoney(item.paid_value === null ? item.estimated_value : item.paid_value), item.paid_value === null ? "estimado" : "pagamento");

      const stripe = appendCell(row, "");
      appendMainAndSub(stripe, item.payment_status || "Sem checkout", item.environment || "");
      if (item.environment) stripe.classList.add(item.environment === "LIVE" ? "is-live" : "is-test");

      const action = appendCell(row, "", "pb-row-action");
      if (item.reservation_code) {
        const link = create("a", "sz_button sz_button_secondary pb-open-reservation", "Abrir");
        link.href = `/reservas/resumo/${encodeURIComponent(item.reservation_code)}`;
        link.setAttribute("aria-label", `Abrir reserva ${item.reservation_code}`);
        action.appendChild(link);
      } else {
        action.appendChild(create("span", "pb-muted-dash", "—"));
      }
      body.appendChild(row);
    });

    currentPage = pagination.page;
    $("#pbReservationsResultCount").textContent = `${formatNumber(pagination.total)} pedido(s)`;
    $("#pbReservationsPage").textContent = `Página ${pagination.page} de ${pagination.pages}`;
    $("#pbReservationsPrevious").disabled = pagination.page <= 1;
    $("#pbReservationsNext").disabled = pagination.page >= pagination.pages;
  }

  function render(data) {
    renderOptions(data.options);
    renderKpis(data.kpis);
    renderStatusBreakdown(data.status_breakdown);
    renderTimeline(data.timeline);
    renderProperties(data.properties);
    renderReservations(data.reservations, data.pagination);
  }

  function paramsFor(page) {
    return new URLSearchParams({
      start: $("#pbReservationsStart").value,
      end: $("#pbReservationsEnd").value,
      status: $("#pbReservationsStatus").value,
      property_id: $("#pbReservationsProperty").value,
      environment: $("#pbReservationsEnvironment").value,
      query: $("#pbReservationsQuery").value.trim(),
      page: String(page || 1),
      page_size: "25"
    });
  }

  async function loadDashboard(page) {
    if (requestController) requestController.abort();
    requestController = new AbortController();
    setStatus("A atualizar as reservas…", false);
    const params = paramsFor(page);
    try {
      const response = await fetch(`${root.dataset.apiUrl}?${params.toString()}`, {
        credentials: "same-origin",
        signal: requestController.signal,
        headers: { Accept: "application/json" }
      });
      const payload = await response.json();
      if (!response.ok || !payload.ok) throw new Error(payload.error || "Não foi possível carregar os dados.");
      render(payload.data);
      const browserUrl = new URL(window.location.href);
      browserUrl.search = params.toString();
      window.history.replaceState({}, "", browserUrl);
      setStatus("", false);
    } catch (error) {
      if (error.name === "AbortError") return;
      setStatus(error.message || "Não foi possível carregar as reservas.", true);
    }
  }

  $("#pbReservationsFilters").addEventListener("submit", (event) => {
    event.preventDefault();
    loadDashboard(1);
  });
  $("#pbReservationsClear").addEventListener("click", () => {
    $("#pbReservationsStatus").value = "";
    $("#pbReservationsProperty").value = "";
    $("#pbReservationsEnvironment").value = "";
    $("#pbReservationsQuery").value = "";
    loadDashboard(1);
  });
  $("#pbReservationsPrevious").addEventListener("click", () => loadDashboard(currentPage - 1));
  $("#pbReservationsNext").addEventListener("click", () => loadDashboard(currentPage + 1));

  loadDashboard(Number(new URLSearchParams(window.location.search).get("page")) || 1);
})();
