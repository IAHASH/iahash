function copyPrompt() {
  const text = document.getElementById("prompt-text").value;
  navigator.clipboard.writeText(text);
  alert("Prompt copiado al portapapeles.");
}

async function verifyConversation(promptId) {
  const url = document.getElementById("conv-url").value;
  const payload = {
    conversation_url: url,
    prompt_id: promptId,
    prompt_text: document.getElementById("prompt-text").value,
    provider: document.getElementById("conv-provider")?.value || "chatgpt",
    model: document.getElementById("conv-model")?.value || "unknown",
  };

  const logEl = document.getElementById("conv-log");
  logEl.textContent = "Procesando verificación...";

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

    logEl.textContent = JSON.stringify(data, null, 2);
  } catch (err) {
    logEl.textContent = `Error de red: ${err}`;
  }
}
