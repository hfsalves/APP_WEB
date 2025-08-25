// static/js/monitor.js

document.addEventListener('DOMContentLoaded', () => {
  const colAtrasadas = document.getElementById('tarefas-atrasadas');
  const colHoje = document.getElementById('tarefas-hoje');
  const colFuturas = document.getElementById('tarefas-futuras');
  const colTratadas = document.getElementById('tarefas-tratadas');
  const modalElement = document.getElementById('tarefaModal');
  const modal = modalElement ? new bootstrap.Modal(modalElement) : null;
  const tarefaDescricao = document.getElementById('tarefaDescricao');
  const tarefaInfo = document.getElementById('tarefaInfo');
  const btnTratar = document.getElementById('btnTratar');
  const btnReabrir = document.getElementById('btnReabrir');
  // botões Reagendar e Nota removidos do UI
  
  console.log('IS_MN_ADMIN =', typeof IS_MN_ADMIN !== 'undefined' ? IS_MN_ADMIN : '(undefined)');
  console.log('mn-nao-agendadas element =', !!document.getElementById('mn-nao-agendadas'));

  let tarefaSelecionada = null;

  

  const hoje = new Date();
  const start = new Date(hoje);
  start.setDate(start.getDate() - 7);
  const end = new Date(hoje);
  end.setDate(end.getDate() + 7);
  const startStr = start.toISOString().slice(0, 10);
  const endStr = end.toISOString().slice(0, 10);

  const CURRENT_USER = window.CURRENT_USER;

  //fetch(`/generic/api/calendar_tasks?start=${startStr}&end=${endStr}`)
  fetch(`/generic/api/monitor_tasks`)
    .then(res => res.json())
    .then(data => {
      colAtrasadas.innerHTML = '';
      colHoje.innerHTML = '';
      colFuturas.innerHTML = '';
      colTratadas.innerHTML = '';
      const hojeStr = hoje.toISOString().slice(0, 10);
      let cntAtrasadas = 0, cntHoje = 0, cntFuturas = 0, cntTratadas = 0;
      const gruposFuturas = new Map();

    data.forEach(t => {
        const dataFormatada = new Date(t.DATA + 'T' + t.HORA);
        const hhmm = t.HORA;
        const ddmm = dataFormatada.toLocaleDateString('pt-PT');
        // Determina título do card: se não tiver origem e não tiver alojamento, mostrar "Tarefa"
        const _semOrigem = !t.ORIGEM || String(t.ORIGEM).trim() === '';
        const _semAloj = !t.ALOJAMENTO || String(t.ALOJAMENTO).trim() === '';
        const _tituloCard = (_semOrigem && _semAloj) ? 'Tarefa' : (t.ALOJAMENTO || '');
        // Se não tiver ORIGEM e nem ALOJAMENTO, mostrar "Tarefa" como título
        const origemVazia = !t.ORIGEM || String(t.ORIGEM).trim() === '';
        const alojVazio = !t.ALOJAMENTO || String(t.ALOJAMENTO).trim() === '';
        const displayAloj = (origemVazia && alojVazio) ? 'Tarefa' : (t.ALOJAMENTO || '');

        const bloco = document.createElement('div');
        bloco.className = 'card tarefa-card mb-2 shadow-sm';

        let texto;
        if (t.DATA === hojeStr) {
          texto = `<strong class="tarefa-alojamento">${_tituloCard}</strong><br><span class='text-muted small'>${hhmm} - ${t.TAREFA}</span>`;
        } else {
          texto = `<strong class="tarefa-alojamento">${_tituloCard}</strong><br><span class='text-muted small'>${ddmm} ${hhmm} - ${t.TAREFA}</span>`;
        }

        // Override do título quando não tem origem e não tem alojamento
        if (origemVazia && alojVazio) {
          if (t.DATA === hojeStr) {
            texto = `<strong class=\"tarefa-alojamento\">Tarefa</strong><br><span class='text-muted small'>${hhmm} - ${t.TAREFA}</span>`;
          } else {
            texto = `<strong class=\"tarefa-alojamento\">Tarefa</strong><br><span class='text-muted small'>${ddmm} ${hhmm} - ${t.TAREFA}</span>`;
          }
        }

        let icone = '';
        if (t.TRATADO) {
          icone = '<i class="fas fa-check-circle text-success float-end"></i>';
        } else if (t.DATA < hojeStr) {
          icone = '<i class="fas fa-exclamation-circle text-danger float-end"></i>';
        }

        // Ícone da origem no canto (direita)
        let origemIcon = '';
        switch ((t.ORIGEM || '').toUpperCase()) {
          case 'MN': origemIcon = '<i class="fa-solid fa-wrench text-dark float-end ms-1" title="Manutenção"></i>'; break;
          case 'LP': origemIcon = '<i class="fa-solid fa-broom text-dark float-end ms-1" title="Limpeza"></i>'; break;
          case 'FS': origemIcon = '<i class="fa-solid fa-cart-shopping text-dark float-end ms-1" title="Falta de Stock"></i>'; break;
          default:
            if (!t.ORIGEM || String(t.ORIGEM).trim() === '') {
              origemIcon = '<i class="fa-solid fa-list-check text-dark float-end ms-1" title="Tarefa"></i>';
            }
            break;
        }
        bloco.innerHTML = `<div class=\"card-body p-2\">${origemIcon}${icone}<div>${texto}</div></div>`;
        // Garante badge do utilizador no topo direito
        try {
          const bodyEl = bloco.querySelector('.card-body');
          if (bodyEl) {
            const nm = t.UTILIZADOR_NOME || t.UTILIZADOR || '';
            const cor = t.UTILIZADOR_COR || '#6c757d';
            if (nm && !bodyEl.querySelector('.user-badge')) {
              const badge = document.createElement('span');
              badge.className = 'user-badge float-end ms-1';
              badge.title = nm;
              badge.style.backgroundColor = cor;
              badge.style.color = '#fff';
              badge.style.borderRadius = '8px';
              badge.style.padding = '2px 6px';
              badge.style.fontSize = '.70rem';
              badge.style.lineHeight = '1.1';
              badge.style.whiteSpace = 'nowrap';
              badge.textContent = nm;
              bodyEl.prepend(badge);
            }
          }
        } catch(_) {}

        bloco.addEventListener('click', () => {
            tarefaSelecionada = t;
            try { window.tarefaSelecionada = t; } catch(_) {}
            tarefaDescricao.textContent = `${t.TAREFA} (${t.HORA} - ${t.ALOJAMENTO})`;

            // buscar info adicional do SQL
            fetch(`/api/tarefa_info/${t.TAREFASSTAMP}`)
                .then(res => res.json())
                .then(data => {
                    const extraInfo = data.info || '';
                    tarefaDescricao.innerHTML = `<strong>${t.TAREFA} (${t.HORA} - ${t.ALOJAMENTO})</strong><br><br>${extraInfo.replace(/\n/g, '<br>')}`;
                })
                .catch(err => console.error('Erro ao buscar info da tarefa', err));

            if (btnTratar) btnTratar.style.display = 'none';
            if (btnReabrir) btnReabrir.style.display = 'none';

            if (!t.TRATADO) {
                if (btnTratar) btnTratar.style.display = 'inline-block';
            } else {
                if (btnReabrir) btnReabrir.style.display = 'inline-block';
            }

            // Botão Abrir (no modal) – controlado por origem e permissões
            try {
              const btnAbrir = document.getElementById('btnAbrirTarefa');
              if (btnAbrir) {
                const oi = getOpenInfo(t);
                if (oi.can) {
                  btnAbrir.style.display = 'inline-block';
                  btnAbrir.onclick = () => { window.location.href = oi.url; };
                } else {
                  btnAbrir.style.display = 'none';
                  btnAbrir.onclick = null;
                }
              }
            } catch(_){}

            if (modal) modal.show();
        });



        if (!t.TRATADO) {
          if (t.DATA < hojeStr) {
            colAtrasadas.appendChild(bloco); cntAtrasadas++;
          } else if (t.DATA === hojeStr) {
            colHoje.appendChild(bloco); cntHoje++;
          } else {
            // Agrupa por diferença de dias
            const base = new Date(hojeStr + 'T00:00:00');
            const dataObj = new Date(t.DATA + 'T00:00:00');
            const diffDays = Math.round((dataObj - base) / (1000*60*60*24));
            if (diffDays >= 1) {
              let grp = gruposFuturas.get(diffDays);
              if (!grp) {
                const header = document.createElement('div');
                header.className = 'bg-light border rounded px-2 py-1 mb-2 d-flex justify-content-between align-items-center';
                const title = diffDays === 1 ? 'Amanhã' : `Daqui a ${diffDays} dias`;
                header.innerHTML = `<span class=\"fw-semibold\">${title}</span>`;
                const container = document.createElement('div');
                container.className = 'mb-3';
                colFuturas.appendChild(header);
                colFuturas.appendChild(container);
                grp = {container};
                gruposFuturas.set(diffDays, grp);
              }
              // Ajusta label: dia semana + dd/mm hh:mm
              const dow = ['Dom','Seg','Ter','Qua','Qui','Sex','Sáb'];
              const d = new Date(t.DATA + 'T' + t.HORA);
              const dd = String(d.getDate()).padStart(2,'0');
              const mm = String(d.getMonth()+1).padStart(2,'0');
              const lbl = `${dow[d.getDay()]} ${dd}/${mm} ${hhmm}`;
              const body = bloco.querySelector('.card-body > div');
              if (body) body.innerHTML = `<strong class=\"tarefa-alojamento\">${displayAloj}</strong><br><span class='text-muted small'>${lbl} - ${t.TAREFA}</span>`;
              // Override quando não tem origem nem alojamento: mostra "Tarefa"
              if (origemVazia && alojVazio && body) {
                body.innerHTML = `<strong class=\"tarefa-alojamento\">Tarefa</strong><br><span class='text-muted small'>${lbl} - ${t.TAREFA}</span>`;
              }
              grp.container.appendChild(bloco);
              cntFuturas++;
            }
          }
        } else {
          colTratadas.appendChild(bloco); cntTratadas++;
        }
      });
      // Atualiza contadores nos cabeçalhos
      const setCount = (id, v) => { const el = document.getElementById(id); if (el) el.textContent = v; };
      setCount('count-atrasadas', cntAtrasadas);
      setCount('count-hoje', cntHoje);
      setCount('count-futuras', cntFuturas);
      setCount('count-tratadas', cntTratadas);
    })
    .catch(err => alert('Erro ao carregar tarefas: ' + err));

  if (btnTratar) {
    btnTratar.addEventListener('click', async () => {
      const sel = (typeof window !== 'undefined' && window.tarefaSelecionada) ? window.tarefaSelecionada : tarefaSelecionada;
      if (!sel) return;
      try {
        const resp = await fetch('/generic/api/tarefas/tratar', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ id: sel.TAREFASSTAMP })
        });
        const js = await resp.json().catch(() => ({}));
        if (!resp.ok || js.ok === false) throw new Error(js.error || 'Falha ao marcar tarefa.');
        window.location.reload();
      } catch (e) {
        alert(e.message || 'Erro ao marcar tarefa como tratada.');
      }
    });
  }

  // Reagendar e Nota foram removidos

  if (btnReabrir) {
    btnReabrir.addEventListener('click', () => {
      if (!tarefaSelecionada) return;
      fetch('/generic/api/tarefas/reabrir', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id: tarefaSelecionada.TAREFASSTAMP })
      }).then(() => window.location.reload());
    });
  }

  // Filtro: UI toggle by clicking the block
  const onlyMineChk = document.getElementById('onlyMineChk');
  const onlyMineBlock = document.getElementById('onlyMineBlock');
  const onlyMineState = document.getElementById('onlyMineState');
  function updateOnlyMineUI() {
    if (!onlyMineChk || !onlyMineBlock) return;
    if (onlyMineChk.checked) {
      onlyMineBlock.classList.add('active');
      if (onlyMineState) onlyMineState.textContent = 'Ativo';
    } else {
      onlyMineBlock.classList.remove('active');
      if (onlyMineState) onlyMineState.textContent = 'Inativo';
    }
  }
  if (onlyMineBlock && onlyMineChk) {
    onlyMineBlock.addEventListener('click', (e) => {
      // avoid double toggling if clicking directly checkbox
      if (e.target && e.target.id === 'onlyMineChk') return;
      onlyMineChk.checked = !onlyMineChk.checked;
      onlyMineChk.dispatchEvent(new Event('change'));
    });
    onlyMineChk.addEventListener('change', updateOnlyMineUI);
    updateOnlyMineUI();
    // Trigger initial data load using current state
    try { onlyMineChk.dispatchEvent(new Event('change')); } catch(_) {}
  }

  // =========================
  // Filtro: Apenas as minhas tarefas (atualiza contadores e grupos)
  // =========================
  function renderTasksUI(list) {
    const data = Array.isArray(list) ? list : [];
    colAtrasadas.innerHTML = '';
    colHoje.innerHTML = '';
    colFuturas.innerHTML = '';
    colTratadas.innerHTML = '';
    const hojeStr = new Date().toISOString().slice(0, 10);

    let cntAtrasadas = 0, cntHoje = 0, cntFuturas = 0, cntTratadas = 0;
    const gruposFuturas = new Map();

    data.forEach(t => {
      const dataFormatada = new Date(t.DATA + 'T' + t.HORA);
      const hhmm = t.HORA;
      const ddmm = dataFormatada.toLocaleDateString('pt-PT');
      // Título do card: se não tiver origem e nem alojamento, mostrar "Tarefa"
      const _semOrigem = !t.ORIGEM || String(t.ORIGEM).trim() === '';
      const _semAloj = !t.ALOJAMENTO || String(t.ALOJAMENTO).trim() === '';
      const _tituloCard = (_semOrigem && _semAloj) ? 'Tarefa' : (t.ALOJAMENTO || '');

      const bloco = document.createElement('div');
      bloco.className = 'card tarefa-card mb-2 shadow-sm';

      let texto;
      if (t.DATA === hojeStr) {
        texto = `<strong class="tarefa-alojamento">${_tituloCard}</strong><br><span class='text-muted small'>${hhmm} - ${t.TAREFA}</span>`;
      } else {
        texto = `<strong class="tarefa-alojamento">${_tituloCard}</strong><br><span class='text-muted small'>${ddmm} ${hhmm} - ${t.TAREFA}</span>`;
      }

      let icone = '';
      if (t.TRATADO) {
        icone = '<i class="fas fa-check-circle text-success float-end"></i>';
      } else if (t.DATA < hojeStr) {
        icone = '<i class="fas fa-exclamation-circle text-danger float-end"></i>';
      }

      // Badge do utilizador
      const esc = (s) => String(s ?? '').replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
      const userName = t.UTILIZADOR_NOME || t.UTILIZADOR || '';
      const userColor = t.UTILIZADOR_COR || '#6c757d';
      const userBadge = userName
        ? `<span class=\"user-badge float-end ms-1\" title=\"${esc(userName)}\" style=\"background-color:${esc(userColor)};color:#fff;border-radius:8px;padding:2px 6px;font-size:.70rem;line-height:1.1;white-space:nowrap;\">${esc(userName)}</span>`
        : '';

      let origemIcon = '';
      switch ((t.ORIGEM || '').toUpperCase()) {
        case 'MN': origemIcon = '<i class="fa-solid fa-wrench text-dark float-end ms-1" title="Manutenção"></i>'; break;
        case 'LP': origemIcon = '<i class="fa-solid fa-broom text-dark float-end ms-1" title="Limpeza"></i>'; break;
        case 'FS': origemIcon = '<i class="fa-solid fa-cart-shopping text-dark float-end ms-1" title="Falta de Stock"></i>'; break;
        default:
          if (!t.ORIGEM || String(t.ORIGEM).trim() === '') {
            origemIcon = '<i class="fa-solid fa-list-check text-dark float-end ms-1" title="Tarefa"></i>';
          }
          break;
      }

      bloco.innerHTML = `<div class="card-body p-2">${userBadge}${origemIcon}${icone}<div>${texto}</div></div>`;

      bloco.addEventListener('click', () => {
        tarefaSelecionada = t;
        try { window.tarefaSelecionada = t; } catch(_) {}
        tarefaDescricao.textContent = `${t.TAREFA} (${t.HORA} - ${t.ALOJAMENTO})`;

        fetch(`/api/tarefa_info/${t.TAREFASSTAMP}`)
          .then(res => res.json())
          .then(data => {
            const extraInfo = data.info || '';
            tarefaDescricao.innerHTML = `<strong>${t.TAREFA} (${t.HORA} - ${t.ALOJAMENTO})</strong><br><br>${extraInfo.replace(/\n/g, '<br>')}`;
          })
          .catch(err => console.error('Erro ao buscar info da tarefa', err));

        if (btnTratar) btnTratar.style.display = 'none';
        if (btnReabrir) btnReabrir.style.display = 'none';
        if (!t.TRATADO) { if (btnTratar) btnTratar.style.display = 'inline-block'; }
        else { if (btnReabrir) btnReabrir.style.display = 'inline-block'; }
        // Botão Abrir (no modal) – por origem/permissões
        try {
          const btnAbrir = document.getElementById('btnAbrirTarefa');
          if (btnAbrir) {
            const oi = getOpenInfo(t);
            if (oi.can) {
              btnAbrir.style.display = 'inline-block';
              btnAbrir.onclick = () => { window.location.href = oi.url; };
            } else {
              btnAbrir.style.display = 'none';
              btnAbrir.onclick = null;
            }
          }
        } catch(_){}
        if (modal) modal.show();
      });

      if (!t.TRATADO) {
        if (t.DATA < hojeStr) {
          colAtrasadas.appendChild(bloco); cntAtrasadas++;
        } else if (t.DATA === hojeStr) {
          colHoje.appendChild(bloco); cntHoje++;
        } else {
          const base = new Date(hojeStr + 'T00:00:00');
          const dataObj = new Date(t.DATA + 'T00:00:00');
          const diffDays = Math.round((dataObj - base) / (1000*60*60*24));
          if (diffDays >= 1) {
            let grp = gruposFuturas.get(diffDays);
            if (!grp) {
              const header = document.createElement('div');
              header.className = 'bg-light border rounded px-2 py-1 mb-2 d-flex justify-content-between align-items-center';
              const title = diffDays === 1 ? 'Amanhã' : `Daqui a ${diffDays} dias`;
              header.innerHTML = `<span class=\"fw-semibold\">${title}</span>`;
              const container = document.createElement('div');
              container.className = 'mb-3';
              colFuturas.appendChild(header);
              colFuturas.appendChild(container);
              grp = {container};
              gruposFuturas.set(diffDays, grp);
            }
            const dow = ['Dom','Seg','Ter','Qua','Qui','Sex','Sáb'];
            const d = new Date(t.DATA + 'T' + t.HORA);
            const dd = String(d.getDate()).padStart(2,'0');
            const mm = String(d.getMonth()+1).padStart(2,'0');
            const lbl = `${dow[d.getDay()]} ${dd}/${mm} ${hhmm}`;
            const body = bloco.querySelector('.card-body > div');
              if (body) body.innerHTML = `<strong class=\"tarefa-alojamento\">${_tituloCard}</strong><br><span class='text-muted small'>${lbl} - ${t.TAREFA}</span>`;
            grp.container.appendChild(bloco);
            cntFuturas++;
          }
        }
      } else {
        colTratadas.appendChild(bloco); cntTratadas++;
      }
    });

    const setCount = (id, v) => { const el = document.getElementById(id); if (el) el.textContent = v; };
    setCount('count-atrasadas', cntAtrasadas);
    setCount('count-hoje', cntHoje);
    setCount('count-futuras', cntFuturas);
    setCount('count-tratadas', cntTratadas);
  }

  const onlyMineChk2 = document.getElementById('onlyMineChk');
  if (onlyMineChk2) {
    onlyMineChk2.addEventListener('change', async () => {
      try {
        const onlyMine = onlyMineChk2.checked ? '1' : '0';
        const resp = await fetch(`/generic/api/monitor_tasks_filtered?only_mine=${onlyMine}`);
        const js = await resp.json();
        renderTasksUI(Array.isArray(js) ? js : (js.rows || []));
      } catch (e) {
        console.error('Erro ao aplicar filtro:', e);
      }
    });
  }
});

