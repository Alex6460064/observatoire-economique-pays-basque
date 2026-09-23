---
title: Accueil
---

```js
import {meta, recouvrement, bmoFamilles, nombre, pourcent} from "./components/donnees.js";
import {tuile, graphiqueMensuel, legendeMensuelle, sources} from "./components/graphiques.js";
```

<div class="hero">
  <h1>La vie économique du Pays Basque, mois par mois</h1>
  <p>Créations d'entreprises, défaillances, cessions de fonds et besoins de recrutement pour les ${meta.perimetre.nb_communes} communes de la ${meta.perimetre.libelle}. Données publiques officielles, mises à jour automatiquement, contrôlées à chaque exécution.</p>
</div>

<div class="grid grid-cols-3">
  ${tuile("creations_etablissements", {lien: "./creations"})}
  ${tuile("defaillances", {lien: "./defaillances"})}
  ${tuile("cessions", {lien: "./cessions"})}
</div>
<div class="grid grid-cols-3">
  ${tuile("creations_entreprises", {lien: "./creations"})}
  ${tuile("immatriculations_rcs", {lien: "./solde"})}
  ${tuile("radiations_rcs", {lien: "./solde"})}
</div>

```js
const derniereAnnee = Math.max(...bmoFamilles.map((d) => d.annee));
const bassinPB = recouvrement.reduce((a, b) => (a.part_population_perimetre > b.part_population_perimetre ? a : b));
const projets = bmoFamilles.filter((d) => d.annee === derniereAnnee && d.code_bassin == bassinPB.code_bassin);
const total = projets.reduce((s, d) => s + d.projets, 0);
const saison = projets.reduce((s, d) => s + (d.projets_saisonniers ?? 0), 0) / projets.reduce((s, d) => s + (d.base_taux_saisonnier ?? 0), 0);
```

<div class="grid grid-cols-2">
  <a class="card tuile" href="./recrutement">
    <h2>Projets de recrutement ${derniereAnnee} (enquête BMO)</h2>
    <span class="big">${nombre(total)}</span>
    <span class="muted">bassin d'emploi « ${bassinPB.libelle_bassin.toLowerCase()} », dont ${pourcent(saison)} saisonniers</span>
  </a>
  <div class="card">
    <h2>Créations d'établissements par mois</h2>
    ${legendeMensuelle()}
    ${resize((width) => graphiqueMensuel("creations_etablissements", {width, hauteur: 180}))}
  </div>
</div>

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
