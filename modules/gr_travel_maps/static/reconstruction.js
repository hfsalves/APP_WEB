(() => {
  'use strict';
  const root = document.getElementById('travelBuilder'); if (!root) return;
  const $ = id => document.getElementById(id);
  const query = new URLSearchParams(location.search);
  const labels = {km:'Quilómetros', ac_nacional:'AC nacional', ac_estrangeiro:'AC estrangeiro'};
  const fmt = value => value == null ? '—' : new Intl.NumberFormat('pt-PT', {maximumFractionDigits:2}).format(Number(value));
  const eur = value => value == null ? 'Por indicar' : new Intl.NumberFormat('pt-PT', {style:'currency',currency:'EUR'}).format(Number(value));
  // Shared ui.js formats .sz_input decimals with a comma; the API uses decimal strings.
  const numericValue = control => control.value.trim().replace(',', '.');
  let context = null, saved = null, history = [], busy = false, pendingWrite = null, loadSequence = 0;
  const inputRows = new Map(), entryRows = new Map();
  function node(tag, value, className) { const el = document.createElement(tag); if (value != null) el.textContent = value; if(className) el.className=className; return el; }
  function cell(row, value) { const td=node('td',value); row.append(td); return td; }
  function error(message='') { $('builderError').hidden=!message; $('builderError').textContent=message; }
  function field(value, type='text', label='') { const el=node('input'); el.className='sz_input'; el.type=type; if(type==='checkbox') el.checked=!!value; else el.value=value ?? ''; if(label) el.setAttribute('aria-label',label); return el; }
  async function api(path, options={}) {
    const response=await fetch(`${root.dataset.apiBase}/${path}`, {cache:'no-store', ...options, headers:{'Accept':'application/json',...options.headers}});
    if(response.redirected || response.status===401) throw new Error('A sessão expirou. Entre novamente na aplicação.');
    if(response.status===403) throw new Error('Sem permissão ou sessão de edição expirada. Atualize a página.');
    const data=await response.json().catch(()=>null);
    if(!response.ok || !data?.ok) throw new Error(data?.error || 'Não foi possível concluir a operação.');
    return data;
  }
  function controls() {
    const historical = saved && saved.current.version !== saved.header.version;
    const edit = context?.can_edit && context?.storage_ready && !busy;
    $('builderGenerate').disabled=!edit || !context?.sources_current;
    $('builderReload').disabled=busy; $('builderLoadWorks').disabled=busy;
    $('builderSave').disabled=!edit || historical || !saved;
    $('builderReject').disabled=!edit || historical || !saved;
    $('builderValidate').disabled=busy || historical || !saved || !context?.can_validate || !context?.sources_current || saved?.current.state!=='POR_VALIDAR';
    $('builderHistory').disabled=busy;
    for(const row of entryRows.values()) for(const control of Object.values(row)) control.disabled=!edit || historical;
  }
  function companyIds() { return [...$('builderCompanies').querySelectorAll('input:checked')].map(el=>Number(el.value)); }
  function inputs() {
    return {origin:$('builderOrigin').value, origin_country:$('builderCountry').value, allowance_country:$('builderAllowanceCountry').value,
      include_weekends:$('builderWeekends').checked, vehicle:$('builderVehicle').value,
      owner:$('builderOwner').value, note:$('builderNote').value,
      blocked_dates:$('builderBlocked').value.split(',').map(v=>v.trim()).filter(Boolean),
      rates:{km:numericValue($('builderKmRate')), ac_nacional:numericValue($('builderNationalRate')), ac_estrangeiro:numericValue($('builderForeignRate'))},
      works:[...inputRows.entries()].filter(([,r])=>r.use.checked).map(([key,r])=>({key,country:r.country.value,city:r.city.value,
        outward_km:numericValue(r.outward_km),return_km:numericValue(r.return_km),distance_source:r.distance_source.value,max_trips:Number(r.max_trips.value)}))};
  }
  function populateInputs(data) {
    $('builderAllowanceCountry').value=data.allowance_country || 'PT'; $('builderWeekends').checked=!!data.include_weekends;
    for(const [id,key] of [['builderOrigin','origin'],['builderCountry','origin_country'],['builderVehicle','vehicle'],['builderOwner','owner'],['builderNote','note']]) $(id).value=data[key] || '';
    $('builderBlocked').value=(data.blocked_dates || []).join(', ');
    for(const [id,key] of [['builderKmRate','km'],['builderNationalRate','ac_nacional'],['builderForeignRate','ac_estrangeiro']]) $(id).value=data.rates?.[key] ?? '';
  }
  function renderWorks(previous={}) {
    const chosen=new Map((previous.works||[]).map(w=>[w.key,w])); inputRows.clear(); $('builderWorks').replaceChildren();
    for(const work of context.works) {
      const old=chosen.get(work.key); const tr=node('tr'); const controls={use:field(!!old,'checkbox',`Usar ${work.work}`)};
      cell(tr).append(controls.use); const title=cell(tr,`${work.work} · ${work.company.name}`); title.append(node('small',`${work.client} · ${work.evidence.length} auto(s)`));
      for(const [key,value,type,label] of [['country',old?.country||'','text','País'],['city',old?.city??work.locality,'text','Local'],['outward_km',old?.outward_km,'number','Ida km'],['return_km',old?.return_km,'number','Regresso km'],['distance_source',old?.distance_source||'','text','Fonte da distância'],['max_trips',old?.max_trips??10,'number','Máximo de visitas']]) {
        const input=field(value,type,`${label} · ${work.work}`); if(type==='number'){input.min='0';input.step=key==='max_trips'?'1':'.01';input.max=key==='max_trips'?'31':'2500';} if(key==='country'){input.maxLength=2;input.placeholder='PT / FR';} controls[key]=input; cell(tr).append(input);
      }
      inputRows.set(work.key,controls); $('builderWorks').append(tr);
    }
    if(!context.works.length){ const tr=node('tr');const td=cell(tr,'Não há obras candidatas com medição positiva para estas empresas e mês.');td.colSpan=8;$('builderWorks').append(tr); }
  }
  function renderVersion() {
    $('builderResult').hidden=!saved; entryRows.clear(); if(!saved){controls();return;}
    const version=saved.current, doc=version.document, historical=version.version!==saved.header.version;
    $('builderVersionTitle').textContent=`Versão ${version.version} · ${version.state.replaceAll('_',' ')}`;
    $('builderVersionMeta').textContent=`${version.actor} · ${new Date(version.created_at).toLocaleString('pt-PT')} · ${version.reason}`;
    $('builderValidationScope').textContent=doc.validation ? `Âmbito validado: ${doc.validation.scope.map(key=>labels[key]).join(', ')}.` : '';
    $('builderHistorical').hidden=!historical;
    $('builderHistory').replaceChildren(...history.map(item=>{const option=node('option',`v${item.version} · ${item.state} · ${item.actor}`); option.value=item.version; return option;}));
    $('builderHistory').value=version.version;
    $('builderTotals').replaceChildren();
    for(const [key,metric] of Object.entries(doc.reconciliation)){const tr=node('tr');[labels[key],fmt(metric.phc),fmt(metric.map),fmt(metric.difference),metric.percent==null?'—':`${fmt(metric.percent)}%`,eur(metric.amount)].forEach(v=>cell(tr,v));$('builderTotals').append(tr);}
    $('builderWarnings').replaceChildren(...doc.warnings.map(w=>node('li',w)));
    $('builderEntries').replaceChildren();
    for(const entry of doc.entries) {
      const tr=node('tr');const controls={included:field(entry.included,'checkbox',`Incluir ${entry.work} ${entry.date}`)};
      cell(tr).append(controls.included); const kind=cell(tr,labels[entry.category]);kind.append(node('small','INFERIDO · confiança baixa'));
      controls.date=field(entry.date,'date',`Data · ${entry.id}`);cell(tr).append(controls.date);
      const work=cell(tr,`${entry.work} · ${entry.country || 'País por confirmar'}`);controls.city=field(entry.city,'text',`Local · ${entry.id}`);work.append(controls.city);
      for(const key of ['quantity','rate']){controls[key]=field(entry[key],'number',`${key==='quantity'?'Quantidade':'Taxa'} · ${entry.id}`);controls[key].step=key==='rate'||entry.category!=='km'?'.000001':'.01';controls[key].dataset.szDecimals='6';if(key==='quantity')controls[key].dataset.szNoDecimalMask='true';controls[key].min='0';cell(tr).append(controls[key]);}
      controls.reason=field(entry.reason,'text',`Motivo · ${entry.id}`);cell(tr).append(controls.reason);
      const vehicle=cell(tr);for(const key of ['vehicle','owner']) {controls[key]=field(entry[key],'text',`${key==='vehicle'?'Viatura':'Proprietário'} · ${entry.id}`);vehicle.append(controls[key]);}
      entryRows.set(entry.id,controls);$('builderEntries').append(tr);
    }
    $('builderEvidence').textContent=JSON.stringify({payroll:doc.payroll,inputs:doc.inputs,assumptions_by:doc.assumptions_by,entries:doc.entries,validation:doc.validation,content_hash:version.content_hash,previous_hash:version.previous_hash},null,2);
    $('builderAcknowledged').checked=false; controls();
  }
  async function load(keepInputs=false) {
    if(busy)return;const seq=++loadSequence;error();busy=true;controls();
    const previous=keepInputs?inputs():null;
    try{
      const params=new URLSearchParams(query);params.delete('autos_feid');
      if(keepInputs)companyIds().forEach(id=>params.append('autos_feid',id));
      const result=await api(`contexto?${params}`); if(seq!==loadSequence)return;
      context=result;saved=result.saved;history=result.history;
      for(const check of $('builderCompanies').querySelectorAll('input')) check.checked=result.measurement_companies.includes(Number(check.value));
      // The saved snapshot may use other companies; reopen the same evidence selection.
      const chosen=previous || saved?.current.document.inputs;
      $('builderEmployee').textContent=`${result.payroll.employee.name} · ${result.payroll.company.name} · ${result.payroll.year}-${String(result.payroll.month).padStart(2,'0')}`;
      $('builderStatus').textContent=result.storage_ready?'Os valores PHC são preservados em cada versão.':'A consulta está disponível. É necessário instalar o armazenamento para guardar propostas.';
      if(result.source_warnings.length) error(result.source_warnings.join(' '));
      if(chosen)populateInputs(chosen);renderWorks(chosen||{});renderVersion();
    }catch(exc){context=null;$('builderResult').hidden=true;error(exc.message);}finally{busy=false;controls();}
  }
  function changes() {
    return saved.current.document.entries.map(entry=>{const row=entryRows.get(entry.id),change={id:entry.id};
      for(const [key,control] of Object.entries(row)){
        const numeric=key==='rate'||key==='quantity';
        const value=key==='included'?control.checked:numeric?numericValue(control):control.value;
        const same=numeric && value!=='' && entry[key]!=null ? Number(value)===Number(entry[key]) : value===(entry[key]??'');
        if(!same)change[key]=value;}
      return change;
    }).filter(row=>Object.keys(row).length>1);
  }
  async function write(path,payload) {
    if(busy)return;error();busy=true;controls();
    const signature=JSON.stringify({path,payload});
    if(pendingWrite?.signature!==signature) pendingWrite={signature,body:{...payload,request_id:crypto.randomUUID()}};
    try{
      const result=await api(path,{method:'POST',headers:{'Content-Type':'application/json','X-Travel-CSRF':root.dataset.csrf},body:JSON.stringify(pendingWrite.body)});
      pendingWrite=null;saved=result;
      const detail=await api(`propostas/${saved.header.id}`); saved=detail;history=detail.history;
      $('builderReason').value='';$('builderStatus').textContent=`Versão ${saved.current.version} guardada.`;renderVersion();
    }catch(exc){error(exc.message);}finally{busy=false;controls();}
  }
  $('builderForm').addEventListener('submit',event=>{event.preventDefault();if(!context)return;
    const values=inputs();write('propostas',{feid:context.payroll.company.feid,year:context.payroll.year,month:context.payroll.month,employee_key:context.payroll.employee.key,
      measurement_companies:companyIds(),inputs:values,reason:values.note,expected_version:saved?.header.version||0});});
  $('builderSave').addEventListener('click',()=>{const values=changes();if(!values.length){error('Não existem alterações nas linhas.');return;}write(`propostas/${saved.header.id}/editar`,{changes:values,reason:$('builderReason').value,expected_version:saved.header.version});});
  for(const [id,action] of [['builderReject','rejeitar'],['builderValidate','validar']])$(id).addEventListener('click',()=>{
    if(changes().length){error('Guarde primeiro as alterações às linhas.');return;}
    write(`propostas/${saved.header.id}/${action}`,{reason:$('builderReason').value,expected_version:saved.header.version,acknowledge_inference:$('builderAcknowledged').checked});});
  $('builderHistory').addEventListener('change',async()=>{if(busy||!saved)return;busy=true;controls();error();try{saved=await api(`propostas/${saved.header.id}?version=${$('builderHistory').value}`);history=saved.history;renderVersion();}catch(exc){error(exc.message);}finally{busy=false;controls();}});
  $('builderLoadWorks').addEventListener('click',()=>load(true));$('builderReload').addEventListener('click',()=>load());
  (async()=>{try{const companies=await api('empresas');$('builderCompanies').replaceChildren(...companies.rows.map(company=>{const label=node('label');const check=field(String(company.feid)===query.get('feid'),'checkbox');check.value=company.feid;label.append(check,node('span',company.name));return label;}));await load();}catch(exc){error(exc.message);}})();
})();
