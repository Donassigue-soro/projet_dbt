with order_items as (

    select * from {{ ref('stg_olist__order_items') }}

),

orders as (

    select * from {{ ref('stg_olist__orders') }}

),

final as (

    select
        oi.order_id,
        oi.order_item_id,
        oi.product_id,
        oi.seller_id,
        oi.price,
        oi.freight_value,
        oi.shipping_limit_at,

        o.customer_id,
        o.order_status,
        o.order_purchased_at,
        o.has_date_anomaly,
        o.is_late_delivery

    from order_items oi
    inner join orders o
        on oi.order_id = o.order_id

)

select * from final