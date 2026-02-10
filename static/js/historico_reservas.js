// static/js/historico_reservas.js

document.addEventListener('DOMContentLoaded', () => {
  const grid = document.getElementById('histGrid');
  const dateInput = document.getElementById('histDate');
  const btnPrev = document.getElementById('histPrev');
  const btnNext = document.getElementById('histNext');
  const infoEl = document.getElementById('histInfo');
  const userSelect = document.getElementById('histUser');

  const escapeHtml = (s) => (s ?? '').toString()
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#039;');

  function statusFor(t) {
    const ini = (t.HORAINI || '').trim();
    const fim = (t.HORAFIM || '').trim();
    const tratado = !!t.TRATADO;
    if (fim) return { key: 'done', label: 'Conclu&iacute;da' };
    if (ini && !fim) return { key: 'run', label: 'Em curso' };
    if (tratado) return { key: 'done', label: 'Conclu&iacute;da' };
    return { key: 'todo', label: 'Planeada' };
  }

  function tipologiaMinutes(tip) {
    const v = (tip || '').toString().trim().toUpperCase();
    if (v === 'T0' || v === 'T1') return 60;
    if (v === 'T2') return 90;
    if (v === 'T3') return 120;
    if (v === 'T4') return 150;
    return null;
  }

  function timeToMin(hhmm) {
    const m = /^(\d{1,2}):(\d{2})$/.exec((hhmm || '').trim());
    if (!m) return null;
    const h = Math.min(23, Math.max(0, Number(m[1])));
    const mm = Math.min(59, Math.max(0, Number(m[2])));
    return h * 60 + mm;
  }

  function minToTime(min) {
    if (min == null || !isFinite(min)) return '';
    let m = Math.round(min);
    if (m < 0) m = 0;
    m = m % (24 * 60);
    const h = Math.floor(m / 60);
    const mm = m % 60;
    return `${String(h).padStart(2, '0')}:${String(mm).padStart(2, '0')}`;
  }

  function render(rows) {
    if (!grid) return;
    if (!rows.length) {
      grid.innerHTML = '<div class="text-muted">Sem tarefas para este dia.</div>';
      return;
    }
    const sorted = [...rows].sort((a, b) => {
      const am = timeToMin(a.HORAINI) ?? timeToMin(a.HORA) ?? 0;
      const bm = timeToMin(b.HORAINI) ?? timeToMin(b.HORA) ?? 0;
      if (am !== bm) return am - bm;
      return String(a.ALOJAMENTO || '').localeCompare(String(b.ALOJAMENTO || ''), 'pt', { sensitivity: 'base' });
    });

    const parts = [];
    let prevEndMin = null;
    let prevPlanEndMin = null;
    sorted.forEach((t, idx) => {
      const alo = (t.ALOJAMENTO || '').toString();
      const hora = (t.HORA || '').toString();
      const horaini = (t.HORAINI || '').toString().trim();
      const horafim = (t.HORAFIM || '').toString().trim();
      const st = statusFor(t);
      const id = (t.TAREFASSTAMP || '').toString().trim();
      const mins = tipologiaMinutes(t.TIPOLOGIA);
      const planStartMin = timeToMin(hora);
      const planEndMin = (planStartMin != null && mins != null) ? (planStartMin + mins) : null;
      const planEnd = (planEndMin != null) ? minToTime(planEndMin) : '';
      const planLabel = (planStartMin != null && mins != null)
        ? `${minToTime(planStartMin)} - ${planEnd} (${mins}m)`
        : (hora || '--:--');

      const startMin = timeToMin(horaini);
      const endMin = timeToMin(horafim);
      const dur = (startMin != null && endMin != null) ? Math.max(0, endMin - startMin) : null;
      const realLabel = `${horaini || '--:--'} - ${horafim || '--:--'}${dur != null ? ` (${dur}m)` : ''}`;
      let realClass = '';
      if (dur != null && mins != null) {
        realClass = dur > mins ? 'bad' : 'good';
      }

      if (idx > 0 && prevEndMin != null && startMin != null) {
        const gapReal = Math.max(0, startMin - prevEndMin);
        let gapPlan = null;
        if (prevPlanEndMin != null && planStartMin != null) {
          gapPlan = Math.max(0, planStartMin - prevPlanEndMin);
        }
        const gapClass = (gapPlan != null) ? (gapReal > gapPlan ? 'bad' : 'good') : '';
        const prevTxt = (gapPlan != null) ? `(${gapPlan}m)` : '(--m)';
        parts.push(`<div class="tcard-gap ${gapClass}">${prevTxt} ${gapReal}m</div>`);
      }

      if (endMin != null) prevEndMin = endMin;
      if (planEndMin != null) prevPlanEndMin = planEndMin;

      parts.push(`
        <div class="tcard" data-id="${escapeHtml(id)}">
          <div class="tcard-head">
            <div class="tcard-title">
              <div class="tcard-alo" title="${escapeHtml(alo)}">${escapeHtml(alo || '(sem alojamento)')}</div>
              <div class="tcard-time">${escapeHtml(planLabel)}</div>
            </div>
          </div>
          <div class="tcard-body">
            <div class="tcard-meta">
              <span class="tbadge ${st.key}">${st.label}</span>
              <span class="tbadge real ${realClass}">${escapeHtml(realLabel)}</span>
            </div>
          </div>
          <div class="tcard-anexos js-anexos">
            <div class="anx-empty">A carregar anexos...</div>
          </div>
        </div>
      `);
    });
    grid.innerHTML = parts.join('');
  }

  async function loadAnexosForTask(tid) {
    const id = (tid || '').toString().trim();
    if (!id) return [];
    const res = await fetch(`/api/anexos?table=TAREFAS&rec=${encodeURIComponent(id)}`);
    if (!res.ok) throw new Error('Falha ao carregar anexos.');
    const arr = await res.json().catch(() => ([]));
    return Array.isArray(arr) ? arr : [];
  }

  function isImg(ext) {
    return /^(png|jpg|jpeg|gif|webp)$/i.test(String(ext || ''));
  }
  function isVid(ext) {
    return /^(mp4|webm|ogg|mov|m4v)$/i.test(String(ext || ''));
  }

  function renderAnexosIntoCard(tid, rows) {
    const id = (tid || '').toString().trim();
    const esc = (window.CSS && typeof window.CSS.escape === 'function')
      ? window.CSS.escape
      : (v) => String(v || '').replace(/["\\]/g, '\\$&');
    const card = grid?.querySelector?.(`.tcard[data-id="${esc(id)}"]`);
    if (!card) return;
    const cont = card.querySelector('.js-anexos');
    if (!cont) return;
    if (!rows || !rows.length) {
      cont.innerHTML = '<div class="anx-empty">Sem anexos.</div>';
      return;
    }
    cont.innerHTML = rows.map(a => {
      const url = (a.CAMINHO || '').toString().trim();
      const typ = (a.TIPO || '').toString().trim();
      const name = (a.FICHEIRO || '').toString().trim();
      let media = `<div class="d-flex align-items-center justify-content-center h-100 text-muted"><i class="fa-regular fa-file-lines fa-lg"></i></div>`;
      if (url && isImg(typ)) media = `<img src="${escapeHtml(url)}" alt="">`;
      else if (url && isVid(typ)) media = `<video src="${escapeHtml(url)}" muted playsinline></video>`;
      const href = url ? `href="${escapeHtml(url)}" target="_blank" rel="noopener"` : '';
      return `
        <div class="anx" title="${escapeHtml(name || typ)}">
          <a ${href} class="d-block h-100 w-100" style="text-decoration:none; color:inherit;">
            ${media}
          </a>
        </div>
      `;
    }).join('');
  }

  async function load() {
    if (!grid) return;
    const d = (dateInput?.value || '').trim();
    grid.innerHTML = '<div class="text-muted">A carregar...</div>';
    const u = (userSelect?.value || '').trim();
    const qs = new URLSearchParams();
    qs.set('data', d);
    if (u) qs.set('user', u);
    const res = await fetch(`/api/historico_reservas?${qs.toString()}`);
    const data = await res.json().catch(() => ({}));
    if (!res.ok || data.error) {
      grid.innerHTML = `<div class="text-danger">Erro: ${escapeHtml(data.error || res.statusText)}</div>`;
      return;
    }
    if (infoEl) infoEl.textContent = `${data.count || 0} tarefa(s)`;
    const rows = Array.isArray(data.rows) ? data.rows : [];
    render(rows);
    await Promise.all(rows.map(async (t) => {
      const id = (t.TAREFASSTAMP || '').toString().trim();
      if (!id) return;
      try {
        const anexos = await loadAnexosForTask(id);
        renderAnexosIntoCard(id, anexos);
      } catch (_) {
        renderAnexosIntoCard(id, []);
      }
    }));
  }

  function setDate(d) {
    if (!dateInput) return;
    const iso = d.toISOString().slice(0, 10);
    dateInput.value = iso;
    load();
  }

  const today = new Date();
  today.setHours(0, 0, 0, 0);
  if (dateInput) dateInput.value = today.toISOString().slice(0, 10);

  btnPrev?.addEventListener('click', () => {
    const d = new Date(dateInput.value + 'T00:00:00');
    d.setDate(d.getDate() - 1);
    setDate(d);
  });
  btnNext?.addEventListener('click', () => {
    const d = new Date(dateInput.value + 'T00:00:00');
    d.setDate(d.getDate() + 1);
    setDate(d);
  });
  dateInput?.addEventListener('change', load);
  userSelect?.addEventListener('change', load);

  async function loadUsers() {
    if (!userSelect) return;
    const res = await fetch('/api/historico_reservas_users');
    const data = await res.json().catch(() => ({}));
    const users = Array.isArray(data.users) ? data.users : [];
    userSelect.innerHTML = '<option value="">Utilizador...</option>' + users
      .map(u => `<option value="${escapeHtml(u.login)}">${escapeHtml(u.nome || u.login)}</option>`)
      .join('');
    if (users.length && window.currentLogin) {
      userSelect.value = String(window.currentLogin);
    }
  }

  loadUsers().finally(load);
});
