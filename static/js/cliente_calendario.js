(function () {
  'use strict';

  const root = document.getElementById('clientCalendar');
  if (!root) return;

  const form = document.getElementById('clientCalendarFilters');
  const lodgingField = document.getElementById('clientCalendarLodgingField');
  const lodgingInput = document.getElementById('clientCalendarLodging');
  const startInput = document.getElementById('clientCalendarStart');
  const cancelledInput = document.getElementById('clientCalendarCancelled');
  const previousButton = document.getElementById('clientCalendarPrevious');
  const nextButton = document.getElementById('clientCalendarNext');
  const todayButton = document.getElementById('clientCalendarToday');
  const status = document.getElementById('clientCalendarStatus');
  const grid = document.getElementById('clientCalendarGrid');
  const empty = document.getElementById('clientCalendarEmpty');
  const dayModalElement = document.getElementById('clientCalendarDayModal');
  const dayTitle = document.getElementById('clientCalendarDayTitle');
  const daySubtitle = document.getElementById('clientCalendarDaySubtitle');
  const dayList = document.getElementById('clientCalendarDayList');
  const state = { data: null, request: null };

  function escapeHtml(value) {
    return String(value ?? '')
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }

  function parseIso(value) {
    const match = /^(\d{4})-(\d{2})-(\d{2})/.exec(String(value || ''));
    return match ? new Date(Number(match[1]), Number(match[2]) - 1, Number(match[3])) : null;
  }

  function isoDate(value) {
    return `${value.getFullYear()}-${String(value.getMonth() + 1).padStart(2, '0')}-${String(value.getDate()).padStart(2, '0')}`;
  }

  function addDays(value, amount) {
    return new Date(value.getFullYear(), value.getMonth(), value.getDate() + amount);
  }

  function dayDifference(start, end) {
    return Math.round((Date.UTC(end.getFullYear(), end.getMonth(), end.getDate()) - Date.UTC(start.getFullYear(), start.getMonth(), start.getDate())) / 86400000);
  }

  function formatDate(value) {
    const parsed = parseIso(value);
    return parsed ? new Intl.DateTimeFormat('pt-PT').format(parsed) : '—';
  }

  function formatMoney(value) {
    return Number(value || 0).toLocaleString('pt-PT', { style: 'currency', currency: 'EUR' });
  }

  function monthValue(value) {
    return `${value.getFullYear()}-${String(value.getMonth() + 1).padStart(2, '0')}`;
  }

  function addMonths(value, amount) {
    return new Date(value.getFullYear(), value.getMonth() + amount, 1);
  }

  function monthTitle(value) {
    const label = new Intl.DateTimeFormat('pt-PT', { month: 'long', year: 'numeric' }).format(value);
    return label.charAt(0).toUpperCase() + label.slice(1);
  }

  function dateRangeLabel(item) {
    const checkinTime = item.checkin_time ? ` às ${escapeHtml(item.checkin_time)}` : '';
    const checkoutTime = item.checkout_time ? ` às ${escapeHtml(item.checkout_time)}` : '';
    return `${formatDate(item.checkin)}${checkinTime} — ${formatDate(item.checkout)}${checkoutTime}`;
  }

  function reservationsForDay(iso) {
    return (state.data?.reservations || []).filter((item) => item.checkin <= iso && item.checkout >= iso);
  }

  function occupiedReservations(iso) {
    return (state.data?.reservations || []).filter((item) => !item.cancelled && item.checkin <= iso && item.checkout > iso);
  }

  function detailMarkup(item) {
    const cancellationValue = item.cancelled && Number(item.cancellation_value || 0) > 0
      ? `<div><span>Valor de cancelamento</span><strong>${escapeHtml(formatMoney(item.cancellation_value))}</strong></div>`
      : '';
    return `
      <article class="client-calendar-detail${item.cancelled ? ' is-cancelled' : ''}">
        <div class="client-calendar-detail-head">
          <span class="client-calendar-detail-code">${escapeHtml(item.reservation || 'Reserva')}</span>
          <span class="sz_badge ${item.cancelled ? 'sz_badge_danger' : 'sz_badge_info'}">${item.cancelled ? 'Cancelada' : 'Ativa'}</span>
        </div>
        <div class="client-calendar-detail-grid">
          <span><strong>Hóspede:</strong> ${escapeHtml(item.guest || '—')}</span>
          <span><strong>Pessoas:</strong> ${escapeHtml(item.people || 0)}</span>
          <span><strong>Estadia:</strong> ${dateRangeLabel(item)}</span>
          <span><strong>Origem:</strong> ${escapeHtml(item.origin || '—')}</span>
        </div>
        <div class="client-calendar-detail-values">
          <div><span>Estadia</span><strong>${escapeHtml(formatMoney(item.stay_value))}</strong></div>
          <div><span>Limpeza</span><strong>${escapeHtml(formatMoney(item.cleaning_value))}</strong></div>
          <div><span>Comissão da plataforma</span><strong>${escapeHtml(formatMoney(item.platform_commission))}</strong></div>
          <div><span>Total da reserva</span><strong>${escapeHtml(formatMoney(item.total_value))}</strong></div>
          <div class="is-net"><span>Valor líquido</span><strong>${escapeHtml(formatMoney(item.net_value))}</strong></div>
          ${cancellationValue}
        </div>
      </article>
    `;
  }

  function showModal(title, subtitle, items) {
    dayTitle.textContent = title;
    daySubtitle.textContent = subtitle;
    dayList.innerHTML = items.map(detailMarkup).join('');
    if (window.bootstrap?.Modal) window.bootstrap.Modal.getOrCreateInstance(dayModalElement).show();
  }

  function openDay(iso) {
    const items = reservationsForDay(iso);
    if (!items.length) return;
    const parsed = parseIso(iso);
    const title = parsed
      ? new Intl.DateTimeFormat('pt-PT', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' }).format(parsed)
      : iso;
    showModal(title, `${state.data?.selected_lodging || ''} · ${items.length} ${items.length === 1 ? 'reserva' : 'reservas'}`, items);
  }

  function openReservation(item) {
    showModal(
      item.guest || item.reservation || 'Reserva',
      `${state.data?.selected_lodging || ''} · ${formatDate(item.checkin)} — ${formatDate(item.checkout)}`,
      [item],
    );
  }

  function monthOccupancy(monthDate) {
    const days = new Date(monthDate.getFullYear(), monthDate.getMonth() + 1, 0).getDate();
    let occupied = 0;
    for (let day = 1; day <= days; day += 1) {
      if (occupiedReservations(isoDate(new Date(monthDate.getFullYear(), monthDate.getMonth(), day))).length) occupied += 1;
    }
    return { occupied, days, percent: days ? Math.round((occupied / days) * 100) : 0 };
  }

  function labelForReservation(item) {
    const name = item.guest || item.reservation || 'Reserva';
    const extra = Math.max(0, Number(item.people || 0) - 1);
    return `${name}${extra ? ` +${extra}` : ''}`;
  }

  function segmentsForWeek(weekStart, monthStart, monthEndExclusive) {
    const today = parseIso(isoDate(new Date()));
    const monthStartPosition = dayDifference(weekStart, monthStart);
    const monthEndPosition = dayDifference(weekStart, monthEndExclusive);
    const segments = [];
    (state.data?.reservations || []).forEach((item) => {
      const arrival = parseIso(item.checkin);
      const rawDeparture = parseIso(item.checkout);
      if (!arrival || !rawDeparture) return;
      const departure = rawDeparture > arrival ? rawDeparture : addDays(arrival, 1);
      const rawStartPosition = dayDifference(weekStart, arrival) + 0.5;
      const rawEndPosition = dayDifference(weekStart, departure) + 0.5;
      const startPosition = Math.max(0, monthStartPosition, rawStartPosition);
      const endPosition = Math.min(7, monthEndPosition, rawEndPosition);
      if (endPosition <= startPosition) return;
      segments.push({
        item,
        startPosition,
        endPosition,
        continuesBefore: rawStartPosition < startPosition,
        continuesAfter: rawEndPosition > endPosition,
        showLabel: rawStartPosition >= Math.max(0, monthStartPosition) && rawStartPosition < Math.min(7, monthEndPosition),
        past: departure <= today,
      });
    });
    segments.sort((a, b) => a.startPosition - b.startPosition || b.endPosition - a.endPosition);
    const laneEnds = [];
    segments.forEach((segment) => {
      let lane = laneEnds.findIndex((endPosition) => segment.startPosition >= endPosition);
      if (lane < 0) lane = laneEnds.length;
      laneEnds[lane] = segment.endPosition;
      segment.lane = lane;
    });
    return { segments, lanes: Math.max(1, laneEnds.length) };
  }

  function renderReservationSegment(segment) {
    const item = segment.item;
    const button = document.createElement('button');
    button.type = 'button';
    button.className = [
      'client-calendar-reservation',
      segment.past ? 'is-past' : 'is-current',
      item.cancelled ? 'is-cancelled' : '',
      segment.continuesBefore ? 'continues-before' : '',
      segment.continuesAfter ? 'continues-after' : '',
    ].filter(Boolean).join(' ');
    button.style.left = `${(segment.startPosition / 7) * 100}%`;
    button.style.right = `${((7 - segment.endPosition) / 7) * 100}%`;
    button.style.setProperty('--reservation-lane', String(segment.lane));
    button.title = `${labelForReservation(item)} · ${item.reservation || 'Reserva'}`;
    button.innerHTML = segment.showLabel ? `<span>${escapeHtml(labelForReservation(item))}</span>` : '<span aria-hidden="true"></span>';
    button.addEventListener('click', (event) => {
      event.stopPropagation();
      openReservation(item);
    });
    return button;
  }

  function renderMonth(monthDate) {
    const card = document.createElement('article');
    card.className = 'client-calendar-month';
    const occupancy = monthOccupancy(monthDate);
    card.innerHTML = `
      <div class="client-calendar-month-head">
        <h2 class="client-calendar-month-title">${escapeHtml(monthTitle(monthDate))}</h2>
        <span class="client-calendar-month-total">${occupancy.occupied} noites ocupadas · ${occupancy.percent}%</span>
      </div>
      <div class="client-calendar-weekdays" aria-hidden="true">
        <span>Segunda</span><span>Terça</span><span>Quarta</span><span>Quinta</span><span>Sexta</span><span>Sábado</span><span>Domingo</span>
      </div>
    `;

    const monthStart = new Date(monthDate.getFullYear(), monthDate.getMonth(), 1);
    const monthEndExclusive = new Date(monthDate.getFullYear(), monthDate.getMonth() + 1, 1);
    const firstWeekStart = addDays(monthStart, -((monthStart.getDay() + 6) % 7));
    const weekCount = Math.ceil(dayDifference(firstWeekStart, monthEndExclusive) / 7);
    const today = isoDate(new Date());

    for (let weekIndex = 0; weekIndex < weekCount; weekIndex += 1) {
      const weekStart = addDays(firstWeekStart, weekIndex * 7);
      const week = document.createElement('div');
      week.className = 'client-calendar-week';
      const weekSegments = segmentsForWeek(weekStart, monthStart, monthEndExclusive);
      week.style.setProperty('--reservation-lanes', String(weekSegments.lanes));

      for (let column = 0; column < 7; column += 1) {
        const current = addDays(weekStart, column);
        const iso = isoDate(current);
        const inMonth = current.getMonth() === monthDate.getMonth();
        const entries = inMonth ? reservationsForDay(iso) : [];
        const cell = document.createElement(entries.length ? 'button' : 'div');
        if (entries.length) cell.type = 'button';
        cell.className = [
          'client-calendar-cell',
          !inMonth ? 'is-outside' : '',
          current.getDay() === 0 || current.getDay() === 6 ? 'is-weekend' : '',
          iso === today ? 'is-today' : '',
        ].filter(Boolean).join(' ');
        cell.style.gridColumn = String(column + 1);
        cell.innerHTML = `<span class="client-calendar-day-number">${current.getDate()}</span>`;
        if (entries.length) {
          cell.title = `${entries.length} ${entries.length === 1 ? 'reserva' : 'reservas'} · ver detalhe`;
          cell.addEventListener('click', () => openDay(iso));
        }
        week.appendChild(cell);
      }
      weekSegments.segments.forEach((segment) => week.appendChild(renderReservationSegment(segment)));
      card.appendChild(week);
    }
    return card;
  }

  function render(data) {
    state.data = data;
    const previousSelection = lodgingInput.value;
    lodgingInput.replaceChildren();
    (data.lodgings || []).forEach((name) => {
      const option = document.createElement('option');
      option.value = name;
      option.textContent = name;
      lodgingInput.appendChild(option);
    });
    lodgingInput.value = data.selected_lodging || previousSelection;
    lodgingField.hidden = (data.lodgings || []).length <= 1;
    grid.replaceChildren();
    const hasLodgings = Boolean(data.selected_lodging);
    empty.hidden = hasLodgings;
    grid.hidden = !hasLodgings;
    if (!hasLodgings) {
      status.textContent = 'Sem alojamentos associados.';
      return;
    }
    grid.appendChild(renderMonth(parseIso(data.start)));
    const active = (data.reservations || []).filter((item) => !item.cancelled).length;
    const cancelled = (data.reservations || []).filter((item) => item.cancelled).length;
    status.textContent = `${data.selected_lodging} · ${active} ${active === 1 ? 'reserva ativa' : 'reservas ativas'}${data.include_cancelled ? ` · ${cancelled} cancelada${cancelled === 1 ? '' : 's'}` : ''}`;
  }

  async function loadCalendar() {
    if (state.request) state.request.abort();
    state.request = new AbortController();
    status.classList.remove('is-error');
    status.textContent = 'A carregar calendário…';
    const params = new URLSearchParams({ start: startInput.value, months: '1' });
    if (lodgingInput.value) params.set('alojamento', lodgingInput.value);
    if (cancelledInput.checked) params.set('include_cancelled', '1');
    try {
      const response = await fetch(`${root.dataset.apiUrl}?${params.toString()}`, { signal: state.request.signal, headers: { Accept: 'application/json' } });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok || !payload.ok) throw new Error(payload.error || 'Não foi possível carregar o calendário.');
      render(payload.data);
    } catch (error) {
      if (error.name === 'AbortError') return;
      status.classList.add('is-error');
      status.textContent = error.message || 'Não foi possível carregar o calendário.';
    }
  }

  function moveStart(amount) {
    const current = parseIso(`${startInput.value || root.dataset.initialMonth}-01`) || new Date();
    startInput.value = monthValue(addMonths(current, amount));
    loadCalendar();
  }

  form.addEventListener('submit', (event) => { event.preventDefault(); loadCalendar(); });
  lodgingInput.addEventListener('change', loadCalendar);
  startInput.addEventListener('change', loadCalendar);
  cancelledInput.addEventListener('change', loadCalendar);
  previousButton.addEventListener('click', () => moveStart(-1));
  nextButton.addEventListener('click', () => moveStart(1));
  todayButton.addEventListener('click', () => { startInput.value = monthValue(new Date()); loadCalendar(); });
  startInput.value = startInput.value || root.dataset.initialMonth || monthValue(new Date());
  loadCalendar();
}());
