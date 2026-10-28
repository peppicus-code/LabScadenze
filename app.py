import streamlit as st
import psycopg2
from psycopg2.extras import RealDictCursor

# 1. Configurazione Iniziale e Connessione al DB Neon per i dati
def get_db_connection():
    # Recupera la stringa dai tuoi secrets di Streamlit Cloud
    conn_string = st.secrets["postgres"]["url"]
    return psycopg2.connect(conn_string, cursor_factory=RealDictCursor)

# Inizializzazione dello stato di login se non presente
if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
if "ruolo" not in st.session_state:
    st.session_state["ruolo"] = None

# 2. Schermata di Login (Mostrata solo se l'utente non è autenticato)
if not st.session_state["logged_in"]:
    st.title("🔒 COMPAL LABSCADENZE v2.0")
    st.subheader("Sviluppato per la gestione della sicurezza cantieri ed attrezzature.")

    # Campi di input
    username = st.text_input("Username o ID Dipendente:")
    password = st.text_input("Chiave d'Accesso (Password):", type="password")

    if st.button("EFFETTUA IL LOGIN"):
        # Controllo locale sicuro per l'amministratore (Bypass tabella utenti)
        if username == "admin" and password == "admin2026":
            st.session_state["logged_in"] = True
            st.session_state["ruolo"] = "admin"
            st.success("Accesso Amministratore eseguito!")
            st.rerun()
        # Spazio per implementare un eventuale login operai statico o su altra tabella
        elif username.startswith("operaio") and password == "operaio2026":
            st.session_state["logged_in"] = True
            st.session_state["ruolo"] = "operaio"
            st.success("Accesso Operatore eseguito!")
            st.rerun()
        else:
            st.error("Credenziali non corrette. Riprova.")

# 3. Interfaccia Principale (Mostrata dopo il Login)
else:
    st.sidebar.write(f"Utente connesso: **{st.session_state['ruolo'].upper()}**")
    if st.sidebar.button("Logout"):
        st.session_state["logged_in"] = False
        st.session_state["ruolo"] = None
        st.rerun()

    st.title("Dashboard Scadenze - Technogeo")
    
    # Esempio di come usi la connessione solo per le scadenze senza toccare "utenti"
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Query di lettura delle scadenze (Assicurati che la colonna 'cantiere' esista qui)
        cursor.execute("SELECT id, cantiere, descrizione, data_scadenza FROM scadenze;")
        scadenze = cursor.fetchall()
        
        # Mostra i dati nella dashboard...
        st.write(scadenze)
        
        # Logica del Tasto Elimina visibile SOLO per l'Admin
        if st.session_state["ruolo"] == "admin":
            st.markdown("### Pannello Amministratore")
            # Inserisci qui il tuo widget di eliminazione record
            
        cursor.close()
        conn.close()
        
    except Exception as e:
        st.error(f"Errore nel caricamento dei dati delle scadenze: {e}")

        

