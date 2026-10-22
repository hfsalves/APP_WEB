"""Calendar-constrained travel proposals from dated employee/team assignments."""
from copy import deepcopy
from datetime import date, timedelta
from decimal import Decimal, ROUND_CEILING

from .config import TravelMapsError

D = Decimal
MAX_STATES = 1600
MAX_OPTIONS_PER_DAY = 80


def assignments(planning):
    result = {}
    for row in planning['records']:
        result.setdefault(row['date'], set()).add(row['work_key'])
    return result


def extra_assignments(planning):
    result = {}
    for row in planning.get('extra_records', []):
        result.setdefault(row['date'], set()).add(row['work_key'])
    return result


def hypothetical(path, dates, planning):
    own = {w['key'] for w in planning['works']}
    return any(key != 'home' and key not in own for key in path)


def allowed(document):
    from . import engine
    from .config import map_bounds
    start, end = map_bounds(document['payroll'])
    excluded = set(document['inputs']['blocked_dates'])
    if document.get('planning') is not None:
        excluded.update(document['planning']['blocked_dates'])
        # A dated assignment is usable on a weekend too; there is no need to invent dates.
        return sorted(day for day in assignments(document['planning']) if start.isoformat() <= day < end.isoformat() and day not in excluded)
    return engine.calendar_days(start, end, excluded, document['inputs'].get('include_weekends', False))


def compatible(path, dates, split, planning, excluded):
    """Require each arrival at work on its recorded day; no relocation across gaps."""
    daily = assignments(planning)
    start, end = dates[0], dates[-1]
    if any(start <= day <= end for day in excluded):
        return False
    possible = daily
    if hypothetical(path, dates, planning):
        # Extra-team visits are hypotheses for a single day, returning to the worker's work.
        if start != end or len(path) not in (3, 5):
            return False
        base = path[0] if len(path) == 3 else path[1]
        if base not in daily.get(start, set()) or (path[-1] if len(path)==3 else path[-2]) != base:
            return False
        possible = {**daily, start: daily.get(start, set()) | extra_assignments(planning).get(start, set())}
    legs = [(a, b, start if index < split else end) for index, (a, b) in enumerate(zip(path, path[1:]))]
    for a, b, day in legs:
        if b != 'home' and b not in possible.get(day, set()):
            return False
        if b == 'home' and a not in daily.get(day, set()):
            return False
    if path[0] != 'home' and path[0] not in daily.get(start, set()):
        # A work-to-work departure can start from the immediately preceding assignment.
        previous = max((day for day in daily if day < start), default=None)
        if previous is None or path[0] not in daily[previous] or any(previous <= day <= start for day in excluded):
            return False
        cursor = date.fromisoformat(previous) + timedelta(days=1)
        while cursor.isoformat() < start:
            if cursor.weekday() < 5 and cursor.isoformat() not in daily:
                return False
            cursor += timedelta(days=1)
    if start != end:
        stay = path[split]
        cursor = date.fromisoformat(start) + timedelta(days=1)
        while cursor.isoformat() < end:
            day = cursor.isoformat()
            if (day in daily and daily[day] != {stay}) or (cursor.weekday() < 5 and day not in daily):
                return False
            cursor += timedelta(days=1)
    return True


