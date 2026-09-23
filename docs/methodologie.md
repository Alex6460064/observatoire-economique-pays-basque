# Méthodologie

Ce document définit précisément chaque indicateur publié. Il est la source unique : la
page « Méthodologie » du site en est une copie générée à chaque exécution.

## Périmètre et calendrier

- **Territoire** : les communes de la Communauté d'agglomération Pays Basque (CAPB, SIREN
  `200067106`), lues à chaque exécution au Code officiel géographique en vigueur via
  geo.api.gouv.fr (158 communes au 23/09/2026). Aucune liste n'est codée en dur.
- **Historique** : 36 mois pleins avant le mois courant, recalculés à chaque exécution depuis
  les sources (pas d'accumulation fragile : Sirene conserve les établissements fermés, le
  BODACC est interrogeable depuis 2008).
- **Mois provisoires** :
  - Sirene : le stock mensuel couvre jusqu'au dernier mois traité par l'INSEE. Les deux
    derniers mois couverts sont **provisoires** car des établissements sont enregistrés
    avec retard (exemple observé : août 2026 compte ~900 créations dans le stock du
    1er septembre, contre ~1 700 un mois ordinaire). Les mois postérieurs ne sont pas publiés.
  - BODACC : le mois courant et le précédent sont **provisoires** (délai de publication
    d'une à trois semaines après le jugement).
- **Comparaisons annuelles** : « 12 derniers mois » = les 12 derniers mois consolidés ;
  comparés aux 12 mois qui les précèdent. Un mois est comparé au même mois de l'année
  précédente, jamais au mois précédent (effets saisonniers).

<a id="creations"></a>
## Créations (source : Sirene, INSEE)

**Créations d'établissements.** Nombre d'établissements dont la *date de création* tombe dans
le mois, situés dans une commune du territoire, **hors transferts et reprises** : un nouveau
SIRET issu d'un transfert ou d'une reprise avec continuité économique (repéré par le fichier
des liens de succession Sirene, `continuiteEconomique = true`) n'est pas une création. Cette
correction retire environ un nouveau SIRET sur cinq.

**Créations d'entreprises.** Nombre de nouvelles unités légales (nouveau SIREN) dont le siège
est situé dans le territoire, hors sièges issus d'une reprise avec continuité économique.

Points d'attention :
- un établissement créé n'est pas une entreprise créée : une entreprise existante qui ouvre
  une boutique crée un établissement, pas une entreprise ;
- la commune du siège est la commune actuelle (un siège transféré depuis est compté dans sa
  nouvelle commune) ;
- ces chiffres diffèrent des « créations d'entreprises » publiées par l'INSEE (répertoire SIDE),
  qui comptent notamment les réactivations d'entrepreneurs individuels ; ils ne sont pas
  destinés à s'y substituer ;
- les unités en **diffusion partielle** (entrepreneurs ayant demandé que leurs données ne
  soient pas diffusées, statut `P`, ~30 % des créations) sont **comptées dans les agrégats**
  mais n'apparaissent jamais individuellement : leur code commune reste renseigné par l'INSEE
  (seule l'adresse est masquée) ;
- **pics de janvier** : environ la moitié des créations de janvier sont datées exactement du
  1er janvier (640 en 2024, 747 en 2025, 497 en 2026), dont une majorité d'activités
  immobilières (location de logements notamment, activité vraisemblablement déclarée en début
  d'année civile). C'est une convention de date de la source, pas un afflux réel ce mois-là ;
- secteur : activité principale en NAF rév. 2 de l'établissement (ou de l'unité légale pour
  les entreprises). Le code NAF 2025 est extrait mais pas encore exploité.

<a id="defaillances"></a>
## Défaillances (source : BODACC, DILA)

Nombre d'**ouvertures** de procédures collectives : annonces de la rubrique « Procédures
collectives » dont le jugement est un *jugement d'ouverture* de sauvegarde, de redressement
judiciaire ou de liquidation judiciaire. Sont exclus : les extensions de procédure, les
jugements de clôture, de conversion (un redressement converti en liquidation n'est compté
qu'une fois, à l'ouverture), les plans, les dépôts d'état des créances.

- **Date** : date du jugement (et non de parution), si elle est cohérente (au plus un an avant
  la parution, jamais après) ; sinon date de parution (19 cas sur 1 809 en septembre 2026).
- **Annulations et rectificatifs** : une annonce annulée n'est pas comptée ; une annonce
  rectifiée est remplacée par son rectificatif.
- Cette définition est proche de celle de la Banque de France pour les défaillances
  (redressements et liquidations) mais inclut les sauvegardes, affichées séparément.

<a id="cessions"></a>
## Cessions (source : BODACC)

Annonces de la rubrique « Ventes et cessions » : ventes de fonds de commerce, de fonds
artisanaux, d'établissements principaux ou secondaires, à la date de parution. La même
rubrique publie des **fusions, scissions et apports partiels d'actifs** (catégorie « Autre
achat, apport, attribution », dont 94 % des annonces sont des fusions/scissions) : ce sont des
restructurations juridiques, **exclues**.

<a id="solde"></a>
## Solde indicatif (source : BODACC)

Immatriculations au RCS (rubrique « Créations ») moins radiations du RCS (rubrique
« Radiations »), deux flux de **la même source** et du même registre. Ce n'est pas un solde
d'entreprises actives :
- les micro-entrepreneurs non inscrits au RCS n'y figurent pas ;
- une radiation peut intervenir longtemps après l'arrêt réel de l'activité (radiations d'office) ;
- les transferts de siège (rubrique « Immatriculations ») ne sont comptés ni d'un côté ni de l'autre.

## Rattachement des annonces BODACC à une commune et à un secteur

Le BODACC ne donne ni code commune INSEE ni code NAF. Pour chaque annonce :

1. **Commune** : code postal + libellé de commune de l'annonce, rapprochés du COG après
   normalisation (accents, « St » → « Saint », « Cedex »…) ; à défaut, code postal s'il ne
   désigne qu'une commune ; à défaut, commune du siège dans Sirene. Le code postal seul ne
   suffit pas : `64270` couvre à la fois des communes basques et béarnaises. Taux de
   localisation : 99,4 %.
2. **Secteur** : activité NAF rév. 2 de l'unité légale dans Sirene (jointure par SIREN, taux
   de jointure 98,8 %), à défaut celle de son siège.
3. **Secteur par IA, à défaut** : si l'annonce n'a pas de SIREN retrouvé ou pas de code NAF
   rév. 2, son texte d'activité (« livraison de repas à domicile à vélo ») est classé par le
   modèle **Jev** de TypeSafe parmi les 88 divisions NAF. Le modèle renvoie une probabilité
   pour chaque division et une confiance :
   - confiance ≥ 0,9 : la division est retenue ;
   - sinon, les probabilités sont additionnées par section NAF ; si une section cumule ≥ 0,8,
     seule la section est retenue (division « non déterminée ») ;
   - sinon, l'annonce reste en « activité non déterminée ».

   Seuils fixés par une évaluation sur 300 annonces dont le secteur est connu par Sirene
   (voir `docs/evaluation_jev.md`) : 76 % des annonces reçoivent un secteur, avec une
   précision de 86 %. Seul le texte d'activité est transmis au modèle. Cette étape est
   optionnelle : sans clé d'API, les annonces concernées restent « non déterminées ».
   Elle concerne environ 2,5 % des événements publiés.

<a id="bmo"></a>
## Recrutement (source : enquête BMO, France Travail)

Projets de recrutement déclarés par les employeurs pour l'année, par bassin d'emploi et par
métier. **Part difficile** : projets jugés difficiles par l'employeur / projets. **Part
saisonnière** : projets saisonniers / projets.

- **Recouvrement** : les bassins d'emploi de France Travail ne coïncident pas avec la CAPB.
  Au zonage 2026, le bassin « Pays Basque » (131 communes) contient 122 communes de la CAPB
  (96,2 % de sa population) et 9 communes landaises ou béarnaises ; les 36 communes souletines
  de la CAPB relèvent du bassin « Béarn ». Le site affiche ce recouvrement, calculé à chaque
  exécution.
- **Secret** : France Travail masque (« * ») les petits effectifs. Ces cellules sont exclues :
  les totaux sont des **minorants** ; les parts sont calculées sur les seules lignes où
  numérateur et dénominateur sont connus.
- **Nomenclature** : FAP2009 jusqu'au millésime 2023, FAP2021 ensuite. Les comparaisons dans
  le temps se font par famille de métiers.

## Secret statistique et protection des personnes

Les répertoires contiennent des entrepreneurs individuels, donc des personnes physiques. Le
site ne publie que des agrégats :

- **aucune donnée nominative** n'est extraite : ni nom, ni dénomination, ni adresse (vérifié
  par un test automatique sur la couche publiée) ;
