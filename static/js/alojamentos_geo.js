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
  lastSelected: null
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
  alt: document.getElementById('geoAlt')
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

const setDirty = (dirty) => {
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
    setMarker(e.latlng.lat, e.latlng.lng);
    updateLatLon(e.latlng.lat, e.latlng.lng, true);
  });
  geoState.map = map;
  geoState.allLayer = L.markerClusterGroup();
};

const setMarker = (lat, lon) => {
  if (!geoState.map) return;
  if (!geoState.marker) {
    geoState.marker = L.marker([lat, lon], { draggable: true }).addTo(geoState.map);
    geoState.marker.on('dragend', () => {
      const pos = geoState.marker.getLatLng();
      updateLatLon(pos.lat, pos.lng, true);
    });
  } else {
    geoState.marker.setLatLng([lat, lon]);
  }
  geoState.map.setView([lat, lon], 16);
};

const clearMarker = () => {
  if (geoState.marker) {
    geoState.map.removeLayer(geoState.marker);
    geoState.marker = null;
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
  [geoEls.morada, geoEls.codpost, geoEls.local].forEach(el => {
    if (isInputEl(el)) el.readOnly = readonly;
  });
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

const bindFormEvents = () => {
  [geoEls.morada, geoEls.codpost, geoEls.local].forEach(el => {
    if (isInputEl(el)) {
      el.addEventListener('input', () => setDirty(true));
    }
  });
  geoEls.locate.addEventListener('click', locateOnMap);
  geoEls.reset.addEventListener('click', resetToDb);
  geoEls.save.addEventListener('click', saveCoords);
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

const initRotas = () => {
  if (!rotasEls.start) return;
  rotasEls.start.addEventListener('click', startRotasJob);
  if (rotasEls.resume) {
    rotasEls.resume.addEventListener('click', resumeRotasJob);
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
