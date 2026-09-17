-- Fails if the JSON columns do not have the expected shape.
-- types / weekday_hours must be arrays; raw_json must be the place object.
select
    id,
    json_type(types) as types_type,
    json_type(weekday_hours) as weekday_hours_type,
    json_type(raw_json) as raw_json_type
from {{ ref('places') }}
where json_type(types) <> 'ARRAY'
   or json_type(weekday_hours) <> 'ARRAY'
   or json_type(raw_json) <> 'OBJECT'
