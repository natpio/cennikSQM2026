import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import re
import hashlib
import math
import numpy as np
import time

# --- 1. KONFIGURACJA ZASOBÓW I BAZY DANYCH ---
SHEET_ID = "1sYlXP6WVzPE09qfmydQYQNsjiZcDgRSJGyWoXfjmkDY"
URL_BAZA = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=CENNIK_BAZA"
URL_OPLATY = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=OPLATY_STALE"
URL_USERS = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=USERS"

# Kompletna tabela tranzytów (Dni w jedną stronę)
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

# Koordynaty geograficzne dla mapy
CITY_COORDS = {
    "Komorniki (Baza)": [52.3358, 16.8122], "Amsterdam": [52.3702, 4.8952], 
    "Berlin": [52.5200, 13.4050], "Londyn": [51.5074, -0.1276],
    "Paryż": [48.8566, 2.3522], "Wiedeń": [48.2082, 16.3738], 
    "Praga": [50.0755, 14.4378], "Genewa": [46.2044, 6.1432], 
    "Barcelona": [41.3851, 2.1734], "Monachium": [48.1351, 11.5820], 
    "Madryt": [40.4168, -3.7038], "Lizbona": [38.7223, -9.1393],
    "Rzym": [41.9028, 12.4964], "Sztokholm": [59.3293, 18.0686]
}

