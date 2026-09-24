---
title: Qualité des données
---

# Qualité des données

<p class="chapeau">Chaque exécution du pipeline contrôle les données avant de publier : si un seul contrôle bloquant échoue, le site n'est pas mis à jour et la version précédente reste en ligne. Cette page expose les résultats de la dernière exécution publiée.</p>

```js
import {qualite, meta, historiqueQualite, historiqueSeries, nombre, pourcent, libelle} from "./components/donnees.js";
import {panneau, sources} from "./components/graphiques.js";
const jours = (iso) => (iso ? Math.round((new Date(meta.genere_le) - new Date(iso)) / 864e5) : null);
const t = qualite.tests;
```

<div class="tuiles">
  <div class="tuile">
    <span class="tuile-nom">Contrôles automatiques</span>
    <span class="big">${t.disponible ? `${t.compte.pass ?? 0} / ${Object.values(t.compte).reduce((a, b) => a + b, 0)}` : "–"}</span>
    <span class="muted">réussis ; ${t.compte.warn ?? 0} alerte(s) non bloquante(s), ${(t.compte.fail ?? 0) + (t.compte.error ?? 0)} échec(s)</span>
  </div>
  <div class="tuile">
    <span class="tuile-nom">Jointure BODACC ↔ Sirene</span>
    <span class="big">${pourcent(qualite.metriques.find((m) => m.metrique === "taux_jointure_sirene").valeur, 1)}</span>
    <span class="muted">des annonces avec SIREN retrouvées dans Sirene (seuil bloquant : 90 %)</span>
  </div>
  <div class="tuile">
    <span class="tuile-nom">Données générées le</span>
    <span class="big">${new Date(meta.genere_le).toLocaleDateString("fr-FR")}</span>
    <span class="muted">exécution automatique (GitHub Actions)</span>
  </div>
</div>

```js
const libelles = {
  geo_communes: "Référentiel communes (geo.api.gouv.fr)",
  naf: "Nomenclature NAF (INSEE)",
  sirene: "Sirene – vérification du stock",
  sirene_etablissements: "Sirene – établissements",
  sirene_unites_legales: "Sirene – unités légales",
  sirene_liens_succession: "Sirene – liens de succession",
  bodacc: "BODACC – annonces",
  bmo: "Enquête BMO",
  bmo_bassins: "Zonage des bassins BMO",
  jev_secteurs: "Attribution sectorielle Jev (TypeSafe)"
};
display(panneau("Fraîcheur de chaque source", null, Inputs.table(qualite.fraicheur_extractions.map((f) => ({
  source: libelles[f.source] ?? f.source,
  millesime: f.millesime,
  extraction: f.derniere_reussite?.slice(0, 10),
  age: jours(f.derniere_reussite),
  lignes: f.lignes,
  echec: f.dernier_echec && f.dernier_echec > (f.derniere_reussite ?? "") ? `échec le ${f.dernier_echec.slice(0, 10)}` : ""
})), {
  header: {source: "Source", millesime: "Millésime / version", extraction: "Dernière extraction réussie", age: "Âge (jours)", lignes: "Lignes", echec: "Incident"},
  format: {lignes: (v) => (v == null ? "–" : nombre(v))},
  layout: "auto"
})));
```

```js
display(html`<p class="note">Contrôle de fraîcheur des données elles-mêmes (date la plus récente observée) : ${qualite.fraicheur_sources.map((f) =>
  html`<span class=${f.statut === "pass" ? "statut-ok" : f.statut === "warn" ? "statut-alerte" : "statut-echec"}>${f.source} ${f.statut === "pass" ? "à jour" : f.statut} (${f.age_jours} j)</span>`
).reduce((a, b) => html`${a} · ${b}`)}. Seuils : BODACC alerte à 4 jours sans parution, échec à 10 ; stock Sirene alerte à 45 jours, échec à 75.</p>`);
```

```js
display(panneau("Contrôles chiffrés", null, Inputs.table(qualite.metriques.map((m) => ({
  source: m.source,
  controle: m.libelle,
  valeur: m.valeur,
  seuil: m.seuil,
  statut: m.statut
})), {
  header: {source: "Source", controle: "Contrôle", valeur: "Valeur", seuil: "Seuil bloquant", statut: "Statut"},
  format: {
    valeur: (v) => (v <= 1 && !Number.isInteger(v) ? pourcent(v, 1) : nombre(v)),
    seuil: (v) => (v == null ? "–" : `≥ ${pourcent(v)}`),
    statut: (s) => (s === "ok" ? "✓ conforme" : s === "info" ? "information" : "✗ échec")
  },
  layout: "auto",
  rows: 20
})));
```

