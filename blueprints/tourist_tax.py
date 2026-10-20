from __future__ import annotations

from datetime import date

from flask import Blueprint, abort, current_app, jsonify, render_template, request, send_file
from flask_login import current_user, login_required
from sqlalchemy import text

from models import db
from services.tourist_tax_service import audit_tourist_tax_access, build_tourist_tax_workbook, tourist_tax_report

bp = Blueprint("tourist_tax", __name__)
ACCESS_TABLE = "TAXAS_TURISTICAS"


def _can_view() -> bool:
    if bool(getattr(current_user, "ADMIN", False)):
        return True
    login = str(getattr(current_user, "LOGIN", "") or "").strip()
    if not login:
        return False
    return bool(db.session.execute(text("""
        SELECT TOP 1 1
        FROM dbo.ACESSOS
        WHERE LOWER(LTRIM(RTRIM(ISNULL(UTILIZADOR, '')))) = LOWER(:login)
          AND UPPER(LTRIM(RTRIM(ISNULL(TABELA, '')))) = :table_name
          AND ISNULL(CONSULTAR, 0) = 1
    """), {"login": login, "table_name": ACCESS_TABLE}).scalar())


def _require_view() -> None:
    if not _can_view():
        abort(403)


def _report():
    return tourist_tax_report(request.args.get("ano", date.today().year), request.args.get("tipo", "mensal"), request.args.get("periodo", date.today().month), feid=2)


def _json_report(report):
    payload = dict(report)
    payload["linhas"] = [
        {
            **row,
            "checkin": row["checkin"].isoformat(),
            "checkout": row["checkout"].isoformat(),
        }
        for row in report.get("linhas", [])
    ]
    return payload


@bp.route("/guestspa/taxas-turisticas")
@login_required
def tourist_tax_page():
    _require_view()
    today = date.today()
    return render_template("tourist_tax.html", page_title="Taxas turísticas", year=today.year, month=today.month)


@bp.route("/guestspa/api/taxas-turisticas")
@login_required
def tourist_tax_api():
    _require_view()
    try:
        report = _report(); audit_tourist_tax_access(getattr(current_user, "LOGIN", ""), report)
        return jsonify({"ok": True, **_json_report(report)})
    except ValueError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
    except Exception:
        db.session.rollback()
        current_app.logger.exception("Erro ao gerar o mapa de taxas turísticas.")
        return jsonify({"ok": False, "error": "Não foi possível gerar o mapa de taxas turísticas."}), 500


@bp.route("/guestspa/api/taxas-turisticas/exportar")
@login_required
def tourist_tax_export():
    _require_view()
    try:
        report = _report(); audit_tourist_tax_access(getattr(current_user, "LOGIN", ""), report, exported=True)
        from io import BytesIO
        return send_file(BytesIO(build_tourist_tax_workbook(report)), as_attachment=True, download_name=f"taxas-turisticas-{report['periodo']['rotulo']}.xlsx", mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    except ValueError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
    except Exception:
        db.session.rollback()
        current_app.logger.exception("Erro ao exportar o mapa de taxas turísticas.")
        return jsonify({"ok": False, "error": "Não foi possível exportar o mapa de taxas turísticas."}), 500
