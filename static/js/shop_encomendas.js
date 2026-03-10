document.addEventListener("DOMContentLoaded", () => {
  const state = {
    meta: null,
    orders: [],
  };

  const els = {
    search: document.getElementById("shopOrdersSearch"),
    stateFilter: document.getElementById("shopOrdersStateFilter"),
    paymentStateFilter: document.getElementById("shopOrdersPaymentStateFilter"),
    dateFrom: document.getElementById("shopOrdersDateFrom"),
    dateTo: document.getElementById("shopOrdersDateTo"),
    refresh: document.getElementById("shopOrdersRefreshBtn"),
    status: document.getElementById("shopOrdersStatus"),
    tableBody: document.getElementById("shopOrdersBody"),
    count: document.getElementById("shopOrdersCount"),
    paidCount: document.getElementById("shopOrdersPaidCount"),
    stripeCount: document.getElementById("shopOrdersStripeCount"),
    totalValue: document.getElementById("shopOrdersTotalValue"),

    modalEl: document.getElementById("shopOrderDetailModal"),
    modalTitle: document.getElementById("shopOrderDetailTitle"),
    modalSubtitle: document.getElementById("shopOrderDetailSubtitle"),
    modalStatus: document.getElementById("shopOrderDetailStatus"),
    kpiState: document.getElementById("shopOrderKpiState"),
    kpiTotal: document.getElementById("shopOrderKpiTotal"),
    kpiPaid: document.getElementById("shopOrderKpiPaid"),
    kpiRefunded: document.getElementById("shopOrderKpiRefunded"),
    headerGrid: document.getElementById("shopOrderHeaderGrid"),
    linesBody: document.getElementById("shopOrderLinesBody"),
    paymentsBody: document.getElementById("shopOrderPaymentsBody"),
    transactionsBody: document.getElementById("shopOrderTransactionsBody"),
    refundsBody: document.getElementById("shopOrderRefundsBody"),
    logsBody: document.getElementById("shopOrderLogsBody"),
  };

  const detailModal = new bootstrap.Modal(els.modalEl);

  const money = (value, currency = "EUR") =>
    new Intl.NumberFormat("pt-PT", { style: "currency", currency }).format(Number(value || 0));
  const dt = (value) => {
    if (!value) return "-";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return value;
    return new Intl.DateTimeFormat("pt-PT", {
      dateStyle: "short",
      timeStyle: "short",
    }).format(date);
  };
  const esc = (value) =>
    String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;");

  async function api(url) {
    const response = await fetch(url);
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(data.error || "Erro inesperado.");
    }
    return data;
  }

  function badge(label, tone) {
    return `<span class="sz_badge sz_badge_${tone}">${esc(label)}</span>`;
  }

  function setStatus(message, tone = "muted") {
    els.status.className = tone === "danger" ? "text-danger shop-bo-status" : "sz_text_muted shop-bo-status";
    els.status.textContent = message;
  }

  function setModalStatus(message, tone = "muted") {
    els.modalStatus.className = tone === "danger" ? "text-danger shop-bo-helper" : "shop-bo-helper";
    els.modalStatus.textContent = message || "";
  }

  function collectFilters() {
    return new URLSearchParams({
      q: els.search.value.trim(),
      estado_id: els.stateFilter.value,
      payment_state: els.paymentStateFilter.value,
      date_from: els.dateFrom.value,
      date_to: els.dateTo.value,
    }).toString();
  }

  function populateMeta() {
    const states = state.meta?.order_states || [];
    const paymentStates = state.meta?.payment_states || [];
    els.stateFilter.innerHTML = '<option value="">Todos</option>' + states.map((item) => (
      `<option value="${item.ENCOMENDA_ESTADO_ID}">${esc(item.NOME)}</option>`
    )).join("");
    els.paymentStateFilter.innerHTML = '<option value="">Todos</option>' + paymentStates.map((item) => (
      `<option value="${item.code}">${esc(item.name)}</option>`
    )).join("");
  }

  function renderOrders(items, summary) {
    if (!items.length) {
      els.tableBody.innerHTML = '<tr class="sz_table_row"><td colspan="10" class="sz_table_cell sz_text_muted">Nenhuma encomenda encontrada.</td></tr>';
    } else {
      els.tableBody.innerHTML = items.map((item) => `
        <tr class="sz_table_row">
          <td class="sz_table_cell shop-bo-code">${item.ENCOMENDA_ID}</td>
          <td class="sz_table_cell shop-bo-code">${esc(item.NUMERO || "-")}</td>
          <td class="sz_table_cell shop-bo-code">${esc(item.RESERVA || "-")}</td>
          <td class="sz_table_cell">${dt(item.CRIADO_EM)}</td>
          <td class="sz_table_cell">${badge(item.ESTADO_NOME || "-", String(item.ESTADO_CODIGO || "").toLowerCase() === "paga" ? "success" : String(item.ESTADO_CODIGO || "").toLowerCase() === "cancelada" ? "warning" : "info")}</td>
          <td class="sz_table_cell sz_text_right">${money(item.TOTAL, item.MOEDA || "EUR")}</td>
          <td class="sz_table_cell">${item.PAGAMENTO_ESTADO ? badge(item.PAGAMENTO_ESTADO, item.PAGAMENTO_ESTADO === "PAGO" ? "success" : item.PAGAMENTO_ESTADO.includes("REEMBOLS") ? "warning" : "info") : '<span class="sz_text_muted">-</span>'}</td>
          <td class="sz_table_cell">${item.TEM_STRIPE ? badge("Stripe", "info") : '<span class="sz_text_muted">Sem Stripe</span>'}</td>
          <td class="sz_table_cell shop-bo-code">${esc(item.PAYMENT_INTENT_ID || item.CHECKOUT_SESSION_ID || item.CHARGE_ID || "-")}</td>
          <td class="sz_table_cell sz_text_right">
            <button type="button" class="sz_button sz_button_ghost shop-bo-row_button" data-action="detail" data-id="${item.ENCOMENDA_ID}">
              <i class="fa-solid fa-eye"></i>
            </button>
          </td>
        </tr>
      `).join("");
    }
    els.count.textContent = String(items.length);
    els.paidCount.textContent = String(summary?.paid_count || 0);
    els.stripeCount.textContent = String(summary?.stripe_count || 0);
    els.totalValue.textContent = money(summary?.total_value || 0, "EUR");
  }

  function renderKeyValueGrid(target, rows) {
    target.innerHTML = rows.map((row) => `
      <div class="shop-bo-metric">
        <div class="shop-bo-metric_label">${esc(row.label)}</div>
        <div class="shop-bo-helper ${row.code ? "shop-bo-code" : ""}">${row.value ? esc(row.value) : "-"}</div>
      </div>
    `).join("");
  }

  function renderTableBody(target, columns, items, emptyLabel) {
    if (!items.length) {
      target.innerHTML = `<tr class="sz_table_row"><td colspan="${columns}" class="sz_table_cell sz_text_muted">${emptyLabel}</td></tr>`;
      return;
    }
    target.innerHTML = items.join("");
  }

  async function loadOrders() {
    setStatus("A carregar encomendas...");
    const data = await api(`/api/shop/encomendas?${collectFilters()}`);
    state.orders = data.items || [];
    renderOrders(state.orders, data.summary || {});
    setStatus(`${data.count || 0} encomenda(s) encontradas.`);
  }

  async function loadMeta() {
    const data = await api("/api/shop/meta");
    state.meta = data.meta;
    populateMeta();
  }

  async function openOrderDetail(orderId) {
    setModalStatus("A carregar detalhe...");
    detailModal.show();
    const data = await api(`/api/shop/encomendas/${orderId}`);
    const header = data.header;
    els.modalTitle.textContent = `Encomenda #${header.ENCOMENDA_ID}`;
    els.modalSubtitle.textContent = `${header.NUMERO || "Sem numero"} · Reserva ${header.RESERVA || "-"}`;
    els.kpiState.textContent = header.ESTADO_NOME || "-";
    els.kpiTotal.textContent = money(header.TOTAL, header.MOEDA || "EUR");
    els.kpiPaid.textContent = money(header.TOTAL_PAGO, header.MOEDA || "EUR");
    els.kpiRefunded.textContent = money(header.TOTAL_REEMBOLSADO, header.MOEDA || "EUR");

    renderKeyValueGrid(els.headerGrid, [
      { label: "ID", value: String(header.ENCOMENDA_ID), code: true },
      { label: "Numero", value: header.NUMERO || "-", code: true },
      { label: "Reserva", value: header.RESERVA || "-", code: true },
      { label: "Estado", value: header.ESTADO_NOME || "-" },
      { label: "Moeda", value: header.MOEDA || "-" },
      { label: "Carrinho", value: header.CARRINHO_ID ? String(header.CARRINHO_ID) : "-" },
      { label: "Criada", value: dt(header.CRIADO_EM) },
      { label: "Alterada", value: dt(header.ALTERADO_EM) },
      { label: "Paga em", value: dt(header.PAGA_EM) },
      { label: "Cancelada em", value: dt(header.CANCELADA_EM) },
      { label: "Subtotal", value: money(header.SUBTOTAL, header.MOEDA || "EUR") },
      { label: "Total", value: money(header.TOTAL, header.MOEDA || "EUR") },
    ]);

    renderTableBody(
      els.linesBody,
      6,
      (data.lines || []).map((line) => `
        <tr class="sz_table_row">
          <td class="sz_table_cell shop-bo-code">${line.NUMERO_LINHA}</td>
          <td class="sz_table_cell">${esc(line.PRODUTO_NOME)}</td>
          <td class="sz_table_cell">${esc(line.VARIANTE_NOME || "-")}</td>
          <td class="sz_table_cell sz_text_right">${Number(line.QUANTIDADE || 0).toLocaleString("pt-PT")}</td>
          <td class="sz_table_cell sz_text_right">${money(line.PRECO_UNITARIO, header.MOEDA || "EUR")}</td>
          <td class="sz_table_cell sz_text_right">${money(line.TOTAL, header.MOEDA || "EUR")}</td>
        </tr>
      `),
      "Sem linhas."
    );

    renderTableBody(
      els.paymentsBody,
      7,
      (data.payments || []).map((payment) => `
        <tr class="sz_table_row">
          <td class="sz_table_cell shop-bo-code">${payment.PAGAMENTO_ID}</td>
          <td class="sz_table_cell">${badge(payment.ESTADO || "-", payment.ESTADO === "PAGO" ? "success" : payment.ESTADO && payment.ESTADO.includes("REEMBOLS") ? "warning" : "info")}</td>
          <td class="sz_table_cell sz_text_right">${money(payment.VALOR, payment.MOEDA || "EUR")}</td>
          <td class="sz_table_cell sz_text_right">${money(payment.VALOR_CAPTURADO, payment.MOEDA || "EUR")}</td>
          <td class="sz_table_cell sz_text_right">${money(payment.VALOR_REEMBOLSADO, payment.MOEDA || "EUR")}</td>
          <td class="sz_table_cell shop-bo-code">${esc(payment.REFERENCIA_EXTERNA || "-")}</td>
          <td class="sz_table_cell">${dt(payment.PAGO_EM)}</td>
        </tr>
      `),
      "Sem pagamentos."
    );

    renderTableBody(
      els.transactionsBody,
      9,
      (data.transactions || []).map((transaction) => `
        <tr class="sz_table_row">
          <td class="sz_table_cell shop-bo-code">${transaction.TRANSACAO_STRIPE_ID}</td>
          <td class="sz_table_cell">${esc(transaction.TIPO_TRANSACAO || "-")}</td>
          <td class="sz_table_cell shop-bo-code">${esc(transaction.EVENT_TYPE || transaction.EVENT_ID || "-")}</td>
          <td class="sz_table_cell shop-bo-code">${esc(transaction.PAYMENT_INTENT_ID || "-")}</td>
          <td class="sz_table_cell shop-bo-code">${esc(transaction.CHECKOUT_SESSION_ID || "-")}</td>
          <td class="sz_table_cell shop-bo-code">${esc(transaction.CHARGE_ID || transaction.REFUND_ID || "-")}</td>
          <td class="sz_table_cell">${esc(transaction.EXTERNAL_STATUS || "-")}</td>
          <td class="sz_table_cell">
            <div>${esc(transaction.PAYLOAD_SUMMARY || "-")}</div>
            ${transaction.PAYLOAD ? `<details class="sz_mt_1"><summary class="shop-bo-helper">Ver raw payload</summary><pre class="shop-bo-pre">${esc(transaction.PAYLOAD)}</pre></details>` : ""}
          </td>
          <td class="sz_table_cell">${dt(transaction.CRIADO_EM)}</td>
        </tr>
      `),
      "Sem transacoes."
    );

    renderTableBody(
      els.refundsBody,
      6,
      (data.refunds || []).map((refund) => `
        <tr class="sz_table_row">
          <td class="sz_table_cell shop-bo-code">${refund.REEMBOLSO_ID}</td>
          <td class="sz_table_cell">${badge(refund.ESTADO || "-", refund.ESTADO === "PROCESSADO" ? "success" : refund.ESTADO === "FALHADO" ? "danger" : "warning")}</td>
          <td class="sz_table_cell sz_text_right">${money(refund.VALOR, refund.MOEDA || "EUR")}</td>
          <td class="sz_table_cell">${esc(refund.MOTIVO || "-")}</td>
          <td class="sz_table_cell shop-bo-code">${esc(refund.REFUND_ID_EXTERNO || "-")}</td>
          <td class="sz_table_cell">${dt(refund.PROCESSADO_EM)}</td>
        </tr>
      `),
      "Sem reembolsos."
    );

    renderTableBody(
      els.logsBody,
      6,
      (data.logs || []).map((log) => `
        <tr class="sz_table_row">
          <td class="sz_table_cell">${dt(log.CRIADO_EM)}</td>
          <td class="sz_table_cell">${badge(log.NIVEL || "-", log.NIVEL === "ERROR" || log.NIVEL === "FATAL" ? "danger" : log.NIVEL === "WARN" ? "warning" : "info")}</td>
          <td class="sz_table_cell">${esc(log.CATEGORIA || "-")}</td>
          <td class="sz_table_cell">${esc(log.EVENTO || "-")}</td>
          <td class="sz_table_cell">${esc(log.MENSAGEM || "-")}</td>
          <td class="sz_table_cell">${esc(log.DETALHE_RESUMO || "-")}</td>
        </tr>
      `),
      "Sem logs."
    );

    setModalStatus(`${(data.transactions || []).length} transacao(oes) Stripe e ${(data.payments || []).length} pagamento(s) associados.`);
  }

  els.refresh.addEventListener("click", () => loadOrders().catch((error) => setStatus(error.message, "danger")));
  els.search.addEventListener("input", () => {
    clearTimeout(els.search._timer);
    els.search._timer = setTimeout(() => loadOrders().catch((error) => setStatus(error.message, "danger")), 250);
  });
  [els.stateFilter, els.paymentStateFilter, els.dateFrom, els.dateTo].forEach((input) => {
    input.addEventListener("change", () => loadOrders().catch((error) => setStatus(error.message, "danger")));
  });
  els.tableBody.addEventListener("click", (event) => {
    const button = event.target.closest('[data-action="detail"]');
    if (!button) return;
    openOrderDetail(button.dataset.id).catch((error) => setModalStatus(error.message, "danger"));
  });

  (async () => {
    try {
      await loadMeta();
      await loadOrders();
    } catch (error) {
      setStatus(error.message, "danger");
    }
  })();
});
