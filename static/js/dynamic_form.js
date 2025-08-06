// static/js/dynamic_form.js
console.warn('✅ novo dynamic_form.js carregado');

// ===============================
// 1. VARIÁVEIS GLOBAIS & INICIALIZAÇÃO
// ===============================

document.addEventListener('DOMContentLoaded', () => {
  console.log('📦 DOM totalmente carregado');

  const itens = document.querySelectorAll('.dropdown-item');
  console.log('🧪 dropdown-item encontrados:', itens.length);

  itens.forEach(item => {
    item.addEventListener('click', e => {
      console.log('🔘 CLICADO:', item.innerText.trim());
      e.preventDefault();
    });
  });
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


// 🧪 DEBUG extra
console.log('🧪 dropdown-item encontrados:', document.querySelectorAll('.dropdown-item').length);

(async function() {

  showLoading()

  const isMobile = window.innerWidth <= 768;
  console.log('📱 Modo:', isMobile ? 'MOBILE' : 'DESKTOP');

  const formState = {};
  const camposByName = {};

  // ─── DEBUG: find all custom‐action buttons ───
  console.log('modal triggers encontrados:', document.querySelectorAll('.btn-custom'));

  const TABLE_NAME   = window.TABLE_NAME;
  const RECORD_STAMP = window.RECORD_STAMP;
  const isAdminUser  = window.IS_ADMIN_USER;
  const DEV_MODE = window.DEV_MODE || false;

  console.log('[dynamic_form.js] TABLE_NAME:', TABLE_NAME);

  // ─── Guardar para onde voltar + que detalhe ancorar ───
  // Captura o return_to (e detail_* se vierem) da URL
  const urlParams = new URLSearchParams(window.location.search);

  // Este form é acedido a partir de outro? Ou diretamente?
  const returnTo = urlParams.get('return_to');
  const RETURN_URL = returnTo && returnTo.trim() !== ''
    ? returnTo
    : `/generic/view/${TABLE_NAME}/`;

  console.log('📍 RETURN_URL =', RETURN_URL);


  const DETAIL_TAB = urlParams.get('detail_table')|| null;
  const DETAIL_PK  = urlParams.get('detail_pk')   || null;

    
// ===============================
// 2. CONSTRUÇÃO DO FORMULÁRIO
// ===============================

  const res  = await fetch(`/generic/api/${TABLE_NAME}?action=describe`);
  const cols = await res.json();

  console.log("🧠 Metadados recebidos:", cols);

    // ===============================
    // FUNÇÃO UTILITÁRIA: AVALIAR EXPRESSÕES DE VISIBILIDADE
    // ===============================
    function avaliarExpressao(expr) {
      try {
        const keys = Object.keys(formState);
        const values = Object.values(formState);

        console.log("🧪 EXPRESSÃO:", expr);
        console.log("🧪 KEYS:", keys);
        console.log("🧪 VALUES:", values);
        console.log("🧪 FORMSTATE:", formState);

        const fn = new Function(...keys, `'use strict'; return (${expr});`);
        const result = fn(...values);

        console.log("✅ RESULTADO:", result);
        return result;

      } catch (err) {
        console.warn(`⚠️ Erro ao avaliar expressão: ${expr}`, err);
        return true;
      }
    }

    // ===============================
    // FUNÇÃO: APLICAR CONDIÇÕES DE VISIBILIDADE AOS CAMPOS
    // ===============================
    function aplicarCondicoesDeVisibilidade() {
      cols.forEach(col => {
        if (!col.condicao_visivel) return;

        const input = camposByName[col.name];
        if (!input) return;

        const wrapper = input.closest('.col-12') || input.closest('.form-check') || input.closest('.mb-3');
        const visivel = avaliarExpressao(col.condicao_visivel, formState);

        if (wrapper) {
          wrapper.style.display = visivel ? '' : 'none';
        }
      });
    }


  console.table(cols.map(c => ({
  campo: c.name,
  ordem: c.ordem,
  ordem_mobile: c.ordem_mobile,
  tam: c.tam,
  tam_mobile: c.tam_mobile
  })));


  // 2. Prepara o form
  const form = document.getElementById('editForm');
  // ——— Montagem customizada por ORDEM (uma row por dezena) ———

  // limpa o form
  form.innerHTML = '';

  // agrupa por dezena de ORDEM
  const grupos = {};
  cols
    .filter(c => !c.admin || isAdminUser)
    .sort((a, b) => {
      const oa = isMobile ? a.ordem_mobile : a.ordem;
      const ob = isMobile ? b.ordem_mobile : b.ordem;
      return (oa || 0) - (ob || 0);
    })
    .forEach(col => {
      const ordemUsada = isMobile ? col.ordem_mobile : col.ordem;
      if ((ordemUsada || 0) === 0) return; // se 0, ignorar no mobile (por convenção)

      const key = Math.floor(ordemUsada / 10) * 10;
      (grupos[key] ||= []).push(col);
    });

  // monta cada grupo numa única row
  Object.keys(grupos)
    .sort((a, b) => a - b)
    .forEach(key => {
      const fields = grupos[key];
      const row    = document.createElement('div');
      row.className = 'row gx-3 gy-2';

      // soma total dos TAM para calcular proporções
      const totalTam = fields.reduce((acc, f) => acc + (isMobile ? f.tam_mobile : f.tam || 1), 0);


      row.style.display = 'flex';
      row.style.flexWrap = 'nowrap';


      fields.forEach(col => {
        const tamUsado = isMobile ? col.tam_mobile : col.tam;
        const fraction = (tamUsado || 1) / totalTam;
        const colDiv = document.createElement('div');
        // fixa largura proporcional e impede flex-grow/shrink
        colDiv.style.flex = `0 0 ${fraction * 100}%`;
        colDiv.style.boxSizing = 'border-box';
        // mantém o mesmo comportamento de responsive para mobile
        colDiv.classList.add('col-12');
        row.appendChild(colDiv);

        // se for um campo "vazio", desenha apenas um espaço reservado
        if (!col.name) {
          colDiv.innerHTML = '<div class="invisible">.</div>'; // ocupa espaço mas invisível
          return;
        }

        // NOVO: campo COLOR
        if ((col.tipo || '').toUpperCase() === 'COLOR') {
          let input = document.createElement('input');
          input.type = 'color';
          input.className = 'form-control-color';
          input.name = col.name;
          input.id = col.name;
          input.value = col.valor || col.valorAtual || col.VALORDEFAULT || '#000000';
          formState[col.name] = input.value;
          camposByName[col.name] = input;
          input.addEventListener('change', e => {
            formState[col.name] = e.target.value;
            aplicarCondicoesDeVisibilidade();
          });

          const wrapper = document.createElement('div');
          wrapper.className = 'mb-3';
          const label = document.createElement('label');
          label.setAttribute('for', col.name);
          label.className = 'form-label';
          label.innerHTML = `${col.descricao || col.name}`;
          wrapper.appendChild(label);
          wrapper.appendChild(input);

          colDiv.appendChild(wrapper);
          return;
        }
                
        const wrapper = document.createElement('div');
        wrapper.className = col.tipo === 'BIT' ? 'form-check mb-3' : 'mb-3';

        if (col.tipo === 'BIT') {
              wrapper.innerHTML = `
                <input class="form-check-input" type="checkbox"
                      id="${col.name}" name="${col.name}">
                <label class="form-check-label" for="${col.name}">
                  ${col.descricao || col.name}
                </label>
              `;

              const input = wrapper.querySelector('input');
              formState[col.name] = false;
              camposByName[col.name] = input;

              input.addEventListener('change', e => {
                const nome = e.target.name.toUpperCase();
                formState[nome] = e.target.type === 'checkbox' ? e.target.checked : e.target.value;
                aplicarCondicoesDeVisibilidade();
              });
            } else {
              const label = document.createElement('label');
              label.setAttribute('for', col.name);
              label.className = 'form-label';
              label.innerHTML = `${col.descricao || col.name}`;
              if (col.obrigatorio) {
                label.innerHTML += ' <span style="color:red">*</span>';
              }


            // DEV MODE: adiciona info ORDEM | TAM se estiver ativo
            if (window.DEV_MODE) {
              const ordemAtual = isMobile ? col.ordem_mobile : col.ordem;
              const tamAtual   = isMobile ? col.tam_mobile   : col.tam;

              const metaTag = document.createElement('span');
              metaTag.textContent = `${ordemAtual}|${tamAtual}`;
              metaTag.className = 'badge-dev-edit';
              metaTag.style.cursor = 'pointer';

              metaTag.addEventListener('click', () => {
                const novaOrdem = prompt(
                  `Nova ${isMobile ? 'ORDEM_MOBILE' : 'ORDEM'} para ${col.name}:`, ordemAtual
                );
                const novoTam = prompt(
                  `Novo ${isMobile ? 'TAM_MOBILE' : 'TAM'} para ${col.name}:`, tamAtual
                );

                const ordemInt = parseInt(novaOrdem, 10);
                const tamInt   = parseInt(novoTam, 10);

                if (isNaN(ordemInt) || isNaN(tamInt)) {
                  alert("Valores inválidos. Ambos devem ser inteiros.");
                  return;
                }

                // Monta dinamicamente o payload com os campos certos
                const body = {
                  tabela: TABLE_NAME,
                  campo: col.name
                };

                if (isMobile) {
                  body.ordem_mobile = ordemInt;
                  body.tam_mobile   = tamInt;
                } else {
                  body.ordem = ordemInt;
                  body.tam   = tamInt;
                }

                fetch('/generic/api/update_campo', {
                  method: 'POST',
                  headers: { 'Content-Type': 'application/json' },
                  body: JSON.stringify(body)
                })
                .then(res => res.json())
                .then(resp => {
                  if (resp.success) {
                    alert("Campo atualizado com sucesso.");
                    window.location.reload();
                  } else {
                    alert("Erro: " + resp.error);
                  }
                })
                .catch(err => {
                  console.error(err);
                  alert("Erro inesperado ao atualizar.");
                });
              });

              label.appendChild(metaTag);
            }
            wrapper.appendChild(label); 

            let input;

            if (col.tipo === 'COMBO') {
              input = document.createElement('select');
                if (col.obrigatorio) {
                  input.required = true;
                }
              camposByName[col.name] = input;
              input.className = 'form-select';
              input.name = col.name;
              input.innerHTML = '<option value="">---</option>';

              formState[col.name] = '';
              input.addEventListener('change', e => {
                const nome = e.target.name.toUpperCase();
                formState[nome] = e.target.type === 'checkbox' ? e.target.checked : e.target.value;
                aplicarCondicoesDeVisibilidade();
              });


            } else if (col.tipo === 'MEMO') {
              input = document.createElement('textarea');
                if (col.obrigatorio) {
                  input.required = true;
                }
              camposByName[col.name] = input;
              input.className = 'form-control';
              input.name = col.name;
              input.rows = 4;

              formState[col.name] = '';
              input.addEventListener('change', e => {
                const nome = e.target.name.toUpperCase();
                formState[nome] = e.target.type === 'checkbox' ? e.target.checked : e.target.value;
                aplicarCondicoesDeVisibilidade();
              });

            } else {
              input = document.createElement('input');
                if (col.obrigatorio) {
                  input.required = true;
                }
              camposByName[col.name] = input;
              input.className = 'form-control';
              input.name = col.name;

              if (col.tipo === 'DATE') {
                input.type = 'text';
                input.classList.add('flatpickr-date');
              } else {
                input.type = 'text';
              }

              if (col.readonly) {
                input.readOnly = true;
                input.classList.add('bg-light');
              }

              if (col.tipo === 'BIT') {
                formState[col.name] = false;
                input.type = 'checkbox';
                input.className = 'form-check-input';
                input.addEventListener('change', e => {
                  const nome = e.target.name.toUpperCase();
                  formState[nome] = e.target.type === 'checkbox' ? e.target.checked : e.target.value;
                  aplicarCondicoesDeVisibilidade();
                });
              } else {
                formState[col.name] = '';
                input.addEventListener('change', e => {
                  const nome = e.target.name.toUpperCase();
                  formState[nome] = e.target.type === 'checkbox' ? e.target.checked : e.target.value;
                  aplicarCondicoesDeVisibilidade();
                });
              }
            }

            wrapper.appendChild(input);
        }

        colDiv.appendChild(wrapper);
      });
      
      form.appendChild(row);
    });

    console.log("💬 formState final antes de aplicar visibilidade:", formState);
    aplicarCondicoesDeVisibilidade();



  // 4. Popula combos
  // ===============================
// 3. COMBOS E VALORES DEFAULT
// ===============================

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

    // 5. Preenche defaults a partir da query string (para inserção de linhas)
  {
    const urlParams = new URLSearchParams(window.location.search);
    urlParams.forEach((val, key) => {
      const el = form.querySelector(`[name="${key}"]`);
      if (!el) return;
      if (el.tagName === 'SELECT') {
        // garante que o <select> já tem as <option>
        if ([...el.options].some(o => o.value === val)) {
          el.value = val;
          formState[el.name] = el.type === 'checkbox' ? el.checked : el.value;
          aplicarCondicoesDeVisibilidade();
        }
      }
      else if (el.type === 'checkbox') {
        el.checked = ['1','true','True'].includes(val);
      } else {
        el.value = val;
      }
    });
  }

  // ===============================
// 4. CARREGAMENTO DE DADOS EXISTENTES
// ===============================

// 4. Se edição, carrega valores com matching inteligente
if (RECORD_STAMP) {
  try {
    const rec = await (await fetch(`/generic/api/${TABLE_NAME}/${RECORD_STAMP}`)).json();
    Object.entries(rec).forEach(([key, val]) => {
      const nome = key.toUpperCase();
      const el = form.querySelector(`[name="${key}"]`);
      if (!el) return;

      if (el.tagName === 'SELECT') {
        const desired = (val || '').toString().trim();
        if ([...el.options].some(o => o.value === desired)) {
          el.value = desired;
        } else {
          const match = [...el.options].find(o => o.textContent.trim() === desired);
          el.value = match ? match.value : '';
        }
        formState[nome] = el.value;
      } else if (el.type === 'checkbox') {
        el.checked = !!val;
        formState[nome] = el.checked;
      } else if (el.classList.contains('flatpickr-date')) {
        if (val) {
          let d, m, y;
          if (/^\d{4}-\d{2}-\d{2}/.test(val)) {
            [y, m, d] = val.slice(0, 10).split('-');
          } else {
            const dt = new Date(val);
            d = String(dt.getDate()).padStart(2, '0');
            m = String(dt.getMonth() + 1).padStart(2, '0');
            y = dt.getFullYear();
          }
          el.value = `${d}.${m}.${y}`;
        } else {
          el.value = '';
        }
        formState[nome] = el.value;
        } else if (el.type === 'color') {
        // se a cor vier sem "#", adiciona
        let cor = (val || '').toString().trim();
        if (cor && !cor.startsWith('#')) cor = '#' + cor;
        el.value = cor || '#000000';
        formState[nome] = el.value;
      } else {
        el.value = val;
        formState[nome] = el.value;
      }
    });
  } catch (e) {
    console.error('Erro ao carregar registro:', e);
  }
} else {
  document.getElementById('btnDelete')?.style.setProperty('display', 'none');
}

hideLoading()

  // ===============================
// 5. FLATPICKR E FORMATOS
// ===============================

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
  }
    // ===============================
// 6. GESTÃO DE DETALHES (1:N)
// ===============================

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

            // 4) Cabeçalho da tabela (checkbox como primeira coluna)
            const thead = tbl.createTHead();
            const hr    = thead.insertRow();

            // inserimos a célula de seleção NA POSIÇÃO 0
            const thSel = hr.insertCell(0);
            thSel.innerHTML = '';        // fica em branco, mas força a coluna
            thSel.style.width = '2rem';  // largura fixa para o checkbox

            // agora as colunas normais (iniciam em índice 1)
            det.campos.forEach(c => {
              if (c.VISIVEL === false) return;  // ignora colunas invisíveis
              const th = document.createElement('th');
              th.textContent = c.LABEL;
              hr.appendChild(th);
            });

            // 5) Corpo da tabela com formatação de datas
            const tbody = tbl.createTBody();
            det.rows.forEach(row => {
              const tr = tbody.insertRow();

              // 5.1) checkbox na célula 0
              const tdSel = tr.insertCell(0);
              const chk   = document.createElement('input');
              chk.type    = 'checkbox';
              chk.className = 'form-check-input detail-select';
              chk.style.transform = 'scale(1.1'; // opcional: aumenta o tamanho
              const pk    = row[det.campos[0].CAMPODESTINO];
              chk.value   = pk;
              tdSel.appendChild(chk);

              // 5.2) restantes colunas (começam em 1)
              det.campos.forEach(c => {
                if (c.VISIVEL === false) return;  // ignora colunas invisíveis
                const td = tr.insertCell();
                let val = row[c.CAMPODESTINO] ?? '';
                td.textContent = val;
              });

              // 5.3) clique na linha
              // 5.3) clique na linha
              tr.addEventListener('click', e => {
                if (e.target !== chk) {
                  const pk = row[det.campos[0].CAMPODESTINO];
                  
                  // Certifica-te que TABLE_NAME e RECORD_STAMP estão definidos globalmente
                  const parentFormUrl = `/generic/form/${TABLE_NAME}/${RECORD_STAMP}`;

                  const p = new URLSearchParams({
                    return_to: parentFormUrl,
                    detail_table: det.tabela,
                    detail_pk: pk
                  });

                  window.location.href = `/generic/form/${det.tabela}/${pk}?${p.toString()}`;
                }
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
              const params = new URLSearchParams();

              // Copia campos do formulário pai para os campos da linha filha
              det.camposcab.forEach((fullSrc, i) => {
                const fullDst = det.camposlin[i];
                if (!fullDst) return;

                const srcCol = fullSrc.split('.')[1];
                const dstCol = fullDst.split('.')[1];
                const val = form.querySelector(`[name="${srcCol}"]`)?.value;

                if (val) params.append(dstCol, val);
              });

              // URL do form da tabela mãe
              const parentFormUrl = `/generic/form/${TABLE_NAME}/${RECORD_STAMP}`;

              params.append('return_to', parentFormUrl);
              params.append('detail_table', det.tabela);

              window.location.href = `/generic/form/${det.tabela}/?${params.toString()}`;
            });

            // Editar (usa a primeira coluna como chave)
            const btnEdit = document.createElement('button');
            btnEdit.className = 'btn btn-sm btn-secondary';
            btnEdit.title = 'Editar';
            btnEdit.innerHTML = '<i class="fa fa-edit"></i>';
            btnEdit.addEventListener('click', () => {
              const id  = row[det.campos[0].CAMPODESTINO];
              const cur = window.location.pathname + window.location.search;
              const ret = encodeURIComponent(cur);
              window.location.href = `/generic/form/${det.tabela}/${id}`
                + `?return_to=${ret}`
                + `&detail_table=${det.tabela}`
                + `&detail_anchor=${id}`;
            });

            // Eliminar
            // Eliminar (tanto single como múltiplos via checkbox)
            const btnDelete = document.createElement('button');
            btnDelete.className = 'btn btn-sm btn-danger';
            btnDelete.title = 'Eliminar';
            btnDelete.innerHTML = '<i class="fa fa-trash"></i>';
            btnDelete.addEventListener('click', async e => {
              e.stopPropagation();

              // ——— AQUI, dentro do listener, antes de qualquer fetch/delete ———
              // 1) encontra qual é o campo PK (invisível) na definição de colunas
              const campoPK = det.campos.find(c => c.PRIMARY_KEY || c.VISIVEL === false)?.CAMPODESTINO;
              if (!campoPK) {
                alert("Chave primária não definida.");
                return;
              }

              // 2) recolhe todas as linhas marcadas
              const checked = Array.from(card.querySelectorAll('tbody input[type="checkbox"]'))
                                  .filter(ch => ch.checked);

              // 3) se não houver nenhuma marcada, apaga só a primeira linha
              if (checked.length === 0) {
                // pega a primeira <tr>
                const firstRow = card.querySelector('tbody tr');
                if (!firstRow) return alert('Nenhum registo visível.');

                // usa o campo PK para ir buscar o valor correto
                const rowData = det.rows.find(r => r[campoPK] === firstRow.querySelector('input').value);
                const id = rowData ? rowData[campoPK] : null;
                if (!id) return alert('Não consegui determinar o ID a eliminar.');

                if (!confirm('Confirmar eliminação deste registo?')) return;

                const resp = await fetch(`/generic/api/${det.tabela}/${id}`, { method: 'DELETE' });
                if (!resp.ok) {
                  const err = await resp.json().catch(() => ({}));
                  return alert('Erro: ' + (err.error || resp.statusText));
                }

                firstRow.remove();
                return;
              }

              // 4) se houver múltiplos marcados, percorre cada um
              if (!confirm(`Eliminar ${checked.length} registo(s)?`)) return;
              for (const ch of checked) {
                const id = ch.value;  // ch.value já foi definido como row[campoPK]
                const resp = await fetch(`/generic/api/${det.tabela}/${id}`, { method: 'DELETE' });
                if (!resp.ok) {
                  const err = await resp.json().catch(() => ({}));
                  alert(`Falha ao eliminar ${id}: ${err.error || resp.statusText}`);
                  continue;
                }
                ch.closest('tr').remove();
              }

              // — fim do listener —
            });


            btnGroup.append(btnInsert, btnDelete);
            card.appendChild(btnGroup);

            // 7) Anexa o card ao container
            detailsContainer.appendChild(card);
          });
        })
        .catch(err => {
          console.error('Erro ao carregar detalhes:', err);
        });
      }   

    // ===============================
