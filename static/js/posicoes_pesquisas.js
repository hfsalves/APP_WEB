'use strict';

(function () {
  const grid = document.getElementById('posicoesGrid');
  if (!grid) return;

  const btnReload = document.getElementById('btnReload');
  const filterNome = document.getElementById('filterNome');
  const filterTipo = document.getElementById('filterTipo');
  const filterEstado = document.getElementById('filterEstado');
  const badgePendentes = document.getElementById('badgePesquisaPendentes');
  const startDay = (() => {
    const d = new Date();
    d.setHours(0, 0, 0, 0);
    return d;
  })();

  const dateIso = (idx) => {
    const d = new Date(startDay);
    d.setDate(d.getDate() + idx);
    return d.toISOString().slice(0, 10);
  };
  const fmtDate = (iso) => {
    try { return new Date(iso).toLocaleDateString('pt-PT', { day: '2-digit', month: 'short' }); }
    catch (e) { return iso; }
  };
  const dayIndex = (iso) => {
    const d = new Date(iso);
    return Math.round((d - startDay) / (1000 * 60 * 60 * 24));
  };

  let currentBlocks = [];
  let currentPesquisas = [];
  let loading = false;
  const selection = new Map(); // ccusto -> {start:null,end:null,hospedes:2}

  const setLoading = (isLoading) => {
    loading = isLoading;
    if (btnReload) {
      btnReload.disabled = isLoading;
      btnReload.innerHTML = isLoading
        ? '<span class="spinner-border spinner-border-sm" role="status"></span> A carregar...'
        : '<i class="fa-solid fa-rotate me-1"></i> Recarregar';
    }
  };

  const getSel = (ccusto) => {
    if (!selection.has(ccusto)) selection.set(ccusto, { start: null, end: null, hospedes: 2 });
    return selection.get(ccusto);
  };

  const buildDays = (blocks) => {
    const days = Array.from({ length: 30 }, (_, i) => {
      const d = new Date(dateIso(i));
      const dow = d.getDay(); // 0=Domingo
      return {
        dateIso: dateIso(i),
        available: false,
        weekend: dow === 0 || dow === 6,
        occupied: true
      };
    });
    (blocks || []).forEach((b) => {
      const s = dayIndex(b.DataInicio);
      const e = dayIndex(b.DataFim);
      for (let i = Math.max(0, s); i <= Math.min(29, e); i++) {
        days[i].available = true;
        days[i].occupied = false;
      }
    });
    return days;
  };

  const rangeAvailable = (days, startIdx, endIdx) => {
    if (startIdx == null) return false;
    const e = endIdx == null ? startIdx : endIdx;
    for (let i = startIdx; i <= e; i++) {
      if (!days[i]?.available) return false;
    }
    return true;
  };

  const renderTimeline = (ccusto, days, sel) => {
    const renderSlice = (slice, offset) => {
      const header = slice.map((day) => {
        const dateObj = new Date(day.dateIso);
        const num = dateObj.getDate();
        const cls = day.weekend ? 'text-danger' : 'text-muted';
        return `<div class="${cls}">${num}</div>`;
      }).join('');

      const cells = slice.map((day, idx) => {
        const globalIdx = idx + offset;
        const isSel =
          sel.start !== null &&
          globalIdx >= sel.start &&
          globalIdx <= (sel.end ?? sel.start);
        const classes = [
          'day',
          day.available ? 'available' : (day.weekend ? 'weekend-occupied' : 'weekday-occupied'),
          day.weekend ? 'weekend' : '',
          isSel ? 'selected' : '',
          sel.start === globalIdx ? 'selected-start' : '',
          sel.end === globalIdx ? 'selected-end' : ''
        ].filter(Boolean).join(' ');
        return `<div class="${classes}" data-ccusto="${encodeURIComponent(ccusto)}" data-idx="${globalIdx}" title="${fmtDate(day.dateIso)}"></div>`;
      }).join('');

      return `
        <div class="timeline-header mb-1">
          ${header}
        </div>
        <div class="timeline-body mb-2">
          ${cells}
        </div>
      `;
    };

    const firstHalf = days.slice(0, 15);
    const secondHalf = days.slice(15, 30);

    return `
      ${renderSlice(firstHalf, 0)}
      ${renderSlice(secondHalf, 15)}
    `;
  };

  const nightsFromSelection = (sel) => {
    if (sel.start === null) return null;
    const end = sel.end ?? sel.start;
    const nights = (end - sel.start) + 1;
    return Math.max(1, nights);
  };

  const render = () => {
    const groups = groupByAloj(currentBlocks, currentPesquisas);
    const filtered = groups.filter((g) => {
      const nomeMatch = !filterNome?.value
        || g.ccusto.toLowerCase().includes(filterNome.value.trim().toLowerCase());
      const tipoVal = (filterTipo?.value || 'TODOS').toUpperCase();
      const tipoMatch = tipoVal === 'TODOS' || (g.tipo || '').toUpperCase() === tipoVal;
      const estadoVal = (filterEstado?.value || 'TODOS').toUpperCase();
      const estadoMatch = matchEstado(g, estadoVal);
      return nomeMatch && tipoMatch && estadoMatch;
    });
    if (!groups.length) {
      grid.innerHTML = '<div class="text-muted">Sem dados para mostrar.</div>';
      return;
    }
    grid.innerHTML = filtered.map((g) => {
      const sel = getSel(g.ccusto);
      const nights = nightsFromSelection(sel);
      const startLabel = sel.start !== null ? fmtDate(dateIso(sel.start)) : '-';
      return `
        <div class="col-12 col-md-6 col-lg-4">
          <div class="pos-card h-100">
            <div class="header d-flex justify-content-between align-items-start">
              <div>
                <div class="fw-bold">${g.ccusto}</div>
                <div class="text-muted small">${g.nmairbnb || ''}</div>
              </div>
              <span class="badge bg-secondary">${g.tipo || ''}</span>
            </div>
            <div class="body">
              <div class="timeline mb-3" data-ccusto="${encodeURIComponent(g.ccusto)}">
                ${renderTimeline(g.ccusto, g.days, sel)}
              </div>
              <div class="d-flex align-items-center justify-content-between mb-2">
                <div class="small text-muted">Início: <strong>${startLabel}</strong> · Noites: <strong>${nights ?? '-'}</strong></div>
                <div class="d-flex align-items-center gap-2">
                  <button class="btn btn-outline-secondary btn-sm btn-hosp" data-ccusto="${encodeURIComponent(g.ccusto)}" data-delta="-1">-</button>
                  <span class="fw-semibold small" data-hospedes-label="${encodeURIComponent(g.ccusto)}">${sel.hospedes}</span>
                  <button class="btn btn-outline-secondary btn-sm btn-hosp" data-ccusto="${encodeURIComponent(g.ccusto)}" data-delta="1">+</button>
                </div>
              </div>
              <button class="btn btn-primary btn-sm w-100 btn-launch" data-ccusto="${encodeURIComponent(g.ccusto)}" ${sel.start === null ? 'disabled' : ''}>
                Lançar pesquisa
              </button>
              <div class="mt-2 small">
                ${renderPesquisas(g)}
              </div>
            </div>
          </div>
        </div>
      `;
    }).join('');

    bindTimelineClicks(groups);
    bindHospedes();
    bindLaunch(groups);
    updatePendentes();
  };

  const renderPesquisas = (g) => {
    const pcs = (g.pesquisas || [])
      .map((p) => {
        const label = `${fmtDate(p.DATA)} · ${p.NOITES}n`;
        const pos = renderPosBadge(p.PAGINA, p.POSICAO);
        const dt = p.DTPESQUISA ? `<span class="text-muted ms-1">${fmtDate(p.DTPESQUISA)}</span>` : '';
        const hosp = p.HOSPEDES ? `<span class="badge bg-light text-dark ms-2">${p.HOSPEDES} pax</span>` : '';
        const actions = `
          <button class="btn btn-outline-danger btn-icon-mini ms-2 btn-del" data-stamp="${p.PESQUISASSTAMP || ''}" title="Eliminar">
            <i class="fa-solid fa-trash"></i>
          </button>
          <button class="btn btn-outline-primary btn-icon-mini ms-1 btn-relaunch" data-stamp="${p.PESQUISASSTAMP || ''}" title="Relançar">
            <i class="fa-solid fa-rotate-right"></i>
          </button>
        `;
        return `<div class="d-flex align-items-center mb-1">${label}${pos}${hosp}${dt}${actions}</div>`;
      });
    if (!pcs.length) return '<span class="text-muted">Sem pesquisas registadas.</span>';
    return pcs.join('');
  };

  const renderPosBadge = (pagina, posicao) => {
    if (Number(pagina) === 99 && Number(posicao) === 99) {
      return '<span class="badge bg-warning text-dark ms-2">Não encontrado</span>';
    }
    if ((!pagina && !posicao) || (Number(pagina) === 0 && Number(posicao) === 0)) {
      return '<span class="badge bg-secondary text-white ms-2">Em pesquisa...</span>';
    }
    const pag = Number(pagina) || 0;
    const pos = Number(posicao) || 0;
    const color = paginaColor(pag);
    return `<span class="badge ${color} ms-2">P${pag || '?'} #${pos || '?'}</span>`;
  };

  const paginaColor = (pag) => {
    if (pag <= 1) return 'bg-success text-white';
    if (pag <= 3) return 'bg-success text-white';
    if (pag <= 6) return 'bg-warning text-dark';
    if (pag <= 10) return 'bg-warning text-dark';
    if (pag <= 15) return 'bg-danger text-white';
    return 'bg-secondary text-white';
  };

  const bindHospedes = () => {
    grid.querySelectorAll('.btn-hosp').forEach((btn) => {
      btn.addEventListener('click', () => {
        const ccusto = decodeURIComponent(btn.dataset.ccusto || '');
        const delta = Number(btn.dataset.delta || 0);
        const sel = getSel(ccusto);
        sel.hospedes = Math.max(1, sel.hospedes + delta);
        render();
      });
    });
  };

  const bindTimelineClicks = (groups) => {
    grid.querySelectorAll('.timeline .day').forEach((cell) => {
      cell.addEventListener('click', () => {
        const ccusto = decodeURIComponent(cell.dataset.ccusto || '');
        const idx = Number(cell.dataset.idx);
        const group = groups.find((g) => g.ccusto === ccusto);
        if (!group || !group.days[idx]?.available) return;

        const sel = getSel(ccusto);
        if (sel.start === null || (sel.start !== null && sel.end !== null)) {
          sel.start = idx;
          sel.end = null;
        } else {
          if (idx < sel.start) {
            sel.start = idx;
            sel.end = null;
          } else {
            if (rangeAvailable(group.days, sel.start, idx)) {
              sel.end = idx;
            } else {
              sel.start = idx;
              sel.end = null;
            }
          }
        }
        render();
      });
    });
  };

  const bindLaunch = (groups) => {
    grid.querySelectorAll('.btn-launch').forEach((btn) => {
      btn.addEventListener('click', async () => {
        if (loading) return;
        const ccusto = decodeURIComponent(btn.dataset.ccusto || '');
        const group = groups.find((g) => g.ccusto === ccusto);
        if (!group) return;
        const sel = getSel(ccusto);
        if (sel.start === null) return;
        const nights = nightsFromSelection(sel);
        const startIso = dateIso(sel.start);
        const hospedes = sel.hospedes;
        setLoading(true);
        try {
          const res = await fetch('/api/pesquisas/posicoes', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              ccusto,
              nmairbnb: group.nmairbnb,
              data: startIso,
              noites: nights,
              hospedes
            })
          });
          const out = await res.json();
          if (!res.ok || out.error) {
            alert(out.error || 'Erro ao registar a pesquisa');
          } else {
            await loadData();
          }
        } catch (e) {
          alert('Erro ao registar a pesquisa');
        } finally {
          setLoading(false);
        }
      });
    });

    grid.querySelectorAll('.btn-del').forEach((btn) => {
      btn.addEventListener('click', async () => {
        if (loading) return;
        const stamp = btn.dataset.stamp;
        if (!stamp) return;
        const confirmDel = confirm('Eliminar esta pesquisa?');
        if (!confirmDel) return;
        setLoading(true);
        try {
          const res = await fetch(`/api/pesquisas/posicoes/${encodeURIComponent(stamp)}`, { method: 'DELETE' });
          const out = await res.json();
          if (!res.ok || out.error) alert(out.error || 'Erro ao eliminar');
          else await loadData();
        } catch (e) {
          alert('Erro ao eliminar');
        } finally {
          setLoading(false);
        }
      });
    });

    grid.querySelectorAll('.btn-relaunch').forEach((btn) => {
      btn.addEventListener('click', async () => {
        if (loading) return;
        const stamp = btn.dataset.stamp;
        if (!stamp) return;
        setLoading(true);
        try {
          const res = await fetch(`/api/pesquisas/posicoes/${encodeURIComponent(stamp)}/relaunch`, { method: 'POST' });
          const out = await res.json();
          if (!res.ok || out.error) alert(out.error || 'Erro ao relançar');
          else await loadData();
        } catch (e) {
          alert('Erro ao relançar');
        } finally {
          setLoading(false);
        }
      });
    });
  };

  const groupByAloj = (blocks, pesquisas) => {
    const map = new Map();
    blocks.forEach((r) => {
      if (!r.DataInicio || !r.DataFim) return;
      if (!map.has(r.CCUSTO)) {
        map.set(r.CCUSTO, {
          ccusto: r.CCUSTO,
          tipo: r.TIPO,
          nmairbnb: r.NMAIRBNB,
          blocks: [],
          pesquisas: []
        });
      }
      map.get(r.CCUSTO).blocks.push(r);
    });

    (pesquisas || []).forEach((p) => {
      const key = p.CCUSTO;
      if (!map.has(key)) {
        map.set(key, {
          ccusto: key,
          tipo: '',
          nmairbnb: '',
          blocks: [],
          pesquisas: []
        });
      }
      map.get(key).pesquisas.push(p);
    });

    return Array.from(map.values()).map((g) => ({
      ...g,
      days: buildDays(g.blocks)
    }));
  };

  const loadData = async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/pesquisas/posicoes');
      const out = await res.json();
      if (!res.ok || out.error) {
        grid.innerHTML = `<div class="text-danger">${out.error || 'Erro ao carregar.'}</div>`;
        return;
      }
      currentBlocks = out.blocks || out.rows || [];
      currentPesquisas = out.pesquisas || [];
      render();
    } catch (e) {
      grid.innerHTML = '<div class="text-danger">Erro ao carregar.</div>';
    } finally {
      setLoading(false);
    }
  };

  if (btnReload) btnReload.addEventListener('click', loadData);
  if (filterNome) filterNome.addEventListener('input', () => render());
  if (filterTipo) filterTipo.addEventListener('change', () => render());
  if (filterEstado) filterEstado.addEventListener('change', () => render());
  loadData();

  const updatePendentes = () => {
    if (!badgePendentes) return;
    const pend = (currentPesquisas || []).filter((p) => (!p.PAGINA && !p.POSICAO) || (Number(p.PAGINA) === 0 && Number(p.POSICAO) === 0));
    badgePendentes.textContent = `Em pesquisa: ${pend.length}`;
  };

  const pesquisaStatus = (p) => {
    if (Number(p.PAGINA) === 99 && Number(p.POSICAO) === 99) return 'NAO_ENCONTRADO';
    if ((!p.PAGINA && !p.POSICAO) || (Number(p.PAGINA) === 0 && Number(p.POSICAO) === 0)) return 'EM_PESQUISA';
    const pag = Number(p.PAGINA) || 0;
    if (pag > 3 && pag <= 15) return 'ALERTA';
    return 'OK';
  };

  const matchEstado = (group, estadoVal) => {
    if (estadoVal === 'TODOS') return true;
    const has = (group.pesquisas || []).some((p) => pesquisaStatus(p) === estadoVal);
    return has;
  };
})();
