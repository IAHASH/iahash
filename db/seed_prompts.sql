-- Seed data for IA-HASH v1.2
INSERT INTO prompts (slug, owner_id, title, description, full_prompt, category, is_master, visibility, h_public)
VALUES
('cv-honest-v1', 'iahash', 'CV Honesto Cognitivo', 'Retrato profesional sincero con foco en logros reales.', 'Eres un asesor profesional. Genera un CV honesto y conciso usando los datos proporcionados.', 'career', 1, 'public', '2832173c8ccc372a75bc697bd8689524c3f82cc7958f6c652ba80ce8252e91bd'),
('habit-builder-v1', 'iahash', 'Constructor de Hábitos', 'Plan corto en 3 pasos para construir un hábito.', 'Actúa como coach de hábitos. Devuelve un plan de 3 pasos personalizado a partir del objetivo indicado.', 'wellbeing', 1, 'public', 'f8e8f22ae29611469bba50ea2072a66b3887ed679c955b10c4448e8cabd7e56c');

INSERT INTO sequences (slug, title, description, category, visibility)
VALUES
('onboarding-7d', 'Onboarding en 7 días', 'Secuencia de prompts para acompañar una semana de trabajo.', 'coaching', 'public'),
('consistency-check', 'Chequeo de Consistencia', 'Comparar respuestas de un mismo prompt en diferentes modelos.', 'qa', 'public');

INSERT INTO sequence_steps (sequence_id, position, title, description, prompt_id)
VALUES
((SELECT id FROM sequences WHERE slug='onboarding-7d'), 1, 'Día 1 - CV Honesto', 'Construye tu CV base.', (SELECT id FROM prompts WHERE slug='cv-honest-v1')),
((SELECT id FROM sequences WHERE slug='onboarding-7d'), 2, 'Día 3 - Refinar hábitos', 'Primer bloque de hábitos.', (SELECT id FROM prompts WHERE slug='habit-builder-v1')),
((SELECT id FROM sequences WHERE slug='consistency-check'), 1, 'Run CV prompt en modelo A', 'Primera ejecución.', (SELECT id FROM prompts WHERE slug='cv-honest-v1')),
((SELECT id FROM sequences WHERE slug='consistency-check'), 2, 'Run CV prompt en modelo B', 'Segunda ejecución.', (SELECT id FROM prompts WHERE slug='cv-honest-v1'));
