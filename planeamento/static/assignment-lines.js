(function () {
    function parsePlanLines(value) {
        if (!value) {
            return null;
        }
        var trimmed = value.trim();
        if (!trimmed) {
            return [];
        }
        try {
            var parsed = JSON.parse(trimmed);
            return Array.isArray(parsed) ? parsed : [];
        } catch (err) {
            return [];
        }
    }

    function ensureIcon(chip) {
        var icon = chip.querySelector('.assignment-chip-icon');
        if (!icon) {
            icon = document.createElement('span');
            icon.className = 'assignment-chip-icon';
            icon.setAttribute('aria-hidden', 'true');
            chip.insertBefore(icon, chip.firstChild);
        }
        return icon;
    }

    function removeIcon(chip) {
        var icon = chip.querySelector('.assignment-chip-icon');
        if (icon && icon.parentNode === chip) {
            chip.removeChild(icon);
        }
    }

    function createDefaultState() {
        return {
            allClosed: false,
            anyMismatch: false,
            allMatched: false,
        };
    }

    function normalizePlanKey(value) {
        return String(value || '').toUpperCase().trim();
    }

    function coerceBoolean(value) {
        if (typeof value === 'boolean') {
            return value;
        }
        if (typeof value === 'number') {
            return Number(value) !== 0;
        }
        if (typeof value === 'string') {
            var trimmed = value.trim().toLowerCase();
            return trimmed === '1' || trimmed === 'true';
        }
        return false;
    }

    function toNumber(value) {
        var num = Number(value);
        return typeof num === 'number' && !isNaN(num) ? num : 0;
    }

    function hasQuantities(values) {
        return values.some(function (value) {
            return Math.abs(value) > 0.000001;
        });
    }

    function valuesApproxEqual(a, b) {
        var diff = Math.abs(a - b);
        if (diff < 0.000001) {
            return true;
        }
        var scale = Math.max(1, Math.abs(a), Math.abs(b));
        return diff / scale < 0.0001;
    }

    var __planStateCache = new Map();

    function fetchProductionState(planStamp) {
        var key = normalizePlanKey(planStamp);
        if (!key) {
            return Promise.resolve(createDefaultState());
        }
        if (__planStateCache.has(key)) {
            return __planStateCache.get(key);
        }
        var promise = fetch('/api/plans/' + encodeURIComponent(key) + '/production-records', { headers: { 'Accept': 'application/json' } })
            .then(function (res) { return res.ok ? res.json() : []; })
            .then(function (rows) {
                if (!Array.isArray(rows) || !rows.length) {
                    return createDefaultState();
                }
                var state = createDefaultState();
                var hasRows = false;
                var closedAll = true;
                var mismatchFound = false;
                var headerCount = 0;
                var matchedCount = 0;

                rows.forEach(function (row) {
                    if (!row) {
                        return;
                    }
                    hasRows = true;
                    if (!coerceBoolean(row.fechado)) {
                        closedAll = false;
                    }

                    var headerValues = [
                        toNumber(row.qtt),
                        toNumber(row.kgferro),
                        toNumber(row.m2serragem),
                    ];

                    if (!hasQuantities(headerValues)) {
                        return;
                    }

                    headerCount += 1;

                    var lineValues = [
                        toNumber(row.lines_qtt_total),
                        toNumber(row.lines_kgferro_total),
                        toNumber(row.lines_m2serragem_total),
                    ];

                    var matches = headerValues.every(function (value, idx) {
                        return valuesApproxEqual(value, lineValues[idx]);
                    });

                    if (matches) {
                        matchedCount += 1;
                    } else {
                        mismatchFound = true;
                    }
                });

                state.allClosed = hasRows ? closedAll : false;
                state.anyMismatch = mismatchFound;
                state.allMatched = !mismatchFound && headerCount > 0 && matchedCount === headerCount;
                return state;
            })
            .catch(function () {
                return createDefaultState();
            });

        __planStateCache.set(key, promise);
        return promise;
    }

    function applyIconState(icon, state) {
        if (!icon) {
            return;
        }
        var mismatch = Boolean(state && state.anyMismatch);
        var closed = Boolean(state && state.allClosed) && !mismatch;
        var fulfilled = Boolean(state && state.allMatched) && !mismatch && !closed;

        icon.classList.toggle('is-mismatch', mismatch);
        icon.classList.toggle('is-closed', closed);
        icon.classList.toggle('is-fulfilled', fulfilled);
    }

    function updateChipStatus(chip) {
        if (!chip || !chip.classList.contains('has-lines')) {
            return;
        }
        var icon = ensureIcon(chip);
        var planStamp = chip.dataset.planStamp || chip.getAttribute('data-plan-stamp') || '';
        fetchProductionState(planStamp).then(function (state) {
            applyIconState(icon, state);
        });
    }

    function updateChip(chip) {
        if (!chip) {
            return;
        }
        var planLinesValue = chip.dataset.planLines;
        var parsed = parsePlanLines(planLinesValue);
        var hasLines;
        if (parsed === null) {
            hasLines = chip.classList.contains('has-lines');
        } else {
            hasLines = parsed.length > 0;
        }
        chip.classList.toggle('has-lines', hasLines);
        if (hasLines) {
            ensureIcon(chip);
            updateChipStatus(chip);
        } else {
            removeIcon(chip);
        }
    }

    function observeChip(chip, observer) {
        if (!chip) {
            return;
        }
        updateChip(chip);
        observer.observe(chip, { attributes: true, attributeFilter: ['data-plan-lines'] });
    }

    function initAssignmentIndicators() {
        var chips = document.querySelectorAll('.assignment-chip[data-plan-stamp]');
        if (!chips.length) {
            return;
        }

        var attributeObserver = new MutationObserver(function (mutations) {
            mutations.forEach(function (mutation) {
                if (mutation.type === 'attributes') {
                    updateChip(mutation.target);
                    updateChipStatus(mutation.target);
                }
            });
        });

        chips.forEach(function (chip) {
            observeChip(chip, attributeObserver);
        });

        var table = document.querySelector('.planning-table');
        if (!table) {
            return;
        }

        var additionObserver = new MutationObserver(function (mutations) {
            mutations.forEach(function (mutation) {
                mutation.addedNodes.forEach(function (node) {
                    if (!(node instanceof Element)) {
                        return;
                    }
                    if (node.matches('.assignment-chip[data-plan-stamp]')) {
                        observeChip(node, attributeObserver);
                        updateChipStatus(node);
                    }
                    if (node.querySelectorAll) {
                        node.querySelectorAll('.assignment-chip[data-plan-stamp]').forEach(function (chip) {
                            observeChip(chip, attributeObserver);
                            updateChipStatus(chip);
                        });
                    }
                });
            });
        });

        additionObserver.observe(table, { childList: true, subtree: true });
    }

    function invalidatePlanState(planStamp) {
        var key = normalizePlanKey(planStamp);
        if (!key) {
            return;
        }
        try {
            __planStateCache.delete(key);
        } catch (err) {
            /* ignore */
        }
        var chips = document.querySelectorAll('.assignment-chip[data-plan-stamp]');
        chips.forEach(function (chip) {
            var chipKey = normalizePlanKey(chip.dataset.planStamp || chip.getAttribute('data-plan-stamp') || '');
            if (chipKey === key) {
                updateChipStatus(chip);
            }
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initAssignmentIndicators);
    } else {
        initAssignmentIndicators();
    }

    window.addEventListener('planning:production-updated', function (event) {
        var detail = event && event.detail;
        var plan = detail && (detail.planStamp || detail.plan_stamp) || '';
        invalidatePlanState(plan);
    });
})();
