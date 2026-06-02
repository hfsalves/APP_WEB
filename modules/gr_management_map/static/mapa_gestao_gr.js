// modules/gr_management_map/static/mapa_gestao_gr.js

document.addEventListener('DOMContentLoaded', () => {
  const cfg = window.MAPA_GESTAO_GR || {};
  const dataInicioInput = document.getElementById('mapDataInicio');
  const dataFimInput = document.getElementById('mapDataFim');
  const btnOrigem = document.getElementById('mapBtnOrigem');
  const btnCcusto = document.getElementById('mapBtnCcusto');
  const btnAplicar = document.getElementById('mapBtnAplicar');
  const btnLimpar = document.getElementById('mapBtnLimpar');
  const btnExpandAll = document.getElementById('mapExpandAll');
  const btnCollapseAll = document.getElementById('mapCollapseAll');
  const btnAccess = document.getElementById('mapAccessBtn');
  const btnAccessSave = document.getElementById('mapAccessSave');
  const btnAccessClearAll = document.getElementById('mapAccessClearAll');
  const btnOrigemAll = document.getElementById('mapOrigemAll');
  const btnOrigemNone = document.getElementById('mapOrigemNone');
  const btnOrigemApply = document.getElementById('mapOrigemApply');
  const btnCcAll = document.getElementById('mapCcAll');
  const btnCcNone = document.getElementById('mapCcNone');
  const btnCcApply = document.getElementById('mapCcApply');
  const origemModalEl = document.getElementById('mapOrigemModal');
  const ccModalEl = document.getElementById('mapCcustoModal');
  const accessModalEl = document.getElementById('mapAccessModal');
  const accessList = document.getElementById('mapAccessList');
  const accessSearch = document.getElementById('mapAccessSearch');
  const accessStatus = document.getElementById('mapAccessStatus');
  const origemList = document.getElementById('mapOrigemList');
  const origemLabel = document.getElementById('mapOrigemLabel');
  const ccList = document.getElementById('mapCcList');
  const ccLabel = document.getElementById('mapCcustoLabel');
  const ccCount = document.getElementById('mapCcustoCount');
  const filtrosLbl = document.getElementById('mapFiltros');
  const tbody = document.getElementById('mapaBody');
  const totalLbl = document.getElementById('mapTotal');
  const loadingOverlay = document.getElementById('loadingOverlay');
  const loadingText = loadingOverlay ? loadingOverlay.querySelector('.loading-text') : null;
  const detailModalEl = document.getElementById('mapDetailModal');
  const detailBody = document.getElementById('mapDetailBody');
  const detailTitle = document.getElementById('mapDetailTitle');
  const detailTotal = document.getElementById('mapDetailTotal');
  const detailCount = document.getElementById('mapDetailCount');

  const fmtNum = new Intl.NumberFormat('pt-PT', {
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
    useGrouping: true
  });
  const fmtNum2 = new Intl.NumberFormat('pt-PT', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
    useGrouping: true
  });
  const fmtPct = new Intl.NumberFormat('pt-PT', { minimumFractionDigits: 0, maximumFractionDigits: 2 });
  const modalOrigem = origemModalEl && window.bootstrap ? new bootstrap.Modal(origemModalEl) : null;
  const modalCcusto = ccModalEl && window.bootstrap ? new bootstrap.Modal(ccModalEl) : null;
  const modalAccess = accessModalEl && window.bootstrap ? new bootstrap.Modal(accessModalEl) : null;
  const detailModal = detailModalEl && window.bootstrap ? new bootstrap.Modal(detailModalEl) : null;

  let ccOptions = [];
  let ccSelected = new Set();
  let origemOptions = [];
  let origemSelected = new Set();
  let accessUsers = [];
  let accessOrigins = [];
  let accessAssignments = new Map();
  let lastRows = [];
  let detailRows = [];
  let detailSort = { key: '', dir: 1 };
  let treeExpanded = new Set();
  let allRefs = [];
  let loadingCount = 0;
  const originalLoadingText = loadingText ? loadingText.textContent : '';
  const monthKeys = ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec'];

  function escapeHtml(value) {
    return String(value ?? '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  function attrEscape(value) {
    return escapeHtml(value);
  }

  function apiUrl(key, fallback) {
    return cfg[key] || fallback;
  }

  const fallbackI18n = {
    'mapa_gestao_gr.title': 'Mapa Gestao GR',
    'mapa_gestao_gr.subtitle': 'Analise central por familia e meses.',
    'mapa_gestao_gr.all_origins': 'Todas as origens',
    'mapa_gestao_gr.all_centers': 'Todos os centros',
    'mapa_gestao_gr.filters_all_origins': 'Todas as origens',
    'mapa_gestao_gr.costs': 'Custos',
    'mapa_gestao_gr.revenue': 'Proveitos',
    'mapa_gestao_gr.balance': 'Saldo',
    'mapa_gestao_gr.accumulated': 'Acumulado',
    'mapa_gestao_gr.no_access': 'Nao tem acesso ao Mapa Gestao GR.',
    'mapa_gestao_gr.loading': 'A carregar...',
    'mapa_gestao_gr.detail': 'Detalhe',
    'mapa_gestao_gr.detail_empty': 'Sem registos.',
    'mapa_gestao_gr.detail_loading': 'A carregar...',
    'mapa_gestao_gr.detail_records': '{count} registos',
    'mapa_gestao_gr.detail_total': 'Total',
    'mapa_gestao_gr.detail_error': 'Erro ao carregar detalhe'
  };

  function tr(key, vars) {
    if (typeof window.t === 'function') {
      const translated = window.t(key, vars);
      if (translated !== key) return translated;
    }
    const dict = window.SZ_I18N || {};
    let text = Object.prototype.hasOwnProperty.call(dict, key) ? dict[key] : (fallbackI18n[key] || key);
    if (text === key && fallbackI18n[key]) text = fallbackI18n[key];
    if (!vars) return text;
    return String(text).replace(/\{([A-Za-z0-9_]+)\}/g, (match, name) => (
      Object.prototype.hasOwnProperty.call(vars, name) ? String(vars[name]) : match
    ));
  }

  function setBusy(isBusy) {
    loadingCount = Math.max(0, loadingCount + (isBusy ? 1 : -1));
    const active = loadingCount > 0;
    if (loadingOverlay) {
      if (active) {
        if (loadingText) loadingText.textContent = tr('mapa_gestao_gr.loading');
        loadingOverlay.style.display = 'flex';
        loadingOverlay.setAttribute('aria-hidden', 'false');
        requestAnimationFrame(() => {
          loadingOverlay.style.opacity = '1';
        });
      } else {
        loadingOverlay.style.opacity = '0';
        loadingOverlay.setAttribute('aria-hidden', 'true');
        window.setTimeout(() => {
          if (loadingCount === 0) {
            loadingOverlay.style.display = 'none';
            if (loadingText) loadingText.textContent = originalLoadingText;
          }
        }, 250);
      }
    }
    [btnAplicar, btnLimpar, btnOrigem, btnCcusto, btnExpandAll, btnCollapseAll, btnAccess, btnAccessSave].forEach((btn) => {
      if (btn) btn.disabled = active;
    });
  }

  async function withBusy(task) {
    setBusy(true);
    try {
      return await task();
    } finally {
      setBusy(false);
    }
  }

  async function fetchJson(url, options = {}) {
    const headers = { Accept: 'application/json', ...(options.headers || {}) };
    const res = await fetch(url, { ...options, headers });
    const text = await res.text();
    let data = null;
    try {
      data = text ? JSON.parse(text) : {};
    } catch (err) {
      const preview = text.replace(/\s+/g, ' ').trim().slice(0, 160);
      throw new Error(
        res.status === 404
          ? `Endpoint nao encontrado: ${url}`
          : `Resposta inesperada do servidor (${res.status || 'sem status'}): ${preview || 'sem conteudo'}`
      );
    }
    if (!res.ok || data.error) {
      throw new Error(data.error || `Erro HTTP ${res.status}`);
    }
    return data;
  }

  function isRevenueRef(ref) {
    const clean = String(ref || '').trim();
    return clean === '7' || clean.startsWith('7.');
  }

  function getDateFilters() {
    return {
      data_inicio: dataInicioInput?.value || cfg.dataInicioDefault || `${cfg.anoPadrao || new Date().getFullYear()}-01-01`,
      data_fim: dataFimInput?.value || cfg.dataFimDefault || `${cfg.anoPadrao || new Date().getFullYear()}-12-31`,
    };
  }

  function getSelectedOrigens() {
    return Array.from(origemSelected).filter(Boolean);
  }

  function isAllOriginsSelected() {
    return origemOptions.length > 0 && origemSelected.size >= origemOptions.length;
  }

  function getSelectedCcustos() {
    return Array.from(ccSelected).filter(Boolean);
  }

  function isAllCentersSelected() {
    return ccOptions.length > 0 && ccSelected.size >= ccOptions.length;
  }

  function buildFilterParams({ includeOrigens = true, includeCcustos = true } = {}) {
    const dates = getDateFilters();
    const qs = new URLSearchParams(dates);
    const origens = getSelectedOrigens();
    if (includeOrigens && origens.length && !isAllOriginsSelected()) qs.set('origens', origens.join(','));
    if (includeCcustos) {
      const ccustos = getSelectedCcustos();
      if (ccustos.length && !isAllCentersSelected()) qs.set('ccustos', ccustos.join(','));
    }
    return qs;
  }

  function setLoading(message) {
    if (tbody) {
      tbody.innerHTML = `<tr><td colspan="15" class="sz_table_cell sz_text_muted text-center">${escapeHtml(message)}</td></tr>`;
    }
  }

  function setNoAccess(message = tr('mapa_gestao_gr.no_access')) {
    lastRows = [];
    allRefs = [];
    treeExpanded = new Set();
    if (tbody) {
      tbody.innerHTML = `<tr><td colspan="15" class="sz_table_cell sz_text_muted text-center">${escapeHtml(message)}</td></tr>`;
    }
    if (totalLbl) totalLbl.textContent = message;
    if (filtrosLbl) filtrosLbl.textContent = '';
  }

  function updateCcLabel() {
    const total = ccOptions.length;
    const selected = ccSelected.size;
    if (ccLabel) {
      if (!total || selected === total) ccLabel.textContent = tr('mapa_gestao_gr.all_centers');
      else if (!selected) ccLabel.textContent = tr('mapa_gestao_gr.no_center');
      else ccLabel.textContent = tr('mapa_gestao_gr.centers_count', { selected, total });
    }
    if (ccCount) {
      ccCount.textContent = total ? tr('mapa_gestao_gr.centers_available', { selected, total }) : tr('mapa_gestao_gr.no_centers_filters');
    }
  }

  function updateOrigemLabel() {
    const total = origemOptions.length;
    const selected = origemSelected.size;
    if (!origemLabel) return;
    if (!total || selected === total) origemLabel.textContent = tr('mapa_gestao_gr.all_origins');
    else if (!selected) origemLabel.textContent = tr('mapa_gestao_gr.no_origin');
    else origemLabel.textContent = tr('mapa_gestao_gr.origins_count', { selected, total });
  }

  function renderOrigemList() {
    if (!origemList) return;
    if (!origemOptions.length) {
      origemList.innerHTML = `<tr><td colspan="2" class="sz_table_cell sz_text_muted text-center">${escapeHtml(tr('mapa_gestao_gr.origins_empty'))}</td></tr>`;
      updateOrigemLabel();
      return;
    }
    origemList.innerHTML = origemOptions.map((origem) => {
      const checked = origemSelected.has(origem) ? ' checked' : '';
      return `
        <tr>
          <td class="text-center"><input type="checkbox" class="form-check-input map-origin-check" value="${attrEscape(origem)}"${checked}></td>
          <td><span class="sz_management_map_origin_name">${escapeHtml(origem)}</span></td>
        </tr>
      `;
    }).join('');
    origemList.querySelectorAll('.map-origin-check').forEach((input) => {
      input.addEventListener('change', () => {
        const value = input.value;
        if (input.checked) origemSelected.add(value);
        else origemSelected.delete(value);
        updateOrigemLabel();
      });
    });
    updateOrigemLabel();
  }

  function renderCcList() {
    if (!ccList) return;
    if (!ccOptions.length) {
      ccList.innerHTML = `<tr><td colspan="3" class="sz_table_cell sz_text_muted text-center">${escapeHtml(tr('mapa_gestao_gr.no_centers_filters'))}</td></tr>`;
      updateCcLabel();
      return;
    }
    ccList.innerHTML = ccOptions.map((option) => {
      const ccusto = String(option.ccusto || '').trim();
      const checked = ccSelected.has(ccusto) ? ' checked' : '';
      return `
        <tr>
          <td class="text-center"><input type="checkbox" class="form-check-input map-cc-check" value="${attrEscape(ccusto)}"${checked}></td>
          <td><span class="sz_management_map_cc_name">${escapeHtml(ccusto)}</span></td>
          <td class="text-end"><span class="badge rounded-pill text-bg-light">${escapeHtml(option.tipo || '')}</span></td>
        </tr>
      `;
    }).join('');
    ccList.querySelectorAll('.map-cc-check').forEach((input) => {
      input.addEventListener('change', () => {
        const value = input.value;
        if (input.checked) ccSelected.add(value);
        else ccSelected.delete(value);
        updateCcLabel();
      });
    });
    updateCcLabel();
  }

  function renderAccessList() {
    if (!accessList) return;
    const term = String(accessSearch?.value || '').trim().toLowerCase();
    const users = accessUsers.filter((user) => {
      if (!term) return true;
      return `${user.login || ''} ${user.nome || ''}`.toLowerCase().includes(term);
    });
    if (!users.length) {
      accessList.innerHTML = `<tr><td colspan="2" class="sz_table_cell sz_text_muted text-center">${escapeHtml(tr('mapa_gestao_gr.users_empty'))}</td></tr>`;
      return;
    }
    if (!accessOrigins.length) {
      accessList.innerHTML = `<tr><td colspan="2" class="sz_table_cell sz_text_muted text-center">${escapeHtml(tr('mapa_gestao_gr.origins_empty'))}</td></tr>`;
      return;
    }
    accessList.innerHTML = users.map((user) => {
      const usstamp = String(user.usstamp || '').trim();
      const selected = accessAssignments.get(usstamp) || new Set();
      const adminBadge = user.admin ? `<small>${escapeHtml(tr('mapa_gestao_gr.admin_full_access'))}</small>` : '';
      const originsHtml = accessOrigins.map((origin) => {
        const checked = selected.has(origin) ? ' checked' : '';
        return `
          <label class="sz_management_map_access_origin" title="${attrEscape(origin)}">
            <input type="checkbox" class="map-access-origin-check" data-usstamp="${attrEscape(usstamp)}" value="${attrEscape(origin)}"${checked}>
            <span>${escapeHtml(origin)}</span>
          </label>
        `;
      }).join('');
      return `
        <tr class="map-access-row" data-user-text="${attrEscape(`${user.login || ''} ${user.nome || ''}`.toLowerCase())}">
          <td>
            <div class="sz_management_map_access_user">
              ${escapeHtml(user.login || '')}
              <small>${escapeHtml(user.nome || '')}</small>
              ${adminBadge}
            </div>
          </td>
          <td><div class="sz_management_map_access_origins">${originsHtml}</div></td>
        </tr>
      `;
    }).join('');
  }

  async function loadAccessConfig() {
    if (!accessList) return;
    if (accessStatus) accessStatus.textContent = '';
    accessList.innerHTML = `<tr><td colspan="2" class="sz_table_cell sz_text_muted text-center">${escapeHtml(tr('mapa_gestao_gr.loading'))}</td></tr>`;
    const data = await fetchJson(apiUrl('acessosUrl', '/api/mapa_gestao_gr/acessos'));
    accessUsers = Array.isArray(data.users) ? data.users : [];
    accessOrigins = Array.isArray(data.origens) ? data.origens.filter(Boolean) : [];
    accessAssignments = new Map();
    (Array.isArray(data.assignments) ? data.assignments : []).forEach((item) => {
      const usstamp = String(item.usstamp || '').trim();
      const origem = String(item.origem || '').trim();
      if (!usstamp || !origem) return;
      if (!accessAssignments.has(usstamp)) accessAssignments.set(usstamp, new Set());
      accessAssignments.get(usstamp).add(origem);
    });
    renderAccessList();
  }

  function collectAccessPayload() {
    return accessUsers.map((user) => {
      const usstamp = String(user.usstamp || '').trim();
      const selected = accessAssignments.get(usstamp) || new Set();
      return { usstamp, origens: Array.from(selected) };
    }).filter((item) => item.usstamp);
  }

  async function saveAccessConfig() {
    const payload = { access: collectAccessPayload() };
    const data = await fetchJson(apiUrl('acessosUrl', '/api/mapa_gestao_gr/acessos'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    if (accessStatus) accessStatus.textContent = tr('mapa_gestao_gr.accesses_saved', { count: Number(data.saved || 0) });
    await loadAccessConfig();
    await refreshFilterOptions({ keepSelection: true });
    await loadMapa();
  }

  async function loadOrigens() {
    if (cfg.hasMapAccess === false) {
      origemOptions = [];
      origemSelected = new Set();
      if (origemLabel) origemLabel.textContent = tr('mapa_gestao_gr.no_access');
      renderOrigemList();
      return;
    }
    const qs = buildFilterParams({ includeOrigens: false, includeCcustos: true });
    const previous = new Set(origemSelected);
    const data = await fetchJson(`${apiUrl('origensUrl', '/api/mapa_gestao_gr/origens')}?${qs.toString()}`);
    if (data.has_access === false) {
      cfg.hasMapAccess = false;
      origemOptions = [];
      origemSelected = new Set();
      if (origemLabel) origemLabel.textContent = tr('mapa_gestao_gr.no_access');
      renderOrigemList();
      return;
    }
    origemOptions = Array.isArray(data.options)
      ? data.options.map((item) => String(item || '').trim()).filter(Boolean)
      : [];
    const available = new Set(origemOptions);
    origemSelected = previous.size
      ? new Set(Array.from(previous).filter((origem) => available.has(origem)))
      : new Set(Array.from(available));
    if (!origemSelected.size && available.size) origemSelected = new Set(Array.from(available));
    renderOrigemList();
  }

  async function loadCcustos({ keepSelection = true } = {}) {
    if (cfg.hasMapAccess === false) {
      ccOptions = [];
      ccSelected = new Set();
      renderCcList();
      return;
    }
    const previous = new Set(ccSelected);
    const qs = buildFilterParams({ includeCcustos: false });
    const data = await fetchJson(`${apiUrl('ccustosUrl', '/api/mapa_gestao_gr/ccustos')}?${qs.toString()}`);
    if (data.has_access === false) {
      cfg.hasMapAccess = false;
      ccOptions = [];
      ccSelected = new Set();
      renderCcList();
      return;
    }
    const raw = Array.isArray(data.options) ? data.options : [];
    const byCc = new Map();
    raw.forEach((item) => {
      const ccusto = String((item && item.ccusto) || item || '').trim();
      if (ccusto && !byCc.has(ccusto)) byCc.set(ccusto, { ccusto, tipo: (item && item.tipo) || '' });
    });
    ccOptions = Array.from(byCc.values());
    const available = new Set(ccOptions.map((item) => item.ccusto));
    if (keepSelection && previous.size) {
      ccSelected = new Set(Array.from(previous).filter((ccusto) => available.has(ccusto)));
    } else {
      ccSelected = new Set(Array.from(available));
    }
    if (!ccSelected.size && available.size) ccSelected = new Set(Array.from(available));
    renderCcList();
  }

  async function loadMapa() {
    setLoading(tr('mapa_gestao_gr.loading'));
    const qs = buildFilterParams({ includeCcustos: true });
    try {
      const data = await fetchJson(`${apiUrl('baseUrl', '/api/mapa_gestao_gr')}?${qs.toString()}`);
      if (data.has_access === false) {
        cfg.hasMapAccess = false;
        setNoAccess(tr('mapa_gestao_gr.no_access'));
        return;
      }
      cfg.hasMapAccess = true;
      lastRows = Array.isArray(data.familias) ? data.familias.map((row) => {
        const meses = Array.isArray(row.meses) ? row.meses.slice(0, 12) : [];
        while (meses.length < 12) meses.push(0);
        return { ...row, meses };
      }) : [];
      allRefs = lastRows.map((row) => String(row.ref || '').trim()).filter(Boolean);
      treeExpanded = new Set();
      renderTabela();
      updateHeader(data);
    } catch (err) {
      console.error(err);
      setLoading(err.message || tr('common.error'));
      if (totalLbl) totalLbl.textContent = '--';
      if (filtrosLbl) filtrosLbl.textContent = '';
    }
  }

  function updateHeader(data) {
    if (totalLbl) totalLbl.textContent = tr('mapa_gestao_gr.subtitle');
    if (filtrosLbl) {
      const origem = isAllOriginsSelected()
        ? tr('mapa_gestao_gr.filters_all_origins')
        : (getSelectedOrigens().length
          ? tr('mapa_gestao_gr.origins_count', { selected: getSelectedOrigens().length, total: origemOptions.length || getSelectedOrigens().length })
          : tr('mapa_gestao_gr.filters_no_origins'));
      const ccustos = getSelectedCcustos();
      const centersLabel = isAllCentersSelected()
        ? tr('mapa_gestao_gr.all_centers')
        : (ccustos.length
          ? tr('mapa_gestao_gr.centers_count', { selected: ccustos.length, total: ccOptions.length || ccustos.length })
          : tr('mapa_gestao_gr.no_center'));
      filtrosLbl.textContent = `${getDateFilters().data_inicio} a ${getDateFilters().data_fim} | ${origem} | ${centersLabel}`;
    }
  }

  function monthLabel(month) {
    const idx = Number(month || 0) - 1;
    if (idx < 0 || idx > 11) return '';
    return tr(`mapa_gestao_gr.month_${monthKeys[idx]}`);
  }

  function detailSortValue(row, key) {
    if (!row || !key) return '';
    if (['quantidade', 'preco', 'total'].includes(key)) {
      const value = Number(row[key] || 0);
      return Number.isFinite(value) ? value : 0;
    }
    if (key === 'data') {
      const value = Date.parse(String(row.data || '').slice(0, 10));
      return Number.isFinite(value) ? value : 0;
    }
    return String(row[key] == null ? '' : row[key]).trim();
  }

  function compareDetailRows(a, b) {
    const key = detailSort.key;
    if (!key) return 0;
    const av = detailSortValue(a, key);
    const bv = detailSortValue(b, key);
    let result = 0;
    if (typeof av === 'number' && typeof bv === 'number') {
      result = av - bv;
    } else {
      result = String(av).localeCompare(String(bv), 'pt-PT', {
        numeric: true,
        sensitivity: 'base'
      });
    }
    return result * detailSort.dir;
  }

  function updateDetailSortIndicators() {
    document.querySelectorAll('#mapDetailTable .map-detail-sort').forEach((th) => {
      const indicator = th.querySelector('.sort-ind');
      if (!indicator) return;
      indicator.textContent = th.dataset.key === detailSort.key
        ? (detailSort.dir > 0 ? '▲' : '▼')
        : '';
    });
  }

  function renderDetailRows() {
    if (!detailBody) return;
    const rows = detailSort.key ? [...detailRows].sort(compareDetailRows) : [...detailRows];
    if (detailCount) detailCount.textContent = tr('mapa_gestao_gr.detail_records', { count: detailRows.length });
    if (!rows.length) {
      detailBody.innerHTML = `<tr><td colspan="12" class="text-center text-muted">${escapeHtml(tr('mapa_gestao_gr.detail_empty'))}</td></tr>`;
      updateDetailSortIndicators();
      return;
    }
    detailBody.innerHTML = rows.map((row) => `
      <tr>
        <td>${escapeHtml(row.origem || '')}</td>
        <td>${escapeHtml(row.documento || '')}</td>
        <td>${escapeHtml(row.numero || '')}</td>
        <td>${escapeHtml(row.data || '')}</td>
        <td>${escapeHtml(row.nome || '')}</td>
        <td>${escapeHtml(row.ccusto || '')}</td>
        <td>${escapeHtml(row.familia || '')}</td>
        <td>${escapeHtml(row.referencia || '')}</td>
        <td>${escapeHtml(row.designacao || '')}</td>
        <td class="text-end">${fmtNum2.format(Number(row.quantidade || 0))}</td>
        <td class="text-end">${fmtNum2.format(Number(row.preco || 0))}</td>
        <td class="text-end fw-semibold">${fmtNum2.format(Number(row.total || 0))}</td>
      </tr>
    `).join('');
    updateDetailSortIndicators();
  }

  async function openDetalhe(ref, mes, nome, level) {
    if (!detailBody || !detailModal) return;
    const qs = buildFilterParams({ includeCcustos: true });
    qs.set('familia', ref);
    if (mes && mes !== 'all') qs.set('mes', mes);
    if (Number(level || 1) <= 2) qs.set('include_children', '1');

    detailBody.innerHTML = `<tr><td colspan="12" class="text-center text-muted">${escapeHtml(tr('mapa_gestao_gr.detail_loading'))}</td></tr>`;
    detailRows = [];
    detailSort = { key: '', dir: 1 };
    if (detailCount) detailCount.textContent = tr('mapa_gestao_gr.detail_records', { count: 0 });
    updateDetailSortIndicators();
    const mesText = mes && mes !== 'all' ? `(${monthLabel(mes)})` : '';
    if (detailTitle) detailTitle.textContent = `${tr('mapa_gestao_gr.detail')} ${ref} ${nome ? '- ' + nome : ''} ${mesText}`.trim();
    if (detailTotal) detailTotal.textContent = `${tr('mapa_gestao_gr.detail_total')}: --`;
    detailModal.show();

    try {
      const data = await fetchJson(`${apiUrl('detalheUrl', '/api/mapa_gestao_gr/detalhe')}?${qs.toString()}`);
      if (data.has_access === false) {
        detailBody.innerHTML = `<tr><td colspan="12" class="text-center text-muted">${escapeHtml(tr('mapa_gestao_gr.no_access'))}</td></tr>`;
        return;
      }
      detailRows = Array.isArray(data.rows) ? data.rows : [];
      renderDetailRows();
      if (detailTotal) detailTotal.innerHTML = `<span class="sz_management_map_detail_metric"><strong>${escapeHtml(tr('mapa_gestao_gr.detail_total'))}:</strong> ${fmtNum2.format(Number(data.total || 0))}</span>`;
    } catch (err) {
      console.error(err);
      detailBody.innerHTML = `<tr><td colspan="12" class="text-center text-danger">${escapeHtml(err.message || tr('mapa_gestao_gr.detail_error'))}</td></tr>`;
      if (detailTotal) detailTotal.textContent = `${tr('mapa_gestao_gr.detail_total')}: --`;
    }
  }

  function renderTabela() {
    if (!tbody) return;
    if (!lastRows.length) {
      tbody.innerHTML = `<tr><td colspan="15" class="text-center text-muted">${escapeHtml(tr('mapa_gestao_gr.no_data_filters'))}</td></tr>`;
      return;
    }
    const hasChild = {};
    lastRows.forEach((row) => {
      const parts = String(row.ref || '').split('.');
      if (parts.length > 1) hasChild[parts.slice(0, -1).join('.')] = true;
    });
    const isVisible = (ref) => {
      const parts = String(ref || '').split('.');
      if (parts.length === 1) return true;
      for (let idx = 1; idx < parts.length; idx += 1) {
        if (!treeExpanded.has(parts.slice(0, idx).join('.'))) return false;
      }
      return true;
    };
    const baseForPct = lastRows
      .filter((row) => Number(row.nivel || 1) === 1 && !isRevenueRef(row.ref))
      .reduce((acc, row) => acc + Number(row.total || 0), 0);

    const rowsHtml = lastRows
      .filter((row) => isVisible(row.ref))
      .map((row) => {
        const nivel = Number(row.nivel || 1);
        const ref = String(row.ref || '');
        const total = Number(row.total || 0);
        const isRevenue = isRevenueRef(ref);
        const percent = isRevenue ? '' : (baseForPct ? `${fmtPct.format((total / baseForPct) * 100)}%` : '');
        const toggle = hasChild[ref]
          ? `<button class="toggle-node" data-ref="${attrEscape(ref)}" title="${treeExpanded.has(ref) ? attrEscape(tr('mapa_gestao_gr.collapse_all')) : attrEscape(tr('mapa_gestao_gr.expand_all'))}"><i class="fa-solid ${treeExpanded.has(ref) ? 'fa-minus' : 'fa-plus'}"></i></button>`
          : '<span class="toggle-spacer"></span>';
        const nome = String(row.nome || ref);
        const meses = row.meses.map((value, idx) => `
          <td class="text-end cell-drill"
              data-ref="${attrEscape(ref)}"
              data-nome="${attrEscape(nome)}"
              data-mes="${idx + 1}"
              data-level="${nivel}">
            ${fmtNum.format(Number(value || 0))}
          </td>
        `).join('');
        return `
          <tr class="mapa-row level-${nivel}${isRevenue ? ' row-proveito' : ''}" data-level="${nivel}">
            <td class="fam-cell level-${nivel} d-flex align-items-center gap-1">${toggle}<span>${escapeHtml(ref)} - ${escapeHtml(nome)}</span></td>
            ${meses}
            <td class="text-end fw-semibold cell-drill"
                data-ref="${attrEscape(ref)}"
                data-nome="${attrEscape(nome)}"
                data-mes="all"
                data-level="${nivel}">
              ${fmtNum.format(total)}
            </td>
            <td class="text-end text-muted">${percent}</td>
          </tr>
        `;
      }).join('');

    const custoMeses = Array(12).fill(0);
    const provMeses = Array(12).fill(0);
    let totalCustos = 0;
    let totalProv = 0;
    lastRows.filter((row) => Number(row.nivel || 1) === 1).forEach((row) => {
      const ref = String(row.ref || '').trim();
      const arr = Array.isArray(row.meses) ? row.meses : [];
      arr.forEach((value, idx) => {
        if (idx < 0 || idx > 11) return;
        if (isRevenueRef(ref)) provMeses[idx] += Number(value || 0);
        else custoMeses[idx] += Number(value || 0);
      });
      if (isRevenueRef(ref)) totalProv += Number(row.total || 0);
      else totalCustos += Number(row.total || 0);
    });

    const saldoMeses = custoMeses.map((cost, idx) => Number(provMeses[idx] || 0) - Number(cost || 0));
    const totalSaldo = totalProv - totalCustos;
    let acumuladoTotal = 0;
    const acumuladoMeses = saldoMeses.map((value) => {
      acumuladoTotal += Number(value || 0);
      return acumuladoTotal;
    });
    const rowResumo = (label, arr, total, extraClass = '') => `
      <tr class="mapa-row total-row ${extraClass}">
        <td class="fam-cell level-1 d-flex align-items-center gap-1"><span class="fw-semibold">${escapeHtml(label)}</span></td>
        ${arr.map((value) => `<td class="text-end fw-semibold">${fmtNum.format(Number(value || 0))}</td>`).join('')}
        <td class="text-end fw-semibold">${fmtNum.format(Number(total || 0))}</td>
        <td class="text-end text-muted fw-semibold"></td>
      </tr>
    `;
    const totalRowHtml = [
      rowResumo(tr('mapa_gestao_gr.costs'), custoMeses, totalCustos, 'total-custos'),
      rowResumo(tr('mapa_gestao_gr.revenue'), provMeses, totalProv, 'total-proveitos'),
      rowResumo(tr('mapa_gestao_gr.balance'), saldoMeses, totalSaldo, 'total-saldo'),
      rowResumo(tr('mapa_gestao_gr.accumulated'), acumuladoMeses, acumuladoTotal, 'total-acumulado')
    ].join('');

    tbody.innerHTML = rowsHtml
      ? rowsHtml + totalRowHtml
      : `<tr><td colspan="15" class="text-center text-muted">${escapeHtml(tr('mapa_gestao_gr.no_visible_data'))}</td></tr>`;
  }

  async function refreshFilterOptions({ keepSelection = true } = {}) {
    try {
      await loadOrigens();
      await loadCcustos({ keepSelection });
    } catch (err) {
      console.error(err);
      if (ccList) ccList.innerHTML = `<tr><td colspan="3" class="text-center text-danger">${escapeHtml(err.message || tr('common.error'))}</td></tr>`;
      updateCcLabel();
    }
  }

  btnCcusto?.addEventListener('click', () => modalCcusto?.show());
  btnOrigem?.addEventListener('click', async () => {
    modalOrigem?.show();
    await withBusy(loadOrigens);
  });
  btnOrigemAll?.addEventListener('click', () => {
    origemSelected = new Set(origemOptions);
    renderOrigemList();
  });
  btnOrigemNone?.addEventListener('click', () => {
    origemSelected = new Set();
    renderOrigemList();
  });
  btnOrigemApply?.addEventListener('click', async () => {
    modalOrigem?.hide();
    await withBusy(async () => {
      await loadCcustos({ keepSelection: false });
    });
  });
  btnAccess?.addEventListener('click', async () => {
    modalAccess?.show();
    await withBusy(loadAccessConfig);
  });
  accessSearch?.addEventListener('input', renderAccessList);
  accessList?.addEventListener('change', (event) => {
    const input = event.target.closest('.map-access-origin-check');
    if (!input) return;
    const usstamp = String(input.dataset.usstamp || '').trim();
    const origem = String(input.value || '').trim();
    if (!usstamp || !origem) return;
    if (!accessAssignments.has(usstamp)) accessAssignments.set(usstamp, new Set());
    if (input.checked) accessAssignments.get(usstamp).add(origem);
    else accessAssignments.get(usstamp).delete(origem);
    if (accessStatus) accessStatus.textContent = tr('mapa_gestao_gr.accesses_unsaved');
  });
  btnAccessClearAll?.addEventListener('click', () => {
    accessAssignments = new Map();
    renderAccessList();
    if (accessStatus) accessStatus.textContent = tr('mapa_gestao_gr.accesses_unsaved');
  });
  btnAccessSave?.addEventListener('click', async () => {
    await withBusy(saveAccessConfig);
  });
  btnCcAll?.addEventListener('click', () => {
    ccSelected = new Set(ccOptions.map((option) => option.ccusto));
    renderCcList();
  });
  btnCcNone?.addEventListener('click', () => {
    ccSelected = new Set();
    renderCcList();
  });
  btnCcApply?.addEventListener('click', () => {
    modalCcusto?.hide();
    withBusy(loadMapa);
  });
  btnAplicar?.addEventListener('click', async () => {
    await withBusy(async () => {
      await refreshFilterOptions({ keepSelection: true });
      await loadMapa();
    });
  });
  btnLimpar?.addEventListener('click', async () => {
    await withBusy(async () => {
      const year = cfg.anoPadrao || new Date().getFullYear();
      if (dataInicioInput) dataInicioInput.value = cfg.dataInicioDefault || `${year}-01-01`;
      if (dataFimInput) dataFimInput.value = cfg.dataFimDefault || `${year}-12-31`;
      await refreshFilterOptions({ keepSelection: false });
      await loadMapa();
    });
  });
  btnExpandAll?.addEventListener('click', () => {
    treeExpanded = new Set(allRefs);
    renderTabela();
  });
  btnCollapseAll?.addEventListener('click', () => {
    treeExpanded = new Set();
    renderTabela();
  });
  tbody?.addEventListener('click', (event) => {
    const btn = event.target.closest('.toggle-node');
    if (btn) {
      const ref = btn.dataset.ref || '';
      if (treeExpanded.has(ref)) treeExpanded.delete(ref);
      else treeExpanded.add(ref);
      renderTabela();
      return;
    }
    const cell = event.target.closest('.cell-drill');
    if (!cell) return;
    openDetalhe(
      cell.dataset.ref || '',
      cell.dataset.mes || '',
      cell.dataset.nome || '',
      Number(cell.dataset.level || '1')
    );
  });
  document.querySelectorAll('#mapDetailTable .map-detail-sort').forEach((th) => {
    th.addEventListener('click', () => {
      const key = th.dataset.key || '';
      if (!key || !detailRows.length) return;
      if (detailSort.key === key) {
        detailSort.dir *= -1;
      } else {
        detailSort = { key, dir: 1 };
      }
      renderDetailRows();
    });
  });

  withBusy(async () => {
    await refreshFilterOptions({ keepSelection: false });
    await loadMapa();
  });
});
