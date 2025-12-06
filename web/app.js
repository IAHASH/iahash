let lastDocument = null;

function prettyPrintJson(obj) {
  try {
    return JSON.stringify(obj, null, 2);
  } catch (_) {
    return String(obj);
  }
}

function setIssueStatus(text, type = "info") {
  const el = document.getElementById("issue-status");
  if (!el) return;
  el.textContent = text || "";
  el.style.color =
    type === "error" ? "#e73c56" : type === "success" ? "#22a179" : "#6b7280";
}

function setVerifyStatus(text, type = "info") {
  const el = document.getElementById("verify-status");
  if (!el) return;
  el.textContent = text || "";
  el.style.color =
    type === "error" ? "#e73c56" : type === "success" ? "#22a179" : "#6b7280";
}

function updateBadge({ valid, reason }) {
  const badge = document.getElementById("verify-badge");
  const hint = document.getElementById("verify-hint");
  if (!badge || !hint) return;

  badge.classList.remove("badge-success", "badge-error");

  if (valid === true) {
    badge.textContent = "IA-HASH válido";
    badge.classList.add("badge-success");
    hint.textContent = "Documento verificado. iahash.com verified ✓";
  } else if (valid === false) {
    badge.textContent = "IA-HASH inválido";
    badge.classList.add("badge-error");
    hint.textContent = reason || "La verificación ha fallado.";
  } else {
    badge.textContent = "Sin verificar";
    hint.textContent = "Genera un IA-HASH o pega uno para probarlo.";
  }
}

async function handleIssue(event) {
  event.preventDefault();

  const btn = document.getElementById("btn-issue");
  if (!btn) return;

  const prompt_maestro = document.getElementById("prompt_maestro").value.trim();
  const respuesta = document.getElementById("respuesta").value.trim();
  const modelo = document.getElementById("modelo").value.trim();
  const prompt_id = document.getElementById("prompt_id").value.trim() || null;
  const subject_id =
    document.getElementById("subject_id").value.trim() || null;

  if (!prompt_maestro || !respuesta || !modelo) {
    setIssueStatus("Faltan campos obligatorios.", "error");
    return;
  }

  btn.disabled = true;
  setIssueStatus("Generando IA-HASH…");

  try {
    const payload = {
      prompt_maestro,
      respuesta,
      modelo,
      prompt_id,
      subject_id,
    };

    const res = await fetch("/api/issue", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!res.ok) {
      const text = await res.text();
      throw new Error(text || "Error en /api/issue");
    }

    const data = await res.json();
    lastDocument = data;

    // Pintar JSON bonito
    const out = document.getElementById("document-output");
    if (out) {
      out.textContent = prettyPrintJson(data);
    }

    // Rellenar textarea de verificación con el último doc
    const verifyInput = document.getElementById("verify-input");
    if (verifyInput) {
      verifyInput.value = prettyPrintJson(data);
    }

    setIssueStatus("IA-HASH generado correctamente.", "success");
    updateBadge({ valid: true, reason: null });
    setVerifyStatus("Documento recién emitido por este issuer.", "success");
  } catch (err) {
    console.error(err);
    setIssueStatus("Error generando IA-HASH.", "error");
    updateBadge({ valid: false, reason: "Error en la emisión." });
  } finally {
    btn.disabled = false;
  }
}

async function handleVerify() {
  const btn = document.getElementById("btn-verify");
  if (!btn) return;

  btn.disabled = true;
  setVerifyStatus("Verificando documento…");

  try {
    const verifyInput = document.getElementById("verify-input");
    let docText = verifyInput.value.trim();

    let docObject = null;

    if (docText) {
      try {
        docObject = JSON.parse(docText);
      } catch (err) {
        setVerifyStatus("El contenido pegado no es JSON válido.", "error");
        btn.disabled = false;
        return;
      }
    } else if (lastDocument) {
      docObject = lastDocument;
    } else {
      setVerifyStatus(
        "No hay documento que verificar. Genera uno o pega un JSON.",
        "error"
      );
      btn.disabled = false;
      return;
    }

    const res = await fetch("/api/verify", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(docObject),
    });

    if (!res.ok) {
      const text = await res.text();
      throw new Error(text || "Error en /api/verify");
    }

    const data = await res.json();
    const { valid, reason } = data;

    // Actualizamos siempre el panel de salida con el doc que hemos verificado
    const out = document.getElementById("document-output");
    if (out) out.textContent = prettyPrintJson(docObject);

    if (valid) {
      setVerifyStatus("IA-HASH verificado correctamente.", "success");
    } else {
      setVerifyStatus(reason || "La verificación ha fallado.", "error");
    }

    updateBadge({ valid, reason });
  } catch (err) {
    console.error(err);
    setVerifyStatus("Error en la verificación.", "error");
    updateBadge({ valid: false, reason: "Error en la llamada /api/verify." });
  } finally {
    btn.disabled = false;
  }
}

function handleUseLast() {
  if (!lastDocument) {
    setVerifyStatus(
      "No hay todavía ningún IA-HASH generado en esta sesión.",
      "error"
    );
    return;
  }
  const verifyInput = document.
