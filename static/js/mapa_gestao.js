// static/js/mapa_gestao.js

document.addEventListener('DOMContentLoaded', () => {
  const anoInput = document.getElementById('mapAno');
  const diffEnableEl = document.getElementById('mapDiffEnable');
  const diffPctEl = document.getElementById('mapDiffPct');
  const ccModalEl = document.getElementById('mapCcustoModal');
  const ccList = document.getElementById('mapCcList');
  const ccLabel = document.getElementById('mapCcustoLabel');
  const ccCount = document.getElementById('mapCcustoCount');
  const btnCcusto = document.getElementById('mapBtnCcusto');
  const btnCcAll = document.getElementById('mapCcAll');
  const btnCcNone = document.getElementById('mapCcNone');
  const btnCcEstrutura = document.getElementById('mapCcEstrutura');
  const btnCcExploracao = document.getElementById('mapCcExploracao');
  const btnCcGestao = document.getElementById('mapCcGestao');
  const btnCcApply = document.getElementById('mapCcApply');
  const btnAplicar = document.getElementById('mapBtnAplicar');
  const btnLimpar = document.getElementById('mapBtnLimpar');
  const btnExpandAll = document.getElementById('mapExpandAll');
  const btnCollapseAll = document.getElementById('mapCollapseAll');
  const detailModalEl = document.getElementById('mapDetailModal');
  const detailBody = document.getElementById('mapDetailBody');
  const detailTitle = document.getElementById('mapDetailTitle');
  const detailTotal = document.getElementById('mapDetailTotal');
  const detailModal = detailModalEl ? new bootstrap.Modal(detailModalEl) : null;
  const tbody = document.getElementById('mapaBody');
  const totalLbl = document.getElementById('mapTotal');
  const filtrosLbl = document.getElementById('mapFiltros');
  const defaultYear = window.MAPA_ANO_PADRAO || new Date().getFullYear();
  const modalCcusto = ccModalEl ? new bootstrap.Modal(ccModalEl) : null;
  let ccOptions = []; // [{ccusto, tipo}]
  let ccSelected = new Set();
  let lastRows = [];
  let treeExpanded = new Set(); // refs abertos (por defeito vazio: apenas nivel 1 visivel)
  let levelOneRefs = [];
  let allRefs = [];

  const fmtNum = new Intl.NumberFormat('pt-PT', { minimumFractionDigits: 0, maximumFractionDigits: 0, useGrouping: true });
  const fmtPct = new Intl.NumberFormat('pt-PT', { minimumFractionDigits: 1, maximumFractionDigits: 1, useGrouping: true });
  const fmtCur = new Intl.NumberFormat('pt-PT', { style: 'currency', currency: 'EUR', maximumFractionDigits: 0, useGrouping: true });
  const fmtNum2 = new Intl.NumberFormat('pt-PT', { minimumFractionDigits: 2, maximumFractionDigits: 2, useGrouping: true });
  const attrEscape = (str) => String(str == null ? '' : str).replace(/"/g, '&quot;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  const monthNames = ['Jan','Fev','Mar','Abr','Mai','Jun','Jul','Ago','Set','Out','Nov','Dez'];

  if (anoInput && !anoInput.value) {
    anoInput.value = defaultYear;
  }

  // evidenciar diferenças vs orçamento (persistência)
  const savedPct = localStorage.getItem('mapDiffPct');
  if (diffPctEl && savedPct != null && savedPct !== '') diffPctEl.value = savedPct;
  // Por defeito: não evidenciar (sem visto), independentemente de preferências anteriores
  if (diffEnableEl) diffEnableEl.checked = false;
  if (diffPctEl && (!diffPctEl.value || diffPctEl.value === '0')) diffPctEl.value = '3';

  function escapeHtml(str) {
    return String(str == null ? '' : str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function getSelectedCcustos() {
    return Array.from(ccSelected);
  }

  function isAllCentersSelected() {
    const selected = getSelectedCcustos();
    if (!ccOptions.length) return true;
    return selected.length === 0 || selected.length === ccOptions.length;
  }

  function updateDiffAvailability() {
    if (!diffEnableEl || !diffPctEl) return;
    const all = isAllCentersSelected();
    if (!all) diffEnableEl.checked = false;
    diffEnableEl.disabled = !all;
    diffPctEl.disabled = !all || !diffEnableEl.checked;
    const title = all ? '' : 'Disponível apenas com Todos os centros selecionados';
    diffEnableEl.title = title;
    diffPctEl.title = title;
  }

  function setLoading(message) {
    if (!tbody) return;
    tbody.innerHTML = `<tr><td colspan="15" class="text-center text-muted">${escapeHtml(message)}</td></tr>`;
  }

  function renderCcList() {
    if (!ccList) return;
    ccList.innerHTML = ccOptions.map((cc) => {
      const checked = ccSelected.has(cc.ccusto) ? 'checked' : '';
      const tipoNorm = (cc.tipo || '').trim().toUpperCase();
      let badge = '<span class="badge bg-secondary-subtle text-secondary ms-auto">Estrutura</span>';
      if (tipoNorm === 'EXPLORACAO') badge = '<span class="badge bg-info-subtle text-info ms-auto">Exploração</span>';
      else if (tipoNorm === 'GESTAO') badge = '<span class="badge bg-success-subtle text-success ms-auto">Gestão</span>';
      return `
        <label class="list-group-item d-flex align-items-center gap-2">
          <input class="form-check-input" type="checkbox" value="${cc.ccusto}" ${checked}>
          <span>${cc.ccusto}</span>
          ${badge}
        </label>
      `;
    }).join('') || '<div class="text-muted">Sem centros de custo.</div>';
    updateCcSummary();
  }

  function updateCcSummary() {
    const total = ccOptions.length;
    const sel = ccSelected.size;
    const label = !sel || sel === total ? 'Todos os centros' : `${sel} selecionado(s)`;
    if (ccLabel) ccLabel.textContent = label;
    if (ccCount) ccCount.textContent = `${sel || total} selecionados${sel ? '' : ' (todos)'}`;
    updateDiffAvailability();
  }

  async function loadCcustos() {
    setLoading('A carregar...');
    try {
      const res = await fetch('/api/mapa_gestao/ccustos');
      const data = await res.json();
      const optsRaw = Array.isArray(data.options)
        ? data.options
        : (data.options ? Object.values(data.options) : []);
      ccOptions = optsRaw.map(o => {
        if (typeof o === 'string') return { ccusto: o, tipo: '' };
        if (o && typeof o === 'object') {
          return { ccusto: o.ccusto || o.CCUSTO || o.Ccusto || '', tipo: o.tipo || o.TIPO || o.Tipo || '' };
        }
        return { ccusto: '', tipo: '' };
      }).filter(o => o.ccusto);
      ccSelected = new Set(ccOptions.map(o => o.ccusto)); // default = todos
      renderCcList();
      updateDiffAvailability();
    } catch (err) {
      console.error(err);
      ccOptions = [];
      ccSelected = new Set();
      if (ccList) ccList.innerHTML = '<div class="text-danger">Erro ao carregar centros de custo.</div>';
      setLoading('Erro ao carregar centros de custo');
      updateDiffAvailability();
    }
  }

  async function loadMapa() {
    setLoading('A carregar...');
    const ano = parseInt(anoInput?.value, 10) || defaultYear;
    const ccustos = getSelectedCcustos();
    const qs = new URLSearchParams({ ano: String(ano) });
    if (ccustos.length) qs.set('ccustos', ccustos.join(','));

    try {
      const res = await fetch(`/api/mapa_gestao?${qs.toString()}`);
      const data = await res.json();
      if (!res.ok || data.error) {
        throw new Error(data.error || 'Erro ao carregar o mapa');
      }
      const fams = Array.isArray(data.familias) ? data.familias : [];
      const normalized = fams.map(r => {
        const meses = Array.isArray(r.meses) ? r.meses.slice(0, 12) : [];
        while (meses.length < 12) meses.push(0);
        const orc_meses = Array.isArray(r.orc_meses) ? r.orc_meses.slice(0, 12) : [];
        while (orc_meses.length < 12) orc_meses.push(0);
        return { ...r, meses, orc_meses };
      });
      lastRows = normalized;
      levelOneRefs = lastRows.filter(r => Number(r.nivel || 1) === 1).map(r => String(r.ref || '').trim());
      allRefs = lastRows.map(r => String(r.ref || '').trim());
      treeExpanded = new Set(); // por defeito: apenas nivel 1 visivel; restantes fechados
      renderTabela();
    } catch (err) {
      console.error(err);
      setLoading(err.message || 'Erro ao carregar dados');
      if (totalLbl) totalLbl.textContent = '--';
      if (filtrosLbl) filtrosLbl.textContent = '';
    }
  }

  function renderTabela() {
    if (!tbody) return;
    if (!lastRows.length) {
      tbody.innerHTML = '<tr><td colspan="15" class="text-center text-muted">Sem dados para os filtros.</td></tr>';
      return;
    }

    // map ref->hasChildren
    const hasChild = {};
    lastRows.forEach(r => {
      const ref = String(r.ref || '');
      const parts = ref.split('.');
      if (parts.length > 1) {
        const parent = parts.slice(0, -1).join('.');
        hasChild[parent] = true;
      }
    });

    const isVisible = (ref) => {
      const parts = String(ref || '').split('.');
      if (parts.length === 1) return true;
      for (let i = 1; i < parts.length; i++) {
        const ancestor = parts.slice(0, i).join('.');
        if (!treeExpanded.has(ancestor)) return false;
      }
      return true;
    };

    const rowsHtml = lastRows
      .filter(r => isVisible(r.ref))
      .map(r => {
        const nivel = Number(r.nivel || 1);
        const ref = String(r.ref || '');
        const isProveito = ref.trim().startsWith('9');
        const diffEnabled = isAllCentersSelected() && !!diffEnableEl?.checked;
        const diffPct = Math.abs(Number(diffPctEl?.value || 3) || 3);
        const percVal = (r.percent === '' || r.percent == null) ? '' : `${fmtPct.format(Number(r.percent || 0))}%`;
        const mesesHtml = r.meses.map((v, idx) => {
          const mesNum = idx + 1;
          let diffClass = '';
          if (diffEnabled) {
            const bArr = Array.isArray(r.orc_meses) ? r.orc_meses : null;
            const budget = bArr ? Number(bArr[idx] || 0) : 0;
            const actual = Number(v || 0);
            if (budget > 0) {
              const pct = ((actual - budget) / budget) * 100;
              // Custos: acima orçamento = vermelho; abaixo = verde
              // Proveitos: abaixo objetivo = vermelho; acima = verde (inverso)
              if (!isProveito) {
                if (pct >= diffPct) diffClass = ' diff-over';
                else if (pct <= -diffPct) diffClass = ' diff-under';
              } else {
                if (pct >= diffPct) diffClass = ' diff-under';
                else if (pct <= -diffPct) diffClass = ' diff-over';
              }
            }
          }
          return `<td class="text-end cell-drill${diffClass}" data-level="${nivel}" data-ref="${attrEscape(ref)}" data-nome="${attrEscape(r.nome || '')}" data-mes="${mesNum}">${fmtNum.format(Number(v || 0))}</td>`;
        }).join('');
        let toggle = '<span class="toggle-spacer"></span>';
        if (nivel <= 2 && hasChild[ref]) {
          const isOpen = treeExpanded.has(ref);
          const icon = isOpen ? 'fa-minus' : 'fa-plus';
          toggle = `<button class="toggle-node" data-ref="${ref}" title="${isOpen ? 'Colapsar' : 'Expandir'}" aria-label="${isOpen ? 'Colapsar' : 'Expandir'}"><i class="fa-solid ${icon}"></i></button>`;
        }
        const rowClass = `mapa-row level-${nivel}${isProveito ? ' row-proveito' : ''}`;
        let totalDiffClass = '';
        if (diffEnabled) {
          const budgetTotal = Number(r.orc_total || 0);
          const actualTotal = Number(r.total || 0);
          if (budgetTotal > 0) {
            const pct = ((actualTotal - budgetTotal) / budgetTotal) * 100;
            if (!isProveito) {
              if (pct >= diffPct) totalDiffClass = ' diff-over';
              else if (pct <= -diffPct) totalDiffClass = ' diff-under';
            } else {
              if (pct >= diffPct) totalDiffClass = ' diff-under';
              else if (pct <= -diffPct) totalDiffClass = ' diff-over';
            }
          }
        }
        return `
          <tr class="${rowClass}" data-level="${nivel}">
            <td class="fam-cell level-${nivel} d-flex align-items-center gap-1">${toggle}<span>${escapeHtml(ref)} - ${escapeHtml(r.nome || '')}</span></td>
            ${mesesHtml}
            <td class="text-end fw-semibold cell-drill${totalDiffClass}" data-level="${nivel}" data-ref="${attrEscape(ref)}" data-nome="${attrEscape(r.nome || '')}" data-mes="all">${fmtNum.format(Number(r.total || 0))}</td>
            <td class="text-end text-muted">${percVal}</td>
          </tr>
        `;
      }).join('');

    // Totais (apenas nivel 1 para evitar duplicar somas dos pais/filhos)
    const custoMeses = Array(12).fill(0);
    const provMeses = Array(12).fill(0);
    let totalCustos = 0;
    let totalProv = 0;
    lastRows.filter(r => Number(r.nivel || 1) === 1).forEach(r => {
      const ref = String(r.ref || '').trim();
      const isProv = ref.startsWith('9');
      (r.meses || []).forEach((v, idx) => {
        if (isProv) provMeses[idx] += Number(v || 0);
        else custoMeses[idx] += Number(v || 0);
      });
      if (isProv) totalProv += Number(r.total || 0);
      else totalCustos += Number(r.total || 0);
    });
    const saldoMeses = custoMeses.map((c, i) => provMeses[i] - c);
    const totalSaldo = totalProv - totalCustos;
    const rowResumo = (label, arr, total, extraClass='') => `
      <tr class="mapa-row total-row ${extraClass}">
        <td class="fam-cell level-1 d-flex align-items-center gap-1"><span class="fw-semibold">${label}</span></td>
        ${arr.map(v => `<td class="text-end fw-semibold">${fmtNum.format(v)}</td>`).join('')}
        <td class="text-end fw-semibold">${fmtNum.format(total)}</td>
        <td class="text-end text-muted fw-semibold"></td>
      </tr>
    `;
    const totalRowHtml = [
      rowResumo('Custos', custoMeses, totalCustos, 'total-custos'),
      rowResumo('Proveitos', provMeses, totalProv, 'total-proveitos'),
      rowResumo('Saldo', saldoMeses, totalSaldo, 'total-saldo')
    ].join('');

    tbody.innerHTML = rowsHtml
      ? rowsHtml + totalRowHtml
      : '<tr><td colspan="15" class="text-center text-muted">Sem dados visíveis.</td></tr>';

    tbody.querySelectorAll('.toggle-node').forEach(btn => {
      btn.addEventListener('click', () => {
        const ref = btn.dataset.ref;
        if (!ref) return;
        if (treeExpanded.has(ref)) treeExpanded.delete(ref); else treeExpanded.add(ref);
        renderTabela();
      });
    });
    tbody.querySelectorAll('.cell-drill').forEach(td => {
      td.addEventListener('click', () => {
        const ref = td.dataset.ref || '';
        const nome = td.dataset.nome || '';
        const mes = td.dataset.mes || '';
        const level = Number(td.dataset.level || '1');
        openDetalhe(ref, mes, nome, level);
      });
    });
  }

  function resolveDescendants(ref) {
    const prefix = ref ? ref + '.' : '';
    return lastRows
      .map(r => String(r.ref || ''))
      .filter(r => r.startsWith(prefix));
  }

  async function openDetalhe(ref, mes, nome, level) {
    if (!detailBody || !detailModal) return;
    const ano = parseInt(anoInput?.value, 10) || defaultYear;
    const ccustos = getSelectedCcustos();
    const qs = new URLSearchParams({ ano: String(ano), familia: ref });
    if (mes && mes !== 'all') qs.set('mes', mes);
    if (ccustos.length) qs.set('ccustos', ccustos.join(','));
    if (level <= 2) qs.set('include_children', '1');

    detailBody.innerHTML = `<tr><td colspan="11" class="text-center text-muted">A carregar...</td></tr>`;
    const mesLabel = mes && mes !== 'all' ? `(${monthNames[(Number(mes) - 1) || 0] || ''})` : '';
    if (detailTitle) detailTitle.textContent = `Detalhe ${ref} ${nome ? '- ' + nome : ''} ${mesLabel}`.trim();
    if (detailTotal) detailTotal.textContent = 'Total: --';
    detailModal.show();

    try {
      const res = await fetch(`/api/mapa_gestao/detalhe?${qs.toString()}`);
      const data = await res.json();
      if (!res.ok || data.error) throw new Error(data.error || 'Erro ao carregar detalhe');
      const rows = Array.isArray(data.rows) ? data.rows : [];
      if (!rows.length) {
        detailBody.innerHTML = '<tr><td colspan="11" class="text-center text-muted">Sem registos.</td></tr>';
      } else {
        detailBody.innerHTML = rows.map(r => {
          const url = r.anexo_url || '';
          const btn = url ? `<a class="btn btn-outline-primary btn-sm" target="_blank" href="${escapeHtml(url)}">Abrir</a>` : '';
          return `
          <tr>
            <td>${escapeHtml(r.documento || '')}</td>
            <td>${escapeHtml(r.numero || '')}</td>
            <td>${escapeHtml(r.data || '')}</td>
            <td>${escapeHtml(r.nome || '')}</td>
            <td>${escapeHtml(r.ccusto || '')}</td>
            <td>${escapeHtml(r.referencia || '')}</td>
            <td>${escapeHtml(r.designacao || '')}</td>
            <td class="text-end">${fmtNum2.format(Number(r.quantidade || 0))}</td>
            <td class="text-end">${fmtNum2.format(Number(r.preco || 0))}</td>
            <td class="text-end fw-semibold">${fmtNum2.format(Number(r.total || 0))}</td>
            <td class="text-center">${btn}</td>
          </tr>
        `;
        }).join('');
      }
      if (detailTotal) {
        const total = Number(data.total || 0);
        const orc = Number(data.orc_total || 0);
        const desvio = Number(data.desvio || 0);
        const pct = data.desvio_pct == null ? null : Number(data.desvio_pct || 0);
        if (orc > 0) {
          const isProveito = String(ref || '').trim().startsWith('9');
          const cls = !isProveito
            ? (desvio > 0 ? 'text-danger' : (desvio < 0 ? 'text-success' : 'text-muted'))
            : (desvio > 0 ? 'text-success' : (desvio < 0 ? 'text-danger' : 'text-muted'));
          const pctTxt = pct == null ? '' : ` (${fmtPct.format(pct)}%)`;
          detailTotal.innerHTML = `
            <span class="fw-bold">Total: ${fmtNum2.format(total)}</span>
            <span class="text-muted small ms-2">Orçamento: ${fmtNum2.format(orc)}</span>
            <span class="text-muted small ms-2">Desvio: <span class="${cls} opacity-75">${fmtNum2.format(desvio)}${pctTxt}</span></span>
          `.trim();
        } else {
          detailTotal.innerHTML = `<span class="fw-bold">Total: ${fmtNum2.format(total)}</span>`;
        }
      }
    } catch (err) {
      console.error(err);
      detailBody.innerHTML = `<tr><td colspan="10" class="text-center text-danger">${escapeHtml(err.message || 'Erro ao carregar detalhe')}</td></tr>`;
      if (detailTotal) detailTotal.textContent = 'Total: --';
    }
  }

  if (btnAplicar) btnAplicar.addEventListener('click', loadMapa);
  diffEnableEl?.addEventListener('change', () => {
    updateDiffAvailability();
    renderTabela();
  });
  diffPctEl?.addEventListener('change', () => {
    localStorage.setItem('mapDiffPct', diffPctEl.value || '3');
    renderTabela();
  });
  diffPctEl?.addEventListener('input', () => {
    // live update, but avoid spamming storage
    renderTabela();
  });
  if (btnLimpar) btnLimpar.addEventListener('click', () => {
    ccSelected = new Set(ccOptions.map(o => o.ccusto)); // todos
    if (anoInput) anoInput.value = defaultYear;
    updateCcSummary();
    renderCcList();
    loadMapa();
  });

  if (btnCcusto && modalCcusto) btnCcusto.addEventListener('click', () => modalCcusto.show());
  if (btnCcAll) btnCcAll.addEventListener('click', () => {
    ccSelected = new Set(ccOptions.map(o => o.ccusto));
    renderCcList();
  });
  if (btnCcNone) btnCcNone.addEventListener('click', () => {
    ccSelected = new Set();
    renderCcList();
  });
  if (btnCcApply && modalCcusto) btnCcApply.addEventListener('click', () => {
    if (ccList) {
      ccSelected = new Set(
        Array.from(ccList.querySelectorAll('input[type="checkbox"]:checked')).map(i => i.value)
      );
    }
    updateCcSummary();
    modalCcusto.hide();
    loadMapa();
  });
  if (btnCcEstrutura) btnCcEstrutura.addEventListener('click', () => {
    const filtered = ccOptions.filter(o => !(o.tipo || '').trim());
    ccSelected = new Set(filtered.map(o => o.ccusto));
    renderCcList();
  });
  if (btnCcExploracao) btnCcExploracao.addEventListener('click', () => {
    const filtered = ccOptions.filter(o => (o.tipo || '').trim().toUpperCase() === 'EXPLORACAO');
    ccSelected = new Set(filtered.map(o => o.ccusto));
    renderCcList();
  });
  if (btnCcGestao) btnCcGestao.addEventListener('click', () => {
    const filtered = ccOptions.filter(o => (o.tipo || '').trim().toUpperCase() === 'GESTAO');
    ccSelected = new Set(filtered.map(o => o.ccusto));
    renderCcList();
  });
  if (btnExpandAll) btnExpandAll.addEventListener('click', () => {
    treeExpanded = new Set(allRefs);
    renderTabela();
  });
  if (btnCollapseAll) btnCollapseAll.addEventListener('click', () => {
    treeExpanded = new Set(); // apenas nivel 1 visivel
    renderTabela();
  });

  loadCcustos().then(loadMapa).catch(err => console.error(err));
});
