-- Seed data for IA-HASH v1.2
--
-- Puede ejecutarse sobre una base vacía o existente: los INSERT usan
-- "OR IGNORE" para no fallar si ya hay datos previos.

INSERT OR IGNORE INTO prompts (
    slug,
    owner_id,
    title,
    description,
    full_prompt,
    category,
    is_master,
    visibility,
    h_public
)
VALUES
    (
        'cv',
        'iahash',
        'CV Honesto Cognitivo',
        'Retrato profesional sincero con foco en logros reales.',
        'Eres un sistema de análisis de trayectoria vital y profesional llamado IA-HASH CV.\n\nOBJETIVO\nAyudarme a construir un CV HONESTO Y COGNITIVO:\n- sin adornos,\n- sin postureo,\n- sin lenguaje vacío,\n- basado en hechos, decisiones, hábitos y patrones reales.\n\nREGLAS DE INTEGRIDAD\n- No inventes logros, títulos ni cargos.\n- No cambies fechas ni amplíes responsabilidades.\n- Si te falta información, marca ese punto como ‘INCOMPLETO’ en lugar de rellenarlo.\n- Evita frases tipo ‘proactivo’ salvo que vayan ligadas a hechos concretos.\n\nPRIVACIDAD\n- No uses nombres reales de personas.\n- No des datos personales sensibles.\n- Para empresas o proyectos, usa nombres genéricos si no hay permiso explícito.\n\nESTRUCTURA DE SALIDA\n1. RESUMEN HONESTO (3–5 frases)\n2. LÍNEA DE TIEMPO CLAVE (años / aprendizajes)\n3. COMPETENCIAS REALES (fortalezas con ejemplos, debilidades)\n4. ESTILO DE TRABAJO (condiciones para rendir, bloqueos)\n5. VALOR DIFERENCIAL\n6. ALERTAS Y RIESGOS (3–5)\n7. PRÓXIMO PASO LÓGICO (reforzar, dejar de hacer)',
        'cv',
        1,
        'public',
        '28321723bccc8727a57bc6997bd6889524c3f862cc7956fc652ba80ce8252e91bd'
    ),
    (
        'habit-builder-v1',
        'iahash',
        'Constructor de Hábitos',
        'Plan corto en 3 pasos para construir un hábito.',
        'Actúa como coach de hábitos. Devuelve un plan de 3 pasos personalizado a partir del objetivo indicado.',
        'wellbeing',
        1,
        'public',
        'f8e8f22ae29611469bba50ea2072a66b3887ed679c955b10c4448e8cabd7e56c'
    );

INSERT OR IGNORE INTO sequences (slug, title, description, category, visibility)
VALUES
    (
        'onboarding-7d',
        'Onboarding en 7 días',
        'Secuencia de prompts para acompañar una semana de trabajo.',
        'coaching',
        'public'
    ),
    (
        'consistency-check',
        'Chequeo de Consistencia',
        'Comparar respuestas de un mismo prompt en diferentes modelos.',
        'qa',
        'public'
    );

INSERT OR IGNORE INTO sequence_steps (sequence_id, position, title, description, prompt_id)
VALUES
    (
        (SELECT id FROM sequences WHERE slug = 'onboarding-7d'),
        1,
        'Día 1 - CV Honesto',
        'Construye tu CV base.',
        (SELECT id FROM prompts WHERE slug = 'cv')
    ),
    (
        (SELECT id FROM sequences WHERE slug = 'onboarding-7d'),
        2,
        'Día 3 - Refinar hábitos',
        'Primer bloque de hábitos.',
        (SELECT id FROM prompts WHERE slug = 'habit-builder-v1')
    ),
    (
        (SELECT id FROM sequences WHERE slug = 'consistency-check'),
        1,
        'Run CV prompt en modelo A',
        'Primera ejecución.',
        (SELECT id FROM prompts WHERE slug = 'cv')
    ),
    (
        (SELECT id FROM sequences WHERE slug = 'consistency-check'),
        2,
        'Run CV prompt en modelo B',
        'Segunda ejecución.',
        (SELECT id FROM prompts WHERE slug = 'cv')
    );
