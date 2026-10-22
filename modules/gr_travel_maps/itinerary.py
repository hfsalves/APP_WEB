"""Deterministic calendar reconstruction over measured works and directed road legs."""
from __future__ import annotations

from copy import deepcopy
from datetime import timedelta
from decimal import Decimal, ROUND_CEILING

from . import allowances, engine, scheduled
from .config import TravelMapsError, map_bounds

D = Decimal
VERSION = 'autos-calendar-v2'
MAX_OPTIONS = 100
MAX_STATES = 1600


def edge(graph, a, b):
    return graph['edges'].get(f'{a}>{b}')


def tour(graph, path, policy, hours):
    legs = [edge(graph, a, b) for a, b in zip(path, path[1:])]
    if any(item is None for item in legs):
        return None
    km = sum((D(item['km']) for item in legs), D(0))
    times = [D(item['seconds']) for item in legs]
    maximum = D(hours)*3600
    if km <= 0 or any(t > maximum for t in times):
        return None
    splits = [i for i in range(1, len(legs)) if sum(times[:i]) <= maximum and sum(times[i:]) <= maximum]
    same_day = sum(times) <= maximum
    if policy == 'same_day' and not same_day or not same_day and not splits:
        return None
    if policy == 'later' and not splits:
        return None
    split = min(splits, key=lambda i: (abs(sum(times[:i])-sum(times[i:])), i)) if splits else None
    required = 2 if policy == 'later' or not same_day else 1
    return {'path': path, 'km': str(km), 'days': required, 'split': split,
            'local_legs': sum(a != 'home' and b != 'home' for a, b in zip(path, path[1:])),
            'round_trip': str(km)}


