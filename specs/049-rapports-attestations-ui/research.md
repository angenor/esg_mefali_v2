# Phase 0 — Research

## R1 — SSR Nuxt + cache CDN court avec invalidation explicite

**Décision** : utiliser `routeRules` Nuxt pour `/verify/**` avec `swr: 60` (équivalent stale-while-revalidate 60 s) couplé à `setResponseHeader('Cache-Control', 'public, max-age=0, s-maxage=60, stale-while-revalidate=60')`. À la révocation côté backend, déclencher une invalidation via webhook interne du CDN (en prod) — tant que ce webhook n'est pas branché, le TTL ≤ 60 s reste un plancher acceptable pour SC-009.

**Rationale** : `routeRules` est la primitive native Nuxt 4 pour le caching SSR, déclarative, compatible Nitro/Vercel/CDN classiques. SWR garantit qu'aucun visiteur ne voit > 60 s d'ancienneté.

**Alternatives écartées** :
- Pas de cache (chaque requête recalcule) → coût et latence trop élevés, contradiction avec Lighthouse 95+.
- Cache long + hydratation client → casse le fallback no-JS (FR-016).

## R2 — SSE depuis Nuxt côté front avec rattrapage au retour de page

**Décision** : `EventSource` natif du navigateur, encapsulé dans un composable `useReportGenerationStream(generationId)` qui (a) ouvre le flux à `GET /me/rapports/generate/{id}/stream` (à confirmer avec backend F24 — sinon fallback poll 1 s), (b) reconnecte automatiquement avec `lastEventId`, (c) au mount de `pages/rapports/index.vue`, lit `useReportsStore().pending` pour rouvrir un flux pour chaque génération encore `running`.

**Rationale** : SSE est plus simple que WebSocket pour un flux unidirectionnel serveur→client, fonctionne nativement sur HTTP/2 + reverse proxy standard, et `lastEventId` couvre le cas de la déconnexion réseau.

**Alternatives écartées** :
- Polling pur → user story 2 demande feedback fluide ; SSE est plus économe.
- WebSocket → sur-ingénierie pour un flux unidirectionnel.

**À confirmer en Phase 2** : si l'endpoint SSE n'existe pas encore côté backend F24, Phase 2 ajoutera une tâche backend de wrapping (lecture du statut en DB toutes les ~500 ms et émission d'événements `progress` / `done` / `failed`) avant de brancher l'UI.

## R3 — Aperçu PDF via URL signée TTL court

**Décision** : ajouter un endpoint backend `GET /me/rapports/{id}/preview-url` retournant `{url: string, expires_at: ISO8601}` où `url` est une URL signée HMAC à TTL 5 min, vérifiée côté serveur contre la session PME et `account_id`. Le front l'injecte dans `<iframe src=...>` du `ReportDrawer.vue`.

**Rationale** : rend l'aperçu compatible avec le viewer PDF natif du navigateur (pas besoin de pdf.js si l'utilisateur a un Chrome/Firefox/Safari récent) tout en garantissant qu'aucune URL permanente ne fuit. Pattern standard, compatible CDN.

**Alternatives écartées** :
- Stream binaire authentifié dans un viewer JS embarqué → poids JS plus élevé, moins compatible.
- URL publique permanente → fuite multi-tenant.

**À confirmer en Phase 2** : tâche backend pour l'endpoint `preview-url` (probablement < 30 lignes, réutilise le storage F24).

## R4 — QR code PNG côté front

**Décision** : utiliser la lib `qrcode` (déjà installée par F30 selon brouillon F49). Composant `ShareAttestationModal.vue` génère le QR à la volée à partir de l'URL absolue `${APP_URL}/verify/{id}`, avec niveau d'erreur `H` (Haute correction) pour rester scannable jusqu'à 4 cm de côté (SC-006).

**Rationale** : génération côté client = aucun aller-retour réseau supplémentaire, rendu instantané, téléchargement PNG via `canvas.toDataURL()`.

**Alternatives écartées** :
- Génération côté backend → latence inutile pour un payload public connu d'avance (l'URL).

## R5 — No-JS fallback pour `/verify/{id}`

