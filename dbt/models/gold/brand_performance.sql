{{ config(
    materialized='incremental',
    unique_key=['brand_id', 'city', 'state_name', 'country'],
    incremental_strategy='delete+insert'
) }}

-- One row per subject brand × city × state × country, covering every city
-- where the subject OR one of its competitors has an operational store.
-- A city with no subject presence still gets a row (our_store_count = 0), so
-- absence is visible instead of silently dropped.
--
-- Rebuild scope: a subject row changes when its own places change, when its
-- own competitor links change, or when one of its competitors changes —
-- because a competitor's stores are aggregated into the subject's row.

with

{% if is_incremental() %}
last_build as (
    select max(updated_at) as last_updated_at from {{ this }}
),

place_changed_brands as (
    select distinct brand_id
    from {{ ref('places_with_locations') }}
    where updated_at > (select last_updated_at from last_build)
),

link_changed_brands as (
    select distinct brand_id
    from {{ ref('competitors') }}
    where created_at > (select last_updated_at from last_build)
),

affected_brands as (
    select brand_id from place_changed_brands
    union
    select brand_id from link_changed_brands
    union
    select c.brand_id
    from {{ ref('competitors') }} c
    where c.competitor_id in (select brand_id from place_changed_brands)
),
{% else %}
affected_brands as (
    select id as brand_id from {{ ref('brands') }}
),
{% endif %}

subject_places as (

    select
        p.brand_id,
        p.city,
        p.state_name,
        p.country,
        p.rating,
        p.user_rating_count,
        p.distance_from_city_center,
        case p.price_level
            when 'PRICE_LEVEL_FREE' then 0
            when 'PRICE_LEVEL_INEXPENSIVE' then 1
            when 'PRICE_LEVEL_MODERATE' then 2
            when 'PRICE_LEVEL_EXPENSIVE' then 3
            when 'PRICE_LEVEL_VERY_EXPENSIVE' then 4
        end as price_rank,
        p.price_level
    from {{ ref('places_with_locations') }} p
    join affected_brands a on a.brand_id = p.brand_id
    where p.city is not null

),

competitor_places as (

    select
        c.brand_id,
        p.city,
        p.state_name,
        p.country,
        p.rating,
        p.user_rating_count,
        p.distance_from_city_center,
        case p.price_level
            when 'PRICE_LEVEL_FREE' then 0
            when 'PRICE_LEVEL_INEXPENSIVE' then 1
            when 'PRICE_LEVEL_MODERATE' then 2
            when 'PRICE_LEVEL_EXPENSIVE' then 3
            when 'PRICE_LEVEL_VERY_EXPENSIVE' then 4
        end as price_rank,
        p.price_level
    from {{ ref('competitors') }} c
    join affected_brands a on a.brand_id = c.brand_id
    join {{ ref('places_with_locations') }} p on p.brand_id = c.competitor_id
    where p.city is not null

),

-- city attributes, independent of which brand is present (so absence rows
-- still carry the size of the opportunity). population is the worldcities
-- city figure, which is already city level (repeated across its ZIPs, hence
-- max). density is intensive and must not be averaged — a sparse ZIP would
-- count as much as a dense one — so it is rebuilt from the extensive
-- quantities: total ZIP population over total ZIP area, where each ZIP's
-- area is recovered as population / density.
city_profile as (

    select
        city,
        state_name,
        country,
        max(lat) as lat,
        max(lng) as lng,
        max(population) as population,
        round(
            sum(zip_population)
            / nullif(sum(zip_population / density), 0), 1
        ) as density
    from {{ ref('locations') }}
    where zip is not null
      and zip_population is not null
      and density > 0
    group by 1, 2, 3

),

-- the grain: every city either side is present in
city_keys as (

    select distinct brand_id, city, state_name, country from subject_places
    union
    select distinct brand_id, city, state_name, country from competitor_places

),

subject_agg as (

    select
        brand_id,
        city,
        state_name,
        country,
        count(*) as our_store_count,
        sum(user_rating_count) as our_total_ratings,
        max(rating) as our_max_rating,
        avg(rating) as our_avg_rating_raw,
        avg(user_rating_count) as our_avg_rating_count_raw,
        arg_max(price_level, price_rank) as our_max_price_level,
        arg_min(price_level, price_rank) as our_min_price_level,
        avg(distance_from_city_center) as our_avg_distance_raw
    from subject_places
    group by 1, 2, 3, 4

),

competitor_agg as (

    select
        brand_id,
        city,
        state_name,
        country,
        count(*) as competitor_store_count,
        sum(user_rating_count) as competitor_total_ratings,
        max(rating) as competitor_max_rating,
        avg(rating) as competitor_avg_rating_raw,
        avg(user_rating_count) as competitor_avg_rating_count_raw,
        arg_max(price_level, price_rank) as competitor_max_price_level,
        arg_min(price_level, price_rank) as competitor_min_price_level,
        avg(distance_from_city_center) as competitor_avg_distance_raw
    from competitor_places
    group by 1, 2, 3, 4

)

select
    k.brand_id,
    b.brand_name,
    k.city,
    k.state_name,
    k.country,
    cp.lat,
    cp.lng,
    cp.population,
    cp.density,

    coalesce(s.our_store_count, 0) as our_store_count,
    coalesce(c.competitor_store_count, 0) as competitor_store_count,
    coalesce(s.our_store_count, 0) - coalesce(c.competitor_store_count, 0)
        as our_store_gap,
    round(
        coalesce(s.our_store_count, 0)
        / nullif(
            coalesce(s.our_store_count, 0)
            + coalesce(c.competitor_store_count, 0), 0
        ), 3
    ) as our_store_share,

    s.our_max_rating,
    round(s.our_avg_rating_raw, 2) as our_avg_rating,
    c.competitor_max_rating,
    round(c.competitor_avg_rating_raw, 2) as competitor_avg_rating,
    round(s.our_avg_rating_raw - c.competitor_avg_rating_raw, 2) as rating_gap,

    coalesce(s.our_total_ratings, 0) as our_total_ratings,
    coalesce(c.competitor_total_ratings, 0) as competitor_total_ratings,
    round(
        coalesce(s.our_total_ratings, 0)
        / nullif(
            coalesce(s.our_total_ratings, 0)
            + coalesce(c.competitor_total_ratings, 0), 0
        ), 3
    ) as review_share,
    round(s.our_avg_rating_count_raw, 1) as our_avg_rating_count,
    round(c.competitor_avg_rating_count_raw, 1) as competitor_avg_rating_count,

    s.our_max_price_level,
    s.our_min_price_level,
    c.competitor_max_price_level,
    c.competitor_min_price_level,

    round(s.our_avg_distance_raw) as our_avg_distance_from_city_center,
    round(c.competitor_avg_distance_raw)
        as competitor_avg_distance_from_city_center,

    current_date as updated_at
from city_keys k
join {{ ref('brands') }} b on b.id = k.brand_id
left join city_profile cp
    on cp.city is not distinct from k.city
   and cp.state_name is not distinct from k.state_name
   and cp.country is not distinct from k.country
left join subject_agg s
    on s.brand_id = k.brand_id
   and s.city is not distinct from k.city
   and s.state_name is not distinct from k.state_name
   and s.country is not distinct from k.country
left join competitor_agg c
    on c.brand_id = k.brand_id
   and c.city is not distinct from k.city
   and c.state_name is not distinct from k.state_name
   and c.country is not distinct from k.country