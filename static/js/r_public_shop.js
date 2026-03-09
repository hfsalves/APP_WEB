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
      hero_kicker: "Chegada preparada",
      hero_title: "Itens a adicionar a sua chegada",
      hero_subtitle: "Escolhe pequenos extras para encontrares tudo pronto quando entrares no alojamento.",
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
      cart_title: "Carrinho",
      cart_total: "Total",
      cart_empty_title: "Ainda nao adicionaste nada",
      cart_empty_text: "Explora os artigos e adiciona o que precisares para encontrares tudo pronto a chegada.",
      checkout_cta: "Avancar para checkout",
      checkout_pending: "Fluxo Stripe preparado no frontend e pendente de integracao backend.",
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
      hero_kicker: "Arrival ready",
      hero_title: "Items to add before you arrive",
      hero_subtitle: "Choose a few extras so everything is ready when you enter the property.",
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
      cart_title: "Cart",
      cart_total: "Total",
      cart_empty_title: "You have not added anything yet",
      cart_empty_text: "Browse the items and add whatever you need so it is ready on arrival.",
      checkout_cta: "Continue to checkout",
      checkout_pending: "Stripe flow is prepared on the frontend and pending backend integration.",
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
      hero_kicker: "Arrivee preparee",
      hero_title: "Articles a ajouter avant votre arrivee",
      hero_subtitle: "Choisissez quelques extras pour tout trouver pret en entrant dans le logement.",
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
      cart_title: "Panier",
      cart_total: "Total",
      cart_empty_title: "Vous n avez encore rien ajoute",
      cart_empty_text: "Parcourez les articles et ajoutez ce dont vous avez besoin pour tout trouver pret a l arrivee.",
      checkout_cta: "Continuer vers le paiement",
      checkout_pending: "Le flux Stripe est prepare cote frontend et attend l integration backend.",
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
      hero_kicker: "Llegada preparada",
      hero_title: "Articulos para anadir a tu llegada",
      hero_subtitle: "Elige pequenos extras para encontrar todo listo al entrar en el alojamiento.",
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
      cart_title: "Carrito",
      cart_total: "Total",
      cart_empty_title: "Todavia no has anadido nada",
      cart_empty_text: "Explora los articulos y anade lo que necesites para encontrarlo todo listo a tu llegada.",
      checkout_cta: "Avanzar al pago",
      checkout_pending: "El flujo Stripe esta preparado en frontend y pendiente de integracion backend.",
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
    currentQuantity: 1,
    loading: true,
    error: "",
    observer: null,
    programmaticScrollUntil: 0,
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

  function accentStyle(accent) {
    const safe = String(accent || "#2563eb");
    return `background: linear-gradient(135deg, ${safe}, rgba(14,165,233,0.86));`;
  }

  function updateStickyMetrics() {
    const shellHeight = els.topbarShell ? Math.ceil(els.topbarShell.getBoundingClientRect().height) : 0;
    document.documentElement.style.setProperty("--shop-sticky-top", `${shellHeight}px`);
    return shellHeight;
  }

  function currentStickyOffset() {
    const topbarHeight = updateStickyMetrics();
    const familyBarHeight = els.familyBar ? Math.ceil(els.familyBar.getBoundingClientRect().height) : 0;
    return topbarHeight + familyBarHeight + 20;
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
      els.stateText.textContent = deadline
        ? t(state.shopState.is_available ? "state_open_text" : "state_closed_text", { deadline })
        : (state.shopState.message || "");
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
              <div class="shop-product-card${state.shopState.is_available ? "" : " is-disabled"}" data-product-card="${escapeHtml(product.code)}" role="button" tabindex="0" aria-label="${escapeHtml(product.name)}">
                <div class="shop-product-thumb" style="${accentStyle(product.accent)}">
                  <i class="fa-solid ${escapeHtml(product.icon)}"></i>
                </div>
                <div class="shop-product-body">
                  <div class="shop-product-name">${escapeHtml(product.name)}</div>
                  <div class="shop-product-subtitle">${escapeHtml(product.subtitle || "")}</div>
                  <div class="shop-product-desc">${escapeHtml(product.description_short || "")}</div>
                </div>
                <div class="shop-product-meta">
                  <div class="shop-product-card-price">${escapeHtml(formatCurrency(product.price, product.currency))}</div>
                  <button type="button" class="shop-product-cta" data-product-add="${escapeHtml(product.code)}" aria-label="${escapeHtml(t("product_add"))}" ${state.shopState.is_available ? "" : "disabled"}>
                    <i class="fa-solid fa-plus"></i>
                  </button>
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
      els.cartBar.classList.toggle("d-none", !hasItems);
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
        <div class="shop-cart-line">
          <div>
            <div class="shop-cart-line-name">${escapeHtml(item.product_name)}</div>
            <div class="shop-cart-line-subtitle">${escapeHtml(item.subtitle || "")}</div>
            <div class="shop-cart-line-price">${escapeHtml(formatCurrency(item.unit_price, item.currency))} / ${escapeHtml(t("line_qty"))}</div>
          </div>
          <div class="shop-cart-line-side">
            <div class="shop-cart-line-total">${escapeHtml(formatCurrency(item.line_total, item.currency))}</div>
            <div class="shop-cart-line-qty">
              <button type="button" data-cart-delta="-1" data-product-code="${escapeHtml(item.product_code)}" ${state.shopState.is_available ? "" : "disabled"}>-</button>
              <strong>${item.quantity}</strong>
              <button type="button" data-cart-delta="1" data-product-code="${escapeHtml(item.product_code)}" ${state.shopState.is_available ? "" : "disabled"}>+</button>
            </div>
          </div>
        </div>
      `).join("") : "";
    }
    if (els.checkoutBtn) {
      els.checkoutBtn.disabled = !hasItems || !state.shopState.is_available;
      if (!state.shopState.is_available) {
        els.checkoutBtn.textContent = t("unavailable_cta");
      } else {
        els.checkoutBtn.textContent = t("checkout_cta");
      }
    }
  }

  function renderCurrentProduct() {
    const product = state.currentProduct;
    if (!product) return;
    if (els.productHero) els.productHero.style.cssText = `${accentStyle(product.accent)} min-height:240px;`;
    if (els.productHeroIcon) els.productHeroIcon.innerHTML = `<i class="fa-solid ${escapeHtml(product.icon)}"></i>`;
    if (els.productHeroIcon) els.productHeroIcon.style.cssText = accentStyle(product.accent);
    if (els.productFamily) els.productFamily.textContent = product.family_name || "";
    if (els.productTitle) els.productTitle.textContent = product.name || "";
    if (els.productPrice) els.productPrice.textContent = formatCurrency(product.price, product.currency);
    if (els.productSubtitle) els.productSubtitle.textContent = product.subtitle || "";
    if (els.productDescription) els.productDescription.textContent = product.description || product.description_short || "";
    if (els.productQtyValue) els.productQtyValue.textContent = String(state.currentQuantity || 1);
    if (els.productAddBtn) {
      els.productAddBtn.disabled = !state.shopState.is_available;
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
    state.currentQuantity = 1;
    renderCurrentProduct();
    openSheet("product");
  }

  async function updateCartItem(productCode, payload) {
    const body = { product_code: productCode };
    if (Object.prototype.hasOwnProperty.call(payload || {}, "delta")) body.delta = payload.delta;
    if (Object.prototype.hasOwnProperty.call(payload || {}, "quantity")) body.quantity = payload.quantity;
    const data = await fetchJson(`/api/r/${encodeURIComponent(PUBLIC_TOKEN)}/shop/cart/items`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    state.cart = data.cart || state.cart;
    state.shopState = data.shop_state || state.shopState;
    renderStateBanner();
    renderCart();
    renderCurrentProduct();
  }

  async function submitCheckout() {
    if (els.checkoutMsg) els.checkoutMsg.textContent = "";
    try {
      const data = await fetchJson(`/api/r/${encodeURIComponent(PUBLIC_TOKEN)}/shop/checkout`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
      });
      if (els.checkoutMsg) els.checkoutMsg.textContent = data.message || t("checkout_pending");
    } catch (error) {
      if (els.checkoutMsg) els.checkoutMsg.textContent = error.message || t("checkout_pending");
    }
  }

  document.addEventListener("click", async (event) => {
    const retryBtn = event.target.closest("#shopRetryBtn");
    if (retryBtn) {
      loadBootstrap();
      return;
    }

    if (els.langMenuBtn && (event.target === els.langMenuBtn || els.langMenuBtn.contains(event.target))) {
      if (els.langMenuList) els.langMenuList.classList.toggle("open");
      return;
    }

    const langBtn = event.target.closest(".shop-lang-option[data-lang]");
    if (langBtn) {
      applyLanguage(langBtn.dataset.lang);
      if (els.langMenuList) els.langMenuList.classList.remove("open");
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

    const productAddBtn = event.target.closest("[data-product-add]");
    if (productAddBtn) {
      if (!state.shopState.is_available) return;
      const code = productAddBtn.getAttribute("data-product-add") || "";
      try {
        await updateCartItem(code, { delta: 1 });
        if (els.checkoutMsg) els.checkoutMsg.textContent = t("added_to_cart");
      } catch (error) {
        if (els.checkoutMsg) els.checkoutMsg.textContent = error.message || "";
      }
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
      try {
        await updateCartItem(code, { delta });
      } catch (error) {
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

  document.addEventListener("click", (event) => {
    if (els.langMenuList && els.langMenuBtn && !els.langMenuBtn.contains(event.target) && !els.langMenuList.contains(event.target)) {
      els.langMenuList.classList.remove("open");
    }
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
      const original = els.productAddBtn.textContent;
      try {
        await updateCartItem(state.currentProduct.code, {
          delta: Number(state.currentQuantity || 1),
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
    els.checkoutBtn.addEventListener("click", submitCheckout);
  }

  window.addEventListener("resize", () => {
    updateStickyMetrics();
    if (state.families.length) renderSections();
  });

  window.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      closeSheet("product");
      closeSheet("cart");
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

  applyLanguage(currentLang());
  updateStickyMetrics();
  loadBootstrap();
})();
