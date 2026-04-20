(function () {
    function normalizeText(value) {
        return String(value || '')
            .normalize('NFD')
            .replace(/[\u0300-\u036f]/g, '')
            .toLowerCase()
            .trim();
    }

    function initPlanningProjectFilter() {
        var input = document.querySelector('[data-project-search-input]');
        var table = document.querySelector('.planning-table');
        if (!input || !table) {
            return;
        }

        var tbody = table.querySelector('tbody');
        var rows = Array.prototype.slice.call(table.querySelectorAll('[data-project-search-row]'));
        if (!tbody || !rows.length) {
            return;
        }

        var emptyRow = document.createElement('tr');
        emptyRow.setAttribute('data-project-search-empty', '1');
        emptyRow.hidden = true;

        var emptyCell = document.createElement('td');
        emptyCell.className = 'empty-cell';
        emptyCell.colSpan = rows[0].children ? rows[0].children.length : 8;
        emptyCell.textContent = 'Sem obras para a pesquisa.';
        emptyRow.appendChild(emptyCell);
        tbody.appendChild(emptyRow);

        function updateFilter() {
            var searchValue = normalizeText(input.value);
            var visibleCount = 0;

            rows.forEach(function (row) {
                var haystack = normalizeText(row.dataset.projectSearch || '');
                var isVisible = !searchValue || haystack.indexOf(searchValue) !== -1;
                row.hidden = !isVisible;
                if (isVisible) {
                    visibleCount += 1;
                }
            });

            emptyRow.hidden = visibleCount !== 0;
        }

        input.addEventListener('input', updateFilter);
        updateFilter();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initPlanningProjectFilter);
    } else {
        initPlanningProjectFilter();
    }
})();
