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
    st.markdown(
        """
        <div style="max-width:380px;margin:4rem auto;text-align:center">
            <h1 style="font-family:'Cormorant Garamond',serif;font-size:2.5rem;color:#c9a84c;letter-spacing:0.1em;border:none;padding:0">FACTURES</h1>
            <p style="color:#6b6560;font-size:0.85rem;letter-spacing:0.15em;text-transform:uppercase;margin-bottom:2rem">Gestion fournisseurs</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown(
            '<p style="color:#6b6560;font-size:0.8rem;text-align:center;letter-spacing:0.1em;text-transform:uppercase">Accès réservé</p>',
            unsafe_allow_html=True,
        )
        email = st.text_input("Email", key="login_email", label_visibility="collapsed", placeholder="Email")
        password = st.text_input("Mot de passe", type="password", key="login_password", label_visibility="collapsed", placeholder="Mot de passe")
        st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)
        if st.button("SE CONNECTER", use_container_width=True, type="primary"):
            res, err = login(email, password)
            if err:
                st.error("Identifiants incorrects.")
            else:
                st.session_state.user = res.user
                st.rerun()
