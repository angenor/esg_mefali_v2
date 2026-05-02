#!/usr/bin/env bash
# F036 — Garde-fou : interdit les valeurs arbitraires Tailwind hors tokens.
# Voir specs/036-design-system-tokens/research.md §R5.
set -euo pipefail

PATTERNS='bg-\[#|text-\[#|border-\[#|p-\[|m-\[|w-\[|h-\[|rounded-\['
TARGETS=()
for d in frontend/app frontend/components; do
  if [ -d "$d" ]; then
    TARGETS+=("$d")
  fi
done

if [ ${#TARGETS[@]} -eq 0 ]; then
  echo "check-no-arbitrary : aucun répertoire cible (frontend/app, frontend/components)."
  exit 0
fi

if grep -RnE "$PATTERNS" "${TARGETS[@]}" 2>/dev/null; then
  echo "" >&2
  echo "ERREUR : valeur arbitraire Tailwind détectée." >&2
  echo "Utiliser un token (couleurs : bg-brand-500, espacements : p-4, etc.)." >&2
  echo "Voir specs/036-design-system-tokens/data-model.md" >&2
  exit 1
fi

echo "check-no-arbitrary : OK (aucune valeur arbitraire)."
