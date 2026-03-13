import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import re
import hashlib
import math
import numpy as np
import time

# --- KONFIGURACJA ZASOBÓW I ADRESY GOOGLE SHEETS ---
SHEET_ID = "1sYlXP6WVzPE09qfmydQYQNsjiZcDgRSJGyWoXfjmkDY"
URL_BAZA = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=CENNIK_BAZA"
URL_OPLATY = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=OPLATY_STALE"
URL_USERS = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=USERS"

# Pełna baza tranzytów SQM Multimedia Solutions
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

st.set_page_config(page_title="SQM VENTAGE v12.3", layout="wide")

# --- CSS: WARSTWA WIZUALNA ---
st.markdown("""
    <style>
    .stApp { background-color: #05070a !important; }
    [data-testid="stSidebar"] { background-color: #0f172a !important; border-right: 1px solid #1e293b; }
    div[data-baseweb="select"] > div, div[data-baseweb="input"] > div, .stNumberInput div[data-baseweb="input"], .stDateInput div[data-baseweb="input"] {
        background-color: #1e293b !important; color: #ffffff !important; border: 1px solid #334155 !important;
    }
    input { color: #ffffff !important; -webkit-text-fill-color: #ffffff !important; }
    .brand-container { padding: 10px 0 20px 0; text-align: center; border-bottom: 1px solid #1e293b; margin-bottom: 20px; }
    .brand-logo { font-family: 'Inter', sans-serif; font-size: 20px; font-weight: 900; color: #ffffff; display: flex; align-items: center; justify-content: center; gap: 10px; }
    .brand-v { background: #ed8936; color: #000; padding: 2px 8px; border-radius: 4px; font-style: italic; }
    .route-header { font-size: 30px !important; font-weight: 900; color: #ffffff; border-bottom: 3px solid #ed8936; margin-bottom: 25px; padding-bottom: 10px; }
    .hero-card { background: linear-gradient(145deg, #1e293b, #0f172a); border: 1px solid #334155; border-radius: 20px; padding: 30px; margin-bottom: 30px; }
    .main-price-value { color: #ffffff; font-size: 64px; font-weight: 950; line-height: 1.1; margin: 15px 0; }
    .price-tag { color: #ed8936; font-size: 20px; font-weight: 900; }
    [data-testid="stSidebar"] label p { color: #94a3b8 !important; font-weight: 700; text-transform: uppercase; font-size: 0.75rem; }
    </style>
""", unsafe_allow_html=True)

# --- SYSTEM AUTORYZACJI ---
def hash_pass(p): return hashlib.sha256(p.strip().encode()).hexdigest()

@st.cache_data(ttl=300)
def load_users():
    try:
        df = pd.read_csv(URL_USERS)
        df.columns = df.columns.str.strip()
        return dict(zip(df['username'].astype(str), df['password'].astype(str)))
    except:
        return {"admin": "f3e99d9459eeb7ffc4cd407d890fbf1db011208fa12d8edc501a7ec26da106a3"}

user_db = load_users()

if "auth" not in st.session_state:
    st.session_state.auth = False
if "user" not in st.session_state:
    st.session_state.user = ""

if not st.session_state.auth:
    _, col, _ = st.columns([1, 1.2, 1])
    with col:
        st.markdown("<h2 style='text-align:center; color:white; margin-top:50px;'>SQM VENTAGE</h2>", unsafe_allow_html=True)
        u_in = st.text_input("Użytkownik", key="login_u").strip()
        p_in = st.text_input("Hasło", type="password", key="login_p").strip()
        if st.button("ZALOGUJ", use_container_width=True):
            if u_in in user_db and user_db[u_in] == hash_pass(p_in):
                st.session_state.auth = True
                st.session_state.user = str(u_in)
                st.rerun()
            else:
                st.error("Błędne dane.")
    st.stop()

# --- POBIERANIE DANYCH ---
@st.cache_data(ttl=60)
def fetch_data():
    try:
        b = pd.read_csv(URL_BAZA)
        o = pd.read_csv(URL_OPLATY)
        b.columns = b.columns.str.strip()
        def clean(v):
            s = re.sub(r'[^\d.]', '', str(v).replace(',', '.'))
            return float(s) if s else 0.0
        for c in ['Eksport', 'Import', 'Postoj']: 
            if c in b.columns: b[c] = b[c].apply(clean)
        o['Wartosc'] = o['Wartosc'].apply(clean)
        return b, o
    except:
        return pd.DataFrame(), pd.DataFrame()

df_baza, df_oplaty = fetch_data()
cfg = dict(zip(df_oplaty['Parametr'], df_oplaty['Wartosc'])) if not df_oplaty.empty else {}

