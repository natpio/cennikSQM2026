import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import re
import hashlib
import extra_streamlit_components as stx

# --- KONFIGURACJA ZASOBÓW ---
SHEET_ID = "1sYlXP6WVzPE09qfmydQYQNsjiZcDgRSJGyWoXfjmkDY"
URL_BAZA = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=CENNIK_BAZA"
URL_OPLATY = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=OPLATY_STALE"
URL_USERS = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=USERS"

st.set_page_config(page_title="SQM VANTAGE | Logistics Intelligence", layout="wide", initial_sidebar_state="expanded")

# --- FUNKCJE BEZPIECZEŃSTWA ---
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def get_cookie_manager():
    return stx.CookieManager()

cookie_manager = get_cookie_manager()

@st.cache_data(ttl=60)
def fetch_user_database():
    try:
        df = pd.read_csv(URL_USERS)
        df.columns = df.columns.str.strip()
        return dict(zip(df['username'].astype(str), df['password'].astype(str)))
    except Exception as e:
        # Fallback w razie problemów z arkuszem (login: admin, hasło: SQM2026!)
        return {"admin": "7990494490f237f37435f3089d38c1a6007e0c8b055371190458df8d03f0b07b"}

user_db = fetch_user_database()

# Logika autoryzacji sesji
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

# Sprawdzenie ciasteczka (Zapamiętaj mnie przez 30 dni)
saved_session = cookie_manager.get(cookie="sqm_vantage_v6")
if saved_session in user_db:
    st.session_state.authenticated = True
    st.session_state.current_user = saved_session

# --- PANEL LOGOWANIA ---
if not st.session_state.authenticated:
    st.markdown("""
        <style>
        .stApp { background: #030508; color: white; }
        .login-container {
            max-width: 450px; margin: 100px auto; padding: 40px;
            background: rgba(255, 255, 255, 0.03);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 20px; backdrop-filter: blur(10px);
            text-align: center;
        }
        </style>
    """, unsafe_allow_html=True)
    
    with st.container():
        st.markdown('<div class="login-container">', unsafe_allow_html=True)
        st.image("https://www.sqm.pl/wp-content/themes/sqm/img/logo-sqm.png", width=200)
        st.title("SQM VANTAGE")
        st.subheader("System Logistyczny v6.0")
        
        user_input = st.text_input("Użytkownik", key="l_user")
        pass_input = st.text_input("Hasło", type="password", key="l_pass")
        
        if st.button("ZALOGUJ SIĘ", use_container_width=True):
            hashed_input = hash_password(pass_input)
            if user_input in user_db and user_db[user_input] == hashed_input:
                st.session_state.authenticated = True
                st.session_state.current_user = user_input
                # Ustawienie ciasteczka na 30 dni
                cookie_manager.set("sqm_vantage_v6", user_input, expires_at=datetime.now() + timedelta(days=30))
                st.rerun()
            else:
                st.error("Nieprawidłowe dane logowania. Sprawdź hasło w Google Sheets.")
        st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

