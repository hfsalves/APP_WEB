(() => {
  'use strict';

  const app = document.getElementById('employeeInsuranceApp');
  if (!app) return;

  const form = document.getElementById('employeeInsuranceFilters');
  const search = document.getElementById('employeeSearch');
  const nationality = document.getElementById('employeeNationality');
  const profession = document.getElementById('employeeProfession');
  const scope = document.getElementById('employeeExportScope');
  const exportButton = document.getElementById('employeeExportButton');
  const status = document.getElementById('employeeInsuranceStatus');
  const error = document.getElementById('employeeInsuranceError');
  const currentRows = document.getElementById('employeeCurrentRows');
  const departureRows = document.getElementById('employeeDepartureRows');
  const professionDialog = document.getElementById('employeeProfessionDialog');
  const numberFormat = new Intl.NumberFormat('pt-PT');
  const moneyFormat = new Intl.NumberFormat('pt-PT', { style: 'currency', currency: 'EUR' });
  let sort = 'nome';
  let direction = 'asc';

  const escapeHtml = (value) => String(value ?? '').replace(/[&<>"']/g, (character) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
  }[character]));
  const formatDate = (value, includeTime = false) => {
    if (!value) return '—';
    const dateOnly = String(value).match(/^(\d{4})-(\d{2})-(\d{2})$/);
    if (dateOnly && !includeTime) return `${dateOnly[3]}/${dateOnly[2]}/${dateOnly[1]}`;
    const parsed = new Date(value);
    if (Number.isNaN(parsed.getTime())) return escapeHtml(value);
    return new Intl.DateTimeFormat('pt-PT', includeTime
      ? { dateStyle: 'short', timeStyle: 'short' }
      : { day: '2-digit', month: '2-digit', year: 'numeric' }).format(parsed);
  };

  function params() {
    return new URLSearchParams({
      q: search.value.trim(), nacionalidade: nationality.value,
      profissao: profession.value, ordenar: sort, direcao: direction
    });
  }

  function setLoading(loading) {
    exportButton.disabled = loading;
    form.querySelectorAll('button, input, select').forEach((element) => { element.disabled = loading; });
    app.classList.toggle('is-loading', loading);
  }

  function fillSelect(select, items, value, label) {
    const selected = select.value;
    select.innerHTML = `<option value="">${escapeHtml(label)}</option>` + items.map((item) => (
      `<option value="${escapeHtml(value(item))}">${escapeHtml(label === 'Todas' ? item : label)}</option>`
    )).join('');
    select.value = selected;
  }

  function renderEmployee(row, departed = false) {
    const warning = row.incompleto
      ? '<span class="employee-insurance-warning" title="Existem dados obrigatórios em falta"><i class="fa-solid fa-triangle-exclamation"></i></span>'
      : '';
    return `<tr class="${row.novo && !departed ? 'is-new' : ''}">
      <td>${escapeHtml(row.nome)}${warning}</td>
      <td>${escapeHtml(row.nacionalidade || '—')}</td>
      <td>${escapeHtml(row.nif || '—')}</td>
      <td>${escapeHtml(row.niss || '—')}</td>
      <td>${formatDate(row.nascimento)}</td>
      <td>${moneyFormat.format(Number(row.salario_base || 0))}</td>
      <td>${moneyFormat.format(Number(row.subsidio_refeicao || 0))}</td>
      <td><span class="employee-insurance-profession"><strong>${escapeHtml(row.profissao_descricao || 'Sem descrição')}</strong><small>CPP/IEFP ${escapeHtml(row.profissao_codigo || '—')}</small></span></td>
    </tr>`;
  }

  function render(payload) {
    document.querySelectorAll('[data-kpi]').forEach((node) => {
      node.textContent = numberFormat.format(Number(payload.totais?.[node.dataset.kpi] || 0));
    });
    currentRows.innerHTML = payload.atuais.length
      ? payload.atuais.map((row) => renderEmployee(row)).join('')
      : '<tr><td colspan="8" class="employee-insurance-empty">Sem funcionários para os filtros aplicados.</td></tr>';
    departureRows.innerHTML = payload.saidas.length
      ? payload.saidas.map((row) => renderEmployee(row, true)).join('')
      : '<tr><td colspan="8" class="employee-insurance-empty">Sem saídas desde a última emissão.</td></tr>';
    document.getElementById('employeeCurrentSummary').textContent = `${numberFormat.format(payload.totais.visiveis)} de ${numberFormat.format(payload.totais.atuais)} funcionários apresentados`;
    document.getElementById('employeeDepartureSummary').textContent = `${numberFormat.format(payload.saidas.length)} saídas para os filtros aplicados`;
    document.getElementById('employeeLastIssue').textContent = payload.ultima_emissao
      ? `Última emissão: ${formatDate(payload.ultima_emissao.DTEMISSAO, true)} por ${payload.ultima_emissao.UTILIZADOR}.`
      : 'Ainda não existe uma emissão anterior.';

    const selectedNationality = nationality.value;
    nationality.innerHTML = '<option value="">Todas</option>' + payload.opcoes.nacionalidades.map((item) => `<option value="${escapeHtml(item)}">${escapeHtml(item)}</option>`).join('');
    nationality.value = selectedNationality;
    const selectedProfession = profession.value;
    profession.innerHTML = '<option value="">Todas</option>' + payload.opcoes.profissoes.map((item) => `<option value="${escapeHtml(item.codigo)}">${escapeHtml(item.descricao)} (${escapeHtml(item.codigo)})</option>`).join('');
    profession.value = selectedProfession;
  }

  async function load() {
    error.hidden = true;
    status.textContent = 'A carregar funcionários…';
    setLoading(true);
    try {
      const response = await fetch(`${app.dataset.apiUrl}?${params()}`, { credentials: 'same-origin', cache: 'no-store' });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok || !payload.ok) throw new Error(payload.error || `Erro HTTP ${response.status}`);
      render(payload);
      status.textContent = `${numberFormat.format(payload.totais.visiveis)} funcionários visíveis · dados lidos da PE`;
    } catch (exception) {
      error.textContent = exception.message || 'Não foi possível carregar o mapa.';
      error.hidden = false;
      status.textContent = 'Erro ao carregar.';
    } finally {
      setLoading(false);
    }
  }

  async function openProfessions() {
    const list = document.getElementById('employeeProfessionList');
    list.innerHTML = '<div class="employee-insurance-status">A carregar profissões…</div>';
    professionDialog.showModal();
    const response = await fetch(app.dataset.professionsUrl, { credentials: 'same-origin', cache: 'no-store' });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok || !payload.ok) {
      list.innerHTML = `<div class="employee-insurance-error">${escapeHtml(payload.error || 'Não foi possível carregar as profissões.')}</div>`;
      return;
    }
    list.innerHTML = payload.profissoes.map((item) => `<div class="employee-profession-row" data-code="${escapeHtml(item.codigo)}">
      <div class="employee-profession-code">${escapeHtml(item.codigo)}</div>
      <label><span>Descrição CPP/IEFP</span><input class="sz_input" maxlength="200" value="${escapeHtml(item.descricao)}" title="Descrição original: ${escapeHtml(item.descricao_fonte)}"></label>
      <button class="sz_button sz_button_primary" type="button"><i class="fa-solid fa-floppy-disk"></i><span>Guardar</span></button>
    </div>`).join('');
    list.querySelectorAll('.employee-profession-row button').forEach((button) => button.addEventListener('click', async () => {
      const row = button.closest('.employee-profession-row');
      const input = row.querySelector('input');
      button.disabled = true;
      try {
        const saveResponse = await fetch(app.dataset.professionsUrl, {
          method: 'POST', credentials: 'same-origin', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ codigo: row.dataset.code, descricao: input.value.trim() })
        });
        const savePayload = await saveResponse.json().catch(() => ({}));
        if (!saveResponse.ok || !savePayload.ok) throw new Error(savePayload.error || 'Não foi possível guardar.');
        button.innerHTML = '<i class="fa-solid fa-check"></i><span>Guardado</span>';
        await load();
      } catch (exception) {
        window.alert(exception.message);
      } finally {
        button.disabled = false;
      }
    }));
  }

  form.addEventListener('submit', (event) => { event.preventDefault(); load(); });
  document.getElementById('employeeClearFilters').addEventListener('click', () => {
    form.reset(); sort = 'nome'; direction = 'asc'; load();
  });
  document.querySelectorAll('[data-sort]').forEach((button) => button.addEventListener('click', () => {
    const selected = button.dataset.sort;
    direction = sort === selected && direction === 'asc' ? 'desc' : 'asc';
    sort = selected;
    load();
  }));
  exportButton.addEventListener('click', () => {
    const query = params();
    query.set('ambito', scope.value);
    window.location.assign(`${app.dataset.exportUrl}?${query}`);
  });
  document.getElementById('employeeProfessionButton')?.addEventListener('click', openProfessions);
  load();
})();
