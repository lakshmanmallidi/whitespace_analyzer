-- Fails if a place appears more than once in the store map mart.
select place_id, count(*) as n
from {{ ref('store_points') }}
group by 1
having count(*) > 1
