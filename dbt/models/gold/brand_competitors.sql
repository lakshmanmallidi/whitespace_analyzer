{{ config(materialized='table') }}

-- The directed competitor graph with names attached, so the app can resolve
-- "which stores are competitors of the brand I am looking at" without
-- reaching into bronze. One row per (brand, competitor) edge.

select
    c.brand_id,
    sb.brand_name,
    c.competitor_id,
    cb.brand_name as competitor_name,
    c.created_at
from {{ ref('competitors') }} c
join {{ ref('brands') }} sb
    on sb.id = c.brand_id
join {{ ref('brands') }} cb
    on cb.id = c.competitor_id
