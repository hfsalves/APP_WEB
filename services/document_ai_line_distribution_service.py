from __future__ import annotations

from copy import deepcopy
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any
from uuid import NAMESPACE_URL, uuid5


TOLERANCE = Decimal('0.01')


def _text(value: Any) -> str:
    return str(value or '').strip()


def _number(value: Any) -> Decimal | None:
    if value is None or (isinstance(value, str) and not value.strip()):
        return None
    try:
        return Decimal(str(value).replace(' ', '').replace(',', '.'))
    except (InvalidOperation, TypeError, ValueError):
        return None


def _stable_id(prefix: str, document_stamp: str, position: int, item: dict[str, Any]) -> str:
    current = _text(item.get(f'{prefix}_id') or item.get('id'))
    if current:
        return current
    identity = '|'.join((
        _text(document_stamp), str(position), _text(item.get('source_ref') or item.get('ref')),
        _text(item.get('description')), _text(item.get('qty') or item.get('quantity')),
        _text(item.get('unit_price')), _text(item.get('net_amount') or item.get('pt')),
    ))
    return str(uuid5(NAMESPACE_URL, f'gr360-document-ai:{prefix}:{identity}'))


def normalize_line_structures(lines: list[dict[str, Any]] | None, document_stamp: str = '') -> list[dict[str, Any]]:
    """Normalize the one line/cost/group/distribution model used by every invoice."""
    result: list[dict[str, Any]] = []
    for position, source in enumerate(lines or []):
        if not isinstance(source, dict):
            continue
        line = deepcopy(source)
        line['line_model_version'] = 'TP065'
        line_id = _stable_id('line', document_stamp, position, line)
        line['line_id'] = line_id
        detailed_costs: list[dict[str, Any]] = []
        for cost_type, values in (
            ('included', line.get('included_costs')),
            ('additional', line.get('additional_costs')),
            ('', line.get('detailed_costs')),
        ):
            for cost_position, source_cost in enumerate(values or []):
                if not isinstance(source_cost, dict):
                    continue
                cost = deepcopy(source_cost)
                cost['cost_type'] = _text(cost.get('cost_type') or cost_type).lower()
                if cost['cost_type'] not in {'included', 'additional'}:
                    cost['cost_type'] = 'included'
                cost['cost_id'] = _stable_id('cost', line_id, len(detailed_costs) + cost_position, cost)
                cost['parent_line_id'] = line_id
                cost['accounting_effective'] = False
                detailed_costs.append(cost)

        # TP065 migration: former C&P movement children become explanatory
        # included costs.  The visible accounting row remains exactly once.
        legacy_fuel = bool(line.get('accounting_consolidated') or line.get('fuel_tolls'))
        if legacy_fuel:
            legacy_children = line.get('sub_lines') if isinstance(line.get('sub_lines'), list) else line.get('sublines')
            for cost_position, source_cost in enumerate(legacy_children or []):
                if not isinstance(source_cost, dict):
                    continue
                cost = deepcopy(source_cost)
                cost['cost_type'] = 'included'
                cost['cost_id'] = _stable_id('cost', line_id, len(detailed_costs) + cost_position, cost)
                cost['parent_line_id'] = line_id
                cost['accounting_effective'] = False
                detailed_costs.append(cost)
            line['qty'] = 1
            line['quantity'] = 1
            line['unit_price'] = line.get('net_amount') if line.get('net_amount') is not None else line.get('pt')
            line.pop('accounting_consolidated', None)
            line.pop('fuel_tolls', None)
            line.pop('sub_lines', None)
            line.pop('sublines', None)
        line.pop('included_costs', None)
        line.pop('additional_costs', None)
        if detailed_costs:
            line['detailed_costs'] = detailed_costs
        line_origin_stamp = _text(line.get('phc_origin_stamp') or line.get('origin_stamp') or line.get('bostamp'))
        line_origin_line_stamp = _text(line.get('phc_origin_line_stamp') or line.get('origin_line_stamp') or line.get('bistamp'))
        if line_origin_stamp:
            line['phc_origin_stamp'] = line_origin_stamp
            line['bostamp'] = line_origin_stamp
        if line_origin_line_stamp:
            line['phc_origin_line_stamp'] = line_origin_line_stamp
            line['bistamp'] = line_origin_line_stamp
        legacy_group = _text(line.get('article_group_code')).upper()
        if not _text(line.get('group_id')) and len(legacy_group) > 1 and legacy_group[1:].isdigit():
            line['group_id'] = f'legacy-{legacy_group[1:]}'
            line['group_role'] = 'principal' if legacy_group.startswith('P') else 'associated'
        line.pop('article_group_code', None)
        children = line.get('sub_lines')
        if not isinstance(children, list):
            children = line.get('sublines')
        normalized_children: list[dict[str, Any]] = []
        for child_position, source_child in enumerate(children or []):
            if not isinstance(source_child, dict):
                continue
            child = deepcopy(source_child)
            child['subline_id'] = _stable_id('subline', line_id, child_position, child)
            child['parent_line_id'] = line_id
            child_origin_stamp = _text(child.get('phc_origin_stamp') or child.get('origin_stamp') or child.get('bostamp'))
            child_origin_line_stamp = _text(child.get('phc_origin_line_stamp') or child.get('origin_line_stamp') or child.get('bistamp'))
            if child_origin_stamp:
                child['phc_origin_stamp'] = child_origin_stamp
                child['bostamp'] = child_origin_stamp
            if child_origin_line_stamp:
                child['phc_origin_line_stamp'] = child_origin_line_stamp
                child['bistamp'] = child_origin_line_stamp
            inherited = {
                'article_ref': line.get('article_ref') or line.get('article') or '',
                'unit_price': line.get('unit_price'),
                'unit': line.get('unit') or '',
                'date': line.get('date') or line.get('data') or '',
                'tax_rate': line.get('tax_rate'),
            }
            for key, value in inherited.items():
                if child.get(key) is None or (isinstance(child.get(key), str) and not child.get(key).strip()):
                    child[key] = value
            normalized_children.append(child)
        if normalized_children:
            line_quantity = _number(line.get('qty') if 'qty' in line else line.get('quantity')) or Decimal('0')
            line_total = _number(line.get('net_amount') if 'net_amount' in line else line.get('pt')) or Decimal('0')
            for child in normalized_children:
                if _number(child.get('percentage')) is not None:
                    continue
                child_total = _number(child.get('net_amount') if 'net_amount' in child else child.get('pt')) or Decimal('0')
                child_quantity = _number(child.get('qty') if 'qty' in child else child.get('quantity')) or Decimal('0')
                ratio = (child_total / line_total) if line_total else ((child_quantity / line_quantity) if line_quantity else Decimal('0'))
                child['percentage'] = float((ratio * Decimal('100')).quantize(Decimal('0.000001'), rounding=ROUND_HALF_UP))
            previous = sum((_number(child.get('percentage')) or Decimal('0') for child in normalized_children[:-1]), Decimal('0'))
            normalized_children[-1]['percentage'] = float((Decimal('100') - previous).quantize(Decimal('0.000001'), rounding=ROUND_HALF_UP))
        line.pop('sublines', None)
        if normalized_children:
            line['sub_lines'] = normalized_children
        elif 'sub_lines' in line:
            line['sub_lines'] = []
        result.append(line)
    return result


