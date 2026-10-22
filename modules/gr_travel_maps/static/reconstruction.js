(() => {
  'use strict';
  const root=document.getElementById('travelBuilder'); if(!root)return;
  const $=id=>document.getElementById(id), query=new URLSearchParams(location.search);
  const labels={km:'Quilómetros',ac_nacional:'AC nacional',ac_estrangeiro:'AC estrangeiro'};
  const fmt=v=>v==null?'—':new Intl.NumberFormat('pt-PT',{maximumFractionDigits:2}).format(Number(v));
  const eur=v=>v==null?'—':new Intl.NumberFormat('pt-PT',{style:'currency',currency:'EUR'}).format(Number(v));
  const numeric=c=>c.value.trim().replace(',','.');
  const preferenceKey=`gr-travel-companies:${root.dataset.preferenceKey}`;
  let context=null,saved=null,draft=null,history=[],busy=false,pendingWrite=null,progressState=null;
  const locations=new Map(),editRows=new Map();
  const node=(tag,value,cls)=>{const el=document.createElement(tag);if(value!=null)el.textContent=value;if(cls)el.className=cls;return el;};
  const cell=(row,value)=>{const el=node('td',value);row.append(el);return el;};
  const field=(value,type,label)=>{const el=node('input');el.type=type;el.className='sz_input';if(type==='checkbox')el.checked=!!value;else el.value=value??'';el.setAttribute('aria-label',label);return el;};
  const doc=()=>draft||saved?.current.document;
  const historical=()=>!!saved&&saved.current.version!==saved.header.version;
  const onDay=(entry,day)=>(entry.driving_dates||[entry.date]).includes(day);
  const dailyKm=(entry,day)=>entry.daily_km?.[day]??entry.quantity;
  function error(message=''){for(const id of ['builderError','calendarDayError']){$(id).hidden=!message;$(id).textContent=message;}}
  function updateProgress(item){
    if(!progressState)return;
    progressState.updated=performance.now();
    $('builderProgressTitle').textContent=item.message;$('builderProgressDetail').textContent=item.detail||'';
    const bar=$('builderProgressBar'),count=$('builderProgressCount');
    if(Number.isInteger(item.total)&&item.total>0){bar.max=item.total;bar.value=item.completed||0;}
    else bar.removeAttribute('value');
    if(item.phase==='locations')count.textContent=`${item.completed} de ${item.total} locais verificados (casa e obras) · ${item.resolved} localizados · ${item.unresolved} por resolver`;
    else if(item.phase==='measurements')count.textContent=`${item.completed} de ${item.total} empresas consultadas`;
    else count.textContent='';
  }
  function progressTime(){
    if(!progressState)return;
    const seconds=Math.floor((performance.now()-progressState.started)/1000),wait=Math.floor((performance.now()-progressState.updated)/1000);
    $('builderProgressTime').textContent=`Tempo decorrido: ${Math.floor(seconds/60)}m ${String(seconds%60).padStart(2,'0')}s${progressState.timer&&wait>=15?` · Há ${wait}s sem nova atualização do servidor`:''}`;
  }
  function startProgress(){
    if(progressState?.timer)clearInterval(progressState.timer);
    progressState={started:performance.now(),updated:performance.now(),timer:null};
    $('builderProgress').hidden=false;$('builderProgress').classList.remove('travel-progress-failed');$('builderProgressBar').hidden=false;
    updateProgress({phase:'preparing',message:'A atualizar os dados PHC e os autos das empresas selecionadas…'});
    progressState.timer=setInterval(progressTime,1000);progressTime();
    $('builderProgress').scrollIntoView({behavior:'smooth',block:'nearest'});
  }
  function stopProgress(failed=false){
    if(!progressState?.timer)return;
    clearInterval(progressState.timer);progressState.timer=null;progressTime();
    $('builderProgress').classList.toggle('travel-progress-failed',failed);
    if(failed){$('builderProgressTitle').textContent='Reconstrução interrompida';$('builderProgressBar').hidden=true;}
    else{updateProgress({phase:'complete',message:draft?'Pré-visualização calculada.':'Proposta guardada para revisão.'});$('builderProgressBar').max=1;$('builderProgressBar').value=1;}
  }
  async function api(path,options={}){
    const response=await fetch(`${root.dataset.apiBase}/${path}`,{cache:'no-store',...options,headers:{Accept:'application/json',...options.headers}});
    if(response.redirected||response.status===401)throw new Error('A sessão expirou. Entre novamente.');
    if(response.status===403)throw new Error('Sem permissão ou sessão expirada. Atualize a página.');
    const data=await response.json().catch(()=>null);if(!response.ok||!data?.ok)throw new Error(data?.error||'Não foi possível concluir a operação.');return data;
  }
  async function streamedWrite(path,options){
    const response=await fetch(`${root.dataset.apiBase}/${path}`,{cache:'no-store',...options,headers:{...options.headers,Accept:'application/x-ndjson'}});
    if(response.redirected||response.status===401)throw new Error('A sessão expirou. Entre novamente.');
    if(response.status===403)throw new Error('Sem permissão ou sessão expirada. Atualize a página.');
    if(!response.ok||!response.headers.get('Content-Type')?.includes('application/x-ndjson')){
      const data=await response.json().catch(()=>null);
      if(response.ok&&data?.ok)return data;
      throw new Error(data?.error||'Não foi possível iniciar a reconstrução.');
    }
    if(!response.body)throw new Error('Não foi possível acompanhar a reconstrução. Atualize os dados para verificar se a proposta ficou guardada.');
    const reader=response.body.getReader(),decoder=new TextDecoder();let buffer='',result=null;
    function accept(line){
      if(!line.trim())return;
      const item=JSON.parse(line);
      if(item.type==='progress')updateProgress(item);
      else if(item.type==='error')throw new Error(item.error||'A reconstrução foi interrompida.');
      else if(item.type==='result'&&item.ok)result=item;
    }
    try{
      while(true){const {done,value}=await reader.read();buffer+=decoder.decode(value,{stream:!done});let newline;
        while((newline=buffer.indexOf('\n'))!==-1){accept(buffer.slice(0,newline));buffer=buffer.slice(newline+1);}
        if(done){if(buffer.trim())accept(buffer);break;}
      }
    }catch(exc){
      await reader.cancel().catch(()=>{});
      if(exc instanceof TypeError||exc instanceof SyntaxError)throw new Error('A ligação à reconstrução foi interrompida. Atualize os dados para verificar se a proposta ficou guardada.');
      throw exc;
    }finally{reader.releaseLock();}
    if(!result)throw new Error('A reconstrução terminou sem confirmação. Atualize os dados antes de tentar novamente.');
    return result;
  }
  function remembered(){try{const ids=JSON.parse(localStorage.getItem(preferenceKey));return Array.isArray(ids)?ids.filter(Number.isInteger):null;}catch{return null;}}
  function companyIds(){return [...$('builderCompanies').querySelectorAll('input:checked')].map(el=>Number(el.value));}
  function remember(){try{localStorage.setItem(preferenceKey,JSON.stringify(companyIds()));}catch{/* Browser storage is optional. */}}
  function controls(){
    const editable=context?.can_edit&&!busy;
    $('builderGenerate').disabled=!editable||!context?.sources_current;
    const reconstructing=!!progressState?.timer;
    $('builderGenerate').textContent=reconstructing?'A reconstruir calendário…':'Reconstruir calendário automaticamente';
    $('builderGenerate').setAttribute('aria-busy',String(reconstructing));
    $('builderReload').disabled=busy;$('builderHistory').disabled=busy;
    $('builderReject').disabled=!editable||!saved||!!draft||historical();
    $('builderValidate').disabled=busy||!saved||!!draft||historical()||!context?.can_validate||!context?.sources_current||saved?.current.state!=='POR_VALIDAR';
    $('calendarDaySave').disabled=!editable||!saved||!!draft||historical();
    for(const el of $('builderForm').querySelectorAll('input,textarea,select'))el.disabled=busy;
    for(const row of locations.values())for(const key of ['address','country','lat','lon'])row[key].disabled=busy;
  }
  function values(){
    const overrides={};for(const [key,row] of locations){const value={};for(const name of ['address','country','lat','lon']){
      const v=row[name].value.trim();if(v!==row.original[name]||(name==='lat'||name==='lon')&&v)value[name]=v;
    }if(Object.keys(value).length)overrides[key]=value;}
    return {origin:$('builderOrigin').value,origin_country:$('builderCountry').value,vehicle:$('builderVehicle').value,owner:$('builderOwner').value,
      allowance_country:$('builderAllowanceCountry').value,include_weekends:$('builderWeekends').checked,return_policy:$('builderReturnPolicy').value,
      max_driving_hours:numeric($('builderDrivingHours')),blocked_dates:$('builderBlocked').value.split(',').map(v=>v.trim()).filter(Boolean),note:$('builderNote').value,
      rates:{km:numeric($('builderKmRate')),ac_nacional:numeric($('builderNationalRate')),ac_estrangeiro:numeric($('builderForeignRate'))},locations:overrides};
  }
  function populate(input){
    for(const [id,key] of [['builderOrigin','origin'],['builderVehicle','vehicle'],['builderOwner','owner'],['builderNote','note']])$(id).value=input[key]||'';
    $('builderCountry').value=input.origin_country||'PT';$('builderAllowanceCountry').value=input.allowance_country||'PT';
    $('builderWeekends').checked=!!input.include_weekends;$('builderReturnPolicy').value=input.return_policy||'auto';$('builderDrivingHours').value=input.max_driving_hours||'10';
    $('builderBlocked').value=(input.blocked_dates||[]).join(', ');
    for(const [id,key] of [['builderKmRate','km'],['builderNationalRate','ac_nacional'],['builderForeignRate','ac_estrangeiro']])$(id).value=input.rates?.[key]??'';
    profileSources();renderLocations(input.locations||{});
  }
  function profileSources(){
    const profile=context?.payroll.employee_profile||{};
    for(const [id,source,key] of [['builderOrigin','builderOriginSource','origin'],['builderVehicle','builderVehicleSource','vehicle']]){
      const value=$(id).value.trim(),ref=profile.provenance?.[key]?.references?.[0];
      $(source).textContent=value&&value===profile[key]&&ref?`Fonte: ${ref.table}.${ref.fields.join(' / ')} (ficha atual).`:value?'Valor da proposta ou declarado, a confirmar.':key==='origin'?'Morada por indicar.':'Matrícula particular não preenchida no PHC.';
    }
  }
  function renderLocations(overrides={}){
    locations.clear();$('builderLocations').replaceChildren();if(!context)return;
    const points=[{key:'home',label:'Casa',address:$('builderOrigin').value,country:$('builderCountry').value},...context.works.map(w=>({key:w.key,label:`${w.work} · ${w.company.name}${w.hypothetical?' · Outra equipa — visita hipotética':''}`,address:[...new Set([w.address,w.locality].filter(Boolean))].join(', '),country:''}))];
    for(const point of points){const tr=node('tr'),row={original:{address:point.address,country:point.country,lat:'',lon:''}};cell(tr,point.label);
      for(const key of ['address','country','lat','lon']){row[key]=field(overrides[point.key]?.[key]??row.original[key],'text',`${key} · ${point.label}`);if(key==='country')row[key].maxLength=2;cell(tr).append(row[key]);}
      const located=doc()?.routes?.locations?.[point.key],missing=doc()?.routes?.unresolved?.find(item=>item.key===point.key);
      cell(tr,missing?.reason|| (located?`${located.precision} · ${located.matched_label||located.label}`:'Por localizar automaticamente'));
      locations.set(point.key,row);$('builderLocations').append(tr);
    }
  }
  const dateLabel=value=>value.split('-').reverse().join('/');
  function shownPeriod(){
    const payroll=doc()?.payroll||context.payroll;
    if(payroll.map_period)return payroll.map_period;
    // Old immutable versions retain their original calendar-month boundaries.
    const {year,month}=payroll,iso=d=>d.toISOString().slice(0,10);
    return {start:iso(new Date(Date.UTC(year,month-1,1))),end:iso(new Date(Date.UTC(year,month,0)))};
  }
  function allDays(){
    if(!context)return[];
    const period=shownPeriod(),end=new Date(`${period.end}T00:00:00Z`),days=[];
    for(let day=new Date(`${period.start}T00:00:00Z`);day<=end;day.setUTCDate(day.getUTCDate()+1))days.push(day.toISOString().slice(0,10));
    return days;
  }
  function render(){
    const document=doc(),employee=context?.payroll.employee;
    const period=shownPeriod(),next=context.payroll.map_period;
    $('builderMapPeriod').textContent=`Calendário: ${dateLabel(period.start)} a ${dateLabel(period.end)} · PHC: ${context.payroll.year}-${String(context.payroll.month).padStart(2,'0')}`;
    $('builderNewPeriod').textContent=next?`Nova reconstrução: ${dateLabel(next.start)} a ${dateLabel(next.end)}.`:'';
    $('builderPeriodChanged').hidden=!next||(period.start===next.start&&period.end===next.end);
    $('builderPeriodChanged').textContent=next?`Esta versão conserva o período anterior. Reconstrua para criar uma nova versão de ${dateLabel(next.start)} a ${dateLabel(next.end)}.`:'';
    const plan=document?document.planning:context?.planning;
    const acCalendar=document?.allowance_calendar;
    $('builderPlanningSummary').textContent=plan?`${plan.days_with_assignments} dias com associação de equipa · ${plan.works.length} obras da equipa · ${plan.extra_works?.length||0} obras de outras equipas para visitas hipotéticas · ${Object.keys(plan.blocked_dates).length} dias com impedimentos. ${acCalendar?`${acCalendar.weekend_days} dias de fim de semana elegíveis por permanência inferida. `:''}AC apenas com trabalho registado ou continuidade de sexta a segunda na mesma obra.`:'Versão anterior baseada apenas nos autos. Uma nova reconstrução consulta o planeamento.';
    $('builderSourceNotice').textContent=plan?'Obras e datas apoiadas no planeamento e no histórico das equipas. A presença individual, as deslocações e as ajudas de custo continuam sujeitas a confirmação.':'Proposta histórica baseada nos autos; as datas e a associação do trabalhador às obras foram inferidas.';
    $('builderWeekendsField').hidden=!!context?.planning;
    const outcome=document?.result,diagnostics=document?.routes?.diagnostics;
    $('builderOutcome').hidden=!outcome;
    $('builderOutcomeText').textContent=outcome?.message||'';
    $('builderOutcome').classList.toggle('travel-outcome-blocked',outcome?.status==='BLOCKED');
    $('builderDiagnostics').textContent=diagnostics?`${diagnostics.works_considered} obras ${plan?'do planeamento':'com medição'} · ${diagnostics.locations_resolved} locais resolvidos · ${diagnostics.road_legs_calculated} percursos calculados` : '';
    $('builderWarningsDetails').open=outcome?.status==='BLOCKED';
    $('builderLocationsDetails').open=outcome?.status==='BLOCKED'&&outcome.unresolved_locations>0;
    $('builderTotals').replaceChildren();if(employee)for(const key of Object.keys(labels)){const m=document?.reconciliation[key],tr=node('tr');[labels[key],fmt(m?m.phc:employee.phc[key].quantity),fmt(m?.map),fmt(m?.difference),m?.percent==null?'—':`${fmt(m.percent)}%`,eur(m?.amount)].forEach(v=>cell(tr,v));$('builderTotals').append(tr);}
    $('builderVersionTitle').textContent=draft?'Pré-visualização — não guardada':saved?`Calendário · versão ${saved.current.version} · ${saved.current.state.replaceAll('_',' ')}`:'Dias do período';
    $('builderVersionMeta').textContent=saved&&!draft?`${saved.current.actor} · ${new Date(saved.current.created_at).toLocaleString('pt-PT')} · ${saved.current.reason}`:'';
    $('builderHistorical').hidden=!historical()||!!draft;$('builderHistoryLabel').hidden=!saved;
    $('builderHistory').replaceChildren(...history.map(v=>{const o=node('option',`v${v.version} · ${v.state} · ${v.actor}`);o.value=v.version;return o;}));if(saved)$('builderHistory').value=saved.current.version;
    $('builderCalendar').replaceChildren();
    const settings=document?.inputs||values(),blocked=new Set(settings.blocked_dates||[]);
    for(const day of allDays()){
      const assignments=(plan?.records||[]).filter(item=>item.date===day);
      const tr=node('tr'),date=new Date(`${day}T12:00:00Z`),weekend=[0,6].includes(date.getUTCDay()),excluded=blocked.has(day)||(plan?!!plan.blocked_dates[day]:weekend&&!settings.include_weekends);
      if(excluded)tr.className='travel-calendar-excluded';
      const dateCell=cell(tr);dateCell.append(node('strong',`${day.slice(-2)}/${day.slice(5,7)}`),node('small',new Intl.DateTimeFormat('pt-PT',{weekday:'long',timeZone:'UTC'}).format(date)));
      const plannedCell=cell(tr);
      const weekendStay=acCalendar?.days.find(item=>item.date===day&&item.basis==='PERMANENCIA_FIM_SEMANA');
      if(assignments.length)for(const item of assignments){const work=plan.works.find(w=>w.key===item.work_key);plannedCell.append(node('div',`${item.team} · ${work?.planning_work||work?.work||'Obra'}`,'travel-calendar-leg'));}
      else if(weekendStay){const work=plan.works.find(w=>w.key===weekendStay.work_key);plannedCell.append(node('div',`Permanência inferida · ${work?.planning_work||work?.work||'Obra'}`,'travel-calendar-leg'),node('small','Sexta e segunda na mesma obra · sem trabalho registado neste dia','travel-muted'));}
      else plannedCell.append(node('span',plan?.blocked_dates[day]||(plan?'Sem associação registada':'Sem planeamento nesta versão'),'travel-muted'));
      const entries=(document?.entries||[]).filter(e=>onDay(e,day)),km=entries.filter(e=>e.category==='km'),ac=entries.filter(e=>e.category!=='km');
      const routeCell=cell(tr);if(km.length)for(const entry of km){const line=node('div',`${entry.from_label||entry.origin} → ${entry.to_label||entry.destination} · ${fmt(dailyKm(entry,day))} km${entry.driving_dates?` · em viagem (${entry.driving_dates.indexOf(day)+1}/${entry.driving_dates.length})`:''}${entry.approximate_distance?' · aproximado':''}`,'travel-calendar-leg');if(!entry.included)line.classList.add('travel-rejected');routeCell.append(line);if(entry.hypothesis){const tag=node('small','HIPÓTESE · sem registo da deslocação','travel-hypothesis');tag.title=entry.hypothesis_reason;routeCell.append(tag);}}
      else{let stay='';for(const journey of document?.journeys||[]){const legs=document.entries.filter(e=>e.included&&e.journey_id===journey.id).sort((a,b)=>a.leg_index-b.leg_index);if(legs.length&&legs[0].date<day&&legs[legs.length-1].date>day){const previous=legs.filter(e=>e.date<day).at(-1);if(previous)stay=`Permanência inferida: ${previous.to_label}`;}}
        routeCell.append(node('span',stay|| (excluded?'Dia excluído':document?'Sem deslocação proposta':'A aguardar reconstrução'),'travel-muted'));}
      cell(tr,km.length?fmt(km.filter(e=>e.included).reduce((sum,e)=>sum+Number(dailyKm(e,day)),0)):'—');
      const acCell=cell(tr);if(ac.length)for(const entry of ac){const line=node('div',`${labels[entry.category]} · ${fmt(entry.quantity)} dia(s) · ${entry.work}${entry.allowance_basis==='PERMANENCIA_FIM_SEMANA'?' · permanência de fim de semana':''}`);if(!entry.included)line.className='travel-rejected';acCell.append(line);}else acCell.textContent='—';
      const state=cell(tr);if(entries.length){state.append(node('small',`INFERIDO · ${saved&&!draft?saved.current.state.replaceAll('_',' '):'POR VALIDAR'}`));const button=node('button','Rever dia','sz_button sz_button_secondary');button.type='button';button.addEventListener('click',()=>openDay(day));state.append(button);}else state.textContent=excluded?'Excluído':'—';
      $('builderCalendar').append(tr);
    }
    $('builderWarnings').replaceChildren(...(document?.warnings||[...(context?.payroll.employee_profile?.warnings||[]),...(plan?.warnings||[])]).map(w=>node('li',w)));
    $('builderEvidence').textContent=document?JSON.stringify(document,null,2):'Sem proposta.';
    $('builderReview').hidden=!saved||!!draft;$('builderValidationScope').textContent=document?.validation?`Âmbito validado: ${document.validation.scope.map(k=>labels[k]).join(', ')}.`:'';
    $('builderHypothesesField').hidden=!(document?.entries||[]).some(e=>e.included&&e.hypothesis);
    $('builderHypothesesConfirmed').checked=false;$('builderAcknowledged').checked=false;controls();
  }
  async function load(keep=false){
    const old=keep?values():null,selected=keep?companyIds():remembered();
    const params=new URLSearchParams(query);params.delete('autos_feid');if(selected?.length)selected.forEach(id=>params.append('autos_feid',id));
    const result=await api(`contexto?${params}`);context=result;saved=result.saved;draft=null;history=result.history;
    for(const check of $('builderCompanies').querySelectorAll('input'))check.checked=result.measurement_companies.includes(Number(check.value));
    $('builderEmployee').textContent=`${result.payroll.employee.name} · ${result.payroll.company.name} · ${result.payroll.year}-${String(result.payroll.month).padStart(2,'0')}`;
    const profile=result.payroll.employee_profile||{};populate(old||saved?.current.document.inputs||{origin:profile.origin,vehicle:profile.vehicle});render();
    $('builderStatus').textContent=result.storage_ready?'Cada reconstrução guardada cria uma versão. Os valores PHC são preservados.':'A gravação dos mapas está indisponível. Pode calcular uma pré-visualização, mas ainda não pode guardar nem validar.';
    if(result.source_warnings.length)error(result.source_warnings.join(' '));
  }
  async function write(path,payload,stream=false){
    const signature=JSON.stringify({path,payload});if(pendingWrite?.signature!==signature)pendingWrite={signature,body:{...payload,request_id:crypto.randomUUID()}};
    const result=await (stream?streamedWrite:api)(path,{method:'POST',headers:{'Content-Type':'application/json','X-Travel-CSRF':root.dataset.csrf},body:JSON.stringify(pendingWrite.body)});pendingWrite=null;
    if(result.persisted===false){draft=result.document;$('builderStatus').textContent=draft.result?.status==='BLOCKED'?'Não foi possível reconstruir este mapa. Consulte o diagnóstico abaixo.':'Pré-visualização disponível. Ainda não foi guardada nem validada.';}
    else{saved=await api(`propostas/${result.header.id}`);history=saved.history;draft=null;$('builderStatus').textContent=`Versão ${saved.current.version} guardada.`;}
    render();renderLocations(doc()?.inputs.locations||{});
  }
  async function perform(callback){if(busy)return;busy=true;error();controls();try{await callback();}catch(exc){stopProgress(true);error(exc.message);}finally{busy=false;controls();}}
  $('builderForm').addEventListener('submit',event=>{event.preventDefault();perform(async()=>{
    if(!companyIds().length)throw new Error('Selecione pelo menos uma empresa de autos.');remember();startProgress();controls();await load(true);
    if(!context.sources_current)throw new Error('As fontes atuais estão indisponíveis. Tente atualizar os dados.');
    $('builderStatus').textContent='Reconstrução em curso. Acompanhe o progresso junto ao botão.';
    const input=values();await write(context.storage_ready?'propostas':'prever',{mode:'AUTOMATIC',feid:context.payroll.company.feid,year:context.payroll.year,month:context.payroll.month,employee_key:context.payroll.employee.key,
      measurement_companies:companyIds(),inputs:input,reason:input.note||'Reconstrução pelas equipas e datas do planeamento, com evidência adicional dos autos.',expected_version:saved?.header.version||0},true);
    stopProgress();
    $('builderOutcome').scrollIntoView({behavior:'smooth',block:'start'});
  });});
  function openDay(day){
    error();
    const document=doc(),today=document.entries.filter(e=>onDay(e,day)),ids=new Set(today.map(e=>e.journey_id).filter(Boolean));
    const entries=document.entries.filter(e=>e.date===day||ids.has(e.journey_id));editRows.clear();$('calendarDayLines').replaceChildren();$('calendarDayTitle').textContent=`Rever ${day}`;$('calendarDayReason').value='';
    for(const entry of entries){const section=node('section',null,'travel-day-line');section.append(node('h3',entry.category==='km'?`${entry.from_label||entry.origin} → ${entry.to_label||entry.destination}`:`${labels[entry.category]} · ${entry.work}`));
      if(entry.hypothesis)section.append(node('p',entry.hypothesis_reason,'travel-hypothesis'));
      if(entry.allowance_basis==='PERMANENCIA_FIM_SEMANA'){const basis=entry.provenance.allowance_calendar;section.append(node('p',`Permanência inferida pela mesma obra em ${dateLabel(basis.friday)} (sexta) e ${dateLabel(basis.monday)} (segunda). Presença no fim de semana por confirmar.`,'travel-muted'));}
      if(entry.driving_dates)section.append(node('p',`${entry.start_date} a ${entry.end_date} · ${fmt(entry.quantity)} km no total. Distribuição diária inferida; locais de pernoita desconhecidos. Para alterar o percurso ou as datas, ajuste os pressupostos e reconstrua.`,'travel-muted'));
      const row={};const grid=node('div',null,'travel-input-grid');
      for(const [key,label,type] of [['included','Incluir viagem','checkbox'],['date','Data','date'],['quantity',entry.category==='km'?'KM':'Dias','number'],['rate','Valor unitário','number'],['vehicle','Matrícula','text'],['owner','Proprietário','text'],['reason','Motivo','text']]){
        const wrapper=node('label',label,'sz_field'),input=field(entry[key],type,`${label} · ${entry.id}`);if(type==='number'){input.step=key==='rate'||entry.category!=='km'?'.000001':'.01';input.dataset.szDecimals='6';input.dataset.szNoDecimalMask='true';input.min='0';}
        input.disabled=!!draft||historical()||!context.can_edit||!!entry.driving_dates&&['date','quantity'].includes(key);row[key]=input;wrapper.append(input);grid.append(wrapper);
      }
      row.included.addEventListener('change',()=>{if(entry.journey_id)for(const related of entries.filter(e=>e.journey_id===entry.journey_id)){const controls=editRows.get(related.id);if(controls)controls.included.checked=row.included.checked;}});
      editRows.set(entry.id,row);section.append(grid);$('calendarDayLines').append(section);
    }
    $('calendarDayDialog').showModal();controls();
  }
  $('calendarDayClose').addEventListener('click',()=>$('calendarDayDialog').close());
  $('calendarDaySave').addEventListener('click',()=>perform(async()=>{
    const changes=[];for(const entry of saved.current.document.entries){const row=editRows.get(entry.id);if(!row)continue;const change={id:entry.id};
      for(const [key,control] of Object.entries(row)){const value=key==='included'?control.checked:['quantity','rate'].includes(key)?numeric(control):control.value;
        const same=['quantity','rate'].includes(key)&&value!==''&&entry[key]!=null?Number(value)===Number(entry[key]):value===(entry[key]??'');if(!same)change[key]=value;}
      if(Object.keys(change).length>1)changes.push(change);
    }if(!changes.length)throw new Error('Não existem alterações.');
    await write(`propostas/${saved.header.id}/editar`,{changes,reason:$('calendarDayReason').value,expected_version:saved.header.version});$('calendarDayDialog').close();
  }));
  for(const [id,action] of [['builderReject','rejeitar'],['builderValidate','validar']])$(id).addEventListener('click',()=>perform(()=>write(`propostas/${saved.header.id}/${action}`,{reason:$('builderReason').value,expected_version:saved.header.version,acknowledge_inference:$('builderAcknowledged').checked,confirm_hypothetical_travel:$('builderHypothesesConfirmed').checked})));
  $('builderHistory').addEventListener('change',()=>perform(async()=>{saved=await api(`propostas/${saved.header.id}?version=${$('builderHistory').value}`);history=saved.history;draft=null;render();}));
  $('builderReload').addEventListener('click',()=>perform(()=>load()));
  for(const id of ['builderOrigin','builderVehicle'])$(id).addEventListener('input',profileSources);
  $('builderOrigin').addEventListener('change',()=>{const row=locations.get('home');if(row){row.address.value=$('builderOrigin').value;row.original.address=$('builderOrigin').value;}});
  $('builderCompanies').addEventListener('change',()=>{remember();$('builderStatus').textContent='Seleção memorizada. Reconstrua o calendário para aplicar estas empresas.';});
  perform(async()=>{const result=await api('empresas'),ids=new Set(result.rows.map(c=>c.feid)),stored=remembered()?.filter(id=>ids.has(id));if(stored)try{localStorage.setItem(preferenceKey,JSON.stringify(stored));}catch{}
    $('builderCompanies').replaceChildren(...result.rows.map(company=>{const label=node('label'),check=field(false,'checkbox',company.name);check.value=company.feid;label.append(check,node('span',company.name));return label;}));await load();});
})();
