# Sources de données — résultats du spike

> Spike réalisé le 23/09/2026 par interrogation directe de chaque source (requêtes et comptages
> reproduits dans le code d'ingestion). Chaque point « à vérifier » du cadrage est tranché ici.

## Synthèse

| Source | Accès retenu | Volumétrie (périmètre) | Jointure | Fraîcheur | Licence |
|---|---|---|---|---|---|
| geo.api.gouv.fr | API, sans clé | 158 communes CAPB ; 545 communes du 64 | code commune INSEE | COG en vigueur | Licence Ouverte 2.0 |
| Sirene stock (INSEE) | Parquet data.gouv.fr, lecture distante DuckDB | 496 021 établissements (dép. 64), 363 439 unités légales, 120 869 liens de succession | SIREN, SIRET, code commune | mensuelle (1er du mois) | Licence Ouverte 2.0 |
| BODACC (DILA) | API Opendatasoft `exports/json`, sans clé | ~15 000 annonces/an (dép. 64, 5 familles) | SIREN (`registre`), code postal + ville | jours ouvrés | Licence Ouverte 2.0 |
| BMO (France Travail) | xlsx/zip data.gouv.fr | 314 à 430 lignes/an (dép. 64) | code bassin | annuelle (avril) | Licence Ouverte (`fr-lo`) |
| Zonage bassins BMO | xlsx statistiques.francetravail.org | 34 990 communes | code commune | annuelle | idem BMO |
| NAF rév. 2 (INSEE) | xls insee.fr | 732 sous-classes, 88 divisions, 21 sections | code NAF | stable | Licence Ouverte 2.0 |
| Jev (TypeSafe) | API, clé (optionnelle) | ~800 annonces classées au 1er run | — | à la demande | service tiers |

## Points « à vérifier » du cadrage : réponses

| Point | Réponse vérifiée |
|---|---|
| Code SIREN de l'EPCI et nombre de communes | **200067106**, « CA du Pays Basque », **158 communes** (geo.api.gouv.fr, 23/09/2026). |
| Formats du stock Sirene | CSV zippé **et Parquet** ; Parquet retenu (StockEtablissement 2,2 Go, StockUniteLegale 709 Mo). |
| Limite d'appels de l'API Sirene | **Non utilisée en V1** (voir ADR-0004) : le stock mensuel suffit à des indicateurs mensuels, et le BODACC couvre le quotidien. Pas de secret ni de quota à gérer. |
| Licence BMO | `fr-lo` sur data.gouv.fr = Licence Ouverte. |
| Statut de diffusion partielle Sirene | Champ `statutDiffusionEtablissement` / `statutDiffusionUniteLegale`, valeurs `O` (diffusible) et `P` (partielle). Pour `P`, l'INSEE masque l'adresse (`codePostalEtablissement = "[ND]"`) mais **conserve le code commune et l'activité**. Règle retenue : compter en agrégat, ne jamais afficher d'unité. 13 % du stock, ~30 % des créations récentes. |

## geo.api.gouv.fr

- `GET /epcis/200067106/communes` : liste des communes au COG en vigueur. La population
  sommée (329 856) diffère de la population de l'EPCI publiée par la même API (325 721) :
  millésimes de population différents ; on utilise la population communale.
- `GET /departements/64/communes` : sert au rapprochement des adresses BODACC (voir plus bas).
- `format=geojson&geometry=contour` : contours (1,7 Mo), simplifiés à 363 Ko pour le site.

## Sirene (fichiers stock)

- Jeu data.gouv.fr `base-sirene-des-entreprises-et-de-leurs-etablissements-siren-siret`,
  ressources repérées par leur titre (« Sirene : Fichier StockEtablissement - … (format parquet) »).
- **Lecture distante** : DuckDB lit les Parquet par requêtes HTTP Range, colonnes utiles
  seulement (~570 Mo transférés au lieu de 2,9 Go) ; extraction du 64 en ~1 min 30.
- Nomenclatures d'activité : `NAFRev2` pour 396 035 établissements du 64, mais aussi `NAF1993`,
  `NAFRev1`, `NAP` (établissements anciens). Une colonne NAF 2025 (`activitePrincipaleNAF25…`)
  est présente ; extraite, pas encore exploitée.
- Anomalies observées : dates de création postérieures à l'extraction (jusqu'en 2027) et une
  date en l'an 8 ; établissements du dernier mois très incomplets (enregistrement tardif).
