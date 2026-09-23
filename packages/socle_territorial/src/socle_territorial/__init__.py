"""Briques partagées entre les pipelines de données territoriales.

Modules :
- ``http``    : client HTTP avec reprises et téléchargement vérifié (sha256) ;
- ``journal`` : journal append-only des extractions (traçabilité, fraîcheur) ;
- ``geo``     : référentiel communes / EPCI via geo.api.gouv.fr ;
- ``bmo``     : ingestion de l'enquête Besoins en Main-d'Œuvre (France Travail) ;
- ``secret``  : secret statistique (suppression primaire et secondaire).
"""

__version__ = "0.1.0"
