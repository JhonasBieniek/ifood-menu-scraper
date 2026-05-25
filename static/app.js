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

let currentResult = null;
let currentJobId = null;
let eventSource = null;

function headers() {
  const h = { "Content-Type": "application/json" };
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
}

async function checkApiKeyRequired() {
  try {
    const res = await fetch("/api/health");
    if (!res.ok) return;
    apiKeyRow.classList.remove("hidden");
  } catch {
    /* ignore */
  }
}

async function loadHistory() {
  try {
    const res = await fetch("/api/scrapes?limit=15", { headers: headers() });
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
        const isActive = currentJobId === item.id && canCancel;
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
        if (btn.dataset.action === "view") await openScrape(id);
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
    const res = await fetch(`/api/scrapes/${jobId}`, { headers: headers() });
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
      setStatus(data.status === "cancelled" ? "Consulta cancelada" : "Scraping com erro", data.status === "cancelled" ? "error" : "error");
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
      headers: headers(),
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

checkApiKeyRequired();
loadHistory();
