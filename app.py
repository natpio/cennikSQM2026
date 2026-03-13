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

st.set_page_config(page_title="SQM LOGISTICS v16.6", layout="wide")

# --- OSTATECZNA NAPRAWA CSS DLA SIDEBARU ---
st.markdown("""
    <style>
    .stApp { background-color: #05070a !important; }
    [data-testid="stSidebar"] { background-color: #0f172a !important; border-right: 1px solid #1e293b; }

    /* Wymuszenie ciemnego tła dla WSZYSTKICH kontrolek w sidebarze */
    [data-testid="stSidebar"] div[data-baseweb="select"], 
    [data-testid="stSidebar"] div[data-baseweb="input"],
    [data-testid="stSidebar"] .stNumberInput div,
    [data-testid="stSidebar"] .stDateInput div {
        background-color: #1e293b !important;
        color: white !important;
    }

    /* Naprawa białego tła w polach tekstowych/numerycznych */
    [data-testid="stSidebar"] input {
        background-color: #1e293b !important;
        color: #ffffff !important;
        border: none !important;
        -webkit-text-fill-color: #ffffff !important;
    }

    /* Naprawa Selectboxa (Barcelona itp) */
    [data-testid="stSidebar"] div[data-baseweb="select"] > div {
        background-color: #1e293b !important;
        color: white !important;
    }
    
    [data-testid="stSidebar"] div[role="listbox"] {
        background-color: #1e293b !important;
        color: white !important;
    }

    /* Kolory nagłówków i etykiet */
    [data-testid="stSidebar"] label p { color: #94a3b8 !important; font-weight: 700; text-transform: uppercase; }
    .sidebar-header { color: #ed8936; font-size: 1rem; font-weight: 800; border-bottom: 1px solid #1e293b; margin: 20px 0 10px 0; }

    .route-header { font-size: 32px !important; font-weight: 900; color: #ffffff; border-bottom: 3px solid #ed8936; margin-bottom: 25px; padding-bottom: 10px; }
    .hero-card { background: linear-gradient(145deg, #1e293b, #0f172a); border: 1px solid #334155; border-radius: 20px; padding: 35px; margin-bottom: 30px; }
    .main-price-value { color: #ffffff; font-size: 85px; font-weight: 950; line-height: 1; margin: 15px 0; }
    .alt-card { background: #0f172a; border-left: 5px solid #475569; padding: 15px 20px; margin-bottom: 10px; border-radius: 8px; display: flex; justify-content: space-between; align-items: center; }
    .alt-best { border-left-color: #ed8936; background: rgba(237, 137, 54, 0.1); }
    </style>
""", unsafe_allow_html=True)

# --- SYSTEM AUTORYZACJI ---
def make_hash(p): return hashlib.sha256(p.strip().encode()).hexdigest()
cookie_manager = stx.CookieManager()

if "authenticated" not in st.session_state: st.session_state.authenticated = False
if "user_id" not in st.session_state: st.session_state.user_id = None
if "logout_triggered" not in st.session_state: st.session_state.logout_triggered = False

@st.cache_data(ttl=30)
def load_users():
    try:
        df = pd.read_csv(URL_USERS)
        df.columns = df.columns.str.strip()
        return dict(zip(df['username'].astype(str), df['password'].astype(str)))
    except: return {"admin": "f3e99d9459eeb7ffc4cd407d890fbf1db011208fa12d8edc501a7ec26da106a3"}

user_db = load_users()

if not st.session_state.authenticated and not st.session_state.logout_triggered:
    c_token = cookie_manager.get(cookie="sqm_session_v16")
    if c_token and c_token in user_db:
        st.session_state.authenticated = True
        st.session_state.user_id = c_token

if not st.session_state.authenticated:
    _, col, _ = st.columns([1, 1.2, 1])
    with col:
        st.markdown("<h2 style='text-align:center; color:white; margin-top:50px;'>SQM LOGISTICS</h2>", unsafe_allow_html=True)
        u_in = st.text_input("Użytkownik", key="log_u")
        p_in = st.text_input("Hasło", type="password", key="log_p")
        if st.button("ZALOGUJ", use_container_width=True):
            if u_in in user_db and user_db[u_in] == make_hash(p_in):
                st.session_state.authenticated = True
                st.session_state.user_id = u_in
                st.session_state.logout_triggered = False
                cookie_manager.set("sqm_session_v16", u_in, expires_at=datetime.now()+timedelta(days=7))
                time.sleep(1); st.rerun()
            else: st.error("Błędne dane")
    st.stop()

# --- POBIERANIE DANYCH ---
@st.cache_data(ttl=60)
def fetch_logs():
    try:
        b = pd.read_csv(URL_BAZA); o = pd.read_csv(URL_OPLATY)
        b.columns = b.columns.str.strip()
        if 'Dostawca' in b.columns: b = b[~b['Dostawca'].str.contains('SQM|Własny|Wlasny', case=False, na=False)]
        def clean(v):
            s = re.sub(r'[^\d.]', '', str(v).replace(',', '.'))
            return float(s) if s else 0.0
        for c in ['Eksport', 'Import', 'Postoj']: 
            if c in b.columns: b[c] = b[c].apply(clean)
        o['Wartosc'] = o['Wartosc'].apply(clean)
        return b, o
    except: return pd.DataFrame(), pd.DataFrame()