// FAB menu toggle
document.getElementById('openFabMenu').onclick = function(e) {
  e.stopPropagation();
  const menu = document.getElementById('fabMenu');
  menu.style.display = (menu.style.display === 'block' ? 'none' : 'block');
};

// Fecha ao clicar fora
document.addEventListener('click', function(e) {
  const menu = document.getElementById('fabMenu');
  if (menu) menu.style.display = 'none';
});

// =========================
// Notas de Reserva (popup)
// =========================
document.addEventListener('DOMContentLoaded', () => {
  const btnOpenNR = document.getElementById('openNotasReserva');
  if (!btnOpenNR) return;
  btnOpenNR.addEventListener('click', () => {
    const modalEl = document.getElementById('nrModal');
    if (!modalEl) return;
    const modal = bootstrap.Modal.getOrCreateInstance(modalEl);
    // limpa estado
    const resDiv = document.getElementById('nrResultados');
    const obsArea = document.getElementById('nrObsArea');
    const obs = document.getElementById('nrObs');
    const din = document.getElementById('nrDataIn');
    const res = document.getElementById('nrReserva');
    if (resDiv) resDiv.innerHTML = '';
    if (obsArea) obsArea.style.display = 'none';
    if (obs) obs.value = '';
    if (din) din.value = '';
    if (res) res.value = '';
    modal.show();
  });

  async function nrBuscar() {
    const din = document.getElementById('nrDataIn').value;
    const reserva = document.getElementById('nrReserva').value.trim();
    const out = document.getElementById('nrResultados');
    const obsArea = document.getElementById('nrObsArea');
    const obs = document.getElementById('nrObs');
    if (out) out.innerHTML = '<div class="text-muted small">A procurar…</div>';

    try {
      let url = '';
      if (din) url = `/generic/api/rs/search?date=${encodeURIComponent(din)}`;
      else if (reserva) url = `/generic/api/rs/search?reserva=${encodeURIComponent(reserva)}`;
      else {
        if (out) out.innerHTML = '<div class="text-muted small">Indica a data de check‑in ou o código da reserva.</div>';
        return;
      }
      const r = await fetch(url);
      const js = await r.json();
      const rows = Array.isArray(js) ? js : (js.rows || []);
      if (!rows.length) {
        out.innerHTML = '<div class="text-muted small">Sem resultados.</div>';
        return;
      }
      // render cards
      out.innerHTML = '';
      const esc = (s) => String(s ?? '').replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
      rows.forEach(row => {
        const card = document.createElement('div');
        card.className = 'card tarefa-card mb-2 shadow-sm nr-card';
        const hospedes = (Number(row.ADULTOS||0) + Number(row.CRIANCAS||0)) || 0;
        const dataIn = row.DATAIN || '';
        const canOpenRS = (typeof window !== 'undefined' && window.CAN_OPEN_RS) ? true : false;
        const openBtn = (canOpenRS && row.RSSTAMP)
          ? `<a class=\"btn btn-sm btn-primary\" href=\"/generic/form/RS/${encodeURIComponent(row.RSSTAMP)}?return_to=/monitor\">Abrir</a>`
          : '';
        card.innerHTML = `
          <div class="card-body p-2">
            <div class="d-flex justify-content-between align-items-center">
              <strong class="tarefa-alojamento">${esc(row.ALOJAMENTO||'')}</strong>
              <div class="d-flex align-items-center gap-2">
                <span class="badge bg-secondary">${(row.RESERVA||'')}</span>
                ${openBtn}
              </div>
            </div>
            <div class="small mt-1"><span class="text-muted">Hóspede:</span> ${esc(row.NOME||'')}</div>
            <div class="text-muted small mt-1">Check‑in: ${dataIn} • Noites: ${row.NOITES||0} • Hóspedes: ${hospedes}</div>
          </div>
        `;
        card.addEventListener('click', () => {
          // visual de seleção
          const container = out;
          if (container) {
            container.querySelectorAll('.nr-card.nr-selected').forEach(el => el.classList.remove('nr-selected'));
          }
          card.classList.add('nr-selected');
          // seleciona
          window.NR_SELECTED = { reserva: row.RESERVA, obs: row.OBS||'', berco: row.BERCO||0, sofacama: row.SOFACAMA||0 };
          if (obs) obs.value = row.OBS || '';
          try {
            const b = document.getElementById('nrBerco');
            const s = document.getElementById('nrSofa');
            if (b) b.checked = !!row.BERCO;
            if (s) s.checked = !!row.SOFACAMA;
          } catch(_){}
          if (obsArea) obsArea.style.display = '';
        });
        out.appendChild(card);
      });
    } catch (e) {
      console.error(e);
      if (out) out.innerHTML = '<div class="text-danger small">Erro ao procurar.</div>';
    }
  }

  const btnBuscar = document.getElementById('nrBuscar');
  if (btnBuscar) btnBuscar.addEventListener('click', nrBuscar);
  const din = document.getElementById('nrDataIn');
  const res = document.getElementById('nrReserva');
  if (din) din.addEventListener('change', nrBuscar);
  if (res) res.addEventListener('keydown', (e) => { if (e.key === 'Enter') { e.preventDefault(); nrBuscar(); }});

  const btnGravar = document.getElementById('nrGravar');
  if (btnGravar) btnGravar.addEventListener('click', async () => {
    const sel = window.NR_SELECTED;
    const obs = document.getElementById('nrObs').value;
    if (!sel || !sel.reserva) { alert('Escolhe uma reserva.'); return; }
    try {
      const berco = !!document.getElementById('nrBerco')?.checked;
      const sofacama = !!document.getElementById('nrSofa')?.checked;
      const r = await fetch('/generic/api/rs/obs', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ reserva: sel.reserva, obs, berco, sofacama })
      });
      const js = await r.json();
      if (!r.ok || js.ok === false) throw new Error(js.error || 'Falha ao gravar.');
      alert('Notas adicionadas à reserva');
      const modalEl = document.getElementById('nrModal');
      if (modalEl) { const modal = bootstrap.Modal.getInstance(modalEl) || new bootstrap.Modal(modalEl); modal.hide(); }
    } catch (e) {
      alert(e.message || 'Erro ao gravar');
    }
  });

  // Ensure modal overlays the floating + button
  const nrModal = document.getElementById('nrModal');
  const fab = document.getElementById('fab-actions');
  if (nrModal && fab) {
    nrModal.addEventListener('shown.bs.modal', () => { fab.style.display = 'none'; });
    nrModal.addEventListener('hidden.bs.modal', () => { fab.style.display = ''; });
  }
});

