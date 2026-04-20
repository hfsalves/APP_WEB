(function () {
    function initTeamRoles() {
        var modal = document.getElementById('team-role-modal');
        var openButtons = Array.prototype.slice.call(document.querySelectorAll('[data-team-roles-open]'));
        if (!modal || !openButtons.length) {
            return;
        }

        var form = modal.querySelector('[data-team-role-form]');
        var editingNumberInput = modal.querySelector('[data-team-role-number]');
        var employeeSelect = modal.querySelector('[data-team-role-employee-select]');
        var roleSelect = modal.querySelector('[data-team-role-select]');
        var saveButton = modal.querySelector('[data-team-role-save]');
        var resetButton = modal.querySelector('[data-team-role-reset]');
        var closeButton = modal.querySelector('[data-team-role-close]');
        var feedback = modal.querySelector('[data-team-role-feedback]');
        var rowsBody = modal.querySelector('[data-team-role-rows]');

        var saveLabel = modal.dataset.saveLabel || 'Guardar';
        var updateLabel = modal.dataset.updateLabel || 'Atualizar';
        var loadingLabel = modal.dataset.savingLabel || saveLabel;
        var editLabel = modal.dataset.editLabel || 'Editar';
        var deleteLabel = modal.dataset.deleteLabel || 'Remover';
        var loadError = modal.dataset.loadError || 'Nao foi possivel carregar os roles INTERSOL.';
        var saveError = modal.dataset.saveError || 'Nao foi possivel guardar o role INTERSOL.';
        var deleteError = modal.dataset.deleteError || 'Nao foi possivel remover o role INTERSOL.';
        var missingEmployeeMessage = modal.dataset.missingEmployee || 'Selecione um colaborador.';
        var missingRoleMessage = modal.dataset.missingRole || 'Selecione um role.';
        var emptyMessage = modal.dataset.emptyMessage || 'Sem roles configurados.';
        var deleteConfirmMessage = modal.dataset.deleteConfirm || 'Remover este role INTERSOL?';
        var employeePlaceholder = modal.dataset.employeePlaceholder || 'Selecione um colaborador';
        var defaultLoadingRow = modal.dataset.loadingLabel || 'A carregar...';

        var keydownHandler = null;
        var employeesLoaded = false;
        var employeesPromise = null;
        var currentRows = [];

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

        function setFeedback(message, isSuccess) {
            if (!feedback) {
                return;
            }
            feedback.textContent = message || '';
            feedback.classList.toggle('is-success', Boolean(message) && isSuccess === true);
        }

        function syncEmployeeSelectState(isSaving) {
            if (!employeeSelect) {
                return;
            }
            employeeSelect.disabled = Boolean(isSaving) || Boolean(editingNumberInput && editingNumberInput.value);
        }

        function setSavingState(isSaving) {
            if (saveButton) {
                saveButton.disabled = isSaving;
                saveButton.textContent = isSaving ? loadingLabel : (editingNumberInput && editingNumberInput.value ? updateLabel : saveLabel);
            }
            if (resetButton) {
                resetButton.disabled = isSaving;
            }
            if (roleSelect) {
                roleSelect.disabled = isSaving;
            }
            syncEmployeeSelectState(isSaving);
        }

        function setRowsLoading() {
            if (!rowsBody) {
                return;
            }
            rowsBody.innerHTML = '';
            var row = document.createElement('tr');
            var cell = document.createElement('td');
            cell.colSpan = 4;
            cell.className = 'modal-empty';
            cell.textContent = defaultLoadingRow;
            row.appendChild(cell);
            rowsBody.appendChild(row);
        }

        function resetForm() {
            if (editingNumberInput) {
                editingNumberInput.value = '';
            }
            if (employeeSelect) {
                employeeSelect.value = '';
            }
            if (roleSelect) {
                roleSelect.value = '';
            }
            if (saveButton) {
                saveButton.textContent = saveLabel;
            }
            syncEmployeeSelectState(false);
            setFeedback('', false);
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

        function createActionButton(label, action, employeeNumber) {
            var button = document.createElement('button');
            button.type = 'button';
            button.className = 'team-role-action-button';
            button.textContent = label;
            button.dataset.action = action;
            button.dataset.employeeNumber = employeeNumber || '';
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
                emptyCell.colSpan = 4;
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

                var roleCell = document.createElement('td');
                roleCell.textContent = row.role_label || row.role || '';
                tr.appendChild(roleCell);

                var actionsCell = document.createElement('td');
                actionsCell.className = 'team-role-actions';
                actionsCell.appendChild(createActionButton(editLabel, 'edit', row.employee_number));
                actionsCell.appendChild(createActionButton(deleteLabel, 'delete', row.employee_number));
                tr.appendChild(actionsCell);

                rowsBody.appendChild(tr);
            });
        }

        function loadRoles() {
            setRowsLoading();
            return fetch('/api/team-intersol-roles', { headers: { 'Accept': 'application/json' }, credentials: 'same-origin' })
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
                });
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

        function editRole(row) {
            if (!row) {
                return;
            }
            ensureEmployeeOption(row.employee_number || '', row.employee_name || '');
            if (editingNumberInput) {
                editingNumberInput.value = row.employee_number || '';
            }
            if (employeeSelect) {
                employeeSelect.value = buildEmployeeOptionKey(row.employee_number || '', row.employee_name || '');
            }
            if (roleSelect) {
                roleSelect.value = row.role || '';
            }
            if (saveButton) {
                saveButton.textContent = updateLabel;
            }
            syncEmployeeSelectState(false);
            setFeedback('', false);
            if (roleSelect) {
                roleSelect.focus({ preventScroll: true });
            }
        }

        function deleteRole(employeeNumber) {
            if (!employeeNumber) {
                return;
            }
            if (!window.confirm(deleteConfirmMessage)) {
                return;
            }
            setFeedback('', false);
            fetch('/api/team-intersol-roles/' + encodeURIComponent(employeeNumber), {
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
                if (editingNumberInput && editingNumberInput.value === employeeNumber) {
                    resetForm();
                }
                return loadRoles();
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
            if (!roleSelect || !roleSelect.value) {
                setFeedback(missingRoleMessage, false);
                if (roleSelect) {
                    roleSelect.focus({ preventScroll: true });
                }
                return;
            }

            var payload = {
                employee_number: employee.number,
                employee_name: employee.name,
                role: roleSelect.value,
            };

            setFeedback('', false);
            setSavingState(true);
            fetch('/api/team-intersol-roles', {
                method: 'POST',
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
                return loadRoles();
            }).catch(function (errorCode) {
                if (errorCode === 'missing_employee_number') {
                    setFeedback(missingEmployeeMessage, false);
                    return;
                }
                if (errorCode === 'invalid_role') {
                    setFeedback(missingRoleMessage, false);
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

            Promise.all([loadEmployees(), loadRoles()]).catch(function () {
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
            closeButton.textContent = modal.dataset.closeLabel || 'Fechar';
        }
        if (rowsBody) {
            rowsBody.addEventListener('click', function (event) {
                var button = event.target.closest('[data-action]');
                if (!button) {
                    return;
                }
                var action = button.dataset.action || '';
                var employeeNumber = button.dataset.employeeNumber || '';
                var row = currentRows.find(function (item) {
                    return item.employee_number === employeeNumber;
                });
                if (action === 'edit') {
                    editRole(row);
                    return;
                }
                if (action === 'delete') {
                    deleteRole(employeeNumber);
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
        document.addEventListener('DOMContentLoaded', initTeamRoles);
    } else {
        initTeamRoles();
    }
})();
