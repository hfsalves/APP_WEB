// static/js/pagamentos.js

document.addEventListener('DOMContentLoaded', () => {
  const payFrom = document.getElementById('payFrom');
  const payTo = document.getElementById('payTo');
  const payLote = document.getElementById('payLote');
  const payQ = document.getElementById('payQ');
  const payClear = document.getElementById('payClear');
  const payRefresh = document.getElementById('payRefresh');
  const tbody = document.getElementById('pagamentosBody');
  const recordCount = document.getElementById('recordCount');
  const table = document.getElementById('pagamentosTable');

  const pagamentoModalEl = document.getElementById('pagamentoModal');
  const pagamentoModal = pagamentoModalEl ? new bootstrap.Modal(pagamentoModalEl) : null;
  const pagamentoModalTitle = document.getElementById('pagamentoModalTitle');
  const pagamentoModalSub = document.getElementById('pagamentoModalSub');
  const pagamentoModalTotal = document.getElementById('pagamentoModalTotal');
  const pH_DataInput = document.getElementById('pH_DataInput');
  const pH_Lote = document.getElementById('pH_Lote');
  const pH_Rno = document.getElementById('pH_Rno');
  const pH_For = document.getElementById('pH_For');
  const pH_Conta = document.getElementById('pH_Conta');
  const pH_Doc = document.getElementById('pH_Doc');
  const pagamentoLinesBody = document.getElementById('pagamentoLinesBody');
  const pagamentoSaveDate = document.getElementById('pagamentoSaveDate');
  const pagamentoDelete = document.getElementById('pagamentoDelete');
  let currentPostamp = '';

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
    if (payFrom && !payFrom.value) payFrom.value = first.toISOString().slice(0, 10);
    if (payTo && !payTo.value) payTo.value = last.toISOString().slice(0, 10);
  }

  async function load() {
    if (!tbody) return;
    tbody.innerHTML = '<tr><td colspan="8" class="text-muted p-3">A carregar...</td></tr>';
    const qs = new URLSearchParams();
    if (payFrom?.value) qs.set('de', payFrom.value);
    if (payTo?.value) qs.set('ate', payTo.value);
    if (payLote?.value) qs.set('lote', payLote.value);
    if (payQ?.value) qs.set('q', payQ.value);

    const res = await fetch(`/api/pagamentos?${qs.toString()}`);
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      const msg = err.error || res.statusText;
      tbody.innerHTML = `<tr><td colspan="8" class="text-danger p-3">Erro: ${escapeHtml(msg)}</td></tr>`;
      if (recordCount) recordCount.textContent = '';
      return;
    }
    const data = await res.json();
    const rows = data.rows || [];
    const total = Number(data.total || 0) || 0;
    if (recordCount) recordCount.textContent = `${rows.length} pagamento(s) - Total: ${fmtMoney(total)}`;

    if (!rows.length) {
      tbody.innerHTML = '<tr><td colspan="8" class="text-muted p-3">Sem pagamentos.</td></tr>';
      return;
    }
    tbody.innerHTML = rows.map(r => {
      const conta = [r.OLCODIGO, r.OLLOCAL].filter(Boolean).join(' - ');
      const doc = [r.CMDESC, r.ADOC].filter(Boolean).join(' ');
      return `
        <tr data-postamp="${escapeHtml((r.POSTAMP || '').toString())}">
          <td>${escapeHtml(r.RDATA || '')}</td>
          <td>${escapeHtml(String(r.LOTE ?? ''))}</td>
          <td>${escapeHtml(String(r.RNO ?? ''))}</td>
          <td>${escapeHtml(String(r.NO ?? ''))}</td>
          <td>${escapeHtml((r.NOME ?? '').toString())}</td>
          <td class="text-end pagamentos-total">${escapeHtml(fmtMoney(r.ETOTAL))}</td>
          <td>${escapeHtml(conta)}</td>
          <td>${escapeHtml(doc)}</td>
        </tr>
      `;
    }).join('');
  }

  async function openPagamento(postamp) {
    if (!pagamentoModal || !postamp) return;
    currentPostamp = postamp;
    if (pagamentoLinesBody) pagamentoLinesBody.innerHTML = '<tr><td colspan="5" class="text-muted p-3">A carregar...</td></tr>';
    if (pagamentoModalTitle) pagamentoModalTitle.textContent = 'Pagamento';
    if (pagamentoModalSub) pagamentoModalSub.textContent = '';
    if (pagamentoModalTotal) pagamentoModalTotal.textContent = '0';
    if (pH_DataInput) pH_DataInput.value = '';
    pagamentoModal.show();

    const res = await fetch(`/api/pagamentos/${encodeURIComponent(postamp)}`);
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      const msg = err.error || res.statusText;
      if (pagamentoLinesBody) pagamentoLinesBody.innerHTML = `<tr><td colspan="5" class="text-danger p-3">Erro: ${escapeHtml(msg)}</td></tr>`;
      return;
    }
    const data = await res.json();
    const h = data.header || {};
    const lines = data.lines || [];

    const conta = [h.OLCODIGO, h.OLLOCAL].filter(Boolean).join(' - ');
    const doc = [h.CMDESC, h.ADOC].filter(Boolean).join(' ');
    if (pagamentoModalTitle) pagamentoModalTitle.textContent = `Pagamento ${escapeHtml(String(h.RNO ?? ''))}`;
    if (pagamentoModalSub) pagamentoModalSub.textContent = `${h.NO ?? ''} - ${(h.NOME ?? '').toString()}`.trim();
    if (pagamentoModalTotal) pagamentoModalTotal.textContent = fmtMoney(h.ETOTAL);
    if (pH_DataInput) pH_DataInput.value = (h.RDATA || '');
    if (pH_Lote) pH_Lote.textContent = String(h.LOTE ?? '--');
    if (pH_Rno) pH_Rno.textContent = String(h.RNO ?? '--');
    if (pH_For) pH_For.textContent = `${h.NO ?? ''} - ${(h.NOME ?? '').toString()}`.trim();
    if (pH_Conta) pH_Conta.textContent = conta || '--';
    if (pH_Doc) pH_Doc.textContent = doc || '--';

    if (!pagamentoLinesBody) return;
    if (!lines.length) {
      pagamentoLinesBody.innerHTML = '<tr><td colspan="5" class="text-muted p-3">Sem linhas.</td></tr>';
      return;
    }
    pagamentoLinesBody.innerHTML = lines.map(l => {
      const ldoc = (l.CDESC || '').toString();
      const ladoc = (l.ADOC || '').toString();
      return `
        <tr>
          <td>${escapeHtml(l.DATALC || '')}</td>
          <td>${escapeHtml(l.DATAVEN || '')}</td>
          <td>${escapeHtml(ldoc)}</td>
          <td>${escapeHtml(ladoc)}</td>
          <td class="text-end fw-bold">${escapeHtml(fmtMoney(l.EVAL))}</td>
        </tr>
      `;
    }).join('');
  }

  function scheduleLoad() {
    clearTimeout(debounce);
    debounce = setTimeout(() => load().catch(err => {
      if (tbody) tbody.innerHTML = `<tr><td colspan="8" class="text-danger p-3">Erro: ${escapeHtml(err?.message || err)}</td></tr>`;
    }), 250);
  }

  payFrom?.addEventListener('change', scheduleLoad);
  payTo?.addEventListener('change', scheduleLoad);
  payLote?.addEventListener('input', scheduleLoad);
  payQ?.addEventListener('input', scheduleLoad);
  payRefresh?.addEventListener('click', (e) => { e.preventDefault(); load(); });
  payClear?.addEventListener('click', (e) => {
    e.preventDefault();
    if (payLote) payLote.value = '';
    if (payQ) payQ.value = '';
    setDefaults();
    load();
  });

  pagamentoSaveDate?.addEventListener('click', async (e) => {
    e.preventDefault();
    if (!currentPostamp) return;
    const dateValue = (pH_DataInput?.value || '').toString().trim();
    if (!dateValue) {
      alert('Indique a data do pagamento.');
      return;
    }

    pagamentoSaveDate.disabled = true;
    try {
      const res = await fetch(`/api/pagamentos/${encodeURIComponent(currentPostamp)}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ RDATA: dateValue })
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.error || res.statusText);
      }
      await res.json().catch(() => ({}));
      pagamentoModal?.hide();
      await load();
    } catch (err) {
      alert(err?.message || err);
    } finally {
      pagamentoSaveDate.disabled = false;
    }
  });

  pagamentoDelete?.addEventListener('click', async (e) => {
    e.preventDefault();
    if (!currentPostamp) return;
    const rno = (pH_Rno?.textContent || '').toString().trim();
    if (!confirm(`Eliminar o pagamento${rno ? ` ${rno}` : ''} e respetivas linhas?`)) return;

    pagamentoDelete.disabled = true;
    try {
      const res = await fetch(`/api/pagamentos/${encodeURIComponent(currentPostamp)}`, { method: 'DELETE' });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.error || res.statusText);
      }
      await res.json().catch(() => ({}));
      pagamentoModal?.hide();
      await load();
    } catch (err) {
      alert(err?.message || err);
    } finally {
      pagamentoDelete.disabled = false;
    }
  });

  table?.addEventListener('click', (e) => {
    const tr = e.target.closest('tr[data-postamp]');
    if (!tr) return;
    const postamp = (tr.dataset.postamp || '').toString().trim();
    if (!postamp) return;
    openPagamento(postamp).catch(err => alert(err?.message || err));
  });

  pagamentoModalEl?.addEventListener('hidden.bs.modal', () => {
    currentPostamp = '';
    if (pagamentoSaveDate) pagamentoSaveDate.disabled = false;
    if (pagamentoDelete) pagamentoDelete.disabled = false;
  });

  setDefaults();
  load();
});
