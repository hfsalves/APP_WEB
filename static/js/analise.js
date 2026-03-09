function carregarAnalise(usqlstamp) {
  const body = document.getElementById('analise-body');
  if (!body) return;

  body.innerHTML = '<div class="sz_text_muted">A carregar...</div>';

  fetch(`/api/analise/${usqlstamp}`)
    .then((r) => r.json())
    .then((data) => {
      if (data.error) {
        body.innerHTML = `<div class="sz_error">${escapeHtml(data.error)}</div>`;
        return;
      }

      const decimais = Number(data.decimais) || 2;
      const mostrarTotais = !!data.totais;
      const rowsOriginais = Array.isArray(data.rows) ? [...data.rows] : [];
      const columns = Array.isArray(data.columns) ? data.columns : [];

      const numericCols = columns.filter((c) =>
        rowsOriginais.every((row) => typeof row[c] === 'number' || /^[\d\s,.\-]+$/.test((row[c] || '').toString()))
      );

      const dateCols = columns.filter((c) =>
        rowsOriginais.every((row) => {
          const v = row[c];
          return v != null &&
            isNaN(parseFloat((v || '').toString().replace(',', '.'))) &&
            !isNaN(Date.parse(v));
        })
      );

      const totals = {};
      numericCols.forEach((c) => { totals[c] = 0; });
      rowsOriginais.forEach((row) => {
        numericCols.forEach((c) => {
          const val = parseFloat((row[c] || '').toString().replace(',', '.').replace(/\s/g, ''));
          totals[c] += isNaN(val) ? 0 : val;
        });
      });

      let html = `
        <div class="sz_analysis_table_wrap sz_table_host">
          <table class="sz_table">
            <thead class="sz_table_head">
              <tr>
                ${columns.map((c, i) => `
                  <th data-index="${i}"${numericCols.includes(c) ? ' class="sz_text_right"' : ''} style="cursor:pointer">${escapeHtml(c)}</th>
                `).join('')}
              </tr>
            </thead>
            <tbody>
              ${renderRows(rowsOriginais, columns, numericCols, dateCols, decimais)}
            </tbody>`;

      if (mostrarTotais) {
        html += `
            <tfoot>
              <tr class="sz_table_row">
                ${columns.map((c, i) => {
                  if (i === 0) return '<td class="sz_table_cell"><strong>Total</strong></td>';
                  if (numericCols.includes(c)) {
                    return `<td class="sz_table_cell sz_text_right"><strong>${totals[c].toLocaleString('pt-PT', {
                      minimumFractionDigits: decimais,
                      maximumFractionDigits: decimais
                    })}</strong></td>`;
                  }
                  return '<td class="sz_table_cell"></td>';
                }).join('')}
              </tr>
            </tfoot>`;
      }

      html += `
          </table>
        </div>`;

      body.innerHTML = html;

      const ths = body.querySelectorAll('thead th');
      let currentSort = { index: null, asc: true };

      ths.forEach((th) => {
        th.addEventListener('click', () => {
          const index = parseInt(th.dataset.index, 10);
          const col = columns[index];
          const asc = currentSort.index === index ? !currentSort.asc : true;
          currentSort = { index, asc };

          const sorted = [...rowsOriginais].sort((a, b) => {
            const va = a[col] ?? '';
            const vb = b[col] ?? '';
            if (numericCols.includes(col)) {
              const na = parseFloat((va || '').toString().replace(',', '.').replace(/\s/g, ''));
              const nb = parseFloat((vb || '').toString().replace(',', '.').replace(/\s/g, ''));
              return asc ? ((isNaN(na) ? 0 : na) - (isNaN(nb) ? 0 : nb)) : ((isNaN(nb) ? 0 : nb) - (isNaN(na) ? 0 : na));
            }
            if (dateCols.includes(col)) {
              return asc ? (new Date(va) - new Date(vb)) : (new Date(vb) - new Date(va));
            }
            return asc
              ? String(va).localeCompare(String(vb), 'pt-PT', { sensitivity: 'base' })
              : String(vb).localeCompare(String(va), 'pt-PT', { sensitivity: 'base' });
          });

          const tbody = body.querySelector('tbody');
          if (tbody) {
            tbody.innerHTML = renderRows(sorted, columns, numericCols, dateCols, decimais);
          }
        });
      });
    })
    .catch((err) => {
      body.innerHTML = `<div class="sz_error">Erro: ${escapeHtml(err.message)}</div>`;
    });
}

function renderRows(data, columns, numericCols, dateCols, decimais) {
  return data.map((row) => `
    <tr class="sz_table_row">
      ${columns.map((c) => {
        let val = row[c] ?? '';
        if (dateCols.includes(c)) {
          const d = new Date(val);
          val = isNaN(d.getTime()) ? '' : d.toLocaleDateString('pt-PT');
        } else if (numericCols.includes(c)) {
          const n = parseFloat(val.toString().replace(',', '.').replace(/\s/g, ''));
          val = isNaN(n) ? '' : n.toLocaleString('pt-PT', {
            minimumFractionDigits: decimais,
            maximumFractionDigits: decimais
          });
          return `<td class="sz_table_cell sz_text_right">${escapeHtml(val)}</td>`;
        }
        return `<td class="sz_table_cell">${escapeHtml(val)}</td>`;
      }).join('')}
    </tr>`).join('');
}

function escapeHtml(s) {
  const m = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' };
  return String(s).replace(/[&<>"']/g, (c) => m[c] || c);
}
