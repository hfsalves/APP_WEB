(function () {
    function initTeamCreate() {
        var modal = document.getElementById('team-create-modal');
        var opener = document.querySelector('[data-team-create-open]');
        if (!modal || !opener) return;

        var form = modal.querySelector('[data-team-create-form]');
        var code = form.elements.code;
        var description = form.elements.description;
        var planning = form.elements.planning;
        var save = modal.querySelector('[data-team-create-save]');
        var cancel = modal.querySelector('[data-team-create-close]');
        var feedback = modal.querySelector('[data-team-create-feedback]');
        var errors = JSON.parse(modal.dataset.errorMap || '{}');
        var saveLabel = save.textContent;
        var saving = false;

        function setSaving(value) {
            saving = value;
            [code, description, planning, save, cancel].forEach(function (element) {
                element.disabled = value;
            });
            form.setAttribute('aria-busy', String(value));
            save.textContent = value ? modal.dataset.savingLabel : saveLabel;
        }

        function close() {
            if (saving) return;
            modal.hidden = true;
            modal.setAttribute('aria-hidden', 'true');
            modal.classList.remove('is-open');
            document.body.classList.remove('modal-open');
            document.removeEventListener('keydown', onKeydown);
            opener.focus();
        }

        function onKeydown(event) {
            if (event.key === 'Escape') {
                event.preventDefault();
                close();
            } else if (event.key === 'Tab') {
                var fields = [code, description, planning, cancel, save].filter(function (field) {
                    return !field.disabled;
                });
                if (!fields.length) {
                    event.preventDefault();
                } else if (event.shiftKey && document.activeElement === fields[0]) {
                    event.preventDefault();
                    fields[fields.length - 1].focus();
                } else if (!event.shiftKey && document.activeElement === fields[fields.length - 1]) {
                    event.preventDefault();
                    fields[0].focus();
                }
            }
        }

        opener.addEventListener('click', function () {
            form.reset();
            feedback.textContent = '';
            setSaving(false);
            modal.hidden = false;
            modal.setAttribute('aria-hidden', 'false');
            modal.classList.add('is-open');
            document.body.classList.add('modal-open');
            document.addEventListener('keydown', onKeydown);
            code.focus();
        });
        cancel.addEventListener('click', close);
        modal.addEventListener('click', function (event) {
            if (event.target === modal) close();
        });
        form.addEventListener('submit', async function (event) {
            event.preventDefault();
            if (saving || !form.reportValidity()) return;
            var payload = {code: code.value.trim(), description: description.value.trim(), planning: planning.value};
            feedback.textContent = '';
            setSaving(true);
            try {
                var response = await fetch('/api/teams', {
                    method: 'POST',
                    credentials: 'same-origin',
                    headers: {'Content-Type': 'application/json', 'Accept': 'application/json'},
                    body: JSON.stringify(payload)
                });
                var data = await response.json().catch(function () { return {}; });
                if (!response.ok || !data.team || !data.team.code) {
                    feedback.textContent = errors[data.error] || modal.dataset.errorGeneric;
                    setSaving(false);
                    if (data.error === 'team_code_exists') code.focus();
                    return;
                }
                window.location.reload();
            } catch (error) {
                feedback.textContent = modal.dataset.errorGeneric;
                setSaving(false);
            }
        });
    }
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initTeamCreate);
    } else {
        initTeamCreate();
    }
})();