// Ensure Notas de Reserva search handlers are bound
document.addEventListener('DOMContentLoaded', () => {
  try {
    const btnBuscar = document.getElementById('nrBuscar');
    const dinEl = document.getElementById('nrDataIn');
    const resEl = document.getElementById('nrReserva');
    if (btnBuscar) btnBuscar.addEventListener('click', () => { if (typeof nrBuscar === 'function') nrBuscar(); });
    if (dinEl) dinEl.addEventListener('change', () => { if (typeof nrBuscar === 'function') nrBuscar(); });
    if (resEl) resEl.addEventListener('keydown', (e) => { if (e.key === 'Enter') { e.preventDefault(); if (typeof nrBuscar === 'function') nrBuscar(); }});
  } catch (e) { /* ignore */ }
});

// =========================
// MN NÃO AGENDADAS (NOVO)
// =========================
document.addEventListener('DOMContentLoaded', () => {
  try {
    const colMN = document.getElementById('mn-nao-agendadas');
    if (!colMN) return; // coluna não está no HTML carregado
    if (typeof IS_MN_ADMIN === 'undefined' || !IS_MN_ADMIN) {
      // se não é admin, esvazia/sai
      colMN.innerHTML = '';
      return;
    }

    // carrega pendentes (MN + FS) ordenados por data
    loadPendentes();

    // submit do modal de agendamento
    const agendarForm = document.getElementById('agendarForm');
    if (agendarForm) {
      agendarForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const mnstamp = document.getElementById('agendarMNStamp').value;
        const data = document.getElementById('agendarData').value; // YYYY-MM-DD
        const hora = document.getElementById('agendarHora').value; // HH:MM

        if (!mnstamp || !data || !hora) {
          alert('Preenche data e hora.');
          return;
        }

        try {
          const resp = await fetch('/generic/api/tarefas/from-mn', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              MNSTAMP: mnstamp,
              DATA: data,
              HORA: hora,
              UTILIZADOR: (typeof window !== 'undefined' && window.CURRENT_USER ? window.CURRENT_USER : null)
            })
          });
          const js = await resp.json();
          if (!resp.ok || js.ok === false) throw new Error(js.error || 'Falha ao agendar manutenção.');

          // fecha modal
          const modalEl = document.getElementById('agendarModal');
          if (modalEl) {
            const modal = bootstrap.Modal.getInstance(modalEl) || new bootstrap.Modal(modalEl);
            modal.hide();
          }

          // refresca coluna MN e as tarefas (se existir função global)
          loadManutencoesNaoAgendadas();
          if (typeof window.loadTarefas === 'function') window.loadTarefas();
        } catch (err) {
          console.error(err);
          alert(err.message || 'Erro ao agendar.');
        }
      });
    }
  } catch (e) {
    console.warn('Init MN não agendadas falhou:', e);
  }
});

