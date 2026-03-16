import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import re
import hashlib
import math
import numpy as np
import pydeck as pdk

# --- 1. KONFIGURACJA ZASOBÓW (GOOGLE SHEETS) ---
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
st.set_page_config(page_title="SQM VENTAGE v5.2.8", layout="wide", initial_sidebar_state="expanded")

# --- 3. STYLE CSS (NAPRAWA ZLEWANIA SIĘ TEKSTU) ---
st.markdown("""
    <style>
    .stApp { background-color: #05070a !important; }
    
    /* SIDEBAR - EKSTREMALNY KONTRAST DLA ETYKIET */
    [data-testid="stSidebar"] { 
        background-color: #0f172a !important; 
        border-right: 1px solid #334155; 
    }
    
    /* Wymuszenie koloru białego dla wszystkich tekstów kontrolnych */
    [data-testid="stSidebar"] label, 
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] .stMarkdown p,
    [data-testid="stSidebar"] .stSelectbox p,
    [data-testid="stSidebar"] div[data-baseweb="select"] span {
        color: #ffffff !important;
        font-weight: 700 !important;
        opacity: 1 !important;
    }

    /* Naprawa czarnych napisów w radio buttonach */
    [data-testid="stSidebar"] .stRadio label p {
        color: #ffffff !important;
        font-weight: 500 !important;
    }

    /* Naprawa czarnych napisów w inputach (daty, liczby) */
    [data-testid="stSidebar"] input {
        color: #ffffff !important;
        background-color: #1e293b !important;
        -webkit-text-fill-color: #ffffff !important;
    }

    /* GŁÓWNY PANEL - KARTA WYNIKÓW */
    .route-header { font-size: 32px !important; font-weight: 900; color: #ffffff; border-bottom: 4px solid #ed8936; margin-bottom: 30px; padding-bottom: 10px; }
    .hero-card { background: linear-gradient(145deg, #1e293b, #0f172a); border: 1px solid #334155; border-radius: 24px; padding: 35px; margin-bottom: 30px; }
    .main-price-value { color: #ffffff; font-size: 72px; font-weight: 950; margin: 10px 0; line-height: 1; }
    
    /* SZCZEGÓŁOWE ROZBICIE KOSZTÓW */
    .breakdown-grid { 
        display: grid; 
        grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); 
        gap: 25px; 
        margin: 30px 0; 
        padding: 25px 0; 
        border-top: 1px solid rgba(255,255,255,0.1); 
        border-bottom: 1px solid rgba(255,255,255,0.1); 
    }
    .cost-item { font-size: 12px; color: #94a3b8; text-transform: uppercase; letter-spacing: 1px; }
    .cost-item b { color: #ffffff; font-size: 20px; display: block; margin-top: 5px; font-weight: 900; }
    
    /* BOX PARAMETRÓW NA DOLE */
    .stat-container { display: flex; gap: 15px; margin-top: 20px; }
    .stat-pill { 
        background: rgba(237, 137, 54, 0.15); 
        border: 1px solid #ed8936; 
        padding: 8px 15px; 
        border-radius: 8px; 
        color: #ed8936; 
        font-weight: 800;
        font-size: 13px;
    }

    .alt-card { background: #0f172a; border-left: 5px solid #334155; padding: 20px 25px; margin-bottom: 15px; border-radius: 12px; display: flex; justify-content: space-between; align-items: center; }
    .alt-best { border-left-color: #ed8936; background: rgba(237, 137, 54, 0.05); }
    .price-tag { color: #ed8936; font-size: 22px; font-weight: 900; }
    </style>
""", unsafe_allow_html=True)

# --- 4. FUNKCJE ---
def make_hash(password): return hashlib.sha256(password.strip().encode()).hexdigest()

@st.cache_data(ttl=60)
def fetch_data():
    try:
        b = pd.read_csv(URL_BAZA); o = pd.read_csv(URL_OPLATY)
        b.columns = b.columns.str.strip(); o.columns = o.columns.str.strip()
        def clean_val(v):
            if pd.isna(v): return 0.0
            s = re.sub(r'[^\d.]', '', str(v).replace(',', '.')); return float(s) if s else 0.0
        for col in ['Eksport', 'Import', 'Postoj']:
            if col in b.columns: b[col] = b[col].apply(clean_val)
        if 'Wartosc' in o.columns: o['Wartosc'] = o['Wartosc'].apply(clean_val)
        return b, o
    except: return pd.DataFrame(), pd.DataFrame()

