-- Cada paper aparece una sola vez
SELECT paper_id FROM stg_papers GROUP BY paper_id HAVING count(*) > 1
