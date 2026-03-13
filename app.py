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

st.set_page_config(page_title="SQM VENTAGE v5.0.6", layout="wide")

# --- CSS Z FIXEM DLA INPUTÓW I HTML ---
st.markdown("""
    <style>
    .stApp { background-color: #05070a !important; }
    [data-testid="stSidebar"] { background-color: #0f172a !important; border-right: 1px solid #1e293b; }

    /* Fix dla białych pól w sidebarze */
    div[data-baseweb="select"] > div, 
    div[data-baseweb="input"] > div,
    .stNumberInput div[data-baseweb="input"] {
        background-color: #1e293b !important;
        color: white !important;
        border: 1px solid #334155 !important;
    }
    
    /* Wymuszenie koloru tekstu w inputach */
    input {
        color: white !important;
        -webkit-text-fill-color: white !important;
    }

    /* Branding */
    .brand-container { padding: 10px 0 20px 0; text-align: center; border-bottom: 1px solid #1e293b; margin-bottom: 20px; }
    .brand-logo { font-family: 'Inter', sans-serif; font-size: 20px; font-weight: 900; color: #ffffff; display: flex; align-items: center; justify-content: center; gap: 10px; }
    .brand-v { background: #ed8936; color: #000; padding: 2px 8px; border-radius: 4px; font-style: italic; }
    .brand-ver { font-size: 10px; color: #94a3b8 !important; margin-top: 5px; }

    /* Nagłówek i Karty */
    .route-header { font-size: 30px !important; font-weight: 900; color: #ffffff; border-bottom: 3px solid #ed8936; margin-bottom: 25px; padding-bottom: 10px; }
    .hero-card { background: linear-gradient(145deg, #1e293b, #0f172a); border: 1px solid #334155; border-radius: 20px; padding: 30px; margin-bottom: 30px; }
    .main-price-value { color: #ffffff; font-size: 64px; font-weight: 950; line-height: 1.1; margin: 15px 0; }

    .breakdown-container { display: flex; flex-wrap: wrap; gap: 20px; margin: 20px 0; padding: 15px 0; border-top: 1px solid rgba(255,255,255,0.1); border-bottom: 1px solid rgba(255,255,255,0.1); }
    .breakdown-item { font-size: 14px; color: #94a3b8; }
    .breakdown-item b { color: #ffffff; font-size: 16px; }

    .alt-card { background: #0f172a; border-left: 5px solid #475569; padding: 18px 25px; margin-bottom: 12px; border-radius: 8px; display: flex; justify-content: space-between; align-items: center; }
    .alt-best { border-left-color: #ed8936; background: rgba(237, 137, 54, 0.1); }
    .price-tag { color: #ed8936; font-size: 20px; font-weight: 900; }
    
    /* Fix dla etykiet */
    [data-testid="stSidebar"] label p { color: #94a3b8 !important; font-weight: 700; text-transform: uppercase; font-size: 0.75rem; }
    </style>
""", unsafe_allow_html=True)

# --- PROSTE LOGOWANIE ---
if "authenticated" not in st.session_state: st.session_state.authenticated = False

if not st.session_state.authenticated:
    _, col, _ = st.columns([1, 1.2, 1])
    with col:
        st.markdown("<h2 style='text-align:center; color:white; margin-top:50px;'>SQM VENTAGE</h2>", unsafe_allow_html=True)
        u = st.text_input("Użytkownik")
        p = st.text_input("Hasło", type="password")
        if st.button("ZALOGUJ", use_container_width=True):
            if p == "sqm2024":
                st.session_state.authenticated = True; st.rerun()
    st.stop()

# --- DANE ---
@st.cache_data(ttl=60)
def fetch_data():
    try:
        b = pd.read_csv(URL_BAZA); o = pd.read_csv(URL_OPLATY); b.columns = b.columns.str.strip()
        def clean(v):
            s = re.sub(r'[^\d.]', '', str(v).replace(',', '.')); return float(s) if s else 0.0
        for c in ['Eksport', 'Import', 'Postoj']: 
            if c in b.columns: b[c] = b[c].apply(clean)
        o['Wartosc'] = o['Wartosc'].apply(clean)
        return b, o
    except: return pd.DataFrame(), pd.DataFrame()

