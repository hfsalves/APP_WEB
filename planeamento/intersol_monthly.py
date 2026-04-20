from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, Iterable, List, Sequence
import unicodedata

Role = str

ROLE_CHEF = "CHEF_EQUIPE"
ROLE_POLISSEUR = "POLISSEUR"
ROLE_AIDE = "AIDE_POLISSEUR"
ROLE_SCIEUR = "SCIEUR"

ROLE_FORFAIT: dict[Role, Decimal] = {
    ROLE_CHEF: Decimal("150"),
    ROLE_POLISSEUR: Decimal("150"),
    ROLE_AIDE: Decimal("130"),
    ROLE_SCIEUR: Decimal("150"),
}

ROLE_MINIMUM: dict[Role, Decimal] = {
    ROLE_CHEF: Decimal("3570"),
    ROLE_POLISSEUR: Decimal("3150"),
    ROLE_AIDE: Decimal("2730"),
}

ROLE_INTEMPERIE: dict[Role, Decimal] = {
    ROLE_CHEF: Decimal("76.50"),
    ROLE_POLISSEUR: Decimal("69.66"),
    ROLE_AIDE: Decimal("64.00"),
    ROLE_SCIEUR: Decimal("69.66"),
}

SCIE_RATE = Decimal("0.18")
STEEL_RATE = Decimal("0.075")
STEEL_THRESHOLD = Decimal("2000")
PRIME_CHANTIER_MULTIPLE = Decimal("40")
PRIME_DEPOT = Decimal("300")
PRIME_CHEF_MONTHLY = Decimal("400")

FINITIONS_15 = {"lisse durcisseur", "lisse", "balaye", "balaye mechanique", "taloche fin", "taloche machine", "taloches fin"}
FINITIONS_15_FRAGMENTS = {"lisse quartz", "lquartzo"}
FINITIONS_BRUT = {"brut"}
FINITIONS_DESACTIVE = {"desactive", "desactivee"}
DEPLACEMENT_PRIORITY = {"z1": 1, "z2": 2, "z3": 3, "z4": 4, "z5": 5, "gd": 6}

DESACTIVE_BRACKETS: list[tuple[int, int, dict[Role, Decimal]]] = [
    (0, 299, {ROLE_AIDE: Decimal("140"), ROLE_POLISSEUR: Decimal("160"), ROLE_CHEF: Decimal("180")}),
    (300, 399, {ROLE_AIDE: Decimal("170"), ROLE_POLISSEUR: Decimal("190"), ROLE_CHEF: Decimal("210")}),
    (400, 499, {ROLE_AIDE: Decimal("205"), ROLE_POLISSEUR: Decimal("225"), ROLE_CHEF: Decimal("245")}),
    (500, 599, {ROLE_AIDE: Decimal("250"), ROLE_POLISSEUR: Decimal("270"), ROLE_CHEF: Decimal("290")}),
    (600, 699, {ROLE_AIDE: Decimal("280"), ROLE_POLISSEUR: Decimal("300"), ROLE_CHEF: Decimal("320")}),
    (700, 799, {ROLE_AIDE: Decimal("290"), ROLE_POLISSEUR: Decimal("310"), ROLE_CHEF: Decimal("330")}),
]


@dataclass(frozen=True)
class Task:
    date: date
    team_code: str
    team_name: str
    employee_number: str
    employee_name: str
    chantier: str
    finish_type: str
    sqm: Decimal
    sqm_total_chantier: Decimal
    sqm_scie: Decimal
    kg_steel: Decimal
    intervention_type: str
    is_intemperie: bool = False
    distance_km: Decimal | None = None
    deplacement_type: str = ""
    effort_prime: Decimal = Decimal("0")
    effort_prime_validated: bool = False
    is_chief: bool = False


@dataclass
class DayBreakdown:
    date: date
    chantier: str
    finish_type: str
    sqm: float
    chantier_total_sqm: float
    sqm_scie: float
    kg_steel: float
    base_value: float
    finitions_value: float
    scie_value: float
    steel_value: float
    prime_multiple: float
    prime_effort: float
    prime_effort_validated: float
    prime_effort_pending: float
    forfait_used: bool
    total: float


