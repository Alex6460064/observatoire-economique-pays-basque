"""Configuration du pipeline : fichier ``config/observatoire.yml`` + variables d'environnement."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import date
from functools import cached_property
from pathlib import Path
from typing import Any

import yaml

# ``absolute`` et non ``resolve`` : on conserve le chemin d'import tel quel (jonction ou
# lien symbolique courts), ce qui évite les chemins > 260 caractères sous Windows.
RACINE = Path(__file__).absolute().parent.parent
FICHIER_CONFIG = RACINE / "config" / "observatoire.yml"


def premier_du_mois(d: date, decalage_mois: int = 0) -> date:
    """Premier jour du mois de ``d`` décalé de ``decalage_mois`` (négatif = passé)."""
    n = d.year * 12 + (d.month - 1) + decalage_mois
    return date(n // 12, n % 12 + 1, 1)


@dataclass(frozen=True)
class Config:
    brut: dict[str, Any]
    perimetre: str
    data_dir: Path
    aujourd_hui: date

    @classmethod
    def charger(cls, perimetre: str | None = None, aujourd_hui: date | None = None) -> Config:
        brut = yaml.safe_load(FICHIER_CONFIG.read_text(encoding="utf-8"))
        perimetre = perimetre or os.environ.get("OBS_PERIMETRE") or brut["perimetre_defaut"]
        if perimetre not in brut["perimetres"]:
            raise ValueError(f"périmètre inconnu : {perimetre} (connus : {list(brut['perimetres'])})")
        data_dir = Path(os.environ.get("OBS_DATA_DIR", RACINE / "data")).resolve()
        return cls(brut, perimetre, data_dir, aujourd_hui or date.today())

    @property
    def p(self) -> dict[str, Any]:
        return self.brut["parametres"]

    @property
    def sources(self) -> dict[str, str]:
        return self.brut["sources"]

    @property
    def def_perimetre(self) -> dict[str, Any]:
        return self.brut["perimetres"][self.perimetre]

    @cached_property
    def debut_historique(self) -> date:
        return premier_du_mois(self.aujourd_hui, -self.p["historique_mois"])

    def dbt_vars(self) -> dict[str, Any]:
        """Paramètres transmis aux modèles dbt (``var(...)``) : une seule source de vérité."""
        return {
            "date_reference": self.aujourd_hui.isoformat(),
            "debut_historique": self.debut_historique.isoformat(),
            "seuil_secret": self.p["seuil_secret"],
            "mois_provisoires_sirene": self.p["mois_provisoires_sirene"],
            "mois_provisoires_bodacc": self.p["mois_provisoires_bodacc"],
        }

    # Arborescence des données (hors git)
    @property
    def raw(self) -> Path:
        return self.data_dir / "raw"

    @property
    def journal_path(self) -> Path:
        return self.data_dir / "journal" / "extractions.jsonl"

    @property
    def warehouse(self) -> Path:
        return self.data_dir / "warehouse" / "observatoire.duckdb"

    @property
    def historique_dir(self) -> Path:
        """Historique agrégé et non sensible, persisté entre runs (branche `donnees` en CI)."""
        return Path(os.environ.get("OBS_HISTORIQUE_DIR", self.data_dir / "historique"))

    @property
    def export_dir(self) -> Path:
        return RACINE / "site" / "src" / "data"
