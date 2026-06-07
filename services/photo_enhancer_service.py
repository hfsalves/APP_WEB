import base64
import io
import json
import os
import re
import shutil
import time
import uuid
import zipfile
from datetime import datetime
from decimal import Decimal
from typing import Any
from urllib import error as urllib_error
from urllib import request as urllib_request

from flask import current_app
from PIL import Image, ImageOps
from sqlalchemy import text
from werkzeug.utils import secure_filename

from models import db


PHOTO_ENHANCER_ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp'}
PHOTO_ENHANCER_DEFAULT_PROFILE = 'guestspa_premium'

PHOTO_ENHANCER_PROFILES = {
    'standard': {
        'label': 'Standard',
        'prompt': (
            "You are a professional real estate photo editor. Improve this image subtly "
            "for a short-term rental listing while preserving the property exactly as it is."
        ),
    },
    'airbnb': {
        'label': 'Airbnb',
        'prompt': (
            "You are a professional Airbnb photographer. Enhance this image for a high-performing "
            "Airbnb listing while preserving the property exactly as it is."
        ),
    },
    'booking': {
        'label': 'Booking',
        'prompt': (
            "You are a professional hospitality photographer. Enhance this image for a Booking.com "
            "listing while preserving the property exactly as it is."
        ),
    },
    'luxury': {
        'label': 'Luxury',
        'prompt': (
            "You are a luxury real estate photographer. Enhance this image for a premium hospitality "
            "listing while preserving the property exactly as it is."
        ),
    },
    'guestspa_premium': {
        'label': 'GuestSpa Premium',
        'prompt': """You are a world-class Airbnb, hospitality and luxury real estate photographer.

Enhance this image as if it had been photographed and edited by a professional Airbnb photographer.

Preserve exactly the same room, architecture, furniture, decoration, windows, doors, walls, flooring, bedding, curtains, lighting fixtures and objects.

Do not add any object.
Do not remove any object.
Do not replace any object.
Do not invent decor.
Do not modify the room layout.
Do not modify dimensions or proportions.

Enhance:

- brightness
- exposure
- dynamic range
- white balance
- color accuracy
- local contrast
- shadow detail
- highlight recovery
- texture detail
- sharpness
- room depth
- perceived spaciousness
- natural daylight

Correct:

- perspective distortion
- vertical lines
- lens distortion

Create a warm, inviting, premium hospitality atmosphere suitable for Airbnb and Booking.com listings.

The image must look natural, realistic and trustworthy.

Avoid:
- fake HDR
- over-saturation
- artificial colors
- unrealistic lighting
- CGI appearance
- generated-image appearance

The final result should look like a high-end professional real estate photograph while remaining 100% faithful to the actual property.""",
    },
}

PHOTO_ENHANCER_PROMPT = PHOTO_ENHANCER_PROFILES[PHOTO_ENHANCER_DEFAULT_PROFILE]['prompt']


class PhotoEnhancerError(Exception):
    pass


def _stamp() -> str:
    return uuid.uuid4().hex.upper()[:25]


def _now() -> datetime:
    return datetime.utcnow()


def _para_value(code: str, default: str = '') -> str:
    key = str(code or '').strip()
    if not key:
        return default
    try:
        para_map = current_app.config.get('PARA_VALUES') or {}
        value = para_map.get(key)
        if value in (None, ''):
            value = para_map.get(key.upper())
        if value not in (None, ''):
            return str(value).strip()
    except Exception:
        pass
    try:
        row = db.session.execute(text("""
            SELECT TOP 1 PARAMETRO, TIPO, CVALOR, DVALOR, NVALOR, LVALOR
            FROM dbo.PARA
            WHERE UPPER(LTRIM(RTRIM(PARAMETRO))) = UPPER(LTRIM(RTRIM(:code)))
        """), {'code': key}).mappings().first()
        if not row:
            return default
        tipo = str(row.get('TIPO') or '').strip().upper()
        if tipo == 'N':
            return str(row.get('NVALOR') or '')
        if tipo == 'D':
            return str(row.get('DVALOR') or '')
        if tipo == 'L':
            return '1' if bool(row.get('LVALOR') or 0) else '0'
        return str(row.get('CVALOR') or '').strip() or default
    except Exception:
        return default


