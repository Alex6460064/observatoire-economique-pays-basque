---
title: Cessions
---

# Ventes et cessions de fonds

<p class="note">Ventes de fonds de commerce, de fonds artisanaux et d'établissements publiées au BODACC (rubrique « Ventes et cessions »), à la date de parution. Les fusions, scissions et apports partiels d'actifs, publiés dans la même rubrique, sont des restructurations juridiques et sont exclus. <a href="./methodologie#cessions">Définitions complètes</a>.</p>

```js
import {tuile, graphiqueMensuel, legendeMensuelle, barresSecteurs, carteCommunes, sources} from "./components/graphiques.js";
import {choixTerritoire, tableauCommunes} from "./components/territoire.js";
```

```js
const territoire = view(choixTerritoire());
```

<div class="grid grid-cols-2">
  ${tuile("cessions")}
  <div class="card">
    <h2>Lecture</h2>
    <p class="note">Les volumes mensuels sont faibles et peuvent varier selon la période de l'année : comparez chaque mois au même mois de l'année précédente (courbe grise), et privilégiez le cumul sur 12 mois pour juger d'une tendance.</p>
  </div>
</div>

## Cessions par mois — ${territoire.nom}

${legendeMensuelle()}

```js
display(resize((width) => graphiqueMensuel("cessions", {geo: territoire.code, width})));
```

## Par secteur d'activité (12 derniers mois consolidés) — ${territoire.nom}

```js
display(resize((width) => barresSecteurs("cessions", {geo: territoire.code, width})));
```

## Par commune

```js
display(resize((width) => carteCommunes("cessions", {width})));
```

```js
display(tableauCommunes("cessions"));
```

```js
display(sources("bodacc", "sirene", "naf", "geo"));
```
