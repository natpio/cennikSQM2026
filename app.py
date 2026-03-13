import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import re
import hashlib
import math
import numpy as np

# ==========================================
# 1. KONFIGURACJA I SKOJARZENIA DANYCH
# ==========================================
SHEET_ID = "1sYlXP6WVzPE09qfmydQYQNsjiZcDgRSJGyWoXfjmkDY"
URL_BAZA = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=CENNIK_BAZA"
URL_OPLATY = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=OPLATY_STALE"
URL_USERS = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=USERS"

# Baza miast i tranzytów (Dni)
TRANSITS = {
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

COORDS = {
    "Komorniki (Baza)": [52.3358, 16.8122], "Amsterdam": [52.3702, 4.8952], 
    "Berlin": [52.5200, 13.4050], "Londyn": [51.5074, -0.1276],
    "Paryż": [48.8566, 2.3522], "Wiedeń": [48.2082, 16.3738], 
    "Praga": [50.0755, 14.4378], "Genewa": [46.2044, 6.1432], 
    "Barcelona": [41.3851, 2.1734], "Monachium": [48.1351, 11.5820], 
    "Madryt": [40.4168, -3.7038], "Lizbona": [38.7223, -9.1393],
    "Rzym": [41.9028, 12.4964], "Sztokholm": [59.3293, 18.0686]
}

# ==========================================
# 2. STYLE CSS (EKSTREMALNY KONTRAST)
# ==========================================
st.set_page_config(page_title="SQM VENTAGE v15.0", layout="wide")

st.markdown("""
    <style>
    /* Globalne tło */
    .stApp { background-color: #0a0e14 !important; }
    
    /* SIDEBAR - NAPRAWA KONTRASTU */
    [data-testid="stSidebar"] { background-color: #111827 !important; border-right: 1px solid #1f2937; }
    [data-testid="stSidebar"] .stMarkdown p, 
    [data-testid="stSidebar"] label, 
    [data-testid="stSidebar"] .stSubheader { 
        color: #FFFFFF !important; 
        font-weight: 700 !important; 
        font-size: 15px !important;
        opacity: 1 !important;
    }
    
    /* Naprawa pól wprowadzania */
    div[data-baseweb="input"] { background-color: #1f2937 !important; border-radius: 8px !important; }
    input { color: #FFFFFF !important; }
    
    /* Branding */
    .brand { font-size: 24px; font-weight: 900; color: #FFFFFF; text-align: center; padding-bottom: 20px; border-bottom: 2px solid #f97316; margin-bottom: 20px; }
    .v-tag { background: #f97316; color: #000; padding: 2px 10px; border-radius: 4px; margin-right: 8px; }
    
    /* Karty KPI */
    .metric-card { background: #1f2937; border: 1px solid #374151; padding: 20px; border-radius: 12px; text-align: center; }
    .metric-val { color: #f97316; font-size: 36px; font-weight: 900; }
    .metric-lbl { color: #9ca3af; font-size: 12px; text-transform: uppercase; margin-top: 5px; }
    
    /* Tabela */
    .stDataFrame { border: 1px solid #374151 !important; border-radius: 10px !important; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 3. LOGIKA SYSTEMOWA (AUTH & DATA)
# ==========================================
def make_hash(p): return hashlib.sha256(p.strip().encode()).hexdigest()

@st.cache_data(ttl=60)
def load_data():
    try:
        b = pd.read_csv(URL_BAZA); o = pd.read_csv(URL_OPLATY); u = pd.read_csv(URL_USERS)
        for d in [b, o, u]: d.columns = d.columns.str.strip()
        def cln(v):
            s = re.sub(r'[^\d.]', '', str(v).replace(',', '.'))
            return float(s) if s else 0.0
        for c in ['Eksport', 'Import', 'Postoj']: 
            if c in b.columns: b[c] = b[c].apply(cln)
        o['Wartosc'] = o['Wartosc'].apply(cln)
        return b, o, dict(zip(u['username'].astype(str), u['password'].astype(str)))
    except:
        return pd.DataFrame(), pd.DataFrame(), {"admin": "f3e99d9459eeb7ffc4cd407d890fbf1db011208fa12d8edc501a7ec26da106a3"}

# Inicjalizacja Sesji
if 'auth_active' not in st.session_state: st.session_state.auth_active = False
if 'user_name' not in st.session_state: st.session_state.user_name = ""

df_baza, df_oplaty, users = load_data()
cfg = dict(zip(df_oplaty['Parametr'], df_oplaty['Wartosc'])) if not df_oplaty.empty else {}

# --- EKRAN LOGOWANIA ---
if not st.session_state.auth_active:
    _, center, _ = st.columns([1, 1, 1])
    with center:
        st.markdown("<div style='height:150px;'></div>", unsafe_allow_html=True)
        st.markdown("<h1 style='text-align:center; color:white;'>SQM VENTAGE</h1>", unsafe_allow_html=True)
        u = st.text_input("Użytkownik", key="login_u")
        p = st.text_input("Hasło", type="password", key="login_p")
        if st.button("ZALOGUJ", use_container_width=True):
            if u in users and users[u] == make_hash(p):
                st.session_state.auth_active = True
                st.session_state.user_name = str(u)
                st.rerun()
            else:
                st.error("Błąd logowania.")
    st.stop()

# ==========================================
# 4. INTERFEJS GŁÓWNY (SIDEBAR)
# ==========================================
with st.sidebar:
    st.markdown('<div class="brand"><span class="v-tag">V15</span> SQM VENTAGE</div>', unsafe_allow_html=True)
    st.markdown(f"Zalogowano: **{st.session_state.user_name.upper()}**")
    
    menu = st.radio("MODUŁY", ["📊 KALKULATOR", "⚙️ ADMIN", "📦 LOGISTYKA"])
    
    st.markdown("---")
    st.subheader("PARAMETRY")
    city = st.selectbox("MIASTO DOCELOWE", sorted(TRANSITS.keys()))
    mode = st.radio("KIERUNEK", ["Eksport + Import", "Tylko Eksport"])
    weight = st.number_input("WAGA NETTO (KG)", value=1000, step=100)
    w_brutto = weight * 1.2
    
    d_m = st.date_input("DATA MONTAŻU", datetime.now() + timedelta(days=7))
    d_stay = 0
    if "Import" in mode:
        d_d = st.date_input("DATA DEMONTAŻU", d_m + timedelta(days=5))
        d_stay = max(0, (d_d - d_m).days)
    
    st.markdown("---")
    if st.button("🚪 WYLOGUJ", use_container_width=True):
        st.session_state.auth_active = False
        st.session_state.user_name = ""
        st.rerun()

# ==========================================
# 5. MODUŁ ADMINA
# ==========================================
if menu == "⚙️ ADMIN":
    st.header("Konfiguracja Systemu")
    if st.session_state.user_name.lower() != "admin":
        st.error("Brak uprawnień. Zaloguj się jako administrator.")
    else:
        st.info(f"Synchronizacja z Google Sheets: [LINK](https://docs.google.com/spreadsheets/d/{SHEET_ID})")
        col1, col2 = st.columns(2)
        with col1: st.subheader("Cennik"); st.dataframe(df_baza, use_container_width=True)
        with col2: st.subheader("Parametry"); st.table(df_oplaty)
    st.stop()

# ==========================================
# 6. SILNIK KALKULACJI I WIDOK
# ==========================================
if menu == "📊 KALKULATOR":
    st.markdown(f"<h2 style='color:white;'>TRASA: KOMORNIKI ➔ {city.upper()}</h2>", unsafe_allow_html=True)
    
    v_types = {"BUS": 1200, "SOLO": 5500, "FTL": 10500}
    results = []

    for v_n, v_c in v_types.items():
        match = df_baza[(df_baza['Miasto'] == city) & (df_baza['Typ_Pojazdu'] == v_n)]
        if not match.empty:
            row = match.mean(numeric_only=True)
            count = math.ceil(w_brutto / v_c)
            tranz = TRANSITS.get(city, {}).get("BUS" if v_n=="BUS" else "FTL/SOLO", 2)
            
            # Obliczenia
            c_exp = row['Eksport'] * count
            c_imp = (row['Import'] * count) if "Import" in mode else 0
            
            # Dodatki (ATA, Ferry, Parking)
            ata = (cfg.get('ATA_CARNET', 166) if city in ["Londyn", "Genewa", "Liverpool", "Manchester"] else 0)
            ferry = (cfg.get('Ferry_UK', 450) if any(x in city for x in ["Londyn", "Liverpool", "Manchester"]) else 0)
            wait = (row['Postoj'] * d_stay * count) + (d_stay * cfg.get('PARKING_DAY', 30) * count)
            
            total = c_exp + c_imp + ata + ferry + wait
            
            results.append({
                "Pojazd": v_n, "Szt": count, "Suma €": round(total, 2), 
                "Exp €": round(c_exp, 2), "Imp €": round(c_imp, 2), "Inne €": round(ata+ferry+wait, 2),
                "Tranz": tranz, "Ładowanie": min(100, (w_brutto/(count*v_c))*100)
            })

    if results:
        best = min(results, key=lambda x: x['Suma €'])
        
        # Dashboard KPI
        c1, c2, c3, c4 = st.columns(4)
        with c1: st.markdown(f'<div class="metric-card"><div class="metric-val">€ {best["Suma €"]:,.2f}</div><div class="metric-lbl">Najlepsza Cena</div></div>', unsafe_allow_html=True)
        with c2: st.markdown(f'<div class="metric-card"><div class="metric-val">{best["Szt"]}x {best["Pojazd"]}</div><div class="metric-lbl">Pojazd</div></div>', unsafe_allow_html=True)
        with c3: st.markdown(f'<div class="metric-card"><div class="metric-val">{best["Tranz"]} Dni</div><div class="metric-lbl">Tranzyt</div></div>', unsafe_allow_html=True)
        with k4: st.markdown(f'<div class="metric-card"><div class="metric-val">{w_brutto:,.0f} kg</div><div class="metric-lbl">Waga Brutto</div></div>', unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Tabela i Mapa
        col_left, col_right = st.columns([1.6, 1])
        
        with col_left:
            st.subheader("Porównanie Ekonomiczne")
            res_df = pd.DataFrame(results)
            st.dataframe(
                res_df,
                column_config={
                    "Suma €": st.column_config.NumberColumn(format="€ %.2f"),
                    "Exp €": st.column_config.NumberColumn(format="€ %.2f"),
                    "Imp €": st.column_config.NumberColumn(format="€ %.2f"),
                    "Inne €": st.column_config.NumberColumn(format="€ %.2f"),
                    "Ładowanie": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%d%%")
                },
                use_container_width=True,
                hide_index=True
            )
            st.warning(f"🚚 Sugerowany wyjazd z bazy: {(d_m - timedelta(days=best['Tranz']+1)).strftime('%Y-%m-%d')}")

        with col_right:
            st.subheader("Trasa")
            s_pos = COORDS["Komorniki (Baza)"]
            e_pos = COORDS.get(city, [50, 10])
            route = pd.DataFrame({'lat': np.linspace(s_pos[0], e_pos[0], 10), 'lon': np.linspace(s_pos[1], e_pos[1], 10)})
            st.map(route, color="#f97316", zoom=4)

if menu == "📦 LOGISTYKA":
    st.info("Moduł planowania załadunku (LDM) w przygotowaniu.")