```js
if (t.disponible && t.non_ok.length) display(html`<p class="note">Alertes non bloquantes de la dernière exécution : ${t.non_ok.map((x) => `${x.test} (${x.lignes} ligne(s))`).join(", ")}.</p>`);
```

```js
display(panneau("Secret statistique", null, Inputs.table(Object.entries(qualite.secret.par_indicateur).map(([ind, s]) => ({
  indicateur: libelle(ind),
  cases: s.cases,
  primaire: s.masquees_primaire,
  secondaire: s.masquees_secondaire
})), {
  header: {indicateur: "Indicateur", cases: "Cases calculées", primaire: `Masquées (< ${qualite.secret.seuil})`, secondaire: "Masquées (anti-recalcul)"},
  format: {cases: nombre, primaire: nombre, secondaire: nombre},
  layout: "auto"
}), html`<p class="note">Le masquage est vérifié par un contrôle indépendant avant publication : aucune case publiée n'est comprise entre 1 et ${qualite.secret.seuil - 1}, et aucune case masquée n'est recalculable par différence avec les totaux publiés.</p>`));
```

```js
const ev = qualite.evaluation_jev;
const part = qualite.metriques.find((m) => m.metrique === "taux_secteur_jev_perimetre")?.valeur;
display(panneau("Attribution sectorielle par IA (Jev, TypeSafe)", null, ev ? html`<p>Pour <strong>${pourcent(part, 1)}</strong> des événements BODACC du territoire, le secteur ne vient pas de Sirene mais d'une classification du texte d'activité de l'annonce par le modèle <strong>${ev.modeles.join(", ")}</strong>. Le modèle ne décide que s'il est assez sûr ; sinon l'événement reste « activité non déterminée ».</p>
<p>Évaluation sur ${ev.echantillon} annonces dont le secteur est connu par Sirene : <strong>${pourcent(ev.politique_retenue.part_division + ev.politique_retenue.part_section)}</strong> reçoivent un secteur, avec une précision de <strong>${pourcent(ev.politique_retenue.precision_globale_attribuees)}</strong> (division : ${pourcent(ev.politique_retenue.precision_division)} ; section seule : ${pourcent(ev.politique_retenue.precision_section)}).</p>
${Inputs.table(ev.calibration, {header: {confiance: "Confiance du modèle", annonces: "Annonces", division_juste: "Division juste"}, format: {division_juste: (v) => pourcent(v)}, layout: "auto"})}
<p class="note">La justesse croît avec la confiance annoncée : c'est ce qui permet de fixer un seuil. Seul le texte d'activité est envoyé au modèle (ni nom, ni SIREN, ni adresse). Évalué le ${ev.evalue_le.slice(0, 10)}.</p>`
: html`<p class="note">Aucune évaluation de l'attribution par IA n'est disponible. Part des événements classés par Jev : ${pourcent(part, 1)}.</p>`));
```

```js
const runs = [...new Set(historiqueQualite.map((d) => d.date_run))];
if (runs.length < 2) {
  display(panneau("Historique des contrôles", null, html`<p class="note">L'historique se construit à chaque exécution (${runs.length} exécution enregistrée pour l'instant). Il permettra de suivre dans le temps le taux de jointure, la localisation et les révisions des séries Sirene (enregistrements tardifs).</p>`));
} else {
  const taux = historiqueQualite.filter((d) => d.metrique.startsWith("taux_")).map((d) => ({...d, date: new Date(d.date_run), valeur: +d.valeur}));
  display(panneau("Historique des contrôles", null, resize((width) => Plot.plot({
    width, height: 240, y: {grid: true, tickFormat: (d) => pourcent(d), label: null},
    marks: [Plot.lineY(taux, {x: "date", y: "valeur", z: "metrique", stroke: "var(--serie-1)", strokeOpacity: 0.7, tip: true, title: "metrique"})]
  }))));
}
```

```js
display(sources("sirene", "bodacc", "bmo", "geo", "naf"));
```
