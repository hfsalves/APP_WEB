document.addEventListener('DOMContentLoaded', () => {
  const els = {
    backInboxBtn: document.getElementById('docAiBackInboxBtn'),
    newBtn: document.getElementById('docAiNewSourceBtn'),
    list: document.getElementById('docAiSourceList'),
    meta: document.getElementById('docAiSourcesMeta'),
    editorMeta: document.getElementById('docAiSourceEditorMeta'),
    name: document.getElementById('docAiSourceName'),
    folder: document.getElementById('docAiSourceFolder'),
    pattern: document.getElementById('docAiSourcePattern'),
    interval: document.getElementById('docAiSourceInterval'),
    subfolders: document.getElementById('docAiSourceSubfolders'),
    active: document.getElementById('docAiSourceActive'),
    lastRun: document.getElementById('docAiSourceLastRun'),
    lastStatus: document.getElementById('docAiSourceLastStatus'),
    saveBtn: document.getElementById('docAiSaveSourceBtn'),
    deleteBtn: document.getElementById('docAiDeleteSourceBtn'),
    status: document.getElementById('docAiSourceStatus'),
  };

  const state = {
    items: [],
    selectedId: '',
  };

  function showMessage(message, type = 'info') {
    if (typeof window.showToast === 'function') {
      window.showToast(message, type);
      return;
    }
    console[type === 'error' ? 'error' : 'log'](message);
  }

  function escapeHtml(value) {
    return String(value == null ? '' : value)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function formatDateTime(value) {
    if (!value) return 'Ainda sem execução.';
    const parsed = new Date(value);
    if (Number.isNaN(parsed.getTime())) return String(value);
    return new Intl.DateTimeFormat('pt-PT', { dateStyle: 'short', timeStyle: 'short' }).format(parsed);
  }

  function setStatus(message, isError = false) {
    if (!els.status) return;
    els.status.textContent = message || '';
    els.status.style.color = isError ? 'var(--sz-color-danger)' : '';
  }

  async function fetchJson(url, options = {}) {
    const response = await fetch(url, options);
    let payload = {};
    try {
      payload = await response.json();
    } catch (_) {}
    if (!response.ok) throw new Error(payload.error || `HTTP ${response.status}`);
    return payload;
  }

  function blankSource() {
    return {
      id: '',
      name: '',
      folder: '',
      file_pattern: '',
      include_subfolders: false,
      active: true,
      interval_minutes: 5,
      last_run_at: '',
      last_status: '',
      last_message: '',
      folder_exists: false,
    };
  }

  function renderList() {
    if (!els.list) return;
    if (!state.items.length) {
      els.list.innerHTML = '<div class="sz_text_muted">Sem origens configuradas.</div>';
      return;
    }
    els.list.innerHTML = state.items.map((item) => `
      <button type="button" class="docai-template-item${state.selectedId === item.id ? ' is-active' : ''}" data-source-id="${escapeHtml(item.id)}">
        <div class="docai-template-item-top">
          <strong>${escapeHtml(item.name || 'Sem nome')}</strong>
          <span class="docai-state-badge ${item.active ? 'status-parsed_ok' : 'status-parse_error'}">${item.active ? 'Ativa' : 'Inativa'}</span>
        </div>
        <div class="sz_text_muted">${escapeHtml(item.folder || 'Sem pasta')}</div>
        <div class="sz_text_muted">${Number(item.interval_minutes || 5)} min. · ${item.include_subfolders ? 'com subpastas' : 'sem subpastas'}</div>
      </button>
    `).join('');
  }

  function applySource(source) {
    const item = source || blankSource();
    state.selectedId = item.id || '';
    if (els.name) els.name.value = item.name || '';
    if (els.folder) els.folder.value = item.folder || '';
    if (els.pattern) els.pattern.value = item.file_pattern || '';
    if (els.interval) els.interval.value = Number(item.interval_minutes || 5);
    if (els.subfolders) els.subfolders.checked = !!item.include_subfolders;
    if (els.active) els.active.checked = item.active !== false;
    if (els.editorMeta) els.editorMeta.textContent = item.id ? `Editar ${item.name || 'origem'}` : 'Nova origem';
    if (els.lastRun) els.lastRun.textContent = formatDateTime(item.last_run_at);
    if (els.lastStatus) {
      const folderState = item.folder ? (item.folder_exists ? 'Pasta acessível.' : 'Pasta ainda não validada neste servidor.') : 'Sem pasta configurada.';
      const status = item.last_status || 'Sem estado.';
      const message = item.last_message ? ` · ${item.last_message}` : '';
      els.lastStatus.textContent = `${status}${message} ${folderState}`;
    }
    if (els.deleteBtn) els.deleteBtn.disabled = !item.id;
    renderList();
  }

  function currentPayload() {
    return {
      name: els.name?.value.trim() || '',
      folder: els.folder?.value.trim() || '',
      file_pattern: els.pattern?.value.trim() || '',
      include_subfolders: !!els.subfolders?.checked,
      active: !!els.active?.checked,
      interval_minutes: Number(els.interval?.value || 5) || 5,
    };
  }

  async function loadSources() {
    setStatus('A carregar origens...');
    try {
      const payload = await fetchJson('/api/document_ai/sources');
      state.items = Array.isArray(payload.items) ? payload.items : [];
      if (els.meta) els.meta.textContent = `${state.items.length} origem(ns) configurada(s).`;
      const selected = state.items.find((item) => item.id === state.selectedId) || state.items[0] || null;
      applySource(selected || blankSource());
      setStatus('Origens carregadas.');
    } catch (error) {
      console.error(error);
      showMessage(error.message || 'Erro ao carregar origens.', 'error');
      setStatus(error.message || 'Erro ao carregar origens.', true);
    }
  }

  async function selectSource(id) {
    if (!id) {
      applySource(blankSource());
      return;
    }
    setStatus('A carregar origem...');
    try {
      const payload = await fetchJson(`/api/document_ai/sources/${encodeURIComponent(id)}`);
      applySource(payload);
      setStatus('Origem carregada.');
    } catch (error) {
      console.error(error);
      showMessage(error.message || 'Erro ao carregar origem.', 'error');
      setStatus(error.message || 'Erro ao carregar origem.', true);
    }
  }

  async function saveSource() {
    const payload = currentPayload();
    if (!payload.name || !payload.folder) {
      showMessage('Indica o nome e a pasta da origem.', 'warning');
      return;
    }
    setStatus('A guardar origem...');
    try {
      const url = state.selectedId
        ? `/api/document_ai/sources/${encodeURIComponent(state.selectedId)}`
        : '/api/document_ai/sources';
      const saved = await fetchJson(url, {
        method: state.selectedId ? 'PUT' : 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      state.selectedId = saved.id || '';
      showMessage('Origem guardada.', 'success');
      await loadSources();
      setStatus('Origem guardada.');
    } catch (error) {
      console.error(error);
      showMessage(error.message || 'Falha ao guardar origem.', 'error');
      setStatus(error.message || 'Falha ao guardar origem.', true);
    }
  }

  async function deleteSource() {
    if (!state.selectedId) return;
    if (!window.confirm('Remover esta origem documental?')) return;
    setStatus('A remover origem...');
    try {
      await fetchJson(`/api/document_ai/sources/${encodeURIComponent(state.selectedId)}`, { method: 'DELETE' });
      state.selectedId = '';
      showMessage('Origem removida.', 'success');
      await loadSources();
      setStatus('Origem removida.');
    } catch (error) {
      console.error(error);
      showMessage(error.message || 'Falha ao remover origem.', 'error');
      setStatus(error.message || 'Falha ao remover origem.', true);
    }
  }

  els.backInboxBtn?.addEventListener('click', () => { window.location.href = '/document_ai/inbox'; });
  els.newBtn?.addEventListener('click', () => applySource(blankSource()));
  els.saveBtn?.addEventListener('click', saveSource);
  els.deleteBtn?.addEventListener('click', deleteSource);
  els.list?.addEventListener('click', (event) => {
    const item = event.target.closest('[data-source-id]');
    if (!item) return;
    selectSource(item.dataset.sourceId || '');
  });

  loadSources();
});
