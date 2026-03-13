import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import re
import hashlib
import extra_streamlit_components as stx
import math

# --- CONFIG ---
SHEET_ID = "1sYlXP6WVzPE09qfmydQYQNsjiZcDgRSJGyWoXfjmkDY"
URL_BAZA = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=CENNIK_BAZA"
URL_OPLATY = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=OPLATY_STALE"
URL_USERS = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=USERS"

# Współrzędne dla natywnej mapy (Szerokość, Długość)
CITY_COORDS = {
    "Komorniki (Baza)": [52.3358, 16.8122],
    "Amsterdam": [52.3702, 4.8952], "Berlin": [52.5200, 13.4050], "Londyn": [51.5074, -0.1276],
    "Paryż": [48.8566, 2.3522], "Wiedeń": [48.2082, 16.3738], "Praga": [50.0755, 14.4378],
    "Genewa": [46.2044, 6.1432], "Zurych": [47.3769, 8.5417], "Barcelona": [41.3851, 2.1734],
    "Monachium": [48.1351, 11.5820], "Mediolan": [45.4642, 9.1900]
}

st.set_page_config(page_title="SQM VANTAGE v14", layout="wide")

# --- CSS (Wymuszenie odświeżenia przez nowe klasy v14) ---
st.markdown("""
    <style>
    .stApp { background: #0a0e14 !important; }
    .v14-container {
        background: rgba(17, 25, 40, 0.95) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-radius: 12px;
        padding: 25px !important;
        margin-bottom: 20px;
    }
    .v14-price-tag {
        font-size: 65px !important;
        font-weight: 800 !important;
        color: #ed8936 !important;
        margin: 10px 0;
    }
    .v14-stat-box {
        background: rgba(255, 255, 255, 0.03);
        padding: 15px;
        border-radius: 8px;
        text-align: center;
    }
    .v14-label { color: #94a3b8; font-size: 0.8rem; text-transform: uppercase; margin-bottom: 5px; }
    .v14-value { color: #ffffff; font-size: 1.2rem; font-weight: 600; }
    </style>
""", unsafe_allow_html=True)

# --- AUTH SYSTEM ---
def make_hash(p): return hashlib.sha256(p.strip().encode()).hexdigest()
cookie_manager = stx.CookieManager()

@st.cache_data(ttl=5)
def load_u():
    df = pd.read_csv(URL_USERS)
    df.columns = df.columns.str.strip()
    return dict(zip(df['username'].astype(str), df['password'].astype(str)))

user_db = load_u()
if "auth" not in st.session_state: st.session_state.auth = False

# Nowy token v14 wymusi przelogowanie i reset cache
c_token = cookie_manager.get(cookie="sqm_v14_session")
if c_token in user_db:
    st.session_state.auth = True
    st.session_state.user = c_token

if not st.session_state.auth:
    _, col, _ = st.columns([1, 1.2, 1])
    with col:
        st.markdown("<h2 style='text-align:center; color:white;'>SQM VANTAGE v14</h2>", unsafe_allow_html=True)
        u_in = st.text_input("Użytkownik")
        p_in = st.text_input("Hasło", type="password")
        if st.button("ZALOGUJ", use_container_width=True):
            if u_in in user_db and user_db[u_in] == make_hash(p_in):
                st.session_state.auth = True
                st.session_state.user = u_in
                cookie_manager.set("sqm_v14_session", u_in, expires_at=datetime.now()+timedelta(days=7))
                st.rerun()
    st.stop()

# --- DATA FETCH ---
@st.cache_data(ttl=60)
def fetch_logs():
    b = pd.read_csv(URL_BAZA); o = pd.read_csv(URL_OPLATY)
    b.columns = b.columns.str.strip()
    def clean(v):
        s = re.sub(r'[^\d.]', '', str(v).replace(',', '.'))
        return float(s) if s else 0.0
    for c in ['Eksport', 'Import', 'Postoj']: b[c] = b[c].apply(clean)
    o['Wartosc'] = o['Wartosc'].apply(clean)
    return b, o

df_baza, df_oplaty = fetch_logs()
cfg = dict(zip(df_oplaty['Parametr'], df_oplaty['Wartosc']))

