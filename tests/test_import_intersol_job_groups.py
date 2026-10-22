from datetime import date, datetime
from decimal import Decimal
from itertools import count

import pytest

from scripts import import_intersol_deliveries as imp


def source_header(number, job):
    return {"BOSTAMP": f"BC{number}", "OBRANO": number, "NO": 31301,
            "ESTAB": 0, "CCUSTO": job, "DATAOBRA": datetime(2026, 9, 1)}


def allocation(bc):
    return {"excel": {"delivery": "565460", "invoice": "26I0131",
                      "delivery_date": date(2026, 9, 2), "invoice_date": date(2026, 9, 30),
                      "price": Decimal("20.80"), "direct_pf": False},
            "source": {"bc": bc, "BISTAMP": f"BC_LINE{bc}", "IVA": Decimal("20")},
            "qty": Decimal("11.952")}


def execute_with_capture(monkeypatch, allocations, headers):
    stamps = count()
    numbers = {130: count(100), 218: count(200)}
    created_headers, created_lines, separators = [], [], []
    monkeypatch.setattr(imp, "DB", "HSOLS_FR")
    monkeypatch.setattr(imp, "_new_stamp", lambda: f"STAMP{next(stamps)}")
    monkeypatch.setattr(imp, "next_number", lambda cursor, ndos, year: next(numbers[ndos]))
    monkeypatch.setattr(imp, "create_header", lambda cursor, **kw: created_headers.append(kw))
    monkeypatch.setattr(imp, "create_tax", lambda *args: None)
    monkeypatch.setattr(imp, "create_origin_line", lambda cursor, **kw: separators.append(kw))

    def line(cursor, **kw):
        stamp = f"LINE{next(stamps)}"
        created_lines.append({**kw, "bistamp": stamp})
        return stamp

    monkeypatch.setattr(imp, "create_line", line)

    class Cursor:
        def execute(self, *args):
            pass

    result = imp.execute(Cursor(), allocations, headers,
                         {102: "BC", 130: "BL", 218: "PF"}, "APP")
    return result, created_headers, created_lines, separators


def test_same_external_bl_and_invoice_split_by_job(monkeypatch):
    headers = {1185: source_header(1185, "FR2035"),
               1401: source_header(1401, "FR2053")}
    result, documents, lines, separators = execute_with_capture(
        monkeypatch, [allocation(1185), allocation(1401)], headers)
    assert result == {"bl": 2, "pf": 2, "lines": 2}
    assert all(doc["net"] == Decimal("248.60") for doc in documents)
    docs = {doc["stamp"]: doc for doc in documents}
    by_line_stamp = {line["bistamp"]: line for line in lines}
    for line in lines:
        document = docs[line["stamp"]]
        expected_job = headers[line["item"]["source"]["bc"]]["CCUSTO"]
        assert document["origin"]["CCUSTO"] == expected_job
        if line["ndos"] == 218:
            parent = by_line_stamp[line["parent"]]
            assert parent["ndos"] == 130
            assert parent["stamp"] == line["parent_header"]
            assert docs[parent["stamp"]]["origin"]["CCUSTO"] == expected_job
    for stamp in docs:
        orders = [line["lordem"] for line in lines if line["stamp"] == stamp]
        orders += [line["lordem"] for line in separators if line["stamp"] == stamp]
        assert len(orders) == len(set(orders))


def test_two_bc_in_same_job_share_bl_and_pf_with_correct_origins(monkeypatch):
    headers = {1185: source_header(1185, "FR2035"),
               1401: source_header(1401, "FR2035")}
    result, _, lines, _ = execute_with_capture(
        monkeypatch, [allocation(1185), allocation(1401)], headers)
    assert result == {"bl": 1, "pf": 1, "lines": 2}
    for line in lines:
        if line["ndos"] == 130:
            assert line["parent_header"] == headers[line["item"]["source"]["bc"]]["BOSTAMP"]


def test_duplicate_bl_number_in_other_job_does_not_block_import(monkeypatch):
    headers = {1185: source_header(1185, "FR2035")}
    excel = [{"delivery": "565460", "bc": 1185}]
    found = [{"OBRANO": 11513, "MAQUINA": "565460", "NO": 31301,
              "ESTAB": 0, "CCUSTO": "FR2201"}]
    monkeypatch.setattr(imp, "rows", lambda *args: found)
    imp.assert_no_duplicates(None, excel, headers)
    found.append({**found[0], "CCUSTO": "FR2035"})
    with pytest.raises(imp.ImportValidationError, match="Já existem"):
        imp.assert_no_duplicates(None, excel, headers)
