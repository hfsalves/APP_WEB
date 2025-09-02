// static/js/newanexo.js
document.addEventListener('DOMContentLoaded', function () {
  const btnAdd = document.getElementById('btnAddAnexo');
  const inputFile = document.getElementById('inputAnexo');
  const lista = document.getElementById('anexos-list');
  const table = window.TABLE_NAME;
  const rec   = window.RECORD_STAMP;

  function refreshAnexos() {
    fetch(`/api/anexos?table=${table}&rec=${rec}`)
      .then(r => r.json())
      .then(arr => {
        if (!arr.length) {
          lista.innerHTML = '<p class="text-muted">Ainda não há anexos.</p>';
          return;
        }
        lista.innerHTML = arr.map(a => `
          <div class="d-flex align-items-center mb-2 p-2 rounded bg-light">
            <a href="${a.CAMINHO}" target="_blank">${a.FICHEIRO}</a>
            <i class="fa fa-times text-danger ms-3" data-id="${a.ANEXOSSTAMP}" style="cursor:pointer"></i>
          </div>
        `).join('');
        lista.querySelectorAll('.fa-times').forEach(el => {
          el.onclick = async function () {
            if (!confirm('Eliminar este anexo?')) return;
            await fetch(`/generic/api/anexos/${el.dataset.id}`, { method: 'DELETE' });
            refreshAnexos();
            if (typeof window.showToast === 'function') {
              window.showToast('Anexo eliminado.', 'info');
            }
          }
        });
      });
  }

  btnAdd.onclick = () => inputFile.click();

  inputFile.onchange = async function () {
    const file = this.files[0];
    if (!file) return;
    const formD = new FormData();
    formD.append('file', file);
    formD.append('table', table);
    formD.append('rec', rec);
    formD.append('descricao', '');

    const res = await fetch('/api/anexos/upload', { method: 'POST', body: formD });
    if (res.ok) {
      inputFile.value = '';
      refreshAnexos();
      if (typeof window.showToast === 'function') {
        window.showToast('Anexo gravado com sucesso.', 'success');
      }
    } else {
      alert('Erro ao anexar!');
    }
  };

  document.getElementById('btnVoltar').onclick = () => window.location.href = '/';

  refreshAnexos();
});
