console.warn('âœ… profile_form.js carregado');

const tr = (key, vars) => (typeof window.t === 'function' ? window.t(key, vars) : key);
const TABLE_NAME = 'US';
const camposEditaveis = ['EMAIL', 'COR', 'VIEWMODE']; // PASSWORD e FOTO tratadas em flows proprios
const camposOcultos = ['PASSWORD', 'FOTO']; // nÃ£o desenhar estes campos no formulÃ¡rio

const camposMostrar = ['NOME', 'COR', 'LOGIN', 'EMAIL'];
const THEME_KEY = 'sz_theme_mode';
const VIEWMODE_BY_THEME = {
  light: 'LIGHT MODE',
  dark: 'DARK MODE',
  geek: 'GEEK MODE'
};
const THEME_BY_VIEWMODE = {
  'LIGHT MODE': 'light',
  'DARK MODE': 'dark',
  'GEEK MODE': 'geek'
};

function normalizeViewMode(viewMode) {
  const raw = String(viewMode || '').trim().toUpperCase();
  if (raw === 'LIGHT' || raw === 'DARK' || raw === 'GEEK') {
    return `${raw} MODE`;
  }
  return THEME_BY_VIEWMODE[raw] ? raw : 'LIGHT MODE';
}

function applyThemeFromViewMode(viewMode) {
  const normalized = normalizeViewMode(viewMode);
  const theme = THEME_BY_VIEWMODE[normalized] || 'light';
  document.documentElement.setAttribute('data-sz-theme', theme);
  try {
    localStorage.setItem(THEME_KEY, theme);
  } catch (_) {}
}
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
  const viewModeSelect = document.getElementById('profileViewMode');

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
      row.style.flexWrap = 'wrap';

      fields.forEach(col => {
        if (camposOcultos.includes(col.name)) return; // salta campos ocultos
        if (!camposMostrar.includes(col.name)) return; // mostra apenas os desejados
        const tamUsado = isMobile ? col.tam_mobile : col.tam;
        const fraction = (tamUsado || 1) / totalTam;
        const colDiv = document.createElement('div');
        // ForÃ§a LOGIN e EMAIL a ocupar 100% da largura
        if (['LOGIN','EMAIL'].includes(col.name)) {
          colDiv.style.flex = '0 0 100%';
        } else {
          colDiv.style.flex = `0 0 ${fraction * 100}%`;
        }
        colDiv.style.boxSizing = 'border-box';
        colDiv.classList.add('col-12');
        row.appendChild(colDiv);

        // Se for um campo vazio, desenha espaÃ§o reservado
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
          // Opcional: Preencher opÃ§Ãµes depois
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
          input.disabled = true; // Nunca editÃ¡vel por perfil
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
          let v = user[col.name] || '';
          if (col.tipo && col.tipo.toUpperCase() === 'COLOR') {
            if (!v || typeof v !== 'string' || !v.startsWith('#')) {
              v = '#223044';
            }
          }
          input.value = v;
        }

        // EditÃ¡vel sÃ³ se constar nos camposEditaveis
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

  if (viewModeSelect) {
    const currentViewMode = normalizeViewMode(user.VIEWMODE);
    viewModeSelect.value = currentViewMode;
    viewModeSelect.addEventListener('change', async () => {
      const selected = normalizeViewMode(viewModeSelect.value);
      applyThemeFromViewMode(selected);
      try {
        const resp = await fetch('/api/profile/viewmode', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ viewmode: selected })
        });
        if (!resp.ok) throw new Error(tr('profile.view_mode_error'));
        const msg = document.getElementById('profileMsg');
        if (msg) {
          msg.textContent = tr('profile.view_mode_saved');
          msg.classList.remove('text-danger');
          msg.classList.add('text-success');
        }
      } catch (_) {
        const msg = document.getElementById('profileMsg');
        if (msg) {
          msg.textContent = tr('profile.view_mode_error');
          msg.classList.remove('text-success');
          msg.classList.add('text-danger');
        }
      }
    });
  }

  hideLoading();
});

// Abrir modal ao clicar no botÃ£o "Alterar Password"
document.getElementById('btnChangePwd').addEventListener('click', () => {
  document.getElementById('formChangePwd').reset();
  document.getElementById('msgPwd').textContent = '';
  const modal = new bootstrap.Modal(document.getElementById('modalChangePwd'));
  modal.show();
});

// Validar e submeter o formulÃ¡rio de alteraÃ§Ã£o de password
document.getElementById('formChangePwd').addEventListener('submit', async function(e) {
  e.preventDefault();
  const pwd1 = document.getElementById('pwd1').value.trim();
  const pwd2 = document.getElementById('pwd2').value.trim();
  const msgDiv = document.getElementById('msgPwd');

  if (!pwd1 || pwd1.length < 4) {
    msgDiv.textContent = tr('profile.password_short');
    msgDiv.classList.remove('text-success');
    msgDiv.classList.add('text-danger');
    return;
  }
  if (pwd1 !== pwd2) {
    msgDiv.textContent = tr('profile.passwords_mismatch');
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
    msgDiv.textContent = tr('profile.password_updated');
    msgDiv.classList.remove('text-danger');
    msgDiv.classList.add('text-success');
    setTimeout(() => {
      bootstrap.Modal.getInstance(document.getElementById('modalChangePwd')).hide();
    }, 1200);
  } else {
    msgDiv.textContent = tr('profile.password_update_error');
    msgDiv.classList.remove('text-success');
    msgDiv.classList.add('text-danger');
  }
});

