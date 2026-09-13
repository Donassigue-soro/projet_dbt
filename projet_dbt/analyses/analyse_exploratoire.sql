-- ============================================
-- 1. VOLUMÉTRIE ET UNICITÉ DES CLÉS
-- ============================================

-- Nombre de lignes par table
SELECT 'customers' AS table_name, COUNT(*) AS nb_rows FROM olist_customers_dataset
UNION ALL
SELECT 'orders', COUNT(*) FROM olist_orders_dataset
UNION ALL
SELECT 'order_items', COUNT(*) FROM olist_order_items_dataset
UNION ALL
SELECT 'payments', COUNT(*) FROM olist_order_payments_dataset
UNION ALL
SELECT 'reviews', COUNT(*) FROM olist_order_reviews_dataset
UNION ALL
SELECT 'products', COUNT(*) FROM olist_products_dataset
UNION ALL
SELECT 'sellers', COUNT(*) FROM olist_sellers_dataset;

-- 1. Vérifier la distinction customer_id vs customer_unique_id
SELECT 
    COUNT(*) AS total_rows,
    COUNT(DISTINCT customer_id) AS distinct_customer_id,
    COUNT(DISTINCT customer_unique_id) AS distinct_customer_unique_id
FROM olist_customers_dataset;

-- 2. Combien de commandes sans review ?
SELECT COUNT(*) AS orders_sans_review
FROM olist_orders_dataset o
LEFT JOIN olist_order_reviews_dataset r ON o.order_id = r.order_id
WHERE r.order_id IS NULL;

-- 3. Distribution du nombre d'items par commande
SELECT nb_items, COUNT(*) AS nb_commandes
FROM (
    SELECT order_id, COUNT(*) AS nb_items
    FROM olist_order_items_dataset
    GROUP BY order_id
) t
GROUP BY nb_items
ORDER BY nb_items;

-- 4. Distribution du nombre de paiements par commande
SELECT nb_payments, COUNT(*) AS nb_commandes
FROM (
    SELECT order_id, COUNT(*) AS nb_payments
    FROM olist_order_payments_dataset
    GROUP BY order_id
) t
GROUP BY nb_payments
ORDER BY nb_payments;

-- 5. Combien de clients ont commandé plusieurs fois ?
SELECT nb_commandes, COUNT(*) AS nb_clients
FROM (
    SELECT customer_unique_id, COUNT(*) AS nb_commandes
    FROM olist_customers_dataset
    GROUP BY customer_unique_id
) t
GROUP BY nb_commandes
ORDER BY nb_commandes;

-- 6. Vérifier les valeurs extrêmes du nombre de paiements (les 29 !)
SELECT order_id, COUNT(*) AS nb_payments, SUM(payment_value) AS total_paye
FROM olist_order_payments_dataset
GROUP BY order_id
ORDER BY nb_payments DESC
LIMIT 5;

-- 7. Y a-t-il des paiements à 0 ou négatifs (anomalies) ?
SELECT COUNT(*) AS anomalies
FROM olist_order_payments_dataset
WHERE payment_value <= 0;

-- 8. Répartition des order_status (pour comprendre le cycle de vie commande)
SELECT order_status, COUNT(*) AS nb, 
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER(), 2) AS pct
FROM olist_orders_dataset
GROUP BY order_status
ORDER BY nb DESC;

-- 9. Les 768 commandes sans review : ont-elles un statut particulier ?
SELECT o.order_status, COUNT(*) AS nb
FROM olist_orders_dataset o
LEFT JOIN olist_order_reviews_dataset r ON o.order_id = r.order_id
WHERE r.order_id IS NULL
GROUP BY o.order_status
ORDER BY nb DESC;

-- 10. Regarder le détail des 9 paiements anormaux
SELECT *
FROM olist_order_payments_dataset
WHERE payment_value <= 0;

-- 11. Vérifier la cohérence installments vs nb_payments (l'hypothèse "carte fractionnée")
SELECT order_id, payment_type, payment_installments, payment_value
FROM olist_order_payments_dataset
WHERE order_id = 'fa65dad1b0e818e3ccc5cb0e39231352';

-- 12. Le client aux 17 commandes : à isoler
SELECT customer_unique_id, COUNT(*) AS nb_commandes
FROM olist_customers_dataset
GROUP BY customer_unique_id
ORDER BY nb_commandes DESC
LIMIT 1;

-- 13. Valeurs manquantes sur products (souvent le point faible du dataset Olist)
SELECT
    COUNT(*) AS total_rows,
    COUNT(*) - COUNT(product_category_name) AS nulls_category,
    COUNT(*) - COUNT(product_weight_g) AS nulls_weight,
    COUNT(*) - COUNT(product_length_cm) AS nulls_length,
    COUNT(*) - COUNT(product_description_lenght) AS nulls_description
FROM olist_products_dataset;

-- 14. Cohérence des dates de commande (délais négatifs = anomalie)
SELECT COUNT(*) AS anomalies_delais
FROM olist_orders_dataset
WHERE order_delivered_customer_date < order_purchase_timestamp
   OR order_approved_at < order_purchase_timestamp
   OR order_delivered_customer_date < order_approved_at;

-- 15. Retards de livraison (livré après la date estimée) — utile pour un futur KPI satisfaction
SELECT 
    COUNT(*) AS nb_commandes_livrees,
    COUNT(*) FILTER (WHERE order_delivered_customer_date > order_estimated_delivery_date) AS nb_retards,
    ROUND(100.0 * COUNT(*) FILTER (WHERE order_delivered_customer_date > order_estimated_delivery_date) / COUNT(*), 2) AS pct_retards
FROM olist_orders_dataset
WHERE order_status = 'delivered';

-- 16. product_category_name en anglais existe-t-il pour toutes les catégories ? (jointure avec la table de traduction)
SELECT COUNT(DISTINCT p.product_category_name) AS categories_produits,
       COUNT(DISTINCT t.product_category_name) AS categories_traduites,
       COUNT(*) FILTER (WHERE t.product_category_name_english IS NULL) AS categories_sans_traduction
FROM olist_products_dataset p
LEFT JOIN product_category_name_translation t 
    ON p.product_category_name = t.product_category_name;

-- 16 bis. Vraie liste des catégories sans traduction (par catégorie, pas par produit)
SELECT DISTINCT p.product_category_name
FROM olist_products_dataset p
LEFT JOIN product_category_name_translation t 
    ON p.product_category_name = t.product_category_name
WHERE p.product_category_name IS NOT NULL
  AND t.product_category_name IS NULL;

-- 17. Vérifier si les 610 lignes sans catégorie sont bien les mêmes partout
SELECT COUNT(*) AS produits_totalement_vides
FROM olist_products_dataset
WHERE product_category_name IS NULL
  AND product_description_lenght IS NULL
  AND product_weight_g IS NULL;

-- 18. Détail des 61 anomalies de dates (pour voir si un pattern se dégage, ex: statut particulier)
SELECT order_status, COUNT(*) AS nb
FROM olist_orders_dataset
WHERE order_delivered_customer_date < order_purchase_timestamp
   OR order_approved_at < order_purchase_timestamp
   OR order_delivered_customer_date < order_approved_at
GROUP BY order_status;