const $ = (id) => document.getElementById(id);
const t = (key, vars) => I18n.t(key, vars);

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
let jsonIdleText = t("json.waiting");

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

function curlKeyHeader() {
  const key = t("curl.keyPlaceholder");
  return authRequired ? ` -H "X-Api-Key: ${key}"` : "";
}

function curlKeyHeaderMultiline() {
  const key = t("curl.keyPlaceholder");
  return authRequired ? `  -H "X-Api-Key: ${key}" \\\n` : "";
}

function buildCurlBlocks() {
  const base = API_BASE;

  const blocks = {
    "curl-migrate": `curl -X POST "${base}/api/migrate" \\
  -H "Content-Type: application/json" \\${curlKeyHeaderMultiline()}
  -d '{"url":"https://www.ifood.com.br/delivery/cidade/loja/uuid"}'`,
    "curl-status": `curl${curlKeyHeader()} \\
  "${base}/api/migrate/JOB_ID"`,
    "curl-sse": `${t("curl.sseComment")}
const es = new EventSource("${base}/api/migrate/JOB_ID/events");
es.addEventListener("progress", (e) => console.log(JSON.parse(e.data)));
es.addEventListener("done", (e) => console.log(JSON.parse(e.data)));
es.addEventListener("error", (e) => console.log(e.data ? JSON.parse(e.data) : "${t("curl.sseError")}"));
es.addEventListener("cancelled", (e) => console.log(JSON.parse(e.data)));`,
    "curl-cancel": `curl -X POST${curlKeyHeader()} \\
  "${base}/api/migrate/JOB_ID/cancel"`,
    "curl-list": `curl${curlKeyHeader()} \\
  "${base}/api/scrapes?limit=20&status=done"`,
    "curl-detail": `curl${curlKeyHeader()} \\
  "${base}/api/scrapes/JOB_ID"`,
    "curl-delete": `curl -X DELETE${curlKeyHeader()} \\
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
    metaStrategy.textContent = t("meta.strategy", { value: data.strategy || "—" });
    metaJobs.textContent = t("meta.jobs", {
      active: data.active_jobs ?? 0,
      max: data.max_concurrent_jobs ?? "—",
    });

    apiKeyRow.classList.toggle("hidden", !authRequired);
    if (authRequired) apiKeyInput.setAttribute("required", "required");
    else apiKeyInput.removeAttribute("required");

    if (apiAuthNote) {
      apiAuthNote.innerHTML = t(authRequired ? "api.note.authOn" : "api.note.authOff");
    }
    buildCurlBlocks();
  } catch {
    /* ignore */
  }
}

async function loadHistory() {
  historyBody.innerHTML = `<tr><td colspan="4" class="muted">${escapeHtml(t("history.loading"))}</td></tr>`;

  try {
    const res = await fetch("/api/scrapes?limit=15", { headers: apiHeadersOnly() });
    if (!res.ok) {
      historyBody.innerHTML = `<tr><td colspan="4" class="muted">${escapeHtml(t("history.errorLoad", { status: res.status }))}</td></tr>`;
      return;
    }
    const data = await res.json();
    if (!data.items.length) {
      historyBody.innerHTML = `<tr><td colspan="4" class="muted">${escapeHtml(t("history.empty"))}</td></tr>`;
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
          <button type="button" class="btn-link" data-action="view" data-id="${item.id}">${escapeHtml(t("action.viewJson"))}</button>
          ${canCancel ? `<button type="button" class="btn-link btn-warn" data-action="cancel" data-id="${item.id}">${escapeHtml(t("action.cancel"))}</button>` : ""}
          <button type="button" class="btn-link btn-danger" data-action="delete" data-id="${item.id}">${escapeHtml(t("action.delete"))}</button>
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
    historyBody.innerHTML = `<tr><td colspan="4" class="muted">${escapeHtml(t("history.networkFail", { message: e.message }))}</td></tr>`;
  }
}

async function openScrape(jobId) {
  try {
    const res = await fetch(`/api/scrapes/${jobId}`, { headers: apiHeadersOnly() });
    if (!res.ok) {
      setStatus(t("status.jobLoadError", { status: res.status }), "error");
      return;
    }
    const data = await res.json();
    urlInput.value = data.url;
    if (data.status === "done" && data.result) {
      showJson(data.result);
      setStatus(t("status.loaded", { name: data.result.name || jobId }), "done");
    } else if (data.status === "error" || data.status === "cancelled") {
      jsonOutput.textContent = data.error || t("json.noDetails");
      setStatus(
        data.status === "cancelled" ? t("status.cancelled") : t("status.scrapeError"),
        "error"
      );
    } else {
      jsonOutput.textContent = JSON.stringify(data, null, 2);
      setStatus(t("status.jobStatus", { status: data.status }), "running");
    }
  } catch (e) {
    setStatus(e.message, "error");
  }
}

async function cancelJob(jobId) {
  if (!confirm(t("confirm.cancel"))) return;

  try {
    const res = await fetch(`/api/migrate/${jobId}/cancel`, {
      method: "POST",
      headers: headers(),
    });
    const body = await res.json().catch(() => ({}));
    if (!res.ok) {
      throw new Error(body.detail || t("status.errorGeneric", { status: res.status }));
    }

    if (currentJobId === jobId) {
      closeEventSource();
      jsonOutput.textContent = t("json.cancelledByUser");
      setStatus(t("status.cancelled"), "error");
      finishJob();
    } else {
      setStatus(t("status.cancelled"), "done");
      loadHistory();
    }
  } catch (e) {
    setStatus(e.message, "error");
  }
}

async function deleteScrape(jobId) {
  if (!confirm(t("confirm.delete"))) return;

  try {
    const res = await fetch(`/api/scrapes/${jobId}`, {
      method: "DELETE",
      headers: apiHeadersOnly(),
    });
    const body = await res.json().catch(() => ({}));
    if (!res.ok) {
      throw new Error(body.detail || t("status.errorGeneric", { status: res.status }));
    }

    if (currentJobId === jobId) {
      closeEventSource();
      currentJobId = null;
      setRunningUi(false);
      jsonOutput.textContent = jsonIdleText;
      resultActions.classList.add("hidden");
      statusEl.classList.add("hidden");
    }

    setStatus(t("status.removed"), "done");
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
    setStatus(t("status.migrationDone"), "done");
    finishJob();
  });

  eventSource.addEventListener("error", (ev) => {
    if (ev.data) {
      const data = JSON.parse(ev.data);
      jsonOutput.textContent = data.message || t("json.scrapeError");
      setStatus(data.message || t("json.scrapeError"), "error");
    } else if (currentJobId !== jobId) {
      return;
    } else {
      setStatus(t("status.sseFailed"), "error");
    }
    finishJob();
  });

  eventSource.addEventListener("cancelled", (ev) => {
    const data = JSON.parse(ev.data);
    jsonOutput.textContent = data.message || t("json.cancelledByUser");
    setStatus(t("status.cancelled"), "error");
    finishJob();
  });
}

async function startMigration() {
  const url = urlInput.value.trim();
  if (!url) {
    setStatus(t("status.urlRequired"), "error");
    return;
  }

  if (authRequired && !apiKeyInput.value.trim()) {
    setStatus(t("status.apiKeyRequired"), "error");
    apiKeyRow.classList.remove("hidden");
    apiKeyInput.focus();
    return;
  }

  closeEventSource();
  clearProgress();
  currentResult = null;
  resultActions.classList.add("hidden");
  jsonOutput.textContent = t("json.starting");
  setRunningUi(true);
  setStatus(t("status.sending"), "running");

  try {
    const res = await fetch("/api/migrate", {
      method: "POST",
      headers: headers(),
      body: JSON.stringify({ url }),
    });

    const body = await res.json().catch(() => ({}));
    if (!res.ok) {
      throw new Error(body.detail || t("status.errorGeneric", { status: res.status }));
    }

    currentJobId = body.job_id;
    setStatus(t("status.jobProgress", { id: currentJobId }), "running");

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
    return new Date(iso).toLocaleString(I18n.getDateLocale());
  } catch {
    return iso;
  }
}

async function copyBlock(blockId) {
  const el = $(blockId);
  if (!el) return;
  try {
    await navigator.clipboard.writeText(el.textContent);
    setStatus(t("status.exampleCopied"), "done");
  } catch {
    setStatus(t("status.copyFailed"), "error");
  }
}

function onLocaleChange() {
  const showIdle = !currentJobId && !currentResult;
  jsonIdleText = t("json.waiting");
  I18n.applyDom();
  buildCurlBlocks();
  refreshHealthMeta();

  const historyTab = $("panel-history");
  if (historyTab && !historyTab.hidden) loadHistory();

  if (showIdle) jsonOutput.textContent = jsonIdleText;
}

document.querySelectorAll(".lang-btn").forEach((btn) => {
  btn.addEventListener("click", () => I18n.setLocale(btn.dataset.lang));
});

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
  jsonOutput.textContent = jsonIdleText;
  resultActions.classList.add("hidden");
  currentResult = null;
  closeEventSource();
  setRunningUi(false);
  currentJobId = null;
});
btnCopy.addEventListener("click", async () => {
  if (!currentResult) return;
  await navigator.clipboard.writeText(JSON.stringify(currentResult, null, 2));
  setStatus(t("status.jsonCopied"), "done");
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

I18n.init(onLocaleChange);
jsonIdleText = t("json.waiting");
jsonOutput.textContent = jsonIdleText;
buildCurlBlocks();
refreshHealthMeta();
loadHistory();
