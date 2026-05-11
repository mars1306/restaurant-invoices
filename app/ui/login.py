import streamlit as st
from app.services.supabase_client import supabase

def signup(email, password):
    try:
        response = supabase.auth.sign_up({"email": email, "password": password})
        return response, None
    except Exception as e:
        return None, str(e)

def login(email, password):
    try:
        response = supabase.auth.sign_in_with_password({"email": email, "password": password})
        return response, None
    except Exception as e:
        return None, str(e)

def logout():
    supabase.auth.sign_out()
    st.session_state.user = None
    st.rerun()

def render_login_page():
    st.title("👨‍🍳 Gestion Factures SaaS")
    st.info("Accès réservé. Veuillez vous connecter avec vos identifiants fournis.")
    
    email = st.text_input("Email", key="login_email")
    password = st.text_input("Mot de passe", type="password", key="login_password")
    
    if st.button("Se connecter", use_container_width=True):
        res, err = login(email, password)
        if err:
            st.error("Identifiants incorrects ou accès non autorisé.")
        else:
            st.session_state.user = res.user
            st.success("Connecté !")
            st.rerun()