async function loadManutencoesNaoAgendadas() {
  const colMN = document.getElementById('mn-nao-agendadas');
  if (!colMN) return;
  colMN.innerHTML = '<div class="text-muted small">A carregar…</div>';

  try {
    const resp = await fetch('/generic/api/monitor/mn-nao-agendadas');
    const js = await resp.json();
    if (!resp.ok) throw new Error(js.error || 'Falha ao carregar MN.');

    const lista = Array.isArray(js.rows) ? js.rows : [];
    // Este método já não é usado diretamente para render da coluna; usar loadPendentes()
    // Mantido por compatibilidade de chamadas antigas
    await loadPendentes();
  } catch (err) {
    console.error(err);
    colMN.innerHTML = '<div class="text-danger small">Erro ao carregar.</div>';
  }
}

async function loadFaltasNaoAgendadas() {
  const colMN = document.getElementById('mn-nao-agendadas');
  if (!colMN) return;
  // Este método já não é usado diretamente para render da coluna; usar loadPendentes()
  try { await loadPendentes(); } catch(_) {}
}

function renderFSCard(fs) {
  const card = document.createElement('div');
  card.className = 'card tarefa-card mb-2 shadow-sm fs-card';
  card.style.cursor = 'pointer';

  const aloj = fs.ALOJAMENTO || '';
  const quem = fs.USERNAME || '';
  const dataStr = fs.DATA ? new Date(fs.DATA).toLocaleDateString('pt-PT') : '';
  const item = fs.ITEM || '';
  const ufs = fs && (fs.URGENTE ?? 0);
  const urgente = (ufs === 1) || (ufs === true) || (ufs === '1') || (String(ufs).toLowerCase() === 'true');

  if (typeof escapeHtml !== 'function') {
    window.escapeHtml = function(s) {
      const str = (s === undefined || s === null) ? '' : String(s);
      return str.replace(/[&<>"']/g, ch => ({ '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;', "'":'&#39;' }[ch]));
    };
  }

  card.innerHTML = `
    <div class="card-body p-2">
      <div class="tarefa-titulo"><strong>${escapeHtml(aloj)}</strong></div>
      <div class="tarefa-subtitulo text-muted small">${escapeHtml(quem)}${(quem && dataStr) ? ' • ' : ''}${escapeHtml(dataStr)}</div>
      <div class="tarefa-texto small">${escapeHtml(item)}</div>
    </div>
  `;

  const body = card.querySelector('.card-body');
  if (body) {
    // ícone de falta (cart)
    const icon = document.createElement('i');
    icon.className = 'fa-solid fa-cart-shopping text-dark float-end';
    icon.title = 'Falta';
    body.prepend(icon);
    // ícone urgente
    if (urgente) {
      const urg = document.createElement('i');
      urg.className = 'fa-solid fa-triangle-exclamation text-danger float-end me-1';
      urg.title = 'Urgente';
      body.prepend(urg);
    }
  }

  card.addEventListener('click', () => {
    const fsstamp = fs.FSSTAMP || fs.fsstamp || '';
    const modalEl = document.getElementById('fsModal');
    const stampEl = document.getElementById('fsStamp');
    if (stampEl) stampEl.value = fsstamp;

    // Preenche resumo no modal FS
    try {
      const resumo = document.getElementById('fsResumo');
      if (resumo) {
        resumo.innerHTML = `
          <div class=\"tarefa-titulo\"><strong>${escapeHtml(aloj)}</strong></div>
          <div class=\"tarefa-subtitulo text-muted small\">${escapeHtml(quem)}${(quem && dataStr) ? ' • ' : ''}${escapeHtml(dataStr)}</div>
          <div class=\"tarefa-texto small\">${escapeHtml(item)}</div>
        `;
      }
    } catch(_) {}

    // Botões do modal FS
    try {
      const btnTratar = document.getElementById('fsTratadaBtn');
      if (btnTratar) {
        btnTratar.onclick = async () => {
          try {
            const r = await fetch('/generic/api/fs/tratar', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ FSSTAMP: fsstamp }) });
            const js = await r.json();
            if (!r.ok || js.ok === false) throw new Error(js.error || 'Falha ao marcar falta.');
            // fecha modal
            const m = bootstrap.Modal.getInstance(modalEl) || new bootstrap.Modal(modalEl);
            m.hide();
            // refresca colunas
            if (typeof loadFaltasNaoAgendadas === 'function') loadFaltasNaoAgendadas();
            if (typeof window.loadTarefas === 'function') window.loadTarefas();
          } catch (e) { alert(e.message || 'Erro'); }
        };
      }

      const btnAbrir = document.getElementById('fsAbrirBtn');
      if (btnAbrir) {
        if (typeof window !== 'undefined' && window.CAN_OPEN_FS) {
          btnAbrir.style.display = 'inline-block';
          btnAbrir.onclick = () => {
            window.location.href = `/generic/form/FS/${encodeURIComponent(fsstamp)}?return_to=/monitor`;
          };
        } else {
          btnAbrir.style.display = 'none';
          btnAbrir.onclick = null;
        }
      }
    } catch(_){}

    if (modalEl) bootstrap.Modal.getOrCreateInstance(modalEl).show();
  });

  return card;
}

// Carrega MN e FS e ordena por DATA (asc)
async function loadPendentes() {
  const col = document.getElementById('mn-nao-agendadas');
  if (!col) return;
  col.innerHTML = '<div class="text-muted small">A carregar…</div>';
  try {
    const isLpAdmin = (typeof window !== 'undefined' && window.IS_LP_ADMIN) ? !!window.IS_LP_ADMIN : false;
    const mnResp = await fetch('/generic/api/monitor/mn-nao-agendadas');
    const mnJs = await mnResp.json();
    const mnList = Array.isArray(mnJs.rows) ? mnJs.rows : [];
    let fsList = [];
    if (isLpAdmin) {
      const fsResp = await fetch('/generic/api/monitor/fs-nao-agendadas');
      const fsJs = await fsResp.json();
      fsList = Array.isArray(fsJs.rows) ? fsJs.rows : [];
    }
    const toTs = (d) => {
      if (!d) return 0;
      // d esperado 'YYYY-MM-DD'
      const dt = new Date(d + 'T00:00:00');
      return dt.getTime();
    };
    const merged = [
      ...mnList.map(x => ({ type:'MN', ts: toTs(x.DATA), data:x })),
      ...fsList.map(x => ({ type:'FS', ts: toTs(x.DATA), data:x }))
    ].sort((a,b) => (a.ts - b.ts) || (a.type.localeCompare(b.type)));

    const cntEl = document.getElementById('count-mn');
    if (cntEl) cntEl.textContent = String(merged.length);

    if (!merged.length) {
      col.innerHTML = '<div class="text-muted small">Sem pendentes.</div>';
      return;
    }
    col.innerHTML = '';
    for (const row of merged) {
      if (row.type === 'MN') col.appendChild(renderMNCardStyled(row.data));
      else col.appendChild(renderFSCard(row.data));
    }
  } catch (err) {
    console.error('Erro ao carregar pendentes:', err);
    col.innerHTML = '<div class="text-danger small">Erro ao carregar.</div>';
  }
}

