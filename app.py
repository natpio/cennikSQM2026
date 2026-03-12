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

# --- CUSTOM CSS ---
st.markdown("""
    <style>
    .stApp { background: radial-gradient(circle at 50% 10%, #1e293b 0%, #030508 100%); color: #e2e8f0; }
    [data-testid="stSidebar"] { background-color: rgba(15, 23, 42, 0.7) !important; backdrop-filter: blur(15px); border-right: 1px solid rgba(255, 255, 255, 0.05); }

    .metric-card {
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.1);
        padding: 15px 20px; border-radius: 12px; backdrop-filter: blur(10px);
    }
    .metric-label { font-size: 0.7rem; color: #94a3b8; text-transform: uppercase; letter-spacing: 1.2px; font-weight: 600; }
    .metric-value { font-size: 1.2rem; font-weight: 700; color: #ffffff; margin-top: 5px; }

    .price-container {
        background: rgba(255, 255, 255, 0.04);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 30px; padding: 45px; margin-top: 20px;
        backdrop-filter: blur(25px); box-shadow: 0 20px 50px rgba(0,0,0,0.4); position: relative;
    }
    .price-container::after {
        content: ""; position: absolute; top: 45px; left: 0; width: 5px; height: 100px;
        background: #ed8936; border-radius: 0 5px 5px 0; box-shadow: 0 0 20px rgba(237, 137, 54, 0.6);
    }

    .price-label { font-size: 0.9rem; color: #ed8936; font-weight: 700; text-transform: uppercase; letter-spacing: 2px; }
    .price-value { font-size: 6rem; font-weight: 900; color: #ffffff; line-height: 0.9; margin: 20px 0; letter-spacing: -3px; }
    .price-currency { font-size: 1.5rem; font-weight: 400; color: #64748b; margin-left: 10px; }

    .components-title { 
        font-size: 0.8rem; color: #64748b; text-transform: uppercase; 
        margin-top: 40px; margin-bottom: 20px; font-weight: 800; letter-spacing: 1.5px;
        border-bottom: 1px solid rgba(255,255,255,0.05); padding-bottom: 10px;
    }
    .components-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 12px; }
    .component-item {
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.05);
        padding: 14px 18px; border-radius: 12px; display: flex; justify-content: space-between; align-items: center;
    }
    .comp-name { font-size: 0.85rem; color: #94a3b8; }
    .comp-price { font-size: 1rem; font-weight: 700; color: #f8fafc; }

    #MainMenu, footer, header {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

# --- DANE ---
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
        miasta = sorted(df_baza['Miasto'].dropna().unique())
        wybrane_miasto = st.selectbox("CEL", miasta)
        waga_input = st.number_input("WAGA NETTO (kg)", min_value=0, value=500)
        data_zal = st.date_input("ZAŁADUNEK", datetime.now())
        data_roz = st.date_input("POWRÓT", datetime.now())
        dni_postoju = max(0, (data_roz - data_zal).days)
        is_admin = st.checkbox("DEBUG")

    waga_total = waga_input * cfg.get('WAGA_BUFOR', 1.2)
    v_class = "BUS" if waga_total <= 1000 else "SOLO" if waga_total <= 5500 else "FTL"
    opcje = df_baza[(df_baza['Miasto'] == wybrane_miasto) & (df_baza['Typ_Pojazdu'] == v_class)].copy()
    
    if not opcje.empty:
        avg_exp = opcje['Eksport'].mean()
        avg_imp = opcje['Import'].mean()
        total_postoj_base = opcje['Postoj'].mean() * dni_postoju
        parking_sqm = dni_postoju * cfg.get('PARKING_DAY', 30)
        
        ata_val, ferry_val = 0, 0
        kraje_odprawy = ["Londyn", "Liverpool", "Manchester", "Bazylea", "Genewa", "Zurych"]
        if wybrane_miasto in kraje_odprawy:
            ata_val = cfg.get('ATA_CARNET', 166)
            if wybrane_miasto in ["Londyn", "Liverpool", "Manchester"]:
                ferry_val = cfg.get('FERRY_BUS', 332) if v_class == "BUS" else cfg.get('FERRY_FTL_SOLO', 522)

        cena_final = avg_exp + avg_imp + total_postoj_base + parking_sqm + ata_val + ferry_val

        # --- WIDOK GŁÓWNY ---
        st.markdown(f"### LOGISTICS VANTAGE / {wybrane_miasto.upper()}")
        
        c1, c2, c3, c4 = st.columns(4)
        c1.markdown(f'<div class="metric-card"><div class="metric-label">Weight (+20%)</div><div class="metric-value">{waga_total:,.0f} kg</div></div>', unsafe_allow_html=True)
        c2.markdown(f'<div class="metric-card"><div class="metric-label">Vehicle</div><div class="metric-value">{v_class}</div></div>', unsafe_allow_html=True)
        c3.markdown(f'<div class="metric-card"><div class="metric-label">Standby</div><div class="metric-value">{dni_postoju} days</div></div>', unsafe_allow_html=True)
        c4.markdown(f'<div class="metric-card"><div class="metric-label">Customs</div><div class="metric-value">{"YES" if wybrane_miasto in kraje_odprawy else "NO"}</div></div>', unsafe_allow_html=True)

        # KOMPONENTY (budujemy płaski HTML bez nowych linii)
        items = [
            ("Eksport (Średnia)", avg_exp),
            ("Import (Średnia)", avg_imp),
            (f"Postój Przewoźnika ({dni_postoju}d)", total_postoj_base),
            (f"Parking SQM ({dni_postoju}d)", parking_sqm)
        ]
        if ata_val > 0: items.append(("Karnet ATA / Odprawa", ata_val))
        if ferry_val > 0: items.append(("Promy / Mosty", ferry_val))

        comp_html = "".join([f'<div class="component-item"><span class="comp-name">{n}</span><span class="comp-price">€ {p:,.2f}</span></div>' for n, p in items])

        # FINALY RENDER (usuwamy znaki nowej linii)
        full_html = f"""
        <div class="price-container">
            <div class="price-label">Estimated Logistics Cost</div>
            <div class="price-value">€ {cena_final:,.2f} <span class="price-currency">netto</span></div>
            <div class="components-title">Price Breakdown (All components)</div>
            <div class="components-grid">{comp_html}</div>
        </div>
        """.replace("\n", " ").strip()

        st.markdown(full_html, unsafe_allow_html=True)

        if is_admin:
            st.dataframe(opcje)
    else:
        st.error(f"No data for {wybrane_miasto} / {v_class}")
