import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import re
import hashlib
import extra_streamlit_components as stx
import pydeck as pdk

# --- KONFIGURACJA ---
SHEET_ID = "1sYlXP6WVzPE09qfmydQYQNsjiZcDgRSJGyWoXfjmkDY"
URL_BAZA = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=CENNIK_BAZA"
URL_OPLATY = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=OPLATY_STALE"
URL_USERS = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=USERS"

# Współrzędne Komornik (Baza SQM)
KOMORNIKI_COORDS = [16.8122, 52.3358] 

st.set_page_config(page_title="SQM VANTAGE v7", layout="wide", initial_sidebar_state="expanded")

# --- SYSTEM BEZPIECZEŃSTWA ---
def hash_password(password):
    return hashlib.sha256(password.strip().encode()).hexdigest()

cookie_manager = stx.CookieManager()

@st.cache_data(ttl=1)
def fetch_users():
    try:
        df = pd.read_csv(URL_USERS)
        df.columns = df.columns.str.strip()
        return dict(zip(df['username'].astype(str).str.strip(), df['password'].astype(str).str.strip()))
    except:
        return {"admin": "f3e99d9459eeb7ffc4cd407d890fbf1db011208fa12d8edc501a7ec26da106a3"}

user_db = fetch_users()

if "auth" not in st.session_state:
    st.session_state.auth = False

saved = cookie_manager.get(cookie="sqm_v7_session")
if saved in user_db:
    st.session_state.auth = True
    st.session_state.user = saved

# --- LOGOWANIE ---
if not st.session_state.auth:
    st.markdown("""
        <style>
        .stApp { background: #030508; color: white; }
        .login-box {
            max-width: 450px; margin: 100px auto; padding: 40px;
            background: rgba(255, 255, 255, 0.05); border: 1px solid #ed8936;
            border-radius: 20px; text-align: center;
        }
        </style>
    """, unsafe_allow_html=True)
    with st.container():
        st.markdown('<div class="login-box">', unsafe_allow_html=True)
        st.image("https://www.sqm.pl/wp-content/themes/sqm/img/logo-sqm.png", width=200)
        u = st.text_input("Użytkownik").strip()
        p = st.text_input("Hasło", type="password").strip()
        if st.button("ZALOGUJ SIĘ", use_container_width=True):
            if u in user_db and user_db[u] == hash_password(p):
                st.session_state.auth = True
                st.session_state.user = u
                cookie_manager.set("sqm_v7_session", u, expires_at=datetime.now() + timedelta(days=30))
                st.rerun()
            else:
                st.error("Błąd logowania")
        st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

# --- NOWY DESIGN CSS ---
st.markdown("""
    <style>
    /* Agresywny gradient tła */
    .stApp {
        background: radial-gradient(circle at 20% 20%, #1a365d 0%, #030508 100%) !important;
    }
    
    /* Szklane kontenery */
    .glass-card {
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 20px;
        padding: 25px;
        backdrop-filter: blur(15px);
        margin-bottom: 20px;
    }

    .main-price-box {
        background: linear-gradient(135deg, rgba(237, 137, 54, 0.1) 0%, rgba(0,0,0,0) 100%);
        border-left: 10px solid #ed8936;
        padding: 40px;
        border-radius: 0 20px 20px 0;
        margin: 20px 0;
    }

    .price-val {
        font-size: 80px;
        font-weight: 900;
        color: #ffffff;
        text-shadow: 0 10px 20px rgba(0,0,0,0.5);
    }

    /* Tabela kosztów */
    .cost-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 15px;
    }
    .cost-item {
        background: rgba(255,255,255,0.05);
        padding: 15px;
        border-radius: 10px;
        border: 1px solid rgba(255,255,255,0.05);
    }
    </style>
""", unsafe_allow_html=True)

# --- DANE ---
@st.cache_data(ttl=60)
def load_data():
    b = pd.read_csv(URL_BAZA); o = pd.read_csv(URL_OPLATY)
    b.columns = b.columns.str.strip(); o.columns = o.columns.str.strip()
    def cl(v):
        s = re.sub(r'[^\d.]', '', str(v).replace(',', '.'))
        return float(s) if s else 0.0
    for c in ['Eksport', 'Import', 'Postoj', 'lat', 'lon']: 
        if c in b.columns: b[c] = b[c].apply(cl)
    o['Wartosc'] = o['Wartosc'].apply(cl)
    return b, o

