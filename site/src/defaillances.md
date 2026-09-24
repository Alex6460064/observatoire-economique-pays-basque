---
title: Défaillances
---

# Défaillances d'entreprises

<p class="chapeau">Nombre d'<strong>ouvertures</strong> de procédures collectives (sauvegarde, redressement judiciaire, liquidation judiciaire) publiées au BODACC, datées au jour du jugement. Les jugements de clôture, de conversion ou d'extension ne sont pas comptés, pour ne pas compter deux fois la même entreprise. <a href="./methodologie#defaillances">Définitions complètes</a>.</p>

```js
import {cellule, fenetres, libelleFenetre} from "./components/donnees.js";
import {tuile, barres, graphiqueMensuel, legendeMensuelle, barresSecteurs, carteCommunes, sources} from "./components/graphiques.js";
import {choixTerritoire, tableauCommunes} from "./components/territoire.js";
```

```js
const [precedente, derniere] = fenetres("defaillances");
// Barre pleine : 12 derniers mois ; barre fantôme grise : 12 mois précédents.
const types = [
  ["liquidation", "Liquidation judiciaire"],
  ["redressement", "Redressement judiciaire"],
  ["sauvegarde", "Sauvegarde"]
].map(([code, libelle]) => ({
  libelle,
  v: cellule("defaillances", "12m", derniere, "TOTAL", "P", code).v,
  n1: cellule("defaillances", "12m", precedente, "TOTAL", "P", code).v
}));
```

<div class="filtres">${territoireInput}</div>

```js
const territoireInput = choixTerritoire();
const territoire = Generators.input(territoireInput);
```

<div class="grille-2">
  ${tuile("defaillances", {geo: territoire.code})}
  <section class="panneau">
    <header><h2>Par type de procédure</h2><span class="portees"><span class="portee">Tout le territoire</span><span class="portee">${libelleFenetre(derniere)}</span></span></header>
    <div class="legende"><span><i style="background:var(--serie-1)"></i>12 derniers mois</span><span><i style="background:var(--serie-n1)"></i>12 mois précédents</span></div>
    ${barres(types, {fantome: true})}
  </section>
</div>

<section class="panneau">
  <header><h2>Ouvertures par mois</h2><span class="portee">${territoire.nom}</span></header>
  ${legendeMensuelle()}
  ${resize((width) => graphiqueMensuel("defaillances", {geo: territoire.code, width}))}
  <p class="note">Les trois derniers mois sont provisoires : un jugement est publié au BODACC en général une à trois semaines après avoir été rendu, parfois bien plus tard.</p>
</section>

<section class="panneau">
  <header><h2>Par secteur d'activité</h2><span class="portees"><span class="portee">${territoire.nom}</span><span class="portee">${libelleFenetre(derniere)}</span></span></header>
  ${barresSecteurs("defaillances", {geo: territoire.code})}
</section>

<section class="panneau">
  <header><h2>Par commune</h2><span class="portees"><span class="portee">Toutes les communes</span><span class="portee">${libelleFenetre(derniere)}</span></span></header>
  <div class="grille-2 grille-carte">
    <div>${resize((width) => carteCommunes("defaillances", {width}))}</div>
    <div>${tableauCommunes("defaillances")}</div>
  </div>
</section>

<p class="avertissement">Aucune liste d'entreprises en difficulté n'est publiée ici, par choix : les annonces du BODACC concernent aussi des entrepreneurs individuels, donc des personnes. Les annonces officielles restent consultables sur <a href="https://www.bodacc.fr">bodacc.fr</a>.</p>

```js
display(sources("bodacc", "sirene", "naf", "geo"));
```
