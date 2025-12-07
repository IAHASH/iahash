function logResult(targetId, data, fallbackError) {
  const el = document.getElementById(targetId);
  try {
    el.textContent = JSON.stringify(data, null, 2);
  } catch (err) {
    el.textContent = fallbackError || String(err);
  }
}

document.addEventListener("DOMContentLoaded", () => {
  document.getElementById("checker-form")?.addEventListener("submit", async (ev) => {
    ev.preventDefault();

    const logEl = document.getElementById("checker-log");
    const raw = document.getElementById("checker-json").value;
    const resultContainer = document.getElementById("result-card");

    let parsed;
    try {
      parsed = JSON.parse(raw);
    } catch (err) {
      const msg = `JSON inválido: ${err}`;
      logEl.textContent = msg;
      renderIAHASHError(resultContainer, msg);
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
        renderIAHASHError(resultContainer, detail);
        return;
      }

      logResult("checker-log", data);
      renderIAHASHResult(resultContainer, data);
    } catch (err) {
      const msg = `Error de red: ${err}`;
      logEl.textContent = msg;
      renderIAHASHError(resultContainer, msg);
    }
  });
});
