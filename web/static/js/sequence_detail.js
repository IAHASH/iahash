async function generateHashForStep(card) {
  const promptText = card.querySelector('.step-prompt-text').value.trim();
  const responseText = card.querySelector('.step-response-text').value.trim();
  const model = card.querySelector('.step-model').value.trim() || 'unknown';
  const promptId = card.dataset.promptId || null;
  const resultBox = card.querySelector('.step-result');

  if (!promptText || !responseText) {
    resultBox.textContent = 'Necesitas prompt y respuesta para generar IA-HASH.';
    return;
  }

  resultBox.textContent = 'Generando IA-HASH...';

  try {
    const res = await fetch('/api/verify/pair', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        prompt_text: promptText,
        response_text: responseText,
        prompt_id: promptId || undefined,
        model,
        store_raw: true,
      }),
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'No se pudo generar IA-HASH');
    }

    const data = await res.json();
    resultBox.textContent = JSON.stringify(data, null, 2);
  } catch (err) {
    console.error(err);
    resultBox.textContent = err.message;
  }
}

document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.sequence-step form').forEach((form) => {
    form.addEventListener('submit', (event) => {
      event.preventDefault();
      const card = form.closest('.sequence-step');
      if (card) {
        generateHashForStep(card);
      }
    });
  });
});
