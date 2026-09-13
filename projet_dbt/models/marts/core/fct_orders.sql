with orders as (

    select * from {{ ref('stg_olist__orders') }}

),

order_items as (

    select * from {{ ref('stg_olist__order_items') }}

),

payments as (

    select * from {{ ref('stg_olist__payments') }}

),

reviews as (

    select * from {{ ref('stg_olist__reviews') }}

),

-- Agrégation des articles : total produit, frais de port, nb d'articles
items_agg as (

    select
        order_id,
        count(*)              as nb_items,
        sum(price)             as total_items_price,
        sum(freight_value)     as total_freight_value

    from order_items
    group by order_id

),

-- Agrégation des paiements : montant total payé, nb de paiements
payments_agg as (

    select
        order_id,
        count(*)               as nb_payments,
        sum(payment_value)     as total_payment_value

    from payments
    group by order_id

),

-- Une commande peut avoir plusieurs reviews (many-to-many vu en EDA) :
-- on prend la note moyenne pour rester au grain "une commande"
reviews_agg as (

    select
        order_id,
        avg(review_score)      as avg_review_score,
        count(*)                as nb_reviews

    from reviews
    group by order_id

),

final as (

    select
        o.order_id,
        o.customer_id,
        o.order_status,
        o.order_purchased_at,
        o.order_approved_at,
        o.order_delivered_carrier_at,
        o.order_delivered_customer_at,
        o.order_estimated_delivery_at,
        o.has_date_anomaly,
        o.is_late_delivery,

        coalesce(i.nb_items, 0)              as nb_items,
        coalesce(i.total_items_price, 0)     as total_items_price,
        coalesce(i.total_freight_value, 0)   as total_freight_value,

        coalesce(p.nb_payments, 0)           as nb_payments,
        coalesce(p.total_payment_value, 0)   as total_payment_value,

        r.avg_review_score,
        coalesce(r.nb_reviews, 0)            as nb_reviews,

        -- Délai de livraison en jours, utile pour des analyses de performance logistique
        date_diff('day', o.order_purchased_at, o.order_delivered_customer_at) as delivery_days

    from orders o
    left join items_agg    i on o.order_id = i.order_id
    left join payments_agg p on o.order_id = p.order_id
    left join reviews_agg  r on o.order_id = r.order_id

)

select * from final