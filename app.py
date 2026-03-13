import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import re
import hashlib
import math
import numpy as np
import time

# ==========================================
# 1. KONFIGURACJA ZASOBÓW I GOOGLE SHEETS
# ==========================================
SHEET_ID = "1sYlXP6WVzPE09qfmydQYQNsjiZcDgRSJGyWoXfjmkDY"
URL_BAZA = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=CENNIK_BAZA"
URL_OPLATY = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=OPLATY_STALE"
URL_USERS = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=USERS"

# Kompletna tabela tranzytów SQM (dni drogi w jedną stronę)
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

# Koordynaty do wizualizacji mapy
CITY_COORDS = {
    "Komorniki (Baza)": [52.3358, 16.8122], "Amsterdam": [52.3702, 4.8952], 
    "Berlin": [52.5200, 13.4050], "Londyn": [51.5074, -0.1276],
    "Paryż": [48.8566, 2.3522], "Wiedeń": [48.2082, 16.3738], 
    "Praga": [50.0755, 14.4378], "Genewa": [46.2044, 6.1432], 
    "Barcelona": [41.3851, 2.1734], "Monachium": [48.1351, 11.5820], 
    "Madryt": [40.4168, -3.7038], "Lizbona": [38.7223, -9.1393],
    "Rzym": [41.9028, 12.4964], "Sztokholm": [59.3293, 18.0686]
}

