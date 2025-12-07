function showTab(name) {
  ["pair", "conversation", "checker"].forEach((id) => {
    document.getElementById(`tab-${id}`).style.display =
      id === name ? "block" : "none";
  });
  document.querySelectorAll(".tab").forEach((tab) => tab.classList.remove("active"));
  const tabIndex = { pair: 0, conversation: 1, checker: 2 }[name];
  document.querySelectorAll(".tab")[tabIndex].classList.add("active");
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
  } catch (err) {
    logEl.textContent = `Error de red: ${err}`;
  }
}
