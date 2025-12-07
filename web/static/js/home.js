(function () {
  /* ----------------- VERIFICACIÓN EXISTENTE ----------------- */

  const form = document.getElementById("verify-form");
  const input = document.getElementById("iah-json-input");
  const clearBtn = document.getElementById("clear-btn");

  const resultBox = document.getElementById("result");
  const resultTitle = document.getElementById("result-title");
  const resultMessage = document.getElementById("result-message");
  const resultRaw = document.getElementById("result-raw");

  function setStateIdle() {
    resultBox.style.display = "none";
    resultBox.className = "verify-result verify-result--idle";
    resultTitle.textContent = "Listo para verificar.";
    resultMessage.textContent =
      "Pega un documento IA-HASH JSON y pulsa “Verificar IA-HASH”.";
    resultRaw.textContent = "(sin datos)";
  }

  function setStateLoading() {
    resultBox.style.display = "block";
    resultBox.className = "verify-result verify-result--loading";
    resultTitle.textContent = "Verificando…";
    resultMessage.textContent = "Recalculando hashes y firma.";
    resultRaw.textContent = "(esperando respuesta del servidor)";
  }

  function setStateError(msg) {
    resultBox.style.display = "block";
    resultBox.className = "verify-result verify-result--error";
    resultTitle.textContent = "Error de verificación";
    resultMessage.textContent = msg;
  }

  function setStateSuccess(isValid, data) {
    resultBox.style.display = "block";
    if (isValid) {
      resultBox.className = "verify-result verify-result--ok";
      resultTitle.textContent = "IA-HASH VERIFIED";
      resultMessage.textContent =
        "Documento IA-HASH válido. Hashes y firma coinciden.";
    } else {
      resultBox.className = "verify-result verify-result--fail";
      resultTitle.textContent = "NO VERIFICADO";
      resultMessage.textContent =
        "Hash o firma no coinciden. El documento no es auténtico.";
    }

    try {
      resultRaw.textContent = JSON.stringify(data, null, 2);
    } catch (err) {
      resultRaw.textContent = String(err);
    }
  }

  form.addEventListener("submit", async function (event) {
    event.preventDefault();

    let doc;
    try {
      doc = JSON.parse(input.value);
    } catch (err) {
      setStateError("JSON inválido.");
      resultRaw.textContent = String(err);
      return;
    }

    setStateLoading();

    try {
      const res = await fetch("/api/check", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ document: doc }),
      });

      const data = await res.json();
      if (!res.ok) {
        const detail = data?.detail || "Error de verificación";
        setStateError(detail);
        resultRaw.textContent = JSON.stringify(data, null, 2);
        return;
      }

      const verification = data.verification || data;
      const isValid =
        verification.valid === true ||
        verification.status === "valid" ||
        verification.verified === true;

      setStateSuccess(Boolean(isValid), data);
    } catch (err) {
      setStateError("Error de red o servidor.");
      resultRaw.textContent = String(err);
    }
  });

  clearBtn.addEventListener("click", function () {
    input.value = "";
    setStateIdle();
  });

  setStateIdle();

  /* --------------- EMISIÓN IA-HASH (PROMPT + RESPUESTA) --------------- */

  const issueBtn = document.getElementById("issue-btn");
  const issueClear = document.getElementById("issue-clear-btn");
  const issueResult = document.getElementById("issue-result");
  const issueMessage = document.getElementById("issue-message");
  const issueTitle = document.getElementById("issue-title");
  const issueOutput = document.getElementById("issue-json-output");

  issueBtn?.addEventListener("click", async () => {
    const prompt = document.getElementById("issue-prompt").value.trim();
    const response = document.getElementById("issue-response").value.trim();
    const model = document.getElementById("issue-model").value.trim();
    const subject = document.getElementById("issue-subject").value.trim();

    if (!prompt || !response) {
      issueResult.style.display = "block";
      issueResult.className = "verify-result verify-result--error";
      issueTitle.textContent = "Faltan datos";
      issueMessage.textContent =
        "Prompt y respuesta son obligatorios para emitir IA-HASH.";
      issueOutput.textContent = "";
      return;
    }

    issueResult.style.display = "block";
    issueResult.className = "verify-result verify-result--loading";
    issueTitle.textContent = "Emitiendo IA-HASH…";
    issueMessage.textContent = "Contactando con el endpoint /api/verify/pair.";
    issueOutput.textContent = "(esperando respuesta)";

    try {
      const res = await fetch("/api/verify/pair", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          prompt_text: prompt,
          response_text: response,
          model: model || "unknown",
          subject_id: subject || null,
        }),
      });

      const data = await res.json();
      if (!res.ok) {
        const detail = data?.detail || "No se pudo emitir el documento IA-HASH.";
        issueResult.className = "verify-result verify-result--error";
        issueTitle.textContent = "Error";
        issueMessage.textContent = detail;
        issueOutput.textContent = JSON.stringify(data, null, 2);
        return;
      }

      issueResult.className = "verify-result verify-result--ok";
      issueTitle.textContent = "IA-HASH emitido ✔";
      issueMessage.textContent = "Copia y guarda el JSON IA-HASH.";
      issueOutput.textContent = JSON.stringify(data, null, 2);
    } catch (err) {
      issueResult.className = "verify-result verify-result--error";
      issueTitle.textContent = "Error";
      issueMessage.textContent = "No se pudo emitir el documento IA-HASH.";
      issueOutput.textContent = String(err);
    }
  });

  issueClear?.addEventListener("click", () => {
    document.getElementById("issue-prompt").value = "";
    document.getElementById("issue-response").value = "";
    document.getElementById("issue-model").value = "";
    document.getElementById("issue-subject").value = "";
    issueResult.style.display = "none";
  });
})();
