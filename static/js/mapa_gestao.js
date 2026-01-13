// static/js/mapa_gestao.js

document.addEventListener('DOMContentLoaded', () => {
  const anoInput = document.getElementById('mapAno');
  const ccModalEl = document.getElementById('mapCcustoModal');
  const ccList = document.getElementById('mapCcList');
  const ccLabel = document.getElementById('mapCcustoLabel');
  const ccCount = document.getElementById('mapCcustoCount');
  const btnCcusto = document.getElementById('mapBtnCcusto');
  const btnCcAll = document.getElementById('mapCcAll');
  const btnCcNone = document.getElementById('mapCcNone');
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
  let ccOptions = [];
  let ccSelected = new Set();
  let lastRows = [];
  let treeExpanded = new Set(); // refs abertos (por defeito vazio: apenas nivel 1 visivel)
  let levelOneRefs = [];
  let allRefs = [];

  const fmtNum = new Intl.NumberFormat('pt-PT', { minimumFractionDigits: 0, maximumFractionDigits: 0 });
  const fmtPct = new Intl.NumberFormat('pt-PT', { minimumFractionDigits: 1, maximumFractionDigits: 1 });
  const fmtCur = new Intl.NumberFormat('pt-PT', { style: 'currency', currency: 'EUR', maximumFractionDigits: 0 });
  const fmtNum2 = new Intl.NumberFormat('pt-PT', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  const attrEscape = (str) => String(str == null ? '' : str).replace(/"/g, '&quot;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  const monthNames = ['Jan','Fev','Mar','Abr','Mai','Jun','Jul','Ago','Set','Out','Nov','Dez'];

  if (anoInput && !anoInput.value) {
    anoInput.value = defaultYear;
  }

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

  function setLoading(message) {
    if (!tbody) return;
    tbody.innerHTML = `<tr><td colspan="15" class="text-center text-muted">${escapeHtml(message)}</td></tr>`;
  }

  function renderCcList() {
    if (!ccList) return;
    ccList.innerHTML = ccOptions.map((cc) => {
      const checked = ccSelected.has(cc) ? 'checked' : '';
      return `
        <label class="list-group-item d-flex align-items-center gap-2">
          <input class="form-check-input" type="checkbox" value="${cc}" ${checked}>
          <span>${cc}</span>
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
  }

  async function loadCcustos() {
    setLoading('A carregar...');
    try {
      const res = await fetch('/api/mapa_gestao/ccustos');
      const data = await res.json();
      ccOptions = Array.isArray(data.options) ? data.options : [];
      ccSelected = new Set(ccOptions); // default = todos
      renderCcList();
    } catch (err) {
      console.error(err);
      ccOptions = [];
      ccSelected = new Set();
      if (ccList) ccList.innerHTML = '<div class="text-danger">Erro ao carregar centros de custo.</div>';
      setLoading('Erro ao carregar centros de custo');
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
        return { ...r, meses };
      });
      lastRows = normalized;
      levelOneRefs = lastRows.filter(r => Number(r.nivel || 1) === 1).map(r => String(r.ref || '').trim());
      allRefs = lastRows.map(r => String(r.ref || '').trim());
      treeExpanded = new Set(levelOneRefs); // por defeito: niveis 1 abertos (mostra nivel 2)
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
        const mesesHtml = r.meses.map((v, idx) => {
          const mesNum = idx + 1;
          return `<td class="text-end cell-drill" data-level="${nivel}" data-ref="${attrEscape(ref)}" data-nome="${attrEscape(r.nome || '')}" data-mes="${mesNum}">${fmtNum.format(Number(v || 0))}</td>`;
        }).join('');
        let toggle = '<span class="toggle-spacer"></span>';
        if (nivel <= 2 && hasChild[ref]) {
          const isOpen = treeExpanded.has(ref);
          const icon = isOpen ? 'fa-minus' : 'fa-plus';
          toggle = `<button class="toggle-node" data-ref="${ref}" title="${isOpen ? 'Colapsar' : 'Expandir'}" aria-label="${isOpen ? 'Colapsar' : 'Expandir'}"><i class="fa-solid ${icon}"></i></button>`;
        }
        const rowClass = `mapa-row level-${nivel}${isProveito ? ' row-proveito' : ''}`;
        return `
          <tr class="${rowClass}" data-level="${nivel}">
            <td class="fam-cell level-${nivel} d-flex align-items-center gap-1">${toggle}<span>${escapeHtml(ref)} - ${escapeHtml(r.nome || '')}</span></td>
            ${mesesHtml}
            <td class="text-end fw-semibold cell-drill" data-level="${nivel}" data-ref="${attrEscape(ref)}" data-nome="${attrEscape(r.nome || '')}" data-mes="all">${fmtNum.format(Number(r.total || 0))}</td>
            <td class="text-end text-muted">${fmtPct.format(Number(r.percent || 0))}%</td>
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
    const totalMeses = custoMeses.map((c, i) => provMeses[i] - c);
    const totalGeral = totalProv - totalCustos;
    const totalRowHtml = `
      <tr class="mapa-row total-row">
        <td class="fam-cell level-1 d-flex align-items-center gap-1"><span class="fw-semibold">Total</span></td>
        ${totalMeses.map(v => `<td class="text-end fw-semibold">${fmtNum.format(v)}</td>`).join('')}
        <td class="text-end fw-semibold">${fmtNum.format(totalGeral)}</td>
        <td class="text-end text-muted fw-semibold">--</td>
      </tr>
    `;

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
      if (detailTotal) detailTotal.textContent = `Total: ${fmtNum2.format(Number(data.total || 0))}`;
    } catch (err) {
      console.error(err);
      detailBody.innerHTML = `<tr><td colspan="10" class="text-center text-danger">${escapeHtml(err.message || 'Erro ao carregar detalhe')}</td></tr>`;
      if (detailTotal) detailTotal.textContent = 'Total: --';
    }
  }

  if (btnAplicar) btnAplicar.addEventListener('click', loadMapa);
  if (btnLimpar) btnLimpar.addEventListener('click', () => {
    ccSelected = new Set(ccOptions); // todos
    if (anoInput) anoInput.value = defaultYear;
    updateCcSummary();
    renderCcList();
    loadMapa();
  });

  if (btnCcusto && modalCcusto) btnCcusto.addEventListener('click', () => modalCcusto.show());
  if (btnCcAll) btnCcAll.addEventListener('click', () => {
    ccSelected = new Set(ccOptions);
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