def photo_enhancer_api_key() -> str:
    return (
        _para_value('PHOTO_ENHANCER_OPENAI_API_KEY')
        or _para_value('SHOP_TRANSLATE_OPENAI_API_KEY')
        or _para_value('OPENAI_API_KEY')
        or os.getenv('PHOTO_ENHANCER_OPENAI_API_KEY')
        or os.getenv('SHOP_TRANSLATE_OPENAI_API_KEY')
        or os.getenv('OPENAI_API_KEY')
        or ''
    ).strip()


def photo_enhancer_model() -> str:
    return (
        _para_value('PHOTO_ENHANCER_OPENAI_MODEL')
        or _para_value('OPENAI_IMAGE_MODEL')
        or os.getenv('PHOTO_ENHANCER_OPENAI_MODEL')
        or os.getenv('OPENAI_IMAGE_MODEL')
        or 'gpt-image-1.5'
    ).strip()


def photo_enhancer_max_bytes() -> int:
    raw = (
        _para_value('PHOTO_ENHANCER_MAX_MB')
        or os.getenv('PHOTO_ENHANCER_MAX_MB')
        or '50'
    )
    try:
        mb = max(1, min(50, int(float(str(raw).replace(',', '.')))))
    except Exception:
        mb = 50
    return mb * 1024 * 1024


def photo_enhancer_timeout() -> int:
    raw = (
        _para_value('PHOTO_ENHANCER_OPENAI_TIMEOUT')
        or os.getenv('PHOTO_ENHANCER_OPENAI_TIMEOUT')
        or '300'
    )
    try:
        return max(60, min(900, int(float(str(raw).replace(',', '.')))))
    except Exception:
        return 300


def photo_enhancer_max_side() -> int:
    raw = (
        _para_value('PHOTO_ENHANCER_MAX_SIDE')
        or os.getenv('PHOTO_ENHANCER_MAX_SIDE')
        or '2048'
    )
    try:
        return max(1024, min(4096, int(float(str(raw).replace(',', '.')))))
    except Exception:
        return 2048


def photo_enhancer_retries() -> int:
    raw = (
        _para_value('PHOTO_ENHANCER_OPENAI_RETRIES')
        or os.getenv('PHOTO_ENHANCER_OPENAI_RETRIES')
        or '2'
    )
    try:
        return max(0, min(4, int(float(str(raw).replace(',', '.')))))
    except Exception:
        return 2


def normalize_photo_enhancer_profile(profile: str | None = None) -> str:
    key = _clean_text(profile or '', 40).lower()
    if key in PHOTO_ENHANCER_PROFILES:
        return key
    configured = (
        _para_value('PHOTO_ENHANCER_DEFAULT_PROFILE')
        or os.getenv('PHOTO_ENHANCER_DEFAULT_PROFILE')
        or PHOTO_ENHANCER_DEFAULT_PROFILE
    )
    key = _clean_text(configured, 40).lower()
    return key if key in PHOTO_ENHANCER_PROFILES else PHOTO_ENHANCER_DEFAULT_PROFILE


def photo_enhancer_prompt_for_profile(profile: str | None = None) -> tuple[str, str]:
    key = normalize_photo_enhancer_profile(profile)
    return key, PHOTO_ENHANCER_PROFILES[key]['prompt']


