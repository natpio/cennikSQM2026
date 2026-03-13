import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import re
import hashlib
import extra_streamlit_components as stx
import math
import numpy as np
import time

# --- KONFIGURACJA ZASOBÓW ---
SHEET_ID = "1sYlXP6WVzPE09qfmydQYQNsjiZcDgRSJGyWoXfjmkDY"
URL_BAZA = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=CENNIK_BAZA"
URL_OPLATY = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=OPLATY_STALE"
URL_USERS = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=USERS"

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
    "Paryż": [48.8566, 2.3522], "Wiedeń": [48.2082, 16.3738], 
    "Praga": [50.0755, 14.4378], "Genewa": [46.2044, 6.1432], 
    "Barcelona": [41.3851, 2.1734], "Monachium": [48.1351, 11.5820], 
    "Madryt": [40.4168, -3.7038], "Lizbona": [38.7223, -9.1393],
    "Rzym": [41.9028, 12.4964], "Sztokholm": [59.3293, 18.0686]
}

st.set_page_config(page_title="SQM VENTAGE v5.0.2", layout="wide")

# --- CSS Z AKTUALIZACJĄ KOLORÓW I ETYKIET ---
st.markdown("""
    <style>
    .stApp { background-color: #05070a !important; }
    [data-testid="stSidebar"] { background-color: #0f172a !important; border-right: 1px solid #1e293b; }

    /* SQM VENTAGE BRANDING */
    .brand-container {
        padding: 10px 0 20px 0;
        text-align: center;
        border-bottom: 1px solid #1e293b;
        margin-bottom: 20px;
    }
    .brand-logo {
        font-family: 'Inter', sans-serif;
        font-size: 20px;
        font-weight: 900;
        letter-spacing: 2px;
        color: #ffffff;
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 10px;
    }
    .brand-v {
        background: #ed8936;
        color: #000;
        padding: 2px 8px;
        border-radius: 4px;
        font-style: italic;
    }
    .brand-ver {
        font-size: 10px;
        color: #ffffff !important; /* Zmiana na biały */
        margin-top: 5px;
        font-weight: 600;
        opacity: 0.9;
    }

    /* Sidebar Fixes */
    [data-testid="stSidebar"] div[data-baseweb="select"], 
    [data-testid="stSidebar"] div[data-baseweb="input"],
    [data-testid="stSidebar"] .stNumberInput div,
    [data-testid="stSidebar"] .stDateInput div {
        background-color: #1e293b !important;
        color: white !important;
    }
    [data-testid="stSidebar"] input {
        background-color: #1e293b !important;
        color: #ffffff !important;
        -webkit-text-fill-color: #ffffff !important;
    }
    [data-testid="stSidebar"] label p { color: #94a3b8 !important; font-weight: 700; text-transform: uppercase; font-size: 0.75rem; }
    
    /* Zmiana koloru nagłówków H3 w Sidebarze na biały (np. PARAMETRY) */
    [data-testid="stSidebar"] h3 {
        color: #ffffff !important;
        font-size: 1.1rem !important;
    }

    /* UI Components */
    .route-header { font-size: 32px !important; font-weight: 900; color: #ffffff; border-bottom: 3px solid #ed8936; margin-bottom: 25px; padding-bottom: 10px; }
    .hero-card { background: linear-gradient(145deg, #1e293b, #0f172a); border: 1px solid #334155; border-radius: 20px; padding: 35px; margin-bottom: 30px; }
    .main-price-value { color: #ffffff; font-size: 85px; font-weight: 950; line-height: 1; margin: 15px 0; }

    .alt-card { 
        background: #0f172a; 
        border-left: 5px solid #475569; 
        padding: 18px 25px; 
        margin-bottom: 12px; 
        border-radius: 8px; 
        display: flex; 
        justify-content: space-between; 
        align-items: center; 
    }
    .alt-card b { color: #ffffff !important; font-size: 18px; font-weight: 800; }
    .alt-card small { color: #94a3b8 !important; font-size: 13px; margin-left: 8px; }
    .alt-best { border-left-color: #ed8936; background: rgba(237, 137, 54, 0.1); }
    .price-tag { color: #ed8936; font-size: 22px; font-weight: 900; }
    </style>
""", unsafe_allow_html=True)

# --- LOGOWANIE ---
def make_hash(p): return hashlib.sha256(p.strip().encode()).hexdigest()
cookie_manager = stx.CookieManager()

