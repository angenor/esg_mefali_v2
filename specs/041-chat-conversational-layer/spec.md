# Feature Specification: Chat Conversational Layer (UI de F12/F13)

**Feature Branch**: `041-chat-conversational-layer`
**Created**: 2026-05-03
**Status**: Draft
**Input**: User description: "F41 — Couche frontend du chat (shell, bubbles, input, EventBus, langgraph) : page chat plein écran où la PME interagit avec le LLM, architecture haut/bas stricte (P10), bulles asymétriques, streaming token-by-token, EventBus pour synchroniser stores Pinia et pages profil ouvertes."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Conversation textuelle libre avec streaming (Priority: P1)

Une PME ouvre `/chat`, tape un message dans la barre input bottom, l'envoie, et voit la réponse du LLM s'afficher progressivement (token-by-token) dans une bulle gauche au-dessus, pendant qu'elle peut continuer à lire. Sa propre question apparaît en bulle droite. La conversation reste lisible (max-width contenue, typographie calme, pas de pictogrammes décoratifs).

**Why this priority**: C'est la fonction cœur du produit — sans cette boucle envoi/streaming/affichage, aucune autre interaction (bottom sheet, viz, mutations) n'a de sens. C'est l'unique surface où la PME accède à l'expertise ESG/financière de la plateforme.

**Independent Test**: Ouvrir `/chat`, envoyer "Bonjour, peux-tu m'expliquer le scope 1 du carbone ?" et vérifier qu'une bulle utilisateur apparaît à droite, puis qu'une bulle LLM apparaît à gauche avec le texte qui se construit token par token (curseur clignotant en fin), et que la bulle se finalise sous 5 secondes.

**Acceptance Scenarios**:

1. **Given** une PME authentifiée sur `/chat` avec input vide, **When** elle tape un message et appuie sur Cmd/Ctrl+Enter, **Then** sa bulle apparaît à droite (fond brand-50) et le premier token LLM s'affiche en moins de 500 ms dans une bulle gauche (fond neutral-50).
2. **Given** un streaming en cours, **When** la PME scrolle vers le haut pour relire un message précédent, **Then** le scroll automatique vers le bas est suspendu jusqu'à ce qu'elle revienne en bas.
3. **Given** une bulle LLM finalisée contenant des citations sourcées, **When** la PME clique sur une citation en superscript, **Then** un popover affiche le détail de la source.
4. **Given** un message envoyé, **When** la connexion réseau se coupe brièvement et reprend, **Then** le streaming reprend sans tokens dupliqués.

---

### User Story 2 - Interaction structurée via bottom sheet (Priority: P1)

Lorsque le LLM a besoin d'une réponse cadrée (choix multiple, upload de document, formulaire, plage de dates), l'input texte se masque et un bottom sheet s'ouvre avec le contrôle approprié. La PME complète, valide ; le bottom sheet se ferme, le message structuré rejoint l'historique de chat, et l'input texte revient.

**Why this priority**: Architecture haut/bas non négociable (constitution P10) — toute saisie structurée DOIT vivre dans un bottom sheet, jamais inline dans une bulle. Sans cette mécanique, la collecte de données ESG/financières fiables est impossible.

**Independent Test**: Provoquer une question LLM de type QCU ("Quelle est la taille de votre entreprise ?") et vérifier que l'input texte disparaît, qu'un bottom sheet s'ouvre avec les choix, que la sélection + validation produit une bulle utilisateur structurée et que l'input texte revient.

**Acceptance Scenarios**:

1. **Given** le LLM invoque un outil de question structurée, **When** la couche chat reçoit l'intention, **Then** l'input texte est masqué et le bottom sheet correspondant s'ouvre.
2. **Given** un bottom sheet ouvert, **When** la PME clique "Répondre librement", **Then** le bottom sheet se ferme, l'input texte revient, et le prochain envoi est traité comme freetext (re-classifié par l'orchestrateur).
3. **Given** un bottom sheet validé, **When** la réponse est envoyée, **Then** une bulle utilisateur résumant la sélection apparaît dans l'historique.

---

### User Story 3 - Synchronisation bidirectionnelle profil ↔ chat (Priority: P1)

