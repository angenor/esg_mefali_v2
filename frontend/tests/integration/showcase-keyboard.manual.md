# Check-list manuelle — `dev/components` showcase clavier + tap targets

> Réf : tasks T098 · spec.md SC-003 (parcours clavier 100 %) · SC-004 (tap targets ≥ 44×44 px sur ≤ 768 px)
> Lien : voir `quickstart.md` § 6.

## Préparation

```bash
make frontend
# Ouvrir http://localhost:3001/dev/components
```

Outils utiles :
- DevTools → Inspector → mesurer les boutons / contrôles (`Computed > width / height`).
- DevTools → Device Toolbar → 375 × 667 px (iPhone SE).
- Outline focus visible : tester en gardant la fenêtre au clavier seul.

## 1. Parcours clavier (SC-003) — desktop

Lancer Tab depuis l'URL bar et descendre toute la page sans souris.

Pour chaque atome, vérifier :

- [ ] **UiButton** : Tab atteint chaque variante ; Enter/Space déclenchent click.
- [ ] **UiInput / UiTextarea / UiNumber** : Tab focus ; saisie OK ; Esc dans `clearable` rend le focus à l'input ; pas de piège.
- [ ] **UiSelect** : Tab → ouverture par Enter/Space ; ↑↓ navigation ; Enter sélectionne ; Esc ferme.
- [ ] **UiCombobox** : Tab focus le champ, recherche en tapant ; ↑↓ active items ; Enter sélectionne ; Esc ferme.
- [ ] **UiMultiSelect** : Backspace retire le dernier chip si l'input est vide ; Tab quitte le champ proprement.
- [ ] **UiRadioGroup** : Tab entre dans le groupe (sélection ou premier item) ; ↑↓ change de sélection ; Tab sort.
- [ ] **UiCheckboxGroup** : Tab atteint chaque case ; Espace toggle.
- [ ] **UiSwitch** : Tab focus ; Espace OU Enter toggle.
- [ ] **UiSlider single** : ←→ Home End PageUp PageDown s'appliquent ; aria-valuenow change.
- [ ] **UiSlider range** : Tab entre les deux thumbs ; chaque thumb répond aux flèches sans dépasser l'autre.
- [ ] **UiDatePicker / UiDateRangePicker** : Tab focus ; saisie clavier ISO acceptée.
- [ ] **UiFileUpload (mode dropzone)** : Tab focus la dropzone ; Enter/Espace ouvre le picker natif.
- [ ] **UiModal** : ouvrir → focus piégé ; Esc ferme ; Tab/Shift+Tab cycle ; restauration du focus au déclencheur.
- [ ] **UiPopover** : Tab focus le trigger ; Enter/Space toggle ; Esc ferme.
- [ ] **UiTooltip** : focus du trigger affiche le tooltip ; blur le retire ; pas de piège de focus.
- [ ] **UiToast** : la notification ne casse pas le focus trap d'une `Modal` ouverte ; le bouton Fermer est atteignable au Tab quand le toast a le focus.
- [ ] Aucun élément capturant Esc qui empêche un parent de réagir (sauf modale au sommet de la pile).

## 2. Tap targets (SC-004) — mobile 375 px

- [ ] DevTools → Toolbar device → 375 × 667.
- [ ] Pour chaque atome interactif : largeur ≥ 44 px et hauteur ≥ 44 px.
- [ ] Cas particuliers à vérifier visuellement :
  - [ ] `UiButton size="sm"` : ≥ 36 px (autorisé en `sm`, mais sur mobile préférer `md`).
  - [ ] `UiSwitch size="sm"` : track 36 px (acceptable, vérifier la zone de hit étendue).
  - [ ] `UiTag.remove` (×) : zone de hit ≥ 24 px (le `min-width/min-height: 24px` reste sous le seuil → noter en debt si la tag est utilisée dans une zone tactile).
  - [ ] `UiInput.clear` (×) : idem.
- [ ] Espacement entre cibles ≥ 8 px sur les rangées denses (`.row` du showcase).

## 3. Lecteur d'écran (rappel)

Couvert par `screenreader-a11y.manual.md` (T102) — vérifier au moins `UiModal` et `UiCombobox`.

## Reporting

Reporter dans le commit / PR :
- Chemin testé : `/dev/components` à la révision `git rev-parse HEAD`.
- Date + nom du testeur.
- Résultats (✅ / ❌ + capture si problème).
