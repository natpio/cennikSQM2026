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

# --- TWOJA TABELA CZASÓW TRANZYTU ---
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

st.set_page_config(page_title="SQM LOGISTICS v15.4", layout="wide")

# --- CUSTOM CSS ---
st.markdown("""
    <style>
    .stApp { background-color: #05070a !important; }
    .route-header { font-size: 36px !important; font-weight: 900; color: #ffffff; border-bottom: 4px solid #ed8936; margin-bottom: 25px; padding-bottom: 10px; }
    .hero-card { background: linear-gradient(145deg, #0f172a, #1a202c); border: 1px solid #2d3748; border-radius: 20px; padding: 35px; margin-bottom: 30px; }
    .main-price-label { color: #ed8936; font-size: 16px; font-weight: 800; text-transform: uppercase; letter-spacing: 1px; }
    .main-price-value { color: #ffffff; font-size: 95px; font-weight: 950; line-height: 0.85; margin: 20px 0; }
    .data-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin-top: 25px; }
    .data-item { background: rgba(255,255,255,0.06); padding: 20px; border-radius: 12px; border: 1px solid rgba(255,255,255,0.1); }
    .data-label { color: #94a3b8; font-size: 11px; font-weight: 700; text-transform: uppercase; }
    .data-value { color: #ffffff; font-size: 24px; font-weight: 900; }
    .cost-row { display: flex; justify-content: space-between; padding: 12px 0; border-bottom: 1px solid #1e293b; }
    .cost-n { color: #cbd5e0; font-size: 15px; }
    .cost-v { color: #ffffff; font-weight: 700; font-size: 17px; }
    .alt-card { background: #0f172a; border-left: 6px solid #4a5568; padding: 18px 25px; margin-bottom: 12px; border-radius: 10px; display: flex; justify-content: space-between; align-items: center; }
    .alt-best { border-left-color: #ed8936; background: rgba(237, 137, 54, 0.1); }
    </style>
""", unsafe_allow_html=True)

# --- SYSTEM LOGOWANIA ---
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
        return dict(zip(df['username'].astype(str), df['password'].astype(str)))
    except:
        return {"admin": "f3e99d9459eeb7ffc4cd407d890fbf1db011208fa12d8edc501a7ec26da106a3"}

user_db = load_users()

# Sprawdzenie ciasteczek
c_token = cookie_manager.get(cookie="sqm_session_v15")
if c_token in user_db:
    st.session_state.auth = True
    st.session_state.user = c_token

if not st.session_state.auth:
    _, col, _ = st.columns([1, 1.2, 1])
    with col:
        st.markdown("<h2 style='text-align:center; color:white; margin-top:50px;'>LOGOWANIE SQM</h2>", unsafe_allow_html=True)
        u_in = st.text_input("Użytkownik")
        p_in = st.text_input("Hasło", type="password")
        if st.button("ZALOGUJ", use_container_width=True):
            if u_in in user_db and user_db[u_in] == make_hash(p_in):
                st.session_state.auth = True
                st.session_state.user = u_in
                cookie_manager.set("sqm_session_v15", u_in, expires_at=datetime.now()+timedelta(days=7))
                st.rerun()
            else:
                st.error("Błędne dane logowania")
    st.stop()

# --- POBIERANIE DANYCH ---
@st.cache_data(ttl=60)
def fetch_logs():
    b = pd.read_csv(URL_BAZA)
    o = pd.read_csv(URL_OPLATY)
    b.columns = b.columns.str.strip()
    # Filtr dostawców własnych
    if 'Dostawca' in b.columns:
        b = b[~b['Dostawca'].str.contains('SQM|Własny|Wlasny', case=False, na=False)]
    def clean(v):
        s = re.sub(r'[^\d.]', '', str(v).replace(',', '.')); return float(s) if s else 0.0
    for c in ['Eksport', 'Import', 'Postoj']: 
        b[c] = b[c].apply(clean)
    o['Wartosc'] = o['Wartosc'].apply(clean)
    return b, o

df_baza, df_oplaty = fetch_logs()
cfg = dict(zip(df_oplaty['Parametr'], df_oplaty['Wartosc']))

# --- SIDEBAR (image_be078e.png) ---
with st.sidebar:
    st.image("https://www.sqm.pl/wp-content/themes/sqm/img/logo-sqm.png", width=150)
    st.write(f"Zalogowany: **{st.session_state.user}**")
    st.markdown("---")
    mode = st.radio("STRATEGIA", ["DEDYKOWANY", "DOŁADUNEK"])
    target = st.selectbox("MIASTO DOCELOWE", sorted(TRANSIT_DATA.keys()))
    weight = st.number_input("WAGA SPRZĘTU (kg)", value=1000, step=500)
    d_start = st.date_input("PIERWSZY DZIEŃ MONTAŻU", datetime.now() + timedelta(days=7))
    d_end = st.date_input("OSTATNI DZIEŃ MONTAŻU", datetime.now() + timedelta(days=10))
    days_stay = max(0, (d_end - d_start).days)
    
    if st.button("WYLOGUJ", use_container_width=True):
        cookie_manager.delete("sqm_session_v15")
        st.session_state.auth = False
        st.rerun()

# --- LOGIKA OBLICZEŃ ---
w_eff = weight * cfg.get('WAGA_BUFOR', 1.2)
caps = {"BUS": 1200, "SOLO": 5500, "FTL": 10500}
results = []

