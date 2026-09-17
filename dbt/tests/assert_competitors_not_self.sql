-- Fails if a brand is linked as its own competitor.
select brand_id, competitor_id
from {{ ref('competitors') }}
where brand_id = competitor_id
