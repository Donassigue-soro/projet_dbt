with products as (

    select * from {{ ref('stg_olist__products') }}

),

order_items as (

    select * from {{ ref('stg_olist__order_items') }}

),

sales_agg as (

    select
        product_id,
        count(*)              as nb_times_sold,
        sum(price)             as total_revenue,
        avg(price)              as avg_selling_price

    from order_items
    group by product_id

),

final as (

    select
        p.product_id,
        p.product_category_name,
        p.product_weight_g,
        p.product_length_cm,
        p.product_height_cm,
        p.product_width_cm,
        p.product_photos_qty,

        coalesce(s.nb_times_sold, 0)     as nb_times_sold,
        coalesce(s.total_revenue, 0)     as total_revenue,
        s.avg_selling_price

    from products p
    left join sales_agg s
        on p.product_id = s.product_id

)

select * from final