@st.cache_data(ttl=60)
def load_users():
    try:
        df = pd.read_csv(URL_USERS); df.columns = df.columns.str.strip()
        return dict(zip(df['username'].astype(str), df['password'].astype(str)))
    except: return {"admin": "f3e99d9459eeb7ffc4cd407d890fbf1db011208fa12d8edc501a7ec26da106a3"}

# --- 5. LOGOWANIE ---
if "authenticated" not in st.session_state: st.session_state.authenticated = False

if not st.session_state.authenticated:
    _, col_log, _ = st.columns([1, 1.2, 1])
    with col_log:
        st.markdown("<div style='text-align:center; margin-top:100px;'><h1 style='color:white;'>SQM <span style='color:#ed8936;'>VENTAGE</span></h1></div>", unsafe_allow_html=True)
        u_input = st.text_input("Użytkownik", key="login_u")
        p_input = st.text_input("Hasło", type="password", key="login_p")
        if st.button("ZALOGUJ DO SYSTEMU", use_container_width=True):
            user_db = load_users()
            if u_input in user_db and user_db[u_input] == make_hash(p_input):
                st.session_state.authenticated = True
                st.session_state.current_user = u_input
                st.rerun()
            else: st.error("Błędny login lub hasło.")
    st.stop()

# --- 6. PRZYGOTOWANIE DANYCH ---
df_baza, df_oplaty = fetch_data()
cfg = dict(zip(df_oplaty['Parametr'], df_oplaty['Wartosc'])) if not df_oplaty.empty else {}