Une PME a la page profil entreprise ouverte dans un onglet et le chat dans un autre. Quand le LLM met à jour un champ entreprise (ex. effectif, secteur) suite à une conversation, la page profil se rafraîchit automatiquement sans rechargement. Inversement, si la PME édite manuellement un champ dans le profil, le contexte LLM est invalidé pour ce champ.

**Why this priority**: Constitution P8 (sync bidirectionnel non négociable) — la base de données est l'unique source de vérité, jamais le contexte LLM. Sans EventBus, l'utilisateur perdrait confiance en voyant des données divergentes.

**Independent Test**: Ouvrir le profil entreprise dans une fenêtre, le chat dans une autre, déclencher une mutation LLM (ex. "Mon entreprise a 12 salariés") et vérifier que le champ effectif passe à 12 dans la page profil sans rechargement.

**Acceptance Scenarios**:

1. **Given** une page entité ouverte et le chat ouvert, **When** le LLM mute un champ via un outil de mutation, **Then** la page entité reflète le nouveau champ en moins de 1 seconde.
2. **Given** une mutation propagée, **When** la PME revient sur l'historique chat, **Then** un indicateur visuel sobre signale qu'une mise à jour a eu lieu (sans re-déclencher le LLM).

---

### User Story 4 - Gestion des conversations passées (Priority: P1)

Une PME accède à une sidebar listant ses conversations précédentes (titre auto, date), peut cliquer sur une ancienne pour relire/poursuivre, ou démarrer un "Nouveau chat".

**Why this priority**: Sans persistance et navigation des threads, chaque session repart de zéro — la mémoire utilisateur s'effondre, l'utilisateur ne peut pas reprendre un dossier en cours.

**Independent Test**: Avoir plusieurs threads en base, ouvrir `/chat`, vérifier la sidebar, cliquer un thread ancien, vérifier que les messages se rechargent intégralement, cliquer "Nouveau chat", vérifier qu'un thread vide démarre.

**Acceptance Scenarios**:

1. **Given** des conversations existantes, **When** la PME ouvre `/chat`, **Then** la sidebar liste les threads par date décroissante avec un titre auto-généré.
2. **Given** un thread sélectionné, **When** la PME y poste un nouveau message, **Then** la conversation se poursuit dans le même thread sans créer de doublon.

---

### User Story 5 - Visualisations dans les bulles LLM (Priority: P1)

Lorsque le LLM répond avec un KPI, un graphique, un schéma ou un tableau, le rendu apparaît dans une bulle gauche élargie (visualisation embed), lisible et non débordante.

**Why this priority**: Le produit livre des analyses ESG chiffrées et des dossiers — sans visualisations inline, le LLM se résume à du texte, ce qui détruit la valeur perçue.

**Independent Test**: Provoquer une réponse LLM avec un KPI carbone et vérifier que la bulle gauche affiche un composant KPI lisible. Idem pour graphique, mermaid, tableau.

**Acceptance Scenarios**:

1. **Given** une réponse LLM contenant une visualisation, **When** la bulle se finalise, **Then** la visualisation correspondante est rendue à l'intérieur, occupe une largeur élargie mais reste contenue, et reste accessible (lecteurs d'écran).

---

### User Story 6 - Onboarding du premier chat (Priority: P1)

Au tout premier accès à `/chat`, la PME bénéficie d'une visite guidée en 4 étapes pointant : input texte, attache fichier, sidebar, exemple de bottom sheet.

**Why this priority**: Sans onboarding, la PME (cible non technique) ne découvre pas l'architecture haut/bas et risque d'abandonner — l'expérience est jugée confuse au premier contact.

**Independent Test**: Connecter une PME nouvelle, ouvrir `/chat` pour la première fois, vérifier les 4 étapes du tour, fermer, vérifier que le tour ne réapparaît pas au prochain accès.

**Acceptance Scenarios**:

1. **Given** un compte PME sans flag onboarding chat, **When** elle ouvre `/chat`, **Then** le tour démarre automatiquement.
2. **Given** un tour terminé ou fermé, **When** la PME revient sur `/chat`, **Then** aucun tour ne se relance.

---

