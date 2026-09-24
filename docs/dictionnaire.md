# Dictionnaire de données

> Généré par `uv run obs documenter` depuis le manifeste dbt et l'entrepôt DuckDB. Ne pas modifier à la main.

Chaîne : `raw` (Parquet, `obs ingerer`) → `staging` → `intermediate` → `marts` (dbt) → fichiers publiés (`obs exporter`, secret statistique).

## Fichiers publiés (site/src/data)

| Fichier | Contenu |
|---|---|
| `indicateurs.csv` | Toutes les cases publiées, après secret statistique. Colonnes : `indicateur`, `type_periode` (mois \| 12m), `periode` (AAAA-MM ; fin de fenêtre pour 12m), `geo` (code commune ou TOTAL), `niveau_secteur` (T tous \| S section \| D division \| P type de procédure), `secteur`, `valeur` (vide si masquée), `secret` (p primaire \| s secondaire), `provisoire` (0/1). Une case absente vaut 0. |
| `communes.csv` | Communes du périmètre : code, nom, population, bassin BMO. |
| `communes.geojson` | Contours simplifiés des communes (geo.api.gouv.fr). |
| `secteurs.csv` | Sections et divisions NAF rév. 2 (+ ZZ non déterminé, <section>_ND division non déterminée). |
| `mois.csv` | Mois publiés et statut par source (consolide \| provisoire \| non_couvert). |
| `bmo_familles.csv` | Projets BMO par bassin × année × famille de métiers. |
| `bmo_metiers.csv` | Projets BMO par métier, dernier millésime. |
| `bmo_recouvrement.json` | Recouvrement entre le périmètre et les bassins BMO. |
| `meta.json` | Périmètre, période, sources avec millésime et date d'extraction. |
| `qualite.json` | Fraîcheur, résultats des tests, métriques qualité, secret, évaluation Jev. |
| `historique_*.csv` | Historique agrégé des runs (séries au total du périmètre, métriques qualité). |

## Couche staging — sources renommées, typées, minimisées (vues)

### `staging.stg_bmo__bassins_communes`

Composition communale des bassins d'emploi BMO (zonage France Travail).

| Colonne | Type | Description |
|---|---|---|
| `code_commune` | VARCHAR |  |
| `libelle_commune` | VARCHAR |  |
| `code_bassin` | VARCHAR |  |
| `libelle_bassin` | VARCHAR |  |
| `millesime_zonage` | INTEGER |  |

### `staging.stg_bmo__projets`

Enquête BMO, lignes métier × bassin des départements du périmètre, tous millésimes ingérés.

| Colonne | Type | Description |
|---|---|---|
| `annee` | INTEGER |  |
| `code_metier` | VARCHAR |  |
| `libelle_metier` | VARCHAR |  |
| `code_famille` | VARCHAR |  |
| `libelle_famille` | VARCHAR |  |
| `code_departement` | VARCHAR |  |
| `code_bassin` | VARCHAR |  |
| `libelle_bassin` | VARCHAR |  |
| `projets` | INTEGER | Nombre de projets de recrutement ; null si secret statistique France Travail. |
| `projets_difficiles` | INTEGER |  |
| `projets_saisonniers` | INTEGER |  |
| `projets_secret` | BOOLEAN |  |
| `nomenclature_metier` | VARCHAR |  |

### `staging.stg_bodacc__annonces`

Annonces BODACC minimisées (aucun nom, aucune adresse), fenêtre d'historique.

| Colonne | Type | Description |
|---|---|---|
| `id_annonce` | VARCHAR | Identifiant BODACC : lettre de publication + n° de parution + n° d'annonce. |
| `publication` | VARCHAR |  |
| `numero_parution` | VARCHAR |  |
| `date_parution` | DATE |  |
| `numero_annonce` | INTEGER |  |
| `type_avis` | VARCHAR |  |
| `famille_avis` | VARCHAR |  |
| `departement` | VARCHAR |  |
| `tribunal` | VARCHAR |  |
| `ville` | VARCHAR |  |
| `code_postal` | VARCHAR |  |
| `ville_normalisee` | VARCHAR |  |
| `siren` | VARCHAR |  |
| `nb_siren` | INTEGER |  |
| `type_personne` | VARCHAR |  |
| `jugement_famille` | VARCHAR |  |
| `jugement_nature` | VARCHAR |  |
| `jugement_date` | DATE |  |
| `categorie_vente` | VARCHAR |  |
| `categorie_creation` | VARCHAR |  |
| `id_avis_precedent` | VARCHAR |  |
| `activite` | VARCHAR |  |

