document.addEventListener('DOMContentLoaded', () => {
  const body = document.getElementById('imputBody');
  const btnSave = document.getElementById('btnSaveImput');
  const btnReload = document.getElementById('btnReloadImput');
  const searchInput = document.getElementById('imputSearch');
  const statusSelect = document.getElementById('imputStatus');
  const clearBtn = document.getElementById('imputClear');

  const now = new Date();
  const currMonth = now.getMonth() + 1;
  const currYear = now.getFullYear();
  let lastRows = [];
  let sortState = { key: 'DATA', dir: 'desc' };

  const escapeHtml = (s) => (s ?? '').toString()
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#039;');

  const fmtDate = (d) => {
    if (!d) return '';
    const dt = new Date(d);
    if (isNaN(dt)) return String(d);
    return dt.toISOString().slice(0, 10);
  };

  const monthValue = (m, y) => {
    const mm = String(m).padStart(2, '0');
    return `${y}-${mm}`;
  };

  function sortRows(rows) {
    const { key, dir } = sortState;
    const mul = dir === 'desc' ? -1 : 1;
    return [...rows].sort((a, b) => {
      const av = a?.[key];
      const bv = b?.[key];
      if (key === 'DATA') {
        const ad = av ? new Date(av) : null;
        const bd = bv ? new Date(bv) : null;
        if (ad && bd) return (ad - bd) * mul;
        if (ad) return -1 * mul;
        if (bd) return 1 * mul;
        return 0;
      }
      if (['TOTAL','IMPUTVALOR','IMPUTMES','IMPUTANO'].includes(key)) {
        return (Number(av || 0) - Number(bv || 0)) * mul;
      }
      return String(av || '').localeCompare(String(bv || ''), 'pt', { sensitivity: 'base' }) * mul;
    });
  }

  function rowImputState(row) {
    const imp = Number(row.IMPUTAR || 0) === 1;
    const nimp = Number(row.NIMPUTAR || 0) === 1;
    if (imp) return 'yes';
    if (nimp) return 'no';
    return 'pending';
  }

  function rowSearchText(row) {
    return [
      row.ORIGEM, row.DATA, row.DOC, row.NOME, row.ALOJAMENTO,
      row.TOTAL, row.IMPUTMES, row.IMPUTANO, row.IMPUTVALOR, row.IMPUTDESIGN
    ].map(v => (v ?? '').toString().toLowerCase()).join(' ');
  }

  function filterRows(rows) {
    const q = (searchInput?.value || '').toString().trim().toLowerCase();
    const st = (statusSelect?.value || 'pending').toString();
    return rows.filter(r => {
      if (st !== 'all' && rowImputState(r) !== st) return false;
      if (q && !rowSearchText(r).includes(q)) return false;
      return true;
    });
  }

  function render(rows) {
    if (!body) return;
    if (!rows.length) {
      body.innerHTML = '<tr><td colspan="12" class="text-muted p-3">Sem registos.</td></tr>';
      return;
    }
    const sorted = sortRows(filterRows(rows));
    const foImputMap = {};
    sorted.forEach(r => {
      if ((r.ORIGEM || '').toUpperCase() === 'FO') {
        foImputMap[r.STAMP] = Number(r.IMPUTAR || 0) === 1;
      }
    });
    body.innerHTML = sorted.map(r => {
      const mes = Number(r.IMPUTMES || 0) || currMonth;
      const ano = Number(r.IMPUTANO || 0) || currYear;
      const base = Number(r.BASE || 0);
      let valor = (r.IMPUTVALOR != null && r.IMPUTVALOR !== '') ? Number(r.IMPUTVALOR) : null;
      if (!valor && base > 0) valor = base;
      const design = r.IMPUTDESIGN || '';
      const imp = Number(r.IMPUTAR || 0) === 1;
      const nimp = Number(r.NIMPUTAR || 0) === 1;
      const origem = (r.ORIGEM || '').toUpperCase();
      const badge = origem === 'MN' ? 'mn' : 'fo';
      const isFn = origem === 'FN';
      const parent = r.FOSTAMP || '';
      const disableFn = isFn && foImputMap[parent] === true;
      return `
        <tr data-origem="${escapeHtml(origem)}" data-stamp="${escapeHtml(r.STAMP || '')}" data-fostamp="${escapeHtml(parent)}" data-imputar="${imp ? '1' : '0'}" data-nimputar="${nimp ? '1' : '0'}" class="${isFn ? 'imput-child' : ''}">
          <td><span class="imput-badge ${badge}">${escapeHtml(origem)}</span></td>
          <td>${escapeHtml(fmtDate(r.DATA))}</td>
          <td title="${escapeHtml(r.DOC || '')}">${escapeHtml(r.DOC || '')}</td>
          <td title="${escapeHtml(r.NOME || '')}">${escapeHtml(r.NOME || '')}</td>
          <td title="${escapeHtml(r.ALOJAMENTO || '')}">${escapeHtml(r.ALOJAMENTO || '')}</td>
          <td class="text-end">${escapeHtml((r.TOTAL ?? '').toString())}</td>
          <td>
            <div class="btn-group imput-toggle" role="group">
              <button type="button" class="btn btn-sm imput-pill ${imp ? 'active' : ''}" data-value="S" ${disableFn ? 'disabled' : ''}>Sim</button>
              <button type="button" class="btn btn-sm imput-pill ${nimp ? 'active' : ''}" data-value="N" ${disableFn ? 'disabled' : ''}>Não</button>
            </div>
          </td>
          <td><input type="month" class="form-control form-control-sm js-mesano" value="${escapeHtml(monthValue(mes, ano))}" ${disableFn ? 'disabled' : ''}></td>
          <td><input type="number" step="0.01" class="form-control form-control-sm text-end js-valor" value="${escapeHtml(valor)}" ${disableFn ? 'disabled' : ''}></td>
          <td><input type="text" class="form-control form-control-sm wide js-design" value="${escapeHtml(design)}" ${disableFn ? 'disabled' : ''}></td>
        </tr>
      `;
    }).join('');

    body.querySelectorAll('tr').forEach(tr => {
      const mesAnoEl = tr.querySelector('.js-mesano');
      const row = sorted.find(r => r.STAMP === tr.dataset.stamp);
      const mes = Number(row?.IMPUTMES || 0) || currMonth;
      const ano = Number(row?.IMPUTANO || 0) || currYear;
      if (mesAnoEl) mesAnoEl.value = monthValue(mes, ano);
    });

    body.querySelectorAll('.imput-toggle .imput-pill').forEach(btn => {
      btn.addEventListener('click', () => {
        const group = btn.closest('.imput-toggle');
        if (!group) return;
        if (btn.disabled) return;
        if (btn.classList.contains('active')) {
          btn.classList.remove('active');
          return;
        }
        group.querySelectorAll('.imput-pill').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        const row = btn.closest('tr');
        if (row?.dataset?.origem === 'FO') {
          applyFoLocks(row.dataset.stamp);
        }
      });
    });

    body.querySelectorAll('tr[data-origem]').forEach(tr => {
      tr.addEventListener('click', (e) => {
        const tag = (e.target?.tagName || '').toLowerCase();
        if (['input', 'select', 'button', 'option'].includes(tag)) return;
        if (e.target?.closest?.('.imput-toggle')) return;
        const origem = (tr.dataset.origem || '').toUpperCase();
        const stamp = tr.dataset.stamp || '';
        if (!stamp) return;
        if (origem === 'FO') {
          window.open(`/generic/fo_compras_form/${encodeURIComponent(stamp)}`, '_blank');
        } else if (origem === 'MN') {
          window.open(`/generic/form/MN/${encodeURIComponent(stamp)}`, '_blank');
        }
      });
    });
  }

  function applyFoLocks(fostamp) {
    const foRow = body?.querySelector?.(`tr[data-origem="FO"][data-stamp="${fostamp}"]`);
    if (!foRow) return;
    const foImput = !!foRow.querySelector('.imput-pill.active[data-value="S"]');
    body?.querySelectorAll?.(`tr[data-origem="FN"][data-fostamp="${fostamp}"]`)?.forEach(tr => {
      tr.querySelectorAll('button.imput-pill, input.js-mesano, input.js-valor, input.js-design').forEach(el => {
        el.disabled = foImput;
      });
    });
  }

  async function load() {
    if (!body) return;
    body.innerHTML = '<tr><td colspan="12" class="text-muted p-3">A carregar...</td></tr>';
    const res = await fetch('/api/imputacao_proprietarios');
    const data = await res.json().catch(() => ({}));
    if (!res.ok || data.error) {
      body.innerHTML = `<tr><td colspan="12" class="text-danger p-3">Erro: ${escapeHtml(data.error || res.statusText)}</td></tr>`;
      return;
    }
    lastRows = Array.isArray(data.rows) ? data.rows : [];
    render(lastRows);
  }

  async function save() {
    const rows = [];
    body?.querySelectorAll('tr[data-stamp]')?.forEach(tr => {
      const active = tr.querySelector('.imput-toggle .imput-pill.active');
      const val = active?.getAttribute('data-value') || '';
      rows.push({
        origem: tr.dataset.origem,
        stamp: tr.dataset.stamp,
        imputar: val === 'S' ? 1 : 0,
        nimputar: val === 'N' ? 1 : 0,
        imputmes: Number((tr.querySelector('.js-mesano')?.value || '').slice(5, 7) || 0),
        imputano: Number((tr.querySelector('.js-mesano')?.value || '').slice(0, 4) || 0),
        imputvalor: Number(tr.querySelector('.js-valor')?.value || 0),
        imputdesign: (tr.querySelector('.js-design')?.value || '').trim()
      });
    });
    const res = await fetch('/api/imputacao_proprietarios/save', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ rows })
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok || data.error) {
      alert(`Erro: ${data.error || res.statusText}`);
      return;
    }
    await load();
  }

  btnReload?.addEventListener('click', load);
  btnSave?.addEventListener('click', save);
  searchInput?.addEventListener('input', () => render(lastRows));
  statusSelect?.addEventListener('change', () => render(lastRows));
  clearBtn?.addEventListener('click', () => {
    if (searchInput) searchInput.value = '';
    render(lastRows);
    searchInput?.focus();
  });
  document.querySelectorAll('.imput-table thead th[data-key]')?.forEach(th => {
    th.addEventListener('click', () => {
      const key = th.getAttribute('data-key');
      if (!key) return;
      if (sortState.key === key) {
        sortState.dir = sortState.dir === 'asc' ? 'desc' : 'asc';
      } else {
        sortState.key = key;
        sortState.dir = 'asc';
      }
      document.querySelectorAll('.imput-table thead th').forEach(h => h.classList.remove('sort-asc','sort-desc'));
      th.classList.add(sortState.dir === 'asc' ? 'sort-asc' : 'sort-desc');
      render(lastRows);
    });
  });
  const initTh = document.querySelector(`.imput-table thead th[data-key="${sortState.key}"]`);
  if (initTh) initTh.classList.add(sortState.dir === 'asc' ? 'sort-asc' : 'sort-desc');
  load();
});