# --- STYLIZACJA GŁÓWNA (CSS) ---
st.markdown("""
    <style>
    .stApp { background: radial-gradient(circle at 50% 10%, #1e293b 0%, #030508 100%); color: #e2e8f0; }
    
    /* Szklane kafelki główne */
    .metric-card {
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.1);
        padding: 20px; border-radius: 15px; backdrop-filter: blur(10px);
        text-align: center;
    }
    .metric-label { font-size: 0.75rem; color: #94a3b8; text-transform: uppercase; letter-spacing: 1.5px; font-weight: 600; }
    .metric-value { font-size: 1.4rem; font-weight: 700; color: #ffffff; margin-top: 8px; }

    /* Kontener ceny głównej */
    .price-container {
        background: rgba(255, 255, 255, 0.04);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 30px; padding: 50px; margin-top: 30px;
        backdrop-filter: blur(25px); box-shadow: 0 25px 50px rgba(0,0,0,0.5);
        position: relative; overflow: hidden;
    }
    .price-container::before {
        content: ""; position: absolute; top: 0; left: 0; width: 8px; height: 100%;
        background: linear-gradient(to bottom, #ed8936, #f6ad55);
    }

    .price-label { font-size: 1rem; color: #ed8936; font-weight: 700; text-transform: uppercase; letter-spacing: 3px; }
    .price-value { font-size: 6.5rem; font-weight: 900; color: #ffffff; line-height: 0.85; margin: 25px 0; letter-spacing: -4px; }
    .price-currency { font-size: 1.8rem; font-weight: 300; color: #64748b; margin-left: 15px; }

    /* Siatka składowych */
    .components-title { 
        font-size: 0.85rem; color: #64748b; text-transform: uppercase; 
        margin-top: 40px; margin-bottom: 20px; font-weight: 800; letter-spacing: 2px;
        border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 10px;
    }
    .components-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 15px; }
    .component-item {
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.05);
        padding: 16px 20px; border-radius: 12px; display: flex; justify-content: space-between; align-items: center;
    }
    .comp-name { font-size: 0.9rem; color: #94a3b8; }
    .comp-price { font-size: 1.1rem; font-weight: 700; color: #f8fafc; }

    /* Ukrycie elementów Streamlit */
    #MainMenu, footer, header { visibility: hidden; }
    </style>
    """, unsafe_allow_html=True)

# --- ŁADOWANIE DANYCH LOGISTYCZNYCH ---
@st.cache_data(ttl=300)
def load_logistics_data():
    try:
        baza = pd.read_csv(URL_BAZA)
        oplaty = pd.read_csv(URL_OPLATY)
        baza.columns = baza.columns.str.strip()
        oplaty.columns = oplaty.columns.str.strip()
        
        def clean_val(x):
            if pd.isna(x): return 0.0
            s = str(x).replace(',', '.').strip()
            s = re.sub(r'[^\d.]', '', s)
            return float(s) if s else 0.0
            
        for col in ['Eksport', 'Import', 'Postoj']:
            if col in baza.columns:
                baza[col] = baza[col].apply(clean_val)
        oplaty['Wartosc'] = oplaty['Wartosc'].apply(clean_val)
        return baza, oplaty
    except Exception as e:
        st.error(f"Błąd ładowania danych: {e}")
        return None, None

df_baza, df_oplaty = load_logistics_data()