def ensure_photo_enhancer_schema() -> None:
    db.session.execute(text("""
        IF OBJECT_ID('dbo.PHOTO_ENHANCER_SESSION', 'U') IS NULL
        BEGIN
            CREATE TABLE dbo.PHOTO_ENHANCER_SESSION (
                ID varchar(25) NOT NULL CONSTRAINT PK_PHOTO_ENHANCER_SESSION PRIMARY KEY,
                FEID int NOT NULL CONSTRAINT DF_PHOTO_ENHANCER_SESSION_FEID DEFAULT 0,
                ALOJAMENTO_ID varchar(25) NOT NULL CONSTRAINT DF_PHOTO_ENHANCER_SESSION_ALOJAMENTO DEFAULT '',
                USER_ID varchar(25) NOT NULL CONSTRAINT DF_PHOTO_ENHANCER_SESSION_USER DEFAULT '',
                STATUS varchar(30) NOT NULL CONSTRAINT DF_PHOTO_ENHANCER_SESSION_STATUS DEFAULT 'ativa',
                CREATED_AT datetime2(0) NOT NULL CONSTRAINT DF_PHOTO_ENHANCER_SESSION_CREATED DEFAULT SYSDATETIME(),
                UPDATED_AT datetime2(0) NULL
            )
        END

        IF OBJECT_ID('dbo.PHOTO_ENHANCER_FILE', 'U') IS NULL
        BEGIN
            CREATE TABLE dbo.PHOTO_ENHANCER_FILE (
                ID varchar(25) NOT NULL CONSTRAINT PK_PHOTO_ENHANCER_FILE PRIMARY KEY,
                SESSION_ID varchar(25) NOT NULL,
                ORIGINAL_FILENAME nvarchar(255) NOT NULL CONSTRAINT DF_PHOTO_ENHANCER_FILE_ORIGNAME DEFAULT '',
                ORIGINAL_PATH varchar(500) NOT NULL CONSTRAINT DF_PHOTO_ENHANCER_FILE_ORIGPATH DEFAULT '',
                ENHANCED_PATH varchar(500) NOT NULL CONSTRAINT DF_PHOTO_ENHANCER_FILE_ENHPATH DEFAULT '',
                THUMB_PATH varchar(500) NOT NULL CONSTRAINT DF_PHOTO_ENHANCER_FILE_THUMBPATH DEFAULT '',
                STATUS varchar(30) NOT NULL CONSTRAINT DF_PHOTO_ENHANCER_FILE_STATUS DEFAULT 'carregada',
                ERROR_MESSAGE nvarchar(max) NULL,
                PROCESSING_PROFILE varchar(40) NOT NULL CONSTRAINT DF_PHOTO_ENHANCER_FILE_PROFILE DEFAULT 'guestspa_premium',
                OPENAI_MODEL varchar(80) NOT NULL CONSTRAINT DF_PHOTO_ENHANCER_FILE_MODEL DEFAULT '',
                PROMPT_USED nvarchar(max) NULL,
                COST_ESTIMATED decimal(18, 6) NULL,
                CREATED_AT datetime2(0) NOT NULL CONSTRAINT DF_PHOTO_ENHANCER_FILE_CREATED DEFAULT SYSDATETIME(),
                UPDATED_AT datetime2(0) NULL,
                CONSTRAINT FK_PHOTO_ENHANCER_FILE_SESSION FOREIGN KEY (SESSION_ID)
                    REFERENCES dbo.PHOTO_ENHANCER_SESSION (ID)
            )
        END

        IF NOT EXISTS (
            SELECT 1 FROM sys.indexes
            WHERE name = 'IX_PHOTO_ENHANCER_SESSION_FEID_AL'
              AND object_id = OBJECT_ID('dbo.PHOTO_ENHANCER_SESSION')
        )
            CREATE INDEX IX_PHOTO_ENHANCER_SESSION_FEID_AL
            ON dbo.PHOTO_ENHANCER_SESSION (FEID, ALOJAMENTO_ID, CREATED_AT DESC)

        IF NOT EXISTS (
            SELECT 1 FROM sys.indexes
            WHERE name = 'IX_PHOTO_ENHANCER_FILE_SESSION'
              AND object_id = OBJECT_ID('dbo.PHOTO_ENHANCER_FILE')
        )
            CREATE INDEX IX_PHOTO_ENHANCER_FILE_SESSION
            ON dbo.PHOTO_ENHANCER_FILE (SESSION_ID, CREATED_AT)

        IF COL_LENGTH('dbo.PHOTO_ENHANCER_FILE', 'PROCESSING_PROFILE') IS NULL
            ALTER TABLE dbo.PHOTO_ENHANCER_FILE
            ADD PROCESSING_PROFILE varchar(40) NOT NULL
                CONSTRAINT DF_PHOTO_ENHANCER_FILE_PROFILE_LATE DEFAULT 'guestspa_premium'
    """))
    db.session.commit()


