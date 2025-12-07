function prettyPrintJson(obj) {
  try {
    return JSON.stringify(obj, null, 2);
  } catch (_) {
    return String(obj);
  }
}

function renderIAHashResult(container, document, opts = {}) {
  if (!container) return;
  const { valid = true, error = null } = opts;

  if (error) {
    container.innerHTML = `<div class="result-block result-block-error">${error}</div>`;
    return;
  }

  if (!document) {
    container.innerHTML = "";
    return;
  }

  const statusLabel = valid ? "VERIFICADO" : "NO VERIFICADO";
  const badgeClass = valid ? "badge-success" : "badge-error";
  const statusHint = valid
    ? "Documento IA-HASH verificado con éxito"
    : "El documento no pasó la verificación";

  const jsonText = prettyPrintJson(document);

  container.innerHTML = `
    <div class="result-block result-block-detailed">
      <div class="result-header">
        <span class="badge ${badgeClass}">${statusLabel}</span>
        <span class="result-hint">${statusHint}</span>
      </div>

      <div class="hash-grid">
        <div class="hash-field"><span>IA-HASH ID</span><code>${document.h_total || "-"}</code></div>
        <div class="hash-field"><span>h_prompt</span><code>${document.h_prompt || "-"}</code></div>
        <div class="hash-field"><span>h_response</span><code>${document.h_respuesta || document.h_response || "-"}</code></div>
        <div class="hash-field"><span>Firma</span><code>${document.firma_total || "-"}</code></div>
        <div class="hash-field"><span>Modelo</span><code>${document.modelo || "-"}</code></div>
        <div class="hash-field"><span>Issuer</span><code>${document.issuer_id || "-"}</code></div>
      </div>

      <div class="result-actions">
        <button type="button" class="btn btn-secondary" data-copy-json>Copiar JSON</button>
      </div>

      <details class="json-details">
        <summary>Ver JSON completo</summary>
        <pre class="code-block mono">${jsonText}</pre>
      </details>
    </div>
  `;

  const copyBtn = container.querySelector("[data-copy-json]");
  if (copyBtn && navigator?.clipboard) {
    copyBtn.addEventListener("click", async () => {
      try {
        await navigator.clipboard.writeText(jsonText);
        copyBtn.textContent = "Copiado";
        setTimeout(() => (copyBtn.textContent = "Copiar JSON"), 1200);
      } catch (err) {
        copyBtn.textContent = "Error";
        setTimeout(() => (copyBtn.textContent = "Copiar JSON"), 1200);
      }
    });
  }
}

function renderError(container, message) {
  if (!container) return;
  container.innerHTML = `<div class="result-block result-block-error">${message}</div>`;
}