df_baza, df_oplaty = fetch_data()
cfg = dict(zip(df_oplaty['Parametr'], df_oplaty['Wartosc'])) if not df_oplaty.empty else {}

# --- SIDEBAR ---
with st.sidebar:
    st.markdown('<div class="brand-container"><div class="brand-logo"><span class="brand-v">V</span> SQM VENTAGE</div><div class="brand-ver">SYSTEM LOGISTYCZNY VER. 5.0.6</div></div>', unsafe_allow_html=True)
    
    st.markdown("### 🚛 PARAMETRY")
    trip_type = st.radio("KIERUNEK", ["PEŁNA TRASA (EXP+IMP)", "TYLKO DOSTAWA (ONE-WAY)"])
    mode = st.radio("STRATEGIA", ["DEDYKOWANY", "DOŁADUNEK"])
    target = st.selectbox("CEL PODRÓŻY", sorted(TRANSIT_DATA.keys()))
    weight = st.number_input("WAGA (KG)", value=1000, step=500)
    
    st.markdown("### 📅 TERMINARZ")
    d_start = st.date_input("PIERWSZY DZIEŃ MONTAŻU", datetime.now() + timedelta(days=5))
    days_stay = 0
    if trip_type == "PEŁNA TRASA (EXP+IMP)":
        d_end = st.date_input("OSTATNI DZIEŃ DEMONTAŻU", d_start + timedelta(days=5))
        days_stay = max(0, (d_end - d_start).days)

    if st.button("🚪 WYLOGUJ", use_container_width=True):
        st.session_state.authenticated = False; st.rerun()

# --- OBLICZENIA ---
w_eff = weight * cfg.get('WAGA_BUFOR', 1.2)
caps = {"BUS": 1200, "SOLO": 5500, "FTL": 10500}
results = []

if not df_baza.empty:
    for v_type, cap in caps.items():
        res = df_baza[(df_baza['Miasto'] == target) & (df_baza['Typ_Pojazdu'] == v_type)]
        if not res.empty:
            r = res.mean(numeric_only=True)
            v_count = math.ceil(w_eff / cap)
            transit = TRANSIT_DATA.get(target, {}).get("BUS" if v_type=="BUS" else "FTL/SOLO", 2)
            
            exp_v = (r['Eksport'] * v_count if mode == "DEDYKOWANY" else r['Eksport'] * (w_eff/cap))
            imp_v = (r['Import'] * v_count if mode == "DEDYKOWANY" else r['Import'] * (w_eff/cap)) if trip_type != "TYLKO DOSTAWA (ONE-WAY)" else 0
            
            ata = (cfg.get('ATA_CARNET', 166) if target in ["Londyn", "Genewa", "Liverpool", "Manchester"] else 0)
            ferry = (cfg.get('Ferry_UK', 450) if any(x in target for x in ["Londyn", "Liverpool", "Manchester"]) else 0)
            park = (days_stay * cfg.get('PARKING_DAY', 30) * v_count)
            stay_v = r['Postoj'] * days_stay * v_count
            
            total = exp_v + imp_v + stay_v + park + ata + ferry
            results.append({
                "Pojazd": v_type, "Szt": v_count, "Total": total, "transit": transit, 
                "load": min(100, (w_eff/(v_count*cap))*100), "exp": exp_v, "imp": imp_v, 
                "stay": stay_v, "fees": ata + ferry + park
            })

