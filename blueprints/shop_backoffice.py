from flask import Blueprint, jsonify, render_template, request
from flask_login import current_user, login_required

from models import Acessos
from services.shop_backoffice_service import (
    ShopNotFoundError,
    ShopServiceError,
    ShopValidationError,
    auto_translate_product,
    delete_product_image,
    get_order_detail,
    get_product_detail,
    get_shop_meta,
    list_families,
    list_orders,
    list_products,
    save_family,
    save_product,
    update_product_image,
    upload_product_image,
)


bp = Blueprint("shop_backoffice", __name__)


def _has_acl(table_name, action="consultar"):
    if getattr(current_user, "ADMIN", False):
        return True
    acesso = (
        Acessos.query.filter_by(utilizador=current_user.LOGIN, tabela=table_name).first()
    )
    return bool(acesso and getattr(acesso, action, False))


def _can_catalog(action="consultar"):
    return any(
        _has_acl(name, action)
        for name in ("SHOP", "SHOP_PRODUTOS", "SHOP_FAMILIAS")
    )


def _can_orders(action="consultar"):
    return any(
        _has_acl(name, action)
        for name in ("SHOP", "SHOP_ENCOMENDAS", "SHOP_PAGAMENTOS")
    )


def _forbidden():
    return jsonify({"error": "Sem permissao para aceder ao modulo SHOP."}), 403


def _handle_service_error(exc):
    if isinstance(exc, ShopValidationError):
        return jsonify({"error": str(exc)}), 400
    if isinstance(exc, ShopNotFoundError):
        return jsonify({"error": str(exc)}), 404
    return jsonify({"error": str(exc)}), 500


@bp.route("/shop/artigos")
@bp.route("/shop_artigos")
@login_required
def shop_articles_page():
    if not _can_catalog("consultar"):
        return ("Sem permissao para consultar o catalogo SHOP.", 403)
    return render_template("shop_artigos.html", page_title="Shop - Artigos", page_name="Shop - Artigos")


@bp.route("/shop/encomendas")
@bp.route("/shop_encomendas")
@login_required
def shop_orders_page():
    if not _can_orders("consultar"):
        return ("Sem permissao para consultar encomendas SHOP.", 403)
    return render_template("shop_encomendas.html", page_title="Shop - Encomendas", page_name="Shop - Encomendas")


@bp.route("/api/shop/meta", methods=["GET"])
@login_required
def api_shop_meta():
    if not (_can_catalog("consultar") or _can_orders("consultar")):
        return _forbidden()
    try:
        return jsonify({"ok": True, "meta": get_shop_meta()})
    except ShopServiceError as exc:
        return _handle_service_error(exc)


@bp.route("/api/shop/familias", methods=["GET", "POST"])
@login_required
def api_shop_families():
    if request.method == "GET":
        if not _can_catalog("consultar"):
            return _forbidden()
        try:
            return jsonify({"ok": True, "items": list_families()})
        except ShopServiceError as exc:
            return _handle_service_error(exc)

    if not _can_catalog("editar") and not _can_catalog("inserir"):
        return _forbidden()
    try:
        payload = request.get_json(silent=True) or {}
        family = save_family(payload)
        return jsonify({"ok": True, "item": family})
    except ShopServiceError as exc:
        return _handle_service_error(exc)


@bp.route("/api/shop/familias/<int:family_id>", methods=["PUT"])
@login_required
def api_shop_family_update(family_id):
    if not _can_catalog("editar"):
        return _forbidden()
    try:
        payload = request.get_json(silent=True) or {}
        family = save_family(payload, family_id=family_id)
        return jsonify({"ok": True, "item": family})
    except ShopServiceError as exc:
        return _handle_service_error(exc)


@bp.route("/api/shop/artigos", methods=["GET", "POST"])
@login_required
def api_shop_products():
    if request.method == "GET":
        if not _can_catalog("consultar"):
            return _forbidden()
        try:
            data = list_products(request.args)
            return jsonify({"ok": True, **data})
        except ShopServiceError as exc:
            return _handle_service_error(exc)

    if not (_can_catalog("inserir") or _can_catalog("editar")):
        return _forbidden()
    try:
        payload = request.get_json(silent=True) or {}
        product = save_product(payload)
        return jsonify({"ok": True, **product})
    except ShopServiceError as exc:
        return _handle_service_error(exc)


@bp.route("/api/shop/artigos/traducoes/auto", methods=["POST"])
@login_required
def api_shop_product_auto_translate():
    if not (_can_catalog("inserir") or _can_catalog("editar")):
        return _forbidden()
    try:
        payload = request.get_json(silent=True) or {}
        return jsonify({"ok": True, "translations": auto_translate_product(payload)})
    except ShopServiceError as exc:
        return _handle_service_error(exc)


@bp.route("/api/shop/artigos/<int:product_id>", methods=["GET", "PUT"])
@login_required
def api_shop_product_detail(product_id):
    if request.method == "GET":
        if not _can_catalog("consultar"):
            return _forbidden()
        try:
            return jsonify({"ok": True, **get_product_detail(product_id)})
        except ShopServiceError as exc:
            return _handle_service_error(exc)

    if not _can_catalog("editar"):
        return _forbidden()
    try:
        payload = request.get_json(silent=True) or {}
        return jsonify({"ok": True, **save_product(payload, product_id=product_id)})
    except ShopServiceError as exc:
        return _handle_service_error(exc)


@bp.route("/api/shop/artigos/<int:product_id>/imagens", methods=["POST"])
@login_required
def api_shop_product_image_upload(product_id):
    if not _can_catalog("editar"):
        return _forbidden()
    try:
        detail = upload_product_image(
            product_id,
            request.files.get("file"),
            alt_text=request.form.get("alt_text"),
        )
        return jsonify({"ok": True, **detail})
    except ShopServiceError as exc:
        return _handle_service_error(exc)


@bp.route("/api/shop/artigos/<int:product_id>/imagens/<int:image_id>", methods=["PUT", "DELETE"])
@login_required
def api_shop_product_image_detail(product_id, image_id):
    if not _can_catalog("editar"):
        return _forbidden()
    try:
        if request.method == "DELETE":
            detail = delete_product_image(product_id, image_id)
        else:
            payload = request.get_json(silent=True) or {}
            detail = update_product_image(product_id, image_id, payload)
        return jsonify({"ok": True, **detail})
    except ShopServiceError as exc:
        return _handle_service_error(exc)


@bp.route("/api/shop/encomendas", methods=["GET"])
@login_required
def api_shop_orders():
    if not _can_orders("consultar"):
        return _forbidden()
    try:
        data = list_orders(request.args)
        return jsonify({"ok": True, **data})
    except ShopServiceError as exc:
        return _handle_service_error(exc)


@bp.route("/api/shop/encomendas/<int:order_id>", methods=["GET"])
@login_required
def api_shop_order_detail(order_id):
    if not _can_orders("consultar"):
        return _forbidden()
    try:
        return jsonify({"ok": True, **get_order_detail(order_id)})
    except ShopServiceError as exc:
        return _handle_service_error(exc)
