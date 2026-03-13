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

# Współrzędne miast (Fallback jeśli brak w arkuszu)
CITY_GEO = {
    "Amsterdam": [4.8952, 52.3702], "Berlin": [13.4050, 52.5200], "Londyn": [-0.1276, 51.5074],
    "Paryż": [2.3522, 48.8566], "Wiedeń": [16.3738, 48.2082], "Praga": [14.4378, 50.0755],
    "Genewa": [6.1432, 46.2044], "Zurych": [8.5417, 47.3769], "Mediolan": [9.1900, 45.4642],
    "Barcelona": [2.1734, 41.3851], "Monachium": [11.5820, 48.1351]
}

st.set_page_config(page_title="SQM VANTAGE v8.0", layout="wide", initial_sidebar_state="expanded")

# --- WYMUSZONE STYLE CSS (TŁO I CZYTELNOŚĆ) ---
st.markdown("""
    <style>
    /* Wymuszenie tła na wszystkich warstwach Streamlit */
    .stApp, .main, .block-container {
        background: radial-gradient(circle at 20% 20%, #1e3a8a 0%, #030508 100%) !important;
        background-attachment: fixed !important;
    }
    
    /* Nakładka z siatką technologiczną */
    .stApp::before {
        content: ""; position: fixed; top: 0; left: 0; width: 100%; height: 100%;
        background-image: linear-gradient(rgba(255,255,255,0.03) 1px, transparent 1px), 
                          linear-gradient(90deg, rgba(255,255,255,0.03) 1px, transparent 1px);
        background-size: 40px 40px; z-index: 0; pointer-events: none;
    }

    /* Szklany kontener ceny */
    .price-card {
        background: rgba(255, 255, 255, 0.03) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-left: 10px solid #ed8936 !important;
        border-radius: 25px;
        padding: 45px !important;
        margin: 25px 0 !important;
        backdrop-filter: blur(20px);
        box-shadow: 0 20px 50px rgba(0,0,0,0.5);
    }

    .big-value {
        font-size: 95px !important;
        font-weight: 900 !important;
        color: #ffffff !important;
        letter-spacing: -3px;
        line-height: 0.8;
        margin: 20px 0;
    }

    .cost-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
        gap: 15px;
        margin-top: 35px;
    }
    
    .cost-pill {
        background: rgba(255,255,255,0.06);
        padding: 15px;
        border-radius: 12px;
        border: 1px solid rgba(255,255,255,0.1);
        text-align: center;
    }

    /* Sidebar Fix */
    section[data-testid="stSidebar"] {
        background-color: rgba(0,0,0,0.4) !important;
        backdrop-filter: blur(10px);
    }
    </style>
""", unsafe_allow_html=True)

# --- FUNKCJE ---
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
        # Rezerwowy admin zgodny z hashem z debugu
        return {"admin": "f3e99d9459eeb7ffc4cd407d890fbf1db011208fa12d8edc501a7ec26da106a3"}

user_db = fetch_users()

if "auth" not in st.session_state:
    st.session_state.auth = False

# Sprawdzenie ciasteczka
saved = cookie_manager.get(cookie="sqm_v8_session")
if saved in user_db:
    st.session_state.auth = True
    st.session_state.user = saved

# --- LOGOWANIE ---
if not st.session_state.auth:
    _, col, _ = st.columns([1,2,1])
    with col:
        st.image("https://www.sqm.pl/wp-content/themes/sqm/img/logo-sqm.png", width=200)
        st.title("SQM VANTAGE LOGIN")
        u_in = st.text_input("Użytkownik").strip()
        p_in = st.text_input("Hasło", type="password").strip()
        
        if st.button("ZALOGUJ", use_container_width=True):
            if u_in in user_db and user_db[u_in] == hash_password(p_in):
                st.session_state.auth = True
                st.session_state.user = u_in
                cookie_manager.set("sqm_v8_session", u_in, expires_at=datetime.now() + timedelta(days=30))
                st.rerun()
            else:
                st.error("Błąd logowania. Sprawdź hasło w arkuszu.")
    st.stop()

# --- ŁADOWANIE DANYCH ---
@st.cache_data(ttl=60)
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

