(function () {
  const state = {
    ano: Number(window.FATRES_ANO_INICIAL || new Date().getFullYear()),
    mes: Number(window.FATRES_MES_INICIAL || new Date().getMonth() + 1),
    rows: [],
    selected: new Set(),
    emissor: "",
    serieStamp: "",
    series: [],
  };

  const els = {
    ano: document.getElementById("fatresAno"),
    mes: document.getElementById("fatresMes"),
    prev: document.getElementById("fatresPrev"),
    next: document.getElementById("fatresNext"),
    refresh: document.getElementById("fatresRefresh"),
    body: document.getElementById("fatresBody"),
    checkAll: document.getElementById("fatresCheckAll"),
    stats: document.getElementById("fatresStats"),
    festamp: document.getElementById("fatresFestamp"),
    fts: document.getElementById("fatresFts"),
    emitir: document.getElementById("fatresEmitir"),
    overlay: document.getElementById("fatresOverlay"),
    overlaySub: document.getElementById("fatresOverlaySub"),
    overlayBar: document.getElementById("fatresOverlayBar"),
  };

  let emitStatusPollTimer = null;
  const nowRef = new Date();
  const maxAno = nowRef.getFullYear();
  const maxMes = nowRef.getMonth() + 1;

  const fmtMoney = (value) =>
    Number(value || 0).toLocaleString("pt-PT", {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    });

  const escapeHtml = (value) =>
    String(value || "").replace(/[&<>\"']/g, (match) => {
      return {
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;",
      }[match];
    });

  const toDMY = (iso) => {
    const value = String(iso || "").trim();
    if (!value || !/^\d{4}-\d{2}-\d{2}$/.test(value)) {
      return "";
    }
    return value.slice(8, 10) + "-" + value.slice(5, 7) + "-" + value.slice(0, 4);
  };

  function emptyRow(message, klass) {
    return (
      '<tr><td colspan="12" class="sz_table_cell fatres-cell-center ' +
      (klass || "sz_text_muted") +
      '">' +
      escapeHtml(message) +
      "</td></tr>"
    );
  }

  function clampToAllowedMonth() {
    if (state.ano > maxAno) {
      state.ano = maxAno;
      state.mes = maxMes;
    } else if (state.ano === maxAno && state.mes > maxMes) {
      state.mes = maxMes;
    }

    state.mes = Math.max(1, Math.min(12, state.mes));

    if (els.ano) {
      els.ano.value = String(state.ano);
    }
    if (els.mes) {
      els.mes.value = String(state.mes);
    }
  }

  function updateNavButtons() {
    const atMax = state.ano >= maxAno && state.mes >= maxMes;
    if (els.next) {
      els.next.disabled = atMax;
    }
  }

  function updateStats() {
    const total = state.rows.filter((row) => Number(row.FATURADO || 0) === 0).length;
    const selected = state.selected.size;
    if (els.stats) {
      els.stats.textContent = selected + " selecionadas de " + total + " por faturar";
    }
  }

  function syncCheckAll() {
    if (!els.checkAll) {
      return;
    }

    const ids = state.rows
      .filter((row) => Number(row.FATURADO || 0) === 0)
      .map((row) => String(row.RSSTAMP || ""));

    if (!ids.length) {
      els.checkAll.checked = false;
      els.checkAll.indeterminate = false;
      return;
    }

    const selected = ids.filter((id) => state.selected.has(id)).length;
    els.checkAll.checked = selected === ids.length;
    els.checkAll.indeterminate = selected > 0 && selected < ids.length;
  }

  function render() {
    if (!els.body) {
      return;
    }

    if (!state.rows.length) {
      els.body.innerHTML = emptyRow("Sem reservas no periodo.", "sz_text_muted");
      updateStats();
      syncCheckAll();
      return;
    }

    els.body.innerHTML = state.rows
      .map((row) => {
        const id = String(row.RSSTAMP || "");
        const faturado = Number(row.FATURADO || 0) === 1;
        const checked = state.selected.has(id);
        const rowClass = "sz_table_row" + (checked ? " fatres-row-selected" : "");

        return (
          '<tr class="' +
          rowClass +
          '" data-id="' +
          escapeHtml(id) +
          '">' +
          '<td class="sz_table_cell fatres-cell-center">' +
          '<input type="checkbox" class="fatres-check" ' +
          (checked ? "checked " : "") +
          (faturado ? "disabled " : "") +
          ">" +
          "</td>" +
          '<td class="sz_table_cell">' +
          escapeHtml(row.RESERVA) +
          "</td>" +
          '<td class="sz_table_cell">' +
          escapeHtml(row.ALOJAMENTO) +
          "</td>" +
          '<td class="sz_table_cell">' +
          escapeHtml(row.HOSPEDE) +
          "</td>" +
          '<td class="sz_table_cell fatres-cell-right">' +
          escapeHtml(toDMY(row.DATAIN)) +
          "</td>" +
          '<td class="sz_table_cell fatres-cell-right">' +
          escapeHtml(toDMY(row.DATAOUT)) +
          "</td>" +
          '<td class="sz_table_cell fatres-cell-right">' +
          Number(row.NOITES || 0) +
          "</td>" +
          '<td class="sz_table_cell fatres-cell-right">' +
          Number(row.PAX || 0) +
          "</td>" +
          '<td class="sz_table_cell fatres-cell-right">' +
          fmtMoney(row.ESTADIA) +
          "</td>" +
          '<td class="sz_table_cell fatres-cell-right">' +
          fmtMoney(row.LIMPEZA) +
          "</td>" +
          '<td class="sz_table_cell fatres-cell-center">' +
          renderFaturadoCell(row, faturado) +
          "</td>" +
          '<td class="sz_table_cell fatres-cell-center">' +
          renderPdfCell(row) +
          "</td>" +
          "</tr>"
        );
      })
      .join("");

    els.body.querySelectorAll("tr[data-id]").forEach((tr) => {
      const id = tr.getAttribute("data-id") || "";
      const checkbox = tr.querySelector(".fatres-check");
      if (!checkbox) {
        return;
      }

      checkbox.addEventListener("change", () => {
        if (checkbox.checked) {
          state.selected.add(id);
        } else {
          state.selected.delete(id);
        }
        render();
      });
    });

    syncCheckAll();
    updateStats();
  }

  function renderFaturadoCell(row, faturado) {
    if (!faturado) {
      return '<span class="fatres-badge-no">Nao</span>';
    }

    if (row.FTSTAMP_FATURA) {
      return (
        '<a class="fatres-fatura-link" href="/faturacao/ft/' +
        encodeURIComponent(String(row.FTSTAMP_FATURA || "").trim()) +
        '" target="_blank" rel="noopener">' +
        escapeHtml(row.FATURA_LABEL || "") +
        "</a>"
      );
    }

    return '<span class="fatres-badge-ok">' + escapeHtml(row.FATURA_LABEL || "Emitida") + "</span>";
  }

  function renderPdfCell(row) {
    const stamp = String(row.FTSTAMP_FATURA || "").trim();
    if (!stamp) {
      return "";
    }

    if (Number(row.PDF_OK || 0) === 1) {
      return (
        '<a class="fatres-pdf-link" href="/api/faturacao/ft/' +
        encodeURIComponent(stamp) +
        '/pdf" target="_blank" rel="noopener" title="Abrir PDF">' +
        '<i class="fa-solid fa-file-pdf"></i>' +
        "</a>"
      );
    }

    return (
      '<button type="button" class="fatres-pdf-gen" data-ftstamp="' +
      escapeHtml(stamp) +
      '" title="Gerar PDF">' +
      '<i class="fa-solid fa-file-circle-plus"></i>' +
      "</button>"
    );
  }

  function renderSeriesSelect() {
    if (!els.fts) {
      return;
    }

    const options =
      '<option value="">Serie de faturacao...</option>' +
      state.series
        .map((serie) => {
          const id = String(serie.FTSSTAMP || "").trim();
          const label =
            (serie.NMDOC || serie.NDOC || "") +
            " - " +
            (serie.SERIE || "") +
            (Number(serie.NO_SAFT || 0) === 1 ? " - NO_SAFT" : "");
          return '<option value="' + escapeHtml(id) + '">' + escapeHtml(label) + "</option>";
        })
        .join("");

    els.fts.innerHTML = options;

    if (state.serieStamp && state.series.some((row) => String(row.FTSSTAMP || "").trim() === state.serieStamp)) {
      els.fts.value = state.serieStamp;
    } else {
      state.serieStamp = "";
    }
  }

  async function loadConfig() {
    if (!els.festamp) {
      return;
    }

    try {
      const qs = new URLSearchParams({ ano: String(state.ano) });
      const response = await fetch("/api/faturacao/reservas/config?" + qs.toString());
      const data = await response.json().catch(() => ({}));

      if (!response.ok || data.error) {
        throw new Error(data.error || "Erro ao carregar configuracao");
      }

      const emissores = Array.isArray(data.emissores) ? data.emissores : [];
      els.festamp.innerHTML =
        '<option value="">Entidade emissora...</option>' +
        emissores
          .map((item) => {
            const id = String(item.FESTAMP || "").trim();
            const txt = (item.NOME || "") + (item.NIF ? " (" + item.NIF + ")" : "");
            return '<option value="' + escapeHtml(id) + '">' + escapeHtml(txt) + "</option>";
          })
          .join("");

      if (state.emissor && emissores.some((item) => String(item.FESTAMP || "").trim() === state.emissor)) {
        els.festamp.value = state.emissor;
      } else {
        state.emissor = emissores.length ? String(emissores[0].FESTAMP || "").trim() : "";
        if (state.emissor) {
          els.festamp.value = state.emissor;
        }
      }

      await loadSeries();
    } catch (_error) {
      els.festamp.innerHTML = '<option value="">Erro a carregar emissor</option>';
      state.series = [];
      renderSeriesSelect();
    }
  }

  async function loadSeries() {
    if (!els.festamp) {
      return;
    }

    state.emissor = String(els.festamp.value || "").trim();

    if (!state.emissor) {
      state.series = [];
      renderSeriesSelect();
      return;
    }

    try {
      const qs = new URLSearchParams({
        festamp: state.emissor,
        ano: String(state.ano),
      });
      const response = await fetch("/api/faturacao/reservas/series?" + qs.toString());
      const data = await response.json().catch(() => []);

      if (!response.ok || data.error) {
        throw new Error(data.error || "Erro ao carregar series");
      }

      state.series = Array.isArray(data) ? data : [];
      if (!state.serieStamp && state.series.length) {
        state.serieStamp = String(state.series[0].FTSSTAMP || "").trim();
      }

      renderSeriesSelect();
    } catch (_error) {
      state.series = [];
      renderSeriesSelect();
    }
  }

  async function waitEmitJob(jobId, fallbackTotal) {
    return new Promise((resolve, reject) => {
      let ticks = 0;
      const maxTicks = 1800;

      emitStatusPollTimer = setInterval(async () => {
        try {
          ticks += 1;

          if (ticks > maxTicks) {
            clearInterval(emitStatusPollTimer);
            emitStatusPollTimer = null;
            reject(new Error("Tempo limite na emissao."));
            return;
          }

          const response = await fetch(
            "/api/faturacao/reservas/emitir/status?job_id=" + encodeURIComponent(jobId)
          );
          const statusData = await response.json().catch(() => ({}));

          if (!response.ok || statusData.error) {
            clearInterval(emitStatusPollTimer);
            emitStatusPollTimer = null;
            reject(new Error(statusData.error || "Erro ao obter progresso"));
            return;
          }

          const percent = Math.max(0, Math.min(100, Number(statusData.percent || 0)));
          const processed = Number(statusData.processed || 0);
          const total = Number(statusData.total || fallbackTotal || 0);
          const created = Number(statusData.created_count || 0);
          const errors = Number(statusData.errors_count || 0);
          const message = String(statusData.message || "").trim() || "A emitir faturas...";

          if (els.overlayBar) {
            els.overlayBar.style.width = percent + "%";
          }
          if (els.overlaySub) {
            els.overlaySub.textContent =
              message + " (" + processed + "/" + total + " - OK " + created + " - Erros " + errors + ")";
          }

          const currentState = String(statusData.state || "").toLowerCase();
          if (currentState === "done") {
            clearInterval(emitStatusPollTimer);
            emitStatusPollTimer = null;
            resolve(statusData.result || {});
            return;
          }

          if (currentState === "error") {
            clearInterval(emitStatusPollTimer);
            emitStatusPollTimer = null;
            reject(new Error(statusData.error || statusData.message || "Erro na emissao"));
          }
        } catch (error) {
          clearInterval(emitStatusPollTimer);
          emitStatusPollTimer = null;
          reject(error);
        }
      }, 500);
    });
  }

  async function emitirSelecionadas() {
    const rsstamps = Array.from(state.selected);
    state.emissor = String(els.festamp ? els.festamp.value : "").trim();
    state.serieStamp = String(els.fts ? els.fts.value : "").trim();

    if (!state.emissor) {
      window.alert("Seleciona a entidade emissora.");
      return;
    }
    if (!state.serieStamp) {
      window.alert("Seleciona a serie de faturacao.");
      return;
    }
    if (!rsstamps.length) {
      window.alert("Seleciona pelo menos uma reserva.");
      return;
    }

    if (!window.confirm("Emitir " + rsstamps.length + " fatura(s) de reserva?")) {
      return;
    }

    if (emitStatusPollTimer) {
      clearInterval(emitStatusPollTimer);
      emitStatusPollTimer = null;
    }

    if (els.emitir) {
      els.emitir.disabled = true;
    }
    if (els.overlay) {
      els.overlay.classList.add("show");
    }
    if (els.overlaySub) {
      els.overlaySub.textContent = "A preparar emissao de " + rsstamps.length + " reservas...";
    }
    if (els.overlayBar) {
      els.overlayBar.style.width = "2%";
    }

    try {
      const response = await fetch("/api/faturacao/reservas/emitir/start", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ano: state.ano,
          mes: state.mes,
          festamp: state.emissor,
          ftsstamp: state.serieStamp,
          rsstamps: rsstamps,
        }),
      });
      const startData = await response.json().catch(() => ({}));

      if (!response.ok || startData.error) {
        throw new Error(startData.error || "Erro ao iniciar emissao");
      }

      const jobId = String(startData.job_id || "").trim();
      if (!jobId) {
        throw new Error("Job de emissao invalido");
      }

      const result = await waitEmitJob(jobId, rsstamps.length);
      const createdCount = Array.isArray(result.created) ? result.created.length : 0;
      const errorsCount = Array.isArray(result.errors) ? result.errors.length : 0;

      const createdIds = new Set(
        (result.created || []).map((item) => String(item && item.RSSTAMP ? item.RSSTAMP : "").trim()).filter(Boolean)
      );
      const createdMap = new Map(
        (result.created || []).map((item) => [String(item && item.RSSTAMP ? item.RSSTAMP : "").trim(), item])
      );

      if (createdIds.size) {
        state.rows = state.rows.map((row) => {
          const id = String(row.RSSTAMP || "").trim();
          if (!createdIds.has(id)) {
            return row;
          }

          const createdRow = createdMap.get(id) || {};
          const label =
            String(createdRow.SERIE_LABEL || "").trim() ||
            (String(createdRow.SERIE || "") + "/" + String(createdRow.FNO || "")).replace(/^\/|\/$/g, "");

          return Object.assign({}, row, {
            FATURADO: 1,
            FATURA_LABEL: label || row.FATURA_LABEL || "Emitida",
            FTSTAMP_FATURA: String(createdRow.FTSTAMP || "").trim() || row.FTSTAMP_FATURA || "",
          });
        });

        createdIds.forEach((id) => state.selected.delete(id));
        render();
      }

      if (els.overlayBar) {
        els.overlayBar.style.width = "100%";
      }
      if (els.overlaySub) {
        els.overlaySub.textContent = "Concluida.";
      }

      let message = "Emissao concluida. Criadas: " + createdCount + ". Erros: " + errorsCount + ".";
      if (errorsCount > 0) {
        const preview = (result.errors || [])
          .slice(0, 5)
          .map((item) => {
            const reserva = item && (item.RESERVA || item.RSSTAMP) ? item.RESERVA || item.RSSTAMP : "";
            return "- " + reserva + ": " + (item && item.error ? item.error : "Erro");
          })
          .join("\n");
        if (preview) {
          message += "\n\nDetalhe:\n" + preview;
        }
      }

      window.alert(message);

      setTimeout(() => {
        if (els.overlay) {
          els.overlay.classList.remove("show");
        }
        if (els.overlayBar) {
          els.overlayBar.style.width = "0%";
        }
      }, 260);
    } catch (error) {
      if (els.overlaySub) {
        els.overlaySub.textContent = "Erro na emissao.";
      }
      setTimeout(() => {
        if (els.overlay) {
          els.overlay.classList.remove("show");
        }
        if (els.overlayBar) {
          els.overlayBar.style.width = "0%";
        }
      }, 220);
      window.alert((error && error.message) || "Erro a emitir reservas");
    } finally {
      if (emitStatusPollTimer) {
        clearInterval(emitStatusPollTimer);
        emitStatusPollTimer = null;
      }
      if (els.emitir) {
        els.emitir.disabled = false;
      }
    }
  }

  async function gerarPdfLinha(ftstamp, buttonEl) {
    const stamp = String(ftstamp || "").trim();
    if (!stamp) {
      return;
    }

    if (buttonEl) {
      buttonEl.disabled = true;
      buttonEl.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i>';
    }

    try {
      const response = await fetch("/api/faturacao/ft/" + encodeURIComponent(stamp) + "/pdf/cache", {
        method: "POST",
      });
      const data = await response.json().catch(() => ({}));

      if (!response.ok || data.error) {
        throw new Error(data.error || "Erro a gerar PDF");
      }

      state.rows = state.rows.map((row) => {
        if (String(row.FTSTAMP_FATURA || "").trim() === stamp) {
          return Object.assign({}, row, { PDF_OK: 1 });
        }
        return row;
      });

      render();
    } catch (error) {
      if (buttonEl) {
        buttonEl.disabled = false;
        buttonEl.innerHTML = '<i class="fa-solid fa-file-circle-plus"></i>';
      }
      window.alert((error && error.message) || "Erro a gerar PDF");
    }
  }

  async function loadData() {
    clampToAllowedMonth();
    updateNavButtons();

    if (!els.body) {
      return;
    }

    els.body.innerHTML = emptyRow("A carregar...", "sz_text_muted");

    try {
      const qs = new URLSearchParams({
        ano: String(state.ano),
        mes: String(state.mes),
      });
      const response = await fetch("/api/faturacao/reservas?" + qs.toString());
      const data = await response.json().catch(() => ({}));

      if (!response.ok || data.error) {
        throw new Error(data.error || "Erro ao carregar reservas");
      }

      state.rows = Array.isArray(data.rows) ? data.rows : [];
      const validIds = new Set(
        state.rows
          .filter((row) => Number(row.FATURADO || 0) === 0)
          .map((row) => String(row.RSSTAMP || ""))
      );

      state.selected = new Set(Array.from(state.selected).filter((id) => validIds.has(id)));
      render();
    } catch (error) {
      els.body.innerHTML = emptyRow((error && error.message) || "Erro", "sz_error");
      updateStats();
      syncCheckAll();
    }
  }

  function shiftMonth(delta) {
    let month = state.mes + delta;
    let year = state.ano;

    if (month < 1) {
      month = 12;
      year -= 1;
    }
    if (month > 12) {
      month = 1;
      year += 1;
    }
    if (year > maxAno || (year === maxAno && month > maxMes)) {
      year = maxAno;
      month = maxMes;
    }

    state.mes = month;
    state.ano = year;

    clampToAllowedMonth();
    updateNavButtons();

    if (els.ano) {
      els.ano.value = String(year);
    }
    if (els.mes) {
      els.mes.value = String(month);
    }

    loadData();
  }

  els.prev && els.prev.addEventListener("click", () => shiftMonth(-1));
  els.next && els.next.addEventListener("click", () => shiftMonth(1));

  els.refresh &&
    els.refresh.addEventListener("click", () => {
      state.ano = Number((els.ano && els.ano.value) || state.ano);
      state.mes = Number((els.mes && els.mes.value) || state.mes);
      clampToAllowedMonth();
      updateNavButtons();
      loadConfig();
      loadData();
    });

  els.ano &&
    els.ano.addEventListener("change", () => {
      state.ano = Number((els.ano && els.ano.value) || state.ano);
      clampToAllowedMonth();
      updateNavButtons();
      loadConfig();
      loadData();
    });

  els.mes &&
    els.mes.addEventListener("change", () => {
      state.mes = Number((els.mes && els.mes.value) || state.mes);
      clampToAllowedMonth();
      updateNavButtons();
      loadData();
    });

  els.checkAll &&
    els.checkAll.addEventListener("change", () => {
      const enabled = !!els.checkAll.checked;
      state.rows.forEach((row) => {
        if (Number(row.FATURADO || 0) === 1) {
          return;
        }
        const id = String(row.RSSTAMP || "");
        if (!id) {
          return;
        }
        if (enabled) {
          state.selected.add(id);
        } else {
          state.selected.delete(id);
        }
      });
      render();
    });

  els.body &&
    els.body.addEventListener("click", (event) => {
      const button = event.target && event.target.closest ? event.target.closest(".fatres-pdf-gen") : null;
      if (!button) {
        return;
      }
      event.preventDefault();
      gerarPdfLinha(button.getAttribute("data-ftstamp") || "", button);
    });

  els.festamp && els.festamp.addEventListener("change", loadSeries);
  els.fts &&
    els.fts.addEventListener("change", () => {
      state.serieStamp = String((els.fts && els.fts.value) || "").trim();
    });
  els.emitir && els.emitir.addEventListener("click", emitirSelecionadas);

  if (els.ano) {
    els.ano.value = String(state.ano);
  }
  if (els.mes) {
    els.mes.value = String(state.mes);
  }

  clampToAllowedMonth();
  updateNavButtons();
  loadConfig();
  loadData();
})();
