import streamlit as st
import pandas as pd
from datetime import datetime

# --- KONFIGURACJA POŁĄCZENIA ---
SHEET_ID = "1sYlXP6WVzPE09qfmydQYQNsjiZcDgRSJGyWoXfjmkDY"
SHEET_NAME_BAZA = "CENNIK_BAZA"
SHEET_NAME_OPLATY = "OPLATY_STALE"

# Tworzenie linków do bezpośredniego pobierania CSV
URL_BAZA = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={SHEET_NAME_BAZA}"
URL_OPLATY = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={SHEET_NAME_OPLATY}"

# Ustawienia strony
st.set_page_config(page_title="SQM VANTAGE v5.1", layout="wide")

# --- STYLE CSS (Branding SQM) ---
st.markdown("""
    <style>
    .main { background-color: #030508; color: #e2e8f0; }
    .stNumberInput, .stSelectbox, .stDateInput { background-color: #1a202c !important; }
    .quote-container {
        background-color: #ffffff;
        color: #030508;
        padding: 40px;
        border-radius: 20px;
        border-left: 12px solid #ed8936;
        margin: 20px 0;
        box-shadow: 0 10px 25px rgba(0,0,0,0.5);
    }
    .metric-card {
        background: rgba(255,255,255,0.05);
        padding: 20px;
        border-radius: 12px;
        border: 1px solid rgba(255,255,255,0.1);
        text-align: center;
    }
    .admin-section {
        background-color: #1a202c;
        padding: 20px;
        border-radius: 10px;
        border: 1px dashed #4a5568;
        margin-top: 30px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- FUNKCJE POBIERANIA DANYCH ---
@st.cache_data(ttl=300)
def fetch_data():
    try:
        df_baza = pd.read_csv(URL_BAZA)
        df_oplaty = pd.read_csv(URL_OPLATY)
        # Czyszczenie nagłówków
        df_baza.columns = df_baza.columns.str.strip()
        df_oplaty.columns = df_oplaty.columns.str.strip()
        return df_baza, df_oplaty
    except Exception as e:
        st.error(f"Nie udało się pobrać danych. Upewnij się, że arkusz jest udostępniony dla 'każdej osoby z linkiem' i nazwy zakładek są poprawne. Błąd: {e}")
        return None, None

df_baza, df_oplaty = fetch_data()

if df_baza is not None and df_oplaty is not None:
    # Mapowanie konfiguracji
    cfg = dict(zip(df_oplaty['Parametr'], df_oplaty['Wartosc']))
    
    # --- PANEL BOCZNY ---
    st.sidebar.title("Kalkulator SQM")
    
    miasta = sorted(df_baza['Miasto'].dropna().unique())
    wybrane_miasto = st.sidebar.selectbox("Kierunek (Miasto)", miasta)
    
    waga_input = st.sidebar.number_input("Waga sprzętu netto (kg)", min_value=1, value=500, step=50)
    
    st.sidebar.markdown("---")
    data_zal = st.sidebar.date_input("Data załadunku", datetime.now())
    data_roz = st.sidebar.date_input("Data powrotu", datetime.now())
    
    dni_postoju = (data_roz - data_zal).days
    if dni_postoju < 0: dni_postoju = 0
    
    is_admin = st.sidebar.checkbox("Pokaż szczegóły logistyka")

    # --- OBLICZENIA ---
    mnoznik_wagi = cfg.get('WAGA_BUFOR', 1.2)
    waga_total = waga_input * mnoznik_wagi
    
    # Dobór pojazdu
    if waga_total <= 1000:
        v_class = "BUS"
    elif waga_total <= 5500:
        v_class = "SOLO"
    else:
        v_class = "FTL"
        
    # Filtracja bazy
    # Upewniamy się, że nazwy kolumn w CSV z Google Sheets są zgodne
    opcje = df_baza[(df_baza['Miasto'] == wybrane_miasto) & (df_baza['Typ_Pojazdu'] == v_class)].copy()
    
    if not opcje.empty:
        # Koszt całkowity każdego przewoźnika
        opcje['Suma_Calkowita'] = opcje['Eksport'] + opcje['Import'] + (dni_postoju * opcje['Postoj'])
        
        # Średnia rynkowa (zgodnie z instrukcją logistyka - nie jesteśmy stratni)
        srednia_rynkowa = opcje['Suma_Calkowita'].mean()
        
        # Dodatki ryczałtowe
        koszt_parkingu = dni_postoju * cfg.get('PARKING_DAY', 30)
        dodatki_extra = 0
        detale_extra = []
        
        kraje_odprawy = ["Londyn", "Liverpool", "Manchester", "Bazylea", "Genewa", "Zurych"]
        if wybrane_miasto in kraje_odprawy:
            ata = cfg.get('ATA_CARNET', 166)
            dodatki_extra += ata
            detale_extra.append(f"Odprawa celna (ATA): €{ata}")
            
            if wybrane_miasto in ["Londyn", "Liverpool", "Manchester"]:
                prom = cfg.get('FERRY_BUS', 332) if v_class == "BUS" else cfg.get('FERRY_FTL_SOLO', 522)
                dodatki_extra += prom
                detale_extra.append(f"Przeprawa promowa: €{prom}")

        cena_final = srednia_rynkowa + koszt_parkingu + dodatki_extra

        # --- WYŚWIETLANIE ---
        st.title(f"Wycena transportu: {wybrane_miasto}")
        
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown(f'<div class="metric-card">Waga z akcesoriami (+20%)<br><b style="font-size:24px;">{waga_total:.1f} kg</b></div>', unsafe_allow_html=True)
        with c2:
            st.markdown(f'<div class="metric-card">Zalecany pojazd<br><b style="font-size:24px;">{v_class}</b></div>', unsafe_allow_html=True)
        with c3:
            st.markdown(f'<div class="metric-card">Dni operacyjne<br><b style="font-size:24px;">{dni_postoju}</b></div>', unsafe_allow_html=True)

        st.markdown(f"""
            <div class="quote-container">
                <p style="margin:0; font-weight:700; color:#4a5568; text-transform:uppercase;">Kwota transportu do ujęcia w ofercie:</p>
                <h1 style="margin:0; font-size: 5.5rem; color:#030508;">€ {cena_final:,.2f} <span style="font-size:1.5rem;">netto</span></h1>
                <p style="margin-top:15px; color:#718096; border-top: 1px solid #eee; padding-top: 10px;">
                    Cena zawiera: transport w obie strony, obsługę postoju oraz wszystkie opłaty drogowe/celne.
                </p>
            </div>
        """, unsafe_allow_html=True)

        if is_admin:
            with st.expander("🛠 SZCZEGÓŁY DLA LOGISTYKA", expanded=True):
                st.markdown('<div class="admin-section">', unsafe_allow_html=True)
                col_a, col_b = st.columns(2)
                with col_a:
                    st.write("**Budowa ceny:**")
                    st.write(f"- Średni koszt bazy: €{srednia_rynkowa:,.2f}")
                    st.write(f"- Parking: €{koszt_parkingu:,.2f}")
                    for d in detale_extra:
                        st.write(f"- {d}")
                with col_b:
                    st.write("**Opcje przewoźników (uśrednione w wyniku):**")
                    st.table(opcje[['Przewoznik', 'Suma_Calkowita']].sort_values('Suma_Calkowita'))
                st.markdown('</div>', unsafe_allow_html=True)

    else:
        st.error(f"Brak danych dla miasta {wybrane_miasto} i pojazdu {v_class} w Twoim arkuszu Google.")

st.markdown("<br><p style='text-align:center; opacity:0.3;'>SQM Logistics Vantage v5.1 | System Wycen 2026</p>", unsafe_allow_html=True)
