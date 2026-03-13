import streamlit as st
import hashlib

# Funkcja musi być identyczna jak w app.py, aby hasze pasowały
def make_hash(p): 
    return hashlib.sha256(p.strip().encode()).hexdigest()

st.set_page_config(page_title="SQM Admin Tool", layout="centered")

st.title("🔐 Generator Kont SQM")
st.markdown("Użyj tego narzędzia, aby przygotować dane do zakładki **USERS** w Google Sheets.")

with st.form("generator"):
    u_name = st.text_input("Nowy login (np. marek_transport)").strip()
    u_pass = st.text_input("Nowe hasło", type="password").strip()
    submitted = st.form_submit_button("GENERUJ DANE")

if submitted:
    if u_name and u_pass:
        h_pass = make_hash(u_pass)
        st.success("Gotowe! Skopiuj poniższe dane do Arkusza Google:")
        
        # Wyświetlenie w formie gotowej do wklejenia w komórki
        col1, col2 = st.columns(2)
        with col1:
            st.code(u_name, language="text")
            st.caption("Wklej do kolumny: username")
        with col2:
            st.code(h_pass, language="text")
            st.caption("Wklej do kolumny: password")
            
        st.warning("⚠️ Pamiętaj, aby w Arkuszu Google nie było zbędnych spacji przed lub po tekście.")
    else:
        st.error("Musisz podać login i hasło!")
