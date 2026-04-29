"""F08 US4 — Calculateur d'effective (fonctions pures, déterministes).

Fusionne 3 couches : Fonds → Intermediaire → Offre selon les règles :
- Critères : reduce par `key` selon operator (min→max, max→min, in→intersect, ...).
- Documents : union par `document_id`.
- Frais : somme par devise (warning si mixed_currency_fees).
- Délais : somme entière (jours).
- Deadline : Offre prime sur Fonds.

Le calculateur ne dépend ni de la DB ni de Pydantic — testable unitairement.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from typing import Any

# ---------- Critères ----------

def _intersect_lists(a: list[Any], b: list[Any]) -> list[Any]:
    """Intersection ordre-stable d'après ``a``."""
    setb = set(b)
    return [x for x in a if x in setb]


def _union_lists(a: list[Any], b: list[Any]) -> list[Any]:
    seen = set()
    out: list[Any] = []
    for x in [*a, *b]:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out


def merge_criteres_two(
    upper: dict[str, Any] | None,
    lower: dict[str, Any] | None,
) -> tuple[dict[str, Any], list[str]]:
    """Fusionne deux critères de même `key` selon leur operator.

    Retourne (critere_fusionné, warnings). Si operators incompatibles, retourne
    le `lower` (priorité couche basse) et un warning.
    """
    warnings: list[str] = []
    if upper is None:
        return lower or {}, warnings
    if lower is None:
        return upper, warnings
    op_u = upper.get("operator")
    op_l = lower.get("operator")
    if op_u != op_l:
        warnings.append(f"operator_mismatch:{upper['key']}:{op_u}vs{op_l}")
        return lower, warnings
    op = op_u
    val_u, val_l = upper.get("value"), lower.get("value")
    out = dict(lower)  # garde source_id/unit du lower
    if op == "min":
        # plus restrictif = max des deux
        out["value"] = max(val_u, val_l)
    elif op == "max":
        out["value"] = min(val_u, val_l)
    elif op == "in":
        if not isinstance(val_u, list) or not isinstance(val_l, list):
            warnings.append(f"in_value_not_list:{upper['key']}")
            return lower, warnings
        intersected = _intersect_lists(val_u, val_l)
        if not intersected:
            warnings.append(f"incompatible_countries:{upper['key']}")
        out["value"] = intersected
    elif op == "not_in":
        if not isinstance(val_u, list) or not isinstance(val_l, list):
            warnings.append(f"not_in_value_not_list:{upper['key']}")
            return lower, warnings
        out["value"] = _union_lists(val_u, val_l)
    elif op == "eq":
        if val_u != val_l:
            warnings.append(f"eq_value_diverges:{upper['key']}")
        out["value"] = val_l  # priorité couche basse
    elif op == "contains":
        # ensemble qui doit contenir tous → intersect des sets requis
        if isinstance(val_u, list) and isinstance(val_l, list):
            out["value"] = _intersect_lists(val_u, val_l)
        else:
            out["value"] = val_l
    else:
        warnings.append(f"unknown_operator:{op}")
    return out, warnings


def merge_criteres(*layers: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[str]]:
    """Fusionne N couches de critères ; layer[0] est la plus générale (Fonds).

    Pour chaque ``key`` rencontrée, applique merge_criteres_two en cascade.
    """
    warnings: list[str] = []
    by_key: dict[str, dict[str, Any]] = {}
    for layer in layers:
        for c in layer or []:
            k = c["key"]
            if k not in by_key:
                by_key[k] = c
            else:
                merged, w = merge_criteres_two(by_key[k], c)
                by_key[k] = merged
                warnings.extend(w)
    return list(by_key.values()), warnings


# ---------- Documents ----------

