# Feature Specification: Design System & Tokens (Fondations UI)

**Feature Branch**: `036-design-system-tokens`
**Created**: 2026-05-02
**Status**: Draft
**Input**: User description: `@docs_et_brouillons/features/36-design-system-tokens.md` — F36 fondations UI : palette, typographie, spacing, radius, ombres, motion, accessibilité, à respecter par les features 037-052.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Fondations design centralisées et cohérentes (Priority: P1)

En tant que développeur frontend de l'équipe ESG Mefali, je veux disposer d'un design system unique (couleurs, typographies, espacements, rayons, ombres, durées d'animation, focus, contrastes) déclaré une seule fois et consommé par toutes les pages, afin que l'UI livrée aux PME ouest-africaines soit cohérente, sobre et inspire confiance, sans qu'aucune feature aval (chat, dashboard, formulaires, rapports, page publique `/verify`) ne réinvente sa propre palette.

**Why this priority**: Toutes les features UI MVP (037-052) dépendent de ces fondations. Sans système de design verrouillé, chaque feature dérive et la plateforme perd l'apparence professionnelle attendue par des dirigeants de PME en finance verte. C'est un préalable bloquant.

**Independent Test**: Une page de référence interne `/dev/design-system` rend toutes les couleurs sémantiques, échelles typographiques, paliers de spacing, niveaux de rayon, ombres, états de focus et démos d'animation. Un revieweur peut valider visuellement la cohérence en 5 minutes sans regarder le code applicatif.

**Acceptance Scenarios**:

1. **Given** la page interne de référence du design system, **When** un développeur l'ouvre dans un navigateur supporté, **Then** elle affiche sans erreur console toutes les sections (palette neutre, palette marque, sémantiques, typographie, spacing, radius, ombres, motion, focus, états désactivés).
2. **Given** un composant existant qui utilise un token, **When** un opérateur design modifie la valeur du token (ex. nuance de vert marque), **Then** la modification se propage à l'ensemble de l'UI sans toucher aux composants.
3. **Given** une revue de PR, **When** un développeur introduit une couleur arbitraire (hors tokens), **Then** la CI ou le linter signalent l'écart avant merge.

---

### User Story 2 - Lisibilité, accessibilité et confiance pour dirigeants PME (Priority: P1)

En tant que dirigeant de PME ouest-africaine consultant la plateforme depuis un smartphone milieu de gamme via une connexion 4G, je veux une interface lisible (contraste suffisant, typographie soignée, valeurs numériques alignées), sobre et qui se charge rapidement, afin de comprendre en confiance les indicateurs ESG, scores et engagements financiers de mon entreprise.

**Why this priority**: Le public cible est non-technicien, parfois en faible bande passante, et l'UI doit transmettre la rigueur d'un produit financier. La lisibilité et l'accessibilité de base sont une exigence métier, pas un confort.

**Independent Test**: Un audit visuel sur smartphone (375 px de large) et desktop (1280 px) vérifie : contrastes AA mesurés (4.5:1 corps, 3:1 texte large), focus visible au clavier sur tous les éléments interactifs, polices nettes (pas de FOIT), valeurs numériques alignées en colonne dans une table KPI.

**Acceptance Scenarios**:

1. **Given** un utilisateur navigue uniquement au clavier, **When** il parcourt une page composée de boutons, liens et champs, **Then** chaque élément reçoit un anneau de focus visible et contrasté.
2. **Given** un utilisateur active la préférence système « réduire les animations », **When** il interagit avec l'UI, **Then** les transitions non-essentielles sont neutralisées (pas de mouvement parasite).
3. **Given** un audit de contraste automatisé sur la page de référence, **When** il s'exécute, **Then** aucun texte du design system n'échoue le seuil AA.
4. **Given** une page contenant des montants et indicateurs chiffrés, **When** elle est rendue, **Then** les chiffres sont alignés (chasse fixe activée) et lisibles dans la police monospace dédiée.

---

### User Story 3 - Évolution maîtrisée (palette, mode sombre, marque) (Priority: P2)

En tant que product manager ou designer, je veux pouvoir faire évoluer la palette (ajustement de la nuance marque, préparation d'un mode sombre futur, changement éventuel de la police principale) sans imposer un refactor à travers le code, afin que la marque puisse mûrir sans coût d'ingénierie disproportionné.

**Why this priority**: Le mode sombre n'est pas livré au MVP mais doit être anticipé. La palette marque peut être ajustée après tests utilisateurs. C'est important mais non bloquant pour livrer la première version.

**Independent Test**: Modifier une variable de token (ex. `--color-brand-500`) ou activer un attribut « mode sombre » sur la racine de l'application doit produire un changement visuel cohérent sans qu'aucun composant ne soit édité. Les tokens sombres existent et sont mappés, même si le bascule reste désactivée au MVP.

**Acceptance Scenarios**:

1. **Given** les tokens dark sont définis mais le basculement est désactivé, **When** un développeur active manuellement la classe ou l'attribut dark sur la racine, **Then** l'UI bascule visuellement sans erreur (tokens dark résolus).
2. **Given** une décision de remplacer la police principale, **When** la nouvelle famille est référencée dans les tokens et chargée localement, **Then** toute l'UI adopte la nouvelle police sans modification de composants.

---

### User Story 4 - Identité de marque et iconographie sobres (Priority: P2)

En tant qu'utilisateur découvrant la plateforme, je veux une identité visuelle sobre (logo, icônes outline cohérentes, illustrations limitées aux états vides), afin de percevoir un produit sérieux et non saturé d'éléments décoratifs.

**Why this priority**: Importante pour la confiance, mais n'empêche pas la livraison fonctionnelle si seuls les tokens et la typographie sont prêts.

**Independent Test**: Inventaire visuel de l'application : un seul jeu d'icônes (style outline cohérent), un logo horizontal et un symbole pour favicon, illustrations spot uniquement présentes sur les écrans vides (max 3 illustrations totales).

**Acceptance Scenarios**:

1. **Given** une page contient des icônes, **When** un revieweur les inspecte, **Then** elles partagent toutes le même style (outline cohérent, taille standard) et viennent du jeu unique retenu.
2. **Given** un écran sans données (liste vide), **When** il s'affiche, **Then** une illustration spot est présente accompagnée d'un message d'aide et d'une action.

---

### Edge Cases

- Un développeur tente d'ajouter une couleur arbitraire hors tokens (ex. valeur hexadécimale dans une classe utilitaire) : la CI doit le détecter et bloquer.
- L'utilisateur a activé `prefers-reduced-motion` au niveau OS : toutes les animations non-essentielles (parallax, fades décoratifs) sont neutralisées ; les feedbacks indispensables (validation de champ) restent perceptibles.
- Connexion lente (4G dégradée) : la police principale doit afficher un fallback système immédiat, sans saut visuel pénalisant (`font-display: swap`).
- Texte contenant des diacritiques français (é, è, ç, à, ô, î, ù, œ) : la police principale doit rendre correctement tous les glyphes nécessaires au français.
- Écran à très haute densité (Retina) ou à très basse résolution (entrée de gamme Android) : tokens d'espacement et radius restent lisibles, jamais flous.
- Mode contraste élevé OS : le focus ring et les couleurs sémantiques restent perceptibles.
- Charge de page mesurée sur smartphone milieu de gamme via 4G : le bundle CSS et les polices ne doivent pas dégrader le LCP.

## Requirements *(mandatory)*

### Functional Requirements

#### Tokens et déclarations centralisées

- **FR-001**: La plateforme MUST exposer un fichier unique de tokens design (couleurs, espacements, rayons, ombres, polices, durées, easings) consommé par tous les composants UI.
- **FR-002**: La couche d'utilitaires CSS MUST lire ces tokens sans duplication de valeurs.
- **FR-003**: La plateforme MUST interdire l'usage de valeurs arbitraires (couleurs, espacements, rayons hors tokens) via un contrôle automatisé exécuté en CI.
- **FR-004**: Les couleurs MUST être référencées par leur rôle sémantique (`success`, `warning`, `danger`, `info`, `brand`, `neutral`) et non par leur teinte technique brute.

#### Palette

- **FR-005**: La palette MUST comprendre au minimum : 11 nuances neutres (50 → 950), une palette marque unique en 9 nuances (50 → 900), et 4 palettes sémantiques (success / warning / danger / info) chacune en 3 nuances (50 / 500 / 700).
- **FR-006**: L'usage de la couleur marque MUST rester parcimonieux (CTA, accents, succès) ; la base de l'UI repose sur les neutres.

#### Typographie

- **FR-007**: La plateforme MUST définir une police principale sans-serif et une police monospace pour les valeurs numériques, toutes deux servies localement (sans appel à un service tiers de polices) avec stratégie de fallback système et `font-display: swap`.
- **FR-008**: L'échelle typographique MUST respecter une progression modulaire d'au moins 9 paliers (de 12 px à 48 px) et fournir des hauteurs de ligne distinctes pour le corps de texte (≈1.5) et les titres (≈1.2).
- **FR-009**: Les valeurs numériques (KPI, montants, indicateurs) MUST être rendues en chasse fixe (`tabular-nums`) afin d'aligner correctement les colonnes.

#### Espacement, rayons, ombres

- **FR-010**: Le système d'espacement MUST respecter une grille de base 4 px et limiter les paliers autorisés à un sous-ensemble fixe (1 / 2 / 3 / 4 / 6 / 8 / 12 / 16 / 24).
- **FR-011**: Le système de rayons MUST proposer 6 niveaux (`sm`, `md`, `lg`, `xl`, `2xl`, `full`) avec un niveau par défaut pour les cartes.
- **FR-012**: Le système d'ombres MUST proposer 5 niveaux subtils (basse opacité), sans effets « néon ».

#### Motion

- **FR-013**: La plateforme MUST définir un vocabulaire d'animations (`fast` ≈120 ms, `base` ≈200 ms, `slow` ≈320 ms) avec courbes d'accélération distinctes pour entrée et sortie.
- **FR-014**: La plateforme MUST détecter la préférence système `prefers-reduced-motion` et neutraliser les transitions non-essentielles, y compris pour les animations pilotées par bibliothèque tierce.

#### Mode sombre

- **FR-015**: Les tokens MUST inclure les valeurs équivalentes pour un mode sombre, mappées automatiquement, sans que le basculement utilisateur soit exposé au MVP.

#### Iconographie et identité

- **FR-016**: La plateforme MUST n'utiliser qu'un seul jeu d'icônes (style outline cohérent) et limiter les illustrations spot aux écrans d'état vide (maximum 3 illustrations spot au MVP).
- **FR-017**: La marque MUST disposer d'un logo horizontal et d'un symbole pour favicon, déclinés en versions claire et sombre.

#### Accessibilité

- **FR-018**: Tous les couples texte/fond du design system MUST atteindre un contraste WCAG AA (≥4.5:1 pour le corps, ≥3:1 pour le texte large).
- **FR-019**: Tous les éléments interactifs MUST exposer un anneau de focus visible (épaisseur ≈2 px, couleur marque, décalage ≈2 px) lors de la navigation au clavier.
- **FR-020**: La plateforme MUST exposer un mécanisme programmatique permettant à n'importe quel composant ou bibliothèque d'animation de respecter `prefers-reduced-motion`.

#### Référence vivante

- **FR-021**: La plateforme MUST exposer en environnement de développement une page de référence rendant l'intégralité des tokens (palette, typographie, spacing, radius, ombres, motion, focus, états).
- **FR-022**: Cette page MUST être désactivée ou non exposée en production.

#### Qualité de production

- **FR-023**: Le code de production MUST ne pas contenir d'instructions de journalisation de débogage (ex. `console.*`).
- **FR-024**: Les ressources statiques (polices, illustrations) MUST être servies depuis l'origine de la plateforme sans dépendance à un CDN tiers de polices.

### Key Entities *(non applicable — pas de données métier)*

Cette feature ne manipule pas d'entités métier persistées. Les artefacts produits sont :

- **Token Design** : variable nommée représentant une décision de style (couleur, espacement, rayon, ombre, police, durée, easing). Attributs : nom, valeur claire, valeur sombre (optionnelle), rôle sémantique.
- **Référence vivante** : page interne listant tous les tokens et leurs rendus visuels.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Un développeur peut faire évoluer la couleur marque ou un palier d'espacement en modifiant une seule valeur, et la modification se propage à 100 % de l'UI sans édition de composants.
- **SC-002**: Aucune valeur de couleur, espacement, rayon ou ombre arbitraire (hors tokens) n'est présente dans le code applicatif au moment de la livraison de la version cible (vérifié par contrôle automatisé).
- **SC-003**: 100 % des couples texte/fond du design system atteignent un contraste WCAG AA, vérifié par audit automatisé.
- **SC-004**: Sur smartphone milieu de gamme en 4G, la première peinture du contenu principal d'une page typique survient en moins de 1,5 seconde.
- **SC-005**: Le poids du code de styles servi en production reste sous le seuil de 30 Ko compressé (gzip).
- **SC-006**: Une revue visuelle de la page de référence en environnement de développement montre toutes les sections (palette, typographie, spacing, radius, ombres, motion, focus, états) sans erreur dans la console du navigateur.
- **SC-007**: 100 % des éléments interactifs présentent un focus visible distinguable lors d'une navigation au clavier de bout en bout sur la page de référence.
- **SC-008**: Lorsque l'utilisateur active `prefers-reduced-motion`, aucune animation décorative n'est jouée (vérifié sur la page de référence et sur un écran applicatif représentatif).
- **SC-009**: Le score d'audit qualité « bonnes pratiques » d'un outil standard (type Lighthouse) atteint au moins 95 sur la page de référence.
- **SC-010**: Un nouveau développeur peut produire un écran respectant le design system en moins de 30 minutes en s'appuyant uniquement sur la page de référence et les tokens, sans recours à une lib UI tierce.

## Assumptions

- La famille de polices principale retenue est Inter (variante woff2), avec JetBrains Mono ou Geist Mono pour la monospace ; un changement reste possible via tokens si un test utilisateur l'exige.
- Le mode sombre est livré « tokens prêts, basculement désactivé » au MVP ; l'activation utilisateur est post-MVP.
- Les langues non latines (Wolof, Bambara, …) sont post-MVP : la couverture de glyphes se limite au français et à l'anglais au MVP.
- Aucune bibliothèque de composants tierce (Vuetify, PrimeVue, Element, etc.) n'est introduite ; les composants sont maison et stylés via tokens.
- Storybook est hors-scope MVP ; la page de référence interne tient lieu de showcase.
- Les illustrations vidéo / Lottie sont hors-scope MVP.
- L'environnement cible est le navigateur récent (deux dernières versions majeures de Chrome, Edge, Safari, Firefox) sur desktop et smartphone, avec une attention particulière aux smartphones Android milieu de gamme.
- La typographie non latine et les ajustements régionaux (par exemple, support RTL) ne sont pas requis au MVP.
- Cette feature ne crée pas de tables en base ni d'endpoints API ; elle ne nécessite donc pas de RLS ni d'audit (constitution P2/P3 non applicables).
- Les principes constitutionnels P10 (UX bottom-sheet pour toute saisie) et P1 (sourcing) n'imposent rien à cette feature de fondations, mais doivent être consommables par les features aval (037-052).

## Hors-scope MVP

- Storybook ou catalogue interactif distinct de la page de référence.
- Bascule utilisateur vers le mode sombre.
- Internationalisation typographique non latine.
- Animations vidéo (Lottie, MP4 décoratifs).
- Personnalisation white-label par compte (la marque est unique au MVP).
- Génération automatique de tokens à partir d'un outil externe (ex. import Figma Tokens) — l'édition reste manuelle.

## Dependencies

- Feature 001 (Foundations & Stack Init) : la stack frontend (framework, layer d'utilitaires CSS) doit être en place.
- Aucune dépendance backend.
- Bloquant pour les features 037 à 052 (UI primitives, app shell, bottom sheet, visualisations, chat conversationnel, onboarding, profil, dashboard PME, plan d'action, scoring ESG, empreinte carbone, credit scoring, rapports, documents/OCR, matching/candidatures/simulateur, notifications/settings/extension panel).
