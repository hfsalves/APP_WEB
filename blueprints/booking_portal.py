from __future__ import annotations

import html
import json
import os
import time
from datetime import date, timedelta
from urllib.parse import urlsplit
from xml.etree.ElementTree import Element, SubElement, tostring

from flask import Blueprint, abort, current_app, g, jsonify, make_response, redirect, render_template, request, session, url_for
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from models import db
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from services.booking_portal_service import (
    alojamento_datas_permitidas,
    alojamento_disponivel,
    autenticar_portal_user,
    build_airbnb_search_url,
    calcular_preco,
    confirmar_email_portal,
    criar_pedido_reserva,
    criar_checkout_teste_portal,
    criar_password_reset_portal,
    get_alojamento,
    get_public_alojamento_ids,
    get_alojamentos_disponiveis_page,
    get_calendario_ocupacao,
    get_portal_user,
    get_portal_user_bookings,
    get_unverified_portal_user_by_email,
    criar_verificacao_email_portal,
    portal_user_exists,
    processar_webhook_stripe_portal,
    redefinir_password_portal,
    sincronizar_checkout_teste_portal,
    verificar_assinatura_webhook_stripe_portal,
    PortalPaymentError,
)
from services.email_service import EmailServiceError, queue_email, send_email_now
from services.booking_portal_legal import (
    COMPLAINTS_LABELS, LEGAL_ENDPOINTS, LEGAL_UPDATED, LEGAL_VERSION, LICENSE_LABELS,
    format_legal_content, get_legal_company, get_legal_content,
)
from services.booking_portal_cookies import (
    apply_language_cookie, cookie_ui, is_same_origin_request,
    read_cookie_consent, save_cookie_consent,
)
from services.booking_portal_seo import (
    PUBLIC_ENDPOINTS, build_booking_seo, is_public_origin, public_url,
)
from services.booking_portal_map import get_map_catalog
from services.booking_portal_map_copy import get_map_copy
from services.booking_portal_whatsapp import build_whatsapp_context
from services.booking_portal_currency import (
    SUPPORTED_CURRENCIES, convert_eur, convert_stay_breakdown, detect_currency,
    format_money, load_currency_snapshot, normalize_currency,
    schedule_fx_refresh, validate_currency_snapshot,
)
from services.booking_portal_analytics import (
    associate_booking, browser_config as analytics_browser_config,
    clear_identity_cookies, collect_event, record_response as record_analytics_response,
    request_traits,
)


bp = Blueprint("booking_portal", __name__)
PORTAL_CURRENCY_SESSION_KEY = "portobreak_currency"


@bp.before_request
def _prepare_portal_currency():
    schedule_fx_refresh(current_app._get_current_object())


def _currency_context() -> dict:
    existing = getattr(g, "portobreak_currency", None)
    if existing:
        return existing
    stored = validate_currency_snapshot(session.get(PORTAL_CURRENCY_SESSION_KEY))
    if stored:
        g.portobreak_currency = stored
        return stored
    country = request_traits().get("country")
    snapshot = load_currency_snapshot(detect_currency(country))
    session[PORTAL_CURRENCY_SESSION_KEY] = snapshot
    session.modified = True
    g.portobreak_currency = snapshot
    return snapshot


def _present_price(preco: dict | None, t: dict, currency: dict) -> dict | None:
    if not preco:
        return preco
    presented = dict(preco)
    if not presented.get("valor"):
        return _translate_price(presented, t)
    if any(presented.get(key) is None for key in (
        "preco_noites", "preco_noites_airbnb", "hospedes_extra_total",
        "limpeza", "taxa_turistica",
    )):
        # Compatibility for legacy/read-only view models. Current production
        # pricing always supplies numeric EUR components before presentation.
        return _translate_price(presented, t)
    converted = convert_stay_breakdown(
        direct_nights=presented.get("preco_noites"),
        airbnb_nights=presented.get("preco_noites_airbnb"),
        extra=presented.get("hospedes_extra_total"),
        cleaning=presented.get("limpeza"),
        tourist_tax=presented.get("taxa_turistica"),
        snapshot=currency,
    )
    code = currency["code"]
    presented.update({
        "currency": code,
        "valor_eur": presented.get("valor"),
        "valor": converted["direct_total"],
        "label": format_money(converted["direct_total"], code),
        "preco_noites": converted["direct_nights"],
        "preco_noites_label": format_money(converted["direct_nights"], code),
        "preco_noites_airbnb": converted["airbnb_nights"],
        "preco_noites_airbnb_label": format_money(converted["airbnb_nights"], code),
        "preco_total_airbnb": converted["airbnb_total"],
        "preco_total_airbnb_label": format_money(converted["airbnb_total"], code),
        "preco_total_portobreak": converted["direct_total"],
        "preco_total_portobreak_label": format_money(converted["direct_total"], code),
        "poupanca_noites": converted["saving"],
        "poupanca_noites_label": format_money(converted["saving"], code),
        "hospedes_extra_total": converted["extra"],
        "hospedes_extra_total_label": format_money(converted["extra"], code),
        "limpeza": converted["cleaning"],
        "limpeza_label": format_money(converted["cleaning"], code),
        "taxa_turistica": converted["tourist_tax"],
        "taxa_turistica_label": format_money(converted["tourist_tax"], code),
    })
    nightly = []
    for item in presented.get("precos_noite") or []:
        converted_item = dict(item)
        converted_item["valor"] = convert_eur(item.get("valor"), currency, whole=True)
        converted_item["label"] = format_money(converted_item["valor"], code, whole=True)
        converted_item["valor_airbnb"] = convert_eur(item.get("valor_airbnb"), currency, whole=True)
        converted_item["label_airbnb"] = format_money(converted_item["valor_airbnb"], code, whole=True)
        nightly.append(converted_item)
    presented["precos_noite"] = nightly
    return _translate_price(presented, t)


def _present_alojamento(alojamento: dict, currency: dict) -> dict:
    item = dict(alojamento or {})
    code = currency["code"]
    from_value = item.get("preco_desde_valor")
    original_from_label = item.get("preco_desde") or ""
    item["preco_desde"] = (
        format_money(convert_eur(from_value, currency, whole=True), code, whole=True)
        if from_value and from_value > 0 else original_from_label
    )
    stay = item.get("preco_estadia")
    if stay and all(stay.get(key) is not None for key in (
        "preco_noites", "preco_noites_airbnb", "hospedes_extra_total",
        "limpeza", "taxa_turistica",
    )):
        converted = convert_stay_breakdown(
            direct_nights=stay.get("preco_noites"), airbnb_nights=stay.get("preco_noites_airbnb"),
            extra=stay.get("hospedes_extra_total"), cleaning=stay.get("limpeza"),
            tourist_tax=stay.get("taxa_turistica"), snapshot=currency,
        )
        item["preco_estadia"] = {
            **stay,
            "currency": code,
            "airbnb_total": converted["airbnb_total"],
            "airbnb_total_label": format_money(converted["airbnb_total"], code),
            "portobreak_total": converted["direct_total"],
            "portobreak_total_label": format_money(converted["direct_total"], code),
            "saving": converted["saving"],
            "saving_label": format_money(converted["saving"], code),
        }
    return item


@bp.after_request
def _measure_portal_response(response):
    return record_analytics_response(response)


@bp.post("/reservas/analitica/eventos")
def analytics_events():
    return collect_event()


@bp.after_request
def _protect_nonpublic_pages_from_indexing(response):
    # Includes redirects, JSON APIs and signed guest pages rendered elsewhere.
    if request.endpoint not in PUBLIC_ENDPOINTS or response.status_code >= 400:
        response.headers["X-Robots-Tag"] = "noindex, nofollow, noarchive, nosnippet"
    return response


@bp.route("/robots.txt")
def robots():
    if is_public_origin():
        body = f"User-agent: *\nDisallow:\n\nSitemap: {public_url('booking_portal.sitemap')}\n"
    else:
        body = "User-agent: *\nDisallow: /\n"
    response = make_response(body)
    response.mimetype = "text/plain"
    # The content depends on the effective host at the reverse proxy.
    response.headers["Cache-Control"] = "no-store"
    return response


@bp.route("/sitemap.xml")
def sitemap():
    try:
        listing_ids = get_public_alojamento_ids()
    except SQLAlchemyError:
        current_app.logger.exception("Não foi possível gerar o sitemap PortoBreak")
        response = make_response("Sitemap temporarily unavailable", 503)
        response.headers["Retry-After"] = "300"
        response.headers["Cache-Control"] = "no-store"
        return response

    root = Element("urlset", xmlns="http://www.sitemaps.org/schemas/sitemap/0.9")
    endpoints = [
        (endpoint, {}) for endpoint in (
            "booking_portal.index", "booking_portal.cancellation_policy",
            "booking_portal.terms", "booking_portal.privacy",
            "booking_portal.cookies", "booking_portal.legal",
        )
    ]
    endpoints.extend(
        ("booking_portal.detail", {"al_id": al_id})
        for al_id in dict.fromkeys(listing_ids) if al_id
    )
    if len(endpoints) * len(SUPPORTED_LANGS) > 50000:
        # Never publish a silently truncated or invalid discovery document.
        abort(503)
    for endpoint, values in endpoints:
        for lang in SUPPORTED_LANGS:
            node = SubElement(root, "url")
            SubElement(node, "loc").text = public_url(endpoint, lang=lang, **values)
    response = make_response(tostring(root, encoding="utf-8", xml_declaration=True))
    response.mimetype = "application/xml"
    response.headers["Cache-Control"] = "public, max-age=300"
    return response


SUPPORTED_LANGS = ("pt", "en", "es", "fr")
LANG_COOKIE = "portobreak_lang"
BOOKING_PAGE_SIZE = 18
PORTAL_USER_SESSION_KEY = "PORTOBREAK_USER_ID"
PORTAL_RESEND_COOLDOWN_SESSION_KEY = "PORTOBREAK_VERIFICATION_RESEND_AT"
PORTAL_RESEND_COOLDOWN_SECONDS = 60
PORTAL_PASSWORD_RESET_COOLDOWN_SESSION_KEY = "PORTOBREAK_PASSWORD_RESET_AT"
PORTAL_PASSWORD_RESET_COOLDOWN_SECONDS = 60
PORTAL_PAYMENT_ACCESS_SESSION_KEY = "PORTOBREAK_PAYMENT_ACCESS"
PORTAL_GUEST_PORTAL_TOKEN_SALT = "portobreak-guest-portal-v1"
PORTAL_GUEST_PORTAL_TOKEN_MAX_AGE = 60 * 60 * 24 * 365
PORTAL_INTERNAL_BOOKING_RECIPIENTS = (
    "pedro@guestspa.pt", "hugo@guestspa.pt", "susana@guestspa.pt", "dyhia@guestspa.pt",
    "helpdesk@guestspa.pt", "hfsalves@hotmail.com", "pnalves.pa@gmail.com", "guestspa.pt@gmail.com",
)

CANCELLATION_POLICY_COPY = {
    "pt": {
        "page_title": "Política de cancelamento",
        "page_lead": "As condições de reembolso dependem da data em que o cancelamento é pedido.",
        "free_title": "Cancelamento gratuito",
        "free_rule": "Reembolso total quando o cancelamento é feito antes do período de 50%.",
        "partial_title": "Reembolso de 50%",
        "partial_rule": "Desde 10 dias antes do check-in até à véspera da chegada.",
        "none_title": "Sem reembolso",
        "none_rule": "No dia do check-in e depois dessa data.",
        "free_message": "Cancelamento gratuito até {date}.",
        "partial_message": "A partir de {date} às 00:00, o reembolso é de 50%.",
        "none_message": "A partir de {date} às 00:00, não existe direito a reembolso.",
        "example_title": "Condições para estas datas",
        "timezone_note": "Os prazos são calculados pela data e hora de Portugal continental.",
        "learn_more": "Consultar política de cancelamento",
        "policy_link": "Políticas de cancelamento",
        "back": "Voltar às reservas",
        "back_to_reservation": "Voltar à Reserva",
    },
    "en": {
        "page_title": "Cancellation policy",
        "page_lead": "Refund conditions depend on the date when cancellation is requested.",
        "free_title": "Free cancellation",
        "free_rule": "Full refund when cancellation is made before the 50% refund period.",
        "partial_title": "50% refund",
        "partial_rule": "From 10 days before check-in until the day before arrival.",
        "none_title": "No refund",
        "none_rule": "On the check-in date and afterwards.",
        "free_message": "Free cancellation until {date}.",
        "partial_message": "From {date} at 00:00, the refund is 50%.",
        "none_message": "From {date} at 00:00, no refund is due.",
        "example_title": "Terms for these dates",
        "timezone_note": "Deadlines use mainland Portugal's date and time.",
        "learn_more": "View cancellation policy",
        "policy_link": "Cancellation policy",
        "back": "Back to bookings",
        "back_to_reservation": "Back to booking",
    },
    "es": {
        "page_title": "Política de cancelación",
        "page_lead": "Las condiciones de reembolso dependen de la fecha en que se solicita la cancelación.",
        "free_title": "Cancelación gratuita",
        "free_rule": "Reembolso total cuando la cancelación se realiza antes del periodo de reembolso del 50%.",
        "partial_title": "Reembolso del 50%",
        "partial_rule": "Desde 10 días antes del check-in hasta la víspera de la llegada.",
        "none_title": "Sin reembolso",
        "none_rule": "El día del check-in y después.",
        "free_message": "Cancelación gratuita hasta el {date}.",
        "partial_message": "A partir del {date} a las 00:00, el reembolso es del 50%.",
        "none_message": "A partir del {date} a las 00:00, no hay derecho a reembolso.",
        "example_title": "Condiciones para estas fechas",
        "timezone_note": "Los plazos se calculan según la fecha y hora de Portugal continental.",
        "learn_more": "Consultar política de cancelación",
        "policy_link": "Política de cancelación",
        "back": "Volver a las reservas",
        "back_to_reservation": "Volver a la reserva",
    },
    "fr": {
        "page_title": "Politique d'annulation",
        "page_lead": "Les conditions de remboursement dépendent de la date de la demande d'annulation.",
        "free_title": "Annulation gratuite",
        "free_rule": "Remboursement intégral lorsque l'annulation intervient avant la période de remboursement à 50 %.",
        "partial_title": "Remboursement de 50 %",
        "partial_rule": "À partir de 10 jours avant l'arrivée et jusqu'à la veille.",
        "none_title": "Aucun remboursement",
        "none_rule": "Le jour de l'arrivée et après cette date.",
        "free_message": "Annulation gratuite jusqu'au {date}.",
        "partial_message": "À partir du {date} à 00:00, le remboursement est de 50 %.",
        "none_message": "À partir du {date} à 00:00, aucun remboursement n'est dû.",
        "example_title": "Conditions pour ces dates",
        "timezone_note": "Les délais sont calculés selon la date et l'heure du Portugal continental.",
        "learn_more": "Consulter la politique d'annulation",
        "policy_link": "Politique d'annulation",
        "back": "Retour aux réservations",
        "back_to_reservation": "Retour à la réservation",
    },
}

CANCELLATION_MONTHS = {
    "pt": ("janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"),
    "en": ("January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"),
    "es": ("enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"),
    "fr": ("janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre"),
}

