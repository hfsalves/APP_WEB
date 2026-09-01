document.addEventListener('DOMContentLoaded', () => {
  const els = {
    panel: document.getElementById('docAiRequiredSettingsPanel'),
    groups: document.getElementById('docAiRequiredGroups'),
    add: document.getElementById('docAiRequiredAddBtn'),
    modal: document.getElementById('docAiRequiredModal'),
    title: document.getElementById('docAiRequiredTitle'),
    closeTop: document.getElementById('docAiRequiredCloseTop'),
    cancel: document.getElementById('docAiRequiredCancel'),
    save: document.getElementById('docAiRequiredSave'),
    docClass: document.getElementById('docAiRequiredClass'),
    view: document.getElementById('docAiRequiredView'),
    field: document.getElementById('docAiRequiredField'),
  };
  if (!els.panel || !els.modal) return;

  let config = null;
  let editing = null;
  const escapeHtml = (value) => String(value == null ? '' : value).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  const showMessage = (message, type = 'info') => typeof window.showToast === 'function' ? window.showToast(message, type) : window.alert(message);
  const label = (items, value) => items?.find((item) => item.value === value)?.label || value;

  async function fetchJson(url, options = {}) {
    const response = await fetch(url, options);
    let payload = {};
    try { payload = await response.json(); } catch (_) {}
    if (!response.ok) throw new Error(payload.error || `HTTP ${response.status}`);
    return payload;
  }

  async function load() {
    els.groups.innerHTML = '<p class="sz_text_muted">A carregar informações...</p>';
    try {
      config = await fetchJson('/api/document_ai/required-info');
      render();
    } catch (error) {
      els.groups.innerHTML = `<p class="sz_text_muted">${escapeHtml(error.message)}</p>`;
    }
  }

  function render() {
    const groups = new Map();
    config.rules.forEach((rule) => {
      if (!groups.has(rule.doc_class)) groups.set(rule.doc_class, []);
      groups.get(rule.doc_class).push(rule);
    });
    const ordered = [...groups.entries()].sort((a, b) => label(config.classifications, a[0]).localeCompare(label(config.classifications, b[0]), 'pt'));
    els.groups.innerHTML = ordered.map(([docClass, rules]) => `
      <section class="docai-distribution-group">
        <h4>${escapeHtml(label(config.classifications, docClass))}</h4>
        <table class="docai-distribution-table is-required">
          <thead><tr><th>Origem</th><th>Informação Obrigatória</th><th>Ação</th></tr></thead>
          <tbody>${rules.sort((a, b) => `${label(config.views, a.view)}:${label(config.fields, a.field)}`.localeCompare(`${label(config.views, b.view)}:${label(config.fields, b.field)}`, 'pt')).map((rule) => `
            <tr>
              <td><button type="button" class="docai-distribution-cell" data-edit-required="${escapeHtml(rule.id)}">${escapeHtml(label(config.views, rule.view))}</button></td>
              <td><button type="button" class="docai-distribution-cell" data-edit-required="${escapeHtml(rule.id)}">${escapeHtml(label(config.fields, rule.field))}</button></td>
              <td><button type="button" class="sz_button sz_button_ghost docai-access-remove" data-delete-required="${escapeHtml(rule.id)}" title="Eliminar" aria-label="Eliminar"><i class="fa-solid fa-trash"></i></button></td>
            </tr>`).join('')}</tbody>
        </table>
      </section>`).join('') || '<p class="sz_text_muted">Sem informações obrigatórias configuradas.</p>';
  }

  function options(select, items, selected) {
    select.innerHTML = (items || []).map((item) => `<option value="${escapeHtml(item.value)}" ${item.value === selected ? 'selected' : ''}>${escapeHtml(item.label)}</option>`).join('');
  }

  function compatibleFields() {
    const view = els.view.value;
    const docClass = els.docClass.value;
    const values = config.fields.filter((item) => (item.views || []).includes(view) && (item.value !== 'supplier_resolved' || docClass === 'advertising'));
    const selected = values.some((item) => item.value === els.field.value) ? els.field.value : (editing?.field || values[0]?.value);
    options(els.field, values, selected);
  }

  function openModal(rule = null) {
    editing = rule;
    options(els.docClass, config.classifications, rule?.doc_class || config.classifications[0]?.value);
    options(els.view, config.views, rule?.view || 'home');
    compatibleFields();
    if (rule) els.field.value = rule.field;
    els.title.textContent = rule ? 'Alterar informação' : 'Adicionar informação';
    els.save.querySelector('span').textContent = rule ? 'Guardar informação' : 'Adicionar informação';
    els.modal.hidden = false;
    els.modal.classList.add('sz_is_open');
  }

  function closeModal() {
    els.modal.classList.remove('sz_is_open');
    els.modal.hidden = true;
    editing = null;
  }

  async function save() {
    els.save.disabled = true;
    try {
      const wasEditing = Boolean(editing);
      config = await fetchJson('/api/document_ai/required-info', {
        method: editing ? 'PUT' : 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id: editing?.id || '', doc_class: els.docClass.value, view: els.view.value, field: els.field.value }),
      });
      render(); closeModal(); showMessage(wasEditing ? 'Informação atualizada!' : 'Informação adicionada!', 'success');
    } catch (error) {
      showMessage(error.message, 'error');
    } finally { els.save.disabled = false; }
  }

  async function remove(ruleId) {
    if (!window.confirm('Eliminar esta informação obrigatória?')) return;
    try {
      config = await fetchJson(`/api/document_ai/required-info/${encodeURIComponent(ruleId)}`, { method: 'DELETE' });
      render(); showMessage('Informação eliminada.', 'success');
    } catch (error) { showMessage(error.message, 'error'); }
  }

  document.addEventListener('docai:settings-tab', (event) => {
    if (event.detail?.tab === 'required' && !config) load();
  });
  els.add.addEventListener('click', () => openModal());
  els.closeTop.addEventListener('click', closeModal);
  els.cancel.addEventListener('click', closeModal);
  els.save.addEventListener('click', save);
  els.modal.addEventListener('click', (event) => { if (event.target === els.modal) closeModal(); });
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && !els.modal.hidden) closeModal();
  });
  els.view.addEventListener('change', compatibleFields);
  els.docClass.addEventListener('change', compatibleFields);
  els.groups.addEventListener('click', (event) => {
    const editId = event.target.closest('[data-edit-required]')?.dataset.editRequired;
    if (editId) { const rule = config.rules.find((item) => item.id === editId); if (rule) openModal(rule); return; }
    const deleteId = event.target.closest('[data-delete-required]')?.dataset.deleteRequired;
    if (deleteId) remove(deleteId);
  });
});
