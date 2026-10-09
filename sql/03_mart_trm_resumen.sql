-- Una fila con los indicadores del corte: valor actual, rango de 52 semanas y variación del año.
CREATE OR REPLACE TABLE marts.trm_resumen AS
WITH corte AS (
    SELECT max(fecha) AS fecha FROM core.trm_diaria
)
SELECT
    c.fecha                                                      AS fecha_corte,
    arg_max(d.trm, d.fecha)                                      AS trm_actual,
    min(d.trm) FILTER (WHERE d.fecha > c.fecha - 365)            AS minimo_52_semanas,
    max(d.trm) FILTER (WHERE d.fecha > c.fecha - 365)            AS maximo_52_semanas,
    round(100 * (arg_max(d.trm, d.fecha)
        / arg_min(d.trm, d.fecha) FILTER (WHERE d.fecha >= date_trunc('year', c.fecha)) - 1), 2)
                                                                 AS variacion_anio_pct,
    count(*)                                                     AS dias_en_bodega
FROM core.trm_diaria AS d
CROSS JOIN corte AS c
GROUP BY c.fecha;
