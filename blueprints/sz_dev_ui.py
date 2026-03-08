from flask import Blueprint, render_template
from flask_login import login_required

bp = Blueprint("sz_dev_ui", __name__, url_prefix="/dev")


@bp.route("/sz-ui")
@login_required
def sz_ui_catalog():
    return render_template("sz_ui.html", page_title="SZ UI Catalog")
