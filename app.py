import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import re
import hashlib
import extra_streamlit_components as stx
import math
import numpy as np

# --- KONFIGURACJA ZASOBÓW ---
SHEET_ID = "1sYlXP6WVzPE09qfmydQYQNsjiZcDgRSJGyWoXfjmkDY"
URL_BAZA = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=CENNIK_BAZA"
URL_OPLATY = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=OPLATY_STALE"
URL_USERS = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=USERS"

# --- TABELA TRANZYTU ---
TRANSIT_DATA = {
    "Berlin": {"BUS": 1, "FTL/SOLO": 1}, "Gdańsk": {"BUS": 1, "FTL/SOLO": 1},
    "Hamburg": {"BUS": 1, "FTL/SOLO": 1}, "Hannover": {"BUS": 1, "FTL/SOLO": 1},
    "Kielce": {"BUS": 1, "FTL/SOLO": 1}, "Lipsk": {"BUS": 1, "FTL/SOLO": 1},
    "Norymberga": {"BUS": 1, "FTL/SOLO": 1}, "Praga": {"BUS": 1, "FTL/SOLO": 1},
    "Warszawa": {"BUS": 1, "FTL/SOLO": 1}, "Amsterdam": {"BUS": 1, "FTL/SOLO": 2},
    "Bazylea": {"BUS": 1, "FTL/SOLO": 2}, "Bruksela": {"BUS": 1, "FTL/SOLO": 2},
    "Budapeszt": {"BUS": 1, "FTL/SOLO": 2}, "Frankfurt nad Menem": {"BUS": 1, "FTL/SOLO": 2},
    "Genewa": {"BUS": 2, "FTL/SOLO": 2}, "Kolonia / Dusseldorf": {"BUS": 1, "FTL/SOLO": 2},
    "Kopenhaga": {"BUS": 1, "FTL/SOLO": 2}, "Mediolan": {"BUS": 2, "FTL/SOLO": 2},
    "Monachium": {"BUS": 1, "FTL/SOLO": 2}, "Paryż": {"BUS": 1, "FTL/SOLO": 2},
    "Wiedeń": {"BUS": 1, "FTL/SOLO": 2}, "Barcelona": {"BUS": 2, "FTL/SOLO": 4},
    "Cannes / Nicea": {"BUS": 2, "FTL/SOLO": 3}, "Liverpool": {"BUS": 2, "FTL/SOLO": 3},
    "Londyn": {"BUS": 2, "FTL/SOLO": 3}, "Lyon": {"BUS": 2, "FTL/SOLO": 3},
    "Manchester": {"BUS": 2, "FTL/SOLO": 3}, "Rzym": {"BUS": 2, "FTL/SOLO": 4},
    "Sofia": {"BUS": 2, "FTL/SOLO": 3}, "Sztokholm": {"BUS": 2, "FTL/SOLO": 3},
    "Tuluza": {"BUS": 2, "FTL/SOLO": 4}, "Lizbona": {"BUS": 3, "FTL/SOLO": 5},
    "Madryt": {"BUS": 3, "FTL/SOLO": 4}, "Sewilla": {"BUS": 3, "FTL/SOLO": 5}
}

CITY_COORDS = {
    "Komorniki (Baza)": [52.3358, 16.8122], "Amsterdam": [52.3702, 4.8952], 
    "Berlin": [52.5200, 13.4050], "Londyn": [51.5074, -0.1276],
    "Paryż": [48.8566, 2.3522], "Wiedeń": [48.2082, 16.3738]
}

st.set_page_config(page_title="SQM LOGISTICS v16.3", layout="wide")

