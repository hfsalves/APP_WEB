(() => {
  const rows = document.getElementById('phcCloseDatesRows');
  const refresh = document.getElementById('phcCloseDatesRefresh');
  const applyAllDate = document.getElementById('phcCloseDatesApplyAllDate');
  const applyAll = document.getElementById('phcCloseDatesApplyAll');
  if (!rows) return;

  const escapeHtml = (value) => String(value ?? '').replace(/[&<>'"]/g, (char) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;'
  }[char]));

  const setRowStatus = (row, message, state = '') => {
    const status = row.querySelector('[data-role="status"]');
    if (!status) return;
    status.textContent = message;
    status.className = `phc-close-date-status ${state}`;
  };

  const render = (items) => {
    if (!items.length) {
      rows.innerHTML = '<tr><td colspan="5" class="sz_text_muted">Não existem bases PHC configuradas.</td></tr>';
      return;
    }
    rows.innerHTML = items.map((item) => {
      const editable = item.status === 'ok';
      const message = item.status === 'ok' ? 'Configurado' : (item.message || 'Indisponível');
      return `<tr data-feid="${item.feid}">
        <td><strong>${escapeHtml(item.name)}</strong></td>
        <td><code>${escapeHtml(item.phc_db)}</code></td>
        <td><input class="sz_input" type="date" value="${escapeHtml(item.value || '')}" ${editable ? '' : 'disabled'} aria-label="Data fechada de ${escapeHtml(item.name)}"></td>
        <td><span data-role="status" class="phc-close-date-status ${editable ? 'is-ok' : 'is-error'}">${escapeHtml(message)}</span></td>
        <td class="phc-close-dates-action"><button type="button" class="sz_button sz_button_primary" data-action="save" ${editable ? '' : 'disabled'} title="Gravar data"><i class="fa-solid fa-floppy-disk"></i><span>Gravar</span></button></td>
      </tr>`;
    }).join('');
  };

  const load = async () => {
    rows.innerHTML = '<tr><td colspan="5" class="sz_text_muted">A carregar bases de dados...</td></tr>';
    try {
      const response = await fetch('/api/phc-close-dates', { headers: { Accept: 'application/json' } });
      const payload = await response.json();
      if (!response.ok || !payload.ok) throw new Error(payload.error || 'Não foi possível carregar as datas fechadas.');
      render(payload.items || []);
    } catch (error) {
      rows.innerHTML = `<tr><td colspan="5" class="phc-close-date-error">${escapeHtml(error.message)}</td></tr>`;
    }
  };

  rows.addEventListener('click', async (event) => {
    const button = event.target.closest('[data-action="save"]');
    if (!button) return;
    const row = button.closest('tr');
    const input = row.querySelector('input[type="date"]');
    if (!input.value) {
      setRowStatus(row, 'Indique uma data.', 'is-error');
      input.focus();
      return;
    }
    button.disabled = true;
    setRowStatus(row, 'A gravar...');
    try {
      const response = await fetch(`/api/phc-close-dates/${row.dataset.feid}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
        body: JSON.stringify({ value: input.value }),
      });
      const payload = await response.json();
      if (!response.ok || !payload.ok) throw new Error(payload.error || 'Não foi possível gravar a data.');
      input.value = payload.item.value;
      setRowStatus(row, 'Gravado', 'is-ok');
    } catch (error) {
      setRowStatus(row, error.message, 'is-error');
    } finally {
      button.disabled = false;
    }
  });

  refresh?.addEventListener('click', load);
  applyAll?.addEventListener('click', async () => {
    if (!applyAllDate?.value) {
      applyAllDate?.focus();
      return;
    }
    if (!window.confirm(`Aplicar a data ${applyAllDate.value.split('-').reverse().join('/')} a todas as bases PHC?`)) return;
    applyAll.disabled = true;
    const original = applyAll.innerHTML;
    applyAll.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i><span>A gravar...</span>';
    try {
      const response = await fetch('/api/phc-close-dates/apply-all', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
        body: JSON.stringify({ value: applyAllDate.value }),
      });
      const payload = await response.json();
      if (!response.ok && !payload.results) throw new Error(payload.error || 'Não foi possível aplicar a data.');
      (payload.results || []).forEach((result) => {
        const row = rows.querySelector(`[data-feid="${result.feid}"]`);
        if (!row) return;
        if (result.ok) {
          row.querySelector('input[type="date"]').value = result.item.value;
          setRowStatus(row, 'Gravado', 'is-ok');
        } else {
          setRowStatus(row, result.error || 'Não foi possível gravar.', 'is-error');
        }
      });
    } catch (error) {
      window.alert(error.message);
    } finally {
      applyAll.disabled = false;
      applyAll.innerHTML = original;
    }
  });
  load();
})();
