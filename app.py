import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import re
import hashlib
import extra_streamlit_components as stx
import math
import numpy as np

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
    "Monachium": [48.1351, 11.5820], "Mediolan": [45.4642, 9.1900],
    "Madryt": [40.4168, -3.7038], "Lizbona": [38.7223, -9.1393]
}

st.set_page_config(page_title="SQM LOGISTICS v15.0", layout="wide")

# --- CSS (Maksymalna Czytelność i Kontrast) ---
st.markdown("""
    <style>
    .stApp { background-color: #05070a !important; }
    
    .route-header { 
        font-size: 40px !important; font-weight: 900; color: #ffffff; 
        padding: 5px 0; border-bottom: 5px solid #ed8936; margin-bottom: 30px;
    }
    
    /* GŁÓWNA SEKCJA CENOWA */
    .hero-card {
        background: linear-gradient(145deg, #0f172a, #1e293b);
        border: 2px solid #334155; border-radius: 24px;
        padding: 40px; margin-bottom: 30px; box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.9);
    }
    .main-price-label { color: #ed8936; font-size: 22px; font-weight: 800; text-transform: uppercase; letter-spacing: 2px; }
    .main-price-value { color: #ffffff; font-size: 110px; font-weight: 950; line-height: 0.85; margin: 25px 0; }
    
    /* SIATKA DANYCH */
    .data-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; margin-top: 30px; }
    .data-item { background: rgba(255,255,255,0.07); padding: 25px; border-radius: 15px; border: 1px solid rgba(255,255,255,0.15); }
    .data-label { color: #94a3b8; font-size: 13px; font-weight: 700; text-transform: uppercase; margin-bottom: 8px; }
    .data-value { color: #ffffff; font-size: 28px; font-weight: 900; }
    
    /* KARTY ALTERNATYW */
    .alt-card { 
        background: #0f172a; border: 1px solid #1e293b; border-left: 8px solid #475569;
        padding: 22px; margin-bottom: 15px; border-radius: 15px;
        display: flex; justify-content: space-between; align-items: center;
    }
    .alt-best { border-left-color: #ed8936; background: rgba(237, 137, 54, 0.12); border-color: #ed8936; }
    
    .cost-row { display: flex; justify-content: space-between; padding: 14px 0; border-bottom: 1px solid #1e293b; }
    .cost-n { color: #cbd5e0; font-size: 17px; }
    .cost-v { color: #ffffff; font-weight: 800; font-size: 19px; }
    </style>
""", unsafe_allow_html=True)

# --- AUTH ---
def make_hash(p): return hashlib.sha256(p.strip().encode()).hexdigest()
cookie_manager = stx.CookieManager()
if "auth" not in st.session_state: st.session_state.auth = False

@st.cache_data(ttl=5)
def load_u():
    try:
        df = pd.read_csv(URL_USERS); df.columns = df.columns.str.strip()
        return dict(zip(df['username'].astype(str), df['password'].astype(str)))
    except: return {"admin": "f3e99d9459eeb7ffc4cd407d890fbf1db011208fa12d8edc501a7ec26da106a3"}

user_db = load_u()
c_token = cookie_manager.get(cookie="sqm_v14_session")
if c_token in user_db: st.session_state.auth, st.session_state.user = True, c_token

if not st.session_state.auth:
    _, col, _ = st.columns([1, 1.2, 1])
    with col:
        st.markdown("<h2 style='text-align:center; color:white;'>SQM VANTAGE</h2>", unsafe_allow_html=True)
        u_in = st.text_input("Użytkownik"); p_in = st.text_input("Hasło", type="password")
        if st.button("ZALOGUJ", use_container_width=True):
            if u_in in user_db and user_db[u_in] == make_hash(p_in):
                st.session_state.auth, st.session_state.user = True, u_in
                cookie_manager.set("sqm_v14_session", u_in, expires_at=datetime.now()+timedelta(days=7))
                st.rerun()
    st.stop()

# --- DATA ---
@st.cache_data(ttl=60)
def fetch_logs():
    b = pd.read_csv(URL_BAZA); o = pd.read_csv(URL_OPLATY); b.columns = b.columns.str.strip()
    # Filtr transportu własnego
    if 'Dostawca' in b.columns:
        b = b[~b['Dostawca'].str.contains('SQM|Własny|Wlasny', case=False, na=False)]
    def clean(v):
        s = re.sub(r'[^\d.]', '', str(v).replace(',', '.')); return float(s) if s else 0.0
    for c in ['Eksport', 'Import', 'Postoj']: b[c] = b[c].apply(clean)
    o['Wartosc'] = o['Wartosc'].apply(clean)
    return b, o

df_baza, df_oplaty = fetch_logs()
cfg = dict(zip(df_oplaty['Parametr'], df_oplaty['Wartosc']))

# --- SIDEBAR ---
with st.sidebar:
    st.image("https://www.sqm.pl/wp-content/themes/sqm/img/logo-sqm.png", width=120)
    st.write(f"Zalogowany: **{st.session_state.user}**")
    mode = st.radio("STRATEGIA", ["DEDYKOWANY", "DOŁADUNEK"])
    target = st.selectbox("MIASTO DOCELOWE", sorted(df_baza['Miasto'].unique()))
    weight = st.number_input("WAGA SPRZĘTU (kg)", value=1500, step=500)
    d_start = st.date_input("ZAŁADUNEK", datetime.now())
    d_end = st.date_input("POWRÓT", datetime.now() + timedelta(days=3))
    days = max(0, (d_end - d_start).days)
    if st.button("WYLOGUJ"):
        cookie_manager.delete("sqm_v14_session"); st.session_state.auth = False; st.rerun()

