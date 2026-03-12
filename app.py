import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import re
import hashlib
import extra_streamlit_components as stx

# --- KONFIGURACJA ZASOBÓW ---
SHEET_ID = "1sYlXP6WVzPE09qfmydQYQNsjiZcDgRSJGyWoXfjmkDY"
URL_BAZA = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=CENNIK_BAZA"
URL_OPLATY = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=OPLATY_STALE"
URL_USERS = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=USERS"

st.set_page_config(page_title="SQM VANTAGE", layout="wide")

# --- FUNKCJE BEZPIECZEŃSTWA ---
def hash_password(password):
    return hashlib.sha256(password.strip().encode()).hexdigest()

def get_cookie_manager():
    return stx.CookieManager()

cookie_manager = get_cookie_manager()

# WYMUSZENIE ODŚWIEŻANIA: ttl=1 sprawia, że każda zmiana w Sheets jest widoczna od razu
@st.cache_data(ttl=1)
def fetch_user_database():
    try:
        df = pd.read_csv(URL_USERS)
        # Czyszczenie nagłówków i danych z ewentualnych spacji
        df.columns = df.columns.str.strip()
        df['username'] = df['username'].astype(str).str.strip()
        df['password'] = df['password'].astype(str).str.strip()
        return dict(zip(df['username'], df['password']))
    except Exception as e:
        # Ratunkowy admin (login: admin, hasło: SQM2026!)
        return {"admin": "7990494490f237f37435f3089d38c1a6007e0c8b055371190458df8d03f0b07b"}

user_db = fetch_user_database()

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

# Sprawdzenie ciasteczka
saved_session = cookie_manager.get(cookie="sqm_vantage_v6")
if saved_session in user_db:
    st.session_state.authenticated = True
    st.session_state.current_user = saved_session

# --- PANEL LOGOWANIA ---
if not st.session_state.authenticated:
    st.markdown("""
        <style>
        .stApp { background: #030508; color: white; }
        .login-box {
            max-width: 400px; margin: 80px auto; padding: 30px;
            background: rgba(255, 255, 255, 0.05);
            border-radius: 15px; border: 1px solid rgba(255, 255, 255, 0.1);
            text-align: center;
        }
        </style>
    """, unsafe_allow_html=True)
    
    with st.container():
        st.markdown('<div class="login-box">', unsafe_allow_html=True)
        st.image("https://www.sqm.pl/wp-content/themes/sqm/img/logo-sqm.png", width=180)
        st.title("SQM VANTAGE")
        
        # .strip() na wejściu usuwa spacje, które telefon lub komputer mogą dodać same
        user_input = st.text_input("Użytkownik").strip()
        pass_input = st.text_input("Hasło", type="password").strip()
        
        if st.button("ZALOGUJ SIĘ", use_container_width=True):
            if user_input in user_db and user_db[user_input] == hash_password(pass_input):
                st.session_state.authenticated = True
                st.session_state.current_user = user_input
                cookie_manager.set("sqm_vantage_v6", user_input, expires_at=datetime.now() + timedelta(days=30))
                st.rerun()
            else:
                st.error("Błąd! Sprawdź czy login i hasło są poprawne.")
                # Wyświetlamy debug (tylko dla Ciebie teraz), żebyś widział co widzi aplikacja:
                with st.expander("Debug systemu (ukryj to potem)"):
                    st.write(f"Wpisany login: '{user_input}'")
                    st.write(f"Hash wpisanego hasła: {hash_password(pass_input)}")
                    st.write(f"Dostępne loginy w bazie: {list(user_db.keys())}")
        st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

# --- DALSZA CZĘŚĆ APLIKACJI (INTERFEJS LOGISTYKA) ---
@st.cache_data(ttl=300)
def load_logistics_data():
    baza = pd.read_csv(URL_BAZA)
    oplaty = pd.read_csv(URL_OPLATY)
    baza.columns = baza.columns.str.strip()
    oplaty.columns = oplaty.columns.str.strip()
    def clean_val(x):
        s = re.sub(r'[^\d.]', '', str(x).replace(',', '.'))
        return float(s) if s else 0.0
    for col in ['Eksport', 'Import', 'Postoj']: baza[col] = baza[col].apply(clean_val)
    oplaty['Wartosc'] = oplaty['Wartosc'].apply(clean_val)
    return baza, oplaty

df_baza, df_oplaty = load_logistics_data()
cfg = dict(zip(df_oplaty['Parametr'], df_oplaty['Wartosc']))

with st.sidebar:
    st.image("https://www.sqm.pl/wp-content/themes/sqm/img/logo-sqm.png", width=150)
    st.write(f"Zalogowany: **{st.session_state.current_user}**")
    miasto = st.selectbox("MIASTO", sorted(df_baza['Miasto'].unique()))
    waga = st.number_input("WAGA (kg)", value=500)
    d1 = st.date_input("ZAŁADUNEK", datetime.now())
    d2 = st.date_input("POWRÓT", datetime.now() + timedelta(days=2))
    dni = max(0, (d2-d1).days)
    if st.button("WYLOGUJ"):
        cookie_manager.delete("sqm_vantage_v6")
        st.session_state.authenticated = False
        st.rerun()

# Obliczenia
w_c = waga * cfg.get('WAGA_BUFOR', 1.2)
v_t = "BUS" if w_c <= 1000 else "SOLO" if w_c <= 5500 else "FTL"
row = df_baza[(df_baza['Miasto'] == miasto) & (df_baza['Typ_Pojazdu'] == v_t)]

if not row.empty:
    e, i = row['Eksport'].mean(), row['Import'].mean()
    p = row['Postoj'].mean() * dni
    park = dni * cfg.get('PARKING_DAY', 30)
    total = e + i + p + park

    st.markdown(f"""
    <div style="background: rgba(255,255,255,0.05); padding: 40px; border-radius: 20px; border-left: 8px solid #ed8936;">
        <h1 style="color: white; font-size: 80px; margin: 0;">€ {total:,.2f}</h1>
        <p style="color: #94a3b8; font-size: 20px;">Rekomendowana stawka transportowa netto</p>
    </div>
    """, unsafe_allow_html=True)
