import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import re
import hashlib
import extra_streamlit_components as stx
import math
import numpy as np

# --- 1. KONFIGURACJA ZASOBÓW I GOOGLE SHEETS ---
SHEET_ID = "1sYlXP6WVzPE09qfmydQYQNsjiZcDgRSJGyWoXfjmkDY"
URL_BAZA = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=CENNIK_BAZA"
URL_OPLATY = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=OPLATY_STALE"
URL_USERS = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=USERS"

# --- 2. DANE TRANZYTOWE ---
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
    "Barcelona": [41.3851, 2.1734], "Genewa": [46.2044, 6.1432]
}

# --- 3. KONFIGURACJA STRONY ---
st.set_page_config(page_title="SQM LOGISTICS v16.4", layout="wide")

# --- 4. AGRESYWNY CSS FIX (NAPRAWA WIDOCZNOŚCI SIDEBARU) ---
st.markdown("""
    <style>
    /* Globalne tło aplikacji */
    .stApp { background-color: #05070a !important; }
    
    /* STYLIZACJA SIDEBARU */
    [data-testid="stSidebar"] {
        background-color: #0f172a !important;
        border-right: 1px solid #1e293b;
    }

    /* UKRYCIE ELEMENTÓW SYSTEMOWYCH */
    [data-testid="stSidebarNav"], header, [data-testid="stHeader"] {
        display: none !important;
    }

    /* WYMUSZENIE BIAŁEGO TEKSTU DLA ETYKIET */
    [data-testid="stSidebar"] label, 
    [data-testid="stSidebar"] .stMarkdown p, 
    [data-testid="stSidebar"] span {
        color: #ffffff !important;
        font-weight: 700 !important;
    }

    /* NAPRAWA PÓL WEJŚCIOWYCH - CIEMNE TŁO + BIAŁA CZCIONKA */
    /* Blokuje błąd, w którym Streamlit rysuje białe pola z białą czcionką */
    [data-testid="stSidebar"] div[data-baseweb="input"],
    [data-testid="stSidebar"] div[data-baseweb="select"],
    [data-testid="stSidebar"] .stSelectbox div,
    [data-testid="stSidebar"] input {
        background-color: #1e293b !important;
        color: #ffffff !important;
        border: 1px solid #334155 !important;
        border-radius: 8px !important;
        -webkit-text-fill-color: #ffffff !important;
    }
    
    /* Naprawa kontrastu dla list rozwijanych po kliknięciu */
    div[role="listbox"] ul {
        background-color: #1e293b !important;
    }
    div[role="option"] {
        color: #ffffff !important;
    }

    /* UI GŁÓWNEGO DASHBOARDU */
    .route-header { font-size: 32px !important; font-weight: 950; color: #ffffff; border-bottom: 4px solid #ed8936; margin-bottom: 30px; padding-bottom: 10px; }
    .hero-card { background: linear-gradient(145deg, #1e293b, #0f172a); border: 1px solid #334155; border-radius: 20px; padding: 35px; margin-bottom: 30px; }
    .main-price-val { color: #ffffff; font-size: 80px; font-weight: 950; line-height: 1; letter-spacing: -2px; }
    
    .data-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin-top: 25px; }
    .data-item { background: rgba(255,255,255,0.05); padding: 15px; border-radius: 12px; border: 1px solid rgba(255,255,255,0.1); }
    .data-label { color: #94a3b8; font-size: 10px; font-weight: 800; text-transform: uppercase; margin-bottom: 5px; }
    .data-value { color: #ffffff; font-size: 20px; font-weight: 900; }
    
    /* Przyciski */
    div.stButton > button {
        background-color: #ed8936 !important;
        color: white !important;
        font-weight: 800 !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 10px 20px !important;
    }
    </style>
""", unsafe_allow_html=True)

