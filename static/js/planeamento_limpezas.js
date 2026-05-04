const PLANNER2 = {
  startHour: 7,
  endHour: 23,
  slotMinutes: 30,
  lodgeWidth: 240,
  slotWidth: 32
};

let planner2Teams = [];

function showPlannerToast(message, type = 'success', options = {}) {
  if (typeof window.showToast === 'function') {
    window.showToast(message, type, options);
    return;
  }
  alert(message);
}

const buildSlots = () => {
  const slots = [];
  for (let h = PLANNER2.startHour; h < PLANNER2.endHour; h++) {
    slots.push(`${String(h).padStart(2, '0')}:00`);
    slots.push(`${String(h).padStart(2, '0')}:30`);
  }
  return slots;
};

const parseTime = (timeStr, fallback) => {
  let time = (timeStr || '').trim();
  if (!time || time === 'N/D') {
    time = fallback;
  }
  const [hStr, mStr = '00'] = time.split(':');
  let h = parseInt(hStr, 10);
  let m = parseInt(mStr, 10);
  if (Number.isNaN(h)) h = parseInt(fallback.split(':')[0], 10);
  if (Number.isNaN(m)) m = parseInt(fallback.split(':')[1], 10);
  return { h, m };
};

const hasDefinedPlannerTime = (timeStr) => {
  const time = String(timeStr || '').trim();
  return !!time && time !== 'N/D';
};

const timeToIndex = (h, m) => {
  const idx = (h - PLANNER2.startHour) * 2 + (m >= 30 ? 1 : 0);
  return Math.max(0, Math.min(idx, (PLANNER2.endHour - PLANNER2.startHour) * 2));
};

const shouldAnchorCheckinAtNight = (h, m) => {
  const beforeVisibleDay = h < PLANNER2.startHour || (h === PLANNER2.startHour && m === 0);
  const afterNightLimit = h > 21 || (h === 21 && m > 0);
  return beforeVisibleDay || afterNightLimit;
};

const normalizeTooltipText = (text) => {
  try {
    return decodeURIComponent(escape(text || ''));
  } catch (_) {
    return text || '';
  }
};

const getPlanner2Tooltip = () => {
  let tip = document.getElementById('planner2Tooltip');
  if (!tip) {
    tip = document.createElement('div');
    tip.id = 'planner2Tooltip';
    tip.className = 'planner2-tooltip';
    tip.style.display = 'none';
    document.body.appendChild(tip);
  }
  return tip;
};

const positionTooltip = (e, tooltip) => {
  const offset = 12;
  const rect = tooltip.getBoundingClientRect();
  let left = e.clientX + offset;
  let top = e.clientY + offset;
  const maxLeft = window.innerWidth - rect.width - 8;
  const maxTop = window.innerHeight - rect.height - 8;
  if (left > maxLeft) left = Math.max(8, maxLeft);
  if (top > maxTop) top = Math.max(8, maxTop);
  tooltip.style.left = `${left}px`;
  tooltip.style.top = `${top}px`;
};

const attachTooltip = (el, text, tooltip) => {
  if (!el || !tooltip) return;
  el.dataset.tooltip = normalizeTooltipText(text || '');
  el.addEventListener('mouseenter', (e) => {
    const content = normalizeTooltipText(el.dataset.tooltip || '')
      .split('\n')
      .map(line => `<div>${line}</div>`)
      .join('');
    tooltip.innerHTML = content;
    tooltip.style.display = 'block';
    positionTooltip(e, tooltip);
  });
  el.addEventListener('mousemove', (e) => {
    positionTooltip(e, tooltip);
  });
  el.addEventListener('mouseleave', () => {
    tooltip.style.display = 'none';
  });
};

const timeFromIndex = (idx) => {
  const h = PLANNER2.startHour + Math.floor(idx / 2);
  const m = (idx % 2) ? 30 : 0;
  return `${String(h).padStart(2,'0')}:${String(m).padStart(2,'0')}`;
};

const formatPlanner2ShortDate = (value) => {
  const raw = String(value || '').trim();
  if (!raw) return '';
  const isoMatch = raw.match(/^(\d{4})-(\d{2})-(\d{2})/);
  if (isoMatch) return `${isoMatch[3]}/${isoMatch[2]}`;
  const parsed = new Date(raw);
  if (Number.isNaN(parsed.getTime())) return raw;
  return parsed.toLocaleDateString('pt-PT', { day: '2-digit', month: '2-digit' });
};

const isPlanner2CleanSinceLast = (row) => {
  return row?.clean_since_last === true
    || row?.clean_since_last === 1
    || String(row?.clean_since_last || '').trim() === '1';
};

const planner2Flag = (value) => {
  return value === true || value === 1 || String(value || '').trim() === '1';
};

const getPlanner2LocalDateString = (date = new Date()) => {
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, '0');
  const d = String(date.getDate()).padStart(2, '0');
  return `${y}-${m}-${d}`;
};

const updatePlanner2NowLine = () => {
  const wrap = document.querySelector('.planner2-table-wrap');
  const table = wrap?.querySelector('.planner2-table');
  if (!wrap || !table) return;
  let line = wrap.querySelector('.planner2-now-line');
  if (!line) {
    line = document.createElement('div');
    line.className = 'planner2-now-line';
    wrap.appendChild(line);
  }

  const now = new Date();
  const isToday = planner2RenderedDate === getPlanner2LocalDateString(now);
  const minutes = (now.getHours() * 60) + now.getMinutes();
  const startMinutes = PLANNER2.startHour * 60;
  const endMinutes = PLANNER2.endHour * 60;
  if (!isToday || minutes < startMinutes || minutes > endMinutes) {
    line.hidden = true;
    return;
  }

  const headerHeight = table.querySelector('thead')?.offsetHeight || 44;
  const x = PLANNER2.lodgeWidth + ((minutes - startMinutes) / PLANNER2.slotMinutes) * PLANNER2.slotWidth;
  line.style.left = `${Math.round(x)}px`;
  line.style.top = `${headerHeight}px`;
  line.style.height = `${Math.max(0, table.offsetHeight - headerHeight)}px`;
  line.hidden = false;
};

const normalizePlanner2Time = (value) => {
  const raw = String(value || '').trim();
  if (!raw) return '';
  const match = raw.match(/^(\d{1,2}):(\d{2})/);
  if (match) return `${match[1].padStart(2, '0')}:${match[2]}`;
  const digits = raw.replace(/\D/g, '');
  if (!digits) return '';
  if (digits.length >= 3) {
    return `${digits.slice(0, -2).padStart(2, '0')}:${digits.slice(-2)}`;
  }
  return `${digits.padStart(2, '0')}:00`;
};

const getPlanner2CleaningStatus = (cl, row, duration) => {
  if (planner2RenderedDate !== getPlanner2LocalDateString()) return null;

  const startedAt = normalizePlanner2Time(cl.taskStartedAt || cl.startedAt);
  const finishedAt = normalizePlanner2Time(cl.taskFinishedAt || cl.finishedAt);
  const done = planner2Flag(cl.taskDone) || planner2Flag(cl.done) || planner2Flag(cl.cleaningDone);
  const taskId = String(cl.taskId || '').trim();

  if (finishedAt || done) {
    return {
      key: 'concluida',
      label: 'Concluída',
      icon: 'fa-solid fa-check',
      detail: finishedAt ? `Concluída às ${finishedAt}` : 'Concluída'
    };
  }
  if (startedAt) {
    return {
      key: 'execucao',
      label: 'Em execução',
      icon: 'fa-solid fa-play',
      detail: `Em execução desde ${startedAt}`
    };
  }
  if (!taskId) {
    return null;
  }

  const { h, m } = parseTime(cl.time, '10:00');
  const endMinutes = (h * 60) + m + Number(duration || 0);
  const now = new Date();
  const nowMinutes = (now.getHours() * 60) + now.getMinutes();
  if (Number.isFinite(endMinutes) && nowMinutes > endMinutes) {
    return {
      key: 'atrasada',
      label: 'Atrasada',
      icon: 'fa-solid fa-triangle-exclamation',
      detail: 'Atrasada'
    };
  }

  return null;
};

const buildHead = (slots) => {
  const headRow = document.getElementById('planner2-head-row');
  headRow.innerHTML = `<th class="planner2-col-lodge">Alojamento</th>`;
  for (let h = PLANNER2.startHour; h < PLANNER2.endHour; h++) {
    const th = document.createElement('th');
    th.className = 'planner2-col-hour';
    th.colSpan = 2;
    th.textContent = `${String(h).padStart(2, '0')}:00`;
    headRow.appendChild(th);
  }
};

