ESG Mefali est une plateforme conversationnelle d'IA qui démocratise l'accès à la finance verte pour les PME francophones africaines.

En Afrique francophone, 90 % des PME sont exclues des fonds verts : dossiers complexes, consultants inabordables (5 000–20 000 $), barrières linguistiques. ESG Mefali résout ce problème grâce à un agent conversationnel intelligent qui guide les entrepreneurs en français.

La plateforme combine : un scoring ESG multi-référentiel (BCEAO, IFC, GCF, etc) adapté aux réalités ouest-africaines, un calculateur d'empreinte carbone contextualisé, un matching intelligent vers 10 fonds verts régionaux et internationaux, un crédit scoring alternatif intégrant mobile money et pratiques vertes, et la génération automatique de dossiers PDF prêts à soumettre.

Une extension Chrome accompagne les PME directement sur les sites de fonds, avec pré-remplissage automatique et suggestions IA pour chaque champ.

Stack technique : Vue 3 + FastAPI + PostgreSQL/pgvector + Claude (OpenRouter). Architecture RAG hybride (SQL + recherche sémantique), 20+ skills dynamiques, streaming SSE.

Notre ambition : rendre chaque PME africaine capable de financer sa transition verte, sans intermédiaire coûteux.

---

## Thématique principale

Finance Durable (avec des composantes Climat et Employabilité verte)

---

## Problème

Les PME francophones africaines sont massivement exclues de la finance verte. Trois barrières les bloquent :

1. Complexité ESG — Les référentiels (IFC, GCF, BCEAO) sont techniques, volumineux et en anglais. Sans consultant spécialisé (5 000–20 000 $), une PME ne peut ni évaluer sa conformité, ni identifier ses lacunes.

2. Opacité du financement vert — Il existe des dizaines de fonds (BOAD, BAD, GCF, AFD/SUNREF...) avec des critères d'éligibilité différents. Les PME ne savent pas lesquels existent, ne savent pas si elles sont éligibles, et abandonnent face à la complexité des dossiers.

3. Invisibilité financière — Sans historique de crédit formel, même les PME vertueuses sur le plan environnemental ne peuvent pas accéder aux prêts bancaires. Leurs bonnes pratiques ESG ne sont ni mesurées ni valorisées.

Résultat : moins de 10 % des financements climat en Afrique atteignent les PME, alors qu'elles représentent 80 % de l'emploi et sont les premières impactées par le changement climatique.

---

## Comment utilisez-vous l'intelligence artificielle concrètement ?

L'IA est au cœur de chaque fonctionnalité :

- Agent conversationnel (Claude via OpenRouter) — Un LLM orchestre 20+ skills dynamiques via function calling. Il collecte les données par dialogue naturel (pas de formulaires), exécute les calculs, et synthétise les résultats en français. Boucle agentique multi-tours (max 10 itérations) avec streaming SSE.

- RAG hybride (SQL + pgvector) — Les documents entreprise et les descriptions de fonds sont découpés en chunks, vectorisés (Voyage AI, 1024 dimensions) et indexés avec HNSW dans PostgreSQL. La recherche combine filtrage SQL (secteur, pays, montant) et similarité cosinus sémantique pour un matching précis des fonds.

- Scoring ESG par NLP — L'agent extrait les réponses quantitatives (pourcentages, kWh, tonnes) et qualitatives (pratiques déclarées) du langage naturel, les mappe sur les grilles multi-référentielles, et calcule les scores pondérés par pilier (E/S/G).

- Crédit scoring alternatif — Modèle hybride combinant score de solvabilité et score d'impact vert, intégrant données ESG, tendances carbone et transactions mobile money.

- Suggestion IA pour formulaires (extension Chrome) — Le LLM génère des contenus adaptés (descriptions de projet, motivations) pour chaque champ de candidature, en contexte avec le profil entreprise et le fonds ciblé.

- Analyse documentaire — OCR (pytesseract) + extraction PDF/Word + chunking intelligent pour analyser les documents entreprise et pré-remplir les dossiers.

---

## En quoi votre approche se distingue par rapport aux solutions existantes ? (200 mots max)

Les solutions ESG existantes (Refinitiv, Sustainalytics, CDP) ciblent les grandes entreprises occidentales avec des abonnements à 10 000+ $/an, des interfaces en anglais et des référentiels inadaptés à l'Afrique.

ESG Mefali se distingue sur 5 axes :

1. Conversationnel-first — Zéro formulaire. L'agent IA pose les bonnes questions, extrait les données du dialogue naturel, et enrichit le profil progressivement. Accessible aux entrepreneurs peu alphabétisés grâce à la saisie vocale.

2. Multi-référentiel contextualisé — Supporte simultanément les cadres BCEAO (UEMOA), IFC et GCF, avec des critères et pondérations adaptés par secteur et pays africain. Pas de grille unique imposée.

3. Du diagnostic à l'action — Ne s'arrête pas au score : génère des plans de réduction carbone chiffrés (coût, ROI en XOF), assemble les dossiers PDF, et guide le remplissage des formulaires en ligne via l'extension Chrome.

4. Crédit scoring inclusif — Valorise les pratiques vertes dans l'accès au crédit, intégrant mobile money et données alternatives pour les PME sans historique bancaire formel.

5. Architecture ouverte — Skills dynamiques en base de données, modèle LLM interchangeable (Claude/GPT/Mistral via OpenRouter), extensible sans redéploiement.