const $ = (id) => document.getElementById(id);

const urlInput = $("url");
const apiKeyInput = $("api-key");
const apiKeyRow = $("api-key-row");
const btnStart = $("btn-start");
const btnCancel = $("btn-cancel");
const btnClear = $("btn-clear");
const btnCopy = $("btn-copy");
const btnDownload = $("btn-download");
const btnRefreshHistory = $("btn-refresh-history");
const statusEl = $("status");
const progressLog = $("progress-log");
const jsonOutput = $("json-output");
const resultActions = $("result-actions");
const historyBody = $("history-body");
const metaStrategy = $("meta-strategy");
const metaJobs = $("meta-jobs");
const apiBaseUrlEl = $("api-base-url");
const apiAuthNote = $("api-auth-note");

let currentResult = null;
let currentJobId = null;
let eventSource = null;
let authRequired = false;

const API_BASE = window.location.origin;

function headers() {
  const h = { "Content-Type": "application/json" };
  const key = apiKeyInput.value.trim();
  if (key) h["X-Api-Key"] = key;
  return h;
}

function apiHeadersOnly() {
  const h = {};
  const key = apiKeyInput.value.trim();
  if (key) h["X-Api-Key"] = key;
  return h;
}

function setStatus(text, type) {
  statusEl.textContent = text;
  statusEl.className = `status ${type}`;
  statusEl.classList.remove("hidden");
}

function setRunningUi(running) {
  btnStart.disabled = running;
  btnCancel.classList.toggle("hidden", !running);
}

function clearProgress() {
  progressLog.innerHTML = "";
}

function appendProgress(message) {
  const li = document.createElement("li");
  li.textContent = message;
  progressLog.appendChild(li);
  progressLog.scrollTop = progressLog.scrollHeight;
}

function showJson(data) {
  currentResult = data;
  jsonOutput.textContent = JSON.stringify(data, null, 2);
  resultActions.classList.remove("hidden");
}

function finishJob() {
  closeEventSource();
  setRunningUi(false);
  currentJobId = null;
  loadHistory();
  refreshHealthMeta();
}

function switchTab(tabId) {
  document.querySelectorAll(".tab-btn").forEach((btn) => {
    const active = btn.dataset.tab === tabId;
    btn.classList.toggle("active", active);
    btn.setAttribute("aria-selected", active ? "true" : "false");
  });
  document.querySelectorAll(".tab-panel").forEach((panel) => {
    const isTarget = panel.id === `panel-${tabId}`;
    panel.classList.toggle("active", isTarget);
    panel.hidden = !isTarget;
  });
  if (tabId === "history") loadHistory();
}

function buildCurlBlocks() {
  const base = API_BASE;
  const keyLine = authRequired ? '  -H "X-Api-Key: SUA_CHAVE" \\\n' : "";

  const blocks = {
    "curl-migrate": `curl -X POST "${base}/api/migrate" \\
  -H "Content-Type: application/json" \\${keyLine}
  -d '{"url":"https://www.ifood.com.br/delivery/cidade/loja/uuid"}'`,
    "curl-status": `curl${authRequired ? ' -H "X-Api-Key: SUA_CHAVE"' : ""} \\
  "${base}/api/migrate/JOB_ID"`,
    "curl-sse": `// JavaScript (navegador / Node com polyfill)
const es = new EventSource("${base}/api/migrate/JOB_ID/events");
es.addEventListener("progress", (e) => console.log(JSON.parse(e.data)));
es.addEventListener("done", (e) => console.log(JSON.parse(e.data)));
es.addEventListener("error", (e) => console.log(e.data ? JSON.parse(e.data) : "erro"));
es.addEventListener("cancelled", (e) => console.log(JSON.parse(e.data)));`,
    "curl-cancel": `curl -X POST${authRequired ? ' -H "X-Api-Key: SUA_CHAVE"' : ""} \\
  "${base}/api/migrate/JOB_ID/cancel"`,
    "curl-list": `curl${authRequired ? ' -H "X-Api-Key: SUA_CHAVE"' : ""} \\
  "${base}/api/scrapes?limit=20&status=done"`,
    "curl-detail": `curl${authRequired ? ' -H "X-Api-Key: SUA_CHAVE"' : ""} \\
  "${base}/api/scrapes/JOB_ID"`,
    "curl-delete": `curl -X DELETE${authRequired ? ' -H "X-Api-Key: SUA_CHAVE"' : ""} \\
  "${base}/api/scrapes/JOB_ID"`,
    "curl-health": `curl "${base}/api/health"`,
  };

  Object.entries(blocks).forEach(([id, text]) => {
    const el = $(id);
    if (el) el.textContent = text;
  });

  if (apiBaseUrlEl) apiBaseUrlEl.textContent = base;
}