BOOKING_FOOTER_COPY = {
    "pt": {
        "tagline": "Alojamentos selecionados para descobrir o Porto com conforto.",
        "navigation": "Navegação",
        "reservations": "Reservas",
        "account": "As minhas reservas",
        "cancellation": "Políticas de cancelamento",
        "institutional": "Informação institucional",
        "address": "Rua Régulo Magauanha, 102, 4000-413 Porto, Portugal",
        "tax_id": "NIF 518401057",
        "privacy_note": "Os dados são tratados exclusivamente para gerir reservas, em conformidade com o RGPD.",
        "rights": "Todos os direitos reservados.",
    },
    "en": {
        "tagline": "Selected stays for discovering Porto in comfort.",
        "navigation": "Navigation",
        "reservations": "Bookings",
        "account": "My bookings",
        "cancellation": "Cancellation policy",
        "institutional": "Company information",
        "address": "Rua Régulo Magauanha, 102, 4000-413 Porto, Portugal",
        "tax_id": "Tax ID 518401057",
        "privacy_note": "Data is processed solely to manage bookings, in accordance with the GDPR.",
        "rights": "All rights reserved.",
    },
    "es": {
        "tagline": "Alojamientos seleccionados para descubrir Oporto con comodidad.",
        "navigation": "Navegación",
        "reservations": "Reservas",
        "account": "Mis reservas",
        "cancellation": "Política de cancelación",
        "institutional": "Información institucional",
        "address": "Rua Régulo Magauanha, 102, 4000-413 Porto, Portugal",
        "tax_id": "NIF 518401057",
        "privacy_note": "Los datos se tratan exclusivamente para gestionar reservas, de conformidad con el RGPD.",
        "rights": "Todos los derechos reservados.",
    },
    "fr": {
        "tagline": "Des hébergements sélectionnés pour découvrir Porto confortablement.",
        "navigation": "Navigation",
        "reservations": "Réservations",
        "account": "Mes réservations",
        "cancellation": "Politique d'annulation",
        "institutional": "Informations légales",
        "address": "Rua Régulo Magauanha, 102, 4000-413 Porto, Portugal",
        "tax_id": "NIF 518401057",
        "privacy_note": "Les données sont traitées uniquement pour gérer les réservations, conformément au RGPD.",
        "rights": "Tous droits réservés.",
    },
}

