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
        var productionModal = document.getElementById('production-modal');
        var productionDialog = productionModal ? productionModal.querySelector('.modal-dialog') : null;
        var productionCloseButtons = productionModal ? productionModal.querySelectorAll('[data-production-close]') : [];
        var productionForm = productionModal ? productionModal.querySelector('[data-production-form]') : null;
        var productionFields = {
            fref: productionForm ? productionForm.querySelector('[data-production-field="fref"]') : null,
            processo: productionForm ? productionForm.querySelector('[data-production-field="processo"]') : null,
            data: productionForm ? productionForm.querySelector('[data-production-field="data"]') : null,
            litem: productionForm ? productionForm.querySelector('[data-production-field="litem"]') : null,
            dgeral: productionForm ? productionForm.querySelector('[data-production-field="dgeral"]') : null,
            qtt: productionForm ? productionForm.querySelector('[data-production-field="qtt"]') : null,
            m3bomba: productionForm ? productionForm.querySelector('[data-production-field="m3bomba"]') : null,
            m2serragem: productionForm ? productionForm.querySelector('[data-production-field="m2serragem"]') : null,
            kgferro: productionForm ? productionForm.querySelector('[data-production-field="kgferro"]') : null,
            m3betao: productionForm ? productionForm.querySelector('[data-production-field="m3betao"]') : null
        };

        var decimalFieldNames = ['qtt', 'm2serragem', 'kgferro', 'm3betao', 'm3bomba'];
        var decimalFieldMap = {};
        decimalFieldNames.forEach(function (name) {
            decimalFieldMap[name] = true;
        });

        function formatDecimalValue(value) {
            if (value === undefined || value === null) {
                return '';
            }
            var sanitized = sanitizeDecimalInput(value);
            if (!sanitized) {
                return '';
            }
            var parsed = parseFloat(sanitized);
            if (!isFinite(parsed)) {
                return '';
            }
            return parsed.toFixed(2);
        }

        function sanitizeDecimalInput(rawValue) {
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
            if (decimals.length > 2) {
                decimals = decimals.slice(0, 2);
            }
            return parts[0] + '.' + decimals;
        }

        function applyDecimalMask(field) {
            if (!field) {
                return;
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
                var normalizedValue = sanitizeDecimalInput(rawValue);
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
                    var sanitizedComposed = sanitizeDecimalInput(composed);
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
                    var sanitizedRecomposed = sanitizeDecimalInput(recomposed);
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
                var sanitized = sanitizeDecimalInput(previous);
                if (sanitized !== previous) {
                    field.value = sanitized;
                    if (field.setSelectionRange && document.activeElement === field) {
                        var caret = sanitized.length;
                        field.setSelectionRange(caret, caret);
                    }
                }
            });
            field.addEventListener('blur', function () {
                field.value = formatDecimalValue(field.value);
            });
        }

        decimalFieldNames.forEach(function (name) {
            applyDecimalMask(productionFields[name]);
        });

        var productionDisplays = {
            teamName: productionForm ? productionForm.querySelector('[data-production-display="team-name"]') : null,
            projectName: productionForm ? productionForm.querySelector('[data-production-display="project-name"]') : null
        };

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

        var menuElement = null;
        var activeChip = null;
        var activePlanStamp = '';
        var productionDraftStore = new Map();
        var lastRenderedDraftCount = 0;

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

        function normalizeNumberValue(value) {        function normalizeNumberValue(value) {
            if (value === undefined || value === null || value === '') {
                return null;
            }
            if (typeof value === 'number' && Number.isFinite(value)) {
                return value;
            }
            var normalized = parseFloat(String(value).replace(',', '.'));
            return Number.isFinite(normalized) ? normalized : null;
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
                if (seenDraftKeys.has(key)) {
                    return;
                }
                var baselineHash = baselineHashes.get(identity) || baselineHashes.get(hash);
                var primaryStamp = normalizePlanStamp(line.u_lplanostamp || line.planLineStamp || line.planlinestamp || line.bistamp || line.plan_stamp || line.planostamp || '');
                var isUnsaved = false;
                if (!baselineHash) {
                    isUnsaved = true;
                } else if (baselineHash !== hash) {
                    isUnsaved = true;
                }
                if (!isUnsaved && (!primaryStamp || primaryStamp === normalizedStamp)) {
                    if (!line.u_lplanostamp && !line.planLineStamp && !line.planlinestamp && !line.bistamp) {
                        isUnsaved = true;
                    }
                }
                if (!isUnsaved && (line.isDraft || line.__isDraft || line.__unsaved || line._isDraft)) {
                    isUnsaved = true;
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

        function renderProductionDrafts(records) {
            if (!productionDraftsContainer || !productionDraftsList) {
                return;
            }
            productionDraftsList.innerHTML = '';
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

                var summary = document.createElement('p');
                summary.className = 'production-records-draft-summary';
                var summaryText = record && record.draftSummary ? record.draftSummary : (formatProductionRecord(record) || productionDraftLabel);
                summary.textContent = summaryText;

                var note = document.createElement('p');
                note.className = 'production-records-draft-note';
                note.textContent = record && record.draftNote ? record.draftNote : productionDraftNote;

                card.appendChild(badge);
                card.appendChild(summary);
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
                item.textContent = formatProductionRecord(record) || (record.u_amstamp ? String(record.u_amstamp) : '');
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
            activeChip = null;
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
            wrapper.innerHTML = [
                '<button type="button" class="assignment-chip-menu-item" data-chip-menu-action="assign">' + assignLabel + '</button>',
                '<button type="button" class="assignment-chip-menu-item" data-chip-menu-action="production">' + productionLabel + '</button>'
            ].join('\n');
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

        if (productionRecordsModal) {
            productionRecordsModal.addEventListener('click', function (event) {
                if (event.target === productionRecordsModal) {
                    closeProductionRecordsModal();
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
    });
})();


