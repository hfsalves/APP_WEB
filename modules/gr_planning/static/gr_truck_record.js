(function () {
  const cfg = window.GR_TRUCK_RECORD || {};
  const form = document.getElementById('grTruckForm');
  const saveBtn = document.getElementById('grTruckSave');
  const deleteBtn = document.getElementById('grTruckDelete');
  const processResults = document.getElementById('grTruckProcessos');
  const vehicleSelect = document.getElementById('grTruckMatricula');
  const trailerSelect = document.getElementById('grTruckAtrelado');
  const driverSelect = document.getElementById('grTruckMotorista');

  if (!form) return;

  const els = {
    stamp: document.getElementById('grTruckStamp'),
    processo: document.getElementById('grTruckProcesso'),
    processoDescricao: document.getElementById('grTruckProcessoDescricao'),
    data: document.getElementById('grTruckData'),
    motorista: document.getElementById('grTruckMotorista'),
    matricula: document.getElementById('grTruckMatricula'),
    atrelado: document.getElementById('grTruckAtrelado'),
    horaini: document.getElementById('grTruckHoraIni'),
    horafim: document.getElementById('grTruckHoraFim'),
    kmsini: document.getElementById('grTruckKmsIni'),
    kmsfim: document.getElementById('grTruckKmsFim'),
    kms: document.getElementById('grTruckKms'),
    descricao: document.getElementById('grTruckDescricao'),
  };

  let searchTimer = null;
  let initialRecord = cfg.record || null;
  let processRows = [];

  const escapeHtml = (value) => String(value ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');

  const showToastMessage = (message, type = 'success') => {
    if (window.showToast) window.showToast(message, type);
    else window.alert(message);
  };

  const returnToList = () => {
    window.location.href = cfg.returnUrl || '/generic/view/RCAMIAO/';
  };

  const intValue = (value) => {
    const parsed = Number(String(value ?? '').replace(',', '.'));
    return Number.isFinite(parsed) ? Math.trunc(parsed) : 0;
  };

  const updateKms = () => {
    const kms = Math.max(0, intValue(els.kmsfim.value) - intValue(els.kmsini.value));
    els.kms.textContent = String(kms);
    return kms;
  };

  const setLoading = (loading) => {
    if (saveBtn) saveBtn.disabled = !!loading;
    if (deleteBtn) deleteBtn.disabled = !!loading;
  };

  const setProject = (processo, descricao = '') => {
    if (els.processo) els.processo.value = processo || '';
    if (els.processoDescricao) els.processoDescricao.value = descricao || '';
  };

  const fillBlankForm = () => {
    form.reset();
    els.stamp.value = '';
    setProject('', '');
    els.data.value = cfg.today || new Date().toISOString().slice(0, 10);
    els.kmsini.value = '0';
    els.kmsfim.value = '0';
    if (els.motorista) els.motorista.value = cfg.defaultDriver || '';
    updateKms();
  };

  const payloadFromForm = () => ({
    stamp: els.stamp.value.trim(),
    data: els.data.value,
    motorista: els.motorista.value.trim(),
    processo: els.processo.value.trim(),
    matricula: els.matricula.value.trim(),
    atrelado: els.atrelado.value.trim(),
    horaini: els.horaini.value,
    horafim: els.horafim.value,
    kmsini: els.kmsini.value,
    kmsfim: els.kmsfim.value,
    descricao: els.descricao.value.trim(),
  });

  const fillForm = (record) => {
    els.stamp.value = record.stamp || '';
    setProject(record.processo || '', record.obra_descricao || '');
    els.data.value = record.data || cfg.today || '';
    els.motorista.value = record.motorista || '';
    els.matricula.value = record.matricula || '';
    els.atrelado.value = record.atrelado || '';
    els.horaini.value = record.horaini || '';
    els.horafim.value = record.horafim || '';
    els.kmsini.value = record.kmsini ?? 0;
    els.kmsfim.value = record.kmsfim ?? 0;
    els.descricao.value = record.descricao || '';
    if (deleteBtn) deleteBtn.hidden = false;
    updateKms();
  };

  const applySelectRows = (select, rows, selected, emptyLabel) => {
    if (!select) return;
    select.innerHTML = `<option value="">${escapeHtml(emptyLabel)}</option>` + rows.map((row) => (
      `<option value="${escapeHtml(row.matricula || row.nome)}">${escapeHtml(row.label || row.matricula || row.nome)}</option>`
    )).join('');
    if (selected) {
      const exists = Array.from(select.options).some((option) => option.value === selected);
      if (!exists) {
        select.insertAdjacentHTML('beforeend', `<option value="${escapeHtml(selected)}">${escapeHtml(selected)}</option>`);
      }
      select.value = selected;
    }
  };

  const loadVehicles = async () => {
    const selectedTruck = els.matricula?.value || initialRecord?.matricula || '';
    const selectedTrailer = els.atrelado?.value || initialRecord?.atrelado || '';
    try {
      const response = await fetch(cfg.vehiclesUrl, { headers: { Accept: 'application/json' } });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(payload.error || 'Erro ao carregar viaturas.');
      const trucks = payload.trucks || payload.rows || [];
      const trailers = payload.trailers || [];
      applySelectRows(vehicleSelect, trucks, selectedTruck, 'Escolher viatura');
      applySelectRows(trailerSelect, trailers, selectedTrailer, 'Sem atrelado');
    } catch (error) {
      if (vehicleSelect) vehicleSelect.innerHTML = '<option value="">Erro ao carregar</option>';
      if (trailerSelect) trailerSelect.innerHTML = '<option value="">Erro ao carregar</option>';
    }
  };

  const loadDrivers = async () => {
    if (!driverSelect) return;
    const selected = els.motorista?.value || initialRecord?.motorista || cfg.defaultDriver || '';
    try {
      const response = await fetch(cfg.driversUrl, { headers: { Accept: 'application/json' } });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(payload.error || 'Erro ao carregar motoristas.');
      const rows = payload.rows || [];
      driverSelect.innerHTML = '<option value="">Escolher motorista</option>' + rows.map((row) => (
        `<option value="${escapeHtml(row.nome)}">${escapeHtml(row.nome)}</option>`
      )).join('');
      if (selected) {
        const exists = Array.from(driverSelect.options).some((option) => option.value === selected);
        if (!exists) {
          driverSelect.insertAdjacentHTML('beforeend', `<option value="${escapeHtml(selected)}">${escapeHtml(selected)}</option>`);
        }
        driverSelect.value = selected;
      }
    } catch (error) {
      driverSelect.innerHTML = '<option value="">Erro ao carregar</option>';
    }
  };

  const hideProcessResults = () => {
    if (processResults) processResults.hidden = true;
  };

  const renderProcessResults = (rows) => {
    if (!processResults) return;
    processRows = Array.isArray(rows) ? rows : [];
    if (!processRows.length) {
      processResults.innerHTML = '<div class="gr-truck-process-empty">Sem obras encontradas.</div>';
      processResults.hidden = false;
      return;
    }
    processResults.innerHTML = processRows.map((row, index) => (
      `<button type="button" class="gr-truck-process-option" data-index="${index}">
        <strong>${escapeHtml(row.processo || '')}</strong>
        <span>${escapeHtml(row.descricao || '')}</span>
      </button>`
    )).join('');
    processResults.hidden = false;
  };

  const searchProcesses = async (term) => {
    if (!processResults) return;
    const query = String(term || '').trim();
    if (query.length < 1) {
      processResults.innerHTML = '';
      processResults.hidden = true;
      return;
    }
    try {
      const response = await fetch(`${cfg.opcUrl}?q=${encodeURIComponent(query)}`, {
        headers: { Accept: 'application/json' },
      });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(payload.error || 'Erro');
      renderProcessResults(payload.rows || []);
      const exact = processRows.find((row) => (
        String(row.processo || '').trim().toUpperCase() === query.toUpperCase()
      ));
      if (exact && els.processoDescricao) els.processoDescricao.value = exact.descricao || '';
    } catch (error) {
      processResults.innerHTML = '';
      processResults.hidden = true;
    }
  };

  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    const data = payloadFromForm();
    if (intValue(data.kmsfim) < intValue(data.kmsini)) {
      showToastMessage('Os kms finais nao podem ser inferiores aos iniciais.', 'warning');
      return;
    }
    setLoading(true);
    try {
      const response = await fetch(cfg.saveUrl, {
        method: 'POST',
        headers: {
          Accept: 'application/json',
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(data),
      });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok || payload.ok === false) throw new Error(payload.error || 'Erro ao gravar.');
      showToastMessage('Registo guardado.');
      window.setTimeout(returnToList, 250);
    } catch (error) {
      showToastMessage(error.message || 'Erro ao gravar.', 'danger');
    } finally {
      setLoading(false);
    }
  });

  deleteBtn?.addEventListener('click', async () => {
    const stamp = els.stamp.value.trim();
    if (!stamp || !window.confirm('Eliminar este registo?')) return;
    setLoading(true);
    try {
      const response = await fetch(`${cfg.recordsUrl}/${encodeURIComponent(stamp)}`, {
        method: 'DELETE',
        headers: { Accept: 'application/json' },
      });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok || payload.ok === false) throw new Error(payload.error || 'Erro ao eliminar.');
      showToastMessage('Registo eliminado.');
      window.setTimeout(returnToList, 250);
    } catch (error) {
      showToastMessage(error.message || 'Erro ao eliminar.', 'danger');
    } finally {
      setLoading(false);
    }
  });

  [els.kmsini, els.kmsfim].forEach((input) => {
    input?.addEventListener('input', updateKms);
  });

  els.processo?.addEventListener('input', () => {
    if (els.processoDescricao) els.processoDescricao.value = '';
    window.clearTimeout(searchTimer);
    searchTimer = window.setTimeout(() => searchProcesses(els.processo.value), 180);
  });

  els.processo?.addEventListener('focus', () => {
    if (els.processo.value.trim()) searchProcesses(els.processo.value);
  });

  processResults?.addEventListener('click', (event) => {
    const option = event.target.closest('.gr-truck-process-option');
    if (!option) return;
    const row = processRows[Number(option.dataset.index)];
    if (!row) return;
    setProject(row.processo || '', row.descricao || '');
    hideProcessResults();
  });

  document.addEventListener('pointerdown', (event) => {
    if (!processResults || processResults.hidden) return;
    if (event.target === els.processo || processResults.contains(event.target)) return;
    hideProcessResults();
  });

  if (initialRecord) fillForm(initialRecord);
  else fillBlankForm();

  loadVehicles();
  loadDrivers();
})();
