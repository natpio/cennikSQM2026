import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import re
import hashlib
import math
import pydeck as pdk

# --- 1. KONFIGURACJA ZASOBÓW (GOOGLE SHEETS) ---
SHEET_ID = "1sYlXP6WVzPE09qfmydQYQNsjiZcDgRSJGyWoXfjmkDY"
URL_BAZA = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=CENNIK_BAZA"
URL_OPLATY = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=OPLATY_STALE"
URL_USERS = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=USERS"

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
st.set_page_config(page_title="SQM VENTAGE", layout="wide", initial_sidebar_state="expanded")

# --- 3. STYLE CSS (ZGODNIE ZE SCREENEM) ---
st.markdown("""
    <style>
    .stApp { background-color: #05070a !important; }
    [data-testid="stSidebar"] { background-color: #0f172a !important; border-right: 1px solid #334155; }
    [data-testid="stSidebar"] label, [data-testid="stSidebar"] p { color: white !important; font-weight: 700 !important; }
    .route-header { font-size: 32px !important; font-weight: 900; color: #ffffff; border-bottom: 4px solid #ed8936; margin-bottom: 30px; padding-bottom: 10px; }
    .hero-card { background: #161b2e; border-radius: 15px; border-left: 5px solid #ed8936; padding: 35px; margin-bottom: 25px; }
    .main-price-value { color: #ffffff; font-size: 64px; font-weight: 900; line-height: 1.1; margin: 10px 0; }
    .breakdown-grid { display: flex; gap: 50px; border-top: 1px solid #2e364f; padding-top: 25px; margin-top: 25px; }
    .cost-item { font-size: 11px; color: #94a3b8; text-transform: uppercase; letter-spacing: 1px; }
    .cost-item b { color: #ffffff; font-size: 20px; display: block; margin-top: 5px; font-weight: 900; }
    .stat-pill { background: rgba(237, 137, 54, 0.1); border: 1px solid #ed8936; padding: 8px 15px; border-radius: 8px; color: #ed8936; font-weight: 800; font-size: 13px; margin-right: 10px; }
    .alt-card { background: #1e2530; padding: 18px 25px; border-radius: 12px; margin-bottom: 12px; display: flex; justify-content: space-between; align-items: center; }
    .alt-label { color: #f39c12; font-weight: bold; font-size: 16px; }
    .alt-price { color: #ffffff; font-size: 22px; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

# --- 4. FUNKCJE POMOCNICZE ---
def make_hash(password): return hashlib.sha256(password.strip().encode()).hexdigest()

@st.cache_data(ttl=60)
def fetch_data():
    try:
        b = pd.read_csv(URL_BAZA); o = pd.read_csv(URL_OPLATY)
        b.columns = b.columns.str.strip(); o.columns = o.columns.str.strip()
        def clean_val(v):
            if pd.isna(v): return 0.0
            s = re.sub(r'[^\d.]', '', str(v).replace(',', '.')); return float(s) if s else 0.0
        for col in ['Eksport', 'Import', 'Postoj']:
            if col in b.columns: b[col] = b[col].apply(clean_val)
        if 'Wartosc' in o.columns: o['Wartosc'] = o['Wartosc'].apply(clean_val)
        return b, o
    except: return pd.DataFrame(), pd.DataFrame()

@st.cache_data(ttl=60)
def load_users():
    try:
        df = pd.read_csv(URL_USERS); df.columns = df.columns.str.strip()
        return dict(zip(df['username'].astype(str), df['password'].astype(str)))
    except: return {"admin": "f3e99d9459eeb7ffc4cd407d890fbf1db011208fa12d8edc501a7ec26da106a3"}

# --- 5. LOGOWANIE ---
if "authenticated" not in st.session_state: st.session_state.authenticated = False
if not st.session_state.authenticated:
    _, col_log, _ = st.columns([1, 1.2, 1])
    with col_log:
        st.markdown("<h1 style='color:white;text-align:center;'>SQM <span style='color:#ed8936;'>VENTAGE</span></h1>", unsafe_allow_html=True)
        u_input = st.text_input("Użytkownik")
        p_input = st.text_input("Hasło", type="password")
        if st.button("ZALOGUJ DO SYSTEMU", use_container_width=True):
            user_db = load_users()
            if u_input in user_db and user_db[u_input] == make_hash(p_input):
                st.session_state.authenticated = True
                st.session_state.current_user = u_input
                st.rerun()
    st.stop()

# --- 6. PRZYGOTOWANIE DANYCH ---
df_baza, df_oplaty = fetch_data()
cfg = dict(zip(df_oplaty['Parametr'], df_oplaty['Wartosc'])) if not df_oplaty.empty else {}

# --- 7. SIDEBAR ---
with st.sidebar:
    st.markdown("### KONFIGURACJA")
    trip_type = st.radio("KIERUNEK", ["PEŁNA TRASA (EXP+IMP)", "TYLKO DOSTAWA (ONE-WAY)"])
    mode = st.radio("STRATEGIA", ["DEDYKOWANY", "DOŁADUNEK"])
    target_city = st.selectbox("MIEJSCE DOCELOWE", sorted(TRANSIT_DATA.keys()))
    st.markdown("---")
    weight_netto = st.number_input("WAGA NETTO (KG)", value=8500, step=100)
    weight_brutto = weight_netto * 1.20
    st.markdown(f'<div style="background:rgba(237,137,54,0.1); border:1px solid #ed8936; padding:15px; border-radius:10px; color:#ed8936; text-align:center;"><div style="font-size:10px; font-weight:bold;">BRUTTO (ESTYMACJA)</div><div style="font-size:22px; font-weight:900;">{weight_brutto:,.0f} KG</div></div>', unsafe_allow_html=True)
    st.markdown("---")
    date_start = st.date_input("DZIEŃ MONTAŻU", datetime.now() + timedelta(days=14))
    days_stay = 0
    if trip_type == "PEŁNA TRASA (EXP+IMP)":
        date_end = st.date_input("DZIEŃ DEMONTAŻU", date_start + timedelta(days=3))
        days_stay = max(0, (date_end - date_start).days)
    if st.button("🚪 WYLOGUJ", use_container_width=True):
        st.session_state.clear(); st.rerun()

# --- 8. LOGIKA WYCENY (BUS=SQM, SOLO/FTL=NAJTAŃSZA SPEDYCJA TCO) ---
v_types = {"BUS": 1200, "SOLO": 5500, "FTL": 10500}
FERRY_CITIES = ["Londyn", "Liverpool", "Manchester", "Sztokholm"]
final_results = []

if not df_baza.empty:
    safe_rates = {}
    for vt in v_types.keys():
        city_rates = df_baza[(df_baza['Miasto'] == target_city) & (df_baza['Typ_Pojazdu'] == vt)].copy()
        if city_rates.empty: continue

        if vt == "BUS":
            # LOGIKA: TYLKO WŁASNY SQM (BEZ NARZUTU 15%)
            sqm = city_rates[city_rates['Przewoznik'].str.contains('SQM', case=False, na=False)]
            if not sqm.empty:
                f_exp = sqm.iloc[0]['Eksport']
                f_imp = sqm.iloc[0]['Import'] if trip_type != "TYLKO DOSTAWA (ONE-WAY)" else 0
                f_stay = sqm.iloc[0]['Postoj']
                curr_ferry = cfg.get('Ferry_UK', 450) if target_city in FERRY_CITIES else 0
                safe_rates[vt] = {'exp': f_exp, 'imp': f_imp, 'stay': f_stay, 'ferry': curr_ferry, 'raw_exp': f_exp}
        else:
            # LOGIKA: NAJTAŃSZA SPEDYCJA POD WZGLĘDEM TCO (EXP+IMP+POSTÓJ)
            m_rows = city_rates[~city_rates['Przewoznik'].str.contains('SQM', case=False, na=False)].copy()
            if not m_rows.empty:
                best_tco = float('inf')
                best_data = None
                for _, row in m_rows.iterrows():
                    p_exp = row['Eksport']
                    p_imp = row['Import'] if trip_type != "TYLKO DOSTAWA (ONE-WAY)" else 0
                    p_stay_total = row['Postoj'] * days_stay
                    total_tco = p_exp + p_imp + p_stay_total
                    if total_tco < best_tco:
                        best_tco = total_tco
                        best_data = {'exp': p_exp, 'imp': p_imp, 'stay': row['Postoj'], 'ferry': 0, 'raw_exp': p_exp}
                if best_data: safe_rates[vt] = best_data

    # GENEROWANIE KOMBINACJI (DEDYKOWANE)
    if safe_rates:
        max_f = math.ceil(weight_brutto / 10500) + 1
        for f in range(max_f + 1):
            for s in range(3):
                for b in range(5):
                    total_cap = f*10500 + s*5500 + b*1200
                    if total_cap >= weight_brutto and total_cap <= weight_brutto + 10500:
                        combo = {"FTL": f, "SOLO": s, "BUS": b}
                        c_exp=0; c_imp=0; c_stay=0; c_ata=0; c_ferry=0; v_labels=[]; max_tr=0
                        for v_n, qty in combo.items():
                            if qty == 0 or v_n not in safe_rates: continue
                            r = safe_rates[v_n]
                            v_labels.append(f"{qty}x {v_n}")
                            c_exp += r['raw_exp'] * qty
                            c_imp += r['imp'] * qty
                            c_stay += r['stay'] * days_stay * qty
                            c_ferry += r['ferry'] * qty
                            if target_city in ["Londyn", "Liverpool", "Manchester", "Genewa", "Bazylea"]:
                                c_ata += cfg.get('ATA_CARNET', 166) * qty
                            tr = TRANSIT_DATA.get(target_city, {}).get("BUS" if v_n=="BUS" else "FTL/SOLO", 2)
                            max_tr = max(max_tr, tr)
                        
                        final_results.append({
                            "v_label": ", ".join(v_labels),
                            "total": c_exp + c_imp + c_stay + c_ata + c_ferry,
                            "tr": max_tr, "util": (weight_brutto/total_cap)*100,
                            "brk": {"Eksport": c_exp, "ATA": c_ata, "Promy": c_ferry, "Import": c_imp, "Postój": c_stay}
                        })
                        break

# --- 9. WIDOK GŁÓWNY ---
if final_results:
    res = sorted(final_results, key=lambda x: x['total'])
    best = res[0]
    
    st.markdown(f'<div class="route-header">KOMORNIKI ➔ {target_city.upper()}</div>', unsafe_allow_html=True)
    
    col_main, col_map = st.columns([1.8, 1])
    
    with col_main:
        # GŁÓWNA KARTA CENY
        st.markdown(f"""
            <div class="hero-card">
                <div style="color:#94a3b8; font-size:12px; font-weight:bold; letter-spacing:1px;">NAJTAŃSZA KOMBINACJA (NETTO)</div>
                <div class="main-price-value">€ {best['total']:,.2f}</div>
                <div class="breakdown-grid">
                    <div class="cost-item">Eksport<b>€ {best['brk']['Eksport']:,.0f}</b></div>
                    <div class="cost-item">ATA<b>€ {best['brk']['ATA']:,.0f}</b></div>
                    <div class="cost-item">Promy<b>€ {best['brk']['Promy']:,.0f}</b></div>
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        # PIGUŁKI STATUSU
        i1, i2, i3, i4 = st.columns(4)
        i1.markdown(f'<div class="stat-pill">🚚 {best["v_label"]}</div>', unsafe_allow_html=True)
        i2.markdown(f'<div class="stat-pill">⏱️ {best["tr"]} DNI</div>', unsafe_allow_html=True)
        i3.markdown(f'<div class="stat-pill">📦 {best["util"]:.0f}%</div>', unsafe_allow_html=True)
        i4.markdown(f'<div class="stat-pill">📅 {date_start.strftime("%d.%m")}</div>', unsafe_allow_html=True)
        
        st.markdown("<br><br>### 📊 PORÓWNANIE INNYCH KOMBINACJI", unsafe_allow_html=True)
        for r in res[:5]:
            st.markdown(f"""
                <div class="alt-card">
                    <span class="alt-label">{r['v_label']} <small style="color:#64748b; font-weight:normal;">(Utylizacja: {r['util']:.0f}%)</small></span>
                    <span class="alt-price">€ {r['total']:,.2f}</span>
                </div>
            """, unsafe_allow_html=True)

    with col_map:
        s_c = CITY_COORDS["Komorniki (Baza)"]
        e_c = CITY_COORDS.get(target_city, [52, 13])
        st.pydeck_chart(pdk.Deck(
            map_style="mapbox://styles/mapbox/dark-v10",
            initial_view_state=pdk.ViewState(latitude=(s_c[0]+e_c[0])/2, longitude=(s_c[1]+e_c[1])/2, zoom=4),
            layers=[pdk.Layer("ArcLayer", data=[{"s": [s_c[1], s_c[0]], "e": [e_c[1], e_c[0]]}], 
            get_source_position="s", get_target_position="e", get_source_color=[237, 137, 54], get_target_color=[255, 255, 255], get_width=4)]
        ))
        st.info(f"Rekomendacja: Dla wagi {weight_brutto:,.0f} kg brutto, najkorzystniejszym rozwiązaniem jest: {best['v_label']}.")

# --- 10. ADMIN TOOL ---
if st.session_state.current_user == "admin":
    with st.expander("⚙️ NARZĘDZIA ADMINISTRATORA"):
        st.dataframe(df_baza, use_container_width=True)
        if st.button("🔄 ODŚWIEŻ DANE Z ARKUSZA"):
            st.cache_data.clear()
            st.rerun()
