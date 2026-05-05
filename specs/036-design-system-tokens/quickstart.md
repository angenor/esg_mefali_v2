# Quickstart — Design System & Tokens

**Feature**: 036-design-system-tokens
**Date**: 2026-05-02

Procédure manuelle pour vérifier les fondations design en local.

---

## 1. Prérequis

```bash
# Postgres dockerisé (utile uniquement si on lance aussi le backend ; pas requis pour ce feature)
make db-up

# Frontend installé
make setup
```

## 2. Démarrer le frontend

```bash
make frontend
# équivalent : cd frontend && pnpm dev --port 3001
```

Attendre `Local: http://localhost:3001`.

## 3. Ouvrir la page de référence

Naviguer sur **http://localhost:3001/dev/design-system**.

Vérifier la présence des sections suivantes, **sans erreur dans la console** :

- Palette neutre (11 nuances)
- Palette brand (9 nuances)
- Sémantiques (success / warning / danger / info — 3 nuances chacune)
- Surface / texte / bordure / focus-ring
- Typographie (échelle xs → 5xl, line-height corps + titre, démo `tabular-nums`)
- Spacing (1, 2, 3, 4, 6, 8, 12, 16, 24)
- Radius (sm → full)
- Shadows (xs → xl)
- Motion (boutons démo `fast` / `base` / `slow`, indicateur `prefers-reduced-motion`)
- Focus (suite de boutons et inputs : Tab pour parcourir)
- États désactivés
- Iconographie (Heroicons outline)
- Logo horizontal + symbole + favicon
- Empty states (3 illustrations)

## 4. Vérifications manuelles

### 4.1 Navigation clavier (SC-007)

- Mettre le focus dans la page (`Tab`).
- Parcourir tous les éléments interactifs jusqu'au bout.
- Chaque élément MUST exposer un anneau de focus visible (≈2 px brand, offset 2 px).

### 4.2 Reduced motion (SC-008)

- macOS : *Réglages → Accessibilité → Affichage → Réduire les animations*.
- Linux GNOME : *Settings → Accessibility → Reduce Animation*.
- Windows : *Paramètres → Accessibilité → Effets visuels → Effets d'animation*.

Recharger `/dev/design-system`. Les boutons motion ne doivent plus jouer d'animation perceptible. L'indicateur affiché doit passer à `prefers-reduced-motion: reduce ✅`.

### 4.3 Mode sombre tokens prêts (User Story 3)

Dans la console DevTools :

```js
document.documentElement.setAttribute('data-theme', 'dark')
```

L'UI doit basculer en sombre sans erreur (les tokens dark se résolvent). Pour revenir : `removeAttribute('data-theme')`.

### 4.4 Audit contraste (SC-003)

- Installer l'extension **axe DevTools** (Chrome / Firefox).
- Lancer un scan sur `/dev/design-system`.
- Aucun item « contrast » ne doit échouer.

### 4.5 Audit Lighthouse Best Practices (SC-009)

- DevTools → onglet *Lighthouse*.
- Cocher *Best Practices* (au minimum), profil mobile.
- Lancer l'audit. Score Best Practices ≥ 95.

### 4.6 Pas de console.* en prod (FR-023)

```bash
cd frontend && pnpm build
grep -rn "console\." .output/public 2>/dev/null
# attendu : aucun résultat applicatif (les libs minifiées peuvent en contenir)
```

## 5. Tests automatisés

### 5.1 Unit (Vitest)

```bash
cd frontend && pnpm vitest run tests/unit/useReducedMotion.spec.ts
```

Attendu : tous les tests passent (mock `matchMedia`, état initial, event `change`).

### 5.2 Garde-fou « pas de valeur arbitraire » (SC-002)

```bash
bash frontend/scripts/check-no-arbitrary.sh
echo "exit=$?"
# attendu : exit=0 (aucune valeur arbitraire détectée dans le code applicatif)
```

Pour vérifier que le garde-fou attrape bien une violation, ajouter temporairement `<div class="bg-[#ff0000]" />` dans une page → le script doit `exit 1`.

### 5.3 Bundle CSS prod (SC-005)

```bash
cd frontend && pnpm build
ls -lh .output/public/_nuxt/*.css
gzip -c .output/public/_nuxt/*.css | wc -c
# attendu : taille gzip < 30720 octets (30 kB)
```

## 6. Performance LCP (SC-004) — manuel

- DevTools → onglet *Performance*.
- Throttling : *Slow 4G* + CPU 4× slowdown.
- Recharger une page applicative typique (par ex. `/login`).
- Onglet *Network* : la requête `Inter-Regular.woff2` doit être en *high priority preload*.
- Mesurer LCP. Cible : < 1500 ms.

## 7. Critères d'acceptation rapides

| Critère                                                  | Comment vérifier              |
|----------------------------------------------------------|-------------------------------|
| SC-001 (changement token propage)                        | éditer `tokens.css`, F5       |
| SC-002 (pas de valeur arbitraire)                        | `check-no-arbitrary.sh`       |
| SC-003 (contraste AA)                                    | axe DevTools                  |
| SC-004 (LCP < 1.5 s)                                     | Lighthouse mobile             |
| SC-005 (CSS < 30 kB)                                     | `gzip -c … \| wc -c`          |
| SC-006 (showcase sans erreur)                            | DevTools console              |
| SC-007 (focus visible)                                   | Tab clavier                   |
| SC-008 (reduced-motion)                                  | toggle OS                     |
| SC-009 (Lighthouse ≥ 95)                                 | Lighthouse                    |
| SC-010 (productivité dev)                                | revue manuelle                |

## 8. Dépannage

| Symptôme                              | Solution                                                    |
|---------------------------------------|-------------------------------------------------------------|
| 404 sur `/dev/design-system` en prod  | comportement attendu (FR-022).                              |
| Inter ne se charge pas                | vérifier `frontend/public/fonts/Inter-Regular.woff2`, MIME `font/woff2` |
| Tokens dark ne s'appliquent pas       | confirmer que `tokens.css` est importé **avant** `@import "tailwindcss"` |
| Lighthouse < 95                       | ouvrir le rapport, traiter chaque item ; souvent : preload manquant ou favicon SVG manquant |
