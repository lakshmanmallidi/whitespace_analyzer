{{ config(materialized='view', contract={'enforced': true}) }}

select
    cast(id as bigint) as id,
    cast(brand_id as bigint) as brand_id,
    cast(place_id as varchar) as place_id,
    cast(name as varchar) as name,
    cast(formatted_address as varchar) as formatted_address,
    cast(postal_code as varchar) as postal_code,
    cast(latitude as double) as latitude,
    cast(longitude as double) as longitude,
    cast(national_phone as varchar) as national_phone,
    cast(international_phone as varchar) as international_phone,
    cast(website_uri as varchar) as website_uri,
    cast(rating as double) as rating,
    cast(user_rating_count as bigint) as user_rating_count,
    cast(price_level as varchar) as price_level,
    cast(business_status as varchar) as business_status,
    cast(primary_type as varchar) as primary_type,
    cast(types as json) as types,
    cast(utc_offset_minutes as bigint) as utc_offset_minutes,
    cast(open_now as boolean) as open_now,
    cast(weekday_hours as json) as weekday_hours,
    cast(google_maps_uri as varchar) as google_maps_uri,
    cast(raw_json as json) as raw_json,
    cast(created_at as timestamp) as created_at,
    cast(updated_at as timestamp) as updated_at
from {{ source('ods', 'places') }}
