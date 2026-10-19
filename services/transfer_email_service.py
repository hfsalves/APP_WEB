from __future__ import annotations

from datetime import date, datetime
from html import escape


def _clean(value) -> str:
    return str(value or "").strip()


def _date_pt(value) -> str:
    if isinstance(value, datetime):
        value = value.date()
    if isinstance(value, date):
        return value.strftime("%d/%m/%Y")
    raw = _clean(value)
    if not raw:
        return ""
    try:
        return date.fromisoformat(raw[:10]).strftime("%d/%m/%Y")
    except ValueError:
        return raw


def build_transfer_confirmation_email(data: dict) -> dict[str, str]:
    """Build the bilingual commercial confirmation sent for a transfer request."""
    reservation = _clean(data.get("reservation"))
    accommodation = _clean(data.get("accommodation"))
    address = _clean(data.get("address"))
    guest_name = _clean(data.get("guest_name"))
    people_count = _clean(data.get("people_count"))
    guest_phone = _clean(data.get("guest_phone"))
    guest_email = _clean(data.get("guest_email"))
    movement_kind = _clean(data.get("movement_kind")).lower() or "arrival"
    route_label_pt = _clean(data.get("route_label_pt") or data.get("arrival_point_pt"))
    route_label_en = _clean(data.get("route_label_en") or data.get("arrival_point_en"))
    service_date = _date_pt(data.get("service_date") or data.get("arrival_date"))
    service_time = _clean(data.get("service_time") or data.get("arrival_time"))
    flight = _clean(data.get("flight")) or "—"
    transfer_id = _clean(data.get("transfer_id"))
    driver_phone = _clean(data.get("driver_phone"))
    departure_date = _date_pt(data.get("departure_date"))
    departure_time = _clean(data.get("departure_time"))

    movement_pt = f"{route_label_pt} — {service_date} às {service_time}".strip()
    movement_en = f"{route_label_en} — {service_date} at {service_time}".strip()
    departure_pt = f"{departure_date} às {departure_time}" if departure_date and departure_time else ""
    departure_en = f"{departure_date} at {departure_time}" if departure_date and departure_time else ""

    pt_rows = [
        ("Reserva", reservation),
        ("Alojamento", accommodation),
        ("Morada", address),
        ("Nome do hóspede", guest_name),
        ("N.º de pessoas", people_count),
        ("Contacto telef.", guest_phone),
        ("Email", guest_email),
        ("Partida" if movement_kind == "departure" else "Chegada", movement_pt),
        ("Voo", flight),
    ]
    en_rows = [
        ("Booking", reservation),
        ("Accommodation", accommodation),
        ("Address", address),
        ("Guest name", guest_name),
        ("Number of guests", people_count),
        ("Phone", guest_phone),
        ("Email", guest_email),
        ("Departure" if movement_kind == "departure" else "Arrival", movement_en),
        ("Flight", flight),
    ]
    if departure_pt:
        pt_rows.append(("Partida", departure_pt))
        en_rows.append(("Departure", departure_en))
    pt_rows.extend([
        ("Valor", "30 EUR por viagem, pago ao motorista."),
        ("Transfer", transfer_id),
        ("Contacto do motorista", driver_phone),
    ])
    en_rows.extend([
        ("Price", "EUR 30 per trip, paid directly to the driver."),
        ("Transfer", transfer_id),
        ("Driver contact", driver_phone),
    ])

    def text_section(title: str, rows: list[tuple[str, str]]) -> str:
        return "\n".join([title, "", *[f"{label}: {value}" for label, value in rows]])

    body_text = (
        text_section("PEDIDO DE TRANSFER CONFIRMADO", pt_rows)
        + "\n\n----------------------------------------\n\n"
        + text_section("TRANSFER REQUEST CONFIRMED", en_rows)
    )

    def html_rows(rows: list[tuple[str, str]]) -> str:
        return "".join(
            '<tr><td style="padding:7px 12px;color:#64748b;width:180px;vertical-align:top;">'
            f"{escape(label)}</td>"
            '<td style="padding:7px 12px;color:#0f172a;font-weight:600;vertical-align:top;">'
            f"{escape(value) or '&mdash;'}</td></tr>"
            for label, value in rows
        )

    body_html = f"""
<!doctype html>
<html lang="pt">
  <body style="margin:0;background:#f1f5f9;font-family:Arial,Helvetica,sans-serif;color:#0f172a;">
    <div style="max-width:720px;margin:0 auto;padding:28px 14px;">
      <div style="background:#063f72;color:#fff;padding:22px 26px;border-radius:14px 14px 0 0;">
        <div style="font-size:13px;letter-spacing:.08em;text-transform:uppercase;opacity:.78;">GuestSpaTur</div>
        <h1 style="font-size:23px;line-height:1.25;margin:7px 0 0;">Pedido de transfer confirmado</h1>
        <div style="font-size:15px;margin-top:5px;opacity:.86;">Transfer request confirmed</div>
      </div>
      <div style="background:#fff;border:1px solid #dbe4ee;border-top:0;padding:24px 18px;border-radius:0 0 14px 14px;">
        <h2 style="font-size:17px;color:#063f72;margin:0 8px 12px;">Português</h2>
        <table role="presentation" style="width:100%;border-collapse:collapse;font-size:14px;">{html_rows(pt_rows)}</table>
        <div style="height:1px;background:#dbe4ee;margin:24px 8px;"></div>
        <h2 style="font-size:17px;color:#063f72;margin:0 8px 12px;">English</h2>
        <table role="presentation" style="width:100%;border-collapse:collapse;font-size:14px;">{html_rows(en_rows)}</table>
      </div>
    </div>
  </body>
</html>
""".strip()

    return {
        "subject": f"Transfer confirmado / Transfer confirmed — {reservation}",
        "body_text": body_text,
        "body_html": body_html,
    }
