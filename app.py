import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import re
import hashlib
import extra_streamlit_components as stx
import math

# --- CONFIG ---
SHEET_ID = "1sYlXP6WVzPE09qfmydQYQNsjiZcDgRSJGyWoXfjmkDY"
URL_BAZA = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=CENNIK_BAZA"
URL_OPLATY = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=OPLATY_STALE"
URL_USERS = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=USERS"

CITY_COORDS = {
    "Komorniki (Baza)": [52.3358, 16.8122], "Amsterdam": [52.3702, 4.8952], 
    "Berlin": [52.5200, 13.4050], "Londyn": [51.5074, -0.1276],
    "Paryż": [48.8566, 2.3522], "Wiedeń": [48.2082, 16.3738], 
    "Praga": [50.0755, 14.4378], "Genewa": [46.2044, 6.1432], 
    "Zurych": [47.3769, 8.5417], "Barcelona": [41.3851, 2.1734],
    "Monachium": [48.1351, 11.5820], "Mediolan": [45.4642, 9.1900]
}

st.set_page_config(page_title="SQM LOGISTICS v14.6", layout="wide")

# --- CSS (Minimalistyczny dla stabilności) ---
st.markdown("""
    <style>
    .stApp { background: #0a0e14 !important; }
    [data-testid="stMetricValue"] { color: #ed8936 !important; font-size: 42px !important; font-weight: 800; }
    .main-price-box { background: rgba(237, 137, 54, 0.05); border: 1px solid #ed8936; border-radius: 10px; padding: 20px; margin-bottom: 20px; }
    .route-header { font-size: 26px; font-weight: 800; color: white; border-bottom: 2px solid #ed8936; padding-bottom: 5px; margin-bottom: 20px; }
    .cost-label { color: #94a3b8; font-size: 0.8rem; font-weight: bold; }
    .cost-val { color: white; font-size: 1.1rem; font-weight: 600; margin-bottom: 10px; }
    </style>
""", unsafe_allow_html=True)

# --- AUTH ---
def make_hash(p): return hashlib.sha256(p.strip().encode()).hexdigest()
cookie_manager = stx.CookieManager()
if "auth" not in st.session_state: st.session_state.auth = False

@st.cache_data(ttl=5)
def load_u():
    try:
        df = pd.read_csv(URL_USERS)
        df.columns = df.columns.str.strip()
        return dict(zip(df['username'].astype(str), df['password'].astype(str)))
    except: return {"admin": "f3e99d9459eeb7ffc4cd407d890fbf1db011208fa12d8edc501a7ec26da106a3"}

user_db = load_u()
c_token = cookie_manager.get(cookie="sqm_v14_session")
if c_token in user_db: st.session_state.auth, st.session_state.user = True, c_token

if not st.session_state.auth:
    _, col, _ = st.columns([1, 1.2, 1])
    with col:
        st.markdown("<h2 style='text-align:center; color:white;'>SQM VANTAGE</h2>", unsafe_allow_html=True)
        u_in = st.text_input("Użytkownik")
        p_in = st.text_input("Hasło", type="password")
        if st.button("ZALOGUJ", use_container_width=True):
            if u_in in user_db and user_db[u_in] == make_hash(p_in):
                st.session_state.auth, st.session_state.user = True, u_in
                cookie_manager.set("sqm_v14_session", u_in, expires_at=datetime.now()+timedelta(days=7))
                st.rerun()
    st.stop()

# --- DATA ---
@st.cache_data(ttl=60)
def fetch_logs():
    b = pd.read_csv(URL_BAZA); o = pd.read_csv(URL_OPLATY)
    b.columns = b.columns.str.strip()
    def clean(v):
        s = re.sub(r'[^\d.]', '', str(v).replace(',', '.'))
        return float(s) if s else 0.0
    for c in ['Eksport', 'Import', 'Postoj']: b[c] = b[c].apply(clean)
    o['Wartosc'] = o['Wartosc'].apply(clean)
    return b, o

df_baza, df_oplaty = fetch_logs()
cfg = dict(zip(df_oplaty['Parametr'], df_oplaty['Wartosc']))

# --- SIDEBAR ---
with st.sidebar:
    st.image("https://www.sqm.pl/wp-content/themes/sqm/img/logo-sqm.png", width=120)
    st.info(f"Logistyka: {st.session_state.user}")
    
    mode = st.radio("STRATEGIA", ["DEDYKOWANY", "DOŁADUNEK"])
    target = st.selectbox("MIProject_Target", sorted(df_baza['Miasto'].unique()))
    weight = st.number_input("WAGA SPRZĘTU (kg)", value=1000, step=500)
    
    d_start = st.date_input("PIERWSZY DZIEŃ MONTAŻU", datetime.now())
    d_end = st.date_input("OSTATNI DZIEŃ MONTAŻU", datetime.now() + timedelta(days=2))
    days = max(0, (d_end - d_start).days)
    
    if st.button("WYLOGUJ"):
        cookie_manager.delete("sqm_v14_session")
        st.session_state.auth = False
        st.rerun()

