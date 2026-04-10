import importlib.util
from typing import Any


def ocr_engine_available() -> bool:
    return bool(
        importlib.util.find_spec('pytesseract')
        and importlib.util.find_spec('PIL')
    )


def _ocr_image_object(image, page_number: int = 1, page_label: str = '') -> dict[str, Any]:
    try:
        import pytesseract
    except Exception as exc:
        return {
            'ok': False,
            'engine': None,
            'text': '',
            'blocks': [],
            'raw_json': {},
            'warnings': [f'Não foi possível inicializar OCR: {exc}'],
        }

    try:
        image_width, image_height = image.size
        raw = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
        blocks = []
        lines = []
        total = len(raw.get('text', []) or [])
        for idx in range(total):
            chunk = str((raw.get('text') or [''])[idx] or '').strip()
            if not chunk:
                continue
            line_no = int(((raw.get('line_num') or [0])[idx] or 0))
            block = {
                'id': f'ocr-{page_number}-{idx + 1}',
                'page': page_number,
                'line_no': line_no or idx + 1,
                'text': chunk,
                'left': int(((raw.get('left') or [0])[idx] or 0)),
                'top': int(((raw.get('top') or [0])[idx] or 0)),
                'width': int(((raw.get('width') or [0])[idx] or 0)),
                'height': int(((raw.get('height') or [0])[idx] or 0)),
                'page_width': int(image_width or 0),
                'page_height': int(image_height or 0),
            }
            blocks.append(block)
            lines.append(chunk)
        return {
            'ok': True,
            'engine': 'pytesseract',
            'text': '\n'.join(lines).strip(),
            'blocks': blocks,
            'raw_json': {'page_label': page_label, 'ocr': raw},
            'warnings': [],
        }
    except Exception as exc:
        return {
            'ok': False,
            'engine': 'pytesseract',
            'text': '',
            'blocks': [],
            'raw_json': {},
            'warnings': [f'Falha no OCR: {exc}'],
        }


def extract_image_text(image_path: str) -> dict[str, Any]:
    """
    OCR simples para imagens.

    Esta função fica isolada para permitir substituir o motor OCR no futuro
    sem tocar no fluxo principal do processamento documental.
    """
    if not ocr_engine_available():
        return {
            'ok': False,
            'engine': None,
            'text': '',
            'blocks': [],
            'raw_json': {},
            'warnings': ['Motor OCR não disponível no servidor.'],
        }

    try:
        from PIL import Image
        import pytesseract
    except Exception as exc:
        return {
            'ok': False,
            'engine': None,
            'text': '',
            'blocks': [],
            'raw_json': {},
            'warnings': [f'Não foi possível inicializar OCR: {exc}'],
        }

    try:
        image = Image.open(image_path)
        return _ocr_image_object(image, page_number=1, page_label=image_path)
    except Exception as exc:
        return {
            'ok': False,
            'engine': 'pytesseract',
            'text': '',
            'blocks': [],
            'raw_json': {},
            'warnings': [f'Falha no OCR: {exc}'],
        }


def extract_image_text_from_object(image, page_number: int = 1, page_label: str = '') -> dict[str, Any]:
    if not ocr_engine_available():
        return {
            'ok': False,
            'engine': None,
            'text': '',
            'blocks': [],
            'raw_json': {},
            'warnings': ['Motor OCR não disponível no servidor.'],
        }
    return _ocr_image_object(image, page_number=page_number, page_label=page_label)
