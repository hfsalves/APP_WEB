import os
import re
import uuid

from flask import Blueprint, current_app, jsonify, render_template, request, send_file
from flask_login import current_user, login_required
from sqlalchemy import text
from werkzeug.utils import secure_filename

from models import db
from services.multiempresa_service import MissingCurrentEntityError, get_current_feid
from services.photo_enhancer_service import (
    PHOTO_ENHANCER_PROMPT,
    PhotoEnhancerError,
    column_exists,
    create_zip_for_session,
    enhance_photo,
    ensure_photo_enhancer_schema,
    ensure_session_folders,
    get_file,
    get_session,
    list_session_files,
    photo_enhancer_max_bytes,
    photo_enhancer_model,
    public_to_abs,
    remove_public_file,
    remove_session_folder,
    row_to_file,
    row_to_session,
    save_uploaded_file,
)


bp = Blueprint('photo_enhancer', __name__)


def _stamp(value) -> str:
    return str(value or '').strip()[:25]


def _is_admin() -> bool:
    return bool(getattr(current_user, 'ADMIN', False) or getattr(current_user, 'DEV', False))


def _current_feid() -> int:
    try:
        return int(get_current_feid() or 0)
    except MissingCurrentEntityError as exc:
        raise PhotoEnhancerError('Empresa ativa nao definida na sessao.') from exc


def _al_feid_filter(alias='AL') -> str:
    if column_exists('AL', 'FEID_GESTOR'):
        return f"AND (ISNULL({alias}.FEID, 0) = :current_feid OR ISNULL({alias}.FEID_GESTOR, 0) = :current_feid)"
    return f"AND ISNULL({alias}.FEID, 0) = :current_feid"


def _al_active_filter(alias='AL') -> str:
    clauses = []
    if column_exists('AL', 'INATIVO'):
        clauses.append(f"ISNULL({alias}.INATIVO, 0) = 0")
    return (' AND ' + ' AND '.join(clauses)) if clauses else ''


def _load_alojamento(alojamento_id: str, current_feid: int):
    where_feid = '' if _is_admin() else _al_feid_filter('AL')
    return db.session.execute(text(f"""
        SELECT TOP 1
            LTRIM(RTRIM(ISNULL(AL.ALSTAMP, ''))) AS ALSTAMP,
            LTRIM(RTRIM(ISNULL(AL.NOME, ''))) AS NOME,
            LTRIM(RTRIM(ISNULL(AL.CCUSTO, ''))) AS CCUSTO,
            LTRIM(RTRIM(ISNULL(AL.TIPOLOGIA, ''))) AS TIPOLOGIA,
            ISNULL(AL.FEID, 0) AS FEID
        FROM dbo.AL AS AL
        WHERE LTRIM(RTRIM(ISNULL(AL.ALSTAMP, ''))) = :alojamento_id
          {_al_active_filter('AL')}
          {where_feid}
    """), {
        'alojamento_id': _stamp(alojamento_id),
        'current_feid': current_feid,
    }).mappings().first()


def _session_payload(session_row):
    session_dict = row_to_session(session_row)
    if not session_dict:
        return None
    return {
        **session_dict,
        'files': list_session_files(session_dict['id']),
    }


def _session_summary(row) -> dict:
    data = dict(row)
    return {
        'id': _stamp(data.get('ID')),
        'status': str(data.get('STATUS') or '').strip(),
        'created_at': data.get('CREATED_AT').isoformat(timespec='seconds') if data.get('CREATED_AT') else '',
        'updated_at': data.get('UPDATED_AT').isoformat(timespec='seconds') if data.get('UPDATED_AT') else '',
        'files_count': int(data.get('FILES_COUNT') or 0),
        'enhanced_count': int(data.get('ENHANCED_COUNT') or 0),
        'errors_count': int(data.get('ERRORS_COUNT') or 0),
    }


def _assert_session_access(session_id: str):
    current_feid = _current_feid()
    session_row = get_session(session_id)
    if not session_row:
        raise PhotoEnhancerError('Sessao nao encontrada.')
    if not _is_admin() and int(session_row.get('FEID') or 0) != current_feid:
        raise PhotoEnhancerError('Sem permissao para esta sessao.')
    if not _is_admin() and not _load_alojamento(session_row.get('ALOJAMENTO_ID'), current_feid):
        raise PhotoEnhancerError('Sem permissao para este alojamento.')
    return session_row


def _assert_file_access(file_id: str):
    file_row = get_file(file_id)
    if not file_row:
        raise PhotoEnhancerError('Ficheiro nao encontrado.')
    session_row = _assert_session_access(file_row.get('SESSION_ID'))
    return file_row, session_row