def column_exists(table_name: str, column_name: str) -> bool:
    try:
        return bool(db.session.execute(
            text("SELECT CASE WHEN COL_LENGTH(:table_name, :column_name) IS NULL THEN 0 ELSE 1 END"),
            {'table_name': f'dbo.{table_name}', 'column_name': column_name},
        ).scalar())
    except Exception:
        return False


def _clean_text(value: Any, max_len: int | None = None) -> str:
    out = str(value or '').strip()
    return out[:max_len] if max_len else out


def _json_datetime(value: Any) -> str:
    if isinstance(value, datetime):
        return value.isoformat(timespec='seconds')
    return str(value or '')


def _json_decimal(value: Any) -> float | None:
    if value in (None, ''):
        return None
    try:
        return float(Decimal(str(value)))
    except Exception:
        return None


def _public_path(*parts: str) -> str:
    safe_parts = [str(part or '').strip('/\\') for part in parts if str(part or '').strip('/\\')]
    return '/' + '/'.join(['static', 'uploads', 'photo_enhancer', *safe_parts]).replace('\\', '/')


def public_to_abs(path_value: str) -> str:
    public_path = str(path_value or '').strip()
    if not public_path.startswith('/static/uploads/photo_enhancer/'):
        raise PhotoEnhancerError('Caminho de ficheiro invalido.')
    rel = public_path.lstrip('/').replace('/', os.sep)
    full_path = os.path.abspath(os.path.join(current_app.root_path, rel))
    root = os.path.abspath(os.path.join(current_app.static_folder, 'uploads', 'photo_enhancer'))
    if not (full_path == root or full_path.startswith(root + os.sep)):
        raise PhotoEnhancerError('Caminho de ficheiro fora da pasta permitida.')
    return full_path


def remove_public_file(path_value: str) -> None:
    public_path = str(path_value or '').strip()
    if not public_path:
        return
    try:
        full_path = public_to_abs(public_path)
        if os.path.isfile(full_path):
            os.remove(full_path)
    except Exception:
        pass


def remove_session_folder(session_row: dict[str, Any]) -> None:
    try:
        feid_part, aloj_part, session_part = session_folder_parts(
            int(session_row.get('FEID') or 0),
            _clean_text(session_row.get('ALOJAMENTO_ID'), 25),
            _clean_text(session_row.get('ID'), 25),
        )
        root = os.path.abspath(os.path.join(current_app.static_folder, 'uploads', 'photo_enhancer'))
        folder = os.path.abspath(os.path.join(root, feid_part, aloj_part, session_part))
        if folder.startswith(root + os.sep) and os.path.isdir(folder):
            shutil.rmtree(folder, ignore_errors=True)
    except Exception:
        pass


def session_folder_parts(feid: int, alojamento_id: str, session_id: str) -> tuple[str, str, str]:
    return str(int(feid or 0)), secure_filename(str(alojamento_id or '').strip())[:60], secure_filename(str(session_id or '').strip())[:60]


