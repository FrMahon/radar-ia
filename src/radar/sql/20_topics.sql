-- Taxonomía de temas y etiquetado de papers por expresiones regulares sobre el título.
-- Solo el título: en los resúmenes casi todos dicen "benchmark" o "agent" de pasada, y eso infla los temas.
-- shortcut: reglas por palabras clave (sin modelo de lenguaje) para que corra en segundos y con poca RAM;
-- si hiciera falta más precisión, reemplazar fct_paper_topics por un clasificador con embeddings.

DROP TABLE IF EXISTS dim_topics;
CREATE TABLE dim_topics (topic_id TEXT PRIMARY KEY, name TEXT NOT NULL, pattern TEXT NOT NULL, description TEXT NOT NULL);
INSERT INTO dim_topics VALUES
    ('agentes',     'Agentes',                '\bagent(s|ic)?\b|multi-agent|tool[- ]use|tool[- ]calling',
                    'Sistemas que planifican y usan herramientas por su cuenta.'),
    ('razonamiento','Razonamiento',           '\breasoning\b|chain[- ]of[- ]thought|test[- ]time (compute|scaling)',
                    'Modelos que resuelven problemas paso a paso.'),
    ('rag',         'Búsqueda y RAG',         'retrieval[- ]augmented|\bRAG\b|\bretriever',
                    'Respuestas apoyadas en documentos buscados al momento.'),
    ('seguridad',   'Seguridad y alineación', '\balignment\b|jailbreak|red[- ]teaming|\bRLHF\b|harmful|\bAI safety\b',
                    'Que los modelos hagan lo que se espera y no causen daño.'),
    ('multimodal',  'Multimodal',             'multi-?modal|vision[- ]language|\bVLMs?\b',
                    'Modelos que combinan texto con imágenes, video o audio.'),
    ('eficiencia',  'Eficiencia',             'quantiz|pruning|distillation|\bLoRA\b|speculative decoding|\bKV[- ]cache',
                    'Modelos más chicos, rápidos o baratos de correr.'),
    ('difusion',    'Difusión',               '\bdiffusion\b',
                    'Generación de imágenes, video y más con modelos de difusión.'),
    ('robotica',    'Robótica',               '\brobot|embodied',
                    'IA que actúa en el mundo físico.'),
    ('evaluacion',  'Evaluación',             '\bbenchmark|\bevaluat|leaderboard',
                    'Cómo se mide lo que un modelo sabe hacer.'),
    ('audio',       'Voz y audio',            '\bspeech\b|\baudio\b|\bASR\b|text-to-speech',
                    'Reconocimiento y síntesis de voz y sonido.');

DROP TABLE IF EXISTS fct_paper_topics;
CREATE TABLE fct_paper_topics AS
SELECT p.paper_id, t.topic_id
FROM stg_papers AS p
JOIN dim_topics AS t ON p.title REGEXP t.pattern;

CREATE INDEX ix_fct_paper_topics ON fct_paper_topics (paper_id);
