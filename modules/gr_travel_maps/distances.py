"""Geocode addresses and read directed road distances; never estimate from payroll.

Only addresses/coordinates go to Photon/OSRM, never employee names or payroll.
Provider endpoints are deployment configuration, not request parameters.
"""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
import json
import math
import os
from pathlib import Path
import re
import threading
import time
import unicodedata
from urllib.parse import urlsplit

import requests
from flask import current_app

from . import engine, postal, progress
from .config import TravelMapsError

_LOCK = threading.Lock()
_LAST_REQUEST = 0.0
_UNAVAILABLE = {}
TTL = 30 * 86400
MAX_LOCATIONS = 100


def now():
    return datetime.now(timezone.utc).isoformat()


def setting(name, default):
    return str(current_app.config.get(name) or os.environ.get(name) or default).rstrip('/')


def normalized(value):
    return re.sub(r'[^a-z0-9]+', ' ', unicodedata.normalize('NFKD', str(value)).encode('ascii', 'ignore').decode().lower()).strip()


def cache_read(key):
    path = Path(current_app.instance_path) / 'gr_travel_geo' / (key + '.json')
    try:
        if time.time() - path.stat().st_mtime < TTL:
            return json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        pass
    return None


def cache_write(key, value):
    folder = Path(current_app.instance_path) / 'gr_travel_geo'
    try:
        folder.mkdir(parents=True, exist_ok=True, mode=0o700)
        path = folder / (key + '.json')
        # Atomic replacement, private permissions; no SQL schema or PHC writes.
        temp = folder / (key + f'.{threading.get_ident()}.tmp')
        fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            json.dump(value, stream, ensure_ascii=False, allow_nan=False)
        os.replace(temp, path)
    except OSError:
        pass  # Cache failure does not invalidate a successful provider response.


def fetch(url, params=None):
    host = urlsplit(url).netloc
    if time.monotonic() < _UNAVAILABLE.get(host, 0):
        raise TravelMapsError('Serviço de mapas temporariamente indisponível; tente novamente mais tarde.')
    try:
        response = requests.get(url, params=params, headers={'User-Agent': 'GR360-TravelMaps/1.0', 'Accept': 'application/json'},
                                timeout=(4, 10), allow_redirects=False)
        response.raise_for_status()
        if len(response.content) > 2_000_000:
            raise ValueError
        result = response.json()
        if not isinstance(result, dict):
            raise ValueError
        return result
    except (requests.RequestException, ValueError):
        _UNAVAILABLE[host] = time.monotonic() + 120
        raise TravelMapsError('Serviço de mapas indisponível ou com resposta inválida; distância por calcular.') from None


def coordinates(lat, lon):
    try:
        lat, lon = float(lat), float(lon)
        if not math.isfinite(lat + lon) or not -90 <= lat <= 90 or not -180 <= lon <= 180:
            raise ValueError
        return lat, lon
    except (TypeError, ValueError):
        raise TravelMapsError('Coordenadas inválidas.') from None


def select_match(features, query, country):
    candidates = []
    tokens = set(normalized(query).split()) - {'rua', 'avenida', 'rue', 'de', 'da', 'do', 'dos', 'das', 'du', 'des', 'la', 'le', 'pt', 'fr'}
    for feature in features:
        try:
            properties = feature['properties']
            lon, lat = feature['geometry']['coordinates'][:2]
            lat, lon = coordinates(lat, lon)
            iso = engine.country(properties.get('countrycode', ''))
            if country and iso != country:
                continue
            label = ', '.join(dict.fromkeys(str(properties.get(k) or '').strip() for k in
                             ('name', 'street', 'housenumber', 'postcode', 'city', 'district', 'country') if properties.get(k)))
            overlap = len(tokens & set(normalized(label).split())) / max(1, len(tokens))
            if overlap < .45:
                continue
            precision = 'MORADA' if properties.get('housenumber') else 'RUA' if properties.get('street') or properties.get('osm_key') == 'highway' else 'LOCALIDADE'
            if precision == 'LOCALIDADE' and properties.get('osm_value') not in ('city', 'town', 'village', 'hamlet', 'suburb', 'quarter', 'neighbourhood', 'postcode'):
                continue
            candidates.append((overlap, {'lat': lat, 'lon': lon, 'country': iso,
                'city': properties.get('city') or properties.get('name') or '', 'label': label,
                'precision': precision, 'osm_type': properties.get('osm_type'), 'osm_id': properties.get('osm_id')}))
        except (KeyError, TypeError, ValueError, TravelMapsError):
            continue
    candidates.sort(key=lambda item: -item[0])
    if not candidates:
        raise TravelMapsError('Morada sem correspondência suficientemente clara; corrija o local ou indique coordenadas.')
    best = candidates[0]
    if any(abs(best[0]-score) < .05 and math.hypot(best[1]['lat']-item['lat'], best[1]['lon']-item['lon']) > .04
           for score, item in candidates[1:]):
        raise TravelMapsError('Morada ambígua entre locais diferentes; indique coordenadas ou complete a morada.')
    return best[1]


