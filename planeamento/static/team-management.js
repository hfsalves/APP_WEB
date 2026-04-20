(function () {



    function parseJSON(value, fallback) {



        if (!value) {



            return fallback;



        }



        try {



            return JSON.parse(value);



        } catch (err) {



            return fallback;



        }



    }



    function initTeamManagement() {



        var root = document.querySelector('[data-team-management]');



        if (!root) {



            return;



        }



        var page = document.body;



        var referenceDate = page.dataset.referenceDate || '';



        var weekStart = page.dataset.weekStart || referenceDate;



        var weekEnd = page.dataset.weekEnd || referenceDate;



        var teamOptions = parseJSON(page.dataset.teamOptions || '[]', []);



        var teamMap = new Map();



        teamOptions.forEach(function (option) {



            if (option && option.code) {



                teamMap.set(option.code, option);



            }



        });



        var modal = document.getElementById('team-action-modal');



        if (!modal) {



            return;



        }



        var errorMap = parseJSON(modal.dataset.errorMap || '{}', {});



        var genericError = modal.dataset.errorGeneric || 'Unexpected error.';



        var successMessage = modal.dataset.successMessage || '';



        var contextMessages = {



            unassigned: modal.dataset.contextUnassigned || '',



            assigned: modal.dataset.contextAssigned || ''



        };



        var teamPlaceholder = modal.dataset.teamPlaceholder || '--';



        var form = modal.querySelector('[data-team-action-form]');



        var actionSelect = form.querySelector('[data-team-action-select]');



        var teamSelectRow = form.querySelector('[data-team-select-row]');



        var teamSelect = form.querySelector('[data-team-target-select]');



        var leadToggleRow = form.querySelector('[data-lead-toggle-row]');



        var leadToggle = form.querySelector('[data-team-lead-toggle]');



        var periodRadios = form.querySelectorAll('[data-team-period-option]');



        var customWrapper = form.querySelector('[data-team-period-custom]');



        var customStartInput = form.querySelector('[data-team-custom-start]');



        var customEndInput = form.querySelector('[data-team-custom-end]');



        var referenceWrapper = form.querySelector('[data-team-period-reference]');



        var referenceInput = form.querySelector('[data-team-reference-input]');



        var referenceLabel = form.querySelector('[data-team-reference-label]');
        var referenceLabelBase = referenceLabel ? referenceLabel.getAttribute('data-reference-base') || referenceLabel.textContent : '';
        var weekLabel = form.querySelector('[data-team-week-label]');
        var weekLabelBase = weekLabel ? weekLabel.getAttribute('data-week-base') || weekLabel.textContent : '';
        var specificWrapper = form.querySelector('[data-team-period-specific]');



        var specificDateInput = form.querySelector('[data-team-specific-date]');



        var feedback = form.querySelector('[data-team-modal-error]');



        var contextLabel = modal.querySelector('[data-team-modal-context]');



        var cancelButton = modal.querySelector('[data-team-action-cancel]');



        var confirmButton = modal.querySelector('[data-team-action-confirm]');



        var confirmDefaultLabel = confirmButton ? confirmButton.textContent : '';



        var confirmLoadingLabel = confirmButton ? (confirmButton.dataset.loadingText || confirmDefaultLabel) : '';



        var currentContext = null;



        var keydownHandler = null;



        function formatReferenceDate(value) {



            if (!value) {



                return "";



            }



            var parts = value.split('-');



            if (parts.length !== 3) {



                return value;



            }



            return parts[2] + '/' + parts[1] + '/' + parts[0];



        }



        function getDefaultReferenceDate() {



            if (referenceDate) {



                return referenceDate;



            }



            if (currentContext && currentContext.membershipStart) {



                return currentContext.membershipStart;



            }



            if (weekStart) {



                return weekStart;



            }



            return "";



        }

        function toggleSection(section, isVisible) {
            if (!section) {
                return;
            }
            section.hidden = !isVisible;
            if (section.style) {
                section.style.display = isVisible ? '' : 'none';
            }
        }

        function updateWeekLabel() {
            if (!weekLabel) {
                return;
            }
            var labelText = weekLabelBase || '';
            var rangeText = '';
            if (weekStart && weekEnd) {
                rangeText = formatReferenceDate(weekStart) + ' a ' + formatReferenceDate(weekEnd);
            } else if (weekStart) {
                rangeText = formatReferenceDate(weekStart);
            } else if (referenceDate) {
                rangeText = formatReferenceDate(referenceDate);
            }
            if (rangeText) {
                weekLabel.textContent = labelText ? labelText + ' (' + rangeText + ')' : rangeText;
            } else {
                weekLabel.textContent = labelText;
            }
        }

        function updateReferenceDisplay(useWeekRange) {



            if (!referenceLabel && !referenceInput) {



                return;



            }



            var labelText = referenceLabelBase || "";



            var referenceValue = "";



            if (useWeekRange) {



                referenceValue = weekStart || referenceDate || "";



                var rangeText = "";



                if (weekStart && weekEnd) {



                    rangeText = formatReferenceDate(weekStart) + ' - ' + formatReferenceDate(weekEnd);



                } else if (weekStart) {



                    rangeText = formatReferenceDate(weekStart);



                } else if (referenceDate) {



                    rangeText = formatReferenceDate(referenceDate);



                }



                if (rangeText) {



                    labelText = labelText ? labelText + ' (' + rangeText + ')' : rangeText;



                }



            } else {



                referenceValue = getDefaultReferenceDate();



                if (referenceValue) {



                    var dateText = formatReferenceDate(referenceValue);



                    labelText = labelText ? labelText + ' (' + dateText + ')' : dateText;



                }



            }



            if (referenceLabel) {



                referenceLabel.textContent = labelText;



            }



            if (referenceInput) {



                referenceInput.value = referenceValue || "";



            }



        }



        function setFeedback(message, isError) {



            if (!feedback) {



                return;



            }



            feedback.textContent = message || '';



            feedback.classList.toggle('is-success', Boolean(message) && isError === false);



        }



        function setLoading(state) {



            if (!confirmButton) {



                return;



            }



            if (state) {



                confirmButton.disabled = true;



                confirmButton.textContent = confirmLoadingLabel;



            } else {



                confirmButton.disabled = false;



                confirmButton.textContent = confirmDefaultLabel;



            }



        }



        function populateTeamSelect(selectedCode) {



            if (!teamSelect) {



                return;



            }



            var fragment = document.createDocumentFragment();



            var placeholderOption = document.createElement('option');



            placeholderOption.value = '';



            placeholderOption.textContent = teamPlaceholder;



            placeholderOption.disabled = true;



            placeholderOption.hidden = false;



            fragment.appendChild(placeholderOption);



            var hasSelected = false;



            teamOptions.forEach(function (option) {



                if (!option || !option.code) {



                    return;



                }



                var optionEl = document.createElement('option');



                optionEl.value = option.code;



                optionEl.textContent = option.name && option.name !== option.code ? option.code + ' — ' + option.name : option.code;



                if (selectedCode && option.code === selectedCode) {



                    optionEl.selected = true;



                    hasSelected = true;



                }



                fragment.appendChild(optionEl);



            });



            if (selectedCode && !hasSelected) {



                var fallbackOption = document.createElement('option');



                fallbackOption.value = selectedCode;



                fallbackOption.textContent = selectedCode;



                fallbackOption.selected = true;



                fragment.appendChild(fallbackOption);



                hasSelected = true;



            }



            teamSelect.innerHTML = '';



            teamSelect.appendChild(fragment);



            if (!hasSelected && teamSelect.options.length > 1) {



                teamSelect.options[1].selected = true;



            }



        }



        function configureActionOptions(context) {



            if (!actionSelect) {



                return;



            }



            var allowed = context.state === 'unassigned'



                ? new Set(['assign', 'lead'])



                : new Set(['transfer', 'remove', 'lead']);



            var firstAvailable = null;



            Array.prototype.forEach.call(actionSelect.options, function (option) {



                var enabled = allowed.has(option.value);



                option.hidden = !enabled;



                option.disabled = !enabled;



                if (enabled && !firstAvailable) {



                    firstAvailable = option.value;



                }



            });



            if (!firstAvailable) {



                firstAvailable = 'assign';



            }



            var selectedOption = actionSelect.options[actionSelect.selectedIndex];



            if (!selectedOption || selectedOption.disabled || selectedOption.hidden) {



                actionSelect.value = firstAvailable;



            }



        }



        function updateActionUI(forceTeamCode) {



            if (!actionSelect) {



                return;



            }



            var action = actionSelect.value;



            var requiresTeam = action === 'assign' || action === 'transfer';



            if (teamSelectRow) {
                toggleSection(teamSelectRow, requiresTeam);
            }
            if (requiresTeam) {



                populateTeamSelect(forceTeamCode || (currentContext ? currentContext.teamCode : ''));



            } else if (teamSelect) {



                teamSelect.value = '';



            }



            var showLeadToggle = action === 'assign' || action === 'transfer';
            if (leadToggleRow) {
                toggleSection(leadToggleRow, showLeadToggle);
            }
            if (leadToggle) {
                if (action === 'lead') {
                    leadToggle.checked = true;
                    leadToggle.disabled = true;
                } else if (action === 'assign' || action === 'transfer') {
                    leadToggle.disabled = false;
                    if (currentContext && currentContext.state === 'assigned') {
                        leadToggle.checked = Boolean(currentContext.isLead);
                    } else {
                        leadToggle.checked = false;
                    }
                } else {
                    leadToggle.checked = false;
                    leadToggle.disabled = true;
                }
            }



        }



                        function updatePeriodUI() {



            var selected = form.querySelector('input[name="team-period"]:checked');



            if (!selected) {



                return;



            }



            var value = selected.value;



            var isCustom = value === 'custom';



            var isSpecific = value === 'specific';



            var isReference = value === 'reference';



            var isWeek = value === 'week';

            updateWeekLabel();



            toggleSection(customWrapper, isCustom);



            toggleSection(specificWrapper, isSpecific);



            toggleSection(referenceWrapper, false);



            if (referenceInput) {



                referenceInput.value = '';



            }



            if (isCustom && customStartInput && !customStartInput.value) {



                customStartInput.value = referenceDate || weekStart || '';



            }



            if (isSpecific && specificDateInput && !specificDateInput.value) {



                specificDateInput.value = referenceDate || weekStart || '';



            }



            if (specificDateInput) {



                specificDateInput.disabled = !isSpecific;



            }



            if (customStartInput) {



                customStartInput.disabled = !isCustom;



            }



            if (customEndInput) {



                customEndInput.disabled = !isCustom;



            }



            if (isWeek) {
                updateReferenceDisplay(true);
            } else if (isReference) {
                updateReferenceDisplay(false);
            } else if (referenceInput) {
                referenceInput.value = '';
            }



        }



function buildContextSummary(context) {



            if (!contextLabel) {



                return;



            }



            var summary = context.name + ' (' + context.number + ')';



            if (context.state === 'assigned' && context.teamName) {



                summary += ' • ' + (contextMessages.assigned || '') + ' ' + context.teamName + ' [' + context.teamCode + ']';



            } else {



                summary += ' • ' + (contextMessages.unassigned || '');



            }



            contextLabel.textContent = summary;



        }



                        function clearForm() {



            if (form) {



                form.reset();



            }



            updateWeekLabel();

            Array.prototype.forEach.call(periodRadios, function (radio) {



                radio.checked = radio.value === 'reference';



            });



            toggleSection(customWrapper, false);



            toggleSection(specificWrapper, false);



            toggleSection(referenceWrapper, false);



            if (specificDateInput) {



                specificDateInput.disabled = true;



            }



            if (customStartInput) {



                customStartInput.disabled = true;



            }



            if (customEndInput) {



                customEndInput.disabled = true;



            }



            updateReferenceDisplay(false);



            var defaultDate = getDefaultReferenceDate();



            if (specificDateInput) {



                specificDateInput.value = defaultDate;



            }



            if (customStartInput) {



                customStartInput.value = defaultDate;



            }



            if (customEndInput) {



                customEndInput.value = '';



            }



        }



function openModal(context) {



            currentContext = context;



            clearForm();



            setFeedback('', true);



            configureActionOptions(context);



            var defaultAction = context.state === 'unassigned' ? 'assign' : 'transfer';



            if (actionSelect) {



                actionSelect.value = defaultAction;



                var selectedOption = actionSelect.options[actionSelect.selectedIndex];



                if (!selectedOption || selectedOption.disabled || selectedOption.hidden) {



                    var firstEnabled = Array.prototype.find.call(actionSelect.options, function (option) {



                        return !option.disabled && !option.hidden;



                    });



                    if (firstEnabled) {



                        actionSelect.value = firstEnabled.value;



                    }



                }



            }



            updateActionUI(context.teamCode);



            updatePeriodUI();



            buildContextSummary(context);



            keydownHandler = function (event) {



                if (event.key === 'Escape') {



                    event.preventDefault();



                    closeModal();



                }



            };



            document.addEventListener('keydown', keydownHandler);



            modal.removeAttribute('hidden');



            modal.classList.add('is-open');



            modal.setAttribute('aria-hidden', 'false');



            document.body.classList.add('modal-open');



            if (actionSelect) {



                actionSelect.focus({ preventScroll: true });



            }



        }



        function closeModal() {



            document.removeEventListener('keydown', keydownHandler);



            keydownHandler = null;



            currentContext = null;



            setLoading(false);



            setFeedback('', true);



            modal.classList.remove('is-open');



            modal.setAttribute('hidden', 'true');



            modal.setAttribute('aria-hidden', 'true');



            document.body.classList.remove('modal-open');



        }



        function handleSubmit() {



            if (!currentContext || !confirmButton) {



                return;



            }



            var action = actionSelect ? actionSelect.value : 'assign';



            var requiresTeam = action === 'assign' || action === 'transfer' || action === 'lead';



            var selectedTeam = teamSelect ? teamSelect.value : '';



            if (requiresTeam && !selectedTeam) {



                setFeedback(errorMap.missing_target_team || genericError, true);



                return;



            }



            var selectedPeriod = form.querySelector('input[name="team-period"]:checked');



            var periodValue = selectedPeriod ? selectedPeriod.value : 'reference';



            var customStart = null;



            var customEnd = null;



            var specificDate = null;



            if (periodValue === 'custom') {



                customStart = customStartInput ? customStartInput.value : null;



                customEnd = customEndInput ? customEndInput.value : null;



                if (customStart === '') {



                    customStart = null;



                }



                if (customEnd === '') {



                    customEnd = null;



                }



                if (!customStart) {



                    setFeedback(errorMap.missing_custom_start || genericError, true);



                    return;



                }



                if (customEnd && customStart && customEnd < customStart) {



                    setFeedback(errorMap.invalid_custom_range || genericError, true);



                    return;



                }



            } else if (periodValue === 'specific') {



                specificDate = specificDateInput ? specificDateInput.value : null;



                if (specificDate === '') {



                    specificDate = null;



                }



                if (!specificDate) {



                    setFeedback(errorMap.missing_specific_date || errorMap.missing_custom_start || genericError, true);



                    return;



                }



            }



            var payload = {



                action: action,



                employee_number: currentContext.number,



                employee_origin: currentContext.origin || '',



                reference_date: referenceDate || weekStart,



                period_type: periodValue,



                custom_start: customStart,



                custom_end: customEnd,



                specific_date: specificDate,



                target_team: requiresTeam ? selectedTeam : '',



                make_lead: action === 'lead' ? true : Boolean(leadToggle && leadToggle.checked)



            };



            setFeedback('', true);



            setLoading(true);



            fetch('/api/team-memberships', {



                method: 'POST',



                headers: {



                    'Content-Type': 'application/json'



                },



                body: JSON.stringify(payload)



            }).then(function (response) {



                return response.json().catch(function () {



                    return {};



                }).then(function (data) {



                    return { ok: response.ok, status: response.status, data: data };



                });



            }).then(function (result) {



                if (!result.ok) {



                    var errorCode = result.data && result.data.error;



                    var message = (errorCode && errorMap[errorCode]) || genericError;



                    if (errorCode === 'database_error' && result.data && result.data.details) {



                        message = message + ' (' + result.data.details + ')';



                    }



                    setFeedback(message, true);



                    setLoading(false);



                    return;



                }



                setLoading(false);



                if (successMessage) {



                    setFeedback(successMessage, false);



                }



                setTimeout(function () {



                    window.location.reload();



                }, 400);



            }).catch(function () {



                setFeedback(genericError, true);



                setLoading(false);



            });



        }



        Array.prototype.forEach.call(periodRadios, function (radio) {



            radio.addEventListener('change', function () {



                setFeedback('', true);



                updatePeriodUI();



            });



        });



        if (actionSelect) {



            actionSelect.addEventListener('change', function () {



                setFeedback('', true);



                updateActionUI(currentContext ? currentContext.teamCode : '');



            });



        }



        if (teamSelect) {



            teamSelect.addEventListener('change', function () {



                setFeedback('', true);



            });



        }



        if (specificDateInput) {



            specificDateInput.addEventListener('change', function () {



                setFeedback('', true);



            });



        }



        if (leadToggle) {



            leadToggle.addEventListener('change', function () {



                setFeedback('', true);



            });



        }



        if (cancelButton) {



            cancelButton.addEventListener('click', function () {



                closeModal();



            });



        }



        if (confirmButton) {



            confirmButton.addEventListener('click', handleSubmit);



        }



        modal.addEventListener('click', function (event) {



            if (event.target === modal) {



                closeModal();



            }



        });



        root.addEventListener('click', function (event) {



            var target = event.target.closest('[data-team-action-trigger]');



            if (!target) {



                return;



            }



            event.preventDefault();



            var context = {



                state: target.dataset.employeeState || 'assigned',



                number: target.dataset.employeeNumber || '',



                name: target.dataset.employeeName || target.dataset.employeeNumber || '',



                origin: target.dataset.employeeOrigin || '',



                teamCode: target.dataset.teamCode || '',



                teamName: target.dataset.teamName || '',



                teamStamp: target.dataset.teamStamp || '',



                isLead: target.dataset.isLead === '1',



                membershipStamp: target.dataset.membershipStamp || '',



                membershipStart: target.dataset.membershipStart || '',



                membershipEnd: target.dataset.membershipEnd || ''



            };



            openModal(context);



        });



    }



    if (document.readyState === 'loading') {



        document.addEventListener('DOMContentLoaded', initTeamManagement);



    } else {



        initTeamManagement();



    }



})();



