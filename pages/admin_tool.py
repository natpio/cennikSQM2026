import streamlit as st
import hashlib

# 1. SPRAWDZENIE UPRAWNIEŃ (Musi być na samej górze)
# Sprawdzamy, czy użytkownik jest zalogowany i czy jego login to 'admin'
if "user" not in st.session_state or st.session_state.user != "admin":
    st.error("Brak uprawnień. Ta sekcja jest dostępna tylko dla administratora.")
    st.stop() # Zatrzymuje renderowanie reszty strony

# --- RESZTA KODU WYKONUJE SIĘ TYLKO DLA ADMINA ---

def make_hash(p): 
    return hashlib.sha256(p.strip().encode()).hexdigest()

st.set_page_config(page_title="SQM Admin Tool", layout="centered")

st.title("🔐 Generator Kont SQM")
st.markdown("Narzędzie dostępne wyłącznie dla głównego konta administratora.")

with st.form("generator"):
    u_name = st.text_input("Nowy login (np. marek_transport)").strip()
    u_pass = st.text_input("Nowe hasło", type="password").strip()
    submitted = st.form_submit_button("GENERUJ DANE")

if submitted:
    if u_name and u_pass:
        h_pass = make_hash(u_pass)
        st.success("Dane wygenerowane!")
        
        col1, col2 = st.columns(2)
        with col1:
            st.code(u_name, language="text")
            st.caption("username")
        with col2:
            st.code(h_pass, language="text")
            st.caption("password (hash)")
            
        st.warning("Wklej powyższe dane do zakładki USERS w Google Sheets.")
    else:
        st.error("Wypełnij oba pola!")
