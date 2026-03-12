import streamlit as st
import pandas as pd
from datetime import datetime
import re

# --- KONFIGURACJA ---
SHEET_ID = "1sYlXP6WVzPE09qfmydQYQNsjiZcDgRSJGyWoXfjmkDY"
SHEET_NAME_BAZA = "CENNIK_BAZA"
SHEET_NAME_OPLATY = "OPLATY_STALE"

URL_BAZA = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={SHEET_NAME_BAZA}"
URL_OPLATY = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={SHEET_NAME_OPLATY}"

st.set_page_config(page_title="SQM VANTAGE | Logistics", layout="wide")

# --- CUSTOM CSS (Styl Glassmorphism z załącznika) ---
st.markdown("""
    <style>
    /* Tło całej aplikacji */
    .stApp {
        background: radial-gradient(circle at 70% 20%, #1e293b 0%, #030508 100%);
        color: #e2e8f0;
    }

    /* Sidebar - Szklany efekt */
    [data-testid="stSidebar"] {
        background-color: rgba(15, 23, 42, 0.8);
        backdrop-filter: blur(10px);
        border-right: 1px solid rgba(255, 255, 255, 0.1);
    }

    /* Karty parametrów (Metric Cards) */
    .metric-card {
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.1);
        padding: 20px;
        border-radius: 15px;
        backdrop-filter: blur(5px);
        text-align: left;
    }
    .metric-label { font-size: 0.8rem; color: #94a3b8; text-transform: uppercase; letter-spacing: 1px; }
    .metric-value { font-size: 1.5rem; font-weight: 700; color: #f8fafc; }

    /* Główna karta z ceną (Kopiujemy styl z obrazka) */
    .price-container {
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.15);
        border-radius: 24px;
        padding: 40px;
        margin: 20px 0;
        box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
        backdrop-filter: blur(20px);
        position: relative;
        overflow: hidden;
    }
    
    .price-container::before {
        content: "";
        position: absolute;
        top: 0; left: 0; width: 6px; height: 100%;
        background: #ed8936; /* Pomarańcz SQM */
    }

    .price-label { font-size: 1rem; color: #ed8936; font-weight: 600; text-transform: uppercase; margin-bottom: 10px; }
    .price-value { font-size: 5rem; font-weight: 900; color: #ffffff; line-height: 1; }
    .price-currency { font-size: 1.5rem; font-weight: 400; color: #94a3b8; }
    
    /* Detale pod ceną */
    .detail-row { display: flex; gap: 20px; margin-top: 25px; border-top: 1px solid rgba(255,255,255,0.1); padding-top: 20px; }
    .detail-item { font-size: 0.9rem; color: #cbd5e1; }
    .detail-item b { color: #ffffff; }

    /* Przycisk Admina */
    .stCheckbox label { color: #94a3b8 !important; }
    </style>
    """, unsafe_allow_html=True)

# --- FUNKCJE DANYCH ---
@st.cache_data(ttl=300)
def fetch_data():
    try:
        df_baza = pd.read_csv(URL_BAZA)
        df_oplaty = pd.read_csv(URL_OPLATY)
        df_baza.columns = df_baza.columns.str.strip()
        df_oplaty.columns = df_oplaty.columns.str.strip()

        def clean_numeric(val):
            if pd.isna(val): return 0.0
            s = str(val).replace(',', '.').strip()
            s = re.sub(r'[^\d.]', '', s)
            return float(s) if s else 0.0

        for col in ['Eksport', 'Import', 'Postoj']:
            if col in df_baza.columns:
                df_baza[col] = df_baza[col].apply(clean_numeric)
        
        df_oplaty['Wartosc'] = df_oplaty['Wartosc'].apply(clean_numeric)
        return df_baza, df_oplaty
    except Exception as e:
        st.error(f"Data Error: {e}")
        return None, None

df_baza, df_oplaty = fetch_data()

