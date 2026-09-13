with products as (

    select * from {{ ref('olist_products_dataset') }}

),

translation as (

    select * from {{ ref('product_category_name_translation') }}

),

renamed as (

    select
        p.product_id,

        -- Fallback sur le nom brut si pas de traduction dispo (2 catégories concernées, vu en EDA)
        coalesce(t.product_category_name_english, p.product_category_name) as product_category_name,

        p.product_name_lenght       as product_name_length,
        p.product_description_lenght as product_description_length,
        p.product_photos_qty,
        p.product_weight_g,
        p.product_length_cm,
        p.product_height_cm,
        p.product_width_cm

    from products p
    left join translation t
        on p.product_category_name = t.product_category_name

)

select * from renamed