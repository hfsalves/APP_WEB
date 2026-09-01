(() => {
  'use strict';

  const root = document.getElementById('phcApprovalLimitsPage');
  if (!root) return;

  const elements = {
    search: document.getElementById('approvalLimitsSearch'),
    refresh: document.getElementById('approvalLimitsRefresh'),
    create: document.getElementById('approvalLimitsNew'),
    rows: document.getElementById('approvalLimitsRows'),
    mobileList: document.getElementById('approvalLimitsMobileList'),
    count: document.getElementById('approvalLimitsCount'),
    alert: document.getElementById('approvalLimitsAlert'),
    editor: document.getElementById('approvalLimitEditor'),
    editorTitle: document.getElementById('approvalLimitEditorTitle'),
    form: document.getElementById('approvalLimitForm'),
    usercode: document.getElementById('approvalLimitUsercode'),
    username: document.getElementById('approvalLimitUsername'),
    value: document.getElementById('approvalLimitValue'),
    formError: document.getElementById('approvalLimitFormError'),
    save: document.getElementById('approvalLimitSave'),
    deleteConfirm: document.getElementById('approvalLimitDeleteConfirm'),
    deleteText: document.getElementById('approvalLimitDeleteText'),
    deleteError: document.getElementById('approvalLimitDeleteError'),
    deleteApply: document.getElementById('approvalLimitDeleteApply')
  };

  const state = {
    items: [],
    users: [],
    editingStamp: '',
    deletingStamp: '',
    loading: false
  };

  const escapeHtml = (value) => String(value ?? '').replace(/[&<>'"]/g, (char) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;'
  }[char]));

  const money = (value) => new Intl.NumberFormat('pt-PT', {
    style: 'currency',
    currency: 'EUR',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  }).format(Number(value || 0));

  const dateTime = (value) => {
    if (!value) return '—';
    const parsed = new Date(value);
    if (Number.isNaN(parsed.getTime())) return '—';
    return new Intl.DateTimeFormat('pt-PT', {
      dateStyle: 'short',
      timeStyle: 'short'
    }).format(parsed);
  };

  async function request(url, options = {}) {
    const response = await fetch(url, {
      ...options,
      headers: {
        Accept: 'application/json',
        ...(options.body ? { 'Content-Type': 'application/json' } : {}),
        ...(options.headers || {})
      }
    });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok || !payload.ok) {
      throw new Error(payload.error || 'Não foi possível concluir a operação.');
    }
    return payload;
  }

  function showAlert(message) {
    elements.alert.textContent = message || '';
    elements.alert.hidden = !message;
  }

  function duplicateLabel(item) {
    if (Number(item.duplicate_count || 0) <= 1) return '';
    return `<span class="phc-approval-limit-duplicate" title="Existem ${item.duplicate_count} registos para este login"><i class="fa-solid fa-triangle-exclamation" aria-hidden="true"></i>Duplicado</span>`;
  }

  function actionButtons(item) {
    return `<div class="phc-approval-limit-actions">
      <button type="button" class="sz_button sz_button_icon sz_button_secondary" data-action="edit" data-stamp="${escapeHtml(item.stamp)}" title="Editar plafond" aria-label="Editar plafond de ${escapeHtml(item.username)}">
        <i class="fa-solid fa-pen" aria-hidden="true"></i>
      </button>
      <button type="button" class="sz_button sz_button_icon sz_button_danger" data-action="delete" data-stamp="${escapeHtml(item.stamp)}" title="Eliminar plafond" aria-label="Eliminar plafond de ${escapeHtml(item.username)}">
        <i class="fa-solid fa-trash" aria-hidden="true"></i>
      </button>
    </div>`;
  }

  function filteredItems() {
    const query = elements.search.value.trim().toLocaleLowerCase('pt-PT');
    if (!query) return state.items;
    return state.items.filter((item) =>
      String(item.usercode || '').toLocaleLowerCase('pt-PT').includes(query)
      || String(item.username || '').toLocaleLowerCase('pt-PT').includes(query)
    );
  }

  function render() {
    const items = filteredItems();
    const total = state.items.length;
    elements.count.textContent = elements.search.value.trim()
      ? `${items.length} de ${total} registos`
      : `${total} ${total === 1 ? 'registo' : 'registos'}`;

    if (!items.length) {
      const message = state.items.length ? 'Não existem registos para a pesquisa.' : 'Não existem plafonds configurados.';
      elements.rows.innerHTML = `<tr><td colspan="5" class="sz_text_muted">${message}</td></tr>`;
      elements.mobileList.innerHTML = `<div class="sz_text_muted">${message}</div>`;
      return;
    }

    elements.rows.innerHTML = items.map((item) => `<tr>
      <td><div class="phc-approval-limit-user"><strong>${escapeHtml(item.usercode)}</strong>${duplicateLabel(item)}</div></td>
      <td>${escapeHtml(item.username || '—')}</td>
      <td class="phc-approval-limit-number"><strong>${escapeHtml(money(item.plafond))}</strong></td>
      <td><div class="phc-approval-limit-updated">${escapeHtml(dateTime(item.updated_at))}<br>${escapeHtml(item.updated_by || '—')}</div></td>
      <td>${actionButtons(item)}</td>
    </tr>`).join('');

    elements.mobileList.innerHTML = items.map((item) => `<article class="phc-approval-limit-card">
      <div class="phc-approval-limit-card-main">
        <strong>${escapeHtml(item.username || '—')}</strong>
        <span>${escapeHtml(item.usercode)}</span>
        ${duplicateLabel(item)}
      </div>
      <div class="phc-approval-limit-card-value">${escapeHtml(money(item.plafond))}</div>
      <div class="phc-approval-limit-card-footer">
        <span class="phc-approval-limit-card-meta">${escapeHtml(dateTime(item.updated_at))}</span>
        ${actionButtons(item)}
      </div>
    </article>`).join('');
  }

  function renderUsers(selected = '') {
    const wanted = String(selected || '').trim().toLowerCase();
    elements.usercode.innerHTML = '<option value="">Selecione um utilizador</option>' + state.users.map((user) => {
      const suffix = user.inactive ? ' · Inativo' : '';
      return `<option value="${escapeHtml(user.usercode)}"${user.usercode.toLowerCase() === wanted ? ' selected' : ''}>${escapeHtml(user.usercode)} · ${escapeHtml(user.username)}${suffix}</option>`;
    }).join('');
    updateSelectedUsername();
  }

  function updateSelectedUsername() {
    const selected = state.users.find((user) => user.usercode === elements.usercode.value);
    elements.username.value = selected ? selected.username : '';
  }

  async function load() {
    if (state.loading) return;
    state.loading = true;
    elements.refresh.disabled = true;
    showAlert('');
    elements.count.textContent = 'A carregar...';
    try {
      const [limitsPayload, usersPayload] = await Promise.all([
        request('/api/approval-limits'),
        request('/api/approval-limits/users')
      ]);
      state.items = limitsPayload.items || [];
      state.users = usersPayload.items || [];
      render();
    } catch (error) {
      state.items = [];
      render();
      showAlert(error.message);
    } finally {
      state.loading = false;
      elements.refresh.disabled = false;
    }
  }

  function openEditor(item = null) {
    state.editingStamp = item ? item.stamp : '';
    elements.editorTitle.textContent = item ? 'Editar plafond' : 'Novo plafond';
    renderUsers(item ? item.usercode : '');
    elements.value.value = item ? item.plafond : '';
    elements.formError.hidden = true;
    elements.formError.textContent = '';
    elements.editor.classList.add('sz_is_open');
    elements.editor.setAttribute('aria-hidden', 'false');
    if (item) elements.value.focus();
    else elements.usercode.focus();
  }

  function closeEditor(force = false) {
    if (elements.save.disabled && !force) return;
    elements.editor.classList.remove('sz_is_open');
    elements.editor.setAttribute('aria-hidden', 'true');
    state.editingStamp = '';
    elements.form.reset();
  }

  async function save(event) {
    event.preventDefault();
    if (!elements.usercode.value || elements.value.value === '') {
      elements.form.reportValidity();
      return;
    }
    elements.save.disabled = true;
    elements.formError.hidden = true;
    try {
      const payload = await request(
        state.editingStamp
          ? `/api/approval-limits/${encodeURIComponent(state.editingStamp)}`
          : '/api/approval-limits',
        {
          method: state.editingStamp ? 'PUT' : 'POST',
          body: JSON.stringify({
            usercode: elements.usercode.value,
            plafond: elements.value.value
          })
        }
      );
      const existingIndex = state.items.findIndex((item) => item.stamp === payload.item.stamp);
      if (existingIndex >= 0) state.items.splice(existingIndex, 1, payload.item);
      else state.items.push(payload.item);
      state.items.sort((left, right) =>
        String(left.username || '').localeCompare(String(right.username || ''), 'pt-PT')
      );
      closeEditor(true);
      await load();
    } catch (error) {
      elements.formError.textContent = error.message;
      elements.formError.hidden = false;
    } finally {
      elements.save.disabled = false;
    }
  }

  function openDelete(item) {
    state.deletingStamp = item.stamp;
    elements.deleteText.textContent = `Pretende eliminar o plafond de ${item.username} (${item.usercode})?`;
    elements.deleteError.hidden = true;
    elements.deleteError.textContent = '';
    elements.deleteConfirm.classList.add('sz_is_open');
    elements.deleteConfirm.setAttribute('aria-hidden', 'false');
    elements.deleteApply.focus();
  }

  function closeDelete(force = false) {
    if (elements.deleteApply.disabled && !force) return;
    elements.deleteConfirm.classList.remove('sz_is_open');
    elements.deleteConfirm.setAttribute('aria-hidden', 'true');
    state.deletingStamp = '';
  }

  async function deleteItem() {
    if (!state.deletingStamp) return;
    elements.deleteApply.disabled = true;
    elements.deleteError.hidden = true;
    try {
      await request(`/api/approval-limits/${encodeURIComponent(state.deletingStamp)}`, {
        method: 'DELETE'
      });
      closeDelete(true);
      await load();
    } catch (error) {
      elements.deleteError.textContent = error.message;
      elements.deleteError.hidden = false;
    } finally {
      elements.deleteApply.disabled = false;
    }
  }

  function handleAction(event) {
    const button = event.target.closest('[data-action][data-stamp]');
    if (!button) return;
    const item = state.items.find((row) => row.stamp === button.dataset.stamp);
    if (!item) return;
    if (button.dataset.action === 'edit') openEditor(item);
    if (button.dataset.action === 'delete') openDelete(item);
  }

  elements.search.addEventListener('input', render);
  elements.refresh.addEventListener('click', load);
  elements.create.addEventListener('click', () => openEditor());
  elements.rows.addEventListener('click', handleAction);
  elements.mobileList.addEventListener('click', handleAction);
  elements.usercode.addEventListener('change', updateSelectedUsername);
  elements.form.addEventListener('submit', save);
  elements.deleteApply.addEventListener('click', deleteItem);
  root.querySelectorAll('[data-editor-close]').forEach((button) => button.addEventListener('click', closeEditor));
  root.querySelectorAll('[data-delete-close]').forEach((button) => button.addEventListener('click', closeDelete));
  elements.editor.addEventListener('click', (event) => {
    if (event.target === elements.editor) closeEditor();
  });
  elements.deleteConfirm.addEventListener('click', (event) => {
    if (event.target === elements.deleteConfirm) closeDelete();
  });
  document.addEventListener('keydown', (event) => {
    if (event.key !== 'Escape') return;
    if (elements.deleteConfirm.classList.contains('sz_is_open')) closeDelete();
    else if (elements.editor.classList.contains('sz_is_open')) closeEditor();
  });

  load();
})();
