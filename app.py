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

st.set_page_config(page_title="SQM LOGISTICS v14.7", layout="wide")

# --- CSS (Maksymalny Kontrast i Czytelność) ---
st.markdown("""
    <style>
    .stApp { background-color: #0e1117 !important; }
    
    /* Nagłówek Trasy */
    .route-header { 
        font-size: 32px !important; font-weight: 800; color: #ffffff; 
        padding: 15px 0; border-bottom: 3px solid #ed8936; margin-bottom: 25px;
        text-transform: uppercase; letter-spacing: 2px;
    }
    
    /* Główna Karta Ceny */
    .main-card {
        background: #1a1f29; border: 2px solid #2d3748; border-radius: 15px;
        padding: 25px; margin-bottom: 20px; box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.5);
    }
    .price-label { color: #ed8936; font-size: 14px; font-weight: bold; text-transform: uppercase; }
    .price-value { color: #ffffff; font-size: 64px; font-weight: 900; margin: 10px 0; }
    
    /* Detale i Składowe */
    .detail-box { background: #262c38; padding: 15px; border-radius: 10px; border-left: 4px solid #ed8936; }
    .detail-label { color: #a0aec0; font-size: 12px; margin-bottom: 5px; }
    .detail-value { color: #ffffff; font-size: 18px; font-weight: bold; }
    
    .cost-grid-item { border-bottom: 1px solid #2d3748; padding: 8px 0; display: flex; justify-content: space-between; }
    .cost-name { color: #cbd5e0; }
    .cost-amount { color: #ffffff; font-weight: bold; }
    
    /* Tabela */
    .stTable { background-color: #1a1f29 !important; border-radius: 10px; overflow: hidden; }
    th { background-color: #2d3748 !important; color: #ed8936 !important; }
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
    st.write(f"👤 **{st.session_state.user}**")
    st.divider()
    
    mode = st.radio("STRATEGIA", ["DEDYKOWANY", "DOŁADUNEK"])
    target = st.selectbox("MIASTO DOCELOWE", sorted(df_baza['Miasto'].unique()))
    weight = st.number_input("WAGA SPRZĘTU (kg)", value=1000, step=500)
    
    d_start = st.date_input("PIERWSZY DZIEŃ MONTAŻU", datetime.now())
    d_end = st.date_input("OSTATNI DZIEŃ MONTAŻU", datetime.now() + timedelta(days=2))
    days = max(0, (d_end - d_start).days)
    
    st.divider()
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
            "Pojazd": v_type, "Szt": v_count, "Załadunek": f"{load_pc:.0f}%", 
            "Suma": total, "exp": exp, "imp": imp, "stay": stay_cost, 
            "park": parking, "ata": ata, "ferry": ferry
        })

if results:
    best = min(results, key=lambda x: x['Suma'])
    
    st.markdown(f'<div class="route-header">LOGISTYKA: KOMORNIKI ➔ {target.upper()}</div>', unsafe_allow_html=True)
    
    col_left, col_right = st.columns([1.8, 1])
    
    with col_left:
        # GŁÓWNA KARTA CENOWA
        st.markdown(f"""
            <div class="main-card">
                <div class="price-label">Rekomendowana Stawka Projektu (Netto)</div>
                <div class="price-value">€ {best['Suma']:,.2f}</div>
                <div style="display: flex; gap: 30px; margin-top: 20px;">
                    <div class="detail-box">
                        <div class="detail-label">TYP POJAZDU</div>
                        <div class="detail-value">{best['Pojazd']} ({best['Szt']} szt.)</div>
                    </div>
                    <div class="detail-box">
                        <div class="detail-label">WAGA Z BUFOREM</div>
                        <div class="detail-value">{w_eff:,.0f} kg</div>
                    </div>
                    <div class="detail-box">
                        <div class="detail-label">WYKORZYSTANIE</div>
                        <div class="detail-value">{best['Załadunek']}</div>
                    </div>
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        # SKŁADOWE KOSZTÓW
        st.markdown("### 📊 SZCZEGÓŁOWE ZESTAWIENIE KOSZTÓW:")
        sc1, sc2 = st.columns(2)
        with sc1:
            st.markdown(f'<div class="cost-grid-item"><span class="cost-name">Eksport (Srednia):</span><span class="cost-amount">€ {best["exp"]:,.2f}</span></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="cost-grid-item"><span class="cost-name">Import (Srednia):</span><span class="cost-amount">€ {best["imp"]:,.2f}</span></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="cost-grid-item"><span class="cost-name">Postój przewoźnika:</span><span class="cost-amount">€ {best["stay"]:,.2f}</span></div>', unsafe_allow_html=True)
        with sc2:
            st.markdown(f'<div class="cost-grid-item"><span class="cost-name">Parkingi SQM:</span><span class="cost-amount">€ {best["park"]:,.2f}</span></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="cost-grid-item"><span class="cost-name">Odprawa ATA:</span><span class="cost-amount">€ {best["ata"]:,.2f}</span></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="cost-grid-item"><span class="cost-name">Promy / Mosty:</span><span class="cost-amount">€ {best["ferry"]:,.2f}</span></div>', unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        st.write("### 🚛 PORÓWNANIE ALTERNATYW")
        df_show = pd.DataFrame(results)[["Pojazd", "Szt", "Załadunek", "Suma"]]
        df_show["Suma"] = df_show["Suma"].map("€ {:,.2f}".format)
        st.table(df_show)

    with col_right:
        base, dest = CITY_COORDS["Komorniki (Baza)"], CITY_COORDS.get(target, [52.5, 13.4])
        st.map(pd.DataFrame({'lat': [base[0], dest[0]], 'lon': [base[1], dest[1]]}), color='#ed8936')
        st.info(f"Czas operacji: {days} dni postoju na miejscu.")
