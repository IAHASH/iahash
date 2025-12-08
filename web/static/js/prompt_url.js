// prompt_url.js - verificación de conversación pública + prompt

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

async function loadPrompts() {
  const select = document.getElementById('master-prompt-select');
  if (!select) return;

  try {
    const res = await fetch('/api/prompts');
    const data = await res.json();
    (data.prompts || []).forEach((prompt) => {
      const opt = document.createElement('option');
      opt.value = prompt.slug || prompt.id;
      opt.textContent = prompt.title || prompt.slug;
      opt.dataset.slug = prompt.slug;
      opt.dataset.id = prompt.id;
      select.appendChild(opt);
    });
  } catch (err) {
    console.warn('No se pudieron cargar los prompts', err);
  }
}

async function updatePromptTextFromSelect() {
  const select = document.getElementById('master-prompt-select');
  const textarea = document.getElementById('prompt-text');
  const hashEl = document.getElementById('prompt-hash');

  if (!select || !textarea) return;
  const value = select.value;
  if (!value) {
    textarea.value = '';
    hashEl.textContent = 'h_public: —';
    return;
  }

  try {
    const res = await fetch(`/api/prompts/${value}`);
    const data = await res.json();
    const prompt = data.prompt;
    if (prompt) {
      textarea.value = prompt.full_prompt || '';
      hashEl.textContent = `h_public: ${prompt.h_public || '—'}`;
    }
  } catch (err) {
    hashEl.textContent = 'No se pudo cargar el prompt seleccionado';
  }
}

function looksLikeShareUrl(url) {
  return /^https:\/\/(chatgpt\.com|chat\.openai\.com)\/share\/[0-9a-fA-F\-]+/.test(url || '');
}

async function sendPromptUrl() {
  const select = document.getElementById('master-prompt-select');
  const promptId = select?.value || '';
  const promptText = document.getElementById('prompt-text').value;
  const url = document.getElementById('conversation-url').value.trim();
  const model = document.getElementById('conversation-model').value || 'unknown';
  const button = document.getElementById('conversation-submit');
  const result = document.getElementById('prompt-url-result');

  if (!promptId && !promptText.trim()) {
    renderResult(result, { ok: false, error_message: 'Selecciona un prompt maestro o pega el texto exacto.' });
    return;
  }

  if (!looksLikeShareUrl(url)) {
    renderResult(result, { ok: false, error_message: 'URL inválida. Usa un enlace público de chatgpt.com/share/…' });
    return;
  }

  button.disabled = true;
  renderResult(result, { ok: true, status: 'ENVIANDO', data: { hashes: {}, document: {} } });

  try {
    const res = await fetch('/api/issue/from_prompt_url', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        prompt_id: promptId || null,
        prompt_text: promptId ? null : promptText,
        share_url: url,
        provider: 'chatgpt',
        model,
      }),
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
  loadPrompts().then(updatePromptTextFromSelect);
  document.getElementById('master-prompt-select')?.addEventListener('change', updatePromptTextFromSelect);
  document.getElementById('conversation-submit')?.addEventListener('click', sendPromptUrl);
});
