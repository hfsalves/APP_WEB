(function () {
    function initTeamRegularizations() {
        var modal = document.getElementById('team-regularization-modal');
        var openButtons = Array.prototype.slice.call(document.querySelectorAll('[data-team-regularizations-open]'));
        if (!modal || !openButtons.length) {
            return;
        }

        var page = document.body;
        var referenceDate = page.dataset.referenceDate || '';
        var defaultMonth = referenceDate ? String(referenceDate).slice(0, 7) : '';
        var form = modal.querySelector('[data-team-regularization-form]');
        var stampInput = modal.querySelector('[data-team-regularization-stamp]');
        var monthInput = modal.querySelector('[data-team-regularization-month]');
        var employeeSelect = modal.querySelector('[data-team-regularization-employee-select]');
        var obsInput = modal.querySelector('[data-team-regularization-obs]');
        var valueInput = modal.querySelector('[data-team-regularization-value]');
        var saveButton = modal.querySelector('[data-team-regularization-save]');
        var resetButton = modal.querySelector('[data-team-regularization-reset]');
        var closeButton = modal.querySelector('[data-team-regularization-close]');
        var feedback = modal.querySelector('[data-team-regularization-feedback]');
        var rowsBody = modal.querySelector('[data-team-regularization-rows]');
        var monthBadge = modal.querySelector('[data-team-regularization-month-badge]');

        var saveLabel = modal.dataset.saveLabel || 'Guardar';
        var updateLabel = modal.dataset.updateLabel || 'Atualizar';
        var loadingLabel = modal.dataset.savingLabel || saveLabel;
        var editLabel = modal.dataset.editLabel || 'Editar';
        var deleteLabel = modal.dataset.deleteLabel || 'Remover';
        var closeLabel = modal.dataset.closeLabel || 'Fechar';
        var loadError = modal.dataset.loadError || 'Nao foi possivel carregar as regularizacoes.';
        var saveError = modal.dataset.saveError || 'Nao foi possivel guardar a regularizacao.';
        var deleteError = modal.dataset.deleteError || 'Nao foi possivel remover a regularizacao.';
        var missingEmployeeMessage = modal.dataset.missingEmployee || 'Selecione um colaborador.';
        var missingMonthMessage = modal.dataset.missingMonth || 'Indique o mes.';
        var missingValueMessage = modal.dataset.missingValue || 'Indique o valor da regularizacao.';
        var emptyMessage = modal.dataset.emptyMessage || 'Sem regularizacoes neste mes.';
        var deleteConfirmMessage = modal.dataset.deleteConfirm || 'Remover esta regularizacao?';
        var employeePlaceholder = modal.dataset.employeePlaceholder || 'Selecione um colaborador';
        var defaultLoadingRow = modal.dataset.loadingLabel || 'A carregar...';
        var keydownHandler = null;
        var employeesLoaded = false;
        var employeesPromise = null;
        var currentRows = [];

        function setFeedback(message, isSuccess) {
            if (!feedback) {
                return;
            }
            feedback.textContent = message || '';
            feedback.classList.toggle('is-success', Boolean(message) && isSuccess === true);
        }

        function formatMonthLabel(value) {
            if (!value) {
                return '';
            }
            var parts = String(value).split('-');
            if (parts.length !== 2) {
                return String(value);
            }
            return parts[1] + '/' + parts[0];
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
            var normalizedName = name ? String(name).trim().toUpperCase() : '';
            return normalizedNumber + '||' + normalizedName;
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

        function setSavingState(isSaving) {
            if (saveButton) {
                saveButton.disabled = isSaving;
                saveButton.textContent = isSaving ? loadingLabel : (stampInput && stampInput.value ? updateLabel : saveLabel);
            }
            if (resetButton) {
                resetButton.disabled = isSaving;
            }
            if (monthInput) {
                monthInput.disabled = isSaving;
            }
            if (employeeSelect) {
                employeeSelect.disabled = isSaving;
            }
            if (obsInput) {
                obsInput.disabled = isSaving;
            }
            if (valueInput) {
                valueInput.disabled = isSaving;
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
            if (monthInput) {
                monthInput.value = defaultMonth;
            }
            if (employeeSelect) {
                employeeSelect.value = '';
            }
            if (obsInput) {
                obsInput.value = '';
            }
            if (valueInput) {
                valueInput.value = '';
            }
            if (saveButton) {
                saveButton.textContent = saveLabel;
            }
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

        function createActionButton(label, action, stamp) {
            var button = document.createElement('button');
            button.type = 'button';
            button.className = 'team-regularization-action-button';
            button.textContent = label;
            button.dataset.action = action;
            button.dataset.regularizationStamp = stamp || '';
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

                var monthCell = document.createElement('td');
                monthCell.textContent = row.month_label || '';
                tr.appendChild(monthCell);

                var numberCell = document.createElement('td');
                numberCell.textContent = row.employee_number || '';
                tr.appendChild(numberCell);

                var nameCell = document.createElement('td');
                nameCell.textContent = row.employee_name || '';
                tr.appendChild(nameCell);

                var obsCell = document.createElement('td');
                obsCell.textContent = row.obs || '';
                tr.appendChild(obsCell);

                var valueCell = document.createElement('td');
                valueCell.className = 'numeric';
                valueCell.textContent = Number(row.value || 0).toFixed(2);
                tr.appendChild(valueCell);

                var actionsCell = document.createElement('td');
                actionsCell.className = 'team-regularization-actions';
                actionsCell.appendChild(createActionButton(editLabel, 'edit', row.u_intersol_regularizacoesstamp));
                actionsCell.appendChild(createActionButton(deleteLabel, 'delete', row.u_intersol_regularizacoesstamp));
                tr.appendChild(actionsCell);

                rowsBody.appendChild(tr);
            });
        }

        function loadRegularizations() {
            setRowsLoading();
            var monthValue = monthInput && monthInput.value ? monthInput.value : defaultMonth;
            var url = '/api/team-intersol-regularizations?month=' + encodeURIComponent(monthValue || '') + '&date=' + encodeURIComponent(referenceDate || '');
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
                    if (monthBadge) {
                        monthBadge.textContent = formatMonthLabel((payload && payload.month) || monthValue || '');
                    }
                });
        }

        function editRegularization(row) {
            if (!row) {
                return;
            }
            ensureEmployeeOption(row.employee_number || '', row.employee_name || '');
            if (stampInput) {
                stampInput.value = row.u_intersol_regularizacoesstamp || '';
            }
            if (monthInput) {
                monthInput.value = row.month_value || defaultMonth;
            }
            if (employeeSelect) {
                employeeSelect.value = buildEmployeeOptionKey(row.employee_number || '', row.employee_name || '');
            }
            if (obsInput) {
                obsInput.value = row.obs || '';
            }
            if (valueInput) {
                valueInput.value = row.value !== undefined && row.value !== null ? String(row.value) : '';
            }
            if (saveButton) {
                saveButton.textContent = updateLabel;
            }
            setFeedback('', false);
            if (obsInput) {
                obsInput.focus({ preventScroll: true });
            }
        }

        function deleteRegularization(regularizationStamp) {
            if (!regularizationStamp) {
                return;
            }
            if (!window.confirm(deleteConfirmMessage)) {
                return;
            }
            setFeedback('', false);
            fetch('/api/team-intersol-regularizations/' + encodeURIComponent(regularizationStamp), {
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
                if (stampInput && stampInput.value === regularizationStamp) {
                    resetForm();
                }
                return loadRegularizations();
            }).catch(function () {
                setFeedback(deleteError, false);
            });
        }

        function handleSubmit(event) {
            event.preventDefault();
            var employee = getSelectedEmployeePayload();
            var monthValue = monthInput && monthInput.value ? monthInput.value : '';
            var valueValue = valueInput && valueInput.value !== '' ? valueInput.value : '';
            if (!monthValue) {
                setFeedback(missingMonthMessage, false);
                if (monthInput) {
                    monthInput.focus({ preventScroll: true });
                }
                return;
            }
            if (!employee.number) {
                setFeedback(missingEmployeeMessage, false);
                if (employeeSelect) {
                    employeeSelect.focus({ preventScroll: true });
                }
                return;
            }
            if (valueValue === '' || isNaN(Number(valueValue))) {
                setFeedback(missingValueMessage, false);
                if (valueInput) {
                    valueInput.focus({ preventScroll: true });
                }
                return;
            }

            var isEdit = Boolean(stampInput && stampInput.value);
            var url = isEdit
                ? '/api/team-intersol-regularizations/' + encodeURIComponent(stampInput.value)
                : '/api/team-intersol-regularizations';
            var method = isEdit ? 'PUT' : 'POST';
            var payload = {
                month: monthValue,
                employee_number: employee.number,
                employee_name: employee.name,
                obs: obsInput ? obsInput.value : '',
                value: valueValue,
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
                if (monthInput) {
                    defaultMonth = monthInput.value || defaultMonth;
                }
                resetForm();
                return loadRegularizations();
            }).catch(function (errorCode) {
                if (errorCode === 'missing_employee_number') {
                    setFeedback(missingEmployeeMessage, false);
                    return;
                }
                if (errorCode === 'invalid_month') {
                    setFeedback(missingMonthMessage, false);
                    return;
                }
                if (errorCode === 'missing_value') {
                    setFeedback(missingValueMessage, false);
                    return;
                }
                setFeedback(saveError, false);
            }).finally(function () {
                setSavingState(false);
            });
        }

        function openModal() {
            resetForm();
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

            Promise.all([loadEmployees(), loadRegularizations()]).catch(function () {
                setFeedback(loadError, false);
            });

            if (monthInput) {
                monthInput.focus({ preventScroll: true });
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

        if (form) {
            form.addEventListener('submit', handleSubmit);
        }
        if (resetButton) {
            resetButton.addEventListener('click', function () {
                resetForm();
            });
        }
        if (monthInput) {
            monthInput.addEventListener('change', function () {
                if (monthBadge) {
                    monthBadge.textContent = formatMonthLabel(monthInput.value || '');
                }
                loadRegularizations().catch(function () {
                    setFeedback(loadError, false);
                });
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
                var regularizationStamp = button.dataset.regularizationStamp || '';
                var row = currentRows.find(function (item) {
                    return item.u_intersol_regularizacoesstamp === regularizationStamp;
                });
                if (action === 'edit') {
                    editRegularization(row);
                    return;
                }
                if (action === 'delete') {
                    deleteRegularization(regularizationStamp);
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
        document.addEventListener('DOMContentLoaded', initTeamRegularizations);
    } else {
        initTeamRegularizations();
    }
})();
