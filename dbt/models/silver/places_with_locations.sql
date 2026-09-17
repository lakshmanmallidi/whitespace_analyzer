{{ config(
    materialized='incremental',
    unique_key='place_id',
    incremental_strategy='delete+insert'
) }}

with places as (

    select
        brand_id,
        place_id,
        postal_code,
        rating,
        user_rating_count,
        price_level,
        updated_at,
        ST_Point(longitude, latitude) as place_location
    from {{ ref('places_history') }}
    where business_status = 'OPERATIONAL'
      and dbt_valid_to is null
    {% if is_incremental() %}
      and updated_at > (select max(updated_at) from {{ this }})
    {% endif %}

),

locations as (

    select
        zip,
        city,
        state_name,
        country,
        population,
        density,
        ST_Point(lng, lat) as city_location
    from {{ ref('locations') }}
    where zip is not null

)

select
    p.brand_id,
    p.place_id,
    p.postal_code,
    p.rating,
    p.user_rating_count,
    p.price_level,
    p.place_location,
    g.city,
    g.state_name,
    g.country,
    g.population,
    g.density,
    g.city_location,
    p.updated_at
from places p
left join locations g
    on g.zip = p.postal_code
