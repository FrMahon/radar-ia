-- Los datos tienen menos de 5 días
SELECT 'arxiv' FROM mart_coverage WHERE last_day IS NULL OR last_day < date('now', '-5 days')
UNION ALL
SELECT 'hf' FROM (SELECT max(snapshot_date) AS d FROM stg_hf_trending) WHERE d IS NULL OR d < date('now', '-5 days')
