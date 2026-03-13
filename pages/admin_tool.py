import streamlit as st
import hashlib

# KONFIGURACJA STRONY (musi być pierwsza)
st.set_page_config(page_title="SQM Admin Tool", layout="centered")

# SPRAWDZENIE UPRAWNIEŃ
# W app.py v11 logujesz do st.session_state.user
current_user = st.session_state.get("user", "")

if current_user != "admin":
    st.error(f"Brak uprawnień. Zalogowano jako: '{current_user}'. Ta sekcja jest dostępna tylko dla konta 'admin'.")
    st.info("Wróć do strony głównej i upewnij się, że jesteś zalogowany na poprawne konto.")
    st.stop()

# --- INTERFEJS DLA ADMINA ---
def make_hash(p): 
    return hashlib.sha256(p.strip().encode()).hexdigest()

st.title("🔐 Generator Kont SQM")
st.markdown("Narzędzie generuje hasze SHA-256 do Arkusza Google.")

with st.form("generator"):
    u_name = st.text_input("Nowy login").strip()
    u_pass = st.text_input("Nowe hasło", type="password").strip()
    submitted = st.form_submit_button("GENERUJ DANE")

if submitted:
    if u_name and u_pass:
        h_pass = make_hash(u_pass)
        st.success("Dane gotowe!")
        col1, col2 = st.columns(2)
        with col1:
            st.code(u_name, language="text")
            st.caption("Do kolumny: username")
        with col2:
            st.code(h_pass, language="text")
            st.caption("Do kolumny: password")
    else:
        st.error("Uzupełnij pola!")
