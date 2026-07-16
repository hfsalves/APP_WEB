const trigger = document.getElementById('btnVaSnc');
const modalElement = document.getElementById('vaSncModal');

if (trigger && modalElement && window.RECORD_STAMP) {
  const body = document.getElementById('vaSncTableBody');
  const status = document.getElementById('vaSncStatus');
  const vehicleLabel = document.getElementById('vaSncVehicle');
  const countLabel = document.getElementById('vaSncCount');
  const emptyState = document.getElementById('vaSncEmpty');
  const addButton = document.getElementById('btnVaSncAdd');
  const saveButton = document.getElementById('btnVaSncSave');
  const modal = bootstrap.Modal.getOrCreateInstance(modalElement);
  const apiBase = `/generic/api/va/${encodeURIComponent(window.RECORD_STAMP)}/snc`;
  let cpooOptionsByDatabase = {};
  let phcSources = [];
  let canEdit = false;

  const notify = (message, type = 'info') => {
    if (typeof window.showToast === 'function') {
      window.showToast(message, type);
    }
  };

  const requestJson = async (url, options = {}) => {
    const response = await fetch(url, {
      ...options,
      headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
    });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok || payload.error) {
      throw new Error(payload.error || `Pedido recusado (${response.status}).`);
    }
    return payload;
  };

  const setStatus = (message = '', type = '') => {
    status.textContent = message;
    status.className = `sz_va_snc_status${type ? ` is-${type}` : ''}`;
    status.hidden = !message;
  };

  const updateSummary = () => {
    const count = body.querySelectorAll('tr[data-va-snc-row]').length;
    countLabel.textContent = `${count} associaç${count === 1 ? 'ão' : 'ões'}`;
    emptyState.hidden = count !== 0;
  };

  const createSncSelect = (databaseName, selectedStamp = '') => {
    const select = document.createElement('select');
    select.className = 'sz_select sz_va_snc_select';
    select.disabled = !canEdit;
    const placeholder = document.createElement('option');
    placeholder.value = '';
    placeholder.textContent = 'Selecionar código SNC';
    select.appendChild(placeholder);
    (cpooOptionsByDatabase[databaseName] || []).forEach((item) => {
      const option = document.createElement('option');
      option.value = item.cpoostamp;
      option.textContent = `${item.snc}${item.descricao ? ` — ${item.descricao}` : ''}`;
      option.dataset.snc = String(item.snc);
      option.selected = item.cpoostamp === selectedStamp;
      select.appendChild(option);
    });
    return select;
  };

  const renderArticleResults = (dropdown, items, input, row) => {
    dropdown.replaceChildren();
    if (!items.length) {
      const empty = document.createElement('div');
      empty.className = 'sz_table_lookup_empty';
      empty.textContent = 'Nenhum artigo encontrado.';
      dropdown.appendChild(empty);
    } else {
      items.forEach((item) => {
        const option = document.createElement('button');
        option.type = 'button';
        option.className = 'sz_table_lookup_item';
        const reference = document.createElement('span');
        reference.className = 'sz_table_lookup_item_label';
        reference.textContent = item.ref;
        const designation = document.createElement('span');
        designation.className = 'sz_table_lookup_item_value';
        designation.textContent = item.design;
        option.append(reference, designation);
        option.addEventListener('click', () => {
          row.dataset.ststamp = item.ststamp;
          input.value = item.ref;
          row.querySelector('[data-va-snc-design]').textContent = item.design;
          dropdown.hidden = true;
          row.classList.remove('is-invalid');
        });
        dropdown.appendChild(option);
      });
    }
    dropdown.hidden = false;
  };

  const bindArticleLookup = (input, dropdown, row) => {
    let timer = 0;
    let requestNumber = 0;
    const search = () => {
      window.clearTimeout(timer);
      timer = window.setTimeout(async () => {
        const currentRequest = ++requestNumber;
        try {
          const params = new URLSearchParams({
            q: input.value.trim(),
            phc_database: row.dataset.phcDatabase || '',
          });
          const data = await requestJson(`${apiBase}/articles?${params.toString()}`);
          if (currentRequest === requestNumber) {
            renderArticleResults(dropdown, data.items || [], input, row);
          }
        } catch (error) {
          if (currentRequest === requestNumber) {
            dropdown.replaceChildren();
            const message = document.createElement('div');
            message.className = 'sz_table_lookup_empty is-danger';
            message.textContent = error.message;
            dropdown.appendChild(message);
            dropdown.hidden = false;
          }
        }
      }, input.value.trim() ? 220 : 0);
    };
    input.addEventListener('focus', search);
    input.addEventListener('input', () => {
      row.dataset.ststamp = '';
      row.querySelector('[data-va-snc-design]').textContent = 'Seleciona uma referência da lista.';
      search();
    });
  };

  const addRow = (data = {}, focus = false) => {
    const row = document.createElement('tr');
    row.dataset.vaSncRow = '';
    row.dataset.vasncstamp = data.vasncstamp || '';
    row.dataset.ststamp = data.ststamp || '';
    row.dataset.phcDatabase = data.phc_database || vehicleLabel.dataset.phcDatabase || '';

    const refCell = document.createElement('td');
    const lookup = document.createElement('div');
    lookup.className = 'sz_table_lookup sz_va_snc_lookup';
    const refInput = document.createElement('input');
    refInput.type = 'search';
    refInput.className = 'sz_input';
    refInput.placeholder = 'Pesquisar referência ou designação';
    refInput.autocomplete = 'off';
    refInput.value = data.ref || '';
    refInput.disabled = !canEdit;
    refInput.setAttribute('aria-label', 'Referência do artigo');
    const dropdown = document.createElement('div');
    dropdown.className = 'sz_table_lookup_dropdown';
    dropdown.hidden = true;
    lookup.append(refInput, dropdown);
    refCell.appendChild(lookup);

    const designCell = document.createElement('td');
    designCell.dataset.vaSncDesign = '';
    designCell.className = 'sz_va_snc_design';
    designCell.textContent = data.design || 'Seleciona uma referência da lista.';

    const sncCell = document.createElement('td');
    sncCell.appendChild(createSncSelect(row.dataset.phcDatabase, data.cpoostamp || ''));

    const originCell = document.createElement('td');
    originCell.className = 'sz_va_snc_origin';
    const originSelect = document.createElement('select');
    originSelect.className = 'sz_select sz_va_snc_origin_select';
    originSelect.disabled = !canEdit;
    phcSources.forEach((source) => {
      const option = document.createElement('option');
      option.value = source.phc_database;
      option.textContent = `${source.origin} · ${source.phc_database}`;
      option.selected = source.phc_database === row.dataset.phcDatabase;
      originSelect.appendChild(option);
    });
    originSelect.addEventListener('change', () => {
      row.dataset.phcDatabase = originSelect.value;
      row.dataset.vasncstamp = '';
      row.dataset.ststamp = '';
      refInput.value = '';
      designCell.textContent = 'Seleciona uma referência da lista.';
      sncCell.replaceChildren(createSncSelect(row.dataset.phcDatabase));
    });
    originCell.appendChild(originSelect);

    const actionCell = document.createElement('td');
    actionCell.className = 'sz_col_fit';
    const removeButton = document.createElement('button');
    removeButton.type = 'button';
    removeButton.className = 'sz_button sz_button_ghost sz_button_icon sz_va_snc_remove';
    removeButton.disabled = !canEdit;
    removeButton.title = 'Remover associação';
    removeButton.setAttribute('aria-label', 'Remover associação');
    removeButton.innerHTML = '<i class="fa fa-trash" aria-hidden="true"></i>';
    removeButton.addEventListener('click', () => {
      row.remove();
      updateSummary();
    });
    actionCell.appendChild(removeButton);

    row.append(refCell, designCell, sncCell, originCell, actionCell);
    body.appendChild(row);
    bindArticleLookup(refInput, dropdown, row);
    updateSummary();
    if (focus) refInput.focus();
  };

  const load = async () => {
    setStatus('A carregar associações SNC…');
    body.replaceChildren();
    addButton.disabled = true;
    saveButton.disabled = true;
    try {
      const data = await requestJson(apiBase);
      cpooOptionsByDatabase = data.cpoo_options_by_database || {};
      phcSources = data.phc_sources || [];
      canEdit = Boolean(data.can_edit);
      const vehicle = data.vehicle || {};
      vehicleLabel.dataset.origin = vehicle.ORIGEM || '';
      vehicleLabel.dataset.phcDatabase = data.phc_database || '';
      vehicleLabel.textContent = [
        vehicle.MATRICULA,
        vehicle.MARCA,
        vehicle.MODELO,
        vehicle.ORIGEM ? `Origem VA ${vehicle.ORIGEM}` : '',
        data.phc_database ? `PHC predefinido ${data.phc_database}` : '',
      ].filter(Boolean).join(' · ');
      (data.rows || []).forEach((row) => addRow(row));
      updateSummary();
      addButton.disabled = !canEdit;
      saveButton.disabled = !canEdit;
      setStatus(canEdit ? '' : 'Consulta apenas: não tens permissão para editar esta viatura.', canEdit ? '' : 'info');
    } catch (error) {
      setStatus(error.message, 'danger');
      updateSummary();
    }
  };

  const save = async () => {
    const rows = [...body.querySelectorAll('tr[data-va-snc-row]')];
    let invalidRow = null;
    const payloadRows = rows.map((row) => {
      const select = row.querySelector('.sz_va_snc_select');
      const item = {
        vasncstamp: row.dataset.vasncstamp || '',
        ststamp: row.dataset.ststamp || '',
        cpoostamp: select?.value || '',
        phc_database: row.dataset.phcDatabase || '',
      };
      row.classList.toggle('is-invalid', !item.phc_database || !item.ststamp || !item.cpoostamp);
      if ((!item.phc_database || !item.ststamp || !item.cpoostamp) && !invalidRow) invalidRow = row;
      return item;
    });
    if (invalidRow) {
      setStatus('Preenche a origem, a referência e o código SNC em todas as linhas.', 'danger');
      invalidRow.querySelector('input, select')?.focus();
      return;
    }

    saveButton.disabled = true;
    addButton.disabled = true;
    setStatus('A gravar associações…');
    try {
      const result = await requestJson(apiBase, { method: 'POST', body: JSON.stringify({ rows: payloadRows }) });
      modal.hide();
      notify(`${result.count || 0} associaç${result.count === 1 ? 'ão gravada' : 'ões gravadas'}.`, 'success');
    } catch (error) {
      setStatus(error.message, 'danger');
    } finally {
      saveButton.disabled = !canEdit;
      addButton.disabled = !canEdit;
    }
  };

  trigger.addEventListener('click', () => {
    modal.show();
    load();
  });
  addButton.addEventListener('click', () => addRow({
    origin: vehicleLabel.dataset.origin || '',
    phc_database: vehicleLabel.dataset.phcDatabase || '',
  }, true));
  saveButton.addEventListener('click', save);
  document.addEventListener('click', (event) => {
    body.querySelectorAll('.sz_table_lookup_dropdown').forEach((dropdown) => {
      if (!dropdown.parentElement.contains(event.target)) dropdown.hidden = true;
    });
  });
}
