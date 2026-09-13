with customers as (

    select * from {{ ref('stg_olist__customers') }}

),

orders as (

    select * from {{ ref('stg_olist__orders') }}

),

customer_orders as (

    select
        c.customer_unique_id,
        c.customer_id,
        c.customer_city,
        c.customer_state,
        o.order_id,
        o.order_purchased_at

    from customers c
    inner join orders o
        on c.customer_id = o.customer_id

),

aggregated as (

    select
        customer_unique_id,

        count(distinct order_id)          as nb_orders,
        min(order_purchased_at)           as first_order_at,
        max(order_purchased_at)           as last_order_at,

        -- On garde la ville/état associés à la commande la plus récente
        -- (un client peut théoriquement déménager entre deux commandes)
        arg_max(customer_city, order_purchased_at)  as customer_city,
        arg_max(customer_state, order_purchased_at) as customer_state

    from customer_orders
    group by customer_unique_id

)

select
    customer_unique_id,
    nb_orders,
    first_order_at,
    last_order_at,
    customer_city,
    customer_state,

    -- Flag simple de segmentation, réutilisable dans les analyses futures
    case
        when nb_orders = 1 then 'one_time'
        else 'returning'
    end as customer_type

from aggregated