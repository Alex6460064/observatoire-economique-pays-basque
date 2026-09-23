// Graphiques et éléments d'interface réutilisés par toutes les pages.
import * as Plot from "npm:@observablehq/plot";
import {html} from "npm:htl";
import {
  cellule,
  evolution,
  fenetres,
  libelle,
  libelleFenetre,
  meta,
  moisLong,
  nombre,
  parSecteur,
  pourcent,
  serieMensuelle,
  contours,
  parCommune
} from "./donnees.js";

// Rôles de couleur (palette de référence validée, voir docs/decisions.md) : définis en CSS.
export const COULEUR = "var(--serie-1)";
export const COULEUR_N1 = "var(--serie-n1)";
export const CATEGORIES = ["var(--serie-1)", "var(--serie-2)", "var(--serie-3)"];

/** Tuile chiffre-clé : valeur 12 mois glissants et évolution vs les 12 mois précédents. */
export function tuile(ind, {geo = "TOTAL", lien} = {}) {
  const [precedente, derniere] = fenetres(ind);
  const a = cellule(ind, "12m", derniere, geo);
  const b = precedente ? cellule(ind, "12m", precedente, geo) : {v: null};
  const evo = evolution(a.v, b.v);
  // Évolution en encre neutre : une hausse n'est pas « bonne » par nature (défaillances, radiations).
  const fleche = evo == null ? "" : evo > 0 ? "▲ " : evo < 0 ? "▼ " : "";
  return html`<a class="card tuile" href=${lien ?? "#"}>
    <h2>${libelle(ind)}</h2>
    <span class="big">${nombre(a.v)}</span>
    <span class="muted">sur 12 mois (${libelleFenetre(derniere)})</span>
    <span class="evolution">${
      evo == null ? "évolution non calculable" : `${fleche}${evo > 0 ? "+" : ""}${pourcent(evo, 1)} sur un an`
    }</span>
  </a>`;
}

/** Série mensuelle : l'année en cours en couleur, la même période un an avant en gris (emphase). */
export function graphiqueMensuel(ind, {geo = "TOTAL", niv = "T", sect = "", width, hauteur = 300} = {}) {
  const s = serieMensuelle(ind, geo, niv, sect);
  const masques = s.filter((d) => d.v == null);
  const provisoires = s.filter((d) => d.provisoire);
  return Plot.plot({
    width,
    height: hauteur,
    marginLeft: 44,
    x: {type: "utc", label: null},
    y: {grid: true, label: "événements / mois", zero: true},
    marks: [
      provisoires.length
        ? Plot.rectX([{x1: provisoires[0].date, x2: new Date(+provisoires.at(-1).date + 31 * 864e5)}], {
            x1: "x1",
            x2: "x2",
            fill: "var(--provisoire)",
            fillOpacity: 1
          })
        : null,
      Plot.lineY(s, {x: "date", y: "n1", stroke: COULEUR_N1, strokeWidth: 2}),
      Plot.lineY(s, {x: "date", y: "v", stroke: COULEUR, strokeWidth: 2}),
      Plot.dot(masques, {x: "date", y: 0, symbol: "times", r: 4, stroke: "var(--theme-foreground-muted)"}),
      Plot.ruleY([0], {stroke: "var(--axe)"}),
      Plot.tip(
        s,
        Plot.pointerX({
          x: "date",
          y: (d) => d.v ?? 0,
          title: (d) =>
            `${moisLong(d.periode)}${d.provisoire ? " (provisoire)" : ""}\n` +
            `${libelle(ind)} : ${d.v == null ? "secret statistique" : nombre(d.v)}\n` +
            `Même mois un an avant : ${d.n1 == null ? "–" : nombre(d.n1)}`
        })
      )
    ]
  });
}

export function legendeMensuelle() {
  return html`<div class="legende">
    <span><i style="background:var(--serie-1)"></i>mois courant</span>
    <span><i style="background:var(--serie-n1)"></i>même mois un an avant</span>
    <span><i class="zone"></i>mois provisoires</span>
    <span>× secret statistique</span>
  </div>`;
}

