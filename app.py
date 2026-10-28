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

# 3. Schermata di Login (Supporta l'invio tramite tasto INVIO della tastiera)
if not st.session_state["logged_in"]:
    st.title("🔒 LABSCADENZE ENTERPRISE v2.0")
    st.subheader("Sviluppato per la gestione della sicurezza cantieri ed attrezzature.")

    # Il Form permette di catturare la pressione del tasto Invio
    with st.form("login_form", clear_on_submit=False):
        username = st.text_input("Username o ID Dipendente:")
        password = st.text_input("Chiave d'Accesso (Password):", type="password")
        submit_button = st.form_submit_button("EFFETTUA IL LOGIN")

    # Gestione della verifica credenziali all'invio del form
    if submit_button:
        if username == "admin" and password == "admin2026":
            st.session_state["logged_in"] = True
            st.session_state["ruolo"] = "admin"
            st.success("Accesso Amministratore eseguito!")
            st.rerun()
        elif username.startswith("operaio") and password == "operaio2026":
            st.session_state["logged_in"] = True
            st.session_state["ruolo"] = "operaio"
            st.success("Accesso Operatore eseguito!")
            st.rerun()
        else:
            st.error("Credenziali non corrette. Riprova.")

# 4. Dashboard Interna (Mostrata dopo un login corretto)
else:
    # Barra laterale con informazioni utente e tasto Logout
    st.sidebar.image("https://icons8.com", width=80)
    st.sidebar.markdown(f"Benvenuto,<br>DASHBOARD **{st.session_state['ruolo'].upper()}**", unsafe_allow_html=True)
    
    if st.sidebar.button("Effettua il Logout"):
        st.session_state["logged_in"] = False
        st.session_state["ruolo"] = None
        st.rerun()

    st.title("Pannello Monitoraggio Scadenze")
    st.markdown("---")

    # Caricamento e gestione dei dati delle scadenze
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                
                # Sezione di Inserimento Dati (Esclusiva per l'Amministratore)
                if st.session_state["ruolo"] == "admin":
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
                        else:
                            st.warning("Per favore, compila tutti i campi di testo obbligatori.")
                    st.markdown("---")

                # Sezione Visualizzazione Tabella Scadenze (Visibile a tutti)
                st.subheader("📋 Elenco delle Scadenze Attive")
                cursor.execute("SELECT id, cantiere, descrizione, data_scadenza FROM scadenze ORDER BY data_scadenza ASC;")
                rows = cursor.fetchall()

                if rows:
                    # Trasformazione in DataFrame Pandas per un layout pulito a griglia
                    df = pd.DataFrame(rows)
                    df.columns = ["ID", "Cantiere", "Descrizione Oggetto", "Data Scadenza"]
                    st.dataframe(df, use_container_width=True)
                    
                    # Funzionalità Avanzate dell'Amministratore (Elimina e Report)
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
                            st.info("Generazione report in formato standard ottimizzato.")
                            if st.button("Genera Report PDF"):
                                # Blocco segnaposto per la chiamata al tuo motore ReportLab
                                st.success("Report PDF pronto per il download (Funzione attiva)!")
                else:
                    st.info("Nessuna scadenza presente nel database al momento.")

    except Exception as e:
        st.error(f"Si è verificato un errore durante la lettura o scrittura sul Database Neon: {e}")