def _destinations(line: dict[str, Any], key: str) -> list[str]:
    aliases = ('ccusto', 'project_ccusto') if key == 'ccusto' else ('registration', 'matricula')
    values = {_text(line.get(alias)) for alias in aliases if _text(line.get(alias))}
    for child in line.get('sub_lines') or []:
        if not isinstance(child, dict):
            continue
        values.update(_text(child.get(alias)) for alias in aliases if _text(child.get(alias)))
    return sorted(values)


def validate_group_pair(principal: dict[str, Any], associated: dict[str, Any]) -> str:
    checks = (
        ('Artigo', _text(principal.get('article_ref') or principal.get('article')), _text(associated.get('article_ref') or associated.get('article'))),
        ('Origem', _text(principal.get('phc_origin_stamp') or principal.get('origin_stamp')), _text(associated.get('phc_origin_stamp') or associated.get('origin_stamp'))),
        ('Data', _text(principal.get('date') or principal.get('data')), _text(associated.get('date') or associated.get('data'))),
        ('IVA', _number(principal.get('tax_rate')), _number(associated.get('tax_rate'))),
    )
    for label, left, right in checks:
        if left not in ('', None) and right not in ('', None) and left != right:
            return f'Impossível agrupar: {label} diferente.'
    for label, key in (('Centro de Custo', 'ccusto'), ('Matrícula', 'registration')):
        left, right = _destinations(principal, key), _destinations(associated, key)
        if left and right and left != right:
            return f'Impossível agrupar: {label} diferente.'
    return ''


