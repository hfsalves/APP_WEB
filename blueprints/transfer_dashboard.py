"""GuestSpaTur transfer requests dashboard."""

from __future__ import annotations

import io
import json
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from flask import Blueprint, abort, jsonify, render_template, request, send_file
from flask_login import current_user, login_required
from sqlalchemy import text

from models import Acessos, db
from services.guest_transfer_service import transfer_request_hash
from services.multiempresa_service import MissingCurrentEntityError, get_current_feid
from services.transfer_dashboard_service import (
    TARGET_FEID,
    TransferDashboardError,
    build_transfer_dashboard,
    build_transfer_workbook,
    transfer_filters,
    transfer_period,
)
from services.transfer_management_service import TransferManagementError, normalize_transfer_edit


bp = Blueprint("transfer_dashboard", __name__)
logger = logging.getLogger(__name__)
LISBON = ZoneInfo("Europe/Lisbon")


def _has_permission(action: str = "consultar") -> bool:
    if bool(getattr(current_user, "ADMIN", False)):
        return True
    login = str(getattr(current_user, "LOGIN", "") or "").strip()
    if not login:
        return False
    access = Acessos.query.filter_by(utilizador=login, tabela="TRANSFERS").first()
    return bool(access and getattr(access, action, False))


def _has_access() -> bool:
    return _has_permission("consultar")


def _require_access() -> None:
    if not _has_access():
        abort(403)
    try:
        current_feid = get_current_feid()
    except MissingCurrentEntityError:
        abort(403)
    if current_feid != TARGET_FEID:
        abort(403)


def _require_permission(action: str) -> None:
    _require_access()
    if not _has_permission(action):
        abort(403)


def _management_schema_ready() -> bool:
    return bool(db.session.execute(text("""
        SELECT CASE WHEN OBJECT_ID('dbo.TRANSFERS_ARCHIVE', 'U') IS NOT NULL
                          AND OBJECT_ID('dbo.TRANSFERS_AUDIT', 'U') IS NOT NULL
                    THEN 1 ELSE 0 END
    """)).scalar())


def _management_row(transfer_stamp: str) -> dict | None:
    row = db.session.execute(text("""
        SELECT T.*, ISNULL(R.FEID, 0) AS RS_FEID
        FROM dbo.TRANSFERS AS T
        INNER JOIN dbo.RS AS R ON R.RSSTAMP=T.RSSTAMP
        WHERE T.TRANSFERSTAMP=:transfer_stamp
          AND ISNULL(R.FEID, 0)=:feid
    """), {"transfer_stamp": transfer_stamp, "feid": TARGET_FEID}).mappings().first()
    return dict(row) if row else None


def _audit_json(row: dict | None) -> str | None:
    if not row:
        return None
    return json.dumps(
        {key: value for key, value in row.items() if key != "RS_FEID"},
        ensure_ascii=False,
        default=str,
        separators=(",", ":"),
    )


def _record_audit(transfer_stamp: str, action: str, before: dict | None, after: dict | None) -> None:
    db.session.execute(text("""
        INSERT INTO dbo.TRANSFERS_AUDIT
            (TRANSFERSTAMP, ACAO, DADOS_ANTES, DADOS_DEPOIS, UTILIZADOR)
        VALUES
            (:transfer_stamp, :action, :before, :after, :user_login)
    """), {
        "transfer_stamp": transfer_stamp,
        "action": action,
        "before": _audit_json(before),
        "after": _audit_json(after),
        "user_login": str(getattr(current_user, "LOGIN", "") or "").strip()[:60],
    })


def _request_payload() -> dict:
    period = transfer_period(request.args.get("period"), request.args.get("start"), request.args.get("end"))
    return build_transfer_dashboard(db.engine, period, transfer_filters(request.args), feid=TARGET_FEID)


@bp.get("/dashboard/transfers")
@login_required
def dashboard_page():
    _require_access()
    period = transfer_period(request.args.get("period"), request.args.get("start"), request.args.get("end"))
    return render_template(
        "transfer_dashboard.html",
        initial_period=period["mode"],
        initial_start=period["start"].isoformat() if period.get("start") else "",
        initial_end=period["end"].isoformat() if period.get("end") else "",
        can_edit_transfer=_has_permission("editar"),
        can_delete_transfer=_has_permission("eliminar"),
    )


@bp.get("/api/dashboard/transfers")
@login_required
def dashboard_data():
    _require_access()
    try:
        response = jsonify({"ok": True, "data": _request_payload()})
    except TransferDashboardError as exc:
        response = jsonify({"ok": False, "error": str(exc)})
        response.status_code = 400
    except Exception:
        logger.exception("Erro ao carregar o resumo de transfers.")
        response = jsonify({"ok": False, "error": "Não foi possível carregar os pedidos de transfer."})
        response.status_code = 500
    response.headers["Cache-Control"] = "private, no-store, max-age=0"
    return response


@bp.get("/dashboard/transfers/export.xlsx")
@login_required
def dashboard_export():
    _require_access()
    try:
        payload = _request_payload()
        exported_at = datetime.now(LISBON)
        content = build_transfer_workbook(payload, exported_at=exported_at)
    except TransferDashboardError as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400
    except Exception:
        logger.exception("Erro ao exportar o resumo de transfers.")
        return jsonify({"ok": False, "error": "Não foi possível exportar os pedidos de transfer."}), 500
    return send_file(
        io.BytesIO(content),
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name=f"transfers_{exported_at:%Y%m%d_%H%M}.xlsx",
        max_age=0,
    )


