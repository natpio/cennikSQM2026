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

# Współrzędne (Uzupełnij w Excelu lub tu dla lepszej mapy)
CITY_GEO = {
    "Amsterdam": [4.8952, 52.3702], "Berlin": [13.4050, 52.5200], "Londyn": [-0.1276, 51.5074],
    "Paryż": [2.3522, 48.8566], "Wiedeń": [16.3738, 48.2082], "Praga": [14.4378, 50.0755],
    "Genewa": [6.1432, 46.2044], "Zurych": [8.5417, 47.3769], "Barcelona": [2.1734, 41.3851]
}

st.set_page_config(page_title="SQM VANTAGE v10", layout="wide")

# --- CSS: MAKSYMALNA CZYTELNOŚĆ ---
st.markdown("""
    <style>
    .stApp {
        background: radial-gradient(circle at 20% 20%, #1e3a8a 0%, #030508 100%) !important;
    }
    /* Półprzezroczysta maska na całe tło dla czytelności */
    .stApp::after {
        content: ""; position: fixed; top: 0; left: 0; width: 100%; height: 100%;
        background: rgba(0,0,0,0.3); z-index: -2;
    }

    .main-card {
        background: rgba(0, 0, 0, 0.7) !important;
        border: 1px solid rgba(255, 255, 255, 0.15) !important;
        border-radius: 20px;
        padding: 40px !important;
        box-shadow: 0 15px 35px rgba(0,0,0,0.8);
    }

    .stat-val { font-size: 85px !important; font-weight: 900 !important; color: #ffffff !important; line-height: 1; }
    .orange-tag { color: #ed8936; font-weight: bold; text-transform: uppercase; letter-spacing: 2px; font-size: 0.85rem; }
    
    .grid-4 {
        display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
        gap: 15px; margin-top: 30px;
    }
    .grid-item {
        background: rgba(255,255,255,0.05); padding: 15px; border-radius: 10px;
        border: 1px solid rgba(255,255,255,0.1);
    }
    
    /* Naprawa widoczności mapy */
    .deckgl-container { border-radius: 20px; overflow: hidden; border: 1px solid rgba(255,255,255,0.1); }
    </style>
""", unsafe_allow_html=True)

# --- AUTH ---
def hash_me(p): return hashlib.sha256(p.strip().encode()).hexdigest()
cookie_manager = stx.CookieManager()

@st.cache_data(ttl=5)
def load_users():
    try:
        df = pd.read_csv(URL_USERS)
        df.columns = df.columns.str.strip()
        return dict(zip(df['username'].astype(str), df['password'].astype(str)))
    except: return {"admin": "f3e99d9459eeb7ffc4cd407d890fbf1db011208fa12d8edc501a7ec26da106a3"}

user_db = load_users()
if "auth" not in st.session_state: st.session_state.auth = False
saved = cookie_manager.get(cookie="sqm_v10_token")
if saved in user_db:
    st.session_state.auth = True
    st.session_state.user = saved

if not st.session_state.auth:
    _, c, _ = st.columns([1,1.5,1])
    with c:
        st.image("https://www.sqm.pl/wp-content/themes/sqm/img/logo-sqm.png", width=200)
        u = st.text_input("Logistyk")
        p = st.text_input("Hasło", type="password")
        if st.button("WEJDŹ DO SYSTEMU", use_container_width=True):
            if u in user_db and user_db[u] == hash_me(p):
                st.session_state.auth = True
                st.session_state.user = u
                cookie_manager.set("sqm_v10_token", u, expires_at=datetime.now()+timedelta(days=30))
                st.rerun()
    st.stop()

# --- DATA LOAD ---
@st.cache_data(ttl=60)
def fetch_log_data():
    b = pd.read_csv(URL_BAZA); o = pd.read_csv(URL_OPLATY)
    b.columns = b.columns.str.strip()
    def clean(v):
        s = re.sub(r'[^\d.]', '', str(v).replace(',', '.'))
        return float(s) if s else 0.0
    for c in ['Eksport', 'Import', 'Postoj']: b[c] = b[c].apply(clean)
    o['Wartosc'] = o['Wartosc'].apply(clean)
    return b, o

df_baza, df_oplaty = fetch_log_data()
cfg = dict(zip(df_oplaty['Parametr'], df_oplaty['Wartosc']))

