import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import re
import hashlib
import extra_streamlit_components as stx
import math
import numpy as np

# --- KONFIGURACJA ZASOBÓW ---
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
    "Berlin": [52.5200, 13.4050], "Londyn": [51.5074, -0.1276],
    "Paryż": [48.8566, 2.3522], "Wiedeń": [48.2082, 16.3738], 
    "Praga": [50.0755, 14.4378], "Genewa": [46.2044, 6.1432], 
    "Barcelona": [41.3851, 2.1734], "Monachium": [48.1351, 11.5820], 
    "Madryt": [40.4168, -3.7038], "Lizbona": [38.7223, -9.1393],
    "Rzym": [41.9028, 12.4964], "Sztokholm": [59.3293, 18.0686]
}

st.set_page_config(page_title="SQM LOGISTICS v16.0", layout="wide")

# --- STYLE CSS (FIX WIDOCZNOŚCI) ---
st.markdown("""
    <style>
    .stApp { background-color: #05070a !important; }
    [data-testid="stSidebar"] { background-color: #0f172a !important; border-right: 1px solid #1e293b; }
    
    /* Naprawa pól tekstowych - czarny tekst, białe tło */
    .stTextInput input, .stNumberInput input, .stSelectbox div[data-baseweb="select"] {
        color: #000000 !important;
        background-color: #ffffff !important;
        -webkit-text-fill-color: #000000 !important;
        font-weight: 600 !important;
    }
    
    [data-testid="stSidebar"] label p { color: #ffffff !important; font-weight: 700 !important; }
    [data-testid="stSidebarNav"] { display: none; }

    .route-header { font-size: 32px !important; font-weight: 900; color: #ffffff; border-bottom: 3px solid #ed8936; margin-bottom: 25px; }
    .hero-card { background: linear-gradient(145deg, #1e293b, #0f172a); border: 1px solid #334155; border-radius: 20px; padding: 35px; }
    .main-price-value { color: #ffffff; font-size: 85px; font-weight: 950; }
    .cost-row { display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid #1e293b; color: white; }
    </style>
""", unsafe_allow_html=True)

# --- SYSTEM AUTORYZACJI ---
def make_hash(p): return hashlib.sha256(p.strip().encode()).hexdigest()
cookie_manager = stx.CookieManager()

if "auth" not in st.session_state:
    st.session_state.auth = False
    st.session_state.user = None

@st.cache_data(ttl=10)
def load_users():
    try:
        df = pd.read_csv(URL_USERS)
        df.columns = df.columns.str.strip()
        return dict(zip(df['username'].astype(str).str.lower(), df['password'].astype(str)))
    except:
        return {"admin": "f3e99d9459eeb7ffc4cd407d890fbf1db011208fa12d8edc501a7ec26da106a3"}

user_db = load_users()
c_token = cookie_manager.get(cookie="sqm_session_v16")

if c_token and c_token.lower() in user_db:
    st.session_state.auth, st.session_state.user = True, c_token

if not st.session_state.auth:
    _, col, _ = st.columns([1, 1.2, 1])
    with col:
        st.markdown("<h2 style='text-align:center; color:white;'>SQM LOGISTICS</h2>", unsafe_allow_html=True)
        u_in = st.text_input("Użytkownik", key="login_u").strip().lower()
        p_in = st.text_input("Hasło", type="password", key="login_p")
        if st.button("ZALOGUJ", use_container_width=True):
            if u_in in user_db and user_db[u_in] == make_hash(p_in):
                st.session_state.auth, st.session_state.user = True, u_in
                cookie_manager.set("sqm_session_v16", u_in, expires_at=datetime.now()+timedelta(days=7))
                st.rerun()
    st.stop()

# --- DANE ---
@st.cache_data(ttl=60)
def fetch_logs():
    b = pd.read_csv(URL_BAZA); o = pd.read_csv(URL_OPLATY); b.columns = b.columns.str.strip()
    def clean(v):
        s = re.sub(r'[^\d.]', '', str(v).replace(',', '.')); return float(s) if s else 0.0
    for c in ['Eksport', 'Import', 'Postoj']: b[c] = b[c].apply(clean)
    o['Wartosc'] = o['Wartosc'].apply(clean)
    return b, o

df_baza, df_oplaty = fetch_logs()
cfg = dict(zip(df_oplaty['Parametr'], df_oplaty['Wartosc']))