if "authenticated" not in st.session_state: st.session_state.authenticated = False
if "user_id" not in st.session_state: st.session_state.user_id = None

@st.cache_data(ttl=30)
def load_users():
    try:
        df = pd.read_csv(URL_USERS); df.columns = df.columns.str.strip()
        return dict(zip(df['username'].astype(str), df['password'].astype(str)))
    except: return {"admin": "f3e99d9459eeb7ffc4cd407d890fbf1db011208fa12d8edc501a7ec26da106a3"}

user_db = load_users()
if not st.session_state.authenticated:
    c_token = cookie_manager.get(cookie="sqm_session_v5")
    if c_token in user_db: st.session_state.authenticated = True; st.session_state.user_id = c_token

if not st.session_state.authenticated:
    _, col, _ = st.columns([1, 1.2, 1])
    with col:
        st.markdown("<h2 style='text-align:center; color:white;'>SQM VENTAGE</h2>", unsafe_allow_html=True)
        u_in = st.text_input("Użytkownik"); p_in = st.text_input("Hasło", type="password")
        if st.button("ZALOGUJ"):
            if u_in in user_db and user_db[u_in] == make_hash(p_in):
                st.session_state.authenticated = True; st.session_state.user_id = u_in
                cookie_manager.set("sqm_session_v5", u_in, expires_at=datetime.now()+timedelta(days=7))
                st.rerun()
    st.stop()

# --- POBIERANIE DANYCH ---
@st.cache_data(ttl=60)
def fetch_logs():
    try:
        b = pd.read_csv(URL_BAZA); o = pd.read_csv(URL_OPLATY); b.columns = b.columns.str.strip()
        if 'Dostawca' in b.columns: b = b[~b['Dostawca'].str.contains('SQM|Własny|Wlasny', case=False, na=False)]
        def clean(v):
            s = re.sub(r'[^\d.]', '', str(v).replace(',', '.')); return float(s) if s else 0.0
        for c in ['Eksport', 'Import', 'Postoj']: 
            if c in b.columns: b[c] = b[c].apply(clean)
        o['Wartosc'] = o['Wartosc'].apply(clean)
        return b, o
    except: return pd.DataFrame(), pd.DataFrame()

df_baza, df_oplaty = fetch_logs()
cfg = dict(zip(df_oplaty['Parametr'], df_oplaty['Wartosc'])) if not df_oplaty.empty else {}

# --- SIDEBAR VENTAGE ---
with st.sidebar:
    st.markdown("""
        <div class="brand-container">
            <div class="brand-logo"><span class="brand-v">V</span> SQM VENTAGE</div>
            <div class="brand-ver">SYSTEM LOGISTYCZNY VER. 5.0.1</div>
        </div>
    """, unsafe_allow_html=True)
    
    st.image("https://www.sqm.pl/wp-content/themes/sqm/img/logo-sqm.png", width=150)
    st.markdown(f"<div style='color:#94a3b8; font-size:11px; margin-bottom:20px;'>OPERATOR: <b>{st.session_state.user_id.upper()}</b></div>", unsafe_allow_html=True)
    
    st.markdown("### 🚛 PARAMETRY")
    trip_type = st.radio("KIERUNEK", ["PEŁNA TRASA (EXP+IMP)", "TYLKO DOSTAWA (ONE-WAY)"])
    mode = st.radio("STRATEGIA", ["DEDYKOWANY", "DOŁADUNEK"])
    target = st.selectbox("CEL PODRÓŻY", sorted(TRANSIT_DATA.keys()))
    weight = st.number_input("WAGA (KG)", value=1000, step=500, min_value=1)
    
    st.markdown("### 📅 TERMINARZ")
    d_start = st.date_input("PIERWSZY DZIEŃ MONTAŻU", datetime.now() + timedelta(days=5))
    
    if trip_type == "PEŁNA TRASA (EXP+IMP)":
        d_end = st.date_input("OSTATNI DZIEŃ DEMONTAŻU", d_start + timedelta(days=5))
        days_stay = max(0, (d_end - d_start).days)
    else:
        days_stay = 0
        st.caption("Tryb One-Way: brak postoju")

    if st.button("🚪 WYLOGUJ"):
        cookie_manager.delete("sqm_session_v5"); st.session_state.authenticated = False; st.rerun()

# --- OBLICZENIA ---
w_eff = weight * cfg.get('WAGA_BUFOR', 1.2)
caps = {"BUS": 1200, "SOLO": 5500, "FTL": 10500}
results = []

