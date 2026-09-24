---
title: Cessions
---

# Ventes et cessions de fonds

<p class="chapeau">Ventes de fonds de commerce, de fonds artisanaux et d'établissements publiées au BODACC (rubrique « Ventes et cessions »), à la date de parution. Les fusions, scissions et apports partiels d'actifs, publiés dans la même rubrique, sont des restructurations juridiques et sont exclus. <a href="./methodologie#cessions">Définitions complètes</a>.</p>

```js
import {fenetres, libelleFenetre} from "./components/donnees.js";
import {tuile, graphiqueMensuel, legendeMensuelle, barresSecteurs, carteCommunes, sources} from "./components/graphiques.js";
import {choixTerritoire, tableauCommunes} from "./components/territoire.js";
const derniere = fenetres("cessions")[1];
```

<div class="filtres">${territoireInput}</div>

```js
const territoireInput = choixTerritoire();
const territoire = Generators.input(territoireInput);
```

<div class="grille-2">
  ${tuile("cessions", {geo: territoire.code})}
  <section class="panneau">
    <header><h2>Comment lire ces chiffres</h2></header>
    <p class="note">Les volumes mensuels sont faibles et peuvent varier selon la période de l'année : comparez chaque mois au même mois de l'année précédente (courbe grise), et privilégiez le cumul sur 12 mois pour juger d'une tendance.</p>
  </section>
</div>

<section class="panneau">
  <header><h2>Cessions par mois</h2><span class="portee">${territoire.nom}</span></header>
  ${legendeMensuelle()}
  ${resize((width) => graphiqueMensuel("cessions", {geo: territoire.code, width}))}
</section>

<section class="panneau">
  <header><h2>Par secteur d'activité</h2><span class="portees"><span class="portee">${territoire.nom}</span><span class="portee">${libelleFenetre(derniere)}</span></span></header>
  ${barresSecteurs("cessions", {geo: territoire.code})}
</section>

<section class="panneau">
  <header><h2>Par commune</h2><span class="portees"><span class="portee">Toutes les communes</span><span class="portee">${libelleFenetre(derniere)}</span></span></header>
  <div class="grille-2 grille-carte">
    <div>${resize((width) => carteCommunes("cessions", {width}))}</div>
    <div>${tableauCommunes("cessions")}</div>
  </div>
</section>

```js
display(sources("bodacc", "sirene", "naf", "geo"));
```
