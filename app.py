import streamlit as st
import pandas as pd
import datetime
import psycopg
from psycopg.rows import dict_row

# 1. Configurazione della pagina del browser
st.set_page_config(
    page_title="LabScadenze Enterprise",
    page_icon="🔒",
    layout="wide"
)

# 2. Connessione al database Neon
def get_db_connection():
    conn_string = st.secrets["connections"]["postgresql"]["url"]
    return psycopg.connect(conn_string, row_factory=dict_row)

# Inizializzazione dello stato della sessione per l'autenticazione
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
if "ruolo" not in st.session_state:
    st.session_state["ruolo"] = None
if "utente_nome" not in st.session_state:
    st.session_state["utente_nome"] = None

# Lista globale delle macro-categorie concordate per l'AD
CATEGORIE_AZIENDALI = [
    "👥 Personale", 
    "🏗️ Macchinari", 
    "🚚 Flotta Aziendale", 
    "💻 Digitale & IT", 
    "🏢 Sedi & Logistica", 
    "📜 Gare & Societario"
]

# 3. Schermata di Login
if not st.session_state["logged_in"]:
    st.title("🔒 LABSCADENZE ENTERPRISE v2.0")
    st.subheader("Sviluppato per la gestione della sicurezza cantieri ed attrezzature.")

    with st.form("login_form", clear_on_submit=False):
        username = st.text_input("Username o ID Dipendente:").strip()
        password = st.text_input("Chiave d'Accesso (Password):", type="password").strip()
        submit_button = st.form_submit_button("EFFETTUA IL LOGIN")

    if submit_button:
        # Controllo prioritario per l'Amministratore
        if username == "admin" and password == "admin2026":
            st.session_state["logged_in"] = True
            st.session_state["ruolo"] = "admin"
            st.session_state["utente_nome"] = "Amministratore"
            st.success("Accesso Amministratore eseguito!")
            st.rerun()
        else:
            # Verifica dinamica sul database dei dipendenti registrati
            try:
                with get_db_connection() as conn:
                    with conn.cursor() as cursor:
                        cursor.execute(
                            "SELECT nominativo FROM dipendenti WHERE username = %s AND password_accesso = %s;", 
                            (username, password)
                        )
                        user_record = cursor.fetchone()
                        
                        if user_record:
                            st.session_state["logged_in"] = True
                            st.session_state["ruolo"] = "operaio"
                            st.session_state["utente_nome"] = user_record["nominativo"]
                            st.success(f"Accesso eseguito come {user_record['nominativo']}!")
                            st.rerun()
                        else:
                            # Fallback temporaneo per utenti vecchio stile
                            if username.startswith("operaio") and password == "operaio2026":
                                st.session_state["logged_in"] = True
                                st.session_state["ruolo"] = "operaio"
                                st.session_state["utente_nome"] = username.capitalize()
                                st.rerun()
                            else:
                                st.error("Credenziali non corrette o dipendente non registrato. Riprova.")
            except Exception as e:
                st.error(f"Errore di autenticazione DB: {e}")

