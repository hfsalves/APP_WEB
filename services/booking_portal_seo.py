"""Public discovery metadata; never serialize reservation or account context."""

import html
import ipaddress
import os
import re
from urllib.parse import quote, urlencode, urlsplit

from flask import current_app, request, url_for


SUPPORTED_LANGS = ("pt", "en", "es", "fr")
PUBLIC_ENDPOINTS = frozenset({
    "booking_portal.index", "booking_portal.detail", "booking_portal.cancellation_policy",
    "booking_portal.terms", "booking_portal.privacy", "booking_portal.cookies", "booking_portal.legal",
})
DEFAULT_PUBLIC_BASE_URL = "https://portobreak.com"
PRIVATE_ROBOTS = "noindex, nofollow, noarchive, nosnippet"
PUBLIC_ROBOTS = "index, follow, max-image-preview:large"
PUBLIC_PATHS = {
    "booking_portal.index": "/reservas",
    "booking_portal.detail": "/reservas/{al_id}",
    "booking_portal.cancellation_policy": "/reservas/politica-cancelamento",
    "booking_portal.terms": "/reservas/termos-condicoes",
    "booking_portal.privacy": "/reservas/politica-privacidade",
    "booking_portal.cookies": "/reservas/politica-cookies",
    "booking_portal.legal": "/reservas/informacao-legal",
}
LOCALES = {"pt": "pt_PT", "en": "en_GB", "es": "es_ES", "fr": "fr_FR"}
SEARCH_KEYS = {"checkin", "checkout", "adultos", "criancas", "bebes", "hospedes", "q", "query"}
COPY = {
    "pt": {
        "catalog": "Alojamentos no Porto", "page": "Página", "private": "Área reservada",
        "description": "Descubra os alojamentos PortoBreak no Porto. Veja fotografias, consulte a disponibilidade e reserve a sua estadia diretamente no nosso portal.",
        "property": "Conheça {name}{location}{capacity}. Consulte fotografias, disponibilidade e condições de reserva no PortoBreak.",
        "location": ", em {location}", "capacity": ", para até {capacity} hóspedes",
    },
    "en": {
        "catalog": "Places to stay in Porto", "page": "Page", "private": "Private area",
        "description": "Discover PortoBreak accommodation in Porto. Browse photos, check availability and book your stay directly through our booking portal.",
        "property": "Explore {name}{location}{capacity}. View photos, availability and booking conditions with PortoBreak.",
        "location": " in {location}", "capacity": ", for up to {capacity} guests",
    },
    "es": {
        "catalog": "Alojamientos en Oporto", "page": "Página", "private": "Área privada",
        "description": "Descubra los alojamientos PortoBreak en Oporto. Vea fotografías, consulte la disponibilidad y reserve su estancia directamente en nuestro portal.",
        "property": "Descubra {name}{location}{capacity}. Consulte fotografías, disponibilidad y condiciones de reserva en PortoBreak.",
        "location": ", en {location}", "capacity": ", para hasta {capacity} huéspedes",
    },
    "fr": {
        "catalog": "Hébergements à Porto", "page": "Page", "private": "Espace privé",
        "description": "Découvrez les hébergements PortoBreak à Porto. Consultez les photos et les disponibilités, puis réservez votre séjour directement sur notre portail.",
        "property": "Découvrez {name}{location}{capacity}. Consultez les photos, les disponibilités et les conditions de réservation sur PortoBreak.",
        "location": ", à {location}", "capacity": ", pour jusqu’à {capacity} personnes",
    },
}


def _language(lang):
    return lang if lang in SUPPORTED_LANGS else "pt"


def _text(value, limit=180):
    """Plain public text only, independently escaped at the presentation boundary."""
    value = re.sub(r"<[^>]*>", " ", html.unescape(str(value or "")))
    value = re.sub(r"[\s\x00-\x1f\x7f]+", " ", value).strip()
    if len(value) > limit:
        value = value[:limit - 1].rsplit(" ", 1)[0].rstrip(".,;:") + "…"
    return value


