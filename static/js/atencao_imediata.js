(function () {
  'use strict';

  const els = {
    grid: document.getElementById('attentionGrid'),
    empty: document.getElementById('attentionEmpty'),
    regime: document.getElementById('attentionRegime'),
    refresh: document.getElementById('attentionRefresh'),
    kpiAloj: document.getElementById('attentionKpiAloj'),
    kpiNights: document.getElementById('attentionKpiNights'),
    kpiPotential: document.getElementById('attentionKpiPotential'),
    kpiUnsynced: document.getElementById('attentionKpiUnsynced'),
    modal: document.getElementById('attentionPriceModal'),
    form: document.getElementById('attentionPriceForm'),
    title: document.getElementById('attentionPriceTitle'),
    summary: document.getElementById('attentionPriceSummary'),
    value: document.getElementById('attentionPriceValue'),
    dateIni: document.getElementById('attentionPriceDateIni'),
    dateFim: document.getElementById('attentionPriceDateFim'),
    motivo: document.getElementById('attentionPriceMotivo'),
    belowMin: document.getElementById('attentionPriceBelowMin'),
    status: document.getElementById('attentionPriceStatus')
  };

  const state = {
    payload: null,
    selected: null,
    modal: null,
    loading: false,
    syncLoading: false,
    syncTimer: null
  };

  const fmtMoney = new Intl.NumberFormat('pt-PT', {
    minimumFractionDigits: 0,
    maximumFractionDigits: 0
  });

  function parseMoneyValue(value) {
    if (typeof value === 'number') return Number.isFinite(value) ? value : 0;
    let text = String(value ?? '').trim().replace(/\s+/g, '');
    if (!text) return 0;
    if (text.includes(',') && text.includes('.')) {
      text = text.lastIndexOf(',') > text.lastIndexOf('.')
        ? text.replace(/\./g, '').replace(',', '.')
        : text.replace(/,/g, '');
    } else if (text.includes(',')) {
      text = text.replace(',', '.');
    }
    const number = Number(text);
    return Number.isFinite(number) ? number : 0;
  }

  function money(value) {
    const number = parseMoneyValue(value);
    return fmtMoney.format(number);
  }

  function escapeHtml(value) {
    return String(value ?? '').replace(/[&<>"']/g, (char) => ({
      '&': '&amp;',
      '<': '&lt;',
      '>': '&gt;',
      '"': '&quot;',
      "'": '&#039;'
    }[char]));
  }

  function setStatus(message, isError) {
    if (!els.status) return;
    els.status.textContent = message || '';
    els.status.classList.toggle('is-error', Boolean(isError));
  }

  async function readJson(response) {
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(payload.error || `Erro HTTP ${response.status}`);
    return payload;
  }

  function updateKpis(payload) {
    const totals = payload?.totals || {};
    if (els.kpiAloj) els.kpiAloj.textContent = String(totals.alojamentos || 0);
    if (els.kpiNights) els.kpiNights.textContent = String(totals.noites_vazias || 0);
    if (els.kpiPotential) els.kpiPotential.textContent = money(totals.potencial || 0);
    if (els.kpiUnsynced) els.kpiUnsynced.textContent = String(totals.por_sincronizar || 0);
  }

  function recalculateRowTotals(row) {
    let vacantCount = 0;
    let vacantTotal = 0;
    (row.days || []).forEach((day) => {
      if (day.state !== 'vacant') return;
      vacantCount += 1;
      const price = parseMoneyValue(day.price);
      if (Number.isFinite(price)) vacantTotal += price;
    });
    row.vacant_count = vacantCount;
    row.vacant_total = vacantTotal;
  }

  function recalculatePayloadTotals(payload) {
    const rows = payload?.rows || [];
    payload.totals = {
      alojamentos: rows.length,
      noites_vazias: rows.reduce((total, row) => total + parseMoneyValue(row.vacant_count), 0),
      potencial: rows.reduce((total, row) => total + parseMoneyValue(row.vacant_total), 0),
      por_sincronizar: rows.reduce((total, row) => total + (row.days || []).filter((day) => (
        day.state === 'vacant' && day.synced === false
      )).length, 0)
    };
  }

  function rerenderCurrentPayload() {
    const scroll = els.grid?.closest('.attention-scroll');
    const left = scroll?.scrollLeft || 0;
    const top = scroll?.scrollTop || 0;
    render(state.payload);
    if (scroll) {
      scroll.scrollLeft = left;
      scroll.scrollTop = top;
    }
  }

  function applyLocalPriceOverride(payload) {
    if (!state.payload || !state.selected?.row) return;
    const row = (state.payload.rows || []).find((item) => item.alojamento === state.selected.row.alojamento);
    if (!row) return;

    const start = String(payload.data_ini || '');
    const end = String(payload.data_fim || start);
    const value = parseMoneyValue(payload.valor);
    (row.days || []).forEach((day) => {
      if (day.state !== 'vacant') return;
      if (String(day.date || '') < start || String(day.date || '') > end) return;
      day.price = value;
      day.synced = false;
    });
    recalculateRowTotals(row);
    recalculatePayloadTotals(state.payload);
    rerenderCurrentPayload();
  }

  function priceCellKey(alojamento, date) {
    return `${String(alojamento || '')}|||${String(date || '')}`;
  }

  function updatePriceButton(button, row, day) {
    button.textContent = money(day.price);
    button.classList.toggle('is-unsynced', day.synced === false);
    button.title = `${row.alojamento} · ${day.date}${day.synced === false ? ' · por sincronizar' : ''}`;
  }

  function applySyncPayload(syncPayload) {
    if (!state.payload) return;
    const syncMap = new Map();
    (syncPayload.items || []).forEach((item) => {
      const displayName = item.alojamento || item.price_alojamento;
      if (!displayName || !item.date) return;
      syncMap.set(priceCellKey(displayName, item.date), item);
    });
    const buttonMap = new Map();
    els.grid?.querySelectorAll('.attention-price').forEach((button) => {
      buttonMap.set(priceCellKey(button.dataset.alojamento, button.dataset.date), button);
    });

    (state.payload.rows || []).forEach((row) => {
      (row.days || []).forEach((day) => {
        if (day.state !== 'vacant') return;
        const item = syncMap.get(priceCellKey(row.alojamento, day.date));
        if (!item) return;
        day.synced = Boolean(item.synced);
        if (item.price !== undefined && item.price !== null) {
          day.price = item.price;
        }
        const button = buttonMap.get(priceCellKey(row.alojamento, day.date));
        if (button) updatePriceButton(button, row, day);
      });
      recalculateRowTotals(row);
    });
    recalculatePayloadTotals(state.payload);
    updateKpis(state.payload);
  }

  async function pollSyncStatus() {
    if (!state.payload || state.loading || state.syncLoading) return;
    const rows = state.payload.rows || [];
    if (!rows.length) return;

    state.syncLoading = true;
    try {
      const response = await fetch('/pricing/api/atencao-imediata-sync', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'same-origin',
        body: JSON.stringify({
          start: state.payload.start,
          end: state.payload.end,
          items: rows.map((row) => ({
            alojamento: row.alojamento,
            price_alojamento: row.price_alojamento || row.alojamento
          }))
        })
      });
      applySyncPayload(await readJson(response));
    } catch (error) {
      // Polling deve ser silencioso para não interromper o utilizador.
    } finally {
      state.syncLoading = false;
    }
  }

  function ensureSyncPolling() {
    if (state.syncTimer) return;
    state.syncTimer = window.setInterval(pollSyncStatus, 10000);
  }

  function buildHead(dates) {
    const corner = document.createElement('div');
    corner.className = 'attention-corner';
    corner.textContent = 'Alojamento';
    corner.style.gridColumn = '1';
    corner.style.gridRow = '1';
    els.grid.appendChild(corner);

    dates.forEach((item, idx) => {
      const head = document.createElement('div');
      head.className = `attention-date-head ${item.is_weekend ? 'is-weekend' : ''}`;
      head.style.gridColumn = String(idx + 2);
      head.style.gridRow = '1';
      const date = new Date(`${item.date}T00:00:00`);
      head.innerHTML = `
        <div class="attention-date-day">${escapeHtml(String(item.day).padStart(2, '0'))}</div>
        <div class="attention-date-meta">${escapeHtml(date.toLocaleDateString('pt-PT', { weekday: 'short' }))}</div>
      `;
      els.grid.appendChild(head);
    });
  }

  function reservationLabel(reservation) {
    if (!reservation) return '';
    return reservation.nome || reservation.origem || reservation.reserva || 'Reserva';
  }

  function renderReservationBars(row, rowNumber, dates) {
    (row.reservations || []).forEach((reservation) => {
      const startIndex = Math.max(0, Number(reservation.start_index || 0));
      const span = Math.min(dates.length - startIndex, Math.max(1, Number(reservation.span || 1)));
      if (startIndex >= dates.length || span <= 0) return;

      const bar = document.createElement('div');
      bar.className = 'attention-reservation';
      bar.style.gridColumn = `${startIndex + 2} / span ${span}`;
      bar.style.gridRow = String(rowNumber);
      bar.title = `${reservationLabel(reservation)} · ${reservation.datain || ''} a ${reservation.dataout || ''}`;
      bar.textContent = reservationLabel(reservation);
      els.grid.appendChild(bar);
    });
  }

  function renderRow(row, dates, rowIndex) {
    const rowNumber = rowIndex + 2;
    const lodge = document.createElement('div');
    lodge.className = 'attention-lodge';
    lodge.style.gridColumn = '1';
    lodge.style.gridRow = String(rowNumber);
    lodge.title = `${row.alojamento} · ${row.regime || '-'} · mínimo ${row.min_noites || 1} noite(s) · ${row.vacant_count || 0} livres`;
    lodge.innerHTML = `
      <div class="attention-lodge-name" title="${escapeHtml(row.alojamento)}">${escapeHtml(row.alojamento)}</div>
    `;
    els.grid.appendChild(lodge);

    dates.forEach((dateItem, idx) => {
      const day = (row.days || [])[idx] || {};
      const cell = document.createElement('div');
      cell.className = `attention-day ${dateItem.is_weekend ? 'is-weekend' : ''} ${day.state === 'occupied' ? 'is-occupied' : ''} ${day.state === 'blocked_gap' ? 'is-short-gap' : ''}`;
      cell.style.gridColumn = String(idx + 2);
      cell.style.gridRow = String(rowNumber);
      if (day.state === 'vacant') {
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.className = `attention-price ${day.synced === false ? 'is-unsynced' : ''}`;
        btn.dataset.alojamento = row.alojamento;
        btn.dataset.date = day.date;
        updatePriceButton(btn, row, day);
        btn.addEventListener('click', () => openPriceModal(row, day));
        cell.appendChild(btn);
      } else if (day.state === 'blocked_gap') {
        const shortGap = document.createElement('div');
        shortGap.className = 'attention-short-gap';
        shortGap.textContent = 'curto';
        shortGap.title = `Buraco inferior ao mínimo de ${row.min_noites || 1} noites`;
        cell.appendChild(shortGap);
      }
      els.grid.appendChild(cell);
    });
    renderReservationBars(row, rowNumber, dates);
  }

  function render(payload) {
    state.payload = payload;
    recalculatePayloadTotals(state.payload);
    updateKpis(payload);
    els.grid.innerHTML = '';
    const dates = payload.dates || [];
    const rows = payload.rows || [];
    els.empty.hidden = rows.length > 0;
    els.grid.hidden = rows.length === 0;
    if (!rows.length) return;
    buildHead(dates);
    rows.forEach((row, idx) => renderRow(row, dates, idx));
  }

  async function load() {
    if (!els.grid || state.loading) return;
    state.loading = true;
    els.refresh.disabled = true;
    els.grid.innerHTML = '<div class="attention-empty">A carregar...</div>';
    try {
      const query = new URLSearchParams();
      if (els.regime?.value) query.set('regime', els.regime.value);
      const response = await fetch(`/pricing/api/atencao-imediata?${query.toString()}`, {
        credentials: 'same-origin'
      });
      render(await readJson(response));
      ensureSyncPolling();
    } catch (error) {
      els.grid.innerHTML = `<div class="attention-empty">${escapeHtml(error.message || 'Erro ao carregar.')}</div>`;
    } finally {
      state.loading = false;
      els.refresh.disabled = false;
    }
  }

  function openPriceModal(row, day) {
    state.selected = { row, day };
    if (!state.modal && window.bootstrap && els.modal) {
      state.modal = window.bootstrap.Modal.getOrCreateInstance(els.modal);
    }
    els.title.textContent = `Alterar preço · ${row.alojamento}`;
    els.summary.textContent = `${row.alojamento} · ${day.date} · mínimo ${row.min_noites || 1} noite(s)`;
    els.value.value = Number(day.price || 0).toFixed(2);
    els.dateIni.value = day.date;
    els.dateFim.value = day.date;
    els.motivo.value = 'Atenção Imediata';
    els.belowMin.checked = false;
    setStatus('');
    state.modal?.show();
  }

  async function savePrice(event) {
    event.preventDefault();
    if (!state.selected) return;
    const payload = {
      alojamento: state.selected.row.alojamento,
      tipo: 'PRECO_FIXO',
      valor: parseMoneyValue(els.value.value),
      data_ini: els.dateIni.value,
      data_fim: els.dateFim.value,
      motivo: els.motivo.value || 'Atenção Imediata',
      permitir_abaixo_min: els.belowMin.checked
    };
    setStatus('A gravar...');
    try {
      const response = await fetch('/pricing/api/override', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'same-origin',
        body: JSON.stringify(payload)
      });
      await readJson(response);
      setStatus('Preço gravado.');
      state.modal?.hide();
      applyLocalPriceOverride(payload);
    } catch (error) {
      setStatus(error.message || 'Erro ao gravar.', true);
    }
  }

  els.refresh?.addEventListener('click', load);
  els.regime?.addEventListener('change', load);
  els.form?.addEventListener('submit', savePrice);
  load();
})();
