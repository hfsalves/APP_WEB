(function () {
  const state = {
    rows: [],
    selected: new Set(),
    options: { alojamentos: [], clientes: [] },
  };

  const els = {
    dataIni: document.getElementById("fatpropDataIni"),
    dataFim: document.getElementById("fatpropDataFim"),
    alojamento: document.getElementById("fatpropAlojamento"),
    cliente: document.getElementById("fatpropCliente"),
    refresh: document.getElementById("fatpropRefresh"),
    enviar: document.getElementById("fatpropEnviar"),
    checkAll: document.getElementById("fatpropCheckAll"),
    body: document.getElementById("fatpropBody"),
    stats: document.getElementById("fatpropStats"),
    totalRows: document.getElementById("fatpropTotalRows"),
    totalValor: document.getElementById("fatpropTotalValor"),
    selectedValor: document.getElementById("fatpropSelectedValor"),
    overlay: document.getElementById("fatpropOverlay"),
    overlaySub: document.getElementById("fatpropOverlaySub"),
  };

  const escapeHtml = (value) =>
    String(value || "").replace(/[&<>\"']/g, (match) => ({
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#39;",
    }[match]));

  const fmtMoney = (value) =>
    Number(value || 0).toLocaleString("pt-PT", {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    });

  const toDMY = (iso) => {
    const value = String(iso || "").trim();
    if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) return "";
    return value.slice(8, 10) + "-" + value.slice(5, 7) + "-" + value.slice(0, 4);
  };

  function selectedRows() {
    return state.rows.filter((row) => state.selected.has(String(row.RSSTAMP || "")));
  }

  function rowConfigOk(row) {
    return Number(row.CONFIG_OK || 0) === 1;
  }

  function rowWarnings(row) {
    const warnings = Array.isArray(row.CONFIG_WARNINGS) ? row.CONFIG_WARNINGS : [];
    return warnings.map((item) => String(item || "").trim()).filter(Boolean);
  }

  function updateStats() {
    const total = state.rows.length;
    const selected = state.selected.size;
    const blocked = state.rows.filter((row) => !rowConfigOk(row)).length;
    const totalValor = state.rows.reduce((sum, row) => sum + Number(row.VALOR_FATURAR || 0), 0);
    const selectedValor = selectedRows().reduce((sum, row) => sum + Number(row.VALOR_FATURAR || 0), 0);

    if (els.stats) {
      els.stats.textContent =
        selected + " selecionadas de " + total + " por faturar" +
        (blocked ? " - " + blocked + " sem configuracao PHC" : "");
    }
    if (els.totalRows) els.totalRows.textContent = String(total);
    if (els.totalValor) els.totalValor.textContent = fmtMoney(totalValor);
    if (els.selectedValor) els.selectedValor.textContent = fmtMoney(selectedValor);
    if (els.enviar) els.enviar.disabled = selected === 0;
  }

  function syncCheckAll() {
    if (!els.checkAll) return;
    if (!state.rows.length) {
      els.checkAll.checked = false;
      els.checkAll.indeterminate = false;
      return;
    }
    const selectable = state.rows.filter(rowConfigOk);
    const selected = selectable.filter((row) => state.selected.has(String(row.RSSTAMP || ""))).length;
    els.checkAll.checked = selectable.length > 0 && selected === selectable.length;
    els.checkAll.indeterminate = selected > 0 && selected < selectable.length;
  }

  function emptyRow(message) {
    return '<tr><td colspan="11" class="sz_table_cell fatprop-empty">' + escapeHtml(message) + "</td></tr>";
  }

  function render() {
    if (!els.body) return;

    if (!state.rows.length) {
      els.body.innerHTML = emptyRow("Sem reservas de gestao por faturar para os filtros selecionados.");
      syncCheckAll();
      updateStats();
      return;
    }

    els.body.innerHTML = state.rows.map((row) => {
      const id = String(row.RSSTAMP || "");
      const checked = state.selected.has(id);
      const configOk = rowConfigOk(row);
      const warnings = rowWarnings(row);
      const warningTitle = warnings.length ? warnings.join("; ") : "";
      const warningIcon = warnings.length
        ? '<span class="fatprop-warning" title="' + escapeHtml(warningTitle) + '"><i class="fa-solid fa-triangle-exclamation"></i></span>'
        : "";
      return (
        '<tr class="sz_table_row' + (checked ? " fatprop-row-selected" : "") + (!configOk ? " fatprop-row-warning" : "") + '" data-id="' + escapeHtml(id) + '">' +
        '<td class="sz_table_cell fatprop-check-cell"><input type="checkbox" class="fatprop-check" ' + (checked ? "checked" : "") + (!configOk ? ' disabled title="' + escapeHtml(warningTitle) + '"' : "") + "></td>" +
        '<td class="sz_table_cell">' + escapeHtml(row.RESERVA || id) + "</td>" +
        '<td class="sz_table_cell">' + escapeHtml(toDMY(row.DATAOUT)) + "</td>" +
        '<td class="sz_table_cell">' + escapeHtml(row.ALOJAMENTO) + "</td>" +
        '<td class="sz_table_cell"><span class="fatprop-owner-cell">' + warningIcon + '<span>' + escapeHtml(row.CLIENTE_NOME || row.CLIENTE) + "</span></span></td>" +
        '<td class="sz_table_cell">' + escapeHtml(row.HOSPEDE) + "</td>" +
        '<td class="sz_table_cell fatprop-money">' + fmtMoney(row.ESTADIA) + "</td>" +
        '<td class="sz_table_cell fatprop-money">' + fmtMoney(row.LIMPEZA) + "</td>" +
        '<td class="sz_table_cell fatprop-money">' + fmtMoney(row.COMISSAO_TG) + "</td>" +
        '<td class="sz_table_cell fatprop-money">' + fmtMoney(row.COMISSAO_PERC) + "%</td>" +
        '<td class="sz_table_cell fatprop-money"><strong>' + fmtMoney(row.VALOR_FATURAR) + "</strong></td>" +
        "</tr>"
      );
    }).join("");

    els.body.querySelectorAll("tr[data-id]").forEach((tr) => {
      const id = tr.getAttribute("data-id") || "";
      const checkbox = tr.querySelector(".fatprop-check");
      tr.addEventListener("click", (event) => {
        if (event.target && event.target.matches && event.target.matches("input")) return;
        if (checkbox && checkbox.disabled) return;
        if (state.selected.has(id)) state.selected.delete(id);
        else state.selected.add(id);
        render();
      });
      checkbox && checkbox.addEventListener("change", () => {
        if (checkbox.checked) state.selected.add(id);
        else state.selected.delete(id);
        render();
      });
    });

    syncCheckAll();
    updateStats();
  }

  function renderSelect(select, items, placeholder) {
    if (!select) return;
    const current = String(select.value || "");
    select.innerHTML =
      '<option value="">' + escapeHtml(placeholder) + "</option>" +
      (items || []).map((item) => '<option value="' + escapeHtml(item) + '">' + escapeHtml(item) + "</option>").join("");
    if (current && (items || []).some((item) => String(item) === current)) {
      select.value = current;
    }
  }

  async function readPayload(response) {
    const contentType = String(response.headers.get("content-type") || "").toLowerCase();
    if (contentType.indexOf("application/json") >= 0) {
      return response.json().catch(() => ({}));
    }
    const text = await response.text().catch(() => "");
    return { error: text ? text.slice(0, 500) : "" };
  }

  async function loadOptions() {
    const response = await fetch("/api/faturacao/proprietarios/options");
    const data = await readPayload(response);
    if (!response.ok || data.error) throw new Error(data.error || "Erro ao carregar filtros");
    state.options = {
      alojamentos: Array.isArray(data.alojamentos) ? data.alojamentos : [],
      clientes: Array.isArray(data.clientes) ? data.clientes : [],
    };
    renderSelect(els.alojamento, state.options.alojamentos, "Todos os alojamentos");
    renderSelect(els.cliente, state.options.clientes, "Todos os proprietarios");
  }

  async function loadRows() {
    if (els.body) els.body.innerHTML = emptyRow("A carregar...");
    const qs = new URLSearchParams();
    if (els.dataIni && els.dataIni.value) qs.set("data_ini", els.dataIni.value);
    if (els.dataFim && els.dataFim.value) qs.set("data_fim", els.dataFim.value);
    if (els.alojamento && els.alojamento.value) qs.set("alojamento", els.alojamento.value);
    if (els.cliente && els.cliente.value) qs.set("cliente", els.cliente.value);

    const response = await fetch("/api/faturacao/proprietarios?" + qs.toString());
    const data = await readPayload(response);
    if (!response.ok || data.error) throw new Error(data.error || "Erro ao carregar reservas");
    state.rows = Array.isArray(data.rows) ? data.rows : [];
    const validIds = new Set(state.rows.map((row) => String(row.RSSTAMP || "")));
    state.selected.forEach((id) => {
      if (!validIds.has(id)) state.selected.delete(id);
    });
    render();
  }

  async function refreshAll() {
    try {
      if (els.refresh) els.refresh.disabled = true;
      await loadOptions();
      await loadRows();
    } catch (error) {
      if (els.body) els.body.innerHTML = emptyRow(error.message || "Erro a carregar dados.");
      state.rows = [];
      state.selected.clear();
      updateStats();
      syncCheckAll();
    } finally {
      if (els.refresh) els.refresh.disabled = false;
    }
  }

  async function enviarPhc() {
    const ids = Array.from(state.selected);
    if (!ids.length) {
      window.alert("Seleciona pelo menos uma reserva.");
      return;
    }
    if (!window.confirm("Enviar " + ids.length + " pedido(s) de faturacao para o PHC?")) return;

    try {
      if (els.enviar) els.enviar.disabled = true;
      if (els.overlay) els.overlay.classList.add("show");
      if (els.overlaySub) els.overlaySub.textContent = "A enviar " + ids.length + " reserva(s)...";

      const response = await fetch("/api/faturacao/proprietarios/enviar-phc", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ rsstamps: ids }),
      });
      const data = await readPayload(response);
      if (!response.ok || data.error || data.ok === false) {
        throw new Error(data.error || (data.result && data.result.error) || "Erro ao enviar para o PHC");
      }

      const status = String(data.status || "").toUpperCase();
      if (status === "DRY_RUN") {
        window.alert("Pedido preparado. Falta configurar o endpoint PHC para envio real.");
      } else {
        window.alert("Pedido enviado para o PHC.");
        ids.forEach((id) => state.selected.delete(id));
      }
      await loadRows();
    } catch (error) {
      window.alert(error.message || "Erro ao enviar para o PHC.");
    } finally {
      if (els.overlay) els.overlay.classList.remove("show");
      updateStats();
    }
  }

  els.refresh && els.refresh.addEventListener("click", loadRows);
  els.enviar && els.enviar.addEventListener("click", enviarPhc);
  [els.dataIni, els.dataFim, els.alojamento, els.cliente].forEach((el) => {
    el && el.addEventListener("change", loadRows);
  });
  els.checkAll && els.checkAll.addEventListener("change", () => {
    const checked = !!els.checkAll.checked;
    state.selected.clear();
    if (checked) {
      state.rows.filter(rowConfigOk).forEach((row) => state.selected.add(String(row.RSSTAMP || "")));
    }
    render();
  });

  refreshAll();
})();
