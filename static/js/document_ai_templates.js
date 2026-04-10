document.addEventListener('DOMContentLoaded', () => {
  const els = {
    search: document.getElementById('docAiTemplateSearch'),
    newBtn: document.getElementById('docAiNewTemplateBtn'),
    docTypeFilter: document.getElementById('docAiTemplateDocTypeFilter'),
    activeFilter: document.getElementById('docAiTemplateActiveFilter'),
    list: document.getElementById('docAiTemplateList'),
    meta: document.getElementById('docAiTemplatesMeta'),
    editorMeta: document.getElementById('docAiTemplateEditorMeta'),
    toggleBtn: document.getElementById('docAiToggleTemplateBtn'),
    suggestBtn: document.getElementById('docAiSuggestTemplateBtn'),
    testBtn: document.getElementById('docAiTestTemplateBtn'),
    saveBtn: document.getElementById('docAiSaveTemplateBtn'),
    status: document.getElementById('docAiTemplateStatus'),
    tabs: Array.from(document.querySelectorAll('.docai-template-tab')),
    panes: Array.from(document.querySelectorAll('.docai-tab-pane')),
    name: document.getElementById('docAiTemplateName'),
    supplierNo: document.getElementById('docAiTemplateSupplierNo'),
    docType: document.getElementById('docAiTemplateDocType'),
    language: document.getElementById('docAiTemplateLanguage'),
    description: document.getElementById('docAiTemplateDescription'),
    parser: document.getElementById('docAiTemplateParser'),
    scoreMin: document.getElementById('docAiTemplateScoreMin'),
    fingerprint: document.getElementById('docAiTemplateFingerprint'),
    matchKeywords: document.getElementById('docAiMatchKeywords'),
    matchRequired: document.getElementById('docAiMatchRequired'),
    matchForbidden: document.getElementById('docAiMatchForbidden'),
    addFieldBtn: document.getElementById('docAiAddFieldBtn'),
    fieldsHost: document.getElementById('docAiTemplateFields'),
    linesEnabled: document.getElementById('docAiLinesEnabled'),
    linesHeaderAliases: document.getElementById('docAiLinesHeaderAliases'),
    linesStopKeywords: document.getElementById('docAiLinesStopKeywords'),
    advancedJson: document.getElementById('docAiAdvancedJson'),
    testModal: document.getElementById('docAiTemplateTestModal'),
    closeTestModalTop: document.getElementById('docAiCloseTestModalTop'),
    closeTestModal: document.getElementById('docAiCloseTestModal'),
    runTemplateTestBtn: document.getElementById('docAiRunTemplateTestBtn'),
    testDocument: document.getElementById('docAiTestDocument'),
    testResult: document.getElementById('docAiTestResult'),
  };

  const state = {
    templates: [],
    parsers: [],
    documents: [],
    llmAvailable: false,
    selectedId: '',
    current: null,
    fieldItems: [],
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
    if (!response.ok) {
      throw new Error(payload.error || `HTTP ${response.status}`);
    }
    return payload;
  }

  function populateStaticFilters() {
    const docTypes = state.templatesDocTypes || [];
    els.docTypeFilter.innerHTML = '<option value="">Todos</option>' + docTypes.map((item) => `<option value="${escapeHtml(item.value)}">${escapeHtml(item.label)}</option>`).join('');
    els.docType.innerHTML = docTypes.map((item) => `<option value="${escapeHtml(item.value)}">${escapeHtml(item.label)}</option>`).join('');
    els.parser.innerHTML = state.parsers.map((item) => `<option value="${escapeHtml(item.id)}">${escapeHtml(item.name)} · v${escapeHtml(item.version)}</option>`).join('');
    els.testDocument.innerHTML = '<option value="">Selecione...</option>' + state.documents.map((item) => (
      `<option value="${escapeHtml(item.DOCINSTAMP || item.docinstamp || item.DOCINSTAMP || item.docinstamp || item.DOCINSTAMP || item.docinstamp || item.docinstamp || item.DOCINSTAMP || item.docinstamp || item.docinstamp || item.DOCINSTAMP || item.docinstamp || item.docinstamp || item.DOCINSTAMP || item.DOCINSTAMP || item.docinstamp || item.DOCINSTAMP || item.docinstamp || item.docinstamp || item.DOCINSTAMP || item.docinstamp || item.DOCINSTAMP || item.docinstamp || item.docinstamp || item.DOCINSTAMP || item.DOCINSTAMP || item.DOCINSTAMP || item.docinstamp || item.docinstamp || item.docinstamp || item.DOCINSTAMP || '')}">${escapeHtml(item.FILE_NAME || item.file_name || '')}</option>`
    )).join('');
    els.testDocument.innerHTML = '<option value="">Selecione...</option>' + state.documents.map((item) => {
      const value = item.docinstamp || item.DOCINSTAMP || '';
      const label = item.file_name || item.FILE_NAME || value || 'Documento';
      return `<option value="${escapeHtml(value)}">${escapeHtml(label)}</option>`;
    }).join('');
  }

  function renderList() {
    if (!els.list) return;
    if (!state.templates.length) {
      els.list.innerHTML = '<div class="sz_text_muted">Sem templates para os filtros atuais.</div>';
      return;
    }
    els.list.innerHTML = state.templates.map((item) => `
      <button type="button" class="docai-template-item${state.selectedId === item.id ? ' is-active' : ''}" data-template-id="${escapeHtml(item.id)}">
        <div class="docai-template-item-top">
          <strong>${escapeHtml(item.name)}</strong>
          <span class="docai-state-badge ${item.active ? 'status-parsed_ok' : 'status-parse_error'}">${item.active ? 'Ativo' : 'Inativo'}</span>
        </div>
        <div class="sz_text_muted">${escapeHtml(item.supplier_name || (item.supplier_no ? `Fornecedor #${item.supplier_no}` : 'Template genérico'))}</div>
        <div class="sz_text_muted">${escapeHtml(item.doc_type || 'unknown')} · ${escapeHtml(item.parser?.name || '')}</div>
      </button>
    `).join('');
  }

  function buildDefaultField() {
    return {
      id: '',
      field_key: '',
      label: '',
      order: state.fieldItems.length + 1,
      required: false,
      match_mode: 'anchor_regex',
      anchors: [],
      regex: '',
      aliases: [],
      postprocess: '',
      config: {},
      active: true,
    };
  }

  function renderFields() {
    if (!els.fieldsHost) return;
    if (!state.fieldItems.length) {
      els.fieldsHost.innerHTML = '<div class="sz_text_muted">Sem campos configurados.</div>';
      return;
    }
    els.fieldsHost.innerHTML = state.fieldItems.map((field, index) => `
      <div class="docai-field-item" data-field-index="${index}">
        <div class="docai-field-item-grid">
          <div class="sz_field">
            <label class="sz_label">Field key</label>
            <input class="sz_input" data-prop="field_key" type="text" value="${escapeHtml(field.field_key || '')}">
          </div>
          <div class="sz_field">
            <label class="sz_label">Label</label>
            <input class="sz_input" data-prop="label" type="text" value="${escapeHtml(field.label || '')}">
          </div>
          <div class="sz_field">
            <label class="sz_label">Postprocess</label>
            <input class="sz_input" data-prop="postprocess" type="text" value="${escapeHtml(field.postprocess || '')}">
          </div>
          <div class="sz_field">
            <label class="sz_label">Anchors</label>
            <input class="sz_input" data-prop="anchors" type="text" value="${escapeHtml((field.anchors || []).join(', '))}">
          </div>
          <div class="sz_field">
            <label class="sz_label">Aliases</label>
            <input class="sz_input" data-prop="aliases" type="text" value="${escapeHtml((field.aliases || []).join(', '))}">
          </div>
          <div class="sz_field">
            <label class="sz_label">Regex</label>
            <input class="sz_input" data-prop="regex" type="text" value="${escapeHtml(field.regex || '')}">
          </div>
        </div>
        <div class="docai-row-actions" style="margin-top: var(--sz-space-2);">
          <button type="button" class="sz_button sz_button_ghost" data-action="required">${field.required ? 'Obrigatório' : 'Opcional'}</button>
          <button type="button" class="sz_button sz_button_ghost" data-action="remove"><i class="fa-solid fa-trash"></i></button>
        </div>
      </div>
    `).join('');
  }

  function setActiveTab(tabName) {
    els.tabs.forEach((button) => {
      const active = button.dataset.tab === tabName;
      button.classList.toggle('is-active', active);
      button.classList.toggle('sz_button_secondary', active);
      button.classList.toggle('sz_button_ghost', !active);
    });
    els.panes.forEach((pane) => {
      pane.classList.toggle('is-active', pane.id === `docAiTab${tabName.charAt(0).toUpperCase()}${tabName.slice(1)}`);
    });
  }

  function syncAdvancedJson() {
    if (!els.advancedJson) return;
    try {
      els.advancedJson.value = JSON.stringify(currentPayload().definition_json, null, 2);
    } catch (_) {}
  }

  function applyTemplateToEditor(template) {
    state.current = template;
    state.selectedId = template?.id || '';
    state.fieldItems = Array.isArray(template?.fields) ? template.fields.map((item) => ({
      ...buildDefaultField(),
      ...item,
      anchors: Array.isArray(item.anchors) ? item.anchors : [],
      aliases: Array.isArray(item.aliases) ? item.aliases : [],
    })) : [];
    if (els.name) els.name.value = template?.name || '';
    if (els.supplierNo) els.supplierNo.value = template?.supplier_no || '';
    if (els.docType) els.docType.value = template?.doc_type || 'unknown';
    if (els.language) els.language.value = template?.language || '';
    if (els.description) els.description.value = template?.description || '';
    if (els.parser) els.parser.value = template?.parser_id || state.parsers[0]?.id || '';
    if (els.scoreMin) els.scoreMin.value = template?.score_min_match ?? 0.55;
    if (els.fingerprint) els.fingerprint.value = template?.fingerprint || '';
    if (els.matchKeywords) els.matchKeywords.value = (template?.match_rules?.keywords || []).join(', ');
    if (els.matchRequired) els.matchRequired.value = (template?.match_rules?.required || []).join(', ');
    if (els.matchForbidden) els.matchForbidden.value = (template?.match_rules?.forbidden || []).join(', ');
    if (els.linesEnabled) els.linesEnabled.value = template?.definition?.lines?.enabled === false ? '0' : '1';
    if (els.linesHeaderAliases) els.linesHeaderAliases.value = (template?.definition?.lines?.header_aliases || []).join(', ');
    if (els.linesStopKeywords) els.linesStopKeywords.value = (template?.definition?.lines?.stop_keywords || []).join(', ');
    renderFields();
    syncAdvancedJson();
    renderList();
    if (els.editorMeta) els.editorMeta.textContent = template?.name ? `Editar ${template.name}` : 'Novo template';
  }

  function blankTemplate() {
    return {
      id: '',
      name: '',
      description: '',
      supplier_no: null,
      doc_type: 'unknown',
      language: '',
      parser_id: state.parsers[0]?.id || '',
      score_min_match: 0.55,
      fingerprint: '',
      match_rules: { keywords: [], required: [], forbidden: [] },
      definition: { lines: { enabled: true, header_aliases: ['ref', 'description', 'qty', 'price'], stop_keywords: ['total', 'subtotal', 'iva'] } },
      fields: [],
    };
  }

  function currentPayload() {
    let advanced = null;
    try {
      advanced = JSON.parse(els.advancedJson.value || '{}');
    } catch (_) {}
    const fields = state.fieldItems.map((field, index) => ({
      ...field,
      order: index + 1,
      anchors: Array.isArray(field.anchors) ? field.anchors : String(field.anchors || '').split(',').map((item) => item.trim()).filter(Boolean),
      aliases: Array.isArray(field.aliases) ? field.aliases : String(field.aliases || '').split(',').map((item) => item.trim()).filter(Boolean),
    }));
    const payload = {
      id: state.selectedId || '',
      name: els.name.value || 'Novo template',
      supplier_no: Number(els.supplierNo.value || 0) || null,
      doc_type: els.docType.value || 'unknown',
      language: els.language.value || '',
      description: els.description.value || '',
      parser_id: els.parser.value || '',
      score_min_match: Number(els.scoreMin.value || 0.55) || 0.55,
      fingerprint: els.fingerprint.value || '',
      match_rules: {
        keywords: els.matchKeywords.value.split(',').map((item) => item.trim()).filter(Boolean),
        required: els.matchRequired.value.split(',').map((item) => item.trim()).filter(Boolean),
        forbidden: els.matchForbidden.value.split(',').map((item) => item.trim()).filter(Boolean),
      },
      lines: {
        enabled: els.linesEnabled.value !== '0',
        header_aliases: els.linesHeaderAliases.value.split(',').map((item) => item.trim()).filter(Boolean),
        stop_keywords: els.linesStopKeywords.value.split(',').map((item) => item.trim()).filter(Boolean),
      },
      fields,
    };
    payload.definition_json = advanced && typeof advanced === 'object' ? advanced : {
      doc_type: payload.doc_type,
      match: payload.match_rules,
      fields: Object.fromEntries(fields.map((field) => [field.field_key, {
        anchors: field.anchors,
        regex: field.regex || '',
        aliases: field.aliases,
        required: !!field.required,
        postprocess: field.postprocess || '',
        config: field.config || {},
        match_mode: field.match_mode || 'anchor_regex',
      }])),
      lines: payload.lines,
    };
    return payload;
  }

  async function loadTemplates() {
    setStatus('A carregar templates...');
    try {
      const params = new URLSearchParams();
      if (els.search?.value.trim()) params.set('search', els.search.value.trim());
      if (els.docTypeFilter?.value) params.set('doc_type', els.docTypeFilter.value);
      if (els.activeFilter?.value) params.set('active', els.activeFilter.value);
      const payload = await fetchJson(`/api/document_ai/templates?${params.toString()}`);
      state.templates = Array.isArray(payload.items) ? payload.items : [];
      state.parsers = Array.isArray(payload.parsers) ? payload.parsers : [];
      state.documents = Array.isArray(payload.documents) ? payload.documents : [];
      state.templatesDocTypes = Array.isArray(payload.doc_types) ? payload.doc_types : [];
      state.llmAvailable = !!payload.llm?.available;
      populateStaticFilters();
      renderList();
      els.suggestBtn.disabled = !state.llmAvailable;
      if (els.meta) els.meta.textContent = `${state.templates.length} template(s) carregado(s).`;
      if (!state.selectedId) {
        applyTemplateToEditor(blankTemplate());
      }
      setStatus('Templates carregados.');
    } catch (error) {
      console.error(error);
      showMessage(error.message || 'Erro ao carregar templates.', 'error');
      setStatus(error.message || 'Erro ao carregar.', true);
    }
  }

  async function selectTemplate(id) {
    if (!id) {
      applyTemplateToEditor(blankTemplate());
      return;
    }
    setStatus('A carregar template...');
    try {
      const payload = await fetchJson(`/api/document_ai/templates/${encodeURIComponent(id)}`);
      applyTemplateToEditor(payload);
      setStatus('Template carregado.');
    } catch (error) {
      console.error(error);
      showMessage(error.message || 'Erro ao carregar template.', 'error');
      setStatus(error.message || 'Erro ao carregar template.', true);
    }
  }

  async function saveCurrentTemplate() {
    const payload = currentPayload();
    setStatus('A guardar template...');
    try {
      const saved = await fetchJson(payload.id ? `/api/document_ai/templates/${encodeURIComponent(payload.id)}` : '/api/document_ai/templates', {
        method: payload.id ? 'PUT' : 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      showMessage('Template guardado.', 'success');
      state.selectedId = saved.id;
      await loadTemplates();
      await selectTemplate(saved.id);
      setStatus('Template guardado.');
    } catch (error) {
      console.error(error);
      showMessage(error.message || 'Falha ao guardar template.', 'error');
      setStatus(error.message || 'Falha ao guardar template.', true);
    }
  }

  function applySuggestedTemplate(suggestion) {
    if (!suggestion || typeof suggestion !== 'object') return;
    const template = {
      ...blankTemplate(),
      ...state.current,
      name: suggestion.name || state.current?.name || '',
      fingerprint: suggestion.fingerprint || state.current?.fingerprint || '',
      doc_type: suggestion.doc_type || state.current?.doc_type || 'unknown',
      score_min_match: Number(suggestion.score_min_match || state.current?.score_min_match || 0.55) || 0.55,
      match_rules: suggestion.match_rules || state.current?.match_rules || { keywords: [], required: [], forbidden: [] },
      definition: {
        ...(state.current?.definition || {}),
        lines: suggestion.lines || state.current?.definition?.lines || { enabled: true, header_aliases: [], stop_keywords: [] },
      },
      fields: Array.isArray(suggestion.fields) ? suggestion.fields.map((field, index) => ({
        ...buildDefaultField(),
        field_key: field.field_key || '',
        label: field.label || field.field_key || '',
        order: index + 1,
        required: !!field.required,
        anchors: Array.isArray(field.anchors) ? field.anchors : [],
        regex: field.regex || '',
        aliases: Array.isArray(field.aliases) ? field.aliases : [],
        postprocess: field.postprocess || '',
      })).filter((field) => field.field_key) : (state.current?.fields || []),
    };
    applyTemplateToEditor(template);
  }

  async function suggestTemplateDefinition() {
    setStatus('A gerar sugestão automática...');
    try {
      let documentContext = {};
      const documentId = String(els.testDocument?.value || '').trim();
      if (documentId) {
        const detail = await fetchJson(`/api/document_ai/documents/${encodeURIComponent(documentId)}`);
        documentContext = {
          file_name: detail.file_name || '',
          extracted_text: detail.extracted_text || '',
          supplier_name: detail.supplier_name || '',
          supplier_no: detail.supplier_no,
          current_result: detail.result || {},
        };
      }
      const payload = await fetchJson('/api/document_ai/suggest', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ...documentContext,
          document_type: els.docType.value || 'unknown',
          supplier_no: Number(els.supplierNo.value || 0) || documentContext.supplier_no || null,
          supplier_name: documentContext.supplier_name || '',
          current_template: currentPayload(),
        }),
      });
      if (!payload.ok || !payload.suggestion) {
        throw new Error(payload.message || 'A sugestão automática não devolveu conteúdo utilizável.');
      }
      applySuggestedTemplate(payload.suggestion);
      showMessage(payload.message || 'Sugestão automática aplicada.', 'success');
      setStatus(payload.message || 'Sugestão automática aplicada.');
    } catch (error) {
      console.error(error);
      showMessage(error.message || 'Falha na sugestão automática.', 'error');
      setStatus(error.message || 'Falha na sugestão automática.', true);
    }
  }

  async function toggleTemplate() {
    if (!state.selectedId) {
      showMessage('Seleciona primeiro um template.', 'warning');
      return;
    }
    try {
      await fetchJson(`/api/document_ai/templates/${encodeURIComponent(state.selectedId)}/toggle`, { method: 'POST' });
      await loadTemplates();
      await selectTemplate(state.selectedId);
      showMessage('Estado do template atualizado.', 'success');
    } catch (error) {
      console.error(error);
      showMessage(error.message || 'Falha ao alterar estado.', 'error');
    }
  }

  async function runTemplateTest() {
    if (!state.selectedId) {
      showMessage('Seleciona primeiro um template.', 'warning');
      return;
    }
    if (!els.testDocument.value) {
      showMessage('Seleciona um documento para teste.', 'warning');
      return;
    }
    try {
      const payload = await fetchJson(`/api/document_ai/templates/${encodeURIComponent(state.selectedId)}/test`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ document_id: els.testDocument.value }),
      });
      els.testResult.value = JSON.stringify(payload, null, 2);
      showMessage('Teste executado.', 'success');
    } catch (error) {
      console.error(error);
      showMessage(error.message || 'Falha ao testar template.', 'error');
    }
  }

  function openTestModal() {
    els.testModal?.classList.add('is-open');
  }

  function closeTestModal() {
    els.testModal?.classList.remove('is-open');
  }

  els.tabs.forEach((button) => button.addEventListener('click', () => setActiveTab(button.dataset.tab || 'identification')));
  els.newBtn?.addEventListener('click', () => {
    state.selectedId = '';
    applyTemplateToEditor(blankTemplate());
  });
  els.search?.addEventListener('change', loadTemplates);
  els.docTypeFilter?.addEventListener('change', loadTemplates);
  els.activeFilter?.addEventListener('change', loadTemplates);
  els.saveBtn?.addEventListener('click', saveCurrentTemplate);
  els.suggestBtn?.addEventListener('click', suggestTemplateDefinition);
  els.toggleBtn?.addEventListener('click', toggleTemplate);
  els.testBtn?.addEventListener('click', openTestModal);
  els.closeTestModal?.addEventListener('click', closeTestModal);
  els.closeTestModalTop?.addEventListener('click', closeTestModal);
  els.runTemplateTestBtn?.addEventListener('click', runTemplateTest);
  els.addFieldBtn?.addEventListener('click', () => {
    state.fieldItems.push(buildDefaultField());
    renderFields();
    syncAdvancedJson();
  });
  els.fieldsHost?.addEventListener('input', (event) => {
    const container = event.target.closest('[data-field-index]');
    if (!container) return;
    const index = Number(container.dataset.fieldIndex || 0);
    const prop = event.target.dataset.prop;
    if (!prop || !state.fieldItems[index]) return;
    if (prop === 'anchors' || prop === 'aliases') {
      state.fieldItems[index][prop] = event.target.value.split(',').map((item) => item.trim()).filter(Boolean);
    } else {
      state.fieldItems[index][prop] = event.target.value;
    }
    syncAdvancedJson();
  });
  els.fieldsHost?.addEventListener('click', (event) => {
    const container = event.target.closest('[data-field-index]');
    if (!container) return;
    const index = Number(container.dataset.fieldIndex || 0);
    const button = event.target.closest('button[data-action]');
    if (!button || !state.fieldItems[index]) return;
    if (button.dataset.action === 'remove') {
      state.fieldItems.splice(index, 1);
      renderFields();
      syncAdvancedJson();
      return;
    }
    if (button.dataset.action === 'required') {
      state.fieldItems[index].required = !state.fieldItems[index].required;
      renderFields();
      syncAdvancedJson();
    }
  });
  [
    els.name, els.supplierNo, els.docType, els.language, els.description, els.parser,
    els.scoreMin, els.fingerprint, els.matchKeywords, els.matchRequired, els.matchForbidden,
    els.linesEnabled, els.linesHeaderAliases, els.linesStopKeywords,
  ].forEach((input) => input?.addEventListener('input', syncAdvancedJson));
  els.list?.addEventListener('click', (event) => {
    const button = event.target.closest('[data-template-id]');
    if (!button) return;
    selectTemplate(button.dataset.templateId || '');
  });

  loadTemplates();
});
