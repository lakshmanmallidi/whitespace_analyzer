-- Fails if a brand × city × state × country row appears more than once.
select brand_id, city, state_name, country, count(*) as n
from {{ ref('brand_performance') }}
group by 1, 2, 3, 4
having count(*) > 1