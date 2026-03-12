import streamlit as st
import hashlib
import pandas as pd

# --- KONFIGURACJA STRONY ---
st.set_page_config(page_title="SQM VANTAGE | Admin Tool", layout="wide")

# --- FUNKCJE POMOCNICZE ---
def hash_password(password):
    """Generuje hash SHA-256 dla podanego hasła."""
    return hashlib.sha256(password.strip().encode()).hexdigest()

# --- ZABEZPIECZENIE PRZED NIEAUTORYZOWANYM DOSTĘPEM ---
# Sprawdzamy czy użytkownik jest zalogowany i czy ma uprawnienia admina
if "auth" not in st.session_state or not st.session_state.auth:
    st.error("⚠️ Brak autoryzacji. Zaloguj się na stronie głównej.")
    if st.button("Powrót do logowania"):
        st.switch_page("app.py")
    st.stop()

if st.session_state.user != "admin":
    st.error("🚫 Brak uprawnień. Ta sekcja jest dostępna tylko dla administratora.")
    st.stop()

# --- INTERFEJS ADMINA ---
st.title("🛠 SQM VANTAGE - Panel Administratora")
st.markdown("---")

col1, col2 = st.columns(2)

with col1:
    st.subheader("Generowanie Haszu Hasła")
    st.write("Wpisz nowe hasło poniżej, aby otrzymać hash do wklejenia w Google Sheets (zakładka USERS).")
    
    new_pass = st.text_input("Hasło do zakodowania", type="password", placeholder="Wpisz np. Nebraska2026")
    
    if new_pass:
        generated_hash = hash_password(new_pass)
        st.info("Gotowy Hash:")
        st.code(generated_hash, language="text")
        st.warning("☝️ Skopiuj powyższy ciąg i wklej go do kolumny 'password' w swoim arkuszu Google.")

with col2:
    st.subheader("Instrukcja aktualizacji bazy")
    st.markdown("""
    1. Otwórz arkusz **SQM_Logistyka_Cennik**.
    2. Przejdź do zakładki **USERS**.
    3. W kolumnie **username** wpisz nazwę użytkownika (np. `admin`).
    4. W kolumnie **password** wklej wygenerowany obok hash.
    5. Odśwież aplikację SQM Vantage.
    """)

st.markdown("---")
st.subheader("Podgląd aktualnej sesji")
st.json({
    "Zalogowany użytkownik": st.session_state.user,
    "Status autoryzacji": st.session_state.auth,
    "Czas sesji": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
})

if st.button("⬅️ Powrót do kalkulatora"):
    st.switch_page("app.py")