@bp.route('/photo-enhancer')
@login_required
def photo_enhancer_page():
    try:
        ensure_photo_enhancer_schema()
    except Exception:
        db.session.rollback()
        current_app.logger.exception('Erro ao preparar tabelas do Photo Enhancer.')
    return render_template(
        'photo_enhancer.html',
        page_title='Sessões Fotográficas',
        max_upload_mb=photo_enhancer_max_bytes() // 1024 // 1024,
        prompt_used=PHOTO_ENHANCER_PROMPT,
    )


@bp.route('/api/photo-enhancer/alojamentos')
@login_required
def api_photo_enhancer_alojamentos():
    try:
        ensure_photo_enhancer_schema()
        current_feid = _current_feid()
        where_feid = '' if _is_admin() else _al_feid_filter('AL')
        rows = db.session.execute(text(f"""
            SELECT TOP 1000
                LTRIM(RTRIM(ISNULL(AL.ALSTAMP, ''))) AS id,
                LTRIM(RTRIM(ISNULL(AL.NOME, ''))) AS nome,
                LTRIM(RTRIM(ISNULL(AL.CCUSTO, ''))) AS ccusto,
                LTRIM(RTRIM(ISNULL(AL.TIPOLOGIA, ''))) AS tipologia
            FROM dbo.AL AS AL
            WHERE LTRIM(RTRIM(ISNULL(AL.ALSTAMP, ''))) <> ''
              AND LTRIM(RTRIM(ISNULL(AL.NOME, ''))) <> ''
              {_al_active_filter('AL')}
              {where_feid}
            ORDER BY LTRIM(RTRIM(ISNULL(AL.NOME, '')))
        """), {'current_feid': current_feid}).mappings().all()
        return jsonify({'ok': True, 'items': [dict(row) for row in rows]})
    except Exception as exc:
        db.session.rollback()
        return jsonify({'ok': False, 'error': str(exc)}), 500


@bp.route('/api/photo-enhancer/sessions', methods=['POST'])
@login_required
def api_photo_enhancer_create_session():
    try:
        ensure_photo_enhancer_schema()
        payload = request.get_json(silent=True) or {}
        alojamento_id = _stamp(payload.get('alojamento_id'))
        if not alojamento_id:
            return jsonify({'ok': False, 'error': 'Escolhe um alojamento.'}), 400
        current_feid = _current_feid()
        alojamento = _load_alojamento(alojamento_id, current_feid)
        if not alojamento:
            return jsonify({'ok': False, 'error': 'Alojamento nao encontrado ou sem permissao.'}), 403
        session_id = uuid.uuid4().hex.upper()[:25]
        db.session.execute(text("""
            INSERT INTO dbo.PHOTO_ENHANCER_SESSION (
                ID, FEID, ALOJAMENTO_ID, USER_ID, STATUS, CREATED_AT, UPDATED_AT
            )
            VALUES (
                :id, :feid, :alojamento_id, :user_id, 'ativa', SYSUTCDATETIME(), SYSUTCDATETIME()
            )
        """), {
            'id': session_id,
            'feid': current_feid,
            'alojamento_id': alojamento_id,
            'user_id': _stamp(getattr(current_user, 'USSTAMP', '') or getattr(current_user, 'LOGIN', '')),
        })
        db.session.commit()
        ensure_session_folders(current_feid, alojamento_id, session_id)
        return jsonify({'ok': True, 'session': _session_payload(get_session(session_id)), 'alojamento': dict(alojamento)})
    except Exception as exc:
        db.session.rollback()
        return jsonify({'ok': False, 'error': str(exc)}), 500


