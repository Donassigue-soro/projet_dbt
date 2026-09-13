-- ============================================================
-- ANALYSES BUSINESS SUR LES MARTS DBT — PROJET OLIST
-- ============================================================
-- Prérequis : avoir lancé `dbt build` au préalable pour que
-- les modèles marts (dim_customers, dim_products, dim_sellers,
-- fct_orders, fct_order_items) existent dans olist.duckdb.
--
-- Utilisation : duckdb olist.duckdb < analyses_business_marts.sql
-- ou copier/coller chaque requête dans le CLI DuckDB.
-- ============================================================


-- ============================================================
-- THEMATIQUE 1 — PERFORMANCE COMMERCIALE GLOBALE
-- ============================================================

-- 1.1 Chiffre d'affaires et volume par mois (tendance globale)
SELECT
    date_trunc('month', order_purchased_at) AS mois,
    COUNT(DISTINCT order_id)                AS nb_commandes,
    SUM(total_payment_value)                AS revenu_total,
    ROUND(AVG(total_payment_value), 2)      AS panier_moyen
FROM fct_orders
WHERE order_status NOT IN ('canceled', 'unavailable')
GROUP BY mois
ORDER BY mois;


-- 1.2 Répartition du revenu par statut de commande (où part la valeur perdue ?)
SELECT
    order_status,
    COUNT(*)                    AS nb_commandes,
    SUM(total_payment_value)    AS revenu_associe
FROM fct_orders
GROUP BY order_status
ORDER BY revenu_associe DESC;


-- ============================================================
-- THEMATIQUE 2 — FIDELISATION CLIENT
-- ============================================================

-- 2.1 Poids du chiffre d'affaires : clients fidèles vs one-time
SELECT
    dc.customer_type,
    COUNT(DISTINCT dc.customer_unique_id) AS nb_clients,
    SUM(fo.total_payment_value)           AS revenu_total,
    ROUND(AVG(fo.total_payment_value), 2) AS panier_moyen
FROM dim_customers dc
INNER JOIN stg_olist__customers sc
    ON dc.customer_unique_id = sc.customer_unique_id
INNER JOIN fct_orders fo
    ON sc.customer_id = fo.customer_id
GROUP BY dc.customer_type;


-- 2.2 Top 10 des clients les plus rentables (segmentation VIP)
SELECT
    dc.customer_unique_id,
    dc.nb_orders,
    dc.customer_state,
    SUM(fo.total_payment_value) AS revenu_genere
FROM dim_customers dc
INNER JOIN stg_olist__customers sc
    ON dc.customer_unique_id = sc.customer_unique_id
INNER JOIN fct_orders fo
    ON sc.customer_id = fo.customer_id
GROUP BY dc.customer_unique_id, dc.nb_orders, dc.customer_state
ORDER BY revenu_genere DESC
LIMIT 10;


-- ============================================================
-- THEMATIQUE 3 — PERFORMANCE PRODUIT
-- ============================================================

-- 3.1 Top 10 catégories par revenu généré
SELECT
    product_category_name,
    COUNT(*)              AS nb_produits_distincts,
    SUM(nb_times_sold)     AS total_ventes,
    SUM(total_revenue)     AS revenu_total
FROM dim_products
GROUP BY product_category_name
ORDER BY revenu_total DESC
LIMIT 10;


-- 3.2 Produits jamais vendus (catalogue dormant)
SELECT COUNT(*) AS produits_jamais_vendus,
       ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM dim_products), 2) AS pct_catalogue
FROM dim_products
WHERE nb_times_sold = 0;


-- ============================================================
-- THEMATIQUE 4 — PERFORMANCE ET SATISFACTION LOGISTIQUE
-- ============================================================

-- 4.1 Taux de retard et note moyenne par catégorie de produit
SELECT
    dp.product_category_name,
    COUNT(DISTINCT foi.order_id)                              AS nb_commandes,
    ROUND(100.0 * SUM(CASE WHEN foi.is_late_delivery THEN 1 ELSE 0 END)
          / COUNT(DISTINCT foi.order_id), 2)                  AS pct_retard,
    ROUND(AVG(fo.avg_review_score), 2)                         AS note_moyenne
FROM fct_order_items foi
INNER JOIN dim_products dp ON foi.product_id = dp.product_id
INNER JOIN fct_orders fo   ON foi.order_id = fo.order_id
WHERE foi.order_status = 'delivered'
GROUP BY dp.product_category_name
HAVING COUNT(DISTINCT foi.order_id) > 100  -- éviter les catégories trop petites, peu fiables
ORDER BY pct_retard DESC
LIMIT 15;


-- ============================================================
-- THEMATIQUE 5 — PERFORMANCE VENDEUR
-- ============================================================

-- 5.1 Top 10 vendeurs par revenu, avec leur taux de retard associé
SELECT
    ds.seller_id,
    ds.seller_state,
    ds.nb_orders,
    ds.total_revenue,
    ROUND(100.0 * SUM(CASE WHEN foi.is_late_delivery THEN 1 ELSE 0 END)
          / COUNT(*), 2) AS pct_retard_livraison
FROM dim_sellers ds
INNER JOIN fct_order_items foi ON ds.seller_id = foi.seller_id
WHERE foi.order_status = 'delivered'
GROUP BY ds.seller_id, ds.seller_state, ds.nb_orders, ds.total_revenue
ORDER BY ds.total_revenue DESC
LIMIT 10;