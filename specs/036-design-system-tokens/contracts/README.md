# Contracts — Design System & Tokens

**Feature**: 036-design-system-tokens
**Date**: 2026-05-02
**Status**: N/A

Cette feature ne crée **aucun contrat d'API** (HTTP, GraphQL, CLI, RPC).
Elle est intégralement frontend (Nuxt 4 + Tailwind v4) et son livrable est :

- un fichier de tokens CSS (`frontend/app/assets/css/tokens.css`),
- un mapping `@theme` dans `frontend/app/assets/css/main.css`,
- un composable Vue (`useReducedMotion`),
- une page de référence `/dev/design-system` (DEV only),
- des polices, illustrations et logos statiques sous `frontend/public/`.

Le « contrat » exposé est donc un **catalogue de tokens nommés** documenté dans
[../data-model.md](../data-model.md). Toute feature aval (037–052) doit consommer
ces tokens via les classes utilitaires Tailwind (`bg-brand-500`, `p-4`, `rounded-2xl`,
`shadow-md`, `text-text`, `text-text-muted`, etc.) ou via `var(--…)` direct en CSS.

## Stabilité du catalogue

- Les **noms** de tokens sont stables et constituent l'API publique consommée par
  les features aval.
- Les **valeurs** peuvent évoluer (ajustement de la nuance brand, calibrage des
  ombres, etc.) sans casser les consommateurs.
- L'ajout de nouveaux tokens est rétrocompatible.
- La suppression ou le renommage d'un token est une **breaking change** et doit
  faire l'objet d'une feature dédiée (refactor coordonné).

## Pas de tests de contrat ici

Aucun test de contrat (Pact, OpenAPI, etc.) n'est généré pour cette feature.
La validation est :

- visuelle (page `/dev/design-system`),
- automatique (script `check-no-arbitrary.sh`, audit contraste, Lighthouse),
- unitaire (`useReducedMotion.spec.ts`).
