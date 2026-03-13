import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import re
import hashlib
import math
import numpy as np

# ==========================================
# 1. KONFIGURACJA I DANE (SQM CORE)
# ==========================================
SHEET_ID = "1sYlXP6WVzPE09qfmydQYQNsjiZcDgRSJGyWoXfjmkDY"
URL_BAZA = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=CENNIK_BAZA"
URL_OPLATY = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=OPLATY_STALE"
URL_USERS = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=USERS"

# Tranzyty (Dni drogi)
TRANSITS = {
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

COORDS = {
    "Komorniki (Baza)": [52.3358, 16.8122], "Amsterdam": [52.3702, 4.8952], 
    "Berlin": [52.5200, 13.4050], "Londyn": [51.5074, -0.1276],
    "Paryż": [48.8566, 2.3522], "Wiedeń": [48.2082, 16.3738], 
    "Praga": [50.0755, 14.4378], "Genewa": [46.2044, 6.1432], 
    "Barcelona": [41.3851, 2.1734], "Monachium": [48.1351, 11.5820], 
    "Madryt": [40.4168, -3.7038], "Lizbona": [38.7223, -9.1393],
    "Rzym": [41.9028, 12.4964], "Sztokholm": [59.3293, 18.0686]
}

# ==========================================
# 2. WYGLĄD I CSS (EKSTREMALNY KONTRAST)
# ==========================================
st.set_page_config(page_title="SQM VENTAGE", layout="wide")

st.markdown("""
    <style>
    /* Globalne tło i czcionki */
    .stApp { background-color: #05070a !important; color: white !important; }
    
    /* SIDEBAR - WYMUSZENIE BIAŁEGO TEKSTU */
    [data-testid="stSidebar"] { background-color: #0f172a !important; border-right: 1px solid #1e293b; }
    [data-testid="stSidebar"] .stMarkdown p, 
    [data-testid="stSidebar"] label, 
    [data-testid="stSidebar"] span,
    [data-testid="stSidebar"] .stSubheader { 
        color: #FFFFFF !important; 
        font-weight: 800 !important; 
        text-shadow: 1px 1px 2px black;
    }

    /* Naprawa pól wejściowych */
    div[data-baseweb="select"] > div, div[data-baseweb="input"] > div {
        background-color: #1e293b !important; color: white !important;
    }
    
    /* Karty KPI */
    .kpi-card { background: #1e293b; border: 1px solid #334155; padding: 20px; border-radius: 10px; text-align: center; }
    .kpi-val { color: #f97316; font-size: 32px; font-weight: 900; }
    .kpi-lbl { color: #94a3b8; font-size: 11px; text-transform: uppercase; }
    
    /* Branding */
    .brand { font-size: 22px; font-weight: 900; color: #FFFFFF; text-align: center; padding: 15px; border-bottom: 3px solid #f97316; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 3. LOGIKA SYSTEMOWA (AUTH & DATA)
# ==========================================
def get_h(p): return hashlib.sha256(p.strip().encode()).hexdigest()

@st.cache_data(ttl=60)
def load_sqm_data():
    try:
        b = pd.read_csv(URL_BAZA); o = pd.read_csv(URL_OPLATY); u = pd.read_csv(URL_USERS)
        for d in [b, o, u]: d.columns = d.columns.str.strip()
        def cl(v):
            s = re.sub(r'[^\d.]', '', str(v).replace(',', '.'))
            return float(s) if s else 0.0
        for c in ['Eksport', 'Import', 'Postoj']: 
            if c in b.columns: b[c] = b[c].apply(cl)
        o['Wartosc'] = o['Wartosc'].apply(cl)
        return b, o, dict(zip(u['username'].astype(str), u['password'].astype(str)))
    except:
        return pd.DataFrame(), pd.DataFrame(), {"admin": "f3e99d9459eeb7ffc4cd407d890fbf1db011208fa12d8edc501a7ec26da106a3"}

# Inicjalizacja stabilnej sesji
if 'logged' not in st.session_state: st.session_state.logged = False
if 'user' not in st.session_state: st.session_state.user = ""

db_b, db_o, users = load_sqm_data()
cfg = dict(zip(db_o['Parametr'], db_o['Wartosc'])) if not db_o.empty else {}

# LOGOWANIE
if not st.session_state.logged:
    _, c, _ = st.columns([1, 1, 1])
    with c:
        st.markdown("<div style='height:100px;'></div>", unsafe_allow_html=True)
        st.markdown("<h1 style='text-align:center;'>SQM LOGIN</h1>", unsafe_allow_html=True)
        u_i = st.text_input("Użytkownik", key="u_field")
        p_i = st.text_input("Hasło", type="password", key="p_field")
        if st.button("ZALOGUJ", use_container_width=True):
            if u_i in users and users[u_i] == get_h(p_i):
                st.session_state.logged = True
                st.session_state.user = str(u_i)
                st.rerun()
            else:
                st.error("Błąd danych.")
    st.stop()

# ==========================================
# 4. SIDEBAR I NAWIGACJA
# ==========================================
with st.sidebar:
    st.markdown('<div class="brand">SQM VENTAGE</div>', unsafe_allow_html=True)
    st.markdown(f"👤 **{st.session_state.user.upper()}**")
    
    view = st.radio("WYBIERZ MODUŁ", ["📊 KALKULATOR", "⚙️ ADMIN"])
    
    st.markdown("---")
    st.subheader("USTAWIENIA TRASY")
    miasto = st.selectbox("DESTYNACJA", sorted(TRANSITS.keys()))
    tryb = st.radio("TYP", ["Eksport + Import", "Tylko Eksport"])
    waga = st.number_input("WAGA NETTO (KG)", value=1000, step=100)
    w_brutto = waga * 1.2
    
    d_m = st.date_input("MONTAŻ", datetime.now() + timedelta(days=7))
    d_stay = 0
    if "Import" in tryb:
        d_d = st.date_input("DEMONTAŻ", d_m + timedelta(days=5))
        d_stay = max(0, (d_d - d_m).days)

    if st.button("🚪 WYLOGUJ", use_container_width=True):
        st.session_state.logged = False
        st.rerun()

# ==========================================
# 5. MODUŁ ADMIN
# ==========================================
if view == "⚙️ ADMIN":
    if st.session_state.user.lower() != "admin":
        st.error("Tylko admin.")
    else:
        st.header("Baza Stawek")
        st.dataframe(db_b, use_container_width=True)
        st.table(db_o)
    st.stop()

# ==========================================
# 6. KALKULATOR (PEŁNA LOGIKA)
# ==========================================
if view == "📊 KALKULATOR":
    st.markdown(f"## TRASA: KOMORNIKI ➔ {miasto.upper()}")
    
    v_map = {"BUS": 1200, "SOLO": 5500, "FTL": 10500}
    results = []

    for v_n, v_cap in v_map.items():
        match = db_b[(db_b['Miasto'] == miasto) & (db_b['Typ_Pojazdu'] == v_n)]
        if not match.empty:
            r = match.mean(numeric_only=True)
            v_qty = math.ceil(w_brutto / v_cap)
            tranz = TRANSITS.get(miasto, {}).get("BUS" if v_n=="BUS" else "FTL/SOLO", 2)
            
            # Koszty
            c_exp = r['Eksport'] * v_qty
            c_imp = (r['Import'] * v_qty) if "Import" in tryb else 0
            
            # Dodatki
            ata = (cfg.get('ATA_CARNET', 166) if miasto in ["Londyn", "Genewa", "Liverpool", "Manchester"] else 0)
            ferry = (cfg.get('Ferry_UK', 450) if any(x in miasto for x in ["Londyn", "Liverpool", "Manchester"]) else 0)
            postoj = (r['Postoj'] * d_stay * v_qty) + (d_stay * cfg.get('PARKING_DAY', 30) * v_qty)
            
            suma = c_exp + c_imp + ata + ferry + postoj
            
            results.append({
                "Pojazd": v_n, "Szt": v_qty, "Razem €": round(suma, 2), 
                "Exp €": round(c_exp, 2), "Imp €": round(c_imp, 2), "Inne €": round(ata+ferry+postoj, 2),
                "Dni": tranz, "Załadunek": min(100, (w_brutto/(v_qty * v_cap))*100)
            })

    if results:
        top = min(results, key=lambda x: x['Razem €'])
        
        # KPI
        k1, k2, k3, k4 = st.columns(4)
        with k1: st.markdown(f'<div class="kpi-card"><div class="kpi-val">€ {top["Razem €"]:,.2f}</div><div class="kpi-lbl">Cena Optymalna</div></div>', unsafe_allow_html=True)
        with k2: st.markdown(f'<div class="kpi-card"><div class="kpi-val">{top["Szt"]}x {top["Pojazd"]}</div><div class="kpi-lbl">Rekomendacja</div></div>', unsafe_allow_html=True)
        with k3: st.markdown(f'<div class="kpi-card"><div class="kpi-val">{top["Dni"]} dni</div><div class="kpi-lbl">Tranzyt</div></div>', unsafe_allow_html=True)
        with k4: st.markdown(f'<div class="kpi-card"><div class="kpi-val">{w_brutto:,.0f} kg</div><div class="kpi-lbl">Waga Brutto</div></div>', unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Tabele i Mapa
        cL, cR = st.columns([1.5, 1])
        with cL:
            st.subheader("Porównanie Ekonomiczne")
            st.dataframe(
                pd.DataFrame(results),
                column_config={
                    "Razem €": st.column_config.NumberColumn(format="€ %.2f"),
                    "Exp €": st.column_config.NumberColumn(format="€ %.2f"),
                    "Imp €": st.column_config.NumberColumn(format="€ %.2f"),
                    "Inne €": st.column_config.NumberColumn(format="€ %.2f"),
                    "Załadunek": st.column_config.ProgressColumn(format="%d%%", min_value=0, max_value=100)
                },
                use_container_width=True, hide_index=True
            )
            st.info(f"🚚 Wyjazd: {(d_m - timedelta(days=top['Dni']+1)).strftime('%Y-%m-%d')}")

        with cR:
            st.subheader("Mapa")
            s_p = COORDS["Komorniki (Baza)"]; e_p = COORDS.get(miasto, [50, 10])
            m_d = pd.DataFrame({'lat': np.linspace(s_p[0], e_p[0], 10), 'lon': np.linspace(s_p[1], e_p[1], 10)})
            st.map(m_d, color="#f97316", zoom=4)
