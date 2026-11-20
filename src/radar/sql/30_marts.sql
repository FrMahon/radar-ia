-- Marts: lo que consume el tablero.

DROP TABLE IF EXISTS mart_coverage;
CREATE TABLE mart_coverage AS
SELECT min(day) AS first_day, max(day) AS last_day, count(DISTINCT day) AS days FROM raw_arxiv;


-- Proporción semanal de papers por tema. Solo semanas completas dentro de lo extraído,
-- para que la primera y la última semana no parezcan caídas.
DROP TABLE IF EXISTS mart_weekly_topics;
CREATE TABLE mart_weekly_topics AS
WITH weeks AS (
    SELECT p.week, count(*) AS total_papers
    FROM stg_papers AS p, mart_coverage AS c
    WHERE p.week >= c.first_day AND date(p.week, '+6 days') <= c.last_day
    GROUP BY p.week
),
counts AS (
    SELECT p.week, pt.topic_id, count(*) AS papers
    FROM fct_paper_topics AS pt
    JOIN stg_papers AS p USING (paper_id)
    GROUP BY p.week, pt.topic_id
)
SELECT
    w.week,
    t.topic_id,
    w.total_papers,
    coalesce(c.papers, 0) AS papers,
    round(1.0 * coalesce(c.papers, 0) / w.total_papers, 4) AS share
FROM weeks AS w
CROSS JOIN dim_topics AS t
LEFT JOIN counts AS c ON c.week = w.week AND c.topic_id = t.topic_id;


-- Cuánto cambió cada tema: primeras 4 semanas contra las últimas 4.
DROP TABLE IF EXISTS mart_topic_growth;
CREATE TABLE mart_topic_growth AS
WITH numbered AS (
    SELECT *,
        dense_rank() OVER (ORDER BY week)      AS from_start,
        dense_rank() OVER (ORDER BY week DESC) AS from_end
    FROM mart_weekly_topics
),
shares AS (
    SELECT
        topic_id,
        1.0 * sum(CASE WHEN from_start <= 4 THEN papers END) / sum(CASE WHEN from_start <= 4 THEN total_papers END) AS share_start,
        1.0 * sum(CASE WHEN from_end   <= 4 THEN papers END) / sum(CASE WHEN from_end   <= 4 THEN total_papers END) AS share_end
    FROM numbered
    GROUP BY topic_id
)
SELECT topic_id, round(share_start, 4) AS share_start, round(share_end, 4) AS share_end,
       round(share_end - share_start, 4) AS change
FROM shares;


-- Modelos en tendencia hoy, comparados con la foto anterior.
DROP TABLE IF EXISTS mart_hf_today;
CREATE TABLE mart_hf_today AS
WITH latest AS (SELECT max(snapshot_date) AS d FROM stg_hf_trending),
previous AS (SELECT max(snapshot_date) AS d FROM stg_hf_trending WHERE snapshot_date < (SELECT d FROM latest)),
streak AS (SELECT model_id, count(*) AS days_trending FROM stg_hf_trending GROUP BY model_id)
SELECT
    t.snapshot_date,
    t.rank,
    t.model_id,
    t.task,
    t.likes,
    t.downloads,
    t.created_date,
    p.rank AS previous_rank,
    (SELECT d FROM previous) AS previous_date,
    s.days_trending
FROM stg_hf_trending AS t
JOIN streak AS s USING (model_id)
LEFT JOIN stg_hf_trending AS p ON p.model_id = t.model_id AND p.snapshot_date = (SELECT d FROM previous)
WHERE t.snapshot_date = (SELECT d FROM latest);