TRANSLATIONS = {
    "pt": {
        "page_reservations": "Reservas",
        "local_stay": "Alojamentos no Porto",
        "hero_title": "Fica no Porto. Reserva diretamente.",
        "hero_lead": "Alojamentos selecionados, tarifas diretas e apoio local.",
        "hero_trust_label": "Vantagens da reserva direta",
        "hero_direct_rates": "Tarifas diretas",
        "hero_secure_payment": "Pagamento seguro",
        "hero_local_support": "Apoio local no Porto",
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
        "airbnb_price": "Preço Airbnb",
        "direct_booking": "Reserva direta",
        "you_save": "Poupa {value}",
        "saving_info_open": "Saber porque poupa na reserva direta",
        "saving_info_title": "Porque poupa na reserva direta",
        "saving_info_body_1": "O PortoBreak é a equipa local responsável pelos alojamentos apresentados neste portal. Somos proprietários ou coanfitriões destes alojamentos no Airbnb e na Booking.com.",
        "saving_info_body_2": "Ao reservar diretamente connosco, evitamos parte dos custos e comissões das plataformas e conseguimos refletir essa diferença no preço da sua estadia. Continua a beneficiar de pagamento seguro e do mesmo apoio local, antes, durante e depois da estadia.",
        "saving_info_body_3": "Muda apenas o canal da reserva: o alojamento e a equipa que cuida de si são os mesmos.",
        "saving_info_close": "Fechar",
        "whatsapp_help": "Precisa de ajuda?",
        "whatsapp_open": "Contactar pelo WhatsApp",
        "whatsapp_offline_title": "O nosso apoio está offline neste momento",
        "whatsapp_offline_text": "A nossa equipa está disponível diariamente das 09:30 às 23:00 (hora de Portugal). Pode enviar-nos a sua mensagem agora e responderemos assim que estivermos disponíveis.",
        "whatsapp_continue": "Enviar mensagem na mesma",
        "whatsapp_close": "Fechar",
        "whatsapp_guest": "hóspede",
        "whatsapp_guests": "hóspedes",
        "whatsapp_property": "Olá! Estou interessado no {property}.",
        "whatsapp_property_dates": "Olá! Estou interessado no {property}, de {checkin} a {checkout}.",
        "whatsapp_property_guests": "Olá! Estou interessado no {property}, para {guests} {guest_label}.",
        "whatsapp_property_dates_guests": "Olá! Estou interessado no {property}, de {checkin} a {checkout}, para {guests} {guest_label}.",
        "whatsapp_generic": "Olá! Preciso de ajuda para encontrar um alojamento no Porto.",
        "whatsapp_generic_dates": "Olá! Procuro alojamento no Porto de {checkin} a {checkout}.",
        "whatsapp_generic_guests": "Olá! Procuro alojamento no Porto para {guests} {guest_label}.",
        "whatsapp_generic_dates_guests": "Olá! Procuro alojamento no Porto de {checkin} a {checkout} para {guests} {guest_label}.",
        "currency": "Moeda",
        "currency_eur": "Euro",
        "currency_gbp": "Libra esterlina",
        "currency_usd": "Dólar americano",
        "total": "Total",
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
        "update_selection_hint": "Atualize para confirmar a disponibilidade e o preço das novas datas e hóspedes.",
        "request_soon": "Pedido de reserva em breve",
        "book_now": "Reservar",
        "booking_request": "Pedido de reserva",
        "payment_details": "Pagamento",
        "booking_request_sent": "Pedido de reserva recebido",
        "booking_request_sent_text": "Recebemos o seu pedido. A nossa equipa vai confirmar a disponibilidade final e responder por email.",
        "account_confirmation_sent": "Enviamos um link para validar o email e ativar a sua conta.",
        "email_verification_title": "Validacao de email",
        "email_verified": "Email validado",
        "email_verified_text": "A sua conta Porto Break ficou pronta a utilizar.",
        "email_already_verified": "Este email ja se encontra validado.",
        "email_verification_expired": "Este link de validacao expirou.",
        "email_verification_invalid": "Este link de validacao nao e valido.",
        "back_to_reservations": "Ver alojamentos",
        "customer_details": "Dados do titular",
        "reserve_as_guest": "Reservar sem criar conta",
        "create_user_account": "Criar conta de utilizador",
        "full_name": "Nome completo",
        "email": "Email",
        "phone": "Telefone",
        "address": "Morada",
        "country": "Pais",
        "tax_id": "NIF",
        "password": "Password",
        "confirm_password": "Confirmar password",
        "notes": "Observacoes",
        "submit_booking_request": "Avancar para pagamento",
        "start_test_payment": "Avancar para pagamento",
        "test_payment_notice": "O pagamento sera processado de forma segura pela Stripe.",
        "test_payment_title": "Pagamento",
        "test_payment_completed": "Pagamento concluido",
        "test_payment_completed_text": "O pagamento foi recebido e a sua reserva esta confirmada. Enviamos tambem os detalhes por email.",
        "test_payment_cancelled": "Pagamento cancelado",
        "test_payment_cancelled_text": "Pode voltar ao alojamento e retomar o processo quando quiser.",
        "test_payment_unavailable": "Nao foi possivel preparar o pagamento.",
        "required_field": "Preencha os campos obrigatorios.",
        "invalid_email": "Indique um email valido.",
        "password_mismatch": "As passwords nao coincidem.",
        "password_short": "A password deve ter pelo menos 8 caracteres.",
        "email_already_registered": "Ja existe uma conta com este email.",
        "booking_unavailable": "Nao foi possivel criar o pedido para estas datas.",
        "booking_as_account": "A reservar como {name}",
        "account_details_prefilled": "Os dados da sua conta foram preenchidos para este pedido.",
        "already_have_account": "Ja tem conta?",
        "sign_in_to_continue": "Entrar",
        "reservation_summary": "Resumo da reserva",
        "guest_portal": "Portal do hospede",
        "open_guest_portal": "Abrir portal do hospede",
        "booking_reference": "Referencia da reserva",
        "total_paid": "Total pago",
        "payment_confirmed": "Pagamento confirmado",
        "login": "Entrar",
        "logout": "Terminar sessao",
        "account": "Conta",
        "my_bookings": "As minhas reservas",
        "my_bookings_lead": "Consulte as suas estadias confirmadas e os respetivos detalhes.",
        "upcoming_stays": "Proximas estadias",
        "past_stays": "Estadias anteriores",
        "no_bookings_title": "Ainda nao tem reservas confirmadas.",
        "no_bookings_text": "Quando uma reserva for paga e confirmada, aparecera aqui.",
        "explore_stays": "Explorar alojamentos",
        "booking_confirmed": "Reserva confirmada",
        "view_booking": "Ver reserva",
        "login_title": "Entre na sua conta",
        "login_lead": "Use o email e a password definidos ao criar a conta Porto Break.",
        "login_submit": "Entrar",
        "invalid_credentials": "Email ou password incorretos.",
        "email_unverified": "Valide o email da sua conta antes de entrar.",
        "resend_validation_email": "Reenviar email de validacao",
        "resend_validation_sent": "Se a conta ainda estiver por validar, enviamos um novo link para o email indicado.",
        "resend_validation_wait": "Aguarde um minuto antes de pedir outro email de validacao.",
        "resend_validation_failed": "Nao foi possivel reenviar o email de validacao. Tente novamente.",
        "forgot_password": "Esqueceu-se da password?",
        "password_recovery": "Recuperar password",
        "password_recovery_lead": "Indique o email da sua conta. Se estiver registado, enviamos um link para definir uma nova password.",
        "send_password_reset": "Enviar link de recuperacao",
        "password_reset_sent": "Se existir uma conta validada com este email, enviamos um link de recuperacao.",
        "new_password": "Nova password",
        "set_new_password": "Definir nova password",
        "password_reset_title": "Definir nova password",
        "password_reset_lead": "Escolha uma password nova para a sua conta Porto Break.",
        "password_reset_success": "Password atualizada",
        "password_reset_success_text": "A sua password foi alterada. Ja pode entrar na sua conta.",
        "password_reset_invalid": "Este link de recuperacao nao e valido ou ja foi utilizado.",
        "password_reset_expired": "Este link de recuperacao expirou. Peca um novo link.",
        "calendar_pick_free": "Escolha uma noite livre para iniciar a estadia.",
        "calendar_pick_checkout": "Agora escolha a data de saida.",
        "calendar_range_occupied": "O intervalo escolhido cruza noites ocupadas.",
        "calendar_blocked_checkin": "Nao e possivel fazer check-in nesta data.",
        "calendar_blocked_checkout": "Nao e possivel fazer check-out nesta data.",
        "calendar_min_nights": "Este alojamento exige no minimo {min} noite(s).",
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
        "reviews_title": "Avaliações",
        "reviews_eyebrow": "Experiências dos hóspedes",
        "reviews_lead": "Opiniões partilhadas por quem ficou neste alojamento.",
        "review_singular": "avaliação",
        "review_plural": "avaliações",
        "view_reviews": "Ver avaliações",
        "review_read_more": "Ver mais",
        "review_read_less": "Ver menos",
        "amenities_eyebrow": "Comodidades",
        "amenities_title": "O que este alojamento oferece",
    },
    "en": {
        "page_reservations": "Bookings",
        "local_stay": "Stays in Porto",
        "hero_title": "Stay in Porto. Book direct.",
        "hero_lead": "Handpicked stays, direct rates and local support.",
        "hero_trust_label": "Direct booking benefits",
        "hero_direct_rates": "Direct rates",
        "hero_secure_payment": "Secure payment",
        "hero_local_support": "Local support in Porto",
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
        "airbnb_price": "Airbnb price",
        "direct_booking": "Direct booking",
        "you_save": "You save {value}",
        "saving_info_open": "Learn why you save by booking direct",
        "saving_info_title": "Why you save by booking direct",
        "saving_info_body_1": "PortoBreak is the local team responsible for every stay shown on this portal. We are the owners or co-hosts of these properties on Airbnb and Booking.com.",
        "saving_info_body_2": "When you book directly with us, we avoid part of the platform costs and commissions and can pass that difference on in the price of your stay. You still benefit from secure payment and the same local support before, during and after your stay.",
        "saving_info_body_3": "Only the booking channel changes: the accommodation and the team looking after you remain the same.",
        "saving_info_close": "Close",
        "whatsapp_help": "Need help?",
        "whatsapp_open": "Contact us on WhatsApp",
        "whatsapp_offline_title": "Our support team is currently offline",
        "whatsapp_offline_text": "Our team is available every day from 09:30 to 23:00 (Portugal time). You can send us your message now and we will reply as soon as we are available.",
        "whatsapp_continue": "Send message anyway",
        "whatsapp_close": "Close",
        "whatsapp_guest": "guest",
        "whatsapp_guests": "guests",
        "whatsapp_property": "Hi! I'm interested in {property}.",
        "whatsapp_property_dates": "Hi! I'm interested in {property}, from {checkin} to {checkout}.",
        "whatsapp_property_guests": "Hi! I'm interested in {property}, for {guests} {guest_label}.",
        "whatsapp_property_dates_guests": "Hi! I'm interested in {property}, from {checkin} to {checkout}, for {guests} {guest_label}.",
        "whatsapp_generic": "Hi! I need some help finding a place to stay in Porto.",
        "whatsapp_generic_dates": "Hi! I'm looking for a place to stay in Porto from {checkin} to {checkout}.",
        "whatsapp_generic_guests": "Hi! I'm looking for a place to stay in Porto for {guests} {guest_label}.",
        "whatsapp_generic_dates_guests": "Hi! I'm looking for a place to stay in Porto from {checkin} to {checkout} for {guests} {guest_label}.",
        "currency": "Currency",
        "currency_eur": "Euro",
        "currency_gbp": "Pound sterling",
        "currency_usd": "US dollar",
        "total": "Total",
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
        "update_selection_hint": "Update to confirm availability and price for the new dates and guests.",
        "request_soon": "Booking request coming soon",
        "book_now": "Book",
        "booking_request": "Booking request",
        "payment_details": "Payment",
        "booking_request_sent": "Booking request received",
        "booking_request_sent_text": "We received your request. Our team will confirm final availability and reply by email.",
        "account_confirmation_sent": "We sent a link to validate your email and activate your account.",
        "email_verification_title": "Email verification",
        "email_verified": "Email verified",
        "email_verified_text": "Your Porto Break account is ready to use.",
        "email_already_verified": "This email has already been verified.",
        "email_verification_expired": "This verification link has expired.",
        "email_verification_invalid": "This verification link is not valid.",
        "back_to_reservations": "View stays",
        "customer_details": "Guest details",
        "reserve_as_guest": "Book without creating an account",
        "create_user_account": "Create a user account",
        "full_name": "Full name",
        "email": "Email",
        "phone": "Phone",
        "address": "Address",
        "country": "Country",
        "tax_id": "Tax ID",
        "password": "Password",
        "confirm_password": "Confirm password",
        "notes": "Notes",
        "submit_booking_request": "Continue to payment",
        "start_test_payment": "Continue to payment",
        "test_payment_notice": "Your payment will be processed securely by Stripe.",
        "test_payment_title": "Payment",
        "test_payment_completed": "Payment completed",
        "test_payment_completed_text": "Your payment was received and your booking is confirmed. We also sent the details by email.",
        "test_payment_cancelled": "Payment cancelled",
        "test_payment_cancelled_text": "You can return to the stay and resume the process whenever you like.",
        "test_payment_unavailable": "We could not prepare the payment.",
        "required_field": "Fill in the required fields.",
        "invalid_email": "Enter a valid email.",
        "password_mismatch": "Passwords do not match.",
        "password_short": "Password must be at least 8 characters.",
        "email_already_registered": "An account with this email already exists.",
        "booking_unavailable": "The request could not be created for these dates.",
        "booking_as_account": "Booking as {name}",
        "account_details_prefilled": "Your account details were filled in for this request.",
        "already_have_account": "Already have an account?",
        "sign_in_to_continue": "Sign in",
        "reservation_summary": "Booking summary",
        "guest_portal": "Guest portal",
        "open_guest_portal": "Open guest portal",
        "booking_reference": "Booking reference",
        "total_paid": "Total paid",
        "payment_confirmed": "Payment confirmed",
        "login": "Sign in",
        "logout": "Sign out",
        "account": "Account",
        "my_bookings": "My bookings",
        "my_bookings_lead": "View your confirmed stays and their details.",
        "upcoming_stays": "Upcoming stays",
        "past_stays": "Past stays",
        "no_bookings_title": "You do not have any confirmed bookings yet.",
        "no_bookings_text": "A paid and confirmed booking will appear here.",
        "explore_stays": "Explore stays",
        "booking_confirmed": "Booking confirmed",
        "view_booking": "View booking",
        "login_title": "Sign in to your account",
        "login_lead": "Use the email and password set when you created your Porto Break account.",
        "login_submit": "Sign in",
        "invalid_credentials": "Incorrect email or password.",
        "email_unverified": "Verify your account email before signing in.",
        "resend_validation_email": "Resend verification email",
        "resend_validation_sent": "If the account is still unverified, we sent a new link to the provided email.",
        "resend_validation_wait": "Wait one minute before requesting another verification email.",
        "resend_validation_failed": "The verification email could not be resent. Please try again.",
        "forgot_password": "Forgot your password?",
        "password_recovery": "Recover password",
        "password_recovery_lead": "Enter your account email. If it is registered, we will send a link to set a new password.",
        "send_password_reset": "Send recovery link",
        "password_reset_sent": "If there is a verified account with this email, we sent a recovery link.",
        "new_password": "New password",
        "set_new_password": "Set new password",
        "password_reset_title": "Set a new password",
        "password_reset_lead": "Choose a new password for your Porto Break account.",
        "password_reset_success": "Password updated",
        "password_reset_success_text": "Your password was changed. You can now sign in to your account.",
        "password_reset_invalid": "This recovery link is invalid or has already been used.",
        "password_reset_expired": "This recovery link has expired. Request a new link.",
        "calendar_pick_free": "Choose a free night to start the stay.",
        "calendar_pick_checkout": "Now choose the check-out date.",
        "calendar_range_occupied": "The selected range crosses occupied nights.",
        "calendar_blocked_checkin": "Check-in is not possible on this date.",
        "calendar_blocked_checkout": "Check-out is not possible on this date.",
        "calendar_min_nights": "This stay requires at least {min} night(s).",
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
        "reviews_title": "Reviews",
        "reviews_eyebrow": "Guest experiences",
        "reviews_lead": "Feedback shared by guests who stayed here.",
        "review_singular": "review",
        "review_plural": "reviews",
        "view_reviews": "View reviews",
        "review_read_more": "Read more",
        "review_read_less": "Show less",
        "amenities_eyebrow": "Amenities",
        "amenities_title": "What this stay offers",
    },
    "es": {
        "page_reservations": "Reservas",
        "local_stay": "Alojamientos en Oporto",
        "hero_title": "Alójate en Oporto. Reserva directamente.",
        "hero_lead": "Alojamientos seleccionados, tarifas directas y asistencia local.",
        "hero_trust_label": "Ventajas de reservar directamente",
        "hero_direct_rates": "Tarifas directas",
        "hero_secure_payment": "Pago seguro",
        "hero_local_support": "Asistencia local en Oporto",
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
        "airbnb_price": "Precio en Airbnb",
        "direct_booking": "Reserva directa",
        "you_save": "Ahorras {value}",
        "saving_info_open": "Descubre por qué ahorras al reservar directamente",
        "saving_info_title": "Por qué ahorras al reservar directamente",
        "saving_info_body_1": "PortoBreak es el equipo local responsable de todos los alojamientos que aparecen en este portal. Somos propietarios o coanfitriones de estos alojamientos en Airbnb y Booking.com.",
        "saving_info_body_2": "Al reservar directamente con nosotros, evitamos parte de los costes y comisiones de las plataformas y podemos trasladar esa diferencia al precio de tu estancia. Sigues beneficiándote de un pago seguro y del mismo apoyo local antes, durante y después de la estancia.",
        "saving_info_body_3": "Solo cambia el canal de reserva: el alojamiento y el equipo que te atiende siguen siendo los mismos.",
        "saving_info_close": "Cerrar",
        "whatsapp_help": "¿Necesita ayuda?",
        "whatsapp_open": "Contactar por WhatsApp",
        "whatsapp_offline_title": "Nuestro equipo de atención no está disponible en este momento",
        "whatsapp_offline_text": "Nuestro equipo está disponible todos los días de 09:30 a 23:00 (hora de Portugal). Puede enviarnos su mensaje ahora y responderemos en cuanto volvamos a estar disponibles.",
        "whatsapp_continue": "Enviar mensaje de todos modos",
        "whatsapp_close": "Cerrar",
        "whatsapp_guest": "huésped",
        "whatsapp_guests": "huéspedes",
        "whatsapp_property": "¡Hola! Me interesa {property}.",
        "whatsapp_property_dates": "¡Hola! Me interesa {property}, del {checkin} al {checkout}.",
        "whatsapp_property_guests": "¡Hola! Me interesa {property}, para {guests} {guest_label}.",
        "whatsapp_property_dates_guests": "¡Hola! Me interesa {property}, del {checkin} al {checkout}, para {guests} {guest_label}.",
        "whatsapp_generic": "¡Hola! Necesito ayuda para encontrar alojamiento en Oporto.",
        "whatsapp_generic_dates": "¡Hola! Busco alojamiento en Oporto del {checkin} al {checkout}.",
        "whatsapp_generic_guests": "¡Hola! Busco alojamiento en Oporto para {guests} {guest_label}.",
        "whatsapp_generic_dates_guests": "¡Hola! Busco alojamiento en Oporto del {checkin} al {checkout} para {guests} {guest_label}.",
        "currency": "Moneda",
        "currency_eur": "Euro",
        "currency_gbp": "Libra esterlina",
        "currency_usd": "Dólar estadounidense",
        "total": "Total",
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
        "update_selection_hint": "Actualiza para confirmar la disponibilidad y el precio de las nuevas fechas y huéspedes.",
        "request_soon": "Solicitud de reserva proximamente",
        "book_now": "Reservar",
        "booking_request": "Solicitud de reserva",
        "payment_details": "Pago",
        "booking_request_sent": "Solicitud recibida",
        "booking_request_sent_text": "Hemos recibido tu solicitud. Nuestro equipo confirmara la disponibilidad final y respondera por email.",
        "account_confirmation_sent": "Hemos enviado un enlace para validar tu email y activar tu cuenta.",
        "email_verification_title": "Validacion de email",
        "email_verified": "Email validado",
        "email_verified_text": "Tu cuenta de Porto Break esta lista para usar.",
        "email_already_verified": "Este email ya esta validado.",
        "email_verification_expired": "Este enlace de validacion ha caducado.",
        "email_verification_invalid": "Este enlace de validacion no es valido.",
        "back_to_reservations": "Ver alojamientos",
        "customer_details": "Datos del titular",
        "reserve_as_guest": "Reservar sin crear cuenta",
        "create_user_account": "Crear cuenta de usuario",
        "full_name": "Nombre completo",
        "email": "Email",
        "phone": "Telefono",
        "address": "Direccion",
        "country": "Pais",
        "tax_id": "NIF",
        "password": "Password",
        "confirm_password": "Confirmar password",
        "notes": "Observaciones",
        "submit_booking_request": "Continuar al pago",
        "start_test_payment": "Continuar al pago",
        "test_payment_notice": "Stripe procesara tu pago de forma segura.",
        "test_payment_title": "Pago",
        "test_payment_completed": "Pago completado",
        "test_payment_completed_text": "Hemos recibido tu pago y tu reserva esta confirmada. Tambien enviamos los detalles por email.",
        "test_payment_cancelled": "Pago cancelado",
        "test_payment_cancelled_text": "Puedes volver al alojamiento y retomar el proceso cuando quieras.",
        "test_payment_unavailable": "No ha sido posible preparar el pago.",
        "required_field": "Rellena los campos obligatorios.",
        "invalid_email": "Indica un email valido.",
        "password_mismatch": "Las passwords no coinciden.",
        "password_short": "La password debe tener al menos 8 caracteres.",
        "email_already_registered": "Ya existe una cuenta con este email.",
        "booking_unavailable": "No ha sido posible crear la solicitud para estas fechas.",
        "booking_as_account": "Reservando como {name}",
        "account_details_prefilled": "Los datos de tu cuenta se han completado para esta solicitud.",
        "already_have_account": "Ya tienes cuenta?",
        "sign_in_to_continue": "Entrar",
        "reservation_summary": "Resumen de la reserva",
        "guest_portal": "Portal del huesped",
        "open_guest_portal": "Abrir portal del huesped",
        "booking_reference": "Referencia de la reserva",
        "total_paid": "Total pagado",
        "payment_confirmed": "Pago confirmado",
        "login": "Entrar",
        "logout": "Cerrar sesion",
        "account": "Cuenta",
        "my_bookings": "Mis reservas",
        "my_bookings_lead": "Consulta tus estancias confirmadas y sus detalles.",
        "upcoming_stays": "Proximas estancias",
        "past_stays": "Estancias anteriores",
        "no_bookings_title": "Aun no tienes reservas confirmadas.",
        "no_bookings_text": "Las reservas pagadas y confirmadas apareceran aqui.",
        "explore_stays": "Ver alojamientos",
        "booking_confirmed": "Reserva confirmada",
        "view_booking": "Ver reserva",
        "login_title": "Entra en tu cuenta",
        "login_lead": "Usa el email y la password definidos al crear tu cuenta de Porto Break.",
        "login_submit": "Entrar",
        "invalid_credentials": "Email o password incorrectos.",
        "email_unverified": "Valida el email de tu cuenta antes de entrar.",
        "resend_validation_email": "Reenviar email de validacion",
        "resend_validation_sent": "Si la cuenta sigue sin validar, hemos enviado un nuevo enlace al email indicado.",
        "resend_validation_wait": "Espera un minuto antes de solicitar otro email de validacion.",
        "resend_validation_failed": "No ha sido posible reenviar el email de validacion. Intentalo de nuevo.",
        "forgot_password": "Has olvidado tu password?",
        "password_recovery": "Recuperar password",
        "password_recovery_lead": "Indica el email de tu cuenta. Si esta registrado, enviaremos un enlace para definir una nueva password.",
        "send_password_reset": "Enviar enlace de recuperacion",
        "password_reset_sent": "Si existe una cuenta validada con este email, hemos enviado un enlace de recuperacion.",
        "new_password": "Nueva password",
        "set_new_password": "Definir nueva password",
        "password_reset_title": "Definir nueva password",
        "password_reset_lead": "Elige una nueva password para tu cuenta de Porto Break.",
        "password_reset_success": "Password actualizada",
        "password_reset_success_text": "Tu password se ha cambiado. Ya puedes entrar en tu cuenta.",
        "password_reset_invalid": "Este enlace de recuperacion no es valido o ya se ha utilizado.",
        "password_reset_expired": "Este enlace de recuperacion ha caducado. Solicita un nuevo enlace.",
        "calendar_pick_free": "Elige una noche libre para iniciar la estancia.",
        "calendar_pick_checkout": "Ahora elige la fecha de salida.",
        "calendar_range_occupied": "El intervalo elegido cruza noches ocupadas.",
        "calendar_blocked_checkin": "No es posible hacer check-in en esta fecha.",
        "calendar_blocked_checkout": "No es posible hacer check-out en esta fecha.",
        "calendar_min_nights": "Este alojamiento exige un minimo de {min} noche(s).",
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
        "reviews_title": "Reseñas",
        "reviews_eyebrow": "Experiencias de huéspedes",
        "reviews_lead": "Opiniones de huéspedes que se alojaron aquí.",
        "review_singular": "reseña",
        "review_plural": "reseñas",
        "view_reviews": "Ver reseñas",
        "review_read_more": "Ver más",
        "review_read_less": "Ver menos",
        "amenities_eyebrow": "Comodidades",
        "amenities_title": "Qué ofrece este alojamiento",
    },
    "fr": {
        "page_reservations": "Reservations",
        "local_stay": "Hébergements à Porto",
        "hero_title": "Séjournez à Porto. Réservez en direct.",
        "hero_lead": "Hébergements sélectionnés, tarifs directs et assistance locale.",
        "hero_trust_label": "Avantages de la réservation directe",
        "hero_direct_rates": "Tarifs directs",
        "hero_secure_payment": "Paiement sécurisé",
        "hero_local_support": "Assistance locale à Porto",
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
        "airbnb_price": "Prix Airbnb",
        "direct_booking": "Réservation directe",
        "you_save": "Vous économisez {value}",
        "saving_info_open": "Découvrez pourquoi vous économisez en réservant directement",
        "saving_info_title": "Pourquoi vous économisez en réservant directement",
        "saving_info_body_1": "PortoBreak est l’équipe locale responsable de tous les hébergements présentés sur ce portail. Nous sommes propriétaires ou co-hôtes de ces logements sur Airbnb et Booking.com.",
        "saving_info_body_2": "En réservant directement auprès de nous, nous évitons une partie des frais et commissions des plateformes et pouvons répercuter cette différence sur le prix de votre séjour. Vous bénéficiez toujours d’un paiement sécurisé et du même accompagnement local avant, pendant et après votre séjour.",
        "saving_info_body_3": "Seul le canal de réservation change : l’hébergement et l’équipe qui s’occupe de vous restent les mêmes.",
        "saving_info_close": "Fermer",
        "whatsapp_help": "Besoin d’aide ?",
        "whatsapp_open": "Nous contacter sur WhatsApp",
        "whatsapp_offline_title": "Notre assistance est actuellement hors ligne",
        "whatsapp_offline_text": "Notre équipe est disponible tous les jours de 09:30 à 23:00 (heure du Portugal). Vous pouvez nous envoyer votre message maintenant et nous vous répondrons dès que nous serons disponibles.",
        "whatsapp_continue": "Envoyer quand même",
        "whatsapp_close": "Fermer",
        "whatsapp_guest": "voyageur",
        "whatsapp_guests": "voyageurs",
        "whatsapp_property": "Bonjour ! Je suis intéressé(e) par {property}.",
        "whatsapp_property_dates": "Bonjour ! Je suis intéressé(e) par {property}, du {checkin} au {checkout}.",
        "whatsapp_property_guests": "Bonjour ! Je suis intéressé(e) par {property}, pour {guests} {guest_label}.",
        "whatsapp_property_dates_guests": "Bonjour ! Je suis intéressé(e) par {property}, du {checkin} au {checkout}, pour {guests} {guest_label}.",
        "whatsapp_generic": "Bonjour ! J’ai besoin d’aide pour trouver un hébergement à Porto.",
        "whatsapp_generic_dates": "Bonjour ! Je cherche un hébergement à Porto du {checkin} au {checkout}.",
        "whatsapp_generic_guests": "Bonjour ! Je cherche un hébergement à Porto pour {guests} {guest_label}.",
        "whatsapp_generic_dates_guests": "Bonjour ! Je cherche un hébergement à Porto du {checkin} au {checkout} pour {guests} {guest_label}.",
        "currency": "Devise",
        "currency_eur": "Euro",
        "currency_gbp": "Livre sterling",
        "currency_usd": "Dollar américain",
        "total": "Total",
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
        "update_selection_hint": "Mettez à jour pour confirmer la disponibilité et le prix des nouvelles dates et des voyageurs.",
        "request_soon": "Demande de reservation bientot disponible",
        "book_now": "Reserver",
        "booking_request": "Demande de reservation",
        "payment_details": "Paiement",
        "booking_request_sent": "Demande recue",
        "booking_request_sent_text": "Nous avons recu votre demande. Notre equipe confirmera la disponibilite finale et repondra par email.",
        "account_confirmation_sent": "Nous avons envoye un lien pour valider votre email et activer votre compte.",
        "email_verification_title": "Validation de l'email",
        "email_verified": "Email valide",
        "email_verified_text": "Votre compte Porto Break est pret a etre utilise.",
        "email_already_verified": "Cet email est deja valide.",
        "email_verification_expired": "Ce lien de validation a expire.",
        "email_verification_invalid": "Ce lien de validation n'est pas valide.",
        "back_to_reservations": "Voir les logements",
        "customer_details": "Coordonnees",
        "reserve_as_guest": "Reserver sans creer de compte",
        "create_user_account": "Creer un compte utilisateur",
        "full_name": "Nom complet",
        "email": "Email",
        "phone": "Telephone",
        "address": "Adresse",
        "country": "Pays",
        "tax_id": "NIF",
        "password": "Mot de passe",
        "confirm_password": "Confirmer le mot de passe",
        "notes": "Observations",
        "submit_booking_request": "Continuer vers le paiement",
        "start_test_payment": "Continuer vers le paiement",
        "test_payment_notice": "Votre paiement sera traite de maniere securisee par Stripe.",
        "test_payment_title": "Paiement",
        "test_payment_completed": "Paiement termine",
        "test_payment_completed_text": "Votre paiement a ete recu et votre reservation est confirmee. Nous avons aussi envoye les details par email.",
        "test_payment_cancelled": "Paiement annule",
        "test_payment_cancelled_text": "Vous pouvez revenir au logement et reprendre le processus quand vous le souhaitez.",
        "test_payment_unavailable": "Impossible de preparer le paiement.",
        "required_field": "Remplissez les champs obligatoires.",
        "invalid_email": "Indiquez un email valide.",
        "password_mismatch": "Les mots de passe ne correspondent pas.",
        "password_short": "Le mot de passe doit contenir au moins 8 caracteres.",
        "email_already_registered": "Un compte existe deja avec cet email.",
        "booking_unavailable": "Impossible de creer la demande pour ces dates.",
        "booking_as_account": "Reservation en tant que {name}",
        "account_details_prefilled": "Les informations de votre compte ont ete renseignees pour cette demande.",
        "already_have_account": "Vous avez deja un compte ?",
        "sign_in_to_continue": "Se connecter",
        "reservation_summary": "Resume de la reservation",
        "guest_portal": "Portail voyageur",
        "open_guest_portal": "Ouvrir le portail voyageur",
        "booking_reference": "Reference de reservation",
        "total_paid": "Total paye",
        "payment_confirmed": "Paiement confirme",
        "login": "Se connecter",
        "logout": "Se deconnecter",
        "account": "Compte",
        "my_bookings": "Mes reservations",
        "my_bookings_lead": "Consultez vos sejours confirmes et leurs details.",
        "upcoming_stays": "Prochains sejours",
        "past_stays": "Sejours precedents",
        "no_bookings_title": "Vous n'avez pas encore de reservations confirmees.",
        "no_bookings_text": "Une reservation payee et confirmee apparaitra ici.",
        "explore_stays": "Voir les logements",
        "booking_confirmed": "Reservation confirmee",
        "view_booking": "Voir la reservation",
        "login_title": "Connectez-vous a votre compte",
        "login_lead": "Utilisez l'email et le mot de passe definis lors de la creation de votre compte Porto Break.",
        "login_submit": "Se connecter",
        "invalid_credentials": "Email ou mot de passe incorrect.",
        "email_unverified": "Validez l'email de votre compte avant de vous connecter.",
        "resend_validation_email": "Renvoyer l'email de validation",
        "resend_validation_sent": "Si le compte n'est pas encore valide, nous avons envoye un nouveau lien a l'email indique.",
        "resend_validation_wait": "Attendez une minute avant de demander un autre email de validation.",
        "resend_validation_failed": "Impossible de renvoyer l'email de validation. Reessayez.",
        "forgot_password": "Mot de passe oublie ?",
        "password_recovery": "Recuperer le mot de passe",
        "password_recovery_lead": "Indiquez l'email de votre compte. S'il est enregistre, nous enverrons un lien pour definir un nouveau mot de passe.",
        "send_password_reset": "Envoyer le lien de recuperation",
        "password_reset_sent": "Si un compte valide existe avec cet email, nous avons envoye un lien de recuperation.",
        "new_password": "Nouveau mot de passe",
        "set_new_password": "Definir le nouveau mot de passe",
        "password_reset_title": "Definir un nouveau mot de passe",
        "password_reset_lead": "Choisissez un nouveau mot de passe pour votre compte Porto Break.",
        "password_reset_success": "Mot de passe mis a jour",
        "password_reset_success_text": "Votre mot de passe a ete modifie. Vous pouvez maintenant vous connecter.",
        "password_reset_invalid": "Ce lien de recuperation n'est pas valide ou a deja ete utilise.",
        "password_reset_expired": "Ce lien de recuperation a expire. Demandez un nouveau lien.",
        "calendar_pick_free": "Choisissez une nuit libre pour commencer le sejour.",
        "calendar_pick_checkout": "Choisissez maintenant la date de depart.",
        "calendar_range_occupied": "La periode choisie traverse des nuits occupees.",
        "calendar_blocked_checkin": "L'arrivee n'est pas possible a cette date.",
        "calendar_blocked_checkout": "Le depart n'est pas possible a cette date.",
        "calendar_min_nights": "Ce logement exige au minimum {min} nuit(s).",
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
        "reviews_title": "Avis",
        "reviews_eyebrow": "Expériences voyageurs",
        "reviews_lead": "Avis partagés par des voyageurs ayant séjourné ici.",
        "review_singular": "avis",
        "review_plural": "avis",
        "view_reviews": "Voir les avis",
        "review_read_more": "Lire plus",
        "review_read_less": "Lire moins",
        "amenities_eyebrow": "Équipements",
        "amenities_title": "Ce que propose ce logement",
    },
}

