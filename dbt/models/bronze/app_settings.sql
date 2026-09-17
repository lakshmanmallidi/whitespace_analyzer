{{ config(materialized='view', contract={'enforced': true}) }}

select
    cast("key" as varchar) as "key",
    cast(value as varchar) as value,
    cast(updated_at as timestamp) as updated_at
from {{ source('ods', 'app_settings') }}
