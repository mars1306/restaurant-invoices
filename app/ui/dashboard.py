"""
Dashboard page: KPIs, charts, overdue invoices.
"""
import os
from datetime import date, timedelta

import pandas as pd
import plotly.express as px
import streamlit as st

from app.database import queries
from app.database.queries import get_config
from app.services.alerts import get_overdue_invoices
from app.utils.helpers import format_currency
from app.utils.logger import get_logger

logger = get_logger("ui.dashboard")


def render() -> None:
    st.title("Tableau de bord")

    # Check for API Key and show setup prompt if missing
    anthropic_key = get_config("OPENROUTER_API_KEY")
    if not anthropic_key:
        st.warning("⚠️ **Configuration requise** : Vous devez configurer votre clé API OpenRouter pour utiliser l'extraction automatique.")
        if st.button("Aller aux Paramètres ⚙️"):
            st.session_state.nav_page = "Paramètres"
            st.rerun()
        st.divider()

    today = date.today()
    # Current week (Monday to Sunday)
    week_start = (today - timedelta(days=today.weekday()))
    week_end = today
    # Current month
    month_start = today.replace(day=1)
    month_end = today

    # --- KPIs ---
    total_week = queries.kpi_total_period(week_start.isoformat(), week_end.isoformat())
    total_month = queries.kpi_total_period(month_start.isoformat(), month_end.isoformat())
    unpaid = queries.kpi_unpaid()

    days_threshold = int(get_config("OVERDUE_DAYS_THRESHOLD", "30"))

    # Mobile responsive layout for metrics
    if st.session_state.get("mobile_mode", False):
        st.metric("Total Semaine (TTC)", format_currency(total_week), help=f"Du {week_start.strftime('%d/%m')} au {week_end.strftime('%d/%m')}")
        st.metric("Total Mois (TTC)", format_currency(total_month), help=f"Depuis le {month_start.strftime('%d/%m')}")
        st.metric("Factures non payées", str(unpaid["count"]))
        st.metric("Montant impayé (TTC)", format_currency(unpaid["total"]))
    else:
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total semaine (TTC)", format_currency(total_week), help=f"Du {week_start.strftime('%d/%m')} au {week_end.strftime('%d/%m')}")
        col2.metric("Total mois (TTC)", format_currency(total_month), help=f"Depuis le {month_start.strftime('%d/%m')}")
        col3.metric("Factures non payees", str(unpaid["count"]))
        col4.metric("Montant impaye (TTC)", format_currency(unpaid["total"]))

    st.divider()

    # --- Charts ---
    chart_col1, chart_col2 = st.columns(2)

    with chart_col1:
        st.subheader("Depenses par fournisseur (30 derniers jours)")
        supplier_data = queries.spend_by_supplier_last_n_days(30)
        if supplier_data:
            df_sup = pd.DataFrame(supplier_data)
            fig = px.bar(
                df_sup,
                x="fournisseur",
                y="total",
                labels={"fournisseur": "Fournisseur", "total": "Total TTC (€)"},
                color="fournisseur",
                color_discrete_sequence=px.colors.qualitative.Set2,
            )
            fig.update_layout(
                showlegend=False,
                xaxis_tickangle=-30,
                margin=dict(l=0, r=0, t=20, b=0),
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Aucune donnee disponible pour les 30 derniers jours.")

    with chart_col2:
        st.subheader("Depenses hebdomadaires (8 dernieres semaines)")
        weekly_data = queries.weekly_spend_last_n_weeks(8)
        if weekly_data:
            df_wk = pd.DataFrame(weekly_data)
            fig2 = px.line(
                df_wk,
                x="semaine",
                y="total",
                labels={"semaine": "Semaine", "total": "Total TTC (€)"},
                markers=True,
                line_shape="spline",
            )
            fig2.update_traces(line_color="#2196F3", marker_size=8)
            fig2.update_layout(margin=dict(l=0, r=0, t=20, b=0))
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("Aucune donnee disponible pour les 8 dernieres semaines.")

    st.divider()

    # --- Overdue invoices ---
    st.subheader(f"Factures en retard (echeance depassee de plus de {days_threshold} jours)")
    overdue = get_overdue_invoices(days_threshold)

    if not overdue:
        st.success("Aucune facture en retard.")
    else:
        df_overdue = pd.DataFrame(overdue)[
            ["id", "fournisseur_nom", "numero_facture", "date_facture", "date_echeance", "total_ttc"]
        ].rename(
            columns={
                "id": "ID",
                "fournisseur_nom": "Fournisseur",
                "numero_facture": "N° Facture",
                "date_facture": "Date",
                "date_echeance": "Echeance",
                "total_ttc": "Total TTC (€)",
            }
        )
        st.dataframe(
            df_overdue.style.format({"Total TTC (€)": "{:.2f}"}),
            use_container_width=True,
            hide_index=True,
        )
        st.warning(f"{len(overdue)} facture(s) en retard de paiement.")
