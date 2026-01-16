// static/js/turnover.js

document.addEventListener('DOMContentLoaded', () => {
  const dateInput = document.getElementById('turnDate');
  const btnPrev = document.getElementById('turnPrev');
  const btnNext = document.getElementById('turnNext');
  const cardsWrap = document.getElementById('turnCards');
  const infoEl = document.getElementById('turnInfo');
  const modalEl = document.getElementById('checkinModal');
  const modalTitle = document.getElementById('turnCheckinTitle');
  const fieldPresencial = document.getElementById('turnPresencial');
  const fieldSef = document.getElementById('turnSef');
  const labelSefUser = document.getElementById('turnSefUser');
  const fieldInstr = document.getElementById('turnInstr');
  const labelInstrUser = document.getElementById('turnInstrUser');
  const fieldUser = document.getElementById('turnUser');
  const fieldEntro = document.getElementById('turnEntro');
  const btnSaveCheckin = document.getElementById('turnSaveCheckin');
  const msgErr = document.getElementById('turnCheckinErr');
  const modal = (() => {
    if (!modalEl) return null;
    if (window.bootstrap && window.bootstrap.Modal) {
      return new bootstrap.Modal(modalEl);
    }
    // Fallback modal controller if bootstrap not on window (minimal)
    return {
      show() {
        modalEl.classList.add('show', 'd-block');
        modalEl.removeAttribute('aria-hidden');
      },
      hide() {
        modalEl.classList.remove('show', 'd-block');
        modalEl.setAttribute('aria-hidden', 'true');
      }
    };
  })();
  let currentAloj = '';

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
    if (val.includes('atras')) return 'atrasada';
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
      const atrasA = statusClass(a.status || '') === 'atrasada';
      const atrasB = statusClass(b.status || '') === 'atrasada';
      if (atrasA && !atrasB) return -1;
      if (!atrasA && atrasB) return 1;

      const doneA = !!a.entrou;
      const doneB = !!b.entrou;
      if (doneA && !doneB) return 1;
      if (!doneA && doneB) return -1;

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
      const status = c.status || 'Já limpo';
      const statusCls = statusClass(status);
      const lastInfo = Boolean(c.last_info);
      const equipa = c.equipa || 'Sem limpeza';
      const horaIni = c.hora_lp ? fmtTime(c.hora_lp) : '';
      const horaFim = c.hora_fim ? fmtTime(c.hora_fim) : '';
      const horaTexto = horaIni
        ? (horaFim ? `${horaIni} - ${horaFim}` : horaIni)
        : (horaFim ? horaFim : '');
      let obs = c.obs || '';
      const obsLower = obs.trim().toLowerCase();
      if (obsLower === 'sofá-cama' || obsLower === 'sofa-cama') {
        obs = '';
      }
      const pax = fmtGuests(c.hospedes);
      const nts = fmtNoites(c.noites);
      const sefBadge = c.sef
        ? '<span class="turn-pill turn-pill-ok">SEF</span>'
        : '<span class="turn-pill turn-pill-warn">SEF</span>';
      const instrBadge = c.instr
        ? '<span class="turn-pill turn-pill-ok"><i class="fa-solid fa-images"></i></span>'
        : '<span class="turn-pill turn-pill-warn"><i class="fa-solid fa-images"></i></span>';
      const usrCheck = c.usrcheckin_nome || c.usrcheckin || '';
      const pres = !!c.presencial;
      const presencialBadge = pres || usrCheck
        ? `<span class="turn-pill ${pres ? 'turn-pill-pres' : 'turn-pill-pres-off'}"><i class="fa-solid ${pres ? 'fa-user' : 'fa-user-slash'}"></i>${usrCheck ? ' ' + escapeHtml(usrCheck) : ''}</span>`
        : '';
      const extra = [];
      const hasOut = Boolean(c.has_check_out);
      const hasIn = Boolean(c.has_check_in);
      const outText = hasOut ? fmtTime(c.check_out) : '';
      const inText = hasIn ? fmtTime(c.check_in) : '';
      const entrou = !!c.entrou;
      const inClass = hasIn ? (entrou ? ' done' : '') : ' muted';
      const headerClass = statusCls === 'atrasada' ? ' delayed' : '';
      const fallbackOut = c.fallback_out || null;
      const fallbackIn = c.fallback_in || null;
      const outHtml = fallbackOut
        ? `<div class="dow">${escapeHtml(fallbackOut.dow || '')}</div><div class="date">${escapeHtml(fallbackOut.date || '')}</div>`
        : escapeHtml(outText);
      const inHtml = fallbackIn
        ? (fallbackIn.text ? `<div class="dow">${escapeHtml(fallbackIn.text)}</div>` : `<div class="dow">${escapeHtml(fallbackIn.dow || '')}</div><div class="date">${escapeHtml(fallbackIn.date || '')}</div>`)
        : escapeHtml(inText);
      return `
        <div class="turn-card" data-aloj="${escapeHtml(c.alojamento || '')}">
          <div class="card-header${headerClass}">
            <span>${escapeHtml(c.alojamento || '')}</span>
            <span class="turn-status ${statusCls}">${escapeHtml(status)}</span>
          </div>
          <div class="card-body">
            <div class="turn-block out ${hasOut ? '' : 'muted'}">
              <div class="label">&nbsp;</div>
              <div class="time">${outHtml}</div>
            </div>
            <div class="turn-middle">
              <div><span class="${lastInfo ? 'text-muted fst-italic' : ''}"><strong>${escapeHtml(equipa)}</strong></span>${horaTexto ? ' &middot; <span class="turn-hours">' + escapeHtml(horaTexto) + '</span>' : ''}</div>
              <div class="d-flex align-items-center gap-2 flex-wrap">
                <span class="turn-pill">${escapeHtml(nts)}</span>
                <span class="turn-pill">${escapeHtml(pax)}</span>
                ${sefBadge}
                ${instrBadge}
                ${presencialBadge}
                ${extra.map(e => `<span class="turn-pill">${escapeHtml(e)}</span>`).join('')}
              </div>
              <div class="text-muted small">${escapeHtml(obs)}</div>
            </div>
            <div class="turn-block in${inClass}">
              <div class="label">${entrou ? '<i class="fa-solid fa-check"></i>' : '&nbsp;'}</div>
              <div class="time">${inHtml}</div>
            </div>
          </div>
        </div>
      `;
    }).join('');
  }

  async function openCheckinModal(aloj) {
    currentAloj = aloj;
    const d = dateInput.value || new Date().toISOString().slice(0, 10);
    if (modalTitle) modalTitle.textContent = `Check-in · ${aloj}`;
    if (msgErr) { msgErr.classList.add('d-none'); msgErr.textContent = ''; }
    btnSaveCheckin?.setAttribute('disabled', 'disabled');
    modal?.show();
    try {
      const res = await fetch(`/api/turnover/checkin?data=${encodeURIComponent(d)}&alojamento=${encodeURIComponent(aloj)}`);
      const data = await res.json();
      if (!res.ok || data.error) throw new Error(data.error || 'Erro ao carregar');
      const users = data.users || [];
      if (fieldUser) {
        fieldUser.innerHTML = '<option value=\"\">(sem responsável)</option>' +
          users.map(u => `<option value=\"${escapeHtml(u.value)}\">${escapeHtml(u.label)}</option>`).join('');
      }
      const info = data.data || {};
      if (fieldSef) fieldSef.checked = !!info.sef;
      if (labelSefUser) {
        const usrsef = info.usrsef || '';
        if (info.sef && usrsef) {
          labelSefUser.textContent = `Marcado por ${usrsef}`;
          labelSefUser.classList.remove('d-none');
        } else {
          labelSefUser.textContent = '';
          labelSefUser.classList.add('d-none');
        }
      }
      if (fieldInstr) fieldInstr.checked = !!info.instr;
      if (labelInstrUser) {
        const uinstr = info.usrinstr || '';
        if (info.instr && uinstr) {
          labelInstrUser.textContent = `Enviado por ${uinstr}`;
          labelInstrUser.classList.remove('d-none');
        } else {
          labelInstrUser.textContent = '';
          labelInstrUser.classList.add('d-none');
        }
      }
      if (fieldPresencial) fieldPresencial.checked = !!info.presencial;
      if (fieldEntro) fieldEntro.checked = !!info.entrou;
      if (fieldUser) fieldUser.value = info.usrcheckin || '';
      btnSaveCheckin?.removeAttribute('disabled');
    } catch (err) {
      console.error(err);
      if (msgErr) {
        msgErr.textContent = err.message || 'Erro';
        msgErr.classList.remove('d-none');
      }
    }
  }

  async function saveCheckin() {
    if (!currentAloj) return;
    const d = dateInput.value || new Date().toISOString().slice(0, 10);
    const payload = {
      alojamento: currentAloj,
      data: d,
      sef: fieldSef?.checked || false,
      instr: fieldInstr?.checked || false,
      presencial: fieldPresencial?.checked || false,
      entrou: fieldEntro?.checked || false,
      usrcheckin: fieldUser?.value || ''
    };
    try {
      btnSaveCheckin?.setAttribute('disabled', 'disabled');
      const res = await fetch('/api/turnover/checkin', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      if (!res.ok || data.error) throw new Error(data.error || 'Erro ao gravar');
      modal?.hide();
      loadData();
    } catch (err) {
      console.error(err);
      if (msgErr) {
        msgErr.textContent = err.message || 'Erro';
        msgErr.classList.remove('d-none');
      }
    } finally {
      btnSaveCheckin?.removeAttribute('disabled');
    }
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

  cardsWrap?.addEventListener('click', (ev) => {
    const block = ev.target.closest('.turn-block.in');
    if (!block || block.classList.contains('muted')) return;
    const card = block.closest('.turn-card');
    const aloj = card?.dataset?.aloj;
    if (aloj) {
      openCheckinModal(aloj);
    }
  });

  btnPrev?.addEventListener('click', () => changeDate(-1));
  btnNext?.addEventListener('click', () => changeDate(1));
  dateInput.addEventListener('change', loadData);
  btnSaveCheckin?.addEventListener('click', saveCheckin);

  if (!dateInput.value) {
    dateInput.value = window.TURNOVER_TODAY || new Date().toISOString().slice(0, 10);
  }
  loadData();
});
