// static/js/recebimentos.js

document.addEventListener('DOMContentLoaded', () => {
  const recFrom = document.getElementById('recFrom');
  const recTo = document.getElementById('recTo');
  const recQ = document.getElementById('recQ');
  const recClear = document.getElementById('recClear');
  const recRefresh = document.getElementById('recRefresh');
  const tbody = document.getElementById('recebimentosBody');
  const recordCount = document.getElementById('recordCount');
  const table = document.getElementById('recebimentosTable');

  const recebimentoModalEl = document.getElementById('recebimentoModal');
  const recebimentoModal = recebimentoModalEl ? new bootstrap.Modal(recebimentoModalEl) : null;
  const recebimentoModalTitle = document.getElementById('recebimentoModalTitle');
  const recebimentoModalSub = document.getElementById('recebimentoModalSub');
  const recebimentoModalTotal = document.getElementById('recebimentoModalTotal');
  const rH_DataInput = document.getElementById('rH_DataInput');
  const rH_Rno = document.getElementById('rH_Rno');
  const rH_Cli = document.getElementById('rH_Cli');
  const rH_Conta = document.getElementById('rH_Conta');
  const rH_Tipo = document.getElementById('rH_Tipo');
  const recebimentoLinesBody = document.getElementById('recebimentoLinesBody');
  const recebimentoSaveDate = document.getElementById('recebimentoSaveDate');
  const recebimentoDelete = document.getElementById('recebimentoDelete');
  let currentRestamp = '';

  const fmt = new Intl.NumberFormat('pt-PT', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  const fmtMoney = (n) => fmt.format(Number(n || 0) || 0);

  const escapeHtml = (s) => (s ?? '').toString()
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#039;');

  let debounce = null;

  function setDefaults() {
    const now = new Date();
    const first = new Date(now.getFullYear(), now.getMonth(), 1);
    const last = new Date(now.getFullYear(), now.getMonth() + 1, 0);
    if (recFrom && !recFrom.value) recFrom.value = first.toISOString().slice(0, 10);
    if (recTo && !recTo.value) recTo.value = last.toISOString().slice(0, 10);
  }

  async function load() {
    if (!tbody) return;
    tbody.innerHTML = '<tr><td colspan="7" class="text-muted p-3">A carregar...</td></tr>';
    const qs = new URLSearchParams();
    if (recFrom?.value) qs.set('de', recFrom.value);
    if (recTo?.value) qs.set('ate', recTo.value);
    if (recQ?.value) qs.set('q', recQ.value);

    const res = await fetch(`/api/recebimentos?${qs.toString()}`);
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      const msg = err.error || res.statusText;
      tbody.innerHTML = `<tr><td colspan="7" class="text-danger p-3">Erro: ${escapeHtml(msg)}</td></tr>`;
      if (recordCount) recordCount.textContent = '';
      return;
    }
    const data = await res.json();
    const rows = data.rows || [];
    const total = Number(data.total || 0) || 0;
    if (recordCount) recordCount.textContent = `${rows.length} recebimento(s) - Total: ${fmtMoney(total)}`;

    if (!rows.length) {
      tbody.innerHTML = '<tr><td colspan="7" class="text-muted p-3">Sem recebimentos.</td></tr>';
      return;
    }
    tbody.innerHTML = rows.map(r => {
      const conta = [r.OLCODIGO, r.OLLOCAL].filter(Boolean).join(' - ');
      const tipo = (r.NMDOC || '').toString();
      return `
        <tr data-restamp="${escapeHtml((r.RESTAMP || '').toString())}">
          <td>${escapeHtml(r.RDATA || '')}</td>
          <td>${escapeHtml(String(r.RNO ?? ''))}</td>
          <td>${escapeHtml(String(r.NO ?? ''))}</td>
          <td>${escapeHtml((r.NOME ?? '').toString())}</td>
          <td class="text-end recebimentos-total">${escapeHtml(fmtMoney(r.ETOTAL))}</td>
          <td>${escapeHtml(conta)}</td>
          <td>${escapeHtml(tipo)}</td>
        </tr>
      `;
    }).join('');
  }

  async function openRecebimento(restamp) {
    if (!recebimentoModal || !restamp) return;
    currentRestamp = restamp;
    if (recebimentoLinesBody) recebimentoLinesBody.innerHTML = '<tr><td colspan="6" class="text-muted p-3">A carregar...</td></tr>';
    if (recebimentoModalTitle) recebimentoModalTitle.textContent = 'Recebimento';
    if (recebimentoModalSub) recebimentoModalSub.textContent = '';
    if (recebimentoModalTotal) recebimentoModalTotal.textContent = '0';
    if (rH_DataInput) rH_DataInput.value = '';
    recebimentoModal.show();

    const res = await fetch(`/api/recebimentos/${encodeURIComponent(restamp)}`);
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      const msg = err.error || res.statusText;
      if (recebimentoLinesBody) recebimentoLinesBody.innerHTML = `<tr><td colspan="6" class="text-danger p-3">Erro: ${escapeHtml(msg)}</td></tr>`;
      return;
    }
    const data = await res.json();
    const h = data.header || {};
    const lines = data.lines || [];

    const conta = [h.OLCODIGO, h.OLLOCAL].filter(Boolean).join(' - ');
    const tipo = (h.NMDOC || '').toString();
    if (recebimentoModalTitle) recebimentoModalTitle.textContent = `Recebimento ${escapeHtml(String(h.RNO ?? ''))}`;
    if (recebimentoModalSub) recebimentoModalSub.textContent = `${h.NO ?? ''} - ${(h.NOME ?? '').toString()}`.trim();
    if (recebimentoModalTotal) recebimentoModalTotal.textContent = fmtMoney(h.ETOTAL);
    if (rH_DataInput) rH_DataInput.value = (h.RDATA || '');
    if (rH_Rno) rH_Rno.textContent = String(h.RNO ?? '--');
    if (rH_Cli) rH_Cli.textContent = `${h.NO ?? ''} - ${(h.NOME ?? '').toString()}`.trim();
    if (rH_Conta) rH_Conta.textContent = conta || '--';
    if (rH_Tipo) rH_Tipo.textContent = tipo || '--';

    if (!recebimentoLinesBody) return;
    if (!lines.length) {
      recebimentoLinesBody.innerHTML = '<tr><td colspan="6" class="text-muted p-3">Sem linhas.</td></tr>';
      return;
    }
    recebimentoLinesBody.innerHTML = lines.map(l => {
      return `
        <tr>
          <td>${escapeHtml(l.DATALC || '')}</td>
          <td>${escapeHtml(l.DATAVEN || '')}</td>
          <td>${escapeHtml((l.CDESC || '').toString())}</td>
          <td>${escapeHtml(String(l.NRDOC ?? ''))}</td>
          <td class="text-end fw-semibold">${escapeHtml(fmtMoney(l.EVAL))}</td>
          <td class="text-end fw-bold">${escapeHtml(fmtMoney(l.EREC))}</td>
        </tr>
      `;
    }).join('');
  }

  function scheduleLoad() {
    clearTimeout(debounce);
    debounce = setTimeout(() => load().catch(err => {
      if (tbody) tbody.innerHTML = `<tr><td colspan="7" class="text-danger p-3">Erro: ${escapeHtml(err?.message || err)}</td></tr>`;
    }), 250);
  }

  recFrom?.addEventListener('change', scheduleLoad);
  recTo?.addEventListener('change', scheduleLoad);
  recQ?.addEventListener('input', scheduleLoad);
  recRefresh?.addEventListener('click', (e) => { e.preventDefault(); load(); });
  recClear?.addEventListener('click', (e) => {
    e.preventDefault();
    if (recQ) recQ.value = '';
    setDefaults();
    load();
  });

  recebimentoSaveDate?.addEventListener('click', async (e) => {
    e.preventDefault();
    if (!currentRestamp) return;
    const dateValue = (rH_DataInput?.value || '').toString().trim();
    if (!dateValue) {
      alert('Indique a data do recebimento.');
      return;
    }
    recebimentoSaveDate.disabled = true;
    try {
      const res = await fetch(`/api/recebimentos/${encodeURIComponent(currentRestamp)}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ RDATA: dateValue })
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.error || res.statusText);
      }
      await res.json().catch(() => ({}));
      recebimentoModal?.hide();
      await load();
    } catch (err) {
      alert(err?.message || err);
    } finally {
      recebimentoSaveDate.disabled = false;
    }
  });

  recebimentoDelete?.addEventListener('click', async (e) => {
    e.preventDefault();
    if (!currentRestamp) return;
    const rno = (rH_Rno?.textContent || '').toString().trim();
    if (!confirm(`Eliminar o recebimento${rno ? ` ${rno}` : ''} e respetivas linhas?`)) return;
    recebimentoDelete.disabled = true;
    try {
      const res = await fetch(`/api/recebimentos/${encodeURIComponent(currentRestamp)}`, { method: 'DELETE' });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.error || res.statusText);
      }
      await res.json().catch(() => ({}));
      recebimentoModal?.hide();
      await load();
    } catch (err) {
      alert(err?.message || err);
    } finally {
      recebimentoDelete.disabled = false;
    }
  });

  table?.addEventListener('click', (e) => {
    const tr = e.target.closest('tr[data-restamp]');
    if (!tr) return;
    const restamp = (tr.dataset.restamp || '').toString().trim();
    if (!restamp) return;
    openRecebimento(restamp).catch(err => alert(err?.message || err));
  });

  recebimentoModalEl?.addEventListener('hidden.bs.modal', () => {
    currentRestamp = '';
    if (recebimentoSaveDate) recebimentoSaveDate.disabled = false;
    if (recebimentoDelete) recebimentoDelete.disabled = false;
  });

  setDefaults();
  load();
});