LANG_LABELS = {
    "pt": "PT",
    "en": "EN",
    "es": "ES",
    "fr": "FR",
}


def _resolve_lang():
    consent = read_cookie_consent()
    remembered = request.cookies.get(LANG_COOKIE) if consent and consent["preferences"] else ""
    candidate = str(request.args.get("lang") or remembered or "").strip().lower()
    if candidate in SUPPORTED_LANGS:
        return candidate
    best = request.accept_languages.best_match(SUPPORTED_LANGS)
    return best if best in SUPPORTED_LANGS else "pt"


def _t(lang):
    return TRANSLATIONS.get(lang) or TRANSLATIONS["pt"]


def _format_cancellation_date(value: date, lang: str) -> str:
    months = CANCELLATION_MONTHS.get(lang) or CANCELLATION_MONTHS["pt"]
    if lang in {"pt", "es"}:
        return f"{value.day} de {months[value.month - 1]}"
    return f"{value.day} {months[value.month - 1]}"


def _cancellation_policy_context(checkin: date | None, lang: str, *, today: date | None = None) -> dict:
    copy = dict(CANCELLATION_POLICY_COPY.get(lang) or CANCELLATION_POLICY_COPY["pt"])
    if not checkin:
        return {**copy, "has_dates": False}

    # A faixa de 50% começa às 00:00 de D-10. Por isso, o último dia
    # integralmente reembolsável é D-11 (ex.: 18/09 para check-in em 29/09).
    partial_from = checkin - timedelta(days=10)
    free_until = partial_from - timedelta(days=1)
    current_date = today or date.today()
    return {
        **copy,
        "has_dates": True,
        "checkin": checkin.isoformat(),
        "free_until": free_until.isoformat(),
        "partial_from": partial_from.isoformat(),
        "no_refund_from": checkin.isoformat(),
        "show_free_cancellation": current_date <= free_until,
        "free_message_text": copy["free_message"].format(date=_format_cancellation_date(free_until, lang)),
        "partial_message_text": copy["partial_message"].format(date=_format_cancellation_date(partial_from, lang)),
        "none_message_text": copy["none_message"].format(date=_format_cancellation_date(checkin, lang)),
    }


def _cancellation_policy_url(checkin: date | None, lang: str, return_to: str = "") -> str:
    args = {"lang": lang}
    if checkin:
        args["checkin"] = checkin.isoformat()
    safe_return_to = _safe_portal_next(return_to)
    if safe_return_to:
        args["return_to"] = safe_return_to
    return url_for("booking_portal.cancellation_policy", **args)


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


def _portal_current_user() -> dict | None:
    user_id = str(session.get(PORTAL_USER_SESSION_KEY) or "").strip()
    if not user_id:
        return None
    user = get_portal_user(user_id)
    if not user:
        session.pop(PORTAL_USER_SESSION_KEY, None)
        return None
    return {
        "id": str(user.get("PBUSERSTAMP") or ""),
        "nome": str(user.get("NOME") or "").strip(),
        "email": str(user.get("EMAIL") or "").strip(),
        "telefone": str(user.get("TELEFONE") or "").strip(),
        "morada": str(user.get("MORADA") or "").strip(),
        "pais": str(user.get("PAIS") or "").strip(),
        "nif": str(user.get("NIF") or "").strip(),
    }


def _safe_portal_next(value: str) -> str:
    raw = str(value or "").strip()
    parsed = urlsplit(raw)
    if (
        raw.startswith("/")
        and not raw.startswith("//")
        and not parsed.scheme
        and not parsed.netloc
        and (parsed.path == "/reservas" or parsed.path.startswith("/reservas/"))
    ):
        return raw
    return ""


def _remember_payment_access(kind: str, identifier: str) -> None:
    value = str(identifier or "").strip()
    if not value:
        return
    access = dict(session.get(PORTAL_PAYMENT_ACCESS_SESSION_KEY) or {})
    items = [str(item) for item in (access.get(kind) or []) if str(item).strip()]
    if value not in items:
        items.append(value)
    access[kind] = items[-12:]
    session[PORTAL_PAYMENT_ACCESS_SESSION_KEY] = access
    session.modified = True


def _has_payment_access(kind: str, identifier: str) -> bool:
    value = str(identifier or "").strip()
    access = dict(session.get(PORTAL_PAYMENT_ACCESS_SESSION_KEY) or {})
    return bool(value and value in {str(item) for item in (access.get(kind) or [])})


def _with_lang_cookie(response, lang):
    return apply_language_cookie(response, lang, read_cookie_consent())


@bp.route("/reservas/preferencias-cookies", methods=["GET", "POST"])
def cookie_preferences():
    if request.method == "GET":
        response = jsonify(consent=read_cookie_consent())
        _with_lang_cookie(response, _resolve_lang())
    elif not is_same_origin_request():
        response = jsonify(error="origin_not_allowed")
        response.status_code = 403
    else:
        values = request.get_json(silent=True)
        if not isinstance(values, dict) or set(values) != {"preferences", "external_maps", "analytics"}:
            response = jsonify(error="invalid_preferences")
            response.status_code = 400
        elif any(type(values[key]) is not bool for key in values):
            response = jsonify(error="invalid_preferences")
            response.status_code = 400
        else:
            response = jsonify({})
            choice = save_cookie_consent(response, lang=_resolve_lang(), **values)
            response.set_data(json.dumps({"consent": choice}))
            if not choice["analytics"]:
                clear_identity_cookies(response)
    response.headers["Cache-Control"] = "private, no-store"
    response.vary.add("Cookie")
    return response


def _render_booking_template(template, lang, **context):
    seo = build_booking_seo(lang, context)
    translations = _t(lang)
    currency = _currency_context()
    legal_content = get_legal_content(lang)
    company = get_legal_company(current_app.config)
    return_to = _safe_portal_next(request.args.get("return_to") or "")
    if request.endpoint in {"booking_portal.detail", "booking_portal.reserve"}:
        return_to = _safe_portal_next(request.full_path.rstrip("?"))
    legal_args = {"lang": lang}
    if return_to:
        legal_args["return_to"] = return_to
    legal_links = [
        {"key": key, "label": legal_content["documents"][key]["title"], "url": url_for(endpoint, **legal_args)}
        for key, endpoint in LEGAL_ENDPOINTS.items()
    ]
    footer_copy = dict(BOOKING_FOOTER_COPY.get(lang) or BOOKING_FOOTER_COPY["pt"])
    footer_copy.update({
        "year": date.today().year,
        "reservations_url": url_for("booking_portal.index", lang=lang),
        "account_url": url_for("booking_portal.my_bookings", lang=lang),
        "cancellation_url": url_for("booking_portal.cancellation_policy", lang=lang),
        "legal": legal_content["ui"]["legal"],
        "legal_links": legal_links,
        "privacy_note": legal_content["ui"]["privacy_note"],
        "privacy_url": url_for("booking_portal.privacy", lang=lang),
        "complaints": COMPLAINTS_LABELS[lang],
        "address": company["address"],
        "tax_id": f"{('Tax ID' if lang == 'en' else 'NIF')} {company['tax_id']}",
    })
    alojamento = context.get("alojamento") or {}
    whatsapp = build_whatsapp_context(
        current_app.config,
        translations,
        property_name=alojamento.get("nome") or "",
        search=context.get("search") or {},
    )
    response = make_response(render_template(
        template,
        seo=seo,
        lang=lang,
        t=translations,
        language_links=_language_links(lang),
        portal_user=_portal_current_user(),
        booking_footer=footer_copy,
        booking_company=company,
        booking_legal_ui=legal_content["ui"],
        booking_legal_links={item["key"]: item for item in legal_links},
        booking_license_label=LICENSE_LABELS[lang],
        cookie_ui=cookie_ui(lang),
        cookie_consent=read_cookie_consent(),
        cookie_preferences_url=url_for("booking_portal.cookie_preferences", lang=lang),
        cookie_policy_url=url_for("booking_portal.cookies", lang=lang),
        booking_analytics=analytics_browser_config(lang, currency["code"]),
        booking_whatsapp=whatsapp,
        booking_currency=currency,
        booking_currency_options=[
            {
                "code": code,
                "symbol": details["symbol"],
                "name": translations.get(f"currency_{code.lower()}", details["name"]),
                "active": code == currency["code"],
            }
            for code, details in SUPPORTED_CURRENCIES.items()
        ],
        booking_currency_action=url_for("booking_portal.set_currency"),
        booking_currency_return=request.full_path.rstrip("?"),
        **context,
    ))
    # Never share cached consent or account state between visitors.
    response.headers["Cache-Control"] = "private, no-store"
    response.headers["X-Robots-Tag"] = seo["robots"]
    response.vary.add("Cookie")
    return _with_lang_cookie(response, lang)


@bp.post("/reservas/moeda")
def set_currency():
    code = normalize_currency(request.form.get("currency"), default="")
    if not code:
        abort(400)
    snapshot = load_currency_snapshot(code)
    if snapshot["code"] != code:
        abort(503)
    session[PORTAL_CURRENCY_SESSION_KEY] = snapshot
    session.modified = True
    target = _safe_portal_next(request.form.get("return_to") or request.referrer or "")
    return redirect(target or url_for("booking_portal.index", lang=_resolve_lang()))


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


