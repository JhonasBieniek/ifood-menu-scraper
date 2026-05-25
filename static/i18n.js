/**
 * i18n — pt-BR (default) e English
 */
const I18n = (() => {
  const STORAGE_KEY = "ifood-migrator-lang";
  const DEFAULT_LOCALE = "pt-BR";

  const messages = {
    "pt-BR": {
      "page.title": "iFood Migrator",
      "eyebrow": "Extrator de cardápio",
      "subtitle":
        "Extraia o cardápio completo de uma loja iFood em JSON — pela interface ou pela API REST.",
      "lang.label": "Idioma",
      "lang.pt": "Português",
      "lang.en": "English",
      "meta.strategy": "Estratégia: {value}",
      "meta.jobs": "Jobs: {active}/{max}",
      "tab.nav.aria": "Seções",
      "tab.extract": "Extração",
      "tab.history": "Histórico",
      "tab.api": "API e uso",
      "steps.aria": "Como usar na interface",
      "step.1": "Cole a URL da loja no iFood",
      "step.2": "Inicie a migração e acompanhe o progresso",
      "step.3": "Copie ou baixe o JSON do cardápio",
      "panel.newExtraction": "Nova extração",
      "label.url": "URL da loja (iFood)",
      "placeholder.url": "https://www.ifood.com.br/delivery/cidade/loja/uuid",
      "label.apiKey": "Chave de API",
      "label.apiKeyHint": "(obrigatória no servidor)",
      "placeholder.apiKey": "Cole o valor de API_KEY do .env",
      "btn.start": "Iniciar migração",
      "btn.cancel": "Cancelar",
      "btn.clear": "Limpar",
      "progress.aria": "Log de progresso",
      "panel.resultJson": "Resultado JSON",
      "btn.copy": "Copiar",
      "btn.download": "Baixar .json",
      "json.waiting": "Aguardando migração…",
      "json.starting": "Iniciando…",
      "json.cancelledByUser": "Cancelado pelo usuário",
      "json.scrapeError": "Erro no scraping",
      "json.noDetails": "Sem detalhes",
      "history.title": "Histórico de scrapings",
      "history.desc":
        "Consultas persistidas no SQLite local. Reabra, cancele jobs ativos ou remova registros.",
      "btn.refresh": "Atualizar",
      "th.store": "Loja",
      "th.status": "Status",
      "th.date": "Data",
      "th.actions": "Ações",
      "history.loading": "Carregando…",
      "history.empty": "Nenhum scraping ainda",
      "history.errorLoad": "Erro ao carregar histórico ({status})",
      "history.networkFail": "Falha de rede: {message}",
      "action.viewJson": "Ver JSON",
      "action.cancel": "Cancelar",
      "action.delete": "Apagar",
      "api.title": "Integração via API REST",
      "api.intro":
        'Todos os endpoints abaixo são assíncronos: você inicia um job com <code>POST /api/migrate</code>, acompanha com <strong>SSE</strong> ou <strong>polling</strong>, e obtém o JSON quando <code>status</code> for <code>done</code>. Documentação interativa em <a href="/docs" target="_blank" rel="noopener">/docs</a> (OpenAPI).',
      "api.note.baseUrl": "Base URL desta instância:",
      "api.note.authOff":
        'Autenticação: desativada — defina <code>API_KEY</code> no <code>.env</code> para exigir o header <code>X-Api-Key</code>.',
      "api.note.authOn":
        "Autenticação: ativa — envie o header <code>X-Api-Key</code> em rotas protegidas (exceto <code>/api/health</code>).",
      "api.note.header": "Header quando autenticação ativa:",
      "api.note.headerValue": "X-Api-Key: sua-chave",
      "api.note.timeout":
        "Timeout padrão do scraping: configurável via <code>SCRAPE_TIMEOUT_S</code> no servidor",
      "api.ep.migrate.desc":
        "Inicia extração. Resposta <strong>202</strong> com <code>job_id</code>, URLs de status, eventos SSE e cancelamento.",
      "api.ep.status.desc":
        "Polling do job: <code>status</code>, <code>progress</code>, <code>result</code> (quando concluído) ou <code>error</code>.",
      "api.ep.sse.desc":
        'Stream em tempo real. Eventos: <code>progress</code>, <code>done</code>, <code>error</code>, <code>cancelled</code>. A interface web usa <code>EventSource</code> neste endpoint.',
      "api.ep.cancel.desc": "Cancela job em <code>pending</code> ou <code>running</code>.",
      "api.ep.list.desc":
        "Lista histórico. Query: <code>limit</code>, <code>offset</code>, <code>status</code> (pending, running, done, error, cancelled).",
      "api.ep.detail.desc": "Detalhe de um scraping (mesmo formato do polling de migrate).",
      "api.ep.delete.desc": "Remove do histórico. Se ainda estiver ativo, cancela antes de apagar.",
      "api.ep.health.desc":
        "Health check público (sem API key). Retorna estratégia, jobs ativos e estatísticas.",
      "btn.copyCurl": "Copiar cURL",
      "btn.copyExample": "Copiar exemplo",
      "api.flow.summary": "Fluxo recomendado (polling)",
      "api.flow.1": "<code>POST /api/migrate</code> com a URL da loja → guarde <code>job_id</code>",
      "api.flow.2":
        "Em loop: <code>GET /api/migrate/{job_id}</code> a cada 2–5 s até status terminal",
      "api.flow.3": "Se <code>done</code>, use o campo <code>result</code> como JSON do cardápio",
      "api.flow.4":
        "Para UX em tempo real, prefira SSE em <code>events_url</code> em vez de polling agressivo",
      "api.flow.ngrok":
        'Expondo via ngrok: defina <code>API_KEY</code> no <code>.env</code> e envie <code>X-Api-Key</code> em todas as rotas protegidas (exceto <code>/api/health</code> e SSE de eventos).',
      "footer.brand": "iFood Migrator",
      "footer.openapi": "OpenAPI /docs",
      "status.urlRequired": "Informe a URL da loja.",
      "status.apiKeyRequired": "Informe a API Key (obrigatória neste servidor).",
      "status.sending": "Enviando solicitação…",
      "status.jobProgress": "Job {id} — aguardando progresso…",
      "status.migrationDone": "Migração concluída.",
      "status.sseFailed": "Conexão SSE encerrada ou falhou.",
      "status.cancelled": "Consulta cancelada.",
      "status.scrapeError": "Scraping com erro",
      "status.loaded": "Carregado: {name}",
      "status.jobStatus": "Status: {status}",
      "status.jobLoadError": "Erro ao carregar job: {status}",
      "status.removed": "Consulta removida do histórico.",
      "status.jsonCopied": "JSON copiado.",
      "status.exampleCopied": "Exemplo copiado para a área de transferência.",
      "status.copyFailed": "Não foi possível copiar.",
      "status.errorGeneric": "Erro {status}",
      "confirm.cancel": "Cancelar esta consulta em andamento?",
      "confirm.delete": "Apagar esta consulta do histórico? Esta ação não pode ser desfeita.",
      "curl.keyPlaceholder": "SUA_CHAVE",
      "curl.sseComment": "// JavaScript (navegador / Node com polyfill)",
      "curl.sseError": "erro",
    },
    en: {
      "page.title": "iFood Migrator",
      "eyebrow": "Menu extractor",
      "subtitle":
        "Extract a store's full iFood menu as JSON — through the web UI or the REST API.",
      "lang.label": "Language",
      "lang.pt": "Portuguese",
      "lang.en": "English",
      "meta.strategy": "Strategy: {value}",
      "meta.jobs": "Jobs: {active}/{max}",
      "tab.nav.aria": "Sections",
      "tab.extract": "Extraction",
      "tab.history": "History",
      "tab.api": "API & usage",
      "steps.aria": "How to use the interface",
      "step.1": "Paste the store's iFood URL",
      "step.2": "Start the migration and watch progress",
      "step.3": "Copy or download the menu JSON",
      "panel.newExtraction": "New extraction",
      "label.url": "Store URL (iFood)",
      "placeholder.url": "https://www.ifood.com.br/delivery/city/store/uuid",
      "label.apiKey": "API key",
      "label.apiKeyHint": "(required on this server)",
      "placeholder.apiKey": "Paste the API_KEY value from .env",
      "btn.start": "Start migration",
      "btn.cancel": "Cancel",
      "btn.clear": "Clear",
      "progress.aria": "Progress log",
      "panel.resultJson": "JSON result",
      "btn.copy": "Copy",
      "btn.download": "Download .json",
      "json.waiting": "Waiting for migration…",
      "json.starting": "Starting…",
      "json.cancelledByUser": "Cancelled by user",
      "json.scrapeError": "Scraping error",
      "json.noDetails": "No details",
      "history.title": "Scraping history",
      "history.desc":
        "Queries stored in local SQLite. Reopen results, cancel active jobs, or remove records.",
      "btn.refresh": "Refresh",
      "th.store": "Store",
      "th.status": "Status",
      "th.date": "Date",
      "th.actions": "Actions",
      "history.loading": "Loading…",
      "history.empty": "No scrapings yet",
      "history.errorLoad": "Failed to load history ({status})",
      "history.networkFail": "Network error: {message}",
      "action.viewJson": "View JSON",
      "action.cancel": "Cancel",
      "action.delete": "Delete",
      "api.title": "REST API integration",
      "api.intro":
        'All endpoints below are asynchronous: start a job with <code>POST /api/migrate</code>, track progress via <strong>SSE</strong> or <strong>polling</strong>, and read the JSON when <code>status</code> is <code>done</code>. Interactive docs at <a href="/docs" target="_blank" rel="noopener">/docs</a> (OpenAPI).',
      "api.note.baseUrl": "Base URL for this instance:",
      "api.note.authOff":
        'Authentication: disabled — set <code>API_KEY</code> in <code>.env</code> to require the <code>X-Api-Key</code> header.',
      "api.note.authOn":
        "Authentication: enabled — send the <code>X-Api-Key</code> header on protected routes (except <code>/api/health</code>).",
      "api.note.header": "Header when authentication is enabled:",
      "api.note.headerValue": "X-Api-Key: your-key",
      "api.note.timeout":
        "Default scraping timeout: configurable via <code>SCRAPE_TIMEOUT_S</code> on the server",
      "api.ep.migrate.desc":
        "Starts extraction. Returns <strong>202</strong> with <code>job_id</code>, status URLs, SSE events, and cancel URL.",
      "api.ep.status.desc":
        "Poll the job: <code>status</code>, <code>progress</code>, <code>result</code> (when finished), or <code>error</code>.",
      "api.ep.sse.desc":
        'Real-time stream. Events: <code>progress</code>, <code>done</code>, <code>error</code>, <code>cancelled</code>. The web UI uses <code>EventSource</code> on this endpoint.',
      "api.ep.cancel.desc": "Cancels a job in <code>pending</code> or <code>running</code> state.",
      "api.ep.list.desc":
        "Lists history. Query params: <code>limit</code>, <code>offset</code>, <code>status</code> (pending, running, done, error, cancelled).",
      "api.ep.detail.desc": "Scraping detail (same shape as migrate polling).",
      "api.ep.delete.desc": "Removes from history. If still active, cancels before deleting.",
      "api.ep.health.desc":
        "Public health check (no API key). Returns strategy, active jobs, and stats.",
      "btn.copyCurl": "Copy cURL",
      "btn.copyExample": "Copy example",
      "api.flow.summary": "Recommended flow (polling)",
      "api.flow.1": "<code>POST /api/migrate</code> with the store URL → save <code>job_id</code>",
      "api.flow.2":
        "Loop: <code>GET /api/migrate/{job_id}</code> every 2–5 s until a terminal status",
      "api.flow.3": "When <code>done</code>, use the <code>result</code> field as the menu JSON",
      "api.flow.4":
        "For real-time UX, prefer SSE on <code>events_url</code> instead of aggressive polling",
      "api.flow.ngrok":
        'Exposing via ngrok: set <code>API_KEY</code> in <code>.env</code> and send <code>X-Api-Key</code> on all protected routes (except <code>/api/health</code> and the events SSE stream).',
      "footer.brand": "iFood Migrator",
      "footer.openapi": "OpenAPI /docs",
      "status.urlRequired": "Enter the store URL.",
      "status.apiKeyRequired": "Enter the API key (required on this server).",
      "status.sending": "Sending request…",
      "status.jobProgress": "Job {id} — waiting for progress…",
      "status.migrationDone": "Migration completed.",
      "status.sseFailed": "SSE connection closed or failed.",
      "status.cancelled": "Request cancelled.",
      "status.scrapeError": "Scraping failed",
      "status.loaded": "Loaded: {name}",
      "status.jobStatus": "Status: {status}",
      "status.jobLoadError": "Failed to load job: {status}",
      "status.removed": "Record removed from history.",
      "status.jsonCopied": "JSON copied.",
      "status.exampleCopied": "Example copied to clipboard.",
      "status.copyFailed": "Could not copy.",
      "status.errorGeneric": "Error {status}",
      "confirm.cancel": "Cancel this in-progress request?",
      "confirm.delete": "Delete this record from history? This cannot be undone.",
      "curl.keyPlaceholder": "YOUR_KEY",
      "curl.sseComment": "// JavaScript (browser / Node with polyfill)",
      "curl.sseError": "error",
    },
  };

  let locale = DEFAULT_LOCALE;
  let onChange = null;

  function normalizeLocale(raw) {
    if (raw === "en" || raw === "en-US") return "en";
    return DEFAULT_LOCALE;
  }

  function t(key, vars = {}) {
    const bag = messages[locale] || messages[DEFAULT_LOCALE];
    let str = bag[key] ?? messages[DEFAULT_LOCALE][key] ?? key;
    Object.entries(vars).forEach(([k, v]) => {
      str = str.replaceAll(`{${k}}`, String(v));
    });
    return str;
  }

  function getLocale() {
    return locale;
  }

  function getDateLocale() {
    return locale === "en" ? "en-US" : "pt-BR";
  }

  function applyDom() {
    document.documentElement.lang = locale === "en" ? "en" : "pt-BR";
    document.title = t("page.title");

    document.querySelectorAll("[data-i18n]").forEach((el) => {
      if (el.id === "json-output") return;
      el.textContent = t(el.dataset.i18n);
    });

    document.querySelectorAll("[data-i18n-html]").forEach((el) => {
      el.innerHTML = t(el.dataset.i18nHtml);
    });

    document.querySelectorAll("[data-i18n-placeholder]").forEach((el) => {
      el.placeholder = t(el.dataset.i18nPlaceholder);
    });

    document.querySelectorAll("[data-i18n-aria]").forEach((el) => {
      el.setAttribute("aria-label", t(el.dataset.i18nAria));
    });

    document.querySelectorAll(".lang-btn").forEach((btn) => {
      const active = btn.dataset.lang === locale;
      btn.classList.toggle("active", active);
      btn.setAttribute("aria-pressed", active ? "true" : "false");
    });
  }

  function setLocale(next, options = {}) {
    const normalized = normalizeLocale(next);
    if (normalized === locale && !options.force) return;
    locale = normalized;
    localStorage.setItem(STORAGE_KEY, locale);
    applyDom();
    if (typeof onChange === "function") onChange(locale);
  }

  function init(handler) {
    onChange = handler;
    const stored = localStorage.getItem(STORAGE_KEY);
    locale = normalizeLocale(stored || DEFAULT_LOCALE);
    applyDom();
  }

  return { t, getLocale, getDateLocale, setLocale, init, applyDom };
})();
