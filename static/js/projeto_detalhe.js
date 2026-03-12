document.addEventListener("DOMContentLoaded", () => {
  const projectStamp = (window.PROJETO_ATUAL || "").trim();
  const state = {
    meta: null,
    project: null,
    tasks: [],
  };

  const els = {
    title: document.getElementById("projectDetailTitle"),
    breadcrumbs: document.getElementById("projectDetailBreadcrumbs"),
    subtitle: document.getElementById("projectDetailSubtitle"),
    status: document.getElementById("projectDetailStatus"),
    code: document.getElementById("projectCodeLabel"),
    name: document.getElementById("projectNameLabel"),
    headerBadges: document.getElementById("projectHeaderBadges"),
    description: document.getElementById("projectDescriptionLabel"),
    responsible: document.getElementById("projectResponsibleLabel"),
    state: document.getElementById("projectStateLabel"),
    priority: document.getElementById("projectPriorityLabel"),
    startDate: document.getElementById("projectStartDateLabel"),
    expectedDate: document.getElementById("projectExpectedDateLabel"),
    endDate: document.getElementById("projectEndDateLabel"),
    progressFill: document.getElementById("projectProgressBarFill"),
    progressText: document.getElementById("projectProgressText"),
    metricTotal: document.getElementById("projectMetricTotalTasks"),
    metricDone: document.getElementById("projectMetricDoneTasks"),
    metricOpen: document.getElementById("projectMetricOpenTasks"),
    metricProgress: document.getElementById("projectMetricProgress"),
    boardGrid: document.getElementById("projectBoardGrid"),
    onlyMine: document.getElementById("projectOnlyMineTasks"),
    refreshBtn: document.getElementById("projectBoardRefreshBtn"),
    editBtn: document.getElementById("projectEditBtn"),
    newTaskBtn: document.getElementById("projectNewTaskBtn"),

    editModalEl: document.getElementById("projectEditModal"),
    editStamp: document.getElementById("projectEditStamp"),
    editCode: document.getElementById("projectEditCode"),
    editName: document.getElementById("projectEditName"),
    editDescription: document.getElementById("projectEditDescription"),
    editResponsible: document.getElementById("projectEditResponsible"),
    editState: document.getElementById("projectEditState"),
    editPriority: document.getElementById("projectEditPriority"),
    editStartDate: document.getElementById("projectEditStartDate"),
    editExpectedDate: document.getElementById("projectEditExpectedDate"),
    editEndDate: document.getElementById("projectEditEndDate"),
    editStatus: document.getElementById("projectEditStatus"),
    editSaveBtn: document.getElementById("projectEditSaveBtn"),

    taskModalEl: document.getElementById("projectTaskModal"),
    taskModalTitle: document.getElementById("projectTaskModalTitle"),
    taskStamp: document.getElementById("projectTaskStamp"),
    taskTitle: document.getElementById("projectTaskTitle"),
    taskDescription: document.getElementById("projectTaskDescription"),
    taskResponsible: document.getElementById("projectTaskResponsible"),
    taskState: document.getElementById("projectTaskState"),
    taskPriority: document.getElementById("projectTaskPriority"),
    taskDuration: document.getElementById("projectTaskDuration"),
    taskDate: document.getElementById("projectTaskDate"),
    taskHour: document.getElementById("projectTaskHour"),
    taskStatus: document.getElementById("projectTaskStatus"),
    taskSaveBtn: document.getElementById("projectTaskSaveBtn"),
    taskCompleteBtn: document.getElementById("projectTaskCompleteBtn"),
    taskCancelBtn: document.getElementById("projectTaskCancelBtn"),
  };

  const editModal = new bootstrap.Modal(els.editModalEl);
  const taskModal = new bootstrap.Modal(els.taskModalEl);

  const currentUser = String(window.PROJETO_USER || "").trim();

  const esc = (value) =>
    String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;");

  const fmtDate = (value) => {
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

  function chip(icon, label, extraClass = "") {
    return `<span class="proj-chip ${extraClass}"><i class="${icon}"></i><span>${esc(label)}</span></span>`;
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

  function setEditStatus(message, tone = "muted") {
    els.editStatus.className = tone === "danger" ? "text-danger proj-helper" : "proj-helper";
    els.editStatus.textContent = message || "";
  }

  function setTaskStatus(message, tone = "muted") {
    els.taskStatus.className = tone === "danger" ? "text-danger proj-helper" : "proj-helper";
    els.taskStatus.textContent = message || "";
  }

  function usersOptions(selected) {
    return ['<option value="">Seleciona...</option>']
      .concat(
        (state.meta?.users || []).map(
          (item) => `<option value="${esc(item.LOGIN)}" ${String(selected || "") === String(item.LOGIN || "") ? "selected" : ""}>${esc(item.NOME || item.LOGIN)}</option>`
        )
      )
      .join("");
  }

  function stateOptions(selected, type) {
    const items = type === "task" ? (state.meta?.task_states || []) : (state.meta?.project_states || []);
    return items
      .map((item) => `<option value="${item.CODIGO}" ${Number(selected) === Number(item.CODIGO) ? "selected" : ""}>${esc(item.NOME)}</option>`)
      .join("");
  }

  function priorityOptions(selected) {
    return (state.meta?.priorities || [])
      .map((item) => `<option value="${item.CODIGO}" ${Number(selected) === Number(item.CODIGO) ? "selected" : ""}>${esc(item.NOME)}</option>`)
      .join("");
  }

  function syncProjectHeader() {
    const project = state.project;
    if (!project) return;
    els.title.textContent = project.NOME || "Projeto";
    els.breadcrumbs.textContent = `ROADMAP / PROJETOS / ${project.CODIGO || "-"}`;
    els.subtitle.textContent = `Responsavel: ${project.RESPONSAVEL_NOME || project.RESPONSAVEL || "-"} · ${project.TOTAL_TAREFAS || 0} tarefa(s)`;
    els.code.textContent = project.CODIGO || "PROJETO";
    els.name.textContent = project.NOME || "-";
    els.description.textContent = project.DESCRICAO || "Sem descricao registada.";
    els.headerBadges.innerHTML = badge(project.ESTADO_NOME, project.ESTADO_COR) + badge(project.PRIORIDADE_NOME, project.PRIORIDADE_COR);
    els.responsible.textContent = project.RESPONSAVEL_NOME || project.RESPONSAVEL || "-";
    els.state.textContent = project.ESTADO_NOME || "-";
    els.priority.textContent = project.PRIORIDADE_NOME || "-";
    els.startDate.textContent = fmtDate(project.DATAINICIO);
    els.expectedDate.textContent = fmtDate(project.DATAPREVISTA);
    els.endDate.textContent = fmtDate(project.DATAFIM);
    els.metricTotal.textContent = project.TOTAL_TAREFAS || 0;
    els.metricDone.textContent = project.TAREFAS_CONCLUIDAS || 0;
    els.metricOpen.textContent = Math.max((project.TOTAL_TAREFAS || 0) - (project.TAREFAS_CONCLUIDAS || 0), 0);
    els.metricProgress.textContent = `${project.PROGRESSO || 0}%`;
    els.progressFill.style.width = `${project.PROGRESSO || 0}%`;
    els.progressText.textContent = `${project.PROGRESSO || 0}% concluido.`;
  }

  function filteredTasks() {
    if (!els.onlyMine.checked || !currentUser) return [...state.tasks];
    return state.tasks.filter((task) => String(task.UTILIZADOR || "").toUpperCase() === currentUser.toUpperCase());
  }

  function renderBoard() {
    const tasks = filteredTasks();
    const lanes = (state.meta?.task_states || []).slice().sort((a, b) => Number(a.ORDEM || 0) - Number(b.ORDEM || 0));
    els.boardGrid.innerHTML = lanes.map((lane) => {
      const laneTasks = tasks.filter((task) => Number(task.ESTADO) === Number(lane.CODIGO));
      const bodyHtml = laneTasks.length
        ? laneTasks.map((task) => `
            <article class="proj-task-card" data-color="${esc(task.ESTADO_COR || lane.COR)}">
              <div class="proj-task-head">
                <div class="proj-task-name">${esc(task.TAREFA || "-")}</div>
                ${badge(task.PRIORIDADE_NOME, task.PRIORIDADE_COR)}
              </div>
              ${task.DESCRICAO ? `<div class="proj-task-description">${esc(task.DESCRICAO)}</div>` : ""}
              <div class="proj-task-meta">
                ${chip("fa-solid fa-user", task.UTILIZADOR_NOME || task.UTILIZADOR || "-")}
                ${task.DATA ? chip("fa-regular fa-calendar", fmtDate(task.DATA)) : ""}
                ${task.HORA ? chip("fa-regular fa-clock", task.HORA) : ""}
                ${task.DURACAO ? chip("fa-solid fa-hourglass-half", `${task.DURACAO} min`) : ""}
              </div>
              <div class="proj-task-actions">
                <select class="sz_select proj-task-status-select" data-status-id="${esc(task.TAREFASSTAMP)}">
                  ${(state.meta?.task_states || []).map((item) => `<option value="${item.CODIGO}" ${Number(item.CODIGO) === Number(task.ESTADO) ? "selected" : ""}>${esc(item.NOME)}</option>`).join("")}
                </select>
                <button type="button" class="sz_button sz_button_ghost" data-edit-task="${esc(task.TAREFASSTAMP)}" title="Editar">
                  <i class="fa-solid fa-pen"></i>
                </button>
                <button type="button" class="sz_button sz_button_ghost" data-complete-task="${esc(task.TAREFASSTAMP)}" title="Concluir">
                  <i class="fa-solid fa-circle-check"></i>
                </button>
                <button type="button" class="sz_button sz_button_ghost" data-cancel-task="${esc(task.TAREFASSTAMP)}" title="Cancelar">
                  <i class="fa-solid fa-ban"></i>
                </button>
              </div>
            </article>
          `).join("")
        : '<div class="proj-empty">Sem tarefas neste estado.</div>';
      return `
        <section class="proj-lane">
          <div class="proj-lane-head">
            <div class="proj-lane-title">${esc(lane.NOME)}</div>
            <div class="proj-lane-count">${laneTasks.length}</div>
          </div>
          <div class="proj-lane-body">${bodyHtml}</div>
        </section>
      `;
    }).join("");

    els.boardGrid.querySelectorAll("[data-edit-task]").forEach((button) => {
      button.addEventListener("click", () => openTaskModal(button.dataset.editTask));
    });
    els.boardGrid.querySelectorAll("[data-complete-task]").forEach((button) => {
      button.addEventListener("click", () => quickTaskState(button.dataset.completeTask, 4));
    });
    els.boardGrid.querySelectorAll("[data-cancel-task]").forEach((button) => {
      button.addEventListener("click", () => quickTaskState(button.dataset.cancelTask, 5));
    });
    els.boardGrid.querySelectorAll("[data-status-id]").forEach((select) => {
      select.addEventListener("change", () => quickTaskState(select.dataset.statusId, Number(select.value)));
    });
  }

  function fillProjectEditModal() {
    const project = state.project;
    if (!project) return;
    els.editStamp.value = project.PROJSTAMP || "";
    els.editCode.value = project.CODIGO || "";
    els.editName.value = project.NOME || "";
    els.editDescription.value = project.DESCRICAO || "";
    els.editResponsible.innerHTML = usersOptions(project.RESPONSAVEL || "");
    els.editState.innerHTML = stateOptions(project.ESTADO || 1, "project");
    els.editPriority.innerHTML = priorityOptions(project.PRIORIDADE || 2);
    els.editStartDate.value = project.DATAINICIO || "";
    els.editExpectedDate.value = project.DATAPREVISTA || "";
    els.editEndDate.value = project.DATAFIM || "";
    setEditStatus("");
  }

  function taskPayloadFromForm(forceState = null) {
    return {
      TAREFA: els.taskTitle.value,
      DESCRICAO: els.taskDescription.value,
      UTILIZADOR: els.taskResponsible.value,
      DATA: els.taskDate.value,
      HORA: els.taskHour.value,
      DURACAO: els.taskDuration.value,
      ESTADO: forceState ?? els.taskState.value,
      PRIORIDADE: els.taskPriority.value,
    };
  }

  function fillTaskModal(task = null) {
    els.taskStamp.value = task?.TAREFASSTAMP || "";
    els.taskTitle.value = task?.TAREFA || "";
    els.taskDescription.value = task?.DESCRICAO || "";
    els.taskResponsible.innerHTML = usersOptions(task?.UTILIZADOR || "");
    els.taskState.innerHTML = stateOptions(task?.ESTADO || 1, "task");
    els.taskPriority.innerHTML = priorityOptions(task?.PRIORIDADE || 2);
    els.taskDuration.value = task?.DURACAO || 60;
    els.taskDate.value = task?.DATA || "";
    els.taskHour.value = task?.HORA || "";
    els.taskModalTitle.textContent = task?.TAREFASSTAMP ? "Editar tarefa" : "Nova tarefa";
    setTaskStatus("");
  }

  async function loadMeta() {
    const response = await api("/api/projetos/meta");
    state.meta = response.meta || {};
  }

  async function loadProject() {
    setStatus("A carregar projeto...");
    const response = await api(`/api/projetos/${encodeURIComponent(projectStamp)}`);
    state.project = response.project || null;
    state.tasks = response.tasks || [];
    syncProjectHeader();
    renderBoard();
    setStatus("Projeto carregado.");
  }

  async function saveProject() {
    try {
      setEditStatus("A gravar projeto...");
      await api(`/api/projetos/${encodeURIComponent(projectStamp)}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          CODIGO: els.editCode.value,
          NOME: els.editName.value,
          DESCRICAO: els.editDescription.value,
          RESPONSAVEL: els.editResponsible.value,
          ESTADO: els.editState.value,
          PRIORIDADE: els.editPriority.value,
          DATAINICIO: els.editStartDate.value,
          DATAPREVISTA: els.editExpectedDate.value,
          DATAFIM: els.editEndDate.value,
        }),
      });
      editModal.hide();
      await loadProject();
    } catch (error) {
      setEditStatus(error.message || "Erro ao gravar projeto.", "danger");
    }
  }

  async function saveTask(forceState = null) {
    try {
      setTaskStatus("A gravar tarefa...");
      const taskId = els.taskStamp.value.trim();
      const url = taskId
        ? `/api/projetos/${encodeURIComponent(projectStamp)}/tarefas/${encodeURIComponent(taskId)}`
        : `/api/projetos/${encodeURIComponent(projectStamp)}/tarefas`;
      const method = taskId ? "PUT" : "POST";
      await api(url, {
        method,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(taskPayloadFromForm(forceState)),
      });
      taskModal.hide();
      await loadProject();
    } catch (error) {
      setTaskStatus(error.message || "Erro ao gravar tarefa.", "danger");
    }
  }

  async function quickTaskState(taskId, stateCode) {
    const task = state.tasks.find((item) => item.TAREFASSTAMP === taskId);
    if (!task) return;
    try {
      setStatus("A atualizar tarefa...");
      await api(`/api/projetos/${encodeURIComponent(projectStamp)}/tarefas/${encodeURIComponent(taskId)}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          TAREFA: task.TAREFA,
          DESCRICAO: task.DESCRICAO,
          UTILIZADOR: task.UTILIZADOR,
          DATA: task.DATA,
          HORA: task.HORA,
          DURACAO: task.DURACAO,
          ESTADO: stateCode,
          PRIORIDADE: task.PRIORIDADE,
        }),
      });
      await loadProject();
    } catch (error) {
      setStatus(error.message || "Erro ao atualizar tarefa.", "danger");
    }
  }

  function openTaskModal(taskId = "") {
    if (!taskId) {
      fillTaskModal(null);
      taskModal.show();
      return;
    }
    const task = state.tasks.find((item) => item.TAREFASSTAMP === taskId);
    fillTaskModal(task || null);
    taskModal.show();
  }

  els.onlyMine.addEventListener("change", renderBoard);
  els.refreshBtn.addEventListener("click", () => loadProject().catch((error) => setStatus(error.message || "Erro ao carregar projeto.", "danger")));
  els.editBtn.addEventListener("click", () => {
    fillProjectEditModal();
    editModal.show();
  });
  els.newTaskBtn.addEventListener("click", () => openTaskModal(""));
  els.editSaveBtn.addEventListener("click", saveProject);
  els.taskSaveBtn.addEventListener("click", () => saveTask());
  els.taskCompleteBtn.addEventListener("click", () => saveTask(4));
  els.taskCancelBtn.addEventListener("click", () => saveTask(5));

  (async () => {
    try {
      await loadMeta();
      await loadProject();
    } catch (error) {
      setStatus(error.message || "Erro ao iniciar projeto.", "danger");
    }
  })();
});