if not df_baza.empty:
    for v_type, cap in caps.items():
        res = df_baza[(df_baza['Miasto'] == target) & (df_baza['Typ_Pojazdu'] == v_type)]
        if not res.empty:
            r = res.mean(numeric_only=True); v_count = math.ceil(w_eff / cap)
            transit_days = TRANSIT_DATA.get(target, {}).get("BUS" if v_type=="BUS" else "FTL/SOLO", 2)
            
            exp = (r['Eksport'] * v_count if mode == "DEDYKOWANY" else r['Eksport'] * (w_eff/cap))
            imp = (r['Import'] * v_count if mode == "DEDYKOWANY" else r['Import'] * (w_eff/cap)) if trip_type == "PEŁNA TRASA (EXP+IMP)" else 0
            
            ata = (cfg.get('ATA_CARNET', 166) if target in ["Londyn", "Genewa", "Liverpool", "Manchester"] else 0)
            ferry = (cfg.get('Ferry_UK', 450) if any(x in target for x in ["Londyn", "Liverpool", "Manchester"]) else 0)
            park = (days_stay * cfg.get('PARKING_DAY', 30) * v_count)
            stay = r['Postoj'] * days_stay * v_count
            
            total = exp + imp + stay + park + ata + ferry
            results.append({"Pojazd": v_type, "Szt": v_count, "Total": total, "transit": transit_days, "load": min(100, (w_eff/(v_count*cap))*100)})

# --- WIDOK GŁÓWNY ---
if results:
    best = min(results, key=lambda x: x['Total'])
    st.markdown(f'<div class="route-header">KOMORNIKI ➔ {target.upper()} <small style="font-size:14px; color:#94a3b8;">({trip_type})</small></div>', unsafe_allow_html=True)
    cl, cr = st.columns([1.8, 1])
    with cl:
        st.markdown(f"""<div class="hero-card"><div style='color:#ed8936;font-size:14px;font-weight:800;'>KOSZT SZACUNKOWY NETTO</div><div class="main-price-value">€ {best['Total']:,.2f}</div>
                    <div style='display:grid;grid-template-columns:repeat(4,1fr);gap:15px;margin-top:25px;'>
                    <div style='background:rgba(255,255,255,0.05);padding:15px;border-radius:10px;'><div style='color:#94a3b8;font-size:10px;font-weight:700;'>TRANZYT</div><div style='color:white;font-size:22px;font-weight:900;'>{best['transit']} dni</div></div>
                    <div style='background:rgba(255,255,255,0.05);padding:15px;border-radius:10px;'><div style='color:#94a3b8;font-size:10px;font-weight:700;'>DNI NA TARGACH</div><div style='color:white;font-size:22px;font-weight:900;'>{days_stay}d</div></div>
                    <div style='background:rgba(255,255,255,0.05);padding:15px;border-radius:10px;'><div style='color:#94a3b8;font-size:10px;font-weight:700;'>OPCJA</div><div style='color:white;font-size:22px;font-weight:900;'>{best['Pojazd']}</div></div>
                    <div style='background:rgba(255,255,255,0.05);padding:15px;border-radius:10px;'><div style='color:#94a3b8;font-size:10px;font-weight:700;'>ZAPEŁNIENIE</div><div style='color:white;font-size:22px;font-weight:900;'>{best['load']:.0f}%</div></div></div></div>""", unsafe_allow_html=True)
        st.write("### 🚛 ANALIZA KOSZTÓW POJAZDÓW")
        for r in sorted(results, key=lambda x: x['Total']):
            is_best = "alt-best" if r['Pojazd'] == best['Pojazd'] else ""
            st.markdown(f"""<div class="alt-card {is_best}"><div><b>{r['Pojazd']}</b> <small>({r['Szt']} szt. | Załadunek {r['load']:.0f}%)</small></div><div class="price-tag">€ {r['Total']:,.2f}</div></div>""", unsafe_allow_html=True)
    with cr:
        b_pos, d_pos = CITY_COORDS["Komorniki (Baza)"], CITY_COORDS.get(target, [48.8, 2.3])
        st.map(pd.DataFrame({'lat': np.linspace(b_pos[0], d_pos[0], 25), 'lon': np.linspace(b_pos[1], d_pos[1], 25)}), color='#ed8936', size=15)
        st.info(f"**Montaż start:** {d_start}")
