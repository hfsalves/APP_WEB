// static/js/tesouraria.js

document.addEventListener('DOMContentLoaded', () => {
  const API = '/generic/api/tesouraria'; // esperado: ?start=YYYY-MM-DD&end=YYYY-MM-DD

  const monthYearEl = document.getElementById('month-year');
  const calendarBody = document.getElementById('calendar-body');
  const agendaList = document.getElementById('agendaList');
  const btnPrev = document.getElementById('prev-month');
  const btnNext = document.getElementById('next-month');
  const btnViewCal = document.getElementById('viewCalendarBtn');
  const btnViewAgenda = document.getElementById('viewAgendaBtn');
  const viewCalendar = document.getElementById('calendarView');
  const viewAgenda = document.getElementById('agendaView');

  const monthNames = ['Janeiro','Fevereiro','Março','Abril','Maio','Junho','Julho','Agosto','Setembro','Outubro','Novembro','Dezembro'];
  let current = new Date();
  current = new Date(current.getFullYear(), current.getMonth(), 1);
  let cacheData = [];

  const weekdayMon0 = (d) => (d.getDay() + 6) % 7; // Monday=0
  const toIso = (d) => [d.getFullYear(), String(d.getMonth()+1).padStart(2,'0'), String(d.getDate()).padStart(2,'0')].join('-');

  function getRangeForMonth(base) {
    const first = new Date(base.getFullYear(), base.getMonth(), 1);
    const last = new Date(base.getFullYear(), base.getMonth()+1, 0);
    const start = new Date(first);
    start.setDate(first.getDate() - weekdayMon0(first));
    const end = new Date(last);
    end.setDate(last.getDate() + (6 - weekdayMon0(last)));
    return { first, last, start, end };
  }

  function groupByDate(rows) {
    const today = new Date();
    today.setHours(0,0,0,0);
    const map = new Map();
    (rows || []).forEach(r => {
      const rawDate = r.DATA || r.data || '';
      const d = new Date(rawDate);
      if (Number.isNaN(d)) return;
      if (d < today) return; // não mostrar previsões no passado
      const iso = toIso(d);
      const tipo = (r.TIPO || r.tipo || '').toString().trim().toUpperCase();
      const valor = Number(r.VALOR ?? r.valor ?? 0) || 0;
      const arr = map.get(iso) || [];
      arr.push({ tipo, valor });
      map.set(iso, arr);
    });
    return map;
  }

  function buildCumulative(map, start, end, baseDate) {
    const cum = new Map();
    let sum = 0;
    const base = baseDate ? new Date(baseDate) : new Date(start);
    base.setHours(0,0,0,0);
    // soma prévia se base < start (para manter acumulado vindo de dias anteriores)
    if (base < start) {
      const pre = new Date(base);
      while (pre < start) {
        const isoPre = toIso(pre);
        const listPre = map.get(isoPre) || [];
        listPre.forEach(it => { sum += Number(it.valor || 0) || 0; });
        pre.setDate(pre.getDate() + 1);
      }
    }
    const cursor = new Date(start);
    while (cursor <= end) {
      const iso = toIso(cursor);
      const list = map.get(iso) || [];
      list.forEach(it => { sum += Number(it.valor || 0) || 0; });
      cum.set(iso, sum);
      cursor.setDate(cursor.getDate() + 1);
    }
    return cum;
  }

  function renderCalendar(start, end, dataRows, cumulativeMap) {
    if (!calendarBody) return;
    const map = groupByDate(dataRows);
    const cum = cumulativeMap || buildCumulative(map, start, end);
    calendarBody.innerHTML = '';

    let cursor = new Date(start);
    while (cursor <= end) {
      const tr = document.createElement('tr');
      for (let i = 0; i < 7; i++) {
        const iso = toIso(cursor);
        const list = map.get(iso) || [];
        const sumsByType = {};
        list.forEach(it => {
          const key = it.tipo || 'OUTROS';
          sumsByType[key] = (sumsByType[key] || 0) + Number(it.valor || 0);
        });
        const saldoDia = cum.get(iso) ?? 0;

        const td = document.createElement('td');
        td.className = 'day-cell p-2';
        if (i >= 5) td.classList.add('weekend');
        const todayIso = toIso(new Date());
        if (iso === todayIso) td.classList.add('today');

        const header = document.createElement('div');
        header.className = 'd-flex justify-content-between align-items-center mb-1';
        header.innerHTML = `<span class="day-num">${cursor.getDate()}</span>`;
        td.appendChild(header);

        if (list.length) {
          const wrap = document.createElement('div');
          wrap.className = 'd-flex flex-column gap-1';
          Object.entries(sumsByType).forEach(([tipo, val]) => {
            const cls = tipo === 'EXPLORACAO' ? 'badge-ent' : (tipo === 'GESTAO' ? 'badge-sai' : 'badge-saldo');
            wrap.innerHTML += `<span class="badge-mov ${cls}">${tipo}: ${val.toLocaleString('pt-PT', { minimumFractionDigits: 2 })}</span>`;
          });
          wrap.innerHTML += `<span class="badge-mov badge-saldo">Saldo: ${saldoDia.toLocaleString('pt-PT', { minimumFractionDigits: 2 })}</span>`;
          td.appendChild(wrap);
        }

        tr.appendChild(td);
        cursor.setDate(cursor.getDate() + 1);
      }
      calendarBody.appendChild(tr);
    }
  }

  function renderAgenda(first, last, dataRows, cumulativeMap) {
    if (!agendaList) return;
    const map = groupByDate(dataRows);
    const cum = cumulativeMap || buildCumulative(map, first, last);
    agendaList.innerHTML = '';
    let cursor = new Date(first);
    let added = 0;
    while (cursor <= last) {
      const iso = toIso(cursor);
      const list = map.get(iso) || [];
      const sumsByType = {};
      list.forEach(it => {
        const key = it.tipo || 'OUTROS';
        const val = Number(it.valor || 0) || 0;
        sumsByType[key] = (sumsByType[key] || 0) + val;
      });
      const saldoDia = cum.get(iso) ?? 0;
      const li = document.createElement('div');
      li.className = 'list-group-item';
      li.innerHTML = `
        <div>
          <div class="fw-semibold">${cursor.getDate().toString().padStart(2,'0')}/${(cursor.getMonth()+1).toString().padStart(2,'0')} (${['Seg','Ter','Qua','Qui','Sex','Sáb','Dom'][weekdayMon0(cursor)]})</div>
        </div>
        <div class="mov-labels">
          ${Object.entries(sumsByType).map(([tipo,val]) => {
            const cls = tipo === 'EXPLORACAO' ? 'badge-ent' : (tipo === 'GESTAO' ? 'badge-sai' : 'badge-saldo');
            return `<span class="badge-mov ${cls}">${tipo}: ${val.toLocaleString('pt-PT', { minimumFractionDigits: 2 })}</span>`;
          }).join('')}
          <span class="badge-mov badge-saldo">Saldo: ${saldoDia.toLocaleString('pt-PT', { minimumFractionDigits: 2 })}</span>
        </div>
      `;
      agendaList.appendChild(li);
      added++;
      cursor.setDate(cursor.getDate() + 1);
    }
    if (added === 0) {
      const empty = document.createElement('div');
      empty.className = 'list-group-item text-muted';
      empty.textContent = 'Sem movimentos no período.';
      agendaList.appendChild(empty);
    }
  }

  async function loadDataAndRender() {
    const { first, last, start, end } = getRangeForMonth(current);
    monthYearEl.textContent = `${monthNames[current.getMonth()]} de ${current.getFullYear()}`;
    // buscar também o mês anterior para obter saldo de abertura
    const fetchStart = new Date(current.getFullYear(), current.getMonth() - 1, 1);
    const startStr = toIso(fetchStart);
    const endStr = toIso(end);
    try {
      const res = await fetch(`${API}?start=${startStr}&end=${endStr}`);
      if (!res.ok) throw new Error(res.statusText);
      cacheData = await res.json();
    } catch (e) {
      cacheData = Array.isArray(window.TESOURARIA_DATA) ? window.TESOURARIA_DATA : [];
    }
    // saldo de abertura fixo (sem movimentos reais ainda)
    const today = new Date(); today.setHours(0,0,0,0);
    const cumMap = buildCumulative(groupByDate(cacheData), start, end, today);
    renderCalendar(start, end, cacheData, cumMap);
    renderAgenda(first, last, cacheData, cumMap);
  }

  function switchView(view) {
    if (!viewCalendar || !viewAgenda) return;
    if (view === 'agenda') {
      viewAgenda.style.display = '';
      viewCalendar.style.display = 'none';
      btnViewAgenda?.classList.add('active');
      btnViewCal?.classList.remove('active');
    } else {
      viewAgenda.style.display = 'none';
      viewCalendar.style.display = '';
      btnViewCal?.classList.add('active');
      btnViewAgenda?.classList.remove('active');
    }
  }

  btnPrev?.addEventListener('click', () => {
    current = new Date(current.getFullYear(), current.getMonth() - 1, 1);
    loadDataAndRender();
  });
  btnNext?.addEventListener('click', () => {
    current = new Date(current.getFullYear(), current.getMonth() + 1, 1);
    loadDataAndRender();
  });
  btnViewCal?.addEventListener('click', () => switchView('cal'));
  btnViewAgenda?.addEventListener('click', () => switchView('agenda'));

  loadDataAndRender();
});
