(() => {
  const config = window.EXPENSE_PROCESSING_CONFIG || {};
  const archive = Boolean(config.archive);
  const permissions = config.permissions || {};
  const companies = Array.isArray(config.companies) ? config.companies : [];
  const fallbackUsers = Array.isArray(config.users) ? config.users : [];
  const state = { rows: [], active: '', selected: new Set(), timers: new Map(), saves: new Map(), saveErrors: new Set(), rates: new Map(), resources: new Map(), returning: '', lookup: null, validating: false };
  const el = {
    from: document.getElementById('expDateFrom'), to: document.getElementById('expDateTo'),
    user: document.getElementById('expUser'), clearFilters: document.getElementById('expClearFilters'), refresh: document.getElementById('expRefresh'),
    rows: document.getElementById('expRows'), summary: document.getElementById('expSummary'),
    launch: document.getElementById('expLaunch'), preview: document.getElementById('expPreview'),
    meta: document.getElementById('expDocumentMeta'), open: document.getElementById('expOpenPdf'),
    deletePdf: document.getElementById('expDeletePdf'), ai: document.getElementById('expRunAi'),
    drop: document.getElementById('expDropZone'), input: document.getElementById('expPdfInput'),
    modal: document.getElementById('expReturnModal'), returnMeta: document.getElementById('expReturnMeta'),
    returnObs: document.getElementById('expReturnObservation'), returnConfirm: document.getElementById('expReturnConfirm'),
    lookupModal: document.getElementById('expLookupModal'), lookupTitle: document.getElementById('expLookupTitle'),
    lookupSearch: document.getElementById('expLookupSearch'), lookupSearchButton: document.getElementById('expLookupSearchButton'),
    lookupResults: document.getElementById('expLookupResults')
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
    if (el.launch) {
      el.launch.disabled = state.validating || !selected.length || selected.some(item => state.saveErrors.has(item.stamp));
      if (!state.validating) el.launch.querySelector('span').textContent = selected.length === 1 ? 'Validar Despesa' : 'Validar Despesas';
    }
    const base = selected[0];
    document.querySelectorAll('.expense-card').forEach(card => {
      const item = findRow(card.dataset.stamp);
      const disabled = base && !state.selected.has(item.stamp) && !compatible(base, item);
      card.classList.toggle('is-incompatible', Boolean(disabled));
      const checkbox = card.querySelector('[data-select]');
      card.classList.toggle('is-selected', state.selected.has(item.stamp));
      if (checkbox) {
        checkbox.disabled = Boolean(disabled);
        checkbox.title = disabled ? 'Seleciona despesas da mesma empresa, colaborador e moeda.' : '';
      }
    });
  }

  function accountingLineHtml(line, index, count, currency) {
    const amounts = vatParts(line.total_com_iva, line.taxaiva);
    const locked = archive || !permissions.editar;
    const disabled = locked ? 'disabled' : '';
    return `<div class="expense-line" data-accounting-line data-line-stamp="${esc(line.stamp||'')}" data-origins="${esc(JSON.stringify(line.origins||{}))}">
      <div class="expense-line-main">
      <div class="expense-line-actions"><button class="sz_icon_button" type="button" data-add-line title="Adicionar linha" aria-label="Adicionar linha" ${disabled}><i class="fa-solid fa-plus"></i></button><button class="sz_icon_button expense-remove-line" type="button" data-remove-line title="${index===0?'A primeira linha não pode ser removida':'Remover linha'}" aria-label="Remover linha" ${locked||index===0?'disabled':''}><i class="fa-solid fa-minus"></i></button></div>
      <label><span class="sz_label">Artigo${origin(line,'artigo_ref')}</span><button class="expense-lookup" type="button" data-lookup="article" data-value="${esc(line.artigo_ref)}" ${disabled}><strong>${esc(line.artigo_ref||'Escolher')}</strong><small>${esc(line.design||'Selecionar artigo PHC')}</small></button><input type="hidden" data-field="artigo_ref" value="${esc(line.artigo_ref)}"></label>
      <label><span class="sz_label">Designação${origin(line,'design')}</span><input class="expense-input" data-field="design" value="${esc(line.design)}" readonly aria-readonly="true"><input type="hidden" data-field="referencia" value="${esc(line.referencia&&String(line.referencia).trim().toLocaleLowerCase()!==String(line.artigo_ref||'').trim().toLocaleLowerCase()?line.referencia:'')}"></label>
      <label><span class="sz_label">Centro de Custo${origin(line,'ccusto')}</span><button class="expense-lookup" type="button" data-lookup="ccusto" data-value="${esc(line.ccusto)}" ${disabled}><strong>${esc(line.ccusto||'Escolher')}</strong></button><input type="hidden" data-field="ccusto" value="${esc(line.ccusto)}"></label>
      <label><span class="sz_label">Matrícula${origin(line,'matricula')}</span><button class="expense-lookup" type="button" data-lookup="vehicle" data-value="${esc(line.matricula)}" ${disabled}><strong>${esc(line.matricula||'Escolher')}</strong></button><input type="hidden" data-field="matricula" value="${esc(line.matricula)}"></label>
      </div><div class="expense-line-values">
      <label><span class="sz_label">Total s/IVA</span><span class="expense-calculated" data-net data-value="${amounts.net.toFixed(2)}">${money(amounts.net,currency)}</span></label>
      <label><span class="sz_label">IVA${origin(line,'tabiva')}</span><select class="expense-select" data-field="tabiva" data-rate="${esc(line.taxaiva)}" ${disabled}><option value="${esc(line.tabiva)}">${esc(line.taxaiva)}%</option></select><span data-vat data-value="${amounts.vat.toFixed(2)}" hidden>${money(amounts.vat,currency)}</span></label>
      <label><span class="sz_label">Total c/IVA${origin(line,'total_com_iva')}</span><input class="expense-input expense-money" data-field="total_com_iva" type="number" min="0" step="0.01" value="${amounts.gross.toFixed(2)}" ${disabled}></label>
      </div>
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
    return `<article class="expense-card ${item.stamp===state.active?'is-active':''} ${state.selected.has(item.stamp)?'is-selected':''}" data-stamp="${esc(item.stamp)}" data-version="${esc(item.version||1)}">
      <div class="expense-card-head">
        ${archive ? badge : `<input class="expense-check" data-select type="checkbox" ${state.selected.has(item.stamp)?'checked':''}>`}
        <div class="expense-card-actions"><span class="expense-save" data-save-state></span>
          ${!archive&&permissions.eliminar?'<button class="sz_icon_button expense-return" type="button" data-return title="Devolver" aria-label="Devolver"><i class="fa-solid fa-arrow-rotate-left"></i></button><button class="sz_icon_button expense-delete" type="button" data-delete title="Eliminar Documento Inbox" aria-label="Eliminar Documento Inbox"><i class="fa-solid fa-trash"></i></button>':''}
          ${archive&&permissions.eliminar&&!item.phc_bostamp?'<button class="sz_icon_button expense-delete" type="button" data-delete-permanent title="Eliminar Documento Arquivo" aria-label="Eliminar Documento Arquivo"><i class="fa-solid fa-trash"></i></button>':''}
        </div>
      </div>
      <div class="expense-card-facts"><div class="expense-card-user"><span class="sz_label">Nome do colaborador</span><strong>${esc(item.penome||item.login||'-')}</strong></div><div><span class="sz_label">Tipo de despesa</span><strong>${esc(item.tipo||'-')}</strong></div><label><span class="sz_label">Data da despesa</span><input class="expense-input" data-expense-field="data_despesa" type="date" value="${esc(item.data_despesa)}" ${archive||!permissions.editar?'disabled':''}></label><div><span class="sz_label">Total c/IVA</span><strong>${money(item.valor,item.moeda)}</strong></div></div>
      <label class="expense-card-company"><span class="sz_label">Empresa</span><select class="expense-select" data-expense-field="feid" ${archive||!permissions.editar?'disabled':''}>${companyOptions(item.feid)}</select></label>
      <div class="expense-accounting"><div class="expense-accounting-head"><span>Linhas contabilísticas</span></div><div class="expense-lines">${lines.map((line,i)=>accountingLineHtml(line,i,lines.length,item.moeda)).join('')}</div></div>
      <footer class="expense-card-foot"><div class="expense-totals"><span>Total da despesa <strong>${money(item.valor,item.moeda)}</strong></span><span>Total das linhas <strong data-total-gross>${money(item.linhas_total_com_iva,item.moeda)}</strong></span><span class="expense-difference ${Math.abs(Number(item.diferenca||0))>.009?'has-difference':'is-zero'}" data-difference>Diferença ${money(item.diferenca,item.moeda)}</span><span data-total-net hidden>${money(item.linhas_total_sem_iva,item.moeda)}</span><span data-total-vat hidden>${money(item.linhas_total_iva,item.moeda)}</span></div></footer>
      <div class="expense-card-comment"><span class="sz_label">Comentário do colaborador</span><p>${esc(item.obs||'Sem comentário.')}</p></div>
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
    recalculate(card);
  }

  function closeLookup() { state.lookup=null; el.lookupModal.hidden=true; el.lookupResults.innerHTML=''; }
  function openLookup(button,card) {
    const kind=button.dataset.lookup, names={article:'Selecionar artigo',ccusto:'Selecionar Centro de Custo',vehicle:'Selecionar matrícula'};
    state.lookup={kind,button,card,rows:[]}; el.lookupTitle.textContent=names[kind]||'Selecionar';
    el.lookupSearch.value=button.dataset.value||''; el.lookupModal.hidden=false; el.lookupSearch.focus();
    searchLookupOptions();
  }
  async function searchLookupOptions() {
    const target=state.lookup;if(!target)return;const item=findRow(target.card.dataset.stamp);const feid=target.card.querySelector('[data-expense-field="feid"]')?.value||item.feid||0;
    const query=el.lookupSearch.value.trim();
    if(target.kind!=='ccusto'&&!query){el.lookupResults.innerHTML='<div class="expense-state">Escreve para pesquisar.</div>';return;}
    const endpoint=target.kind==='article'?'artigos':target.kind==='vehicle'?'viaturas':'centros-custo';
    el.lookupResults.innerHTML='<div class="expense-state"><i class="fa-solid fa-circle-notch fa-spin"></i><span>A pesquisar...</span></div>';
    let response;
    try { response=await fetch(`/api/colaborador/despesas/processamento/${endpoint}?feid=${encodeURIComponent(feid)}&q=${encodeURIComponent(query)}`,{credentials:'same-origin'}); }
    catch(_error){el.lookupResults.innerHTML='<div class="expense-state">Erro ao consultar o PHC.</div>';return;}
    const result=await response.json().catch(()=>({}));if(!response.ok||!result.ok){el.lookupResults.innerHTML=`<div class="expense-state">${esc(result.error||'Erro ao consultar o PHC.')}</div>`;return;}
    target.rows=result.rows||[];
    el.lookupResults.innerHTML=target.rows.map((row,index)=>{const value=typeof row==='string'?row:(target.kind==='article'?row.ref:target.kind==='ccusto'?row.ccusto:row.matricula);const detail=typeof row==='string'?'':(target.kind==='article'?row.design:target.kind==='ccusto'?row.design:[row.marca,row.modelo,row.nofrota].filter(Boolean).join(' · '));return `<button type="button" data-lookup-index="${index}"><strong>${esc(value)}</strong><small>${esc(detail)}</small></button>`;}).join('')||'<div class="expense-state">Nenhum resultado válido.</div>';
  }
  function selectLookup(index) {
    const target=state.lookup,row=target?.rows?.[Number(index)];if(!target||row===undefined)return;
    const line=target.button.closest('[data-accounting-line]');const value=typeof row==='string'?row:(target.kind==='article'?row.ref:target.kind==='ccusto'?row.ccusto:row.matricula);
    const field=target.kind==='article'?'artigo_ref':target.kind==='vehicle'?'matricula':'ccusto';
    line.querySelector(`[data-field="${field}"]`).value=value||'';target.button.dataset.value=value||'';target.button.querySelector('strong').textContent=value||'Escolher';target.button.classList.remove('is-unverified');
    if(target.kind==='article'){line.querySelector('[data-field="design"]').value=row.design||'';target.button.querySelector('small').textContent=row.design||'Artigo PHC';}
    let origins={};try{origins=JSON.parse(line.dataset.origins||'{}');}catch(_error){}origins[field]='manual';line.dataset.origins=JSON.stringify(origins);
    const card=target.card;closeLookup();recalculate(card);schedule(card);
  }

  function collect(card) {
    const item = findRow(card.dataset.stamp);
    return {
      stamp:item.stamp, version:Number(card.dataset.version||item.version||1),
      data_despesa:card.querySelector('[data-expense-field="data_despesa"]')?.value||'',
      feid:card.querySelector('[data-expense-field="feid"]')?.value||'', moeda:item.moeda||'EUR',
      valor:item.valor,
      accounting_lines:[...card.querySelectorAll('[data-accounting-line]')].map(line => {
        const select = line.querySelector('[data-field="tabiva"]');
        return {
          stamp:line.dataset.lineStamp||'', artigo_ref:line.querySelector('[data-field="artigo_ref"]')?.value||'',
          referencia:line.querySelector('[data-field="referencia"]')?.value||'',
          design:line.querySelector('[data-field="design"]')?.value||'',
          ccusto:line.querySelector('[data-field="ccusto"]')?.value||'',
          matricula:line.querySelector('[data-field="matricula"]')?.value||'',
          tabiva:select?.value||'', taxaiva:select?.selectedOptions?.[0]?.dataset.rate||select?.dataset.rate||0,
          total_sem_iva:line.querySelector('[data-net]')?.dataset.value||0,
          valor_iva:line.querySelector('[data-vat]')?.dataset.value||0,
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
      line.querySelector('[data-net]').dataset.value = amounts.net.toFixed(2);
      line.querySelector('[data-vat]').textContent = money(amounts.vat,item.moeda);
      line.querySelector('[data-vat]').dataset.value = amounts.vat.toFixed(2);
    });
    const difference = Math.round((Number(item.valor||0)-gross+Number.EPSILON)*100)/100;
    card.querySelector('[data-total-net]').textContent=money(net,item.moeda);
    card.querySelector('[data-total-vat]').textContent=money(vat,item.moeda);
    card.querySelector('[data-total-gross]').textContent=money(gross,item.moeda);
    const differenceNode=card.querySelector('[data-difference]');
    differenceNode.textContent=`Diferença ${money(difference,item.moeda)}`;
    differenceNode.classList.toggle('has-difference',Math.abs(difference)>.009);
    differenceNode.classList.toggle('is-zero',Math.abs(difference)<=.009);
  }

  function setSave(card,status,message='') {
    const node=card.querySelector('[data-save-state]'); if(!node)return;
    node.className=`expense-save ${status==='ok'?'is-ok':status==='error'||status==='conflict'?'is-error':''}`; node.title=message;
    node.innerHTML=status==='saving'?'<i class="fa-solid fa-circle-notch fa-spin"></i> A guardar...':status==='ok'?'<i class="fa-solid fa-check"></i> Guardado':status==='conflict'?'<i class="fa-solid fa-triangle-exclamation"></i> Despesa alterada por outro utilizador. <button type="button" data-reload-expenses>Atualizar</button>':status==='error'?'<i class="fa-solid fa-triangle-exclamation"></i> Erro ao guardar':'';
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
      const result=await promise; Object.assign(findRow(stamp),result.line); card.dataset.version=result.line.version; state.saveErrors.delete(stamp); setSave(card,'ok'); updateSummary(); return true;
    } catch(error) {
      state.saveErrors.add(stamp); setSave(card,error.conflict?'conflict':'error',error.message); updateSummary();
      return false;
    } finally { state.saves.delete(stamp); }
  }
  async function flushPendingSaves(stamps) {
    for(const stamp of stamps){clearTimeout(state.timers.get(stamp));const card=el.rows.querySelector(`[data-stamp="${CSS.escape(stamp)}"]`);if(card&&!(await save(card)))return false;}
    return true;
  }

  async function loadRates(select,feid) {
    if(!feid){select.innerHTML='<option value="">Escolher</option>';return;}
    if(!state.rates.has(String(feid))) state.rates.set(String(feid),fetch(`/api/colaborador/despesas/processamento/taxasiva?feid=${encodeURIComponent(feid)}`,{credentials:'same-origin'}).then(async r=>{const result=await r.json().catch(()=>({}));if(!r.ok||!result.ok)throw new Error(result.error||'Erro ao consultar o PHC.');return result.rows||[];}));
    const current=select.value;
    try { const rates=await state.rates.get(String(feid)); select.innerHTML='<option value="">Escolher</option>'+rates.map(rate=>`<option value="${esc(rate.tabiva)}" data-rate="${esc(rate.taxaiva)}" ${String(rate.tabiva)===String(current)?'selected':''}>${esc(rate.label)}</option>`).join(''); }
    catch(error){state.rates.delete(String(feid));select.innerHTML=`<option value="">${esc(error.message)}</option>`;}
  }

  function renderPreview() {
    const item=activeRow(), path=item?.file_url||'';
    el.meta.textContent=item?`${item.penome||item.login||''} · ${item.data_despesa||''} · ${item.tipo||''} · ${money(item.valor,item.moeda)}`:'Seleciona uma despesa.';
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
  function clearFilters(){
    localStorage.removeItem(`expense-processing-filters-${archive}`);
    el.from.value=el.from.defaultValue;
    el.to.value=el.to.defaultValue;
    el.user.value='';
    load();
  }
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
  function clearCompanyValues(card,item,newFeid) {
    const invalidated=[];
    card.querySelectorAll('[data-accounting-line]').forEach(line=>{
      [['artigo_ref','Artigo'],['design','Designação'],['ccusto','Centro de Custo'],['matricula','Matrícula'],['tabiva','IVA']].forEach(([field,label])=>{const input=line.querySelector(`[data-field="${field}"]`);if(input?.value&&!invalidated.includes(label))invalidated.push(label);if(input)input.value='';});
      line.querySelectorAll('[data-lookup]').forEach(button=>{button.dataset.value='';button.classList.remove('is-unverified');button.removeAttribute('title');button.querySelector('strong').textContent='Escolher';if(button.dataset.lookup==='article')button.querySelector('small').textContent='Selecionar artigo PHC';});
    });
    const company=companies.find(value=>String(value.feid)===String(newFeid));
    item.feid=Number(newFeid||0);item.moeda=String(company?.phc_db||'').toUpperCase().includes('_MA')?'MAD':'EUR';
    state.resources.clear();state.rates.delete(String(newFeid));
    card.querySelectorAll('[data-field="tabiva"]').forEach(select=>loadRates(select,newFeid));
    if(invalidated.length){state.saveErrors.add(item.stamp);setSave(card,'error',`Valores da Empresa anterior removidos: ${invalidated.join(', ')}.`);}
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
    if(event.target.closest('[data-reload-expenses]')){await load();return;}
    const lookup=event.target.closest('[data-lookup]');if(lookup){openLookup(lookup,card);return;}
    if(event.target.closest('[data-add-line]')){
      const lines=card.querySelector('.expense-lines');
      lines.insertAdjacentHTML('beforeend',accountingLineHtml({stamp:'',origens:{}},lines.children.length,lines.children.length+1,item.moeda));
      loadRates(lines.lastElementChild.querySelector('[data-field="tabiva"]'),item.feid);recalculate(card);schedule(card);return;
    }
    if(event.target.closest('[data-remove-line]')){
      const lines=card.querySelector('.expense-lines');if(lines.children.length<=1)return;
      event.target.closest('[data-accounting-line]').remove();recalculate(card);schedule(card);return;
    }
    if(event.target.closest('[data-return]')){
      state.returning=item.stamp;el.returnMeta.textContent=`${item.penome||item.login} · ${item.data_despesa}`;el.returnObs.value='';el.returnConfirm.disabled=true;el.modal.hidden=false;el.returnObs.focus();return;
    }
    if(event.target.closest('[data-delete]')){
      if(!confirm('Eliminar Documento Inbox? Ficará visível no arquivo como Eliminada.'))return;
      const response=await fetch(`/api/colaborador/despesas/processamento/${encodeURIComponent(item.stamp)}`,{method:'DELETE',credentials:'same-origin'});
      const result=await response.json().catch(()=>({}));if(!response.ok||!result.ok)return alert(result.error||'Erro ao eliminar.');await load();return;
    }
    if(event.target.closest('[data-delete-permanent]')){
      if(!confirm('Eliminar Documento Arquivo? Esta ação não pode ser anulada.'))return;
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
      const item=findRow(card.dataset.stamp);clearCompanyValues(card,item,event.target.value);recalculate(card);updateSummary();return;
    }
    recalculate(card);schedule(card);
  });
  el.rows.addEventListener('input',event=>{
    const card=event.target.closest('.expense-card');if(!card)return;
    const accountingLine=event.target.closest('[data-accounting-line]');
    if(accountingLine&&event.target.dataset.field){
      let origins={};try{origins=JSON.parse(accountingLine.dataset.origins||'{}');}catch(_error){}
      origins[event.target.dataset.field]='manual';accountingLine.dataset.origins=JSON.stringify(origins);
    }
    recalculate(card);schedule(card);
  });
  el.rows.addEventListener('scroll',()=>sessionStorage.setItem(`expense-scroll-${archive}`,String(el.rows.scrollTop)),{passive:true});
  el.launch?.addEventListener('click',async()=>{
    if(state.validating)return;
    const stamps=[...state.selected];if(!(await flushPendingSaves(stamps)))return alert('Não foi possível guardar todas as alterações.');
    const issues=[];let firstInvalid='';
    selectedRows().forEach(item=>{const card=el.rows.querySelector(`[data-stamp="${CSS.escape(item.stamp)}"]`),payload=collect(card);const add=message=>{issues.push(`${item.data_despesa||item.penome||'Despesa'}: ${message}`);firstInvalid=firstInvalid||item.stamp;};if(!payload.feid)add('Empresa em falta.');if(!item.peno)add('Número PHC do colaborador em falta.');if(!/^[A-Z]{3}$/.test(String(payload.moeda||'').toUpperCase()))add('Moeda ISO inválida.');payload.accounting_lines.forEach((line,index)=>{const prefix=`linha ${index+1}`;if(!line.artigo_ref)add(`${prefix}: Artigo em falta.`);if(!line.ccusto)add(`${prefix}: Centro de Custo em falta.`);if(!line.tabiva)add(`${prefix}: IVA em falta.`);if(Number(line.total_com_iva)<0)add(`${prefix}: valor negativo não autorizado.`);if(Math.abs((Number(line.total_sem_iva)+Number(line.valor_iva))-Number(line.total_com_iva))>.009)add(`${prefix}: Totais incoerentes.`);});});
    if(issues.length){if(firstInvalid){const card=el.rows.querySelector(`[data-stamp="${CSS.escape(firstInvalid)}"]`);activate(card);card.scrollIntoView({block:'start',behavior:'smooth'});}return alert(issues.join('\n'));}
    const plural=stamps.length!==1;if(!confirm(`Validar ${plural?'Despesas':'Despesa'}? O documento PHC só será criado após o controlo integral.`))return;
    state.validating=true;el.launch.disabled=true;el.launch.querySelector('span').textContent=plural?'A validar Despesas...':'A validar Despesa...';
    try {
      const response=await fetch('/api/colaborador/despesas/processamento/lancar-phc',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'same-origin',body:JSON.stringify({stamps})});
      const result=await response.json().catch(()=>({}));if(!response.ok||!result.ok)throw new Error(result.error||'Erro ao validar despesas no PHC.');
      alert(`Documento criado no PHC: Despesa N.º ${result.obrano}`);await load();
    } catch(error){alert(error.message);} finally {state.validating=false;updateSummary();}
  });
  el.deletePdf?.addEventListener('click',async()=>{
    const item=activeRow();if(!item||!confirm('Eliminar PDF? A despesa e a classificação serão mantidas.'))return;
    const response=await fetch(`/api/colaborador/despesas/processamento/${encodeURIComponent(item.stamp)}/pdf`,{method:'DELETE',credentials:'same-origin'});
    const result=await response.json().catch(()=>({}));if(!response.ok||!result.ok)return alert(result.error||'Erro ao eliminar PDF.');await load();
  });
  el.ai?.addEventListener('click',async()=>{
    const item=activeRow();if(!item)return;
    el.ai.disabled=true;el.ai.innerHTML='<i class="fa-solid fa-circle-notch fa-spin"></i><span>A analisar...</span>';
    const response=await fetch(`/api/colaborador/despesas/processamento/${encodeURIComponent(item.stamp)}/analisar-ia`,{method:'POST',credentials:'same-origin'});
    const result=await response.json().catch(()=>({}));
    el.ai.innerHTML='<i class="fa-solid fa-wand-magic-sparkles"></i><span>IA</span>';
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
  document.querySelectorAll('[data-lookup-close]').forEach(button=>button.addEventListener('click',closeLookup));
  el.lookupSearchButton?.addEventListener('click',searchLookupOptions);
  el.lookupSearch?.addEventListener('keydown',event=>{if(event.key==='Enter'){event.preventDefault();searchLookupOptions();}if(event.key==='Escape')closeLookup();});
  el.lookupResults?.addEventListener('click',event=>{const option=event.target.closest('[data-lookup-index]');if(option)selectLookup(option.dataset.lookupIndex);});
  [el.from,el.to,el.user].forEach(input=>input.addEventListener('change',()=>{saveFilters();load();}));
  el.clearFilters?.addEventListener('click',clearFilters);
  el.refresh.addEventListener('click',load);updateUsers(fallbackUsers);restoreFilters();load();
})();
