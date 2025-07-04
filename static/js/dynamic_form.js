// static/js/dynamic_form.js
// Formulário genérico com tratamento de COMBO matching robusto, BIT booleano, datas e erros no submit

(async function() {
  const TABLE_NAME   = window.TABLE_NAME;
  const RECORD_STAMP = window.RECORD_STAMP;
  const isAdminUser  = window.IS_ADMIN_USER;

  // 1. Carrega metadados
  const res   = await fetch(`/generic/api/${TABLE_NAME}?action=describe`);
  const cols  = await res.json();

// 2. Monta o formulário
const form = document.getElementById('editForm');
// usa grid do Bootstrap em vez de colunas custom
form.className = 'row gx-3 gy-2';
form.innerHTML = `
  <div id="nonAdminCol" class="col-12 col-md-6"></div>
  <div id="adminCol"    class="col-12 col-md-6"></div>
`;
const nonAdminCol = document.getElementById('nonAdminCol');
const adminCol    = document.getElementById('adminCol');

// esconde a coluna de admin, se não for
if (!window.IS_ADMIN_USER) {
  adminCol.style.display = 'none';
}

// distribui campos conforme a propriedade `admin`
 cols
   .sort((a, b) => (a.ordem||0) - (b.ordem||0))
  .forEach(col => {
    // campos admin-only saltados para user não-admin
    if (col.admin && !window.IS_ADMIN_USER) return;

    // wrapper para cada campo
    const wrapper = document.createElement('div');
    wrapper.className = col.tipo === 'BIT' ? 'form-check mb-3' : 'mb-3';

    if (col.tipo === 'BIT') {
      // checkbox
      wrapper.innerHTML = `
        <input class="form-check-input" type="checkbox"
               id="${col.name}" name="${col.name}">
        <label class="form-check-label" for="${col.name}">
          ${col.descricao || col.name}
        </label>
      `;
    } else {
      // label
      const label = document.createElement('label');
      label.setAttribute('for', col.name);
      label.className = 'form-label';
      label.textContent = col.descricao || col.name;
      wrapper.appendChild(label);

      let input;
      if (col.tipo === 'COMBO') {
        // select
        input = document.createElement('select');
        input.className = 'form-select';
        input.name = col.name;
        input.innerHTML = '<option value="">---</option>';
      } else {
        // input text/number/date/time
        input = document.createElement('input');
        input.className = 'form-control';
        input.name = col.name;
        switch (col.tipo) {
          case 'DATE':
            input.type = 'text';
            input.classList.add('flatpickr-date');
            break;
          case 'HOUR':
            input.type = 'time';
            break;
          case 'INT':
            input.type = 'number';
            break;
          case 'DECIMAL':
            input.type = 'number';
            input.step = '0.01';
            break;
          default:
            input.type = 'text';
        }
      }
      if (col.readonly) input.disabled = true;
      wrapper.appendChild(input);
    }

    // anexa ao container correto
    if (col.admin) adminCol.appendChild(wrapper);
    else           nonAdminCol.appendChild(wrapper);
  });

// 3. Popula combos
// ... resto do teu código ...


  // 4. Popula combos
  await Promise.all(
    cols
      .filter(c => c.tipo === 'COMBO' && c.combo)
      .map(async c => {
        const sel = form.querySelector(`select[name="${c.name}"]`);
        if (!sel) return;
        let opts = [];
        try {
          if (/^\s*SELECT\s+/i.test(c.combo)) {
            opts = await (await fetch(
              `/generic/api/options?query=${encodeURIComponent(c.combo)}`
            )).json();
          } else {
            opts = await (await fetch(c.combo)).json();
          }
        } catch (e) {
          console.error('Falha ao carregar combo', c.name, e);
        }
        opts.forEach(o => {
          const opt = document.createElement('option');
          if (Array.isArray(o)) {
            opt.value = o[0];
            opt.textContent = o[1];
          } else if (o.value !== undefined && o.text !== undefined) {
            opt.value       = o.value;
            opt.textContent = o.text;
          } else {
            opt.value       = o;
            opt.textContent = o;
          }
          sel.append(opt);
        });
      })
  );


  // 4. Se edição, carrega valores com matching inteligente
  if (RECORD_STAMP) {
    try {
      const rec = await (await fetch(`/generic/api/${TABLE_NAME}/${RECORD_STAMP}`)).json();
      Object.entries(rec).forEach(([key, val]) => {
        const el = form.querySelector(`[name="${key}"]`);
        if (!el) return;
        if (el.tagName === 'SELECT') {
          const desired = (val||'').toString().trim();
          // tenta match por value
          if ([...el.options].some(o => o.value === desired)) {
            el.value = desired;
          } else {
            // tenta match por texto
            const match = [...el.options].find(o => o.textContent.trim() === desired);
            el.value = match ? match.value : '';
          }
        } else if (el.type === 'checkbox') {
          el.checked = !!val;
        } else if (el.classList.contains('flatpickr-date')) {
            if (val) {
              let d, m, y;
              if (/^\d{4}-\d{2}-\d{2}/.test(val)) {
                // veio em ISO: "2025-07-02..."
                [y, m, d] = val.slice(0,10).split('-');
              } else {
                // veio em RFC: "Fri, 04 Jul 2025 00:00:00 GMT"
                const dt = new Date(val);
                d = String(dt.getDate()).padStart(2, '0');
                m = String(dt.getMonth() + 1).padStart(2, '0');
                y = dt.getFullYear();
              }
              el.value = `${d}.${m}.${y}`;
            } else {
              el.value = '';
            }
          }

       else {
          el.value = val;
        }
      });
    } catch (e) {
      console.error('Erro ao carregar registro:', e);
    }
  } else {
    document.getElementById('btnDelete')?.style.setProperty('display','none');
  }

  // 5. Inicializa Flatpickr: em edição mantém o valor, em criação força hoje
  if (window.flatpickr) {
    form.querySelectorAll('.flatpickr-date').forEach(el => {
      console.log('>>> flatpickr init on', el.id, 'value=', el.value);
      flatpickr(el, {
        dateFormat: 'd.m.Y',      // mantém tua máscara
        allowInput: true,
        defaultDate: RECORD_STAMP  // se for novo, RECORD_STAMP é falsy
                    ? el.value    // edição: valor que veio do servidor
                    : new Date(), // criação: hoje
        onReady: (selDates, dateStr, inst) => {
          if (!RECORD_STAMP) {
            // força mesmo: substitui qualquer default falhado por hoje
            inst.setDate(new Date(), true);
          }
        }
      });
    });

    // === Início dynamic_details ===
    const detailsContainer = document.getElementById('details-container');
    if (detailsContainer) {
      fetch(`/generic/api/dynamic_details/${TABLE_NAME}/${RECORD_STAMP}`)
        .then(res => res.json())
        .then(detalhes => {
          detalhes.forEach(det => {
            // 1) Card de detalhe
            const card = document.createElement('div');
            card.className = 'card p-3 mb-4';

            // 2) Título
            const title = document.createElement('h5');
            title.textContent = det.tabela;
            card.appendChild(title);

            // 3) Wrapper responsivo e tabela
            const wrapper = document.createElement('div');
            wrapper.className = 'table-responsive mb-3';
            const tbl = document.createElement('table');
            tbl.className = 'table table-striped table-sm';
            wrapper.appendChild(tbl);
            card.appendChild(wrapper);

            // 4) Cabeçalho da tabela
            const thead = tbl.createTHead();
            const hr    = thead.insertRow();
            det.campos.forEach(c => {
              const th = document.createElement('th');
              th.textContent = c.LABEL;
              hr.appendChild(th);
            });

            // 5) Corpo da tabela com formatação de datas
            const tbody = tbl.createTBody();
            det.rows.forEach(row => {
              const tr = tbody.insertRow();
              det.campos.forEach(c => {
                const td = tr.insertCell();
                let val = row[c.CAMPODESTINO] ?? '';

                // ISO date YYYY-MM-DD → DD.MM.YYYY
                if (/^\d{4}-\d{2}-\d{2}$/.test(val)) {
                  const [y, m, d] = val.split('-');
                  val = `${d}.${m}.${y}`;
                }
                // RFC date string → DD.MM.YYYY
                else if (typeof val === 'string' && val.includes('GMT')) {
                  const dt = new Date(val);
                  const d2 = String(dt.getDate()).padStart(2,'0');
                  const m2 = String(dt.getMonth()+1).padStart(2,'0');
                  const y2 = dt.getFullYear();
                  val = `${d2}.${m2}.${y2}`;
                }

                td.textContent = val;
              });
            });

            // 6) Botões de ação (Inserir / Editar / Eliminar)
            const btnGroup = document.createElement('div');
            btnGroup.className = 'btn-group';

            // Inserir
            const btnInsert = document.createElement('button');
            btnInsert.className = 'btn btn-sm btn-primary';
            btnInsert.title = 'Inserir';
            btnInsert.innerHTML = '<i class="fa fa-plus"></i>';
            btnInsert.addEventListener('click', () => {
              location = `/generic/form/${det.tabela}/`;
            });

            // Editar (usa a primeira coluna como chave)
            const btnEdit = document.createElement('button');
            btnEdit.className = 'btn btn-sm btn-secondary';
            btnEdit.title = 'Editar';
            btnEdit.innerHTML = '<i class="fa fa-edit"></i>';
            btnEdit.addEventListener('click', () => {
              const id = row[det.campos[0].CAMPODESTINO];
              location = `/generic/form/${det.tabela}/${id}`;
            });

            // Eliminar
            const btnDelete = document.createElement('button');
            btnDelete.className = 'btn btn-sm btn-danger';
            btnDelete.title = 'Eliminar';
            btnDelete.innerHTML = '<i class="fa fa-trash"></i>';
            btnDelete.addEventListener('click', async () => {
              if (!confirm('Confirmar eliminação?')) return;
              await fetch(`/generic/api/${det.tabela}/${row[det.campos[0].CAMPODESTINO]}`, { method: 'DELETE' });
              // opcional: recarregar os detalhes
              card.remove();
            });

            btnGroup.append(btnInsert, btnEdit, btnDelete);
            card.appendChild(btnGroup);

            // 7) Anexa o card ao container
            detailsContainer.appendChild(card);
          });
        })
        .catch(err => {
          console.error('Erro ao carregar detalhes:', err);
        });
    }
    // === Fim dynamic_details ===

    }


  // 6. Cancelar e eliminar
  document.getElementById('btnCancel')?.addEventListener('click', ()=> {
  window.location.href = window.RETURN_TO;
  });
  document.getElementById('btnDelete')?.addEventListener('click', async () => {
    if (!confirm('Confirmar eliminação?')) return;
    await fetch(`/generic/api/${TABLE_NAME}/${RECORD_STAMP}`, { method:'DELETE' });
    window.location.href = window.RETURN_TO;
  });
  // Voltar
  document.getElementById('btnBack')?.addEventListener('click', () => {
    window.location.href = window.RETURN_TO;
  });


    const userPerms = window.USER_PERMS[TABLE_NAME] || {};

    // Se for edição (RECORD_STAMP), valida `editar` e `eliminar`
    if (RECORD_STAMP) {
    if (!userPerms.editar) {
        // desabilita todos os controles
        form.querySelectorAll('input, select, textarea').forEach(el => el.disabled = true);
        document.getElementById('btnSave').style.display = 'none';
    }
    if (!userPerms.eliminar) {
        document.getElementById('btnDelete').style.display = 'none';
    }
    } else {
    // se for criação, valida `inserir`
    if (!userPerms.inserir) {
        document.getElementById('btnSave').style.display = 'none';
    }
    }

  // 7. Submit com tratamento de erros
  form.addEventListener('submit', async e => {
    e.preventDefault();
    const data = {};
    new FormData(form).forEach((v, k) => data[k] = v);
    // BIT para booleano
    form.querySelectorAll('input[type="checkbox"]').forEach(cb => data[cb.name] = cb.checked);
    // Datas para ISO
    form.querySelectorAll('.flatpickr-date').forEach(input => {
      const raw = input.value.trim();
      if (raw) {
        const [d,m,y] = raw.split(/\D+/);
        if (d && m && y) data[input.name] = `${y.padStart(4,'0')}-${m.padStart(2,'0')}-${d.padStart(2,'0')}`;
      }
    });
    const url = `/generic/api/${TABLE_NAME}${RECORD_STAMP ? `/${RECORD_STAMP}` : ''}`;
    const method = RECORD_STAMP ? 'PUT' : 'POST';
    try {
      const res = await fetch(url, { method, headers:{'Content-Type':'application/json'}, body: JSON.stringify(data) });
      if (!res.ok) {
        let msg;
        try { const err = await res.json(); msg = err.error || JSON.stringify(err); }
        catch { msg = await res.text(); }
        return alert(`Erro ao gravar: ${msg}`);
      }
      window.location.href = window.RETURN_TO;
    } catch (net) {
      alert(`Erro de rede: ${net.message}`);
    }
  });

  document.querySelectorAll('.btn-custom').forEach(btn => {
  btn.addEventListener('click', async () => {
    const tipo = btn.dataset.tipo;
    const acao = btn.dataset.acao;
    const destino = btn.dataset.destino;

    if (tipo === 'MODAL') {
      abrirModal(acao);
    }
  });
});


  // 8. Cursor no final
  form.querySelectorAll('input[type="text"],input[type="number"],input[type="time"]').forEach(i =>
    i.addEventListener('focus', () => { const v = i.value; i.value = ''; i.value = v; })  
  );
})();

