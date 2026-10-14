(() => {
  'use strict';
  const root = document.getElementById('travelMaps');
  if (!root) return;
  const $ = id => document.getElementById(id);
  const categories = ['km', 'ac_nacional', 'ac_estrangeiro'];
  const labels = {km: 'Quilómetros', ac_nacional: 'AC nacional', ac_estrangeiro: 'AC estrangeiro'};
  const quantityFormat = new Intl.NumberFormat('pt-PT', {maximumFractionDigits: 2});
  const moneyFormat = new Intl.NumberFormat('pt-PT', {style: 'currency', currency: 'EUR'});
  const rateFormat = new Intl.NumberFormat('pt-PT', {minimumFractionDigits: 2, maximumFractionDigits: 6});
  const fmt = value => value == null ? '—' : quantityFormat.format(Number(value));
  const money = value => value == null ? 'Não configurado' : moneyFormat.format(Number(value));
  const date = value => value ? String(value).slice(0, 10).split('-').reverse().join('/') : '—';
  let employees = [], payroll = null;
  const controllers = {};

  function node(tag, text, className) {
    const result = document.createElement(tag);
    if (text != null) result.textContent = String(text);
    if (className) result.className = className;
    return result;
  }
  function empty(bodyId, columns, message) {
    const td = node('td', message, 'travel-empty'); td.colSpan = columns;
    const row = node('tr'); row.append(td); $(bodyId).replaceChildren(row);
  }
  function messages(id, values, isError = false) {
    $(id).replaceChildren(...values.map(value => node('p', value, isError ? 'travel-error' : 'travel-muted')));
  }
  function cell(row, value, className) { const td = node('td', value, className); row.append(td); return td; }
  function table(headers) {
    const wrap = node('div', null, 'travel-scroll'); wrap.tabIndex = 0;
    const tab = node('table', null, 'sz_table travel-table'); const head = node('thead'); const tr = node('tr');
    headers.forEach(label => tr.append(node('th', label))); head.append(tr);
    const body = node('tbody'); tab.append(head, body); wrap.append(tab); return {wrap, body};
  }
  function periodParams(feid) {
    const [year, month] = $('travelPeriod').value.split('-');
    return new URLSearchParams({feid, ano: year || '', mes: month || ''});
  }
  async function fetchJson(path, signal) {
    const response = await fetch(`${root.dataset.apiBase}/${path}`, {signal, cache: 'no-store', headers: {'Accept': 'application/json'}});
    if (response.redirected || response.status === 401) throw new Error('A sessão expirou. Entre novamente na aplicação.');
    if (response.status === 403) throw new Error('Sem permissão para consultar estes dados.');
    const data = await response.json().catch(() => null);
    if (!response.ok || !data || !data.ok) throw new Error(data?.error || 'Não foi possível consultar os dados. Tente novamente.');
    return data;
  }
  function clearMetrics() {
    ['metricEmployees', 'metricReceipts', 'metricKm', 'metricKmAmount', 'metricNational', 'metricNationalAmount', 'metricForeign', 'metricForeignAmount']
      .forEach(id => { $(id).textContent = '—'; });
  }
  function attachProposals(data) {
    const byEmployee = new Map(data.rows.map(item => [item.employee_key,item]));
    const existing = new Set(employees.map(item => item.key));
    for (const proposal of data.rows) {
      if (existing.has(proposal.employee_key) || proposal.restricted) continue;
      employees.push({key:proposal.employee_key,name:proposal.employee_name,number:proposal.employee_number,
        phc:Object.fromEntries(categories.map(key=>[key,{quantity:null,amount:null}])),receipts:[],lines:[],
        warnings:['Sem recibo PHC atual disponível. O histórico do mapa mantém-se acessível.'],currentPhcMissing:true});
    }
    for (const employee of employees) {
      const proposal=byEmployee.get(employee.key);
      employee.proposalsUnavailable=!!proposal?.restricted;
      employee.proposal=proposal?.restricted ? null : proposal;
      employee.phcChanged=employee.proposal && categories.some(key => ['quantity','amount'].some(field => {
        const before=employee.proposal.snapshot_phc[key][field], now=employee.phc[key][field];
        return (before==null)!==(now==null) || (before!=null && Number(before)!==Number(now));
      }));
    }
  }
  function renderEmployees() {
    const query = $('travelSearch').value.trim().toLocaleLowerCase('pt-PT');
    const visible = employees.filter(item => `${item.number} ${item.name}`.toLocaleLowerCase('pt-PT').includes(query));
    $('travelEmployees').replaceChildren();
    for (const employee of visible) {
      const tr = node('tr');
      const name = cell(tr, employee.name); name.append(node('small', `N.º ${employee.number}`));
      cell(tr, fmt(employee.phc.km.quantity), 'travel-number');
      cell(tr, employee.proposal ? fmt(employee.proposal.reconciliation.km.map) : '—', 'travel-number');
      cell(tr, employee.proposal && !employee.phcChanged ? fmt(employee.proposal.reconciliation.km.difference) : '—', 'travel-number');
      cell(tr, fmt(employee.phc.ac_nacional.quantity), 'travel-number');
      cell(tr, employee.proposal ? fmt(employee.proposal.reconciliation.ac_nacional.map) : '—', 'travel-number');
      cell(tr, fmt(employee.phc.ac_estrangeiro.quantity), 'travel-number');
      cell(tr, employee.proposal ? fmt(employee.proposal.reconciliation.ac_estrangeiro.map) : '—', 'travel-number');
      const status = cell(tr); status.append(node('span', employee.currentPhcMissing ? 'PHC por confirmar' : employee.phcChanged ? 'PHC alterado' : employee.proposal ? employee.proposal.state.replaceAll('_',' ') : employee.proposalsUnavailable ? 'Estado indisponível' : 'Sem mapa', 'travel-badge'));
      if (employee.warnings.length) status.append(node('small', 'Conferência necessária', 'travel-warning'));
      const button = node('button', 'Ver detalhe', 'sz_button sz_button_secondary travel-detail-button'); button.type = 'button';
      button.setAttribute('aria-label', `Ver detalhe de ${employee.name}`);
      button.addEventListener('click', () => openDetail(employee)); cell(tr).append(button);
      $('travelEmployees').append(tr);
    }
    if (!visible.length) empty('travelEmployees', 10, employees.length ? 'Nenhum trabalhador corresponde à pesquisa.' : 'Não existem recibos PHC com data neste mês.');
    $('travelEmployeeCount').textContent = `${visible.length} de ${employees.length} trabalhadores · totais acima relativos ao período completo`;
  }
  function openDetail(employee) {
    $('travelDetailTitle').textContent = employee.name;
    $('travelDetailSubtitle').textContent = `N.º ${employee.number} · ${payroll.company.name} · ${$('travelPeriod').value}`;
    const body = $('travelDetailBody'); body.replaceChildren();
    const link = node('a', 'Abrir reconstrução e histórico', 'sz_button sz_button_primary');
    const params = periodParams($('travelCompany').value); params.set('employee_key',employee.key);
    link.href = `/mapas-deslocacoes/reconstrucao?${params}`; body.append(link);
    body.append(node('p', 'As datas dos recibos abaixo pertencem ao processamento salarial. Consulte a reconstrução para rever propostas, diferenças e versões.', 'travel-notice'));
    employee.warnings.forEach(warning => body.append(node('p', warning, 'travel-warning')));
    const totals = table(['Tipo', 'PHC', 'Valor PHC', 'Mapa', 'Diferença', 'Reconciliação']);
    categories.forEach(category => {
      const tr = node('tr'); cell(tr, labels[category]); cell(tr, fmt(employee.phc[category].quantity));
      cell(tr, employee.currentPhcMissing ? 'Indisponível' : money(employee.phc[category].amount));
      const metric = employee.proposal?.reconciliation[category];
      cell(tr, fmt(metric?.map)); cell(tr, employee.phcChanged ? 'PHC alterado' : fmt(metric?.difference));
      cell(tr, !metric || employee.phcChanged || metric.percent == null ? '—' : `${fmt(metric.percent)}%`); totals.body.append(tr);
    }); body.append(totals.wrap);
    body.append(node('h3', 'Recibos incluídos'));
    const receipts = table(['Recibo', 'Data', 'Ano / mês de referência', 'Estado PHC original']);
    employee.receipts.forEach(item => {
      const tr = node('tr'); cell(tr, item.RECIBO); cell(tr, date(item.DATA));
      cell(tr, [item.ANO, item.MESREF].filter(Boolean).join(' / ') || '—'); cell(tr, item.STATUS ?? '—'); receipts.body.append(tr);
    }); body.append(receipts.wrap);
    body.append(node('h3', 'Linhas das rubricas configuradas'));
    if (!employee.lines.length) body.append(node('p', 'Sem linhas das rubricas configuradas neste período.', 'travel-muted'));
    else {
      const lines = table(['Recibo', 'Rubrica', 'Descrição PHC', 'Quantidade', 'Valor unitário', 'Valor PHC', 'Referência salarial']);
      employee.lines.forEach(item => {
        const data = item.original; const tr = node('tr');
        cell(tr, data.RECIBO); cell(tr, data.CR); const description = cell(tr, data.REM);
        item.warnings.forEach(warning => description.append(node('small', warning, 'travel-warning')));
        cell(tr, fmt(data.RQTT), 'travel-number'); cell(tr, rateFormat.format(Number(data.ERVU)), 'travel-number');
        cell(tr, money(data.ERE), 'travel-number'); cell(tr, date(data.DTREF)); lines.body.append(tr);
      }); body.append(lines.wrap);
    }
    const evidence = node('details'); evidence.append(node('summary', 'Referências das fontes PHC'));
    const refs = table(['Base', 'Recibo · PRSTAMP', 'Linha · PRRESTAMP']);
    employee.lines.forEach(item => { const tr = node('tr'); cell(tr, item.source.database); cell(tr, item.original.PRSTAMP); cell(tr, item.source.stamp); refs.body.append(tr); });
    evidence.append(refs.wrap); body.append(evidence);
    $('travelDetail').showModal();
  }
  async function loadMonthly() {
    controllers.payroll?.abort(); const controller = new AbortController(); controllers.payroll = controller;
    employees = []; payroll = null; clearMetrics(); $('travelDetail').close(); $('travelReadAt').textContent = '';
    $('travelCriteria').hidden = true;
    $('travelEmployeeCount').textContent = ''; empty('travelEmployees', 10, 'A consultar os recibos PHC…'); messages('travelPayrollMessages', []);
    try {
      const data = await fetchJson(`mensal?${periodParams($('travelCompany').value)}`, controller.signal);
      if (controller.signal.aborted) return;
      payroll = data; employees = data.rows;
      $('metricEmployees').textContent = fmt(data.employee_count); $('metricReceipts').textContent = `${data.receipt_count} recibos · ${data.line_count} linhas`;
      [['km', 'Km'], ['ac_nacional', 'National'], ['ac_estrangeiro', 'Foreign']].forEach(([key, suffix]) => {
        $(`metric${suffix}`).textContent = fmt(data.totals[key].quantity); $(`metric${suffix}Amount`).textContent = money(data.totals[key].amount);
      });
      const missing = categories.filter(key => data.mapping?.codes[key] == null).map(key => labels[key]);
      const notices = [];
      if (missing.length) notices.push(`Rubricas por configurar: ${missing.join(', ')}. Os respetivos valores não são apresentados como zero.`);
      try {
        const proposals = await fetchJson(`propostas?${periodParams($('travelCompany').value)}`, controller.signal);
        if (controller.signal.aborted) return;
        attachProposals(proposals);
      } catch (error) {
        if (controller.signal.aborted) return;
        employees.forEach(employee => { employee.proposalsUnavailable=true; });
        notices.push(`Propostas indisponíveis: ${error.message}`);
      }
      messages('travelPayrollMessages', notices);
      messages('travelCriteriaBody', data.warnings); $('travelCriteria').hidden = false;
      $('travelReadAt').textContent = `Consulta em ${new Date(data.read_at).toLocaleString('pt-PT', {timeZone: 'Europe/Lisbon'})} · ${data.company.phc_db}`;
      renderEmployees();
    } catch (error) {
      if (controller.signal.aborted) return;
      empty('travelEmployees', 10, 'Valores PHC indisponíveis.'); messages('travelPayrollMessages', [error.message], true);
      try {
        const proposals = await fetchJson(`propostas?${periodParams($('travelCompany').value)}`, controller.signal);
        if (controller.signal.aborted) return;
        payroll=proposals; employees=[]; attachProposals(proposals);
        if(employees.length) renderEmployees();
      } catch (_) { /* Preserve the original PHC error; never fabricate zero totals. */ }
    }
  }
  async function loadAutos() {
    controllers.autos?.abort(); const controller = new AbortController(); controllers.autos = controller;
    empty('travelAutos', 5, 'A consultar os autos de medição…'); messages('travelAutosMessages', []); $('travelAutoCount').textContent = '';
    try {
      const data = await fetchJson(`autos?${periodParams($('travelWorksCompany').value)}`, controller.signal);
      if (controller.signal.aborted) return;
      $('travelAutos').replaceChildren();
      data.rows.forEach(item => {
        const tr = node('tr'); const auto = cell(tr, `${item.series} · ${item.number}`); auto.append(node('small', date(item.date)));
        const work = cell(tr, item.work || 'Obra por identificar'); work.append(node('small', item.description));
        cell(tr, item.client);
        const location = cell(tr, [item.address, item.locality].filter(Boolean).join(' · ') || 'Local por confirmar');
        if (item.work_matches !== 1) location.append(node('small', 'Ligação ao cadastro por confirmar'));
        cell(tr, item.has_positive_measurement ? 'Positiva · obra candidata' : 'Sem medição positiva');
        $('travelAutos').append(tr);
      });
      if (!data.rows.length) empty('travelAutos', 5, data.source_state === 'UNCONFIGURED' ? 'Não foram identificadas séries de autos de cliente nesta empresa.' : 'Não existem autos não anulados com data neste mês.');
      $('travelAutoCount').textContent = `${data.rows.length} autos · ${data.work_count} obras candidatas · ${data.company.name}`;
      messages('travelAutosMessages', []);
    } catch (error) {
      if (controller.signal.aborted) return;
      empty('travelAutos', 5, 'Autos indisponíveis.'); messages('travelAutosMessages', [error.message], true);
    }
  }
  function refresh() {
    if (!$('travelFilters').reportValidity() || !$('travelCompany').value) {
      controllers.payroll?.abort(); controllers.autos?.abort(); employees = []; payroll = null;
      clearMetrics(); $('travelDetail').close(); $('travelCriteria').hidden = true;
      $('travelReadAt').textContent = ''; $('travelEmployeeCount').textContent = ''; $('travelAutoCount').textContent = '';
      messages('travelPayrollMessages', []); messages('travelAutosMessages', []);
      empty('travelEmployees', 10, 'Selecione uma empresa e um mês válidos.'); empty('travelAutos', 5, 'Selecione um mês válido.');
      return;
    }
    return Promise.allSettled([loadMonthly(), loadAutos()]);
  }
  $('travelFilters').addEventListener('submit', event => { event.preventDefault(); if (!$('travelCompany').value) initialize(); else refresh(); });
  $('travelCompany').addEventListener('change', () => { $('travelWorksCompany').value = $('travelCompany').value; refresh(); });
  $('travelPeriod').addEventListener('change', refresh);
  $('travelWorksCompany').addEventListener('change', loadAutos);
  $('travelSearch').addEventListener('input', () => { if (payroll) renderEmployees(); });
  $('travelCloseDetail').addEventListener('click', () => $('travelDetail').close());

  async function initialize() {
    $('travelRefresh').disabled = true; $('travelCompaniesError').hidden = true;
    try {
      const data = await fetchJson('empresas');
      ['travelCompany', 'travelWorksCompany'].forEach(id => {
        $(id).replaceChildren(...data.rows.map(company => { const option = node('option', company.name); option.value = company.feid; return option; }));
        if (data.rows.some(company => String(company.feid) === root.dataset.feid)) $(id).value = root.dataset.feid;
        $(id).disabled = !data.rows.length;
      });
      $('travelRefresh').disabled = !data.rows.length;
      if (!data.rows.length) {
        empty('travelEmployees', 10, 'Sem empresas PHC acessíveis.'); empty('travelAutos', 5, 'Sem empresas PHC acessíveis.'); return;
      }
      await refresh();
    } catch (error) {
      $('travelRefresh').disabled = false;
      $('travelCompaniesError').hidden = false; $('travelCompaniesError').textContent = error.message;
      empty('travelEmployees', 10, 'Empresas indisponíveis.');
    }
  }
  initialize();
})();
