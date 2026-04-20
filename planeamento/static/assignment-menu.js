(function () {
    function ready(fn) {
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', fn);
        } else {
            fn();
        }
    }

    function clamp(value, min, max) {
        return Math.min(Math.max(value, min), max);
    }

    ready(function () {
        var planningTable = document.querySelector('.planning-table');
        if (!planningTable) {
            return;
        }

        var assignLabel = planningTable.dataset.chipMenuAssign || 'Work assignment';
        var productionLabel = planningTable.dataset.chipMenuProduction || 'Production records';
        var otherLabel = planningTable.dataset.chipMenuOther || 'Outras opções';
        var isPlanningAdminValue = (planningTable.dataset.isAdmin || '').toString().toLowerCase();
        var isPlanningAdmin = isPlanningAdminValue === '1' || isPlanningAdminValue === 'true';
        var productionModal = document.getElementById('production-modal');
        var productionDialog = productionModal ? productionModal.querySelector('.modal-dialog') : null;
        var productionCloseButtons = productionModal ? productionModal.querySelectorAll('[data-production-close]') : [];
        var productionForm = productionModal ? productionModal.querySelector('[data-production-form]') : null;
        var productionFields = {
            fref: productionForm ? productionForm.querySelector('[data-production-field="fref"]') : null,
            processo: productionForm ? productionForm.querySelector('[data-production-field="processo"]') : null,
            data: productionForm ? productionForm.querySelector('[data-production-field="data"]') : null,
            litem: productionForm ? productionForm.querySelector('[data-production-field="litem"]') : null,
            acabamento: productionForm ? productionForm.querySelector('[data-production-field="acabamento"]') : null,
            dgeral: productionForm ? productionForm.querySelector('[data-production-field="dgeral"]') : null,
            qtt: productionForm ? productionForm.querySelector('[data-production-field="qtt"]') : null,
            m3bomba: productionForm ? productionForm.querySelector('[data-production-field="m3bomba"]') : null,
            m2serragem: productionForm ? productionForm.querySelector('[data-production-field="m2serragem"]') : null,
            kgferro: productionForm ? productionForm.querySelector('[data-production-field="kgferro"]') : null,
            m3betao: productionForm ? productionForm.querySelector('[data-production-field="m3betao"]') : null
        };

        var decimalFieldNames = ['qtt', 'm2serragem', 'kgferro', 'm3betao', 'm3bomba'];
        var decimalFieldMap = {};
        var productionLineComparisonFields = ['qtt', 'kgferro', 'm2serragem'];
        var productionLineEditableFields = ['qtt', 'kgferro', 'm2serragem', 'u_prime'];
        var productionLineFieldDecimalPlaces = {
            qtt: 3,
            kgferro: 3,
            m2serragem: 3,
            u_prime: 2
        };
        var productionLineTotals = null;
        var productionLineData = [];
        decimalFieldNames.forEach(function (name) {
            decimalFieldMap[name] = true;
        });
        var otherOptionsFields = [];

        function formatDecimalValue(value, decimalPlaces) {
            if (value === undefined || value === null) {
                return '';
            }
            var places = typeof decimalPlaces === 'number' && decimalPlaces >= 0 ? decimalPlaces : 2;
            var sanitized = sanitizeDecimalInput(value, places);
            if (!sanitized) {
                return '';
            }
            var parsed = parseFloat(sanitized);
            if (!isFinite(parsed)) {
                return '';
            }
            return parsed.toFixed(places);
        }

        function sanitizeDecimalInput(rawValue, maxDecimals) {
            if (rawValue === undefined || rawValue === null) {
                return '';
            }
            var value = typeof rawValue === 'string' ? rawValue : String(rawValue);
            value = value.replace(',', '.');
            var result = '';
            var hasDecimal = false;
            for (var i = 0; i < value.length; i += 1) {
                var ch = value.charAt(i);
                if (ch >= '0' && ch <= '9') {
                    result += ch;
                    continue;
                }
                if (ch === '.' && !hasDecimal) {
                    result += '.';
                    hasDecimal = true;
                }
            }
            if (!hasDecimal) {
                return result;
            }
            var parts = result.split('.');
            var decimals = parts.length > 1 ? parts[1] : '';
            var limit = typeof maxDecimals === 'number' && maxDecimals >= 0 ? maxDecimals : 2;
            if (decimals.length > limit) {
                decimals = decimals.slice(0, limit);
            }
            return limit === 0 ? parts[0] : parts[0] + '.' + decimals;
        }

        function applyDecimalMask(field) {
            if (!field) {
                return;
            }
            var decimalPlacesAttr = field.getAttribute('data-decimal-places') || (field.dataset ? field.dataset.decimalPlaces : '');
            var decimalPlaces = parseInt(decimalPlacesAttr, 10);
            if (!Number.isFinite(decimalPlaces) || decimalPlaces < 0) {
                decimalPlaces = 2;
            }
            field.addEventListener('keydown', function (event) {
                var key = event.key;
                if (key !== ',' && key !== '.' && key !== 'Decimal') {
                    return;
                }
                var rawValue = field.value || '';
                if (!rawValue.length) {
                    return;
                }
                var normalizedValue = sanitizeDecimalInput(rawValue, decimalPlaces);
                if (normalizedValue !== rawValue) {
                    rawValue = normalizedValue;
                    field.value = normalizedValue;
                }
                var selectionStart = typeof field.selectionStart === 'number' ? field.selectionStart : null;
                var selectionEnd = typeof field.selectionEnd === 'number' ? field.selectionEnd : selectionStart;
                if (selectionStart === null || selectionEnd === null) {
                    return;
                }
                var decimalIndex = rawValue.indexOf('.');
                var displayDecimalIndex = rawValue.indexOf('.');
                if (displayDecimalIndex === -1) {
                    displayDecimalIndex = rawValue.indexOf(',');
                }
                if (displayDecimalIndex === -1) {
                    displayDecimalIndex = decimalIndex;
                }
                if (decimalIndex === -1) {
                    event.preventDefault();
                    var prefix = rawValue.slice(0, selectionStart).replace(/[^0-9]/g, '');
                    var suffix = rawValue.slice(selectionEnd).replace(/[^0-9]/g, '');
                    var composed = prefix + '.' + suffix;
                    var sanitizedComposed = sanitizeDecimalInput(composed, decimalPlaces);
                    field.value = sanitizedComposed;
                    if (field.setSelectionRange) {
                        var caretForInsert = sanitizedComposed.indexOf('.');
                        if (caretForInsert === -1) {
                            caretForInsert = sanitizedComposed.length;
                        } else {
                            caretForInsert += 1;
                        }
                        field.setSelectionRange(caretForInsert, caretForInsert);
                    }
                    return;
                }
                if (selectionStart <= displayDecimalIndex) {
                    event.preventDefault();
                    var integerPart = rawValue.slice(0, selectionStart).replace(/[^0-9]/g, '');
                    var decimals = rawValue.slice(decimalIndex + 1);
                    var recomposed = integerPart;
                    if (decimals.length) {
                        recomposed += '.' + decimals;
                    }
                    var sanitizedRecomposed = sanitizeDecimalInput(recomposed, decimalPlaces);
                    field.value = sanitizedRecomposed;
                    if (field.setSelectionRange) {
                        var caretIndex = sanitizedRecomposed.indexOf('.');
                        if (caretIndex === -1) {
                            caretIndex = sanitizedRecomposed.length;
                        } else {
                            caretIndex += 1;
                        }
                        field.setSelectionRange(caretIndex, caretIndex);
                    }
                }
            });
            field.addEventListener('input', function () {
                var previous = field.value || '';
                var sanitized = sanitizeDecimalInput(previous, decimalPlaces);
                if (sanitized !== previous) {
                    field.value = sanitized;
                    if (field.setSelectionRange && document.activeElement === field) {
                        var caret = sanitized.length;
                        field.setSelectionRange(caret, caret);
                    }
                }
            });
            field.addEventListener('blur', function () {
                field.value = formatDecimalValue(field.value, decimalPlaces);
            });
        }

        function debugLog(label, payload) {
            if (typeof console === 'undefined' || !console || typeof console.log !== 'function') {
                return;
            }
            try {
                console.log('[other-options]', label, payload || '');
            } catch (err) {
                /* ignore console errors */
            }
        }

        decimalFieldNames.forEach(function (name) {
            applyDecimalMask(productionFields[name]);
        });

        productionLineComparisonFields.forEach(function (name) {
            var field = productionFields[name];
            if (!field) {
                return;
            }
            field.addEventListener('input', updateProductionFieldComparisons);
            field.addEventListener('blur', updateProductionFieldComparisons);
        });

        var productionDisplays = {
            teamName: productionForm ? productionForm.querySelector('[data-production-display="team-name"]') : null,
            projectName: productionForm ? productionForm.querySelector('[data-production-display="project-name"]') : null,
            missingQty: productionForm ? productionForm.querySelector('[data-production-display="missing-qtt"]') : null
        };

        var productionLinesContainer = productionForm ? productionForm.querySelector('[data-production-lines]') : null;
        var productionLinesBody = productionForm ? productionForm.querySelector('[data-production-lines-body]') : null;
        var productionLinesMessage = productionForm ? productionForm.querySelector('[data-production-lines-message]') : null;
        var productionLinesDistributeButton = productionForm ? productionForm.querySelector('[data-production-lines-distribute]') : null;
        var productionLinesAddButton = productionForm ? productionForm.querySelector('[data-production-lines-add]') : null;
        if (productionLinesDistributeButton) {
            productionLinesDistributeButton.disabled = true;
        }
        var productionLinesLoadingText = productionLinesContainer ? (productionLinesContainer.dataset.loading || '') : '';
        var productionLinesEmptyText = productionLinesContainer ? (productionLinesContainer.dataset.empty || '') : '';
        var productionLinesErrorText = productionLinesContainer ? (productionLinesContainer.dataset.error || '') : '';
        var productionLinesDeleteLabel = productionLinesContainer ? (productionLinesContainer.dataset.deleteLabel || 'Delete') : 'Delete';
        var productionLinesDeleteConfirm = productionLinesContainer ? (productionLinesContainer.dataset.deleteConfirm || '') : '';
        var productionClosedCheckbox = productionForm ? productionForm.querySelector('[data-production-closed]') : null;
        if (productionClosedCheckbox) { productionClosedCheckbox.disabled = true; }

        var productionRecordsModal = document.getElementById('production-records-modal');
        var productionRecordsDialog = productionRecordsModal ? productionRecordsModal.querySelector('.modal-dialog') : null;
        var productionRecordsList = productionRecordsModal ? productionRecordsModal.querySelector('[data-production-records-list]') : null;
        var productionRecordsMessage = productionRecordsModal ? productionRecordsModal.querySelector('[data-production-records-message]') : null;
        var productionRecordsNewButton = productionRecordsModal ? productionRecordsModal.querySelector('[data-production-records-new]') : null;
        var productionRecordsCancelButton = productionRecordsModal ? productionRecordsModal.querySelector('[data-production-records-cancel]') : null;
        var productionRecordsLoadingText = productionRecordsModal ? (productionRecordsModal.dataset.loading || 'Loading production records...') : '';
        var productionRecordsErrorText = productionRecordsModal ? (productionRecordsModal.dataset.error || 'Unable to load production records.') : '';
        var productionRecordsEmptyText = productionRecordsModal ? (productionRecordsModal.dataset.empty || 'No production records.') : '';
        var productionDraftsContainer = productionRecordsModal ? productionRecordsModal.querySelector('[data-production-records-drafts]') : null;
        var productionDraftsList = productionRecordsModal ? productionRecordsModal.querySelector('[data-production-records-drafts-list]') : null;
        var productionDraftLabel = productionRecordsModal ? (productionRecordsModal.dataset.draftLabel || 'Draft') : 'Draft';
        var productionDraftNote = productionRecordsModal ? (productionRecordsModal.dataset.draftNote || 'Save this record before continuing.') : 'Save this record before continuing.';
        var otherOptionsModal = document.getElementById('other-options-modal');
        var otherOptionsDialog = otherOptionsModal ? otherOptionsModal.querySelector('.modal-dialog') : null;
        var otherOptionsCloseButtons = otherOptionsModal ? otherOptionsModal.querySelectorAll('[data-other-options-close]') : [];
        var otherOptionsSaveButton = otherOptionsModal ? otherOptionsModal.querySelector('[data-other-options-save]') : null;
        otherOptionsFields = otherOptionsModal ? otherOptionsModal.querySelectorAll('[data-other-options-field]') : [];
        var otherOptionsFeedback = otherOptionsModal ? otherOptionsModal.querySelector('[data-other-options-feedback]') : null;
        var otherOptionsDate = otherOptionsModal ? otherOptionsModal.querySelector('[data-other-options-date]') : null;
        var otherOptionsProject = otherOptionsModal ? otherOptionsModal.querySelector('[data-other-options-project]') : null;
        var otherOptionsTeam = otherOptionsModal ? otherOptionsModal.querySelector('[data-other-options-team]') : null;
        var otherOptionsLoadingText = otherOptionsModal ? (otherOptionsModal.dataset.loadingText || '') : '';
        var otherOptionsErrorText = otherOptionsModal ? (otherOptionsModal.dataset.errorText || '') : '';
        var otherOptionsPendingText = otherOptionsModal ? (otherOptionsModal.dataset.pendingText || '') : '';
        var otherOptionsSavedText = otherOptionsModal ? (otherOptionsModal.dataset.savedText || '') : '';
        otherOptionsFields.forEach(function (field) {
            applyDecimalMask(field);
        });
        var productionFormFeedback = productionModal ? productionModal.querySelector('[data-production-feedback]') : null;
        var productionSaveButton = productionModal ? productionModal.querySelector('[data-production-save]') : null;

        var menuElement = null;
        var activeChip = null;
        var activePlanStamp = '';
        var productionDraftStore = new Map();
        var lastRenderedDraftCount = 0;
        var activeProductionChip = null;
        var activeProductionRecord = null;
        var activeProductionPlanStamp = '';
        var budgetItemsCache = new Map();
        var productionFinishOptions = [];
        var productionFinishOptionsPromise = null;
        var productionMissingUpdateToken = 0;
        var productionMissingUpdateTimer = null;
        var planOptionDrafts = new Map();
        var lastFocusedBeforeOtherOptions = null;
        var chipMutationObserver = null;
        var CASH_BADGE_SVG = '<svg viewBox="0 0 512 512" focusable="false" aria-hidden="true"><path d="M256 32c-17 0-32.7 8.9-41.4 23.6L5.1 423.5C-7.6 445.9 8.5 472 33.4 472H478.6c24.9 0 41-26.1 28.3-48.5L297.4 55.6C288.7 40.9 273 32 256 32zm0 128c13.3 0 24 10.7 24 24v96c0 13.3-10.7 24-24 24s-24-10.7-24-24V184c0-13.3 10.7-24 24-24zm32 232c0 17.7-14.3 32-32 32s-32-14.3-32-32s14.3-32 32-32s32 14.3 32 32z"/></svg>';

        function normalizePlanStamp(value) {
            if (value === undefined || value === null) {
                return '';
            }
            return String(value).trim().toUpperCase();
        }

        function parseJsonList(value) {
            if (!value) {
                return [];
            }
            if (Array.isArray(value)) {
                return value;
            }
            if (typeof value === 'string') {
                try {
                    var parsed = JSON.parse(value);
                    return Array.isArray(parsed) ? parsed : [];
                } catch (err) {
                    return [];
                }
            }
            return [];
        }

        function parsePlanStampMap(value) {
            if (!value) {
                return {};
            }
            if (typeof value === 'object' && value !== null && !Array.isArray(value)) {
                return value;
            }
            if (typeof value === 'string') {
                try {
                    var parsed = JSON.parse(value);
                    if (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) {
                        return parsed;
                    }
                } catch (err) {
                    return {};
                }
            }
            return {};
        }

        function cloneDraftRecord(record) {
            if (!record || typeof record !== 'object') {
                return null;
            }
            try {
                return JSON.parse(JSON.stringify(record));
            } catch (err) {
                var clone = {};
                Object.keys(record).forEach(function (key) {
                    clone[key] = record[key];
                });
                return clone;
            }
        }

        function getStoredDraftRecords(planStamp) {
            var normalizedStamp = normalizePlanStamp(planStamp);
            if (!normalizedStamp) {
                return [];
            }
            if (productionDraftStore.has(normalizedStamp)) {
                return parseJsonList(productionDraftStore.get(normalizedStamp));
            }
            return [];
        }

        function setDraftRecords(planStamp, records) {
            var normalizedStamp = normalizePlanStamp(planStamp);
            if (!normalizedStamp) {
                return;
            }
            var parsed = parseJsonList(records);
            var normalized = [];
            parsed.forEach(function (entry) {
                var clone = cloneDraftRecord(entry);
                if (clone) {
                    normalized.push(clone);
                }
            });
            if (normalized.length) {
                productionDraftStore.set(normalizedStamp, normalized);
            } else if (productionDraftStore.has(normalizedStamp)) {
                productionDraftStore.delete(normalizedStamp);
            }
            if (normalizedStamp === activePlanStamp) {
                renderProductionDrafts(normalized);
            }
        }


        function mergeDraftRecordsFromSource(planStamp, source) {
            var normalizedStamp = normalizePlanStamp(planStamp);
            if (!source) {
                return [];
            }
            var parsed = [];
            if (Array.isArray(source)) {
                parsed = source;
            } else if (typeof source === 'string') {
                parsed = parseJsonList(source);
            } else if (typeof source === 'object') {
                var direct = null;
                if (normalizedStamp && Object.prototype.hasOwnProperty.call(source, normalizedStamp)) {
                    direct = source[normalizedStamp];
                } else if (planStamp && Object.prototype.hasOwnProperty.call(source, planStamp)) {
                    direct = source[planStamp];
                }
                if (direct !== null && direct !== undefined) {
                    parsed = parseJsonList(direct);
                } else {
                    var aggregated = [];
                    Object.keys(source).forEach(function (key) {
                        var keyStamp = normalizePlanStamp(key);
                        if (!normalizedStamp || keyStamp === normalizedStamp) {
                            var portion = parseJsonList(source[key]);
                            if (portion.length) {
                                aggregated = aggregated.concat(portion);
                            }
                        }
                    });
                    parsed = aggregated;
                }
            }
            var cloned = [];
            parseJsonList(parsed).forEach(function (entry) {
                var clone = cloneDraftRecord(entry);
                if (clone) {
                    cloned.push(clone);
                }
            });
            if (normalizedStamp) {
                if (cloned.length) {
                    productionDraftStore.set(normalizedStamp, cloned.slice());
                } else if (productionDraftStore.has(normalizedStamp)) {
                    productionDraftStore.delete(normalizedStamp);
                }
            }
            return cloned;
        }

        function assignmentListContains(list, planStamp) {
            if (!Array.isArray(list)) {
                return false;
            }
            var normalized = normalizePlanStamp(planStamp);
            if (!normalized) {
                return false;
            }
            for (var index = 0; index < list.length; index += 1) {
                var item = list[index];
                if (!item || typeof item !== 'object') {
                    continue;
                }
                var stamp = item.plan_stamp || item.planStamp || item.u_planostamp || item.planostamp || item.planstamp || item.stamp;
                if (normalizePlanStamp(stamp) === normalized) {
                    return true;
                }
            }
            return false;
        }

        function chipAssignmentIsDraft(chip, planStamp) {
            var normalizedStamp = normalizePlanStamp(planStamp);
            if (!normalizedStamp || !chip) {
                return false;
            }
            var cell = chip.closest('.day-cell');
            if (!cell || !cell.dataset) {
                return false;
            }
            if (typeof console !== 'undefined') {
                try {
                    console.log('chipAssignmentIsDraft check', {
                        planStamp: normalizedStamp,
                        cellDataset: Object.assign({}, cell.dataset),
                        chipDataset: Object.assign({}, chip.dataset || {}),
                        initialAssignments: cell.dataset.initialAssignments,
                        planStampMap: cell.dataset.planStampMap,
                        initialPlanStampMap: cell.dataset.initialPlanStampMap
                    });
                } catch (err) {
                    /* ignore console errors */
                }
            }
            var currentMap = parsePlanStampMap(cell.dataset.planStampMap);
            var hasInCurrent = false;
            Object.keys(currentMap).forEach(function (key) {
                if (normalizePlanStamp(currentMap[key]) === normalizedStamp) {
                    hasInCurrent = true;
                }
            });
            if (!hasInCurrent) {
                if (normalizePlanStamp(chip.dataset.planStamp || '') === normalizedStamp) {
                    hasInCurrent = true;
                }
            }
            if (!hasInCurrent) {
                return false;
            }
            var initialMap = parsePlanStampMap(cell.dataset.initialPlanStampMap);
            var existedInitially = false;
            Object.keys(initialMap).forEach(function (key) {
                if (normalizePlanStamp(initialMap[key]) === normalizedStamp) {
                    existedInitially = true;
                }
            });
            if (existedInitially) {
                return false;
            }
            var initialAssignments = parseJsonList(cell.dataset.initialAssignments);
            if (assignmentListContains(initialAssignments, normalizedStamp)) {
                return false;
            }
            return true;
        }

        function buildDraftRecordFromAssignment(chip, planStamp) {
            var normalizedStamp = normalizePlanStamp(planStamp);
            var cell = chip ? chip.closest('.day-cell') : null;
            var chipData = chip && chip.dataset ? chip.dataset : {};
            var cellData = cell && cell.dataset ? cell.dataset : {};
            var isoDate = chipData.planDate || cellData.date || '';
            var dateLabel = cellData.dateLabel || cellData.weekdayLabel || '';
            if (!dateLabel && isoDate) {
                dateLabel = isoDate.slice(0, 10);
            }
            var projectLabel = chipData.planProjectName || chipData.planProjectName || chipData.planProcess || cellData.projectDescription || cellData.projectName || '';
            var teamLabel = chipData.planTeamName || chipData.planFref || chipData.teamCode || (chip && chip.textContent ? chip.textContent.trim() : '');
            var summaryParts = [];
            if (dateLabel) {
                summaryParts.push(dateLabel);
            }
            if (projectLabel) {
                summaryParts.push(projectLabel);
            }
            if (teamLabel) {
                summaryParts.push(teamLabel);
            }
            return {
                planStamp: normalizedStamp,
                data: isoDate,
                dgeral: projectLabel,
                draftSummary: summaryParts.join(' · ') || productionDraftLabel,
                draftTeam: teamLabel,
                draftDateLabel: dateLabel,
                draftProject: projectLabel,
                draftNote: productionDraftNote
            };
        }

        function normalizeNumberValue(value) {
            if (value === undefined || value === null || value === '') {
                return null;
            }
            if (typeof value === 'number' && Number.isFinite(value)) {
                return value;
            }
            var normalized = parseFloat(String(value).replace(',', '.'));
            return Number.isFinite(normalized) ? normalized : null;
        }

        function formatSignedDecimal(value, decimalPlaces) {
            if (!Number.isFinite(value)) {
                return '';
            }
            var places = typeof decimalPlaces === 'number' && decimalPlaces >= 0 ? decimalPlaces : 2;
            return value.toFixed(places);
        }

        function setProductionMissingDisplay(text) {
            if (!productionDisplays.missingQty) {
                return;
            }
            productionDisplays.missingQty.value = text || '';
        }

        function scheduleProductionMissingUpdate() {
            if (productionMissingUpdateTimer) {
                clearTimeout(productionMissingUpdateTimer);
            }
            productionMissingUpdateTimer = setTimeout(function () {
                productionMissingUpdateTimer = null;
                updateProductionMissingFromBudget();
            }, 150);
        }

        function fetchProjectBudgetItems(projectCode) {
            var normalized = normalizePlanStamp(projectCode);
            if (!normalized) {
                return Promise.resolve([]);
            }
            if (budgetItemsCache.has(normalized)) {
                return budgetItemsCache.get(normalized);
            }
            var promise = fetch('/api/projects/' + encodeURIComponent(normalized) + '/budget-items', {
                headers: { 'Accept': 'application/json' },
                credentials: 'same-origin'
            }).then(function (res) {
                if (!res.ok) {
                    return [];
                }
                return res.json().catch(function () { return []; });
            }).then(function (data) {
                return Array.isArray(data) ? data : [];
            }).catch(function () {
                return [];
            });
            budgetItemsCache.set(normalized, promise);
            return promise;
        }

        function findBudgetItem(items, litemValue) {
            if (!Array.isArray(items) || !items.length) {
                return null;
            }
            var litem = parseInt(String(litemValue || '').trim(), 10);
            if (!Number.isFinite(litem)) {
                return null;
            }
            for (var i = 0; i < items.length; i += 1) {
                var item = items[i];
                if (!item) {
                    continue;
                }
                var candidate = item.litem !== undefined && item.litem !== null ? parseInt(String(item.litem).trim(), 10) : NaN;
                if (Number.isFinite(candidate) && candidate === litem) {
                    return item;
                }
            }
            return null;
        }

        function updateProductionMissingFromBudget() {
            if (!productionDisplays.missingQty) {
                return;
            }
            var projectCode = productionForm && productionForm.dataset ? (productionForm.dataset.projectCode || '') : '';
            if (!projectCode && productionFields.processo) {
                projectCode = productionFields.processo.value || '';
            }
            var litemValue = productionFields.litem ? productionFields.litem.value : '';
            if (!projectCode || !String(litemValue || '').trim()) {
                setProductionMissingDisplay('');
                return;
            }
            var token = ++productionMissingUpdateToken;
            fetchProjectBudgetItems(projectCode).then(function (items) {
                if (token !== productionMissingUpdateToken) {
                    return;
                }
                var match = findBudgetItem(items, litemValue);
                if (!match) {
                    setProductionMissingDisplay('');
                    return;
                }
                var planned = normalizeNumberValue(match.qtt);
                var measured = normalizeNumberValue(match.qtt2);
                var plannedVal = Number.isFinite(planned) ? planned : 0;
                var measuredVal = Number.isFinite(measured) ? measured : 0;
                var missingVal = plannedVal - measuredVal;
                var unit = match.unidade !== undefined && match.unidade !== null ? String(match.unidade).trim() : '';
                var formatted = formatSignedDecimal(missingVal, 2);
                setProductionMissingDisplay(formatted ? (formatted + (unit ? (' ' + unit) : '')) : '');
            });
        }

        function normaliseDateValue(value) {
            if (value === undefined || value === null || value === '') {
                return '';
            }
            if (value instanceof Date && !Number.isNaN(value.getTime())) {
                return value.toISOString().slice(0, 10);
            }
            if (typeof value === 'number' && Number.isFinite(value)) {
                try {
                    var dateFromNumber = new Date(value);
                    if (!Number.isNaN(dateFromNumber.getTime())) {
                        return dateFromNumber.toISOString().slice(0, 10);
                    }
                } catch (err) {
                    /* ignore */
                }
            }
            if (typeof value === 'string') {
                var trimmed = value.trim();
                if (!trimmed) {
                    return '';
                }
                if (/^\d{4}-\d{2}-\d{2}/.test(trimmed)) {
                    return trimmed.slice(0, 10);
                }
                try {
                    var parsed = new Date(trimmed);
                    if (!Number.isNaN(parsed.getTime())) {
                        return parsed.toISOString().slice(0, 10);
                    }
                } catch (err) {
                    /* ignore */
                }
            }
            return '';
        }

        function otherOptionsKeyFromChip(chip) {
            if (!chip) {
                return '';
            }
            var cell = chip.closest('.day-cell');
            var projectCode = chip.dataset ? (chip.dataset.planProcess || '') : '';
            if (!projectCode && cell && cell.dataset) {
                projectCode = cell.dataset.projectCode || '';
            }
            var teamCode = chip.dataset ? (chip.dataset.teamCode || '') : '';
            var dateValue = chip.dataset ? (chip.dataset.planDate || '') : '';
            if (!dateValue && cell && cell.dataset) {
                dateValue = cell.dataset.date || '';
            }
            return [projectCode, teamCode, dateValue].map(function (part) {
                return (part || '').toString().trim().toUpperCase();
            }).join('|');
        }

        function readPlanMetaFromChip(chip) {
            if (!chip) {
                return {};
            }
            var cell = chip.closest('.day-cell');
            var chipData = chip.dataset || {};
            var cellData = cell && cell.dataset ? cell.dataset : {};
            return {
                planDate: chipData.planDate || cellData.date || '',
                teamCode: chipData.teamCode || '',
                projectCode: chipData.planProcess || cellData.projectCode || ''
            };
        }

        function setPlanOptionDraft(key, values, meta) {
            if (!key) {
                return;
            }
            planOptionDrafts.set(key, { values: values || {}, meta: meta || {} });
        }

        function getPlanOptionDraft(key) {
            if (!key) {
                return null;
            }
            return planOptionDrafts.get(key) || null;
        }

        function updateChipEconomicState(chip, fixedValue, bonusValue) {
            if (!chip || !isPlanningAdmin) {
                return;
            }
            var normalizedFixed = normalizeNumberValue(fixedValue);
            var normalizedBonus = normalizeNumberValue(bonusValue);
            chip.dataset.planFixo = normalizedFixed !== null && normalizedFixed !== undefined ? normalizedFixed : '';
            chip.dataset.planPremio = normalizedBonus !== null && normalizedBonus !== undefined ? normalizedBonus : '';
            var hasEconomic = (normalizedFixed !== null && Math.abs(normalizedFixed) > 0) || (normalizedBonus !== null && Math.abs(normalizedBonus) > 0);
            var badge = chip.querySelector('.assignment-chip-cash');
            if (hasEconomic) {
                if (!badge) {
                    badge = document.createElement('span');
                    badge.className = 'assignment-chip-cash';
                    badge.setAttribute('title', 'Valores económicos');
                    badge.setAttribute('aria-hidden', 'true');
                    badge.innerHTML = CASH_BADGE_SVG;
                    chip.appendChild(badge);
                    var sr = document.createElement('span');
                    sr.className = 'sr-only';
                    sr.textContent = 'Valores económicos';
                    chip.appendChild(sr);
                }
            } else if (badge) {
                badge.remove();
                var srOnly = chip.querySelector('.sr-only');
                if (srOnly && srOnly.textContent === 'Valores económicos') {
                    srOnly.remove();
                }
            }
        }

        function renderProductionFinishOptions(selectedValue) {
            var field = productionFields.acabamento;
            if (!field) {
                return;
            }
            var currentValue = selectedValue;
            if (currentValue === undefined || currentValue === null) {
                currentValue = field.value || '';
            }
            currentValue = String(currentValue || '').trim();

            field.innerHTML = '';

            var placeholder = document.createElement('option');
            placeholder.value = '';
            placeholder.textContent = '-- selecionar --';
            field.appendChild(placeholder);

            var seen = new Set();
            productionFinishOptions.forEach(function (item) {
                var value = String(item || '').trim();
                if (!value || seen.has(value)) {
                    return;
                }
                seen.add(value);
                var option = document.createElement('option');
                option.value = value;
                option.textContent = value;
                field.appendChild(option);
            });

            if (currentValue && !seen.has(currentValue)) {
                var currentOption = document.createElement('option');
                currentOption.value = currentValue;
                currentOption.textContent = currentValue;
                field.appendChild(currentOption);
            }

            field.value = currentValue || '';
            field.disabled = false;
        }

        function loadProductionFinishOptions(selectedValue) {
            var field = productionFields.acabamento;
            if (!field) {
                return Promise.resolve([]);
            }
            if (productionFinishOptions.length) {
                renderProductionFinishOptions(selectedValue);
                return Promise.resolve(productionFinishOptions.slice());
            }
            if (productionFinishOptionsPromise) {
                return productionFinishOptionsPromise.then(function (rows) {
                    renderProductionFinishOptions(selectedValue);
                    return rows;
                });
            }

            field.disabled = true;
            productionFinishOptionsPromise = fetch('/api/production-finitions', {
                headers: { 'Accept': 'application/json' },
                credentials: 'same-origin'
            }).then(function (response) {
                if (!response.ok) {
                    throw new Error(String(response.status || 'error'));
                }
                return response.json().catch(function () {
                    return [];
                });
            }).then(function (rows) {
                var next = [];
                var seen = new Set();
                if (Array.isArray(rows)) {
                    rows.forEach(function (item) {
                        var value = typeof item === 'string'
                            ? item
                            : (item && item.ref !== undefined && item.ref !== null ? item.ref : '');
                        value = String(value || '').trim();
                        if (!value || seen.has(value)) {
                            return;
                        }
                        seen.add(value);
                        next.push(value);
                    });
                }
                productionFinishOptions = next;
                return next;
            }).catch(function () {
                productionFinishOptions = [];
                return [];
            }).finally(function () {
                productionFinishOptionsPromise = null;
                renderProductionFinishOptions(selectedValue);
            });

            return productionFinishOptionsPromise;
        }

        function setProductionField(name, value) {
            var field = productionFields[name];
            if (!field) {
                return;
            }
            if (value === undefined || value === null || value === '') {
                field.value = '';
                return;
            }
            if (name === 'data') {
                field.value = normaliseDateValue(value);
                return;
            }
            if (decimalFieldMap[name]) {
                var formatted = formatDecimalValue(value, 2);
                field.value = formatted || '';
                return;
            }
            if (field.tagName && field.tagName.toUpperCase() === 'SELECT') {
                renderProductionFinishOptions(value);
                return;
            }
            field.value = typeof value === 'string' ? value : String(value);
        }

        function focusFirstProductionField() {
            var orderedFields = [
                productionFields.data,
                productionFields.litem,
                productionFields.acabamento,
                productionFields.dgeral,
                productionFields.qtt
            ];
            for (var index = 0; index < orderedFields.length; index += 1) {
                var field = orderedFields[index];
                if (!field || field.disabled || field.readOnly) {
                    continue;
                }
                try {
                    field.focus({ preventScroll: true });
                } catch (err) {
                    try {
                        field.focus();
                    } catch (innerErr) {
                        /* ignore focus errors */
                    }
                }
                return;
            }
        }

        function resetProductionFormState() {
            if (!productionForm) {
                return;
            }
            try {
                productionForm.reset();
            } catch (err) {
                /* ignore reset errors */
            }
            Object.keys(productionFields).forEach(function (key) {
                var field = productionFields[key];
                if (!field) {
                    return;
                }
                field.value = '';
            });
            if (productionDisplays.teamName) {
                productionDisplays.teamName.value = '';
            }
            if (productionDisplays.projectName) {
                productionDisplays.projectName.value = '';
            }
            if (productionDisplays.missingQty) {
                productionDisplays.missingQty.value = '';
            }
            if (productionForm.dataset) {
                delete productionForm.dataset.planStamp;
                delete productionForm.dataset.amStamp;
                delete productionForm.dataset.mode;
                delete productionForm.dataset.planLineStamp;
                delete productionForm.dataset.teamCode;
                delete productionForm.dataset.projectCode;
            }
            if (productionFormFeedback) {
                productionFormFeedback.textContent = '';
                productionFormFeedback.hidden = true;
                productionFormFeedback.classList.remove('is-error');
                productionFormFeedback.classList.remove('is-success');
            }
            if (productionLinesContainer) {
                productionLinesContainer.setAttribute('hidden', 'hidden');
            }
            if (productionLinesBody) {
                productionLinesBody.innerHTML = '';
            }
            if (productionLinesMessage) {
                productionLinesMessage.textContent = '';
                productionLinesMessage.hidden = true;
            }
            if (productionLinesDistributeButton) {
                productionLinesDistributeButton.disabled = true;
            }
            productionLineTotals = null;
            productionLineData = [];
            updateProductionFieldComparisons();
            updateClosedState();
            setProductionSaveState(false);
        }


        function applyProductionDisplays(chipData, record) {
            if (!productionDisplays.teamName && !productionDisplays.projectName) {
                return;
            }
            var teamLabel = '';
            if (chipData) {
                teamLabel = chipData.planTeamName || chipData.planFref || chipData.teamCode || '';
            }
            if (!teamLabel && record && record.fref) {
                teamLabel = String(record.fref);
            }
            if (productionDisplays.teamName) {
                productionDisplays.teamName.value = teamLabel || '';
            }
            var projectLabel = '';
            if (chipData) {
                projectLabel = chipData.planProjectName || chipData.planProcess || '';
            }
            if (!projectLabel && record && record.processo) {
                projectLabel = String(record.processo);
            }
            if (productionDisplays.projectName) {
                productionDisplays.projectName.value = projectLabel || '';
            }
        }

        function coerceDecimalValue(value) {
            if (value === undefined || value === null) {
                return null;
            }
            if (typeof value === 'number') {
                return Number.isFinite(value) ? value : null;
            }
            var stringValue = String(value).trim();
            if (!stringValue) {
                return null;
            }
            var normalised = stringValue.replace(',', '.');
            var parsed = parseFloat(normalised);
            return Number.isFinite(parsed) ? parsed : null;
        }

        function computeProductionLineTotals(lines) {
            if (!Array.isArray(lines) || !lines.length) {
                return null;
            }
            var totals = { qtt: 0, kgferro: 0, m2serragem: 0 };
            var hasValue = false;
            lines.forEach(function (line) {
                if (!line || typeof line !== 'object') {
                    return;
                }
                productionLineComparisonFields.forEach(function (fieldName) {
                    var numericValue = coerceDecimalValue(line[fieldName]);
                    if (numericValue !== null) {
                        totals[fieldName] += numericValue;
                        hasValue = true;
                    }
                });
            });
            if (!hasValue) {
                productionLineComparisonFields.forEach(function (fieldName) {
                    totals[fieldName] = 0;
                });
            }
            return totals;
        }

        function quantizeLineValue(value, fieldName) {
            var numeric = coerceDecimalValue(value);
            if (numeric === null) {
                return null;
            }
            var decimalPlaces = getProductionLineDecimalPlaces(fieldName);
            var multiplier = Math.pow(10, decimalPlaces);
            return Math.round(numeric * multiplier) / multiplier;
        }

        function setProductionLineValue(lineIndex, fieldName, value) {
            if (!Array.isArray(productionLineData) || !productionLineData[lineIndex]) {
                return;
            }
            var normalized = quantizeLineValue(value, fieldName);
            productionLineData[lineIndex][fieldName] = normalized;
            if (!productionLinesBody) {
                return;
            }
            var selector = '[data-line-index="' + lineIndex + '"][data-line-field="' + fieldName + '"]';
            var input = productionLinesBody.querySelector(selector);
            if (input) {
                input.value = normalized === null ? '' : formatProductionLineMetric(normalized, fieldName);
            }
        }

        function toggleProductionFieldMismatch(field, mismatch, totalValue) {
            if (!field) {
                return;
            }
            if (mismatch) {
                field.classList.add('production-input-mismatch');
                field.setAttribute('aria-invalid', 'true');
                if (totalValue !== null && Number.isFinite(totalValue)) {
                    field.dataset.mismatchTotal = totalValue.toFixed(3);
                } else {
                    delete field.dataset.mismatchTotal;
                }
            } else {
                field.classList.remove('production-input-mismatch');
                field.removeAttribute('aria-invalid');
                delete field.dataset.mismatchTotal;
            }
        }

        function updateClosedState() {
            if (typeof productionClosedCheckbox === 'undefined') { return; }
            if (!productionClosedCheckbox) { return; }
            var epsilon = 0.005;
            if (!productionLineTotals) { productionClosedCheckbox.disabled = true; return; }
            var allMatch = true;
            productionLineComparisonFields.forEach(function (fieldName) {
                var headerField = productionFields[fieldName];
                if (!headerField) { allMatch = false; return; }
                var inputValue = coerceDecimalValue(headerField.value || '');
                var totalValue = productionLineTotals[fieldName];
                if (totalValue === null || !Number.isFinite(totalValue)) { allMatch = false; return; }
                if (inputValue === null) {
                    if (Math.abs(totalValue) > epsilon) { allMatch = false; }
                } else {
                    if (Math.abs(inputValue - totalValue) > epsilon) { allMatch = false; }
                }
            });
            productionClosedCheckbox.disabled = !allMatch;
        }


        function updateProductionFieldComparisons() {
            var epsilon = 0.005;
            productionLineComparisonFields.forEach(function (fieldName) {
                var field = productionFields[fieldName];
                if (!field) {
                    return;
                }
                if (!productionLineTotals || !Object.prototype.hasOwnProperty.call(productionLineTotals, fieldName)) {
                    toggleProductionFieldMismatch(field, false, null);
                    return;
                }
                var totalValue = productionLineTotals[fieldName];
                if (totalValue === null || !Number.isFinite(totalValue)) {
                    toggleProductionFieldMismatch(field, false, null);
                    return;
                }
                var inputValue = coerceDecimalValue(field.value || '');
                var mismatch;
                if (inputValue === null) {
                    mismatch = Math.abs(totalValue) > epsilon;
                } else {
                    mismatch = Math.abs(inputValue - totalValue) > epsilon;
                }
                toggleProductionFieldMismatch(field, mismatch, totalValue);
            });
               function updateClosedState() {
            if (!productionClosedCheckbox) { return; }
            var epsilon = 0.005;
            if (!productionLineTotals) { productionClosedCheckbox.disabled = true; return; }
            var allMatch = true;
            productionLineComparisonFields.forEach(function (fieldName) {
                var headerField = productionFields[fieldName];
                if (!headerField) { allMatch = false; return; }
                var inputValue = coerceDecimalValue(headerField.value || '');
                var totalValue = productionLineTotals[fieldName];
                if (totalValue === null || !Number.isFinite(totalValue)) { allMatch = false; return; }
                if (inputValue === null) {
                    if (Math.abs(totalValue) > epsilon) { allMatch = false; }
                } else {
                    if (Math.abs(inputValue - totalValue) > epsilon) { allMatch = false; }
                }
            });
            productionClosedCheckbox.disabled = !allMatch;
        }

 }

        function getProductionLineDecimalPlaces(fieldName) {
            if (fieldName && Object.prototype.hasOwnProperty.call(productionLineFieldDecimalPlaces, fieldName)) {
                return productionLineFieldDecimalPlaces[fieldName];
            }
            return 3;
        }

        function formatProductionLineMetric(value, fieldName) {
            var formatted = formatDecimalValue(value, getProductionLineDecimalPlaces(fieldName));
            if (!formatted) {
                return '';
            }
            return formatted;
        }

        function setProductionLinesMessage(message) {
            if (!productionLinesMessage) {
                return;
            }
            productionLinesMessage.textContent = message || '';
            productionLinesMessage.hidden = !message;
        }

        function renderProductionLines(lines) {
            if (!productionLinesContainer || !productionLinesBody) {
                return;
            }
            productionLinesContainer.removeAttribute('hidden');
            productionLinesBody.innerHTML = '';
            if (!Array.isArray(lines) || !lines.length) {
                productionLineData = [];
                productionLineTotals = null;
                setProductionLinesMessage(productionLinesEmptyText);
                if (productionLinesDistributeButton) {
                    productionLinesDistributeButton.disabled = true;
                }
                updateProductionFieldComparisons();
                return;
            }
            productionLineData = lines.map(function (line) {
                var clone = Object.assign({}, line || {});
                productionLineEditableFields.forEach(function (fieldName) {
                    var numericValue = coerceDecimalValue(clone[fieldName]);
                    var decimalPlaces = getProductionLineDecimalPlaces(fieldName);
                    var multiplier = Math.pow(10, decimalPlaces);
                    clone[fieldName] = numericValue === null ? null : Math.round(numericValue * multiplier) / multiplier;
                });
                return clone;
            });
            productionLineTotals = computeProductionLineTotals(productionLineData) || { qtt: 0, kgferro: 0, m2serragem: 0 };
            setProductionLinesMessage('');
            if (productionLinesDistributeButton) {
                productionLinesDistributeButton.disabled = productionLineData.length === 0;
            }
            productionLineData.forEach(function (lineData, index) {
                var row = document.createElement('div');
                row.className = 'production-lines-row';

                var nameCell = document.createElement('span');
                nameCell.className = 'production-lines-cell production-lines-cell--name';
                var nameValue = lineData && lineData.nome !== undefined && lineData.nome !== null ? String(lineData.nome).trim() : '';
                if (lineData && lineData.__isNew) {
                    var select = document.createElement('select');
                    select.className = 'production-lines-input production-lines-select';
                    select.dataset.lineIndex = String(index);
                    var placeholder = document.createElement('option');
                    placeholder.value = '';
                    placeholder.textContent = '— selecionar —';
                    select.appendChild(placeholder);
                    ensureEmployeesLoaded().then(function (rows) {
                        rows.forEach(function (emp) {
                            var opt = document.createElement('option');
                            opt.value = String(emp.no);
                            opt.textContent = String(emp.cval4) + ' (' + String(emp.no) + ')';
                            select.appendChild(opt);
                        });
                        if (lineData.no) { select.value = String(lineData.no); select.title = nameValue || ''; }
                    });
                    select.addEventListener('change', function () {
                        var idx = parseInt(select.dataset.lineIndex || '-1', 10);
                        var option = select.options[select.selectedIndex];
                        var valueNo = select.value || '';
                        var valueNome = option && option.textContent ? option.textContent.replace(/\s*\(.*\)$/, '') : '';
                        if (Number.isFinite(idx) && productionLineData[idx]) {
                            productionLineData[idx].no = valueNo;
                            productionLineData[idx].nome = valueNome;
                        }
                        select.title = valueNome || '';
                    });
                    nameCell.appendChild(select);
                } else {
                    nameCell.textContent = nameValue;
                }
                row.appendChild(nameCell);

                productionLineEditableFields.forEach(function (fieldName) {
                    var metricCell = document.createElement('span');
                    metricCell.className = 'production-lines-cell production-lines-cell--metric';

                    var metricInput = document.createElement('input');
                    metricInput.type = 'text';
                    metricInput.className = 'production-lines-input production-decimal-input';
                    metricInput.value = formatProductionLineMetric(lineData ? lineData[fieldName] : '', fieldName);
                    metricInput.dataset.lineIndex = String(index);
                    metricInput.dataset.lineField = fieldName;
                    metricInput.setAttribute('data-decimal-places', String(getProductionLineDecimalPlaces(fieldName)));
                    metricInput.setAttribute('inputmode', 'decimal');
                    metricInput.autocomplete = 'off';

                    applyDecimalMask(metricInput);
                    metricInput.addEventListener('input', handleProductionLineValueChange);
                    metricInput.addEventListener('blur', handleProductionLineValueChange);

                    metricCell.appendChild(metricInput);
                    row.appendChild(metricCell);
                });

                var actionsCell = document.createElement('span');
                actionsCell.className = 'production-lines-cell production-lines-cell--actions';

                var deleteButton = document.createElement('button');
                deleteButton.type = 'button';
                deleteButton.className = 'production-lines-delete';
                deleteButton.dataset.lineIndex = String(index);
                deleteButton.setAttribute('aria-label', productionLinesDeleteLabel);
                deleteButton.setAttribute('title', productionLinesDeleteLabel);
                var deleteIcon = document.createElement('span');
                deleteIcon.setAttribute('aria-hidden', 'true');
                deleteIcon.textContent = '×';
                deleteButton.appendChild(deleteIcon);
                if (productionLinesDeleteConfirm) {
                    deleteButton.dataset.confirm = productionLinesDeleteConfirm;
                }
                deleteButton.addEventListener('click', function () {
                    deleteProductionLineAt(index, deleteButton);
                });

                actionsCell.appendChild(deleteButton);
                row.appendChild(actionsCell);

                productionLinesBody.appendChild(row);
            });
            updateProductionFieldComparisons();
            updateClosedState();
        }

        function handleProductionLineValueChange(event) {
            var target = event && event.target;
            if (!target || !target.dataset) {
                return;
            }
            var lineIndex = parseInt(target.dataset.lineIndex, 10);
            var fieldName = target.dataset.lineField;
            if (!Number.isFinite(lineIndex) || !fieldName) {
                return;
            }
            if (!Array.isArray(productionLineData) || !productionLineData[lineIndex]) {
                return;
            }
            var numericValue = coerceDecimalValue(target.value || '');
            var normalizedValue = numericValue === null ? null : quantizeLineValue(numericValue, fieldName);
            productionLineData[lineIndex][fieldName] = normalizedValue;
            if (event && event.type === 'blur') {
                setProductionLineValue(lineIndex, fieldName, normalizedValue);
            }
            productionLineTotals = computeProductionLineTotals(productionLineData) || { qtt: 0, kgferro: 0, m2serragem: 0 };
            updateProductionFieldComparisons();
            updateClosedState();
        }

        function deleteProductionLineAt(lineIndex, triggerButton) {
            if (!Array.isArray(productionLineData) || !productionLineData[lineIndex]) {
                return;
            }
            var line = productionLineData[lineIndex];
            var stamp = line && line.u_amlstamp !== undefined && line.u_amlstamp !== null ? String(line.u_amlstamp).trim() : '';
            var confirmMessage = productionLinesDeleteConfirm;
            if (triggerButton && triggerButton.dataset && triggerButton.dataset.confirm) {
                confirmMessage = triggerButton.dataset.confirm;
            }
            if (confirmMessage) {
                try {
                    if (!window.confirm(confirmMessage)) {
                        return;
                    }
                } catch (err) {
                    /* ignore confirm errors */
                }
            }
            function finalizeDeletion() {
                productionLineData.splice(lineIndex, 1);
                refreshProductionLinesView();
                try {
                    var planStampValue = productionForm && productionForm.dataset ? (productionForm.dataset.planStamp || '') : '';
                    if (planStampValue) {
                        window.dispatchEvent(new CustomEvent('planning:production-updated', { detail: { planStamp: String(planStampValue).toUpperCase() } }));
                    }
                } catch (err) { /* ignore */ }
            }
            if (!stamp) {
                finalizeDeletion();
                return;
            }
            if (triggerButton) {
                try {
                    triggerButton.disabled = true;
                } catch (err) {
                    /* ignore disable errors */
                }
            }
            fetch('/api/production-lines/' + encodeURIComponent(stamp), {
                method: 'DELETE',
                headers: { 'Accept': 'application/json' }
            })
                .then(function (response) {
                    if (response.status === 204 || response.status === 404) {
                        finalizeDeletion();
                        return null;
                    }
                    var contentType = response.headers ? (response.headers.get('Content-Type') || '') : '';
                    if (contentType.indexOf('application/json') !== -1) {
                        return response.json().catch(function () {
                            return {};
                        }).then(function (data) {
                            var error = new Error('Request failed');
                            error.response = response;
                            error.data = data;
                            throw error;
                        });
                    }
                    var genericError = new Error('Request failed');
                    genericError.response = response;
                    genericError.data = {};
                    throw genericError;
                })
                .catch(function (error) {
                    var message = productionLinesErrorText || 'Unable to delete production line.';
                    if (error && error.data) {
                        if (typeof error.data.details === 'string' && error.data.details.length) {
                            message = error.data.details;
                        } else if (typeof error.data.error === 'string' && error.data.error.length) {
                            message = error.data.error;
                        }
                    }
                    showProductionFormFeedback(message, true);
                    if (triggerButton) {
                        try {
                            triggerButton.disabled = false;
                        } catch (err) {
                            /* ignore enable errors */
                        }
                    }
                    if (error && error.response) {
                        try {
                            console.error('production-line delete failed', error);
                        } catch (err) {
                            /* ignore console errors */
                        }
                    }
                });
        }

        function refreshProductionLinesView() {
            if (!Array.isArray(productionLineData)) {
                renderProductionLines([]);
                return;
            }
            var cloned = productionLineData.map(function (line) {
                return line ? Object.assign({}, line) : line;
            });
            renderProductionLines(cloned);
        }

        function addProductionLine() {
            if (!Array.isArray(productionLineData)) {
                productionLineData = [];
            }
            var newLine = { __isNew: true, u_amlstamp: '', no: '', nome: '', qtt: 0, kgferro: 0, m2serragem: 0, u_prime: 0 };
            productionLineData.push(newLine);
            refreshProductionLinesView();
        }

        function ensureEmployeesLoaded() {
            if (window.__employeesLoaded) { return Promise.resolve(window.__employees || []); }
            return fetch('/api/employees', { headers: { 'Accept': 'application/json' } })
                .then(function (res) { return res.json(); })
                .then(function (rows) { window.__employees = Array.isArray(rows) ? rows : []; window.__employeesLoaded = true; return window.__employees; })
                .catch(function () { window.__employees = []; window.__employeesLoaded = true; return []; });
        }

        function distributeProductionLines() {
            if (!Array.isArray(productionLineData) || !productionLineData.length) {
                return;
            }
            var epsilon = 0.0005;
            var changed = false;
            productionLineComparisonFields.forEach(function (fieldName) {
                var totalField = productionFields[fieldName];
                if (!totalField) {
                    return;
                }
                var totalValue = coerceDecimalValue(totalField.value || '');
                if (totalValue === null) {
                    totalValue = 0;
                }
                var existingSum = 0;
                var eligibleIndexes = [];
                productionLineData.forEach(function (lineData, index) {
                    var lineValue = coerceDecimalValue(lineData ? lineData[fieldName] : null);
                    if (lineValue === null) {
                        lineValue = 0;
                    }
                    if (Math.abs(lineValue) > epsilon) {
                        existingSum += lineValue;
                    } else {
                        eligibleIndexes.push(index);
                    }
                });
                if (!eligibleIndexes.length) {
                    return;
                }
                var remainder = totalValue - existingSum;
                if (remainder <= epsilon) {
                    eligibleIndexes.forEach(function (index) {
                        setProductionLineValue(index, fieldName, 0);
                    });
                    changed = true;
                    return;
                }
                var normalizedRemainder = remainder;
                var assigned = 0;
                for (var i = 0; i < eligibleIndexes.length; i += 1) {
                    var value;
                    if (i === eligibleIndexes.length - 1) {
                        value = Math.max(0, normalizedRemainder - assigned);
                    } else {
                        value = Math.max(0, normalizedRemainder / eligibleIndexes.length);
                    }
                    value = quantizeLineValue(value, fieldName);
                    if (value === null) {
                        value = 0;
                    }
                    assigned += value;
                    var targetIndex = eligibleIndexes[i];
                    var currentValue = coerceDecimalValue(productionLineData[targetIndex][fieldName]);
                    if (currentValue === null) {
                        currentValue = 0;
                    }
                    if (Math.abs(currentValue - value) > epsilon) {
                        changed = true;
                    }
                    setProductionLineValue(targetIndex, fieldName, value);
                }
            });
            if (!changed) {
                return;
            }
            productionLineTotals = computeProductionLineTotals(productionLineData) || { qtt: 0, kgferro: 0, m2serragem: 0 };
            updateProductionFieldComparisons();
            updateClosedState();
        }

        function fetchProductionLines(amStamp) {
            if (!productionLinesContainer || !productionLinesBody) {
                return;
            }
            productionLinesContainer.removeAttribute('hidden');
            productionLinesBody.innerHTML = '';
            setProductionLinesMessage(productionLinesLoadingText);
            productionLineTotals = null;
            productionLineData = [];
            if (productionLinesDistributeButton) {
                productionLinesDistributeButton.disabled = true;
            }
            updateProductionFieldComparisons();
            if (!amStamp) {
                renderProductionLines([]);
                return;
            }
            var url = '/api/production-records/' + encodeURIComponent(amStamp) + '/lines';
            fetch(url, { headers: { 'Accept': 'application/json' } })
                .then(function (response) {
                    if (!response.ok) {
                        throw new Error(String(response.status || 'error'));
                    }
                    return response.json();
                })
                .then(function (data) {
                    if (!Array.isArray(data)) {
                        productionLineTotals = null;
                        productionLineData = [];
                        productionLinesBody.innerHTML = '';
                        setProductionLinesMessage(productionLinesErrorText || productionRecordsErrorText || '');
                        if (productionLinesDistributeButton) {
                            productionLinesDistributeButton.disabled = true;
                        }
                        updateProductionFieldComparisons();
                        return;
                    }
                    renderProductionLines(data);
                })
                .catch(function () {
                    productionLineTotals = null;
                    productionLineData = [];
                    productionLinesBody.innerHTML = '';
                    setProductionLinesMessage(productionLinesErrorText || productionRecordsErrorText || '');
                    if (productionLinesDistributeButton) {
                        productionLinesDistributeButton.disabled = true;
                    }
                    updateProductionFieldComparisons();
                });
        }

        
        function openProductionModal(chip, record) {
            if (!productionModal || !productionForm) {
                return;
            }
            var baseChip = chip || activeChip || activeProductionChip || null;
            var chipData = baseChip && baseChip.dataset ? baseChip.dataset : {};
            activeProductionChip = baseChip;
            activeProductionRecord = record || null;

            var planStampSource = record ? (record.planostamp || record.plan_stamp || record.planStamp || record.u_planostamp || '') : '';
            if (!planStampSource && chipData && chipData.planStamp) {
                planStampSource = chipData.planStamp;
            }
            var normalizedPlanStamp = normalizePlanStamp(planStampSource);
            activeProductionPlanStamp = normalizedPlanStamp;

            resetProductionFormState();
            showProductionFormFeedback('', false);
            setProductionSaveState(false);

            if (productionForm.dataset) {
                if (normalizedPlanStamp) {
                    productionForm.dataset.planStamp = normalizedPlanStamp;
                }
                if (record && record.u_amstamp) {
                    productionForm.dataset.amStamp = String(record.u_amstamp).trim();
                    productionForm.dataset.mode = 'edit';
                } else {
                    productionForm.dataset.mode = 'create';
                }
                if (record && record.bistamp) {
                    productionForm.dataset.planLineStamp = String(record.bistamp).trim();
                }
                if (chipData && chipData.teamCode) {
                    productionForm.dataset.teamCode = chipData.teamCode;
                }
                if (chipData && chipData.planProcess) {
                    productionForm.dataset.projectCode = chipData.planProcess;
                }
            }

            setProductionField('fref', record && record.fref !== undefined && record.fref !== null ? record.fref : (chipData.planFref || chipData.teamCode || ''));
            setProductionField('processo', record && record.processo !== undefined && record.processo !== null ? record.processo : (chipData.planProcess || ''));
            setProductionField('data', record && record.data ? record.data : (chipData.planDate || ''));
            setProductionField('litem', record && record.litem !== undefined && record.litem !== null ? record.litem : '');
            setProductionField('acabamento', record && record.acabamento !== undefined && record.acabamento !== null ? record.acabamento : '');
            setProductionField('dgeral', record && record.dgeral !== undefined && record.dgeral !== null ? record.dgeral : '');
            setProductionField('qtt', record && record.qtt !== undefined && record.qtt !== null ? record.qtt : '');
            setProductionField('kgferro', record && record.kgferro !== undefined && record.kgferro !== null ? record.kgferro : '');
            setProductionField('m2serragem', record && record.m2serragem !== undefined && record.m2serragem !== null ? record.m2serragem : '');
            setProductionField('m3bomba', record && record.m3bomba !== undefined && record.m3bomba !== null ? record.m3bomba : '');
            setProductionField('m3betao', record && record.m3betao !== undefined && record.m3betao !== null ? record.m3betao : '');
            loadProductionFinishOptions(record && record.acabamento !== undefined && record.acabamento !== null ? record.acabamento : '');

            applyProductionDisplays(chipData, record);
            if (productionClosedCheckbox) {
                var closedVal = record && (record.fechado === 1 || record.fechado === true || String(record.fechado).toLowerCase() === 'true');
                productionClosedCheckbox.checked = !!closedVal;
            }
            if (productionClosedCheckbox) { productionClosedCheckbox.disabled = true; }

            if (record && record.u_amstamp) {
                fetchProductionLines(String(record.u_amstamp).trim());
            } else {
                renderProductionLines([]);
            }

            updateProductionMissingFromBudget();
            productionModal.classList.add('is-open');
            productionModal.removeAttribute('hidden');
            productionModal.setAttribute('aria-hidden', 'false');
            syncBodyModalState();
            if (productionDialog) {
                try {
                    productionDialog.focus({ preventScroll: true });
                } catch (err) {
                    /* ignore focus errors */
                }
            }
            focusFirstProductionField();
        }

        function closeProductionModal() {
            if (!productionModal) {
                return;
            }
            productionModal.classList.remove('is-open');
            productionModal.setAttribute('aria-hidden', 'true');
            productionModal.setAttribute('hidden', 'hidden');
            resetProductionFormState();
            activeProductionChip = null;
            activeProductionRecord = null;
            activeProductionPlanStamp = '';
            syncBodyModalState();
        }

        function showProductionFormFeedback(message, isError) {
            if (!productionFormFeedback) {
                return;
            }
            if (!message) {
                productionFormFeedback.textContent = '';
                productionFormFeedback.hidden = true;
                productionFormFeedback.classList.remove('is-error');
                productionFormFeedback.classList.remove('is-success');
                return;
            }
            productionFormFeedback.textContent = message;
            productionFormFeedback.hidden = false;
            productionFormFeedback.classList.remove('is-error');
            productionFormFeedback.classList.remove('is-success');
            if (isError === true) {
                productionFormFeedback.classList.add('is-error');
            } else if (isError === false) {
                productionFormFeedback.classList.add('is-success');
            }
        }

        function setProductionSaveState(isSaving) {
            if (!productionSaveButton) {
                return;
            }
            if (isSaving) {
                if (!Object.prototype.hasOwnProperty.call(productionSaveButton.dataset, 'originalText')) {
                    productionSaveButton.dataset.originalText = productionSaveButton.textContent || '';
                }
                var loadingText = productionSaveButton.dataset.loadingText || productionSaveButton.dataset.originalText || '';
                if (loadingText) {
                    productionSaveButton.textContent = loadingText;
                }
                productionSaveButton.disabled = true;
            } else {
                productionSaveButton.disabled = false;
                if (Object.prototype.hasOwnProperty.call(productionSaveButton.dataset, 'originalText')) {
                    productionSaveButton.textContent = productionSaveButton.dataset.originalText;
                    delete productionSaveButton.dataset.originalText;
                }
            }
        }

        function collectProductionFormPayload() {
            var payload = {};
            var planStampValue = productionForm && productionForm.dataset ? (productionForm.dataset.planStamp || '') : '';
            if (planStampValue) {
                payload.plan_stamp = planStampValue;
            }
            if (productionForm && productionForm.dataset && productionForm.dataset.planLineStamp) {
                payload.plan_line_stamp = productionForm.dataset.planLineStamp;
            }
            if (productionForm && productionForm.dataset && productionForm.dataset.teamCode) {
                payload.team_code = productionForm.dataset.teamCode;
            }
            if (productionForm && productionForm.dataset && productionForm.dataset.projectCode) {
                payload.project_code = productionForm.dataset.projectCode;
            }
            if (productionFields.fref) {
                var frefValue = String(productionFields.fref.value || '').trim();
                payload.fref = frefValue ? frefValue.toUpperCase() : '';
            }
            if (productionFields.processo) {
                var processoValue = String(productionFields.processo.value || '').trim();
                payload.processo = processoValue ? processoValue.toUpperCase() : '';
            }
            if (productionFields.data) {
                var dateValue = normaliseDateValue(productionFields.data.value || '');
                payload.data = dateValue || null;
            } else {
                payload.data = null;
            }
            if (productionFields.litem) {
                var litemValue = String(productionFields.litem.value || '').trim();
                payload.litem = litemValue ? litemValue : null;
            } else {
                payload.litem = null;
            }
            if (productionFields.acabamento) {
                var acabamentoValue = String(productionFields.acabamento.value || '').trim();
                payload.acabamento = acabamentoValue ? acabamentoValue : null;
            } else {
                payload.acabamento = null;
            }
            if (productionFields.dgeral) {
                payload.dgeral = String(productionFields.dgeral.value || '').trim();
            } else {
                payload.dgeral = '';
            }
            var decimalNames = ['qtt', 'kgferro', 'm2serragem', 'm3bomba', 'm3betao'];
            decimalNames.forEach(function (fieldName) {
                var field = productionFields[fieldName];
                if (!field) {
                    payload[fieldName] = null;
                    return;
                }
                var formatted = formatDecimalValue(field.value || '', 2);
                payload[fieldName] = formatted ? formatted : null;
            });

            if (Array.isArray(productionLineData) && productionLineData.length) {
                var linesPayload = [];
                productionLineData.forEach(function (lineData) {
                    if (!lineData || lineData.u_amlstamp === undefined || lineData.u_amlstamp === null) {
                        return;
                    }
                    var stamp = String(lineData.u_amlstamp).trim();
                    if (!stamp) {
                        return;
                    }
                    var entry = { u_amlstamp: stamp };
                    productionLineEditableFields.forEach(function (fieldName) {
                        if (!Object.prototype.hasOwnProperty.call(lineData, fieldName)) {
                            return;
                        }
                        var value = lineData[fieldName];
                        if (value === undefined || value === null || value === '') {
                            entry[fieldName] = null;
                            return;
                        }
                        var formattedValue = formatDecimalValue(value, getProductionLineDecimalPlaces(fieldName));
                        entry[fieldName] = formattedValue ? formattedValue : null;
                    });
                    linesPayload.push(entry);
                });
                if (linesPayload.length) {
                    payload.lines = linesPayload;
                }
            }

            var newLinesPayload = [];
            if (Array.isArray(productionLineData)) {
                productionLineData.forEach(function (ld) {
                    if (ld && ld.__isNew && ld.no && ld.nome) {
                        var newQtt = quantizeLineValue(ld.qtt, 'qtt');
                        if (newQtt === null) { newQtt = 0; }
                        var newKg = quantizeLineValue(ld.kgferro, 'kgferro');
                        if (newKg === null) { newKg = 0; }
                        var newM2 = quantizeLineValue(ld.m2serragem, 'm2serragem');
                        if (newM2 === null) { newM2 = 0; }
                        var newPrime = quantizeLineValue(ld.u_prime, 'u_prime');
                        if (newPrime === null) { newPrime = 0; }
                        newLinesPayload.push({
                            no: ld.no,
                            nome: ld.nome,
                            qtt: newQtt, kgferro: newKg, m2serragem: newM2, u_prime: newPrime
                        });
                    }
                });
            }
            if (newLinesPayload.length) {
                payload.new_lines = newLinesPayload;
            }
                        if (productionClosedCheckbox) {
                payload.fechado = productionClosedCheckbox.checked ? 1 : 0;
            }
            return payload;
        }

        function submitProductionForm() {
            if (!productionForm) {
                return;
            }
            var amStamp = productionForm.dataset ? (productionForm.dataset.amStamp || '') : '';
            if (!amStamp) {
                var identifierMessage = productionRecordsErrorText || 'Unable to determine the production record identifier.';
                showProductionFormFeedback(identifierMessage, true);
                return;
            }
            var payload = collectProductionFormPayload();
            setProductionSaveState(true);
            showProductionFormFeedback('', false);
            var url = '/api/production-records/' + encodeURIComponent(amStamp);
            fetch(url, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                },
                body: JSON.stringify(payload)
            })
                .then(function (response) {
                    if (!response.ok) {
                        return response.json().catch(function () {
                            return {};
                        }).then(function (data) {
                            var error = new Error('Request failed');
                            error.response = response;
                            error.data = data;
                            throw error;
                        });
                    }
                    var contentType = response.headers.get('Content-Type') || '';
                    if (contentType.indexOf('application/json') !== -1) {
                        return response.json().catch(function () {
                            return null;
                        });
                    }
                    return null;
                })
                .then(function () {
                    try {
                        var planStampValue = productionForm && productionForm.dataset ? (productionForm.dataset.planStamp || '') : '';
                        if (planStampValue) {
                            window.dispatchEvent(new CustomEvent('planning:production-updated', { detail: { planStamp: String(planStampValue).toUpperCase() } }));
                        }
                    } catch (err) { /* ignore */ }
                    closeProductionModal();
                })
                .catch(function (error) {
                    var message = productionRecordsErrorText || 'Unable to save production record.';
                    if (error && error.data) {
                        if (typeof error.data.details === 'string' && error.data.details.length) {
                            message = error.data.details;
                        } else if (error.data.fields && typeof error.data.fields === 'object') {
                            try {
                                var invalidKeys = Object.keys(error.data.fields).filter(function (fieldKey) {
                                    return Object.prototype.hasOwnProperty.call(error.data.fields, fieldKey);
                                });
                                if (invalidKeys.length) {
                                    message = 'Invalid fields: ' + invalidKeys.join(', ');
                                }
                            } catch (err) {
                                /* ignore */
                            }
                        } else if (error.data.line_fields && typeof error.data.line_fields === 'object') {
                            try {
                                var lineSummaries = Object.keys(error.data.line_fields).filter(function (lineKey) {
                                    return Object.prototype.hasOwnProperty.call(error.data.line_fields, lineKey);
                                }).map(function (lineKey) {
                                    var numericKey = Number(lineKey);
                                    var labelIndex = Number.isFinite(numericKey) ? numericKey + 1 : lineKey;
                                    var fieldMap = error.data.line_fields[lineKey];
                                    if (fieldMap && typeof fieldMap === 'object') {
                                        var fieldNames = Object.keys(fieldMap).filter(function (fieldName) {
                                            return Object.prototype.hasOwnProperty.call(fieldMap, fieldName);
                                        });
                                        if (fieldNames.length) {
                                            return 'line ' + labelIndex + ' (' + fieldNames.join(', ') + ')';
                                        }
                                    }
                                    return 'line ' + labelIndex;
                                });
                                if (lineSummaries.length) {
                                    message = 'Invalid line values: ' + lineSummaries.join('; ');
                                } else {
                                    message = 'Invalid line values.';
                                }
                            } catch (err) {
                                /* ignore */
                            }
                        } else if (typeof error.data.error === 'string' && error.data.error.length) {
                            message = error.data.error;
                        }
                    }
                    showProductionFormFeedback(message, true);
                    if (error && error.response) {
                        try {
                            console.error('production-save failed', error);
                        } catch (err) {
                            /* ignore console errors */
                        }
                    }
                })
                .finally(function () {
                    setProductionSaveState(false);
                });
        }

        function readPlanLinesForStamp(raw, planStamp) {
            var normalizedStamp = normalizePlanStamp(planStamp);
            var collected = [];
            function pushEntries(entries) {
                if (!entries) {
                    return;
                }
                if (Array.isArray(entries)) {
                    entries.forEach(function (entry) {
                        if (!entry || typeof entry !== 'object') {
                            return;
                        }
                        var entryStamp = normalizePlanStamp(entry.planStamp || entry.plan_stamp || entry.planostamp || entry.u_planostamp || normalizedStamp);
                        if (normalizedStamp && entryStamp && entryStamp !== normalizedStamp) {
                            return;
                        }
                        if (!entry.planStamp && normalizedStamp) {
                            entry.planStamp = normalizedStamp;
                        }
                        collected.push(entry);
                    });
                    return;
                }
                if (typeof entries === 'string') {
                    var parsedList = parseJsonList(entries);
                    if (parsedList.length) {
                        pushEntries(parsedList);
                        return;
                    }
                    var parsedMap = parsePlanStampMap(entries);
                    if (parsedMap && typeof parsedMap === 'object') {
                        pushEntries(parsedMap);
                    }
                    return;
                }
                if (typeof entries === 'object') {
                    Object.keys(entries).forEach(function (key) {
                        var entry = entries[key];
                        var keyStamp = normalizePlanStamp(key);
                        if (!normalizedStamp || keyStamp === normalizedStamp) {
                            pushEntries(entry);
                        }
                    });
                }
            }
            pushEntries(raw);
            return collected;
        }

        function planLineIdentity(line) {
            if (!line || typeof line !== 'object') {
                return '';
            }
            var identifiers = [
                line.u_lplanostamp,
                line.uLplanostamp,
                line.planLineStamp,
                line.planlinestamp,
                line.plan_line_stamp,
                line.planLineId,
                line.bistamp,
                line.lineStamp,
                line.id,
                line.tempId,
                line.__tempId
            ];
            for (var index = 0; index < identifiers.length; index += 1) {
                var value = identifiers[index];
                if (value !== undefined && value !== null && String(value).length) {
                    return String(value).trim().toUpperCase();
                }
            }
            return '';
        }

        function planLineHash(line) {
            if (!line || typeof line !== 'object') {
                return '';
            }
            var normalized = {
                stamp: normalizePlanStamp(line.u_lplanostamp || line.uLplanostamp || line.planLineStamp || line.planlinestamp || line.bistamp || line.plan_stamp || line.planostamp || ''),
                temp: line.tempId || line.__tempId || line.id || '',
                litem: line.litem !== undefined && line.litem !== null ? Number(line.litem) : null,
                data: line.data ? String(line.data).slice(0, 10) : '',
                processo: line.processo || '',
                fref: line.fref || '',
                dgeral: line.dgeral || line.descricao || line.description || '',
                qtt: normalizeNumberValue(line.qtt),
                m3bomba: normalizeNumberValue(line.m3bomba),
                m2serragem: normalizeNumberValue(line.m2serragem),
                kgferro: normalizeNumberValue(line.kgferro),
                m3betao: normalizeNumberValue(line.m3betao),
                fixo: normalizeNumberValue(line.fixo)
            };
            return JSON.stringify(normalized);
        }

        function getPlanLineChangeCandidates(planStamp) {
            var normalizedStamp = normalizePlanStamp(planStamp);
            if (!normalizedStamp || typeof planningData === 'undefined' || !planningData || typeof planningData.collectPlanLineChanges !== 'function') {
                return [];
            }
            try {
                var snapshot = planningData.collectPlanLineChanges();
                var candidates = [];
                if (snapshot && typeof snapshot === 'object') {
                    var sets = [];
                    if (Array.isArray(snapshot.insertions)) {
                        sets.push(snapshot.insertions);
                    }
                    if (Array.isArray(snapshot.updates)) {
                        sets.push(snapshot.updates);
                    }
                    sets.forEach(function (entries) {
                        entries.forEach(function (change) {
                            if (!change || typeof change !== 'object') {
                                return;
                            }
                            var changeStamp = normalizePlanStamp(change.planStamp || change.plan_stamp || change.planostamp || change.u_planostamp || '');
                            if (changeStamp && changeStamp !== normalizedStamp) {
                                return;
                            }
                            if (change.line && typeof change.line === 'object') {
                                candidates.push(change.line);
                            } else {
                                candidates.push(change);
                            }
                        });
                    });
                }
                return candidates;
            } catch (err) {
                return [];
            }
        }

        function collectPlanLineDrafts(chip, planStamp) {
            var normalizedStamp = normalizePlanStamp(planStamp);
            if (!normalizedStamp) {
                return [];
            }
            var cell = chip ? chip.closest('.day-cell') : null;
            var chipData = chip && chip.dataset ? chip.dataset : {};
            var cellData = cell && cell.dataset ? cell.dataset : {};

            var candidateLines = [];
            readPlanLinesForStamp(chipData.planLines, normalizedStamp).forEach(function (entry) {
                candidateLines.push(entry);
            });
            readPlanLinesForStamp(chipData.planLineCache, normalizedStamp).forEach(function (entry) {
                candidateLines.push(entry);
            });
            readPlanLinesForStamp(cellData.planLines, normalizedStamp).forEach(function (entry) {
                candidateLines.push(entry);
            });
            readPlanLinesForStamp(cellData.planLineMap, normalizedStamp).forEach(function (entry) {
                candidateLines.push(entry);
            });
            getPlanLineChangeCandidates(normalizedStamp).forEach(function (entry) {
                candidateLines.push(entry);
            });

            var baselineLines = [];
            readPlanLinesForStamp(cellData.initialPlanLines, normalizedStamp).forEach(function (entry) {
                baselineLines.push(entry);
            });
            readPlanLinesForStamp(cellData.initialPlanLineMap, normalizedStamp).forEach(function (entry) {
                baselineLines.push(entry);
            });

            var baselineHashes = new Map();
            baselineLines.forEach(function (line) {
                var identity = planLineIdentity(line);
                var hash = planLineHash(line);
                var key = identity || hash;
                if (key) {
                    baselineHashes.set(key, hash);
                }
            });

            if (typeof console !== 'undefined') {
                try {
                    var grouped = typeof console.groupCollapsed === 'function';
                    if (grouped) {
                        console.groupCollapsed('collectPlanLineDrafts', normalizedStamp);
                    }
                    console.log('chip dataset', chipData);
                    console.log('cell dataset', cellData);
                    console.log('candidate plan lines', candidateLines);
                    console.log('baseline plan lines', baselineLines);
                    if (grouped) {
                        console.groupEnd();
                    }
                } catch (err) {
                    /* ignore console errors */
                }
            }

            var drafts = [];
            var seenDraftKeys = new Set();

            candidateLines.forEach(function (line) {
                if (!line || typeof line !== 'object') {
                    return;
                }
                var identity = planLineIdentity(line);
                var hash = planLineHash(line);
                var key = identity || hash || JSON.stringify(line);
                var baselineHash = baselineHashes.get(identity) || baselineHashes.get(hash);
                var planLineStamp = normalizePlanStamp(line.u_lplanostamp || line.uLplanostamp || line.planLineStamp || line.planlinestamp || line.plan_line_stamp || line.planLineId || '');
                var hasPersistentStamp = !!planLineStamp;
                var flaggedDraft = Boolean(line.isDraft || line.__isDraft || line.__unsaved || line._isDraft);
                var isUnsaved = false;
                if (flaggedDraft) {
                    isUnsaved = true;
                } else if (!hasPersistentStamp) {
                    isUnsaved = true;
                } else if (baselineHash && baselineHash !== hash) {
                    isUnsaved = true;
                }
                if (typeof console !== 'undefined') {
                    try {
                        console.log('collectPlanLineDrafts candidate', {
                            planStamp: normalizedStamp,
                            line: line,
                            identity: identity,
                            hash: hash,
                            key: key,
                            baselineHash: baselineHash,
                            hasPersistentStamp: hasPersistentStamp,
                            planLineStamp: planLineStamp,
                            flaggedDraft: flaggedDraft,
                            isUnsaved: isUnsaved,
                            seenDraftKeysHasKey: seenDraftKeys.has(key)
                        });
                    } catch (err) {
                        /* ignore console errors */
                    }
                }
                if (seenDraftKeys.has(key)) {
                    return;
                }
                if (!isUnsaved) {
                    return;
                }
                seenDraftKeys.add(key);

                var draftRecord = buildDraftRecordFromAssignment(chip, normalizedStamp);
                if (line.data) {
                    draftRecord.data = String(line.data).slice(0, 10);
                }
                var dateLabel = draftRecord.draftDateLabel || '';
                if (line.datalabel && line.datalabel.length) {
                    dateLabel = line.datalabel;
                } else if (!dateLabel && draftRecord.data) {
                    dateLabel = draftRecord.data;
                }
                draftRecord.draftDateLabel = dateLabel;

                var description = line.dgeral || line.descricao || line.description || draftRecord.draftProject || draftRecord.dgeral || '';
                if (description) {
                    draftRecord.dgeral = description;
                }

                if (line.litem !== undefined && line.litem !== null && line.litem !== '') {
                    draftRecord.litem = String(line.litem).trim();
                }

                var summaryParts = [];
                if (dateLabel) {
                    summaryParts.push(dateLabel);
                } else if (draftRecord.data) {
                    summaryParts.push(draftRecord.data);
                }
                if (line.litem !== undefined && line.litem !== null && line.litem !== '') {
                    summaryParts.push('Item ' + line.litem);
                }
                if (description && summaryParts.indexOf(description) === -1) {
                    summaryParts.push(description);
                }
                if (draftRecord.draftTeam) {
                    summaryParts.push(draftRecord.draftTeam);
                }
                draftRecord.draftSummary = summaryParts.join(' · ') || draftRecord.draftSummary;

                ['qtt', 'm3bomba', 'm2serragem', 'kgferro', 'm3betao'].forEach(function (field) {
                    if (line[field] !== undefined && line[field] !== null && line[field] !== '') {
                        var numericValue = normalizeNumberValue(line[field]);
                        draftRecord[field] = numericValue !== null ? numericValue : line[field];
                    }
                });
                draftRecord.draftPlanLine = line;
                draftRecord.isDraft = true;
                draftRecord.draftNote = draftRecord.draftNote || productionDraftNote;
                drafts.push(draftRecord);
            });

            if (typeof console !== 'undefined') {
                console.log('collectPlanLineDrafts -> drafts', drafts);
            }
            return drafts;
        }

        function lookupDraftRecords(planStamp, chip) {
            var normalizedStamp = normalizePlanStamp(planStamp);
            if (!normalizedStamp) {
                return [];
            }

            var stored = getStoredDraftRecords(normalizedStamp);
            if (typeof console !== 'undefined') {
                try {
                    console.log('lookupDraftRecords initial store', { planStamp: normalizedStamp, storedCount: stored.length });
                } catch (err) {
                    /* ignore console errors */
                }
            }
            if (stored.length) {
                if (typeof console !== 'undefined') {
                    try {
                        console.log('lookupDraftRecords using stored drafts', { planStamp: normalizedStamp, storedCount: stored.length });
                    } catch (err) {
                        /* ignore console errors */
                    }
                }
                if (chip && !chipAssignmentIsDraft(chip, normalizedStamp)) {
                    setDraftRecords(normalizedStamp, []);
                    stored = [];
                } else {
                    return stored;
                }
            }

            var dataset = chip && chip.dataset ? chip.dataset.productionDrafts : '';
            if (!dataset && chip) {
                var draftCell = chip.closest('[data-production-drafts]');
                if (draftCell && draftCell.dataset) {
                    dataset = draftCell.dataset.productionDrafts || '';
                }
            }
            if (dataset) {
                if (typeof console !== 'undefined') {
                    try {
                        console.log('lookupDraftRecords dataset', { planStamp: normalizedStamp, dataset: dataset });
                    } catch (err) {
                        /* ignore console errors */
                    }
                }
                stored = mergeDraftRecordsFromSource(normalizedStamp, dataset);
                if (stored.length) {
                    return stored;
                }
            }

            var planLineDrafts = collectPlanLineDrafts(chip || null, normalizedStamp);
            if (typeof console !== 'undefined') {
                try {
                    console.log('lookupDraftRecords planLineDrafts', { planStamp: normalizedStamp, draftCount: planLineDrafts.length });
                } catch (err) {
                    /* ignore console errors */
                }
            }
            if (planLineDrafts.length) {
                setDraftRecords(normalizedStamp, planLineDrafts);
                return planLineDrafts;
            }

            if (typeof window !== 'undefined') {
                var globalStore = window.planningProductionDrafts || window.productionDrafts || null;
                if (globalStore) {
                    var globalValue;
                    if (typeof globalStore.get === 'function') {
                        globalValue = globalStore.get(normalizedStamp);
                    } else if (Object.prototype.hasOwnProperty.call(globalStore, normalizedStamp)) {
                        globalValue = globalStore[normalizedStamp];
                    }
                    stored = mergeDraftRecordsFromSource(normalizedStamp, globalValue);
                    if (stored.length) {
                        return stored;
                    }
                }
            }

            return [];
        }
        function syncBodyModalState() {
            if (document.querySelector('.modal-overlay.is-open')) {
                document.body.classList.add('modal-open');
            } else {
                document.body.classList.remove('modal-open');
            }
        }

        function showProductionRecordsMessage(message) {
            if (!productionRecordsMessage) {
                return;
            }
            if (message) {
                productionRecordsMessage.textContent = message;
                productionRecordsMessage.hidden = false;
                if (productionRecordsList) {
                    productionRecordsList.hidden = true;
                }
            } else {
                productionRecordsMessage.textContent = '';
                productionRecordsMessage.hidden = true;
                if (productionRecordsList) {
                    productionRecordsList.hidden = false;
                }
            }
        }

        function renderProductionDrafts(records) {
            if (!productionDraftsContainer || !productionDraftsList) {
                return;
            }
            productionDraftsList.innerHTML = '';
            if (typeof console !== 'undefined') {
                try {
                    console.log('renderProductionDrafts', { planStamp: activePlanStamp, count: Array.isArray(records) ? records.length : null, records: records });
                } catch (err) {
                    /* ignore console errors */
                }
            }
            if (!Array.isArray(records) || !records.length) {
                productionDraftsContainer.hidden = true;
                lastRenderedDraftCount = 0;
                return;
            }
            productionDraftsContainer.hidden = false;
            lastRenderedDraftCount = records.length;
            records.forEach(function (record) {
                var item = document.createElement('li');
                item.className = 'production-records-draft-item';
                var card = document.createElement('div');
                card.className = 'production-records-draft-card';
                card.setAttribute('role', 'presentation');

                var badge = document.createElement('span');
                badge.className = 'production-records-draft-badge';
                badge.textContent = productionDraftLabel;

                var title = document.createElement('div');
                title.className = 'production-records-draft-title';

                var litemValue = record && record.litem !== undefined && record.litem !== null && record.litem !== '' ? String(record.litem).trim() : '';
                if (litemValue) {
                    var code = document.createElement('span');
                    code.className = 'production-records-draft-code';
                    code.textContent = litemValue;
                    title.appendChild(code);
                }

                var descriptionText = record && (record.dgeral || record.descricao || record.description) ? (record.dgeral || record.descricao || record.description) : '';
                if (descriptionText) {
                    var description = document.createElement('span');
                    description.className = 'production-records-draft-description';
                    description.textContent = descriptionText;
                    title.appendChild(description);
                }

                var note = document.createElement('p');
                note.className = 'production-records-draft-note';
                note.textContent = record && record.draftNote ? record.draftNote : productionDraftNote;

                card.appendChild(badge);
                card.appendChild(title);
                card.appendChild(note);
                item.appendChild(card);
                productionDraftsList.appendChild(item);
            });
        }

        function ingestDraftRecordsFrom(source) {
            if (!source) {
                return;
            }
            if (typeof source.forEach === 'function') {
                source.forEach(function (value, key) {
                    var normalizedKey = normalizePlanStamp(key);
                    if (!normalizedKey) {
                        return;
                    }
                    setDraftRecords(normalizedKey, value);
                });
                return;
            }
            if (Array.isArray(source)) {
                return;
            }
            if (typeof source === 'object') {
                Object.keys(source).forEach(function (key) {
                    var normalizedKey = normalizePlanStamp(key);
                    if (!normalizedKey) {
                        return;
                    }
                    setDraftRecords(normalizedKey, source[key]);
                });
            }
        }

        function closeProductionRecordsModal() {
            if (!productionRecordsModal) {
                return;
            }
            productionRecordsModal.classList.remove('is-open');
            productionRecordsModal.setAttribute('aria-hidden', 'true');
            productionRecordsModal.setAttribute('hidden', 'hidden');
            if (productionRecordsList) {
                productionRecordsList.innerHTML = '';
                productionRecordsList.hidden = true;
            }
            if (productionRecordsMessage) {
                productionRecordsMessage.textContent = '';
                productionRecordsMessage.hidden = true;
            }
            if (productionDraftsList) {
                productionDraftsList.innerHTML = '';
            }
            if (productionDraftsContainer) {
                productionDraftsContainer.hidden = true;
            }
            lastRenderedDraftCount = 0;
            activePlanStamp = '';
            syncBodyModalState();
        }

        function setOtherOptionsFeedback(message, isError) {
            if (!otherOptionsFeedback) {
                return;
            }
            if (!message) {
                otherOptionsFeedback.textContent = '';
                otherOptionsFeedback.hidden = true;
                otherOptionsFeedback.classList.remove('is-error');
                otherOptionsFeedback.classList.remove('is-success');
                return;
            }
            otherOptionsFeedback.textContent = message;
            otherOptionsFeedback.hidden = false;
            otherOptionsFeedback.classList.remove('is-error');
            otherOptionsFeedback.classList.remove('is-success');
            if (isError) {
                otherOptionsFeedback.classList.add('is-error');
            } else {
                otherOptionsFeedback.classList.add('is-success');
            }
        }

        function setOtherOptionsLoading(isLoading) {
            if (!otherOptionsFields || !otherOptionsFields.length) {
                return;
            }
            otherOptionsFields.forEach(function (field) {
                field.disabled = !!isLoading;
            });
            if (otherOptionsSaveButton) {
                otherOptionsSaveButton.disabled = !!isLoading;
            }
            if (isLoading && otherOptionsLoadingText) {
                setOtherOptionsFeedback(otherOptionsLoadingText, false);
            } else if (!isLoading) {
                setOtherOptionsFeedback('', false);
            }
        }

        function fillOtherOptionsFields(values) {
            var fixoField = null;
            var premioField = null;
            otherOptionsFields.forEach(function (field) {
                var key = field.dataset ? field.dataset.otherOptionsField : field.getAttribute('data-other-options-field');
                if (key === 'fixo') {
                    fixoField = field;
                } else if (key === 'premio') {
                    premioField = field;
                }
            });
            if (fixoField) {
                fixoField.value = values && values.fixo !== undefined && values.fixo !== null && values.fixo !== '' ? formatDecimalValue(values.fixo, 2) : '';
            }
            if (premioField) {
                premioField.value = values && values.premio !== undefined && values.premio !== null && values.premio !== '' ? formatDecimalValue(values.premio, 2) : '';
            }
        }

        function renderOtherOptionsMeta(chip) {
            var cell = chip ? chip.closest('.day-cell') : null;
            var chipData = chip && chip.dataset ? chip.dataset : {};
            if (otherOptionsDate) {
                otherOptionsDate.textContent = chipData.planDate || (cell && cell.dataset ? (cell.dataset.dateLabel || cell.dataset.date || '') : '') || '--';
            }
            if (otherOptionsProject) {
                var projectCode = chipData.planProcess || (cell && cell.dataset ? cell.dataset.projectCode : '') || '';
                var projectName = chipData.planProjectName || (cell && cell.dataset ? (cell.dataset.projectName || '') : '');
                otherOptionsProject.textContent = (projectCode ? (projectCode + ' ') : '') + (projectName || '').trim();
            }
            if (otherOptionsTeam) {
                var teamCode = chipData.teamCode || '';
                var teamName = chipData.planTeamName || '';
                otherOptionsTeam.textContent = (teamCode ? (teamCode + ' ') : '') + (teamName || '').trim();
            }
        }

        function fetchPlanOptions(planStamp) {
            var normalizedStamp = normalizePlanStamp(planStamp);
            if (!normalizedStamp) {
                return Promise.resolve(null);
            }
            setOtherOptionsLoading(true);
            return fetch('/api/plans/' + encodeURIComponent(normalizedStamp), { credentials: 'same-origin' })
                .then(function (response) {
                    if (!response.ok) {
                        throw new Error('load_failed');
                    }
                    return response.json();
                })
                .then(function (data) {
                    debugLog('fetch-plan-options:success', data);
                    return {
                        fixo: normalizeNumberValue(data && data.fixo),
                        premio: normalizeNumberValue(data && data.premio),
                        stamp: normalizedStamp
                    };
                })
                .catch(function () {
                    setOtherOptionsFeedback(otherOptionsErrorText || 'Erro ao carregar', true);
                    return null;
                })
                .finally(function () {
                    setOtherOptionsLoading(false);
                });
        }

        function persistPlanOptions(planStamp, values, chip, meta) {
            var normalizedStamp = normalizePlanStamp(planStamp);
            if (!normalizedStamp) {
                return Promise.resolve(null);
            }
            var planMeta = meta || readPlanMetaFromChip(chip);
            var payload = {};
            var fixedValue = normalizeNumberValue(values ? values.fixo : null);
            var bonusValue = normalizeNumberValue(values ? values.premio : null);
            var fixedFormatted = formatDecimalValue(fixedValue !== null ? fixedValue : 0, 2);
            var bonusFormatted = formatDecimalValue(bonusValue !== null ? bonusValue : 0, 2);
            payload.fixo = fixedFormatted ? parseFloat(fixedFormatted) : 0;
            payload.premio = bonusFormatted ? parseFloat(bonusFormatted) : 0;
            if (planMeta) {
                if (planMeta.planDate) {
                    payload.data = planMeta.planDate;
                }
                if (planMeta.teamCode) {
                    payload.fref = planMeta.teamCode;
                }
                if (planMeta.projectCode) {
                    payload.processo = planMeta.projectCode;
                }
            }
            setOtherOptionsLoading(true);
            debugLog('persist-plan-options', { stamp: normalizedStamp, payload: payload, meta: planMeta });
            return fetch('/api/plans/' + encodeURIComponent(normalizedStamp) + '/values', {
                method: 'PATCH',
                credentials: 'same-origin',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(payload)
            }).then(function (response) {
                debugLog('put-response', { status: response.status });
                if (!response.ok) {
                    return response.text().then(function (text) {
                        debugLog('put-error-body', text);
                        throw new Error('save_failed');
                    });
                }
                return response.json();
            }).then(function (data) {
                debugLog('save-success', data);
                setPlanOptionDraft(normalizedStamp, values, planMeta);
                if (activeChip) {
                    updateChipEconomicState(activeChip, payload.fixo, payload.premio);
                }
                setOtherOptionsFeedback(otherOptionsSavedText || '', false);
                return true;
            }).catch(function (err) {
                debugLog('save-error', err && err.message ? err.message : err);
                setOtherOptionsFeedback(otherOptionsErrorText || 'Erro ao gravar', true);
                return false;
            }).finally(function () {
                setOtherOptionsLoading(false);
            });
        }

        function ensurePlanExists(planStamp) {
            var normalizedStamp = normalizePlanStamp(planStamp);
            if (!normalizedStamp) {
                return Promise.resolve(false);
            }
            return fetch('/api/plans/' + encodeURIComponent(normalizedStamp), { method: 'GET', credentials: 'same-origin' })
                .then(function (response) {
                    if (response.status === 404) {
                        return false;
                    }
                    if (!response.ok) {
                        return false;
                    }
                    return true;
                })
                .catch(function () {
                    return false;
                });
        }

        function openOtherOptionsModal(chip) {
            if (!otherOptionsModal) {
                return;
            }
            var planStampValue = chip && chip.dataset ? (chip.dataset.planStamp || chip.dataset.plan_stamp || '') : '';
            if (!planStampValue) {
                var warnMissing = otherOptionsPendingText || 'Grave o registo antes de editar estes valores.';
                if (typeof window !== 'undefined' && window.alert) {
                    window.alert(warnMissing);
                } else {
                    debugLog('pending-warning', warnMissing);
                }
                return;
            }
            ensurePlanExists(planStampValue).then(function (exists) {
                if (!exists) {
                    var warnText = otherOptionsPendingText || 'Grave o registo antes de editar estes valores.';
                    if (typeof window !== 'undefined' && window.alert) {
                        window.alert(warnText);
                    } else {
                        debugLog('missing-plan-warning', warnText);
                    }
                    return;
                }
                activeChip = chip || activeChip;
                lastFocusedBeforeOtherOptions = document.activeElement;
                debugLog('open-modal', { stamp: chip && chip.dataset ? chip.dataset.planStamp : null, meta: readPlanMetaFromChip(chip) });
                var meta = readPlanMetaFromChip(chip);
                renderOtherOptionsMeta(chip);
                fillOtherOptionsFields({ fixo: '', premio: '' });
                setOtherOptionsFeedback('', false);
                otherOptionsModal.classList.add('is-open');
                otherOptionsModal.removeAttribute('hidden');
                otherOptionsModal.setAttribute('aria-hidden', 'false');
                syncBodyModalState();
                var normalizedStamp = normalizePlanStamp(planStampValue);
                var fallbackKey = otherOptionsKeyFromChip(chip);
                if (normalizedStamp) {
                    var cached = getPlanOptionDraft(normalizedStamp);
                    if (cached && cached.values) {
                        fillOtherOptionsFields(cached.values);
                    } else {
                        debugLog('fetch-plan-options', { stamp: normalizedStamp });
                        fetchPlanOptions(normalizedStamp).then(function (values) {
                            if (values) {
                                setPlanOptionDraft(normalizedStamp, values, meta);
                                fillOtherOptionsFields(values);
                            }
                        });
                    }
                } else {
                    var pending = getPlanOptionDraft(fallbackKey);
                    if (pending && pending.values) {
                        fillOtherOptionsFields(pending.values);
                    } else {
                        fillOtherOptionsFields({ fixo: '', premio: '' });
                    }
                    if (otherOptionsPendingText) {
                        setOtherOptionsFeedback(otherOptionsPendingText, false);
                    }
                }
                if (otherOptionsDialog) {
                    try {
                        otherOptionsDialog.focus({ preventScroll: true });
                    } catch (err) {
                        /* ignore focus errors */
                    }
                }
            });
        }

        function closeOtherOptionsModal() {
            if (!otherOptionsModal) {
                return;
            }
            if (otherOptionsModal.contains(document.activeElement)) {
                try {
                    document.activeElement.blur();
                } catch (err) {
                    /* ignore blur errors */
                }
            }
            otherOptionsModal.classList.remove('is-open');
            otherOptionsModal.setAttribute('aria-hidden', 'true');
            otherOptionsModal.setAttribute('hidden', 'hidden');
            syncBodyModalState();
            if (lastFocusedBeforeOtherOptions && typeof lastFocusedBeforeOtherOptions.focus === 'function') {
                try {
                    lastFocusedBeforeOtherOptions.focus({ preventScroll: true });
                } catch (err) {
                    /* ignore focus errors */
                }
            }
            lastFocusedBeforeOtherOptions = null;
        }

        function formatProductionRecord(record) {
            if (!record) {
                return '';
            }
            var parts = [];
            if (record.data) {
                parts.push(String(record.data).slice(0, 10));
            }
            if (record.dgeral) {
                parts.push(String(record.dgeral));
            }
            if (!parts.length && record.u_amstamp) {
                parts.push(String(record.u_amstamp));
            }
            if (record.qtt !== undefined && record.qtt !== null && record.qtt !== '') {
                parts.push('Qtd: ' + record.qtt);
            }
            return parts.join(' Ã‚Â· ');
        }

        function renderProductionRecords(records, chip) {
            if (!productionRecordsList) {
                return;
            }
            productionRecordsList.innerHTML = '';
            if (!Array.isArray(records) || !records.length) {
                if (lastRenderedDraftCount > 0) {
                    if (productionRecordsMessage) {
                        productionRecordsMessage.textContent = '';
                        productionRecordsMessage.hidden = true;
                    }
                    productionRecordsList.hidden = true;
                } else {
                    showProductionRecordsMessage(productionRecordsEmptyText);
                }
                return;
            }
            if (productionRecordsMessage) {
                productionRecordsMessage.textContent = '';
                productionRecordsMessage.hidden = true;
            }
            productionRecordsList.hidden = false;
            records.forEach(function (record) {
                var item = document.createElement('button');
                item.type = 'button';
                item.className = 'production-records-item';

                var title = document.createElement('div');
                title.className = 'production-records-item-title';

                var litemValue = record && record.litem !== undefined && record.litem !== null && record.litem !== '' ? String(record.litem).trim() : '';
                if (litemValue) {
                    var code = document.createElement('span');
                    code.className = 'production-records-item-code';
                    code.textContent = litemValue;
                    title.appendChild(code);
                }

                var descriptionText = record && (record.dgeral || record.descricao || record.description) ? (record.dgeral || record.descricao || record.description) : '';
                if (descriptionText) {
                    var description = document.createElement('span');
                    description.className = 'production-records-item-description';
                    description.textContent = descriptionText;
                    title.appendChild(description);
                }

                item.appendChild(title);

                var meta = document.createElement('div');
                meta.className = 'production-records-item-meta';

                var quantityValue = record ? record.qtt : null;
                var quantityText = '—';
                if (quantityValue !== undefined && quantityValue !== null && quantityValue !== '') {
                    var formattedQuantity = formatDecimalValue(quantityValue, 2);
                    quantityText = formattedQuantity || String(quantityValue);
                }
                meta.textContent = 'Qtd: ' + quantityText;
                item.appendChild(meta);

                var ariaLabel = formatProductionRecord(record) || (record && record.u_amstamp ? String(record.u_amstamp) : '');
                if (ariaLabel) {
                    item.setAttribute('aria-label', ariaLabel);
                }

                item.addEventListener('click', function () {
                    handleProductionRecordSelect(chip, record);
                });
                productionRecordsList.appendChild(item);
            });
            var firstItem = productionRecordsList.querySelector('.production-records-item');
            if (firstItem) {
                firstItem.focus({ preventScroll: true });
            }
        }

        function loadProductionRecords(chip) {
            if (!productionRecordsModal) {
                return;
            }
            if (productionRecordsList) {
                productionRecordsList.innerHTML = '';
                productionRecordsList.hidden = true;
            }
            showProductionRecordsMessage(productionRecordsLoadingText || 'Loading...');
            var rawPlanStamp = chip && chip.dataset ? chip.dataset.planStamp : '';
            var planStamp = normalizePlanStamp(rawPlanStamp);
            if (!planStamp) {
                if (lastRenderedDraftCount > 0) {
                    if (productionRecordsMessage) {
                        productionRecordsMessage.textContent = '';
                        productionRecordsMessage.hidden = true;
                    }
                    if (productionRecordsList) {
                        productionRecordsList.hidden = true;
                    }
                } else {
                    showProductionRecordsMessage(productionRecordsEmptyText || '');
                }
                return;
            }
            var url = '/api/plans/' + encodeURIComponent(planStamp) + '/production-records';
            fetch(url, { headers: { 'Accept': 'application/json' } })
                .then(function (response) {
                    if (!response.ok) {
                        throw new Error(String(response.status || 'error'));
                    }
                    return response.json();
                })
                .then(function (data) {
                    if (!Array.isArray(data)) {
                        throw new Error('Invalid response');
                    }
                    renderProductionRecords(data, chip);
                })
                .catch(function () {
                    showProductionRecordsMessage(productionRecordsErrorText || 'Error loading records');
                });
        }

        function handleProductionRecordSelect(chip, record) {
            closeProductionRecordsModal();
            openProductionModal(chip, record);
        }

        function openProductionRecordsModal(chip) {
            if (!productionRecordsModal) {
                openProductionModal(chip, null);
                return;
            }
            activeChip = chip;
            var planStamp = chip && chip.dataset ? (chip.dataset.planStamp || '') : '';
            var normalizedStamp = normalizePlanStamp(planStamp);
            if (typeof console !== 'undefined') {
                var debugCell = chip ? chip.closest('.day-cell') : null;
                var grouped = typeof console.groupCollapsed === 'function';
                if (grouped) {
                    console.groupCollapsed('production-records modal', normalizedStamp || planStamp);
                }
                console.log('chip dataset', chip && chip.dataset ? Object.assign({}, chip.dataset) : null);
                console.log('cell dataset', debugCell && debugCell.dataset ? Object.assign({}, debugCell.dataset) : null);
                console.log('planStamp raw/normalized', planStamp, normalizedStamp);
                if (typeof planningData !== 'undefined' && planningData && typeof planningData.collectPlanLineChanges === 'function') {
                    try {
                        console.log('planLine changes snapshot', planningData.collectPlanLineChanges());
                    } catch (err) {
                        console.warn('collectPlanLineChanges failed', err);
                    }
                }
                if (grouped) {
                    console.groupEnd();
                }
            }
            activePlanStamp = normalizedStamp;
            var draftRecords = lookupDraftRecords(normalizedStamp, chip);
            if (typeof console !== 'undefined') {
                try {
                    console.log('openProductionRecordsModal drafts', { planStamp: normalizedStamp, draftCount: draftRecords.length });
                } catch (err) {
                    /* ignore console errors */
                }
            }
            renderProductionDrafts(draftRecords);
            productionRecordsModal.classList.add('is-open');
            productionRecordsModal.removeAttribute('hidden');
            productionRecordsModal.setAttribute('aria-hidden', 'false');
            syncBodyModalState();
            if (productionRecordsDialog) {
                productionRecordsDialog.focus({ preventScroll: true });
            }
            loadProductionRecords(chip);
        }

        function removeMenu() {
            if (menuElement) {
                menuElement.remove();
                menuElement = null;
            }
        }

        function closeMenu() {
            removeMenu();
        }

        function ensureMenu() {
            if (menuElement) {
                removeMenu();
            }
            var wrapper = document.createElement('div');
            wrapper.className = 'assignment-chip-menu';
            var menuItems = [
                '<button type="button" class="assignment-chip-menu-item" data-chip-menu-action="assign">' + assignLabel + '</button>',
                '<button type="button" class="assignment-chip-menu-item" data-chip-menu-action="production">' + productionLabel + '</button>'
            ];
            if (isPlanningAdmin) {
                menuItems.push('<button type="button" class="assignment-chip-menu-item" data-chip-menu-action="other">' + otherLabel + '</button>');
            }
            wrapper.innerHTML = menuItems.join('\n');
            wrapper.addEventListener('click', function (event) {
                var actionButton = event.target.closest('[data-chip-menu-action]');
                if (!actionButton) {
                    return;
                }
                event.preventDefault();
                event.stopPropagation();
                var action = actionButton.dataset.chipMenuAction;
                var chipTarget = activeChip;
                if (!chipTarget) {
                    closeMenu();
                    return;
                }
                if (action === 'assign') {
                    chipTarget.dataset.menuBypass = '1';
                    closeMenu();
                    window.setTimeout(function () {
                        chipTarget.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true }));
                    }, 0);
                } else if (action === 'production') {
                    closeMenu();
                    openProductionRecordsModal(chipTarget);
                } else if (action === 'other') {
                    closeMenu();
                    activeChip = chipTarget;
                    openOtherOptionsModal(chipTarget);
                }
            });
            wrapper.addEventListener('keydown', function (event) {
                if (event.key === 'Escape') {
                    closeMenu();
                }
            });
            menuElement = wrapper;
            document.body.appendChild(wrapper);
            return wrapper;
        }

        function positionMenu(chip) {
            if (!menuElement) {
                return;
            }
            menuElement.classList.add('is-visible');
            menuElement.style.visibility = 'hidden';
            menuElement.style.left = '0px';
            menuElement.style.top = '0px';
            var rect = chip.getBoundingClientRect();
            var menuRect = menuElement.getBoundingClientRect();
            var viewportWidth = window.innerWidth;
            var viewportHeight = window.innerHeight;
            var left = rect.left + window.scrollX;
            var top = rect.bottom + window.scrollY + 6;
            var maxLeft = viewportWidth - menuRect.width - 12 + window.scrollX;
            var maxTop = viewportHeight - menuRect.height - 12 + window.scrollY;
            left = clamp(left, window.scrollX + 12, maxLeft);
            top = clamp(top, window.scrollY + 12, maxTop);
            menuElement.style.left = left + 'px';
            menuElement.style.top = top + 'px';
            menuElement.style.visibility = 'visible';
            var firstButton = menuElement.querySelector('.assignment-chip-menu-item');
            if (firstButton) {
                firstButton.focus({ preventScroll: true });
            }
        }

        function openMenu(chip) {
            activeChip = chip;
            ensureMenu();
            positionMenu(chip);
        }

        function handleDocumentClick(event) {
            var target = event.target;
            if (menuElement && menuElement.contains(target)) {
                return;
            }
            if (otherOptionsModal && otherOptionsModal.contains(target)) {
                return;
            }
            var chip = target.closest('.assignment-chip[data-plan-stamp]');
            if (!chip) {
                closeMenu();
                return;
            }
            if (chip.dataset.menuBypass === '1') {
                delete chip.dataset.menuBypass;
                closeMenu();
                return;
            }
            event.preventDefault();
            event.stopPropagation();
            event.stopImmediatePropagation();
            openMenu(chip);
        }

        function handleKeydown(event) {
            if (event.key === 'Escape') {
                if (otherOptionsModal && otherOptionsModal.classList.contains('is-open')) {
                    closeOtherOptionsModal();
                    event.stopPropagation();
                    return;
                }
                if (productionRecordsModal && productionRecordsModal.classList.contains('is-open')) {
                    closeProductionRecordsModal();
                    event.stopPropagation();
                    return;
                }
                if (menuElement) {
                    closeMenu();
                    event.stopPropagation();
                    return;
                }
                if (productionModal && productionModal.classList.contains('is-open')) {
                    closeProductionModal();
                    event.stopPropagation();
                }
            }
        }

        document.addEventListener('click', handleDocumentClick, true);
        document.addEventListener('keydown', handleKeydown, true);
        window.addEventListener('scroll', closeMenu, true);
        window.addEventListener('resize', closeMenu);

        function maybePersistPendingOptions(chip) {
            if (!chip) {
                return;
            }
            var newStamp = normalizePlanStamp(chip.dataset ? chip.dataset.planStamp || chip.dataset.plan_stamp : '');
            if (!newStamp) {
                return;
            }
            var fallbackKey = otherOptionsKeyFromChip(chip);
            var pending = getPlanOptionDraft(fallbackKey);
            if (!pending) {
                return;
            }
            planOptionDrafts.delete(fallbackKey);
            setPlanOptionDraft(newStamp, pending.values || {}, pending.meta || readPlanMetaFromChip(chip));
            persistPlanOptions(newStamp, pending.values || {}, chip, pending.meta || readPlanMetaFromChip(chip));
        }

        function startChipObserver() {
            if (!window.MutationObserver) {
                return;
            }
            chipMutationObserver = new MutationObserver(function (records) {
                records.forEach(function (record) {
                    if (record.type === 'attributes' && record.attributeName === 'data-plan-stamp') {
                        var target = record.target;
                        if (target && target.classList && target.classList.contains('assignment-chip')) {
                            maybePersistPendingOptions(target);
                        }
                    }
                });
            });
            document.querySelectorAll('.assignment-chip').forEach(function (chip) {
                chipMutationObserver.observe(chip, { attributes: true, attributeFilter: ['data-plan-stamp'] });
            });
        }

        if (typeof window !== 'undefined') {
            ingestDraftRecordsFrom(window.productionDrafts);
            ingestDraftRecordsFrom(window.planningProductionDrafts);

            var draftApi = window.planningProductionDrafts;
            var apiIsObject = draftApi && typeof draftApi === 'object';
            if (!apiIsObject) {
                draftApi = {};
            }
            var apiIsMap = draftApi && typeof draftApi.forEach === 'function' && typeof draftApi.entries === 'function';
            var originalSet = apiIsObject && typeof draftApi.set === 'function' ? draftApi.set.bind(draftApi) : null;
            var originalGet = apiIsObject && typeof draftApi.get === 'function' ? draftApi.get.bind(draftApi) : null;
            var originalClear = apiIsObject && typeof draftApi.clear === 'function' ? draftApi.clear.bind(draftApi) : null;
            var originalDelete = apiIsObject && typeof draftApi.delete === 'function' ? draftApi.delete.bind(draftApi) : null;

            draftApi.set = function (planStamp, drafts) {
                if (originalSet) {
                    originalSet(planStamp, drafts);
                } else if (!apiIsMap) {
                    var key = normalizePlanStamp(planStamp);
                    if (key) {
                        draftApi[key] = drafts;
                    }
                }
                setDraftRecords(planStamp || '', drafts || []);
                return draftApi;
            };

            draftApi.get = function (planStamp) {
                var normalized = normalizePlanStamp(planStamp);
                var stored = getStoredDraftRecords(normalized);
                if (stored.length) {
                    return stored;
                }
                if (originalGet) {
                    return originalGet(planStamp);
                }
                if (!apiIsMap && normalized && Object.prototype.hasOwnProperty.call(draftApi, normalized)) {
                    return draftApi[normalized];
                }
                return [];
            };

            draftApi.delete = function (planStamp) {
                var normalized = normalizePlanStamp(planStamp);
                var removed = false;
                if (originalDelete) {
                    removed = originalDelete(planStamp) || removed;
                } else if (!apiIsMap && normalized && Object.prototype.hasOwnProperty.call(draftApi, normalized)) {
                    delete draftApi[normalized];
                    removed = true;
                }
                if (normalized) {
                    var hadStored = productionDraftStore.has(normalized);
                    setDraftRecords(normalized, []);
                    removed = removed || hadStored;
                }
                return removed;
            };

            draftApi.clear = function (planStamp) {
                var normalized = normalizePlanStamp(planStamp);
                if (normalized) {
                    if (originalDelete) {
                        originalDelete(planStamp);
                    } else if (!apiIsMap && Object.prototype.hasOwnProperty.call(draftApi, normalized)) {
                        delete draftApi[normalized];
                    }
                    setDraftRecords(normalized, []);
                    return draftApi;
                }
                productionDraftStore.clear();
                if (originalClear) {
                    originalClear();
                } else if (!apiIsMap) {
                    Object.keys(draftApi).forEach(function (key) {
                        delete draftApi[key];
                    });
                }
                if (activePlanStamp) {
                    renderProductionDrafts([]);
                }
                return draftApi;
            };

            draftApi.refresh = function (planStamp) {
                var normalized = normalizePlanStamp(planStamp);
                if (normalized && normalized === activePlanStamp) {
                    renderProductionDrafts(getStoredDraftRecords(normalized));
                }
                return draftApi;
            };

            window.planningProductionDrafts = draftApi;
            window.productionDrafts = draftApi;

            window.addEventListener('planning:production-drafts', function (event) {
                var detail = event && event.detail;
                if (!detail || typeof detail !== 'object') {
                    return;
                }
                draftApi.set(detail.planStamp || '', detail.drafts || []);
            });

            if (activePlanStamp) {
                renderProductionDrafts(getStoredDraftRecords(activePlanStamp));
            }
        }

        if (productionLinesDistributeButton) {
            productionLinesDistributeButton.addEventListener('click', function () {
                distributeProductionLines();
            });
        }

