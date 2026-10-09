-- Volatilidad: desviación estándar móvil (20 días hábiles) del cambio diario en %.
-- Solo se usan los días en que empieza a regir cada TRM, así los fines de semana
-- (que repiten el valor del viernes) no aplanan la medida.
CREATE OR REPLACE TABLE marts.trm_volatilidad AS
WITH habiles AS (
    SELECT fecha, trm
    FROM core.trm_diaria
    WHERE fecha = vigencia_desde
),
cambios AS (
    SELECT
        fecha,
        trm,
        100 * (trm / lag(trm) OVER (ORDER BY fecha) - 1) AS cambio_pct
    FROM habiles
)
SELECT
    fecha,
    trm,
    round(cambio_pct, 3) AS cambio_pct,
    round(stddev_samp(cambio_pct) OVER (ORDER BY fecha ROWS BETWEEN 19 PRECEDING AND CURRENT ROW), 3)
        AS volatilidad_20d
FROM cambios
ORDER BY fecha;
