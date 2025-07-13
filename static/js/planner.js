// static/js/planner.js

// =============================
// --- PLANNER LAYOUT CONFIG ---
// =============================
const LAYOUT = {
  tableWidth: 1600,      // px total largura da grelha
  lodging: 190,          // "Alojamento" col
  tp: 30,                // "TP" col
  zone: 68,
  last_team: 50,         // "Últ. Equipa" col
  out: 40,               // "Hora Out" col
  timeslot: 30,          // cada meia hora (07:00, 07:30, ... 23:30)
  trailing: 40           // cada das 4 finais
};

let teams = [];
let openDropdown = null;

// ===========================
document.addEventListener('DOMContentLoaded', function() {
// SÓ depois de carregar equipas é que se faz setup do planner!
fetch('/generic/api/EQ')
.then(r => r.json())
.then(data => {
    teams = data;

    // Agora sim, tudo o resto!
    const dateInput = document.getElementById('planner-date');
    let currentDate = dateInput.value || new Date().toISOString().slice(0,10);

    flatpickr(dateInput, {
    defaultDate: currentDate,
    dateFormat: 'Y-m-d',
    onChange: (_, dateStr) => loadPlanner(dateStr)
    });

    loadPlanner(currentDate);


    document.getElementById('prev-day').addEventListener('click', () => changeDay(-1));
    document.getElementById('next-day').addEventListener('click', () => changeDay(1));

    let planData = [];
    const timeslots = [];
    for (let h = 7; h <= 24; h++) {
    timeslots.push(`${String(h).padStart(2,'0')}:00`);
    if (h < 23) timeslots.push(`${String(h).padStart(2,'0')}:30`);
    }

    function changeDay(offset) {
    const d = new Date(currentDate);
    d.setDate(d.getDate() + offset);
    const iso = d.toISOString().slice(0,10);

    currentDate = iso;  // Atualiza variável global
    dateInput._flatpickr.setDate(iso);  // Atualiza o input
    loadPlanner(iso);   // Faz load do novo dia
    }


    function loadPlanner(date) {
        currentDate = date;
        fetch(`/generic/api/cleaning_plan?date=${date}`)
        .then(res => { if (!res.ok) throw new Error(res.statusText); return res.json(); })
        .then(data => {
            planData = data;
            renderPlanner();
        })
        .catch(err => console.error('Erro ao carregar planner:', err));
    }

    function renderPlanner() {
        const table = document.querySelector('.planner-table');
        table.style.width = `${LAYOUT.tableWidth}px`;
        const headerRow = table.querySelector('thead tr');
        // Rebuild header: fixed + timeslots + trailing
        headerRow.innerHTML = `
        <th style="width:${LAYOUT.lodging}px">Alojamento</th>
        <th style="width:${LAYOUT.tp}px">TP</th>
        <th style="width:${LAYOUT.zone}px">Zona</th>
        <th style="width:${LAYOUT.last_team}px">Últ. Equipa</th>
        <th style="width:${LAYOUT.out}px">Hora Out</th>
        `;
        // Horas no header (uma por cada hora, com colspan=2)
        for (let h = 7; h <= 23; h++) {
        const th = document.createElement('th');
        th.className = 'text-center p-1';
        th.colSpan = 2;
        th.style.minWidth = `${LAYOUT.timeslot*2}px`;
        th.style.width = `${LAYOUT.timeslot*2}px`;
        th.textContent = `${String(h).padStart(2,'0')}:00`;
        headerRow.appendChild(th);
        }
        headerRow.insertAdjacentHTML('beforeend', `
        <th style="width:${LAYOUT.trailing}px">Hora In</th>
        <th style="width:${LAYOUT.trailing}px">Pessoas</th>
        <th style="width:${LAYOUT.trailing}px">Noites</th>
        <th style="width:${LAYOUT.trailing}px">Custo</th>
        `);

        const tbody = document.getElementById('planner-body');
        tbody.innerHTML = '';

        // Sort: first with checkout, then without; both by zone, lodging
        const withOut = planData.filter(r => r.checkout_time);
        const withoutOut = planData.filter(r => !r.checkout_time);
        const sortFn = (a, b) => {
        if (a.zone < b.zone) return -1;
        if (a.zone > b.zone) return 1;
        return a.lodging.localeCompare(b.lodging);
        };
        withOut.sort(sortFn);
        withoutOut.sort(sortFn);
        const ordered = planData;

        ordered.forEach(row => {
        const tr = document.createElement('tr');
        if (!row.checkout_time) {
            // shading for rows without checkout using Bootstrap's table-secondary
            tr.classList.add('table-secondary');
        }
        // Base cols
        let html = `
            <td style="width:${LAYOUT.lodging}px">${row.lodging}</td>
            <td style="width:${LAYOUT.tp}px">${row.typology}</td>
            <td style="width:${LAYOUT.zone}px">${row.zone}</td>
            <td style="width:${LAYOUT.last_team}px">${row.last_team || ''}</td>
            <td style="width:${LAYOUT.out}px">${row.checkout_time || ''}</td>
        `;
        tr.innerHTML = html;
        // Timeslot cells (meia em meia hora)
        timeslots.forEach(slot => {
            const td = document.createElement('td');
            td.className = 'p-0 border-top-0 border-bottom-0';
            td.setAttribute('data-time', slot);
            td.style.width = `${LAYOUT.timeslot}px`;
            td.style.minWidth = `${LAYOUT.timeslot}px`;
            td.style.height = '2rem';
            td.addEventListener('click', (e) => onTimeslotClick(row.lodging, slot, e));
            tr.appendChild(td);
        });
        // Trailing cols
        tr.insertAdjacentHTML('beforeend', `
            <td style="width:${LAYOUT.trailing}px">${row.checkin_time || ''}</td>
            <td style="width:${LAYOUT.trailing}px">${row.checkin_people || ''}</td>
            <td style="width:${LAYOUT.trailing}px">${row.checkin_nights || ''}</td>
            <td style="width:${LAYOUT.trailing}px">${row.cost || 0}</td>
        `);

        tbody.appendChild(tr);

        // ─── Draw checkout Gantt bar as overlay div ───
        (function() {
            let checkout = row.checkout_time;
            if (row.checkout_reservation && (!checkout || checkout === 'N/D')) {
            checkout = '11:00';
            }
            if (!row.checkout_reservation) return; // Só desenha barra se existe reserva de saída
            let [hStr, mStr] = checkout.split(':');
            let hour = parseInt(hStr, 10);
            let mins = parseInt(mStr || '0', 10);
            if (isNaN(hour)) hour = 11;
            if (isNaN(mins)) mins = 0;

            // Colunas fixas: 4 primeiras
            // Usa os valores do LAYOUT diretamente para garantir alinhamento
            let barLeft = 0;
            let endIdx = (hour - 7) * 2;
            if (mins >= 30) endIdx += 1;
            if (endIdx < 0) endIdx = 0;
            if (endIdx > timeslots.length - 1) endIdx = timeslots.length - 1;
            let barWidth =
            20 + 
            LAYOUT.lodging +
            LAYOUT.tp +
            LAYOUT.zone +
            LAYOUT.last_team +
            LAYOUT.out +
            (LAYOUT.timeslot * endIdx) +
            (LAYOUT.timeslot * ((mins % 60) / 30 ? 0.5 : 0)); // se for exatamente :30 acrescenta meia coluna

            tr.querySelectorAll('.gantt-bar-checkout').forEach(el => el.remove());
            const bar = document.createElement('div');
            bar.className = 'gantt-bar-checkout';
            bar.style.position = 'absolute';
            bar.style.top = '6px';
            bar.style.left = `${barLeft}px`;
            bar.style.width = `${barWidth}px`;
            bar.style.height = 'calc(100% - 12px)';
            bar.style.backgroundColor = 'rgba(255, 0, 0, 0.22)';
            bar.style.borderRadius = '12px';
            bar.style.zIndex = '10';
            bar.style.pointerEvents = 'none';
            tr.style.position = 'relative';
            tr.appendChild(bar);
        })();


        // ─── Draw OCCUPIED (bar across if occupied, blue) ───
        (function() {
        // planner_status == 3 → ocupado
        if (row.planner_status === 3) {
            tr.querySelectorAll('.gantt-bar-occupied').forEach(el => el.remove());
            const bar = document.createElement('div');
            bar.className = 'gantt-bar-occupied';
            bar.style.position = 'absolute';
            bar.style.top = '6px';
            bar.style.left = '0px';
            bar.style.width = '1600px';
            bar.style.height = 'calc(100% - 12px)';
            bar.style.backgroundColor = 'rgba(0, 91, 255, 0.12)';
            bar.style.borderRadius = '10px';
            bar.style.zIndex = '7';
            bar.style.pointerEvents = 'none';
            tr.style.position = 'relative';
            tr.appendChild(bar);
        }
        })();


        // ─── Draw checkin Gantt bar as overlay div ───
        (function() {
            let checkin = row.checkin_time;
            if (row.checkin_reservation && (!checkin || checkin === 'N/D')) {
            checkin = '15:00';
            }
            if (!checkin) return; // <- SEGURO! Só entra se houver hora
            let [hStr, mStr] = checkin.split(':');
            let hour = parseInt(hStr, 10);
            let mins = parseInt(mStr || '0', 10);

            // Corrige: se check-in for depois da meia-noite mas antes das 7h (hora começa por "0"), mete na última coluna (23:30)
            if ((hStr.startsWith('0') || hour < 7)) {
            hour = 23;
            mins = 30;
            }
            if (isNaN(hour)) hour = 15;
            if (isNaN(mins)) mins = 0;


            let startIdx = (hour - 7) * 2;
            if (mins >= 30) startIdx += 1;
            if (startIdx < 0) startIdx = 0;
            let endIdx = timeslots.length - 1;
            let barLeft =
            20 +
            LAYOUT.lodging +
            LAYOUT.tp +
            LAYOUT.zone +
            LAYOUT.last_team +
            LAYOUT.out +
            (LAYOUT.timeslot * startIdx);
            let barWidth = LAYOUT.timeslot * (endIdx - startIdx + 1) + 180;

            tr.querySelectorAll('.gantt-bar-checkin').forEach(el => el.remove());
            const bar = document.createElement('div');
            bar.className = 'gantt-bar-checkin';
            bar.style.position = 'absolute';
            bar.style.top = '6px';
            bar.style.left = `${barLeft}px`;
            bar.style.width = `${barWidth}px`;
            bar.style.height = 'calc(100% - 12px)';
            bar.style.backgroundColor = 'rgba(50, 200, 60, 0.22)';
            bar.style.borderRadius = '12px';
            bar.style.zIndex = '8';
            bar.style.pointerEvents = 'none';
            tr.style.position = 'relative';
            tr.appendChild(bar);
        })();

        // ─── Draw cleaning Gantt bar from DB ───
        (function() {
        if (!row.cleaning_team || !row.cleaning_time) return; // Só se existir limpeza agendada
        // Cor da equipa
        const teamColor = (teams.find(t => t.NOME.trim() === row.cleaning_team.trim()) || {}).COR || '#bbb';
        let [hStr, mStr] = row.cleaning_time.split(':');
        let hour = parseInt(hStr, 10), mins = parseInt(mStr||'0',10);
        if (isNaN(hour)) hour = 10;
        if (isNaN(mins)) mins = 0;
        let startIdx = (hour - 7) * 2 + (mins >= 30 ? 1 : 0);
        if (startIdx < 0) startIdx = 0;
        const duration = getCleaningDuration(row.typology || row.tp);
        const slots = Math.ceil(duration/30);
        const barLeft = 20
            + LAYOUT.lodging + LAYOUT.tp + LAYOUT.zone + LAYOUT.last_team + LAYOUT.out
            + (LAYOUT.timeslot * startIdx);
        const barWidth = LAYOUT.timeslot * slots;

        tr.querySelectorAll('.gantt-bar-cleaning').forEach(el => el.remove());
        const bar = document.createElement('div');
        bar.className = 'gantt-bar-cleaning';
        Object.assign(bar.style, {
            position: 'absolute',
            top: '6px',
            left: `${barLeft}px`,
            width: `${barWidth}px`,
            height: '18px',
            backgroundColor: teamColor,
            opacity: '1',
            borderRadius: '8px',
            zIndex: '16',
            pointerEvents: 'auto',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center'
        });
        const label = document.createElement('span');
        Object.assign(label.style, {
            fontSize: '8px',
            fontWeight: 'bold',
            color: '#fff',
            textShadow: '1px 1px 4px #222'
        });
        label.textContent = row.cleaning_team;
        bar.appendChild(label);

        tr.style.position = 'relative';
        tr.appendChild(bar);

        // ao clicar, mostrar menu
        bar.addEventListener('click', e => {
            e.stopPropagation();
            if (openDropdown) { openDropdown.remove(); openDropdown = null; }
            const rect = bar.getBoundingClientRect();
            const menu = document.createElement('div');
            menu.style.zIndex = '20000';
            Object.assign(menu.style, {
            position: 'fixed',
            left: `${rect.left}px`,
            top:  `${rect.bottom}px`,
            background: '#fff',
            border: '1px solid #ccc',
            boxShadow: '0 4px 12px rgba(0,0,0,0.1)',
            borderRadius: '4px'
            });
            [
            { label: 'Abrir', icon: 'fa-regular fa-pen-to-square' },
            { label: 'Eliminar', icon: 'fa-regular fa-trash-can' }
            ].forEach(({ label, icon }) => {
            const item = document.createElement('div');
            Object.assign(item.style, { padding: '4px 8px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '6px' });

            const i = document.createElement('i');
            i.className = icon;
            i.style.minWidth = '18px';

            const span = document.createElement('span');
            span.textContent = label;

            item.append(i, span);

            
            item.addEventListener('click', ev => {
                ev.stopPropagation();
                if (label === 'Abrir') {
                window.open(`/generic/form/LP/${row.cleaning_id}`, '_blank');
                } else {
                fetch(`/generic/api/LP/${row.cleaning_id}`, {
                method: 'DELETE'
                })
                .then(() => loadPlanner(currentDate))
                .catch(err => alert('Erro ao eliminar: '+err));
                }
                menu.remove();
            });
            menu.appendChild(item);
            });
            document.body.appendChild(menu);
            openDropdown = menu;
            setTimeout(() => {
            window.addEventListener('click', () => {
                if (openDropdown) { openDropdown.remove(); openDropdown = null; }
            }, { once: true });
            }, 0);
        });
        })();

    
        });
    }

    // Função utilitária para calcular a duração da limpeza
    function getCleaningDuration(typology) {
    switch ((typology || '').trim()) {
        case "T0":
        case "T1":
        return 60;      // 1 hora
        case "T2":
        case "T3":
        return 90;      // 1h30
        case "T4":
        case "T5":
        return 120;     // 2h
        default:
        return 60;      // 1 hora para vazio ou não definido
    }
    }

    function onTimeslotClick(lodging, slot, event) {
    event && event.stopPropagation();
    if (openDropdown) {
        openDropdown.remove();
        openDropdown = null;
    }
    const td = event?.currentTarget || document.querySelector(`td[data-time='${slot}']`);
    const rect = td.getBoundingClientRect();
    const tr = td.closest('tr');
    const row = planData.find(r => r.lodging === lodging);
    console.log('row:', row);

    // Dropdown para escolher equipa
    const dropdown = document.createElement('div');
    dropdown.className = 'team-dropdown';
    dropdown.style.position = 'fixed';
    dropdown.style.left = rect.left + 'px';
    dropdown.style.top = rect.bottom + 'px';
    dropdown.style.minWidth = '140px';
    dropdown.style.background = '#fff';
    dropdown.style.border = '1px solid #ccc';
    dropdown.style.zIndex = 20000;
    dropdown.style.boxShadow = '0 4px 12px rgba(0,0,0,0.1)';
    dropdown.style.fontSize = '13px';
    dropdown.style.padding = '2px 0';
    dropdown.style.borderRadius = '8px';

    teams.forEach(team => {
        const item = document.createElement('div');
        item.className = 'dropdown-item py-1 px-2';
        item.textContent = team.NOME;
        item.style.cursor = 'pointer';
        item.style.display = 'flex';
        item.style.alignItems = 'center';
        if (team.COR) {
        const dot = document.createElement('span');
        dot.style.display = 'inline-block';
        dot.style.width = '10px';
        dot.style.height = '10px';
        dot.style.borderRadius = '50%';
        dot.style.marginRight = '8px';
        dot.style.background = team.COR;
        item.prepend(dot);
        }
        item.onclick = function(e) {
        e.stopPropagation();
        if (openDropdown) openDropdown.remove();
        openDropdown = null;
        desenhaBarraEquipa(tr, td, slot, row, team); // NOVO: desenha barra
        };
        dropdown.appendChild(item);
    });
    document.body.appendChild(dropdown);
    openDropdown = dropdown;
    setTimeout(() => {
        window.addEventListener('click', closeDropdown, { once: true });
    }, 0);
    function closeDropdown() {
        if (openDropdown) openDropdown.remove();
        openDropdown = null;
    }
    }

    // Função para desenhar a barra de equipa
    function desenhaBarraEquipa(tr, td, slot, row, team) {
    // Limpa barras antigas desenhadas pelo user (não remove as de checkin/checkout)
    tr.querySelectorAll('.gantt-bar-team').forEach(el => el.remove());

    // Duração da barra, conforme tipologia
    let tp = ((row && (row.typology || row.tp || '')) + '').toUpperCase().trim();


    const minutos = getCleaningDuration(row.typology);

    // Índice do slot clicado
    const idx = Array.from(td.parentNode.children).indexOf(td) - 3; // menos colunas fixas
    const startIdx = idx;
    const slots = Math.ceil(minutos / 30); // quantos slots ocupa (30min cada)
    const barLeft =
        30 +
        LAYOUT.lodging +
        LAYOUT.tp +
        LAYOUT.last_team +
        LAYOUT.out +
        (LAYOUT.timeslot * startIdx);
    const barWidth = LAYOUT.timeslot * slots;

    // Desenha barra
    const bar = document.createElement('div');
    bar.className = 'gantt-bar-team';
    bar.style.position = 'absolute';
    bar.style.top = '6px';
    bar.style.left = `${barLeft}px`;
    bar.style.width = `${barWidth}px`;
    bar.style.height = 'calc(100% - 12px)';
    bar.style.backgroundColor = team.COR || '#999';
    bar.style.opacity = '0.4';
    bar.style.borderRadius = '10px';
    bar.style.zIndex = '18';
    bar.style.pointerEvents = 'none';
    bar.style.display = 'flex';
    bar.style.alignItems = 'center';
    bar.style.justifyContent = 'center';

    // Texto na barra
    const label = document.createElement('span');
    label.textContent = team.NOME;
    label.style.fontSize = '8px';
    label.style.fontWeight = 'bold';
    label.style.color = '#fff';
    label.style.textShadow = '1px 1px 4px #222';
    label.style.margin = 'auto';
    bar.appendChild(label);

    tr.style.position = 'relative';
    tr.appendChild(bar);
    }


    function recolherLimpezasParaGravar() {
    const result = [];
    document.querySelectorAll('.gantt-bar-team').forEach(bar => {
        const tr = bar.closest('tr');
        if (!tr) return;
        // Extrair alojamento e data
        const alojamento = tr.children[0].textContent.trim();
        const typology = tr.children[2].textContent.trim(); // se quiseres usar
        // Extrair hora de início (slot)
        // O left da barra -> slot inicial
        const left = parseInt(bar.style.left, 10) || 0;
        // Calcula o índice do slot
        const colFixas = 7; // zona, alojamento, tp, last_team, out
        const idx = Math.round((left - 400) / LAYOUT.timeslot);
        const h = 7 + Math.floor(idx / 2);
        const m = (idx % 2) ? "30" : "00";
        const hora = `${String(h).padStart(2, '0')}:${m}`;
        // Equipa: texto dentro da barra
        const equipa = bar.textContent.trim();
        result.push({
        ALOJAMENTO: alojamento,
        DATA: document.getElementById('planner-date').value,
        HORA: hora,
        EQUIPA: equipa
        // podes adicionar +campos aqui se quiseres
        });
    });
    return result;
    }



    document.getElementById('save-planner').addEventListener('click', () => {
    const limpezas = recolherLimpezasParaGravar();

    if (limpezas.length === 0) {
        alert("Nada para gravar.");
        return;
    }

    fetch('/generic/api/LP/gravar', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(limpezas)
    })
    .then(res => res.json())
    .then(resp => {
        if (resp.success) {
            alert("Limpezas gravadas!");
            loadPlanner(currentDate);
            const mainContent = document.querySelector('.main-content');
            if (mainContent) {
            mainContent.scrollTo({ top: 0, behavior: 'smooth' });
            } else {
            // fallback: tenta no window
            window.scrollTo({ top: 0, behavior: 'smooth' });
            }
        } else {
        alert("Erro ao gravar limpezas.");
        }
    })
    .catch(err => alert("Falha ao gravar limpezas: " + err));
    });


    document.getElementById('cancel-planner').addEventListener('click', () => loadPlanner(currentDate));

    flatpickr(dateInput, {
    defaultDate: currentDate,
    dateFormat: 'Y-m-d',
    onChange: (_, dateStr) => loadPlanner(dateStr)
    });

    loadPlanner(currentDate);


    
    })


.catch(err => console.error("Erro a carregar equipas:", err));
});