import streamlit as st
import pandas as pd
from datetime import datetime
import re

# --- KONFIGURACJA POŁĄCZENIA ---
SHEET_ID = "1sYlXP6WVzPE09qfmydQYQNsjiZcDgRSJGyWoXfjmkDY"
SHEET_NAME_BAZA = "CENNIK_BAZA"
SHEET_NAME_OPLATY = "OPLATY_STALE"

# Linki do pobierania CSV z Google Sheets
URL_BAZA = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={SHEET_NAME_BAZA}"
URL_OPLATY = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={SHEET_NAME_OPLATY}"

# Ustawienia strony Streamlit
st.set_page_config(page_title="SQM VANTAGE v5.1", layout="wide")

# --- STYLE CSS (Branding SQM Multimedia Solutions) ---
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

# --- FUNKCJE POBIERANIA I CZYSZCZENIA DANYCH ---
@st.cache_data(ttl=300)
def fetch_data():
    try:
        # Pobieranie bazy cenowej
        df_baza = pd.read_csv(URL_BAZA)
        df_baza.columns = df_baza.columns.str.strip()
        
        # Funkcja czyszcząca liczby (usuwa przecinki, spacje, waluty)
        def clean_numeric(value):
            if pd.isna(value): return 0.0
            s = str(value).replace(',', '.').strip()
            s = re.sub(r'[^\d.]', '', s)
            try:
                return float(s)
            except:
                return 0.0

        # Czyszczenie kluczowych kolumn finansowych
        for col in ['Eksport', 'Import', 'Postoj']:
            if col in df_baza.columns:
                df_baza[col] = df_baza[col].apply(clean_numeric)

        # Pobieranie opłat stałych
        df_oplaty = pd.read_csv(URL_OPLATY)
        df_oplaty.columns = df_oplaty.columns.str.strip()
        df_oplaty['Wartosc'] = df_oplaty['Wartosc'].apply(clean_numeric)
        
        return df_baza, df_oplaty
    except Exception as e:
        st.error(f"Błąd połączenia z bazą danych: {e}")
        return None, None

df_baza, df_oplaty = fetch_data()

