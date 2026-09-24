"""Référentiel géographique via l'API Découpage administratif (geo.api.gouv.fr).

La liste des communes n'est jamais codée en dur : elle est lue au Code officiel
géographique (COG) en vigueur à chaque run, à partir du code SIREN de l'EPCI.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable
from typing import Any

from socle_territorial import http

GEO_API = "https://geo.api.gouv.fr"
CHAMPS_COMMUNE = "nom,code,codesPostaux,population,codeDepartement,codeEpci"

COLONNES_COMMUNE = {
    "code_commune": "VARCHAR",
    "nom_commune": "VARCHAR",
    "code_departement": "VARCHAR",
    "code_epci": "VARCHAR",
    "population": "INTEGER",
    "codes_postaux": "VARCHAR[]",
}


def _aplatir(c: dict[str, Any]) -> dict[str, Any]:
    return {
        "code_commune": c["code"],
        "nom_commune": c["nom"],
        "code_departement": c.get("codeDepartement"),
        "code_epci": c.get("codeEpci"),
        "population": c.get("population"),
        "codes_postaux": sorted(c.get("codesPostaux") or []),
    }


_CODE_DEPARTEMENT = re.compile(r"\d{2,3}|2[AB]")


def valider_departements(codes: Iterable[str]) -> list[str]:
    """Codes triés, vérifiés avant insertion dans une requête (SQL DuckDB, ODSQL du BODACC)."""
    deps = sorted(codes)
    invalides = [d for d in deps if not _CODE_DEPARTEMENT.fullmatch(d)]
    if invalides:
        raise ValueError(f"Codes département invalides : {invalides}")
    return deps


def epci(code_epci: str) -> dict[str, Any]:
    return http.get_json(f"{GEO_API}/epcis/{code_epci}", {"fields": "nom,code,codesDepartements,population"})


def communes_epci(code_epci: str) -> list[dict[str, Any]]:
    data = http.get_json(f"{GEO_API}/epcis/{code_epci}/communes", {"fields": CHAMPS_COMMUNE})
    if not data:
        raise ValueError(f"Aucune commune renvoyée pour l'EPCI {code_epci} : code erroné ?")
    return [_aplatir(c) for c in data]


def communes_departement(code_dep: str) -> list[dict[str, Any]]:
    data = http.get_json(f"{GEO_API}/departements/{code_dep}/communes", {"fields": CHAMPS_COMMUNE})
    if not data:
        raise ValueError(f"Aucune commune renvoyée pour le département {code_dep}")
    return [_aplatir(c) for c in data]


_ARTICLES = re.compile(r"^(LE|LA|LES|L) ")
_SAINT = re.compile(r"\b(ST|STE)\b")


def normaliser_nom(nom: str | None) -> str:
    """Clé de rapprochement tolérante pour les libellés de commune saisis librement.

    ``"St-Jean-de-Luz"``, ``"SAINT JEAN DE LUZ"`` et ``"Saint-Jean-de-Luz"`` donnent la même clé.
    Les articles initiaux sont retirés (``"L'Hôpital-Saint-Blaise"`` -> ``"HOPITAL SAINT BLAISE"``).
    """
    if not nom:
        return ""
    s = unicodedata.normalize("NFKD", nom).encode("ascii", "ignore").decode().upper()
    s = re.sub(r"[^A-Z0-9]+", " ", s).strip()
    s = re.sub(r"\bCEDEX\b.*$", "", s).strip()
    s = _SAINT.sub(lambda m: "SAINTE" if m.group(1) == "STE" else "SAINT", s)
    s = _ARTICLES.sub("", s)
    return s


def contours_epci(code_epci: str) -> dict[str, Any]:
    """Contours des communes d'un EPCI (GeoJSON, WGS84)."""
    fc = http.get_json(
        f"{GEO_API}/epcis/{code_epci}/communes",
        {"format": "geojson", "geometry": "contour", "fields": "code,nom"},
    )
    if fc.get("type") != "FeatureCollection" or not fc.get("features"):
        raise ValueError(f"contours vides pour l'EPCI {code_epci}")
    return fc


def _perpendiculaire(p: list[float], a: list[float], b: list[float]) -> float:
    (x, y), (x1, y1), (x2, y2) = p, a, b
    dx, dy = x2 - x1, y2 - y1
    if dx == dy == 0:
        return ((x - x1) ** 2 + (y - y1) ** 2) ** 0.5
    return abs(dy * x - dx * y + x2 * y1 - y2 * x1) / (dx * dx + dy * dy) ** 0.5


def _douglas_peucker(points: list[list[float]], tolerance: float) -> list[list[float]]:
    if len(points) < 3:
        return points
    pile, garder = [(0, len(points) - 1)], {0, len(points) - 1}
    while pile:
        debut, fin = pile.pop()
        idx, dmax = None, tolerance
        for i in range(debut + 1, fin):
            d = _perpendiculaire(points[i], points[debut], points[fin])
            if d > dmax:
                idx, dmax = i, d
        if idx is not None:
            garder.add(idx)
            pile += [(debut, idx), (idx, fin)]
    return [points[i] for i in sorted(garder)]


def simplifier(fc: dict[str, Any], tolerance: float = 0.0002, decimales: int = 4) -> dict[str, Any]:
    """Allège un GeoJSON pour l'affichage web (Douglas-Peucker + arrondi), sans dépendance.

    Tolérance en degrés (0,0002° ≈ 20 m) : invisible à l'échelle d'une carte de communes.
    Un anneau n'est jamais réduit sous 4 points (anneau fermé valide).
    """

    def anneau(r: list[list[float]]) -> list[list[float]]:
        s = _douglas_peucker(r, tolerance)
        s = s if len(s) >= 4 else r
        return [[round(x, decimales), round(y, decimales)] for x, y in s]

    def geometrie(g: dict[str, Any]) -> dict[str, Any]:
        if g["type"] == "Polygon":
            return {"type": "Polygon", "coordinates": [anneau(r) for r in g["coordinates"]]}
        if g["type"] == "MultiPolygon":
            return {"type": "MultiPolygon", "coordinates": [[anneau(r) for r in p] for p in g["coordinates"]]}
        return g

    return {
        "type": "FeatureCollection",
        "features": [{**f, "geometry": geometrie(f["geometry"])} for f in fc["features"]],
    }
