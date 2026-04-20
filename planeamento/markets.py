"""Market metadata helpers."""
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Set


@dataclass(frozen=True)
class Market:
    raw_value: str
    code: str
    label: str
    flag_asset: Optional[str]
    emoji: str = ""


_MARKETS: Dict[str, Market] = {}
_CODE_ALIASES: Dict[str, Set[str]] = {}


def _normalise(raw_value: str) -> str:
    return raw_value.strip().upper()


def _register(raw_value: str, code: str, label: str, flag_asset: str, emoji: str = "") -> None:
    normalised = _normalise(raw_value)
    market = Market(raw_value=raw_value, code=code, label=label, flag_asset=flag_asset, emoji=emoji)
    _MARKETS[normalised] = market
    bucket = _CODE_ALIASES.setdefault(code, set())
    bucket.add(raw_value)


_REGISTERED_DATA = [
    ("HSOLS PORTUGAL", "PT", "Portugal", "flags/pt.svg", "\U0001F1F5\U0001F1F9"),
    ("HSOLS MAROC", "MA", "Marrocos", "flags/ma.svg", "\U0001F1F2\U0001F1E6"),
    ("HSOLS ESPAGNE", "ES", "Espanha", "flags/es.svg", "\U0001F1EA\U0001F1F8"),
    ("HSOLS FRANCE", "FR", "Franca", "flags/fr.svg", "\U0001F1EB\U0001F1F7"),
    ("INTERSOL-ALSACE", "IA", "Intersol Alsace", "flags/fr.svg", "\U0001F1EB\U0001F1F7"),
    ("INTERSOL-LORRAINE", "IL", "Intersol Lorraine", "flags/fr.svg", "\U0001F1EB\U0001F1F7"),
    ("INTERSOL-CHAMPAGNE", "IC", "Intersol Champagne", "flags/fr.svg", "\U0001F1EB\U0001F1F7"),
    ("HSOLS ESPANHA", "ES", "Espanha", "flags/es.svg", "\U0001F1EA\U0001F1F8"),
    ("HSOLS ALLEMAGNE", "DE", "Alemanha", "flags/de.svg", "\U0001F1E9\U0001F1EA"),
    ("HSOLS MARROC", "MA", "Marrocos", "flags/ma.svg", "\U0001F1F2\U0001F1E6"),
]

for raw_value, code, label, asset, emoji in _REGISTERED_DATA:
    _register(raw_value, code, label, asset, emoji)


def _fallback_market(raw_value: str) -> Market:
    label = raw_value.title()
    return Market(raw_value=raw_value, code=_normalise(raw_value)[:2], label=label, flag_asset=None, emoji="")


def get_market(raw_value: str) -> Market:
    normalised = _normalise(raw_value)
    return _MARKETS.get(normalised, _fallback_market(raw_value))


def list_markets() -> List[Market]:
    by_code: Dict[str, Market] = {}
    for market in _MARKETS.values():
        by_code.setdefault(market.code, market)
    return sorted(by_code.values(), key=lambda m: m.label)


def market_filters(selected_codes: Iterable[str]) -> List[str]:
    raw_filters: List[str] = []
    for code in selected_codes:
        aliases = _CODE_ALIASES.get(code)
        if not aliases:
            continue
        raw_filters.extend(aliases)
    return raw_filters
