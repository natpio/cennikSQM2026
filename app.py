import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import re
import hashlib
import math
import numpy as np
import pydeck as pdk

# --- 1. KONFIGURACJA ZASOBÓW (GOOGLE SHEETS) ---
SHEET_ID = "1sYlXP6WVzPE09qfmydQYQNsjiZcDgRSJGyWoXfjmkDY"
URL_BAZA = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=CENNIK_BAZA"
URL_OPLATY = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=OPLATY_STALE"
URL_USERS = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=USERS"

# Statyczna baza tranzytów dla logistyki SQM
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
st.set_page_config(page_title="SQM VENTAGE v5.2.2", layout="wide")

# --- 3. STYLE CSS ---
st.markdown("""
    <style>
    .stApp { background-color: #05070a !important; }
    [data-testid="stSidebar"] { background-color: #0f172a !important; border-right: 1px solid #1e293b; }
    div[data-baseweb="select"] > div, div[data-baseweb="input"] > div, 
    .stNumberInput div[data-baseweb="input"], .stDateInput div[data-baseweb="input"] {
        background-color: #1e293b !important; color: #ffffff !important; border: 1px solid #334155 !important;
    }
    input { color: #ffffff !important; -webkit-text-fill-color: #ffffff !important; }
    .brand-container { padding: 10px 0 20px 0; text-align: center; border-bottom: 1px solid #1e293b; margin-bottom: 20px; }
    .brand-logo { font-size: 22px; font-weight: 900; color: #ffffff; display: flex; align-items: center; justify-content: center; gap: 10px; }
    .brand-v { background: #ed8936; color: #000; padding: 2px 10px; border-radius: 4px; }
    .route-header { font-size: 32px !important; font-weight: 900; color: #ffffff; border-bottom: 4px solid #ed8936; margin-bottom: 30px; padding-bottom: 10px; }
    .hero-card { background: linear-gradient(145deg, #1e293b, #0f172a); border: 1px solid #334155; border-radius: 24px; padding: 35px; margin-bottom: 30px; }
    .main-price-value { color: #ffffff; font-size: 72px; font-weight: 950; margin: 10px 0; }
    .breakdown-container { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 20px; margin: 25px 0; padding: 25px 0; border-top: 1px solid rgba(255,255,255,0.1); border-bottom: 1px solid rgba(255,255,255,0.1); }
    .breakdown-item { font-size: 13px; color: #94a3b8; }
    .breakdown-item b { color: #ffffff; font-size: 17px; display: block; margin-top: 5px; }
    .alt-card { background: #0f172a; border-left: 5px solid #334155; padding: 20px 25px; margin-bottom: 15px; border-radius: 12px; display: flex; justify-content: space-between; align-items: center; }
    .alt-best { border-left-color: #ed8936; background: rgba(237, 137, 54, 0.05); }
    .price-tag { color: #ed8936; font-size: 22px; font-weight: 900; }
    </style>
""", unsafe_allow_html=True)

# --- 4. FUNKCJE POMOCNICZE ---
def make_hash(p): return hashlib.sha256(p.strip().encode()).hexdigest()

@st.cache_data(ttl=60)
def fetch_data():
    try:
        b = pd.read_csv(URL_BAZA); o = pd.read_csv(URL_OPLATY); b.columns = b.columns.str.strip()
        def clean(v): s = re.sub(r'[^\d.]', '', str(v).replace(',', '.')); return float(s) if s else 0.0
        for c in ['Eksport', 'Import', 'Postoj']: 
            if c in b.columns: b[c] = b[c].apply(clean)
        o['Wartosc'] = o['Wartosc'].apply(clean)
        return b, o
    except: return pd.DataFrame(), pd.DataFrame()

@st.cache_data(ttl=60)
def load_users():
    try:
        df = pd.read_csv(URL_USERS); df.columns = df.columns.str.strip()
        return dict(zip(df['username'].astype(str), df['password'].astype(str)))
    except: return {"admin": "f3e99d9459eeb7ffc4cd407d890fbf1db011208fa12d8edc501a7ec26da106a3"}

