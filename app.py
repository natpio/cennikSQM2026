import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import re
import hashlib
import math
import numpy as np
import pydeck as pdk

# --- 1. KONFIGURACJA ZASOBÓW I ARKUSZY ---
SHEET_ID = "1sYlXP6WVzPE09qfmydQYQNsjiZcDgRSJGyWoXfjmkDY"
URL_BAZA = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=CENNIK_BAZA"
URL_OPLATY = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=OPLATY_STALE"
URL_USERS = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=USERS"

# Baza czasów tranzytu (dni)
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

# Współrzędne geograficzne dla mapy
CITY_COORDS = {
    "Komorniki (Baza)": [52.3358, 16.8122], "Amsterdam": [52.3702, 4.8952], 
    "Barcelona": [41.3851, 2.1734], "Bazylea": [47.5596, 7.5886], "Berlin": [52.5200, 13.4050],
    "Bruksela": [50.8503, 4.3517], "Budapeszt": [47.4979, 19.0402], "Cannes / Nicea": [43.5528, 7.0174],
    "Frankfurt nad Menem": [50.1109, 8.6821], "Gdańsk": [54.3520, 18.6466], "Genewa": [46.2044, 6.1432],
    "Hamburg": [53.5511, 9.9937], "Hannover": [52.3759, 9.7320], "Kielce": [50.8660, 20.6286],
    "Kolonia / Dusseldorf": [51.2277, 6.7735], "Kopenhaga": [55.6761, 12.5683], "Lipsk": [51.3397, 12.3731],
    "Liverpool": [53.4084, -2.9916], "Lizbona": [38.7223, -9.1393], "Londyn": [51.5074, -0.1276],
    "Lyon": [45.7640, 4.8357], "Madryt": [40.4168, -3.7038], "Manchester": [53.4808, -2.2426],
    "Mediolan": [45.4642, 9.1900], "Monachium": [48.1351, 11.5820], "Norymberga": [49.4521, 11.0767],
    "Paryż": [48.8566, 2.3522], "Praga": [50.0755, 14.4378], "Rzym": [41.9028, 12.4964],
    "Sewilla": [37.3891, -5.9845], "Sofia": [42.6977, 23.3219], "Sztokholm": [59.3293, 18.0686],
    "Tuluza": [43.6047, 1.4442], "Warszawa": [52.2297, 21.0122], "Wiedeń": [48.2082, 16.3738]
}

# --- 2. KONFIGURACJA STRONY ---
st.set_page_config(page_title="SQM VENTAGE v5.1.7", layout="wide", initial_sidebar_state="expanded")

