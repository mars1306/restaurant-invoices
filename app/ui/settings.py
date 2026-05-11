"""
Settings page for application configuration (API keys, etc.)
"""
import streamlit as st
from app.database.queries import get_config, set_config

def render() -> None:
    st.title("Paramètres")
    st.markdown("Configurez vos clés API et les seuils d'alerte.")

    # License & Security Section
    st.header("Activation & Licence")
    license_key = get_config("LICENSE_KEY", "DEMO-MODE")
    new_license = st.text_input("Clé de Licence Manager", value=license_key, type="password")
    
    if st.button("Activer la Licence"):
        set_config("LICENSE_KEY", new_license)
        st.success("Application activée avec succès !")

    st.markdown("---")
    # API Keys Section
    st.header("Connexion AI")
    anthropic_key = get_config("ANTHROPIC_API_KEY", "")
    
    new_key = st.text_input(
        "Clé API Anthropic (Claude)", 
        value=anthropic_key, 
        type="password",
        help="Utilisée pour l'extraction automatique des factures via Claude Vision."
    )
    
    if st.button("Enregistrer la clé API"):
        if new_key:
            set_config("ANTHROPIC_API_KEY", new_key)
            st.success("Clé API enregistrée avec succès !")
        else:
            st.warning("Veuillez entrer une clé valide.")

    st.markdown("---")

    # Alert Thresholds Section
    st.header("Seuils d'Alerte")
    
    spike_threshold = get_config("PRICE_SPIKE_THRESHOLD", "10")
    new_spike = st.number_input(
        "Seuil de hausse de prix (%)", 
        min_value=1, 
        max_value=100, 
        value=int(spike_threshold)
    )
    
    overdue_threshold = get_config("OVERDUE_DAYS_THRESHOLD", "30")
    new_overdue = st.number_input(
        "Seuil de facture impayée (jours)", 
        min_value=1, 
        value=int(overdue_threshold)
    )
    
    if st.button("Enregistrer les seuils"):
        set_config("PRICE_SPIKE_THRESHOLD", str(new_spike))
        set_config("OVERDUE_DAYS_THRESHOLD", str(new_overdue))
        st.success("Paramètres mis à jour !")
