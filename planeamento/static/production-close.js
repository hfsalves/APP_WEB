(function () {
    function normalizePlanStamp(value) {
        return (value || '').toString().trim().toUpperCase();
    }

    function dispatchPlanUpdates(planStamps) {
        if (!Array.isArray(planStamps) || !planStamps.length) {
            return;
        }
        planStamps.forEach(function (stamp) {
            var normalized = normalizePlanStamp(stamp);
            if (!normalized) {
                return;
            }
            window.dispatchEvent(new CustomEvent('planning:production-updated', {
                detail: { planStamp: normalized }
            }));
        });
    }

    var toastContainer;

    function ensureToastContainer() {
        if (toastContainer && document.body.contains(toastContainer)) {
            return toastContainer;
        }
        toastContainer = document.createElement('div');
        toastContainer.className = 'toast-container';
        document.body.appendChild(toastContainer);
        return toastContainer;
    }

    function showToast(message, isError) {
        if (!message) {
            return;
        }
        var container = ensureToastContainer();
        var toast = document.createElement('div');
        toast.className = 'toast';
        if (isError) {
            toast.classList.add('is-error');
        }
        toast.textContent = message;
        container.appendChild(toast);
        requestAnimationFrame(function () {
            toast.classList.add('is-visible');
        });
        setTimeout(function () {
            toast.classList.remove('is-visible');
            setTimeout(function () {
                if (toast.parentNode) {
                    toast.parentNode.removeChild(toast);
                }
            }, 300);
        }, 4000);
    }

    document.addEventListener('DOMContentLoaded', function () {
        var button = document.querySelector('[data-production-close]');
        if (!button) {
            return;
        }

        var defaultLabel = button.textContent.trim();
        var loadingLabel = button.getAttribute('data-loading-text') || defaultLabel;
        var successTemplate = button.getAttribute('data-success-text') || '';
        var errorTemplate = button.getAttribute('data-error-text') || '';
        var missingWeekMessage = button.getAttribute('data-week-missing-text') || '';
        var emptyMessage = button.getAttribute('data-empty-text') || '';
        var confirmMessage = button.getAttribute('data-confirm-text') || '';

        function getWeekRange() {
            var root = document.body;
            var start = root ? (root.dataset.weekStart || '') : '';
            var end = root ? (root.dataset.weekEnd || '') : '';
            return { start: start, end: end };
        }

        function formatSuccess(count) {
            if (!successTemplate) {
                return '';
            }
            return successTemplate.replace('{count}', count);
        }

        function handleResult(result) {
            var count = Number(result.closed || 0);
            if (count > 0) {
                var message = formatSuccess(count);
                showToast(message || successTemplate || '', false);
                dispatchPlanUpdates(result.plans);
            } else {
                showToast(emptyMessage || successTemplate || '', false);
            }
        }

        function handleError(fallbackMessage) {
            var message = fallbackMessage || errorTemplate || '';
            showToast(message, true);
        }

        button.addEventListener('click', function (event) {
            event.preventDefault();
            if (button.disabled) {
                return;
            }
            if (confirmMessage && !window.confirm(confirmMessage)) {
                return;
            }
            var range = getWeekRange();
            if (!range.start || !range.end) {
                handleError(missingWeekMessage);
                return;
            }

            button.disabled = true;
            button.textContent = loadingLabel;

            fetch('/api/production/close-week', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ week_start: range.start, week_end: range.end })
            }).then(function (response) {
                return response.json().catch(function () { return {}; }).then(function (data) {
                    return { ok: response.ok, status: response.status, data: data };
                });
            }).then(function (result) {
                if (result.ok) {
                    handleResult(result.data || {});
                } else {
                    var serverMessage = (result.data && result.data.details) || errorTemplate;
                    handleError(serverMessage);
                }
            }).catch(function () {
                handleError(errorTemplate);
            }).finally(function () {
                button.disabled = false;
                button.textContent = defaultLabel;
            });
        });
    });
})();
