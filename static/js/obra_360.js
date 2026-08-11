(() => {
  const page = document.getElementById('obra360Page');
  if (!page) return;

  const code = page.dataset.codigo || '';
  const state = { overview: null, cards: new Map(), activeTab: 'resumo', searchTimer: null, allowedTabs: new Set() };
  const tabConfig = {
    resumo: { title: 'Resumo da obra', description: 'Indicadores comerciais, operacionais e de tesouraria da obra.', cards: ['orcamento', 'autos_cliente', 'faturas_cliente'] },
    comercial: { title: 'Comercial', description: 'Orçamento, contrato e adicionais da obra.', cards: ['orcamento', 'contrato', 'adicionais'] },
    compras: { title: 'Compras', description: 'Compras imputadas à obra.', cards: ['compras'] },
    blbc: { title: 'BC/BL', description: 'Bons de commande e bons de livraison de fornecedor associados à obra.', cards: ['bc', 'bl'] },
    autos: { title: 'Autos', description: 'Autos de cliente e de subempreiteiro.', cards: ['autos_cliente', 'autos_subempreiteiro'] },
    faturacao: { title: 'Faturação', description: 'Faturas de cliente emitidas para a obra.', cards: ['faturas_cliente'] },
    recebimentos: { title: 'Tesouraria', description: 'Recebimentos de cliente e pagamentos a fornecedor associados à obra.', cards: ['recebimentos', 'pagamentos'] },
    custos: { title: 'Custos', description: 'Custos reais e compromissos imputados à obra.', cards: ['custos'] },
    producao: { title: 'Produção', description: 'Marcações de planeamento, intervenções executadas e equipas da obra.', cards: ['producao'] },
    documentos: { title: 'Documentos', description: 'Anexos e documentação operacional.', cards: ['anexos'] },
  };
  const activeCardCodes = ['orcamento', 'compras', 'autos_cliente', 'autos_subempreiteiro', 'contratos_se', 'faturas_cliente', 'recebimentos', 'pagamentos', 'bl', 'bc', 'custos', 'producao', 'anexos'];
  const cardTabCodes = {
    orcamento: 'comercial', compras: 'compras', autos_cliente: 'autos', autos_subempreiteiro: 'autos', contratos_se: 'autos',
    faturas_cliente: 'faturacao', recebimentos: 'recebimentos', pagamentos: 'recebimentos',
    bl: 'blbc', bc: 'blbc', custos: 'custos', producao: 'producao', anexos: 'documentos',
    contratos_se: 'autos',
  };
  const money = new Intl.NumberFormat('pt-PT', { style: 'currency', currency: 'EUR' });

  const esc = (value) => String(value ?? '').replace(/[&<>'"]/g, (char) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[char]));
  const formatMoney = (value) => value === null || value === undefined ? 'Ainda sem dados integrados' : money.format(Number(value));
  const statusLabel = (status) => ({ confirmado: 'Confirmado', parcial: 'Parcial', previsto: 'Previsto', sem_dados: 'Sem dados', planeada: 'Planeada', em_execucao: 'Em execução', concluida: 'Concluída' }[status] || status || 'Sem dados');
  const formatDate = (value) => {
    if (!value) return 'Sem data';
    const match = String(value).match(/^(\d{4})-(\d{2})-(\d{2})/);
    return match ? `${match[3]}/${match[2]}/${match[1]}` : String(value);
  };

  function confirmedCardValue(cardCode) {
    const card = state.cards.get(cardCode);
    if (!card || card.state !== 'available' || card.value === null || card.value === undefined) return null;
    const value = Number(card.value);
    return Number.isFinite(value) ? value : null;
  }

  function renderSummaryKpis() {
    const container = document.getElementById('obra360SummaryKpis');
    if (!container) return;
    if (state.activeTab !== 'resumo') {
      container.hidden = true;
      container.innerHTML = '';
      return;
    }

    const received = confirmedCardValue('recebimentos');
    const paid = confirmedCardValue('pagamentos');
    const revenue = confirmedCardValue('faturas_cliente');
    const costs = confirmedCardValue('custos');
    const treasury = received !== null && paid !== null ? received - paid : null;
    const margin = revenue !== null && costs !== null ? revenue - costs : null;
    const indicators = [
      {
        label: 'Saldo de tesouraria',
        value: treasury,
        source: 'Recebimentos - pagamentos',
      },
      {
        label: 'Margem da obra',
        value: margin,
        source: 'Proveitos faturados - custos',
      },
    ];
    container.innerHTML = indicators.map((indicator) => `<div class="obra360-summary-kpi">
      <span>${esc(indicator.label)}</span>
      <strong class="${indicator.value === null ? 'is-empty' : ''}">${indicator.value === null ? 'Ainda sem dados integrados' : esc(formatMoney(indicator.value))}</strong>
      <small>${esc(indicator.source)}</small>
    </div>`).join('');
    container.hidden = false;
  }

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

  function canAccessTab(tabCode) {
    return !state.allowedTabs.size || state.allowedTabs.has(tabCode);
  }

  function renderTabs() {
    document.querySelectorAll('.obra360-tab').forEach((tab) => {
      const allowed = canAccessTab(tab.dataset.tab);
      tab.hidden = !allowed;
      tab.classList.toggle('is-active', allowed && tab.dataset.tab === state.activeTab);
    });
  }

  function cardHtml(card) {
    if (card.display_mode === 'production') {
      const interventionText = `${card.intervention_count || 0} intervenção${card.intervention_count === 1 ? '' : 'ões'}`;
      return `<article class="sz_panel obra360-card is-available obra360-production-card" data-card="${esc(card.code)}">
        <div class="obra360-card-top"><h3>${esc(formatDate(card.date))}</h3><span class="obra360-status is-${esc(card.status)}">${esc(card.status_label || statusLabel(card.status))}</span></div>
        <div class="obra360-card-value obra360-production-team">${esc(card.team || 'Equipa por definir')}</div>
        <div class="obra360-card-meta">${esc(interventionText)}</div>
        <div class="obra360-card-source">Planeamento da obra</div>
        <div class="obra360-card-actions"><button type="button" class="sz_button sz_button_ghost" data-detail="${esc(card.code)}"><i class="fa-solid fa-list"></i><span>Detalhe</span></button></div></article>`;
    }
    if (card.display_mode === 'count') {
      const count = Number(card.record_count || 0);
      return `<article class="sz_panel obra360-card is-available" data-card="${esc(card.code)}">
        <div class="obra360-card-top"><h3>${esc(card.title)}</h3><span class="obra360-status is-${esc(card.status)}">${esc(statusLabel(card.status))}</span></div>
        <div class="obra360-card-value">${count} documento${count === 1 ? '' : 's'}</div>
        <div class="obra360-card-meta">Anexos disponíveis na ficha da obra</div>
        <div class="obra360-card-source">${esc(card.source || '')}</div>
        <div class="obra360-card-actions"><button type="button" class="sz_button sz_button_ghost" data-detail="${esc(card.code)}"><i class="fa-solid fa-list"></i><span>Detalhe</span></button></div></article>`;
    }
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
    renderSummaryKpis();
    const source = config.cards
      ? config.cards.map((cardCode) => state.overview.cards.find((card) => card.code === cardCode)).filter((card) => card && canAccessTab(cardTabCodes[card.code] || state.activeTab))
      : state.overview.cards;
    const renderedSource = source.map((card) => state.cards.get(card.code) || card);
    if (state.activeTab === 'resumo') {
      const cardFor = (cardCode) => {
        const card = state.cards.get(cardCode) || state.overview.cards.find((item) => item.code === cardCode);
        return card && canAccessTab(cardTabCodes[cardCode] || 'resumo') ? card : null;
      };
      const renderRow = (rowClass, cardCodes) => {
        const cards = cardCodes.map(cardFor).filter(Boolean);
        return cards.length ? `<div class="obra360-card-grid obra360-summary-row ${rowClass}">${cards.map((card) => cardHtml(card)).join('')}</div>` : '';
      };
      document.getElementById('obra360Cards').innerHTML = [
        renderRow('obra360-summary-primary', ['orcamento', 'autos_cliente', 'faturas_cliente']),
        renderRow('obra360-summary-operations', ['bc', 'contratos_se', 'bl', 'autos_subempreiteiro', 'compras']),
        renderRow('obra360-summary-treasury', ['pagamentos', 'recebimentos']),
      ].filter(Boolean).join('') || '<div class="obra360-module-notice"><i class="fa-solid fa-circle-info" aria-hidden="true"></i><div><strong>Sem dados disponíveis</strong><span>Não existem elementos integrados para esta secção.</span></div></div>';
      return;
    }
    let available = renderedSource.filter((card) => card.state !== 'preparation');
    const costsCard = state.activeTab === 'custos' ? renderedSource.find((card) => card.code === 'custos') : null;
    if (costsCard && costsCard.state === 'available') {
      available = (costsCard.groups || []).map((group) => {
        const card = {
          ...group,
          code: `custos:${group.family}`,
          cost_family: group.family,
          section: 'costs',
        };
        state.cards.set(card.code, card);
        return card;
      });
    }
    const productionCard = state.activeTab === 'producao' ? renderedSource.find((card) => card.code === 'producao') : null;
    if (productionCard && productionCard.state === 'available') {
      available = (productionCard.assignments || []).map((assignment) => {
        const card = {
          ...assignment,
          code: `producao:${assignment.plan_stamp}`,
          production_plan_stamp: assignment.plan_stamp,
          display_mode: 'production',
          drilldown_available: true,
        };
        state.cards.set(card.code, card);
        return card;
      });
    }
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
    if (card.production_plan_stamp) {
      openProductionDetail(card.production_plan_stamp, card.date, card.team);
      return;
    }
    if (card.cost_family) {
      openCostSubgroups(card.cost_family, card.title);
      return;
    }
    document.getElementById('obra360DetailTitle').textContent = card.title;
    document.getElementById('obra360DetailSource').textContent = card.source || '';
    const rows = Array.isArray(card.rows) ? card.rows : [];
    const body = document.getElementById('obra360DetailBody');
    if (!rows.length) body.innerHTML = '<div class="sz_empty_state">Não existem documentos disponíveis para este indicador.</div>';
    else if (cardCode === 'anexos') {
      body.innerHTML = `<div class="sz_table_wrap"><table class="sz_table sz_table_compact"><thead><tr><th>Descrição</th><th>Ficheiro</th><th>Data</th><th>Tipo</th><th>Tamanho</th></tr></thead><tbody>${rows.map((row) => `<tr><td>${esc(row.description || 'Anexo PHC')}</td><td>${esc(row.filename || '')}</td><td>${esc(formatDate(row.date))}</td><td>${esc(row.extension || '')}</td><td>${esc(row.size ? `${Math.round(Number(row.size) / 1024)} KB` : '')}</td></tr>`).join('')}</tbody></table></div>`;
    }
    else {
      const partyColumn = ['compras', 'autos_subempreiteiro', 'contratos_se', 'bl', 'bc', 'pagamentos'].includes(cardCode) ? '<th>Fornecedor</th>' : (cardCode === 'recebimentos' ? '<th>Cliente</th>' : '');
      body.innerHTML = `<div class="sz_table_wrap"><table class="sz_table sz_table_compact"><thead><tr><th>Documento</th><th>Data</th>${partyColumn}<th>Referência</th><th>Valor</th><th>Estado</th><th></th></tr></thead><tbody>${rows.map((row) => `<tr><td>${esc(row.descricao || row.ft_descricao || 'Documento PHC')}</td><td>${esc(row.data || '')}</td>${partyColumn ? `<td>${esc(row.fornecedor || row.cliente || 'Sem entidade')}</td>` : ''}<td>${esc(row.processo || row.ccusto || '')}</td><td>${esc(formatMoney(row.total_iva ?? row.total ?? row.producao ?? 0))}</td><td>${esc(row.estado || (row.faturado ? 'Faturado' : (row.fechada ? 'Fechado' : 'Disponível')))}</td><td>${cardCode === 'autos_cliente' ? `<button type="button" class="sz_button sz_button_ghost sz_button_compact" data-auto-lines="${esc(row.oristamp)}" data-auto-label="${esc(row.descricao || 'Auto de cliente')}"><i class="fa-solid fa-list"></i><span>Linhas</span></button>` : ''}${cardCode === 'autos_subempreiteiro' ? `<button type="button" class="sz_button sz_button_ghost sz_button_compact" data-subcontractor-auto-lines="${esc(row.oristamp)}" data-subcontractor-auto-label="${esc(row.descricao || 'Auto de subempreitada')}"><i class="fa-solid fa-list"></i><span>Linhas</span></button>` : ''}${cardCode === 'contratos_se' ? `<button type="button" class="sz_button sz_button_ghost sz_button_compact" data-contract-lines="${esc(row.oristamp)}" data-contract-label="${esc(row.descricao || 'Contrato de subempreitada')}"><i class="fa-solid fa-list"></i><span>Detalhe</span></button>` : ''}${cardCode === 'compras' ? `<button type="button" class="sz_button sz_button_ghost sz_button_compact" data-purchase-lines="${esc(row.oristamp)}" data-purchase-label="${esc(row.descricao || 'Compra de fornecedor')}"><i class="fa-solid fa-list"></i><span>Linhas</span></button>` : ''}${cardCode === 'recebimentos' ? `<button type="button" class="sz_button sz_button_ghost sz_button_compact" data-receipt-lines="${esc(row.oristamp)}" data-receipt-label="${esc(row.descricao || 'Recebimento')}"><i class="fa-solid fa-list"></i><span>Linhas</span></button>` : ''}${cardCode === 'pagamentos' ? `<button type="button" class="sz_button sz_button_ghost sz_button_compact" data-payment-lines="${esc(row.oristamp)}" data-payment-label="${esc(row.descricao || 'Pagamento')}"><i class="fa-solid fa-list"></i><span>Linhas</span></button>` : ''}${cardCode === 'faturas_cliente' ? `<button type="button" class="sz_button sz_button_ghost sz_button_compact" data-invoice-lines="${esc(row.oristamp)}" data-invoice-label="${esc(row.descricao || 'Fatura de cliente')}"><i class="fa-solid fa-list"></i><span>Linhas</span></button>` : ''}${['bl', 'bc'].includes(cardCode) ? `<button type="button" class="sz_button sz_button_ghost sz_button_compact" data-logistics-lines="${esc(row.oristamp)}" data-logistics-kind="${esc(cardCode)}" data-logistics-label="${esc(row.descricao || card.title)}"><i class="fa-solid fa-list"></i><span>Linhas</span></button>` : ''}${row.open_url ? `<a class="sz_button sz_button_ghost sz_button_compact" href="${esc(row.open_url)}"><i class="fa-solid fa-arrow-up-right-from-square"></i><span>Abrir</span></a>` : ''}</td></tr>`).join('')}</tbody></table></div>`;
    }
    bootstrap.Modal.getOrCreateInstance(document.getElementById('obra360DetailModal')).show();
  }

  async function openCostSubgroups(family, label) {
    const modal = bootstrap.Modal.getOrCreateInstance(document.getElementById('obra360DetailModal'));
    const body = document.getElementById('obra360DetailBody');
    document.getElementById('obra360DetailTitle').textContent = label;
    document.getElementById('obra360DetailSource').textContent = 'Mapa de Gestão / v_custo';
    body.innerHTML = '<div class="sz_empty_state">A carregar subgrupos de custos...</div>';
    modal.show();
    try {
      const response = await fetch(`/api/obra-360/${encodeURIComponent(code)}/custos/${encodeURIComponent(family)}/subgrupos`);
      const data = await response.json();
      if (!response.ok || !data.ok) throw new Error(data.error || 'Não foi possível carregar os subgrupos de custos.');
      const groups = Array.isArray(data.subgroups) ? data.subgroups : [];
      body.innerHTML = groups.length
        ? `<div class="sz_table_wrap"><table class="sz_table sz_table_compact"><thead><tr><th>Subgrupo</th><th>Movimentos</th><th>Último movimento</th><th>Total</th><th></th></tr></thead><tbody>${groups.map((group) => `<tr><td>${esc(group.title || group.family)}</td><td>${esc(group.record_count || 0)}</td><td>${esc(group.updated_at || '')}</td><td>${esc(formatMoney(group.total))}</td><td><button type="button" class="sz_button sz_button_ghost sz_button_compact" data-cost-lines="${esc(group.family)}" data-cost-label="${esc(group.title || group.family)}"><i class="fa-solid fa-list"></i><span>Movimentos</span></button></td></tr>`).join('')}</tbody></table></div>`
        : '<div class="sz_empty_state">Não existem subgrupos de custos nesta família.</div>';
    } catch (error) {
      body.innerHTML = `<div class="sz_empty_state">${esc(error.message)}</div>`;
    }
  }

  async function openCostLines(family, label) {
    const body = document.getElementById('obra360DetailBody');
    document.getElementById('obra360DetailTitle').textContent = label;
    document.getElementById('obra360DetailSource').textContent = 'Movimentos de custo / Mapa de Gestão';
    body.innerHTML = '<div class="sz_empty_state">A carregar movimentos de custo...</div>';
    try {
      const response = await fetch(`/api/obra-360/${encodeURIComponent(code)}/custos/${encodeURIComponent(family)}/linhas`);
      const data = await response.json();
      if (!response.ok || !data.ok) throw new Error(data.error || 'Não foi possível carregar os movimentos de custo.');
      const lines = Array.isArray(data.lines) ? data.lines : [];
      body.innerHTML = lines.length
        ? `<div class="sz_table_wrap"><table class="sz_table sz_table_compact"><thead><tr><th>Documento</th><th>Data</th><th>Fornecedor</th><th>Ref.</th><th>Designação</th><th>Qtd.</th><th>Preço unit.</th><th>Total</th></tr></thead><tbody>${lines.map((line) => `<tr><td>${esc([line.document, line.number].filter(Boolean).join(' ') || 'Movimento')}</td><td>${esc(line.date || '')}</td><td>${esc(line.supplier || '')}</td><td>${esc(line.reference || '')}</td><td>${esc(line.designation || '')}</td><td>${esc(line.quantity ?? '')}</td><td>${esc(formatMoney(line.unit_price))}</td><td>${esc(formatMoney(line.total))}</td></tr>`).join('')}</tbody></table></div>`
        : '<div class="sz_empty_state">Não existem movimentos de custo neste subgrupo.</div>';
    } catch (error) {
      body.innerHTML = `<div class="sz_empty_state">${esc(error.message)}</div>`;
    }
  }

  async function openProductionDetail(planStamp, plannedDate, team) {
    const modal = bootstrap.Modal.getOrCreateInstance(document.getElementById('obra360DetailModal'));
    const body = document.getElementById('obra360DetailBody');
    document.getElementById('obra360DetailTitle').textContent = `Produção · ${formatDate(plannedDate)}`;
    document.getElementById('obra360DetailSource').textContent = team || 'Planeamento da obra';
    body.innerHTML = '<div class="sz_empty_state">A carregar intervenções e equipa...</div>';
    modal.show();
    try {
      const response = await fetch(`/api/obra-360/${encodeURIComponent(code)}/producao/${encodeURIComponent(planStamp)}/detalhe`);
      const data = await response.json();
      if (!response.ok || !data.ok) throw new Error(data.error || 'Não foi possível carregar a marcação de produção.');
      const interventions = Array.isArray(data.interventions) ? data.interventions : [];
      if (!interventions.length) {
        body.innerHTML = '<div class="sz_empty_state">Esta marcação ainda não tem intervenções executadas.</div>';
        return;
      }
      body.innerHTML = interventions.map((intervention, index) => {
        const members = Array.isArray(intervention.members) ? intervention.members : [];
        const metrics = [
          intervention.quantity ? `Produção: ${intervention.quantity} m²` : '',
          intervention.kg_ferro ? `Ferro: ${intervention.kg_ferro} kg` : '',
          intervention.m2_serragem ? `Serragem: ${intervention.m2_serragem} m²` : '',
          intervention.m3_betao ? `Betão: ${intervention.m3_betao} m³` : '',
        ].filter(Boolean).join(' · ');
        return `<section class="obra360-production-detail">
          <div class="obra360-production-detail-head"><strong>Intervenção ${index + 1}</strong><span class="obra360-status is-confirmado">${esc(intervention.status || '')}</span></div>
          <p><strong>${esc(intervention.description || 'Sem descrição')}</strong></p>
          ${intervention.finish ? `<p>${esc(intervention.finish)}</p>` : ''}
          ${metrics ? `<p class="obra360-card-meta">${esc(metrics)}</p>` : ''}
          ${intervention.notes ? `<p class="obra360-card-meta">${esc(intervention.notes)}</p>` : ''}
          <div class="obra360-production-members"><strong>Produção por elemento</strong>${members.length ? `<div class="sz_table_wrap"><table class="sz_table sz_table_compact"><thead><tr><th>Colaborador</th><th>M²</th><th>Kg ferro</th><th>M² serragem</th></tr></thead><tbody>${members.map((member) => `<tr><td>${esc(member.name || 'Sem nome')}${member.number ? ` <span class="obra360-production-member-number">N.º ${esc(member.number)}</span>` : ''}</td><td>${esc(member.quantity ?? 0)}</td><td>${esc(member.kg_ferro ?? 0)}</td><td>${esc(member.m2_serragem ?? 0)}</td></tr>`).join('')}</tbody></table></div>` : '<p class="obra360-card-meta">Sem elementos registados.</p>'}</div>
        </section>`;
      }).join('');
    } catch (error) {
      body.innerHTML = `<div class="sz_empty_state">${esc(error.message)}</div>`;
    }
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

  async function openSubcontractorContractDetail(contractStamp, label) {
    const body = document.getElementById('obra360DetailBody');
    document.getElementById('obra360DetailTitle').textContent = label;
    document.getElementById('obra360DetailSource').textContent = 'Contrato de subempreitada';
    body.innerHTML = '<div class="sz_empty_state">A carregar contrato e execução...</div>';
    try {
      const response = await fetch(`/api/obra-360/${encodeURIComponent(code)}/contratos-se/${encodeURIComponent(contractStamp)}/detalhe`);
      const data = await response.json();
      if (!response.ok || !data.ok) throw new Error(data.error || 'Não foi possível carregar o contrato de subempreitada.');
      const contract = data.contract || {};
      const lines = Array.isArray(data.lines) ? data.lines : [];
      document.getElementById('obra360DetailTitle').textContent = `${label} · ${contract.supplier_name || 'Subempreiteiro'}`;
      document.getElementById('obra360DetailSource').textContent = `Contratado: ${formatMoney(contract.contract_value)} · Executado: ${formatMoney(contract.executed_value)} · Por executar: ${formatMoney(contract.remaining_value)}`;
      body.innerHTML = lines.length
        ? `<div class="sz_table_wrap"><table class="sz_table sz_table_compact"><thead><tr><th>Ref.</th><th>Designação</th><th>Un.</th><th>Contratado</th><th>Executado</th><th>Por executar</th><th>Valor</th><th>Executado</th><th>Por executar</th></tr></thead><tbody>${lines.map((line) => `<tr><td>${esc(line.ref || '')}</td><td>${esc(line.design || '')}</td><td>${esc(line.unit || '')}</td><td>${esc(line.qty ?? '')}</td><td>${esc(line.executed_qty ?? '')}</td><td>${esc(line.remaining_qty ?? '')}</td><td>${esc(formatMoney(line.value))}</td><td>${esc(formatMoney(line.executed_value))}</td><td>${esc(formatMoney(line.remaining_value))}</td></tr>`).join('')}</tbody></table></div>`
        : '<div class="sz_empty_state">Este contrato não tem linhas.</div>';
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

  async function openPurchaseLines(purchaseStamp, label) {
    const body = document.getElementById('obra360DetailBody');
    body.innerHTML = '<div class="sz_empty_state">A carregar linhas da compra...</div>';
    try {
      const response = await fetch(`/api/obra-360/${encodeURIComponent(code)}/compras/${encodeURIComponent(purchaseStamp)}/linhas`);
      const data = await response.json();
      if (!response.ok || !data.ok) throw new Error(data.error || 'Não foi possível carregar as linhas desta compra.');
      const lines = Array.isArray(data.lines) ? data.lines : [];
      document.getElementById('obra360DetailTitle').textContent = label;
      document.getElementById('obra360DetailSource').textContent = 'Linhas da compra de fornecedor';
      body.innerHTML = lines.length
        ? `<div class="sz_table_wrap"><table class="sz_table sz_table_compact"><thead><tr><th>Ref.</th><th>Designação</th><th>Un.</th><th>Qtd.</th><th>Preço unit.</th><th>IVA</th><th>Total</th></tr></thead><tbody>${lines.map((line) => `<tr><td>${esc(line.reference || '')}</td><td>${esc(line.designation || '')}</td><td>${esc(line.unit || '')}</td><td>${esc(line.quantity ?? '')}</td><td>${esc(formatMoney(line.unit_price))}</td><td>${esc(line.vat_rate ?? 0)}%</td><td>${esc(formatMoney(line.total))}</td></tr>`).join('')}</tbody></table></div>`
        : '<div class="sz_empty_state">Esta compra não tem linhas.</div>';
    } catch (error) {
      body.innerHTML = `<div class="sz_empty_state">${esc(error.message)}</div>`;
    }
  }

  async function openSubcontractorAutoLines(autoStamp, label) {
    const body = document.getElementById('obra360DetailBody');
    body.innerHTML = '<div class="sz_empty_state">A carregar linhas do auto de subempreitada...</div>';
    try {
      const response = await fetch(`/api/obra-360/${encodeURIComponent(code)}/autos-subempreiteiro/${encodeURIComponent(autoStamp)}/linhas`);
      const data = await response.json();
      if (!response.ok || !data.ok) throw new Error(data.error || 'Não foi possível carregar as linhas deste auto de subempreitada.');
      const lines = Array.isArray(data.lines) ? data.lines : [];
      document.getElementById('obra360DetailTitle').textContent = label;
      document.getElementById('obra360DetailSource').textContent = 'Linhas do auto de subempreitada';
      body.innerHTML = lines.length
        ? `<div class="sz_table_wrap"><table class="sz_table sz_table_compact"><thead><tr><th>Ref.</th><th>Designação</th><th>Un.</th><th>Qtd.</th><th>Preço unit.</th><th>IVA</th><th>Total</th></tr></thead><tbody>${lines.map((line) => `<tr><td>${esc(line.reference || '')}</td><td>${esc(line.designation || line.description || '')}</td><td>${esc(line.unit || '')}</td><td>${esc(line.quantity ?? '')}</td><td>${esc(formatMoney(line.unit_price))}</td><td>${esc(line.vat_rate ?? 0)}%</td><td>${esc(formatMoney(line.total))}</td></tr>`).join('')}</tbody></table></div>`
        : '<div class="sz_empty_state">Este auto não tem linhas.</div>';
    } catch (error) {
      body.innerHTML = `<div class="sz_empty_state">${esc(error.message)}</div>`;
    }
  }

  async function openSettlementLines(kind, documentStamp, label) {
    const isReceipt = kind === 'recebimentos';
    const body = document.getElementById('obra360DetailBody');
    body.innerHTML = `<div class="sz_empty_state">A carregar linhas do ${isReceipt ? 'recebimento' : 'pagamento'}...</div>`;
    try {
      const response = await fetch(`/api/obra-360/${encodeURIComponent(code)}/${kind}/${encodeURIComponent(documentStamp)}/linhas`);
      const data = await response.json();
      if (!response.ok || !data.ok) throw new Error(data.error || `Não foi possível carregar as linhas deste ${isReceipt ? 'recebimento' : 'pagamento'}.`);
      const lines = Array.isArray(data.lines) ? data.lines : [];
      document.getElementById('obra360DetailTitle').textContent = label;
      document.getElementById('obra360DetailSource').textContent = isReceipt ? 'Faturas de cliente liquidadas neste recebimento' : 'Compras de fornecedor liquidadas neste pagamento';
      const partyLabel = isReceipt ? 'Cliente' : 'Fornecedor';
      const amountLabel = isReceipt ? 'Recebido' : 'Pago';
      body.innerHTML = lines.length
        ? `<div class="sz_table_wrap"><table class="sz_table sz_table_compact"><thead><tr><th>Documento</th><th>Data</th><th>${partyLabel}</th><th>Valor documento</th><th>${amountLabel}</th></tr></thead><tbody>${lines.map((line) => `<tr><td>${esc(line.document || '')}</td><td>${esc(line.date || '')}</td><td>${esc(line.client || line.supplier || '')}</td><td>${esc(formatMoney(line.invoice_total ?? line.purchase_total))}</td><td>${esc(formatMoney(line.received ?? line.paid))}</td></tr>`).join('')}</tbody></table></div>`
        : `<div class="sz_empty_state">Este ${isReceipt ? 'recebimento' : 'pagamento'} não tem linhas desta obra.</div>`;
    } catch (error) {
      body.innerHTML = `<div class="sz_empty_state">${esc(error.message)}</div>`;
    }
  }

  async function openInvoiceLines(invoiceStamp, label) {
    const body = document.getElementById('obra360DetailBody');
    body.innerHTML = '<div class="sz_empty_state">A carregar linhas da fatura...</div>';
    try {
      const response = await fetch(`/api/obra-360/${encodeURIComponent(code)}/faturas/${encodeURIComponent(invoiceStamp)}/linhas`);
      const data = await response.json();
      if (!response.ok || !data.ok) throw new Error(data.error || 'Não foi possível carregar as linhas da fatura.');
      const lines = Array.isArray(data.lines) ? data.lines : [];
      document.getElementById('obra360DetailTitle').textContent = label;
      document.getElementById('obra360DetailSource').textContent = 'Linhas da fatura de cliente';
      body.innerHTML = lines.length
        ? `<div class="sz_table_wrap"><table class="sz_table sz_table_compact"><thead><tr><th>Ref.</th><th>Designação</th><th>Un.</th><th>Qtd.</th><th>Preço unit.</th><th>IVA</th><th>Total</th></tr></thead><tbody>${lines.map((line) => `<tr><td>${esc(line.reference || '')}</td><td>${esc(line.designation || line.description || '')}</td><td>${esc(line.unit || '')}</td><td>${esc(line.quantity ?? '')}</td><td>${esc(formatMoney(line.unit_price))}</td><td>${esc(line.vat_rate ?? 0)}%</td><td>${esc(formatMoney(line.total))}</td></tr>`).join('')}</tbody></table></div>`
        : '<div class="sz_empty_state">Esta fatura não tem linhas.</div>';
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
    state.overview = data;
    state.allowedTabs = new Set(data.allowed_tabs || Object.keys(tabConfig));
    if (!canAccessTab(state.activeTab)) state.activeTab = [...state.allowedTabs][0] || 'resumo';
    renderHeader(data.work, data.form_url); renderTabs(); renderCards();
    for (const cardCode of activeCardCodes.filter((item) => canAccessTab(cardTabCodes[item]))) {
      try { await loadCard(cardCode); } catch (error) { console.error(error); }
    }
  }

  document.querySelector('.obra360-tabs').addEventListener('click', (event) => {
    const button = event.target.closest('[data-tab]'); if (!button) return;
    if (!canAccessTab(button.dataset.tab)) return;
    state.activeTab = button.dataset.tab;
    renderTabs();
    renderCards();
  });
  document.getElementById('obra360Cards').addEventListener('click', (event) => { const button = event.target.closest('[data-detail]'); if (button) openDetail(button.dataset.detail); });
  document.getElementById('obra360DetailBody').addEventListener('click', (event) => {
    const button = event.target.closest('[data-auto-lines]');
    if (button) openAutoLines(button.dataset.autoLines, button.dataset.autoLabel);
    const contractButton = event.target.closest('[data-contract-lines]');
    if (contractButton) openSubcontractorContractDetail(contractButton.dataset.contractLines, contractButton.dataset.contractLabel);
    const logisticsButton = event.target.closest('[data-logistics-lines]');
    if (logisticsButton) openLogisticsLines(logisticsButton.dataset.logisticsKind, logisticsButton.dataset.logisticsLines, logisticsButton.dataset.logisticsLabel);
    const purchaseButton = event.target.closest('[data-purchase-lines]');
    if (purchaseButton) openPurchaseLines(purchaseButton.dataset.purchaseLines, purchaseButton.dataset.purchaseLabel);
    const subcontractorAutoButton = event.target.closest('[data-subcontractor-auto-lines]');
    if (subcontractorAutoButton) openSubcontractorAutoLines(subcontractorAutoButton.dataset.subcontractorAutoLines, subcontractorAutoButton.dataset.subcontractorAutoLabel);
    const receiptButton = event.target.closest('[data-receipt-lines]');
    if (receiptButton) openSettlementLines('recebimentos', receiptButton.dataset.receiptLines, receiptButton.dataset.receiptLabel);
    const paymentButton = event.target.closest('[data-payment-lines]');
    if (paymentButton) openSettlementLines('pagamentos', paymentButton.dataset.paymentLines, paymentButton.dataset.paymentLabel);
    const invoiceButton = event.target.closest('[data-invoice-lines]');
    if (invoiceButton) openInvoiceLines(invoiceButton.dataset.invoiceLines, invoiceButton.dataset.invoiceLabel);
    const costLinesButton = event.target.closest('[data-cost-lines]');
    if (costLinesButton) openCostLines(costLinesButton.dataset.costLines, costLinesButton.dataset.costLabel);
  });
  document.getElementById('obra360SearchResults').addEventListener('click', (event) => { const item = event.target.closest('[data-code]'); if (item) window.location.assign(`/obra-360/${encodeURIComponent(item.dataset.code)}`); });
  document.getElementById('obra360Search').addEventListener('input', (event) => { clearTimeout(state.searchTimer); state.searchTimer = setTimeout(() => search(event.target.value), 260); });
  document.addEventListener('click', (event) => { if (!event.target.closest('.obra360-search-wrap')) document.getElementById('obra360SearchResults').hidden = true; });

  function accessMatrixHtml(data) {
    const tabs = Array.isArray(data.tabs) ? data.tabs : [];
    const users = Array.isArray(data.users) ? data.users : [];
    if (!users.length) return '<div class="sz_empty_state">Não existem utilizadores para configurar.</div>';
    return `<div class="sz_table_wrap obra360-access-table-wrap"><table class="sz_table sz_table_compact obra360-access-table"><thead><tr><th>Utilizador</th>${tabs.map((tab) => `<th title="${esc(tab.label)}">${esc(tab.label)}</th>`).join('')}</tr></thead><tbody>${users.map((user) => `<tr data-usstamp="${esc(user.usstamp)}"><td><strong>${esc(user.nome || user.login)}</strong><span>${esc(user.login)}${user.admin ? ' · Administrador' : ''}</span></td>${tabs.map((tab) => `<td><input type="checkbox" data-access-tab="${esc(tab.code)}" ${user.tabs.includes(tab.code) ? 'checked' : ''} ${user.admin ? 'disabled' : ''} aria-label="${esc(`${user.nome || user.login} - ${tab.label}`)}"></td>`).join('')}</tr>`).join('')}</tbody></table></div>`;
  }

  async function openAccessModal() {
    const modalElement = document.getElementById('obra360AccessModal');
    const body = document.getElementById('obra360AccessBody');
    if (!modalElement || !body) return;
    const modal = bootstrap.Modal.getOrCreateInstance(modalElement);
    body.innerHTML = '<div class="sz_empty_state">A carregar acessos...</div>';
    modal.show();
    try {
      const response = await fetch('/api/obra-360/acessos');
      const data = await response.json();
      if (!response.ok || !data.ok) throw new Error(data.error || 'Não foi possível carregar os acessos.');
      body.innerHTML = accessMatrixHtml(data);
    } catch (error) {
      body.innerHTML = `<div class="sz_empty_state">${esc(error.message)}</div>`;
    }
  }

  async function saveAccessModal() {
    const body = document.getElementById('obra360AccessBody');
    const save = document.getElementById('obra360AccessSave');
    if (!body || !save) return;
    const users = [...body.querySelectorAll('tbody tr[data-usstamp]')].map((row) => ({
      usstamp: row.dataset.usstamp,
      tabs: [...row.querySelectorAll('[data-access-tab]:checked:not(:disabled)')].map((input) => input.dataset.accessTab),
    }));
    save.disabled = true;
    try {
      const response = await fetch('/api/obra-360/acessos', {
        method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ users }),
      });
      const data = await response.json();
      if (!response.ok || !data.ok) throw new Error(data.error || 'Não foi possível gravar os acessos.');
      bootstrap.Modal.getInstance(document.getElementById('obra360AccessModal'))?.hide();
    } catch (error) {
      window.alert(error.message);
    } finally {
      save.disabled = false;
    }
  }

  document.getElementById('obra360AccessButton')?.addEventListener('click', openAccessModal);
  document.getElementById('obra360AccessSave')?.addEventListener('click', saveAccessModal);
  init().catch((error) => { document.getElementById('obra360Title').textContent = 'Não foi possível abrir a obra'; document.getElementById('obra360Subtitle').textContent = error.message; document.getElementById('obra360Header').innerHTML = `<div class="obra360-error">${esc(error.message)}</div>`; });
})();