**Décision** : la page est rendue intégralement côté serveur (Nuxt SSR) avec un template HTML qui contient toutes les infos critiques (verdict, raison sociale, dates, KPI) avant l'hydratation. Aucune dépendance JavaScript pour afficher les données ; l'hydratation côté client n'apporte que la bascule de langue interactive et la copie du lien (avec fallback `<details>` natif si JS absent). Le badge ✓/✗ et le bandeau de révocation sont du HTML pur stylé en Tailwind.

**Rationale** : satisfait FR-016 (essentiel lisible sans JS), Lighthouse SEO 95+ et résilience.

**Alternatives écartées** :
- SPA + skeleton → casse le no-JS et fait chuter Lighthouse.

## R6 — Bilingue scope contrôlé (FR/EN sur `/verify` uniquement)

**Décision** : composable interne `useVerifyI18n()` qui charge un dictionnaire JSON statique (`i18n/verify/fr.json`, `i18n/verify/en.json`). Le dictionnaire couvre :
- libellés statiques (header, footer, badges, encart pédagogique, libellés de dates) ;
- énumérations contrôlées (types d'attestation : `conformite_esg` → "Conformité ESG" / "ESG Compliance" ; motifs de révocation : `erreur_emission` → "Erreur d'émission" / "Issuance error" ; libellés d'indicateurs standards venant du catalogue backend, qui devra exposer un `label_en` pour les indicateurs publiés en EN).

Persistance via cookie `mefali_verify_lang` (`fr` | `en`), lu côté serveur dès la première requête.

**Rationale** : évite de tirer `@nuxtjs/i18n` complet pour 2 langues sur une seule page ; cookie persiste la préférence sans state global.

**À confirmer en Phase 2** : le backend F30 doit exposer `label_en` sur les indicateurs (ou un fallback `label`) ; sinon l'UI affiche le `label` FR avec une mention discrète. Tâche Phase 2 dédiée.

**Alternatives écartées** :
- `@nuxtjs/i18n` complet → poids inutile pour ce scope.
- Traduction automatique côté front → risque sémantique inacceptable sur des KPI ESG.

## R7 — Lighthouse ≥ 95 sur mobile

**Décision** : combiner les techniques suivantes :
- preload des polices (`link rel="preload" as="font"`).
- `loading="lazy"` sur l'image d'illustration de l'encart pédagogique.
- aucune dépendance JS lourde sur la page publique (pas de chart.js, pas de gsap).
- balises Open Graph + JSON-LD `Organization` + `Certification` injectées côté SSR.
- `<html lang="fr">` ou `<html lang="en">` selon le cookie.
- header `Cache-Control: s-maxage=60, stale-while-revalidate=60` cohérent CDN.
- compression brotli activée côté CDN/Nitro.

**Rationale** : page minimaliste, peu d'assets, SSR pur ; les 95+ sont atteignables sans tour de magie.

**Alternatives écartées** :
- AMP → plus maintenu, surcoût d'apprentissage.

## R8 — Réutilisation de l'écosystème déjà livré

**Décision** : réutiliser :
- layout `public.vue` (F38) — déjà inclus.
- composant `<VizSourcePin>` (F40) pour les repères de source dans `PayloadView.vue`.
- design tokens (F36) et primitives UI (F37) pour table, drawer, modale, badge.
- store pattern Pinia déjà utilisé par `creditScore`, `carbon`, etc.

**Rationale** : cohérence visuelle et accélération.

## Résumé des dépendances Phase 2 hors UI pure

Trois petites tâches backend à prévoir dans `tasks.md` :
1. Endpoint `GET /me/rapports/generate/{id}/stream` (SSE, ou un poll-friendly `GET /me/rapports/generate/{id}` à défaut).
2. Endpoint `GET /me/rapports/{id}/preview-url` (URL signée TTL 5 min).
3. Champ `label_en` (optionnel) pour `Indicateur` exposé sur le payload public d'attestation.

Si l'un de ces backends est jugé hors-scope par le PO, les fallbacks UI sont :
1. Polling 1 s.
2. Drawer sans aperçu inline (uniquement métadonnées + bouton « Télécharger »).
3. Affichage des libellés FR partout, switch FR/EN limité aux libellés statiques.