### `staging.stg_enrichissement__secteurs_jev`

_(sans description)_

| Colonne | Type | Description |
|---|---|---|
| `id_annonce` | VARCHAR |  |
| `modele` | VARCHAR |  |
| `niveau` | VARCHAR |  |
| `code_division` | VARCHAR |  |
| `code_section` | VARCHAR |  |
| `confiance` | DOUBLE |  |
| `masse_section` | DOUBLE |  |

### `staging.stg_geo__codes_postaux`

Couples (code postal, commune) des départements du périmètre, avec libellé normalisé pour le rapprochement BODACC.

| Colonne | Type | Description |
|---|---|---|
| `code_postal` | VARCHAR |  |
| `code_commune` | VARCHAR |  |
| `nom_commune` | VARCHAR |  |
| `nom_normalise` | VARCHAR |  |

### `staging.stg_geo__communes_perimetre`

Communes du périmètre étudié (COG en vigueur, geo.api.gouv.fr).

| Colonne | Type | Description |
|---|---|---|
| `code_commune` | VARCHAR | Code officiel géographique (INSEE) de la commune. |
| `nom_commune` | VARCHAR |  |
| `code_departement` | VARCHAR |  |
| `code_epci` | VARCHAR |  |
| `population` | INTEGER | Population municipale selon geo.api.gouv.fr. |
| `codes_postaux` | VARCHAR[] |  |

### `staging.stg_naf__secteurs`

Sous-classes NAF rév. 2 avec division et section (libellés INSEE).

| Colonne | Type | Description |
|---|---|---|
| `code_naf` | VARCHAR |  |
| `code_division` | VARCHAR |  |
| `libelle_division` | VARCHAR |  |
| `code_section` | VARCHAR |  |
| `libelle_section` | VARCHAR |  |

### `staging.stg_sirene__etablissements`

Établissements Sirene des départements du périmètre (sans colonne nominative ni adresse). Stock mensuel complété par l'API Sirene, dont la version l'emporte.

| Colonne | Type | Description |
|---|---|---|
| `siret` | VARCHAR | Identifiant de l'établissement (14 chiffres). Usage interne uniquement, jamais publié. |
| `siren` | VARCHAR |  |
| `nic` | VARCHAR |  |
| `statut_diffusion` | VARCHAR | O = diffusible ; P = diffusion partielle (compté en agrégat, jamais affiché individuellement). |
| `date_creation` | DATE |  |
| `tranche_effectifs` | VARCHAR |  |
| `est_siege` | BOOLEAN |  |
| `code_commune` | VARCHAR | Code commune INSEE de l'établissement. |
| `etat_administratif` | VARCHAR |  |
| `date_debut_periode` | DATE |  |
| `nomenclature_activite` | VARCHAR |  |
| `code_naf` | VARCHAR |  |
| `code_naf25` | VARCHAR |  |
| `est_employeur` | BOOLEAN |  |
| `date_dernier_traitement` | TIMESTAMP |  |

### `staging.stg_sirene__liens_succession`

Liens de succession entre établissements (transferts, reprises) dont le successeur est dans le périmètre départemental. Une ligne par lien : version API, sinon la plus récemment traitée du stock.

| Colonne | Type | Description |
|---|---|---|
| `siret_predecesseur` | VARCHAR |  |
| `siret_successeur` | VARCHAR |  |
| `date_lien` | DATE |  |
| `est_transfert_siege` | BOOLEAN |  |
| `est_continuite_economique` | BOOLEAN |  |

### `staging.stg_sirene__unites_legales`

Unités légales Sirene ayant au moins un établissement dans les départements du périmètre. Stock mensuel complété par l'API Sirene, dont la version l'emporte.

| Colonne | Type | Description |
|---|---|---|
| `siren` | VARCHAR |  |
| `statut_diffusion` | VARCHAR |  |
| `est_purgee` | BOOLEAN |  |
| `date_creation` | DATE |  |
| `categorie_juridique` | BIGINT |  |
| `est_entrepreneur_individuel` | BOOLEAN |  |
| `code_naf` | VARCHAR |  |
| `etat_administratif` | VARCHAR |  |
| `siret_siege` | VARCHAR |  |
| `categorie_entreprise` | VARCHAR |  |

## Couche intermédiaire — règles métier (tables)

### `intermediate.int_bodacc__annonces_valides`

Annonces BODACC valides (annulations retirées, rectificatifs substitués) et classées par événement.