def distribution_errors(line: dict[str, Any]) -> list[str]:
    children = [child for child in (line.get('sub_lines') or []) if isinstance(child, dict)]
    if not children:
        return []
    quantity = _number(line.get('qty') if 'qty' in line else line.get('quantity')) or Decimal('0')
    total = _number(line.get('net_amount') if 'net_amount' in line else line.get('pt')) or Decimal('0')
    unit_price = _number(line.get('unit_price')) or Decimal('0')
    errors: list[str] = []
    combinations: set[tuple[str, str]] = set()
    distributed_quantity = Decimal('0')
    distributed_total = Decimal('0')
    for position, child in enumerate(children):
        ccusto = _text(child.get('ccusto') or child.get('project_ccusto'))
        registration = _text(child.get('registration') or child.get('matricula'))
        child_quantity = _number(child.get('qty') if 'qty' in child else child.get('quantity'))
        child_total = _number(child.get('net_amount') if 'net_amount' in child else child.get('pt'))
        child_tax = _number(child.get('tax_rate') if child.get('tax_rate') not in (None, '') else line.get('tax_rate'))
        if not ccusto:
            errors.append('Matrícula s/Centro de Custo' if registration else 'Falta Centro de Custo numa sublinha.')
        if bool(line.get('vehicle_required')) and not registration:
            errors.append('Falta Matrícula numa sublinha.')
        if child_quantity is None or child_total is None:
            errors.append('Falta distribuir Quantidade e PT numa sublinha.')
            continue
        if child_tax is None:
            errors.append('Falta IVA numa sublinha.')
        if child_quantity < 0 or child_total < 0:
            errors.append('Quantidade e PT não podem ser negativos.')
        combination = (ccusto.casefold(), registration.casefold())
        if combination in combinations:
            errors.append('Existe uma combinação Centro de Custo/Matrícula duplicada.')
        combinations.add(combination)
        distributed_quantity += child_quantity
        distributed_total += child_total
        percentage = _number(child.get('percentage'))
        if percentage is None:
            errors.append('Falta a percentagem numa sublinha.')
        elif percentage < 0:
            errors.append('A percentagem não pode ser negativa.')
        elif quantity and abs((quantity * percentage / Decimal('100')) - child_quantity) > TOLERANCE:
            errors.append('A percentagem não corresponde à Quantidade distribuída.')
        if unit_price and abs((child_quantity * unit_price) - child_total) > TOLERANCE:
            errors.append('Quantidade × PU não corresponde ao PT numa sublinha.')
    if distributed_quantity > quantity + TOLERANCE or distributed_total > total + TOLERANCE:
        errors.append('Uma sublinha excede o saldo por distribuir.')
    if abs(distributed_quantity - quantity) > TOLERANCE:
        errors.append('A Quantidade distribuída não corresponde à linha.')
    if abs(distributed_total - total) > TOLERANCE:
        errors.append('O Valor distribuído não corresponde à linha.')
    percentage_total = sum((_number(child.get('percentage')) or Decimal('0') for child in children), Decimal('0'))
    if abs(percentage_total - Decimal('100')) > Decimal('0.0001'):
        errors.append('A distribuição deve totalizar exatamente 100 %.')
    if not unit_price:
        errors.append('PU igual a zero: corrige explicitamente a linha antes de validar.')
    return list(dict.fromkeys(errors))


def origin_lineage_errors(lines: list[dict[str, Any]] | None) -> list[str]:
    """Validate BOSTAMP/BISTAMP pairs on each effective Portal line without inferring group-wide links."""
    errors: list[str] = []
    for line in normalize_line_structures(lines):
        children = [child for child in (line.get('sub_lines') or []) if isinstance(child, dict)]
        effective = children or [line]
        for item in effective:
            bostamp = _text(item.get('phc_origin_stamp') or item.get('bostamp'))
            bistamp = _text(item.get('phc_origin_line_stamp') or item.get('bistamp'))
            if bool(bostamp) != bool(bistamp):
                errors.append('A filiação PHC da linha está incompleta: confirma BOSTAMP e BISTAMP.')
            for link in item.get('phc_origin_links') or []:
                if not isinstance(link, dict):
                    continue
                link_bo = _text(link.get('bostamp') or link.get('origin_stamp'))
                link_bi = _text(link.get('bistamp') or link.get('origin_line_stamp'))
                if not link_bo or not link_bi:
                    errors.append('A filiação PHC da linha está incompleta: confirma BOSTAMP e BISTAMP.')
    return list(dict.fromkeys(errors))


def line_workflow_errors(lines: list[dict[str, Any]] | None) -> list[str]:
    items = normalize_line_structures(lines)
    errors: list[str] = []
    groups: dict[str, list[dict[str, Any]]] = {}
    for line in items:
        group_id = _text(line.get('group_id'))
        if group_id:
            groups.setdefault(group_id, []).append(line)
        errors.extend(distribution_errors(line))
    errors.extend(origin_lineage_errors(items))
    for members in groups.values():
        principals = [line for line in members if _text(line.get('group_role')) == 'principal']
        if len(principals) != 1:
            errors.append('Existe um grupo sem uma única linha principal.')
            continue
        for associated in members:
            if associated is principals[0]:
                continue
            conflict = validate_group_pair(principals[0], associated)
            if conflict:
                errors.append(conflict)
    return list(dict.fromkeys(errors))
