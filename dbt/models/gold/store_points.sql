{{ config(
    materialized='incremental',
    unique_key='place_id',
    incremental_strategy='delete+insert'
) }}

-- One row per operational store that resolved to a city, with its coordinates.
-- This is the store-grain companion to `brand_performance` (which is city
-- grain): the map needs individual pins, and bronze `places` is where the
-- store name and address live.
--
-- Coordinates come from the silver point geometry rather than the raw
-- latitude/longitude columns, so the map and the distance calculations in
-- `places_with_locations` always agree on the same geometry.
--
-- Incremental on place_id: a re-fetched store carries a higher `updated_at`,
-- so it replaces its own row instead of appending a second pin. The watermark
-- is the same column the bronze store name and address are refreshed from, so
-- renamed or re-addressed stores come through on the same pass.

select
    p.place_id,
    p.brand_id,
    b.brand_name,
    pl.name as store_name,
    pl.formatted_address,
    p.city,
    p.state_name,
    p.country,
    st_x(p.place_location) as longitude,
    st_y(p.place_location) as latitude,
    p.rating,
    p.user_rating_count,
    p.price_level,
    p.updated_at
from {{ ref('places_with_locations') }} p
join {{ ref('brands') }} b
    on b.id = p.brand_id
left join {{ ref('places') }} pl
    on pl.place_id = p.place_id
{% if is_incremental() %}
where p.updated_at > (select max(updated_at) from {{ this }})
{% endif %}