# --- 5. LOGOWANIE I AUTORYZACJA ---
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
        st.markdown("<h2 style='text-align:center; color:white; margin-top:80px;'>SQM LOGISTICS SYSTEM</h2>", unsafe_allow_html=True)
        u_in = st.text_input("Użytkownik", key="login_u")
        p_in = st.text_input("Hasło", type="password", key="login_p")
        if st.button("WEJDŹ DO SYSTEMU", use_container_width=True):
            if u_in in user_db and user_db[u_in] == make_hash(p_in):
                st.session_state.auth, st.session_state.user = True, u_in
                cookie_manager.set("sqm_session_v16", u_in, expires_at=datetime.now()+timedelta(days=7))
                st.rerun()
            else:
                st.error("Błędne dane logowania")
    st.stop()

# --- 6. POBIERANIE I PRZETWARZANIE DANYCH ---
@st.cache_data(ttl=60)
def fetch_data():
    b = pd.read_csv(URL_BAZA); o = pd.read_csv(URL_OPLATY); b.columns = b.columns.str.strip()
    if 'Dostawca' in b.columns:
        b = b[~b['Dostawca'].str.contains('SQM|Własny|Wlasny', case=False, na=False)]
    
    def clean_num(v):
        s = re.sub(r'[^\d.]', '', str(v).replace(',', '.')); return float(s) if s else 0.0
    
    for col in ['Eksport', 'Import', 'Postoj']:
        b[col] = b[col].apply(clean_num)
    o['Wartosc'] = o['Wartosc'].apply(clean_num)
    return b, o

df_baza, df_oplaty = fetch_data()
cfg = dict(zip(df_oplaty['Parametr'], df_oplaty['Wartosc']))

# --- 7. SIDEBAR (NAPRAWIONA WIDOCZNOŚĆ) ---
with st.sidebar:
    st.markdown("<div style='padding-top: 20px;'></div>", unsafe_allow_html=True)
    st.image("https://www.sqm.pl/wp-content/themes/sqm/img/logo-sqm.png", width=180)
    st.markdown(f"<div style='color: #ed8936; font-size: 14px; font-weight: 800; margin-bottom: 25px;'>ZALOGOWANY: {st.session_state.user.upper()}</div>", unsafe_allow_html=True)
    
    st.markdown("### PARAMETRY TRANSPORTU")
    calc_mode = st.radio("TYP ŁADUNKU", ["DEDYKOWANY", "DOŁADUNEK"])
    dest_city = st.selectbox("MIASTO DOCELOWE", sorted(TRANSIT_DATA.keys()))
    net_weight = st.number_input("WAGA NETTO (kg)", value=1000, step=100)
    
    st.markdown("---")
    st.markdown("### TERMINARZ TARGOWY")
    date_load = st.date_input("ZAŁADUNEK", datetime.now() + timedelta(days=5))
    date_unload = st.date_input("ROZŁADUNEK POWROTNY", date_load + timedelta(days=7))
    total_days_stay = max(0, (date_unload - date_load).days)
    
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("WYLOGUJ Z SYSTEMU", use_container_width=True):
        cookie_manager.delete("sqm_session_v16")
        st.session_state.auth = False
        st.rerun()

# --- 8. LOGIKA OBLICZENIOWA ---
effective_weight = net_weight * cfg.get('WAGA_BUFOR', 1.2)
vehicle_caps = {"BUS": 1200, "SOLO": 5500, "FTL": 10500}
calc_results = []