# --- SIDEBAR ---
with st.sidebar:
    st.image("https://www.sqm.pl/wp-content/themes/sqm/img/logo-sqm.png", width=150)
    st.markdown(f"Operator: **{st.session_state.user}**")
    
    # KLUCZOWA ZMIANA: WYBÓR TRYBU
    mode = st.radio("STRATEGIA WYCENY", ["DEDYKOWANY (Pełne auto)", "DOŁADUNEK (Z kilograma)"])
    
    dest = st.selectbox("MIASTO", sorted(df_baza['Miasto'].unique()))
    weight = st.number_input("WAGA SPRZĘTU (kg)", value=500, step=50)
    d1 = st.date_input("START", datetime.now())
    d2 = st.date_input("KONIEC", datetime.now() + timedelta(days=2))
    dni = max(0, (d2-d1).days)
    
    if st.button("WYLOGUJ"):
        cookie_manager.delete("sqm_v10_token")
        st.session_state.auth = False
        st.rerun()

# --- LOGIKA BIZNESOWA ---
w_total = weight * cfg.get('WAGA_BUFOR', 1.2)
v_type = "BUS" if w_total <= 1200 else "SOLO" if w_total <= 5500 else "FTL"

res = df_baza[(df_baza['Miasto'] == dest) & (df_baza['Typ_Pojazdu'] == v_type)]

if not res.empty:
    r = res.iloc[0]
    
    if "DEDYKOWANY" in mode:
        # Płacimy za całe auto (stawka ryczałtowa)
        exp = r['Eksport']
        imp = r['Import']
        label_mode = "Dedykowany"
    else:
        # Płacimy za kilogramy (doładunek)
        exp = r['Eksport'] * w_total
        imp = r['Import'] * w_total
        label_mode = "Doładunek"

    standby = r['Postoj'] * dni
    parking = dni * cfg.get('PARKING_DAY', 30)
    grand = exp + imp + standby + parking
    
    # Dodatki celne
    ata = cfg.get('ATA_CARNET', 166) if dest in ["Londyn", "Genewa", "Zurych"] else 0
    grand += ata

    # --- RENDEROWANIE ---
    st.title(f"VANTAGE LOGISTICS / {dest.upper()}")
    
    col_ui, col_map = st.columns([1.5, 1])
    
    with col_ui:
        st.markdown(f"""
            <div class="main-card">
                <div class="orange-tag">Sugerowany Budżet ({label_mode})</div>
                <div class="stat-val">€ {grand:,.2f}</div>
                <div style="color:#94a3b8; margin-top:10px;">
                    Transport {v_type} | Realna waga: {weight}kg | Wycena operacyjna: {w_total:.0f}kg
                </div>
                
                <div class="grid-4">
                    <div class="grid-item"><small>EKSPORT</small><br><b>€ {exp:,.2f}</b></div>
                    <div class="grid-item"><small>IMPORT</small><br><b>€ {imp:,.2f}</b></div>
                    <div class="grid-item"><small>POSTÓJ ({dni}d)</small><br><b>€ {standby:,.2f}</b></div>
                    <div class="grid-item"><small>DODATKI</small><br><b>€ {parking+ata:,.2f}</b></div>
                </div>
            </div>
        """, unsafe_allow_html=True)

    with col_map:
        target = CITY_GEO.get(dest, [13.4, 52.5])
        st.pydeck_chart(pdk.Deck(
            map_style='mapbox://styles/mapbox/dark-v10',
            initial_view_state=pdk.ViewState(
                latitude=(START_COORDS[1] + target[1])/2,
                longitude=(START_COORDS[0] + target[0])/2,
                zoom=4, pitch=45
            ),
            layers=[
                pdk.Layer("ArcLayer", data=pd.DataFrame([{"s": START_COORDS, "t": target}]),
                          get_source_position="s", get_target_position="t",
                          get_source_color=[237, 137, 54], get_target_color=[255, 255, 255], get_width=6),
                pdk.Layer("ScatterplotLayer", data=pd.DataFrame([{"p": START_COORDS}]),
                          get_position="p", get_color=[237, 137, 54], get_radius=50000)
            ]
        ))
else:
    st.error(f"Brak stawek w bazie dla: {dest} / {v_type}")

st.markdown("<p style='text-align:center; opacity:0.2; margin-top:50px;'>SQM Multimedia Solutions Logistics | 2026</p>", unsafe_allow_html=True)
