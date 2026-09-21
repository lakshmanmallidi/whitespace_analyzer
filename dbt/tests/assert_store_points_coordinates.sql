-- Fails if a store cannot be plotted: missing coordinates or values outside
-- the valid longitude/latitude range.
select place_id, longitude, latitude
from {{ ref('store_points') }}
where longitude is null
   or latitude is null
   or longitude < -180
   or longitude > 180
   or latitude < -90
   or latitude > 90
