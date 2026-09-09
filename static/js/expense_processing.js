(() => {
  const config = window.EXPENSE_PROCESSING_CONFIG || {};
  const archive = Boolean(config.archive);
  const permissions = config.permissions || {};
  const companies = Array.isArray(config.companies) ? config.companies : [];
  const fallbackUsers = Array.isArray(config.users) ? config.users : [];
  const state = { rows: [], active: '', selected: new Set(), timers: new Map(), saves: new Map(), rates: new Map(), resources: new Map(), returning: '' };
  const el = {
    from: document.getElementById('expDateFrom'), to: document.getElementById('expDateTo'),
    user: document.getElementById('expUser'), refresh: document.getElementById('expRefresh'),
    rows: document.getElementById('expRows'), summary: document.getElementById('expSummary'),
    launch: document.getElementById('expLaunch'), preview: document.getElementById('expPreview'),
    meta: document.getElementById('expDocumentMeta'), open: document.getElementById('expOpenPdf'),
    deletePdf: document.getElementById('expDeletePdf'), ai: document.getElementById('expRunAi'),
    drop: document.getElementById('expDropZone'), input: document.getElementById('expPdfInput'),
    modal: document.getElementById('expReturnModal'), returnMeta: document.getElementById('expReturnMeta'),
    returnObs: document.getElementById('expReturnObservation'), returnConfirm: document.getElementById('expReturnConfirm')
  };
  const esc = value => String(value ?? '').replace(/[&<>"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
  const money = (value, currency='EUR') => `${Number(value || 0).toLocaleString('pt-PT',{minimumFractionDigits:2,maximumFractionDigits:2})} ${currency || 'EUR'}`;
  const findRow = stamp => state.rows.find(item => item.stamp === stamp);
  const activeRow = () => findRow(state.active);
  const vatParts = (grossValue, rateValue) => {
    const gross = Math.round((Number(grossValue || 0) + Number.EPSILON) * 100) / 100;
    const rate = Number(rateValue || 0);
    const net = rate > 0 ? Math.round((gross / (1 + rate / 100) + Number.EPSILON) * 100) / 100 : gross;
    return { net, vat: Math.round((gross - net + Number.EPSILON) * 100) / 100, gross };
  };
  const companyOptions = selected => '<option value="">Escolher</option>' + companies.map(company =>
    `<option value="${esc(company.feid)}" ${String(company.feid)===String(selected)?'selected':''}>${esc(company.nome)}</option>`
  ).join('');
  const selectedRows = () => state.rows.filter(item => state.selected.has(item.stamp));
  const compatible = (base, item) => !base || [base.feid, base.login, String(base.moeda||'EUR').toUpperCase()].join('|') === [item.feid, item.login, String(item.moeda||'EUR').toUpperCase()].join('|');
  const origin = (line, field) => line.origins?.[field] ? `<span class="expense-origin" title="Origem: ${esc(line.origins[field])}">${esc(String(line.origins[field]).toUpperCase())}</span>` : '';

  function updateSummary() {
    const selected = selectedRows();
    const total = selected.reduce((sum, item) => sum + Number(item.valor || 0), 0);
    el.summary.textContent = archive
      ? `Arquivo · ${state.rows.length}`
      : `Despesas a analisar · ${state.rows.length}${selected.length ? ` | ${selected.length} selecionada${selected.length===1?'':'s'} · ${money(total, selected[0]?.moeda)}` : ''}`;
    if (el.launch) el.launch.disabled = !selected.length;
    const base = selected[0];
    document.querySelectorAll('.expense-card').forEach(card => {
      const item = findRow(card.dataset.stamp);
      const disabled = base && !state.selected.has(item.stamp) && !compatible(base, item);
      card.classList.toggle('is-incompatible', Boolean(disabled));
      const checkbox = card.querySelector('[data-select]');
      if (checkbox) {
        checkbox.disabled = Boolean(disabled);
        checkbox.title = disabled ? 'Seleciona despesas da mesma empresa, colaborador e moeda.' : '';
      }
    });
  }

  function accountingLineHtml(line, index, count, currency) {
    const amounts = vatParts(line.total_com_iva, line.taxaiva);
    return `<div class="expense-line" data-accounting-line data-line-stamp="${esc(line.stamp||'')}" data-origins="${esc(JSON.stringify(line.origins||{}))}">
      <label><span class="sz_label">Artigo${origin(line,'artigo_ref')}</span><input class="expense-input" data-field="artigo_ref" value="${esc(line.artigo_ref)}" placeholder="Referência PHC" autocomplete="off"></label>
      <label><span class="sz_label">Referência${origin(line,'referencia')}</span><input class="expense-input" data-field="referencia" value="${esc(line.referencia)}"></label>
      <label><span class="sz_label">Designação${origin(line,'design')}</span><input class="expense-input" data-field="design" value="${esc(line.design)}"></label>
      <label><span class="sz_label">Centro de custo${origin(line,'ccusto')}</span><input class="expense-input" data-field="ccusto" value="${esc(line.ccusto)}"></label>
      <label><span class="sz_label">Matrícula${origin(line,'matricula')}</span><input class="expense-input" data-field="matricula" value="${esc(line.matricula)}" autocomplete="off"></label>
      <label><span class="sz_label">IVA${origin(line,'tabiva')}</span><select class="expense-select" data-field="tabiva" data-rate="${esc(line.taxaiva)}"><option value="${esc(line.tabiva)}">${esc(line.taxaiva)}%</option></select></label>
      <label><span class="sz_label">Sem IVA</span><span class="expense-calculated" data-net>${money(amounts.net,currency)}</span></label>
      <label><span class="sz_label">IVA</span><span class="expense-calculated" data-vat>${money(amounts.vat,currency)}</span></label>
      <label><span class="sz_label">Com IVA${origin(line,'total_com_iva')}</span><input class="expense-input expense-money" data-field="total_com_iva" type="number" min="0" step="0.01" value="${amounts.gross.toFixed(2)}"></label>
      <button class="sz_icon_button danger expense-remove-line" type="button" data-remove-line title="${index===0?'A primeira linha não pode ser removida':'Remover linha'}" aria-label="Remover linha" ${index===0?'disabled':''}><i class="fa-solid fa-minus"></i></button>
    </div>`;
  }

  function cardHtml(item) {
    const lines = item.accounting_lines?.length ? item.accounting_lines : [{
      stamp:'', artigo_ref:item.ref||'', design:item.design||'', referencia:item.referencia_documento||'',
      ccusto:item.ccusto||'', matricula:item.viatura||'', tabiva:item.tabiva||'', taxaiva:item.taxaiva||0,
      total_com_iva:item.valor||0, origens:item.origens||{}
    }];
    const status = (item.arquivo_estado || item.estado || '').toUpperCase();
    const badge = status === 'DEVOLVIDA' ? '<span class="expense-archive-badge returned">Devolvida</span>'
      : status === 'ELIMINADA' ? '<span class="expense-archive-badge deleted">Eliminada</span>'
      : item.phc_bostamp ? `<span class="expense-archive-badge posted">${esc(item.phc_nmdos||'PHC')} n.º ${esc(item.phc_obrano||'')}</span>` : '';
    return `<article class="expense-card ${item.stamp===state.active?'is-active':''}" data-stamp="${esc(item.stamp)}" data-version="${esc(item.version||1)}">
      <div class="expense-card-head">
        ${archive ? badge : `<input class="expense-check" data-select type="checkbox" ${state.selected.has(item.stamp)?'checked':''}>`}
        <label><span class="sz_label">Data</span><input class="expense-input" data-expense-field="data_despesa" type="date" value="${esc(item.data_despesa)}" ${archive?'disabled':''}></label>
        <div class="expense-card-user"><strong>${esc(item.penome||item.login||'-')}</strong><small>${esc(item.peno?`N.º ${item.peno}`:item.login||'')}</small></div>
        <label><span class="sz_label">Empresa</span><select class="expense-select" data-expense-field="feid" ${archive?'disabled':''}>${companyOptions(item.feid)}</select></label>
        <div class="expense-card-actions"><span class="expense-save" data-save-state></span>
          ${!archive&&permissions.eliminar?'<button class="sz_icon_button" type="button" data-return title="Devolver ao colaborador" aria-label="Devolver ao colaborador"><i class="fa-solid fa-arrow-rotate-left"></i></button><button class="sz_icon_button danger" type="button" data-delete title="Eliminar despesa" aria-label="Eliminar despesa"><i class="fa-solid fa-trash"></i></button>':''}
          ${archive&&permissions.eliminar&&!item.phc_bostamp?'<button class="sz_icon_button danger" type="button" data-delete-permanent title="Eliminar definitivamente" aria-label="Eliminar definitivamente"><i class="fa-solid fa-trash"></i></button>':''}
        </div>
      </div>
      <label class="expense-card-comment"><span class="sz_label">Comentário</span><input class="expense-input" data-expense-field="obs" maxlength="100" value="${esc(item.obs)}" ${archive?'disabled':''}></label>
      <div class="expense-accounting"><div class="expense-accounting-head"><span>Linhas contabilísticas</span>${!archive&&permissions.editar?'<button class="sz_icon_button" type="button" data-add-line title="Adicionar linha" aria-label="Adicionar linha"><i class="fa-solid fa-plus"></i></button>':''}</div><div class="expense-lines">${lines.map((line,i)=>accountingLineHtml(line,i,lines.length,item.moeda)).join('')}</div></div>
      <footer class="expense-card-foot"><div class="expense-totals"><span>Despesa <strong>${money(item.valor,item.moeda)}</strong></span><span>Sem IVA <strong data-total-net>${money(item.linhas_total_sem_iva,item.moeda)}</strong></span><span>IVA <strong data-total-vat>${money(item.linhas_total_iva,item.moeda)}</strong></span><span>Linhas <strong data-total-gross>${money(item.linhas_total_com_iva,item.moeda)}</strong></span><span class="expense-difference ${Math.abs(Number(item.diferenca||0))>.009?'has-difference':''}" data-difference>Diferença ${money(item.diferenca,item.moeda)}</span></div><small>${esc(item.tipo||'')}</small></footer>
    </article>`;
  }

  function render() {
    if (!state.rows.length) {
      el.rows.innerHTML = `<div class="expense-state"><i class="fa-solid fa-inbox"></i><span>${archive?'O arquivo está vazio para os filtros atuais.':'Não existem despesas por processar.'}</span></div>`;
      state.active = ''; renderPreview(); updateSummary(); return;
    }
    if (!findRow(state.active)) state.active = state.rows[0].stamp;
    let lastGroup='';
    el.rows.innerHTML = state.rows.map(item=>{
      if(!archive)return cardHtml(item);
      const group=item.phc_bostamp?`${item.phc_nmdos||'PHC'} n.º ${item.phc_obrano||''}`:(item.arquivo_estado||item.estado||'Outras');
      const heading=group!==lastGroup?`<div class="expense-archive-group"><span>${esc(group)}</span></div>`:'';
      lastGroup=group;return heading+cardHtml(item);
    }).join('');
    el.rows.querySelectorAll('.expense-card').forEach(card => hydrateCard(card));
    renderPreview(); updateSummary();
  }

  function hydrateCard(card) {
    const item = findRow(card.dataset.stamp);
    card.querySelectorAll('[data-field="tabiva"]').forEach(select => loadRates(select, item.feid));
    loadCostCenters(card, item.feid);
    prepareLookups(card);
    recalculate(card);
  }

  function bindDatalist(input, key, values) {
    let list=document.getElementById(key);
    if(!list){list=document.createElement('datalist');list.id=key;document.body.appendChild(list);}
    list.innerHTML=values.map(value=>`<option value="${esc(value)}"></option>`).join('');
    input.setAttribute('list',key);
  }
  async function loadCostCenters(card,feid) {
    const key=`ccusto-${feid||0}`;
    if(!state.resources.has(key)) state.resources.set(key,fetch(`/api/colaborador/despesas/processamento/centros-custo?feid=${encodeURIComponent(feid||0)}`,{credentials:'same-origin'}).then(r=>r.json()).then(r=>r.rows||[]));
    const values=await state.resources.get(key);
    card.querySelectorAll('[data-field="ccusto"]').forEach((input,index)=>bindDatalist(input,`expense-ccusto-${card.dataset.stamp}-${index}`,values));
  }
  function prepareLookups(card) {
    card.querySelectorAll('[data-accounting-line]').forEach((line,index)=>{
      const article=line.querySelector('[data-field="artigo_ref"]'), plate=line.querySelector('[data-field="matricula"]');
      bindDatalist(article,`expense-article-${card.dataset.stamp}-${index}`,[]);
      bindDatalist(plate,`expense-plate-${card.dataset.stamp}-${index}`,[]);
    });
  }
  async function searchLookup(input,card) {
    const query=input.value.trim();if(!query)return;
    const item=findRow(card.dataset.stamp);
    if(input.dataset.field==='artigo_ref'){
      const response=await fetch(`/api/colaborador/despesas/processamento/artigos?feid=${encodeURIComponent(item.feid||0)}&q=${encodeURIComponent(query)}`,{credentials:'same-origin'});
      const result=await response.json().catch(()=>({})), rows=result.rows||[];
      bindDatalist(input,input.getAttribute('list'),rows.map(value=>value.ref));
      input._expenseOptions=rows;
    }else if(input.dataset.field==='matricula'){
      const response=await fetch(`/api/colaborador/despesas/processamento/viaturas?feid=${encodeURIComponent(item.feid||0)}&q=${encodeURIComponent(query)}`,{credentials:'same-origin'});
      const result=await response.json().catch(()=>({}));
      bindDatalist(input,input.getAttribute('list'),(result.rows||[]).map(value=>value.matricula));
    }
  }

  function collect(card) {
    const item = findRow(card.dataset.stamp);
    return {
      stamp:item.stamp, version:Number(card.dataset.version||item.version||1),
      data_despesa:card.querySelector('[data-expense-field="data_despesa"]')?.value||'',
      feid:card.querySelector('[data-expense-field="feid"]')?.value||'', moeda:item.moeda||'EUR',
      valor:item.valor, obs:card.querySelector('[data-expense-field="obs"]')?.value||'',
      accounting_lines:[...card.querySelectorAll('[data-accounting-line]')].map(line => {
        const select = line.querySelector('[data-field="tabiva"]');
        return {
          stamp:line.dataset.lineStamp||'', artigo_ref:line.querySelector('[data-field="artigo_ref"]')?.value||'',
          referencia:line.querySelector('[data-field="referencia"]')?.value||'',
          design:line.querySelector('[data-field="design"]')?.value||'',
          ccusto:line.querySelector('[data-field="ccusto"]')?.value||'',
          matricula:line.querySelector('[data-field="matricula"]')?.value||'',
          tabiva:select?.value||'', taxaiva:select?.selectedOptions?.[0]?.dataset.rate||select?.dataset.rate||0,
          total_com_iva:line.querySelector('[data-field="total_com_iva"]')?.value||0,
          origens:(()=>{try{return JSON.parse(line.dataset.origins||'{}');}catch(_error){return {};}})()
        };
      })
    };
  }

  function recalculate(card) {
    const item = findRow(card.dataset.stamp), payload = collect(card);
    let net=0, vat=0, gross=0;
    card.querySelectorAll('[data-accounting-line]').forEach((line,index) => {
      const amounts = vatParts(payload.accounting_lines[index].total_com_iva, payload.accounting_lines[index].taxaiva);
      net += amounts.net; vat += amounts.vat; gross += amounts.gross;
      line.querySelector('[data-net]').textContent = money(amounts.net,item.moeda);
      line.querySelector('[data-vat]').textContent = money(amounts.vat,item.moeda);
    });
    const difference = Math.round((Number(item.valor||0)-gross+Number.EPSILON)*100)/100;
    card.querySelector('[data-total-net]').textContent=money(net,item.moeda);
    card.querySelector('[data-total-vat]').textContent=money(vat,item.moeda);
    card.querySelector('[data-total-gross]').textContent=money(gross,item.moeda);
    const differenceNode=card.querySelector('[data-difference]');
    differenceNode.textContent=`Diferença ${money(difference,item.moeda)}`;
    differenceNode.classList.toggle('has-difference',Math.abs(difference)>.009);
  }

  function setSave(card,status,message='') {
    const node=card.querySelector('[data-save-state]'); if(!node)return;
    node.className=`expense-save ${status==='ok'?'is-ok':status==='error'?'is-error':''}`; node.title=message;
    node.innerHTML=status==='saving'?'<i class="fa-solid fa-circle-notch fa-spin"></i>':status==='ok'?'<i class="fa-solid fa-check"></i>':status==='error'?'<i class="fa-solid fa-triangle-exclamation"></i>':'';
  }
  function schedule(card) {
    if(archive||!permissions.editar)return;
    const stamp=card.dataset.stamp; clearTimeout(state.timers.get(stamp));
    state.timers.set(stamp,setTimeout(()=>save(card),450));
  }
  async function save(card) {
    if(!card?.isConnected)return false;
    const stamp=card.dataset.stamp;
    if(state.saves.get(stamp))await state.saves.get(stamp).catch(()=>null);
    const payload=collect(card); setSave(card,'saving');
    const promise=fetch(`/api/colaborador/despesas/processamento/${encodeURIComponent(stamp)}/classificacao`,{
      method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',body:JSON.stringify(payload)
    }).then(async response=>{const result=await response.json().catch(()=>({}));if(!response.ok||!result.ok){const error=new Error(result.error||'Erro ao gravar.');error.conflict=response.status===409;throw error;}return result;});
    state.saves.set(stamp,promise);
    try {
      const result=await promise; Object.assign(findRow(stamp),result.line); card.dataset.version=result.line.version; setSave(card,'ok'); return true;
    } catch(error) {
      setSave(card,'error',error.message);
      if(error.conflict&&confirm(`${error.message}\n\nAtualizar agora?`))await load();
      return false;
    } finally { state.saves.delete(stamp); }
  }
  async function flushPendingSaves(stamps) {
    for(const stamp of stamps){clearTimeout(state.timers.get(stamp));const card=el.rows.querySelector(`[data-stamp="${CSS.escape(stamp)}"]`);if(card&&!(await save(card)))return false;}
    return true;
  }

  async function loadRates(select,feid) {
    if(!feid){select.innerHTML='<option value="">Escolher</option>';return;}
    if(!state.rates.has(String(feid))) state.rates.set(String(feid),fetch(`/api/colaborador/despesas/processamento/taxasiva?feid=${encodeURIComponent(feid)}`,{credentials:'same-origin'}).then(r=>r.json()).then(r=>r.rows||[]));
    const rates=await state.rates.get(String(feid)), current=select.value;
    select.innerHTML='<option value="">Escolher</option>'+rates.map(rate=>`<option value="${esc(rate.tabiva)}" data-rate="${esc(rate.taxaiva)}" ${String(rate.tabiva)===String(current)?'selected':''}>${esc(rate.label)}</option>`).join('');
  }

  function renderPreview() {
    const item=activeRow(), path=item?.file_url||'';
    el.meta.textContent=item?`${item.penome||item.login||''} · ${item.data_despesa||''}`:'Seleciona uma despesa.';
    el.open.setAttribute('aria-disabled',path?'false':'true'); el.open.href=path||'#';
    el.deletePdf.disabled=!path||archive||!permissions.editar; el.ai.disabled=!path||archive||!permissions.editar;
    if(!path){el.preview.className='expense-preview-empty';el.preview.innerHTML='<i class="fa-solid fa-file-arrow-up"></i><span>Esta despesa não tem PDF</span><small>Larga aqui um PDF até 50 MB</small>';return;}
    el.preview.className='';
    el.preview.innerHTML=String(item.file_ext).toLowerCase()==='.pdf'? `<iframe src="${esc(path)}" title="PDF da despesa"></iframe>` : `<img src="${esc(path)}" alt="Documento da despesa">`;
  }
  function updateUsers(users) {
    const value=el.user.value, list=Array.isArray(users)&&users.length?users:fallbackUsers;
    el.user.innerHTML='<option value="">Todos</option>'+list.map(user=>`<option value="${esc(user.login)}" ${user.login===value?'selected':''}>${esc(user.nome||user.login)} · ${esc(user.total)}</option>`).join('');
    if(value&&!list.some(user=>user.login===value))el.user.value='';
  }
  function saveFilters(){localStorage.setItem(`expense-processing-filters-${archive}`,JSON.stringify({from:el.from.value,to:el.to.value,user:el.user.value}));}
  function restoreFilters(){try{const saved=JSON.parse(localStorage.getItem(`expense-processing-filters-${archive}`)||'{}');if(saved.from!==undefined)el.from.value=saved.from;if(saved.to!==undefined)el.to.value=saved.to;if(saved.user!==undefined)el.user.value=saved.user;}catch(_error){}}
  async function load() {
    const params=new URLSearchParams({date_from:el.from.value,date_to:el.to.value,user:el.user.value,arquivo:archive?'1':'0'});
    el.rows.innerHTML='<div class="expense-state"><i class="fa-solid fa-circle-notch fa-spin"></i><span>A carregar despesas...</span></div>';
    try {
      const response=await fetch(`/api/colaborador/despesas/processamento?${params}`,{credentials:'same-origin'});
      const result=await response.json(); if(!response.ok||!result.ok)throw new Error(result.error||'Erro ao carregar.');
      state.rows=result.rows||[]; state.selected.clear(); state.active=sessionStorage.getItem(`expense-active-${archive}`)||state.rows[0]?.stamp||'';
      updateUsers(result.users); render();
      requestAnimationFrame(()=>{el.rows.scrollTop=Number(sessionStorage.getItem(`expense-scroll-${archive}`)||0);});
    } catch(error) {el.rows.innerHTML=`<div class="expense-state"><i class="fa-solid fa-triangle-exclamation"></i><span>${esc(error.message)}</span><button class="sz_button sz_button_secondary" data-retry>Repetir</button></div>`;}
  }
  function activate(card) {
    state.active=card.dataset.stamp; sessionStorage.setItem(`expense-active-${archive}`,state.active);
    el.rows.querySelectorAll('.expense-card').forEach(node=>node.classList.toggle('is-active',node===card)); renderPreview();
  }
  async function upload(file) {
    const item=activeRow(); if(!item||archive||!permissions.editar)return;
    if(!file||file.type!=='application/pdf'&&!file.name.toLowerCase().endsWith('.pdf'))return alert('Seleciona um ficheiro PDF.');
    if(file.size>50*1024*1024)return alert('O PDF não pode ultrapassar 50 MB.');
    const data=new FormData();data.append('file',file);
    const response=await fetch(`/api/colaborador/despesas/processamento/${encodeURIComponent(item.stamp)}/pdf`,{method:'POST',credentials:'same-origin',body:data});
    const result=await response.json().catch(()=>({}));if(!response.ok||!result.ok)return alert(result.error||'Erro ao carregar PDF.');await load();
  }

  el.rows.addEventListener('click',async event=>{
    const card=event.target.closest('.expense-card');
    if(!card){if(event.target.closest('[data-retry]'))load();return;}
    activate(card); const item=findRow(card.dataset.stamp);
    if(event.target.closest('[data-add-line]')){
      const lines=card.querySelector('.expense-lines');
      lines.insertAdjacentHTML('beforeend',accountingLineHtml({stamp:'',origens:{}},lines.children.length,lines.children.length+1,item.moeda));
      loadRates(lines.lastElementChild.querySelector('[data-field="tabiva"]'),item.feid);prepareLookups(card);loadCostCenters(card,item.feid);recalculate(card);schedule(card);return;
    }
    if(event.target.closest('[data-remove-line]')){
      const lines=card.querySelector('.expense-lines');if(lines.children.length<=1)return;
      event.target.closest('[data-accounting-line]').remove();recalculate(card);schedule(card);return;
    }
    if(event.target.closest('[data-return]')){
      state.returning=item.stamp;el.returnMeta.textContent=`${item.penome||item.login} · ${item.data_despesa}`;el.returnObs.value='';el.returnConfirm.disabled=true;el.modal.hidden=false;el.returnObs.focus();return;
    }
    if(event.target.closest('[data-delete]')){
      if(!confirm('Eliminar esta despesa do processamento? Ficará visível no arquivo como Eliminada.'))return;
      const response=await fetch(`/api/colaborador/despesas/processamento/${encodeURIComponent(item.stamp)}`,{method:'DELETE',credentials:'same-origin'});
      const result=await response.json().catch(()=>({}));if(!response.ok||!result.ok)return alert(result.error||'Erro ao eliminar.');await load();return;
    }
    if(event.target.closest('[data-delete-permanent]')){
      if(!confirm('Eliminar definitivamente esta despesa e os anexos do Portal? Esta ação não pode ser anulada.'))return;
      const response=await fetch(`/api/colaborador/despesas/processamento/${encodeURIComponent(item.stamp)}/arquivo`,{method:'DELETE',credentials:'same-origin'});
      const result=await response.json().catch(()=>({}));if(!response.ok||!result.ok)return alert(result.error||'Erro ao eliminar.');await load();
    }
  });
  el.rows.addEventListener('change',event=>{
    const card=event.target.closest('.expense-card');if(!card)return;
    if(event.target.matches('[data-select]')){
      const item=findRow(card.dataset.stamp);
      if(event.target.checked){const base=selectedRows()[0];if(!compatible(base,item)){event.target.checked=false;return;}state.selected.add(item.stamp);}else state.selected.delete(item.stamp);
      updateSummary();return;
    }
    if(event.target.matches('[data-expense-field="feid"]')){
      card.querySelectorAll('[data-field="tabiva"]').forEach(select=>{select.value='';loadRates(select,event.target.value);});
      card.querySelectorAll('[data-field="ccusto"],[data-field="matricula"]').forEach(input=>input.value='');
      loadCostCenters(card,event.target.value);
    }
    if(event.target.matches('[data-field="artigo_ref"]')){
      const selected=(event.target._expenseOptions||[]).find(option=>option.ref===event.target.value);
      const design=event.target.closest('[data-accounting-line]')?.querySelector('[data-field="design"]');
      if(selected&&design&&!design.value)design.value=selected.design||'';
    }
    recalculate(card);schedule(card);
  });
  el.rows.addEventListener('input',event=>{
    const card=event.target.closest('.expense-card');if(!card)return;
    if(event.target.matches('[data-field="artigo_ref"],[data-field="matricula"]')){
      clearTimeout(event.target._lookupTimer);event.target._lookupTimer=setTimeout(()=>searchLookup(event.target,card),250);
    }
    const accountingLine=event.target.closest('[data-accounting-line]');
    if(accountingLine&&event.target.dataset.field){
      let origins={};try{origins=JSON.parse(accountingLine.dataset.origins||'{}');}catch(_error){}
      origins[event.target.dataset.field]='manual';accountingLine.dataset.origins=JSON.stringify(origins);
    }
    recalculate(card);schedule(card);
  });
  el.rows.addEventListener('scroll',()=>sessionStorage.setItem(`expense-scroll-${archive}`,String(el.rows.scrollTop)),{passive:true});
  el.launch?.addEventListener('click',async()=>{
    const stamps=[...state.selected];if(!(await flushPendingSaves(stamps)))return alert('Não foi possível guardar todas as alterações.');
    const issues=[];selectedRows().forEach(item=>{if(!item.feid)issues.push('Empresa em falta.');const card=el.rows.querySelector(`[data-stamp="${CSS.escape(item.stamp)}"]`);collect(card).accounting_lines.forEach((line,index)=>{if(!line.artigo_ref)issues.push(`${item.data_despesa}, linha ${index+1}: artigo em falta.`);});});
    if(issues.length)return alert(issues.join('\n'));if(!confirm(`Lançar ${stamps.length} despesa(s) no PHC?`))return;
    el.launch.disabled=true;
    const response=await fetch('/api/colaborador/despesas/processamento/lancar-phc',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',body:JSON.stringify({stamps})});
    const result=await response.json().catch(()=>({}));if(!response.ok||!result.ok){el.launch.disabled=false;return alert(result.error||'Erro ao lançar no PHC.');}
    alert(`${result.nmdos} n.º ${result.obrano} criado com sucesso.`);await load();
  });
  el.deletePdf?.addEventListener('click',async()=>{
    const item=activeRow();if(!item||!confirm('Eliminar apenas o PDF desta despesa? A despesa e a classificação serão mantidas.'))return;
    const response=await fetch(`/api/colaborador/despesas/processamento/${encodeURIComponent(item.stamp)}/pdf`,{method:'DELETE',credentials:'same-origin'});
    const result=await response.json().catch(()=>({}));if(!response.ok||!result.ok)return alert(result.error||'Erro ao eliminar PDF.');await load();
  });
  el.ai?.addEventListener('click',async()=>{
    const item=activeRow();if(!item)return;
    el.ai.disabled=true;el.ai.innerHTML='<i class="fa-solid fa-circle-notch fa-spin"></i>';
    const response=await fetch(`/api/colaborador/despesas/processamento/${encodeURIComponent(item.stamp)}/analisar-ia`,{method:'POST',credentials:'same-origin'});
    const result=await response.json().catch(()=>({}));
    el.ai.innerHTML='<i class="fa-solid fa-wand-magic-sparkles"></i>';
    if(!response.ok||!result.ok){el.ai.disabled=false;return alert(result.error||'A análise IA falhou. A despesa foi mantida sem alterações.');}
    alert(result.message||'Documento analisado.');await load();
  });
  ['dragenter','dragover'].forEach(name=>el.drop.addEventListener(name,event=>{event.preventDefault();el.drop.classList.add('is-dragging');}));
  ['dragleave','drop'].forEach(name=>el.drop.addEventListener(name,event=>{event.preventDefault();el.drop.classList.remove('is-dragging');}));
  el.drop.addEventListener('drop',event=>upload(event.dataTransfer.files?.[0]));
  el.drop.addEventListener('dblclick',()=>{if(activeRow()&&!activeRow().file_url)el.input.click();});
  el.input.addEventListener('change',()=>upload(el.input.files?.[0]));
  el.returnObs?.addEventListener('input',()=>el.returnConfirm.disabled=!el.returnObs.value.trim());
  el.returnConfirm?.addEventListener('click',async()=>{
    const response=await fetch(`/api/colaborador/despesas/processamento/${encodeURIComponent(state.returning)}/devolver`,{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',body:JSON.stringify({observacao:el.returnObs.value.trim()})});
    const result=await response.json().catch(()=>({}));if(!response.ok||!result.ok)return alert(result.error||'Erro ao devolver.');el.modal.hidden=true;await load();
  });
  document.querySelectorAll('[data-modal-close]').forEach(button=>button.addEventListener('click',()=>el.modal.hidden=true));
  [el.from,el.to,el.user].forEach(input=>input.addEventListener('change',()=>{saveFilters();load();}));
  el.refresh.addEventListener('click',load);updateUsers(fallbackUsers);restoreFilters();load();
})();
