document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('sequence-form');
  const stepsContainer = document.getElementById('steps-container');
  const template = document.getElementById('step-template');
  const message = document.getElementById('sequence-message');
  const addStepBtn = document.getElementById('add-step');

  const updateLabels = () => {
    stepsContainer.querySelectorAll('.step-card').forEach((card, idx) => {
      card.querySelector('.step-number').textContent = idx + 1;
      const title = card.querySelector('.step-title');
      card.querySelector('.step-title-label').textContent = title.value || 'Paso';
    });
  };

  const addStep = () => {
    const clone = template.content.cloneNode(true);
    const card = clone.querySelector('.step-card');

    card.querySelector('.step-title').addEventListener('input', updateLabels);
    card.querySelector('.remove-step').addEventListener('click', () => {
      card.remove();
      updateLabels();
    });

    stepsContainer.appendChild(clone);
    updateLabels();
  };

  addStepBtn?.addEventListener('click', addStep);

  form?.addEventListener('submit', async (event) => {
    event.preventDefault();
    message.textContent = 'Guardando...';

    const payload = {
      slug: form.slug.value.trim(),
      title: form.title.value.trim(),
      description: form.description.value.trim(),
      category: form.category.value.trim(),
      visibility: form.visibility.value,
      steps: [],
    };

    stepsContainer.querySelectorAll('.step-card').forEach((card, idx) => {
      const titleEl = card.querySelector('.step-title');
      const descEl = card.querySelector('.step-description');
      const promptEl = card.querySelector('.step-prompt');

      if (titleEl.value.trim()) {
        payload.steps.push({
          position: idx + 1,
          title: titleEl.value.trim(),
          description: descEl.value.trim(),
          prompt_id: promptEl.value ? Number(promptEl.value) : null,
        });
      }
    });

    try {
      const res = await fetch('/api/sequences', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'No se pudo guardar la secuencia');
      }

      const data = await res.json();
      message.textContent = 'Secuencia creada correctamente';
      if (data.sequence?.slug) {
        setTimeout(() => {
          window.location.href = `/sequences/${data.sequence.slug}`;
        }, 600);
      }
    } catch (err) {
      console.error(err);
      message.textContent = err.message;
    }
  });

  // Inicializa con un paso por defecto
  addStep();
});
