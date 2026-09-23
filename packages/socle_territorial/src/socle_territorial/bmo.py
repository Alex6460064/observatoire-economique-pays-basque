"""Enquête Besoins en Main-d'Œuvre (BMO, France Travail).

Sources vérifiées (spike du 23/09/2026) :
- millésimes : jeu data.gouv.fr ``561fa564c751df4f2acdbb48`` (licence ``fr-lo``), un
  fichier xlsx (ou zip contenant un xlsx) par année ;
- composition communale des bassins : fichier ``Bassins_d'emploi_AAAA.xlsx`` publié sur
  statistiques.francetravail.org (page méthodologie du millésime).

Le format varie d'une année à l'autre (ordre des colonnes, suffixe ``BE23``/``BE26``,
nomenclature FAP2009 jusqu'en 2023 puis FAP2021) : les colonnes sont donc repérées
par leur nom, jamais par leur position. Les cellules ``*`` sont couvertes par le secret
statistique de France Travail : elles deviennent ``None`` (et non 0).
"""

from __future__ import annotations

import re
import unicodedata
import zipfile
from pathlib import Path
from typing import Any

from python_calamine import CalamineWorkbook

from socle_territorial import http

DATASET_BMO = "561fa564c751df4f2acdbb48"

COLONNES_BMO = {
    "annee": "INTEGER",
    "code_metier": "VARCHAR",
    "libelle_metier": "VARCHAR",
    "code_famille": "VARCHAR",
    "libelle_famille": "VARCHAR",
    "code_departement": "VARCHAR",
    "code_bassin": "VARCHAR",
    "libelle_bassin": "VARCHAR",
    "projets": "INTEGER",
    "projets_difficiles": "INTEGER",
    "projets_saisonniers": "INTEGER",
    "projets_secret": "BOOLEAN",
}

COLONNES_BASSINS = {
    "code_commune": "VARCHAR",
    "libelle_commune": "VARCHAR",
    "code_bassin": "VARCHAR",
    "libelle_bassin": "VARCHAR",
    "millesime_zonage": "INTEGER",
}


def _cle(s: Any) -> str:
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "_", s).strip("_")


def lister_millesimes(annee_min: int) -> list[dict[str, Any]]:
    """Millésimes disponibles sur data.gouv.fr, du plus ancien au plus récent."""
    ds = http.get_json(f"https://www.data.gouv.fr/api/1/datasets/{DATASET_BMO}/")
    out = []
    for r in ds["resources"]:
        m = re.search(r"(20\d\d)", r["title"])
        if not m or int(m.group(1)) < annee_min:
            continue
        out.append({"annee": int(m.group(1)), "url": r["url"], "titre": r["title"]})
    return sorted(out, key=lambda x: x["annee"])


def _xlsx_depuis(path: Path) -> Path:
    if path.suffix.lower() != ".zip":
        return path
    with zipfile.ZipFile(path) as z:
        noms = [n for n in z.namelist() if n.lower().endswith((".xlsx", ".xls"))]
        if len(noms) != 1:
            raise ValueError(f"{path.name} : attendu 1 classeur dans l'archive, trouvé {noms}")
        cible = path.with_suffix(Path(noms[0]).suffix)
        cible.write_bytes(z.read(noms[0]))
        return cible


def _entier(v: Any) -> int | None:
    if v is None or v == "" or str(v).strip() == "*":
        return None
    return int(float(v))


def _code(v: Any) -> str | None:
    """Les codes lus par calamine arrivent parfois en float (``7539.0``)."""
    if v is None or v == "":
        return None
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    return str(v).strip()


def lire_bmo(path: Path, departements: set[str] | None = None) -> list[dict[str, Any]]:
    """Lit un fichier BMO (xlsx ou zip) et renvoie les lignes normalisées.

    ``departements`` restreint aux départements utiles (le fichier national fait ~50 000 lignes).
    """
    wb = CalamineWorkbook.from_path(str(_xlsx_depuis(path)))
    feuilles = [s for s in wb.sheet_names if "open_data" in _cle(s)]
    if len(feuilles) != 1:
        raise ValueError(f"{path.name} : feuille de données introuvable parmi {wb.sheet_names}")
    lignes = wb.get_sheet_by_name(feuilles[0]).to_python()
    entete = [_cle(h) for h in lignes[0]]

    def idx(*motifs: str) -> int:
        for i, h in enumerate(entete):
            if any(re.fullmatch(m, h) for m in motifs):
                return i
        raise ValueError(f"{path.name} : colonne {motifs} absente de {entete}")

    i_annee = idx("annee")
    i_code_met, i_lib_met = idx("code_metier_bmo"), idx("nom_metier_bmo")
    i_fam, i_lib_fam = idx("famille_met"), idx("lbl_fam_met")
    i_dep = idx("dept")
    i_be, i_lib_be = idx(r"be\d\d"), idx(r"nombe\d\d")
    i_met, i_xmet, i_smet = idx("met"), idx("xmet"), idx("smet")

    out = []
    for r in lignes[1:]:
        if not any(r):
            continue
        dep = _code(r[i_dep])
        if departements and dep not in departements:
            continue
        projets = _entier(r[i_met])
        out.append(
            {
                "annee": _entier(r[i_annee]),
                "code_metier": _code(r[i_code_met]),
                "libelle_metier": r[i_lib_met],
                "code_famille": _code(r[i_fam]),
                "libelle_famille": r[i_lib_fam],
                "code_departement": dep,
                "code_bassin": _code(r[i_be]),
                "libelle_bassin": r[i_lib_be],
                "projets": projets,
                "projets_difficiles": _entier(r[i_xmet]),
                "projets_saisonniers": _entier(r[i_smet]),
                "projets_secret": projets is None,
            }
        )
    return out


def lire_bassins(path: Path) -> list[dict[str, Any]]:
    """Lit la table communes -> bassins d'emploi BMO (``Bassins_d'emploi_AAAA.xlsx``)."""
    wb = CalamineWorkbook.from_path(str(path))
    lignes = wb.get_sheet_by_name(wb.sheet_names[0]).to_python()
    entete = [_cle(h) for h in lignes[0]]
    try:
        i_com, i_lib = entete.index("code_commune"), entete.index("lib_commune")
        i_be = next(i for i, h in enumerate(entete) if re.fullmatch(r"code_bassin_\d{4}", h))
        i_lib_be = next(i for i, h in enumerate(entete) if re.fullmatch(r"lib_bassin_\d{4}", h))
    except (ValueError, StopIteration) as exc:
        raise ValueError(f"{path.name} : en-tête inattendu {entete}") from exc
    millesime = int(entete[i_be][-4:])
    return [
        {
            "code_commune": _code(r[i_com]).zfill(5),
            "libelle_commune": r[i_lib],
            "code_bassin": _code(r[i_be]),
            "libelle_bassin": r[i_lib_be],
            "millesime_zonage": millesime,
        }
        for r in lignes[1:]
        if r[i_com]
    ]
