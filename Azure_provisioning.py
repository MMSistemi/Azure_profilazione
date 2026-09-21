import streamlit as st
from datetime import datetime, timedelta

# Funzioni di utilità
def formatta_data(data: str) -> str:
    for sep in ["-", "/"]:
        try:
            g, m, a = map(int, data.split(sep))
            dt = datetime(a, m, g) + timedelta(days=1)
            return dt.strftime("%m/%d/%Y 00:00")
        except:
            continue
    return data

def genera_samaccountname(
    nome: str,
    cognome: str,
    secondo_nome: str = "",
    secondo_cognome: str = "",
    esterno: bool = False
) -> str:
    n  = nome.strip().lower()
    sn = secondo_nome.strip().lower()
    c  = cognome.strip().lower()
    sc = secondo_cognome.strip().lower()
    suffix = ".ext" if esterno else ""
    limit  = 16 if esterno else 20

    cand = f"{n}{sn}.{c}{sc}"
    if len(cand) <= limit:
        return cand + suffix

    cand = f"{n[:1]}{sn[:1]}.{c}{sc}"
    if len(cand) <= limit:
        return cand + suffix

    return (f"{n[:1]}{sn[:1]}.{c}" )[:limit] + suffix

def build_full_name(
    cognome: str,
    secondo_cognome: str,
    nome: str,
    secondo_nome: str,
    esterno: bool = False
) -> str:
    parts = [cognome, secondo_cognome, nome, secondo_nome]
    full = ' '.join([p for p in parts if p])
    return f"{full} (esterno)" if esterno else full

# Sezione Streamlit per "Gestione Creazione Utenze → Azure"
def gestione_creazione_azure():
    st.header("Creazione Utenze Azure")

    nome             = st.text_input("Nome", key="Nome_Azure").strip().capitalize()
    secondo_nome     = st.text_input("Secondo Nome", key="SecondoNome_Azure").strip().capitalize()
    cognome          = st.text_input("Cognome", key="Cognome_Azure").strip().capitalize()
    secondo_cognome  = st.text_input("Secondo Cognome", key="SecondoCognome_Azure").strip().capitalize()
    telefono_aziendale = st.text_input("Telefono Aziendale (senza prefisso)", key="TelAziendale").strip()
    email_aziendale  = st.text_input("Email Aziendale", key="EmailAziendale").strip()
    manager          = st.text_input("Manager", key="Manager_Azure").strip()
    data_fine        = st.text_input("Data Fine (gg/mm/aaaa)", key="Data_fine_Azure").strip()
    cf               = st.text_input("Codice Fiscale", key="Codice_fiscale").strip()

    casella_personale = st.checkbox("Casella Personale Consip", key="Casella_Personale_Azure")
    sm_list = []
    if casella_personale:
        sm_text = st.text_area("Sulle quali SM va profilato (uno per riga)", key="SM_Azure")
        sm_list = [s.strip() for s in sm_text.split("\n") if s.strip()]

    if st.button("Genera Richiesta Azure"):
        # Generazione campi
        sAMAccountName   = genera_samaccountname(nome, cognome, secondo_nome, secondo_cognome, esterno=True)
        telefono_fmt     = f"+39 {telefono_aziendale}" if telefono_aziendale else ""
        display_name_str = build_full_name(cognome, secondo_cognome, nome, secondo_nome, esterno=True)
        name_fmt         = build_full_name(cognome, secondo_cognome, nome, secondo_nome, esterno=False)

        # Tabella Markdown
        table = [
            ["Campo", "Valore"],
            ["Tipo Utenza", "Azure"],
            ["Utenza", sAMAccountName],
            ["Alias", sAMAccountName],
            ["Name", name_fmt],
            ["DisplayName", display_name_str],
            ["cn", display_name_str],
            ["GivenName", ' '.join(filter(None, [nome, secondo_nome]))],
            ["Surname", ' '.join(filter(None, [cognome, secondo_cognome]))],
            ["Email aziendale", email_aziendale],
            ["Manager", manager],
            ["Cell", telefono_fmt],
            ["Data Fine (mm/gg/aaaa)**", formatta_data(data_fine)],
            ["Codice Fiscale", cf],
        ]
        if casella_personale:
            table.append(["e-mail Consip", f"{sAMAccountName}@consip.it"])

        md = "| " + " | ".join(table[0]) + " |\n"
        md += "| " + " | ".join(["---"] * len(table[0])) + " |\n"
        for row in table[1:]:
            md += "| " + " | ".join(row) + " |\n"

        st.markdown("Ciao, si richiede la definizione di un’utenza Azure come sotto indicato.")
        st.markdown(md)
        st.markdown("**Nota**: il campo “Data Fine” deve essere inserito in Azure come “EmployeeHireDate”.")

        # Selezione licenze e SM
        st.markdown("**Aggiungere Gruppo**\n- O365 Teams Base")
        if casella_personale and sm_list:
            st.markdown("**Profilare su SM:**")
            for sm in sm_list:
                st.markdown(f"- {sm}@consip.it")

        # MFA e contatti
        st.markdown("""
Aggiungere all’utenza la MFA.  
Gli utenti verranno contattati per supporto MFA da imac@consip.it.

Grazie""")

        st.markdown("""
----------------------------------------------------------------------------------
Definita utenza bisogna riassegnare il ticket con:
- **Tipologia:** Software di produttivitò individuale 
- **Descrizione:** Microsoft Office - Assistenza
il Testo da utilizzare è il seguente:

Si richiede cortesemente contatto utenti per MFA/accesso utente/webmail: 
`{name} – {phone} – {email}`  

Nota attenzione alla PSW. Grazie ciao
""".format(name=name_fmt, phone=telefono_fmt, email=email_aziendale)
        )
        if casella_personale and sm_list:
            for sm in sm_list:
                st.markdown(f"Webmail: https://outlook.office.com/mail/{sm}@consip.it")
# Nel tuo app principale:
if __name__ == "__main__":
    st.title("Gestione Utenze Consip")
    gestione_creazione_azure()
