const geoState = {
  list: [],
  filtered: [],
  selected: null,
  original: null,
  dirty: false,
  map: null,
  marker: null,
  alternatives: [],
  mode: 'single',
  allLayer: null,
  lastSelected: null,
  routeLayer: null,
  routeStopsLayer: null,
  routeSelectedStamps: new Set()
};

const geoEls = {
  list: document.getElementById('geoList'),
  status: document.getElementById('geoListStatus'),
  search: document.getElementById('geoSearch'),
  toggleAll: document.getElementById('geoToggleAll'),
  count: document.getElementById('geoCount'),
  left: document.querySelector('.geo-left'),
  right: document.querySelector('.geo-right'),
  name: document.getElementById('geoSelectedName'),
  dirty: document.getElementById('geoDirty'),
  morada: document.getElementById('geoMorada'),
  codpost: document.getElementById('geoCodpost'),
  local: document.getElementById('geoLocal'),
  lat: document.getElementById('geoLat'),
  lon: document.getElementById('geoLon'),
  locate: document.getElementById('geoLocate'),
  save: document.getElementById('geoSave'),
  reset: document.getElementById('geoReset'),
  alt: document.getElementById('geoAlt'),
  routeBtn: document.getElementById('geoRouteBtn'),
  routeInfo: document.getElementById('geoRouteInfo'),
  routeModal: document.getElementById('geoRouteModal'),
  routeFrom: document.getElementById('geoRouteFrom'),
  routeCards: document.getElementById('geoRouteCards'),
  routeReturn: document.getElementById('geoRouteReturn'),
  routeLoading: document.getElementById('geoRouteLoading'),
  routeApply: document.getElementById('geoRouteApply')
};

const isInputEl = (el) => el && (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA' || el.tagName === 'SELECT');
const getFieldValue = (el) => {
  if (!el) return '';
  return isInputEl(el) ? el.value : (el.textContent || '');
};
const setFieldValue = (el, value) => {
  if (!el) return;
  if (isInputEl(el)) {
    el.value = value || '';
  } else {
    el.textContent = value || '—';
  }
};
const isSedeSelected = () => !!(geoState.selected && Number(geoState.selected.IS_SEDE || 0) === 1);

const setDirty = (dirty) => {
  if (isSedeSelected()) {
    geoState.dirty = false;
    if (geoEls.dirty) geoEls.dirty.classList.remove('visible');
    if (geoEls.save) geoEls.save.disabled = true;
    return;
  }
  geoState.dirty = !!dirty;
  if (geoEls.dirty) {
    geoEls.dirty.classList.toggle('visible', geoState.dirty);
  }
  if (geoEls.save) {
    geoEls.save.disabled = !geoState.dirty || !geoState.selected || geoState.mode === 'all';
  }
};

const updateLatLon = (lat, lon, markDirty = true) => {
  setFieldValue(geoEls.lat, lat != null ? Number(lat).toFixed(6) : '');
  setFieldValue(geoEls.lon, lon != null ? Number(lon).toFixed(6) : '');
  if (markDirty) setDirty(true);
};

const getLat = (item) => item.LAT ?? item.lat ?? null;
const getLon = (item) => item.LON ?? item.lon ?? null;

const createMap = () => {
  const map = L.map('geoMap', {
    center: [41.1579, -8.6291],
    zoom: 12
  });
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '&copy; OpenStreetMap'
  }).addTo(map);
  map.on('click', (e) => {
    if (isSedeSelected() || geoState.mode === 'all') return;
    setMarker(e.latlng.lat, e.latlng.lng);
    updateLatLon(e.latlng.lat, e.latlng.lng, true);
  });
  geoState.map = map;
  geoState.allLayer = L.markerClusterGroup();
};

const setMarker = (lat, lon) => {
  if (!geoState.map) return;
  const canEditMarker = geoState.mode !== 'all' && !isSedeSelected();
  if (!geoState.marker) {
    geoState.marker = L.marker([lat, lon], { draggable: canEditMarker }).addTo(geoState.map);
    geoState.marker.on('dragend', () => {
      if (!canEditMarker) return;
      const pos = geoState.marker.getLatLng();
      updateLatLon(pos.lat, pos.lng, true);
    });
  } else {
    geoState.marker.setLatLng([lat, lon]);
    if (geoState.marker.dragging) {
      if (canEditMarker) geoState.marker.dragging.enable();
      else geoState.marker.dragging.disable();
    }
  }
  geoState.map.setView([lat, lon], 16);
};

