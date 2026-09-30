"""
Dashboard interactif — Projet Olist (dbt + DuckDB)

Se connecte en LECTURE SEULE à olist.duckdb pour ne jamais entrer en conflit
avec les commandes `dbt run` / `dbt build` / `dbt test` lancées en parallèle.

Lancement :
    streamlit run dashboard_olist.py

Prérequis :
    pip install streamlit duckdb plotly pandas
    Avoir déjà lancé `dbt build` au moins une fois pour que les marts existent.
"""

import duckdb
import pandas as pd
import plotly.express as px
import streamlit as st

# ============================================================
# CONFIGURATION
# ============================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "olist.duckdb")

st.set_page_config(
    page_title="Olist — Dashboard",
    page_icon="📦",
    layout="wide",
)


@st.cache_resource
def get_connection():
    # read_only=True : permet de lire pendant qu'un `dbt build` tourne ailleurs,
    # sans jamais provoquer d'erreur de lock DuckDB.
    try:
        return duckdb.connect(DB_PATH, read_only=True)
    except Exception as e:
        st.error(
            f"Impossible de se connecter à `{DB_PATH}` en lecture seule.\n\n"
            f"Cause probable : une session DuckDB CLI ou un `dbt build` est "
            f"encore ouvert(e) et verrouille le fichier.\n\n"
            f"Erreur DuckDB : {e}"
        )
        st.stop()


@st.cache_data(ttl=600)
def run_query(sql: str) -> pd.DataFrame:
    con = get_connection()
    try:
        df = con.execute(sql).df()
    except Exception as e:
        st.error(f"Échec de la requête SQL :\n\n```sql\n{sql}\n```\n\nErreur : {e}")
        st.stop()
    if df is None:
        st.error("La requête n'a retourné aucun résultat exploitable (df=None).")
        st.stop()
    return df


# ============================================================
# SIDEBAR — NAVIGATION
# ============================================================

st.sidebar.title("📦 Olist Dashboard")
page = st.sidebar.radio(
    "Section",
    [
        "Vue d'ensemble",
        "Fidélisation client",
        "Performance produit",
        "Logistique & satisfaction",
        "Performance vendeur",
    ],
)

st.sidebar.markdown("---")
st.sidebar.caption(
    "Données issues du pipeline dbt (staging → marts). "
    "Connexion en lecture seule à `olist.duckdb`."
)


# ============================================================
# PAGE 1 — VUE D'ENSEMBLE
# ============================================================

if page == "Vue d'ensemble":
    st.title("Vue d'ensemble")

    kpi = run_query("""
        SELECT
            COUNT(DISTINCT order_id) AS nb_commandes,
            SUM(total_payment_value) AS revenu_total,
            ROUND(AVG(total_payment_value), 2) AS panier_moyen,
            ROUND(100.0 * SUM(CASE WHEN is_late_delivery THEN 1 ELSE 0 END)
                  / NULLIF(SUM(CASE WHEN order_status = 'delivered' THEN 1 ELSE 0 END), 0), 2) AS pct_retard
        FROM fct_orders
        WHERE order_status NOT IN ('canceled', 'unavailable')
    """).iloc[0]

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Commandes", f"{int(kpi['nb_commandes']):,}".replace(",", " "))
    col2.metric("Revenu total", f"{kpi['revenu_total']:,.0f} R$".replace(",", " "))
    col3.metric("Panier moyen", f"{kpi['panier_moyen']:.2f} R$")
    col4.metric("Taux de retard livraison", f"{kpi['pct_retard']:.2f} %")

    st.markdown("### Évolution mensuelle du revenu et du volume de commandes")

    monthly = run_query("""
        SELECT
            date_trunc('month', order_purchased_at) AS mois,
            COUNT(DISTINCT order_id) AS nb_commandes,
            SUM(total_payment_value) AS revenu_total
        FROM fct_orders
        WHERE order_status NOT IN ('canceled', 'unavailable')
        GROUP BY mois
        ORDER BY mois
    """)

    fig = px.bar(monthly, x="mois", y="revenu_total", title="Revenu mensuel (R$)")
    fig.add_scatter(
        x=monthly["mois"], y=monthly["nb_commandes"] * (monthly["revenu_total"].max() / monthly["nb_commandes"].max()),
        mode="lines+markers", name="Nb commandes (échelle relative)", yaxis="y",
    )
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("### Répartition du revenu par statut de commande")

    by_status = run_query("""
        SELECT order_status, COUNT(*) AS nb_commandes, SUM(total_payment_value) AS revenu_associe
        FROM fct_orders
        GROUP BY order_status
        ORDER BY revenu_associe DESC
    """)

    col_a, col_b = st.columns([2, 1])
    with col_a:
        fig2 = px.bar(by_status, x="order_status", y="revenu_associe", title="Revenu par statut")
        st.plotly_chart(fig2, use_container_width=True)
    with col_b:
        st.dataframe(by_status, use_container_width=True, hide_index=True)


# ============================================================
# PAGE 2 — FIDELISATION CLIENT
# ============================================================

