"""Authorized orchestration: read current PHC/autos, snapshot, infer, append a version."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone

from models import db
from . import engine, service, store
from .config import TravelMapsError, period_bounds


def database():
    # The application's routed session chooses client/GR360_CORE; db.engine is
    # the legacy default and must never be used here.
    result = db.session.get_bind()
    store.require_schema(result)
    return result


def actor(user):
    return engine.text(str(getattr(user, 'LOGIN', '') or ''), 'Utilizador', 100, True)


def measurement_companies(raw, employer, user):
    if raw is None:
        raw = [employer]
    if not isinstance(raw, list) or not raw or len(raw) > 8:
        raise TravelMapsError('Selecione entre uma e oito empresas de autos.')
    result = []
    for feid in raw:
        company = service.company_for_user(feid, user)
        if company['feid'] not in result:
            result.append(company['feid'])
    return sorted(result)


def payroll_snapshot(feid, year, month, employee_key, user):
    panel = service.monthly_panel(feid, year, month, user)
    employee = next((row for row in panel['rows'] if row['key'] == employee_key), None)
    if employee is None:
        raise store.NotFound('O trabalhador não tem recibo neste período e empresa.')
    return {key: panel[key] for key in ('company', 'year', 'month', 'read_at', 'mapping', 'period_basis')} | {
        'employee': employee, 'warnings': panel['warnings']}


def payroll_fingerprint(payroll):
    employee = deepcopy(payroll['employee'])
    employee['lines'].sort(key=lambda row: row['source']['stamp'])
    employee['receipts'].sort(key=lambda row: row['PRSTAMP'])
    return engine.digest({'company': payroll['company'], 'year': payroll['year'], 'month': payroll['month'],
                          'mapping': payroll['mapping'], 'employee': employee})


def authorize(saved, user):
    header = saved['header']
    service.company_for_user(header['feid'], user)
    for batch in saved['current']['document']['measurements']:
        service.company_for_user(batch['company']['feid'], user)
    return saved


def visible_history(db_engine, map_id, user):
    result = []
    for item in store.history(db_engine, map_id):
        try:
            authorize(store.get(db_engine, map_id, item['version']), user)
        except TravelMapsError as exc:
            if exc.status_code == 403:
                continue
            raise
        result.append(item)
    return result


def context(feid, year, month, employee_key, companies, user):
    company = service.company_for_user(feid, user)
    start, _ = period_bounds(year, month)
    employee_key = engine.text(employee_key, 'Trabalhador', 250, True)
    # Read-only PHC remains usable until the explicit migration has been deployed.
    db_engine = db.session.get_bind()
    installed = store.ready(db_engine)
    identity = {'feid': company['feid'], 'phc_db': company['phc_db'], 'employee_key': employee_key,
                'year': start.year, 'month': start.month}
    saved = store.find(db_engine, identity) if installed else None
    if saved:
        authorize(saved, user)
        if companies is None:
            companies = [batch['company']['feid'] for batch in saved['current']['document']['measurements']]
    source_warnings = []
    try:
        payroll = payroll_snapshot(feid, year, month, employee_key, user)
    except TravelMapsError as exc:
        if saved is None or exc.status_code == 403:
            raise
        payroll = deepcopy(saved['current']['document']['payroll'])
        source_warnings.append('PHC atual indisponível. São apresentados os valores históricos guardados. ' + str(exc))
    ids = measurement_companies(companies, company['feid'], user)
    try:
        batches = [service.monthly_measurements(company, year, month, user) for company in ids]
    except TravelMapsError as exc:
        if saved is None or exc.status_code == 403:
            raise
        batches = deepcopy(saved['current']['document']['measurements'])
        ids = [batch['company']['feid'] for batch in batches]
        source_warnings.append('Autos atuais indisponíveis. São apresentadas as evidências históricas guardadas. ' + str(exc))
    return {'payroll': payroll, 'works': engine.candidates(batches), 'measurement_companies': ids,
            'sources_current': not source_warnings, 'source_warnings': source_warnings,
            'storage_ready': installed, 'saved': saved,
            'history': visible_history(db_engine, saved['header']['id'], user) if saved else []}


def list_month(feid, year, month, user):
    start, _ = period_bounds(year, month)
    company = service.company_for_user(feid, user)
    db_engine = database()
    result = []
    for saved in store.monthly(db_engine, company['feid'], start.year, start.month):
        # Only return information after checking every evidence-company ACL.
        try:
            authorize(saved, user)
        except TravelMapsError as exc:
            if exc.status_code == 403:
                result.append({'employee_key': saved['header']['employee_key'], 'restricted': True})
                continue
            raise
        version = saved['current']
        result.append({'id': saved['header']['id'], 'employee_key': saved['header']['employee_key'],
                       'employee_name': version['document']['payroll']['employee']['name'],
                       'employee_number': version['document']['payroll']['employee']['number'],
                       'version': version['version'], 'state': version['state'],
                       'snapshot_phc': version['document']['payroll']['employee']['phc'],
                       'reconciliation': version['document']['reconciliation']})
    return {'rows': result, 'company': service.public_company(company), 'year': start.year, 'month': start.month}


def detail(map_id, user, version=None):
    db_engine = database()
    # Authorization always uses latest evidence as well as the requested historical version.
    authorize(store.get(db_engine, map_id), user)
    saved = authorize(store.get(db_engine, map_id, version), user)
    return {**saved, 'history': visible_history(db_engine, map_id, user)}


def save(db_engine, document, payload, user, action, state):
    reason = engine.text(payload.get('reason', ''), 'Motivo da operação', 1000, True)
    saved = store.append(db_engine, document, action=action, state=state, actor=actor(user),
                        user_stamp=str(getattr(user, 'USSTAMP', '') or '')[:25], reason=reason,
                        expected_version=payload.get('expected_version'), request_id=payload.get('request_id'),
                        request_hash=engine.digest({'action': action, 'payload': payload}))
    return authorize(saved, user)


def generate(payload, user):
    # Establish company scope before touching the persistence layer.
    service.company_for_user(payload.get('feid'), user)
    db_engine = database()
    payroll = payroll_snapshot(payload.get('feid'), payload.get('year'), payload.get('month'), payload.get('employee_key'), user)
    previous = store.find(db_engine, store.scope(payroll))
    if previous:
        authorize(previous, user)
    ids = measurement_companies(payload.get('measurement_companies'), payroll['company']['feid'], user)
    batches = [service.monthly_measurements(company, payroll['year'], payroll['month'], user) for company in ids]
    document = engine.build(payroll, batches, payload.get('inputs'))
    document['assumptions_by'] = actor(user)
    document['warnings'] = list(dict.fromkeys([*document['warnings'], *payroll['employee']['warnings']]))
    return save(db_engine, document, payload, user, 'GENERATE', 'POR_VALIDAR')


def ensure_sources_current(document, user):
    original = document['payroll']
    current = payroll_snapshot(original['company']['feid'], original['year'], original['month'], original['employee']['key'], user)
    if payroll_fingerprint(current) != payroll_fingerprint(original):
        raise store.Conflict('O PHC mudou desde esta proposta. Gere uma nova versão antes de validar.')
    used = {entry['work_key'] for entry in document['entries'] if entry['included']}
    relevant = [work for work in engine.candidates(document['measurements']) if work['key'] in used]
    batches = [service.monthly_measurements(batch['company']['feid'], original['year'], original['month'], user)
               for batch in document['measurements']]
    actual = {work['key']: work for work in engine.candidates(batches)}
    for work in relevant:
        # Additional autos need not invalidate a proposal; original references must still match.
        records = {record['bostamp']: record for record in actual.get(work['key'], {}).get('evidence', [])}
        if any(engine.digest(records.get(record['bostamp'])) != engine.digest(record) for record in work['evidence']):
            raise store.Conflict('Um auto usado na proposta mudou ou deixou de ter medição positiva. Gere uma nova versão.')


def change(map_id, payload, user, action):
    db_engine = database()
    saved = authorize(store.get(db_engine, map_id), user)
    retry = store.replay(db_engine, payload.get('request_id'),
        engine.digest({'action': action, 'payload': {**payload, 'map_id': map_id}}), actor(user), map_id)
    if retry:
        return authorize(retry, user)
    if payload.get('expected_version') != saved['header']['version']:
        raise store.Conflict('Existe uma versão mais recente. Atualize antes de gravar.')
    # Verify the complete chain before adding a human decision to it.
    store.history(db_engine, map_id)
    document = saved['current']['document']
    note = engine.text(payload.get('reason', ''), 'Motivo da operação', 1000, True)
    if action == 'EDIT':
        document = engine.edit(document, payload.get('changes'), actor(user), note)
        state = 'POR_VALIDAR'
    elif action == 'VALIDATE':
        if saved['current']['state'] != 'POR_VALIDAR':
            raise store.Conflict('Só pode validar uma proposta por validar.')
        if payload.get('acknowledge_inference') is not True:
            raise TravelMapsError('Confirme explicitamente que reviu as inferências e as diferenças.')
        if not any(entry['included'] for entry in document['entries']):
            raise TravelMapsError('Não existem linhas incluídas para validar.')
        if any(value['phc'] is not None and engine.D(value['phc']) < 0 for value in document['reconciliation'].values()):
            raise TravelMapsError('Resolva as regularizações com total negativo antes de validar.')
        engine.check_entries(document, validating=True)
        ensure_sources_current(document, user)
        document = deepcopy(document)
        document['validation'] = {'actor': actor(user), 'user_stamp': str(getattr(user, 'USSTAMP', '') or ''),
            'at': datetime.now(timezone.utc).isoformat(), 'reason': note,
            'scope': [key for key in engine.CATEGORIES if document['payroll']['employee']['phc'][key]['quantity'] is not None],
            'acknowledge_inference': True}
        for entry in document['entries']:
            entry['validation_state'] = 'VALIDADO' if entry['included'] else 'REJEITADO'
            # Evidence stays INFERIDO, regardless of approval and numeric reconciliation.
        state = 'VALIDADO'
    elif action == 'REJECT':
        document = deepcopy(document)
        document['validation'] = None
        for entry in document['entries']:
            entry['validation_state'] = 'REJEITADO'
        state = 'REJEITADO'
    else:
        raise TravelMapsError('Operação desconhecida.')
    return save(db_engine, document, {**payload, 'map_id': map_id}, user, action, state)
