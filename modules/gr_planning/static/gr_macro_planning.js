(function () {
  const config = window.GR_MACRO_PLANNING || {};
  const weeks = Array.isArray(config.weeks) && config.weeks.length ? config.weeks : Array.from({ length: 52 }, (_, idx) => idx + 1);

  const grid = document.querySelector('.gr-macro-grid');
  const emptyState = document.getElementById('grMacroEmpty');
  const saveBtn = document.getElementById('grMacroSave');
  const statusEl = document.getElementById('grMacroStatus');
  const yearSelect = document.getElementById('grMacroYear');

  if (!grid) return;

  const escapeHtml = (value) => String(value ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');

  const isColorValue = (value) => {
    const raw = String(value || '').trim();
    return /^#[0-9a-f]{3}([0-9a-f]{3})?$/i.test(raw)
      || /^rgb(a)?\(/i.test(raw)
      || /^hsl(a)?\(/i.test(raw);
  };

  const safeColor = (value) => (isColorValue(value) ? String(value).trim() : '#d8dee8');

  const textColorFor = (value) => {
    const color = safeColor(value);
    const hex = color.startsWith('#') ? color.slice(1) : '';
    if (hex.length !== 3 && hex.length !== 6) return '#fff';
    const full = hex.length === 3 ? hex.split('').map((ch) => ch + ch).join('') : hex;
    const r = parseInt(full.slice(0, 2), 16);
    const g = parseInt(full.slice(2, 4), 16);
    const b = parseInt(full.slice(4, 6), 16);
    return ((r * 299 + g * 587 + b * 114) / 1000) > 150 ? '#162033' : '#fff';
  };

  const createCell = (className, content) => {
    const cell = document.createElement('div');
    cell.className = className;
    cell.innerHTML = content;
    return cell;
  };

  const showToastMessage = (message, type = 'success') => {
    if (window.showToast) {
      window.showToast(message, type);
      return;
    }
    window.alert(message);
  };

  const cssEscape = (value) => {
    if (window.CSS?.escape) return window.CSS.escape(String(value));
    return String(value).replace(/["\\]/g, '\\$&');
  };

  const clamp = (value, min, max) => Math.max(min, Math.min(max, value));

  const weekFromPointer = (timeline, clientX) => {
    const firstCell = timeline.querySelector('.gr-macro-week-cell');
    if (!firstCell) return 1;
    const cellRect = firstCell.getBoundingClientRect();
    const timelineRect = timeline.getBoundingClientRect();
    const cellWidth = cellRect.width || 1;
    return clamp(Math.floor((clientX - timelineRect.left) / cellWidth) + 1, 1, weeks.length);
  };

  const initialsFromLabel = (label) => {
    const words = String(label || '')
      .trim()
      .split(/\s+/)
      .filter(Boolean);
    if (!words.length) return '';
    return words.map((word) => word.charAt(0).toUpperCase()).join('');
  };

  const barLabelHtml = (label) => `
    <button type="button" class="gr-macro-bar-handle gr-macro-bar-handle-start" data-bar-handle="start" aria-label="Ajustar inicio"></button>
    <span>${escapeHtml(label)}</span>
    <button type="button" class="gr-macro-bar-handle gr-macro-bar-handle-end" data-bar-handle="end" aria-label="Ajustar fim"></button>
  `;

  const updateBarLabel = (bar) => {
    const label = bar.dataset.label || bar.dataset.supervisor || '';
    const shortLabel = bar.dataset.shortLabel || initialsFromLabel(label);
    const span = bar.querySelector('span');
    if (!span) return;
    span.textContent = label;
    window.requestAnimationFrame(() => {
      span.textContent = span.scrollWidth > span.clientWidth + 1 ? shortLabel : label;
    });
  };

  const syncBarGeometry = (bar, startWeek, endWeek) => {
    const safeStart = clamp(Number(startWeek) || 1, 1, weeks.length);
    const safeEnd = clamp(Number(endWeek) || safeStart, safeStart, weeks.length);
    const duration = safeEnd - safeStart + 1;
    const label = bar.dataset.label || bar.dataset.supervisor || bar.textContent.trim();
    bar.dataset.startWeek = String(safeStart);
    bar.dataset.endWeek = String(safeEnd);
    bar.style.setProperty('--start-week', String(safeStart));
    bar.style.setProperty('--duration-weeks', String(duration));
    bar.title = `${label} - S${safeStart} a S${safeEnd}`;
    updateBarLabel(bar);
  };

  const rangesOverlap = (startA, endA, startB, endB) => startA <= endB && startB <= endA;

  const timelineRangeHasOverlap = (timeline, startWeek, endWeek, ignoreBar = null) => {
    if (!timeline) return false;
    return Array.from(timeline.querySelectorAll('.gr-macro-bar')).some((bar) => {
      if (ignoreBar && bar === ignoreBar) return false;
      const barStart = Number(bar.dataset.startWeek || 0);
      const barEnd = Number(bar.dataset.endWeek || barStart);
      return rangesOverlap(startWeek, endWeek, barStart, barEnd);
    });
  };

  const plannedWorks = new Set(
    Array.from(grid.querySelectorAll('[data-processo]'))
      .map((el) => String(el.dataset.processo || '').trim())
      .filter(Boolean)
  );
  const selectedTeams = new Map();
  const selectedSupervisors = new Map();
  let activeTeamCell = null;
  let activeWeekSelection = null;
  let activeBarDrag = null;
  let activeBarMenu = null;
  let isDirty = false;
  let isSaving = false;

  const setStatus = (message) => {
    if (statusEl) statusEl.textContent = message;
  };

  const setDirty = (dirty) => {
    isDirty = !!dirty;
    if (saveBtn) saveBtn.disabled = isSaving || !isDirty;
    setStatus(isDirty ? 'Alteracoes por gravar.' : 'Planeamento guardado.');
  };

  const rowElements = (processo) => Array.from(
    grid.querySelectorAll(`[data-processo="${cssEscape(processo)}"]`)
  );

  const updateEmptyState = () => {
    const hasRows = !!grid.querySelector('.gr-macro-timeline');
    emptyState?.classList.toggle('is-hidden', hasRows);
  };

  const updateRowDuration = (timeline) => {
    if (!timeline) return 0;
    const weeksSet = new Set();
    timeline.querySelectorAll('.gr-macro-bar').forEach((bar) => {
      const start = Number(bar.dataset.startWeek || 0);
      const end = Number(bar.dataset.endWeek || start);
      for (let week = start; week <= end; week += 1) weeksSet.add(week);
    });
    const duration = weeksSet.size;
    const processo = timeline.dataset.processo || '';
    const durationCell = grid.querySelector(`.gr-macro-col-duracao[data-processo="${cssEscape(processo)}"]`);
    if (durationCell) {
      durationCell.dataset.duration = String(duration);
      durationCell.textContent = duration ? `${duration} sem.` : '-';
    }
    return duration;
  };

  const closeBarMenu = () => {
    activeBarMenu?.remove();
    activeBarMenu = null;
  };

  const openBarMenu = (bar, clientX, clientY) => {
    closeBarMenu();
    activeBarMenu = document.createElement('div');
    activeBarMenu.className = 'gr-macro-bar-menu';
    activeBarMenu.innerHTML = `
      <button type="button" class="gr-macro-bar-menu-delete">
        <i class="fa-solid fa-trash"></i>
        <span>Eliminar</span>
      </button>
    `;
    activeBarMenu.querySelector('.gr-macro-bar-menu-delete')?.addEventListener('click', () => {
      const timeline = bar.closest('.gr-macro-timeline');
      bar.remove();
      updateRowDuration(timeline);
      setDirty(true);
      closeBarMenu();
    });
    document.body.appendChild(activeBarMenu);

    const menuRect = activeBarMenu.getBoundingClientRect();
    const left = clamp(clientX, 8, window.innerWidth - menuRect.width - 8);
    const top = clamp(clientY + 8, 8, window.innerHeight - menuRect.height - 8);
    activeBarMenu.style.left = `${left}px`;
    activeBarMenu.style.top = `${top}px`;
  };

  const normalizeWork = (work) => ({
    id: String(work?.processo || work?.id || work?.code || '').trim(),
    code: String(work?.processo || work?.code || work?.id || '').trim(),
    description: String(work?.descricao || work?.description || '').trim(),
  });

  const normalizeTeam = (team) => ({
    id: String(team?.codigo || '').trim(),
    code: String(team?.codigo || '').trim(),
    description: String(team?.nome || '').trim(),
    color: safeColor(team?.cor || '#d8dee8'),
  });

  const normalizeSupervisor = (supervisor) => ({
    id: String(supervisor?.nome || '').trim(),
    code: String(supervisor?.nome || '').trim(),
    description: '',
    color: safeColor(supervisor?.cor || '#d8dee8'),
  });

  const addWorkToPlanning = (work) => {
    const row = normalizeWork(work);
    if (!row.id || plannedWorks.has(row.id)) return;
    plannedWorks.add(row.id);

    const obra = createCell(
      'gr-macro-cell gr-macro-sticky gr-macro-col-obra',
      `<div class="gr-macro-work-title">
        <strong>${escapeHtml(row.code)}</strong>
        <button type="button" class="gr-macro-row-delete" aria-label="Remover obra">
          <i class="fa-solid fa-trash"></i>
        </button>
      </div>
      <span>${escapeHtml(row.description || 'Sem descricao')}</span>`
    );
    obra.dataset.processo = row.id;
    obra.dataset.description = row.description || '';

    const quantidade = createCell('gr-macro-cell gr-macro-sticky gr-macro-col-quantidade', '-');
    quantidade.dataset.processo = row.id;
    quantidade.dataset.qtt = '';
    const equipa = createCell(
      'gr-macro-cell gr-macro-sticky gr-macro-col-equipa gr-macro-team-cell',
      '<span class="gr-macro-team gr-macro-tone-muted">-</span>'
    );
    equipa.dataset.processo = row.id;
    equipa.setAttribute('role', 'button');
    equipa.setAttribute('tabindex', '0');
    const duracao = createCell('gr-macro-cell gr-macro-sticky gr-macro-col-duracao', '-');
    duracao.dataset.processo = row.id;
    duracao.dataset.duration = '0';
    const timeline = document.createElement('div');
    timeline.className = 'gr-macro-timeline';
    timeline.dataset.processo = row.id;

    weeks.forEach((week) => {
      const weekCell = document.createElement('div');
      weekCell.className = 'gr-macro-week-cell';
      weekCell.dataset.week = String(week);
      weekCell.style.setProperty('--week', String(week));
      timeline.appendChild(weekCell);
    });

    grid.insertBefore(obra, emptyState);
    grid.insertBefore(quantidade, emptyState);
    grid.insertBefore(equipa, emptyState);
    grid.insertBefore(duracao, emptyState);
    grid.insertBefore(timeline, emptyState);
    updateEmptyState();
    setDirty(true);
  };

  const createLookupModal = ({
    openBtnId,
    modalId,
    closeTopBtnId,
    closeBtnId,
    confirmBtnId,
    searchInputId,
    resultsId,
    statusId,
    selectedCountId,
    url,
    normalizer,
    selectedStore,
    disabledStore,
    itemLabelSingular,
    itemLabelPlural,
    emptyMessage,
    searchError,
    initialMessage,
    renderColor = false,
    multi = true,
    searchOnOpen = false,
    selectedAdjectiveSingular = 'selecionada',
    selectedAdjectivePlural = 'selecionadas',
    onClose = null,
    onConfirm,
  }) => {
    const openBtn = document.getElementById(openBtnId);
    const modal = document.getElementById(modalId);
    const closeTopBtn = document.getElementById(closeTopBtnId);
    const closeBtn = document.getElementById(closeBtnId);
    const confirmBtn = document.getElementById(confirmBtnId);
    const searchInput = document.getElementById(searchInputId);
    const resultsHost = document.getElementById(resultsId);
    const statusEl = document.getElementById(statusId);
    const selectedCountEl = document.getElementById(selectedCountId);

    if (!modal || !confirmBtn || !searchInput || !resultsHost) return null;

    let searchTimer = null;
    let lastController = null;

    const setStatus = (message) => {
      if (statusEl) statusEl.textContent = message || '';
    };

    const updateSelectedCount = () => {
      const total = selectedStore.size;
      if (selectedCountEl) {
        selectedCountEl.textContent = `${total} ${total === 1 ? itemLabelSingular : itemLabelPlural} ${total === 1 ? selectedAdjectiveSingular : selectedAdjectivePlural}`;
      }
      confirmBtn.disabled = total === 0;
    };

    const closeModal = () => {
      modal.classList.remove('is-open');
      modal.setAttribute('aria-hidden', 'true');
      if (lastController) lastController.abort();
      if (typeof onClose === 'function') onClose();
    };

    const openModal = () => {
      selectedStore.clear();
      updateSelectedCount();
      modal.classList.add('is-open');
      modal.setAttribute('aria-hidden', 'false');
      resultsHost.innerHTML = '';
      setStatus(initialMessage);
      searchInput.value = '';
      window.setTimeout(() => searchInput.focus(), 50);
      if (searchOnOpen) searchItems();
    };

    const renderResults = (rows) => {
      const usableRows = (rows || []).map(normalizer).filter((row) => row.id);
      if (!usableRows.length) {
        resultsHost.innerHTML = '';
        setStatus(emptyMessage);
        return;
      }
      resultsHost.innerHTML = usableRows.map((row) => {
        const disabled = disabledStore?.has(row.id);
        const selectedClass = selectedStore.has(row.id) ? ' is-selected' : '';
        const color = renderColor ? safeColor(row.color) : '';
        return `
          <button
            type="button"
            class="gr-macro-work-option${renderColor ? ' has-color-preview' : ''}${selectedClass}"
            data-id="${escapeHtml(row.id)}"
            data-code="${escapeHtml(row.code)}"
            data-description="${escapeHtml(row.description)}"
            data-color="${escapeHtml(color)}"
            ${disabled ? 'disabled' : ''}>
            <span class="gr-macro-work-check"><i class="fa-solid fa-check"></i></span>
            ${renderColor ? `<span class="gr-macro-color-preview" style="--team-color:${escapeHtml(color)}"></span>` : ''}
            <span class="gr-macro-work-main">
              <span class="gr-macro-work-code">${escapeHtml(row.code)}${disabled ? ' - ja no planeamento' : ''}</span>
              <span class="gr-macro-work-description">${escapeHtml(row.description || 'Sem descricao')}</span>
            </span>
          </button>
        `;
      }).join('');
      setStatus(`${usableRows.length} ${usableRows.length === 1 ? itemLabelSingular : itemLabelPlural} encontradas.`);
    };

    const searchItems = async () => {
      const term = String(searchInput.value || '').trim();
      if (lastController) lastController.abort();
      lastController = new AbortController();
      setStatus('A pesquisar...');
      try {
        const response = await fetch(`${url}?q=${encodeURIComponent(term)}`, {
          headers: { Accept: 'application/json' },
          signal: lastController.signal,
        });
        const payload = await response.json().catch(() => ({}));
        if (!response.ok) throw new Error(payload.error || searchError);
        renderResults(payload.rows || []);
      } catch (error) {
        if (error.name === 'AbortError') return;
        resultsHost.innerHTML = '';
        setStatus(error.message || searchError);
      }
    };

    openBtn?.addEventListener('click', openModal);
    closeTopBtn?.addEventListener('click', closeModal);
    closeBtn?.addEventListener('click', closeModal);
    searchInput.addEventListener('input', () => {
      window.clearTimeout(searchTimer);
      searchTimer = window.setTimeout(searchItems, 220);
    });

    resultsHost.addEventListener('click', (event) => {
      const option = event.target.closest('.gr-macro-work-option');
      if (!option || option.disabled) return;
      const item = {
        id: String(option.dataset.id || '').trim(),
        code: String(option.dataset.code || '').trim(),
        description: String(option.dataset.description || '').trim(),
        color: safeColor(option.dataset.color || '#d8dee8'),
      };
      if (!item.id) return;
      if (selectedStore.has(item.id)) {
        selectedStore.delete(item.id);
        option.classList.remove('is-selected');
      } else {
        if (!multi) {
          selectedStore.clear();
          resultsHost.querySelectorAll('.gr-macro-work-option.is-selected').forEach((el) => {
            el.classList.remove('is-selected');
          });
        }
        selectedStore.set(item.id, item);
        option.classList.add('is-selected');
      }
      updateSelectedCount();
    });

    confirmBtn.addEventListener('click', () => {
      onConfirm(Array.from(selectedStore.values()));
      closeModal();
    });

    modal.addEventListener('click', (event) => {
      if (event.target === modal) closeModal();
    });

    document.addEventListener('keydown', (event) => {
      if (event.key === 'Escape' && modal.classList.contains('is-open')) closeModal();
    });

    updateSelectedCount();
    return { openModal, closeModal, selectedStore };
  };

  createLookupModal({
    openBtnId: 'grMacroOpenWorks',
    modalId: 'grMacroWorksModal',
    closeTopBtnId: 'grMacroCloseWorksTop',
    closeBtnId: 'grMacroCloseWorks',
    confirmBtnId: 'grMacroConfirmWorks',
    searchInputId: 'grMacroWorkSearch',
    resultsId: 'grMacroWorkResults',
    statusId: 'grMacroWorkStatus',
    selectedCountId: 'grMacroSelectedCount',
    url: config.opcUrl || '/api/gr_planning/macro/opc',
    normalizer: normalizeWork,
    selectedStore: new Map(),
    disabledStore: plannedWorks,
    itemLabelSingular: 'obra',
    itemLabelPlural: 'obras',
    emptyMessage: 'Sem obras encontradas.',
    searchError: 'Erro ao pesquisar obras.',
    initialMessage: 'Comece a escrever para pesquisar.',
    onConfirm: (items) => items.forEach(addWorkToPlanning),
  });

  const applyTeamToCell = (team) => {
    if (!activeTeamCell || !team) return;
    const color = safeColor(team.color);
    activeTeamCell.dataset.teamCode = team.code;
    activeTeamCell.dataset.teamName = team.description;
    activeTeamCell.dataset.teamColor = color;
    activeTeamCell.innerHTML = `
      <span class="gr-macro-team" style="background:${escapeHtml(color)}; color:${escapeHtml(textColorFor(color))};">
        ${escapeHtml(team.code)}
      </span>
    `;
    setDirty(true);
  };

  const teamLookup = createLookupModal({
    modalId: 'grMacroTeamsModal',
    closeTopBtnId: 'grMacroCloseTeamsTop',
    closeBtnId: 'grMacroCloseTeams',
    confirmBtnId: 'grMacroConfirmTeams',
    searchInputId: 'grMacroTeamSearch',
    resultsId: 'grMacroTeamResults',
    statusId: 'grMacroTeamStatus',
    selectedCountId: 'grMacroTeamSelectedCount',
    url: config.teamsUrl || '/api/gr_planning/macro/teams',
    normalizer: normalizeTeam,
    selectedStore: selectedTeams,
    itemLabelSingular: 'equipa',
    itemLabelPlural: 'equipas',
    emptyMessage: 'Sem equipas encontradas.',
    searchError: 'Erro ao pesquisar equipas.',
    initialMessage: 'Comece a escrever para pesquisar.',
    renderColor: true,
    multi: false,
    searchOnOpen: true,
    onConfirm: (items) => applyTeamToCell(items[0]),
  });

  const clearWeekSelectionMarks = () => {
    grid.querySelectorAll('.gr-macro-week-cell.is-selecting').forEach((cell) => {
      cell.classList.remove('is-selecting');
    });
  };

  const markWeekSelection = (timeline, startWeek, endWeek) => {
    clearWeekSelectionMarks();
    const minWeek = Math.min(startWeek, endWeek);
    const maxWeek = Math.max(startWeek, endWeek);
    timeline.querySelectorAll('.gr-macro-week-cell').forEach((cell) => {
      const week = Number(cell.dataset.week || 0);
      if (week >= minWeek && week <= maxWeek) cell.classList.add('is-selecting');
    });
  };

  const selectedWeekRange = () => {
    if (!activeWeekSelection) return null;
    const startWeek = Math.min(activeWeekSelection.startWeek, activeWeekSelection.endWeek);
    const endWeek = Math.max(activeWeekSelection.startWeek, activeWeekSelection.endWeek);
    return {
      timeline: activeWeekSelection.timeline,
      processo: activeWeekSelection.timeline.dataset.processo || '',
      startWeek,
      endWeek,
      duration: endWeek - startWeek + 1,
    };
  };

  const applySupervisorToSelection = (supervisor) => {
    const selection = selectedWeekRange();
    if (!selection || !supervisor) return;
    if (timelineRangeHasOverlap(selection.timeline, selection.startWeek, selection.endWeek)) {
      showToastMessage('Ja existe planeamento nessa obra para as semanas selecionadas.', 'warning');
      clearWeekSelectionMarks();
      activeWeekSelection = null;
      return;
    }
    const color = safeColor(supervisor.color);
    const bar = document.createElement('div');
    bar.className = 'gr-macro-bar';
    bar.style.setProperty('--start-week', String(selection.startWeek));
    bar.style.setProperty('--duration-weeks', String(selection.duration));
    bar.style.background = color;
    bar.style.color = textColorFor(color);
    bar.dataset.supervisor = supervisor.code;
    bar.dataset.label = supervisor.code;
    bar.dataset.shortLabel = initialsFromLabel(supervisor.code);
    bar.dataset.color = color;
    bar.dataset.startWeek = String(selection.startWeek);
    bar.dataset.endWeek = String(selection.endWeek);
    bar.title = `${supervisor.code} - S${selection.startWeek} a S${selection.endWeek}`;
    bar.innerHTML = barLabelHtml(supervisor.code);
    syncBarGeometry(bar, selection.startWeek, selection.endWeek);
    selection.timeline.appendChild(bar);
    updateRowDuration(selection.timeline);
    setDirty(true);
    clearWeekSelectionMarks();
    activeWeekSelection = null;
  };

  grid.querySelectorAll('.gr-macro-bar').forEach((bar) => {
    const span = bar.querySelector('span');
    const label = bar.dataset.label || bar.dataset.supervisor || span?.textContent?.trim() || '';
    bar.dataset.label = label;
    bar.dataset.shortLabel = bar.dataset.shortLabel || initialsFromLabel(label);
    updateBarLabel(bar);
  });

  window.addEventListener('resize', () => {
    grid.querySelectorAll('.gr-macro-bar').forEach(updateBarLabel);
  });

  grid.querySelectorAll('.gr-macro-timeline').forEach(updateRowDuration);

  const supervisorLookup = createLookupModal({
    modalId: 'grMacroSupervisorsModal',
    closeTopBtnId: 'grMacroCloseSupervisorsTop',
    closeBtnId: 'grMacroCloseSupervisors',
    confirmBtnId: 'grMacroConfirmSupervisors',
    searchInputId: 'grMacroSupervisorSearch',
    resultsId: 'grMacroSupervisorResults',
    statusId: 'grMacroSupervisorStatus',
    selectedCountId: 'grMacroSupervisorSelectedCount',
    url: config.supervisorsUrl || '/api/gr_planning/macro/supervisors',
    normalizer: normalizeSupervisor,
    selectedStore: selectedSupervisors,
    itemLabelSingular: 'encarregado',
    itemLabelPlural: 'encarregados',
    emptyMessage: 'Sem encarregados encontrados.',
    searchError: 'Erro ao pesquisar encarregados.',
    initialMessage: 'A carregar encarregados.',
    renderColor: true,
    multi: false,
    searchOnOpen: true,
    selectedAdjectiveSingular: 'selecionado',
    selectedAdjectivePlural: 'selecionados',
    onClose: () => {
      clearWeekSelectionMarks();
      activeWeekSelection = null;
    },
    onConfirm: (items) => applySupervisorToSelection(items[0]),
  });

  const openTeamForCell = (cell) => {
    if (!cell || !teamLookup) return;
    activeTeamCell = cell;
    teamLookup.openModal();
  };

  grid.addEventListener('click', (event) => {
    const deleteRowBtn = event.target.closest('.gr-macro-row-delete');
    if (deleteRowBtn && grid.contains(deleteRowBtn)) {
      const obraCell = deleteRowBtn.closest('.gr-macro-col-obra');
      const processo = obraCell?.dataset.processo || '';
      if (!processo) return;
      if (!window.confirm(`Remover a obra ${processo} do planeamento?`)) return;
      rowElements(processo).forEach((el) => el.remove());
      plannedWorks.delete(processo);
      updateEmptyState();
      setDirty(true);
      return;
    }

    const teamCell = event.target.closest('.gr-macro-team-cell');
    if (!teamCell || !grid.contains(teamCell)) return;
    openTeamForCell(teamCell);
  });

  grid.addEventListener('keydown', (event) => {
    if (event.key !== 'Enter' && event.key !== ' ') return;
    const teamCell = event.target.closest('.gr-macro-team-cell');
    if (!teamCell || !grid.contains(teamCell)) return;
    event.preventDefault();
    openTeamForCell(teamCell);
  });

  grid.addEventListener('mousedown', (event) => {
    const bar = event.target.closest('.gr-macro-bar');
    if (!bar || !grid.contains(bar)) return;
    const timeline = bar.closest('.gr-macro-timeline');
    if (!timeline) return;

    const startWeek = Number(bar.dataset.startWeek || 0) || Number(bar.style.getPropertyValue('--start-week')) || 1;
    const duration = Number(bar.style.getPropertyValue('--duration-weeks')) || 1;
    const endWeek = Number(bar.dataset.endWeek || 0) || (startWeek + duration - 1);
    const handle = event.target.closest('[data-bar-handle]');
    const pointerWeek = weekFromPointer(timeline, event.clientX);

    event.preventDefault();
    event.stopImmediatePropagation();
    activeBarDrag = {
      bar,
      timeline,
      mode: handle?.dataset.barHandle || 'move',
      startWeek,
      endWeek,
      pointerWeek,
      duration: endWeek - startWeek + 1,
      originX: event.clientX,
      originY: event.clientY,
      moved: false,
      changed: false,
    };
    closeBarMenu();
    document.body.classList.add('gr-macro-dragging-bar');
  });

  grid.addEventListener('mousedown', (event) => {
    if (event.target.closest('.gr-macro-bar')) return;
    const weekCell = event.target.closest('.gr-macro-week-cell');
    if (!weekCell || !grid.contains(weekCell)) return;
    const timeline = weekCell.closest('.gr-macro-timeline');
    const week = Number(weekCell.dataset.week || 0);
    if (!timeline || !week) return;
    event.preventDefault();
    activeWeekSelection = {
      timeline,
      startWeek: week,
      endWeek: week,
      dragging: true,
    };
    markWeekSelection(timeline, week, week);
  });

  grid.addEventListener('mouseover', (event) => {
    if (!activeWeekSelection?.dragging) return;
    const weekCell = event.target.closest('.gr-macro-week-cell');
    if (!weekCell || !grid.contains(weekCell)) return;
    const timeline = weekCell.closest('.gr-macro-timeline');
    if (timeline !== activeWeekSelection.timeline) return;
    const week = Number(weekCell.dataset.week || 0);
    if (!week) return;
    activeWeekSelection.endWeek = week;
    markWeekSelection(timeline, activeWeekSelection.startWeek, week);
  });

  document.addEventListener('mousemove', (event) => {
    if (!activeBarDrag) return;
    event.preventDefault();
    const movedEnough = Math.abs(event.clientX - activeBarDrag.originX) > 3
      || Math.abs(event.clientY - activeBarDrag.originY) > 3;
    if (!movedEnough) return;
    activeBarDrag.moved = true;
    const week = weekFromPointer(activeBarDrag.timeline, event.clientX);

    if (activeBarDrag.mode === 'start') {
      const startWeek = clamp(week, 1, activeBarDrag.endWeek);
      if (!timelineRangeHasOverlap(activeBarDrag.timeline, startWeek, activeBarDrag.endWeek, activeBarDrag.bar)) {
        syncBarGeometry(activeBarDrag.bar, startWeek, activeBarDrag.endWeek);
        activeBarDrag.changed = true;
      }
      return;
    }

    if (activeBarDrag.mode === 'end') {
      const endWeek = clamp(week, activeBarDrag.startWeek, weeks.length);
      if (!timelineRangeHasOverlap(activeBarDrag.timeline, activeBarDrag.startWeek, endWeek, activeBarDrag.bar)) {
        syncBarGeometry(activeBarDrag.bar, activeBarDrag.startWeek, endWeek);
        activeBarDrag.changed = true;
      }
      return;
    }

    const delta = week - activeBarDrag.pointerWeek;
    const maxStart = Math.max(1, weeks.length - activeBarDrag.duration + 1);
    const startWeek = clamp(activeBarDrag.startWeek + delta, 1, maxStart);
    const endWeek = startWeek + activeBarDrag.duration - 1;
    if (!timelineRangeHasOverlap(activeBarDrag.timeline, startWeek, endWeek, activeBarDrag.bar)) {
      syncBarGeometry(activeBarDrag.bar, startWeek, endWeek);
      activeBarDrag.changed = true;
    }
  });

  document.addEventListener('mouseup', (event) => {
    if (activeBarDrag) {
      const drag = activeBarDrag;
      activeBarDrag = null;
      document.body.classList.remove('gr-macro-dragging-bar');
      if (!drag.moved && drag.mode === 'move') {
        openBarMenu(drag.bar, event.clientX, event.clientY);
      } else if (drag.changed) {
        updateRowDuration(drag.timeline);
        setDirty(true);
      }
      return;
    }
    if (!activeWeekSelection?.dragging) return;
    activeWeekSelection.dragging = false;
    const selection = selectedWeekRange();
    if (selection && timelineRangeHasOverlap(selection.timeline, selection.startWeek, selection.endWeek)) {
      showToastMessage('Ja existe planeamento nessa obra para as semanas selecionadas.', 'warning');
      clearWeekSelectionMarks();
      activeWeekSelection = null;
      return;
    }
    if (supervisorLookup) supervisorLookup.openModal();
  });

  document.addEventListener('click', (event) => {
    if (!activeBarMenu) return;
    if (event.target.closest('.gr-macro-bar-menu') || event.target.closest('.gr-macro-bar')) return;
    closeBarMenu();
  });

  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') closeBarMenu();
  });

  const serializePlanning = () => {
    const rows = Array.from(grid.querySelectorAll('.gr-macro-timeline')).map((timeline, index) => {
      const processo = String(timeline.dataset.processo || '').trim();
      const obraCell = grid.querySelector(`.gr-macro-col-obra[data-processo="${cssEscape(processo)}"]`);
      const teamCell = grid.querySelector(`.gr-macro-team-cell[data-processo="${cssEscape(processo)}"]`);
      const qttCell = grid.querySelector(`.gr-macro-col-quantidade[data-processo="${cssEscape(processo)}"]`);
      return {
        processo,
        descricao: String(obraCell?.dataset.description || '').trim(),
        fref: String(teamCell?.dataset.teamCode || '').trim(),
        qtt: String(qttCell?.dataset.qtt || '').trim(),
        ordem: index + 1,
        bars: Array.from(timeline.querySelectorAll('.gr-macro-bar')).map((bar) => ({
          encarregado: String(bar.dataset.supervisor || bar.dataset.label || '').trim(),
          startWeek: Number(bar.dataset.startWeek || 0),
          endWeek: Number(bar.dataset.endWeek || 0),
        })).filter((bar) => bar.encarregado && bar.startWeek && bar.endWeek),
      };
    }).filter((row) => row.processo);
    return {
      year: Number(config.year || yearSelect?.value || new Date().getFullYear()),
      rows,
    };
  };

  const savePlanning = async () => {
    if (!saveBtn || isSaving) return;
    isSaving = true;
    saveBtn.disabled = true;
    setStatus('A gravar planeamento...');
    try {
      const response = await fetch(config.planUrl || '/api/gr_planning/macro/plan', {
        method: 'POST',
        headers: {
          Accept: 'application/json',
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(serializePlanning()),
      });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok || payload.ok === false) throw new Error(payload.error || 'Erro ao gravar planeamento.');
      setDirty(false);
      showToastMessage('Planeamento guardado.');
    } catch (error) {
      setStatus('Erro ao gravar planeamento.');
      showToastMessage(error.message || 'Erro ao gravar planeamento.', 'danger');
      saveBtn.disabled = false;
    } finally {
      isSaving = false;
      if (!isDirty && saveBtn) saveBtn.disabled = true;
    }
  };

  saveBtn?.addEventListener('click', savePlanning);

  yearSelect?.addEventListener('change', () => {
    if (isDirty && !window.confirm('Existem alteracoes por gravar. Mudar de ano sem gravar?')) {
      yearSelect.value = String(config.year || '');
      return;
    }
    yearSelect.closest('form')?.submit();
  });

  window.addEventListener('beforeunload', (event) => {
    if (!isDirty) return;
    event.preventDefault();
    event.returnValue = '';
  });

  updateEmptyState();
  setDirty(false);
})();