// Handler de gravaÃ§Ã£o do perfil (envia campos editÃ¡veis)
document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('profileForm');
  if (!form) return;
  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const payload = {};
    for (const name of (window.camposEditaveis || camposEditaveis)) {
      const el = form.querySelector(`[name="${name}"]`);
      if (el) payload[name] = el.value;
    }
    const viewModeSelect = document.getElementById('profileViewMode');
    if (viewModeSelect) {
      payload.VIEWMODE = normalizeViewMode(viewModeSelect.value);
      applyThemeFromViewMode(payload.VIEWMODE);
    }
    const msg = document.getElementById('profileMsg');
    try {
      const resp = await fetch('/api/profile/save', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      if (resp.ok) {
        msg.textContent = tr('profile.saved');
        msg.classList.remove('text-danger');
        msg.classList.add('text-success');
      } else {
        const err = await resp.json().catch(()=>({error: tr('common.error')}));
        msg.textContent = (err && err.error) ? err.error : tr('profile.save_error');
        msg.classList.remove('text-success');
        msg.classList.add('text-danger');
      }
    } catch (err) {
      msg.textContent = tr('profile.network_save_error');
      msg.classList.remove('text-success');
      msg.classList.add('text-danger');
    }
  });
});

// Upload de foto (form no topo do perfil)
document.addEventListener('DOMContentLoaded', () => {
  const uploadForm = document.getElementById('photoUploadForm');
  if (!uploadForm) return;
  uploadForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const fileInput = document.getElementById('photoInput');
    if (!fileInput || !fileInput.files || !fileInput.files[0]) return;
    const fd = new FormData();
    fd.append('photo', fileInput.files[0]);
    try {
      const resp = await fetch('/api/profile/upload_photo', { method: 'POST', body: fd });
      if (!resp.ok) throw new Error(tr('profile.upload_failed'));
      const data = await resp.json();
      const newPath = data.path; // relativo a /static
      const preview = document.getElementById('profilePhotoPreview');
      if (preview) preview.src = `/static/${newPath}`;
      let headerImg = document.getElementById('headerUserPhoto');
      const headerIcon = document.getElementById('headerUserIcon');
      if (!headerImg) {
        const btn = document.getElementById('userMenuToggle');
        if (btn) {
          headerImg = document.createElement('img');
          headerImg.id = 'headerUserPhoto';
          headerImg.style.width = '40px';
          headerImg.style.height = '40px';
          headerImg.style.objectFit = 'cover';
          btn.innerHTML = '';
          btn.appendChild(headerImg);
        }
      }
      if (headerImg) {
        headerImg.src = `/static/${newPath}`;
        headerImg.style.display = 'block';
      }
      if (headerIcon) headerIcon.style.display = 'none';
    } catch (err) {
      console.error(err);
      alert(tr('profile.photo_load_error'));
    }
  });
});

// Click no botÃ£o e upload no change
document.addEventListener('DOMContentLoaded', () => {
  const trigger = document.getElementById('btnUploadPhoto');
  const input = document.getElementById('photoInput');
  if (!trigger || !input) return;
  trigger.addEventListener('click', () => input.click());
  input.addEventListener('change', async () => {
    if (!input.files || !input.files[0]) return;
    const fd = new FormData();
    fd.append('photo', input.files[0]);
    try {
      const resp = await fetch('/api/profile/upload_photo', { method: 'POST', body: fd });
      if (!resp.ok) throw new Error(tr('profile.upload_failed'));
      const data = await resp.json();
      const newPath = data.path;
      const preview = document.getElementById('profilePhotoPreview');
      if (preview) preview.src = `/static/${newPath}`;
      let headerImg = document.getElementById('headerUserPhoto');
      const headerIcon = document.getElementById('headerUserIcon');
      if (!headerImg) {
        const btn = document.getElementById('userMenuToggle');
        if (btn) {
          headerImg = document.createElement('img');
          headerImg.id = 'headerUserPhoto';
          headerImg.style.width = '40px';
          headerImg.style.height = '40px';
          headerImg.style.objectFit = 'cover';
          btn.innerHTML = '';
          btn.appendChild(headerImg);
        }
      }
      if (headerImg) {
        headerImg.src = `/static/${newPath}`;
        headerImg.style.display = 'block';
      }
      if (headerIcon) headerIcon.style.display = 'none';
    } catch (err) {
      console.error(err);
      alert(tr('profile.photo_load_error'));
    } finally {
      input.value = '';
    }
  });
});

