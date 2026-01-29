// static/js/tesouraria.js

document.addEventListener('DOMContentLoaded', () => {
  const API = '/generic/api/tesouraria'; // esperado: ?start=YYYY-MM-DD&end=YYYY-MM-DD
  const API_BA = '/generic/api/tesouraria/ba'; // esperado: ?start=YYYY-MM-DD&end=YYYY-MM-DD
  const API_BA_BASE = '/generic/api/tesouraria/ba/saldo_base'; // ?before=YYYY-MM-DD
  const API_BA_EXTRATO = '/generic/api/tesouraria/ba/extrato'; // ?start=YYYY-MM-DD&end=YYYY-MM-DD

  const monthYearEl = document.getElementById('month-year');
  const calendarBody = document.getElementById('calendar-body');
  const agendaList = document.getElementById('agendaList');
  const btnPrev = document.getElementById('prev-month');
  const btnNext = document.getElementById('next-month');
  const btnViewCal = document.getElementById('viewCalendarBtn');
  const btnViewAgenda = document.getElementById('viewAgendaBtn');
  const btnViewExtrato = document.getElementById('viewExtratoBtn');
  const viewCalendar = document.getElementById('calendarView');
  const viewAgenda = document.getElementById('agendaView');
  const viewExtrato = document.getElementById('extratoView');
  const extratoBody = document.getElementById('extratoBody');
  const accountFilter = document.getElementById('accountFilter');
  const baDetailModalEl = document.getElementById('baDetailModal');
  const baDetailTitle = document.getElementById('baDetailTitle');
  const baDetailBody = document.getElementById('baDetailBody');
  const baDetailTotal = document.getElementById('baDetailTotal');
  const baDetailModal = baDetailModalEl ? new bootstrap.Modal(baDetailModalEl) : null;

  const monthNames = ['Janeiro','Fevereiro','Março','Abril','Maio','Junho','Julho','Agosto','Setembro','Outubro','Novembro','Dezembro'];
  let current = new Date();
  current = new Date(current.getFullYear(), current.getMonth(), 1);
  let cacheData = [];
  let cacheBa = [];
  let cacheBaExtrato = [];

  const fmt = (n) => Number(n || 0).toLocaleString('pt-PT', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
    useGrouping: true
  });

  const escapeHtml = (str) => String(str == null ? '' : str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');

  const weekdayMon0 = (d) => (d.getDay() + 6) % 7; // Monday=0
  const toIso = (d) => [d.getFullYear(), String(d.getMonth()+1).padStart(2,'0'), String(d.getDate()).padStart(2,'0')].join('-');

  function toIsoFromRaw(rawDate) {
    if (!rawDate) return '';
    if (typeof rawDate === 'string') {
      const s = rawDate.trim();
      if (s.length >= 10 && /^\d{4}-\d{2}-\d{2}/.test(s)) return s.slice(0, 10);
    }
    const d = new Date(rawDate);
    if (Number.isNaN(d)) return '';
    return toIso(d);
  }

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

  function groupBaByDate(rows) {
    const map = new Map(); // iso -> { entrada, saida }
    (rows || []).forEach(r => {
      const iso = toIsoFromRaw(r.DATA || r.data || '');
      if (!iso) return;
      const entrada = Number(r.EENTRADA ?? r.eentrada ?? 0) || 0;
      const saida = Number(r.ESAIDA ?? r.esaida ?? 0) || 0;
      const cur = map.get(iso) || { entrada: 0, saida: 0 };
      cur.entrada += entrada;
      cur.saida += saida;
      map.set(iso, cur);
    });
    return map;
  }

  function groupBaExtratoByDate(rows) {
    const map = new Map(); // iso -> array of { kind, documento, descricao, valor }
    (rows || []).forEach(r => {
      const iso = toIsoFromRaw(r.DATA || r.data || '');
      if (!iso) return;
      const kind = (r.KIND || r.kind || '').toString().trim().toLowerCase();
      const documento = (r.DOCUMENTO || r.documento || '').toString().trim();
      const descricao = (r.DESCRICAO || r.descricao || '').toString().trim();
      const valor = Number(r.VALOR ?? r.valor ?? 0) || 0;
      const arr = map.get(iso) || [];
      arr.push({ kind, documento, descricao, valor });
      map.set(iso, arr);
    });
    return map;
  }

  function renderExtrato(first, last, dataRows, baseSum, baExtratoRows) {
    if (!extratoBody) return;
    const preMap = groupByDate(dataRows); // previsões só no futuro
    const baMap = groupBaExtratoByDate(baExtratoRows);

    const rows = [];
    let saldo = Number(baseSum || 0) || 0;

    // saldo inicial
    rows.push({
      date: toIso(first),
      desc: 'Saldo inicial',
      in: '',
      out: '',
      saldo
    });

    let cursor = new Date(first);
    while (cursor <= last) {
      const iso = toIso(cursor);
      const dayBa = baMap.get(iso) || [];
      const dayPrevList = preMap.get(iso) || [];
      const dayPrev = dayPrevList.reduce((acc, it) => acc + (Number(it.valor || 0) || 0), 0);

      // ordenar dentro do dia: entradas, saídas, previsões (como no calendário)
      const ins = dayBa.filter(x => x.kind === 'in');
      const outs = dayBa.filter(x => x.kind === 'out');

      ins.forEach(m => {
        saldo += Number(m.valor || 0) || 0;
        const d = [m.documento, m.descricao].filter(Boolean).join(' - ') || 'Entrada';
        rows.push({ date: iso, desc: d, in: Number(m.valor || 0), out: '', saldo, cls: 'extrato-kind-in' });
      });
      outs.forEach(m => {
        const v = Number(m.valor || 0) || 0;
        saldo -= v;
        const d = [m.documento, m.descricao].filter(Boolean).join(' - ') || 'Saída';
        rows.push({ date: iso, desc: d, in: '', out: v, saldo, cls: 'extrato-kind-out' });
      });
      if (Number(dayPrev || 0) !== 0) {
        saldo += dayPrev;
        const isIn = dayPrev >= 0;
        rows.push({
          date: iso,
          desc: 'Previsões',
          in: isIn ? dayPrev : '',
          out: !isIn ? Math.abs(dayPrev) : '',
          saldo,
          cls: 'extrato-kind-prev'
        });
      }

      cursor.setDate(cursor.getDate() + 1);
    }

    extratoBody.innerHTML = '';
    if (!rows.length) {
      extratoBody.innerHTML = '<tr><td colspan="5" class="text-muted text-center p-3">Sem movimentos.</td></tr>';
      return;
    }
    rows.forEach(r => {
      const tr = document.createElement('tr');
      const desc = escapeHtml(r.desc || '');
      const inVal = r.in === '' ? '' : fmt(r.in);
      const outVal = r.out === '' ? '' : fmt(r.out);
      const saldoCls = (Number(r.saldo || 0) < 0) ? 'text-danger' : '';
      tr.innerHTML = `
        <td>${escapeHtml(r.date)}</td>
        <td class="extrato-desc ${r.cls || ''}">${desc}</td>
        <td class="text-end ${r.cls === 'extrato-kind-in' ? 'extrato-kind-in' : ''}">${escapeHtml(inVal)}</td>
        <td class="text-end ${r.cls === 'extrato-kind-out' ? 'extrato-kind-out' : ''}">${escapeHtml(outVal)}</td>
        <td class="text-end fw-bold ${saldoCls}">${escapeHtml(fmt(r.saldo))}</td>
      `;
      extratoBody.appendChild(tr);
    });
  }

  async function openBaDetail(dateIso, kind) {
    if (!baDetailModal || !baDetailBody) return;
    const kindLabel = kind === 'in' ? 'Entradas' : 'Saídas';
    if (baDetailTitle) baDetailTitle.textContent = `${kindLabel} - ${dateIso}`;
    if (baDetailTotal) baDetailTotal.textContent = 'Total: --';
    baDetailBody.innerHTML = `<tr><td colspan="3" class="text-center text-muted">A carregar...</td></tr>`;
    baDetailModal.show();
    try {
      const qs = new URLSearchParams({ date: dateIso, kind });
      const res = await fetch(`/generic/api/tesouraria/ba/detalhe?${qs.toString()}`);
      const data = await res.json().catch(() => ({}));
      if (!res.ok || data.error) throw new Error(data.error || res.statusText);
      const rows = Array.isArray(data.rows) ? data.rows : [];
      if (!rows.length) {
        baDetailBody.innerHTML = `<tr><td colspan="3" class="text-center text-muted">Sem movimentos.</td></tr>`;
      } else {
        baDetailBody.innerHTML = rows.map(r => `
          <tr>
            <td>${escapeHtml(r.documento || '')}</td>
            <td>${escapeHtml(r.descricao || '')}</td>
            <td class="text-end fw-semibold">${fmt(r.valor || 0)}</td>
          </tr>
        `).join('');
      }
      if (baDetailTotal) baDetailTotal.textContent = `Total: ${fmt(data.total || 0)}`;
    } catch (err) {
      baDetailBody.innerHTML = `<tr><td colspan="3" class="text-center text-danger">${escapeHtml(err.message || 'Erro')}</td></tr>`;
      if (baDetailTotal) baDetailTotal.textContent = 'Total: --';
    }
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

  function buildCumulativeCombined(preMap, baMap, start, end, baseSum) {
    const cum = new Map();
    let sum = Number(baseSum || 0) || 0;

    const addDayNet = (iso) => {
      const preList = preMap.get(iso) || [];
      const preSum = preList.reduce((acc, it) => acc + (Number(it.valor || 0) || 0), 0);
      const ba = baMap.get(iso) || { entrada: 0, saida: 0 };
      const baNet = (Number(ba.entrada || 0) || 0) - (Number(ba.saida || 0) || 0);
      sum += preSum + baNet;
    };

    const cursor = new Date(start);
    while (cursor <= end) {
      const iso = toIso(cursor);
      addDayNet(iso);
      cum.set(iso, sum);
      cursor.setDate(cursor.getDate() + 1);
    }
    return cum;
  }

  function renderCalendar(start, end, dataRows, cumulativeMap, baRows) {
    if (!calendarBody) return;
    const map = groupByDate(dataRows);
    const baMap = groupBaByDate(baRows);
    const cum = cumulativeMap || buildCumulativeCombined(map, baMap, start, end, 0);
    calendarBody.innerHTML = '';

    let cursor = new Date(start);
    while (cursor <= end) {
      const tr = document.createElement('tr');
      for (let i = 0; i < 7; i++) {
        const iso = toIso(cursor);
        const list = map.get(iso) || [];
        const previsao = list.reduce((acc, it) => acc + (Number(it.valor || 0) || 0), 0);
        const saldoDia = cum.get(iso) ?? 0;
        const ba = baMap.get(iso) || { entrada: 0, saida: 0 };

        const td = document.createElement('td');
        td.className = 'day-cell p-2';
        if (i >= 5) td.classList.add('weekend');
        const todayIso = toIso(new Date());
        if (iso === todayIso) td.classList.add('today');

        const header = document.createElement('div');
        header.className = 'd-flex justify-content-between align-items-center mb-1';
        header.innerHTML = `<span class="day-num">${cursor.getDate()}</span>`;
        td.appendChild(header);

        const wrap = document.createElement('div');
        wrap.className = 'd-flex flex-column gap-1 day-cards';

        const cashCards = [];
        if (Number(ba.entrada || 0) !== 0) cashCards.push(`<button type="button" class="cash-card in js-ba-detail" data-date="${iso}" data-kind="in" title="Entradas">▲ ${fmt(ba.entrada)}</button>`);
        if (Number(ba.saida || 0) !== 0) cashCards.push(`<button type="button" class="cash-card out js-ba-detail" data-date="${iso}" data-kind="out" title="Saídas">▼ ${fmt(ba.saida)}</button>`);
        if (Number(previsao || 0) !== 0) cashCards.push(`<span class="cash-card prev" title="Previsões" aria-label="Previsões"><i class="fa-regular fa-calendar"></i> ${fmt(previsao)}</span>`);
        if (cashCards.length) wrap.innerHTML += `<div class="cash-cards cash-cards-vertical">${cashCards.join('')}</div>`;

        wrap.innerHTML += `<span class="badge-mov badge-saldo">${fmt(saldoDia)}</span>`;
        td.appendChild(wrap);

        tr.appendChild(td);
        cursor.setDate(cursor.getDate() + 1);
      }
      calendarBody.appendChild(tr);
    }
  }
  function renderAgenda(first, last, dataRows, cumulativeMap, baRows) {
    if (!agendaList) return;
    const map = groupByDate(dataRows);
    const baMap = groupBaByDate(baRows);
    const cum = cumulativeMap || buildCumulativeCombined(map, baMap, first, last, 0);
    agendaList.innerHTML = '';
    let cursor = new Date(first);
    let added = 0;
    while (cursor <= last) {
      const iso = toIso(cursor);
      const list = map.get(iso) || [];
      const previsao = list.reduce((acc, it) => acc + (Number(it.valor || 0) || 0), 0);
      const saldoDia = cum.get(iso) ?? 0;
      const ba = baMap.get(iso) || { entrada: 0, saida: 0 };
      const li = document.createElement('div');
      const wd = weekdayMon0(cursor);
      li.className = 'list-group-item' + (wd >= 5 ? ' weekend' : '');

      const badges = [];
      if (Number(ba.entrada || 0) !== 0) badges.push(`<button type="button" class="cash-card in js-ba-detail" data-date="${iso}" data-kind="in" title="Entradas">▲ ${fmt(ba.entrada)}</button>`);
      if (Number(ba.saida || 0) !== 0) badges.push(`<button type="button" class="cash-card out js-ba-detail" data-date="${iso}" data-kind="out" title="Saídas">▼ ${fmt(ba.saida)}</button>`);
      if (Number(previsao || 0) !== 0) badges.push(`<span class="cash-card prev" title="Previsões" aria-label="Previsões"><i class="fa-regular fa-calendar"></i> ${fmt(previsao)}</span>`);

      li.innerHTML = `
        <div>
          <div class="fw-semibold">${cursor.getDate().toString().padStart(2,'0')}/${(cursor.getMonth()+1).toString().padStart(2,'0')} (${['Seg','Ter','Qua','Qui','Sex','Sáb','Dom'][wd]})</div>
        </div>
        <div class="mov-labels">
          ${badges.join('')}
          <span class="badge-mov badge-saldo">${fmt(saldoDia)}</span>
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
  async function loadAccounts() {
    if (!accountFilter) return;
    try {
      const res = await fetch('/generic/api/tesouraria/contas');
      if (!res.ok) throw new Error(res.statusText);
      const contas = await res.json();
      accountFilter.innerHTML = '<option value="">Todas</option>';
      contas.forEach(c => {
        const opt = document.createElement('option');
        opt.value = c.NOCONTA ?? c.noconta ?? '';
        const banco = c.BANCO || c.banco || '';
        const conta = c.CONTA || c.conta || '';
        opt.textContent = [banco, conta].filter(Boolean).join(' - ');
        accountFilter.append(opt);
      });
    } catch (_) {}
  }

  async function loadDataAndRender() {
    const { first, last, start, end } = getRangeForMonth(current);
    monthYearEl.textContent = `${monthNames[current.getMonth()]} de ${current.getFullYear()}`;
    // buscar também o mês anterior para obter saldo de abertura
    const fetchStart = new Date(current.getFullYear(), current.getMonth() - 1, 1);
    const startStr = toIso(fetchStart);
    const endStr = toIso(end);
    const startGridStr = toIso(start);
    const endGridStr = toIso(end);
    const account = accountFilter?.value || '';
    try {
      const url = new URL(API, window.location.origin);
      url.searchParams.set('start', startStr);
      url.searchParams.set('end', endStr);
      if (account) url.searchParams.set('account', account);
      const res = await fetch(url.toString());
      if (!res.ok) throw new Error(res.statusText);
      cacheData = await res.json();
    } catch (e) {
      cacheData = Array.isArray(window.TESOURARIA_DATA) ? window.TESOURARIA_DATA : [];
    }
    try {
      const urlBa = new URL(API_BA, window.location.origin);
      urlBa.searchParams.set('start', startGridStr);
      urlBa.searchParams.set('end', endGridStr);
      const resBa = await fetch(urlBa.toString());
      if (!resBa.ok) throw new Error(resBa.statusText);
      cacheBa = await resBa.json();
    } catch (_) {
      cacheBa = [];
    }

    try {
      const urlEx = new URL(API_BA_EXTRATO, window.location.origin);
      urlEx.searchParams.set('start', toIso(first));
      urlEx.searchParams.set('end', toIso(last));
      const resEx = await fetch(urlEx.toString());
      if (!resEx.ok) throw new Error(resEx.statusText);
      cacheBaExtrato = await resEx.json();
    } catch (_) {
      cacheBaExtrato = [];
    }
    const preMap = groupByDate(cacheData);
    const baMap = groupBaByDate(cacheBa);
    let baseSum = 0;
    try {
      const urlBase = new URL(API_BA_BASE, window.location.origin);
      urlBase.searchParams.set('before', startGridStr);
      const resBase = await fetch(urlBase.toString());
      const dataBase = await resBase.json().catch(() => ({}));
      if (!resBase.ok || dataBase.error) throw new Error(dataBase.error || resBase.statusText);
      baseSum = Number(dataBase.base || 0) || 0;
    } catch (_) {
      baseSum = 0;
    }
    // saldo do dia (base de sempre + previsões + movimentos reais)
    const cumMap = buildCumulativeCombined(preMap, baMap, start, end, baseSum);
    renderCalendar(start, end, cacheData, cumMap, cacheBa);
    renderAgenda(first, last, cacheData, cumMap, cacheBa);
    renderExtrato(first, last, cacheData, baseSum, cacheBaExtrato);
  }

  function switchView(view) {
    if (!viewCalendar || !viewAgenda || !viewExtrato) return;
    if (view === 'agenda') {
      viewAgenda.style.display = '';
      viewCalendar.style.display = 'none';
      viewExtrato.style.display = 'none';
      btnViewAgenda?.classList.add('active');
      btnViewCal?.classList.remove('active');
      btnViewExtrato?.classList.remove('active');
    } else if (view === 'extrato') {
      viewAgenda.style.display = 'none';
      viewCalendar.style.display = 'none';
      viewExtrato.style.display = '';
      btnViewExtrato?.classList.add('active');
      btnViewCal?.classList.remove('active');
      btnViewAgenda?.classList.remove('active');
    } else {
      viewAgenda.style.display = 'none';
      viewCalendar.style.display = '';
      viewExtrato.style.display = 'none';
      btnViewCal?.classList.add('active');
      btnViewAgenda?.classList.remove('active');
      btnViewExtrato?.classList.remove('active');
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
  accountFilter?.addEventListener('change', () => loadDataAndRender());
  btnViewCal?.addEventListener('click', () => switchView('cal'));
  btnViewAgenda?.addEventListener('click', () => switchView('agenda'));
  btnViewExtrato?.addEventListener('click', () => switchView('extrato'));

  loadAccounts().then(loadDataAndRender);

  // Delegação: clique em cards de entradas/saídas abre detalhe
  document.addEventListener('click', (e) => {
    const btn = e.target.closest?.('.js-ba-detail');
    if (!btn) return;
    const dateIso = btn.dataset.date || '';
    const kindRaw = (btn.dataset.kind || '').toLowerCase();
    const kind = kindRaw === 'in' ? 'in' : 'out';
    if (!dateIso) return;
    openBaDetail(dateIso, kind);
  });
});
