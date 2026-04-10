import importlib.util
from typing import Any


DEFAULT_PREPROCESS_CONFIG = {
    'grayscale': True,
    'denoise': True,
    'contrast': True,
    'threshold': True,
    'deskew': False,
    'auto_rotate': False,
    'normalize_resolution': True,
    'target_width': 1800,
}


def opencv_available() -> bool:
    return bool(importlib.util.find_spec('cv2') and importlib.util.find_spec('numpy') and importlib.util.find_spec('PIL'))


def default_preprocess_config(overrides: dict[str, Any] | None = None) -> dict[str, Any]:
    config = dict(DEFAULT_PREPROCESS_CONFIG)
    if overrides:
        config.update({key: value for key, value in overrides.items() if key in config})
    return config


def _deskew_image(gray_image, cv2, np):
    coords = np.column_stack(np.where(gray_image < 250))
    if coords.size == 0:
        return gray_image, 0.0
    angle = cv2.minAreaRect(coords)[-1]
    if angle < -45:
        angle = -(90 + angle)
    else:
        angle = -angle
    if abs(angle) < 0.8:
        return gray_image, 0.0
    height, width = gray_image.shape[:2]
    center = (width // 2, height // 2)
    matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
    rotated = cv2.warpAffine(
        gray_image,
        matrix,
        (width, height),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_REPLICATE,
    )
    return rotated, float(angle)


def preprocess_document_image(image, config: dict[str, Any] | None = None) -> dict[str, Any]:
    cfg = default_preprocess_config(config)
    if not opencv_available():
        return {
            'ok': True,
            'image': image,
            'applied_steps': [],
            'notes': ['opencv_unavailable'],
            'warnings': ['OpenCV não está instalado; imagem usada sem pré-processamento.'],
            'geometry_changed': False,
        }

    try:
        import cv2  # type: ignore
        import numpy as np  # type: ignore
        from PIL import Image
    except Exception as exc:
        return {
            'ok': True,
            'image': image,
            'applied_steps': [],
            'notes': ['opencv_init_failed'],
            'warnings': [f'OpenCV indisponível: {exc}'],
            'geometry_changed': False,
        }

    applied_steps = []
    notes = []
    warnings = []
    geometry_changed = False

    pil_image = image.convert('RGB')
    frame = np.array(pil_image)
    frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)

    if cfg.get('normalize_resolution'):
        target_width = int(cfg.get('target_width') or 1800)
        if target_width > 0 and frame.shape[1] < target_width:
            scale = target_width / max(frame.shape[1], 1)
            new_width = int(frame.shape[1] * scale)
            new_height = int(frame.shape[0] * scale)
            frame = cv2.resize(frame, (new_width, new_height), interpolation=cv2.INTER_CUBIC)
            applied_steps.append('normalize_resolution')

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) if cfg.get('grayscale', True) else frame
    if cfg.get('grayscale', True):
        applied_steps.append('grayscale')

    if cfg.get('denoise', True):
        gray = cv2.fastNlMeansDenoising(gray, None, 12, 7, 21)
        applied_steps.append('denoise')

    if cfg.get('contrast', True):
        clahe = cv2.createCLAHE(clipLimit=2.4, tileGridSize=(8, 8))
        gray = clahe.apply(gray)
        applied_steps.append('contrast')

    if cfg.get('deskew'):
        gray, angle = _deskew_image(gray, cv2, np)
        if angle:
            geometry_changed = True
            notes.append({'deskew_angle': round(angle, 3)})
            applied_steps.append('deskew')

    if cfg.get('threshold', True):
        gray = cv2.adaptiveThreshold(
            gray,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            31,
            11,
        )
        applied_steps.append('adaptive_threshold')

    try:
        if len(getattr(gray, 'shape', [])) == 3:
            result_image = Image.fromarray(cv2.cvtColor(gray, cv2.COLOR_BGR2RGB))
        else:
            result_image = Image.fromarray(gray)
    except Exception:
        warnings.append('Não foi possível converter a imagem pré-processada; imagem original usada.')
        result_image = pil_image

    return {
        'ok': True,
        'image': result_image,
        'applied_steps': applied_steps,
        'notes': notes,
        'warnings': warnings,
        'geometry_changed': geometry_changed,
    }
