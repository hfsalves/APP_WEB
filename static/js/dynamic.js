// dynamic.js (enhanced with typed column support)
// Script para gerar dinamicamente a grelha e o formulário de CRUD genérico

document.addEventListener('DOMContentLoaded', async () => {
  console.log('dynamic.js loaded for table:', TABLE_NAME, 'record:', RECORD_STAMP);

  const gridDiv = document.getElementById('grid');
  const filtersDiv = document.getElementById('filters');

  try {
    // 1) Fetch column metadata (describe)
    console.log('Fetching metadata');
    const metaRes = await fetch(`/generic/api/${TABLE_NAME}?action=describe`);
    if (!metaRes.ok) throw new Error(`Describe request failed: ${metaRes.status}`);
    const metaJson = await metaRes.json();
    console.log('Metadata received:', metaJson);
    const columns = metaJson.columns;

    if (!columns || columns.length === 0) {
      console.error('No columns metadata. Check CAMPOS table for', TABLE_NAME);
      gridDiv.innerHTML = '<p>Nenhuma configuração de colunas encontrada.</p>';
      return;
    }

    // 2) Build filters UI with type-specific inputs
    filtersDiv.innerHTML = '';
    columns.filter(c => c.filtro).forEach(col => {
      const wrapper = document.createElement('div');
      wrapper.classList.add('filter-group');
      const label = document.createElement('label');
      label.textContent = col.descricao || col.name;
      let input;
      switch(col.tipo) {
        case 'DATE':
          input = document.createElement('input'); input.type = 'date'; break;
        case 'DECIMAL':
          input = document.createElement('input'); input.type = 'number'; input.step = '0.01'; break;
        case 'INT':
          input = document.createElement('input'); input.type = 'number'; input.step = '1'; break;
        case 'HOUR':
          input = document.createElement('input'); input.type = 'time'; break;
        case 'BIT':
          input = document.createElement('input'); input.type = 'checkbox'; break;
        default:
          input = document.createElement('input'); input.type = 'text';
      }
      input.name = col.name;
      input.addEventListener('change', loadGrid);
      wrapper.append(label, input);
      filtersDiv.appendChild(wrapper);
    });

    // Formatters per type
    function formatValue(type, value) {
      if (value == null) return '';
      switch(type) {
        case 'DECIMAL':
          return Number(value).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
        case 'INT':
          return Number(value).toString();
        case 'DATE':
          const d = new Date(value);
          return `${String(d.getDate()).padStart(2,'0')}.${String(d.getMonth()+1).padStart(2,'0')}.${d.getFullYear()}`;
        case 'HOUR':
          const [h,m] = value.split(':');
          return `${h.padStart(2,'0')}:${m.padStart(2,'0')}`;
        case 'BIT':
          return value ? '✔️' : '';
        default:
          return value;
      }
    }

    // 3) Function to load grid data
    async function loadGrid() {
      try {
        console.log('Loading grid data');
        let url = `/generic/api/${TABLE_NAME}`;
        const params = new URLSearchParams();
        filtersDiv.querySelectorAll('input').forEach(input => {
          if ((input.type === 'checkbox' && input.checked) || (input.value && input.type !== 'checkbox')) {
            params.append(input.name, input.value);
          }
        });
        if ([...params].length) url += `?${params.toString()}`;
        console.log('Fetching data from:', url);

        const res = await fetch(url);
        if (!res.ok) {
          const errText = await res.text();
          console.error('Error response body:', errText);
          throw new Error(`Data request failed: ${res.status}: ${errText}`);
        }
        const data = await res.json();
        console.log('Data received:', data);

        // Build table
        gridDiv.innerHTML = '';
        const table = document.createElement('table');
        table.classList.add('dynamic-table');

        // Header
        const thead = document.createElement('thead');
        const trHead = document.createElement('tr');
        columns.filter(c => c.lista).forEach(col => {
          const th = document.createElement('th');
          th.textContent = col.descricao || col.name;
          if (col.tipo === 'BIT') th.style.textAlign = 'center';
          trHead.appendChild(th);
        });
        thead.appendChild(trHead);
        table.appendChild(thead);

        // Body
        const tbody = document.createElement('tbody');
        data.forEach(row => {
          const tr = document.createElement('tr');
          tr.dataset.stamp = row[`${TABLE_NAME.toUpperCase()}STAMP`];
          tr.addEventListener('click', () => openEditModal(row));
          columns.filter(c => c.lista).forEach(col => {
            const td = document.createElement('td');
            td.textContent = formatValue(col.tipo, row[col.name]);
            if (col.tipo === 'BIT') td.style.textAlign = 'center';
            tr.appendChild(td);
          });
          tbody.appendChild(tr);
        });
        table.appendChild(tbody);
        gridDiv.appendChild(table);
      } catch (err) {
        console.error('Error in loadGrid:', err);
        gridDiv.innerHTML = `<p>Erro ao carregar dados: ${err.message}</p>`;
      }
    }

    function openEditModal(row) {
      modalTitle.textContent = row ? 'Editar' : 'Novo';
      editForm.innerHTML = '';
      columns.forEach(col => {
        if (!col.primary_key) {
          const grp = document.createElement('div');
          grp.classList.add('form-group');
          const lbl = document.createElement('label');
          lbl.textContent = col.descricao || col.name;
          const inp = document.createElement('input');
          inp.name = col.name;
          inp.value = row ? row[col.name] || '' : '';
          grp.append(lbl, inp);
          editForm.appendChild(grp);
        } else if (row) {
          const inp = document.createElement('input');
          inp.type = 'hidden';
          inp.name = col.name;
          inp.value = row[col.name];
          editForm.appendChild(inp);
        }
      });
      const actions = document.createElement('div');
      actions.classList.add('form-actions');
      actions.innerHTML = editForm.querySelector('.form-actions')?.innerHTML;
      editForm.appendChild(actions);
      modal.style.display = 'block';
    }

    function closeModal() {
      modal.style.display = 'none';
    }

    editForm.onsubmit = async (e) => {
      e.preventDefault();
      const formData = new FormData(editForm);
      const payload = {};
      formData.forEach((v, k) => payload[k] = v);
      const method = payload[`${TABLE_NAME.toUpperCase()}STAMP`] ? 'PUT' : 'POST';
      await fetch(`/generic/api/${TABLE_NAME}`, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      closeModal();
      loadGrid();
    };

    // 5) Initial load
    loadGrid();
    if (RECORD_STAMP) {
      fetch(`/generic/api/${TABLE_NAME}/${RECORD_STAMP}`)
        .then(res => res.json())
        .then(rec => openEditModal(rec))
        .catch(err => console.error('Erro fetch record:', err));
    }

  } catch (err) {
    console.error('Error in initialization:', err);
    gridDiv.innerHTML = `<p>Erro na inicialização: ${err.message}</p>`;
  }
});
