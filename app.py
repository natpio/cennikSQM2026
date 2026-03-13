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

# Statyczne dane tranzytowe SQM (dni drogi)
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

# Koordynaty miast dla mapy
CITY_COORDS = {
    "Komorniki (Baza)": [52.3358, 16.8122], "Amsterdam": [52.3702, 4.8952], 
    "Berlin": [52.5200, 13.4050], "Londyn": [51.5074, -0.1276],
    "Paryż": [48.8566, 2.3522], "Wiedeń": [48.2082, 16.3738], 
    "Praga": [50.0755, 14.4378], "Genewa": [46.2044, 6.1432], 
    "Barcelona": [41.3851, 2.1734], "Monachium": [48.1351, 11.5820], 
    "Madryt": [40.4168, -3.7038], "Lizbona": [38.7223, -9.1393],
    "Rzym": [41.9028, 12.4964], "Sztokholm": [59.3293, 18.0686]
}

# Konfiguracja strony
st.set_page_config(page_title="SQM VENTAGE v12.1", layout="wide", initial_sidebar_state="expanded")

# --- CSS: DESIGN SYSTEM SQM ---
st.markdown("""
    <style>
    .stApp { background-color: #05070a !important; }
    [data-testid="stSidebar"] { background-color: #0f172a !important; border-right: 1px solid #1e293b; }
    
    /* Inputy i Selektory */
    div[data-baseweb="select"] > div, 
    div[data-baseweb="input"] > div,
    .stNumberInput div[data-baseweb="input"],
    .stDateInput div[data-baseweb="input"] {
        background-color: #1e293b !important;
        color: #ffffff !important;
        border: 1px solid #334155 !important;
    }
    input { color: #ffffff !important; -webkit-text-fill-color: #ffffff !important; }
    
    /* Nagłówki i Branding */
    .brand-container { padding: 10px 0 20px 0; text-align: center; border-bottom: 1px solid #1e293b; margin-bottom: 20px; }
    .brand-logo { font-family: 'Inter', sans-serif; font-size: 20px; font-weight: 900; color: #ffffff; display: flex; align-items: center; justify-content: center; gap: 10px; }
    .brand-v { background: #ed8936; color: #000; padding: 2px 8px; border-radius: 4px; font-style: italic; }
    .route-header { font-size: 30px !important; font-weight: 900; color: #ffffff; border-bottom: 3px solid #ed8936; margin-bottom: 25px; padding-bottom: 10px; }
    
    /* Karty wyników */
    .hero-card { background: linear-gradient(145deg, #1e293b, #0f172a); border: 1px solid #334155; border-radius: 20px; padding: 30px; margin-bottom: 30px; }
    .main-price-value { color: #ffffff; font-size: 64px; font-weight: 950; line-height: 1.1; margin: 15px 0; }
    .breakdown-container { display: flex; flex-wrap: wrap; gap: 20px; margin: 20px 0; padding: 15px 0; border-top: 1px solid rgba(255,255,255,0.1); border-bottom: 1px solid rgba(255,255,255,0.1); }
    .breakdown-item { font-size: 14px; color: #94a3b8; }
    .breakdown-item b { color: #ffffff; font-size: 16px; }
    
    /* Alternatywy */
    .alt-card { background: #0f172a; border-left: 5px solid #475569; padding: 18px 25px; margin-bottom: 12px; border-radius: 8px; display: flex; justify-content: space-between; align-items: center; }
    .alt-best { border-left-color: #ed8936; background: rgba(237, 137, 54, 0.1); }
    .price-tag { color: #ed8936; font-size: 20px; font-weight: 900; }
    
    /* Sidebar Labels */
    [data-testid="stSidebar"] label p { color: #94a3b8 !important; font-weight: 700; text-transform: uppercase; font-size: 0.75rem; }
    </style>
""", unsafe_allow_html=True)

# --- SYSTEM AUTORYZACJI (STABILNY) ---
def make_hash(p):
    return hashlib.sha256(p.strip().encode()).hexdigest()

@st.cache_data(ttl=300)
def load_users():
    try:
        df = pd.read_csv(URL_USERS)
        df.columns = df.columns.str.strip()
        return dict(zip(df['username'].astype(str), df['password'].astype(str)))
    except:
        # Fallback bezpieczeństwa
        return {"admin": "f3e99d9459eeb7ffc4cd407d890fbf1db011208fa12d8edc501a7ec26da106a3"}

user_db = load_users()

if "auth_status" not in st.session_state:
    st.session_state.auth_status = False
if "logged_user" not in st.session_state:
    st.session_state.logged_user = ""

