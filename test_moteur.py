# -*- coding: utf-8 -*-
"""Test du moteur avec un vrai document de Mathieu (cahier d'Histoire 1).
Lancer : python3 test_moteur.py"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import moteur

# Le test travaille dans un dossier temporaire pour ne jamais toucher
# à l'index réel de l'application.
_tmp = tempfile.mkdtemp()
moteur.DOSSIER = _tmp
moteur.FICHIER_INDEX = os.path.join(_tmp, "index.json")
moteur.DOSSIER_DOCS = os.path.join(_tmp, "documents")

PDF = os.path.expanduser("~/workspace/your_files/cahier-histoire-1/cahier1-eleve.pdf")

index = {"documents": [], "extraits": []}
octets = open(PDF, "rb").read()
pages, n_extraits = moteur.ajouter_document(index, "cahier1-eleve.pdf",
                                            "Histoire, cahier 1", octets)
print(f"Extraction : {pages} pages, {n_extraits} extraits")
assert pages >= 10 and n_extraits >= 15, "Extraction trop faible"

question = ("Selon l'Acte de l'Amérique du Nord britannique, quels pouvoirs "
            "reviennent au gouvernement fédéral et lesquels aux provinces ?")
resultats = moteur.rechercher(index, question, k=5)
print(f"Recherche : {len(resultats)} extraits pertinents")
assert resultats, "Aucun résultat"
reponse = moteur.reponse_documentaire(question, resultats)
print("\n--- Réponse documentaire ---\n")
print(reponse)
assert "p." in reponse and "cahier1-eleve.pdf" in reponse, "Sources absentes"
print("\nTEST RÉUSSI")
