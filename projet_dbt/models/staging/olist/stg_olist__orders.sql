with source as (

    select * from {{ ref('olist_orders_dataset') }}

),

renamed as (

    select
        order_id,
        customer_id,
        order_status,
        order_purchase_timestamp::timestamp       as order_purchased_at,
        order_approved_at::timestamp              as order_approved_at,
        order_delivered_carrier_date::timestamp   as order_delivered_carrier_at,
        order_delivered_customer_date::timestamp  as order_delivered_customer_at,
        order_estimated_delivery_date::timestamp  as order_estimated_delivery_at,

        case
            when order_delivered_customer_date < order_purchase_timestamp then true
            when order_approved_at < order_purchase_timestamp then true
            when order_delivered_customer_date < order_approved_at then true
            else false
        end as has_date_anomaly,

        case
            when order_delivered_customer_date > order_estimated_delivery_date then true
            when order_delivered_customer_date is null then null
            else false
        end as is_late_delivery

    from source

)

select * from renamed