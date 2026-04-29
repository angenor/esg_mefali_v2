"""F11 — Taxonomie sectorielle MVP + pays UEMOA/CEDEAO.

Liste maison (~50 codes) sourcée par l'équipe ESG Mefali. Peut migrer plus
tard vers F09 (catalog référentiel) — voir clarify-11.log Q3.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Sector:
    code: str
    label: str


SECTORS: tuple[Sector, ...] = (
    Sector("agro_culture_vivriere", "Agriculture — culture vivrière"),
    Sector("agro_culture_rente", "Agriculture — culture de rente"),
    Sector("agro_elevage", "Élevage"),
    Sector("agro_aquaculture", "Aquaculture / pêche"),
    Sector("agro_transformation", "Agro-transformation"),
    Sector("agro_distribution", "Distribution agricole"),
    Sector("artisanat_textile", "Artisanat — textile"),
    Sector("artisanat_cuir", "Artisanat — cuir / maroquinerie"),
    Sector("artisanat_bois", "Artisanat — bois / ameublement"),
    Sector("artisanat_metallerie", "Artisanat — métallerie"),
    Sector("commerce_detail", "Commerce de détail"),
    Sector("commerce_gros", "Commerce de gros"),
    Sector("commerce_import_export", "Import / export"),
    Sector("services_restauration", "Services — restauration"),
    Sector("services_hotellerie", "Services — hôtellerie"),
    Sector("services_tourisme", "Services — tourisme"),
    Sector("services_education", "Services — éducation"),
    Sector("services_sante", "Services — santé"),
    Sector("services_juridiques", "Services — juridiques"),
    Sector("services_conseil", "Services — conseil / audit"),
    Sector("services_compta", "Services — comptabilité"),
    Sector("services_marketing", "Services — marketing / communication"),
    Sector("services_logistique", "Services — logistique / transport"),
    Sector("services_evenementiel", "Services — événementiel"),
    Sector("services_securite", "Services — sécurité privée"),
    Sector("services_nettoyage", "Services — nettoyage / hygiène"),
    Sector("tic_developpement", "TIC — développement logiciel"),
    Sector("tic_hosting", "TIC — hébergement / cloud"),
    Sector("tic_telecoms", "TIC — télécoms"),
    Sector("tic_medias", "TIC — médias / contenu"),
    Sector("fintech", "Fintech"),
    Sector("microfinance", "Microfinance"),
    Sector("banque_assurance", "Banque / assurance"),
    Sector("industrie_materiaux", "Industrie — matériaux de construction"),
    Sector("industrie_chimie", "Industrie — chimie"),
    Sector("industrie_emballage", "Industrie — emballage"),
    Sector("industrie_textile", "Industrie — textile / confection"),
    Sector("industrie_pharma", "Industrie — pharma / cosmétique"),
    Sector("energie_solaire", "Énergie — solaire"),
    Sector("energie_biomasse", "Énergie — biomasse"),
    Sector("energie_eolien", "Énergie — éolien"),
    Sector("eau_assainissement", "Eau et assainissement"),
    Sector("dechets_recyclage", "Déchets / recyclage"),
    Sector("mobilite_transport", "Mobilité / transport routier"),
    Sector("btp_construction", "BTP — construction"),
    Sector("btp_genie_civil", "BTP — génie civil"),
    Sector("immobilier", "Immobilier"),
    Sector("mines_carrieres", "Mines et carrières"),
    Sector("foret_bois", "Forêt / exploitation du bois"),
    Sector("autre", "Autre / non classé"),
)


_SECTOR_BY_CODE: dict[str, Sector] = {s.code: s for s in SECTORS}


def get_sector(code: str) -> Sector | None:
    return _SECTOR_BY_CODE.get(code)


def all_sector_codes() -> frozenset[str]:
    return frozenset(_SECTOR_BY_CODE)


# UEMOA: BJ, BF, CI, GW, ML, NE, SN, TG
# CEDEAO additionnels: CV, GM, GH, GN, LR, NG, SL
UEMOA_CEDEAO_ISO2: frozenset[str] = frozenset(
    {
        "BJ", "BF", "CI", "GW", "ML", "NE", "SN", "TG",
        "CV", "GM", "GH", "GN", "LR", "NG", "SL",
    }
)


# Devises acceptées pour les montants money (peg FCFA-EUR 655.957 — F05).
ALLOWED_CURRENCIES: frozenset[str] = frozenset({"XOF", "EUR", "USD"})
