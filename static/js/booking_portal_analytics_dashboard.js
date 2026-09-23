(function () {
  "use strict";

  const root = document.getElementById("pbAnalyticsDashboard");
  if (!root) return;

  const $ = (selector, scope) => (scope || root).querySelector(selector);
  const numberFormat = new Intl.NumberFormat("pt-PT");
  const decimalFormat = new Intl.NumberFormat("pt-PT", { maximumFractionDigits: 1 });
  const dateFormat = new Intl.DateTimeFormat("pt-PT", { day: "2-digit", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" });
  const monthFormat = new Intl.DateTimeFormat("pt-PT", { month: "short", year: "numeric", timeZone: "UTC" });
  const countryNames = typeof Intl.DisplayNames === "function" ? new Intl.DisplayNames(["pt"], { type: "region" }) : null;
  const sourceLabels = { direct: "Direto", search: "Motores de pesquisa", social: "Redes sociais", referral: "Outros sites", internal: "Navegação interna", google: "Google", bing: "Bing", facebook: "Facebook", instagram: "Instagram", newsletter: "Newsletter", unknown: "Sem referência" };
  const deviceLabels = { desktop: "Desktop", mobile: "Mobile", tablet: "Tablet", bot: "Bot", unknown: "Desconhecido" };
  const languageLabels = { pt: "Português", en: "Inglês", es: "Espanhol", fr: "Francês", unknown: "Desconhecido" };
  const colors = ["#2f5da8", "#ff6b18", "#188d56", "#8b5cf6", "#1f7ab8", "#b77a12"];

  let chart = null;
  let requestController = null;

  function formatNumber(value) {
    return value === null || value === undefined ? "—" : numberFormat.format(value);
  }

  function formatPercent(value) {
    return value === null || value === undefined ? "—" : `${decimalFormat.format(value)}%`;
  }

  function formatSeconds(value) {
    if (value === null || value === undefined) return "—";
    const seconds = Math.max(0, Math.round(Number(value) || 0));
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const rest = seconds % 60;
    if (hours) return `${hours} h ${minutes} min`;
    if (minutes) return `${minutes} min ${rest} s`;
    return `${rest} s`;
  }

  function formatDate(value) {
    if (!value) return "—";
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? "—" : dateFormat.format(date);
  }

  function countryLabel(code) {
    const clean = String(code || "ZZ").toUpperCase();
    if (clean === "ZZ") return "Desconhecido";
    try { return countryNames ? countryNames.of(clean) : clean; } catch (_) { return clean; }
  }

  function monthLabel(value) {
    const parts = String(value || "").split("-");
    if (parts.length !== 2) return value || "Desconhecido";
    return monthFormat.format(new Date(Date.UTC(Number(parts[0]), Number(parts[1]) - 1, 1)));
  }

  function localIsoDate(date) {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, "0");
    const day = String(date.getDate()).padStart(2, "0");
    return `${year}-${month}-${day}`;
  }

  function setStatus(message, isError) {
    const node = $("#pbAnalyticsStatus");
    node.textContent = message || "";
    node.classList.toggle("is-visible", Boolean(message));
    node.classList.toggle("is-error", Boolean(isError));
  }

  function create(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  }

  function renderRankedList(selector, items, options) {
    const host = $(selector);
    const settings = options || {};
    host.replaceChildren();
    const max = Math.max(1, ...items.map((item) => Number(item.value) || 0));
    items.forEach((item) => {
      const row = create("div", "pb-rank-item");
      const label = settings.label ? settings.label(item) : item.label;
      row.appendChild(create("span", "pb-rank-label", label || "Desconhecido"));
      const value = create("span", "pb-rank-value", `${formatNumber(item.value)} · ${formatPercent(item.share)}`);
      if (settings.meta) {
        const meta = settings.meta(item);
        if (meta) value.appendChild(create("span", "pb-rank-meta", `  ${meta}`));
      }
      row.appendChild(value);
      const bar = create("span", "pb-rank-bar");
      const fill = create("span");
      fill.style.width = `${Math.max(2, ((Number(item.value) || 0) / max) * 100)}%`;
      bar.appendChild(fill);
      row.appendChild(bar);
      host.appendChild(row);
    });
  }

  function renderKpis(kpis) {
    root.querySelectorAll("[data-kpi]").forEach((node) => {
      const key = node.dataset.kpi;
      node.textContent = key === "average_active_seconds" ? formatSeconds(kpis[key]) : formatNumber(kpis[key]);
    });
    root.querySelectorAll("[data-kpi-percent]").forEach((node) => {
      node.textContent = formatPercent(kpis[node.dataset.kpiPercent]);
    });
    $("[data-kpi-note='pageviews_per_session']").textContent = `${decimalFormat.format(kpis.pageviews_per_session || 0)} por sessão`;
    $("[data-kpi-note='session_conversion_rate']").textContent = `${formatPercent(kpis.session_conversion_rate)} das sessões`;
    $("[data-kpi-note='payment_rate']").textContent = `${formatPercent(kpis.payment_rate)} dos pedidos`;
  }

  function renderTimeline(items) {
    const canvas = $("#pbTimelineChart");
    if (!canvas) return;
    if (!window.Chart) {
      canvas.hidden = true;
      if (!$("#pbTimelineFallback")) {
        const fallback = create("p", "pb-card-footnote", "O gráfico não ficou disponível. Os restantes indicadores mantêm-se atualizados.");
        fallback.id = "pbTimelineFallback";
        canvas.parentElement.appendChild(fallback);
      }
      return;
    }
    if (chart) chart.destroy();
    const styles = getComputedStyle(root);
    chart = new window.Chart(canvas, {
      type: "line",
      data: {
        labels: items.map((item) => new Intl.DateTimeFormat("pt-PT", { day: "2-digit", month: "short", timeZone: "UTC" }).format(new Date(`${item.date}T00:00:00Z`))),
        datasets: [
          { label: "Visitas", data: items.map((item) => item.visits), borderColor: "#2f5da8", backgroundColor: "rgba(47,93,168,.1)", fill: true, tension: .32, pointRadius: items.length > 45 ? 0 : 2, borderWidth: 2 },
          { label: "Sessões consentidas", data: items.map((item) => item.sessions), borderColor: "#ff6b18", backgroundColor: "transparent", tension: .32, pointRadius: items.length > 45 ? 0 : 2, borderWidth: 2 },
          { label: "Reservas pagas", data: items.map((item) => item.paid), borderColor: "#188d56", backgroundColor: "transparent", tension: .32, pointRadius: 2, borderWidth: 2 }
        ]
      },
      options: {
        maintainAspectRatio: false,
        responsive: true,
        interaction: { intersect: false, mode: "index" },
        plugins: { legend: { display: false }, tooltip: { padding: 10 } },
        scales: {
          x: { grid: { display: false }, ticks: { color: styles.getPropertyValue("--sz-color-text-muted"), maxTicksLimit: 10, font: { size: 10 } } },
          y: { beginAtZero: true, ticks: { precision: 0, color: styles.getPropertyValue("--sz-color-text-muted"), font: { size: 10 } }, grid: { color: styles.getPropertyValue("--sz-color-border") } }
        }
      }
    });
  }

  function renderDeviceDonut(items) {
    const host = $("#pbDeviceDonut");
    const total = items.reduce((sum, item) => sum + (Number(item.value) || 0), 0);
    let cursor = 0;
    const stops = [];
    items.slice(0, colors.length).forEach((item, index) => {
      const end = cursor + (total ? (Number(item.value) / total) * 100 : 0);
      stops.push(`${colors[index]} ${cursor}% ${end}%`);
      cursor = end;
    });
    if (cursor < 100) stops.push(`var(--sz-color-border) ${cursor}% 100%`);
    host.style.background = `conic-gradient(${stops.join(",")})`;
    $("span", host).textContent = formatNumber(total);
  }

  function appendCell(row, value, className, label) {
    const cell = create("td", className, value);
    if (label) cell.dataset.label = label;
    row.appendChild(cell);
    return cell;
  }

  function renderProperties(items) {
    const body = $("#pbPropertyRows");
    body.replaceChildren();
    if (!items.length) {
      const row = create("tr");
      const cell = appendCell(row, "Ainda sem visualizações de alojamentos neste período.", "pb-table-empty");
      cell.colSpan = 6;
      body.appendChild(row);
      return;
    }
    items.forEach((item) => {
      const row = create("tr");
      appendCell(row, item.name, "", "Alojamento");
      appendCell(row, formatNumber(item.views), "", "Visualizações");
      appendCell(row, formatSeconds(item.active_seconds), "", "Tempo ativo");
      appendCell(row, formatNumber(item.bookings), "", "Pedidos");
      appendCell(row, formatNumber(item.paid), "", "Pagas");
      appendCell(row, formatPercent(item.conversion_rate), "", "Conversão");
      body.appendChild(row);
    });
  }

  function sessionSource(item) {
    const bits = [sourceLabels[item.source] || item.source || "Desconhecida"];
    if (item.medium) bits.push(item.medium);
    if (item.campaign) bits.push(item.campaign);
    return bits.join(" · ");
  }

  function renderSessions(items) {
    const body = $("#pbSessionRows");
    body.replaceChildren();
    if (!items.length) {
      const row = create("tr");
      const cell = appendCell(row, "Ainda sem sessões consentidas neste período.", "pb-table-empty");
      cell.colSpan = 8;
      body.appendChild(row);
      return;
    }
    items.forEach((item) => {
      const row = create("tr");
      appendCell(row, formatDate(item.started_at), "", "Início");
      appendCell(row, sessionSource(item), "", "Origem");
      appendCell(row, countryLabel(item.country), "", "País");
      appendCell(row, deviceLabels[item.device] || item.device, "", "Dispositivo");
      appendCell(row, [item.browser, item.os].filter(Boolean).join(" · "), "", "Browser");
      appendCell(row, formatNumber(item.page_views), "", "Páginas");
      appendCell(row, formatSeconds(item.active_seconds), "", "Tempo ativo");
      const result = appendCell(row, "", "", "Resultado");
      const chip = create("span", `pb-status-chip${item.paid ? " is-paid" : item.converted ? " is-converted" : ""}`, item.paid ? "Paga" : item.converted ? "Pedido" : "Navegação");
      result.appendChild(chip);
      body.appendChild(row);
    });
  }

  function render(data) {
    renderKpis(data.kpis);
    renderTimeline(data.timeline);
    renderRankedList("#pbSourceList", data.sources, {
      label: (item) => sourceLabels[item.key] || item.label,
      meta: (item) => `${formatNumber(item.sessions)} sessão(ões)${item.conversions ? ` · ${formatNumber(item.conversions)} pedido(s)` : ""}`
    });
    renderRankedList("#pbCountryList", data.countries, { label: (item) => countryLabel(item.key) });
    renderRankedList("#pbDeviceList", data.devices, { label: (item) => deviceLabels[item.key] || item.label });
    renderRankedList("#pbBrowserList", data.browsers);
    renderRankedList("#pbOsList", data.operating_systems);
    renderRankedList("#pbLanguageList", data.languages, { label: (item) => languageLabels[item.key] || item.label });
    renderRankedList("#pbPageList", data.pages, { meta: (item) => formatSeconds(item.active_seconds) });
    renderRankedList("#pbCheckinMonthList", data.searches.checkin_months, { label: (item) => monthLabel(item.key) });
    renderDeviceDonut(data.devices);

    $("#pbSearchAccesses").textContent = formatNumber(data.searches.accesses_with_search);
    $("#pbSearchWithDates").textContent = formatNumber(data.searches.pageviews_with_dates);
    $("#pbSearchNights").textContent = data.searches.average_nights === null ? "—" : decimalFormat.format(data.searches.average_nights);
    $("#pbSearchGuests").textContent = data.searches.average_guests === null ? "—" : decimalFormat.format(data.searches.average_guests);
    $("#pbSearchText").textContent = formatNumber(data.searches.pageviews_with_text_query);

    renderProperties(data.properties);
    renderSessions(data.recent_sessions);

    const unknown = data.data_quality.unknown_country_accesses;
    $("#pbUnknownCountry").textContent = `${formatNumber(unknown)} acesso(s) sem país determinado.`;
    $("#pbRetention").textContent = `${data.data_quality.granular_retention_days} dias para detalhe; ${data.data_quality.aggregate_retention_days} dias para totais agregados.`;
  }

  function currentParams() {
    return new URLSearchParams({
      start: $("#pbAnalyticsStart").value,
      end: $("#pbAnalyticsEnd").value,
      include_bots: $("#pbIncludeBots").checked ? "1" : "0",
      include_validation: $("#pbIncludeValidation").checked ? "1" : "0"
    });
  }

  async function loadDashboard() {
    if (requestController) requestController.abort();
    requestController = new AbortController();
    setStatus("A atualizar a analítica…", false);
    const params = currentParams();
    const url = `${root.dataset.apiUrl}?${params.toString()}`;
    try {
      const response = await fetch(url, { credentials: "same-origin", signal: requestController.signal, headers: { Accept: "application/json" } });
      const payload = await response.json();
      if (!response.ok || !payload.ok) throw new Error(payload.error || "Não foi possível carregar os dados.");
      render(payload.data);
      const browserUrl = new URL(window.location.href);
      browserUrl.search = params.toString();
      window.history.replaceState({}, "", browserUrl);
      setStatus("", false);
    } catch (error) {
      if (error.name === "AbortError") return;
      setStatus(error.message || "Não foi possível carregar os dados.", true);
    }
  }

  $("#pbAnalyticsFilters").addEventListener("submit", (event) => { event.preventDefault(); loadDashboard(); });
  $("#pbAnalyticsAdvancedToggle").addEventListener("click", (event) => {
    const panel = $("#pbAnalyticsAdvanced");
    panel.hidden = !panel.hidden;
    event.currentTarget.setAttribute("aria-expanded", String(!panel.hidden));
  });
  [$("#pbIncludeBots"), $("#pbIncludeValidation")].forEach((node) => node.addEventListener("change", loadDashboard));
  root.querySelectorAll(".pb-period-button").forEach((button) => button.addEventListener("click", () => {
    const end = new Date();
    const start = new Date(end);
    start.setDate(end.getDate() - Number(button.dataset.days) + 1);
    $("#pbAnalyticsStart").value = localIsoDate(start);
    $("#pbAnalyticsEnd").value = localIsoDate(end);
    root.querySelectorAll(".pb-period-button").forEach((item) => item.classList.toggle("is-active", item === button));
    loadDashboard();
  }));

  loadDashboard();
})();
