import streamlit as st
import pandas as pd
from datetime import datetime
import re

# --- KONFIGURACJA POŁĄCZENIA Z ARKUSZEM ---
SHEET_ID = "1sYlXP6WVzPE09qfmydQYQNsjiZcDgRSJGyWoXfjmkDY"
SHEET_NAME_BAZA = "CENNIK_BAZA"
SHEET_NAME_OPLATY = "OPLATY_STALE"

URL_BAZA = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={SHEET_NAME_BAZA}"
URL_OPLATY = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={SHEET_NAME_OPLATY}"

st.set_page_config(page_title="SQM VANTAGE | Logistics Intelligence", layout="wide")

# --- CUSTOM CSS (Styl High-End Glassmorphism) ---
st.markdown("""
    <style>
    /* Tło i baza interfejsu */
    .stApp {
        background: radial-gradient(circle at 50% 10%, #1e293b 0%, #030508 100%);
        color: #e2e8f0;
    }

    /* Sidebar - Szklany blur */
    [data-testid="stSidebar"] {
        background-color: rgba(15, 23, 42, 0.7) !important;
        backdrop-filter: blur(15px);
        border-right: 1px solid rgba(255, 255, 255, 0.05);
    }

    /* Karty parametrów u góry */
    .metric-card {
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.1);
        padding: 15px 20px;
        border-radius: 12px;
        backdrop-filter: blur(10px);
        margin-bottom: 10px;
    }
    .metric-label { font-size: 0.7rem; color: #94a3b8; text-transform: uppercase; letter-spacing: 1.2px; font-weight: 600; }
    .metric-value { font-size: 1.2rem; font-weight: 700; color: #ffffff; margin-top: 5px; }

    /* Główny kontener wyniku z ceną */
    .price-container {
        background: rgba(255, 255, 255, 0.04);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 30px;
        padding: 45px;
        margin-top: 20px;
        backdrop-filter: blur(25px);
        box-shadow: 0 20px 50px rgba(0,0,0,0.4);
        position: relative;
    }
    
    /* Neonowy akcent SQM */
    .price-container::after {
        content: "";
        position: absolute;
        top: 45px; left: 0; width: 5px; height: 100px;
        background: #ed8936;
        border-radius: 0 5px 5px 0;
        box-shadow: 0 0 20px rgba(237, 137, 54, 0.6);
    }

    .price-label { font-size: 0.9rem; color: #ed8936; font-weight: 700; text-transform: uppercase; letter-spacing: 2px; }
    .price-value { font-size: 6rem; font-weight: 900; color: #ffffff; line-height: 0.9; margin: 20px 0; letter-spacing: -3px; }
    .price-currency { font-size: 1.5rem; font-weight: 400; color: #64748b; margin-left: 10px; }

    /* Sekcja składowych (Breakdown) */
    .components-title { 
        font-size: 0.8rem; color: #64748b; text-transform: uppercase; 
        margin-top: 40px; margin-bottom: 20px; font-weight: 800; letter-spacing: 1.5px;
        border-bottom: 1px solid rgba(255,255,255,0.05); padding-bottom: 10px;
    }

    .components-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
        gap: 12px;
    }

    .component-item {
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.05);
        padding: 14px 18px;
        border-radius: 12px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        transition: all 0.2s ease;
    }
    .component-item:hover {
        background: rgba(255, 255, 255, 0.06);
        border-color: rgba(255, 255, 255, 0.15);
        transform: translateY(-2px);
    }
    .comp-name { font-size: 0.85rem; color: #94a3b8; }
    .comp-price { font-size: 1rem; font-weight: 700; color: #f8fafc; }

    /* Ukrycie domyślnych elementów Streamlit */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

# --- FUNKCJE POBIERANIA I CZYSZCZENIA DANYCH ---
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
    
    # --- PANEL BOCZNY (INPUTY) ---
    with st.sidebar:
        st.image("https://www.sqm.pl/wp-content/themes/sqm/img/logo-sqm.png", width=160)
        st.markdown("<br>", unsafe_allow_html=True)
        
        miasta = sorted(df_baza['Miasto'].dropna().unique())
        wybrane_miasto = st.selectbox("MIASTO DOCELOWE", miasta)
        
        waga_input = st.number_input("WAGA PROJEKTU (kg)", min_value=0, value=500, step=100)
        
        st.markdown("---")
        data_zal = st.date_input("ZAŁADUNEK", datetime.now())
        data_roz = st.date_input("POWRÓT", datetime.now())
        dni_postoju = max(0, (data_roz - data_zal).days)
        
        st.markdown("<br>"*5, unsafe_allow_html=True)
        is_admin = st.checkbox("DEBUG LOGS (ADMIN)")

    # --- LOGIKA OBLICZEŃ ---
    # Automatyczne przeliczenie wagi projektowej na operacyjną (+20%)
    waga_total = waga_input * cfg.get('WAGA_BUFOR', 1.2)
    
    # Dobór pojazdu
    if waga_total <= 1000: v_class = "BUS"
    elif waga_total <= 5500: v_class = "SOLO"
    else: v_class = "FTL"
        
    # Filtracja bazy
    opcje = df_baza[(df_baza['Miasto'] == wybrane_miasto) & (df_baza['Typ_Pojazdu'] == v_class)].copy()
    
    if not opcje.empty:
        # Kalkulacja składowych (średnie rynkowe)
        avg_exp = opcje['Eksport'].mean()
        avg_imp = opcje['Import'].mean()
        avg_postoj_rate = opcje['Postoj'].mean()
        total_postoj_base = avg_postoj_rate * dni_postoju
        
        # Koszty stałe SQM (np. parking)
        parking_sqm = dni_postoju * cfg.get('PARKING_DAY', 30)
        
        # Opłaty specjalne (ATA, Promy, Mosty)
        ata_val, ferry_val = 0, 0
        kraje_odprawy = ["Londyn", "Liverpool", "Manchester", "Bazylea", "Genewa", "Zurych"]
        if wybrane_miasto in kraje_odprawy:
            ata_val = cfg.get('ATA_CARNET', 166)
            if wybrane_miasto in ["Londyn", "Liverpool", "Manchester"]:
                # Promy zależne od klasy pojazdu
                ferry_val = cfg.get('FERRY_BUS', 332) if v_class == "BUS" else cfg.get('FERRY_FTL_SOLO', 522)

        # WYNIK FINALNY
        cena_final = avg_exp + avg_imp + total_postoj_base + parking_sqm + ata_val + ferry_val

        # --- WIDOK GŁÓWNY (INTERFEJS) ---
        st.markdown(f"### LOGISTICS VANTAGE / {wybrane_miasto.upper()}")
        
        # Górne kafelki podsumowujące
        h1, h2, h3, h4 = st.columns(4)
        h1.markdown(f'<div class="metric-card"><div class="metric-label">Operational Weight</div><div class="metric-value">{waga_total:,.0f} kg</div></div>', unsafe_allow_html=True)
        h2.markdown(f'<div class="metric-card"><div class="metric-label">Selected Unit</div><div class="metric-value">{v_class}</div></div>', unsafe_allow_html=True)
        h3.markdown(f'<div class="metric-card"><div class="metric-label">Total Days</div><div class="metric-value">{dni_postoju}</div></div>', unsafe_allow_html=True)
        h4.markdown(f'<div class="metric-card"><div class="metric-label">Customs Zone</div><div class="metric-value">{"Required" if wybrane_miasto in kraje_odprawy else "None"}</div></div>', unsafe_allow_html=True)

        # Przygotowanie listy składowych
        components = [
            ("Eksport (Średnia)", avg_exp),
            ("Import (Średnia)", avg_imp),
            (f"Postój Przewoźnika ({dni_postoju} d)", total_postoj_base),
            (f"Parking SQM ({dni_postoju} d)", parking_sqm)
        ]
        if ata_val > 0: components.append(("Karnet ATA / Odprawa", ata_val))
        if ferry_val > 0: components.append(("Przeprawa / Promy / Mosty", ferry_val))

        # Renderowanie siatki składowych
        comp_html = "".join([f'<div class="component-item"><span class="comp-name">{n}</span><span class="comp-price">€ {p:,.2f}</span></div>' for n, p in components])

        # GŁÓWNA KARTA WYNIKU
        st.markdown(f"""
            <div class="price-container">
                <div class="price-label">Recommended Project Logistics Rate</div>
                <div class="price-value">€ {cena_final:,.2f} <span class="price-currency">netto</span></div>
                
                <div class="components-title">Rate Breakdown (All components included)</div>
                <div class="components-grid">
                    {comp_html}
                </div>
            </div>
        """, unsafe_allow_html=True)

        # Wgląd administracyjny
        if is_admin:
            with st.expander("🛠 LOGISTICS DATABASE LOGS", expanded=True):
                st.dataframe(opcje[['Przewoznik', 'Eksport', 'Import', 'Postoj', 'Suma_Calkowita']])
    else:
        st.error(f"BRAK DANYCH: Nie znaleziono stawek w arkuszu dla trasy {wybrane_miasto} i pojazdu {v_class}.")

st.markdown("<br><p style='text-align:right; opacity: 0.2; font-size: 0.7rem;'>SQM MULTIMEDIA SOLUTIONS | VANTAGE v5.5 | 2026</p>", unsafe_allow_html=True)
