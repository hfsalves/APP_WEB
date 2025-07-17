// static/js/dynamic_list.js
// Lista genérica com modal de filtros, suporte a intervalo de datas e ordenação.

document.addEventListener('DOMContentLoaded', () => {
  const tableName       = window.TABLE_NAME;
  const gridDiv         = document.getElementById('grid');
  const btnFilterToggle = document.getElementById('btnFilterToggle');
  const btnNew          = document.getElementById('btnNew');
  const modalFiltros    = document.getElementById('modalFiltros');
  const filterForm      = document.getElementById('filter-form');
  const userPerms       = window.USER_PERMS[tableName] || {};
  let currentCols       = [];


  // transforma o “Filtrar” e o “Novo” em icon-only e os alinha lado‐a‐lado
  btnFilterToggle.innerHTML = '<i class="fa fa-filter"></i>';
  btnFilterToggle.className = 'btn btn-outline-secondary me-2';

  btnNew.innerHTML = '<i class="fa fa-plus"></i>';
  btnNew.className = 'btn btn-outline-primary';

  // garante que ficam juntos
  const header = document.querySelector('.dynamic-header');
  header.classList.add('d-flex', 'align-items-center');

  // —— ICON-ONLY BUTTONS ——
  // Renderiza só o ícone e alinha-os lado a lado
  if (btnFilterToggle) {
    btnFilterToggle.innerHTML = '<i class="fa fa-filter"></i>';
    btnFilterToggle.classList.add('btn', 'btn-outline-secondary', 'me-2');
  }
  if (btnNew) {
    btnNew.innerHTML = '<i class="fa fa-plus"></i>';
    btnNew.classList.add('btn', 'btn-primary');
  }
  // — end ICON-ONLY BUTTONS —

  // 1) Sem permissão de consulta, aborta
  if (!userPerms.consultar) {
    alert('Sem permissão para consultar esta lista.');
    return;
  }

  // 2) Move o modal de filtros para <body> (fora do blur)
  document.body.appendChild(modalFiltros);

  // 3) Botão “Filtrar” abre modal e aplica blur só no fundo
  btnFilterToggle.addEventListener('click', () => {
    document.body.classList.add('modal-filtros-open');
    const modal = bootstrap.Modal.getOrCreateInstance(modalFiltros);
    modal.show();
    modalFiltros.addEventListener('hidden.bs.modal', () => {
      document.body.classList.remove('modal-filtros-open');
    }, { once: true });
  });

  // 4) Botão “Novo”
  if (btnNew) {
    btnNew.addEventListener('click', () => {
      location.href = `/generic/form/${tableName}/`;
    });
  }

  // 5) Ao submeter filtros, esconde modal e carrega dados
  filterForm.addEventListener('submit', e => {
    e.preventDefault();
    bootstrap.Modal.getInstance(modalFiltros).hide();
    loadData();
  });

  // 5) Submit do form de filtros
  filterForm.addEventListener('submit', e => {
    e.preventDefault();
    bootstrap.Modal.getInstance(modalFiltros).hide();
    loadData();
  });

  // 6) Botão pequeno “Aplicar”
  if (applyFilters) {
    applyFilters.addEventListener('click', () => {
      filterForm.requestSubmit();
    });
  }  

  // 6) Inicialização da lista
  initListView().catch(console.error);

  // guarda os dados e estado de ordenação
  let dataRows = [];
  let sortField = null;
  let sortDir = 1; // 1 = asc, -1 = desc

  function showLoading() {
    const overlay = document.getElementById('loadingOverlay');
    overlay.style.display = 'flex';
    setTimeout(() => overlay.style.opacity = '1', 15);
  }
  function hideLoading() {
    const overlay = document.getElementById('loadingOverlay');
    overlay.style.opacity = '0';
    setTimeout(() => overlay.style.display = 'none', 250); // espera pelo fade-out
  }


  async function initListView() {
    // a) Describe para metadados
    let meta;
    try {
      const res = await fetch(`/generic/api/${tableName}?action=describe`);
      if (!res.ok) throw new Error(res.statusText);
      meta = await res.json();
    } catch (e) {
      console.error('Falha ao carregar metadados:', e);
      gridDiv.innerHTML = `<p class="text-danger">Erro ao carregar filtros.</p>`;
      return;
    }
    // b) Separa colunas de filtros e de listagem
    const filterCols = meta.filter(c => c.filtro);
    currentCols      = meta.filter(c => c.lista);

    // c) Monta filtros no modal
    renderFilters(filterCols);

    // d) Load inicial de dados
    showLoading()

    await loadData();

    hideLoading()
  
  }
  

  function renderFilters(cols) {
    filterForm.innerHTML = '';
    filterForm.className  = 'row g-3';

    cols.forEach(col => {
      // DATE cria “De” e “Até”
      if (col.tipo === 'DATE') {
        ['from','to'].forEach((dir, i) => {
          const wrap = document.createElement('div');
          wrap.classList.add('col-md-6');
          const lbl = document.createElement('label');
          lbl.classList.add('form-label');
          lbl.textContent = `${col.descricao || col.name} (${dir==='from'?'De':'Até'})`;
          const inp = document.createElement('input');
          inp.type     = 'date';
          inp.name     = `${col.name}_${dir}`;
          inp.classList.add('form-control');
          wrap.append(lbl, inp);
          filterForm.append(wrap);
        });

      // COMBO
      } else if (col.tipo === 'COMBO') {
        const wrap = document.createElement('div');
        wrap.classList.add('col-md-6');
        const lbl = document.createElement('label');
        lbl.classList.add('form-label');
        lbl.textContent = col.descricao || col.name;
        const sel = document.createElement('select');
        sel.name = col.name;
        sel.classList.add('form-select');
        sel.innerHTML = '<option value="">---</option>';
        wrap.append(lbl, sel);
        filterForm.append(wrap);

        // Popula async
        (async () => {
          let opts = [];
          try {
            if (/^\s*SELECT\s+/i.test(col.combo)) {
              opts = await (await fetch(
                `/generic/api/options?query=${encodeURIComponent(col.combo)}`
              )).json();
            } else {
              opts = await (await fetch(col.combo)).json();
            }
          } catch (e) {
            console.error('Erro COMBO', col.name, e);
          }
          opts.forEach(o => {
            const v   = typeof o === 'object' ? Object.values(o)[0] : o;
            const opt = document.createElement('option');
            opt.value       = v ?? '';
            opt.textContent = v;
            sel.append(opt);
          });
        })();

      // Intervalo de datas
      } else if (col.tipo === 'DATE') {
        // (handled above)

      // BIT
      } else if (col.tipo === 'BIT') {
        const wrap = document.createElement('div');
        wrap.classList.add('col-md-6','form-check');
        const inp = document.createElement('input');
        inp.type  = 'checkbox';
        inp.name  = col.name;
        inp.id    = col.name;
        inp.classList.add('form-check-input');
        const lbl = document.createElement('label');
        lbl.classList.add('form-check-label','ms-2');
        lbl.setAttribute('for', col.name);
        lbl.textContent = col.descricao || col.name;
        wrap.append(inp, lbl);
        filterForm.append(wrap);

      // Outros
      } else {
        const wrap = document.createElement('div');
        wrap.classList.add('col-md-6');
        const lbl = document.createElement('label');
        lbl.classList.add('form-label');
        lbl.textContent = col.descricao || col.name;
        const inp = document.createElement('input');
        inp.name = col.name;
        inp.classList.add('form-control');
        switch (col.tipo) {
          case 'HOUR':    inp.type = 'time';    break;
          case 'INT':     inp.type = 'number';  inp.step = '1';    break;
          case 'DECIMAL': inp.type = 'number';  inp.step = '0.01'; break;
          default:        inp.type = 'text';
        }
        wrap.append(lbl, inp);
        filterForm.append(wrap);
      }
    });
  }

  

  async function loadData() {
    const params = new URLSearchParams();
    filterForm.querySelectorAll('[name]').forEach(el => {
      if (el.type === 'checkbox') {
        if (el.checked) params.append(el.name, '1');
      } else if (el.value) {
        params.append(el.name, el.value);
      }
    });

    const url = `/generic/api/${tableName}` +
      (params.toString() ? '?' + params.toString() : '');
    const res = await fetch(url);
    if (!res.ok) {
      gridDiv.innerHTML = `<p class="text-danger">Erro ${res.status}</p>`;
      return;
    }
    dataRows = await res.json();
    renderTable(currentCols, dataRows);
  }

  function renderTable(cols, rows) {
    gridDiv.innerHTML = '';
    const table = document.createElement('table');
    table.classList.add('table','table-hover','align-middle');

    // Cabeçalho com ordenação
    const thead = document.createElement('thead');
    const trh   = document.createElement('tr');
    cols.forEach((c, idx) => {
      const th = document.createElement('th');
      th.textContent = c.descricao || c.name;
      th.style.cursor = 'pointer';
      th.addEventListener('click', () => {
        sortDir   = (sortField === c.name) ? -sortDir : 1;
        sortField = c.name;
        dataRows.sort((a, b) => {
          let va = a[c.name], vb = b[c.name], res = 0;
          switch (c.tipo) {
            case 'INT':    res = (Number(va)||0) - (Number(vb)||0); break;
            case 'DECIMAL':res = (Number(va)||0) - (Number(vb)||0); break;
            case 'DATE':   res = new Date(va) - new Date(vb);      break;
            case 'BIT':    res = ((va?1:0) - (vb?1:0));             break;
            default:       res = String(va||'').localeCompare(String(vb||''));
          }
          return res * sortDir;
        });
        renderTable(cols, dataRows);
      });
      trh.append(th);
    });
    thead.append(trh);
    table.append(thead);

    // Corpo
    const tbody = document.createElement('tbody');
    rows.forEach(r => {
      const tr = document.createElement('tr');
      tr.style.cursor = 'pointer';
      cols.forEach(c => {
        const td = document.createElement('td');
        let v = r[c.name];

        // formata datas
        if (c.tipo==='DATE' && v) {
          const d = new Date(v);
          if (!isNaN(d)) {
            const dd   = String(d.getDate()).padStart(2,'0');
            const mm   = String(d.getMonth()+1).padStart(2,'0');
            const yyyy = d.getFullYear();
            v = `${dd}.${mm}.${yyyy}`;
          }
        }
        // BIT como ✓
        if (c.tipo==='BIT') {
          td.innerHTML = (v===1||v==='1'||v===true) ? '✔' : '';
        } else {
          td.textContent = v ?? '';
        }
        tr.append(td);
      });

      // clique abre edição
      const pk = r[`${tableName.toUpperCase()}STAMP`];
      tr.addEventListener('click', () => {
        location.href = `/generic/form/${tableName}/${pk}`;
      });
      tbody.append(tr);
    });
    table.append(tbody);
    gridDiv.append(table);
  }

});




