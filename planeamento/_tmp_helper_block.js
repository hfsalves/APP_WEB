(function(){
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

})();