# --- KRYTYCZNY CSS DLA CZYTELNOŚCI (Naprawa błędu z białymi polami) ---
st.markdown("""
    <style>
    /* 1. TŁO SIDEBARU I RESET SYSTEMOWY */
    [data-testid="stSidebar"] {
        background-color: #0f172a !important;
        border-right: 1px solid #1e293b;
    }
    
    [data-testid="stSidebarNav"], header, [data-testid="stHeader"] {
        display: none !important;
    }

    /* 2. ETYKIETY I NAPISY W SIDEBARZE - BIAŁE I WYRAŹNE */
    [data-testid="stSidebar"] label, 
    [data-testid="stSidebar"] .stMarkdown p, 
    [data-testid="stSidebar"] span {
        color: #ffffff !important;
        font-weight: 700 !important;
        font-size: 14px !important;
    }

    /* 3. FIX DLA WIDOCZNOŚCI TEKSTU W POLACH (Force Black on White) */
    /* Jeśli Streamlit wymusza białe tło pola, my wymuszamy CZARNY tekst */
    [data-testid="stSidebar"] input, 
    [data-testid="stSidebar"] select,
    [data-testid="stSidebar"] div[data-baseweb="input"] input,
    [data-testid="stSidebar"] div[data-baseweb="select"] div {
        color: #000000 !important;
        -webkit-text-fill-color: #000000 !important;
        font-weight: 800 !important;
        background-color: #ffffff !important;
    }

    /* 4. STYLIZACJA WYNIKÓW (GŁÓWNY PANEL) */
    .stApp { background-color: #05070a !important; }
    .route-header { font-size: 30px !important; font-weight: 900; color: #ffffff; border-bottom: 3px solid #ed8936; margin-bottom: 20px; }
    .hero-card { background: linear-gradient(145deg, #1e293b, #0f172a); border: 1px solid #334155; border-radius: 15px; padding: 25px; margin-bottom: 20px; }
    .main-price { color: #ffffff; font-size: 70px; font-weight: 900; }
    
    .data-item { background: rgba(255,255,255,0.05); padding: 10px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.1); }
    .data-label { color: #94a3b8; font-size: 11px; font-weight: 700; text-transform: uppercase; }
    .data-value { color: #ffffff; font-size: 18px; font-weight: 800; }
    </style>
""", unsafe_allow_html=True)

# --- LOGOWANIE ---
def make_hash(p): return hashlib.sha256(p.strip().encode()).hexdigest()
cookie_manager = stx.CookieManager()

if "auth" not in st.session_state:
    st.session_state.auth = False
    st.session_state.user = None

@st.cache_data(ttl=10)
def load_users():
    try:
        df = pd.read_csv(URL_USERS); df.columns = df.columns.str.strip()
        return dict(zip(df['username'].astype(str), df['password'].astype(str)))
    except:
        return {"admin": "f3e99d9459eeb7ffc4cd407d890fbf1db011208fa12d8edc501a7ec26da106a3"}

user_db = load_users()
c_token = cookie_manager.get(cookie="sqm_session_v16")
if c_token in user_db:
    st.session_state.auth, st.session_state.user = True, c_token

if not st.session_state.auth:
    _, col, _ = st.columns([1, 1.2, 1])
    with col:
        st.markdown("<h2 style='text-align:center; color:white; margin-top:50px;'>SQM LOGISTICS</h2>", unsafe_allow_html=True)
        u_in = st.text_input("Użytkownik", key="l_user")
        p_in = st.text_input("Hasło", type="password", key="l_pass")
        if st.button("ZALOGUJ", use_container_width=True):
            if u_in in user_db and user_db[u_in] == make_hash(p_in):
                st.session_state.auth, st.session_state.user = True, u_in
                cookie_manager.set("sqm_session_v16", u_in, expires_at=datetime.now()+timedelta(days=7))
                st.rerun()
    st.stop()

# --- DANE ---
@st.cache_data(ttl=60)
def fetch_logs():
    b = pd.read_csv(URL_BAZA); o = pd.read_csv(URL_OPLATY); b.columns = b.columns.str.strip()
    if 'Dostawca' in b.columns:
        b = b[~b['Dostawca'].str.contains('SQM|Własny|Wlasny', case=False, na=False)]
    def clean(v):
        s = re.sub(r'[^\d.]', '', str(v).replace(',', '.')); return float(s) if s else 0.0
    for c in ['Eksport', 'Import', 'Postoj']: b[c] = b[c].apply(clean)
    o['Wartosc'] = o['Wartosc'].apply(clean)
    return b, o

df_baza, df_oplaty = fetch_logs()
cfg = dict(zip(df_oplaty['Parametr'], df_oplaty['Wartosc']))

