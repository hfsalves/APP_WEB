// static/js/fr_import.js

document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('frForm');
  const fileEl = document.getElementById('frFile');
  const statusEl = document.getElementById('frStatus');
  const metaEl = document.getElementById('frMeta');
  const countEl = document.getElementById('frCount');
  const submitBtn = document.getElementById('frSubmit');
  const tbody = document.querySelector('#frPreview tbody');

  const esc = (s) => (s ?? '').toString()
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#039;');

  const fmtMoney = (v) => {
    const n = Number(v || 0) || 0;
    return n.toLocaleString('pt-PT', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  };

  function setStatus(msg, kind) {
    if (!statusEl) return;
    statusEl.className = 'small ' + (kind === 'err' ? 'text-danger' : kind === 'ok' ? 'text-success' : 'text-muted');
    statusEl.textContent = msg || '';
  }

  function render(rows) {
    if (!tbody) return;
    if (!Array.isArray(rows) || !rows.length) {
      tbody.innerHTML = '<tr><td colspan="10" class="text-muted">Sem dados.</td></tr>';
      return;
    }
    tbody.innerHTML = rows.map(r => {
      const mode = (r.MODE || '').toString().toUpperCase() === 'U' ? 'U' : 'I';
      const badge = mode === 'U'
        ? '<span class="badge bg-warning text-dark">UPD</span>'
        : '<span class="badge bg-success">INS</span>';
      const anul = Number(r.ANULADO || 0) === 1 ? '<span class="badge bg-danger">Sim</span>' : '<span class="badge bg-light text-dark">Não</span>';
      return `
        <tr>
          <td class="op-pill">${badge}</td>
          <td>${esc(r.DOCUMENTO || '')}</td>
          <td>${esc(r.DATA || '')}</td>
          <td class="text-truncate" style="max-width:320px;" title="${esc(r.CLIENTE || '')}">${esc(r.CLIENTE || '')}</td>
          <td>${esc(r.CCUSTO || '')}</td>
          <td>${esc(r.ARTIGO || '')}</td>
          <td class="text-end">${esc(fmtMoney(r.BASE))}</td>
          <td class="text-end">${esc(fmtMoney(r.TAXAIVA))}</td>
          <td class="text-end">${esc(fmtMoney(r.IVA))}</td>
          <td>${anul}</td>
        </tr>
      `;
    }).join('');
  }

  form?.addEventListener('submit', async (e) => {
    e.preventDefault();
    if (!fileEl?.files?.[0]) {
      alert('Escolha um ficheiro .xlsx');
      return;
    }
    const fd = new FormData();
    fd.append('file', fileEl.files[0]);

    try {
      if (submitBtn) submitBtn.disabled = true;
      setStatus('A importar...', '');
      const res = await fetch('/api/fr/import', { method: 'POST', body: fd });
      const js = await res.json().catch(() => ({}));
      if (!res.ok || js.error) throw new Error(js.error || res.statusText);

      const ins = Number(js.inserted || 0);
      const upd = Number(js.updated || 0);
      const skp = Number(js.skipped || 0);
      const sample = js.sample || [];
      if (countEl) countEl.textContent = String(sample.length || 0);
      if (metaEl) metaEl.textContent = `Inseridas: ${ins} | Atualizadas: ${upd} | Ignoradas: ${skp}`;
      render(sample);
      setStatus('Importação concluída.', 'ok');
    } catch (err) {
      setStatus('Erro: ' + (err?.message || String(err)), 'err');
    } finally {
      if (submitBtn) submitBtn.disabled = false;
    }
  });
});