# --- LOGIKA ---
w_eff = weight * cfg.get('WAGA_BUFOR', 1.2)
caps = {"BUS": 1200, "SOLO": 5500, "FTL": 10500}
results = []

for v_type, cap in caps.items():
    res = df_baza[(df_baza['Miasto'] == target) & (df_baza['Typ_Pojazdu'] == v_type)]
    if not res.empty:
        r = res.mean(numeric_only=True)
        v_count = math.ceil(w_eff / cap)
        load_pc = min(100, (w_eff / (v_count * cap)) * 100)
        exp = (r['Eksport'] * v_count if mode == "DEDYKOWANY" else r['Eksport'] * (w_eff/cap))
        imp = (r['Import'] * v_count if mode == "DEDYKOWANY" else r['Import'] * (w_eff/cap))
        ata = (cfg.get('ATA_CARNET', 166) if target in ["Londyn", "Genewa", "Zurych"] else 0)
        ferry = (cfg.get('Ferry_UK', 450) if target == "Londyn" else 0)
        parking = (days * cfg.get('PARKING_DAY', 30) * v_count)
        stay_cost = r['Postoj'] * days * v_count
        transit = (2 if target in ["Barcelona", "Londyn", "Madryt", "Lisbona"] else 1)
        
        total = exp + imp + stay_cost + parking + ata + ferry
        results.append({"Pojazd": v_type, "Szt": v_count, "Load": f"{load_pc:.0f}%", "Total": total, "exp": exp, "imp": imp, "stay": stay_cost, "park": parking, "ata": ata, "ferry": ferry, "transit": transit})

if results:
    best = min(results, key=lambda x: x['Total'])
    st.markdown(f'<div class="route-header">LOGISTYKA: KOMORNIKI ➔ {target.upper()}</div>', unsafe_allow_html=True)
    
    cl, cr = st.columns([1.8, 1])
    
    with cl:
        # GIGANTYCZNA CENA
        st.markdown(f"""
            <div class="hero-card">
                <div class="main-price-label">Rekomendowana Stawka Projektu (Netto)</div>
                <div class="main-price-value">€ {best['Total']:,.2f}</div>
                <div class="data-grid">
                    <div class="data-item"><div class="data-label">Dni Tranzytu</div><div class="data-value">{best['transit']}</div></div>
                    <div class="data-item"><div class="data-label">Dni Postoju</div><div class="data-value">{days}</div></div>
                    <div class="data-item"><div class="data-label">Typ Pojazdu</div><div class="data-value">{best['Pojazd']}</div></div>
                    <div class="data-item"><div class="data-label">Liczba Aut</div><div class="data-value">{best['Szt']}</div></div>
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        # SKŁADOWE
        st.write("### 📊 SZCZEGÓŁY KOSZTÓW (STAWEK RYNKOWYCH):")
        s1, s2 = st.columns(2)
        with s1:
            st.markdown(f'<div class="cost-row"><span class="cost-n">Eksport:</span><span class="cost-v">€ {best["exp"]:,.2f}</span></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="cost-row"><span class="cost-n">Import:</span><span class="cost-v">€ {best["imp"]:,.2f}</span></div>', unsafe_allow_html=True)
        with s2:
            st.markdown(f'<div class="cost-row"><span class="cost-n">Postój i Parkingi:</span><span class="cost-v">€ {best["stay"] + best["park"]:,.2f}</span></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="cost-row"><span class="cost-n">Opłaty dodatkowe:</span><span class="cost-v">€ {best["ata"] + best["ferry"]:,.2f}</span></div>', unsafe_allow_html=True)

        # ALTERNATYWY - PIONOWE KARTY
        st.markdown("<br>### 🚛 DOSTĘPNE OPCJE TRANSPORTU:", unsafe_allow_html=True)
        for r in sorted(results, key=lambda x: x['Total']):
            is_best = "alt-best" if r['Pojazd'] == best['Pojazd'] else ""
            st.markdown(f"""
                <div class="alt-card {is_best}">
                    <div style="font-weight: 900; font-size: 22px; color: white;">{r['Pojazd']} <span style="font-size: 14px; color: #94a3b8; font-weight: 400;">({r['Szt']} szt. | Wykorzystanie: {r['Load']})</span></div>
                    <div style="font-size: 26px; font-weight: 950; color: #ed8936;">€ {r['Total']:,.2f}</div>
                </div>
            """, unsafe_allow_html=True)

    with cr:
        # NAPRAWIONA MAPA (Niezawodny Streamlit Map)
        b_pos = CITY_COORDS["Komorniki (Baza)"]
        d_pos = CITY_COORDS.get(target, [48.8, 2.3])
        
        # Generowanie punktów "ścieżki" dla lepszego wyglądu
        lats = np.linspace(b_pos[0], d_pos[0], 20)
        lons = np.linspace(b_pos[1], d_pos[1], 20)
        path_df = pd.DataFrame({'lat': lats, 'lon': lons})
        
        st.write("### 📍 TRASA PRZEJAZDU")
        st.map(path_df, color='#ed8936', size=20, zoom=4)
        
        st.markdown(f"""
            <div style="background: rgba(237, 137, 54, 0.1); padding: 20px; border-radius: 10px; border: 1px solid #ed8936; margin-top: 20px;">
                <h4 style="color: #ed8936; margin: 0;">PODSUMOWANIE CZASU</h4>
                <p style="color: white; font-size: 18px; margin: 10px 0 0 0;">
                    Łączny czas operacji: <b>{best['transit'] + days} dni</b>
                </p>
            </div>
        """, unsafe_allow_html=True)
