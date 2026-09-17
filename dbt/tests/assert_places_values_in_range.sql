-- Fails if any place has coordinates/rating/counts outside valid ranges.
select
    id,
    latitude,
    longitude,
    rating,
    user_rating_count
from {{ ref('places') }}
where latitude not between -90 and 90
   or longitude not between -180 and 180
   or rating not between 0 and 5
   or user_rating_count < 0
