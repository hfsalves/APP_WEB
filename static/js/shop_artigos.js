document.addEventListener("DOMContentLoaded", () => {
  const state = {
    meta: null,
    families: [],
    products: [],
    currentProduct: null,
  };

  const els = {
    search: document.getElementById("shopProductsSearch"),
    familyFilter: document.getElementById("shopProductsFamilyFilter"),
    activeFilter: document.getElementById("shopProductsActiveFilter"),
    sort: document.getElementById("shopProductsSort"),
    status: document.getElementById("shopProductsStatus"),
    refresh: document.getElementById("shopProductsRefreshBtn"),
    newBtn: document.getElementById("shopNewProductBtn"),
    familyBtn: document.getElementById("shopFamiliesBtn"),
    tableBody: document.getElementById("shopProductsBody"),
    count: document.getElementById("shopProductsCount"),
    activeCount: document.getElementById("shopProductsActiveCount"),
    familiesCount: document.getElementById("shopProductsFamiliesCount"),

    productModalEl: document.getElementById("shopProductModal"),
    productTitle: document.getElementById("shopProductModalTitle"),
    productStatus: document.getElementById("shopProductModalStatus"),
    productId: document.getElementById("shopProductId"),
    productCode: document.getElementById("shopProductCode"),
    productFamily: document.getElementById("shopProductFamily"),
    productName: document.getElementById("shopProductName"),
    productTitleInput: document.getElementById("shopProductTitle"),
    productSubtitle: document.getElementById("shopProductSubtitle"),
    productPrice: document.getElementById("shopProductPrice"),
    productOrder: document.getElementById("shopProductOrder"),
    productDescriptionShort: document.getElementById("shopProductDescriptionShort"),
    productDescription: document.getElementById("shopProductDescription"),
    productActive: document.getElementById("shopProductActive"),
    productTranslationsBtn: document.getElementById("shopProductTranslationsBtn"),
    openFamiliesFromProduct: document.getElementById("shopProductOpenFamiliesBtn"),
    saveProduct: document.getElementById("shopSaveProductBtn"),
    variantsBody: document.getElementById("shopVariantsBody"),
    addVariantBtn: document.getElementById("shopAddVariantBtn"),
    imageFile: document.getElementById("shopImageFile"),
    imageAltText: document.getElementById("shopImageAltText"),
    uploadImageBtn: document.getElementById("shopUploadImageBtn"),
    imagesGrid: document.getElementById("shopImagesGrid"),
    imagesHint: document.getElementById("shopImagesHint"),

    translationsModalEl: document.getElementById("shopTranslationsModal"),
    translationsStatus: document.getElementById("shopTranslationsStatus"),
    autoTranslateBtn: document.getElementById("shopAutoTranslateBtn"),
    productNameEn: document.getElementById("shopProductNameEn"),
    productTitleEn: document.getElementById("shopProductTitleEn"),
    productSubtitleEn: document.getElementById("shopProductSubtitleEn"),
    productDescriptionShortEn: document.getElementById("shopProductDescriptionShortEn"),
    productDescriptionEn: document.getElementById("shopProductDescriptionEn"),
    productNameEs: document.getElementById("shopProductNameEs"),
    productTitleEs: document.getElementById("shopProductTitleEs"),
    productSubtitleEs: document.getElementById("shopProductSubtitleEs"),
    productDescriptionShortEs: document.getElementById("shopProductDescriptionShortEs"),
    productDescriptionEs: document.getElementById("shopProductDescriptionEs"),
    productNameFr: document.getElementById("shopProductNameFr"),
    productTitleFr: document.getElementById("shopProductTitleFr"),
    productSubtitleFr: document.getElementById("shopProductSubtitleFr"),
    productDescriptionShortFr: document.getElementById("shopProductDescriptionShortFr"),
    productDescriptionFr: document.getElementById("shopProductDescriptionFr"),

    familiesModalEl: document.getElementById("shopFamiliesModal"),
    familiesBody: document.getElementById("shopFamiliesBody"),
    familyModalStatus: document.getElementById("shopFamilyModalStatus"),
    familyId: document.getElementById("shopFamilyId"),
    familyCode: document.getElementById("shopFamilyCode"),
    familyOrder: document.getElementById("shopFamilyOrder"),
    familyName: document.getElementById("shopFamilyName"),
    familyTitle: document.getElementById("shopFamilyTitle"),
    familyDescription: document.getElementById("shopFamilyDescription"),
    familyActive: document.getElementById("shopFamilyActive"),
    saveFamilyBtn: document.getElementById("shopSaveFamilyBtn"),
    newFamilyBtn: document.getElementById("shopNewFamilyBtn"),
  };

  const productModal = new bootstrap.Modal(els.productModalEl);
  const translationsModal = new bootstrap.Modal(els.translationsModalEl);
  const familiesModal = new bootstrap.Modal(els.familiesModalEl);

  const money = (value, currency = "EUR") =>
    new Intl.NumberFormat("pt-PT", { style: "currency", currency }).format(Number(value || 0));
  const dt = (value) => {
    if (!value) return "-";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return value;
    return new Intl.DateTimeFormat("pt-PT", {
      dateStyle: "short",
      timeStyle: "short",
    }).format(date);
  };
  const badge = (label, tone) => `<span class="sz_badge sz_badge_${tone}">${label}</span>`;
  const esc = (value) =>
    String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;");

  async function api(url, options = {}) {
    const response = await fetch(url, options);
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(data.error || "Erro inesperado.");
    }
    return data;
  }

  function setStatus(message, tone = "muted") {
    els.status.className = tone === "danger" ? "text-danger shop-bo-status" : "sz_text_muted shop-bo-status";
    els.status.textContent = message;
  }

  function setProductModalStatus(message, tone = "muted") {
    els.productStatus.className = tone === "danger" ? "text-danger shop-bo-helper" : "shop-bo-helper";
    els.productStatus.textContent = message || "";
  }

  function setFamilyModalStatus(message, tone = "muted") {
    els.familyModalStatus.className = tone === "danger" ? "text-danger shop-bo-helper" : "shop-bo-helper";
    els.familyModalStatus.textContent = message || "";
  }

  function setTranslationsStatus(message, tone = "muted") {
    els.translationsStatus.className = tone === "danger" ? "text-danger shop-bo-helper" : "shop-bo-helper";
    els.translationsStatus.textContent = message || "";
  }

  function resetTranslationsForm() {
    [
      "productNameEn", "productTitleEn", "productSubtitleEn", "productDescriptionShortEn", "productDescriptionEn",
      "productNameEs", "productTitleEs", "productSubtitleEs", "productDescriptionShortEs", "productDescriptionEs",
      "productNameFr", "productTitleFr", "productSubtitleFr", "productDescriptionShortFr", "productDescriptionFr",
    ].forEach((key) => {
      if (els[key]) els[key].value = "";
    });
    setTranslationsStatus("");
  }

  function fillTranslationsForm(product) {
    els.productNameEn.value = product.NOME_EN || "";
    els.productTitleEn.value = product.TITULO_EN || "";
    els.productSubtitleEn.value = product.SUBTITULO_EN || "";
    els.productDescriptionShortEn.value = product.DESCRICAO_CURTA_EN || "";
    els.productDescriptionEn.value = product.DESCRICAO_EN || "";

    els.productNameEs.value = product.NOME_ES || "";
    els.productTitleEs.value = product.TITULO_ES || "";
    els.productSubtitleEs.value = product.SUBTITULO_ES || "";
    els.productDescriptionShortEs.value = product.DESCRICAO_CURTA_ES || "";
    els.productDescriptionEs.value = product.DESCRICAO_ES || "";

    els.productNameFr.value = product.NOME_FR || "";
    els.productTitleFr.value = product.TITULO_FR || "";
    els.productSubtitleFr.value = product.SUBTITULO_FR || "";
    els.productDescriptionShortFr.value = product.DESCRICAO_CURTA_FR || "";
    els.productDescriptionFr.value = product.DESCRICAO_FR || "";
    setTranslationsStatus("");
  }

  function collectTranslationsPayload() {
    return {
      NOME_EN: els.productNameEn.value,
      TITULO_EN: els.productTitleEn.value,
      SUBTITULO_EN: els.productSubtitleEn.value,
      DESCRICAO_CURTA_EN: els.productDescriptionShortEn.value,
      DESCRICAO_EN: els.productDescriptionEn.value,
      NOME_ES: els.productNameEs.value,
      TITULO_ES: els.productTitleEs.value,
      SUBTITULO_ES: els.productSubtitleEs.value,
      DESCRICAO_CURTA_ES: els.productDescriptionShortEs.value,
      DESCRICAO_ES: els.productDescriptionEs.value,
      NOME_FR: els.productNameFr.value,
      TITULO_FR: els.productTitleFr.value,
      SUBTITULO_FR: els.productSubtitleFr.value,
      DESCRICAO_CURTA_FR: els.productDescriptionShortFr.value,
      DESCRICAO_FR: els.productDescriptionFr.value,
    };
  }

  function familyOptionsHtml(selectedId) {
    return ['<option value="">Seleciona...</option>']
      .concat(
        state.families.map((family) => {
          const selected = Number(selectedId) === Number(family.FAMILIA_ID) ? "selected" : "";
          return `<option value="${family.FAMILIA_ID}" ${selected}>${esc(family.NOME)}</option>`;
        })
      )
      .join("");
  }

  function populateFamilySelectors(selectedId = null) {
    els.familyFilter.innerHTML = '<option value="">Todas</option>' + state.families.map((family) => (
      `<option value="${family.FAMILIA_ID}">${esc(family.NOME)}</option>`
    )).join("");
    if (els.familyFilter.dataset.currentValue) {
      els.familyFilter.value = els.familyFilter.dataset.currentValue;
    }
    els.productFamily.innerHTML = familyOptionsHtml(selectedId);
  }

  function collectFilters() {
    return new URLSearchParams({
      q: els.search.value.trim(),
      family_id: els.familyFilter.value,
      active: els.activeFilter.value,
      sort: els.sort.value,
    }).toString();
  }

  function renderProducts(items, summary) {
    els.tableBody.innerHTML = "";
    if (!items.length) {
      els.tableBody.innerHTML = '<tr class="sz_table_row"><td colspan="9" class="sz_table_cell sz_text_muted">Nenhum artigo encontrado.</td></tr>';
    } else {
      els.tableBody.innerHTML = items.map((item) => `
        <tr class="sz_table_row">
          <td class="sz_table_cell shop-bo-code">${item.PRODUTO_ID}</td>
          <td class="sz_table_cell">
            <div class="shop-bo-name">
              <div class="shop-bo-thumb">${item.IMAGEM_URL ? `<img src="${esc(item.IMAGEM_URL)}" alt="">` : ""}</div>
              <div class="shop-bo-name_text">
                <div class="shop-bo-name_title">${esc(item.NOME)}</div>
                <div class="shop-bo-name_subtitle">${esc(item.CODIGO)} · ${esc(item.SUBTITULO || "")}</div>
              </div>
            </div>
          </td>
          <td class="sz_table_cell">${esc(item.FAMILIA_NOME)}</td>
          <td class="sz_table_cell sz_text_right">${money(item.PRECO, item.MOEDA || "EUR")}</td>
          <td class="sz_table_cell sz_text_right">${Number(item.STOCK_ATUAL || 0).toLocaleString("pt-PT")}</td>
          <td class="sz_table_cell">${item.ATIVO ? badge("Ativo", "success") : badge("Inativo", "warning")}</td>
          <td class="sz_table_cell sz_text_right">${item.ORDEM ?? 0}</td>
          <td class="sz_table_cell">${dt(item.ALTERADO_EM)}</td>
          <td class="sz_table_cell sz_text_right">
            <button class="sz_button sz_button_ghost shop-bo-row_button" data-action="edit" data-id="${item.PRODUTO_ID}">
              <i class="fa-solid fa-pen"></i>
            </button>
          </td>
        </tr>
      `).join("");
    }
    els.count.textContent = summary ? String(items.length) : "0";
    els.activeCount.textContent = summary ? String(summary.active_count || 0) : "0";
    els.familiesCount.textContent = summary ? String(summary.families_count || 0) : "0";
  }

  function emptyVariantRow() {
    return {
      CODIGO: "",
      TIPO_VARIANTE: "OUTRO",
      NOME: "",
      VALOR: "",
      PRECO: "",
      ORDEM: 0,
      PADRAO: false,
      ATIVO: true,
    };
  }

  function renderVariants(variants) {
    const rows = variants.length ? variants : [];
    if (!rows.length) {
      els.variantsBody.innerHTML = '<tr class="sz_table_row"><td colspan="8" class="sz_table_cell sz_text_muted">Sem variantes.</td></tr>';
      return;
    }
    els.variantsBody.innerHTML = rows.map((variant, index) => `
      <tr class="sz_table_row">
        <td class="sz_table_cell">
          <select class="sz_select" data-field="TIPO_VARIANTE">
            ${(state.meta?.variant_types || []).map((type) => `<option value="${type.code}" ${String(variant.TIPO_VARIANTE) === type.code ? "selected" : ""}>${type.name}</option>`).join("")}
          </select>
        </td>
        <td class="sz_table_cell"><input class="sz_input" data-field="NOME" type="text" value="${esc(variant.NOME || "")}"></td>
        <td class="sz_table_cell"><input class="sz_input" data-field="VALOR" type="text" value="${esc(variant.VALOR || "")}"></td>
        <td class="sz_table_cell"><input class="sz_input" data-field="PRECO" type="number" min="0" step="0.01" value="${esc(variant.PRECO ?? "")}"></td>
        <td class="sz_table_cell"><input class="sz_input" data-field="ORDEM" type="number" min="0" step="1" value="${esc(variant.ORDEM ?? 0)}"></td>
        <td class="sz_table_cell"><input type="radio" name="shopVariantDefault" ${variant.PADRAO ? "checked" : ""}></td>
        <td class="sz_table_cell"><input type="checkbox" data-field="ATIVO" ${variant.ATIVO !== false ? "checked" : ""}></td>
        <td class="sz_table_cell sz_text_right">
          <button type="button" class="sz_button sz_button_ghost shop-bo-row_button" data-action="remove-variant" data-index="${index}">
            <i class="fa-solid fa-trash"></i>
          </button>
        </td>
      </tr>
    `).join("");
  }

  function renderImages(images) {
    if (!images.length) {
      els.imagesGrid.innerHTML = '<div class="shop-bo-empty">Sem imagens.</div>';
      return;
    }
    els.imagesGrid.innerHTML = images.map((image) => `
      <div class="shop-bo-image_card" data-image-id="${image.PRODUTO_IMAGEM_ID}">
        <div class="shop-bo-image_preview">${image.URL ? `<img src="${esc(image.URL)}" alt="${esc(image.ALT_TEXT || "")}">` : ""}</div>
        <div class="shop-bo-image_body">
          <input class="sz_input" data-field="ALT_TEXT" type="text" value="${esc(image.ALT_TEXT || "")}" placeholder="Alt text">
          <div class="shop-bo-form_grid">
            <div class="sz_field">
              <label class="sz_label">Ordem</label>
              <input class="sz_input" data-field="ORDEM" type="number" min="0" step="1" value="${esc(image.ORDEM ?? 0)}">
            </div>
            <label class="shop-bo-inline_check">
              <input data-field="E_PRINCIPAL" type="checkbox" ${image.E_PRINCIPAL ? "checked" : ""}>
              <span>Principal</span>
            </label>
          </div>
          <div class="shop-bo-inline_checks">
            <label class="shop-bo-inline_check">
              <input data-field="ATIVO" type="checkbox" ${image.ATIVO ? "checked" : ""}>
              <span>Ativa</span>
            </label>
          </div>
          <div class="shop-bo-upload_row">
            <button type="button" class="sz_button sz_button_secondary" data-action="save-image">Atualizar</button>
            <button type="button" class="sz_button sz_button_danger" data-action="delete-image">Remover</button>
          </div>
        </div>
      </div>
    `).join("");
  }

  function resetProductForm() {
    state.currentProduct = null;
    els.productTitle.textContent = "Novo artigo";
    els.productId.value = "";
    els.productCode.value = "";
    els.productName.value = "";
    els.productTitleInput.value = "";
    els.productSubtitle.value = "";
    els.productPrice.value = "";
    els.productOrder.value = "0";
    els.productDescriptionShort.value = "";
    els.productDescription.value = "";
    els.productActive.checked = true;
    els.productFamily.innerHTML = familyOptionsHtml(null);
    resetTranslationsForm();
    renderVariants([]);
    renderImages([]);
    els.imagesHint.textContent = "Guarda o artigo para poderes carregar imagens.";
    els.uploadImageBtn.disabled = true;
    setProductModalStatus("");
  }

  function fillProductForm(detail) {
    state.currentProduct = detail;
    const product = detail.product;
    els.productTitle.textContent = `Artigo #${product.PRODUTO_ID}`;
    els.productId.value = product.PRODUTO_ID;
    els.productCode.value = product.CODIGO || "";
    els.productName.value = product.NOME || "";
    els.productTitleInput.value = product.TITULO || "";
    els.productSubtitle.value = product.SUBTITULO || "";
    els.productPrice.value = product.PRECO ?? "";
    els.productOrder.value = product.ORDEM ?? 0;
    els.productDescriptionShort.value = product.DESCRICAO_CURTA || "";
    els.productDescription.value = product.DESCRICAO || "";
    els.productActive.checked = !!product.ATIVO;
    els.productFamily.innerHTML = familyOptionsHtml(product.FAMILIA_ID);
    fillTranslationsForm(product);
    renderVariants(detail.variants || []);
    renderImages(detail.images || []);
    els.imagesHint.textContent = "Carrega, reordena e marca a imagem principal.";
    els.uploadImageBtn.disabled = false;
    setProductModalStatus(`Stock atual calculado: ${Number(product.STOCK_ATUAL || 0).toLocaleString("pt-PT")}`);
  }

  function collectVariants() {
    return Array.from(els.variantsBody.querySelectorAll("tr.sz_table_row")).map((row) => ({
      TIPO_VARIANTE: row.querySelector('[data-field="TIPO_VARIANTE"]')?.value || "OUTRO",
      NOME: row.querySelector('[data-field="NOME"]')?.value || "",
      VALOR: row.querySelector('[data-field="VALOR"]')?.value || "",
      PRECO: row.querySelector('[data-field="PRECO"]')?.value || "",
      ORDEM: row.querySelector('[data-field="ORDEM"]')?.value || 0,
      PADRAO: !!row.querySelector('input[type="radio"]')?.checked,
      ATIVO: !!row.querySelector('[data-field="ATIVO"]')?.checked,
    })).filter((row) => row.NOME.trim() && row.VALOR.trim());
  }

  function collectProductPayload() {
    return {
      CODIGO: els.productCode.value,
      FAMILIA_ID: els.productFamily.value,
      NOME: els.productName.value,
      TITULO: els.productTitleInput.value,
      SUBTITULO: els.productSubtitle.value,
      DESCRICAO_CURTA: els.productDescriptionShort.value,
      DESCRICAO: els.productDescription.value,
      PRECO: els.productPrice.value,
      ORDEM: els.productOrder.value,
      ATIVO: els.productActive.checked,
      ...collectTranslationsPayload(),
      VARIANTES: collectVariants(),
    };
  }

  function familyPayload() {
    return {
      CODIGO: els.familyCode.value,
      NOME: els.familyName.value,
      TITULO: els.familyTitle.value,
      DESCRICAO: els.familyDescription.value,
      ORDEM: els.familyOrder.value,
      ATIVO: els.familyActive.checked,
    };
  }

  function fillFamilyForm(item = null) {
    els.familyId.value = item?.FAMILIA_ID || "";
    els.familyCode.value = item?.CODIGO || "";
    els.familyName.value = item?.NOME || "";
    els.familyTitle.value = item?.TITULO || "";
    els.familyDescription.value = item?.DESCRICAO || "";
    els.familyOrder.value = item?.ORDEM ?? 0;
    els.familyActive.checked = item ? !!item.ATIVO : true;
    setFamilyModalStatus("");
  }

  function renderFamiliesTable(items) {
    els.familiesBody.innerHTML = items.length
      ? items.map((item) => `
        <tr class="sz_table_row" data-family-id="${item.FAMILIA_ID}">
          <td class="sz_table_cell shop-bo-code">${item.FAMILIA_ID}</td>
          <td class="sz_table_cell shop-bo-code">${esc(item.CODIGO)}</td>
          <td class="sz_table_cell">${esc(item.NOME)}</td>
          <td class="sz_table_cell">${esc(item.TITULO || "")}</td>
          <td class="sz_table_cell sz_text_right">${item.ORDEM ?? 0}</td>
          <td class="sz_table_cell">${item.ATIVO ? badge("Ativa", "success") : badge("Inativa", "warning")}</td>
        </tr>
      `).join("")
      : '<tr class="sz_table_row"><td colspan="6" class="sz_table_cell sz_text_muted">Sem familias.</td></tr>';
  }

  async function loadMeta() {
    const data = await api("/api/shop/meta");
    state.meta = data.meta;
    state.families = data.meta.families || [];
    populateFamilySelectors();
  }

  async function loadFamilies() {
    const data = await api("/api/shop/familias");
    state.families = data.items || [];
    populateFamilySelectors(Number(els.productFamily.value || 0));
    renderFamiliesTable(state.families);
  }

  async function loadProducts() {
    setStatus("A carregar catalogo...");
    els.familyFilter.dataset.currentValue = els.familyFilter.value;
    const data = await api(`/api/shop/artigos?${collectFilters()}`);
    state.products = data.items || [];
    renderProducts(state.products, data.summary || {});
    setStatus(`${data.count || 0} artigo(s) encontrados.`);
  }

  async function openProduct(productId) {
    setProductModalStatus("A carregar artigo...");
    const detail = await api(`/api/shop/artigos/${productId}`);
    fillProductForm(detail);
    productModal.show();
  }

  async function saveCurrentProduct() {
    const productId = els.productId.value;
    const payload = collectProductPayload();
    setProductModalStatus("A gravar...");
    const detail = productId
      ? await api(`/api/shop/artigos/${productId}`, {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        })
      : await api("/api/shop/artigos", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
    fillProductForm(detail);
    await loadProducts();
    setProductModalStatus("Artigo gravado com sucesso.");
  }

  async function autoTranslateCurrentProduct() {
    setTranslationsStatus("A traduzir automaticamente...");
    const data = await api("/api/shop/artigos/traducoes/auto", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        NOME: els.productName.value,
        TITULO: els.productTitleInput.value,
        SUBTITULO: els.productSubtitle.value,
        DESCRICAO_CURTA: els.productDescriptionShort.value,
        DESCRICAO: els.productDescription.value,
      }),
    });
    fillTranslationsForm(data.translations || {});
    setTranslationsStatus("Traducoes preenchidas. Revê antes de gravar o artigo.");
  }

  async function uploadCurrentImage() {
    const productId = els.productId.value;
    if (!productId) {
      setProductModalStatus("Guarda o artigo antes de carregar imagens.", "danger");
      return;
    }
    const file = els.imageFile.files?.[0];
    if (!file) {
      setProductModalStatus("Seleciona um ficheiro de imagem.", "danger");
      return;
    }
    const formData = new FormData();
    formData.append("file", file);
    formData.append("alt_text", els.imageAltText.value || "");
    setProductModalStatus("A carregar imagem...");
    const detail = await api(`/api/shop/artigos/${productId}/imagens`, {
      method: "POST",
      body: formData,
    });
    fillProductForm(detail);
    els.imageFile.value = "";
    els.imageAltText.value = "";
    await loadProducts();
    setProductModalStatus("Imagem carregada.");
  }

  async function saveImageCard(card) {
    const productId = els.productId.value;
    const imageId = card.dataset.imageId;
    const payload = {
      ALT_TEXT: card.querySelector('[data-field="ALT_TEXT"]')?.value || "",
      ORDEM: card.querySelector('[data-field="ORDEM"]')?.value || 0,
      ATIVO: !!card.querySelector('[data-field="ATIVO"]')?.checked,
      E_PRINCIPAL: !!card.querySelector('[data-field="E_PRINCIPAL"]')?.checked,
    };
    setProductModalStatus("A atualizar imagem...");
    const detail = await api(`/api/shop/artigos/${productId}/imagens/${imageId}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    fillProductForm(detail);
    await loadProducts();
    setProductModalStatus("Imagem atualizada.");
  }

  async function deleteImageCard(card) {
    const productId = els.productId.value;
    const imageId = card.dataset.imageId;
    setProductModalStatus("A remover imagem...");
    const detail = await api(`/api/shop/artigos/${productId}/imagens/${imageId}`, {
      method: "DELETE",
    });
    fillProductForm(detail);
    await loadProducts();
    setProductModalStatus("Imagem removida.");
  }

  async function saveFamilyForm() {
    const id = els.familyId.value;
    const payload = familyPayload();
    setFamilyModalStatus("A gravar familia...");
    const data = id
      ? await api(`/api/shop/familias/${id}`, {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        })
      : await api("/api/shop/familias", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });
    fillFamilyForm(data.item);
    await loadFamilies();
    setFamilyModalStatus("Familia gravada.");
  }

  els.refresh.addEventListener("click", () => loadProducts().catch((error) => setStatus(error.message, "danger")));
  els.newBtn.addEventListener("click", () => {
    resetProductForm();
    productModal.show();
  });
  els.familyBtn.addEventListener("click", async () => {
    await loadFamilies().catch((error) => setFamilyModalStatus(error.message, "danger"));
    fillFamilyForm();
    familiesModal.show();
  });
  els.openFamiliesFromProduct.addEventListener("click", async () => {
    await loadFamilies().catch((error) => setFamilyModalStatus(error.message, "danger"));
    familiesModal.show();
  });
  els.productTranslationsBtn.addEventListener("click", () => {
    translationsModal.show();
  });
  els.addVariantBtn.addEventListener("click", () => {
    const current = collectVariants();
    current.push(emptyVariantRow());
    renderVariants(current);
  });
  els.saveProduct.addEventListener("click", () => saveCurrentProduct().catch((error) => setProductModalStatus(error.message, "danger")));
  els.autoTranslateBtn.addEventListener("click", () => autoTranslateCurrentProduct().catch((error) => setTranslationsStatus(error.message, "danger")));
  els.uploadImageBtn.addEventListener("click", () => uploadCurrentImage().catch((error) => setProductModalStatus(error.message, "danger")));
  els.saveFamilyBtn.addEventListener("click", () => saveFamilyForm().catch((error) => setFamilyModalStatus(error.message, "danger")));
  els.newFamilyBtn.addEventListener("click", () => fillFamilyForm());

  els.search.addEventListener("input", () => {
    clearTimeout(els.search._timer);
    els.search._timer = setTimeout(() => loadProducts().catch((error) => setStatus(error.message, "danger")), 250);
  });
  [els.familyFilter, els.activeFilter, els.sort].forEach((input) => {
    input.addEventListener("change", () => loadProducts().catch((error) => setStatus(error.message, "danger")));
  });

  els.tableBody.addEventListener("click", (event) => {
    const button = event.target.closest('[data-action="edit"]');
    if (!button) return;
    openProduct(button.dataset.id).catch((error) => setStatus(error.message, "danger"));
  });

  els.variantsBody.addEventListener("click", (event) => {
    const button = event.target.closest('[data-action="remove-variant"]');
    if (!button) return;
    const current = collectVariants();
    current.splice(Number(button.dataset.index), 1);
    renderVariants(current);
  });

  els.imagesGrid.addEventListener("click", (event) => {
    const card = event.target.closest(".shop-bo-image_card");
    if (!card) return;
    const action = event.target.closest("[data-action]");
    if (!action) return;
    if (action.dataset.action === "save-image") {
      saveImageCard(card).catch((error) => setProductModalStatus(error.message, "danger"));
    }
    if (action.dataset.action === "delete-image") {
      deleteImageCard(card).catch((error) => setProductModalStatus(error.message, "danger"));
    }
  });

  els.familiesBody.addEventListener("click", (event) => {
    const row = event.target.closest("[data-family-id]");
    if (!row) return;
    const item = state.families.find((family) => Number(family.FAMILIA_ID) === Number(row.dataset.familyId));
    if (item) fillFamilyForm(item);
  });

  (async () => {
    try {
      await loadMeta();
      await loadFamilies();
      await loadProducts();
    } catch (error) {
      setStatus(error.message, "danger");
    }
  })();
});