def _reservation_query_args(params: dict, lang: str) -> dict:
    query = {"lang": lang}
    for key in ("checkin", "checkout", "adultos", "criancas", "bebes"):
        value = (params.get("raw") or {}).get(key)
        if value:
            query[key] = value
    return query


def _map_query_args(params: dict, lang: str) -> dict:
    """Keep the catalog search, including the legacy party count, across views."""
    query = _reservation_query_args(params, lang)
    raw = params.get("raw") or {}
    if raw.get("hospedes"):
        query["hospedes"] = raw["hospedes"]
    if params.get("query"):
        query["q"] = params["query"]
    return query


def _map_json(payload: dict, status: int = 200):
    response = jsonify(payload)
    response.status_code = status
    # Availability and quotations must not be reused as a promise of inventory.
    response.headers["Cache-Control"] = "private, no-store"
    response.vary.add("Cookie")
    return response


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
            for page_number in range(1, pages + 1)
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


def _date_policy_messages(al_id: str, params: dict, t: dict) -> list[str]:
    if not params.get("checkin") or not params.get("checkout") or params.get("errors"):
        return []
    result = alojamento_datas_permitidas(al_id, params["checkin"], params["checkout"])
    messages = []
    min_nights = int(result.get("min_nights") or 1)
    for error in result.get("errors") or []:
        if error == "min_nights":
            messages.append(t["calendar_min_nights"].format(min=min_nights))
        elif error == "blocked_checkin":
            messages.append(t["calendar_blocked_checkin"])
        elif error == "blocked_checkout":
            messages.append(t["calendar_blocked_checkout"])
    return messages


def _booking_customer_from_form() -> dict:
    return {
        "nome": str(request.form.get("nome") or "").strip(),
        "email": str(request.form.get("email") or "").strip(),
        "telefone": str(request.form.get("telefone") or "").strip(),
        "morada": str(request.form.get("morada") or "").strip(),
        "pais": str(request.form.get("pais") or "").strip(),
        "nif": str(request.form.get("nif") or "").strip(),
        "observacoes": str(request.form.get("observacoes") or "").strip(),
    }


def _booking_form_errors(customer: dict, *, create_account: bool, t: dict) -> list[str]:
    errors = []
    email = str(customer.get("email") or "").strip()
    if not customer.get("nome") or not email or not customer.get("pais"):
        errors.append(t["required_field"])
    if email and ("@" not in email or "." not in email.rsplit("@", 1)[-1]):
        errors.append(t["invalid_email"])
    if create_account:
        password = str(request.form.get("password") or "")
        confirm_password = str(request.form.get("confirm_password") or "")
        if len(password) < 8:
            errors.append(t["password_short"])
        if password != confirm_password:
            errors.append(t["password_mismatch"])
        if email and portal_user_exists(email):
            errors.append(t["email_already_registered"])
    return list(dict.fromkeys(errors))


def _portobreak_public_url(endpoint: str, **values) -> str:
    base_url = str(
        current_app.config.get("PORTOBREAK_PUBLIC_BASE_URL")
        or os.environ.get("PORTOBREAK_PUBLIC_BASE_URL")
        or "https://portobreak.com"
    ).strip().rstrip("/")
    return f"{base_url}{url_for(endpoint, **values)}"


def _guest_portal_serializer() -> URLSafeTimedSerializer:
    secret = str(current_app.config.get("SECRET_KEY") or "").strip()
    if not secret:
        raise RuntimeError("A chave da aplicacao nao esta configurada.")
    return URLSafeTimedSerializer(secret, salt=PORTAL_GUEST_PORTAL_TOKEN_SALT)


def _guest_portal_url(booking_id: str, email: str, lang: str) -> str:
    token = _guest_portal_serializer().dumps({
        "booking_id": str(booking_id or "").strip(),
        "email": str(email or "").strip().lower(),
    })
    return _portobreak_public_url("booking_portal.guest_portal", token=token, lang=lang)


def _guest_summary_from_booking(booking: dict, t: dict) -> str:
    parts = []
    for key, label_key in (("ADULTOS", "adults"), ("CRIANCAS", "children"), ("BEBES", "babies")):
        try:
            count = int(booking.get(key) or 0)
        except (TypeError, ValueError):
            count = 0
        if count:
            parts.append(f"{count} {t[label_key]}")
    return " / ".join(parts)


def _confirmed_booking_summary(booking_id: str, *, payment_id: str | None = None, lang: str = "pt", lock=False) -> dict | None:
    booking_id = str(booking_id or "").strip()
    if not booking_id:
        return None
    payment_condition = "AND P.PBPAYSTAMP = :payment_id" if payment_id else ""
    lock_hint = " WITH (UPDLOCK, HOLDLOCK)" if lock else ""
    booking = db.session.execute(
        text(
            f"""
            SELECT TOP 1
                B.PBBKSTAMP, B.PBUSERSTAMP, B.EMAIL_ID, B.EMAIL_INTERNO_ID, B.ALSTAMP, B.AL_NOME,
                B.CHECKIN, B.CHECKOUT, B.NOITES, B.ADULTOS, B.CRIANCAS, B.BEBES,
                B.CLIENTE_NOME, B.CLIENTE_EMAIL, B.CLIENTE_TELEFONE, B.CLIENTE_MORADA,
                B.CLIENTE_PAIS, B.CLIENTE_NIF, B.PRECO_ESTIMADO, B.PRECO_LABEL,
                R.RESERVA, P.PBPAYSTAMP, P.MOEDA, P.VALOR
            FROM dbo.PB_BOOKING_REQUESTS AS B{lock_hint}
            INNER JOIN dbo.PB_STRIPE_TEST_PAYMENTS AS P ON P.PBBKSTAMP = B.PBBKSTAMP
            INNER JOIN dbo.RS AS R ON R.RSSTAMP = P.RSSTAMP
            WHERE B.PBBKSTAMP = :booking_id
              {payment_condition}
              AND B.ESTADO = 'CONFIRMADO'
              AND P.ESTADO IN ('PAGO_TESTE', 'PAGO')
            """
        ),
        {"booking_id": booking_id, "payment_id": payment_id},
    ).mappings().first()
    if not booking:
        return None

    result = dict(booking)
    alojamento = get_alojamento(result.get("ALSTAMP"), lang=lang) or {}
    result["nome"] = alojamento.get("nome") or str(result.get("AL_NOME") or "").strip()
    result["foto"] = alojamento.get("foto") or ""
    result["localizacao"] = alojamento.get("localizacao") or ""
    result["guest_summary"] = _guest_summary_from_booking(result, _t(lang))
    result["dates"] = f"{result.get('CHECKIN') or ''} - {result.get('CHECKOUT') or ''}".strip(" -")
    total = (
        format_money(result.get("VALOR"), result.get("MOEDA") or "EUR")
        if result.get("VALOR") is not None else ""
    )
    if not total:
        total = str(result.get("PRECO_LABEL") or "").strip()
    if not total and result.get("PRECO_ESTIMADO") is not None:
        total = f"{result['PRECO_ESTIMADO']:.2f} EUR"
    result["total"] = total
    result["reservation_code"] = str(result.get("RESERVA") or "").strip()
    result["portal_url"] = _guest_portal_url(result["PBBKSTAMP"], result.get("CLIENTE_EMAIL") or "", lang)
    return result


def _send_account_verification_email(verification: dict, *, lang: str) -> int | None:
    email = str(verification.get("email") or "").strip()
    token = str(verification.get("token") or "").strip()
    if not email or not token:
        return None

    subjects = {
        "pt": "Valide o seu email - Porto Break",
        "en": "Verify your email - Porto Break",
        "es": "Valida tu email - Porto Break",
        "fr": "Validez votre email - Porto Break",
    }
    content = {
        "pt": {
            "greeting": "Olá",
            "intro": "Para ativar a sua conta Porto Break, valide o seu endereço de email.",
            "button": "Validar email",
            "expiry": "Este link e valido durante 48 horas.",
            "fallback": "Se o botao nao abrir, use este link:",
        },
        "en": {
            "greeting": "Hello",
            "intro": "To activate your Porto Break account, please verify your email address.",
            "button": "Verify email",
            "expiry": "This link is valid for 48 hours.",
            "fallback": "If the button does not open, use this link:",
        },
        "es": {
            "greeting": "Hola",
            "intro": "Para activar tu cuenta de Porto Break, valida tu direccion de email.",
            "button": "Validar email",
            "expiry": "Este enlace es valido durante 48 horas.",
            "fallback": "Si el boton no se abre, usa este enlace:",
        },
        "fr": {
            "greeting": "Bonjour",
            "intro": "Pour activer votre compte Porto Break, validez votre adresse email.",
            "button": "Valider l'email",
            "expiry": "Ce lien est valable pendant 48 heures.",
            "fallback": "Si le bouton ne s'ouvre pas, utilisez ce lien :",
        },
    }
    text_content = content.get(lang) or content["pt"]
    name = str(verification.get("nome") or "").strip()
    greeting = f"{text_content['greeting']} {name}".strip() + ","
    verify_url = _portobreak_public_url(
        "booking_portal.verify_email",
        token=token,
        lang=lang,
    )
    body_text = "\n".join([
        greeting,
        "",
        text_content["intro"],
        "",
        text_content["button"] + ": " + verify_url,
        text_content["expiry"],
        "",
        "Porto Break",
    ])
    body_html = f"""
    <div style="font-family:Inter,Arial,sans-serif;color:#1c1917;background:#f7f3ed;padding:24px;">
      <div style="max-width:620px;margin:0 auto;background:#fff;border:1px solid #ded6cb;border-radius:10px;padding:24px;">
        <h1 style="margin:0 0 12px;font-size:24px;">Porto Break</h1>
        <p style="margin:0 0 18px;">{html.escape(greeting)}</p>
        <p style="margin:0 0 24px;">{html.escape(text_content['intro'])}</p>
        <p style="margin:0 0 24px;">
          <a href="{html.escape(verify_url, quote=True)}" style="display:inline-block;background:#f97316;color:#fff;text-decoration:none;border-radius:8px;padding:12px 18px;font-weight:800;">{html.escape(text_content['button'])}</a>
        </p>
        <p style="margin:0 0 12px;color:#6b6258;font-size:14px;">{html.escape(text_content['expiry'])}</p>
        <p style="margin:0;color:#6b6258;font-size:12px;word-break:break-all;">{html.escape(text_content['fallback'])}<br>{html.escape(verify_url)}</p>
      </div>
    </div>
    """
    try:
        email_id = queue_email(
            to=email,
            subject=subjects.get(lang, subjects["pt"]),
            body_html=body_html,
            body_text=body_text,
            priority=2,
            context="PORTOBREAK_EMAIL_VERIFICATION",
            context_id=str(verification.get("id") or ""),
            created_by="portobreak_public",
            from_email="noreply@portobreak.com",
            from_name="Porto Break",
        )
        db.session.execute(
            text(
                """
                UPDATE dbo.PB_EMAIL_VERIFICATIONS
                SET EMAIL_ID = :email_id
                WHERE PBEMAILVERSTAMP = :verification_id
                """
            ),
            {"email_id": email_id, "verification_id": verification.get("id")},
        )
        db.session.commit()
        send_result = send_email_now(email_id)
        if not send_result.get("ok"):
            current_app.logger.warning(
                "Email de validacao Porto Break %s ficou com erro: %s",
                email_id,
                send_result.get("error") or "",
            )
        return int(email_id)
    except EmailServiceError:
        db.session.rollback()
        current_app.logger.exception("Nao foi possivel enviar email de validacao Porto Break")
    except Exception:
        db.session.rollback()
        current_app.logger.exception("Erro inesperado ao enviar email de validacao Porto Break")
    return None


def _send_password_reset_email(reset: dict, *, lang: str) -> int | None:
    email = str(reset.get("email") or "").strip()
    token = str(reset.get("token") or "").strip()
    if not email or not token:
        return None

    subjects = {
        "pt": "Recuperacao de password - Porto Break",
        "en": "Password recovery - Porto Break",
        "es": "Recuperacion de password - Porto Break",
        "fr": "Recuperation du mot de passe - Porto Break",
    }
    content = {
        "pt": {
            "greeting": "Olá",
            "intro": "Recebemos um pedido para definir uma nova password para a sua conta Porto Break.",
            "button": "Definir nova password",
            "expiry": "Este link e valido durante uma hora.",
            "ignore": "Se nao fez este pedido, pode ignorar este email.",
        },
        "en": {
            "greeting": "Hello",
            "intro": "We received a request to set a new password for your Porto Break account.",
            "button": "Set new password",
            "expiry": "This link is valid for one hour.",
            "ignore": "If you did not make this request, you can ignore this email.",
        },
        "es": {
            "greeting": "Hola",
            "intro": "Hemos recibido una solicitud para definir una nueva password para tu cuenta de Porto Break.",
            "button": "Definir nueva password",
            "expiry": "Este enlace es valido durante una hora.",
            "ignore": "Si no hiciste esta solicitud, puedes ignorar este email.",
        },
        "fr": {
            "greeting": "Bonjour",
            "intro": "Nous avons recu une demande pour definir un nouveau mot de passe pour votre compte Porto Break.",
            "button": "Definir le nouveau mot de passe",
            "expiry": "Ce lien est valable pendant une heure.",
            "ignore": "Si vous n'avez pas fait cette demande, vous pouvez ignorer cet email.",
        },
    }
    text_content = content.get(lang) or content["pt"]
    name = str(reset.get("nome") or "").strip()
    greeting = f"{text_content['greeting']} {name}".strip() + ","
    reset_url = _portobreak_public_url("booking_portal.password_reset", token=token, lang=lang)
    body_text = "\n".join([
        greeting,
        "",
        text_content["intro"],
        "",
        text_content["button"] + ": " + reset_url,
        text_content["expiry"],
        text_content["ignore"],
        "",
        "Porto Break",
    ])
    body_html = f"""
    <div style="font-family:Inter,Arial,sans-serif;color:#1c1917;background:#f7f3ed;padding:24px;">
      <div style="max-width:620px;margin:0 auto;background:#fff;border:1px solid #ded6cb;border-radius:10px;padding:24px;">
        <h1 style="margin:0 0 12px;font-size:24px;">Porto Break</h1>
        <p style="margin:0 0 18px;">{html.escape(greeting)}</p>
        <p style="margin:0 0 24px;">{html.escape(text_content['intro'])}</p>
        <p style="margin:0 0 24px;">
          <a href="{html.escape(reset_url, quote=True)}" style="display:inline-block;background:#f97316;color:#fff;text-decoration:none;border-radius:8px;padding:12px 18px;font-weight:800;">{html.escape(text_content['button'])}</a>
        </p>
        <p style="margin:0 0 12px;color:#6b6258;font-size:14px;">{html.escape(text_content['expiry'])}</p>
        <p style="margin:0;color:#6b6258;font-size:14px;">{html.escape(text_content['ignore'])}</p>
      </div>
    </div>
    """
    try:
        email_id = queue_email(
            to=email,
            subject=subjects.get(lang, subjects["pt"]),
            body_html=body_html,
            body_text=body_text,
            priority=2,
            context="PORTOBREAK_PASSWORD_RESET",
            context_id=str(reset.get("id") or ""),
            created_by="portobreak_public",
            from_email="noreply@portobreak.com",
            from_name="Porto Break",
        )
        db.session.execute(
            text(
                """
                UPDATE dbo.PB_PASSWORD_RESETS
                SET EMAIL_ID = :email_id
                WHERE PBPASSWORDRESETSTAMP = :reset_id
                """
            ),
            {"email_id": email_id, "reset_id": reset.get("id")},
        )
        db.session.commit()
        send_result = send_email_now(email_id)
        if not send_result.get("ok"):
            current_app.logger.warning(
                "Email de recuperacao Porto Break %s ficou com erro: %s",
                email_id,
                send_result.get("error") or "",
            )
        return int(email_id)
    except EmailServiceError:
        db.session.rollback()
        current_app.logger.exception("Nao foi possivel enviar email de recuperacao Porto Break")
    except Exception:
        db.session.rollback()
        current_app.logger.exception("Erro inesperado ao enviar email de recuperacao Porto Break")
    return None


