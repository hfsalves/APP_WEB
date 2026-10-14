"""Pure deterministic proposals. Measurement dossiers establish candidates, never attendance."""
from __future__ import annotations

from copy import deepcopy
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import hashlib
import json

from .config import CATEGORIES, TravelMapsError, period_bounds

ENGINE_VERSION = 'autos-v2'
MAX_STATES = 6000
MAX_WORKS = 40
D = Decimal


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def number(value, label, maximum='1000000', places=2):
    try:
        result = D(str(value))
        if not result.is_finite() or result < 0 or result > D(maximum):
            raise ValueError
        if result != result.quantize(D(10) ** -places):
            raise ValueError
        return result
    except (InvalidOperation, TypeError, ValueError):
        raise TravelMapsError(f'{label}: indique um número não negativo, até {maximum}, com no máximo {places} casas decimais.') from None


def text(value, label, limit=500, required=False):
    if not isinstance(value, str) or len(value) > limit or (required and not value.strip()):
        raise TravelMapsError(f'{label}: texto inválido ou em falta (máximo {limit} caracteres).')
    return value.strip()


def country(value):
    value = text(value, 'País', 2).upper()
    if value and (len(value) != 2 or not value.isascii() or not value.isalpha() or value in ('XX', 'ZZ')):
        raise TravelMapsError('Indique o código do país com duas letras, ou deixe-o por confirmar.')
    return value


def candidates(measurements):
    grouped = {}
    for batch in measurements:
        for record in batch['rows']:
            if not record['has_positive_measurement'] or not record['work']:
                continue
            identity = [batch['company']['feid'], batch['company']['phc_db'], record['work']]
            key = digest(identity)
            if key not in grouped:
                grouped[key] = {'key': key, 'company': batch['company'], 'work': record['work'],
                                'client': record['client'], 'address': record['address'], 'locality': record['locality'],
                                'evidence': []}
            grouped[key]['evidence'].append(deepcopy(record))
    # Multiple autos for a work do not multiply the number of permissible trips.
    return sorted(grouped.values(), key=lambda w: (w['company']['feid'], w['work'], w['key']))


def normalize_inputs(raw, available, start, end):
    if not isinstance(raw, dict):
        raise TravelMapsError('Pressupostos inválidos.')
    result = {
        'origin': text(raw.get('origin', ''), 'Origem', 300),
        'origin_country': country(raw.get('origin_country', 'PT')),
        'allowance_country': country(raw.get('allowance_country', 'PT')),
        'note': text(raw.get('note', ''), 'Fonte dos pressupostos', 1000, True),
        'vehicle': text(raw.get('vehicle', ''), 'Viatura', 80),
        'owner': text(raw.get('owner', ''), 'Proprietário', 200),
        'blocked_dates': [], 'works': [], 'rates': {}, 'include_weekends': raw.get('include_weekends', False),
    }
    if type(result['include_weekends']) is not bool:
        raise TravelMapsError('Opção de fins de semana inválida.')
    blocked = raw.get('blocked_dates', [])
    if not isinstance(blocked, list) or len(blocked) > 31:
        raise TravelMapsError('Lista de dias excluídos inválida.')
    for value in blocked:
        try:
            day = date.fromisoformat(value)
        except (ValueError, TypeError):
            raise TravelMapsError('Data excluída inválida.') from None
        if not start <= day < end:
            raise TravelMapsError('Os dias excluídos têm de pertencer ao mês do mapa.')
        result['blocked_dates'].append(day.isoformat())
    result['blocked_dates'] = sorted(set(result['blocked_dates']))
    selections = raw.get('works', [])
    if not isinstance(selections, list) or len(selections) > MAX_WORKS:
        raise TravelMapsError(f'Selecione no máximo {MAX_WORKS} obras por proposta.')
    known, seen = {w['key']: w for w in available}, set()
    for selection in selections:
        if not isinstance(selection, dict) or selection.get('key') not in known or selection['key'] in seen:
            raise TravelMapsError('Obra repetida ou sem auto com medição positiva neste mês.')
        key = selection['key']; seen.add(key)
        work = known[key]
        outward = selection.get('outward_km')
        back = selection.get('return_km')
        outward = None if outward in (None, '') else str(number(outward, 'Distância de ida', '2500'))
        back = None if back in (None, '') else str(number(back, 'Distância de regresso', '2500'))
        if back is not None and outward is None:
            raise TravelMapsError('Indique também a distância de ida.')
        distance_source = text(selection.get('distance_source', ''), 'Fonte da distância', 500)
        if outward is not None and (not result['origin'] or not distance_source):
            raise TravelMapsError('Uma distância requer origem e fonte do percurso.')
        maximum = selection.get('max_trips')
        automatic_limit = maximum in (None, '')
        if automatic_limit:
            maximum = len(calendar_days(start, end, result['blocked_dates'], result['include_weekends']))
        if type(maximum) is not int or not 0 <= maximum <= 31:
            raise TravelMapsError('O limite de deslocações por obra e mês deve estar entre 0 e 31.')
        result['works'].append({
            'key': key, 'country': country(selection.get('country', '')),
            'city': text(selection.get('city', work['locality']), 'Local', 300),
            'outward_km': outward, 'return_km': back, 'distance_source': distance_source, 'max_trips': maximum,
            'max_trips_source': 'CALENDARIO' if automatic_limit else 'DECLARADO',
        })
    result['works'].sort(key=lambda item: (known[item['key']]['company']['feid'], known[item['key']]['work'], item['key']))
    rates = raw.get('rates', {})
    if not isinstance(rates, dict) or set(rates) - set(CATEGORIES):
        raise TravelMapsError('Valores unitários inválidos.')
    for category, value in rates.items():
        if value not in (None, ''):
            result['rates'][category] = str(number(value, 'Valor unitário', '10000', 6))
    return result


