// static/js/calendar.js

document.addEventListener('DOMContentLoaded', function() {
  // Ajuste de padding/margens no mobile
  function adjustMobilePadding() {
    const widget = document.querySelector('.widget-calendar');
    const header = widget?.querySelector('.widget-header');
    const body   = widget?.querySelector('.widget-body');
    if (window.innerWidth < 768) {
      widget.style.paddingLeft = '0';
      widget.style.paddingRight = '0';
      header?.classList.replace('px-4', 'px-0');
      body?.classList.replace('px-4', 'px-0');
    } else {
      widget.style.paddingLeft = '';
      widget.style.paddingRight = '';
      header?.classList.replace('px-0', 'px-4');
      body?.classList.replace('px-0', 'px-4');
    }
  }
  window.addEventListener('resize', adjustMobilePadding);
  adjustMobilePadding();

  const CALENDAR_API = '/generic/api/calendar_tasks';
  let now = new Date();
  let currentYear = now.getFullYear();
  let currentMonth = now.getMonth(); // 0 = Janeiro

  // Filtros (mesmo comportamento do Monitor)
  const filtersSummaryEl = document.getElementById('filtersSummary');
  const filtersModalEl = document.getElementById('filtersModal');
  const filtersModal = filtersModalEl ? new bootstrap.Modal(filtersModalEl) : null;
  const btnOpenFilters = document.getElementById('openFilters');
  const btnTabUsers = document.getElementById('filtersTabUsers');
  const btnTabAloj = document.getElementById('filtersTabAloj');
  const btnTabOrigins = document.getElementById('filtersTabOrigins');
  const listContainer = document.getElementById('filtersList');
  const listWrapper = document.querySelector('#filtersModal .filters-list-wrapper');
  const btnApply = document.getElementById('filtersApply');
  const btnClear = document.getElementById('filtersClear');
  const btnAll   = document.getElementById('filtersSelectAll');
  const btnNone  = document.getElementById('filtersSelectNone');
  const notaTarefaModalEl = document.getElementById('notaTarefaModal');
  const notaTarefaModal = notaTarefaModalEl ? bootstrap.Modal.getOrCreateInstance(notaTarefaModalEl) : null;
  const notaTarefaForm = document.getElementById('notaTarefaForm');
  const ntUser = document.getElementById('ntUser');
  const ntData = document.getElementById('ntData');
  const ntHora = document.getElementById('ntHora');
  const ntDuracao = document.getElementById('ntDuracao');
  const ntTarefa = document.getElementById('ntTarefa');
  const ntAloj = document.getElementById('ntAloj');
  const ntGravar = document.getElementById('ntGravar');

  function setFiltersLoading(isLoading) {
    try {
      if (listWrapper) listWrapper.classList.toggle('loading', !!isLoading);
      if (listContainer) listContainer.setAttribute('aria-busy', isLoading ? 'true' : 'false');
    } catch (_) {}
  }

  const CURRENT_USER = window.CURRENT_USER;
  const IS_ADMIN = Number(window.IS_ADMIN || 0) === 1;

  const state = {
    users: new Set([CURRENT_USER]),
    aloj: new Set(),
    origins: new Set(),
  };
  let cacheUsers = null;
  let cacheAloj = null;
  let temp = { users: new Set(), aloj: new Set(), origins: new Set() };
  let tempAll = { users: false, aloj: true, origins: true };
  let currentTab = 'users';

  function normalizeStr(v) { return (v == null ? '' : String(v)).trim(); }

  function updateFiltersSummary() {
    const usersLabel = (state.users.size === 1 && state.users.has(CURRENT_USER))
      ? 'Utilizador: Eu'
      : (state.users.size > 0 ? `Utilizadores: ${state.users.size}` : 'Utilizadores: Todos');
    const alojLabel = state.aloj.size > 0 ? `Aloj.: ${state.aloj.size}` : 'Aloj.: Todos';
    const origLabel = state.origins.size > 0 ? `Origens: ${state.origins.size}` : 'Origens: Todas';
    if (filtersSummaryEl) filtersSummaryEl.textContent = `${usersLabel} • ${alojLabel} • ${origLabel}`;
  }

  async function fetchUsersList() {
    if (!IS_ADMIN) return [CURRENT_USER];
    if (cacheUsers) return cacheUsers;
    try {
      const res = await fetch('/generic/api/US?INATIVO=0');
      if (!res.ok) throw new Error('HTTP ' + res.status);
      const rows = await res.json();
      cacheUsers = rows.map(r => r.LOGIN).filter(Boolean).sort((a,b)=>a.localeCompare(b));
      return cacheUsers;
    } catch (_) {
      cacheUsers = [CURRENT_USER];
      return cacheUsers;
    }
  }

  async function fetchAlojList() {
    if (cacheAloj) return cacheAloj;
    try {
      let nomes = [];
      try {
        const resA = await fetch('/api/alojamentos?basic=1');
        if (!resA.ok) throw new Error('HTTP ' + resA.status);
        const dataA = await resA.json();
        if (dataA && Array.isArray(dataA.rows)) {
          nomes = dataA.rows.map(r => r.NOME).filter(Boolean);
        }
      } catch (_) {
        const res = await fetch('/generic/api/AL?INATIVO=0');
        if (!res.ok) throw new Error('HTTP ' + res.status);
        const rows = await res.json();
        nomes = rows.map(r => r.NOME).filter(Boolean);
      }
      nomes.sort((a,b)=>a.localeCompare(b));
      cacheAloj = [''].concat(nomes);
      return cacheAloj;
    } catch (_) {
      cacheAloj = [''];
      return cacheAloj;
    }
  }

  function renderCards(items, type) {
    if (!listContainer) return;
    listContainer.innerHTML = '';
    items.forEach(val => {
      const card = document.createElement('div');
      card.className = 'select-card';
      card.style.minHeight = '36px';
      const key = normalizeStr(val);
      let label = key;
      if (type === 'aloj' && key === '') label = 'Sem alojamento';
      if (type === 'origins') {
        const map = { 'MN': 'Manutenção', 'LP': 'Limpeza', 'FS': 'Faltas', '': 'Tarefas' };
        label = map[key] || key;
      }
      card.textContent = label;

      const markSelected = (tempAll[type] === true) || (temp[type] && temp[type].has(key));
      if (markSelected) card.classList.add('selected');

      card.addEventListener('click', () => {
        const sel = card.classList.toggle('selected');
        if (tempAll[type] === true) {
          tempAll[type] = false;
          temp[type] = new Set(items.map(v => normalizeStr(v)));
        }
        if (!temp[type]) temp[type] = new Set();
        if (sel) temp[type].add(key); else temp[type].delete(key);
      });

      listContainer.appendChild(card);
    });
  }

  async function showTab(tab) {
    setFiltersLoading(true);
    currentTab = tab;
    if (btnTabUsers) btnTabUsers.classList.toggle('active', tab === 'users');
    if (btnTabAloj) btnTabAloj.classList.toggle('active', tab === 'aloj');
    if (btnTabOrigins) btnTabOrigins.classList.toggle('active', tab === 'origins');
    try {
      if (tab === 'users') {
        const users = await fetchUsersList();
        renderCards(users, 'users');
      } else if (tab === 'aloj') {
        const aloj = await fetchAlojList();
        renderCards(aloj, 'aloj');
      } else {
        const origins = ['MN', 'LP', 'FS', ''];
        renderCards(origins, 'origins');
      }
    } finally {
      setFiltersLoading(false);
    }
  }

  async function openFiltersModal() {
    if (state.users.size === 0) { tempAll.users = true; temp.users = new Set(); } else { tempAll.users = false; temp.users = new Set(state.users); }
    if (state.aloj.size === 0) { tempAll.aloj = true; temp.aloj = new Set(); } else { tempAll.aloj = false; temp.aloj = new Set(state.aloj); }
    if (state.origins.size === 0) { tempAll.origins = true; temp.origins = new Set(); } else { tempAll.origins = false; temp.origins = new Set(state.origins); }
    await showTab(currentTab || 'users');
    if (filtersModal) filtersModal.show();
  }

  function nextHalfHour() {
    const dt = new Date();
    dt.setMinutes(dt.getMinutes() < 30 ? 30 : 60, 0, 0);
    return `${String(dt.getHours()).padStart(2, '0')}:${String(dt.getMinutes()).padStart(2, '0')}`;
  }

  async function fillNovaTarefaCombos() {
    if (ntUser) {
      const users = await fetchUsersList();
      ntUser.innerHTML = users.map(login => `<option value="${login}">${login}</option>`).join('');
      ntUser.value = CURRENT_USER || users[0] || '';
    }
    if (ntAloj) {
      const alojList = await fetchAlojList();
      ntAloj.innerHTML =
        '<option value="">(Sem alojamento)</option>' +
        alojList
          .filter(nome => nome !== '')
          .map(nome => `<option value="${nome}">${nome}</option>`)
          .join('');
      ntAloj.value = '';
    }
  }

  async function openNovaTarefaModal(dateIso) {
    if (!notaTarefaModal) return;
    try {
      await fillNovaTarefaCombos();
    } catch (_) {}
    if (ntData) ntData.value = dateIso || toLocalIso(new Date());
    if (ntHora) ntHora.value = nextHalfHour();
    if (ntDuracao) ntDuracao.value = 60;
    if (ntTarefa) ntTarefa.value = '';
    notaTarefaModal.show();
    setTimeout(() => {
      try { ntTarefa?.focus(); } catch (_) {}
    }, 120);
  }

  // Tarefas carregadas para o intervalo atual
  let loadedTasks = [];

  const monthNames = [
    'Janeiro','Fevereiro','Março','Abril','Maio','Junho',
    'Julho','Agosto','Setembro','Outubro','Novembro','Dezembro'
  ];

  // Utility: formata uma Date em 'YYYY-MM-DD' no fuso local
  function toLocalIso(d) {
    return [
      d.getFullYear(),
      String(d.getMonth() + 1).padStart(2, '0'),
      String(d.getDate()).padStart(2, '0')
    ].join('-');
  }

  function loadCalendar(year, month) {
    const firstDay = new Date(year, month, 1);
    const lastDay  = new Date(year, month + 1, 0);

    // calcula início e fim para preencher toda a semana (começa no Domingo)
    const weekdayMon0 = (d) => (d.getDay() + 6) % 7;
    const shiftStart = weekdayMon0(firstDay);
    const startDate  = new Date(firstDay);
    startDate.setDate(firstDay.getDate() - shiftStart);

    const shiftEnd = 6 - weekdayMon0(lastDay);
    const endDate  = new Date(lastDay);
    endDate.setDate(lastDay.getDate() + shiftEnd);

    document.getElementById('month-year').textContent = `${monthNames[month]} de ${year}`;
    clearError();

    const startStr = toLocalIso(startDate);
    const endStr   = toLocalIso(endDate);

    fetch(`${CALENDAR_API}?start=${startStr}&end=${endStr}`)
      .then(res => { if (!res.ok) throw new Error(res.status + ' ' + res.statusText); return res.json(); })
      .then(tasks => { loadedTasks = Array.isArray(tasks) ? tasks : []; renderCalendar(startDate, endDate, loadedTasks); })
      .catch(err => showError(`Erro ao carregar dados: ${err.message}`));
  }

  function showError(msg) {
    let errEl = document.getElementById('calendar-error');
    if (!errEl) {
      errEl = document.createElement('div');
      errEl.id = 'calendar-error';
      errEl.className = 'text-danger mb-3';
      document.querySelector('.container-fluid').prepend(errEl);
    }
    errEl.textContent = msg;
    const tbody = document.getElementById('calendar-body');
    if (tbody) tbody.innerHTML = '';
  }

  function clearError() {
    const errEl = document.getElementById('calendar-error');
    if (errEl) errEl.remove();
  }

  function renderCalendar(startDate, endDate, tasks) {
    clearError();
    const tbody = document.getElementById('calendar-body');
    tbody.innerHTML = '';

    let cursor = new Date(startDate);
    const todayIso = toLocalIso(new Date());
    const totalDays = Math.floor((endDate.getTime() - startDate.getTime()) / 86400000) + 1;
    const totalRows = Math.ceil(totalDays / 7);
    for (let r = 0; r < totalRows; r++) {
      const tr = document.createElement('tr');
      for (let c = 0; c < 7; c++) {
        // guarda data específica desta célula
        const cellDate = new Date(cursor);
        const cellIso = toLocalIso(cellDate);

        const td = document.createElement('td');
        td.className = 'align-top p-1 droppable-cell day-cell';
        if (cellIso === todayIso) td.classList.add('today');
        if (cellDate.getMonth() !== currentMonth) td.classList.add('other-month');

        td.addEventListener('dragover', e => e.preventDefault());
        td.addEventListener('drop', e => {
          e.preventDefault();
          const stamp = e.dataTransfer.getData('text/plain');
          const newDate = toLocalIso(cellDate);
          fetch(`/generic/api/TAREFAS/${stamp}`, {
            method: 'PUT',
            headers: {'Content-Type':'application/json'},
            body: JSON.stringify({DATA: newDate})
          }).then(() => loadCalendar(currentYear, currentMonth));
        });
        td.addEventListener('click', (e) => {
          if (e.target.closest('.cal-task-chip')) return;
          openNovaTarefaModal(cellIso);
        });

        const dayDiv = document.createElement('div');
        dayDiv.className = 'day-number';
        dayDiv.textContent = cellDate.getDate();
        td.appendChild(dayDiv);

        // filtra tasks usando data local da célula
        const iso = cellIso;
        const usersSet = state.users; // vazio => todos
        const alojSet = state.aloj;   // vazio => todos
        const origSet = state.origins; // vazio => todas

        const baseTasks = (tasks || []).filter(t => t.DATA === iso);

        const matches = (t) => {
          const u = normalizeStr(t.UTILIZADOR);
          const a = normalizeStr(t.ALOJAMENTO);
          const o = normalizeStr(t.ORIGEM).toUpperCase();
          if (usersSet.size > 0 && !usersSet.has(u)) return false;
          if (alojSet.size > 0) {
            const aval = a === '' ? '' : a;
            if (!alojSet.has(aval)) return false;
          }
          if (origSet.size > 0) {
            const oval = o === '' ? '' : o;
            if (!origSet.has(oval)) return false;
          }
          return true;
        };

        const initiallyMatched = baseTasks.filter(matches);

        const lpPairs = new Set();
        if (usersSet.size > 0) {
          for (const t of baseTasks) {
            const u = normalizeStr(t.UTILIZADOR);
            const a = normalizeStr(t.ALOJAMENTO);
            const o = normalizeStr(t.ORIGEM).toUpperCase();
            if (!usersSet.has(u)) continue;
            if (alojSet.size > 0 && !alojSet.has(a === '' ? '' : a)) continue;
            if (t.DATA === iso && o === 'LP') {
              lpPairs.add(`${t.DATA}||${a}`);
            }
          }
        }
        const includeOrigins = (origSet.size === 0) ? new Set(['MN','FS']) : new Set(Array.from(origSet).filter(x => x === 'MN' || x === 'FS'));
        const extra = [];
        if (lpPairs.size > 0 && includeOrigins.size > 0) {
          const seen = new Set();
          for (const t of baseTasks) {
            const a = normalizeStr(t.ALOJAMENTO);
            const o = normalizeStr(t.ORIGEM).toUpperCase();
            const keyPair = `${t.DATA}||${a}`;
            if (!lpPairs.has(keyPair)) continue;
            if (!includeOrigins.has(o)) continue;
            if (alojSet.size > 0 && !alojSet.has(a === '' ? '' : a)) continue;
            const k = `${o}|${t.DATA}|${t.HORA || ''}|${a}|${t.TAREFA || ''}|${normalizeStr(t.UTILIZADOR)}`;
            if (seen.has(k)) continue;
            seen.add(k);
            extra.push(t);
          }
        }
        const finalTasks = initiallyMatched.concat(extra);

        finalTasks.forEach(t => {
          const div = document.createElement('div');
          div.className = 'cal-task-chip';
          div.draggable = true;
          div.addEventListener('dragstart', e => {
            e.dataTransfer.setData('text/plain', t.TAREFASSTAMP);
          });

          let content = '';
          if (t.TRATADO) {
            content += '<span class="me-1"><i class="fa-solid fa-check" style="color:#ffffff;"></i></span>';
          }
          const trailer = t.TAREFA.length > 20 ? t.TAREFA.slice(0,20) + '…' : t.TAREFA;
          if (t.ALOJAMENTO?.trim()) {
            content += `<strong>${t.ALOJAMENTO}</strong><br>${t.HORA} : ${trailer}`;
          } else {
            content += `${t.HORA} : ${trailer}`;
          }
          div.innerHTML = content;

          div.style.backgroundColor = t.COR || '#333333';
          div.onclick = (e) => {
            e.stopPropagation();
            window.location.href = `/generic/form/TAREFAS/${t.TAREFASSTAMP}?return_to=/generic/view/calendar/`;
          };
          td.appendChild(div);
        });

        tr.appendChild(td);
        // avança cursor para o próximo dia
        cursor.setDate(cursor.getDate() + 1);
      }
      tbody.appendChild(tr);
    }
  }

  // navegação mês a mês
  document.getElementById('prev-month').onclick = () => {
    if (currentMonth === 0) { currentMonth = 11; currentYear--; } else { currentMonth--; }
    loadCalendar(currentYear, currentMonth);
  };
  document.getElementById('next-month').onclick = () => {
    if (currentMonth === 11) { currentMonth = 0; currentYear++; } else { currentMonth++; }
    loadCalendar(currentYear, currentMonth);
  };

  // Listeners do modal de filtros
  if (btnOpenFilters) btnOpenFilters.addEventListener('click', openFiltersModal);
  if (btnTabUsers) btnTabUsers.addEventListener('click', () => showTab('users'));
  if (btnTabAloj) btnTabAloj.addEventListener('click', () => showTab('aloj'));
  if (btnTabOrigins) btnTabOrigins.addEventListener('click', () => showTab('origins'));
  if (btnClear) btnClear.addEventListener('click', async () => {
    tempAll.users = false; temp.users = new Set([CURRENT_USER]);
    await fetchAlojList(); tempAll.aloj = true; temp.aloj = new Set();
    tempAll.origins = true; temp.origins = new Set();
    await showTab(currentTab);
  });
  if (btnAll) btnAll.addEventListener('click', async () => {
    if (currentTab === 'users') {
      const users = await fetchUsersList();
      tempAll.users = true; temp.users = new Set();
      renderCards(users, 'users');
    } else if (currentTab === 'aloj') {
      const aloj = await fetchAlojList();
      tempAll.aloj = true; temp.aloj = new Set();
      renderCards(aloj, 'aloj');
    } else {
      const origins = ['MN','LP','FS',''];
      tempAll.origins = true; temp.origins = new Set();
      renderCards(origins, 'origins');
    }
  });
  if (btnNone) btnNone.addEventListener('click', async () => {
    if (currentTab === 'users') {
      tempAll.users = false; temp.users = new Set();
      const users = await fetchUsersList();
      renderCards(users, 'users');
    } else if (currentTab === 'aloj') {
      tempAll.aloj = false; temp.aloj = new Set();
      const aloj = await fetchAlojList();
      renderCards(aloj, 'aloj');
    } else {
      tempAll.origins = false; temp.origins = new Set();
      const origins = ['MN','LP','FS',''];
      renderCards(origins, 'origins');
    }
  });
  if (btnApply) btnApply.addEventListener('click', () => {
    state.users = tempAll.users ? new Set() : new Set(temp.users);
    state.aloj = tempAll.aloj ? new Set() : new Set(temp.aloj);
    state.origins = tempAll.origins ? new Set() : new Set(temp.origins);
    if (filtersModal) filtersModal.hide();
    updateFiltersSummary();
    // recalcula o intervalo completo (semana inteira) para manter o alinhamento correto
    const firstDay = new Date(currentYear, currentMonth, 1);
    const lastDay  = new Date(currentYear, currentMonth + 1, 0);
    const weekdayMon0 = (d) => (d.getDay() + 6) % 7;
    const shiftStart = weekdayMon0(firstDay);
    const startDate = new Date(firstDay);
    startDate.setDate(firstDay.getDate() - shiftStart);
    const shiftEnd = 6 - weekdayMon0(lastDay);
    const endDate = new Date(lastDay);
    endDate.setDate(lastDay.getDate() + shiftEnd);
    renderCalendar(startDate, endDate, loadedTasks || []);
  });

  if (notaTarefaForm) {
    notaTarefaForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const user = ntUser?.value || CURRENT_USER || '';
      const data = ntData?.value || '';
      const hora = ntHora?.value || '';
      const dur = parseInt(ntDuracao?.value || '60', 10);
      const tarefa = ntTarefa?.value?.trim() || '';
      const aloj = ntAloj?.value || '';

      if (!tarefa) { alert('Indica a descrição da tarefa.'); return; }
      if (!data || !hora || !Number.isFinite(dur) || dur <= 0) { alert('Verifica data, hora e duração.'); return; }

      if (ntGravar) ntGravar.disabled = true;
      try {
        const resp = await fetch('/generic/api/tarefas/nova', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            UTILIZADOR: user,
            DATA: data,
            HORA: hora,
            DURACAO: dur,
            TAREFA: tarefa,
            ALOJAMENTO: aloj
          })
        });
        const js = await resp.json().catch(() => ({}));
        if (!resp.ok || js.ok === false) throw new Error(js.error || 'Falha ao criar tarefa');
        if (notaTarefaModal) notaTarefaModal.hide();
        loadCalendar(currentYear, currentMonth);
      } catch (err) {
        alert(err.message || 'Erro ao criar tarefa');
      } finally {
        if (ntGravar) ntGravar.disabled = false;
      }
    });
  }

  // Resumo inicial
  updateFiltersSummary();

  loadCalendar(currentYear, currentMonth);
});
