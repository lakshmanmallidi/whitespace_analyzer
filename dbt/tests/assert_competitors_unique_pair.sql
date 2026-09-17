-- Fails if a brand→competitor link appears more than once.
select brand_id, competitor_id, count(*) as n
from {{ ref('competitors') }}
group by brand_id, competitor_id
having count(*) > 1
