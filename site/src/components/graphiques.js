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
  nomCommune,
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

/** Panneau : titre, portée des données (territoire, période) et contenu, qui changent ensemble. */
export function panneau(titre, portees, ...contenu) {
  const p = [portees].flat().filter(Boolean);
  return html`<section class="panneau">
    <header><h2>${titre}</h2>${p.length ? html`<span class="portees">${p.map((x) => html`<span class="portee">${x}</span>`)}</span>` : null}</header>
    ${contenu}
  </section>`;
}

/** Valeur publiée, ou mention explicite du secret statistique (jamais un zéro). */
export const valeurOuSecret = (v, classe = "") =>
  v == null
    ? html`<span class="${classe} secret" title="Secret statistique : moins de ${meta.seuil_secret} événements ou case recalculable">secret</span>`
    : html`<span class=${classe}>${nombre(v)}</span>`;

/** Contenu d'une tuile : valeur 12 mois glissants et évolution vs les 12 mois précédents. */
function contenuTuile(ind, geo) {
  const [precedente, derniere] = fenetres(ind);
  const a = cellule(ind, "12m", derniere, geo);
  const b = precedente ? cellule(ind, "12m", precedente, geo) : {v: null};
  const evo = evolution(a.v, b.v);
  // Évolution en encre neutre : une hausse n'est pas « bonne » par nature (défaillances, radiations).
  const fleche = evo == null ? "" : evo > 0 ? "▲ " : evo < 0 ? "▼ " : "";
  return [
    html`<span class="tuile-nom">${libelle(ind)}</span>`,
    valeurOuSecret(a.v, "big"),
    html`<span class="muted">${geo === "TOTAL" ? "" : `${nomCommune.get(geo)}, `}sur 12 mois (${libelleFenetre(derniere)})</span>`,
    html`<span class="evolution">${
      evo == null ? "évolution non calculable" : `${fleche}${evo > 0 ? "+" : ""}${pourcent(evo, 1)} sur un an`
    }</span>`,
    sparkline(ind, geo)
  ];
}

/** Tuile chiffre-clé, cliquable si `lien` est fourni. */
export function tuile(ind, {geo = "TOTAL", lien} = {}) {
  return lien
    ? html`<a class="tuile" href=${lien}>${contenuTuile(ind, geo)}</a>`
    : html`<div class="tuile">${contenuTuile(ind, geo)}</div>`;
}

// Dernier onglet choisi par groupe : un changement de territoire ne réinitialise pas la mesure.
const ongletsChoisis = new Map();

/**
 * Tuiles-onglets : la tuile choisie pilote les panneaux qui suivent (à utiliser avec view()).
 * La valeur est le code de l'indicateur choisi.
 */
export function onglets(indicateurs, {geo = "TOTAL", cle = indicateurs.join()} = {}) {
  const boutons = indicateurs.map(
    (ind) => html`<button type="button" class="tuile" data-ind=${ind}>${contenuTuile(ind, geo)}</button>`
  );
  const el = html`<div class="tuiles" role="group" aria-label="Indicateur affiché">${boutons}</div>`;
  const choisir = (ind) => {
    el.value = ind;
    ongletsChoisis.set(cle, ind);
    for (const b of boutons) b.setAttribute("aria-pressed", String(b.dataset.ind === ind));
  };
  choisir(ongletsChoisis.get(cle) ?? indicateurs[0]);
  for (const b of boutons)
    b.onclick = () => {
      if (b.dataset.ind === el.value) return;
      choisir(b.dataset.ind);
      el.dispatchEvent(new Event("input", {bubbles: true}));
    };
  return el;
}

/**
 * Barres horizontales en HTML : libellé au-dessus de la barre (jamais tronqué, retour à la
 * ligne sur mobile), valeur à droite. `n1` optionnel : barre fantôme de la période précédente.
 * Une valeur masquée est écrite « secret », sans barre.
 */
