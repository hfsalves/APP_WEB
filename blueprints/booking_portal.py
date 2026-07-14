from __future__ import annotations

from datetime import date

from flask import Blueprint, abort, jsonify, make_response, render_template, request, url_for

from services.booking_portal_service import (
    alojamento_disponivel,
    calcular_preco,
    get_alojamento,
    get_alojamentos_disponiveis_page,
    get_noites_ocupadas,
)


bp = Blueprint("booking_portal", __name__)

SUPPORTED_LANGS = ("pt", "en", "es", "fr")
LANG_COOKIE = "portobreak_lang"
BOOKING_PAGE_SIZE = 18

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
        "adults": "Adultos",
        "children": "Criancas",
        "babies": "Bebes",
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
        "need_adult": "Indique pelo menos 1 adulto quando existem criancas ou bebes.",
        "adults_capacity_error": "Este alojamento permite no maximo {max} adulto(s).",
        "total_capacity_error": "Este alojamento permite no maximo {max} hospede(s), excluindo bebes.",
        "babies_capacity_error": "Este alojamento permite no maximo 2 bebes.",
        "crib_one_only": "So e possivel colocar um berco neste alojamento.",
        "crib_unavailable": "Neste alojamento nao e possivel a colocacao de berco.",
        "need_dates": "Indique as datas de check-in e check-out.",
        "checkout_after_checkin": "A data de check-out deve ser posterior ao check-in.",
        "nights_line": "Noites",
        "extra_guests_line": "Hospedes extra",
        "cleaning_fee": "Taxa de limpeza",
        "tourist_tax": "Taxa turistica",
        "day": "dia",
        "days": "dias",
        "page": "Pagina",
        "previous": "Anterior",
        "next": "Seguinte",
        "location": "Localizacao",
        "map_hint": "Zona aproximada do alojamento",
        "open_map": "Abrir mapa",
        "close": "Fechar",
        "map_unavailable": "Localizacao indisponivel",
        "read_more": "Ver mais",
        "read_less": "Ver menos",
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
        "adults": "Adults",
        "children": "Children",
        "babies": "Babies",
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
        "need_adult": "Enter at least 1 adult when children or babies are included.",
        "adults_capacity_error": "This stay allows up to {max} adult(s).",
        "total_capacity_error": "This stay allows up to {max} guest(s), excluding babies.",
        "babies_capacity_error": "This stay allows up to 2 babies.",
        "crib_one_only": "Only one crib can be placed in this stay.",
        "crib_unavailable": "A crib cannot be placed in this stay.",
        "need_dates": "Enter both check-in and check-out dates.",
        "checkout_after_checkin": "Check-out must be after check-in.",
        "nights_line": "Nights",
        "extra_guests_line": "Extra guests",
        "cleaning_fee": "Cleaning fee",
        "tourist_tax": "Tourist tax",
        "day": "day",
        "days": "days",
        "page": "Page",
        "previous": "Previous",
        "next": "Next",
        "location": "Location",
        "map_hint": "Approximate stay location",
        "open_map": "Open map",
        "close": "Close",
        "map_unavailable": "Location unavailable",
        "read_more": "Read more",
        "read_less": "Show less",
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
        "adults": "Adultos",
        "children": "Ninos",
        "babies": "Bebes",
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
        "need_adult": "Indica al menos 1 adulto cuando hay ninos o bebes.",
        "adults_capacity_error": "Este alojamiento permite como maximo {max} adulto(s).",
        "total_capacity_error": "Este alojamiento permite como maximo {max} huesped(es), sin contar bebes.",
        "babies_capacity_error": "Este alojamiento permite como maximo 2 bebes.",
        "crib_one_only": "Solo es posible colocar una cuna en este alojamiento.",
        "crib_unavailable": "En este alojamiento no es posible colocar una cuna.",
        "need_dates": "Indica las fechas de entrada y salida.",
        "checkout_after_checkin": "La salida debe ser posterior a la entrada.",
        "nights_line": "Noches",
        "extra_guests_line": "Huespedes extra",
        "cleaning_fee": "Tasa de limpieza",
        "tourist_tax": "Tasa turistica",
        "day": "dia",
        "days": "dias",
        "page": "Pagina",
        "previous": "Anterior",
        "next": "Siguiente",
        "location": "Ubicacion",
        "map_hint": "Zona aproximada del alojamiento",
        "open_map": "Abrir mapa",
        "close": "Cerrar",
        "map_unavailable": "Ubicacion no disponible",
        "read_more": "Ver mas",
        "read_less": "Ver menos",
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
        "adults": "Adultes",
        "children": "Enfants",
        "babies": "Bebes",
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
        "need_adult": "Indiquez au moins 1 adulte lorsqu'il y a des enfants ou des bebes.",
        "adults_capacity_error": "Ce logement accepte au maximum {max} adulte(s).",
        "total_capacity_error": "Ce logement accepte au maximum {max} voyageur(s), hors bebes.",
        "babies_capacity_error": "Ce logement accepte au maximum 2 bebes.",
        "crib_one_only": "Un seul lit bebe peut etre installe dans ce logement.",
        "crib_unavailable": "Il n'est pas possible d'installer un lit bebe dans ce logement.",
        "need_dates": "Indiquez les dates d'arrivee et de depart.",
        "checkout_after_checkin": "La date de depart doit etre apres l'arrivee.",
        "nights_line": "Nuits",
        "extra_guests_line": "Voyageurs supplementaires",
        "cleaning_fee": "Frais de menage",
        "tourist_tax": "Taxe de sejour",
        "day": "jour",
        "days": "jours",
        "page": "Page",
        "previous": "Precedent",
        "next": "Suivant",
        "location": "Emplacement",
        "map_hint": "Zone approximative du logement",
        "open_map": "Ouvrir la carte",
        "close": "Fermer",
        "map_unavailable": "Emplacement indisponible",
        "read_more": "Lire plus",
        "read_less": "Lire moins",
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


