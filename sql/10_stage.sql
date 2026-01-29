CREATE OR REPLACE VIEW stg_flights AS
SELECT
    icao_empresa_aerea,
    numero_voo,
    codigo_autorizacao_di,
    codigo_tipo_linha,
    icao_aerodromo_origem,
    icao_aerodromo_destino,

    ---- #Clean data
    try_cast(NULLIF(NULLIF(NULLIF(partida_prevista, 'null'), 'N/A'), '') AS TIMESTAMP) AS sched_dep_ts,
    try_cast(NULLIF(NULLIF(NULLIF(partida_real,     'null'), 'N/A'), '') AS TIMESTAMP) AS actual_dep_ts,
    try_cast(NULLIF(NULLIF(NULLIF(chegada_prevista, 'null'), 'N/A'), '') AS TIMESTAMP) AS sched_arr_ts,
    try_cast(NULLIF(NULLIF(NULLIF(chegada_real,     'null'), 'N/A'), '') AS TIMESTAMP) AS actual_arr_ts,

    situacao_voo, 
    codigo_justificativa,

    (upper(situacao_voo) = 'CANCELADO') AS is_cancelled
FROM raw_vra;

CREATE OR REPLACE VIEW fact_flights AS
SELECT
    *,
    date_diff('minute', sched_dep_ts, actual_dep_ts) AS delay_dep_minutes,
    (date_diff('minute', sched_dep_ts, actual_dep_ts) >= 15) AS is_delayed_15
FROM stg_flights
WHERE sched_dep_ts IS NOT NULL;