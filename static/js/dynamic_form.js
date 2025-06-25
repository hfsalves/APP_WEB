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
          el.value = val ? val.slice(0,10) : '';
        } else {
          el.value = val;
        }
      });
    } catch (e) {
      console.error('Erro ao carregar registro:', e);
    }
  } else {
    document.getElementById('btnDelete')?.style.setProperty('display','none');
  }

  // 5. Inicializa Flatpickr
  if (window.flatpickr) {
    form.querySelectorAll('.flatpickr-date').forEach(el =>
      flatpickr(el, { dateFormat:'d.m.Y', allowInput:true, defaultDate: el.value || null })
    );
  }

  // 6. Cancelar e eliminar
  document.getElementById('btnCancel')?.addEventListener('click', () => {
    location = `/generic/view/${TABLE_NAME}/`;
  });
  document.getElementById('btnDelete')?.addEventListener('click', async () => {
    if (!confirm('Confirmar eliminação?')) return;
    await fetch(`/generic/api/${TABLE_NAME}/${RECORD_STAMP}`, { method:'DELETE' });
    location = `/generic/view/${TABLE_NAME}/`;
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
      location = `/generic/view/${TABLE_NAME}/`;
    } catch (net) {
      alert(`Erro de rede: ${net.message}`);
    }
  });

  // 8. Cursor no final
  form.querySelectorAll('input[type="text"],input[type="number"],input[type="time"]').forEach(i =>
    i.addEventListener('focus', () => { const v = i.value; i.value = ''; i.value = v; })
  );
})();
