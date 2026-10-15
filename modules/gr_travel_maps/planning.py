"""Read dated team assignments without importing/initializing the legacy app."""
from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime, timezone, timedelta

import pyodbc
from flask import current_app

from modules.gr_planning.service import _build_hsols_master_config
from . import engine, service, sources
from .config import SourceUnavailable, TravelMapsError, period_bounds


@contextmanager
def reader():
    conn = None
    try:
        conn = pyodbc.connect(_build_hsols_master_config().as_odbc_string(), timeout=10,
                              autocommit=False, attrs_before={101: 1})
        conn.timeout = 25
        yield conn.cursor()
    except pyodbc.Error as exc:
        current_app.logger.warning('Mapas: planeamento indisponível (SQLSTATE %s).', str(exc.args[0])[:5])
        raise SourceUnavailable('Não foi possível ler as equipas e o planeamento. Tente novamente.') from None
    finally:
        if conn is not None:
            try:
                conn.rollback()
            finally:
                conn.close()


def read_rows(payroll):
    start, end = period_bounds(payroll['year'], payroll['month'])
    employee = payroll['employee']
    if not employee['identity_resolved']:
        raise TravelMapsError('Resolva a identidade PHC antes de consultar a equipa.')
    with reader() as cursor:
        memberships = sources.rows(cursor, """
            SELECT U_TEAMSTAMP, FREFSTAMP, FREF, NO, ORIGEM, DATAINI, DATAFIM, AUSENTE
            FROM dbo.U_TEAM WHERE NO = ? AND UPPER(LTRIM(RTRIM(ORIGEM))) = UPPER(?)
              AND CAST(DATAINI AS date) < ?
              AND (DATAFIM IS NULL OR CAST(DATAFIM AS date) = '19000101' OR CAST(DATAFIM AS date) >= ?)
            ORDER BY U_TEAMSTAMP
        """, (employee['number'], payroll['company']['phc_db'], end, start))
        assignments = sources.rows(cursor, """
            SELECT P.U_PLANOSTAMP, P.DATA, P.FREF, P.PROCESSO, T.U_TEAMSTAMP,
                   W.OPCSTAMP, W.WORK_MATCHES
            FROM dbo.U_TEAM T JOIN dbo.U_PLANO P ON P.FREF = T.FREF
              AND P.DATA >= CAST(T.DATAINI AS date)
              AND (T.DATAFIM IS NULL OR CAST(T.DATAFIM AS date) = '19000101' OR P.DATA <= CAST(T.DATAFIM AS date))
            OUTER APPLY (SELECT COUNT(*) AS WORK_MATCHES,
                CASE WHEN COUNT(*)=1 THEN MAX(O.OPCSTAMP) END AS OPCSTAMP
                FROM dbo.OPC O WHERE O.PROCESSO = P.PROCESSO) W
            WHERE T.NO = ? AND UPPER(LTRIM(RTRIM(T.ORIGEM))) = UPPER(?)
              AND P.DATA >= ? AND P.DATA < ?
            ORDER BY P.DATA, P.U_PLANOSTAMP, T.U_TEAMSTAMP
        """, (employee['number'], payroll['company']['phc_db'], start, end))
        other_assignments = sources.rows(cursor, """
            SELECT P.U_PLANOSTAMP, P.DATA, P.FREF, P.PROCESSO, W.OPCSTAMP, W.WORK_MATCHES
            FROM dbo.U_PLANO P OUTER APPLY (SELECT COUNT(*) AS WORK_MATCHES,
                CASE WHEN COUNT(*)=1 THEN MAX(O.OPCSTAMP) END AS OPCSTAMP
                FROM dbo.OPC O WHERE O.PROCESSO=P.PROCESSO) W
            WHERE P.DATA >= ? AND P.DATA < ? ORDER BY P.DATA,P.U_PLANOSTAMP
        """, (start, end))
        # U_AUSENCIAS has no company key. Only use it if the number is globally unique.
        identities = sources.rows(cursor, 'SELECT BDADOS, PESTAMP FROM dbo.V_PE WHERE NO = ?', (employee['number'],))
        absence_identity = len(identities) == 1 and service.clean(identities[0]['BDADOS']).upper() == payroll['company']['phc_db'].upper() and service.clean(identities[0]['PESTAMP']) == employee['pestamp']
        absences = sources.rows(cursor, """SELECT U_AUSENCIASSTAMP, DATAINI, DATAFIM FROM dbo.U_AUSENCIAS
            WHERE NO = ? AND CAST(DATAINI AS date) < ? AND CAST(DATAFIM AS date) >= ?
            ORDER BY U_AUSENCIASSTAMP""", (employee['number'], end, start)) if absence_identity else []
    return {'memberships': memberships, 'assignments': assignments, 'other_assignments': other_assignments, 'absences': absences,
            'absence_identity_unique': absence_identity}


