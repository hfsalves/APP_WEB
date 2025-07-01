// static/js/dynamic_form.js
// Formulário genérico com tratamento de COMBO matching robusto, BIT booleano, datas e erros no submit

(async function() {
  const TABLE_NAME   = window.TABLE_NAME;
  const RECORD_STAMP = window.RECORD_STAMP;
  const isAdminUser  = window.IS_ADMIN_USER;

  // 1. Carrega metadados
  let columns;
  try {
    const res = await fetch(`/generic/api/${TABLE_NAME}?action=describe`);
    if (!res.ok) throw new Error(res.statusText);
    const body = await res.json();
    columns = Array.isArray(body) ? body : body.columns;
  } catch (err) {
    console.error('Erro a carregar describe:', err);
    document.getElementById('editForm').innerHTML = '<p>Erro ao carregar formulário.</p>';
    return;
  }

  // 2. Monta o formulário
  const form = document.getElementById('editForm');
  form.classList.add('two-cols');
  form.innerHTML = '<div class="coluna-1"></div><div class="coluna-2"></div>';
  const [col1, col2] = form.querySelectorAll('.coluna-1, .coluna-2');

  columns.sort((a,b)=>a.ordem-b.ordem).forEach(col => {
    if (col.admin && !isAdminUser) return;
    const wrapper = document.createElement('div');
    wrapper.classList.add('form-group');
    if (col.tipo === 'BIT') wrapper.classList.add('checkbox');

    const label = document.createElement('label');
    label.textContent = col.descricao || col.name;
    wrapper.append(label);

    let input;
    if (col.tipo === 'COMBO') {
      input = document.createElement('select');
      input.name = col.name;
      input.innerHTML = '<option value="">---</option>';
    } else {
      input = document.createElement('input');
      input.name = col.name;
      switch(col.tipo) {
        case 'DATE':   input.type = 'text'; input.classList.add('flatpickr-date'); break;
        case 'HOUR':   input.type = 'time'; break;
        case 'INT':    input.type = 'number'; break;
        case 'DECIMAL':input.type = 'number'; input.step = '0.01'; break;
        case 'BIT':    input.type = 'checkbox'; break;
        default:       input.type = 'text';
      }
    }
    if (col.readonly) input.disabled = true;
    wrapper.append(input);
    (col.admin ? col2 : col1).append(wrapper);
  });

  // 3. Popula combos
  await Promise.all(columns.filter(c=>c.tipo==='COMBO'&&c.combo).map(async c => {
    const sel = form.querySelector(`select[name="${c.name}"]`);
    if (!sel) return;
    let opts = [];
    try {
      if (/^\s*SELECT\s+/i.test(c.combo)) {
        opts = await (await fetch(`/generic/api/options?query=${encodeURIComponent(c.combo)}`)).json();
      } else {
        opts = await (await fetch(c.combo)).json();
      }
    } catch (e) {
      console.error('Falha ao carregar combo', c.name, e);
    }
    opts.forEach(o => {
      const option = document.createElement('option');
      const value = typeof o === 'object' ? Object.values(o)[0] : o;
      option.value = value?.toString() || '';
      option.textContent = value;
      sel.append(option);
    });
  }));

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
        .then(r => r.json())
        .then(detalhes => {
          detalhes.forEach(det => {
            // 1) Card/container
            const card = document.createElement('div');
            card.className = 'card p-3 mb-4';

            // 2) Título da tabela-filho
            const title = document.createElement('h5');
            title.textContent = det.tabela;
            card.appendChild(title);

            // 1) Criar o wrapper bootstrap
            const wrapper = document.createElement('div');
            wrapper.className = 'table-responsive mb-3'; 
              // mb-3 dá um espacinho em baixo

            // 2) A própria tabela
            const tbl = document.createElement('table');
            tbl.className = 'table table-striped table-sm'; 
              // table-sm deixa-a mais compacta

            // 3) Anexar a tabela ao wrapper
            wrapper.appendChild(tbl);

            // 4) Colocar o wrapper no cartão em vez da tabela direta
            card.appendChild(wrapper);


            // 3a) Cabeçalho
            const thead = tbl.createTHead();
            const hr = thead.insertRow();
            det.campos.forEach(c => {
              const th = document.createElement('th');
              th.textContent = c.LABEL;
              hr.appendChild(th);
            });

            // 3b) Corpo com formatação de datas
            const tbody = tbl.createTBody();
            det.rows.forEach(row => {
              const tr = tbody.insertRow();
              det.campos.forEach(c => {
                const td = tr.insertCell();
                let val = row[c.CAMPODESTINO] ?? '';

                // Caso venha no formato ISO (YYYY-MM-DD)
                if (typeof val === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(val)) {
                  const [y, m, d] = val.split('-');
                  val = `${d}.${m}.${y}`;
                }
                // Caso venha no formato RFC "Fri, 04 Jul 2025 00:00:00 GMT"
                else if (typeof val === 'string' && val.includes('GMT')) {
                  const dt = new Date(val);
                  const d = dt.getDate().toString().padStart(2, '0');
                  const m = (dt.getMonth() + 1).toString().padStart(2, '0');
                  const y = dt.getFullYear();
                  val = `${d}.${m}.${y}`;
                }

                td.textContent = val;
              });
            });

            card.appendChild(tbl);

            // 4) Botões inserir/editar/apagar
            const btnGroup = document.createElement('div');
            btnGroup.className = 'btn-group';
            [
              {icon: 'fa-plus',  fn: () => abrirInserir(det.tabela)},
              {icon: 'fa-edit',  fn: () => abrirEditar(det.tabela)},
              {icon: 'fa-trash', fn: () => apagarDetalhe(det.tabela)}
            ].forEach(b => {
              const btn = document.createElement('button');
              btn.type = 'button';
              btn.className = 'btn btn-outline-secondary btn-sm';
              btn.innerHTML = `<i class="fas ${b.icon}"></i>`;
              btn.onclick = b.fn;
              btnGroup.appendChild(btn);
            });
            card.appendChild(btnGroup);

            // 5) Adicionar ao ecrã
            detailsContainer.appendChild(card);
          });
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
