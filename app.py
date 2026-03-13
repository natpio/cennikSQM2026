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

st.set_page_config(page_title="SQM LOGISTICS VANTAGE v14.5", layout="wide")

# --- CSS (Naprawa czytelności i UI) ---
st.markdown("""
    <style>
    .stApp { background: #0a0e14 !important; }
    .header-route { color: #ffffff !important; font-size: 24px !important; font-weight: 800 !important; letter-spacing: 1px; padding: 10px 0; border-bottom: 2px solid #ed8936; margin-bottom: 20px; }
    .v14-container { background: rgba(17, 25, 40, 0.95); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 12px; padding: 20px; margin-bottom: 15px; }
    .v14-price-tag { font-size: 55px; font-weight: 800; color: #ed8936; margin: 5px 0; }
    .v14-label { color: #94a3b8; font-size: 0.75rem; text-transform: uppercase; font-weight: bold; }
    .v14-value { color: #ffffff; font-size: 1.1rem; font-weight: 600; }
    
    /* Grid dla składowych kosztów */
    .cost-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 10px; margin-top: 15px; }
    .cost-item { background: rgba(255, 255, 255, 0.03); border: 1px solid rgba(255, 255, 255, 0.05); padding: 10px; border-radius: 8px; }
    .cost-price { color: #e2e8f0; font-weight: bold; font-size: 1rem; }
    
    .compare-table { width: 100%; border-collapse: collapse; }
    .compare-table th { background: rgba(237, 137, 54, 0.2); color: #ed8936; padding: 10px; text-align: left; }
    .compare-table td { padding: 10px; border-bottom: 1px solid rgba(255,255,255,0.05); color: #e2e8f0; }
    .best-row { background: rgba(237, 137, 54, 0.15); border-left: 4px solid #ed8936; }
    
    /* Naprawa sidebaru */
    .user-info { color: #ed8936; font-weight: bold; margin-bottom: 20px; padding: 5px; border-radius: 5px; background: rgba(237, 137, 54, 0.1); text-align: center; }
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
    st.markdown(f'<div class="user-info">Zalogowany: {st.session_state.user}</div>', unsafe_allow_html=True)
    
    mode = st.radio("STRATEGIA", ["DEDYKOWANY", "DOŁADUNEK"])
    target = st.selectbox("MIASTO DOCELOWE", sorted(df_baza['Miasto'].unique()))
    weight = st.number_input("WAGA SPRZĘTU (kg)", value=1000, step=500)
    
    d_start = st.date_input("PIERWSZY DZIEŃ MONTAŻU", datetime.now())
    d_end = st.date_input("OSTATNI DZIEŃ MONTAŻU", datetime.now() + timedelta(days=2))
    days = max(0, (d_end - d_start).days)
    
    if st.button("WYLOGUJ"):
        cookie_manager.delete("sqm_v14_session")
        st.session_state.auth = False
        st.rerun()

# --- LOGIKA WYBORU ---
w_eff = weight * cfg.get('WAGA_BUFOR', 1.2)
caps = {"BUS": 1200, "SOLO": 5500, "FTL": 10500} # FTL wg ustaleń 10.5t
results = []

for v_type, cap in caps.items():
    res = df_baza[(df_baza['Miasto'] == target) & (df_baza['Typ_Pojazdu'] == v_type)]
    if not res.empty:
        r = res.iloc[0]
        v_count = math.ceil(w_eff / cap)
        load_pc = min(100, (w_eff / (v_count * cap)) * 100)
        
        # Obliczenia bazowe
        if mode == "DEDYKOWANY":
            exp, imp = r['Eksport'] * v_count, r['Import'] * v_count
        else:
            ratio = min(1.0, w_eff / cap)
            exp, imp = r['Eksport'] * ratio, r['Import'] * ratio

        # Dodatkowe koszty (promy, mosty, ATA - zdefiniowane w bazie lub statyczne)
        ata = (cfg.get('ATA_CARNET', 166) if target in ["Londyn", "Genewa", "Zurych"] else 0)
        ferry = (cfg.get('Ferry_UK', 450) if target == "Londyn" else 0)
        parking = (days * cfg.get('PARKING_DAY', 30) * v_count)
        stay_cost = r['Postoj'] * days * v_count
        
        total = exp + imp + stay_cost + parking + ata + ferry
        
        results.append({
            "typ": v_type, "total": total, "count": v_count, "load": load_pc,
            "detale": {"Exp": exp, "Imp": imp, "Stay": stay_cost, "Park": parking, "ATA": ata, "Ferry": ferry}
        })

if results:
    best = min(results, key=lambda x: x['total'])
    
    # Nagłówek trasy o wysokim kontraście
    st.markdown(f'<div class="header-route">ANALIZA LOGISTYCZNA: KOMORNIKI ➔ {target.upper()}</div>', unsafe_allow_html=True)
    
    c1, c2 = st.columns([1.6, 1])
    
    with c1:
        # GŁÓWNA KARTA CENOWA
        st.markdown(f"""
            <div class="v14-container">
                <div class="v14-label">Rekomendowana Stawka Projektu (Netto)</div>
                <div class="v14-price-tag">€ {best['total']:,.2f}</div>
                <div style="display: flex; gap: 20px;">
                    <div><div class="v14-label">Pojazd</div><div class="v14-value">{best['typ']} ({best['count']} szt.)</div></div>
                    <div><div class="v14-label">Waga (+20%)</div><div class="v14-value">{w_eff:,.0f} kg</div></div>
                    <div><div class="v14-label">Wykorzystanie</div><div class="v14-value">{best['load']:.1f}%</div></div>
                </div>
                
                <div class="v14-label" style="margin-top:20px; border-top: 1px solid rgba(255,255,255,0.1); padding-top:15px;">Składowe ceny:</div>
                <div class="cost-grid">
                    <div class="cost-item"><div class="v14-label">Export</div><div class="cost-price">€ {best['detale']['Exp']:,.2f}</div></div>
                    <div class="cost-item"><div class="v14-label">Import</div><div class="cost-price">€ {best['detale']['Imp']:,.2f}</div></div>
                    <div class="cost-item"><div class="v14-label">Postój</div><div class="cost-price">€ {best['detale']['Stay']:,.2f}</div></div>
                    <div class="cost-item"><div class="v14-label">Parkingi</div><div class="cost-price">€ {best['detale']['Park']:,.2f}</div></div>
                    <div class="cost-item"><div class="v14-label">ATA / Cło</div><div class="cost-price">€ {best['detale']['ATA']:,.2f}</div></div>
                    <div class="cost-item"><div class="v14-label">Promy/Mosty</div><div class="cost-price">€ {best['detale']['Ferry']:,.2f}</div></div>
                </div>
            </div>
        """, unsafe_allow_html=True)

        # TABELA PORÓWNAWCZA
        rows = "".join([f"<tr class='{'best-row' if x['typ'] == best['typ'] else ''}'><td>{x['typ']}</td><td>{x['count']}</td><td>{x['load']:.0f}%</td><td>€ {x['total']:,.2f}</td><td>{'Najtaniej' if x['typ'] == best['typ'] else '+ € ' + f'{x['total'] - best['total']:,.2f}'}</td></tr>" for x in sorted(results, key=lambda x: x['total'])])
        
        st.markdown(f"""
            <div class="v14-container">
                <div class="v14-label" style="margin-bottom:10px;">Porównanie alternatyw:</div>
                <table class="compare-table">
                    <thead><tr><th>Pojazd</th><th>Szt.</th><th>Ładunek</th><th>Suma</th><th>Różnica</th></tr></thead>
                    <tbody>{rows}</tbody>
                </table>
            </div>
        """, unsafe_allow_html=True)

    with c2:
        base, dest = CITY_COORDS["Komorniki (Baza)"], CITY_COORDS.get(target, [52.5, 13.4])
        st.map(pd.DataFrame({'lat': [base[0], dest[0]], 'lon': [base[1], dest[1]]}), color='#ed8936', size=40)
        st.caption(f"Trasa logistyczna dla SQM: Komorniki — {target}")
