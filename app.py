import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import re
import hashlib
import math
import numpy as np

# ==========================================
# 1. KONFIGURACJA ZASOBÓW (SQM CORE)
# ==========================================
SHEET_ID = "1sYlXP6WVzPE09qfmydQYQNsjiZcDgRSJGyWoXfjmkDY"
URL_BAZA = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=CENNIK_BAZA"
URL_OPLATY = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=OPLATY_STALE"
URL_USERS = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=USERS"

# Dane tranzytowe SQM
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

# ==========================================
# 2. EKSTREMALNY DESIGN CSS (ULTRA-WIDOCZNOŚĆ)
# ==========================================
st.set_page_config(page_title="SQM VENTAGE v16.2", layout="wide")

st.markdown("""
    <style>
    /* Globalne tło aplikacji */
    .stApp { background-color: #05070a !important; }
    
    /* NAPRAWA RUBRYK - BIAŁE TŁO, CZARNY TEKST (Rozwiązuje problem ze screenów) */
    div[data-baseweb="input"], div[data-baseweb="select"], .stNumberInput div, .stDateInput div {
        background-color: #FFFFFF !important;
        border: 2px solid #ed8936 !important;
        border-radius: 8px !important;
    }
    input, select, span, div[role="listbox"] {
        color: #000000 !important;
        font-weight: 800 !important;
        -webkit-text-fill-color: #000000 !important;
    }
    
    /* Pasek boczny - Etykiety */
    [data-testid="stSidebar"] { background-color: #0f172a !important; }
    [data-testid="stSidebar"] label p { 
        color: #FFFFFF !important; 
        font-weight: 900 !important; 
        text-transform: uppercase;
        font-size: 13px !important;
    }

    /* Nagłówek i Karty Wyników */
    .route-header { font-size: 30px !important; font-weight: 900; color: #FFFFFF; border-bottom: 3px solid #ed8936; margin-bottom: 20px; }
    .hero-card { background: linear-gradient(145deg, #1e293b, #0f172a); border: 1px solid #334155; border-radius: 20px; padding: 30px; margin-bottom: 25px; }
    .main-price-value { color: #FFFFFF; font-size: 75px; font-weight: 950; line-height: 1; margin: 15px 0; }
    
    /* Grid danych */
    .data-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin-top: 20px; }
    .data-item { background: rgba(255,255,255,0.05); padding: 12px; border-radius: 10px; border: 1px solid rgba(255,255,255,0.1); }
    .data-label { color: #94a3b8 !important; font-size: 10px; font-weight: 700; text-transform: uppercase; }
    .data-value { color: #FFFFFF !important; font-size: 20px; font-weight: 900; }
    
    /* Tabela Porównawcza */
    .alt-card { background: #0f172a; border-left: 5px solid #475569; padding: 15px; margin-bottom: 10px; border-radius: 8px; display: flex; justify-content: space-between; align-items: center; }
    .alt-best { border-left-color: #ed8936; background: rgba(237, 137, 54, 0.15); }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 3. LOGIKA SYSTEMOWA (AUTH & DATA)
# ==========================================
def make_hash(p): return hashlib.sha256(p.strip().encode()).hexdigest()

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
    st.session_state.user = ""

@st.cache_data(ttl=300)
def load_users():
    try:
        df = pd.read_csv(URL_USERS); df.columns = df.columns.str.strip()
        return dict(zip(df['username'].astype(str), df['password'].astype(str)))
    except:
        return {"admin": "f3e99d9459eeb7ffc4cd407d890fbf1db011208fa12d8edc501a7ec26da106a3"}

# LOGOWANIE
if not st.session_state.authenticated:
    _, col, _ = st.columns([1, 1.2, 1])
    with col:
        st.markdown("<h2 style='text-align:center; color:white; margin-top:50px;'>SQM LOGISTICS</h2>", unsafe_allow_html=True)
        u = st.text_input("Użytkownik", key="l_u")
        p = st.text_input("Hasło", type="password", key="l_p")
        if st.button("ZALOGUJ", use_container_width=True):
            db = load_users()
            if u in db and db[u] == make_hash(p):
                st.session_state.authenticated = True
                st.session_state.user = u
                st.rerun()
            else: st.error("Błędne dane.")
    st.stop()

# POBIERANIE DANYCH LOGISTYCZNYCH
@st.cache_data(ttl=60)
def fetch_logs():
    b = pd.read_csv(URL_BAZA); o = pd.read_csv(URL_OPLATY)
    b.columns = b.columns.str.strip()
    if 'Dostawca' in b.columns:
        b = b[~b['Dostawca'].str.contains('SQM|Własny|Wlasny', case=False, na=False)]
    def clean(v):
        s = re.sub(r'[^\d.]', '', str(v).replace(',', '.'))
        return float(s) if s else 0.0
    for c in ['Eksport', 'Import', 'Postoj']: b[c] = b[c].apply(clean)
    o['Wartosc'] = o['Wartosc'].apply(clean)
    return b, o

df_baza, df_oplaty = fetch_logs()
cfg = dict(zip(df_oplaty['Parametr'], df_oplaty['Wartosc']))

# ==========================================
# 4. SIDEBAR - PARAMETRY TRASY
# ==========================================
with st.sidebar:
    st.image("https://www.sqm.pl/wp-content/themes/sqm/img/logo-sqm.png", width=180)
    st.markdown(f"<p style='color:#ed8936; font-size:16px; font-weight:900;'>OPERATOR: {st.session_state.user.upper()}</p>", unsafe_allow_html=True)
    
    target = st.selectbox("CEL PODRÓŻY / DESTYNACJA", sorted(TRANSIT_DATA.keys()))
    weight = st.number_input("WAGA ŁADUNKU NETTO (KG)", value=1000, step=100)
    
    st.markdown("---")
    d_m = st.date_input("DATA MONTAŻU / ROZŁADUNKU", datetime.now() + timedelta(days=7))
    d_d = st.date_input("DATA DEMONTAŻU / ZAŁADUNKU", d_m + timedelta(days=4))
    days_stay = max(0, (d_d - d_m).days)
    
    if st.button("🚪 WYLOGUJ", use_container_width=True):
        st.session_state.authenticated = False
        st.rerun()

# ==========================================
# 5. OBLICZENIA LOGISTYCZNE
# ==========================================
w_eff = weight * cfg.get('WAGA_BUFOR', 1.2)
caps = {"BUS": 1200, "SOLO": 5500, "FTL": 10500}
results = []

for v_t, cap in caps.items():
    res = df_baza[(df_baza['Miasto'] == target) & (df_baza['Typ_Pojazdu'] == v_t)]
    if not res.empty:
        r = res.mean(numeric_only=True)
        v_qty = math.ceil(w_eff / cap)
        tr_k = "BUS" if v_t == "BUS" else "FTL/SOLO"
        tr_d = TRANSIT_DATA.get(target, {}).get(tr_k, 2)
        
        c_exp = r['Eksport'] * v_qty
        c_imp = r['Import'] * v_qty
        c_ata = (cfg.get('ATA_CARNET', 166) if target in ["Londyn", "Genewa", "Liverpool", "Manchester"] else 0)
        c_ferry = (cfg.get('Ferry_UK', 450) if any(x in target for x in ["Londyn", "Liverpool", "Manchester"]) else 0)
        c_park = (days_stay * cfg.get('PARKING_DAY', 30) * v_qty)
        c_stay = r['Postoj'] * days_stay * v_qty
        
        results.append({
            "Pojazd": v_t, "Szt": v_qty, "Total": c_exp+c_imp+c_stay+c_park+c_ata+c_ferry, 
            "exp": c_exp, "imp": c_imp, "stay": c_stay, "other": c_ata+c_ferry+c_park, 
            "tr": tr_d, "load": min(100, (w_eff/(v_qty*cap))*100)
        })

# ==========================================
# 6. WIDOK GŁÓWNY (ANALIZA SQM)
# ==========================================
if results:
    best = min(results, key=lambda x: x['Total'])
    st.markdown(f'<div class="route-header">KOMORNIKI ➔ {target.upper()}</div>', unsafe_allow_html=True)
    
    L, R = st.columns([1.7, 1])
    
    with L:
        # HERO CARD
        st.markdown(f"""
            <div class="hero-card">
                <div style="color:#ed8936; font-weight:800; font-size:14px;">ESTYMACJA KOSZTÓW TRANSPORTU (NETTO)</div>
                <div class="main-price-value">€ {best['Total']:,.2f}</div>
                <div class="data-grid">
                    <div class="data-item"><div class="data-label">Tranzyt</div><div class="data-value">{best['tr']} DNI</div></div>
                    <div class="data-item"><div class="data-label">Postój</div><div class="data-value">{days_stay} DNI</div></div>
                    <div class="data-item"><div class="data-label">Konfiguracja</div><div class="data-value">{best['Szt']}x {best['Pojazd']}</div></div>
                    <div class="data-item"><div class="data-label">Zapełnienie</div><div class="data-value">{best['load']:.0f}%</div></div>
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        st.write("### 💰 ROZBICIE KOSZTÓW")
        s1, s2 = st.columns(2)
        with s1:
            st.markdown(f"<p style='color:#cbd5e0'>Eksport: <b>€ {best['exp']:,.2f}</b></p>", unsafe_allow_html=True)
            st.markdown(f"<p style='color:#cbd5e0'>Import: <b>€ {best['imp']:,.2f}</b></p>", unsafe_allow_html=True)
        with s2:
            st.markdown(f"<p style='color:#cbd5e0'>Postój: <b>€ {best['stay']:,.2f}</b></p>", unsafe_allow_html=True)
            st.markdown(f"<p style='color:#cbd5e0'>Dodatki: <b>€ {best['other']:,.2f}</b></p>", unsafe_allow_html=True)

        st.markdown("<br>### 📊 PORÓWNANIE FLOTY", unsafe_allow_html=True)
        for r in sorted(results, key=lambda x: x['Total']):
            is_b = "alt-best" if r['Pojazd'] == best['Pojazd'] else ""
            st.markdown(f"""
                <div class="alt-card {is_b}">
                    <div style="color:white; font-weight:800;">{r['Pojazd']} <span style="font-weight:400; font-size:12px; color:#94a3b8;">({r['Szt']} szt. | Ładunek {r['load']:.0f}%)</span></div>
                    <div style="color:#ed8936; font-size:22px; font-weight:950;">€ {r['Total']:,.2f}</div>
                </div>
            """, unsafe_allow_html=True)

    with R:
        st.write("### 📍 WIZUALIZACJA TRASY")
        b_p = CITY_COORDS["Komorniki (Baza)"]
        d_p = CITY_COORDS.get(target, [52, 13])
        path = pd.DataFrame({'lat': np.linspace(b_p[0], d_p[0], 20), 'lon': np.linspace(b_p[1], d_p[1], 20)})
        st.map(path, color='#ed8936', size=10)
        
        st.info(f"🚚 **Wyjazd z bazy:** {(d_m - timedelta(days=best['tr']+1)).strftime('%Y-%m-%d')}")
        st.success(f"📦 **Gotowość na rozładunek:** {d_m.strftime('%Y-%m-%d')}")