const clearMarker = () => {
  if (geoState.marker) {
    geoState.map.removeLayer(geoState.marker);
    geoState.marker = null;
  }
};

const clearRoute = () => {
  if (!geoState.map) return;
  if (geoState.routeLayer) {
    geoState.map.removeLayer(geoState.routeLayer);
    geoState.routeLayer = null;
  }
  if (geoState.routeStopsLayer) {
    geoState.map.removeLayer(geoState.routeStopsLayer);
    geoState.routeStopsLayer = null;
  }
  if (geoEls.routeInfo) {
    geoEls.routeInfo.style.display = 'none';
    geoEls.routeInfo.textContent = '';
  }
};

const renderList = () => {
  const list = geoState.filtered;
  geoEls.list.innerHTML = '';
  if (!list.length) {
    geoEls.list.innerHTML = '<div class="geo-empty">Sem resultados</div>';
    return;
  }
  list.forEach(item => {
    const div = document.createElement('div');
    div.className = 'geo-item';
    if (geoState.selected && geoState.selected.ALSTAMP === item.ALSTAMP) {
      div.classList.add('active');
    }
    const coords = (item.LAT != null && item.LON != null)
      ? `${Number(item.LAT).toFixed(6)}, ${Number(item.LON).toFixed(6)}`
      : 'Sem coordenadas';
    div.innerHTML = `
      <div class="geo-item-title">${item.NOME || ''}</div>
      <div class="geo-item-sub">${coords}</div>
    `;
    div.addEventListener('click', () => {
      if (geoState.mode === 'all') return;
      selectItem(item.ALSTAMP);
    });
    geoEls.list.appendChild(div);
  });
};

const applySearch = () => {
  const term = (geoEls.search.value || '').trim().toLowerCase();
  if (!term) {
    geoState.filtered = geoState.list.slice();
  } else {
    geoState.filtered = geoState.list.filter(item => {
      const text = `${item.NOME || ''} ${item.MORADA || ''} ${item.CODPOST || ''} ${item.LOCAL || ''}`.toLowerCase();
      return text.includes(term);
    });
  }
  renderList();
};

const loadList = async () => {
  geoEls.status.textContent = 'A carregar...';
  const res = await fetch('/api/alojamentos_geo');
  const data = await res.json();
  geoState.list = Array.isArray(data) ? data : [];
  geoState.filtered = geoState.list.slice();
  geoEls.status.textContent = `${geoState.list.length} alojamentos`;
  renderList();
  if (geoState.mode === 'all') {
    renderAllMarkers();
  }
};

const fillForm = (item) => {
  geoEls.name.textContent = item.NOME || 'Seleciona um alojamento';
  setFieldValue(geoEls.morada, item.MORADA || '');
  setFieldValue(geoEls.codpost, item.CODPOST || '');
  setFieldValue(geoEls.local, item.LOCAL || '');
  updateLatLon(item.LAT, item.LON, false);
  const readonly = geoState.mode === 'all';
  const locked = readonly || Number(item.IS_SEDE || 0) === 1;
  [geoEls.morada, geoEls.codpost, geoEls.local].forEach(el => {
    if (isInputEl(el)) el.readOnly = locked;
  });
  geoEls.locate.disabled = locked;
  geoEls.save.disabled = locked || !geoState.dirty;
  geoEls.reset.disabled = locked;
  if (geoEls.routeBtn) geoEls.routeBtn.disabled = (geoState.mode === 'all' || !item.ALSTAMP);
};

const selectItem = async (alstamp) => {
  if (geoState.mode === 'all') return;
  const res = await fetch(`/api/alojamentos_geo/${alstamp}`);
  const data = await res.json();
  if (data.error) {
    showToast(data.error, 'danger');
    return;
  }
  geoState.selected = data;
  geoState.lastSelected = data.ALSTAMP;
  geoState.original = { ...data };
  setDirty(false);
  clearRoute();
  fillForm(data);
  geoEls.alt.innerHTML = '';
  if (data.LAT != null && data.LON != null) {
    setMarker(data.LAT, data.LON);
  } else {
    clearMarker();
    await locateOnMap();
  }
  applySearch();
};