@bp.put("/api/dashboard/transfers/<transfer_stamp>")
@login_required
def dashboard_update(transfer_stamp: str):
    _require_permission("editar")
    if not _management_schema_ready():
        return jsonify({"ok": False, "error": "Falta aplicar a estrutura de gestão de transfers."}), 503
    before = _management_row(str(transfer_stamp or "").strip())
    if not before:
        return jsonify({"ok": False, "error": "Pedido de transfer não encontrado."}), 404
    try:
        values = normalize_transfer_edit(request.get_json(silent=True) or {})
        request_hash = transfer_request_hash(
            rsstamp=before.get("RSSTAMP"),
            route=values["origin"],
            service_date=values["service_date"],
            service_time=values["service_time"],
            flight=values["flight"],
        )
        duplicate = db.session.execute(text("""
            SELECT TOP 1 TRANSFERSTAMP
            FROM dbo.TRANSFERS
            WHERE REQUEST_HASH=:request_hash
              AND TRANSFERSTAMP<>:transfer_stamp
              AND UPPER(LTRIM(RTRIM(ISNULL(ESTADO,'')))) NOT IN ('CANCELADO','CANCELADA')
        """), {"request_hash": request_hash, "transfer_stamp": transfer_stamp}).scalar()
        if duplicate:
            return jsonify({
                "ok": False,
                "error": "Já existe outro pedido ativo com o mesmo percurso, data, hora e voo.",
                "duplicate_transfer_stamp": str(duplicate),
            }), 409

        db.session.execute(text("""
            UPDATE dbo.TRANSFERS
            SET ORIGEM=:origin,
                DATA_CHEGADA=:service_date,
                HORA_CHEGADA=:service_time,
                NUM_VOO=:flight,
                TEM_PARTIDA=:has_departure,
                DATA_PARTIDA=:departure_date,
                HORA_PARTIDA=:departure_time,
                MORADA=:address,
                NOME_HOSPEDE=:guest_name,
                NUM_PESSOAS=:people,
                CONTACTO_TELEF=:guest_phone,
                EMAIL_HOSPEDE=:guest_email,
                MOTORISTA_CONTACTO=:driver_phone,
                MOTORISTA_EMAIL=:driver_email,
                VALOR=:value,
                REQUEST_HASH=:request_hash,
                DTALT=GETDATE()
            WHERE TRANSFERSTAMP=:transfer_stamp
        """), {
            **values,
            "has_departure": 1 if values["has_departure"] else 0,
            "request_hash": request_hash,
            "transfer_stamp": transfer_stamp,
        })
        after = _management_row(transfer_stamp)
        _record_audit(transfer_stamp, "EDITAR", before, after)
        db.session.commit()
        return jsonify({"ok": True, "message": "Pedido de transfer atualizado."})
    except TransferManagementError as exc:
        db.session.rollback()
        return jsonify({"ok": False, "error": str(exc)}), 400
    except Exception:
        db.session.rollback()
        logger.exception("Erro ao atualizar o transfer %s.", transfer_stamp)
        return jsonify({"ok": False, "error": "Não foi possível atualizar o pedido de transfer."}), 500


@bp.delete("/api/dashboard/transfers/<transfer_stamp>")
@login_required
def dashboard_delete(transfer_stamp: str):
    _require_permission("eliminar")
    if not _management_schema_ready():
        return jsonify({"ok": False, "error": "Falta aplicar a estrutura de gestão de transfers."}), 503
    before = _management_row(str(transfer_stamp or "").strip())
    if not before:
        return jsonify({"ok": False, "error": "Pedido de transfer não encontrado."}), 404
    payload = request.get_json(silent=True) or {}
    reason = str(payload.get("reason") or "Eliminado manualmente no dashboard.").strip()[:250]
    user_login = str(getattr(current_user, "LOGIN", "") or "").strip()[:60]
    try:
        db.session.execute(text("""
            INSERT INTO dbo.TRANSFERS_ARCHIVE
            SELECT T.*, SYSUTCDATETIME(), :user_login, :reason
            FROM dbo.TRANSFERS AS T
            WHERE T.TRANSFERSTAMP=:transfer_stamp
              AND NOT EXISTS (
                  SELECT 1 FROM dbo.TRANSFERS_ARCHIVE AS A
                  WHERE A.TRANSFERSTAMP=T.TRANSFERSTAMP
              )
        """), {
            "user_login": user_login,
            "reason": reason,
            "transfer_stamp": transfer_stamp,
        })
        email_id = before.get("EMAIL_ID")
        if email_id:
            db.session.execute(text("""
                UPDATE dbo.EMAIL_QUEUE
                SET ESTADO='CANCELADO',
                    ERRO_ULTIMA_TENTATIVA='Cancelado: pedido de transfer eliminado no dashboard.'
                WHERE ID=:email_id
                  AND UPPER(LTRIM(RTRIM(ISNULL(ESTADO,'')))) IN ('PENDENTE','A_ENVIAR','ERRO')
            """), {"email_id": email_id})
        _record_audit(transfer_stamp, "ELIMINAR", before, None)
        db.session.execute(
            text("DELETE FROM dbo.TRANSFERS WHERE TRANSFERSTAMP=:transfer_stamp"),
            {"transfer_stamp": transfer_stamp},
        )
        db.session.commit()
        return jsonify({"ok": True, "message": "Pedido de transfer eliminado."})
    except Exception:
        db.session.rollback()
        logger.exception("Erro ao eliminar o transfer %s.", transfer_stamp)
        return jsonify({"ok": False, "error": "Não foi possível eliminar o pedido de transfer."}), 500

