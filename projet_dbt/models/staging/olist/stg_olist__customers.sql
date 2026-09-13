with source as (

    select * from {{ ref('olist_customers_dataset') }}

),

renamed as (

    select
        customer_id,               -- clé technique : 1 par commande
        customer_unique_id,        -- vraie clé personne physique (utilisée dans dim_customers)
        customer_zip_code_prefix,
        customer_city,
        customer_state

    from source

)

select * from renamed