- **secret primaire** : toute case comptant de 1 à 4 événements est masquée (seuil N = 5) ;
- **secret secondaire** : une case masquée ne doit pas pouvoir être recalculée par différence
  (total − cases publiées). Pour chaque égalité publiée (communes → territoire, sections →
  total, divisions → section, mois → cumul 12 mois, types de procédure → total), si une seule
  case est masquée, la plus petite case non nulle du groupe l'est aussi, jusqu'à stabilité ;
- un contrôle **indépendant** vérifie ces deux propriétés avant chaque publication ;
- le détail commune × secteur n'est publié qu'en cumul sur 12 mois (plus robuste que par mois).

Limite assumée : l'algorithme de secret secondaire est glouton ; il garantit l'absence de
recalcul direct dans les relations publiées, sans minimiser le nombre de cases masquées.

## Limites connues

- Localisation BODACC : l'adresse de l'annonce est celle du siège pour une société ; une
  entreprise immatriculée hors du département mais active dans le territoire n'est pas vue.
- Sirene reflète les déclarations administratives, parfois tardives ou erronées (34 dates
  de création postérieures à la date d'extraction ont été détectées et écartées).
- Le secteur NAF des radiations est inconnu pour ~13 % d'entre elles (unités anciennes codées
  dans une nomenclature antérieure) ; l'IA en rattrape une partie.
