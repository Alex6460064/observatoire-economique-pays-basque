"""Journal des extractions : une ligne JSON par extraction, jamais réécrite.

Le journal est la mémoire du pipeline : il permet d'afficher la fraîcheur de chaque
source, de savoir quel millésime a servi à produire un chiffre, et de détecter une
chute anormale de volumétrie d'un run à l'autre. Il ne contient aucune donnée
individuelle, seulement des métadonnées d'extraction.
"""

from __future__ import annotations

import json
import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


@dataclass
class Extraction:
    source: str
    """Identifiant stable de la source, ex. ``bodacc``, ``sirene_etablissements``."""
    millesime: str | None = None
    """Version de la donnée source (date du stock, année d'enquête, mois de parution…)."""
    url: str | None = None
    lignes: int | None = None
    sha256: str | None = None
    statut: str = "en_cours"
    erreur: str | None = None
    debut: str = field(default_factory=lambda: datetime.now(UTC).isoformat(timespec="seconds"))
    fin: str | None = None
    duree_s: float | None = None
    details: dict[str, Any] = field(default_factory=dict)


class Journal:
    def __init__(self, path: Path) -> None:
        self.path = path

    def ecrire(self, e: Extraction) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(e), ensure_ascii=False) + "\n")

    def lire(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        with self.path.open(encoding="utf-8") as f:
            return [json.loads(line) for line in f if line.strip()]

    def derniere_reussie(self, source: str) -> dict[str, Any] | None:
        ok = [e for e in self.lire() if e["source"] == source and e["statut"] == "ok"]
        return ok[-1] if ok else None

    @contextmanager
    def extraction(self, source: str, **kwargs: Any) -> Iterator[Extraction]:
        """Enregistre l'extraction en ``ok`` ou ``echec`` même si une exception remonte."""
        e = Extraction(source=source, **kwargs)
        t0 = time.monotonic()
        try:
            yield e
            e.statut = "ok"
        except BaseException as exc:
            e.statut = "echec"
            e.erreur = f"{type(exc).__name__}: {exc}"[:500]
            raise
        finally:
            e.fin = datetime.now(UTC).isoformat(timespec="seconds")
            e.duree_s = round(time.monotonic() - t0, 2)
            self.ecrire(e)
