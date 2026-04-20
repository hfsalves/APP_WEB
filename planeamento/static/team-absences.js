(function () {
    function initTeamAbsences() {
        var modal = document.getElementById('team-absence-modal');
        var openButtons = Array.prototype.slice.call(document.querySelectorAll('[data-team-absences-open]'));
        if (!modal || !openButtons.length) {
            return;
        }

        var page = document.body;
        var referenceDate = page.dataset.referenceDate || '';
        var form = modal.querySelector('[data-team-absence-form]');
        var stampInput = modal.querySelector('[data-absence-stamp]');
        var employeeSelect = modal.querySelector('[data-absence-employee-select]');
        var startInput = modal.querySelector('[data-absence-start-date]');
        var endInput = modal.querySelector('[data-absence-end-date]');
        var obsInput = modal.querySelector('[data-absence-obs]');
        var saveButton = modal.querySelector('[data-absence-save]');
        var resetButton = modal.querySelector('[data-absence-reset]');
        var closeButton = modal.querySelector('[data-team-absence-close]');
        var feedback = modal.querySelector('[data-team-absence-feedback]');
        var rowsBody = modal.querySelector('[data-team-absence-rows]');
        var referenceBadge = modal.querySelector('[data-team-absence-reference]');

        var saveLabel = modal.dataset.saveLabel || 'Guardar';
        var updateLabel = modal.dataset.updateLabel || 'Atualizar';
        var loadingLabel = modal.dataset.savingLabel || saveLabel;
        var editLabel = modal.dataset.editLabel || 'Editar';
        var deleteLabel = modal.dataset.deleteLabel || 'Eliminar';
        var closeLabel = modal.dataset.closeLabel || 'Fechar';
        var loadError = modal.dataset.loadError || 'Não foi possível carregar as ausências.';
        var saveError = modal.dataset.saveError || 'Não foi possível guardar a ausência.';
        var deleteError = modal.dataset.deleteError || 'Não foi possível eliminar a ausência.';
        var missingEmployeeMessage = modal.dataset.missingEmployee || 'Selecione um colaborador.';
        var missingDatesMessage = modal.dataset.missingDates || 'Indique as datas da ausência.';
        var invalidRangeMessage = modal.dataset.invalidRange || 'A data final deve ser posterior ou igual à data inicial.';
        var emptyMessage = modal.dataset.emptyMessage || 'Sem ausências presentes ou futuras.';
        var deleteConfirmMessage = modal.dataset.deleteConfirm || 'Eliminar esta ausência?';
        var statusCurrentLabel = modal.dataset.statusCurrent || 'Em curso';
        var statusFutureLabel = modal.dataset.statusFuture || 'Futura';
        var employeePlaceholder = modal.dataset.employeePlaceholder || 'Selecione um colaborador';
        var defaultLoadingRow = modal.dataset.loadingLabel || 'A carregar...';
        var keydownHandler = null;
        var employeesLoaded = false;
        var employeesPromise = null;
        var currentRows = [];

        function formatDisplayDate(value) {
            if (!value) {
                return '';
            }
            var parts = String(value).split('-');
            if (parts.length !== 3) {
                return String(value);
            }
            return parts[2] + '/' + parts[1] + '/' + parts[0];
        }

        function setFeedback(message, isSuccess) {
            if (!feedback) {
                return;
            }
            feedback.textContent = message || '';
            feedback.classList.toggle('is-success', Boolean(message) && isSuccess === true);
        }

        function setSavingState(isSaving) {
            if (saveButton) {
                saveButton.disabled = isSaving;
                saveButton.textContent = isSaving ? loadingLabel : (stampInput && stampInput.value ? updateLabel : saveLabel);
            }
            if (resetButton) {
                resetButton.disabled = isSaving;
            }
            if (employeeSelect) {
                employeeSelect.disabled = isSaving;
            }
            if (startInput) {
                startInput.disabled = isSaving;
            }
            if (endInput) {
                endInput.disabled = isSaving;
            }
            if (obsInput) {
                obsInput.disabled = isSaving;
            }
        }

        function setRowsLoading() {
            if (!rowsBody) {
                return;
            }
            rowsBody.innerHTML = '';
            var row = document.createElement('tr');
            var cell = document.createElement('td');
            cell.colSpan = 6;
            cell.className = 'modal-empty';
            cell.textContent = defaultLoadingRow;
            row.appendChild(cell);
            rowsBody.appendChild(row);
        }

        function resetForm() {
            if (stampInput) {
                stampInput.value = '';
            }
            if (employeeSelect) {
                employeeSelect.value = '';
            }
            if (startInput) {
                startInput.value = referenceDate || '';
            }
            if (endInput) {
                endInput.value = referenceDate || '';
            }
            if (obsInput) {
                obsInput.value = '';
            }
            if (saveButton) {
                saveButton.textContent = saveLabel;
            }
            setFeedback('', false);
        }

        function formatEmployeeLabel(number, name) {
            var normalizedNumber = number ? String(number).trim() : '';
            var normalizedName = name ? String(name).trim() : '';
            if (normalizedName && normalizedNumber && normalizedName !== normalizedNumber) {
                return normalizedName + ' (' + normalizedNumber + ')';
            }
            return normalizedName || normalizedNumber;
        }

        function buildEmployeeOptionKey(number, name) {
            var normalizedNumber = number ? String(number).trim() : '';
            var normalizedName = name ? String(name).trim() : '';
            return normalizedNumber + '||' + normalizedName.toUpperCase();
        }

        function ensureEmployeeOption(number, name) {
            if (!employeeSelect || !number) {
                return;
            }
            var optionKey = buildEmployeeOptionKey(number, name);
            var existing = Array.prototype.find.call(employeeSelect.options, function (option) {
                return (option.dataset.employeeKey || '') === optionKey;
            });
            if (existing) {
                if (name) {
                    existing.dataset.employeeName = name;
                    existing.dataset.employeeNumber = String(number).trim();
                    existing.dataset.employeeKey = optionKey;
                    existing.textContent = formatEmployeeLabel(number, name);
                }
                return;
            }
            var option = document.createElement('option');
            option.value = optionKey;
            option.textContent = formatEmployeeLabel(number, name);
            option.dataset.employeeKey = optionKey;
            option.dataset.employeeNumber = String(number).trim();
            option.dataset.employeeName = name || '';
            employeeSelect.appendChild(option);
        }

        function populateEmployeeOptions(rows) {
            if (!employeeSelect) {
                return;
            }
            var currentValue = employeeSelect.value || '';
            employeeSelect.innerHTML = '';
            var placeholderOption = document.createElement('option');
            placeholderOption.value = '';
            placeholderOption.textContent = employeePlaceholder;
            employeeSelect.appendChild(placeholderOption);

            (rows || []).forEach(function (row) {
                if (!row || row.no === undefined || row.no === null) {
                    return;
                }
                var number = String(row.no).trim();
                var name = row.cval4 !== undefined && row.cval4 !== null ? String(row.cval4).trim() : '';
                if (!number) {
                    return;
                }
                ensureEmployeeOption(number, name);
            });

            if (currentValue) {
                employeeSelect.value = currentValue;
            }
        }

        function loadEmployees() {
            if (employeesLoaded) {
                return Promise.resolve();
            }
            if (employeesPromise) {
                return employeesPromise;
            }
            employeesPromise = fetch('/api/employees', { headers: { 'Accept': 'application/json' }, credentials: 'same-origin' })
                .then(function (response) {
                    if (!response.ok) {
                        throw new Error('employees_load_failed');
                    }
                    return response.json();
                })
                .then(function (rows) {
                    populateEmployeeOptions(Array.isArray(rows) ? rows : []);
                    employeesLoaded = true;
                })
                .finally(function () {
                    employeesPromise = null;
                });
            return employeesPromise;
        }

        function createActionButton(label, action, stamp) {
            var button = document.createElement('button');
            button.type = 'button';
            button.className = 'team-absence-action-button';
            button.textContent = label;
            button.dataset.action = action;
            button.dataset.absenceStamp = stamp || '';
            if (action === 'delete') {
                button.classList.add('is-delete');
            }
            return button;
        }

        function renderRows(rows) {
            currentRows = Array.isArray(rows) ? rows.slice() : [];
            if (!rowsBody) {
                return;
            }
            rowsBody.innerHTML = '';
            if (!currentRows.length) {
                var emptyRow = document.createElement('tr');
                var emptyCell = document.createElement('td');
                emptyCell.colSpan = 6;
                emptyCell.className = 'modal-empty';
                emptyCell.textContent = emptyMessage;
                emptyRow.appendChild(emptyCell);
                rowsBody.appendChild(emptyRow);
                return;
            }

            currentRows.forEach(function (row) {
                var tr = document.createElement('tr');

                var numberCell = document.createElement('td');
                numberCell.textContent = row.employee_number || '';
                tr.appendChild(numberCell);

                var nameCell = document.createElement('td');
                nameCell.textContent = row.employee_name || '';
                tr.appendChild(nameCell);

                var startCell = document.createElement('td');
                startCell.textContent = row.start_date_label || formatDisplayDate(row.start_date || '');
                tr.appendChild(startCell);

                var endCell = document.createElement('td');
                endCell.textContent = row.end_date_label || formatDisplayDate(row.end_date || '');
                tr.appendChild(endCell);

                var statusCell = document.createElement('td');
                var badge = document.createElement('span');
                badge.className = 'team-absence-status' + (row.is_current ? ' is-current' : ' is-future');
                badge.textContent = row.is_current ? statusCurrentLabel : statusFutureLabel;
                statusCell.appendChild(badge);
                tr.appendChild(statusCell);

                var actionsCell = document.createElement('td');
                actionsCell.className = 'team-absence-actions';
                actionsCell.appendChild(createActionButton(editLabel, 'edit', row.u_ausenciasstamp));
                actionsCell.appendChild(createActionButton(deleteLabel, 'delete', row.u_ausenciasstamp));
                tr.appendChild(actionsCell);

                rowsBody.appendChild(tr);
            });
        }

        function loadAbsences() {
            setRowsLoading();
            var url = '/api/team-absences?date=' + encodeURIComponent(referenceDate || '');
            return fetch(url, { headers: { 'Accept': 'application/json' }, credentials: 'same-origin' })
                .then(function (response) {
                    return response.json().catch(function () {
                        return {};
                    }).then(function (payload) {
                        if (!response.ok) {
                            throw payload && payload.error ? payload.error : 'load_failed';
                        }
                        return payload;
                    });
                })
                .then(function (payload) {
                    renderRows(payload && Array.isArray(payload.rows) ? payload.rows : []);
                    if (referenceBadge) {
                        referenceBadge.textContent = formatDisplayDate((payload && payload.reference_date) || referenceDate || '');
                    }
                });
        }

        function openModal() {
            resetForm();
            if (referenceBadge) {
                referenceBadge.textContent = formatDisplayDate(referenceDate || '');
            }
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

            loadEmployees().catch(function () {
                setFeedback(loadError, false);
            });
            loadAbsences().catch(function () {
                renderRows([]);
                setFeedback(loadError, false);
            });

            if (employeeSelect) {
                employeeSelect.focus({ preventScroll: true });
            }
        }

        function closeModal() {
            if (keydownHandler) {
                document.removeEventListener('keydown', keydownHandler);
                keydownHandler = null;
            }
            modal.classList.remove('is-open');
            modal.setAttribute('hidden', 'true');
            modal.setAttribute('aria-hidden', 'true');
            document.body.classList.remove('modal-open');
            setSavingState(false);
            setFeedback('', false);
        }

        function getSelectedEmployeePayload() {
            if (!employeeSelect) {
                return { number: '', name: '' };
            }
            var selectedOption = employeeSelect.options[employeeSelect.selectedIndex];
            return {
                number: selectedOption ? (selectedOption.dataset.employeeNumber || '') : '',
                name: selectedOption ? (selectedOption.dataset.employeeName || selectedOption.textContent || '') : '',
            };
        }

        function editAbsence(row) {
            if (!row) {
                return;
            }
            ensureEmployeeOption(row.employee_number || '', row.employee_name || '');
            if (stampInput) {
                stampInput.value = row.u_ausenciasstamp || '';
            }
            if (employeeSelect) {
                employeeSelect.value = buildEmployeeOptionKey(row.employee_number || '', row.employee_name || '');
            }
            if (startInput) {
                startInput.value = row.start_date || '';
            }
            if (endInput) {
                endInput.value = row.end_date || '';
            }
            if (obsInput) {
                obsInput.value = row.obs || '';
            }
            if (saveButton) {
                saveButton.textContent = updateLabel;
            }
            setFeedback('', false);
            if (startInput) {
                startInput.focus({ preventScroll: true });
            }
        }

        function deleteAbsence(absenceStamp) {
            if (!absenceStamp) {
                return;
            }
            if (!window.confirm(deleteConfirmMessage)) {
                return;
            }
            setFeedback('', false);
            fetch('/api/team-absences/' + encodeURIComponent(absenceStamp), {
                method: 'DELETE',
                headers: { 'Accept': 'application/json' },
                credentials: 'same-origin',
            }).then(function (response) {
                return response.json().catch(function () {
                    return {};
                }).then(function (payload) {
                    if (!response.ok) {
                        throw payload && payload.error ? payload.error : 'delete_failed';
                    }
                    return payload;
                });
            }).then(function () {
                if (stampInput && stampInput.value === absenceStamp) {
                    resetForm();
                }
                return loadAbsences();
            }).catch(function () {
                setFeedback(deleteError, false);
            });
        }

        function handleSubmit(event) {
            event.preventDefault();
            var employee = getSelectedEmployeePayload();
            if (!employee.number) {
                setFeedback(missingEmployeeMessage, false);
                if (employeeSelect) {
                    employeeSelect.focus({ preventScroll: true });
                }
                return;
            }
            if (!startInput || !startInput.value || !endInput || !endInput.value) {
                setFeedback(missingDatesMessage, false);
                return;
            }
            if (endInput.value < startInput.value) {
                setFeedback(invalidRangeMessage, false);
                return;
            }

            var isEdit = Boolean(stampInput && stampInput.value);
            var url = isEdit
                ? '/api/team-absences/' + encodeURIComponent(stampInput.value)
                : '/api/team-absences';
            var method = isEdit ? 'PUT' : 'POST';
            var payload = {
                employee_number: employee.number,
                employee_name: employee.name,
                start_date: startInput.value,
                end_date: endInput.value,
                obs: obsInput ? obsInput.value : '',
                marcada: 0,
            };

            setFeedback('', false);
            setSavingState(true);
            fetch(url, {
                method: method,
                headers: {
                    'Accept': 'application/json',
                    'Content-Type': 'application/json',
                },
                credentials: 'same-origin',
                body: JSON.stringify(payload),
            }).then(function (response) {
                return response.json().catch(function () {
                    return {};
                }).then(function (body) {
                    if (!response.ok) {
                        throw body && body.error ? body.error : 'save_failed';
                    }
                    return body;
                });
            }).then(function () {
                resetForm();
                return loadAbsences();
            }).catch(function (errorCode) {
                if (errorCode === 'missing_employee_number') {
                    setFeedback(missingEmployeeMessage, false);
                    return;
                }
                if (errorCode === 'missing_dates') {
                    setFeedback(missingDatesMessage, false);
                    return;
                }
                if (errorCode === 'invalid_date_range') {
                    setFeedback(invalidRangeMessage, false);
                    return;
                }
                setFeedback(saveError, false);
            }).finally(function () {
                setSavingState(false);
            });
        }

        if (form) {
            form.addEventListener('submit', handleSubmit);
        }
        if (resetButton) {
            resetButton.addEventListener('click', function () {
                resetForm();
            });
        }
        if (closeButton) {
            closeButton.addEventListener('click', function () {
                closeModal();
            });
            closeButton.textContent = closeLabel;
        }
        if (rowsBody) {
            rowsBody.addEventListener('click', function (event) {
                var button = event.target.closest('[data-action]');
                if (!button) {
                    return;
                }
                var action = button.dataset.action || '';
                var absenceStamp = button.dataset.absenceStamp || '';
                var row = currentRows.find(function (item) {
                    return item.u_ausenciasstamp === absenceStamp;
                });
                if (action === 'edit') {
                    editAbsence(row);
                    return;
                }
                if (action === 'delete') {
                    deleteAbsence(absenceStamp);
                }
            });
        }

        modal.addEventListener('click', function (event) {
            if (event.target === modal) {
                closeModal();
            }
        });

        openButtons.forEach(function (button) {
            button.addEventListener('click', function () {
                openModal();
            });
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initTeamAbsences);
    } else {
        initTeamAbsences();
    }
})();
