// pairs.js - manejo de la página de pares IA-HASH

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
    const msg = payload?.error_message || 'Ocurrió un error';
    setStatus(`Error · ${payload?.error_code || ''}`.trim(), 'error');
    messageEl.textContent = msg;
    preEl.textContent = msg;
    return;
  }

  const data = payload.data || {};
  const verification = data.verification || {};
  const statusLabel = verification.status || payload.status || 'OK';
  const ok = payload.ok !== false && verification.valid !== false;
  setStatus(`${statusLabel}`, ok ? 'ok' : 'error');

  messageEl.textContent = verification.valid === false
    ? (verification.errors || []).join('; ')
    : 'Documento IA-HASH emitido y verificado localmente.';

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

async function sendPair() {
  const prompt = document.getElementById('pair-prompt').value;
  const answer = document.getElementById('pair-answer').value;
  const model = document.getElementById('pair-model').value || 'unknown';
  const button = document.getElementById('pair-submit');
  const result = document.getElementById('pair-result');

  if (!prompt.trim() || !answer.trim()) {
    renderResult(result, { ok: false, error_message: 'Prompt y respuesta son obligatorios.' });
    return;
  }

  button.disabled = true;
  renderResult(result, { ok: true, status: 'ENVIANDO', data: { hashes: {}, document: {} } });

  try {
    const res = await fetch('/api/verify/pair', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ prompt_text: prompt, response_text: answer, model }),
    });

    const payload = await res.json();
    if (!res.ok || payload.ok === false) {
      renderResult(result, payload);
      return;
    }
    renderResult(result, payload);
  } catch (err) {
    renderResult(result, { ok: false, error_message: `Error de red: ${err}` });
  } finally {
    button.disabled = false;
  }
}

window.addEventListener('DOMContentLoaded', () => {
  document.getElementById('pair-submit')?.addEventListener('click', sendPair);
});