const locateOnMap = async () => {
  if (!geoState.selected) {
    showToast('Seleciona um alojamento primeiro.', 'warning');
    return;
  }
  if (isSedeSelected()) return;
  geoEls.alt.innerHTML = '<div class="geo-alt-loading">A localizar...</div>';
  const payload = {
    morada: getFieldValue(geoEls.morada),
    codpost: getFieldValue(geoEls.codpost),
    local: getFieldValue(geoEls.local),
    limit: 5
  };
  const res = await fetch('/api/alojamentos_geo/geocode', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
  const data = await res.json();
  if (data.error) {
    geoEls.alt.innerHTML = `<div class="geo-alt-error">${data.error}</div>`;
    return;
  }
  geoState.alternatives = data.results || [];
  if (!geoState.alternatives.length) {
    geoEls.alt.innerHTML = `<div class="geo-alt-error">Não foi possível localizar...</div>`;
    return;
  }
  const first = geoState.alternatives[0];
  setMarker(first.lat, first.lon);
  updateLatLon(first.lat, first.lon, true);
  renderAlternatives();
};

const renderAlternatives = () => {
  if (!geoState.alternatives.length) {
    geoEls.alt.innerHTML = '';
    return;
  }
  const list = document.createElement('div');
  list.className = 'geo-alt-list';
  geoState.alternatives.slice(0, 5).forEach((alt, idx) => {
    const item = document.createElement('button');
    item.type = 'button';
    item.className = 'geo-alt-item';
    item.innerHTML = `<span>${idx + 1}. ${alt.display_name}</span>`;
    item.addEventListener('click', () => {
      setMarker(alt.lat, alt.lon);
      updateLatLon(alt.lat, alt.lon, true);
    });
    list.appendChild(item);
  });
  geoEls.alt.innerHTML = '<div class="geo-alt-title">Alternativas</div>';
  geoEls.alt.appendChild(list);
};

const resetToDb = () => {
  if (isSedeSelected()) return;
  if (!geoState.original) return;
  fillForm(geoState.original);
  geoEls.alt.innerHTML = '';
  if (geoState.original.LAT != null && geoState.original.LON != null) {
    setMarker(geoState.original.LAT, geoState.original.LON);
  } else {
    clearMarker();
  }
  setDirty(false);
};

const setAllModeUI = (enabled) => {
  geoState.mode = enabled ? 'all' : 'single';
  geoEls.left.classList.toggle('geo-disabled', enabled);
  geoEls.search.disabled = enabled;
  geoEls.right.classList.toggle('geo-readonly', enabled);
  geoEls.locate.disabled = enabled;
  geoEls.save.disabled = enabled || !geoState.dirty;
  geoEls.reset.disabled = enabled;
  geoEls.routeBtn.disabled = enabled || !geoState.selected;
  if (geoEls.toggleAll) {
    geoEls.toggleAll.classList.toggle('btn-outline-primary', !enabled);
    geoEls.toggleAll.classList.toggle('btn-primary', enabled);
    geoEls.toggleAll.textContent = enabled ? 'Voltar ao modo individual ' : 'Mostra Todos ';
    if (geoEls.count) {
      geoEls.toggleAll.appendChild(geoEls.count);
    }
  }
};

const renderAllMarkers = () => {
  if (!geoState.map || !geoState.allLayer) return;
  geoState.allLayer.clearLayers();
  const valid = geoState.list.filter(item => {
    const lat = parseFloat(getLat(item));
    const lon = parseFloat(getLon(item));
    return Number.isFinite(lat) && Number.isFinite(lon);
  });
  valid.forEach(item => {
    const lat = parseFloat(getLat(item));
    const lon = parseFloat(getLon(item));
    const marker = L.marker([lat, lon], { draggable: false });
    marker.bindPopup(`<strong>${item.NOME || ''}</strong><br>${lat.toFixed(6)}, ${lon.toFixed(6)}`);
    geoState.allLayer.addLayer(marker);
  });
  geoState.map.addLayer(geoState.allLayer);
  if (valid.length) {
    const bounds = geoState.allLayer.getBounds();
    geoState.map.fitBounds(bounds, { padding: [20, 20] });
  }
  if (geoEls.count) {
    geoEls.count.textContent = `(${valid.length} no mapa)`;
  }
};

const clearAllMarkers = () => {
  if (!geoState.map || !geoState.allLayer) return;
  geoState.map.removeLayer(geoState.allLayer);
  geoState.allLayer.clearLayers();
};

const enterAllMode = () => {
  geoState.lastSelected = geoState.selected ? geoState.selected.ALSTAMP : geoState.lastSelected;
  clearMarker();
  geoEls.alt.innerHTML = '';
  clearRoute();
  setAllModeUI(true);
  if (!geoState.list.length) {
    loadList().then(renderAllMarkers).catch(() => renderAllMarkers());
  } else {
    renderAllMarkers();
  }
};

const exitAllMode = () => {
  setAllModeUI(false);
  clearAllMarkers();
  if (geoState.lastSelected) {
    selectItem(geoState.lastSelected);
  }
};

const saveCoords = async () => {
  if (isSedeSelected()) {
    showToast('A geolocalização da sede não é editável neste ecrã.', 'warning');
    return;
  }
  if (!geoState.selected) {
    showToast('Seleciona um alojamento primeiro.', 'warning');
    return;
  }
  const lat = parseFloat(getFieldValue(geoEls.lat));
  const lon = parseFloat(getFieldValue(geoEls.lon));
  if (Number.isNaN(lat) || Number.isNaN(lon)) {
    showToast('Latitude/Longitude inválidas.', 'danger');
    return;
  }
  const payload = {
    lat,
    lon,
    morada: getFieldValue(geoEls.morada),
    codpost: getFieldValue(geoEls.codpost),
    local: getFieldValue(geoEls.local)
  };
  const res = await fetch(`/api/alojamentos_geo/${geoState.selected.ALSTAMP}/coords`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
  const data = await res.json();
  if (!data.success) {
    showToast(data.error || 'Erro ao guardar', 'danger');
    return;
  }
  showToast('Coordenadas guardadas.');
  geoState.selected = { ...geoState.selected, ...payload, LAT: lat, LON: lon };
  geoState.original = { ...geoState.selected };
  const idx = geoState.list.findIndex(item => item.ALSTAMP === geoState.selected.ALSTAMP);
  if (idx >= 0) {
    geoState.list[idx] = { ...geoState.list[idx], ...geoState.selected };
  }
  setDirty(false);
  applySearch();
};

const openRouteModal = () => {
  if (!geoState.selected) {
    showToast('Seleciona um local primeiro.', 'warning');
    return;
  }
  if (geoState.mode === 'all') return;
  if (geoEls.routeFrom) geoEls.routeFrom.textContent = geoState.selected.NOME || '—';
  geoState.routeSelectedStamps = new Set();
  if (geoEls.routeReturn) geoEls.routeReturn.checked = false;
  const selectedStamp = String(geoState.selected.ALSTAMP || '').trim();
  const opts = geoState.list.filter(x => String(x.ALSTAMP || '').trim() !== selectedStamp);
  if (geoEls.routeCards) {
    geoEls.routeCards.innerHTML = '';
    opts.forEach(item => {
      const stamp = String(item.ALSTAMP || '').trim();
      const card = document.createElement('button');
      card.type = 'button';
      card.className = 'geo-route-card';
      card.dataset.stamp = stamp;
      const hasCoords = Number.isFinite(Number(item.LAT)) && Number.isFinite(Number(item.LON));
      card.innerHTML = `
        <div class="geo-route-card-title">${item.NOME || stamp}</div>
        <div class="geo-route-card-sub">${hasCoords ? `${Number(item.LAT).toFixed(4)}, ${Number(item.LON).toFixed(4)}` : 'Sem coordenadas'}</div>
      `;
      card.addEventListener('click', () => {
        if (geoState.routeSelectedStamps.has(stamp)) {
          geoState.routeSelectedStamps.delete(stamp);
          card.classList.remove('active');
        } else {
          geoState.routeSelectedStamps.add(stamp);
          card.classList.add('active');
        }
      });
      geoEls.routeCards.appendChild(card);
    });
  }
  bootstrap.Modal.getOrCreateInstance(geoEls.routeModal).show();
};

const drawRoute = async () => {
  if (!geoState.selected) return;
  const fromStamp = String(geoState.selected.ALSTAMP || '').trim();
  const destinations = Array.from(geoState.routeSelectedStamps || []);
  if (!destinations.length) {
    showToast('Seleciona pelo menos um destino.', 'warning');
    return;
  }
  if (geoEls.routeLoading) geoEls.routeLoading.classList.add('visible');
  if (geoEls.routeApply) geoEls.routeApply.disabled = true;
  if (geoEls.routeCards) geoEls.routeCards.style.pointerEvents = 'none';
  let res, data;
  try {
    res = await fetch('/api/alojamentos_geo/rota', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        from_stamp: fromStamp,
        to_stamps: destinations,
        return_to_origin: !!geoEls.routeReturn?.checked
      })
    });
    data = await res.json().catch(() => ({}));
  } finally {
    if (geoEls.routeLoading) geoEls.routeLoading.classList.remove('visible');
    if (geoEls.routeApply) geoEls.routeApply.disabled = false;
    if (geoEls.routeCards) geoEls.routeCards.style.pointerEvents = '';
  }
  if (!res?.ok || data?.error) {
    showToast(data?.error || 'Não foi possível calcular o percurso.', 'danger');
    return;
  }
  const coords = (data.geometry && Array.isArray(data.geometry.coordinates)) ? data.geometry.coordinates : [];
  if (!coords.length) {
    showToast('Sem geometria de percurso.', 'warning');
    return;
  }
  clearRoute();
  const latlngs = coords.map(c => [Number(c[1]), Number(c[0])]);
  geoState.routeLayer = L.polyline(latlngs, { color: '#2563eb', weight: 4, opacity: 0.9 }).addTo(geoState.map);
  geoState.routeStopsLayer = L.layerGroup().addTo(geoState.map);
  if (Array.isArray(data.route_points)) {
    data.route_points.forEach((pt, idx) => {
      const lat = Number(pt.lat);
      const lon = Number(pt.lon);
      if (!Number.isFinite(lat) || !Number.isFinite(lon)) return;
      const marker = L.marker([lat, lon], {
        icon: L.divIcon({
          className: 'geo-route-stop-icon',
          html: `<span>${idx + 1}</span>`,
          iconSize: [20, 20],
          iconAnchor: [10, 10]
        })
      });
      marker.bindTooltip(`${idx + 1}. ${pt.name || ''}`, { direction: 'top', offset: [0, -8] });
      geoState.routeStopsLayer.addLayer(marker);
    });
  }
  geoState.map.fitBounds(geoState.routeLayer.getBounds(), { padding: [24, 24] });
  if (geoEls.routeInfo) {
    geoEls.routeInfo.style.display = 'block';
    const routeNames = Array.isArray(data.route_names) ? data.route_names.join(' → ') : '';
    geoEls.routeInfo.textContent = `${routeNames || `${data.from_name} → ${data.to_name || ''}`} • ${Number(data.distance_km || 0).toFixed(2)} km • ${Number(data.duration_min || 0)} min`;
    if (Array.isArray(data.combinations) && data.combinations.length) {
      const tooltip = data.combinations.map((c, idx) => {
        const names = Array.isArray(c.route_names) ? c.route_names.join(' → ') : '';
        const km = (c.distance_km == null) ? '-' : `${Number(c.distance_km).toFixed(2)} km`;
        const mins = (c.duration_min == null) ? '-' : `${Number(c.duration_min)} min`;
        let extra = '';
        if (c.status === 'coords_separadas') extra = ' [coords separadas]';
        if (c.status === 'sem_rota') extra = ' [sem rota]';
        return `${idx + 1}. ${names} • ${km} • ${mins}${extra}`;
      }).join('\n');
      geoEls.routeInfo.title = tooltip;
    } else {
      geoEls.routeInfo.title = '';
    }
  }
  bootstrap.Modal.getInstance(geoEls.routeModal)?.hide();
};

