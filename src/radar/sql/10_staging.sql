-- Staging: tipa y limpia lo crudo. Una fila por paper (su última versión) y una por modelo en cada foto.

DROP TABLE IF EXISTS stg_papers;
CREATE TABLE stg_papers AS
WITH parsed AS (
    SELECT
        json_extract(payload, '$.id')               AS paper_id,
        json_extract(payload, '$.version')          AS version,
        json_extract(payload, '$.title')            AS title,
        json_extract(payload, '$.abstract')         AS abstract,
        json_extract(payload, '$.published')        AS published_at,
        json_extract(payload, '$.primary_category') AS primary_category,
        json_extract(payload, '$.n_authors')        AS n_authors,
        day                                         AS extracted_day
    FROM raw_arxiv
),
latest AS (
    SELECT *, row_number() OVER (PARTITION BY paper_id ORDER BY version DESC, extracted_day DESC) AS rn
    FROM parsed
)
SELECT
    paper_id,
    version,
    title,
    abstract,
    published_at,
    date(published_at)                     AS published_date,
    date(published_at, '-6 days', 'weekday 1') AS week,  -- lunes de la semana
    primary_category,
    n_authors
FROM latest
WHERE rn = 1;

CREATE UNIQUE INDEX ix_stg_papers ON stg_papers (paper_id);
CREATE INDEX ix_stg_papers_week ON stg_papers (week);


DROP TABLE IF EXISTS stg_hf_trending;
CREATE TABLE stg_hf_trending AS
SELECT
    snapshot_date,
    json_extract(payload, '$.rank')                 AS rank,
    json_extract(payload, '$.id')                   AS model_id,
    coalesce(json_extract(payload, '$.pipeline_tag'), 'sin tarea') AS task,
    json_extract(payload, '$.likes')                AS likes,
    json_extract(payload, '$.downloads')            AS downloads,
    json_extract(payload, '$.trendingScore')        AS trending_score,
    date(json_extract(payload, '$.createdAt'))      AS created_date
FROM raw_hf;