# --- SIDEBAR ---
with st.sidebar:
    st.markdown('<div class="brand-container"><div class="brand-logo"><span class="brand-v">V</span> SQM VENTAGE</div></div>', unsafe_allow_html=True)
    st.markdown(f"👤 Zalogowany: **{st.session_state.user}**")
    
    menu = st.radio("NAWIGACJA", ["PLANOWANIE TRAS", "ADMIN TOOL"])
    
    st.markdown("---")
    if st.button("🚪 WYLOGUJ", use_container_width=True):
        st.session_state.auth = False
        st.session_state.user = ""
        st.rerun()

# --- MODUŁ: ADMIN TOOL ---
if menu == "ADMIN TOOL":
    st.title("⚙️ Panel Administratora")
    # Sztywne sprawdzenie czy użytkownik to admin (małe litery)
    current_user = st.session_state.user.lower()
    
    if current_user != "admin":
        st.error(f"Brak uprawnień. Zalogowano jako: '{st.session_state.user}'.")
        st.info("Ta sekcja wymaga uprawnień administratora.")
    else:
        st.success("Weryfikacja pomyślna. Masz pełny dostęp.")
        st.markdown(f"🔗 [Link do bazy Google Sheets](https://docs.google.com/spreadsheets/d/{SHEET_ID})")
        
        st.subheader("Aktualne stawki w systemie")
        st.dataframe(df_baza, use_container_width=True)
        
        st.subheader("Koszty stałe (ATA, Ferry, Parking)")
        st.table(df_oplaty)
    st.stop()

# --- MODUŁ: PLANOWANIE TRAS ---
st.markdown(f'<div class="route-header">KALKULACJA TRANSPORTU</div>', unsafe_allow_html=True)

with st.sidebar:
    st.markdown("### 🚛 PARAMETRY")
    target = st.selectbox("CEL", sorted(TRANSIT_DATA.keys()))
    trip_type = st.radio("TYP TRASY", ["PEŁNA (EXP+IMP)", "ONE-WAY"])
    mode = st.radio("ŁADUNEK", ["DEDYKOWANY", "DOŁADUNEK"])
    base_weight = st.number_input("WAGA (KG)", value=1000, step=100)
    real_weight = base_weight * 1.20
    d_start = st.date_input("MONTAŻ", datetime.now() + timedelta(days=7))

# Obliczenia logistyczne
caps = {"BUS": 1200, "SOLO": 5500, "FTL": 10500}
results = []
if not df_baza.empty:
    for v_type, cap in caps.items():
        res = df_baza[(df_baza['Miasto'] == target) & (df_baza['Typ_Pojazdu'] == v_type)]
        if not res.empty:
            r = res.mean(numeric_only=True)
            v_count = math.ceil(real_weight / cap)
            transit = TRANSIT_DATA.get(target, {}).get("BUS" if v_type=="BUS" else "FTL/SOLO", 2)
            
            exp_v = r['Eksport'] * (v_count if mode == "DEDYKOWANY" else real_weight/cap)
            imp_v = (r['Import'] * (v_count if mode == "DEDYKOWANY" else real_weight/cap)) if "PEŁNA" in trip_type else 0
            
            # Dodatki regionalne
            ata = (cfg.get('ATA_CARNET', 166) if target in ["Londyn", "Genewa"] else 0)
            ferry = (cfg.get('Ferry_UK', 450) if "Londyn" in target or "Manchester" in target else 0)
            
            total = exp_v + imp_v + ata + ferry
            results.append({
                "Pojazd": v_type, 
                "Szt": v_count, 
                "Total": total, 
                "transit": transit, 
                "load": min(100, (real_weight/(v_count*cap))*100)
            })

if results:
    best = min(results, key=lambda x: x['Total'])
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown(f"""
            <div class="hero-card">
                <div style='color:#ed8936; font-size:14px; font-weight:800;'>NAJLEPSZA OPCJA</div>
                <div class="main-price-value">€ {best['Total']:,.2f}</div>
                <div style='color:#94a3b8;'>
                    Sugerowane: {best['Szt']}x {best['Pojazd']} | Tranzyt: {best['transit']} dni | Wypełnienie: {best['load']:.0f}%
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        st.subheader("Porównanie kosztów")
        st.dataframe(pd.DataFrame(results)[["Pojazd", "Szt", "Total", "load"]].style.format({"Total": "€ {:.2f}", "load": "{:.1f}%"}))
    
    with col2:
        st.info(f"📅 Planowany wyjazd: {(d_start - timedelta(days=best['transit']+1)).strftime('%Y-%m-%d')}")
        b_pos = CITY_COORDS["Komorniki (Baza)"]
        d_pos = CITY_COORDS.get(target, [50, 15])
        st.map(pd.DataFrame({'lat': [b_pos[0], d_pos[0]], 'lon': [b_pos[1], d_pos[1]]}))
