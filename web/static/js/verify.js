const TAB_KEYS = ["pair", "prompt-url", "checker"];

function showTab(name) {
  const target = TAB_KEYS.includes(name) ? name : "pair";
  TAB_KEYS.forEach((id) => {
    const el = document.getElementById(`tab-${id}`);
    if (el) el.style.display = id === target ? "block" : "none";
  });
  document.querySelectorAll(".tab").forEach((tab) => tab.classList.remove("active"));
  const tabIndex = TAB_KEYS.indexOf(target);
  if (tabIndex >= 0) {
    const tab = document.querySelectorAll(".tab")[tabIndex];
    tab?.classList.add("active");
  }
  if (window.location.hash !== `#${target}`) {
    history.replaceState(null, "", `#${target}`);
  }
}

function renderResult(targetId, data, fallbackError) {
  const el = document.getElementById(targetId);
  try {
    el.textContent = JSON.stringify(data, null, 2);
  } catch (err) {
    el.textContent = fallbackError || String(err);
  }
}

function setStatusBadge(statusText) {
  const badge = document.getElementById("result-status");
  if (!badge) return;
  badge.textContent = statusText || "Pendiente";
}

function updateResultCard(data) {
  if (!data) return;
  const card = document.getElementById("result-card");
  if (!card) return;

  const documentData = data.document || data;
  const verification = data.verification || {};
  const iahId = documentData.iah_id || documentData.id || "—";
  const status =
    verification.status || documentData.status || documentData.state || documentData.validation?.status || "pendiente";

  document.getElementById("result-iah-id").textContent = iahId;
  document.getElementById("result-hash-prompt").textContent =
    documentData.h_prompt || documentData.hash_prompt || "—";
  document.getElementById("result-hash-response").textContent =
    documentData.h_response || documentData.hash_response || "—";
  document.getElementById("result-hash-total").textContent =
    documentData.h_total || documentData.hash_total || documentData.h_iah || "—";
  document.getElementById("result-signature").textContent =
    documentData.signature || documentData.firma_total || "—";
  setStatusBadge(status.toUpperCase());

  renderResult("result-raw", data, "No se pudo serializar el resultado");
  const errors = verification.errors || data.errors || [];
  const errorList = document.getElementById("error-list");
  const errorBox = document.getElementById("result-errors");
  if (errorList && errorBox) {
    errorList.innerHTML = "";
    if (errors.length > 0) {
      errors.forEach((err) => {
        const li = document.createElement("li");
        li.textContent = err;
        errorList.appendChild(li);
      });
      errorBox.style.display = "block";
    } else {
      errorBox.style.display = "none";
    }
  }

  const normalizedBox = document.getElementById("normalized-container");
  if (normalizedBox) {
    const normalizedPrompt = verification.normalized_prompt_text;
    const normalizedResponse = verification.normalized_response_text;
    const shouldShow = documentData.store_raw && (normalizedPrompt || normalizedResponse);

    if (shouldShow) {
      document.getElementById("normalized-prompt").textContent =
        normalizedPrompt || "(sin prompt normalizado)";
      document.getElementById("normalized-response").textContent =
        normalizedResponse || "(sin respuesta normalizada)";
      normalizedBox.style.display = "grid";
    } else {
      normalizedBox.style.display = "none";
    }
  }

  card.style.display = "grid";
}

async function submitPair() {
  const payload = {
    prompt_text: document.getElementById("pair-prompt").value,
    response_text: document.getElementById("pair-response").value,
    model: document.getElementById("pair-model").value,
  };

  const logEl = document.getElementById("pair-log");
  logEl.textContent = "Enviando…";

  try {
    const res = await fetch("/api/verify/pair", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    const data = await res.json();
    if (!res.ok) {
      const detail = data?.detail || "Error generando IA-HASH";
      logEl.textContent = detail;
      return;
    }

    renderResult("pair-log", data);
    updateResultCard(data);
  } catch (err) {
    logEl.textContent = `Error de red: ${err}`;
  }
}

async function submitConversation() {
  const payload = {
    conversation_url: document.getElementById("conv-url").value,
    prompt_id: document.getElementById("prompt-slug").value || null,
    provider: document.getElementById("conv-provider")?.value || null,
    model: document.getElementById("conv-model")?.value || "unknown",
  };

  const logEl = document.getElementById("conv-log");
  logEl.textContent = "Enviando…";

  try {
    const res = await fetch("/api/verify/conversation", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    const data = await res.json();
    if (!res.ok) {
      const detail = data?.detail || "Error verificando conversación";
      logEl.textContent = detail;
      return;
    }

    renderResult("conv-log", data);
    updateResultCard(data);
  } catch (err) {
    logEl.textContent = `Error de red: ${err}`;
  }
}

async function submitChecker() {
  const logEl = document.getElementById("checker-log");
  const raw = document.getElementById("checker-json").value;

  let parsed;
  try {
    parsed = JSON.parse(raw);
  } catch (err) {
    logEl.textContent = `JSON inválido: ${err}`;
    return;
  }

  try {
    const res = await fetch("/api/check", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ document: parsed }),
    });

    const data = await res.json();
    if (!res.ok) {
      const detail = data?.detail || "Error en checker";
      logEl.textContent = detail;
      return;
    }

    renderResult("checker-log", data);
    updateResultCard(data);
  } catch (err) {
    logEl.textContent = `Error de red: ${err}`;
  }
}

function syncTabWithHash() {
  const hash = window.location.hash.replace("#", "");
  if (TAB_KEYS.includes(hash)) {
    showTab(hash);
  }
}

document.addEventListener("DOMContentLoaded", () => {
  document.getElementById("pair-form")?.addEventListener("submit", (ev) => {
    ev.preventDefault();
    submitPair();
  });

  document
    .getElementById("conversation-form")
    ?.addEventListener("submit", (ev) => {
      ev.preventDefault();
      submitConversation();
    });

  document.getElementById("checker-form")?.addEventListener("submit", (ev) => {
    ev.preventDefault();
    submitChecker();
  });

  syncTabWithHash();
  window.addEventListener("hashchange", syncTabWithHash);
});