def _send_booking_confirmation_email(success: dict, customer: dict, params: dict, preco: dict, lang: str) -> int | None:
    email = str(customer.get("email") or "").strip()
    if not email:
        return None

    subjects = {
        "pt": "Recebemos o seu pedido de reserva - Porto Break",
        "en": "We received your booking request - Porto Break",
        "es": "Hemos recibido tu solicitud de reserva - Porto Break",
        "fr": "Nous avons recu votre demande de reservation - Porto Break",
    }
    intros = {
        "pt": "Recebemos o seu pedido de reserva. A nossa equipa vai confirmar a disponibilidade final e responder por email.",
        "en": "We received your booking request. Our team will confirm final availability and reply by email.",
        "es": "Hemos recibido tu solicitud de reserva. Nuestro equipo confirmara la disponibilidad final y respondera por email.",
        "fr": "Nous avons recu votre demande de reservation. Notre equipe confirmera la disponibilite finale et repondra par email.",
    }
    labels = {
        "pt": {"stay": "Alojamento", "dates": "Datas", "guests": "Hospedes", "estimate": "Estimativa", "request": "Pedido", "note": "Este email confirma apenas a rececao do pedido. A reserva ainda nao esta confirmada."},
        "en": {"stay": "Stay", "dates": "Dates", "guests": "Guests", "estimate": "Estimate", "request": "Request", "note": "This email only confirms that we received the request. The booking is not confirmed yet."},
        "es": {"stay": "Alojamiento", "dates": "Fechas", "guests": "Huespedes", "estimate": "Estimacion", "request": "Solicitud", "note": "Este email solo confirma la recepcion de la solicitud. La reserva aun no esta confirmada."},
        "fr": {"stay": "Logement", "dates": "Dates", "guests": "Voyageurs", "estimate": "Estimation", "request": "Demande", "note": "Cet email confirme uniquement la reception de la demande. La reservation n'est pas encore confirmee."},
    }
    lang_labels = labels.get(lang) or labels["pt"]
    alojamento = success.get("alojamento") or {}
    guest_summary = params.get("guest_summary") or ""
    dates = f"{params.get('raw', {}).get('checkin') or ''} - {params.get('raw', {}).get('checkout') or ''}".strip(" -")
    estimate = (preco or {}).get("label") or ""
    request_id = success.get("id") or ""
    greeting_name = str(customer.get("nome") or "").strip()
    greeting = f"Olá {greeting_name}," if lang == "pt" else f"Hello {greeting_name},"
    if lang == "es":
        greeting = f"Hola {greeting_name},"
    elif lang == "fr":
        greeting = f"Bonjour {greeting_name},"

    text_lines = [
        greeting,
        "",
        intros.get(lang, intros["pt"]),
        "",
        f"{lang_labels['stay']}: {alojamento.get('nome') or ''}",
        f"{lang_labels['dates']}: {dates}",
        f"{lang_labels['guests']}: {guest_summary}",
        f"{lang_labels['estimate']}: {estimate}",
        f"{lang_labels['request']}: {request_id}",
        "",
        lang_labels["note"],
        "",
        "Porto Break",
    ]
    rows = [
        (lang_labels["stay"], alojamento.get("nome") or ""),
        (lang_labels["dates"], dates),
        (lang_labels["guests"], guest_summary),
        (lang_labels["estimate"], estimate),
        (lang_labels["request"], request_id),
    ]
    html_rows = "".join(
        "<tr>"
        f"<td style=\"padding:8px 10px;color:#6b6258;font-weight:700;\">{html.escape(str(label))}</td>"
        f"<td style=\"padding:8px 10px;color:#1c1917;font-weight:800;\">{html.escape(str(value))}</td>"
        "</tr>"
        for label, value in rows
    )
    body_html = f"""
    <div style="font-family:Inter,Arial,sans-serif;color:#1c1917;background:#f7f3ed;padding:24px;">
      <div style="max-width:620px;margin:0 auto;background:#fff;border:1px solid #ded6cb;border-radius:10px;padding:24px;">
        <h1 style="margin:0 0 12px;font-size:24px;">Porto Break</h1>
        <p style="margin:0 0 18px;">{html.escape(greeting)}</p>
        <p style="margin:0 0 18px;">{html.escape(intros.get(lang, intros["pt"]))}</p>
        <table style="width:100%;border-collapse:collapse;background:#f7f3ed;border-radius:8px;overflow:hidden;">{html_rows}</table>
        <p style="margin:18px 0 0;color:#6b6258;font-size:14px;">{html.escape(lang_labels["note"])}</p>
      </div>
    </div>
    """

    try:
        email_id = queue_email(
            to=email,
            subject=subjects.get(lang, subjects["pt"]),
            body_html=body_html,
            body_text="\n".join(text_lines),
            priority=3,
            context="PORTOBREAK_BOOKING_REQUEST",
            context_id=request_id,
            created_by="portobreak_public",
            from_email="noreply@portobreak.com",
            from_name="Porto Break",
        )
        db.session.execute(
            text("UPDATE dbo.PB_BOOKING_REQUESTS SET EMAIL_ID = :email_id WHERE PBBKSTAMP = :request_id"),
            {"email_id": email_id, "request_id": request_id},
        )
        db.session.commit()
        send_result = send_email_now(email_id)
        if not send_result.get("ok"):
            current_app.logger.warning(
                "Email Porto Break %s ficou com erro para pedido %s: %s",
                email_id,
                request_id,
                send_result.get("error") or "",
            )
        return int(email_id)
    except EmailServiceError:
        db.session.rollback()
        current_app.logger.exception("Nao foi possivel enfileirar email Porto Break para pedido %s", request_id)
    except Exception:
        db.session.rollback()
        current_app.logger.exception("Erro inesperado ao preparar email Porto Break para pedido %s", request_id)
    return None


def _send_paid_booking_confirmation_email(payment: dict, lang: str) -> int | None:
    """Send the booking confirmation once Stripe payment and the RS record exist."""
    payment_id = str(payment.get("id") or "").strip()
    booking_id = str(payment.get("booking_id") or "").strip()
    reservation_code = str(payment.get("reservation_code") or "").strip()
    if not payment_id or not booking_id or not reservation_code:
        return None

    try:
        booking = _confirmed_booking_summary(booking_id, payment_id=payment_id, lang=lang, lock=True)
        if not booking or booking.get("EMAIL_ID"):
            db.session.rollback()
            return None

        email = str(booking.get("CLIENTE_EMAIL") or "").strip()
        if not email:
            db.session.rollback()
            return None

        content = {
            "pt": {
                "subject": "Reserva confirmada - Porto Break",
                "greeting": "Ola",
                "intro": "O seu pagamento foi recebido e a sua reserva esta confirmada.",
                "stay": "Alojamento",
                "dates": "Datas",
                "guests": "Hospedes",
                "total": "Total pago",
                "reference": "Referencia",
                "note": "Pode consultar todos os detalhes da sua estadia no portal do hospede.",
                "button": "Abrir portal do hospede",
                "link": "Se o botao nao abrir, use este link:",
            },
            "en": {
                "subject": "Booking confirmed - Porto Break",
                "greeting": "Hello",
                "intro": "Your payment was received and your booking is confirmed.",
                "stay": "Stay",
                "dates": "Dates",
                "guests": "Guests",
                "total": "Total paid",
                "reference": "Reference",
                "note": "You can view all your stay details in the guest portal.",
                "button": "Open guest portal",
                "link": "If the button does not open, use this link:",
            },
            "es": {
                "subject": "Reserva confirmada - Porto Break",
                "greeting": "Hola",
                "intro": "Hemos recibido tu pago y tu reserva esta confirmada.",
                "stay": "Alojamiento",
                "dates": "Fechas",
                "guests": "Huespedes",
                "total": "Total pagado",
                "reference": "Referencia",
                "note": "Puedes consultar todos los detalles de tu estancia en el portal del huesped.",
                "button": "Abrir portal del huesped",
                "link": "Si el boton no abre, utiliza este enlace:",
            },
            "fr": {
                "subject": "Reservation confirmee - Porto Break",
                "greeting": "Bonjour",
                "intro": "Votre paiement a ete recu et votre reservation est confirmee.",
                "stay": "Logement",
                "dates": "Dates",
                "guests": "Voyageurs",
                "total": "Total paye",
                "reference": "Reference",
                "note": "Vous pouvez consulter tous les details de votre sejour dans le portail voyageur.",
                "button": "Ouvrir le portail voyageur",
                "link": "Si le bouton ne fonctionne pas, utilisez ce lien :",
            },
        }
        copy = content.get(lang) or content["pt"]
        reservation = booking.get("reservation_code") or reservation_code
        customer_name = str(booking.get("CLIENTE_NOME") or "").strip()
        greeting = f"{copy['greeting']} {customer_name},".strip() if customer_name else f"{copy['greeting']},"
        rows = [
            (copy["stay"], str(booking.get("nome") or "")),
            (copy["dates"], booking.get("dates") or ""),
            (copy["guests"], booking.get("guest_summary") or ""),
            (copy["total"], booking.get("total") or ""),
            (copy["reference"], reservation),
        ]
        portal_url = str(booking.get("portal_url") or "")
        text_body = "\n".join([
            greeting,
            "",
            copy["intro"],
            "",
            *[f"{label}: {value}" for label, value in rows],
            "",
            copy["note"],
            copy["button"] + ": " + portal_url,
            "",
            "Porto Break",
        ])
        html_rows = "".join(
            "<tr>"
            f"<td style=\"padding:8px 10px;color:#6b6258;font-weight:700;\">{html.escape(label)}</td>"
            f"<td style=\"padding:8px 10px;color:#1c1917;font-weight:800;\">{html.escape(value)}</td>"
            "</tr>"
            for label, value in rows
        )
        image_block = ""
        if booking.get("foto"):
            image_block = (
                f'<img src="{html.escape(str(booking["foto"]), quote=True)}" '
                f'alt="{html.escape(str(booking.get("nome") or "Porto Break"), quote=True)}" '
                'style="display:block;width:100%;height:230px;object-fit:cover;border-radius:10px 10px 0 0;" />'
            )
        body_html = f"""
        <div style="font-family:Inter,Arial,sans-serif;color:#1c1917;background:#f5f1ea;padding:28px 16px;">
          <div style="max-width:620px;margin:0 auto;background:#ffffff;border:1px solid #e2d8ca;border-radius:12px;overflow:hidden;">
            {image_block}
            <div style="padding:28px;">
              <p style="margin:0 0 8px;color:#f97316;font-size:12px;font-weight:800;letter-spacing:1.4px;text-transform:uppercase;">Porto Break</p>
              <h1 style="margin:0 0 14px;font-size:28px;line-height:1.15;">{html.escape(str(booking.get('nome') or ''))}</h1>
              <p style="margin:0 0 20px;">{html.escape(greeting)}</p>
              <p style="margin:0 0 22px;color:#615a52;line-height:1.5;">{html.escape(copy['intro'])}</p>
              <table style="width:100%;border-collapse:collapse;background:#f7f3ed;border-radius:8px;overflow:hidden;">{html_rows}</table>
              <p style="margin:22px 0 14px;color:#615a52;font-size:14px;line-height:1.5;">{html.escape(copy['note'])}</p>
              <p style="margin:0 0 20px;"><a href="{html.escape(portal_url, quote=True)}" style="display:inline-block;background:#f97316;color:#ffffff;text-decoration:none;border-radius:7px;padding:13px 18px;font-weight:800;">{html.escape(copy['button'])}</a></p>
              <p style="margin:0;color:#766e64;font-size:12px;line-height:1.5;">{html.escape(copy['link'])}<br><a href="{html.escape(portal_url, quote=True)}" style="color:#0b5f9e;word-break:break-all;">{html.escape(portal_url)}</a></p>
            </div>
          </div>
        </div>
        """
        email_id = queue_email(
            to=email,
            subject=copy["subject"],
            body_html=body_html,
            body_text=text_body,
            priority=3,
            context="PORTOBREAK_BOOKING_CONFIRMED",
            context_id=reservation,
            created_by="portobreak_public",
            from_email="noreply@portobreak.com",
            from_name="Porto Break",
        )
        db.session.execute(
            text(
                """
                UPDATE dbo.PB_BOOKING_REQUESTS
                SET EMAIL_ID = :email_id, DTALT = SYSUTCDATETIME()
                WHERE PBBKSTAMP = :booking_id
                  AND EMAIL_ID IS NULL
                """
            ),
            {"email_id": email_id, "booking_id": booking_id},
        )
        db.session.commit()
        send_result = send_email_now(email_id)
        if not send_result.get("ok"):
            current_app.logger.warning(
                "Email de confirmacao Porto Break %s ficou com erro para reserva %s: %s",
                email_id,
                reservation,
                send_result.get("error") or "",
            )
        return int(email_id)
    except EmailServiceError:
        db.session.rollback()
        current_app.logger.exception("Nao foi possivel enviar email de confirmacao Porto Break para reserva %s", reservation_code)
    except Exception:
        db.session.rollback()
        current_app.logger.exception("Erro inesperado ao enviar email de confirmacao Porto Break para reserva %s", reservation_code)
    return None


