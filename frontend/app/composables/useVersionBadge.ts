// F04 — VersionBadge text formatter (T112, US7).
// Renders the French label: "Évalué selon Référentiel <name> v<version> du <dd/mm/yyyy>".

export function formatVersionBadge(
  referentielName: string,
  version: number,
  validFrom: string,
): string {
  const date = new Date(validFrom);
  const formatted = new Intl.DateTimeFormat('fr-FR', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
  }).format(date);
  return `Évalué selon Référentiel ${referentielName} v${version} du ${formatted}`;
}

export function useVersionBadge() {
  return { formatVersionBadge };
}
