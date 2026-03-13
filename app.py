import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import re
import hashlib
import math
import numpy as np

# =================================================================
# 1. KONFIGURACJA I DANE STATYCZNE (DOKŁADNE DANE SQM)
# =================================================================
SHEET_ID = "1sYlXP6WVzPE09qfmydQYQNsjiZcDgRSJGyWoXfjmkDY"
URL_BAZA = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=CENNIK_BAZA"
URL_OPLATY = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=OPLATY_STALE"
URL_USERS = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=USERS"

# Kompletna baza tranzytowa (Dni drogi)
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

# =================================================================
# 2. FUNKCJE POMOCNICZE (CZYSZCZENIE I DANE)
# =================================================================
def hash_pass(p):
    return hashlib.sha256(p.strip().encode()).hexdigest()

@st.cache_data(ttl=60)
def load_all_remote_data():
    try:
        # Pobieranie 3 arkuszy jednocześnie
        b = pd.read_csv(URL_BAZA)
        o = pd.read_csv(URL_OPLATY)
        u = pd.read_csv(URL_USERS)
        
        # Standaryzacja nazw kolumn
        for df in [b, o, u]: df.columns = df.columns.str.strip()
        
        # Funkcja czyszcząca liczby (obsługa przecinków i walut)
        def clean_num(x):
            s = re.sub(r'[^\d.]', '', str(x).replace(',', '.'))
            return float(s) if s else 0.0
            
        for col in ['Eksport', 'Import', 'Postoj']:
            if col in b.columns: b[col] = b[col].apply(clean_num)
        o['Wartosc'] = o['Wartosc'].apply(clean_num)
        
        return b, o, dict(zip(u['username'].astype(str), u['password'].astype(str)))
    except Exception as e:
        st.error(f"KRYTYCZNY BŁĄD DANYCH: {e}")
        return pd.DataFrame(), pd.DataFrame(), {"admin": "f3e99d9459eeb7ffc4cd407d890fbf1db011208fa12d8edc501a7ec26da106a3"}

