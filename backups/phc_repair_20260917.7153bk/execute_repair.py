"""Exact, backed-up PHC repair. Default execution rolls the transaction back.

Only --apply commits, after locked preflight and complete after-image validation.
No procedure is executed, no trigger disabled, no accounting counterpart changed.
"""
import argparse
import copy
import hashlib
import json
import sys
from collections import Counter
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

import pyodbc

sys.path.insert(0, '/tmp/phc-integration-analysis.y6j6RC')
from db_read import rows, values

ROOT = Path(__file__).resolve().parent
BASELINE = json.loads((ROOT / 'before.json').read_text())
PLAN = json.loads((ROOT / 'repair_plan.json').read_text())
ML_PLAN = json.loads((ROOT / 'ml_plan_review.json').read_text())
PK = {'GESTAO.FO': 'fostamp', 'GESTAO.FN': 'fnstamp',
      'Guest_SPA_Tur.FO': 'fostamp', 'Guest_SPA_Tur.FO2': 'fo2stamp',
      'Guest_SPA_Tur.FN': 'fnstamp', 'Guest_SPA_Tur.FOT': 'fotstamp',
      'Guest_SPA_Tur.ML': 'mlstamp', 'Guest_SPA_Tur.DO': 'dostamp',
      'GESTAO.IM': 'imstamp', 'Guest_SPA_Tur.PC': 'pcstamp'}
SCHEMA = {table: {c['COLUMN_NAME'].lower(): c for c in cols}
          for table, cols in BASELINE['schema'].items()}
NUMERIC = {'numeric', 'decimal', 'money', 'smallmoney', 'float', 'real',
           'int', 'smallint', 'bigint', 'tinyint'}


def dec(value):
    return Decimal(str(value or 0))


def save(path, obj):
    path.write_text(json.dumps(obj, default=str, ensure_ascii=False, indent=2))


def log(**obj):
    print(json.dumps(obj, default=str, ensure_ascii=False), flush=True)


def qual(table):
    assert table in PK
    db, name = table.split('.')
    return f'[{db}].dbo.[{name}]'


def normalize(table, row):
    result = {}
    for key, value in row.items():
        key = key.lower()
        if value is not None and SCHEMA[table][key]['DATA_TYPE'] in NUMERIC:
            result[key] = dec(value)
        else:
            result[key] = value if value is None or isinstance(value, bool) else str(value)
    return result


def indexed(table, records):
    key = PK[table]
    result = {str(row[key]).rstrip(): normalize(table, row) for row in records}
    assert len(result) == len(records), ('Non-unique primary key', table)
    return result


def compare(expected, actual, phase):
    errors = []
    for table in PK:
        lhs, rhs = indexed(table, expected[table]), indexed(table, actual[table])
        if lhs.keys() != rhs.keys():
            errors.append({'table': table, 'missing': sorted(lhs.keys()-rhs.keys()),
                           'extra': sorted(rhs.keys()-lhs.keys())})
        for key in lhs.keys() & rhs.keys():
            fields = [f for f in lhs[key] if lhs[key][f] != rhs[key][f]]
            if fields:
                errors.append({'table': table, 'key': key, 'changed_fields': fields,
                               'values': {f: {'expected': lhs[key][f], 'actual': rhs[key][f]} for f in fields}})
    if errors:
        save(ROOT / f'{phase}_differences.json', errors)
        raise RuntimeError(f'{phase}: {len(errors)} unplanned differences; transaction must not commit')


def connection():
    for route in ('primary', 'fallback'):
        driver = next(d for d in pyodbc.drivers() if 'SQL Server' in d)
        connstr = (f"DRIVER={{{driver}}};SERVER={values['prod_'+route+'_server']},{values['prod_'+route+'_port']};"
                   f"DATABASE={values['prod_database']};UID={values['prod_username']};PWD={values['prod_password']};"
                   'TrustServerCertificate=Yes;ApplicationIntent=ReadWrite;APP=PHC_Exact_Backup_Repair_20260917')
        try:
            conn = pyodbc.connect(connstr, timeout=5, autocommit=False)
            conn.timeout = 90
            conn.cursor().execute('SET XACT_ABORT ON; SET LOCK_TIMEOUT 15000; SET DEADLOCK_PRIORITY LOW; SET NOCOUNT ON;')
            return conn
        except pyodbc.Error as exc:
            log(connection_route=route, error_code=exc.args[0])
    raise RuntimeError('SQL connection unavailable')


def snapshot(conn, lock=False):
    tables = {}
    stamps = BASELINE['scope_fostamps']
    do_stamps = sorted({r['dostamp'].strip() for r in BASELINE['tables']['Guest_SPA_Tur.FO'] if r['dostamp'].strip()})
    fn_stamps = [r['fnstamp'] for r in BASELINE['tables']['GESTAO.FN']]
    accounts = sorted({r['conta'] for r in BASELINE['tables']['Guest_SPA_Tur.ML']})
    selects = [('GESTAO.FO', 'fostamp', stamps), ('GESTAO.FN', 'fostamp', stamps),
               ('Guest_SPA_Tur.FO', 'fostamp', stamps), ('Guest_SPA_Tur.FO2', 'fo2stamp', stamps),
               ('Guest_SPA_Tur.FN', 'fostamp', stamps), ('Guest_SPA_Tur.FOT', 'fostamp', stamps),
               ('Guest_SPA_Tur.ML', 'dostamp', do_stamps), ('Guest_SPA_Tur.DO', 'dostamp', do_stamps),
               ('GESTAO.IM', 'oristamp', stamps + fn_stamps), ('Guest_SPA_Tur.PC', 'conta', accounts)]
    for table, key, ids in selects:
        hint = ' WITH (UPDLOCK,HOLDLOCK)' if lock else ''
        sql = f'SELECT * FROM {qual(table)}{hint} WHERE [{key}] IN (' + ','.join('?' for _ in ids) + ')'
        tables[table] = [{k.lower(): v for k, v in r.items()} for r in rows(conn, sql, ids)]
    return tables


def build_operations():
    assert not PLAN['inserts']
    excluded = set(BASELINE['petrogal_excluded'])
    assert len(excluded) == 8 and set(PLAN['excluded_petrogal']) == excluded
    documents = {r['fostamp']: r for r in PLAN['documents']}
    assert len(documents) == 192 and not excluded & documents.keys()
    operations = [dict(r, action='DELETE') for r in PLAN['deletes']]
    operations += [dict(r, action='UPDATE') for r in PLAN['updates']]
    assert ML_PLAN['document_count'] == 56 and ML_PLAN['ml_update_count'] == 113
    assert not ML_PLAN['ambiguous_documents']
    for r in ML_PLAN['updates']:
        old = next(x for x in BASELINE['tables']['Guest_SPA_Tur.ML'] if x['mlstamp'] == r['mlstamp'])
        assert old['dostamp'] == r['dostamp'] and old['oristamp'].strip() == r['fostamp']
        assert old['conta'].strip() == r['conta'].strip()
        for field, value in r['before'].items():
            assert dec(old[field]) == dec(value)
        assert dec(r['after']['ecre']) == dec(old['ecre']) and dec(r['after']['cre']) == dec(old['cre'])
        assert dec(r['after']['edeb']) * Decimal('200.482') == dec(r['after']['deb'])
        operations.append({'action': 'UPDATE', 'table': 'Guest_SPA_Tur.ML', 'key': 'mlstamp',
                           'id': r['mlstamp'], 'fostamp': r['fostamp'],
                           'values': {k: r['after'][k] for k in ('edeb', 'deb')}})
    expected = copy.deepcopy(BASELINE['tables'])
    seen = set()
    for op in operations:
        assert op['fostamp'] in documents and op['fostamp'] not in excluded
        assert (op['table'], op['id']) not in seen
        seen.add((op['table'], op['id']))
        assert op['key'] == PK[op['table']]
        found = [r for r in expected[op['table']] if r[op['key']] == op['id']]
        assert len(found) == 1
        record = found[0]
        if op['action'] == 'DELETE':
            if op['table'].endswith('.FN'):
                assert not record['ref'].strip() and not record['design'].strip()
            expected[op['table']].remove(record)
        else:
            for key, value in op['values'].items():
                assert key in SCHEMA[op['table']]
                scale = SCHEMA[op['table']][key]['NUMERIC_SCALE']
                record[key] = dec(value).quantize(Decimal(10)**-scale, rounding=ROUND_HALF_UP)
    validate_business(expected)
    return operations, expected


def validate_business(tables):
    for doc in PLAN['documents']:
        stamp = doc['fostamp']
        fot = [r for r in tables['Guest_SPA_Tur.FOT'] if r['fostamp'] == stamp]
        assert sum((dec(r['ebaseinc']) for r in fot), Decimal(0)) == dec(doc['base'])
        assert sum((dec(r['evalor']) for r in fot), Decimal(0)) == dec(doc['vat'])
        for table in ('GESTAO.FO', 'Guest_SPA_Tur.FO'):
            fo = next(r for r in tables[table] if r['fostamp'] == stamp)
            assert sum((dec(fo[f'eivav{i}']) for i in range(1, 10)), Decimal(0)) == dec(doc['vat'])
            assert dec(fo['eivain']) == dec(doc['base']) and dec(fo['ettiva']) == dec(doc['vat'])
            assert dec(fo['etotal']) == dec(doc['total']) == dec(doc['base']) + dec(doc['vat'])
    for doc in ML_PLAN['documents']:
        ml = [r for r in tables['Guest_SPA_Tur.ML'] if r['dostamp'] == doc['dostamp']]
        base = sum((dec(r['edeb'])-dec(r['ecre']) for r in ml
                    if r['mlstamp'] != doc['counterparty_ml_unchanged']
                    and not r['conta'].strip().startswith('243')), Decimal(0))
        vat = sum((dec(r['edeb'])-dec(r['ecre']) for r in ml if r['conta'].strip().startswith('243')), Decimal(0))
        debit = sum((dec(r['edeb']) for r in ml), Decimal(0))
        credit = sum((dec(r['ecre']) for r in ml), Decimal(0))
        assert base == dec(doc['base']), (doc['document'], 'base', base)
        assert vat == dec(doc['iva']), (doc['document'], 'VAT', vat)
        assert debit == credit == dec(doc['total']), (doc['document'], 'balance', debit, credit)
        local_debit = sum((dec(r['deb']) for r in ml), Decimal(0))
        local_credit = sum((dec(r['cre']) for r in ml), Decimal(0))
        assert local_debit == local_credit, (doc['document'], 'legacy balance')


def execute_chunk(conn, chunk):
    statements = ['DECLARE @changed TABLE (target_id varchar(100));']
    params = []
    for op in chunk:
        table, key = qual(op['table']), op['key']
        output = f'OUTPUT deleted.[{key}] INTO @changed' if op['action'] == 'DELETE' else f'OUTPUT inserted.[{key}] INTO @changed'
        if op['action'] == 'DELETE':
            sql = f'DELETE FROM {table} {output} WHERE [{key}]=?'
        else:
            assignments = ','.join(f'[{k}]=?' for k in op['values'])
            params.extend(dec(v) for v in op['values'].values())
            sql = f'UPDATE {table} SET {assignments} {output} WHERE [{key}]=?'
        params.append(op['id'])
        if op['table'].endswith(('.FN', '.FOT')):
            sql += ' AND fostamp=?'
            params.append(op['fostamp'])
        elif op['table'].endswith('.ML'):
            sql += ' AND oristamp=?'
            params.append(op['fostamp'])
        if op['action'] == 'DELETE' and op['table'].endswith('.FN'):
            sql += " AND LTRIM(RTRIM(ISNULL(ref,'')))='' AND LTRIM(RTRIM(ISNULL(design,'')))=''"
        statements.append(sql + ';')
    statements.append('SELECT target_id AS __repair_changed_id FROM @changed;')
    cur = conn.cursor()
    cur.execute('\n'.join(statements), params)
    changed = []
    while True:
        if cur.description and cur.description[0][0] == '__repair_changed_id':
            changed.extend(str(r[0]).rstrip() for r in cur.fetchall())
        elif cur.description:
            cur.fetchall()
        if not cur.nextset():
            break
    assert Counter(changed) == Counter(op['id'].rstrip() for op in chunk), ('Affected row mismatch', changed)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    mode = 'apply' if args.apply else 'dry_run'
    if args.apply and (ROOT / 'apply_report.json').exists():
        raise RuntimeError('An apply report already exists. Inspect it; never blindly reapply.')
    operations, expected = build_operations()
    report = {'mode': mode, 'started_at': datetime.now().isoformat(), 'status': 'planned',
              'documents': 192, 'petrogal_excluded': 8, 'accounting_documents': 56,
              'operation_counts': dict(Counter(r['action']+' '+r['table'] for r in operations)),
              'source_sha256': {p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest()
                                for p in ('before.json','repair_plan.json','ml_plan_review.json')}}
    save(ROOT / f'{mode}_report.json', report)
    conn = connection()
    commit_attempted = False
    try:
        live = snapshot(conn, lock=True)
        compare(BASELINE['tables'], live, mode+'_preflight')
        log(stage='locked_preflight_passed', operations=len(operations), **report['operation_counts'])
        for i in range(0, len(operations), 25):
            execute_chunk(conn, operations[i:i+25])
            if i % 100 == 0:
                log(stage='in_transaction', completed=min(i+25, len(operations)), total=len(operations))
        after = snapshot(conn)
        compare(expected, after, mode+'_after')
        validate_business(after)
        report.update(status='validated_pending_commit' if args.apply else 'validated_pending_rollback',
                      validated_at=datetime.now().isoformat(),
                      iva_reduction=ML_PLAN['iva_reduction_total'])
        save(ROOT / f'{mode}_after.json', {'captured_at': datetime.now().isoformat(), 'tables': after})
        save(ROOT / f'{mode}_report.json', report)
        if args.apply:
            commit_attempted = True
            conn.commit()
            report['status'] = 'committed'
        else:
            conn.rollback()
            report['status'] = 'rolled_back_successfully'
        report['finished_at'] = datetime.now().isoformat()
        save(ROOT / f'{mode}_report.json', report)
        log(**report)
    except Exception as exc:
        conn.rollback()
        report.update(status='commit_outcome_requires_verification' if commit_attempted else 'rolled_back_error',
                      error_type=type(exc).__name__, error=str(exc), finished_at=datetime.now().isoformat())
        save(ROOT / f'{mode}_report.json', report)
        log(**report)
        raise
    finally:
        conn.close()


if __name__ == '__main__':
    main()
