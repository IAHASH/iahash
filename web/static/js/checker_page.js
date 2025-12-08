// checker_page.js - comprobador de documentos IA-HASH

function renderResult(container, payload) {
  const statusEl = container.querySelector('[data-status]');
  const messageEl = container.querySelector('[data-message]');
  const hashesEl = container.querySelector('[data-hashes]');
  const preEl = container.querySelector('pre');

  const setStatus = (text, type = 'neutral') => {
    statusEl.textContent = text;
    statusEl.className = `status-line status-${type}`;
  };

  hashesEl.innerHTML = '';

  if (!payload || payload.ok === false) {
    const msg = payload?.error_message || 'Documento inválido';
    setStatus(`Error · ${payload?.error_code || ''}`.trim(), 'error');
    messageEl.textContent = msg;
    preEl.textContent = msg;
    const data = payload?.data || {};
    const hashes = data.hashes || {};
    Object.entries(hashes).forEach(([label, value]) => {
      if (!value) return;
      const item = document.createElement('div');
      item.className = 'hash-item';
      item.innerHTML = `<strong>${label}</strong><br>${value}`;
      hashesEl.appendChild(item);
    });
    return;
  }

  const data = payload.data || {};
  const verification = data.verification || {};
  const statusLabel = verification.status || payload.status || 'OK';
  const ok = payload.ok !== false && verification.valid !== false;
  setStatus(`${statusLabel}`, ok ? 'ok' : 'error');

  messageEl.textContent = verification.valid === false
    ? (verification.errors || []).join('; ')
    : 'Documento verificado correctamente.';

  const hashes = data.hashes || {};
  Object.entries({
    iah_id: data.iah_id,
    h_prompt: hashes.h_prompt,
    h_response: hashes.h_response,
    h_total: hashes.h_total,
    signature: hashes.signature,
    issuer_pk_url: hashes.issuer_pk_url,
  }).forEach(([label, value]) => {
    if (!value) return;
    const item = document.createElement('div');
    item.className = 'hash-item';
    item.innerHTML = `<strong>${label}</strong><br>${value}`;
    hashesEl.appendChild(item);
  });

  try {
    preEl.textContent = JSON.stringify(data.document || payload, null, 2);
  } catch (err) {
    preEl.textContent = String(err);
  }
}

function parseInputValue(raw) {
  const text = raw.trim();
  if (!text) return null;
  if (text.startsWith('{') && text.endsWith('}')) {
    try {
      return JSON.parse(text);
    } catch (err) {
      return { __error: `JSON inválido: ${err}` };
    }
  }
  return text;
}

async function runCheck() {
  const raw = document.getElementById('checker-input').value;
  const parsed = parseInputValue(raw);
  const result = document.getElementById('checker-result');
  const pkUrl = document.getElementById('checker-pk-url').value || null;
  const button = document.getElementById('checker-submit');

  if (!parsed) {
    renderResult(result, { ok: false, error_message: 'Debes pegar un documento IA-HASH o un identificador.' });
    return;
  }

  if (parsed && parsed.__error) {
    renderResult(result, { ok: false, error_message: parsed.__error });
    return;
  }

  button.disabled = true;
  renderResult(result, { ok: true, status: 'ENVIANDO', data: { hashes: {}, document: {} } });

  const payload = typeof parsed === 'string'
    ? { identifier: parsed, issuer_pk_url: pkUrl }
    : { document: parsed, issuer_pk_url: pkUrl };

  try {
    const res = await fetch('/api/check', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    const data = await res.json();
    if (!res.ok || data.ok === false) {
      renderResult(result, data);
      return;
    }
    renderResult(result, data);
  } catch (err) {
    renderResult(result, { ok: false, error_message: `Error de red: ${err}` });
  } finally {
    button.disabled = false;
  }
}

window.addEventListener('DOMContentLoaded', () => {
  document.getElementById('checker-submit')?.addEventListener('click', runCheck);
});
