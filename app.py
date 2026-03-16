import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import re
import hashlib
import math
import numpy as np
import pydeck as pdk

# --- 1. KONFIGURACJA ZASOBÓW (GOOGLE SHEETS) ---
# Identyfikator arkusza SQM Multimedia Solutions
SHEET_ID = "1sYlXP6WVzPE09qfmydQYQNsjiZcDgRSJGyWoXfjmkDY"
URL_BAZA = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=CENNIK_BAZA"
URL_OPLATY = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=OPLATY_STALE"
URL_USERS = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=USERS"

# Pełna mapa tranzytów (Dni robocze) - kluczowe dla planowania slotów rozładunkowych
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

# Koordynaty GPS dla wizualizacji mapy PyDeck
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
st.set_page_config(page_title="SQM VENTAGE v5.2.3", layout="wide", initial_sidebar_state="expanded")

# --- 3. STYLE CSS (UI DESIGN) ---
st.markdown("""
    <style>
    .stApp { background-color: #05070a !important; }
    [data-testid="stSidebar"] { background-color: #0f172a !important; border-right: 1px solid #1e293b; }
    
    /* Inputy i Selecty */
    div[data-baseweb="select"] > div, div[data-baseweb="input"] > div, 
    .stNumberInput div[data-baseweb="input"], .stDateInput div[data-baseweb="input"] {
        background-color: #1e293b !important; color: #ffffff !important; border: 1px solid #334155 !important;
    }
    input { color: #ffffff !important; -webkit-text-fill-color: #ffffff !important; }
    
    /* Brand Logo Section */
    .brand-container { padding: 10px 0 20px 0; text-align: center; border-bottom: 1px solid #1e293b; margin-bottom: 20px; }
    .brand-logo { font-size: 22px; font-weight: 900; color: #ffffff; display: flex; align-items: center; justify-content: center; gap: 10px; }
    .brand-v { background: #ed8936; color: #000; padding: 2px 10px; border-radius: 4px; }
    
    /* Route Header */
    .route-header { font-size: 32px !important; font-weight: 900; color: #ffffff; border-bottom: 4px solid #ed8936; margin-bottom: 30px; padding-bottom: 10px; }
    
    /* Hero Card (Główna cena) */
    .hero-card { background: linear-gradient(145deg, #1e293b, #0f172a); border: 1px solid #334155; border-radius: 24px; padding: 35px; margin-bottom: 30px; }
    .main-price-value { color: #ffffff; font-size: 72px; font-weight: 950; margin: 10px 0; line-height: 1; }
    
    /* Breakdown list */
    .breakdown-container { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 20px; margin: 25px 0; padding: 25px 0; border-top: 1px solid rgba(255,255,255,0.1); border-bottom: 1px solid rgba(255,255,255,0.1); }
    .breakdown-item { font-size: 13px; color: #94a3b8; }
    .breakdown-item b { color: #ffffff; font-size: 17px; display: block; margin-top: 5px; }
    
    /* Alternative cards */
    .alt-card { background: #0f172a; border-left: 5px solid #334155; padding: 20px 25px; margin-bottom: 15px; border-radius: 12px; display: flex; justify-content: space-between; align-items: center; transition: 0.3s; }
    .alt-best { border-left-color: #ed8936; background: rgba(237, 137, 54, 0.05); }
    .price-tag { color: #ed8936; font-size: 22px; font-weight: 900; }
    </style>
""", unsafe_allow_html=True)

# --- 4. FUNKCJE LOGICZNE (BACKEND) ---
def make_hash(p):
    """Generowanie skrótu SHA-256 dla hasła."""
    return hashlib.sha256(p.strip().encode()).hexdigest()

@st.cache_data(ttl=60)
def fetch_data():
    """Pobieranie danych z Google Sheets z czyszczeniem formatowania."""
    try:
        b = pd.read_csv(URL_BAZA)
        o = pd.read_csv(URL_OPLATY)
        b.columns = b.columns.str.strip()
        o.columns = o.columns.str.strip()
        
        def clean_currency(v):
            if pd.isna(v): return 0.0
            s = re.sub(r'[^\d.]', '', str(v).replace(',', '.'))
            return float(s) if s else 0.0

        for col in ['Eksport', 'Import', 'Postoj']:
            if col in b.columns:
                b[col] = b[col].apply(clean_currency)
        
        if 'Wartosc' in o.columns:
            o['Wartosc'] = o['Wartosc'].apply(clean_currency)
            
        return b, o
    except Exception as e:
        st.error(f"Błąd krytyczny pobierania danych: {e}")
        return pd.DataFrame(), pd.DataFrame()

