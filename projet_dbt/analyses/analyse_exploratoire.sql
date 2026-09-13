-- ============================================
-- 1. VOLUMÉTRIE ET UNICITÉ DES CLÉS
-- ============================================

-- Nombre de lignes par table
SELECT 'customers' AS table_name, COUNT(*) AS nb_rows FROM read_csv_auto('.../olist_customers_dataset.csv')
UNION ALL
SELECT 'orders', COUNT(*) FROM read_csv_auto('.../olist_orders_dataset.csv')
UNION ALL
SELECT 'order_items', COUNT(*) FROM read_csv_auto('.../olist_order_items_dataset.csv')
UNION ALL
SELECT 'payments', COUNT(*) FROM read_csv_auto('.../olist_order_payments_dataset.csv')
UNION ALL
SELECT 'reviews', COUNT(*) FROM read_csv_auto('.../olist_order_reviews_dataset.csv')
UNION ALL
SELECT 'products', COUNT(*) FROM read_csv_auto('.../olist_products_dataset.csv')
UNION ALL
SELECT 'sellers', COUNT(*) FROM read_csv_auto('.../olist_sellers_dataset.csv');

-- Vérifier l'unicité de customer_id
SELECT customer_id, COUNT(*) AS occurrences
FROM read_csv_auto('.../olist_customers_dataset.csv')
GROUP BY customer_id
HAVING COUNT(*) > 1;

-- Vérifier l'unicité de order_id dans orders
SELECT order_id, COUNT(*) AS occurrences
FROM read_csv_auto('.../olist_orders_dataset.csv')
GROUP BY order_id
HAVING COUNT(*) > 1;

-- ============================================
-- 2. VALEURS MANQUANTES (exemple sur orders)
-- ============================================

SELECT
    COUNT(*) AS total_rows,
    COUNT(*) - COUNT(order_approved_at) AS nulls_approved_at,
    COUNT(*) - COUNT(order_delivered_carrier_date) AS nulls_delivered_carrier,
    COUNT(*) - COUNT(order_delivered_customer_date) AS nulls_delivered_customer,
    COUNT(*) - COUNT(order_estimated_delivery_date) AS nulls_estimated_delivery
FROM read_csv_auto('.../olist_orders_dataset.csv');

-- ============================================
-- 3. DISTRIBUTION DES STATUTS DE COMMANDE
-- ============================================

SELECT order_status, COUNT(*) AS nb, 
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER(), 2) AS pct
FROM read_csv_auto('.../olist_orders_dataset.csv')
GROUP BY order_status
ORDER BY nb DESC;

-- ============================================
-- 4. COHÉRENCE TEMPORELLE DES COMMANDES
-- ============================================

SELECT COUNT(*) AS anomalies_dates
FROM read_csv_auto('.../olist_orders_dataset.csv')
WHERE order_delivered_customer_date < order_purchase_timestamp
   OR order_approved_at < order_purchase_timestamp;

-- ============================================
-- 5. ORPHELINS ENTRE TABLES (ex: order_items vs orders)
-- ============================================

SELECT COUNT(*) AS orphan_order_items
FROM read_csv_auto('.../olist_order_items_dataset.csv') oi
LEFT JOIN read_csv_auto('.../olist_orders_dataset.csv') o
    ON oi.order_id = o.order_id
WHERE o.order_id IS NULL;

-- ============================================
-- 6. CARDINALITÉ DES CATÉGORIES PRODUITS
-- ============================================

SELECT product_category_name, COUNT(*) AS nb_produits
FROM read_csv_auto('.../olist_products_dataset.csv')
GROUP BY product_category_name
ORDER BY nb_produits DESC
LIMIT 20;

-- ============================================
-- 7. DISTRIBUTION DES MOYENS DE PAIEMENT
-- ============================================

SELECT payment_type, COUNT(*) AS nb, AVG(payment_value) AS montant_moyen
FROM read_csv_auto('.../olist_order_payments_dataset.csv')
GROUP BY payment_type
ORDER BY nb DESC;

-- ============================================
-- 8. DISTRIBUTION DES NOTES DE REVIEW
-- ============================================

SELECT review_score, COUNT(*) AS nb
FROM read_csv_auto('.../olist_order_reviews_dataset.csv')
GROUP BY review_score
ORDER BY review_score;