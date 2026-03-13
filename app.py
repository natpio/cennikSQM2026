import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import re
import hashlib
import extra_streamlit_components as stx
import math
import numpy as np

# --- CONFIG & DATA ---
SHEET_ID = "1sYlXP6WVzPE09qfmydQYQNsjiZcDgRSJGyWoXfjmkDY"
URL_BAZA = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=CENNIK_BAZA"
URL_OPLATY = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=OPLATY_STALE"
URL_USERS = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=USERS"

# TWOJA TABELA CZASÓW (image_bd2e11.png)
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
    "Zurych": [47.3769, 8.5417], "Barcelona": [41.3851, 2.1734],
    "Monachium": [48.1351, 11.5820], "Mediolan": [45.4642, 9.1900],
    "Madryt": [40.4168, -3.7038], "Lizbona": [38.7223, -9.1393],
    "Rzym": [41.9028, 12.4964], "Sztokholm": [59.3293, 18.0686]
}

st.set_page_config(page_title="SQM LOGISTICS v15.2", layout="wide")

# --- CSS ---
st.markdown("""
    <style>
    .stApp { background-color: #05070a !important; }
    .route-header { font-size: 38px !important; font-weight: 900; color: #ffffff; border-bottom: 5px solid #ed8936; margin-bottom: 25px; }
    .hero-card { background: linear-gradient(145deg, #0f172a, #1e293b); border: 2px solid #334155; border-radius: 20px; padding: 35px; }
    .main-price-value { color: #ffffff; font-size: 100px; font-weight: 950; line-height: 0.85; margin: 20px 0; }
    .data-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin-top: 25px; }
    .data-item { background: rgba(255,255,255,0.08); padding: 20px; border-radius: 12px; border: 1px solid rgba(255,255,255,0.1); }
    .data-label { color: #94a3b8; font-size: 11px; font-weight: 700; text-transform: uppercase; }
    .data-value { color: #ffffff; font-size: 24px; font-weight: 900; }
    .cost-row { display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid #1e293b; font-size: 15px; }
    .cost-n { color: #94a3b8; }
    .cost-v { color: #ffffff; font-weight: 700; }
    </style>
""", unsafe_allow_html=True)

# --- AUTH & DATA LOADING ---
def make_hash(p): return hashlib.sha256(p.strip().encode()).hexdigest()
cookie_manager = stx.CookieManager()

@st.cache_data(ttl=60)
def fetch_logs():
    b = pd.read_csv(URL_BAZA); o = pd.read_csv(URL_OPLATY); b.columns = b.columns.str.strip()
    if 'Dostawca' in b.columns: b = b[~b['Dostawca'].str.contains('SQM|Własny|Wlasny', case=False, na=False)]
    def clean(v):
        s = re.sub(r'[^\d.]', '', str(v).replace(',', '.')); return float(s) if s else 0.0
    for c in ['Eksport', 'Import', 'Postoj']: b[c] = b[c].apply(clean)
    o['Wartosc'] = o['Wartosc'].apply(clean)
    return b, o

df_baza, df_oplaty = fetch_logs()
cfg = dict(zip(df_oplaty['Parametr'], df_oplaty['Wartosc']))

# --- SIDEBAR ---
with st.sidebar:
    st.image("https://www.sqm.pl/wp-content/themes/sqm/img/logo-sqm.png", width=120)
    mode = st.radio("STRATEGIA", ["DEDYKOWANY", "DOŁADUNEK"])
    target = st.selectbox("MIASTO DOCELOWE", sorted(TRANSIT_DATA.keys()))
    weight = st.number_input("WAGA SPRZĘTU (kg)", value=1500, step=500)
    d_start = st.date_input("PIERWSZY DZIEŃ MONTAŻU", datetime.now() + timedelta(days=7))
    d_end = st.date_input("OSTATNI DZIEŃ MONTAŻU", datetime.now() + timedelta(days=10))
    days_stay = max(0, (d_end - d_start).days)

