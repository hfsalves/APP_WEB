// static/js/dashboard.js

// Função utilitária para parsear números formatados (remove espaços e vírgulas)
function parseNumber(val) {
  if (val == null || val === '') return 0;
  const s = typeof val === 'string'
    ? val.replace(/\s/g, '').replace(',', '.')
    : val;
  const n = Number(s);
  return isNaN(n) ? 0 : n;
}

document.addEventListener('DOMContentLoaded', () => {
  showLoading();
  fetch('/api/dashboard')
    .then(r => r.json())
    .then(data => {
      const widgetPromises = [];
      [1,2,3].forEach(col => {
        const colDiv = document.getElementById('col-' + col);
        colDiv.innerHTML = '';
        data[col].forEach(widget => {
          // Modifica renderWidget para devolver uma Promise se tiver fetch!
          const prom = renderWidget(widget, colDiv);
          if (prom && typeof prom.then === 'function') widgetPromises.push(prom);
        });
      });
      // Espera por todos os widgets que devolvem Promise (os que têm fetch)
      return Promise.all(widgetPromises);
    })
    .finally(hideLoading);
});


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

function renderWidget(widget, colDiv) {
  const wDiv = document.createElement('div');
  wDiv.className = 'widget widget-' + widget.tipo.toLowerCase();
  wDiv.innerHTML = `
    <div class="widget-header">
      <h3>${widget.titulo || formatTitle(widget.nome)}</h3>
      <button class="expand-btn" title="Expandir">⤢</button>
    </div>
    <div class="widget-body"></div>
  `;
  colDiv.appendChild(wDiv);

  const body = wDiv.querySelector('.widget-body');
  const expandBtn = wDiv.querySelector('.expand-btn');
  expandBtn.style.display = 'none';

  // Aplica maxheight se definido
  let maxH = widget.maxheight;
  try {
    const cfg = JSON.parse(widget.config || '{}');
    if (!maxH && cfg.maxheight) maxH = cfg.maxheight;
  } catch {}
  if (maxH) {
    body.style.maxHeight = maxH + 'px';
    body.style.overflowY = 'auto';
  }

  // Função para mostrar/ocultar botão expandir
  const toggleExpandBtn = () => {
    if (maxH && body.scrollHeight > body.clientHeight) expandBtn.style.display = '';
    else expandBtn.style.display = 'none';
  };
  expandBtn.addEventListener('click', () => wDiv.classList.toggle('expanded'));

if (widget.tipo === 'ANALISE') {
  return fetch(`/api/widget/analise/${widget.nome}`)
    .then(r => r.json())
    .then(data => {
      if (data.error) {
        body.innerHTML = `<span class="error-msg">${data.error}</span>`;
        toggleExpandBtn();
        return;
      }

      // 1) Colunas numéricas (só dígitos, espaço, vírgula ou ponto)
      const numericCols = data.columns.filter(c =>
        data.rows.every(row => {
          const v = row[c];
          if (typeof v === 'number') return true;
          if (typeof v === 'string') return /^[\d\s,\.]+$/.test(v);
          return false;
        })
      );

      // 2) Colunas DECIMAL (com casas decimais)
      const decimalCols = numericCols.filter(c =>
        data.rows.some(row => parseNumber(row[c]) % 1 !== 0)
      );

      // 3) Colunas de data: tudo o que Date.parse entende mas não é numérico
      const dateCols = data.columns.filter(c =>
        data.rows.every(row => {
          const v = row[c];
          return v != null
            && isNaN(parseNumber(v))     // não é número
            && !isNaN(Date.parse(v));    // é reconhecido como data
        })
      );

      // Totais
      const totals = {};
      numericCols.forEach(c => totals[c] = 0);
      data.rows.forEach(row =>
        numericCols.forEach(c => { totals[c] += parseNumber(row[c]); })
      );

      // Monta HTML da tabela
      let html = '<table>';

      // Cabeçalho
      html += '<thead><tr>' +
        data.columns.map(c =>
          `<th${numericCols.includes(c) ? ' class="num"' : ''}>${c}</th>`
        ).join('') +
      '</tr></thead>';

      // Corpo
      html += '<tbody>' +
        data.rows.map(row => '<tr>' +
          data.columns.map(c => {
            //  → Se for data, formata dd.mm.yyyy
            if (dateCols.includes(c)) {
              const d = new Date(row[c]);
              const dd = String(d.getDate()).padStart(2,'0');
              const mm = String(d.getMonth()+1).padStart(2,'0');
              const yyyy = d.getFullYear();
              return `<td>${dd}.${mm}.${yyyy}</td>`;
            }
            //  → Se for número, formata com separador de milhar e decimais
            if (numericCols.includes(c)) {
              return `<td class="num">${formatNumber(parseNumber(row[c]))}</td>`;
            }
            //  → Senão, mostra o texto cru
            return `<td>${row[c]}</td>`;
          }).join('') +
        '</tr>').join('') +
      '</tbody>';

      // Rodapé (apenas se houver DECIMAL)
      if (decimalCols.length > 0) {
        html += '<tfoot><tr>' +
          data.columns.map((c,i) => {
            if (i === 0) return '<td>Total</td>';
            if (numericCols.includes(c)) {
              return `<td class="num">${formatNumber(totals[c])}</td>`;
            }
            return '<td></td>';
          }).join('') +
        '</tr></tfoot>';
      }

      html += '</table>';
      body.innerHTML = html;
      toggleExpandBtn();
    })
    .catch(err => {
      body.innerHTML = `<span class="error-msg">Erro: ${err.message}</span>`;
      toggleExpandBtn();
    });
}

if (widget.tipo === 'HTML') {
  body.innerHTML = widget.config || '<em>(sem conteúdo)</em>';
}


  if (widget.tipo === 'GRAFICO') {
    fetch(`/api/widget/analise/${widget.nome}`)
      .then(r => r.json())
      .then(data => {
        if (data.error) {
          body.innerHTML = `<span class="error-msg">${data.error}</span>`;
          toggleExpandBtn();
          return;
        }
        let cfg = {};
        try { cfg = JSON.parse(widget.config); } catch {}
        const chartType = cfg.tipo_grafico || 'bar';
        const labelCol = cfg.label_col || data.columns[0];
        const dataCol = cfg.data_col || data.columns[1];
        const labels = data.rows.map(r => r[labelCol]);
        const values = data.rows.map(r => parseNumber(r[dataCol]));

        const dataset = { label: widget.titulo || widget.nome, data: values };
        if (chartType === 'bar' || chartType === 'line') {
          Object.assign(dataset, {
            backgroundColor: 'rgba(0, 123, 255, 0.5)',
            borderColor: 'rgba(0, 123, 255, 1)',
            borderWidth: 1,
            borderRadius: 5,
            borderSkipped: false
          });
        } else {
          dataset.backgroundColor = labels.map((_,i) => `hsl(${Math.round(i*360/labels.length)},70%,60%)`);
          dataset.borderWidth = 1;
        }
        body.innerHTML = '';
        const canvas = document.createElement('canvas');
        body.appendChild(canvas);
        new Chart(canvas.getContext('2d'), {
          type: chartType,
          data: { labels, datasets: [dataset] },
          options: {
            responsive: true,
            plugins: { legend: { display: chartType !== 'bar' && chartType !== 'line' } },
            scales: (chartType === 'bar' || chartType === 'line') ? {
              x: { grid: { display: false } },
              y: { beginAtZero: true, grid: { display: true, color: '#e0e0e0' } }
            } : {}
          }
        });
        toggleExpandBtn();
      })
      .catch(err => {
        body.innerHTML = `<span class="error-msg">${err.message}</span>`;
        toggleExpandBtn();
      });
  }
}

// Formata número com separador de milhar e duas casas
function formatNumber(n) {
  const num = Number(n);
  if (isNaN(num)) return '';
  const parts = num.toFixed(2).split('.');
  parts[0] = parts[0].replace(/\B(?=(\d{3})+(?!\d))/g,' ');
  return parts.join(',');
}

function formatTitle(str) {
  return str.replace(/_/g,' ').replace(/\b\w/g,l=>l.toUpperCase());
}
