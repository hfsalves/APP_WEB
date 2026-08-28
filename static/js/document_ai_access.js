document.addEventListener('DOMContentLoaded', () => {
  const modal = document.getElementById('docAiAccessModal');
  const entityModal = document.getElementById('docAiAccessEntityModal');
  if (!modal || !entityModal) return;

  const els = {
    open: document.getElementById('docAiAccessAdminBtn'), close: document.getElementById('docAiAccessCloseTop'),
    cancel: document.getElementById('docAiAccessCancel'), save: document.getElementById('docAiAccessSave'),
    search: document.getElementById('docAiAccessSearch'), list: document.getElementById('docAiAccessList'),
    add: document.getElementById('docAiAccessAddBtn'), addForm: document.getElementById('docAiAccessAddForm'),
    user: document.getElementById('docAiAccessUser'), view: document.getElementById('docAiAccessView'),
    addConfirm: document.getElementById('docAiAccessAddConfirm'), entityClose: document.getElementById('docAiAccessEntityCloseTop'),
    entityCancel: document.getElementById('docAiAccessEntityCancel'), entityApply: document.getElementById('docAiAccessEntityApply'),
    entitySearch: document.getElementById('docAiAccessEntitySearch'), entityList: document.getElementById('docAiAccessEntityList'),
    allEntities: document.getElementById('docAiAccessAllEntities'),
  };
  const permissionLabels = { consult: 'Consultar', create: 'Criar', analyze: 'Analisar', delete: 'Eliminar', ai: 'iA', associate: 'Associar', validate: 'Validar' };
  let config = null;
  let expanded = new Set();
  let editingAssignment = null;
  let entityDraft = null;

  const escapeHtml = (value) => String(value == null ? '' : value).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  const showMessage = (message, type = 'info') => typeof window.showToast === 'function' ? window.showToast(message, type) : window.alert(message);
  const viewLabel = (value) => config?.views.find((item) => item.value === value)?.label || value;
  const userLabel = (login) => config?.users.find((item) => item.login.toLowerCase() === login)?.name || login;

  async function fetchJson(url, options = {}) {
    const response = await fetch(url, options);
    let payload = {};
    try { payload = await response.json(); } catch (_) {}
    if (!response.ok) throw new Error(payload.error || `HTTP ${response.status}`);
    return payload;
  }

  function entityLabel(item) {
    if (item.all_entities) return 'Todas';
    if (item.entity_ids.length === 1) return config.entities.find((entity) => entity.feid === item.entity_ids[0])?.name || '1 entidade';
    return `${item.entity_ids.length} entidades`;
  }

  function render() {
    if (!config) return;
    const query = String(els.search.value || '').trim().toLowerCase();
    const byUser = new Map();
    config.assignments.forEach((item) => {
      if (!byUser.has(item.login)) byUser.set(item.login, []);
      byUser.get(item.login).push(item);
    });
    const users = [...byUser.entries()].filter(([login]) => `${login} ${userLabel(login)}`.toLowerCase().includes(query));
    els.list.innerHTML = users.length ? users.map(([login, assignments]) => {
      const open = expanded.has(login);
      const isAdmin = config.admin_logins.includes(login);
      return `<section class="docai-access-user">
        <div class="docai-access-user-main">
          <button type="button" class="docai-access-expand" data-expand="${escapeHtml(login)}" aria-label="${open ? 'Ocultar' : 'Mostrar'} visualizações"><i class="fa-solid fa-${open ? 'minus' : 'plus'}"></i></button>
          <div><strong>${escapeHtml(userLabel(login))}</strong><span>${escapeHtml(login)} · ${assignments.length} visualização${assignments.length === 1 ? '' : 'ões'}</span></div>
          <span class="docai-access-entity-summary">${assignments.every((item) => item.all_entities) ? 'Todas' : 'Âmbito limitado'}</span>
          <label class="docai-access-check"><input type="checkbox" data-admin="${escapeHtml(login)}" ${isAdmin ? 'checked' : ''}><span>Administrador</span></label>
        </div>
        <div class="docai-access-views" ${open ? '' : 'hidden'}>
          ${assignments.sort((a, b) => config.views.findIndex(v => v.value === a.view) - config.views.findIndex(v => v.value === b.view)).map((item) => `
            <div class="docai-access-view-row" data-assignment="${escapeHtml(item.id)}">
              <strong>${escapeHtml(viewLabel(item.view))}</strong>
              <button type="button" class="docai-access-entity-button" data-entities="${escapeHtml(item.id)}">${escapeHtml(entityLabel(item))}</button>
              <div class="docai-access-permissions">${Object.entries(permissionLabels).map(([key, label]) => `<label class="docai-access-check"><input type="checkbox" data-permission="${key}" ${item.permissions[key] ? 'checked' : ''}><span>${label}</span></label>`).join('')}</div>
              <button type="button" class="sz_button sz_button_ghost docai-access-remove" data-remove="${escapeHtml(item.id)}" title="Remover visualização" aria-label="Remover visualização"><i class="fa-solid fa-trash"></i></button>
            </div>`).join('')}
        </div>
      </section>`;
    }).join('') : '<p class="sz_text_muted">Sem acessos configurados para esta pesquisa.</p>';
  }

  function populateSelectors() {
    els.user.innerHTML = config.users.map((item) => `<option value="${escapeHtml(item.login.toLowerCase())}">${escapeHtml(item.name)} · ${escapeHtml(item.login)}</option>`).join('');
    els.view.innerHTML = config.views.map((item) => `<option value="${escapeHtml(item.value)}">${escapeHtml(item.label)}</option>`).join('');
  }

  async function openModal() {
    modal.hidden = false;
    modal.classList.add('sz_is_open');
    els.list.innerHTML = '<p class="sz_text_muted">A carregar...</p>';
    try {
      config = await fetchJson('/api/document_ai/access-configuration');
      expanded = new Set();
      populateSelectors();
      render();
    } catch (error) {
      showMessage(error.message, 'error');
      modal.classList.remove('sz_is_open');
      modal.hidden = true;
    }
  }

  function closeModal() { modal.classList.remove('sz_is_open'); modal.hidden = true; els.addForm.hidden = true; }

  function openEntities(item) {
    editingAssignment = item;
    entityDraft = { all_entities: item.all_entities, entity_ids: [...item.entity_ids] };
    els.allEntities.checked = entityDraft.all_entities;
    els.entitySearch.value = '';
    renderEntities();
    entityModal.hidden = false;
    entityModal.classList.add('sz_is_open');
  }

  function renderEntities() {
    const query = String(els.entitySearch.value || '').trim().toLowerCase();
    els.entityList.innerHTML = config.entities.filter((item) => item.name.toLowerCase().includes(query)).map((item) => `
      <label class="docai-access-check"><input type="checkbox" value="${item.feid}" ${entityDraft.entity_ids.includes(item.feid) ? 'checked' : ''} ${entityDraft.all_entities ? 'disabled' : ''}><span>${escapeHtml(item.name)}</span></label>
    `).join('');
  }

  els.open?.addEventListener('click', openModal);
  els.close.addEventListener('click', closeModal);
  els.cancel.addEventListener('click', closeModal);
  modal.addEventListener('click', (event) => { if (event.target === modal) closeModal(); });
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && !modal.hidden && entityModal.hidden) closeModal();
  });
  els.search.addEventListener('input', render);
  els.add.addEventListener('click', () => { els.addForm.hidden = !els.addForm.hidden; });
  els.addConfirm.addEventListener('click', () => {
    const login = els.user.value.toLowerCase();
    const view = els.view.value;
    const existing = config.assignments.find((item) => item.login === login && item.view === view);
    if (existing) { expanded.add(login); render(); return; }
    config.assignments.push({ id: `new-${Date.now()}`, login, view, all_entities: true, entity_ids: [], permissions: Object.fromEntries(Object.keys(permissionLabels).map((key) => [key, true])) });
    expanded.add(login); els.addForm.hidden = true; render();
  });
  els.list.addEventListener('change', (event) => {
    const admin = event.target.dataset.admin;
    if (admin) {
      config.admin_logins = event.target.checked ? [...new Set([...config.admin_logins, admin])] : config.admin_logins.filter((value) => value !== admin);
      return;
    }
    const row = event.target.closest('[data-assignment]');
    if (!row || !event.target.dataset.permission) return;
    const item = config.assignments.find((entry) => entry.id === row.dataset.assignment);
    if (item) item.permissions[event.target.dataset.permission] = event.target.checked;
  });
  els.list.addEventListener('click', (event) => {
    const expand = event.target.closest('[data-expand]')?.dataset.expand;
    if (expand) { expanded.has(expand) ? expanded.delete(expand) : expanded.add(expand); render(); return; }
    const entityId = event.target.closest('[data-entities]')?.dataset.entities;
    if (entityId) { const item = config.assignments.find((entry) => entry.id === entityId); if (item) openEntities(item); return; }
    const removeId = event.target.closest('[data-remove]')?.dataset.remove;
    if (removeId) { config.assignments = config.assignments.filter((item) => item.id !== removeId); render(); }
  });
  els.entitySearch.addEventListener('input', renderEntities);
  els.allEntities.addEventListener('change', () => { entityDraft.all_entities = els.allEntities.checked; renderEntities(); });
  els.entityList.addEventListener('change', (event) => {
    const feid = Number(event.target.value || 0); if (!feid) return;
    entityDraft.entity_ids = event.target.checked ? [...new Set([...entityDraft.entity_ids, feid])] : entityDraft.entity_ids.filter((value) => value !== feid);
  });
  const closeEntities = () => { entityModal.classList.remove('sz_is_open'); entityModal.hidden = true; editingAssignment = null; entityDraft = null; };
  els.entityClose.addEventListener('click', closeEntities); els.entityCancel.addEventListener('click', closeEntities);
  els.entityApply.addEventListener('click', () => {
    if (!entityDraft.all_entities && !entityDraft.entity_ids.length) { showMessage('Seleciona pelo menos uma entidade.', 'error'); return; }
    editingAssignment.all_entities = entityDraft.all_entities; editingAssignment.entity_ids = entityDraft.all_entities ? [] : [...entityDraft.entity_ids]; closeEntities(); render();
  });
  els.save.addEventListener('click', async () => {
    els.save.disabled = true;
    try {
      config = await fetchJson('/api/document_ai/access-configuration', { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ assignments: config.assignments, admin_logins: config.admin_logins }) });
      showMessage('Acessos guardados.', 'success'); closeModal(); window.location.reload();
    } catch (error) { showMessage(error.message, 'error'); } finally { els.save.disabled = false; }
  });
});
