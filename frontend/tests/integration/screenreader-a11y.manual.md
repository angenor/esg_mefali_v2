# Check-list manuelle — lecteur d'écran (SC-009)

> Réf : tasks T102 · spec.md SC-009 (au moins un atome modal et un atome listbox testés au lecteur d'écran)
> Outils : VoiceOver (macOS, `Cmd+F5`) · NVDA (Windows, gratuit) · Orca (Linux).

## Préparation

```bash
make frontend
# http://localhost:3001/dev/components
```

Activer le lecteur d'écran AVANT d'ouvrir la page. Tester avec les raccourcis clavier seuls (pas de souris).

## 1. UiModal

- [ ] Ouvrir la modale via le bouton "Ouvrir modal".
- [ ] Le lecteur annonce le rôle (`dialog`) et le titre (libellé `aria-labelledby` du header).
- [ ] Le focus est piégé : `Tab`/`Shift+Tab` reste à l'intérieur.
- [ ] `Esc` ferme la modale, le focus retourne au déclencheur.
- [ ] Le contenu post-fermeture est annoncé (focus + contexte).

## 2. UiCombobox

- [ ] Naviguer jusqu'à un combobox.
- [ ] Le lecteur annonce le rôle (`combobox`), `aria-expanded`, et l'option active (`aria-activedescendant`).
- [ ] Taper pour filtrer les options ; le lecteur annonce le nombre de résultats ou l'option en cours.
- [ ] `↑`/`↓` change l'option active — annoncée.
- [ ] `Enter` sélectionne — annoncée.
- [ ] `Esc` ferme la liste sans sélection.

## 3. (Bonus) UiToast

- [ ] Déclencher un toast `severity='error'` — annoncé via `aria-live="assertive"`.
- [ ] Toast `severity='info'` — annoncé via `aria-live="polite"` (sans interrompre).

## 4. (Bonus) UiRadioGroup

- [ ] Le lecteur annonce le `radiogroup` puis l'option sélectionnée.
- [ ] `↑`/`↓` change la sélection — annoncée.

## Reporting

À consigner dans la PR de F37 / commit dédié :
- OS + lecteur d'écran (version).
- Date + testeur.
- Captures audio si disponibles (sinon transcription textuelle).
- Anomalies trouvées — créer une issue Github "ui-primitives a11y" si présentes.