@bp.route('/api/photo-enhancer/sessions')
@login_required
def api_photo_enhancer_sessions():
    try:
        ensure_photo_enhancer_schema()
        alojamento_id = _stamp(request.args.get('alojamento_id'))
        if not alojamento_id:
            return jsonify({'ok': True, 'items': []})
        current_feid = _current_feid()
        if not _load_alojamento(alojamento_id, current_feid):
            return jsonify({'ok': False, 'error': 'Alojamento nao encontrado ou sem permissao.'}), 403
        rows = db.session.execute(text("""
            SELECT TOP 100
                S.ID,
                S.STATUS,
                S.CREATED_AT,
                S.UPDATED_AT,
                COUNT(F.ID) AS FILES_COUNT,
                SUM(CASE WHEN LTRIM(RTRIM(ISNULL(F.ENHANCED_PATH, ''))) <> '' THEN 1 ELSE 0 END) AS ENHANCED_COUNT,
                SUM(CASE WHEN ISNULL(F.STATUS, '') = 'erro' THEN 1 ELSE 0 END) AS ERRORS_COUNT
            FROM dbo.PHOTO_ENHANCER_SESSION AS S
            LEFT JOIN dbo.PHOTO_ENHANCER_FILE AS F
                ON F.SESSION_ID = S.ID
            WHERE S.ALOJAMENTO_ID = :alojamento_id
              AND (:is_admin = 1 OR S.FEID = :current_feid)
            GROUP BY S.ID, S.STATUS, S.CREATED_AT, S.UPDATED_AT
            ORDER BY ISNULL(S.UPDATED_AT, S.CREATED_AT) DESC, S.CREATED_AT DESC
        """), {
            'alojamento_id': alojamento_id,
            'current_feid': current_feid,
            'is_admin': 1 if _is_admin() else 0,
        }).mappings().all()
        return jsonify({'ok': True, 'items': [_session_summary(row) for row in rows]})
    except Exception as exc:
        db.session.rollback()
        return jsonify({'ok': False, 'error': str(exc)}), 500


@bp.route('/api/photo-enhancer/sessions/<session_id>')
@login_required
def api_photo_enhancer_session(session_id):
    try:
        ensure_photo_enhancer_schema()
        session_row = _assert_session_access(session_id)
        return jsonify({'ok': True, 'session': _session_payload(session_row)})
    except PhotoEnhancerError as exc:
        return jsonify({'ok': False, 'error': str(exc)}), 403
    except Exception as exc:
        db.session.rollback()
        return jsonify({'ok': False, 'error': str(exc)}), 500


@bp.route('/api/photo-enhancer/sessions/<session_id>/upload', methods=['POST'])
@login_required
def api_photo_enhancer_upload(session_id):
    try:
        ensure_photo_enhancer_schema()
        session_row = _assert_session_access(session_id)
        uploads = request.files.getlist('files')
        if not uploads:
            return jsonify({'ok': False, 'error': 'Seleciona pelo menos uma imagem.'}), 400
        created = []
        errors = []
        for file_storage in uploads:
            try:
                created.append(row_to_file(save_uploaded_file(file_storage, dict(session_row))))
            except Exception as exc:
                errors.append({'filename': str(getattr(file_storage, 'filename', '') or ''), 'error': str(exc)})
        db.session.execute(text("""
            UPDATE dbo.PHOTO_ENHANCER_SESSION
            SET UPDATED_AT = SYSUTCDATETIME()
            WHERE ID = :id
        """), {'id': _stamp(session_id)})
        db.session.commit()
        status = 201 if created else 400
        error_message = ''
        if not created and errors:
            first_error = errors[0]
            error_message = ': '.join(
                item for item in [
                    str(first_error.get('filename') or '').strip(),
                    str(first_error.get('error') or '').strip(),
                ] if item
            )
        return jsonify({
            'ok': bool(created),
            'error': error_message,
            'created': created,
            'errors': errors,
            'session': _session_payload(get_session(session_id)),
        }), status
    except PhotoEnhancerError as exc:
        db.session.rollback()
        return jsonify({'ok': False, 'error': str(exc)}), 403
    except Exception as exc:
        db.session.rollback()
        return jsonify({'ok': False, 'error': str(exc)}), 500


