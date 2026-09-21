{{ config(materialized='table') }}

{% set match_threshold_m = 75000 %}

-- ZIPs are attributed to the nearest matching city: the same city name/state
-- can appear several times in worldcities, which used to fan a ZIP out to up
-- to 11 rows. Distance also guards against same-name towns in the same state
-- (e.g. Richland, PA sits 103 km from any worldcities "richland").
-- 75 km keeps genuine metro spread (outer ZIPs of LA/Denver reach ~60 km)
-- while rejecting those mismatches.

with worldcities as (

    select
        lower(trim(city)) as city,
        lat,
        lng,
        lower(trim(country)) as country,
        lower(trim(admin_name)) as state_name,
        population
    from {{ ref('worldcities') }}

),

uszips as (

    select
        zip,
        state_name,
        lower(trim(city)) as city,
        lower(trim(state_name)) as state_name_key,
        'united states' as country,
        density,
        population as zip_population,
        lat,
        lng
    from {{ ref('uszips') }}

),

candidates as (

    select
        w.city,
        w.lat,
        w.lng,
        w.country,
        w.population,
        z.zip,
        z.state_name,
        z.density,
        z.zip_population,
        ST_Distance_Sphere(
            ST_Point(w.lng, w.lat),
            ST_Point(z.lng, z.lat)
        ) as distance_m,
        row_number() over (
            partition by z.zip
            order by ST_Distance_Sphere(
                ST_Point(w.lng, w.lat),
                ST_Point(z.lng, z.lat)
            )
        ) as rn
    from worldcities w
    left join uszips z
        on z.city = w.city
        and z.country = w.country
        and z.state_name_key = w.state_name

)

-- keep every worldcities row (left-join semantics); only the nearest city
-- within the threshold keeps the ZIP, the rest fall back to unmatched
select
    city,
    lat,
    lng,
    country,
    population,
    case when rn = 1 and distance_m <= {{ match_threshold_m }} then zip end as zip,
    case when rn = 1 and distance_m <= {{ match_threshold_m }} then state_name end as state_name,
    case when rn = 1 and distance_m <= {{ match_threshold_m }} then density end as density,
    case when rn = 1 and distance_m <= {{ match_threshold_m }} then zip_population end as zip_population
from candidates
