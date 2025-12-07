function renderIAHASHResult(container, iahashDoc) {
  if (!container) return;
  const documentData = iahashDoc.document || iahashDoc || {};
  const verification = iahashDoc.verification || {};
  const iahId = documentData.iah_id || documentData.id || "—";
  const statusText =
    verification.status || documentData.status || documentData.state || "PENDING";
  const errors = verification.errors || iahashDoc.errors || [];
  const normalizedPrompt = verification.normalized_prompt_text;
  const normalizedResponse = verification.normalized_response_text;
  const shouldShowNormalized =
    documentData.store_raw && (normalizedPrompt || normalizedResponse);

  container.classList.add("result-card");
  container.innerHTML = `
    <div class="result-card__head">
      <div>
        <p class="muted">Resultado IA-HASH</p>
        <h3 class="iah-id">${iahId}</h3>
      </div>
      <div class="result-head-actions">
        <button type="button" class="button-secondary copy-json">Copiar JSON</button>
        <span class="badge" data-role="status">${statusText}</span>
      </div>
    </div>
    <div class="result-grid">
      <div>
        <p class="muted label">h_prompt</p>
        <p class="mono" data-field="h_prompt">—</p>
      </div>
      <div>
        <p class="muted label">h_response</p>
        <p class="mono" data-field="h_response">—</p>
      </div>
      <div>
        <p class="muted label">h_total</p>
        <p class="mono" data-field="h_total">—</p>
      </div>
      <div>
        <p class="muted label">Firma</p>
        <p class="mono" data-field="signature">—</p>
      </div>
      <div>
        <p class="muted label">Modelo</p>
        <p class="mono" data-field="model">—</p>
      </div>
      <div>
        <p class="muted label">Issuer ID</p>
        <p class="mono" data-field="issuer">—</p>
      </div>
      <div>
        <p class="muted label">issuer_pk_url</p>
        <p class="mono" data-field="issuer-url">—</p>
      </div>
    </div>
    <details class="result-details">
      <summary>Ver JSON completo</summary>
      <pre class="result-raw muted" data-field="raw">(sin datos)</pre>
    </details>
    <div class="result-meta-grid">
      <div class="result-errors" data-field="errors" style="display:none;">
        <h4>Errores</h4>
        <ul data-field="error-list"></ul>
      </div>
      <div class="result-normalized" data-field="normalized" style="display:none;">
        <h4>Texto normalizado (store_raw)</h4>
        <div class="normalized-row">
          <p class="muted label">Prompt</p>
          <pre class="result-raw" data-field="normalized-prompt"></pre>
        </div>
        <div class="normalized-row">
          <p class="muted label">Respuesta</p>
          <pre class="result-raw" data-field="normalized-response"></pre>
        </div>
      </div>
    </div>
  `;

  const setText = (selector, value) => {
    const el = container.querySelector(selector);
    if (el) {
      el.textContent = value ?? "—";
    }
  };

  setText(".iah-id", iahId);
  setText("[data-field='h_prompt']", documentData.h_prompt || documentData.hash_prompt);
  setText(
    "[data-field='h_response']",
    documentData.h_response || documentData.hash_response,
  );
  setText(
    "[data-field='h_total']",
    documentData.h_total || documentData.hash_total || documentData.h_iah,
  );
  setText("[data-field='signature']", documentData.signature || documentData.firma_total);
  setText("[data-field='model']", documentData.model || "unknown");
  setText("[data-field='issuer']", documentData.issuer_id || "—");
  setText("[data-field='issuer-url']", documentData.issuer_pk_url || "—");

  const statusEl = container.querySelector("[data-role='status']");
  if (statusEl) {
    const normalized = statusText?.toUpperCase?.() || "PENDING";
    statusEl.textContent = normalized;
    statusEl.className = "badge " +
      (normalized === "VERIFIED"
        ? "badge--ok"
        : normalized.includes("INVALID")
        ? "badge--error"
        : "badge--pending");
  }

  const rawEl = container.querySelector("[data-field='raw']");
  if (rawEl) {
    try {
      rawEl.textContent = JSON.stringify(iahashDoc, null, 2);
    } catch (err) {
      rawEl.textContent = String(err);
    }
  }

  const errorBox = container.querySelector("[data-field='errors']");
  const errorList = container.querySelector("[data-field='error-list']");
  if (errorBox && errorList) {
    if (errors.length) {
      errorList.innerHTML = "";
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

  const normalizedBox = container.querySelector("[data-field='normalized']");
  if (normalizedBox) {
    if (shouldShowNormalized) {
      container.querySelector("[data-field='normalized-prompt']").textContent =
        normalizedPrompt || "(sin prompt normalizado)";
      container.querySelector("[data-field='normalized-response']").textContent =
        normalizedResponse || "(sin respuesta normalizada)";
      normalizedBox.style.display = "grid";
    } else {
      normalizedBox.style.display = "none";
    }
  }

  container.style.display = "grid";

  const copyBtn = container.querySelector(".copy-json");
  copyBtn?.addEventListener("click", () => {
    const text = rawEl?.textContent || "";
    if (!text.trim()) return;
    navigator.clipboard?.writeText(text).then(() => {
      copyBtn.textContent = "Copiado";
      setTimeout(() => {
        copyBtn.textContent = "Copiar JSON";
      }, 1200);
    });
  });
}

function showError(container, message) {
  if (!container) return;
  container.classList.add("verify-result", "verify-result--error");
  container.textContent = "";
  const strong = document.createElement("strong");
  strong.textContent = "Error:";
  const span = document.createElement("span");
  span.style.marginLeft = "6px";
  span.textContent = message;
  container.appendChild(strong);
  container.appendChild(span);
  container.style.display = "block";
}