| Colonne | Type | Description |
|---|---|---|
| `id_annonce` | VARCHAR |  |
| `publication` | VARCHAR |  |
| `numero_parution` | VARCHAR |  |
| `date_parution` | DATE |  |
| `numero_annonce` | INTEGER |  |
| `type_avis` | VARCHAR |  |
| `famille_avis` | VARCHAR |  |
| `departement` | VARCHAR |  |
| `tribunal` | VARCHAR |  |
| `ville` | VARCHAR |  |
| `code_postal` | VARCHAR |  |
| `ville_normalisee` | VARCHAR |  |
| `siren` | VARCHAR |  |
| `nb_siren` | INTEGER |  |
| `type_personne` | VARCHAR |  |
| `jugement_famille` | VARCHAR |  |
| `jugement_nature` | VARCHAR |  |
| `jugement_date` | DATE |  |
| `categorie_vente` | VARCHAR |  |
| `categorie_creation` | VARCHAR |  |
| `id_avis_precedent` | VARCHAR |  |
| `activite` | VARCHAR |  |
| `evenement` | VARCHAR | immatriculation \| radiation \| cession (vente de fonds hors restructurations) \| restructuration (fusion, scission, apport) \| ouverture_procedure (jugement d'ouverture de sauvegarde, redressement ou liquidation, hors extension) \| autre_procedure \| transfert_entrant. |
| `type_procedure` | VARCHAR |  |
| `date_evenement` | DATE | Date du jugement pour les procédures collectives (si cohérente), date de parution sinon. |
| `date_jugement_incoherente` | BOOLEAN |  |

### `intermediate.int_bodacc__evenements_localises`

Annonces valides rattachées à une commune (cp + libellé, cp unique, ou siège Sirene) et à un code NAF.

| Colonne | Type | Description |
|---|---|---|
| `id_annonce` | VARCHAR |  |
| `date_parution` | DATE |  |
| `date_evenement` | DATE |  |
| `mois` | DATE |  |
| `evenement` | VARCHAR |  |
| `type_procedure` | VARCHAR |  |
| `type_personne` | VARCHAR |  |
| `siren` | VARCHAR |  |
| `departement` | VARCHAR |  |
| `date_jugement_incoherente` | BOOLEAN |  |
| `code_commune` | VARCHAR |  |
| `methode_localisation` | VARCHAR |  |
| `code_naf_sirene` | VARCHAR |  |
| `siren_trouve_sirene` | BOOLEAN |  |
| `activite` | VARCHAR |  |
| `source_secteur` | VARCHAR | Origine du secteur : sirene \| jev_division \| jev_section (attribution Jev, TypeSafe) \| non_determine. |
| `code_division` | VARCHAR |  |
| `code_section` | VARCHAR |  |

### `intermediate.int_sirene__creations_entreprises`

Nouvelles unités légales dont le siège est dans le périmètre.

| Colonne | Type | Description |
|---|---|---|
| `siren` | VARCHAR |  |
| `date_creation` | DATE |  |
| `mois` | DATE |  |
| `code_commune` | VARCHAR |  |
| `code_naf` | VARCHAR |  |
| `est_entrepreneur_individuel` | BOOLEAN |  |
| `est_reprise_ou_transfert` | BOOLEAN |  |
| `date_creation_future` | BOOLEAN |  |

### `intermediate.int_sirene__creations_etablissements`

Établissements du périmètre créés dans la fenêtre d'historique, avec repérage des reprises/transferts.

| Colonne | Type | Description |
|---|---|---|
| `siret` | VARCHAR |  |
| `siren` | VARCHAR |  |
| `code_commune` | VARCHAR |  |
| `date_creation` | DATE |  |
| `mois` | DATE |  |
| `code_naf` | VARCHAR |  |
| `est_siege` | BOOLEAN |  |
| `statut_diffusion` | VARCHAR |  |
| `est_reprise_ou_transfert` | BOOLEAN |  |
| `date_creation_future` | BOOLEAN |  |

## Couche marts — tables prêtes à l'analyse, source unique de l'export public

### `marts.dim_communes`

Communes du périmètre avec population et bassin d'emploi BMO.

| Colonne | Type | Description |
|---|---|---|
| `code_commune` | VARCHAR | Code commune INSEE (COG en vigueur). |
| `nom_commune` | VARCHAR | Libellé officiel. |
| `code_departement` | VARCHAR |  |
| `code_epci` | VARCHAR |  |
| `population` | INTEGER | Population municipale (geo.api.gouv.fr). |
| `code_bassin_bmo` | VARCHAR | Bassin d'emploi BMO de rattachement (zonage France Travail). |
| `libelle_bassin_bmo` | VARCHAR |  |

### `marts.dim_mois`

Mois publiés et statut de consolidation (consolide / provisoire / non_couvert) par famille de source.

| Colonne | Type | Description |
|---|---|---|
| `mois` | DATE |  |
| `periode` | VARCHAR |  |
| `statut_sirene` | VARCHAR |  |
| `statut_bodacc` | VARCHAR |  |

### `marts.dim_secteurs`

Divisions et sections NAF rév. 2, plus la modalité ZZ « Activité non déterminée ».

| Colonne | Type | Description |
|---|---|---|
| `code_division` | VARCHAR |  |
| `libelle_division` | VARCHAR |  |
| `code_section` | VARCHAR |  |
| `libelle_section` | VARCHAR |  |

### `marts.fct_evenements_mensuels`

Comptages bruts par indicateur × mois × commune × division NAF. Table interne : le secret statistique est appliqué à l'export, jamais ici.


| Colonne | Type | Description |
|---|---|---|
| `indicateur` | VARCHAR | creations_etablissements \| creations_entreprises \| immatriculations_rcs \| radiations_rcs \| cessions \| defaillances. Définitions : docs/methodologie.md. |
| `mois` | DATE |  |
| `code_commune` | VARCHAR |  |
| `code_section` | VARCHAR |  |
| `code_division` | VARCHAR |  |
| `detail` | VARCHAR | Pour les défaillances : liquidation \| redressement \| sauvegarde \| autre. |
| `valeur` | BIGINT | Nombre d'événements. |

### `marts.mart_bmo_familles`

Projets de recrutement BMO par bassin × année × famille de métiers (minorants si secret France Travail).

| Colonne | Type | Description |
|---|---|---|
| `annee` | INTEGER |  |
| `code_bassin` | VARCHAR |  |
| `libelle_bassin` | VARCHAR |  |
| `code_famille` | VARCHAR |  |
| `libelle_famille` | VARCHAR |  |
| `projets` | HUGEINT | Somme des projets non secrets. |
| `projets_difficiles` | HUGEINT |  |
| `base_taux_difficile` | HUGEINT |  |
| `projets_saisonniers` | HUGEINT |  |
| `base_taux_saisonnier` | HUGEINT |  |
| `nb_metiers` | BIGINT |  |
| `nb_metiers_secret` | BIGINT | Nombre de lignes métier couvertes par le secret France Travail. |

### `marts.mart_bmo_metiers`

Projets BMO par métier pour les bassins du périmètre.

| Colonne | Type | Description |
|---|---|---|
| `annee` | INTEGER |  |
| `code_bassin` | VARCHAR |  |
| `libelle_bassin` | VARCHAR |  |
| `code_famille` | VARCHAR |  |
| `libelle_famille` | VARCHAR |  |
| `code_metier` | VARCHAR |  |
| `libelle_metier` | VARCHAR |  |
| `nomenclature_metier` | VARCHAR |  |
| `projets` | INTEGER |  |
| `projets_difficiles` | INTEGER |  |
| `projets_saisonniers` | INTEGER |  |
| `projets_secret` | BOOLEAN |  |

### `marts.mart_bmo_recouvrement`

Recouvrement communes / population entre le périmètre et chaque bassin BMO concerné.

| Colonne | Type | Description |
|---|---|---|
| `code_bassin` | VARCHAR |  |
| `libelle_bassin` | VARCHAR |  |
| `millesime_zonage` | INTEGER |  |
| `nb_communes_bassin` | BIGINT |  |
| `nb_communes_bassin_dans_perimetre` | BIGINT |  |
| `nb_communes_bassin_hors_perimetre` | BIGINT |  |
| `population_perimetre_dans_bassin` | HUGEINT |  |
| `part_population_perimetre` | DOUBLE |  |
| `communes_hors_perimetre` | VARCHAR |  |

### `marts.mart_qualite_indicateurs`

Contrôles de qualité chiffrés, avec seuil et statut, publiés sur la page qualité.

| Colonne | Type | Description |
|---|---|---|
| `source` | VARCHAR |  |
| `metrique` | VARCHAR |  |
| `libelle` | VARCHAR |  |
| `valeur` | DOUBLE |  |
| `seuil` | DOUBLE |  |
| `sens` | VARCHAR |  |
| `statut` | VARCHAR |  |
