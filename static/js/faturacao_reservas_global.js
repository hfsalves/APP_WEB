(function () {
  const state = {
    rows: [],
    selected: new Set(),
    options: { alojamentos: [], clientes: [] },
  };

  const els = {
    dataIni: document.getElementById("fatglobDataIni"),
    dataFim: document.getElementById("fatglobDataFim"),
    faturado: document.getElementById("fatglobFaturado"),
    tipo: document.getElementById("fatglobTipo"),
    alojamento: document.getElementById("fatglobAlojamento"),
    cliente: document.getElementById("fatglobCliente"),
    refresh: document.getElementById("fatglobRefresh"),
    emitir: document.getElementById("fatglobEmitir"),
    checkAll: document.getElementById("fatglobCheckAll"),
    body: document.getElementById("fatglobBody"),
    stats: document.getElementById("fatglobStats"),
    totalRows: document.getElementById("fatglobTotalRows"),
    totalValor: document.getElementById("fatglobTotalValor"),
    selectedValor: document.getElementById("fatglobSelectedValor"),
    blockedRows: document.getElementById("fatglobBlockedRows"),
    overlay: document.getElementById("fatglobOverlay"),
    overlaySub: document.getElementById("fatglobOverlaySub"),
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

  function rowWarnings(row) {
    const warnings = Array.isArray(row.CONFIG_WARNINGS) ? row.CONFIG_WARNINGS : [];
    return warnings.map((item) => String(item || "").trim()).filter(Boolean);
  }

  function rowSelectable(row) {
    return Number(row.FATURADO || 0) !== 1 && Number(row.CONFIG_OK || 0) === 1;
  }

  function selectedRows() {
    return state.rows.filter((row) => state.selected.has(String(row.RSSTAMP || "")));
  }

  function updateStats() {
    const total = state.rows.length;
    const selected = state.selected.size;
    const blocked = state.rows.filter((row) => !rowSelectable(row)).length;
    const totalValor = state.rows.reduce((sum, row) => sum + Number(row.VALOR_TOTAL || 0), 0);
    const selectedValor = selectedRows().reduce((sum, row) => sum + Number(row.VALOR_TOTAL || 0), 0);
    if (els.stats) {
      els.stats.textContent =
        selected + " selecionadas de " + total + " reservas" +
        (blocked ? " - " + blocked + " bloqueadas" : "");
    }
    if (els.totalRows) els.totalRows.textContent = String(total);
    if (els.totalValor) els.totalValor.textContent = fmtMoney(totalValor);
    if (els.selectedValor) els.selectedValor.textContent = fmtMoney(selectedValor);
    if (els.blockedRows) els.blockedRows.textContent = String(blocked);
    if (els.emitir) els.emitir.disabled = selected === 0;
  }

  function syncCheckAll() {
    if (!els.checkAll) return;
    const selectable = state.rows.filter(rowSelectable);
    const selected = selectable.filter((row) => state.selected.has(String(row.RSSTAMP || ""))).length;
    els.checkAll.checked = selectable.length > 0 && selected === selectable.length;
    els.checkAll.indeterminate = selected > 0 && selected < selectable.length;
    els.checkAll.disabled = selectable.length === 0;
  }

  function emptyRow(message) {
    return '<tr><td colspan="13" class="sz_table_cell fatglob-empty">' + escapeHtml(message) + "</td></tr>";
  }

  function tipoLabel(tipo) {
    return String(tipo || "").toUpperCase() === "GESTAO" ? "Gestao" : "Exploracao";
  }

  function statusBadge(row) {
    if (Number(row.FATURADO || 0) === 1) {
      const label = [row.PHC_DOC, row.PHC_NUMERO].filter(Boolean).join(" ");
      return '<span class="fatglob-badge ok"><i class="fa-solid fa-circle-check"></i><span>' + escapeHtml(label || "Faturado") + "</span></span>";
    }
    const warnings = rowWarnings(row);
    if (warnings.length) {
      const missingBd = warnings.some((item) => item.toUpperCase().indexOf("BDPHC") >= 0);
      const label = missingBd ? "BDPHC em falta" : warnings[0];
      return '<span class="fatglob-badge warn" title="' + escapeHtml(warnings.join("; ")) + '"><i class="fa-solid fa-triangle-exclamation"></i><span>' + escapeHtml(label) + "</span></span>";
    }
    return '<span class="fatglob-badge"><i class="fa-regular fa-clock"></i><span>Por faturar</span></span>';
  }

  function render() {
    if (!els.body) return;
    if (!state.rows.length) {
      els.body.innerHTML = emptyRow("Sem reservas para os filtros selecionados.");
      syncCheckAll();
      updateStats();
      return;
    }

    els.body.innerHTML = state.rows.map((row) => {
      const id = String(row.RSSTAMP || "");
      const checked = state.selected.has(id);
      const selectable = rowSelectable(row);
      const warnings = rowWarnings(row);
      const warningTitle = warnings.join("; ");
      const warningIcon = warnings.length
        ? '<span class="fatglob-warning" title="' + escapeHtml(warningTitle) + '"><i class="fa-solid fa-triangle-exclamation"></i></span>'
        : "";
      const missingBd = warnings.some((item) => item.toUpperCase().indexOf("BDPHC") >= 0);
      const ownerName = row.TIPO === "GESTAO" ? (row.CLIENTE_NOME || row.CLIENTE || "") : "";
      const ownerCell = ownerName || missingBd
        ? '<span class="fatglob-owner-cell">' + warningIcon + '<span class="fatglob-owner-name">' + escapeHtml(ownerName || "Proprietario sem nome") + "</span>" + (missingBd ? '<span class="fatglob-config-warning">BDPHC em falta</span>' : "") + "</span>"
        : "";
      const pdfUrl = String(row.PHC_PDF_URL || "").trim();
      const pdfCell = pdfUrl
        ? '<a class="fatglob-pdf-link" href="' + escapeHtml(pdfUrl) + '" target="_blank" rel="noopener" title="Abrir PDF"><i class="fa-solid fa-file-pdf"></i></a>'
        : '<span class="fatglob-pdf-empty" title="PDF indisponivel"><i class="fa-regular fa-file-pdf"></i></span>';
      return (
        '<tr class="sz_table_row' + (checked ? " fatglob-row-selected" : "") + (!selectable ? " fatglob-row-blocked" : "") + '" data-id="' + escapeHtml(id) + '">' +
        '<td class="sz_table_cell fatglob-check-cell"><input type="checkbox" class="fatglob-check" ' + (checked ? "checked" : "") + (!selectable ? ' disabled title="' + escapeHtml(warningTitle || "Reserva bloqueada") + '"' : "") + "></td>" +
        '<td class="sz_table_cell">' + statusBadge(row) + "</td>" +
        '<td class="sz_table_cell fatglob-pdf-cell">' + pdfCell + "</td>" +
        '<td class="sz_table_cell">' + escapeHtml(tipoLabel(row.TIPO)) + "</td>" +
        '<td class="sz_table_cell">' + escapeHtml(row.RESERVA || id) + "</td>" +
        '<td class="sz_table_cell">' + escapeHtml(toDMY(row.DATAOUT)) + "</td>" +
        '<td class="sz_table_cell">' + escapeHtml(toDMY(row.FDATA)) + "</td>" +
        '<td class="sz_table_cell">' + escapeHtml(row.ALOJAMENTO) + "</td>" +
        '<td class="sz_table_cell">' + ownerCell + "</td>" +
        '<td class="sz_table_cell">' + escapeHtml(row.HOSPEDE) + "</td>" +
        '<td class="sz_table_cell fatglob-money">' + fmtMoney(row.ESTADIA) + "</td>" +
        '<td class="sz_table_cell fatglob-money">' + fmtMoney(row.LIMPEZA) + "</td>" +
        '<td class="sz_table_cell fatglob-money"><strong>' + fmtMoney(row.VALOR_TOTAL) + "</strong></td>" +
        "</tr>"
      );
    }).join("");

    els.body.querySelectorAll("tr[data-id]").forEach((tr) => {
      const id = tr.getAttribute("data-id") || "";
      const checkbox = tr.querySelector(".fatglob-check");
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
    const response = await fetch("/api/faturacao/reservas-global/options");
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
    if (els.faturado && els.faturado.value) qs.set("faturado", els.faturado.value);
    if (els.tipo && els.tipo.value) qs.set("tipo", els.tipo.value);
    if (els.alojamento && els.alojamento.value) qs.set("alojamento", els.alojamento.value);
    if (els.cliente && els.cliente.value) qs.set("cliente", els.cliente.value);

    const response = await fetch("/api/faturacao/reservas-global?" + qs.toString());
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

  async function emitir() {
    const ids = Array.from(state.selected);
    if (!ids.length) {
      window.alert("Seleciona pelo menos uma reserva.");
      return;
    }
    if (!window.confirm("Emitir " + ids.length + " fatura(s) no PHC?")) return;
    try {
      if (els.emitir) els.emitir.disabled = true;
      if (els.overlay) els.overlay.classList.add("show");
      if (els.overlaySub) els.overlaySub.textContent = "A enviar " + ids.length + " reserva(s)...";
      const response = await fetch("/api/faturacao/reservas-global/emitir", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ rsstamps: ids }),
      });
      const data = await readPayload(response);
      if (!response.ok && data.error) throw new Error(data.error);
      const created = Array.isArray(data.created) ? data.created : [];
      const errors = Array.isArray(data.errors) ? data.errors : [];
      if (created.length) {
        ids.forEach((id) => state.selected.delete(id));
      }
      if (errors.length) {
        window.alert("Emitidas: " + created.length + "\nErros: " + errors.length + "\n\n" + errors.slice(0, 5).map((err) => (err.RESERVA || err.RSSTAMP || "") + ": " + err.error).join("\n"));
      } else {
        window.alert("Faturas emitidas no PHC: " + created.length);
      }
      await loadRows();
    } catch (error) {
      window.alert(error.message || "Erro ao emitir faturas.");
    } finally {
      if (els.overlay) els.overlay.classList.remove("show");
      updateStats();
    }
  }

  els.refresh && els.refresh.addEventListener("click", loadRows);
  els.emitir && els.emitir.addEventListener("click", emitir);
  [els.dataIni, els.dataFim, els.faturado, els.tipo, els.alojamento, els.cliente].forEach((el) => {
    el && el.addEventListener("change", loadRows);
  });
  els.checkAll && els.checkAll.addEventListener("change", () => {
    const checked = !!els.checkAll.checked;
    state.selected.clear();
    if (checked) {
      state.rows.filter(rowSelectable).forEach((row) => state.selected.add(String(row.RSSTAMP || "")));
    }
    render();
  });

  refreshAll();
})();
