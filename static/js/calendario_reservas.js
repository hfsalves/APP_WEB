// static/js/calendario_reservas.js

document.addEventListener('DOMContentLoaded', () => {
  const el = document.getElementById('rescalTimeline');
  const loadingEl = document.getElementById('rescalLoading');
  const rangeEl = document.getElementById('rescalRange');
  const filterEl = document.getElementById('rescalFilter');
  const btnReload = document.getElementById('rescalReload');
  const btnToday = document.getElementById('rescalToday');
  const btnPrev30 = document.getElementById('rescalPrev30');
  const btnNext30 = document.getElementById('rescalNext30');
  const hScrollEl = document.getElementById('rescalHScroll');
  const hScrollInnerEl = document.getElementById('rescalHScrollInner');

  const priceModalEl = document.getElementById('rescalPriceModal');
  const selAlojEl = document.getElementById('rescalSelAloj');
  const selPeriodoEl = document.getElementById('rescalSelPeriodo');
  const inpPBase = document.getElementById('rescalPBase');
  const selDesc = document.getElementById('rescalDesc');
  const inpPrecoFinal = document.getElementById('rescalPrecoFinal');
  const hintEl = document.getElementById('rescalPriceHint');
  const btnCancelSel = document.getElementById('rescalCancelSel');
  const btnSavePrices = document.getElementById('rescalSavePrices');

  if (!el || typeof vis === 'undefined') return;

  const fmtDate = new Intl.DateTimeFormat('pt-PT', { year: 'numeric', month: '2-digit', day: '2-digit' });
  const fmtCur = new Intl.NumberFormat('pt-PT', { style: 'currency', currency: 'EUR', minimumFractionDigits: 0, maximumFractionDigits: 0, useGrouping: true });
  const fmtDow = new Intl.DateTimeFormat('pt-PT', { weekday: 'short' });
  const escapeHtml = (str) => String(str == null ? '' : str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');

  const today = () => {
    const d = new Date();
    d.setHours(0, 0, 0, 0);
    return d;
  };

  const addDays = (d, n) => {
    const x = new Date(d.getTime());
    x.setDate(x.getDate() + Number(n || 0));
    return x;
  };

  function eachDay(start, endIncl, cb) {
    const d = new Date(start.getTime());
    d.setHours(0, 0, 0, 0);
    const end = new Date(endIncl.getTime());
    end.setHours(0, 0, 0, 0);
    while (d <= end) {
      cb(new Date(d.getTime()));
      d.setDate(d.getDate() + 1);
    }
  }

  function addWeekendBackgroundItems(startDate, endDate) {
    // 0=Dom, 6=Sáb
    eachDay(startDate, endDate, (d) => {
      const wd = d.getDay();
      if (wd !== 0 && wd !== 6) return;
      const id = `wknd-${toIsoDate(d)}`;
      items.add({
        id,
        type: 'background',
        start: `${toIsoDate(d)} 00:00:00`,
        end: `${toIsoDate(addDays(d, 1))} 00:00:00`,
        className: 'weekend-bg'
      });
    });
  }

  function addBlockedItems(blockedList) {
    const seen = new Set();
    (Array.isArray(blockedList) ? blockedList : []).forEach(b => {
      const groupId = b?.group;
      const dateKey = b?.date;
      if (!groupId || !dateKey) return;
      const seenKey = `${String(groupId)}|${dateKey}`;
      if (seen.has(seenKey)) return;
      seen.add(seenKey);
      const d = new Date(dateKey + 'T00:00:00');
      const title = `${groupId} | ${fmtDate.format(d)}`;
      const id = `bq:${encGroupId(groupId)}|${dateKey}`;
      if (items.get(id)) return;
      items.add({
        id,
        type: 'background',
        group: groupId,
        start: `${dateKey} 00:00:00`,
        end: `${toIsoDate(addDays(new Date(dateKey + 'T00:00:00'), 1))} 00:00:00`,
        className: (Number(b?.tratado || 0) ? 'bq-lock bq-treated' : 'bq-lock bq-pending'),
        title,
      });
    });
  }

  function decorateBlockedDom() {
    const nodes = el.querySelectorAll?.('.vis-item.bq-lock');
    if (!nodes || !nodes.length) return;
    nodes.forEach((node) => {
      try {
        let icon = node.querySelector?.('.bq-lock-icon');
        if (!icon) {
          icon = document.createElement('span');
          icon.className = 'bq-lock-icon';
          icon.innerHTML = '<i class="fa-solid fa-lock"></i>';
          node.appendChild(icon);
        }

        const hasTitle = !!(node.getAttribute && node.getAttribute('title'));
        if (!hasTitle) {
          const id = (node.getAttribute?.('data-id') || node.dataset?.id || '').trim();
          const m = id.match(/^bq:(.+)\|(\d{4}-\d{2}-\d{2})$/);
          if (m) {
            const groupName = decodeURIComponent(m[1]);
            const d = new Date(m[2] + 'T00:00:00');
            node.setAttribute('title', `${groupName} | ${fmtDate.format(d)}`);
          }
        }
      } catch (_) {}
    });
  }

  // preços são renderizados como items normais (type: range) para garantir consistência

  let decoRaf = null;
  function scheduleDecorations() {
    if (decoRaf) return;
    decoRaf = requestAnimationFrame(() => {
      decoRaf = null;
      decorateBlockedDom();
    });
    // fallback: vis por vezes re-renderiza após o RAF
    setTimeout(() => {
      try { decorateBlockedDom(); } catch (_) {}
    }, 50);
  }

  const toIsoDate = (d) => {
    const x = new Date(d.getTime());
    const y = x.getFullYear();
    const m = String(x.getMonth() + 1).padStart(2, '0');
    const day = String(x.getDate()).padStart(2, '0');
    return `${y}-${m}-${day}`;
  };

  let windowStart = addDays(today(), -5);
  let windowEnd = addDays(windowStart, 119); // 120 dias

  let groups = new vis.DataSet([]);
  let items = new vis.DataSet([]);

  // Seleção de células (group + dia)
  const selectedCells = new Set(); // key = `${encGroup}|YYYY-MM-DD`
  let selectionItemIds = [];
  let pbaseItemIds = [];
  let groupOrderIds = [];
  let groupIndexById = new Map();
  let dragState = null; // { anchor:{groupId,dateKey}, base:Set, last:Set, raf:number|null, ignoreClick:boolean }
  const MAX_SELECTED_CELLS = 5000;
  let ignoreNextClick = false;
  let groupFilter = '';
  let lastPriceRecByKey = new Map(); // group|date -> {pbase,desconto,preco,tratado}
  let lastOccupiedByGroup = new Map(); // groupId -> Set(YYYY-MM-DD)
  let lastPriceByKey = new Map(); // group|date -> {preco,desconto}

  const MS_DAY = 24 * 60 * 60 * 1000;
  const DAY_PX = 36; // largura por dia (fixa)
  const GROUP_W_PX = 240;
  const ROW_HEIGHT = 27;
  const MIN_DAYS_VISIBLE = 12; // mínimo de dias visíveis
  let currentVisibleDays = MIN_DAYS_VISIBLE;

  const options = {
    width: '100%',
    height: '100%',
    orientation: { axis: 'top', item: 'top' },
    stack: false,
    groupOrder: 'content',
    horizontalScroll: true,
    verticalScroll: true,
    autoResize: true,
    zoomable: false,
    moveable: false, // drag do rato fica disponível para seleção
    margin: { item: 1, axis: 10 },
    selectable: true,
    multiselect: false,
    start: windowStart,
    end: addDays(windowEnd, 1),
    min: windowStart,
    max: addDays(windowEnd, 1),
    timeAxis: { scale: 'day', step: 1 },
    format: {
      minorLabels: { day: 'D' },
      majorLabels: { day: 'MMM YYYY' }
    }
  };

  const timeline = new vis.Timeline(el, items, groups, options);
  let hScrollBound = false;
  let syncingHScroll = false;
  let syncingWindow = false;
  function totalDaysInRange() {
    return Math.max(1, Math.round((windowEnd.getTime() - windowStart.getTime()) / MS_DAY) + 1);
  }
  function windowStartOffsetDays() {
    const w = timeline.getWindow();
    const s = floorToDay(new Date(w.start));
    return Math.max(0, Math.round((s.getTime() - windowStart.getTime()) / MS_DAY));
  }
  function syncHScrollWidth() {
    if (!hScrollEl || !hScrollInnerEl) return;
    const totalDays = totalDaysInRange();
    const hScrollWidth = totalDays * DAY_PX;
    hScrollInnerEl.style.width = `${hScrollWidth}px`;
    if (!syncingHScroll) {
      syncingHScroll = true;
      const barMax = Math.max(1, hScrollEl.scrollWidth - hScrollEl.clientWidth);
      const maxOffsetDays = Math.max(0, totalDays - currentVisibleDays);
      const offset = Math.min(maxOffsetDays, windowStartOffsetDays());
      hScrollEl.scrollLeft = (maxOffsetDays > 0) ? (offset / maxOffsetDays) * barMax : 0;
      syncingHScroll = false;
    }
  }
  function bindHScroll() {
    if (hScrollBound || !hScrollEl || !hScrollInnerEl) return false;
    hScrollBound = true;
    hScrollEl.addEventListener('scroll', () => {
      if (syncingHScroll || syncingWindow) return;
      syncingWindow = true;
      const totalDays = totalDaysInRange();
      const maxOffsetDays = Math.max(0, totalDays - currentVisibleDays);
      const barMax = Math.max(1, hScrollEl.scrollWidth - hScrollEl.clientWidth);
      const ratio = (barMax > 0) ? (hScrollEl.scrollLeft / barMax) : 0;
      const offsetDays = Math.round(ratio * maxOffsetDays);
      const start = addDays(windowStart, offsetDays);
      const end = addDays(start, currentVisibleDays);
      timeline.setWindow(start, end, { animation: false });
      syncingWindow = false;
    });
    syncHScrollWidth();
    return true;
  }
  function decorateAxisLabels() {
    const nodes = el.querySelectorAll?.('.vis-time-axis .vis-text.vis-minor');
    if (!nodes || !nodes.length) return;
    nodes.forEach((node) => {
      try {
        const raw = node.getAttribute('data-date') || node.getAttribute('data-time') || node.dataset?.date || node.dataset?.time;
        const ms = raw != null ? Number(raw) : NaN;
        if (!isFinite(ms)) return;
        const d = new Date(ms);
        if (!isFinite(d.getTime())) return;
        let dow = fmtDow.format(d);
        dow = dow.replace(/\.$/, '');
        const day = d.getDate();
        node.innerHTML = `<div class="rescal-dow">${dow}</div><div class="rescal-dom">${day}</div>`;
      } catch (_) {}
    });
  }
  timeline.on('changed', () => {
    // manter cadeados visíveis após scroll/redraw
    scheduleDecorations();
    decorateAxisLabels();
    syncHScrollWidth();
  });
  timeline.on('rangechanged', () => {
    syncHScrollWidth();
  });
  requestAnimationFrame(() => {
    try { timeline.redraw(); } catch (_) {}
    applyFixedDayWidth();
    bindHScroll();
    syncHScrollWidth();
  });

  function encGroupId(groupId) {
    return encodeURIComponent(String(groupId == null ? '' : groupId));
  }

  function keyToParts(key) {
    const i = key.indexOf('|');
    if (i < 0) return { groupId: '', dateKey: '' };
    const enc = key.slice(0, i);
    const dateKey = key.slice(i + 1);
    return { groupId: decodeURIComponent(enc), dateKey };
  }

  function dateKeyFromTime(time) {
    if (!time) return null;
    const d = new Date(time);
    d.setHours(0, 0, 0, 0);
    const min = new Date(windowStart.getTime());
    min.setHours(0, 0, 0, 0);
    const max = new Date(windowEnd.getTime());
    max.setHours(0, 0, 0, 0);
    if (d < min || d > max) return null;
    return toIsoDate(d);
  }

  function rebuildGroupOrderCache() {
    const ordered = groups.get({ order: 'content' }).filter(g => g && g.visible !== false);
    groupOrderIds = ordered.map(g => g.id);
    groupIndexById = new Map();
    groupOrderIds.forEach((id, idx) => groupIndexById.set(String(id), idx));
  }

  function normText(s) {
    return String(s == null ? '' : s)
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '')
      .toLowerCase()
      .trim();
  }

  function applyGroupFilter() {
    const q = normText(groupFilter);
    const all = groups.get();
    if (!q) {
      groups.update(all.map(g => ({ id: g.id, visible: true })));
      rebuildGroupOrderCache();
      return;
    }

    const upd = [];
    for (const g of all) {
      const label = normText(g.content || g.id);
      upd.push({ id: g.id, visible: label.includes(q) });
    }
    groups.update(upd);
    rebuildGroupOrderCache();
    renderPricesForVisibleRange(0);
    syncRowHeights();
  }

  function clearSelectionItems() {
    if (selectionItemIds.length) {
      try { items.remove(selectionItemIds); } catch (_) {}
    }
    selectionItemIds = [];
  }

  function clearPbaseItems() {
    if (pbaseItemIds.length) {
      try { items.remove(pbaseItemIds); } catch (_) {}
    }
    pbaseItemIds = [];
  }

  function floorToDay(d) {
    const x = new Date(d.getTime());
    x.setHours(0, 0, 0, 0);
    return x;
  }

  function buildPbaseContent(priceVal, descVal) {
      const wrap = document.createElement('div');
      wrap.className = 'pbase-wrap';
      wrap.style.position = 'relative';
      wrap.style.width = '100%';
      wrap.style.height = '100%';
      wrap.style.minHeight = '26px';
      wrap.style.padding = '2px 4px';
      wrap.style.boxSizing = 'border-box';

      const price = document.createElement('span');
      price.className = 'pbase-price';
      price.textContent = String(priceVal);
      price.style.position = 'absolute';
      price.style.top = '2px';
      price.style.right = '4px';
      price.style.fontSize = '9px';
      price.style.fontWeight = '400';
      price.style.lineHeight = '1';
      price.style.setProperty('color', '#334155', 'important');
      wrap.appendChild(price);

      if (descVal > 0) {
        const disc = document.createElement('span');
        disc.className = 'pbase-discount';
        disc.textContent = String(descVal);
        disc.style.position = 'absolute';
        disc.style.left = '9px';
        disc.style.bottom = '2px';
        disc.style.fontSize = '9px';
        disc.style.fontWeight = '800';
        disc.style.lineHeight = '1';
        disc.style.setProperty('color', '#b91c1c', 'important');
        wrap.appendChild(disc);
      }

      return wrap;
    }

  function addPbaseItems(occupiedByGroup, priceByKey, rangeStart, rangeEnd) {
    clearPbaseItems();

    const allGroups = groups.get();
    const start = floorToDay(rangeStart ? new Date(rangeStart) : windowStart);
    const end = floorToDay(rangeEnd ? new Date(rangeEnd) : windowEnd);

    const batch = [];
    const ids = [];

    for (const g of allGroups) {
      if (!g) continue;
      if (g.visible === false) continue;
      const groupId = g.id;
      const baseP = Math.round(Number(g.pbase || 0));
      if (!groupId) continue;

      const occ = occupiedByGroup?.get?.(String(groupId)) || new Set();
      eachDay(start, end, (d) => {
        const dateKey = toIsoDate(d);
        if (occ.has(dateKey)) return;

        const mapKey = `${String(groupId)}|${dateKey}`;
        const override = priceByKey?.get?.(mapKey); // {preco,desconto} | number | undefined
        const overridePreco = (override && typeof override === 'object') ? override.preco : override;
        const overrideDesc = (override && typeof override === 'object') ? override.desconto : 0;
        const val = Math.round(Number((overridePreco != null ? overridePreco : baseP) || 0));
        const desc = Math.round(Number(overrideDesc || 0));
        if (!isFinite(val) || val <= 0) return;

        const id = `pb:${encGroupId(groupId)}|${dateKey}`;
        ids.push(id);
        batch.push({
          id,
          type: 'range',
          group: groupId,
          start: `${dateKey} 00:00:00`,
          end: `${toIsoDate(addDays(d, 1))} 00:00:00`,
          content: buildPbaseContent(val, desc),
          title: String(val),
          className: 'pbase-item',
          selectable: false,
          preco: val,
          desconto: (isFinite(desc) && desc > 0) ? desc : 0,
        });
      });
    }

    if (batch.length) items.add(batch);
    pbaseItemIds = ids;
  }

  let priceRenderTimer = null;
  function renderPricesForVisibleRange(delayMs = 0) {
    if (priceRenderTimer) clearTimeout(priceRenderTimer);
    const ms = Number(delayMs || 0);
    priceRenderTimer = setTimeout(() => {
      priceRenderTimer = null;
      addPbaseItems(lastOccupiedByGroup, lastPriceByKey, windowStart, windowEnd);
    }, ms);
  }

  function syncRowHeights() {
    const visibleCount = groups.get().filter(g => g && g.visible !== false).length;
    const totalH = visibleCount * ROW_HEIGHT;
    if (!isFinite(totalH) || totalH <= 0) return;
    const centerContent = el.querySelector('.vis-panel.vis-center .vis-content');
    const leftContent = el.querySelector('.vis-panel.vis-left .vis-content');
    const labelset = el.querySelector('.vis-labelset');
    const itemset = el.querySelector('.vis-itemset');
    [centerContent, leftContent, labelset, itemset].forEach((node) => {
      if (!node) return;
      node.style.height = `${totalH}px`;
      node.style.minHeight = `${totalH}px`;
    });
  }

  function renderSelection() {
    clearSelectionItems();
    if (!selectedCells.size) return;

    const ids = [];
    for (const key of selectedCells) {
      const { groupId, dateKey } = keyToParts(key);
      if (!groupId || !dateKey) continue;
      const id = `sel:${encGroupId(groupId)}|${dateKey}`;
      ids.push(id);
      items.add({
        id,
        type: 'background',
        group: groupId,
        start: `${dateKey} 00:00:00`,
        end: `${toIsoDate(addDays(new Date(dateKey + 'T00:00:00'), 1))} 00:00:00`,
        className: 'cell-sel'
      });
    }
    selectionItemIds = ids;
    scheduleDecorations();
  }

  function computeSelectionSummary() {
    const alojSet = new Set();
    let minD = null;
    let maxD = null;
    let count = 0;

    for (const key of selectedCells) {
      const { groupId, dateKey } = keyToParts(key);
      if (!groupId || !dateKey) continue;
      alojSet.add(groupId);
      const d = new Date(dateKey + 'T00:00:00');
      if (!minD || d < minD) minD = d;
      if (!maxD || d > maxD) maxD = d;
      count += 1;
    }

    const aloj = Array.from(alojSet).sort((a, b) => String(a).localeCompare(String(b)));
    let periodo = '--';
    if (minD && maxD) {
      if (toIsoDate(minD) === toIsoDate(maxD)) periodo = fmtDate.format(minD);
      else periodo = `${fmtDate.format(minD)} -> ${fmtDate.format(maxD)}`;
      periodo += ` (${count} célula(s))`;
    }
    return { aloj, minD, maxD, count, periodo };
  }

  function getGroupPbase(groupId) {
    try {
      const g = groups.get(groupId);
      return Math.round(Number(g?.pbase || 0));
    } catch (_) {
      return 0;
    }
  }

  function computeCommonValues() {
    let commonBase = null;
    let commonDesc = null;
    let commonPreco = null;

    for (const key of selectedCells) {
      const { groupId, dateKey } = keyToParts(key);
      const mapKey = `${String(groupId)}|${dateKey}`;
      const rec = lastPriceRecByKey.get(mapKey);

      const base = Math.round(Number(rec?.pbase ?? getGroupPbase(groupId) ?? 0));
      const desc = Number(rec?.desconto ?? 0);
      const preco = Math.round(Number(rec?.preco ?? (base * (1 - (desc / 100))) ?? 0));

      if (commonBase === null) commonBase = base; else if (commonBase !== base) commonBase = undefined;
      if (commonDesc === null) commonDesc = desc; else if (commonDesc !== desc) commonDesc = undefined;
      if (commonPreco === null) commonPreco = preco; else if (commonPreco !== preco) commonPreco = undefined;
    }

    return { commonBase, commonDesc, commonPreco };
  }

  function calcFinal(pbase, desconto) {
    const b = Number(pbase || 0);
    const d = Number(desconto || 0);
    if (!isFinite(b) || !isFinite(d)) return 0;
    return Math.round(b * (1 - (d / 100)));
  }

  function setFinalFromInputs() {
    if (!inpPrecoFinal) return;
    const p = Number(inpPBase?.value || 0);
    const d = Number(selDesc?.value || 0);
    inpPrecoFinal.value = String(calcFinal(p, d));
  }

  function clearSelectionAndClose(modal) {
    selectedCells.clear();
    renderSelection();
    try { modal?.hide?.(); } catch (_) {}
  }

  function openPriceModal() {
    if (!priceModalEl || typeof bootstrap === 'undefined') return;
    if (!selectedCells.size) return;

    const summary = computeSelectionSummary();
    if (selAlojEl) {
      selAlojEl.textContent = summary.aloj.length > 6
        ? `${summary.aloj.slice(0, 6).join(', ')} (+${summary.aloj.length - 6})`
        : summary.aloj.join(', ');
    }
    if (selPeriodoEl) selPeriodoEl.textContent = summary.periodo;

    const common = computeCommonValues();
    const hasCommon = (common.commonBase !== undefined && common.commonDesc !== undefined && common.commonPreco !== undefined);

    if (inpPBase) inpPBase.value = (common.commonBase == null || common.commonBase === undefined) ? '' : String(common.commonBase);
    if (selDesc) selDesc.value = (common.commonDesc == null || common.commonDesc === undefined) ? '' : String(common.commonDesc);
    setFinalFromInputs();

    if (hintEl) {
      hintEl.textContent = hasCommon ? '' : 'Valores diferentes na seleção; ao gravar aplica-se a todas as células.';
    }

    const modal = bootstrap.Modal.getOrCreateInstance(priceModalEl);
    modal.show();

    const onHidden = () => {
      // se fechar pelo X/fora, não mexe na seleção
      priceModalEl.removeEventListener('hidden.bs.modal', onHidden);
    };
    priceModalEl.addEventListener('hidden.bs.modal', onHidden);

    btnCancelSel?.addEventListener('click', () => clearSelectionAndClose(modal), { once: true });

    const onChange = () => setFinalFromInputs();
    inpPBase?.addEventListener('input', onChange, { once: false });
    selDesc?.addEventListener('change', onChange, { once: false });

    btnSavePrices?.addEventListener('click', async () => {
      const pbase = Number(inpPBase?.value || 0);
      const desc = Number(selDesc?.value || 0);
      if (!isFinite(pbase) || pbase <= 0) {
        if (hintEl) hintEl.textContent = 'Preço base inválido.';
        return;
      }
      if (![0, 10, 20, 30, 40, 50, 60].includes(desc)) {
        if (hintEl) hintEl.textContent = 'Desconto inválido.';
        return;
      }
      const preco = calcFinal(pbase, desc);

      const cells = [];
      for (const key of selectedCells) {
        const { groupId, dateKey } = keyToParts(key);
        if (!groupId || !dateKey) continue;
        cells.push({ group: groupId, date: dateKey });
      }

      try {
        btnSavePrices.disabled = true;
        const res = await fetch('/api/precos_bulk', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ cells, pbase, desconto: desc, preco }),
        });
        const out = await res.json();
        if (!res.ok || out.error) throw new Error(out.error || 'Erro ao gravar');

        // Atualizar apenas as células selecionadas (sem recarregar o ecrã/posição)
        for (const c of cells) {
          const groupId = String(c.group || '').trim();
          const dateKey = String(c.date || '').trim();
          if (!groupId || !dateKey) continue;

          const mapKey = `${groupId}|${dateKey}`;
          lastPriceRecByKey.set(mapKey, { pbase, desconto: desc, preco, tratado: 0 });

          const occ = lastOccupiedByGroup?.get?.(groupId);
          const isOcc = !!(occ && occ.has(dateKey));
          const id = `pb:${encGroupId(groupId)}|${dateKey}`;

          if (isOcc || preco <= 0) {
            if (items.get(id)) {
              try { items.remove(id); } catch (_) {}
            }
            continue;
          }

          const patch = {
            id,
            type: 'range',
            group: groupId,
            start: `${dateKey} 00:00:00`,
            end: `${toIsoDate(addDays(new Date(dateKey + 'T00:00:00'), 1))} 00:00:00`,
            content: buildPbaseContent(Math.round(preco), Math.round(desc)),
            title: String(Math.round(preco)),
            className: 'pbase-item',
            selectable: false,
            preco: Math.round(preco),
            desconto: (isFinite(desc) && desc > 0) ? Math.round(desc) : 0,
          };

          if (items.get(id)) items.update(patch);
          else {
            items.add(patch);
            pbaseItemIds.push(id);
          }
        }

        scheduleDecorations();
        clearSelectionAndClose(modal);
      } catch (e) {
        if (hintEl) hintEl.textContent = `Erro: ${e.message || e}`;
      } finally {
        btnSavePrices.disabled = false;
      }
    }, { once: true });
  }

  function pruneSelectionToRange() {
    if (!selectedCells.size) return;
    const validGroupIds = new Set(groups.getIds().map(String));
    const keep = new Set();
    for (const key of selectedCells) {
      const { groupId, dateKey } = keyToParts(key);
      if (!validGroupIds.has(String(groupId))) continue;
      const d = new Date(dateKey + 'T00:00:00');
      d.setHours(0, 0, 0, 0);
      if (d < windowStart || d > windowEnd) continue;
      keep.add(`${encGroupId(groupId)}|${dateKey}`);
    }
    selectedCells.clear();
    for (const k of keep) selectedCells.add(k);
  }

  function computeRectSelection(anchor, current) {
    if (!anchor || !current) return new Set();
    const aIdx = groupIndexById.get(String(anchor.groupId));
    const bIdx = groupIndexById.get(String(current.groupId));
    if (aIdx == null || bIdx == null) return new Set();

    const aDate = new Date(anchor.dateKey + 'T00:00:00');
    const bDate = new Date(current.dateKey + 'T00:00:00');
    aDate.setHours(0, 0, 0, 0);
    bDate.setHours(0, 0, 0, 0);

    const g0 = Math.min(aIdx, bIdx);
    const g1 = Math.max(aIdx, bIdx);
    const d0 = aDate <= bDate ? aDate : bDate;
    const d1 = aDate <= bDate ? bDate : aDate;

    const rect = new Set();
    for (let gi = g0; gi <= g1; gi++) {
      const groupId = groupOrderIds[gi];
      if (groupId == null) continue;
      const enc = encGroupId(groupId);

      const d = new Date(d0.getTime());
      while (d <= d1) {
        rect.add(`${enc}|${toIsoDate(d)}`);
        if (rect.size >= MAX_SELECTED_CELLS) return rect;
        d.setDate(d.getDate() + 1);
      }
    }
    return rect;
  }

  function clampDate(d, minD, maxD) {
    const t = d.getTime();
    const mn = minD.getTime();
    const mx = maxD.getTime();
    return new Date(Math.min(Math.max(t, mn), mx));
  }

  function applyFixedDayWidth() {
    const totalW = el.getBoundingClientRect?.().width || el.clientWidth || window.innerWidth || 1200;
    const centerW = Math.max(320, totalW - GROUP_W_PX - 24);
    const totalDays = Math.max(1, Math.round((windowEnd.getTime() - windowStart.getTime()) / MS_DAY) + 1);
    const visibleDays = Math.max(MIN_DAYS_VISIBLE, Math.min(totalDays, Math.floor(centerW / DAY_PX)));
    currentVisibleDays = visibleDays;
    const interval = visibleDays * MS_DAY;

    const min = windowStart;
    const max = addDays(windowEnd, 1); // exclusivo
    // zoom fixo: intervalo constante
    timeline.setOptions({ zoomMin: interval, zoomMax: interval, min, max });

    const start = clampDate(windowStart, min, new Date(max.getTime() - interval));
    const end = new Date(start.getTime() + interval);
    timeline.setWindow(start, end, { animation: false });
  }

  function setLoading(on) {
    if (!loadingEl) return;
    loadingEl.classList.toggle('d-none', !on);
  }

  function setRangeLabel() {
    if (!rangeEl) return;
    rangeEl.textContent = `${fmtDate.format(windowStart)} → ${fmtDate.format(windowEnd)} (120 dias)`;
  }

  async function loadData() {
    setLoading(true);
    setRangeLabel();
    const qs = new URLSearchParams({ start: toIsoDate(windowStart), end: toIsoDate(windowEnd) });
    try {
      const res = await fetch(`/api/calendario_reservas?${qs.toString()}`);
      const data = await res.json();
      if (!res.ok || data.error) throw new Error(data.error || 'Erro ao carregar reservas');

      groups.clear();
      items.clear();
      (Array.isArray(data.groups) ? data.groups : []).forEach(g => {
        if (!g || !g.id) return;
        groups.add({ id: g.id, content: g.content || g.id, visible: true, pbase: Number(g.pbase || 0) });
      });
      rebuildGroupOrderCache();
      applyGroupFilter();

      const occupiedByGroup = new Map(); // groupId -> Set(YYYY-MM-DD)
      (Array.isArray(data.items) ? data.items : []).forEach(it => {
        if (!it || !it.id || !it.group || !it.start || !it.end) return;
        const hosp = String(it.hospede || '').trim();
        const valor = Number(it.valor || 0);

        // marcar dias ocupados (checkout exclusivo)
        try {
          const s = floorToDay(new Date(it.start));
          const e = floorToDay(new Date(it.end));
          e.setDate(e.getDate() - 1);
          if (isFinite(s.getTime()) && isFinite(e.getTime()) && s <= e) {
            const set = occupiedByGroup.get(String(it.group)) || new Set();
            const d = new Date(s.getTime());
            while (d <= e) {
              set.add(toIsoDate(d));
              d.setDate(d.getDate() + 1);
            }
            occupiedByGroup.set(String(it.group), set);
          }
        } catch (_) {}
        const label = [hosp || 'Reserva', isFinite(valor) ? fmtCur.format(valor) : ''].filter(Boolean).join(' • ');
        items.add({
          id: it.id,
          group: it.group,
          start: it.start,
          end: it.end,
          content: `<span class="rs-label">${escapeHtml(label)}</span>`,
          title: it.title || '',
          className: it.className || 'rs-item'
        });
      });

      // fixar janela
      windowStart = new Date(data.start + 'T00:00:00');
      windowEnd = new Date(data.end + 'T00:00:00');

      // evidenciar fins de semana (Sáb/Dom) no background
      addWeekendBackgroundItems(windowStart, windowEnd);

      // noites bloqueadas (cadeados)
      addBlockedItems(data.blocked);

      const priceByKey = new Map();
      lastPriceRecByKey = new Map();
      (Array.isArray(data.prices) ? data.prices : []).forEach(p => {
        const groupId = p?.group;
        const dateKey = p?.date;
        if (!groupId || !dateKey) return;
        const key = `${String(groupId)}|${dateKey}`;
        priceByKey.set(key, { preco: Number(p?.preco || 0), desconto: Number(p?.desconto || 0) });
        lastPriceRecByKey.set(key, {
          pbase: Number(p?.pbase || 0),
          desconto: Number(p?.desconto || 0),
          preco: Number(p?.preco || 0),
          tratado: Number(p?.tratado || 0),
        });
      });
      lastPriceByKey = priceByKey;

      // preço por data (PRECOS.PRECO) com fallback para AL.PBASE
      lastOccupiedByGroup = occupiedByGroup;

      pruneSelectionToRange();
      renderSelection();

      timeline.setOptions({
        min: windowStart,
        max: addDays(windowEnd, 1)
      });
      // garantir que o layout do timeline já foi calculado antes de medir larguras
      try { timeline.redraw(); } catch (_) {}
      scheduleDecorations();
      syncRowHeights();
      requestAnimationFrame(() => applyFixedDayWidth());
      renderPricesForVisibleRange(0);
      setTimeout(applyFixedDayWidth, 80);
      setTimeout(applyFixedDayWidth, 220);
      setRangeLabel();
    } catch (err) {
      console.error(err);
      if (rangeEl) rangeEl.textContent = `Erro: ${err.message || err}`;
    } finally {
      setLoading(false);
    }
  }

  btnReload?.addEventListener('click', loadData);
  btnToday?.addEventListener('click', () => {
    windowStart = addDays(today(), -5);
    windowEnd = addDays(windowStart, 119);
    loadData();
  });
  btnPrev30?.addEventListener('click', () => {
    windowStart = addDays(windowStart, -30);
    windowEnd = addDays(windowStart, 119);
    loadData();
  });
  btnNext30?.addEventListener('click', () => {
    windowStart = addDays(windowStart, 30);
    windowEnd = addDays(windowStart, 119);
    loadData();
  });

  window.addEventListener('resize', () => {
    // recalcula número de dias visíveis consoante a largura
    applyFixedDayWidth();
  });

  let filterRaf = null;
  filterEl?.addEventListener('input', () => {
    groupFilter = filterEl.value || '';
    if (filterRaf) cancelAnimationFrame(filterRaf);
    filterRaf = requestAnimationFrame(() => {
      filterRaf = null;
      applyGroupFilter();
    });
  });

  // Click numa célula: seleciona dia+alojamento (Ctrl para alternar)
  timeline.on('click', (props) => {
    if (ignoreNextClick) {
      ignoreNextClick = false;
      return;
    }
    if (!props) return;
    if (props.item) {
      const it = items.get(props.item);
      const cls = String(it?.className || '');
      const isCellOverlay = (it && it.type === 'background') || cls.includes('pbase-item');
      if (!isCellOverlay) return;
    }
    const groupId = props.group;
    const dateKey = dateKeyFromTime(props.time);
    if (!groupId || !dateKey) return;

    const ev = props.event || {};
    const toggle = !!(ev.ctrlKey || ev.metaKey);
    const key = `${encGroupId(groupId)}|${dateKey}`;

    if (toggle) {
      if (selectedCells.has(key)) selectedCells.delete(key);
      else selectedCells.add(key);
    } else {
      selectedCells.clear();
      selectedCells.add(key);
    }
    renderSelection();
    openPriceModal();
  });

  function startDragSelection(ev) {
    if (ev.button !== 0) return;
    const props = timeline.getEventProperties(ev);
    if (!props) return;
    if (props.item) {
      const it = items.get(props.item);
      const cls = String(it?.className || '');
      const isCellOverlay = (it && it.type === 'background') || cls.includes('pbase-item');
      if (!isCellOverlay) return; // não iniciar no topo de uma reserva
    }
    const groupId = props.group;
    const dateKey = dateKeyFromTime(props.time);
    if (!groupId || !dateKey) return;

    // Impede o vis-timeline de interpretar o drag como scroll/pan
    try { ev.preventDefault(); } catch (_) {}
    try { ev.stopPropagation(); } catch (_) {}
    try { ev.stopImmediatePropagation?.(); } catch (_) {}

    const additive = !!(ev.ctrlKey || ev.metaKey);
    dragState = {
      anchor: { groupId, dateKey },
      base: additive ? new Set(selectedCells) : new Set(),
      last: null,
      raf: null,
      ignoreClick: false,
    };

    // Seleciona logo a célula inicial (para o user ver imediatamente)
    const first = new Set(dragState.base);
    first.add(`${encGroupId(groupId)}|${dateKey}`);
    dragState.last = first;
    selectedCells.clear();
    for (const k of first) selectedCells.add(k);
    renderSelection();

    // Pointer capture para receber movimentos mesmo que o cursor saia da grelha
    const center = ev.currentTarget;
    const prevOverflow = center?.style?.overflow;
    const prevTouchAction = center?.style?.touchAction;
    const prevUserSelect = document.body.style.userSelect;
    if (center?.style) {
      // enquanto está a selecionar, não deixar o drag "puxar" o scroll vertical do container
      center.style.overflow = 'hidden';
      center.style.touchAction = 'none';
    }
    document.body.style.userSelect = 'none';

    if (center?.setPointerCapture && ev.pointerId != null) {
      try { center.setPointerCapture(ev.pointerId); } catch (_) {}
    }

    const onMove = (e) => {
      if (!dragState) return;
      try { e.preventDefault(); } catch (_) {}
      try { e.stopPropagation(); } catch (_) {}
      try { e.stopImmediatePropagation?.(); } catch (_) {}
      const p = timeline.getEventProperties(e);
      const gid = p?.group;
      const dk = dateKeyFromTime(p?.time);
      if (!gid || !dk) return;

      const rect = computeRectSelection(dragState.anchor, { groupId: gid, dateKey: dk });
      const merged = new Set(dragState.base);
      for (const k of rect) {
        merged.add(k);
        if (merged.size >= MAX_SELECTED_CELLS) break;
      }
      dragState.last = merged;

      if (dragState.raf) return;
      dragState.raf = requestAnimationFrame(() => {
        if (!dragState) return;
        dragState.raf = null;
        selectedCells.clear();
        for (const k of dragState.last || []) selectedCells.add(k);
        renderSelection();
      });
    };

    const endDrag = (e) => {
      if (!dragState) return;
      ignoreNextClick = true;
      if (dragState.raf) cancelAnimationFrame(dragState.raf);
      dragState = null;

      if (center?.style) {
        center.style.overflow = prevOverflow ?? '';
        center.style.touchAction = prevTouchAction ?? '';
      }
      document.body.style.userSelect = prevUserSelect ?? '';
      try { e?.preventDefault?.(); } catch (_) {}
      try { e?.stopPropagation?.(); } catch (_) {}
      try { e?.stopImmediatePropagation?.(); } catch (_) {}

      ev.currentTarget?.removeEventListener?.('pointermove', onMove, true);
      ev.currentTarget?.removeEventListener?.('pointerup', endDrag, true);
      ev.currentTarget?.removeEventListener?.('pointercancel', endDrag, true);
      openPriceModal();
    };

    ev.currentTarget?.addEventListener?.('pointermove', onMove, true);
    ev.currentTarget?.addEventListener?.('pointerup', endDrag, true);
    ev.currentTarget?.addEventListener?.('pointercancel', endDrag, true);
  }

  function bindDragSelection() {
    const center = el.querySelector('.vis-panel.vis-center');
    if (!center) return false;
    // Pointer events funcionam melhor com drag + pointer capture
    center.addEventListener('pointerdown', startDragSelection, true);
    return true;
  }

  // O DOM do timeline pode ainda não existir neste momento, por isso tentamos algumas vezes.
  let bindTries = 0;
  const bindTimer = setInterval(() => {
    if (bindDragSelection() || bindTries++ > 20) clearInterval(bindTimer);
  }, 100);

  loadData();
});
