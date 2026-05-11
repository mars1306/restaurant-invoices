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
    
    tab1, tab2 = st.tabs(["Connexion", "Inscription"])
    
    with tab1:
        email = st.text_input("Email", key="login_email")
        password = st.text_input("Mot de passe", type="password", key="login_password")
        if st.button("Se connecter"):
            res, err = login(email, password)
            if err:
                st.error(f"Erreur : {err}")
            else:
                st.session_state.user = res.user
                st.success("Connecté !")
                st.rerun()
                
    with tab2:
        new_email = st.text_input("Email", key="signup_email")
        new_password = st.text_input("Mot de passe", type="password", key="signup_password")
        if st.button("Créer un compte"):
            res, err = signup(new_email, new_password)
            if err:
                st.error(f"Erreur : {err}")
            else:
                st.success("Compte créé ! Veuillez vérifier votre email (si activé) ou vous connecter.")
