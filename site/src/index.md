---
title: Accueil
---

```js
import {meta, recouvrement, bmoFamilles, cellule, evolution, fenetres, libelle, libelleFenetre, nombre, pourcent} from "./components/donnees.js";
import {compter, graphiqueMensuel, legendeMensuelle, sparkline, sources} from "./components/graphiques.js";
```

```js
// Valeur des 12 derniers mois consolidés d'un indicateur, et son évolution sur un an.
const douzeMois = (ind) => {
  const [precedente, fin] = fenetres(ind);
  const v = cellule(ind, "12m", fin).v;
  const evo = evolution(v, precedente ? cellule(ind, "12m", precedente).v : null);
  return {fin, v, evo};
};
const texteEvolution = (evo) => (evo == null ? "évolution non calculable" : `${evo > 0 ? "+" : ""}${pourcent(evo, 1)} sur un an`);

// La phrase n'annonce une période commune que si les trois indicateurs partagent la même fenêtre.
const phraseInd = ["creations_etablissements", "defaillances", "cessions"];
const finsPhrase = new Set(phraseInd.map((i) => douzeMois(i).fin));
const moisEntier = new Intl.DateTimeFormat("fr-FR", {month: "long", year: "numeric", timeZone: "UTC"});
const versDate = (p, decalage = 0) => new Date(Date.UTC(+p.slice(0, 4), +p.slice(5, 7) - 1 + decalage, 1));
const finCommune = [...finsPhrase][0];
const ouverture = finsPhrase.size === 1
  ? `Entre ${moisEntier.format(versDate(finCommune, -11))} et ${moisEntier.format(versDate(finCommune))}, dans les ${meta.perimetre.nb_communes} communes de la ${meta.perimetre.libelle},`
  : `Sur les douze derniers mois publiés par chaque source, dans les ${meta.perimetre.nb_communes} communes de la ${meta.perimetre.libelle},`;

const chiffre = (ind) => {
  const {v} = douzeMois(ind);
  const el = html`<span class="phrase-chiffre">${nombre(v)}</span>`;
  if (v != null) compter(el, v);
  return el;
};
const ligne = (ind, lien, texte) => html`<a class="ligne" href=${lien}>${chiffre(ind)}<span class="phrase-texte">${texte}</span></a>`;
```

<div class="phrase">
  <p>${ouverture}</p>
  ${ligne("creations_etablissements", "./creations", "établissements ont été créés ;")}
  ${ligne("defaillances", "./defaillances", "procédures collectives ont été ouvertes ;")}
  ${ligne("cessions", "./cessions", "fonds de commerce ont été vendus ou cédés.")}
</div>

<div class="accueil-graphique">
  ${legendeMensuelle()}
  ${resize((width) => graphiqueMensuel("creations_etablissements", {width, hauteur: 260, trace: true}))}
  <p class="note">Créations d'établissements par mois. Les pics de janvier viennent d'une convention de date de Sirene, pas d'un afflux réel (<a href="./methodologie#creations">explication</a>).</p>
</div>

```js
const derniereAnnee = Math.max(...bmoFamilles.map((d) => d.annee));
const bassinPB = recouvrement.reduce((a, b) => (a.part_population_perimetre > b.part_population_perimetre ? a : b));
const projets = bmoFamilles.filter((d) => d.annee === derniereAnnee && d.code_bassin == bassinPB.code_bassin);
const total = projets.reduce((s, d) => s + d.projets, 0);
const saison = projets.reduce((s, d) => s + (d.projets_saisonniers ?? 0), 0) / projets.reduce((s, d) => s + (d.base_taux_saisonnier ?? 0), 0);

const rangee = (ind, lien) => {
  const {fin, v, evo} = douzeMois(ind);
  return html`<li><a href=${lien}>
    <span class="indice-nom">${libelle(ind)}<small>12 mois, ${libelleFenetre(fin)}</small></span>
    <span class="indice-valeur">${nombre(v)}</span>
    <span class="evolution">${texteEvolution(evo)}</span>
    ${sparkline(ind)}
  </a></li>`;
};
```

## Les autres indicateurs

<ul class="indice">
  ${rangee("creations_entreprises", "./creations")}
  ${rangee("immatriculations_rcs", "./solde")}
  ${rangee("radiations_rcs", "./solde")}
  <li><a href="./recrutement">
    <span class="indice-nom">Projets de recrutement ${derniereAnnee}<small>enquête BMO, bassin « ${bassinPB.libelle_bassin.toLowerCase()} »</small></span>
    <span class="indice-valeur">${nombre(total)}</span>
    <span class="evolution">dont ${pourcent(saison)} saisonniers</span>
    <span></span>
  </a></li>
</ul>

<p class="note">Mini-courbes : 24 derniers mois consolidés, hors mois provisoires.</p>

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
