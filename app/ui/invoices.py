"""
Invoice list + payment management + reprocess.
"""
import json
import os
from datetime import date

import pandas as pd
import streamlit as st

from app.database import queries
from app.services.extractor import extract_invoice
from app.services.storage import file_exists, read_file_bytes
from app.utils.helpers import format_currency
from app.utils.logger import get_logger

logger = get_logger("ui.invoices")


def render() -> None:
    st.title("Factures")

    # --- Filters ---
    with st.expander("Filtres", expanded=True):
        filter_col1, filter_col2, filter_col3, filter_col4 = st.columns(4)

        with filter_col1:
            statut_options = ["Tous", "non payé", "payé"]
            selected_statut = st.selectbox("Statut", statut_options, key="filter_statut")

        with filter_col2:
            fournisseurs = queries.list_fournisseurs()
            fourn_names = ["Tous"] + [f["nom"] for f in fournisseurs]
            selected_fourn = st.selectbox("Fournisseur", fourn_names, key="filter_fourn")

        with filter_col3:
            date_from = st.date_input("Date de", value=None, key="filter_date_from")

        with filter_col4:
            date_to = st.date_input("Date a", value=None, key="filter_date_to")

    # Resolve filter values
    statut_filter = None if selected_statut == "Tous" else selected_statut
    fourn_id_filter = None
    if selected_fourn != "Tous":
        match = next((f for f in fournisseurs if f["nom"] == selected_fourn), None)
        if match:
            fourn_id_filter = match["id"]

    date_from_str = date_from.isoformat() if date_from else None
    date_to_str = date_to.isoformat() if date_to else None

    factures = queries.list_factures(
        statut=statut_filter,
        fournisseur_id=fourn_id_filter,
        date_from=date_from_str,
        date_to=date_to_str,
    )

    if not factures:
        st.info("Aucune facture trouvee avec ces filtres.")
        return

    st.caption(f"{len(factures)} facture(s) trouvee(s)")

    # Display each invoice as an expander row
    for facture in factures:
        fid = facture["id"]
        title = (
            f"[{facture['statut'].upper()}] "
            f"{facture.get('fournisseur_nom') or 'Inconnu'} — "
            f"N°{facture.get('numero_facture') or '?'} — "
            f"{facture.get('date_facture') or '?'} — "
            f"{format_currency(facture.get('total_ttc'))}"
        )

        with st.expander(title, expanded=False):
            _render_invoice_detail(facture)

    st.divider()
    st.caption("Cliquez sur une facture pour voir les details, marquer payee ou retraiter.")


def _render_invoice_detail(facture: dict) -> None:
    fid = facture["id"]

    col_info, col_actions = st.columns([3, 1])

    with col_info:
        info_col1, info_col2 = st.columns(2)
        with info_col1:
            st.markdown(f"**Fournisseur :** {facture.get('fournisseur_nom') or '—'}")
            st.markdown(f"**N° Facture :** {facture.get('numero_facture') or '—'}")
            st.markdown(f"**Date :** {facture.get('date_facture') or '—'}")
            st.markdown(f"**Echeance :** {facture.get('date_echeance') or '—'}")
        with info_col2:
            st.markdown(f"**Total HT :** {format_currency(facture.get('total_ht'))}")
            st.markdown(f"**Total TTC :** {format_currency(facture.get('total_ttc'))}")
            st.markdown(f"**TVA :** {format_currency(facture.get('tva'))}")
            st.markdown(f"**Statut :** {facture.get('statut') or '—'}")
            if facture.get("date_paiement"):
                st.markdown(f"**Paye le :** {facture['date_paiement']}")

    with col_actions:
        if facture.get("statut") == "non payé":
            _render_mark_paid_section(fid)
        else:
            if st.button("Marquer non paye", key=f"unpay_{fid}"):
                queries.mark_unpaid(fid)
                logger.info("Invoice %d marked unpaid", fid)
                st.rerun()

        st.divider()
        _render_reprocess_section(fid, facture)

    # Products table
    produits = queries.get_produits_for_facture(fid)
    if produits:
        st.subheader("Produits")
        df_prod = pd.DataFrame(produits)[["nom", "quantite", "prix_unitaire", "prix_total"]]
        df_prod.columns = ["Produit", "Quantite", "Prix unitaire (€)", "Prix total (€)"]
        st.dataframe(
            df_prod.style.format(
                {"Prix unitaire (€)": "{:.2f}", "Prix total (€)": "{:.2f}"}, na_rep="—"
            ),
            use_container_width=True,
            hide_index=True,
        )

    # File link
    if facture.get("fichier_path") and file_exists(facture["fichier_path"]):
        fpath = facture["fichier_path"]
        ext = os.path.splitext(fpath)[1].lower()
        file_bytes = read_file_bytes(fpath)
        mime = "application/pdf" if ext == ".pdf" else "image/png" if ext == ".png" else "image/jpeg"
        st.download_button(
            label="Telecharger le fichier original",
            data=file_bytes,
            file_name=os.path.basename(fpath),
            mime=mime,
            key=f"dl_{fid}",
        )


def _render_mark_paid_section(facture_id: int) -> None:
    st.markdown("**Marquer comme payee**")
    pay_date_key = f"pay_date_{facture_id}"
    pay_date = st.date_input(
        "Date de paiement",
        value=date.today(),
        key=pay_date_key,
    )
    if st.button("Confirmer paiement", key=f"pay_btn_{facture_id}", type="primary"):
        queries.mark_paid(facture_id, pay_date.isoformat())
        logger.info("Invoice %d marked paid on %s", facture_id, pay_date)
        st.success("Marque comme payee.")
        st.rerun()


def _render_reprocess_section(facture_id: int, facture: dict) -> None:
    st.markdown("**Retraiter avec IA**")
    if st.button("Retraiter", key=f"reprocess_{facture_id}"):
        fpath = facture.get("fichier_path")
        if not fpath or not file_exists(fpath):
            st.error("Fichier introuvable, impossible de retraiter.")
            return

        with st.spinner("Retraitement en cours..."):
            file_bytes = read_file_bytes(fpath)
            result = extract_invoice(file_bytes, os.path.basename(fpath))

        if result.get("_extraction_error"):
            st.warning(f"Erreur : {result['_extraction_error']}")
        else:
            queries.update_facture_with_produits(facture_id, result)
            logger.info("Invoice %d reprocessed successfully", facture_id)
            st.success("Facture mise a jour avec succes.")
            st.rerun()
