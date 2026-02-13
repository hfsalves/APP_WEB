document.addEventListener('DOMContentLoaded', () => {
  const els = {
    body: document.getElementById('paraBody'),
    reload: document.getElementById('paraReload'),
    save: document.getElementById('paraSave'),
    search: document.getElementById('paraSearch'),
    clear: document.getElementById('paraClear'),
    newBtn: document.getElementById('paraNewBtn'),
    newModal: document.getElementById('paraNewModal'),
    newGrupo: document.getElementById('newGrupo'),
    newGrupoBtn: document.getElementById('newGrupoBtn'),
    newParametro: document.getElementById('newParametro'),
    newDescricao: document.getElementById('newDescricao'),
    newTipo: document.getElementById('newTipo'),
    newValor: document.getElementById('newValor'),
    newSave: document.getElementById('newParaSave'),
    editModal: document.getElementById('paraEditModal'),
    editStamp: document.getElementById('editParastamp'),
    editParametro: document.getElementById('editParametro'),
    editDescricao: document.getElementById('editDescricao'),
    editSave: document.getElementById('editParaSave'),
    editDelete: document.getElementById('editParaDelete')
  };

  let allRows = [];
  let groups = [];
  const expanded = new Set();

  const esc = (s) => String(s ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#039;');

  const fmtTipo = (t) => (t || '').toUpperCase();

  function matchesSearch(r, q) {
    if (!q) return true;
    const txt = [
      r.GRUPO, r.PARAMETRO, r.DESCRICAO, r.TIPO, r.VALOR
    ].map(v => String(v ?? '').toLowerCase()).join(' ');
    return txt.includes(q);
  }

  function valueInputHtml(r) {
    const t = fmtTipo(r.TIPO);
    if (t === 'N') return `<input class="form-control form-control-sm js-vn" type="number" step="0.0001" value="${esc(r.NVALOR)}">`;
    if (t === 'D') return `<input class="form-control form-control-sm js-vd" type="date" value="${esc(r.DVALOR || '')}">`;
    if (t === 'L') return `<input class="form-check-input js-vl" type="checkbox" ${Number(r.LVALOR || 0) ? 'checked' : ''}>`;
    return `<input class="form-control form-control-sm js-vc" type="text" value="${esc(r.CVALOR || '')}" maxlength="200">`;
  }

  function render() {
    const q = (els.search.value || '').trim().toLowerCase();
    const rows = allRows.filter(r => matchesSearch(r, q));
    if (!rows.length) {
      els.body.innerHTML = '<tr><td colspan="3" class="text-muted p-3">Sem registos.</td></tr>';
      return;
    }

    const map = new Map();
    rows.forEach(r => {
      const g = (r.GRUPO || 'Sem grupo').trim() || 'Sem grupo';
      if (!map.has(g)) map.set(g, []);
      map.get(g).push(r);
    });

    let html = '';
    [...map.keys()].sort((a, b) => a.localeCompare(b, 'pt', { sensitivity: 'base' })).forEach(g => {
      const isOpen = expanded.has(g);
      html += `<tr class="para-group-row" data-group="${esc(g)}"><td colspan="3"><button type="button" class="btn btn-sm para-group-toggle">${isOpen ? '−' : '+'}</button>${esc(g)}</td></tr>`;
      if (isOpen) {
        const inGroup = [...map.get(g)].sort((a, b) =>
          String(a.DESCRICAO || '').localeCompare(String(b.DESCRICAO || ''), 'pt', { sensitivity: 'base' })
        );
        inGroup.forEach(r => {
          html += `
            <tr data-stamp="${esc(r.PARASTAMP)}" data-tipo="${esc(r.TIPO)}">
              <td>${esc(r.DESCRICAO)}</td>
              <td>${valueInputHtml(r)}</td>
              <td class="para-codigo" data-edit="${esc(r.PARASTAMP)}">${esc(r.PARAMETRO)}</td>
            </tr>
          `;
        });
      }
    });
    els.body.innerHTML = html;

    els.body.querySelectorAll('.para-group-row').forEach(tr => {
      tr.addEventListener('click', () => {
        const g = tr.getAttribute('data-group');
        if (!g) return;
        if (expanded.has(g)) expanded.delete(g); else expanded.add(g);
        render();
      });
    });
    els.body.querySelectorAll('[data-edit]').forEach(el => {
      el.addEventListener('click', (ev) => {
        ev.stopPropagation();
        const stamp = el.getAttribute('data-edit');
        const row = allRows.find(r => String(r.PARASTAMP || '') === String(stamp || ''));
        if (!row) return;
        els.editStamp.value = row.PARASTAMP || '';
        els.editParametro.value = row.PARAMETRO || '';
        els.editDescricao.value = row.DESCRICAO || '';
        bootstrap.Modal.getOrCreateInstance(els.editModal).show();
      });
    });
  }

  async function load() {
    els.body.innerHTML = '<tr><td colspan="3" class="text-muted p-3">A carregar...</td></tr>';
    const res = await fetch('/api/parametros');
    const data = await res.json().catch(() => ({}));
    if (!res.ok || data.error) {
      els.body.innerHTML = `<tr><td colspan="3" class="text-danger p-3">Erro: ${esc(data.error || res.statusText)}</td></tr>`;
      return;
    }
    groups = Array.isArray(data.groups) ? data.groups : [];
    allRows = Array.isArray(data.rows) ? data.rows : [];
    groups.forEach(g => expanded.add(g));
    render();
  }

  async function save() {
    const payload = [];
    els.body.querySelectorAll('tr[data-stamp]').forEach(tr => {
      const stamp = tr.getAttribute('data-stamp');
      const tipo = fmtTipo(tr.getAttribute('data-tipo'));
      const row = { PARASTAMP: stamp, TIPO: tipo };
      if (tipo === 'N') row.NVALOR = Number(tr.querySelector('.js-vn')?.value || 0);
      else if (tipo === 'D') row.DVALOR = tr.querySelector('.js-vd')?.value || '';
      else if (tipo === 'L') row.LVALOR = tr.querySelector('.js-vl')?.checked ? 1 : 0;
      else row.CVALOR = tr.querySelector('.js-vc')?.value || '';
      payload.push(row);
    });
    const res = await fetch('/api/parametros/save', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ rows: payload })
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok || data.error) {
      alert(`Erro: ${data.error || res.statusText}`);
      return;
    }
    await load();
  }

  function fillNewGroups() {
    els.newGrupo.innerHTML = '';
    groups.forEach(g => {
      const o = document.createElement('option');
      o.value = g;
      o.textContent = g;
      els.newGrupo.appendChild(o);
    });
  }

  async function createNew() {
    const t = fmtTipo(els.newTipo.value);
    const body = {
      GRUPO: (els.newGrupo.value || '').trim(),
      PARAMETRO: (els.newParametro.value || '').trim(),
      DESCRICAO: (els.newDescricao.value || '').trim(),
      TIPO: t
    };
    const v = (els.newValor.value || '').trim();
    if (t === 'N') body.NVALOR = Number(v || 0);
    else if (t === 'D') body.DVALOR = v;
    else if (t === 'L') body.LVALOR = (v === '1' || v.toLowerCase() === 'true' || v.toLowerCase() === 'sim') ? 1 : 0;
    else body.CVALOR = v;

    const res = await fetch('/api/parametros/new', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok || data.error) {
      alert(`Erro: ${data.error || res.statusText}`);
      return;
    }
    bootstrap.Modal.getInstance(els.newModal)?.hide();
    await load();
  }

  async function saveEditMeta() {
    const body = {
      PARASTAMP: (els.editStamp.value || '').trim(),
      PARAMETRO: (els.editParametro.value || '').trim(),
      DESCRICAO: (els.editDescricao.value || '').trim()
    };
    const res = await fetch('/api/parametros/edit_meta', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok || data.error) {
      alert(`Erro: ${data.error || res.statusText}`);
      return;
    }
    bootstrap.Modal.getInstance(els.editModal)?.hide();
    await load();
  }

  async function deleteParametro() {
    const stamp = (els.editStamp.value || '').trim();
    if (!stamp) return;
    if (!confirm('Eliminar este parâmetro?')) return;
    const res = await fetch('/api/parametros/delete', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ PARASTAMP: stamp })
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok || data.error) {
      alert(`Erro: ${data.error || res.statusText}`);
      return;
    }
    bootstrap.Modal.getInstance(els.editModal)?.hide();
    await load();
  }

  async function createNewGroup() {
    const nome = prompt('Nome do novo grupo:');
    if (!nome || !nome.trim()) return;
    const res = await fetch('/api/parametros/group/new', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ GRUPO: nome.trim() })
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok || data.error) {
      alert(`Erro: ${data.error || res.statusText}`);
      return;
    }
    await load();
    fillNewGroups();
    els.newGrupo.value = nome.trim();
  }

  els.reload?.addEventListener('click', load);
  els.save?.addEventListener('click', save);
  els.search?.addEventListener('input', render);
  els.clear?.addEventListener('click', () => { els.search.value = ''; render(); els.search.focus(); });
  els.newBtn?.addEventListener('click', () => {
    fillNewGroups();
    els.newParametro.value = '';
    els.newDescricao.value = '';
    els.newTipo.value = 'C';
    els.newValor.value = '';
    bootstrap.Modal.getOrCreateInstance(els.newModal).show();
  });
  els.newSave?.addEventListener('click', createNew);
  els.newGrupoBtn?.addEventListener('click', createNewGroup);
  els.editSave?.addEventListener('click', saveEditMeta);
  els.editDelete?.addEventListener('click', deleteParametro);

  load();
});