def serial(row):
    return {key: service.original(value) for key, value in row.items()}


def ref(table, stamp):
    return {'database': 'HSOLS_MASTER', 'table': table, 'stamp': service.clean(stamp)}


def snapshot(payroll, batches, user):
    data = read_rows(payroll)
    stamps = sorted({service.clean(row['OPCSTAMP']) for row in data['assignments'] + data.get('other_assignments', []) if row['OPCSTAMP']})
    catalogs = []
    for batch in batches:
        company = service.company_for_user(batch['company']['feid'], user)
        catalogs.append({'company': service.public_company(company), 'rows': sources.planned_work_rows(company, stamps)})
    return assemble(payroll, batches, data, catalogs)


def assemble(payroll, batches, data, catalogs):
    """Only explicit employee origin and OPC stamps can join separate PHC bases."""
    clean = service.clean
    memberships = {clean(row['U_TEAMSTAMP']): row for row in data['memberships']}
    matches = {}
    for catalog in catalogs:
        for row in catalog['rows']:
            matches.setdefault(clean(row['OPCSTAMP']), []).append((catalog['company'], row))
    works, records, blocked, warnings = {}, [], {}, []
    all_dates = {}
    for row in data['assignments']:
        day = service.original(row['DATA'])[:10]
        all_dates.setdefault(day, set()).add(clean(row['FREF']))
    # Overlapping team memberships on a day are unresolved, not multiple visits.
    for day, teams in all_dates.items():
        if len(teams) > 1:
            blocked[day] = 'Associação simultânea a várias equipas; confirmar a equipa deste dia.'
    for row in data['assignments']:
        day = service.original(row['DATA'])[:10]
        member = memberships[clean(row['U_TEAMSTAMP'])]
        if member['AUSENTE']:
            blocked[day] = 'O registo de pertença à equipa está assinalado como ausente.'
        options = matches.get(clean(row['OPCSTAMP']), [])
        if not options or int(row['WORK_MATCHES']) != 1:
            blocked[day] = 'Obra do planeamento sem ligação segura às empresas selecionadas.'
            continue
        # Copies across companies share the same OPCSTAMP: one physical work.
        # Repeated stamps within a company are ambiguous and never selected.
        if len({c['feid'] for c, _ in options}) != len(options):
            blocked[day] = 'Correspondência duplicada da obra; confirme a ficha OPC.'
            continue
        options.sort(key=lambda item: (item[0]['feid'] != payroll['company']['feid'], item[0]['feid']))
        company, work_row = options[0]
        key = engine.digest([company['feid'], company['phc_db'], clean(work_row['PROCESSO'])])
        if key not in works:
            evidence = [deepcopy(auto) for batch in batches for auto in batch['rows']
                        if auto['has_positive_measurement'] and auto.get('work_stamp') == clean(row['OPCSTAMP'])]
            works[key] = {'key': key, 'company': company, 'work': clean(work_row['PROCESSO']),
                'planning_work': clean(row['PROCESSO']), 'work_stamp': clean(row['OPCSTAMP']),
                'client': clean(work_row['NOME']), 'address': clean(work_row['MORADA']), 'locality': clean(work_row['LOCALIDADE']),
                'evidence': evidence, 'planning_refs': [], 'work_source': {'database': company['phc_db'], 'table': 'OPC', 'stamp': clean(row['OPCSTAMP'])}}
        evidence = {'date': day, 'work_key': key, 'team': clean(row['FREF']),
                    'sources': [ref('U_PLANO', row['U_PLANOSTAMP']), ref('U_TEAM', row['U_TEAMSTAMP']), ref('OPC', row['OPCSTAMP'])]}
        if evidence not in records:
            records.append(evidence)
            works[key]['planning_refs'].append(evidence)
    start, end = period_bounds(payroll['year'], payroll['month'])
    for absence in data['absences']:
        first = service.original(absence['DATAINI'])[:10]; last = service.original(absence['DATAFIM'])[:10]
        for offset in range((end-start).days):
            day = (start+timedelta(days=offset)).isoformat()
            if first <= day <= last:
                blocked[day] = 'Ausência registada no período.'
    records = [r for r in records if r['date'] not in blocked]
    used = {r['work_key'] for r in records}
    works = [works[key] for key in sorted(used)]
    for work in works:
        work['planning_refs'] = [r for r in records if r['work_key'] == work['key']]
    extra_works, extra_records = {}, []
    own_stamps = {work['work_stamp'] for work in works}
    own_teams = {r['team'] for r in records}
    own_dates = {r['date'] for r in records}
    if len(works) == 1 and engine.D(payroll['employee']['phc']['km']['quantity'] or '0') > 0:
        for row in data.get('other_assignments', []):
            day = service.original(row['DATA'])[:10]
            stamp = clean(row['OPCSTAMP'])
            options = matches.get(stamp, [])
            if day not in own_dates or clean(row['FREF']) in own_teams or stamp in own_stamps or int(row['WORK_MATCHES']) != 1:
                continue
            if not options or len({c['feid'] for c, _ in options}) != len(options):
                continue
            options.sort(key=lambda item: (item[0]['feid'] != payroll['company']['feid'], item[0]['feid']))
            company, work_row = options[0]
            key = engine.digest([company['feid'], company['phc_db'], clean(work_row['PROCESSO'])])
            evidence = {'date': day, 'work_key': key, 'team': clean(row['FREF']),
                        'sources': [ref('U_PLANO', row['U_PLANOSTAMP']), ref('OPC', stamp)]}
            extra_records.append(evidence)
            extra_works.setdefault(key, {'key': key, 'company': company, 'work': clean(work_row['PROCESSO']),
                'planning_work': clean(row['PROCESSO']), 'work_stamp': stamp, 'client': clean(work_row['NOME']),
                'address': clean(work_row['MORADA']), 'locality': clean(work_row['LOCALIDADE']), 'hypothetical': True,
                'evidence': [deepcopy(auto) for batch in batches for auto in batch['rows'] if auto['has_positive_measurement'] and auto.get('work_stamp') == stamp],
                'planning_refs': [], 'work_source': {'database': company['phc_db'], 'table': 'OPC', 'stamp': stamp}})['planning_refs'].append(evidence)
    if not records:
        warnings.append('Sem ligação utilizável entre trabalhador, equipa, obra e data neste mês. Não são propostas viagens apenas para acertar o total PHC.')
    if not data['absence_identity_unique']:
        warnings.append('Ausências sem empresa de origem: número de trabalhador não único; não foram associadas automaticamente. Confirme os dias excluídos.')
    without_autos = sum(not work['evidence'] for work in works)
    if without_autos:
        warnings.append(f'{without_autos} obra(s) associadas no planeamento sem auto positivo nas empresas selecionadas neste mês.')
    if blocked:
        warnings.append(f'{len(blocked)} dia(s) excluídos por ausência, conflito de equipa ou obra sem ligação segura.')
    original = {**data, 'catalogs': catalogs}
    # Preserve only authorized work records. Omitted assignments expose no work identifiers.
    authorized_stamps = {s['stamp'] for r in records for s in r['sources'] if s['table'] == 'U_PLANO'}
    original['assignments'] = [r for r in data['assignments'] if clean(r['U_PLANOSTAMP']) in authorized_stamps]
    extra_stamps = {s['stamp'] for r in extra_records for s in r['sources'] if s['table'] == 'U_PLANO'}
    serialized = {'memberships': [serial(r) for r in data['memberships']],
                  'assignments': [serial(r) for r in original['assignments']],
                  'other_team_assignments': [serial(r) for r in data.get('other_assignments', []) if clean(r['U_PLANOSTAMP']) in extra_stamps],
                  'absences': [serial(r) for r in data['absences']],
                  'catalogs': [{'company': c['company'], 'rows': [serial(r) for r in c['rows']]} for c in catalogs]}
    result = {'source': 'PLANEAMENTO_EQUIPAS', 'records': records, 'works': works, 'blocked_dates': blocked,
              'original': serialized, 'warnings': warnings, 'read_at': datetime.now(timezone.utc).isoformat(),
              'days_with_assignments': len({r['date'] for r in records}),
              'extra_works': list(extra_works.values()), 'extra_records': extra_records}
    result['fingerprint'] = engine.digest({'original': serialized, 'blocked_dates': blocked, 'records': records, 'extra_records': extra_records})
    return result
