(() => {
  const root = document.getElementById('amenitiesApp');
  if (!root) return;

  const $ = (id) => document.getElementById(id);
  const els = {
    reload: $('amenitiesReload'), manage: $('amenitiesManage'), search: $('amenitiesSearch'),
    category: $('amenitiesCategory'), zone: $('amenitiesZone'), summary: $('amenitiesSummary'),
    status: $('amenitiesStatus'), wrap: $('amenitiesMatrixWrap'), head: $('amenitiesMatrixHead'), body: $('amenitiesMatrixBody'),
    dialog: $('amenitiesDialog'), dialogClose: $('amenitiesDialogClose'), catalogBody: $('amenitiesCatalogBody'),
    catalogEmpty: $('amenitiesCatalogEmpty'), catalogSearch: $('catalogSearch'), catalogCategory: $('catalogCategory'),
    catalogActive: $('catalogActive'), catalogPortal: $('catalogPortal'), newButton: $('amenityNew'),
    form: $('amenityForm'), formClose: $('amenityFormClose'), cancel: $('amenityCancel'), save: $('amenitySave'),
    formMode: $('amenityFormMode'), formTitle: $('amenityFormTitle'), formError: $('amenityFormError'),
    id: $('amenityId'), code: $('amenityCode'), pt: $('amenityPt'), en: $('amenityEn'), es: $('amenityEs'), fr: $('amenityFr'),
    editorCategory: $('amenityCategory'), order: $('amenityOrder'), icon: $('amenityIcon'), iconButton: $('amenityIconButton'),
    iconPicker: $('amenityIconPicker'), iconPreview: $('amenityIconPreview'), iconName: $('amenityIconName'),
    active: $('amenityActive'), show: $('amenityShow'), filter: $('amenityFilter'), toast: $('amenitiesToast'),
  };

  const state = { properties: [], amenities: [], relations: new Set(), categories: [], icons: [], zones: [], canEdit: false };
  const esc = (value) => String(value ?? '').replace(/[&<>'"]/g, (char) => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[char]));
  const relationKey = (propertyName, amenityId) => `${propertyName}\u0001${amenityId}`;
  const categoryLabel = (code) => state.categories.find((item) => item.code === code)?.label || code;

  function toast(message, error = false) {
    els.toast.textContent = message;
    els.toast.classList.toggle('is-error', error);
    els.toast.hidden = false;
    clearTimeout(toast.timer);
    toast.timer = setTimeout(() => { els.toast.hidden = true; }, 3200);
  }

  async function request(url, options = {}) {
    const response = await fetch(url, { headers: {'Content-Type': 'application/json'}, ...options });
    const data = await response.json().catch(() => ({}));
    if (!response.ok || data.ok === false) throw new Error(data.error || 'Ocorreu um erro inesperado.');
    return data;
  }

  function fillSelect(select, items, placeholder, valueKey = 'code', labelKey = 'label') {
    const current = select.value;
    select.innerHTML = `<option value="">${esc(placeholder)}</option>` + items.map((item) => `<option value="${esc(typeof item === 'string' ? item : item[valueKey])}">${esc(typeof item === 'string' ? item : item[labelKey])}</option>`).join('');
    if ([...select.options].some((option) => option.value === current)) select.value = current;
  }

  function activeAmenities() {
    const category = els.category.value;
    return state.amenities.filter((item) => Number(item.ativa) === 1 && (!category || item.categoria === category));
  }

  function visibleProperties() {
    const term = els.search.value.trim().toLocaleLowerCase('pt');
    const zone = els.zone.value;
    return state.properties.filter((item) => (!term || item.NOME.toLocaleLowerCase('pt').includes(term)) && (!zone || String(item.ZONA || '') === zone));
  }

  function renderMatrix() {
    const amenities = activeAmenities();
    const properties = visibleProperties();
    const groups = [];
    amenities.forEach((amenity) => {
      let group = groups.find((item) => item.code === amenity.categoria);
      if (!group) { group = {code: amenity.categoria, items: []}; groups.push(group); }
      group.items.push(amenity);
    });
    els.head.innerHTML = `<tr><th class="amenities-property-column" rowspan="2">Alojamento</th>${groups.map((group) => `<th colspan="${group.items.length}">${esc(categoryLabel(group.code))}</th>`).join('')}</tr><tr>${amenities.map((item) => `
      <th title="${esc(item.nome_pt)}">
        <div class="amenities-column-head"><i class="fa-solid ${esc(item.icone)}"></i><span>${esc(item.nome_pt)}</span>
          ${state.canEdit ? `<div class="amenities-column-actions"><button type="button" data-bulk="1" data-id="${item.id}" title="Marcar nos alojamentos visíveis" aria-label="Marcar ${esc(item.nome_pt)} em todos os alojamentos visíveis"><i class="fa-solid fa-check"></i></button><button type="button" data-bulk="0" data-id="${item.id}" title="Desmarcar nos alojamentos visíveis" aria-label="Desmarcar ${esc(item.nome_pt)} em todos os alojamentos visíveis"><i class="fa-solid fa-minus"></i></button></div>` : ''}
        </div>
      </th>`).join('')}</tr>`;
    els.body.innerHTML = properties.length && amenities.length ? properties.map((property) => `<tr data-property="${esc(property.NOME)}">
      <td class="amenities-property-column"><span class="amenities-property-name" title="${esc(property.NOME)}">${esc(property.NOME)}</span><span class="amenities-property-meta">${esc([property.ZONA, property.LOCAL].filter(Boolean).join(' · '))}</span></td>
      ${amenities.map((item) => { const checked = state.relations.has(relationKey(property.NOME, item.id)); return `<td><label class="amenities-check"><input type="checkbox" data-property="${esc(property.NOME)}" data-id="${item.id}" ${checked ? 'checked' : ''} ${state.canEdit ? '' : 'disabled'} aria-label="${esc(property.NOME)}: ${esc(item.nome_pt)}"></label></td>`; }).join('')}
    </tr>`).join('') : `<tr><td class="amenities-property-column">Sem resultados</td><td colspan="${Math.max(amenities.length, 1)}">Ajuste os filtros para ver alojamentos e comodidades.</td></tr>`;
    els.summary.textContent = `${properties.length} alojamentos · ${amenities.length} comodidades`;
  }

  function renderCatalog() {
    const term = els.catalogSearch.value.trim().toLocaleLowerCase('pt');
    const category = els.catalogCategory.value;
    const active = els.catalogActive.value;
    const portal = els.catalogPortal.value;
    const items = state.amenities.filter((item) => {
      const haystack = [item.codigo,item.nome_pt,item.nome_en,item.nome_es,item.nome_fr].join(' ').toLocaleLowerCase('pt');
      return (!term || haystack.includes(term)) && (!category || item.categoria === category)
        && (active === '' || String(Number(item.ativa)) === active)
        && (!portal || (portal === 'show' ? Number(item.mostra_portobreak) : Number(item.filtro_portobreak)));
    });
    els.catalogBody.innerHTML = items.map((item) => `<tr>
      <td><div class="amenities-catalog-main"><span class="amenities-catalog-icon" title="${esc(item.icone)}"><i class="fa-solid ${esc(item.icone)}"></i></span><span><strong>${esc(item.nome_pt)}</strong><small>${esc(item.codigo)}</small></span></div></td>
      <td class="amenities-translations"><strong>EN</strong> ${esc(item.nome_en)}<br><strong>ES</strong> ${esc(item.nome_es)}<br><strong>FR</strong> ${esc(item.nome_fr)}</td>
      <td data-label="Categoria">${esc(categoryLabel(item.categoria))}</td><td data-label="Ordem">${Number(item.ordem)}</td>
      <td data-label="Estado"><span class="amenities-state ${Number(item.ativa) ? 'is-on' : ''}"><i class="fa-solid ${Number(item.ativa) ? 'fa-check' : 'fa-pause'}"></i>${Number(item.ativa) ? 'Ativa' : 'Inativa'}</span></td>
      <td data-label="PortoBreak"><span class="amenities-state ${Number(item.mostra_portobreak) ? 'is-on' : ''}">${Number(item.mostra_portobreak) ? 'Sim' : 'Não'}</span></td>
      <td data-label="Filtro"><span class="amenities-state ${Number(item.filtro_portobreak) ? 'is-on' : ''}">${Number(item.filtro_portobreak) ? 'Sim' : 'Não'}</span></td>
      <td>${state.canEdit ? `<button class="amenities-edit-button" type="button" data-edit="${item.id}" aria-label="Editar ${esc(item.nome_pt)}"><i class="fa-solid fa-pen"></i></button>` : ''}</td>
    </tr>`).join('');
    els.catalogEmpty.hidden = items.length > 0;
  }

  function chooseIcon(icon) {
    els.icon.value = icon;
    els.iconPreview.className = `fa-solid ${icon || 'fa-circle-question'}`;
    els.iconName.textContent = icon || 'Escolher ícone';
    els.iconPicker.querySelectorAll('button').forEach((button) => button.classList.toggle('is-active', button.dataset.icon === icon));
  }

  function openEditor(item = null) {
    els.form.reset();
    els.formError.hidden = true;
    els.id.value = item?.id || '';
    els.code.value = item?.codigo || '';
    els.code.readOnly = Boolean(item);
    els.pt.value = item?.nome_pt || '';
    els.en.value = item?.nome_en || '';
    els.es.value = item?.nome_es || '';
    els.fr.value = item?.nome_fr || '';
    els.editorCategory.value = item?.categoria || state.categories[0]?.code || '';
    els.order.value = item?.ordem ?? 10;
    els.active.checked = item ? Boolean(Number(item.ativa)) : true;
    els.show.checked = item ? Boolean(Number(item.mostra_portobreak)) : true;
    els.filter.checked = item ? Boolean(Number(item.filtro_portobreak)) : false;
    els.formMode.textContent = item ? 'Editar' : 'Nova';
    els.formTitle.textContent = item?.nome_pt || 'Comodidade';
    chooseIcon(item?.icone || '');
    els.iconPicker.hidden = true;
    els.iconButton.setAttribute('aria-expanded', 'false');
    els.form.hidden = false;
    setTimeout(() => (item ? els.pt : els.code).focus(), 0);
  }

  function closeEditor() { els.form.hidden = true; }

  async function loadState(preserve = true) {
    const filters = preserve ? {search:els.search.value, category:els.category.value, zone:els.zone.value} : {};
    els.status.hidden = false; els.status.textContent = 'A carregar comodidades…'; els.wrap.hidden = true;
    try {
      const data = await request(root.dataset.stateUrl);
      state.properties = data.properties || [];
      state.amenities = data.amenities || [];
      state.categories = data.categories || [];
      state.icons = data.icons || [];
      state.zones = data.zones || [];
      state.canEdit = Boolean(data.can_edit);
      state.relations = new Set((data.relations || []).map((item) => relationKey(item.ALOJAMENTO, item.COMODIDADE_ID)));
      fillSelect(els.category, state.categories, 'Todas as categorias');
      fillSelect(els.catalogCategory, state.categories, 'Todas as categorias');
      els.editorCategory.innerHTML = state.categories.map((item) => `<option value="${esc(item.code)}">${esc(item.label)}</option>`).join('');
      fillSelect(els.zone, state.zones, 'Todas as zonas');
      if (preserve) { els.search.value = filters.search || ''; els.category.value = filters.category || ''; els.zone.value = filters.zone || ''; }
      els.iconPicker.innerHTML = state.icons.map((icon) => `<button type="button" data-icon="${esc(icon)}" title="${esc(icon)}" aria-label="${esc(icon)}"><i class="fa-solid ${esc(icon)}"></i></button>`).join('');
      renderMatrix(); renderCatalog();
      els.status.hidden = true; els.wrap.hidden = false;
      els.newButton.hidden = !state.canEdit;
    } catch (error) {
      els.status.textContent = error.message; toast(error.message, true);
    }
  }

  els.body.addEventListener('change', async (event) => {
    const input = event.target.closest('input[data-property][data-id]');
    if (!input) return;
    const oldValue = !input.checked;
    const wrapper = input.closest('.amenities-check');
    wrapper.classList.add('is-saving'); input.disabled = true;
    try {
      await request(root.dataset.relationUrl, {method:'PUT', body:JSON.stringify({alojamento:input.dataset.property, amenity_id:Number(input.dataset.id), enabled:input.checked})});
      const key = relationKey(input.dataset.property, input.dataset.id);
      input.checked ? state.relations.add(key) : state.relations.delete(key);
      toast('Comodidade atualizada.');
    } catch (error) {
      input.checked = oldValue; wrapper.classList.add('is-error'); toast(error.message, true);
      setTimeout(() => wrapper.classList.remove('is-error'), 1800);
    } finally { wrapper.classList.remove('is-saving'); input.disabled = !state.canEdit; }
  });

  els.head.addEventListener('click', async (event) => {
    const button = event.target.closest('button[data-bulk]');
    if (!button) return;
    const enabled = button.dataset.bulk === '1';
    const item = state.amenities.find((candidate) => Number(candidate.id) === Number(button.dataset.id));
    const properties = visibleProperties();
    if (!properties.length || !item) return;
    if (!window.confirm(`${enabled ? 'Marcar' : 'Desmarcar'} “${item.nome_pt}” nos ${properties.length} alojamentos atualmente visíveis?`)) return;
    button.disabled = true;
    try {
      const data = await request(root.dataset.bulkUrl, {method:'PUT', body:JSON.stringify({amenity_id:Number(item.id), enabled, alojamentos:properties.map((property) => property.NOME)})});
      properties.forEach((property) => { const key = relationKey(property.NOME,item.id); enabled ? state.relations.add(key) : state.relations.delete(key); });
      renderMatrix(); toast(`${data.count} alojamentos atualizados.`);
    } catch (error) { toast(error.message, true); }
    finally { button.disabled = false; }
  });

  [els.search, els.category, els.zone].forEach((element) => element.addEventListener(element.tagName === 'INPUT' ? 'input' : 'change', renderMatrix));
  [els.catalogSearch, els.catalogCategory, els.catalogActive, els.catalogPortal].forEach((element) => element.addEventListener(element.tagName === 'INPUT' ? 'input' : 'change', renderCatalog));
  els.reload.addEventListener('click', () => loadState(true));
  els.manage.addEventListener('click', () => { renderCatalog(); els.dialog.showModal(); });
  els.dialogClose.addEventListener('click', () => els.dialog.close());
  els.dialog.addEventListener('click', (event) => { if (event.target === els.dialog) els.dialog.close(); });
  els.newButton.addEventListener('click', () => openEditor());
  els.catalogBody.addEventListener('click', (event) => { const button = event.target.closest('[data-edit]'); if (button) openEditor(state.amenities.find((item) => Number(item.id) === Number(button.dataset.edit))); });
  [els.formClose, els.cancel].forEach((button) => button.addEventListener('click', closeEditor));
  els.iconButton.addEventListener('click', () => { els.iconPicker.hidden = !els.iconPicker.hidden; els.iconButton.setAttribute('aria-expanded', String(!els.iconPicker.hidden)); });
  els.iconPicker.addEventListener('click', (event) => { const button = event.target.closest('[data-icon]'); if (button) { chooseIcon(button.dataset.icon); els.iconPicker.hidden = true; els.iconButton.setAttribute('aria-expanded','false'); } });
  els.filter.addEventListener('change', () => { if (els.filter.checked) { els.active.checked = true; els.show.checked = true; } });
  els.active.addEventListener('change', () => { if (!els.active.checked) els.filter.checked = false; });
  els.show.addEventListener('change', () => { if (!els.show.checked) els.filter.checked = false; });

  els.form.addEventListener('submit', async (event) => {
    event.preventDefault();
    const payload = {codigo:els.code.value,nome_pt:els.pt.value,nome_en:els.en.value,nome_es:els.es.value,nome_fr:els.fr.value,categoria:els.editorCategory.value,icone:els.icon.value,ordem:els.order.value,ativa:els.active.checked,mostra_portobreak:els.show.checked,filtro_portobreak:els.filter.checked};
    els.formError.hidden = true; els.save.disabled = true;
    try {
      if (!payload.icone) throw new Error('Escolha um ícone.');
      const id = els.id.value;
      const url = id ? `${root.dataset.catalogUrl}/${id}` : root.dataset.catalogUrl;
      await request(url, {method:id ? 'PUT' : 'POST', body:JSON.stringify(payload)});
      closeEditor(); await loadState(true); renderCatalog(); toast(id ? 'Comodidade atualizada.' : 'Comodidade criada.');
    } catch (error) { els.formError.textContent = error.message; els.formError.hidden = false; }
    finally { els.save.disabled = false; }
  });

  loadState(false);
})();
