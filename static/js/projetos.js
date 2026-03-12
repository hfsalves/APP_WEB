document.addEventListener("DOMContentLoaded", () => {
  const state = {
    meta: null,
    items: [],
  };

  const els = {
    search: document.getElementById("projectsSearch"),
    stateFilter: document.getElementById("projectsStateFilter"),
    responsibleFilter: document.getElementById("projectsResponsibleFilter"),
    mineFilter: document.getElementById("projectsMineFilter"),
    refreshBtn: document.getElementById("projectsRefreshBtn"),
    newBtn: document.getElementById("projectsNewBtn"),
    status: document.getElementById("projectsStatus"),
    body: document.getElementById("projectsTableBody"),
    metricTotal: document.getElementById("projectsMetricTotal"),
    metricActive: document.getElementById("projectsMetricActive"),
    metricDone: document.getElementById("projectsMetricDone"),
    metricOverdue: document.getElementById("projectsMetricOverdue"),

    modalEl: document.getElementById("projectModal"),
    modalTitle: document.getElementById("projectModalTitle"),
    modalStatus: document.getElementById("projectModalStatus"),
    formStamp: document.getElementById("projectFormStamp"),
    formCode: document.getElementById("projectFormCode"),
    formName: document.getElementById("projectFormName"),
    formDescription: document.getElementById("projectFormDescription"),
    formResponsible: document.getElementById("projectFormResponsible"),
    formState: document.getElementById("projectFormState"),
    formPriority: document.getElementById("projectFormPriority"),
    formStartDate: document.getElementById("projectFormStartDate"),
    formExpectedDate: document.getElementById("projectFormExpectedDate"),
    formEndDate: document.getElementById("projectFormEndDate"),
    saveBtn: document.getElementById("projectSaveBtn"),
  };

  const modal = new bootstrap.Modal(els.modalEl);

  const esc = (value) =>
    String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;");

  const formatDate = (value) => {
    if (!value) return "-";
    try {
      return new Intl.DateTimeFormat("pt-PT", { dateStyle: "short" }).format(new Date(value));
    } catch (_) {
      return value;
    }
  };

  function badge(label, tone) {
    return `<span class="sz_badge sz_badge_${tone || "secondary"}">${esc(label || "-")}</span>`;
  }

  function progressHtml(value) {
    const pct = Math.max(0, Math.min(Number(value || 0), 100));
    return `
      <div class="proj-progress">
        <div class="proj-progress-bar"><span style="width:${pct}%"></span></div>
        <div class="proj-progress-text">${pct}% concluido</div>
      </div>
    `;
  }

  async function api(url, options = {}) {
    const response = await fetch(url, options);
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(data.error || "Erro inesperado.");
    }
    return data;
  }

  function setStatus(message, tone = "muted") {
    els.status.className = tone === "danger" ? "text-danger proj-status" : "sz_text_muted proj-status";
    els.status.textContent = message;
  }

  function setModalStatus(message, tone = "muted") {
    els.modalStatus.className = tone === "danger" ? "text-danger proj-helper" : "proj-helper";
    els.modalStatus.textContent = message || "";
  }

  function priorityOptions(selected) {
    return (state.meta?.priorities || [])
      .map((item) => `<option value="${item.CODIGO}" ${Number(selected) === Number(item.CODIGO) ? "selected" : ""}>${esc(item.NOME)}</option>`)
      .join("");
  }

  function stateOptions(selected) {
    return (state.meta?.project_states || [])
      .map((item) => `<option value="${item.CODIGO}" ${Number(selected) === Number(item.CODIGO) ? "selected" : ""}>${esc(item.NOME)}</option>`)
      .join("");
  }

  function responsibleOptions(selected) {
    return ['<option value="">Seleciona...</option>']
      .concat(
        (state.meta?.users || []).map(
          (item) => `<option value="${esc(item.LOGIN)}" ${String(selected || "") === String(item.LOGIN || "") ? "selected" : ""}>${esc(item.NOME || item.LOGIN)}<\/option>`
        )
      )
      .join("");
  }

  function fillFilterOptions() {
    els.stateFilter.innerHTML = '<option value="">Todos</option>' + (state.meta?.project_states || [])
      .map((item) => `<option value="${item.CODIGO}">${esc(item.NOME)}</option>`)
      .join("");
    els.responsibleFilter.innerHTML = '<option value="">Todos</option>' + (state.meta?.users || [])
      .map((item) => `<option value="${esc(item.LOGIN)}">${esc(item.NOME || item.LOGIN)}</option>`)
      .join("");
  }

  function fillModal(project = null) {
    els.formStamp.value = project?.PROJSTAMP || "";
    els.formCode.value = project?.CODIGO || "";
    els.formName.value = project?.NOME || "";
    els.formDescription.value = project?.DESCRICAO || "";
    els.formResponsible.innerHTML = responsibleOptions(project?.RESPONSAVEL || "");
    els.formState.innerHTML = stateOptions(project?.ESTADO || 1);
    els.formPriority.innerHTML = priorityOptions(project?.PRIORIDADE || 2);
    els.formStartDate.value = project?.DATAINICIO || "";
    els.formExpectedDate.value = project?.DATAPREVISTA || "";
    els.formEndDate.value = project?.DATAFIM || "";
    els.modalTitle.textContent = project?.PROJSTAMP ? `Projeto ${project.CODIGO || ""}` : "Novo projeto";
    setModalStatus("");
  }

  function collectPayload() {
    return {
      CODIGO: els.formCode.value,
      NOME: els.formName.value,
      DESCRICAO: els.formDescription.value,
      RESPONSAVEL: els.formResponsible.value,
      ESTADO: els.formState.value,
      PRIORIDADE: els.formPriority.value,
      DATAINICIO: els.formStartDate.value,
      DATAPREVISTA: els.formExpectedDate.value,
      DATAFIM: els.formEndDate.value,
    };
  }

  function renderTable() {
    if (!state.items.length) {
      els.body.innerHTML = '<tr class="sz_table_row"><td colspan="9" class="sz_table_cell sz_text_muted">Sem projetos para os filtros atuais.</td></tr>';
      return;
    }
    els.body.innerHTML = state.items.map((item) => `
      <tr class="sz_table_row" data-open="${esc(item.PROJSTAMP)}">
        <td class="sz_table_cell"><strong>${esc(item.CODIGO || "-")}</strong></td>
        <td class="sz_table_cell">
          <div class="proj-row-main">
            <div class="proj-row-title">${esc(item.NOME || "-")}</div>
            <div class="proj-row-subtitle">${esc(item.DESCRICAO || "Sem descricao.")}</div>
          </div>
        </td>
        <td class="sz_table_cell">${esc(item.RESPONSAVEL_NOME || item.RESPONSAVEL || "-")}</td>
        <td class="sz_table_cell">${badge(item.ESTADO_NOME, item.ESTADO_COR)}</td>
        <td class="sz_table_cell">${badge(item.PRIORIDADE_NOME, item.PRIORIDADE_COR)}</td>
        <td class="sz_table_cell">${formatDate(item.DATAPREVISTA)}</td>
        <td class="sz_table_cell">${item.TAREFAS_CONCLUIDAS}/${item.TOTAL_TAREFAS}</td>
        <td class="sz_table_cell">${progressHtml(item.PROGRESSO)}</td>
        <td class="sz_table_cell sz_text_right">
          <button type="button" class="sz_button sz_button_ghost" data-edit="${esc(item.PROJSTAMP)}">
            <i class="fa-solid fa-pen"></i>
          </button>
        </td>
      </tr>
    `).join("");

    els.body.querySelectorAll("[data-open]").forEach((row) => {
      row.addEventListener("click", (event) => {
        if (event.target.closest("[data-edit]")) return;
        window.location.href = `/projetos/${encodeURIComponent(row.dataset.open)}`;
      });
    });

    els.body.querySelectorAll("[data-edit]").forEach((button) => {
      button.addEventListener("click", async (event) => {
        event.stopPropagation();
        const project = state.items.find((item) => item.PROJSTAMP === button.dataset.edit);
        fillModal(project || null);
        modal.show();
      });
    });
  }

  function renderMetrics(metrics) {
    els.metricTotal.textContent = metrics.total_projects || 0;
    els.metricActive.textContent = metrics.active_projects || 0;
    els.metricDone.textContent = metrics.completed_projects || 0;
    els.metricOverdue.textContent = metrics.overdue_projects || 0;
  }

  async function loadMeta() {
    const response = await api("/api/projetos/meta");
    state.meta = response.meta || {};
    fillFilterOptions();
  }

  async function loadProjects() {
    setStatus("A carregar projetos...");
    const params = new URLSearchParams();
    if (els.search.value.trim()) params.set("q", els.search.value.trim());
    if (els.stateFilter.value) params.set("estado", els.stateFilter.value);
    if (els.responsibleFilter.value) params.set("responsavel", els.responsibleFilter.value);
    if (els.mineFilter.checked) params.set("mine", "1");
    const response = await api(`/api/projetos?${params.toString()}`);
    state.items = response.items || [];
    renderTable();
    renderMetrics(response.metrics || {});
    setStatus(`${state.items.length} projeto(s) carregado(s).`);
  }

  async function saveProject() {
    try {
      setModalStatus("A gravar projeto...");
      const stamp = els.formStamp.value.trim();
      const method = stamp ? "PUT" : "POST";
      const url = stamp ? `/api/projetos/${encodeURIComponent(stamp)}` : "/api/projetos";
      await api(url, {
        method,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(collectPayload()),
      });
      modal.hide();
      await loadProjects();
    } catch (error) {
      setModalStatus(error.message || "Erro ao gravar projeto.", "danger");
    }
  }

  const debouncedLoad = (() => {
    let timer = null;
    return () => {
      clearTimeout(timer);
      timer = setTimeout(() => loadProjects().catch((error) => setStatus(error.message || "Erro ao carregar projetos.", "danger")), 220);
    };
  })();

  els.search.addEventListener("input", debouncedLoad);
  els.stateFilter.addEventListener("change", () => loadProjects().catch((error) => setStatus(error.message || "Erro ao carregar projetos.", "danger")));
  els.responsibleFilter.addEventListener("change", () => loadProjects().catch((error) => setStatus(error.message || "Erro ao carregar projetos.", "danger")));
  els.mineFilter.addEventListener("change", () => loadProjects().catch((error) => setStatus(error.message || "Erro ao carregar projetos.", "danger")));
  els.refreshBtn.addEventListener("click", () => loadProjects().catch((error) => setStatus(error.message || "Erro ao carregar projetos.", "danger")));
  els.newBtn.addEventListener("click", () => {
    fillModal(null);
    modal.show();
  });
  els.saveBtn.addEventListener("click", saveProject);

  (async () => {
    try {
      await loadMeta();
      await loadProjects();
    } catch (error) {
      setStatus(error.message || "Erro ao iniciar modulo de projetos.", "danger");
    }
  })();
});
