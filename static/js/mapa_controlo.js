// static/js/mapa_controlo.js

document.addEventListener('DOMContentLoaded', () => {
  const anoInput = document.getElementById('mcAno');
  const mesSelect = document.getElementById('mcMes');
  const btnAplicar = document.getElementById('mcBtnAplicar');
  const btnHoje = document.getElementById('mcBtnHoje');
  const tbody = document.getElementById('mcBody');
  const totalsRow = document.getElementById('mcTotalsRow');
  const detailModalEl = document.getElementById('mcDetailModal');
  const detailModal = detailModalEl && window.bootstrap?.Modal ? new window.bootstrap.Modal(detailModalEl) : null;
  const detailTitle = document.getElementById('mcDetailTitle');
  const detailBody = document.getElementById('mcDetailBody');
  const detailTotal = document.getElementById('mcDetailTotal');

  const defaultYear = window.MC_ANO_PADRAO || new Date().getFullYear();
  const defaultMonth = window.MC_MES_PADRAO || (new Date().getMonth() + 1);

  const fmtNum2 = new Intl.NumberFormat('pt-PT', { minimumFractionDigits: 2, maximumFractionDigits: 2, useGrouping: true });
  const escapeHtml = (str) => String(str == null ? '' : str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');

  if (anoInput && !anoInput.value) anoInput.value = defaultYear;
  if (mesSelect) mesSelect.value = String(defaultMonth);

  function setLoading(message) {
    if (!tbody) return;
    tbody.innerHTML = `<tr><td colspan="9" class="text-center text-muted">${escapeHtml(message)}</td></tr>`;
  }

  const groupLabels = {
    proveito: 'Proveito',
    rendas: 'Rendas',
    luz: 'Luz',
    agua: 'Água',
    comunicacoes: 'Comunicações',
    outros: 'Outros',
    total_custos: 'Total',
    saldo: 'Saldo',
  };

  function moneyCell(value, isSaldo = false, ccusto = '', group = '') {
    const num = Number(value || 0);
    let cls = '';
    if (num === 0) {
      cls = 'mc-zero';
    } else if (isSaldo) {
      cls = num < 0 ? 'mc-negative' : (num > 0 ? 'mc-positive' : '');
    }
    const attrs = ccusto && group
      ? ` data-ccusto="${escapeHtml(ccusto)}" data-grupo="${escapeHtml(group)}"`
      : '';
    const clickCls = ccusto && group ? ' mc-cell-drill' : '';
    return `<td class="text-end ${cls}${clickCls}"${attrs}>${fmtNum2.format(num)}</td>`;
  }

  function renderTotals(totals) {
    if (!totalsRow) return;
    const cells = totalsRow.querySelectorAll('th,td');
    if (!cells || cells.length < 9) return;
    const setVal = (cell, val, isSaldo = false) => {
      const num = Number(val || 0);
      cell.textContent = fmtNum2.format(num);
      cell.classList.toggle('mc-zero', num === 0);
      if (isSaldo && num !== 0) {
        cell.classList.toggle('mc-negative', num < 0);
        cell.classList.toggle('mc-positive', num > 0);
      } else {
        cell.classList.remove('mc-negative', 'mc-positive');
      }
    };
    cells[0].textContent = totals?.ccusto || 'TOTAL';
    setVal(cells[1], totals?.proveito);
    setVal(cells[2], totals?.rendas);
    setVal(cells[3], totals?.luz);
    setVal(cells[4], totals?.agua);
    setVal(cells[5], totals?.comunicacoes);
    setVal(cells[6], totals?.outros);
    setVal(cells[7], totals?.total_custos);
    setVal(cells[8], totals?.saldo, true);
  }

  async function openDetalhe(ccusto, grupo) {
    if (!detailModal || !detailBody) return;
    const ano = parseInt(anoInput?.value, 10) || defaultYear;
    const mes = parseInt(mesSelect?.value, 10) || defaultMonth;
    const qs = new URLSearchParams({
      ano: String(ano),
      mes: String(mes),
      ccusto: String(ccusto || ''),
      grupo: String(grupo || ''),
    });

    detailBody.innerHTML = `<tr><td colspan="12" class="text-center text-muted">A carregar...</td></tr>`;
    if (detailTitle) detailTitle.textContent = `Detalhe ${ccusto} - ${groupLabels[grupo] || grupo}`;
    if (detailTotal) detailTotal.textContent = 'Total: --';
    detailModal.show();

    try {
      const res = await fetch(`/api/mapa_controlo/detalhe?${qs.toString()}`);
      const data = await res.json().catch(() => ({}));
      if (!res.ok || data.error) throw new Error(data.error || 'Erro ao carregar detalhe');
      const rows = Array.isArray(data.rows) ? data.rows : [];
      if (!rows.length) {
        detailBody.innerHTML = '<tr><td colspan="12" class="text-center text-muted">Sem registos.</td></tr>';
      } else {
        detailBody.innerHTML = rows.map((r) => {
          const url = r.anexo_url || '';
          const btn = url ? `<a class="btn btn-outline-primary btn-sm" target="_blank" href="${escapeHtml(url)}">Abrir</a>` : '';
          return `
            <tr>
              <td>${escapeHtml(r.documento || '')}</td>
              <td>${escapeHtml(r.numero || '')}</td>
              <td>${escapeHtml(r.data || '')}</td>
              <td>${escapeHtml(r.nome || '')}</td>
              <td>${escapeHtml(r.ccusto || '')}</td>
              <td>${escapeHtml(r.familia || '')}</td>
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
      detailBody.innerHTML = `<tr><td colspan="12" class="text-center text-danger">${escapeHtml(err.message || 'Erro ao carregar detalhe')}</td></tr>`;
      if (detailTotal) detailTotal.textContent = 'Total: --';
    }
  }

  async function loadMapa() {
    const ano = parseInt(anoInput?.value, 10) || defaultYear;
    const mes = parseInt(mesSelect?.value, 10) || defaultMonth;
    setLoading('A carregar...');
    try {
      const qs = new URLSearchParams({ ano: String(ano), mes: String(mes) });
      const res = await fetch(`/api/mapa_controlo?${qs.toString()}`);
      const data = await res.json().catch(() => ({}));
      if (!res.ok || data.error) throw new Error(data.error || res.statusText);
      const rows = Array.isArray(data.rows) ? data.rows : [];
      if (!rows.length) {
        tbody.innerHTML = `<tr><td colspan="9" class="text-center text-muted">Sem registos.</td></tr>`;
      } else {
        tbody.innerHTML = rows.map(r => `
          <tr>
            <td>${escapeHtml(r.ccusto || '')}</td>
            ${moneyCell(r.proveito, false, r.ccusto, 'proveito')}
            ${moneyCell(r.rendas, false, r.ccusto, 'rendas')}
            ${moneyCell(r.luz, false, r.ccusto, 'luz')}
            ${moneyCell(r.agua, false, r.ccusto, 'agua')}
            ${moneyCell(r.comunicacoes, false, r.ccusto, 'comunicacoes')}
            ${moneyCell(r.outros, false, r.ccusto, 'outros')}
            ${moneyCell(r.total_custos, false, r.ccusto, 'total_custos')}
            ${moneyCell(r.saldo, true, r.ccusto, 'saldo')}
          </tr>
        `).join('');
        tbody.querySelectorAll('[data-ccusto][data-grupo]').forEach((cell) => {
          cell.addEventListener('click', () => {
            openDetalhe(cell.dataset.ccusto || '', cell.dataset.grupo || '');
          });
        });
      }
      renderTotals(data.totals || {});
    } catch (err) {
      console.error(err);
      tbody.innerHTML = `<tr><td colspan="9" class="text-center text-danger">${escapeHtml(err.message || 'Erro')}</td></tr>`;
      renderTotals({});
    }
  }

  btnAplicar?.addEventListener('click', loadMapa);
  btnHoje?.addEventListener('click', () => {
    if (anoInput) anoInput.value = defaultYear;
    if (mesSelect) mesSelect.value = String(defaultMonth);
    loadMapa();
  });

  loadMapa();
});