def _parse_people_arg(name, *, minimum=0, maximum=50):
    value = str(request.args.get(name) or "").strip()
    if not value:
        return None, ""
    try:
        number = int(value)
        if number < minimum or number > maximum:
            return None, "invalid_guests"
        return number, ""
    except Exception:
        return None, "invalid_guests"


def _search_params(lang):
    t = _t(lang)
    checkin, checkin_error = _parse_date_arg("checkin")
    checkout, checkout_error = _parse_date_arg("checkout")
    has_party_args = any(name in request.args for name in ("adultos", "criancas", "bebes"))
    adultos, adultos_error = _parse_people_arg("adultos", minimum=1)
    criancas, criancas_error = _parse_people_arg("criancas", minimum=0)
    bebes, bebes_error = _parse_people_arg("bebes", minimum=0)
    hospedes_legacy, hospedes_error = _parse_people_arg("hospedes", minimum=1)
    if not has_party_args and hospedes_legacy:
        adultos = hospedes_legacy
    hospedes = ((adultos or 0) + (criancas or 0)) if (adultos or criancas) else hospedes_legacy
    query = str(request.args.get("q") or request.args.get("query") or "").strip()

    errors = []
    error_keys = set()
    for error in (checkin_error, checkout_error, adultos_error, criancas_error, bebes_error, hospedes_error):
        if error and error not in error_keys:
            errors.append(t.get(error, error))
            error_keys.add(error)

    if (criancas or bebes) and not adultos:
        errors.append(t["need_adult"])
    if (checkin and not checkout) or (checkout and not checkin):
        errors.append(t["need_dates"])
    if checkin and checkout and checkout <= checkin:
        errors.append(t["checkout_after_checkin"])

    guest_summary = []
    if adultos:
        guest_summary.append(f"{adultos} {t['adults']}")
    if criancas:
        guest_summary.append(f"{criancas} {t['children']}")
    if bebes:
        guest_summary.append(f"{bebes} {t['babies']}")

    return {
        "checkin": checkin,
        "checkout": checkout,
        "hospedes": hospedes,
        "adultos": adultos,
        "criancas": criancas or 0,
        "bebes": bebes or 0,
        "query": query,
        "errors": errors,
        "guest_summary": " / ".join(guest_summary),
        "has_search": any([checkin, checkout, hospedes, bebes, query]),
        "raw": {
            "checkin": request.args.get("checkin", ""),
            "checkout": request.args.get("checkout", ""),
            "hospedes": request.args.get("hospedes", ""),
            "adultos": request.args.get("adultos", str(adultos or "") if (not has_party_args and hospedes_legacy) else ""),
            "criancas": request.args.get("criancas", ""),
            "bebes": request.args.get("bebes", ""),
            "query": query,
            "lang": lang,
        },
    }


def _parse_page_arg():
    try:
        return max(1, int(str(request.args.get("page") or "1").strip()))
    except Exception:
        return 1


def _detail_url(al_id: str, params: dict):
    query = {}
    for key in ("checkin", "checkout", "adultos", "criancas", "bebes", "hospedes"):
        value = (params.get("raw") or {}).get(key)
        if value:
            query[key] = value
    lang = (params.get("raw") or {}).get("lang")
    if lang:
        query["lang"] = lang
    return url_for("booking_portal.detail", al_id=al_id, **query)


def _pagination_url(page_number: int, lang: str):
    args = {}
    for key in ("checkin", "checkout", "adultos", "criancas", "bebes", "hospedes", "q"):
        value = request.args.get(key)
        if value:
            args[key] = value
    args["lang"] = lang
    args["page"] = max(1, int(page_number or 1))
    return url_for("booking_portal.index", **args)