if df_baza is not None and df_oplaty is not None:
    cfg = dict(zip(df_oplaty['Parametr'], df_oplaty['Wartosc']))
    
    # --- SIDEBAR ---
    with st.sidebar:
        st.image("https://www.sqm.pl/wp-content/themes/sqm/img/logo-sqm.png", width=160)
        st.markdown("<br>", unsafe_allow_html=True)
        
        miasta = sorted(df_baza['Miasto'].dropna().unique())
        wybrane_miasto = st.selectbox("DESTINATION", miasta)
        
        waga_input = st.number_input("MAIN PROJECT WEIGHT (kg)", min_value=0, value=500, step=100)
        
        st.markdown("---")
        data_zal = st.date_input("LOADING DATE", datetime.now())
        data_roz = st.date_input("RETURN DATE", datetime.now())
        
        dni_postoju = (data_roz - data_zal).days
        dni_postoju = max(0, dni_postoju)
        
        st.markdown("<br>"*5, unsafe_allow_html=True)
        is_admin = st.checkbox("LOGISTICS DETAILS")

    # --- OBLICZENIA ---
    waga_total = waga_input * cfg.get('WAGA_BUFOR', 1.2)
    
    if waga_total <= 1000: v_class = "BUS"
    elif waga_total <= 5500: v_class = "SOLO"
    else: v_class = "FTL"
        
    opcje = df_baza[(df_baza['Miasto'] == wybrane_miasto) & (df_baza['Typ_Pojazdu'] == v_class)].copy()
    
    if not opcje.empty:
        opcje['Suma_Calkowita'] = opcje['Eksport'] + opcje['Import'] + (dni_postoju * opcje['Postoj'])
        srednia_rynkowa = opcje['Suma_Calkowita'].mean()
        
        koszt_parkingu = dni_postoju * cfg.get('PARKING_DAY', 30)
        dodatki_extra = 0
        
        kraje_odprawy = ["Londyn", "Liverpool", "Manchester", "Bazylea", "Genewa", "Zurych"]
        if wybrane_miasto in kraje_odprawy:
            dodatki_extra += cfg.get('ATA_CARNET', 166)
            if wybrane_miasto in ["Londyn", "Liverpool", "Manchester"]:
                dodatki_extra += cfg.get('FERRY_BUS', 332) if v_class == "BUS" else cfg.get('FERRY_FTL_SOLO', 522)

        cena_final = srednia_rynkowa + koszt_parkingu + dodatki_extra

        # --- WIDOK GŁÓWNY ---
        st.markdown(f"### LOGISTICS VANTAGE / {wybrane_miasto.upper()}")
        
        # Grid z parametrami
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.markdown(f'<div class="metric-card"><div class="metric-label">Operational Weight</div><div class="metric-value">{waga_total:,.1f} kg</div></div>', unsafe_allow_html=True)
        with c2:
            st.markdown(f'<div class="metric-card"><div class="metric-label">Vehicle Type</div><div class="metric-value">{v_class}</div></div>', unsafe_allow_html=True)
        with c3:
            st.markdown(f'<div class="metric-card"><div class="metric-label">Event Days</div><div class="metric-value">{dni_postoju}</div></div>', unsafe_allow_html=True)
        with c4:
            st.markdown(f'<div class="metric-card"><div class="metric-label">Customs Zone</div><div class="metric-value">{"YES" if wybrane_miasto in kraje_odprawy else "NO"}</div></div>', unsafe_allow_html=True)

        # Główna karta ceny (Styl z obrazka)
        st.markdown(f"""
            <div class="price-container">
                <div class="price-label">Recommended Logistics Rate</div>
                <div class="price-value">€ {cena_final:,.2f} <span class="price-currency">net</span></div>
                <div class="detail-row">
                    <div class="detail-item">Route: <b>PL &harr; {wybrane_miasto}</b></div>
                    <div class="detail-item">Insurance: <b>Covered</b></div>
                    <div class="detail-item">Fuel & Tolls: <b>Included</b></div>
                </div>
            </div>
        """, unsafe_allow_html=True)

        if is_admin:
            with st.expander("ANALYTICAL BREAKDOWN"):
                col_a, col_b = st.columns(2)
                with col_a:
                    st.write("**Cost Factors:**")
                    st.write(f"• Market Average: €{srednia_rynkowa:,.2f}")
                    st.write(f"• Parking Allowance: €{koszt_parkingu:,.2f}")
                    st.write(f"• Surcharges (Ferry/ATA): €{dodatki_extra:,.2f}")
                with col_b:
                    st.write("**Database Comparison:**")
                    st.dataframe(opcje[['Przewoznik', 'Suma_Calkowita']].sort_values('Suma_Calkowita'))
    else:
        st.error(f"No pricing data found for {wybrane_miasto} / {v_class}")

st.markdown("<div style='text-align:right; font-size: 0.7rem; opacity: 0.5;'>SQM VANTAGE v5.2 | INTELLIGENCE INTERFACE</div>", unsafe_allow_html=True)