const bindFormEvents = () => {
  if (geoEls.routeBtn) geoEls.routeBtn.disabled = true;
  [geoEls.morada, geoEls.codpost, geoEls.local].forEach(el => {
    if (isInputEl(el)) {
      el.addEventListener('input', () => setDirty(true));
    }
  });
  geoEls.locate.addEventListener('click', locateOnMap);
  geoEls.reset.addEventListener('click', resetToDb);
  geoEls.save.addEventListener('click', saveCoords);
  geoEls.routeBtn.addEventListener('click', openRouteModal);
  geoEls.routeApply.addEventListener('click', drawRoute);
  geoEls.search.addEventListener('input', applySearch);
  geoEls.toggleAll.addEventListener('click', () => {
    if (geoState.mode === 'single') {
      enterAllMode();
    } else {
      exitAllMode();
    }
  });
};

const rotasEls = {
  start: document.getElementById('rotasStart'),
  resume: document.getElementById('rotasResume'),
  missing: document.getElementById('rotasMissing'),
  stop: document.getElementById('rotasStop'),
  bar: document.getElementById('rotasProgress'),
  text: document.getElementById('rotasText'),
  counts: document.getElementById('rotasCounts')
};

let rotasPollTimer = null;
let rotasJobId = null;

const updateRotasUI = (data) => {
  if (!data) return;
  const state = data.State || data.state || '';
  const total = Number(data.Total || 0);
  const processed = Number(data.Processed || 0);
  const ok = Number(data.Ok || 0);
  const errors = Number(data.Errors || 0);
  const pending = Number(data.Pending || 0);
  const percent = total > 0 ? Math.min(100, Math.round((processed / total) * 100)) : 0;
  if (rotasEls.bar) rotasEls.bar.style.width = `${percent}%`;
  if (rotasEls.text) rotasEls.text.textContent = data.Message || data.Stage || state || '';
  if (rotasEls.counts) {
    rotasEls.counts.textContent = `${processed}/${total} · OK ${ok} · Erros ${errors} · Pendentes ${pending}`;
  }
  if (rotasEls.start) {
    rotasEls.start.disabled = (state === 'running' || state === 'stopping');
  }
  if (rotasEls.resume) {
    rotasEls.resume.disabled = (state === 'running' || state === 'stopping');
  }
  if (rotasEls.missing) {
    rotasEls.missing.disabled = (state === 'running' || state === 'stopping');
  }
  if (rotasEls.stop) {
    rotasEls.stop.disabled = !(state === 'running' || state === 'stopping');
  }
};