# --- 5. SYSTEM LOGOWANIA ---
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    _, col, _ = st.columns([1, 1.2, 1])
    with col:
        st.markdown("<div style='text-align:center; margin-top:100px;'><h1 style='color:white;'>SQM VENTAGE</h1></div>", unsafe_allow_html=True)
        u_in = st.text_input("Użytkownik", key="login_user")
        p_in = st.text_input("Hasło", type="password", key="login_pass")
        if st.button("ZALOGUJ DO SYSTEMU", use_container_width=True):
            users = load_users()
            if u_in in users and users[u_in] == make_hash(p_in):
                st.session_state.authenticated = True
                st.session_state.current_user = u_in
                st.rerun()
            else: st.error("Nieprawidłowe dane logowania.")
    st.stop()

# --- 6. PRZYGOTOWANIE DANYCH ---
df_baza, df_oplaty = fetch_data()
cfg = dict(zip(df_oplaty['Parametr'], df_oplaty['Wartosc'])) if not df_oplaty.empty else {}

# --- 7. PASEK BOCZNY (SIDEBAR) ---
with st.sidebar:
    st.markdown('<div class="brand-container"><div class="brand-logo"><span class="brand-v">V</span> SQM VENTAGE</div></div>', unsafe_allow_html=True)
    trip_type = st.radio("KIERUNEK", ["PEŁNA TRASA (EXP+IMP)", "TYLKO DOSTAWA (ONE-WAY)"])
    mode = st.radio("STRATEGIA", ["DEDYKOWANY", "DOŁADUNEK"])
    target = st.selectbox("CEL PODRÓŻY", sorted(TRANSIT_DATA.keys()))
    base_weight = st.number_input("WAGA NETTO (KG)", value=1000, step=100)
    real_weight = base_weight * 1.20 # Współczynnik opakowań/palet
    st.markdown(f'<div style="background:rgba(237,137,54,0.1); border:1px solid #ed8936; padding:12px; border-radius:8px; color:#ed8936; text-align:center; font-weight:bold;">BRUTTO: {real_weight:,.0f} KG</div>', unsafe_allow_html=True)
    d_start = st.date_input("DATA MONTAŻU", datetime.now() + timedelta(days=7))
    days_stay = 0
    if trip_type == "PEŁNA TRASA (EXP+IMP)":
        d_end = st.date_input("DATA DEMONTAŻU", d_start + timedelta(days=4))
        days_stay = max(0, (d_end - d_start).days)
    if st.button("🚪 WYLOGUJ", use_container_width=True):
        st.session_state.clear()
        st.rerun()

# --- 8. DYNAMICZNA STRUKTURA ZAKŁADEK (DLA ADMINA) ---
# Twarda blokada widoczności tabów dla osób postronnych
if st.session_state.current_user == "admin":
    tab_calc, tab_admin = st.tabs(["🚀 KALKULATOR", "⚙️ ADMIN TOOL"])
else:
    tab_calc = st.container()
    tab_admin = None

