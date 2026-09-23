"""Construction des cubes publiés et de leurs relations additives, puis application du secret.

Pour un indicateur, les cases publiées sont :

- par mois  : chaque commune et le total du périmètre (tous secteurs) ;
              chaque section NAF au total du périmètre ;
              (défaillances) chaque type de procédure au total du périmètre ;
- sur 12 mois glissants (deux fenêtres : les 12 derniers mois consolidés et les 12 précédents) :
              commune × section, commune × tous secteurs, total × section, total × division ;
              (défaillances) chaque type de procédure au total du périmètre.

Chaque égalité additive que ces cases permettent d'écrire est déclarée comme relation,
afin que le secret secondaire empêche tout recalcul par différence, y compris dans le
temps (12 mois = somme des mois).
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date

from socle_territorial.secret import Motif, appliquer_secret, verifier_secret

from ingestion.config import premier_du_mois

TOTAL = "TOTAL"
# Clé d'une case : (type_periode, periode, geo, niveau_secteur, code_secteur)
#   type_periode : "mois" | "12m" ; periode : "AAAA-MM" (mois, ou dernier mois de la fenêtre)
#   niveau_secteur : "T" (tous) | "S" (section) | "D" (division) | "P" (type de procédure)
Cle = tuple[str, str, str, str, str]


@dataclass(frozen=True)
class Evenement:
    mois: date
    code_commune: str
    code_section: str
    code_division: str
    detail: str | None
    valeur: int


@dataclass
class Cube:
    valeurs: dict[Cle, int]
    relations: list[list[Cle]]
    masque: dict[Cle, Motif]


def _p(m: date) -> str:
    return m.strftime("%Y-%m")


def fenetres(dernier_consolide: date, premier_disponible: date) -> list[tuple[str, list[date]]]:
    """Fenêtres de 12 mois se terminant au dernier mois consolidé et 12 mois avant, si couvertes."""
    out = []
    for decalage in (0, -12):
        fin = premier_du_mois(dernier_consolide, decalage)
        mois = [premier_du_mois(fin, -i) for i in range(11, -1, -1)]
        if mois[0] >= premier_disponible:
            out.append((_p(fin), mois))
    return out


def construire_cube(
    evenements: Iterable[Evenement],
    mois_publies: list[date],
    mois_consolides: list[date],
    communes: list[str],
    sections: list[str],
    divisions_par_section: dict[str, list[str]],
    types_detail: list[str] | None = None,
) -> Cube:
    ev = list(evenements)
    valeurs: dict[Cle, int] = defaultdict(int)
    geos = [*communes, TOTAL]
    divisions = [d for s in sections for d in divisions_par_section.get(s, [])]

    # Initialisation dense (les zéros participent aux relations).
    for m in mois_publies:
        p = _p(m)
        for g in geos:
            valeurs[("mois", p, g, "T", "")] = 0
        for s in sections:
            valeurs[("mois", p, TOTAL, "S", s)] = 0
        for t in types_detail or []:
            valeurs[("mois", p, TOTAL, "P", t)] = 0
    wins = fenetres(max(mois_consolides), min(mois_publies)) if mois_consolides else []
    for w, _ in wins:
        for g in geos:
            valeurs[("12m", w, g, "T", "")] = 0
            for s in sections:
                valeurs[("12m", w, g, "S", s)] = 0
        for d in divisions:
            valeurs[("12m", w, TOTAL, "D", d)] = 0
        for t in types_detail or []:
            valeurs[("12m", w, TOTAL, "P", t)] = 0

    publies = set(mois_publies)
    for e in ev:
        if e.mois not in publies:
            continue
        p = _p(e.mois)
        for g in (e.code_commune, TOTAL):
            valeurs[("mois", p, g, "T", "")] += e.valeur
        valeurs[("mois", p, TOTAL, "S", e.code_section)] += e.valeur
        if types_detail is not None:
            valeurs[("mois", p, TOTAL, "P", e.detail or "autre")] += e.valeur
        for w, mois_w in wins:
            if e.mois in mois_w:
                for g in (e.code_commune, TOTAL):
                    valeurs[("12m", w, g, "T", "")] += e.valeur
                    valeurs[("12m", w, g, "S", e.code_section)] += e.valeur
                valeurs[("12m", w, TOTAL, "D", e.code_division)] += e.valeur
                if types_detail is not None:
                    valeurs[("12m", w, TOTAL, "P", e.detail or "autre")] += e.valeur

    inconnues = {k for k in valeurs if k[3] in "SD" and k[4] not in {*sections, *divisions}}
    if inconnues:
        raise ValueError(f"secteurs hors référentiel : {sorted(inconnues)[:3]}")

    rel: list[list[Cle]] = []
    for m in mois_publies:
        p = _p(m)
        tot = ("mois", p, TOTAL, "T", "")
        rel.append([*(("mois", p, c, "T", "") for c in communes), tot])
        rel.append([*(("mois", p, TOTAL, "S", s) for s in sections), tot])
        if types_detail:
            rel.append([*(("mois", p, TOTAL, "P", t) for t in types_detail), tot])
    for w, mois_w in wins:
        for g in geos:  # lignes : sections -> tous secteurs, pour chaque géographie
            rel.append([*(("12m", w, g, "S", s) for s in sections), ("12m", w, g, "T", "")])
        for s in ("", *sections):  # colonnes : communes -> total, pour chaque secteur
            niv = "T" if s == "" else "S"
            rel.append([*(("12m", w, c, niv, s) for c in communes), ("12m", w, TOTAL, niv, s)])
        for s in sections:  # divisions -> section
            ds = divisions_par_section.get(s, [])
            if ds:
                rel.append([*(("12m", w, TOTAL, "D", d) for d in ds), ("12m", w, TOTAL, "S", s)])
        for g in geos:  # temps : mois -> 12 mois
            rel.append([*(("mois", _p(m), g, "T", "") for m in mois_w), ("12m", w, g, "T", "")])
        for s in sections:
            rel.append([*(("mois", _p(m), TOTAL, "S", s) for m in mois_w), ("12m", w, TOTAL, "S", s)])
        if types_detail:
            rel.append([*(("12m", w, TOTAL, "P", t) for t in types_detail), ("12m", w, TOTAL, "T", "")])
            for t in types_detail:
                rel.append([*(("mois", _p(m), TOTAL, "P", t) for m in mois_w), ("12m", w, TOTAL, "P", t)])
    return Cube(dict(valeurs), rel, {})


def secretiser(cube: Cube, seuil: int) -> Cube:
    cube.masque = appliquer_secret(cube.valeurs, cube.relations, seuil)
    erreurs = verifier_secret(cube.valeurs, cube.masque, cube.relations, seuil)
    if erreurs:
        raise AssertionError(f"secret statistique non respecté : {erreurs[:3]}")
    return cube