@bp.route('/api/photo-enhancer/files/<file_id>/enhance', methods=['POST'])
@login_required
def api_photo_enhancer_enhance(file_id):
    try:
        ensure_photo_enhancer_schema()
        file_row, session_row = _assert_file_access(file_id)
        file_dict = row_to_file(file_row)
        payload = request.get_json(silent=True) or {}
        custom_instructions = str(payload.get('custom_instructions') or '').strip()[:2000]

        db.session.execute(text("""
            UPDATE dbo.PHOTO_ENHANCER_FILE
            SET STATUS = 'em_processamento',
                ERROR_MESSAGE = NULL,
                UPDATED_AT = SYSUTCDATETIME()
            WHERE ID = :id
        """), {'id': _stamp(file_id)})
        db.session.commit()

        folders = ensure_session_folders(
            int(session_row.get('FEID') or 0),
            session_row.get('ALOJAMENTO_ID'),
            session_row.get('ID'),
        )
        enhanced_name = f"{_stamp(file_id)}_enhanced.jpg"
        enhanced_abs = os.path.join(folders['enhanced'], enhanced_name)
        result = enhance_photo(
            file_dict['original_path'],
            enhanced_abs,
            user_id=getattr(current_user, 'USSTAMP', '') or getattr(current_user, 'LOGIN', ''),
            custom_instructions=custom_instructions,
        )
        feid_part, aloj_part, session_part = (
            str(int(session_row.get('FEID') or 0)),
            secure_filename(str(session_row.get('ALOJAMENTO_ID') or '').strip())[:60],
            secure_filename(str(session_row.get('ID') or '').strip())[:60],
        )
        enhanced_path = f"/static/uploads/photo_enhancer/{feid_part}/{aloj_part}/{session_part}/enhanced/{enhanced_name}"
        db.session.execute(text("""
            UPDATE dbo.PHOTO_ENHANCER_FILE
            SET STATUS = 'melhorada',
                ENHANCED_PATH = :enhanced_path,
                PROCESSING_PROFILE = :profile,
                OPENAI_MODEL = :model,
                PROMPT_USED = :prompt,
                UPDATED_AT = SYSUTCDATETIME()
            WHERE ID = :id
        """), {
            'id': _stamp(file_id),
            'enhanced_path': enhanced_path,
            'profile': result.get('profile') or 'guestspa_premium',
            'model': result.get('model') or photo_enhancer_model(),
            'prompt': result.get('prompt') or PHOTO_ENHANCER_PROMPT,
        })
        db.session.execute(text("""
            UPDATE dbo.PHOTO_ENHANCER_SESSION
            SET UPDATED_AT = SYSUTCDATETIME()
            WHERE ID = :id
        """), {'id': _stamp(session_row.get('ID'))})
        db.session.commit()
        return jsonify({'ok': True, 'file': row_to_file(get_file(file_id))})
    except Exception as exc:
        db.session.rollback()
        try:
            db.session.execute(text("""
                UPDATE dbo.PHOTO_ENHANCER_FILE
                SET STATUS = 'erro',
                    ERROR_MESSAGE = :error,
                    UPDATED_AT = SYSUTCDATETIME()
                WHERE ID = :id
            """), {'id': _stamp(file_id), 'error': str(exc)[:4000]})
            db.session.commit()
        except Exception:
            db.session.rollback()
        status = 403 if isinstance(exc, PhotoEnhancerError) else 500
        return jsonify({'ok': False, 'error': str(exc), 'file': row_to_file(get_file(file_id)) if get_file(file_id) else None}), status


@bp.route('/api/photo-enhancer/files/<file_id>/metadata', methods=['PATCH'])
@login_required
def api_photo_enhancer_update_file_metadata(file_id):
    try:
        ensure_photo_enhancer_schema()
        file_row, session_row = _assert_file_access(file_id)
        payload = request.get_json(silent=True) or {}
        raw_tag = str(payload.get('tags') or '').strip()
        tags = next((part.strip() for part in re.split(r'[,;\r\n]+', raw_tag) if part.strip()), '')[:80]
        db.session.execute(text("""
            UPDATE dbo.PHOTO_ENHANCER_FILE
            SET TAGS = :tags,
                UPDATED_AT = SYSUTCDATETIME()
            WHERE ID = :id
        """), {'id': _stamp(file_id), 'tags': tags})
        db.session.execute(text("""
            UPDATE dbo.PHOTO_ENHANCER_SESSION
            SET UPDATED_AT = SYSUTCDATETIME()
            WHERE ID = :id
        """), {'id': _stamp(session_row.get('ID'))})
        db.session.commit()
        return jsonify({'ok': True, 'file': row_to_file(get_file(file_row.get('ID')))})
    except PhotoEnhancerError as exc:
        db.session.rollback()
        return jsonify({'ok': False, 'error': str(exc)}), 403
    except Exception as exc:
        db.session.rollback()
        return jsonify({'ok': False, 'error': str(exc)}), 500


@bp.route('/api/photo-enhancer/files/<file_id>/cover', methods=['POST'])
@login_required
def api_photo_enhancer_set_cover(file_id):
    try:
        ensure_photo_enhancer_schema()
        file_row, session_row = _assert_file_access(file_id)
        session_id = _stamp(session_row.get('ID'))
        db.session.execute(text("""
            UPDATE dbo.PHOTO_ENHANCER_FILE
            SET IS_COVER = 0,
                UPDATED_AT = SYSUTCDATETIME()
            WHERE SESSION_ID = :session_id
        """), {'session_id': session_id})
        db.session.execute(text("""
            UPDATE dbo.PHOTO_ENHANCER_FILE
            SET IS_COVER = 1,
                UPDATED_AT = SYSUTCDATETIME()
            WHERE ID = :id
        """), {'id': _stamp(file_row.get('ID'))})
        db.session.execute(text("""
            UPDATE dbo.PHOTO_ENHANCER_SESSION
            SET UPDATED_AT = SYSUTCDATETIME()
            WHERE ID = :id
        """), {'id': session_id})
        db.session.commit()
        return jsonify({'ok': True, 'session': _session_payload(get_session(session_id))})
    except PhotoEnhancerError as exc:
        db.session.rollback()
        return jsonify({'ok': False, 'error': str(exc)}), 403
    except Exception as exc:
        db.session.rollback()
        return jsonify({'ok': False, 'error': str(exc)}), 500


