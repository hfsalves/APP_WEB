from datetime import date

import pytest

from services.faturacao_reservas_global_service import (
    append_fatura_texto_payload_lines,
    current_fatura_date,
    fatura_recipient_name,
    fatura_texto_lines,
    normalize_fatura_texto,
)


def test_reservation_invoice_always_uses_current_date():
    today = date(2026, 9, 30)

    assert current_fatura_date(today) == today


def test_normalizes_windows_newlines_and_preserves_line_order():
    value = normalize_fatura_texto('Primeira linha\r\nSegunda linha\rTerceira linha')

    assert value == 'Primeira linha\nSegunda linha\nTerceira linha'
    assert fatura_texto_lines(value) == [
        'Primeira linha',
        'Segunda linha',
        'Terceira linha',
    ]


def test_rejects_invoice_text_line_longer_than_fi_design():
    with pytest.raises(ValueError, match='linha 2.*60 caracteres'):
        normalize_fatura_texto('Linha válida\n' + ('x' * 61))


def test_rejects_text_longer_than_rs_column():
    value = '\n'.join(['x' * 60, 'y' * 60, 'z' * 60, 'w' * 58])

    with pytest.raises(ValueError, match='240 caracteres'):
        normalize_fatura_texto(value)


def test_accepts_exact_rs_and_fi_limits():
    value = '\n'.join(['x' * 60, 'y' * 60, 'z' * 60, 'w' * 57])

    assert len(value) == 240
    assert normalize_fatura_texto(value) == value


def test_invoice_recipient_uses_ftnome_instead_of_guest_name():
    row = {
        'FTNOME': '  MAC-AVIATION TECHNICAL SUPPORT, LDA  ',
        'HOSPEDE': 'Fabio Machado',
    }

    assert fatura_recipient_name(row) == 'MAC-AVIATION TECHNICAL SUPPORT, LDA'


def test_invoice_recipient_falls_back_to_guest_name_when_ftnome_is_empty():
    row = {'FTNOME': '   ', 'HOSPEDE': '  Fabio Machado  '}

    assert fatura_recipient_name(row) == 'Fabio Machado'


def test_invoice_recipient_accepts_raw_rs_name_as_fallback():
    assert fatura_recipient_name({'FTNOME': '', 'NOME': 'Fabio Machado'}) == 'Fabio Machado'


def test_invoice_recipient_uses_default_when_both_names_are_empty():
    assert fatura_recipient_name({'FTNOME': '', 'HOSPEDE': ''}) == 'Cliente Final'


def test_appends_text_rows_after_billable_rows():
    lines = [{'ref': 'ESTADIA', 'design': 'Estadia', 'qtt': 1, 'epv': 100}]

    result = append_fatura_texto_payload_lines(lines, 'Nota um\n\nNota dois')

    assert result == [
        {'ref': 'ESTADIA', 'design': 'Estadia', 'qtt': 1, 'epv': 100},
        {
            'ref': '', 'design': 'Nota um', 'qtt': 0, 'epv': 0,
            'tabiva': 4, 'iva': 0,
        },
        {
            'ref': '', 'design': 'Nota dois', 'qtt': 0, 'epv': 0,
            'tabiva': 4, 'iva': 0,
        },
    ]