def geocode(query, country=''):
    global _LAST_REQUEST
    if not query:
        raise TravelMapsError('Morada/local em falta no PHC.')
    endpoint = setting('GR_TRAVEL_PHOTON_URL', 'https://photon.komoot.io')
    key = engine.digest(['photon-v1', endpoint, normalized(query), country])
    with _LOCK:
        cached = cache_read(key)
        if cached is not None:
            return cached
        if time.monotonic() < _UNAVAILABLE.get(urlsplit(endpoint).netloc, 0):
            raise TravelMapsError('Pesquisa de moradas temporariamente indisponível.')
        wait = 1.05 - (time.monotonic() - _LAST_REQUEST)
        if wait > 0:
            time.sleep(wait)
        _LAST_REQUEST = time.monotonic()
        params = {'q': query, 'limit': 4}
        if country:
            params['countrycode'] = country
        data = fetch(endpoint + '/api', params)
        result = select_match(data.get('features', []), query, country)
        result['source'] = {'kind': 'GEOCODIFICADO', 'provider': 'Photon', 'endpoint': endpoint,
                            'query': query, 'country_filter': country, 'read_at': now(),
                            'osm_type': result.pop('osm_type'), 'osm_id': result.pop('osm_id')}
        cache_write(key, result)
        return result


def locate_address(query, country, locality=''):
    """A locality fallback is approximate and never substitutes a changed address."""
    try:
        return geocode(query, country)
    except TravelMapsError:
        if locality and query and normalized(query) != normalized(locality):
            try:
                result = geocode(locality, country)
                return {**result, 'precision': 'LOCALIDADE', 'source': {**result['source'],
                    'address_not_resolved': query, 'rule': 'Aproximação pela localidade da ficha; morada exata por confirmar.'}}
            except TravelMapsError:
                pass
        return postal.lookup(query, country, locality)


def road_matrix(locations):
    ordered = sorted(locations)
    if len(ordered) < 2:
        return {}, []
    endpoint = setting('GR_TRAVEL_OSRM_URL', 'https://router.project-osrm.org')
    coords = ';'.join(f"{locations[key]['lon']},{locations[key]['lat']}" for key in ordered)
    key = engine.digest(['osrm-v1', endpoint, coords])
    with _LOCK:
        data = cache_read(key)
        if data is None:
            response = fetch(endpoint + '/table/v1/driving/' + coords, {'annotations': 'distance,duration'})
            if response.get('code') != 'Ok' or response.get('fallback_speed_cells'):
                raise TravelMapsError('O serviço não devolveu percursos rodoviários válidos.')
            data = {'response': response, 'read_at': now()}
            cache_write(key, data)
    response = data['response']; n = len(ordered)
    matrix, durations = response.get('distances'), response.get('durations')
    if not isinstance(matrix, list) or not isinstance(durations, list) or len(matrix) != n or len(durations) != n:
        raise TravelMapsError('Matriz de distâncias incompleta.')
    edges, warnings = {}, []
    for i, origin in enumerate(ordered):
        if len(matrix[i]) != n or len(durations[i]) != n:
            raise TravelMapsError('Matriz de distâncias incompleta.')
        for j, destination in enumerate(ordered):
            if i == j or matrix[i][j] is None or durations[i][j] is None:
                continue
            try:
                meters, seconds = Decimal(str(matrix[i][j])), Decimal(str(durations[i][j]))
                if not meters.is_finite() or not seconds.is_finite() or meters < 0 or seconds < 0:
                    raise ValueError
                snapped = [response.get('sources', [{}]*n)[i].get('distance', 0),
                           response.get('destinations', [{}]*n)[j].get('distance', 0)]
                if any(float(distance) > 2000 for distance in snapped):
                    warnings.append('Há locais afastados da rede rodoviária; esses percursos foram excluídos.')
                    continue
            except (ValueError, TypeError, ArithmeticError, IndexError):
                raise TravelMapsError('Distância rodoviária inválida.') from None
            edges[f'{origin}>{destination}'] = {'from': origin, 'to': destination,
                'km': str((meters/1000).quantize(Decimal('.01'), rounding=ROUND_HALF_UP)), 'meters': str(meters),
                'seconds': str(seconds), 'source': {'kind': 'CALCULADO', 'provider': 'OSRM', 'endpoint': endpoint,
                'profile': 'driving', 'read_at': data['read_at'], 'data_version': response.get('data_version'),
                'rule': 'Distância rodoviária do percurso mais rápido, arredondada a 0,01 km; sentidos calculados separadamente.'}}
    return edges, list(dict.fromkeys(warnings))


