import streamlit as st
import pandas as pd
from datetime import datetime
import re

# --- KONFIGURACJA POŁĄCZENIA ---
SHEET_ID = "1sYlXP6WVzPE09qfmydQYQNsjiZcDgRSJGyWoXfjmkDY"
SHEET_NAME_BAZA = "CENNIK_BAZA"
SHEET_NAME_OPLATY = "OPLATY_STALE"

URL_BAZA = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={SHEET_NAME_BAZA}"
URL_OPLATY = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={SHEET_NAME_OPLATY}"

st.set_page_config(page_title="SQM VANTAGE | Logistics Intelligence", layout="wide")

# --- CUSTOM CSS (Styl nowoczesny Dashboard + Składowe) ---
st.markdown("""
    <style>
    /* Tło i baza */
    .stApp { background: radial-gradient(circle at 70% 20%, #1e293b 0%, #030508 100%); color: #e2e8f0; }
    [data-testid="stSidebar"] { background-color: rgba(15, 23, 42, 0.8); backdrop-filter: blur(10px); border-right: 1px solid rgba(255, 255, 255, 0.1); }

    /* Główne karty parametrów */
    .metric-card {
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.1);
        padding: 20px;
        border-radius: 15px;
        backdrop-filter: blur(5px);
    }
    .metric-label { font-size: 0.75rem; color: #94a3b8; text-transform: uppercase; letter-spacing: 1px; }
    .metric-value { font-size: 1.4rem; font-weight: 700; color: #f8fafc; }

    /* Kontener ceny głównej */
    .price-container {
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.15);
        border-radius: 24px;
        padding: 40px;
        margin-top: 25px;
        backdrop-filter: blur(20px);
        position: relative;
    }
    .price-container::before { content: ""; position: absolute; top: 0; left: 0; width: 6px; height: 100%; background: #ed8936; }
    .price-label { font-size: 1rem; color: #ed8936; font-weight: 600; text-transform: uppercase; }
    .price-value { font-size: 5.5rem; font-weight: 900; color: #ffffff; line-height: 1; margin: 15px 0; }
    
    /* Składowe (Kafelki) */
    .components-title { font-size: 0.9rem; color: #94a3b8; text-transform: uppercase; margin-top: 35px; margin-bottom: 15px; font-weight: 600; letter-spacing: 1px; }
    .components-grid { display: flex; flex-wrap: wrap; gap: 12px; }
    .component-tag {
        background: rgba(255, 255, 255, 0.08);
        border: 1px solid rgba(255, 255, 255, 0.1);
        padding: 12px 20px;
        border-radius: 12px;
        font-size: 0.9rem;
        color: #cbd5e1;
        display: flex;
        align-items: center;
        min-width: 220px;
        justify-content: space-between;
    }
    .component-tag b { color: #ffffff; font-size: 1rem; margin-left: 15px; }
    </style>
    """, unsafe_allow_html=True)

# --- SILNIK DANYCH ---
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
        st.error(f"Data Connection Error: {e}"); return None, None

df_baza, df_oplaty = fetch_data()

