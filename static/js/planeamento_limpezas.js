const PLANNER2 = {
  startHour: 7,
  endHour: 23,
  slotMinutes: 30,
  lodgeWidth: 240,
  slotWidth: 32
};

let planner2Teams = [];

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

const timeToIndex = (h, m) => {
  const idx = (h - PLANNER2.startHour) * 2 + (m >= 30 ? 1 : 0);
  return Math.max(0, Math.min(idx, (PLANNER2.endHour - PLANNER2.startHour) * 2));
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
let planner2CleaningMenu = null;
const planner2DistanceCache = new Map();
const planner2DistancePending = new Set();

const setPlanner2Dirty = (isDirty) => {
  planner2Dirty = !!isDirty;
  if (planner2SaveBtn) {
    planner2SaveBtn.disabled = !planner2Dirty;
    planner2SaveBtn.classList.toggle('btn-primary', planner2Dirty);
    planner2SaveBtn.classList.toggle('btn-secondary', !planner2Dirty);
  }
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
        typology: row.typology || row.tp
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

const getDistanceKey = (fromAddr, toAddr) => {
  if (!fromAddr || !toAddr) return '';
  return `${fromAddr}|||${toAddr}`.toLowerCase().trim();
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
    Object.entries(data || {}).forEach(([key, km]) => {
      planner2DistanceCache.set(key, km);
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
      const duration = getCleaningDuration(cl.typology || row.typology || row.tp);
      const startMinutes = timeToMinutes(cl.time || '');
      const address = buildAddress(row.al_codpost, row.al_local, row.al_morada);
      if (!teamsMap.has(teamName)) {
        teamsMap.set(teamName, { items: [], totalMinutes: 0 });
      }
      const entry = teamsMap.get(teamName);
      entry.items.push({
        lodging: row.lodging || '',
        typology,
        startMinutes,
        duration,
        address,
        cleaning: cl
      });
      entry.totalMinutes += duration;
    });
  });

  const names = Array.from(teamsMap.keys()).sort((a, b) => a.localeCompare(b));
  container.innerHTML = '';
  const missingPairs = [];
  const addDistancePair = (fromAddr, toAddr) => {
    const key = getDistanceKey(fromAddr, toAddr);
    if (!key) return;
    if (!planner2DistanceCache.has(key) && !planner2DistancePending.has(key)) {
      planner2DistancePending.add(key);
      missingPairs.push({ key, from: fromAddr, to: toAddr });
    }
  };
  names.forEach((name) => {
    const meta = teamsMap.get(name);
    const addresses = Array.from(new Set(meta.items.map(i => i.address).filter(Boolean)));
    addresses.forEach((fromAddr) => {
      addresses.forEach((toAddr) => {
        if (fromAddr !== toAddr) addDistancePair(fromAddr, toAddr);
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

    const buildSequence = (items, times) => {
      const list = document.createElement('div');
      list.className = 'planner2-team-schedule';
      let lastEnd = null;
      const entries = [];
      items.forEach((item, idx) => {
        const startMinutes = times[idx];
        const endMinutes = startMinutes + item.duration;
        if (lastEnd !== null) {
          const prev = entries[entries.length - 1];
          const fromAddr = prev && prev.address ? prev.address : '';
          const toAddr = item.address || '';
          const key = getDistanceKey(fromAddr, toAddr);
          const gapMinutes = Math.max(0, startMinutes - lastEnd);
          const hasGap = gapMinutes > 0;
          if (hasGap || (fromAddr && toAddr && fromAddr !== toAddr)) {
            entries.push({
              type: 'gap',
              duration: gapMinutes,
              distanceKey: key,
              fromAddr,
              toAddr
            });
          }
        }
        entries.push({
          type: 'clean',
          label: `${item.lodging}`,
          meta: `${minutesToTime(startMinutes)} · ${item.typology} · ${formatMinutes(item.duration)}`,
          address: item.address
        });
        lastEnd = endMinutes;
      });
      entries.forEach((entry, idx) => {
        const tag = document.createElement('div');
        if (entry.type === 'gap') {
          tag.className = 'planner2-team-tag planner2-team-gap';
          const distance = entry.distanceKey ? planner2DistanceCache.get(entry.distanceKey) : null;
          const distanceText = typeof distance === 'number' ? `${distance} km` : (entry.distanceKey && planner2DistancePending.has(entry.distanceKey) ? '...' : '—');
          tag.innerHTML = `<span>${formatMinutes(entry.duration)}</span><span class="planner2-team-tag-meta">${distanceText}</span>`;
          const fromText = entry.fromAddr || '-';
          const toText = entry.toAddr || '-';
          tag.title = `De: ${fromText}\nPara: ${toText}\nKey: ${entry.distanceKey || '-'}`;
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
    plannedWrap.appendChild(buildSequence(plannedItems, plannedTimes));

    const buildSuggestionOrder = () => {
      if (plannedItems.length <= 1) return plannedItems.slice();
      const allDistancesReady = plannedItems.every((a) => plannedItems.every((b) => {
        if (a === b) return true;
        const addrA = String(a.address || '').trim().toLowerCase();
        const addrB = String(b.address || '').trim().toLowerCase();
        if (addrA && addrA === addrB) return true;
        const key = getDistanceKey(a.address, b.address);
        return !!key && planner2DistanceCache.has(key);
      }));
      if (!allDistancesReady) return plannedItems.slice();

      const dist = (a, b) => {
        const addrA = String(a.address || '').trim().toLowerCase();
        const addrB = String(b.address || '').trim().toLowerCase();
        if (addrA && addrA === addrB) return 0;
        const key = getDistanceKey(a.address, b.address);
        const v = planner2DistanceCache.get(key);
        return typeof v === 'number' ? v : 9999;
      };

      const routeDistance = (seq) => seq.reduce((sum, item, idx) => {
        if (idx === 0) return 0;
        return sum + dist(seq[idx - 1], item);
      }, 0);

      const start = plannedItems[0];
      const rest = plannedItems.slice(1);
      if (plannedItems.length <= 7) {
        let best = null;
        let bestCost = Infinity;
        const permute = (prefix, remaining) => {
          if (!remaining.length) {
            const seq = [start, ...prefix];
            const cost = routeDistance(seq);
            if (cost < bestCost) {
              bestCost = cost;
              best = seq;
            }
            return;
          }
          for (let i = 0; i < remaining.length; i += 1) {
            const next = remaining[i];
            const newPrefix = prefix.concat(next);
            const newRemaining = remaining.slice(0, i).concat(remaining.slice(i + 1));
            permute(newPrefix, newRemaining);
          }
        };
        permute([], rest);
        return best || plannedItems.slice();
      }

      const order = [start];
      const remaining = rest.slice();
      while (remaining.length) {
        const current = order[order.length - 1];
        let bestIdx = 0;
        let bestDist = dist(current, remaining[0]);
        for (let i = 1; i < remaining.length; i += 1) {
          const d = dist(current, remaining[i]);
          if (d < bestDist) {
            bestDist = d;
            bestIdx = i;
          }
        }
        order.push(remaining.splice(bestIdx, 1)[0]);
      }

      let best = order.slice();
      let bestCost = routeDistance(best);
      let improved = true;
      let loops = 0;
      while (improved && loops < 50) {
        improved = false;
        loops += 1;
        for (let i = 1; i < best.length - 2; i += 1) {
          for (let k = i + 1; k < best.length - 1; k += 1) {
            const newOrder = best.slice(0, i)
              .concat(best.slice(i, k + 1).reverse())
              .concat(best.slice(k + 1));
            const newCost = routeDistance(newOrder);
            if (newCost + 0.001 < bestCost) {
              best = newOrder;
              bestCost = newCost;
              improved = true;
            }
          }
        }
      }
      return best;
    };

    const suggestedItems = buildSuggestionOrder();
    const suggestedWrap = document.createElement('div');
    suggestedWrap.className = 'planner2-team-section planner2-team-section-suggested';
    const suggestedHeader = document.createElement('div');
    suggestedHeader.className = 'planner2-team-section-header';
    const suggestedTitle = document.createElement('div');
    suggestedTitle.className = 'planner2-team-section-title';
    const sameOrder = suggestedItems.length === plannedItems.length
      && suggestedItems.every((item, idx) => item === plannedItems[idx]);
    suggestedTitle.textContent = 'Sugestão';
    if (!sameOrder) {
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
      suggestedWrap.appendChild(buildSequence(suggestedItems, plannedTimes));
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

  const rows = data.slice();
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
      const ka = getCleanKey(a);
      const kb = getCleanKey(b);
      if (ka.has !== kb.has) return ka.has ? -1 : 1;
      if (ka.team !== kb.team) return ka.team.localeCompare(kb.team);
      if (ka.time !== kb.time) return ka.time.localeCompare(kb.time);
      return String(a.lodging || '').localeCompare(String(b.lodging || ''));
    });
  }

  rows.forEach((row) => {
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

    const checkoutHas = !!row.checkout_reservation;
    if (checkoutHas) {
      let { h, m } = parseTime(row.checkout_time, '11:00');
      if (h < 7 || (h === 7 && m <= 0)) {
        h = 7;
        m = 30;
      }
      const endIdx = timeToIndex(h, m);
      const checkoutLabel = `${String(h).padStart(2,'0')}:${String(m).padStart(2,'0')}`;
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
      const originalTime = parseTime(row.checkin_time, '15:00');
      let { h, m } = originalTime;
      let barHour = h;
      let barMin = m;
      if (h > 21 || (h === 21 && m > 0)) {
        barHour = 21;
        barMin = 0;
      }
      const startIdx = timeToIndex(barHour, barMin);
      const totalSlots = slots.length;
      const guests = Number(row.checkin_people || 0);
      const nights = Number(row.checkin_nights || 0);
      const checkinLabel = `${String(h).padStart(2,'0')}:${String(m).padStart(2,'0')} · ${guests}P · ${nights}N`;
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
        `Checkin: ${String(h).padStart(2,'0')}:${String(m).padStart(2,'0')}`,
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
        const duration = getCleaningDuration(cl.typology || row.typology || row.tp);
        const slotsCount = Math.max(1, Math.ceil(duration / 30));
        const totalSlots = slots.length;
        const cappedSlots = Math.min(slotsCount, Math.max(0, totalSlots - startIdx));
        const endIdx = startIdx + cappedSlots;
        const key = cl._tmpId || cl.id || `${idx}`;
        return { cl, startIdx, cappedSlots, endIdx, key };
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

      bars.forEach(({ cl, startIdx, cappedSlots, laneIndex, key }) => {
        const bar = document.createElement('div');
        bar.className = 'planner2-bar planner2-bar-cleaning';
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
};

const loadPlanner2 = async (dateStr) => {
  planner2DistanceCache.clear();
  planner2DistancePending.clear();
  const res = await fetch(`/generic/api/cleaning_plan?date=${encodeURIComponent(dateStr)}`);
  if (!res.ok) throw new Error(res.statusText);
  const data = await res.json();
  planner2Data = buildPlanner2Rows(data);
  const slots = buildSlots();
  buildHead(slots);
  renderRows(planner2Data, slots);
  renderPlanner2TeamCards();
  setPlanner2Dirty(false);
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
  menu.style.left = `${rect.left}px`;
  menu.style.top = `${rect.bottom + 6}px`;
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
          const res = await fetch(`/generic/api/LP/${cl.id}`, { method: 'DELETE' });
          if (!res.ok) throw new Error(res.statusText);
        } catch (err) {
          alert(`Erro ao eliminar: ${err.message || err}`);
          return;
        }
      }
      row.cleanings = (row.cleanings || []).filter((c) => {
        const cKey = c._tmpId || c.id || '';
        const clKey = cl._tmpId || cl.id || '';
        return String(cKey) !== String(clKey);
      });
      setPlanner2Dirty(true);
      const slots = buildSlots();
      buildHead(slots);
      renderRows(planner2Data, slots);
      renderPlanner2TeamCards();
    });
    menu.appendChild(item);
  });
  document.body.appendChild(menu);
  planner2CleaningMenu = menu;
  setTimeout(() => {
    window.addEventListener('click', closePlanner2Menu, { once: true });
  }, 0);
};

const getCleaningDuration = (typology) => {
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
  planner2SaveBtn = document.getElementById('planner2-save');
  if (planner2SaveBtn) {
    planner2SaveBtn.classList.add('btn-secondary');
    planner2SaveBtn.classList.remove('btn-primary');
    planner2SaveBtn.disabled = true;
  }
  const showOcc = document.getElementById('planner2-show-occupied');
  const showEmpty = document.getElementById('planner2-show-empty');
  let currentDate = window.PLANNER2_INITIAL_DATE || new Date().toISOString().slice(0, 10);

  flatpickr(dateInput, {
    defaultDate: currentDate,
    dateFormat: 'Y-m-d',
    onChange: (_, dateStr) => {
      currentDate = dateStr;
      loadPlanner2(currentDate);
    }
  });

  const changeDay = (delta) => {
    const d = new Date(currentDate);
    d.setDate(d.getDate() + delta);
    currentDate = d.toISOString().slice(0, 10);
    dateInput._flatpickr.setDate(currentDate, true);
    loadPlanner2(currentDate);
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
    sortBtn.classList.toggle('btn-outline-secondary', !planner2SortMode);
    sortBtn.classList.toggle('btn-outline-primary', planner2SortMode);
    rerender();
  });

  planner2SaveBtn?.addEventListener('click', async () => {
    if (planner2SaveBtn.disabled) return;
    const payload = collectPlanner2Payload(currentDate);
    if (!payload.length) {
      alert('Nada para gravar.');
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
    } catch (err) {
      alert(`Erro ao gravar: ${err.message || err}`);
      setPlanner2Dirty(true);
    }
  });

  fetch('/generic/api/EQ')
    .then(r => r.json())
    .then(data => { planner2Teams = Array.isArray(data) ? data : []; })
    .catch(() => { planner2Teams = []; })
    .finally(() => loadPlanner2(currentDate));
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
  dropdown.style.left = `${rect.left}px`;
  dropdown.style.top = `${rect.bottom + 4}px`;
  planner2Teams.forEach((team) => {
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
  });
  document.body.appendChild(dropdown);
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