def ensure_session_folders(feid: int, alojamento_id: str, session_id: str) -> dict[str, str]:
    feid_part, aloj_part, session_part = session_folder_parts(feid, alojamento_id, session_id)
    base = os.path.join(current_app.static_folder, 'uploads', 'photo_enhancer', feid_part, aloj_part, session_part)
    folders = {
        'base': base,
        'originals': os.path.join(base, 'originals'),
        'enhanced': os.path.join(base, 'enhanced'),
        'thumbs': os.path.join(base, 'thumbs'),
        'zips': os.path.join(base, 'zips'),
    }
    for path in folders.values():
        os.makedirs(path, exist_ok=True)
    return folders


def validate_upload(file_storage) -> tuple[str, str]:
    original_name = secure_filename(str(file_storage.filename or '').strip())
    if not original_name or '.' not in original_name:
        raise PhotoEnhancerError('Ficheiro sem nome ou extensao valida.')
    _, ext = os.path.splitext(original_name)
    ext = ext.lower()
    if ext not in PHOTO_ENHANCER_ALLOWED_EXTENSIONS:
        raise PhotoEnhancerError('Apenas sao aceites imagens jpg, jpeg, png e webp.')
    return original_name, ext


def make_thumbnail(original_abs: str, thumb_abs: str) -> None:
    with Image.open(original_abs) as image:
        image = ImageOps.exif_transpose(image)
        if image.mode not in ('RGB', 'L'):
            image = image.convert('RGB')
        image.thumbnail((640, 640), Image.Resampling.LANCZOS)
        image.save(thumb_abs, format='JPEG', quality=82, optimize=True)


def save_uploaded_file(file_storage, session_row: dict[str, Any]) -> dict[str, Any]:
    original_name, ext = validate_upload(file_storage)
    file_id = _stamp()
    feid = int(session_row.get('FEID') or 0)
    alojamento_id = _clean_text(session_row.get('ALOJAMENTO_ID'), 25)
    session_id = _clean_text(session_row.get('ID'), 25)
    folders = ensure_session_folders(feid, alojamento_id, session_id)
    stored_original = f'{file_id}{ext}'
    original_abs = os.path.join(folders['originals'], stored_original)
    file_storage.save(original_abs)
    size = os.path.getsize(original_abs)
    if size <= 0:
        try:
            os.remove(original_abs)
        except Exception:
            pass
        raise PhotoEnhancerError('O ficheiro esta vazio.')
    if size > photo_enhancer_max_bytes():
        try:
            os.remove(original_abs)
        except Exception:
            pass
        raise PhotoEnhancerError(f'O ficheiro excede o limite de {photo_enhancer_max_bytes() // 1024 // 1024} MB.')

    thumb_name = f'{file_id}.jpg'
    thumb_abs = os.path.join(folders['thumbs'], thumb_name)
    try:
        make_thumbnail(original_abs, thumb_abs)
    except Exception as exc:
        try:
            os.remove(original_abs)
        except Exception:
            pass
        raise PhotoEnhancerError(f'Nao foi possivel gerar thumbnail: {exc}') from exc

    feid_part, aloj_part, session_part = session_folder_parts(feid, alojamento_id, session_id)
    original_path = _public_path(feid_part, aloj_part, session_part, 'originals', stored_original)
    thumb_path = _public_path(feid_part, aloj_part, session_part, 'thumbs', thumb_name)
    db.session.execute(text("""
        INSERT INTO dbo.PHOTO_ENHANCER_FILE (
            ID, SESSION_ID, ORIGINAL_FILENAME, ORIGINAL_PATH, THUMB_PATH, STATUS, CREATED_AT, UPDATED_AT
        )
        VALUES (
            :id, :session_id, :filename, :original_path, :thumb_path, 'carregada', :now, :now
        )
    """), {
        'id': file_id,
        'session_id': session_id,
        'filename': original_name[:255],
        'original_path': original_path,
        'thumb_path': thumb_path,
        'now': _now(),
    })
    return get_file(file_id)