# --- SIDEBAR ---
with st.sidebar:
    st.image("https://www.sqm.pl/wp-content/themes/sqm/img/logo-sqm.png", width=180)
    st.markdown(f"**Użytkownik:** {st.session_state.user.upper()}")
    
    # NAWIGACJA
    page = st.radio("MODUŁ", ["KALKULATOR", "ADMIN TOOL"])
    st.markdown("---")
    
    if page == "KALKULATOR":
        mode = st.radio("STRATEGIA", ["DEDYKOWANY", "DOŁADUNEK"])
        target = st.selectbox("CEL PODRÓŻY", sorted(TRANSIT_DATA.keys()))
        weight = st.number_input("WAGA (kg)", value=1000, step=500)
        d_start = st.date_input("ZAŁADUNEK", datetime.now() + timedelta(days=5))
        d_end = st.date_input("POWRÓT", datetime.now() + timedelta(days=10))
        days_stay = max(0, (d_end - d_start).days)
    
    # PRZYCISK WYLOGOWANIA (NAPRAWIONY)
    if st.button("🔴 WYLOGUJ", use_container_width=True):
        cookie_manager.delete("sqm_session_v16")
        for key in st.session_state.keys():
            del st.session_state[key]
        st.rerun()

# --- LOGIKA MODUŁÓW ---
if page == "ADMIN TOOL":
    st.markdown('<div class="route-header">ADMIN TOOL & GENERATOR</div>', unsafe_allow_html=True)
    
    # Sekcja Generatora Haseł
    st.write("### 🔑 GENERATOR HASHY (DLA ARKUSZA USERS)")
    raw_p = st.text_input("Wpisz nowe hasło do zahashowania:", type="password")
    if raw_p:
        new_h = make_hash(raw_p)
        st.code(new_h, language="text")
        st.info("Skopiuj powyższy kod i wklej go do kolumny 'password' w arkuszu USERS.")
    
    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        st.write("### ⚙️ EDYCJA OPŁAT")
        st.data_editor(df_oplaty, use_container_width=True)
    with col2:
        st.write("### 🚛 PODGLĄD BAZY")
        st.dataframe(df_baza, use_container_width=True)

else:
    # --- KALKULACJE ---
    w_eff = weight * cfg.get('WAGA_BUFOR', 1.2)
    caps = {"BUS": 1200, "SOLO": 5500, "FTL": 10500}
    results = []

    for v_type, cap in caps.items():
        res = df_baza[(df_baza['Miasto'] == target) & (df_baza['Typ_Pojazdu'] == v_type)]
        if not res.empty:
            r = res.mean(numeric_only=True)
            v_count = math.ceil(w_eff / cap)
            transit_days = TRANSIT_DATA.get(target, {}).get("BUS" if v_type == "BUS" else "FTL/SOLO", 2)
            
            exp = (r['Eksport'] * v_count if mode == "DEDYKOWANY" else r['Eksport'] * (w_eff/cap))
            imp = (r['Import'] * v_count if mode == "DEDYKOWANY" else r['Import'] * (w_eff/cap))
            ata = (cfg.get('ATA_CARNET', 166) if target in ["Londyn", "Genewa", "Liverpool", "Manchester"] else 0)
            ferry = (cfg.get('Ferry_UK', 450) if "Londyn" in target or "Manchester" in target else 0)
            parking = (days_stay * cfg.get('PARKING_DAY', 30) * v_count)
            stay_cost = r['Postoj'] * days_stay * v_count
            
            results.append({
                "Pojazd": v_type, "Szt": v_count, "Total": exp+imp+stay_cost+parking+ata+ferry,
                "exp": exp, "imp": imp, "transit": transit_days, "load": min(100, (w_eff/(v_count*cap))*100)
            })

    if results:
        best = min(results, key=lambda x: x['Total'])
        st.markdown(f'<div class="route-header">TRASA: KOMORNIKI ➔ {target.upper()}</div>', unsafe_allow_html=True)
        
        c1, c2 = st.columns([2, 1])
        with c1:
            st.markdown(f"""
                <div class="hero-card">
                    <div style="color: #ed8936; font-weight: 800;">ESTYMACJA KOSZTÓW (NETTO)</div>
                    <div class="main-price-value">€ {best['Total']:,.2f}</div>
                    <p style="color: #94a3b8;">Najlepsza opcja: {best['Pojazd']} ({best['Szt']} szt.) | Załadowanie: {best['load']:.0f}%</p>
                </div>
            """, unsafe_allow_html=True)
            
            st.write("### 🚛 INNE MOŻLIWOŚCI")
            for r in sorted(results, key=lambda x: x['Total']):
                st.markdown(f"**{r['Pojazd']}**: € {r['Total']:,.2f} (Tranzyt: {r['transit']} dni)")

        with c2:
            st.write("### 📍 MAPA I TERMINY")
            b_p, d_p = CITY_COORDS["Komorniki (Baza)"], CITY_COORDS.get(target, [48.8, 2.3])
            path_df = pd.DataFrame({'lat': np.linspace(b_p[0], d_p[0], 20), 'lon': np.linspace(b_p[1], d_p[1], 20)})
            st.map(path_df, color='#ed8936')
            st.info(f"Sugerowany wyjazd: {(d_start - timedelta(days=best['transit'])).strftime('%Y-%m-%d')}")
