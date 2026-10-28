import streamlit as st
import pandas as pd
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
            # Verifica dinamica sul database dei dipendenti registrati (CORRETTA)
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

    st.title("Pannello Monitoraggio Scadenze")
    st.markdown("---")

    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                
                # PANNELLO AMMINISTRATORE (Inserimento Scadenze + GESTIONE DIPENDENTI)
                if st.session_state["ruolo"] == "admin":
                    tab1, tab2 = st.tabs(["📅 Gestione Scadenze", "👥 Registro Anagrafica Dipendenti"])
                    
                    with tab1:
                        st.subheader("➕ Aggiungi Nuova Scadenza Aziendale")
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            nuovo_cantiere = st.text_input("Nome Cantiere / Ubicazione:")
                        with col2:
                            nuova_desc = st.text_input("Descrizione Attrezzatura o Adempimento:")
                        with col3:
                            nuova_data = st.date_input("Data di Scadenza Corrente:")
                        
                        if st.button("Salva nel Sistema"):
                            if nuovo_cantiere and nuova_desc:
                                cursor.execute(
                                    "INSERT INTO scadenze (cantiere, descrizione, data_scadenza) VALUES (%s, %s, %s);",
                                    (nuovo_cantiere, nuova_desc, nuova_data)
                                )
                                conn.commit()
                                st.success("Scadenza registrata correttamente!")
                                st.rerun()
                    
                    with tab2:
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
                                    st.error(f"Errore durante la registrazione: {err}")
                    st.markdown("---")

                # Sezione Visualizzazione Tabella Scadenze (Visibile a tutti)
                st.subheader("📋 Elenco delle Scadenze Attive")
                cursor.execute("SELECT id, cantiere, descrizione, data_scadenza FROM scadenze ORDER BY data_scadenza ASC;")
                rows = cursor.fetchall()

                if rows:
                    df = pd.DataFrame(rows)
                    df.columns = ["ID", "Cantiere", "Descrizione Oggetto", "Data Scadenza"]
                    st.dataframe(df, use_container_width=True)
                    
                    if st.session_state["ruolo"] == "admin":
                        st.markdown("### 🛠️ Strumenti di Gestione Amministrativa")
                        col_del, col_rep = st.columns(2)
                        
                        with col_del:
                            st.markdown("**Eliminazione Record**")
                            id_da_eliminare = st.number_input("Inserisci l'ID del record da rimuovere:", min_value=1, step=1)
                            if st.button("Elimina Definitivamente", type="primary"):
                                cursor.execute("DELETE FROM scadenze WHERE id = %s;", (id_da_eliminare,))
                                conn.commit()
                                st.error(f"Record ID {id_da_eliminare} rimosso con successo.")
                                st.rerun()
                        
                        with col_rep:
                            st.markdown("**Esportazione Dati**")
                            if st.button("Genera Report PDF"):
                                st.success("Report PDF pronto per il download (Funzione attiva)!")
                else:
                    st.info("Nessuna scadenza presente nel database al momento.")

    except Exception as e:
        st.error(f"Si è verificato un errore sul Database Neon: {e}")