for v_type, cap in vehicle_caps.items():
    v_data = df_baza[(df_baza['Miasto'] == dest_city) & (df_baza['Typ_Pojazdu'] == v_type)]
    if not v_data.empty:
        avg_rates = v_data.mean(numeric_only=True)
        v_needed = math.ceil(effective_weight / cap)
        
        # Czas tranzytu
        t_category = "BUS" if v_type == "BUS" else "FTL/SOLO"
        t_days = TRANSIT_DATA.get(dest_city, {}).get(t_category, 2)
        
        # Składniki kosztów
        if calc_mode == "DEDYKOWANY":
            c_exp = avg_rates['Eksport'] * v_needed
            c_imp = avg_rates['Import'] * v_needed
        else:
            c_exp = avg_rates['Eksport'] * (effective_weight / cap)
            c_imp = avg_rates['Import'] * (effective_weight / cap)
            
        c_stay = avg_rates['Postoj'] * total_days_stay * v_needed
        c_parking = total_days_stay * cfg.get('PARKING_DAY', 30) * v_needed
        
        # Koszty specyficzne dla regionów
        c_ata = cfg.get('ATA_CARNET', 166) if dest_city in ["Londyn", "Genewa", "Liverpool", "Manchester"] else 0
        c_ferry = cfg.get('Ferry_UK', 450) if any(x in dest_city for x in ["Londyn", "Liverpool", "Manchester"]) else 0
        
        total_sum = c_exp + c_imp + c_stay + c_parking + c_ata + c_ferry
        
        calc_results.append({
            "Pojazd": v_type, "Szt": v_needed, "Total": total_sum,
            "Eksport": c_exp, "Import": c_imp, "Postoj": c_stay, 
            "Inne": c_parking + c_ata + c_ferry, "Transit": t_days,
            "Util": min(100, (effective_weight / (v_needed * cap)) * 100)
        })

# --- 9. WIDOK GŁÓWNY (DASHBOARD) ---
if calc_results:
    best_option = min(calc_results, key=lambda x: x['Total'])
    st.markdown(f'<div class="route-header">LOGISTYKA: KOMORNIKI ➔ {dest_city.upper()}</div>', unsafe_allow_html=True)
    
    col_main, col_side = st.columns([2, 1])
    
    with col_main:
        # GŁÓWNA KARTA CENOWA
        st.markdown(f"""
            <div class="hero-card">
                <div style="color: #ed8936; font-size: 14px; font-weight: 800; text-transform: uppercase; margin-bottom: 10px;">Estymowany Koszt Całkowity (Netto)</div>
                <div class="main-price-val">€ {best_option['Total']:,.2f}</div>
                <div class="data-grid">
                    <div class="data-item"><div class="data-label">Główny Pojazd</div><div class="data-value">{best_option['Pojazd']}</div></div>
                    <div class="data-item"><div class="data-label">Liczba Aut</div><div class="data-value">{best_option['Szt']} szt.</div></div>
                    <div class="data-item"><div class="data-label">Dni Tranzytu</div><div class="data-value">{best_option['Transit']} dni</div></div>
                    <div class="data-item"><div class="data-label">Dni na Miejscu</div><div class="data-value">{total_days_stay} dni</div></div>
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        # SZCZEGÓŁY KOSZTÓW
        st.write("### 🔍 ANALIZA KOSZTÓW")
        sc1, sc2 = st.columns(2)
        with sc1:
            st.metric("Eksport", f"€ {best_option['Eksport']:,.2f}")
            st.metric("Import", f"€ {best_option['Import']:,.2f}")
        with sc2:
            st.metric("Postoje i Parkingi", f"€ {best_option['Postoj'] + best_option['Inne']:,.2f}")
            st.metric("Wykorzystanie Przestrzeni", f"{best_option['Util']:.1f}%")

    with col_side:
        # MAPA I PODSUMOWANIE CZASOWE
        st.write("### 📍 TRASA")
        b_pos = CITY_COORDS["Komorniki (Baza)"]
        d_pos = CITY_COORDS.get(dest_city, [48.8, 2.3])
        map_data = pd.DataFrame({'lat': [b_pos[0], d_pos[0]], 'lon': [b_pos[1], d_pos[1]]})
        st.map(map_data, color='#ed8936', zoom=4)
        
        st.info(f"**Data wyjazdu z bazy:** {(date_load - timedelta(days=best_option['Transit'])).strftime('%Y-%m-%d')}")
        st.warning(f"**Waga z buforem bezpieczeństwa:** {effective_weight:,.0f} kg")

    # ALTERNATYWY
    st.write("---")
    st.write("### 🚛 INNE OPCJE TRANSPORTU")
    for res in sorted(calc_results, key=lambda x: x['Total']):
        with st.expander(f"{res['Pojazd']} ({res['Szt']} szt.) — € {res['Total']:,.2f}"):
            st.write(f"Koszt na jednostkę: € {res['Total']/res['Szt']:,.2f}")
            st.progress(res['Util']/100)
