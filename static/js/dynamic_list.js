// static/js/dynamic_list.js
// Lista genÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â‚¬Å¾Ã‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€¦Ã‚Â¡ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â©rica com modal de filtros, suporte a intervalo de datas e ordenaÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â‚¬Å¾Ã‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€¦Ã‚Â¡ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â§ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â‚¬Å¾Ã‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€¦Ã‚Â¡ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â£o.

document.addEventListener('DOMContentLoaded', () => {
  const tableName       = window.TABLE_NAME;
  const gridDiv         = document.getElementById('grid');
  const btnFilterToggle = document.getElementById('btnFilterToggle');
  const btnNewAttachment= document.getElementById('btnNewAttachment');
  const btnNew          = document.getElementById('btnNew');
  const modalFiltros    = document.getElementById('modalFiltros');
  const closeFiltersBtn = document.getElementById('closeFiltersModal');
  const closeFiltersTopBtn = document.getElementById('closeFiltersModalTop');
  const filterForm      = document.getElementById('filter-form');
  const userPerms       = window.USER_PERMS[tableName] || {};
  const isFoList        = (tableName || '').toUpperCase() === 'FO';
  const tableForm       = (window.TABLE_FORM || '').trim();
  const listUrl         = window.location.pathname + window.location.search;
  let currentCols       = [];



  // Ajusta os botÃƒÆ’Ã‚Âµes do header (com guardas)
  if (btnFilterToggle) {
    btnFilterToggle.innerHTML = '<i class="fa fa-filter"></i><span>Filtrar</span>';
    btnFilterToggle.className = 'sz_button sz_button_ghost';
  }
  if (btnNew) {
    btnNew.innerHTML = '<i class="fa fa-plus"></i><span>Novo</span>';
    btnNew.className = 'sz_button sz_button_primary';
  }
  if (btnNewAttachment) {
    btnNewAttachment.innerHTML = '<i class="fa fa-paperclip"></i><span>+ Anexo</span>';
    btnNewAttachment.classList.add('btn-attach-custom');
  }
  // removido botão de anexo específico

  // garante que ficam juntos
  const header = document.querySelector('.dynamic-header'); if(header){ header.classList.add('d-flex','align-items-center'); }

  // ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã¢â‚¬Â¦Ãƒâ€šÃ‚Â¡ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€¦Ã‚Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚ÂÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã¢â‚¬Â¦Ãƒâ€šÃ‚Â¡ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€¦Ã‚Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â ICON-ONLY BUTTONS ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã¢â‚¬Â¦Ãƒâ€šÃ‚Â¡ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€¦Ã‚Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚ÂÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã¢â‚¬Â¦Ãƒâ€šÃ‚Â¡ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€¦Ã‚Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â

  // 1) Sem permissÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â‚¬Å¾Ã‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€¦Ã‚Â¡ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â£o de consulta, aborta
  if (!userPerms.consultar) {
    alert('Sem permissÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â‚¬Å¾Ã‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€¦Ã‚Â¡ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â£o para consultar esta lista.');
    return;
  }

  const sanitizeBaseForm = (path) => {
    const base = path.startsWith('/') ? path : `/${path}`;
    return base.replace(/\/+$/, '');
  };

  const resolveFormUrl = (stamp = '') => {
    const upperTable = (tableName || '').toUpperCase();
    if (upperTable === 'FT') {
      return stamp ? `/faturacao/ft/${stamp}` : '/faturacao/ft/new';
    }
    if (upperTable === 'RS') {
      return stamp ? `/reservas/rs/${stamp}` : '/reservas/rs/new';
    }
    if (tableForm) {
      const pref = tableForm.startsWith('/') ? tableForm : `/generic/${tableForm}`;
      const base = sanitizeBaseForm(pref).toLowerCase(); // rotas registadas em minúsculas
      return stamp ? `${base}/${stamp}` : `${base}/`;
    }
    return `/generic/form/${tableName}/${stamp || ''}`;
  };

  const withReturnTo = (url) => {
    try {
      const sep = url.includes('?') ? '&' : '?';
      return `${url}${sep}return_to=${encodeURIComponent(listUrl)}`;
    } catch (_) {
      return url;
    }
  };

  function openFiltersModal() {
    if (!modalFiltros) return;
    document.body.classList.add('modal-filtros-open');
    modalFiltros.classList.add('sz_is_open');
    modalFiltros.setAttribute('aria-hidden', 'false');
  }

  function closeFiltersModal() {
    if (!modalFiltros) return;
    modalFiltros.classList.remove('sz_is_open');
    modalFiltros.setAttribute('aria-hidden', 'true');
    document.body.classList.remove('modal-filtros-open');
  }

  // Move o modal de filtros para <body> (fora de containers com overflow)
  if (modalFiltros) { document.body.appendChild(modalFiltros); }

  // Botão Filtrar abre modal
  if (btnFilterToggle && modalFiltros) {
    btnFilterToggle.addEventListener('click', () => {
      openFiltersModal();
    });
  }
  if (closeFiltersBtn) {
    closeFiltersBtn.addEventListener('click', closeFiltersModal);
  }
  if (closeFiltersTopBtn) {
    closeFiltersTopBtn.addEventListener('click', closeFiltersModal);
  }
  if (modalFiltros) {
    modalFiltros.addEventListener('click', (e) => {
      if (e.target === modalFiltros) {
        closeFiltersModal();
      }
    });
  }
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && modalFiltros && modalFiltros.classList.contains('sz_is_open')) {
      closeFiltersModal();
    }
  });

  if (btnNew) {
    btnNew.addEventListener('click', () => {
      location.href = withReturnTo(resolveFormUrl());
    });
  }
  if (btnNewAttachment) {
    btnNewAttachment.addEventListener('click', async (e) => {
      e.preventDefault();
      e.stopPropagation();
      try {
        if (isFoList) {
          await handleFoAttachmentFlow();
        } else {
          await handleGenericAttachmentFlow();
        }
      } catch (err) {
        alert('Erro ao anexar: ' + err.message);
      }
    });
  }
  // 5) Ao submeter filtros, esconde modal e carrega dados
  filterForm.addEventListener('submit', e => {
    e.preventDefault();
    closeFiltersModal();
    loadData();
  });

  const clearFiltersBtn = document.getElementById('clearFilters');
  if (clearFiltersBtn) {
    clearFiltersBtn.addEventListener('click', () => {
      filterForm.reset();
    });
  }

  // 6) BotÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â‚¬Å¾Ã‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€¦Ã‚Â¡ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â£o pequeno ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã¢â‚¬Â¦Ãƒâ€šÃ‚Â¡ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€šÃ‚Â¦ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã¢â‚¬Â¦ÃƒÂ¢Ã¢â€šÂ¬Ã…â€œAplicarÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã¢â‚¬Â¦Ãƒâ€šÃ‚Â¡ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€¦Ã‚Â¡ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â
  const applyFiltersBtn = document.getElementById('applyFilters');
  if (applyFiltersBtn && filterForm) {
    applyFiltersBtn.addEventListener('click', () => filterForm.requestSubmit());
  }

  // 6) InicializaÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â‚¬Å¾Ã‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€¦Ã‚Â¡ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â§ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â‚¬Å¾Ã‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€¦Ã‚Â¡ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â£o da lista
  initListView().catch(console.error);

  // guarda os dados e estado de ordenaÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â‚¬Å¾Ã‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€¦Ã‚Â¡ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â§ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â‚¬Å¾Ã‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€¦Ã‚Â¡ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â£o
  let dataRows = [];
  let sortField = null;
  let sortDir = 1; // 1 = asc, -1 = desc

  function showLoading() {
    const overlay = document.getElementById('loadingOverlay');
    overlay.style.display = 'flex';
    setTimeout(() => overlay.style.opacity = '1', 15);
  }
  function hideLoading() {
    const overlay = document.getElementById('loadingOverlay');
    overlay.style.opacity = '0';
    setTimeout(() => overlay.style.display = 'none', 250); // espera pelo fade-out
  }

  async function captureFileFromCamera(accept = 'image/*', captureEnv = 'environment') {
    return new Promise((resolve, reject) => {
      const input = document.createElement('input');
      input.type = 'file';
      input.accept = accept;
      if (captureEnv) input.capture = captureEnv;
      input.style.display = 'none';
      document.body.appendChild(input);
      input.addEventListener('change', () => {
        const file = input.files?.[0];
        input.remove();
        resolve(file || null);
      }, { once: true });
      input.addEventListener('error', (err) => {
        input.remove();
        reject(err);
      }, { once: true });
      input.click();
    });
  }

  async function handleFoAttachmentFlow() {
    const docPhoto = await captureFileFromCamera('image/*', 'environment');
    if (!docPhoto) return;

    const recStamp = crypto.randomUUID().replace(/-/g, '').toUpperCase().slice(0, 25);
    const fd = new FormData();
    fd.append('file', docPhoto);
    fd.append('table', 'FO');
    fd.append('rec', recStamp);
    fd.append('descricao', '');
    const up = await fetch('/api/anexos/upload', { method: 'POST', body: fd });
    if (!up.ok) {
      const err = await up.json().catch(() => ({}));
      throw new Error(err.error || up.statusText);
    }
    const todayIso = new Date().toISOString().slice(0, 10);
    const foPayload = { FOSTAMP: recStamp, DATA: todayIso, PDATA: todayIso, OBS: 'Documento por classificar' };
    const foRes = await fetch('/generic/api/FO', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(foPayload)
    });
    if (!foRes.ok) {
      const err = await foRes.json().catch(() => ({}));
      throw new Error(err.error || foRes.statusText);
    }
    alert('Anexo adicionado.');
    if (typeof loadData === 'function') {
      await loadData();
    } else {
      window.location.reload();
    }
  }

  async function handleGenericAttachmentFlow() {
    const picker = document.createElement('input');
    picker.type = 'file';
    picker.accept = 'image/*,application/pdf,application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document,application/vnd.ms-excel,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,text/plain';
    picker.capture = 'environment';
    picker.style.display = 'none';
    picker.multiple = false;
    document.body.appendChild(picker);
    picker.addEventListener('change', async () => {
      const file = picker.files?.[0];
      picker.remove();
      if (!file) return;
      const recStamp = crypto.randomUUID().replace(/-/g, '').toUpperCase().slice(0, 25);
      const fd = new FormData();
      fd.append('file', file);
      fd.append('table', 'FO');
      fd.append('rec', recStamp);
      fd.append('descricao', '');
      const up = await fetch('/api/anexos/upload', { method: 'POST', body: fd });
      if (!up.ok) {
        const err = await up.json().catch(() => ({}));
        alert('Erro ao anexar: ' + (err.error || up.statusText));
        return;
      }
      const todayIso = new Date().toISOString().slice(0, 10);
      const foPayload = { FOSTAMP: recStamp, DATA: todayIso, PDATA: todayIso, OBS: 'Documento por classificar' };
      const foRes = await fetch('/generic/api/FO', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(foPayload)
      });
      if (!foRes.ok) {
        const err = await foRes.json().catch(() => ({}));
        alert('Anexo gravado, mas falhou criar FO: ' + (err.error || foRes.statusText));
        return;
      }
      alert('Anexo adicionado.');
      if (typeof loadData === 'function') {
        await loadData();
      } else {
        window.location.reload();
      }
    }, { once: true });
    picker.click();
  }


  async function initListView() {
    // a) Describe para metadados
    let meta;
    try {
      const res = await fetch(`/generic/api/${tableName}?action=describe`);
      if (!res.ok) throw new Error(res.statusText);
      meta = await res.json();
    } catch (e) {
      console.error('Falha ao carregar metadados:', e);
      gridDiv.innerHTML = `<p class="text-danger">Erro ao carregar filtros.</p>`;
      return;
    }
    // b) Separa colunas de filtros e de listagem
    const filterCols = meta.filter(c => c.filtro);
    currentCols      = meta.filter(c => c.lista);

    // c) Monta filtros no modal
    renderFilters(filterCols);

    // d) Load inicial de dados
    showLoading()

    await loadData();

    hideLoading()
  
  }
  

  function resolveFilterDefaultToken(rawValue) {
    const token = String(rawValue || '').trim();
    if (!token) return '';
    const lower = token.toLowerCase();
    const today = new Date();
    const toIso = (dt) => {
      const y = dt.getFullYear();
      const m = String(dt.getMonth() + 1).padStart(2, '0');
      const d = String(dt.getDate()).padStart(2, '0');
      return `${y}-${m}-${d}`;
    };
    if (lower === 'today') return toIso(today);
    if (lower === 'month_start') return toIso(new Date(today.getFullYear(), today.getMonth(), 1));
    if (lower === 'month_end') return toIso(new Date(today.getFullYear(), today.getMonth() + 1, 0));
    if (lower === 'year_start') return `${today.getFullYear()}-01-01`;
    if (lower === 'year_end') return `${today.getFullYear()}-12-31`;
    const m = lower.match(/^today\s*([+-])\s*(\d+)$/);
    if (m) {
      const dt = new Date(today);
      const delta = Number(m[2] || 0) * (m[1] === '-' ? -1 : 1);
      dt.setDate(dt.getDate() + delta);
      return toIso(dt);
    }
    return token;
  }

  function parseDefaultFilter(col) {
    const raw = String(col?.filtrodefault || '').trim();
    if (!raw) return null;
    if (col.tipo === 'DATE') {
      const parts = raw.split('|');
      return {
        from: resolveFilterDefaultToken(parts[0] || ''),
        to: resolveFilterDefaultToken(parts[1] || '')
      };
    }
    const match = raw.match(/^(>=|<=|=|>|<|like)\s*:(.*)$/i);
    return {
      operator: match ? match[1].toLowerCase() : '=',
      value: resolveFilterDefaultToken(match ? match[2] : raw)
    };
  }

  function markDefaultControl(el, value) {
    if (!el || value === null || value === undefined || value === '') return;
    const defaultValue = String(value);
    el.value = defaultValue;
    el.dataset.defaultValue = defaultValue;
    el.dataset.defaultApplied = '1';
    el.dataset.hasDefaultFilter = '1';
    const syncState = () => {
      el.dataset.defaultApplied = (String(el.value || '') === defaultValue) ? '1' : '0';
    };
    el.addEventListener('input', syncState);
    el.addEventListener('change', syncState);
  }

  function renderFilters(cols) {
    filterForm.innerHTML = '';
    filterForm.className = 'sz_dynamic_filters_form';

    cols.forEach(col => {
      const defaultFilter = parseDefaultFilter(col);
      if (col.tipo === 'DATE') {
        const wrapRow = document.createElement('div');
        wrapRow.classList.add('sz_field', 'sz_filter_date_range');

        const label = document.createElement('label');
        label.classList.add('sz_label');
        label.textContent = col.descricao || col.name;
        wrapRow.append(label);

        const row = document.createElement('div');
        row.classList.add('sz_grid', 'sz_grid_2', 'sz_filter_date_range_row');

        ['from', 'to'].forEach(dir => {
          const inp = document.createElement('input');
          inp.type = 'date';
          inp.name = `${col.name}_${dir}`;
          inp.dataset.isDateRange = '1';
          inp.classList.add('sz_date', 'sz_filter_date_input');
          inp.placeholder = dir === 'from' ? 'De' : 'Até';
          if (defaultFilter && defaultFilter[dir]) markDefaultControl(inp, defaultFilter[dir]);
          row.append(inp);
        });

        wrapRow.append(row);
        filterForm.append(wrapRow);
        
      } else if (col.tipo === 'COMBO') {
        const wrap = document.createElement('div');
        wrap.classList.add('sz_field');
        const lbl = document.createElement('label');
        lbl.classList.add('sz_label');
        lbl.textContent = col.descricao || col.name;
        const sel = document.createElement('select');
        sel.name = col.name;
        sel.classList.add('sz_select');
        sel.innerHTML = '<option value=\"\">---</option>';
        wrap.append(lbl, sel);
        filterForm.append(wrap);

        (async () => {
          let opts = [];
          try {
            if (/^\s*SELECT\s+/i.test(col.combo)) {
              const resp = await fetch(`/generic/api/options?query=${encodeURIComponent(col.combo)}`);
              opts = await resp.json();
            } else {
              const resp = await fetch(col.combo);
              opts = await resp.json();
            }
          } catch (e) {
            console.error('Erro COMBO', col.name, e);
          }
          opts.forEach(o => {
            const v = typeof o === 'object' ? Object.values(o)[0] : o;
            const opt = document.createElement('option');
            opt.value = v ?? '';
            opt.textContent = v;
            sel.append(opt);
          });
          if (defaultFilter && defaultFilter.value !== '') markDefaultControl(sel, defaultFilter.value);
        })();
      } else if (col.tipo === 'BIT') {
        const wrap = document.createElement('div');
        wrap.classList.add('sz_field');
        const lbl = document.createElement('label');
        lbl.classList.add('sz_label');
        lbl.textContent = col.descricao || col.name;
        const sel = document.createElement('select');
        sel.name = col.name;
        sel.classList.add('sz_select');
        sel.innerHTML = `
          <option value="">---</option>
          <option value="1">Sim</option>
          <option value="0">Não</option>
        `;
        if (defaultFilter && defaultFilter.value !== '') markDefaultControl(sel, defaultFilter.value);
        wrap.append(lbl, sel);
        filterForm.append(wrap);
      } else {
        const wrap = document.createElement('div');
        wrap.classList.add('sz_field');
        const lbl = document.createElement('label');
        lbl.classList.add('sz_label');
        lbl.textContent = col.descricao || col.name;
        const inp = document.createElement('input');
        inp.name = col.name;
        inp.classList.add('sz_input');
        switch (col.tipo) {
          case 'HOUR':
            inp.type = 'time';
            break;
          case 'INT':
            inp.type = 'number';
            inp.step = '1';
            break;
          case 'DECIMAL':
            inp.type = 'number';
            inp.step = '0.01';
            break;
          default:
            inp.type = 'text';
        }
        if (defaultFilter && defaultFilter.value !== '') markDefaultControl(inp, defaultFilter.value);
        wrap.append(lbl, inp);
        filterForm.append(wrap);
      }
    });
  }
  async function loadData() {
    const params = new URLSearchParams();
    filterForm.querySelectorAll('[name]').forEach(el => {
      if (el.dataset.defaultApplied === '1' && el.dataset.isDateRange !== '1') {
        return;
      }
      if (el.dataset.hasDefaultFilter === '1' && !el.value && el.type !== 'checkbox') {
        params.append(`__clear_default__${el.name}`, '1');
        return;
      }
      if (el.type === 'checkbox') {
        if (el.checked) params.append(el.name, '1');
      } else if (el.value) {
        params.append(el.name, el.value);
      }
    });

    const url = `/generic/api/${tableName}` +
      (params.toString() ? '?' + params.toString() : '');
    const res = await fetch(url);
    if (!res.ok) {
      gridDiv.innerHTML = `<p class="text-danger">Erro ${res.status}</p>`;
      return;
    }
    dataRows = await res.json();
    const cntEl = document.getElementById('recordCount');
    if (cntEl) {
      const n = (dataRows || []).length;
      cntEl.textContent = n + (n === 1 ? ' registo' : ' registos');
    }
    if(cntEl){ const n = (dataRows||[]).length; cntEl.textContent = n + (n===1? ' registo' : ' registos'); }
    renderTable(currentCols, dataRows);
  }

  function renderTable(cols, rows) {
    gridDiv.innerHTML = '';
    const tableWrap = document.createElement('div');
    tableWrap.classList.add('sz_table_wrap');
    const table = document.createElement('table');
    table.classList.add('sz_table');

    // CabeÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â‚¬Å¾Ã‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€¦Ã‚Â¡ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â§alho com ordenaÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â‚¬Å¾Ã‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€¦Ã‚Â¡ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â§ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â‚¬Å¾Ã‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€¦Ã‚Â¡ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â£o
    const thead = document.createElement('thead');
    thead.classList.add('sz_table_head');
    const trh   = document.createElement('tr');
    trh.classList.add('sz_table_row');
    cols.forEach((c, idx) => {
      const th = document.createElement('th');
      th.classList.add('sz_table_cell');
      th.textContent = c.descricao || c.name;
      th.style.cursor = 'pointer';
      th.addEventListener('click', () => {
        sortDir   = (sortField === c.name) ? -sortDir : 1;
        sortField = c.name;
        dataRows.sort((a, b) => {
          let va = a[c.name], vb = b[c.name], res = 0;
          switch (c.tipo) {
            case 'INT':    res = (Number(va)||0) - (Number(vb)||0); break;
            case 'DECIMAL':res = (Number(va)||0) - (Number(vb)||0); break;
            case 'DATE':   res = new Date(va) - new Date(vb);      break;
            case 'BIT':    res = ((va?1:0) - (vb?1:0));             break;
            default:       res = String(va||'').localeCompare(String(vb||''));
          }
          return res * sortDir;
        });
        renderTable(cols, dataRows);
      });
      trh.append(th);
    });
    thead.append(trh);
    table.append(thead);

    // Corpo
    const tbody = document.createElement('tbody');
    rows.forEach(r => {
      const tr = document.createElement('tr');
      tr.classList.add('sz_table_row');
      tr.style.cursor = 'pointer';
      cols.forEach(c => {
        const td = document.createElement('td');
        td.classList.add('sz_table_cell');
        let v = r[c.name];

        // formata datas
        if (c.tipo==='DATE' && v) {
          const d = new Date(v);
          if (!isNaN(d)) {
            const dd   = String(d.getDate()).padStart(2,'0');
            const mm   = String(d.getMonth()+1).padStart(2,'0');
            const yyyy = d.getFullYear();
            v = `${dd}.${mm}.${yyyy}`;
          }
        }
        // BIT como ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€šÃ‚Â¦ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã¢â‚¬Â¦ÃƒÂ¢Ã¢â€šÂ¬Ã…â€œÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€¦Ã‚Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â¦ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€¦Ã¢â‚¬Å“
        if (c.tipo==='BIT') {
          const isTrue = (v === 1 || v === '1' || v === true);
          td.innerHTML = isTrue ? '<i class="fa fa-check"></i>' : '';
        } else {
          td.textContent = v ?? '';
        }
        tr.append(td);
      });

      // clique abre ediÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â‚¬Å¾Ã‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€¦Ã‚Â¡ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â§ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â‚¬Å¾Ã‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€¦Ã‚Â¡ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â£o
      const pk = r[`${tableName.toUpperCase()}STAMP`];
      tr.addEventListener('click', () => {
        location.href = withReturnTo(resolveFormUrl(pk));
      });
      tbody.append(tr);
    });
    table.append(tbody);
    tableWrap.append(table);
    gridDiv.append(tableWrap);
  }

});
