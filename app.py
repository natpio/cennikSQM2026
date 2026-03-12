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

# --- BEZPIECZEŃSTWO ---
def hash_password(password):
    return hashlib.sha256(password.strip().encode()).hexdigest()

cookie_manager = stx.CookieManager()

@st.cache_data(ttl=1)
def fetch_users():
    try:
        df = pd.read_csv(URL_USERS)
        df.columns = df.columns.str.strip()
        df['username'] = df['username'].astype(str).str.strip()
        df['password'] = df['password'].astype(str).str.strip()
        return dict(zip(df['username'], df['password']))
    except:
        return {"admin": "f3e99d9459eeb7ffc4cd407d890fbf1db011208fa12d8edc501a7ec26da106a3"}

user_db = fetch_users()

if "auth" not in st.session_state:
    st.session_state.auth = False

# Sprawdzenie sesji
saved = cookie_manager.get(cookie="sqm_v6_session")
if saved in user_db:
    st.session_state.auth = True
    st.session_state.user = saved

# --- LOGOWANIE ---
if not st.session_state.auth:
    st.markdown("<style>.stApp {background: #030508; color: white;}</style>", unsafe_allow_html=True)
    _, col, _ = st.columns([1,2,1])
    with col:
        st.image("https://www.sqm.pl/wp-content/themes/sqm/img/logo-sqm.png", width=200)
        st.title("SQM VANTAGE LOGIN")
        u_in = st.text_input("Użytkownik").strip()
        p_in = st.text_input("Hasło", type="password").strip()
        
        if st.button("ZALOGUJ", use_container_width=True):
            h_in = hash_password(p_in)
            if u_in in user_db and user_db[u_in] == h_in:
                st.session_state.auth = True
                st.session_state.user = u_in
                cookie_manager.set("sqm_v6_session", u_in, expires_at=datetime.now() + timedelta(days=30))
                st.rerun()
            else:
                st.error("Błąd logowania.")
                with st.expander("Debug systemu"):
                    st.write(f"Wpisany login: '{u_in}'")
                    st.write(f"Hash wpisanego hasła: {h_in}")
                    st.write(f"Dostępne loginy: {list(user_db.keys())}")
    st.stop()

# --- GŁÓWNA APLIKACJA ---
@st.cache_data(ttl=300)
def load_data():
    b = pd.read_csv(URL_BAZA); o = pd.read_csv(URL_OPLATY)
    b.columns = b.columns.str.strip()
    def cl(v):
        s = re.sub(r'[^\d.]', '', str(v).replace(',', '.'))
        return float(s) if s else 0.0
    for c in ['Eksport', 'Import', 'Postoj']: b[c] = b[c].apply(cl)
    o['Wartosc'] = o['Wartosc'].apply(cl)
    return b, o

df_baza, df_oplaty = load_data()
cfg = dict(zip(df_oplaty['Parametr'], df_oplaty['Wartosc']))

# Sidebar
with st.sidebar:
    st.image("https://www.sqm.pl/wp-content/themes/sqm/img/logo-sqm.png", width=150)
    st.subheader(f"User: {st.session_state.user}")
    m = st.selectbox("DESTINATION", sorted(df_baza['Miasto'].unique()))
    w = st.number_input("MAIN PROJECT WEIGHT (kg)", value=500)
    d1 = st.date_input("LOADING DATE", datetime.now())
    d2 = st.date_input("RETURN DATE", datetime.now() + timedelta(days=2))
    dni = max(0, (d2-d1).days)
    if st.button("LOGOUT"):
        cookie_manager.delete("sqm_v6_session")
        st.session_state.auth = False
        st.rerun()

# Kalkulacja
w_b = w * cfg.get('WAGA_BUFOR', 1.2)
v_t = "BUS" if w_b <= 1000 else "SOLO" if w_b <= 5500 else "FTL"
row = df_baza[(df_baza['Miasto'] == m) & (df_baza['Typ_Pojazdu'] == v_t)]

if not row.empty:
    e, i = row['Eksport'].mean(), row['Import'].mean()
    p = row['Postoj'].mean() * dni
    park = dni * cfg.get('PARKING_DAY', 30)
    total = e + i + p + park

    # NAGŁÓWEK RAPORTU
    st.title(f"LOGISTICS VANTAGE / {m.upper()}")
    
    # KAFELKI GÓRNE
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("PROJECT WEIGHT (+20%)", f"{w_b:.0f} kg")
    c2.metric("SELECTED VEHICLE", v_t)
    c3.metric("DAYS ON SITE", dni)
    c4.metric("CUSTOMS REQUIRED", "YES" if m in ["Londyn", "Genewa"] else "NO")

    # GŁÓWNA CENA I SKŁADOWE (NAPRAWIONE RENDEROWANIE)
    st.markdown(f"""
    <div style="background: #1e293b; padding: 40px; border-radius: 20px; border-left: 10px solid #ed8936; margin-top: 20px;">
        <div style="color: #ed8936; font-weight: bold; letter-spacing: 2px;">RECOMMENDED PROJECT RATE (NETTO)</div>
        <div style="font-size: 70px; font-weight: 900; color: white; margin: 10px 0;">€ {total:,.2f}</div>
        
        <div style="margin-top: 30px; border-top: 10px solid rgba(255,255,255,0.1); padding-top: 20px;">
            <div style="color: #64748b; font-size: 14px; text-transform: uppercase; margin-bottom: 15px;">Price Breakdown:</div>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 10px;">
                <div style="background: rgba(255,255,255,0.05); padding: 15px; border-radius: 10px; display: flex; justify-content: space-between;">
                    <span style="color: #94a3b8;">Eksport</span><span style="color: white; font-weight: bold;">€ {e:,.2f}</span>
                </div>
                <div style="background: rgba(255,255,255,0.05); padding: 15px; border-radius: 10px; display: flex; justify-content: space-between;">
                    <span style="color: #94a3b8;">Import</span><span style="color: white; font-weight: bold;">€ {i:,.2f}</span>
                </div>
                <div style="background: rgba(255,255,255,0.05); padding: 15px; border-radius: 10px; display: flex; justify-content: space-between;">
                    <span style="color: #94a3b8;">Postój</span><span style="color: white; font-weight: bold;">€ {p:,.2f}</span>
                </div>
                <div style="background: rgba(255,255,255,0.05); padding: 15px; border-radius: 10px; display: flex; justify-content: space-between;">
                    <span style="color: #94a3b8;">Parking</span><span style="color: white; font-weight: bold;">€ {park:,.2f}</span>
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
else:
    st.warning("No data for this destination.")
