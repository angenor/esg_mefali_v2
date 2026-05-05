# Manuel — `/dev/form-candidature` (F37, US1)

> Page DEV-only ; protégée par `middleware: dev-only` (404 en production).

## Préparation

```bash
cd frontend && pnpm dev --port 3001
# ouvrir http://localhost:3001/dev/form-candidature
```

## Check-list clavier (SC-003)

- [ ] `Tab` parcourt les 7 contrôles dans l'ordre du DOM (Raison sociale → CA → Secteur → Pays → Date → Documents → Envoyer).
- [ ] `Shift+Tab` revient en arrière sans piéger le focus.
- [ ] Combobox « Pays » : `↑` `↓` déplacent l'item actif, `Enter` sélectionne, `Esc` ferme.
- [ ] Dropzone Documents : `Enter` ou `Espace` ouvre le file picker.
- [ ] Bouton « Envoyer » : `Enter` soumet (déclenche `onSubmit`).

## Check-list lecteur d'écran

- [ ] Combobox annonce `aria-expanded`, `role="listbox"`, items `role="option"`.
- [ ] Erreurs : tout `role="alert"` est lu.
- [ ] Champ requis : l'astérisque visuel est doublé d'un libellé clair.

## Check-list mobile (SC-004) — viewport 375 px

- [ ] Aucune cible interactive < 44 × 44 px (boutons, dropzone, options Combobox).
- [ ] Pas de scroll horizontal sur la page entière.
- [ ] `UiNumber` affiche le clavier numérique (`inputmode="decimal"`).

## Captures attendues

Stocker les captures dans `frontend/tests/integration/.artifacts/form-candidature/`
(non commit) lors d'une session manuelle ; conserver uniquement la check-list ici.