def choose(graph, target, days, policy, hours, planning, excluded):
    from .itinerary import tour
    daily = assignments(planning)
    extras = extra_assignments(planning)
    indexed = {day: index for index, day in enumerate(days)}
    by_day = {day: [] for day in days}
    truncated = False
    for day in days:
        works = sorted(daily[day] & graph['locations'].keys())
        previous = max((d for d in daily if d < day), default=None)
        bases = sorted((daily.get(previous, set()) | daily[day]) & graph['locations'].keys())
        paths = [['home', a, 'home'] for a in works]
        paths += [['home', a, b, a, 'home'] for a in works for b in works if a != b]
        paths += [[a, b, a] for a in bases for b in works if a != b]
        paths += [[a, b, a] for a in works for b in sorted(extras.get(day, set()) & graph['locations'].keys()) if a != b]
        paths += [['home', a, b, a, 'home'] for a in works for b in sorted(extras.get(day, set()) & graph['locations'].keys()) if a != b]
        for path in paths:
            item = tour(graph, path, policy, hours)
            if not item:
                continue
            item['international_trip'] = international(graph, path)
            if policy != 'later' and item['days'] == 1 and compatible(path, [day], len(path)-1, planning, excluded):
                by_day[day].append((item, [day]))
            if policy != 'same_day' and item['split'] is not None:
                for last in days[indexed[day]+1:]:
                    if compatible(path, [day, last], item['split'], planning, excluded):
                        by_day[day].append((item, [day, last]))
        if policy != 'same_day':
            by_day[day].extend(international_options(graph, day, days, hours, planning, excluded))
        # Deterministic caps retain both low-cost and near-target options.
        options = by_day[day]
        if len(options) > MAX_OPTIONS_PER_DAY:
            truncated = True
            low = sorted(options, key=lambda x: (D(x[0]['km']), x[1], x[0]['path']))[:20]
            near = sorted(options, key=lambda x: (abs(D(x[0]['km'])-target),
                          indexed[x[1][0]]-indexed[x[1][-1]] if x[0].get('international_trip') else 0, x[1], x[0]['path']))
            unique = {}
            for item, dates in low + near:
                unique.setdefault((tuple(item['path']), tuple(dates)), (item, dates))
            by_day[day] = list(unique.values())[:MAX_OPTIONS_PER_DAY]
    # One route per day/interval. Track the journey base to prevent teleportation.
    layers = [dict() for _ in range(len(days)+1)]
    layers[0][(0, '')] = ()
    target_units = int(target*100)
    maximum = max((int(D(item['km'])*100) for options in by_day.values() for item, _ in options), default=0)

    def rank(total, path):
        # Equivalent solutions favour few visits, spread over the eligible dates.
        spread = sum(abs(indexed[dates[0]]*2*len(path) - (2*i+1)*len(days))
                     for i, (_, dates) in enumerate(path))
        uncovered = sum(indexed[dates[0]] + len(days)-1-indexed[dates[-1]]
                        for item, dates in path if item.get('international_trip'))
        return (abs(total-target_units), total > target_units,
                sum(item['local_legs'] for item, _ in path), len(path), uncovered, spread,
                tuple((tuple(dates), tuple(item['path'])) for item, dates in path))

    def retain(layer, key, path):
        if key not in layer or rank(key[0], path) < rank(key[0], layer[key]):
            layer[key] = path

    for index, day in enumerate(days):
        layer = layers[index]
        if len(layer) > MAX_STATES:
            truncated = True
            near = sorted(layer, key=lambda key: rank(key[0], layer[key]))
            low = sorted(layer)[:MAX_STATES//4]
            layer = {key: layer[key] for key in list(dict.fromkeys(low+near))[:MAX_STATES]}
        for (total, base), chosen in layer.items():
            retain(layers[index+1], (total, base), chosen)
            for item, dates in by_day[day]:
                if base and base != item['path'][0]:
                    continue
                amount = total + int(D(item['km'])*100)
                if amount <= target_units + maximum:
                    retain(layers[indexed[dates[-1]]+1], (amount, item['path'][0]), chosen+((item, dates),))
    last = layers[-1]
    best = min(last, key=lambda key: rank(key[0], last[key]))
    return deepcopy(list(last[best])), truncated


def international(graph, path):
    return path[0] == 'home' and graph['locations'].get('home', {}).get('country') == 'PT' and any(
        graph['locations'][key].get('country') not in ('', 'PT', None) for key in path if key != 'home')


def international_options(graph, day, days, hours, planning, excluded):
    """Long road legs use consecutive travel days, without inventing overnight places."""
    from .itinerary import edge
    daily = assignments(planning)
    result = []
    for work in sorted(daily[day] & graph['locations'].keys()):
        path = ['home', work, 'home']
        if not international(graph, path):
            continue
        routes = [edge(graph, a, b) for a, b in zip(path, path[1:])]
        if any(route is None for route in routes):
            continue
        counts = [max(1, int((D(route['seconds'])/(D(hours)*3600)).to_integral_value(rounding=ROUND_CEILING))) for route in routes]
        if max(counts) <= 1 or sum(counts) > len(days):
            continue
        def window(start, count):
            return [(date.fromisoformat(start)+timedelta(days=i)).isoformat() for i in range(count)]
        outbound = window(day, counts[0])
        if any(work not in daily.get(d, set()) or d not in days for d in outbound):
            continue
        for return_start in days:
            if return_start <= outbound[-1]:
                continue
            inbound = window(return_start, counts[1])
            if any(work not in daily.get(d, set()) or d not in days for d in inbound):
                continue
            dates = [outbound[0], inbound[-1]]
            if not compatible(path, dates, 1, planning, excluded):
                continue
            km = str(sum((D(route['km']) for route in routes), D(0)))
            result.append(({'path': path, 'km': km, 'round_trip': km, 'days': sum(counts), 'split': 1,
                            'local_legs': 0, 'international_trip': True, 'travel_windows': [outbound, inbound]}, dates))
    return result


def annotate(document, *, preserve_declared=False):
    from . import allowances
    planning = document['planning']
    for entry in document['entries']:
        refs = [row for row in planning['records'] if row['date'] in entry.get('driving_dates', [entry['date']]) and
                row['work_key'] in entry.get('work_keys', [entry['work_key']])]
        entry['provenance']['employee_assignment'] = {'kind': 'PLANEAMENTO', 'references': deepcopy(refs),
            'rule': 'Trabalhador por origem/número, equipa no período e obra na data registada; presença individual por confirmar.'}
        if not preserve_declared or entry['provenance']['date'].get('kind') != 'DECLARADO':
            entry['provenance']['date'] = {'kind': 'INFERIDO', 'references': deepcopy(refs),
                'rule': 'Data da viagem proposta dentro das datas de afetação da equipa à obra.'}
        entry['confidence'] = {'level': 'MEDIA', 'reason': 'Obra e data apoiadas no planeamento da equipa; percurso, meio de transporte e presença individual sujeitos a confirmação.'}
        extra_refs = [row for row in planning.get('extra_records', []) if row['date'] == entry['date'] and
                      row['work_key'] in entry.get('work_keys', [entry['work_key']])]
        if extra_refs:
            entry['hypothesis'] = True
            entry['hypothesis_reason'] = 'Visita proposta a obra de outra equipa; sem registo de presença deste trabalhador.'
            entry['provenance']['employee_assignment'] = {'kind': 'INFERIDO', 'rule': entry['hypothesis_reason'],
                'own_team_references': deepcopy(refs), 'other_team_references': deepcopy(extra_refs)}
            entry['confidence'] = {'level': 'BAIXA', 'reason': entry['hypothesis_reason']}
            if not preserve_declared or entry['provenance'].get('reason', {}).get('kind') != 'DECLARADO':
                entry['reason'] = f"Visita proposta a outra obra: {entry.get('from_label', '')} → {entry.get('to_label', '')}. Presença por confirmar."
        if entry.get('hypothesis'):
            entry['confidence'] = {'level': 'BAIXA', 'reason': entry['hypothesis_reason']}
    warning = 'O planeamento sustenta equipa, obra e data. Não comprova a deslocação, a utilização de viatura própria ou o direito a ajuda de custo.'
    if warning not in document['warnings']:
        document['warnings'].append(warning)
    if any(e.get('hypothesis') and e['included'] for e in document['entries']):
        warning = 'Há deslocações hipotéticas sem registo da viagem ou da presença noutra equipa. Confirme que ocorreram antes de validar; caso contrário, exclua-as.'
        if warning not in document['warnings']:
            document['warnings'].append(warning)
    allowances.annotate(document, preserve_declared=preserve_declared)


def check(document):
    from . import allowances
    planning = document['planning']
    daily = assignments(planning)
    ac_days = allowances.eligible(document)
    excluded = set(document['inputs']['blocked_dates']) | set(planning['blocked_dates'])
    for entry in document['entries']:
        if entry['included'] and entry['category'] != 'km' and entry['work_key'] not in ac_days.get(entry['date'], {}):
            raise TravelMapsError('Ajuda de custo sem trabalho registado ou permanência de fim de semana compatível com o planeamento, as ausências e as deslocações.')
    for journey in document['journeys']:
        legs = sorted((e for e in document['entries'] if e['included'] and e.get('journey_id') == journey['id']), key=lambda e: e['leg_index'])
        if not legs:
            continue
        if any(e.get('driving_dates') for e in legs):
            if journey['path'][0] != 'home' or len(legs) != 2 or journey['path'][-1] != 'home':
                raise TravelMapsError('Intervalo de viagem internacional inválido.')
            work = journey['path'][1]
            for leg in legs:
                dates = leg.get('driving_dates', [])
                if not dates or dates != sorted(set(dates)) or leg['date'] != dates[-1] or leg['start_date'] != dates[0] or leg['end_date'] != dates[-1]:
                    raise TravelMapsError('Datas de condução incoerentes; reconstrua a viagem.')
                if any(work not in daily.get(day, set()) or day in excluded for day in dates) or any(
                    date.fromisoformat(b)-date.fromisoformat(a) != timedelta(days=1) for a, b in zip(dates, dates[1:])):
                    raise TravelMapsError('A viagem atravessa datas sem associação à obra ou dias excluídos.')
            if legs[0]['end_date'] >= legs[1]['start_date'] or not compatible(journey['path'], [legs[0]['start_date'], legs[1]['end_date']], 1, planning, excluded):
                raise TravelMapsError('Ida e regresso incompatíveis com o calendário da obra.')
            continue
        dates = sorted({e['date'] for e in legs})
        if len(dates) > 2:
            raise TravelMapsError('Uma viagem tem mais de duas datas de deslocação.')
        split = sum(e['date'] == dates[0] for e in legs)
        if not compatible(journey['path'], dates, split, planning, excluded):
            raise TravelMapsError('Viagem incompatível com as obras e datas do planeamento da equipa.')