def _send_internal_paid_booking_notification(payment: dict, lang: str) -> int | None:
    """Send the operations team one independent notification per confirmed booking."""
    payment_id = str(payment.get("id") or "").strip()
    booking_id = str(payment.get("booking_id") or "").strip()
    reservation_code = str(payment.get("reservation_code") or "").strip()
    if not payment_id or not booking_id or not reservation_code:
        return None

    try:
        booking = _confirmed_booking_summary(booking_id, payment_id=payment_id, lang=lang, lock=True)
        if not booking or booking.get("EMAIL_INTERNO_ID"):
            db.session.rollback()
            return None

        rows = [
            ("Referência", booking.get("reservation_code") or reservation_code),
            ("Alojamento", booking.get("nome") or ""),
            ("Localização", booking.get("localizacao") or ""),
            ("Check-in", booking.get("CHECKIN") or ""),
            ("Check-out", booking.get("CHECKOUT") or ""),
            ("Noites", booking.get("NOITES") or 0),
            ("Hóspedes", booking.get("guest_summary") or ""),
            ("Total pago", booking.get("total") or ""),
            ("Nome do hóspede", booking.get("CLIENTE_NOME") or ""),
            ("Email do hóspede", booking.get("CLIENTE_EMAIL") or ""),
            ("Telefone", booking.get("CLIENTE_TELEFONE") or ""),
            ("Morada", booking.get("CLIENTE_MORADA") or ""),
            ("País", booking.get("CLIENTE_PAIS") or ""),
            ("NIF", booking.get("CLIENTE_NIF") or ""),
        ]
        text_body = "\n".join([
            "Nova reserva confirmada no Porto Break.", "",
            *[f"{label}: {value}" for label, value in rows],
        ])
        html_rows = "".join(
            "<tr>"
            f'<td style="padding:8px 10px;color:#6b6258;font-weight:700;">{html.escape(str(label))}</td>'
            f'<td style="padding:8px 10px;color:#1c1917;">{html.escape(str(value))}</td>'
            "</tr>"
            for label, value in rows
        )
        body_html = f"""
        <div style="font-family:Inter,Arial,sans-serif;color:#1c1917;background:#f5f1ea;padding:28px 16px;">
          <div style="max-width:620px;margin:0 auto;background:#ffffff;border:1px solid #e2d8ca;border-radius:12px;padding:28px;">
            <p style="margin:0 0 8px;color:#f97316;font-size:12px;font-weight:800;letter-spacing:1.4px;text-transform:uppercase;">Porto Break · Operações</p>
            <h1 style="margin:0 0 14px;font-size:28px;line-height:1.15;">Nova reserva confirmada</h1>
            <p style="margin:0 0 22px;color:#615a52;line-height:1.5;">O pagamento foi confirmado. Seguem todos os dados operacionais da reserva.</p>
            <table style="width:100%;border-collapse:collapse;background:#f7f3ed;border-radius:8px;overflow:hidden;">{html_rows}</table>
          </div>
        </div>
        """
        email_id = queue_email(
            to=list(PORTAL_INTERNAL_BOOKING_RECIPIENTS),
            subject=f"Nova reserva confirmada · {booking.get('reservation_code') or reservation_code} · Porto Break",
            body_html=body_html,
            body_text=text_body,
            priority=2,
            context="PORTOBREAK_BOOKING_INTERNAL_NOTIFICATION",
            context_id=booking_id,
            created_by="portobreak_public",
            from_email="noreply@portobreak.com",
            from_name="Porto Break",
        )
        updated = db.session.execute(
            text("""
                UPDATE dbo.PB_BOOKING_REQUESTS
                SET EMAIL_INTERNO_ID = :email_id, DTALT = SYSUTCDATETIME()
                WHERE PBBKSTAMP = :booking_id AND EMAIL_INTERNO_ID IS NULL
            """),
            {"email_id": email_id, "booking_id": booking_id},
        )
        if not updated.rowcount:
            db.session.rollback()
            return None
        db.session.commit()
        send_result = send_email_now(email_id)
        if not send_result.get("ok"):
            current_app.logger.warning(
                "Notificação interna Porto Break %s ficou com erro para reserva %s: %s",
                email_id, reservation_code, send_result.get("error") or "",
            )
        return int(email_id)
    except EmailServiceError:
        db.session.rollback()
        current_app.logger.exception("Não foi possível enviar notificação interna Porto Break para reserva %s", reservation_code)
    except Exception:
        db.session.rollback()
        current_app.logger.exception("Erro inesperado na notificação interna Porto Break para reserva %s", reservation_code)
    return None


@bp.route("/portal-reservas/recuperar-password", methods=["GET", "POST"])
@bp.route("/reservas/recuperar-password", methods=["GET", "POST"])
def password_recovery():
    lang = _resolve_lang()
    t = _t(lang)
    email = ""
    status = ""
    if request.method == "POST":
        email = str(request.form.get("email") or "").strip()
        now = int(time.time())
        last_sent_at = int(session.get(PORTAL_PASSWORD_RESET_COOLDOWN_SESSION_KEY) or 0)
        if last_sent_at and now - last_sent_at < PORTAL_PASSWORD_RESET_COOLDOWN_SECONDS:
            status = t["resend_validation_wait"]
        else:
            try:
                reset = criar_password_reset_portal(email)
                if reset:
                    _send_password_reset_email(reset, lang=lang)
                session[PORTAL_PASSWORD_RESET_COOLDOWN_SESSION_KEY] = now
                status = t["password_reset_sent"]
            except Exception:
                db.session.rollback()
                current_app.logger.exception("Erro ao preparar recuperacao de password Porto Break")
                status = t["password_reset_sent"]

    return _render_booking_template(
        "booking_portal/password_recovery.html",
        lang,
        recovery_email=email,
        recovery_status=status,
        page_title=t["password_recovery"],
    )


@bp.route("/portal-reservas/redefinir-password/<token>", methods=["GET", "POST"])
@bp.route("/reservas/redefinir-password/<token>", methods=["GET", "POST"])
def password_reset(token):
    lang = _resolve_lang()
    t = _t(lang)
    errors = []
    success = False
    if request.method == "POST":
        password = str(request.form.get("password") or "")
        confirm_password = str(request.form.get("confirm_password") or "")
        if len(password) < 8:
            errors.append(t["password_short"])
        if password != confirm_password:
            errors.append(t["password_mismatch"])
        if not errors:
            result = redefinir_password_portal(token, password)
            if result == "updated":
                success = True
            elif result == "expired":
                errors.append(t["password_reset_expired"])
            else:
                errors.append(t["password_reset_invalid"])

    return _render_booking_template(
        "booking_portal/password_reset.html",
        lang,
        reset_token=token,
        reset_errors=errors,
        reset_success=success,
        page_title=t["password_reset_title"],
    )


@bp.route("/portal-reservas/entrar", methods=["GET", "POST"])
@bp.route("/reservas/entrar", methods=["GET", "POST"])
def login():
    lang = _resolve_lang()
    t = _t(lang)
    existing_user = _portal_current_user()
    next_url = _safe_portal_next(request.values.get("next") or "")
    if existing_user:
        return redirect(next_url or url_for("booking_portal.index", lang=lang))

    email = ""
    errors = []
    can_resend_verification = False
    if request.method == "POST":
        email = str(request.form.get("email") or "").strip()
        password = str(request.form.get("password") or "")
        user, reason = autenticar_portal_user(email, password)
        if user:
            session[PORTAL_USER_SESSION_KEY] = user["id"]
            session.modified = True
            return redirect(next_url or url_for("booking_portal.index", lang=lang))
        errors.append(t.get(reason, t["invalid_credentials"]))
        can_resend_verification = reason == "email_unverified"

    return _render_booking_template(
        "booking_portal/login.html",
        lang,
        login_email=email,
        login_errors=errors,
        can_resend_verification=can_resend_verification,
        resend_status="",
        next_url=next_url,
        page_title=t["login_title"],
    )


@bp.route("/portal-reservas/reenviar-validacao", methods=["POST"])
@bp.route("/reservas/reenviar-validacao", methods=["POST"])
def resend_email_verification():
    lang = _resolve_lang()
    t = _t(lang)
    email = str(request.form.get("email") or "").strip()
    next_url = _safe_portal_next(request.form.get("next") or "")
    now = int(time.time())
    last_sent_at = int(session.get(PORTAL_RESEND_COOLDOWN_SESSION_KEY) or 0)
    resend_status = ""

    if last_sent_at and now - last_sent_at < PORTAL_RESEND_COOLDOWN_SECONDS:
        resend_status = t["resend_validation_wait"]
    else:
        user = get_unverified_portal_user_by_email(email)
        if user:
            try:
                verification = criar_verificacao_email_portal(user.get("PBUSERSTAMP"))
                email_id = _send_account_verification_email(verification or {}, lang=lang)
                if not email_id:
                    resend_status = t["resend_validation_failed"]
                else:
                    session[PORTAL_RESEND_COOLDOWN_SESSION_KEY] = now
                    resend_status = t["resend_validation_sent"]
            except Exception:
                db.session.rollback()
                current_app.logger.exception("Erro ao reenviar validacao de email Porto Break")
                resend_status = t["resend_validation_failed"]
        else:
            # A resposta e intencionalmente generica para nao expor contas existentes.
            session[PORTAL_RESEND_COOLDOWN_SESSION_KEY] = now
            resend_status = t["resend_validation_sent"]

    return _render_booking_template(
        "booking_portal/login.html",
        lang,
        login_email=email,
        login_errors=[],
        can_resend_verification=True,
        resend_status=resend_status,
        next_url=next_url,
        page_title=t["login_title"],
    )


@bp.route("/portal-reservas/sair", methods=["POST"])
@bp.route("/reservas/sair", methods=["POST"])
def logout():
    session.pop(PORTAL_USER_SESSION_KEY, None)
    return redirect(url_for("booking_portal.index", lang=_resolve_lang()))


@bp.route("/portal-reservas/minhas-reservas")
@bp.route("/reservas/minhas-reservas")
def my_bookings():
    lang = _resolve_lang()
    portal_user = _portal_current_user()
    if not portal_user:
        next_url = url_for("booking_portal.my_bookings", lang=lang)
        return redirect(url_for("booking_portal.login", lang=lang, next=next_url))

    bookings = get_portal_user_bookings(portal_user["id"], lang=lang)
    today = date.today()
    upcoming_bookings = []
    past_bookings = []
    for booking in bookings:
        booking["portal_url"] = _guest_portal_url(
            booking.get("PBBKSTAMP"),
            booking.get("CLIENTE_EMAIL"),
            lang,
        )
        checkout = booking.get("CHECKOUT")
        if checkout and checkout >= today:
            upcoming_bookings.append(booking)
        else:
            past_bookings.append(booking)

    upcoming_bookings.sort(key=lambda booking: booking.get("CHECKIN") or date.max)
    return _render_booking_template(
        "booking_portal/my_bookings.html",
        lang,
        upcoming_bookings=upcoming_bookings,
        past_bookings=past_bookings,
        page_title=_t(lang)["my_bookings"],
    )


def _render_legal_document(document_key):
    lang = _resolve_lang()
    content = get_legal_content(lang)
    return_to = _safe_portal_next(request.args.get("return_to") or "")
    link_args = {"lang": lang}
    if return_to:
        link_args["return_to"] = return_to
    urls = {f"{key}_url": url_for(endpoint, **link_args) for key, endpoint in LEGAL_ENDPOINTS.items()}
    urls["cancellation_url"] = url_for("booking_portal.cancellation_policy", **link_args)
    document = format_legal_content(content["documents"][document_key], {
        **get_legal_company(current_app.config),
        **urls,
        "session_cookie_name": current_app.config.get("SESSION_COOKIE_NAME", "session"),
    })
    document.update({"version": LEGAL_VERSION, "updated": LEGAL_UPDATED})
    policy = CANCELLATION_POLICY_COPY[lang]
    return _render_booking_template(
        "booking_portal/legal_page.html",
        lang,
        legal_document=document,
        legal_ui=content["ui"],
        legal_navigation=[
            {"label": content["documents"][key]["title"], "url": urls[f"{key}_url"], "active": key == document_key}
            for key in LEGAL_ENDPOINTS
        ],
        back_url=return_to or url_for("booking_portal.index", lang=lang),
        back_label=policy["back_to_reservation"] if return_to else policy["back"],
        page_title=document["title"],
    )


@bp.route("/reservas/termos-condicoes")
def terms():
    return _render_legal_document("terms")


@bp.route("/reservas/politica-privacidade")
def privacy():
    return _render_legal_document("privacy")


@bp.route("/reservas/politica-cookies")
def cookies():
    return _render_legal_document("cookies")


@bp.route("/reservas/informacao-legal")
def legal():
    return _render_legal_document("legal")


@bp.route("/portal-reservas/politica-cancelamento")
@bp.route("/reservas/politica-cancelamento")
def cancellation_policy():
    lang = _resolve_lang()
    checkin, _ = _parse_date_arg("checkin")
    policy = _cancellation_policy_context(checkin, lang)
    return_to = _safe_portal_next(request.args.get("return_to") or "")
    return _render_booking_template(
        "booking_portal/cancellation_policy.html",
        lang,
        policy=policy,
        back_url=return_to or url_for("booking_portal.index", lang=lang),
        back_label=policy["back_to_reservation"] if return_to else policy["back"],
        page_title=policy["page_title"],
    )


@bp.route("/portal-reservas")
@bp.route("/reservas")
def index():
    lang = _resolve_lang()
    currency = _currency_context()
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
    alojamentos = [_present_alojamento(item, currency) for item in pagination["items"]]
    for alojamento in alojamentos:
        alojamento["detail_url"] = _detail_url(alojamento["id"], params)

    return _render_booking_template(
        "booking_portal/index.html",
        lang,
        alojamentos=alojamentos,
        pagination=_pagination_context(pagination, lang),
        search=params,
        catalog_map={
            "view": "map" if request.args.get("view") == "map" else "list",
            "lang": lang,
            "data_url": url_for("booking_portal.map_catalog", **_map_query_args(params, lang)),
            "labels": get_map_copy(lang),
        },
        page_title=_t(lang)["page_reservations"],
    )


@bp.get("/reservas/mapa-dados")
def map_catalog():
    lang = _resolve_lang()
    params = _search_params(lang)
    try:
        catalog = get_map_catalog(params)
    except SQLAlchemyError:
        current_app.logger.exception("Não foi possível carregar o mapa de alojamentos PortoBreak")
        return _map_json({"error": get_map_copy(lang)["error"]}, 503)

    query = _map_query_args(params, lang)
    # Deliberate public allowlist: never serialize decorated AL records or RS data.
    items = [
        {
            "id": item["id"], "name": item["name"],
            "lat": item["lat"], "lon": item["lon"],
            "available": bool(item["available"]),
            "detail_url": _detail_url(item["id"], params),
            "quote_url": url_for("booking_portal.map_quote", al_id=item["id"], **query),
        }
        for item in catalog["items"]
    ]
    return _map_json({
        "items": items,
        "total": catalog["total"], "matched": catalog["matched"],
        "missing_coordinates": catalog["missing_coordinates"],
        "has_search": bool(catalog["has_search"] or params["errors"]),
        "has_dates": catalog["has_dates"],
        "errors": params["errors"], "guest_summary": params["guest_summary"],
    })


@bp.get("/reservas/<al_id>/simulacao-mapa")
def map_quote(al_id):
    """Read-only preview, computed only when a visitor selects a map property."""
    lang = _resolve_lang()
    params = _search_params(lang)
    t = _t(lang)
    copy = get_map_copy(lang)
    currency = _currency_context()
    try:
        alojamento = get_alojamento(al_id, lang=lang)
        if not alojamento:
            abort(404)
        constraints = _guest_constraints(alojamento, params, t)
        errors = list(params["errors"]) + constraints["errors"] + _date_policy_messages(al_id, params, t)
        has_dates = bool(params["checkin"] and params["checkout"])
        available = None
        price = None
        if has_dates and not errors:
            available = alojamento_disponivel(al_id, params["checkin"], params["checkout"])
            if available:
                calculated = _present_price(calcular_preco(
                    al_id, params["checkin"], params["checkout"], params["hospedes"],
                ), t, currency)
                if calculated and calculated.get("valor"):
                    price = {
                        "label": calculated["label"],
                        "airbnb_total_label": calculated.get("preco_total_airbnb_label") or "",
                        "airbnb_url": build_airbnb_search_url(
                            alojamento.get("airbnb_room_id"),
                            params["checkin"], params["checkout"],
                            params["adultos"] or params["hospedes"] or 1,
                        ),
                        "direct_total_label": calculated.get("preco_total_portobreak_label") or "",
                        "saving_label": calculated.get("poupanca_noites_label") or "",
                        "lines": [
                            {"label": line["label"], "value": line["value"]}
                            for line in calculated.get("linhas", [])
                        ],
                        "nights": calculated["noites"], "is_estimate": True,
                    }
                else:
                    errors.append(copy["no_price"])
            else:
                errors.append(t["unavailable_selected"])
        elif errors:
            available = False
    except SQLAlchemyError:
        current_app.logger.exception("Não foi possível simular um alojamento no mapa PortoBreak")
        return _map_json({"error": copy["quote_error"]}, 503)

    alojamento = _present_alojamento(alojamento, currency)
    detail_url = _detail_url(al_id, params)
    # The policy's return link goes back to the map with the same search.
    return_to = url_for("booking_portal.index", view="map", **_map_query_args(params, lang))
    policy = _cancellation_policy_context(params["checkin"], lang)
    cancellation = {
        "label": policy["free_message_text"] if policy.get("show_free_cancellation") else policy["policy_link"],
        "url": _cancellation_policy_url(params["checkin"], lang, return_to),
    }
    return _map_json({
        "id": alojamento["id"], "name": alojamento["nome"],
        "image": alojamento.get("foto_principal") or "",
        "tipologia": alojamento.get("tipologia") or "",
        "capacity": alojamento.get("capacidade"),
        "location": alojamento.get("localizacao") or "",
        "from_price": alojamento.get("preco_desde") or "",
        "price": price, "available": available,
        "reserve_enabled": bool(available is True and price and not errors),
        "errors": errors, "notes": constraints["notes"],
        "detail_url": detail_url,
        "reserve_url": url_for("booking_portal.reserve", al_id=al_id, **_reservation_query_args(params, lang)),
        "dates": {
            "checkin": params["checkin"].isoformat() if params["checkin"] else "",
            "checkout": params["checkout"].isoformat() if params["checkout"] else "",
        },
        "guest_summary": params["guest_summary"] or (f"1 {t['guest']}" if has_dates else ""),
        "cancellation": cancellation,
    })


