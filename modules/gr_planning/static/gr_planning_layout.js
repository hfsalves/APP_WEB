(function () {
  const observedHosts = new WeakSet();

  function applyButtonTheme(button, variants) {
    if (!button) {
      return;
    }
    button.classList.add('sz_button');
    ['sz_button_primary', 'sz_button_secondary', 'sz_button_ghost', 'sz_button_danger'].forEach((className) => {
      button.classList.remove(className);
    });
    variants.forEach((className) => button.classList.add(className));
  }

  function applyPlanningContextLayout() {
    const host = document.querySelector('[data-gr-planning-host]');
    const contextHost = document.querySelector('[data-gr-planning-context-host]');
    if (!host || !contextHost) {
      return;
    }

    const filtersLayout = host.querySelector('.filters-layout');
    if (!filtersLayout) {
      return;
    }

    const filtersCard = filtersLayout.querySelector('.filters-card');
    const filtersForm = filtersLayout.querySelector('.filters-form');
    const productionCard = filtersLayout.querySelector('.production-control-card');
    const dbError = filtersLayout.querySelector('.error');

    if (filtersForm && !contextHost.contains(filtersForm)) {
      contextHost.appendChild(filtersForm);
      filtersForm.classList.add('gr-planning-context-form');
    }

    if (filtersForm && contextHost.contains(filtersForm)) {
      contextHost.setAttribute('data-filters-area', '');
      if (filtersCard && filtersCard.hasAttribute('data-filters-area')) {
        filtersCard.removeAttribute('data-filters-area');
      }
    }

    const weekInput = contextHost.querySelector('#week-picker');
    if (weekInput) {
      weekInput.setAttribute('aria-label', 'Semana');
      weekInput.setAttribute('title', 'Semana');
    }

    const marketSummary = contextHost.querySelector('.filter-control.filter-markets summary');
    if (marketSummary) {
      marketSummary.setAttribute('aria-label', 'Mercados');
      marketSummary.setAttribute('title', 'Mercados');
    }

    const typeSummary = contextHost.querySelector('.filter-control.filter-types summary');
    if (typeSummary) {
      typeSummary.setAttribute('aria-label', 'Tipo');
      typeSummary.setAttribute('title', 'Tipo');
    }

    contextHost.querySelectorAll('.week-nav-button').forEach((button) => {
      applyButtonTheme(button, ['sz_button_ghost']);
    });

    const submitButton = contextHost.querySelector('.filters-submit');
    if (submitButton) {
      applyButtonTheme(submitButton, ['sz_button_secondary']);
    }

    if (productionCard && !contextHost.contains(productionCard)) {
      const productionButton = productionCard.querySelector('.production-close-button');
      if (productionButton) {
        const filterActions = contextHost.querySelector('.filter-actions');
        if (filterActions) {
          filterActions.appendChild(productionButton);
        } else {
          contextHost.appendChild(productionButton);
        }
      } else {
        contextHost.appendChild(productionCard);
      }
    }

    const productionButton = contextHost.querySelector('.production-close-button');
    if (productionButton) {
      applyButtonTheme(productionButton, ['sz_button_primary']);
    }

    if (dbError) {
      dbError.remove();
    }

    if (filtersForm && contextHost.contains(filtersForm)) {
      filtersLayout.classList.add('gr-planning-context-migrated');
      if (filtersCard) {
        filtersCard.remove();
      }
      if (productionCard && !contextHost.contains(productionCard)) {
        productionCard.remove();
      }
    } else {
      filtersLayout.classList.remove('gr-planning-context-migrated');
    }
  }

  function applyTeamManagementContextLayout() {
    const host = document.querySelector('[data-gr-team-management-host]');
    const contextHost = document.querySelector('[data-gr-team-management-context-host]');
    if (!host || !contextHost) {
      return;
    }

    const filtersCard = host.querySelector('.filters-card');
    if (!filtersCard) {
      return;
    }

    const filtersForm = filtersCard.querySelector('.filters-form');
    if (filtersForm && !contextHost.contains(filtersForm)) {
      contextHost.appendChild(filtersForm);
      filtersForm.classList.add('gr-team-management-context-form');
    }

    if (filtersForm && contextHost.contains(filtersForm)) {
      contextHost.setAttribute('data-filters-area', '');
      if (filtersCard.hasAttribute('data-filters-area')) {
        filtersCard.removeAttribute('data-filters-area');
      }
    }

    const referenceDateInput = contextHost.querySelector('#date-filter');
    if (referenceDateInput) {
      referenceDateInput.setAttribute('aria-label', 'Data de referencia');
      referenceDateInput.setAttribute('title', 'Data de referencia');
    }

    const submitButton = contextHost.querySelector('.filters-submit');
    if (submitButton) {
      applyButtonTheme(submitButton, ['sz_button_secondary']);
    }

    contextHost.querySelectorAll('.table-export-button').forEach((button) => {
      applyButtonTheme(button, ['sz_button_ghost']);
    });

    if (filtersForm && contextHost.contains(filtersForm)) {
      filtersCard.remove();
    }
  }

  function applyMonthlySheetContextLayout() {
    const host = document.querySelector('[data-gr-monthly-sheet-host]');
    const contextHost = document.querySelector('[data-gr-monthly-context-host]');
    if (!host || !contextHost) {
      return;
    }

    const filtersLayout = host.querySelector('.filters-layout');
    if (!filtersLayout) {
      return;
    }

    const filtersCard = filtersLayout.querySelector('.filters-card');
    const filtersForm = filtersLayout.querySelector('.filters-form');

    if (filtersForm && !contextHost.contains(filtersForm)) {
      contextHost.appendChild(filtersForm);
      filtersForm.classList.add('gr-monthly-context-form');
    }

    if (filtersForm && contextHost.contains(filtersForm)) {
      contextHost.setAttribute('data-filters-area', '');
      if (filtersCard && filtersCard.hasAttribute('data-filters-area')) {
        filtersCard.removeAttribute('data-filters-area');
      }
    }

    const monthInput = contextHost.querySelector('#month-filter');
    if (monthInput) {
      monthInput.setAttribute('aria-label', 'Mes');
      monthInput.setAttribute('title', 'Mes');
    }

    const teamSummary = contextHost.querySelector('.filter-control.filter-teams summary');
    if (teamSummary) {
      teamSummary.setAttribute('aria-label', 'Equipas');
      teamSummary.setAttribute('title', 'Equipas');
    }

    const submitButton = contextHost.querySelector('.filters-submit');
    if (submitButton) {
      applyButtonTheme(submitButton, ['sz_button_secondary']);
    }

    if (filtersForm && contextHost.contains(filtersForm)) {
      filtersLayout.classList.add('gr-monthly-context-migrated');
      if (filtersCard) {
        filtersCard.remove();
      }
    } else {
      filtersLayout.classList.remove('gr-monthly-context-migrated');
    }
  }

  function applyMonthlySheetIntersolContextLayout() {
    const host = document.querySelector('[data-gr-monthly-intersol-host]');
    const contextHost = document.querySelector('[data-gr-monthly-intersol-context-host]');
    if (!host || !contextHost) {
      return;
    }

    const filtersLayout = host.querySelector('.filters-layout');
    if (!filtersLayout) {
      return;
    }

    const filtersCard = filtersLayout.querySelector('.filters-card');
    const filtersForm = filtersLayout.querySelector('.filters-form');

    if (filtersForm && !contextHost.contains(filtersForm)) {
      contextHost.appendChild(filtersForm);
      filtersForm.classList.add('gr-monthly-intersol-context-form');
    }

    if (filtersForm && contextHost.contains(filtersForm)) {
      contextHost.setAttribute('data-filters-area', '');
      if (filtersCard && filtersCard.hasAttribute('data-filters-area')) {
        filtersCard.removeAttribute('data-filters-area');
      }
    }

    const monthInput = contextHost.querySelector('#month-filter');
    if (monthInput) {
      monthInput.setAttribute('aria-label', 'Mes');
      monthInput.setAttribute('title', 'Mes');
    }

    const teamSummary = contextHost.querySelector('.filter-control.filter-teams summary');
    if (teamSummary) {
      teamSummary.setAttribute('aria-label', 'Equipas');
      teamSummary.setAttribute('title', 'Equipas');
    }

    const submitButton = contextHost.querySelector('.filters-submit');
    if (submitButton) {
      applyButtonTheme(submitButton, ['sz_button_secondary']);
    }

    if (filtersForm && contextHost.contains(filtersForm)) {
      filtersLayout.classList.add('gr-monthly-intersol-context-migrated');
      if (filtersCard) {
        filtersCard.remove();
      }
    } else {
      filtersLayout.classList.remove('gr-monthly-intersol-context-migrated');
    }
  }

  function applyLayouts() {
    applyPlanningContextLayout();
    applyTeamManagementContextLayout();
    applyMonthlySheetContextLayout();
    applyMonthlySheetIntersolContextLayout();
  }

  function startLayoutObserver(hostSelector) {
    const host = document.querySelector(hostSelector);
    if (!host || observedHosts.has(host)) {
      return;
    }

    observedHosts.add(host);
    const observer = new MutationObserver(() => {
      applyLayouts();
    });

    observer.observe(host, {
      childList: true,
      subtree: true,
    });
  }

  function init() {
    applyLayouts();
    startLayoutObserver('[data-gr-planning-host]');
    startLayoutObserver('[data-gr-team-management-host]');
    startLayoutObserver('[data-gr-monthly-sheet-host]');
    startLayoutObserver('[data-gr-monthly-intersol-host]');
    window.setTimeout(applyLayouts, 0);
    window.setTimeout(applyLayouts, 150);
    window.setTimeout(applyLayouts, 500);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
