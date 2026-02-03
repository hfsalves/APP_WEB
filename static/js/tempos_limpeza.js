// static/js/tempos_limpeza.js

document.addEventListener('DOMContentLoaded', () => {
  const grid = document.getElementById('temposGrid');
  const infoCache = new Map(); // TAREFASSTAMP -> html

  // Nova falta (FS)
  const openNovaFalta = document.getElementById('openNovaFalta');
  const nfModalEl = document.getElementById('novaFaltaModalTL');
  const nfModal = nfModalEl ? new bootstrap.Modal(nfModalEl) : null;
  const nfForm = document.getElementById('novaFaltaFormTL');
  const nfUserWrap = document.getElementById('nfUserWrapTL');
  const nfUser = document.getElementById('nfUserTL');
  const nfAloj = document.getElementById('nfAlojTL');
  const nfData = document.getElementById('nfDataTL');
  const nfUrg = document.getElementById('nfUrgenteTL');
  const nfItem = document.getElementById('nfItemTL');
  const nfStatus = document.getElementById('nfStatusTL');
  const nfGravar = document.getElementById('nfGravarTL');
  const lpMeta = (typeof window !== 'undefined' && window.TEMPOS_LIMPEZA_META) ? window.TEMPOS_LIMPEZA_META : {};
  const lpCanAssign = !!lpMeta.can_assign;
  const lpCurrentUser = (lpMeta.current_user || '').toString();

  // Video
  const videoModalEl = document.getElementById('videoModal');
  const videoModal = videoModalEl ? new bootstrap.Modal(videoModalEl) : null;
  const vidPreview = document.getElementById('vidPreview');
  const vidTimer = document.getElementById('vidTimer');
  const vidStatus = document.getElementById('vidStatus');
  const vidRec = document.getElementById('vidRec');
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
  const anexosCache = new Map(); // TAREFASSTAMP -> array

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
	            ${canStop ? `<button class="btn btn-sm btn-outline-primary js-camera" title="Gravar e enviar v&iacute;deo"><i class="fa-solid fa-video me-1"></i> C&acirc;mara</button>` : ''}
            ${canStop ? `<button class="btn btn-sm btn-stop js-stop"><i class="fa-solid fa-stop me-1"></i> Terminar</button>` : ''}
          </div>
          <div class="tcard-detail">
            <div class="tcard-detail-inner js-detail">
              <div class="tcard-detail-loading">A carregar...</div>
            </div>
          </div>
          <div class="tcard-anexos js-anexos">
            <div class="anx-empty">A carregar anexos...</div>
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

    // carregar anexos por tarefa (best-effort)
    await Promise.all((rows || []).map(async (t) => {
      const id = (t.TAREFASSTAMP || '').toString().trim();
      if (!id) return;
      try {
        await loadAnexosForTask(id);
      } catch (_) {
        anexosCache.set(id, []);
      }
      renderAnexosIntoCard(id);
    }));
  }

  async function loadOptions(query) {
    const q = encodeURIComponent(query);
    const r = await fetch(`/generic/api/options?query=${q}`);
    const js = await r.json().catch(() => ([]));
    if (!r.ok || js.error) throw new Error(js.error || r.statusText);
    return Array.isArray(js) ? js : (js.options || []);
  }

  function setNfStatus(msg) {
    if (!nfStatus) return;
    nfStatus.textContent = (msg || '').toString();
  }

  openNovaFalta?.addEventListener('click', async () => {
    if (!nfModal) return;
    setNfStatus('');
    if (nfItem) nfItem.value = '';
    if (nfUrg) nfUrg.checked = false;

    // defaults
    const hoje = new Date();
    if (nfData) nfData.value = hoje.toISOString().slice(0, 10);

    // user select
    try {
      if (nfUserWrap) nfUserWrap.style.display = lpCanAssign ? '' : 'none';
      if (nfUser) {
        if (lpCanAssign) {
          const listU = await loadOptions("SELECT LOGIN FROM US WHERE ISNULL(INATIVO,0)=0 ORDER BY 1");
          nfUser.innerHTML = listU.map(o => `<option value="${escapeHtml(o.value)}">${escapeHtml(o.text)}</option>`).join('');
          nfUser.value = lpCurrentUser || (listU[0]?.value ?? '');
        } else {
          nfUser.innerHTML = `<option value="${escapeHtml(lpCurrentUser)}">${escapeHtml(lpCurrentUser)}</option>`;
          nfUser.value = lpCurrentUser;
        }
      }
    } catch (_) {
      if (nfUser) {
        nfUser.innerHTML = `<option value="${escapeHtml(lpCurrentUser)}">${escapeHtml(lpCurrentUser)}</option>`;
        nfUser.value = lpCurrentUser;
      }
    }

    // alojamentos (obrigatorio na FS)
    try {
      const listA = await loadOptions("SELECT NOME FROM AL WHERE ISNULL(INATIVO,0)=0 ORDER BY 1");
      if (nfAloj) {
        nfAloj.innerHTML = listA.map(o => `<option value="${escapeHtml(o.value)}">${escapeHtml(o.text)}</option>`).join('');
        if (!nfAloj.value) nfAloj.value = listA[0]?.value ?? '';
      }
    } catch (_) {
      if (nfAloj) nfAloj.innerHTML = '';
    }

    nfModal.show();
  });

  nfForm?.addEventListener('submit', async (e) => {
    e.preventDefault();
    if (!nfModal) return;

    const payload = {
      ALOJAMENTO: (nfAloj?.value || '').trim(),
      DATA: (nfData?.value || '').trim(),
      USERNAME: (nfUser?.value || lpCurrentUser || '').trim(),
      ITEM: (nfItem?.value || '').trim(),
      URGENTE: nfUrg?.checked ? 1 : 0,
    };

    if (!payload.ALOJAMENTO) { setNfStatus('Indica o alojamento.'); return; }
    if (!payload.DATA) { setNfStatus('Indica a data.'); return; }
    if (!payload.USERNAME) { setNfStatus('Indica o utilizador.'); return; }
    if (!payload.ITEM) { setNfStatus('Indica o item em falta.'); return; }

    try {
      if (nfGravar) nfGravar.disabled = true;
      setNfStatus('A gravar...');
      const r = await fetch('/generic/api/fs_falta', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      const js = await r.json().catch(() => ({}));
      if (!r.ok || js.error) throw new Error(js.error || r.statusText);
      (bootstrap.Modal.getInstance(nfModalEl) || nfModal).hide();
    } catch (err) {
      setNfStatus(err?.message || err);
    } finally {
      if (nfGravar) nfGravar.disabled = false;
    }
  });

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
    if (vidRec) {
      vidRec.disabled = false;
      vidRec.classList.remove('btn-outline-light', 'btn-outline-danger');
      vidRec.classList.add('btn-danger');
      vidRec.innerHTML = '<span class="rec-dot me-2" aria-hidden="true"></span> Gravar';
    }
    if (vidUpload) vidUpload.disabled = true;
    if (videoModalEl) videoModalEl.classList.remove('is-recording');
  }

  function stopRecording() {
    try { if (mediaRecorder && mediaRecorder.state !== 'inactive') mediaRecorder.stop(); } catch (_) {}
    mediaRecorder = null;
    clearInterval(recTimer); recTimer = null;
    clearTimeout(autoStopTimer); autoStopTimer = null;
    if (vidRec) {
      vidRec.disabled = false;
      vidRec.classList.remove('btn-outline-light', 'btn-outline-danger');
      vidRec.classList.add('btn-danger');
      vidRec.innerHTML = '<span class="rec-dot me-2" aria-hidden="true"></span> Gravar';
    }
    if (videoModalEl) videoModalEl.classList.remove('is-recording');
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
      if (vidRec) vidRec.style.display = 'none';
      setVidStatus('Este dispositivo n\u00E3o suporta c\u00E2mara no browser. Envie um ficheiro.');
      return false;
    }

    if (vidPickFile) vidPickFile.style.display = 'none';
    if (vidFile) vidFile.style.display = 'none';
    if (vidRec) vidRec.style.display = '';

    const baseConstraints = {
      audio: { echoCancellation: true, noiseSuppression: true, channelCount: 1 },
      video: {
        // Preferir camara traseira (environment). Alguns browsers so aceitam ideal, outros suportam exact.
        facingMode: { exact: 'environment' },
        width: { ideal: 640 },
        height: { ideal: 360 },
        frameRate: { ideal: 15, max: 24 }
      }
    };
    try {
      mediaStream = await navigator.mediaDevices.getUserMedia(baseConstraints);
    } catch (_) {
      // fallback mais permissivo
      const fallback = {
        ...baseConstraints,
        video: { ...baseConstraints.video, facingMode: { ideal: 'environment' } }
      };
      mediaStream = await navigator.mediaDevices.getUserMedia(fallback);
    }
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
	    if (!currentVideoTaskId) throw new Error('Tarefa inv\u00E1lida.');
    const fd = new FormData();
    fd.append('table', 'TAREFAS');
    fd.append('rec', currentVideoTaskId);
	    fd.append('descricao', 'V\u00EDdeo limpeza');
    fd.append('file', file);
    const res = await fetch('/api/anexos/upload', { method: 'POST', body: fd });
    const js = await res.json().catch(() => ({}));
    if (!res.ok || js.error) throw new Error(js.error || res.statusText);
    return js;
  }

  function isImg(ext) {
    return /^(png|jpg|jpeg|gif|webp)$/i.test(String(ext || ''));
  }
  function isVid(ext) {
    return /^(mp4|webm|ogg|mov|m4v)$/i.test(String(ext || ''));
  }

  async function loadAnexosForTask(tid, { force } = { force: false }) {
    const id = (tid || '').toString().trim();
    if (!id) return;
    if (!force && anexosCache.has(id)) return;
    const res = await fetch(`/api/anexos?table=TAREFAS&rec=${encodeURIComponent(id)}`);
    if (!res.ok) throw new Error('Falha ao carregar anexos.');
    const arr = await res.json().catch(() => ([]));
    anexosCache.set(id, Array.isArray(arr) ? arr : []);
  }

  function renderAnexosIntoCard(tid) {
    const id = (tid || '').toString().trim();
    const esc = (window.CSS && typeof window.CSS.escape === 'function')
      ? window.CSS.escape
      : (v) => String(v || '').replace(/["\\]/g, '\\$&');
    const card = grid?.querySelector?.(`.tcard[data-id="${esc(id)}"]`);
    if (!card) return;
    const cont = card.querySelector('.js-anexos');
    if (!cont) return;

    const rows = anexosCache.get(id) || [];
    if (!rows.length) {
      cont.innerHTML = '<div class="anx-empty">Sem anexos.</div>';
      return;
    }

    cont.innerHTML = rows.map(a => {
      const stamp = (a.ANEXOSSTAMP || a.anexosstamp || '').toString().trim();
      const url = (a.CAMINHO || '').toString().trim();
      const typ = (a.TIPO || '').toString().trim();
      const name = (a.FICHEIRO || '').toString().trim();
      let media = `<div class="d-flex align-items-center justify-content-center h-100 text-muted"><i class="fa-regular fa-file-lines fa-lg"></i></div>`;
      if (url && isImg(typ)) media = `<img src="${escapeHtml(url)}" alt="">`;
      else if (url && isVid(typ)) media = `<video src="${escapeHtml(url)}" muted playsinline></video>`;

      const delBtn = stamp ? `<button type="button" class="anx-del js-anx-del" data-stamp="${escapeHtml(stamp)}" title="Eliminar"><i class="fa-solid fa-trash"></i></button>` : '';
      const href = url ? `href="${escapeHtml(url)}" target="_blank" rel="noopener"` : '';
      return `
        <div class="anx" title="${escapeHtml(name || typ)}">
          <a ${href} class="d-block h-100 w-100" style="text-decoration:none; color:inherit;">
            ${media}
          </a>
          ${delBtn}
        </div>
      `;
    }).join('');
  }

  grid?.addEventListener('click', async (e) => {
    const btnToggle = e.target.closest?.('.js-toggle');
    const btnCam = e.target.closest?.('.js-camera');
    const btnAnxDel = e.target.closest?.('.js-anx-del');
    const btnStart = e.target.closest?.('.js-start');
    const btnStop = e.target.closest?.('.js-stop');
    const card = e.target.closest?.('.tcard[data-id]');
    const id = (card?.dataset?.id || '').toString().trim();
    if (!id) return;

    if (btnAnxDel) {
      e.preventDefault();
      e.stopPropagation?.();
      const stamp = (btnAnxDel.dataset.stamp || '').toString().trim();
      if (!stamp) return;
      const ok = confirm('Eliminar este anexo?');
      if (!ok) return;
      btnAnxDel.disabled = true;
      try {
        const r = await fetch(`/api/anexos/${encodeURIComponent(stamp)}`, { method: 'DELETE' });
        const js = await r.json().catch(() => ({}));
        if (!r.ok || js.error) throw new Error(js.error || r.statusText);
        await loadAnexosForTask(id, { force: true });
        renderAnexosIntoCard(id);
      } catch (err) {
        alert(err?.message || err);
      } finally {
        btnAnxDel.disabled = false;
      }
      return;
    }

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
      if (vidRec) vidRec.style.display = 'none';
      setVidStatus(err?.message || 'Erro ao abrir a c\u00E2mara.');
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

  async function startRecording() {
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
	      alert('Este browser n\u00E3o suporta grava\u00E7\u00E3o. Use \"Escolher ficheiro\".');
      return;
    }
    recordedBlob = null;
    recChunks = [];
    recSeconds = 0;
    setTimerText(0);
    setVidStatus('A gravar...');
    if (videoModalEl) videoModalEl.classList.add('is-recording');
    if (vidUpload) vidUpload.disabled = true;
    if (vidRec) {
      // "Parar" tem de ser bem visivel no fundo claro do modal
      vidRec.classList.remove('btn-danger', 'btn-outline-light');
      vidRec.classList.add('btn-outline-danger');
      vidRec.innerHTML = '<i class="fa-solid fa-stop me-1"></i> Parar';
    }

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
	        setVidStatus('Grava\u00E7\u00E3o pronta para enviar.');
      } catch (_) {
	        setVidStatus('Erro ao finalizar grava\u00E7\u00E3o.');
      }
    };

    if (vidRec) vidRec.disabled = false;
    try { mediaRecorder.start(); } catch (err) {
      alert(err?.message || err);
      if (vidRec) {
        vidRec.disabled = false;
        vidRec.classList.remove('btn-outline-light');
        vidRec.classList.add('btn-danger');
        vidRec.innerHTML = '<span class="rec-dot me-2" aria-hidden="true"></span> Gravar';
      }
      if (videoModalEl) videoModalEl.classList.remove('is-recording');
      return;
    }

    recTimer = setInterval(() => {
      recSeconds += 1;
      setTimerText(recSeconds);
      if (recSeconds >= 60) stopRecording();
    }, 1000);
    autoStopTimer = setTimeout(() => stopRecording(), 60000);
  }

  vidRec?.addEventListener('click', async () => {
    // toggle gravar/parar
    try {
      if (mediaRecorder && mediaRecorder.state !== 'inactive') {
        stopRecording();
        return;
      }
      if (recordedBlob) {
        // ja existe gravacao pronta; nao iniciar por cima sem confirmacao
	        const ok = confirm('J\u00E1 existe uma grava\u00E7\u00E3o pronta. Queres gravar outra por cima?');
        if (!ok) return;
        recordedBlob = null;
      }
      await startRecording();
    } catch (err) {
      alert(err?.message || err);
    }
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
      // refrescar anexos no card
      try {
        if (currentVideoTaskId) {
          await loadAnexosForTask(currentVideoTaskId, { force: true });
          renderAnexosIntoCard(currentVideoTaskId);
        }
      } catch (_) {}
      setTimeout(() => { try { videoModal?.hide(); } catch (_) {} }, 600);
    } catch (err) {
      vidUpload.disabled = false;
      setVidStatus('Erro: ' + (err?.message || err));
    }
  });

  load();
});