def _multipart_body(fields: dict[str, str], files: list[tuple[str, str, bytes, str]]) -> tuple[bytes, str]:
    boundary = f'----StationZeroPhotoEnhancer{uuid.uuid4().hex}'
    body = bytearray()
    for name, value in fields.items():
        body.extend(f'--{boundary}\r\n'.encode('utf-8'))
        body.extend(f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode('utf-8'))
        body.extend(str(value).encode('utf-8'))
        body.extend(b'\r\n')
    for field_name, filename, data, content_type in files:
        safe_name = secure_filename(filename) or 'image.jpg'
        body.extend(f'--{boundary}\r\n'.encode('utf-8'))
        body.extend(
            f'Content-Disposition: form-data; name="{field_name}"; filename="{safe_name}"\r\n'.encode('utf-8')
        )
        body.extend(f'Content-Type: {content_type or "application/octet-stream"}\r\n\r\n'.encode('utf-8'))
        body.extend(data)
        body.extend(b'\r\n')
    body.extend(f'--{boundary}--\r\n'.encode('utf-8'))
    return bytes(body), boundary


def _prepare_openai_image(original_abs: str) -> tuple[str, bytes, str, tuple[int, int]]:
    try:
        with Image.open(original_abs) as image:
            image = ImageOps.exif_transpose(image)
            if image.mode in ('RGBA', 'LA') or ('transparency' in image.info):
                rgba = image.convert('RGBA')
                background = Image.new('RGBA', rgba.size, (255, 255, 255, 255))
                background.alpha_composite(rgba)
                image = background.convert('RGB')
            elif image.mode != 'RGB':
                image = image.convert('RGB')

            original_size = image.size
            max_side = photo_enhancer_max_side()
            if max(image.size) > max_side:
                image.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)

            output = io.BytesIO()
            image.save(output, format='JPEG', quality=90, optimize=True)
            image_bytes = output.getvalue()
            if len(image_bytes) > photo_enhancer_max_bytes():
                output = io.BytesIO()
                image.save(output, format='JPEG', quality=84, optimize=True)
                image_bytes = output.getvalue()
            return 'input.jpg', image_bytes, 'image/jpeg', original_size
    except Exception as exc:
        raise PhotoEnhancerError(f'Nao foi possivel preparar a imagem para a OpenAI: {exc}') from exc


def _openai_size_for_aspect(size: tuple[int, int]) -> str:
    width, height = size
    if width <= 0 or height <= 0:
        return 'auto'
    ratio = width / height
    if ratio >= 1.12:
        return '1536x1024'
    if ratio <= 0.89:
        return '1024x1536'
    return '1024x1024'


