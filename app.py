import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import re
import hashlib
import extra_streamlit_components as stx
import pydeck as pdk

# --- KONFIGURACJA ARKUSZA ---
SHEET_ID = "1sYlXP6WVzPE09qfmydQYQNsjiZcDgRSJGyWoXfjmkDY"
URL_BAZA = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=CENNIK_BAZA"
URL_OPLATY = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=OPLATY_STALE"
URL_USERS = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=USERS"

# Baza SQM Komorniki
START_COORDS = [16.8122, 52.3358] 

# Koordynaty fallback (dla mapy)
CITY_GEO = {
    "Amsterdam": [4.8952, 52.3702], "Berlin": [13.4050, 52.5200], "Londyn": [-0.1276, 51.5074],
    "Paryż": [2.3522, 48.8566], "Wiedeń": [16.3738, 48.2082], "Praga": [14.4378, 50.0755],
    "Genewa": [6.1432, 46.2044], "Zurych": [8.5417, 47.3769], "Barcelona": [2.1734, 41.3851],
    "Monachium": [11.5820, 48.1351], "Mediolan": [9.1900, 45.4642]
}

st.set_page_config(page_title="SQM VANTAGE v12", layout="wide")

# --- CSS: WYMUSZENIE NOWEGO WYGLĄDU ---
st.markdown("""
    <style>
    /* Wymuszenie tła i usunięcie starych stylów */
    .stApp {
        background: #0e1117 !important;
        background-image: radial-gradient(circle at 20% 20%, #1e3a8a 0%, #030508 100%) !important;
    }
    
    /* Nowy styl karty wyceny (wyraźnie inny niż na Twoim zdjęciu) */
    .v12-price-container {
        background: rgba(0, 0, 0, 0.85) !important;
        border: 3px solid #ed8936 !important;
        border-radius: 25px;
        padding: 40px !important;
        margin-top: 20px;
        box-shadow: 0 0 40px rgba(0,0,0,0.9);
    }

    .v12-header {
        color: #ed8936;
        text-transform: uppercase;
        font-weight: 900;
        letter-spacing: 4px;
        font-size: 1.1rem;
    }

    .v12-main-price {
        font-size: 100px !important;
        font-weight: 900 !important;
        color: #ffffff !important;
        margin: 15px 0;
        line-height: 1;
    }

    .v12-grid {
        display: grid;
        grid-template-columns: repeat(2, 1fr);
        gap: 20px;
        margin-top: 30px;
    }

    .v12-item {
        border-bottom: 1px solid rgba(255,255,255,0.1);
        padding-bottom: 10px;
    }

    .v12-item-label { color: #94a3b8; font-size: 0.8rem; text-transform: uppercase; }
    .v12-item-val { color: #f8fafc; font-size: 1.3rem; font-weight: 700; }
    </style>
""", unsafe_allow_html=True)

# --- AUTH ---
def hash_val(p): return hashlib.sha256(p.strip().encode()).hexdigest()
cookie_manager = stx.CookieManager()

@st.cache_data(ttl=5)
def load_u():
    try:
        df = pd.read_csv(URL_USERS)
        df.columns = df.columns.str.strip()
        return dict(zip(df['username'].astype(str), df['password'].astype(str)))
    except: return {"admin": "f3e99d9459eeb7ffc4cd407d890fbf1db011208fa12d8edc501a7ec26da106a3"}

user_db = load_u()
if "auth" not in st.session_state: st.session_state.auth = False

# Token v12 wymusi ponowne logowanie
session_token = cookie_manager.get(cookie="sqm_v12_session")
if session_token in user_db:
    st.session_state.auth = True
    st.session_state.user = session_token

if not st.session_state.auth:
    _, c, _ = st.columns([1,1.5,1])
    with c:
        st.markdown("<h1 style='color:white; text-align:center;'>SQM VANTAGE v12</h1>", unsafe_allow_html=True)
        u_in = st.text_input("User").strip()
        p_in = st.text_input("Pass", type="password").strip()
        if st.button("LOGIN", use_container_width=True):
            if u_in in user_db and user_db[u_in] == hash_val(p_in):
                st.session_state.auth = True
                st.session_state.user = u_in
                cookie_manager.set("sqm_v12_session", u_in, expires_at=datetime.now()+timedelta(days=30))
                st.rerun()
            else: st.error("Invalid credentials.")
    st.stop()