/** Barres horizontales par section NAF sur 12 mois (magnitude : une seule teinte). */
export function barresSecteurs(ind, {geo = "TOTAL", niv = "S", width, max = 25} = {}) {
  const [, fin] = fenetres(ind);
  const donnees = parSecteur(ind, fin, geo, niv)
    .filter((d) => d.v != null)
    .sort((a, b) => b.v - a.v)
    .slice(0, max);
  const masquees = parSecteur(ind, fin, geo, niv).filter((d) => d.v == null).length;
  const graphique = Plot.plot({
    width,
    height: 26 * donnees.length + 40,
    marginLeft: Math.min(320, width * 0.48),
    x: {grid: true, label: `événements sur 12 mois (${libelleFenetre(fin)})`},
    y: {label: null, domain: donnees.map((d) => d.libelle)},
    marks: [
      Plot.barX(donnees, {x: "v", y: "libelle", fill: COULEUR, rx: 4, insetTop: 2, insetBottom: 2, tip: true}),
      Plot.ruleX([0], {stroke: "var(--axe)"}),
      Plot.text(donnees, {x: "v", y: "libelle", text: (d) => nombre(d.v), dx: 4, textAnchor: "start", fill: "var(--theme-foreground-muted)"})
    ],
    style: {overflow: "visible"}
  });
  return html`<div>${graphique}${
    masquees ? html`<p class="note">${masquees} secteur(s) non affiché(s) : secret statistique (moins de ${meta.seuil_secret} événements ou case recalculable).</p>` : ""
  }</div>`;
}

/**
 * Carte des communes : taux pour 1 000 habitants sur les 12 derniers mois consolidés.
 * Rampe séquentielle à une teinte (magnitude), classes par quantiles (distribution très
 * asymétrique) ; communes sous secret statistique en gris neutre, jamais colorées.
 */
export function carteCommunes(ind, {width} = {}) {
  const [precedente, fin] = fenetres(ind);
  const valeurs = new Map(parCommune(ind, fin, precedente).map((d) => [d.code, d]));
  const connus = [...valeurs.values()].filter((d) => d.pour1000 != null);
  const hauteur = Math.min(560, Math.round(width * 0.78));
  const titre = (f) => {
    const d = valeurs.get(f.properties.code);
    return `${f.properties.nom}
${
      d?.v == null ? "secret statistique" : `${nombre(d.v)} sur 12 mois · ${d.pour1000.toLocaleString("fr-FR", {maximumFractionDigits: 1})} pour 1 000 hab.`
    }`;
  };
  const carte = Plot.plot({
    width,
    height: hauteur,
    projection: {type: "mercator", domain: contours},
    color: {
      type: "quantile",
      n: 5,
      scheme: "blues",
      domain: connus.map((d) => d.pour1000),
      label: `pour 1 000 habitants (${libelleFenetre(fin)})`,
      legend: true,
      tickFormat: (d) => d.toLocaleString("fr-FR", {maximumFractionDigits: 1})
    },
    marks: [
      Plot.geo(contours.features, {
        fill: (f) => valeurs.get(f.properties.code)?.pour1000 ?? null,
        stroke: "var(--theme-background)",
        strokeWidth: 0.6
      }),
      Plot.geo(contours.features.filter((f) => valeurs.get(f.properties.code)?.v == null), {
        fill: "var(--theme-foreground-faintest)",
        stroke: "var(--theme-background)",
        strokeWidth: 0.6
      }),
      Plot.tip(contours.features, Plot.pointer(Plot.geoCentroid({title: titre})))
    ]
  });
  return html`<div>${carte}<p class="note">Gris : commune sous secret statistique (moins de ${meta.seuil_secret} événements, ou valeur masquée pour empêcher un recalcul). Survolez une commune pour le détail.</p></div>`;
}

/** Pied de page obligatoire : chaque source citée avec millésime et date d'extraction. */
export function sources(...cles) {
  return html`<div class="sources"><strong>Sources</strong><ul>${cles.map((k) => {
    const s = meta.sources[k];
    return html`<li><a href=${s.url}>${s.nom}</a> — ${s.millesime} ; extrait le ${s.extrait_le ?? "?"} ; ${s.licence}.</li>`;
  })}</ul><p>Traitements : observatoire économique du Pays Basque, données générées le ${meta.genere_le.slice(0, 10)}. Agrégats uniquement ; cases de moins de ${meta.seuil_secret} événements masquées.</p></div>`;
}
