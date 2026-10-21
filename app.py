# -*- coding: utf-8 -*-
"""
Le Classeur : l'espace personnel de préparation de Mathieu.
Trois espaces séparés (Histoire sec. 4, Monde contemporain,
Éducation financière), documents ancrés, aucun historique conservé
d'une visite à l'autre.

Cahier des charges : CAHIER-DES-CHARGES.md (choix des séries 1 et 2).
Mode documentaire par défaut (gratuit) ; mode IA si une clé API
est configurée (ANTHROPIC_API_KEY ou OPENAI_API_KEY).
"""
import os
import urllib.parse

import streamlit as st

import moteur
from regles import REGLES_PAR_DEFAUT

st.set_page_config(page_title="Le Classeur", page_icon=":material/library_books:",
                   layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Work+Sans:wght@400;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Work Sans', sans-serif; }
h1, h2, h3 { font-weight: 700; letter-spacing: .01em; }
.stApp { background-color: #FFFFFF; color: #1F1F1F; }
section[data-testid="stSidebar"] { background-color: #F7F7F5; }
</style>
""", unsafe_allow_html=True)

ICONES_MATIERES = {
    "Histoire sec. 4": ":material/history_edu:",
    "Monde contemporain": ":material/public:",
    "Éducation financière": ":material/payments:",
}
ICONES_FICHIERS = {
    ".pdf": ":material/picture_as_pdf:",
    ".docx": ":material/description:",
    ".txt": ":material/article:",
    ".md": ":material/article:",
}


def icone_fichier(nom):
    for ext, icone in ICONES_FICHIERS.items():
        if nom.lower().endswith(ext):
            return icone
    return ":material/insert_drive_file:"


# ------------------------------------------------------------------ accès
def mot_de_passe_attendu():
    try:
        if "mot_de_passe" in st.secrets:
            return st.secrets["mot_de_passe"]
    except Exception:
        pass
    return os.environ.get("ATELIER_MDP", "preparation")


if not st.session_state.get("connecte"):
    st.title(":material/library_books: Le Classeur")
    st.write("Ton espace personnel de préparation. Entre ton mot de passe.")
    saisie = st.text_input("Mot de passe", type="password")
    if st.button("Entrer", icon=":material/login:"):
        if saisie == mot_de_passe_attendu():
            st.session_state["connecte"] = True
            st.rerun()
        else:
            st.error("Mot de passe incorrect.")
    st.stop()

# ------------------------------------------------------------------ état
index = moteur.charger_index()
liens = moteur.charger_liens()
if "espace" not in st.session_state:
    st.session_state["espace"] = "Accueil"
if "messages" not in st.session_state:
    st.session_state["messages"] = {}
chemin_regles = os.path.join(moteur.DOSSIER, "regles.txt")
if os.path.exists(chemin_regles):
    with open(chemin_regles, encoding="utf-8") as f:
        regles_actuelles = f.read()
else:
    regles_actuelles = REGLES_PAR_DEFAUT


def documents_de(matiere):
    return [d for d in index["documents"] if d.get("matiere") == matiere]


def themes_de(matiere):
    return sorted({d["theme"] for d in documents_de(matiere)})


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
                      "max_tokens": 2500,
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


def produire(matiere, question):
    resultats = moteur.rechercher(index, question, k=5, matiere=matiere)
    reponse = repondre_ia(question, resultats)
    if reponse is None:
        reponse = moteur.reponse_documentaire(question, resultats)
    msgs = st.session_state["messages"].setdefault(matiere, [])
    msgs.append({"role": "user", "content": question})
    msgs.append({"role": "assistant", "content": reponse})


def boutons_export(cle_unique, titre, texte):
    c1, c2 = st.columns(2)
    c1.download_button("Word", moteur.exporter_docx(titre, texte),
                       file_name=cle_unique + ".docx",
                       mime="application/vnd.openxmlformats-officedocument."
                            "wordprocessingml.document",
                       icon=":material/download:", key="dlw_" + cle_unique)
    c2.download_button("PDF", moteur.exporter_pdf(titre, texte),
                       file_name=cle_unique + ".pdf", mime="application/pdf",
                       icon=":material/download:", key="dlp_" + cle_unique)


# ------------------------------------------------------------------ barre latérale
with st.sidebar:
    st.markdown("## :material/library_books: Le Classeur")
    if st.button("Accueil", icon=":material/home:", use_container_width=True,
                 type="primary" if st.session_state["espace"] == "Accueil" else "secondary"):
        st.session_state["espace"] = "Accueil"
        st.rerun()
    for m in moteur.MATIERES:
        if st.button(m, icon=ICONES_MATIERES[m], use_container_width=True,
                     type="primary" if st.session_state["espace"] == m else "secondary"):
            st.session_state["espace"] = m
            st.rerun()
    espace = st.session_state["espace"]
    if espace in moteur.MATIERES:
        st.divider()
        st.markdown(f"**Liens · {espace}**")
        liens_m = [l for l in liens if l["matiere"] == espace]
        if liens_m:
            for l in liens_m:
                st.markdown(f":material/link: [{l['titre']}]({l['url']})")
                if l.get("theme"):
                    st.caption(l["theme"])
        else:
            st.caption("Aucun lien. Ajoute-les dans l'onglet Liens de la matière.")
    st.divider()
    with st.expander("Règles permanentes"):
        nouvelles = st.text_area("Appliquées au mode IA", value=regles_actuelles,
                                 height=260, key="regles_zone")
        if st.button("Enregistrer", icon=":material/save:"):
            os.makedirs(moteur.DOSSIER, exist_ok=True)
            with open(chemin_regles, "w", encoding="utf-8") as f:
                f.write(nouvelles)
            st.success("Règles enregistrées.")
    _, cle = cle_api()
    st.caption("Mode IA actif (clé API détectée)." if cle else
               "Mode documentaire : réponses tirées de tes documents, sans IA externe.")

espace = st.session_state["espace"]

# ------------------------------------------------------------------ accueil
if espace == "Accueil":
    st.title(":material/home: Accueil")
    st.write("Tes trois matières, tes documents, tes outils. "
             "Choisis un espace pour commencer à travailler.")
    colonnes = st.columns(3)
    for i, m in enumerate(moteur.MATIERES):
        docs = documents_de(m)
        with colonnes[i]:
            with st.container(border=True):
                st.markdown(f"### {ICONES_MATIERES[m]} {m}")
                st.write(f"**{len(docs)}** document(s) · "
                         f"**{len(themes_de(m))}** thème(s)")
                ajouts = [d["ajoute_le"] for d in docs if d.get("ajoute_le")]
                st.caption("Dernier ajout : " + (max(ajouts) if ajouts else "aucun"))
                if st.button("Ouvrir l'espace", icon=":material/arrow_forward:",
                             key="ouvrir_" + str(i), use_container_width=True):
                    st.session_state["espace"] = m
                    st.rerun()
    st.divider()
    st.subheader(":material/history: Derniers documents ajoutés")
    tous = sorted(index["documents"], key=lambda d: d.get("ajoute_le", ""),
                  reverse=True)[:5]
    if tous:
        for d in tous:
            st.markdown(f"{icone_fichier(d['nom'])} **{d['nom']}** · "
                        f"{d.get('matiere', '')} · {d['theme']} · {d['pages']} pages")
    else:
        st.write("Aucun document pour l'instant. Ouvre une matière et dépose "
                 "tes documents dans son onglet Documents.")

# ------------------------------------------------------------------ espace matière
if espace in moteur.MATIERES:
    matiere = espace
    docs_m = documents_de(matiere)
    st.title(f"{ICONES_MATIERES[matiere]} {matiere}")
    onglets = st.tabs([":material/chat: Clavardage",
                       ":material/folder_open: Documents",
                       ":material/menu_book: Lire",
                       ":material/widgets: Outils",
                       ":material/link: Liens"])

    # ------------------------------------------------ clavardage
    with onglets[0]:
        msgs = st.session_state["messages"].get(matiere, [])
        for pos, msg in enumerate(msgs):
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
                if msg["role"] == "assistant":
                    boutons_export(f"chat_{matiere}_{pos}", "Échange, Le Classeur",
                                   msg["content"])
        question = st.chat_input(f"Question sur tes documents de {matiere}...")
        if question:
            st.session_state["derniere_question"] = question
            produire(matiere, question)
            st.rerun()
        derniere = st.session_state.get("derniere_question")
        if derniere and msgs:
            if st.button("Chercher sur le web", icon=":material/travel_explore:",
                         key="web_" + matiere):
                st.session_state["web_resultats"] = (
                    derniere, moteur.recherche_web(derniere))
            res = st.session_state.get("web_resultats")
            if res and res[0] == derniere:
                st.markdown("**Résultats web**")
                if res[1]:
                    for r in res[1]:
                        st.markdown(f"[{r['titre']}]({r['url']})")
                        if r["extrait"]:
                            st.caption(r["extrait"])
                else:
                    st.caption("La recherche intégrée n'a rien ramené.")
                st.link_button("Ouvrir cette recherche dans Google",
                               "https://www.google.com/search?q=" +
                               urllib.parse.quote(derniere),
                               icon=":material/open_in_new:")

    # ------------------------------------------------ documents
    with onglets[1]:
        theme_depot = st.text_input("Thème ou chapitre du dépôt",
                                    placeholder="Ex. Population, chapitre 3",
                                    key="theme_" + matiere)
        fichiers = st.file_uploader("Glisse tes documents ici (PDF, Word, texte)",
                                    type=["pdf", "docx", "txt", "md"],
                                    accept_multiple_files=True,
                                    key="dep_" + matiere)
        if fichiers and st.button("Indexer les documents",
                                  icon=":material/upload_file:",
                                  key="idx_" + matiere):
            for f in fichiers:
                try:
                    p, n = moteur.ajouter_document(
                        index, f.name, theme_depot or "Sans thème",
                        f.getvalue(), matiere=matiere)
                    st.success(f"{f.name} : {p} pages, {n} extraits indexés.")
                except Exception as e:
                    st.error(f"{f.name} : {e}")
            st.rerun()
        st.divider()
        if docs_m:
            for d in docs_m:
                c1, c2, c3 = st.columns([5, 3, 1])
                c1.markdown(f"{icone_fichier(d['nom'])} **{d['nom']}**")
                c2.caption(f"{d['theme']} · {d['pages']} pages")
                if c3.button("Retirer", icon=":material/delete:",
                             key="ret_" + matiere + d["nom"]):
                    moteur.retirer_document(index, d["nom"])
                    st.rerun()
        else:
            st.write("Aucun document dans cette matière pour l'instant.")

    # ------------------------------------------------ lire
    with onglets[2]:
        if not docs_m:
            st.write("Dépose d'abord un document dans l'onglet Documents.")
        else:
            choix = st.selectbox("Document à ouvrir", [d["nom"] for d in docs_m],
                                 key="lecture_" + matiere)
            n_pdf = moteur.nombre_pages_pdf(choix)
            if n_pdf:
                c1, c2, c3 = st.columns([1, 2, 1])
                page_cle = "page_" + matiere + "_" + choix
                page_actuelle = st.session_state.get(page_cle, 1)
                if c1.button("Précédent", icon=":material/arrow_back:",
                             key="prec_" + page_cle, disabled=page_actuelle <= 1):
                    st.session_state[page_cle] = page_actuelle - 1
                    st.rerun()
                page = c2.number_input(f"Page (1 à {n_pdf})", min_value=1,
                                       max_value=n_pdf, value=page_actuelle,
                                       step=1, key="num_" + page_cle)
                st.session_state[page_cle] = int(page)
                if c3.button("Suivant", icon=":material/arrow_forward:",
                             key="suiv_" + page_cle, disabled=int(page) >= n_pdf):
                    st.session_state[page_cle] = int(page) + 1
                    st.rerun()
                image = moteur.image_page_pdf(choix, int(page))
                if image:
                    st.image(image, caption=f"{choix} · page {int(page)} sur {n_pdf}",
                             use_container_width=True)
            else:
                pages = moteur.texte_pages(choix)
                if pages:
                    numeros = [p for p, _ in pages]
                    bloc = st.selectbox("Bloc", numeros, key="bloc_" + choix)
                    st.write(dict(pages)[bloc])
                else:
                    st.write("Document introuvable sur le serveur.")

    # ------------------------------------------------ outils
    with onglets[3]:
        outil = st.radio("Outil", ["Examens et corrigés", "Questionnaire de visionnement",
                                   "Banque de questions", "Aide-mémoire"],
                         horizontal=True, key="outil_" + matiere)

        if outil == "Examens et corrigés":
            st.markdown("#### Préparer un examen ou un corrigé")
            themes = ["Tous"] + themes_de(matiere)
            theme_ex = st.selectbox("Matière couverte (thème)", themes,
                                    key="ex_theme_" + matiere)
            types_q = st.multiselect(
                "Types de questions",
                ["QCM", "Vrai ou faux", "Réponses courtes", "Comparaisons",
                 "Mises en situation"],
                default=["QCM", "Vrai ou faux", "Réponses courtes"],
                key="ex_types_" + matiere)
            difficulte = st.slider("Difficulté visée (sur 10)", 1, 10, 6,
                                   key="ex_diff_" + matiere)
            c1, c2 = st.columns(2)
            nb_q = c1.number_input("Nombre de questions", 5, 60, 20,
                                   key="ex_nb_" + matiere)
            total_pts = c2.number_input("Total de points", 10, 200, 60,
                                        key="ex_pts_" + matiere)
            if st.button("Préparer la demande", icon=":material/quiz:",
                         key="ex_go_" + matiere):
                demande = (
                    f"Produis un examen pour la matière {matiere}, thème : "
                    f"{theme_ex}. Types de questions : {', '.join(types_q)}. "
                    f"Nombre de questions : {nb_q}. Total : {total_pts} points. "
                    f"Difficulté visée : {difficulte}/10. Ajoute le corrigé complet. "
                    "Questions de compréhension (interprétation, causes et effets, "
                    "application), vocabulaire simple pour des 17 ans.")
                resultats = moteur.rechercher(
                    index, demande, k=6,
                    theme=None if theme_ex == "Tous" else theme_ex,
                    matiere=matiere)
                texte = repondre_ia(demande, resultats)
                if texte is None:
                    sources = "\n".join(
                        f"- {e['doc']}, p. {e['page']}" for _, e in resultats)
                    texte = ("DEMANDE PRÉPARÉE (la rédaction s'activera avec le "
                             "mode IA)\n\n" + demande +
                             "\n\nExtraits sources rassemblés :\n" +
                             (sources or "Aucun document sur ce thème."))
                st.session_state["examen_" + matiere] = texte
            texte_ex = st.session_state.get("examen_" + matiere)
            if texte_ex:
                st.text_area("Résultat", value=texte_ex, height=320,
                             key="ex_res_" + matiere)
                boutons_export("examen_" + matiere, "Examen, " + matiere, texte_ex)

        elif outil == "Questionnaire de visionnement":
            st.markdown("#### Questionnaire de visionnement")
            mode = st.radio("Mode", ["À partir d'un lien vidéo",
                                     "Remettre un questionnaire au format"],
                            key="vis_mode_" + matiere)
            if mode == "À partir d'un lien vidéo":
                titre_v = st.text_input("Titre de la vidéo", key="vis_titre_" + matiere)
                lien_v = st.text_input("Lien de la vidéo", key="vis_lien_" + matiere)
                if st.button("Préparer le questionnaire", icon=":material/movie:",
                             key="vis_go_" + matiere):
                    lignes = [f"Questionnaire de visionnement : {titre_v or 'Sans titre'}",
                              f"Source : {lien_v}", "", "Nom : ____________   Groupe : ______",
                              "", "PAGE 1"]
                    for i in range(1, 21):
                        if i == 11:
                            lignes += ["", "PAGE 2"]
                        lignes += [f"{i}. ", "________________________________________", ""]
                    lignes.append("Note : les questions se rédigent avec le mode IA "
                                  "ou à la main ; la structure suit tes règles "
                                  "(question 11 en page 2).")
                    st.session_state["vis_" + matiere] = "\n".join(lignes)
            else:
                fichier_q = st.file_uploader("Ton questionnaire existant",
                                             type=["pdf", "docx", "txt", "md"],
                                             key="vis_fic_" + matiere)
                if fichier_q and st.button("Remettre au format",
                                            icon=":material/format_align_left:",
                                            key="vis_fmt_" + matiere):
                    try:
                        pages_q = moteur.extraire_pages(fichier_q.name,
                                                         fichier_q.getvalue())
                        texte_brut = "\n".join(t for _, t in pages_q)
                        questions = []
                        en_cours = ""
                        for ligne in texte_brut.split("\n"):
                            ligne = ligne.strip()
                            if not ligne:
                                continue
                            if ligne[0].isdigit() and (". " in ligne[:5] or ") " in ligne[:5]):
                                if en_cours:
                                    questions.append(en_cours)
                                en_cours = ligne.split(" ", 1)[-1] if " " in ligne else ligne
                            elif en_cours:
                                en_cours += " " + ligne
                            else:
                                en_cours = ligne
                        if en_cours:
                            questions.append(en_cours)
                        sortie = ["Questionnaire de visionnement", "",
                                  "Nom : ____________   Groupe : ______", "", "PAGE 1"]
                        for i, q in enumerate(questions, 1):
                            if i == 11:
                                sortie += ["", "PAGE 2"]
                            sortie += [f"{i}. {q}",
                                       "________________________________________", ""]
                        st.session_state["vis_" + matiere] = "\n".join(sortie)
                    except Exception as e:
                        st.error(f"Lecture impossible : {e}")
            texte_vis = st.session_state.get("vis_" + matiere)
            if texte_vis:
                st.text_area("Résultat", value=texte_vis, height=320,
                             key="vis_res_" + matiere)
                boutons_export("visionnement_" + matiere,
                               "Questionnaire de visionnement", texte_vis)

        elif outil == "Banque de questions":
            st.markdown("#### Banque de questions, classée par chapitre d'origine")
            if st.button("Construire la banque depuis mes documents",
                         icon=":material/library_books:", key="banque_go_" + matiere):
                st.session_state["banque_" + matiere] = moteur.extraire_questions(
                    index, matiere)
            banque = st.session_state.get("banque_" + matiere)
            if banque:
                tout = []
                for theme_b, items in banque.items():
                    with st.expander(f"{theme_b} : {len(items)} question(s)"):
                        for it in items:
                            st.markdown(f"- {it['question']}")
                            st.caption(f"{it['doc']}, p. {it['page']}")
                            tout.append(f"[{theme_b}] {it['question']} "
                                        f"({it['doc']}, p. {it['page']})")
                if tout:
                    boutons_export("banque_" + matiere, "Banque de questions, " + matiere,
                                   "\n".join(tout))
            elif banque is not None:
                st.write("Aucune question repérée dans les documents de cette matière.")

        else:  # Aide-mémoire
            st.markdown("#### Fiche synthèse d'une page, depuis tes notes")
            if docs_m:
                doc_fiche = st.selectbox("Document source",
                                         [d["nom"] for d in docs_m],
                                         key="fiche_doc_" + matiere)
                if st.button("Produire la fiche", icon=":material/summarize:",
                             key="fiche_go_" + matiere):
                    st.session_state["fiche_" + matiere] = moteur.fiche_depuis_document(
                        index, doc_fiche)
                fiche = st.session_state.get("fiche_" + matiere)
                if fiche:
                    st.text_area("Fiche", value=fiche, height=320,
                                 key="fiche_res_" + matiere)
                    boutons_export("fiche_" + matiere, "Fiche synthèse", fiche)
            else:
                st.write("Dépose d'abord un document de notes dans cette matière.")

    # ------------------------------------------------ liens
    with onglets[4]:
        st.markdown("#### Tes liens pour cette matière")
        st.caption("Ils apparaissent aussi dans la barre latérale, à gauche.")
        with st.form("ajout_lien_" + matiere):
            lt = st.text_input("Titre du lien")
            lu = st.text_input("Adresse (https://...)")
            lth = st.text_input("Thème (optionnel)")
            if st.form_submit_button("Ajouter le lien", icon=":material/add_link:"):
                if lt and lu:
                    moteur.ajouter_lien(liens, matiere, lth, lt, lu)
                    st.rerun()
        liens_m = [l for l in liens if l["matiere"] == matiere]
        if liens_m:
            for l in liens_m:
                c1, c2 = st.columns([5, 1])
                c1.markdown(f":material/link: [{l['titre']}]({l['url']})")
                if l.get("theme"):
                    c1.caption(l["theme"])
                if c2.button("Retirer", icon=":material/delete:",
                             key="lien_ret_" + l["titre"] + l["url"]):
                    moteur.retirer_lien(liens, l)
                    st.rerun()
        else:
            st.write("Aucun lien pour cette matière.")
