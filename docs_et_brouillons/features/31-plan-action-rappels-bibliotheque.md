# F31 — Plan d'Action, Rappels Cron & Bibliothèque de Ressources

**Phase** : 9 — Plan d'Action et Accompagnement (Module 6)
**Modules brainstorm** : 6.1 (Générateur de Feuille de Route), 6.2 (Système de Suivi et Rappels), 6.3 (Bibliothèque de Ressources)
**Dépendances** : F12, F23, F25
**Estimation** : 2.5 jours

## Contexte et objectif

Cette feature transforme les diagnostics en **action concrète et continue** :

1. **Feuille de route** personnalisée 6/12/24 mois avec étapes atteignables, ressources sourcées, coûts/bénéfices estimés, intégration des délais d'instruction des Offres ciblées (F25/F27).
2. **Système de rappels (cron)** : échéances appels à projets, dates limites par Offre, relances auprès des intermédiaires si silence radio, célébration des progrès (gamification légère).
3. **Bibliothèque de ressources** : guides ESG en français, modèles de documents, formations vidéo courtes, FAQ contextualisées, **fiches par intermédiaire** ("Comment soumettre à BOAD", "Comment travailler avec PNUD").

## User Stories

### US1 — Générer une feuille de route (P1)
**En tant que** PME,
**je veux** un bouton "Générer mon plan d'action" qui produit une roadmap personnalisée :
- horizon configurable (6 / 12 / 24 mois),
- jalons concrets ordonnés (combler tel indicateur ESG manquant, candidater à telle Offre, réduire émissions de X%),
- estimation coûts/bénéfices,
- intégration des deadlines des Offres ciblées,
- ressources liées (guides, templates, fiches intermédiaires).

**afin de** ne pas se perdre.

### US2 — Étapes concrètes et atteignables (P1)
**En tant que** PME,
**je veux** que chaque étape ait :
- un titre court actionable,
- un horizon (semaine/mois précis),
- une catégorie (ESG / Carbone / Crédit / Candidature),
- une priorité (haute / moyenne / basse),
- des ressources liées,
- un statut (à faire / en cours / fait / différé),
- une PME-personne responsable (déclaratif).

**afin de** un plan exécutable.

### US3 — Cron de rappels intelligents (P1)
**En tant que** PME,
**je veux** des rappels automatiques :
- J-30, J-7, J-1 avant deadline d'une Offre `call_for_proposals`,
- 7 jours après création d'une candidature en `brouillon` non éditée,
- 14 jours après soumission d'une candidature sans nouvelles (relance intermédiaire),
- Mensuel : "Bilan d'avancement de votre plan".

**Canaux** : email + dashboard + (post-MVP push).

### US4 — Tableau de bord d'avancement du plan (P1)
**En tant que** PME,
**je veux** voir :
- progression globale (% étapes complétées),
- prochaines échéances,
- étapes en retard (rouge),
- célébration des étapes complétées (gamification : badges, encouragements),

**afin de** rester motivée.

### US5 — Bibliothèque de ressources sourcées (P1)
**En tant que** PME,
**je veux** accéder à `/ressources` avec :
- guides pratiques ESG en français (chacun sourcé F03),
- modèles de documents (politique anti-corruption, charte ESG, plan ESS) en Word/PDF,
- formations vidéo courtes (intégrées YouTube ou hébergées),
- FAQ contextualisées par thème,
- **fiches par intermédiaire** (BOAD, PNUD, AFD, Ecobank, etc.).

**afin de** apprendre et trouver des modèles.

### US6 — Fiches par intermédiaire (P1)
**En tant que** PME ciblant un intermédiaire,
**je veux** une fiche détaillée :
- présentation de l'intermédiaire,
- procédure de soumission étape par étape,
- contacts utiles,
- documents attendus,
- délais habituels,
- exemples de questions des fund officers.

**afin de** ne pas être surprise.

### US7 — Recommandation contextuelle de ressources (P2)
**En tant que** PME,
**je veux** que sur la page d'une candidature à une Offre, je voie automatiquement la fiche de l'intermédiaire et des ressources liées,
**afin de** centraliser.

### US8 — Tool LLM `generate_action_plan` (P2)
**En tant que** PME via chat,
**je veux** dire "fais-moi un plan 12 mois" → roadmap structurée avec timeline (`show_timeline` F16),
**afin de** roadmap conversationnelle.

## Exigences fonctionnelles

