// static/js/extrato_import.js

document.addEventListener('DOMContentLoaded', () => {
  const contaSel = document.getElementById('extConta');
  const form = document.getElementById('extForm');
  const fileIn = document.getElementById('extFile');
  const statusEl = document.getElementById('extStatus');
  const btn = document.getElementById('extSubmit');
  const countEl = document.getElementById('extCount');
  const metaEl = document.getElementById('extMeta');
  const tbody = document.querySelector('#extPreview tbody');

  const fmtMoney = (v) => {
    const n = Number(v || 0) || 0;
    return n.toLocaleString('pt-PT', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  };

  const esc = (s) => (s ?? '').toString()
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#039;');

  function setStatus(msg, kind) {
    if (!statusEl) return;
    statusEl.className = 'small ' + (kind === 'err' ? 'text-danger' : kind === 'ok' ? 'text-success' : 'text-muted');
    statusEl.textContent = msg || '';
  }

  async function loadAccounts() {
    if (!contaSel) return;
    contaSel.innerHTML = '<option value="">A carregar...</option>';
    try {
      const r = await fetch('/generic/api/tesouraria/contas');
      const js = await r.json().catch(() => ([]));
      if (!r.ok || js.error) throw new Error(js.error || r.statusText);
      const rows = Array.isArray(js) ? js : [];
      contaSel.innerHTML = rows.map(c => {
        const noconta = (c.NOCONTA ?? c.noconta ?? '').toString();
        const banco = (c.BANCO || c.banco || '').toString();
        const conta = (c.CONTA || c.conta || '').toString();
        const label = [banco, conta].filter(Boolean).join(' - ') || noconta;
        return `<option value="${esc(noconta)}">${esc(label)}</option>`;
      }).join('');
      const has1 = Array.from(contaSel.options).some(o => (o.value || '') === '1');
      if (has1) contaSel.value = '1';
    } catch (e) {
      contaSel.innerHTML = '<option value="">(Erro a carregar contas)</option>';
      setStatus(e?.message || String(e), 'err');
    }
  }

  loadAccounts();

  form?.addEventListener('submit', async (e) => {
    e.preventDefault();
    if (!fileIn?.files?.length) { setStatus('Seleciona um ficheiro CSV.', 'err'); return; }
    if (!contaSel?.value) { setStatus('Seleciona a conta.', 'err'); return; }

    try {
      setStatus('A importar...', '');
      if (btn) btn.disabled = true;
      const fd = new FormData(form);
      const r = await fetch('/api/extratos/import', { method: 'POST', body: fd });
      const js = await r.json().catch(() => ({}));
      if (!r.ok || js.error) throw new Error(js.error || r.statusText);

      const inserted = Number(js.inserted || 0) || 0;
      const skipped = Number(js.skipped || 0) || 0;
      const extstamp = (js.EXTSTAMP || '').toString();
      if (countEl) countEl.textContent = String(inserted);
      if (metaEl) metaEl.textContent = `EXTSTAMP: ${extstamp} | Inseridas: ${inserted} | Ignoradas: ${skipped}`;

      const rows = Array.isArray(js.sample) ? js.sample : [];
      if (tbody) {
        if (!rows.length) {
          tbody.innerHTML = '<tr><td colspan="4" class="text-muted">Sem dados.</td></tr>';
        } else {
          tbody.innerHTML = rows.map(r0 => {
            const v = Number(r0.VALOR || 0) || 0;
            const cls = v < 0 ? 'text-danger' : 'text-success';
            return `
              <tr>
                <td>${esc(r0.DATA || '')}</td>
                <td>${esc(r0.DTVALOR || '')}</td>
                <td class="text-truncate" style="max-width:420px;" title="${esc(r0.DESCRICAO || '')}">${esc(r0.DESCRICAO || '')}</td>
                <td class="text-end ${cls}" style="font-variant-numeric: tabular-nums;">${fmtMoney(v)}</td>
              </tr>
            `;
          }).join('');
        }
      }

      setStatus('Importado com sucesso.', 'ok');
    } catch (err) {
      setStatus(err?.message || String(err), 'err');
    } finally {
      if (btn) btn.disabled = false;
    }
  });
});