def public_base_url():
    """Configured canonical origin, never inferred from an incoming Host header."""
    configured = current_app.config.get("PORTOBREAK_PUBLIC_BASE_URL")
    value = str(configured or os.environ.get("PORTOBREAK_PUBLIC_BASE_URL") or DEFAULT_PUBLIC_BASE_URL).strip()
    try:
        parsed = urlsplit(value)
        hostname = parsed.hostname or ""
        parsed.port  # Validate malformed or out-of-range ports.
        valid = (
            parsed.scheme in {"http", "https"} and hostname
            and not parsed.username and not parsed.password and "@" not in parsed.netloc
            and not parsed.query and not parsed.fragment
            and not re.search(r"[\s\\\x00-\x1f\x7f]", value)
            and all(part not in {".", ".."} for part in parsed.path.split("/"))
            and "//" not in parsed.path
        )
        if valid:
            return f"{parsed.scheme.lower()}://{parsed.netloc.lower()}{parsed.path.rstrip('/')}"
    except (TypeError, ValueError):
        pass
    return DEFAULT_PUBLIC_BASE_URL


def public_url(endpoint, lang=None, **values):
    """Only public route parameters survive into canonical or sitemap URLs."""
    if endpoint in PUBLIC_PATHS:
        path = PUBLIC_PATHS[endpoint]
        if endpoint == "booking_portal.detail":
            identifier = str(values.get("al_id") or "").strip()
            if not identifier:
                raise ValueError("A public property URL requires al_id")
            path = path.format(al_id=quote(identifier, safe=""))
    elif endpoint in {"booking_portal.sitemap", "booking_portal.robots"}:
        # Discovery endpoints only; never copy a private path or request query.
        path = url_for(endpoint, _external=False).split("?", 1)[0]
    else:
        raise ValueError("Only public discovery endpoints have public SEO URLs")
    query = {}
    if lang is not None:
        query["lang"] = _language(lang)
    if endpoint == "booking_portal.index":
        try:
            page = int(values.get("page") or 1)
        except (TypeError, ValueError):
            page = 1
        if page > 1:
            query["page"] = page
    return public_base_url() + path + ("?" + urlencode(query) if query else "")


def is_public_origin():
    configured_host = urlsplit(public_base_url()).hostname or ""
    # Match the application's reverse-proxy routing convention, but only against
    # the configured public domain; forwarded headers never build public URLs.
    effective_host = (request.headers.get("X-Forwarded-Host") or request.host).split(",", 1)[0].strip()
    try:
        parsed = urlsplit("//" + effective_host)
        host = (parsed.hostname or "").lower()
        if parsed.path or parsed.query or parsed.fragment or parsed.username or parsed.password:
            return False
        parsed.port
        if host == "localhost" or host.endswith(".localhost"):
            return False
        try:
            if ipaddress.ip_address(host).is_private or ipaddress.ip_address(host).is_loopback:
                return False
        except ValueError:
            pass
    except ValueError:
        return False
    base_host = configured_host.removeprefix("www.")
    return host in {base_host, "www." + base_host}


def robots_directive(endpoint=None, *, filtered=False):
    endpoint = endpoint or request.endpoint
    if endpoint not in PUBLIC_ENDPOINTS:
        return PRIVATE_ROBOTS
    if filtered or not is_public_origin():
        return "noindex, follow"
    return PUBLIC_ROBOTS


def _public_image(value):
    """Only an existing public property image, never arbitrary or signed URLs."""
    image = str(value or "").strip()
    base = public_base_url()
    fallback = base + "/static/images/booking_portal/portobreak-logo-current.png"
    if image.startswith("/static/"):
        image = base + image
    try:
        parsed = urlsplit(image)
        configured_host = (urlsplit(base).hostname or "").removeprefix("www.")
        public_static_paths = {"/static/", urlsplit(base).path.rstrip("/") + "/static/"}
        if (
            parsed.scheme == "https" and parsed.hostname in {configured_host, "www." + configured_host, "szeroapp.com", "www.szeroapp.com"}
            and not parsed.username and not parsed.password and not parsed.query and not parsed.fragment
            and any(parsed.path.startswith(path) for path in public_static_paths)
            and not re.search(r"[\s\\\x00-\x1f\x7f]", image)
        ):
            return image
    except ValueError:
        pass
    return fallback


