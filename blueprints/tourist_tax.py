from __future__ import annotations

from datetime import date

from flask import Blueprint, jsonify, render_template, request, send_file
from flask_login import current_user, login_required

from services.tourist_tax_service import audit_tourist_tax_access, build_tourist_tax_workbook, tourist_tax_report

bp = Blueprint("tourist_tax", __name__)


def _report():
    return tourist_tax_report(request.args.get("ano", date.today().year), request.args.get("tipo", "mensal"), request.args.get("periodo", date.today().month), feid=2)


@bp.route("/guestspa/taxas-turisticas")
@login_required
def tourist_tax_page():
    today = date.today()
    return render_template("tourist_tax.html", page_title="Taxas turísticas", year=today.year, month=today.month)


@bp.route("/guestspa/api/taxas-turisticas")
@login_required
def tourist_tax_api():
    try:
        report = _report(); audit_tourist_tax_access(getattr(current_user, "LOGIN", ""), report)
        return jsonify({"ok": True, **report})
    except ValueError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
    except Exception:
        return jsonify({"ok": False, "error": "Não foi possível gerar o mapa de taxas turísticas."}), 500


@bp.route("/guestspa/api/taxas-turisticas/exportar")
@login_required
def tourist_tax_export():
    try:
        report = _report(); audit_tourist_tax_access(getattr(current_user, "LOGIN", ""), report, exported=True)
        from io import BytesIO
        return send_file(BytesIO(build_tourist_tax_workbook(report)), as_attachment=True, download_name=f"taxas-turisticas-{report['periodo']['rotulo']}.xlsx", mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    except ValueError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
    except Exception:
        return jsonify({"ok": False, "error": "Não foi possível exportar o mapa de taxas turísticas."}), 500
