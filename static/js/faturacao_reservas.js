(function () {
  const state = {
    ano: Number(window.FATRES_ANO_INICIAL || new Date().getFullYear()),
    mes: Number(window.FATRES_MES_INICIAL || (new Date().getMonth() + 1)),
    rows: [],
    selected: new Set(),
    emissor: '',
    serieStamp: '',
    series: [],
  };

  const els = {
    ano: document.getElementById('fatresAno'),
    mes: document.getElementById('fatresMes'),
    prev: document.getElementById('fatresPrev'),
    next: document.getElementById('fatresNext'),
    refresh: document.getElementById('fatresRefresh'),
    body: document.getElementById('fatresBody'),
    checkAll: document.getElementById('fatresCheckAll'),
    stats: document.getElementById('fatresStats'),
    festamp: document.getElementById('fatresFestamp'),
    fts: document.getElementById('fatresFts'),
    emitir: document.getElementById('fatresEmitir'),
    overlay: document.getElementById('fatresOverlay'),
    overlaySub: document.getElementById('fatresOverlaySub'),
    overlayBar: document.getElementById('fatresOverlayBar'),
  };
  let emitStatusPollTimer = null;

  const fmtMoney = (v) => Number(v || 0).toLocaleString('pt-PT', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  const escapeHtml = (s) => String(s || '').replace(/[&<>"']/g, m => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[m]));
  const toDMY = (iso) => {
    const v = String(iso || '').trim();
    if (!v || !/^\d{4}-\d{2}-\d{2}$/.test(v)) return '';
    return `${v.slice(8,10)}-${v.slice(5,7)}-${v.slice(0,4)}`;
  };
  const nowRef = new Date();
  const maxAno = nowRef.getFullYear();
  const maxMes = nowRef.getMonth() + 1;

  function clampToAllowedMonth() {
    if (state.ano > maxAno) {
      state.ano = maxAno;
      state.mes = maxMes;
    } else if (state.ano === maxAno && state.mes > maxMes) {
      state.mes = maxMes;
    }
    state.mes = Math.max(1, Math.min(12, state.mes));
    if (els.ano) els.ano.value = String(state.ano);
    if (els.mes) els.mes.value = String(state.mes);
  }

  function updateNavButtons() {
    const atMax = (state.ano >= maxAno && state.mes >= maxMes);
    if (els.next) els.next.disabled = atMax;
  }

  function updateStats() {
    const total = state.rows.filter(r => Number(r.FATURADO || 0) === 0).length;
    const sel = state.selected.size;
    if (els.stats) els.stats.textContent = `${sel} selecionadas de ${total} por faturar`;
  }

  function syncCheckAll() {
    if (!els.checkAll) return;
    const ids = state.rows.filter(r => Number(r.FATURADO || 0) === 0).map(r => String(r.RSSTAMP || ''));
    if (!ids.length) {
      els.checkAll.checked = false;
      els.checkAll.indeterminate = false;
      return;
    }
    const sel = ids.filter(id => state.selected.has(id)).length;
    els.checkAll.checked = sel === ids.length;
    els.checkAll.indeterminate = sel > 0 && sel < ids.length;
  }

  function render() {
    if (!els.body) return;
    if (!state.rows.length) {
      els.body.innerHTML = '<tr><td colspan="12" class="text-muted p-3">Sem reservas no período.</td></tr>';
      updateStats();
      syncCheckAll();
      return;
    }

    els.body.innerHTML = state.rows.map(r => {
      const id = String(r.RSSTAMP || '');
      const faturado = Number(r.FATURADO || 0) === 1;
      const checked = state.selected.has(id) ? 'checked' : '';
      const dis = faturado ? 'disabled' : '';
      return `
        <tr data-id="${escapeHtml(id)}">
          <td class="text-center"><input type="checkbox" class="fatres-check" ${checked} ${dis}></td>
          <td>${escapeHtml(r.RESERVA)}</td>
          <td>${escapeHtml(r.ALOJAMENTO)}</td>
          <td>${escapeHtml(r.HOSPEDE)}</td>
          <td class="text-center">${escapeHtml(toDMY(r.DATAIN))}</td>
          <td class="text-center">${escapeHtml(toDMY(r.DATAOUT))}</td>
          <td class="text-end">${Number(r.NOITES || 0)}</td>
          <td class="text-end">${Number(r.PAX || 0)}</td>
          <td class="text-end">${fmtMoney(r.ESTADIA)}</td>
          <td class="text-end">${fmtMoney(r.LIMPEZA)}</td>
          <td class="text-center">${
            faturado
              ? (r.FTSTAMP_FATURA
                  ? `<a class="fatres-fatura-link" href="/faturacao/ft/${encodeURIComponent(String(r.FTSTAMP_FATURA || '').trim())}" target="_blank" rel="noopener">${escapeHtml(r.FATURA_LABEL || '')}</a>`
                  : `<span class="fatres-badge-ok">${escapeHtml(r.FATURA_LABEL || 'Emitida')}</span>`)
              : '<span class="fatres-badge-no">Não</span>'
          }</td>
          <td class="text-center">${
            r.FTSTAMP_FATURA
              ? (Number(r.PDF_OK || 0) === 1
                  ? `<a class="fatres-pdf-link" href="/api/faturacao/ft/${encodeURIComponent(String(r.FTSTAMP_FATURA || '').trim())}/pdf" target="_blank" rel="noopener" title="Abrir PDF"><i class="fa-solid fa-file-pdf"></i></a>`
                  : `<button type="button" class="btn btn-link p-0 fatres-pdf-gen" data-ftstamp="${escapeHtml(String(r.FTSTAMP_FATURA || '').trim())}" title="Gerar PDF"><i class="fa-solid fa-file-circle-plus"></i></button>`)
              : ''
          }</td>
        </tr>
      `;
    }).join('');

    els.body.querySelectorAll('tr[data-id]').forEach(tr => {
      const id = tr.getAttribute('data-id') || '';
      const row = state.rows.find(x => String(x.RSSTAMP || '') === id);
      if (!row) return;
      const ck = tr.querySelector('.fatres-check');
      if (!ck) return;
      ck.addEventListener('change', () => {
        if (ck.checked) state.selected.add(id);
        else state.selected.delete(id);
        syncCheckAll();
        updateStats();
      });
    });

    syncCheckAll();
    updateStats();
  }

  function renderSeriesSelect() {
    if (!els.fts) return;
    els.fts.innerHTML = '<option value="">Série de faturação...</option>' + state.series.map(s => {
      const id = String(s.FTSSTAMP || '').trim();
      const txt = `${s.NMDOC || s.NDOC || ''} · ${s.SERIE || ''}${Number(s.NO_SAFT || 0) === 1 ? ' · NO_SAFT' : ''}`;
      return `<option value="${escapeHtml(id)}">${escapeHtml(txt)}</option>`;
    }).join('');
    if (state.serieStamp && state.series.some(x => String(x.FTSSTAMP || '').trim() === state.serieStamp)) {
      els.fts.value = state.serieStamp;
    } else {
      state.serieStamp = '';
    }
  }

  async function loadConfig() {
    if (!els.festamp) return;
    try {
      const qs = new URLSearchParams({ ano: String(state.ano) });
      const res = await fetch(`/api/faturacao/reservas/config?${qs.toString()}`);
      const data = await res.json().catch(() => ({}));
      if (!res.ok || data.error) throw new Error(data.error || 'Erro ao carregar configuração');
      const em = Array.isArray(data.emissores) ? data.emissores : [];
      els.festamp.innerHTML = '<option value="">Entidade emissora...</option>' + em.map(x => {
        const id = String(x.FESTAMP || '').trim();
        const txt = `${x.NOME || ''}${x.NIF ? ` (${x.NIF})` : ''}`;
        return `<option value="${escapeHtml(id)}">${escapeHtml(txt)}</option>`;
      }).join('');
      if (state.emissor && em.some(x => String(x.FESTAMP || '').trim() === state.emissor)) {
        els.festamp.value = state.emissor;
      } else {
        state.emissor = em.length ? String(em[0].FESTAMP || '').trim() : '';
        if (state.emissor) els.festamp.value = state.emissor;
      }
      await loadSeries();
    } catch (e) {
      if (els.festamp) els.festamp.innerHTML = '<option value="">Erro a carregar emissor</option>';
      state.series = [];
      renderSeriesSelect();
    }
  }

  async function loadSeries() {
    if (!els.festamp) return;
    state.emissor = String(els.festamp.value || '').trim();
    if (!state.emissor) {
      state.series = [];
      renderSeriesSelect();
      return;
    }
    try {
      const qs = new URLSearchParams({ festamp: state.emissor, ano: String(state.ano) });
      const res = await fetch(`/api/faturacao/reservas/series?${qs.toString()}`);
      const data = await res.json().catch(() => []);
      if (!res.ok || data.error) throw new Error(data.error || 'Erro ao carregar séries');
      state.series = Array.isArray(data) ? data : [];
      if (!state.serieStamp && state.series.length) state.serieStamp = String(state.series[0].FTSSTAMP || '').trim();
      renderSeriesSelect();
    } catch (_) {
      state.series = [];
      renderSeriesSelect();
    }
  }

  async function waitEmitJob(jobId, fallbackTotal) {
    return await new Promise((resolve, reject) => {
      let ticks = 0;
      const maxTicks = 1800;
      emitStatusPollTimer = setInterval(async () => {
        try {
          ticks += 1;
          if (ticks > maxTicks) {
            clearInterval(emitStatusPollTimer);
            emitStatusPollTimer = null;
            reject(new Error('Tempo limite na emissão.'));
            return;
          }

          const rs = await fetch(`/api/faturacao/reservas/emitir/status?job_id=${encodeURIComponent(jobId)}`);
          const st = await rs.json().catch(() => ({}));
          if (!rs.ok || st.error) {
            clearInterval(emitStatusPollTimer);
            emitStatusPollTimer = null;
            reject(new Error(st.error || 'Erro ao obter progresso'));
            return;
          }

          const pct = Math.max(0, Math.min(100, Number(st.percent || 0)));
          if (els.overlayBar) els.overlayBar.style.width = `${pct}%`;
          const processed = Number(st.processed || 0);
          const total = Number(st.total || fallbackTotal || 0);
          const created = Number(st.created_count || 0);
          const errors = Number(st.errors_count || 0);
          const msg = String(st.message || '').trim() || 'A emitir faturas...';
          if (els.overlaySub) els.overlaySub.textContent = `${msg} (${processed}/${total} · OK ${created} · Erros ${errors})`;

          const stateVal = String(st.state || '').toLowerCase();
          if (stateVal === 'done') {
            clearInterval(emitStatusPollTimer);
            emitStatusPollTimer = null;
            resolve(st.result || {});
            return;
          }
          if (stateVal === 'error') {
            clearInterval(emitStatusPollTimer);
            emitStatusPollTimer = null;
            reject(new Error(st.error || st.message || 'Erro na emissão'));
          }
        } catch (err) {
          clearInterval(emitStatusPollTimer);
          emitStatusPollTimer = null;
          reject(err);
        }
      }, 500);
    });
  }

  async function emitirSelecionadas() {
    const rsstamps = [...state.selected];
    state.emissor = String(els.festamp?.value || '').trim();
    state.serieStamp = String(els.fts?.value || '').trim();
    if (!state.emissor) return alert('Seleciona a entidade emissora.');
    if (!state.serieStamp) return alert('Seleciona a série de faturação.');
    if (!rsstamps.length) return alert('Seleciona pelo menos uma reserva.');
    const ok = confirm(`Emitir ${rsstamps.length} fatura(s) de reserva?`);
    if (!ok) return;

    if (emitStatusPollTimer) { clearInterval(emitStatusPollTimer); emitStatusPollTimer = null; }
    if (els.emitir) els.emitir.disabled = true;
    if (els.overlay) els.overlay.classList.add('show');
    if (els.overlaySub) els.overlaySub.textContent = `A preparar emissão de ${rsstamps.length} reservas...`;
    if (els.overlayBar) els.overlayBar.style.width = '2%';

    try {
      const resStart = await fetch('/api/faturacao/reservas/emitir/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ano: state.ano,
          mes: state.mes,
          festamp: state.emissor,
          ftsstamp: state.serieStamp,
          rsstamps
        })
      });
      const startData = await resStart.json().catch(() => ({}));
      if (!resStart.ok || startData.error) throw new Error(startData.error || 'Erro ao iniciar emissão');
      const jobId = String(startData.job_id || '').trim();
      if (!jobId) throw new Error('Job de emissão inválido');

      const data = await waitEmitJob(jobId, rsstamps.length);
      const created = Array.isArray(data.created) ? data.created.length : 0;
      const errors = Array.isArray(data.errors) ? data.errors.length : 0;
      let msg = `Emissão concluída. Criadas: ${created}. Erros: ${errors}.`;
      if (errors > 0) {
        const preview = (data.errors || []).slice(0, 5).map(e => {
          const resv = e?.RESERVA || e?.RSSTAMP || '';
          return `- ${resv}: ${e?.error || 'Erro'}`;
        }).join('\n');
        if (preview) msg += `\n\nDetalhe:\n${preview}`;
      }
      alert(msg);

      const createdIds = new Set((data.created || []).map(x => String(x?.RSSTAMP || '').trim()).filter(Boolean));
      const createdMap = new Map((data.created || []).map(x => [String(x?.RSSTAMP || '').trim(), x]));
      if (createdIds.size) {
        state.rows = state.rows.map(r => {
          const id = String(r.RSSTAMP || '').trim();
          if (createdIds.has(id)) {
            const it = createdMap.get(id) || {};
            const label = String(it.SERIE_LABEL || '').trim() || `${it.SERIE || ''}/${it.FNO || ''}`.replace(/^\/|\/$/g, '');
            return {
              ...r,
              FATURADO: 1,
              FATURA_LABEL: label || r.FATURA_LABEL || 'Emitida',
              FTSTAMP_FATURA: String(it.FTSTAMP || '').trim() || r.FTSTAMP_FATURA || ''
            };
          }
          return r;
        });
        createdIds.forEach(id => state.selected.delete(id));
        render();
      }

      if (els.overlayBar) els.overlayBar.style.width = '100%';
      if (els.overlaySub) els.overlaySub.textContent = 'Concluído.';
      setTimeout(() => {
        if (els.overlay) els.overlay.classList.remove('show');
        if (els.overlayBar) els.overlayBar.style.width = '0%';
      }, 260);
    } catch (e) {
      if (els.overlaySub) els.overlaySub.textContent = 'Erro na emissão.';
      setTimeout(() => {
        if (els.overlay) els.overlay.classList.remove('show');
        if (els.overlayBar) els.overlayBar.style.width = '0%';
      }, 220);
      alert(e.message || 'Erro a emitir reservas');
    } finally {
      if (emitStatusPollTimer) { clearInterval(emitStatusPollTimer); emitStatusPollTimer = null; }
      if (els.emitir) els.emitir.disabled = false;
    }
  }

  async function gerarPdfLinha(ftstamp, buttonEl) {
    const stamp = String(ftstamp || '').trim();
    if (!stamp) return;
    if (buttonEl) {
      buttonEl.disabled = true;
      buttonEl.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i>';
    }
    try {
      const res = await fetch(`/api/faturacao/ft/${encodeURIComponent(stamp)}/pdf/cache`, { method: 'POST' });
      const data = await res.json().catch(() => ({}));
      if (!res.ok || data.error) throw new Error(data.error || 'Erro a gerar PDF');
      state.rows = state.rows.map(r => {
        if (String(r.FTSTAMP_FATURA || '').trim() === stamp) return { ...r, PDF_OK: 1 };
        return r;
      });
      render();
    } catch (e) {
      if (buttonEl) {
        buttonEl.disabled = false;
        buttonEl.innerHTML = '<i class="fa-solid fa-file-circle-plus"></i>';
      }
      alert(e.message || 'Erro a gerar PDF');
    }
  }

  async function loadData() {
    clampToAllowedMonth();
    updateNavButtons();
    if (!els.body) return;
    els.body.innerHTML = '<tr><td colspan="12" class="text-muted p-3">A carregar...</td></tr>';
    const qs = new URLSearchParams({ ano: String(state.ano), mes: String(state.mes) });
    try {
      const res = await fetch(`/api/faturacao/reservas?${qs.toString()}`);
      const data = await res.json().catch(() => ({}));
      if (!res.ok || data.error) throw new Error(data.error || 'Erro ao carregar reservas');
      state.rows = Array.isArray(data.rows) ? data.rows : [];
      const validIds = new Set(state.rows.filter(r => Number(r.FATURADO || 0) === 0).map(r => String(r.RSSTAMP || '')));
      state.selected = new Set([...state.selected].filter(id => validIds.has(id)));
      render();
    } catch (e) {
      els.body.innerHTML = `<tr><td colspan="12" class="text-danger p-3">${escapeHtml(e.message || 'Erro')}</td></tr>`;
      updateStats();
      syncCheckAll();
    }
  }

  function shiftMonth(delta) {
    let m = state.mes + delta;
    let y = state.ano;
    if (m < 1) { m = 12; y -= 1; }
    if (m > 12) { m = 1; y += 1; }
    if (y > maxAno || (y === maxAno && m > maxMes)) {
      y = maxAno;
      m = maxMes;
    }
    state.mes = m;
    state.ano = y;
    clampToAllowedMonth();
    updateNavButtons();
    if (els.ano) els.ano.value = String(y);
    if (els.mes) els.mes.value = String(m);
    loadData();
  }

  els.prev?.addEventListener('click', () => shiftMonth(-1));
  els.next?.addEventListener('click', () => shiftMonth(1));
  els.refresh?.addEventListener('click', () => {
    state.ano = Number(els.ano?.value || state.ano);
    state.mes = Number(els.mes?.value || state.mes);
    clampToAllowedMonth();
    updateNavButtons();
    loadConfig();
    loadData();
  });
  els.ano?.addEventListener('change', () => {
    state.ano = Number(els.ano?.value || state.ano);
    clampToAllowedMonth();
    updateNavButtons();
    loadConfig();
    loadData();
  });
  els.mes?.addEventListener('change', () => {
    state.mes = Number(els.mes?.value || state.mes);
    clampToAllowedMonth();
    updateNavButtons();
    loadData();
  });
  els.checkAll?.addEventListener('change', () => {
    const on = !!els.checkAll.checked;
    state.rows.forEach(r => {
      if (Number(r.FATURADO || 0) === 1) return;
      const id = String(r.RSSTAMP || '');
      if (!id) return;
      if (on) state.selected.add(id);
      else state.selected.delete(id);
    });
    render();
  });
  els.body?.addEventListener('click', (ev) => {
    const btn = ev.target?.closest?.('.fatres-pdf-gen');
    if (!btn) return;
    ev.preventDefault();
    gerarPdfLinha(btn.getAttribute('data-ftstamp') || '', btn);
  });
  els.festamp?.addEventListener('change', loadSeries);
  els.fts?.addEventListener('change', () => {
    state.serieStamp = String(els.fts?.value || '').trim();
  });
  els.emitir?.addEventListener('click', emitirSelecionadas);

  if (els.ano) els.ano.value = String(state.ano);
  if (els.mes) els.mes.value = String(state.mes);
  clampToAllowedMonth();
  updateNavButtons();
  loadConfig();
  loadData();
})();
