import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import re
import hashlib
import math
import numpy as np

# =================================================================
# 1. KONFIGURACJA I DANE (SQM LOGISTICS CORE)
# =================================================================
SHEET_ID = "1sYlXP6WVzPE09qfmydQYQNsjiZcDgRSJGyWoXfjmkDY"
URL_BAZA = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=CENNIK_BAZA"
URL_OPLATY = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=OPLATY_STALE"
URL_USERS = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=USERS"

# Baza tranzytowa SQM Multimedia Solutions
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
# 2. LOGIKA SYSTEMOWA (AUTH & DATA)
# =================================================================
st.set_page_config(page_title="SQM VENTAGE v14.0", layout="wide", initial_sidebar_state="expanded")

def get_hash(password):
    return hashlib.sha256(password.strip().encode()).hexdigest()

@st.cache_data(ttl=60)
def load_sqm_data():
    try:
        b = pd.read_csv(URL_BAZA)
        o = pd.read_csv(URL_OPLATY)
        u = pd.read_csv(URL_USERS)
        for df in [b, o, u]: df.columns = df.columns.str.strip()
        def clean(v):
            s = re.sub(r'[^\d.]', '', str(v).replace(',', '.'))
            return float(s) if s else 0.0
        for c in ['Eksport', 'Import', 'Postoj']: 
            if c in b.columns: b[c] = b[c].apply(clean)
        o['Wartosc'] = o['Wartosc'].apply(clean)
        return b, o, dict(zip(u['username'].astype(str), u['password'].astype(str)))
    except:
        return pd.DataFrame(), pd.DataFrame(), {"admin": "f3e99d9459eeb7ffc4cd407d890fbf1db011208fa12d8edc501a7ec26da106a3"}

df_baza, df_oplaty, user_db = load_sqm_data()
cfg = dict(zip(df_oplaty['Parametr'], df_oplaty['Wartosc'])) if not df_oplaty.empty else {}

# Inicjalizacja sesji (Stabilna)
if 'auth' not in st.session_state: st.session_state.auth = False
if 'user' not in st.session_state: st.session_state.user = ""

# Interfejs CSS
st.markdown("""
    <style>
    .stApp { background-color: #05070a !important; }
    [data-testid="stSidebar"] { background-color: #0f172a !important; border-right: 1px solid #1e293b; }
    
    /* Naprawa kontrastu czcionek na sidebarze */
    [data-testid="stSidebar"] .stMarkdown p, [data-testid="stSidebar"] label p { 
        color: #e2e8f0 !important; font-size: 14px !important; font-weight: 600 !important;
    }
    [data-testid="stSidebar"] .stRadio div[role="radiogroup"] label { color: #ffffff !important; }

    /* Inputy */
    div[data-baseweb="select"] > div, div[data-baseweb="input"] > div, 
    .stNumberInput div[data-baseweb="input"], .stDateInput div[data-baseweb="input"] {
        background-color: #1e293b !important; color: #ffffff !important; border: 1px solid #334155 !important;
    }
    
    /* Karty i UI */
    .sqm-header { font-size: 28px; font-weight: 900; color: #ffffff; border-left: 6px solid #ed8936; padding-left: 20px; margin-bottom: 25px; }
    .kpi-box { background: #1e293b; border: 1px solid #334155; border-radius: 12px; padding: 22px; text-align: center; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); }
    .kpi-val { font-size: 34px; font-weight: 900; color: #ed8936; line-height: 1; }
    .kpi-lab { font-size: 11px; color: #94a3b8; text-transform: uppercase; letter-spacing: 1px; margin-top: 8px; }
    
    .brand-logo { font-size: 22px; font-weight: 900; color: #ffffff; text-align: center; padding: 20px 0; border-bottom: 1px solid #1e293b; margin-bottom: 20px; }
    .brand-v { background: #ed8936; color: #000; padding: 2px 8px; border-radius: 4px; font-style: italic; margin-right: 5px; }
    </style>
""", unsafe_allow_html=True)

