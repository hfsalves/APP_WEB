"""Local GeoNames postal lookup. Downloads public datasets, never sends addresses.

The coordinates describe a postal place, not a verified home or building.
CC BY attribution and the original row/version are retained in every match.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import io
import math
import os
from pathlib import Path
import re
import threading
import time
import unicodedata
import zipfile

import requests
from flask import current_app

from .config import TravelMapsError

_LOCK = threading.Lock()
_INDEX = {}
_RETRY_AFTER = {}
TTL = 30 * 86400
BASE_URL = 'https://download.geonames.org/export/zip/'
DEFAULT_COUNTRIES = 'PT,FR,ES,DE,BE,LU'


def name(value):
    value = unicodedata.normalize('NFKD', str(value)).encode('ascii', 'ignore').decode().lower()
    value = re.sub(r'\bst\b', 'saint', value)
    value = re.sub(r'\bste\b', 'sainte', value)
    return re.sub(r'[^a-z0-9]+', ' ', value).strip()


def parse(body, iso):
    postal, places = {}, {}
    for line in body.splitlines():
        fields = line.split('\t')
        if len(fields) < 12 or fields[0] != iso:
            continue
        try:
            lat, lon = float(fields[9]), float(fields[10])
            if not math.isfinite(lat + lon) or not -90 <= lat <= 90 or not -180 <= lon <= 180:
                continue
        except ValueError:
            continue
        # Original country, code, place, coordinates and reported accuracy.
        row = (iso, fields[1], fields[2], lat, lon, fields[11])
        postal.setdefault(fields[1].upper(), []).append(row)
        # Most PT postal codes share place coordinates: don't duplicate all rows.
        places.setdefault(name(fields[2]), {}).setdefault((lat, lon), row)
    if not postal:
        raise TravelMapsError('Catálogo de localidades vazio ou inválido.')
    return {'postal': postal, 'places': places}


def read_archive(data, iso):
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            info = archive.getinfo(iso + '.txt')
            if info.file_size > 48_000_000:
                raise ValueError
            return parse(archive.read(info).decode('utf-8'), iso)
    except (ValueError, KeyError, UnicodeError, zipfile.BadZipFile, OSError):
        raise TravelMapsError('Catálogo de localidades inválido.') from None


def download(iso):
    if time.monotonic() < _RETRY_AFTER.get(iso, 0):
        raise TravelMapsError('Catálogo de localidades temporariamente indisponível.')
    try:
        with requests.get(BASE_URL + iso + '.zip', headers={'User-Agent': 'GR360-TravelMaps/1.0'},
                          timeout=(4, 15), stream=True, allow_redirects=False) as response:
            response.raise_for_status()
            data = bytearray()
            for chunk in response.iter_content(65536):
                data.extend(chunk)
                if len(data) > 5_000_000:
                    raise ValueError
            return bytes(data)
    except (requests.RequestException, ValueError):
        _RETRY_AFTER[iso] = time.monotonic() + 120
        raise TravelMapsError('Não foi possível obter o catálogo de localidades.') from None


def dataset(iso):
    if not re.fullmatch('[A-Z]{2}', iso):
        raise TravelMapsError('País inválido para o catálogo de localidades.')
    folder = Path(current_app.instance_path) / 'gr_travel_geo' / 'postal'
    path = folder / (iso + '.zip'); key = str(path)
    with _LOCK:
        cached = _INDEX.get(key)
        if cached and time.monotonic() - cached['loaded_at'] < 3600:
            return cached
        old = None; stamp = time.time()
        try:
            if path.stat().st_size <= 5_000_000:
                old = path.read_bytes(); stamp = path.stat().st_mtime
        except OSError:
            pass
        data = old; index = None
        if old is not None:
            try:
                index = read_archive(old, iso)
            except TravelMapsError:
                old = data = None
        if old is None or time.time() - stamp >= TTL:
            try:
                fresh = download(iso)
                index = read_archive(fresh, iso)
                data, stamp = fresh, time.time()
                try:
                    folder.mkdir(parents=True, exist_ok=True, mode=0o700)
                    temp = folder / (iso + f'.{os.getpid()}.{threading.get_ident()}.tmp')
                    with os.fdopen(os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600), 'wb') as stream:
                        stream.write(fresh)
                    os.replace(temp, path)
                except OSError:
                    pass  # A successful lookup still works when the disk cache is unavailable.
            except TravelMapsError:
                if old is None:
                    raise TravelMapsError('Catálogo de localidades indisponível; localização por resolver.') from None
        index.update(loaded_at=time.monotonic(), source={
            'dataset': BASE_URL + iso + '.zip', 'sha256': hashlib.sha256(data).hexdigest(),
            'downloaded_at': datetime.fromtimestamp(stamp, timezone.utc).isoformat(),
            'cache_stale': time.time() - stamp >= TTL})
        _INDEX[key] = index
        return index


def configured_countries():
    raw = current_app.config.get('GR_TRAVEL_POSTAL_COUNTRIES') or os.environ.get('GR_TRAVEL_POSTAL_COUNTRIES') or DEFAULT_COUNTRIES
    countries = str(raw).upper().replace(' ', '').split(',')
    if not 1 <= len(countries) <= 20 or any(not re.fullmatch('[A-Z]{2}', iso) for iso in countries):
        raise TravelMapsError('Configuração de países do catálogo inválida.')
    return list(dict.fromkeys(countries))


def lookup(query, country='', locality=''):
    codes = set(re.findall(r'\b(?:\d{4}[- ]\d{3}|\d{4,5})\b', query))
    codes = {code.replace(' ', '-') for code in codes}
    # Without a postal code, use only an explicit locality field, never street names.
    place = name(re.sub(r'\b\d[\d -]*\b', ' ', locality))
    if not codes and not place:
        raise TravelMapsError('Sem código postal ou localidade para localizar automaticamente.')
    countries = [country] if country else configured_countries()
    matches = []; tokens = set(name(locality or query).split())
    for iso in countries:
        index = dataset(iso)
        if codes:
            for code in sorted(codes):
                for row in index['postal'].get(code, []):
                    words = set(name(row[2]).split())
                    hits = sum(any(word == token or len(token) >= 4 and word.startswith(token) for token in tokens) for word in words)
                    score = hits / max(1, len(words))
                    # A known country and exact code can identify a small postal area.
                    # Unknown countries additionally require a compatible place name.
                    if score >= .6 or country and not place:
                        matches.append((score, row, index['source']))
        else:
            matches.extend((1, row, index['source']) for row in index['places'].get(place, {}).values())
    if not matches:
        raise TravelMapsError('Código postal/localidade sem correspondência clara; confirme os dados da obra.')
    matches.sort(key=lambda item: (-item[0], item[1]))
    best = matches[0]; competing = [item for item in matches if best[0] - item[0] < .15]
    first = best[1]
    # Disambiguation only: this separation is never used as road mileage.
    for _, row, _ in competing:
        separation = math.hypot((first[3]-row[3])*111, (first[4]-row[4])*111*math.cos(math.radians(first[3])))
        if first[0] != row[0] or separation > 3:
            raise TravelMapsError('Código postal/localidade ambíguos; indique um local mais preciso.')
    iso, code, city, lat, lon, accuracy = first
    return {'lat': lat, 'lon': lon, 'country': iso, 'city': city, 'label': f'{code} {city}, {iso}',
            'precision': 'CODIGO_POSTAL' if codes else 'LOCALIDADE', 'source': {
                'kind': 'GEOCODIFICADO', 'provider': 'GeoNames', **best[2],
                'read_at': datetime.now(timezone.utc).isoformat(), 'postal_code': code,
                'place_name': city, 'country': iso, 'latitude': lat, 'longitude': lon, 'accuracy': accuracy,
                'query': query, 'country_filter': country, 'countries_considered': countries,
                'address_not_resolved': query, 'license': 'CC BY 4.0',
                'rule': 'Ponto aproximado do código postal/localidade; não confirma a morada exata.'}}
