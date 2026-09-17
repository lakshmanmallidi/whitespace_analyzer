{% snapshot places_history %}

{{
    config(
        unique_key='place_id',
        strategy='timestamp',
        updated_at='updated_at'
    )
}}

select * from {{ ref('places') }}

{% endsnapshot %}
