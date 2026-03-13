import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import re
import hashlib
import extra_streamlit_components as stx
import math

# --- 1. KONFIGURACJA I ADRESY ---
SHEET_ID = "1sYlXP6WVzPE09qfmydQYQNsjiZcDgRSJGyWoXfjmkDY"
URL_BAZA = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=CENNIK_BAZA"
URL_OPLATY = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=OPLATY_STALE"
URL_USERS = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=USERS"

# --- 2. TABELA TRANZYTU (Zgodna z dokumentacją) ---
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

st.set_page_config(page_title="SQM LOGISTICS v17.1", layout="wide")

# --- 3. RADYKALNY CSS (Fix białych pól w sidebarze) ---
st.markdown("""
    <style>
    /* Globalne tło */
    .stApp { background-color: #05070a !important; }
    
    /* Ukrycie paska systemowego na górze */
    header, [data-testid="stHeader"] { display: none !important; }

    /* SIDEBAR - TŁO I KONTRAST */
    [data-testid="stSidebar"] {
        background-color: #0f172a !important;
        border-right: 1px solid #334155;
    }
    
    /* FIX DLA PÓL WEJŚCIOWYCH - Wymuszenie widoczności czcionki */
    /* Robimy tło pól bardzo ciemne, a czcionkę białą - to jedyny sposób na błąd ze screena */
    [data-testid="stSidebar"] div[data-baseweb="input"],
    [data-testid="stSidebar"] div[data-baseweb="select"],
    [data-testid="stSidebar"] input,
    [data-testid="stSidebar"] .stSelectbox div {
        background-color: #1e293b !important;
        color: #ffffff !important;
        border: 1px solid #ed8936 !important;
        border-radius: 4px !important;
        -webkit-text-fill-color: #ffffff !important;
    }

    /* Wymuszenie koloru etykiet */
    [data-testid="stSidebar"] label, [data-testid="stSidebar"] p {
        color: #ffffff !important;
        font-weight: 700 !important;
        text-transform: uppercase;
        font-size: 11px;
    }

    /* GŁÓWNY WIDOK - KARTA CENOWA */
    .hero-card {
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        border: 1px solid #334155;
        border-radius: 20px;
        padding: 40px;
        margin-bottom: 30px;
    }
    .main-price { color: #ffffff; font-size: 85px; font-weight: 950; letter-spacing: -3px; line-height: 1; }
    .price-label { color: #ed8936; font-size: 14px; font-weight: 800; text-transform: uppercase; }
    
    .data-item { background: rgba(255,255,255,0.04); padding: 15px; border-radius: 12px; border: 1px solid rgba(255,255,255,0.1); }
    .data-label { color: #94a3b8; font-size: 10px; font-weight: 700; text-transform: uppercase; }
    .data-value { color: #ffffff; font-size: 20px; font-weight: 900; }
    </style>
""", unsafe_allow_html=True)

# --- 4. LOGOWANIE ---
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
    _, col, _ = st.columns([1, 1.2, 1])
    with col:
        st.markdown("<h2 style='text-align:center; color:white; margin-top:80px;'>SQM LOGISTICS</h2>", unsafe_allow_html=True)
        u = st.text_input("Użytkownik", key="u_log")
        p = st.text_input("Hasło", type="password", key="p_log")
        if st.button("ZALOGUJ", use_container_width=True):
            if u in user_db and user_db[u] == make_hash(p):
                st.session_state.auth, st.session_state.user = True, u
                cookie_manager.set("sqm_session_v17", u, expires_at=datetime.now()+timedelta(days=7))
                st.rerun()
    st.stop()

# --- 5. DANE ---
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

# --- 6. SIDEBAR (Pasek boczny - FIX) ---
with st.sidebar:
    st.markdown("<br>", unsafe_allow_html=True)
    st.image("https://www.sqm.pl/wp-content/themes/sqm/img/logo-sqm.png", width=180)
    st.markdown(f"<p style='color:#ed8936; font-weight:800;'>UŻYTKOWNIK: {st.session_state.user.upper()}</p>", unsafe_allow_html=True)
    
    st.markdown("### KONFIGURACJA CENNIKA")
    target = st.selectbox("CEL PODRÓŻY", sorted(TRANSIT_DATA.keys()))
    mode = st.radio("STRATEGIA", ["DEDYKOWANY", "DOŁADUNEK"])
    
    st.markdown("---")
    weight = st.number_input("WAGA ŁADUNKU (KG)", value=1000, step=500)
    
    st.markdown("---")
    d_start = st.date_input("ZAŁADUNEK", datetime.now() + timedelta(days=5))
    d_end = st.date_input("POWRÓT", d_start + timedelta(days=7))
    days_stay = max(0, (d_end - d_start).days)
    
    if st.button("WYLOGUJ"):
        cookie_manager.delete("sqm_session_v17")
        st.session_state.auth = False
        st.rerun()