# --- CALCULATIONS ---
w_eff = weight * cfg.get('WAGA_BUFOR', 1.2)
caps = {"BUS": 1200, "SOLO": 5500, "FTL": 10500}
results = []

for v_type, cap in caps.items():
    res = df_baza[(df_baza['Miasto'] == target) & (df_baza['Typ_Pojazdu'] == v_type)]
    if not res.empty:
        r = res.mean(numeric_only=True)
        v_count = math.ceil(w_eff / cap)
        
        # POBIERANIE CZASU Z TWOJEJ TABELI
        t_key = "BUS" if v_type == "BUS" else "FTL/SOLO"
        transit_days = TRANSIT_DATA.get(target, {}).get(t_key, 2)
        
        exp = (r['Eksport'] * v_count if mode == "DEDYKOWANY" else r['Eksport'] * (w_eff/cap))
        imp = (r['Import'] * v_count if mode == "DEDYKOWANY" else r['Import'] * (w_eff/cap))
        ata = (cfg.get('ATA_CARNET', 166) if target in ["Londyn", "Genewa", "Zurych", "Liverpool", "Manchester"] else 0)
        ferry = (cfg.get('Ferry_UK', 450) if target in ["Londyn", "Liverpool", "Manchester"] else 0)
        parking = (days_stay * cfg.get('PARKING_DAY', 30) * v_count)
        stay_cost = r['Postoj'] * days_stay * v_count
        
        results.append({
            "Pojazd": v_type, "Szt": v_count, "Total": exp+imp+stay_cost+parking+ata+ferry, 
            "exp": exp, "imp": imp, "stay": stay_cost, "park": parking, "ata": ata, 
            "ferry": ferry, "transit": transit_days, "load": min(100, (w_eff/(v_count*cap))*100)
        })

if results:
    best = min(results, key=lambda x: x['Total'])
    st.markdown(f'<div class="route-header">LOGISTYKA: KOMORNIKI ➔ {target.upper()}</div>', unsafe_allow_html=True)
    
    cl, cr = st.columns([1.8, 1])
    with cl:
        st.markdown(f"""
            <div class="hero-card">
                <div class="main-price-value">€ {best['Total']:,.2f}</div>
                <div class="data-grid">
                    <div class="data-item"><div class="data-label">Tranzyt (Tabela)</div><div class="data-value">{best['transit']} dni</div></div>
                    <div class="data-item"><div class="data-label">Dni na miejscu</div><div class="data-value">{days_stay} dni</div></div>
                    <div class="data-item"><div class="data-label">Pojazd</div><div class="data-value">{best['Pojazd']}</div></div>
                    <div class="data-item"><div class="data-label">Auta</div><div class="data-value">{best['Szt']} szt.</div></div>
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        st.write("### 📊 SZCZEGÓŁY KOSZTÓW:")
        s1, s2 = st.columns(2)
        with s1:
            st.markdown(f'<div class="cost-row"><span class="cost-n">Eksport:</span><span class="cost-v">€ {best["exp"]:,.2f}</span></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="cost-row"><span class="cost-n">Import:</span><span class="cost-v">€ {best["imp"]:,.2f}</span></div>', unsafe_allow_html=True)
        with s2:
            st.markdown(f'<div class="cost-row"><span class="cost-n">Postój (Montaż):</span><span class="cost-v">€ {best["stay"]:,.2f}</span></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="cost-row"><span class="cost-n">Opłaty (ATA/Ferry/Park):</span><span class="cost-v">€ {best["ata"]+best["ferry"]+best["park"]:,.2f}</span></div>', unsafe_allow_html=True)

    with cr:
        b_pos = CITY_COORDS["Komorniki (Baza)"]
        d_pos = CITY_COORDS.get(target, [48.8, 2.3])
        path_df = pd.DataFrame({'lat': np.linspace(b_pos[0], d_pos[0], 20), 'lon': np.linspace(b_pos[1], d_pos[1], 20)})
        st.write("### 📍 TRASA")
        st.map(path_df, color='#ed8936', size=15)
        
        st.info(f"Rekomendacja: Załadunek w Komornikach min. **{best['transit']} dni** przed montażem.")
