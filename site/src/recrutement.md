---
title: Recrutement (BMO)
---

# Intentions de recrutement : enquête BMO

<p class="chapeau">L'enquête Besoins en Main-d'Œuvre de France Travail interroge chaque automne les employeurs sur leurs projets d'embauche de l'année suivante. Un projet n'est pas une embauche réalisée. Les résultats sont publiés par <strong>bassin d'emploi</strong>, un découpage de France Travail qui ne coïncide pas avec la communauté d'agglomération. <a href="./methodologie#bmo">Définitions</a>.</p>

```js
import {recouvrement, bmoFamilles, bmoMetiers, meta, nombre, pourcent} from "./components/donnees.js";
import {barres, panneau, sources} from "./components/graphiques.js";
```

```js
const parDefaut = recouvrement.reduce((a, b) => (a.part_population_perimetre > b.part_population_perimetre ? a : b));
const bassinInput = Inputs.select(recouvrement, {
  label: "Bassin d'emploi",
  format: (b) => `${b.libelle_bassin} (${pourcent(b.part_population_perimetre)} de la population du territoire)`,
  value: parDefaut
});
const bassin = Generators.input(bassinInput);
```

<div class="filtres">${bassinInput}</div>

<section class="panneau">
  <header><h2>Ce que couvre le bassin « ${bassin.libelle_bassin} »</h2></header>
  <p>${bassin.nb_communes_bassin_dans_perimetre} des ${meta.perimetre.nb_communes} communes du territoire, soit <strong>${pourcent(bassin.part_population_perimetre, 1)}</strong> de sa population. Le bassin compte aussi ${bassin.nb_communes_bassin_hors_perimetre} communes hors du territoire${bassin.communes_hors_perimetre ? html` : ${bassin.communes_hors_perimetre.toLowerCase()}` : ""}.</p>
  <p class="note">Zonage des bassins : millésime ${bassin.millesime_zonage}, appliqué à tous les millésimes de l'enquête (codes de bassin vérifiés identiques de 2023 à 2026).</p>
</section>

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

<div class="tuiles">
  <div class="tuile"><span class="tuile-nom">Projets de recrutement ${derniere}</span><span class="big">${nombre(courant.projets)}</span><span class="muted">minorant : ${courant.secret} métiers sur ${courant.metiers} couverts par le secret</span></div>
  <div class="tuile"><span class="tuile-nom">Jugés difficiles</span><span class="big">${pourcent(courant.difficiles)}</span><span class="muted">des projets, selon les employeurs</span></div>
  <div class="tuile"><span class="tuile-nom">Saisonniers</span><span class="big">${pourcent(courant.saisonniers)}</span><span class="muted">des projets</span></div>
</div>

```js
display(html`<div class="grille-2">
  ${panneau("Projets par millésime", bassin.libelle_bassin, resize((width) => Plot.plot({
    width, height: 220, marginLeft: 50, marginTop: 24,
    x: {label: null, tickFormat: (d) => String(d), type: "band"},
    y: {grid: true, label: null, tickFormat: (d) => nombre(d)},
    marks: [
      Plot.barY(parAnnee, {x: "annee", y: "projets", fill: "var(--serie-1)", rx: 4, insetLeft: 4, insetRight: 4, tip: true}),
      Plot.text(parAnnee, {x: "annee", y: "projets", text: (d) => nombre(d.projets), dy: -8, fill: "var(--theme-foreground-muted)"}),
      Plot.ruleY([0], {stroke: "var(--axe)"})
    ]
  })))}
  ${panneau("Part des projets difficiles et saisonniers", bassin.libelle_bassin, html`<div class="legende">
    <span><i style="background:var(--serie-2)"></i>jugés difficiles</span>
    <span><i style="background:var(--serie-3)"></i>saisonniers</span>
  </div>`, resize((width) => Plot.plot({
    width, height: 200, marginLeft: 50,
    x: {label: null, tickFormat: (d) => String(d), type: "point", inset: 20},
    y: {grid: true, label: null, tickFormat: (d) => pourcent(d), domain: [0, 1]},
    color: {domain: ["Difficiles", "Saisonniers"], range: ["var(--serie-2)", "var(--serie-3)"]},
    marks: [
      Plot.lineY(parAnnee.flatMap((d) => [{annee: d.annee, part: d.difficiles, serie: "Difficiles"}, {annee: d.annee, part: d.saisonniers, serie: "Saisonniers"}]),
        {x: "annee", y: "part", stroke: "serie", strokeWidth: 2, marker: "circle", tip: {format: {part: (v) => pourcent(v)}}})
    ]
  })))}
</div>`);
```

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
display(panneau(`Par famille de métiers, ${derniere}`, bassin.libelle_bassin, barres(familles.map((d) => ({libelle: d.famille, v: d.projets})))));
display(panneau(`Difficultés et saisonnalité par famille, ${derniere}`, bassin.libelle_bassin, Inputs.table(familles, {
  header: {famille: "Famille de métiers", projets: "Projets", difficiles: "Part difficiles", saisonniers: "Part saisonniers"},
  format: {projets: nombre, difficiles: (v) => pourcent(v), saisonniers: (v) => pourcent(v)},
  layout: "auto"
})));
```

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
display(panneau(`Les 20 métiers les plus recherchés, ${derniere}`, bassin.libelle_bassin, Inputs.table(metiers, {
  header: {metier: "Métier", famille: "Famille", projets: "Projets", difficiles: "Difficiles", saisonniers: "Saisonniers"},
  format: {projets: nombre, difficiles: (v) => pourcent(v), saisonniers: (v) => pourcent(v)},
  rows: 20
}), html`<p class="note">Nomenclature des métiers : FAP2009 jusqu'au millésime 2023, FAP2021 ensuite ; les comparaisons dans le temps se font donc par famille de métiers, pas par métier. Cellules « * » de France Travail (secret statistique) exclues des totaux, qui sont des minorants.</p>`));
```

```js
display(sources("bmo", "geo"));
```