# 4. Dashboard Interna
else:
    st.sidebar.image("https://icons8.com", width=80)
    st.sidebar.markdown(f"Utente: **{st.session_state['utente_nome']}**<br>Ruolo: **{st.session_state['ruolo'].upper()}**", unsafe_allow_html=True)
    
    if st.sidebar.button("Effettua il Logout"):
        st.session_state["logged_in"] = False
        st.session_state["ruolo"] = None
        st.session_state["utente_nome"] = None
        st.rerun()

    st.title("📊 LabScadenze Enterprise — Sistema di Controllo Globale")
    st.markdown("---")

    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                
                # Pre-elaborazione: Verifichiamo se esiste la colonna 'categoria' nella tabella scadenze
                cursor.execute("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name='scadenze' AND column_name='categoria';
                """)
                has_categoria_column = cursor.fetchone() is not None

                # =========================================================================
                # PANNELLO AMMINISTRATORE (Vista AD con KPI e Multi-Tab)
                # =========================================================================
                if st.session_state["ruolo"] == "admin":
                    
                    # 1. Recupero dati generali per conteggio scadenze critiche (KPI)
                    cursor.execute("SELECT data_scadenza FROM scadenze;")
                    all_dates = cursor.fetchall()
                    
                    oggi = datetime.date.today()
                    fra_30_giorni = oggi + datetime.timedelta(days=30)
                    
                    critiche = 0
                    in_arrivo = 0
                    in_regola = 0
                    
                    for d in all_dates:
                        dt = d['data_scadenza']
                        if isinstance(dt, datetime.datetime):
                            dt = dt.date()
                        if dt < oggi:
                            critiche += 1
                        elif oggi <= dt <= fra_30_giorni:
                            in_arrivo += 1
                        else:
                            in_regola += 1

                    # Visualizzazione dei Contatori Direzionali KPI
                    col_kpi1, col_kpi2, col_kpi3, col_kpi4 = st.columns(4)
                    col_kpi1.metric(label="🔴 Scadute / Critiche", value=str(critiche), delta="Intervento immediato" if critiche > 0 else "Allineato", delta_color="inverse")
                    col_kpi2.metric(label="🟠 In Scadenza (30 gg)", value=str(in_arrivo))
                    col_kpi3.metric(label="🟢 In Regola", value=str(in_regola))
                    col_kpi4.metric(label="🏢 Asset Totali Monitorati", value=str(len(all_dates)))
                    
                    st.markdown("---")

                    # Gestione delle viste tramite Tab principali
                    tab_op1, tab_op2 = st.tabs(["📅 Inserimento e Gestione", "👥 Registro Anagrafica Dipendenti"])
                    
                    with tab_op1:
                        st.subheader("➕ Inserisci un nuovo Elemento nel Monitoraggio Globale")
                        col1, col2, col3, col4 = st.columns(4)
                        with col1:
                            nuovo_cantiere = st.text_input("Nome Cantiere / Ubicazione:")
                        with col2:
                            nuova_desc = st.text_input("Descrizione Attrezzatura o Adempimento:")
                        with col3:
                            nuova_data = st.date_input("Data di Scadenza Corrente:")
                        with col4:
                            # Menu a tendina per l'AD con tutte le nuove categorie
                            nuova_cat = st.selectbox("Categoria Asset:", CATEGORIE_AZIENDALI)
                        
                        if st.button("Salva nel Sistema"):
                            if nuovo_cantiere and nuova_desc:
                                # Se la colonna 'categoria' esiste nel DB, la inseriamo, altrimenti salviamo normalmente
                                if has_categoria_column:
                                    cursor.execute(
                                        "INSERT INTO scadenze (cantiere, descrizione, data_scadenza, categoria) VALUES (%s, %s, %s, %s);",
                                        (nuovo_cantiere, nuova_desc, nuova_data, nuova_cat)
                                    )
                                else:
                                    cursor.execute(
                                        "INSERT INTO scadenze (cantiere, descrizione, data_scadenza) VALUES (%s, %s, %s);",
                                        (nuovo_cantiere, nuova_desc, nuova_data)
                                    )
                                conn.commit()
                                st.success("Scadenza registrata correttamente ed associata alla categoria!")
                                st.rerun()
                    
                    with tab_op2:
                        st.subheader("👤 Registra Nuovo Dipendente / Operaio")
                        col_dep1, col_dep2, col_dep3 = st.columns(3)
                        with col_dep1:
                            reg_nome = st.text_input("Nome e Cognome Dipendente:")
                        with col_dep2:
                            reg_user = st.text_input("Username per il Login (es: m.rossi):")
                        with col_dep3:
                            reg_pass = st.text_input("Password di Accesso:", type="password", key="reg_pass")
                        
                        if st.button("Abilita e Registra Dipendente"):
                            if reg_nome and reg_user and reg_pass:
                                try:
                                    cursor.execute(
                                        "INSERT INTO dipendenti (username, password_accesso, nominativo) VALUES (%s, %s, %s);",
                                        (reg_user, reg_pass, reg_nome)
                                    )
                                    conn.commit()
                                    st.success(f"Dipendente {reg_nome} registrato ed abilitato con successo!")
                                    st.rerun()
                                except Exception as err:







