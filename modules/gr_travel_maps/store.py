"""Append-only full versions, atomic head changes and optimistic concurrency.

Schema creation is a deployment operation; no request creates tables. SQLAlchemy
Core allows testing the same transactions against an isolated SQLite database.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
import uuid

from sqlalchemy import (Column, DateTime, ForeignKey, Integer, MetaData, String, Table,
                        UnicodeText, insert, select, update, inspect)
from sqlalchemy.dialects.mssql import DATETIME2, NVARCHAR
from sqlalchemy.exc import IntegrityError, OperationalError

from .config import TravelMapsError
from .engine import digest

metadata = MetaData()
UTCDateTime = DateTime().with_variant(DATETIME2(precision=6), 'mssql')
JSONText = UnicodeText().with_variant(NVARCHAR(None), 'mssql')
maps = Table('GR_TRAVEL_MAP', metadata,
    Column('id', String(36), primary_key=True),
    Column('scope_hash', String(64), nullable=False, unique=True),
    Column('feid', Integer, nullable=False), Column('phc_db', String(128), nullable=False),
    Column('employee_key', String(250), nullable=False),
    Column('year', Integer, nullable=False), Column('month', Integer, nullable=False),
    Column('version', Integer, nullable=False),
)
versions = Table('GR_TRAVEL_MAP_VERSION', metadata,
    Column('map_id', String(36), ForeignKey(maps.c.id), primary_key=True),
    Column('version', Integer, primary_key=True),
    Column('request_id', String(36), nullable=False, unique=True),
    Column('request_hash', String(64), nullable=False),
    Column('action', String(16), nullable=False), Column('state', String(16), nullable=False),
    Column('actor', String(100), nullable=False), Column('user_stamp', String(25), nullable=False),
    Column('created_at', UTCDateTime, nullable=False), Column('reason', JSONText, nullable=False),
    Column('document', JSONText, nullable=False), Column('previous_hash', String(64), nullable=False),
    Column('content_hash', String(64), nullable=False),
)


class Conflict(TravelMapsError):
    status_code = 409


class NotFound(TravelMapsError):
    status_code = 404


class StorageUnavailable(TravelMapsError):
    status_code = 503


def ready(engine):
    inspector = inspect(engine)
    return all(inspector.has_table(table.name) for table in (maps, versions))


def require_schema(engine):
    if not ready(engine):
        raise StorageUnavailable('O armazenamento de propostas ainda não foi instalado. A leitura PHC continua disponível.')


def scope(payroll):
    return {key: value for key, value in {
        'feid': payroll['company']['feid'], 'phc_db': payroll['company']['phc_db'],
        'employee_key': payroll['employee']['key'], 'year': payroll['year'], 'month': payroll['month'],
    }.items()}


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)


def envelope(row):
    return {key: row[key] for key in ('map_id', 'version', 'request_id', 'request_hash', 'action', 'state',
                                      'actor', 'user_stamp', 'reason', 'document', 'previous_hash')} | {
        'created_at': row['created_at'].isoformat(timespec='microseconds')}


def decode(row):
    result = dict(row)
    if digest(envelope(result)) != result['content_hash']:
        raise StorageUnavailable('A integridade do histórico necessita de verificação. A operação foi interrompida.')
    result['created_at'] = result['created_at'].isoformat(timespec='microseconds') + 'Z'
    result['document'] = json.loads(result['document'])
    result.pop('request_hash', None)
    return result


def get(engine, map_id, version=None):
    with engine.connect() as conn:
        header = conn.execute(select(maps).where(maps.c.id == map_id)).mappings().first()
        if header is None:
            raise NotFound('Mapa não encontrado.')
        row = conn.execute(select(versions).where(versions.c.map_id == map_id,
                versions.c.version == (header['version'] if version is None else version))).mappings().first()
        if row is None:
            raise NotFound('Versão não encontrada.')
        return {'header': dict(header), 'current': decode(row)}


def find(engine, identity):
    with engine.connect() as conn:
        row = conn.execute(select(maps.c.id).where(maps.c.scope_hash == digest(identity))).first()
    return None if row is None else get(engine, row[0])


def history(engine, map_id):
    with engine.connect() as conn:
        records = conn.execute(select(versions).where(versions.c.map_id == map_id).order_by(versions.c.version)).mappings().all()
    previous = ''
    result = []
    for record in records:
        item = decode(record)
        if item['previous_hash'] != previous or item['version'] != len(result) + 1:
            raise StorageUnavailable('A sequência do histórico necessita de verificação.')
        previous = item['content_hash']
        item.pop('document')
        result.append(item)
    return result


def replay(engine, request_id, request_hash, actor, map_id):
    with engine.connect() as conn:
        row = conn.execute(select(versions).where(versions.c.request_id == request_id)).mappings().first()
    if row is None:
        return None
    if row['request_hash'] != request_hash or row['actor'] != actor or row['map_id'] != map_id:
        raise Conflict('O identificador desta operação já foi utilizado para outra alteração.')
    return get(engine, map_id, row['version'])


def monthly(engine, feid, year, month):
    with engine.connect() as conn:
        records = conn.execute(select(maps, versions).select_from(maps.join(versions,
            (maps.c.id == versions.c.map_id) & (maps.c.version == versions.c.version)))
            .where(maps.c.feid == feid, maps.c.year == year, maps.c.month == month)).mappings().all()
    return [{'header': {col.name: row[col] for col in maps.c},
             'current': decode({col.name: row[col] for col in versions.c})} for row in records]


def append(engine, document, *, action, state, actor, user_stamp, reason, expected_version, request_id, request_hash):
    identity = scope(document['payroll'])
    if type(expected_version) is not int or expected_version < 0:
        raise TravelMapsError('Indique a versão que foi consultada antes de gravar.')
    try:
        request_id = str(uuid.UUID(request_id))
    except (ValueError, TypeError, AttributeError):
        raise TravelMapsError('Identificador da operação inválido.') from None
    if len(canonical(document).encode('utf-8')) > 4_000_000:
        raise TravelMapsError('A proposta tem demasiada evidência para guardar numa versão. Reduza as obras selecionadas.')
    try:
        with engine.begin() as conn:
            retry = conn.execute(select(versions).where(versions.c.request_id == request_id)).mappings().first()
            if retry is not None:
                saved = decode(retry)
                if retry['request_hash'] != request_hash or retry['actor'] != actor or scope(saved['document']['payroll']) != identity:
                    raise Conflict('O identificador desta operação já foi utilizado para outra alteração.')
                return {'header': dict(conn.execute(select(maps).where(maps.c.id == retry['map_id'])).mappings().one()), 'current': saved}
            header = conn.execute(select(maps).where(maps.c.scope_hash == digest(identity))).mappings().first()
            if header is None:
                if expected_version != 0:
                    raise Conflict('O mapa foi alterado. Atualize antes de gravar.')
                header = {'id': str(uuid.uuid4()), 'scope_hash': digest(identity), **identity, 'version': 0}
                conn.execute(insert(maps).values(**header))
            if header['version'] != expected_version:
                raise Conflict('Existe uma versão mais recente. Atualize antes de gravar.')
            previous_hash = ''
            if expected_version:
                previous = conn.execute(select(versions).where(versions.c.map_id == header['id'], versions.c.version == expected_version)).mappings().one()
                decode(previous)
                previous_hash = previous['content_hash']
            # CAS must succeed before the immutable version is inserted. Both commit together.
            changed = conn.execute(update(maps).where(maps.c.id == header['id'], maps.c.version == expected_version)
                                   .values(version=expected_version+1))
            if changed.rowcount != 1:
                raise Conflict('Outra pessoa gravou entretanto. Atualize antes de gravar.')
            record = {'map_id': header['id'], 'version': expected_version+1, 'request_id': request_id,
                'request_hash': request_hash, 'action': action, 'state': state, 'actor': actor, 'user_stamp': user_stamp,
                'created_at': datetime.now(timezone.utc).replace(tzinfo=None), 'reason': reason,
                'document': canonical(document), 'previous_hash': previous_hash}
            record['content_hash'] = digest(envelope(record))
            conn.execute(insert(versions).values(**record))
            return {'header': {**header, 'version': record['version']}, 'current': decode(record)}
    except IntegrityError:
        # Includes concurrent first creation and idempotency-key races. Entire transaction rolls back.
        with engine.connect() as conn:
            retry = conn.execute(select(versions).where(versions.c.request_id == request_id)).mappings().first()
        if retry and retry['request_hash'] == request_hash and retry['actor'] == actor:
            saved = get(engine, retry['map_id'], retry['version'])
            if scope(saved['current']['document']['payroll']) == identity:
                return saved
        raise Conflict('A proposta foi gravada noutra operação. Atualize antes de continuar.') from None
    except OperationalError as exc:
        if any(code in str(exc).lower() for code in ('database is locked', 'deadlock', '40001', '1205')):
            raise Conflict('Outra operação está a gravar este mapa. Atualize antes de continuar.') from None
        raise
