(function () {
  const INITIAL_PAGE = window.R_PUBLIC_SHOP || {};
  const PUBLIC_TOKEN = String(INITIAL_PAGE.token || "").trim();
  const LANG_KEY = "r_public_lang";
  const LOCALES = { pt: "pt-PT", en: "en-GB", fr: "fr-FR", es: "es-ES" };
  const FLAG_META = {
    pt: { flagClass: "fi fi-pt", code: "PT" },
    en: { flagClass: "fi fi-gb", code: "EN" },
    fr: { flagClass: "fi fi-fr", code: "FR" },
    es: { flagClass: "fi fi-es", code: "ES" },
  };
  const I18N = {
    pt: {
      btn_back: "Voltar",
      hero_kicker: "Shop da estadia",
      hero_title: "Encomendas durante a estadia",
      hero_subtitle: "Escolhe entrega gratuita ou express e recebe os artigos no momento certo da tua reserva.",
      label_reservation: "Reserva",
      label_checkin: "Check-in",
      loading: "A carregar loja...",
      state_open_title: "Compra disponivel",
      state_closed_title: "Janela de compra encerrada",
      state_open_text: "Podes adicionar itens ate {deadline}.",
      state_closed_text: "As encomendas para esta reserva encerraram em {deadline}.",
      family_items: "{count} artigos",
      cart_bar_summary: "{count} itens · {total}",
      cart_view: "Ver carrinho",
      product_add: "Adicionar ao carrinho",
      product_open: "Ver detalhe",
      product_increase: "Aumentar quantidade",
      product_decrease: "Diminuir quantidade",
      product_remove: "Remover do carrinho",
      product_variants: "Variantes",
      cart_title: "Carrinho",
      cart_total: "Total",
      delivery_title: "Entrega",
      delivery_sheet_title: "Escolhe a entrega",
      delivery_sheet_hint: "Seleciona como queres receber a encomenda antes de seguir para o checkout.",
      delivery_total: "Total com entrega",
      delivery_continue_checkout: "Continuar para checkout",
      delivery_option_free: "Entrega gratuita",
      delivery_option_express: "Entrega express",
      delivery_window_before_checkin: "Colocamos tudo no alojamento antes do check-in.",
      delivery_window_next_morning: "Entregamos no dia seguinte de manha com a nossa chave.",
      delivery_window_scheduled_1h: "Entrega entre {start} e {end}.",
      delivery_presence_required: "Tens de estar no alojamento para receber o estafeta.",
      delivery_presence_not_required: "Nao precisas de estar no alojamento.",
      delivery_unavailable: "Neste momento nao existe nenhuma modalidade de entrega disponivel.",
      cart_empty_title: "Ainda nao adicionaste nada",
      cart_empty_text: "Explora os artigos e adiciona o que precisares para a tua estadia.",
      checkout_cta: "Avancar para checkout",
      checkout_pending: "Nao foi possivel iniciar o checkout Stripe.",
      checkout_redirecting: "A redirecionar para o checkout Stripe...",
      checkout_pending_confirmation: "A confirmar o pagamento...",
      checkout_success: "Pagamento confirmado com sucesso.",
      checkout_cancelled: "Checkout cancelado. O carrinho continua disponivel.",
      added_to_cart: "Adicionado ao carrinho.",
      unavailable_cta: "Fora da janela de compra",
      error_loading: "Nao foi possivel carregar a loja neste momento.",
      retry: "Tentar novamente",
      close: "Fechar",
      line_qty: "Qtd.",
      cart_items_count: "{count} itens",
      empty_price: "0,00 EUR",
    },
    en: {
      btn_back: "Back",
      hero_kicker: "Stay shop",
      hero_title: "Orders during your stay",
      hero_subtitle: "Choose free or express delivery and receive your items at the right moment of your reservation.",
      label_reservation: "Reservation",
      label_checkin: "Check-in",
      loading: "Loading shop...",
      state_open_title: "Ordering available",
      state_closed_title: "Ordering window closed",
      state_open_text: "You can add items until {deadline}.",
      state_closed_text: "Orders for this reservation closed on {deadline}.",
      family_items: "{count} items",
      cart_bar_summary: "{count} items · {total}",
      cart_view: "View cart",
      product_add: "Add to cart",
      product_open: "View details",
      product_increase: "Increase quantity",
      product_decrease: "Decrease quantity",
      product_remove: "Remove from cart",
      product_variants: "Variants",
      cart_title: "Cart",
      cart_total: "Total",
      delivery_title: "Delivery",
      delivery_sheet_title: "Choose delivery",
      delivery_sheet_hint: "Select how you want to receive the order before continuing to checkout.",
      delivery_total: "Total with delivery",
      delivery_continue_checkout: "Continue to checkout",
      delivery_option_free: "Free delivery",
      delivery_option_express: "Express delivery",
      delivery_window_before_checkin: "We place everything in the property before check-in.",
      delivery_window_next_morning: "We deliver the next morning using our own key.",
      delivery_window_scheduled_1h: "Delivery between {start} and {end}.",
      delivery_presence_required: "You need to be at the property to receive the courier.",
      delivery_presence_not_required: "You do not need to be at the property.",
      delivery_unavailable: "There is no delivery method available right now.",
      cart_empty_title: "You have not added anything yet",
      cart_empty_text: "Browse the items and add whatever you need for your stay.",
      checkout_cta: "Continue to checkout",
      checkout_pending: "Could not start Stripe checkout.",
      checkout_redirecting: "Redirecting to Stripe checkout...",
      checkout_pending_confirmation: "Confirming payment...",
      checkout_success: "Payment confirmed successfully.",
      checkout_cancelled: "Checkout cancelled. Your cart is still available.",
      added_to_cart: "Added to cart.",
      unavailable_cta: "Ordering window closed",
      error_loading: "The shop could not be loaded right now.",
      retry: "Try again",
      close: "Close",
      line_qty: "Qty.",
      cart_items_count: "{count} items",
      empty_price: "EUR 0.00",
    },
    fr: {
      btn_back: "Retour",
      hero_kicker: "Boutique du sejour",
      hero_title: "Commandes pendant le sejour",
      hero_subtitle: "Choisissez la livraison gratuite ou express et recevez vos articles au bon moment de votre reservation.",
      label_reservation: "Reservation",
      label_checkin: "Check-in",
      loading: "Chargement de la boutique...",
      state_open_title: "Commande disponible",
      state_closed_title: "Fenetre de commande fermee",
      state_open_text: "Vous pouvez ajouter des articles jusqu au {deadline}.",
      state_closed_text: "Les commandes pour cette reservation ont ferme le {deadline}.",
      family_items: "{count} articles",
      cart_bar_summary: "{count} articles · {total}",
      cart_view: "Voir le panier",
      product_add: "Ajouter au panier",
      product_open: "Voir le detail",
      product_increase: "Augmenter la quantite",
      product_decrease: "Diminuer la quantite",
      product_remove: "Retirer du panier",
      product_variants: "Variantes",
      cart_title: "Panier",
      cart_total: "Total",
      delivery_title: "Livraison",
      delivery_sheet_title: "Choisissez la livraison",
      delivery_sheet_hint: "Selectionnez comment vous souhaitez recevoir la commande avant de passer au paiement.",
      delivery_total: "Total avec livraison",
      delivery_continue_checkout: "Continuer vers le paiement",
      delivery_option_free: "Livraison gratuite",
      delivery_option_express: "Livraison express",
      delivery_window_before_checkin: "Nous deposons tout dans le logement avant le check-in.",
      delivery_window_next_morning: "Nous livrons le lendemain matin avec notre propre cle.",
      delivery_window_scheduled_1h: "Livraison entre {start} et {end}.",
      delivery_presence_required: "Vous devez etre sur place pour recevoir le coursier.",
      delivery_presence_not_required: "Vous n avez pas besoin d etre sur place.",
      delivery_unavailable: "Aucun mode de livraison n est disponible pour le moment.",
      cart_empty_title: "Vous n avez encore rien ajoute",
      cart_empty_text: "Parcourez les articles et ajoutez ce dont vous avez besoin pour votre sejour.",
      checkout_cta: "Continuer vers le paiement",
      checkout_pending: "Impossible de lancer le paiement Stripe.",
      checkout_redirecting: "Redirection vers le paiement Stripe...",
      checkout_pending_confirmation: "Confirmation du paiement...",
      checkout_success: "Paiement confirme avec succes.",
      checkout_cancelled: "Paiement annule. Votre panier reste disponible.",
      added_to_cart: "Ajoute au panier.",
      unavailable_cta: "Hors delai de commande",
      error_loading: "Impossible de charger la boutique pour le moment.",
      retry: "Reessayer",
      close: "Fermer",
      line_qty: "Qt.",
      cart_items_count: "{count} articles",
      empty_price: "0,00 EUR",
    },
    es: {
      btn_back: "Volver",
      hero_kicker: "Tienda de la estancia",
      hero_title: "Pedidos durante la estancia",
      hero_subtitle: "Elige entrega gratuita o express y recibe tus articulos en el momento adecuado de tu reserva.",
      label_reservation: "Reserva",
      label_checkin: "Check-in",
      loading: "Cargando tienda...",
      state_open_title: "Compra disponible",
      state_closed_title: "Ventana de compra cerrada",
      state_open_text: "Puedes anadir articulos hasta {deadline}.",
      state_closed_text: "Los pedidos para esta reserva cerraron el {deadline}.",
      family_items: "{count} articulos",
      cart_bar_summary: "{count} articulos · {total}",
      cart_view: "Ver carrito",
      product_add: "Anadir al carrito",
      product_open: "Ver detalle",
      product_increase: "Aumentar cantidad",
      product_decrease: "Reducir cantidad",
      product_remove: "Quitar del carrito",
      product_variants: "Variantes",
      cart_title: "Carrito",
      cart_total: "Total",
      delivery_title: "Entrega",
      delivery_sheet_title: "Elige la entrega",
      delivery_sheet_hint: "Selecciona como quieres recibir el pedido antes de continuar al checkout.",
      delivery_total: "Total con entrega",
      delivery_continue_checkout: "Continuar al checkout",
      delivery_option_free: "Entrega gratuita",
      delivery_option_express: "Entrega express",
      delivery_window_before_checkin: "Dejamos todo en el alojamiento antes del check-in.",
      delivery_window_next_morning: "Entregamos a la manana siguiente con nuestra llave.",
      delivery_window_scheduled_1h: "Entrega entre {start} y {end}.",
      delivery_presence_required: "Tienes que estar en el alojamiento para recibir al mensajero.",
      delivery_presence_not_required: "No necesitas estar en el alojamiento.",
      delivery_unavailable: "Ahora mismo no hay ninguna modalidad de entrega disponible.",
      cart_empty_title: "Todavia no has anadido nada",
      cart_empty_text: "Explora los articulos y anade lo que necesites para tu estancia.",
      checkout_cta: "Avanzar al pago",
      checkout_pending: "No se pudo iniciar el checkout de Stripe.",
      checkout_redirecting: "Redirigiendo al checkout de Stripe...",
      checkout_pending_confirmation: "Confirmando pago...",
      checkout_success: "Pago confirmado correctamente.",
      checkout_cancelled: "Checkout cancelado. Tu carrito sigue disponible.",
      added_to_cart: "Anadido al carrito.",
      unavailable_cta: "Fuera de plazo de compra",
      error_loading: "No se pudo cargar la tienda ahora mismo.",
      retry: "Reintentar",
      close: "Cerrar",
      line_qty: "Cant.",
      cart_items_count: "{count} articulos",
      empty_price: "0,00 EUR",
    },
  };

  const els = {
    topbarShell: document.querySelector(".shop-topbar-shell"),
    topbar: document.querySelector(".shop-topbar"),
    langMenuBtn: document.getElementById("langMenuBtn"),
    langMenuList: document.getElementById("langMenuList"),
    langMenuFlag: document.getElementById("langMenuFlag"),
    langMenuCode: document.getElementById("langMenuCode"),
    langOptions: Array.from(document.querySelectorAll(".shop-lang-option[data-lang]")),
    stateBanner: document.getElementById("shopStateBanner"),
    stateTitle: document.getElementById("shopStateTitle"),
    stateText: document.getElementById("shopStateText"),
    familyBar: document.getElementById("shopFamilyBar"),
    familyTabs: document.getElementById("shopFamilyTabs"),
    loading: document.getElementById("shopLoading"),
    error: document.getElementById("shopError"),
    sections: document.getElementById("shopSections"),
    cartBar: document.getElementById("cartBar"),
    cartBarSummary: document.getElementById("cartBarSummary"),
    productSheet: document.getElementById("productSheet"),
    productHero: document.getElementById("productHero"),
    productHeroIcon: document.getElementById("productHeroIcon"),
    productFamily: document.getElementById("productFamily"),
    productTitle: document.getElementById("productTitle"),
    productPrice: document.getElementById("productPrice"),
    productSubtitle: document.getElementById("productSubtitle"),
    productDescription: document.getElementById("productDescription"),
    productVariantsBlock: document.getElementById("productVariantsBlock"),
    productVariants: document.getElementById("productVariants"),
    productQtyMinus: document.getElementById("productQtyMinus"),
    productQtyPlus: document.getElementById("productQtyPlus"),
    productQtyValue: document.getElementById("productQtyValue"),
    productAddBtn: document.getElementById("productAddBtn"),
    cartSheet: document.getElementById("cartSheet"),
    cartEmpty: document.getElementById("cartEmpty"),
    cartItems: document.getElementById("cartItems"),
    cartTitleSummary: document.getElementById("cartTitleSummary"),
    cartTotalValue: document.getElementById("cartTotalValue"),
    checkoutBtn: document.getElementById("checkoutBtn"),
    checkoutMsg: document.getElementById("checkoutMsg"),
    deliverySheet: document.getElementById("deliverySheet"),
    deliveryOptions: document.getElementById("deliveryOptions"),
    deliveryTotalValue: document.getElementById("deliveryTotalValue"),
    deliveryConfirmBtn: document.getElementById("deliveryConfirmBtn"),
    deliveryMsg: document.getElementById("deliveryMsg"),
  };

  const state = {
    reservation: null,
    shopState: {
      is_available: !!INITIAL_PAGE.shop_available,
      message: String(INITIAL_PAGE.shop_message || "").trim(),
      deadline_label: String(INITIAL_PAGE.shop_deadline_label || "").trim(),
    },
    families: [],
    products: [],
    productsByCode: {},
    cart: { items: [], items_count: 0, total_quantity: 0, total: 0, currency: "EUR" },
    activeFamily: "",
    currentProduct: null,
    currentVariantId: null,
    currentQuantity: 1,
    selectedDeliveryMethod: "",
    loading: true,
    error: "",
    observer: null,
    programmaticScrollUntil: 0,
    pendingProducts: {},
    cartFeedbackTimer: 0,
  };

  function currentLang() {
    const lang = String(localStorage.getItem(LANG_KEY) || "pt").toLowerCase();
    return I18N[lang] ? lang : "pt";
  }

  function t(key, vars) {
    const dict = I18N[currentLang()] || I18N.pt;
    let text = dict[key] || I18N.pt[key] || key;
    const values = vars || {};
    Object.keys(values).forEach((token) => {
      text = text.replace(new RegExp(`\\{${token}\\}`, "g"), String(values[token]));
    });
    return text;
  }

  function formatCurrency(value, currency) {
    try {
      return new Intl.NumberFormat(LOCALES[currentLang()] || "pt-PT", {
        style: "currency",
        currency: currency || "EUR",
      }).format(Number(value || 0));
    } catch (_) {
      const amount = Number(value || 0).toFixed(2).replace(".", ",");
      return `${amount} ${(currency || "EUR").toUpperCase()}`;
    }
  }

  function escapeHtml(value) {
    return String(value || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function localizedProductField(entity, field) {
    const lang = currentLang();
    const translations = entity && typeof entity === "object" ? (entity.translations || {}) : {};
    const langValue = translations[lang] && translations[lang][field];
    if (langValue) return String(langValue);
    const ptValue = translations.pt && translations.pt[field];
    if (ptValue) return String(ptValue);
    const fallbackMap = {
      name: entity?.name,
      title: entity?.title,
      subtitle: entity?.subtitle,
      description_short: entity?.description_short,
      description: entity?.description,
    };
    return String(fallbackMap[field] || "");
  }

  function accentStyle(accent) {
    const safe = String(accent || "#2563eb");
    return `background: linear-gradient(135deg, ${safe}, rgba(14,165,233,0.86));`;
  }

  function deliveryOptions() {
    return Array.isArray(state.shopState?.delivery_options) ? state.shopState.delivery_options : [];
  }

  function selectedDeliveryOption() {
    const wanted = String(state.selectedDeliveryMethod || "").trim().toUpperCase();
    const options = deliveryOptions();
    return options.find((item) => String(item.code || "").trim().toUpperCase() === wanted) || null;
  }

  function ensureDeliverySelection() {
    const options = deliveryOptions();
    const current = selectedDeliveryOption();
    if (current) return current;
    const fallback = options.find((item) => item.is_default) || options[0] || null;
    state.selectedDeliveryMethod = fallback ? String(fallback.code || "").trim().toUpperCase() : "";
    return fallback;
  }

  function deliveryOptionLabel(option) {
    const code = String(option?.code || "").trim().toUpperCase();
    if (code === "EXPRESS") return t("delivery_option_express");
    if (code === "FREE") return t("delivery_option_free");
    return code;
  }

  function deliveryOptionWindow(option) {
    const windowCode = String(option?.window_code || "").trim().toLowerCase();
    if (windowCode === "before_checkin") return t("delivery_window_before_checkin");
    if (windowCode === "next_morning") return t("delivery_window_next_morning");
    if (windowCode === "scheduled_1h") {
      const start = formatDeliveryPoint(option?.window_start, false);
      const end = formatDeliveryPoint(option?.window_end, true);
      return t("delivery_window_scheduled_1h", { start, end });
    }
    return "";
  }

  function deliveryOptionPresence(option) {
    return option?.requires_presence ? t("delivery_presence_required") : t("delivery_presence_not_required");
  }

  function cartGrandTotal() {
    const deliveryFee = Number(selectedDeliveryOption()?.price || 0);
    return Number(state.cart?.total || 0) + deliveryFee;
  }

  function formatDeliveryPoint(value, timeOnlyWhenSameDay) {
    const raw = String(value || "").trim();
    if (!raw) return "";
    const dateObj = new Date(raw);
    if (Number.isNaN(dateObj.getTime())) return raw;
    const locale = LOCALES[currentLang()] || "pt-PT";
    const options = timeOnlyWhenSameDay
      ? { hour: "2-digit", minute: "2-digit" }
      : { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" };
    return new Intl.DateTimeFormat(locale, options).format(dateObj);
  }

  function renderDeliverySheet() {
    const cart = state.cart || { items: [], total: 0, currency: "EUR" };
    const options = deliveryOptions();
    const deliveryOption = ensureDeliverySelection();
    if (els.deliveryOptions) {
      els.deliveryOptions.innerHTML = options.length
        ? options.map((option) => {
            const code = String(option.code || "").trim().toUpperCase();
            const checked = deliveryOption && code === String(deliveryOption.code || "").trim().toUpperCase();
            return `
              <label class="shop-delivery-option${checked ? " is-active" : ""}">
                <input type="radio" name="shopDeliveryMethod" value="${escapeHtml(code)}" ${checked ? "checked" : ""}>
                <div class="shop-delivery-option-copy">
                  <div class="shop-delivery-option-head">
                    <strong>${escapeHtml(deliveryOptionLabel(option))}</strong>
                    <span>${escapeHtml(formatCurrency(option.price || 0, cart.currency || "EUR"))}</span>
                  </div>
                  <div class="shop-delivery-option-text">${escapeHtml(deliveryOptionWindow(option))}</div>
                  <div class="shop-delivery-option-note">${escapeHtml(deliveryOptionPresence(option))}</div>
                </div>
              </label>
            `;
          }).join("")
        : `<div class="shop-delivery-empty">${escapeHtml(t("delivery_unavailable"))}</div>`;
    }
    if (els.deliveryTotalValue) {
      els.deliveryTotalValue.textContent = formatCurrency(cartGrandTotal(), cart.currency || "EUR");
    }
    if (els.deliveryConfirmBtn) {
      els.deliveryConfirmBtn.disabled = !deliveryOption || !state.shopState.is_available || !cart.items?.length;
    }
  }

  function renderProductThumb(product, extraClass) {
    const imageUrl = String((product && product.image_url) || "").trim();
    const classes = ["shop-product-thumb"];
    const altLabel = localizedProductField(product, "name") || localizedProductField(product, "title") || "";
    if (extraClass) classes.push(extraClass);
    if (imageUrl) {
      return `<div class="${classes.join(" ")} shop-product-thumb-image" style="${accentStyle(product.accent)}"><img src="${escapeHtml(imageUrl)}" alt="${escapeHtml(altLabel)}" loading="lazy"></div>`;
    }
    return `<div class="${classes.join(" ")}" style="${accentStyle(product.accent)}"><i class="fa-solid ${escapeHtml(product.icon)}"></i></div>`;
  }

  function productCodeKey(productCode) {
    return String(productCode || "").trim().toUpperCase();
  }

  function normalizeVariantId(variantId) {
    const num = Number(variantId || 0);
    return Number.isFinite(num) && num > 0 ? num : null;
  }

  function cartLineKey(productCode, variantId) {
    const code = productCodeKey(productCode);
    const normalizedVariantId = normalizeVariantId(variantId);
    return normalizedVariantId ? `${code}::${normalizedVariantId}` : code;
  }

  function defaultVariantFor(product) {
    const variants = Array.isArray(product?.variants) ? product.variants : [];
    if (!variants.length) return null;
    const wantedId = normalizeVariantId(product?.default_variant_id);
    if (wantedId) {
      const wanted = variants.find((item) => normalizeVariantId(item.id) === wantedId);
      if (wanted) return wanted;
    }
    return variants.find((item) => item.is_default) || variants[0] || null;
  }

  function variantForProduct(product, variantId) {
    const variants = Array.isArray(product?.variants) ? product.variants : [];
    const normalizedVariantId = normalizeVariantId(variantId);
    if (!variants.length) return null;
    if (normalizedVariantId) {
      const found = variants.find((item) => normalizeVariantId(item.id) === normalizedVariantId);
      if (found) return found;
    }
    return defaultVariantFor(product);
  }

  function effectivePrice(product, variantId) {
    const variant = variantForProduct(product, variantId);
    if (variant && variant.price !== null && variant.price !== undefined && variant.price !== "") {
      return Number(variant.price || 0);
    }
    return Number(product?.price || 0);
  }

  function cartItemFor(productCode, variantId) {
    const key = cartLineKey(productCode, variantId);
    return (state.cart.items || []).find((item) => String(item.key || cartLineKey(item.product_code, item.variant_id)) === key) || null;
  }

  function cartQuantityFor(productCode, variantId) {
    const item = cartItemFor(productCode, variantId);
    return item ? Number(item.quantity || 0) : 0;
  }

  function isProductPending(productCode, variantId) {
    return !!state.pendingProducts[cartLineKey(productCode, variantId)];
  }

  function listVariantForProduct(product) {
    return defaultVariantFor(product);
  }

  function updateStickyMetrics() {
    return els.familyBar ? Math.ceil(els.familyBar.getBoundingClientRect().height) : 0;
  }

  function currentStickyOffset() {
    return updateStickyMetrics() + 10;
  }

  function scrollToFamilySection(familyCode, behavior) {
    const section = document.querySelector(`[data-family-section="${familyCode}"]`);
    if (!section) return;
    const targetTop = Math.max(0, window.scrollY + section.getBoundingClientRect().top - currentStickyOffset());
    state.programmaticScrollUntil = Date.now() + 900;
    window.scrollTo({
      top: targetTop,
      behavior: behavior || "smooth",
    });
    window.setTimeout(() => {
      state.programmaticScrollUntil = 0;
    }, 950);
  }

  function renderProductQtyControlMarkup(product) {
    const code = productCodeKey(product?.code);
    const variant = listVariantForProduct(product);
    const variantId = normalizeVariantId(variant?.id);
    const quantity = cartQuantityFor(code, variantId);
    const expanded = quantity > 0;
    const pending = isProductPending(code, variantId);
    const leftIcon = quantity <= 1 ? "fa-trash-can" : "fa-minus";
    const leftLabel = quantity <= 1 ? t("product_remove") : t("product_decrease");
    return `
      <div class="shop-product-qty${expanded ? " is-expanded" : ""}${pending ? " is-pending" : ""}" data-product-qty="${escapeHtml(code)}" data-variant-id="${escapeHtml(variantId || "")}" data-qty="${quantity}">
        <button type="button" class="shop-product-qty-add" data-product-qty-add="${escapeHtml(code)}" data-variant-id="${escapeHtml(variantId || "")}" aria-label="${escapeHtml(t("product_add"))}" ${(!state.shopState.is_available || pending) ? "disabled" : ""}>
          <i class="fa-solid fa-plus"></i>
        </button>
        <div class="shop-product-qty-expanded">
          <button type="button" class="shop-product-qty-btn shop-product-qty-btn-left" data-product-qty-decrease="${escapeHtml(code)}" data-variant-id="${escapeHtml(variantId || "")}" aria-label="${escapeHtml(leftLabel)}" ${(!state.shopState.is_available || pending) ? "disabled" : ""}>
            <i class="fa-solid ${leftIcon}"></i>
          </button>
          <span class="shop-product-qty-value">${quantity}</span>
          <button type="button" class="shop-product-qty-btn" data-product-qty-increase="${escapeHtml(code)}" data-variant-id="${escapeHtml(variantId || "")}" aria-label="${escapeHtml(t("product_increase"))}" ${(!state.shopState.is_available || pending) ? "disabled" : ""}>
            <i class="fa-solid fa-plus"></i>
          </button>
        </div>
      </div>
    `;
  }

  function syncProductControls(productCode) {
    const controls = productCode
      ? Array.from(document.querySelectorAll(`[data-product-qty="${productCodeKey(productCode)}"]`))
      : Array.from(document.querySelectorAll("[data-product-qty]"));

    controls.forEach((control) => {
      const code = control.getAttribute("data-product-qty") || "";
      const variantId = normalizeVariantId(control.getAttribute("data-variant-id"));
      const quantity = cartQuantityFor(code, variantId);
      const pending = isProductPending(code, variantId);
      const expanded = quantity > 0;
      const leftIcon = quantity <= 1 ? "fa-trash-can" : "fa-minus";
      const leftLabel = quantity <= 1 ? t("product_remove") : t("product_decrease");
      control.classList.toggle("is-expanded", expanded);
      control.classList.toggle("is-pending", pending);
      control.setAttribute("data-qty", String(quantity));

      const addBtn = control.querySelector("[data-product-qty-add]");
      const decBtn = control.querySelector("[data-product-qty-decrease]");
      const incBtn = control.querySelector("[data-product-qty-increase]");
      const valueNode = control.querySelector(".shop-product-qty-value");
      const leftIconNode = decBtn ? decBtn.querySelector("i") : null;
      const shouldDisable = !state.shopState.is_available || pending;

      if (addBtn) addBtn.disabled = shouldDisable;
      if (decBtn) {
        decBtn.disabled = shouldDisable;
        decBtn.setAttribute("aria-label", leftLabel);
      }
      if (incBtn) incBtn.disabled = shouldDisable;
      if (valueNode) valueNode.textContent = String(quantity);
      if (leftIconNode) leftIconNode.className = `fa-solid ${leftIcon}`;
    });
  }

  function triggerCartFeedback() {
    if (!els.cartBar) return;
    els.cartBar.classList.remove("is-feedback");
    void els.cartBar.offsetWidth;
    els.cartBar.classList.remove("d-none");
    els.cartBar.classList.add("is-feedback");
    if (state.cartFeedbackTimer) window.clearTimeout(state.cartFeedbackTimer);
    state.cartFeedbackTimer = window.setTimeout(() => {
      els.cartBar.classList.remove("is-feedback");
      if (!state.cart.total_quantity) {
        els.cartBar.classList.add("d-none");
      }
      state.cartFeedbackTimer = 0;
    }, 320);
  }

  function applyLanguage(lang) {
    const active = I18N[lang] ? lang : "pt";
    localStorage.setItem(LANG_KEY, active);
    document.documentElement.lang = active;
    document.querySelectorAll("[data-i18n]").forEach((node) => {
      const key = node.getAttribute("data-i18n");
      if (key) node.textContent = t(key);
    });
    els.langOptions.forEach((btn) => btn.classList.toggle("active", btn.dataset.lang === active));
    const meta = FLAG_META[active] || FLAG_META.pt;
    if (els.langMenuFlag) els.langMenuFlag.className = meta.flagClass;
    if (els.langMenuCode) els.langMenuCode.textContent = meta.code;
    renderStateBanner();
    renderFamilies();
    renderSections();
    renderCart();
    renderCurrentProduct();
  }

  function renderStateBanner() {
    if (!els.stateBanner) return;
    els.stateBanner.classList.toggle("is-warning", !state.shopState.is_available);
    if (els.stateTitle) {
      els.stateTitle.textContent = state.shopState.is_available ? t("state_open_title") : t("state_closed_title");
    }
    if (els.stateText) {
      const deadline = state.shopState.deadline_label || "";
      els.stateText.textContent = state.shopState.message
        || (deadline
          ? t(state.shopState.is_available ? "state_open_text" : "state_closed_text", { deadline })
          : "");
    }
  }

  function renderFamilies() {
    if (!els.familyTabs) return;
    const existingTabs = Array.from(els.familyTabs.querySelectorAll("[data-family-tab]"));
    const sameStructure = existingTabs.length === state.families.length
      && existingTabs.every((tab, index) => tab.getAttribute("data-family-tab") === state.families[index].code);
    if (sameStructure) {
      updateFamilyActiveState();
      syncActiveFamilyTab("smooth");
      return;
    }
    els.familyTabs.innerHTML = state.families.map((family) => {
      const activeClass = family.code === state.activeFamily ? " is-active" : "";
      return `
        <button type="button" class="shop-family-tab${activeClass}" data-family-tab="${escapeHtml(family.code)}">
          <i class="fa-solid ${escapeHtml(family.icon)}"></i>
          <span>${escapeHtml(family.name)}</span>
        </button>
      `;
    }).join("");
    syncActiveFamilyTab("auto");
  }

  function updateFamilyActiveState() {
    if (!els.familyTabs) return;
    els.familyTabs.querySelectorAll("[data-family-tab]").forEach((tab) => {
      tab.classList.toggle("is-active", tab.getAttribute("data-family-tab") === state.activeFamily);
    });
  }

  function syncActiveFamilyTab(behavior) {
    if (!els.familyTabs || !state.activeFamily) return;
    const activeTab = els.familyTabs.querySelector(`[data-family-tab="${state.activeFamily}"]`);
    if (!activeTab) return;
    activeTab.scrollIntoView({
      behavior: behavior || "auto",
      block: "nearest",
      inline: "center",
    });
  }

  function renderSections() {
    if (!els.sections) return;
    if (!state.families.length) {
      els.sections.innerHTML = "";
      return;
    }
    els.sections.innerHTML = state.families.map((family) => {
      const products = state.products.filter((item) => item.family_code === family.code);
      return `
        <section class="shop-section" data-family-section="${escapeHtml(family.code)}">
          <div class="shop-section-header">
            <div>
              <h2 class="shop-section-title">${escapeHtml(family.name)}</h2>
              <p class="shop-section-subtitle">${escapeHtml(family.description || "")}</p>
            </div>
            <div class="shop-section-count">${escapeHtml(t("family_items", { count: products.length }))}</div>
          </div>
          <div class="shop-product-grid">
            ${products.map((product) => `
              <div class="shop-product-card${state.shopState.is_available ? "" : " is-disabled"}" data-product-card="${escapeHtml(product.code)}" role="button" tabindex="0" aria-label="${escapeHtml(localizedProductField(product, "name"))}">
                ${renderProductThumb(product)}
                <div class="shop-product-body">
                  <div class="shop-product-name">${escapeHtml(localizedProductField(product, "name"))}</div>
                  <div class="shop-product-subtitle">${escapeHtml(localizedProductField(product, "subtitle"))}</div>
                  ${product.default_variant_label ? `<div class="shop-product-subtitle">${escapeHtml(product.default_variant_label)}</div>` : ""}
                  <div class="shop-product-desc">${escapeHtml(localizedProductField(product, "description_short"))}</div>
                </div>
                <div class="shop-product-meta">
                  <div class="shop-product-card-price">${escapeHtml(formatCurrency(effectivePrice(product, product.default_variant_id), product.currency))}</div>
                  ${renderProductQtyControlMarkup(product)}
                </div>
              </div>
            `).join("")}
          </div>
        </section>
      `;
    }).join("");

    const stickyOffset = currentStickyOffset();
    els.sections.querySelectorAll("[data-family-section]").forEach((section) => {
      section.style.scrollMarginTop = `${stickyOffset}px`;
    });

    bindSectionObserver();
    syncProductControls();
  }

  function bindSectionObserver() {
    if (state.observer) state.observer.disconnect();
    const sections = Array.from(document.querySelectorAll("[data-family-section]"));
    if (!sections.length) return;
    state.observer = new IntersectionObserver((entries) => {
      if (Date.now() < state.programmaticScrollUntil) return;
      const visible = entries
        .filter((entry) => entry.isIntersecting)
        .sort((a, b) => b.intersectionRatio - a.intersectionRatio);
      if (visible[0]) {
        state.activeFamily = visible[0].target.getAttribute("data-family-section") || state.activeFamily;
        renderFamilies();
        syncActiveFamilyTab("smooth");
      }
    }, {
      rootMargin: "-18% 0px -62% 0px",
      threshold: [0.1, 0.4, 0.7],
    });
    sections.forEach((section) => state.observer.observe(section));
  }

  function renderCart() {
    const cart = state.cart || { items: [], total_quantity: 0, total: 0, currency: "EUR" };
    const hasItems = Array.isArray(cart.items) && cart.items.length > 0;
    if (els.cartBar) {
      const keepVisible = els.cartBar.classList.contains("is-feedback");
      els.cartBar.classList.toggle("d-none", !hasItems && !keepVisible);
    }
    if (els.cartBarSummary) {
      els.cartBarSummary.textContent = hasItems
        ? t("cart_bar_summary", { count: cart.total_quantity, total: formatCurrency(cart.total, cart.currency) })
        : t("empty_price");
    }
    if (els.cartTitleSummary) {
      els.cartTitleSummary.textContent = t("cart_items_count", { count: cart.total_quantity || 0 });
    }
    if (els.cartTotalValue) {
      els.cartTotalValue.textContent = formatCurrency(cart.total || 0, cart.currency || "EUR");
    }
    if (els.cartEmpty) {
      els.cartEmpty.classList.toggle("d-none", hasItems);
    }
    if (els.cartItems) {
      els.cartItems.innerHTML = hasItems ? cart.items.map((item) => `
        <div class="shop-cart-line" data-cart-line-key="${escapeHtml(item.key || cartLineKey(item.product_code, item.variant_id))}">
          <div>
            <div class="shop-cart-line-name">${escapeHtml(localizedProductField(item, "name") || item.product_name)}</div>
            ${item.variant_label ? `<div class="shop-cart-line-subtitle">${escapeHtml(item.variant_label)}</div>` : ""}
            <div class="shop-cart-line-subtitle">${escapeHtml(localizedProductField(item, "subtitle") || item.subtitle || "")}</div>
            <div class="shop-cart-line-price">${escapeHtml(formatCurrency(item.unit_price, item.currency))} / ${escapeHtml(t("line_qty"))}</div>
          </div>
          <div class="shop-cart-line-side">
            <div class="shop-cart-line-total">${escapeHtml(formatCurrency(item.line_total, item.currency))}</div>
            <div class="shop-cart-line-qty">
              <button type="button" data-cart-delta="-1" data-product-code="${escapeHtml(item.product_code)}" data-variant-id="${escapeHtml(item.variant_id || "")}" ${(!state.shopState.is_available || isProductPending(item.product_code, item.variant_id)) ? "disabled" : ""}>-</button>
              <strong>${item.quantity}</strong>
              <button type="button" data-cart-delta="1" data-product-code="${escapeHtml(item.product_code)}" data-variant-id="${escapeHtml(item.variant_id || "")}" ${(!state.shopState.is_available || isProductPending(item.product_code, item.variant_id)) ? "disabled" : ""}>+</button>
            </div>
          </div>
        </div>
      `).join("") : "";
    }
    if (els.checkoutBtn) {
      const hasDeliveryOptions = deliveryOptions().length > 0;
      els.checkoutBtn.disabled = !hasItems || !state.shopState.is_available || !hasDeliveryOptions;
      if (!state.shopState.is_available || !hasDeliveryOptions) {
        els.checkoutBtn.textContent = t("unavailable_cta");
      } else {
        els.checkoutBtn.textContent = t("checkout_cta");
      }
    }
    renderDeliverySheet();
  }

  function wait(ms) {
    return new Promise((resolve) => window.setTimeout(resolve, ms));
  }

  async function animateCartLineRemoval(lineEl) {
    if (!lineEl) return;
    lineEl.classList.add("is-removing");
    const buttons = Array.from(lineEl.querySelectorAll("button"));
    buttons.forEach((btn) => { btn.disabled = true; });
    await wait(180);
  }

  function renderCurrentProduct() {
    const product = state.currentProduct;
    if (!product) return;
    const selectedVariant = variantForProduct(product, state.currentVariantId);
    const selectedVariantId = normalizeVariantId(selectedVariant?.id);
    const pending = isProductPending(product.code, selectedVariantId);
    const imageUrl = String(product.image_url || "").trim();
    if (els.productHero) {
      els.productHero.style.cssText = `${accentStyle(product.accent)} min-height:246px;`;
      els.productHero.classList.toggle("is-image", !!imageUrl);
    }
    if (els.productHeroIcon) {
      els.productHeroIcon.innerHTML = imageUrl
        ? `<img src="${escapeHtml(imageUrl)}" alt="${escapeHtml(localizedProductField(product, "name") || localizedProductField(product, "title"))}" loading="eager">`
        : `<i class="fa-solid ${escapeHtml(product.icon)}"></i>`;
    }
    if (els.productHeroIcon) {
      els.productHeroIcon.classList.toggle("is-image", !!imageUrl);
      els.productHeroIcon.style.cssText = accentStyle(product.accent);
    }
    if (els.productFamily) els.productFamily.textContent = product.family_name || "";
    if (els.productTitle) els.productTitle.textContent = localizedProductField(product, "title") || localizedProductField(product, "name");
    if (els.productPrice) els.productPrice.textContent = formatCurrency(effectivePrice(product, selectedVariantId), product.currency);
    if (els.productSubtitle) {
      els.productSubtitle.textContent = selectedVariant?.label || localizedProductField(product, "subtitle") || "";
    }
    if (els.productDescription) {
      els.productDescription.textContent = selectedVariant?.description_short || localizedProductField(product, "description") || localizedProductField(product, "description_short") || "";
    }
    if (els.productVariantsBlock) {
      const variants = Array.isArray(product.variants) ? product.variants : [];
      els.productVariantsBlock.classList.toggle("d-none", !variants.length);
    }
    if (els.productVariants) {
      const variants = Array.isArray(product.variants) ? product.variants : [];
      els.productVariants.innerHTML = variants.map((variant) => `
        <button type="button" class="shop-product-variant-chip${normalizeVariantId(variant.id) === selectedVariantId ? " is-active" : ""}" data-product-variant="${escapeHtml(variant.id)}">
          ${escapeHtml(variant.label || variant.name || variant.value || "")}
        </button>
      `).join("");
    }
    if (els.productQtyValue) els.productQtyValue.textContent = String(state.currentQuantity || 1);
    if (els.productQtyMinus) els.productQtyMinus.disabled = pending;
    if (els.productQtyPlus) els.productQtyPlus.disabled = pending;
    if (els.productAddBtn) {
      els.productAddBtn.disabled = !state.shopState.is_available || pending;
      els.productAddBtn.textContent = state.shopState.is_available ? t("product_add") : t("unavailable_cta");
    }
  }

  function openSheet(which) {
    if (which === "product" && els.productSheet) {
      els.productSheet.classList.add("is-open");
      els.productSheet.setAttribute("aria-hidden", "false");
    }
    if (which === "cart" && els.cartSheet) {
      els.cartSheet.classList.add("is-open");
      els.cartSheet.setAttribute("aria-hidden", "false");
    }
    if (which === "delivery" && els.deliverySheet) {
      els.deliverySheet.classList.add("is-open");
      els.deliverySheet.setAttribute("aria-hidden", "false");
      renderDeliverySheet();
    }
    document.body.style.overflow = "hidden";
  }

  function closeSheet(which) {
    if (which === "product" && els.productSheet) {
      els.productSheet.classList.remove("is-open");
      els.productSheet.setAttribute("aria-hidden", "true");
    }
    if (which === "cart" && els.cartSheet) {
      els.cartSheet.classList.remove("is-open");
      els.cartSheet.setAttribute("aria-hidden", "true");
    }
    if (which === "delivery" && els.deliverySheet) {
      els.deliverySheet.classList.remove("is-open");
      els.deliverySheet.setAttribute("aria-hidden", "true");
    }
    if (!document.querySelector(".shop-sheet.is-open")) {
      document.body.style.overflow = "";
    }
  }

  async function fetchJson(url, options) {
    const response = await fetch(url, options || {});
    let payload = {};
    try {
      payload = await response.json();
    } catch (_) {
      payload = {};
    }
    if (!response.ok) {
      throw new Error(payload.error || t("error_loading"));
    }
    return payload;
  }

  async function loadBootstrap() {
    state.loading = true;
    state.error = "";
    if (els.loading) els.loading.classList.remove("d-none");
    if (els.error) els.error.classList.add("d-none");
    if (els.sections) els.sections.classList.add("d-none");
    try {
      const data = await fetchJson(`/api/r/${encodeURIComponent(PUBLIC_TOKEN)}/shop/bootstrap`);
      state.reservation = data.reservation || null;
      state.shopState = data.shop_state || state.shopState;
      state.families = Array.isArray(data.catalog?.families) ? data.catalog.families : [];
      state.products = Array.isArray(data.catalog?.products) ? data.catalog.products : [];
      state.productsByCode = {};
      state.products.forEach((product) => {
        state.productsByCode[product.code] = product;
      });
      state.cart = data.cart || state.cart;
      state.selectedDeliveryMethod = String(state.shopState?.default_delivery_method || state.selectedDeliveryMethod || "").trim().toUpperCase();
      ensureDeliverySelection();
      state.activeFamily = state.activeFamily || (state.families[0] ? state.families[0].code : "");
      renderStateBanner();
      renderFamilies();
      renderSections();
      renderCart();
      applyLanguage(currentLang());
      if (els.sections) els.sections.classList.remove("d-none");
    } catch (error) {
      state.error = error.message || t("error_loading");
      if (els.error) {
        els.error.innerHTML = `${escapeHtml(state.error)} <button type="button" class="btn btn-sm btn-outline-light ms-2" id="shopRetryBtn">${escapeHtml(t("retry"))}</button>`;
        els.error.classList.remove("d-none");
      }
    } finally {
      state.loading = false;
      if (els.loading) els.loading.classList.add("d-none");
    }
  }

  async function openProduct(productCode) {
    const code = String(productCode || "").trim().toUpperCase();
    if (!code) return;
    const fallback = state.productsByCode[code];
    try {
      const data = await fetchJson(`/api/r/${encodeURIComponent(PUBLIC_TOKEN)}/shop/products/${encodeURIComponent(code)}`);
      state.currentProduct = data.product || fallback || null;
    } catch (_) {
      state.currentProduct = fallback || null;
    }
    if (!state.currentProduct) return;
    state.currentVariantId = normalizeVariantId(defaultVariantFor(state.currentProduct)?.id);
    state.currentQuantity = 1;
    renderCurrentProduct();
    openSheet("product");
  }

  async function updateCartItem(productCode, payload) {
    const code = productCodeKey(productCode);
    const variantId = normalizeVariantId(payload?.variantId);
    const lineKey = String(payload?.lineKey || "").trim();
    const skipOptimisticCartRender = !!payload?.skipOptimisticCartRender;
    const body = { product_code: code };
    if (variantId) body.variant_id = variantId;
    if (lineKey) body.line_key = lineKey;
    if (Object.prototype.hasOwnProperty.call(payload || {}, "delta")) body.delta = payload.delta;
    if (Object.prototype.hasOwnProperty.call(payload || {}, "quantity")) body.quantity = payload.quantity;
    const pendingKey = lineKey || cartLineKey(code, variantId);
    state.pendingProducts[pendingKey] = true;
    syncProductControls(code);
    if (!skipOptimisticCartRender) renderCart();
    renderCurrentProduct();
    try {
      const data = await fetchJson(`/api/r/${encodeURIComponent(PUBLIC_TOKEN)}/shop/cart/items`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      state.cart = data.cart || state.cart;
      state.shopState = data.shop_state || state.shopState;
      if (!selectedDeliveryOption()) {
        state.selectedDeliveryMethod = String(state.shopState?.default_delivery_method || "").trim().toUpperCase();
      }
      ensureDeliverySelection();
      renderStateBanner();
      renderCart();
      renderCurrentProduct();
      syncProductControls(code);
      triggerCartFeedback();
    } finally {
      delete state.pendingProducts[pendingKey];
      syncProductControls(code);
      renderCart();
      renderCurrentProduct();
    }
  }

  async function submitCheckout() {
    const deliveryOption = ensureDeliverySelection();
    if (els.deliveryConfirmBtn) els.deliveryConfirmBtn.disabled = true;
    if (els.deliveryMsg) els.deliveryMsg.textContent = "";
    if (!deliveryOption) {
      if (els.deliveryMsg) els.deliveryMsg.textContent = t("delivery_unavailable");
      if (els.deliveryConfirmBtn) els.deliveryConfirmBtn.disabled = false;
      return;
    }
    try {
      const data = await fetchJson(`/api/r/${encodeURIComponent(PUBLIC_TOKEN)}/shop/checkout`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          lang: currentLang(),
          delivery_method: String(deliveryOption.code || "").trim().toUpperCase(),
        }),
      });
      if (data.checkout_url) {
        if (els.deliveryMsg) els.deliveryMsg.textContent = data.message || t("checkout_redirecting");
        window.setTimeout(() => {
          window.location.assign(String(data.checkout_url));
        }, 120);
        return;
      }
      if (els.deliveryMsg) els.deliveryMsg.textContent = data.message || t("checkout_pending");
    } catch (error) {
      if (els.deliveryMsg) els.deliveryMsg.textContent = error.message || t("checkout_pending");
    } finally {
      if (els.deliveryConfirmBtn) els.deliveryConfirmBtn.disabled = false;
    }
  }

  async function handleCheckoutReturn() {
    const params = new URLSearchParams(window.location.search || "");
    const checkoutState = String(params.get("checkout") || "").trim().toLowerCase();
    const sessionId = String(params.get("session_id") || "").trim();
    if (!checkoutState) return;

    const cleanUrl = `${window.location.pathname}${window.location.hash || ""}`;
    const cleanupUrl = () => {
      try {
        window.history.replaceState({}, document.title, cleanUrl);
      } catch (_) {
        // noop
      }
    };

    if (checkoutState === "cancel") {
      if (els.checkoutMsg) els.checkoutMsg.textContent = t("checkout_cancelled");
      if (els.deliveryMsg) els.deliveryMsg.textContent = "";
      openSheet("cart");
      cleanupUrl();
      return;
    }

    if (checkoutState !== "success" || !sessionId) {
      cleanupUrl();
      return;
    }

    if (els.checkoutMsg) els.checkoutMsg.textContent = t("checkout_pending_confirmation");
    if (els.deliveryMsg) els.deliveryMsg.textContent = "";
    try {
      const data = await fetchJson(`/api/r/${encodeURIComponent(PUBLIC_TOKEN)}/shop/checkout/confirm?session_id=${encodeURIComponent(sessionId)}`);
      state.cart = data.cart || state.cart;
      state.shopState = data.shop_state || state.shopState;
      if (!selectedDeliveryOption()) {
        state.selectedDeliveryMethod = String(state.shopState?.default_delivery_method || "").trim().toUpperCase();
      }
      ensureDeliverySelection();
      renderStateBanner();
      renderCart();
      renderCurrentProduct();
      if (els.checkoutMsg) {
        els.checkoutMsg.textContent = data.message || (String(data.status || "").toLowerCase() === "paid" ? t("checkout_success") : t("checkout_pending_confirmation"));
      }
      if (String(data.status || "").toLowerCase() === "paid") {
        triggerCartFeedback();
      }
      openSheet("cart");
    } catch (error) {
      if (els.checkoutMsg) els.checkoutMsg.textContent = error.message || t("checkout_pending");
      openSheet("cart");
    } finally {
      cleanupUrl();
    }
  }

  document.addEventListener("click", async (event) => {
    const retryBtn = event.target.closest("#shopRetryBtn");
    if (retryBtn) {
      loadBootstrap();
      return;
    }

    const familyTab = event.target.closest("[data-family-tab]");
    if (familyTab) {
      const familyCode = familyTab.getAttribute("data-family-tab") || "";
      if (familyCode) {
        state.activeFamily = familyCode;
        renderFamilies();
        syncActiveFamilyTab("smooth");
        scrollToFamilySection(familyCode, "smooth");
      }
      return;
    }

    const productQtyAddBtn = event.target.closest("[data-product-qty-add]");
    if (productQtyAddBtn) {
      if (!state.shopState.is_available) return;
      const code = productQtyAddBtn.getAttribute("data-product-qty-add") || "";
      const variantId = normalizeVariantId(productQtyAddBtn.getAttribute("data-variant-id"));
      if (isProductPending(code, variantId)) return;
      try {
        await updateCartItem(code, { delta: 1, variantId });
        if (els.checkoutMsg) els.checkoutMsg.textContent = t("added_to_cart");
      } catch (error) {
        if (els.checkoutMsg) els.checkoutMsg.textContent = error.message || "";
      }
      return;
    }

    const productQtyDecreaseBtn = event.target.closest("[data-product-qty-decrease]");
    if (productQtyDecreaseBtn) {
      if (!state.shopState.is_available) return;
      const code = productQtyDecreaseBtn.getAttribute("data-product-qty-decrease") || "";
      const variantId = normalizeVariantId(productQtyDecreaseBtn.getAttribute("data-variant-id"));
      if (isProductPending(code, variantId)) return;
      const quantity = cartQuantityFor(code, variantId);
      try {
        if (quantity <= 1) {
          await updateCartItem(code, { quantity: 0, variantId });
        } else {
          await updateCartItem(code, { delta: -1, variantId });
        }
      } catch (error) {
        if (els.checkoutMsg) els.checkoutMsg.textContent = error.message || "";
      }
      return;
    }

    const productQtyIncreaseBtn = event.target.closest("[data-product-qty-increase]");
    if (productQtyIncreaseBtn) {
      if (!state.shopState.is_available) return;
      const code = productQtyIncreaseBtn.getAttribute("data-product-qty-increase") || "";
      const variantId = normalizeVariantId(productQtyIncreaseBtn.getAttribute("data-variant-id"));
      if (isProductPending(code, variantId)) return;
      try {
        await updateCartItem(code, { delta: 1, variantId });
      } catch (error) {
        if (els.checkoutMsg) els.checkoutMsg.textContent = error.message || "";
      }
      return;
    }

    const variantChip = event.target.closest("[data-product-variant]");
    if (variantChip && state.currentProduct) {
      state.currentVariantId = normalizeVariantId(variantChip.getAttribute("data-product-variant"));
      renderCurrentProduct();
      return;
    }

    const productCard = event.target.closest("[data-product-card]");
    if (productCard) {
      openProduct(productCard.getAttribute("data-product-card"));
      return;
    }

    const cartDeltaBtn = event.target.closest("[data-cart-delta][data-product-code]");
    if (cartDeltaBtn) {
      if (!state.shopState.is_available) return;
      const delta = Number(cartDeltaBtn.getAttribute("data-cart-delta") || 0);
      const code = cartDeltaBtn.getAttribute("data-product-code") || "";
      const variantId = normalizeVariantId(cartDeltaBtn.getAttribute("data-variant-id"));
      const lineKey = String(cartDeltaBtn.closest("[data-cart-line-key]")?.getAttribute("data-cart-line-key") || "").trim();
      if (isProductPending(code, variantId)) return;
      const lineEl = cartDeltaBtn.closest("[data-cart-line-key]");
      const quantity = cartQuantityFor(code, variantId);
      try {
        if (delta < 0 && quantity <= 1) {
          await animateCartLineRemoval(lineEl);
          await updateCartItem(code, { quantity: 0, variantId, lineKey, skipOptimisticCartRender: true });
          return;
        }
        await updateCartItem(code, { delta, variantId, lineKey });
      } catch (error) {
        if (lineEl) lineEl.classList.remove("is-removing");
        if (els.checkoutMsg) els.checkoutMsg.textContent = error.message || "";
      }
      return;
    }

    const closeBtn = event.target.closest("[data-close-sheet]");
    if (closeBtn) {
      closeSheet(closeBtn.getAttribute("data-close-sheet"));
      return;
    }
  });

  document.addEventListener("change", (event) => {
    const deliveryInput = event.target.closest('input[name="shopDeliveryMethod"]');
    if (!deliveryInput) return;
    state.selectedDeliveryMethod = String(deliveryInput.value || "").trim().toUpperCase();
    renderDeliverySheet();
  });

  if (els.productQtyMinus) {
    els.productQtyMinus.addEventListener("click", () => {
      state.currentQuantity = Math.max(1, Number(state.currentQuantity || 1) - 1);
      renderCurrentProduct();
    });
  }

  if (els.productQtyPlus) {
    els.productQtyPlus.addEventListener("click", () => {
      state.currentQuantity = Math.min(99, Number(state.currentQuantity || 1) + 1);
      renderCurrentProduct();
    });
  }

  if (els.productAddBtn) {
    els.productAddBtn.addEventListener("click", async () => {
      if (!state.currentProduct || !state.shopState.is_available) return;
      if (isProductPending(state.currentProduct.code, state.currentVariantId)) return;
      const original = els.productAddBtn.textContent;
      try {
        await updateCartItem(state.currentProduct.code, {
          delta: Number(state.currentQuantity || 1),
          variantId: state.currentVariantId,
        });
        els.productAddBtn.textContent = t("added_to_cart");
        window.setTimeout(() => {
          closeSheet("product");
          els.productAddBtn.textContent = original;
        }, 450);
      } catch (error) {
        els.productAddBtn.textContent = error.message || original;
        window.setTimeout(() => {
          els.productAddBtn.textContent = original;
        }, 900);
      }
    });
  }

  if (els.cartBar) {
    els.cartBar.addEventListener("click", () => openSheet("cart"));
  }

  if (els.checkoutBtn) {
    els.checkoutBtn.addEventListener("click", () => {
      if (!state.cart?.items?.length || !state.shopState.is_available || !deliveryOptions().length) {
        renderCart();
        return;
      }
      if (els.checkoutMsg) els.checkoutMsg.textContent = "";
      if (els.deliveryMsg) els.deliveryMsg.textContent = "";
      closeSheet("cart");
      openSheet("delivery");
    });
  }

  if (els.deliveryConfirmBtn) {
    els.deliveryConfirmBtn.addEventListener("click", submitCheckout);
  }

  window.addEventListener("resize", () => {
    updateStickyMetrics();
    if (state.families.length) renderSections();
  });

  window.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      closeSheet("product");
      closeSheet("cart");
      closeSheet("delivery");
      return;
    }
    if (event.key === "Enter" || event.key === " ") {
      const card = document.activeElement && document.activeElement.closest ? document.activeElement.closest("[data-product-card]") : null;
      if (card && document.activeElement === card) {
        event.preventDefault();
        openProduct(card.getAttribute("data-product-card"));
      }
    }
  });

  async function init() {
    applyLanguage(currentLang());
    updateStickyMetrics();
    await loadBootstrap();
    await handleCheckoutReturn();
  }

  init();
})();
