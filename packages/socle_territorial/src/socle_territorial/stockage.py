"""Écriture de fichiers Parquet typés à partir de lignes Python.

Le schéma est toujours explicite : un Parquet vide garde ses colonnes et ses types,
et une dérive de type dans la source fait échouer l'écriture au lieu de se propager.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

import duckdb


def ecrire_parquet(
    lignes: Iterable[Mapping[str, Any]],
    dest: Path,
    colonnes: Mapping[str, str],
) -> int:
    """Écrit ``lignes`` dans ``dest`` (Parquet, zstd) avec le schéma ``colonnes`` (nom -> type DuckDB).

    Écriture atomique via un fichier temporaire. Renvoie le nombre de lignes écrites.
    """
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp_json = dest.with_suffix(".ndjson.part")
    tmp_parquet = dest.with_suffix(".parquet.part")
    n = 0
    with tmp_json.open("w", encoding="utf-8") as f:
        for ligne in lignes:
            f.write(json.dumps({k: ligne.get(k) for k in colonnes}, ensure_ascii=False, default=str))
            f.write("\n")
            n += 1
    cols = ", ".join(f"'{k}': '{v}'" for k, v in colonnes.items())
    select = ", ".join(f'"{k}"' for k in colonnes)
    con = duckdb.connect()
    try:
        con.execute(
            f"""
            copy (
                select {select}
                from read_json(?, format = 'newline_delimited', columns = {{{cols}}})
            ) to '{tmp_parquet.as_posix()}' (format parquet, compression zstd)
            """,
            [tmp_json.as_posix()],
        )
    finally:
        con.close()
        tmp_json.unlink(missing_ok=True)
    tmp_parquet.replace(dest)
    return n
