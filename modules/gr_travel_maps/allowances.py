"""AC eligibility from work assignments and explicitly inferred weekend stays."""
from copy import deepcopy
from datetime import date, timedelta

from .config import map_bounds

POLICY = 'PLANNING_WORK_AND_WEEKEND_STAY_V1'
WEEKEND = 'PERMANENCIA_FIM_SEMANA'


def travel_allows_stay(document, work, friday, monday):
    """A proposed return home or stay elsewhere overrides an inferred weekend."""
    from .itinerary import presence
    weekend = [(date.fromisoformat(friday)+timedelta(days=i)).isoformat() for i in (1, 2)]
    for journey in document.get('journeys', []):
        legs = sorted((e for e in document['entries'] if e['included'] and e.get('journey_id') == journey['id']), key=lambda e: e['leg_index'])
        if not legs:
            continue
        for leg in legs:
            if leg['to_key'] == 'home' and friday <= leg['date'] < monday:
                return False
            if leg['from_key'] == 'home' and friday < leg.get('start_date', leg['date']) <= monday:
                return False
        if any(work not in places for places in presence(legs, weekend).values()):
            return False
    return True


def eligible(document):
    """Return date/work evidence. This never grants KM dates or invents work days."""
    plan = document.get('planning')
    if plan is None:
        return {}
    start, end = map_bounds(document['payroll'])
    blocked = set(document['inputs']['blocked_dates']) | set(plan['blocked_dates']) | set(plan.get('context_blocked_dates', {}))
    daily = {}
    for row in plan['records'] + plan.get('context_records', []):
        daily.setdefault(row['date'], {}).setdefault(row['work_key'], []).append(row)
    result = {}
    for day, works in daily.items():
        if start.isoformat() <= day < end.isoformat() and day not in blocked:
            result[day] = {key: {'kind': 'PLANEAMENTO', 'basis': 'TRABALHO_REGISTADO',
                                'rule': 'Obra e data registadas para a equipa do colaborador.', 'references': deepcopy(refs)}
                           for key, refs in works.items()}
    if document.get('allowance_policy') != POLICY:
        return result
    for offset in range((end-start).days):
        day = start+timedelta(days=offset); iso = day.isoformat()
        if day.weekday() < 5 or iso in daily or iso in blocked:
            continue
        friday = day-timedelta(days=day.weekday()-4)
        monday = friday+timedelta(days=3)
        first, last = friday.isoformat(), monday.isoformat()
        before, after = daily.get(first, {}), daily.get(last, {})
        if len(before) != 1 or set(before) != set(after):
            continue
        work = next(iter(before))
        interval = [(friday+timedelta(days=i)).isoformat() for i in range(4)]
        if any(d in blocked or d in daily and set(daily[d]) != {work} for d in interval):
            continue
        if not travel_allows_stay(document, work, first, last):
            continue
        result[iso] = {work: {'kind': 'INFERIDO', 'basis': WEEKEND, 'friday': first, 'monday': last,
            'rule': 'Permanência inferida no fim de semana: trabalho na sexta e na segunda na mesma obra, sem ausência, exclusão ou percurso incompatível.',
            'references': deepcopy(before[work]+after[work])}}
    return dict(sorted(result.items()))


def annotate(document, *, preserve_declared=False):
    eligible_days = eligible(document)
    for entry in document['entries']:
        if entry['category'] == 'km':
            continue
        evidence = eligible_days.get(entry['date'], {}).get(entry['work_key'])
        previous_basis = entry.get('allowance_basis')
        entry['allowance_basis'] = evidence['basis'] if evidence else None
        entry['provenance'].pop('allowance_calendar', None)
        if evidence is None:
            continue
        entry['provenance']['allowance_calendar'] = deepcopy(evidence)
        if evidence['basis'] != WEEKEND:
            if previous_basis == WEEKEND and entry['provenance'].get('reason', {}).get('kind') != 'DECLARADO':
                entry['reason'] = f'Atividade proposta na obra {entry["work"]}, apoiada no planeamento da equipa.'
            continue
        entry['provenance']['employee_assignment'] = deepcopy(evidence)
        if not preserve_declared or entry['provenance']['date'].get('kind') != 'DECLARADO':
            entry['provenance']['date'] = deepcopy(evidence)
        entry['confidence'] = {'level': 'BAIXA', 'reason': evidence['rule']}
        if not preserve_declared or entry['provenance'].get('reason', {}).get('kind') != 'DECLARADO':
            entry['reason'] = f'Permanência inferida de fim de semana na obra {entry["work"]}; continuidade entre {evidence["friday"]} e {evidence["monday"]}.'
    document['allowance_calendar'] = {'policy': document.get('allowance_policy'),
        'days': [{'date': day, 'work_key': key, 'basis': evidence['basis']}
                 for day, works in eligible_days.items() for key, evidence in works.items()],
        'work_days': sum(any(e['basis']=='TRABALHO_REGISTADO' for e in works.values()) for works in eligible_days.values()),
        'weekend_days': sum(any(e['basis']==WEEKEND for e in works.values()) for works in eligible_days.values())}
    warning = 'AC de fim de semana: permanência inferida pela mesma obra na sexta e na segunda. Não corresponde a trabalho registado no sábado/domingo.'
    document['warnings'] = [w for w in document['warnings'] if w != warning]
    if any(e['included'] and e.get('allowance_basis') == WEEKEND for e in document['entries']):
        document['warnings'].append(warning)
