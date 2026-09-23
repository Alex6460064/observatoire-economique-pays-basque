"""Secret statistique pour la publication de comptages.

Deux étapes :

1. **Suppression primaire** : toute case dont la valeur est comprise entre 1 et
   ``seuil - 1`` est masquée. Un zéro n'est pas sensible (il ne désigne personne).
2. **Suppression secondaire** : une case masquée ne doit pas pouvoir être recalculée
   par différence. Pour chaque relation additive publiée (ex. « les communes somment au
   total du territoire », « les mois somment au cumul 12 mois »), si exactement une
   case de la relation est masquée, on masque aussi la plus petite case non nulle
   restante. On itère jusqu'à stabilité, car un masquage secondaire peut créer un
   nouveau cas isolé dans une autre relation.

Limite assumée (documentée dans ``docs/methodologie.md``) : l'algorithme est un
heuristique glouton, pas une optimisation (type τ-ARGUS). Il garantit qu'aucune
relation publiée ne contient une case masquée isolée ; il ne minimise pas le
nombre de cases masquées.
"""

from __future__ import annotations

from collections.abc import Hashable, Iterable, Mapping, Sequence
from typing import Literal

Motif = Literal["primaire", "secondaire"]


def appliquer_secret[K: Hashable](
    valeurs: Mapping[K, int],
    relations: Iterable[Sequence[K]],
    seuil: int,
    max_iterations: int = 100,
) -> dict[K, Motif]:
    """Renvoie les cases à masquer et le motif du masquage.

    ``valeurs``   : valeur de chaque case publiée (entiers >= 0).
    ``relations`` : groupes de cases liées par une égalité additive publiée
                    (le total fait lui-même partie du groupe).
    """
    if seuil < 2:
        raise ValueError("seuil doit valoir au moins 2")
    for k, v in valeurs.items():
        if v < 0:
            raise ValueError(f"valeur négative pour {k!r} : {v}")

    masque: dict[K, Motif] = {k: "primaire" for k, v in valeurs.items() if 0 < v < seuil}
    groupes = [list(dict.fromkeys(g)) for g in relations]
    for g in groupes:
        inconnues = [k for k in g if k not in valeurs]
        if inconnues:
            raise KeyError(f"relation référençant des cases inconnues : {inconnues[:3]}")

    for _ in range(max_iterations):
        change = False
        for g in groupes:
            masquees = [k for k in g if k in masque]
            if len(masquees) != 1:
                continue
            candidates = [k for k in g if k not in masque and valeurs[k] > 0]
            if not candidates:
                # Toutes les autres cases valent 0 : le total égale la case masquée.
                # On masque un zéro pour casser l'égalité (le total, s'il est < seuil,
                # est de toute façon masqué en primaire).
                candidates = [k for k in g if k not in masque]
            if not candidates:
                continue
            cible = min(candidates, key=lambda k: (valeurs[k], repr(k)))
            masque[cible] = "secondaire"
            change = True
        if not change:
            return masque
    raise RuntimeError("le secret secondaire ne converge pas : relations incohérentes ?")


def verifier_secret[K: Hashable](
    valeurs: Mapping[K, int],
    masque: Mapping[K, Motif],
    relations: Iterable[Sequence[K]],
    seuil: int,
) -> list[str]:
    """Contrôle indépendant de ``appliquer_secret`` : renvoie la liste des violations."""
    erreurs = []
    for k, v in valeurs.items():
        if 0 < v < seuil and k not in masque:
            erreurs.append(f"case sous le seuil publiée : {k!r}={v}")
    for g in relations:
        g = list(dict.fromkeys(g))
        if sum(1 for k in g if k in masque) == 1:
            erreurs.append(f"case masquée recalculable par différence dans {g[:4]}…")
    return erreurs