def build_booking_seo(lang, context):
    """Allowlist public facts instead of serializing a template/booking context."""
    lang = _language(lang)
    copy = COPY[lang]
    endpoint = request.endpoint
    if endpoint not in PUBLIC_ENDPOINTS:
        return {
            "title": f"{copy['private']} | PortoBreak", "robots": PRIVATE_ROBOTS,
            "description": "", "canonical": "", "alternates": [], "jsonld": [],
            "image": "", "image_alt": "", "locale": "", "locale_alternates": [],
        }

    values = {}
    filtered = endpoint == "booking_portal.index" and (
        bool((context.get("search") or {}).get("has_search"))
        or any(str(request.args.get(key) or "").strip() for key in SEARCH_KEYS)
    )
    property_data = context.get("alojamento") or {}
    if endpoint == "booking_portal.detail":
        values["al_id"] = (request.view_args or {}).get("al_id") or property_data.get("id")
        name = _text(property_data.get("nome"), 100) or copy["catalog"]
        title = name if re.search(r"\bporto\s*break\b", name, re.IGNORECASE) else f"{name} | PortoBreak"
        location = _text(property_data.get("localizacao"), 60)
        try:
            capacity = max(0, int(property_data.get("capacidade") or 0))
        except (TypeError, ValueError):
            capacity = 0
        description = _text(copy["property"].format(
            name=name,
            location=copy["location"].format(location=location) if location else "",
            capacity=copy["capacity"].format(capacity=capacity) if capacity else "",
        ))
    elif endpoint == "booking_portal.index":
        page = 1
        if not filtered:
            try:
                page = max(1, int((context.get("pagination") or {}).get("page") or request.args.get("page") or 1))
            except (TypeError, ValueError):
                pass
        values["page"] = page
        title = copy["catalog"] + (f" — {copy['page']} {page}" if page > 1 else "") + " | PortoBreak"
        description = copy["description"]
    else:
        document = context.get("legal_document") or context.get("policy") or {}
        heading = _text(document.get("title") or document.get("page_title") or context.get("page_title"), 120)
        title = f"{heading} | PortoBreak" if heading else "PortoBreak"
        description = _text(document.get("lead") or document.get("page_lead") or copy["description"])

    canonical = public_url(endpoint, lang, **values)
    image = _public_image(property_data.get("foto_principal") if endpoint == "booking_portal.detail" else "")
    graph = [{
        "@context": "https://schema.org", "@type": "WebPage",
        "@id": canonical + "#webpage", "url": canonical, "name": title,
        "description": description, "inLanguage": lang,
        "isPartOf": {"@type": "WebSite", "name": "PortoBreak", "url": public_url("booking_portal.index", lang)},
    }]
    if endpoint != "booking_portal.index":
        graph.append({
            "@context": "https://schema.org", "@type": "BreadcrumbList",
            "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": copy["catalog"], "item": public_url("booking_portal.index", lang)},
                {"@type": "ListItem", "position": 2, "name": title.removesuffix(" | PortoBreak"), "item": canonical},
            ],
        })
    if endpoint == "booking_portal.detail":
        accommodation = {
            "@context": "https://schema.org", "@type": "Accommodation",
            "@id": canonical + "#accommodation", "name": name, "url": canonical,
            "description": description, "image": image,
        }
        if capacity:
            accommodation["occupancy"] = {"@type": "QuantitativeValue", "maxValue": capacity}
        graph.append(accommodation)
        graph[0]["mainEntity"] = {"@id": canonical + "#accommodation"}

    return {
        "title": title, "description": description, "robots": robots_directive(endpoint, filtered=filtered),
        "canonical": canonical,
        "alternates": [{"lang": code, "url": public_url(endpoint, code, **values)} for code in SUPPORTED_LANGS]
            + [{"lang": "x-default", "url": public_url(endpoint, "pt", **values)}],
        "locale": LOCALES[lang], "locale_alternates": [LOCALES[code] for code in SUPPORTED_LANGS if code != lang],
        "image": image, "image_alt": _text(property_data.get("nome"), 100) if endpoint == "booking_portal.detail" else "PortoBreak",
        "jsonld": graph,
    }