# --- 3. PEŁNY ARKUSZ STYLÓW CSS ---
st.markdown("""
    <style>
    /* Globalne tło */
    .stApp { background-color: #05070a !important; }
    
    /* Sidebar */
    [data-testid="stSidebar"] { background-color: #0f172a !important; border-right: 1px solid #1e293b; }
    [data-testid="stSidebar"] .stMarkdown p { color: #94a3b8; font-size: 0.8rem; font-weight: 600; text-transform: uppercase; }

    /* Inputy i Selecty */
    div[data-baseweb="select"] > div, div[data-baseweb="input"] > div, 
    .stNumberInput div[data-baseweb="input"], .stDateInput div[data-baseweb="input"] {
        background-color: #1e293b !important; color: #ffffff !important; border: 1px solid #334155 !important;
    }
    input { color: #ffffff !important; -webkit-text-fill-color: #ffffff !important; }

    /* Branding */
    .brand-container { padding: 10px 0 20px 0; text-align: center; border-bottom: 1px solid #1e293b; margin-bottom: 20px; }
    .brand-logo { font-size: 22px; font-weight: 900; color: #ffffff; display: flex; align-items: center; justify-content: center; gap: 10px; }
    .brand-v { background: #ed8936; color: #000; padding: 2px 10px; border-radius: 4px; font-style: italic; }

    /* Widgety wagowe */
    .weight-info { background: rgba(237, 137, 54, 0.1); border: 1px solid #ed8936; padding: 12px; border-radius: 8px; color: #ed8936; font-size: 0.9rem; font-weight: bold; margin-bottom: 20px; text-align: center; }

    /* Karty Wyników */
    .route-header { font-size: 32px !important; font-weight: 900; color: #ffffff; border-bottom: 4px solid #ed8936; margin-bottom: 30px; padding-bottom: 10px; letter-spacing: -1px; }
    .hero-card { background: linear-gradient(145deg, #1e293b, #0f172a); border: 1px solid #334155; border-radius: 24px; padding: 35px; margin-bottom: 30px; box-shadow: 0 10px 30px rgba(0,0,0,0.5); }
    .main-price-value { color: #ffffff; font-size: 72px; font-weight: 950; margin: 10px 0; letter-spacing: -2px; }
    
    /* Rozbicie kosztów */
    .breakdown-container { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 20px; margin: 25px 0; padding: 25px 0; border-top: 1px solid rgba(255,255,255,0.1); border-bottom: 1px solid rgba(255,255,255,0.1); }
    .breakdown-item { font-size: 13px; color: #94a3b8; }
    .breakdown-item b { color: #ffffff; font-size: 17px; display: block; margin-top: 5px; }

    /* Analiza porównawcza */
    .alt-card { background: #0f172a; border-left: 5px solid #334155; padding: 20px 25px; margin-bottom: 15px; border-radius: 12px; display: flex; justify-content: space-between; align-items: center; transition: 0.3s; }
    .alt-best { border-left-color: #ed8936; background: rgba(237, 137, 54, 0.05); }
    .price-tag { color: #ed8936; font-size: 22px; font-weight: 900; }
    </style>
""", unsafe_allow_html=True)

# --- 4. FUNKCJE POMOCNICZE ---
def make_hash(p):
    return hashlib.sha256(p.strip().encode()).hexdigest()

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
    except:
        return pd.DataFrame(), pd.DataFrame()

@st.cache_data(ttl=60)
def load_users():
    try:
        df = pd.read_csv(URL_USERS)
        df.columns = df.columns.str.strip()
        return dict(zip(df['username'].astype(str), df['password'].astype(str)))
    except:
        return {"admin": "f3e99d9459eeb7ffc4cd407d890fbf1db011208fa12d8edc501a7ec26da106a3"}

# --- 5. SYSTEM LOGOWANIA (NAPRAWIONY) ---
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    _, col, _ = st.columns([1, 1.2, 1])
    with col:
        st.markdown("<div style='text-align:center; margin-top:100px;'><h1 style='color:white; font-size:40px; font-weight:900;'>SQM <span style='color:#ed8936;'>VENTAGE</span></h1></div>", unsafe_allow_html=True)
        u_in = st.text_input("Użytkownik", key="login_user")
        p_in = st.text_input("Hasło", type="password", key="login_pass")
        if st.button("ZALOGUJ DO SYSTEMU", use_container_width=True):
            users = load_users()
            if u_in in users and users[u_in] == make_hash(p_in):
                st.session_state.authenticated = True
                st.session_state.user_role = "admin" # Kluczowe: nadajemy rolę przy logowaniu
                st.session_state.current_user = u_in
                st.rerun()
            else:
                st.error("Nieprawidłowe dane logowania.")
    st.stop()

# --- 6. PRZYGOTOWANIE DANYCH ---
df_baza, df_oplaty = fetch_data()
cfg = dict(zip(df_oplaty['Parametr'], df_oplaty['Wartosc'])) if not df_oplaty.empty else {}

