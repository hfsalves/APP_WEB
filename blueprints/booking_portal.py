from __future__ import annotations

import html
import os
from datetime import date
from urllib.parse import urlsplit

from flask import Blueprint, abort, current_app, jsonify, make_response, redirect, render_template, request, session, url_for

from models import db
from sqlalchemy import text

from services.booking_portal_service import (
    alojamento_datas_permitidas,
    alojamento_disponivel,
    autenticar_portal_user,
    calcular_preco,
    confirmar_email_portal,
    criar_pedido_reserva,
    get_alojamento,
    get_alojamentos_disponiveis_page,
    get_calendario_ocupacao,
    get_portal_user,
    criar_verificacao_email_portal,
    portal_user_exists,
)
from services.email_service import EmailServiceError, queue_email, send_email_now


bp = Blueprint("booking_portal", __name__)

SUPPORTED_LANGS = ("pt", "en", "es", "fr")
LANG_COOKIE = "portobreak_lang"
BOOKING_PAGE_SIZE = 18
PORTAL_USER_SESSION_KEY = "PORTOBREAK_USER_ID"

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
        "book_now": "Reservar",
        "booking_request": "Pedido de reserva",
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
        "submit_booking_request": "Enviar pedido de reserva",
        "required_field": "Preencha os campos obrigatorios.",
        "invalid_email": "Indique um email valido.",
        "password_mismatch": "As passwords nao coincidem.",
        "password_short": "A password deve ter pelo menos 8 caracteres.",
        "email_already_registered": "Ja existe uma conta com este email.",
        "booking_unavailable": "Nao foi possivel criar o pedido para estas datas.",
        "login": "Entrar",
        "logout": "Terminar sessao",
        "account": "Conta",
        "login_title": "Entre na sua conta",
        "login_lead": "Use o email e a password definidos ao criar a conta Porto Break.",
        "login_submit": "Entrar",
        "invalid_credentials": "Email ou password incorretos.",
        "email_unverified": "Valide o email da sua conta antes de entrar.",
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
        "book_now": "Book",
        "booking_request": "Booking request",
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
        "submit_booking_request": "Send booking request",
        "required_field": "Fill in the required fields.",
        "invalid_email": "Enter a valid email.",
        "password_mismatch": "Passwords do not match.",
        "password_short": "Password must be at least 8 characters.",
        "email_already_registered": "An account with this email already exists.",
        "booking_unavailable": "The request could not be created for these dates.",
        "login": "Sign in",
        "logout": "Sign out",
        "account": "Account",
        "login_title": "Sign in to your account",
        "login_lead": "Use the email and password set when you created your Porto Break account.",
        "login_submit": "Sign in",
        "invalid_credentials": "Incorrect email or password.",
        "email_unverified": "Verify your account email before signing in.",
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
        "book_now": "Reservar",
        "booking_request": "Solicitud de reserva",
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
        "submit_booking_request": "Enviar solicitud de reserva",
        "required_field": "Rellena los campos obligatorios.",
        "invalid_email": "Indica un email valido.",
        "password_mismatch": "Las passwords no coinciden.",
        "password_short": "La password debe tener al menos 8 caracteres.",
        "email_already_registered": "Ya existe una cuenta con este email.",
        "booking_unavailable": "No ha sido posible crear la solicitud para estas fechas.",
        "login": "Entrar",
        "logout": "Cerrar sesion",
        "account": "Cuenta",
        "login_title": "Entra en tu cuenta",
        "login_lead": "Usa el email y la password definidos al crear tu cuenta de Porto Break.",
        "login_submit": "Entrar",
        "invalid_credentials": "Email o password incorrectos.",
        "email_unverified": "Valida el email de tu cuenta antes de entrar.",
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
        "book_now": "Reserver",
        "booking_request": "Demande de reservation",
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
        "submit_booking_request": "Envoyer la demande",
        "required_field": "Remplissez les champs obligatoires.",
        "invalid_email": "Indiquez un email valide.",
        "password_mismatch": "Les mots de passe ne correspondent pas.",
        "password_short": "Le mot de passe doit contenir au moins 8 caracteres.",
        "email_already_registered": "Un compte existe deja avec cet email.",
        "booking_unavailable": "Impossible de creer la demande pour ces dates.",
        "login": "Se connecter",
        "logout": "Se deconnecter",
        "account": "Compte",
        "login_title": "Connectez-vous a votre compte",
        "login_lead": "Utilisez l'email et le mot de passe definis lors de la creation de votre compte Porto Break.",
        "login_submit": "Se connecter",
        "invalid_credentials": "Email ou mot de passe incorrect.",
        "email_unverified": "Validez l'email de votre compte avant de vous connecter.",
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


