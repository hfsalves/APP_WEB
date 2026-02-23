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
  routeSelectedStamps: new Set(),
  metroLayer: null,
  metroVisible: false,
  metroLoaded: false,
  poiList: [],
  poiFiltered: [],
  poiSelected: null,
  poiGroups: [],
  poiModalSelectedStamp: null,
  poiPlaceResults: [],
  poiMarker: null,
  poiEditStamp: null
};

const geoEls = {
  list: document.getElementById('geoList'),
  status: document.getElementById('geoListStatus'),
  search: document.getElementById('geoSearch'),
  toggleAll: document.getElementById('geoToggleAll'),
  toggleMetro: document.getElementById('geoToggleMetro'),
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
  routeApply: document.getElementById('geoRouteApply'),
  poiSearch: document.getElementById('geoPoiSearch'),
  poiStatus: document.getElementById('geoPoiStatus'),
  poiList: document.getElementById('geoPoiList'),
  poiDetail: document.getElementById('geoPoiDetail'),
  poiAddBtn: document.getElementById('geoPoiAddBtn'),
  poiGroupsBtn: document.getElementById('geoPoiGroupsBtn'),
  poiModal: document.getElementById('geoPoiModal'),
  poiStepSearch: document.getElementById('geoPoiStepSearch'),
  poiStepCreate: document.getElementById('geoPoiStepCreate'),
  poiStepAssoc: document.getElementById('geoPoiStepAssoc'),
  poiModalSearch: document.getElementById('geoPoiModalSearch'),
  poiModalResults: document.getElementById('geoPoiModalResults'),
  poiShowCreate: document.getElementById('geoPoiShowCreate'),
  poiCreateNome: document.getElementById('geoPoiCreateNome'),
  poiCreateTipo: document.getElementById('geoPoiCreateTipo'),
  poiCreateGrupo: document.getElementById('geoPoiCreateGrupo'),
  poiCreateMorada: document.getElementById('geoPoiCreateMorada'),
  poiCreateLat: document.getElementById('geoPoiCreateLat'),
  poiCreateLng: document.getElementById('geoPoiCreateLng'),
  poiCreateUrl: document.getElementById('geoPoiCreateUrl'),
  poiCreateUrlMaps: document.getElementById('geoPoiCreateUrlMaps'),
  poiCreateSave: document.getElementById('geoPoiCreateSave'),
  poiCreateCancel: document.getElementById('geoPoiCreateCancel'),
  poiAssocBack: document.getElementById('geoPoiAssocBack'),
  poiAssocName: document.getElementById('geoPoiAssocName'),
  poiAssocList: document.getElementById('geoPoiAssocList'),
  poiAssocConfirm: document.getElementById('geoPoiAssocConfirm'),
  poigModal: document.getElementById('geoPoigModal'),
  poigList: document.getElementById('geoPoigList'),
  poigStamp: document.getElementById('geoPoigStamp'),
  poigNome: document.getElementById('geoPoigNome'),
  poigSlug: document.getElementById('geoPoigSlug'),
  poigDescr: document.getElementById('geoPoigDescr'),
  poigOrdem: document.getElementById('geoPoigOrdem'),
  poigAtivo: document.getElementById('geoPoigAtivo'),
  poigSave: document.getElementById('geoPoigSave'),
  poigClear: document.getElementById('geoPoigClear')
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
const hasValidCoords = (item) => {
  const lat = Number(getLat(item));
  const lon = Number(getLon(item));
  if (!Number.isFinite(lat) || !Number.isFinite(lon)) return false;
  if (Math.abs(lat) < 0.000001 && Math.abs(lon) < 0.000001) return false;
  return true;
};

const createMap = () => {
  const map = L.map('geoMap', {
    center: [41.1579, -8.6291],
    zoom: 12
  });

  const osm = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '&copy; OpenStreetMap'
  });
  const sat = L.tileLayer(
    'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
    {
      maxZoom: 19,
      attribution: 'Tiles &copy; Esri'
    }
  );

  osm.addTo(map);
  L.control.layers(
    {
      'OpenStreetMap': osm,
      'Satélite': sat
    },
    {},
    { position: 'topright' }
  ).addTo(map);

  map.on('click', (e) => {
    if (isSedeSelected() || geoState.mode === 'all') return;
    setMarker(e.latlng.lat, e.latlng.lng);
    updateLatLon(e.latlng.lat, e.latlng.lng, true);
  });
  geoState.map = map;
  geoState.allLayer = L.markerClusterGroup();
  geoState.metroLayer = L.layerGroup();
};