@dataclass
class EmployeeMonthlyResult:
    employee_number: str
    employee_name: str
    team_code: str
    team_name: str
    role: Role
    business_days: int
    worked_days: int
    m2_total: float
    finitions_pay: float
    scie_total_m2: float
    scie_pay: float
    kg_total: float
    kg_pay: float
    prime_multiple: float
    prime_chef: float
    prime_depot: float
    prime_effort: float
    prime_effort_validated: float
    prime_effort_pending: float
    intemperies_total: float
    complement_minimum: float
    panier_repas: int
    grand_deplacement: int
    zone_counts: dict[str, int]
    total: float
    daily_breakdown: list[DayBreakdown]


def _normalize_label(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value or "").encode("ascii", "ignore").decode("ascii")
    return normalized.lower().strip()


def _quantize(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _count_business_days(month_start: date, month_end: date, holidays: Iterable[date] | None = None) -> int:
    holiday_set = {h for h in (holidays or []) if isinstance(h, date)}
    current = month_start
    days = 0
    while current <= month_end:
        if current.weekday() < 5 and current not in holiday_set:
            days += 1
        current += timedelta(days=1)
    return days


def _lookup_desactive(role: Role, chantier_total: Decimal) -> Decimal:
    sqm = int(chantier_total)
    for lower, upper, payouts in DESACTIVE_BRACKETS:
        if lower <= sqm <= upper:
            return payouts.get(role, Decimal("0"))
    # Use the last bracket for values above the configured ranges
    if DESACTIVE_BRACKETS:
        return DESACTIVE_BRACKETS[-1][2].get(role, Decimal("0"))
    return Decimal("0")


def _finish_payout_role(role: Role) -> Role:
    if role in {ROLE_SCIEUR, ROLE_CHEF}:
        return ROLE_POLISSEUR
    return role


def _finitions_threshold(role: Role) -> Decimal:
    payout_role = _finish_payout_role(role)
    if payout_role == ROLE_AIDE:
        return ROLE_FORFAIT[ROLE_AIDE] / Decimal("1.5")
    return Decimal("100")


def _normalize_deplacement_type(value: str) -> str | None:
    label = _normalize_label(value)
    compact = label.replace(" ", "")
    if compact in {"gd", "granddeplacement", "granddeplacements"}:
        return "gd"
    if compact in {"z1", "zone1"}:
        return "z1"
    if compact in {"z2", "zone2"}:
        return "z2"
    if compact in {"z3", "zone3"}:
        return "z3"
    if compact in {"z4", "zone4"}:
        return "z4"
    if compact in {"z5", "zone5"}:
        return "z5"
    return None


def _distance_to_deplacement_type(distance_km: Decimal | None) -> str | None:
    if distance_km is None:
        return None
    distance_float = float(distance_km)
    if distance_float > 50:
        return "gd"
    if 0 <= distance_float < 10:
        return "z1"
    if distance_float < 20:
        return "z2"
    if distance_float < 30:
        return "z3"
    if distance_float < 40:
        return "z4"
    if distance_float < 50:
        return "z5"
    return None


def _resolve_day_deplacement_type(tasks: Sequence[Task]) -> str | None:
    candidates = {
        normalized
        for normalized in (_normalize_deplacement_type(task.deplacement_type) for task in tasks)
        if normalized
    }
    if candidates:
        return max(candidates, key=lambda item: DEPLACEMENT_PRIORITY.get(item, 0))
    day_distance = max((task.distance_km for task in tasks if task.distance_km is not None), default=None)
    return _distance_to_deplacement_type(day_distance)


def _compute_finitions_value(tasks: Sequence[Task], role: Role) -> Decimal:
    payout_role = _finish_payout_role(role)
    finitions_15_sqm = Decimal("0")
    brut_sqm = Decimal("0")
    desactive_value = Decimal("0")

    for task in tasks:
        finish_norm = _normalize_label(task.finish_type)
        if finish_norm in FINITIONS_15 or any(token in finish_norm for token in FINITIONS_15_FRAGMENTS):
            finitions_15_sqm += task.sqm
        if finish_norm in FINITIONS_BRUT:
            brut_sqm += task.sqm
        if any(token in finish_norm for token in FINITIONS_DESACTIVE):
            desactive_value = max(desactive_value, _lookup_desactive(payout_role, task.sqm_total_chantier))

    candidate = Decimal("0")
    if finitions_15_sqm > _finitions_threshold(role):
        candidate = max(candidate, finitions_15_sqm * Decimal("1.5"))
    if brut_sqm > Decimal("200"):
        candidate = max(candidate, brut_sqm * Decimal("0.75"))
    candidate = max(candidate, desactive_value)
    return candidate


def _compute_day_value(tasks: Sequence[Task], role: Role) -> tuple[Decimal, Decimal, Decimal, Decimal, Decimal, bool]:
    """Return (base_value, finitions_value, scie_value, steel_value, prime_multiple, forfait_used)."""
    forfait = ROLE_FORFAIT.get(role, Decimal("0"))
    finitions_value = _compute_finitions_value(tasks, role)
    scie_value = sum((task.sqm_scie for task in tasks), start=Decimal("0")) * SCIE_RATE
    steel_total = sum((task.kg_steel for task in tasks), start=Decimal("0"))
    coulage_chantiers = {
        _normalize_label(task.chantier)
        for task in tasks
        if task.intervention_type == "coulage" and _normalize_label(task.chantier)
    }
    has_coulage = bool(coulage_chantiers)
    has_non_scie_work = any(task.intervention_type != "scie" for task in tasks)
    pure_scie_day = role == ROLE_SCIEUR and finitions_value <= Decimal("0") and not has_non_scie_work
    if steel_total > Decimal("0") and (has_coulage or steel_total > STEEL_THRESHOLD):
        steel_value = steel_total * STEEL_RATE
    else:
        steel_value = Decimal("0")
    prime_multiple = PRIME_CHANTIER_MULTIPLE if len(coulage_chantiers) >= 2 else Decimal("0")

    if role != ROLE_SCIEUR and not has_coulage and finitions_value <= Decimal("0"):
        # For non-scieurs, sciage only supplements productive coulage/finition days.
        scie_value = Decimal("0")
    elif role == ROLE_SCIEUR and not pure_scie_day and not has_coulage:
        # For scieurs, sciage supplements the day only when there is coulage.
        scie_value = Decimal("0")

    forfait_used = False
    base_value = finitions_value
    steel_only_day = steel_value > Decimal("0") and not has_coulage and finitions_value <= Decimal("0") and scie_value <= Decimal("0")

    if steel_only_day:
        base_value = Decimal("0")
    elif pure_scie_day:
        # Pure scie days for scieurs are paid either on sqm or at the forfait minimum.
        if scie_value < forfait:
            base_value = forfait
            scie_value = Decimal("0")
            forfait_used = True
        else:
            base_value = Decimal("0")
    else:
        if base_value < forfait:
            base_value = forfait
            forfait_used = True

    day_total = base_value + scie_value + steel_value + prime_multiple
    return (
        _quantize(base_value),
        _quantize(finitions_value),
        _quantize(scie_value),
        _quantize(steel_value),
        _quantize(prime_multiple),
        forfait_used,
    )


def compute_monthly_sheet(
    tasks: Sequence[Task],
    *,
    month_start: date,
    month_end: date,
    roles_by_employee: Dict[str, Role],
    depot_manager_numbers: set[str] | None = None,
    holidays: Iterable[date] | None = None,
) -> tuple[list[EmployeeMonthlyResult], dict[str, float]]:
    depot_manager_numbers = depot_manager_numbers or set()
    business_days = _count_business_days(month_start, month_end, holidays)

    grouped: dict[str, list[Task]] = {}
    for task in tasks:
        grouped.setdefault(task.employee_number, []).append(task)

    summary: list[EmployeeMonthlyResult] = []

    totals_accumulator = {
        "m2_total": Decimal("0"),
        "finitions_pay": Decimal("0"),
        "scie_total": Decimal("0"),
        "scie_pay": Decimal("0"),
        "kg_total": Decimal("0"),
        "kg_pay": Decimal("0"),
        "prime_multiple": Decimal("0"),
        "prime_chef": Decimal("0"),
        "prime_depot": Decimal("0"),
        "prime_effort": Decimal("0"),
        "prime_effort_validated": Decimal("0"),
        "prime_effort_pending": Decimal("0"),
        "intemperies_total": Decimal("0"),
        "complement_minimum": Decimal("0"),
        "total": Decimal("0"),
        "panier_repas": 0,
        "gd": 0,
        "z1": 0,
        "z2": 0,
        "z3": 0,
        "z4": 0,
        "z5": 0,
        "worked_days": 0,
    }

    for employee_number, employee_tasks in grouped.items():
        employee_tasks.sort(key=lambda t: (t.date, t.chantier, t.finish_type))
        if not employee_tasks:
            continue
        employee_name = employee_tasks[0].employee_name
        team_code = employee_tasks[0].team_code
        team_name = employee_tasks[0].team_name
        role = roles_by_employee.get(employee_number, ROLE_POLISSEUR)
        per_day: dict[date, list[Task]] = {}
        for task in employee_tasks:
            per_day.setdefault(task.date, []).append(task)

        worked_days = 0
        m2_total = Decimal("0")
        finitions_pay = Decimal("0")
        scie_total = Decimal("0")
        scie_pay = Decimal("0")
        kg_total = Decimal("0")
        kg_pay = Decimal("0")
        prime_multiple_total = Decimal("0")
        prime_effort_total = Decimal("0")
        prime_effort_validated_total = Decimal("0")
        prime_effort_pending_total = Decimal("0")
        intemperies_total = Decimal("0")
        daily_breakdown: list[DayBreakdown] = []
        zone_counts = {"z1": 0, "z2": 0, "z3": 0, "z4": 0, "z5": 0}
        grand_deplacement = 0
        panier_repas = 0
        chief_days = 0

        for day, day_tasks in sorted(per_day.items(), key=lambda kv: kv[0]):
            day_role = ROLE_CHEF if any(task.is_chief for task in day_tasks) else role
            day_effort_prime_total = sum((task.effort_prime for task in day_tasks), start=Decimal("0"))
            day_effort_prime_validated = sum(
                (task.effort_prime for task in day_tasks if task.effort_prime_validated),
                start=Decimal("0"),
            )
            day_effort_prime_pending = day_effort_prime_total - day_effort_prime_validated
            prime_effort_total += day_effort_prime_total
            prime_effort_validated_total += day_effort_prime_validated
            prime_effort_pending_total += day_effort_prime_pending
            if all(task.is_intemperie for task in day_tasks):
                pay_intemp = ROLE_INTEMPERIE.get(day_role, Decimal("0"))
                intemperies_total += pay_intemp
                chantier_total_sqm = sum(
                    (
                        total
                        for total in {
                            _normalize_label(task.chantier): task.sqm_total_chantier
                            for task in day_tasks
                            if _normalize_label(task.chantier)
                        }.values()
                    ),
                    start=Decimal("0"),
                )
                daily_breakdown.append(
                    DayBreakdown(
                        date=day,
                        chantier="; ".join({t.chantier for t in day_tasks}) or "",
                        finish_type="INTEMPERIE",
                        sqm=float(sum((t.sqm for t in day_tasks), start=Decimal("0"))),
                        chantier_total_sqm=float(_quantize(chantier_total_sqm)),
                        sqm_scie=float(sum((t.sqm_scie for t in day_tasks), start=Decimal("0"))),
                        kg_steel=float(sum((t.kg_steel for t in day_tasks), start=Decimal("0"))),
                        base_value=float(_quantize(pay_intemp)),
                        finitions_value=0.0,
                        scie_value=0.0,
                        steel_value=0.0,
                        prime_multiple=0.0,
                        prime_effort=float(_quantize(day_effort_prime_total)),
                        prime_effort_validated=float(_quantize(day_effort_prime_validated)),
                        prime_effort_pending=float(_quantize(day_effort_prime_pending)),
                        forfait_used=False,
                        total=float(_quantize(pay_intemp + day_effort_prime_validated)),
                    )
                )
                continue

            worked_days += 1
            panier_repas += 1
            if day_role == ROLE_CHEF:
                chief_days += 1
            base_value, fin_value, scie_val, steel_val, prime_mult, forfait_used = _compute_day_value(day_tasks, day_role)
            m2_total += sum((t.sqm for t in day_tasks), start=Decimal("0"))
            scie_total += sum((t.sqm_scie for t in day_tasks), start=Decimal("0"))
            kg_total += sum((t.kg_steel for t in day_tasks), start=Decimal("0"))
            finitions_pay += base_value
            scie_pay += scie_val
            kg_pay += steel_val
            prime_multiple_total += prime_mult
            chantier_total_sqm = sum(
                (
                    total
                    for total in {
                        _normalize_label(task.chantier): task.sqm_total_chantier
                        for task in day_tasks
                        if _normalize_label(task.chantier)
                    }.values()
                ),
                start=Decimal("0"),
            )

            day_deplacement_type = _resolve_day_deplacement_type(day_tasks)
            if day_deplacement_type == "gd":
                grand_deplacement += 1
            elif day_deplacement_type in zone_counts:
                zone_counts[day_deplacement_type] += 1

            day_total = base_value + scie_val + steel_val + prime_mult + _quantize(day_effort_prime_validated)
            daily_breakdown.append(
                DayBreakdown(
                    date=day,
                    chantier="; ".join({t.chantier for t in day_tasks}) or "",
                    finish_type=", ".join({t.finish_type for t in day_tasks}),
                    sqm=float(sum((t.sqm for t in day_tasks), start=Decimal("0"))),
                    chantier_total_sqm=float(_quantize(chantier_total_sqm)),
                    sqm_scie=float(sum((t.sqm_scie for t in day_tasks), start=Decimal("0"))),
                    kg_steel=float(sum((t.kg_steel for t in day_tasks), start=Decimal("0"))),
                    base_value=float(base_value),
                    finitions_value=float(fin_value),
                    scie_value=float(scie_val),
                    steel_value=float(steel_val),
                    prime_multiple=float(prime_mult),
                    prime_effort=float(_quantize(day_effort_prime_total)),
                    prime_effort_validated=float(_quantize(day_effort_prime_validated)),
                    prime_effort_pending=float(_quantize(day_effort_prime_pending)),
                    forfait_used=forfait_used,
                    total=float(day_total),
                )
            )

        prime_chef = Decimal("0")
        if chief_days and business_days:
            payable_chief_days = min(chief_days, business_days)
            prime_chef = PRIME_CHEF_MONTHLY / Decimal(business_days) * Decimal(payable_chief_days)
        prime_depot = PRIME_DEPOT if employee_number in depot_manager_numbers and role == ROLE_SCIEUR else Decimal("0")

        min_value = Decimal("0")
        if role in ROLE_MINIMUM and business_days:
            min_value = ROLE_MINIMUM[role] / Decimal(business_days) * Decimal(worked_days)

        monthly_without_intemp = finitions_pay + scie_pay + kg_pay + prime_multiple_total + prime_effort_validated_total
        complement_minimum = Decimal("0")
        if monthly_without_intemp < min_value:
            complement_minimum = min_value - monthly_without_intemp
        total_pay = monthly_without_intemp + complement_minimum + prime_chef + prime_depot + intemperies_total

        summary.append(
            EmployeeMonthlyResult(
                employee_number=employee_number,
                employee_name=employee_name,
                team_code=team_code,
                team_name=team_name,
                role=role,
                business_days=business_days,
                worked_days=worked_days,
                m2_total=float(_quantize(m2_total)),
                finitions_pay=float(_quantize(finitions_pay)),
                scie_total_m2=float(_quantize(scie_total)),
                scie_pay=float(_quantize(scie_pay)),
                kg_total=float(_quantize(kg_total)),
                kg_pay=float(_quantize(kg_pay)),
                prime_multiple=float(_quantize(prime_multiple_total)),
                prime_chef=float(_quantize(prime_chef)),
                prime_depot=float(_quantize(prime_depot)),
                prime_effort=float(_quantize(prime_effort_total)),
                prime_effort_validated=float(_quantize(prime_effort_validated_total)),
                prime_effort_pending=float(_quantize(prime_effort_pending_total)),
                intemperies_total=float(_quantize(intemperies_total)),
                complement_minimum=float(_quantize(complement_minimum)),
                panier_repas=panier_repas,
                grand_deplacement=grand_deplacement,
                zone_counts=zone_counts,
                total=float(_quantize(total_pay)),
                daily_breakdown=daily_breakdown,
            )
        )

        totals_accumulator["m2_total"] += m2_total
        totals_accumulator["finitions_pay"] += finitions_pay
        totals_accumulator["scie_total"] += scie_total
        totals_accumulator["scie_pay"] += scie_pay
        totals_accumulator["kg_total"] += kg_total
        totals_accumulator["kg_pay"] += kg_pay
        totals_accumulator["prime_multiple"] += prime_multiple_total
        totals_accumulator["prime_chef"] += prime_chef
        totals_accumulator["prime_depot"] += prime_depot
        totals_accumulator["prime_effort"] += prime_effort_total
        totals_accumulator["prime_effort_validated"] += prime_effort_validated_total
        totals_accumulator["prime_effort_pending"] += prime_effort_pending_total
        totals_accumulator["intemperies_total"] += intemperies_total
        totals_accumulator["complement_minimum"] += complement_minimum
        totals_accumulator["total"] += total_pay
        totals_accumulator["panier_repas"] += panier_repas
        totals_accumulator["gd"] += grand_deplacement
        totals_accumulator["z1"] += zone_counts["z1"]
        totals_accumulator["z2"] += zone_counts["z2"]
        totals_accumulator["z3"] += zone_counts["z3"]
        totals_accumulator["z4"] += zone_counts["z4"]
        totals_accumulator["z5"] += zone_counts["z5"]
        totals_accumulator["worked_days"] += worked_days

    summary.sort(key=lambda r: (r.team_code, r.employee_name.lower()))

    totals = {
        "team_code": "Total",
        "employee_name": "",
        "business_days": business_days,
        "worked_days": totals_accumulator["worked_days"],
        "m2_total": float(_quantize(totals_accumulator["m2_total"])),
        "finitions_pay": float(_quantize(totals_accumulator["finitions_pay"])),
        "scie_total": float(_quantize(totals_accumulator["scie_total"])),
        "scie_pay": float(_quantize(totals_accumulator["scie_pay"])),
        "kg_total": float(_quantize(totals_accumulator["kg_total"])),
        "kg_pay": float(_quantize(totals_accumulator["kg_pay"])),
        "prime_multiple": float(_quantize(totals_accumulator["prime_multiple"])),
        "prime_chef": float(_quantize(totals_accumulator["prime_chef"])),
        "prime_depot": float(_quantize(totals_accumulator["prime_depot"])),
        "prime_effort": float(_quantize(totals_accumulator["prime_effort"])),
        "prime_effort_validated": float(_quantize(totals_accumulator["prime_effort_validated"])),
        "prime_effort_pending": float(_quantize(totals_accumulator["prime_effort_pending"])),
        "intemperies_total": float(_quantize(totals_accumulator["intemperies_total"])),
        "complement_minimum": float(_quantize(totals_accumulator["complement_minimum"])),
        "panier_repas": totals_accumulator["panier_repas"],
        "gd": totals_accumulator["gd"],
        "z1": totals_accumulator["z1"],
        "z2": totals_accumulator["z2"],
        "z3": totals_accumulator["z3"],
        "z4": totals_accumulator["z4"],
        "z5": totals_accumulator["z5"],
        "total": float(_quantize(totals_accumulator["total"])),
    }

    return summary, totals
