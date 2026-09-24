// Graphiques et éléments d'interface réutilisés par toutes les pages.
import * as Plot from "npm:@observablehq/plot";
import {html, svg} from "npm:htl";
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

const reduireMouvement = () => matchMedia("(prefers-reduced-motion: reduce)").matches;

/** Compteur animé jusqu'à la valeur publiée ; le texte final est toujours nombre(cible). */
export function compter(el, cible) {
  if (reduireMouvement()) return;
  const t0 = performance.now();
  const pas = (t) => {
    const k = Math.min(1, (t - t0) / 900);
    el.textContent = nombre(Math.round(cible * (1 - (1 - k) ** 3)));
    if (k < 1) requestAnimationFrame(pas);
  };
  requestAnimationFrame(pas);
}

/** Mini-courbe des 24 derniers mois consolidés (mois provisoires exclus : pas de fausse tendance). */
export function sparkline(ind, geo = "TOTAL") {
  const s = serieMensuelle(ind, geo).filter((d) => !d.provisoire).slice(-24);
  return Plot.plot({
    width: 320,
    height: 44,
    margin: 3,
    axis: null,
    className: "sparkline",
    ariaLabel: `Évolution mensuelle sur 24 mois : ${libelle(ind)}`,
    x: {type: "utc"},
    y: {zero: true},
    marks: [
      Plot.areaY(s, {x: "date", y: "v", fill: COULEUR, fillOpacity: 0.06, curve: "monotone-x"}),
      Plot.lineY(s, {x: "date", y: "v", stroke: COULEUR, strokeWidth: 1.6, curve: "monotone-x"})
    ]
  });
}

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
    ${sparkline(ind, geo)}
  </a>`;
}

let identifiants = 0;
const moisCourt = new Intl.DateTimeFormat("fr-FR", {month: "short", timeZone: "UTC"});
// Axe en français ; l'année n'est rappelée qu'en janvier.
const moisAxe = (d) => (d.getUTCMonth() === 0 ? `${moisCourt.format(d)}
${d.getUTCFullYear()}` : moisCourt.format(d));
const moisSuivant = (date) => new Date(Date.UTC(date.getUTCFullYear(), date.getUTCMonth() + 1, 1));
// Pics de janvier des créations Sirene : date conventionnelle du 1er janvier (docs/methodologie.md).
const effetJanvier = (ind, periode) => ind.startsWith("creations_") && periode.endsWith("-01");

/**
 * Série mensuelle : l'année en cours en couleur, la même période un an avant en gris (emphase).
 * Rendu inspiré de Bklit UI (aire en dégradé, courbe monotone, réticule au survol). Les mois
 * masqués sont des bandes hachurées et des trous dans la courbe, jamais des zéros ; un zéro
 * tracé est un vrai zéro publié.
 */
export function graphiqueMensuel(ind, {geo = "TOTAL", niv = "T", sect = "", width, hauteur = 300, trace = false} = {}) {
  const s = serieMensuelle(ind, geo, niv, sect);
  const masques = s.filter((d) => d.v == null);
  const provisoires = s.filter((d) => d.provisoire);
  // Mois publiés entourés de mois masqués : sans point, ils seraient invisibles.
  const isoles = s.filter((d, i) => d.v != null && s[i - 1]?.v == null && s[i + 1]?.v == null);
  const id = ++identifiants;
  const graphique = Plot.plot({
    width,
    height: hauteur,
    marginLeft: 44,
    className: trace ? "trace" : undefined,
    x: {type: "utc", label: null, tickFormat: moisAxe},
    y: {grid: true, label: "événements / mois", zero: true, tickFormat: (d) => nombre(d)},
    marks: [
      () => svg`<defs>
        <linearGradient id=${`degrade-${id}`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" style="stop-color:var(--serie-1);stop-opacity:.12" />
          <stop offset="1" style="stop-color:var(--serie-1);stop-opacity:0" />
        </linearGradient>
        <pattern id=${`hachure-${id}`} width="5" height="5" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
          <rect width="1.5" height="5" style="fill:var(--masque)" />
        </pattern>
      </defs>`,
      provisoires.length
        ? Plot.rectX([{x1: provisoires[0].date, x2: moisSuivant(provisoires.at(-1).date)}], {
            x1: "x1",
            x2: "x2",
            fill: "var(--provisoire)"
          })
        : null,
      Plot.rectX(masques, {x1: "date", x2: (d) => moisSuivant(d.date), fill: `url(#hachure-${id})`}),
      Plot.areaY(s, {x: "date", y: "v", fill: `url(#degrade-${id})`, curve: "monotone-x"}),
      Plot.lineY(s, {x: "date", y: "n1", stroke: COULEUR_N1, strokeWidth: 2, curve: "monotone-x"}),
      Plot.lineY(s, {x: "date", y: "v", stroke: COULEUR, strokeWidth: 2, curve: "monotone-x"}),
      Plot.dot(isoles, {x: "date", y: "v", r: 2.5, fill: COULEUR}),
      Plot.ruleY([0], {stroke: "var(--axe)"}),
      Plot.ruleX(s, Plot.pointerX({x: "date", stroke: "var(--reticule)", strokeWidth: 1})),
      // Point masqué par opacité (et non filtré) : le réticule reste aligné sur le mois survolé.
      Plot.dot(
        s,
        Plot.pointerX({
          x: "date",
          y: (d) => d.v ?? 0,
          r: 4.5,
          fill: "var(--gorri)",
          stroke: "var(--theme-background)",
          strokeWidth: 2,
          fillOpacity: (d) => (d.v == null ? 0 : 1),
          strokeOpacity: (d) => (d.v == null ? 0 : 1)
        })
      ),
      Plot.tip(
        s,
        Plot.pointerX({
          fill: "var(--chaux)",
          stroke: "var(--trait)",
          x: "date",
          y: (d) => d.v ?? 0,
          title: (d) =>
            `${moisLong(d.periode)}${d.provisoire ? " (provisoire)" : ""}\n` +
            `${libelle(ind)} : ${d.v == null ? "secret statistique" : nombre(d.v)}\n` +
            `Même mois un an avant : ${d.n1 == null ? "–" : nombre(d.n1)}` +
            (effetJanvier(ind, d.periode) ? "\nJanvier gonflé : dates conventionnelles au 1er janvier" : "")
        })
      )
    ]
  });
  // pathLength normalisé : l'animation CSS du tracé ne dépend pas de la longueur de la courbe.
  if (trace) for (const p of graphique.querySelectorAll('g[aria-label="line"] path')) p.setAttribute("pathLength", "1");
  return graphique;
}

