with source as (

    select * from {{ ref('olist_order_payments_dataset') }}

),

renamed as (

    select
        order_id,
        payment_sequential,       -- ordre du paiement pour la commande (1, 2, 3...)
        payment_type,
        payment_installments,
        payment_value,

        -- Flag pour documenter le cas légitime des vouchers à 0€ (découvert en EDA)
        case
            when payment_value = 0 and payment_type = 'voucher' then true
            else false
        end as is_zero_value_voucher

    from source

)

select * from renamed