// --- Override renderer to add FontAwesome maintenance icon ---
// Ensures MN cards show an icon in the top-right corner.
if (typeof renderMNCardStyled !== 'function') {
  // Fallback if previous version not present
  function renderMNCardStyled(mn) {
    const card = document.createElement('div');
    card.className = 'card tarefa-card mb-2 shadow-sm tarefa-manutencao';
    card.style.cursor = 'pointer';

    const aloj = mn.ALOJAMENTO || '';
    const quem = mn.NOME || mn.UTILIZADOR || '';
    const dataStr = mn.DATA ? new Date(mn.DATA).toLocaleDateString('pt-PT') : '';
    const incid = mn.INCIDENCIA || mn.DESCRICAO || '';

    if (typeof escapeHtml !== 'function') {
      window.escapeHtml = function(s) {
        const str = (s === undefined || s === null) ? '' : String(s);
        return str.replace(/[&<>"']/g, ch => ({
          '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
        })[ch]);
      };
    }

    // Botão do modal: marcar MN como tratada diretamente
    const btnMnTratada = document.getElementById('mnTratadaBtn');
    if (btnMnTratada) {
      btnMnTratada.addEventListener('click', async (e) => {
        e.preventDefault();
        const mnstamp = document.getElementById('agendarMNStamp')?.value;
        if (!mnstamp) {
          alert('Sem referência da manutenção.');
          return;
        }
        const ok = window.confirm('Queres marcar a manutenção como tratada?');
        if (!ok) return;
        try {
          const resp = await fetch('/generic/api/mn/tratar', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ MNSTAMP: mnstamp })
          });
          const js = await resp.json();
          if (!resp.ok || js.ok === false) throw new Error(js.error || 'Falha ao marcar como tratada');
          // Fecha o modal
          const modalEl = document.getElementById('agendarModal');
          if (modalEl) {
            const modal = bootstrap.Modal.getInstance(modalEl) || new bootstrap.Modal(modalEl);
            modal.hide();
          }
          // Recarrega colunas
          if (typeof loadManutencoesNaoAgendadas === 'function') loadManutencoesNaoAgendadas();
          if (typeof window.loadTarefas === 'function') window.loadTarefas();
        } catch (err) {
          console.error(err);
          alert(err.message || 'Erro ao marcar manutenção como tratada.');
        }
      });
    }

    card.innerHTML = `
      <div class="card-body p-2">
        <div class="tarefa-titulo"><strong>${escapeHtml(aloj)}</strong></div>
        <div class="tarefa-subtitulo text-muted small">${escapeHtml(quem)}${(quem && dataStr) ? ' • ' : ''}${escapeHtml(dataStr)}</div>
        <div class="tarefa-texto small">${escapeHtml(incid)}</div>
      </div>
    `;

    const body = card.querySelector('.card-body');
    if (body) {
      const icon = document.createElement('i');
      icon.className = 'fa-solid fa-screwdriver-wrench text-primary float-end';
      icon.title = 'Manutenção';
      body.prepend(icon);
      // urgente
      try {
        const u = mn && (mn.URGENTE ?? 0);
        const isUrg = (u === 1) || (u === true) || (u === '1') || (String(u).toLowerCase() === 'true');
        if (isUrg) {
          const urg = document.createElement('i');
          urg.className = 'fa-solid fa-triangle-exclamation text-danger float-end me-1';
          urg.title = 'Urgente';
          body.prepend(urg);
        }
      } catch(_){}
    }

    card.addEventListener('click', () => {
      const mnstamp = mn.MNSTAMP || mn.mnstamp || '';
      const modalEl = document.getElementById('agendarModal');
      const stampEl = document.getElementById('agendarMNStamp');
      if (stampEl) stampEl.value = mnstamp;
      try { window.CURRENT_MN = mn; } catch(_) {}
      // Defaults: hoje e próxima meia hora
      try {
        const dEl = document.getElementById('agendarData');
        const hEl = document.getElementById('agendarHora');
        const now = new Date();
        if (dEl) dEl.value = now.toISOString().slice(0,10);
        const round = new Date(now);
        round.setMinutes(round.getMinutes() < 30 ? 30 : 60, 0, 0);
        const hh = String(round.getHours()).padStart(2,'0');
        const mm = String(round.getMinutes()).padStart(2,'0');
        if (hEl) hEl.value = `${hh}:${mm}`;
      } catch(_){}

      // Replicar card no topo do modal
      try {
        const resumo = document.getElementById('mnResumo');
        if (resumo) {
          const esc = window.escapeHtml || (s => String(s ?? '').replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;','\'':'&#39;'}[ch])));
          resumo.innerHTML = `
            <div class=\"tarefa-titulo\"><strong>${esc(aloj)}</strong></div>
            <div class=\"tarefa-subtitulo text-muted small\">${esc(quem)}${(quem && dataStr) ? ' • ' : ''}${esc(dataStr)}</div>
            <div class=\"tarefa-texto small\">${esc(incid)}</div>
          `;
        }
      } catch(_){}

      // Blocos por cada próximo Check-Out
      try {
        const optsEl = document.getElementById('mnOutOptions');
        if (optsEl) {
          optsEl.innerHTML = '<div class="text-muted small">A carregar check-outs…</div>';
          fetch(`/generic/api/monitor/outs?alojamento=${encodeURIComponent(aloj)}`)
            .then(r => r.json())
            .then(js => {
              const rows = Array.isArray(js.rows) ? js.rows : [];
              if (!rows.length) { optsEl.innerHTML = '<div class="text-muted small">Sem check-outs futuros.</div>'; return; }
              const fmtDDMM = (d) => {
                if (!d) return '';
                if (/^\d{4}-\d{2}-\d{2}$/.test(d)) { const [Y,M,D] = d.split('-'); return `${D}/${M}`; }
                try { const dt = new Date(d); return `${String(dt.getDate()).padStart(2,'0')}/${String(dt.getMonth()+1).padStart(2,'0')}`; } catch(_) { return d; }
              };
              optsEl.innerHTML = '';
              rows.forEach((r) => {
                const coDate = fmtDDMM(r.DATAOUT);
                const coHora = r.HORAOUT && r.HORAOUT !== 'N/D' ? r.HORAOUT : 'N/D';
                const ciDate = fmtDDMM(r.DATAIN || '');
                const ciHora = r.HORAIN || '';
                const lpLine = (r.LPHORA || r.LPEQUIPA) ? `<div class=\"small text-muted\"><strong>Limpeza:</strong> ${(r.LPHORA||'')} ${(r.LPEQUIPA? ' • ' + r.LPEQUIPA : '')}</div>` : '';
                const block = document.createElement('div');
                block.className = 'border rounded p-2 mb-2';
                block.style.cursor = 'pointer';
                block.innerHTML = `
                  <div><strong>Check-Out:</strong> ${coDate}${coHora ? ' • ' + coHora : ''}</div>
                  <div class=\"small text-muted\"><strong>Check-In:</strong> ${ciDate}${ciHora ? ' • ' + ciHora : ''}</div>
                  ${lpLine}
                `;
                block.addEventListener('click', () => {
                  try {
                    const dEl = document.getElementById('agendarData');
                    const hEl = document.getElementById('agendarHora');
                    if (dEl && r.DATAOUT) dEl.value = r.DATAOUT;
                    let hora = r.HORAOUT && r.HORAOUT !== 'N/D' ? r.HORAOUT : '11:00';
                    if (hEl) hEl.value = hora;
                  } catch(_) {}
                });
                optsEl.appendChild(block);
              });
            })
            .catch(() => { optsEl.innerHTML = '<div class="text-muted small">Sem informação disponível.</div>'; });
        }
      } catch(_){}
      // Configura o botão Abrir (mostrar sempre para debug)
      try {
        const btnAbrirMn = document.getElementById('mnAbrirBtn');
        if (btnAbrirMn) {
          btnAbrirMn.style.display = 'inline-block';
          btnAbrirMn.onclick = () => {
            window.location.href = `/generic/form/MN/${encodeURIComponent(mnstamp)}?return_to=/monitor`;
          };
        }
      } catch(_){}
      if (modalEl) {
        const modal = bootstrap.Modal.getOrCreateInstance(modalEl);
        modal.show();
      }
    });

    return card;
  }
} else {
  // Redefine to ensure icon presence if function exists already
  const _prevRenderMN = renderMNCardStyled;
  renderMNCardStyled = function(mn) {
    const card = _prevRenderMN(mn);
    const body = card && card.querySelector ? card.querySelector('.card-body') : null;
    if (body && !body.querySelector('.fa-screwdriver-wrench')) {
      const icon = document.createElement('i');
      icon.className = 'fa-solid fa-screwdriver-wrench text-primary float-end';
      icon.title = 'Manutenção';
      body.prepend(icon);
    }
    return card;
  };
}

// Enforce desired MN icon: fa-wrench in dark color
(function() {
  function wrapWithWrench(fn) {
    return function(mn) {
      const card = fn(mn);
      try {
        const body = card && card.querySelector ? card.querySelector('.card-body') : null;
        if (body) {
          // remove any previous maintenance icons
          body.querySelectorAll('.fa-screwdriver-wrench, .fa-wrench').forEach(el => el.remove());
          // add requested icon (dark)
          const icon = document.createElement('i');
          icon.className = 'fa-solid fa-wrench float-end text-dark';
          icon.title = 'Manutenção';
          body.prepend(icon);
        }
      } catch (e) {}
      return card;
    }
  }
  if (typeof renderMNCardStyled === 'function') {
    renderMNCardStyled = wrapWithWrench(renderMNCardStyled);
  }
})();

// Helper: preenche blocos de próximos check-outs clicáveis
function fillOutOptions(aloj) {
  try {
    const optsEl = document.getElementById('mnOutOptions');
    if (!optsEl || !aloj) return;
    optsEl.innerHTML = '<div class="text-muted small">A carregar check-outs…</div>';
    fetch(`/generic/api/monitor/outs?alojamento=${encodeURIComponent(aloj)}`)
      .then(r => r.json())
      .then(js => {
        const rows = Array.isArray(js.rows) ? js.rows : [];
        if (!rows.length) { optsEl.innerHTML = '<div class="text-muted small">Sem check-outs futuros.</div>'; return; }
        const fmtDDMM = (d) => {
          if (!d) return '';
          if (/^\d{4}-\d{2}-\d{2}$/.test(d)) { const [Y,M,D] = d.split('-'); return `${D}/${M}`; }
          try { const dt = new Date(d); return `${String(dt.getDate()).padStart(2,'0')}/${String(dt.getMonth()+1).padStart(2,'0')}`; } catch(_) { return d; }
        };
        optsEl.innerHTML = '';
        rows.forEach((r) => {
          const coDate = fmtDDMM(r.DATAOUT);
          const coHora = r.HORAOUT && r.HORAOUT !== 'N/D' ? r.HORAOUT : 'N/D';
          const ciDate = fmtDDMM(r.DATAIN || '');
          const ciHora = r.HORAIN || '';
          const lpLine = (r.LPHORA || r.LPEQUIPA) ? `<div class=\"small text-muted\"><strong>Limpeza:</strong> ${(r.LPHORA||'')} ${(r.LPEQUIPA? ' • ' + r.LPEQUIPA : '')}</div>` : '';
          const block = document.createElement('div');
          block.className = 'mn-out-option border rounded p-2 mb-2';
          block.style.cursor = 'pointer';
          block.innerHTML = `
            <div><strong>Check-Out:</strong> ${coDate}${coHora ? ' • ' + coHora : ''}</div>
            <div class=\"small text-muted\"><strong>Check-In:</strong> ${ciDate}${ciHora ? ' • ' + ciHora : ''}</div>
            ${lpLine}
          `;
          block.addEventListener('click', () => {
            try {
              const dEl = document.getElementById('agendarData');
              const hEl = document.getElementById('agendarHora');
              if (dEl && r.DATAOUT) dEl.value = r.DATAOUT;
              let hora = r.HORAOUT && r.HORAOUT !== 'N/D' ? r.HORAOUT : '11:00';
              if (hEl) hEl.value = hora;
              // seleção visual
              try {
                optsEl.querySelectorAll('.mn-out-option').forEach(el => {
                  el.classList.remove('mn-selected');
                  el.style.border = '';
                  el.style.boxShadow = '';
                  el.style.background = '';
                });
                block.classList.add('mn-selected');
                // também aplica estilos inline para garantir override
                block.style.border = '2px solid #0d6efd';
                block.style.boxShadow = '0 0 0 .15rem rgba(13,110,253,.25)';
                block.style.background = '#f4f8ff';
              } catch(_){}
            } catch(_) {}
          });
          optsEl.appendChild(block);
        });
      })
      .catch(() => { optsEl.innerHTML = '<div class="text-muted small">Sem informação disponível.</div>'; });
  } catch(_) {}
}

