document.addEventListener('DOMContentLoaded', function() {
  const CALENDAR_API = '/generic/api/calendar_tasks';
  let now = new Date();
  let currentYear = now.getFullYear();
  let currentMonth = now.getMonth(); // 0 = Janeiro

  const monthNames = [
    'Janeiro','Fevereiro','Março','Abril','Maio','Junho',
    'Julho','Agosto','Setembro','Outubro','Novembro','Dezembro'
  ];

  function loadCalendar(year, month) {
    const firstDay = new Date(year, month, 1);
    const lastDay  = new Date(year, month + 1, 0);

    // Ajuste para iniciar na segunda-feira
    const shiftStart = (firstDay.getDay() + 6) % 7;
    const startDate  = new Date(firstDay);
    startDate.setDate(firstDay.getDate() - shiftStart);

    // Ajuste para terminar no domingo
    const shiftEnd = (lastDay.getDay() + 6) % 7;
    const endDate  = new Date(lastDay);
    endDate.setDate(lastDay.getDate() + (6 - shiftEnd));

    document.getElementById('month-year').textContent = `${monthNames[month]} de ${year}`;
    clearError();

    const startStr = startDate.toISOString().slice(0,10);
    const endStr   = endDate.toISOString().slice(0,10);

    fetch(`${CALENDAR_API}?start=${startStr}&end=${endStr}`)
      .then(res => {
        if (!res.ok) throw new Error(res.status + ' ' + res.statusText);
        return res.json();
      })
      .then(tasks => renderCalendar(startDate, endDate, tasks))
      .catch(err => showError(`Erro ao carregar dados: ${err.message}`));
  }

  function showError(msg) {
    let errEl = document.getElementById('calendar-error');
    if (!errEl) {
      errEl = document.createElement('div');
      errEl.id = 'calendar-error';
      errEl.className = 'text-danger mb-3';
      document.querySelector('.container-fluid').prepend(errEl);
    }
    errEl.textContent = msg;
    const tbody = document.getElementById('calendar-body');
    if (tbody) tbody.innerHTML = '';
  }

  function clearError() {
    const errEl = document.getElementById('calendar-error');
    if (errEl) errEl.remove();
  }

  function renderCalendar(startDate, endDate, tasks) {
    clearError();
    const tbl = document.querySelector('.calendar-table');
    const tbody = document.getElementById('calendar-body');
    tbody.innerHTML = '';

    // Layout fixo de colunas iguais
    tbl.style.tableLayout = 'fixed';
    tbl.style.width = '100%';

    let cursor = new Date(startDate);
    // Gerar exatamente 5 linhas
    for (let r = 0; r < 5; r++) {
      const tr = document.createElement('tr');
      for (let c = 0; c < 7; c++) {
        const td = document.createElement('td');
        td.className = 'align-top p-1';
        td.style.width = '14.2857%';
        td.style.verticalAlign = 'top';
        td.style.paddingTop = '0.5rem';
        td.style.paddingBottom = '0.5rem';

        // Data do dia
        const dayDiv = document.createElement('div');
        dayDiv.className = 'fw-bold mb-1';
        dayDiv.textContent = cursor.getDate();
        dayDiv.style.color = '#aaa';
        td.appendChild(dayDiv);

        // Inserir tarefas
        const iso = [
            cursor.getFullYear(),
            String(cursor.getMonth() + 1).padStart(2,'0'),
            String(cursor.getDate()).padStart(2,'0')
            ].join('-');
        tasks.filter(t => t.DATA === iso).forEach(t => {
          const div = document.createElement('div');

          
    const trailer = t.TAREFA.substring(0,20);
    if (t.ALOJAMENTO && t.ALOJAMENTO.trim() !== '') {
      // usamos innerHTML para inserir o <br>
      div.innerHTML = 
        `<strong>${t.ALOJAMENTO}</strong><br>` +
        `${t.HORA} : ${trailer}`;
    } else {
      div.textContent = `${t.HORA} : ${trailer}`;
    }


          div.style.backgroundColor = t.COR || '#333333';
          div.style.color = '#fff';
          div.style.padding = '2px 4px';
          div.style.marginBottom = '2px';
          div.style.borderRadius = '3px';
          div.style.fontSize = '0.8em';
          div.style.whiteSpace = 'nowrap';
          div.style.textOverflow = 'ellipsis';
          div.style.overflow = 'hidden';
          div.style.cursor = 'pointer';
          // Ao clicar, abre a view da tarefa
          div.onclick = () => {
            window.location.href = `/generic/form/TAREFAS/${t.TAREFASSTAMP}?return_to=/generic/view/calendar/`;
          };
          td.appendChild(div);
        });

        tr.appendChild(td);
        cursor.setDate(cursor.getDate() + 1);
      }
      tbody.appendChild(tr);
    }
  }

  // Navegação de meses
  document.getElementById('prev-month').onclick = () => {
    if (currentMonth === 0) { currentMonth = 11; currentYear--; }
    else { currentMonth--; }
    loadCalendar(currentYear, currentMonth);
  };
  document.getElementById('next-month').onclick = () => {
    if (currentMonth === 11) { currentMonth = 0; currentYear++; }
    else { currentMonth++; }
    loadCalendar(currentYear, currentMonth);
  };

  loadCalendar(currentYear, currentMonth);
});