# --- WIDOK ---
if results:
    best = min(results, key=lambda x: x['Total'])
    # Obliczanie sugerowanej daty wyjazdu (Data montażu - czas tranzytu - 1 dzień zapasu)
    suggested_departure = d_start - timedelta(days=best['transit'] + 1)
    
    st.markdown(f'<div class="route-header">KOMORNIKI ➔ {target.upper()}</div>', unsafe_allow_html=True)
    
    cl, cr = st.columns([1.8, 1])
    with cl:
        # KARTA GŁÓWNA - CAŁOŚĆ W JEDNYM ST.MARKDOWN
        imp_html = f'<div class="breakdown-item">Import: <b>€ {best["imp"]:,.0f}</b></div>' if trip_type != "TYLKO DOSTAWA (ONE-WAY)" else ""
        
        st.markdown(f"""
            <div class="hero-card">
                <div style='color:#ed8936; font-size:14px; font-weight:800; letter-spacing:1px;'>KOSZT SZACUNKOWY NETTO</div>
                <div class="main-price-value">€ {best['Total']:,.2f}</div>
                
                <div class="breakdown-container">
                    <div class="breakdown-item">Eksport: <b>€ {best['exp']:,.0f}</b></div>
                    {imp_html}
                    <div class="breakdown-item">Postój (montaż): <b>€ {best['stay']:,.0f}</b></div>
                    <div class="breakdown-item">Opłaty dodatkowe: <b>€ {best['fees']:,.0f}</b></div>
                </div>

                <div style='display:grid; grid-template-columns: repeat(4, 1fr); gap:15px;'>
                    <div style='background:rgba(255,255,255,0.05); padding:15px; border-radius:12px; text-align:center;'>
                        <div style='color:#94a3b8; font-size:10px; font-weight:700;'>TRANZYT</div>
                        <div style='color:white; font-size:20px; font-weight:900;'>{best['transit']} dni</div>
                    </div>
                    <div style='background:rgba(255,255,255,0.05); padding:15px; border-radius:12px; text-align:center;'>
                        <div style='color:#94a3b8; font-size:10px; font-weight:700;'>TARGI</div>
                        <div style='color:white; font-size:20px; font-weight:900;'>{days_stay} dni</div>
                    </div>
                    <div style='background:rgba(255,255,255,0.05); padding:15px; border-radius:12px; text-align:center;'>
                        <div style='color:#94a3b8; font-size:10px; font-weight:700;'>AUTO</div>
                        <div style='color:white; font-size:20px; font-weight:900;'>{best['Pojazd']}</div>
                    </div>
                    <div style='background:rgba(255,255,255,0.05); padding:15px; border-radius:12px; text-align:center;'>
                        <div style='color:#94a3b8; font-size:10px; font-weight:700;'>ŁADUNEK</div>
                        <div style='color:white; font-size:20px; font-weight:900;'>{best['load']:.0f}%</div>
                    </div>
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        st.markdown("### 📊 ANALIZA PORÓWNAWCZA")
        for r in sorted(results, key=lambda x: x['Total']):
            is_best = "alt-best" if r['Pojazd'] == best['Pojazd'] else ""
            st.markdown(f"""
                <div class="alt-card {is_best}">
                    <div style='color:white;'><b>{r['Pojazd']}</b> <small style='color:#94a3b8; margin-left:10px;'>({r['Szt']} szt. | Ładunek {r['load']:.0f}%)</small></div>
                    <div class="price-tag">€ {r['Total']:,.2f}</div>
                </div>
            """, unsafe_allow_html=True)

    with cr:
        b_pos, d_pos = CITY_COORDS["Komorniki (Baza)"], CITY_COORDS.get(target, [48.8, 2.3])
        st.map(pd.DataFrame({'lat': np.linspace(b_pos[0], d_pos[0], 25), 'lon': np.linspace(b_pos[1], d_pos[1], 25)}), color='#ed8936', size=15)
        # Sugerowana data wyjazdu pod mapą
        st.warning(f"🚚 **Sugerowana data wyjazdu:** {suggested_departure.strftime('%Y-%m-%d')}")
        st.caption(f"Wyliczenie: {best['transit']} dni tranzytu + 1 dzień buforu przed montażem ({d_start}).")
