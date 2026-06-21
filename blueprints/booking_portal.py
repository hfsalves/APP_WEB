from __future__ import annotations

from datetime import date

from flask import Blueprint, abort, make_response, render_template, request, url_for

from services.booking_portal_service import (
    alojamento_disponivel,
    calcular_preco,
    get_alojamento,
    get_alojamentos_disponiveis,
    get_noites_ocupadas,
)


bp = Blueprint("booking_portal", __name__)

SUPPORTED_LANGS = ("pt", "en", "es", "fr")
LANG_COOKIE = "portobreak_lang"

TRANSLATIONS = {
    "pt": {
        "page_reservations": "Reservas",
        "local_stay": "Alojamento local",
        "hero_title": "Reserve a sua pausa no Porto.",
        "hero_lead": "Apartamentos selecionados, pesquisa direta por datas e disponibilidade em tempo real.",
        "availability": "Disponibilidade",
        "results_found": "Resultados encontrados",
        "available_stays": "Alojamentos disponiveis",
        "stay": "alojamento",
        "stays": "alojamentos",
        "checkin": "Check-in",
        "checkout": "Check-out",
        "guests": "Hospedes",
        "guest": "hospede",
        "name_location": "Nome ou localizacao",
        "search_placeholder": "Porto, centro, estudio...",
        "search": "Pesquisar",
        "searching": "A pesquisar...",
        "from": "desde",
        "price_on_request": "Preco sob consulta",
        "view_stay": "Ver alojamento",
        "empty_title": "Nao encontramos alojamentos para esta pesquisa.",
        "empty_text": "Ajuste as datas, o numero de hospedes ou a localizacao.",
        "clear_search": "Limpar pesquisa",
        "stay_label": "Alojamento",
        "estimate": "Estimativa",
        "night": "noite",
        "nights": "noites",
        "per_night": "por noite",
        "choose": "A escolher",
        "available_selected": "Disponivel para as datas selecionadas",
        "unavailable_selected": "Indisponivel para as datas selecionadas",
        "choose_dates_status": "Escolha datas para confirmar disponibilidade",
        "previous_month": "Mes anterior",
        "next_month": "Mes seguinte",
        "calendar": "Calendario",
        "weekdays": ["Seg", "Ter", "Qua", "Qui", "Sex", "Sab", "Dom"],
        "months": ["Janeiro", "Fevereiro", "Marco", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"],
        "calendar_start": "Escolha a data de entrada e depois a data de saida.",
        "free": "Livre",
        "occupied_night": "Noite ocupada",
        "selected": "Selecionado",
        "update": "Atualizar",
        "request_soon": "Pedido de reserva em breve",
        "calendar_pick_free": "Escolha uma noite livre para iniciar a estadia.",
        "calendar_pick_checkout": "Agora escolha a data de saida.",
        "calendar_range_occupied": "O intervalo escolhido cruza noites ocupadas.",
        "calendar_dates_selected": "Datas selecionadas. Atualize para recalcular disponibilidade e preco.",
        "calendar_need_dates": "Escolha a data de entrada e a data de saida.",
        "invalid_date": "Data invalida.",
        "invalid_guests": "Indique um numero de hospedes valido.",
        "need_dates": "Indique as datas de check-in e check-out.",
        "checkout_after_checkin": "A data de check-out deve ser posterior ao check-in.",
        "nights_line": "Noites",
        "cleaning_fee": "Taxa de limpeza",
        "tourist_tax": "Taxa turistica",
        "day": "dia",
        "days": "dias",
    },
    "en": {
        "page_reservations": "Bookings",
        "local_stay": "Short-term rentals",
        "hero_title": "Book your Porto break.",
        "hero_lead": "Selected apartments, direct date search and real-time availability.",
        "availability": "Availability",
        "results_found": "Results found",
        "available_stays": "Available stays",
        "stay": "stay",
        "stays": "stays",
        "checkin": "Check-in",
        "checkout": "Check-out",
        "guests": "Guests",
        "guest": "guest",
        "name_location": "Name or location",
        "search_placeholder": "Porto, centre, studio...",
        "search": "Search",
        "searching": "Searching...",
        "from": "from",
        "price_on_request": "Price on request",
        "view_stay": "View stay",
        "empty_title": "No stays matched this search.",
        "empty_text": "Adjust the dates, number of guests or location.",
        "clear_search": "Clear search",
        "stay_label": "Stay",
        "estimate": "Estimate",
        "night": "night",
        "nights": "nights",
        "per_night": "per night",
        "choose": "To choose",
        "available_selected": "Available for the selected dates",
        "unavailable_selected": "Unavailable for the selected dates",
        "choose_dates_status": "Choose dates to confirm availability",
        "previous_month": "Previous month",
        "next_month": "Next month",
        "calendar": "Calendar",
        "weekdays": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
        "months": ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"],
        "calendar_start": "Choose the check-in date and then the check-out date.",
        "free": "Free",
        "occupied_night": "Occupied night",
        "selected": "Selected",
        "update": "Update",
        "request_soon": "Booking request coming soon",
        "calendar_pick_free": "Choose a free night to start the stay.",
        "calendar_pick_checkout": "Now choose the check-out date.",
        "calendar_range_occupied": "The selected range crosses occupied nights.",
        "calendar_dates_selected": "Dates selected. Update to recalculate availability and price.",
        "calendar_need_dates": "Choose the check-in and check-out dates.",
        "invalid_date": "Invalid date.",
        "invalid_guests": "Enter a valid number of guests.",
        "need_dates": "Enter both check-in and check-out dates.",
        "checkout_after_checkin": "Check-out must be after check-in.",
        "nights_line": "Nights",
        "cleaning_fee": "Cleaning fee",
        "tourist_tax": "Tourist tax",
        "day": "day",
        "days": "days",
    },
    "es": {
        "page_reservations": "Reservas",
        "local_stay": "Alojamiento turistico",
        "hero_title": "Reserva tu pausa en Oporto.",
        "hero_lead": "Apartamentos seleccionados, busqueda directa por fechas y disponibilidad en tiempo real.",
        "availability": "Disponibilidad",
        "results_found": "Resultados encontrados",
        "available_stays": "Alojamientos disponibles",
        "stay": "alojamiento",
        "stays": "alojamientos",
        "checkin": "Entrada",
        "checkout": "Salida",
        "guests": "Huespedes",
        "guest": "huesped",
        "name_location": "Nombre o ubicacion",
        "search_placeholder": "Oporto, centro, estudio...",
        "search": "Buscar",
        "searching": "Buscando...",
        "from": "desde",
        "price_on_request": "Precio bajo consulta",
        "view_stay": "Ver alojamiento",
        "empty_title": "No encontramos alojamientos para esta busqueda.",
        "empty_text": "Ajusta las fechas, el numero de huespedes o la ubicacion.",
        "clear_search": "Limpiar busqueda",
        "stay_label": "Alojamiento",
        "estimate": "Estimacion",
        "night": "noche",
        "nights": "noches",
        "per_night": "por noche",
        "choose": "Por elegir",
        "available_selected": "Disponible para las fechas seleccionadas",
        "unavailable_selected": "No disponible para las fechas seleccionadas",
        "choose_dates_status": "Elige fechas para confirmar disponibilidad",
        "previous_month": "Mes anterior",
        "next_month": "Mes siguiente",
        "calendar": "Calendario",
        "weekdays": ["Lun", "Mar", "Mie", "Jue", "Vie", "Sab", "Dom"],
        "months": ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"],
        "calendar_start": "Elige la fecha de entrada y despues la fecha de salida.",
        "free": "Libre",
        "occupied_night": "Noche ocupada",
        "selected": "Seleccionado",
        "update": "Actualizar",
        "request_soon": "Solicitud de reserva proximamente",
        "calendar_pick_free": "Elige una noche libre para iniciar la estancia.",
        "calendar_pick_checkout": "Ahora elige la fecha de salida.",
        "calendar_range_occupied": "El intervalo elegido cruza noches ocupadas.",
        "calendar_dates_selected": "Fechas seleccionadas. Actualiza para recalcular disponibilidad y precio.",
        "calendar_need_dates": "Elige la fecha de entrada y la fecha de salida.",
        "invalid_date": "Fecha invalida.",
        "invalid_guests": "Indica un numero valido de huespedes.",
        "need_dates": "Indica las fechas de entrada y salida.",
        "checkout_after_checkin": "La salida debe ser posterior a la entrada.",
        "nights_line": "Noches",
        "cleaning_fee": "Tasa de limpieza",
        "tourist_tax": "Tasa turistica",
        "day": "dia",
        "days": "dias",
    },
    "fr": {
        "page_reservations": "Reservations",
        "local_stay": "Location courte duree",
        "hero_title": "Reservez votre pause a Porto.",
        "hero_lead": "Appartements selectionnes, recherche directe par dates et disponibilite en temps reel.",
        "availability": "Disponibilite",
        "results_found": "Resultats trouves",
        "available_stays": "Logements disponibles",
        "stay": "logement",
        "stays": "logements",
        "checkin": "Arrivee",
        "checkout": "Depart",
        "guests": "Voyageurs",
        "guest": "voyageur",
        "name_location": "Nom ou emplacement",
        "search_placeholder": "Porto, centre, studio...",
        "search": "Rechercher",
        "searching": "Recherche...",
        "from": "a partir de",
        "price_on_request": "Prix sur demande",
        "view_stay": "Voir le logement",
        "empty_title": "Aucun logement ne correspond a cette recherche.",
        "empty_text": "Modifiez les dates, le nombre de voyageurs ou l'emplacement.",
        "clear_search": "Effacer la recherche",
        "stay_label": "Logement",
        "estimate": "Estimation",
        "night": "nuit",
        "nights": "nuits",
        "per_night": "par nuit",
        "choose": "A choisir",
        "available_selected": "Disponible pour les dates selectionnees",
        "unavailable_selected": "Indisponible pour les dates selectionnees",
        "choose_dates_status": "Choisissez des dates pour confirmer la disponibilite",
        "previous_month": "Mois precedent",
        "next_month": "Mois suivant",
        "calendar": "Calendrier",
        "weekdays": ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"],
        "months": ["Janvier", "Fevrier", "Mars", "Avril", "Mai", "Juin", "Juillet", "Aout", "Septembre", "Octobre", "Novembre", "Decembre"],
        "calendar_start": "Choisissez la date d'arrivee puis la date de depart.",
        "free": "Libre",
        "occupied_night": "Nuit occupee",
        "selected": "Selectionne",
        "update": "Mettre a jour",
        "request_soon": "Demande de reservation bientot disponible",
        "calendar_pick_free": "Choisissez une nuit libre pour commencer le sejour.",
        "calendar_pick_checkout": "Choisissez maintenant la date de depart.",
        "calendar_range_occupied": "La periode choisie traverse des nuits occupees.",
        "calendar_dates_selected": "Dates selectionnees. Mettez a jour pour recalculer disponibilite et prix.",
        "calendar_need_dates": "Choisissez les dates d'arrivee et de depart.",
        "invalid_date": "Date invalide.",
        "invalid_guests": "Indiquez un nombre de voyageurs valide.",
        "need_dates": "Indiquez les dates d'arrivee et de depart.",
        "checkout_after_checkin": "La date de depart doit etre apres l'arrivee.",
        "nights_line": "Nuits",
        "cleaning_fee": "Frais de menage",
        "tourist_tax": "Taxe de sejour",
        "day": "jour",
        "days": "jours",
    },
}

LANG_LABELS = {
    "pt": "PT",
    "en": "EN",
    "es": "ES",
    "fr": "FR",
}


def _resolve_lang():
    candidate = str(request.args.get("lang") or request.cookies.get(LANG_COOKIE) or "").strip().lower()
    if candidate in SUPPORTED_LANGS:
        return candidate
    best = request.accept_languages.best_match(SUPPORTED_LANGS)
    return best if best in SUPPORTED_LANGS else "pt"


def _t(lang):
    return TRANSLATIONS.get(lang) or TRANSLATIONS["pt"]


def _lang_url(lang):
    args = request.args.to_dict(flat=True)
    args["lang"] = lang
    try:
        return url_for(request.endpoint, **(request.view_args or {}), **args)
    except Exception:
        return url_for("booking_portal.index", lang=lang)


def _language_links(active_lang):
    return [
        {
            "code": code,
            "label": LANG_LABELS.get(code, code.upper()),
            "url": _lang_url(code),
            "active": code == active_lang,
        }
        for code in SUPPORTED_LANGS
    ]


def _with_lang_cookie(response, lang):
    response.set_cookie(LANG_COOKIE, lang, max_age=60 * 60 * 24 * 365, samesite="Lax")
    return response


def _render_booking_template(template, lang, **context):
    response = make_response(render_template(
        template,
        lang=lang,
        t=_t(lang),
        language_links=_language_links(lang),
        **context,
    ))
    return _with_lang_cookie(response, lang)


def _parse_date_arg(name: str):
    value = str(request.args.get(name) or "").strip()
    if not value:
        return None, ""
    try:
        return date.fromisoformat(value), ""
    except Exception:
            return None, "invalid_date"


def _parse_hospedes_arg():
    value = str(request.args.get("hospedes") or "").strip()
    if not value:
        return None, ""
    try:
        number = int(value)
        if number <= 0 or number > 50:
                return None, "invalid_guests"
        return number, ""
    except Exception:
        return None, "invalid_guests"


def _search_params(lang):
    t = _t(lang)
    checkin, checkin_error = _parse_date_arg("checkin")
    checkout, checkout_error = _parse_date_arg("checkout")
    hospedes, hospedes_error = _parse_hospedes_arg()
    query = str(request.args.get("q") or request.args.get("query") or "").strip()

    errors = []
    for error in (checkin_error, checkout_error, hospedes_error):
        if error and error not in errors:
            errors.append(t.get(error, error))

    if (checkin and not checkout) or (checkout and not checkin):
        errors.append(t["need_dates"])
    if checkin and checkout and checkout <= checkin:
        errors.append(t["checkout_after_checkin"])

    return {
        "checkin": checkin,
        "checkout": checkout,
        "hospedes": hospedes,
        "query": query,
        "errors": errors,
        "has_search": any([checkin, checkout, hospedes, query]),
        "raw": {
            "checkin": request.args.get("checkin", ""),
            "checkout": request.args.get("checkout", ""),
            "hospedes": request.args.get("hospedes", ""),
            "query": query,
            "lang": lang,
        },
    }


def _detail_url(al_id: str, params: dict):
    query = {}
    for key in ("checkin", "checkout", "hospedes"):
        value = (params.get("raw") or {}).get(key)
        if value:
            query[key] = value
    lang = (params.get("raw") or {}).get("lang")
    if lang:
        query["lang"] = lang
    return url_for("booking_portal.detail", al_id=al_id, **query)


def _translate_price(preco, t):
    if not preco:
        return preco
    translated = dict(preco)
    if translated.get("valor"):
        noites = int(translated.get("noites") or 0)
        hospedes = int(translated.get("hospedes") or 1)
        dias_taxa = int(translated.get("taxa_turistica_dias") or 0)
        translated["linhas"] = [
            {"label": f"{t['nights_line']} ({noites})", "value": translated.get("preco_noites_label", "")},
            {"label": t["cleaning_fee"], "value": translated.get("limpeza_label", "")},
            {
                "label": (
                    f"{t['tourist_tax']} ({hospedes} "
                    f"{t['guest'] if hospedes == 1 else t['guests']} x {dias_taxa} "
                    f"{t['day'] if dias_taxa == 1 else t['days']})"
                ),
                "value": translated.get("taxa_turistica_label", ""),
            },
        ]
    else:
        translated["label"] = t["price_on_request"] if translated.get("label") == "Preco sob consulta" else translated.get("label")
    return translated


@bp.route("/portal-reservas")
@bp.route("/reservas")
def index():
    lang = _resolve_lang()
    params = _search_params(lang)
    query_allowed = not params["errors"]
    alojamentos = get_alojamentos_disponiveis(
        checkin=params["checkin"] if query_allowed else None,
        checkout=params["checkout"] if query_allowed else None,
        hospedes=params["hospedes"] if query_allowed else None,
        query=params["query"] if query_allowed else None,
    )
    for alojamento in alojamentos:
        alojamento["detail_url"] = _detail_url(alojamento["id"], params)

    return _render_booking_template(
        "booking_portal/index.html",
        lang,
        alojamentos=alojamentos,
        search=params,
        page_title=_t(lang)["page_reservations"],
    )


@bp.route("/portal-reservas/alojamento/<al_id>")
@bp.route("/reservas/<al_id>")
def detail(al_id):
    lang = _resolve_lang()
    params = _search_params(lang)
    t = _t(lang)
    alojamento = get_alojamento(al_id)
    if not alojamento:
        abort(404)

    disponibilidade = None
    preco = _translate_price(calcular_preco(al_id, params["checkin"], params["checkout"], params["hospedes"]), t)
    if params["checkin"] and params["checkout"] and not params["errors"]:
        disponibilidade = alojamento_disponivel(al_id, params["checkin"], params["checkout"])

    calendar_start = (params["checkin"] or date.today()).replace(day=1)
    calendario = {
        "initial_month": calendar_start.isoformat(),
        "occupied": get_noites_ocupadas(al_id, start=calendar_start, months=12),
    }

    return _render_booking_template(
        "booking_portal/detail.html",
        lang,
        alojamento=alojamento,
        search=params,
        disponibilidade=disponibilidade,
        preco=preco,
        calendario=calendario,
        page_title=alojamento["nome"],
    )
