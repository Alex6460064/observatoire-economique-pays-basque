---
title: Créations
---

# Créations d'établissements et d'entreprises

<p class="chapeau">Un <strong>établissement</strong> est un lieu d'activité (un magasin, un atelier) ; une <strong>entreprise</strong> (unité légale) peut en avoir plusieurs. Les transferts et reprises d'activité existante ne sont pas comptés. <a href="./methodologie#creations">Définitions complètes</a>.</p>

```js
import {meta, libelle, fenetres, libelleFenetre} from "./components/donnees.js";
import {onglets, graphiqueMensuel, legendeMensuelle, barresSecteurs, carteCommunes, sources} from "./components/graphiques.js";
import {choixTerritoire, tableauCommunes} from "./components/territoire.js";
```

<div class="filtres">${territoireInput}</div>

```js
const territoireInput = choixTerritoire();
const territoire = Generators.input(territoireInput);
```

```js
const mesure = view(onglets(["creations_etablissements", "creations_entreprises"], {geo: territoire.code}));
```

```js
const fin = fenetres(mesure)[1];
```

<p class="onglets-aide">Choisissez une tuile pour afficher son détail ci-dessous.</p>

<section class="panneau">
  <header><h2>${libelle(mesure)} par mois</h2><span class="portee">${territoire.nom}</span></header>
  ${legendeMensuelle()}
  ${resize((width) => graphiqueMensuel(mesure, {geo: territoire.code, width}))}
  <p class="note">Les pics de janvier viennent d'une convention de date : environ la moitié des créations de janvier sont datées du 1er janvier, surtout des activités immobilières. <a href="./methodologie#creations">Explication</a>.${territoire.code !== "TOTAL" ? ` À l'échelle d'une commune, les mois comptant moins de ${meta.seuil_secret} créations sont masqués (bandes hachurées) ; une courbe à zéro signifie aucune création ce mois-là.` : ""}</p>
</section>

<div class="grille-2">
  <section class="panneau">
    <header><h2>Par secteur d'activité</h2><span class="portees"><span class="portee">${territoire.nom}</span><span class="portee">${libelleFenetre(fin)}</span></span></header>
    ${barresSecteurs(mesure, {geo: territoire.code})}
  </section>
  <section class="panneau">
    <header><h2>Les 15 divisions les plus créatrices</h2><span class="portees"><span class="portee">Tout le territoire</span><span class="portee">${libelleFenetre(fin)}</span></span></header>
    ${barresSecteurs(mesure, {niv: "D", max: 15})}
  </section>
</div>

<section class="panneau">
  <header><h2>${libelle(mesure)} par commune</h2><span class="portees"><span class="portee">Toutes les communes</span><span class="portee">${libelleFenetre(fin)}</span></span></header>
  <div class="grille-2 grille-carte">
    <div>${resize((width) => carteCommunes(mesure, {width}))}</div>
    <div>${tableauCommunes(mesure)}</div>
  </div>
</section>

```js
display(sources("sirene", "naf", "geo"));
```
