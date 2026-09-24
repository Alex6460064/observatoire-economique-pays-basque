# Décisions d'architecture

Format : ADR léger (Michael Nygard). Toutes les décisions datent du 23/09/2026 (V1), statut « acceptée ».

| ADR | Décision |
|---|---|
| [0001](#adr-0001) | Python + DuckDB + Parquet, modélisation avec dbt-duckdb |
| [0002](#adr-0002) | Tableau de bord statique avec Observable Framework |
| [0003](#adr-0003) | Lecture distante du stock Sirene et minimisation à l'ingestion |
| [0004](#adr-0004) | API Sirene en complément optionnel du stock (révisée le 24/09/2026) |
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

**Addendum (24/09/2026).** Le rendu visuel de Bklit UI est repris sans ses composants : aire en
dégradé, courbe `monotone-x` (sans dépassement entre deux points, donc sans valeur inventée),
réticule, grille pointillée et révélation animée, en options Plot et CSS (`graphiques.js`,
`style.css`). Aucune dépendance n'est ajoutée ; les mois masqués restent des trous.

**Addendum (24/09/2026, direction « Etxe »).** La première refonte a été rejetée, parce qu'elle
gardait la structure du gabarit (barre latérale, grille de cartes). La direction retenue part des
maisons du Labourd :
- **Couleurs.** Blanc de chaux pour le fond, encre du colombage pour le texte et les séries, rouge
  basque réservé à l'accent (marque, page active, point survolé), vert des volets pour la carte.
  Thème clair et sombre maison, avec un bouton de bascule mémorisé ; le site suit le système par
  défaut.
- **Structure.** Navigation horizontale (`sidebar: false`). L'accueil s'ouvre sur une phrase dont
  les chiffres forment la typographie, suivie d'un index des indicateurs en lignes. Plus de
  cartes : les blocs sont séparés par des filets. Les encadrés « Note » d'Observable sont
  neutralisés.
- **Mouvement.** Un seul moment animé, à l'accueil : les chiffres comptent et la courbe se trace.
  Rien d'autre ne bouge sans action du visiteur, et tout est coupé avec `prefers-reduced-motion`.
- **Police Public Sans** chargée depuis Google Fonts, chiffres tabulaires. Compromis : une requête
  vers Google par visiteur.
- **Secret statistique.** Mois et communes masqués en hachures (courbes, carte). Une courbe à 0
  est un vrai zéro publié. Les axes sont formatés en français.

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
## ADR-0004 : API Sirene en complément optionnel du stock

*Révisée le 24/09/2026. Décision initiale (V1) : pas d'API Sirene, stock mensuel seul.*

**Contexte.** Le stock mensuel s'arrête au dernier traitement du mois précédent : les créations
des dernières semaines manquent ou sont très incomplètes (enregistrements tardifs). L'API
Sirene 3.11 donne ces données au jour le jour, mais elle demande une clé du portail INSEE
et limite le débit (30 requêtes/min sur le plan « Accès public »).

**Décision.** Le stock reste la base. Quand `INSEE_API_KEY` est définie, chaque run complète
le stock par l'API :
- les établissements des départements du périmètre **traités** depuis le dernier traitement
  du stock et **créés** dans la fenêtre d'historique. Filtrer sur la seule date de création
  ferait manquer les enregistrements tardifs ;
- les unités légales et les liens de succession de ces établissements ;
- le paramètre `champs` limite la réponse aux colonnes du stock, sans nom ni adresse ;
- une requête toutes les `60 / sirene_api_requetes_minute` secondes ; les 429 sont réessayés.

Les fichiers ont le schéma du stock (`raw/sirene_api/`) et sont fusionnés en staging. La
version API, plus récente, l'emporte : par siret pour les établissements, par siren pour les
unités légales. Pour les liens de succession, on garde une seule ligne par (prédécesseur,
successeur, date) : celle de l'API, sinon la plus récemment traitée du stock, qui garde
plusieurs versions d'un même lien. Le complément est reconstruit à chaque run contre le stock
en place. Sans clé, trois fichiers vides sont écrits et le pipeline se comporte comme en V1.

**Conséquences.** + les mois récents sont plus complets (bab_littoral, 24/09/2026 : août
278 → 364 créations, juillet 512 → 537), et le mois courant devient visible, marqué provisoire.
− un secret à gérer, et environ 2 min d'appels par run à cause du quota. − le statut des mois
(`dim_mois`) dépend du traitement le plus récent observé, donc de la présence de la clé. Sans
elle, le calendrier recule d'un mois. − les établissements créés avant la fenêtre et modifiés
depuis le stock ne sont pas rafraîchis. Aucun indicateur ne les utilise aujourd'hui.

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

**Débit (mesuré sur 300 annonces).** Une requête par annonce, 8 en parallèle : 23 annonces/s ;
32 en parallèle : 78 annonces/s, précision inchangée. Regrouper 10 annonces par requête (motif
« fan-out ») : 87 annonces/s seulement, sans gain de tokens (chaque question porte ses 88 options)
et au prix d'un `state` mêlant plusieurs annonces, ce que la documentation de Jev déconseille ;
25 annonces par requête dépassent la limite de contexte. Retenu : une annonce par requête,
parallélisme 32.

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
