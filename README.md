# Le Classeur

L'espace personnel de préparation de Mathieu : trois espaces séparés
(Histoire sec. 4, Monde contemporain, Éducation financière), des documents
ancrés, un clavardage qui répond à partir de ses documents.

Décisions de design : voir CAHIER-DES-CHARGES.md (séries 1 et 2,
choix de Mathieu du 20 octobre 2026). En résumé : thème clair, icônes,
barre latérale à gauche, tableau de bord à l'accueil, aucun historique
conservé d'une visite à l'autre.

## Contenu d'un espace de matière
- Clavardage : questions sur les documents de la matière, sources citées,
  bouton de recherche web, exportation Word et PDF de chaque réponse.
- Documents : dépôt en lot, liste avec icônes, retrait.
- Lire : le document à l'écran, page par page (précédent, suivant, numéro).
- Outils : examens et corrigés (gabarits par matière), questionnaire de
  visionnement (lien vidéo ou remise au format), banque de questions
  classée par chapitre d'origine, aide-mémoire depuis les notes.
- Liens : liens utiles de la matière, repris dans la barre latérale.

## Deux modes de réponse
1. Mode documentaire (par défaut, gratuit) : réponses assemblées avec les
   phrases exactes des documents, pages citées. Recherche et citation,
   pas de rédaction.
2. Mode IA (optionnel) : avec une clé API (Anthropic ou OpenAI) dans les
   secrets, le modèle rédige à partir des extraits et des règles
   permanentes. Décision du 20 octobre 2026 : pas de clé pour l'instant.

## Démarrer
- En ligne : https://atelier-preparation.streamlit.app/ (mot de passe
  en secret Streamlit « mot_de_passe »).
- En local : pip install -r requirements.txt, puis streamlit run app.py.
  Mot de passe temporaire : preparation (variable ATELIER_MDP).

## Fichiers
- app.py : l'interface du Classeur
- moteur.py : extraction, indexation, recherche, banque, fiches, exports
- regles.py : les règles permanentes par défaut
- CAHIER-DES-CHARGES.md : toutes les décisions de design
- donnees/ : documents déposés et index (jamais poussé sur GitHub)
- test_moteur.py : vérifie le moteur (dossier temporaire, sans danger)

## Limites connues
- Sur Streamlit Cloud, les documents déposés disparaissent au redémarrage
  de l'application (stockage permanent à ajouter si l'usage le justifie).
- La recherche web intégrée peut être bloquée par les moteurs sur les
  réseaux de centre de données ; le bouton Google direct fonctionne
  toujours.
