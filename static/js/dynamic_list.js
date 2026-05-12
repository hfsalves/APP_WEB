// static/js/dynamic_list.js
// Lista genÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â‚¬Å¾Ã‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€¦Ã‚Â¡ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â©rica com modal de filtros, suporte a intervalo de datas e ordenaÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â‚¬Å¾Ã‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€¦Ã‚Â¡ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â§ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â‚¬Å¾Ã‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€¦Ã‚Â¡ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â£o.

document.addEventListener('DOMContentLoaded', () => {
  const tr = (key, vars) => (typeof window.t === 'function' ? window.t(key, vars) : key);
  const tableName       = window.TABLE_NAME;
  const gridDiv         = document.getElementById('grid');
  const btnSortToggle   = document.getElementById('btnSortToggle');
  const btnFilterToggle = document.getElementById('btnFilterToggle');
  const btnNewAttachment= document.getElementById('btnNewAttachment');
  const btnNew          = document.getElementById('btnNew');
  const modalSort       = document.getElementById('modalSort');
  const closeSortBtn    = document.getElementById('closeSortModal');
  const closeSortTopBtn = document.getElementById('closeSortModalTop');
  const applySortBtn    = document.getElementById('applySort');
  const sortFieldList   = document.getElementById('sortFieldList');
  const modalFiltros    = document.getElementById('modalFiltros');
  const closeFiltersBtn = document.getElementById('closeFiltersModal');
  const closeFiltersTopBtn = document.getElementById('closeFiltersModalTop');
  const filterForm      = document.getElementById('filter-form');
  const userPerms       = window.USER_PERMS[tableName] || {};
  const isFoList        = (tableName || '').toUpperCase() === 'FO';
  const tableForm       = (window.TABLE_FORM || '').trim();
  const menuStamp       = (window.MENU_STAMP || '').trim();
  const listUrl         = window.location.pathname + window.location.search;
  let currentCols       = [];
  let mobileCardCols    = [];
  let listUseExactWidths = false;
  const mobileListQuery = window.matchMedia('(max-width: 768px)');
  let pendingSortField  = null;
  let pendingSortDir    = 1;

  const escapeHtml = (value) => String(value ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');

  const toAppRelativeUrl = (value, fallback = '') => {
    const raw = String(value || '').trim();
    if (!raw) return fallback;
    if (/^(javascript|data|vbscript):/i.test(raw)) return fallback;
    if (/^https?:\/\//i.test(raw) || raw.startsWith('//')) {
      try {
        const parsed = new URL(raw.startsWith('//') ? `${window.location.protocol}${raw}` : raw);
        return `${parsed.pathname}${parsed.search}${parsed.hash}` || fallback;
      } catch (_) {
        return fallback;
      }
    }
    return raw;
  };

  const navigateTo = (url) => {
    window.location.href = toAppRelativeUrl(url, '/');
  };

  const isMobileCardView = () => !!mobileListQuery.matches && Array.isArray(mobileCardCols) && mobileCardCols.length > 0;



  // Ajusta os botÃƒÆ’Ã‚Âµes do header (com guardas)
  if (btnFilterToggle) {
    btnFilterToggle.innerHTML = `<i class="fa fa-filter"></i><span>${escapeHtml(tr('common.filter'))}</span>`;
    btnFilterToggle.className = 'sz_button sz_button_ghost';
    btnFilterToggle.setAttribute('aria-label', tr('common.filter'));
  }
  if (btnSortToggle) {
    btnSortToggle.innerHTML = `<i class="fa fa-arrow-down-wide-short"></i><span>${escapeHtml(tr('common.sort'))}</span>`;
    btnSortToggle.className = 'sz_button sz_button_ghost';
    btnSortToggle.setAttribute('aria-label', tr('common.sort'));
  }
  if (btnNew) {
    btnNew.innerHTML = `<i class="fa fa-plus"></i><span>${escapeHtml(tr('common.new'))}</span>`;
    btnNew.className = 'sz_button sz_button_primary';
    btnNew.setAttribute('aria-label', tr('common.new'));
  }
  if (btnNewAttachment) {
    btnNewAttachment.innerHTML = `<i class="fa fa-paperclip"></i><span>${escapeHtml(tr('common.new_attachment'))}</span>`;
    btnNewAttachment.classList.add('btn-attach-custom');
    btnNewAttachment.setAttribute('aria-label', tr('common.new_attachment'));
  }
  // removido botão de anexo específico

  // garante que ficam juntos
  const header = document.querySelector('.dynamic-header'); if(header){ header.classList.add('d-flex','align-items-center'); }

  // ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã¢â‚¬Â¦Ãƒâ€šÃ‚Â¡ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€¦Ã‚Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚ÂÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã¢â‚¬Â¦Ãƒâ€šÃ‚Â¡ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€¦Ã‚Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â ICON-ONLY BUTTONS ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã¢â‚¬Â¦Ãƒâ€šÃ‚Â¡ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€¦Ã‚Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚ÂÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã¢â‚¬Â¦Ãƒâ€šÃ‚Â¡ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€¦Ã‚Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â¬ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â

  // 1) Sem permissÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â‚¬Å¾Ã‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€¦Ã‚Â¡ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â£o de consulta, aborta
  if (!userPerms.consultar) {
    alert(tr('dynamic_list.no_permission'));
    return;
  }

  const sanitizeBaseForm = (path) => {
    const base = path.startsWith('/') ? path : `/${path}`;
    return base.replace(/\/+$/, '');
  };

  const resolveFormUrl = (stamp = '') => {
    const upperTable = (tableName || '').toUpperCase();
    const appendMenuStamp = (url) => {
      if (!menuStamp) return url;
      const sep = url.includes('?') ? '&' : '?';
      return `${url}${sep}menustamp=${encodeURIComponent(menuStamp)}`;
    };
    if (upperTable === 'FT') {
      return appendMenuStamp(stamp ? `/faturacao/ft/${stamp}` : '/faturacao/ft/new');
    }
    if (upperTable === 'RS') {
      return appendMenuStamp(stamp ? `/reservas/rs/${stamp}` : '/reservas/rs/new');
    }
    if (tableForm) {
      const relativeForm = toAppRelativeUrl(tableForm, tableForm);
      const pref = relativeForm.startsWith('/') ? relativeForm : `/generic/${relativeForm}`;
      const base = sanitizeBaseForm(pref).toLowerCase(); // rotas registadas em minúsculas
      return appendMenuStamp(stamp ? `${base}/${stamp}` : `${base}/`);
    }
    return appendMenuStamp(`/generic/form/${tableName}/${stamp || ''}`);
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

  function getVisibleSortColumns() {
    const source = isMobileCardView() ? mobileCardCols : currentCols;
    return (Array.isArray(source) ? source : []).filter((col) => String(col?.name || '').trim());
  }

  function compareRowsByColumn(col, leftRow, rightRow, direction = 1) {
    if (!col) return 0;
    const fieldName = String(col.name || '').trim();
    const kind = String(col.tipo || '').trim().toUpperCase();
    const leftValue = leftRow?.[fieldName];
    const rightValue = rightRow?.[fieldName];
    let result = 0;
    switch (kind) {
      case 'INT':
      case 'DECIMAL':
        result = (Number(leftValue) || 0) - (Number(rightValue) || 0);
        break;
      case 'DATE':
        result = (new Date(leftValue).getTime() || 0) - (new Date(rightValue).getTime() || 0);
        break;
      case 'BIT':
        result = ((leftValue ? 1 : 0) - (rightValue ? 1 : 0));
        break;
      default:
        result = String(leftValue || '').localeCompare(String(rightValue || ''), 'pt', { sensitivity: 'base', numeric: true });
        break;
    }
    return result * (direction >= 0 ? 1 : -1);
  }

  function applyActiveSort() {
    if (!Array.isArray(dataRows) || !dataRows.length || !sortField) return;
    const col = getVisibleSortColumns().find((item) => String(item?.name || '') === String(sortField || ''));
    if (!col) return;
    dataRows.sort((leftRow, rightRow) => compareRowsByColumn(col, leftRow, rightRow, sortDir));
  }

  function renderSortOptions() {
    if (!sortFieldList) return;
    const cols = getVisibleSortColumns();
    if (!cols.length) {
      sortFieldList.innerHTML = `<div class="sz_text_muted">${escapeHtml(tr('dynamic_list.no_sort_fields'))}</div>`;
      return;
    }
    sortFieldList.innerHTML = cols.map((col) => {
      const fieldName = String(col?.name || '').trim();
      const active = fieldName && fieldName === String(pendingSortField || '');
      const direction = active && Number(pendingSortDir || 1) < 0 ? 'DESC' : 'ASC';
      const icon = active
        ? (direction === 'DESC' ? 'fa-arrow-down-wide-short' : 'fa-arrow-up-short-wide')
        : 'fa-minus';
      return `
        <button type="button" class="sz_button sz_button_ghost sz_dynamic_sort_option${active ? ' is-active' : ''}" data-sort-field="${escapeHtml(fieldName)}">
          <span class="sz_dynamic_sort_option_main">
            <span class="sz_dynamic_sort_option_label">${escapeHtml(col.descricao || fieldName)}</span>
            <span class="sz_dynamic_sort_option_hint">${escapeHtml(active ? tr('dynamic_list.sort_direction', { direction }) : tr('dynamic_list.sort_tap'))}</span>
          </span>
          <span class="sz_dynamic_sort_option_state" aria-hidden="true">
            <i class="fa-solid ${icon}"></i>
          </span>
        </button>
      `;
    }).join('');
  }

  function openSortModal() {
    if (!modalSort) return;
    pendingSortField = sortField;
    pendingSortDir = sortDir;
    renderSortOptions();
    document.body.classList.add('modal-sort-open');
    modalSort.classList.add('sz_is_open');
    modalSort.setAttribute('aria-hidden', 'false');
  }

  function closeSortModal() {
    if (!modalSort) return;
    modalSort.classList.remove('sz_is_open');
    modalSort.setAttribute('aria-hidden', 'true');
    document.body.classList.remove('modal-sort-open');
  }

  // Move o modal de filtros para <body> (fora de containers com overflow)
  if (modalFiltros) { document.body.appendChild(modalFiltros); }
  if (modalSort) { document.body.appendChild(modalSort); }

  // Botão Filtrar abre modal
  if (btnFilterToggle && modalFiltros) {
    btnFilterToggle.addEventListener('click', () => {
      openFiltersModal();
    });
  }
  if (btnSortToggle && modalSort) {
    btnSortToggle.addEventListener('click', () => {
      openSortModal();
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
  if (closeSortBtn) {
    closeSortBtn.addEventListener('click', closeSortModal);
  }
  if (closeSortTopBtn) {
    closeSortTopBtn.addEventListener('click', closeSortModal);
  }
  if (modalSort) {
    modalSort.addEventListener('click', (e) => {
      if (e.target === modalSort) {
        closeSortModal();
      }
    });
  }
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && modalFiltros && modalFiltros.classList.contains('sz_is_open')) {
      closeFiltersModal();
    }
    if (e.key === 'Escape' && modalSort && modalSort.classList.contains('sz_is_open')) {
      closeSortModal();
    }
  });

  if (sortFieldList) {
    sortFieldList.addEventListener('click', (event) => {
      const option = event.target.closest('[data-sort-field]');
      if (!option) return;
      const nextField = String(option.dataset.sortField || '').trim();
      if (!nextField) return;
      if (pendingSortField === nextField) {
        pendingSortDir = Number(pendingSortDir || 1) * -1;
      } else {
        pendingSortField = nextField;
        pendingSortDir = 1;
      }
      renderSortOptions();
    });
  }
  if (applySortBtn) {
    applySortBtn.addEventListener('click', () => {
      sortField = pendingSortField;
      sortDir = Number(pendingSortDir || 1) >= 0 ? 1 : -1;
      applyActiveSort();
      renderGrid();
      closeSortModal();
    });
  }

  if (btnNew) {
    btnNew.addEventListener('click', () => {
      navigateTo(withReturnTo(resolveFormUrl()));
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
        alert(tr('dynamic_list.attachment_error', { error: err.message }));
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

  const handleViewportModeChange = () => {
    if (!Array.isArray(dataRows) || !dataRows.length) {
      renderGrid();
      return;
    }
    renderGrid();
  };
  if (typeof mobileListQuery.addEventListener === 'function') {
    mobileListQuery.addEventListener('change', handleViewportModeChange);
  } else if (typeof mobileListQuery.addListener === 'function') {
    mobileListQuery.addListener(handleViewportModeChange);
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
        alert(tr('dynamic_list.attachment_error', { error: err.error || up.statusText }));
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
      const params = new URLSearchParams({
        action: 'describe',
        include_screen_meta: '1'
      });
      if (menuStamp) params.set('menustamp', menuStamp);
      const res = await fetch(`/generic/api/${tableName}?${params.toString()}`);
      if (!res.ok) throw new Error(res.statusText);
      const payload = await res.json();
      meta = Array.isArray(payload) ? payload : (Array.isArray(payload?.columns) ? payload.columns : []);
      listUseExactWidths = !!payload?.screen?.list_use_exact_widths;
    } catch (e) {
      console.error('Falha ao carregar metadados:', e);
      gridDiv.innerHTML = `<p class="text-danger">${escapeHtml(tr('dynamic_list.filters_load_error'))}</p>`;
      return;
    }
    // b) Separa colunas de filtros e de listagem
    const filterCols = meta.filter(c => c.filtro);
    currentCols      = meta
      .filter(c => c.lista)
      .sort((a, b) => {
        const orderDiff = (Number(a.ordem_lista || 0) - Number(b.ordem_lista || 0));
        if (orderDiff !== 0) return orderDiff;
        return Number(a.ordem || 0) - Number(b.ordem || 0);
      });
    mobileCardCols   = meta
      .filter(c => Number(c.ordem_lista_mobile || 0) > 0)
      .sort((a, b) => {
        const orderDiff = Number(a.ordem_lista_mobile || 0) - Number(b.ordem_lista_mobile || 0);
        if (orderDiff !== 0) return orderDiff;
        return Number(a.ordem_lista || 0) - Number(b.ordem_lista || 0);
      });

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
    filterForm.className = 'sz_dynamic_filters_form sz_dynamic_filters_form_mobile_2col';

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
        row.classList.add('sz_filter_date_range_row');

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
              const resp = await fetch(toAppRelativeUrl(col.combo, col.combo));
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
      cntEl.textContent = tr(n === 1 ? 'dynamic_list.record_count_one' : 'dynamic_list.record_count_other', { count: n });
    }
    if(cntEl){ const n = (dataRows||[]).length; cntEl.textContent = tr(n === 1 ? 'dynamic_list.record_count_one' : 'dynamic_list.record_count_other', { count: n }); }
    applyActiveSort();
    renderGrid();
  }

  function formatListValue(col, rawValue) {
    let value = rawValue;
    if (col?.tipo === 'DATE' && value) {
      const d = new Date(value);
      if (!isNaN(d)) {
        const dd = String(d.getDate()).padStart(2, '0');
        const mm = String(d.getMonth() + 1).padStart(2, '0');
        const yyyy = d.getFullYear();
        value = `${dd}.${mm}.${yyyy}`;
      }
    }
    if (col?.tipo === 'BIT') {
      return (value === 1 || value === '1' || value === true) ? 'Yes' : 'No';
    }
    return value ?? '';
  }

  function getDesktopListColWidth(col, colsList) {
    const width = Math.max(5, Number(col?.tam_lista || col?.tam || 5));
    if (listUseExactWidths) return `${width}%`;
    const total = (Array.isArray(colsList) ? colsList : []).reduce((acc, item) => (
      acc + Math.max(5, Number(item?.tam_lista || item?.tam || 5))
    ), 0) || 1;
    return `${(width / total) * 100}%`;
  }

  function getMobileCardColWidth(col, rowCols) {
    const width = Math.max(5, Number(col?.tam_lista_mobile || col?.tam_mobile || col?.tam_lista || col?.tam || 5));
    if (listUseExactWidths) return `${width}%`;
    const total = (Array.isArray(rowCols) ? rowCols : []).reduce((acc, item) => (
      acc + Math.max(5, Number(item?.tam_lista_mobile || item?.tam_mobile || item?.tam_lista || item?.tam || 5))
    ), 0) || 1;
    return `${(width / total) * 100}%`;
  }

  function getMobileCardRows(cols) {
    const groups = new Map();
    (Array.isArray(cols) ? cols : []).forEach((col) => {
      const order = Number(col?.ordem_lista_mobile || 0);
      if (order <= 0) return;
      const rowId = Math.max(1, Math.floor(order / 10));
      if (!groups.has(rowId)) groups.set(rowId, []);
      groups.get(rowId).push(col);
    });
    return [...groups.entries()]
      .sort((a, b) => a[0] - b[0])
      .map(([, rowCols]) => rowCols.sort((a, b) => Number(a?.ordem_lista_mobile || 0) - Number(b?.ordem_lista_mobile || 0)));
  }

  function renderGrid() {
    gridDiv.classList.toggle('is-mobile-cards', isMobileCardView());
    if (isMobileCardView()) {
      renderMobileCards(mobileCardCols, dataRows);
      return;
    }
    renderTable(currentCols, dataRows);
  }

  function renderTable(cols, rows) {
    gridDiv.innerHTML = '';
    const tableWrap = document.createElement('div');
    tableWrap.classList.add('sz_table_wrap');
    const table = document.createElement('table');
    table.classList.add('sz_table');
    table.style.width = '100%';
    table.style.tableLayout = 'fixed';

    const colgroup = document.createElement('colgroup');
    cols.forEach((c) => {
      const col = document.createElement('col');
      col.style.width = getDesktopListColWidth(c, cols);
      colgroup.append(col);
    });
    table.append(colgroup);

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
        applyActiveSort();
        renderGrid();
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
        const v = r[c.name];
        if (c.tipo==='BIT') {
          const isTrue = (v === 1 || v === '1' || v === true);
          td.innerHTML = isTrue ? '<i class="fa fa-check"></i>' : '';
        } else {
          td.textContent = formatListValue(c, v);
        }
        tr.append(td);
      });

      // clique abre ediÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â‚¬Å¾Ã‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€¦Ã‚Â¡ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â§ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Â ÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã‚Â ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬ÃƒÂ¢Ã¢â‚¬Å¾Ã‚Â¢ÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã‚Â¢ÃƒÂ¢Ã¢â‚¬Å¡Ã‚Â¬Ãƒâ€¦Ã‚Â¡ÃƒÆ’Ã†â€™ÃƒÂ¢Ã¢â€šÂ¬Ã…Â¡ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Â£o
      const pk = r[`${tableName.toUpperCase()}STAMP`];
      tr.addEventListener('click', () => {
        navigateTo(withReturnTo(resolveFormUrl(pk)));
      });
      tbody.append(tr);
    });
    table.append(tbody);
    tableWrap.append(table);
    gridDiv.append(tableWrap);
  }

  function renderMobileCards(cols, rows) {
    gridDiv.innerHTML = '';
    const host = document.createElement('div');
    host.className = 'sz_dynamic_list_cards';

    if (!Array.isArray(rows) || !rows.length) {
      host.innerHTML = `<div class="sz_card sz_dynamic_list_card sz_dynamic_list_card_empty"><div class="sz_text_muted">${escapeHtml(tr('dynamic_list.empty'))}</div></div>`;
      gridDiv.append(host);
      return;
    }

    const cardRows = getMobileCardRows(cols);
    rows.forEach((row) => {
      const pk = row[`${tableName.toUpperCase()}STAMP`];
      const card = document.createElement('article');
      card.className = 'sz_card sz_dynamic_list_card';
      card.tabIndex = 0;

      cardRows.forEach((rowCols) => {
        const cardRow = document.createElement('div');
        cardRow.className = 'sz_dynamic_list_card_row';
        rowCols.forEach((col) => {
          const cell = document.createElement('div');
          cell.className = 'sz_dynamic_list_card_cell';
          cell.style.flex = `0 0 ${getMobileCardColWidth(col, rowCols)}`;
          cell.style.maxWidth = getMobileCardColWidth(col, rowCols);

          const showLabel = col.lista_mobile_show_label !== false;
          const labelText = String(col.lista_mobile_label || col.descricao || col.name || '').trim();
          const valueText = String(formatListValue(col, row[col.name]) || '').trim();

          if (showLabel && labelText) {
            const label = document.createElement('div');
            label.className = 'sz_dynamic_list_card_label';
            label.textContent = labelText;
            cell.append(label);
          }

          const value = document.createElement('div');
          value.className = 'sz_dynamic_list_card_value';
          if (col.lista_mobile_bold) value.classList.add('is-bold');
          if (col.lista_mobile_italic) value.classList.add('is-italic');
          if (col.tipo === 'BIT') {
            value.innerHTML = valueText === 'Yes'
              ? '<i class="fa fa-check"></i>'
              : '<span class="sz_text_muted">No</span>';
          } else {
            value.textContent = valueText || ' ';
          }
          cell.append(value);
          cardRow.append(cell);
        });
        card.append(cardRow);
      });

      card.addEventListener('click', () => {
        navigateTo(withReturnTo(resolveFormUrl(pk)));
      });
      card.addEventListener('keydown', (event) => {
        if (event.key !== 'Enter' && event.key !== ' ') return;
        event.preventDefault();
        navigateTo(withReturnTo(resolveFormUrl(pk)));
      });
      host.append(card);
    });

    gridDiv.append(host);
  }

});
