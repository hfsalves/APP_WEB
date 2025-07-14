// static/js/monitor.js

document.addEventListener('DOMContentLoaded', () => {
  const colAtrasadas = document.getElementById('tarefas-atrasadas');
  const colHoje = document.getElementById('tarefas-hoje');
  const colFuturas = document.getElementById('tarefas-futuras');
  const colTratadas = document.getElementById('tarefas-tratadas');
  const modalElement = document.getElementById('tarefaModal');
  const modal = modalElement ? new bootstrap.Modal(modalElement) : null;
  const tarefaDescricao = document.getElementById('tarefaDescricao');
  const btnTratar = document.getElementById('btnTratar');
  const btnReabrir = document.getElementById('btnReabrir');
  const btnReagendar = document.getElementById('btnReagendar');
  const btnNota = document.getElementById('btnNota');
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