df_baza, df_oplaty = load_data()
cfg = dict(zip(df_oplaty['Parametr'], df_oplaty['Wartosc']))

# --- SIDEBAR ---
with st.sidebar:
    st.image("https://www.sqm.pl/wp-content/themes/sqm/img/logo-sqm.png", width=150)
    miasto = st.selectbox("CEL TRANSPORTU", sorted(df_baza['Miasto'].unique()))
    waga = st.number_input("WAGA (kg)", value=500, step=100)
    d1 = st.date_input("START", datetime.now())
    d2 = st.date_input("POWRÓT", datetime.now() + timedelta(days=3))
    dni = max(0, (d2-d1).days)
    if st.button("WYLOGUJ"):
        cookie_manager.delete("sqm_v7_session")
        st.session_state.auth = False
        st.rerun()

# --- LOGIKA ---
w_c = waga * cfg.get('WAGA_BUFOR', 1.2)
v_t = "BUS" if w_c <= 1000 else "SOLO" if w_c <= 5500 else "FTL"
res = df_baza[(df_baza['Miasto'] == miasto) & (df_baza['Typ_Pojazdu'] == v_type if 'v_type' in locals() else v_t)]

if not res.empty:
    row = res.iloc[0]
    e, i, p_day = row['Eksport'], row['Import'], row['Postoj']
    total = e + i + (p_day * dni) + (dni * cfg.get('PARKING_DAY', 30))
    
    # Dodatki (UK/CH)
    if miasto in ["Londyn", "Genewa", "Zurych"]:
        total += cfg.get('ATA_CARNET', 166)

    # --- WIDOK GŁÓWNY ---
    col_main, col_map = st.columns([1.2, 1])

    with col_main:
        st.markdown(f"""
            <div class="main-price-box">
                <div style="color:#ed8936; font-weight:bold; letter-spacing:2px">WYCENA TRANSPORTU / {miasto.upper()}</div>
                <div class="price-val">€ {total:,.2f}</div>
                <div style="opacity:0.6">Pojazd: {v_t} | Waga: {w_c:.0f}kg | Dni: {dni}</div>
            </div>
        """, unsafe_allow_html=True)
        
        st.markdown('<div class="cost-grid">', unsafe_allow_html=True)
        st.markdown(f'<div class="cost-item"><small>Eksport</small><br><b>€ {e:,.2f}</b></div>', unsafe_allow_html=True)
        st.markdown(f'<div class="cost-item"><small>Import</small><br><b>€ {i:,.2f}</b></div>', unsafe_allow_html=True)
        st.markdown(f'<div class="cost-item"><small>Postój</small><br><b>€ {p_day*dni:,.2f}</b></div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with col_map:
        # Wizualizacja trasy na mapie
        target_coords = [row['lon'], row['lat']]
        
        # Tworzenie linii trasy
        route_data = pd.DataFrame([{
            "start": KOMORNIKI_COORDS,
            "end": target_coords,
            "name": f"Komorniki -> {miasto}"
        }])

        st.pydeck_chart(pdk.Deck(
            map_style='mapbox://styles/mapbox/dark-v10',
            initial_view_state=pdk.ViewState(
                latitude=(52.33 + row['lat'])/2,
                longitude=(16.81 + row['lon'])/2,
                zoom=4,
                pitch=45,
            ),
            layers=[
                pdk.Layer(
                    "ArcLayer",
                    data=route_data,
                    get_source_position="start",
                    get_target_position="end",
                    get_source_color=[237, 137, 54, 200],
                    get_target_color=[255, 255, 255, 200],
                    get_width=5,
                ),
                pdk.Layer(
                    "ScatterplotLayer",
                    data=pd.DataFrame([{"pos": KOMORNIKI_COORDS}]),
                    get_position="pos",
                    get_color=[237, 137, 54],
                    get_radius=20000,
                )
            ],
        ))