// static/js/dynamic_form.js
// Formulário genérico com tratamento de COMBO, valores por defeito e submissão.

let currentModalName = null;

// Debug: mostra o RECORD_STAMP global
console.log('🚀 dynamic_form.js carregado - RECORD_STAMP global:', window.RECORD_STAMP);

// Abre o modal e carrega campos dinâmicos
function abrirModal(nomeModal) {
  currentModalName = nomeModal;
  fetch(`/generic/api/modal/${nomeModal}`)
    .then(res => res.json())
    .then(data => {
      if (!data.success) {
        alert('Erro ao carregar modal: ' + data.message);
        return;
      }
      console.log('⚙️ Dados do modal:', data);
      // Ajusta título do modal
      const titleEl = document.getElementById('genericModalLabel');
      if (titleEl) titleEl.innerText = data.titulo || 'Ação';
      // Desenha campos
      renderModalFields(data.campos || []);
      // Inicia Flatpickr nos campos de data
      if (window.flatpickr) {
        document.querySelectorAll('#modalBody .flatpickr-date').forEach(el =>
          flatpickr(el, { dateFormat: 'd-m-Y', allowInput: true })
        );
      }
      // Exibe o modal
      const modalEl = document.getElementById('genericModal');
      new bootstrap.Modal(modalEl).show();
    })
    .catch(err => {
      console.error('Erro ao carregar modal:', err);
      alert('Erro ao carregar o formulário do modal');
});
}