// Quando o modal de MN abrir, preencher defaults + resumo + próximos eventos
document.addEventListener('DOMContentLoaded', () => {
  const modalEl = document.getElementById('agendarModal');
  if (!modalEl) return;
  modalEl.addEventListener('shown.bs.modal', () => {
    try {
      const mn = (typeof window !== 'undefined' && window.CURRENT_MN) ? window.CURRENT_MN : null;
      // Defaults de Data e Hora (se vazios ou sempre forçar)
      const dEl = document.getElementById('agendarData');
      const hEl = document.getElementById('agendarHora');
      const now = new Date();
      if (dEl) dEl.value = now.toISOString().slice(0,10);
      const round = new Date(now);
      round.setMinutes(round.getMinutes() < 30 ? 30 : 60, 0, 0);
      const hh = String(round.getHours()).padStart(2,'0');
      const mm = String(round.getMinutes()).padStart(2,'0');
      if (hEl) hEl.value = `${hh}:${mm}`;

      // Resumo + Próximos eventos baseados no mnstamp (não depende de window.CURRENT_MN)
      const resumo = document.getElementById('mnResumo');
      const infoEl = document.getElementById('mnOutOptions');
      const stampEl = document.getElementById('agendarMNStamp');
      const mnstamp = stampEl && stampEl.value;
      if (resumo && mnstamp) {
        resumo.innerHTML = '<div class="text-muted small">A carregar…</div>';
        fetch(`/generic/api/mn/${encodeURIComponent(mnstamp)}`)
          .then(r => r.json())
          .then(row => {
            const esc = window.escapeHtml || (s => String(s ?? '').replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;','\'':'&#39;'}[ch])));
            const aloj = row.ALOJAMENTO || '';
            const quem = row.NOME || '';
            const dataStr = row.DATA || '';
            const incid = row.INCIDENCIA || '';
            resumo.innerHTML = `
              <div class=\"tarefa-titulo\"><strong>${esc(aloj)}</strong></div>
              <div class=\"tarefa-subtitulo text-muted small\">${esc(quem)}${(quem && dataStr) ? ' • ' : ''}${esc(dataStr)}</div>
              <div class=\"tarefa-texto small\">${esc(incid)}</div>
            `;
            // Preenche blocos de check-outs (override conteúdo anterior)
            if (infoEl) setTimeout(() => fillOutOptions(aloj), 0);
          })
          .catch(() => { resumo.innerHTML = ''; });
      }
    } catch (_) {}
  });
});

// Add "Marcar como tratada" button to MN cards
(function() {
  function withTratarButton(fn) {
    return function(mn) {
      const card = fn(mn);
      try {
        const body = card && card.querySelector ? card.querySelector('.card-body') : null;
        if (body && !body.querySelector('.mn-actions')) {
          const actions = document.createElement('div');
          actions.className = 'mn-actions tarefa-acoes mt-2 d-flex gap-2';

          const btnTratar = document.createElement('button');
          btnTratar.type = 'button';
          btnTratar.className = 'btn btn-sm btn-success';
          btnTratar.textContent = 'Marcar como tratada';
          btnTratar.addEventListener('click', async (ev) => {
            ev.stopPropagation();
            const stamp = mn.MNSTAMP || mn.mnstamp || '';
            if (!stamp) return;
            try {
              const resp = await fetch('/generic/api/mn/tratar', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ MNSTAMP: stamp })
              });
              const js = await resp.json();
              if (!resp.ok || js.ok === false) throw new Error(js.error || 'Falha ao marcar como tratada');
              // Atualiza a lista de MN e tarefas
              if (typeof loadManutencoesNaoAgendadas === 'function') loadManutencoesNaoAgendadas();
              if (typeof window.loadTarefas === 'function') window.loadTarefas();
            } catch (e) {
              alert(e.message || 'Erro');
            }
          });

          actions.appendChild(btnTratar);
          body.appendChild(actions);
        }
      } catch (e) {}
      return card;
    }
  }
  if (typeof renderMNCardStyled === 'function') {
    renderMNCardStyled = withTratarButton(renderMNCardStyled);
  }
})();

// Delegated handler for modal button (works even if DOMContentLoaded already fired)
document.addEventListener('click', async (evt) => {
  const btn = evt.target.closest('#mnTratadaBtn');
  if (!btn) return;
  evt.preventDefault();
  const stampEl = document.getElementById('agendarMNStamp');
  const mnstamp = stampEl && stampEl.value;
  if (!mnstamp) {
    alert('Sem referência da manutenção.');
    return;
  }
  const ok = window.confirm('Queres marcar a manutenção como tratada?');
  if (!ok) return;
  try {
    const resp = await fetch('/generic/api/mn/tratar', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ MNSTAMP: mnstamp })
    });
    const js = await resp.json();
    if (!resp.ok || js.ok === false) throw new Error(js.error || 'Falha ao marcar como tratada');
    const modalEl = document.getElementById('agendarModal');
    if (modalEl) {
      const modal = bootstrap.Modal.getInstance(modalEl) || new bootstrap.Modal(modalEl);
      modal.hide();
    }
    if (typeof loadManutencoesNaoAgendadas === 'function') loadManutencoesNaoAgendadas();
    if (typeof window.loadTarefas === 'function') window.loadTarefas();
  } catch (err) {
    console.error(err);
    alert(err.message || 'Erro ao marcar manutenção como tratada.');
  }
});

// Helper: decide permissões/URL para Abrir conforme ORIGEM
function getOpenInfo(t) {
  const origin = (t.ORIGEM || '').toUpperCase().trim();
  if (origin === 'MN') {
    return {
      can: !!(typeof window !== 'undefined' && window.CAN_OPEN_MN),
      url: t.ORISTAMP
        ? `/generic/form/MN/${encodeURIComponent(t.ORISTAMP)}?return_to=/monitor`
        : (t.TAREFASSTAMP
            ? `/generic/form/TAREFAS/${encodeURIComponent(t.TAREFASSTAMP)}?return_to=/monitor`
            : '#')
    };
  }
  if (origin === 'LP') {
    return {
      can: !!(typeof window !== 'undefined' && window.CAN_OPEN_LP),
      url: t.ORISTAMP
        ? `/generic/form/LP/${encodeURIComponent(t.ORISTAMP)}?return_to=/monitor`
        : (t.TAREFASSTAMP
            ? `/generic/form/TAREFAS/${encodeURIComponent(t.TAREFASSTAMP)}?return_to=/monitor`
            : '#')
    };
  }
  if (origin === 'FS') {
    return {
      can: !!(typeof window !== 'undefined' && window.CAN_OPEN_FS),
      url: t.ORISTAMP
        ? `/generic/form/FS/${encodeURIComponent(t.ORISTAMP)}?return_to=/monitor`
        : (t.TAREFASSTAMP
            ? `/generic/form/TAREFAS/${encodeURIComponent(t.TAREFASSTAMP)}?return_to=/monitor`
            : '#')
    };
  }
  return {
    can: !!(typeof window !== 'undefined' && window.CAN_OPEN_TAREFAS) && !!t.TAREFASSTAMP,
    url: `/generic/form/TAREFAS/${encodeURIComponent(t.TAREFASSTAMP || '')}?return_to=/monitor`
  };
}

// Navegar para o registo de MN a partir do modal (botão Abrir)
document.addEventListener('click', (evt) => {
  const btn = evt.target.closest('#mnAbrirBtn');
  if (!btn) return;
  evt.preventDefault();
  try {
    const stampEl = document.getElementById('agendarMNStamp');
    const mnstamp = stampEl && stampEl.value;
    if (!mnstamp) return;
    window.location.href = `/generic/form/MN/${encodeURIComponent(mnstamp)}?return_to=/monitor`;
  } catch (_) {}
});

// Confirmação ao marcar tarefa como tratada (popup de tarefas)
// Usa captura para interceptar antes do handler existente
document.addEventListener('click', function(e) {
  const btn = e.target.closest('#btnTratar');
  if (!btn) return;
  const ok = window.confirm('Queres marcar a tarefa como tratada?');
  if (!ok) {
    e.preventDefault();
    e.stopImmediatePropagation();
  }
}, true);

