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

# Baza SQM Komorniki
START_COORDS = [16.8122, 52.3358] 

# Słownik współrzędnych (na wypadek braku w Excelu)
CITY_COORDS = {
    "Amsterdam": [4.8952, 52.3702], "Berlin": [13.4050, 52.5200], "Londyn": [-0.1276, 51.5074],
    "Paryż": [2.3522, 48.8566], "Wiedeń": [16.3738, 48.2082], "Praga": [14.4378, 50.0755],
    "Genewa": [6.1432, 46.2044], "Zurych": [8.5417, 47.3769], "Mediolan": [9.1900, 45.4642]
}

st.set_page_config(page_title="SQM VANTAGE | Logistics", layout="wide")

# --- CSS: WYMUSZENIE WYGLĄDU ---
st.markdown("""
    <style>
    /* Agresywne tło z teksturą */
    .stApp {
        background: radial-gradient(circle at 30% 30%, #1a365d 0%, #02040a 100%) !important;
        background-attachment: fixed;
    }
    .stApp::before {
        content: ""; position: fixed; top: 0; left: 0; width: 100%; height: 100%;
        background-image: radial-gradient(rgba(255,255,255,0.05) 1px, transparent 1px);
        background-size: 30px 30px; z-index: -1;
    }

    /* Kontener wyceny */
    .main-price-card {
        background: rgba(255, 255, 255, 0.03) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-left: 8px solid #ed8936 !important;
        border-radius: 20px;
        padding: 40px;
        margin: 20px 0;
        backdrop-filter: blur(20px);
    }

    .price-big {
        font-size: 90px !important;
        font-weight: 900 !important;
        color: white !important;
        line-height: 1;
        margin: 10px 0;
    }

    .grid-costs {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
        gap: 15px;
        margin-top: 30px;
    }
    .cost-box {
        background: rgba(255,255,255,0.05);
        padding: 15px;
        border-radius: 12px;
        border: 1px solid rgba(255,255,255,0.05);
    }
    </style>
""", unsafe_allow_html=True)

# --- LOGIKA SYSTEMOWA ---
def hash_password(p): return hashlib.sha256(p.strip().encode()).hexdigest()
cookie_manager = stx.CookieManager()

@st.cache_data(ttl=1)
def fetch_users():
    try:
        df = pd.read_csv(URL_USERS)
        df.columns = df.columns.str.strip()
        return dict(zip(df['username'].astype(str), df['password'].astype(str)))
    except: return {"admin": "f3e99d9459eeb7ffc4cd407d890fbf1db011208fa12d8edc501a7ec26da106a3"}

user_db = fetch_users()

if "auth" not in st.session_state: st.session_state.auth = False
saved = cookie_manager.get(cookie="sqm_v75_session")
if saved in user_db:
    st.session_state.auth = True
    st.session_state.user = saved

if not st.session_state.auth:
    # (Ekran logowania - pominięty dla zwięzłości, taki sam jak wcześniej)
    st.title("Logowanie SQM VANTAGE")
    u = st.text_input("Użytkownik")
    p = st.text_input("Hasło", type="password")
    if st.button("Zaloguj"):
        if u in user_db and user_db[u] == hash_password(p):
            st.session_state.auth = True
            st.session_state.user = u
            cookie_manager.set("sqm_v75_session", u, expires_at=datetime.now()+timedelta(days=30))
            st.rerun()
    st.stop()

# --- DANE I KALKULACJA ---
@st.cache_data(ttl=60)
def load_data():
    b = pd.read_csv(URL_BAZA); o = pd.read_csv(URL_OPLATY)
    b.columns = b.columns.str.strip(); o.columns = o.columns.str.strip()
    def cl(v):
        s = re.sub(r'[^\d.]', '', str(v).replace(',', '.'))
        return float(s) if s else 0.0
    for c in ['Eksport', 'Import', 'Postoj']: b[c] = b[c].apply(cl)
    o['Wartosc'] = o['Wartosc'].apply(cl)
    return b, o

df_baza, df_oplaty = load_data()
cfg = dict(zip(df_oplaty['Parametr'], df_oplaty['Wartosc']))

# SIDEBAR
with st.sidebar:
    st.image("https://www.sqm.pl/wp-content/themes/sqm/img/logo-sqm.png", width=150)
    miasto = st.selectbox("CEL", sorted(df_baza['Miasto'].unique()))
    waga = st.number_input("WAGA (kg)", value=500)
    d1 = st.date_input("ZAŁADUNEK", datetime.now())
    d2 = st.date_input("POWRÓT", datetime.now() + timedelta(days=2))
    dni = max(0, (d2-d1).days)

# WYLICZENIA
w_c = waga * cfg.get('WAGA_BUFOR', 1.2)
v_t = "BUS" if w_c <= 1000 else "SOLO" if w_c <= 5500 else "FTL"
res = df_baza[(df_baza['Miasto'] == miasto) & (df_baza['Typ_Pojazdu'] == v_t)]

if not res.empty:
    r = res.iloc[0]
    total = r['Eksport'] + r['Import'] + (r['Postoj'] * dni) + (dni * cfg.get('PARKING_DAY', 30))
    
    # --- WIDOK ---
    col1, col2 = st.columns([1.5, 1])
    
    with col1:
        st.markdown(f"""
            <div class="main-price-card">
                <div style="color:#ed8936; letter-spacing:2px; font-weight:bold;">LOGISTICS VANTAGE / {miasto.upper()}</div>
                <div class="price-big">€ {total:,.2f}</div>
                <div class="grid-costs">
                    <div class="cost-box"><small>Eksport</small><br><b>€ {r['Eksport']:,.2f}</b></div>
                    <div class="cost-box"><small>Import</small><br><b>€ {r['Import']:,.2f}</b></div>
                    <div class="cost-box"><small>Postój ({dni}d)</small><br><b>€ {r['Postoj']*dni:,.2f}</b></div>
                    <div class="cost-box"><small>Pojazd</small><br><b>{v_t}</b></div>
                </div>
            </div>
        """, unsafe_allow_html=True)

    with col2:
        # MAPA
        end_coords = CITY_COORDS.get(miasto, [13.40, 52.52]) # Domyślnie Berlin jeśli nie ma w słowniku
        route_df = pd.DataFrame([{"start": START_COORDS, "end": end_coords}])
        
        st.pydeck_chart(pdk.Deck(
            map_style='mapbox://styles/mapbox/dark-v10',
            initial_view_state=pdk.ViewState(
                latitude=(START_COORDS[1] + end_coords[1])/2,
                longitude=(START_COORDS[0] + end_coords[0])/2,
                zoom=4, pitch=40
            ),
            layers=[
                pdk.Layer("ArcLayer", data=route_df, get_source_position="start", 
                          get_target_position="end", get_source_color=[237, 137, 54], 
                          get_target_color=[255, 255, 255], get_width=5),
                pdk.Layer("ScatterplotLayer", data=pd.DataFrame([{"p": START_COORDS}]), 
                          get_position="p", get_color=[237, 137, 54], get_radius=30000)
            ]
        ))