# --- 7. SIDEBAR (FILTRY) ---
with st.sidebar:
    st.markdown('<div class="brand-container"><div class="brand-logo"><span class="brand-v">V</span> SQM VENTAGE</div></div>', unsafe_allow_html=True)
    
    st.markdown("### Kierunek i Strategia")
    trip_type = st.radio("TYP TRANSPORTU", ["PEŁNA TRASA (EXP+IMP)", "TYLKO DOSTAWA (ONE-WAY)"])
    mode = st.radio("RODZAJ ŁADUNKU", ["DEDYKOWANY", "DOŁADUNEK"])
    
    st.markdown("### Cel Podróży")
    target = st.selectbox("MIASTO DOCELOWE", sorted(TRANSIT_DATA.keys()))
    
    st.markdown("### Parametry Towaru")
    base_weight = st.number_input("WAGA NETTO (KG)", value=1000, step=100)
    real_weight = base_weight * 1.20 # Współczynnik bezpieczeństwa 20%
    st.markdown(f'<div class="weight-info">WAGA BRUTTO: {real_weight:,.0f} KG</div>', unsafe_allow_html=True)
    
    st.markdown("### Harmonogram")
    d_start = st.date_input("DATA MONTAŻU", datetime.now() + timedelta(days=7))
    days_stay = 0
    if trip_type == "PEŁNA TRASA (EXP+IMP)":
        d_end = st.date_input("DATA DEMONTAŻU", d_start + timedelta(days=4))
        days_stay = max(0, (d_end - d_start).days)

    if st.button("WYLOGUJ"):
        st.session_state.clear()
        st.rerun()

# --- 8. SILNIK OBLICZENIOWY ---
caps = {"BUS": 1200, "SOLO": 5500, "FTL": 10500}
results = []

if not df_baza.empty:
    for v_type, cap in caps.items():
        res = df_baza[(df_baza['Miasto'] == target) & (df_baza['Typ_Pojazdu'] == v_type)]
        if not res.empty:
            r = res.iloc[0]
            v_count = math.ceil(real_weight / cap)
            transit_days = TRANSIT_DATA.get(target, {}).get("BUS" if v_type=="BUS" else "FTL/SOLO", 2)
            
            # Koszty podstawowe
            exp_v = (r['Eksport'] * v_count if mode == "DEDYKOWANY" else r['Eksport'] * (real_weight/cap))
            imp_v = (r['Import'] * v_count if mode == "DEDYKOWANY" else r['Import'] * (real_weight/cap)) if trip_type != "TYLKO DOSTAWA (ONE-WAY)" else 0
            
            # Postój i parking
            stay_v = r['Postoj'] * days_stay * v_count
            park_v = (days_stay * cfg.get('PARKING_DAY', 30) * v_count)
            
            # Dodatki UK/CH
            ata_v = (cfg.get('ATA_CARNET', 166) if target in ["Londyn", "Genewa", "Liverpool", "Manchester"] else 0)
            ferry_v = (cfg.get('Ferry_UK', 450) if any(x in target for x in ["Londyn", "Liverpool", "Manchester"]) else 0)
            
            total = exp_v + imp_v + stay_v + park_v + ata_v + ferry_v
            
            results.append({
                "Pojazd": v_type, "Szt": v_count, "Total": total, "transit": transit_days,
                "load": min(100, (real_weight/(v_count*cap))*100),
                "exp": exp_v, "imp": imp_v, "stay": stay_v, "stay_rate": r['Postoj'], "parking": park_v, "ata": ata_v, "ferry": ferry_v
            })

