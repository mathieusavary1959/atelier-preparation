# -*- coding: utf-8 -*-
"""
Moteur documentaire de l'Atelier de préparation.
Extraction de texte (PDF, Word, texte), découpage, indexation locale
et recherche par pertinence, sans aucun service externe.
La génération par IA (clé API) est branchée dans app.py par-dessus
les extraits trouvés ici : les réponses restent ancrées dans les documents.
"""
import io
import json
import math
import os
import re
import unicodedata
from collections import Counter

DOSSIER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "donnees")
FICHIER_INDEX = os.path.join(DOSSIER, "index.json")
FICHIER_LIENS = os.path.join(DOSSIER, "liens.json")
DOSSIER_DOCS = os.path.join(DOSSIER, "documents")

MATIERES = ["Histoire sec. 4", "Monde contemporain", "Éducation financière"]


def matiere_depuis_theme(theme):
    t = plier(theme or "")
    if t.startswith("histoire"):
        return "Histoire sec. 4"
    if t.startswith("monde"):
        return "Monde contemporain"
    if t.startswith("education") or t.startswith("financ"):
        return "Éducation financière"
    return "Monde contemporain"

MOTS_VIDES = set("""
le la les de des du un une et est sont au aux en dans sur par pour avec sans
qui que quoi dont où ce cet cette ces il elle ils elles nous vous on se sa son
ses leur leurs a à y d l j n s t c m qu aux être avoir fait faire plus moins
très aussi comme mais ou donc car ne pas au aux être auxiliaire the of and to
""".split())


def plier(texte):
    """Minuscules sans accents, pour comparer sans rater les correspondances."""
    texte = unicodedata.normalize("NFD", texte.lower())
    return "".join(c for c in texte if unicodedata.category(c) != "Mn")


def jetons(texte):
    mots = re.findall(r"[a-zàâäéèêëîïôöùûüç0-9]{3,}", plier(texte))
    return [m for m in mots if m not in MOTS_VIDES]


# ---------------------------------------------------------------- extraction
def extraire_pages(nom, octets):
    """Retourne une liste de (page, texte). Page = numéro réel pour un PDF,
    bloc de paragraphes pour un Word."""
    bas = nom.lower()
    if bas.endswith(".pdf"):
        import fitz
        doc = fitz.open(stream=octets, filetype="pdf")
        pages = []
        for i, page in enumerate(doc):
            pages.append((i + 1, page.get_text()))
        doc.close()
        return pages
    if bas.endswith(".docx"):
        import docx
        d = docx.Document(io.BytesIO(octets))
        paragraphes = [p.text for p in d.paragraphs if p.text.strip()]
        for tableau in d.tables:
            for ligne in tableau.rows:
                for cellule in ligne.cells:
                    if cellule.text.strip():
                        paragraphes.append(cellule.text)
        pages, bloc, numero = [], [], 1
        for p in paragraphes:
            bloc.append(p)
            if sum(len(x) for x in bloc) > 2500:
                pages.append((numero, "\n".join(bloc)))
                bloc, numero = [], numero + 1
        if bloc:
            pages.append((numero, "\n".join(bloc)))
        return pages
    if bas.endswith((".txt", ".md")):
        return [(1, octets.decode("utf-8", errors="ignore"))]
    raise ValueError("Format non pris en charge : " + nom)


def decouper(nom_doc, theme, pages, taille=1200, chevauchement=150, matiere=None):
    """Découpe le texte en extraits repérables (document, page)."""
    extraits = []
    for page, texte in pages:
        texte = re.sub(r"\s+", " ", texte).strip()
        debut = 0
        while debut < len(texte):
            fin = debut + taille
            extraits.append({
                "doc": nom_doc,
                "theme": theme,
                "matiere": matiere or matiere_depuis_theme(theme),
                "page": page,
                "texte": texte[debut:fin],
            })
            if fin >= len(texte):
                break
            debut = fin - chevauchement
    return extraits


# ---------------------------------------------------------------- index
def charger_index():
    if os.path.exists(FICHIER_INDEX):
        with open(FICHIER_INDEX, encoding="utf-8") as f:
            index = json.load(f)
    else:
        index = {"documents": [], "extraits": []}
    # Migration : les anciens index n'ont pas de matière
    for d in index["documents"]:
        if "matiere" not in d:
            d["matiere"] = matiere_depuis_theme(d.get("theme", ""))
        if "ajoute_le" not in d:
            d["ajoute_le"] = ""
    for e in index["extraits"]:
        if "matiere" not in e:
            e["matiere"] = matiere_depuis_theme(e.get("theme", ""))
    return index


def sauver_index(index):
    os.makedirs(DOSSIER_DOCS, exist_ok=True)
    with open(FICHIER_INDEX, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False)


