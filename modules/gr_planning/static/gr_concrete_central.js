(function () {
  const cfg = window.GR_CONCRETE_CENTRAL || {};
  const form = document.getElementById('grCentralForm');
  const saveBtn = document.getElementById('grCentralSave');
  const deleteBtn = document.getElementById('grCentralDelete');
  const processResults = document.getElementById('grCentralProcessos');
  const vehicleSelect = document.getElementById('grCentralMatricula');
  const driverSelect = document.getElementById('grCentralMotorista');
  const refPickBtn = document.getElementById('grCentralRefPick');
  const refModal = document.getElementById('grCentralRefModal');
  const refList = document.getElementById('grCentralRefList');
  const refSearch = document.getElementById('grCentralRefSearch');
  const refApplyBtn = document.getElementById('grCentralRefApply');

  if (!form) return;

  const els = {
    stamp: document.getElementById('grCentralStamp'),
    processo: document.getElementById('grCentralProcesso'),
    processoDescricao: document.getElementById('grCentralProcessoDescricao'),
    data: document.getElementById('grCentralData'),
    servico: document.getElementById('grCentralServico'),
    matricula: document.getElementById('grCentralMatricula'),
    motorista: document.getElementById('grCentralMotorista'),
    horaini: document.getElementById('grCentralHoraIni'),
    horafim: document.getElementById('grCentralHoraFim'),
    cinicial: document.getElementById('grCentralCInicial'),
    cfinal: document.getElementById('grCentralCFinal'),
    qtt: document.getElementById('grCentralQtt'),
    refbetao: document.getElementById('grCentralRefBetao'),
    areia: document.getElementById('grCentralAreia'),
    brita: document.getElementById('grCentralBrita'),
    cimento: document.getElementById('grCentralCimento'),
    aditivo: document.getElementById('grCentralAditivo'),
    descricao: document.getElementById('grCentralDescricao'),
  };

  let searchTimer = null;
  let initialRecord = cfg.record || null;
  let processRows = [];
  let refRows = [];
  let refSelected = new Set();

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
    window.location.href = cfg.returnUrl || '/generic/view/RCENTRAL/';
  };

  const num = (value) => {
    const parsed = Number(String(value ?? '').replace(',', '.'));
    return Number.isFinite(parsed) ? parsed : 0;
  };

  const fmt = (value, digits = 3) => num(value).toLocaleString('pt-PT', {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });

  const updateQtt = () => {
    const qtt = Math.max(0, num(els.cfinal.value) - num(els.cinicial.value));
    els.qtt.textContent = fmt(qtt);
    return qtt;
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
    els.cinicial.value = '0';
    els.cfinal.value = '0';
    els.areia.value = '0';
    els.brita.value = '0';
    els.cimento.value = '0';
    els.aditivo.value = '0';
    if (els.motorista) els.motorista.value = cfg.defaultDriver || '';
    if (els.servico) els.servico.value = 'PRODUÇÃO';
    updateQtt();
  };

  const payloadFromForm = () => ({
    stamp: els.stamp.value.trim(),
    processo: els.processo.value.trim(),
    servico: els.servico.value,
    motorista: els.motorista.value.trim(),
    matricula: els.matricula.value.trim(),
    data: els.data.value,
    horaini: els.horaini.value,
    horafim: els.horafim.value,
    cinicial: els.cinicial.value,
    cfinal: els.cfinal.value,
    refbetao: els.refbetao.value.trim(),
    areia: els.areia.value,
    brita: els.brita.value,
    cimento: els.cimento.value,
    aditivo: els.aditivo.value,
    descricao: els.descricao.value.trim(),
  });

  const fillForm = (record) => {
    els.stamp.value = record.stamp || '';
    setProject(record.processo || '', record.obra_descricao || '');
    els.data.value = record.data || cfg.today || '';
    els.servico.value = record.servico || 'PRODUÇÃO';
    els.matricula.value = record.matricula || '';
    els.motorista.value = record.motorista || '';
    els.horaini.value = record.horaini || '';
    els.horafim.value = record.horafim || '';
    els.cinicial.value = record.cinicial ?? 0;
    els.cfinal.value = record.cfinal ?? 0;
    els.refbetao.value = record.refbetao || '';
    els.areia.value = record.areia ?? 0;
    els.brita.value = record.brita ?? 0;
    els.cimento.value = record.cimento ?? 0;
    els.aditivo.value = record.aditivo ?? 0;
    els.descricao.value = record.descricao || '';
    if (deleteBtn) deleteBtn.hidden = false;
    updateQtt();
  };

  const loadVehicles = async () => {
    if (!vehicleSelect) return;
    const selected = els.matricula?.value || initialRecord?.matricula || '';
    try {
      const response = await fetch(cfg.vehiclesUrl, { headers: { Accept: 'application/json' } });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(payload.error || 'Erro ao carregar centrais.');
      const rows = payload.rows || [];
      vehicleSelect.innerHTML = '<option value="">Escolher central</option>' + rows.map((row) => (
        `<option value="${escapeHtml(row.matricula)}">${escapeHtml(row.label || row.matricula)}</option>`
      )).join('');
      if (selected) {
        const exists = Array.from(vehicleSelect.options).some((option) => option.value === selected);
        if (!exists) {
          vehicleSelect.insertAdjacentHTML('beforeend', `<option value="${escapeHtml(selected)}">${escapeHtml(selected)}</option>`);
        }
        vehicleSelect.value = selected;
      }
    } catch (error) {
      vehicleSelect.innerHTML = '<option value="">Erro ao carregar</option>';
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

  const parseRefs = (value) => String(value || '')
    .split(';')
    .map((item) => item.trim())
    .filter(Boolean);

  const closeRefModal = () => {
    if (!refModal) return;
    refModal.hidden = true;
    document.body.classList.remove('gr-central-ref-open');
  };

  const renderRefRows = () => {
    if (!refList) return;
    const term = String(refSearch?.value || '').trim().toLowerCase();
    const rows = refRows.filter((row) => {
      if (!term) return true;
      return `${row.ref || ''} ${row.design || ''}`.toLowerCase().includes(term);
    });
    if (!rows.length) {
      refList.innerHTML = '<div class="gr-central-ref-empty">Sem referencias para esta obra.</div>';
      return;
    }
    refList.innerHTML = rows.map((row, index) => {
      const ref = String(row.ref || '').trim();
      const design = String(row.design || '').trim();
      const checked = refSelected.has(ref) ? ' checked' : '';
      return `
        <label class="gr-central-ref-row">
          <input type="checkbox" value="${escapeHtml(ref)}" data-ref-index="${index}"${checked}>
          <span>
            <strong>${escapeHtml(ref)}</strong>
            <span>${escapeHtml(design)}</span>
          </span>
        </label>
      `;
    }).join('');
  };

  const openRefModal = async () => {
    if (!refModal || !refList) return;
    const processo = els.processo.value.trim();
    if (!processo) {
      showToastMessage('Escolha primeiro a obra.', 'warning');
      els.processo.focus();
      return;
    }
    refModal.hidden = false;
    document.body.classList.add('gr-central-ref-open');
    refSelected = new Set(parseRefs(els.refbetao.value));
    if (refSearch) refSearch.value = '';
    refList.innerHTML = '<div class="gr-central-ref-empty">A carregar referencias...</div>';
    try {
      const response = await fetch(`${cfg.refsUrl}?processo=${encodeURIComponent(processo)}`, {
        headers: { Accept: 'application/json' },
      });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(payload.error || 'Erro ao carregar referencias.');
      refRows = Array.isArray(payload.rows) ? payload.rows : [];
      renderRefRows();
      window.setTimeout(() => refSearch?.focus(), 30);
    } catch (error) {
      refRows = [];
      refList.innerHTML = `<div class="gr-central-ref-empty">${escapeHtml(error.message || 'Erro ao carregar referencias.')}</div>`;
    }
  };

  const renderProcessResults = (rows) => {
    if (!processResults) return;
    processRows = Array.isArray(rows) ? rows : [];
    if (!processRows.length) {
      processResults.innerHTML = '<div class="gr-central-process-empty">Sem obras encontradas.</div>';
      processResults.hidden = false;
      return;
    }
    processResults.innerHTML = processRows.map((row, index) => (
      `<button type="button" class="gr-central-process-option" data-index="${index}">
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
    if (num(data.cfinal) < num(data.cinicial)) {
      showToastMessage('O contador final nao pode ser inferior ao inicial.', 'warning');
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

  [els.cinicial, els.cfinal].forEach((input) => {
    input?.addEventListener('input', updateQtt);
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
    const option = event.target.closest('.gr-central-process-option');
    if (!option) return;
    const row = processRows[Number(option.dataset.index)];
    if (!row) return;
    setProject(row.processo || '', row.descricao || '');
    hideProcessResults();
  });

  refPickBtn?.addEventListener('click', openRefModal);
  els.refbetao?.addEventListener('dblclick', openRefModal);
  refSearch?.addEventListener('input', renderRefRows);

  refList?.addEventListener('change', (event) => {
    const input = event.target.closest('input[type="checkbox"]');
    if (!input) return;
    const ref = String(input.value || '').trim();
    if (!ref) return;
    if (input.checked) refSelected.add(ref);
    else refSelected.delete(ref);
  });

  refModal?.addEventListener('click', (event) => {
    if (event.target.closest('[data-ref-close]')) {
      closeRefModal();
    }
  });

  refApplyBtn?.addEventListener('click', () => {
    if (!refList) return;
    const refs = [];
    refRows.forEach((row) => {
      const ref = String(row.ref || '').trim();
      if (ref && refSelected.has(ref) && !refs.includes(ref)) refs.push(ref);
    });
    const fittedRefs = [];
    refs.forEach((ref) => {
      const candidate = [...fittedRefs, ref].join('; ');
      if (candidate.length <= 254) fittedRefs.push(ref);
    });
    if (fittedRefs.length < refs.length) {
      showToastMessage('Algumas referencias nao cabem no campo.', 'warning');
    }
    els.refbetao.value = fittedRefs.join('; ');
    closeRefModal();
  });

  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && refModal && !refModal.hidden) {
      closeRefModal();
    }
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
