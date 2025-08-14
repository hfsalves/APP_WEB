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
  const btnReagendar = document.getElementById('btnReagendar');
  const btnNota = document.getElementById('btnNota');
  
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

    data.forEach(t => {
        const dataFormatada = new Date(t.DATA + 'T' + t.HORA);
        const hhmm = t.HORA;
        const ddmm = dataFormatada.toLocaleDateString('pt-PT');

        const bloco = document.createElement('div');
        bloco.className = 'card tarefa-card mb-2 shadow-sm';

        let texto;
        if (t.DATA === hojeStr) {
          texto = `<strong>${t.ALOJAMENTO}</strong><br><span class='text-muted small'>${hhmm} - ${t.TAREFA}</span>`;
        } else {
          texto = `<strong>${t.ALOJAMENTO}</strong><br><span class='text-muted small'>${ddmm} ${hhmm} - ${t.TAREFA}</span>`;
        }

        let icone = '';
        if (t.TRATADO) {
          icone = '<i class="fas fa-check-circle text-success float-end"></i>';
        } else if (t.DATA < hojeStr) {
          icone = '<i class="fas fa-exclamation-circle text-danger float-end"></i>';
        }

        bloco.innerHTML = `<div class="card-body p-2">${icone}<div>${texto}</div></div>`;

        bloco.addEventListener('click', () => {
            tarefaSelecionada = t;
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
            if (btnReagendar) btnReagendar.style.display = 'none';
            if (btnNota) btnNota.style.display = 'none';

            if (!t.TRATADO) {
                if (btnTratar) btnTratar.style.display = 'inline-block';
                if (btnReagendar) btnReagendar.style.display = 'inline-block';
            } else {
                if (btnReabrir) btnReabrir.style.display = 'inline-block';
            }
            if (btnNota) btnNota.style.display = 'inline-block';

            if (modal) modal.show();
        });



        if (!t.TRATADO) {
          if (t.DATA < hojeStr) {
            colAtrasadas.appendChild(bloco);
          } else if (t.DATA === hojeStr) {
            colHoje.appendChild(bloco);
          } else {
            colFuturas.appendChild(bloco);
          }
        } else {
          colTratadas.appendChild(bloco);
        }
      });
    })
    .catch(err => alert('Erro ao carregar tarefas: ' + err));

  if (btnTratar) {
    btnTratar.addEventListener('click', () => {
      if (!tarefaSelecionada) return;
      fetch('/generic/api/tarefas/tratar', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id: tarefaSelecionada.TAREFASSTAMP })
      }).then(() => window.location.reload());
    });
  }

  if (btnReagendar) {
    btnReagendar.addEventListener('click', () => {
      alert('Funcionalidade de reagendamento por implementar.');
    });
  }

  if (btnNota) {
    btnNota.addEventListener('click', () => {
      alert('Funcionalidade de nota por implementar.');
    });
  }

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

    // carrega a lista
    loadManutencoesNaoAgendadas();

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
              UTILIZADOR: (typeof CURRENT_USER !== 'undefined' ? CURRENT_USER : null)
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
    if (lista.length === 0) {
      colMN.innerHTML = '<div class="text-muted small">Sem manutenções por agendar.</div>';
      return;
    }

    colMN.innerHTML = '';
    for (const mn of lista) colMN.appendChild(renderMNCard(mn));
  } catch (err) {
    console.error(err);
    colMN.innerHTML = '<div class="text-danger small">Erro ao carregar.</div>';
  }
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