- **FR-001** : Service backend `ActionPlanService` :
  - `generate(account_id, horizon_months) -> ActionPlan`,
  - parcourt : indicateurs ESG manquants (F23), réductions carbone prioritaires (F28), candidatures en cours (F25), améliorations crédit (F29),
  - produit liste d'étapes avec priorité/horizon/ressources.
- **FR-002** : Table `action_plan` : `id, account_id, horizon_months, generated_at, version`.
- **FR-003** : Table `action_step` : `id, plan_id, title, description, category ENUM, priority ENUM, horizon_at, status ENUM('todo','doing','done','postponed'), responsible_user_id NULL, ressource_ids INT[], offre_id NULL (si lié), source_id NULL`.
- **FR-004** : Endpoints :
  - `POST /me/action-plan/generate?horizon=12` → génère/régénère.
  - `GET /me/action-plan` → plan actuel avec étapes.
  - `PATCH /me/action-plan/steps/{id}` → édition statut/déclaratif.
- **FR-005** : Page Vue `/profil/plan-action` : timeline, jauge progression, liste étapes par catégorie.
- **FR-006** : Cron jobs (Python `apscheduler` ou cron système, MVP simple) :
  - `notify_offer_deadlines` (quotidien) : J-30/7/1.
  - `notify_inactive_candidatures` (quotidien).
  - `monthly_progress_digest` (1er du mois) : email avec progression du plan.
- **FR-007** : Service email transactionnel (cohérent F10 — provider à clarifier : Resend/Postmark/SES). Templates HTML par type de notification.
- **FR-008** : Table `notification` : `id, account_id, user_id, kind, title, body, link, read_at NULL, sent_email_at NULL, created_at`. UI dashboard la consomme.
- **FR-009** : Tables ressources :
  - `ressource` : `id, kind ENUM('guide','template','video','faq','fiche_intermediaire'), title, description, content_md NULL, file_path NULL, video_url NULL, intermediaire_id NULL, fonds_id NULL, source_id, status, version`.
  - CRUD admin (cohérent F06).
- **FR-010** : Page Vue `/ressources` (liste filtrable) + `/ressources/[id]` (détail).
- **FR-011** : Fiches intermédiaires : sous-type de `ressource` avec `intermediaire_id` lié à F08.
- **FR-012** : Tool LLM `generate_action_plan(horizon_months?)` exposé en F14.

## Exigences non-fonctionnelles

- **NFR-001** : Génération d'un plan complet < 2s.
- **NFR-002** : Cron de rappels traite 1000+ comptes en < 5 min.
- **NFR-003** : Email envoyés avec retry (max 3) + log si échec.
- **NFR-004** : Toutes les ressources sont sourcées (cohérent F03).

## Entités clés

- **ActionPlan**, **ActionStep** (FR-002, FR-003).
- **Notification** (FR-008).
- **Ressource** (FR-009).

## Success Criteria

- **SC-001** : PME complète son profil + projet → génère plan 12 mois → reçoit 10–20 étapes priorisées.
- **SC-002** : Cron J-7 envoie email à PME ayant Offre échéance dans 7 jours.
- **SC-003** : Bibliothèque contient au moins : 5 guides, 3 templates, 5 fiches intermédiaires (seedés).
- **SC-004** : Page `/ressources` charge et filtre correctement.
- **SC-005** : Fiche intermédiaire BOAD complète et lisible.

## Hors-scope MVP

- Gamification avancée (points, classements).
- Plan personnalisé par LLM (skill dédiée — post-MVP).
- Notifications push mobile / SMS (post-MVP).
- Marketplace de mentors / consultants liés aux étapes (post-MVP).
- Génération de modèles de documents personnalisés (en MVP, modèles génériques sourcés).

## Risques et points de vigilance

- **Pertinence du plan** : un plan trop générique = inutile. Investir dans la logique de génération qui croise vraiment les manquements ESG / carbone / crédit / candidatures.
- **Surcharge de notifications** : digest plutôt que stream. Préférences utilisateur (post-MVP).
- **Fiches intermédiaires** : nécessitent un travail manuel important par l'équipe ESG Mefali. Prévoir le temps.
- **Cron en production** : si le backend redémarre, les jobs ne doivent pas se rejouer en double. APScheduler avec persistence DB ou cron OS classique avec idempotence.
- **Anti-spam** : email transactionnel avec SPF/DKIM/DMARC propres, sinon ça finit en spam.