def ajouter_document(index, nom, theme, octets, matiere=None):
    import datetime
    matiere = matiere or matiere_depuis_theme(theme)
    os.makedirs(DOSSIER_DOCS, exist_ok=True)
    chemin = os.path.join(DOSSIER_DOCS, nom)
    with open(chemin, "wb") as f:
        f.write(octets)
    pages = extraire_pages(nom, octets)
    nouveaux = decouper(nom, theme, pages, matiere=matiere)
    index["extraits"] = [e for e in index["extraits"] if e["doc"] != nom]
    index["extraits"].extend(nouveaux)
    index["documents"] = [d for d in index["documents"] if d["nom"] != nom]
    index["documents"].append({
        "nom": nom, "theme": theme, "matiere": matiere,
        "pages": len(pages), "extraits": len(nouveaux),
        "ajoute_le": datetime.date.today().isoformat(),
    })
    sauver_index(index)
    return len(pages), len(nouveaux)


def retirer_document(index, nom):
    index["extraits"] = [e for e in index["extraits"] if e["doc"] != nom]
    index["documents"] = [d for d in index["documents"] if d["nom"] != nom]
    chemin = os.path.join(DOSSIER_DOCS, nom)
    if os.path.exists(chemin):
        os.remove(chemin)
    sauver_index(index)


# ---------------------------------------------------------------- recherche
def rechercher(index, question, k=5, theme=None, matiere=None):
    """Score de pertinence maison (fréquence des termes, rareté dans le fonds)."""
    q = Counter(jetons(question))
    if not q or not index["extraits"]:
        return []
    fonds = [e for e in index["extraits"]
             if theme in (None, "Tous", e["theme"])
             and matiere in (None, e.get("matiere"))]
    n = max(len(fonds), 1)
    df = Counter()
    for e in fonds:
        for m in set(jetons(e["texte"])):
            df[m] += 1
    resultats = []
    for e in fonds:
        compteur = Counter(jetons(e["texte"]))
        score = 0.0
        for mot, fois in q.items():
            if compteur[mot]:
                idf = math.log((n + 1) / (df[mot] + 1)) + 1
                score += fois * (1 + math.log(compteur[mot])) * idf
        if score > 0:
            resultats.append((score, e))
    resultats.sort(key=lambda r: -r[0])
    return resultats[:k]


def phrases_pertinentes(texte, question, max_phrases=3):
    q = set(jetons(question))
    phrases = re.split(r"(?<=[.!?])\s+", texte)
    notees = []
    for p in phrases:
        p = p.strip()
        if len(p) < 25:
            continue
        hits = sum(1 for m in jetons(p) if m in q)
        notees.append((hits, p))
    notees.sort(key=lambda r: -r[0])
    return [p for h, p in notees if h > 0][:max_phrases]


def reponse_documentaire(question, resultats):
    """Réponse assemblée uniquement avec des phrases des documents,
    chacune suivie de sa source. Aucune invention."""
    if not resultats:
        return ("Je ne trouve rien dans tes documents sur ce sujet. "
                "Vérifie le thème choisi ou dépose le document pertinent.")
    lignes = ["D'après tes documents :"]
    sources = []
    for score, e in resultats:
        phrases = phrases_pertinentes(e["texte"], question)
        if not phrases and len(sources) == 0:
            phrases = [e["texte"][:300].strip()]
        for p in phrases[:2]:
            lignes.append("- " + p + f"  [{e['doc']}, p. {e['page']}]")
        s = f"{e['doc']}, p. {e['page']}"
        if s not in sources:
            sources.append(s)
    lignes.append("")
    lignes.append("Sources : " + " ; ".join(sources))
    return "\n".join(lignes)


# ---------------------------------------------------------------- lecture à l'écran
def chemin_document(nom):
    return os.path.join(DOSSIER_DOCS, nom)


def nombre_pages_pdf(nom):
    chemin = chemin_document(nom)
    if not nom.lower().endswith(".pdf") or not os.path.exists(chemin):
        return 0
    import fitz
    doc = fitz.open(chemin)
    n = doc.page_count
    doc.close()
    return n


def image_page_pdf(nom, numero):
    """Rend une page de PDF en image PNG (numero commence à 1)."""
    chemin = chemin_document(nom)
    import fitz
    doc = fitz.open(chemin)
    if numero < 1 or numero > doc.page_count:
        doc.close()
        return None
    page = doc.load_page(numero - 1)
    pix = page.get_pixmap(dpi=110)
    octets = pix.tobytes("png")
    doc.close()
    return octets


def texte_pages(nom):
    """Relit le document déposé et retourne ses pages de texte."""
    chemin = chemin_document(nom)
    if not os.path.exists(chemin):
        return []
    with open(chemin, "rb") as f:
        return extraire_pages(nom, f.read())


