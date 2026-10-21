# -*- coding: utf-8 -*-
"""
Atelier de préparation : l'espace personnel de Mathieu pour travailler
avec une IA ancrée dans ses propres documents de cours.

Deux modes de réponse :
1. Mode documentaire (par défaut, aucun coût) : recherche dans les documents
   déposés et réponse assemblée avec leurs phrases exactes, sources citées.
2. Mode IA (optionnel) : si une clé API est configurée (Anthropic ou OpenAI),
   le modèle rédige à partir des extraits trouvés et des règles permanentes.

Lancer : streamlit run app.py
Mot de passe : variable ATELIER_MDP, secret Streamlit « mot_de_passe »,
sinon le mot temporaire « preparation » (à changer avant tout déploiement).
"""
import os

import streamlit as st

import moteur
from regles import REGLES_PAR_DEFAUT

st.set_page_config(page_title="Atelier de préparation", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Work+Sans:wght@400;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Work Sans', sans-serif; }
h1, h2, h3 { font-family: 'Bebas Neue', sans-serif; letter-spacing: .04em; }
.stApp { background-color: #0d0d0d; color: #f2f2f2; }
section[data-testid="stSidebar"] { background-color: #141414; }
</style>
""", unsafe_allow_html=True)

# ------------------------------------------------------------------ accès
def mot_de_passe_attendu():
    try:
        if "mot_de_passe" in st.secrets:
            return st.secrets["mot_de_passe"]
    except Exception:
        pass
    return os.environ.get("ATELIER_MDP", "preparation")


if not st.session_state.get("connecte"):
    st.title("Atelier de préparation")
    st.write("Espace personnel. Entre ton mot de passe.")
    saisie = st.text_input("Mot de passe", type="password")
    if st.button("Entrer"):
        if saisie == mot_de_passe_attendu():
            st.session_state["connecte"] = True
            st.rerun()
        else:
            st.error("Mot de passe incorrect.")
    st.stop()

# ------------------------------------------------------------------ état
index = moteur.charger_index()
if "messages" not in st.session_state:
    st.session_state["messages"] = []
chemin_regles = os.path.join(moteur.DOSSIER, "regles.txt")
if os.path.exists(chemin_regles):
    with open(chemin_regles, encoding="utf-8") as f:
        regles_actuelles = f.read()
else:
    regles_actuelles = REGLES_PAR_DEFAUT


def cle_api():
    for nom in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY"):
        try:
            if nom in st.secrets:
                return nom, st.secrets[nom]
        except Exception:
            pass
        if os.environ.get(nom):
            return nom, os.environ[nom]
    return None, None


def repondre_ia(question, resultats):
    """Rédaction par le modèle, strictement à partir des extraits trouvés."""
    nom_cle, cle = cle_api()
    if not cle:
        return None
    contexte = "\n\n".join(
        f"[{e['doc']}, p. {e['page']}]\n{e['texte']}" for _, e in resultats)
    prompt = (f"{regles_actuelles}\n\nExtraits des documents de Mathieu :\n"
              f"{contexte}\n\nDemande : {question}\n\n"
              "Réponds en citant le document et la page pour chaque fait.")
    import requests
    try:
        if nom_cle == "ANTHROPIC_API_KEY":
            r = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers={"x-api-key": cle, "anthropic-version": "2023-06-01",
                         "content-type": "application/json"},
                json={"model": os.environ.get("ATELIER_MODELE", "claude-sonnet-4-5"),
                      "max_tokens": 2000,
                      "messages": [{"role": "user", "content": prompt}]},
                timeout=120)
            r.raise_for_status()
            return r.json()["content"][0]["text"]
        r = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {cle}"},
            json={"model": os.environ.get("ATELIER_MODELE", "gpt-4o"),
                  "messages": [{"role": "user", "content": prompt}]},
            timeout=120)
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]
    except Exception as e:
        return f"Le mode IA a échoué ({e}). Réponse documentaire ci-dessous.\n\n" + \
            moteur.reponse_documentaire(question, resultats)


def produire(question, theme):
    resultats = moteur.rechercher(index, question, k=5, theme=theme)
    reponse = repondre_ia(question, resultats)
    if reponse is None:
        reponse = moteur.reponse_documentaire(question, resultats)
    st.session_state["messages"].append({"role": "user", "content": question})
    st.session_state["messages"].append({"role": "assistant", "content": reponse})


# ------------------------------------------------------------------ barre latérale
with st.sidebar:
    st.title("Bibliothèque")
    theme_depot = st.text_input("Thème du dépôt", placeholder="Ex. Histoire, cahier 1")
    fichiers = st.file_uploader("Déposer des documents (PDF, Word, texte)",
                                type=["pdf", "docx", "txt", "md"],
                                accept_multiple_files=True)
    if fichiers and st.button("Indexer les documents"):
        for f in fichiers:
            try:
                pages, extraits = moteur.ajouter_document(
                    index, f.name, theme_depot or "Sans thème", f.getvalue())
                st.success(f"{f.name} : {pages} pages, {extraits} extraits indexés.")
            except Exception as e:
                st.error(f"{f.name} : {e}")
        st.rerun()
    st.divider()
    if index["documents"]:
        for d in index["documents"]:
            c1, c2 = st.columns([4, 1])
            c1.write(f"**{d['nom']}**\n\n{d['theme']} · {d['pages']} pages")
            if c2.button("Retirer", key="ret_" + d["nom"]):
                moteur.retirer_document(index, d["nom"])
                st.rerun()
    else:
        st.write("Aucun document pour l'instant.")
    st.divider()
    themes = ["Tous"] + sorted({d["theme"] for d in index["documents"]})
    theme_choisi = st.selectbox("Travailler sur", themes)
    _, cle = cle_api()
    st.caption("Mode IA actif (clé API détectée)." if cle else
               "Mode documentaire : réponses tirées des documents, sans IA externe.")

# ------------------------------------------------------------------ zone principale
st.title("Atelier de préparation")
onglets = st.tabs(["Clavardage", "Actions rapides", "Règles permanentes"])

with onglets[0]:
    for m in st.session_state["messages"]:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])
    question = st.chat_input("Pose une question sur tes documents...")
    if question:
        produire(question, theme_choisi)
        st.rerun()
    if st.session_state["messages"]:
        echange = "\n\n".join(
            ("**Moi :** " if m["role"] == "user" else "**Atelier :** ") + m["content"]
            for m in st.session_state["messages"])
        st.download_button("Télécharger l'échange (.md)", echange,
                           file_name="echange-atelier.md")

with onglets[1]:
    st.write("Ces actions interrogent le thème sélectionné dans la barre latérale.")
    b1, b2, b3 = st.columns(3)
    if b1.button("Résumer la matière"):
        produire("Fais un résumé fidèle et structuré de la matière contenue "
                 "dans les documents, en citant les sources.", theme_choisi)
        st.rerun()
    if b2.button("5 questions de compréhension"):
        produire("Produis 5 questions qui valident la compréhension des concepts "
                 "(interprétation, causes et effets, application), avec les réponses "
                 "et leurs sources.", theme_choisi)
        st.rerun()
    if b3.button("Points clés à enseigner"):
        produire("Quels sont les points clés à enseigner selon les documents, "
                 "et quelles confusions d'élèves faut-il prévenir ?", theme_choisi)
        st.rerun()

with onglets[2]:
    nouvelles = st.text_area("Tes règles, appliquées à chaque demande du mode IA",
                             value=regles_actuelles, height=380)
    if st.button("Enregistrer les règles"):
        os.makedirs(moteur.DOSSIER, exist_ok=True)
        with open(chemin_regles, "w", encoding="utf-8") as f:
            f.write(nouvelles)
        st.success("Règles enregistrées.")
