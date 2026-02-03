// static/js/tempos_limpeza.js

document.addEventListener('DOMContentLoaded', () => {
  const grid = document.getElementById('temposGrid');
  const infoCache = new Map(); // TAREFASSTAMP -> html

  // Vídeo
  const videoModalEl = document.getElementById('videoModal');
  const videoModal = videoModalEl ? new bootstrap.Modal(videoModalEl) : null;
  const vidPreview = document.getElementById('vidPreview');
  const vidTimer = document.getElementById('vidTimer');
  const vidStatus = document.getElementById('vidStatus');
  const vidStart = document.getElementById('vidStart');
  const vidStop = document.getElementById('vidStop');
  const vidUpload = document.getElementById('vidUpload');
  const vidPickFile = document.getElementById('vidPickFile');
  const vidFile = document.getElementById('vidFile');

  let currentVideoTaskId = '';
  let mediaStream = null;
  let mediaRecorder = null;
  let recordedBlob = null;
  let recChunks = [];
  let recTimer = null;
  let recSeconds = 0;
  let autoStopTimer = null;

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

  function render(rows, user) {
    if (!grid) return;
    if (!rows.length) {
      grid.innerHTML = '<div class="text-muted">Sem tarefas de limpeza para hoje.</div>';
      return;
    }
    const active = rows.find(r => (r.HORAINI || '').trim() && !(r.HORAFIM || '').trim());
    grid.innerHTML = rows.map(t => {
      const id = (t.TAREFASSTAMP || '').toString();
      const alo = (t.ALOJAMENTO || '').toString();
      const hora = (t.HORA || '').toString();
      const tarefa = (t.TAREFA || '').toString();
      const ini = (t.HORAINI || '').toString().trim();
      const fim = (t.HORAFIM || '').toString().trim();
      const st = statusFor(t);

      const canStart = !ini && !fim;
      const canStop = !!ini && !fim;
      const warnStart = active && canStart ? 'data-warn="1"' : '';

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
          <div class="tcard-actions">
            <button class="btn btn-sm btn-outline-primary btn-info-toggle js-toggle" aria-expanded="false">
              <i class="fa-solid fa-circle-info me-1"></i> Info
            </button>
            ${canStart ? `<button class="btn btn-sm btn-start js-start" ${warnStart}><i class="fa-solid fa-play me-1"></i> Iniciar</button>` : ''}
            ${canStop ? `<button class="btn btn-sm btn-outline-primary js-camera" title="Gravar e enviar vídeo"><i class="fa-solid fa-video me-1"></i> C&acirc;mara</button>` : ''}
            ${canStop ? `<button class="btn btn-sm btn-stop js-stop"><i class="fa-solid fa-stop me-1"></i> Terminar</button>` : ''}
          </div>
          <div class="tcard-detail">
            <div class="tcard-detail-inner js-detail">
              <div class="tcard-detail-loading">A carregar...</div>
            </div>
          </div>
        </div>
      `;
    }).join('');
  }

  async function load() {
    if (!grid) return;
    grid.innerHTML = '<div class="text-muted">A carregar...</div>';
    const res = await fetch('/api/tempos_limpeza/hoje');
    const data = await res.json().catch(() => ({}));
    if (!res.ok || data.error) {
      grid.innerHTML = `<div class="text-danger">Erro: ${escapeHtml(data.error || res.statusText)}</div>`;
      return;
    }
    const rows = Array.isArray(data.rows) ? data.rows : [];
    render(rows, data.user || '');
  }

  function setVidStatus(text) {
    if (vidStatus) vidStatus.textContent = text || '';
  }

  function setTimerText(sec) {
    const s = Math.max(0, Math.min(60, Number(sec || 0) || 0));
    const mm = String(Math.floor(s / 60)).padStart(2, '0');
    const ss = String(s % 60).padStart(2, '0');
    if (vidTimer) vidTimer.textContent = `${mm}:${ss}`;
  }

  function stopStream() {
    try {
      if (mediaStream) {
        mediaStream.getTracks().forEach(t => { try { t.stop(); } catch (_) {} });
      }
    } catch (_) {}
    mediaStream = null;
  }

  function resetRecorderUi() {
    recordedBlob = null;
    recChunks = [];
    recSeconds = 0;
    setTimerText(0);
    if (vidStop) vidStop.disabled = true;
    if (vidStart) vidStart.disabled = false;
    if (vidUpload) vidUpload.disabled = true;
  }

  function stopRecording() {
    try { if (mediaRecorder && mediaRecorder.state !== 'inactive') mediaRecorder.stop(); } catch (_) {}
    mediaRecorder = null;
    clearInterval(recTimer); recTimer = null;
    clearTimeout(autoStopTimer); autoStopTimer = null;
    if (vidStop) vidStop.disabled = true;
    if (vidStart) vidStart.disabled = false;
  }

  async function ensureCameraPreview() {
    if (!vidPreview) return false;
    stopStream();
    resetRecorderUi();
    setVidStatus('');

    const supports = !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia);
    if (!supports) {
      // fallback: upload file
      if (vidPickFile) vidPickFile.style.display = '';
      if (vidFile) vidFile.style.display = '';
      if (vidStart) vidStart.style.display = 'none';
      if (vidStop) vidStop.style.display = 'none';
      setVidStatus('Este dispositivo não suporta câmara no browser. Envie um ficheiro.');
      return false;
    }

    if (vidPickFile) vidPickFile.style.display = 'none';
    if (vidFile) vidFile.style.display = 'none';
    if (vidStart) vidStart.style.display = '';
    if (vidStop) vidStop.style.display = '';

    const constraints = {
      audio: { echoCancellation: true, noiseSuppression: true, channelCount: 1 },
      video: { width: { ideal: 640 }, height: { ideal: 360 }, frameRate: { ideal: 15, max: 24 } }
    };
    mediaStream = await navigator.mediaDevices.getUserMedia(constraints);
    vidPreview.srcObject = mediaStream;
    vidPreview.muted = true;
    try { await vidPreview.play(); } catch (_) {}
    return true;
  }

  function pickMimeType() {
    const types = [
      'video/webm;codecs=vp9,opus',
      'video/webm;codecs=vp8,opus',
      'video/webm'
    ];
    for (const t of types) {
      try { if (window.MediaRecorder && MediaRecorder.isTypeSupported(t)) return t; } catch (_) {}
    }
    return '';
  }

  async function uploadVideo(file) {
    if (!currentVideoTaskId) throw new Error('Tarefa inválida.');
    const fd = new FormData();
    fd.append('table', 'TAREFAS');
    fd.append('rec', currentVideoTaskId);
    fd.append('descricao', 'Vídeo limpeza');
    fd.append('file', file);
    const res = await fetch('/api/anexos/upload', { method: 'POST', body: fd });
    const js = await res.json().catch(() => ({}));
    if (!res.ok || js.error) throw new Error(js.error || res.statusText);
    return js;
  }

  grid?.addEventListener('click', async (e) => {
    const btnToggle = e.target.closest?.('.js-toggle');
    const btnCam = e.target.closest?.('.js-camera');
    const btnStart = e.target.closest?.('.js-start');
    const btnStop = e.target.closest?.('.js-stop');
    const card = e.target.closest?.('.tcard[data-id]');
    const id = (card?.dataset?.id || '').toString().trim();
    if (!id) return;

    if (btnToggle) {
      e.preventDefault();
      e.stopPropagation?.();
      const willOpen = !card.classList.contains('expanded');
      const isOpen = card.classList.toggle('expanded', willOpen);
      const detailEl = card.querySelector('.js-detail');
      if (!detailEl) return;
      btnToggle.setAttribute('aria-expanded', willOpen ? 'true' : 'false');
      btnToggle.classList.toggle('active', willOpen);
      if (!willOpen) return;
      if (detailEl.dataset.loaded === '1') return;

      try {
        const cached = infoCache.get(id);
        if (cached != null) {
          detailEl.innerHTML = cached;
          detailEl.dataset.loaded = '1';
          return;
        }
        detailEl.innerHTML = '<div class="tcard-detail-loading">A carregar...</div>';
        const res = await fetch(`/api/tarefa_info/${encodeURIComponent(id)}`);
        const data = await res.json().catch(() => ({}));
        if (!res.ok || data.error) throw new Error(data.error || res.statusText);
        const html = (data.info || '').toString();
        detailEl.innerHTML = html || '<div class="text-muted">Sem detalhe.</div>';
        detailEl.dataset.loaded = '1';
        infoCache.set(id, detailEl.innerHTML);
      } catch (err) {
        detailEl.innerHTML = `<div class="text-danger">Erro: ${escapeHtml(err?.message || err)}</div>`;
      }
      return;
    }

    if (btnCam) {
      e.preventDefault();
      currentVideoTaskId = id;
      if (!videoModal) return;
      videoModal.show();
      return;
    }

    if (btnStart) {
      if (btnStart.dataset.warn === '1') {
        const ok = confirm('J&aacute; existe uma limpeza iniciada. Queres iniciar esta na mesma?');
        if (!ok) return;
      }
      btnStart.disabled = true;
      try {
        const r = await fetch('/api/tempos_limpeza/start', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ id })
        });
        const js = await r.json().catch(() => ({}));
        if (!r.ok || js.error) throw new Error(js.error || r.statusText);
        await load();
      } catch (err) {
        alert(err?.message || err);
      } finally {
        btnStart.disabled = false;
      }
    }

    if (btnStop) {
      const ok = confirm('Terminar esta limpeza?');
      if (!ok) return;
      btnStop.disabled = true;
      try {
        const r = await fetch('/api/tempos_limpeza/stop', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ id })
        });
        const js = await r.json().catch(() => ({}));
        if (!r.ok || js.error) throw new Error(js.error || r.statusText);
        await load();
      } catch (err) {
        alert(err?.message || err);
      } finally {
        btnStop.disabled = false;
      }
    }
  });

  // Modal camera lifecycle
  videoModalEl?.addEventListener('shown.bs.modal', async () => {
    try {
      await ensureCameraPreview();
    } catch (err) {
      if (vidPickFile) vidPickFile.style.display = '';
      if (vidFile) vidFile.style.display = '';
      if (vidStart) vidStart.style.display = 'none';
      if (vidStop) vidStop.style.display = 'none';
      setVidStatus(err?.message || 'Erro ao abrir a câmara.');
    }
  });
  videoModalEl?.addEventListener('hidden.bs.modal', () => {
    stopRecording();
    stopStream();
    resetRecorderUi();
    currentVideoTaskId = '';
    setVidStatus('');
    if (vidPreview) {
      try { vidPreview.pause(); } catch (_) {}
      try { vidPreview.srcObject = null; } catch (_) {}
    }
    if (vidFile) vidFile.value = '';
  });

  vidPickFile?.addEventListener('click', () => vidFile?.click());
  vidFile?.addEventListener('change', () => {
    const f = vidFile.files && vidFile.files[0];
    if (!f) return;
    recordedBlob = f;
    if (vidUpload) vidUpload.disabled = false;
    setVidStatus(`Ficheiro: ${f.name}`);
  });

  vidStart?.addEventListener('click', async () => {
    if (!mediaStream) {
      try {
        const ok = await ensureCameraPreview();
        if (!ok) return;
      } catch (err) {
        alert(err?.message || err);
        return;
      }
    }
    if (!window.MediaRecorder) {
      alert('Este browser não suporta gravação. Use "Escolher ficheiro".');
      return;
    }
    recordedBlob = null;
    recChunks = [];
    recSeconds = 0;
    setTimerText(0);
    setVidStatus('A gravar...');

    const mimeType = pickMimeType();
    const opts = {
      mimeType: mimeType || undefined,
      videoBitsPerSecond: 450000,
      audioBitsPerSecond: 64000
    };
    mediaRecorder = new MediaRecorder(mediaStream, opts);
    mediaRecorder.ondataavailable = (ev) => {
      if (ev.data && ev.data.size > 0) recChunks.push(ev.data);
    };
    mediaRecorder.onstop = async () => {
      try {
        const blob = new Blob(recChunks, { type: mimeType || 'video/webm' });
        recordedBlob = blob;
        if (vidUpload) vidUpload.disabled = false;
        setVidStatus('Gravação pronta para enviar.');
      } catch (_) {
        setVidStatus('Erro ao finalizar gravação.');
      }
    };

    vidStart.disabled = true;
    vidStop.disabled = false;
    try { mediaRecorder.start(); } catch (err) { alert(err?.message || err); vidStart.disabled = false; vidStop.disabled = true; return; }

    recTimer = setInterval(() => {
      recSeconds += 1;
      setTimerText(recSeconds);
      if (recSeconds >= 60) stopRecording();
    }, 1000);
    autoStopTimer = setTimeout(() => stopRecording(), 60000);
  });

  vidStop?.addEventListener('click', () => {
    stopRecording();
  });

  vidUpload?.addEventListener('click', async () => {
    if (!currentVideoTaskId) return;
    if (!recordedBlob) return;
    vidUpload.disabled = true;
    try {
      let file = recordedBlob;
      if (recordedBlob instanceof Blob && !(recordedBlob instanceof File)) {
        const ts = new Date().toISOString().replace(/[:.]/g, '-');
        file = new File([recordedBlob], `video_${ts}.webm`, { type: recordedBlob.type || 'video/webm' });
      }
      setVidStatus('A enviar...');
      await uploadVideo(file);
      setVidStatus('Enviado com sucesso.');
      setTimeout(() => { try { videoModal?.hide(); } catch (_) {} }, 600);
    } catch (err) {
      vidUpload.disabled = false;
      setVidStatus('Erro: ' + (err?.message || err));
    }
  });

  load();
});
