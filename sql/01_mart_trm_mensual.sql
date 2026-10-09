-- Resumen mensual: promedio, mínimo, máximo, apertura, cierre y variación contra el mes anterior.
CREATE OR REPLACE TABLE marts.trm_mensual AS
WITH mensual AS (
    SELECT
        date_trunc('month', fecha)::DATE  AS mes,
        round(avg(trm), 2)                AS trm_promedio,
        min(trm)                          AS trm_minima,
        max(trm)                          AS trm_maxima,
        arg_min(trm, fecha)               AS trm_apertura,
        arg_max(trm, fecha)               AS trm_cierre,
        count(*)                          AS dias
    FROM core.trm_diaria
    GROUP BY 1
)
SELECT
    *,
    round(100 * (trm_cierre / lag(trm_cierre) OVER (ORDER BY mes) - 1), 2) AS variacion_pct
FROM mensual
ORDER BY mes;
