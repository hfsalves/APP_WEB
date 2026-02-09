// static/js/historico_reservas.js

document.addEventListener('DOMContentLoaded', () => {
  const grid = document.getElementById('histGrid');
  const dateInput = document.getElementById('histDate');
  const btnPrev = document.getElementById('histPrev');
  const btnNext = document.getElementById('histNext');
  const infoEl = document.getElementById('histInfo');

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
    if (fim) return { key: 'done', label: `Conclu&iacute;da ${escapeHtml(ini)} - ${escapeHtml(fim)}` };
    if (ini && !fim) return { key: 'run', label: `Em execu&ccedil;&atilde;o desde ${escapeHtml(ini)}` };
    if (tratado) return { key: 'done', label: 'Conclu&iacute;da' };
    return { key: 'todo', label: 'Por iniciar' };
  }

  function render(rows) {
    if (!grid) return;
    if (!rows.length) {
      grid.innerHTML = '<div class="text-muted">Sem tarefas para este dia.</div>';
      return;
    }
    grid.innerHTML = rows.map(t => {
      const alo = (t.ALOJAMENTO || '').toString();
      const hora = (t.HORA || '').toString();
      const tarefa = (t.TAREFA || '').toString();
      const st = statusFor(t);
      const id = (t.TAREFASSTAMP || '').toString().trim();
      return `
        <div class="tcard" data-id="${escapeHtml(id)}">
          <div class="tcard-head">
            <div class="tcard-title">
              <div class="tcard-alo" title="${escapeHtml(alo)}">${escapeHtml(alo || '(sem alojamento)')}</div>
              <div class="tcard-time">${escapeHtml(hora || '--:--')}</div>
            </div>
          </div>
          <div class="tcard-body">
            <div class="tcard-sub" title="${escapeHtml(tarefa)}">${escapeHtml(tarefa || 'Limpeza')}</div>
            <div class="tcard-meta">
              <span class="tbadge ${st.key}">${st.label}</span>
            </div>
          </div>
          <div class="tcard-anexos js-anexos">
            <div class="anx-empty">A carregar anexos...</div>
          </div>
        </div>
      `;
    }).join('');
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
    const res = await fetch(`/api/historico_reservas?data=${encodeURIComponent(d)}`);
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

  load();
});