elif page == "Fidélisation client":
    st.title("Fidélisation client")

    seg = run_query("""
        SELECT
            dc.customer_type,
            COUNT(DISTINCT dc.customer_unique_id) AS nb_clients,
            SUM(fo.total_payment_value) AS revenu_total,
            ROUND(AVG(fo.total_payment_value), 2) AS panier_moyen
        FROM dim_customers dc
        INNER JOIN stg_olist__customers sc ON dc.customer_unique_id = sc.customer_unique_id
        INNER JOIN fct_orders fo ON sc.customer_id = fo.customer_id
        GROUP BY dc.customer_type
    """)

    col1, col2 = st.columns(2)
    with col1:
        fig = px.pie(seg, names="customer_type", values="nb_clients",
                     title="Répartition des clients (nombre)")
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        fig2 = px.pie(seg, names="customer_type", values="revenu_total",
                      title="Répartition du revenu généré")
        st.plotly_chart(fig2, use_container_width=True)

    st.markdown("### Top 10 des clients les plus rentables")

    top_clients = run_query("""
        SELECT
            dc.customer_unique_id,
            dc.nb_orders,
            dc.customer_state,
            SUM(fo.total_payment_value) AS revenu_genere
        FROM dim_customers dc
        INNER JOIN stg_olist__customers sc ON dc.customer_unique_id = sc.customer_unique_id
        INNER JOIN fct_orders fo ON sc.customer_id = fo.customer_id
        GROUP BY dc.customer_unique_id, dc.nb_orders, dc.customer_state
        ORDER BY revenu_genere DESC
        LIMIT 10
    """)
    st.dataframe(top_clients, use_container_width=True, hide_index=True)

    st.markdown("### Répartition géographique des clients (par état)")

    by_state = run_query("""
        SELECT customer_state, COUNT(*) AS nb_clients
        FROM dim_customers
        GROUP BY customer_state
        ORDER BY nb_clients DESC
    """)
    fig3 = px.bar(by_state, x="customer_state", y="nb_clients", title="Clients par état")
    st.plotly_chart(fig3, use_container_width=True)


# ============================================================
# PAGE 3 — PERFORMANCE PRODUIT
# ============================================================

elif page == "Performance produit":
    st.title("Performance produit")

    top_categories = run_query("""
        SELECT
            product_category_name,
            COUNT(*) AS nb_produits_distincts,
            SUM(nb_times_sold) AS total_ventes,
            SUM(total_revenue) AS revenu_total
        FROM dim_products
        WHERE product_category_name IS NOT NULL
        GROUP BY product_category_name
        ORDER BY revenu_total DESC
        LIMIT 15
    """)

    fig = px.bar(
        top_categories.sort_values("revenu_total"),
        x="revenu_total", y="product_category_name",
        orientation="h", title="Top 15 catégories par revenu",
    )
    st.plotly_chart(fig, use_container_width=True)

    col1, col2 = st.columns(2)

    with col1:
        dormant = run_query("""
            SELECT COUNT(*) AS produits_jamais_vendus,
                   ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM dim_products), 2) AS pct_catalogue
            FROM dim_products
            WHERE nb_times_sold = 0
        """).iloc[0]
        st.metric("Produits jamais vendus", f"{int(dormant['produits_jamais_vendus']):,}".replace(",", " "))
        st.metric("Part du catalogue dormant", f"{dormant['pct_catalogue']:.2f} %")

    with col2:
        st.markdown("**Top 10 produits par revenu**")
        top_products = run_query("""
            SELECT product_id, product_category_name, nb_times_sold, total_revenue
            FROM dim_products
            ORDER BY total_revenue DESC
            LIMIT 10
        """)
        st.dataframe(top_products, use_container_width=True, hide_index=True)


# ============================================================
# PAGE 4 — LOGISTIQUE & SATISFACTION
# ============================================================

elif page == "Logistique & satisfaction":
    st.title("Logistique & satisfaction")

    by_category = run_query("""
        SELECT
            dp.product_category_name,
            COUNT(DISTINCT foi.order_id) AS nb_commandes,
            ROUND(100.0 * SUM(CASE WHEN foi.is_late_delivery THEN 1 ELSE 0 END)
                  / COUNT(DISTINCT foi.order_id), 2) AS pct_retard,
            ROUND(AVG(fo.avg_review_score), 2) AS note_moyenne
        FROM fct_order_items foi
        INNER JOIN dim_products dp ON foi.product_id = dp.product_id
        INNER JOIN fct_orders fo ON foi.order_id = fo.order_id
        WHERE foi.order_status = 'delivered' AND dp.product_category_name IS NOT NULL
        GROUP BY dp.product_category_name
        HAVING COUNT(DISTINCT foi.order_id) > 100
        ORDER BY pct_retard DESC
        LIMIT 15
    """)

    col1, col2 = st.columns(2)
    with col1:
        fig = px.bar(by_category.sort_values("pct_retard"),
                     x="pct_retard", y="product_category_name",
                     orientation="h", title="Taux de retard par catégorie (%)")
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        fig2 = px.scatter(by_category, x="pct_retard", y="note_moyenne",
                           size="nb_commandes", hover_name="product_category_name",
                           title="Retard vs note moyenne (taille = nb commandes)")
        st.plotly_chart(fig2, use_container_width=True)

    st.markdown("### Distribution des notes de satisfaction")

    scores = run_query("""
        SELECT review_score, COUNT(*) AS nb
        FROM stg_olist__reviews
        GROUP BY review_score
        ORDER BY review_score
    """)
    fig3 = px.bar(scores, x="review_score", y="nb", title="Répartition des notes (1 à 5)")
    st.plotly_chart(fig3, use_container_width=True)


# ============================================================
# PAGE 5 — PERFORMANCE VENDEUR
# ============================================================

elif page == "Performance vendeur":
    st.title("Performance vendeur")

    top_sellers = run_query("""
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
        LIMIT 10
    """)

    st.markdown("### Top 10 vendeurs par revenu")
    st.dataframe(top_sellers, use_container_width=True, hide_index=True)

    by_state = run_query("""
        SELECT seller_state, COUNT(*) AS nb_vendeurs, SUM(total_revenue) AS revenu_total
        FROM dim_sellers
        GROUP BY seller_state
        ORDER BY revenu_total DESC
    """)
    fig = px.bar(by_state, x="seller_state", y="revenu_total", title="Revenu par état vendeur")
    st.plotly_chart(fig, use_container_width=True)