df_baza, df_oplaty = fetch_logs()
cfg = dict(zip(df_oplaty['Parametr'], df_oplaty['Wartosc'])) if not df_oplaty.empty else {}

# --- SIDEBAR ---
with st.sidebar:
    st.markdown("<br>", unsafe_allow_html=True)
    st.image("https://www.sqm.pl/wp-content/themes/sqm/img/logo-sqm.png", width=180)
    
    st.markdown(f"""
        <div style='background: #1e293b; padding: 15px; border-radius: 10px; border-left: 4px solid #ed8936; margin: 20px 0;'>
            <div style='color: #94a3b8; font-size: 10px; font-weight: 700; text-transform: uppercase;'>Operator</div>
            <div style='color: #ffffff; font-size: 14px; font-weight: 800;'>{st.session_state.user_id.upper() if st.session_state.user_id else ""}</div>
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown('<div class="sidebar-header">⚙️ KONFIGURACJA</div>', unsafe_allow_html=True)
    mode = st.radio("STRATEGIA", ["DEDYKOWANY", "DOŁADUNEK"])
    target = st.selectbox("CEL PODRÓŻY", sorted(TRANSIT_DATA.keys()))
    weight = st.number_input("WAGA (KG)", value=1000, step=500, min_value=1)
    
    st.markdown('<div class="sidebar-header">📅 TERMINARZ</div>', unsafe_allow_html=True)
    d_start = st.date_input("ZAŁADUNEK", datetime.now() + timedelta(days=5))
    d_end = st.date_input("POWRÓT", datetime.now() + timedelta(days=10))
    days_stay = max(0, (d_end - d_start).days)
    
    st.info(f"Postój: {days_stay} dni")
    if st.button("🚪 WYLOGUJ MNIE", use_container_width=True):
        st.session_state.logout_triggered = True; st.session_state.authenticated = False
        cookie_manager.delete("sqm_session_v16"); time.sleep(0.8); st.rerun()

# --- OBLICZENIA I WIDOK ---
w_eff = weight * cfg.get('WAGA_BUFOR', 1.2)
caps = {"BUS": 1200, "SOLO": 5500, "FTL": 10500}
results = []

if not df_baza.empty:
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
            results.append({"Pojazd": v_type, "Szt": v_count, "Total": exp+imp+stay_cost+parking+ata+ferry, "exp": exp, "imp": imp, "stay": stay_cost, "park": parking, "ata": ata, "ferry": ferry, "transit": transit_days, "load": min(100, (w_eff/(v_count*cap))*100)})

if results:
    best = min(results, key=lambda x: x['Total'])
    st.markdown(f'<div class="route-header">KOMORNIKI ➔ {target.upper()}</div>', unsafe_allow_html=True)
    cl, cr = st.columns([1.8, 1])
    with cl:
        st.markdown(f"""<div class="hero-card"><div style='color:#ed8936;font-size:14px;font-weight:800;text-transform:uppercase;'>Sugerowana Stawka (Netto)</div><div class="main-price-value">€ {best['Total']:,.2f}</div>
                    <div style='display:grid;grid-template-columns:repeat(4,1fr);gap:15px;margin-top:25px;'>
                    <div style='background:rgba(255,255,255,0.05);padding:15px;border-radius:10px;'><div style='color:#94a3b8;font-size:10px;font-weight:700;'>TRANZYT</div><div style='color:white;font-size:22px;font-weight:900;'>{best['transit']} dni</div></div>
                    <div style='background:rgba(255,255,255,0.05);padding:15px;border-radius:10px;'><div style='color:#94a3b8;font-size:10px;font-weight:700;'>POSTÓJ</div><div style='color:white;font-size:22px;font-weight:900;'>{days_stay} dni</div></div>
                    <div style='background:rgba(255,255,255,0.05);padding:15px;border-radius:10px;'><div style='color:#94a3b8;font-size:10px;font-weight:700;'>POJAZD</div><div style='color:white;font-size:22px;font-weight:900;'>{best['Pojazd']}</div></div>
                    <div style='background:rgba(255,255,255,0.05);padding:15px;border-radius:10px;'><div style='color:#94a3b8;font-size:10px;font-weight:700;'>ŁADUNEK</div><div style='color:white;font-size:22px;font-weight:900;'>{best['load']:.0f}%</div></div></div></div>""", unsafe_allow_html=True)
        st.write("### 📊 ANALIZA")
        for r in sorted(results, key=lambda x: x['Total']):
            is_best = "alt-best" if r['Pojazd'] == best['Pojazd'] else ""
            st.markdown(f"""<div class="alt-card {is_best}"><div><b>{r['Pojazd']}</b> <small>({r['Szt']} szt.)</small></div><div style='color:#ed8936;font-size:20px;font-weight:900;'>€ {r['Total']:,.2f}</div></div>""", unsafe_allow_html=True)
    with cr:
        b_pos, d_pos = CITY_COORDS["Komorniki (Baza)"], CITY_COORDS.get(target, [48.8, 2.3])
        st.map(pd.DataFrame({'lat': np.linspace(b_pos[0], d_pos[0], 25), 'lon': np.linspace(b_pos[1], d_pos[1], 25)}), color='#ed8936', size=15)
        st.info(f"**Wyjazd:** {(d_start - timedelta(days=best['transit'])).strftime('%Y-%m-%d')}")