def search(options, target, slots):
    """Bounded repeated-tour subset sum. All amounts are integer hundredths of km."""
    target = D(target)*100
    if target <= 0 or not options or slots <= 0:
        return [], False
    sizes = [int(D(option['km'])*100) for option in options]
    ceiling = target + max(sizes)
    layers = [{0: ()}] + [{} for _ in range(slots)]
    best = (0, ()); truncated = False
    def rank(total, path):
        return (abs(total-target), total > target, sum(options[i]['local_legs'] for i in path), len(path), path)
    for used in range(slots+1):
        layer = layers[used]
        if len(layer) > MAX_STATES:
            truncated = True
            near = sorted(layer, key=lambda total: rank(total, layer[total]))
            low = sorted(layer)[:MAX_STATES//4]
            layer = {total: layer[total] for total in list(dict.fromkeys(low+near))[:MAX_STATES]}
            layers[used] = layer
        for total, path in layer.items():
            if rank(total, path) < rank(*best):
                best = (total, path)
            for index, option in enumerate(options):
                next_day, next_total = used+option['days'], total+sizes[index]
                if next_day > slots or next_total > ceiling:
                    continue
                proposed = path+(index,)
                old = layers[next_day].get(next_total)
                if old is None or rank(next_total, proposed) < rank(next_total, old):
                    layers[next_day][next_total] = proposed
    return [deepcopy(options[i]) for i in best[1]], truncated


def choose_tours(graph, target, slots, policy, hours):
    works = sorted(key for key in graph['locations'] if key != 'home')
    home = [option for key in works if (option := tour(graph, ['home', key, 'home'], policy, hours))]
    chosen, truncated = search(home, target, slots)
    initial_home = sum((D(item['km']) for item in chosen), D(0))
    warnings = []
    if chosen and initial_home == target:
        return chosen, truncated, warnings
    if chosen and target >= min(D(option['km']) for option in home):
        # A local detour is attached to the home trip that reaches A, never teleported in.
        extras = [option for a in works for b in works if a != b and
                  (option := tour(graph, ['home', a, b, a, 'home'], policy, hours))]
        residual = abs(target-initial_home)
        extras.sort(key=lambda item: (abs(D(item['km']) - target), item['km'], item['path']))
        # Also retain small detours useful for a small remaining PHC balance.
        small = sorted(extras, key=lambda item: (abs((D(item['km']) - D(edge(graph, 'home', item['path'][1])['km']) -
                          D(edge(graph, item['path'][1], 'home')['km'])) - residual), item['path']))
        extras = list({tuple(item['path']): item for item in small[:30]+extras[:MAX_OPTIONS]}.values())
        if len(home)+len(extras) > MAX_OPTIONS:
            truncated = True
        improved, cut = search(home+extras[:max(0, MAX_OPTIONS-len(home))], target, slots)
        truncated |= cut
        if improved:
            chosen = improved
    else:
        # Low payroll KM can represent only transfers between sites. Keep one base
        # for the whole sequence and explicitly disclose the assumed initial presence.
        candidates = []
        for a in works:
            options = [option for b in works if a != b and (option := tour(graph, [a, b, a], policy, hours))]
            if options:
                score = min(abs(target-D(o['km'])*max(1, min(slots//o['days'], int(target/D(o['km'])+D('.5'))))) for o in options)
                candidates.append((score, a, options))
        candidates.sort(key=lambda item: (item[0], item[1]))
        if len(candidates) > 8:
            truncated = True
        best_rank = (abs(target-initial_home), initial_home > target, len(chosen))
        for _, a, options in candidates[:8]:
            result, cut = search(options, target, slots); truncated |= cut
            total = sum((D(item['km']) for item in result), D(0))
            rank = (abs(target-total), total > target, len(result))
            if result and rank < best_rank:
                chosen, best_rank = result, rank
        if chosen and chosen[0]['path'][0] != 'home':
            label = graph['locations'][chosen[0]['path'][0]]['label']
            warnings.append(f'Presença inicial na obra {label} inferida. O percurso até essa obra não integra os quilómetros propostos; confirme como o trabalhador lá chegou.')
    return chosen, truncated, warnings


def distribute(tours, days, policy):
    if not tours:
        return []
    # Spread complete journeys through the month, without overlapping a delayed return.
    spare = len(days)-sum(item['days'] for item in tours)
    if policy == 'auto':
        for item in tours:
            if spare and item['days'] == 1 and item['split'] is not None:
                item['days'] = 2; spare -= 1
    used = sum(item['days'] for item in tours)
    gap = len(days)-used
    result, cursor = [], 0
    for i, item in enumerate(tours):
        offset = (gap*(i+1))//(len(tours)+1)
        start = cursor+offset
        assigned = days[start:start+item['days']]
        cursor += item['days']
        result.append((item, assigned))
    return result


def presence(legs, days):
    result = {}
    for day in sorted(days):
        if not legs[0].get('start_date', legs[0]['date']) <= day <= legs[-1]['date']:
            continue
        current = legs[0]['from_key']
        for leg in legs:
            if leg['date'] < day:
                current = leg['to_key']
        visited = {current}
        for leg in legs:
            if leg.get('driving_dates') and day in leg['driving_dates']:
                # Intermediate driving days have no invented overnight locality.
                visited = set()
                if day == leg['start_date']:
                    visited.add(leg['from_key'])
                if day == leg['end_date']:
                    visited.add(leg['to_key'])
                current = leg['to_key']
            elif leg['date'] == day:
                visited.update((leg['from_key'], leg['to_key'])); current = leg['to_key']
        result[day] = visited - {'home'}
    return result


def daily_allocation(quantity, dates):
    """Distribute hundredths of km exactly; these daily portions remain inferred."""
    units, remainder = divmod(int(D(quantity)*100), len(dates))
    return {day: str(D(units+(index < remainder))/100) for index, day in enumerate(dates)}


def build(payroll, batches, raw, graph, planning=None):
    if not isinstance(raw, dict):
        raise TravelMapsError('Pressupostos inválidos.')
    policy = raw.get('return_policy', 'auto')
    if policy not in ('auto', 'same_day', 'later'):
        raise TravelMapsError('Opção de regresso inválida.')
    hours = engine.number(raw.get('max_driving_hours', '10'), 'Horas máximas de condução por dia', '24')
    if hours < 1:
        raise TravelMapsError('Indique pelo menos uma hora de condução possível por dia.')
    available = engine.candidates(batches, planning); by_key = {work['key']: work for work in available}
    selections = [{'key': work['key'], 'country': graph['locations'].get(work['key'], {}).get('country', ''),
                   'city': graph['locations'].get(work['key'], {}).get('city') or work['locality'] or work['address']}
                  for work in available]
    home = graph['locations'].get('home', {})
    raw = {**raw, 'works': selections, 'note': raw.get('note') or 'Reconstrução automática a partir dos autos do mês e distâncias rodoviárias; datas e presença inferidas.'}
    if home:
        raw['origin'], raw['origin_country'] = home['address'], home['country']
    document = engine.build(payroll, batches, raw, max_works=99, available=available)
    document.update(mode='AUTOMATIC', engine_version=VERSION, routes=deepcopy(graph), journeys=[], entries=[])
    document['inputs'].update(return_policy=policy, max_driving_hours=str(hours), locations=deepcopy(raw.get('locations', {})))
    if planning is not None:
        document['planning'] = deepcopy(planning)
        document['engine_version'] = 'planning-calendar-v4'
        document['allowance_policy'] = allowances.POLICY
        document['warnings'] = [w for w in document['warnings'] if not w.startswith(('As datas e a associação', 'Calendário convencional', 'Calendário inclui'))]
        document['warnings'].extend(planning['warnings'])
    document['warnings'] = [w for w in document['warnings'] if 'total PHC' in w or not w.startswith(('Sem percursos', 'ac_estrangeiro:', 'ac_nacional:'))]
    document['warnings'].extend(graph['warnings'])
    if planning is None:
        document['warnings'].append('Obras candidatas durante o mês pela data dos autos; a atividade em cada dia e a distribuição das viagens são inferidas.')
    start, end = map_bounds(payroll)
    days = scheduled.allowed(document)
    employee = payroll['employee']; target = D(employee['phc']['km']['quantity'] or '0')
    assigned_tours = None
    if planning is not None:
        assigned_tours, truncated = scheduled.choose(graph, target, days, policy, hours, planning,
            set(document['inputs']['blocked_dates']) | set(planning['blocked_dates']))
        tours = [item for item, _ in assigned_tours]; warnings = []
        if tours and tours[0]['path'][0] != 'home':
            warnings.append('Proposta apenas entre obras: posição inicial apoiada no planeamento; o percurso desde casa e o meio de transporte continuam por confirmar.')
    else:
        tours, truncated, warnings = choose_tours(graph, target, len(days), policy, hours)
    # Group AC requiring another country/work at the end of the available month,
    # instead of inventing many isolated foreign stays between domestic trips.
    reserved = {}; travel_days = list(days)
    visited = {key for item in tours for key in item['path'] if key != 'home'}
    reference = document['inputs']['allowance_country']
    for category in (() if planning is not None else ('ac_estrangeiro', 'ac_nacional')):
        amount = D(employee['phc'][category]['quantity'] or '0')
        eligible = [item for item in selections if item['country'] and reference and
                    ((item['country'] != reference) if category == 'ac_estrangeiro' else (item['country'] == reference))]
        if amount > 0 and eligible and not visited.intersection(item['key'] for item in eligible):
            count = min(len(travel_days), int(amount.to_integral_value(rounding=ROUND_CEILING)))
            if count:
                for day in travel_days[-count:]:
                    reserved[day] = (category, eligible[0])
                travel_days = travel_days[:-count]
    if reserved:
        tours, cut, warnings = choose_tours(graph, target, len(travel_days), policy, hours)
        truncated |= cut
        document['warnings'].append('Dias de AC sem percurso KM compatível agrupados no fim do calendário disponível; permanência e deslocação até à obra continuam por confirmar.')
    document['warnings'].extend(warnings); document['search_truncated'] = truncated
    if truncated:
        document['warnings'].append('Pesquisa limitada de combinações: solução aproximada, sem garantia de ótimo.')
    occupied = {}; selections = {item['key']: item for item in document['inputs']['works']}
    for index, (item, assigned) in enumerate(assigned_tours if assigned_tours is not None else distribute(tours, travel_days, policy)):
        journey_id = engine.digest([item['path'], assigned, index])[:24]
        path = item['path']; split = item['split'] if len(assigned) == 2 else len(path)-1
        document['journeys'].append({'id': journey_id, 'path': path, 'outbound_date': assigned[0], 'return_date': assigned[-1],
                                    'base_inferred': path[0] != 'home', 'international_trip': item.get('international_trip', False)})
        work_keys = list(dict.fromkeys(key for key in path if key != 'home'))
        for leg_index, (a, b) in enumerate(zip(path, path[1:])):
            driving_dates = item.get('travel_windows', [])[leg_index] if item.get('travel_windows') else None
            day = driving_dates[-1] if driving_dates else assigned[0] if leg_index < split else assigned[-1]
            route = edge(graph, a, b); work_key = b if b != 'home' else a
            source_point, destination = graph['locations'][a], graph['locations'][b]
            entry = engine.make_entry('km', day, D(route['km']), by_key[work_key], selections[work_key], document['inputs'], employee)
            entry.update(id=engine.digest([journey_id, leg_index])[:24], journey_id=journey_id, leg_index=leg_index,
                         approximate_distance=any(point.get('precision') in ('RUA', 'LOCALIDADE', 'CODIGO_POSTAL') for point in (source_point, destination)),
                         from_key=a, to_key=b, work_keys=work_keys, origin=source_point['address'] or source_point['label'],
                         destination=destination['address'] or destination['label'], from_label=source_point['label'], to_label=destination['label'],
                         travel_type='ENTRE_OBRAS' if a != 'home' and b != 'home' else 'CASA_OBRA' if a == 'home' else 'REGRESSO_CASA',
                         reason=f"Deslocação proposta: {source_point['label']} → {destination['label']}.")
            entry['provenance'].update(distance=deepcopy(route), date={'kind': 'INFERIDO', 'rule': 'Viagens distribuídas pelo calendário; regresso ligado à ida.'},
                work={'kind': 'PLANEAMENTO' if planning is not None else 'AUTO_MEDICAO',
                      'references': [ref for key in work_keys for ref in (by_key[key].get('planning_refs') or [record['source'] for record in by_key[key]['evidence']])]},
                origin=deepcopy(document['inputs']['provenance']['origin']) if a == 'home' else
                    {'kind': 'PLANEAMENTO' if planning is not None else 'AUTO_MEDICAO', 'references': deepcopy(by_key[a].get('planning_refs') or [record['source'] for record in by_key[a]['evidence']])},
                geolocation={'from': deepcopy(source_point['source']), 'to': deepcopy(destination['source'])},
                country={'kind': graph['locations'][work_key]['source']['kind'], 'reference': deepcopy(graph['locations'][work_key]['source'])})
            if item.get('international_trip'):
                entry.update(hypothesis=True, hypothesis_reason='Viagem rodoviária entre a casa em Portugal e a obra no estrangeiro proposta para reconciliação; não existe registo desta viagem.')
            if driving_dates:
                entry.update(driving_dates=driving_dates, start_date=driving_dates[0], end_date=driving_dates[-1],
                             daily_km=daily_allocation(entry['quantity'], driving_dates))
                entry['provenance']['travel_days'] = {'kind': 'INFERIDO', 'dates': driving_dates,
                    'rule': 'Condução repartida por dias consecutivos dentro do limite diário; km repartidos uniformemente, sem localização de pernoita conhecida.'}
            document['entries'].append(entry)
    allowance_days = allowances.eligible(document) if planning is not None else {}
    presence_days = sorted(set(days) | set(allowance_days))
    for journey in document['journeys']:
        legs = [e for e in document['entries'] if e.get('journey_id') == journey['id']]
        for day, work_keys_at_day in presence(legs, presence_days).items():
            occupied[day] = {'journey': journey['id'], 'works': work_keys_at_day}
    # Reuse compatible travel days for AC, then spread the remaining AC over free days.
    used_ac = set()
    international_works = {key for item in tours if item.get('international_trip') for key in item['path'] if key != 'home'}
    for category in ('ac_estrangeiro', 'ac_nacional'):
        quantity = employee['phc'][category]['quantity']
        if quantity is None or D(quantity) <= 0:
            continue
        remaining = D(quantity); reference = document['inputs']['allowance_country']
        eligible = [s for s in selections.values() if s['country'] and reference and
                    ((s['country'] != reference) if category == 'ac_estrangeiro' else (s['country'] == reference))]
        compatible = [(day, next((s for s in eligible if s['key'] in occupied.get(day, {}).get('works', [])), None)) for day in days if day not in used_ac]
        fixed = [(day, selection) for day, (kind, selection) in sorted(reserved.items()) if kind == category]
        candidates = fixed + [(day, selection) for day, selection in compatible if selection and day not in reserved]
        free = [day for day in days if day not in used_ac and day not in occupied and day not in reserved]
        needed = max(0, int(remaining.to_integral_value(rounding=ROUND_CEILING))-len(candidates))
        if eligible and needed:
            for index in range(min(needed, len(free))):
                day = free[((2*index+1)*len(free))//(2*min(needed, len(free)))]
                candidates.append((day, eligible[index % len(eligible)]))
        if planning is not None:
            # Work dates first; inferred weekend stays may cover the remaining PHC days.
            candidates = [(day, next((s for s in eligible if s['key'] in allowance_days[day] and
                           (s['key'] not in international_works or day in occupied) and
                           (day not in occupied or s['key'] in occupied[day]['works'])), None)) for day in allowance_days if day not in used_ac]
            candidates = [(day, selection) for day, selection in candidates if selection]
            candidates.sort(key=lambda item: (allowance_days[item[0]][item[1]['key']]['basis'] == allowances.WEEKEND, item[0]))
        for day, selection in candidates:
            if remaining <= 0:
                break
            amount = min(D(1), remaining)
            entry = engine.make_entry(category, day, amount, by_key[selection['key']], selection, document['inputs'], employee)
            entry['provenance']['date'] = {'kind': 'INFERIDO', 'rule': 'Distribuição no calendário, compatível com os percursos propostos.'}
            entry['provenance']['country'] = {'kind': graph['locations'][selection['key']]['source']['kind'], 'reference': deepcopy(graph['locations'][selection['key']]['source'])}
            document['entries'].append(entry); remaining -= amount; used_ac.add(day)
        if remaining:
            document['warnings'].append(f'{category}: {remaining} dias por reconciliar, sem local/calendário compatível.')
    if target > 0 and not tours:
        document['warnings'].append('Sem combinação rodoviária possível para os quilómetros PHC com os locais e dias disponíveis.')
    document['entries'].sort(key=lambda e: (e['date'], e.get('journey_id', ''), e.get('leg_index', 0), e['category']))
    document['reconciliation'] = engine.summarize(document)
    # Preserve every used directed leg, plus all location results and source autos.
    # Unused matrix cells need not inflate each immutable map version.
    used_edges = {f"{e['from_key']}>{e['to_key']}" for e in document['entries'] if e['category'] == 'km'}
    document['routes']['edge_count_considered'] = len(graph['edges'])
    document['routes']['edges'] = {key: value for key, value in document['routes']['edges'].items() if key in used_edges}
    document['result'] = result_summary(document)
    if planning is not None:
        scheduled.annotate(document)
        if not planning['records']:
            document['result']['message'] = 'Sem datas e obras associadas à equipa deste trabalhador nas empresas selecionadas. Confirme o histórico das equipas e o planeamento.'
    check_entries(document)
    return document


def result_summary(document):
    graph = document['routes']; included = [entry for entry in document['entries'] if entry['included']]
    missing = len(graph['unresolved'])
    approximate = sum(point.get('precision') in ('RUA', 'LOCALIDADE', 'CODIGO_POSTAL') for point in graph['locations'].values())
    remaining = [kind for kind, value in document['reconciliation'].items() if value['difference'] is not None and D(value['difference']) != 0]
    positive = any(D(value['phc'] or '0') > 0 for value in document['reconciliation'].values())
    if not included and positive:
        status = 'BLOCKED'
        message = 'Não foi possível propor deslocações ou ajudas de custo.'
        if not graph['locations']:
            message += ' Nenhum local foi resolvido; confirme as moradas/códigos postais abaixo.'
        elif not graph['edges']:
            message += ' Sem percursos rodoviários ou obras com país compatível.'
        else:
            message += ' Sem combinação compatível com os quilómetros e o calendário.'
    elif not included:
        status, message = 'NO_MOVEMENTS', 'Não há quantidades PHC positivas para reconstruir neste período.'
    else:
        status = 'PARTIAL' if missing or approximate or remaining else 'PROPOSED'
        message = f'Proposta com {len(included)} troços/dias.'
    if approximate:
        message += f' {approximate} localizações aproximadas: os percursos exigem confirmação.'
    if missing:
        message += f' {missing} locais por resolver, excluídos do cálculo.'
    return {'status': status, 'message': message, 'entries': len(included),
            'unresolved_locations': missing, 'approximate_locations': approximate,
            'categories_unreconciled': remaining}


def check_entries(document, validating=False):
    start, end = map_bounds(document['payroll'])
    days = set(scheduled.allowed(document))
    ac_days = set(allowances.eligible(document)) if document.get('planning') is not None else days
    if document.get('planning') is not None:
        scheduled.check(document)
    groups, ac = {}, {}
    for entry in document['entries']:
        if not entry['included']:
            continue
        if entry['date'] not in (days if entry['category'] == 'km' else ac_days):
            raise TravelMapsError('Uma linha está fora dos dias permitidos do período do mapa.')
        if entry.get('driving_dates') and (any(day not in days for day in entry['driving_dates']) or
                entry.get('daily_km') != daily_allocation(entry['quantity'], entry['driving_dates'])):
            raise TravelMapsError('Distribuição diária da viagem incoerente; reconstrua a proposta.')
        if validating and (not entry['reason'] or entry['rate'] is None or not entry['country'] or not entry['city']):
            raise TravelMapsError('Complete motivo, local, país e taxa antes de validar.')
        if entry['category'] == 'km':
            groups.setdefault(entry['journey_id'], []).append(entry)
            if validating and (not entry['origin'] or not entry['vehicle'] or not entry['owner']):
                raise TravelMapsError('Indique origem, matrícula e proprietário antes de validar quilómetros.')
        else:
            if entry['date'] in ac:
                raise TravelMapsError('Existem ajudas de custo sobrepostas.')
            ac[entry['date']] = entry
    busy = {}; base = None
    international_presence = {}
    international_works = {key for journey in document['journeys'] if journey.get('international_trip') and groups.get(journey['id'])
                           for key in journey['path'] if key != 'home'}
    for journey in document['journeys']:
        legs = sorted(groups.get(journey['id'], []), key=lambda e: e['leg_index'])
        if not legs:
            continue
        if len(legs) != len(journey['path'])-1:
            raise TravelMapsError('Uma viagem tem troços em falta. Exclua ou reponha a viagem completa.')
        if any(e['from_key'] != journey['path'][i] or e['to_key'] != journey['path'][i+1] for i, e in enumerate(legs)):
            raise TravelMapsError('Os troços da viagem não são contínuos.')
        if any(b['date'] < a['date'] for a, b in zip(legs, legs[1:])):
            raise TravelMapsError('Um regresso não pode preceder a ida.')
        if base is not None and journey['path'][0] != base:
            raise TravelMapsError('Viagens com pontos de partida incompatíveis.')
        base = journey['path'][0]
        seconds = {}
        for entry in legs:
            dates = entry.get('driving_dates', [entry['date']])
            for day in dates:
                seconds[day] = seconds.get(day, D(0))+D(entry['provenance']['distance']['seconds'])/len(dates)
        if any(value > D(document['inputs']['max_driving_hours'])*3600 for value in seconds.values()):
            raise TravelMapsError('Um dia excede o limite de horas de condução.')
        for day, work_keys_at_day in presence(legs, days | ac_days).items():
            if journey.get('international_trip'):
                international_presence.setdefault(day, set()).update(work_keys_at_day)
            if legs[0].get('start_date', legs[0]['date']) <= day <= legs[-1]['date']:
                if day in busy:
                    raise TravelMapsError('Há outra viagem antes do regresso da anterior.')
                busy[day] = journey['id']
                if day in ac and ac[day]['work_key'] not in work_keys_at_day:
                    raise TravelMapsError('Ajuda de custo incompatível com a viagem nesse dia.')
    for day, entry in ac.items():
        if entry['work_key'] in international_works and entry['work_key'] not in international_presence.get(day, set()):
            raise TravelMapsError('Ajuda de custo fora da permanência proposta na viagem internacional.')


def calendar(document):
    start, end = map_bounds(document['payroll'])
    allowed = set(scheduled.allowed(document))
    ac_allowed = set(allowances.eligible(document)) if document.get('planning') is not None else allowed
    result = []
    for offset in range((end-start).days):
        day = start+timedelta(days=offset); iso = day.isoformat()
        entries = [entry for entry in document['entries'] if iso in entry.get('driving_dates', [entry['date']])]
        result.append({'date': iso, 'available': iso in allowed, 'allowance_available': iso in ac_allowed, 'entries': entries,
                       'km': str(sum((D(e.get('daily_km', {}).get(iso, e['quantity'])) for e in entries if e['included'] and e['category'] == 'km'), D(0)))})
    return result