# --- 2. KONFIGURACJA STRONY I UI ---
st.set_page_config(page_title="SQM VENTAGE v12.4", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
    <style>
    .stApp { background-color: #05070a !important; }
    [data-testid="stSidebar"] { background-color: #0f172a !important; border-right: 1px solid #1e293b; }
    
    /* Inputy i pola wyboru */
    div[data-baseweb="select"] > div, 
    div[data-baseweb="input"] > div,
    .stNumberInput div[data-baseweb="input"],
    .stDateInput div[data-baseweb="input"] {
        background-color: #1e293b !important;
        color: #ffffff !important;
        border: 1px solid #334155 !important;
    }
    input { color: #ffffff !important; -webkit-text-fill-color: #ffffff !important; }
    
    /* Branding */
    .brand-container { padding: 10px 0 20px 0; text-align: center; border-bottom: 1px solid #1e293b; margin-bottom: 20px; }
    .brand-logo { font-family: 'Inter', sans-serif; font-size: 20px; font-weight: 900; color: #ffffff; display: flex; align-items: center; justify-content: center; gap: 10px; }
    .brand-v { background: #ed8936; color: #000; padding: 2px 8px; border-radius: 4px; font-style: italic; }
    
    /* Karty i Nagłówki */
    .route-header { font-size: 30px !important; font-weight: 900; color: #ffffff; border-bottom: 3px solid #ed8936; margin-bottom: 25px; padding-bottom: 10px; }
    .hero-card { background: linear-gradient(145deg, #1e293b, #0f172a); border: 1px solid #334155; border-radius: 20px; padding: 30px; margin-bottom: 30px; }
    .main-price-value { color: #ffffff; font-size: 64px; font-weight: 950; line-height: 1.1; margin: 15px 0; }
    .price-tag { color: #ed8936; font-size: 20px; font-weight: 900; }
    
    /* Tabela wyników */
    .stDataFrame { background-color: #0f172a !important; border-radius: 10px; }
    </style>
""", unsafe_allow_html=True)

# --- 3. SYSTEM LOGOWANIA I SESJI ---
def get_hash(password):
    return hashlib.sha256(password.strip().encode()).hexdigest()

@st.cache_data(ttl=300)
def load_user_database():
    try:
        df = pd.read_csv(URL_USERS)
        df.columns = df.columns.str.strip()
        return dict(zip(df['username'].astype(str), df['password'].astype(str)))
    except:
        return {"admin": "f3e99d9459eeb7ffc4cd407d890fbf1db011208fa12d8edc501a7ec26da106a3"}

user_db = load_user_database()

# Inicjalizacja stanu sesji jeśli nie istnieje
if 'auth_active' not in st.session_state:
    st.session_state.auth_active = False
if 'user_name' not in st.session_state:
    st.session_state.user_name = ""

# Interfejs logowania
if not st.session_state.auth_active:
    _, center_col, _ = st.columns([1, 1.2, 1])
    with center_col:
        st.markdown("<div style='height:100px;'></div>", unsafe_allow_html=True)
        st.markdown("<h1 style='text-align:center; color:white;'>SQM VENTAGE</h1>", unsafe_allow_html=True)
        login_u = st.text_input("Użytkownik", key="u_login").strip()
        login_p = st.text_input("Hasło", type="password", key="p_login").strip()
        if st.button("ZALOGUJ DO SYSTEMU", use_container_width=True):
            if login_u in user_db and user_db[login_u] == get_hash(login_p):
                st.session_state.auth_active = True
                st.session_state.user_name = str(login_u)
                st.rerun()
            else:
                st.error("Błąd uwierzytelniania. Sprawdź dane.")
    st.stop()

# --- 4. FUNKCJE POBIERANIA DANYCH LOGISTYCZNYCH ---
@st.cache_data(ttl=60)
def get_logistics_data():
    try:
        baza = pd.read_csv(URL_BAZA)
        oplaty = pd.read_csv(URL_OPLATY)
        baza.columns = baza.columns.str.strip()
        def clean_val(v):
            s = re.sub(r'[^\d.]', '', str(v).replace(',', '.'))
            return float(s) if s else 0.0
        for col in ['Eksport', 'Import', 'Postoj']:
            if col in baza.columns:
                baza[col] = baza[col].apply(clean_val)
        oplaty['Wartosc'] = oplaty['Wartosc'].apply(clean_val)
        return baza, oplaty
    except:
        return pd.DataFrame(), pd.DataFrame()

df_baza, df_oplaty = get_logistics_data()
cfg = dict(zip(df_oplaty['Parametr'], df_oplaty['Wartosc'])) if not df_oplaty.empty else {}

# --- 5. SIDEBAR: NAWIGACJA I WYLOGOWANIE ---
with st.sidebar:
    st.markdown('<div class="brand-container"><div class="brand-logo"><span class="brand-v">V</span> SQM VENTAGE</div></div>', unsafe_allow_html=True)
    st.markdown(f"👤 Zalogowany: **{st.session_state.user_name}**")
    
    # Przełącznik Modułów
    app_mode = st.radio("MODUŁ SYSTEMOWY", ["📊 KALKULATOR", "⚙️ ADMIN TOOL"])
    
    st.markdown("---")
    
    # Parametry Kalkulatora (wyświetlane tylko w trybie Kalkulatora)
    if app_mode == "📊 KALKULATOR":
        st.markdown("### 🚛 KONFIGURACJA TRASY")
        target_city = st.selectbox("MIASTO DOCELOWE", sorted(TRANSIT_DATA.keys()))
        trip_mode = st.radio("KIERUNEK", ["EXP + IMP", "ONE-WAY"])
        load_strategy = st.radio("STRATEGIA ŁADUNKU", ["DEDYKOWANY", "DOŁADUNEK"])
        
        weight_main = st.number_input("WAGA NETTO (KG)", value=1000, step=100)
        weight_brutto = weight_main * 1.20 # Rezerwa 20% na akcesoria
        st.markdown(f"**Waga brutto: {weight_brutto:,.0f} kg**")
        
        date_start = st.date_input("START MONTAŻU", datetime.now() + timedelta(days=7))
        days_on_site = 0
        if trip_mode == "EXP + IMP":
            date_end = st.date_input("KONIEC DEMONTAŻU", date_start + timedelta(days=5))
            days_on_site = max(0, (date_end - date_start).days)
    
    st.markdown("---")
    
    # Przycisk wylogowania
    if st.button("🚪 WYLOGUJ MNIE", use_container_width=True):
        st.session_state.auth_active = False
        st.session_state.user_name = ""
        st.rerun()

# --- 6. WIDOK: ADMIN TOOL ---
if app_mode == "⚙️ ADMIN TOOL":
    st.title("⚙️ Panel Zarządzania Systemem")
    
    # Krytyczne sprawdzenie uprawnień
    if st.session_state.user_name.lower() != "admin":
        st.error(f"Odmowa dostępu. Użytkownik '{st.session_state.user_name}' nie posiada uprawnień administratora.")
        st.info("Zaloguj się na konto 'admin', aby edytować stawki.")
    else:
        st.success("Autoryzacja Admina poprawna.")
        st.markdown(f"### 📄 Baza Danych (Google Sheets)")
        st.markdown(f"Edytuj dane źródłowe tutaj: [Link do Arkusza SQM](https://docs.google.com/spreadsheets/d/{SHEET_ID})")
        
        tab_baza, tab_koszty = st.tabs(["Cennik Przewoźników", "Koszty Dodatkowe"])
        with tab_baza:
            st.dataframe(df_baza, use_container_width=True, height=500)
        with tab_koszty:
            st.table(df_oplaty)
    st.stop()

# --- 7. WIDOK: KALKULATOR LOGISTYCZNY ---
st.markdown(f'<div class="route-header">TRASA: KOMORNIKI ➔ {target_city.upper()}</div>', unsafe_allow_html=True)

caps = {"BUS": 1200, "SOLO": 5500, "FTL": 10500}
results = []

if not df_baza.empty:
    for v_type, cap in caps.items():
        # Pobranie stawek dla konkretnego miasta i pojazdu
        match = df_baza[(df_baza['Miasto'] == target_city) & (df_baza['Typ_Pojazdu'] == v_type)]
        if not match.empty:
            data_row = match.mean(numeric_only=True)
            num_vehicles = math.ceil(weight_brutto / cap)
            
            # Pobranie dni tranzytu
            t_days = TRANSIT_DATA.get(target_city, {}).get("BUS" if v_type=="BUS" else "FTL/SOLO", 2)
            
            # Obliczenie frachtu
            if load_strategy == "DEDYKOWANY":
                cost_exp = data_row['Eksport'] * num_vehicles
                cost_imp = (data_row['Import'] * num_vehicles) if "EXP + IMP" in trip_mode else 0
            else:
                # Doładunek liczony proporcjonalnie do wagi
                cost_exp = data_row['Eksport'] * (weight_brutto / cap)
                cost_imp = (data_row['Import'] * (weight_brutto / cap)) if "EXP + IMP" in trip_mode else 0
            
            # Dodatki (ATA, Ferry, Parking, Postój)
            fee_ata = (cfg.get('ATA_CARNET', 166) if target_city in ["Londyn", "Genewa", "Liverpool", "Manchester"] else 0)
            fee_ferry = (cfg.get('Ferry_UK', 450) if any(x in target_city for x in ["Londyn", "Liverpool", "Manchester"]) else 0)
            fee_parking = (days_on_site * cfg.get('PARKING_DAY', 30) * num_vehicles)
            fee_postoj = (data_row['Postoj'] * days_on_site * num_vehicles)
            
            grand_total = cost_exp + cost_imp + fee_ata + fee_ferry + fee_parking + fee_postoj
            
            results.append({
                "Pojazd": v_type,
                "Sztuk": num_vehicles,
                "Suma €": grand_total,
                "Eksport €": cost_exp,
                "Import €": cost_imp,
                "Inne €": fee_ata + fee_ferry + fee_parking + fee_postoj,
                "Tranzyt (dni)": t_days,
                "Wypełnienie": min(100, (weight_brutto / (num_vehicles * cap)) * 100)
            })

if results:
    # Wybór najlepszej opcji
    best_option = min(results, key=lambda x: x['Suma €'])
    departure_date = date_start - timedelta(days=best_option['Tranzyt (dni)'] + 1)
    
    col_main, col_map = st.columns([1.8, 1])
    
    with col_main:
        st.markdown(f"""
            <div class="hero-card">
                <div style='color:#ed8936; font-size:14px; font-weight:800;'>NAJLEPSZA KONFIGURACJA (NETTO)</div>
                <div class="main-price-value">€ {best_option['Suma €']:,.2f}</div>
                <div style='display: grid; grid-template-columns: 1fr 1fr; gap: 10px; border-top: 1px solid #334155; padding-top: 15px;'>
                    <div style='color: #94a3b8; font-size: 14px;'>Eksport: <b>€ {best_option['Eksport €']:,.0f}</b></div>
                    <div style='color: #94a3b8; font-size: 14px;'>Import: <b>€ {best_option['Import €']:,.0f}</b></div>
                    <div style='color: #94a3b8; font-size: 14px;'>Pojazd: <b>{best_option['Sztuk']}x {best_option['Pojazd']}</b></div>
                    <div style='color: #94a3b8; font-size: 14px;'>Załadunek: <b>{best_option['Wypełnienie']:.0f}%</b></div>
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        st.subheader("📋 Porównanie wszystkich opcji")
        results_df = pd.DataFrame(results)
        st.dataframe(results_df.style.format({"Suma €": "{:.2f}", "Wypełnienie": "{:.0f}%"}), use_container_width=True)

    with col_map:
        st.success(f"🚚 **WYJAZD Z BAZY: {departure_date.strftime('%Y-%m-%d')}**")
        st.info(f"Kalkulacja uwzględnia {best_option['Tranzyt (dni)']} dni drogi oraz 1 dzień zapasu.")
        
        # Wizualizacja trasy
        base_loc = CITY_COORDS["Komorniki (Baza)"]
        dest_loc = CITY_COORDS.get(target_city, [50, 10])
        map_data = pd.DataFrame({
            'lat': np.linspace(base_loc[0], dest_loc[0], 20),
            'lon': np.linspace(base_loc[1], dest_loc[1], 20)
        })
        st.map(map_data, color="#ed8936", size=10)
else:
    st.error("Brak dostępnych stawek dla tej trasy w bazie danych.")
