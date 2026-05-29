document.addEventListener('DOMContentLoaded', () => {
  const teamEl = document.getElementById('clexTeam');
  const startEl = document.getElementById('clexStart');
  const endEl = document.getElementById('clexEnd');
  const onlyDoneEl = document.getElementById('clexOnlyDone');
  const onlyWeekendEl = document.getElementById('clexOnlyWeekend');
  const calcBtn = document.getElementById('clexCalculate');
  const pricesOpenBtn = document.getElementById('clexPricesOpen');
  const pricesModalEl = document.getElementById('clexPricesModal');
  const pricesModal = pricesModalEl ? new bootstrap.Modal(pricesModalEl) : null;
  const pricesBody = document.getElementById('clexPricesBody');
  const priceStampEl = document.getElementById('clexPriceStamp');
  const priceTeamEl = document.getElementById('clexPriceTeam');
  const priceTypologyEl = document.getElementById('clexPriceTypology');
  const priceValueEl = document.getElementById('clexPriceValue');
  const priceNewBtn = document.getElementById('clexPriceNew');
  const priceSaveBtn = document.getElementById('clexPriceSave');
  const priceMessageEl = document.getElementById('clexPriceMessage');
  const body = document.getElementById('clexBody');
  const countEl = document.getElementById('clexCount');
  const totalEl = document.getElementById('clexTotal');
  const missingEl = document.getElementById('clexMissing');
  let priceRows = [];
  let priceOptions = { equipas: [], tipologias: [] };

  const fmtMoney = new Intl.NumberFormat('pt-PT', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
    useGrouping: true
  });

  const escapeHtml = (s) => (s ?? '').toString()
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#039;');

  function isoDate(date) {
    return date.toISOString().slice(0, 10);
  }

  function setDefaultDates() {
    const now = new Date();
    const first = new Date(now.getFullYear(), now.getMonth(), 1);
    if (startEl && !startEl.value) startEl.value = isoDate(first);
    if (endEl && !endEl.value) endEl.value = isoDate(now);
  }

  function setSummary(summary = {}) {
    if (countEl) countEl.textContent = String(summary.count ?? 0);
    if (totalEl) totalEl.textContent = fmtMoney.format(Number(summary.total || 0));
    if (missingEl) missingEl.textContent = String(summary.missing_prices ?? 0);
  }

  function renderRows(rows) {
    if (!body) return;
    if (!rows.length) {
      body.innerHTML = '<tr><td colspan="12" class="text-muted p-3">Sem limpezas para os filtros selecionados.</td></tr>';
      return;
    }
    body.innerHTML = rows.map((row) => {
      const done = Number(row.TERMINADA || 0) === 1 || Number(row.TAREFA_TRATADA || 0) === 1;
      const hasPrice = Number(row.TEM_PRECO || 0) === 1;
      const priceLabel = hasPrice ? fmtMoney.format(Number(row.PRECO || 0)) : 'Sem preço';
      const custodia = Number(row.CUSTODIA || 0);
      const custodiaLabel = custodia ? fmtMoney.format(custodia) : '';
      return `
        <tr>
          <td>${escapeHtml(row.DATA || '')}</td>
          <td>${escapeHtml(row.HORA || '')}</td>
          <td title="${escapeHtml(row.ALOJAMENTO || '')}">${escapeHtml(row.ALOJAMENTO || '')}</td>
          <td>${escapeHtml(row.TIPOLOGIA || '')}</td>
          <td>${escapeHtml(row.HOSPEDES ?? 0)}</td>
          <td>${escapeHtml(row.NOITES ?? 0)}</td>
          <td><span class="clex-badge ${done ? 'done' : ''}">${done ? 'Feita' : 'Planeada'}</span></td>
          <td>${escapeHtml(row.HORAINI || '')}</td>
          <td>${escapeHtml(row.HORAFIM || '')}</td>
          <td class="text-end"><span class="${hasPrice ? '' : 'clex-badge missing'}">${escapeHtml(priceLabel)}</span></td>
          <td class="text-end">${escapeHtml(custodiaLabel)}</td>
          <td title="${escapeHtml(row.OBS || '')}">${escapeHtml(row.OBS || '')}</td>
        </tr>
      `;
    }).join('');
  }

  async function fetchJson(url, options = {}) {
    const res = await fetch(url, options);
    const data = await res.json().catch(() => ({}));
    if (!res.ok || data.error) throw new Error(data.error || res.statusText);
    return data;
  }

  async function loadTeams() {
    if (!teamEl) return;
    teamEl.innerHTML = '<option value="">A carregar...</option>';
    try {
      const data = await fetchJson('/api/limpezas_externas/equipas');
      const rows = Array.isArray(data.rows) ? data.rows : [];
      teamEl.innerHTML = '<option value="">Escolhe a equipa</option>' + rows.map((row) => {
        const suffix = row.EXTERNA ? ' · externa' : '';
        return `<option value="${escapeHtml(row.NOME || '')}">${escapeHtml((row.NOME || '') + suffix)}</option>`;
      }).join('');
    } catch (error) {
      teamEl.innerHTML = '<option value="">Erro ao carregar</option>';
      throw error;
    }
  }

  function setPriceMessage(text = '', kind = '') {
    if (!priceMessageEl) return;
    priceMessageEl.textContent = text;
    priceMessageEl.classList.toggle('is-error', kind === 'error');
    priceMessageEl.classList.toggle('is-ok', kind === 'ok');
  }

  function renderPriceOptions() {
    if (priceTeamEl) {
      priceTeamEl.innerHTML = '<option value="">Escolhe a equipa</option>' + (priceOptions.equipas || []).map((row) => {
        const suffix = row.EXTERNA ? ' · externa' : '';
        return `<option value="${escapeHtml(row.NOME || '')}">${escapeHtml((row.NOME || '') + suffix)}</option>`;
      }).join('');
    }
    if (priceTypologyEl) {
      priceTypologyEl.innerHTML = '<option value="">Todas as tipologias</option>' + (priceOptions.tipologias || []).map((tipologia) => (
        `<option value="${escapeHtml(tipologia)}">${escapeHtml(tipologia)}</option>`
      )).join('');
    }
  }

  function resetPriceForm() {
    if (priceStampEl) priceStampEl.value = '';
    if (priceTeamEl) priceTeamEl.value = '';
    if (priceTypologyEl) priceTypologyEl.value = '';
    if (priceValueEl) priceValueEl.value = '';
    setPriceMessage('');
  }

  function fillPriceForm(row) {
    if (priceStampEl) priceStampEl.value = row.TPSTAMP || '';
    if (priceTeamEl) priceTeamEl.value = row.EQUIPA || '';
    if (priceTypologyEl) priceTypologyEl.value = row.TIPOLOGIA || '';
    if (priceValueEl) {
      const n = Number(row.PCUSTO || 0);
      priceValueEl.value = Number.isFinite(n) ? n.toFixed(2) : '';
      priceValueEl.focus();
    }
    setPriceMessage('A editar preço existente.');
  }

  function renderPrices() {
    if (!pricesBody) return;
    if (!priceRows.length) {
      pricesBody.innerHTML = '<tr><td colspan="4" class="text-muted p-3">Sem preços configurados.</td></tr>';
      return;
    }
    pricesBody.innerHTML = priceRows.map((row) => {
      const price = fmtMoney.format(Number(row.PCUSTO || 0));
      const typology = (row.TIPOLOGIA || '').trim() || 'Todas';
      return `
        <tr data-stamp="${escapeHtml(row.TPSTAMP || '')}">
          <td>${escapeHtml(row.EQUIPA || '')}</td>
          <td>${escapeHtml(typology)}</td>
          <td class="text-end">${escapeHtml(price)}</td>
          <td class="text-end">
            <span class="external-cleanings-price-actions">
              <button class="external-cleanings-price-icon" type="button" data-action="edit" title="Editar">
                <i class="fa-solid fa-pen"></i>
              </button>
              <button class="external-cleanings-price-icon is-danger" type="button" data-action="delete" title="Eliminar">
                <i class="fa-solid fa-trash"></i>
              </button>
            </span>
          </td>
        </tr>
      `;
    }).join('');
  }

  async function loadPriceOptions() {
    const data = await fetchJson('/api/limpezas_externas/precos/options');
    priceOptions = {
      equipas: Array.isArray(data.equipas) ? data.equipas : [],
      tipologias: Array.isArray(data.tipologias) ? data.tipologias : []
    };
    renderPriceOptions();
  }

  async function loadPrices() {
    if (pricesBody) pricesBody.innerHTML = '<tr><td colspan="4" class="text-muted p-3">A carregar...</td></tr>';
    const data = await fetchJson('/api/limpezas_externas/precos');
    priceRows = Array.isArray(data.rows) ? data.rows : [];
    renderPrices();
  }

  async function openPricesModal() {
    if (!pricesModal) return;
    pricesModal.show();
    resetPriceForm();
    setPriceMessage('A carregar tabela de preços...');
    try {
      await Promise.all([loadPriceOptions(), loadPrices()]);
      setPriceMessage('');
    } catch (error) {
      setPriceMessage(error.message || String(error), 'error');
      if (pricesBody) pricesBody.innerHTML = '<tr><td colspan="4" class="text-danger p-3">Erro ao carregar preços.</td></tr>';
    }
  }

  async function savePrice() {
    const payload = {
      TPSTAMP: (priceStampEl?.value || '').trim(),
      EQUIPA: (priceTeamEl?.value || '').trim(),
      TIPOLOGIA: (priceTypologyEl?.value || '').trim(),
      PCUSTO: (priceValueEl?.value || '').trim()
    };
    if (!payload.EQUIPA) {
      setPriceMessage('Escolhe a equipa.', 'error');
      return;
    }
    if (payload.PCUSTO === '') {
      setPriceMessage('Indica o preço.', 'error');
      return;
    }
    if (priceSaveBtn) priceSaveBtn.disabled = true;
    try {
      await fetchJson('/api/limpezas_externas/precos', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      await loadPrices();
      resetPriceForm();
      setPriceMessage('Preço gravado.', 'ok');
    } catch (error) {
      setPriceMessage(error.message || String(error), 'error');
    } finally {
      if (priceSaveBtn) priceSaveBtn.disabled = false;
    }
  }

  async function deletePrice(stamp) {
    if (!stamp) return;
    const row = priceRows.find((item) => String(item.TPSTAMP || '') === String(stamp));
    const label = row ? `${row.EQUIPA || ''} / ${(row.TIPOLOGIA || '').trim() || 'Todas'}` : 'este preço';
    if (!confirm(`Eliminar ${label}?`)) return;
    try {
      await fetchJson(`/api/limpezas_externas/precos/${encodeURIComponent(stamp)}`, { method: 'DELETE' });
      await loadPrices();
      if (priceStampEl && priceStampEl.value === stamp) resetPriceForm();
      setPriceMessage('Preço eliminado.', 'ok');
    } catch (error) {
      setPriceMessage(error.message || String(error), 'error');
    }
  }

  async function calculate() {
    const equipa = (teamEl?.value || '').trim();
    const dataIni = startEl?.value || '';
    const dataFim = endEl?.value || '';
    if (!equipa) {
      alert('Escolhe uma equipa.');
      return;
    }
    if (!dataIni || !dataFim) {
      alert('Escolhe o período.');
      return;
    }
    if (body) body.innerHTML = '<tr><td colspan="12" class="text-muted p-3">A calcular...</td></tr>';
    if (calcBtn) calcBtn.disabled = true;
    try {
      const params = new URLSearchParams({
        equipa,
        data_ini: dataIni,
        data_fim: dataFim,
        only_done: onlyDoneEl?.checked ? '1' : '0',
        only_weekend: onlyWeekendEl?.checked ? '1' : '0'
      });
      const res = await fetch(`/api/limpezas_externas?${params.toString()}`);
      const data = await res.json().catch(() => ({}));
      if (!res.ok || data.error) throw new Error(data.error || res.statusText);
      setSummary(data.summary || {});
      renderRows(Array.isArray(data.rows) ? data.rows : []);
    } catch (error) {
      if (body) body.innerHTML = `<tr><td colspan="12" class="text-danger p-3">Erro: ${escapeHtml(error.message || error)}</td></tr>`;
      setSummary({});
    } finally {
      if (calcBtn) calcBtn.disabled = false;
    }
  }

  setDefaultDates();
  loadTeams().catch((error) => {
    if (body) body.innerHTML = `<tr><td colspan="12" class="text-danger p-3">Erro: ${escapeHtml(error.message || error)}</td></tr>`;
  });
  calcBtn?.addEventListener('click', calculate);
  pricesOpenBtn?.addEventListener('click', openPricesModal);
  priceNewBtn?.addEventListener('click', resetPriceForm);
  priceSaveBtn?.addEventListener('click', savePrice);
  pricesBody?.addEventListener('click', (event) => {
    const button = event.target.closest('button[data-action]');
    if (!button) return;
    const tr = button.closest('tr');
    const stamp = tr?.getAttribute('data-stamp') || '';
    const row = priceRows.find((item) => String(item.TPSTAMP || '') === String(stamp));
    if (button.dataset.action === 'edit' && row) fillPriceForm(row);
    if (button.dataset.action === 'delete') deletePrice(stamp);
  });
});