- **Transferts/reprises** : `StockEtablissementLiensSuccession` (`continuiteEconomique`) permet
  d'exclure les nouveaux SIRET qui ne sont pas des créations (~21 % des nouveaux SIRET du périmètre).
- API Sirene (INSEE) : non utilisée en V1.

## BODACC

- Endpoint : `https://bodacc-datadila.opendatasoft.com/api/explore/v2.1/catalog/datasets/annonces-commerciales`.
  50,7 millions d'annonces au total ; 609 257 pour le 64 depuis 2008. L'endpoint `records` est
  plafonné en pagination ; l'endpoint **`exports/json`** renvoie un mois complet en une requête.
- Familles utiles : `creation`, `immatriculation`, `vente`, `collective`, `radiation`
  (+ `dpc` dépôts des comptes, `modification`, `conciliation` non utilisés).
- **Localisation** : ni code commune INSEE ni NAF. Champs `ville` et `cp` (adresse du siège ou
  de l'établissement). Le code postal seul est ambigu : `64270` couvre des communes basques et
  béarnaises (Salies-de-Béarn, Puyoo…). Rapprochement code postal + libellé normalisé contre
  toutes les communes du département : **98,5 %** des annonces localisées ainsi, 99,4 % au total
  avec les repli (code postal unique, siège Sirene).
- **SIREN** : champ `registre` (forme compacte et espacée alternées). Présent sur 98,9 % des
  annonces valides ; 93 % des procédures collectives (les autres : associations, etc.).
  **Taux de jointure avec Sirene : 98,8 %**.
- Procédures collectives : `jugement.famille` = « Jugement d'ouverture » et `jugement.nature`
  (liquidation, redressement, sauvegarde, extension…) ; date du jugement dans `jugement.date`.
- Ventes : `acte.vente.categorieVente` ; la catégorie « Autre achat, apport, attribution » est
  à 94 % constituée de fusions et scissions (exclues des cessions).
- Rectificatifs et annulations : `parutionavisprecedent` → identifiant de l'annonce visée
  (`lettre + n° parution + n° annonce`), retrouvée dans 171 cas sur 209 (les autres sont
  antérieurs à la fenêtre).
- **Données personnelles** : noms, prénoms, nationalité, adresses des entrepreneurs
  individuels figurent dans `listepersonnes`. Minimisation dès l'ingestion : rien de nominatif
  n'est écrit sur disque.
- Vagues de radiations : certains mois concentrent des radiations publiées en lot (ex.
  avril 2026 : 526 radiations d'entrepreneurs individuels du périmètre contre quelques dizaines les autres mois).

## Enquête BMO

- Jeu data.gouv.fr `561fa564c751df4f2acdbb48`, un fichier par millésime (2015 → 2026 ;
  2026 publié le 21/04/2026). Formats hétérogènes : xlsx direct ou zip, ordre des colonnes
  variable, colonne de bassin suffixée par l'année (`BE23`…`BE26`) → lecture par nom de colonne.
- Nomenclature métier FAP2009 jusqu'en 2023, FAP2021 ensuite (codes `A0Z40` → `A0X40`).
- Secret France Travail : `*` sur 8 à 14 % des lignes (effectifs) et 22 à 35 % (difficiles).
- Dans le 64, deux bassins : **7539 « Pays Basque »** et **7538 « Béarn »**, codes stables de
  2023 à 2026.
- Zonage communal 2026 (`Bassins_d'emploi_2026.xlsx`, servi via une redirection vers
  `images.pr-rooms.com`) : le bassin Pays Basque compte 131 communes, dont **122 de la CAPB
  (96,2 % de sa population)**, 8 communes landaises et Gestas (Béarn) ; **36 communes souletines**
  de la CAPB sont dans le bassin Béarn.

## NAF rév. 2

`naf2008_5_niveaux.xls` (correspondance sous-classe → division → section) et les listes de
libellés `naf2008_liste_n1.xls` / `n2.xls` sur insee.fr.

## Jev (TypeSafe) — enrichissement optionnel

API `POST /v1/systemone`, modèle figé `jev-1.13.0`, 0,042 $ par million de tokens en entrée,
~3 800 tokens par annonce (88 options), soit environ 0,05 $ pour 300 annonces ; débit mesuré de 78 annonces/s
avec 32 requêtes en parallèle. Utilisé uniquement pour classer le texte d'activité des annonces
sans NAF. Évaluation : `docs/evaluation_jev.md`.
