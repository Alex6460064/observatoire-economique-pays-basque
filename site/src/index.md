---
title: Accueil
---

# Observatoire économique du Pays Basque

<p class="chapeau">Créations, défaillances et cessions d'entreprises dans les ${meta.perimetre.nb_communes} communes ${meta.perimetre.libelle_complement}, mis à jour chaque jour à partir des données publiques. Chaque chiffre couvre les douze derniers mois consolidés et se compare aux douze mois précédents.</p>

```js
import {meta, recouvrement, bmoFamilles, nombre, pourcent} from "./components/donnees.js";
import {tuile, graphiqueMensuel, legendeMensuelle, panneau, sources} from "./components/graphiques.js";
```

<div class="indice">
  ${tuile("creations_etablissements", {lien: "./creations"})}
  ${tuile("defaillances", {lien: "./defaillances"})}
  ${tuile("cessions", {lien: "./cessions"})}
  ${tuile("creations_entreprises", {lien: "./creations"})}
  ${tuile("immatriculations_rcs", {lien: "./solde"})}
  ${tuile("radiations_rcs", {lien: "./solde"})}
  <a class="tuile" href="./recrutement">
    <span class="tuile-nom">Projets de recrutement ${derniereAnnee}</span>
    <span class="big">${nombre(total)}</span>
    <span class="muted">enquête BMO, bassin «&nbsp;${bassinPB.libelle_bassin.toLowerCase()}&nbsp;»</span>
    <span class="evolution">dont ${pourcent(saison)} saisonniers</span>
  </a>
</div>

<p class="note">Mini-courbes : 24 derniers mois consolidés, hors mois provisoires. Choisissez un indicateur pour son détail par mois, secteur et commune.</p>

```js
const derniereAnnee = Math.max(...bmoFamilles.map((d) => d.annee));
const bassinPB = recouvrement.reduce((a, b) => (a.part_population_perimetre > b.part_population_perimetre ? a : b));
const projets = bmoFamilles.filter((d) => d.annee === derniereAnnee && d.code_bassin == bassinPB.code_bassin);
const total = projets.reduce((s, d) => s + d.projets, 0);
const saison = projets.reduce((s, d) => s + (d.projets_saisonniers ?? 0), 0) / projets.reduce((s, d) => s + (d.base_taux_saisonnier ?? 0), 0);
```

```js
display(panneau("Créations d'établissements par mois", "Tout le territoire",
  legendeMensuelle(),
  resize((width) => graphiqueMensuel("creations_etablissements", {width, hauteur: 260, trace: true})),
  html`<p class="note">Les pics de janvier viennent d'une convention de date de Sirene, pas d'un afflux réel (<a href="./methodologie#creations">explication</a>).</p>`
));
```

## Ce que montre ce tableau de bord

- **Créations** : nouveaux établissements et nouvelles entreprises inscrits au répertoire Sirene, hors transferts et reprises.
- **Défaillances** : ouvertures de sauvegarde, redressement et liquidation judiciaires publiées au BODACC.
- **Cessions** : ventes de fonds de commerce publiées au BODACC.
- **Recrutement** : intentions d'embauche des employeurs (enquête Besoins en Main-d'Œuvre de France Travail).

Chaque chiffre est défini précisément dans la [méthodologie](./methodologie) ; la [page qualité](./qualite) montre la fraîcheur de chaque source et le résultat des contrôles automatiques. Les douze derniers mois sont comparés aux douze mois précédents ; les mois les plus récents sont **provisoires** (enregistrements et publications tardifs).

<p class="note">Seuls des agrégats sont publiés : aucun nom, aucune liste d'entreprises. Toute case de moins de ${meta.seuil_secret} événements est masquée, ainsi que les cases qui permettraient de la recalculer.</p>

```js
display(sources("sirene", "bodacc", "bmo", "geo"));
```