def calendar_days(start, end, blocked, include_weekends=False):
    return [(start + timedelta(days=i)).isoformat() for i in range((end-start).days)
            if (include_weekends or (start + timedelta(days=i)).weekday() < 5) and (start + timedelta(days=i)).isoformat() not in blocked]


def km_combination(target, routes, slots, max_states=MAX_STATES):
    """Bounded subset sum in hundredths of km. No rounded distances to force a fit.

    Exact while states fit the configured bound; deterministic beam reduction is
    disclosed when used. Preference: residual, undershoot, fewer visits, stable order.
    """
    target = D(target) * 100
    if target <= 0 or not routes or (slots <= 0 and not any(w.get('private_slots', 0) for w in routes)):
        return [], False
    ceiling = target + max(int(D(w['round_trip']) * 100) for w in routes)
    # A day already assigned AC at this same work can host one KM visit.
    # Those private slots cannot be used by any other work.
    states = {(0, 0, 0): ()}  # distance, shared calendar slots consumed, visits
    truncated = False
    for work in routes:
        distance = int(D(work['round_trip']) * 100)
        next_states = {}
        for (total, shared, used), path in states.items():
            private = work.get('private_slots', 0)
            for count in range(min(work['max_trips'], private+slots-shared) + 1):
                new_total = total + count * distance
                if new_total > ceiling:
                    break
                key = (new_total, shared+max(0,count-private), used+count)
                proposal = path + (count,)
                if key not in next_states or proposal > next_states[key]:
                    next_states[key] = proposal
        if len(next_states) > max_states:
            truncated = True
            # Retain low totals as well as near-target states for later works.
            ranked = sorted(next_states, key=lambda k: (abs(k[0]-target), k[0] > target, k[2], k[1], k[0]))
            low = sorted(next_states, key=lambda k: (k[0], k[1], k[2]))[:max_states//4]
            keys = list(dict.fromkeys(low + ranked))[:max_states]
            next_states = {key: next_states[key] for key in keys}
        states = next_states
    best = min(states, key=lambda k: (abs(k[0]-target), k[0] > target, k[2], k[0], k[1]))
    return [(work, count) for work, count in zip(routes, states[best]) if count], truncated


def reconciliation(phc, value):
    if phc is None:
        return {'phc': None, 'map': str(value), 'difference': None, 'percent': None}
    target = D(phc)
    difference = value-target
    percent = (D(100) if not difference else D(0)) if not target else max(D(0), D(100)*(1-abs(difference)/abs(target)))
    return {'phc': str(target), 'map': str(value), 'difference': str(difference),
            'percent': str(percent.quantize(D('.01'), rounding=ROUND_HALF_UP))}


def summarize(document):
    result = {}
    for category in CATEGORIES:
        lines = [line for line in document['entries'] if line['category'] == category and line['included']]
        quantity = sum((D(line['quantity']) for line in lines), D(0))
        result[category] = reconciliation(document['payroll']['employee']['phc'][category]['quantity'], quantity)
        result[category]['amount'] = (None if any(line['amount'] is None for line in lines)
                                      else str(sum((D(line['amount']) for line in lines), D(0))))
    return result


def rate_for(employee, category, inputs):
    if category in inputs['rates']:
        return inputs['rates'][category], {'kind': 'DECLARADO', 'reference': inputs['note']}
    lines = [line for line in employee['lines'] if line['category'] == category and D(line['original']['RQTT']) > 0]
    values = {line['original']['ERVU'] for line in lines}
    numeric = {D(value) for value in values}
    if len(numeric) == 1 and next(iter(numeric)) >= 0:
        return str(next(iter(numeric))), {'kind': 'PHC', 'references': [line['source'] for line in lines]}
    return None, {'kind': 'DESCONHECIDO', 'reason': 'Sem valor unitário único no PHC.'}


def make_entry(category, day, quantity, work, selection, inputs, employee):
    rate, rate_source = rate_for(employee, category, inputs)
    references = [record['source'] for record in work['evidence']]
    return {
        'id': digest([category, day, work['key']])[:24], 'category': category, 'date': day,
        'start_date': day, 'end_date': day, 'quantity': str(quantity), 'rate': rate,
        'amount': None if rate is None else str((quantity * D(rate)).quantize(D('.01'), rounding=ROUND_HALF_UP)),
        'work_key': work['key'], 'work': work['work'], 'client': work['client'],
        'country': selection['country'] or None, 'city': selection['city'],
        'origin': inputs['origin'], 'destination': work['address'] or selection['city'] or work['work'],
        'reason': f'Atividade proposta na obra {work["work"]}, com auto de medição no mês.',
        'travel_type': 'IDA_VOLTA' if category == 'km' else category.upper(),
        'vehicle': inputs['vehicle'], 'owner': inputs['owner'], 'included': True,
        'evidence_type': 'INFERIDO', 'validation_state': 'POR_VALIDAR',
        'confidence': {'level': 'BAIXA', 'reason': 'O auto não identifica presença, trabalhador ou viagem.'},
        'provenance': {
            'work': {'kind': 'AUTO_MEDICAO', 'references': references},
            'date': {'kind': 'INFERIDO', 'rule': 'Primeiros dias livres do calendário convencional do mês.'},
            'employee_assignment': {'kind': 'INFERIDO', 'rule': 'Obra selecionada para proposta; não existe registo de presença.'},
            'country': {'kind': 'DECLARADO', 'reference': inputs['note']},
            'allowance_classification': {'kind': 'CALCULADO', 'reference_country': inputs['allowance_country'],
                                        'rule': 'País da obra comparado com o país de referência declarado das AC.'},
            'origin': deepcopy(inputs['provenance']['origin']),
            'vehicle': deepcopy(inputs['provenance']['vehicle']),
            'owner': {'kind': 'DECLARADO', 'reference': inputs['note']},
            'quantity': {'kind': 'CALCULADO', 'rule': 'ida + regresso' if category == 'km' else 'distribuição dos dias PHC pelo calendário disponível'},
            'rate': rate_source,
        },
    }


def build(payroll, measurements, raw_inputs):
    start, end = period_bounds(payroll['year'], payroll['month'])
    employee = payroll['employee']
    if not employee['identity_resolved']:
        raise TravelMapsError('Resolva a identidade PHC do trabalhador antes de guardar propostas.')
    available = candidates(measurements)
    profile = payroll.get('employee_profile', {})
    if isinstance(raw_inputs, dict):
        raw_inputs = {**{field: profile.get(field, '') for field in ('origin', 'vehicle')}, **raw_inputs}
    inputs = normalize_inputs(raw_inputs, available, start, end)
    # Only server-read PE/PE2 data may establish PHC provenance. Client metadata is ignored.
    inputs['provenance'] = {}
    for field in ('origin', 'vehicle'):
        source = profile.get('provenance', {}).get(field)
        if source and inputs[field] and inputs[field] == profile.get(field):
            inputs['provenance'][field] = deepcopy(source)
        else:
            inputs['provenance'][field] = {'kind': 'DECLARADO', 'reference': inputs['note']}
            if source:
                inputs['provenance'][field]['previous_source'] = deepcopy(source)
    document = {'engine_version': ENGINE_VERSION, 'payroll': deepcopy(payroll), 'measurements': deepcopy(measurements),
                'inputs': inputs, 'entries': [], 'warnings': [
                    'As datas e a associação trabalhador/obra são inferidas; os autos não comprovam presenças.',
                    'Os autos são selecionados pela data do documento; o período efetivo de produção necessita de confirmação.',
                    ('Calendário inclui fins de semana por opção do revisor.' if inputs['include_weekends'] else 'Calendário convencional de segunda a sexta.') + ' Feriados e ausências só são excluídos quando indicados pelo revisor.',
                    'O valor unitário PHC é uma referência salarial, não uma verificação de elegibilidade fiscal.',
                ], 'validation': None, 'search_truncated': False}
    document['warnings'].extend(profile.get('warnings', []))
    free = calendar_days(start, end, inputs['blocked_dates'], inputs['include_weekends'])
    works = {work['key']: work for work in available}
    selections = inputs['works']
    selected_refs = {(works[selection['key']]['company']['feid'], record['bostamp'])
                     for selection in selections for record in works[selection['key']]['evidence']}
    for batch in document['measurements']:
        batch['rows'] = [record for record in batch['rows'] if (batch['company']['feid'], record['bostamp']) in selected_refs]
    # AC occupies dates first. KM may reuse a day only at that same work.
    for category in ('ac_estrangeiro', 'ac_nacional'):
        target = employee['phc'][category]['quantity']
        if target is None or D(target) <= 0:
            continue
        eligible = [s for s in selections if s['country'] and
                    ((s['country'] != inputs['allowance_country']) if category == 'ac_estrangeiro' else (s['country'] == inputs['allowance_country']))]
        if not inputs['allowance_country'] or not eligible:
            document['warnings'].append(f'{category}: sem obra com país indicado compatível; dias por reconciliar.')
            continue
        selection = eligible[0]  # Stable tie-break, never claimed to be evidence of this worker.
        if len(eligible) > 1:
            document['warnings'].append(f'{category}: entre {len(eligible)} obras elegíveis, foi proposta a primeira por empresa/código. A associação necessita de revisão.')
        remaining = D(target)
        while remaining > 0 and free:
            quantity = min(D(1), remaining)
            document['entries'].append(make_entry(category, free.pop(0), quantity, works[selection['key']], selection, inputs, employee))
            remaining -= quantity
        if remaining > 0:
            document['warnings'].append(f'{category}: calendário insuficiente; {remaining} dias por distribuir.')
    routes = []
    private_dates = {}
    for entry in document['entries']:
        private_dates.setdefault(entry['work_key'], []).append(entry['date'])
    for selection in selections:
        if selection['outward_km'] is None:
            continue
        back = selection['return_km'] if selection['return_km'] is not None else selection['outward_km']
        distance = D(selection['outward_km']) + D(back)
        if distance > 0:
            routes.append({**selection, 'round_trip': str(distance), 'private_slots': len(private_dates.get(selection['key'], []))})
    target = employee['phc']['km']['quantity']
    chosen, truncated = km_combination(target or '0', routes, len(free))
    document['search_truncated'] = truncated
    if truncated:
        document['warnings'].append('A pesquisa atingiu o limite de combinações: a solução é aproximada, sem garantia de ótimo.')
    if target is not None and D(target) > 0 and not routes:
        document['warnings'].append('Sem percursos com distância e fonte: quilómetros por reconciliar.')
    for selection, count in chosen:
        for _ in range(count):
            dates = private_dates.get(selection['key'], [])
            day = dates.pop(0) if dates else free.pop(0)
            entry = make_entry('km', day, D(selection['round_trip']), works[selection['key']], selection, inputs, employee)
            entry['provenance']['distance'] = {'kind': 'DECLARADO', 'outward_km': selection['outward_km'],
                'return_km': selection['return_km'], 'symmetric_return_inferred': selection['return_km'] is None,
                'reference': selection['distance_source']}
            document['entries'].append(entry)
    for category in CATEGORIES:
        target = employee['phc'][category]['quantity']
        if target is None:
            document['warnings'].append(f'{category}: total PHC desconhecido; categoria fora do âmbito de validação.')
        elif D(target) < 0:
            document['warnings'].append(f'{category}: total PHC negativo, necessita de análise de regularizações.')
    if any(line['rate'] is None for line in document['entries']):
        document['warnings'].append('Existem valores unitários por indicar antes da validação.')
    document['entries'].sort(key=lambda entry: (entry['date'], entry['category'], entry['id']))
    check_entries(document)
    document['reconciliation'] = summarize(document)
    return document


def check_entries(document, validating=False):
    start, end = period_bounds(document['payroll']['year'], document['payroll']['month'])
    days = set(calendar_days(start, end, document['inputs']['blocked_dates'], document['inputs'].get('include_weekends', False)))
    occupancy = {}
    for entry in document['entries']:
        if not entry['included']:
            continue
        if entry['date'] not in days:
            raise TravelMapsError('Uma linha está fora dos dias permitidos do mês.')
        same_day = occupancy.setdefault(entry['date'], [])
        if any(other['work_key'] != entry['work_key'] or (other['category'] == 'km') == (entry['category'] == 'km') for other in same_day):
            raise TravelMapsError('Existem deslocações ou ajudas de custo incompatíveis na mesma data.')
        same_day.append(entry)
        if validating and (not entry['reason'] or entry['rate'] is None or not entry['city'] or not entry['country']):
            raise TravelMapsError('Complete motivo, local, país e valor unitário de todas as linhas incluídas.')
        if validating and entry['category'] == 'km' and (not entry['origin'] or not entry['vehicle'] or not entry['owner']):
            raise TravelMapsError('Indique origem, viatura e proprietário antes de validar quilómetros.')


def edit(document, changes, actor, note):
    result = deepcopy(document)
    if not isinstance(changes, list) or not changes or len(changes) > 62:
        raise TravelMapsError('Indique as linhas a alterar.')
    known = {entry['id']: entry for entry in result['entries']}
    seen = set()
    for change in changes:
        if not isinstance(change, dict) or change.get('id') not in known or change['id'] in seen:
            raise TravelMapsError('Linha desconhecida ou repetida.')
        seen.add(change['id']); entry = known[change['id']]
        allowed = {'date', 'quantity', 'rate', 'reason', 'included', 'city', 'vehicle', 'owner', 'origin'}
        if set(change) - allowed - {'id'}:
            raise TravelMapsError('A alteração contém campos protegidos.')
        for key, value in change.items():
            if key == 'id': continue
            before = deepcopy(entry[key])
            if key in ('quantity', 'rate'):
                value = str(number(value, key, '1' if key == 'quantity' and entry['category'] != 'km' else '10000',
                                   6 if key == 'rate' or entry['category'] != 'km' else 2))
                if key == 'quantity' and D(value) <= 0:
                    raise TravelMapsError('A quantidade deve ser positiva; exclua a linha para a rejeitar.')
            elif key == 'included':
                if type(value) is not bool: raise TravelMapsError('Inclusão de linha inválida.')
            else:
                value = text(value, key, 500)
            if before != value:
                entry[key] = value
                entry['provenance'].setdefault('human_changes', []).append({'field': key, 'before': before, 'after': value, 'actor': actor, 'reason': note})
                entry['provenance'][key] = {'kind': 'DECLARADO', 'actor': actor, 'reference': note,
                                            'previous_source': deepcopy(entry['provenance'].get(key))}
        entry['start_date'] = entry['end_date'] = entry['date']
        entry['amount'] = None if entry['rate'] is None else str((D(entry['quantity'])*D(entry['rate'])).quantize(D('.01'), rounding=ROUND_HALF_UP))
    result['validation'] = None
    for entry in result['entries']:
        entry['validation_state'] = 'POR_VALIDAR'
    check_entries(result)
    result['entries'].sort(key=lambda entry: (entry['date'], entry['category'], entry['id']))
    result['reconciliation'] = summarize(result)
    return result
