(function () {
  const currentEntity = window.FTS_CURRENT_ENTITY || {};
  const state = {
    rows: [],
    currentStamp: String(window.FTS_INITIAL_STAMP || '').trim(),
    current: null,
    currentFtsx: null,
    searchTimer: null,
  };

  const permissions = {
    create: !!window.FTS_CAN_CREATE,
    edit: !!window.FTS_CAN_EDIT,
  };

  const els = {
    list: document.getElementById('ftsList'),
    listSummary: document.getElementById('ftsListSummary'),
    editorTitle: document.getElementById('ftsEditorTitle'),
    statTotal: document.getElementById('ftsStatTotal'),
    statWithFtsx: document.getElementById('ftsStatWithFtsx'),
    statActive: document.getElementById('ftsStatActive'),
    btnNewTop: document.getElementById('ftsBtnNewTop'),
    btnCancel: document.getElementById('ftsBtnCancel'),
    btnSaveBottom: document.getElementById('ftsBtnSaveBottom'),
    btnCreateFtsx: document.getElementById('ftsCreateFtsxBtn'),
    ftsxStatusBadge: document.getElementById('ftsxStatusBadge'),
    ftsxMissingNote: document.getElementById('ftsxMissingNote'),
    ftsxFormWrap: document.getElementById('ftsxFormWrap'),
    ftsxLastHash: document.getElementById('ftsxLAST_HASH'),
    ftsxLastHashCopy: document.getElementById('ftsxLAST_HASH_COPY'),
    filters: {
      serie: document.getElementById('ftsFilterSerie'),
      ano: document.getElementById('ftsFilterAno'),
      ndoc: document.getElementById('ftsFilterNdoc'),
      ativa: document.getElementById('ftsFilterAtiva'),
      tiposaft: document.getElementById('ftsFilterTipoSaft'),
      ftsx: document.getElementById('ftsFilterFtsx'),
    },
    fields: {
      fts: {
        FTSSTAMP: document.getElementById('ftsFTSSTAMP'),
        FESTAMP: document.getElementById('ftsFESTAMP'),
        FEID: document.getElementById('ftsFEID'),
        ANO: document.getElementById('ftsANO'),
        NDOC: document.getElementById('ftsNDOC'),
        SERIE: document.getElementById('ftsSERIE'),
        DESCR: document.getElementById('ftsDESCR'),
        TIPOSAFT: document.getElementById('ftsTIPOSAFT'),
        ESTADO: document.getElementById('ftsESTADO'),
        ULTIMO_FNO: document.getElementById('ftsULTIMO_FNO'),
        ATIVA: document.getElementById('ftsATIVA'),
        NO_SAFT: document.getElementById('ftsNO_SAFT'),
        DTCriacao: document.getElementById('ftsDTCriacao'),
        DTAlteracao: document.getElementById('ftsDTAlteracao'),
        USERCRIACAO: document.getElementById('ftsUSERCRIACAO'),
        USERALTERACAO: document.getElementById('ftsUSERALTERACAO'),
      },
      ftsx: {
        FTSXSTAMP: document.getElementById('ftsxFTSXSTAMP'),
        FTSSTAMP: document.getElementById('ftsxFTSSTAMP'),
        FEID: document.getElementById('ftsxFEID'),
        HASHVER: document.getElementById('ftsxHASHVER'),
        COD_VALIDACAO_SERIE: document.getElementById('ftsxCOD_VALIDACAO_SERIE'),
        ATCUD_PREFIX: document.getElementById('ftsxATCUD_PREFIX'),
        AT_SERIE_ESTADO: document.getElementById('ftsxAT_SERIE_ESTADO'),
        AT_SERIE_DATA: document.getElementById('ftsxAT_SERIE_DATA'),
        AT_SERIE_MSG: document.getElementById('ftsxAT_SERIE_MSG'),
        DTCriacao: document.getElementById('ftsxDTCriacao'),
        DTAlteracao: document.getElementById('ftsxDTAlteracao'),
        USERCRIACAO: document.getElementById('ftsxUSERCRIACAO'),
        USERALTERACAO: document.getElementById('ftsxUSERALTERACAO'),
      },
    },
  };

  const ftsEditableKeys = ['NDOC', 'SERIE', 'DESCR', 'ATIVA', 'ESTADO', 'NO_SAFT', 'TIPOSAFT'];
  const ftsxEditableKeys = ['COD_VALIDACAO_SERIE', 'ATCUD_PREFIX', 'AT_SERIE_ESTADO', 'AT_SERIE_DATA', 'AT_SERIE_MSG'];

  const esc = (value) => String(value ?? '').replace(/[&<>"']/g, (match) => (
    { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[match]
  ));

  function showToast(message, type = 'success') {
    if (typeof window.showToast === 'function') {
      window.showToast(message, type);
      return;
    }
    window.alert(message);
  }

  async function fetchJson(url, options = {}) {
    const response = await fetch(url, options);
    const text = await response.text();
    let data = {};
    if (text) {
      try {
        data = JSON.parse(text);
      } catch (error) {
        data = {};
      }
    }
    if (!response.ok || data.error) {
      throw new Error(data.error || 'Erro de comunicação.');
    }
    return data;
  }

  function emptyFtsRow() {
    return {
      FTSSTAMP: '',
      FESTAMP: String(currentEntity.FESTAMP || '').trim(),
      FEID: Number(currentEntity.FEID || 0),
      ANO: new Date().getFullYear(),
      NDOC: '',
      NMDOC: '',
      SERIE: '',
      DESCR: '',
      ATIVA: 1,
      ESTADO: 0,
      ULTIMO_FNO: 0,
      NO_SAFT: 0,
      TIPOSAFT: '',
      DTCriacao: '',
      DTAlteracao: '',
      USERCRIACAO: '',
      USERALTERACAO: '',
      HAS_FTSX: 0,
    };
  }

  function emptyFtsxRow(parentStamp = '') {
    return {
      FTSXSTAMP: '',
      FTSSTAMP: parentStamp,
      FEID: Number(currentEntity.FEID || 0),
      HASHVER: '',
      LAST_HASH: '',
      COD_VALIDACAO_SERIE: '',
      ATCUD_PREFIX: '',
      AT_SERIE_ESTADO: 0,
      AT_SERIE_DATA: '',
      AT_SERIE_MSG: '',
      DTCriacao: '',
      DTAlteracao: '',
      USERCRIACAO: '',
      USERALTERACAO: '',
    };
  }

  function normalizeFts(row) {
    return { ...emptyFtsRow(), ...(row || {}) };
  }

  function normalizeFtsx(row, parentStamp = '') {
    return { ...emptyFtsxRow(parentStamp), ...(row || {}) };
  }

  function isExistingFts() {
    return !!String(els.fields.fts.FTSSTAMP?.value || '').trim();
  }

  function hasExistingFtsx() {
    return !!String(els.fields.ftsx.FTSXSTAMP?.value || '').trim();
  }

  function canWriteCurrent() {
    return isExistingFts() ? permissions.edit : permissions.create;
  }

  function truncateHash(value) {
    const raw = String(value || '').trim();
    if (!raw) return '—';
    if (raw.length <= 36) return raw;
    return `${raw.slice(0, 18)}…${raw.slice(-10)}`;
  }

  function formatDateTime(value) {
    const raw = String(value || '').trim();
    if (!raw) return '';
    try {
      const dt = new Date(raw.replace(' ', 'T'));
      if (Number.isNaN(dt.getTime())) return raw;
      const pad = (num) => String(num).padStart(2, '0');
      return `${pad(dt.getDate())}/${pad(dt.getMonth() + 1)}/${dt.getFullYear()} ${pad(dt.getHours())}:${pad(dt.getMinutes())}:${pad(dt.getSeconds())}`;
    } catch (error) {
      return raw;
    }
  }

  function toDateTimeInput(value) {
    const raw = String(value || '').trim();
    if (!raw || raw.startsWith('1900-01-01')) return '';
    try {
      const dt = new Date(raw.replace(' ', 'T'));
      if (Number.isNaN(dt.getTime())) return '';
      const pad = (num) => String(num).padStart(2, '0');
      return `${dt.getFullYear()}-${pad(dt.getMonth() + 1)}-${pad(dt.getDate())}T${pad(dt.getHours())}:${pad(dt.getMinutes())}`;
    } catch (error) {
      return '';
    }
  }

  function boolBadge(value, trueLabel, falseLabel) {
    const active = Number(value || 0) === 1;
    return `<span class="sz_fts_badge ${active ? 'sz_fts_badge_ok' : 'sz_fts_badge_warn'}">${esc(active ? trueLabel : falseLabel)}</span>`;
  }

  function ftsxBadge(row) {
    return Number(row.HAS_FTSX || 0) === 1
      ? '<span class="sz_fts_badge sz_fts_badge_ok">FTSX</span>'
      : '<span class="sz_fts_badge sz_fts_badge_warn">Sem FTSX</span>';
  }

  function atEstadoBadge(row) {
    if (Number(row.HAS_FTSX || 0) !== 1) {
      return '<span class="sz_fts_badge sz_fts_badge_muted">AT —</span>';
    }
    return `<span class="sz_fts_badge sz_fts_badge_muted">AT ${esc(row.AT_SERIE_ESTADO ?? 0)}</span>`;
  }

  function updateStats() {
    const total = state.rows.length;
    const withFtsx = state.rows.filter((row) => Number(row.HAS_FTSX || 0) === 1).length;
    const active = state.rows.filter((row) => Number(row.ATIVA || 0) === 1).length;
    if (els.statTotal) els.statTotal.textContent = String(total);
    if (els.statWithFtsx) els.statWithFtsx.textContent = String(withFtsx);
    if (els.statActive) els.statActive.textContent = String(active);
  }

  function listItemHtml(row) {
    return `
      <div class="sz_panel sz_stack sz_fts_list_item ${state.currentStamp === row.FTSSTAMP ? 'sz_is_active' : ''}" data-ftsstamp="${esc(row.FTSSTAMP)}">
        <div class="sz_fts_list_head">
          <div class="sz_stack">
            <div class="sz_label">${esc(row.SERIE || '(sem série)')}</div>
            <div class="sz_text_muted">${esc(row.DESCR || '')}</div>
          </div>
          <div class="sz_fts_badges">
            ${boolBadge(row.ATIVA, 'Ativa', 'Inativa')}
            ${ftsxBadge(row)}
            ${atEstadoBadge(row)}
          </div>
        </div>
        <div class="sz_fts_list_meta">
          <span><strong>NDOC:</strong> ${esc(row.NDOC || 0)}</span>
          <span><strong>Ano:</strong> ${esc(row.ANO || 0)}</span>
          <span><strong>Estado:</strong> ${esc(row.ESTADO || 0)}</span>
          <span><strong>Último FNO:</strong> ${esc(row.ULTIMO_FNO || 0)}</span>
          <span><strong>NO_SAFT:</strong> ${Number(row.NO_SAFT || 0) === 1 ? '1' : '0'}</span>
          <span><strong>TIPOSAFT:</strong> ${esc(row.TIPOSAFT || '—')}</span>
          <span><strong>COD:</strong> ${esc(row.COD_VALIDACAO_SERIE || '—')}</span>
          <span><strong>Prefixo:</strong> ${esc(row.ATCUD_PREFIX || '—')}</span>
        </div>
      </div>
    `;
  }

  function renderList() {
    if (!els.list) return;
    if (!state.rows.length) {
      els.list.innerHTML = '<div class="sz_panel sz_fts_empty">Sem séries para os filtros aplicados.</div>';
      if (els.listSummary) els.listSummary.textContent = '0 séries';
      updateStats();
      return;
    }
    els.list.innerHTML = state.rows.map(listItemHtml).join('');
    if (els.listSummary) {
      els.listSummary.textContent = `${state.rows.length} série${state.rows.length === 1 ? '' : 's'}`;
    }
    updateStats();
    els.list.querySelectorAll('[data-ftsstamp]').forEach((node) => {
      node.addEventListener('click', () => openDetail(node.getAttribute('data-ftsstamp') || ''));
    });
  }

  function setFtsEditable(enabled) {
    ftsEditableKeys.forEach((key) => {
      const field = els.fields.fts[key];
      if (!field) return;
      field.disabled = !enabled;
    });
  }

  function setFtsxEditable(enabled) {
    ftsxEditableKeys.forEach((key) => {
      const field = els.fields.ftsx[key];
      if (!field) return;
      field.disabled = !enabled;
    });
  }

  function updateButtons() {
    const canWrite = canWriteCurrent();
    setFtsEditable(canWrite);
    setFtsxEditable(canWrite && hasExistingFtsx());
    if (els.btnNewTop) els.btnNewTop.disabled = !permissions.create;
    if (els.btnSaveBottom) els.btnSaveBottom.disabled = !canWrite;
    if (els.btnCreateFtsx) {
      els.btnCreateFtsx.disabled = !permissions.edit || !isExistingFts() || hasExistingFtsx();
    }
    if (els.ftsxLastHashCopy) {
      els.ftsxLastHashCopy.disabled = !String(state.currentFtsx?.LAST_HASH || '').trim();
    }
  }

  function fillFtsForm(row) {
    const current = normalizeFts(row);
    state.current = current;
    Object.entries(els.fields.fts).forEach(([key, field]) => {
      if (!field) return;
      if (field.type === 'checkbox') {
        field.checked = Number(current[key] || 0) === 1;
      } else {
        field.value = current[key] ?? '';
      }
    });
    if (els.editorTitle) {
      els.editorTitle.textContent = current.SERIE
        ? `${current.SERIE} · ${current.ANO || new Date().getFullYear()}`
        : 'Nova série';
    }
  }

  function fillFtsxForm(row, parentStamp = '') {
    const current = row ? normalizeFtsx(row, parentStamp) : null;
    state.currentFtsx = current;
    const hasFtsx = !!current;

    if (els.ftsxMissingNote) {
      els.ftsxMissingNote.hidden = hasFtsx;
    }
    if (els.ftsxFormWrap) {
      els.ftsxFormWrap.hidden = !hasFtsx;
    }

    if (els.ftsxStatusBadge) {
      if (hasFtsx) {
        els.ftsxStatusBadge.className = 'sz_fts_badge sz_fts_badge_ok';
        els.ftsxStatusBadge.textContent = `AT ${current.AT_SERIE_ESTADO ?? 0}`;
      } else {
        els.ftsxStatusBadge.className = 'sz_fts_badge sz_fts_badge_warn';
        els.ftsxStatusBadge.textContent = 'Sem configuração AT';
      }
    }

    const normalized = current || emptyFtsxRow(parentStamp);
    Object.entries(els.fields.ftsx).forEach(([key, field]) => {
      if (!field) return;
      if (key === 'AT_SERIE_DATA') {
        field.value = toDateTimeInput(normalized[key]);
      } else {
        field.value = normalized[key] ?? '';
      }
    });

    if (els.ftsxLastHash) {
      const lastHash = String(normalized.LAST_HASH || '').trim();
      els.ftsxLastHash.textContent = truncateHash(lastHash);
      els.ftsxLastHash.title = lastHash;
    }
  }

  function fillDetail(detail) {
    const fts = normalizeFts(detail?.fts || {});
    fillFtsForm(fts);
    fillFtsxForm(detail?.ftsx || null, fts.FTSSTAMP || '');
    updateButtons();
  }

  function buildListQuery() {
    const qs = new URLSearchParams();
    const serie = String(els.filters.serie?.value || '').trim();
    const ano = String(els.filters.ano?.value || '').trim();
    const ndoc = String(els.filters.ndoc?.value || '').trim();
    const ativa = String(els.filters.ativa?.value || '').trim();
    const tiposaft = String(els.filters.tiposaft?.value || '').trim();
    const ftsx = String(els.filters.ftsx?.value || '').trim();
    if (serie) qs.set('serie', serie);
    if (ano) qs.set('ano', ano);
    if (ndoc) qs.set('ndoc', ndoc);
    if (ativa) qs.set('ativa', ativa);
    if (tiposaft) qs.set('tiposaft', tiposaft);
    if (ftsx) qs.set('has_ftsx', ftsx);
    return qs.toString();
  }

  async function loadList() {
    if (!els.list) return;
    els.list.innerHTML = '<div class="sz_panel sz_fts_empty">A carregar...</div>';
    try {
      const qs = buildListQuery();
      const data = await fetchJson(`/api/fts${qs ? `?${qs}` : ''}`);
      state.rows = Array.isArray(data.rows) ? data.rows : [];
      renderList();
      const target = state.currentStamp && state.rows.some((row) => row.FTSSTAMP === state.currentStamp)
        ? state.currentStamp
        : (state.rows[0]?.FTSSTAMP || '');
      if (target) {
        await openDetail(target, { silent: true });
      } else {
        state.currentStamp = '';
        fillDetail({ fts: emptyFtsRow(), ftsx: null });
      }
    } catch (error) {
      state.rows = [];
      renderList();
      fillDetail({ fts: emptyFtsRow(), ftsx: null });
      showToast(error.message || 'Erro ao carregar séries.', 'danger');
    }
  }

  async function openDetail(ftsstamp, options = {}) {
    const normalized = String(ftsstamp || '').trim();
    if (!normalized) {
      state.currentStamp = '';
      fillDetail({ fts: emptyFtsRow(), ftsx: null });
      renderList();
      return;
    }
    try {
      const data = await fetchJson(`/api/fts/${encodeURIComponent(normalized)}`);
      state.currentStamp = normalized;
      fillDetail(data);
      renderList();
    } catch (error) {
      if (!options.silent) showToast(error.message || 'Erro ao carregar a série.', 'danger');
    }
  }

  function collectFtsPayload() {
    return {
      NDOC: String(els.fields.fts.NDOC?.value || '').trim(),
      SERIE: String(els.fields.fts.SERIE?.value || '').trim(),
      DESCR: String(els.fields.fts.DESCR?.value || '').trim(),
      ATIVA: els.fields.fts.ATIVA?.checked ? 1 : 0,
      ESTADO: String(els.fields.fts.ESTADO?.value || '').trim(),
      NO_SAFT: els.fields.fts.NO_SAFT?.checked ? 1 : 0,
      TIPOSAFT: String(els.fields.fts.TIPOSAFT?.value || '').trim().toUpperCase(),
    };
  }

  function collectFtsxPayload() {
    return {
      FTSSTAMP: String(els.fields.ftsx.FTSSTAMP?.value || '').trim(),
      COD_VALIDACAO_SERIE: String(els.fields.ftsx.COD_VALIDACAO_SERIE?.value || '').trim(),
      ATCUD_PREFIX: String(els.fields.ftsx.ATCUD_PREFIX?.value || '').trim(),
      AT_SERIE_ESTADO: String(els.fields.ftsx.AT_SERIE_ESTADO?.value || '').trim(),
      AT_SERIE_DATA: String(els.fields.ftsx.AT_SERIE_DATA?.value || '').trim(),
      AT_SERIE_MSG: String(els.fields.ftsx.AT_SERIE_MSG?.value || '').trim(),
    };
  }

  async function saveCurrent() {
    if (!canWriteCurrent()) return;
    try {
      let currentStamp = String(els.fields.fts.FTSSTAMP?.value || '').trim();
      const payload = collectFtsPayload();
      let data;
      if (currentStamp) {
        data = await fetchJson(`/api/fts/${encodeURIComponent(currentStamp)}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });
      } else {
        data = await fetchJson('/api/fts', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });
        currentStamp = String(data.fts?.FTSSTAMP || '').trim();
      }

      if (hasExistingFtsx()) {
        const ftsxStamp = String(els.fields.ftsx.FTSXSTAMP?.value || '').trim();
        await fetchJson(`/api/ftsx/${encodeURIComponent(ftsxStamp)}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(collectFtsxPayload()),
        });
      }

      await loadList();
      if (currentStamp) {
        await openDetail(currentStamp, { silent: true });
      }
      showToast('Série gravada.', 'success');
    } catch (error) {
      showToast(error.message || 'Erro ao gravar a série.', 'danger');
    }
  }

  async function createFtsx() {
    const ftsstamp = String(els.fields.fts.FTSSTAMP?.value || '').trim();
    if (!ftsstamp) {
      showToast('Grave a série antes de criar a configuração AT.', 'warning');
      return;
    }
    try {
      await fetchJson(`/api/fts/${encodeURIComponent(ftsstamp)}/create_ftsx`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      });
      await loadList();
      await openDetail(ftsstamp, { silent: true });
      showToast('Configuração AT criada.', 'success');
    } catch (error) {
      showToast(error.message || 'Erro ao criar configuração AT.', 'danger');
    }
  }

  async function copyLastHash() {
    const raw = String(state.currentFtsx?.LAST_HASH || '').trim();
    if (!raw) return;
    try {
      if (navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(raw);
      } else {
        const tmp = document.createElement('textarea');
        tmp.value = raw;
        document.body.appendChild(tmp);
        tmp.select();
        document.execCommand('copy');
        document.body.removeChild(tmp);
      }
      showToast('LAST_HASH copiado.', 'success');
    } catch (error) {
      showToast('Não foi possível copiar o LAST_HASH.', 'danger');
    }
  }

  function scheduleListReload() {
    window.clearTimeout(state.searchTimer);
    state.searchTimer = window.setTimeout(() => {
      loadList().catch(() => {});
    }, 250);
  }

  function bindEvents() {
    Object.values(els.filters).forEach((field) => {
      if (!field) return;
      const handler = (field.tagName === 'SELECT' || field.type === 'number') ? 'change' : 'input';
      field.addEventListener(handler, scheduleListReload);
    });

    els.btnNewTop?.addEventListener('click', () => {
      state.currentStamp = '';
      fillDetail({ fts: emptyFtsRow(), ftsx: null });
      renderList();
    });

    els.btnCancel?.addEventListener('click', () => {
      if (state.currentStamp) {
        openDetail(state.currentStamp).catch(() => {});
      } else {
        fillDetail({ fts: emptyFtsRow(), ftsx: null });
      }
    });

    els.btnSaveBottom?.addEventListener('click', () => {
      saveCurrent().catch(() => {});
    });

    els.btnCreateFtsx?.addEventListener('click', () => {
      createFtsx().catch(() => {});
    });

    els.ftsxLastHashCopy?.addEventListener('click', () => {
      copyLastHash().catch(() => {});
    });
  }

  bindEvents();
  fillDetail({ fts: emptyFtsRow(), ftsx: null });
  loadList().catch(() => {});
})();
