console.warn('✅ profile_form.js carregado');

const TABLE_NAME = 'US';
const camposEditaveis = ['EMAIL', 'PASSWORD', 'FOTO']; // Ajusta aqui os campos editáveis do perfil

function showLoading() {
  const overlay = document.getElementById('loadingOverlay');
  if (overlay) {
    overlay.style.display = 'flex';
    setTimeout(() => overlay.style.opacity = '1', 15);
  }
}
function hideLoading() {
  const overlay = document.getElementById('loadingOverlay');
  if (overlay) {
    overlay.style.opacity = '0';
    setTimeout(() => overlay.style.display = 'none', 250);
  }
}

document.addEventListener('DOMContentLoaded', async () => {
  showLoading();

  const form = document.getElementById('profileForm');
  if (!form) {
    hideLoading();
    return;
  }

  // Vai buscar metadados dos campos da tabela US
  const res = await fetch(`/generic/api/${TABLE_NAME}?action=describe`);
  const cols = await res.json();

  // Vai buscar os dados do utilizador autenticado
  const userRes = await fetch('/api/whoami');
  const user = await userRes.json();

  // Limpa o form
  form.innerHTML = '';

  // Agrupa por dezena de ORDEM (layout igual ao dynamic_form)
  const isMobile = window.innerWidth <= 768;
  const grupos = {};
  cols
    .sort((a, b) => {
      const oa = isMobile ? a.ordem_mobile : a.ordem;
      const ob = isMobile ? b.ordem_mobile : b.ordem;
      return (oa || 0) - (ob || 0);
    })
    .forEach(col => {
      const ordemUsada = isMobile ? col.ordem_mobile : col.ordem;
      if ((ordemUsada || 0) === 0) return;
      const key = Math.floor(ordemUsada / 10) * 10;
      (grupos[key] ||= []).push(col);
    });

  Object.keys(grupos)
    .sort((a, b) => a - b)
    .forEach(key => {
      const fields = grupos[key];
      const row = document.createElement('div');
      row.className = 'row gx-3 gy-2';
      const totalTam = fields.reduce((acc, f) => acc + (isMobile ? f.tam_mobile : f.tam || 1), 0);
      row.style.display = 'flex';
      row.style.flexWrap = 'nowrap';

      fields.forEach(col => {
        const tamUsado = isMobile ? col.tam_mobile : col.tam;
        const fraction = (tamUsado || 1) / totalTam;
        const colDiv = document.createElement('div');
        colDiv.style.flex = `0 0 ${fraction * 100}%`;
        colDiv.style.boxSizing = 'border-box';
        colDiv.classList.add('col-12');
        row.appendChild(colDiv);

        // Se for um campo vazio, desenha espaço reservado
        if (!col.name) {
          colDiv.innerHTML = '<div class="invisible">.</div>';
          return;
        }

        const wrapper = document.createElement('div');
        wrapper.className = col.tipo === 'BIT' ? 'form-check mb-3' : 'mb-3';
        let input;
        
        // === COMBO ===
        if (col.tipo === 'COMBO') {
          input = document.createElement('select');
          input.className = 'form-select';
          input.name = col.name;
          input.innerHTML = '<option value="">---</option>';
          // Opcional: Preencher opções depois
        }
        // === MEMO ===
        else if (col.tipo === 'MEMO') {
          input = document.createElement('textarea');
          input.className = 'form-control';
          input.name = col.name;
          input.rows = 4;
        }
        // === COLOR ===
        else if (col.tipo && col.tipo.toUpperCase() === 'COLOR') {
          input = document.createElement('input');
          input.type = 'color';
          input.className = 'form-control-color';
          input.name = col.name;
        }
        // === BIT ===
        else if (col.tipo === 'BIT') {
          input = document.createElement('input');
          input.type = 'checkbox';
          input.className = 'form-check-input';
          input.name = col.name;
          input.checked = !!user[col.name];
          input.disabled = true; // Nunca editável por perfil
        }
        // === TEXT, DATE, ETC ===
        else {
          input = document.createElement('input');
          input.type = (col.tipo === 'DATE') ? 'text' : 'text';
          input.className = 'form-control';
          input.name = col.name;
        }

        // Preencher valor do utilizador
        if (col.tipo !== 'BIT') {
          input.value = user[col.name] || '';
        }

        // Editável só se constar nos camposEditaveis
        if (!camposEditaveis.includes(col.name)) {
          input.readOnly = true;
          input.classList.add('bg-light');
        } else {
          input.readOnly = false;
        }
        
        // Label
        const label = document.createElement('label');
        label.setAttribute('for', col.name);
        label.className = 'form-label';
        label.innerHTML = `${col.descricao || col.name}`;
        wrapper.appendChild(label);
        wrapper.appendChild(input);
        colDiv.appendChild(wrapper);
      });
      form.appendChild(row);
    });

  hideLoading();

  // Submissão do perfil (apenas placeholder, ainda não grava nada)
  form.addEventListener('submit', e => {
    e.preventDefault();
    document.getElementById('profileMsg').textContent = '🚧 Gravação ainda não implementada!';
  });
});

// Abrir modal ao clicar no botão "Alterar Password"
document.getElementById('btnChangePwd').addEventListener('click', () => {
  document.getElementById('formChangePwd').reset();
  document.getElementById('msgPwd').textContent = '';
  const modal = new bootstrap.Modal(document.getElementById('modalChangePwd'));
  modal.show();
});

// Validar e submeter o formulário de alteração de password
document.getElementById('formChangePwd').addEventListener('submit', async function(e) {
  e.preventDefault();
  const pwd1 = document.getElementById('pwd1').value.trim();
  const pwd2 = document.getElementById('pwd2').value.trim();
  const msgDiv = document.getElementById('msgPwd');

  if (!pwd1 || pwd1.length < 4) {
    msgDiv.textContent = 'Password deve ter pelo menos 4 caracteres.';
    msgDiv.classList.remove('text-success');
    msgDiv.classList.add('text-danger');
    return;
  }
  if (pwd1 !== pwd2) {
    msgDiv.textContent = 'As passwords não coincidem!';
    msgDiv.classList.remove('text-success');
    msgDiv.classList.add('text-danger');
    return;
  }

  // Chama a API para atualizar password
  const res = await fetch('/api/profile/change_password', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({ password: pwd1 })
  });

  if (res.ok) {
    msgDiv.textContent = 'Password alterada com sucesso!';
    msgDiv.classList.remove('text-danger');
    msgDiv.classList.add('text-success');
    setTimeout(() => {
      bootstrap.Modal.getInstance(document.getElementById('modalChangePwd')).hide();
    }, 1200);
  } else {
    msgDiv.textContent = 'Erro ao atualizar password!';
    msgDiv.classList.remove('text-success');
    msgDiv.classList.add('text-danger');
  }
});
