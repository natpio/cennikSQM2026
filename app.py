import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import re
import hashlib
import extra_streamlit_components as stx
import pydeck as pdk
import math

# --- CONFIG ---
SHEET_ID = "1sYlXP6WVzPE09qfmydQYQNsjiZcDgRSJGyWoXfjmkDY"
URL_BAZA = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=CENNIK_BAZA"
URL_OPLATY = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=OPLATY_STALE"
URL_USERS = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=USERS"

START_COORDS = [16.8122, 52.3358] 
CITY_GEO = {
    "Amsterdam": [4.8952, 52.3702], "Berlin": [13.4050, 52.5200], "Londyn": [-0.1276, 51.5074],
    "Paryż": [2.3522, 48.8566], "Wiedeń": [16.3738, 48.2082], "Praga": [14.4378, 50.0755],
    "Genewa": [6.1432, 46.2044], "Zurych": [8.5417, 47.3769], "Barcelona": [2.1734, 41.3851],
    "Monachium": [11.5820, 48.1351], "Mediolan": [9.1900, 45.4642]
}

st.set_page_config(page_title="SQM VANTAGE v13", layout="wide")

# --- CSS (v13) ---
st.markdown("""
    <style>
    .stApp { background: #0e1117 !important; background-image: radial-gradient(circle at 20% 20%, #1a2a4a 0%, #030508 100%) !important; }
    .v13-card { background: rgba(0, 0, 0, 0.8) !important; border-left: 5px solid #ed8936 !important; border-radius: 15px; padding: 30px !important; margin-bottom: 20px; }
    .v13-price { font-size: 70px !important; font-weight: 900 !important; color: #ffffff !important; line-height: 1; }
    .v13-label { color: #ed8936; font-weight: bold; text-transform: uppercase; letter-spacing: 2px; }
    .v13-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 15px; margin-top: 20px; }
    .v13-sub { border-top: 1px solid rgba(255,255,255,0.1); padding-top: 8px; }
    .v13-sub-label { color: #94a3b8; font-size: 0.75rem; }
    .v13-sub-val { color: #f8fafc; font-size: 1.1rem; font-weight: 600; }
    </style>
""", unsafe_allow_html=True)

# --- AUTH ---
def h(p): return hashlib.sha256(p.strip().encode()).hexdigest()
cookie_manager = stx.CookieManager()
if "auth" not in st.session_state: st.session_state.auth = False

@st.cache_data(ttl=5)
def get_u():
    df = pd.read_csv(URL_USERS)
    df.columns = df.columns.str.strip()
    return dict(zip(df['username'].astype(str), df['password'].astype(str)))

u_db = get_u()
token = cookie_manager.get(cookie="sqm_v13_token")
if token in u_db: st.session_state.auth, st.session_state.user = True, token

if not st.session_state.auth:
    _, c, _ = st.columns([1,1.5,1])
    with c:
        u = st.text_input("Logistyk")
        p = st.text_input("Klucz", type="password")
        if st.button("AUTORYZUJ", use_container_width=True):
            if u in u_db and u_db[u] == h(p):
                st.session_state.auth, st.session_state.user = True, u
                cookie_manager.set("sqm_v13_token", u, expires_at=datetime.now()+timedelta(days=30))
                st.rerun()
    st.stop()

# --- DATA ---
@st.cache_data(ttl=30)
def fetch():
    b = pd.read_csv(URL_BAZA); o = pd.read_csv(URL_OPLATY)
    b.columns = b.columns.str.strip()
    def cl(v): 
        s = re.sub(r'[^\d.]', '', str(v).replace(',', '.'))
        return float(s) if s else 0.0
    for c in ['Eksport', 'Import', 'Postoj']: b[c] = b[c].apply(cl)
    o['Wartosc'] = o['Wartosc'].apply(cl)
    return b, o

df_b, df_o = fetch()
cfg = dict(zip(df_o['Parametr'], df_o['Wartosc']))

# --- SIDEBAR ---
with st.sidebar:
    st.image("https://www.sqm.pl/wp-content/themes/sqm/img/logo-sqm.png", width=150)
    strat = st.radio("TRYB", ["DEDYKOWANY (Pełne auto)", "DOŁADUNEK (z wagi)"])
    dest = st.selectbox("CEL", sorted(df_b['Miasto'].unique()))
    kg = st.number_input("ŁADUNEK (kg)", value=500, step=100)
    d1 = st.date_input("START", datetime.now())
    d2 = st.date_input("KONIEC", datetime.now() + timedelta(days=2))
    dni = max(0, (d2-d1).days)

