import os
import datetime as dt
import duckdb
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "olist.duckdb")

# Palette : encre, jade (couleur principale), or (mise en avant), gris-bleu
INK, JADE, GOLD, MIST, GRID = "#1B2A41", "#0E7C66", "#E9B44C", "#9AA8B8", "#E6EAF0"

st.set_page_config(page_title="Olist — Tableau de bord", page_icon="📦", layout="wide")

st.markdown(
    f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;600;800&display=swap');
    html, body, [class*="css"] {{ font-family: 'Manrope', sans-serif; }}
    h1 {{ font-weight: 800; letter-spacing: -0.02em; }}
    h3 {{ font-weight: 600; }}
    [data-testid="stMetric"] {{
        background: #fff; border: 1px solid {GRID}; border-left: 4px solid {JADE};
        border-radius: 6px; padding: 14px 18px;
    }}
    [data-testid="stMetricLabel"] {{ color: {MIST}; }}
    [data-testid="stMetricValue"] {{ font-weight: 800; font-size: 1.9rem; }}
    [data-testid="stMetricValue"] > div {{ overflow: visible; text-overflow: clip; white-space: nowrap; }}    section[data-testid="stSidebar"] {{ border-right: 1px solid {GRID}; background: #fff; }}
    section[data-testid="stSidebar"] [role="radiogroup"] label {{ padding: 4px 0; }}
    section[data-testid="stSidebar"] a {{ color: {JADE}; font-weight: 600; }}
    </style>
    """,
    unsafe_allow_html=True,
)

# ============================================================
# OUTILS
# ============================================================

CATEGORIES_FR = {
    "health_beauty": "Santé & beauté", "watches_gifts": "Montres & cadeaux",
    "bed_bath_table": "Literie & bain", "sports_leisure": "Sport & loisirs",
    "computers_accessories": "Informatique", "furniture_decor": "Mobilier & déco",
    "cool_stuff": "Objets insolites", "housewares": "Maison", "auto": "Auto",
    "garden_tools": "Jardin", "toys": "Jouets", "baby": "Bébé",
    "perfumery": "Parfumerie", "telephony": "Téléphonie",
    "office_furniture": "Mobilier de bureau", "stationery": "Papeterie",
    "computers": "Ordinateurs", "pet_shop": "Animalerie",
    "fashion_bags_accessories": "Sacs & accessoires", "electronics": "Électronique",
}
STATUTS_FR = {
    "delivered": "Livrée", "shipped": "Expédiée", "canceled": "Annulée",
    "unavailable": "Indisponible", "invoiced": "Facturée", "processing": "En préparation",
    "created": "Créée", "approved": "Approuvée",
}


def cat_fr(s: pd.Series) -> pd.Series:
    return s.map(lambda c: CATEGORIES_FR.get(c, str(c).replace("_", " ").capitalize()))


def fmt_int(n) -> str:
    return f"{int(n):,}".replace(",", " ")


def fmt_money(n) -> str:
    n = float(n)
    return f"{n / 1e6:.1f} M R$".replace(".", ",") if n >= 1e6 else f"{fmt_int(n)} R$"


def style(fig, height=380, legend=False):
    fig.update_layout(
        template="plotly_white", height=height, showlegend=legend,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Manrope, sans-serif", color=INK, size=13),
        margin=dict(l=10, r=10, t=30, b=10),
        legend=dict(orientation="h", y=1.12, x=0),
    )
    fig.update_xaxes(gridcolor=GRID, zeroline=False)
    fig.update_yaxes(gridcolor=GRID, zeroline=False)
    return fig


def show(fig, **kw):
    st.plotly_chart(style(fig, **kw), width='stretch')


@st.cache_resource
def get_connection():
    try:
        return duckdb.connect(DB_PATH, read_only=True)
    except Exception as e:
        st.error(f"Connexion impossible à `{DB_PATH}` : {e}")
        st.stop()


@st.cache_data(ttl=600)
def run_query(sql: str) -> pd.DataFrame:
    try:
        cur = get_connection().cursor()
        try:
            return cur.execute(sql).df()
        finally:
            cur.close()
    except Exception as e:
        st.error(f"Échec de la requête :\n\n```sql\n{sql}\n```\n\n{e}")
        st.stop()

# ============================================================
# NAVIGATION
# ============================================================

st.sidebar.markdown(
    f"""
    <div style="font-size:1.5rem;font-weight:800;letter-spacing:-0.02em;color:{INK};">Olist</div>
    <div style="color:{MIST};font-size:0.9rem;margin-bottom:1rem;">
        Pilotage des ventes, de la livraison et de la satisfaction client
    </div>
    """,
    unsafe_allow_html=True,
)

PAGES = {
    "Vue d'ensemble": "Vue d'ensemble",
    "Fidélisation client": "Fidélisation client",
    "Performance produit": "Produits",
    "Logistique & satisfaction": "Livraison et satisfaction",
    "Performance vendeur": "Vendeurs",
}
choix = st.sidebar.radio("Section", list(PAGES.values()), label_visibility="collapsed")
page = next(k for k, v in PAGES.items() if v == choix)

# ---- Filtres (pages basées sur fct_orders) ----
DEB, FIN = dt.date(2017, 1, 1), dt.date(2018, 8, 31)
d_debut, d_fin, etats = DEB, FIN, []

if page in ("Vue d'ensemble", "Fidélisation client"):
    st.sidebar.markdown("---")
    st.sidebar.markdown("**Filtres**")
    etats_dispo = run_query(
        "SELECT DISTINCT customer_state FROM dim_customers "
        "WHERE customer_state IS NOT NULL ORDER BY 1"
    )["customer_state"].tolist()
    dates = st.sidebar.date_input(
        "Période d'achat", value=(DEB, FIN),
        min_value=dt.date(2016, 9, 1), max_value=dt.date(2018, 10, 31),
        format="DD/MM/YYYY",
    )
    if isinstance(dates, (tuple, list)) and len(dates) == 2:
        d_debut, d_fin = dates
    etats = st.sidebar.multiselect("État du client", etats_dispo, placeholder="Tous les états")


def filtres(alias: str = "") -> str:
    """Condition SQL (période + états) à insérer après un WHERE sur fct_orders."""
    p = f"{alias}." if alias else ""
    cond = (f"{p}order_purchased_at >= '{d_debut}' "
            f"AND {p}order_purchased_at < '{d_fin + dt.timedelta(days=1)}'")
    if etats:
        liste = ", ".join("'" + e.replace("'", "''") + "'" for e in etats)
        cond += (f" AND {p}customer_id IN (SELECT customer_id FROM stg_olist__customers "
                 f"WHERE customer_state IN ({liste}))")
    return cond


def libelle_filtres() -> str:
    zone = ", ".join(etats) if etats else "tous les états"
    return f"Période : {d_debut:%d/%m/%Y} au {d_fin:%d/%m/%Y} · Clients : {zone}"


st.sidebar.markdown("---")

st.sidebar.markdown("**À propos**")
st.sidebar.caption(
    "Projet réalisé seul, de la donnée brute au tableau de bord : "
    "SQL, dbt, DuckDB, Python et Streamlit."
)
st.sidebar.caption("Données publiques Olist, commandes de 2016 à 2018. Montants en réais brésiliens (R$).")
st.sidebar.markdown("[Code source sur GitHub](https://github.com/Donassigue-soro/projet_dbt)")

# ============================================================
# PAGE 1 — VUE D'ENSEMBLE
# ============================================================

if page == "Vue d'ensemble":
    st.title("Vue d'ensemble")
    st.caption(libelle_filtres())

    kpi = run_query(f"""
        SELECT
            COUNT(DISTINCT order_id) AS nb_commandes,
            SUM(total_payment_value) AS revenu_total,
            ROUND(AVG(total_payment_value), 2) AS panier_moyen,
            ROUND(100.0 * SUM(CASE WHEN is_late_delivery THEN 1 ELSE 0 END)
                  / NULLIF(SUM(CASE WHEN order_status = 'delivered' THEN 1 ELSE 0 END), 0), 2) AS pct_retard
        FROM fct_orders
        WHERE order_status NOT IN ('canceled', 'unavailable')
          AND {filtres()}
    """).iloc[0]

    if int(kpi["nb_commandes"]) == 0:
        st.warning("Aucune commande pour ces filtres. Élargissez la période ou l'état.")
        st.stop()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Commandes", fmt_int(kpi["nb_commandes"]))
    c2.metric("Revenu total", fmt_money(kpi["revenu_total"]))
    c3.metric("Panier moyen", f"{kpi['panier_moyen']:.2f} R$".replace(".", ","))
    pct = kpi["pct_retard"]
    c4.metric("Livraisons en retard", "n.d." if pd.isna(pct) else f"{pct:.1f} %".replace(".", ","))
    st.caption("Commandes annulées ou indisponibles exclues.")

    st.markdown("### Évolution mensuelle du revenu et des commandes")

    monthly = run_query(f"""
        SELECT date_trunc('month', order_purchased_at) AS mois,
               COUNT(DISTINCT order_id) AS nb_commandes,
               SUM(total_payment_value) AS revenu_total
        FROM fct_orders
        WHERE order_status NOT IN ('canceled', 'unavailable')
          AND {filtres()}
        GROUP BY mois ORDER BY mois
    """)
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_bar(x=monthly["mois"], y=monthly["revenu_total"], name="Revenu (R$)",
                marker_color=JADE, opacity=0.85)
    fig.add_scatter(x=monthly["mois"], y=monthly["nb_commandes"], name="Commandes",
                    mode="lines+markers", line=dict(color=GOLD, width=3), secondary_y=True)
    fig.update_yaxes(title_text="Revenu (R$)", secondary_y=False)
    fig.update_yaxes(title_text="Commandes", secondary_y=True, showgrid=False)
    show(fig, legend=True)

    st.markdown("### Revenu par statut de commande")
    by_status = run_query(f"""
        SELECT order_status, COUNT(*) AS nb_commandes, SUM(total_payment_value) AS revenu_associe
        FROM fct_orders WHERE {filtres()}
        GROUP BY order_status ORDER BY revenu_associe DESC
    """)
    by_status["Statut"] = by_status["order_status"].map(lambda s: STATUTS_FR.get(s, s))
    ca, cb = st.columns([2, 1])
    with ca:
        show(go.Figure(go.Bar(x=by_status["Statut"], y=by_status["revenu_associe"], marker_color=JADE)))
    with cb:
        st.dataframe(
            by_status[["Statut", "nb_commandes", "revenu_associe"]].rename(
                columns={"nb_commandes": "Commandes", "revenu_associe": "Revenu (R$)"}),
            width='stretch', hide_index=True,
            column_config={"Revenu (R$)": st.column_config.NumberColumn(format="%.0f")})

# ============================================================
# PAGE 2 — FIDÉLISATION CLIENT
# ============================================================

elif page == "Fidélisation client":
    seg = run_query(f"""
        SELECT dc.customer_type,
               COUNT(DISTINCT dc.customer_unique_id) AS nb_clients,
               SUM(fo.total_payment_value) AS revenu_total
        FROM dim_customers dc
        INNER JOIN stg_olist__customers sc ON dc.customer_unique_id = sc.customer_unique_id
        INNER JOIN fct_orders fo ON sc.customer_id = fo.customer_id
        WHERE {filtres('fo')}
        GROUP BY dc.customer_type
    """)
    if seg.empty:
        st.title("Fidélisation client")
        st.caption(libelle_filtres())
        st.warning("Aucun client pour ces filtres. Élargissez la période ou l'état.")
        st.stop()

    seg["Type"] = seg["customer_type"].map({"one_time": "Achat unique", "returning": "Client fidèle"})
    part = 100 * seg.loc[seg["customer_type"] == "one_time", "nb_clients"].sum() / seg["nb_clients"].sum()
    st.title(f"{part:.0f} % des clients n'achètent qu'une seule fois")
    st.caption(libelle_filtres())

    colors = {"Achat unique": MIST, "Client fidèle": JADE}
    c1, c2 = st.columns(2)
    for col, val, titre in [(c1, "nb_clients", "Part des clients"), (c2, "revenu_total", "Part du revenu")]:
        with col:
            st.markdown(f"**{titre}**")
            f = go.Figure(go.Pie(labels=seg["Type"], values=seg[val], hole=0.6,
                                 marker_colors=[colors[t] for t in seg["Type"]],
                                 textinfo="percent", sort=False))
            show(f, height=300, legend=True)

    st.markdown("### Les 10 clients les plus rentables")
    top = run_query(f"""
        SELECT dc.nb_orders, dc.customer_state, SUM(fo.total_payment_value) AS revenu_genere
        FROM dim_customers dc
        INNER JOIN stg_olist__customers sc ON dc.customer_unique_id = sc.customer_unique_id
        INNER JOIN fct_orders fo ON sc.customer_id = fo.customer_id
        WHERE {filtres('fo')}
        GROUP BY dc.customer_unique_id, dc.nb_orders, dc.customer_state
        ORDER BY revenu_genere DESC LIMIT 10
    """)
    top.insert(0, "Rang", range(1, len(top) + 1))
    st.dataframe(
        top.rename(columns={"nb_orders": "Commandes", "customer_state": "État", "revenu_genere": "Revenu (R$)"}),
        width='stretch', hide_index=True,
        column_config={"Revenu (R$)": st.column_config.NumberColumn(format="%.0f")})

    st.markdown("### Où vivent les clients")
    cond_etat = ("WHERE customer_state IN (" + ", ".join("'" + e.replace("'", "''") + "'" for e in etats) + ")") if etats else ""
    by_state = run_query(f"""
        SELECT customer_state, COUNT(*) AS nb_clients FROM dim_customers
        {cond_etat} GROUP BY customer_state ORDER BY nb_clients DESC
    """)
    show(go.Figure(go.Bar(x=by_state["customer_state"], y=by_state["nb_clients"], marker_color=JADE)))
    st.caption("Ce graphique suit le filtre d'état, pas la période.")

# ============================================================
# PAGE 3 — PERFORMANCE PRODUIT
# ============================================================

elif page == "Performance produit":
    st.title("Performance produit")

    cats = run_query("""
        SELECT product_category_name, SUM(total_revenue) AS revenu_total
        FROM dim_products WHERE product_category_name IS NOT NULL
        GROUP BY product_category_name ORDER BY revenu_total DESC LIMIT 15
    """)
    cats["Catégorie"] = cat_fr(cats["product_category_name"])
    cats = cats.sort_values("revenu_total")
    st.markdown("### Les 15 catégories qui rapportent le plus")
    colors = [GOLD if i >= len(cats) - 3 else JADE for i in range(len(cats))]
    show(go.Figure(go.Bar(x=cats["revenu_total"], y=cats["Catégorie"], orientation="h",
                          marker_color=colors)), height=480)
    st.caption("Les trois premières catégories en or. Revenu en R$.")

    c1, c2 = st.columns([1, 2])
    with c1:
        d = run_query("""
            SELECT COUNT(*) AS n,
                   ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM dim_products), 2) AS pct
            FROM dim_products WHERE nb_times_sold = 0
        """).iloc[0]
        st.metric("Produits jamais vendus", fmt_int(d["n"]))
        st.metric("Part du catalogue", f"{d['pct']:.1f} %".replace(".", ","))
    with c2:
        st.markdown("**Top 10 produits par revenu**")
        tp = run_query("""
            SELECT product_category_name, nb_times_sold, total_revenue
            FROM dim_products ORDER BY total_revenue DESC LIMIT 10
        """)
        tp["product_category_name"] = cat_fr(tp["product_category_name"])
        st.dataframe(
            tp.rename(columns={"product_category_name": "Catégorie", "nb_times_sold": "Ventes",
                               "total_revenue": "Revenu (R$)"}),
            width='stretch', hide_index=True,
            column_config={"Revenu (R$)": st.column_config.NumberColumn(format="%.0f")})

# ============================================================
# PAGE 4 — LOGISTIQUE & SATISFACTION
# ============================================================

elif page == "Logistique & satisfaction":
    st.title("Logistique & satisfaction")

    bc = run_query("""
        SELECT dp.product_category_name,
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
        ORDER BY pct_retard DESC LIMIT 15
    """)
    bc["Catégorie"] = cat_fr(bc["product_category_name"])

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Taux de retard par catégorie (%)**")
        b = bc.sort_values("pct_retard")
        show(go.Figure(go.Bar(x=b["pct_retard"], y=b["Catégorie"], orientation="h",
                              marker_color=GOLD)), height=460)
    with c2:
        st.markdown("**Plus il y a de retard, plus la note baisse**")
        f = go.Figure(go.Scatter(
            x=bc["pct_retard"], y=bc["note_moyenne"], mode="markers", text=bc["Catégorie"],
            marker=dict(size=bc["nb_commandes"], sizemode="area",
                        sizeref=2.0 * bc["nb_commandes"].max() / 40**2,
                        color=JADE, opacity=0.7, line=dict(color="#fff", width=1)),
            hovertemplate="%{text}<br>Retard : %{x} %<br>Note : %{y}<extra></extra>"))
        f.update_xaxes(title_text="Retard (%)")
        f.update_yaxes(title_text="Note moyenne (sur 5)")
        show(f, height=460)
        st.caption("Taille des bulles : nombre de commandes.")

    st.markdown("### Notes de satisfaction")
    sc = run_query("""
        SELECT review_score, COUNT(*) AS nb FROM stg_olist__reviews
        GROUP BY review_score ORDER BY review_score
    """)
    palette = {1: GOLD, 2: GOLD, 3: MIST, 4: JADE, 5: JADE}
    show(go.Figure(go.Bar(x=sc["review_score"].astype(str) + " ★", y=sc["nb"],
                          marker_color=[palette[int(s)] for s in sc["review_score"]])), height=320)

# ============================================================
# PAGE 5 — PERFORMANCE VENDEUR
# ============================================================

elif page == "Performance vendeur":
    st.title("Performance vendeur")

    st.markdown("### Les 10 vendeurs qui rapportent le plus")
    ts = run_query("""
        SELECT ds.seller_id, ds.seller_state, ds.nb_orders, ds.total_revenue,
               ROUND(100.0 * SUM(CASE WHEN foi.is_late_delivery THEN 1 ELSE 0 END)
                     / COUNT(*), 2) AS pct_retard_livraison
        FROM dim_sellers ds
        INNER JOIN fct_order_items foi ON ds.seller_id = foi.seller_id
        WHERE foi.order_status = 'delivered'
        GROUP BY ds.seller_id, ds.seller_state, ds.nb_orders, ds.total_revenue
        ORDER BY ds.total_revenue DESC LIMIT 10
    """)
    ts["seller_id"] = ts["seller_id"].str[:8] + "…"
    st.dataframe(
        ts.rename(columns={"seller_id": "Vendeur", "seller_state": "État", "nb_orders": "Commandes",
                           "total_revenue": "Revenu (R$)", "pct_retard_livraison": "Retard (%)"}),
        width='stretch', hide_index=True,
        column_config={"Revenu (R$)": st.column_config.NumberColumn(format="%.0f")})

    st.markdown("### Revenu par état du vendeur")
    bs = run_query("""
        SELECT seller_state, COUNT(*) AS nb_vendeurs, SUM(total_revenue) AS revenu_total
        FROM dim_sellers GROUP BY seller_state ORDER BY revenu_total DESC
    """)
    show(go.Figure(go.Bar(x=bs["seller_state"], y=bs["revenu_total"], marker_color=JADE)))