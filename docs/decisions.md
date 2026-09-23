# Décisions d'architecture

Format : ADR léger (Michael Nygard). Toutes les décisions datent du 23/09/2026 (V1), statut « acceptée ».

| ADR | Décision |
|---|---|
| [0001](#adr-0001) | Python + DuckDB + Parquet, modélisation avec dbt-duckdb |
| [0002](#adr-0002) | Tableau de bord statique avec Observable Framework |
| [0003](#adr-0003) | Lecture distante du stock Sirene et minimisation à l'ingestion |
| [0004](#adr-0004) | Pas d'API Sirene en V1 |
| [0005](#adr-0005) | Recalcul depuis les sources + historique agrégé versionné |
| [0006](#adr-0006) | Secret statistique : seuil 5, suppression secondaire vérifiée |
| [0007](#adr-0007) | Localisation BODACC par code postal + libellé, secteur via Sirene |
| [0008](#adr-0008) | Attribution sectorielle par IA (Jev) optionnelle et évaluée |
| [0009](#adr-0009) | GitHub Actions quotidien, publication conditionnée aux contrôles |
| [0010](#adr-0010) | Paquet partagé `socle-territorial` (workspace uv) |

---

<a id="adr-0001"></a>
## ADR-0001 : Python + DuckDB + Parquet, modélisation avec dbt-duckdb

**Contexte.** Volumes modestes (≤ 500 000 lignes après filtrage), exécution sur un runner GitHub
gratuit, besoin de couches lisibles (raw → staging → marts) et de tests de données.

**Décision.** Ingestion en Python 3.12 (uv), fichiers bruts en Parquet, entrepôt DuckDB, modèles
et tests en **dbt-duckdb** (sources lues en place par `external_location`).

**Alternatives.**
- *SQL versionné exécuté par un script maison* : plus léger, mais il aurait fallu réécrire l'ordre
  d'exécution, les tests génériques, la fraîcheur des sources et la documentation que dbt fournit.
- *PostgreSQL* : serveur à héberger, sans bénéfice à ce volume.

**Conséquences.** + tests déclaratifs (unicité, non-nullité, valeurs, relations), fraîcheur des
sources (`dbt source freshness`), lignage, manifeste réutilisé pour générer le dictionnaire.
− une dépendance lourde (dbt-core) ; dbt 1.12 est compatible Python 3.12 et Windows.

<a id="adr-0002"></a>
## ADR-0002 : tableau de bord statique avec Observable Framework

**Contexte.** Site public gratuit (GitHub Pages), lisible sur mobile, graphiques de qualité,
mise à jour automatique, pas de serveur.

**Décision.** **Observable Framework** (pages Markdown + JavaScript réactif, Observable Plot) ;
les données sont produites par le pipeline puis servies en fichiers statiques.

**Alternatives.**
- *Evidence* : très bon pour du BI en SQL, mais moins de contrôle sur la forme des graphiques
  (carte, séries avec N-1, tuiles).
- *Vite + React + Tailwind + shadcn + Bklit UI* : rendu soigné, mais dépendances alpha (visx 4)
  et beaucoup de pièces (routeur, build, composants) pour un site de données statique. Écarté
  au profit du plus simple.
- *Streamlit/Dash* : nécessitent un serveur.

**Conséquences.** + un seul langage de graphique (Plot) y compris la carte, build statique vérifié
(liens validés), rendu complet en ~1 s. − les calculs d'affichage se font dans le navigateur à
partir d'un CSV de ~1 Mo.

<a id="adr-0003"></a>
## ADR-0003 : lecture distante du stock Sirene et minimisation à l'ingestion

**Contexte.** Le stock Sirene fait 2,9 Go en Parquet ; il contient des entrepreneurs individuels
(noms, adresses). Le BODACC contient aussi des noms et adresses.

**Décision.** DuckDB lit les Parquet de data.gouv.fr **à distance** (HTTP Range) en ne
transférant que les colonnes utiles, filtrées sur les départements du périmètre. Aucune colonne
nominative ni d'adresse n'est extraite, ni de Sirene ni du BODACC (principe de minimisation).

**Conséquences.** + ~1 min 30 d'extraction au lieu d'un téléchargement de 2,9 Go ; le disque et
le cache CI ne contiennent aucune donnée nominative. − dépend du serveur de fichiers de
data.gouv.fr (requêtes Range) ; un changement de titre de ressource fait échouer le run
(volontairement, plutôt que de lire un mauvais fichier).

<a id="adr-0004"></a>
## ADR-0004 : pas d'API Sirene en V1

**Contexte.** L'API Sirene demande une authentification et impose un quota ; elle apporte la
fraîcheur quotidienne.

**Décision.** V1 sans API Sirene : indicateurs de créations **mensuels** fondés sur le stock
mensuel ; le BODACC (quotidien) couvre les événements récents.

**Conséquences.** + aucun secret obligatoire, pas de gestion de quota. − les créations du mois
écoulé n'apparaissent qu'au stock suivant (mois marqués provisoires). Extension possible en V2.

<a id="adr-0005"></a>
## ADR-0005 : recalcul depuis les sources + historique agrégé versionné

**Contexte.** Le cadrage demande des séries construites dans la durée. Mais conserver des
extractions brutes dans un dépôt public exposerait des données d'entrepreneurs individuels.

**Décision.** Les indicateurs sont **recalculés à chaque run** depuis les sources, qui sont
rejouables (Sirene conserve les établissements fermés ; le BODACC est interrogeable depuis 2008).
Ce qui ne se reconstitue pas — les métriques qualité de chaque run et les séries **telles que
publiées à chaque date** (révisions) — est historisé en CSV agrégés et post-secret sur la branche
`donnees`. Le BODACC est extrait de façon **incrémentale** par mois de parution, avec un cache CI.

**Conséquences.** + aucun état fragile : un run `--forcer` reconstruit tout ; l'historique ne
contient rien de sensible. − chaque run relit le stock Sirene s'il a changé (~1 min 30).

<a id="adr-0006"></a>
## ADR-0006 : secret statistique, seuil 5 et suppression secondaire vérifiée

**Contexte.** Le cadrage impose de ne pas publier de croisement de moins de N éléments (N = 3 à 5)
et de ne rien rendre nominatif.

**Décision.** N = **5** (le plus protecteur de la fourchette). Suppression primaire des cases
de 1 à 4 ; suppression secondaire gloutonne itérative sur toutes les égalités additives publiées
(communes → total, sections → total, divisions → section, mois → 12 mois, types → total) ;
**vérification indépendante** avant écriture ; le détail commune × secteur n'est publié qu'en
cumul 12 mois.

**Alternatives.** τ-ARGUS (optimal, mais outil Java externe) ; arrondi/bruitage (fausse les
totaux et les vérifications à la main demandées par le cadrage).

Révisions entre exécutions (revue de code du 23/09/2026) : un mois consolidé peut être révisé
par une publication tardive, et deux versions publiées peuvent être comparées. Mesure : 1,8 % des
ouvertures tombaient dans un mois déjà consolidé avec 2 mois provisoires ; porté à 3 mois. Le
risque résiduel est accepté car l'événement ainsi révélé est lui-même public, et seul le total
du territoire est historisé.

**Conséquences.** + garantie testée (tests aléatoires sur 200 tableaux croisés) ; les totaux du
territoire restent tous publiés. − le détail communal mensuel est très masqué pour les petits
indicateurs (défaillances, cessions) : d'où la carte et les tableaux en cumul 12 mois.

<a id="adr-0007"></a>
## ADR-0007 : localisation BODACC par code postal + libellé, secteur via Sirene

**Contexte.** Le BODACC n'a ni code commune INSEE ni code NAF. Le code postal seul est ambigu
(64270 couvre le Pays Basque et le Béarn).

**Décision.** Commune : code postal + libellé normalisé (macro SQL miroir de la fonction Python),
puis code postal unique, puis siège Sirene. Secteur : NAF de l'unité légale via le SIREN.

**Conséquences.** + 99,4 % des annonces localisées, 98,8 % jointes à Sirene, seuils bloquants à
90 %. − la commune est celle du siège pour une société (pas celle de chaque établissement).

<a id="adr-0008"></a>
## ADR-0008 : attribution sectorielle par IA (Jev) optionnelle et évaluée

**Contexte.** ~7 % des événements BODACC du périmètre restent sans secteur, alors que l'annonce
décrit l'activité en texte libre.

**Décision.** Une question `Choice` Jev (TypeSafe) par annonce sur les 88 divisions NAF, avec
remontée à la section par somme des probabilités quand la confiance est insuffisante (recette
« Classification using confidence » de TypeSafe). Seuils fixés par une évaluation sur 300
annonces au NAF connu (`docs/evaluation_jev.md`). Modèle figé `jev-1.13.0`, cache par annonce,
seul le texte d'activité est envoyé, étape ignorée sans clé.

**Alternatives.** Règles par mots-clés (fragiles, longues à maintenir) ; LLM génératif (plus cher,
sortie non typée, pas de probabilités calibrées).

**Conséquences.** + part des événements sans secteur réduite de 6,8 % à 4,4 %, précision mesurée
de 86 % sur les attributions, publiée sur la page qualité. − dépendance à un service tiers,
isolée et non bloquante ; la vérité terrain (code APE Sirene) est elle-même imparfaite.

<a id="adr-0009"></a>
## ADR-0009 : GitHub Actions quotidien, publication conditionnée aux contrôles

**Décision.** Un workflow quotidien enchaîne ingestion → dbt build (modèles + tests) → fraîcheur
des sources → enrichissement → export (secret vérifié) → build du site ; **toute erreur arrête
le workflow et rien n'est publié**. Le stock Sirene n'est relu que s'il a changé. Publication
GitHub Pages activée par la variable de dépôt `PUBLIER_PAGES`.

**Conséquences.** + une seule planification (le stock mensuel est détecté automatiquement) ;
le journal des extractions est archivé à chaque run. − GitHub Pages gratuit exige un dépôt
public : le dépôt est privé tant que la V1 n'est pas relue.

<a id="adr-0010"></a>
## ADR-0010 : paquet partagé `socle-territorial`

**Contexte.** La piste 1 réutilisera le référentiel géographique, l'ingestion BMO et les
utilitaires d'extraction.

**Décision.** Paquet Python distinct dans un workspace uv (`packages/socle_territorial`) : `geo`
(communes, contours, normalisation), `bmo`, `journal`, `http`, `stockage`, `secret`. Aucune
dépendance vers le code propre à l'observatoire ; tests dédiés.

**Conséquences.** + réutilisable tel quel (`uv add --editable ../piste5/packages/socle_territorial`
ou publication ultérieure). − une frontière à maintenir entre générique et spécifique.