for v_type, cap in caps.items():
    res = df_baza[(df_baza['Miasto'] == target) & (df_baza['Typ_Pojazdu'] == v_type)]
    if not res.empty:
        r = res.mean(numeric_only=True)
        v_count = math.ceil(w_eff / cap)
        
        # Pobieranie czasu z Twojej tabeli
        t_key = "BUS" if v_type == "BUS" else "FTL/SOLO"
        transit_days = TRANSIT_DATA.get(target, {}).get(t_key, 2)
        
        # Stawki rynkowe
        exp = (r['Eksport'] * v_count if mode == "DEDYKOWANY" else r['Eksport'] * (w_eff/cap))
        imp = (r['Import'] * v_count if mode == "DEDYKOWANY" else r['Import'] * (w_eff/cap))
        
        # Opłaty stałe
        ata = (cfg.get('ATA_CARNET', 166) if target in ["Londyn", "Genewa", "Liverpool", "Manchester"] else 0)
        ferry = (cfg.get('Ferry_UK', 450) if any(x in target for x in ["Londyn", "Liverpool", "Manchester"]) else 0)
        parking = (days_stay * cfg.get('PARKING_DAY', 30) * v_count)
        stay_cost = r['Postoj'] * days_stay * v_count
        
        results.append({
            "Pojazd": v_type, "Szt": v_count, "Total": exp+imp+stay_cost+parking+ata+ferry, 
            "exp": exp, "imp": imp, "stay": stay_cost, "park": parking, "ata": ata, 
            "ferry": ferry, "transit": transit_days, "load": min(100, (w_eff/(v_count*cap))*100)
        })

# --- GŁÓWNY DASHBOARD ---
if results:
    best = min(results, key=lambda x: x['Total'])
    st.markdown(f'<div class="route-header">ANALIZA LOGISTYCZNA: KOMORNIKI ➔ {target.upper()}</div>', unsafe_allow_html=True)
    
    cl, cr = st.columns([1.8, 1])
    
    with cl:
        # KARTA KOSZTU GŁÓWNEGO
        st.markdown(f"""
            <div class="hero-card">
                <div class="main-price-label">Sugerowana Stawka Projektu (Netto)</div>
                <div class="main-price-value">€ {best['Total']:,.2f}</div>
                <div class="data-grid">
                    <div class="data-item"><div class="data-label">Tranzyt (Tabela)</div><div class="data-value">{best['transit']} dni</div></div>
                    <div class="data-item"><div class="data-label">Czas Montażu</div><div class="data-value">{days_stay} dni</div></div>
                    <div class="data-item"><div class="data-label">Rekomendacja</div><div class="data-value">{best['Pojazd']}</div></div>
                    <div class="data-item"><div class="data-label">Ładowne</div><div class="data-value">{best['load']:.0f}%</div></div>
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        # SKŁADOWE KOSZTÓW
        st.write("### 📊 SZCZEGÓŁOWE ZESTAWIENIE KOSZTÓW")
        s1, s2 = st.columns(2)
        with s1:
            st.markdown(f'<div class="cost-row"><span class="cost-n">Eksport (Średnia rynkowa):</span><span class="cost-v">€ {best["exp"]:,.2f}</span></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="cost-row"><span class="cost-n">Import (Średnia rynkowa):</span><span class="cost-v">€ {best["imp"]:,.2f}</span></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="cost-row"><span class="cost-n">Postój (Dni montażu):</span><span class="cost-v">€ {best["stay"]:,.2f}</span></div>', unsafe_allow_html=True)
        with s2:
            st.markdown(f'<div class="cost-row"><span class="cost-n">Parkingi i Diety:</span><span class="cost-v">€ {best["park"]:,.2f}</span></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="cost-row"><span class="cost-n">Odprawa ATA / Cło:</span><span class="cost-v">€ {best["ata"]:,.2f}</span></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="cost-row"><span class="cost-n">Promy / Eurotunel:</span><span class="cost-v">€ {best["ferry"]:,.2f}</span></div>', unsafe_allow_html=True)

        # PORÓWNANIE ALTERNATYW
        st.markdown("<br>### 🚛 DOSTĘPNE OPCJE TRANSPORTU", unsafe_allow_html=True)
        for r in sorted(results, key=lambda x: x['Total']):
            is_best = "alt-best" if r['Pojazd'] == best['Pojazd'] else ""
            st.markdown(f"""
                <div class="alt-card {is_best}">
                    <div style="font-weight: 800; font-size: 18px; color: white;">{r['Pojazd']} <span style="font-size: 12px; color: #94a3b8; font-weight: 400;">({r['Szt']} szt. | Wykorzystanie: {r['load']:.0f}%)</span></div>
                    <div style="font-size: 24px; font-weight: 950; color: #ed8936;">€ {r['Total']:,.2f}</div>
                </div>
            """, unsafe_allow_html=True)

    with cr:
        # MAPA
        b_pos = CITY_COORDS["Komorniki (Baza)"]
        d_pos = CITY_COORDS.get(target, [48.8, 2.3])
        path_df = pd.DataFrame({'lat': np.linspace(b_pos[0], d_pos[0], 25), 'lon': np.linspace(b_pos[1], d_pos[1], 25)})
        
        st.write("### 📍 TRASA PRZEJAZDU")
        st.map(path_df, color='#ed8936', size=15)
        
        st.warning(f"Zgodnie z Twoją tabelą, tranzyt dla tego miasta wynosi: **{best['transit']} dni**.")
        st.info(f"Sugerowana data wyjazdu z Komornik: **{(d_start - timedelta(days=best['transit'])).strftime('%Y-%m-%d')}**")
