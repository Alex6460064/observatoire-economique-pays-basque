---
title: Recrutement (BMO)
---

# Intentions de recrutement : enquête BMO

<p class="note">L'enquête Besoins en Main-d'Œuvre de France Travail interroge chaque automne les employeurs sur leurs projets d'embauche de l'année suivante. Un projet n'est pas une embauche réalisée. Les résultats sont publiés par <strong>bassin d'emploi</strong>, un découpage de France Travail qui ne coïncide pas avec la communauté d'agglomération. <a href="./methodologie#bmo">Définitions</a>.</p>

```js
import {recouvrement, bmoFamilles, bmoMetiers, meta, nombre, pourcent} from "./components/donnees.js";
import {sources} from "./components/graphiques.js";
```

```js
const parDefaut = recouvrement.reduce((a, b) => (a.part_population_perimetre > b.part_population_perimetre ? a : b));
const bassin = view(Inputs.select(recouvrement, {
  label: "Bassin d'emploi",
  format: (b) => `${b.libelle_bassin} (${pourcent(b.part_population_perimetre)} de la population du territoire)`,
  value: parDefaut
}));
```

<div class="card">
  <h2>Ce que couvre le bassin « ${bassin.libelle_bassin} »</h2>
  <p>${bassin.nb_communes_bassin_dans_perimetre} des ${meta.perimetre.nb_communes} communes du territoire, soit <strong>${pourcent(bassin.part_population_perimetre, 1)}</strong> de sa population. Le bassin compte aussi ${bassin.nb_communes_bassin_hors_perimetre} communes hors du territoire${bassin.communes_hors_perimetre ? html` : ${bassin.communes_hors_perimetre.toLowerCase()}` : ""}.</p>
  <p class="note">Zonage des bassins : millésime ${bassin.millesime_zonage}, appliqué à tous les millésimes de l'enquête (codes de bassin vérifiés identiques de 2023 à 2026).</p>
</div>

```js
const lignes = bmoFamilles.filter((d) => d.code_bassin == bassin.code_bassin);
const annees = [...new Set(lignes.map((d) => d.annee))].sort();
const derniere = annees.at(-1);
const parAnnee = annees.map((annee) => {
  const l = lignes.filter((d) => d.annee === annee);
  const somme = (k) => l.reduce((s, d) => s + (d[k] ?? 0), 0);
  return {
    annee,
    projets: somme("projets"),
    difficiles: somme("projets_difficiles") / somme("base_taux_difficile"),
    saisonniers: somme("projets_saisonniers") / somme("base_taux_saisonnier"),
    secret: somme("nb_metiers_secret"),
    metiers: somme("nb_metiers")
  };
});
const courant = parAnnee.at(-1);
```

<div class="grid grid-cols-3">
  <div class="card tuile"><h2>Projets de recrutement ${derniere}</h2><span class="big">${nombre(courant.projets)}</span><span class="muted">minorant : ${courant.secret} métiers sur ${courant.metiers} couverts par le secret</span></div>
  <div class="card tuile"><h2>Jugés difficiles</h2><span class="big">${pourcent(courant.difficiles)}</span><span class="muted">des projets, selon les employeurs</span></div>
  <div class="card tuile"><h2>Saisonniers</h2><span class="big">${pourcent(courant.saisonniers)}</span><span class="muted">des projets</span></div>
</div>

## Évolution par millésime