# --- LOGIKA ---
w_eff = weight * cfg.get('WAGA_BUFOR', 1.2)
caps = {"BUS": 1200, "SOLO": 5500, "FTL": 10500}
results = []

for v_type, cap in caps.items():
    res = df_baza[(df_baza['Miasto'] == target) & (df_baza['Typ_Pojazdu'] == v_type)]
    if not res.empty:
        r = res.iloc[0]
        v_count = math.ceil(w_eff / cap)
        load_pc = min(100, (w_eff / (v_count * cap)) * 100)
        
        if mode == "DEDYKOWANY":
            exp, imp = r['Eksport'] * v_count, r['Import'] * v_count
        else:
            ratio = min(1.0, w_eff / cap)
            exp, imp = r['Eksport'] * ratio, r['Import'] * ratio

        ata = (cfg.get('ATA_CARNET', 166) if target in ["Londyn", "Genewa", "Zurych"] else 0)
        ferry = (cfg.get('Ferry_UK', 450) if target == "Londyn" else 0)
        parking = (days * cfg.get('PARKING_DAY', 30) * v_count)
        stay_cost = r['Postoj'] * days * v_count
        
        total = exp + imp + stay_cost + parking + ata + ferry
        results.append({
            "Pojazd": v_type, "Szt.": v_count, "Ładunek": f"{load_pc:.0f}%", 
            "Suma": total, "exp": exp, "imp": imp, "stay": stay_cost, 
            "park": parking, "ata": ata, "ferry": ferry
        })

if results:
    best = min(results, key=lambda x: x['Suma'])
    
    st.markdown(f'<div class="route-header">LOGISTYKA: KOMORNIKI ➔ {target.upper()}</div>', unsafe_allow_html=True)
    
    col_main, col_map = st.columns([1.6, 1])
    
    with col_main:
        with st.container():
            st.markdown('<div class="main-price-box">', unsafe_allow_html=True)
            st.metric("REKOMENDOWANA STAWKA (NETTO)", f"€ {best['Suma']:,.2f}")
            
            c1, c2, c3 = st.columns(3)
            c1.markdown(f'<div class="cost-label">POJAZD</div><div class="cost-val">{best["Pojazd"]} ({best["Szt."]} szt.)</div>', unsafe_allow_html=True)
            c2.markdown(f'<div class="cost-label">WAGA (+20%)</div><div class="cost-val">{w_eff:,.0f} kg</div>', unsafe_allow_html=True)
            c3.markdown(f'<div class="cost-label">ZAŁADOWANIE</div><div class="cost-val">{best["Ładunek"]}</div>', unsafe_allow_html=True)
            
            st.markdown('<div style="margin-top:20px; border-top:1px solid rgba(255,255,255,0.1); padding-top:10px;"></div>', unsafe_allow_html=True)
            st.write("**SZCZEGÓŁOWE SKŁADOWE KOSZTÓW:**")
            
            sc1, sc2, sc3 = st.columns(3)
            sc1.markdown(f"**Eksport:** € {best['exp']:,.2f}")
            sc1.markdown(f"**Import:** € {best['imp']:,.2f}")
            sc2.markdown(f"**Postój:** € {best['stay']:,.2f}")
            sc2.markdown(f"**Parkingi:** € {best['park']:,.2f}")
            sc3.markdown(f"**ATA/Cło:** € {best['ata']:,.2f}")
            sc3.markdown(f"**Promy/Mosty:** € {best['ferry']:,.2f}")
            st.markdown('</div>', unsafe_allow_html=True)

        st.write("### PORÓWNANIE ROZWIĄZAŃ")
        df_res = pd.DataFrame(results)[["Pojazd", "Szt.", "Ładunek", "Suma"]]
        df_res["Suma"] = df_res["Suma"].map("€ {:,.2f}".format)
        st.table(df_res)

    with col_map:
        base, dest = CITY_COORDS["Komorniki (Baza)"], CITY_COORDS.get(target, [52.5, 13.4])
        st.map(pd.DataFrame({'lat': [base[0], dest[0]], 'lon': [base[1], dest[1]]}), color='#ed8936')
        st.info(f"Czas trwania montażu/postoju: {days} dni.")
