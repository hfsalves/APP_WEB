(function () {
  const tr = (key, vars) => (typeof window.t === 'function' ? window.t(key, vars) : key);

  const state = {
    enabled: true,
    rows: [],
    languages: [],
    origins: [],
    dirty: {},
    loading: false,
    selectedLanguage: String(window.DB_I18N_INITIAL_LANGUAGE || '').trim(),
    selectedOrigin: String(window.DB_I18N_INITIAL_ORIGIN || '').trim().toUpperCase(),
    search: '',
    autoTranslateAvailable: false,
    autoTranslateWarning: '',
    translationModel: '',
    searchTimer: null,
  };

  const els = {
    language: document.getElementById('dbI18nLanguage'),
    origin: document.getElementById('dbI18nOrigin'),
    search: document.getElementById('dbI18nSearch'),
    overwrite: document.getElementById('dbI18nOverwrite'),
    btnRefresh: document.getElementById('dbI18nRefreshBtn'),
    btnAuto: document.getElementById('dbI18nAutoBtn'),
    btnSave: document.getElementById('dbI18nSaveBtn'),
    notice: document.getElementById('dbI18nNotice'),
    summary: document.getElementById('dbI18nSummary'),
    modelHint: document.getElementById('dbI18nModelHint'),
    body: document.getElementById('dbI18nBody'),
  };

  function esc(value) {
    return String(value ?? '').replace(/[&<>"']/g, (match) => (
      { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[match]
    ));
  }

  function showToast(message, type = 'success') {
    if (typeof window.showToast === 'function') {
      window.showToast(message, type);
      return;
    }
    window.alert(message);
  }

  function rowKey(origin, oristamp, language) {
    return [String(language || '').trim(), String(origin || '').trim(), String(oristamp || '').trim()].join('::');
  }

  function dirtyItemsForCurrentLanguage() {
    return Object.values(state.dirty).filter((item) => item.language === state.selectedLanguage);
  }

  function dirtyValueForRow(row) {
    const key = rowKey(row.origin, row.oristamp, state.selectedLanguage);
    return Object.prototype.hasOwnProperty.call(state.dirty, key)
      ? state.dirty[key].translation
      : String(row.translation || '');
  }

  function currentLanguageIsBase() {
    return String(state.selectedLanguage || '') === 'pt_PT';
  }

  function statusForRow(row) {
    if (currentLanguageIsBase()) return 'base';
    const value = String(dirtyValueForRow(row) || '').trim();
    return value && value !== String(row.source_text || '').trim() ? 'translated' : 'pending';
  }

  function statusMeta(status) {
    if (status === 'translated') {
      return { label: tr('db_i18n.status_translated'), className: 'sz_badge sz_badge_success sz_db_i18n_badge' };
    }
    if (status === 'base') {
      return { label: tr('db_i18n.status_base'), className: 'sz_badge sz_badge_info sz_db_i18n_badge' };
    }
    return { label: tr('db_i18n.status_pending'), className: 'sz_badge sz_badge_warning sz_db_i18n_badge' };
  }

  function applySelectOptions(select, items, selectedValue) {
    if (!select) return;
    const html = (items || []).map((item) => {
      const code = String(item.code || '').trim();
      const label = String(item.label || code).trim() || code;
      const selected = code === String(selectedValue || '').trim() ? 'selected' : '';
      return `<option value="${esc(code)}" ${selected}>${esc(label)}</option>`;
    }).join('');
    select.innerHTML = html || '<option value=""></option>';
    select.value = String(selectedValue || '').trim();
  }

  function findLanguageLabel(code) {
    const match = (state.languages || []).find((item) => String(item.code || '').trim() === String(code || '').trim());
    return match ? String(match.label || code).trim() : String(code || '').trim();
  }

  function findOriginLabel(code) {
    const match = (state.origins || []).find((item) => String(item.code || '').trim() === String(code || '').trim());
    return match ? String(match.label || code).trim() : String(code || '').trim();
  }

  function setNotice(message, kind) {
    if (!els.notice) return;
    const text = String(message || '').trim();
    if (!text) {
      els.notice.classList.add('sz_hidden');
      els.notice.classList.remove('is-warning', 'is-info');
      els.notice.textContent = '';
      return;
    }
    els.notice.classList.remove('sz_hidden');
    els.notice.classList.remove('is-warning', 'is-info');
    if (kind === 'warning') {
      els.notice.classList.add('is-warning');
    } else {
      els.notice.classList.add('is-info');
    }
    els.notice.textContent = text;
  }

  function clearTableBody() {
    if (!els.body) return;
    while (els.body.firstChild) {
      els.body.removeChild(els.body.firstChild);
    }
  }

  function appendText(parent, tagName, className, text) {
    const node = document.createElement(tagName);
    if (className) node.className = className;
    node.textContent = String(text ?? '');
    parent.appendChild(node);
    return node;
  }

  function renderMessageRow(message) {
    if (!els.body) return;
    clearTableBody();
    const row = document.createElement('tr');
    const cell = document.createElement('td');
    cell.colSpan = 6;
    cell.className = 'sz_text_muted';
    cell.textContent = String(message || '');
    row.appendChild(cell);
    els.body.appendChild(row);
  }

  function renderNotice() {
    if (!state.enabled) {
      setNotice(tr('db_i18n.multilingual_required'), 'warning');
      return;
    }
    if (currentLanguageIsBase()) {
      setNotice(tr('db_i18n.base_language_readonly'), 'info');
      return;
    }
    if (!state.autoTranslateAvailable && state.autoTranslateWarning) {
      setNotice(state.autoTranslateWarning, 'warning');
      return;
    }
    setNotice('', '');
  }

  function renderModelHint() {
    if (!els.modelHint) return;
    els.modelHint.textContent = state.translationModel ? `OpenAI: ${state.translationModel}` : '';
  }

  function renderSummary() {
    if (!els.summary) return;
    if (!state.enabled) {
      els.summary.textContent = tr('db_i18n.multilingual_required');
      return;
    }

    const dirtyCount = dirtyItemsForCurrentLanguage().length;
    if (currentLanguageIsBase()) {
      els.summary.textContent = tr('db_i18n.summary_base', { total: state.rows.length });
      return;
    }

    let pending = 0;
    let translated = 0;
    state.rows.forEach((row) => {
      if (statusForRow(row) === 'translated') {
        translated += 1;
      } else {
        pending += 1;
      }
    });

    let text = tr('db_i18n.summary', {
      total: state.rows.length,
      translated,
      pending,
    });
    if (dirtyCount > 0) {
      text += ` | ${tr('db_i18n.summary_dirty', { count: dirtyCount })}`;
    }
    els.summary.textContent = text;
  }

  function updateControls() {
    const dirtyCount = dirtyItemsForCurrentLanguage().length;
    if (els.btnRefresh) els.btnRefresh.disabled = state.loading;
    if (els.btnSave) els.btnSave.disabled = state.loading || !state.enabled || currentLanguageIsBase() || dirtyCount <= 0;
    if (els.btnAuto) {
      els.btnAuto.disabled = (
        state.loading
        || !state.enabled
        || currentLanguageIsBase()
        || dirtyCount > 0
        || !state.autoTranslateAvailable
      );
    }
    if (els.language) els.language.disabled = state.loading;
    if (els.origin) els.origin.disabled = state.loading;
    if (els.search) els.search.disabled = state.loading;
    if (els.overwrite) els.overwrite.disabled = state.loading || !state.enabled || currentLanguageIsBase();
  }

  function renderRows() {
    if (!els.body) return;

    if (!state.rows.length) {
      renderMessageRow(tr('db_i18n.no_rows'));
      renderSummary();
      updateControls();
      renderNotice();
      renderModelHint();
      return;
    }

    try {
      clearTableBody();
      const fragment = document.createDocumentFragment();

      state.rows.forEach((row) => {
        const origin = String(row.origin || '').trim();
        const oristamp = String(row.oristamp || '').trim();
        const value = dirtyValueForRow(row);
        const dirty = Object.prototype.hasOwnProperty.call(state.dirty, rowKey(origin, oristamp, state.selectedLanguage));
        const status = statusForRow(row);
        const meta = statusMeta(status);
        const readonly = currentLanguageIsBase();

        const trEl = document.createElement('tr');
        trEl.className = `sz_db_i18n_row ${dirty ? 'is-dirty' : ''}`.trim();
        trEl.dataset.origin = origin;
        trEl.dataset.oristamp = oristamp;

        const originCell = document.createElement('td');
        appendText(originCell, 'span', 'sz_badge sz_badge_info', findOriginLabel(origin) || origin);
        trEl.appendChild(originCell);

        const contextCell = document.createElement('td');
        const contextWrap = document.createElement('div');
        contextWrap.className = 'sz_db_i18n_context';
        appendText(contextWrap, 'div', 'sz_db_i18n_context_main', row.context || '-');
        appendText(contextWrap, 'div', 'sz_db_i18n_context_extra', row.context_extra || '');
        contextCell.appendChild(contextWrap);
        trEl.appendChild(contextCell);

        const keyCell = document.createElement('td');
        appendText(keyCell, 'div', 'sz_db_i18n_key', oristamp);
        trEl.appendChild(keyCell);

        const statusCell = document.createElement('td');
        appendText(statusCell, 'span', meta.className, meta.label);
        trEl.appendChild(statusCell);

        const sourceCell = document.createElement('td');
        appendText(sourceCell, 'div', 'sz_db_i18n_source', row.source_text || '');
        trEl.appendChild(sourceCell);

        const translationCell = document.createElement('td');
        const textarea = document.createElement('textarea');
        textarea.className = 'sz_textarea sz_db_i18n_textarea';
        textarea.dataset.origin = origin;
        textarea.dataset.oristamp = oristamp;
        textarea.rows = 3;
        textarea.readOnly = readonly;
        textarea.disabled = readonly;
        textarea.value = String(value || '');
        translationCell.appendChild(textarea);
        trEl.appendChild(translationCell);

        fragment.appendChild(trEl);
      });

      els.body.appendChild(fragment);
    } catch (error) {
      renderMessageRow(tr('db_i18n.loading_error'));
      setNotice((error && error.message) || tr('db_i18n.loading_error'), 'warning');
      updateControls();
      renderModelHint();
      return;
    }

    renderSummary();
    updateControls();
    renderNotice();
    renderModelHint();
  }

  function setLoadingState(flag, message) {
    state.loading = !!flag;
    if (flag && els.body) {
      renderMessageRow(message || tr('common.loading'));
    }
    updateControls();
  }

  function applyBootstrap(payload) {
    state.enabled = payload.enabled !== false;
    state.languages = Array.isArray(payload.languages) ? payload.languages : [];
    state.origins = Array.isArray(payload.origins) ? payload.origins : [];
    state.selectedLanguage = String(payload.selected_language || state.selectedLanguage || 'en').trim() || 'en';
    state.selectedOrigin = String(payload.selected_origin || state.selectedOrigin || '').trim().toUpperCase();
    state.rows = Array.isArray(payload.rows) ? payload.rows : [];
    state.autoTranslateAvailable = !!payload.auto_translate_available;
    state.autoTranslateWarning = String(payload.auto_translate_warning || '').trim();
    state.translationModel = String(payload.translation_model || '').trim();

    applySelectOptions(els.language, state.languages, state.selectedLanguage);
    applySelectOptions(els.origin, state.origins, state.selectedOrigin);
    renderRows();
  }

  function applyRowsPayload(payload) {
    state.enabled = payload.enabled !== false;
    state.rows = Array.isArray(payload.rows) ? payload.rows : [];
    state.selectedLanguage = String(payload.language || state.selectedLanguage || '').trim();
    state.selectedOrigin = String(payload.origin || state.selectedOrigin || '').trim().toUpperCase();
    if (els.language && state.selectedLanguage) els.language.value = state.selectedLanguage;
    if (els.origin) els.origin.value = state.selectedOrigin;
    renderRows();
  }

  async function fetchJson(url, options) {
    const res = await fetch(url, options);
    const payload = await res.json().catch(() => ({}));
    if (!res.ok) {
      throw new Error(payload.error || `HTTP ${res.status}`);
    }
    return payload;
  }

  async function loadBootstrap() {
    const qs = new URLSearchParams();
    if (state.selectedLanguage) qs.set('language', state.selectedLanguage);
    if (state.selectedOrigin) qs.set('origin', state.selectedOrigin);
    if (state.search) qs.set('search', state.search);

    setLoadingState(true, tr('common.loading'));
    try {
      const payload = await fetchJson(`/api/i18n/db/bootstrap?${qs.toString()}`);
      applyBootstrap(payload);
    } catch (error) {
      state.enabled = false;
      state.rows = [];
      renderRows();
      setNotice(error.message || tr('db_i18n.loading_error'), 'warning');
      showToast(error.message || tr('db_i18n.loading_error'), 'danger');
    } finally {
      setLoadingState(false);
      renderRows();
    }
  }

  async function loadRows() {
    const qs = new URLSearchParams();
    if (state.selectedLanguage) qs.set('language', state.selectedLanguage);
    if (state.selectedOrigin) qs.set('origin', state.selectedOrigin);
    if (state.search) qs.set('search', state.search);

    setLoadingState(true, tr('common.loading'));
    try {
      const payload = await fetchJson(`/api/i18n/db/translations?${qs.toString()}`);
      applyRowsPayload(payload);
    } catch (error) {
      showToast(error.message || tr('db_i18n.loading_error'), 'danger');
    } finally {
      setLoadingState(false);
      renderRows();
    }
  }

  async function saveChanges() {
    const rows = dirtyItemsForCurrentLanguage().map((item) => ({
      origin: item.origin,
      oristamp: item.oristamp,
      translation: item.translation,
    }));
    if (!rows.length) return;

    setLoadingState(true, tr('common.loading'));
    try {
      await fetchJson('/api/i18n/db/translations/save', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          language: state.selectedLanguage,
          rows,
        }),
      });

      rows.forEach((item) => {
        delete state.dirty[rowKey(item.origin, item.oristamp, state.selectedLanguage)];
      });
      showToast(tr('db_i18n.save_success'));
      await loadRows();
    } catch (error) {
      showToast(error.message || tr('db_i18n.save_error'), 'danger');
    } finally {
      setLoadingState(false);
      renderRows();
    }
  }

  async function autoTranslate() {
    if (dirtyItemsForCurrentLanguage().length) {
      showToast(tr('db_i18n.save_before_auto_translate'), 'warning');
      return;
    }
    if (!state.autoTranslateAvailable) {
      showToast(state.autoTranslateWarning || tr('db_i18n.openai_missing_key'), 'warning');
      return;
    }

    let confirmText = tr('db_i18n.confirm_auto_translate', {
      language: findLanguageLabel(state.selectedLanguage),
    });
    if (state.selectedOrigin) {
      confirmText += ` (${findOriginLabel(state.selectedOrigin)})`;
    }
    if (els.overwrite && els.overwrite.checked) {
      confirmText += `\n${tr('db_i18n.overwrite_warning')}`;
    }
    if (!window.confirm(confirmText)) {
      return;
    }

    setLoadingState(true, tr('common.loading'));
    try {
      const payload = await fetchJson('/api/i18n/db/translations/auto_translate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          language: state.selectedLanguage,
          origin: state.selectedOrigin,
          overwrite: !!(els.overwrite && els.overwrite.checked),
        }),
      });

      if (Number(payload.updated || 0) > 0) {
        showToast(tr('db_i18n.auto_translate_success', { updated: Number(payload.updated || 0) }));
      } else {
        showToast(tr('db_i18n.nothing_to_translate'), 'warning');
      }
      await loadRows();
    } catch (error) {
      showToast(error.message || tr('db_i18n.auto_translate_error'), 'danger');
    } finally {
      setLoadingState(false);
      renderRows();
    }
  }

  function handleTextareaInput(event) {
    const target = event.target.closest('textarea[data-origin][data-oristamp]');
    if (!target) return;
    const origin = String(target.dataset.origin || '').trim();
    const oristamp = String(target.dataset.oristamp || '').trim();
    const row = state.rows.find((item) => item.origin === origin && item.oristamp === oristamp) || null;
    const key = rowKey(origin, oristamp, state.selectedLanguage);
    const nextValue = String(target.value || '').trim();

    if (row && nextValue === String(row.translation || '').trim()) {
      delete state.dirty[key];
    } else {
      state.dirty[key] = {
        language: state.selectedLanguage,
        origin,
        oristamp,
        translation: nextValue,
      };
    }

    const rowElement = target.closest('tr');
    if (rowElement) {
      rowElement.classList.toggle('is-dirty', Object.prototype.hasOwnProperty.call(state.dirty, key));
      const badge = rowElement.querySelector('.sz_db_i18n_badge');
      if (badge && row) {
        const meta = statusMeta(statusForRow(row));
        badge.className = meta.className;
        badge.textContent = meta.label;
      }
    }

    renderSummary();
    updateControls();
  }

  function bindEvents() {
    els.language?.addEventListener('change', function () {
      state.selectedLanguage = String(els.language.value || '').trim();
      loadRows();
    });

    els.origin?.addEventListener('change', function () {
      state.selectedOrigin = String(els.origin.value || '').trim().toUpperCase();
      loadRows();
    });

    els.search?.addEventListener('input', function () {
      clearTimeout(state.searchTimer);
      state.searchTimer = window.setTimeout(() => {
        state.search = String(els.search.value || '').trim();
        loadRows();
      }, 250);
    });

    els.btnRefresh?.addEventListener('click', function () {
      loadRows();
    });

    els.btnSave?.addEventListener('click', function () {
      saveChanges();
    });

    els.btnAuto?.addEventListener('click', function () {
      autoTranslate();
    });

    els.body?.addEventListener('input', handleTextareaInput);
  }

  bindEvents();
  loadBootstrap();
})();