# =================================================================
# 3. PANEL LOGOWANIA
# =================================================================
if not st.session_state.auth:
    _, col, _ = st.columns([1, 1.1, 1])
    with col:
        st.markdown("<div style='height:120px;'></div>", unsafe_allow_html=True)
        st.markdown("<h1 style='text-align:center; color:white;'>SQM VENTAGE</h1>", unsafe_allow_html=True)
        u_in = st.text_input("Użytkownik", key="log_u").strip()
        p_in = st.text_input("Hasło", type="password", key="log_p").strip()
        if st.button("ZALOGUJ", use_container_width=True):
            if u_in in user_db and user_db[u_in] == get_hash(p_in):
                st.session_state.auth = True
                st.session_state.user = str(u_in)
                st.rerun()
            else:
                st.error("Błąd autoryzacji.")
    st.stop()

# =================================================================
# 4. NAWIGACJA (SIDEBAR)
# =================================================================
with st.sidebar:
    st.markdown('<div class="brand-logo"><span class="brand-v">V</span> SQM VENTAGE</div>', unsafe_allow_html=True)
    st.markdown(f"👤 Operator: **{st.session_state.user.upper()}**")
    
    view = st.radio("MENU SYSTEMOWE", ["📊 KALKULATOR FRachtu", "⚙️ ADMIN TOOL", "📦 PLANOWANIE NACZEPY"])
    
    st.markdown("---")
    if view == "📊 KALKULATOR FRachtu":
        st.subheader("PARAMETRY TRASY")
        dest = st.selectbox("CEL PODRÓŻY", sorted(TRANSIT_DATA.keys()))
        t_mode = st.radio("TYP TRASY", ["PEŁNA (EXP+IMP)", "ONE-WAY"])
        strategy = st.radio("ŁADUNEK", ["DEDYKOWANY", "DOŁADUNEK"])
        weight = st.number_input("WAGA NETTO (KG)", value=1000, step=100) * 1.2 # Brutto
        d_m = st.date_input("MONTAŻ", datetime.now() + timedelta(days=7))
        d_stay = 0
        if "PEŁNA" in t_mode:
            d_d = st.date_input("DEMONTAŻ", d_m + timedelta(days=5))
            d_stay = max(0, (d_d - d_m).days)

    if st.button("🚪 WYLOGUJ", use_container_width=True):
        st.session_state.auth = False
        st.session_state.user = ""
        st.rerun()

# =================================================================
# 5. WIDOK: ADMIN TOOL
# =================================================================
if view == "⚙️ ADMIN TOOL":
    st.markdown('<div class="sqm-header">ADMINISTRACJA SYSTEMEM</div>', unsafe_allow_html=True)
    if st.session_state.user.lower() != "admin":
        st.error(f"Brak uprawnień. Zalogowano jako: '{st.session_state.user}'.")
        st.info("Sekcja dostępna tylko dla konta 'admin'.")
    else:
        st.success("Dostęp autoryzowany.")
        st.markdown(f"🔗 [Edytuj bazę w Google Sheets](https://docs.google.com/spreadsheets/d/{SHEET_ID})")
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Stawki bazowe")
            st.dataframe(df_baza, use_container_width=True)
        with c2:
            st.subheader("Koszty stałe")
            st.table(df_oplaty)
    st.stop()

