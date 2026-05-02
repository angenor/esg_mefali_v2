# F49 — Rapports PDF + Page publique /verify (UI de F24 + F30)

**Phase** : E — Documents, rapports, attestations
**Modules brainstorm** : 4.1 rapports + 4.2 attestations vérifiables
**Dépendances** : F36, F37, F38, F40, F24 backend rapports, F30 backend attestations Ed25519
**Estimation** : 3 jours

## Contexte et objectif

Deux pages liées :

1. **`/rapports`** (PME authentifiée) — liste rapports PDF + attestations actives signées Ed25519.
2. **`/verify/{id}`** (public, **non authentifié**) — page sobre vérification attestation via QR code. Aucun login. Read-only. **Vitrine produit majeure** — première impression aux décideurs financiers.

## User Stories

### Page `/rapports` (PME)

- **US1 Liste rapports (P1)** — table : titre, type (Conformité / Carbone / Candidature), date, taille PDF, statut. Bouton "Télécharger" + "Régénérer".
- **US2 Aperçu rapport (P1)** — click ligne → drawer slide-in droite avec iframe PDF.js + métadonnées.
- **US3 Nouvelle génération (P1)** — modal : type rapport + référentiel + période. Submit `POST /me/rapports/generate` + spinner + lien download (SSE ou polling).
- **US4 Liste attestations (P1)** — table avec QR code mini, statut (active / expirée / révoquée), bouton "Partager".
- **US5 Action partage (P1)** — modal copy-link `/verify/{id}` + QR PNG download.
- **US6 Révocation (P1)** — confirm modal → `POST /me/attestations/{id}/revoke`.

### Page publique `/verify/{id}`

- **US7 Vérification publique (P1)** — `GET /verify/{id}` (sans auth, `meta.public = true`) : badge ✓/✗ signature Ed25519, raison sociale, type d'attestation, dates émission/expiration.
- **US8 Détails contenus (P1)** — payload lisible (KPIs, sources via `<VizSourcePin>` F40), lecture seule.
- **US9 Statut révocation (P1)** — badge rouge "RÉVOQUÉE le YYYY-MM-DD" + raison.
- **US10 Lien explicatif (P1)** — bandeau "Qu'est-ce qu'une attestation ESG Mefali ?" + lien doc.
- **US11 Multi-langue (P2)** — switch FR/EN (banques internationales).
- **US12 Branding sobre (P1)** — header logo, footer mentions + RGPD + `/about`. Aucun lien retour app PME.

## Exigences fonctionnelles

- **FR-001** : `pages/rapports/index.vue` + `pages/verify/[id].vue` + `components/rapports/{ReportTable,ReportDrawer,GenerateModal,AttestationCard}.vue`.
- **FR-002** : `pages/verify/[id].vue` utilise layout `public.vue` F38, `meta.public = true`, pas d'auth.
- **FR-003** : Pinia `useReportsStore` + `useAttestationsStore`.
- **FR-004** : PDF preview via `pdf.js` lazy load.
- **FR-005** : QR code via `qrcode` lib (déjà installé F30).
- **FR-006** : Vérification Ed25519 = résultat backend (`/verify/{id}` → `valid: true/false`), pas de crypto côté client.
- **FR-007** : Page publique : `GET /verify/{id}` SSR Nuxt (SEO + partage).

## Exigences non-fonctionnelles

- **NFR-001** : `/verify/{id}` LCP < 1.2 s.
- **NFR-002** : SEO : `<title>`, OG tags, JSON-LD `Organization` + `Certification`.
- **NFR-003** : Mobile-first sur `/verify/{id}`.
- **NFR-004** : 0 JS requis pour lire la page publique (no-JS fallback).

## Success Criteria

- **SC-001** : `/rapports` liste 5 rapports + 2 attestations, download fonctionne.
- **SC-002** : Génération rapport : feedback progressif jusqu'à download.
- **SC-003** : `/verify/{abc-123}` → badge ✓ + détails corrects.
- **SC-004** : `/verify/{revoked-id}` → badge ✗ + statut révocation.
- **SC-005** : Lighthouse 95+ sur `/verify/{id}`.

## Hors-scope MVP

- Annotations PDF → post-MVP.
- Webhook notification banques → P7 interdit (pas d'intermédiaire automatisé).
- Animation cinématique page publique → post-MVP.
- Workflow "révocation par banque" → post-MVP.

## Risques et points de vigilance

- Page publique = vitrine : design irréprochable.
- Pas de crypto côté client : trust backend signature check.
- SSR `/verify` : backend down → page erreur sobre, pas crash.
- QR code : tester scan sur 5 modèles téléphones.
- Multi-tenant : `/verify/{id}` ne leak pas d'autres données (RLS via `is_public`).
