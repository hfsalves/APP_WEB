import importlib.util
import io
import mimetypes
import os
from typing import Any


def _is_pdf(file_ext: str, mime_type: str) -> bool:
    ext = str(file_ext or '').lower()
    mime = str(mime_type or '').lower()
    return ext == '.pdf' or 'pdf' in mime


def _is_image(file_ext: str, mime_type: str) -> bool:
    ext = str(file_ext or '').lower()
    mime = str(mime_type or '').lower()
    return ext in {'.png', '.jpg', '.jpeg', '.tif', '.tiff', '.bmp', '.webp'} or mime.startswith('image/')


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def _split_lines(text_value: str) -> list[str]:
    return [line.strip() for line in str(text_value or '').splitlines() if str(line or '').strip()]


def _make_blocks_from_pages(pages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    blocks = []
    for page in pages:
        page_no = _safe_int(page.get('page'), 0) or 1
        for idx, line in enumerate(_split_lines(page.get('text') or ''), start=1):
            blocks.append({
                'id': f'p{page_no}-l{idx}',
                'page': page_no,
                'line_no': idx,
                'text': line,
            })
    return blocks


def extract_pdf_blocks_with_fitz(file_path: str) -> dict[str, Any] | None:
    if not importlib.util.find_spec('fitz'):
        return None
    try:
        import fitz  # type: ignore
    except Exception:
        return None

    pages = []
    blocks = []
    all_text = []
    with fitz.open(file_path) as pdf:
        for page_no, page in enumerate(pdf, start=1):
            rect = page.rect
            page_width = round(float(rect.width or 0), 2)
            page_height = round(float(rect.height or 0), 2)
            pages.append({'page': page_no, 'width': page_width, 'height': page_height})
            raw = page.get_text('dict') or {}
            page_lines = []
            line_no = 0
            for block in (raw.get('blocks') or []):
                if _safe_int(block.get('type'), 0) != 0:
                    continue
                for line in (block.get('lines') or []):
                    spans = line.get('spans') or []
                    text_value = ''.join(str(span.get('text') or '') for span in spans).strip()
                    if not text_value:
                        continue
                    line_no += 1
                    bbox = line.get('bbox') or block.get('bbox') or [0, 0, 0, 0]
                    try:
                        x0, y0, x1, y1 = [float(item or 0) for item in bbox[:4]]
                    except Exception:
                        x0 = y0 = x1 = y1 = 0.0
                    blocks.append({
                        'id': f'pdf-p{page_no}-l{line_no}',
                        'page': page_no,
                        'line_no': line_no,
                        'text': text_value,
                        'left': round(x0, 2),
                        'top': round(y0, 2),
                        'width': round(max(x1 - x0, 0.0), 2),
                        'height': round(max(y1 - y0, 0.0), 2),
                        'page_width': page_width,
                        'page_height': page_height,
                    })
                    page_lines.append(text_value)
            if page_lines:
                all_text.append('\n'.join(page_lines))
    return {
        'pages': pages,
        'blocks': blocks,
        'text': '\n'.join(chunk for chunk in all_text if chunk).strip(),
    }


def extract_pdf_direct_text(file_path: str) -> dict[str, Any]:
    warnings = []
    fitz_payload = extract_pdf_blocks_with_fitz(file_path)
    if fitz_payload and str(fitz_payload.get('text') or '').strip():
        return {
            'ok': True,
            'method': 'direct_pdf_text',
            'engine': 'fitz',
            'text': fitz_payload.get('text') or '',
            'blocks': fitz_payload.get('blocks') or [],
            'raw_json': {'pages': fitz_payload.get('pages') or []},
            'warnings': warnings,
            'source_kind': 'pdf',
        }

    if importlib.util.find_spec('pypdf'):
        try:
            from pypdf import PdfReader  # type: ignore

            reader = PdfReader(file_path)
            pages = []
            chunks = []
            for idx, page in enumerate(reader.pages, start=1):
                text_value = page.extract_text() or ''
                pages.append({'page': idx, 'text': text_value})
                if text_value.strip():
                    chunks.append(text_value)
            text_value = '\n'.join(chunks).strip()
            if text_value:
                return {
                    'ok': True,
                    'method': 'direct_pdf_text',
                    'engine': 'pypdf',
                    'text': text_value,
                    'blocks': _make_blocks_from_pages(pages),
                    'raw_json': {'pages': pages},
                    'warnings': warnings,
                    'source_kind': 'pdf',
                }
        except Exception as exc:
            warnings.append(f'Pypdf indisponível para extração direta: {exc}')

    return {
        'ok': False,
        'method': 'direct_pdf_text',
        'engine': None,
        'text': '',
        'blocks': [],
        'raw_json': {},
        'warnings': warnings,
        'source_kind': 'pdf',
    }


def load_image_source(file_path: str) -> dict[str, Any]:
    if not importlib.util.find_spec('PIL'):
        return {'ok': False, 'warnings': ['Pillow não está instalado.'], 'pages': []}
    try:
        from PIL import Image
    except Exception as exc:
        return {'ok': False, 'warnings': [f'Não foi possível abrir imagem: {exc}'], 'pages': []}

    try:
        image = Image.open(file_path).convert('RGB')
        return {
            'ok': True,
            'warnings': [],
            'pages': [{
                'page': 1,
                'image': image,
                'width': image.width,
                'height': image.height,
            }],
            'source_kind': 'image',
        }
    except Exception as exc:
        return {'ok': False, 'warnings': [f'Não foi possível ler imagem: {exc}'], 'pages': [], 'source_kind': 'image'}


def render_pdf_to_images(file_path: str, zoom: float = 2.5) -> dict[str, Any]:
    if not importlib.util.find_spec('fitz'):
        return {'ok': False, 'warnings': ['PyMuPDF/fitz não está instalado.'], 'pages': []}
    if not importlib.util.find_spec('PIL'):
        return {'ok': False, 'warnings': ['Pillow não está instalado.'], 'pages': []}
    try:
        import fitz  # type: ignore
        from PIL import Image
    except Exception as exc:
        return {'ok': False, 'warnings': [f'Conversão PDF->imagem indisponível: {exc}'], 'pages': []}

    warnings = []
    pages = []
    with fitz.open(file_path) as pdf:
        for page_no, page in enumerate(pdf, start=1):
            pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
            image = Image.open(io.BytesIO(pix.tobytes('png'))).convert('RGB')
            pages.append({
                'page': page_no,
                'image': image,
                'width': image.width,
                'height': image.height,
                'original_width': image.width,
                'original_height': image.height,
            })
    return {
        'ok': bool(pages),
        'warnings': warnings,
        'pages': pages,
        'source_kind': 'pdf',
    }


def build_plain_text_payload(file_path: str) -> dict[str, Any]:
    try:
        with open(file_path, 'r', encoding='utf-8') as handle:
            text_value = handle.read()
        lines = _split_lines(text_value)
        return {
            'ok': bool(text_value.strip()),
            'method': 'plain_text',
            'engine': 'plain_text',
            'text': text_value.strip(),
            'blocks': [{'id': f'txt-{idx + 1}', 'page': 1, 'line_no': idx + 1, 'text': line} for idx, line in enumerate(lines)],
            'raw_json': {},
            'warnings': [],
            'source_kind': 'text',
        }
    except Exception:
        mime = mimetypes.guess_type(file_path)[0] or 'application/octet-stream'
        return {
            'ok': False,
            'method': 'plain_text',
            'engine': None,
            'text': '',
            'blocks': [],
            'raw_json': {'mime_type': mime},
            'warnings': ['Tipo de ficheiro ainda não suportado para extração direta.'],
            'source_kind': 'unknown',
        }


def detect_source_kind(file_ext: str, mime_type: str) -> str:
    if _is_pdf(file_ext, mime_type):
        return 'pdf'
    if _is_image(file_ext, mime_type):
        return 'image'
    return 'text'