@st.cache_data(ttl=60)
def load_users():
    """Ładowanie bazy użytkowników."""
    try:
        df = pd.read_csv(URL_USERS)
        df.columns = df.columns.str.strip()
        return dict(zip(df['username'].astype(str), df['password'].astype(str)))
    except:
        # Fallback na admina, jeśli arkusz nie odpowiada
        return {"admin": "f3e99d9459eeb7ffc4cd407d890fbf1db011208fa12d8edc501a7ec26da106a3"}

# --- 5. OBSŁUGA SESJI I LOGOWANIA ---
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "current_user" not in st.session_state:
    st.session_state.current_user = None

if not st.session_state.authenticated:
    _, col_log, _ = st.columns([1, 1.2, 1])
    with col_log:
        st.markdown("<div style='text-align:center; margin-top:100px;'><h1 style='color:white;'>SQM <span style='color:#ed8936;'>VENTAGE</span></h1><p style='color:#94a3b8;'>Logistyka Targowa v5.2.3</p></div>", unsafe_allow_html=True)
        user_input = st.text_input("Użytkownik", placeholder="Wpisz login...")
        pass_input = st.text_input("Hasło", type="password", placeholder="Wpisz hasło...")
        
        if st.button("ZALOGUJ DO SYSTEMU", use_container_width=True):
            user_db = load_users()
            if user_input in user_db and user_db[user_input] == make_hash(pass_input):
                st.session_state.authenticated = True
                st.session_state.current_user = user_input
                st.rerun()
            else:
                st.error("Nieprawidłowy login lub hasło.")
    st.stop()

# --- 6. PRZYGOTOWANIE DANYCH DO OBLICZEŃ ---
df_baza, df_oplaty = fetch_data()
# Konwersja tabeli opłat na słownik dla łatwego dostępu
cfg = dict(zip(df_oplaty['Parametr'], df_oplaty['Wartosc'])) if not df_oplaty.empty else {}