export function legendeMensuelle() {
  return html`<div class="legende">
    <span><i style="background:var(--serie-1)"></i>mois courant</span>
    <span><i style="background:var(--serie-n1)"></i>même mois un an avant</span>
    <span><i class="zone"></i>mois provisoires</span>
    <span><i class="hachure"></i>mois masqué (secret statistique)</span>
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
    x: {grid: true, label: `événements sur 12 mois (${libelleFenetre(fin)})`, tickFormat: (d) => nombre(d)},
    y: {label: null, domain: donnees.map((d) => d.libelle)},
    marks: [
      Plot.barX(donnees, {x: "v", y: "libelle", fill: COULEUR, rx: 4, insetTop: 3, insetBottom: 3, tip: {fill: "var(--chaux)", stroke: "var(--trait)"}}),
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
  const id = ++identifiants;
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
      range: ["#dde6e0", "#afc7ba", "#7ca590", "#4d8169", "#2c5e4a"],
      domain: connus.map((d) => d.pour1000),
      label: `pour 1 000 habitants (${libelleFenetre(fin)})`,
      legend: true,
      tickFormat: (d) => d.toLocaleString("fr-FR", {maximumFractionDigits: 1})
    },
    marks: [
      () => svg`<defs><pattern id=${`hachure-carte-${id}`} width="5" height="5" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
        <rect width="1.5" height="5" style="fill:var(--masque)" />
      </pattern></defs>`,
      Plot.geo(contours.features, {
        fill: (f) => valeurs.get(f.properties.code)?.pour1000 ?? null,
        stroke: "var(--theme-background)",
        strokeWidth: 0.6
      }),
      Plot.geo(contours.features.filter((f) => valeurs.get(f.properties.code)?.v == null), {
        fill: `url(#hachure-carte-${id})`,
        stroke: "var(--theme-background)",
        strokeWidth: 0.6
      }),
      Plot.tip(contours.features, Plot.pointer(Plot.geoCentroid({title: titre, fill: "var(--chaux)", stroke: "var(--trait)"})))
    ]
  });
  return html`<div>${carte}<p class="note">Hachuré : commune sous secret statistique (moins de ${meta.seuil_secret} événements, ou valeur masquée pour empêcher un recalcul). Survolez une commune pour le détail.</p></div>`;
}

/** Pied de page obligatoire : chaque source citée avec millésime et date d'extraction. */
export function sources(...cles) {
  return html`<div class="sources"><strong>Sources</strong><ul>${cles.map((k) => {
    const s = meta.sources[k];
    return html`<li><a href=${s.url}>${s.nom}</a> — ${s.millesime} ; extrait le ${s.extrait_le ?? "?"} ; ${s.licence}.</li>`;
  })}</ul><p>Traitements : observatoire économique du Pays Basque, données générées le ${meta.genere_le.slice(0, 10)}. Agrégats uniquement ; cases de moins de ${meta.seuil_secret} événements masquées.</p></div>`;
}
