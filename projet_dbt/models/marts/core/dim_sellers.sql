with sellers as (

    select * from {{ ref('stg_olist__sellers') }}

),

order_items as (

    select * from {{ ref('stg_olist__order_items') }}

),

sales_agg as (

    select
        seller_id,
        count(*)                       as nb_items_sold,
        count(distinct order_id)       as nb_orders,
        sum(price)                     as total_revenue,
        sum(freight_value)             as total_freight_collected

    from order_items
    group by seller_id

),

final as (

    select
        s.seller_id,
        s.seller_city,
        s.seller_state,

        coalesce(sa.nb_items_sold, 0)            as nb_items_sold,
        coalesce(sa.nb_orders, 0)                as nb_orders,
        coalesce(sa.total_revenue, 0)            as total_revenue,
        coalesce(sa.total_freight_collected, 0)  as total_freight_collected

    from sellers s
    left join sales_agg sa
        on s.seller_id = sa.seller_id

)

select * from final