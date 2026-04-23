from flask import Flask

from i18n import i18n_enabled, sync_i18n_config_from_params


def test_sync_i18n_config_accepts_case_insensitive_parameter_names():
    app = Flask(__name__)
    app.config["USA_MULTILINGUA"] = 0

    sync_i18n_config_from_params(app, {"usa_multilingua": True})

    assert i18n_enabled(app)


def test_sync_i18n_config_accepts_case_insensitive_language_parameter_names():
    app = Flask(__name__)
    app.config["DEFAULT_LANGUAGE"] = "pt_PT"

    sync_i18n_config_from_params(app, {"idioma_app": "en"})

    assert app.config["DEFAULT_LANGUAGE"] == "en"