if df_baza is not None:
    # Parametry stałe
    cfg = dict(zip(df_oplaty['Parametr'], df_oplaty['Wartosc']))
    
    # --- SIDEBAR / FILTRY ---
    with st.sidebar:
        st.image("https://www.sqm.pl/wp-content/themes/sqm/img/logo-sqm.png", width=150)
        st.info(f"Zalogowany jako: {st.session_state.current_user}")
        
        st.markdown("### 🛠 PARAMETRY TRANSPORTU")
        lista_miast = sorted(df_baza['Miasto'].dropna().unique())
        wybrane_miasto = st.selectbox("MIASTO DOCELOWE", lista_miast)
        
        waga_brutto = st.number_input("WAGA SPRZĘTU (kg)", min_value=1, value=500, step=100)
        
        col_d1, col_d2 = st.columns(2)
        with col_d1:
            data_start = st.date_input("ZAŁADUNEK", datetime.now())
        with col_d2:
            data_end = st.date_input("POWRÓT", datetime.now() + timedelta(days=3))
            
        dni_postoju = max(0, (data_end - data_start).days)
        
        st.markdown("---")
        if st.button("WYLOGUJ Z SYSTEMU"):
            cookie_manager.delete("sqm_vantage_v6")
            st.session_state.authenticated = False
            st.rerun()

    # --- LOGIKA OBLICZEŃ ---
    # 1. Waga operacyjna z buforem bezpieczeństwa
    waga_operacyjna = waga_brutto * cfg.get('WAGA_BUFOR', 1.2)
    
    # 2. Dobór typu pojazdu
    if waga_operacyjna <= 1000:
        typ_pojazdu = "BUS"
    elif waga_operacyjna <= 5500:
        typ_pojazdu = "SOLO"
    else:
        typ_pojazdu = "FTL"
        
    # 3. Pobranie stawek z bazy
    opcje = df_baza[(df_baza['Miasto'] == wybrane_miasto) & (df_baza['Typ_Pojazdu'] == typ_pojazdu)]
    
    if not opcje.empty:
        # Średnie stawki
        stawka_eksport = opcje['Eksport'].mean()
        stawka_import = opcje['Import'].mean()
        stawka_postoj_dzien = opcje['Postoj'].mean()
        
        # Obliczenia dodatkowe
        koszt_postoju = stawka_postoj_dzien * dni_postoju
        koszt_parkingu = dni_postoju * cfg.get('PARKING_DAY', 30)
        
        # Odprawy celne i przeprawy
        koszt_ata = 0
        koszt_przeprawy = 0
        kraje_celne = ["Londyn", "Liverpool", "Manchester", "Bazylea", "Genewa", "Zurych"]
        
        if wybrane_miasto in kraje_celne:
            koszt_ata = cfg.get('ATA_CARNET', 166)
            if any(uk in wybrane_miasto for uk in ["Londyn", "Liverpool", "Manchester"]):
                koszt_przeprawy = cfg.get('FERRY_BUS', 332) if typ_pojazdu == "BUS" else cfg.get('FERRY_FTL_SOLO', 522)
        
        suma_netto = stawka_eksport + stawka_import + koszt_postoju + koszt_parkingu + koszt_ata + koszt_przeprawy

        # --- PREZENTACJA WYNIKÓW ---
        st.markdown(f"## 📊 RAPORT LOGISTYCZNY: {wybrane_miasto.upper()}")
        
        # Górne wskaźniki
        m1, m2, m3, m4 = st.columns(4)
        with m1:
            st.markdown(f'<div class="metric-card"><div class="metric-label">Waga Operacyjna</div><div class="metric-value">{waga_operacyjna:,.0f} kg</div></div>', unsafe_allow_html=True)
        with m2:
            st.markdown(f'<div class="metric-card"><div class="metric-label">Pojazd</div><div class="metric-value">{typ_pojazdu}</div></div>', unsafe_allow_html=True)
        with m3:
            st.markdown(f'<div class="metric-card"><div class="metric-label">Czas trwania</div><div class="metric-value">{dni_postoju} dni</div></div>', unsafe_allow_html=True)
        with m4:
            status_cło = "WYMAGANE" if wybrane_miasto in kraje_celne else "NIE DOTYCZY"
            st.markdown(f'<div class="metric-card"><div class="metric-label">Odprawa Celna</div><div class="metric-value">{status_cło}</div></div>', unsafe_allow_html=True)

        # Składowe do listy
        lista_skladowych = [
            ("Transport: Eksport", stawka_eksport),
            ("Transport: Import", stawka_import),
            (f"Standby przewoźnika ({dni_postoju} d)", koszt_postoju),
            (f"Miejsce parkingowe ({dni_postoju} d)", koszt_parkingu)
        ]
        if koszt_ata > 0: lista_skladowych.append(("Karnet ATA", koszt_ata))
        if koszt_przeprawy > 0: lista_skladowych.append(("Przeprawa promowa / Eurotunel", koszt_przeprawy))

        komponenty_html = "".join([f'<div class="component-item"><span class="comp-name">{nazwa}</span><span class="comp-price">€ {kwota:,.2f}</span></div>' for nazwa, kwota in lista_skladowych])

        glowny_panel_html = f"""
        <div class="price-container">
            <div class="price-label">Rekomendowana stawka projektu</div>
            <div class="price-value">€ {suma_netto:,.2f} <span class="price-currency">netto</span></div>
            <div class="components-title">Szczegółowe zestawienie kosztów</div>
            <div class="components-grid">{komponenty_html}</div>
        </div>
        """.replace("\n", " ")

        st.markdown(glowny_panel_html, unsafe_allow_html=True)

    else:
        st.warning(f"Brak danych w bazie dla miasta {wybrane_miasto} i pojazdu typu {typ_pojazdu}.")

st.markdown("<br><p style='text-align:center; opacity: 0.3; font-size: 0.8rem;'>SQM Multimedia Solutions | Logistics Vantage 2026</p>", unsafe_allow_html=True)
