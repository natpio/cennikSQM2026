import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import re
import hashlib
import extra_streamlit_components as stx
import math
import pydeck as pdk

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

st.set_page_config(page_title="SQM LOGISTICS v14.8", layout="wide")

# --- CSS (Ultra High Contrast) ---
st.markdown("""
    <style>
    .stApp { background-color: #05070a !important; }
    
    /* Nagłówek Trasy */
    .route-header { 
        font-size: 34px !important; font-weight: 900; color: #ffffff; 
        padding: 10px 0; border-bottom: 4px solid #ed8936; margin-bottom: 30px;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.5);
    }
    
    /* Główna Sekcja */
    .hero-card {
        background: linear-gradient(145deg, #111827, #1f2937);
        border: 1px solid #374151; border-radius: 20px;
        padding: 35px; margin-bottom: 25px; box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.7);
    }
    .main-price-label { color: #ed8936; font-size: 18px; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; }
    .main-price-value { color: #ffffff; font-size: 82px; font-weight: 900; line-height: 1; margin: 15px 0; }
    
    /* Nowe Karty Danych */
    .data-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin-top: 25px; }
    .data-item { background: rgba(255,255,255,0.03); padding: 15px; border-radius: 12px; border: 1px solid rgba(255,255,255,0.1); }
    .data-label { color: #9ca3af; font-size: 11px; text-transform: uppercase; font-weight: 600; }
    .data-value { color: #ffffff; font-size: 20px; font-weight: 800; }
    
    /* Porównanie Alternatyw - Karty */
    .alt-card { 
        background: #111827; border-left: 5px solid #4b5563; 
        padding: 15px; margin-bottom: 10px; border-radius: 8px;
        display: flex; justify-content: space-between; align-items: center;
    }
    .alt-best { border-left: 5px solid #ed8936; background: rgba(237, 137, 54, 0.05); }
    
    /* Składowe - Czytelna Lista */
    .cost-row { display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid #374151; }
    .cost-n { color: #d1d5db; font-size: 15px; }
    .cost-v { color: #ffffff; font-weight: 700; font-size: 16px; }
    </style>
""", unsafe_allow_html=True)

# --- AUTH & DATA (Bez zmian w logice) ---
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
    st.image("https://www.sqm.pl/wp-content/themes/sqm/img/logo-sqm.png", width=120)
    st.info(f"User: {st.session_state.user}")
    mode = st.radio("STRATEGIA", ["DEDYKOWANY", "DOŁADUNEK"])
    target = st.selectbox("MIASTO DOCELOWE", sorted(df_baza['Miasto'].unique()))
    weight = st.number_input("WAGA SPRZĘTU (kg)", value=1000, step=500)
    d_start = st.date_input("PIERWSZY DZIEŃ MONTAŻU", datetime.now())
    d_end = st.date_input("OSTATNI DZIEŃ MONTAŻU", datetime.now() + timedelta(days=2))
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
        r = res.iloc[0]
        v_count = math.ceil(w_eff / cap)
        load_pc = min(100, (w_eff / (v_count * cap)) * 100)
        exp = (r['Eksport'] * v_count if mode == "DEDYKOWANY" else r['Eksport'] * (w_eff/cap))
        imp = (r['Import'] * v_count if mode == "DEDYKOWANY" else r['Import'] * (w_eff/cap))
        ata = (cfg.get('ATA_CARNET', 166) if target in ["Londyn", "Genewa", "Zurych"] else 0)
        ferry = (cfg.get('Ferry_UK', 450) if target == "Londyn" else 0)
        parking = (days * cfg.get('PARKING_DAY', 30) * v_count)
        stay_cost = r['Postoj'] * days * v_count
        transit = (2 if target in ["Barcelona", "Londyn"] else 1) # Prosta logika tranzytu
        
        total = exp + imp + stay_cost + parking + ata + ferry
        results.append({"Pojazd": v_type, "Szt": v_count, "Load": f"{load_pc:.0f}%", "Total": total, "exp": exp, "imp": imp, "stay": stay_cost, "park": parking, "ata": ata, "ferry": ferry, "transit": transit})