def merge_documents(*layers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Union par document_id, dernière couche prime."""
    by_id: dict[str, dict[str, Any]] = {}
    for layer in layers:
        for d in layer or []:
            by_id[d["document_id"]] = d
    return list(by_id.values())


# ---------- Frais ----------

def sum_frais(*layers: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    """Somme les frais par clé. Détecte ``mixed_currency_fees``.

    Convention : si ``frais`` contient une clé `currency`, on vérifie la
    cohérence ; sinon on additionne champ par champ (numerics seulement).
    """
    warnings: list[str] = []
    out: dict[str, Any] = {}
    currencies: set[str] = set()
    for layer in layers:
        if not layer:
            continue
        if "currency" in layer:
            currencies.add(layer["currency"])
        for k, v in layer.items():
            if k == "currency":
                out["currency"] = v
                continue
            if isinstance(v, (int, float)):
                out[k] = round(float(out.get(k, 0)) + float(v), 6)
            elif k not in out:
                out[k] = v
    if len(currencies) > 1:
        warnings.append("mixed_currency_fees")
    return out, warnings


# ---------- Délais ----------

def sum_delais(*layers: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, int] = {}
    for layer in layers:
        if not layer:
            continue
        for k, v in layer.items():
            if isinstance(v, (int, float)):
                out[k] = int(out.get(k, 0)) + int(v)
    return out


def total_delais_jours(delais: dict[str, Any]) -> int:
    return sum(int(v) for v in delais.values() if isinstance(v, (int, float)))


# ---------- Snapshot hash ----------

def compute_snapshot_hash(payload: dict[str, Any]) -> str:
    """sha256 stable d'un payload (clés triées, JSON canonique)."""
    blob = json.dumps(payload, sort_keys=True, default=str, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


# ---------- Pipeline complet ----------

def compute_effective(
    fonds: dict[str, Any],
    intermediaire: dict[str, Any],
    offre: dict[str, Any],
) -> dict[str, Any]:
    """Pipeline complet : retourne le dict EffectiveResponse-compatible.

    Les dicts d'entrée doivent avoir les clés :
    - fonds: criteres_json, documents_requis_json, frais_json, delais_json,
             deadline, submission_mode.
    - intermediaire: criteres_json, documents_requis_json, frais_json, delais_json.
    - offre: criteres_offre_specifiques, documents_specifiques,
             frais_specifiques, delais_specifiques, accepted_languages, deadline.
    """
    warnings: list[str] = []

    fonds_criteres = _ensure_list(fonds.get("criteres_json"))
    inter_criteres = _ensure_list(intermediaire.get("criteres_json"))
    offre_criteres = _ensure_list(offre.get("criteres_offre_specifiques"))
    criteres_eff, w_c = merge_criteres(fonds_criteres, inter_criteres, offre_criteres)
    warnings.extend(w_c)

    docs_eff = merge_documents(
        _ensure_list(fonds.get("documents_requis_json")),
        _ensure_list(intermediaire.get("documents_requis_json")),
        _ensure_list(offre.get("documents_specifiques")),
    )

    frais_eff, w_f = sum_frais(
        _ensure_dict(fonds.get("frais_json")),
        _ensure_dict(intermediaire.get("frais_json")),
        _ensure_dict(offre.get("frais_specifiques")),
    )
    warnings.extend(w_f)

    delais_eff = sum_delais(
        _ensure_dict(fonds.get("delais_json")),
        _ensure_dict(intermediaire.get("delais_json")),
        _ensure_dict(offre.get("delais_specifiques")),
    )
    delais_jours = total_delais_jours(delais_eff)

    # Deadline : Offre override sinon Fonds (heredite via submission_mode)
    deadline = offre.get("deadline") or fonds.get("deadline")

    accepted_langs = offre.get("accepted_languages") or ["fr"]

    payload = {
        "criteres": criteres_eff,
        "documents": docs_eff,
        "frais": frais_eff,
        "delais": delais_eff,
        "deadline": str(deadline) if deadline else None,
        "languages": accepted_langs,
    }
    snapshot_hash = compute_snapshot_hash(payload)

    return {
        "fonds_layer": {
            "criteres": fonds_criteres,
            "documents": _ensure_list(fonds.get("documents_requis_json")),
            "frais": _ensure_dict(fonds.get("frais_json")),
            "delais": _ensure_dict(fonds.get("delais_json")),
            "referentiel": None,
            "deadline": fonds.get("deadline"),
        },
        "intermediaire_layer": {
            "criteres": inter_criteres,
            "documents": _ensure_list(intermediaire.get("documents_requis_json")),
            "frais": _ensure_dict(intermediaire.get("frais_json")),
            "delais": _ensure_dict(intermediaire.get("delais_json")),
            "referentiel": None,
            "deadline": None,
        },
        "offre_layer": {
            "criteres": offre_criteres,
            "documents": _ensure_list(offre.get("documents_specifiques")),
            "frais": _ensure_dict(offre.get("frais_specifiques")),
            "delais": _ensure_dict(offre.get("delais_specifiques")),
            "referentiel": None,
            "deadline": offre.get("deadline"),
        },
        "criteres_effectifs": criteres_eff,
        "documents_effectifs": docs_eff,
        "frais_effectifs": frais_eff,
        "delais_effectifs_jours": delais_jours,
        "referentiel_effectif": None,
        "accepted_languages": accepted_langs,
        "deadline": deadline,
        "effective_warning": warnings,
        "snapshot_hash": snapshot_hash,
    }


def _ensure_list(v: Any) -> list[Any]:
    if v is None:
        return []
    if isinstance(v, str):
        try:
            parsed = json.loads(v)
            return parsed if isinstance(parsed, list) else []
        except Exception:
            return []
    return list(v) if isinstance(v, Iterable) and not isinstance(v, dict) else []


def _ensure_dict(v: Any) -> dict[str, Any]:
    if v is None:
        return {}
    if isinstance(v, str):
        try:
            parsed = json.loads(v)
            return parsed if isinstance(parsed, dict) else {}
        except Exception:
            return {}
    return dict(v) if isinstance(v, dict) else {}
