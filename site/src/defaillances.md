---
title: Défaillances
---

# Défaillances d'entreprises

<p class="note">Nombre d'<strong>ouvertures</strong> de procédures collectives (sauvegarde, redressement judiciaire, liquidation judiciaire) publiées au BODACC, datées au jour du jugement. Les jugements de clôture, de conversion ou d'extension ne sont pas comptés, pour ne pas compter deux fois la même entreprise. <a href="./methodologie#defaillances">Définitions complètes</a>.</p>

```js
import {cellule, fenetres, libelleFenetre, nombre, pourcent, evolution} from "./components/donnees.js";
import {tuile, graphiqueMensuel, legendeMensuelle, barresSecteurs, carteCommunes, sources} from "./components/graphiques.js";
import {choixTerritoire, tableauCommunes} from "./components/territoire.js";
```

```js
const territoire = view(choixTerritoire());
```

<div class="grid grid-cols-2">
  ${tuile("defaillances")}
  <div class="card">
    <h2>Par type de procédure, 12 derniers mois consolidés</h2>
    <div class="legende"><span><i style="background:var(--serie-1)"></i>12 derniers mois</span><span><i style="background:var(--serie-n1)"></i>12 mois précédents</span></div>
    ${resize((width) => typesProcedure(width))}
  </div>
</div>

```js
const TYPES = [
  ["liquidation", "Liquidation judiciaire"],
  ["redressement", "Redressement judiciaire"],
  ["sauvegarde", "Sauvegarde"]
];
const [precedente, derniere] = fenetres("defaillances");
function typesProcedure(width) {
  // Barre pleine : 12 derniers mois ; barre fantôme grise : 12 mois précédents.
  const donnees = TYPES.map(([code, lib]) => ({
    type: lib,
    v: cellule("defaillances", "12m", derniere, "TOTAL", "P", code).v,
    n1: cellule("defaillances", "12m", precedente, "TOTAL", "P", code).v
  }));
  return Plot.plot({
    width,
    height: 150,
    marginLeft: Math.min(180, width * 0.4),
    marginRight: 40,
    x: {grid: true, label: "ouvertures sur 12 mois"},
    y: {label: null, domain: TYPES.map((t) => t[1])},
    marks: [
      Plot.barX(donnees.filter((d) => d.n1 != null), {x: "n1", y: "type", fill: "var(--serie-n1)", rx: 4, insetTop: 4, insetBottom: 4}),
      Plot.barX(donnees.filter((d) => d.v != null), {x: "v", y: "type", fill: "var(--serie-1)", rx: 4, insetTop: 12, insetBottom: 12,
        tip: true, title: (d) => `${d.type}
12 derniers mois : ${nombre(d.v)}
12 mois précédents : ${nombre(d.n1)}`}),
      Plot.text(donnees, {x: (d) => Math.max(d.v ?? 0, d.n1 ?? 0), y: "type", text: (d) => (d.v == null ? "secret" : nombre(d.v)), dx: 6, textAnchor: "start", fill: "var(--theme-foreground-muted)"}),
      Plot.ruleX([0], {stroke: "var(--axe)"})
    ]
  });
}
```

## Ouvertures par mois — ${territoire.nom}

${legendeMensuelle()}

```js
display(resize((width) => graphiqueMensuel("defaillances", {geo: territoire.code, width})));
```

<p class="note">Les trois derniers mois sont provisoires : un jugement est publié au BODACC en général une à trois semaines après avoir été rendu, parfois bien plus tard.</p>

## Par secteur d'activité (12 derniers mois consolidés) — ${territoire.nom}

```js
display(resize((width) => barresSecteurs("defaillances", {geo: territoire.code, width})));
```

## Par commune

```js
display(resize((width) => carteCommunes("defaillances", {width})));
```

```js
display(tableauCommunes("defaillances"));
```

<p class="avertissement">Aucune liste d'entreprises en difficulté n'est publiée ici, par choix : les annonces du BODACC concernent aussi des entrepreneurs individuels, donc des personnes. Les annonces officielles restent consultables sur <a href="https://www.bodacc.fr">bodacc.fr</a>.</p>

```js
display(sources("bodacc", "sirene", "naf", "geo"));
```