export function barres(lignes, {fantome = false} = {}) {
  const max = Math.max(1, ...lignes.flatMap((d) => [d.v ?? 0, fantome ? (d.n1 ?? 0) : 0]));
  const largeur = (v) => `${(100 * v) / max}%`;
  return html`<ol class="barres">${lignes.map(
    (d) => html`<li>
      <span class="barres-libelle">${d.libelle}</span>
      ${valeurOuSecret(d.v, "barres-valeur")}
      <span class="barres-piste" aria-hidden="true">${
        fantome && d.n1 != null ? html`<i class="fantome" style=${{width: largeur(d.n1)}}></i>` : null
      }${d.v == null ? null : html`<i style=${{width: largeur(d.v)}}></i>`}</span>
    </li>`
  )}</ol>`;
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
  // Mois provisoires incomplets : tracés en pointillés depuis le dernier mois consolidé, sans
  // aire, pour que leur baisse ne se lise pas comme une tendance.
  const iProv = s.findIndex((d) => d.provisoire);
  const consolides = iProv < 0 ? s : s.slice(0, iProv);
  const recents = iProv < 0 ? [] : s.slice(Math.max(0, iProv - 1));
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
      provisoires.length
        ? Plot.text([moisSuivant(provisoires.at(-1).date)], {
            x: (d) => d,
            text: () => "provisoire",
            frameAnchor: "top",
            textAnchor: "end",
            dx: -4,
            dy: 4,
            fontSize: 11,
            fill: "var(--texte-3)"
          })
        : null,
      Plot.rectX(masques, {x1: "date", x2: (d) => moisSuivant(d.date), fill: `url(#hachure-${id})`}),
      Plot.areaY(consolides, {x: "date", y: "v", fill: `url(#degrade-${id})`, curve: "monotone-x"}),
      Plot.lineY(s, {x: "date", y: "n1", stroke: COULEUR_N1, strokeWidth: 2, curve: "monotone-x"}),
      Plot.lineY(consolides, {x: "date", y: "v", stroke: COULEUR, strokeWidth: 2, curve: "monotone-x"}),
      Plot.lineY(recents, {
        x: "date",
        y: "v",
        stroke: COULEUR,
        strokeWidth: 2,
        strokeOpacity: 0.55,
        strokeDasharray: "4 3",
        curve: "monotone-x",
        className: "segment-provisoire"
      }),
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
          fill: "var(--accent)",
          stroke: "var(--theme-background)",
          strokeWidth: 2,
          fillOpacity: (d) => (d.v == null ? 0 : 1),
          strokeOpacity: (d) => (d.v == null ? 0 : 1)
        })
      ),
      Plot.tip(
        s,
        Plot.pointerX({
          fill: "var(--surface)",
          stroke: "var(--bord)",
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
  if (trace)
    for (const p of graphique.querySelectorAll('g[aria-label="line"]:not(.segment-provisoire) path'))
      p.setAttribute("pathLength", "1");
  return graphique;
}

export function legendeMensuelle() {
  return html`<div class="legende">
    <span><i style="background:var(--serie-1)"></i>mois courant</span>
    <span><i style="background:var(--serie-n1)"></i>même mois un an avant</span>
    <span><i class="pointille"></i><i class="zone"></i>mois provisoires (incomplets)</span>
    <span><i class="hachure"></i>mois masqué (secret statistique)</span>
  </div>`;
}

/** Barres par section NAF sur les 12 derniers mois consolidés (magnitude : une seule teinte). */
export function barresSecteurs(ind, {geo = "TOTAL", niv = "S", max = 25} = {}) {
  const [, fin] = fenetres(ind);
  const donnees = parSecteur(ind, fin, geo, niv)
    .filter((d) => d.v != null)
    .sort((a, b) => b.v - a.v)
    .slice(0, max);
  const masquees = parSecteur(ind, fin, geo, niv).filter((d) => d.v == null).length;
  return html`<div>${
    donnees.length ? barres(donnees) : html`<p class="note">Aucun secteur publiable sur cette période.</p>`
  }${
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
      range: ["#dfe7f0", "#b3c6da", "#83a2c2", "#5579a3", "#2f5378"],
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
      Plot.tip(contours.features, Plot.pointer(Plot.geoCentroid({title: titre, fill: "var(--surface)", stroke: "var(--bord)"})))
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