# --- 7. OBLICZENIA ---
w_eff = weight * cfg.get('WAGA_BUFOR', 1.2)
v_caps = {"BUS": 1200, "SOLO": 5500, "FTL": 24000}
results = []

for v_type, cap in v_caps.items():
    db_res = df_baza[(df_baza['Miasto'] == target) & (df_baza['Typ_Pojazdu'] == v_type)]
    if not db_res.empty:
        rates = db_res.mean(numeric_only=True)
        v_count = math.ceil(w_eff / cap)
        
        t_key = "BUS" if v_type == "BUS" else "FTL/SOLO"
        t_days = TRANSIT_DATA.get(target, {}).get(t_key, 2)
        
        if mode == "DEDYKOWANY":
            c_exp, c_imp = rates['Eksport'] * v_count, rates['Import'] * v_count
        else:
            ratio = w_eff / cap
            c_exp, c_imp = rates['Eksport'] * ratio, rates['Import'] * ratio
            
        c_stay = rates['Postoj'] * days_stay * v_count
        c_park = days_stay * cfg.get('PARKING_DAY', 30) * v_count
        c_ata = cfg.get('ATA_CARNET', 166) if target in ["Londyn", "Genewa", "Liverpool", "Manchester"] else 0
        c_ferry = cfg.get('Ferry_UK', 450) if any(x in target for x in ["Londyn", "Liverpool", "Manchester"]) else 0
        
        total = c_exp + c_imp + c_stay + c_park + c_ata + c_ferry
        
        results.append({
            "Pojazd": v_type, "Szt": v_count, "Total": total, "Transit": t_days,
            "Exp": c_exp, "Imp": c_imp, "Stay": c_stay, "Extra": c_park + c_ata + c_ferry,
            "Util": min(100, (w_eff / (v_count * cap)) * 100)
        })

# --- 8. WIDOK ---
if results:
    best = min(results, key=lambda x: x['Total'])
    st.markdown(f'<h1 style="color:white; margin-bottom:20px;">{target.upper()} | {mode}</h1>', unsafe_allow_html=True)
    
    col1, col2 = st.columns([1.8, 1])
    with col1:
        st.markdown(f"""
            <div class="hero-card">
                <div class="price-label">Sugerowana Kwota Netto</div>
                <div class="main-price">€ {best['Total']:,.2f}</div>
                <div style="display:grid; grid-template-columns: repeat(4, 1fr); gap:15px; margin-top:30px;">
                    <div class="data-item"><div class="data-label">Tranzyt</div><div class="data-value">{best['Transit']} dni</div></div>
                    <div class="data-item"><div class="data-label">Pojazd</div><div class="data-value">{best['Pojazd']}</div></div>
                    <div class="data-item"><div class="data-label">Liczba aut</div><div class="data-value">{best['Szt']} szt.</div></div>
                    <div class="data-item"><div class="data-label">Zapełnienie</div><div class="data-value">{best['Util']:.0f}%</div></div>
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        st.write("### 🔍 ROZBICIE KOSZTÓW")
        st.json({
            "Transport (Średnia Exp/Imp)": f"€ {best['Exp']+best['Imp']:,.2f}",
            "Koszty Postoju (SQM+Przewoźnik)": f"€ {best['Stay']+best['Extra']:,.2f}"
        })

    with col2:
        st.write("### 📍 LOGISTYKA")
        st.map(pd.DataFrame({'lat': [52.33, 48.85], 'lon': [16.81, 2.35]}), color='#ed8936')
        st.success(f"Sugerowany wyjazd z bazy: {(d_start - timedelta(days=best['Transit'])).strftime('%Y-%m-%d')}")
