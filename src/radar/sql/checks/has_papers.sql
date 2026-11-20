-- Hay papers de arXiv para mostrar (sin datos, no se publica una página vacía)
SELECT 1 WHERE (SELECT count(*) FROM stg_papers) = 0