# --- SIDEBAR (NAPRAWIONA CZYTELNOŚĆ) ---
with st.sidebar:
    st.image("https://www.sqm.pl/wp-content/themes/sqm/img/logo-sqm.png", width=160)
    st.markdown(f"<div style='color:#ed8936; font-weight:800; margin-bottom:20px;'>ZALOGOWANY: {st.session_state.user.upper()}</div>", unsafe_allow_html=True)
    
    st.markdown("### KONFIGURACJA")
    mode = st.radio("STRATEGIA", ["DEDYKOWANY", "DOŁADUNEK"])
    target = st.selectbox("CEL PODRÓŻY", sorted(TRANSIT_DATA.keys()))
    weight = st.number_input("WAGA ŁADUNKU (kg)", value=1000, step=500)
    
    st.markdown("---")
    st.markdown("### TERMINY")
    d_start = st.date_input("DATA ZAŁADUNKU", datetime.now() + timedelta(days=5))
    d_end = st.date_input("DATA POWROTU", datetime.now() + timedelta(days=10))
    days_stay = max(0, (d_end - d_start).days)
    
    if st.button("WYLOGUJ", use_container_width=True):
        cookie_manager.delete("sqm_session_v16")
        st.session_state.auth = False
        st.rerun()

# --- LOGIKA OBLICZEŃ ---
w_eff = weight * cfg.get('WAGA_BUFOR', 1.2)
caps = {"BUS": 1200, "SOLO": 5500, "FTL": 10500}
results = []

for v_type, cap in caps.items():
    res = df_baza[(df_baza['Miasto'] == target) & (df_baza['Typ_Pojazdu'] == v_type)]
    if not res.empty:
        r = res.mean(numeric_only=True)
        v_count = math.ceil(w_eff / cap)
        t_key = "BUS" if v_type == "BUS" else "FTL/SOLO"
        transit_days = TRANSIT_DATA.get(target, {}).get(t_key, 2)
        
        exp = (r['Eksport'] * v_count if mode == "DEDYKOWANY" else r['Eksport'] * (w_eff/cap))
        imp = (r['Import'] * v_count if mode == "DEDYKOWANY" else r['Import'] * (w_eff/cap))
        ata = (cfg.get('ATA_CARNET', 166) if target in ["Londyn", "Genewa", "Liverpool", "Manchester"] else 0)
        ferry = (cfg.get('Ferry_UK', 450) if any(x in target for x in ["Londyn", "Liverpool", "Manchester"]) else 0)
        parking = (days_stay * cfg.get('PARKING_DAY', 30) * v_count)
        stay_cost = r['Postoj'] * days_stay * v_count
        
        results.append({
            "Pojazd": v_type, "Szt": v_count, "Total": exp+imp+stay_cost+parking+ata+ferry, 
            "exp": exp, "imp": imp, "stay": stay_cost, "park": parking, "ata": ata, 
            "ferry": ferry, "transit": transit_days, "load": min(100, (w_eff/(v_count*cap))*100)
        })

# --- GŁÓWNY WIDOK ---
if results:
    best = min(results, key=lambda x: x['Total'])
    st.markdown(f'<div class="route-header">KOMORNIKI ➔ {target.upper()}</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns([1.8, 1])
    with col1:
        st.markdown(f"""
            <div class="hero-card">
                <div style="color:#ed8936; font-size:12px; font-weight:800; text-transform:uppercase;">Sugerowana Stawka Projektu (Netto)</div>
                <div class="main-price">€ {best['Total']:,.2f}</div>
                <div style="display:grid; grid-template-columns: repeat(4, 1fr); gap:10px; margin-top:20px;">
                    <div class="data-item"><div class="data-label">Pojazd</div><div class="data-value">{best['Pojazd']}</div></div>
                    <div class="data-item"><div class="data-label">Tranzyt</div><div class="data-value">{best['transit']} dni</div></div>
                    <div class="data-item"><div class="data-label">Postój</div><div class="data-value">{days_stay} dni</div></div>
                    <div class="data-item"><div class="data-label">Zapełnienie</div><div class="data-value">{best['load']:.0f}%</div></div>
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        st.write("### 🚛 SZCZEGÓŁY KOSZTÓW")
        st.json({
            "Transport (Exp+Imp)": f"€ {best['exp']+best['imp']:,.2f}",
            "Koszty Postoju": f"€ {best['stay']+best['park']:,.2f}",
            "Opłaty Dodatkowe (ATA/UK)": f"€ {best['ata']+best['ferry']:,.2f}"
        })

    with col2:
        st.write("### 📍 TRASA")
        st.map(pd.DataFrame({'lat': [52.33, 48.85], 'lon': [16.81, 2.35]}), color='#ed8936')
