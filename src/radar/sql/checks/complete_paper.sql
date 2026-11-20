-- Todo paper tiene título, resumen y fecha
SELECT paper_id FROM stg_papers
WHERE coalesce(title, '') = '' OR coalesce(abstract, '') = '' OR published_date IS NULL