// 7. ANEXOS
// ===============================

// ——— Início Anexos ———
    const btnAddAnexo = document.getElementById('btnAddAnexo');
    const inputAnexo  = document.getElementById('inputAnexo');
    const listaAnx    = document.getElementById('anexos-list');

    async function refreshAnexos() {
      if (!RECORD_STAMP) return; // só em edição
      const res = await fetch(`/api/anexos?table=${TABLE_NAME}&rec=${RECORD_STAMP}`);
      if (!res.ok) return console.error('Falha ao listar anexos');
      const arr = await res.json();

      if (!arr.length) {
        listaAnx.innerHTML = '<p class="text-muted">Ainda não há anexos.</p>';
        return;
      }

      listaAnx.innerHTML = arr.map(a => `
        <div class="d-inline-flex align-items-center me-2 mb-2 p-2 rounded-pill bg-light">
          <i class="fa fa-info-circle text-primary me-2" 
            data-id="${a.ANEXOSSTAMP}" title="Ver detalhes"
            style="cursor: pointer;"></i>

          <!-- O link do ficheiro volta aqui: -->
          <a href="${a.CAMINHO}" target="_blank" class="text-decoration-none text-body">
            ${a.FICHEIRO}
          </a>

          <i class="fa fa-times text-danger ms-2" 
            data-id="${a.ANEXOSSTAMP}" title="Eliminar anexo" 
            style="cursor: pointer;"></i>
        </div>
      `).join('');

      // info → abre dynamic_form da tabela ANEXOS
      listaAnx.querySelectorAll('.fa-info-circle').forEach(el => {
        el.addEventListener('click', () => {
          const id = el.dataset.id;
          window.location.href = `/generic/form/ANEXOS/${id}`;
        });
      });

      // × → apagar
      listaAnx.querySelectorAll('.fa-times').forEach(el => {
        el.addEventListener('click', async () => {
          const id = el.dataset.id;
          if (!confirm('Eliminar este anexo?')) return;

          // aqui: ajusta a URL para o teu endpoint de delete correto.
          // Por exemplo, se estiver em generic/api/anexos/<id>:
          const resp = await fetch(`/generic/api/anexos/${id}`, { method: 'DELETE' });

          if (!resp.ok) {
            const err = await resp.json().catch(() => ({}));
            return alert('Erro ao eliminar: ' + (err.error || resp.statusText));
          }
          await refreshAnexos();
        });
      });
    }


    // abrir file picker
    btnAddAnexo.addEventListener('click', () => inputAnexo.click());

    // upload
    inputAnexo.addEventListener('change', async () => {
      const file = inputAnexo.files[0];
      if (!file || !RECORD_STAMP) return;
      const formD = new FormData();
      formD.append('file', file);
      formD.append('table', TABLE_NAME);
      formD.append('rec', RECORD_STAMP);
      formD.append('descricao', ''); 

      const res = await fetch('/api/anexos/upload', {
        method: 'POST',
        body: formD
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        return alert('Erro ao anexar: ' + (err.error || res.statusText));
      }
      inputAnexo.value = '';
      await refreshAnexos();
    });

    // assim que o form carrega, busca os anexos
    if (RECORD_STAMP) {
      await refreshAnexos();
    }
    // ——— Fim Anexos ———



    // ===============================
// 8. PERMISSÕES E BOTÕES
// ===============================

// 6. Cancelar e eliminar
    document.getElementById('btnCancel')?.addEventListener('click', ()=> {
    window.location.href = RETURN_URL;
    });
    // Eliminar
    document.getElementById('btnDelete')?.addEventListener('click', async () => {
      if (!RECORD_STAMP || !TABLE_NAME) return;
      if (!confirm('Confirmar eliminação?')) return;

      try {
        const resp = await fetch(`/generic/api/${TABLE_NAME}/${RECORD_STAMP}`, { method: 'DELETE' });
        if (!resp.ok) {
          const err = await resp.json().catch(() => ({}));
          alert('Erro: ' + (err.error || resp.statusText));
          return;
        }
        window.location.href = RETURN_URL;
      } catch (err) {
        console.error('Erro ao eliminar:', err);
        alert('Erro inesperado ao eliminar.');
      }
    });

      // ===============================
// 10. MODAIS CUSTOMIZADOS
// ===============================

// ─── Hooks para os botões customizados de MODAL ───
      // (click em qualquer <a class="dropdown-item btn-custom" data-tipo="MODAL">)
      document.addEventListener('click', e => {
        const btn = e.target.closest('.dropdown-item.btn-custom[data-tipo="MODAL"]');
        if (!btn) return;
        console.log('⚡ custom modal button clicked:', btn.dataset.acao);
        e.preventDefault();
        abrirModal(btn.dataset.acao);
      });

      // Hook para botões customizados do tipo ACAO (executa código JS do campo ACAO)
      document.addEventListener('click', e => {
        // <a> ou <button> com .btn-custom[data-tipo="ACAO"]
        const btn = e.target.closest('.btn-custom[data-tipo="ACAO"]');
        if (!btn) return;

        e.preventDefault();
        try {
          // O código vem no atributo data-acao (campo ACAO da MENUBOTOES)
          // Podes usar RECORD_STAMP, TABLE_NAME, etc, aqui.
          // Usa new Function para correr o código JS
          const fn = new Function('TABLE_NAME', 'RECORD_STAMP', btn.dataset.acao);
          fn(window.TABLE_NAME, window.RECORD_STAMP);
        } catch (err) {
          alert("Erro ao executar ação: " + err.message);
        }
      });      

    // Voltar
    document.getElementById('btnBack')?.addEventListener('click', () => {
      if (RETURN_URL) {
        window.location.href = RETURN_URL;
      } else {
        history.back();
      }
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

  // ===============================
// 9. SUBMISSÃO DO FORMULÁRIO
// ===============================

// 7. Submit com tratamento de erros
  form.addEventListener('submit', async e => {
    e.preventDefault();

    // ✂️ Limpar espaços dos campos de texto
    form.querySelectorAll('input, textarea').forEach(el => {
      const tipo = el.type?.toLowerCase();
      if (tipo !== 'checkbox' && typeof el.value === 'string') {
        el.value = el.value.trim();
      }
    });

    if (!form.checkValidity()) {
      form.classList.add('was-validated');
      alert("⚠️ Existem campos obrigatórios por preencher.");
      return;
    }

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
      window.location.href = RETURN_URL;
    } catch (net) {
      alert(`Erro de rede: ${net.message}`);
    }
  });


  aplicarCondicoesDeVisibilidade();

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

// static/js/dynamic_form.js

// ===============================
// 10. MODAIS CUSTOMIZADOS
// ===============================

// ─── Hooks para os botões customizados de MODAL ───
document.addEventListener('click', e => {
  // procura o <a> ou <button> mais perto que tenha classe btn-custom e data-tipo="MODAL"
  const btn = e.target.closest('.btn-custom[data-tipo="MODAL"]');
  if (!btn) return;

  e.preventDefault();
  // data-acao contém o nome do modal
  const nomeModal = btn.dataset.acao;
  abrirModal(nomeModal);
});

// at the very top, before any form-building logic
function criarInputPadrao(campo, valorAtual = '') {
  const input = document.createElement('input');
  input.type = 'text';
  input.className = 'form-control';
  input.value = valorAtual;
  return input;
}

function renderCampo(campo, valorAtual = '') {
  const div = document.createElement('div');
  div.className = 'col-12 mb-3';
  const label = document.createElement('label');
  label.className = 'form-label';
  label.textContent = campo.descricao || campo.name;
  div.appendChild(label);

  let input;
  const tipo = campo.tipo.toUpperCase();

  if (tipo === 'COLOR') {
    input = document.createElement('input');
    input.type = 'color';
    input.className = 'form-control form-control-color';
    input.value = valorAtual || '#000000';
  }
  else if (tipo === 'LINK') {
    const wrapper = document.createElement('div');
    wrapper.className = 'input-group';
    input = document.createElement('input');
    input.type = 'text';
    input.className = 'form-control';
    input.placeholder = 'https://...';
    input.value = valorAtual || '';
    const button = document.createElement('a');
    button.className = 'btn btn-outline-secondary';
    button.target = '_blank';
    button.href   = input.value || '#';
    button.innerHTML = '<i class="fa fa-link"></i>';
    input.addEventListener('input', () => button.href = input.value);
    wrapper.appendChild(input);
    wrapper.appendChild(button);
    div.appendChild(wrapper);
    // skip the `div.appendChild(input)` below
    input.dataset.campo = campo.name;
    return div;
  }
  else {
    input = criarInputPadrao(campo, valorAtual);
  }

  input.dataset.campo = campo.name;
  div.appendChild(input);
  return div;
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

// Expõe no global para onclick inline (se precisares)
window.abrirModal = abrirModal;
window.gravarModal = gravarModal;

// ===============================
// 11. EVENTOS GERAIS
// ===============================

// Liga todos os dropdown-items que abrem modal
document.querySelectorAll('.dropdown-item.btn-custom[data-tipo="MODAL"]')
  .forEach(el => {
    el.addEventListener('click', e => {
      e.preventDefault();
      abrirModal(el.dataset.acao);
    });
  });
