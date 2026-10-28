
        import streamlit as st
import psycopg  # Modificato da psycopg2 a psycopg per allinearsi ai tuoi requisiti
from psycopg.rows import dict_row  # Ottiene i dati come dizionari (sostituisce RealDictCursor)

# 1. Configurazione Connessione al DB Neon
def get_db_connection():
    # Recupera la stringa dai tuoi secrets di Streamlit Cloud
    conn_string = st.secrets["postgres"]["url"]
    return psycopg.connect(conn_string, row_factory=dict_row)

# Inizializzazione dello stato di login
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
if "ruolo" not in st.session_state:
    st.session_state["ruolo"] = None

# 2. Schermata di Login Unificata
if not st.session_state["logged_in"]:
    st.title("🔒 COMPAL LABSCADENZE v2.0")
    st.subheader("Sviluppato per la gestione della sicurezza cantieri ed attrezzature.")

    username = st.text_input("Username o ID Dipendente:")
    password = st.text_input("Chiave d'Accesso (Password):", type="password")

    if st.button("EFFETTUA IL LOGIN"):
        # Controllo locale statico per l'amministratore (Evita l'errore sulla tabella utenti mancante)
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

# 3. Interfaccia Principale (Dopo il Login)
else:
    st.sidebar.write(f"Utente connesso: **{st.session_state['ruolo'].upper()}**")
    if st.sidebar.button("Logout"):
        st.session_state["logged_in"] = False
        st.session_state["ruolo"] = None
        st.rerun()

    st.title("Dashboard Scadenze - Technogeo")
    
    # Caricamento sicuro delle scadenze dal database
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                # Query di lettura delle scadenze
                cursor.execute("SELECT id, cantiere, descrizione, data_scadenza FROM scadenze;")
                scadenze = cursor.fetchall()
                
                # Mostra i dati nella tabella principale
                st.write(scadenze)
                
                # Pannello di amministrazione avanzato (es. Tasto Elimina)
                if st.session_state["ruolo"] == "admin":
                    st.markdown("### Pannello Amministratore")
                    # Qui puoi reinserire il tuo widget per eliminare i record
                    
    except Exception as e:
        st.error(f"Errore nel caricamento dei dati delle scadenze: {e}")