if results:
    best = min(results, key=lambda x: x['Total'])
    st.markdown(f'<div class="route-header">LOGISTYKA: KOMORNIKI ➔ {target.upper()}</div>', unsafe_allow_html=True)
    
    c_left, c_right = st.columns([1.8, 1])
    
    with c_left:
        # GŁÓWNA KARTA CENOWA (v14.8 - Mega czcionka)
        st.markdown(f"""
            <div class="hero-card">
                <div class="main-price-label">Rekomendowana Stawka Projektu (Netto)</div>
                <div class="main-price-value">€ {best['Total']:,.2f}</div>
                <div class="data-grid">
                    <div class="data-item"><div class="data-label">Pojazd</div><div class="data-value">{best['Pojazd']} ({best['Szt']} szt.)</div></div>
                    <div class="data-item"><div class="data-label">Waga (+20%)</div><div class="data-value">{w_eff:,.0f} kg</div></div>
                    <div class="data-item"><div class="data-label">Tranzyt</div><div class="data-value">{best['transit']} dni</div></div>
                    <div class="data-item"><div class="data-label">Postój</div><div class="data-value">{days} dni</div></div>
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        # SKŁADOWE (Lista o wysokim kontraście)
        st.markdown("### 📋 SZCZEGÓŁOWE SKŁADOWE:")
        sc1, sc2 = st.columns(2)
        with sc1:
            st.markdown(f'<div class="cost-row"><span class="cost-n">Eksport:</span><span class="cost-v">€ {best["exp"]:,.2f}</span></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="cost-row"><span class="cost-n">Import:</span><span class="cost-v">€ {best["imp"]:,.2f}</span></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="cost-row"><span class="cost-n">Postój (montaż):</span><span class="cost-v">€ {best["stay"]:,.2f}</span></div>', unsafe_allow_html=True)
        with sc2:
            st.markdown(f'<div class="cost-row"><span class="cost-n">Parkingi SQM:</span><span class="cost-v">€ {best["park"]:,.2f}</span></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="cost-row"><span class="cost-n">Odprawa/ATA:</span><span class="cost-v">€ {best["ata"]:,.2f}</span></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="cost-row"><span class="cost-n">Promy/Mosty:</span><span class="cost-v">€ {best["ferry"]:,.2f}</span></div>', unsafe_allow_html=True)

        # PORÓWNANIE (Karty zamiast tabeli)
        st.markdown("<br>### 🚛 ALTERNATYWNE POJAZDY:", unsafe_allow_html=True)
        for r in sorted(results, key=lambda x: x['Total']):
            is_best = "alt-best" if r['Pojazd'] == best['Pojazd'] else ""
            st.markdown(f"""
                <div class="alt-card {is_best}">
                    <div style="font-weight: 800; font-size: 18px; color: white;">{r['Pojazd']} <span style="font-size: 12px; color: #9ca3af;">({r['Szt']} szt., {r['Load']} załadunku)</span></div>
                    <div style="font-size: 20px; font-weight: 900; color: #ed8936;">€ {r['Total']:,.2f}</div>
                </div>
            """, unsafe_allow_html=True)

    with c_right:
        # PODRASOWANA MAPA (Dark Style)
        base_coords = CITY_COORDS["Komorniki (Baza)"]
        dest_coords = CITY_COORDS.get(target, [41.3, 2.1])
        
        view_state = pdk.ViewState(latitude=(base_coords[0]+dest_coords[0])/2, longitude=(base_coords[1]+dest_coords[1])/2, zoom=4, pitch=45)
        layer = pdk.Layer("ArcLayer", data=[{'s': base_coords[::-1], 't': dest_coords[::-1]}], get_source_position="s", get_target_position="t", get_source_color=[237, 137, 54, 200], get_target_color=[255, 255, 255, 200], stroke_width=4)
        
        st.pydeck_chart(pdk.Deck(layers=[layer], initial_view_state=view_state, map_style="mapbox://styles/mapbox/dark-v10"))
        st.success(f"Trasa potwierdzona. Całkowity czas operacji: {best['transit'] + days} dni.")
