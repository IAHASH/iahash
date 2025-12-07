function clearIAHASHContainer(container) {
  if (!container) return;
  container.innerHTML = "";
  container.style.display = "none";
  container.className = "result-card";
}

function renderLoading(container, labelText = "Procesando…") {
  if (!container) return;
  clearIAHASHContainer(container);
  container.classList.add("result-card", "verify-result");
  container.innerHTML = `<div class="loading">${labelText}</div>`;
  container.style.display = "block";
}

function renderError(container, payload) {
  if (!container) return;
  const message =
    (payload && payload.error && payload.error.message) ||
    payload?.detail ||
    payload?.message ||
    payload?.toString?.() ||
    "Ocurrió un error";

  clearIAHASHContainer(container);
  container.classList.add("verify-result", "verify-result--error");
  container.innerHTML = `<strong>Error:</strong> <span style="margin-left: 6px;">${message}</span>`;
  container.style.display = "block";
}

function renderIssuedDocument(container, response) {
  if (!container) return;
  const isIssued =
    (response?.status ? response.status === "ISSUED" : Boolean(response?.document)) &&
    response?.document;
  if (!isIssued) {
    return renderError(container, response || { message: "Respuesta inválida" });
  }

  const documentData = response.document || {};
  const verification = response?.verification || {};
  const normalizedPrompt = verification.normalized_prompt_text;
  const normalizedResponse = verification.normalized_response_text;
  const shouldShowNormalized =
    documentData.store_raw && (normalizedPrompt || normalizedResponse);

  const iahId = documentData.iah_id || documentData.id || "—";
  const statusText =
    (verification?.status || response?.status || "ISSUED").toString().toUpperCase();
  const statusDetail = verification?.status_detail;
  const errors = verification.errors || response?.errors || [];
  const warnings = verification.warnings || [];

  clearIAHASHContainer(container);

  container.innerHTML = `
    <div class="result-card__head">
      <div>
        <p class="muted">Resultado IA-HASH</p>
        <h3 class="iah-id">${iahId}</h3>
      </div>
      <div class="result-head-actions">
        <button type="button" class="button-secondary copy-json">Copiar JSON IA-HASH</button>
        <span class="badge" data-role="status">${statusText}</span>
      </div>
    </div>
    <div class="result-summary">
      <div>
        <p class="muted label">Modelo</p>
        <p class="mono" data-field="model">—</p>
      </div>
      <div>
        <p class="muted label">Proveedor</p>
        <p class="mono" data-field="provider">—</p>
      </div>
      <div>
        <p class="muted label">Timestamp</p>
        <p class="mono" data-field="timestamp">—</p>
      </div>
      <div>
        <p class="muted label">Hash público del prompt</p>
        <p class="mono" data-field="prompt-public">—</p>
      </div>
      <div>
        <p class="muted label">Conversation URL</p>
        <p class="mono" data-field="conversation-url">—</p>
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
      <div class="result-errors" data-field="warnings" style="display:none;">
        <h4>Warnings</h4>
        <ul data-field="warning-list"></ul>
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
      if (selector === "[data-field='conversation-url']" && value) {
        el.textContent = "";
        const link = document.createElement("a");
        link.href = value;
        link.target = "_blank";
        link.rel = "noreferrer";
        link.textContent = value;
        el.appendChild(link);
        return;
      }
      el.textContent = value ?? "—";
    }
  };

  setText(".iah-id", iahId);
  setText(
    "[data-role='status']",
    statusDetail ? `${statusText} · ${statusDetail}` : statusText,
  );
  setText("[data-field='h_prompt']", documentData.h_prompt || documentData.hash_prompt);
  setText("[data-field='h_response']", documentData.h_response || documentData.hash_response);
  setText(
    "[data-field='h_total']",
    documentData.h_total || documentData.hash_total || documentData.h_iah,
  );
  setText("[data-field='signature']", documentData.signature || documentData.firma_total);
  setText("[data-field='model']", documentData.model || "unknown");
  setText("[data-field='provider']", documentData.provider || "—");
  setText("[data-field='issuer']", documentData.issuer_id || "—");
  const resolvedIssuerPk =
    documentData.issuer_pk_url || verification.resolved_issuer_pk_url || "—";
  setText("[data-field='issuer-url']", resolvedIssuerPk);
  setText("[data-field='timestamp']", documentData.timestamp || "—");
  setText(
    "[data-field='prompt-public']",
    documentData.prompt_public_hash || documentData.h_public || "—",
  );
  setText("[data-field='conversation-url']", documentData.conversation_url || "");

  const statusEl = container.querySelector("[data-role='status']");
  if (statusEl) {
    const normalized = statusText || "ISSUED";
    statusEl.textContent = normalized;
    statusEl.className =
      "badge " +
      (normalized.includes("VERIFIED")
        ? "badge--ok"
        : normalized.includes("INVALID")
        ? "badge--error"
        : "badge--pending");
  }

  const rawEl = container.querySelector("[data-field='raw']");
  if (rawEl) {
    try {
      rawEl.textContent = JSON.stringify(response, null, 2);
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

  const warningBox = container.querySelector("[data-field='warnings']");
  const warningList = container.querySelector("[data-field='warning-list']");
  if (warningBox && warningList) {
    if (warnings.length) {
      warningList.innerHTML = "";
      warnings.forEach((warn) => {
        const li = document.createElement("li");
        li.textContent = warn;
        warningList.appendChild(li);
      });
      warningBox.style.display = "block";
    } else {
      warningBox.style.display = "none";
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
        copyBtn.textContent = "Copiar JSON IA-HASH";
      }, 1200);
    });
  });
}

function renderShareVerification(container, payload) {
  if (!container) return;
  if (!payload || payload.success !== true) {
    const message = payload?.error || payload?.reason || "Verificación fallida";
    return renderError(container, { message });
  }

  clearIAHASHContainer(container);
  container.classList.add("result-card", "verify-result");

  const provider = payload.provider || "chatgpt";
  const model = payload.model || "unknown";
  const conversationUrl = payload.conversation_url || payload.url;

  container.innerHTML = `
    <div class="result-card__head">
      <div>
        <p class="muted">Verificación de conversación</p>
        <h3 class="iah-id">ChatGPT share</h3>
      </div>
      <div class="result-head-actions">
        <span class="badge badge--ok" data-role="status">OK</span>
      </div>
    </div>
    <div class="result-summary">
      <div>
        <p class="muted label">Proveedor</p>
        <p class="mono" data-field="provider">${provider}</p>
      </div>
      <div>
        <p class="muted label">Modelo</p>
        <p class="mono" data-field="model">${model}</p>
      </div>
      <div>
        <p class="muted label">Conversation URL</p>
        <p class="mono" data-field="conversation-url">${conversationUrl || "—"}</p>
      </div>
    </div>
    <div class="result-meta-grid">
      <div class="result-normalized" data-field="normalized" style="display:grid;">
        <h4>Prompt extraído</h4>
        <pre class="result-raw" data-field="prompt-block"></pre>
        <h4>Respuesta extraída</h4>
        <pre class="result-raw" data-field="response-block"></pre>
      </div>
    </div>
    <details class="result-details">
      <summary>Ver JSON completo</summary>
      <pre class="result-raw muted" data-field="raw">(sin datos)</pre>
    </details>
  `;

  const promptBlock = container.querySelector("[data-field='prompt-block']");
  if (promptBlock) {
    promptBlock.textContent = payload.extracted_prompt || "(sin prompt)";
  }

  const responseBlock = container.querySelector("[data-field='response-block']");
  if (responseBlock) {
    responseBlock.textContent = payload.extracted_answer || "(sin respuesta)";
  }

  const convEl = container.querySelector("[data-field='conversation-url']");
  if (convEl && conversationUrl) {
    convEl.textContent = "";
    const link = document.createElement("a");
    link.href = conversationUrl;
    link.target = "_blank";
    link.rel = "noreferrer";
    link.textContent = conversationUrl;
    convEl.appendChild(link);
  }

  const rawEl = container.querySelector("[data-field='raw']");
  if (rawEl) {
    try {
      rawEl.textContent = JSON.stringify(payload, null, 2);
    } catch (err) {
      rawEl.textContent = String(err);
    }
  }

  container.style.display = "grid";
}

window.renderIssuedDocument = renderIssuedDocument;
window.renderError = renderError;
window.renderLoading = renderLoading;
window.renderIAHASHResult = renderIssuedDocument;
window.renderIAHASHError = renderError;
window.renderShareVerification = renderShareVerification;
window.clearIAHASHContainer = clearIAHASHContainer;
