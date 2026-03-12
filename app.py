import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import re
import hashlib
import extra_streamlit_components as stx

# --- KONFIGURACJA ---
SHEET_ID = "1sYlXP6WVzPE09qfmydQYQNsjiZcDgRSJGyWoXfjmkDY"
URL_BAZA = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=CENNIK_BAZA"
URL_OPLATY = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=OPLATY_STALE"
URL_USERS = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=USERS"

st.set_page_config(page_title="SQM VANTAGE", layout="wide")

# --- SYSTEM LOGOWANIA ---
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def get_manager():
    return stx.CookieManager()

cookie_manager = get_manager()

@st.cache_data(ttl=60)
def fetch_users():
    try:
        df = pd.read_csv(URL_USERS)
        return dict(zip(df['username'].astype(str), df['password'].astype(str)))
    except:
        # HASŁO RATUNKOWE: Jeśli arkusz nie działa, login: admin, hasło: SQM2026!
        return {"admin": "7990494490f237f37435f3089d38c1a6007e0c8b055371190458df8d03f0b07b"}

user_db = fetch_users()

if "auth" not in st.session_state:
    st.session_state.auth = False

# Sprawdź ciasteczko
saved_user = cookie_manager.get(cookie="sqm_session")
if saved_user in user_db:
    st.session_state.auth = True
    st.session_state.user = saved_user

if not st.session_state.auth:
    st.markdown("<style>.stApp {background: #0f172a;}</style>", unsafe_allow_html=True)
    _, col, _ = st.columns([1,2,1])
    with col:
        st.image("https://www.sqm.pl/wp-content/themes/sqm/img/logo-sqm.png", width=200)
        st.title("Logowanie SQM VANTAGE")
        u = st.text_input("Użytkownik")
        p = st.text_input("Hasło", type="password")
        if st.button("ZALOGUJ"):
            if u in user_db and user_db[u] == hash_password(p):
                st.session_state.auth = True
                st.session_state.user = u
                cookie_manager.set("sqm_session", u, expires_at=datetime.now() + timedelta(days=30))
                st.rerun()
            else:
                st.error("Błędne dane. Upewnij się, że hash w Google Sheets jest poprawny.")
    st.stop()

# --- GŁÓWNA APLIKACJA ---
@st.cache_data(ttl=300)
def load_data():
    b = pd.read_csv(URL_BAZA)
    o = pd.read_csv(URL_OPLATY)
    b.columns = b.columns.str.strip()
    def clean(v):
        s = re.sub(r'[^\d.]', '', str(v).replace(',', '.'))
        return float(s) if s else 0.0
    for c in ['Eksport', 'Import', 'Postoj']:
        if c in b.columns: b[c] = b[c].apply(clean)
    o['Wartosc'] = o['Wartosc'].apply(clean)
    return b, o

df_baza, df_oplaty = load_data()
cfg = dict(zip(df_oplaty['Parametr'], df_oplaty['Wartosc']))

with st.sidebar:
    st.image("https://www.sqm.pl/wp-content/themes/sqm/img/logo-sqm.png", width=150)
    st.write(f"Zalogowany: **{st.session_state.user}**")
    miasto = st.selectbox("KIERUNEK", sorted(df_baza['Miasto'].unique()))
    waga = st.number_input("WAGA (kg)", value=500)
    d1 = st.date_input("ZAŁADUNEK", datetime.now())
    d2 = st.date_input("POWRÓT", datetime.now() + timedelta(days=2))
    dni = max(0, (d2-d1).days)
    if st.button("WYLOGUJ"):
        cookie_manager.delete("sqm_session")
        st.session_state.auth = False
        st.rerun()

# OBLICZENIA
w_calc = waga * cfg.get('WAGA_BUFOR', 1.2)
v_type = "BUS" if w_calc <= 1000 else "SOLO" if w_calc <= 5500 else "FTL"
row = df_baza[(df_baza['Miasto'] == miasto) & (df_baza['Typ_Pojazdu'] == v_type)]

if not row.empty:
    e, i = row['Eksport'].mean(), row['Import'].mean()
    p = row['Postoj'].mean() * dni
    park = dni * cfg.get('PARKING_DAY', 30)
    total = e + i + p + park

    # GENEROWANIE HTML (BEZ NOWYCH LINII)
    items = [("Eksport", e), ("Import", i), (f"Standby ({dni}d)", p), (f"Parking ({dni}d)", park)]
    comp_html = "".join([f'<div style="background:rgba(255,255,255,0.05);padding:15px;border-radius:10px;border:1px solid rgba(255,255,255,0.1);display:flex;justify-content:space-between;align-items:center;"><span style="color:#94a3b8;font-size:13px;">{n}</span><span style="color:white;font-weight:bold;">€ {v:,.2f}</span></div>' for n, v in items])

    main_html = f"""
    <div style="font-family:sans-serif; background:radial-gradient(circle at 50% 10%, #1e293b 0%, #030508 100%); padding:40px; border-radius:20px; color:white;">
        <div style="color:#ed8936; font-weight:bold; letter-spacing:2px; font-size:12px; margin-bottom:10px;">ESTIMATED RATE</div>
        <div style="font-size:70px; font-weight:900; margin-bottom:30px;">€ {total:,.2f} <span style="font-size:20px; color:#64748b; font-weight:400;">netto</span></div>
        <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(240px, 1fr)); gap:15px;">{comp_html}</div>
    </div>
    """
    
    # WYMUSZENIE RENDEROWANIA PRZEZ IFRAME (Rozwiązuje problem wyświetlania tekstu)
    st.components.v1.html(main_html, height=400)
else:
    st.error("Brak danych dla wybranej konfiguracji.")