# ---------------------------------------------------------------- liens (barre latérale)
def charger_liens():
    if os.path.exists(FICHIER_LIENS):
        with open(FICHIER_LIENS, encoding="utf-8") as f:
            return json.load(f)
    return []


def sauver_liens(liens):
    os.makedirs(DOSSIER, exist_ok=True)
    with open(FICHIER_LIENS, "w", encoding="utf-8") as f:
        json.dump(liens, f, ensure_ascii=False)


def ajouter_lien(liens, matiere, theme, titre, url):
    liens.append({"matiere": matiere, "theme": theme, "titre": titre, "url": url})
    sauver_liens(liens)


def retirer_lien(liens, cible):
    liens.remove(cible)
    sauver_liens(liens)


# ---------------------------------------------------------------- recherche web
def recherche_web(question, n=5):
    """Recherche web affichée dans l'app (moteur DuckDuckGo, sans clé).
    Retourne une liste de {titre, url, extrait}. En cas d'échec, liste vide
    et l'interface propose le lien Google direct."""
    import urllib.parse
    import urllib.request
    url = "https://html.duckduckgo.com/html/?q=" + urllib.parse.quote(question)
    requete = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(requete, timeout=15) as r:
            html = r.read().decode("utf-8", errors="ignore")
    except Exception:
        return []
    resultats = []
    for bloc in re.findall(r'class="result__a" href="([^"]+)".*?>(.*?)</a>', html, re.S):
        lien, titre = bloc
        if "uddg=" in lien:
            lien = urllib.parse.unquote(lien.split("uddg=")[1].split("&")[0])
        titre = re.sub(r"<[^>]+>", "", titre).strip()
        if titre and lien.startswith("http"):
            resultats.append({"titre": titre, "url": lien, "extrait": ""})
        if len(resultats) >= n:
            break
    extraits = re.findall(r'class="result__snippet"[^>]*>(.*?)</a>', html, re.S)
    for i, e in enumerate(extraits[:len(resultats)]):
        resultats[i]["extrait"] = re.sub(r"<[^>]+>", "", e).strip()
    return resultats


# ---------------------------------------------------------------- banque de questions
def extraire_questions(index, matiere):
    """Repère les questions (phrases en ?) dans les documents d'une matière
    et les classe par chapitre (thème du document d'origine)."""
    banque = {}
    vues = set()
    for e in index["extraits"]:
        if e.get("matiere") != matiere:
            continue
        for phrase in re.split(r"(?<=[.!?])\s+", e["texte"]):
            phrase = phrase.strip()
            if phrase.endswith("?") and 20 <= len(phrase) <= 300:
                cle = plier(phrase)
                if cle in vues:
                    continue
                vues.add(cle)
                banque.setdefault(e["theme"], []).append({
                    "question": phrase, "doc": e["doc"], "page": e["page"],
                })
    return banque


# ---------------------------------------------------------------- aide-mémoire
def fiche_depuis_document(index, nom_doc):
    """Fiche synthèse extractive : pour chaque page, les énoncés les plus
    denses en contenu (phrases longues et informatives), sans rédaction."""
    pages = {}
    for e in index["extraits"]:
        if e["doc"] == nom_doc:
            pages.setdefault(e["page"], []).append(e["texte"])
    lignes = [f"FICHE SYNTHÈSE : {nom_doc}", ""]
    for page in sorted(pages):
        texte = " ".join(pages[page])
        phrases = [p.strip() for p in re.split(r"(?<=[.!?])\s+", texte)
                   if 60 <= len(p.strip()) <= 320]
        phrases.sort(key=lambda p: -len(set(jetons(p))))
        lignes.append(f"Page {page}")
        for p in phrases[:2]:
            lignes.append("- " + p)
        lignes.append("")
    return "\n".join(lignes)


# ---------------------------------------------------------------- exports
def exporter_docx(titre, texte):
    import docx
    doc = docx.Document()
    doc.add_heading(titre, level=1)
    for ligne in texte.split("\n"):
        if ligne.strip():
            doc.add_paragraph(ligne)
    tampon = io.BytesIO()
    doc.save(tampon)
    return tampon.getvalue()


def exporter_pdf(titre, texte):
    import fitz
    doc = fitz.open()
    page = doc.new_page()
    y = 56
    page.insert_text((56, y), titre[:80], fontsize=15)
    y += 26
    for ligne in texte.split("\n"):
        for morceau in [ligne[i:i + 95] for i in range(0, max(len(ligne), 1), 95)]:
            if y > 780:
                page = doc.new_page()
                y = 56
            page.insert_text((56, y), morceau, fontsize=10.5)
            y += 15
        y += 3
    octets = doc.tobytes()
    doc.close()
    return octets
