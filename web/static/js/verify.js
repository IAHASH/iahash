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
    renderIAHASHResult(document.getElementById("result-card"), data);
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
    renderIAHASHResult(document.getElementById("result-card"), data);
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
    renderIAHASHResult(document.getElementById("result-card"), data);
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
