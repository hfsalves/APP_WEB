// static/js/mapa_controlo.js

document.addEventListener('DOMContentLoaded', () => {
  const anoInput = document.getElementById('mcAno');
  const mesSelect = document.getElementById('mcMes');
  const btnAplicar = document.getElementById('mcBtnAplicar');
  const btnHoje = document.getElementById('mcBtnHoje');
  const tbody = document.getElementById('mcBody');
  const totalsRow = document.getElementById('mcTotalsRow');

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

  function moneyCell(value, isSaldo = false) {
    const num = Number(value || 0);
    let cls = '';
    if (num === 0) {
      cls = 'mc-zero';
    } else if (isSaldo) {
      cls = num < 0 ? 'mc-negative' : (num > 0 ? 'mc-positive' : '');
    }
    return `<td class="text-end ${cls}">${fmtNum2.format(num)}</td>`;
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
            ${moneyCell(r.proveito)}
            ${moneyCell(r.rendas)}
            ${moneyCell(r.luz)}
            ${moneyCell(r.agua)}
            ${moneyCell(r.comunicacoes)}
            ${moneyCell(r.outros)}
            ${moneyCell(r.total_custos)}
            ${moneyCell(r.saldo, true)}
          </tr>
        `).join('');
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