// Gera os elementos de campo dentro do modal
function renderModalFields(campos) {
  const container = document.getElementById('modalBody');
  if (!container) {
    console.error('❌ Container #modalBody não encontrado!');
    return;
  }
  container.innerHTML = '';

  campos
    .sort((a, b) => a.ORDEM - b.ORDEM)
    .forEach(col => {
      // Cria wrapper e label
      const wrapper = document.createElement('div');
      wrapper.className = 'form-group';
      if (col.TIPO === 'BIT') wrapper.classList.add('checkbox');

      const label = document.createElement('label');
      label.setAttribute('for', col.CAMPO);
      label.textContent = col.LABEL || col.CAMPO;
      wrapper.appendChild(label);

      let input;
      // ── 1) COMBO ─────────────────────────────────────────────
      if (col.TIPO === 'COMBO') {
        input = document.createElement('select');
        input.name = col.CAMPO;
        input.id   = col.CAMPO;
        input.className = 'form-control';
        // opção vazia
        input.innerHTML = '<option value="">---</option>';
        // popula com OPCOES vindas do servidor
        if (Array.isArray(col.OPCOES)) {
          col.OPCOES.forEach(opt => {
            const o = document.createElement('option');
            o.value = opt[0];
            o.textContent = opt[1];
            input.appendChild(o);
          });
        }
        // aplica default só depois das opções existirem
        if (col.VALORDEFAULT) {
          let def = col.VALORDEFAULT.trim();
          // strip de aspas, se houver
          if (/^".*"$/.test(def)) def = def.slice(1, -1);
          input.value = def;
        }

      // ── 2) INPUTS (TEXT, DATE, HOUR, INT, DECIMAL, BIT) ───────
      } else {
        input = document.createElement('input');
        input.name = col.CAMPO;
        input.id   = col.CAMPO;
        input.className = 'form-control';

        switch (col.TIPO) {
          case 'DATE':
            input.type = 'text';
            input.classList.add('flatpickr-date');
            break;
          case 'HOUR':
            input.type = 'time';
            break;
          case 'INT':
            input.type = 'number';
            input.step = '1';
            break;
          case 'DECIMAL':
            input.type = 'number';
            input.step = '0.01';
            break;
          case 'BIT':
            input.type = 'checkbox';
            break;
          default:
            input.type = 'text';
        }

        if (col.VALORDEFAULT) {
          let def = col.VALORDEFAULT.trim();
          // macro RECORD_STAMP
          if (/^\{\s*RECORD_STAMP\s*\}$/.test(def)) {
            def = window.RECORD_STAMP || '';
          }
          // strip de aspas
          else if (/^".*"$/.test(def)) {
            def = def.slice(1, -1);
          }
          if (input.type === 'checkbox') {
            input.checked = ['1','true','True'].includes(def);
          } else {
            input.value = def;
          }
        }
      }

      wrapper.appendChild(input);
      container.appendChild(wrapper);
    });
}