def _fit_enhanced_to_original_aspect(enhanced_abs: str, original_size: tuple[int, int]) -> None:
    original_width, original_height = original_size
    if original_width <= 0 or original_height <= 0 or not os.path.isfile(enhanced_abs):
        return
    target_ratio = original_width / original_height
    with Image.open(enhanced_abs) as image:
        image = ImageOps.exif_transpose(image).convert('RGB')
        width, height = image.size
        current_ratio = width / height if height else target_ratio
        if abs(current_ratio - target_ratio) > 0.002:
            if current_ratio > target_ratio:
                new_width = max(1, int(round(height * target_ratio)))
                left = max(0, (width - new_width) // 2)
                image = image.crop((left, 0, left + new_width, height))
            else:
                new_height = max(1, int(round(width / target_ratio)))
                top = max(0, (height - new_height) // 2)
                image = image.crop((0, top, width, top + new_height))
        if image.size != original_size:
            image = image.resize(original_size, Image.Resampling.LANCZOS)
        image.save(enhanced_abs, format='JPEG', quality=94, optimize=True)


def _is_transient_openai_error(status_code: int | None, details: str = '') -> bool:
    text_value = str(details or '').lower()
    return (
        (status_code is not None and status_code >= 500)
        or 'timeout' in text_value
        or 'timed out' in text_value
        or 'upstream connect error' in text_value
        or 'disconnect/reset before headers' in text_value
        or 'connection reset' in text_value
    )


def _friendly_openai_error(details: str) -> str:
    text_value = str(details or '').strip()
    lowered = text_value.lower()
    if (
        'timeout' in lowered
        or 'upstream connect error' in lowered
        or 'disconnect/reset before headers' in lowered
        or 'connection reset' in lowered
    ):
        return 'A ligacao a OpenAI expirou ou foi interrompida. Tenta novamente daqui a pouco.'
    return f'Falha na OpenAI: {text_value[:500]}'


def enhance_photo(original_path: str, enhanced_abs: str, user_id: str = '', profile: str | None = None) -> dict[str, Any]:
    api_key = photo_enhancer_api_key()
    if not api_key:
        raise PhotoEnhancerError('Integração OpenAI indisponível. Configura SHOP_TRANSLATE_OPENAI_API_KEY na tabela PARA.')

    original_abs = public_to_abs(original_path) if original_path.startswith('/static/') else os.path.abspath(original_path)
    if not os.path.isfile(original_abs):
        raise PhotoEnhancerError('Imagem original nao encontrada.')

    filename, image_bytes, mime_type, original_size = _prepare_openai_image(original_abs)

    model = photo_enhancer_model()
    profile_key, prompt = photo_enhancer_prompt_for_profile(profile)
    fields = {
        'model': model,
        'prompt': prompt,
        'n': '1',
        'size': _openai_size_for_aspect(original_size),
        'quality': 'medium',
        'output_format': 'jpeg',
    }
    if user_id:
        fields['user'] = _clean_text(user_id, 64)
    body, boundary = _multipart_body(
        fields,
        [('image', filename, image_bytes, mime_type)],
    )
    req = urllib_request.Request(
        'https://api.openai.com/v1/images/edits',
        data=body,
        headers={
            'Authorization': f'Bearer {api_key}',
            'Content-Type': f'multipart/form-data; boundary={boundary}',
        },
        method='POST',
    )
    payload = None
    last_error: Exception | None = None
    attempts = photo_enhancer_retries() + 1
    for attempt in range(attempts):
        try:
            with urllib_request.urlopen(req, timeout=photo_enhancer_timeout()) as response:
                payload = json.loads(response.read().decode('utf-8'))
            break
        except urllib_error.HTTPError as exc:
            details = ''
            try:
                details = exc.read().decode('utf-8')
            except Exception:
                details = str(exc)
            last_error = exc
            if attempt + 1 < attempts and _is_transient_openai_error(getattr(exc, 'code', None), details):
                time.sleep(1.5 * (attempt + 1))
                continue
            raise PhotoEnhancerError(_friendly_openai_error(details)) from exc
        except Exception as exc:
            last_error = exc
            details = str(exc)
            if attempt + 1 < attempts and _is_transient_openai_error(None, details):
                time.sleep(1.5 * (attempt + 1))
                continue
            raise PhotoEnhancerError(_friendly_openai_error(details)) from exc
    if payload is None:
        raise PhotoEnhancerError(_friendly_openai_error(str(last_error or 'sem resposta')))

    data = payload.get('data') or []
    if not data or not data[0].get('b64_json'):
        raise PhotoEnhancerError('A OpenAI nao devolveu imagem utilizavel.')
    os.makedirs(os.path.dirname(enhanced_abs), exist_ok=True)
    with open(enhanced_abs, 'wb') as handle:
        handle.write(base64.b64decode(data[0]['b64_json']))
    _fit_enhanced_to_original_aspect(enhanced_abs, original_size)
    return {
        'model': model,
        'prompt': prompt,
        'profile': profile_key,
        'usage': payload.get('usage') or data[0].get('usage') or None,
    }


def row_to_session(row) -> dict[str, Any] | None:
    if not row:
        return None
    data = dict(row)
    return {
        'id': _clean_text(data.get('ID'), 25),
        'feid': int(data.get('FEID') or 0),
        'alojamento_id': _clean_text(data.get('ALOJAMENTO_ID'), 25),
        'user_id': _clean_text(data.get('USER_ID'), 25),
        'status': _clean_text(data.get('STATUS'), 30),
        'created_at': _json_datetime(data.get('CREATED_AT')),
        'updated_at': _json_datetime(data.get('UPDATED_AT')),
    }


def row_to_file(row) -> dict[str, Any]:
    data = dict(row)
    return {
        'id': _clean_text(data.get('ID'), 25),
        'session_id': _clean_text(data.get('SESSION_ID'), 25),
        'original_filename': _clean_text(data.get('ORIGINAL_FILENAME')),
        'original_path': _clean_text(data.get('ORIGINAL_PATH')),
        'enhanced_path': _clean_text(data.get('ENHANCED_PATH')),
        'thumb_path': _clean_text(data.get('THUMB_PATH')),
        'status': _clean_text(data.get('STATUS'), 30),
        'error_message': _clean_text(data.get('ERROR_MESSAGE')),
        'processing_profile': _clean_text(data.get('PROCESSING_PROFILE'), 40) or PHOTO_ENHANCER_DEFAULT_PROFILE,
        'openai_model': _clean_text(data.get('OPENAI_MODEL'), 80),
        'cost_estimated': _json_decimal(data.get('COST_ESTIMATED')),
        'created_at': _json_datetime(data.get('CREATED_AT')),
        'updated_at': _json_datetime(data.get('UPDATED_AT')),
    }


def get_session(session_id: str):
    return db.session.execute(text("""
        SELECT TOP 1 *
        FROM dbo.PHOTO_ENHANCER_SESSION
        WHERE ID = :id
    """), {'id': _clean_text(session_id, 25)}).mappings().first()


def get_file(file_id: str):
    return db.session.execute(text("""
        SELECT TOP 1 *
        FROM dbo.PHOTO_ENHANCER_FILE
        WHERE ID = :id
    """), {'id': _clean_text(file_id, 25)}).mappings().first()


def list_session_files(session_id: str) -> list[dict[str, Any]]:
    rows = db.session.execute(text("""
        SELECT *
        FROM dbo.PHOTO_ENHANCER_FILE
        WHERE SESSION_ID = :session_id
        ORDER BY CREATED_AT, ID
    """), {'session_id': _clean_text(session_id, 25)}).mappings().all()
    return [row_to_file(row) for row in rows]


def create_zip_for_session(session_row: dict[str, Any], files: list[dict[str, Any]]) -> tuple[str, str]:
    enhanced_files = [item for item in files if item.get('enhanced_path')]
    if not enhanced_files:
        raise PhotoEnhancerError('Ainda nao existem imagens melhoradas para descarregar.')
    folders = ensure_session_folders(
        int(session_row.get('FEID') or 0),
        _clean_text(session_row.get('ALOJAMENTO_ID'), 25),
        _clean_text(session_row.get('ID'), 25),
    )
    zip_name = f"photo_enhancer_{_clean_text(session_row.get('ID'), 25)}.zip"
    zip_abs = os.path.join(folders['zips'], zip_name)
    with zipfile.ZipFile(zip_abs, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for idx, item in enumerate(enhanced_files, start=1):
            enhanced_abs = public_to_abs(item.get('enhanced_path') or '')
            if not os.path.isfile(enhanced_abs):
                continue
            base_name = os.path.splitext(secure_filename(item.get('original_filename') or f'foto_{idx}'))[0]
            arc_name = re.sub(r'_+', '_', f'{idx:02d}_{base_name}_melhorada.jpg')
            archive.write(enhanced_abs, arc_name)
    return zip_abs, zip_name