let planner2Data = [];
let planner2Drag = null;
let planner2SortMode = false;
let planner2OpenDropdown = null;
let planner2Dirty = false;
let planner2SaveBtn = null;
let planner2CancelBtn = null;
let planner2CleaningMenu = null;
let planner2Loading = false;
let planner2LoadingText = null;
let planner2RenderedDate = '';
const planner2DistanceCache = new Map();
const planner2DistancePending = new Set();

const loadPlanner2Teams = async (dateStr) => {
  try {
    const params = dateStr ? `?date=${encodeURIComponent(dateStr)}` : '';
    const res = await fetch(`/generic/api/planner2_teams${params}`);
    const data = await res.json().catch(() => []);
    if (!res.ok || data.error) throw new Error(data.error || res.statusText);
    planner2Teams = Array.isArray(data) ? data : [];
  } catch (err) {
    planner2Teams = [];
    showPlannerToast(`Erro ao carregar equipas: ${err.message || err}`, 'warning');
  }
};

const isPlanner2LpAdminTeam = (team) => {
  const value = team?.LPADMIN ?? team?.lpadmin ?? team?.US_LPADMIN ?? team?.us_lpadmin;
  return value === true || value === 1 || String(value || '').trim() === '1';
};

const setPlanner2Dirty = (isDirty) => {
  planner2Dirty = !!isDirty;
  if (planner2SaveBtn) {
    planner2SaveBtn.disabled = !planner2Dirty;
    planner2SaveBtn.classList.toggle('sz_button_primary', planner2Dirty);
    planner2SaveBtn.classList.toggle('sz_button_ghost', !planner2Dirty);
  }
  if (planner2CancelBtn) {
    planner2CancelBtn.disabled = !planner2Dirty;
  }
};

const showPlanner2Loading = (message = 'A carregar...') => {
  const overlay = document.getElementById('loadingOverlay');
  if (!overlay) return;
  const text = overlay.querySelector('.loading-text');
  if (text) {
    if (planner2LoadingText === null) planner2LoadingText = text.textContent;
    text.textContent = message;
  }
  planner2Loading = true;
  overlay.style.display = 'flex';
  overlay.setAttribute('aria-hidden', 'false');
  requestAnimationFrame(() => {
    overlay.style.opacity = '1';
  });
};

const hidePlanner2Loading = () => {
  const overlay = document.getElementById('loadingOverlay');
  planner2Loading = false;
  if (!overlay) return;
  const text = overlay.querySelector('.loading-text');
  if (text && planner2LoadingText !== null) text.textContent = planner2LoadingText;
  overlay.style.opacity = '0';
  overlay.setAttribute('aria-hidden', 'true');
  setTimeout(() => {
    if (!planner2Loading) overlay.style.display = 'none';
  }, 250);
};

const buildPlanner2Rows = (data) => {
  const map = new Map();
  (Array.isArray(data) ? data : []).forEach((row) => {
    const key = String(row.lodging || '').trim();
    if (!key) return;
    if (!map.has(key)) {
      map.set(key, { ...row, cleanings: [] });
    }
    const entry = map.get(key);
    if (row.cleaning_time || row.cleaning_team) {
      entry.cleanings.push({
        time: row.cleaning_time,
        team: row.cleaning_team,
        id: row.cleaning_id,
        typology: row.typology || row.tp,
        cleaningMinutes: Number(row.cleaning_minutes || 0),
        cleaningDone: row.cleaning_done,
        taskId: row.cleaning_task_id,
        taskDone: row.cleaning_task_done,
        taskStartedAt: row.cleaning_started_at,
        taskFinishedAt: row.cleaning_finished_at,
        taskUser: row.cleaning_task_user
      });
    }
  });
  return Array.from(map.values());
};

const collectPlanner2Payload = (dateStr) => {
  const payload = [];
  planner2Data.forEach((row) => {
    (row.cleanings || []).forEach((cl) => {
      const time = String(cl.time || '').trim();
      const team = String(cl.team || '').trim();
      if (!time || !team) return;
      const entry = {
        ALOJAMENTO: String(row.lodging || '').trim(),
        DATA: dateStr,
        HORA: time,
        EQUIPA: team
      };
      if (cl.id) entry.LPSTAMP = cl.id;
      payload.push(entry);
    });
  });
  return payload;
};

const formatMinutes = (total) => {
  const mins = Math.max(0, Math.round(total || 0));
  const h = Math.floor(mins / 60);
  const m = mins % 60;
  if (h && m) return `${h}h${String(m).padStart(2, '0')}`;
  if (h) return `${h}h`;
  return `${m}m`;
};

const timeToMinutes = (timeStr) => {
  const { h, m } = parseTime(timeStr, '00:00');
  return (h * 60) + m;
};