# --- 7. SIDEBAR ---
with st.sidebar:
    st.markdown('<div style="text-align:center; margin-bottom:20px;"><div class="brand-logo"><span class="brand-v">V</span> SQM VENTAGE</div></div>', unsafe_allow_html=True)
    
    trip_type = st.radio("KIERUNEK", ["PEŁNA TRASA (EXP+IMP)", "TYLKO DOSTAWA (ONE-WAY)"])
    mode = st.radio("STRATEGIA", ["DEDYKOWANY", "DOŁADUNEK"])
    target_city = st.selectbox("MIEJSCE DOCELOWE", sorted(TRANSIT_DATA.keys()))
    
    st.markdown("---")
    weight_netto = st.number_input("WAGA NETTO (KG)", value=1000, step=100)
    weight_brutto = weight_netto * 1.20
    
    st.markdown(f"""
        <div style="background:rgba(237,137,54,0.1); border:1px solid #ed8936; padding:15px; border-radius:10px; color:#ed8936; text-align:center;">
            <div style="font-size:10px; font-weight:bold;">BRUTTO (ESTYMACJA)</div>
            <div style="font-size:22px; font-weight:900;">{weight_brutto:,.0f} KG</div>
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    date_start = st.date_input("DZIEŃ MONTAŻU", datetime.now() + timedelta(days=7))
    days_stay = 0
    if trip_type == "PEŁNA TRASA (EXP+IMP)":
        date_end = st.date_input("DZIEŃ DEMONTAŻU", date_start + timedelta(days=4))
        days_stay = max(0, (date_end - date_start).days)
        
    if st.button("🚪 WYLOGUJ", use_container_width=True):
        st.session_state.clear()
        st.rerun()

# --- 8. LOGIKA OBLICZEŃ ---
v_types = {"BUS": 1200, "SOLO": 5500, "FTL": 10500}
final_results = []

if not df_baza.empty:
    for v_name, v_cap in v_types.items():
        match = df_baza[(df_baza['Miasto'] == target_city) & (df_baza['Typ_Pojazdu'] == v_name)]
        if not match.empty:
            row = match.iloc[0]
            count = math.ceil(weight_brutto / v_cap)
            tr = TRANSIT_DATA.get(target_city, {}).get("BUS" if v_name=="BUS" else "FTL/SOLO", 2)
            
            # Obliczenia szczegółowe
            c_exp = row['Eksport'] * (count if mode == "DEDYKOWANY" else (weight_brutto / v_cap))
            c_imp = (row['Import'] * (count if mode == "DEDYKOWANY" else (weight_brutto / v_cap))) if trip_type != "TYLKO DOSTAWA (ONE-WAY)" else 0
            c_stay = row['Postoj'] * days_stay * count
            c_park = (days_stay * cfg.get('PARKING_DAY', 30) * count)
            
            # ATA i Promy (tylko UK i Szwajcaria)
            c_ata = (cfg.get('ATA_CARNET', 166) if target_city in ["Londyn", "Genewa", "Liverpool", "Manchester"] else 0)
            c_ferry = (cfg.get('Ferry_UK', 450) if any(x in target_city for x in ["Londyn", "Liverpool", "Manchester"]) else 0)
            
            total = c_exp + c_imp + c_stay + c_park + c_ata + c_ferry
            
            final_results.append({
                "v": v_name, "qty": count, "total": total, "tr": tr,
                "util": min(100, (weight_brutto / (count * v_cap)) * 100),
                "brk": {
                    "Eksport": c_exp, "Import": c_imp, "Postój": c_stay, 
                    "Parking/Hotel": c_park, "Karnet ATA": c_ata, "Promy": c_ferry
                }
            })

# --- 9. WIDOK GŁÓWNY ---
if st.session_state.current_user == "admin":
    tab_calc, tab_admin = st.tabs(["🚀 KALKULATOR", "⚙️ ADMIN TOOL"])
else:
    tab_calc, tab_admin = st.container(), None

with tab_calc:
    if final_results:
        best = min(final_results, key=lambda x: x['total'])
        dep_date = date_start - timedelta(days=best['tr'] + 1)
        
        st.markdown(f'<div class="route-header">KOMORNIKI ➔ {target_city.upper()}</div>', unsafe_allow_html=True)
        
        c_left, c_right = st.columns([1.8, 1])
        
        with c_left:
            # Budowanie rozbicia kosztów (tylko te, które są > 0)
            costs_html = "".join([f"<div class='cost-item'>{k}<b>€ {v:,.0f}</b></div>" for k, v in best['brk'].items() if v > 0])
            
            st.markdown(f"""
                <div class="hero-card">
                    <div style="color:#ed8936; font-size:13px; font-weight:800; letter-spacing:1px;">KOSZT SZACUNKOWY NETTO</div>
                    <div class="main-price-value">€ {best['total']:,.2f}</div>
                    <div class="breakdown-grid">{costs_html}</div>
                    <div class="stat-container">
                        <div class="stat-pill">🚛 {best['v']} x{best['qty']}</div>
                        <div class="stat-pill">⏱️ TRANZYT: {best['tr']} DNI</div>
                        <div class="stat-pill">📦 ŁADUNEK: {best['util']:.0f}%</div>
                        <div class="stat-pill">📅 WYJAZD: {dep_date.strftime('%d.%m')}</div>
                    </div>
                </div>
            """, unsafe_allow_html=True)
            
            st.markdown("### 📊 ANALIZA POZOSTAŁYCH OPCJI")
            for res in sorted(final_results, key=lambda x: x['total']):
                is_win = "alt-best" if res['v'] == best['v'] else ""
                st.markdown(f'<div class="alt-card {is_win}"><div><b>{res["v"]}</b> ({res["qty"]} szt. | utylizacja {res["util"]:.0f}%)</div><div class="price-tag">€ {res["total"]:,.2f}</div></div>', unsafe_allow_html=True)
        
        with c_right:
            s_c, e_c = CITY_COORDS["Komorniki (Baza)"], CITY_COORDS.get(target_city, [52, 13])
            st.pydeck_chart(pdk.Deck(map_provider="carto", map_style="light", 
                initial_view_state=pdk.ViewState(latitude=(s_c[0]+e_c[0])/2, longitude=(s_c[1]+e_c[1])/2, zoom=4),
                layers=[pdk.Layer("ArcLayer", data=pd.DataFrame([{"s": [s_c[1], s_c[0]], "e": [e_c[1], e_c[0]]}]), get_source_position="s", get_target_position="e", get_source_color=[237, 137, 54], get_width=5)]))
            st.warning(f"Zalecany wyjazd z bazy: **{dep_date.strftime('%Y-%m-%d')}** (Biorąc pod uwagę {best['tr']} dni tranzytu + 1 dzień zapasu).")

# --- TAB 2: ADMIN ---
if tab_admin is not None:
    with tab_admin:
        st.header("⚙️ Zarządzanie SQM VENTAGE")
        st.dataframe(df_baza, use_container_width=True)
        st.link_button("📂 EDYTUJ GOOGLE SHEETS", f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit")
        if st.button("🔄 SYNCHRONIZUJ DANE"): st.cache_data.clear(); st.rerun()