### User Story 7 - Erreurs LLM et reprise (Priority: P1)

Si le pipeline LLM échoue (validation Pydantic, timeout, erreur réseau), une bulle d'erreur sobre apparaît avec un bouton "Réessayer" qui relance la dernière requête.

**Why this priority**: Les pannes LLM doivent être visibles sans alarmer ni bloquer — sinon la PME perd confiance et ne sait pas si son message a été pris en compte.

**Independent Test**: Forcer un timeout sur une requête, vérifier qu'une bulle d'erreur sobre s'affiche, cliquer "Réessayer", vérifier que la requête repart proprement.

**Acceptance Scenarios**:

1. **Given** un envoi en cours, **When** le pipeline retourne une erreur après 2 retries, **Then** une bulle d'erreur s'affiche avec libellé clair et bouton "Réessayer".
2. **Given** une bulle d'erreur, **When** la PME clique "Réessayer", **Then** la requête originale est rejouée sans saisie supplémentaire.

---

### User Story 8 - Suggestions et reformulation (Priority: P2)

Sous la dernière bulle LLM, la PME voit 2-3 suggestions courtes (chips) du type "Continuer", "Reformuler", "Donne un exemple" pour relancer la conversation sans taper.

**Why this priority**: Améliore la fluidité, mais la conversation libre fonctionne sans. Reportable post-MVP si pression calendaire.

**Independent Test**: Vérifier que les chips apparaissent après chaque bulle LLM finalisée et que cliquer un chip envoie la requête correspondante comme un message normal.

**Acceptance Scenarios**:

1. **Given** une bulle LLM finalisée, **When** la PME ne tape rien, **Then** 2-3 chips suggérés apparaissent dessous.
2. **Given** un chip cliqué, **When** la requête part, **Then** la conversation reprend comme un envoi standard.

---

### User Story 9 - Indicateur de mémoire conversationnelle (Priority: P2)

Un badge discret en barre supérieure indique la taille du contexte mémoire courant ; cliquer ouvre une modale détaillant les éléments mémorisés.

**Why this priority**: Transparence appréciée pour les utilisateurs avancés mais non bloquante — le système fonctionne sans cette visibilité.

**Independent Test**: Échanger plusieurs messages, vérifier que le badge évolue, cliquer pour voir la modale détail.

**Acceptance Scenarios**:

1. **Given** un thread en cours, **When** la mémoire évolue, **Then** le badge reflète la taille courante.
2. **Given** la modale ouverte, **When** la PME la lit, **Then** elle voit la liste lisible des éléments mémorisés.

---

### Edge Cases