# --- 7. PASEK BOCZNY (KONTROLA PARAMETRÓW) ---
with st.sidebar:
    st.markdown('<div class="brand-container"><div class="brand-logo"><span class="brand-v">V</span> SQM VENTAGE</div></div>', unsafe_allow_html=True)
    
    st.subheader("PARAMETRY TRASY")
    trip_type = st.radio("KIERUNEK", ["PEŁNA TRASA (EXP+IMP)", "TYLKO DOSTAWA (ONE-WAY)"])
    mode = st.radio("STRATEGIA ZAŁADUNKU", ["DEDYKOWANY", "DOŁADUNEK"])
    target_city = st.selectbox("MIEJSCE DOCELOWE", sorted(TRANSIT_DATA.keys()))
    
    st.markdown("---")
    st.subheader("ŁADUNEK")
    input_weight = st.number_input("WAGA PROJEKTU (KG NETTO)", value=1000, step=100)
    # Automatyczne doliczanie wagi opakowań (20%) - specyfika SQM
    real_weight_total = input_weight * 1.20
    st.markdown(f"""
        <div style="background:rgba(237,137,54,0.1); border:1px solid #ed8936; padding:15px; border-radius:10px; color:#ed8936; text-align:center;">
            <div style="font-size:10px; opacity:0.8;">ESTYMACJA WAGI BRUTTO</div>
            <div style="font-size:22px; font-weight:900;">{real_weight_total:,.0f} KG</div>
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    st.subheader("HARMONOGRAM")
    date_mount = st.date_input("DATA MONTAŻU", datetime.now() + timedelta(days=7))
    
    stay_duration = 0
    if trip_type == "PEŁNA TRASA (EXP+IMP)":
        date_demount = st.date_input("DATA DEMONTAŻU", date_mount + timedelta(days=4))
        stay_duration = max(0, (date_demount - date_mount).days)
    
    st.markdown("---")
    if st.button("🚪 WYLOGUJ MNIE", use_container_width=True):
        st.session_state.clear()
        st.rerun()

# --- 8. LOGIKA WIDOCZNOŚCI ZAKŁADEK (PERMISJE) ---
if st.session_state.current_user == "admin":
    tab_calc, tab_admin = st.tabs(["🚀 KALKULATOR LOGISTYCZNY", "⚙️ PANEL ADMINISTRATORA"])
else:
    # Osoby postronne nie widzą nawet paska zakładek
    tab_calc = st.container()
    tab_admin = None

# --- TAB 1: KALKULATOR (DOSTĘPNY DLA WSZYSTKICH) ---
with tab_calc:
    # Definicja tonażu aut we flocie
    vehicle_caps = {"BUS": 1200, "SOLO": 5500, "FTL": 10500}
    calculation_results = []
    
    if not df_baza.empty:
        for v_name, v_cap in vehicle_caps.items():
            # Filtrowanie stawek dla konkretnego miasta i auta
            match = df_baza[(df_baza['Miasto'] == target_city) & (df_baza['Typ_Pojazdu'] == v_name)]
            
            if not match.empty:
                row = match.iloc[0]
                num_vehicles = math.ceil(real_weight_total / v_cap)
                
                # Pobranie dni tranzytu
                transit_days = TRANSIT_DATA.get(target_city, {}).get("BUS" if v_name=="BUS" else "FTL/SOLO", 2)
                
                # 1. Koszt eksportu
                if mode == "DEDYKOWANY":
                    cost_exp = row['Eksport'] * num_vehicles
                else:
                    cost_exp = row['Eksport'] * (real_weight_total / v_cap)
                
                # 2. Koszt importu
                cost_imp = 0
                if trip_type == "PEŁNA TRASA (EXP+IMP)":
                    if mode == "DEDYKOWANY":
                        cost_imp = row['Import'] * num_vehicles
                    else:
                        cost_imp = row['Import'] * (real_weight_total / v_cap)
                
                # 3. Koszty postoju i delegacji
                cost_stay = row['Postoj'] * stay_duration * num_vehicles
                cost_parking = (stay_duration * cfg.get('PARKING_DAY', 30) * num_vehicles)
                
                # 4. Dodatki celne i specjalne
                cost_ata = (cfg.get('ATA_CARNET', 166) if target_city in ["Londyn", "Genewa", "Liverpool", "Manchester"] else 0)
                cost_ferry = (cfg.get('Ferry_UK', 450) if any(x in target_city for x in ["Londyn", "Liverpool", "Manchester"]) else 0)
                
                total_netto = cost_exp + cost_imp + cost_stay + cost_parking + cost_ata + cost_ferry
                
                calculation_results.append({
                    "type": v_name,
                    "count": num_vehicles,
                    "total": total_netto,
                    "transit": transit_days,
                    "utilization": min(100, (real_weight_total / (num_vehicles * v_cap)) * 100),
                    "breakdown": {
                        "Eksport": cost_exp,
                        "Import": cost_imp,
                        "Postój": cost_stay,
                        "Hotele/Parking": cost_parking,
                        "Odprawa/ATA": cost_ata,
                        "Prom": cost_ferry
                    }
                })

    if calculation_results:
        # Wybór najlepszej opcji (najniższa cena)
        best_option = min(calculation_results, key=lambda x: x['total'])
        departure_date = date_mount - timedelta(days=best_option['transit'] + 1)
        
        st.markdown(f'<div class="route-header">KOMORNIKI ➔ {target_city.upper()}</div>', unsafe_allow_html=True)
        
        col_res, col_map = st.columns([1.8, 1])
        
        with col_res:
            # HTML dla breakdownu w karcie głównej
            breakdown_html = ""
            for label, val in best_option['breakdown'].items():
                if val > 0:
                    breakdown_html += f"<div class='breakdown-item'>{label}: <b>€ {val:,.0f}</b></div>"

            st.markdown(f"""
                <div class="hero-card">
                    <div style='color:#ed8936; font-size:14px; font-weight:800; letter-spacing:1px;'>NAJLEPSZA OPCJA: {best_option['type']} x{best_option['count']}</div>
                    <div class="main-price-value">€ {best_option['total']:,.2f}</div>
                    <div class="breakdown-container">{breakdown_html}</div>
                    <div style='display:grid; grid-template-columns: repeat(3, 1fr); gap:15px;'>
                        <div style='background:rgba(255,255,255,0.05); padding:15px; border-radius:15px; text-align:center;'>
                            <div style='color:#94a3b8; font-size:10px;'>CZAS TRANZYTU</div><div style='color:white; font-size:20px; font-weight:900;'>{best_option['transit']} dni</div>
                        </div>
                        <div style='background:rgba(255,255,255,0.05); padding:15px; border-radius:15px; text-align:center;'>
                            <div style='color:#94a3b8; font-size:10px;'>ZAŁADUNEK</div><div style='color:white; font-size:20px; font-weight:900;'>{best_option['utilization']:.0f}%</div>
                        </div>
                        <div style='background:rgba(255,255,255,0.05); padding:15px; border-radius:15px; text-align:center;'>
                            <div style='color:#94a3b8; font-size:10px;'>DATA WYJAZDU</div><div style='color:#ed8936; font-size:20px; font-weight:900;'>{departure_date.strftime('%d.%m')}</div>
                        </div>
                    </div>
                </div>
            """, unsafe_allow_html=True)
            
            st.subheader("PORÓWNANIE DOSTĘPNYCH POJAZDÓW")
            for res in sorted(calculation_results, key=lambda x: x['total']):
                is_win = "alt-best" if res['type'] == best_option['type'] else ""
                st.markdown(f"""
                    <div class="alt-card {is_win}">
                        <div>
                            <span style='font-size:18px; font-weight:800;'>{res['type']}</span> 
                            <span style='color:#94a3b8; margin-left:10px;'>({res['count']} szt. | wypełnienie {res['utilization']:.0f}%)</span>
                        </div>
                        <div class="price-tag">€ {res['total']:,.2f}</div>
                    </div>
                """, unsafe_allow_html=True)

        with col_map:
            # Mapa PyDeck
            origin = CITY_COORDS["Komorniki (Baza)"]
            dest = CITY_COORDS.get(target_city, [52.5, 13.4])
            
            st.pydeck_chart(pdk.Deck(
                map_provider="carto",
                map_style="light",
                initial_view_state=pdk.ViewState(
                    latitude=(origin[0] + dest[0]) / 2,
                    longitude=(origin[1] + dest[1]) / 2,
                    zoom=4,
                    pitch=45
                ),
                layers=[
                    pdk.Layer(
                        "ArcLayer",
                        data=pd.DataFrame([{"start": [origin[1], origin[0]], "end": [dest[1], dest[0]]}]),
                        get_source_position="start",
                        get_target_position="end",
                        get_source_color=[237, 137, 54, 200],
                        get_target_color=[255, 255, 255, 80],
                        get_width=6
                    ),
                    pdk.Layer(
                        "ScatterplotLayer",
                        data=pd.DataFrame([{"p": [origin[1], origin[0]]}, {"p": [dest[1], dest[0]]}]),
                        get_position="p",
                        get_color=[237, 137, 54],
                        get_radius=50000
                    )
                ]
            ))
            st.info(f"💡 Sugerowany termin wyjazdu z bazy w Komornikach: **{departure_date.strftime('%A, %d %B %Y')}**")

# --- TAB 2: PANEL ADMINA (TYLKO DLA "admin") ---
if tab_admin is not None:
    with tab_admin:
        st.header("⚙️ Zarządzanie Danymi SQM VENTAGE")
        
        # 1. Generator nowych użytkowników
        with st.expander("🔐 GENERATOR NOWYCH KONT", expanded=True):
            st.write("Stwórz dane do wklejenia w zakładce USERS w Arkuszu Google.")
            c_u, c_p = st.columns(2)
            new_u_name = c_u.text_input("Nazwa użytkownika (np. k.nowak)", key="admin_gen_u")
            new_u_pass = c_p.text_input("Hasło (czysty tekst)", type="password", key="admin_gen_p")
            
            if new_u_name and new_u_pass:
                gen_hash = make_hash(new_u_pass)
                st.success("✅ Gotowe! Skopiuj poniższe dane do Arkusza Google:")
                st.code(f"KOLUMNA username: {new_u_name}\nKOLUMNA password: {gen_hash}")

        st.markdown("---")
        
        # 2. Przegląd bieżących danych
        col_v1, col_v2 = st.columns(2)
        with col_v1:
            st.subheader("Bieżący Cennik (BAZA)")
            st.dataframe(df_baza, use_container_width=True, height=300)
        with col_v2:
            st.subheader("Opłaty Dodatkowe")
            st.dataframe(df_oplaty, use_container_width=True)
            
        st.markdown("---")
        
        # 3. Kontrola synchronizacji
        st.write("Wszelkie zmiany stawek wykonuj bezpośrednio w Arkuszu Google. Aplikacja zaciągnie je po kliknięciu przycisku poniżej.")
        st.link_button("📂 EDYTUJ DANE W ARKUSZU GOOGLE", f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit")
        
        if st.button("🔄 WYMUŚ SYNCHRONIZACJĘ I CZYŚĆ CACHE", use_container_width=True):
            st.cache_data.clear()
            st.success("Cache wyczyszczony. Dane zostaną pobrane ponownie przy następnym kroku.")
            st.rerun()
