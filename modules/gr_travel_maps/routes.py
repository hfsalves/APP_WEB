from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import secrets
import hmac
import json

from flask import Blueprint, Response, abort, current_app, jsonify, render_template, request, session, stream_with_context
from flask_login import current_user, login_required
from werkzeug.exceptions import HTTPException

from .access import can_consult, can_change, in_gr360_context
from .config import TravelMapsError
from . import service, reconstruction, engine


bp = Blueprint("gr_travel_maps", __name__, template_folder="templates", static_folder="static",
               static_url_path="/gr_travel_maps/static")


@bp.before_request
@login_required
def guard():
    if not in_gr360_context():
        abort(404)
    if not can_consult(current_user):
        abort(403)


@bp.after_request
def private_response(response):
    response.headers["Cache-Control"] = "private, no-store, max-age=0"
    response.headers["Pragma"] = "no-cache"
    return response


@bp.errorhandler(TravelMapsError)
def known_error(exc):
    return jsonify({"ok": False, "error": str(exc)}), exc.status_code


def respond(callback):
    try:
        return jsonify({"ok": True, **callback()})
    except (TravelMapsError, HTTPException):
        raise
    except Exception as exc:
        current_app.logger.warning("Mapas PHC: consulta indisponível (%s).", type(exc).__name__)
        return jsonify({"ok": False, "error": "Não foi possível consultar os dados. Tente novamente."}), 502


@bp.get("/mapas-deslocacoes")
def page():
    previous = datetime.now(ZoneInfo("Europe/Lisbon")).date().replace(day=1) - timedelta(days=1)
    return render_template("gr_travel_maps/monthly.html", initial_year=previous.year,
                           initial_month=previous.month, initial_feid=session.get("current_feid"))


@bp.get("/api/gr_mapas/empresas")
def companies():
    return respond(lambda: {"rows": [service.public_company(company)
                                     for company in service.list_companies_for_user(current_user)]})


@bp.get("/api/gr_mapas/mensal")
def monthly():
    return respond(lambda: service.monthly_panel(request.args.get("feid"), request.args.get("ano"),
                                                 request.args.get("mes"), current_user))


@bp.get("/api/gr_mapas/autos")
def measurements():
    return respond(lambda: service.monthly_measurements(request.args.get("feid"), request.args.get("ano"),
                                                        request.args.get("mes"), current_user))


def csrf_token():
    if not session.get('travel_maps_csrf'):
        session['travel_maps_csrf'] = secrets.token_urlsafe(32)
    return session['travel_maps_csrf']


def write_payload(validate=False):
    if not can_change(current_user, validate=validate):
        abort(403)
    supplied = request.headers.get('X-Travel-CSRF', '')
    expected = session.get('travel_maps_csrf', '')
    if not expected or not hmac.compare_digest(supplied.encode(), expected.encode()):
        abort(403)
    if request.content_length is None or request.content_length > 256_000:
        abort(413)
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        raise TravelMapsError('Envie um objeto JSON válido.')
    return payload


@bp.get('/mapas-deslocacoes/reconstrucao')
def reconstruction_page():
    return render_template('gr_travel_maps/reconstruction.html', csrf_token=csrf_token(),
        preference_key=engine.digest([str(current_user.get_id()) if hasattr(current_user, 'get_id') else str(getattr(current_user, 'USSTAMP', '')),
                                      str(getattr(current_user, 'LOGIN', ''))]))


@bp.get('/api/gr_mapas/contexto')
def reconstruction_context():
    def load():
        result = reconstruction.context(request.args.get('feid'), request.args.get('ano'), request.args.get('mes'),
            request.args.get('employee_key'), request.args.getlist('autos_feid') or None, current_user)
        return {**result, 'can_edit': can_change(current_user), 'can_validate': can_change(current_user, validate=True)}
    return respond(load)


@bp.get('/api/gr_mapas/propostas')
def proposals():
    return respond(lambda: reconstruction.list_month(request.args.get('feid'), request.args.get('ano'), request.args.get('mes'), current_user))


@bp.get('/api/gr_mapas/propostas/<map_id>')
def proposal_detail(map_id):
    def load():
        version = request.args.get('version')
        if version is not None:
            try:
                version = int(version)
            except ValueError:
                raise TravelMapsError('Versão inválida.') from None
        return reconstruction.detail(map_id, current_user, version)
    return respond(load)


@bp.post('/api/gr_mapas/propostas')
def generate_proposal():
    if request.accept_mimetypes.best == 'application/x-ndjson':
        return reconstruction_stream(write_payload())
    return respond(lambda: reconstruction.generate(write_payload(), current_user))


@bp.post('/api/gr_mapas/prever')
def preview_proposal():
    if request.accept_mimetypes.best == 'application/x-ndjson':
        return reconstruction_stream(write_payload(), persist=False)
    return respond(lambda: reconstruction.preview(write_payload(), current_user))


def reconstruction_stream(payload, *, persist=True):
    """Keep authorization/context on the request; no shared jobs or worker threads."""
    steps = reconstruction.generate_steps(payload, current_user, persist=persist)

    def encode(value):
        return json.dumps(value, ensure_ascii=False, allow_nan=False) + '\n'

    def messages():
        try:
            while True:
                try:
                    item = next(steps)
                except StopIteration as completed:
                    yield encode({'type': 'result', 'ok': True, **completed.value})
                    return
                yield encode(item)
        except TravelMapsError as exc:
            yield encode({'type': 'error', 'ok': False, 'status': exc.status_code, 'error': str(exc)})
        except HTTPException as exc:
            yield encode({'type': 'error', 'ok': False, 'status': exc.code, 'error': 'Sem acesso a estes dados ou sessão expirada.'})
        except Exception as exc:
            current_app.logger.warning('Mapas PHC: reconstrução interrompida (%s).', type(exc).__name__)
            yield encode({'type': 'error', 'ok': False, 'status': 502,
                          'error': 'Não foi possível concluir a reconstrução. Atualize os dados antes de tentar novamente.'})
        finally:
            steps.close()

    return Response(stream_with_context(messages()), content_type='application/x-ndjson; charset=utf-8',
                    headers={'X-Accel-Buffering': 'no', 'X-Content-Type-Options': 'nosniff'})


@bp.post('/api/gr_mapas/propostas/<map_id>/editar')
def edit_proposal(map_id):
    return respond(lambda: reconstruction.change(map_id, write_payload(), current_user, 'EDIT'))


@bp.post('/api/gr_mapas/propostas/<map_id>/validar')
def validate_proposal(map_id):
    return respond(lambda: reconstruction.change(map_id, write_payload(validate=True), current_user, 'VALIDATE'))


@bp.post('/api/gr_mapas/propostas/<map_id>/rejeitar')
def reject_proposal(map_id):
    return respond(lambda: reconstruction.change(map_id, write_payload(), current_user, 'REJECT'))