- Que se passe-t-il si le LLM renvoie un Markdown malformé pendant le streaming (ex. `**bold` non fermé) ? La bulle ne doit pas crasher ; le rendu se complète quand le token de fermeture arrive.
- Que se passe-t-il si la PME envoie un nouveau message alors qu'un streaming est encore en cours ? Comportement attendu : envoi mis en file ou bloqué proprement (à clarifier en planning).
- Que se passe-t-il sur mobile quand le clavier virtuel s'ouvre ? L'input texte doit rester visible (safe area iOS), les bulles ne doivent pas être recouvertes.
- Que se passe-t-il si un schéma mermaid contient 100+ nœuds ? Le rendu doit être asynchrone ou plafonné pour ne pas geler la page.
- Que se passe-t-il si la sidebar contient plusieurs centaines de threads ? Pagination ou virtualisation obligatoire pour ne pas dégrader le scroll.
- Que se passe-t-il si une mutation LLM arrive alors que la PME édite manuellement le même champ dans la page profil ? Conflit à signaler sans écraser silencieusement la saisie utilisateur.
- Que se passe-t-il si le LLM tente d'injecter du contenu HTML/script dans une réponse ? Le sanitizer doit l'éliminer avant rendu.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: La plateforme MUST exposer une page chat plein écran accessible via `/chat` ainsi qu'une route paramétrée par identifiant de thread permettant de revenir sur une conversation antérieure.
- **FR-002**: L'interface MUST respecter une architecture haut/bas stricte : zone haute = historique de bulles (LLM gauche, utilisateur droite, asymétriques), zone basse = input texte OU bottom sheet OU visualisation, jamais autre chose.
- **FR-003**: Les bulles utilisateur MUST apparaître à droite avec un fond distinct, et les bulles LLM à gauche avec un fond neutre, l'horodatage étant accessible au survol.
- **FR-004**: Les bulles LLM MUST rendre le contenu Markdown sanitisé (titres, listes, code, tables, blocs mermaid déclenchant la librairie de visualisation), sans permettre l'injection de scripts ou d'iframes.
- **FR-005**: Les citations P1 (sourcing constitutionnel) inline MUST apparaître en superscript cliquable et ouvrir un popover de détail de source.
- **FR-006**: Quand la réponse LLM contient une visualisation (KPI, graphique, schéma, tableau), la bulle gauche MUST embarquer le composant correspondant en largeur élargie.
- **FR-007**: Pendant la rédaction LLM, un indicateur de saisie animé MUST être visible avant l'arrivée du premier token.
- **FR-008**: La couche chat MUST afficher la réponse LLM en streaming token-by-token avec un curseur clignotant en fin de stream, le rendu Markdown tolérant les contenus partiels sans crash.
- **FR-009**: La barre input MUST proposer une zone texte auto-redimensionnable (1 à 6 lignes), un bouton d'envoi, un bouton d'attache de fichier, et le raccourci Cmd/Ctrl+Enter pour envoyer.
- **FR-010**: Quand l'orchestrateur LLM invoque une question structurée ou une commande nécessitant un contrôle dédié, la couche chat MUST masquer l'input texte et ouvrir le bottom sheet correspondant.
- **FR-011**: Tout bottom sheet ouvert MUST proposer un bouton "Répondre librement" qui le ferme, restaure l'input texte, et fait que le prochain envoi est re-classifié comme freetext.
- **FR-012**: La couche chat MUST exposer une sidebar listant les conversations passées (titre auto-généré, date, icône) avec un bouton "Nouveau chat".
- **FR-013**: La couche chat MUST propager les mutations LLM aux stores et aux pages profil ouvertes via un bus d'événements client-side, sans déclencher de boucle qui rappelle le LLM sur ces mutations UI.
- **FR-014**: Quand une erreur du pipeline LLM survient (validation, timeout, réseau), la couche chat MUST afficher une bulle d'erreur sobre avec un bouton "Réessayer" relançant la dernière requête.
- **FR-015**: Le scroll de l'historique MUST se positionner automatiquement en bas à chaque nouveau message, sauf si la PME a scrollé vers le haut, auquel cas la position MUST être préservée.
- **FR-016**: La reconnexion en cours de streaming MUST reprendre sans dupliquer de tokens, en s'appuyant sur un identifiant de séquence.
- **FR-017**: Sur mobile, l'input MUST rester visible et accessible quand le clavier virtuel s'ouvre (safe area).
- **FR-018**: La largeur maximale du contenu (bulles + input) MUST être bornée pour préserver la lisibilité (référence : 720 px de largeur de contenu).
- **FR-019**: Au premier accès à `/chat` pour un compte donné, la couche chat MUST déclencher un tour guidé en 4 étapes (input, attache fichier, sidebar, exemple de bottom sheet) et MUST garantir qu'il ne se relance pas une fois terminé ou fermé.
- **FR-020**: La couche chat MUST permettre de consulter à la demande le contenu mémoire associé au thread courant.
- **FR-021**: La couche chat MUST proposer 2-3 suggestions courtes (chips) sous la dernière bulle LLM finalisée, et l'envoi d'un chip MUST être traité comme un envoi standard.
- **FR-022**: Un badge en barre supérieure MUST refléter la taille courante de la mémoire conversationnelle et MUST ouvrir une modale de détail au clic.
- **FR-023**: Tout contenu généré par le LLM MUST être strictement assaini avant rendu (suppression des balises script, iframe, gestionnaires d'événements et URI dangereuses).
- **FR-024**: Tous les libellés et messages utilisateur MUST être en français, conformément à la règle linguistique du projet.
- **FR-025**: La couche chat MUST consigner les messages utilisateur et LLM dans un thread persistant, de sorte qu'un retour ultérieur sur ce thread restitue l'historique complet.

### Key Entities

- **Thread de conversation** : représente un fil d'échange entre une PME et le LLM ; possède un identifiant, un titre auto-généré, une date de création, une date de dernière activité, un compte propriétaire.
- **Message** : appartient à un thread, possède un auteur (utilisateur ou LLM), un horodatage, un contenu textuel ou une charge structurée (visualisation, sélection issue d'un bottom sheet), un identifiant de séquence pour la dédup en streaming.
- **Source citée** : référence sourcée associée à une portion de message LLM, accessible via popover.
- **État de mémoire** : snapshot consultable du contexte conversationnel courant, sa taille étant exposée en barre supérieure.
- **Événement de synchronisation** : message diffusé par le bus client signalant qu'une entité métier a été mutée, contenant le type d'entité, son identifiant et la liste des champs modifiés.
- **Erreur conversationnelle** : représente un échec du pipeline (validation, timeout, réseau) qui se matérialise en bulle d'erreur rejouable.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Le premier token de la réponse LLM s'affiche en moins de 500 ms après l'envoi d'un message utilisateur dans 95 % des cas en conditions réseau normales.
- **SC-002**: Une bulle LLM complète (réponse texte sans outil) se finalise en moins de 5 secondes dans 95 % des cas.
- **SC-003**: Lorsqu'une question structurée est invoquée, le bottom sheet s'ouvre et l'input texte se masque en moins de 300 ms.
- **SC-004**: Lorsqu'une mutation LLM affecte une entité visible dans une autre page ouverte, cette page reflète le nouvel état en moins de 1 seconde sans rechargement explicite.
- **SC-005**: Au moins 90 % des PME qui suivent le tour d'onboarding chat parviennent à envoyer leur premier message libre sans assistance extérieure.
- **SC-006**: Sur mobile, l'input reste accessible (non recouvert) quand le clavier virtuel s'ouvre dans 100 % des cas testés sur les deux principales plateformes mobiles.
- **SC-007**: Le taux d'erreurs LLM affichées comme bulles d'erreur jouables (réessayer fonctionnel) reste supérieur à 99 % — autrement dit, les échecs ne dégénèrent pas en page cassée.
- **SC-008**: Lors d'une coupure réseau brève (<10 s) en cours de streaming, le contenu se reconstitue sans tokens dupliqués dans 100 % des cas testés.
- **SC-009**: Aucune injection de script ou contenu actif provenant d'une réponse LLM ne s'exécute dans le navigateur (audit de sécurité dédié sur 100 % des cas testés).
- **SC-010**: Sur la sidebar, l'ouverture d'un thread ancien (jusqu'à plusieurs mois d'historique) restitue l'intégralité des messages en moins de 2 secondes.

## Assumptions

- Les API backend nécessaires (envoi de message, streaming de réponse, lecture/écriture de threads, détection d'invocation d'outil, mémoire conversationnelle) sont fournies par les features F12/F13/F14/F18 et stables au moment de l'implémentation.
- Les composants de visualisation (KPI, graphiques, mermaid, tableaux) sont fournis par F40 et exposent une API stable pour embed inline.
- Le moteur de bottom sheet (ouverture, fermeture, animation, accessibilité) est fourni par F39.
- Les primitives UI (textarea, boutons, toasts, modales) sont fournies par F37 et le shell applicatif (header, navigation, layout) par F38.
- Le design system tokens (couleurs neutres, brand-50, typographie, espacements) provient de F36.
- L'authentification PME est déjà en place (F02) ; la couche chat ne gère pas la connexion mais consomme la session courante.
- Le LLM, l'orchestrateur et la mémoire (F13/F14/F18) émettent des événements normalisés (intention d'outil, mutation d'entité, fin de stream, erreur) que la couche chat consomme.
- Le périmètre MVP exclut explicitement : voix entrante/sortante, multi-utilisateur sur un même thread, recherche plein-texte dans les messages, export PDF de thread.
- La langue par défaut de l'interface est le français ; pas de bascule de langue pour les contenus chat.
- Les conversations sont privées au compte PME et soumises au RLS PostgreSQL standard du projet.
