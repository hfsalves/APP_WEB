function carregarAnalise(usqlstamp) {
  const body = document.getElementById("analise-body");
  body.innerHTML = "A carregar...";

  fetch(`/api/analise/${usqlstamp}`)
    .then(r => r.json())
    .then(data => {
      if (data.error) {
        body.innerHTML = `<span class="error-msg">${data.error}</span>`;
        return;
      }

      const decimais = Number(data.decimais) || 2;
      const mostrarTotais = data.totais;

      const rowsOriginais = [...data.rows]; // preserva para reordenar
      const columns = data.columns;

      const numericCols = columns.filter(c =>
        data.rows.every(row => typeof row[c] === 'number' || /^[\d\s,\.]+$/.test(row[c] || ''))
      );

      const dateCols = columns.filter(c =>
        data.rows.every(row => {
          const v = row[c];
          return v != null &&
                 isNaN(parseFloat((v || '').toString().replace(',', '.'))) &&
                 !isNaN(Date.parse(v));
        })
      );

      const totals = {};
      numericCols.forEach(c => totals[c] = 0);
      data.rows.forEach(row =>
        numericCols.forEach(c => {
          const val = parseFloat((row[c] || '').toString().replace(',', '.').replace(/\s/g, ''));
          totals[c] += isNaN(val) ? 0 : val;
        })
      );

      let html = '<table><thead><tr>' +
        columns.map((c, i) =>
          `<th data-index="${i}"${numericCols.includes(c) ? ' class="num"' : ''} style="cursor:pointer">${c}</th>`
        ).join('') +
        '</tr></thead><tbody>' +
        renderRows(rowsOriginais, columns, numericCols, dateCols, decimais) +
        '</tbody>';

      if (mostrarTotais) {
        html += '<tfoot><tr>' +
          columns.map((c, i) => {
            if (i === 0) return '<td>Total</td>';
            if (numericCols.includes(c)) {
              return `<td class="num">${totals[c].toLocaleString('pt-PT', {
                minimumFractionDigits: decimais,
                maximumFractionDigits: decimais
              })}</td>`;
            }
            return '<td></td>';
          }).join('') +
        '</tr></tfoot>';
      }

      html += '</table>';
      body.innerHTML = html;

      // liga os eventos de ordenação
      const ths = body.querySelectorAll('thead th');
      let currentSort = { index: null, asc: true };

      ths.forEach(th => {
        th.addEventListener('click', () => {
          const index = parseInt(th.dataset.index);
          const col = columns[index];

          const asc = (currentSort.index === index) ? !currentSort.asc : true;
          currentSort = { index, asc };

          const sorted = [...rowsOriginais].sort((a, b) => {
            const va = a[col] ?? '';
            const vb = b[col] ?? '';
            if (numericCols.includes(col)) {
              return asc ? va - vb : vb - va;
            }
            if (dateCols.includes(col)) {
              return asc ? new Date(va) - new Date(vb) : new Date(vb) - new Date(va);
            }
            return asc ? String(va).localeCompare(String(vb)) : String(vb).localeCompare(String(va));
          });

          const tbody = body.querySelector('tbody');
          tbody.innerHTML = renderRows(sorted, columns, numericCols, dateCols, decimais);
        });
      });
    })
    .catch(err => {
      body.innerHTML = `<span class="error-msg">Erro: ${err.message}</span>`;
    });
}

function renderRows(data, columns, numericCols, dateCols, decimais) {
  return data.map(row => '<tr>' +
    columns.map(c => {
      let val = row[c] ?? '';
      if (dateCols.includes(c)) {
        const d = new Date(val);
        val = d.toLocaleDateString('pt-PT');
      } else if (numericCols.includes(c)) {
        const n = parseFloat(val.toString().replace(',', '.').replace(/\s/g, ''));
        val = isNaN(n) ? '' : n.toLocaleString('pt-PT', {
          minimumFractionDigits: decimais,
          maximumFractionDigits: decimais
        });
        return `<td class="num">${val}</td>`;
      }
      return `<td>${val}</td>`;
    }).join('') +
  '</tr>').join('');
}