if df_baza is not None and df_oplaty is not None:
    # Mapowanie konfiguracji na słownik
    cfg = dict(zip(df_oplaty['Parametr'], df_oplaty['Wartosc']))
    
    # --- PANEL BOCZNY (INPUTY) ---
    st.sidebar.image("https://www.sqm.pl/wp-content/themes/sqm/img/logo-sqm.png", width=180)
    st.sidebar.title("Kalkulator Transportu")
    
    miasta = sorted(df_baza['Miasto'].dropna().unique())
    wybrane_miasto = st.sidebar.selectbox("Miasto docelowe", miasta)
    
    waga_input = st.sidebar.number_input("Waga sprzętu netto (kg)", min_value=1, value=500, step=100)
    
    st.sidebar.markdown("---")
    data_zal = st.sidebar.date_input("Data załadunku", datetime.now())
    data_roz = st.sidebar.date_input("Data powrotu (rozładunek PL)", datetime.now())
    
    dni_postoju = (data_roz - data_zal).days
    if dni_postoju < 0: dni_postoju = 0
    
    is_admin = st.sidebar.checkbox("Pokaż szczegóły logistyka")

    # --- LOGIKA OBLICZEŃ ---
    
    # 1. Obliczanie wagi z akcesoriami (+20% zgodnie z WAGA_BUFOR)
    mnoznik_wagi = cfg.get('WAGA_BUFOR', 1.2)
    waga_total = waga_input * mnoznik_wagi
    
    # 2. Automatyczny dobór najmniejszego pojazdu
    if waga_total <= 1000:
        v_class = "BUS"
    elif waga_total <= 5500:
        v_class = "SOLO"
    else:
        v_class = "FTL"
        
    # 3. Filtrowanie bazy dla wybranej trasy i pojazdu
    opcje = df_baza[(df_baza['Miasto'] == wybrane_miasto) & (df_baza['Typ_Pojazdu'] == v_class)].copy()
    
    if not opcje.empty:
        # Kalkulacja kosztu całkowitego dla każdego przewoźnika
        opcje['Suma_Calkowita'] = opcje['Eksport'] + opcje['Import'] + (dni_postoju * opcje['Postoj'])
        
        # OBLICZANIE ŚREDNIEJ RYNKOWEJ (Market Average)
        srednia_rynkowa = opcje['Suma_Calkowita'].mean()
        
        # 4. Koszty dodatkowe
        koszt_parkingu = dni_postoju * cfg.get('PARKING_DAY', 30)
        dodatki_extra = 0
        detale_extra = []
        
        # Obsługa stref specjalnych (UK / CH)
        kraje_odprawy = ["Londyn", "Liverpool", "Manchester", "Bazylea", "Genewa", "Zurych"]
        if wybrane_miasto in kraje_odprawy:
            ata = cfg.get('ATA_CARNET', 166)
            dodatki_extra += ata
            detale_extra.append(f"Odprawa / Karnet ATA: €{ata}")
            
            if wybrane_miasto in ["Londyn", "Liverpool", "Manchester"]:
                prom = cfg.get('FERRY_BUS', 332) if v_class == "BUS" else cfg.get('FERRY_FTL_SOLO', 522)
                dodatki_extra += prom
                detale_extra.append(f"Przeprawa promowa: €{prom}")

        # WYNIK FINALNY
        cena_final = srednia_rynkowa + koszt_parkingu + dodatki_extra

        # --- PREZENTACJA DLA HANDLOWCA ---
        st.title(f"Logistyka: PL ↔ {wybrane_miasto}")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(f'<div class="metric-card">Waga z akcesoriami (+20%)<br><b style="font-size:24px;">{waga_total:.1f} kg</b></div>', unsafe_allow_html=True)
        with col2:
            st.markdown(f'<div class="metric-card">Typ dobranej jednostki<br><b style="font-size:24px;">{v_class}</b></div>', unsafe_allow_html=True)
        with col3:
            st.markdown(f'<div class="metric-card">Dni operacyjne (postój)<br><b style="font-size:24px;">{dni_postoju} dni</b></div>', unsafe_allow_html=True)

        st.markdown(f"""
            <div class="quote-container">
                <p style="margin:0; font-weight:700; color:#4a5568; text-transform:uppercase; letter-spacing:1px;">Kwota transportu do ujęcia w ofercie:</p>
                <h1 style="margin:0; font-size: 5.5rem; color:#030508;">€ {cena_final:,.2f} <span style="font-size:1.5rem;">netto</span></h1>
                <p style="margin-top:15px; color:#718096; border-top: 1px solid #eee; padding-top: 10px; font-style: italic;">
                    Stawka ryczałtowa. Zawiera koszty paliwa, opłaty drogowe, przeprawy oraz obsługę logistyczną postoju.
                </p>
            </div>
        """, unsafe_allow_html=True)

        # --- WIDOK LOGISTYKA (ADMIN) ---
        if is_admin:
            with st.expander("🛠 SZCZEGÓŁY ANALITYCZNE (WIDOK LOGISTYKA)", expanded=True):
                st.markdown('<div class="admin-section">', unsafe_allow_html=True)
                ca, cb = st.columns(2)
                with ca:
                    st.write("**Składowe ceny rynkowej:**")
                    st.write(f"- Średnia z bazy przewoźników: €{srednia_rynkowa:,.2f}")
                    st.write(f"- Parking (SQM Standard): €{koszt_parkingu:,.2f}")
                    for d in detale_extra:
                        st.write(f"- {d}")
                with cb:
                    st.write("**Dostępni przewoźnicy dla tej trasy:**")
                    # Pokazujemy realne koszty z bazy dla porównania
                    st.dataframe(opcje[['Przewoznik', 'Suma_Calkowita']].sort_values('Suma_Calkowita'))
                
                # Szybka ocena potencjalnego zysku na flocie własnej
                sqm_only = opcje[opcje['Przewoznik'].str.contains("SQM", case=False, na=False)]
                if not sqm_only.empty:
                    koszt_wlasny = sqm_only['Suma_Calkowita'].min() + koszt_parkingu + dodatki_extra
                    st.success(f"💡 Jeśli pojedzie flota własna SQM, koszt wyniesie ok. €{koszt_wlasny:,.2f} (Zysk operacyjny: €{cena_final - koszt_wlasny:,.2f})")
                st.markdown('</div>', unsafe_allow_html=True)

    else:
        st.error(f"Brak danych w arkuszu dla miasta {wybrane_miasto} i pojazdu {v_class}. Uzupełnij zakładkę CENNIK_BAZA.")

else:
    st.warning("Nie udało się załadować danych. Sprawdź ustawienia udostępniania arkusza Google.")

st.markdown("<br><p style='text-align:center; opacity:0.3;'>SQM Multimedia Solutions | Vantage Intelligence v5.1</p>", unsafe_allow_html=True)
