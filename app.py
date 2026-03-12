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

# --- ZARZĄDZANIE SESJĄ (COOKIES) ---
def get_manager():
    return stx.CookieManager()

cookie_manager = get_manager()

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

@st.cache_data(ttl=600)
def fetch_users():
    try:
        df = pd.read_csv(URL_USERS)
        return dict(zip(df['username'].astype(str), df['password'].astype(str)))
    except:
        return {"admin": "5f4dcc3b5aa765d61d8327deb882cf99"} # hasło: password

user_db = fetch_users()
saved_user = cookie_manager.get(cookie="sqm_vantage_session")

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if saved_user in user_db:
    st.session_state.authenticated = True
    st.session_state.user = saved_user

# --- EKRAN LOGOWANIA ---
if not st.session_state.authenticated:
    st.markdown("<style>.stApp {background: #0f172a; color: white;}</style>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1,2,1])
    with c2:
        st.image("https://www.sqm.pl/wp-content/themes/sqm/img/logo-sqm.png", width=200)
        st.title("Logowanie SQM VANTAGE")
        u = st.text_input("Użytkownik")
        p = st.text_input("Hasło", type="password")
        if st.button("ZALOGUJ"):
            if u in user_db and user_db[u] == hash_password(p):
                st.session_state.authenticated = True
                st.session_state.user = u
                cookie_manager.set("sqm_vantage_session", u, expires_at=datetime.now() + timedelta(days=30))
                st.rerun()
            else:
                st.error("Nieprawidłowe dane logowania.")
    st.stop()

# --- CUSTOM CSS ---
st.markdown("""
    <style>
    .stApp { background: radial-gradient(circle at 50% 10%, #1e293b 0%, #030508 100%); color: #e2e8f0; }
    .price-container { background: rgba(255, 255, 255, 0.04); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 30px; padding: 40px; backdrop-filter: blur(25px); margin-top: 20px; position: relative; }
    .price-container::after { content: ""; position: absolute; top: 40px; left: 0; width: 5px; height: 80px; background: #ed8936; border-radius: 0 5px 5px 0; }
    .price-label { font-size: 0.9rem; color: #ed8936; font-weight: 700; text-transform: uppercase; letter-spacing: 2px; }
    .price-value { font-size: 5.5rem; font-weight: 900; color: #ffffff; line-height: 1; margin: 15px 0; letter-spacing: -2px; }
    .components-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 12px; margin-top: 30px; }
    .component-item { background: rgba(255, 255, 255, 0.03); border: 1px solid rgba(255, 255, 255, 0.05); padding: 14px 18px; border-radius: 12px; display: flex; justify-content: space-between; align-items: center; }
    .comp-name { font-size: 0.8rem; color: #94a3b8; }
    .comp-price { font-size: 1rem; font-weight: 700; color: #f8fafc; }
    </style>
""", unsafe_allow_html=True)

# --- DANE I LOGIKA ---
@st.cache_data(ttl=300)
def fetch_data():
    try:
        b = pd.read_csv(URL_BAZA); o = pd.read_csv(URL_OPLATY)
        b.columns = b.columns.str.strip(); o.columns = o.columns.str.strip()
        def cln(v):
            if pd.isna(v): return 0.0
            s = re.sub(r'[^\d.]', '', str(v).replace(',', '.'))
            return float(s) if s else 0.0
        for c in ['Eksport', 'Import', 'Postoj']:
            if c in b.columns: b[c] = b[c].apply(cln)
        o['Wartosc'] = o['Wartosc'].apply(cln)
        return b, o
    except: return None, None

df_baza, df_oplaty = fetch_data()

if df_baza is not None:
    cfg = dict(zip(df_oplaty['Parametr'], df_oplaty['Wartosc']))
    with st.sidebar:
        st.image("https://www.sqm.pl/wp-content/themes/sqm/img/logo-sqm.png", width=150)
        st.write(f"Zalogowany: **{st.session_state.user}**")
        miasto = st.selectbox("CEL", sorted(df_baza['Miasto'].unique()))
        waga = st.number_input("WAGA SPRZĘTU (kg)", value=500, step=100)
        data_z = st.date_input("ZAŁADUNEK", datetime.now())
        data_p = st.date_input("POWRÓT", datetime.now() + timedelta(days=3))
        dni = max(0, (data_p - data_z).days)
        if st.button("WYLOGUJ"):
            cookie_manager.delete("sqm_vantage_session")
            st.session_state.authenticated = False
            st.rerun()

    w_total = waga * cfg.get('WAGA_BUFOR', 1.2)
    v_type = "BUS" if w_total <= 1000 else "SOLO" if w_total <= 5500 else "FTL"
    res = df_baza[(df_baza['Miasto'] == miasto) & (df_baza['Typ_Pojazdu'] == v_type)]

    if not res.empty:
        e, i = res['Eksport'].mean(), res['Import'].mean()
        p = res['Postoj'].mean() * dni
        park = dni * cfg.get('PARKING_DAY', 30)
        
        ata, ferry = 0, 0
        if miasto in ["Londyn", "Liverpool", "Manchester", "Bazylea", "Genewa", "Zurych"]:
            ata = cfg.get('ATA_CARNET', 166)
            if "Londyn" in miasto or "Liverpool" in miasto or "Manchester" in miasto:
                ferry = cfg.get('FERRY_BUS', 332) if v_type == "BUS" else cfg.get('FERRY_FTL_SOLO', 522)
        
        total = e + i + p + park + ata + ferry

        items = [("Eksport", e), ("Import", i), (f"Standby ({dni}d)", p), (f"Parking ({dni}d)", park)]
        if ata > 0: items.append(("Karnet ATA", ata))