```js
display(html`<div class="grid grid-cols-2">
  <div>${resize((width) => Plot.plot({
    width, height: 220, marginLeft: 50,
    x: {label: null, tickFormat: (d) => String(d), type: "band"},
    y: {grid: true, label: "projets de recrutement"},
    marks: [
      Plot.barY(parAnnee, {x: "annee", y: "projets", fill: "var(--serie-1)", rx: 4, insetLeft: 4, insetRight: 4, tip: true}),
      Plot.text(parAnnee, {x: "annee", y: "projets", text: (d) => nombre(d.projets), dy: -8, fill: "var(--theme-foreground-muted)"}),
      Plot.ruleY([0], {stroke: "var(--axe)"})
    ]
  }))}</div>
  <div>${resize((width) => Plot.plot({
    width, height: 220, marginLeft: 50,
    x: {label: null, tickFormat: (d) => String(d), type: "point", inset: 20},
    y: {grid: true, label: "part des projets", tickFormat: (d) => pourcent(d), domain: [0, 1]},
    color: {domain: ["Difficiles", "Saisonniers"], range: ["var(--serie-2)", "var(--serie-3)"]},
    marks: [
      Plot.lineY(parAnnee.flatMap((d) => [{annee: d.annee, part: d.difficiles, serie: "Difficiles"}, {annee: d.annee, part: d.saisonniers, serie: "Saisonniers"}]),
        {x: "annee", y: "part", stroke: "serie", strokeWidth: 2, marker: "circle", tip: true}),
      Plot.text(parAnnee, Plot.selectLast({x: "annee", y: "difficiles", text: () => "difficiles", dx: 8, textAnchor: "start", fill: "var(--theme-foreground-muted)"})),
      Plot.text(parAnnee, Plot.selectLast({x: "annee", y: "saisonniers", text: () => "saisonniers", dx: 8, textAnchor: "start", fill: "var(--theme-foreground-muted)"}))
    ],
    marginRight: 80
  }))}</div>
</div>`);
```

## Par famille de métiers, ${derniere}

```js
const familles = lignes
  .filter((d) => d.annee === derniere)
  .map((d) => ({
    famille: d.libelle_famille,
    projets: d.projets,
    difficiles: d.base_taux_difficile ? d.projets_difficiles / d.base_taux_difficile : null,
    saisonniers: d.base_taux_saisonnier ? d.projets_saisonniers / d.base_taux_saisonnier : null
  }))
  .sort((a, b) => b.projets - a.projets);
display(resize((width) => Plot.plot({
  width, height: 34 * familles.length + 40, marginLeft: Math.min(300, width * 0.45),
  x: {grid: true, label: "projets de recrutement"},
  y: {label: null, domain: familles.map((d) => d.famille)},
  marks: [
    Plot.barX(familles, {x: "projets", y: "famille", fill: "var(--serie-1)", rx: 4, insetTop: 3, insetBottom: 3, tip: true}),
    Plot.text(familles, {x: "projets", y: "famille", text: (d) => nombre(d.projets), dx: 4, textAnchor: "start", fill: "var(--theme-foreground-muted)"}),
    Plot.ruleX([0], {stroke: "var(--axe)"})
  ]
})));
display(Inputs.table(familles, {
  header: {famille: "Famille de métiers", projets: "Projets", difficiles: "Part difficiles", saisonniers: "Part saisonniers"},
  format: {projets: nombre, difficiles: (v) => pourcent(v), saisonniers: (v) => pourcent(v)}
}));
```

## Les métiers les plus recherchés, ${derniere}

```js
const metiers = bmoMetiers
  .filter((d) => d.code_bassin == bassin.code_bassin && d.projets != null)
  .sort((a, b) => b.projets - a.projets)
  .slice(0, 20)
  .map((d) => ({
    metier: d.libelle_metier,
    famille: d.libelle_famille,
    projets: d.projets,
    difficiles: d.projets_difficiles == null ? null : d.projets_difficiles / d.projets,
    saisonniers: d.projets_saisonniers == null ? null : d.projets_saisonniers / d.projets
  }));
display(Inputs.table(metiers, {
  header: {metier: "Métier", famille: "Famille", projets: "Projets", difficiles: "Difficiles", saisonniers: "Saisonniers"},
  format: {projets: nombre, difficiles: (v) => pourcent(v), saisonniers: (v) => pourcent(v)},
  rows: 20
}));
```

<p class="note">Nomenclature des métiers : FAP2009 jusqu'au millésime 2023, FAP2021 ensuite ; les comparaisons dans le temps se font donc par famille de métiers, pas par métier. Cellules « * » de France Travail (secret statistique) exclues des totaux, qui sont des minorants.</p>

```js
display(sources("bmo", "geo"));
```