# =================================================================
# 3. INTERFEJS UŻYTKOWNIKA I CSS
# =================================================================
st.set_page_config(page_title="SQM VENTAGE v13.0 PRO", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #05070a !important; }
    [data-testid="stSidebar"] { background-color: #0f172a !important; border-right: 1px solid #1e293b; }
    
    /* Inputy */
    div[data-baseweb="select"] > div, div[data-baseweb="input"] > div, 
    .stNumberInput div[data-baseweb="input"], .stDateInput div[data-baseweb="input"] {
        background-color: #1e293b !important; color: #ffffff !important; border: 1px solid #334155 !important;
    }
    
    /* Nagłówki sekcji */
    .section-header { font-size: 24px; font-weight: 900; color: #ffffff; border-left: 5px solid #ed8936; padding-left: 15px; margin-bottom: 20px; }
    
    /* Branding */
    .brand-container { padding: 10px 0 20px 0; text-align: center; border-bottom: 1px solid #1e293b; margin-bottom: 20px; }
    .brand-logo { font-family: 'Inter', sans-serif; font-size: 20px; font-weight: 900; color: #ffffff; display: flex; align-items: center; justify-content: center; gap: 10px; }
    .brand-v { background: #ed8936; color: #000; padding: 2px 8px; border-radius: 4px; font-style: italic; }
    
    /* Karty wyników */
    .kpi-card { background: #1e293b; border: 1px solid #334155; border-radius: 12px; padding: 20px; text-align: center; }
    .kpi-value { font-size: 32px; font-weight: 900; color: #ed8936; }
    .kpi-label { font-size: 12px; color: #94a3b8; text-transform: uppercase; }
    </style>
""", unsafe_allow_html=True)

# =================================================================
# 4. LOGIKA SESJI I AUTORYZACJI
# =================================================================
df_baza, df_oplaty, user_db = load_all_remote_data()
cfg = dict(zip(df_oplaty['Parametr'], df_oplaty['Wartosc'])) if not df_oplaty.empty else {}

if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'user_role' not in st.session_state: st.session_state.user_role = ""

# Ekran Logowania
if not st.session_state.logged_in:
    _, center, _ = st.columns([1, 1, 1])
    with center:
        st.markdown("<div style='height:100px;'></div>", unsafe_allow_html=True)
        st.markdown("<h1 style='text-align:center; color:white;'>SQM VENTAGE</h1>", unsafe_allow_html=True)
        u = st.text_input("Login").strip()
        p = st.text_input("Hasło", type="password").strip()
        if st.button("ZALOGUJ DO SYSTEMU", use_container_width=True):
            if u in user_db and user_db[u] == hash_pass(p):
                st.session_state.logged_in = True
                st.session_state.user_role = str(u).lower()
                st.rerun()
            else:
                st.error("Błędne dane logowania.")
    st.stop()

# =================================================================
# 5. NAWIGACJA (SIDEBAR)
# =================================================================
with st.sidebar:
    st.markdown('<div class="brand-container"><div class="brand-logo"><span class="brand-v">V</span> SQM VENTAGE</div></div>', unsafe_allow_html=True)
    st.markdown(f"👤 Użytkownik: **{st.session_state.user_role.upper()}**")
    
    page = st.radio("WYBIERZ MODUŁ", ["📊 KALKULATOR", "⚙️ ADMIN TOOL", "📦 PLANOWANIE PRZESTRZENI"])
    
    st.markdown("---")
    
    if page == "📊 KALKULATOR":
        st.markdown("### PARAMETRY TRASY")
        target = st.selectbox("CEL", sorted(TRANSIT_DATA.keys()))
        trip_type = st.radio("TRYB", ["EXP + IMP", "ONE-WAY"])
        strategy = st.radio("ZAŁADUNEK", ["DEDYKOWANY", "DOŁADUNEK"])
        
        weight_netto = st.number_input("WAGA NETTO (KG)", value=1000, step=100)
        weight_brutto = weight_netto * 1.2 # Standard SQM
        
        d_montaz = st.date_input("DATA MONTAŻU", datetime.now() + timedelta(days=7))
        d_stay = 0
        if "EXP + IMP" in trip_type:
            d_demontaz = st.date_input("DATA DEMONTAŻU", d_montaz + timedelta(days=5))
            d_stay = max(0, (d_demontaz - d_montaz).days)

    if st.button("🚪 WYLOGUJ", use_container_width=True):
        st.session_state.logged_in = False
        st.rerun()

# =================================================================
# 6. MODUŁ: ADMIN TOOL
# =================================================================
if page == "⚙️ ADMIN TOOL":
    st.markdown('<div class="section-header">PANEL ADMINISTRATORA</div>', unsafe_allow_html=True)
    
    if st.session_state.user_role != "admin":
        st.warning("⚠️ Brak uprawnień do edycji stawek. Zaloguj się jako administrator.")
    else:
        st.success("Weryfikacja pomyślna. Dane synchronizowane z Google Sheets.")
        st.markdown(f"🔗 [Link do Arkusza Google](https://docs.google.com/spreadsheets/d/{SHEET_ID})")
        
        col_a, col_b = st.columns(2)
        with col_a:
            st.subheader("Baza Stawek")
            st.dataframe(df_baza, use_container_width=True)
        with col_b:
            st.subheader("Parametry Systemowe")
            st.table(df_oplaty)
    st.stop()

# =================================================================
# 7. MODUŁ: KALKULATOR (SILNIK LOGISTYCZNY)
# =================================================================
if page == "📊 KALKULATOR":
    st.markdown(f'<div class="section-header">KALKULACJA: KOMORNIKI ➔ {target.upper()}</div>', unsafe_allow_html=True)
    
    caps = {"BUS": 1200, "SOLO": 5500, "FTL": 10500}
    results = []

    if not df_baza.empty:
        for v_name, v_cap in caps.items():
            match = df_baza[(df_baza['Miasto'] == target) & (df_baza['Typ_Pojazdu'] == v_name)]
            if not match.empty:
                data = match.mean(numeric_only=True)
                v_count = math.ceil(weight_brutto / v_cap)
                transit = TRANSIT_DATA.get(target, {}).get("BUS" if v_name=="BUS" else "FTL/SOLO", 2)
                
                # Obliczanie frachtu
                if strategy == "DEDYKOWANY":
                    c_exp = data['Eksport'] * v_count
                    c_imp = (data['Import'] * v_count) if "EXP + IMP" in trip_type else 0
                else:
                    c_exp = data['Eksport'] * (weight_brutto / v_cap)
                    c_imp = (data['Import'] * (weight_brutto / v_cap)) if "EXP + IMP" in trip_type else 0
                
                # Dodatki regionalne i postoje
                ata = (cfg.get('ATA_CARNET', 166) if target in ["Londyn", "Genewa", "Liverpool", "Manchester"] else 0)
                ferry = (cfg.get('Ferry_UK', 450) if any(x in target for x in ["Londyn", "Liverpool", "Manchester"]) else 0)
                parking = (d_stay * cfg.get('PARKING_DAY', 30) * v_count)
                wait = (data['Postoj'] * d_stay * v_count)
                
                total = c_exp + c_imp + ata + ferry + parking + wait
                
                results.append({
                    "Pojazd": v_name, "Szt": v_count, "Suma €": total, 
                    "Exp €": c_exp, "Imp €": c_imp, "Inne €": ata+ferry+parking+wait,
                    "Tranzyt": transit, "Ładowanie": min(100, (weight_brutto/(v_count*v_cap))*100)
                })

    if results:
        best = min(results, key=lambda x: x['Suma €'])
        
        # Dashboard Wyników
        c1, c2, c3, c4 = st.columns(4)
        with c1: st.markdown(f'<div class="kpi-card"><div class="kpi-label">Koszt całkowity</div><div class="kpi-value">€ {best["Suma €"]:,.2f}</div></div>', unsafe_allow_html=True)
        with c2: st.markdown(f'<div class="kpi-card"><div class="kpi-label">Pojazd</div><div class="kpi-value">{best["Szt"]}x {best["Pojazd"]}</div></div>', unsafe_allow_html=True)
        with c3: st.markdown(f'<div class="kpi-card"><div class="kpi-label">Tranzyt</div><div class="kpi-value">{best["Tranzyt"]} Dni</div></div>', unsafe_allow_html=True)
        with c4: st.markdown(f'<div class="kpi-card"><div class="kpi-label">Waga Brutto</div><div class="kpi-value">{weight_brutto:,.0f} kg</div></div>', unsafe_allow_html=True)
        
        st.markdown("---")
        
        col_map, col_table = st.columns([1, 1.5])
        with col_map:
            st.success(f"🚚 Wyjazd: {(d_montaz - timedelta(days=best['Tranzyt']+1)).strftime('%Y-%m-%d')}")
            b_loc = CITY_COORDS["Komorniki (Baza)"]
            d_loc = CITY_COORDS.get(target, [50, 10])
            st.map(pd.DataFrame({'lat': [b_loc[0], d_loc[0]], 'lon': [b_loc[1], d_loc[1]]}), zoom=4)
        
        with col_table:
            st.subheader("Porównanie Ekonomiczne")
            res_df = pd.DataFrame(results)
            st.dataframe(res_df.style.format({"Suma €": "{:.2f}", "Ładowanie": "{:.0f}%"}), use_container_width=True)

# =================================================================
# 8. MODUŁ: PLANOWANIE PRZESTRZENI (PLACEHOLDER)
# =================================================================
if page == "📦 PLANOWANIE PRZESTRZENI":
    st.markdown('<div class="section-header">PLANOWANIE PRZESTRZENI NA NACZEPIE</div>', unsafe_allow_html=True)
    st.info("Moduł wizualizacji LDM / m3 jest w trakcie synchronizacji z bazą sprzętową SQM.")
