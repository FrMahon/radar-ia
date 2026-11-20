-- Ninguna semana tiene menos del 40 % del volumen promedio (sería un hueco en la extracción)
WITH weeks AS (SELECT DISTINCT week, total_papers FROM mart_weekly_topics)
SELECT week FROM weeks WHERE total_papers < 0.4 * (SELECT avg(total_papers) FROM weeks)
