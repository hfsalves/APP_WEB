// static/js/turnover.js

document.addEventListener('DOMContentLoaded', () => {
  const dateInput = document.getElementById('turnDate');
  const btnPrev = document.getElementById('turnPrev');
  const btnNext = document.getElementById('turnNext');
  const cardsWrap = document.getElementById('turnCards');
  const infoEl = document.getElementById('turnInfo');

  if (!dateInput) return;

  const fmtTime = (t) => {
    const s = String(t == null ? '' : t).trim();
    if (!s) return 'N/D';
    const m = s.match(/^(\d{1,2}):(\d{2})$/);
    if (m) return `${m[1].padStart(2, '0')}:${m[2]}`;
    const digits = s.replace(/\D/g, '');
    if (!digits) return 'N/D';
    if (digits.length >= 3) {
      const mins = digits.slice(-2);
      const hours = digits.slice(0, -2).padStart(2, '0');
      return `${hours}:${mins}`;
    }
    return `${digits.padStart(2, '0')}:00`;
  };

  const fmtGuests = (n) => `${Number(n || 0)}P`;
  const fmtNoites = (n) => `${Number(n || 0)}N`;

  async function loadData() {
    const d = dateInput.value || new Date().toISOString().slice(0, 10);
    try {
      const res = await fetch(`/api/turnover?data=${encodeURIComponent(d)}`);
      const text = await res.text();
      let data;
      try {
        data = JSON.parse(text);
      } catch (_) {
        throw new Error(text || 'Resposta invalida do servidor');
      }
      if (!res.ok || data.error) throw new Error(data.error || 'Erro ao carregar dados');
      renderCards(data.cards || []);
      if (infoEl) infoEl.textContent = `Total alojamentos: ${data.cards ? data.cards.length : 0}`;
    } catch (err) {
      console.error(err);
      if (cardsWrap) cardsWrap.innerHTML = `<div class="text-danger">${escapeHtml(err.message || 'Erro')}</div>`;
    }
  }

  function statusClass(s) {
    const val = (s || '').toLowerCase();
    if (val.includes('plane')) return 'planeada';
    if (val.includes('conclu')) return 'concluida';
    return 'sem';
  }

  function toMinutes(hhmm) {
    const s = String(hhmm || '').trim();
    if (!s) return null;
    const m = s.match(/^(\d{1,2}):(\d{2})$/);
    if (m) return parseInt(m[1], 10) * 60 + parseInt(m[2], 10);
    const digits = s.replace(/\D/g, '');
    if (digits.length >= 3) {
      const mins = parseInt(digits.slice(-2), 10);
      const hours = parseInt(digits.slice(0, -2), 10);
      return hours * 60 + mins;
    }
    if (digits) return parseInt(digits, 10) * 60;
    return null;
  }

  function renderCards(list) {
    if (!cardsWrap) return;
    if (!list.length) {
      cardsWrap.innerHTML = '<div class="text-muted">Sem alojamentos para este dia.</div>';
      return;
    }

    const sorted = list.slice().sort((a, b) => {
      const hasA = !!a.has_check_in;
      const hasB = !!b.has_check_in;
      if (hasA && !hasB) return -1;
      if (!hasA && hasB) return 1;
      const tA = hasA ? toMinutes(a.check_in) : null;
      const tB = hasB ? toMinutes(b.check_in) : null;
      const scoreA = hasA ? (tA === null ? 0 : 1) : 2;
      const scoreB = hasB ? (tB === null ? 0 : 1) : 2;
      if (scoreA !== scoreB) return scoreA - scoreB;
      if (scoreA === 2) return (a.alojamento || '').localeCompare(b.alojamento || '', 'pt-PT');
      if (scoreA === 0 && scoreB === 0) return (a.alojamento || '').localeCompare(b.alojamento || '', 'pt-PT');
      return (tA || 0) - (tB || 0) || (a.alojamento || '').localeCompare(b.alojamento || '', 'pt-PT');
    });

    cardsWrap.innerHTML = sorted.map(c => {
      const status = c.status || 'Sem limpeza';
      const statusCls = statusClass(status);
      const equipa = c.equipa || '—';
      let obs = c.obs || '';
      if (obs.trim().toLowerCase() === 'sofá-cama' || obs.trim().toLowerCase() === 'sofa-cama') {
        obs = '';
      }
      const pax = fmtGuests(c.hospedes);
      const nts = fmtNoites(c.noites);
      const extra = [];
      // berço e sofá-cama não são mostrados na UI
      const hasOut = Boolean(c.has_check_out);
      const hasIn = Boolean(c.has_check_in);
      const outText = hasOut ? fmtTime(c.check_out) : '';
      const inText = hasIn ? fmtTime(c.check_in) : '';
      return `
        <div class="turn-card">
          <div class="card-header">
            <span>${escapeHtml(c.alojamento || '')}</span>
            <span class="turn-status ${statusCls}">${escapeHtml(status)}</span>
          </div>
          <div class="card-body">
            <div class="turn-block out ${hasOut ? '' : 'muted'}">
              <div class="label">&nbsp;</div>
              <div class="time">${escapeHtml(outText)}</div>
            </div>
            <div class="turn-middle">
              <div><strong>${escapeHtml(equipa)}</strong></div>
              <div class="d-flex align-items-center gap-2 flex-wrap">
                <span class="turn-pill">${escapeHtml(nts)}</span>
                <span class="turn-pill">${escapeHtml(pax)}</span>
                ${extra.map(e => `<span class="turn-pill">${escapeHtml(e)}</span>`).join('')}
              </div>
              <div class="text-muted small">${escapeHtml(obs)}</div>
            </div>
            <div class="turn-block in ${hasIn ? '' : 'muted'}">
              <div class="label">&nbsp;</div>
              <div class="time">${escapeHtml(inText)}</div>
            </div>
          </div>
        </div>
      `;
    }).join('');
  }

  function escapeHtml(str) {
    return String(str == null ? '' : str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function changeDate(delta) {
    try {
      const base = dateInput.value ? new Date(dateInput.value) : new Date();
      base.setDate(base.getDate() + delta);
      dateInput.value = base.toISOString().slice(0, 10);
      loadData();
    } catch (err) {
      console.error(err);
    }
  }

  btnPrev?.addEventListener('click', () => changeDate(-1));
  btnNext?.addEventListener('click', () => changeDate(1));
  dateInput.addEventListener('change', loadData);

  if (!dateInput.value) {
    dateInput.value = window.TURNOVER_TODAY || new Date().toISOString().slice(0, 10);
  }
  loadData();
});
