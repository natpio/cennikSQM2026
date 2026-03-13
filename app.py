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
    "Komorniki (Baza)": [52.3358, 16.8122],
    "Amsterdam": [52.3702, 4.8952], "Berlin": [52.5200, 13.4050], "Londyn": [51.5074, -0.1276],
    "Paryż": [48.8566, 2.3522], "Wiedeń": [48.2082, 16.3738], "Praga": [50.0755, 14.4378],
    "Genewa": [46.2044, 6.1432], "Zurych": [47.3769, 8.5417], "Barcelona": [41.3851, 2.1734],
    "Monachium": [48.1351, 11.5820], "Mediolan": [45.4642, 9.1900]
}

st.set_page_config(page_title="SQM VANTAGE v14.2", layout="wide")

# --- CSS (Naprawa czytelności tabeli) ---
st.markdown("""
    <style>
    .stApp { background: #0a0e14 !important; }
    .v14-container { background: rgba(17, 25, 40, 0.95) !important; border: 1px solid rgba(255, 255, 255, 0.1) !important; border-radius: 12px; padding: 25px !important; margin-bottom: 20px; }
    .v14-price-tag { font-size: 55px !important; font-weight: 800 !important; color: #ed8936 !important; margin: 5px 0; }
    .v14-stat-box { background: rgba(255, 255, 255, 0.03); padding: 12px; border-radius: 8px; text-align: center; border: 1px solid rgba(255,255,255,0.05); }
    .v14-label { color: #94a3b8; font-size: 0.75rem; text-transform: uppercase; font-weight: bold; }
    .v14-value { color: #ffffff; font-size: 1.1rem; font-weight: 600; }
    
    /* Styl dla tabeli porównawczej */
    .compare-table { width: 100%; border-collapse: collapse; margin-top: 15px; border-radius: 8px; overflow: hidden; }
    .compare-table th { background: rgba(237, 137, 54, 0.2); color: #ed8936; padding: 12px; text-align: left; font-size: 0.85rem; border-bottom: 2px solid rgba(237, 137, 54, 0.3); }
    .compare-table td { padding: 12px; border-top: 1px solid rgba(255,255,255,0.05); color: #e2e8f0; font-size: 0.9rem; background: rgba(255,255,255,0.02); }
    .best-row { background: rgba(237, 137, 54, 0.15) !important; font-weight: bold; border-left: 4px solid #ed8936; }
    </style>
""", unsafe_allow_html=True)

# --- AUTH ---
def make_hash(p): return hashlib.sha256(p.strip().encode()).hexdigest()
cookie_manager = stx.CookieManager()

@st.cache_data(ttl=5)
def load_u():
    try:
        df = pd.read_csv(URL_USERS)
        df.columns = df.columns.str.strip()
        return dict(zip(df['username'].astype(str), df['password'].astype(str)))
    except: return {"admin": "f3e99d9459eeb7ffc4cd407d890fbf1db011208fa12d8edc501a7ec26da106a3"}

user_db = load_u()
if "auth" not in st.session_state: st.session_state.auth = False
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
    mode = st.radio("STRATEGIA", ["DEDYKOWANY", "DOŁADUNEK"])
    target = st.selectbox("MIASTO DOCELOWE", sorted(df_baza['Miasto'].unique()))
    weight = st.number_input("WAGA ŁADUNKU (kg)", value=1000, step=500)
    d_start = st.date_input("ZAŁADUNEK", datetime.now())
    d_end = st.date_input("POWRÓT", datetime.now() + timedelta(days=2))
    days = max(0, (d_end - d_start).days)
    if st.button("WYLOGUJ"):
        cookie_manager.delete("sqm_v14_session")
        st.session_state.auth = False
        st.rerun()

# --- LOGIKA ---
w_eff = weight * cfg.get('WAGA_BUFOR', 1.2)
caps = {"BUS": 1200, "SOLO": 5500, "FTL": 13600}
results = []

for v_type, cap in caps.items():
    res = df_baza[(df_baza['Miasto'] == target) & (df_baza['Typ_Pojazdu'] == v_type)]
    if not res.empty:
        r = res.iloc[0]
        v_count = math.ceil(w_eff / cap)
        
        if mode == "DEDYKOWANY":
            exp, imp = r['Eksport'] * v_count, r['Import'] * v_count
        else:
            ratio = min(1.0, w_eff / cap)
            exp, imp = r['Eksport'] * ratio, r['Import'] * ratio

        stay = r['Postoj'] * days * v_count
        fees = (days * cfg.get('PARKING_DAY', 30) * v_count) + (cfg.get('ATA_CARNET', 166) if target in ["Londyn", "Genewa", "Zurych"] else 0)
        total = exp + imp + stay + fees
        results.append({"typ": v_type, "total": total, "count": v_count})

if results:
    best = min(results, key=lambda x: x['total'])
    
    # --- UI GŁÓWNE ---
    st.markdown(f"### ANALIZA LOGISTYCZNA: KOMORNIKI ➔ {target.upper()}")
    c1, c2 = st.columns([1.4, 1])
    
    with c1:
        # GŁÓWNA KARTA WYNIKU
        st.markdown(f"""
            <div class="v14-container">
                <div class="v14-label">Sugerowana Stawka Projektu ({mode})</div>
                <div class="v14-price-tag">€ {best['total']:,.2f}</div>
                <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 10px; margin-bottom: 25px;">
                    <div class="v14-stat-box"><div class="v14-label">Pojazd</div><div class="v14-value">{best['typ']}</div></div>
                    <div class="v14-stat-box"><div class="v14-label">Ilość</div><div class="v14-value">{best['count']} szt.</div></div>
                    <div class="v14-stat-box"><div class="v14-label">Waga +20%</div><div class="v14-value">{w_eff:,.0f} kg</div></div>
                </div>
        """, unsafe_allow_html=True)

        # TABELA PORÓWNAWCZA (NAPRAWIONA)
        rows_html = ""
        for x in sorted(results, key=lambda x: x['total']):
            is_best = "best-row" if x['typ'] == best['typ'] else ""
            diff = f"+ € {x['total'] - best['total']:,.2f}" if x['total'] > best['total'] else "Najtaniej"
            rows_html += f"""
                <tr class="{is_best}">
                    <td>{x['typ']}</td>
                    <td>{x['count']} szt.</td>
                    <td>€ {x['total']:,.2f}</td>
                    <td style="color: {'#ed8936' if diff == 'Najtaniej' else '#94a3b8'}">{diff}</td>
                </tr>
            """

        st.markdown(f"""
                <div class="v14-label" style="margin-top: 10px;">Porównanie alternatyw:</div>
                <table class="compare-table">
                    <thead>
                        <tr><th>Pojazd</th><th>Ilość</th><th>Koszt Total</th><th>Status</th></tr>
                    </thead>
                    <tbody>
                        {rows_html}
                    </tbody>
                </table>
            </div>
        """, unsafe_allow_html=True)

    with c2:
        # MAPA
        base = CITY_COORDS["Komorniki (Baza)"]
        dest = CITY_COORDS.get(target, [52.5, 13.4])
        map_data = pd.DataFrame({'lat': [base[0], dest[0]], 'lon': [base[1], dest[1]]})
        st.map(map_data, color='#ed8936', size=25)
        st.caption(f"Trasa: Komorniki — {target}")

else:
    st.error("Brak stawek dla tej trasy.")
