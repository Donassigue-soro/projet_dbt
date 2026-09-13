with source as (

    select * from {{ ref('olist_order_items_dataset') }}

),

renamed as (

    select
        order_id,
        order_item_id,              -- numéro de ligne dans la commande (1, 2, 3...)
        product_id,
        seller_id,
        shipping_limit_date::timestamp as shipping_limit_at,
        price,
        freight_value

    from source

)

select * from renamed