async function refreshHealthMeta() {
  try {
    const res = await fetch("/api/health");
    if (!res.ok) return;
    const data = await res.json();
    authRequired = Boolean(data.auth_required);
    metaStrategy.textContent = `Estratégia: ${data.strategy || "—"}`;
    metaJobs.textContent = `Jobs: ${data.active_jobs ?? 0}/${data.max_concurrent_jobs ?? "—"}`;

    apiKeyRow.classList.toggle("hidden", !authRequired);
    if (authRequired) apiKeyInput.setAttribute("required", "required");
    else apiKeyInput.removeAttribute("required");

    if (apiAuthNote) {
      apiAuthNote.textContent = authRequired
        ? "Autenticação: ativa — envie o header X-Api-Key em rotas protegidas (exceto /api/health)."
        : "Autenticação: desativada — defina API_KEY no .env para exigir o header X-Api-Key.";
    }
    buildCurlBlocks();
  } catch {
    /* ignore */
  }
}

async function loadHistory() {
  try {
    const res = await fetch("/api/scrapes?limit=15", { headers: apiHeadersOnly() });
    if (!res.ok) {
      historyBody.innerHTML = `<tr><td colspan="4" class="muted">Erro ao carregar histórico (${res.status})</td></tr>`;
      return;
    }
    const data = await res.json();
    if (!data.items.length) {
      historyBody.innerHTML = `<tr><td colspan="4" class="muted">Nenhum scraping ainda</td></tr>`;
      return;
    }
    historyBody.innerHTML = data.items
      .map((item) => {
        const canCancel = item.status === "pending" || item.status === "running";
        return `
      <tr>
        <td>${escapeHtml(item.store_name || truncateUrl(item.url))}</td>
        <td><span class="badge ${item.status}">${item.status}</span></td>
        <td>${formatDate(item.created_at)}</td>
        <td class="row-actions">
          <button type="button" class="btn-link" data-action="view" data-id="${item.id}">Ver JSON</button>
          ${canCancel ? `<button type="button" class="btn-link btn-warn" data-action="cancel" data-id="${item.id}">Cancelar</button>` : ""}
          <button type="button" class="btn-link btn-danger" data-action="delete" data-id="${item.id}">Apagar</button>
        </td>
      </tr>`;
      })
      .join("");

    historyBody.querySelectorAll("[data-action]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const id = btn.dataset.id;
        if (btn.dataset.action === "view") {
          switchTab("extract");
          await openScrape(id);
        }
        if (btn.dataset.action === "cancel") await cancelJob(id);
        if (btn.dataset.action === "delete") await deleteScrape(id);
      });
    });
  } catch (e) {
    historyBody.innerHTML = `<tr><td colspan="4" class="muted">Falha de rede: ${escapeHtml(e.message)}</td></tr>`;
  }
}

async function openScrape(jobId) {
  try {
    const res = await fetch(`/api/scrapes/${jobId}`, { headers: apiHeadersOnly() });
    if (!res.ok) {
      setStatus(`Erro ao carregar job: ${res.status}`, "error");
      return;
    }
    const data = await res.json();
    urlInput.value = data.url;
    if (data.status === "done" && data.result) {
      showJson(data.result);
      setStatus(`Carregado: ${data.result.name || jobId}`, "done");
    } else if (data.status === "error" || data.status === "cancelled") {
      jsonOutput.textContent = data.error || "Sem detalhes";
      setStatus(
        data.status === "cancelled" ? "Consulta cancelada" : "Scraping com erro",
        "error"
      );
    } else {
      jsonOutput.textContent = JSON.stringify(data, null, 2);
      setStatus(`Status: ${data.status}`, "running");
    }
  } catch (e) {
    setStatus(e.message, "error");
  }
}

async function cancelJob(jobId) {
  if (!confirm("Cancelar esta consulta em andamento?")) return;

  try {
    const res = await fetch(`/api/migrate/${jobId}/cancel`, {
      method: "POST",
      headers: headers(),
    });
    const body = await res.json().catch(() => ({}));
    if (!res.ok) {
      throw new Error(body.detail || `Erro ${res.status}`);
    }

    if (currentJobId === jobId) {
      closeEventSource();
      jsonOutput.textContent = "Cancelado pelo usuário";
      setStatus("Consulta cancelada.", "error");
      finishJob();
    } else {
      setStatus("Consulta cancelada.", "done");
      loadHistory();
    }
  } catch (e) {
    setStatus(e.message, "error");
  }
}

async function deleteScrape(jobId) {
  if (!confirm("Apagar esta consulta do histórico? Esta ação não pode ser desfeita.")) return;

  try {
    const res = await fetch(`/api/scrapes/${jobId}`, {
      method: "DELETE",
      headers: apiHeadersOnly(),
    });
    const body = await res.json().catch(() => ({}));
    if (!res.ok) {
      throw new Error(body.detail || `Erro ${res.status}`);
    }

    if (currentJobId === jobId) {
      closeEventSource();
      currentJobId = null;
      setRunningUi(false);
      jsonOutput.textContent = "Aguardando migração…";
      resultActions.classList.add("hidden");
      statusEl.classList.add("hidden");
    }

    setStatus("Consulta removida do histórico.", "done");
    loadHistory();
  } catch (e) {
    setStatus(e.message, "error");
  }
}