# =================================================================
# 6. WIDOK: KALKULATOR (LOGIKA I FORMATOWANIE)
# =================================================================
if view == "📊 KALKULATOR FRachtu":
    st.markdown(f'<div class="sqm-header">KALKULACJA: KOMORNIKI ➔ {dest.upper()}</div>', unsafe_allow_html=True)
    
    caps = {"BUS": 1200, "SOLO": 5500, "FTL": 10500}
    results = []

    if not df_baza.empty:
        for v_n, v_c in caps.items():
            match = df_baza[(df_baza['Miasto'] == dest) & (df_baza['Typ_Pojazdu'] == v_n)]
            if not match.empty:
                r = match.mean(numeric_only=True)
                qty = math.ceil(weight / v_c)
                transit = TRANSIT_DATA.get(dest, {}).get("BUS" if v_n=="BUS" else "FTL/SOLO", 2)
                
                # Koszty frachtu
                c_e = r['Eksport'] * (qty if strategy=="DEDYKOWANY" else weight/v_c)
                c_i = (r['Import'] * (qty if strategy=="DEDYKOWANY" else weight/v_c)) if "PEŁNA" in t_mode else 0
                
                # Opcje UK / CH
                ata = (cfg.get('ATA_CARNET', 166) if dest in ["Londyn", "Genewa", "Liverpool", "Manchester"] else 0)
                ferry = (cfg.get('Ferry_UK', 450) if any(x in dest for x in ["Londyn", "Liverpool", "Manchester"]) else 0)
                wait = (r['Postoj'] * d_stay * qty) + (d_stay * cfg.get('PARKING_DAY', 30) * qty)
                
                total = c_e + c_i + ata + ferry + wait
                
                results.append({
                    "Pojazd": v_n, "Szt": qty, "Suma €": round(total, 2), 
                    "Exp €": round(c_e, 2), "Imp €": round(c_i, 2), "Inne €": round(ata+ferry+wait, 2),
                    "Tranz": transit, "Ładowanie": min(100, (weight/(qty*v_c))*100)
                })

    if results:
        best = min(results, key=lambda x: x['Suma €'])
        
        # Dashboard KPI
        k1, k2, k3, k4 = st.columns(4)
        with k1: st.markdown(f'<div class="kpi-box"><div class="kpi-val">€ {best["Suma €"]:,.2f}</div><div class="kpi-lab">Najniższy Koszt</div></div>', unsafe_allow_html=True)
        with k2: st.markdown(f'<div class="kpi-box"><div class="kpi-val">{best["Szt"]}x {best["Pojazd"]}</div><div class="kpi-lab">Rekomendacja</div></div>', unsafe_allow_html=True)
        with k3: st.markdown(f'<div class="kpi-box"><div class="kpi-val">{best["Tranz"]} Dni</div><div class="kpi-lab">Czas Tranzytu</div></div>', unsafe_allow_html=True)
        with k4: st.markdown(f'<div class="kpi-box"><div class="kpi-val">{weight:,.0f} kg</div><div class="kpi-lab">Waga Brutto</div></div>', unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Sekcja dolna: Tabela po lewej, Mapa po prawej
        col_table, col_map = st.columns([1.5, 1])
        
        with col_table:
            st.subheader("Porównanie Ekonomiczne")
            res_df = pd.DataFrame(results)
            # Formatowanie tabeli, aby nie było naukowego zapisu i zbędnych zer
            st.dataframe(
                res_df.style.format({
                    "Suma €": "{:.2f}", 
                    "Exp €": "{:.2f}", 
                    "Imp €": "{:.2f}", 
                    "Inne €": "{:.2f}", 
                    "Ładowanie": "{:.0f}%"
                }), 
                use_container_width=True
            )
        
        with col_map:
            st.subheader("Trasa Przejazdu")
            st.info(f"🚚 Wyjazd: {(d_m - timedelta(days=best['Tranz']+1)).strftime('%Y-%m-%d')}")
            
            # Generowanie punktów trasy dla mapy
            start_pos = CITY_COORDS["Komorniki (Baza)"]
            end_pos = CITY_COORDS.get(dest, [50, 10])
            route_pts = pd.DataFrame({
                'lat': np.linspace(start_pos[0], end_pos[0], 10),
                'lon': np.linspace(start_pos[1], end_pos[1], 10)
            })
            st.map(route_pts, color="#ed8936", zoom=4)

# =================================================================
# 7. MODUŁ: PLANOWANIE NACZEPY
# =================================================================
if view == "📦 PLANOWANIE NACZEPY":
    st.markdown('<div class="sqm-header">PLANOWANIE PRZESTRZENI (LDM)</div>', unsafe_allow_html=True)
    st.warning("Trwa integracja z bazą wymiarów Case-ów SQM.")