# EKRAN LOGOWANIA
if not st.session_state.auth_status:
    _, col, _ = st.columns([1, 1.2, 1])
    with col:
        st.markdown("<div style='height:100px;'></div>", unsafe_allow_html=True)
        st.markdown("<h1 style='text-align:center; color:white;'>SQM VENTAGE</h1>", unsafe_allow_html=True)
        u = st.text_input("Użytkownik", key="u_field").strip()
        p = st.text_input("Hasło", type="password", key="p_field").strip()
        if st.button("ZALOGUJ DO SYSTEMU", use_container_width=True):
            if u in user_db and user_db[u] == make_hash(p):
                st.session_state.auth_status = True
                st.session_state.logged_user = u
                st.rerun()
            else:
                st.error("Nieprawidłowy login lub hasło.")
    st.stop()

# --- POBIERANIE DANYCH LOGISTYCZNYCH ---
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

# --- SIDEBAR: NAWIGACJA I PARAMETRY ---
with st.sidebar:
    st.markdown('<div class="brand-container"><div class="brand-logo"><span class="brand-v">V</span> SQM VENTAGE</div></div>', unsafe_allow_html=True)
    st.markdown(f"👤 Użytkownik: **{st.session_state.logged_user}**")
    
    menu = st.radio("MODUŁ SYSTEMU", ["📊 KALKULATOR TRAS", "⚙️ ADMIN PANEL"])
    
    st.markdown("---")
    
    if menu == "📊 KALKULATOR TRAS":
        st.markdown("### 🚛 PARAMETRY TRANSPORTU")
        trip_type = st.radio("KIERUNEK", ["PEŁNA TRASA (EXP+IMP)", "TYLKO DOSTAWA (ONE-WAY)"])
        mode = st.radio("STRATEGIA", ["DEDYKOWANY (FULL)", "DOŁADUNEK (PARTIAL)"])
        target = st.selectbox("CEL PODRÓŻY", sorted(TRANSIT_DATA.keys()))
        
        base_weight = st.number_input("WAGA PROJEKTU (KG)", value=1000, step=100)
        real_weight = base_weight * 1.20 
        
        st.markdown(f"""<div style='background:rgba(237,137,54,0.1); border:1px solid #ed8936; padding:10px; border-radius:5px; color:#ed8936; font-size:0.8rem;'>WAGA BRUTTO (+20%): {real_weight:,.0f} KG</div>""", unsafe_allow_html=True)
        
        d_start = st.date_input("DATA MONTAŻU", datetime.now() + timedelta(days=7))
        days_stay = 0
        if trip_type == "PEŁNA TRASA (EXP+IMP)":
            d_end = st.date_input("DATA DEMONTAŻU", d_start + timedelta(days=5))
            days_stay = max(0, (d_end - d_start).days)

    st.markdown("---")
    
    # WYLOGOWANIE (GWARANTOWANE DZIAŁANIE)
    if st.button("🚪 WYLOGUJ Z SYSTEMU", use_container_width=True):
        st.session_state.auth_status = False
        st.session_state.logged_user = ""
        st.rerun()

# --- WIDOK: ADMIN PANEL ---
if menu == "⚙️ ADMIN PANEL":
    st.title("Panel Administracyjny")
    if st.session_state.logged_user != "admin":
        st.warning("⚠️ Brak uprawnień do edycji bazy danych. Zaloguj się jako administrator.")
    else:
        st.info("💡 Zarządzanie stawkami odbywa się poprzez Google Sheets.")
        st.markdown(f"[Otwórz Arkusz Bazowy SQM](https://docs.google.com/spreadsheets/d/{SHEET_ID})")
        st.subheader("Aktualne Stawki (Podgląd)")
        st.dataframe(df_baza, use_container_width=True)
    st.stop()

# --- WIDOK: KALKULATOR (OBLICZENIA LOGISTYCZNE) ---
caps = {"BUS": 1200, "SOLO": 5500, "FTL": 10500}
results = []

if not df_baza.empty:
    for v_type, cap in caps.items():
        res = df_baza[(df_baza['Miasto'] == target) & (df_baza['Typ_Pojazdu'] == v_type)]
        if not res.empty:
            r = res.mean(numeric_only=True)
            v_count = math.ceil(real_weight / cap)
            transit_days = TRANSIT_DATA.get(target, {}).get("BUS" if v_type=="BUS" else "FTL/SOLO", 2)
            
            if mode == "DEDYKOWANY (FULL)":
                exp_v = r['Eksport'] * v_count
                imp_v = (r['Import'] * v_count) if trip_type != "TYLKO DOSTAWA (ONE-WAY)" else 0
            else:
                exp_v = r['Eksport'] * (real_weight / cap)
                imp_v = (r['Import'] * (real_weight / cap)) if trip_type != "TYLKO DOSTAWA (ONE-WAY)" else 0
            
            # Dodatki specyficzne
            ata = (cfg.get('ATA_CARNET', 166) if target in ["Londyn", "Genewa", "Liverpool", "Manchester"] else 0)
            ferry = (cfg.get('Ferry_UK', 450) if any(x in target for x in ["Londyn", "Liverpool", "Manchester"]) else 0)
            park = (days_stay * cfg.get('PARKING_DAY', 30) * v_count)
            stay_v = r['Postoj'] * days_stay * v_count
            
            total = exp_v + imp_v + stay_v + park + ata + ferry
            results.append({
                "Pojazd": v_type, "Szt": v_count, "Total": total, "transit": transit_days, 
                "load": min(100, (real_weight / (v_count * cap)) * 100), "exp": exp_v, "imp": imp_v, 
                "stay": stay_v, "fees": ata + ferry + park
            })

