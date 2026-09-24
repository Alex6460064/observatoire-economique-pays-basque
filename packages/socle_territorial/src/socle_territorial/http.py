"""Client HTTP commun : reprises exponentielles, user-agent explicite, téléchargements vérifiés."""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path
from typing import Any

import httpx
from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

log = logging.getLogger(__name__)

USER_AGENT = "observatoire-pays-basque/0.1 (+https://github.com/Alex6460064/observatoire-economique-pays-basque)"
DEFAULT_TIMEOUT = httpx.Timeout(60.0, connect=15.0)


def _is_retryable(exc: BaseException) -> bool:
    """Erreurs réseau et 429/5xx : on réessaie. 4xx métier : on échoue tout de suite."""
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code == 429 or exc.response.status_code >= 500
    return isinstance(exc, httpx.TransportError)


_retry = retry(
    retry=retry_if_exception(_is_retryable),
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=2, min=2, max=60),
    reraise=True,
)


def client() -> httpx.Client:
    return httpx.Client(
        headers={"User-Agent": USER_AGENT},
        timeout=DEFAULT_TIMEOUT,
        follow_redirects=True,
    )


@_retry
def get_json(url: str, params: dict[str, Any] | None = None, headers: dict[str, str] | None = None) -> Any:
    with client() as c:
        r = c.get(url, params=params, headers=headers)
        r.raise_for_status()
        return r.json()


@_retry
def download(url: str, dest: Path) -> str:
    """Télécharge ``url`` vers ``dest`` de façon atomique et renvoie le sha256 du contenu.

    Le fichier est écrit dans ``dest.part`` puis renommé : un téléchargement interrompu
    ne laisse jamais un fichier tronqué à la place d'un fichier valide.
    """
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    sha = hashlib.sha256()
    try:
        with client() as c, c.stream("GET", url) as r:
            r.raise_for_status()
            with tmp.open("wb") as f:
                for chunk in r.iter_bytes(chunk_size=1 << 20):
                    sha.update(chunk)
                    f.write(chunk)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise
    tmp.replace(dest)
    log.info("téléchargé %s -> %s", url, dest)
    return sha.hexdigest()


def sha256_file(path: Path) -> str:
    sha = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            sha.update(chunk)
    return sha.hexdigest()