// =========================
// Filtro: Apenas as minhas tarefas (setup imediato)
// =========================
(function setupOnlyMineFilter() {
  const chk = document.getElementById('onlyMineChk');
  if (!chk) return;

  const storageKey = 'monitor_only_mine';
  try {
    const stored = localStorage.getItem(storageKey);
    chk.checked = stored === null ? true : stored === '1';
  } catch (_) { chk.checked = true; }

  chk.addEventListener('change', () => {
    try { localStorage.setItem(storageKey, chk.checked ? '1' : '0'); } catch (_) {}
    reloadTasksFilteredImmediate();
  });

  reloadTasksFilteredImmediate();

  function getOnlyMine() { return !!chk.checked; }

  function shouldShowTask(t) {
    const currentUser = (typeof window !== 'undefined' && window.CURRENT_USER) ? window.CURRENT_USER : '';
    const isMnAdmin = (typeof window !== 'undefined' && window.IS_MN_ADMIN) ? !!window.IS_MN_ADMIN : false;
    const isLpAdmin = (typeof window !== 'undefined' && window.IS_LP_ADMIN) ? !!window.IS_LP_ADMIN : false;
    if (getOnlyMine()) return (t.UTILIZADOR || '').toUpperCase() === (currentUser || '').toUpperCase();
    const origins = [];
    if (isMnAdmin) origins.push('MN');
    if (isLpAdmin) { origins.push('LP'); origins.push('FS'); }
    if (origins.length === 0) return (t.UTILIZADOR || '').toUpperCase() === (currentUser || '').toUpperCase();
    return origins.includes((t.ORIGEM || '').toUpperCase());
  }

  async function reloadTasksFilteredImmediate() {
    try {
      const onlyMine = !!chk.checked;
      const res = await fetch(`/generic/api/monitor_tasks_filtered?only_mine=${onlyMine ? '1' : '0'}`);
      const data = await res.json();
      window.MONITOR_TAREFAS_DATA = Array.isArray(data) ? data : (data.rows || []);
      renderTasksFilteredImmediate(window.MONITOR_TAREFAS_DATA);
    } catch (err) {
      console.error('Erro a recarregar tarefas (filtro):', err);
    }
  }

  function renderTasksFilteredImmediate(data) {
    const colAtrasadas = document.getElementById('tarefas-atrasadas');
    const colHoje = document.getElementById('tarefas-hoje');
    const colFuturas = document.getElementById('tarefas-futuras');
    const colTratadas = document.getElementById('tarefas-tratadas');
    if (!colAtrasadas || !colHoje || !colFuturas || !colTratadas) return;

    colAtrasadas.innerHTML = '';
    colHoje.innerHTML = '';
    colFuturas.innerHTML = '';
    colTratadas.innerHTML = '';

    const hoje = new Date();
    const hojeStr = hoje.toISOString().slice(0, 10);

    (data || []).filter(shouldShowTask).forEach(t => {
      const dataFormatada = new Date(t.DATA + 'T' + t.HORA);
      const hhmm = t.HORA;
      const ddmm = dataFormatada.toLocaleDateString('pt-PT');
      // Título do card: se não tiver origem e nem alojamento, mostrar "Tarefa"
      const _semOrigem = !t.ORIGEM || String(t.ORIGEM).trim() === '';
      const _semAloj = !t.ALOJAMENTO || String(t.ALOJAMENTO).trim() === '';
      const _tituloCard = (_semOrigem && _semAloj) ? 'Tarefa' : (t.ALOJAMENTO || '');

      const bloco = document.createElement('div');
      bloco.className = 'card tarefa-card mb-2 shadow-sm';

      let texto;
      if (t.DATA === hojeStr) {
        texto = `<strong class=\"tarefa-alojamento\">${_tituloCard}</strong><br><span class='text-muted small'>${hhmm} - ${t.TAREFA}</span>`;
      } else {
        texto = `<strong class=\"tarefa-alojamento\">${_tituloCard}</strong><br><span class='text-muted small'>${ddmm} ${hhmm} - ${t.TAREFA}</span>`;
      }

      let icone = '';
      if (t.TRATADO) {
        icone = '<i class="fas fa-check-circle text-success float-end"></i>';
      } else if (t.DATA < hojeStr) {
        icone = '<i class="fas fa-exclamation-circle text-danger float-end"></i>';
      }

      // Badge do utilizador (nome) com cor
      const esc = (typeof window !== 'undefined' && typeof window.escapeHtml === 'function')
        ? window.escapeHtml
        : (s => String(s ?? '').replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;','\'':'&#39;'}[ch])));
      const userName = t.UTILIZADOR_NOME || t.UTILIZADOR || '';
      const userColor = t.UTILIZADOR_COR || '#6c757d';
      const userBadge = userName
        ? `<span class="user-badge float-end ms-1" title="${esc(userName)}" style="background-color:${esc(userColor)};color:#fff;border-radius:8px;padding:2px 6px;font-size:.70rem;line-height:1.1;white-space:nowrap;">${esc(userName)}</span>`
        : '';

      let origemIcon = '';
      switch ((t.ORIGEM || '').toUpperCase()) {
        case 'MN': origemIcon = '<i class="fa-solid fa-wrench text-dark float-end ms-1" title="Manutenção"></i>'; break;
        case 'LP': origemIcon = '<i class="fa-solid fa-broom text-dark float-end ms-1" title="Limpeza"></i>'; break;
        case 'FS': origemIcon = '<i class="fa-solid fa-cart-shopping text-dark float-end ms-1" title="Falta de Stock"></i>'; break;
        default:
          if (!t.ORIGEM || String(t.ORIGEM).trim() === '') {
            origemIcon = '<i class="fa-solid fa-list-check text-dark float-end ms-1" title="Tarefa"></i>';
          }
          break;
      }

        bloco.innerHTML = `<div class=\"card-body p-2\">${userBadge}${origemIcon}${icone}<div>${texto}</div></div>`;

      bloco.addEventListener('click', () => {
        const modalElement = document.getElementById('tarefaModal');
        const modal = modalElement ? new bootstrap.Modal(modalElement) : null;
        const tarefaDescricao = document.getElementById('tarefaDescricao');
        const btnTratar = document.getElementById('btnTratar');
        const btnReabrir = document.getElementById('btnReabrir');

        window.tarefaSelecionada = t;
        if (tarefaDescricao) tarefaDescricao.textContent = `${t.TAREFA} (${t.HORA} - ${t.ALOJAMENTO})`;

        fetch(`/api/tarefa_info/${t.TAREFASSTAMP}`)
          .then(res => res.json())
          .then(info => {
            const extraInfo = info.info || '';
            if (tarefaDescricao) tarefaDescricao.innerHTML = `<strong>${t.TAREFA} (${t.HORA} - ${t.ALOJAMENTO})</strong><br><br>${extraInfo.replace(/\n/g, '<br>')}`;
          })
          .catch(err => console.error('Erro ao buscar info da tarefa', err));

        if (btnTratar) btnTratar.style.display = 'none';
        if (btnReabrir) btnReabrir.style.display = 'none';
        if (!t.TRATADO) { if (btnTratar) btnTratar.style.display = 'inline-block'; }
        else { if (btnReabrir) btnReabrir.style.display = 'inline-block'; }

        // Botão Abrir (no modal) – por origem/permissões
        try {
          const btnAbrir = document.getElementById('btnAbrirTarefa');
          if (btnAbrir) {
            const oiM = getOpenInfo(t);
            if (oiM.can) {
              btnAbrir.style.display = 'inline-block';
              btnAbrir.onclick = () => { window.location.href = oiM.url; };
            } else {
              btnAbrir.style.display = 'none';
              btnAbrir.onclick = null;
            }
          }
        } catch(_){}
        if (modal) modal.show();
      });

      if (!t.TRATADO) {
        if (t.DATA < hojeStr) colAtrasadas.appendChild(bloco);
        else if (t.DATA === hojeStr) colHoje.appendChild(bloco);
        else colFuturas.appendChild(bloco);
      } else {
        colTratadas.appendChild(bloco);
      }
    });
  }
})();

// Força o estado por defeito com visto e recarrega
document.addEventListener('DOMContentLoaded', () => {
  const chk = document.getElementById('onlyMineChk');
  if (chk) {
    chk.checked = true;
    try { localStorage.setItem('monitor_only_mine','1'); } catch(_){}
    // dispara mudança para garantir render
    try { chk.dispatchEvent(new Event('change')); } catch(_){}
  }
});