if (productionLinesAddButton) {
            productionLinesAddButton.addEventListener('click', function () {
                addProductionLine();
            });
        }

        if (productionSaveButton) {
            productionSaveButton.addEventListener('click', function () {
                submitProductionForm();
            });
        }

        if (productionForm) {
            productionForm.addEventListener('submit', function (event) {
                event.preventDefault();
                submitProductionForm();
            });
        }

        if (productionRecordsModal) {
            productionRecordsModal.addEventListener('click', function (event) {
                if (event.target === productionRecordsModal) {
                    closeProductionRecordsModal();
                }
            });
        }

        if (otherOptionsModal) {
            otherOptionsModal.addEventListener('click', function (event) {
                if (event.target === otherOptionsModal) {
                    closeOtherOptionsModal();
                }
            });
            otherOptionsModal.addEventListener('transitionend', function () {
                if (!otherOptionsModal.classList.contains('is-open')) {
                    otherOptionsModal.setAttribute('aria-hidden', 'true');
                    otherOptionsModal.setAttribute('hidden', 'hidden');
                }
            });
        }

        otherOptionsCloseButtons.forEach(function (button) {
            button.addEventListener('click', function () {
                closeOtherOptionsModal();
            });
        });

        if (otherOptionsSaveButton) {
            otherOptionsSaveButton.addEventListener('click', function () {
                var chip = activeChip;
                if (!chip) {
                    closeOtherOptionsModal();
                    return;
                }
                var planStamp = chip.dataset ? (chip.dataset.planStamp || chip.dataset.plan_stamp || '') : '';
                var normalizedStamp = normalizePlanStamp(planStamp);
                var fallbackKey = otherOptionsKeyFromChip(chip);
                var values = {};
                otherOptionsFields.forEach(function (field) {
                    var key = field.dataset ? field.dataset.otherOptionsField : field.getAttribute('data-other-options-field');
                    if (!key) {
                        return;
                    }
                    values[key] = field.value;
                });
                var meta = readPlanMetaFromChip(chip);
                debugLog('save-click', { stamp: normalizedStamp, fallbackKey: fallbackKey, values: values, meta: meta });
                if (normalizedStamp) {
                    persistPlanOptions(normalizedStamp, values, chip, meta).then(function (ok) {
                        if (ok) {
                            closeOtherOptionsModal();
                        }
                    });
                } else {
                    setPlanOptionDraft(fallbackKey, values, meta);
                    if (otherOptionsPendingText) {
                        setOtherOptionsFeedback(otherOptionsPendingText, false);
                    }
                }
            });
        }

        if (productionRecordsNewButton) {
            productionRecordsNewButton.addEventListener('click', function () {
                closeProductionRecordsModal();
                openProductionModal(activeChip || null, null);
            });
        }

        if (productionRecordsCancelButton) {
            productionRecordsCancelButton.addEventListener('click', function () {
                closeProductionRecordsModal();
            });
        }

        if (productionModal) {
            productionModal.addEventListener('click', function (event) {
                if (event.target === productionModal) {
                    closeProductionModal();
                }
            });
            productionCloseButtons.forEach(function (button) {
                button.addEventListener('click', function () {
                    closeProductionModal();
                });
            });
        }

        if (productionFields.litem) {
            productionFields.litem.addEventListener('input', scheduleProductionMissingUpdate);
            productionFields.litem.addEventListener('blur', scheduleProductionMissingUpdate);
        }
        if (productionFields.processo) {
            productionFields.processo.addEventListener('input', scheduleProductionMissingUpdate);
            productionFields.processo.addEventListener('blur', scheduleProductionMissingUpdate);
        }

        startChipObserver();
    });
})();



