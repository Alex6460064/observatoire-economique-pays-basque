---
title: Solde indicatif
---

# Solde indicatif : immatriculations et radiations

<p class="avertissement"><strong>À lire avec précaution.</strong> Ce solde compare deux flux d'une <em>même</em> source, le registre du commerce et des sociétés (RCS) tel que publié au BODACC : immatriculations d'une part, radiations d'autre part. Il ne mesure ni l'emploi, ni le stock d'entreprises actives. Il ignore les micro-entrepreneurs non inscrits au RCS, et une radiation peut suivre de plusieurs années la fin réelle d'activité (radiations d'office). Il sert à repérer des inflexions, pas à compter des entreprises. <a href="./methodologie#solde">Détails</a>.</p>

```js
import {serieMensuelle, cellule, fenetres, libelleFenetre, communes, nombre, pourcent} from "./components/donnees.js";
import {tuile, sources} from "./components/graphiques.js";
```

<div class="grid grid-cols-3">
  ${tuile("immatriculations_rcs")}
  ${tuile("radiations_rcs")}
  <div class="card tuile">
    <h2>Solde sur 12 mois</h2>
    <span class="big">${soldeTexte}</span>
    <span class="muted">${libelleFenetre(derniere)}</span>
  </div>
</div>

```js
const [precedente, derniere] = fenetres("immatriculations_rcs");
const imm = cellule("immatriculations_rcs", "12m", derniere).v;
const rad = cellule("radiations_rcs", "12m", derniere).v;
const soldeTexte = imm == null || rad == null ? "–" : `${imm - rad > 0 ? "+" : ""}${nombre(imm - rad)}`;
const flux = [
  ...serieMensuelle("immatriculations_rcs").map((d) => ({...d, flux: "Immatriculations"})),
  ...serieMensuelle("radiations_rcs").map((d) => ({...d, flux: "Radiations"}))
];
const solde = serieMensuelle("immatriculations_rcs").map((d, i) => {
  const r = serieMensuelle("radiations_rcs")[i];
  return {date: d.date, periode: d.periode, provisoire: d.provisoire, solde: d.v == null || r.v == null ? null : d.v - r.v};
});
```

## Flux mensuels

<div class="legende">
  <span><i style="background:var(--serie-1)"></i>Immatriculations</span>
  <span><i style="background:var(--serie-2)"></i>Radiations</span>
</div>

```js
display(resize((width) => Plot.plot({
  width,
  height: 280,
  marginLeft: 44,
  x: {type: "utc", label: null},
  y: {grid: true, label: "annonces / mois", zero: true},
  color: {domain: ["Immatriculations", "Radiations"], range: ["var(--serie-1)", "var(--serie-2)"]},
  marks: [
    Plot.lineY(flux, {x: "date", y: "v", stroke: "flux", strokeWidth: 2}),
    Plot.text(flux, Plot.selectLast({x: "date", y: "v", z: "flux", text: "flux", dx: 6, textAnchor: "start", fill: "var(--theme-foreground-muted)"})),
    Plot.ruleY([0], {stroke: "var(--axe)"}),
    Plot.tip(flux, Plot.pointer({x: "date", y: "v", title: (d) => `${d.flux}, ${d.periode}${d.provisoire ? " (provisoire)" : ""} : ${nombre(d.v)}`}))
  ],
  marginRight: 110
})));
```

```js
// Détection automatique des mois atypiques (plus de deux fois la médiane de la série).
const atypiques = ["immatriculations_rcs", "radiations_rcs"].flatMap((ind) => {
  const s = serieMensuelle(ind).filter((d) => d.v != null);
  const med = d3.median(s, (d) => d.v);
  return s.filter((d) => d.v > 2 * med).map((d) => ({ind, periode: d.periode, v: d.v, med}));
});
if (atypiques.length) display(html`<p class="note"><strong>Mois atypiques</strong> (plus de deux fois la médiane) : ${atypiques.map((a) => `${a.ind === "radiations_rcs" ? "radiations" : "immatriculations"} ${a.periode} (${nombre(a.v)})`).join(", ")}. Ces pics correspondent à des annonces publiées en nombre sur un même mois${atypiques.some((a) => a.ind === "radiations_rcs") ? " (pour les radiations, vraisemblablement des radiations administratives groupées par les greffes)" : ""} : ils ne traduisent pas des événements économiques survenus ce seul mois.</p>`);
```

## Solde mensuel

```js
display(resize((width) => Plot.plot({
  width,
  height: 220,
  marginLeft: 44,
  x: {type: "utc", label: null},
  y: {grid: true, label: "immatriculations − radiations"},
  marks: [
    Plot.rectY(solde.filter((d) => d.solde != null), {
      x1: "date",
      x2: (d) => new Date(+d.date + 27 * 864e5),
      y: "solde",
      fill: (d) => (d.solde >= 0 ? "var(--serie-1)" : "var(--negatif)"),
      tip: true,
      title: (d) => `${d.periode}${d.provisoire ? " (provisoire)" : ""} : ${d.solde > 0 ? "+" : ""}${nombre(d.solde)}`
    }),
    Plot.ruleY([0], {stroke: "var(--axe)"})
  ]
})));
```

<p class="note">Bleu : plus d'immatriculations que de radiations ; rouge : l'inverse. Barre absente : l'un des deux flux est masqué (secret statistique). Les trois derniers mois sont provisoires.</p>

## Par commune, 12 derniers mois consolidés

```js
const lignes = communes.map((c) => {
  const i = cellule("immatriculations_rcs", "12m", derniere, c.code_commune).v;
  const r = cellule("radiations_rcs", "12m", derniere, c.code_commune).v;
  return {commune: c.nom_commune, immatriculations: i, radiations: r, solde: i == null || r == null ? null : i - r};
}).sort((a, b) => (b.immatriculations ?? -1) - (a.immatriculations ?? -1));
display(Inputs.table(lignes, {
  format: {immatriculations: nombre, radiations: nombre, solde: (v) => (v == null ? "–" : `${v > 0 ? "+" : ""}${nombre(v)}`)},
  header: {commune: "Commune", immatriculations: "Immatriculations", radiations: "Radiations", solde: "Solde"},
  rows: 12
}));
```

```js
display(sources("bodacc", "geo"));
```
