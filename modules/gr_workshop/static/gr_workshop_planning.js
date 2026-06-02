(function () {
  const cfg = window.GR_WORKSHOP_PLANNING || {};
  const DAY_START_MINUTES = 8 * 60;
  const DAY_END_MINUTES = 20 * 60;
  const SLOT_MINUTES = 15;
  const MINUTE_HEIGHT = 0.6;

  const state = {
    week: null,
    days: [],
    mechanics: [],
    unplanned: [],
    planned: [],
    dragItem: null,
    isSaving: false,
  };

  const els = {
    page: document.getElementById('grWorkshopPlanningPage'),
    prev: document.getElementById('workshopPlanPrev'),
    next: document.getElementById('workshopPlanNext'),
    today: document.getElementById('workshopPlanToday'),
    refresh: document.getElementById('workshopPlanRefresh'),
    week: document.getElementById('workshopPlanWeek'),
    mechanic: document.getElementById('workshopPlanMechanic'),
    backlog: document.getElementById('workshopPlanBacklog'),
    backlogCount: document.getElementById('workshopPlanBacklogCount'),
    days: document.getElementById('workshopPlanDays'),
    times: document.getElementById('workshopPlanTimes'),
    grid: document.getElementById('workshopPlanGrid'),
  };

  if (!els.page || !cfg.planningUrl || !cfg.planUrlTemplate) return;

  const esc = (value) => String(value ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');

  const todayLocal = () => {
    const d = new Date();
    d.setMinutes(d.getMinutes() - d.getTimezoneOffset());
    return d.toISOString().slice(0, 10);
  };

  const addDays = (isoDate, count) => {
    const [year, month, day] = String(isoDate || todayLocal()).split('-').map(Number);
    const d = new Date(year, month - 1, day);
    d.setDate(d.getDate() + count);
    d.setMinutes(d.getMinutes() - d.getTimezoneOffset());
    return d.toISOString().slice(0, 10);
  };

  const minutesToTime = (minutes) => {
    const safe = Math.max(0, Math.min(23 * 60 + 59, Math.round(minutes || 0)));
    return `${String(Math.floor(safe / 60)).padStart(2, '0')}:${String(safe % 60).padStart(2, '0')}`;
  };

  const timeToMinutes = (value) => {
    const match = String(value || '').match(/^(\d{2}):(\d{2})$/);
    if (!match) return null;
    return Number(match[1]) * 60 + Number(match[2]);
  };

  async function api(url, options = {}) {
    const response = await fetch(url, {
      headers: {
        Accept: 'application/json',
        ...(options.body ? { 'Content-Type': 'application/json' } : {}),
      },
      ...options,
    });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(payload.error || 'Erro inesperado.');
    return payload;
  }

  function toast(message, type = 'success') {
    if (window.showToast) window.showToast(message, type);
    else window.alert(message);
  }

  function planUrl(stamp) {
    return cfg.planUrlTemplate.replace('__STAMP__', encodeURIComponent(stamp));
  }

  function assignMechanicUrl(stamp) {
    return cfg.assignMechanicUrlTemplate.replace('__STAMP__', encodeURIComponent(stamp));
  }

  function cssColor(value) {
    const raw = String(value || '').trim();
    if (/^#[0-9a-f]{3}([0-9a-f]{3})?$/i.test(raw)) return raw;
    if (/^[a-z]+$/i.test(raw)) return raw;
    return '#60A5FA';
  }

  function allItems() {
    return [...state.unplanned, ...state.planned];
  }

  function findItem(stamp) {
    return allItems().find((item) => item.OFICINA_FOLHASTAMP === stamp);
  }

  function jobTitle(item) {
    return item.TRAB_DESCRICAO || item.TRABALHO || 'Trabalho sem descrição';
  }

  function vehicleTitle(item) {
    return item.MATRICULA || item.VEICULO_LABEL || 'Sem matrícula';
  }

  function durationLabel(item) {
    const tempo = Number(item.TEMPO || 0);
    return tempo > 0 ? `${tempo} min` : 'Sem tempo';
  }

  function mechanicLabel(item) {
    return item.MECANICO || 'Sem mecânico';
  }

  function effectiveMechanicStamp(item) {
    return els.mechanic?.value || item?.OFICINA_MECSTAMP || '';
  }

  function setLoading(message = 'A carregar...') {
    els.backlog.innerHTML = `<div class="gr-workshop-plan-empty">${esc(message)}</div>`;
    els.grid.innerHTML = '';
  }

  async function loadPlanning(weekDate) {
    const params = new URLSearchParams();
    params.set('week', weekDate || state.week?.start || todayLocal());
    if (els.mechanic?.value) params.set('mecanico', els.mechanic.value);
    setLoading();
    const payload = await api(`${cfg.planningUrl}?${params.toString()}`);
    state.week = payload.week || {};
    state.days = payload.days || [];
    state.mechanics = payload.mechanics || [];
    state.unplanned = payload.unplanned || [];
    state.planned = payload.planned || [];
    els.week.value = state.week.start || weekDate || todayLocal();
    renderMechanicFilter(payload.mechanic || '');
    render();
  }

  function render() {
    renderDays();
    renderTimes();
    renderBacklog();
    renderGrid();
  }

  function renderDays() {
    els.days.innerHTML = state.days.map((day) => `
      <div class="gr-workshop-day-head${day.weekend ? ' is-weekend' : ''}">
        <strong>${esc(day.weekday)}</strong>
        <span>${esc(day.label)}</span>
      </div>
    `).join('');
  }

  function renderMechanicFilter(selected) {
    if (!els.mechanic) return;
    const current = selected || els.mechanic.value || '';
    els.mechanic.innerHTML = [
      '<option value="">Todos</option>',
      ...state.mechanics.map((item) => `<option value="${esc(item.OFICINA_MECSTAMP)}">${esc(item.NOME)}</option>`),
    ].join('');
    els.mechanic.value = current;
  }

  function renderTimes() {
    const rows = [];
    for (let minute = DAY_START_MINUTES; minute <= DAY_END_MINUTES; minute += 60) {
      rows.push(`
        <div class="gr-workshop-time-row" style="top:${(minute - DAY_START_MINUTES) * MINUTE_HEIGHT}px">
          ${esc(minutesToTime(minute))}
        </div>
      `);
    }
    els.times.innerHTML = rows.join('');
  }

  function renderBacklog() {
    els.backlogCount.textContent = `${state.unplanned.length} ${state.unplanned.length === 1 ? 'trabalho' : 'trabalhos'}`;
    if (!state.unplanned.length) {
      els.backlog.innerHTML = '<div class="gr-workshop-plan-empty">Tudo planeado nesta empresa.</div>';
      return;
    }
    els.backlog.innerHTML = state.unplanned.map((item) => {
      const noTime = Number(item.TEMPO || 0) <= 0;
      const mechanicColor = cssColor(item.MECANICO_COR);
      return `
        <article class="gr-workshop-plan-card${noTime ? ' is-no-time' : ''}" draggable="true" data-stamp="${esc(item.OFICINA_FOLHASTAMP)}" style="--mechanic-color:${esc(mechanicColor)}">
          <strong>#${esc(item.NO || '')} · ${esc(vehicleTitle(item))}</strong>
          <span>${esc(jobTitle(item))}</span>
          <div class="gr-workshop-plan-card-meta">
            <span>${esc(durationLabel(item))}</span>
            <span class="gr-workshop-plan-mechanic">${esc(mechanicLabel(item))}</span>
          </div>
        </article>
      `;
    }).join('');
    els.backlog.querySelectorAll('[data-stamp]').forEach((card) => {
      bindDraggable(card);
      card.addEventListener('click', (event) => {
        event.stopPropagation();
        const item = findItem(card.dataset.stamp);
        if (item) openBacklogMenu(card, item);
      });
    });
  }

  function renderGrid() {
    els.grid.innerHTML = state.days.map((day) => `
      <div class="gr-workshop-day-column${day.weekend ? ' is-weekend' : ''}" data-date="${esc(day.date)}">
        <div class="gr-workshop-drop-indicator" hidden></div>
      </div>
    `).join('');
    els.grid.querySelectorAll('.gr-workshop-day-column').forEach((dayEl) => {
      dayEl.addEventListener('dragenter', (event) => {
        event.preventDefault();
        dayEl.classList.add('is-drop-target');
      });
      dayEl.addEventListener('dragover', (event) => {
        event.preventDefault();
        event.dataTransfer.dropEffect = 'move';
        updateDropIndicator(dayEl, event.clientY);
      });
      dayEl.addEventListener('dragleave', (event) => {
        if (!dayEl.contains(event.relatedTarget)) clearDropIndicator(dayEl);
      });
      dayEl.addEventListener('drop', (event) => handleDrop(event, dayEl));
    });
    renderBlocks();
  }

  function layoutOverlaps(items) {
    const sorted = [...items].sort((a, b) => {
      const aStart = Number(a.PLANNED_START_MINUTES ?? timeToMinutes(a.PLAN_HORAINI) ?? 0);
      const bStart = Number(b.PLANNED_START_MINUTES ?? timeToMinutes(b.PLAN_HORAINI) ?? 0);
      return aStart - bStart || Number(a.NO || 0) - Number(b.NO || 0);
    });
    const layouts = new Map();
    let group = [];
    let groupEnd = -1;

    const flushGroup = () => {
      if (!group.length) return;
      const colEnds = [];
      group.forEach((item) => {
        const start = Number(item.PLANNED_START_MINUTES ?? timeToMinutes(item.PLAN_HORAINI) ?? DAY_START_MINUTES);
        const end = Number(item.PLANNED_END_MINUTES ?? timeToMinutes(item.PLAN_HORAFIM) ?? (start + Number(item.TEMPO || 0)));
        let col = colEnds.findIndex((value) => value <= start);
        if (col === -1) {
          col = colEnds.length;
          colEnds.push(end);
        } else {
          colEnds[col] = end;
        }
        layouts.set(item.OFICINA_FOLHASTAMP, { col, columns: 1 });
      });
      const columns = Math.max(1, colEnds.length);
      group.forEach((item) => {
        const layout = layouts.get(item.OFICINA_FOLHASTAMP);
        layout.columns = columns;
      });
      group = [];
      groupEnd = -1;
    };

    sorted.forEach((item) => {
      const start = Number(item.PLANNED_START_MINUTES ?? timeToMinutes(item.PLAN_HORAINI) ?? DAY_START_MINUTES);
      const end = Number(item.PLANNED_END_MINUTES ?? timeToMinutes(item.PLAN_HORAFIM) ?? (start + Number(item.TEMPO || 0)));
      if (group.length && start >= groupEnd) flushGroup();
      group.push(item);
      groupEnd = Math.max(groupEnd, end);
    });
    flushGroup();
    return layouts;
  }

  function renderBlocks() {
    state.days.forEach((day) => {
      const dayEl = els.grid.querySelector(`[data-date="${CSS.escape(day.date || '')}"]`);
      if (!dayEl) return;
      const dayItems = state.planned.filter((item) => item.PLAN_DATA === day.date);
      const layouts = layoutOverlaps(dayItems);
      dayItems.forEach((item) => {
      const start = Number(item.PLANNED_START_MINUTES ?? timeToMinutes(item.PLAN_HORAINI) ?? DAY_START_MINUTES);
      const tempo = Math.max(0, Number(item.TEMPO || 0));
      const height = Math.max(tempo * MINUTE_HEIGHT, 30);
      const top = Math.max(0, (start - DAY_START_MINUTES) * MINUTE_HEIGHT);
      const layout = layouts.get(item.OFICINA_FOLHASTAMP) || { col: 0, columns: 1 };
      const width = 100 / layout.columns;
      const left = layout.col * width;
      const mechanicColor = cssColor(item.MECANICO_COR);
      const block = document.createElement('article');
      block.className = 'gr-workshop-plan-block';
      block.draggable = true;
      block.dataset.stamp = item.OFICINA_FOLHASTAMP;
      block.style.top = `${top}px`;
      block.style.height = `${height}px`;
      block.style.left = `calc(${left}% + .35rem)`;
      block.style.width = `calc(${width}% - .7rem)`;
      block.style.setProperty('--mechanic-color', mechanicColor);
      block.innerHTML = `
        <strong>#${esc(item.NO || '')} · ${esc(vehicleTitle(item))}</strong>
        <span class="gr-workshop-plan-block-time">${esc(item.PLAN_HORAINI || '')} - ${esc(item.PLAN_HORAFIM || '')}</span>
        <span>${esc(jobTitle(item))}</span>
        <span class="gr-workshop-plan-block-meta">
          <span>${esc(durationLabel(item))}</span>
          <span class="gr-workshop-plan-mechanic">${esc(mechanicLabel(item))}</span>
        </span>
      `;
      bindDraggable(block);
      block.addEventListener('click', (event) => {
        event.stopPropagation();
        openMechanicMenu(block, item);
      });
      dayEl.appendChild(block);
    });
    });
  }

  function closeMechanicMenus() {
    document.querySelectorAll('.gr-workshop-mechanic-menu').forEach((node) => node.remove());
  }

  function openMechanicMenu(block, item) {
    closeMechanicMenus();
    const menu = document.createElement('div');
    menu.className = 'gr-workshop-mechanic-menu';
    const rows = [{ OFICINA_MECSTAMP: '', NOME: 'Sem mecânico', COR: '#94A3B8' }, ...state.mechanics];
    menu.innerHTML = `
      <button type="button" data-action="open">
        <i class="fa-solid fa-arrow-up-right-from-square"></i>
        <span>Abrir</span>
      </button>
      <button type="button" class="is-danger" data-action="unplan">
        <i class="fa-solid fa-calendar-xmark"></i>
        <span>Remover</span>
      </button>
      <div class="gr-workshop-mechanic-menu-separator"></div>
      <div class="gr-workshop-mechanic-menu-title">Mecânico</div>
      ${rows.map((row) => `
        <button type="button" data-mechanic="${esc(row.OFICINA_MECSTAMP || '')}">
          <span class="gr-workshop-mechanic-menu-dot" style="--mechanic-color:${esc(cssColor(row.COR))}"></span>
          <span>${esc(row.NOME || 'Sem mecânico')}</span>
        </button>
      `).join('')}
    `;
    menu.style.left = block.style.left;
    const top = Math.min((Number.parseFloat(block.style.top) || 0) + block.offsetHeight, 360);
    menu.style.top = `${top}px`;
    menu.querySelector('[data-action="open"]')?.addEventListener('click', (event) => {
      event.stopPropagation();
      openSheet(item.OFICINA_FOLHASTAMP);
    });
    menu.querySelector('[data-action="unplan"]')?.addEventListener('click', async (event) => {
      event.stopPropagation();
      await removePlanning(item.OFICINA_FOLHASTAMP);
    });
    menu.querySelectorAll('[data-mechanic]').forEach((button) => {
      button.addEventListener('click', async (event) => {
        event.stopPropagation();
        await assignMechanic(item.OFICINA_FOLHASTAMP, button.dataset.mechanic || '');
      });
    });
    block.parentElement.appendChild(menu);
  }

  function openBacklogMenu(card, item) {
    closeMechanicMenus();
    const menu = document.createElement('div');
    menu.className = 'gr-workshop-mechanic-menu';
    const rows = [{ OFICINA_MECSTAMP: '', NOME: 'Sem mecânico', COR: '#94A3B8' }, ...state.mechanics];
    menu.innerHTML = `
      <button type="button" data-action="open">
        <i class="fa-solid fa-arrow-up-right-from-square"></i>
        <span>Abrir</span>
      </button>
      <div class="gr-workshop-mechanic-menu-separator"></div>
      <div class="gr-workshop-mechanic-menu-title">Mecânico</div>
      ${rows.map((row) => `
        <button type="button" data-mechanic="${esc(row.OFICINA_MECSTAMP || '')}">
          <span class="gr-workshop-mechanic-menu-dot" style="--mechanic-color:${esc(cssColor(row.COR))}"></span>
          <span>${esc(row.NOME || 'Sem mecânico')}</span>
        </button>
      `).join('')}
    `;
    menu.style.left = '.35rem';
    menu.style.top = 'calc(100% - .25rem)';
    menu.querySelector('[data-action="open"]')?.addEventListener('click', (event) => {
      event.stopPropagation();
      openSheet(item.OFICINA_FOLHASTAMP);
    });
    menu.querySelectorAll('[data-mechanic]').forEach((button) => {
      button.addEventListener('click', async (event) => {
        event.stopPropagation();
        await assignMechanic(item.OFICINA_FOLHASTAMP, button.dataset.mechanic || '');
      });
    });
    card.appendChild(menu);
  }

  function openSheet(stamp) {
    if (!stamp || !cfg.sheetPageUrl) return;
    window.location.href = `${cfg.sheetPageUrl}?folha=${encodeURIComponent(stamp)}`;
  }

  async function removePlanning(stamp) {
    if (state.isSaving) return;
    if (!window.confirm('Remover esta folha do planeamento?')) return;
    state.isSaving = true;
    try {
      await api(planUrl(stamp), { method: 'DELETE' });
      toast('Folha removida do planeamento.');
      closeMechanicMenus();
      await loadPlanning(state.week?.start || els.week.value || todayLocal());
    } catch (error) {
      toast(error.message, 'danger');
    } finally {
      state.isSaving = false;
    }
  }

  async function assignMechanic(stamp, mechanicStamp) {
    if (state.isSaving) return;
    state.isSaving = true;
    try {
      await api(assignMechanicUrl(stamp), {
        method: 'PUT',
        body: JSON.stringify({ OFICINA_MECSTAMP: mechanicStamp }),
      });
      toast('Mecânico atribuído.');
      closeMechanicMenus();
      await loadPlanning(state.week?.start || els.week.value || todayLocal());
    } catch (error) {
      toast(error.message, 'danger');
    } finally {
      state.isSaving = false;
    }
  }

  function bindDraggable(node) {
    node.addEventListener('dragstart', (event) => {
      const stamp = node.dataset.stamp;
      state.dragItem = findItem(stamp);
      event.dataTransfer.effectAllowed = 'move';
      event.dataTransfer.setData('text/plain', stamp || '');
    });
    node.addEventListener('dragend', () => {
      state.dragItem = null;
      els.grid.querySelectorAll('.gr-workshop-day-column').forEach(clearDropIndicator);
    });
  }

  function snappedMinutes(dayEl, clientY, tempo) {
    const rect = dayEl.getBoundingClientRect();
    const raw = DAY_START_MINUTES + ((clientY - rect.top) / MINUTE_HEIGHT);
    let minute = Math.round(raw / SLOT_MINUTES) * SLOT_MINUTES;
    const maxStart = DAY_END_MINUTES - tempo;
    if (maxStart < DAY_START_MINUTES) return null;
    minute = Math.max(DAY_START_MINUTES, Math.min(minute, Math.floor(maxStart / SLOT_MINUTES) * SLOT_MINUTES));
    return minute;
  }

  function nextFreeMechanicMinute(dayDate, item, startMinute, tempo) {
    const mechanicStamp = effectiveMechanicStamp(item);
    if (!mechanicStamp) return startMinute;
    const intervals = state.planned
      .filter((planned) => (
        planned.OFICINA_FOLHASTAMP !== item.OFICINA_FOLHASTAMP
        && planned.PLAN_DATA === dayDate
        && planned.OFICINA_MECSTAMP === mechanicStamp
        && planned.PLAN_HORAINI
      ))
      .map((planned) => {
        const start = Number(planned.PLANNED_START_MINUTES ?? timeToMinutes(planned.PLAN_HORAINI) ?? 0);
        const end = Number(
          planned.PLANNED_END_MINUTES
          ?? timeToMinutes(planned.PLAN_HORAFIM)
          ?? (start + Number(planned.TEMPO || 0))
        );
        return { start, end };
      })
      .filter((slot) => slot.end > slot.start)
      .sort((a, b) => a.start - b.start);

    let candidate = startMinute;
    while (true) {
      const candidateEnd = candidate + tempo;
      const collision = intervals.find((slot) => candidate < slot.end && candidateEnd > slot.start);
      if (!collision) return candidate;
      candidate = collision.end;
      if (candidate + tempo > DAY_END_MINUTES) return null;
    }
  }

  function updateDropIndicator(dayEl, clientY) {
    const item = state.dragItem;
    const indicator = dayEl.querySelector('.gr-workshop-drop-indicator');
    if (!item || !indicator) return;
    const tempo = Math.max(0, Number(item.TEMPO || 0));
    const snapped = snappedMinutes(dayEl, clientY, tempo || SLOT_MINUTES);
    const minute = snapped === null ? null : nextFreeMechanicMinute(dayEl.dataset.date, item, snapped, tempo || SLOT_MINUTES);
    if (minute === null) {
      indicator.hidden = true;
      return;
    }
    indicator.hidden = false;
    indicator.style.top = `${(minute - DAY_START_MINUTES) * MINUTE_HEIGHT}px`;
    indicator.style.height = `${Math.max((tempo || SLOT_MINUTES) * MINUTE_HEIGHT, 24)}px`;
    indicator.textContent = minute === snapped ? minutesToTime(minute) : `${minutesToTime(minute)} livre`;
  }

  function clearDropIndicator(dayEl) {
    dayEl.classList.remove('is-drop-target');
    const indicator = dayEl.querySelector('.gr-workshop-drop-indicator');
    if (indicator) indicator.hidden = true;
  }

  async function handleDrop(event, dayEl) {
    event.preventDefault();
    clearDropIndicator(dayEl);
    if (state.isSaving) return;
    const stamp = event.dataTransfer.getData('text/plain') || state.dragItem?.OFICINA_FOLHASTAMP || '';
    const item = findItem(stamp);
    if (!item) return;
    const tempo = Math.max(0, Number(item.TEMPO || 0));
    if (tempo <= 0) {
      toast('Define o TEMPO em minutos antes de planear.', 'warning');
      return;
    }
    const snapped = snappedMinutes(dayEl, event.clientY, tempo);
    const minute = snapped === null ? null : nextFreeMechanicMinute(dayEl.dataset.date, item, snapped, tempo);
    if (minute === null) {
      toast('A duração ultrapassa o horário 08:00-20:00.', 'warning');
      return;
    }
    state.isSaving = true;
    try {
      await api(planUrl(stamp), {
        method: 'PUT',
        body: JSON.stringify({
          PLAN_DATA: dayEl.dataset.date,
          PLAN_HORAINI: minutesToTime(minute),
          ...(els.mechanic?.value ? { OFICINA_MECSTAMP: els.mechanic.value } : {}),
        }),
      });
      toast(minute === snapped ? 'Planeamento gravado.' : `Planeamento ajustado para ${minutesToTime(minute)}.`);
      await loadPlanning(state.week?.start || dayEl.dataset.date);
    } catch (error) {
      toast(error.message, 'danger');
    } finally {
      state.isSaving = false;
      state.dragItem = null;
    }
  }

  function bindEvents() {
    els.prev.addEventListener('click', () => loadPlanning(state.week?.previous || addDays(els.week.value, -7)));
    els.next.addEventListener('click', () => loadPlanning(state.week?.next || addDays(els.week.value, 7)));
    els.today.addEventListener('click', () => loadPlanning(todayLocal()));
    els.refresh.addEventListener('click', () => loadPlanning(state.week?.start || els.week.value || todayLocal()));
    els.week.addEventListener('change', () => loadPlanning(els.week.value || todayLocal()));
    els.mechanic?.addEventListener('change', () => loadPlanning(state.week?.start || els.week.value || todayLocal()));
    document.addEventListener('click', (event) => {
      if (
        !event.target.closest('.gr-workshop-mechanic-menu')
        && !event.target.closest('.gr-workshop-plan-block')
        && !event.target.closest('.gr-workshop-plan-card')
      ) {
        closeMechanicMenus();
      }
    });
  }

  bindEvents();
  loadPlanning(todayLocal()).catch((error) => {
    setLoading(error.message);
    toast(error.message, 'danger');
  });
})();