const normalizeMetroColor = (raw, fallback = '#1d4ed8') => {
  const val = String(raw || '').trim();
  if (!val) return fallback;
  if (/^#[0-9a-f]{6}$/i.test(val)) return val;
  if (/^[0-9a-f]{6}$/i.test(val)) return `#${val}`;
  return fallback;
};

const metroFallbackColorByRef = (ref) => {
  switch (String(ref || '').trim().toUpperCase()) {
    case 'A': return '#2b6cb0';
    case 'B': return '#d53f8c';
    case 'C': return '#38a169';
    case 'D': return '#805ad5';
    case 'E': return '#d69e2e';
    case 'F': return '#dd6b20';
    default: return '#1d4ed8';
  }
};

const parseMetroSegments = (relation) => {
  const out = [];
  if (Array.isArray(relation?.members)) {
    relation.members.forEach((m) => {
      if (!Array.isArray(m?.geometry) || m.geometry.length < 2) return;
      const latlngs = m.geometry
        .map((p) => [Number(p.lat), Number(p.lon)])
        .filter((xy) => Number.isFinite(xy[0]) && Number.isFinite(xy[1]));
      if (latlngs.length >= 2) out.push(latlngs);
    });
  }
  if (!out.length && Array.isArray(relation?.geometry) && relation.geometry.length >= 2) {
    const latlngs = relation.geometry
      .map((p) => [Number(p.lat), Number(p.lon)])
      .filter((xy) => Number.isFinite(xy[0]) && Number.isFinite(xy[1]));
    if (latlngs.length >= 2) out.push(latlngs);
  }
  return out;
};

const loadMetroLayer = async () => {
  if (geoState.metroLoaded) return true;
  if (!geoState.map || !geoState.metroLayer) return false;

  const query = [
    '[out:json][timeout:30];',
    '(',
    'relation["type"="route"]["route"~"subway|light_rail"]["operator"~"Metro do Porto",i];',
    ');',
    'out geom;'
  ].join('');

  let payload = null;
  try {
    const res = await fetch('https://overpass-api.de/api/interpreter', {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8' },
      body: `data=${encodeURIComponent(query)}`
    });
    payload = await res.json();
    if (!res.ok) throw new Error(payload?.remark || res.statusText);
  } catch (err) {
    showToast(`Erro ao carregar Metro: ${err.message || err}`, 'danger');
    return false;
  }

  const rels = Array.isArray(payload?.elements)
    ? payload.elements.filter((e) => e && e.type === 'relation')
    : [];
  if (!rels.length) {
    showToast('Sem dados de linhas de Metro no OpenStreetMap.', 'warning');
    return false;
  }

  rels.forEach((rel) => {
    const tags = rel.tags || {};
    const ref = String(tags.ref || '').trim();
    const lineName = String(tags.name || '').trim() || (ref ? `Linha ${ref}` : 'Metro do Porto');
    const color = normalizeMetroColor(tags.colour || tags.color || tags.route_color, metroFallbackColorByRef(ref));
    const segments = parseMetroSegments(rel);
    segments.forEach((latlngs) => {
      const poly = L.polyline(latlngs, {
        color,
        weight: 4,
        opacity: 0.85,
        lineCap: 'round',
        lineJoin: 'round'
      });
      poly.bindTooltip(lineName, { sticky: true, direction: 'top', opacity: 0.9 });
      geoState.metroLayer.addLayer(poly);
    });
  });

  geoState.metroLoaded = true;
  return geoState.metroLayer.getLayers().length > 0;
};

const setMetroButtonState = () => {
  if (!geoEls.toggleMetro) return;
  geoEls.toggleMetro.classList.toggle('btn-outline-secondary', !geoState.metroVisible);
  geoEls.toggleMetro.classList.toggle('btn-primary', geoState.metroVisible);
};

const toggleMetroLayer = async () => {
  if (!geoState.map || !geoState.metroLayer) return;
  if (geoState.metroVisible) {
    geoState.map.removeLayer(geoState.metroLayer);
    geoState.metroVisible = false;
    setMetroButtonState();
    return;
  }

  if (geoEls.toggleMetro) {
    geoEls.toggleMetro.disabled = true;
    geoEls.toggleMetro.textContent = 'Metro...';
  }
  const ok = await loadMetroLayer();
  if (geoEls.toggleMetro) {
    geoEls.toggleMetro.disabled = false;
    geoEls.toggleMetro.textContent = 'Metro';
  }
  if (!ok) {
    setMetroButtonState();
    return;
  }

  geoState.metroLayer.addTo(geoState.map);
  geoState.metroVisible = true;
  setMetroButtonState();
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

const clearPoiMarker = () => {
  if (!geoState.map || !geoState.poiMarker) return;
  geoState.map.removeLayer(geoState.poiMarker);
  geoState.poiMarker = null;
};

const showPoiOnMap = (poi) => {
  if (!geoState.map || !poi) return;
  const lat = Number(poi.LAT ?? poi.lat ?? null);
  const lng = Number(poi.LNG ?? poi.lng ?? null);
  if (!Number.isFinite(lat) || !Number.isFinite(lng)) {
    showToast('POI sem coordenadas válidas.', 'warning');
    return;
  }
  clearPoiMarker();
  geoState.poiMarker = L.circleMarker([lat, lng], {
    radius: 9,
    color: '#1d4ed8',
    weight: 2,
    fillColor: '#60a5fa',
    fillOpacity: 0.95
  }).addTo(geoState.map);
  geoState.poiMarker.bindPopup(
    `<strong>${esc(poi.NOME || 'POI')}</strong><br>${lat.toFixed(6)}, ${lng.toFixed(6)}`
  ).openPopup();
  geoState.map.setView([lat, lng], Math.max(geoState.map.getZoom(), 16));
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
    const hasCoords = hasValidCoords(item);
    if (!hasCoords) div.classList.add('geo-item-no-coords');
    const coords = hasCoords
      ? `${Number(getLat(item)).toFixed(6)}, ${Number(getLon(item)).toFixed(6)}`
      : 'Sem coordenadas';
    div.innerHTML = `
      <div class="geo-item-head">
        <div class="geo-item-title">${item.NOME || ''}</div>
        <span class="geo-item-badge ${hasCoords ? 'ok' : 'warn'}">${hasCoords ? 'GPS' : 'Sem GPS'}</span>
      </div>
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
  clearPoiMarker();
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
  if (hasValidCoords(data)) {
    setMarker(Number(getLat(data)), Number(getLon(data)));
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
  if (hasValidCoords(geoState.original)) {
    setMarker(Number(getLat(geoState.original)), Number(getLon(geoState.original)));
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
  const valid = geoState.list.filter(item => hasValidCoords(item));
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
  clearPoiMarker();
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
  clearPoiMarker();
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
      const hasCoords = hasValidCoords(item);
      card.innerHTML = `
        <div class="geo-route-card-title">${item.NOME || stamp}</div>
        <div class="geo-route-card-sub">${hasCoords ? `${Number(getLat(item)).toFixed(4)}, ${Number(getLon(item)).toFixed(4)}` : 'Sem coordenadas'}</div>
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

const esc = (v) => String(v == null ? '' : v)
  .replace(/&/g, '&amp;')
  .replace(/</g, '&lt;')
  .replace(/>/g, '&gt;')
  .replace(/"/g, '&quot;')
  .replace(/'/g, '&#39;');

const debounce = (fn, wait = 300) => {
  let t = null;
  return (...args) => {
    if (t) clearTimeout(t);
    t = setTimeout(() => fn(...args), wait);
  };
};

const poiModal = geoEls.poiModal ? bootstrap.Modal.getOrCreateInstance(geoEls.poiModal) : null;
const poigModal = geoEls.poigModal ? bootstrap.Modal.getOrCreateInstance(geoEls.poigModal) : null;

const poiSetStep = (step) => {
  if (geoEls.poiStepSearch) geoEls.poiStepSearch.style.display = step === 'search' ? '' : 'none';
  if (geoEls.poiStepCreate) geoEls.poiStepCreate.style.display = step === 'create' ? '' : 'none';
  if (geoEls.poiStepAssoc) geoEls.poiStepAssoc.style.display = step === 'assoc' ? '' : 'none';
  if (geoEls.poiAssocConfirm) geoEls.poiAssocConfirm.style.display = step === 'assoc' ? '' : 'none';
};

const loadPoiGroups = async () => {
  try {
    const res = await fetch('/api/poig');
    const data = await res.json();
    geoState.poiGroups = Array.isArray(data) ? data : [];
  } catch (_) {
    geoState.poiGroups = [];
  }
  if (geoEls.poiCreateGrupo) {
    geoEls.poiCreateGrupo.innerHTML = `<option value="">(Sem grupo)</option>` + geoState.poiGroups
      .map(g => `<option value="${esc(g.POIGSTAMP)}">${esc(g.NOME || '')}</option>`)
      .join('');
  }
};

const renderPoiList = () => {
  if (!geoEls.poiList) return;
  const rows = geoState.poiFiltered || [];
  if (!rows.length) {
    geoEls.poiList.innerHTML = '<div class="geo-empty">Sem POI</div>';
    return;
  }
  geoEls.poiList.innerHTML = rows.map((r) => `
    <div class="geo-item ${geoState.poiSelected && geoState.poiSelected.POISTAMP === r.POISTAMP ? 'active' : ''}" data-poi="${esc(r.POISTAMP)}">
      <div class="geo-item-head">
        <div class="geo-item-title">${esc(r.NOME || '')}</div>
        <span class="geo-item-badge ${Number(r.ATIVO || 0) ? 'ok' : 'warn'}">${Number(r.ATIVO || 0) ? 'Ativo' : 'Inativo'}</span>
      </div>
      <div class="geo-item-sub">${esc(r.GRUPO_NOME || 'Sem grupo')} · ${esc(r.TIPO || '-')} · ${Number(r.ALOJ_CNT || 0)} aloj.</div>
    </div>
  `).join('');
  geoEls.poiList.querySelectorAll('[data-poi]').forEach((el) => {
    el.addEventListener('click', () => selectPoi(el.getAttribute('data-poi') || ''));
    const stamp = el.getAttribute('data-poi') || '';
    const actions = document.createElement('div');
    actions.className = 'd-flex gap-1 mt-2';
    const btnEdit = document.createElement('button');
    btnEdit.type = 'button';
    btnEdit.className = 'btn btn-outline-secondary btn-sm py-0 px-2';
    btnEdit.textContent = 'Editar';
    btnEdit.addEventListener('click', (ev) => {
      ev.stopPropagation();
      openPoiEditModal(stamp);
    });
    const btnAssoc = document.createElement('button');
    btnAssoc.type = 'button';
    btnAssoc.className = 'btn btn-outline-primary btn-sm py-0 px-2';
    btnAssoc.textContent = 'Associar';
    btnAssoc.addEventListener('click', (ev) => {
      ev.stopPropagation();
      if (!stamp) return;
      poiModal?.show();
      openPoiAssocStep(stamp, geoState.poiList);
    });
    actions.appendChild(btnEdit);
    actions.appendChild(btnAssoc);
    el.appendChild(actions);
  });
};

const loadPoiList = async () => {
  if (!geoEls.poiStatus) return;
  geoEls.poiStatus.textContent = 'A carregar POI...';
  const q = (geoEls.poiSearch?.value || '').trim();
  const qs = new URLSearchParams();
  if (q) qs.set('q', q);
  try {
    const res = await fetch(`/api/poi/list?${qs.toString()}`);
    const data = await res.json();
    geoState.poiList = Array.isArray(data) ? data : [];
    geoState.poiFiltered = geoState.poiList.slice();
    geoEls.poiStatus.textContent = `${geoState.poiList.length} POI`;
    renderPoiList();
  } catch (err) {
    geoEls.poiStatus.textContent = 'Erro ao carregar POI';
    geoEls.poiList.innerHTML = '';
  }
};

const renderPoiDetail = () => {
  if (!geoEls.poiDetail) return;
  geoEls.poiDetail.innerHTML = '';
};

const selectPoi = async (poistamp) => {
  if (!poistamp) return;
  const res = await fetch(`/api/poi/${encodeURIComponent(poistamp)}`);
  const data = await res.json().catch(() => ({}));
  if (!res.ok || data.error) return showToast(data.error || 'Erro ao obter POI', 'danger');
  geoState.poiSelected = data.poi || null;
  renderPoiList();
  renderPoiDetail(data.poi, data.assoc || []);
  showPoiOnMap(data.poi || null);
};

const poiSearchModal = debounce(async () => {
  const q = (geoEls.poiModalSearch?.value || '').trim();
  if (!q) {
    if (geoEls.poiModalResults) geoEls.poiModalResults.innerHTML = '<div class="text-muted small">Pesquisa locais (OSM/Maps) por nome ou morada.</div>';
    return;
  }
  const res = await fetch(`/api/poi/search_places?q=${encodeURIComponent(q)}&limit=15`);
  const rows = await res.json().catch(() => []);
  if (!res.ok || rows?.error) {
    if (geoEls.poiModalResults) geoEls.poiModalResults.innerHTML = `<div class="text-danger small">${esc(rows?.error || 'Erro na pesquisa')}</div>`;
    return;
  }
  geoState.poiPlaceResults = Array.isArray(rows) ? rows : [];
  if (!geoEls.poiModalResults) return;
  geoEls.poiModalResults.innerHTML = (geoState.poiPlaceResults || []).map((r, idx) => `
    <div class="geo-poi-modal-row d-flex justify-content-between align-items-center">
      <div>
        <div class="fw-semibold small">${esc(r.name || '')}</div>
        <div class="text-muted" style="font-size:.75rem;">${esc(r.display_name || '')}</div>
      </div>
      <button class="btn btn-sm btn-outline-primary" data-sel-place="${idx}">Usar</button>
    </div>
  `).join('') || '<div class="text-muted small">Sem resultados.</div>';
  geoEls.poiModalResults.querySelectorAll('[data-sel-place]').forEach((b) => {
    b.addEventListener('click', () => {
      const idx = Number(b.getAttribute('data-sel-place') || -1);
      const place = geoState.poiPlaceResults[idx];
      if (!place) return;
      if (geoEls.poiCreateNome) geoEls.poiCreateNome.value = place.name || '';
      if (geoEls.poiCreateTipo) geoEls.poiCreateTipo.value = place.type || '';
      if (geoEls.poiCreateMorada) geoEls.poiCreateMorada.value = place.display_name || '';
      if (geoEls.poiCreateLat) geoEls.poiCreateLat.value = place.lat ?? '';
      if (geoEls.poiCreateLng) geoEls.poiCreateLng.value = place.lng ?? '';
      if (geoEls.poiCreateUrlMaps) geoEls.poiCreateUrlMaps.value = place.url_maps || '';
      poiSetStep('create');
    });
  });
}, 280);

const openPoiAssocStep = async (poistamp, rowsCache = null) => {
  geoState.poiModalSelectedStamp = poistamp;
  const list = Array.isArray(rowsCache) ? rowsCache : [];
  const picked = list.find(r => String(r.POISTAMP || '') === String(poistamp));
  if (geoEls.poiAssocName) geoEls.poiAssocName.textContent = picked?.NOME || poistamp;
  poiSetStep('assoc');
  if (geoEls.poiAssocList) geoEls.poiAssocList.innerHTML = '<div class="text-muted small">A carregar alojamentos pr?ximos...</div>';

  let assocSet = new Set();
  try {
    const detRes = await fetch(`/api/poi/${encodeURIComponent(poistamp)}`);
    const det = await detRes.json().catch(() => ({}));
    if (detRes.ok && !det.error && Array.isArray(det.assoc)) {
      assocSet = new Set(det.assoc.map(a => String(a.AL_NOME || '').trim().toLowerCase()).filter(Boolean));
    }
  } catch (_) {}

  const res = await fetch(`/api/poi/${encodeURIComponent(poistamp)}/nearby?limit=20`);
  const rows = await res.json().catch(() => []);
  if (!res.ok || rows.error) {
    if (geoEls.poiAssocList) geoEls.poiAssocList.innerHTML = `<div class="text-danger small">${esc(rows.error || 'Erro')}</div>`;
    return;
  }

  if (geoEls.poiAssocList) {
    geoEls.poiAssocList.innerHTML = rows.map(r => {
      const alNome = String(r.NOME || '').trim();
      const checked = assocSet.has(alNome.toLowerCase()) ? 'checked' : '';
      return `
      <label class="geo-poi-modal-row d-flex justify-content-between align-items-center">
        <div>
          <div class="fw-semibold small">${esc(alNome)}</div>
          <div class="text-muted" style="font-size:.75rem;">${Number(r.DIST_METROS || 0)} m</div>
        </div>
        <input class="form-check-input" type="checkbox" data-assoc-nome="${esc(alNome)}" data-assoc-dist="${Number(r.DIST_METROS || 0)}" ${checked}>
      </label>
    `;
    }).join('') || '<div class="text-muted small">Sem alojamentos com coordenadas.</div>';
  }
};

const openPoiModal = async () => {
  await loadPoiGroups();
  geoState.poiEditStamp = null;
  poiSetStep('search');
  geoState.poiModalSelectedStamp = null;
  geoState.poiPlaceResults = [];
  if (geoEls.poiModalSearch) geoEls.poiModalSearch.value = '';
  if (geoEls.poiModalResults) geoEls.poiModalResults.innerHTML = '<div class="text-muted small">Pesquisa locais (OSM/Maps) por nome ou morada.</div>';
  if (geoEls.poiAssocList) geoEls.poiAssocList.innerHTML = '';
  if (geoEls.poiCreateSave) geoEls.poiCreateSave.textContent = 'Criar POI';
  if (geoEls.poiCreateNome) geoEls.poiCreateNome.value = '';
  if (geoEls.poiCreateTipo) geoEls.poiCreateTipo.value = '';
  if (geoEls.poiCreateMorada) geoEls.poiCreateMorada.value = '';
  if (geoEls.poiCreateLat) geoEls.poiCreateLat.value = '';
  if (geoEls.poiCreateLng) geoEls.poiCreateLng.value = '';
  if (geoEls.poiCreateUrl) geoEls.poiCreateUrl.value = '';
  if (geoEls.poiCreateUrlMaps) geoEls.poiCreateUrlMaps.value = '';
  if (geoEls.poiCreateGrupo) geoEls.poiCreateGrupo.value = '';
  poiModal?.show();
};

const openPoiEditModal = async (poistamp) => {
  if (!poistamp) return;
  await loadPoiGroups();
  const res = await fetch(`/api/poi/${encodeURIComponent(poistamp)}`);
  const data = await res.json().catch(() => ({}));
  if (!res.ok || data.error) {
    showToast(data.error || 'Erro ao obter POI', 'danger');
    return;
  }
  const poi = data.poi || {};
  geoState.poiEditStamp = poistamp;
  if (geoEls.poiCreateNome) geoEls.poiCreateNome.value = poi.NOME || '';
  if (geoEls.poiCreateTipo) geoEls.poiCreateTipo.value = poi.TIPO || '';
  if (geoEls.poiCreateMorada) geoEls.poiCreateMorada.value = poi.MORADA || '';
  if (geoEls.poiCreateLat) geoEls.poiCreateLat.value = poi.LAT ?? '';
  if (geoEls.poiCreateLng) geoEls.poiCreateLng.value = poi.LNG ?? '';
  if (geoEls.poiCreateUrl) geoEls.poiCreateUrl.value = poi.URL || '';
  if (geoEls.poiCreateUrlMaps) geoEls.poiCreateUrlMaps.value = poi.URL_MAPS || '';
  if (geoEls.poiCreateGrupo) geoEls.poiCreateGrupo.value = poi.POIGSTAMP || '';
  if (geoEls.poiCreateSave) geoEls.poiCreateSave.textContent = 'Guardar alterações';
  poiSetStep('create');
  poiModal?.show();
};

const createPoiFromModal = async () => {
  const payload = {
    NOME: geoEls.poiCreateNome?.value || '',
    TIPO: geoEls.poiCreateTipo?.value || '',
    POIGSTAMP: geoEls.poiCreateGrupo?.value || '',
    LAT: geoEls.poiCreateLat?.value || '',
    LNG: geoEls.poiCreateLng?.value || '',
    MORADA: geoEls.poiCreateMorada?.value || '',
    URL: geoEls.poiCreateUrl?.value || '',
    URL_MAPS: geoEls.poiCreateUrlMaps?.value || ''
  };
  const editing = !!geoState.poiEditStamp;
  const url = editing ? `/api/poi/${encodeURIComponent(geoState.poiEditStamp)}` : '/api/poi';
  const res = await fetch(url, {
    method: editing ? 'PUT' : 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok || data.error) return showToast(data.error || (editing ? 'Erro ao atualizar POI' : 'Erro ao criar POI'), 'danger');
  const poiStamp = data.POISTAMP || geoState.poiEditStamp;
  showToast(editing ? 'POI atualizado' : 'POI criado');
  await loadPoiList();
  if (poiStamp) await selectPoi(poiStamp);
  if (editing) {
    geoState.poiEditStamp = null;
    if (geoEls.poiCreateSave) geoEls.poiCreateSave.textContent = 'Criar POI';
    poiModal?.hide();
    return;
  }
  openPoiAssocStep(poiStamp);
};

const confirmPoiAssociations = async () => {
  const poistamp = geoState.poiModalSelectedStamp;
  if (!poistamp) return;
  const picks = Array.from(geoEls.poiAssocList?.querySelectorAll('input[type="checkbox"][data-assoc-nome]:checked') || [])
    .map(i => ({ AL_NOME: i.getAttribute('data-assoc-nome') || '', DIST_METROS: Number(i.getAttribute('data-assoc-dist') || 0) }));
  if (!picks.length) return showToast('Seleciona pelo menos um alojamento.', 'warning');
  const res = await fetch(`/api/poi/${encodeURIComponent(poistamp)}/associacoes`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ alojamentos: picks })
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok || data.error) return showToast(data.error || 'Erro ao associar', 'danger');
  showToast(`Associações: ${data.inserted || 0} novas, ${data.updated || 0} atualizadas`);
  poiModal?.hide();
  loadPoiList();
  selectPoi(poistamp);
};

const renderPoigList = () => {
  if (!geoEls.poigList) return;
  const rows = geoState.poiGroups || [];
  geoEls.poigList.innerHTML = rows.map(g => `
    <div class="geo-poi-modal-row d-flex justify-content-between align-items-center">
      <div>
        <div class="fw-semibold small">${esc(g.NOME || '')} <span class="text-muted">(${esc(g.SLUG || '')})</span></div>
        <div class="text-muted" style="font-size:.75rem;">Ordem ${Number(g.ORDEM || 0)} · ${Number(g.ATIVO || 0) ? 'Ativo' : 'Inativo'}</div>
      </div>
      <div class="d-flex gap-1">
        <button class="btn btn-sm btn-outline-primary" data-poig-edit="${esc(g.POIGSTAMP)}">Editar</button>
        <button class="btn btn-sm btn-outline-danger" data-poig-del="${esc(g.POIGSTAMP)}">Apagar</button>
      </div>
    </div>
  `).join('') || '<div class="text-muted small">Sem grupos.</div>';
  geoEls.poigList.querySelectorAll('[data-poig-edit]').forEach((btn) => {
    btn.addEventListener('click', () => {
      const s = btn.getAttribute('data-poig-edit') || '';
      const g = rows.find(x => String(x.POIGSTAMP) === s);
      if (!g) return;
      geoEls.poigStamp.value = g.POIGSTAMP || '';
      geoEls.poigNome.value = g.NOME || '';
      geoEls.poigSlug.value = g.SLUG || '';
      geoEls.poigDescr.value = g.DESCR || '';
      geoEls.poigOrdem.value = Number(g.ORDEM || 0);
      geoEls.poigAtivo.checked = !!Number(g.ATIVO || 0);
    });
  });
  geoEls.poigList.querySelectorAll('[data-poig-del]').forEach((btn) => {
    btn.addEventListener('click', async () => {
      const s = btn.getAttribute('data-poig-del') || '';
      if (!confirm('Apagar grupo?')) return;
      const res = await fetch(`/api/poig/${encodeURIComponent(s)}`, { method: 'DELETE' });
      const data = await res.json().catch(() => ({}));
      if (!res.ok || data.error) return showToast(data.error || 'Erro ao apagar grupo', 'danger');
      showToast('Grupo apagado');
      await loadPoiGroups();
      renderPoigList();
    });
  });
};

const clearPoigForm = () => {
  if (!geoEls.poigStamp) return;
  geoEls.poigStamp.value = '';
  geoEls.poigNome.value = '';
  geoEls.poigSlug.value = '';
  geoEls.poigDescr.value = '';
  geoEls.poigOrdem.value = 0;
  geoEls.poigAtivo.checked = true;
};

const savePoig = async () => {
  const stamp = (geoEls.poigStamp?.value || '').trim();
  const payload = {
    NOME: geoEls.poigNome?.value || '',
    SLUG: geoEls.poigSlug?.value || '',
    DESCR: geoEls.poigDescr?.value || '',
    ORDEM: Number(geoEls.poigOrdem?.value || 0),
    ATIVO: !!geoEls.poigAtivo?.checked
  };
  const url = stamp ? `/api/poig/${encodeURIComponent(stamp)}` : '/api/poig';
  const method = stamp ? 'PUT' : 'POST';
  const res = await fetch(url, {
    method,
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok || data.error) return showToast(data.error || 'Erro ao guardar grupo', 'danger');
  showToast('Grupo guardado');
  clearPoigForm();
  await loadPoiGroups();
  renderPoigList();
};

const openPoigModal = async () => {
  await loadPoiGroups();
  renderPoigList();
  clearPoigForm();
  poigModal?.show();
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
  geoEls.toggleMetro?.addEventListener('click', toggleMetroLayer);

  geoEls.poiSearch?.addEventListener('input', debounce(loadPoiList, 250));
  geoEls.poiAddBtn?.addEventListener('click', openPoiModal);
  geoEls.poiGroupsBtn?.addEventListener('click', openPoigModal);
  geoEls.poiModalSearch?.addEventListener('input', poiSearchModal);
  geoEls.poiShowCreate?.addEventListener('click', () => poiSetStep('create'));
  geoEls.poiCreateCancel?.addEventListener('click', () => poiSetStep('search'));
  geoEls.poiCreateSave?.addEventListener('click', createPoiFromModal);
  geoEls.poiAssocBack?.addEventListener('click', () => poiSetStep('search'));
  geoEls.poiAssocConfirm?.addEventListener('click', confirmPoiAssociations);
  geoEls.poigSave?.addEventListener('click', savePoig);
  geoEls.poigClear?.addEventListener('click', clearPoigForm);
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
  setMetroButtonState();
  bindFormEvents();
  initRotas();
  loadPoiGroups().catch(() => {});
  loadPoiList().catch(() => {
    if (geoEls.poiStatus) geoEls.poiStatus.textContent = 'Erro ao carregar POI';
  });
  loadList().catch(() => {
    geoEls.status.textContent = 'Erro ao carregar.';
  });
});