def prepare(payroll, batches, raw_inputs):
    return progress.finish(prepare_steps(payroll, batches, raw_inputs))


def prepare_steps(payroll, batches, raw_inputs, planning=None):
    works = engine.candidates(batches, planning)
    overrides = raw_inputs.get('locations', {})
    if not isinstance(overrides, dict) or set(overrides) - {'home', *(w['key'] for w in works)}:
        raise TravelMapsError('Correção de local desconhecida.')
    if len(works) > MAX_LOCATIONS-1:
        raise TravelMapsError('Há mais de 99 obras candidatas. Restrinja as empresas para calcular os percursos.')
    profile = payroll.get('employee_profile', {})
    home_address = engine.text(raw_inputs.get('origin', profile.get('origin', '')), 'Origem', 300)
    home_country = engine.country(raw_inputs.get('origin_country', 'PT'))
    home_locality = profile.get('original', {}).get('pe', {}).get('LOCAL', '') if home_address == profile.get('origin') else ''
    points = [{'key': 'home', 'label': 'Casa', 'address': home_address, 'country': home_country, 'locality': home_locality}]
    for work in works:
        query = ', '.join(dict.fromkeys(value.strip() for value in (work['address'], work['locality']) if value.strip()))
        points.append({'key': work['key'], 'label': work['work'], 'address': query, 'country': '', 'locality': work['locality']})
    locations, unresolved, warnings = {}, [], []
    deadline = time.monotonic() + 90
    for index, point in enumerate(points):
        override = overrides.get(point['key'], {})
        if not isinstance(override, dict) or set(override) - {'address', 'country', 'lat', 'lon'}:
            raise TravelMapsError('Correção de local inválida.')
        query = engine.text(override.get('address', point['address']), 'Morada/local', 500)
        iso = engine.country(override.get('country', point['country']))
        yield progress.event('locations', 'A localizar a casa do trabalhador…' if point['key'] == 'home'
                             else f"A localizar a obra {point['label']}…",
                             current=point['label'], detail=query, completed=index, total=len(points),
                             resolved=len(locations), unresolved=len(unresolved))
        try:
            if time.monotonic() > deadline:
                raise TravelMapsError('Tempo de localização excedido. Repita a reconstrução; os locais já calculados ficam em cache.')
            if override.get('lat') not in (None, '') or override.get('lon') not in (None, ''):
                lat, lon = coordinates(override.get('lat'), override.get('lon'))
                if not iso:
                    raise TravelMapsError('Indique o país das coordenadas declaradas.')
                located = {'lat': lat, 'lon': lon, 'label': query or point['label'], 'city': query or point['label'],
                           'country': iso, 'precision': 'DECLARADO', 'source': {'kind': 'DECLARADO', 'reference': raw_inputs.get('note', '')}}
            else:
                located = locate_address(query, iso, point['locality'] if query == point['address'] else '')
            locations[point['key']] = {**point, **located, 'address': query,
                                       'label': point['label'], 'matched_label': located['label']}
            if located['precision'] in ('RUA', 'LOCALIDADE', 'CODIGO_POSTAL'):
                warnings.append(f"{point['label']}: localização aproximada ({located['precision'].lower()}); confirme o ponto do percurso.")
        except TravelMapsError as exc:
            unresolved.append({'key': point['key'], 'label': point['label'], 'address': query, 'reason': str(exc)})
        yield progress.event('locations', f"{point['label']}: " + ('localizado.' if point['key'] in locations else 'por resolver.'),
                             current=point['label'], detail=query, completed=index+1, total=len(points),
                             resolved=len(locations), unresolved=len(unresolved))
    yield progress.event('routes', f'A calcular percursos rodoviários entre {len(locations)} locais…',
                         resolved=len(locations), unresolved=len(unresolved))
    try:
        edges, road_warnings = road_matrix(locations)
        warnings.extend(road_warnings)
    except TravelMapsError as exc:
        edges = {}; warnings.append(str(exc))
    if unresolved:
        warnings.append(f'{len(unresolved)} local(is) por resolver; só os percursos calculados entram na proposta.')
    approximate = [key for key, point in locations.items() if point['precision'] in ('RUA', 'LOCALIDADE', 'CODIGO_POSTAL')]
    return {'locations': locations, 'edges': edges, 'unresolved': unresolved, 'warnings': warnings, 'read_at': now(),
            'diagnostics': {'works_considered': len(works), 'locations_resolved': len(locations),
                            'locations_unresolved': len(unresolved), 'approximate_locations': len(approximate),
                            'road_legs_calculated': len(edges)}}
