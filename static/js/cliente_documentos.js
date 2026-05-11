(function () {
  const els = {
    explorer: document.getElementById('clientDocumentsExplorer'),
    breadcrumb: document.getElementById('clientDocumentsBreadcrumb'),
    up: document.getElementById('clientDocumentsUp'),
    meta: document.getElementById('clientDocumentsMeta'),
    refresh: document.getElementById('clientDocumentsRefresh'),
    uploadBtn: document.getElementById('clientDocumentsUploadBtn'),
    uploadInput: document.getElementById('clientDocumentsUploadInput'),
    drop: document.getElementById('clientDocumentsDrop'),
    status: document.getElementById('clientDocumentsStatus'),
  };

  const state = {
    folders: [],
    folderMap: new Map(),
    currentPath: '',
    uploadFolder: 'ENVIADOS_PELO_CLIENTE',
  };

  function escapeHtml(value) {
    return String(value ?? '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function normalizePath(value) {
    return String(value || '')
      .replace(/\\/g, '/')
      .replace(/^\/+|\/+$/g, '')
      .replace(/\/+/g, '/');
  }

  function basename(path) {
    const parts = normalizePath(path).split('/').filter(Boolean);
    return parts[parts.length - 1] || 'Documentos';
  }

  function parentPath(path) {
    const parts = normalizePath(path).split('/').filter(Boolean);
    parts.pop();
    return parts.join('/');
  }

  function setStatus(message, type = '') {
    if (!els.status) return;
    els.status.textContent = message || '';
    els.status.classList.toggle('is-error', type === 'error');
    els.status.classList.toggle('is-success', type === 'success');
  }

  function formatBytes(value) {
    const size = Number(value || 0);
    if (size < 1024) return `${size} B`;
    if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`;
    return `${(size / (1024 * 1024)).toFixed(1)} MB`;
  }

  function formatDate(value) {
    const raw = String(value || '').trim();
    if (!raw) return '';
    const date = new Date(raw);
    if (Number.isNaN(date.getTime())) return raw.slice(0, 10);
    return date.toLocaleDateString('pt-PT');
  }

  function iconFor(ext) {
    const key = String(ext || '').toLowerCase();
    if (key === 'pdf') return 'fa-file-pdf';
    if (['xls', 'xlsx', 'csv'].includes(key)) return 'fa-file-excel';
    if (['doc', 'docx'].includes(key)) return 'fa-file-word';
    if (['png', 'jpg', 'jpeg', 'webp'].includes(key)) return 'fa-file-image';
    if (['zip', 'rar', '7z'].includes(key)) return 'fa-file-zipper';
    return 'fa-file-lines';
  }

  function folderIcon(folder) {
    if (folder?.is_client_uploads) return 'fa-inbox';
    return 'fa-folder';
  }

  function getChildFolders(path) {
    const current = normalizePath(path);
    return state.folders
      .filter((folder) => {
        const folderPath = normalizePath(folder.path);
        return folderPath && parentPath(folderPath) === current;
      })
      .sort((a, b) => {
        if (a.is_client_uploads !== b.is_client_uploads) return a.is_client_uploads ? 1 : -1;
        return basename(a.path).localeCompare(basename(b.path), 'pt', { sensitivity: 'base' });
      });
  }

  function renderBreadcrumb() {
    if (!els.breadcrumb) return;
    const parts = normalizePath(state.currentPath).split('/').filter(Boolean);
    const buttons = [
      '<button type="button" data-doc-path="">Documentos</button>',
    ];
    let cursor = '';
    parts.forEach((part) => {
      cursor = cursor ? `${cursor}/${part}` : part;
      buttons.push('<span class="client-documents-breadcrumb-sep">/</span>');
      buttons.push(`<button type="button" data-doc-path="${escapeHtml(cursor)}">${escapeHtml(part)}</button>`);
    });
    els.breadcrumb.innerHTML = buttons.join('');
  }

  function renderExplorer() {
    const currentPath = normalizePath(state.currentPath);
    const currentFolder = state.folderMap.get(currentPath) || state.folderMap.get('') || { files: [] };
    const folders = getChildFolders(currentPath);
    const files = Array.isArray(currentFolder.files) ? currentFolder.files : [];
    const total = folders.length + files.length;

    if (els.up) els.up.disabled = !currentPath;
    if (els.meta) {
      const label = currentPath ? basename(currentPath) : 'Documentos';
      els.meta.textContent = `${label} \u00b7 ${folders.length} pasta${folders.length === 1 ? '' : 's'} \u00b7 ${files.length} ficheiro${files.length === 1 ? '' : 's'}`;
    }
    renderBreadcrumb();

    if (!els.explorer) return;
    if (!total) {
      els.explorer.innerHTML = '<div class="client-documents-empty">Esta pasta esta vazia.</div>';
      return;
    }

    const folderRows = folders.map((folder) => `
      <button type="button" class="client-document-row" data-folder-path="${escapeHtml(normalizePath(folder.path))}">
        <span class="client-document-row-name">
          <span class="client-document-icon"><i class="fa-solid ${folderIcon(folder)}"></i></span>
          <span class="client-document-main">
            <span class="client-document-name">${escapeHtml(folder.name || basename(folder.path))}</span>
            <span class="client-document-folder-hint">${folder.is_client_uploads ? 'Documentos enviados pelo cliente' : 'Pasta'}</span>
          </span>
        </span>
        <span class="client-document-cell">Pasta</span>
        <span class="client-document-cell">-</span>
        <span class="client-document-cell">-</span>
        <span class="client-document-actions"></span>
      </button>
    `);

    const fileRows = files.map((file) => `
      <div class="client-document-row" data-download-url="${escapeHtml(file.download_url || '')}">
        <span class="client-document-row-name">
          <span class="client-document-icon"><i class="fa-solid ${iconFor(file.ext)}"></i></span>
          <span class="client-document-main">
            <span class="client-document-name">${escapeHtml(file.name || '')}</span>
            <span class="client-document-folder-hint">${escapeHtml(formatBytes(file.size))} &middot; ${escapeHtml(formatDate(file.modified))}</span>
          </span>
        </span>
        <span class="client-document-cell">${escapeHtml((file.ext || 'ficheiro').toUpperCase())}</span>
        <span class="client-document-cell">${escapeHtml(formatBytes(file.size))}</span>
        <span class="client-document-cell">${escapeHtml(formatDate(file.modified))}</span>
        <span class="client-document-actions">
          <a class="client-document-action" href="${escapeHtml(file.download_url || '#')}" title="Descarregar" aria-label="Descarregar ${escapeHtml(file.name || '')}">
            <i class="fa-solid fa-download"></i>
          </a>
          ${file.can_delete ? `
            <button type="button" class="client-document-action is-danger" data-delete-doc="${escapeHtml(file.path || '')}" data-delete-name="${escapeHtml(file.name || '')}" title="Eliminar" aria-label="Eliminar ${escapeHtml(file.name || '')}">
              <i class="fa-solid fa-trash"></i>
            </button>
          ` : ''}
        </span>
      </div>
    `);

    els.explorer.innerHTML = `
      <div class="client-documents-list">
        <div class="client-documents-list-head">
          <span>Nome</span>
          <span>Tipo</span>
          <span>Tamanho</span>
          <span>Modificado</span>
          <span></span>
        </div>
        ${folderRows.join('')}
        ${fileRows.join('')}
      </div>
    `;
  }

  function openFolder(path) {
    const nextPath = normalizePath(path);
    if (!state.folderMap.has(nextPath)) return;
    state.currentPath = nextPath;
    renderExplorer();
  }

  async function loadDocuments(preferredPath = state.currentPath) {
    if (els.explorer) els.explorer.innerHTML = '<div class="client-documents-empty">A carregar documentos...</div>';
    setStatus('');
    try {
      const response = await fetch('/api/cliente/documentos');
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data.error || 'Erro ao carregar documentos.');

      state.uploadFolder = normalizePath(data.upload_folder || state.uploadFolder);
      state.folders = Array.isArray(data.folders)
        ? data.folders.map((folder) => ({ ...folder, path: normalizePath(folder.path) }))
        : [];
      state.folderMap = new Map(state.folders.map((folder) => [normalizePath(folder.path), folder]));
      if (!state.folderMap.has('')) {
        state.folderMap.set('', { name: 'Documentos', path: '', files: [] });
      }

      const nextPath = normalizePath(preferredPath);
      state.currentPath = state.folderMap.has(nextPath) ? nextPath : '';
      renderExplorer();
    } catch (error) {
      if (els.explorer) {
        els.explorer.innerHTML = `<div class="client-documents-empty">Erro: ${escapeHtml(error.message || 'Nao foi possivel carregar documentos.')}</div>`;
      }
    }
  }

  async function uploadOneFile(file) {
    const formData = new FormData();
    formData.append('file', file);
    const response = await fetch('/api/cliente/documentos/upload', { method: 'POST', body: formData });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.error || 'Erro ao carregar documento.');
    return data;
  }

  async function uploadFiles(fileList) {
    const files = Array.from(fileList || []).filter(Boolean);
    if (!files.length) return;
    setStatus(files.length === 1 ? 'A carregar documento...' : `A carregar ${files.length} documentos...`);
    if (els.uploadBtn) els.uploadBtn.disabled = true;
    try {
      for (const file of files) {
        await uploadOneFile(file);
      }
      setStatus(files.length === 1 ? 'Documento carregado.' : 'Documentos carregados.', 'success');
      if (els.uploadInput) els.uploadInput.value = '';
      await loadDocuments(state.uploadFolder);
    } catch (error) {
      setStatus(error.message || 'Erro ao carregar documento.', 'error');
    } finally {
      if (els.uploadBtn) els.uploadBtn.disabled = false;
    }
  }

  async function deleteDocument(path, name) {
    const relPath = normalizePath(path);
    if (!relPath) return;
    const label = name || basename(relPath);
    if (!window.confirm(`Eliminar "${label}"?`)) return;

    setStatus('A eliminar documento...');
    try {
      const response = await fetch('/api/cliente/documentos/delete', {
        method: 'DELETE',
        headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
        body: JSON.stringify({ path: relPath }),
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok || data.error) throw new Error(data.error || 'Erro ao eliminar documento.');
      setStatus('Documento eliminado.', 'success');
      await loadDocuments(state.currentPath);
    } catch (error) {
      setStatus(error.message || 'Erro ao eliminar documento.', 'error');
    }
  }

  document.addEventListener('DOMContentLoaded', () => {
    els.refresh?.addEventListener('click', () => loadDocuments());
    els.up?.addEventListener('click', () => openFolder(parentPath(state.currentPath)));
    els.breadcrumb?.addEventListener('click', (event) => {
      const button = event.target.closest('[data-doc-path]');
      if (button) openFolder(button.getAttribute('data-doc-path') || '');
    });
    els.explorer?.addEventListener('click', (event) => {
      const deleteButton = event.target.closest('[data-delete-doc]');
      if (deleteButton) {
        event.preventDefault();
        event.stopPropagation();
        deleteDocument(deleteButton.getAttribute('data-delete-doc') || '', deleteButton.getAttribute('data-delete-name') || '');
        return;
      }
      const folderButton = event.target.closest('[data-folder-path]');
      if (folderButton) openFolder(folderButton.getAttribute('data-folder-path') || '');
      const downloadRow = event.target.closest('[data-download-url]');
      const downloadUrl = downloadRow?.getAttribute('data-download-url') || '';
      if (downloadUrl && !event.target.closest('.client-document-action')) {
        window.location.href = downloadUrl;
      }
    });
    els.uploadBtn?.addEventListener('click', () => els.uploadInput?.click());
    els.drop?.addEventListener('click', () => els.uploadInput?.click());
    els.uploadInput?.addEventListener('change', (event) => uploadFiles(event.target.files));
    els.drop?.addEventListener('dragover', (event) => {
      event.preventDefault();
      els.drop.classList.add('is-dragover');
    });
    els.drop?.addEventListener('dragleave', () => {
      els.drop.classList.remove('is-dragover');
    });
    els.drop?.addEventListener('drop', (event) => {
      event.preventDefault();
      els.drop.classList.remove('is-dragover');
      uploadFiles(event.dataTransfer?.files);
    });
    loadDocuments();
  });
})();
