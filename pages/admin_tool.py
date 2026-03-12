import streamlit as st
import hashlib

# ZABEZPIECZENIE: Sprawdzamy czy użytkownik jest zalogowany jako admin
if "authenticated" not in st.session_state or not st.session_state.authenticated:
    st.error("Musisz się zalogować w menu głównym, aby uzyskać dostęp.")
    st.stop()

if st.session_state.user != "admin":
    st.error("Brak uprawnień. Tylko użytkownik 'admin' może zarządzać kontami.")
    st.stop()

# --- WŁAŚCIWE NARZĘDZIE ---
st.title("👤 SQM | Zarządzanie Użytkownikami")
st.write("Generuj hashe haseł, aby dodać je do arkusza Google Sheets.")

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

with st.form("generator"):
    new_user = st.text_input("Nazwa nowego użytkownika")
    new_pw = st.text_input("Hasło do zakodowania", type="password")
    submit = st.form_submit_button("GENERUJ HASH")

if submit:
    if new_user and new_pw:
        h = hash_password(new_pw)
        st.success(f"Dla użytkownika: **{new_user}**")
        st.code(h)
        st.warning("Skopiuj ten kod i wklej go do swojego arkusza Google w zakładce USERS.")
    else:
        st.error("Wypełnij oba pola!")
