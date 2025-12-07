function copyPrompt() {
  const text = document.getElementById("prompt-text").value;
  navigator.clipboard.writeText(text);
  alert("Prompt copiado al portapapeles.");
}

async function generateIAHash(promptId) {
  const responseText = document.getElementById("response-text").value;
  const payload = {
    prompt_text: document.getElementById("prompt-text").value,
    response_text: responseText,
    prompt_id: promptId,
    model: document.getElementById("pair-model")?.value || "unknown",
    store_raw: true,
  };

  const logEl = document.getElementById("pair-log");
  logEl.textContent = "Generando IA-HASH...";

  try {
    const res = await fetch("/api/verify/pair", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    const data = await res.json();
    if (!res.ok) {
      logEl.textContent = data?.detail || "Error generando IA-HASH";
      return;
    }

    logEl.textContent = JSON.stringify(data, null, 2);
  } catch (err) {
    logEl.textContent = `Error de red: ${err}`;
  }
}

async function verifyShareWithIAHASH(promptId) {
  const url = document.getElementById("conv-url").value.trim();
  const model = (document.getElementById("conv-model")?.value || "chatgpt").trim() || "chatgpt";
  const resultContainer = document.getElementById("conv-result");
  const logEl = document.getElementById("conv-log");

  if (!url) {
    showError(resultContainer, "Por favor, pega una URL de ChatGPT.");
    return;
  }

  logEl.textContent = "Procesando verificación...";
  resultContainer.style.display = "block";
  resultContainer.textContent = "Verificando…";

  try {
    const res = await fetch("/api/issue-from-share", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        share_url: url,
        model,
        prompt_id: promptId,
      }),
    });

    if (!res.ok) {
      const text = await res.text();
      showError(resultContainer, `Error al verificar la URL: ${text}`);
      return;
    }

    const doc = await res.json();
    renderIAHASHResult(resultContainer, doc);
    logEl.textContent = "Documento IA-HASH generado desde ChatGPT share.";
  } catch (err) {
    console.error(err);
    showError(resultContainer, "Error de red al contactar con IA-HASH.");
  }
}