def _with_lang_cookie(response, lang):
    response.set_cookie(LANG_COOKIE, lang, max_age=60 * 60 * 24 * 365, samesite="Lax")
    return response


def _render_booking_template(template, lang, **context):
    response = make_response(render_template(
        template,
        lang=lang,
        t=_t(lang),
        language_links=_language_links(lang),
        portal_user=_portal_current_user(),
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


def _reservation_query_args(params: dict, lang: str) -> dict:
    query = {"lang": lang}
    for key in ("checkin", "checkout", "adultos", "criancas", "bebes"):
        value = (params.get("raw") or {}).get(key)
        if value:
            query[key] = value
    return query


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
    if request.method == "POST":
        email = str(request.form.get("email") or "").strip()
        password = str(request.form.get("password") or "")
        user, reason = autenticar_portal_user(email, password)
        if user:
            session[PORTAL_USER_SESSION_KEY] = user["id"]
            session.modified = True
            return redirect(next_url or url_for("booking_portal.index", lang=lang))
        errors.append(t.get(reason, t["invalid_credentials"]))

    return _render_booking_template(
        "booking_portal/login.html",
        lang,
        login_email=email,
        login_errors=errors,
        next_url=next_url,
        page_title=t["login_title"],
    )


@bp.route("/portal-reservas/sair", methods=["POST"])
@bp.route("/reservas/sair", methods=["POST"])
def logout():
    session.pop(PORTAL_USER_SESSION_KEY, None)
    return redirect(url_for("booking_portal.index", lang=_resolve_lang()))


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
    date_policy_errors = _date_policy_messages(al_id, params, t)
    disponibilidade = None
    blocking_errors = guest_constraints["errors"] + date_policy_errors
    if blocking_errors:
        preco = _translate_price(calcular_preco(al_id, None, None, None), t)
    else:
        preco = _translate_price(calcular_preco(al_id, params["checkin"], params["checkout"], params["hospedes"]), t)
    if params["checkin"] and params["checkout"] and not params["errors"] and not blocking_errors:
        disponibilidade = alojamento_disponivel(al_id, params["checkin"], params["checkout"])

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
        page_title=alojamento["nome"],
    )


@bp.route("/portal-reservas/alojamento/<al_id>/reservar", methods=["GET", "POST"])
@bp.route("/reservas/<al_id>/reservar", methods=["GET", "POST"])
def reserve(al_id):
    lang = _resolve_lang()
    t = _t(lang)
    params = _search_params(lang)
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
        preco = _translate_price(calcular_preco(al_id, None, None, None), t)
    else:
        preco = _translate_price(calcular_preco(al_id, params["checkin"], params["checkout"], params["hospedes"]), t)

    customer = {
        "nome": "",
        "email": "",
        "telefone": "",
        "morada": "",
        "pais": "Portugal" if lang == "pt" else "",
        "nif": "",
        "observacoes": "",
    }
    account_mode = "guest"
    form_errors = []
    success = None

    if request.method == "POST":
        account_mode = "account" if request.form.get("account_mode") == "account" else "guest"
        customer = _booking_customer_from_form()
        create_account = account_mode == "account"
        form_errors = _booking_form_errors(customer, create_account=create_account, t=t)
        if not booking_errors and not form_errors:
            try:
                success = criar_pedido_reserva(
                    al_id,
                    params,
                    customer,
                    create_account=create_account,
                    password=request.form.get("password") if create_account else None,
                    ip=request.headers.get("CF-Connecting-IP") or request.remote_addr or "",
                    user_agent=request.headers.get("User-Agent", ""),
                )
                verification = success.pop("email_verification", None)
                if verification:
                    verification.update({
                        "email": customer.get("email"),
                        "nome": customer.get("nome"),
                    })
                    success["verification_email_id"] = _send_account_verification_email(verification, lang=lang)
                    success["email_verification_sent"] = bool(success["verification_email_id"])
                success["email_id"] = _send_booking_confirmation_email(success, customer, params, preco, lang)
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
        preco=preco,
        success=success,
        detail_url=url_for("booking_portal.detail", al_id=al_id, **_reservation_query_args(params, lang)),
        page_title=t["booking_request"],
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