@bp.route("/portal-reservas/alojamento/<al_id>")
@bp.route("/reservas/<al_id>")
def detail(al_id):
    lang = _resolve_lang()
    currency = _currency_context()
    params = _search_params(lang)
    t = _t(lang)
    alojamento = get_alojamento(al_id, lang=lang)
    if not alojamento:
        abort(404)

    guest_constraints = _guest_constraints(alojamento, params, t)
    date_policy_errors = _date_policy_messages(al_id, params, t)
    disponibilidade = None
    blocking_errors = guest_constraints["errors"] + date_policy_errors
    if blocking_errors:
        preco = _present_price(calcular_preco(al_id, None, None, None), t, currency)
    else:
        preco = _present_price(calcular_preco(al_id, params["checkin"], params["checkout"], params["hospedes"]), t, currency)
    if params["checkin"] and params["checkout"] and not params["errors"] and not blocking_errors:
        disponibilidade = alojamento_disponivel(al_id, params["checkin"], params["checkout"])
    if preco.get("valor"):
        preco["airbnb_url"] = build_airbnb_search_url(
            alojamento.get("airbnb_room_id"),
            params["checkin"], params["checkout"],
            params["adultos"] or params["hospedes"] or 1,
        )

    calendar_start = (params["checkin"] or date.today()).replace(day=1)
    calendario = get_calendario_ocupacao(al_id, start=calendar_start, months=12)
    calendario["initial_month"] = calendar_start.isoformat()
    reserve_enabled = bool(
        disponibilidade is True
        and params["checkin"]
        and params["checkout"]
        and not params["errors"]
        and not blocking_errors
    )

    alojamento = _present_alojamento(alojamento, currency)
    return _render_booking_template(
        "booking_portal/detail.html",
        lang,
        alojamento=alojamento,
        search=params,
        guest_errors=blocking_errors,
        guest_notes=guest_constraints["notes"],
        disponibilidade=disponibilidade,
        preco=preco,
        calendario=calendario,
        reserve_enabled=reserve_enabled,
        reserve_url=url_for("booking_portal.reserve", al_id=al_id, **_reservation_query_args(params, lang)),
        cancellation_policy=_cancellation_policy_context(params.get("checkin"), lang),
        cancellation_policy_url=_cancellation_policy_url(
            params.get("checkin"),
            lang,
            request.full_path.rstrip("?"),
        ),
        page_title=alojamento["nome"],
    )


@bp.route("/portal-reservas/alojamento/<al_id>/reservar", methods=["GET", "POST"])
@bp.route("/reservas/<al_id>/reservar", methods=["GET", "POST"])
def reserve(al_id):
    lang = _resolve_lang()
    currency = _currency_context()
    t = _t(lang)
    params = _search_params(lang)
    portal_user = _portal_current_user()
    alojamento = get_alojamento(al_id, lang=lang)
    if not alojamento:
        abort(404)

    guest_constraints = _guest_constraints(alojamento, params, t)
    date_policy_errors = _date_policy_messages(al_id, params, t)
    booking_errors = list(params["errors"]) + guest_constraints["errors"] + date_policy_errors
    disponibilidade = None
    if params["checkin"] and params["checkout"] and not booking_errors:
        disponibilidade = alojamento_disponivel(al_id, params["checkin"], params["checkout"])
        if disponibilidade is not True:
            booking_errors.append(t["unavailable_selected"])

    if booking_errors:
        preco = _present_price(calcular_preco(al_id, None, None, None), t, currency)
    else:
        preco = _present_price(calcular_preco(al_id, params["checkin"], params["checkout"], params["hospedes"]), t, currency)
    if preco.get("valor"):
        preco["airbnb_url"] = build_airbnb_search_url(
            alojamento.get("airbnb_room_id"),
            params["checkin"], params["checkout"],
            params["adultos"] or params["hospedes"] or 1,
        )

    customer = {
        "nome": "",
        "email": "",
        "telefone": "",
        "morada": "",
        "pais": "Portugal" if lang == "pt" else "",
        "nif": "",
        "observacoes": "",
    }
    if portal_user:
        customer.update({
            "nome": portal_user.get("nome") or "",
            "email": portal_user.get("email") or "",
            "telefone": portal_user.get("telefone") or "",
            "morada": portal_user.get("morada") or "",
            "pais": portal_user.get("pais") or ("Portugal" if lang == "pt" else ""),
            "nif": portal_user.get("nif") or "",
        })
    account_mode = "guest"
    form_errors = []
    success = None

    if request.method == "POST":
        account_mode = "signed_in" if portal_user else ("account" if request.form.get("account_mode") == "account" else "guest")
        customer = _booking_customer_from_form()
        if portal_user:
            customer["email"] = portal_user.get("email") or ""
        create_account = account_mode == "account" and not portal_user
        form_errors = _booking_form_errors(customer, create_account=create_account, t=t)
        if not booking_errors and not form_errors:
            try:
                success = criar_pedido_reserva(
                    al_id,
                    params,
                    customer,
                    create_account=create_account,
                    password=request.form.get("password") if create_account else None,
                    authenticated_user_id=portal_user.get("id") if portal_user else None,
                    ip=request.headers.get("CF-Connecting-IP") or request.remote_addr or "",
                    user_agent=request.headers.get("User-Agent", ""),
                    currency_snapshot=currency,
                )
                verification = success.pop("email_verification", None)
                if verification:
                    verification.update({
                        "email": customer.get("email"),
                        "nome": customer.get("nome"),
                    })
                    success["verification_email_id"] = _send_account_verification_email(verification, lang=lang)
                    success["email_verification_sent"] = bool(success["verification_email_id"])
                _remember_payment_access("booking", success["id"])
                associate_booking(success["id"])
                return _start_portal_payment(success["id"], lang, portal_user)
            except ValueError as exc:
                db.session.rollback()
                if str(exc) == "email_ja_registado":
                    form_errors.append(t["email_already_registered"])
                else:
                    form_errors.append(t["booking_unavailable"])
            except Exception:
                db.session.rollback()
                current_app.logger.exception("Erro ao criar pedido de reserva publico para AL %s", al_id)
                form_errors.append(t["booking_unavailable"])

    alojamento = _present_alojamento(alojamento, currency)
    return _render_booking_template(
        "booking_portal/reserve.html",
        lang,
        alojamento=alojamento,
        search=params,
        guest_notes=guest_constraints["notes"],
        booking_errors=booking_errors,
        form_errors=form_errors,
        customer=customer,
        account_mode=account_mode,
        signed_in_user=portal_user,
        booking_account_label=(t["booking_as_account"].format(name=portal_user.get("nome") or portal_user.get("email") or "") if portal_user else ""),
        preco=preco,
        success=success,
        detail_url=url_for("booking_portal.detail", al_id=al_id, **_reservation_query_args(params, lang)),
        cancellation_policy=_cancellation_policy_context(params.get("checkin"), lang),
        cancellation_policy_url=_cancellation_policy_url(
            params.get("checkin"),
            lang,
            request.full_path.rstrip("?"),
        ),
        login_url=url_for(
            "booking_portal.login",
            lang=lang,
            next=url_for("booking_portal.reserve", al_id=al_id, **_reservation_query_args(params, lang)),
        ),
        page_title=t["payment_details"],
    )


def _start_portal_payment(request_id, lang, portal_user):
    t = _t(lang)
    if not portal_user and not _has_payment_access("booking", request_id):
        abort(404)

    placeholder = "PORTOBREAK_CHECKOUT_SESSION"
    result_base_url = url_for(
        "booking_portal.payment_result",
        lang=lang,
        session_id=placeholder,
        _external=True,
    ).replace(placeholder, "{CHECKOUT_SESSION_ID}")
    try:
        checkout = criar_checkout_teste_portal(
            request_id,
            portal_user.get("id") if portal_user else None,
            success_url=f"{result_base_url}&checkout=success",
            cancel_url=f"{result_base_url}&checkout=cancel",
            lang=lang,
        )
    except PortalPaymentError as exc:
        current_app.logger.warning("Pagamento Stripe de teste indisponivel para pedido %s: %s", request_id, exc)
        return _render_booking_template(
            "booking_portal/payment_result.html",
            lang,
            payment=None,
            payment_error=str(exc) or t["test_payment_unavailable"],
            cancelled=False,
            back_url=url_for("booking_portal.index", lang=lang),
            page_title=t["test_payment_title"],
        )
    except Exception:
        current_app.logger.exception("Erro ao criar checkout Stripe de teste para pedido %s", request_id)
        return _render_booking_template(
            "booking_portal/payment_result.html",
            lang,
            payment=None,
            payment_error=t["test_payment_unavailable"],
            cancelled=False,
            back_url=url_for("booking_portal.index", lang=lang),
            page_title=t["test_payment_title"],
        )
    _remember_payment_access("checkout", checkout["session_id"])
    return redirect(checkout["checkout_url"])


@bp.route("/portal-reservas/pagamento/<request_id>", methods=["POST"])
@bp.route("/reservas/pagamento/<request_id>", methods=["POST"])
def start_payment(request_id):
    lang = _resolve_lang()
    portal_user = _portal_current_user()
    return _start_portal_payment(request_id, lang, portal_user)


@bp.route("/portal-reservas/pagamento/resultado")
@bp.route("/reservas/pagamento/resultado")
def payment_result():
    lang = _resolve_lang()
    t = _t(lang)
    portal_user = _portal_current_user()
    session_id = str(request.args.get("session_id") or "").strip()
    if not session_id:
        abort(404)
    if not portal_user and not _has_payment_access("checkout", session_id):
        abort(404)
    cancelled = str(request.args.get("checkout") or "").strip().lower() == "cancel"
    booking = None
    try:
        payment = sincronizar_checkout_teste_portal(session_id, portal_user.get("id") if portal_user else None)
        if not payment:
            abort(404)
        if payment.get("paid") and payment.get("reservation_code"):
            _send_paid_booking_confirmation_email(payment, lang)
            _send_internal_paid_booking_notification(payment, lang)
            booking = _confirmed_booking_summary(payment.get("booking_id"), payment_id=payment.get("id"), lang=lang)
        payment_error = ""
    except PortalPaymentError as exc:
        current_app.logger.warning("Erro a confirmar checkout Stripe de teste %s: %s", session_id, exc)
        payment = None
        payment_error = str(exc) or t["test_payment_unavailable"]
    except Exception:
        current_app.logger.exception("Erro inesperado a confirmar checkout Stripe de teste %s", session_id)
        payment = None
        payment_error = t["test_payment_unavailable"]
    return _render_booking_template(
        "booking_portal/payment_result.html",
        lang,
        payment=payment,
        booking=booking,
        payment_error=payment_error,
        cancelled=cancelled,
        back_url=url_for("booking_portal.index", lang=lang),
        page_title=t["test_payment_title"],
    )


@bp.route("/portal-reservas/stripe/webhook", methods=["POST"])
@bp.route("/reservas/stripe/webhook", methods=["POST"])
def stripe_webhook():
    payload = request.get_data(cache=False, as_text=False) or b""
    signature = request.headers.get("Stripe-Signature") or ""
    if not verificar_assinatura_webhook_stripe_portal(payload, signature):
        current_app.logger.warning("Webhook Stripe Porto Break rejeitado por assinatura invalida.")
        return jsonify({"error": "Assinatura invalida."}), 400
    try:
        event = json.loads(payload.decode("utf-8") or "{}")
    except Exception:
        return jsonify({"error": "Payload invalido."}), 400
    try:
        result = processar_webhook_stripe_portal(event)
        payment = result.get("payment") or {}
        if payment.get("paid") and payment.get("reservation_code"):
            _send_paid_booking_confirmation_email(payment, _resolve_lang())
            _send_internal_paid_booking_notification(payment, _resolve_lang())
        return jsonify({"ok": True, "duplicate": bool(result.get("duplicate"))})
    except PortalPaymentError as exc:
        current_app.logger.exception("Falha ao processar webhook Stripe Porto Break: %s", exc)
        return jsonify({"error": "Falha ao processar pagamento."}), 500
    except Exception:
        current_app.logger.exception("Erro inesperado no webhook Stripe Porto Break")
        return jsonify({"error": "Erro interno."}), 500


@bp.route("/portal-reservas/portal/<token>")
@bp.route("/reservas/portal/<token>")
def guest_portal(token):
    lang = _resolve_lang()
    try:
        payload = _guest_portal_serializer().loads(token, max_age=PORTAL_GUEST_PORTAL_TOKEN_MAX_AGE)
    except (BadSignature, SignatureExpired):
        abort(404)
    booking_id = str((payload or {}).get("booking_id") or "").strip()
    token_email = str((payload or {}).get("email") or "").strip().lower()
    booking = _confirmed_booking_summary(booking_id, lang=lang)
    if not booking or str(booking.get("CLIENTE_EMAIL") or "").strip().lower() != token_email:
        abort(404)
    reservation_code = str(booking.get("reservation_code") or "").strip()
    public_portal_view = current_app.view_functions.get("public_reserva_page")
    if not reservation_code or not public_portal_view:
        abort(404)

    # Reutiliza a area completa de hospede ja usada em r_public2, mas a
    # entrada continua protegida pelo link assinado deste portal.
    return public_portal_view(
        reservation_code,
        force_public_v2=True,
        portal_account=_portal_current_user(),
    )


@bp.route("/portal-reservas/validar-email/<token>")
@bp.route("/reservas/validar-email/<token>")
def verify_email(token):
    lang = _resolve_lang()
    t = _t(lang)
    result = confirmar_email_portal(token)
    if result == "confirmed":
        title = t["email_verified"]
        message = t["email_verified_text"]
        success = True
    elif result == "already_confirmed":
        title = t["email_verified"]
        message = t["email_already_verified"]
        success = True
    elif result == "expired":
        title = t["email_verification_title"]
        message = t["email_verification_expired"]
        success = False
    else:
        title = t["email_verification_title"]
        message = t["email_verification_invalid"]
        success = False
    return _render_booking_template(
        "booking_portal/email_verification.html",
        lang,
        verification_title=title,
        verification_message=message,
        verification_success=success,
        page_title=title,
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
        **get_calendario_ocupacao(al_id, start=start or date.today(), months=months),
    })
