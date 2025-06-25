// static/js/dynamic_list.js
// Script to render the list view with COMBO filters and type-specific formatting

document.addEventListener('DOMContentLoaded', () => {
  const tableName = window.TABLE_NAME;
  const gridDiv = document.getElementById('grid');
  const filtersContainer = document.getElementById('filters');
  const userPerms = window.USER_PERMS[tableName] || {};

  // 1) Permissão de consulta
  if (!userPerms.consultar) {
    alert('Sem permissão para consultar esta lista.');
    return;
  }
  if (!filtersContainer || !gridDiv) {
    console.error('Elementos #filters ou #grid não encontrados no DOM');
    return;
  }

  initListView().catch(err => console.error('Erro ao inicializar lista:', err));

  async function initListView() {
    // 1) DESCRIBE para metadados
    let meta;
    try {
      const res = await fetch(`/generic/api/${tableName}?action=describe`);
      if (!res.ok) throw new Error(`Describe falhou: ${res.status}`);
      const body = await res.json();
      meta = Array.isArray(body) ? body : Array.isArray(body.columns) ? body.columns : [];
    } catch (err) {
      console.error('Erro ao carregar metadados:', err);
      filtersContainer.innerHTML = '<p>Erro ao carregar filtros.</p>';
      return;
    }

    // 2) Separar colunas de filtro e de listagem
    const filterCols = meta.filter(c => c.filtro);
    const listCols = meta.filter(c => c.lista);

    // 3) Renderizar filtros
    const filterForm = renderFilters(filterCols);

    // 4) Popula COMBO filters
    await Promise.all(
      filterCols.filter(c => c.tipo === 'COMBO' && c.combo).map(async c => {
        const sel = filterForm.querySelector(`select[name="${c.name}"]`);
        if (!sel) return;
        let opts = [];
        try {
          if (/^\s*SELECT\s+/i.test(c.combo)) {
            opts = await (await fetch(`/generic/api/options?query=${encodeURIComponent(c.combo)}`)).json();
          } else {
            opts = await (await fetch(c.combo)).json();
          }
        } catch (e) {
          console.error('Falha ao carregar opções COMBO:', c.name, e);
        }
        opts.forEach(o => {
          const option = document.createElement('option');
          const value = (typeof o === 'object') ? Object.values(o)[0] : o;
          option.value = value != null ? value.toString() : '';
          option.textContent = value;
          sel.append(option);
        });
      })
    );

    // 5) Bind de submit e inicial load
    filterForm.addEventListener('submit', e => {
      e.preventDefault();
      loadData();
    });
    await loadData();

    // Carrega dados
    async function loadData() {
      const params = new URLSearchParams();
      filterForm.querySelectorAll('[name]').forEach(input => {
        if ((input.type === 'checkbox' && input.checked) ||
            (input.type !== 'checkbox' && input.value)) {
          params.append(input.name, input.value);
        }
      });
      const url = `/generic/api/${tableName}${params.toString() ? '?' + params.toString() : ''}`;
      const res = await fetch(url);
      if (!res.ok) {
        gridDiv.innerHTML = `<p>Erro ao carregar dados: ${res.status}</p>`;
        return;
      }
      const data = await res.json();
      renderTable(listCols, data);
    }

    // Função de renderização de filtros
    function renderFilters(cols) {
      filtersContainer.innerHTML = '';
      const form = document.createElement('form');
      form.id = 'filter-form';
      form.classList.add('filter-form');
      form.style.display = 'flex';
      form.style.flexWrap = 'wrap';
      form.style.gap = '0.5rem';

      cols.forEach(col => {
        const wrapper = document.createElement('div');
        wrapper.classList.add('filter-item');
        const label = document.createElement('label');
        label.setAttribute('for', col.name);
        label.textContent = col.descricao || col.name;

        let input;
        if (col.tipo === 'COMBO') {
          input = document.createElement('select');
          const placeholder = document.createElement('option');
          placeholder.value = '';
          placeholder.textContent = '---';
          input.append(placeholder);
        } else {
          input = document.createElement('input');
          switch (col.tipo) {
            case 'DATE':    input.type = 'date'; break;
            case 'DECIMAL': input.type = 'number'; input.step = '0.01'; break;
            case 'INT':     input.type = 'number'; input.step = '1'; break;
            case 'HOUR':    input.type = 'time'; break;
            case 'BIT':     input.type = 'checkbox'; break;
            default:        input.type = 'text';
          }
        }
        input.name = col.name;
        input.id = col.name;
        wrapper.append(label, input);
        form.append(wrapper);
      });

      // Botão Filtrar
      const btnFilter = document.createElement('button');
      btnFilter.type = 'submit';
      btnFilter.textContent = 'Filtrar';
      btnFilter.classList.add('btn', 'btn-secondary');
      form.append(btnFilter);

      // Botão Novo se permissão inserir
      if (userPerms.inserir) {
        const btnNew = document.createElement('button');
        btnNew.type = 'button';
        btnNew.textContent = 'Novo';
        btnNew.classList.add('btn', 'btn-primary');
        btnNew.addEventListener('click', () => {
          window.location.href = `/generic/form/${tableName}/`;
        });
        form.append(btnNew);
      }

      filtersContainer.append(form);
      return form;
    }

    // Função para render tabela
    function renderTable(cols, rows) {
      gridDiv.innerHTML = '';
      const table = document.createElement('table');
      table.classList.add('list-table');
      const thead = document.createElement('thead');
      const headRow = document.createElement('tr');
      cols.forEach(c => {
        const th = document.createElement('th');
        th.textContent = c.descricao || c.name;
        headRow.append(th);
      });
      thead.append(headRow);
      table.append(thead);

      const tbody = document.createElement('tbody');
      const stampField = `${tableName.toUpperCase()}STAMP`;
      rows.forEach(r => {
        const tr = document.createElement('tr');
        cols.forEach(c => {
          const td = document.createElement('td');
          td.textContent = formatValue(c.tipo, r[c.name]);
          tr.append(td);
        });
        tr.addEventListener('click', () => {
          window.location = `/generic/form/${tableName}/${r[stampField]}`;
        });
        tbody.append(tr);
      });
      table.append(tbody);
      gridDiv.append(table);
    }

    // Formatação de valores
    function formatValue(type, val) {
      if (val == null) return '';
      switch (type) {
        case 'DECIMAL': return Number(val).toLocaleString(undefined, {minimumFractionDigits:2, maximumFractionDigits:2});
        case 'INT':     return Number(val).toString();
        case 'DATE':    {
          const d = new Date(val);
          return `${String(d.getDate()).padStart(2,'0')}.${String(d.getMonth()+1).padStart(2,'0')}.${d.getFullYear()}`;
        }
        case 'HOUR':    return val.slice(0,5);
        case 'BIT':     return val ? '✓' : '';
        default:        return val;
      }
    }
  }
});