if results:
    best = min(results, key=lambda x: x['Total'])
    dep_date = d_start - timedelta(days=best['transit'] + 1)
    
    st.markdown(f'<div class="route-header">KOMORNIKI ➔ {target.upper()}</div>', unsafe_allow_html=True)
    
    cl, cr = st.columns([1.8, 1])
    with cl:
        # Główna Karta Wyniku
        imp_html = f'<div class="breakdown-item">Import: <b>€ {best["imp"]:,.0f}</b></div>' if "PEŁNA" in trip_type else ""
        st.markdown(f"""
            <div class="hero-card">
                <div style='color:#ed8936; font-size:14px; font-weight:800;'>KOSZT SZACUNKOWY NETTO</div>
                <div class="main-price-value">€ {best['Total']:,.2f}</div>
                <div class="breakdown-container">
                    <div class="breakdown-item">Eksport: <b>€ {best['exp']:,.0f}</b></div>
                    {imp_html}
                    <div class="breakdown-item">Postój: <b>€ {best['stay']:,.0f}</b></div>
                    <div class="breakdown-item">Opłaty: <b>€ {best['fees']:,.0f}</b></div>
                </div>
                <div style='display:grid; grid-template-columns: repeat(4, 1fr); gap:15px;'>
                    <div style='background:rgba(255,255,255,0.05); padding:15px; border-radius:12px; text-align:center;'>
                        <div style='color:#94a3b8; font-size:10px;'>TRANZYT</div>
                        <div style='color:white; font-size:18px; font-weight:900;'>{best['transit']} dni</div>
                    </div>
                    <div style='background:rgba(255,255,255,0.05); padding:15px; border-radius:12px; text-align:center;'>
                        <div style='color:#94a3b8; font-size:10px;'>ŁADUNEK</div>
                        <div style='color:white; font-size:18px; font-weight:900;'>{best['load']:.0f}%</div>
                    </div>
                    <div style='background:rgba(255,255,255,0.05); padding:15px; border-radius:12px; text-align:center;'>
                        <div style='color:#94a3b8; font-size:10px;'>AUTO</div>
                        <div style='color:white; font-size:18px; font-weight:900;'>{best['Pojazd']}</div>
                    </div>
                    <div style='background:rgba(255,255,255,0.05); padding:15px; border-radius:12px; text-align:center;'>
                        <div style='color:#94a3b8; font-size:10px;'>SZTUK</div>
                        <div style='color:white; font-size:18px; font-weight:900;'>{best['Szt']}</div>
                    </div>
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        st.markdown("### 📊 PORÓWNANIE TYPÓW TRANSPORTU")
        for r in sorted(results, key=lambda x: x['Total']):
            is_best = "alt-best" if r['Pojazd'] == best['Pojazd'] else ""
            st.markdown(f"""
                <div class="alt-card {is_best}">
                    <div style='color:white;'><b>{r['Pojazd']}</b> <small style='color:#94a3b8; margin-left:10px;'>({r['Szt']} szt. | Załadunek {r['load']:.0f}%)</small></div>
                    <div class="price-tag">€ {r['Total']:,.2f}</div>
                </div>
            """, unsafe_allow_html=True)

    with cr:
        # Mapa i Planowanie
        b_pos, d_pos = CITY_COORDS["Komorniki (Baza)"], CITY_COORDS.get(target, [48.8, 2.3])
        map_df = pd.DataFrame({'lat': np.linspace(b_pos[0], d_pos[0], 25), 'lon': np.linspace(b_pos[1], d_pos[1], 25)})
        st.map(map_df, color='#ed8936', size=20)
        
        st.success(f"🗓️ **PLANOWANY WYJAZD: {dep_date.strftime('%Y-%m-%d')}**")
        st.info(f"Kalkulacja uwzględnia {best['transit']} dni jazdy + 1 dzień bufora.")
else:
    st.error("⚠️ Brak danych dla wybranego miasta w bazie Google Sheets.")
