(function () {
    function computeSnapshot(form) {
        var parts = [];
        var elements = form.elements;
        for (var i = 0; i < elements.length; i += 1) {
            var element = elements[i];
            if (!element || element.disabled) {
                continue;
            }
            var name = element.name;
            if (!name) {
                continue;
            }
            var type = (element.type || '').toLowerCase();
            if (type === 'submit' || type === 'button') {
                continue;
            }
            if (type === 'checkbox' || type === 'radio') {
                parts.push(name + ':' + element.value + '=' + (element.checked ? '1' : '0'));
            } else {
                parts.push(name + '=' + element.value);
            }
        }
        return parts.join('&');
    }

    function initFiltersState() {
        var filtersArea = document.querySelector('[data-filters-area]');
        if (!filtersArea) {
            return;
        }
        var form = filtersArea.querySelector('.filters-form');
        if (!form) {
            return;
        }
        var submitButton = form.querySelector('.filters-submit');
        if (!submitButton) {
            return;
        }

        var initialSnapshot = computeSnapshot(form);

        function updateButtonState() {
            var isDirty = computeSnapshot(form) !== initialSnapshot;
            if (isDirty) {
                submitButton.disabled = false;
            } else {
                submitButton.disabled = true;
            }
        }

        submitButton.disabled = true;

        var handleMutate = function () {
            updateButtonState();
        };

        form.addEventListener('input', handleMutate, true);
        form.addEventListener('change', handleMutate, true);

        form.addEventListener('submit', function () {
            submitButton.disabled = true;
            initialSnapshot = computeSnapshot(form);
        });

        updateButtonState();
    }

    function initAppMenuState() {
        var menu = document.querySelector('[data-app-menu]');
        if (!menu) {
            return;
        }
        var toggle = menu.querySelector('.app-menu-toggle');

        function updateState() {
            var isEditing = document.body.classList.contains('editing-active');
            if (isEditing) {
                menu.classList.add('is-disabled');
                menu.removeAttribute('open');
                if (toggle) {
                    toggle.setAttribute('aria-disabled', 'true');
                }
            } else {
                menu.classList.remove('is-disabled');
                if (toggle) {
                    toggle.removeAttribute('aria-disabled');
                }
            }
        }

        updateState();

        var observer = new MutationObserver(function (records) {
            for (var i = 0; i < records.length; i += 1) {
                if (records[i].attributeName === 'class') {
                    updateState();
                    break;
                }
            }
        });
        observer.observe(document.body, { attributes: true, attributeFilter: ['class'] });

        menu.addEventListener('toggle', function () {
            if (menu.hasAttribute('open') && menu.classList.contains('is-disabled')) {
                menu.removeAttribute('open');
            }
        });
    }

    function init() {
        initFiltersState();
        initAppMenuState();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