def _pagination_context(pagination: dict, lang: str) -> dict:
    page = int(pagination.get("page") or 1)
    pages = int(pagination.get("pages") or 1)
    start_page = max(1, page - 2)
    end_page = min(pages, page + 2)
    if end_page - start_page < 4:
        start_page = max(1, min(start_page, end_page - 4))
        end_page = min(pages, max(end_page, start_page + 4))
    return {
        **pagination,
        "prev_url": _pagination_url(page - 1, lang) if page > 1 else "",
        "next_url": _pagination_url(page + 1, lang) if page < pages else "",
        "page_links": [
            {
                "page": page_number,
                "url": _pagination_url(page_number, lang),
                "active": page_number == page,
            }
            for page_number in range(start_page, end_page + 1)
        ],
    }


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
        ]
        hospedes_extra = int(translated.get("hospedes_extra") or 0)
        if hospedes_extra > 0:
            translated["linhas"].append({
                "label": (
                    f"{t['extra_guests_line']} ({hospedes_extra} x {noites} "
                    f"{t['night'] if noites == 1 else t['nights']})"
                ),
                "value": translated.get("hospedes_extra_total_label", ""),
            })
        translated["linhas"].extend([
            {"label": t["cleaning_fee"], "value": translated.get("limpeza_label", "")},
            {
                "label": (
                    f"{t['tourist_tax']} ({hospedes} "
                    f"{t['guest'] if hospedes == 1 else t['guests']} x {dias_taxa} "
                    f"{t['day'] if dias_taxa == 1 else t['days']})"
                ),
                "value": translated.get("taxa_turistica_label", ""),
            },
        ])
    else:
        translated["label"] = t["price_on_request"] if translated.get("label") == "Preco sob consulta" else translated.get("label")
    return translated


def _guest_constraints(alojamento: dict, params: dict, t: dict) -> dict:
    adultos = int(params.get("adultos") or 0)
    criancas = int(params.get("criancas") or 0)
    bebes = int(params.get("bebes") or 0)
    max_adultos = int(alojamento.get("lot_adultos") or 0)
    max_criancas = int(alojamento.get("lot_criancas") or 0)
    max_total = max_adultos + max_criancas if (max_adultos or max_criancas) else int(alojamento.get("capacidade") or 0)
    errors = []
    notes = []

    if adultos and max_adultos and adultos > max_adultos:
        errors.append(t["adults_capacity_error"].format(max=max_adultos))
    if (adultos or criancas) and max_total and (adultos + criancas) > max_total:
        errors.append(t["total_capacity_error"].format(max=max_total))
    if bebes:
        if bebes > 2:
            errors.append(t["babies_capacity_error"])
        elif alojamento.get("berco"):
            if bebes > 1:
                notes.append(t["crib_one_only"])
        else:
            notes.append(t["crib_unavailable"])

    return {"errors": errors, "notes": notes}


@bp.route("/portal-reservas")
@bp.route("/reservas")
def index():
    lang = _resolve_lang()
    params = _search_params(lang)
    page = _parse_page_arg()
    query_allowed = not params["errors"]
    pagination = get_alojamentos_disponiveis_page(
        checkin=params["checkin"] if query_allowed else None,
        checkout=params["checkout"] if query_allowed else None,
        hospedes=params["hospedes"] if query_allowed else None,
        adultos=params["adultos"] if query_allowed else None,
        criancas=params["criancas"] if query_allowed else None,
        bebes=params["bebes"] if query_allowed else None,
        query=params["query"] if query_allowed else None,
        page=page,
        per_page=BOOKING_PAGE_SIZE,
        lang=lang,
    )
    alojamentos = pagination["items"]
    for alojamento in alojamentos:
        alojamento["detail_url"] = _detail_url(alojamento["id"], params)

    return _render_booking_template(
        "booking_portal/index.html",
        lang,
        alojamentos=alojamentos,
        pagination=_pagination_context(pagination, lang),
        search=params,
        page_title=_t(lang)["page_reservations"],
    )


@bp.route("/portal-reservas/alojamento/<al_id>")
@bp.route("/reservas/<al_id>")
def detail(al_id):
    lang = _resolve_lang()
    params = _search_params(lang)
    t = _t(lang)
    alojamento = get_alojamento(al_id, lang=lang)
    if not alojamento:
        abort(404)

    guest_constraints = _guest_constraints(alojamento, params, t)
    disponibilidade = None
    if guest_constraints["errors"]:
        preco = _translate_price(calcular_preco(al_id, None, None, None), t)
    else:
        preco = _translate_price(calcular_preco(al_id, params["checkin"], params["checkout"], params["hospedes"]), t)
    if params["checkin"] and params["checkout"] and not params["errors"] and not guest_constraints["errors"]:
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
        guest_errors=guest_constraints["errors"],
        guest_notes=guest_constraints["notes"],
        disponibilidade=disponibilidade,
        preco=preco,
        calendario=calendario,
        page_title=alojamento["nome"],
    )


@bp.route("/portal-reservas/alojamento/<al_id>/ocupacao")
@bp.route("/reservas/<al_id>/ocupacao")
def occupied_nights(al_id):
    start, start_error = _parse_date_arg("start")
    if start_error:
        return jsonify({"error": _t(_resolve_lang()).get(start_error, start_error)}), 400

    try:
        months = max(1, min(int(str(request.args.get("months") or "2").strip()), 12))
    except Exception:
        months = 2

    return jsonify({
        "occupied": get_noites_ocupadas(al_id, start=start or date.today(), months=months),
    })
