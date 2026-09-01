document.addEventListener('DOMContentLoaded', () => {
  const els = {
    settingsModal: document.getElementById('docAiAccessModal'),
    tabs: Array.from(document.querySelectorAll('[data-settings-tab]')),
    accessPanel: document.getElementById('docAiAccessSettingsPanel'),
    requiredPanel: document.getElementById('docAiRequiredSettingsPanel'),
    distributionPanel: document.getElementById('docAiDistributionSettingsPanel'),
    accessSave: document.getElementById('docAiAccessSave'),
    add: document.getElementById('docAiDistributionAddBtn'),
    groups: document.getElementById('docAiDistributionGroups'),
    modal: document.getElementById('docAiDistributionModal'),
    title: document.getElementById('docAiDistributionTitle'),
    closeTop: document.getElementById('docAiDistributionCloseTop'),
    cancel: document.getElementById('docAiDistributionCancel'),
    save: document.getElementById('docAiDistributionSave'),
    docClass: document.getElementById('docAiDistributionClass'),
    source: document.getElementById('docAiDistributionSource'),
    destination: document.getElementById('docAiDistributionDestination'),
    state: document.getElementById('docAiDistributionState'),
    applyExisting: document.getElementById('docAiDistributionApplyExisting'),
  };
  if (!els.settingsModal || !els.distributionPanel || !els.modal) return;

  let config = null;
  let editingRule = null;
  const escapeHtml = (value) => String(value == null ? '' : value).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  const showMessage = (message, type = 'info') => typeof window.showToast === 'function' ? window.showToast(message, type) : window.alert(message);
  const label = (items, value, fallback = value) => items?.find((item) => item.value === value)?.label || fallback;

  async function fetchJson(url, options = {}) {
    const response = await fetch(url, options);
    let payload = {};
    try { payload = await response.json(); } catch (_) {}
    if (!response.ok) throw new Error(payload.error || `HTTP ${response.status}`);
    return payload;
  }

  async function loadDistribution() {
    els.groups.innerHTML = '<p class="sz_text_muted">A carregar distribuições...</p>';
    try {
      config = await fetchJson('/api/document_ai/distribution-configuration');
      render();
    } catch (error) {
      els.groups.innerHTML = `<p class="sz_text_muted">${escapeHtml(error.message)}</p>`;
    }
  }

  function render() {
    if (!config) return;
    const groups = new Map();
    config.rules.forEach((rule) => {
      if (!groups.has(rule.doc_class)) groups.set(rule.doc_class, []);
      groups.get(rule.doc_class).push(rule);
    });
    const ordered = [...groups.entries()].sort((left, right) => (
      label(config.classifications, left[0]).localeCompare(label(config.classifications, right[0]), 'pt')
    ));
    els.groups.innerHTML = ordered.map(([docClass, rules]) => `
      <section class="docai-distribution-group">
        <h4>${escapeHtml(label(config.classifications, docClass))}</h4>
        <table class="docai-distribution-table is-distribution">
          <thead><tr><th>Origem</th><th>Destino</th><th>Estado</th><th>Ação</th></tr></thead>
          <tbody>${rules.sort((a, b) => `${a.source}:${a.destination}`.localeCompare(`${b.source}:${b.destination}`)).map((rule) => `
            <tr>
              <td><button type="button" class="docai-distribution-cell" data-edit-rule="${escapeHtml(rule.id)}">${escapeHtml(label(config.views, rule.source))}</button></td>
              <td><button type="button" class="docai-distribution-cell" data-edit-rule="${escapeHtml(rule.id)}">${escapeHtml(rule.terminal ? 's/Destino' : label(config.views, rule.destination))}</button></td>
              <td><button type="button" class="docai-distribution-cell docai-distribution-state" data-state="${escapeHtml(rule.state)}" data-edit-rule="${escapeHtml(rule.id)}">${escapeHtml(label(config.states, rule.state, '-'))}</button></td>
              <td><button type="button" class="sz_button sz_button_ghost docai-access-remove" data-delete-rule="${escapeHtml(rule.id)}" title="Eliminar" aria-label="Eliminar"><i class="fa-solid fa-trash"></i></button></td>
            </tr>`).join('')}</tbody>
        </table>
      </section>
    `).join('') || '<p class="sz_text_muted">Sem distribuições configuradas.</p>';
  }

  function setOptions(select, items, selected, extra = []) {
    select.innerHTML = [...extra, ...(items || [])].map((item) => `<option value="${escapeHtml(item.value)}" ${item.value === selected ? 'selected' : ''}>${escapeHtml(item.label)}</option>`).join('');
  }

  function constrainState() {
    const destination = els.destination.value;
    const docClass = els.docClass.value;
    let allowed = config.states;
    if (!destination) allowed = config.states.filter((item) => item.value === 'none');
    else if (destination === 'management') allowed = config.states.filter((item) => item.value === 'automatic');
    else if (destination === 'accounting' && docClass === 'invoice') allowed = config.states.filter((item) => ['pending', 'validated'].includes(item.value));
    else if (destination === 'accounting' && docClass === 'credit_note') allowed = config.states.filter((item) => item.value === 'none');
    const current = allowed.some((item) => item.value === els.state.value) ? els.state.value : allowed[0]?.value;
    setOptions(els.state, allowed, current);
  }

  function openRuleModal(rule = null) {
    if (!config) return;
    editingRule = rule;
    setOptions(els.docClass, config.classifications, rule?.doc_class || config.classifications[0]?.value);
    setOptions(els.source, config.views, rule?.source || 'home');
    setOptions(els.destination, config.views, rule?.terminal ? '' : (rule?.destination || ''), [{ value: '', label: 's/Destino' }]);
    setOptions(els.state, config.states, rule?.state || 'none');
    constrainState();
    els.applyExisting.checked = false;
    els.title.textContent = rule ? 'Alterar distribuição' : 'Adicionar distribuição';
    els.save.querySelector('span').textContent = rule ? 'Guardar distribuição' : 'Adicionar distribuição';
    els.modal.hidden = false;
    els.modal.classList.add('sz_is_open');
  }

  function closeRuleModal() { els.modal.classList.remove('sz_is_open'); els.modal.hidden = true; editingRule = null; }

  async function saveRule() {
    const wasEditing = Boolean(editingRule);
    els.save.disabled = true;
    try {
      const payload = {
        id: editingRule?.id || '',
        doc_class: els.docClass.value,
        source: els.source.value,
        destination: els.destination.value,
        terminal: !els.destination.value,
        state: els.state.value,
        apply_to_existing: els.applyExisting.checked,
      };
      if (payload.apply_to_existing) {
        const impact = await fetchJson('/api/document_ai/distribution-configuration/impact', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });
        const count = Number(impact.documents || 0);
        if (!window.confirm(`Aplicar esta distribuição a ${count} documento${count === 1 ? '' : 's'} já validado${count === 1 ? '' : 's'}? As etapas concluídas não serão reabertas.`)) return;
      }
      config = await fetchJson('/api/document_ai/distribution-configuration', {
        method: editingRule ? 'PUT' : 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      const retroactive = config.retroactive;
      render(); closeRuleModal();
      const baseMessage = wasEditing ? 'Distribuição atualizada!' : 'Distribuição adicionada!';
      showMessage(retroactive ? `${baseMessage} ${retroactive.applied || 0} documento(s) atualizado(s).` : baseMessage, 'success');
    } catch (error) {
      showMessage(error.message, 'error');
    } finally { els.save.disabled = false; }
  }

  async function deleteRule(ruleId) {
    if (!window.confirm('Eliminar esta distribuição?')) return;
    try {
      config = await fetchJson(`/api/document_ai/distribution-configuration/${encodeURIComponent(ruleId)}`, { method: 'DELETE' });
      render(); showMessage('Distribuição eliminada.', 'success');
    } catch (error) { showMessage(error.message, 'error'); }
  }

  function selectSettingsTab(tabName) {
    els.accessPanel.hidden = tabName !== 'access';
    if (els.requiredPanel) els.requiredPanel.hidden = tabName !== 'required';
    els.distributionPanel.hidden = tabName !== 'distribution';
    els.accessSave.hidden = tabName !== 'access';
    els.tabs.forEach((tab) => {
      const selected = tab.dataset.settingsTab === tabName;
      tab.classList.toggle('is-active', selected);
      tab.setAttribute('aria-selected', selected ? 'true' : 'false');
    });
    if (tabName === 'distribution' && !config) loadDistribution();
    document.dispatchEvent(new CustomEvent('docai:settings-tab', { detail: { tab: tabName } }));
  }

  els.tabs.forEach((tab) => tab.addEventListener('click', () => selectSettingsTab(tab.dataset.settingsTab)));
  document.getElementById('docAiAccessAdminBtn')?.addEventListener('click', () => selectSettingsTab('access'));
  els.add.addEventListener('click', () => openRuleModal());
  els.closeTop.addEventListener('click', closeRuleModal);
  els.cancel.addEventListener('click', closeRuleModal);
  els.save.addEventListener('click', saveRule);
  els.modal.addEventListener('click', (event) => { if (event.target === els.modal) closeRuleModal(); });
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && !els.modal.hidden) closeRuleModal();
  });
  els.destination.addEventListener('change', constrainState);
  els.docClass.addEventListener('change', constrainState);
  els.groups.addEventListener('click', (event) => {
    const editId = event.target.closest('[data-edit-rule]')?.dataset.editRule;
    if (editId) { const rule = config.rules.find((item) => item.id === editId); if (rule) openRuleModal(rule); return; }
    const deleteId = event.target.closest('[data-delete-rule]')?.dataset.deleteRule;
    if (deleteId) deleteRule(deleteId);
  });
});
