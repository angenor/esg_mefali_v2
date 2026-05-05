// F43 T003 — Liste pays ISO 3166-1 alpha-2 ordonnée pour `CountryMultiSelect`.
//
// Source : United Nations / UN/LOCODE (https://unece.org/trade/cefact/unlocode-code-list-country-and-territory)
// + référentiels UEMOA (https://www.uemoa.int) et CEDEAO (https://ecowas.int).
//
// Ordre :
//   1. UEMOA (8 pays) — cible principale ESG Mefali
//   2. CEDEAO élargie (6 pays additionnels — hors UEMOA)
//   3. Reste du monde, alphabétique sur le label FR
//
// Les noms FR proviennent du registre ISO (édition 2022) — voir liens ci-dessus.

export interface CountryIso2 {
  /** Code ISO 3166-1 alpha-2 (2 lettres majuscules). */
  code: string
  /** Libellé français. */
  name: string
  /** Cluster d'affichage (UEMOA en haut, puis CEDEAO élargie, puis monde). */
  cluster: "uemoa" | "cedeao" | "world"
}

const UEMOA: CountryIso2[] = [
  { code: "BJ", name: "Bénin", cluster: "uemoa" },
  { code: "BF", name: "Burkina Faso", cluster: "uemoa" },
  { code: "CI", name: "Côte d'Ivoire", cluster: "uemoa" },
  { code: "GW", name: "Guinée-Bissau", cluster: "uemoa" },
  { code: "ML", name: "Mali", cluster: "uemoa" },
  { code: "NE", name: "Niger", cluster: "uemoa" },
  { code: "SN", name: "Sénégal", cluster: "uemoa" },
  { code: "TG", name: "Togo", cluster: "uemoa" },
]

const CEDEAO_EXTRA: CountryIso2[] = [
  { code: "CV", name: "Cap-Vert", cluster: "cedeao" },
  { code: "GH", name: "Ghana", cluster: "cedeao" },
  { code: "GM", name: "Gambie", cluster: "cedeao" },
  { code: "LR", name: "Libéria", cluster: "cedeao" },
  { code: "NG", name: "Nigéria", cluster: "cedeao" },
  { code: "SL", name: "Sierra Leone", cluster: "cedeao" },
]

const WORLD: CountryIso2[] = [
  { code: "DE", name: "Allemagne", cluster: "world" },
  { code: "AO", name: "Angola", cluster: "world" },
  { code: "SA", name: "Arabie saoudite", cluster: "world" },
  { code: "AR", name: "Argentine", cluster: "world" },
  { code: "AU", name: "Australie", cluster: "world" },
  { code: "AT", name: "Autriche", cluster: "world" },
  { code: "BE", name: "Belgique", cluster: "world" },
  { code: "BR", name: "Brésil", cluster: "world" },
  { code: "BI", name: "Burundi", cluster: "world" },
  { code: "CM", name: "Cameroun", cluster: "world" },
  { code: "CA", name: "Canada", cluster: "world" },
  { code: "CL", name: "Chili", cluster: "world" },
  { code: "CN", name: "Chine", cluster: "world" },
  { code: "CO", name: "Colombie", cluster: "world" },
  { code: "CG", name: "Congo (Brazzaville)", cluster: "world" },
  { code: "CD", name: "Congo (Kinshasa)", cluster: "world" },
  { code: "KR", name: "Corée du Sud", cluster: "world" },
  { code: "DK", name: "Danemark", cluster: "world" },
  { code: "EG", name: "Égypte", cluster: "world" },
  { code: "AE", name: "Émirats arabes unis", cluster: "world" },
  { code: "ES", name: "Espagne", cluster: "world" },
  { code: "US", name: "États-Unis", cluster: "world" },
  { code: "ET", name: "Éthiopie", cluster: "world" },
  { code: "FI", name: "Finlande", cluster: "world" },
  { code: "FR", name: "France", cluster: "world" },
  { code: "GA", name: "Gabon", cluster: "world" },
  { code: "GR", name: "Grèce", cluster: "world" },
  { code: "GN", name: "Guinée", cluster: "world" },
  { code: "GQ", name: "Guinée équatoriale", cluster: "world" },
  { code: "IN", name: "Inde", cluster: "world" },
  { code: "ID", name: "Indonésie", cluster: "world" },
  { code: "IE", name: "Irlande", cluster: "world" },
  { code: "IL", name: "Israël", cluster: "world" },
  { code: "IT", name: "Italie", cluster: "world" },
  { code: "JP", name: "Japon", cluster: "world" },
  { code: "KE", name: "Kenya", cluster: "world" },
  { code: "LU", name: "Luxembourg", cluster: "world" },
  { code: "MG", name: "Madagascar", cluster: "world" },
  { code: "MA", name: "Maroc", cluster: "world" },
  { code: "MU", name: "Maurice", cluster: "world" },
  { code: "MR", name: "Mauritanie", cluster: "world" },
  { code: "MX", name: "Mexique", cluster: "world" },
  { code: "MZ", name: "Mozambique", cluster: "world" },
  { code: "NL", name: "Pays-Bas", cluster: "world" },
  { code: "NO", name: "Norvège", cluster: "world" },
  { code: "NZ", name: "Nouvelle-Zélande", cluster: "world" },
  { code: "PL", name: "Pologne", cluster: "world" },
  { code: "PT", name: "Portugal", cluster: "world" },
  { code: "QA", name: "Qatar", cluster: "world" },
  { code: "GB", name: "Royaume-Uni", cluster: "world" },
  { code: "RW", name: "Rwanda", cluster: "world" },
  { code: "RU", name: "Russie", cluster: "world" },
  { code: "ST", name: "Sao Tomé-et-Principe", cluster: "world" },
  { code: "SG", name: "Singapour", cluster: "world" },
  { code: "SE", name: "Suède", cluster: "world" },
  { code: "CH", name: "Suisse", cluster: "world" },
  { code: "TZ", name: "Tanzanie", cluster: "world" },
  { code: "TD", name: "Tchad", cluster: "world" },
  { code: "TR", name: "Turquie", cluster: "world" },
  { code: "TN", name: "Tunisie", cluster: "world" },
  { code: "UG", name: "Ouganda", cluster: "world" },
  { code: "ZA", name: "Afrique du Sud", cluster: "world" },
  { code: "ZM", name: "Zambie", cluster: "world" },
  { code: "ZW", name: "Zimbabwe", cluster: "world" },
]

// Tri WORLD une seule fois (locale FR) — UEMOA et CEDEAO conservent leur ordre métier.
const WORLD_SORTED = [...WORLD].sort((a, b) =>
  a.name.localeCompare(b.name, "fr", { sensitivity: "base" }),
)

export const COUNTRIES_ISO2: ReadonlyArray<CountryIso2> = [
  ...UEMOA,
  ...CEDEAO_EXTRA,
  ...WORLD_SORTED,
]

const CODE_INDEX = new Map(COUNTRIES_ISO2.map((c) => [c.code, c]))

export function isValidIso2(code: string): boolean {
  return CODE_INDEX.has(code)
}

export function findCountry(code: string): CountryIso2 | null {
  return CODE_INDEX.get(code) ?? null
}