# --- DATA ---
@st.cache_data(ttl=30)
def get_data():
    b = pd.read_csv(URL_BAZA); o = pd.read_csv(URL_OPLATY)
    b.columns = b.columns.str.strip()
    def cl(v):
        s = re.sub(r'[^\d.]', '', str(v).replace(',', '.'))
        return float(s) if s else 0.0
    for c in ['Eksport', 'Import', 'Postoj']: b[c] = b[c].apply(cl)
    o['Wartosc'] = o['Wartosc'].apply(cl)
    return b, o

df_baza, df_oplaty = get_data()
cfg = dict(zip(df_oplaty['Parametr'], df_oplaty['Wartosc']))

# --- SIDEBAR ---
with st.sidebar:
    st.image("https://www.sqm.pl/wp-content/themes/sqm/img/logo-sqm.png", width=150)
    st.markdown(f"User: **{st.session_state.user}**")
    
    # Wybór trybu (Dedyk vs Doładunek)
    strat = st.radio("STRATEGIA", ["DEDYKOWANY (Pełne auto)", "DOŁADUNEK (z wagi)"])
    
    dest = st.selectbox("CEL", sorted(df_baza['Miasto'].unique()))
    kg = st.number_input("WAGA (kg)", value=500, step=50)
    d1 = st.date_input("ZAŁADUNEK", datetime.now())
    d2 = st.date_input("POWRÓT", datetime.now() + timedelta(days=2))
    dni = max(0, (d2-d1).days)
    
    if st.button("LOGOUT"):
        cookie_manager.delete("sqm_v12_session")
        st.session_state.auth = False
        st.rerun()

# --- KALKULACJA ---
w_eff = kg * cfg.get('WAGA_BUFOR', 1.2)
v_type = "BUS" if w_eff <= 1200 else "SOLO" if w_eff <= 5500 else "FTL"
res = df_baza[(df_baza['Miasto'] == dest) & (df_baza['Typ_Pojazdu'] == v_type)]

if not res.empty:
    r = res.iloc[0]
    
    if "DEDYKOWANY" in strat:
        exp, imp = r['Eksport'], r['Import']
    else:
        exp, imp = r['Eksport'] * w_eff, r['Import'] * w_eff

    postoj = r['Postoj'] * dni
    oplaty = (dni * cfg.get('PARKING_DAY', 30)) + (cfg.get('ATA_CARNET', 166) if dest in ["Londyn", "Genewa", "Zurych"] else 0)
    total = exp + imp + postoj + oplaty

    # --- UI GŁÓWNE ---
    st.title(f"{dest.upper()} // LOGISTICS ANALYSIS")
    
    c_price, c_map = st.columns([1.3, 1])
    
    with c_price:
        st.markdown(f"""
            <div class="v12-price-container">
                <div class="v12-header">Estymacja Kosztów ({strat})</div>
                <div class="v12-main-price">€ {total:,.2f}</div>
                <div class="v12-grid">
                    <div class="v12-item"><div class="v12-item-label">Eksport</div><div class="v12-item-val">€ {exp:,.2f}</div></div>
                    <div class="v12-item"><div class="v12-item-label">Import</div><div class="v12-item-val">€ {imp:,.2f}</div></div>
                    <div class="v12-item"><div class="v12-item-label">Pojazd</div><div class="v12-item-val">{v_type}</div></div>
                    <div class="v12-item"><div class="v12-item-label">Dni postoju</div><div class="v12-item-val">{dni} d</div></div>
                    <div class="v12-item"><div class="v12-item-label">Postój koszt</div><div class="v12-item-val">€ {postoj:,.2f}</div></div>
                    <div class="v12-item"><div class="v12-item-label">Dodatki</div><div class="v12-item-val">€ {oplaty:,.2f}</div></div>
                </div>
            </div>
        """, unsafe_allow_html=True)

    with c_map:
        # MAPA (wymaga pydeck w requirements.txt)
        target_pos = CITY_GEO.get(dest, [13.4, 52.5])
        st.pydeck_chart(pdk.Deck(
            map_style='mapbox://styles/mapbox/dark-v10',
            initial_view_state=pdk.ViewState(
                latitude=(START_COORDS[1] + target_pos[1])/2,
                longitude=(START_COORDS[0] + target_pos[0])/2,
                zoom=4, pitch=45
            ),
            layers=[
                pdk.Layer("ArcLayer", data=pd.DataFrame([{"s": START_COORDS, "t": target_pos}]),
                          get_source_position="s", get_target_position="t",
                          get_source_color=[237, 137, 54], get_target_color=[255, 255, 255], get_width=5)
            ]
        ))
else:
    st.error(f"Brak stawek dla {dest} / {v_type}")