const minutesToTime = (mins) => {
  const h = Math.floor(mins / 60);
  const m = mins % 60;
  return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}`;
};

const roundUpToSlot = (mins, slot = 30) => {
  if (!Number.isFinite(mins)) return mins;
  return Math.ceil(mins / slot) * slot;
};

const getDistanceKey = (fromStamp, toStamp) => {
  const a = String(fromStamp || '').trim().toLowerCase();
  const b = String(toStamp || '').trim().toLowerCase();
  if (!a || !b) return '';
  if (a === b) return `${a}|||${b}`;
  return a < b ? `${a}|||${b}` : `${b}|||${a}`;
};

const buildAddress = (codpost, local, morada) => {
  const street = '';
  const post = String(codpost || '').trim();
  const city = String(local || '').trim();
  const parts = [street, post, city].filter(Boolean).join(', ');
  if (!parts) return '';
  return /portugal/i.test(parts) ? parts : `${parts}, Portugal`;
};

const fetchPlanner2Distances = async (pairs) => {
  try {
    const res = await fetch('/generic/api/osm_distances', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ pairs })
    });
    if (!res.ok) throw new Error(res.statusText);
    const data = await res.json();
    Object.entries(data || {}).forEach(([key, val]) => {
      const km = typeof val === 'number' ? val : Number(val?.km || 0);
      const seconds = typeof val === 'number' ? 0 : Number(val?.seconds || 0);
      planner2DistanceCache.set(key, { km, seconds });
      planner2DistancePending.delete(key);
    });
    renderPlanner2TeamCards();
  } catch (_) {
    pairs.forEach(p => planner2DistancePending.delete(p.key));
  }
};

const renderPlanner2TeamCards = () => {
  const container = document.getElementById('planner2-team-cards');
  if (!container) return;
  const teamsMap = new Map();
  planner2Data.forEach((row) => {
    (row.cleanings || []).forEach((cl) => {
      const teamName = String(cl.team || '').trim();
      if (!teamName) return;
      const typology = String(cl.typology || row.typology || row.tp || '').trim() || '-';
      const duration = getCleaningDuration(
        { ...cl, cleaningMinutes: Number(cl.cleaningMinutes || row.cleaning_minutes || 0) },
        row.typology || row.tp || ''
      );
      const startMinutes = timeToMinutes(cl.time || '');
      const lodgingStamp = String(row.al_stamp || '').trim();
      const lodgingName = row.lodging || '';
      const hasCheckout = String(row.checkout_reservation || '').trim() || String(row.checkout_time || '').trim();
      const hasCheckin = String(row.checkin_reservation || '').trim() || String(row.checkin_time || '').trim();
      const checkoutTime = parseTime(row.checkout_time, '11:00');
      const checkinTime = parseTime(row.checkin_time, '15:00');
      const earliestStart = hasCheckout ? (checkoutTime.h * 60 + checkoutTime.m) : null;
      const latestFinish = hasCheckin ? (checkinTime.h * 60 + checkinTime.m) : null;
      if (!teamsMap.has(teamName)) {
        teamsMap.set(teamName, { items: [], totalMinutes: 0 });
      }
      const entry = teamsMap.get(teamName);
      entry.items.push({
        lodging: lodgingName,
        stamp: lodgingStamp,
        typology,
        startMinutes,
        duration,
        address: lodgingName,
        earliestStart,
        latestFinish,
        cleaning: cl
      });
      entry.totalMinutes += duration;
    });
  });

  const names = Array.from(teamsMap.keys()).sort((a, b) => a.localeCompare(b));
  container.innerHTML = '';
  const missingPairs = [];
  const addDistancePair = (fromStamp, toStamp) => {
    const key = getDistanceKey(fromStamp, toStamp);
    if (!key) return;
    if (!planner2DistanceCache.has(key) && !planner2DistancePending.has(key)) {
      planner2DistancePending.add(key);
      missingPairs.push({ key, from_stamp: fromStamp, to_stamp: toStamp });
    }
  };
  names.forEach((name) => {
    const meta = teamsMap.get(name);
    const stamps = Array.from(new Set(meta.items.map(i => i.stamp).filter(Boolean)));
    stamps.forEach((fromStamp) => {
      stamps.forEach((toStamp) => {
        if (fromStamp !== toStamp) addDistancePair(fromStamp, toStamp);
      });
    });
  });

  names.forEach((name) => {
    const meta = teamsMap.get(name);
    const plannedItems = meta.items.slice().sort((a, b) => a.startMinutes - b.startMinutes);
    const plannedTimes = plannedItems.map(i => i.startMinutes);
    const card = document.createElement('div');
    card.className = 'planner2-team-card';
    const color = (planner2Teams.find(t => String(t.NOME || '').trim() === name) || {}).COR;
    card.innerHTML = `
      <div class="planner2-team-card-header">
        <span class="planner2-team-chip" style="${color ? `background:${color};` : ''}"></span>
        <span class="planner2-team-name">${name}</span>
        <span class="planner2-team-total">${formatMinutes(meta.totalMinutes)}</span>
      </div>
    `;

    const buildSequence = (items, times, lunchInfo) => {
      const list = document.createElement('div');
      list.className = 'planner2-team-schedule';
      let lastEnd = null;
      const entries = [];
      items.forEach((item, idx) => {
        const startMinutes = times[idx];
        const endMinutes = startMinutes + item.duration;
        if (lastEnd !== null) {
          const prev = entries[entries.length - 1];
          const fromStamp = prev && prev.stamp ? prev.stamp : '';
          const toStamp = item.stamp || '';
          const key = getDistanceKey(fromStamp, toStamp);
          const gapMinutes = Math.max(0, startMinutes - lastEnd);
          const hasGap = gapMinutes > 0;
          if (hasGap || (fromStamp && toStamp && fromStamp !== toStamp)) {
            entries.push({
              type: 'gap',
              duration: gapMinutes,
              distanceKey: key,
              fromName: prev ? prev.lodging : '',
              toName: item.lodging || '',
              start: lastEnd,
              end: startMinutes
            });
          }
        }
        entries.push({
          type: 'clean',
          label: `${item.lodging}`,
          meta: `${minutesToTime(startMinutes)} · ${item.typology} · ${formatMinutes(item.duration)}`,
          address: item.address,
          stamp: item.stamp,
          lodging: item.lodging,
          start: startMinutes,
          end: endMinutes
        });
        lastEnd = endMinutes;
      });
      const lunchStart = lunchInfo && typeof lunchInfo.lunchStart === 'number' ? lunchInfo.lunchStart : null;
      const lunchMinutes = lunchInfo && typeof lunchInfo.lunchMinutes === 'number' ? lunchInfo.lunchMinutes : 0;
      if (lunchStart != null && lunchMinutes) {
        let inserted = false;
        for (let i = 0; i < entries.length; i += 1) {
          const entry = entries[i];
          if (entry.start != null && entry.end != null && lunchStart >= entry.start && lunchStart <= entry.end) {
            entries.splice(i + 1, 0, {
              type: 'lunch',
              label: `Almoço ${minutesToTime(entry.end)}`,
              start: entry.end,
              end: entry.end + lunchMinutes
            });
            inserted = true;
            break;
          }
        }
        if (!inserted) {
          entries.push({
            type: 'lunch',
            label: `Almoço ${minutesToTime(lunchStart)}`,
            start: lunchStart,
            end: lunchStart + lunchMinutes
          });
        }
      }
      entries.forEach((entry, idx) => {
        const tag = document.createElement('div');
        if (entry.type === 'gap') {
          tag.className = 'planner2-team-tag planner2-team-gap';
          const distance = entry.distanceKey ? planner2DistanceCache.get(entry.distanceKey) : null;
          const kmVal = distance ? Number(distance.km || 0) : 0;
          let travelMin = 0;
          if (distance && distance.seconds) {
            travelMin = Math.ceil(Number(distance.seconds || 0) / 60);
          } else if (kmVal > 0) {
            travelMin = 30;
          }
          if (kmVal > 0) {
            travelMin = Math.max(30, Math.ceil(travelMin / 30) * 30);
          }
          const distanceText = entry.distanceKey && planner2DistancePending.has(entry.distanceKey)
            ? '...'
            : `${kmVal} km`;
          tag.innerHTML = `<span>${formatMinutes(travelMin)}</span><span class="planner2-team-tag-meta">${distanceText}</span>`;
          const fromText = entry.fromName || '-';
          const toText = entry.toName || '-';
          tag.title = `De: ${fromText}\nPara: ${toText}\nKey: ${entry.distanceKey || '-'}`;
        } else if (entry.type === 'lunch') {
          tag.className = 'planner2-team-tag planner2-team-lunch';
          const lunchStartText = entry.start != null ? minutesToTime(entry.start) : '';
          const lunchDuration = entry.end != null && entry.start != null ? formatMinutes(entry.end - entry.start) : '';
          tag.innerHTML = `<span><i class="fa-solid fa-utensils"></i> ${lunchStartText}</span><span class="planner2-team-tag-meta">${lunchDuration}</span>`;
        } else {
          tag.className = 'planner2-team-tag';
          tag.innerHTML = `<span>${entry.label}</span><span class="planner2-team-tag-meta">${entry.meta}</span>`;
        }
        list.appendChild(tag);
        if (idx < entries.length - 1) {
          const arrow = document.createElement('span');
          arrow.className = 'planner2-team-arrow';
          arrow.innerHTML = '&#8594;';
          list.appendChild(arrow);
        }
      });
      return list;
    };

    const plannedWrap = document.createElement('div');
    plannedWrap.className = 'planner2-team-section';
    const plannedTitle = document.createElement('div');
    plannedTitle.className = 'planner2-team-section-title';
    plannedTitle.textContent = 'Planeado';
    plannedWrap.appendChild(plannedTitle);

    const getTeamField = (team, keys) => {
      for (let i = 0; i < keys.length; i += 1) {
        const k = keys[i];
        if (team && team[k] != null) return team[k];
      }
      return '';
    };

    const team = planner2Teams.find(t => String(t.NOME || '').trim() === name) || {};
    const teamStartStr = String(getTeamField(team, ['HORAINI', 'horaini', 'HoraIni']) || '09:00');
    const teamEndStr = String(getTeamField(team, ['HORAFIM', 'horafim', 'HoraFim']) || '18:00');
    const teamStartMin = timeToMinutes(teamStartStr);
    const teamEndMin = timeToMinutes(teamEndStr);
    const lunchMinutes = (teamStartMin === 570 || teamEndMin === 1050) ? 30 : 60;
    const LUNCH_START = 12 * 60;
    const LUNCH_END = 14 * 60;

    const getTravelInfo = (fromStamp, toStamp) => {
      const key = getDistanceKey(fromStamp, toStamp);
      if (!key) return { km: 0, seconds: 0, missing: true };
      if (!planner2DistanceCache.has(key)) return { km: 0, seconds: 0, missing: true };
      const v = planner2DistanceCache.get(key) || {};
      return {
        km: Number(v.km || 0),
        seconds: Number(v.seconds || 0),
        missing: false
      };
    };

    const permutations = (items) => {
      const out = [];
      const permute = (prefix, rest) => {
        if (!rest.length) {
          out.push(prefix);
          return;
        }
        for (let i = 0; i < rest.length; i += 1) {
          const next = rest[i];
          const newPrefix = prefix.concat(next);
          const newRest = rest.slice(0, i).concat(rest.slice(i + 1));
          permute(newPrefix, newRest);
        }
      };
      permute([], items);
      return out;
    };

      const simulatePermutation = (order, lunchIndex, allowViolations) => {
        let current = teamStartMin;
        let travelSeconds = 0;
        let totalKm = 0;
        let waitMinutes = 0;
        let lunchTaken = false;
        let lunchStart = null;
        let penalty = 0;
        const alerts = [];
        const scheduleTimes = [];

      const insertLunch = () => {
        if (lunchTaken) return true;
        const latestStart = LUNCH_END - lunchMinutes;
        if (current > latestStart) {
          if (allowViolations) {
            penalty += 100000;
            alerts.push('Sem tempo para almoço');
            lunchTaken = true;
            lunchStart = current;
            return true;
          }
          return false;
        }
        const lunchAt = Math.max(current, LUNCH_START);
        if (lunchAt > latestStart) {
          if (allowViolations) {
            penalty += 100000;
            alerts.push('Almoço fora da janela');
            lunchTaken = true;
            lunchStart = lunchAt;
            return true;
          }
          return false;
        }
        if (lunchAt > current) {
          waitMinutes += lunchAt - current;
        }
        current = lunchAt + lunchMinutes;
        lunchTaken = true;
        lunchStart = lunchAt;
        return true;
      };

      for (let i = 0; i <= order.length; i += 1) {
        if (i === lunchIndex) {
          if (!insertLunch()) return { valid: false, penalty: Infinity, alerts: ['Sem almoço'] };
        }
        if (i === order.length) break;
        const item = order[i];

        if (i > 0) {
          const prev = order[i - 1];
          const travel = getTravelInfo(prev.stamp, item.stamp);
          if (travel.missing) {
            penalty += 2000;
            alerts.push(`Sem rota entre ${prev.lodging} e ${item.lodging}`);
          }
          travelSeconds += travel.seconds;
          totalKm += travel.km;
          current += Math.ceil(travel.seconds / 60);
        }

          if (item.earliestStart != null && current < item.earliestStart) {
            waitMinutes += item.earliestStart - current;
            current = item.earliestStart;
          }

          current = roundUpToSlot(current, 30);
          scheduleTimes.push(current);
          const endTime = current + item.duration;
        if (item.latestFinish != null && endTime > item.latestFinish) {
          const late = endTime - item.latestFinish;
          if (allowViolations) {
            penalty += late * 1000;
            alerts.push(`Falha check-in (${item.lodging})`);
          } else {
            return { valid: false, penalty: Infinity, alerts: [`Falha check-in (${item.lodging})`] };
          }
        }
        current = endTime;
      }

      if (!lunchTaken) {
        if (!insertLunch()) return { valid: false, penalty: Infinity, alerts: ['Sem almoço'] };
      }

      if (current > teamEndMin) {
        const overtime = current - teamEndMin;
        if (allowViolations) {
          penalty += overtime * 500;
          alerts.push('Fim após horário');
        } else {
          return { valid: false, penalty: Infinity, alerts: ['Fim após horário'] };
        }
      }

        return {
          valid: penalty === 0,
          penalty,
          order,
          scheduleTimes,
          travelSeconds,
          totalKm,
          waitMinutes,
          endTime: current,
          lunchMinutes,
        lunchStart,
        alerts
      };
    };

    const buildSuggestionOrder = () => {
      if (plannedItems.length <= 1) {
        return {
          items: plannedItems.slice(),
          times: plannedItems.length ? [plannedItems[0].startMinutes] : [],
          metrics: {
            totalKm: 0,
            travelSeconds: 0,
            waitMinutes: 0,
            endTime: teamStartMin,
            lunchMinutes,
            lunchStart: null,
            alerts: [],
            valid: true
          }
        };
      }

      const orders = permutations(plannedItems);
      let bestValid = null;
      let bestFallback = null;

      orders.forEach((order) => {
        for (let lunchIndex = 0; lunchIndex <= order.length; lunchIndex += 1) {
          const res = simulatePermutation(order, lunchIndex, false);
          if (res.valid) {
            const resStart = Array.isArray(res.scheduleTimes) && res.scheduleTimes.length ? res.scheduleTimes[0] : teamStartMin;
            const bestStart = bestValid && Array.isArray(bestValid.scheduleTimes) && bestValid.scheduleTimes.length
              ? bestValid.scheduleTimes[0]
              : teamStartMin;
            if (
              !bestValid
              || res.endTime < bestValid.endTime
              || (res.endTime === bestValid.endTime && resStart < bestStart)
              || (res.endTime === bestValid.endTime && resStart === bestStart && res.totalKm < bestValid.totalKm)
              || (res.endTime === bestValid.endTime && resStart === bestStart && res.totalKm === bestValid.totalKm && res.waitMinutes < bestValid.waitMinutes)
              || (res.endTime === bestValid.endTime && resStart === bestStart && res.totalKm === bestValid.totalKm && res.waitMinutes === bestValid.waitMinutes && res.travelSeconds < bestValid.travelSeconds)
            ) {
              bestValid = res;
            }
          }
          const fallback = simulatePermutation(order, lunchIndex, true);
          if (!bestFallback || fallback.penalty < bestFallback.penalty) {
            bestFallback = fallback;
          }
        }
      });

      const chosen = bestValid || bestFallback;
      return {
        items: chosen ? chosen.order : plannedItems.slice(),
        times: chosen ? chosen.scheduleTimes : plannedItems.map(i => i.startMinutes),
        metrics: {
          totalKm: chosen ? chosen.totalKm : 0,
          travelSeconds: chosen ? chosen.travelSeconds : 0,
          waitMinutes: chosen ? chosen.waitMinutes : 0,
          endTime: chosen ? chosen.endTime : teamStartMin,
          startTime: chosen && Array.isArray(chosen.scheduleTimes) && chosen.scheduleTimes.length ? chosen.scheduleTimes[0] : teamStartMin,
          lunchMinutes,
          lunchStart: chosen ? chosen.lunchStart : null,
          alerts: chosen ? chosen.alerts : ['Sem solução válida'],
          valid: !!(chosen && chosen.valid)
        }
      };
    };

    const plannedOrder = plannedItems.slice().sort((a, b) => a.startMinutes - b.startMinutes);
    let plannedMetrics = null;
    if (plannedOrder.length) {
      let totalKm = 0;
      let travelSeconds = 0;
      let waitMinutes = 0;
      for (let i = 0; i < plannedOrder.length - 1; i += 1) {
        const cur = plannedOrder[i];
        const next = plannedOrder[i + 1];
        const endCur = cur.startMinutes + cur.duration;
        const gap = Math.max(0, next.startMinutes - endCur);
        waitMinutes += gap;
        const travel = getTravelInfo(cur.stamp, next.stamp);
        travelSeconds += travel.seconds;
        totalKm += travel.km;
      }
      const endTime = plannedOrder[plannedOrder.length - 1].startMinutes + plannedOrder[plannedOrder.length - 1].duration;
      let lunchStart = null;
      for (let i = 0; i < plannedOrder.length - 1; i += 1) {
        const endCur = plannedOrder[i].startMinutes + plannedOrder[i].duration;
        const nextStart = plannedOrder[i + 1].startMinutes;
        const gapStart = Math.max(endCur, LUNCH_START);
        const gapEnd = Math.min(nextStart, LUNCH_END);
        if (gapEnd - gapStart >= lunchMinutes) {
          lunchStart = gapStart;
          break;
        }
      }
      if (lunchStart == null) {
        const gapStart = Math.max(endTime, LUNCH_START);
        if (LUNCH_END - gapStart >= lunchMinutes) {
          lunchStart = gapStart;
        }
      }
      plannedMetrics = {
        totalKm,
        travelSeconds,
        waitMinutes,
        endTime,
        lunchMinutes,
        lunchStart
      };
    }

    if (plannedMetrics) {
      const plannedMeta = document.createElement('div');
      plannedMeta.className = 'planner2-team-section-meta';
      const travelMinutes = Math.round((plannedMetrics.travelSeconds || 0) / 60);
      const endText = minutesToTime(plannedMetrics.endTime || teamStartMin);
      plannedMeta.textContent = `${Number(plannedMetrics.totalKm || 0).toFixed(2)} km · Desloc. ${formatMinutes(travelMinutes)} · Espera ${formatMinutes(plannedMetrics.waitMinutes || 0)} · Fim ${endText} · Almoço ${plannedMetrics.lunchMinutes || 0}m`;
      plannedWrap.appendChild(plannedMeta);
    }

    plannedWrap.appendChild(buildSequence(plannedItems, plannedTimes, plannedMetrics));

    const suggestion = buildSuggestionOrder();
    const suggestedItems = suggestion.items || [];
    const suggestionTimes = suggestion.times || plannedTimes;
    const suggestionMetrics = suggestion.metrics || {};
    const suggestedWrap = document.createElement('div');
    suggestedWrap.className = 'planner2-team-section planner2-team-section-suggested';
    const suggestedHeader = document.createElement('div');
    suggestedHeader.className = 'planner2-team-section-header';
    const suggestedTitle = document.createElement('div');
    suggestedTitle.className = 'planner2-team-section-title';
    const sameOrder = suggestedItems.length === plannedItems.length
      && suggestedItems.every((item, idx) => item === plannedItems[idx]);
    const plannedScore = plannedMetrics ? (
      (plannedMetrics.endTime || 0) * 1000000
      + (plannedMetrics.waitMinutes || 0) * 1000
      + (plannedMetrics.travelSeconds || 0)
      + (plannedMetrics.totalKm || 0)
    ) : null;
    const suggestedScore = suggestionMetrics ? (
      (suggestionMetrics.endTime || 0) * 1000000
      + (suggestionMetrics.waitMinutes || 0) * 1000
      + (suggestionMetrics.travelSeconds || 0)
      + (suggestionMetrics.totalKm || 0)
    ) : null;
    const suggestionWorseOrEqual = plannedScore != null && suggestedScore != null && suggestedScore >= plannedScore;
    suggestedTitle.textContent = 'Sugestão';
    if (!sameOrder && !suggestionWorseOrEqual) {
      const metaLine = document.createElement('div');
      metaLine.className = 'planner2-team-section-meta';
      const travelMinutes = Math.round((suggestionMetrics.travelSeconds || 0) / 60);
      const fallbackStart = plannedTimes.length ? plannedTimes[0] : 0;
      const endText = minutesToTime(suggestionMetrics.endTime || fallbackStart);
      metaLine.textContent = `${Number(suggestionMetrics.totalKm || 0).toFixed(2)} km · Desloc. ${formatMinutes(travelMinutes)} · Espera ${formatMinutes(suggestionMetrics.waitMinutes || 0)} · Fim ${endText} · Almoço ${suggestionMetrics.lunchMinutes || 0}m`;
      const applyBtn = document.createElement('button');
      applyBtn.type = 'button';
      applyBtn.className = 'btn btn-sm btn-outline-primary planner2-team-apply';
      applyBtn.textContent = 'Aplicar';
      applyBtn.addEventListener('click', () => {
        const sortedTimes = plannedTimes.slice().sort((a, b) => a - b);
        suggestedItems.forEach((item, idx) => {
          const minutes = sortedTimes[idx] ?? item.startMinutes;
          const timeStr = minutesToTime(minutes);
          if (item.cleaning) {
            item.cleaning.time = timeStr;
          }
        });
        setPlanner2Dirty(true);
        const slots = buildSlots();
        buildHead(slots);
        renderRows(planner2Data, slots);
        renderPlanner2TeamCards();
      });
      suggestedHeader.appendChild(suggestedTitle);
      suggestedHeader.appendChild(applyBtn);
      suggestedWrap.appendChild(suggestedHeader);
      suggestedWrap.appendChild(metaLine);
      if (Array.isArray(suggestionMetrics.alerts) && suggestionMetrics.alerts.length) {
        const alertLine = document.createElement('div');
        alertLine.className = 'planner2-team-section-alerts';
        alertLine.textContent = suggestionMetrics.alerts.join(' | ');
        suggestedWrap.appendChild(alertLine);
      }
      suggestedWrap.appendChild(buildSequence(suggestedItems, suggestionTimes, suggestionMetrics));
      card.appendChild(plannedWrap);
      card.appendChild(suggestedWrap);
    } else {
      card.appendChild(plannedWrap);
    }
    container.appendChild(card);
  });

  if (missingPairs.length) {
    fetchPlanner2Distances(missingPairs);
  }
};

const renderRows = (data, slots) => {
  const tbody = document.getElementById('planner2-body');
  const lodgeWidth = PLANNER2.lodgeWidth;
  tbody.innerHTML = '';
  const tooltip = getPlanner2Tooltip();
  const showOccupied = document.getElementById('planner2-show-occupied')?.checked ?? true;
  const showEmpty = document.getElementById('planner2-show-empty')?.checked ?? true;

  const rows = data.map((row, index) => ({ row, index }));
  if (planner2SortMode) {
    const getCleanKey = (row) => {
      const list = Array.isArray(row.cleanings) ? row.cleanings.slice() : [];
      if (!list.length) return { has: false, team: '', time: '' };
      list.sort((a, b) => String(a.time || '').localeCompare(String(b.time || '')));
      const first = list[0] || {};
      return {
        has: true,
        team: String(first.team || '').trim(),
        time: String(first.time || '').trim()
      };
    };
    rows.sort((a, b) => {
      const ka = getCleanKey(a.row);
      const kb = getCleanKey(b.row);
      if (ka.has !== kb.has) return ka.has ? -1 : 1;
      if (ka.team !== kb.team) return ka.team.localeCompare(kb.team);
      if (ka.time !== kb.time) return ka.time.localeCompare(kb.time);
      return String(a.row.lodging || '').localeCompare(String(b.row.lodging || ''));
    });
  }
  rows.forEach((entry, displayIndex) => {
    entry.displayIndex = displayIndex;
  });
  rows.sort((a, b) => {
    const cleanA = isPlanner2CleanSinceLast(a.row);
    const cleanB = isPlanner2CleanSinceLast(b.row);
    if (cleanA !== cleanB) return cleanA ? 1 : -1;
    return a.displayIndex - b.displayIndex;
  });

  rows.forEach(({ row }) => {
    const hasCheckout = !!row.checkout_reservation;
    const hasCheckin = !!row.checkin_reservation;
    const hasCleaning = Array.isArray(row.cleanings) && row.cleanings.length > 0;
    const isOccupied = Number(row.planner_status || 0) === 3;
    const isEmpty = Number(row.planner_status || 0) === 4;

    if (!hasCheckout && !hasCheckin && !hasCleaning) {
      if ((isOccupied && !showOccupied) || (isEmpty && !showEmpty)) {
        return;
      }
      if (!isOccupied && !isEmpty && !showOccupied && !showEmpty) {
        return;
      }
    }

    const tr = document.createElement('tr');
    const lodgeTd = document.createElement('td');
    lodgeTd.className = 'planner2-col-lodge';
    lodgeTd.textContent = row.lodging || '';
    lodgeTd.style.width = `${lodgeWidth}px`;
    lodgeTd.style.minWidth = `${lodgeWidth}px`;
    lodgeTd.style.maxWidth = `${lodgeWidth}px`;
    tr.appendChild(lodgeTd);

    slots.forEach((slot) => {
      const td = document.createElement('td');
      td.className = 'planner2-slot';
      td.dataset.time = slot;
      td.addEventListener('click', (e) => {
        e.stopPropagation();
        openPlanner2TeamDropdown(td, row, slot);
      });
      tr.appendChild(td);
    });

    tbody.appendChild(tr);

    const cleanSinceLast = isPlanner2CleanSinceLast(row);
    const lastCleanTeam = String(row.last_team || '').trim();
    const lastCleanDate = formatPlanner2ShortDate(row.last_clean_date);
    if (cleanSinceLast && lastCleanTeam && lastCleanDate) {
      const cleanIdx = timeToIndex(7, 0);
      const totalSlots = slots.length;
      const slotCount = Math.min(8, Math.max(1, totalSlots - cleanIdx));
      const bar = document.createElement('div');
      bar.className = 'planner2-bar planner2-bar-clean-state';
      bar.style.left = `${lodgeWidth + cleanIdx * PLANNER2.slotWidth}px`;
      bar.style.width = `${slotCount * PLANNER2.slotWidth}px`;
      attachTooltip(bar, `Limpo por ${lastCleanTeam} a ${lastCleanDate}`, tooltip);
      const label = document.createElement('span');
      label.className = 'planner2-bar-label';
      label.textContent = `Limpo por ${lastCleanTeam} a ${lastCleanDate}`;
      bar.appendChild(label);
      tr.appendChild(bar);
    }

    const checkoutHas = !!row.checkout_reservation;
    if (checkoutHas) {
      const checkoutHasDefinedTime = hasDefinedPlannerTime(row.checkout_time);
      let { h, m } = parseTime(row.checkout_time, '11:00');
      if (h < 7 || (h === 7 && m <= 0)) {
        h = 7;
        m = 30;
      }
      const endIdx = timeToIndex(h, m);
      const checkoutLabel = checkoutHasDefinedTime ? `${String(h).padStart(2,'0')}:${String(m).padStart(2,'0')}` : 'N/D';
      const bar = document.createElement('div');
      bar.className = 'planner2-bar planner2-bar-checkout';
      bar.style.left = `${lodgeWidth}px`;
      bar.style.width = `${endIdx * PLANNER2.slotWidth}px`;
      const guestsOut = Number(row.checkout_people || 0);
      const nightsOut = Number(row.checkout_nights || 0);
      const typology = row.typology || '';
      const lastTeam = row.last_team || '';
      const guestName = String(row.checkout_guest || '').trim();
      const guestCountry = String(row.checkout_country || '').trim();
      attachTooltip(bar, [
        `Hóspede: ${guestName || '-'}`,
        `País: ${guestCountry || '-'}`,
        `Checkout: ${checkoutLabel}`,
        `Hóspedes: ${guestsOut}`,
        `Noites: ${nightsOut}`,
        `Tipologia: ${typology || '-'}`,
        `Última limpeza: ${lastTeam || '-'}`
      ].join('\n'), tooltip);
      const label = document.createElement('span');
      label.className = 'planner2-bar-label planner2-bar-label-right';
      label.textContent = checkoutLabel;
      bar.appendChild(label);
      tr.appendChild(bar);
    }

    const checkinHas = !!row.checkin_reservation;
    if (checkinHas) {
      const checkinHasDefinedTime = hasDefinedPlannerTime(row.checkin_time);
      const originalTime = parseTime(row.checkin_time, '15:00');
      let { h, m } = originalTime;
      let barHour = h;
      let barMin = m;
      if (shouldAnchorCheckinAtNight(h, m)) {
        barHour = 21;
        barMin = 0;
      }
      const startIdx = timeToIndex(barHour, barMin);
      const totalSlots = slots.length;
      const guests = Number(row.checkin_people || 0);
      const nights = Number(row.checkin_nights || 0);
      const checkinTimeLabel = checkinHasDefinedTime ? `${String(h).padStart(2,'0')}:${String(m).padStart(2,'0')}` : 'N/D';
      const checkinLabel = `${checkinTimeLabel} · ${guests}P · ${nights}N`;
      const bar = document.createElement('div');
      bar.className = 'planner2-bar planner2-bar-checkin';
      bar.style.left = `${lodgeWidth + startIdx * PLANNER2.slotWidth}px`;
      bar.style.width = `${(totalSlots - startIdx) * PLANNER2.slotWidth}px`;
      const guestName = String(row.checkin_guest || '').trim();
      const guestCountry = String(row.checkin_country || '').trim();
      const typology = row.typology || '';
      attachTooltip(bar, [
        `Hóspede: ${guestName || '-'}`,
        `País: ${guestCountry || '-'}`,
        `Checkin: ${checkinTimeLabel}`,
        `Hóspedes: ${guests}`,
        `Noites: ${nights}`,
        `Tipologia: ${typology || '-'}`
      ].join('\n'), tooltip);
      const label = document.createElement('span');
      label.className = 'planner2-bar-label planner2-bar-label-left';
      label.textContent = checkinLabel;
      label.textContent = normalizeTooltipText(label.textContent);
      bar.appendChild(label);
      tr.appendChild(bar);
    }

    if (Number(row.planner_status || 0) === 3) {
      const totalSlots = slots.length;
      const guests = Number(row.occupied_people || row.checkout_people || row.checkin_people || 0);
      const nights = Number(row.occupied_nights || row.checkout_nights || row.checkin_nights || 0);
      const guestName = String(row.occupied_guest || row.checkin_guest || row.checkout_guest || '').trim();
      const guestCountry = String(row.occupied_country || row.checkin_country || row.checkout_country || '').trim();
      const typology = row.typology || '';
      const bar = document.createElement('div');
      bar.className = 'planner2-bar planner2-bar-occupied planner2-bar-center';
      bar.style.left = `${lodgeWidth}px`;
      bar.style.width = `${totalSlots * PLANNER2.slotWidth}px`;
      const tooltipLines = [
        `Hóspede: ${guestName || '-'}`,
        `País: ${guestCountry || '-'}`,
        `Hóspedes: ${guests || '-'}`,
        `Noites: ${nights || '-'}`,
        `Tipologia: ${typology || '-'}`
      ];
      attachTooltip(bar, tooltipLines.join('\n'), tooltip);
      const label = document.createElement('span');
      label.className = 'planner2-bar-label planner2-bar-label-left';
      label.textContent = guests && nights ? `${guests}P · ${nights}N` : '';
      bar.appendChild(label);
      tr.appendChild(bar);
    }

    if (hasCleaning) {
      const cleanings = row.cleanings.slice();
      cleanings.forEach((cl) => {
        if (!cl.id && !cl._tmpId) {
          cl._tmpId = `tmp-${Date.now()}-${Math.random().toString(36).slice(2)}`;
        }
      });
      const bars = cleanings.map((cl, idx) => {
        const { h, m } = parseTime(cl.time, '10:00');
        let startIdx = timeToIndex(h, m);
        if (startIdx < 0) startIdx = 0;
        const duration = getCleaningDuration(
          { ...cl, cleaningMinutes: Number(cl.cleaningMinutes || row.cleaning_minutes || 0) },
          row.typology || row.tp || ''
        );
        const status = getPlanner2CleaningStatus(cl, row, duration);
        const slotsCount = Math.max(1, Math.ceil(duration / 30));
        const totalSlots = slots.length;
        const cappedSlots = Math.min(slotsCount, Math.max(0, totalSlots - startIdx));
        const endIdx = startIdx + cappedSlots;
        const key = cl._tmpId || cl.id || `${idx}`;
        return { cl, startIdx, cappedSlots, endIdx, key, status };
      });

      bars.sort((a, b) => {
        if (a.startIdx !== b.startIdx) return a.startIdx - b.startIdx;
        if (a.endIdx !== b.endIdx) return a.endIdx - b.endIdx;
        return String(a.key).localeCompare(String(b.key));
      });

      const lanes = [];
      bars.forEach((item) => {
        let laneIndex = 0;
        while (lanes[laneIndex] && lanes[laneIndex] > item.startIdx) {
          laneIndex += 1;
        }
        lanes[laneIndex] = item.endIdx;
        item.laneIndex = laneIndex;
      });

      const laneCount = Math.max(1, lanes.length);
      const rowHeight = 32 + (laneCount - 1) * 26;
      tr.style.height = `${rowHeight}px`;
      tr.querySelectorAll('td').forEach(td => { td.style.height = `${rowHeight}px`; });

      bars.forEach(({ cl, startIdx, cappedSlots, laneIndex, key, status }) => {
        const bar = document.createElement('div');
        bar.className = 'planner2-bar planner2-bar-cleaning';
        if (status) {
          bar.classList.add('planner2-bar-cleaning-status', `planner2-cleaning-status-${status.key}`);
        }
        bar.dataset.startIdx = String(startIdx);
        bar.dataset.slotCount = String(cappedSlots);
        bar.dataset.tmpId = String(key);
        const topOffset = 4 + (laneIndex * 26);
        bar.style.top = `${topOffset}px`;
        bar.style.left = `${lodgeWidth + startIdx * PLANNER2.slotWidth}px`;
        bar.style.width = `${cappedSlots * PLANNER2.slotWidth}px`;
        const teamColor = (planner2Teams.find(t => String(t.NOME || '').trim() === String(cl.team || '').trim()) || {}).COR;
        if (teamColor) {
          bar.style.background = `linear-gradient(90deg, ${teamColor}66, ${teamColor}33)`;
          bar.style.borderColor = `${teamColor}99`;
        }
        const label = document.createElement('span');
        label.className = 'planner2-bar-label';
        label.textContent = String(cl.team || '').trim();
        bar.appendChild(label);
        if (status) {
          const icon = document.createElement('span');
          icon.className = 'planner2-clean-status-icon';
          icon.title = status.label;
          icon.setAttribute('aria-label', status.label);
          const i = document.createElement('i');
          i.className = status.icon;
          icon.appendChild(i);
          bar.appendChild(icon);
          const taskUser = String(cl.taskUser || '').trim();
          attachTooltip(bar, [
            `Limpeza: ${String(cl.team || '').trim() || '-'}`,
            `Estado: ${status.detail || status.label}`,
            taskUser ? `Utilizador: ${taskUser}` : '',
            `Hora: ${normalizePlanner2Time(cl.time) || '-'}`
          ].filter(Boolean).join('\n'), tooltip);
        }
        tr.appendChild(bar);
        bar.addEventListener('mousedown', (e) => {
          e.preventDefault();
          planner2Drag = {
            bar,
            row,
            startIdx,
            laneIndex,
            key,
            offsetX: e.clientX - bar.getBoundingClientRect().left
          };
          bar.dataset.dragged = '0';
          bar.dataset.dragStartX = String(e.clientX);
          bar.classList.add('planner2-bar-dragging');
        });
        bar.addEventListener('click', (e) => {
          e.stopPropagation();
          if (bar.dataset.dragged === '1') return;
          openPlanner2CleaningMenu(bar, row, cl);
        });
      });
    }
  });
  tbody.querySelectorAll('.planner2-bar-label').forEach((el) => {
    el.textContent = normalizeTooltipText(el.textContent);
  });
  requestAnimationFrame(updatePlanner2NowLine);
};

const loadPlanner2 = async (dateStr) => {
  showPlanner2Loading('A carregar...');
  try {
    planner2RenderedDate = String(dateStr || '').slice(0, 10);
    planner2DistanceCache.clear();
    planner2DistancePending.clear();
    await loadPlanner2Teams(dateStr);
    const res = await fetch(`/generic/api/cleaning_plan?date=${encodeURIComponent(dateStr)}`);
    if (!res.ok) throw new Error(res.statusText);
    const data = await res.json();
    planner2Data = buildPlanner2Rows(data);
    const slots = buildSlots();
    buildHead(slots);
    renderRows(planner2Data, slots);
    renderPlanner2TeamCards();
    setPlanner2Dirty(false);
  } finally {
    hidePlanner2Loading();
  }
};

const closePlanner2Menu = () => {
  if (planner2CleaningMenu) {
    planner2CleaningMenu.remove();
    planner2CleaningMenu = null;
  }
};

const openPlanner2CleaningMenu = (bar, row, cl) => {
  closePlanner2Menu();
  const rect = bar.getBoundingClientRect();
  const menu = document.createElement('div');
  menu.className = 'planner2-cleaning-menu';
  const items = [
    { label: 'Abrir', icon: 'fa-regular fa-pen-to-square' },
    { label: 'Eliminar', icon: 'fa-regular fa-trash-can' }
  ];
  items.forEach(({ label, icon }) => {
    const item = document.createElement('div');
    item.className = 'planner2-cleaning-menu-item';
    const i = document.createElement('i');
    i.className = icon;
    const span = document.createElement('span');
    span.textContent = label;
    item.appendChild(i);
    item.appendChild(span);
    item.addEventListener('click', async (e) => {
      e.stopPropagation();
      closePlanner2Menu();
      if (label === 'Abrir') {
        if (cl.id) {
          window.open(`/generic/form/LP/${cl.id}`, '_blank');
        }
        return;
      }
      if (cl.id) {
        try {
          const res = await fetch(`/generic/api/LP/${encodeURIComponent(cl.id)}/planner-delete`, { method: 'DELETE' });
          const data = await res.json().catch(() => ({}));
          if (!res.ok || data.error) throw new Error(data.error || res.statusText || 'Erro ao eliminar');
        } catch (err) {
          showPlannerToast(`Erro ao eliminar: ${err.message || err}`, 'danger');
          return;
        }
      }
      row.cleanings = (row.cleanings || []).filter((c) => {
        const cKey = c._tmpId || c.id || '';
        const clKey = cl._tmpId || cl.id || '';
        return String(cKey) !== String(clKey);
      });
      showPlannerToast('Registo eliminado.', 'success');
      setPlanner2Dirty(true);
      const slots = buildSlots();
      buildHead(slots);
      renderRows(planner2Data, slots);
      renderPlanner2TeamCards();
    });
    menu.appendChild(item);
  });
  menu.style.visibility = 'hidden';
  document.body.appendChild(menu);
  const viewportPadding = 8;
  const gap = 6;
  const menuRect = menu.getBoundingClientRect();
  const menuWidth = Math.ceil(menuRect.width || 150);
  const menuHeight = Math.ceil(menuRect.height || 0);
  const viewportWidth = window.innerWidth || document.documentElement.clientWidth || 0;
  const viewportHeight = window.innerHeight || document.documentElement.clientHeight || 0;
  const anchorMidY = rect.top + (rect.height / 2);

  let left = rect.left;
  if (left + menuWidth > viewportWidth - viewportPadding) {
    left = Math.max(viewportPadding, viewportWidth - menuWidth - viewportPadding);
  }
  if (left < viewportPadding) left = viewportPadding;

  let top = anchorMidY > (viewportHeight / 2)
    ? rect.top - menuHeight - gap
    : rect.bottom + gap;
  if (top < viewportPadding) top = viewportPadding;
  if (top + menuHeight > viewportHeight - viewportPadding) {
    top = Math.max(viewportPadding, viewportHeight - menuHeight - viewportPadding);
  }

  menu.style.left = `${Math.round(left)}px`;
  menu.style.top = `${Math.round(top)}px`;
  menu.style.visibility = '';
  planner2CleaningMenu = menu;
  setTimeout(() => {
    window.addEventListener('click', closePlanner2Menu, { once: true });
  }, 0);
};

const getCleaningDuration = (source, fallbackTypology = '') => {
  const configuredMinutes = Number(
    typeof source === 'object' && source !== null
      ? (source.cleaningMinutes ?? source.cleaning_minutes ?? source.lpTempo ?? source.lp_tempo ?? 0)
      : 0
  );
  if (Number.isFinite(configuredMinutes) && configuredMinutes > 0) {
    return configuredMinutes;
  }

  const typology = typeof source === 'string'
    ? source
    : (source?.typology || source?.tp || fallbackTypology || '');

  switch ((typology || '').trim()) {
    case 'T0':
    case 'T1':
      return 60;
    case 'T2':
    case 'T3':
      return 90;
    case 'T4':
    case 'T5':
      return 120;
    default:
      return 60;
  }
};

const setupPlanner2 = () => {
  const dateInput = document.getElementById('planner2-date');
  const prevBtn = document.getElementById('planner2-prev');
  const nextBtn = document.getElementById('planner2-next');
  const sortBtn = document.getElementById('planner2-sort-cleaning');
  const printBtn = document.getElementById('planner2-print-labels');
  planner2SaveBtn = document.getElementById('planner2-save');
  planner2CancelBtn = document.getElementById('planner2-cancel');
  if (planner2SaveBtn) {
    planner2SaveBtn.classList.add('sz_button_ghost');
    planner2SaveBtn.classList.remove('sz_button_primary');
    planner2SaveBtn.disabled = true;
  }
  if (planner2CancelBtn) planner2CancelBtn.disabled = true;
  const showOcc = document.getElementById('planner2-show-occupied');
  const showEmpty = document.getElementById('planner2-show-empty');
  let currentDate = window.PLANNER2_INITIAL_DATE || new Date().toISOString().slice(0, 10);
  let suppressDateChange = false;

  const canChangePlanner2Date = () => {
    if (!planner2Dirty) return true;
    showPlannerToast('Existem alterações por gravar. Grave ou cancele antes de mudar de data.', 'warning');
    return false;
  };

  const resetPickerDate = () => {
    if (dateInput?._flatpickr) {
      suppressDateChange = true;
      dateInput._flatpickr.setDate(currentDate, false);
      suppressDateChange = false;
    } else if (dateInput) {
      dateInput.value = currentDate;
    }
  };

  const setPlanner2Date = (nextDate, updatePicker = true) => {
    if (!nextDate || nextDate === currentDate || planner2Loading) {
      if (nextDate !== currentDate) resetPickerDate();
      return;
    }
    if (!canChangePlanner2Date()) {
      resetPickerDate();
      return;
    }
    currentDate = nextDate;
    if (updatePicker && dateInput?._flatpickr) {
      suppressDateChange = true;
      dateInput._flatpickr.setDate(currentDate, false);
      suppressDateChange = false;
    }
    loadPlanner2(currentDate).catch((err) => {
      showPlannerToast(`Erro ao carregar planeamento: ${err.message || err}`, 'danger');
    });
  };

  flatpickr(dateInput, {
    defaultDate: currentDate,
    dateFormat: 'Y-m-d',
    onChange: (_, dateStr) => {
      if (suppressDateChange) return;
      setPlanner2Date(dateStr, false);
    }
  });

  const changeDay = (delta) => {
    const d = new Date(currentDate);
    d.setDate(d.getDate() + delta);
    setPlanner2Date(d.toISOString().slice(0, 10));
  };

  prevBtn.addEventListener('click', () => changeDay(-1));
  nextBtn.addEventListener('click', () => changeDay(1));
  const rerender = () => {
    const slots = buildSlots();
    buildHead(slots);
    renderRows(planner2Data, slots);
    renderPlanner2TeamCards();
  };
  showOcc?.addEventListener('change', rerender);
  showEmpty?.addEventListener('change', rerender);
  sortBtn?.addEventListener('click', () => {
    planner2SortMode = !planner2SortMode;
    sortBtn.classList.toggle('sz_button_ghost', !planner2SortMode);
    sortBtn.classList.toggle('sz_button_primary', planner2SortMode);
    rerender();
  });

  printBtn?.addEventListener('click', async () => {
    const date = dateInput?.value || currentDate;
    if (!date) {
      alert('Seleciona uma data primeiro!');
      return;
    }
    printBtn.disabled = true;
    printBtn.innerHTML = '<i class="fa-solid fa-spinner fa-print"></i>';
    try {
      const res = await fetch(`/planner/api/imprimir_etiquetas?date=${encodeURIComponent(date)}`, {
        method: 'POST'
      });
      const data = await res.json();
      if (data.success) {
        alert('Etiquetas criadas!');
      } else {
        alert(`Erro: ${data.error || 'Erro desconhecido.'}`);
      }
    } catch (err) {
      alert(`Erro ao criar etiquetas: ${err.message || err}`);
    } finally {
      printBtn.disabled = false;
      printBtn.innerHTML = '<i class="fa-solid fa-print"></i>';
    }
  });

  planner2SaveBtn?.addEventListener('click', async () => {
    if (planner2SaveBtn.disabled || planner2Loading) return;
    const payload = collectPlanner2Payload(currentDate);
    if (!payload.length) {
      showPlannerToast('Nada para gravar.', 'warning');
      setPlanner2Dirty(false);
      return;
    }
    planner2SaveBtn.disabled = true;
    try {
      const res = await fetch('/generic/api/LP/gravar', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      if (!res.ok) throw new Error(res.statusText);
      const data = await res.json();
      if (!data.success) throw new Error(data.message || 'Erro ao gravar');
      await loadPlanner2(currentDate);
      setPlanner2Dirty(false);
      showPlannerToast('Registos gravados.', 'success');
    } catch (err) {
      showPlannerToast(`Erro ao gravar: ${err.message || err}`, 'danger');
      setPlanner2Dirty(true);
    }
  });

  planner2CancelBtn?.addEventListener('click', async () => {
    if (planner2CancelBtn.disabled || planner2Loading) return;
    try {
      await loadPlanner2(currentDate);
      showPlannerToast('Alterações canceladas.', 'success');
    } catch (err) {
      showPlannerToast(`Erro ao cancelar alterações: ${err.message || err}`, 'danger');
      setPlanner2Dirty(true);
    }
  });

  loadPlanner2(currentDate).catch((err) => {
    showPlannerToast(`Erro ao carregar planeamento: ${err.message || err}`, 'danger');
  });
  window.setInterval(updatePlanner2NowLine, 60000);
};

document.addEventListener('DOMContentLoaded', setupPlanner2);

const openPlanner2TeamDropdown = (cell, row, slot) => {
  if (planner2OpenDropdown) {
    planner2OpenDropdown.remove();
    planner2OpenDropdown = null;
  }
  const rect = cell.getBoundingClientRect();
  const dropdown = document.createElement('div');
  dropdown.className = 'planner2-team-dropdown';
  if (!planner2Teams.length) {
    const empty = document.createElement('div');
    empty.className = 'planner2-team-item';
    empty.textContent = 'Sem equipas disponiveis';
    empty.style.cursor = 'default';
    empty.style.opacity = '0.72';
    dropdown.appendChild(empty);
  }
  const appendTeamItem = (team) => {
    const item = document.createElement('div');
    item.className = 'planner2-team-item';
    const dot = document.createElement('span');
    dot.className = 'planner2-team-dot';
    if (team.COR) dot.style.background = team.COR;
    const label = document.createElement('span');
    label.textContent = team.NOME;
    item.appendChild(dot);
    item.appendChild(label);
    item.addEventListener('click', (e) => {
      e.stopPropagation();
      const existing = row.cleanings || [];
      existing.push({
        time: slot,
        team: team.NOME,
        typology: row.typology || row.tp,
        cleaningMinutes: Number(row.cleaning_minutes || 0),
        _tmpId: `tmp-${Date.now()}-${Math.random().toString(36).slice(2)}`
      });
      row.cleanings = existing;
      setPlanner2Dirty(true);
      if (planner2OpenDropdown) {
        planner2OpenDropdown.remove();
        planner2OpenDropdown = null;
      }
      const slots = buildSlots();
      buildHead(slots);
      renderRows(planner2Data, slots);
      renderPlanner2TeamCards();
    });
    dropdown.appendChild(item);
  };

  const regularTeams = planner2Teams.filter((team) => !isPlanner2LpAdminTeam(team));
  const lpAdminTeams = planner2Teams.filter(isPlanner2LpAdminTeam);
  regularTeams.forEach(appendTeamItem);
  if (regularTeams.length && lpAdminTeams.length) {
    const separator = document.createElement('div');
    separator.className = 'planner2-team-separator';
    dropdown.appendChild(separator);
  }
  lpAdminTeams.forEach(appendTeamItem);
  dropdown.style.visibility = 'hidden';
  document.body.appendChild(dropdown);
  const viewportPadding = 8;
  const gap = 4;
  const dropdownRect = dropdown.getBoundingClientRect();
  const dropdownWidth = Math.ceil(dropdownRect.width || 180);
  const dropdownHeight = Math.ceil(dropdownRect.height || 0);
  const viewportWidth = window.innerWidth || document.documentElement.clientWidth || 0;
  const viewportHeight = window.innerHeight || document.documentElement.clientHeight || 0;
  const anchorMidY = rect.top + (rect.height / 2);

  let left = rect.left;
  if (left + dropdownWidth > viewportWidth - viewportPadding) {
    left = Math.max(viewportPadding, viewportWidth - dropdownWidth - viewportPadding);
  }
  if (left < viewportPadding) left = viewportPadding;

  let top = anchorMidY > (viewportHeight / 2)
    ? rect.top - dropdownHeight - gap
    : rect.bottom + gap;
  if (top + dropdownHeight > viewportHeight - viewportPadding) {
    top = Math.max(viewportPadding, viewportHeight - dropdownHeight - viewportPadding);
  }
  if (top < viewportPadding) top = viewportPadding;

  dropdown.style.left = `${Math.round(left)}px`;
  dropdown.style.top = `${Math.round(top)}px`;
  dropdown.style.visibility = '';
  planner2OpenDropdown = dropdown;
};

document.addEventListener('click', () => {
  if (planner2OpenDropdown) {
    planner2OpenDropdown.remove();
    planner2OpenDropdown = null;
  }
  closePlanner2Menu();
});

document.addEventListener('mousemove', (e) => {
  if (!planner2Drag) return;
  const { bar, offsetX } = planner2Drag;
  const rowEl = bar.closest('tr');
  if (!rowEl) return;
  const dragStartX = parseFloat(bar.dataset.dragStartX || '0');
  if (Math.abs(e.clientX - dragStartX) > 3) {
    bar.dataset.dragged = '1';
  }
  const lodgeWidth = PLANNER2.lodgeWidth;
  const rowRect = rowEl.getBoundingClientRect();
  let x = e.clientX - rowRect.left - lodgeWidth - offsetX;
  if (x < 0) x = 0;
  const maxX = (buildSlots().length * PLANNER2.slotWidth) - bar.offsetWidth;
  if (x > maxX) x = maxX;
  const idx = Math.round(x / PLANNER2.slotWidth);
  bar.style.left = `${lodgeWidth + idx * PLANNER2.slotWidth}px`;
  bar.dataset.startIdx = String(idx);

  const bars = Array.from(rowEl.querySelectorAll('.planner2-bar-cleaning'));
  const items = bars.map((b) => {
    const left = parseFloat(b.style.left || '0');
    return {
      bar: b,
      left,
      right: left + b.offsetWidth,
      key: b.dataset.tmpId || ''
    };
  }).sort((a, b) => (a.left - b.left) || String(a.key).localeCompare(String(b.key)));

  const lanes = [];
  items.forEach((it) => {
    let laneIndex = 0;
    while (lanes[laneIndex] && lanes[laneIndex] > it.left) {
      laneIndex += 1;
    }
    lanes[laneIndex] = it.right;
    it.laneIndex = laneIndex;
  });

  const laneCount = Math.max(1, lanes.length);
  const rowHeight = 32 + (laneCount - 1) * 26;
  rowEl.style.height = `${rowHeight}px`;
  rowEl.querySelectorAll('td').forEach(td => { td.style.height = `${rowHeight}px`; });
  items.forEach((it) => {
    it.bar.style.top = `${4 + it.laneIndex * 26}px`;
  });
});

document.addEventListener('mouseup', () => {
  if (!planner2Drag) return;
  const { bar, row, key } = planner2Drag;
  bar.classList.remove('planner2-bar-dragging');
  const wasDragged = String(bar.dataset.dragged || '0') === '1';
  if (!wasDragged) {
    planner2Drag = null;
    return;
  }
  const idx = parseInt(bar.dataset.startIdx || '0', 10);
  bar.dataset.newTime = timeFromIndex(idx);
  if (row && Array.isArray(row.cleanings)) {
    const newTime = bar.dataset.newTime;
    const entry = row.cleanings.find((cl) => {
      const clKey = cl._tmpId || cl.id || '';
      return String(clKey) === String(key);
    });
    if (entry && newTime) {
      entry.time = newTime;
    }
  }
  setPlanner2Dirty(true);
  planner2Drag = null;
  setTimeout(() => {
    if (bar) bar.dataset.dragged = '0';
  }, 30);
  if (planner2SortMode) {
    const slots = buildSlots();
    buildHead(slots);
    renderRows(planner2Data, slots);
    renderPlanner2TeamCards();
    return;
  }
  const rowEl = bar.closest('tr');
  if (rowEl) {
    const bars = Array.from(rowEl.querySelectorAll('.planner2-bar-cleaning'));
    const items = bars.map((b) => {
      const left = parseFloat(b.style.left || '0');
      return {
        bar: b,
        left,
        right: left + b.offsetWidth,
        key: b.dataset.tmpId || ''
      };
    }).sort((a, b) => (a.left - b.left) || String(a.key).localeCompare(String(b.key)));
    const lanes = [];
    items.forEach((it) => {
      let laneIndex = 0;
      while (lanes[laneIndex] && lanes[laneIndex] > it.left) {
        laneIndex += 1;
      }
      lanes[laneIndex] = it.right;
      it.laneIndex = laneIndex;
    });
    const laneCount = Math.max(1, lanes.length);
    const rowHeight = 32 + (laneCount - 1) * 26;
    rowEl.style.height = `${rowHeight}px`;
    rowEl.querySelectorAll('td').forEach(td => { td.style.height = `${rowHeight}px`; });
    items.forEach((it) => {
      it.bar.style.top = `${4 + it.laneIndex * 26}px`;
    });
  }
});

