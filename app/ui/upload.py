"""
Upload page: drag & drop / file picker, OpenAI extraction, review, save.
"""
import json
import os

import streamlit as st

from app.database.queries import insert_facture_with_produits
from app.services.extractor import extract_invoice
from app.services.storage import save_uploaded_file
from app.utils.logger import get_logger

logger = get_logger("ui.upload")


def render() -> None:
    st.title("Importer une facture")

    uploaded_file = st.file_uploader(
        "Glissez-déposez ou sélectionnez une facture (PDF, PNG, JPG)",
        type=["pdf", "png", "jpg", "jpeg"],
        key="upload_file_input",
    )

    if uploaded_file is None:
        st.info("Aucun fichier sélectionné. Veuillez importer une facture.")
        return

    file_bytes = uploaded_file.read()
    filename = uploaded_file.name

    # File preview
    st.subheader("Apercu du fichier")
    ext = os.path.splitext(filename)[1].lower()
    if ext == ".pdf":
        st.caption(f"Fichier PDF : **{filename}** ({len(file_bytes):,} octets)")
        # Show a download link for PDF preview
        st.download_button(
            label="Telecharger le PDF pour visualisation",
            data=file_bytes,
            file_name=filename,
            mime="application/pdf",
        )
    elif ext in (".jpg", ".jpeg", ".png"):
        st.image(file_bytes, caption=filename, use_container_width=True)

    st.divider()

    # Extraction trigger
    extract_key = f"extracted_{uploaded_file.file_id if hasattr(uploaded_file, 'file_id') else filename}"

    if extract_key not in st.session_state:
        st.session_state[extract_key] = None

    col1, col2 = st.columns([1, 3])
    with col1:
        run_extract = st.button("Analyser avec IA", type="primary", use_container_width=True)

    if run_extract:
        with st.spinner("Analyse en cours via GPT-4o Vision..."):
            result = extract_invoice(file_bytes, filename)
        st.session_state[extract_key] = result
        logger.info("Extraction done for %s, error=%s", filename, result.get("_extraction_error"))

    extracted = st.session_state[extract_key]

    if extracted is None:
        return

    # Show extraction error if any
    if extracted.get("_extraction_error"):
        st.error(f"Erreur d'extraction : {extracted['_extraction_error']}")
        st.warning("Vous pouvez corriger les champs manuellement avant de sauvegarder.")

    st.subheader("Donnees extraites — Verifiez et corrigez si besoin")

    with st.form("review_form"):
        col_a, col_b = st.columns(2)

        with col_a:
            fournisseur = st.text_input(
                "Fournisseur", value=extracted.get("fournisseur") or ""
            )
            date_facture = st.text_input(
                "Date facture (AAAA-MM-JJ)", value=extracted.get("date_facture") or ""
            )
            date_echeance = st.text_input(
                "Date echeance (AAAA-MM-JJ)", value=extracted.get("date_echeance") or ""
            )
            numero_facture = st.text_input(
                "Numero de facture", value=extracted.get("numero_facture") or ""
            )

        with col_b:
            total_ht = st.text_input(
                "Total HT (€)", value=str(extracted.get("total_ht") or "")
            )
            total_ttc = st.text_input(
                "Total TTC (€)", value=str(extracted.get("total_ttc") or "")
            )
            tva = st.text_input(
                "TVA (€)", value=str(extracted.get("tva") or "")
            )
            statut = st.selectbox(
                "Statut",
                options=["non payé", "payé"],
                index=0 if (extracted.get("statut") or "non payé") == "non payé" else 1,
            )

        st.subheader("Produits extraits")
        produits = extracted.get("produits") or []
        produits_json = st.text_area(
            "Produits (JSON — modifiable)",
            value=json.dumps(produits, ensure_ascii=False, indent=2),
            height=200,
        )

        submitted = st.form_submit_button("Confirmer et sauvegarder", type="primary")

    if submitted:
        # Parse products JSON
        try:
            produits_parsed = json.loads(produits_json)
        except json.JSONDecodeError as exc:
            st.error(f"JSON produits invalide : {exc}")
            return

        # Build consolidated data
        data = {
            "fournisseur": fournisseur.strip() or "Inconnu",
            "date_facture": date_facture.strip() or None,
            "date_echeance": date_echeance.strip() or None,
            "numero_facture": numero_facture.strip() or None,
            "total_ht": total_ht.strip() or None,
            "total_ttc": total_ttc.strip() or None,
            "tva": tva.strip() or None,
            "statut": statut,
            "produits": produits_parsed,
        }

        with st.spinner("Sauvegarde du fichier et insertion en base..."):
            fichier_path = save_uploaded_file(file_bytes, filename)
            facture_id = insert_facture_with_produits(data, fichier_path)

        st.success(
            f"Facture #{facture_id} sauvegardee avec succes ! "
            f"Fichier : {os.path.basename(fichier_path)}"
        )
        logger.info("Invoice saved: id=%d, file=%s", facture_id, fichier_path)

        # Clear session state for this upload
        st.session_state[extract_key] = None