# --- 9. WIDOK GŁÓWNY (DASHBOARD) ---
if results:
    best = min(results, key=lambda x: x['Total'])
    departure_date = d_start - timedelta(days=best['transit'] + 1)
    
    st.markdown(f'<div class="route-header">KOMORNIKI ➔ {target.upper()}</div>', unsafe_allow_html=True)
    
    col_left, col_right = st.columns([1.8, 1])
    
    with col_left:
        # Karta główna ceny
        b_html = f"<div class='breakdown-item'>Eksport: <b>€ {best['exp']:,.0f}</b></div>"
        if trip_type != "TYLKO DOSTAWA (ONE-WAY)":
            b_html += f"<div class='breakdown-item'>Import: <b>€ {best['imp']:,.0f}</b></div>"
        b_html += f"<div class='breakdown-item'>Postój ({days_stay} dni): <b>€ {best['stay']:,.0f}</b></div>"
        if best['parking'] > 0: b_html += f"<div class='breakdown-item'>Parking: <b>€ {best['parking']:,.0f}</b></div>"
        if best['ata'] > 0: b_html += f"<div class='breakdown-item'>Odprawa/ATA: <b>€ {best['ata']:,.0f}</b></div>"
        if best['ferry'] > 0: b_html += f"<div class='breakdown-item'>Prom: <b>€ {best['ferry']:,.0f}</b></div>"

        st.markdown(f"""
            <div class="hero-card">
                <div style='color:#ed8936; font-size:14px; font-weight:800; text-transform:uppercase;'>Szacunkowy Koszt Logistyki</div>
                <div class="main-price-value">€ {best['Total']:,.2f}</div>
                <div class="breakdown-container">{b_html}</div>
                <div style='display:grid; grid-template-columns: repeat(4, 1fr); gap:15px;'>
                    <div style='background:rgba(255,255,255,0.05); padding:15px; border-radius:15px; text-align:center;'>
                        <div style='color:#94a3b8; font-size:10px;'>TRANZYT</div><div style='color:white; font-size:20px; font-weight:900;'>{best['transit']} dni</div>
                    </div>
                    <div style='background:rgba(255,255,255,0.05); padding:15px; border-radius:15px; text-align:center;'>
                        <div style='color:#94a3b8; font-size:10px;'>AUTO</div><div style='color:white; font-size:20px; font-weight:900;'>{best['Pojazd']}</div>
                    </div>
                    <div style='background:rgba(255,255,255,0.05); padding:15px; border-radius:15px; text-align:center;'>
                        <div style='color:#94a3b8; font-size:10px;'>SZTUK</div><div style='color:white; font-size:20px; font-weight:900;'>{best['Szt']}</div>
                    </div>
                    <div style='background:rgba(255,255,255,0.05); padding:15px; border-radius:15px; text-align:center;'>
                        <div style='color:#94a3b8; font-size:10px;'>ŁADOWNOŚĆ</div><div style='color:white; font-size:20px; font-weight:900;'>{best['load']:.0f}%</div>
                    </div>
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        st.markdown("### 📊 OPCJE ALTERNATYWNE")
        for r in sorted(results, key=lambda x: x['Total']):
            is_best = "alt-best" if r['Pojazd'] == best['Pojazd'] else ""
            st.markdown(f"""
                <div class="alt-card {is_best}">
                    <div style='color:white;'><b>{r['Pojazd']}</b> <span style='color:#64748b; margin-left:10px;'>({r['Szt']} szt. | Ładunek: {r['load']:.0f}%)</span></div>
                    <div class="price-tag">€ {r['Total']:,.2f}</div>
                </div>
            """, unsafe_allow_html=True)

    with col_right:
        # MAPA EUROPY - CARTO (BEZ POTRZEBY TOKENA)
        s_pos = CITY_COORDS["Komorniki (Baza)"]
        e_pos = CITY_COORDS.get(target, [52.5, 13.4])
        
        arc_df = pd.DataFrame([{"start": [s_pos[1], s_pos[0]], "end": [e_pos[1], e_pos[0]]}])

        st.pydeck_chart(pdk.Deck(
            map_provider="carto", map_style="light",
            initial_view_state=pdk.ViewState(latitude=(s_pos[0]+e_pos[0])/2, longitude=(s_pos[1]+e_pos[1])/2, zoom=4, pitch=0),
            layers=[
                pdk.Layer("ArcLayer", data=arc_df, get_source_position="start", get_target_position="end", 
                          get_source_color=[237, 137, 54], get_target_color=[0, 0, 0], get_width=6),
                pdk.Layer("ScatterplotLayer", data=pd.DataFrame([{"p": [s_pos[1], s_pos[0]]}, {"p": [e_pos[1], e_pos[0]]}]),
                          get_position="p", get_color=[237, 137, 54], get_radius=40000)
            ]
        ))
        st.warning(f"🚚 **WYJAZD Z BAZY: {departure_date.strftime('%Y-%m-%d')}**")
        st.info("Obliczono jako: Dzień montażu - (tranzyt + 1 dzień zapasu).")
