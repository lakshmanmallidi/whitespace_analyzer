{{ config(materialized='view', contract={'enforced': true}) }}

select
    cast(id as bigint) as id,
    cast(brand_name as varchar) as brand_name,
    cast(industry_domain as varchar) as industry_domain,
    cast(website_url as varchar) as website_url,
    cast(created_at as timestamp) as created_at
from {{ source('ods', 'brands') }}