// =========================
// Filtro: Apenas as minhas tarefas
// =========================
(function() {
  const onlyMineKey = 'monitor_only_mine';

  function getOnlyMine() {
    const chk = document.getElementById('onlyMineChk');
    if (chk) return !!chk.checked;
    try {
      const stored = localStorage.getItem(onlyMineKey);
      return stored === null ? true : stored === '1';
    } catch (_) { return true; }
  }

  function setOnlyMine(val) {
    try { localStorage.setItem(onlyMineKey, val ? '1' : '0'); } catch (_) {}
  }

  function shouldShowTask(t, onlyMine) {
    const currentUser = (typeof window !== 'undefined' && window.CURRENT_USER) ? window.CURRENT_USER : '';
    const isMnAdmin = (typeof window !== 'undefined' && window.IS_MN_ADMIN) ? !!window.IS_MN_ADMIN : false;
    const isLpAdmin = (typeof window !== 'undefined' && window.IS_LP_ADMIN) ? !!window.IS_LP_ADMIN : false;
    if (onlyMine) return (t.UTILIZADOR || '').toUpperCase() === (currentUser || '').toUpperCase();
    const origins = [];
    if (isMnAdmin) origins.push('MN');
    if (isLpAdmin) { origins.push('LP'); origins.push('FS'); }
    if (origins.length === 0) return (t.UTILIZADOR || '').toUpperCase() === (currentUser || '').toUpperCase();
    return origins.includes((t.ORIGEM || '').toUpperCase());
  }

  function renderTasksFiltered(data) {
    const colAtrasadas = document.getElementById('tarefas-atrasadas');
    const colHoje = document.getElementById('tarefas-hoje');
    const colFuturas = document.getElementById('tarefas-futuras');
    const colTratadas = document.getElementById('tarefas-tratadas');
    if (!colAtrasadas || !colHoje || !colFuturas || !colTratadas) return;

    colAtrasadas.innerHTML = '';
    colHoje.innerHTML = '';
    colFuturas.innerHTML = '';
    colTratadas.innerHTML = '';

    const hoje = new Date();
    const hojeStr = hoje.toISOString().slice(0, 10);
    const onlyMine = getOnlyMine();

    (data || []).filter(t => shouldShowTask(t, onlyMine)).forEach(t => {
      const dataFormatada = new Date(t.DATA + 'T' + t.HORA);
      const hhmm = t.HORA;
      const ddmm = dataFormatada.toLocaleDateString('pt-PT');
      // Título do card: se não tiver origem e nem alojamento, mostrar "Tarefa"
      const _semOrigem = !t.ORIGEM || String(t.ORIGEM).trim() === '';
      const _semAloj = !t.ALOJAMENTO || String(t.ALOJAMENTO).trim() === '';
      const _tituloCard = (_semOrigem && _semAloj) ? 'Tarefa' : (t.ALOJAMENTO || '');

      const bloco = document.createElement('div');
      bloco.className = 'card tarefa-card mb-2 shadow-sm';

      let texto;
      if (t.DATA === hojeStr) {
        texto = `<strong class=\"tarefa-alojamento\">${_tituloCard}</strong><br><span class='text-muted small'>${hhmm} - ${t.TAREFA}</span>`;
      } else {
        texto = `<strong class=\"tarefa-alojamento\">${_tituloCard}</strong><br><span class='text-muted small'>${ddmm} ${hhmm} - ${t.TAREFA}</span>`;
      }

      let icone = '';
      if (t.TRATADO) {
        icone = '<i class="fas fa-check-circle text-success float-end"></i>';
      } else if (t.DATA < hojeStr) {
        icone = '<i class="fas fa-exclamation-circle text-danger float-end"></i>';
      }

      // Badge do utilizador
      const esc = (typeof window !== 'undefined' && typeof window.escapeHtml === 'function')
        ? window.escapeHtml
        : (s => String(s ?? '').replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;','\'':'&#39;'}[ch])));
      const userName = t.UTILIZADOR_NOME || t.UTILIZADOR || '';
      const userColor = t.UTILIZADOR_COR || '#6c757d';
      const userBadge = userName
        ? `<span class=\"user-badge float-end ms-1\" title=\"${esc(userName)}\" style=\"background-color:${esc(userColor)};color:#fff;border-radius:8px;padding:2px 6px;font-size:.70rem;line-height:1.1;white-space:nowrap;\">${esc(userName)}</span>`
        : '';

      let origemIcon = '';
      switch ((t.ORIGEM || '').toUpperCase()) {
        case 'MN': origemIcon = '<i class="fa-solid fa-wrench text-dark float-end ms-1" title="Manutenção"></i>'; break;
        case 'LP': origemIcon = '<i class="fa-solid fa-broom text-dark float-end ms-1" title="Limpeza"></i>'; break;
        case 'FS': origemIcon = '<i class="fa-solid fa-cart-shopping text-dark float-end ms-1" title="Falta de Stock"></i>'; break;
        default:
          if (!t.ORIGEM || String(t.ORIGEM).trim() === '') {
            origemIcon = '<i class="fa-solid fa-list-check text-dark float-end ms-1" title="Tarefa"></i>';
          }
          break;
      }

      bloco.innerHTML = `<div class=\"card-body p-2\">${userBadge}${origemIcon}${icone}<div>${texto}</div></div>`;

      bloco.addEventListener('click', () => {
        const modalElement = document.getElementById('tarefaModal');
        const modal = modalElement ? new bootstrap.Modal(modalElement) : null;
        const tarefaDescricao = document.getElementById('tarefaDescricao');
        const btnTratar = document.getElementById('btnTratar');
        const btnReabrir = document.getElementById('btnReabrir');
        
        tarefaSelecionada = t;
        if (tarefaDescricao) tarefaDescricao.textContent = `${t.TAREFA} (${t.HORA} - ${t.ALOJAMENTO})`;

        fetch(`/api/tarefa_info/${t.TAREFASSTAMP}`)
          .then(res => res.json())
          .then(data => {
            const extraInfo = data.info || '';
            if (tarefaDescricao) tarefaDescricao.innerHTML = `<strong>${t.TAREFA} (${t.HORA} - ${t.ALOJAMENTO})</strong><br><br>${extraInfo.replace(/\n/g, '<br>')}`;
          })
          .catch(err => console.error('Erro ao buscar info da tarefa', err));

        if (btnTratar) btnTratar.style.display = 'none';
        if (btnReabrir) btnReabrir.style.display = 'none';
        if (!t.TRATADO) { if (btnTratar) btnTratar.style.display = 'inline-block'; } else { if (btnReabrir) btnReabrir.style.display = 'inline-block'; }
        if (modal) modal.show();
      });

      if (!t.TRATADO) {
        if (t.DATA < hojeStr) colAtrasadas.appendChild(bloco);
        else if (t.DATA === hojeStr) colHoje.appendChild(bloco);
        else colFuturas.appendChild(bloco);
      } else {
        colTratadas.appendChild(bloco);
      }
    });
  }

  async function reloadTasksFiltered() {
    try {
      const res = await fetch('/generic/api/monitor_tasks');
      const data = await res.json();
      window.MONITOR_TAREFAS_DATA = Array.isArray(data) ? data : (data.rows || []);
      renderTasksFiltered(window.MONITOR_TAREFAS_DATA);
    } catch (err) {
      console.error(err);
    }
  }

  document.addEventListener('DOMContentLoaded', () => {
    const chk = document.getElementById('onlyMineChk');
    if (chk) {
      // default checked
      try {
        const stored = localStorage.getItem(onlyMineKey);
        chk.checked = stored === null ? true : stored === '1';
      } catch (_) { chk.checked = true; }
      chk.addEventListener('change', () => {
        setOnlyMine(chk.checked);
        if (window.MONITOR_TAREFAS_DATA) renderTasksFiltered(window.MONITOR_TAREFAS_DATA);
        else reloadTasksFiltered();
      });
    }
    // ensure initial render uses our filter logic
    reloadTasksFiltered();
  });
})();

// Novo renderer: cards de MN semelhantes aos das tarefas
function renderMNCardStyled(mn) {
  // Espera { MNSTAMP, NOME (quem pediu), ALOJAMENTO, INCIDENCIA, DATA (YYYY-MM-DD) }
  const card = document.createElement('div');
  card.className = 'card tarefa-card mb-2 shadow-sm tarefa-manutencao';
  card.style.cursor = 'pointer';

  const aloj = mn.ALOJAMENTO || '';
  const quem = mn.NOME || mn.UTILIZADOR || '';
  const dataStr = mn.DATA ? new Date(mn.DATA).toLocaleDateString('pt-PT') : '';
  const incid = mn.INCIDENCIA || mn.DESCRICAO || '';

  card.innerHTML = `
    <div class="card-body p-2">
      <div class="tarefa-titulo"><strong>${escapeHtml(aloj)}</strong></div>
      <div class="tarefa-subtitulo text-muted small">${escapeHtml(quem)}${(quem && dataStr) ? ' • ' : ''}${escapeHtml(dataStr)}</div>
      <div class="tarefa-texto small">${escapeHtml(incid)}</div>
    </div>
  `;

  card.addEventListener('click', () => {
    const mnstamp = mn.MNSTAMP || mn.MNSTAMP || mn.mnstamp || '';
    const modalEl = document.getElementById('agendarModal');
    const stampEl = document.getElementById('agendarMNStamp');
    if (stampEl) stampEl.value = mnstamp;
    if (modalEl) {
      const modal = bootstrap.Modal.getOrCreateInstance(modalEl);
      modal.show();
    }
  });

  return card;
}

// Helper para escapar HTML em campos vindos do servidor
function escapeHtml(s) {
  const str = (s === undefined || s === null) ? '' : String(s);
  return str.replace(/[&<>"']/g, ch => ({
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#39;'
  })[ch]);
}

function renderMNCard(mn) {
  // Espera { MNSTAMP, NOME, ALOJAMENTO, INCIDENCIA, DATA(YYYY-MM-DD) }
  const card = document.createElement('div');
  card.className = 'card tarefa-card mb-2 shadow-sm tarefa-manutencao';
  card.style.cursor = 'pointer';

  const body = document.createElement('div');
  body.className = 'card-body p-2 position-relative';

  // Ícone de manutenção (canto superior direito)
  const icon = document.createElement('i');
  icon.className = 'fa-solid fa-wrench position-absolute';
  icon.style.top = '6px';
  icon.style.right = '8px';
  icon.style.opacity = '0.7';
  body.appendChild(icon);

  // Título (incidência)
  const titulo = document.createElement('div');
  titulo.className = 'tarefa-titulo';
  titulo.textContent = mn.INCIDENCIA || '(Sem descrição)';
  body.appendChild(titulo);

  // Subtítulo (nome • alojamento • data)
  const sub = document.createElement('div');
  sub.className = 'tarefa-subtitulo';
  const aloj = mn.ALOJAMENTO ? ` • ${mn.ALOJAMENTO}` : '';
  const dataFmt = formatDatePT(mn.DATA);
  sub.textContent = `${mn.NOME || ''}${aloj}${mn.DATA ? ' • ' + dataFmt : ''}`;
  body.appendChild(sub);

  // Ao clicar no cartão abre o modal de agendamento
  card.addEventListener('click', () => {
    const modalEl = document.getElementById('agendarModal');
    if (!modalEl) return;

    // Preenche os campos do modal
    const hid = document.getElementById('agendarMNStamp');
    const inpData = document.getElementById('agendarData');
    const inpHora = document.getElementById('agendarHora');

    if (hid) hid.value = mn.MNSTAMP || '';
    if (inpData) inpData.value = mn.DATA || '';
    if (inpHora) inpHora.value = '';

    const modal = bootstrap.Modal.getInstance(modalEl) || new bootstrap.Modal(modalEl);
    modal.show();
  });

  card.appendChild(body);
  return card;
}

// util: YYYY-MM-DD -> DD.MM.YYYY
function formatDatePT(s) {
  if (!s) return '';
  const yyyy = s.slice(0,4), mm = s.slice(5,7), dd = s.slice(8,10);
  if (yyyy && mm && dd) return `${dd}.${mm}.${yyyy}`;
  return s;
}
