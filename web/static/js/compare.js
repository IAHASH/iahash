const BASE_FIELDS = ["h_prompt", "h_response", "h_total", "model", "timestamp"];
const OPTIONAL_FIELDS = [
  "prompt_id",
  "issuer_id",
  "issuer_pk_url",
  "conversation_url",
  "provider",
  "subject_id",
  "prompt_hmac",
  "prompt_hmac_verified",
  "type",
  "mode",
  "store_raw",
];

function setText(targetId, value) {
  const el = document.getElementById(targetId);
  if (!el) return;
  el.textContent = value || "";
}

function readFileToTextarea(fileInputId, textareaId) {
  const input = document.getElementById(fileInputId);
  const textarea = document.getElementById(textareaId);
  if (!input || !textarea) return;

  input.addEventListener("change", () => {
    const [file] = input.files || [];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (e) => {
      textarea.value = e.target?.result || "";
    };
    reader.readAsText(file);
  });
}

function parseDocument(raw, label) {
  if (!raw) {
    throw new Error(`El documento ${label} está vacío`);
  }
  try {
    return JSON.parse(raw);
  } catch (err) {
    throw new Error(`JSON de ${label} inválido: ${err}`);
  }
}

function evaluateField(aValue, bValue) {
  if (aValue === undefined && bValue === undefined) {
    return { status: "warn", label: "Sin datos" };
  }
  if (aValue === bValue) {
    return { status: "match", label: "Coincide" };
  }
  if (aValue === undefined || bValue === undefined) {
    return { status: "warn", label: "Falta en uno" };
  }
  return { status: "mismatch", label: "Diferente" };
}

function createDiffRow(key, label, valueA, valueB) {
  const { status, label: statusLabel } = evaluateField(valueA, valueB);
  const statusClass = `diff-pill diff-pill--${status}`;

  return `
    <div class="diff-row">
      <div class="diff-key">${label}</div>
      <div class="diff-value mono">${valueA ?? "—"}</div>
      <div class="diff-value mono">${valueB ?? "—"}</div>
      <div class="diff-status"><span class="${statusClass}">${statusLabel}</span></div>
    </div>
  `;
}

function renderDifferences(docA, docB) {
  const table = document.getElementById("diff-table");
  if (!table) return;

  const rows = [];
  rows.push(
    "<div class=\"diff-head\"><div>Campo</div><div>Documento A</div><div>Documento B</div><div>Estado</div></div>"
  );

  BASE_FIELDS.forEach((field) => {
    rows.push(createDiffRow(field, field, docA[field], docB[field]));
  });

  rows.push('<div class="diff-separator">Opcionales</div>');
  OPTIONAL_FIELDS.forEach((field) => {
    const hasAny = docA[field] !== undefined || docB[field] !== undefined;
    if (!hasAny) return;
    rows.push(createDiffRow(field, field, docA[field], docB[field]));
  });

  table.innerHTML = rows.join("\n");
}

function handleCompare() {
  setText("compare-error", "");
  const rawA = document.getElementById("json-a")?.value.trim();
  const rawB = document.getElementById("json-b")?.value.trim();

  let docA;
  let docB;

  try {
    docA = parseDocument(rawA, "A");
    setText("status-a", `IAH: ${docA.iah_id || docA.id || "(sin id)"}`);
  } catch (err) {
    setText("compare-error", err.message);
    return;
  }

  try {
    docB = parseDocument(rawB, "B");
    setText("status-b", `IAH: ${docB.iah_id || docB.id || "(sin id)"}`);
  } catch (err) {
    setText("compare-error", err.message);
    return;
  }

  renderDifferences(docA, docB);
  document.getElementById("compare-result").style.display = "grid";
  document.getElementById("compare-summary").textContent = "Comparación completada";
}

function resetForm() {
  ["json-a", "json-b"].forEach((id) => {
    const el = document.getElementById(id);
    if (el) el.value = "";
  });
  ["status-a", "status-b", "compare-error"].forEach((id) => setText(id, ""));
  const result = document.getElementById("compare-result");
  if (result) result.style.display = "none";
}

document.addEventListener("DOMContentLoaded", () => {
  readFileToTextarea("file-a", "json-a");
  readFileToTextarea("file-b", "json-b");

  document.getElementById("compare-btn")?.addEventListener("click", handleCompare);
  document.getElementById("reset-btn")?.addEventListener("click", resetForm);
});