function closeEventSource() {
  if (eventSource) {
    eventSource.close();
    eventSource = null;
  }
}

function bindSseEvents(jobId) {
  eventSource.addEventListener("progress", (ev) => {
    const data = JSON.parse(ev.data);
    appendProgress(data.message);
  });

  eventSource.addEventListener("done", (ev) => {
    const data = JSON.parse(ev.data);
    showJson(data.result);
    setStatus("Migração concluída.", "done");
    finishJob();
  });

  eventSource.addEventListener("error", (ev) => {
    if (ev.data) {
      const data = JSON.parse(ev.data);
      jsonOutput.textContent = data.message || "Erro no scraping";
      setStatus(data.message || "Erro", "error");
    } else if (currentJobId !== jobId) {
      return;
    } else {
      setStatus("Conexão SSE encerrada ou falhou.", "error");
    }
    finishJob();
  });

  eventSource.addEventListener("cancelled", (ev) => {
    const data = JSON.parse(ev.data);
    jsonOutput.textContent = data.message || "Cancelado pelo usuário";
    setStatus("Consulta cancelada.", "error");
    finishJob();
  });
}

async function startMigration() {
  const url = urlInput.value.trim();
  if (!url) {
    setStatus("Informe a URL da loja.", "error");
    return;
  }

  if (authRequired && !apiKeyInput.value.trim()) {
    setStatus("Informe a API Key (obrigatória neste servidor).", "error");
    apiKeyRow.classList.remove("hidden");
    apiKeyInput.focus();
    return;
  }

  closeEventSource();
  clearProgress();
  currentResult = null;
  resultActions.classList.add("hidden");
  jsonOutput.textContent = "Iniciando…";
  setRunningUi(true);
  setStatus("Enviando solicitação…", "running");

  try {
    const res = await fetch("/api/migrate", {
      method: "POST",
      headers: headers(),
      body: JSON.stringify({ url }),
    });

    const body = await res.json().catch(() => ({}));
    if (!res.ok) {
      throw new Error(body.detail || `Erro ${res.status}`);
    }

    currentJobId = body.job_id;
    setStatus(`Job ${currentJobId} — aguardando progresso…`, "running");

    eventSource = new EventSource(`${body.events_url}`);
    bindSseEvents(currentJobId);
    refreshHealthMeta();
  } catch (e) {
    setStatus(e.message, "error");
    jsonOutput.textContent = e.message;
    finishJob();
  }
}

function escapeHtml(s) {
  const d = document.createElement("div");
  d.textContent = s;
  return d.innerHTML;
}

function truncateUrl(url) {
  return url.length > 48 ? url.slice(0, 45) + "…" : url;
}

function formatDate(iso) {
  try {
    return new Date(iso).toLocaleString("pt-BR");
  } catch {
    return iso;
  }
}

async function copyBlock(blockId) {
  const el = $(blockId);
  if (!el) return;
  try {
    await navigator.clipboard.writeText(el.textContent);
    setStatus("Exemplo copiado para a área de transferência.", "done");
  } catch {
    setStatus("Não foi possível copiar.", "error");
  }
}

document.querySelectorAll(".tab-btn").forEach((btn) => {
  btn.addEventListener("click", () => switchTab(btn.dataset.tab));
});

document.querySelectorAll(".btn-copy").forEach((btn) => {
  btn.addEventListener("click", () => copyBlock(btn.dataset.copy));
});

btnStart.addEventListener("click", startMigration);
btnCancel.addEventListener("click", () => {
  if (currentJobId) cancelJob(currentJobId);
});
btnClear.addEventListener("click", () => {
  urlInput.value = "";
  clearProgress();
  statusEl.classList.add("hidden");
  jsonOutput.textContent = "Aguardando migração…";
  resultActions.classList.add("hidden");
  currentResult = null;
  closeEventSource();
  setRunningUi(false);
  currentJobId = null;
});
btnCopy.addEventListener("click", async () => {
  if (!currentResult) return;
  await navigator.clipboard.writeText(JSON.stringify(currentResult, null, 2));
  setStatus("JSON copiado.", "done");
});
btnDownload.addEventListener("click", () => {
  if (!currentResult) return;
  const name = (currentResult.name || "cardapio").replace(/\s+/g, "-").toLowerCase();
  const blob = new Blob([JSON.stringify(currentResult, null, 2)], { type: "application/json" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = `${name}.json`;
  a.click();
  URL.revokeObjectURL(a.href);
});
btnRefreshHistory.addEventListener("click", loadHistory);

urlInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !btnStart.disabled) startMigration();
});

apiKeyInput.addEventListener("input", buildCurlBlocks);

refreshHealthMeta();
loadHistory();
