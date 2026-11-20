-- Cada etiqueta apunta a un tema de la taxonomía y a un paper existente
SELECT pt.paper_id FROM fct_paper_topics AS pt
LEFT JOIN dim_topics AS t USING (topic_id)
LEFT JOIN stg_papers AS p USING (paper_id)
WHERE t.topic_id IS NULL OR p.paper_id IS NULL
