-- sql/20_features.sql
-- Feature layer for Plan B (prediction before departure)

--- Airport-level historical delay
CREATE OR REPLACE VIEW airport_delay_stats AS 
SELECT
    icao_aerodromo_origem,
    AVG(is_delayed_15::INT) AS delay_rate_airport,
    COUNT(*) AS n_airport
FROM fact_flights
WHERE is_cancelled =  FALSE
    AND actual_dep_ts IS NOT NULL
GROUP BY 1;

--- Route-Level historical delay
CREATE OR REPLACE VIEW route_delay_stats AS 
SELECT
    icao_aerodromo_origem,
    icao_aerodromo_destino,
    AVG(is_delayed_15::INT) AS delay_rate_route,
    COUNT(*) AS n_route
FROM fact_flights
WHERE is_cancelled = FALSE
    AND actual_dep_ts IS NOT NULL
GROUP BY 1,2;

-- Airline-level historical delay
CREATE OR REPLACE VIEW airline_delay_stats AS 
SELECT
    icao_empresa_aerea,
    AVG(is_delayed_15::INT) AS delay_rate_airline,
    COUNT(*) AS n_airline
FROM fact_flights
WHERE is_cancelled = FALSE
    AND actual_dep_ts IS NOT NULL
GROUP BY 1;

--Airport hour historical delay
CREATE OR REPLACE VIEW airport_hour_delay_stats AS 
SELECT
    icao_empresa_aerea,
    EXTRACT('hour' FROM sched_dep_ts) AS dep_hour,
    AVG(is_delayed_15::INT) AS delay_rate_airport_hour,
    COUNT(*) AS n_airport_hour
FROM fact_flights
WHERE is_cancelled = FALSE
    AND actual_dep_ts IS NOT NULL
    AND sched_dep_ts IS NOT NULL
GROUP BY 1,2;

-- Final Model View
CREATE OR REPLACE VIEW v_feature_model AS
SELECT

    f.sched_dep_ts,
    f.is_delayed_15::INT AS y_delayed_15,

    f.icao_empresa_aerea,
    f.icao_aerodromo_origem,
    f.icao_aerodromo_destino,

    EXTRACT('hour'  FROM f.sched_dep_ts) AS dep_hour,
    EXTRACT('dow'   FROM f.sched_dep_ts) AS dep_dow,
    EXTRACT('month' FROM f.sched_dep_ts) AS dep_month,

    a.delay_rate_airport,
    a.n_airport,
    r.n_route,
    r.delay_rate_route,
    ah.delay_rate_airport_hour,
    ah.n_airport_hour,
    al.delay_rate_airline
FROM fact_flights f
LEFT JOIN airport_delay_stats a
    ON f.icao_aerodromo_origem = a.icao_aerodromo_origem
LEFT JOIN route_delay_stats r
    ON f.icao_aerodromo_origem = r.icao_aerodromo_origem
    AND f.icao_aerodromo_destino = r.icao_aerodromo_destino
LEFT JOIN airline_delay_stats al
    ON f.icao_empresa_aerea = al.icao_empresa_aerea
LEFT JOIN airport_hour_delay_stats ah
  ON f.icao_aerodromo_origem = ah.icao_aerodromo_origem
  AND EXTRACT('hour' FROM f.sched_dep_ts) = ah.dep_hour
WHERE f.is_cancelled = FALSE
    AND f.actual_dep_ts IS NOT NULL
    AND f.sched_dep_ts IS NOT NULL;


