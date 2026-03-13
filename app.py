import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import re
import hashlib
import extra_streamlit_components as stx
import math
import numpy as np

# --- 1. KONFIGURACJA ZASOBÓW ---
SHEET_ID = "1sYlXP6WVzPE09qfmydQYQNsjiZcDgRSJGyWoXfjmkDY"
URL_BAZA = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=CENNIK_BAZA"
URL_OPLATY = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=OPLATY_STALE"
URL_USERS = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=USERS"

# --- 2. PEŁNA TABELA TRANZYTU ---
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

st.set_page_config(page_title="SQM LOGISTICS v17.0", layout="wide")

# --- 3. AGRESYWNY CSS DLA INTERFEJSU SQM ---
st.markdown("""
    <style>
    .stApp { background-color: #05070a !important; }
    
    /* SIDEBAR - Kontrast i widoczność */
    [data-testid="stSidebar"] {
        background-color: #0f172a !important;
        border-right: 2px solid #ed8936;
    }
    [data-testid="stSidebarNav"], header { display: none !important; }

    /* FIX DLA WIDOCZNOŚCI WPISYWANEGO TEKSTU */
    /* Wymuszamy czarne tło i jaskrawą czcionkę dla pól tekstowych */
    [data-testid="stSidebar"] input, 
    [data-testid="stSidebar"] select,
    [data-testid="stSidebar"] div[data-baseweb="input"],
    [data-testid="stSidebar"] div[data-baseweb="select"] {
        background-color: #1e293b !important;
        color: #ffffff !important;
        border: 1px solid #ed8936 !important;
        -webkit-text-fill-color: #ffffff !important;
    }
    [data-testid="stSidebar"] label, [data-testid="stSidebar"] p {
        color: #ffffff !important;
        font-weight: 800 !important;
        text-transform: uppercase;
        font-size: 12px;
    }

    /* GŁÓWNY PANEL */
    .hero-card {
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        border-radius: 20px;
        padding: 40px;
        border: 1px solid #334155;
        box-shadow: 0 20px 50px rgba(0,0,0,0.5);
        margin-bottom: 30px;
    }
    .main-price { color: #ffffff; font-size: 90px; font-weight: 950; letter-spacing: -3px; line-height: 1; }
    .price-label { color: #ed8936; font-size: 14px; font-weight: 800; text-transform: uppercase; margin-bottom: 10px; }
    
    /* ANALIZA KOSZTÓW */
    .cost-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; }
    .cost-box { background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.1); padding: 20px; border-radius: 12px; }
    .cost-title { color: #94a3b8; font-size: 10px; font-weight: 700; text-transform: uppercase; margin-bottom: 8px; }
    .cost-value { color: #ffffff; font-size: 24px; font-weight: 900; }
    </style>
""", unsafe_allow_html=True)

# --- 4. SYSTEM LOGOWANIA ---
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
c_token = cookie_manager.get(cookie="sqm_session_v17")
if c_token in user_db:
    st.session_state.auth, st.session_state.user = True, c_token

if not st.session_state.auth:
    _, col, _ = st.columns([1, 1.3, 1])
    with col:
        st.markdown("<h1 style='text-align:center; color:white; margin-top:100px;'>SQM LOGISTICS</h1>", unsafe_allow_html=True)
        u = st.text_input("Użytkownik", key="u_login")
        p = st.text_input("Hasło", type="password", key="p_login")
        if st.button("ZALOGUJ DO SYSTEMU", use_container_width=True):
            if u in user_db and user_db[u] == make_hash(p):
                st.session_state.auth, st.session_state.user = True, u
                cookie_manager.set("sqm_session_v17", u, expires_at=datetime.now()+timedelta(days=7))
                st.rerun()
    st.stop()

# --- 5. POBIERANIE DANYCH ---
@st.cache_data(ttl=60)
def fetch_data():
    b = pd.read_csv(URL_BAZA); o = pd.read_csv(URL_OPLATY); b.columns = b.columns.str.strip()
    if 'Dostawca' in b.columns:
        b = b[~b['Dostawca'].str.contains('SQM|Własny|Wlasny', case=False, na=False)]
    def clean(v):
        s = re.sub(r'[^\d.]', '', str(v).replace(',', '.')); return float(s) if s else 0.0
    for c in ['Eksport', 'Import', 'Postoj']: b[c] = b[c].apply(clean)
    o['Wartosc'] = o['Wartosc'].apply(clean)
    return b, o

df_baza, df_oplaty = fetch_data()
cfg = dict(zip(df_oplaty['Parametr'], df_oplaty['Wartosc']))

# --- 6. SIDEBAR (NAPRAWIONA WIDOCZNOŚĆ) ---
with st.sidebar:
    st.markdown("<br>", unsafe_allow_html=True)
    st.image("https://www.sqm.pl/wp-content/themes/sqm/img/logo-sqm.png", width=200)
    st.markdown(f"<p style='color:#ed8936; text-align:center;'>OPERATOR: {st.session_state.user.upper()}</p>", unsafe_allow_html=True)
    
    st.markdown("### KONFIGURACJA TRASY")
    target = st.selectbox("CEL PODRÓŻY", sorted(TRANSIT_DATA.keys()))
    mode = st.radio("STRATEGIA", ["DEDYKOWANY", "DOŁADUNEK"])
    
    st.markdown("---")
    st.markdown("### PARAMETRY ŁADUNKU")
    weight = st.number_input("WAGA (KG)", value=1500, step=500)
    ldm = st.number_input("METRY BIEŻĄCE (LDM)", value=2.4, step=0.4)
    vol = st.number_input("OBJĘTOŚĆ (M3)", value=10.0, step=1.0)
    
    st.markdown("---")
    st.markdown("### TERMINY TARGOWE")
    d_start = st.date_input("ZAŁADUNEK", datetime.now() + timedelta(days=7))
    d_end = st.date_input("POWRÓT", d_start + timedelta(days=5))
    days_stay = max(0, (d_end - d_start).days)
    
    if st.button("WYLOGUJ"):
        cookie_manager.delete("sqm_session_v17")
        st.session_state.auth = False
        st.rerun()

