-- En cada foto de Hugging Face, un puesto por modelo y un modelo por puesto
SELECT snapshot_date FROM stg_hf_trending GROUP BY snapshot_date, rank HAVING count(*) > 1
UNION ALL
SELECT snapshot_date FROM stg_hf_trending GROUP BY snapshot_date, model_id HAVING count(*) > 1
