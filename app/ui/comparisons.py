"""
Comparisons page: week-over-week, month-over-month, price variation, supplier comparison.
"""
import os
from datetime import date, timedelta

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from app.database import queries
from app.services.alerts import get_price_spikes
from app.utils.helpers import format_currency
from app.utils.logger import get_logger

logger = get_logger("ui.comparisons")


def _week_bounds(offset: int = 0):
    """Return (start, end) ISO strings for the week `offset` weeks ago."""
    today = date.today()
    monday = today - timedelta(days=today.weekday()) - timedelta(weeks=offset)
    sunday = monday + timedelta(days=6)
    return monday.isoformat(), min(sunday, today).isoformat()


def _month_bounds(offset: int = 0):
    """Return (start, end) ISO strings for the month `offset` months ago."""
    today = date.today()
    # Go to first of this month, then subtract months
    year = today.year
    month = today.month - offset
    while month <= 0:
        month += 12
        year -= 1

    first = date(year, month, 1)
    # Last day of the month
    if month == 12:
        last = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        last = date(year, month + 1, 1) - timedelta(days=1)

    return first.isoformat(), min(last, today).isoformat()


def render() -> None:
    st.title("Comparaisons")

    # ---- Week-over-week ----
    st.subheader("Semaine en cours vs semaine precedente")

    w_cur_start, w_cur_end = _week_bounds(0)
    w_prev_start, w_prev_end = _week_bounds(1)

    totals_wk = queries.spend_comparison_by_period(w_prev_start, w_prev_end, w_cur_start, w_cur_end)
    prev_wk = totals_wk["period1"]
    cur_wk = totals_wk["period2"]

    variation_wk = None
    if prev_wk and prev_wk != 0:
        variation_wk = ((cur_wk - prev_wk) / abs(prev_wk)) * 100

    wk_col1, wk_col2, wk_col3 = st.columns(3)
    wk_col1.metric(
        f"Semaine precedente\n({w_prev_start} — {w_prev_end})",
        format_currency(prev_wk),
    )
    wk_col2.metric(
        f"Semaine en cours\n({w_cur_start} — {w_cur_end})",
        format_currency(cur_wk),
        delta=f"{variation_wk:+.1f}%" if variation_wk is not None else None,
        delta_color="inverse",
    )
    wk_col3.metric(
        "Evolution",
        f"{variation_wk:+.1f}%" if variation_wk is not None else "—",
    )

    st.divider()

    # ---- Month-over-month ----
    st.subheader("Mois en cours vs mois precedent")

    m_cur_start, m_cur_end = _month_bounds(0)
    m_prev_start, m_prev_end = _month_bounds(1)

    totals_mo = queries.spend_comparison_by_period(m_prev_start, m_prev_end, m_cur_start, m_cur_end)
    prev_mo = totals_mo["period1"]
    cur_mo = totals_mo["period2"]

    variation_mo = None
    if prev_mo and prev_mo != 0:
        variation_mo = ((cur_mo - prev_mo) / abs(prev_mo)) * 100

    mo_col1, mo_col2, mo_col3 = st.columns(3)
    mo_col1.metric(
        f"Mois precedent\n({m_prev_start[:7]})",
        format_currency(prev_mo),
    )
    mo_col2.metric(
        f"Mois en cours\n({m_cur_start[:7]})",
        format_currency(cur_mo),
        delta=f"{variation_mo:+.1f}%" if variation_mo is not None else None,
        delta_color="inverse",
    )
    mo_col3.metric(
        "Evolution",
        f"{variation_mo:+.1f}%" if variation_mo is not None else "—",
    )

    st.divider()

    # ---- Price spikes ----
    pct_threshold = float(os.environ.get("PRICE_SPIKE_THRESHOLD", "10"))
    st.subheader(f"Variations de prix produits (seuil : +{pct_threshold:.0f}%)")

    spikes = get_price_spikes(pct_threshold)

    if not spikes:
        st.success("Aucune hausse de prix significative detectee.")
    else:
        df_spikes = pd.DataFrame(spikes)
        # Rename columns for display
        df_display = df_spikes.rename(
            columns={
                "nom": "Produit",
                "prix_precedent": "Prix precedent (€)",
                "prix_actuel": "Prix actuel (€)",
                "variation_pct": "Variation (%)",
                "date_precedente": "Date precedente",
                "date_actuelle": "Date actuelle",
                "fournisseur_actuel": "Fournisseur",
            }
        )

        def highlight_spike(val):
            if isinstance(val, float) and val > 0:
                return "background-color: #FFEBEE; color: #B71C1C; font-weight: bold"
            return ""

        styled = df_display.style.map(
            highlight_spike, subset=["Variation (%)"]
        ).format(
            {
                "Prix precedent (€)": "{:.2f}",
                "Prix actuel (€)": "{:.2f}",
                "Variation (%)": "{:+.1f}",
            },
            na_rep="—",
        )
        st.dataframe(styled, use_container_width=True, hide_index=True)

    st.divider()

    # ---- Supplier comparison: current month vs previous month ----
    st.subheader("Depenses par fournisseur : mois en cours vs mois precedent")

    supplier_comp = queries.supplier_spend_comparison(
        m_prev_start, m_prev_end, m_cur_start, m_cur_end
    )

    if not supplier_comp:
        st.info("Pas assez de donnees pour la comparaison par fournisseur.")
    else:
        df_sup = pd.DataFrame(supplier_comp)

        fig = go.Figure()
        fig.add_trace(
            go.Bar(
                name=f"Mois precedent ({m_prev_start[:7]})",
                x=df_sup["fournisseur"],
                y=df_sup["periode1"],
                marker_color="#90CAF9",
            )
        )
        fig.add_trace(
            go.Bar(
                name=f"Mois en cours ({m_cur_start[:7]})",
                x=df_sup["fournisseur"],
                y=df_sup["periode2"],
                marker_color="#1565C0",
            )
        )
        fig.update_layout(
            barmode="group",
            xaxis_title="Fournisseur",
            yaxis_title="Total TTC (€)",
            xaxis_tickangle=-30,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            margin=dict(l=0, r=0, t=40, b=0),
        )
        st.plotly_chart(fig, use_container_width=True)

        # Table view
        df_table = df_sup.rename(
            columns={
                "fournisseur": "Fournisseur",
                "periode1": f"Mois precedent (€)",
                "periode2": f"Mois en cours (€)",
            }
        )
        df_table["Evolution (€)"] = df_table["Mois en cours (€)"] - df_table["Mois precedent (€)"]
        df_table["Evolution (%)"] = df_table.apply(
            lambda r: (
                ((r["Mois en cours (€)"] - r["Mois precedent (€)"]) / abs(r["Mois precedent (€)"]) * 100)
                if r["Mois precedent (€)"] != 0
                else None
            ),
            axis=1,
        )

        def highlight_delta(val):
            if isinstance(val, float):
                if val > 0:
                    return "color: #B71C1C"
                if val < 0:
                    return "color: #1B5E20"
            return ""

        styled_table = df_table.style.map(
            highlight_delta, subset=["Evolution (€)", "Evolution (%)"]
        ).format(
            {
                "Mois precedent (€)": "{:.2f}",
                "Mois en cours (€)": "{:.2f}",
                "Evolution (€)": "{:+.2f}",
                "Evolution (%)": "{:+.1f}",
            },
            na_rep="—",
        )
        st.dataframe(styled_table, use_container_width=True, hide_index=True)