# --- 7. LOGIKA OBLICZENIOWA (LDM / WAGA / VOL) ---
# Pojemności pojazdów
v_caps = {
    "BUS": {"kg": 1200, "ldm": 4.2, "m3": 15},
    "SOLO": {"kg": 5500, "ldm": 7.2, "m3": 40},
    "FTL": {"kg": 24000, "ldm": 13.6, "m3": 90}
}

results = []
w_eff = weight * cfg.get('WAGA_BUFOR', 1.2)

for v_type, cap in v_caps.items():
    # Ile aut potrzeba na podstawie 3 parametrów?
    needed_by_kg = math.ceil(w_eff / cap['kg'])
    needed_by_ldm = math.ceil(ldm / cap['ldm'])
    needed_by_vol = math.ceil(vol / cap['m3'])
    v_count = max(needed_by_kg, needed_by_ldm, needed_by_vol)
    
    # Dane z bazy
    db_res = df_baza[(df_baza['Miasto'] == target) & (df_baza['Typ_Pojazdu'] == v_type)]
    if not db_res.empty:
        rates = db_res.mean(numeric_only=True)
        t_key = "BUS" if v_type == "BUS" else "FTL/SOLO"
        t_days = TRANSIT_DATA.get(target, {}).get(t_key, 2)
        
        # Koszty podstawowe
        if mode == "DEDYKOWANY":
            c_exp, c_imp = rates['Eksport'] * v_count, rates['Import'] * v_count
        else:
            ratio = max(w_eff/cap['kg'], ldm/cap['ldm'], vol/cap['m3'])
            c_exp, c_imp = rates['Eksport'] * ratio, rates['Import'] * ratio
            
        # Koszty dodatkowe
        c_stay = rates['Postoj'] * days_stay * v_count
        c_park = days_stay * cfg.get('PARKING_DAY', 30) * v_count
        c_ata = cfg.get('ATA_CARNET', 166) if target in ["Londyn", "Genewa", "Liverpool", "Manchester"] else 0
        c_ferry = cfg.get('Ferry_UK', 450) if any(x in target for x in ["Londyn", "Liverpool", "Manchester"]) else 0
        
        total = c_exp + c_imp + c_stay + c_park + c_ata + c_ferry
        
        results.append({
            "Pojazd": v_type, "Szt": v_count, "Total": total, "Transit": t_days,
            "Exp": c_exp, "Imp": c_imp, "Stay": c_stay, "Extra": c_park + c_ata + c_ferry,
            "Load": min(100, (max(w_eff/cap['kg'], ldm/cap['ldm'], vol/cap['m3']) / v_count) * 100)
        })

# --- 8. WIDOK GŁÓWNY ---
if results:
    best = min(results, key=lambda x: x['Total'])
    st.markdown(f'<div style="font-size:35px; font-weight:900; color:white; border-left:8px solid #ed8936; padding-left:20px; margin-bottom:30px;">{target.upper()} | {mode}</div>', unsafe_allow_html=True)
    
    col_l, col_r = st.columns([1.8, 1])
    
    with col_l:
        st.markdown(f"""
            <div class="hero-card">
                <div class="price-label">Sugerowana Kwota Netto Za Projekt</div>
                <div class="main-price">€ {best['Total']:,.2f}</div>
                <div style="display:grid; grid-template-columns: repeat(4, 1fr); gap:15px; margin-top:30px;">
                    <div class="cost-box"><div class="cost-title">Tranzyt</div><div class="cost-value">{best['Transit']} dni</div></div>
                    <div class="cost-box"><div class="cost-title">Pojazd</div><div class="cost-value">{best['Pojazd']}</div></div>
                    <div class="cost-box"><div class="cost-title">Liczba aut</div><div class="cost-value">{best['Szt']} szt.</div></div>
                    <div class="cost-box"><div class="cost-title">Zapełnienie</div><div class="cost-value">{best['Load']:.1f}%</div></div>
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        st.write("### 📊 ZESTAWIENIE SZCZEGÓŁOWE")
        st.markdown(f"""
            <div class="cost-grid">
                <div class="cost-box"><div class="cost-title">Transport (Exp/Imp)</div><div class="cost-value">€ {best['Exp']+best['Imp']:,.2f}</div></div>
                <div class="cost-box"><div class="cost-title">Postój na miejscu</div><div class="cost-value">€ {best['Stay']:,.2f}</div></div>
                <div class="cost-box"><div class="cost-title">Dodatki (ATA/UK/Park)</div><div class="cost-value">€ {best['Extra']:,.2f}</div></div>
            </div>
        """, unsafe_allow_html=True)

    with col_r:
        st.write("### 📍 LOGISTYKA TRASY")
        st.map(pd.DataFrame({'lat': [52.33, 48.85], 'lon': [16.81, 2.35]}), color='#ed8936', zoom=4)
        st.success(f"**Wyjazd z bazy:** {(d_start - timedelta(days=best['Transit'])).strftime('%Y-%m-%d')}")
        st.info(f"**Planowana waga z buforem:** {w_eff:,.0f} kg")

    st.write("### 🚛 DOSTĘPNE KONFIGURACJE")
    st.table(pd.DataFrame(results)[['Pojazd', 'Szt', 'Total', 'Transit', 'Load']])
