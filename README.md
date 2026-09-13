# Projet dbt — Olist E-Commerce

Pipeline de transformation de données construit avec **dbt** et **DuckDB**, à partir du dataset public [Olist Brazilian E-Commerce](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce).

Le projet part de 9 fichiers CSV bruts (seeds) et les transforme, via une couche de nettoyage (staging) puis une couche métier (marts), en tables prêtes pour l'analyse business.

---

## Stack technique

- **dbt** (Data Build Tool) — orchestration des transformations SQL
- **DuckDB** — moteur de base de données local (fichier `olist.duckdb`)
- **Adapter** : `dbt-duckdb`

---

## Structure du projet

```
projet_dbt/
├── seeds/                          # CSV bruts sources
│   ├── olist_customers_dataset.csv
│   ├── olist_geolocation_dataset.csv
│   ├── olist_order_items_dataset.csv
│   ├── olist_order_payments_dataset.csv
│   ├── olist_order_reviews_dataset.csv
│   ├── olist_orders_dataset.csv
│   ├── olist_products_dataset.csv
│   ├── olist_sellers_dataset.csv
│   └── product_category_name_translation.csv
│
├── models/
│   ├── staging/
│   │   └── olist/
│   │       ├── stg_olist__customers.sql
│   │       ├── stg_olist__geolocation.sql
│   │       ├── stg_olist__order_items.sql
│   │       ├── stg_olist__orders.sql
│   │       ├── stg_olist__payments.sql
│   │       ├── stg_olist__products.sql
│   │       ├── stg_olist__reviews.sql
│   │       ├── stg_olist__sellers.sql
│   │       └── schema.yml           # tests + documentation staging
│   │
│   └── marts/
│       └── core/
│           ├── dim_customers.sql
│           ├── dim_products.sql
│           ├── dim_sellers.sql
│           ├── fct_orders.sql
│           ├── fct_order_items.sql
│           └── schema.yml           # tests + documentation marts
│
├── analyses_business_marts.sql      # requêtes d'analyse business (hors pipeline dbt)
├── profiles.yml
├── dbt_project.yml
└── olist.duckdb                     # base DuckDB générée localement
```

---

## Installation et exécution

### 1. Charger les seeds en base

```bash
cd projet_dbt
dbt seed
```

### 2. Construire l'ensemble du pipeline (modèles + tests)

```bash
dbt build
```

Ou étape par étape :

```bash
dbt run --select staging.olist
dbt test --select staging.olist
dbt run --select marts.core
dbt test --select marts.core
```

### 3. Explorer les données directement en SQL

```bash
duckdb olist.duckdb
```

⚠️ **Ne jamais garder une session DuckDB CLI ouverte en parallèle d'une commande `dbt run`/`dbt test`** — DuckDB verrouille le fichier en écriture, ce qui bloque dbt (`Conflicting lock` error). Fermer la session (`.quit`) avant de relancer dbt.

### 4. Générer la documentation dbt

```bash
dbt docs generate
dbt docs serve
```

---

## Modèle de données

### Couche staging (`models/staging/olist/`)

Une table par seed, nettoyée et renommée, sans logique métier. Chaque modèle documente les particularités réelles des données découvertes en EDA :

| Modèle | Grain | Particularité clé |
|---|---|---|
| `stg_olist__orders` | 1 commande | 61 commandes livrées avec incohérence de dates (flag `has_date_anomaly`) |
| `stg_olist__customers` | 1 commande (côté client) | `customer_id` ≠ `customer_unique_id` : le premier est technique (1 par commande), le second identifie la vraie personne |
| `stg_olist__order_items` | 1 article commandé | Clé logique composée : `order_id` + `order_item_id` |
| `stg_olist__payments` | 1 paiement | Clé logique composée : `order_id` + `payment_sequential`. Les paiements à 0€ sont des vouchers légitimes |
| `stg_olist__reviews` | 1 couple review/commande | Relation many-to-many : un `review_id` peut être associé à plusieurs `order_id` |
| `stg_olist__products` | 1 produit | Catégorie traduite en anglais (fallback en portugais si non traduite) |
| `stg_olist__sellers` | 1 vendeur | — |
| `stg_olist__geolocation` | 1 point GPS | Dédupliqué des doublons exacts (1 000 163 lignes brutes → 738 332 distinctes) |

### Couche marts (`models/marts/core/`)

Tables orientées analyse métier :

| Modèle | Grain | Description |
|---|---|---|
| `dim_customers` | 1 client (`customer_unique_id`) | Nombre de commandes, dates de 1ère/dernière commande, segment `one_time`/`returning` |
| `dim_products` | 1 produit | Enrichi de statistiques de vente (nb ventes, revenu total) |
| `dim_sellers` | 1 vendeur | Enrichi de statistiques de vente (nb articles/commandes vendus, revenu) |
| `fct_orders` | 1 commande | Montants agrégés, délai de livraison, note de satisfaction moyenne |
| `fct_order_items` | 1 article commandé | Grain fin pour croiser produit × vendeur × commande |

---

## Principales découvertes de l'EDA

- **~99 441 commandes**, **~96 096 clients uniques** (distinction `customer_id` / `customer_unique_id`)
- **97 % des clients** n'ont commandé qu'une seule fois
- **~8,11 %** des commandes livrées arrivent après la date estimée
- **768 commandes** n'ont pas de review associée (comportemental, pas une anomalie de données)
- **2 catégories de produits** (`pc_gamer`, `portateis_cozinha_e_preparadores_de_alimentos`) n'ont pas de traduction anglaise dans le référentiel
- **61 commandes livrées** ont un horodatage incohérent (probable bug de saisie côté source, isolé et documenté plutôt que corrigé silencieusement)

---

## Tests de qualité

Le projet compte une cinquantaine de tests dbt génériques (`unique`, `not_null`, `accepted_values`, `relationships`, `dbt_utils.unique_combination_of_columns`), répartis sur les couches staging et marts. Les tests reflètent les règles métier réelles découvertes en EDA plutôt que des suppositions — par exemple, aucun test `unique` n'est posé sur une colonne qui se répète légitimement (`customer_unique_id`, `review_id`).

---

## Requêtes d'analyse business

Le fichier `analyses_business_marts.sql` (à la racine, hors du dossier `models/`) regroupe des requêtes prêtes à l'emploi sur les marts, organisées par thématique :

1. Performance commerciale globale
2. Fidélisation client
3. Performance produit
4. Performance et satisfaction logistique
5. Performance vendeur

Ce fichier est volontairement en SQL pur (pas de Jinja `{{ ref() }}`) : il est fait pour être exécuté directement dans le CLI DuckDB, pas pour être parsé par dbt.
