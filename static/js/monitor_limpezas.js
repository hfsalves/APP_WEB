(function () {
  const REFRESH_MS = 45000;
  const MAX_ROWS = 11;

  const $ = (id) => document.getElementById(id);
  const board = $('cleaningBoard');

  function escapeHtml(value) {
    return String(value == null ? '' : value)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function formatDateLabel(value) {
    const raw = String(value || '').slice(0, 10);
    const match = raw.match(/^(\d{4})-(\d{2})-(\d{2})$/);
    if (!match) return 'Hoje';
    const d = new Date(Number(match[1]), Number(match[2]) - 1, Number(match[3]));
    return d.toLocaleDateString('pt-PT', {
      weekday: 'long',
      day: '2-digit',
      month: 'long'
    });
  }

  function timeLabel(value, fallback) {
    const raw = String(value || '').trim();
    const match = raw.match(/^(\d{1,2}):(\d{2})/);
    if (match) return `${match[1].padStart(2, '0')}:${match[2]}`;
    return fallback || '--:--';
  }

  function updateClock() {
    const now = new Date();
    const clock = $('opsClock');
    const date = $('opsClockDate');
    if (clock) {
      clock.textContent = now.toLocaleTimeString('pt-PT', {
        hour: '2-digit',
        minute: '2-digit'
      });
    }
    if (date) {
      date.textContent = now.toLocaleDateString('pt-PT', {
        weekday: 'short',
        day: '2-digit',
        month: '2-digit'
      });
    }
  }

  function setText(id, value) {
    const el = $(id);
    if (el) el.textContent = value;
  }

  function renderNext(item) {
    const card = $('nextCard');
    if (!card) return;
    if (!item) {
      card.innerHTML = `
        <div class="next-kicker">Proxima limpeza</div>
        <div class="next-time">--:--</div>
        <div class="next-name">Sem limpezas pendentes</div>
        <div class="next-meta">Tudo o que existe para hoje esta fechado.</div>
      `;
      return;
    }
    const status = item.status || {};
    card.innerHTML = `
      <div class="next-kicker">${escapeHtml(status.label || 'Proxima limpeza')}</div>
      <div class="next-time">${escapeHtml(timeLabel(item.time))}</div>
      <div class="next-name">${escapeHtml(item.lodging || '-')}</div>
      <div class="next-meta">
        ${escapeHtml(item.team || 'Sem equipa')}<br>
        ${escapeHtml(item.duration_label || '')}${item.end_time ? ` ate ${escapeHtml(item.end_time)}` : ''}
      </div>
    `;
  }

  function rowHtml(item) {
    const status = item.status || {};
    const tone = status.tone || 'quiet';
    const windowBits = [];
    if (item.checkout_time) windowBits.push(`out ${timeLabel(item.checkout_time, '')}`);
    if (item.checkin_time) windowBits.push(`in ${timeLabel(item.checkin_time, '')}`);
    const extraBits = [item.typology, item.zone, item.duration_label].filter(Boolean);
    const peopleBits = [];
    if (item.guests) peopleBits.push(`${item.guests} hosp.`);
    if (item.nights) peopleBits.push(`${item.nights} noites`);
    return `
      <article class="cleaning-row" data-tone="${escapeHtml(tone)}">
        <div>
          <div class="time-block">${escapeHtml(timeLabel(item.time))}</div>
          <div class="end-time">${item.end_time ? `fim ${escapeHtml(item.end_time)}` : 'fim --:--'}</div>
        </div>
        <div class="place">
          <div class="place-name">${escapeHtml(item.lodging || '-')}</div>
          <div class="place-extra">${escapeHtml(extraBits.join(' · ') || 'Limpeza')}</div>
        </div>
        <div class="team">
          <strong>${escapeHtml(item.team || 'Sem equipa')}</strong>
          ${escapeHtml(peopleBits.join(' · ') || item.notes || '')}
        </div>
        <div class="window">
          <strong>${escapeHtml(windowBits.join(' / ') || '-')}</strong>
          ${escapeHtml(status.detail || '')}
        </div>
        <div>
          <span class="status-pill" data-tone="${escapeHtml(tone)}">
            <i class="${statusIcon(status.key)}"></i>
            <span>${escapeHtml(status.label || '-')}</span>
          </span>
        </div>
      </article>
    `;
  }

  function statusIcon(key) {
    if (key === 'done') return 'fa-solid fa-check';
    if (key === 'running') return 'fa-solid fa-play';
    if (key === 'late' || key === 'late_running') return 'fa-solid fa-triangle-exclamation';
    if (key === 'unassigned') return 'fa-solid fa-user-plus';
    if (key === 'due') return 'fa-solid fa-bell';
    return 'fa-regular fa-clock';
  }

  function sortItems(items) {
    const priority = {
      late: 0,
      late_running: 0,
      due: 1,
      running: 2,
      planned: 3,
      unassigned: 4,
      done: 5
    };
    return (Array.isArray(items) ? items : []).slice().sort((a, b) => {
      const pa = priority[(a.status || {}).key] ?? 9;
      const pb = priority[(b.status || {}).key] ?? 9;
      if (pa !== pb) return pa - pb;
      return String(a.time || '99:99').localeCompare(String(b.time || '99:99'));
    });
  }

  function render(payload) {
    const totals = payload.totals || {};
    const total = Number(totals.total || 0);
    const done = Number(totals.done || 0);
    const running = Number(totals.running || 0);
    const late = Number(totals.late || 0);
    const planned = Number(totals.planned || 0);
    const unassigned = Number(totals.unassigned || 0);
    const open = Math.max(0, total - done);
    const progress = Number(payload.progress || 0);

    setText('monitorDateLabel', formatDateLabel(payload.date));
    setText('progressNumber', `${progress}%`);
    setText('metricTotal', total);
    setText('metricRunning', running);
    setText('metricLate', late);
    setText('metricOpen', open);
    setText('stackLate', late);
    setText('stackRunning', running);
    setText('stackPlanned', planned + unassigned);
    setText('stackDone', done);
    setText('opsRefresh', `Atualizado ${payload.updated_at || '--:--'}`);

    const fill = $('progressFill');
    if (fill) fill.style.width = `${Math.max(0, Math.min(progress, 100))}%`;

    renderNext(payload.next);

    if (!board) return;
    const items = sortItems(payload.items).slice(0, MAX_ROWS);
    if (!items.length) {
      board.innerHTML = '<div class="empty-state">Sem limpezas planeadas para hoje.</div>';
      return;
    }
    board.innerHTML = items.map(rowHtml).join('');
  }

  async function load() {
    try {
      const response = await fetch('/api/monitor/limpezas', {
        headers: { Accept: 'application/json' },
        cache: 'no-store'
      });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok || payload.error) {
        throw new Error(payload.error || response.statusText || 'Erro ao carregar');
      }
      render(payload);
    } catch (err) {
      if (board) {
        board.innerHTML = `<div class="error-state">Sem ligacao ao servidor<br><small>${escapeHtml(err.message || err)}</small></div>`;
      }
      setText('opsRefresh', 'Falha na atualizacao');
    }
  }

  updateClock();
  load();
  setInterval(updateClock, 1000);
  setInterval(load, REFRESH_MS);
})();