// ── Inicializa Flatpickr nos campos de DATE ───────────────────
if (window.flatpickr) {
  form.querySelectorAll('.flatpickr-date').forEach(el => {
    flatpickr(el, {
      dateFormat: 'd.m.Y',
      allowInput: true,
      // converte a string “DD.MM.YYYY” numa Date válida
      parseDate: (datestr) => {
        const [d, m, y] = datestr.split('.');
        return new Date(`${y}-${m}-${d}`);
      },
      // se houver valor (modo edição), usa-o convertido; senão hoje
      defaultDate: el.value
        ? (()=>{
            const [d, m, y] = el.value.split('.');
            return new Date(`${y}-${m}-${d}`);
          })()
        : new Date()
    });
  });
}

// Submete o modal ao servidor
function gravarModal() {
  const container = document.getElementById('modalBody');
  if (!container) return console.error('❌ Container #modalBody não encontrado');

  const inputs = container.querySelectorAll('input[name], select[name]');
  const dados = { __modal__: currentModalName };

  inputs.forEach(i => {
    if (i.type === 'checkbox') {
      dados[i.name] = i.checked ? 1 : 0;
    } else {
      let val = i.value.trim();

      // Se for campo de data (flatpickr-date), converte dd.mm.YYYY → YYYY-MM-DD
      if (i.classList.contains('flatpickr-date') && val) {
        const [d, m, y] = val.split(/\D+/);
        if (d && m && y) {
          val = `${y.padStart(4,'0')}-${m.padStart(2,'0')}-${d.padStart(2,'0')}`;
        }
      }

      dados[i.name] = val;
    }
  });

  console.log('📤 Enviando dados modal:', dados);
  fetch('/generic/api/modal/gravar', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(dados)
  })
  .then(res => res.json())
  .then(data => {
    if (data.success) {
      const modalEl = document.getElementById('genericModal');
      bootstrap.Modal.getInstance(modalEl).hide();
      document.querySelectorAll('.modal-backdrop').forEach(b => b.remove());
    } else {
      alert('Erro ao gravar modal: ' + data.error);
    }
  })
  .catch(e => {
    console.error('Erro ao gravar modal:', e);
    alert('Erro ao gravar modal. Veja console.');
  });
}


// Expõe no global se quiser usar onclick inline
window.abrirModal = abrirModal;
window.gravarModal = gravarModal;
