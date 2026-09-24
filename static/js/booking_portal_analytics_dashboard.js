(function () {
  "use strict";
  const root = document.getElementById("pbAnalyticsDashboard");
  if (!root) return;
  const $ = (selector, scope) => (scope || root).querySelector(selector);
  const n = new Intl.NumberFormat("pt-PT");
  const d = new Intl.NumberFormat("pt-PT", { maximumFractionDigits: 1 });
  const dateFormat = new Intl.DateTimeFormat("pt-PT", { day: "2-digit", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" });
  const names = typeof Intl.DisplayNames === "function" ? new Intl.DisplayNames(["pt"], { type: "region" }) : null;
  const sourceLabels = { direct: "Direto", search: "Motores de pesquisa", social: "Redes sociais", referral: "Outros sites", unknown: "Sem referência" };
  const deviceLabels = { desktop: "Desktop", mobile: "Mobile", tablet: "Tablet", unknown: "Desconhecido" };
  const classLabels = { HUMAN: "Humano", LIKELY_HUMAN: "Provavelmente humano", SUSPECTED_BOT: "Suspeito", BOT: "Bot", UNKNOWN: "Não atribuível", LEGACY: "Histórico (legacy)" };
  let controller;
  function value(v) { return v === null || v === undefined ? "—" : n.format(v); }
  function seconds(v) { if (v === null || v === undefined) return "Não medido"; const s = Math.max(0, Number(v) || 0); return s >= 60 ? `${Math.floor(s / 60)} min ${Math.round(s % 60)} s` : `${Math.round(s)} s`; }
  function percent(v) { return v === null || v === undefined ? "—" : `${d.format(v)}%`; }
  function country(code) { try { return code === "ZZ" ? "Desconhecido" : names ? names.of(code) : code; } catch (_) { return code; } }
  function make(tag, cls, content) { const el = document.createElement(tag); if (cls) el.className = cls; if (content !== undefined) el.textContent = content; return el; }
  function status(message, error) { const el = $("#pbAnalyticsStatus"); if (!el) return; el.textContent = message || ""; el.classList.toggle("is-visible", !!message); el.classList.toggle("is-error", !!error); }
  function ranked(selector, items, label) {
    const host = $(selector); if (!host) return; host.replaceChildren();
    if (!items || !items.length) { host.appendChild(make("p", "pb-card-footnote", "Sem dados suficientes neste filtro.")); return; }
    const top = Math.max(...items.map(x => Number(x.value) || 0), 1);
    items.forEach(item => { const row = make("div", "pb-rank-item"); row.append(make("span", "pb-rank-label", label ? label(item) : item.label), make("span", "pb-rank-value", `${value(item.value)} · ${percent(item.share)}`)); const bar = make("span", "pb-rank-bar"); const fill = make("span"); fill.style.width = `${Math.max(2, (Number(item.value) || 0) / top * 100)}%`; bar.appendChild(fill); row.appendChild(bar); host.appendChild(row); });
  }
  function appendCell(row, content, label) { const cell = make("td", "", content); if (label) cell.dataset.label = label; row.appendChild(cell); return cell; }
  function properties(items) { const body = $("#pbPropertyRows"); if (!body) return; body.replaceChildren(); if (!items.length) { const row = make("tr"); const cell = appendCell(row, "Ainda sem visualizações qualificadas neste período."); cell.colSpan = 5; body.appendChild(row); return; } items.forEach(item => { const row = make("tr"); appendCell(row, item.name, "Alojamento"); appendCell(row, value(item.views), "Pageviews"); appendCell(row, seconds(item.active_seconds), "Tempo ativo"); appendCell(row, value(item.bookings), "Reservas"); appendCell(row, percent(item.conversion_rate), "Conversão"); body.appendChild(row); }); }
  function sessionRows(items) { const body = $("#pbSessionRows"); if (!body) return; body.replaceChildren(); if (!items.length) { const row = make("tr"); const cell = appendCell(row, "Ainda sem sessões consentidas neste filtro."); cell.colSpan = 8; body.appendChild(row); return; } items.forEach(item => { const row = make("tr"); appendCell(row, item.started_at ? dateFormat.format(new Date(item.started_at)) : "—", "Início"); appendCell(row, sourceLabels[item.source] || item.source || "Desconhecida", "Origem"); appendCell(row, country(item.country), "País"); appendCell(row, deviceLabels[item.device] || item.device, "Dispositivo"); appendCell(row, `${item.browser} · ${item.os}`, "Cliente"); appendCell(row, value(item.page_views), "Páginas"); appendCell(row, seconds(item.active_seconds), "Tempo ativo"); appendCell(row, classLabels[item.traffic_class] || item.traffic_class, "Qualidade"); body.appendChild(row); }); }
  function funnel(items) { const host = $("#pbFunnelList"); if (!host) return; host.replaceChildren(); (items || []).forEach(item => { const row = make("div", "pb-rank-item"); row.append(make("span", "pb-rank-label", item.label), make("span", "pb-rank-value", `${value(item.value)}${item.rate === null ? "" : ` · ${percent(item.rate)}`}`)); host.appendChild(row); }); }
  function diagnostics(items) { const host = $("#pbDiagnosticsRows"); if (!host) return; host.replaceChildren(); if (!items.length) { host.appendChild(make("p", "pb-card-footnote", "Sem tráfego suspeito ou bot neste período.")); return; } items.slice(0, 20).forEach(item => { const row = make("div", "pb-diagnostic-row"); row.append(make("strong", "", classLabels[item.traffic_class] || item.traffic_class), make("span", "", `${item.reason || "sem razão"} · ${country(item.country)}`), make("span", "", item.requests === null ? `${item.pages} páginas · ${seconds(item.active_seconds)}` : `${value(item.requests)} requests · ${item.pages}`)); host.appendChild(row); }); }
  function render(data) {
    root.querySelectorAll("[data-kpi]").forEach(el => el.textContent = el.dataset.kpi === "average_active_seconds" ? seconds(data.kpis[el.dataset.kpi]) : value(data.kpis[el.dataset.kpi]));
    const note = $("[data-kpi-note='pageviews_per_session']"); if (note) note.textContent = data.kpis.pageviews_per_session === null ? "por sessão" : `${d.format(data.kpis.pageviews_per_session)} por sessão`;
    ranked("#pbSourceList", data.sources, item => sourceLabels[item.key] || item.label);
    ranked("#pbCountryList", data.countries, item => country(item.key)); ranked("#pbDeviceList", data.devices, item => deviceLabels[item.key] || item.label);
    ranked("#pbBrowserList", data.browsers); ranked("#pbOsList", data.operating_systems); ranked("#pbLanguageList", data.languages);
    ranked("#pbPageList", data.pages); ranked("#pbCheckinMonthList", []);
    properties(data.properties); sessionRows(data.recent_sessions); funnel(data.funnel); diagnostics(data.traffic_quality.diagnostics);
    const request = $("#pbTechnicalRequests"); if (request) request.textContent = `${value(data.kpis.requests)} requests técnicos não atribuíveis a pessoas.`;
    const quality = $("#pbTrafficQuality"); if (quality) quality.textContent = (data.traffic_quality.request_classes || []).map(x => `${classLabels[x.key] || x.key}: ${value(x.value)}`).join(" · ") || "Sem requests.";
    const unknown = $("#pbUnknownCountry"); if (unknown) unknown.textContent = `${value(data.data_quality.unknown_country_sessions)} sessão(ões) sem país determinado.`;
    const retention = $("#pbRetention"); if (retention) retention.textContent = `${data.data_quality.granular_retention_days} dias para detalhe; ${data.data_quality.aggregate_retention_days} dias para requests agregados.`;
  }
  function params() { return new URLSearchParams({ start: $("#pbAnalyticsStart").value, end: $("#pbAnalyticsEnd").value, traffic: $("#pbTrafficFilter").value, include_validation: $("#pbIncludeValidation").checked ? "1" : "0" }); }
  async function load() { if (controller) controller.abort(); controller = new AbortController(); status("A atualizar a analítica…"); try { const response = await fetch(`${root.dataset.apiUrl}?${params()}`, { credentials: "same-origin", headers: { Accept: "application/json" }, signal: controller.signal }); const payload = await response.json(); if (!response.ok || !payload.ok) throw new Error(payload.error || "Não foi possível carregar os dados."); render(payload.data); const url = new URL(location.href); url.search = params(); history.replaceState({}, "", url); status(""); } catch (error) { if (error.name !== "AbortError") status(error.message || "Não foi possível carregar os dados.", true); } }
  $("#pbAnalyticsFilters").addEventListener("submit", event => { event.preventDefault(); load(); });
  [$("#pbTrafficFilter"), $("#pbIncludeValidation")].forEach(el => el && el.addEventListener("change", load));
  root.querySelectorAll(".pb-period-button").forEach(button => button.addEventListener("click", () => { const end = new Date(), start = new Date(end); start.setDate(end.getDate() - Number(button.dataset.days) + 1); const iso = x => `${x.getFullYear()}-${String(x.getMonth() + 1).padStart(2, "0")}-${String(x.getDate()).padStart(2, "0")}`; $("#pbAnalyticsStart").value = iso(start); $("#pbAnalyticsEnd").value = iso(end); load(); }));
  load();
})();