# --- INTERFEJS ---
with st.sidebar:
    st.image("https://www.sqm.pl/wp-content/themes/sqm/img/logo-sqm.png", width=150)
    st.subheader(f"Logistyk: {st.session_state.user}")
    m_dest = st.selectbox("MIASTO DOCELOWE", sorted(df_baza['Miasto'].unique()))
    w_raw = st.number_input("WAGA SPRZĘTU (kg)", value=500, step=100)
    d_start = st.date_input("DATA ZAŁADUNKU", datetime.now())
    d_end = st.date_input("DATA POWROTU", datetime.now() + timedelta(days=2))
    dni_site = max(0, (d_end - d_start).days)
    
    if st.button("WYLOGUJ"):
        cookie_manager.delete("sqm_v8_session")
        st.session_state.auth = False
        st.rerun()

# --- KALKULACJA ---
w_eff = w_raw * cfg.get('WAGA_BUFOR', 1.2)
v_type = "BUS" if w_eff <= 1000 else "SOLO" if w_eff <= 5500 else "FTL"
res = df_baza[(df_baza['Miasto'] == m_dest) & (df_baza['Typ_Pojazdu'] == v_type)]

if not res.empty:
    r = res.iloc[0]
    cost_e = r['Eksport']
    cost_i = r['Import']
    cost_p = r['Postoj'] * dni_site
    cost_park = dni_site * cfg.get('PARKING_DAY', 30)
    
    total = cost_e + cost_i + cost_p + cost_park
    
    # Dodatek UK/CH (Cło/Prom)
    ata = 0
    if m_dest in ["Londyn", "Genewa", "Zurych"]:
        ata = cfg.get('ATA_CARNET', 166)
        total += ata

    # --- WIDOK GŁÓWNY ---
    st.title(f"LOGISTICS VANTAGE / {m_dest.upper()}")
    
    c_main, c_map = st.columns([1.3, 1])
    
    with c_main:
        st.markdown(f"""
            <div class="price-card">
                <div style="color: #ed8936; font-weight: bold; letter-spacing: 2px; text-transform: uppercase;">Rekomendowana Stawka Projektu</div>
                <div class="big-value">€ {total:,.2f}</div>
                <div style="color: #94a3b8; margin-bottom: 20px;">Typ: {v_type} | Waga: {w_eff:.0f} kg | Dni: {dni_site}</div>
                <div class="cost-grid">
                    <div class="cost-pill"><small>Eksport</small><br><b>€ {cost_e:,.2f}</b></div>
                    <div class="cost-pill"><small>Import</small><br><b>€ {cost_i:,.2f}</b></div>
                    <div class="cost-pill"><small>Postój</small><br><b>€ {cost_p:,.2f}</b></div>
                    <div class="cost-pill"><small>Parking</small><br><b>€ {cost_park:,.2f}</b></div>
                </div>
            </div>
        """, unsafe_allow_html=True)

    with c_map:
        # Mapa trasy z Komornik
        target_coords = CITY_GEO.get(m_dest, [13.4, 52.5]) # Berlin jako fallback
        route_df = pd.DataFrame([{"source": KOMORNIKI_COORDS, "target": target_coords}])
        
        st.pydeck_chart(pdk.Deck(
            map_style='mapbox://styles/mapbox/dark-v10',
            initial_view_state=pdk.ViewState(
                latitude=(KOMORNIKI_COORDS[1] + target_coords[1]) / 2,
                longitude=(KOMORNIKI_COORDS[0] + target_coords[0]) / 2,
                zoom=4, pitch=45
            ),
            layers=[
                pdk.Layer(
                    "ArcLayer", data=route_df, get_source_position="source", get_target_position="target",
                    get_source_color=[237, 137, 54, 255], get_target_color=[255, 255, 255, 150], get_width=6
                ),
                pdk.Layer(
                    "ScatterplotLayer", data=pd.DataFrame([{"p": KOMORNIKI_COORDS}]),
                    get_position="p", get_color=[237, 137, 54], get_radius=30000
                )
            ]
        ))
else:
    st.error(f"Brak danych dla {m_dest} ({v_type})")

st.markdown("<br><p style='text-align:right; opacity: 0.3;'>SQM Multimedia Solutions | 2026</p>", unsafe_allow_html=True)
