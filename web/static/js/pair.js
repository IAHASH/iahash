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

function syncTabWithHash() {
  const hash = window.location.hash.replace("#", "");
  if (TAB_KEYS.includes(hash)) {
    showTab(hash);
  }
}

function setLoading(button, isLoading, loadingText, defaultText) {
  if (!button) return;
  button.disabled = isLoading;
  button.textContent = isLoading ? loadingText : defaultText;
}

function logResult(targetId, data, fallbackError) {
  const el = document.getElementById(targetId);
  if (!el) return;
  try {
    el.textContent = JSON.stringify(data, null, 2);
  } catch (err) {
    el.textContent = fallbackError || String(err);
  }
}

function isValidChatGPTShare(url) {
  return /^https:\/\/(chatgpt\.com|chat\.openai\.com)\/share\/.+/.test(url || '');
}

async function submitPair() {
  const payload = {
    prompt_text: document.getElementById("pair-prompt").value,
    response_text: document.getElementById("pair-response").value,
    model: document.getElementById("pair-model").value,
  };

  const logEl = document.getElementById("pair-log");
  const button = document.getElementById("pair-submit");
  const resultContainer = document.getElementById("result-card");

  logEl.textContent = "Enviando…";
  renderLoading(resultContainer, "Generando IA-HASH…");
  setLoading(button, true, "Generando…", "Generar IA-HASH");

  try {
    const res = await fetch("/api/verify/pair", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    const data = await res.json();
    if (!res.ok || data?.status !== "ISSUED") {
      const detail = data?.error?.message || data?.detail || "Error generando IA-HASH";
      logEl.textContent = detail;
      renderError(resultContainer, data);
      return;
    }

    logResult("pair-log", data);
    renderIssuedDocument(resultContainer, data);
  } catch (err) {
    const msg = `Error de red: ${err}`;
    logEl.textContent = msg;
    renderError(resultContainer, msg);
  } finally {
    setLoading(button, false, "Generando…", "Generar IA-HASH");
  }
}

function updatePromptMeta() {
  const select = document.getElementById("prompt-slug");
  const meta = document.getElementById("prompt-meta");
  if (!select || !meta) return;

  const option = select.options[select.selectedIndex];
  const slug = option?.dataset?.slug || "—";
  const hPublic = option?.dataset?.hPublic || "—";

  meta.querySelector("[data-meta='slug']")?.replaceChildren(document.createTextNode(slug || "—"));
  meta.querySelector("[data-meta='h-public']")?.replaceChildren(document.createTextNode(hPublic || "—"));
}

async function submitConversation() {
  const shareUrl = document.getElementById("conv-url").value;
  const promptId =
    (document.getElementById("prompt-slug")?.value || "").trim() || null;
  const manualPrompt = (document.getElementById("prompt-manual")?.value || "").trim();
  const provider = document.getElementById("conv-provider")?.value || "chatgpt";
  const model = document.getElementById("conv-model")?.value || "unknown";

  const logEl = document.getElementById("conv-log");
  const button = document.getElementById("conv-submit");
  const resultContainer = document.getElementById("result-card");

  renderLoading(resultContainer, "Verificando URL y generando IA-HASH…");
  logEl.textContent = "Enviando…";

  if (!promptId && !manualPrompt) {
    const detail = "Selecciona un prompt maestro o pega el texto exacto usado.";
    renderError(resultContainer, { message: detail });
    logEl.textContent = detail;
    return;
  }

  if (!isValidChatGPTShare(shareUrl || "")) {
    const detail = "URL inválida. Usa un enlace de chatgpt.com/share.";
    renderError(resultContainer, { message: detail });
    logEl.textContent = detail;
    return;
  }

  setLoading(button, true, "Generando…", "Generar IA-HASH");

  try {
    const res = await fetch("/api/issue/from_prompt_url", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        prompt_id: promptId || null,
        provider,
        share_url: shareUrl,
        model,
        prompt_text: promptId ? null : manualPrompt,
      }),
    });

    const data = await res.json();
    if (!res.ok || data?.status !== "ISSUED") {
      const detail = data?.error?.message || data?.detail || data?.reason || "Error verificando conversación";
      logEl.textContent = detail;
      renderError(resultContainer, data);
      return;
    }

    logResult("conv-log", data);
    renderIssuedDocument(resultContainer, data);
  } catch (err) {
    const msg = `Error de red: ${err}`;
    logEl.textContent = msg;
    renderError(resultContainer, msg);
  } finally {
    setLoading(button, false, "Generando…", "Generar IA-HASH");
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

  document.getElementById("prompt-slug")?.addEventListener("change", updatePromptMeta);
  updatePromptMeta();

  syncTabWithHash();
  window.addEventListener("hashchange", syncTabWithHash);
});