const stopRotasPolling = () => {
  if (rotasPollTimer) {
    clearInterval(rotasPollTimer);
    rotasPollTimer = null;
  }
};

const pollRotasStatus = async () => {
  if (!rotasJobId) return;
  const res = await fetch(`/api/rotas/rebuild/status?job_id=${encodeURIComponent(rotasJobId)}`);
  const data = await res.json();
  updateRotasUI(data);
  const state = data.State || data.state || '';
  if (state === 'done' || state === 'error' || state === 'stopped') {
    stopRotasPolling();
  }
};

const startRotasPolling = () => {
  stopRotasPolling();
  rotasPollTimer = setInterval(pollRotasStatus, 1500);
};

const startRotasJob = async () => {
  if (!confirm('Isto pode demorar; vai recalcular todas as rotas. Continuar?')) return;
  const res = await fetch('/api/rotas/rebuild/start', { method: 'POST' });
  const data = await res.json();
  if (res.status === 409 && data.job_id) {
    rotasJobId = data.job_id;
    startRotasPolling();
    return;
  }
  if (!data.job_id) {
    showToast(data.error || 'Não foi possível iniciar', 'danger');
    return;
  }
  rotasJobId = data.job_id;
  startRotasPolling();
};

const resumeRotasJob = async () => {
  if (!confirm('Retomar apenas as rotas pendentes?')) return;
  const res = await fetch('/api/rotas/rebuild/resume', { method: 'POST' });
  const data = await res.json();
  if (res.status === 409 && data.job_id) {
    rotasJobId = data.job_id;
    startRotasPolling();
    return;
  }
  if (!data.job_id) {
    showToast(data.error || 'NÃ£o foi possÃ­vel retomar', 'danger');
    return;
  }
  rotasJobId = data.job_id;
  startRotasPolling();
};