# --- LOGIKA V13: OPTYMALIZACJA ---
w_eff = kg * cfg.get('WAGA_BUFOR', 1.2)
# Limity ładowności
payloads = {"BUS": 1200, "SOLO": 5500, "FTL": 13600}

# 1. Wybór bazowego typu pojazdu (aby sprawdzić ceny w bazie)
if w_eff <= 1200: v_candidates = ["BUS", "SOLO", "FTL"]
elif w_eff <= 5500: v_candidates = ["SOLO", "FTL"]
else: v_candidates = ["FTL"]

best_price = float('inf')
best_v = "FTL"
best_rows = None

# Szukamy najtańszej opcji (Mix ceny i wagi)
for v in v_candidates:
    row = df_b[(df_b['Miasto'] == dest) & (df_b['Typ_Pojazdu'] == v)]
    if not row.empty:
        r = row.iloc[0]
        if "DEDYKOWANY" in strat:
            curr_p = r['Eksport'] + r['Import']
        else:
            # Ratio dla doładunku
            ratio = min(1.0, w_eff / payloads.get(v, 13600))
            curr_p = (r['Eksport'] + r['Import']) * ratio
        
        if curr_p < best_price:
            best_price = curr_p
            best_v = v
            best_rows = r

if best_rows is not None:
    # 2. Obliczanie ilości aut (jeśli ładunek > FTL)
    num_vehicles = math.ceil(w_eff / payloads.get(best_v, 13600))
    
    # Przeliczenie finalne
    if "DEDYKOWANY" in strat:
        exp = best_rows['Eksport'] * num_vehicles
        imp = best_rows['Import'] * num_vehicles
    else:
        # W doładunku zakładamy proporcję z jednego auta
        ratio = min(1.0, w_eff / payloads.get(best_v, 13600))
        exp = best_rows['Eksport'] * ratio
        imp = best_rows['Import'] * ratio

    postoj = best_rows['Postoj'] * dni * num_vehicles
    oplaty = (dni * cfg.get('PARKING_DAY', 30) * num_vehicles) + (cfg.get('ATA_CARNET', 166) if dest in ["Londyn", "Genewa", "Zurych"] else 0)
    total = exp + imp + postoj + oplaty

    # --- UI ---
    st.title(f"TRASA: KOMORNIKI ➔ {dest.upper()}")
    c1, c2 = st.columns([1.5, 1])
    
    with c1:
        st.markdown(f"""
            <div class="v13-card">
                <div class="v13-label">Sugerowana Stawka ({strat})</div>
                <div class="v13-price">€ {total:,.2f}</div>
                <div class="v13-grid">
                    <div class="v13-sub"><div class="v13-sub-label">Typ Pojazdu</div><div class="v13-sub-val">{best_v}</div></div>
                    <div class="v13-sub"><div class="v13-sub-label">Ilość Pojazdów</div><div class="v13-sub-val">{num_vehicles} szt.</div></div>
                    <div class="v13-sub"><div class="v13-sub-label">Waga (z buforem)</div><div class="v13-sub-val">{w_eff:,.0f} kg</div></div>
                    <div class="v13-sub"><div class="v13-sub-label">Eksport</div><div class="v13-sub-val">€ {exp:,.2f}</div></div>
                    <div class="v13-sub"><div class="v13-sub-label">Import</div><div class="v13-sub-val">€ {imp:,.2f}</div></div>
                    <div class="v13-sub"><div class="v13-sub-label">Inne (Postój/Opłaty)</div><div class="v13-sub-val">€ {postoj+oplaty:,.2f}</div></div>
                </div>
            </div>
        """, unsafe_allow_html=True)

    with c2:
        # MAPA z poprawionym stylem dla lepszej widoczności
        t_geo = CITY_GEO.get(dest, [13.4, 52.5])
        st.pydeck_chart(pdk.Deck(
            map_style='mapbox://styles/mapbox/navigation-night-v1',
            initial_view_state=pdk.ViewState(latitude=(START_COORDS[1]+t_geo[1])/2, longitude=(START_COORDS[0]+t_geo[0])/2, zoom=4, pitch=40),
            layers=[pdk.Layer("ArcLayer", data=pd.DataFrame([{"s": START_COORDS, "t": t_geo}]), get_source_position="s", get_target_position="t", get_source_color=[237, 137, 54], get_target_color=[255, 255, 255], get_width=5)]
        ))
