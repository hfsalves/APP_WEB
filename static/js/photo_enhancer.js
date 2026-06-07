(function () {
  'use strict';

  const page = document.querySelector('.photo-enhancer-page');
  if (!page) return;

  const els = {
    lodge: document.getElementById('photoEnhancerLodge'),
    lodgeList: document.getElementById('photoEnhancerLodgeList'),
    sessionSelect: document.getElementById('photoEnhancerSessionSelect'),
    newSession: document.getElementById('photoEnhancerNewSession'),
    enhanceAll: document.getElementById('photoEnhancerEnhanceAll'),
    deleteSession: document.getElementById('photoEnhancerDeleteSession'),
    zip: document.getElementById('photoEnhancerZip'),
    files: document.getElementById('photoEnhancerFiles'),
    pickFiles: document.getElementById('photoEnhancerPickFiles'),
    grid: document.getElementById('photoEnhancerGrid'),
    empty: document.getElementById('photoEnhancerEmpty'),
    sessionLabel: document.getElementById('photoEnhancerSessionLabel'),
    status: document.getElementById('photoEnhancerStatus'),
    kpiLoaded: document.getElementById('photoKpiLoaded'),
    kpiEnhanced: document.getElementById('photoKpiEnhanced'),
    kpiErrors: document.getElementById('photoKpiErrors'),
    comparisonModal: document.getElementById('photoComparisonModal'),
    comparisonTitle: document.getElementById('photoComparisonTitle'),
    comparisonOriginal: document.getElementById('photoComparisonOriginal'),
    comparisonEnhanced: document.getElementById('photoComparisonEnhanced'),
    comparisonDownload: document.getElementById('photoComparisonDownload')
  };

  const state = {
    alojamentos: [],
    sessions: [],
    session: null,
    busy: false
  };

  const maxMb = Number(page.dataset.photoEnhancerMaxMb || 50);

  function setStatus(message, kind) {
    if (!els.status) return;
    els.status.textContent = message || '';
    els.status.dataset.kind = kind || '';
  }

  async function fetchJson(url, options) {
    const response = await fetch(url, {
      credentials: 'same-origin',
      ...(options || {})
    });
    let payload = null;
    try {
      payload = await response.json();
    } catch (error) {
      payload = null;
    }
    if (!response.ok || (payload && payload.ok === false)) {
      throw new Error((payload && payload.error) || `Erro HTTP ${response.status}`);
    }
    return payload || {};
  }

  function imageUrl(path) {
    if (!path) return '';
    const joiner = path.includes('?') ? '&' : '?';
    return `${path}${joiner}v=${Date.now()}`;
  }

  function selectedAlojamento() {
    const value = String(els.lodge?.value || '').trim().toLowerCase();
    if (!value) return null;
    return state.alojamentos.find((item) => {
      const label = lodgeLabel(item).toLowerCase();
      return label === value || String(item.nome || '').trim().toLowerCase() === value;
    }) || null;
  }

  function lodgeLabel(item) {
    const nome = String(item.nome || '').trim();
    const tipo = String(item.tipologia || '').trim();
    return tipo ? `${nome} · ${tipo}` : nome;
  }

  function renderLodges() {
    if (!els.lodgeList) return;
    els.lodgeList.innerHTML = '';
    const fragment = document.createDocumentFragment();
    state.alojamentos.forEach((item) => {
      const option = document.createElement('option');
      option.value = lodgeLabel(item);
      fragment.appendChild(option);
    });
    els.lodgeList.appendChild(fragment);
  }

  function formatDateTime(value) {
    if (!value) return '';
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return String(value);
    return date.toLocaleString('pt-PT', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  }

  function renderSessions() {
    if (!els.sessionSelect) return;
    els.sessionSelect.innerHTML = '';
    if (!state.sessions.length) {
      const option = document.createElement('option');
      option.value = '';
      option.textContent = 'Sem sessões';
      els.sessionSelect.appendChild(option);
      els.sessionSelect.disabled = true;
      return;
    }
    const empty = document.createElement('option');
    empty.value = '';
    empty.textContent = 'Escolher sessão';
    els.sessionSelect.appendChild(empty);
    state.sessions.forEach((item) => {
      const option = document.createElement('option');
      option.value = item.id;
      const when = formatDateTime(item.updated_at || item.created_at);
      option.textContent = `${when || item.id} · ${item.files_count || 0} fotos · ${item.enhanced_count || 0} melhoradas`;
      els.sessionSelect.appendChild(option);
    });
    els.sessionSelect.disabled = false;
    if (state.session) els.sessionSelect.value = state.session.id;
  }

  function fileList() {
    return (state.session && Array.isArray(state.session.files)) ? state.session.files : [];
  }

  function updateSummary() {
    const files = fileList();
    const enhanced = files.filter((item) => item.enhanced_path).length;
    const errors = files.filter((item) => item.status === 'erro').length;
    if (els.kpiLoaded) els.kpiLoaded.textContent = String(files.length);
    if (els.kpiEnhanced) els.kpiEnhanced.textContent = String(enhanced);
    if (els.kpiErrors) els.kpiErrors.textContent = String(errors);
    if (els.zip) els.zip.disabled = !state.session || enhanced === 0;
    if (els.enhanceAll) els.enhanceAll.disabled = state.busy || files.length === 0;
    if (els.deleteSession) els.deleteSession.disabled = state.busy || !state.session;
    if (els.pickFiles) els.pickFiles.disabled = state.busy || !selectedAlojamento();
    if (els.sessionLabel) {
      els.sessionLabel.textContent = state.session ? `Sessão ${state.session.id}` : 'Sem sessão ativa';
    }
  }

  function statusClass(status) {
    if (status === 'em_processamento') return 'is-processing';
    if (status === 'melhorada') return 'is-enhanced';
    if (status === 'erro') return 'is-error';
    return '';
  }

  function statusLabel(status) {
    if (status === 'em_processamento') return 'Em processamento';
    if (status === 'melhorada') return 'Melhorada';
    if (status === 'erro') return 'Erro';
    return 'Carregada';
  }

  function statusIcon(status) {
    if (status === 'em_processamento') return 'fa-spinner fa-spin';
    if (status === 'melhorada') return 'fa-circle-check';
    if (status === 'erro') return 'fa-triangle-exclamation';
    return 'fa-image';
  }

  function button(className, icon, label) {
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = className;
    btn.innerHTML = `<i class="fa-solid ${icon}"></i><span>${label}</span>`;
    return btn;
  }

  function renderCards() {
    const files = fileList();
    if (!els.grid) return;
    els.grid.innerHTML = '';
    if (els.empty) els.empty.style.display = files.length ? 'none' : '';
    const fragment = document.createDocumentFragment();
    files.forEach((item) => {
      const card = document.createElement('article');
      card.className = 'photo-card';
      card.dataset.fileId = item.id;

      const thumbs = document.createElement('div');
      thumbs.className = `photo-card_thumbs ${item.enhanced_path ? 'has-enhanced' : ''}`;

      function makeThumb(label, src, alt) {
        const thumb = document.createElement('div');
        thumb.className = 'photo-card_thumb';
        const labelEl = document.createElement('div');
        labelEl.className = 'photo-card_thumb_label';
        labelEl.textContent = label;
        const img = document.createElement('img');
        img.alt = alt || label;
        img.src = imageUrl(src);
        thumb.appendChild(labelEl);
        thumb.appendChild(img);
        return thumb;
      }

      thumbs.appendChild(makeThumb('Original', item.thumb_path || item.original_path, item.original_filename || 'Original'));
      if (item.enhanced_path) {
        thumbs.appendChild(makeThumb('Melhorada', item.enhanced_path, `${item.original_filename || 'Foto'} melhorada`));
      }

      const body = document.createElement('div');
      body.className = 'photo-card_body';

      const name = document.createElement('div');
      name.className = 'photo-card_name';
      name.title = item.original_filename || '';
      name.textContent = item.original_filename || 'Foto';

      const status = document.createElement('div');
      status.className = `photo-card_status ${statusClass(item.status)}`;
      status.innerHTML = `<i class="fa-solid ${statusIcon(item.status)}"></i><span>${statusLabel(item.status)}</span>`;

      const error = document.createElement('div');
      error.className = 'photo-card_error';
      error.textContent = item.error_message || '';

      const actions = document.createElement('div');
      actions.className = 'photo-card_actions';
      const enhanceBtn = button('sz_button sz_button_secondary', 'wand-magic-sparkles', item.enhanced_path ? 'Melhorar novamente' : 'Melhorar');
      enhanceBtn.disabled = state.busy;
      enhanceBtn.addEventListener('click', () => enhanceFile(item.id));
      actions.appendChild(enhanceBtn);

      if (item.enhanced_path) {
        const compareBtn = button('sz_button sz_button_secondary', 'columns', 'Ver comparação');
        compareBtn.addEventListener('click', () => openComparison(item));
        actions.appendChild(compareBtn);

        const download = document.createElement('a');
        download.className = 'sz_button sz_button_primary';
        download.href = `/api/photo-enhancer/files/${encodeURIComponent(item.id)}/download`;
        download.innerHTML = '<i class="fa-solid fa-download"></i><span>Descarregar</span>';
        actions.appendChild(download);
      }

      const removeBtn = button('sz_button sz_button_danger', 'trash', 'Remover');
      removeBtn.disabled = state.busy;
      removeBtn.addEventListener('click', () => deleteFile(item));
      actions.appendChild(removeBtn);

      body.appendChild(name);
      body.appendChild(status);
      body.appendChild(error);
      body.appendChild(actions);
      card.appendChild(thumbs);
      card.appendChild(body);
      fragment.appendChild(card);
    });
    els.grid.appendChild(fragment);
    updateSummary();
  }

  async function loadAlojamentos() {
    try {
      const payload = await fetchJson('/api/photo-enhancer/alojamentos');
      state.alojamentos = payload.items || [];
      renderLodges();
    } catch (error) {
      setStatus(error.message || 'Erro ao carregar alojamentos.', 'error');
    }
  }

  async function loadSessionsForSelectedLodge(openLatest) {
    const alojamento = selectedAlojamento();
    state.sessions = [];
    if (!alojamento) {
      state.session = null;
      renderSessions();
      renderCards();
      return;
    }
    try {
      const payload = await fetchJson(`/api/photo-enhancer/sessions?alojamento_id=${encodeURIComponent(alojamento.id)}`);
      state.sessions = payload.items || [];
      renderSessions();
      if (openLatest && state.sessions.length) {
        await openSession(state.sessions[0].id);
      } else {
        setStatus(state.sessions.length ? 'Há sessões anteriores para este alojamento.' : 'Sem sessões anteriores para este alojamento.', 'idle');
      }
    } catch (error) {
      renderSessions();
      setStatus(error.message || 'Erro ao carregar sessões.', 'error');
    }
  }

  async function openSession(sessionId) {
    if (!sessionId) {
      state.session = null;
      renderCards();
      return;
    }
    state.busy = true;
    updateSummary();
    try {
      const payload = await fetchJson(`/api/photo-enhancer/sessions/${encodeURIComponent(sessionId)}`);
      state.session = payload.session;
      if (els.sessionSelect) els.sessionSelect.value = state.session.id;
      setStatus('Sessão aberta.', 'success');
    } catch (error) {
      setStatus(error.message || 'Erro ao abrir sessão.', 'error');
    } finally {
      state.busy = false;
      updateSummary();
      renderCards();
    }
  }

  async function createSession() {
    const alojamento = selectedAlojamento();
    if (!alojamento) {
      setStatus('Escolhe um alojamento válido.', 'error');
      return null;
    }
    state.busy = true;
    updateSummary();
    try {
      const payload = await fetchJson('/api/photo-enhancer/sessions', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({alojamento_id: alojamento.id})
      });
      state.session = payload.session;
      await loadSessionsForSelectedLodge(false);
      if (els.sessionSelect) els.sessionSelect.value = state.session.id;
      setStatus(alojamento.nome || 'Sessão criada.', 'success');
      return state.session;
    } catch (error) {
      setStatus(error.message || 'Erro ao criar sessão.', 'error');
      return null;
    } finally {
      state.busy = false;
      updateSummary();
      renderCards();
    }
  }

  async function ensureSession() {
    if (state.session) return state.session;
    return createSession();
  }

  async function uploadFiles(files) {
    const session = await ensureSession();
    if (!session) return;
    const selected = Array.from(files || []);
    if (!selected.length) return;
    const tooLarge = selected.find((file) => file.size > maxMb * 1024 * 1024);
    if (tooLarge) {
      setStatus(`${tooLarge.name} excede ${maxMb} MB.`, 'error');
      return;
    }
    const form = new FormData();
    selected.forEach((file) => form.append('files', file));
    state.busy = true;
    setStatus('A carregar fotos...', 'busy');
    updateSummary();
    renderCards();
    try {
      const payload = await fetchJson(`/api/photo-enhancer/sessions/${encodeURIComponent(session.id)}/upload`, {
        method: 'POST',
        body: form
      });
      state.session = payload.session || state.session;
      const errors = payload.errors || [];
      setStatus(errors.length ? `${selected.length - errors.length} fotos carregadas, ${errors.length} com erro.` : 'Fotos carregadas.', errors.length ? 'warning' : 'success');
      renderCards();
    } catch (error) {
      setStatus(error.message || 'Erro no upload.', 'error');
    } finally {
      state.busy = false;
      updateSummary();
      renderCards();
      if (els.files) els.files.value = '';
    }
  }

  function mergeFile(updated) {
    if (!state.session || !updated) return;
    const files = fileList();
    const idx = files.findIndex((item) => item.id === updated.id);
    if (idx >= 0) {
      files[idx] = updated;
    } else {
      files.push(updated);
    }
  }

  async function enhanceFile(fileId) {
    state.busy = true;
    const files = fileList();
    const target = files.find((item) => item.id === fileId);
    if (target) target.status = 'em_processamento';
    setStatus('A melhorar foto...', 'busy');
    renderCards();
    try {
      const payload = await fetchJson(`/api/photo-enhancer/files/${encodeURIComponent(fileId)}/enhance`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({})
      });
      mergeFile(payload.file);
      setStatus('Foto melhorada.', 'success');
    } catch (error) {
      setStatus(error.message || 'Erro ao melhorar foto.', 'error');
      try {
        if (state.session) {
          const sessionPayload = await fetchJson(`/api/photo-enhancer/sessions/${encodeURIComponent(state.session.id)}`);
          state.session = sessionPayload.session || state.session;
        }
      } catch (innerError) {
        // Mantem o estado local se a atualização falhar.
      }
    } finally {
      state.busy = false;
      renderCards();
    }
  }

  async function enhanceAllFiles() {
    const files = fileList();
    if (!files.length || state.busy) return;
    let targets = files.filter((item) => !item.enhanced_path);
    if (!targets.length) {
      if (!window.confirm('Todas as fotos já estão melhoradas. Melhorar novamente todas?')) return;
      targets = files.slice();
    }
    state.busy = true;
    updateSummary();
    try {
      for (let index = 0; index < targets.length; index += 1) {
        const target = targets[index];
        setStatus(`A melhorar ${index + 1} de ${targets.length}...`, 'busy');
        const local = fileList().find((item) => item.id === target.id);
        if (local) local.status = 'em_processamento';
        renderCards();
        const payload = await fetchJson(`/api/photo-enhancer/files/${encodeURIComponent(target.id)}/enhance`, {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({})
        });
        mergeFile(payload.file);
      }
      setStatus(`${targets.length} foto${targets.length === 1 ? '' : 's'} melhorada${targets.length === 1 ? '' : 's'}.`, 'success');
    } catch (error) {
      setStatus(error.message || 'Erro ao melhorar fotos.', 'error');
      if (state.session) {
        try {
          const sessionPayload = await fetchJson(`/api/photo-enhancer/sessions/${encodeURIComponent(state.session.id)}`);
          state.session = sessionPayload.session || state.session;
        } catch (innerError) {
          // Mantem o estado atual se a sincronização falhar.
        }
      }
    } finally {
      state.busy = false;
      renderCards();
    }
  }

  async function deleteFile(item) {
    if (!item || !item.id || state.busy) return;
    const label = item.original_filename || 'esta foto';
    if (!window.confirm(`Remover ${label} desta sessão?`)) return;
    state.busy = true;
    setStatus('A remover foto...', 'busy');
    renderCards();
    try {
      const payload = await fetchJson(`/api/photo-enhancer/files/${encodeURIComponent(item.id)}`, {
        method: 'DELETE'
      });
      state.session = payload.session || state.session;
      setStatus('Foto removida.', 'success');
    } catch (error) {
      setStatus(error.message || 'Erro ao remover foto.', 'error');
    } finally {
      state.busy = false;
      renderCards();
    }
  }

  async function deleteCurrentSession() {
    if (!state.session || state.busy) return;
    if (!window.confirm('Remover esta sessão e todas as fotos associadas?')) return;
    const sessionId = state.session.id;
    state.busy = true;
    updateSummary();
    try {
      await fetchJson(`/api/photo-enhancer/sessions/${encodeURIComponent(sessionId)}`, {
        method: 'DELETE'
      });
      state.session = null;
      await loadSessionsForSelectedLodge(false);
      setStatus('Sessão removida.', 'success');
      renderCards();
    } catch (error) {
      setStatus(error.message || 'Erro ao remover sessão.', 'error');
    } finally {
      state.busy = false;
      updateSummary();
      renderCards();
    }
  }

  function openComparison(item) {
    if (!item || !item.enhanced_path) return;
    if (els.comparisonTitle) els.comparisonTitle.textContent = item.original_filename || 'Comparação';
    if (els.comparisonOriginal) {
      els.comparisonOriginal.onload = () => {
        const width = els.comparisonOriginal.naturalWidth || 4;
        const height = els.comparisonOriginal.naturalHeight || 3;
        document.documentElement.style.setProperty('--photo-comparison-ratio', `${width} / ${height}`);
      };
      els.comparisonOriginal.src = imageUrl(item.original_path);
    }
    if (els.comparisonEnhanced) els.comparisonEnhanced.src = imageUrl(item.enhanced_path);
    if (els.comparisonDownload) {
      els.comparisonDownload.href = `/api/photo-enhancer/files/${encodeURIComponent(item.id)}/download`;
    }
    if (window.bootstrap && els.comparisonModal) {
      window.bootstrap.Modal.getOrCreateInstance(els.comparisonModal).show();
    }
  }

  function downloadZip() {
    if (!state.session) return;
    window.location.href = `/api/photo-enhancer/sessions/${encodeURIComponent(state.session.id)}/zip`;
  }

  function bindEvents() {
    els.newSession?.addEventListener('click', createSession);
    els.enhanceAll?.addEventListener('click', enhanceAllFiles);
    els.deleteSession?.addEventListener('click', deleteCurrentSession);
    els.pickFiles?.addEventListener('click', () => els.files?.click());
    els.files?.addEventListener('change', () => uploadFiles(els.files.files));
    els.zip?.addEventListener('click', downloadZip);
    els.sessionSelect?.addEventListener('change', () => openSession(els.sessionSelect.value));
    els.lodge?.addEventListener('input', () => {
      updateSummary();
    });
    els.lodge?.addEventListener('change', () => {
      state.session = null;
      loadSessionsForSelectedLodge(false);
      renderCards();
    });
  }

  bindEvents();
  loadAlojamentos();
  renderCards();
})();
