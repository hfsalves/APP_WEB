from datetime import date
from decimal import Decimal

from price_engine import (
    _configured_minimum_price,
    _effective_minimum_prices,
    _flags_use_configured_minimum,
)


class _SessionMustNotBeUsed:
    def execute(self, *_args, **_kwargs):
        raise AssertionError("The monthly factor must not be read for minimum prices.")


def test_configured_minimum_price_is_absolute():
    assert _configured_minimum_price(Decimal("70")) == Decimal("70")


def test_effective_minimum_does_not_change_between_months():
    minimums = _effective_minimum_prices(
        _SessionMustNotBeUsed(),
        Decimal("70"),
        date(2026, 1, 31),
        date(2026, 2, 1),
    )

    assert minimums == {
        date(2026, 1, 31): Decimal("70"),
        date(2026, 2, 1): Decimal("70"),
    }


def test_stored_flags_require_the_absolute_minimum_rule():
    old_flags = '{"month":{"min_effective":49},"clamp":{"min":49}}'
    current_flags = (
        '{"month":{"min_effective":70,"min_affected_by_factor":false},'
        '"clamp":{"min":70}}'
    )

    assert not _flags_use_configured_minimum(old_flags, Decimal("70"))
    assert _flags_use_configured_minimum(current_flags, Decimal("70"))
