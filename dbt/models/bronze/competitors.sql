{{ config(materialized='view', contract={'enforced': true}) }}

select
    cast(brand_id as bigint) as brand_id,
    cast(competitor_id as bigint) as competitor_id,
    cast(created_at as timestamp) as created_at
from {{ source('ods', 'competitors') }}
