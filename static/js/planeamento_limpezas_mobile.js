(() => {
  'use strict';

  const state = {
    date: String(window.CLEANING_MOBILE_INITIAL_DATE || '').slice(0, 10),
    rows: [],
    teams: [],
    selected: null,
    selectedTeam: '',
    deletedIds: [],
    sortMode: 'team',
    dirty: false,
  };

  const $ = (selector) => document.querySelector(selector);

  function ensurePersonList() {
    const current = $('#cleaningMobilePersonList');
    if (current) return current;

    const legacySelect = $('#cleaningMobileTeamSelect');
    if (!legacySelect) return null;

    const picker = document.createElement('div');
    picker.className = 'cleaning-mobile-team-picker';
    picker.innerHTML = '<span class="cleaning-mobile-field-label">Escolher equipa</span><div class="cleaning-mobile-person-list" id="cleaningMobilePersonList"></div>';
    const legacyField = legacySelect.closest('.cleaning-mobile-field');
    if (legacyField) legacyField.replaceWith(picker);
    else legacySelect.replaceWith(picker);
    return picker.querySelector('#cleaningMobilePersonList');
  }

  function ensureTimeStepper() {
    const input = $('#cleaningMobileTimeInput');
    if (!input) return null;
    input.type = 'text';
    input.readOnly = true;
    input.removeAttribute('step');
    input.setAttribute('aria-label', 'Hora de início selecionada');
    if ($('#cleaningMobileTimeMinus') && $('#cleaningMobileTimePlus')) return input;

    const stepper = document.createElement('span');
    stepper.className = 'cleaning-mobile-time-stepper';
    const minus = document.createElement('button');
    minus.type = 'button';
    minus.id = 'cleaningMobileTimeMinus';
    minus.setAttribute('aria-label', 'Reduzir 15 minutos');
    minus.textContent = '−';
    const plus = document.createElement('button');
    plus.type = 'button';
    plus.id = 'cleaningMobileTimePlus';
    plus.setAttribute('aria-label', 'Aumentar 15 minutos');
    plus.textContent = '+';
    input.parentNode.insertBefore(stepper, input);
    stepper.append(minus, input, plus);
    return input;
  }

  function ensureCancelButton() {
    const current = $('#cleaningMobileCancel');
    if (current) return current;
    const save = $('#cleaningMobileSave');
    const footer = save?.closest('.cleaning-mobile-footer');
    if (!save || !footer) return null;
    const cancel = document.createElement('button');
    cancel.type = 'button';
    cancel.className = 'cleaning-mobile-cancel';
    cancel.id = 'cleaningMobileCancel';
    cancel.disabled = true;
    cancel.innerHTML = '<i class="fa-solid fa-rotate-left"></i> Cancelar';
    footer.insertBefore(cancel, save);
    return cancel;
  }

  function ensureSortControls() {
    let lodging = $('#cleaningMobileSortLodging');
    let team = $('#cleaningMobileSortTeam');
    let print = $('#cleaningMobilePrint');
    if (lodging && team && !print) {
      print = document.createElement('button');
      print.type = 'button';
      print.className = 'cleaning-mobile-print';
      print.id = 'cleaningMobilePrint';
      print.setAttribute('aria-label', 'Imprimir etiquetas do dia');
      print.title = 'Imprimir etiquetas do dia';
      print.innerHTML = '<i class="fa-solid fa-print"></i>';
      team.parentElement.appendChild(print);
    }
    if (lodging && team && print) return { lodging, team, print };
    const status = $('.cleaning-mobile-status');
    if (!status) return { lodging: null, team: null, print: null };
    const controls = document.createElement('div');
    controls.className = 'cleaning-mobile-sort';
    controls.setAttribute('aria-label', 'Ordenação do planeamento');
    controls.innerHTML = '<button type="button" id="cleaningMobileSortLodging" aria-pressed="false"><i class="fa-solid fa-house"></i> Alojamento</button><button type="button" class="is-active" id="cleaningMobileSortTeam" aria-pressed="true"><i class="fa-solid fa-user"></i> Equipa</button><button type="button" class="cleaning-mobile-print" id="cleaningMobilePrint" aria-label="Imprimir etiquetas do dia" title="Imprimir etiquetas do dia"><i class="fa-solid fa-print"></i></button>';
    status.insertAdjacentElement('afterend', controls);
    lodging = controls.querySelector('#cleaningMobileSortLodging');
    team = controls.querySelector('#cleaningMobileSortTeam');
    print = controls.querySelector('#cleaningMobilePrint');
    return { lodging, team, print };
  }

  document.querySelector('meta[name="viewport"]')?.setAttribute('content', 'width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no');
  const sortControls = ensureSortControls();

  const els = {
    previous: $('#cleaningMobilePrevious'), next: $('#cleaningMobileNext'), date: $('#cleaningMobileDate'),
    dateInput: $('#cleaningMobileDateInput'), weekday: $('#cleaningMobileWeekday'), dateLabel: $('#cleaningMobileDateLabel'),
    pendingCount: $('#cleaningMobilePendingCount'), plannedCount: $('#cleaningMobilePlannedCount'),
    pendingSection: $('#cleaningMobilePendingSection'), pendingList: $('#cleaningMobilePendingList'), assignedSection: $('#cleaningMobileAssignedSection'), teamList: $('#cleaningMobileTeamList'), empty: $('#cleaningMobileEmpty'),
    sortLodging: sortControls.lodging, sortTeam: sortControls.team, print: sortControls.print,
    save: $('#cleaningMobileSave'), cancel: ensureCancelButton(), sheet: $('#cleaningMobileSheet'), sheetClose: $('#cleaningMobileSheetClose'),
    sheetTitle: $('#cleaningMobileSheetTitle'), sheetProperty: $('#cleaningMobileSheetProperty'), sheetWindow: $('#cleaningMobileSheetWindow'),
    personList: ensurePersonList(), timeInput: ensureTimeStepper(), timeMinus: $('#cleaningMobileTimeMinus'), timePlus: $('#cleaningMobileTimePlus'), warning: $('#cleaningMobileScheduleWarning'),
    sheetSave: $('#cleaningMobileSheetSave'), sheetRemove: $('#cleaningMobileSheetRemove'),
  };

  const localDate = () => new Date().toISOString().slice(0, 10);
  const isLocal = (row) => String(row.row_type || '').toUpperCase() === 'LOCAL';
  const plannerFlag = (value) => value === true || value === 1 || String(value || '').trim() === '1';
  const isOnLeave = (team) => plannerFlag(team?.FOLGA ?? team?.folga);
  const isExternal = (team) => plannerFlag(team?.EXTERNA ?? team?.externa);
  const isCoordinator = (team) => plannerFlag(team?.LPADMIN ?? team?.lpadmin ?? team?.US_LPADMIN ?? team?.us_lpadmin);
  const teamName = (team) => String(team?.NOME || team?.nome || '').trim();
  const cleaningsFor = (row) => Array.isArray(row.cleanings) ? row.cleanings : [];
  const normalizeTime = (value, fallback = '—') => {
    const time = String(value || '').trim();
    return time && time !== 'N/D' ? time.slice(0, 5) : fallback;
  };
  const formatDate = (value, options) => new Date(`${value}T12:00:00`).toLocaleDateString('pt-PT', options);
  const esc = (value) => String(value ?? '').replace(/[&<>'"]/g, char => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' })[char]);

  function dateOnly(value) {
    const raw = String(value || '').trim();
    if (!raw) return null;
    const iso = raw.match(/^(\d{4})-(\d{2})-(\d{2})/);
    if (iso) return new Date(Number(iso[1]), Number(iso[2]) - 1, Number(iso[3]));
    const parsed = new Date(raw);
    return Number.isNaN(parsed.getTime()) ? null : new Date(parsed.getFullYear(), parsed.getMonth(), parsed.getDate());
  }

  function shortDate(value) {
    const parsed = dateOnly(value);
    return parsed ? parsed.toLocaleDateString('pt-PT', { day: '2-digit', month: '2-digit' }) : '';
  }

  function daysBetween(from, to) {
    const start = dateOnly(from);
    const end = dateOnly(to);
    return start && end ? Math.round((end.getTime() - start.getTime()) / 86400000) : null;
  }

  function isCleanSinceLast(row) {
    return plannerFlag(row?.clean_since_last);
  }

  function deferredState(row) {
    if (!row?.checkout_reservation || cleaningsFor(row).length) return null;
    const postponedDate = String(row.postponed_date || '').trim();
    if (postponedDate) {
      return {
        kind: 'future',
        date: postponedDate,
        team: String(row.postponed_team || '').trim(),
        nextCheckin: String(row.next_checkin_date || '').trim(),
      };
    }
    const minNights = Number(row.min_nights || row.al_noites || 0);
    const nextCheckin = String(row.next_checkin_date || '').trim();
    const gapDays = daysBetween(state.date, nextCheckin);
    if (!Number.isFinite(minNights) || minNights <= 0 || gapDays === null || gapDays <= 0 || gapDays >= minNights) return null;
    return { kind: 'pending', nextCheckin };
  }

  function checkinDisplay(row) {
    if (row.checkin_reservation) return normalizeTime(row.checkin_time);
    const date = shortDate(row.next_checkin_date);
    const time = normalizeTime(row.next_checkin_time, '');
    return [date, time].filter(Boolean).join(' · ') || '—';
  }

  function teamFlagMarkup(name) {
    const normalizedName = String(name || '').trim() || 'Sem equipa';
    const configuredTeam = state.teams.find(team => teamName(team) === normalizedName);
    const configuredColor = String(configuredTeam?.COR || '').trim();
    const color = window.CSS?.supports?.('color', configuredColor) ? configuredColor : '#6f8ca8';
    return `<span class="cleaning-mobile-team-flag" style="--cleaning-team-color:${esc(color)}"><i></i>${esc(normalizedName)}</span>`;
  }

  function cleaningDuration(row) {
    const configured = Number(row?.cleaning_minutes || 0);
    if (Number.isFinite(configured) && configured > 0) return configured;
    const typology = String(row?.typology || '').trim();
    if (['T0', 'T1'].includes(typology)) return 60;
    if (['T2', 'T3'].includes(typology)) return 90;
    if (['T4', 'T5'].includes(typology)) return 120;
    return 60;
  }

  function timeToMinutes(value) {
    const normalized = normalizeTime(value, '');
    if (!/^\d{2}:\d{2}$/.test(normalized)) return null;
    const [hour, minute] = normalized.split(':').map(Number);
    return Number.isFinite(hour) && Number.isFinite(minute) ? (hour * 60) + minute : null;
  }

  function minutesToTime(value) {
    const minutes = Math.max(0, Math.min(23 * 60 + 59, Number(value) || 0));
    return `${String(Math.floor(minutes / 60)).padStart(2, '0')}:${String(minutes % 60).padStart(2, '0')}`;
  }

  function adjustStartTime(deltaMinutes) {
    const current = timeToMinutes(els.timeInput.value);
    const next = Math.max(0, Math.min(23 * 60 + 45, (current ?? 0) + deltaMinutes));
    els.timeInput.value = minutesToTime(next);
    updateWarning();
  }

  function teamJobs(name, excludedCleaning = null) {
    return state.rows.flatMap(row => cleaningsFor(row)
      .filter(cleaning => cleaning !== excludedCleaning && cleaning.team === name)
      .map(cleaning => ({ row, cleaning })));
  }

  function nextAvailableTime(name, targetRow, excludedCleaning = null) {
    const lastEnd = teamJobs(name, excludedCleaning).reduce((latest, job) => {
      const start = timeToMinutes(job.cleaning.time);
      return start === null ? latest : Math.max(latest, start + cleaningDuration(job.row));
    }, 0);
    const checkout = timeToMinutes(targetRow?.checkout_time);
    const earliest = checkout === null ? 7 * 60 : checkout;
    const suggested = Math.max(lastEnd, earliest);
    return minutesToTime(Math.ceil(suggested / 15) * 15);
  }

  function buildRows(data) {
    const byPlace = new Map();
    (Array.isArray(data) ? data : []).forEach((raw) => {
      const name = String(raw.lodging || '').trim();
      if (!name) return;
      const type = String(raw.row_type || 'ALOJAMENTO').toUpperCase();
      const key = `${type}:${name}`;
      if (!byPlace.has(key)) byPlace.set(key, { ...raw, row_type: type, cleanings: [] });
      const row = byPlace.get(key);
      if (raw.cleaning_id || raw.cleaning_time || raw.cleaning_team) {
        row.cleanings.push({
          id: raw.cleaning_id,
          time: normalizeTime(raw.cleaning_time, ''),
          team: String(raw.cleaning_team || '').trim(),
          folga: raw.cleaning_folga,
          local: type === 'LOCAL' ? name : '',
        });
      }
    });
    return [...byPlace.values()];
  }

  function setDirty(value) {
    state.dirty = Boolean(value);
    els.save.disabled = !state.dirty;
    els.cancel.disabled = !state.dirty;
    els.previous.disabled = state.dirty;
    els.next.disabled = state.dirty;
    els.date.disabled = state.dirty;
    els.print.disabled = state.dirty;
  }

  function setSortMode(mode) {
    state.sortMode = mode === 'lodging' ? 'lodging' : 'team';
    const lodgingActive = state.sortMode === 'lodging';
    els.sortLodging.classList.toggle('is-active', lodgingActive);
    els.sortTeam.classList.toggle('is-active', !lodgingActive);
    els.sortLodging.setAttribute('aria-pressed', String(lodgingActive));
    els.sortTeam.setAttribute('aria-pressed', String(!lodgingActive));
    render();
  }

  function updateDateHeader() {
    els.dateInput.value = state.date;
    els.weekday.textContent = formatDate(state.date, { weekday: 'long' });
    els.dateLabel.textContent = formatDate(state.date, { day: '2-digit', month: 'long', year: 'numeric' });
  }

  function cardMarkup(row, cleaning) {
    const pending = !cleaning;
    const checkout = normalizeTime(row.checkout_time);
    const checkin = checkinDisplay(row);
    const plannedTime = pending ? 'por atribuir' : normalizeTime(cleaning.time);
    const rowLabel = isLocal(row) ? 'Local' : (row.typology || 'Alojamento');
    const duration = cleaningDuration(row);
    const durationText = duration ? ` · ${duration} min` : '';
    return `<button class="cleaning-mobile-card${pending ? ' is-pending' : ''}" type="button" data-row="${esc(row._key)}" data-cleaning="${esc(cleaning?._key || '')}">
      <span class="cleaning-mobile-card-head"><span class="cleaning-mobile-card-name">${esc(row.lodging)}</span><span class="cleaning-mobile-card-time">${esc(plannedTime)}</span></span>
      <span class="cleaning-mobile-window"><span class="cleaning-mobile-window-item">CHECK-OUT<strong>${esc(checkout)}</strong></span><span class="cleaning-mobile-window-item is-checkin">CHECK-IN<strong>${esc(checkin)}</strong></span></span>
      <span class="cleaning-mobile-card-meta">${pending ? esc(`${rowLabel}${durationText}`) : `${teamFlagMarkup(cleaning.team)}<span class="cleaning-mobile-card-detail">${esc(`${rowLabel}${durationText}`)}</span>`}</span>
      <span class="cleaning-mobile-card-action">${pending ? 'Atribuir limpeza →' : 'Editar limpeza →'}</span>
    </button>`;
  }

  function statusCardMarkup(row, status) {
    const future = status.kind === 'future';
    const statusDate = shortDate(future ? status.date : row.last_clean_date);
    const team = future ? status.team : String(row.last_team || '').trim();
    const badge = future ? `Atribuída para ${statusDate}` : `Limpa em ${statusDate}`;
    const detail = future ? 'Limpeza planeada para outra data' : 'Limpeza efetuada anteriormente';
    return `<article class="cleaning-mobile-card cleaning-mobile-card-status ${future ? 'is-future' : 'is-previous'}">
      <span class="cleaning-mobile-card-head"><span class="cleaning-mobile-card-name">${esc(row.lodging)}</span><span class="cleaning-mobile-card-time">${esc(badge)}</span></span>
      <span class="cleaning-mobile-window"><span class="cleaning-mobile-window-item">CHECK-OUT<strong>${esc(normalizeTime(row.checkout_time))}</strong></span><span class="cleaning-mobile-window-item is-checkin">CHECK-IN<strong>${esc(checkinDisplay(row))}</strong></span></span>
      <span class="cleaning-mobile-card-meta">${teamFlagMarkup(team || 'Equipa por indicar')}<span class="cleaning-mobile-card-detail">${esc(detail)}</span></span>
    </article>`;
  }

  function bindCards() {
    document.querySelectorAll('button.cleaning-mobile-card[data-row]').forEach((button) => {
      button.addEventListener('click', () => {
        const row = state.rows.find(item => item._key === button.dataset.row);
        const cleaning = cleaningsFor(row).find(item => item._key === button.dataset.cleaning) || null;
        if (row) openSheet(row, cleaning);
      });
    });
  }

  function render() {
    state.rows.forEach((row, index) => {
      row._key = row._key || `row-${index}`;
      cleaningsFor(row).forEach((cleaning, cleaningIndex) => { cleaning._key = cleaning._key || `cleaning-${index}-${cleaningIndex}`; });
    });
    const special = state.rows.flatMap(row => {
      if (cleaningsFor(row).length) return [];
      const deferred = deferredState(row);
      if (deferred?.kind === 'future') return [{ row, status: deferred }];
      if (row.checkin_reservation && isCleanSinceLast(row)) return [{ row, status: { kind: 'previous' } }];
      return [];
    });
    const specialRows = new Set(special.map(item => item.row));
    const requiredRows = state.rows.filter(row => (
      Boolean(row.checkout_reservation)
      || (Boolean(row.checkin_reservation) && !isCleanSinceLast(row))
    ));
    const pending = requiredRows.filter(row => !cleaningsFor(row).length && !specialRows.has(row));
    if (state.sortMode === 'lodging') pending.sort((a, b) => String(a.lodging || '').localeCompare(String(b.lodging || ''), 'pt'));
    const planned = requiredRows.length - pending.length;
    els.pendingCount.textContent = pending.length;
    els.plannedCount.textContent = `${planned} de ${requiredRows.length}`;
    els.pendingSection.hidden = state.sortMode === 'lodging' || !pending.length;
    els.pendingList.innerHTML = pending.map(row => cardMarkup(row, null)).join('');

    const assigned = state.rows.flatMap(row => cleaningsFor(row).map(cleaning => ({ row, cleaning })))
      .sort((a, b) => state.sortMode === 'lodging'
        ? String(a.row.lodging || '').localeCompare(String(b.row.lodging || ''), 'pt') || String(a.cleaning.time).localeCompare(String(b.cleaning.time))
        : String(a.cleaning.team).localeCompare(String(b.cleaning.team), 'pt') || String(a.cleaning.time).localeCompare(String(b.cleaning.time)));
    if (state.sortMode === 'lodging') {
      const flatItems = [
        ...pending.map(row => ({ row, time: '', markup: cardMarkup(row, null) })),
        ...assigned.map(({ row, cleaning }) => ({ row, time: cleaning.time || '', markup: cardMarkup(row, cleaning) })),
        ...special.map(({ row, status }) => ({ row, time: '', markup: statusCardMarkup(row, status) })),
      ].sort((a, b) => String(a.row.lodging || '').localeCompare(String(b.row.lodging || ''), 'pt') || String(a.time).localeCompare(String(b.time)));
      els.assignedSection.querySelector('.cleaning-mobile-section-title').hidden = true;
      els.teamList.innerHTML = `<div class="cleaning-mobile-list">${flatItems.map(item => item.markup).join('')}</div>`;
      els.empty.hidden = Boolean(flatItems.length);
      bindCards();
      return;
    }

    els.assignedSection.querySelector('.cleaning-mobile-section-title').hidden = false;
    const groups = new Map();
    assigned.forEach(item => {
      const key = item.cleaning.team || 'Sem equipa';
      if (!groups.has(key)) groups.set(key, []);
      groups.get(key).push(item);
    });
    const teamSections = [...groups.entries()].map(([name, jobs]) => {
      const configuredTeam = state.teams.find(team => teamName(team) === name);
      const color = configuredTeam?.COR || '#58c7bb';
      return `<section class="cleaning-mobile-team"><h3 class="cleaning-mobile-team-heading"><i class="cleaning-mobile-team-dot" style="background:${esc(color)}"></i>${esc(name)}<small>${jobs.length} limpeza${jobs.length === 1 ? '' : 's'}</small></h3><div class="cleaning-mobile-list">${jobs.map(({ row, cleaning }) => cardMarkup(row, cleaning)).join('')}</div></section>`;
    }).join('');
    const specialSection = special.length ? `<section class="cleaning-mobile-status-queue"><div class="cleaning-mobile-section-title"><h2>Outras datas</h2><span>Já encaminhadas</span></div><div class="cleaning-mobile-list">${special.map(({ row, status }) => statusCardMarkup(row, status)).join('')}</div></section>` : '';
    els.teamList.innerHTML = teamSections + specialSection;
    els.empty.hidden = Boolean(pending.length || assigned.length || special.length);
    bindCards();
  }

  function renderWindow(row) {
    els.sheetWindow.innerHTML = `<span class="cleaning-mobile-window-item">CHECK-OUT<strong>${esc(normalizeTime(row.checkout_time))}</strong></span><span class="cleaning-mobile-window-item is-checkin">CHECK-IN<strong>${esc(checkinDisplay(row))}</strong></span>`;
  }

  function renderPeople() {
    const { row, cleaning } = state.selected || {};
    if (!row) return;
    if (!els.personList) {
      els.sheetSave.disabled = true;
      showError(new Error('Não foi possível apresentar a lista de pessoas. Atualize a página e tente novamente.'));
      return;
    }
    if (!state.teams.length) {
      els.personList.innerHTML = '<div class="cleaning-mobile-person-empty">Sem pessoas disponíveis para este dia.</div>';
      els.sheetSave.disabled = true;
      return;
    }
    const personCard = (team) => {
      const name = teamName(team);
      const count = teamJobs(name).length;
      const nextTime = nextAvailableTime(name, row, cleaning);
      const selected = name === state.selectedTeam;
      return `<button type="button" class="cleaning-mobile-person-card${selected ? ' is-selected' : ''}${isOnLeave(team) ? ' is-on-leave' : ''}" data-team="${esc(name)}" aria-pressed="${selected ? 'true' : 'false'}">
        <i class="cleaning-mobile-person-color" style="background:${esc(team.COR || '#58c7bb')}"></i>
        <span class="cleaning-mobile-person-name">${esc(name)}${isOnLeave(team) ? ' · Folga' : ''}</span>
        <span class="cleaning-mobile-person-load">${count} limpeza${count === 1 ? '' : 's'} · <span class="cleaning-mobile-person-next">próxima ${esc(nextTime)}</span></span>
      </button>`;
    };
    const namedTeams = state.teams.filter(team => teamName(team));
    const activeTeams = namedTeams.filter(team => !isOnLeave(team));
    const groups = [
      ['Internas', activeTeams.filter(team => !isExternal(team) && !isCoordinator(team))],
      ['Externas', activeTeams.filter(team => isExternal(team) && !isCoordinator(team))],
      ['Coordenação', activeTeams.filter(isCoordinator)],
      ['Folgas', namedTeams.filter(isOnLeave)],
    ].filter(([, teams]) => teams.length);
    els.personList.innerHTML = groups.map(([title, teams]) => `<section class="cleaning-mobile-person-group">
      <h3 class="cleaning-mobile-person-group-title">${esc(title)}</h3>
      <div class="cleaning-mobile-person-group-grid">${teams.map(personCard).join('')}</div>
    </section>`).join('');
    els.personList.querySelectorAll('.cleaning-mobile-person-card').forEach(card => {
      card.addEventListener('click', () => {
        state.selectedTeam = card.dataset.team || '';
        els.timeInput.value = nextAvailableTime(state.selectedTeam, row, cleaning);
        els.sheetSave.disabled = !state.selectedTeam;
        renderPeople();
        updateWarning();
      });
    });
  }

  function updateWarning() {
    const row = state.selected?.row;
    if (!row) return;
    const checkin = normalizeTime(row.checkin_time, '');
    const start = normalizeTime(els.timeInput.value, '');
    const duration = cleaningDuration(row);
    if (!checkin || !start || !duration) { els.warning.hidden = true; return; }
    const [startHour, startMinute] = start.split(':').map(Number);
    const [inHour, inMinute] = checkin.split(':').map(Number);
    const end = startHour * 60 + startMinute + duration;
    const checkinMinutes = inHour * 60 + inMinute;
    if (end > checkinMinutes) {
      els.warning.textContent = `A duração prevista termina às ${String(Math.floor(end / 60)).padStart(2, '0')}:${String(end % 60).padStart(2, '0')}, depois do check-in previsto.`;
      els.warning.hidden = false;
    } else els.warning.hidden = true;
  }

  function openSheet(row, cleaning) {
    state.selected = { row, cleaning };
    state.selectedTeam = cleaning?.team || '';
    els.sheetTitle.textContent = cleaning ? 'Editar limpeza' : 'Atribuir limpeza';
    els.sheetProperty.textContent = row.lodging;
    renderWindow(row);
    els.timeInput.value = normalizeTime(cleaning?.time || row.checkout_time, '10:00');
    els.sheetSave.disabled = !state.selectedTeam;
    els.sheetRemove.hidden = !cleaning;
    renderPeople();
    updateWarning();
    els.sheet.classList.add('is-open');
    els.sheet.setAttribute('aria-hidden', 'false');
  }

  function closeSheet() {
    els.sheet.classList.remove('is-open');
    els.sheet.setAttribute('aria-hidden', 'true');
    state.selected = null;
    state.selectedTeam = '';
  }

  async function load() {
    updateDateHeader();
    const [planResponse, teamsResponse] = await Promise.all([
      fetch(`/generic/api/cleaning_plan?date=${encodeURIComponent(state.date)}`),
      fetch(`/generic/api/planner2_teams?date=${encodeURIComponent(state.date)}`),
    ]);
    const plan = await planResponse.json().catch(() => []);
    const teams = await teamsResponse.json().catch(() => []);
    if (!planResponse.ok) throw new Error(plan.error || 'Não foi possível carregar o planeamento.');
    state.rows = buildRows(plan);
    state.teams = Array.isArray(teams) ? teams : [];
    state.deletedIds = [];
    render();
    setDirty(false);
  }

  function payload() {
    return state.rows.flatMap(row => cleaningsFor(row).filter(cleaning => cleaning.team && cleaning.time).map(cleaning => {
      const item = { ALOJAMENTO: isLocal(row) ? '' : row.lodging, LOCAL: isLocal(row) ? row.lodging : '', DATA: state.date, HORA: cleaning.time, EQUIPA: cleaning.team };
      if (cleaning.id) item.LPSTAMP = cleaning.id;
      const assignedTeam = state.teams.find(team => teamName(team) === cleaning.team);
      item.FOLGA = isOnLeave(assignedTeam) ? 1 : 0;
      return item;
    }));
  }

  async function save() {
    const updates = payload();
    if (updates.length) {
      const response = await fetch('/generic/api/LP/gravar', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(updates) });
      const data = await response.json().catch(() => ({}));
      if (!response.ok || !data.success) throw new Error(data.message || 'Não foi possível gravar as alterações.');
    }
    for (const cleaningId of state.deletedIds) {
      const response = await fetch(`/generic/api/LP/${encodeURIComponent(cleaningId)}/planner-delete`, { method: 'DELETE' });
      const data = await response.json().catch(() => ({}));
      if (!response.ok || data.error) throw new Error(data.error || 'Não foi possível remover uma limpeza.');
    }
    await load();
  }

  function changeDate(days) {
    if (state.dirty) return;
    const next = new Date(`${state.date}T12:00:00`);
    next.setDate(next.getDate() + days);
    state.date = next.toISOString().slice(0, 10);
    load().catch(showError);
  }

  function showError(error) {
    const message = error?.message || 'Ocorreu um erro.';
    if (typeof window.showToast === 'function') window.showToast(message, 'danger'); else window.alert(message);
  }

  function showSuccess(message) {
    if (typeof window.showToast === 'function') window.showToast(message, 'success'); else window.alert(message);
  }

  async function printLabels() {
    if (!state.date || state.dirty) return;
    els.print.disabled = true;
    els.print.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i>';
    try {
      const response = await fetch(`/planner/api/imprimir_etiquetas?date=${encodeURIComponent(state.date)}`, { method: 'POST' });
      const data = await response.json().catch(() => ({}));
      if (!response.ok || !data.success) throw new Error(data.error || 'Não foi possível criar as etiquetas.');
      showSuccess('Etiquetas criadas.');
    } finally {
      els.print.disabled = state.dirty;
      els.print.innerHTML = '<i class="fa-solid fa-print"></i>';
    }
  }

  els.previous.addEventListener('click', () => changeDate(-1));
  els.next.addEventListener('click', () => changeDate(1));
  els.sortLodging.addEventListener('click', () => setSortMode('lodging'));
  els.sortTeam.addEventListener('click', () => setSortMode('team'));
  els.print.addEventListener('click', () => printLabels().catch(showError));
  els.date.addEventListener('click', () => els.dateInput.showPicker?.() || els.dateInput.click());
  els.dateInput.addEventListener('change', () => {
    if (state.dirty) { els.dateInput.value = state.date; return; }
    if (els.dateInput.value) { state.date = els.dateInput.value; load().catch(showError); }
  });
  els.sheetClose.addEventListener('click', closeSheet);
  els.sheet.addEventListener('click', event => { if (event.target === els.sheet) closeSheet(); });
  els.timeMinus.addEventListener('click', () => adjustStartTime(-15));
  els.timePlus.addEventListener('click', () => adjustStartTime(15));
  els.sheetSave.addEventListener('click', () => {
    const { row, cleaning } = state.selected || {};
    const assignedTeam = state.teams.find(team => teamName(team) === state.selectedTeam);
    if (!row || !assignedTeam || !els.timeInput.value) return;
    const item = cleaning || { _key: `new-${Date.now()}`, local: isLocal(row) ? row.lodging : '' };
    item.team = teamName(assignedTeam);
    item.time = els.timeInput.value;
    item.folga = isOnLeave(assignedTeam) ? 1 : 0;
    if (!cleaning) row.cleanings.push(item);
    setDirty(true);
    closeSheet();
    if (!cleaning) {
      const sourceCard = [...document.querySelectorAll('button.cleaning-mobile-card[data-row]')]
        .find(card => card.dataset.row === row._key && !card.dataset.cleaning);
      if (sourceCard) {
        sourceCard.classList.add('is-assigned-exit');
        window.setTimeout(render, 420);
      } else render();
    } else render();
  });
  els.sheetRemove.addEventListener('click', async () => {
    const { row, cleaning } = state.selected || {};
    if (!row || !cleaning || !window.confirm('Remover esta limpeza?')) return;
    if (!cleaning.id) {
      row.cleanings = cleaningsFor(row).filter(item => item._key !== cleaning._key);
      closeSheet();
      setDirty(true);
      render();
      return;
    }
    state.deletedIds.push(cleaning.id);
    row.cleanings = cleaningsFor(row).filter(item => item._key !== cleaning._key);
    closeSheet();
    setDirty(true);
    render();
  });
  els.save.addEventListener('click', () => save().catch(showError));
  els.cancel.addEventListener('click', () => {
    if (!state.dirty) return;
    load().catch(showError);
  });

  if (!state.date) state.date = localDate();
  load().catch(showError);
})();
