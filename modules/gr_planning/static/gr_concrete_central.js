(function () {
  const cfg = window.GR_CONCRETE_CENTRAL || {};
  const form = document.getElementById('grCentralForm');
  const saveBtn = document.getElementById('grCentralSave');
  const deleteBtn = document.getElementById('grCentralDelete');
  const formHint = document.getElementById('grCentralFormHint');
  const processDatalist = document.getElementById('grCentralProcessos');
  const vehicleSelect = document.getElementById('grCentralMatricula');

  if (!form) return;

  const els = {
    stamp: document.getElementById('grCentralStamp'),
    processo: document.getElementById('grCentralProcesso'),
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

  const fillBlankForm = () => {
    form.reset();
    els.stamp.value = '';
    els.data.value = cfg.today || new Date().toISOString().slice(0, 10);
    els.cinicial.value = '0';
    els.cfinal.value = '0';
    els.areia.value = '0';
    els.brita.value = '0';
    els.cimento.value = '0';
    els.aditivo.value = '0';
    if (els.servico) els.servico.value = 'PRODUÇÃO';
    if (formHint) formHint.textContent = 'Novo registo diario.';
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
    els.processo.value = record.processo || '';
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
    if (formHint) formHint.textContent = `Editar registo ${record.processo || ''}`.trim();
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

  const searchProcesses = async (term) => {
    if (!processDatalist) return;
    const query = String(term || '').trim();
    if (query.length < 1) {
      processDatalist.innerHTML = '';
      return;
    }
    try {
      const response = await fetch(`${cfg.opcUrl}?q=${encodeURIComponent(query)}`, {
        headers: { Accept: 'application/json' },
      });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(payload.error || 'Erro');
      processDatalist.innerHTML = (payload.rows || []).map((row) => (
        `<option value="${escapeHtml(row.processo)}">${escapeHtml(row.descricao || '')}</option>`
      )).join('');
    } catch (error) {
      processDatalist.innerHTML = '';
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
    window.clearTimeout(searchTimer);
    searchTimer = window.setTimeout(() => searchProcesses(els.processo.value), 180);
  });

  if (initialRecord) fillForm(initialRecord);
  else fillBlankForm();

  loadVehicles();
})();