if df_baza is not None and df_oplaty is not None:
    cfg = dict(zip(df_oplaty['Parametr'], df_oplaty['Wartosc']))
    
    # --- PANEL BOCZNY (INPUTY) ---
    with st.sidebar:
        st.image("https://www.sqm.pl/wp-content/themes/sqm/img/logo-sqm.png", width=160)
        st.markdown("<br>", unsafe_allow_html=True)
        
        miasta = sorted(df_baza['Miasto'].dropna().unique())
        wybrane_miasto = st.selectbox("DESTINATION / MIASTO", miasta)
        
        waga_input = st.number_input("MAIN PROJECT WEIGHT (kg)", min_value=0, value=500, step=100)
        
        st.markdown("---")
        data_zal = st.date_input("LOADING DATE", datetime.now())
        data_roz = st.date_input("RETURN DATE", datetime.now())
        
        dni_postoju = max(0, (data_roz - data_zal).days)
        
        st.markdown("<br>"*5, unsafe_allow_html=True)
        is_admin = st.checkbox("SHOW LOGISTICS LOGS")

    # --- LOGIKA OBLICZEŃ ---
    waga_total = waga_input * cfg.get('WAGA_BUFOR', 1.2)
    
    # Dobór pojazdu
    if waga_total <= 1000: v_class = "BUS"
    elif waga_total <= 5500: v_class = "SOLO"
    else: v_class = "FTL"
        
    opcje = df_baza[(df_baza['Miasto'] == wybrane_miasto) & (df_baza['Typ_Pojazdu'] == v_class)].copy()
    
    if not opcje.empty:
        # 1. Średnie rynkowe z bazy
        avg_exp = opcje['Eksport'].mean()
        avg_imp = opcje['Import'].mean()
        avg_postoj_rate = opcje['Postoj'].mean()
        total_postoj_base = avg_postoj_rate * dni_postoju
        
        # 2. Koszty stałe SQM
        parking_sqm = dni_postoju * cfg.get('PARKING_DAY', 30)
        
        # 3. Opłaty dodatkowe (Odprawy/Promy)
        ata_val = 0
        ferry_val = 0
        kraje_odprawy = ["Londyn", "Liverpool", "Manchester", "Bazylea", "Genewa", "Zurych"]
        
        if wybrane_miasto in kraje_odprawy:
            ata_val = cfg.get('ATA_CARNET', 166)
            if wybrane_miasto in ["Londyn", "Liverpool", "Manchester"]:
                ferry_val = cfg.get('FERRY_BUS', 332) if v_class == "BUS" else cfg.get('FERRY_FTL_SOLO', 522)

        # SUMA FINALNA
        cena_final = avg_exp + avg_imp + total_postoj_base + parking_sqm + ata_val + ferry_val

        # --- PREZENTACJA WYNIKÓW ---
        st.markdown(f"### LOGISTICS VANTAGE / {wybrane_miasto.upper()}")
        
        # Górne wskaźniki
        c1, c2, c3, c4 = st.columns(4)
        c1.markdown(f'<div class="metric-card"><div class="metric-label">Project Weight (+20%)</div><div class="metric-value">{waga_total:,.0f} kg</div></div>', unsafe_allow_html=True)
        c2.markdown(f'<div class="metric-card"><div class="metric-label">Selected Vehicle</div><div class="metric-value">{v_class}</div></div>', unsafe_allow_html=True)
        c3.markdown(f'<div class="metric-card"><div class="metric-label">Days on Site</div><div class="metric-value">{dni_postoju}</div></div>', unsafe_allow_html=True)
        c4.markdown(f'<div class="metric-card"><div class="metric-label">Customs Required</div><div class="metric-value">{"YES (ATA)" if wybrane_miasto in kraje_odprawy else "NO"}</div></div>', unsafe_allow_html=True)

        # Budowa listy składowych (HTML Chips)
        tags_html = f"""
            <div class="component-tag">Eksport (Średnia) <b>€{avg_exp:,.2f}</b></div>
            <div class="component-tag">Import (Średnia) <b>€{avg_imp:,.2f}</b></div>
            <div class="component-tag">Postój Przewoźnika <b>€{total_postoj_base:,.2f}</b></div>
            <div class="component-tag">Parking SQM <b>€{parking_sqm:,.2f}</b></div>
        """
        if ata_val > 0:
            tags_html += f'<div class="component-tag">Karnet ATA / Odprawa <b>€{ata_val:,.2f}</b></div>'
        if ferry_val > 0:
            tags_html += f'<div class="component-tag">Promy / Eurotunel <b>€{ferry_val:,.2f}</b></div>'

        # KARTA GŁÓWNA
        st.markdown(f"""
            <div class="price-container">
                <div class="price-label">Recommended Project Rate (Netto)</div>
                <div class="price-value">€ {cena_final:,.2f}</div>
                
                <div class="components-title">Pełne zestawienie składowych ceny:</div>
                <div class="components-grid">
                    {tags_html}
                </div>
            </div>
        """, unsafe_allow_html=True)

        # PANEL ADMINA
        if is_admin:
            with st.expander("🛠 LOGISTICS DATABASE LOGS"):
                st.write(f"Kalkulacja dla {v_class} na trasie PL - {wybrane_miasto}")
                st.dataframe(opcje[['Przewoznik', 'Eksport', 'Import', 'Postoj', 'Suma_Calkowita']].sort_values('Suma_Calkowita'))
    else:
        st.error(f"BRAK DANYCH: Nie znaleziono stawek dla {wybrane_miasto} i pojazdu {v_class}. Uzupełnij arkusz Google.")

st.markdown("<br><p style='text-align:right; opacity: 0.3; font-size: 0.8rem;'>SQM VANTAGE v5.3 | 2026 Logistics Intelligence</p>", unsafe_allow_html=True)
