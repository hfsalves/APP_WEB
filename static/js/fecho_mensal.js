document.addEventListener('DOMContentLoaded', () => {
  const els = {
    ano: document.getElementById('fechoAno'),
    mes: document.getElementById('fechoMes'),
    prev: document.getElementById('fechoPrev'),
    next: document.getElementById('fechoNext'),
    reload: document.getElementById('fechoReload'),
    export: document.getElementById('fechoExport'),
    body: document.getElementById('fechoBody'),
    totals: document.getElementById('fechoTotals'),
    impSede: document.getElementById('btnImpSede'),
    impLav: document.getElementById('btnImpLav'),
    impLimp: document.getElementById('btnImpLimp'),
    impHelp: document.getElementById('btnImpHelp'),
    delImpMes: document.getElementById('btnDelImpMes')
  };

  let state = {
    ano: Number(window.FECHO_ANO_INICIAL || new Date().getFullYear()),
    mes: Number(window.FECHO_MES_INICIAL || (new Date().getMonth() + 1)),
    rows: [],
    totals: null,
    expanded: {
      EXPLORACAO: false,
      GESTAO: false
    },
    imputStatus: {}
  };

  const fmt = (n) => {
    const v = Number(n || 0);
    return v.toLocaleString('pt-PT', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  };
  const saldoValue = (n) => -Number(n || 0);
  const fmtSaldo = (n) => fmt(saldoValue(n));
  const saldoClass = (n) => (saldoValue(n) < 0 ? 'fecho-neg' : '');
  const fmtCsvNum = (n) => Number(n || 0).toFixed(2).replace('.', ',');

  const currentYearMonth = () => ({
    ano: Number(els.ano.value || state.ano || new Date().getFullYear()),
    mes: Number(els.mes.value || state.mes || (new Date().getMonth() + 1))
  });

  const applyYearMonth = () => {
    els.ano.value = state.ano;
    els.mes.value = String(state.mes);
  };

  function calcGroupTotals(rows) {
    return rows.reduce((acc, r) => {
      acc.LIMPEZAS += Number(r.LIMPEZAS || 0);
      acc.F1 += Number(r.F1 || 0);
      acc.F2 += Number(r.F2 || 0);
      acc.F3 += Number(r.F3 || 0);
      acc.F4 += Number(r.F4 || 0);
      acc.F9 += Number(r.F9 || 0);
      acc.TOTAL_MES += Number(r.TOTAL_MES || 0);
      return acc;
    }, { LIMPEZAS: 0, F1: 0, F2: 0, F3: 0, F4: 0, F9: 0, TOTAL_MES: 0 });
  }

  function renderTotals() {
    const t = state.totals || { F1: 0, F2: 0, F3: 0, F4: 0, F9: 0, TOTAL_MES: 0 };
    els.totals.innerHTML = `
      <td></td>
      <td></td>
      <td></td>
      <td class="text-end">${fmt(t.F1)}</td>
      <td class="text-end">${fmt(t.F2)}</td>
      <td class="text-end">${fmt(t.F3)}</td>
      <td class="text-end">${fmt(t.F4)}</td>
      <td class="text-end fecho-col-proveitos">${fmt(t.F9)}</td>
      <td class="text-end fecho-col-total ${saldoClass(t.TOTAL_MES)}">${fmtSaldo(t.TOTAL_MES)}</td>
    `;
  }

  function rowHtml(r, cls = '') {
    return `
      <tr class="${cls}">
        <td>${r.CCUSTO || ''}</td>
        <td>${r.TIPOLOGIA || ''}</td>
        <td class="text-end">${Number(r.LIMPEZAS || 0)}</td>
        <td class="text-end">${fmt(r.F1)}</td>
        <td class="text-end">${fmt(r.F2)}</td>
        <td class="text-end">${fmt(r.F3)}</td>
        <td class="text-end">${fmt(r.F4)}</td>
        <td class="text-end fecho-col-proveitos">${fmt(r.F9)}</td>
        <td class="text-end fecho-col-total ${saldoClass(r.TOTAL_MES)}">${fmtSaldo(r.TOTAL_MES)}</td>
      </tr>
    `;
  }

  function render() {
    const rows = Array.isArray(state.rows) ? state.rows : [];
    if (!rows.length) {
      els.body.innerHTML = '<tr><td colspan="9" class="text-muted p-3">Sem dados para o mês selecionado.</td></tr>';
      renderTotals();
      return;
    }

    const groupedMode = true;
    const alojExpl = rows.filter(r => (r.TIPO || '').toUpperCase() === 'EXPLORACAO');
    const alojGest = rows.filter(r => (r.TIPO || '').toUpperCase() === 'GESTAO');
    const others = rows.filter(r => !['EXPLORACAO', 'GESTAO'].includes((r.TIPO || '').toUpperCase()));

    let html = '';
    if (groupedMode) {
      const explTot = calcGroupTotals(alojExpl);
      const gestTot = calcGroupTotals(alojGest);
      html += others.map(r => rowHtml(r)).join('');
      if (alojExpl.length) {
        html += `
          <tr class="fecho-group" data-group="EXPLORACAO">
            <td><button type="button" class="btn btn-sm fecho-expand-btn">${state.expanded.EXPLORACAO ? '−' : '+'}</button>ALOJAMENTOS - EXPLORACAO</td>
            <td></td>
            <td class="text-end">${Number(explTot.LIMPEZAS || 0)}</td>
            <td class="text-end">${fmt(explTot.F1)}</td>
            <td class="text-end">${fmt(explTot.F2)}</td>
            <td class="text-end">${fmt(explTot.F3)}</td>
            <td class="text-end">${fmt(explTot.F4)}</td>
            <td class="text-end fecho-col-proveitos">${fmt(explTot.F9)}</td>
            <td class="text-end fecho-col-total ${saldoClass(explTot.TOTAL_MES)}">${fmtSaldo(explTot.TOTAL_MES)}</td>
          </tr>`;
        if (state.expanded.EXPLORACAO) {
          html += alojExpl.map(r => rowHtml(r, 'fecho-child')).join('');
        }
      }
      if (alojGest.length) {
        html += `
          <tr class="fecho-group" data-group="GESTAO">
            <td><button type="button" class="btn btn-sm fecho-expand-btn">${state.expanded.GESTAO ? '−' : '+'}</button>ALOJAMENTOS - GESTAO</td>
            <td></td>
            <td class="text-end">${Number(gestTot.LIMPEZAS || 0)}</td>
            <td class="text-end">${fmt(gestTot.F1)}</td>
            <td class="text-end">${fmt(gestTot.F2)}</td>
            <td class="text-end">${fmt(gestTot.F3)}</td>
            <td class="text-end">${fmt(gestTot.F4)}</td>
            <td class="text-end fecho-col-proveitos">${fmt(gestTot.F9)}</td>
            <td class="text-end fecho-col-total ${saldoClass(gestTot.TOTAL_MES)}">${fmtSaldo(gestTot.TOTAL_MES)}</td>
          </tr>`;
        if (state.expanded.GESTAO) {
          html += alojGest.map(r => rowHtml(r, 'fecho-child')).join('');
        }
      }
    } else {
      html = rows.map(r => rowHtml(r)).join('');
    }

    els.body.innerHTML = html;
    renderTotals();

    els.body.querySelectorAll('tr.fecho-group').forEach(tr => {
      tr.addEventListener('click', () => {
        const g = tr.getAttribute('data-group');
        if (!g) return;
        state.expanded[g] = !state.expanded[g];
        render();
      });
    });
  }

  function buildExportRows() {
    const rows = Array.isArray(state.rows) ? state.rows : [];
    const groupedMode = true;
    const alojExpl = rows.filter(r => (r.TIPO || '').toUpperCase() === 'EXPLORACAO');
    const alojGest = rows.filter(r => (r.TIPO || '').toUpperCase() === 'GESTAO');
    const others = rows.filter(r => !['EXPLORACAO', 'GESTAO'].includes((r.TIPO || '').toUpperCase()));
    const out = [];
    const pushRow = (r) => {
      out.push([
        r.CCUSTO || '',
        r.TIPOLOGIA || '',
        Number(r.LIMPEZAS || 0),
        fmtCsvNum(r.F1),
        fmtCsvNum(r.F2),
        fmtCsvNum(r.F3),
        fmtCsvNum(r.F4),
        fmtCsvNum(r.F9),
        fmtCsvNum(saldoValue(r.TOTAL_MES))
      ]);
    };

    if (groupedMode) {
      const explTot = calcGroupTotals(alojExpl);
      const gestTot = calcGroupTotals(alojGest);
      others.forEach(pushRow);
      if (alojExpl.length) {
        out.push([
          'ALOJAMENTOS - EXPLORACAO', '', Number(explTot.LIMPEZAS || 0),
          fmtCsvNum(explTot.F1), fmtCsvNum(explTot.F2), fmtCsvNum(explTot.F3), fmtCsvNum(explTot.F4), fmtCsvNum(explTot.F9), fmtCsvNum(saldoValue(explTot.TOTAL_MES))
        ]);
        alojExpl.forEach(pushRow);
      }
      if (alojGest.length) {
        out.push([
          'ALOJAMENTOS - GESTAO', '', Number(gestTot.LIMPEZAS || 0),
          fmtCsvNum(gestTot.F1), fmtCsvNum(gestTot.F2), fmtCsvNum(gestTot.F3), fmtCsvNum(gestTot.F4), fmtCsvNum(gestTot.F9), fmtCsvNum(saldoValue(gestTot.TOTAL_MES))
        ]);
        alojGest.forEach(pushRow);
      }
    } else {
      rows.forEach(pushRow);
    }
    return out;
  }

  function exportCsv() {
    const fam1 = document.getElementById('fechoFam1')?.textContent?.trim() || 'Fam. 1';
    const fam2 = document.getElementById('fechoFam2')?.textContent?.trim() || 'Fam. 2';
    const fam3 = document.getElementById('fechoFam3')?.textContent?.trim() || 'Fam. 3';
    const fam4 = document.getElementById('fechoFam4')?.textContent?.trim() || 'Fam. 4';
    const fam9 = document.getElementById('fechoFam9')?.textContent?.trim() || 'Fam. 9';
    const lines = [];
    lines.push(['Centro de Custo', 'Tipologia', 'Limpezas', fam1, fam2, fam3, fam4, fam9, 'Saldo Mensal']);
    buildExportRows().forEach(r => lines.push(r));
    const t = state.totals || { F1: 0, F2: 0, F3: 0, F4: 0, F9: 0, TOTAL_MES: 0 };
    lines.push(['', '', '', fmtCsvNum(t.F1), fmtCsvNum(t.F2), fmtCsvNum(t.F3), fmtCsvNum(t.F4), fmtCsvNum(t.F9), fmtCsvNum(saldoValue(t.TOTAL_MES))]);

    const esc = (v) => `"${String(v ?? '').replace(/"/g, '""')}"`;
    const csv = '\ufeff' + lines.map(row => row.map(esc).join(';')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    const mm = String(state.mes).padStart(2, '0');
    a.href = url;
    a.download = `fecho_mensal_${state.ano}_${mm}.csv`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  }

  function applyImputButtonsStatus() {
    const status = state.imputStatus || {};
    const cfg = [
      { el: els.impSede, key: 'SEDE', label: 'SEDE' },
      { el: els.impLimp, key: 'LIMPEZA', label: 'LIMPEZA' },
      { el: els.impLav, key: 'LAVANDARIA', label: 'LAVANDARIA' },
      { el: els.impHelp, key: 'HELPDESK', label: 'HELPDESK' }
    ];
    cfg.forEach(({ el, key, label }) => {
      if (!el) return;
      const done = !!status[key];
      el.classList.toggle('done', done);
      el.innerHTML = done ? `<i class="fa-solid fa-check me-1"></i>${label}` : label;
      el.title = done ? 'Imputação já gerada para o mês' : '';
    });
  }

  async function load() {
    const { ano, mes } = currentYearMonth();
    state.ano = ano;
    state.mes = mes;
    applyYearMonth();
    els.body.innerHTML = '<tr><td colspan="9" class="text-muted p-3">A carregar...</td></tr>';
    try {
      const qs = new URLSearchParams({ ano: String(ano), mes: String(mes) });
      const res = await fetch(`/api/fecho_mensal?${qs.toString()}`);
      const data = await res.json().catch(() => ({}));
      if (!res.ok || data.error) throw new Error(data.error || res.statusText);
      state.rows = Array.isArray(data.rows) ? data.rows : [];
      state.totals = data.totals || null;
      state.imputStatus = data.imput_status || {};
      const labels = data.fam_labels || {};
      const setFamTitle = (id, code) => {
        const el = document.getElementById(id);
        if (!el) return;
        const nome = (labels[code] || '').trim();
        el.textContent = nome ? `${code} · ${nome}` : `Fam. ${code}`;
      };
      setFamTitle('fechoFam1', '1');
      setFamTitle('fechoFam2', '2');
      setFamTitle('fechoFam3', '3');
      setFamTitle('fechoFam4', '4');
      setFamTitle('fechoFam9', '9');
      applyImputButtonsStatus();
      render();
    } catch (err) {
      els.body.innerHTML = `<tr><td colspan="9" class="text-danger p-3">Erro: ${(err.message || err)}</td></tr>`;
    }
  }

  async function postImputar(ccustoOri, familia) {
    const { ano, mes } = currentYearMonth();
    const res = await fetch('/api/fecho_mensal/imputar', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ano, mes, ccusto_ori: ccustoOri, familia })
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok || data.error) {
      alert(`Erro: ${data.error || res.statusText}`);
      return false;
    }
    if (data.message) alert(data.message);
    await load();
    return true;
  }

  async function deleteImputacoesMes() {
    const { ano, mes } = currentYearMonth();
    const res = await fetch('/api/fecho_mensal/imputacoes_mes', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ano, mes })
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok || data.error) {
      alert(`Erro: ${data.error || res.statusText}`);
      return;
    }
    await load();
  }

  els.prev?.addEventListener('click', () => {
    let { ano, mes } = currentYearMonth();
    mes -= 1;
    if (mes < 1) { mes = 12; ano -= 1; }
    state.ano = ano; state.mes = mes; applyYearMonth(); load();
  });

  els.next?.addEventListener('click', () => {
    let { ano, mes } = currentYearMonth();
    mes += 1;
    if (mes > 12) { mes = 1; ano += 1; }
    state.ano = ano; state.mes = mes; applyYearMonth(); load();
  });

  els.ano?.addEventListener('change', load);
  els.mes?.addEventListener('change', load);
  els.reload?.addEventListener('click', load);
  els.export?.addEventListener('click', exportCsv);

  els.impSede?.addEventListener('click', () => postImputar('SEDE', '4.1'));
  els.impLav?.addEventListener('click', () => postImputar('LAVANDARIA', '4.3'));
  els.impLimp?.addEventListener('click', () => postImputar('LIMPEZA', '4.2'));
  els.impHelp?.addEventListener('click', () => postImputar('HELPDESK', '4.4'));
  els.delImpMes?.addEventListener('click', () => {
    if (!confirm('Eliminar imputações 4.x do mês selecionado?')) return;
    deleteImputacoesMes();
  });

  applyYearMonth();
  load();
});