# ==========================================
# 2. KONFIGURACJA UI I STYLIZACJA CSS
# ==========================================
st.set_page_config(page_title="SQM VENTAGE v12.5", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
    <style>
    .stApp { background-color: #05070a !important; }
    [data-testid="stSidebar"] { background-color: #0f172a !important; border-right: 1px solid #1e293b; }
    
    /* Inputy i Selektory */
    div[data-baseweb="select"] > div, div[data-baseweb="input"] > div, 
    .stNumberInput div[data-baseweb="input"], .stDateInput div[data-baseweb="input"] {
        background-color: #1e293b !important; color: #ffffff !important; border: 1px solid #334155 !important;
    }
    input { color: #ffffff !important; -webkit-text-fill-color: #ffffff !important; }
    
    /* Branding SQM */
    .brand-container { padding: 10px 0 20px 0; text-align: center; border-bottom: 1px solid #1e293b; margin-bottom: 20px; }
    .brand-logo { font-family: 'Inter', sans-serif; font-size: 20px; font-weight: 900; color: #ffffff; display: flex; align-items: center; justify-content: center; gap: 10px; }
    .brand-v { background: #ed8936; color: #000; padding: 2px 8px; border-radius: 4px; font-style: italic; }
    
    /* Nagłówki i Karty */
    .route-header { font-size: 30px !important; font-weight: 900; color: #ffffff; border-bottom: 3px solid #ed8936; margin-bottom: 25px; padding-bottom: 10px; }
    .hero-card { background: linear-gradient(145deg, #1e293b, #0f172a); border: 1px solid #334155; border-radius: 20px; padding: 30px; margin-bottom: 30px; }
    .main-price-value { color: #ffffff; font-size: 64px; font-weight: 950; line-height: 1.1; margin: 15px 0; }
    
    /* Tabele */
    .stDataFrame { background-color: #0f172a !important; }
    [data-testid="stSidebar"] label p { color: #94a3b8 !important; font-weight: 700; text-transform: uppercase; font-size: 0.75rem; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 3. LOGIKA AUTORYZACJI (BEZ CIASTECZEK)
# ==========================================
def make_hash(p):
    return hashlib.sha256(p.strip().encode()).hexdigest()

@st.cache_data(ttl=300)
def load_users():
    try:
        df = pd.read_csv(URL_USERS)
        df.columns = df.columns.str.strip()
        return dict(zip(df['username'].astype(str), df['password'].astype(str)))
    except:
        # Fallback jeśli arkusz nie odpowiada
        return {"admin": "f3e99d9459eeb7ffc4cd407d890fbf1db011208fa12d8edc501a7ec26da106a3"}

user_db = load_users()

# Inicjalizacja stanu sesji
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'current_user' not in st.session_state:
    st.session_state.current_user = ""

# Formularz logowania
if not st.session_state.authenticated:
    _, login_col, _ = st.columns([1, 1.2, 1])
    with login_col:
        st.markdown("<div style='height:100px;'></div>", unsafe_allow_html=True)
        st.markdown("<h2 style='text-align:center; color:white;'>SQM VENTAGE LOGIN</h2>", unsafe_allow_html=True)
        u_field = st.text_input("Użytkownik", key="u_field").strip()
        p_field = st.text_input("Hasło", type="password", key="p_field").strip()
        
        if st.button("ZALOGUJ", use_container_width=True):
            if u_field in user_db and user_db[u_field] == make_hash(p_field):
                st.session_state.authenticated = True
                st.session_state.current_user = str(u_field)
                st.rerun()
            else:
                st.error("Nieprawidłowe dane logowania.")
    st.stop()

# ==========================================
# 4. POBIERANIE I CZYSZCZENIE DANYCH
# ==========================================
@st.cache_data(ttl=60)
def fetch_all_data():
    try:
        b = pd.read_csv(URL_BAZA)
        o = pd.read_csv(URL_OPLATY)
        b.columns = b.columns.str.strip()
        
        def clean_currency(val):
            s = re.sub(r'[^\d.]', '', str(val).replace(',', '.'))
            return float(s) if s else 0.0
            
        for col in ['Eksport', 'Import', 'Postoj']:
            if col in b.columns:
                b[col] = b[col].apply(clean_currency)
        o['Wartosc'] = o['Wartosc'].apply(clean_currency)
        
        return b, o
    except Exception as e:
        st.error(f"Błąd bazy danych: {e}")
        return pd.DataFrame(), pd.DataFrame()

df_baza, df_oplaty = fetch_all_data()
cfg = dict(zip(df_oplaty['Parametr'], df_oplaty['Wartosc'])) if not df_oplaty.empty else {}

# ==========================================
# 5. SIDEBAR: NAWIGACJA I WYLOGOWANIE
# ==========================================
with st.sidebar:
    st.markdown('<div class="brand-container"><div class="brand-logo"><span class="brand-v">V</span> SQM VENTAGE</div></div>', unsafe_allow_html=True)
    st.markdown(f"👤 Zalogowany: **{st.session_state.current_user}**")
    
    app_menu = st.radio("NAWIGACJA", ["📊 KALKULATOR", "⚙️ ADMIN TOOL"])
    
    st.markdown("---")
    
    # Przycisk wylogowania - czyści sesję natychmiast
    if st.button("🚪 WYLOGUJ Z SYSTEMU", use_container_width=True):
        st.session_state.authenticated = False
        st.session_state.current_user = ""
        st.rerun()

# ==========================================
# 6. MODUŁ: ADMIN TOOL (PEŁNY)
# ==========================================
if app_menu == "⚙️ ADMIN TOOL":
    st.title("⚙️ Panel Administratora SQM")
    
    # Rygorystyczne sprawdzenie uprawnień
    if str(st.session_state.current_user).lower() != "admin":
        st.error(f"Brak uprawnień. Zalogowano jako: '{st.session_state.current_user}'.")
        st.info("Tylko konto 'admin' może przeglądać i edytować bazę stawek.")
    else:
        st.success("Dostęp przyznany: Administrator Systemu.")
        st.markdown(f"### 🌐 Zarządzanie Danymi Źródłowymi")
        st.info(f"Wszystkie zmiany wprowadzone w arkuszu będą widoczne w aplikacji po 60 sekundach.")
        st.markdown(f"[OTWÓRZ ARKUSZ GOOGLE SHEETS](https://docs.google.com/spreadsheets/d/{SHEET_ID})")
        
        t1, t2 = st.tabs(["CENNIK BAZOWY", "USTAWIENIA SYSTEMOWE"])
        with t1:
            st.dataframe(df_baza, use_container_width=True, height=600)
        with t2:
            st.table(df_oplaty)
    st.stop()

# ==========================================
# 7. MODUŁ: KALKULATOR (PEŁNY)
# ==========================================
st.markdown(f'<div class="route-header">NOWA KALKULACJA: {st.session_state.current_user.upper()}</div>', unsafe_allow_html=True)

with st.sidebar:
    st.markdown("### 🚛 PARAMETRY TRANSPORTU")
    dest = st.selectbox("MIASTO DOCELOWE", sorted(TRANSIT_DATA.keys()))
    t_type = st.radio("KIERUNEK", ["Eksport + Import", "Tylko Eksport"])
    strat = st.radio("STRATEGIA", ["DEDYKOWANY (Pełne auto)", "DOŁADUNEK (Część auta)"])
    
    w_netto = st.number_input("WAGA ŁADUNKU (KG)", value=1000, step=100)
    w_brutto = w_netto * 1.20 # Rezerwa logistyczna SQM
    
    d_montaz = st.date_input("DATA MONTAŻU", datetime.now() + timedelta(days=7))
    d_stay = 0
    if "Eksport + Import" in t_type:
        d_demontaz = st.date_input("DATA DEMONTAŻU", d_montaz + timedelta(days=5))
        d_stay = max(0, (d_demontaz - d_montaz).days)

# Silnik obliczeniowy SQM
caps = {"BUS": 1200, "SOLO": 5500, "FTL": 10500}
results = []

if not df_baza.empty:
    for v_name, v_cap in caps.items():
        match = df_baza[(df_baza['Miasto'] == dest) & (df_baza['Typ_Pojazdu'] == v_name)]
        if not match.empty:
            row = match.mean(numeric_only=True)
            v_qty = math.ceil(w_brutto / v_cap)
            t_days = TRANSIT_DATA.get(dest, {}).get("BUS" if v_name=="BUS" else "FTL/SOLO", 2)
            
            # Obliczanie bazowe
            if strat == "DEDYKOWANY (Pełne auto)":
                c_exp = row['Eksport'] * v_qty
                c_imp = (row['Import'] * v_qty) if "Import" in t_type else 0
            else:
                c_exp = row['Eksport'] * (w_brutto / v_cap)
                c_imp = (row['Import'] * (w_brutto / v_cap)) if "Import" in t_type else 0
            
            # Koszty dodatkowe (ATA, Ferry, Postój)
            c_ata = (cfg.get('ATA_CARNET', 166) if dest in ["Londyn", "Genewa", "Liverpool", "Manchester"] else 0)
            c_ferry = (cfg.get('Ferry_UK', 450) if any(x in dest for x in ["Londyn", "Liverpool", "Manchester"]) else 0)
            c_parking = (d_stay * cfg.get('PARKING_DAY', 30) * v_qty)
            c_wait = (row['Postoj'] * d_stay * v_qty)
            
            final_val = c_exp + c_imp + c_ata + c_ferry + c_parking + c_wait
            
            results.append({
                "Pojazd": v_name, "Szt": v_qty, "Razem €": final_val, 
                "Eksport €": c_exp, "Import €": c_imp, "Dodatki €": c_ata+c_ferry+c_parking+c_wait,
                "Tranzyt": t_days, "Załadunek": min(100, (w_brutto/(v_qty*v_cap))*100)
            })

if results:
    best = min(results, key=lambda x: x['Razem €'])
    dep_date = d_montaz - timedelta(days=best['Tranzyt'] + 1)
    
    col_l, col_r = st.columns([1.8, 1])
    
    with col_l:
        st.markdown(f"""
            <div class="hero-card">
                <div style='color:#ed8936; font-size:14px; font-weight:800;'>WYCENA OPTYMALNA (NETTO)</div>
                <div class="main-price-value">€ {best['Razem €']:,.2f}</div>
                <div style='display: grid; grid-template-columns: 1fr 1fr; gap: 15px; border-top: 1px solid #334155; padding-top: 15px; margin-top: 15px;'>
                    <div style='color:#94a3b8;'>Pojazd: <b>{best['Szt']}x {best['Pojazd']}</b></div>
                    <div style='color:#94a3b8;'>Eksport: <b>€ {best['Eksport €']:,.0f}</b></div>
                    <div style='color:#94a3b8;'>Tranzyt: <b>{best['Tranzyt']} dni</b></div>
                    <div style='color:#94a3b8;'>Import: <b>€ {best['Import €']:,.0f}</b></div>
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        st.subheader("📊 Wszystkie dostępne opcje")
        st.dataframe(pd.DataFrame(results).style.format({"Razem €": "{:.2f}", "Załadunek": "{:.0f}%"}), use_container_width=True)

    with col_r:
        st.success(f"🗓️ WYJAZD Z BAZY: {dep_date.strftime('%Y-%m-%d')}")
        st.info(f"Opracowano dla wagi brutto: {w_brutto:,.0f} kg")
        
        # Mapa trasy
        b_c = CITY_COORDS["Komorniki (Baza)"]
        d_c = CITY_COORDS.get(dest, [50, 10])
        st.map(pd.DataFrame({'lat': np.linspace(b_c[0], d_c[0], 15), 'lon': np.linspace(b_c[1], d_c[1], 15)}), color="#ed8936")
else:
    st.error("Błąd: Nie znaleziono stawek dla tego kierunku.")