@bp.route('/api/photo-enhancer/files/<file_id>/download')
@login_required
def api_photo_enhancer_download(file_id):
    try:
        ensure_photo_enhancer_schema()
        file_row, _session_row = _assert_file_access(file_id)
        file_dict = row_to_file(file_row)
        if not file_dict.get('enhanced_path'):
            return jsonify({'ok': False, 'error': 'Imagem melhorada ainda nao existe.'}), 404
        full_path = public_to_abs(file_dict['enhanced_path'])
        original_base = secure_filename((file_dict.get('original_filename') or 'foto').rsplit('.', 1)[0]) or 'foto'
        download_name = f"{original_base}_melhorada.jpg"
        return send_file(full_path, as_attachment=True, download_name=download_name)
    except PhotoEnhancerError as exc:
        return jsonify({'ok': False, 'error': str(exc)}), 403
    except Exception as exc:
        db.session.rollback()
        return jsonify({'ok': False, 'error': str(exc)}), 500


@bp.route('/api/photo-enhancer/files/<file_id>', methods=['DELETE'])
@login_required
def api_photo_enhancer_delete_file(file_id):
    try:
        ensure_photo_enhancer_schema()
        file_row, session_row = _assert_file_access(file_id)
        file_dict = row_to_file(file_row)
        db.session.execute(text("""
            DELETE FROM dbo.PHOTO_ENHANCER_FILE
            WHERE ID = :id
        """), {'id': _stamp(file_id)})
        db.session.execute(text("""
            UPDATE dbo.PHOTO_ENHANCER_SESSION
            SET UPDATED_AT = SYSUTCDATETIME()
            WHERE ID = :id
        """), {'id': _stamp(session_row.get('ID'))})
        db.session.commit()
        remove_public_file(file_dict.get('original_path'))
        remove_public_file(file_dict.get('enhanced_path'))
        remove_public_file(file_dict.get('thumb_path'))
        return jsonify({'ok': True, 'session': _session_payload(get_session(session_row.get('ID')))})
    except PhotoEnhancerError as exc:
        db.session.rollback()
        return jsonify({'ok': False, 'error': str(exc)}), 403
    except Exception as exc:
        db.session.rollback()
        return jsonify({'ok': False, 'error': str(exc)}), 500


@bp.route('/api/photo-enhancer/sessions/<session_id>', methods=['DELETE'])
@login_required
def api_photo_enhancer_delete_session(session_id):
    try:
        ensure_photo_enhancer_schema()
        session_row = _assert_session_access(session_id)
        files = list_session_files(session_id)
        db.session.execute(text("""
            DELETE FROM dbo.PHOTO_ENHANCER_FILE
            WHERE SESSION_ID = :session_id
        """), {'session_id': _stamp(session_id)})
        db.session.execute(text("""
            DELETE FROM dbo.PHOTO_ENHANCER_SESSION
            WHERE ID = :session_id
        """), {'session_id': _stamp(session_id)})
        db.session.commit()
        for item in files:
            remove_public_file(item.get('original_path'))
            remove_public_file(item.get('enhanced_path'))
            remove_public_file(item.get('thumb_path'))
        remove_session_folder(dict(session_row))
        return jsonify({'ok': True})
    except PhotoEnhancerError as exc:
        db.session.rollback()
        return jsonify({'ok': False, 'error': str(exc)}), 403
    except Exception as exc:
        db.session.rollback()
        return jsonify({'ok': False, 'error': str(exc)}), 500


@bp.route('/api/photo-enhancer/sessions/<session_id>/zip')
@login_required
def api_photo_enhancer_zip(session_id):
    try:
        ensure_photo_enhancer_schema()
        session_row = _assert_session_access(session_id)
        files = list_session_files(session_id)
        zip_abs, zip_name = create_zip_for_session(dict(session_row), files)
        return send_file(zip_abs, as_attachment=True, download_name=zip_name)
    except PhotoEnhancerError as exc:
        return jsonify({'ok': False, 'error': str(exc)}), 400
    except Exception as exc:
        db.session.rollback()
        return jsonify({'ok': False, 'error': str(exc)}), 500