# --- SIDEBAR ---
with st.sidebar:
    st.image("https://www.sqm.pl/wp-content/themes/sqm/img/logo-sqm.png", width=120)
    st.write(f"Zalogowany: **{st.session_state.user}**")
    mode = st.radio("STRATEGIA", ["DEDYKOWANY", "DOŁADUNEK"])
    target = st.selectbox("MIASTO DOCELOWE", sorted(df_baza['Miasto'].unique()))
    weight = st.number_input("WAGA ŁADUNKU (kg)", value=1000, step=500)
    d_start = st.date_input("DATA ZAŁADUNKU", datetime.now())
    d_end = st.date_input("DATA ROZŁADUNKU", datetime.now() + timedelta(days=2))
    days = max(0, (d_end - d_start).days)
    if st.button("WYLOGUJ"):
        cookie_manager.delete("sqm_v14_session")
        st.session_state.auth = False
        st.rerun()

# --- LOGIKA WYBORU POJAZDU (MIX WAGA/CENA) ---
w_eff = weight * cfg.get('WAGA_BUFOR', 1.2)
caps = {"BUS": 1200, "SOLO": 5500, "FTL": 13600}

# Wyliczamy najtańszą opcję
best_v, best_price, best_row = None, float('inf'), None

for v_type, cap in caps.items():
    res = df_baza[(df_baza['Miasto'] == target) & (df_baza['Typ_Pojazdu'] == v_type)]
    if not res.empty:
        r = res.iloc[0]
        # Koszt 1 auta tego typu
        if mode == "DEDYKOWANY":
            c = r['Eksport'] + r['Import']
        else:
            # Doładunek proporcjonalny
            ratio = min(1.0, w_eff / cap)
            c = (r['Eksport'] + r['Import']) * ratio
        
        if c < best_price:
            best_price, best_v, best_row = c, v_type, r

if best_row is not None:
    # Wyliczamy ile takich aut potrzebujemy
    count = math.ceil(w_eff / caps[best_v])
    
    # Finalne koszty
    if mode == "DEDYKOWANY":
        exp, imp = best_row['Eksport'] * count, best_row['Import'] * count
    else:
        ratio = min(1.0, w_eff / caps[best_v])
        exp, imp = best_row['Eksport'] * ratio, best_row['Import'] * ratio

    stay = best_row['Postoj'] * days * count
    fees = (days * cfg.get('PARKING_DAY', 30) * count) + (cfg.get('ATA_CARNET', 166) if target in ["Londyn", "Genewa", "Zurych"] else 0)
    total = exp + imp + stay + fees

    # --- UI GŁÓWNE ---
    st.markdown(f"### ANALIZA LOGISTYCZNA: KOMORNIKI ➔ {target.upper()}")
    
    col_main, col_map = st.columns([1.2, 1])
    
    with col_main:
        st.markdown(f"""
            <div class="v14-container">
                <div class="v14-label">Sugerowany Koszt Projektu ({mode})</div>
                <div class="v14-price-tag">€ {total:,.2f}</div>
                <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 10px;">
                    <div class="v14-stat-box"><div class="v14-label">Pojazd</div><div class="v14-value">{best_v}</div></div>
                    <div class="v14-stat-box"><div class="v14-label">Ilość</div><div class="v14-value">{count} szt.</div></div>
                    <div class="v14-stat-box"><div class="v14-label">Waga +20%</div><div class="v14-value">{w_eff:,.0f} kg</div></div>
                </div>
                <div style="margin-top: 20px; border-top: 1px solid #333; padding-top: 15px;">
                    <table style="width:100%; color: #94a3b8;">
                        <tr><td>Eksport Netto:</td><td style="text-align:right; color:white;">€ {exp:,.2f}</td></tr>
                        <tr><td>Import Netto:</td><td style="text-align:right; color:white;">€ {imp:,.2f}</td></tr>
                        <tr><td>Postój ({days} dni):</td><td style="text-align:right; color:white;">€ {stay:,.2f}</td></tr>
                        <tr><td>Opłaty stałe:</td><td style="text-align:right; color:white;">€ {fees:,.2f}</td></tr>
                    </table>
                </div>
            </div>
        """, unsafe_allow_html=True)

    with col_map:
        # NOWA NATYWNA MAPA (Bezpłatna, Szybka, Niezawodna)
        base_pos = CITY_COORDS["Komorniki (Baza)"]
        dest_pos = CITY_COORDS.get(target, [52.5, 13.4])
        
        map_df = pd.DataFrame({
            'lat': [base_pos[0], dest_pos[0]],
            'lon': [base_pos[1], dest_pos[1]],
            'name': ['SQM Baza', target]
        })
        st.map(map_df, size=20, color='#ed8936')
        st.caption(f"Trasa operacyjna: Komorniki — {target}")

else:
    st.error(f"Brak stawek w bazie dla lokalizacji: {target}")
