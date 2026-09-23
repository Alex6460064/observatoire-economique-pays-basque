---
title: Créations
---

# Créations d'établissements et d'entreprises

<p class="note">Un <strong>établissement</strong> est un lieu d'activité (un magasin, un atelier) ; une <strong>entreprise</strong> (unité légale) peut en avoir plusieurs. Les nouveaux numéros SIRET issus d'un transfert ou d'une reprise d'activité existante ne sont pas des créations et sont exclus. <a href="./methodologie#creations">Définitions complètes</a>.</p>

```js
import {meta, libelle} from "./components/donnees.js";
import {tuile, graphiqueMensuel, legendeMensuelle, barresSecteurs, carteCommunes, sources} from "./components/graphiques.js";
import {choixTerritoire, tableauCommunes} from "./components/territoire.js";
```

```js
const mesure = view(Inputs.radio(new Map([
  ["Établissements", "creations_etablissements"],
  ["Entreprises", "creations_entreprises"]
]), {label: "Mesure", value: "creations_etablissements"}));
```

```js
const territoire = view(choixTerritoire());
```

<div class="grid grid-cols-2">
  ${tuile("creations_etablissements")}
  ${tuile("creations_entreprises")}
</div>

## ${libelle(mesure)} par mois — ${territoire.nom}

${legendeMensuelle()}

```js
display(resize((width) => graphiqueMensuel(mesure, {geo: territoire.code, width})));
```

<p class="note">Les pics de janvier viennent d'une convention de date : environ la moitié des créations de janvier sont datées du 1er janvier, surtout des activités immobilières. <a href="./methodologie#creations">Explication</a>.</p>

```js
if (territoire.code !== "TOTAL") display(html`<p class="note">À l'échelle d'une commune, les mois comptant moins de ${meta.seuil_secret} créations sont masqués (×). Le cumul sur 12 mois, plus robuste, figure dans le tableau ci-dessous.</p>`);
```

## Par secteur d'activité (12 derniers mois consolidés) — ${territoire.nom}

```js
display(resize((width) => barresSecteurs(mesure, {geo: territoire.code, width})));
```

```js
if (territoire.code === "TOTAL") {
  display(html`<h2>Les 15 divisions d'activité les plus créatrices</h2>`);
  display(resize((width) => barresSecteurs(mesure, {niv: "D", width, max: 15})));
}
```

## Par commune

```js
display(resize((width) => carteCommunes(mesure, {width})));
```

```js
display(tableauCommunes(mesure));
```

```js
display(sources("sirene", "naf", "geo"));
```
