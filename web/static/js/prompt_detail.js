function isValidChatGPTShare(url) {
  return /^https:\/\/(chatgpt\.com|chat\.openai\.com)\/share\/.+/.test(url || '');
}

function toggleButtonState(button, isLoading, loadingText, defaultText) {
  if (!button) return;
  button.disabled = isLoading;
  button.textContent = isLoading ? loadingText : defaultText;
}

function copyPrompt() {
  const text = document.getElementById("prompt-text").value;
  navigator.clipboard.writeText(text);
  const btn = document.getElementById("copy-prompt-btn");
  if (btn) {
    btn.textContent = "Copiado";
    setTimeout(() => (btn.textContent = "Copiar Prompt"), 1400);
  }
}

function updateSummary(documentData) {
  const summary = document.getElementById("share-summary");
  if (!summary || !documentData) return;

  const setValue = (selector, value, defaultValue = "—") => {
    const el = summary.querySelector(selector);
    if (!el) return;
    if (selector === "[data-summary='conversation-url']" && value) {
      el.textContent = "";
      const link = document.createElement("a");
      link.href = value;
      link.target = "_blank";
      link.rel = "noreferrer";
      link.textContent = value;
      el.appendChild(link);
      return;
    }
    el.textContent = value || defaultValue;
  };

  setValue("[data-summary='title']", documentData.prompt_title || summary.dataset.promptTitle);
  setValue(
    "[data-summary='h-public']",
    documentData.prompt_public_hash || documentData.h_public || summary.dataset.promptH,
  );
  setValue("[data-summary='provider']", documentData.provider || "chatgpt");
  setValue("[data-summary='model']", documentData.model || "chatgpt");
  setValue("[data-summary='conversation-url']", documentData.conversation_url || "");
}

async function generatePair(promptId) {
  const payload = {
    prompt_text: document.getElementById("prompt-text").value,
    response_text: document.getElementById("response-text").value,
    prompt_id: promptId,
    model: document.getElementById("pair-model")?.value || "unknown",
    store_raw: true,
  };

  const logEl = document.getElementById("pair-log");
  const button = document.getElementById("pair-submit");
  const resultContainer = document.getElementById("pair-result");

  renderLoading(resultContainer, "Generando IA-HASH…");
  logEl.textContent = "Generando IA-HASH...";
  toggleButtonState(button, true, "Generando…", "Generar IA-HASH");

  try {
    const res = await fetch("/api/verify/pair", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    const data = await res.json();
    if (!res.ok || data?.status !== "ISSUED") {
      const detail = data?.error?.message || data?.detail || "Error generando IA-HASH";
      renderError(resultContainer, data);
      logEl.textContent = detail;
      return;
    }

    renderIssuedDocument(resultContainer, data);
    logEl.textContent = "IA-HASH emitido correctamente.";
  } catch (err) {
    renderError(resultContainer, "Error de red al generar IA-HASH.");
    logEl.textContent = `Error de red: ${err}`;
  } finally {
    toggleButtonState(button, false, "Generando…", "Generar IA-HASH");
  }
}

async function verifyShareWithIAHASH(promptId) {
  const urlInput = document.getElementById("conv-url");
  const providerSelect = document.getElementById("conv-provider");
  const modelInput = document.getElementById("conv-model");
  const resultContainer = document.getElementById("conv-result");
  const logEl = document.getElementById("conv-log");
  const button = document.getElementById("conv-submit");

  const shareUrl = urlInput.value.trim();
  const provider = providerSelect?.value || "chatgpt";
  const model = modelInput?.value?.trim() || "chatgpt";

  renderLoading(resultContainer, "Verificando URL y generando IA-HASH…");
  logEl.textContent = "";

  if (!isValidChatGPTShare(shareUrl)) {
    renderError(resultContainer, "URL inválida. Usa un enlace de chatgpt.com/share.");
    return;
  }

  toggleButtonState(button, true, "Verificando…", "Verificar con IA-HASH");
  logEl.textContent = "Procesando verificación...";

  try {
    const res = await fetch("/api/issue/from_prompt_url", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        prompt_id: promptId,
        provider,
        share_url: shareUrl,
        model,
      }),
    });

    const data = await res.json();
    if (!res.ok || data?.status !== "ISSUED") {
      const detail = data?.error?.message || data?.detail || "Error al verificar la URL";
      renderError(resultContainer, data);
      logEl.textContent = detail;
      return;
    }

    renderIssuedDocument(resultContainer, data);
    updateSummary(data.document || {});
    logEl.textContent = "Documento IA-HASH generado desde ChatGPT.";
  } catch (err) {
    renderError(resultContainer, "Error de red al contactar con IA-HASH.");
    logEl.textContent = `Error de red: ${err}`;
  } finally {
    toggleButtonState(button, false, "Verificando…", "Verificar con IA-HASH");
  }
}

document.addEventListener("DOMContentLoaded", () => {
  const contextEl = document.getElementById("prompt-context");
  const promptId = contextEl?.dataset.promptId;

  document.getElementById("copy-prompt-btn")?.addEventListener("click", (ev) => {
    ev.preventDefault();
    copyPrompt();
  });

  document.getElementById("pair-form")?.addEventListener("submit", (ev) => {
    ev.preventDefault();
    generatePair(promptId);
  });

  document.getElementById("conversation-form")?.addEventListener("submit", (ev) => {
    ev.preventDefault();
    verifyShareWithIAHASH(promptId);
  });
});
