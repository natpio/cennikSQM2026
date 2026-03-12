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

# --- CUSTOM CSS (Glassmorphism + Components) ---
st.markdown("""
    <style>
    .stApp { background: radial-gradient(circle at 70% 20%, #1e293b 0%, #030508 100%); color: #e2e8f0; }
    [data-testid="stSidebar"] { background-color: rgba(15, 23, 42, 0.8); backdrop-filter: blur(10px); }

    /* Karta ceny */
    .price-container {
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.15);
        border-radius: 24px;
        padding: 40px;
        margin-top: 20px;
        backdrop-filter: blur(20px);
        position: relative;
    }
    .price-container::before { content: ""; position: absolute; top: 0; left: 0; width: 6px; height: 100%; background: #ed8936; }
    .price-label { font-size: 0.9rem; color: #ed8936; font-weight: 600; text-transform: uppercase; letter-spacing: 1px; }
    .price-value { font-size: 5rem; font-weight: 900; color: #ffffff; line-height: 1; margin: 10px 0; }
    
    /* Składowe (Chips) */
    .components-title { font-size: 0.8rem; color: #94a3b8; text-transform: uppercase; margin-top: 30px; margin-bottom: 15px; font-weight: 600; }
    .components-grid { display: flex; flex-wrap: wrap; gap: 10px; }
    .component-tag {
        background: rgba(255, 255, 255, 0.07);
        border: 1px solid rgba(255, 255, 255, 0.1);
        padding: 8px 16px;
        border-radius: 10px;
        font-size: 0.85rem;
        color: #cbd5e1;
        display: flex;
        justify-content: space-between;
        min-width: 180px;
    }
    .component-tag b { color: #f8fafc; margin-left: 10px; }

    /* Metric Cards */
    .metric-card {
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.1);
        padding: 20px; border-radius: 15px; text-align: left;
    }
    .metric-label { font-size: 0.7rem; color: #94a3b8; text-transform: uppercase; }
    .metric-value { font-size: 1.3rem; font-weight: 700; color: #f8fafc; }
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
        st.error(f"Error: {e}"); return None, None

df_baza, df_oplaty = fetch_data()

if df_baza is not None and df_oplaty is not None:
    cfg = dict(zip(df_oplaty['Parametr'], df_oplaty['Wartosc']))
    
    with st.sidebar:
        st.image("https://www.sqm.pl/wp-content/themes/sqm/img/logo-sqm.png", width=160)
        st.markdown("<br>", unsafe_allow_html=True)
        miasta = sorted(df_baza['Miasto'].dropna().unique())
        wybrane_miasto = st.selectbox("DESTINATION", miasta)
        waga_input = st.number_input("PROJECT WEIGHT (kg)", min_value=0, value=500, step=100)
        st.markdown("---")
        data_zal = st.date_input("LOAD", datetime.now())
        data_roz = st.date_input("RETURN", datetime.now())
        dni_postoju = max(0, (data_roz - data_zal).days)
        is_admin = st.checkbox("DEBUG VIEW")

    # --- LOGIKA ---
    waga_total = waga_input * cfg.get('WAGA_BUFOR', 1.2)
    if waga_total <= 1000: v_class = "BUS"
    elif waga_total <= 5500: v_class = "SOLO"
    else: v_class = "FTL"
        
    opcje = df_baza[(df_baza['Miasto'] == wybrane_miasto) & (df_baza['Typ_Pojazdu'] == v_class)].copy()
    
    if not opcje.empty:
        # Składowe rynkowe (średnie)
        avg_exp = opcje['Eksport'].mean()
        avg_imp = opcje['Import'].mean()
        avg_postoj_rate = opcje['Postoj'].mean()
        total_postoj_base = avg_postoj_rate * dni_postoju
        
        # Koszty dodatkowe
        parking_sqm = dni_postoju * cfg.get('PARKING_DAY', 30)
        
        ata_val = 0
        ferry_val = 0
        kraje_odprawy = ["Londyn", "Liverpool", "Manchester", "Bazylea", "Genewa", "Zurych"]
        if wybrane_miasto in kraje_odprawy:
            ata_val = cfg.get('ATA_CARNET', 166)
            if wybrane_miasto in ["Londyn", "Liverpool", "Manchester"]:
                ferry_val = cfg.get('FERRY_BUS', 332) if v_class == "BUS" else cfg.get('FERRY_FTL_SOLO', 522)

        cena_final = avg_exp + avg_imp + total_postoj_base + parking_sqm + ata_val + ferry_val

        # --- INTERFEJS ---
        st.markdown(f"### LOGISTICS VANTAGE / {wybrane_miasto.upper()}")
        
        cols = st.columns(4)
        cols[0].markdown(f'<div class="metric-card"><div class="metric-label">Operational Weight</div><div class="metric-value">{waga_total:,.0f} kg</div></div>', unsafe_allow_html=True)
        cols[1].markdown(f'<div class="metric-card"><div class="metric-label">Vehicle</div><div class="metric-value">{v_class}</div></div>', unsafe_allow_html=True)
        cols[2].markdown(f'<div class="metric-card"><div class="metric-label">Event Days</div><div class="metric-value">{dni_postoju}</div></div>', unsafe_allow_html=True)
        cols[3].markdown(f'<div class="metric-card"><div class="metric-label">Route Type</div><div class="metric-value">{"Non-EU" if wybrane_miasto in kraje_odprawy else "EU Standard"}</div></div>', unsafe_allow_html=True)

        # KARTA WYNIKU
        tags_html = f"""
            <div class="component-tag">Export Base <b>€{avg_exp:,.2f}</b></div>
            <div class="component-tag">Import Base <b>€{avg_imp:,.2f}</b></div>
            <div class="component-tag">Operator Standby <b>€{total_postoj_base:,.2f}</b></div>
            <div class="component-tag">SQM Parking Fee <b>€{parking_sqm:,.2f}</b></div>
        """
        if ata_val > 0: tags_html += f'<div class="component-tag">ATA Carnet / Customs <b>€{ata_val:,.2f}</b></div>'
        if ferry_val > 0: tags_html += f'<div class="component-tag">Ferry / Eurotunnel <b>€{ferry_val:,.2f}</b></div>'

        st.markdown(f"""
            <div class="price-container">
                <div class="price-label">Estimated Project Rate</div>
                <div class="price-value">€ {cena_final:,.2f}</div>
                
                <div class="components-title">Rate Breakdown (Average Market Components)</div>
                <div class="components-grid">
                    {tags_html}
                </div>
            </div>
        """, unsafe_allow_html=True)

        if is_admin:
            st.dataframe(opcje)
    else:
        st.error(f"No pricing for {wybrane_miasto} as {v_class}")
