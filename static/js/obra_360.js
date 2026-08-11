(() => {
  const page = document.getElementById('obra360Page');
  if (!page) return;

  const code = page.dataset.codigo || '';
  const state = { overview: null, cards: new Map(), activeTab: 'resumo', searchTimer: null };
  const tabConfig = {
    resumo: { title: 'Resumo da obra', description: 'Indicadores e documentos já integrados para esta obra.', cards: ['orcamento', 'autos_cliente', 'faturas_cliente'] },
    comercial: { title: 'Comercial', description: 'Orçamento, contrato e adicionais da obra.', cards: ['orcamento', 'contrato', 'adicionais'] },
    compras: { title: 'Compras', description: 'Compras, fornecedores e faturas imputadas à obra.', cards: ['compras', 'faturas_fornecedor', 'fornecedores'] },
    blbc: { title: 'BC/BL', description: 'Bons de commande e bons de livraison de fornecedor associados à obra.', cards: ['bc', 'bl'] },
    autos: { title: 'Autos', description: 'Autos de cliente e de subempreiteiro.', cards: ['autos_cliente', 'autos_subempreiteiro'] },
    faturacao: { title: 'Faturação', description: 'Faturas de cliente emitidas para a obra.', cards: ['faturas_cliente'] },
    recebimentos: { title: 'Recebimentos', description: 'Recebimentos associados à obra.', cards: ['recebimentos'] },
    custos: { title: 'Custos', description: 'Custos reais e compromissos imputados à obra.', cards: ['custos'] },
    producao: { title: 'Produção', description: 'Produção e materiais associados à obra.', cards: ['producao', 'materiais'] },
    documentos: { title: 'Documentos', description: 'Anexos e documentação operacional.', cards: ['anexos'] },
    financeiro: { title: 'Financeiro', description: 'Proveitos, pagamentos e margem da obra.', cards: ['proveitos', 'pagamentos', 'margem'] },
  };
  const activeCardCodes = ['orcamento', 'autos_cliente', 'faturas_cliente', 'bl', 'bc'];
  const money = new Intl.NumberFormat('pt-PT', { style: 'currency', currency: 'EUR' });

  const esc = (value) => String(value ?? '').replace(/[&<>'"]/g, (char) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[char]));
  const formatMoney = (value) => value === null || value === undefined ? 'Ainda sem dados integrados' : money.format(Number(value));
  const statusLabel = (status) => ({ confirmado: 'Confirmado', parcial: 'Parcial', previsto: 'Previsto', sem_dados: 'Sem dados' }[status] || status || 'Sem dados');

  function renderHeader(work, formUrl) {
    document.getElementById('obra360Title').textContent = `${work.codigo || work.ccusto} · ${work.designacao || 'Obra'}`;
    document.getElementById('obra360Subtitle').textContent = [work.cliente, work.empresa, work.estado].filter(Boolean).join(' · ') || 'Dossiê operacional da obra';
    const facts = [
      ['Código / centro de custo', work.ccusto || work.codigo],
      ['Cliente', work.cliente],
      ['Empresa', work.empresa],
      ['Estado', work.estado],
    ].filter(([, value]) => String(value || '').trim());
    document.getElementById('obra360Header').innerHTML = facts
      .map(([label, value]) => `<div class="obra360-header-item"><span>${esc(label)}</span><strong>${esc(value)}</strong></div>`)
      .join('');
    const link = document.getElementById('obra360FormLink');
    link.href = formUrl; link.hidden = false;
  }

  function cardHtml(card) {
    const hasValue = card.value !== null && card.value !== undefined;
    const recordText = card.record_count === null || card.record_count === undefined ? '' : `${card.record_count} registo${card.record_count === 1 ? '' : 's'}`;
    const action = card.state === 'available'
      ? `<div class="obra360-card-actions"><button type="button" class="sz_button sz_button_ghost" data-detail="${esc(card.code)}"><i class="fa-solid fa-list"></i><span>Detalhe</span></button></div>`
      : `<div class="obra360-card-footer">${esc(card.message || 'Em preparação. Ainda sem dados integrados.')}</div>`;
    return `<article class="sz_panel obra360-card is-${esc(card.state)}" data-card="${esc(card.code)}">
      <div class="obra360-card-top"><h3>${esc(card.title)}</h3><span class="obra360-status is-${esc(card.status)}">${esc(statusLabel(card.status))}</span></div>
      <div class="obra360-card-value${hasValue ? '' : ' is-empty'}">${hasValue ? formatMoney(card.value) : 'Ainda sem dados integrados'}</div>
      <div class="obra360-card-meta">${esc(recordText || card.source || '')}</div>
      <div class="obra360-card-source">${esc(card.source || '')}</div>${action}</article>`;
  }

  function moduleNotice(cards) {
    const pending = cards.filter((card) => card.state === 'preparation').map((card) => card.title);
    if (!pending.length) return '';
    return `<div class="obra360-module-notice"><i class="fa-solid fa-circle-info" aria-hidden="true"></i><div><strong>Em preparação</strong><span>${esc(pending.join(' · '))} ainda não têm dados integrados neste dossiê.</span></div></div>`;
  }

  function renderCards() {
    if (!state.overview) return;
    const config = tabConfig[state.activeTab];
    document.getElementById('obra360SectionTitle').textContent = config.title;
    document.getElementById('obra360SectionDescription').textContent = config.description;
    const source = config.cards
      ? config.cards.map((cardCode) => state.overview.cards.find((card) => card.code === cardCode)).filter(Boolean)
      : state.overview.cards;
    const renderedSource = source.map((card) => state.cards.get(card.code) || card);
    const available = renderedSource.filter((card) => card.state !== 'preparation');
    const cardsHtml = available.length
      ? `<div class="obra360-card-grid">${available.map((card) => cardHtml(card)).join('')}</div>`
      : '';
    const content = `${cardsHtml}${moduleNotice(renderedSource)}`;
    document.getElementById('obra360Cards').innerHTML = content || '<div class="obra360-module-notice"><i class="fa-solid fa-circle-info" aria-hidden="true"></i><div><strong>Sem dados disponíveis</strong><span>Não existem elementos integrados para esta secção.</span></div></div>';
  }

  async function loadCard(cardCode) {
    const response = await fetch(`/api/obra-360/${encodeURIComponent(code)}/cards/${encodeURIComponent(cardCode)}`);
    const data = await response.json();
    if (!response.ok || !data.ok) throw new Error(data.error || 'Não foi possível carregar o card.');
    state.cards.set(cardCode, data.card);
    renderCards();
  }

  function openDetail(cardCode) {
    const card = state.cards.get(cardCode);
    if (!card || !card.drilldown_available) return;
    document.getElementById('obra360DetailTitle').textContent = card.title;
    document.getElementById('obra360DetailSource').textContent = card.source || '';
    const rows = Array.isArray(card.rows) ? card.rows : [];
    const body = document.getElementById('obra360DetailBody');
    if (!rows.length) body.innerHTML = '<div class="sz_empty_state">Não existem documentos disponíveis para este indicador.</div>';
    else {
      const supplierColumn = ['bl', 'bc'].includes(cardCode) ? '<th>Fornecedor</th>' : '';
      body.innerHTML = `<div class="sz_table_wrap"><table class="sz_table sz_table_compact"><thead><tr><th>Documento</th><th>Data</th>${supplierColumn}<th>Referência</th><th>Valor</th><th>Estado</th><th></th></tr></thead><tbody>${rows.map((row) => `<tr><td>${esc(row.descricao || row.ft_descricao || 'Documento PHC')}</td><td>${esc(row.data || '')}</td>${['bl', 'bc'].includes(cardCode) ? `<td>${esc(row.fornecedor || 'Sem fornecedor')}</td>` : ''}<td>${esc(row.processo || row.ccusto || '')}</td><td>${esc(formatMoney(row.total_iva ?? row.total ?? row.producao ?? 0))}</td><td>${row.faturado ? 'Faturado' : (row.fechada ? 'Fechado' : 'Disponível')}</td><td>${cardCode === 'autos_cliente' ? `<button type="button" class="sz_button sz_button_ghost sz_button_compact" data-auto-lines="${esc(row.oristamp)}" data-auto-label="${esc(row.descricao || 'Auto de cliente')}"><i class="fa-solid fa-list"></i><span>Linhas</span></button>` : ''}${['bl', 'bc'].includes(cardCode) ? `<button type="button" class="sz_button sz_button_ghost sz_button_compact" data-logistics-lines="${esc(row.oristamp)}" data-logistics-kind="${esc(cardCode)}" data-logistics-label="${esc(row.descricao || card.title)}"><i class="fa-solid fa-list"></i><span>Linhas</span></button>` : ''}${row.open_url ? `<a class="sz_button sz_button_ghost sz_button_compact" href="${esc(row.open_url)}"><i class="fa-solid fa-arrow-up-right-from-square"></i><span>Abrir</span></a>` : ''}</td></tr>`).join('')}</tbody></table></div>`;
    }
    bootstrap.Modal.getOrCreateInstance(document.getElementById('obra360DetailModal')).show();
  }

  async function openAutoLines(autoStamp, label) {
    const body = document.getElementById('obra360DetailBody');
    body.innerHTML = '<div class="sz_empty_state">A carregar linhas do auto...</div>';
    try {
      const response = await fetch(`/api/obra-360/${encodeURIComponent(code)}/autos/${encodeURIComponent(autoStamp)}/linhas`);
      const data = await response.json();
      if (!response.ok || !data.ok) throw new Error(data.error || 'Não foi possível carregar as linhas do auto.');
      const lines = Array.isArray(data.lines) ? data.lines : [];
      document.getElementById('obra360DetailTitle').textContent = label;
      document.getElementById('obra360DetailSource').textContent = 'Linhas do auto de cliente';
      body.innerHTML = lines.length
        ? `<div class="sz_table_wrap"><table class="sz_table sz_table_compact"><thead><tr><th>Ref.</th><th>Designação</th><th>Un.</th><th>Qtd.</th><th>Preço unit.</th><th>IVA</th><th>Total</th></tr></thead><tbody>${lines.map((line) => `<tr><td>${esc(line.reference || '')}</td><td>${esc(line.designation || line.description || '')}</td><td>${esc(line.unit || '')}</td><td>${esc(line.quantity ?? '')}</td><td>${esc(formatMoney(line.unit_price))}</td><td>${esc(line.vat_rate ?? 0)}%</td><td>${esc(formatMoney(line.total))}</td></tr>`).join('')}</tbody></table></div>`
        : '<div class="sz_empty_state">Este auto não tem linhas.</div>';
    } catch (error) {
      body.innerHTML = `<div class="sz_empty_state">${esc(error.message)}</div>`;
    }
  }

  async function openLogisticsLines(kind, documentStamp, label) {
    const body = document.getElementById('obra360DetailBody');
    body.innerHTML = '<div class="sz_empty_state">A carregar linhas do documento...</div>';
    try {
      const response = await fetch(`/api/obra-360/${encodeURIComponent(code)}/logistica/${encodeURIComponent(kind)}/${encodeURIComponent(documentStamp)}/linhas`);
      const data = await response.json();
      if (!response.ok || !data.ok) throw new Error(data.error || 'Não foi possível carregar as linhas deste documento.');
      const lines = Array.isArray(data.lines) ? data.lines : [];
      document.getElementById('obra360DetailTitle').textContent = label;
      document.getElementById('obra360DetailSource').textContent = kind === 'bl' ? 'Linhas do bon de livraison fornecedor' : 'Linhas do bon de commande fornecedor';
      body.innerHTML = lines.length
        ? `<div class="sz_table_wrap"><table class="sz_table sz_table_compact"><thead><tr><th>Ref.</th><th>Designação</th><th>Un.</th><th>Qtd.</th><th>Preço unit.</th><th>IVA</th><th>Total</th></tr></thead><tbody>${lines.map((line) => `<tr><td>${esc(line.reference || '')}</td><td>${esc(line.designation || line.description || '')}</td><td>${esc(line.unit || '')}</td><td>${esc(line.quantity ?? '')}</td><td>${esc(formatMoney(line.unit_price))}</td><td>${esc(line.vat_rate ?? 0)}%</td><td>${esc(formatMoney(line.total))}</td></tr>`).join('')}</tbody></table></div>`
        : '<div class="sz_empty_state">Este documento não tem linhas.</div>';
    } catch (error) {
      body.innerHTML = `<div class="sz_empty_state">${esc(error.message)}</div>`;
    }
  }

  function renderSearchResults(works) {
    const box = document.getElementById('obra360SearchResults');
    if (!works.length) { box.innerHTML = '<div class="obra360-search-empty">Sem obras encontradas.</div>'; box.hidden = false; return; }
    box.innerHTML = works.map((work) => `<button type="button" data-code="${esc(work.codigo)}"><strong>${esc(work.codigo)} · ${esc(work.designacao || 'Sem designação')}</strong><span>${esc([work.cliente, work.empresa, work.estado].filter(Boolean).join(' · '))}</span></button>`).join('');
    box.hidden = false;
  }

  async function search(query) {
    if (query.trim().length < 2) { document.getElementById('obra360SearchResults').hidden = true; return; }
    const response = await fetch(`/api/obra-360/search?q=${encodeURIComponent(query)}`);
    const data = await response.json();
    renderSearchResults(data.works || []);
  }

  async function init() {
    const response = await fetch(`/api/obra-360/${encodeURIComponent(code)}/overview`);
    const data = await response.json();
    if (data.ambiguous) { renderSearchResults(data.works || []); document.getElementById('obra360Title').textContent = 'Escolha a obra'; document.getElementById('obra360Subtitle').textContent = 'Foram encontradas várias obras com este código.'; return; }
    if (!response.ok || !data.ok) throw new Error(data.error || 'Não foi possível abrir o dossiê da obra.');
    state.overview = data; renderHeader(data.work, data.form_url); renderCards();
    for (const cardCode of activeCardCodes) {
      try { await loadCard(cardCode); } catch (error) { console.error(error); }
    }
  }

  document.querySelector('.obra360-tabs').addEventListener('click', (event) => {
    const button = event.target.closest('[data-tab]'); if (!button) return;
    state.activeTab = button.dataset.tab;
    document.querySelectorAll('.obra360-tab').forEach((tab) => tab.classList.toggle('is-active', tab === button));
    renderCards();
  });
  document.getElementById('obra360Cards').addEventListener('click', (event) => { const button = event.target.closest('[data-detail]'); if (button) openDetail(button.dataset.detail); });
  document.getElementById('obra360DetailBody').addEventListener('click', (event) => {
    const button = event.target.closest('[data-auto-lines]');
    if (button) openAutoLines(button.dataset.autoLines, button.dataset.autoLabel);
    const logisticsButton = event.target.closest('[data-logistics-lines]');
    if (logisticsButton) openLogisticsLines(logisticsButton.dataset.logisticsKind, logisticsButton.dataset.logisticsLines, logisticsButton.dataset.logisticsLabel);
  });
  document.getElementById('obra360SearchResults').addEventListener('click', (event) => { const item = event.target.closest('[data-code]'); if (item) window.location.assign(`/obra-360/${encodeURIComponent(item.dataset.code)}`); });
  document.getElementById('obra360Search').addEventListener('input', (event) => { clearTimeout(state.searchTimer); state.searchTimer = setTimeout(() => search(event.target.value), 260); });
  document.addEventListener('click', (event) => { if (!event.target.closest('.obra360-search-wrap')) document.getElementById('obra360SearchResults').hidden = true; });
  init().catch((error) => { document.getElementById('obra360Title').textContent = 'Não foi possível abrir a obra'; document.getElementById('obra360Subtitle').textContent = error.message; document.getElementById('obra360Header').innerHTML = `<div class="obra360-error">${esc(error.message)}</div>`; });
})();