const stopRotasJob = async () => {
  if (!rotasJobId) return;
  await fetch('/api/rotas/rebuild/stop', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ job_id: rotasJobId })
  });
  pollRotasStatus();
};

const generateMissingRotas = async () => {
  let data = {};
  let res;
  try {
    res = await fetch('/api/rotas/rebuild/generate_missing', { method: 'POST' });
    data = await res.json();
  } catch (e) {
    showToast('Erro ao gerar pares', 'danger');
    return;
  }
  if (!res.ok || !(data.ok || data.success)) {
    showToast(data.error || 'Erro ao gerar pares', 'danger');
    return;
  }
  showToast(`Pares gerados: ${data.inserted || 0}`);
};

const initRotas = () => {
  if (!rotasEls.start) return;
  rotasEls.start.addEventListener('click', startRotasJob);
  if (rotasEls.resume) {
    rotasEls.resume.addEventListener('click', resumeRotasJob);
  }
  if (rotasEls.missing) {
    rotasEls.missing.addEventListener('click', generateMissingRotas);
  }
  rotasEls.stop.addEventListener('click', stopRotasJob);
  fetch('/api/rotas/rebuild/status')
    .then(r => r.json())
    .then(data => {
      if (data.JobId) rotasJobId = data.JobId;
      updateRotasUI(data);
      const state = data.State || data.state || '';
      if (state === 'running' || state === 'stopping') {
        startRotasPolling();
      }
    })
    .catch(() => {});
};

document.addEventListener('DOMContentLoaded', () => {
  createMap();
  bindFormEvents();
  initRotas();
  loadList().catch(() => {
    geoEls.status.textContent = 'Erro ao carregar.';
  });
});