# --- TAB 1: KALKULATOR LOGISTYCZNY ---
with tab_calc:
    caps = {"BUS": 1200, "SOLO": 5500, "FTL": 10500}
    results = []
    if not df_baza.empty:
        for v_type, cap in caps.items():
            res = df_baza[(df_baza['Miasto'] == target) & (df_baza['Typ_Pojazdu'] == v_type)]
            if not res.empty:
                r = res.iloc[0]; v_count = math.ceil(real_weight / cap)
                transit = TRANSIT_DATA.get(target, {}).get("BUS" if v_type=="BUS" else "FTL/SOLO", 2)
                exp_v = (r['Eksport'] * v_count if mode == "DEDYKOWANY" else r['Eksport'] * (real_weight/cap))
                imp_v = (r['Import'] * v_count if mode == "DEDYKOWANY" else r['Import'] * (real_weight/cap)) if trip_type != "TYLKO DOSTAWA (ONE-WAY)" else 0
                stay_v = r['Postoj'] * days_stay * v_count
                park_v = (days_stay * cfg.get('PARKING_DAY', 30) * v_count)
                ata_v = (cfg.get('ATA_CARNET', 166) if target in ["Londyn", "Genewa", "Liverpool", "Manchester"] else 0)
                ferry_v = (cfg.get('Ferry_UK', 450) if any(x in target for x in ["Londyn", "Liverpool", "Manchester"]) else 0)
                results.append({
                    "Pojazd": v_type, "Szt": v_count, "Total": exp_v + imp_v + stay_v + park_v + ata_v + ferry_v,
                    "transit": transit, "load": min(100, (real_weight/(v_count*cap))*100),
                    "exp": exp_v, "imp": imp_v, "stay": stay_v, "park": park_v, "ata": ata_v, "ferry": ferry_v
                })
    
    if results:
        best = min(results, key=lambda x: x['Total'])
        dep_date = d_start - timedelta(days=best['transit'] + 1)
        st.markdown(f'<div class="route-header">KOMORNIKI ➔ {target.upper()}</div>', unsafe_allow_html=True)
        cl, cr = st.columns([1.8, 1])
        with cl:
            b_html = f"<div class='breakdown-item'>Eksport: <b>€ {best['exp']:,.0f}</b></div>"
            if trip_type != "TYLKO DOSTAWA (ONE-WAY)": b_html += f"<div class='breakdown-item'>Import: <b>€ {best['imp']:,.0f}</b></div>"
            b_html += f"<div class='breakdown-item'>Postój: <b>€ {best['stay']:,.0f}</b></div>"
            if best['park'] > 0: b_html += f"<div class='breakdown-item'>Parking/Diety: <b>€ {best['park']:,.0f}</b></div>"
            st.markdown(f'<div class="hero-card"><div style="color:#ed8936; font-size:14px; font-weight:800;">KOSZT SZACUNKOWY NETTO</div><div class="main-price-value">€ {best["Total"]:,.2f}</div><div class="breakdown-container">{b_html}</div></div>', unsafe_allow_html=True)
            for r in sorted(results, key=lambda x: x['Total']):
                is_best = "alt-best" if r['Pojazd'] == best['Pojazd'] else ""
                st.markdown(f'<div class="alt-card {is_best}"><div><b>{r["Pojazd"]}</b> ({r["Szt"]} szt.)</div><div class="price-tag">€ {r["Total"]:,.2f}</div></div>', unsafe_allow_html=True)
        with cr:
            s, e = CITY_COORDS["Komorniki (Baza)"], CITY_COORDS.get(target, [52.5, 13.4])
            st.pydeck_chart(pdk.Deck(map_provider="carto", map_style="light", initial_view_state=pdk.ViewState(latitude=(s[0]+e[0])/2, longitude=(s[1]+e[1])/2, zoom=4), layers=[pdk.Layer("ArcLayer", data=pd.DataFrame([{"s": [s[1], s[0]], "e": [e[1], e[0]]}]), get_source_position="s", get_target_position="e", get_source_color=[237, 137, 54], get_width=5)]))
            st.warning(f"🚚 **TERMIN WYJAZDU: {dep_date.strftime('%Y-%m-%d')}**")

# --- TAB 2: ADMIN TOOL (WIDOCZNY TYLKO DLA ADMINA) ---
if tab_admin is not None:
    with tab_admin:
        st.header("⚙️ Zarządzanie Systemem (Dostęp: ADMIN)")
        
        # Generator Kont - Narzędzie pomocnicze
        with st.expander("🔐 GENERATOR HASHY (DO ARKUSZA USERS)", expanded=True):
            st.markdown("Użyj tego formularza, aby stworzyć dane do wklejenia w Google Sheets.")
            col_u, col_p = st.columns(2)
            gen_u = col_u.text_input("Nazwa użytkownika", key="gen_u")
            gen_p = col_p.text_input("Hasło", type="password", key="gen_p")
            if gen_u and gen_p:
                h = make_hash(gen_p)
                st.info("Wklej to do kolumn 'username' i 'password' w arkuszu USERS:")
                st.code(f"User: {gen_u}\nHash: {h}")

        st.markdown("---")
        col_db1, col_db2 = st.columns(2)
        with col_db1:
            st.subheader("Cennik w Bazie")
            st.dataframe(df_baza, use_container_width=True)
        with col_db2:
            st.subheader("Parametry Stałe")
            st.dataframe(df_oplaty, use_container_width=True)
            
        st.link_button("👉 OTWÓRZ ARKUSZ GOOGLE", f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit")
        if st.button("🔄 ODSWIEŻ DANE (CLEAR CACHE)"):
            st.cache_data.clear()
            st.rerun()
