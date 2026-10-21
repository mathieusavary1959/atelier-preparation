# Atelier de préparation

Ton espace personnel pour travailler avec une IA ancrée dans tes documents
de cours. Pour toi seulement, pas pour les élèves.

## Ce que ça fait

- Tu déposes tes documents (PDF, Word, texte) par thème.
- Ils sont lus et indexés une fois. Ensuite, tu poses des questions et
  l'application répond à partir de tes documents, en citant la page source.
- Onglet Actions rapides : résumé de la matière, questions de compréhension,
  points clés à enseigner.
- Onglet Règles permanentes : tes standards (difficulté, vocabulaire simple,
  noir typographique, etc.), appliqués à chaque demande du mode IA.

## Deux modes de réponse

1. Mode documentaire (actif par défaut, gratuit) : les réponses sont
   assemblées avec les phrases exactes de tes documents. Aucune invention,
   mais pas de rédaction : c'est de la recherche sourcée.
2. Mode IA (optionnel) : avec une clé API à ton nom (Anthropic ou OpenAI,
   coût à l'usage), le modèle rédige de vraies réponses et productions
   à partir des extraits trouvés et de tes règles. C'est ce mode qui
   rapproche l'atelier de ton environnement Muse habituel.

## Démarrer sur ton poste

1. Installer Python, puis : pip install -r requirements.txt
2. Lancer : streamlit run app.py
3. Mot de passe temporaire : preparation
   (à changer avant tout déploiement : variable ATELIER_MDP ou secret
   Streamlit « mot_de_passe »)

## Pour le mode IA

Définir la variable d'environnement ANTHROPIC_API_KEY (ou OPENAI_API_KEY)
avant de lancer, ou la mettre dans les secrets Streamlit au déploiement.
Le modèle se choisit avec ATELIER_MODELE si besoin.

## Fichiers

- app.py : l'interface
- moteur.py : extraction, indexation et recherche dans les documents
- regles.py : tes règles par défaut
- donnees/ : tes documents déposés et l'index (créé au premier dépôt)
- test_moteur.py : vérifie le moteur avec le cahier d'Histoire 1

## État de la maquette

Démonstration déjà chargée : notes d'Études (22 pages) et cahier
d'Histoire 1 (16 pages). Vérifiée le 20 octobre 2026 : extraction,
recherche et citations fonctionnels.
Étape suivante possible : déploiement privé (Streamlit Cloud, mot de
passe) pour y accéder de l'école et de la maison.
